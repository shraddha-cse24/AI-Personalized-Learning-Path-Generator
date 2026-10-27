"""
simulation.py -- Member 3: compare the adaptive engine with a fixed topic sequence and random practice.

SIMULATION ASSUMPTIONS (these are assumptions, not findings about real students)
--------------------------------------------------------------------------------
A1. Every simulated learner has a hidden ability per topic:  theta_c = mu_student + noise,
    mu_student ~ N(0, 0.8),  noise ~ N(0, 0.6).
A2. True P(correct) on exercise e in topic c  =  sigmoid(theta_c + logit(base_rate_e)).
    (theta = 0 reproduces the historical correct rate of that exercise.)
A3. Learning: after each attempt theta_c += 0.10 * 4p(1-p), p = true P(correct).
    Learning is largest when the exercise is neither too easy nor too hard (p near 0.5).
A4. A topic is "truly learned" when sigmoid(theta_c + logit(topic base rate)) >= 0.85.
A5. The simulator does NOT assume prerequisites help learning, so it cannot reward the
    heuristic unlock gate. It only measures practice quality and structure.
The simulator is independent of Member 2's model, but it is still a simplified world:
treat the results as a sanity check of the policy, not as evidence of real learning gains.
"""
from __future__ import annotations

import math
import random
from typing import Callable, Dict, List

import numpy as np

from .recommendation_engine import RecommendationEngine
from .topic_graph import TopicGraph


def _sig(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


class SimLearner:
    def __init__(self, graph: TopicGraph, rng: random.Random):
        mu = rng.gauss(0, 0.8)
        self.theta0 = {c: mu + rng.gauss(0, 0.6) for c in graph.concepts}
        self.theta = dict(self.theta0)

    def p_correct(self, graph, ucid) -> float:
        e = graph.exercises[ucid]
        return _sig(self.theta[e["concept"]] + _logit(e["base_rate"]))

    def attempt(self, graph, ucid, rng) -> bool:
        p = self.p_correct(graph, ucid)
        e = graph.exercises[ucid]
        self.theta[e["concept"]] = min(3.0, self.theta[e["concept"]] + 0.10 * 4 * p * (1 - p))
        return rng.random() < p

    def learned(self, graph, code) -> bool:
        return _sig(self.theta[code] + _logit(graph.concepts[code].base_rate)) >= 0.85


# ----------------------------------------------------------------------------- policies
def fixed_sequence_policy(graph: TopicGraph) -> Callable:
    order = [u for c in sorted(graph.concepts.values(), key=lambda c: (c.level, c.code)) for u in c.ucids]

    def make():
        it = iter(order)
        return lambda sid, eng, rng: next(it)
    return make


def random_policy(graph: TopicGraph) -> Callable:
    all_ids = list(graph.exercises)

    def make():
        return lambda sid, eng, rng: rng.choice(all_ids)
    return make


def adaptive_policy(graph: TopicGraph) -> Callable:
    def make():
        return lambda sid, eng, rng: eng.next_exercises(sid, 1)[0]["ucid"]
    return make


def run(graph: TopicGraph, engine_factory, n_learners: int = 40, n_answers: int = 150, seed: int = 7):
    """engine_factory(policy_name) -> RecommendationEngine. Returns {policy: [per-learner metric dicts]}."""
    policies = {"adaptive": adaptive_policy(graph), "fixed_sequence": fixed_sequence_policy(graph),
                "random": random_policy(graph)}
    results: Dict[str, List[dict]] = {k: [] for k in policies}
    for name, make_policy in policies.items():
        eng: RecommendationEngine = engine_factory(name)
        for i in range(n_learners):
            rng = random.Random(seed * 1000 + i)            # same learner for every policy
            learner = SimLearner(graph, random.Random(seed * 1000 + i))
            sid = f"sim{i}"
            pick = make_policy()
            served, repeats, viol, frus, bored, ncorrect = set(), 0, 0, 0, 0, 0
            touched = set()
            for t in range(n_answers):
                ucid = pick(sid, eng, rng)
                code = graph.concept_of(ucid)
                if not eng.is_unlocked(sid, code):
                    viol += 1
                p = learner.p_correct(graph, ucid)
                frus += p < 0.40
                bored += p > 0.90
                repeats += ucid in served
                served.add(ucid)
                touched.add(code)
                y = learner.attempt(graph, ucid, rng)
                ncorrect += int(y)
                eng.record_answer(sid, ucid, y, f"2026-01-05 10:{t // 60 % 60:02d}:{t % 60:02d}")
            gains = [learner.theta[c] - learner.theta0[c] for c in touched]
            newly = sum(1 for c in graph.concepts if learner.learned(graph, c) and not
                        _sig(learner.theta0[c] + _logit(graph.concepts[c].base_rate)) >= 0.85)
            weak0 = [c for c in graph.concepts
                     if _sig(learner.theta0[c] + _logit(graph.concepts[c].base_rate)) < 0.60]
            results[name].append({
                "mean_theta_gain_touched": float(np.mean(gains)) if gains else 0.0,
                "total_theta_gain": float(sum(learner.theta[c] - learner.theta0[c] for c in graph.concepts)),
                "topics_newly_learned": newly,
                "weak_topics_start": len(weak0),
                "weak_topics_improved": sum(1 for c in weak0 if learner.theta[c] - learner.theta0[c] > 0.3),
                "distinct_topics": len(touched),
                "repeat_rate": repeats / n_answers,
                "gate_violation_rate": viol / n_answers,
                "frustrating_rate(p<0.4)": frus / n_answers,
                "too_easy_rate(p>0.9)": bored / n_answers,
                "observed_correct_rate": ncorrect / n_answers,
            })
    return results


def summarize(results, metric_keys=None, n_boot: int = 2000, seed: int = 1) -> dict:
    keys = metric_keys or list(results["adaptive"][0])
    rng = np.random.default_rng(seed)
    out = {}
    for pol, rows in results.items():
        out[pol] = {k: float(np.mean([r[k] for r in rows])) for k in keys}
    diffs = {}
    n = len(results["adaptive"])
    for other in ("fixed_sequence", "random"):
        for k in keys:
            d = np.array([a[k] - b[k] for a, b in zip(results["adaptive"], results[other])])
            boots = [d[rng.integers(0, n, n)].mean() for _ in range(n_boot)]
            diffs[f"adaptive - {other} | {k}"] = (float(d.mean()), float(np.percentile(boots, 2.5)),
                                                  float(np.percentile(boots, 97.5)))
    return {"means": out, "paired_differences": diffs}
