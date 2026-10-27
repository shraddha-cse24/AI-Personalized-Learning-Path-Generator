"""
recommendation_engine.py  --  Member 3: adaptive learning-path recommender.

Inputs   : TopicGraph (topics + unlock rules) and Member 2's LearningPredictor (P(correct)).
Outputs  : an ordered learning path (list of topic steps, each with ranked exercises and a reason).

How a recommendation is made (all rules are explicit and explainable)
---------------------------------------------------------------------
1. For every topic, the engine tracks the student's own attempts/correct answers.
   Topic mastery = smoothed accuracy:  (correct + k*base_rate) / (attempts + k)
   where base_rate is the topic's historical correct rate, k = `prior_strength` (2).
2. Topic status:
      new       no attempts yet
      weak      >= min_attempts_weak attempts and mastery < weak_threshold
      mastered  >= min(5, number of exercises in the topic, at least 2) attempts and mastery >= 0.80
      learning  everything else
3. A topic is "unlocked" according to the TopicGraph gate (prerequisites / curriculum levels).
4. Priority:  revise weak topics  >  continue topics in progress  >  start newly unlocked topics
   >  review "proficient" topics.  Mastered topics are not recommended again (unless nothing else
   is left -> spaced review).
   "proficient" = one full pass through the topic's exercises with moderate accuracy (0.55-0.80);
   it counts as cleared for unlocking and is only reviewed later.
   Fatigue rule: after `streak_limit` answers in a row in one topic the topic rests for
   `cooldown_answers` answers.  A weak topic drilled `stall_factor` x its pool size without
   recovering is "stalled" and left to a teacher/other help instead of looping forever.
5. Inside a topic, exercises are ranked by how close Member 2's predicted P(correct) is to a
   target (0.80 for revision, 0.70 for practice, 0.75 for a new topic): "challenging but doable".
   Exercises answered recently are excluded; unseen exercises come first.
6. Every step carries a plain-language `reason`.

Fallbacks: no history -> foundation topics; predictor missing or failing -> exercise base rates;
unknown student -> created on first use; unknown exercise id -> UnknownExerciseError (HTTP 404 in API).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from .topic_graph import TopicGraph


class UnknownExerciseError(KeyError):
    """Raised when an exercise id is not in the exercise lookup."""


@dataclass
class EngineConfig:
    mastery_threshold: float = 0.80
    weak_threshold: float = 0.55
    min_attempts_master: int = 5
    min_attempts_weak: int = 3
    prior_strength: float = 2.0
    gate_fraction: float = 0.34
    streak_limit: int = 6
    streak_penalty: float = 2.5
    cooldown_answers: int = 12
    stall_factor: float = 2.0
    max_revise_steps: int = 2
    recent_block: int = 10
    target_revise: float = 0.80
    target_practice: float = 0.70
    target_new: float = 0.75
    target_review: float = 0.85
    include_chinese: bool = False      # False = English-only output (default)


@dataclass
class Learner:
    start_level: int = 0
    concept: Dict[int, List[int]] = field(default_factory=dict)       # code -> [attempts, correct]
    ex_seen: Dict[str, int] = field(default_factory=dict)
    recent: deque = field(default_factory=lambda: deque(maxlen=10))   # last answered ucids
    streak_code: Optional[int] = None
    streak_len: int = 0
    cooldown: Dict[int, int] = field(default_factory=dict)      # code -> answered-count until which it rests
    answered: int = 0
    correct: int = 0
    last_ts: Optional[object] = None


class RecommendationEngine:
    def __init__(self, graph: TopicGraph, predictor=None, config: Optional[EngineConfig] = None):
        self.graph = graph
        self.predictor = predictor
        self.cfg = config or EngineConfig()
        self._learners: Dict[str, Learner] = {}

    # ================================================================== student state
    def _learner(self, student_id) -> Learner:
        key = str(student_id)
        if key not in self._learners:
            self._learners[key] = Learner(recent=deque(maxlen=self.cfg.recent_block))
        return self._learners[key]

    def register_student(self, student_id, start_stage: Optional[str] = None) -> None:
        """Optional placement: unlock all topics up to the first level of `start_stage`."""
        L = self._learner(student_id)
        if start_stage:
            L.start_level = self.graph.stage_start_level(start_stage)

    def record_answer(self, student_id, ucid, is_correct: bool, ts=None) -> None:
        ucid = str(ucid)
        code = self.graph.concept_of(ucid)
        if code is None:
            raise UnknownExerciseError(f"unknown exercise id: {ucid}")
        L = self._learner(student_id)
        y = int(bool(is_correct))
        c = L.concept.setdefault(code, [0, 0])
        c[0] += 1
        c[1] += y
        L.ex_seen[ucid] = L.ex_seen.get(ucid, 0) + 1
        L.recent.append(ucid)
        L.answered += 1
        L.correct += y
        L.streak_len = L.streak_len + 1 if L.streak_code == code else 1
        L.streak_code = code
        if L.streak_len >= self.cfg.streak_limit:
            L.cooldown[code] = L.answered + self.cfg.cooldown_answers
        if self.predictor is not None:
            self.predictor.observe(str(student_id), ucid, bool(y), ts)

    def load_history(self, student_id, rows: Iterable) -> None:
        """rows: iterable of (ts, ucid, is_correct) in chronological order (e.g. from the database)."""
        for ts, ucid, y in rows:
            self.record_answer(student_id, ucid, y, ts)

    def reset_student(self, student_id) -> None:
        self._learners.pop(str(student_id), None)

    # ================================================================== topic state
    def _mastery(self, code: int, n: int, c: int) -> float:
        base = self.graph.concepts[code].base_rate
        k = self.cfg.prior_strength
        return (c + k * base) / (n + k)

    def attempts_needed(self, code: int) -> int:
        """Attempts required before a topic can count as mastered (small topics need fewer)."""
        return min(self.cfg.min_attempts_master, max(2, len(self.graph.concepts[code].ucids)))

    def concept_state(self, student_id, code: int) -> dict:
        L = self._learner(student_id)
        n, c = L.concept.get(code, [0, 0])
        m = self._mastery(code, n, c)
        cfg = self.cfg
        size = len(self.graph.concepts[code].ucids)
        need = self.attempts_needed(code)
        if n == 0:
            status = "new"
        elif n >= need and m >= cfg.mastery_threshold:
            status = "mastered"
        elif n >= cfg.min_attempts_weak and m < cfg.weak_threshold:
            status = "weak"
        elif n >= max(need, size):
            status = "proficient"        # finished a full pass with moderate accuracy
        else:
            status = "learning"
        stalled = status == "weak" and n >= cfg.stall_factor * size
        # mastery is None until the student has attempted the topic (the prior alone is not "their" mastery)
        return {"attempts": n, "correct": c, "accuracy": (c / n) if n else None,
                "mastery": round(m, 4) if n else None, "prior_mastery": round(m, 4),
                "status": status, "stalled": stalled}

    def _all_states(self, student_id) -> Dict[int, dict]:
        return {code: self.concept_state(student_id, code) for code in self.graph.concepts}

    def _mastered_set(self, states) -> set:
        """Topics that count as cleared for unlocking others: mastered or proficient."""
        return {c for c, s in states.items() if s["status"] in ("mastered", "proficient")}

    def is_unlocked(self, student_id, code: int) -> bool:
        L = self._learner(student_id)
        mastered = self._mastered_set(self._all_states(student_id))
        return self.graph.unlock_status(code, mastered, L.start_level, self.cfg.gate_fraction)[0]

    # ================================================================== progress (dashboard)
    def progress(self, student_id) -> dict:
        L = self._learner(student_id)
        states = self._all_states(student_id)
        mastered = self._mastered_set(states)
        topics = []
        counts = {"new": 0, "learning": 0, "weak": 0, "proficient": 0, "mastered": 0}
        for code, s in states.items():
            concept = self.graph.concepts[code]
            unlocked, detail = self.graph.unlock_status(code, mastered, L.start_level, self.cfg.gate_fraction)
            counts[s["status"]] += 1
            zh = {"title_zh": concept.title_zh} if self.cfg.include_chinese else {}
            topics.append({"concept_code": code, "name": concept.display_name, **zh,
                           "area_code": concept.area_code, "area_name": concept.area_name,
                           "group_code": concept.group_code, "stage": concept.stage,
                           "level": concept.level, "unlocked": unlocked, "unlock_detail": detail,
                           "n_exercises": len(concept.ucids), **s})
        topics.sort(key=lambda t: (t["level"], t["concept_code"]))
        return {"student_id": str(student_id), "answered": L.answered,
                "accuracy": (L.correct / L.answered) if L.answered else None,
                "status_counts": counts, "graph_source": self.graph.source, "topics": topics}

    # ================================================================== recommendation
    def _score(self, L: Learner, code: int, s: dict) -> float:
        cfg, concept = self.cfg, self.graph.concepts[code]
        if s["status"] == "weak":
            score = 3.0 + (cfg.weak_threshold - s["mastery"])
        elif s["status"] == "learning":
            score = 2.0 + min(0.9, max(0.0, cfg.mastery_threshold - s["mastery"]))
        elif s["status"] == "proficient":
            score = 0.5 + 0.3 * max(0.0, cfg.mastery_threshold - s["mastery"])
        else:  # new
            score = 1.0 + 0.2 * concept.base_rate + 0.05 * (1 - concept.level / max(1, self.graph.max_level))
        if L.answered < L.cooldown.get(code, 0):
            score -= cfg.streak_penalty
        return score

    def _reason(self, action: str, s: dict, concept, gate_detail: str, cold: bool, p_first: Optional[float]) -> str:
        cfg = self.cfg
        need = self.attempts_needed(concept.code)
        p_txt = f" (predicted success about {p_first:.0%})" if p_first is not None else ""
        if action == "revise":
            return (f"Your accuracy in this topic is {s['accuracy']:.0%} over {s['attempts']} attempts, below the "
                    f"{cfg.weak_threshold:.0%} level, so we revisit it with questions you are likely to get right{p_txt}.")
        if action == "practice":
            return (f"This topic is in progress ({s['attempts']} attempts, estimated mastery {s['mastery']:.0%}). "
                    f"It counts as mastered at {cfg.mastery_threshold:.0%} after at least {need} "
                    f"attempts, so keep practising{p_txt}.")
        if action == "advance":
            if cold:
                return (f"No answer history yet, so we start with a foundation topic ({gate_detail}) "
                        f"to learn where you stand{p_txt}.")
            return f"New topic unlocked: {gate_detail}. Starting with questions at a comfortable level{p_txt}."
        if s["status"] == "proficient":
            return (f"You completed this topic with {s['accuracy']:.0%} accuracy. A short review will help lock "
                    f"it in{p_txt}.")
        return (f"All other unlocked topics are done, so this is a spaced review of a topic with estimated "
                f"mastery {s['mastery']:.0%}{p_txt}.")

    def _predict(self, student_id, ucids: List[str]):
        """-> (list of probabilities, fallback_used)"""
        if self.predictor is not None:
            try:
                p = self.predictor.predict_many(str(student_id), ucids, None)
                return [float(x) for x in p], False
            except Exception:
                pass
        return [self.graph.exercises[u]["base_rate"] for u in ucids], True

    def _pick_exercises(self, student_id, L: Learner, code: int, target: float, k: int):
        concept = self.graph.concepts[code]
        recent = set(L.recent)
        unseen = [u for u in concept.ucids if L.ex_seen.get(u, 0) == 0]
        pool = list(unseen)
        if len(pool) < k:      # top up with least-practised exercises that were not answered recently
            seen_ok = sorted((u for u in concept.ucids if u not in pool and u not in recent),
                             key=lambda u: L.ex_seen.get(u, 0))
            pool += seen_ok[: k - len(pool)]
        if not pool:
            pool = list(concept.ucids)
        probs, fallback = self._predict(student_id, pool)
        ranked = sorted(zip(pool, probs), key=lambda t: (abs(t[1] - target), -self.graph.exercises[t[0]]["base_rate"], t[0]))
        out = [{"ucid": u, "label": self.graph.exercises[u].get("label_en"),
                **({"name_zh": self.graph.exercises[u].get("name_zh")} if self.cfg.include_chinese else {}),
                "difficulty": self.graph.exercises[u]["difficulty"],
                "predicted_p_correct": round(p, 4),
                "exercise_base_rate": round(self.graph.exercises[u]["base_rate"], 4),
                "seen_before": L.ex_seen.get(u, 0) > 0} for u, p in ranked[:k]]
        return out, fallback

    def generate_path(self, student_id, n_steps: int = 5, exercises_per_step: int = 3,
                      exercise_steps: int = 1) -> dict:
        """
        Ordered learning path. Exercises are computed for the first `exercise_steps` steps only
        (the later steps are previews that will be re-planned after the next answer).
        """
        L = self._learner(student_id)
        states = self._all_states(student_id)
        mastered = self._mastered_set(states)
        cold = L.answered == 0

        cands = []
        n_locked = 0
        for code, s in states.items():
            if s["status"] == "mastered" or s["stalled"]:
                continue
            unlocked, detail = self.graph.unlock_status(code, mastered, L.start_level, self.cfg.gate_fraction)
            if s["status"] == "new" and not unlocked:
                n_locked += 1
                continue
            cands.append((self._score(L, code, s), code, s, detail))
        cands.sort(key=lambda t: (-t[0], self.graph.concepts[t[1]].level, t[1]))

        chosen, revise_count = [], 0
        for item in cands:
            status = item[2]["status"]
            if status == "weak":
                if revise_count >= self.cfg.max_revise_steps:
                    continue
                revise_count += 1
            chosen.append(item)
            if len(chosen) == n_steps:
                break

        review_mode = False
        if not chosen:       # everything unlocked is mastered -> spaced review
            review_mode = True
            pool = sorted(((s["mastery"], code, s) for code, s in states.items()
                           if s["status"] == "mastered" or s["stalled"]))
            chosen = [(0.0, code, s, "mastered earlier") for _, code, s in pool[:n_steps]]

        steps = []
        for rank, (score, code, s, detail) in enumerate(chosen, start=1):
            concept = self.graph.concepts[code]
            action = {"weak": "revise", "learning": "practice", "new": "advance",
                      "proficient": "review"}.get(s["status"], "review")
            if review_mode:
                action = "review"
            target = {"revise": self.cfg.target_revise, "practice": self.cfg.target_practice,
                      "advance": self.cfg.target_new, "review": self.cfg.target_review}[action]
            exercises, fb = ([], False)
            if rank <= exercise_steps:
                exercises, fb = self._pick_exercises(student_id, L, code, target, exercises_per_step)
            p_first = exercises[0]["predicted_p_correct"] if exercises else None
            zh = {"title_zh": concept.title_zh} if self.cfg.include_chinese else {}
            step = {"rank": rank, "concept_code": code, "name": concept.display_name, **zh,
                    "area_code": concept.area_code, "area_name": concept.area_name,
                    "group_code": concept.group_code, "concept_label": concept.label, "stage": concept.stage, "level": concept.level,
                    "action": action, "status": s["status"], "mastery": s["mastery"],
                    "attempts": s["attempts"], "accuracy": s["accuracy"], "priority_score": round(score, 3),
                    "reason": self._reason(action, s, concept, detail, cold, p_first),
                    "exercises": exercises, "fallback_used": fb}
            if self.predictor is not None and exercises:
                try:
                    step["model_bkt_mastery"] = round(float(self.predictor.bkt_mastery(str(student_id), exercises[0]["ucid"])), 4)
                except Exception:
                    pass
            steps.append(step)

        notes = []
        for code, until in sorted(L.cooldown.items(), key=lambda kv: kv[1]):
            left = until - L.answered
            st = states[code]
            if left > 0 and st["status"] in ("weak", "learning"):
                notes.append(f"{self.graph.concepts[code].display_name} is resting after a long practice run; "
                             f"it will come back after about {left} more answers "
                             f"(current mastery {st['mastery']:.0%}).")
        return {"student_id": str(student_id), "answered": L.answered, "cold_start": cold,
                "graph_source": self.graph.source, "locked_topics": n_locked, "notes": notes, "steps": steps}

    def next_exercises(self, student_id, k: int = 3) -> List[dict]:
        """Flat list of the next k exercises (top step), each with topic, action and reason."""
        path = self.generate_path(student_id, n_steps=1, exercises_per_step=k, exercise_steps=1)
        if not path["steps"]:
            return []
        st = path["steps"][0]
        return [{**ex, "concept_code": st["concept_code"], "topic": st["name"],
                 "action": st["action"], "reason": st["reason"]} for ex in st["exercises"]]
