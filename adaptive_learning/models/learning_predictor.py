"""
learning_predictor.py  --  Member 2 handoff module (inference + student-state tracking)

Predicts P(student answers the NEXT exercise correctly) and tracks BKT mastery.
The feature logic here is the online twin of the offline "strict" feature builder in
member2_final_pipeline.ipynb; the notebook verifies the two agree (parity test).

Typical use (Member 3):

    from learning_predictor import LearningPredictor
    lp = LearningPredictor.from_files("member2_final_model.joblib",
                                      "member2_model_card.json",
                                      "member2_exercise_lookup.csv")

    lp.observe("student_42", "ex_abc", is_correct=True, ts="2026-01-05 10:03:00")   # after every answer
    p  = lp.predict_proba("student_42", "ex_xyz", ts="2026-01-05 10:40:00")           # before answering
    ps = lp.predict_many("student_42", ["ex_1", "ex_2", "ex_3"])                      # candidate exercises
    m  = lp.bkt_mastery("student_42", "ex_xyz")                                       # concept mastery

Design rules (identical to training):
  * Only answers from STRICTLY EARLIER timestamp buckets are visible to a prediction.
    Answers observed inside the current bucket stay "pending" until time moves forward.
    Calling predict with ts=None means "time has moved on" and releases pending answers.
  * Unknown exercise / missing metadata never raises: category codes become NaN/"other"
    and the target-encoded difficulty falls back to the training prior.
  * A student with no history gets NaN history features (the model was trained with
    exactly this cold-start representation).
"""
from __future__ import annotations

import json
from collections import deque

import joblib
import numpy as np
import pandas as pd

__all__ = ["LearningPredictor"]

_NAN = float("nan")


class _StudentState:
    __slots__ = ("attempts", "correct", "last10", "last_y", "last_ts",
                 "pending", "pending_ts", "concept", "exercise", "mastery")

    def __init__(self):
        self.attempts = 0
        self.correct = 0
        self.last10 = deque(maxlen=10)
        self.last_y = None
        self.last_ts = None
        self.pending = []          # [(ucid, concept_key, y)] observed inside the current bucket
        self.pending_ts = None
        self.concept = {}          # concept_key -> [attempts, correct]   (committed only)
        self.exercise = {}         # ucid        -> [attempts, correct]   (committed only)
        self.mastery = {}          # concept_key -> BKT P(L) after committed answers


class LearningPredictor:
    def __init__(self, model, card: dict, lookup: pd.DataFrame):
        self.model = model
        self.card = card
        self.feature_names = list(card["features"])
        self.bucket = card.get("timestamp_bucket_seconds") or None
        self.prior = float(card["priors"]["encoding_prior"])
        self.concept_other = float(card["concept_other_code"])
        self.bkt = {k: float(v) for k, v in card["bkt_params"].items()}
        self.thresholds = {"default": 0.5,
                           "accuracy": float(card["threshold_accuracy"]),
                           "balanced": float(card["threshold_balanced"])}
        lk = lookup.copy()
        lk["ucid"] = lk["ucid"].astype(str)
        self._ex = {
            r[0]: (int(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[6]))
            for r in zip(lk["ucid"], lk["concept_code"], lk["concept_cat"], lk["difficulty_code"],
                         lk["stage_code"], lk["exercise_enc"], lk["concept_enc"])
        }
        self._students = {}

    # ------------------------------------------------------------------ loading
    @classmethod
    def from_files(cls, model_path, card_path, lookup_path):
        model = joblib.load(model_path)
        with open(card_path, "r", encoding="utf-8") as fh:
            card = json.load(fh)
        lookup = pd.read_csv(lookup_path, dtype={"ucid": str})
        return cls(model, card, lookup)

    # ------------------------------------------------------------------ helpers
    def _bucket_ts(self, ts):
        """-> epoch seconds floored to the training timestamp resolution, or None."""
        if ts is None:
            return None
        if isinstance(ts, (int, float, np.integer, np.floating)):
            t = pd.Timestamp(float(ts), unit="s", tz="UTC")
        else:
            t = pd.Timestamp(ts)
            t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
        sec = int(t.timestamp())
        if self.bucket:
            sec -= sec % int(self.bucket)
        return sec

    def _state(self, student_id):
        key = str(student_id)
        st = self._students.get(key)
        if st is None:
            st = self._students[key] = _StudentState()
        return st

    def _concept_key(self, ucid):
        ex = self._ex.get(str(ucid))
        return ex[0] if ex is not None else ("unk", str(ucid))

    def _bkt_step(self, m, y):
        pl0, pt, pg, ps = self.bkt["p_l0"], self.bkt["p_t"], self.bkt["p_g"], self.bkt["p_s"]
        if y:
            num = m * (1.0 - ps)
            den = num + (1.0 - m) * pg
        else:
            num = m * ps
            den = num + (1.0 - m) * (1.0 - pg)
        m = num / den
        return m + (1.0 - m) * pt

    def _commit(self, st):
        for ucid, ckey, y in st.pending:
            st.attempts += 1
            st.correct += y
            st.last10.append(y)
            st.last_y = y
            c = st.concept.setdefault(ckey, [0, 0]); c[0] += 1; c[1] += y
            e = st.exercise.setdefault(ucid, [0, 0]); e[0] += 1; e[1] += y
            st.mastery[ckey] = self._bkt_step(st.mastery.get(ckey, self.bkt["p_l0"]), y)
        if st.pending:
            st.last_ts = st.pending_ts
        st.pending = []
        st.pending_ts = None

    def _release(self, st, tsb):
        """Make answers from strictly earlier buckets visible."""
        if st.pending and (tsb is None or tsb > st.pending_ts):
            self._commit(st)

    # ------------------------------------------------------------------ public API
    def observe(self, student_id, ucid, is_correct, ts=None):
        """Record an answer. Timestamps must be non-decreasing per student."""
        st = self._state(student_id)
        tsb = self._bucket_ts(ts) if ts is not None else self._bucket_ts(pd.Timestamp.now("UTC"))
        if st.pending and tsb < st.pending_ts:
            raise ValueError("observe(): timestamps must be non-decreasing per student")
        if st.last_ts is not None and tsb < st.last_ts:
            raise ValueError("observe(): timestamp is older than already committed history")
        self._release(st, tsb)
        ucid = str(ucid)
        st.pending.append((ucid, self._concept_key(ucid), int(bool(is_correct))))
        st.pending_ts = tsb

    def load_history(self, student_id, rows):
        """rows: iterable of (ts, ucid, is_correct) in chronological order."""
        for ts, ucid, y in rows:
            self.observe(student_id, ucid, y, ts)

    def features(self, student_id, ucid, ts=None) -> dict:
        st = self._state(student_id)
        tsb = self._bucket_ts(ts)
        self._release(st, tsb)
        return self._row(st, str(ucid), tsb)

    def _row(self, st, ucid, tsb):
        ex = self._ex.get(ucid)
        if ex is None:
            ckey, ccat, dcode, scode, e_enc, c_enc = ("unk", ucid), self.concept_other, _NAN, _NAN, self.prior, self.prior
        else:
            ckey, ccat, dcode, scode, e_enc, c_enc = ex
        n = st.attempts
        c = st.concept.get(ckey, (0, 0))
        e = st.exercise.get(ucid, (0, 0))
        last10 = st.last10
        gap = _NAN
        if tsb is not None and st.last_ts is not None:
            gap = (tsb - st.last_ts) / 60.0
        return {
            "stu_attempts": float(n),
            "stu_acc": st.correct / n if n else _NAN,
            "prev_correct": float(st.last_y) if n else _NAN,
            "recent10_acc": (sum(last10) / len(last10)) if len(last10) else _NAN,
            "concept_attempts": float(c[0]),
            "concept_acc": c[1] / c[0] if c[0] else _NAN,
            "exercise_attempts": float(e[0]),
            "exercise_acc": e[1] / e[0] if e[0] else _NAN,
            "gap_minutes": gap,
            "exercise_enc": e_enc,
            "concept_enc": c_enc,
            "difficulty_code": dcode,
            "stage_code": scode,
            "concept_cat": ccat,
        }

    def _frame(self, rows):
        return pd.DataFrame(rows, columns=self.feature_names).astype("float32")

    def predict_proba(self, student_id, ucid, ts=None) -> float:
        return float(self.predict_many(student_id, [ucid], ts)[0])

    def predict_many(self, student_id, ucids, ts=None) -> np.ndarray:
        st = self._state(student_id)
        tsb = self._bucket_ts(ts)
        self._release(st, tsb)
        rows = [self._row(st, str(u), tsb) for u in ucids]
        if not rows:
            return np.empty(0)
        return self.model.predict_proba(self._frame(rows))[:, 1]

    def predict_label(self, student_id, ucid, ts=None, mode="balanced") -> int:
        """1 = predicted correct. mode: 'balanced' (default), 'accuracy' or 'default' (0.5)."""
        return int(self.predict_proba(student_id, ucid, ts) >= self.thresholds[mode])

    def rank_by_target(self, student_id, ucids, target=0.7, ts=None):
        """Sort candidates by closeness of predicted P(correct) to `target` (challenging-but-doable)."""
        ucids = list(ucids)
        p = self.predict_many(student_id, ucids, ts)
        order = np.argsort(np.abs(p - target), kind="stable")
        return [(ucids[i], float(p[i])) for i in order]

    def bkt_mastery(self, student_id, ucid) -> float:
        """Current BKT P(mastery) of the concept behind `ucid`, including answers still pending."""
        st = self._state(student_id)
        ckey = self._concept_key(ucid)
        m = st.mastery.get(ckey, self.bkt["p_l0"])
        for _, k, y in st.pending:
            if k == ckey:
                m = self._bkt_step(m, y)
        return float(m)

    def state_summary(self, student_id) -> dict:
        st = self._state(student_id)
        n = st.attempts + len(st.pending)
        c = st.correct + sum(y for _, _, y in st.pending)
        return {"answers": n, "accuracy": (c / n) if n else None, "concepts_seen": len(st.concept)}
