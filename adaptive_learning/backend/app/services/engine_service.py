"""RecommendationEngine and Member 2 LearningPredictor service.

Handles singleton initialization, student state restoration from SQLite,
thread-safe attempt recording, and recommendation generation.
"""

from __future__ import annotations

import logging
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import BASE_DIR
from backend.app.db.base import utc_now
from backend.app.models.attempt import Attempt
from backend.app.models.profile import StudentProfile

# Ensure BASE_DIR and BASE_DIR / "models" are in sys.path for engine & predictor imports
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
models_dir = BASE_DIR / "models"
if str(models_dir) not in sys.path:
    sys.path.insert(0, str(models_dir))

from engine import EngineConfig, RecommendationEngine, TopicGraph, UnknownExerciseError  # noqa: E402
from learning_predictor import LearningPredictor  # noqa: E402

logger = logging.getLogger(__name__)


def _format_placement_reason(reason: str, stage: str, learning_level: str) -> str:
    """Format recommendation reason to be placement-appropriate, replacing raw 'foundation level' text."""
    stg = (stage or "").lower()
    lvl = (learning_level or "").lower()

    if stg == "senior" or lvl == "advanced":
        placement = "Senior High"
    elif stg == "junior" or lvl == "intermediate":
        placement = "Junior High"
    else:
        placement = "Elementary"

    formatted = reason
    formatted = formatted.replace("foundation topic (foundation level)", f"starting topic ({placement} placement)")
    formatted = formatted.replace("foundation topic (selected topic)", f"curriculum topic ({placement} placement)")
    formatted = formatted.replace("(foundation level)", f"({placement} placement)")
    formatted = formatted.replace("foundation topic", f"{placement} topic" if placement != "Elementary" else "introductory topic")
    formatted = formatted.replace("New topic unlocked: foundation level.", f"New topic unlocked for {placement} placement.")
    formatted = formatted.replace("New topic unlocked: foundation level", f"New topic unlocked for {placement} placement")
    return formatted


class EngineService:
    """Thread-safe manager for the RecommendationEngine and LearningPredictor."""

    def __init__(self, base_dir: Path = BASE_DIR):
        self.base_dir = Path(base_dir)
        self._lock = threading.RLock()
        self._engine: Optional[RecommendationEngine] = None
        self._graph: Optional[TopicGraph] = None
        self._predictor: Optional[LearningPredictor] = None
        self._initialized_students: Set[str] = set()

    def get_engine(self) -> RecommendationEngine:
        """Return initialized RecommendationEngine singleton, creating it if needed."""
        with self._lock:
            if self._engine is None:
                self._initialize()
            return self._engine

    def _initialize(self) -> None:
        """Load topic graph and Member 2 predictor artifacts."""
        logger.info("Initializing TopicGraph and LearningPredictor from %s...", self.base_dir)

        # 1. Build TopicGraph from project lookup and metadata CSVs
        graph = TopicGraph.from_project(self.base_dir)
        self._graph = graph

        # 2. Load Member 2 trained model, model card, and lookup
        model_path = self.base_dir / "models" / "member2_final_model.joblib"
        card_path = self.base_dir / "models" / "member2_model_card.json"
        lookup_path = self.base_dir / "models" / "member2_exercise_lookup.csv"

        predictor: Optional[LearningPredictor] = None
        if model_path.exists() and card_path.exists() and lookup_path.exists():
            try:
                predictor = LearningPredictor.from_files(
                    model_path=str(model_path),
                    card_path=str(card_path),
                    lookup_path=str(lookup_path),
                )
                logger.info("Member 2 LearningPredictor successfully loaded.")
            except Exception as exc:
                logger.warning("Could not load LearningPredictor (%s). Running with fallback base rates.", exc)
                predictor = None
        else:
            logger.warning("Predictor artifacts missing at %s. Running without predictor.", self.base_dir / "models")

        self._predictor = predictor

        # 3. Create RecommendationEngine instance
        config = EngineConfig(include_chinese=False)
        self._engine = RecommendationEngine(graph=graph, predictor=predictor, config=config)
        logger.info("RecommendationEngine initialized successfully with %d concepts and %d exercises.",
                    len(graph.concepts), len(graph.exercises))

    def ensure_student_loaded(self, student_id: str, db: Session) -> None:
        """Restore student state into RecommendationEngine from database if not already loaded.

        Prevents duplicate history replays by checking self._initialized_students under lock.
        """
        student_key = str(student_id)
        with self._lock:
            engine = self.get_engine()
            if student_key in self._initialized_students:
                return

            # Retrieve student onboarding stage from profile
            stmt = select(StudentProfile).where(StudentProfile.student_id == student_key)
            profile = db.scalars(stmt).first()
            stage = profile.engine_stage if profile else "elementary"

            # Register student stage placement
            engine.register_student(student_key, start_stage=stage)

            # Query historical attempts in chronological order (replay index)
            attempt_stmt = (
                select(Attempt)
                .where(Attempt.student_id == student_key)
                .order_by(Attempt.timestamp.asc(), Attempt.id.asc())
            )
            attempts = db.scalars(attempt_stmt).all()

            # Replay history rows: (ts, ucid, is_correct)
            if attempts:
                history_rows = [
                    (att.timestamp, att.ucid, bool(att.is_correct))
                    for att in attempts
                ]
                engine.load_history(student_key, history_rows)
                logger.info("Replayed %d historical attempts for student %s.", len(history_rows), student_key)

            self._initialized_students.add(student_key)

    def record_attempt(
        self,
        student_id: str,
        ucid: str,
        is_correct: bool,
        db: Session,
        timestamp: Optional[datetime] = None,
    ) -> Attempt:
        """Validate exercise UCID, derive concept_code, persist Attempt in SQLite, and update engine."""
        student_key = str(student_id)
        ucid_str = str(ucid).strip()

        with self._lock:
            engine = self.get_engine()

            # 1. Validate UCID against graph exercises
            concept_code = engine.graph.concept_of(ucid_str)
            if concept_code is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Exercise UCID '{ucid_str}' not found in curriculum dataset.",
                )

            # 2. Ensure student history is restored in memory
            self.ensure_student_loaded(student_key, db)

            # 3. Determine safe, monotonic timestamp for LearningPredictor
            now = utc_now()
            if timestamp is not None:
                ts = timestamp if timestamp.tzinfo is not None else timestamp.replace(tzinfo=timezone.utc)
            else:
                ts = now

            # Ensure timestamp is not older than the student's most recent committed attempt
            last_attempt = db.scalars(
                select(Attempt)
                .where(Attempt.student_id == student_key)
                .order_by(Attempt.timestamp.desc(), Attempt.id.desc())
            ).first()

            if last_attempt is not None and ts < last_attempt.timestamp:
                ts = last_attempt.timestamp + timedelta(milliseconds=10)

            # 4. Persist to database
            attempt = Attempt(
                student_id=student_key,
                ucid=ucid_str,
                concept_code=concept_code,
                is_correct=bool(is_correct),
                timestamp=ts,
            )
            db.add(attempt)
            db.flush()
            db.commit()

            # 5. Update engine in-memory state
            try:
                engine.record_answer(
                    student_id=student_key,
                    ucid=ucid_str,
                    is_correct=bool(is_correct),
                    ts=attempt.timestamp,
                )
            except Exception as exc:
                logger.exception("Engine update failed after DB commit for student %s: %s", student_key, exc)
                self.reset_student_state(student_key, db)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update recommendation engine state.",
                )

            return attempt

    def get_learning_path(
        self,
        student_id: str,
        db: Session,
        n_steps: int = 5,
        exercises_per_step: int = 3,
        exercise_steps: int = 1,
    ) -> Dict[str, Any]:
        """Generate personalized learning path respecting student stage placement and engine rules."""
        student_key = str(student_id)
        with self._lock:
            engine = self.get_engine()
            self.ensure_student_loaded(student_key, db)

            stmt = select(StudentProfile).where(StudentProfile.student_id == student_key)
            profile = db.scalars(stmt).first()
            stage = profile.engine_stage if profile else "elementary"
            learning_level = profile.learning_level if profile else "beginner"

            # Generate full candidate steps from the recommendation engine
            full_path = engine.generate_path(
                student_id=student_key,
                n_steps=len(engine.graph.concepts),
                exercises_per_step=exercises_per_step,
                exercise_steps=0,
            )

            all_steps = full_path.get("steps", [])
            if not all_steps:
                return full_path

            # Pedagogical priority sorting:
            # Priority 1: Topics needing revision (weak: attempts >= 3, mastery < 0.55)
            revise_steps = [s for s in all_steps if s["action"] == "revise"]
            # Priority 2: Topics in progress (learning)
            practice_steps = [s for s in all_steps if s["action"] == "practice"]

            # Priority 3: Newly unlocked topics (advance).
            # If the student placed into Junior or Senior stage, prioritize unattempted topics
            # matching their placement stage over lower-grade elementary topics.
            new_steps = [s for s in all_steps if s["action"] == "advance"]
            if stage == "senior":
                st_match = [s for s in new_steps if s["stage"] == "senior"]
                st_junior = [s for s in new_steps if s["stage"] == "junior"]
                st_elem = [s for s in new_steps if s["stage"] == "elementary"]
                ordered_new = st_match + st_junior + st_elem
            elif stage == "junior":
                st_match = [s for s in new_steps if s["stage"] == "junior"]
                st_senior = [s for s in new_steps if s["stage"] == "senior"]
                st_elem = [s for s in new_steps if s["stage"] == "elementary"]
                ordered_new = st_match + st_senior + st_elem
            else:
                ordered_new = new_steps

            # Priority 4: Review steps (proficient / mastered)
            review_steps = [s for s in all_steps if s["action"] == "review"]

            chosen_steps = []
            chosen_steps.extend(revise_steps[: engine.cfg.max_revise_steps])
            for s in practice_steps:
                if len(chosen_steps) < n_steps:
                    chosen_steps.append(s)
            for s in ordered_new:
                if len(chosen_steps) < n_steps:
                    chosen_steps.append(s)
            for s in review_steps:
                if len(chosen_steps) < n_steps:
                    chosen_steps.append(s)

            final_steps = chosen_steps[:n_steps]
            L = engine._learner(student_key)

            # Re-rank and populate exercises for the requested exercise_steps
            for rank, step in enumerate(final_steps, start=1):
                step["rank"] = rank
                action = step["action"]
                target = {
                    "revise": engine.cfg.target_revise,
                    "practice": engine.cfg.target_practice,
                    "advance": engine.cfg.target_new,
                    "review": engine.cfg.target_review,
                }[action]

                if rank <= exercise_steps:
                    exercises, fb = engine._pick_exercises(
                        student_key, L, step["concept_code"], target, exercises_per_step
                    )
                    step["exercises"] = exercises
                    step["fallback_used"] = fb
                    if exercises and engine.predictor is not None:
                        try:
                            step["model_bkt_mastery"] = round(
                                float(engine.predictor.bkt_mastery(student_key, exercises[0]["ucid"])), 4
                            )
                        except Exception:
                            pass
                else:
                    step["exercises"] = []

                # Ensure cold-start reason reflects the student's actual placement level
                if action == "advance" and L.answered == 0:
                    lvl_disp = learning_level.title() if learning_level else "Beginner"
                    stg_disp = (
                        "Senior High" if stage == "senior"
                        else "Junior High" if stage == "junior"
                        else "Elementary"
                    )
                    step["reason"] = (
                        f"Starting topic for your {lvl_disp} ({stg_disp}) placement: "
                        f"{step['name']}."
                    )
                    if step["exercises"]:
                        step["reason"] += f" (predicted success about {step['exercises'][0]['predicted_p_correct']:.0%})"
                else:
                    step["reason"] = _format_placement_reason(
                        step["reason"], step.get("stage") or stage, learning_level
                    )

            return {
                "student_id": student_key,
                "answered": L.answered,
                "cold_start": L.answered == 0,
                "graph_source": engine.graph.source,
                "locked_topics": full_path.get("locked_topics", 0),
                "notes": full_path.get("notes", []),
                "steps": final_steps,
            }

    def get_mastery(self, student_id: str, db: Session) -> Dict[str, Any]:
        """Return student curriculum mastery and progress summary."""
        student_key = str(student_id)
        with self._lock:
            engine = self.get_engine()
            self.ensure_student_loaded(student_key, db)
            return engine.progress(student_key)

    def get_next_exercises(
        self,
        student_id: str,
        db: Session,
        k: int = 3,
        concept_code: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Return next recommended exercises.

        If concept_code is supplied, fetches candidate exercises specifically for that topic.
        Otherwise, returns candidate exercises from the top step of the student's path.
        """
        student_key = str(student_id)
        with self._lock:
            engine = self.get_engine()
            self.ensure_student_loaded(student_key, db)
            L = engine._learner(student_key)

            if concept_code is not None:
                code_int = int(concept_code)
                if code_int not in engine.graph.concepts:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Concept code {code_int} not found in curriculum dataset.",
                    )
                stmt = select(StudentProfile).where(StudentProfile.student_id == student_key)
                profile = db.scalars(stmt).first()
                stage = profile.engine_stage if profile else "elementary"
                learning_level = profile.learning_level if profile else "beginner"

                concept = engine.graph.concepts[code_int]
                s = engine.concept_state(student_key, code_int)
                action = {"weak": "revise", "learning": "practice", "new": "advance", "proficient": "review"}.get(
                    s["status"], "practice"
                )
                target = {
                    "revise": engine.cfg.target_revise,
                    "practice": engine.cfg.target_practice,
                    "advance": engine.cfg.target_new,
                    "review": engine.cfg.target_review,
                }[action]
                exercises, fb = engine._pick_exercises(student_key, L, code_int, target, k)
                p_first = exercises[0]["predicted_p_correct"] if exercises else None
                cold = L.answered == 0
                raw_reason = engine._reason(action, s, concept, "selected topic", cold, p_first)
                reason = _format_placement_reason(raw_reason, concept.stage or stage, learning_level)
                return [
                    {
                        **ex,
                        "concept_code": code_int,
                        "topic": concept.display_name,
                        "action": action,
                        "stage": concept.stage,
                        "reason": reason,
                    }
                    for ex in exercises
                ]

            # Use top step from personalized learning path
            path = self.get_learning_path(student_key, db, n_steps=1, exercises_per_step=k, exercise_steps=1)
            if not path["steps"]:
                return []
            st = path["steps"][0]
            return [
                {
                    **ex,
                    "concept_code": st["concept_code"],
                    "topic": st["name"],
                    "action": st["action"],
                    "stage": st.get("stage"),
                    "reason": st["reason"],
                }
                for ex in st["exercises"]
            ]

    def update_student_stage(self, student_id: str, stage: str) -> None:
        """Update student starting placement stage in the engine."""
        student_key = str(student_id)
        with self._lock:
            engine = self.get_engine()
            engine.register_student(student_key, start_stage=stage)

    def reset_student_state(self, student_id: str, db: Optional[Session] = None) -> None:
        """Reset in-memory student state and optionally reload from database."""
        student_key = str(student_id)
        with self._lock:
            self._initialized_students.discard(student_key)
            if self._engine is not None:
                self._engine.reset_student(student_key)
            if self._predictor is not None and hasattr(self._predictor, "_students"):
                self._predictor._students.pop(student_key, None)
            if db is not None:
                self.ensure_student_loaded(student_key, db)

    def reset_all_students(self) -> None:
        """Clear all student state from memory (used primarily for test isolation)."""
        with self._lock:
            self._initialized_students.clear()
            if self._engine is not None:
                self._engine._learners.clear()
            if self._predictor is not None and hasattr(self._predictor, "_students"):
                self._predictor._students.clear()


# Global engine service singleton instance
engine_service = EngineService()


def get_engine() -> RecommendationEngine:
    """Helper to access global RecommendationEngine."""
    return engine_service.get_engine()
