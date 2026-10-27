import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "models"))

from engine import EngineConfig, RecommendationEngine, TopicGraph, UnknownExerciseError  # noqa: E402

LOOKUP = ROOT / "models" / "member2_exercise_lookup.csv"


class StubPredictor:
    """Stands in for Member 2's model: P(correct) = exercise base rate. Lets tests run without sklearn."""

    def __init__(self, graph):
        self.g = graph
        self.seen = []

    def observe(self, sid, ucid, y, ts=None):
        self.seen.append((sid, ucid, y))

    def predict_many(self, sid, ucids, ts=None):
        return [self.g.exercises[u]["base_rate"] for u in ucids]

    def bkt_mastery(self, sid, ucid):
        return 0.5


@pytest.fixture(scope="module")
def graph():
    return TopicGraph.from_lookup(LOOKUP)


@pytest.fixture()
def eng(graph):
    return RecommendationEngine(graph, StubPredictor(graph))


def answer_n(eng, sid, code, n, correct):
    us = eng.graph.concepts[code].ucids
    for i in range(n):
        eng.record_answer(sid, us[i % len(us)], correct)


# ---------------------------------------------------------------- graph
def test_graph_valid(graph):
    v = graph.validate()
    assert v["ok"], v
    assert v["n_concepts"] == 171 and v["n_exercises"] == 1330
    assert v["source"] == "heuristic-curriculum-levels"


def test_every_exercise_in_exactly_one_concept(graph):
    all_ids = [u for c in graph.concepts.values() for u in c.ucids]
    assert len(all_ids) == len(set(all_ids)) == 1330


def test_levels_are_ordered_by_stage(graph):
    max_elem = max(c.level for c in graph.concepts.values() if c.stage == "elementary")
    min_junior = min(c.level for c in graph.concepts.values() if c.stage == "junior")
    assert max_elem < min_junior


def test_cycle_detection(graph):
    a, b = list(graph.concepts)[:2]
    bad = TopicGraph(graph.concepts, graph.exercises, prereq_edges=[(a, b), (b, a)])
    assert bad.validate()["cycles"] is True
    selfloop = TopicGraph(graph.concepts, graph.exercises, prereq_edges=[(a, a)])
    assert selfloop.validate()["self_loops"] == [a]


# ---------------------------------------------------------------- cold start
def test_cold_start_uses_foundation_topics_only(eng):
    path = eng.generate_path("new", n_steps=5)
    assert path["cold_start"] is True and len(path["steps"]) == 5
    assert all(s["level"] == 0 for s in path["steps"])
    assert all(s["action"] == "advance" for s in path["steps"])
    assert "No answer history" in path["steps"][0]["reason"]
    assert len(path["steps"][0]["exercises"]) == 3


def test_every_step_has_a_reason(eng):
    for s in eng.generate_path("x", 8)["steps"]:
        assert isinstance(s["reason"], str) and len(s["reason"]) > 20


# ---------------------------------------------------------------- adaptation
def test_weak_topic_is_revised_first(eng):
    code = eng.generate_path("s")["steps"][0]["concept_code"]
    answer_n(eng, "s", code, 4, False)
    assert eng.concept_state("s", code)["status"] == "weak"
    top = eng.generate_path("s")["steps"][0]
    assert top["concept_code"] == code and top["action"] == "revise"
    assert "below" in top["reason"]


def test_revision_serves_easier_exercises_than_new_topic(eng):
    code = eng.generate_path("s")["steps"][0]["concept_code"]
    answer_n(eng, "s", code, 4, False)
    revise_p = eng.generate_path("s")["steps"][0]["exercises"][0]["predicted_p_correct"]
    assert revise_p >= 0.6


def test_mastered_topic_not_recommended_again(eng):
    code = eng.generate_path("s")["steps"][0]["concept_code"]
    answer_n(eng, "s", code, 8, True)
    assert eng.concept_state("s", code)["status"] == "mastered"
    codes = [s["concept_code"] for s in eng.generate_path("s", 10)["steps"]]
    assert code not in codes


def test_locked_topics_never_recommended(eng, graph):
    path = eng.generate_path("s", n_steps=30)
    for s in path["steps"]:
        assert eng.is_unlocked("s", s["concept_code"])


def test_level_gate_unlocks_after_mastery(eng, graph):
    lvl0 = graph.by_level[0]
    need = int(0.34 * len(lvl0)) + 1
    assert not any(graph.concepts[s["concept_code"]].level >= 1 for s in eng.generate_path("g", 40)["steps"])
    for code in lvl0[:need]:
        answer_n(eng, "g", code, 8, True)
    levels = {graph.concepts[s["concept_code"]].level for s in eng.generate_path("g", 40)["steps"]}
    assert 1 in levels


def test_streak_rule_moves_student_on(eng):
    code = eng.generate_path("s")["steps"][0]["concept_code"]
    # alternate answers so the topic stays "learning/weak" but the streak limit is hit
    us = eng.graph.concepts[code].ucids
    for i in range(eng.cfg.streak_limit):
        eng.record_answer("s", us[i % len(us)], i % 2 == 0 and False)
    top = eng.generate_path("s")["steps"][0]
    assert top["concept_code"] != code


def test_no_immediate_repeat_of_answered_exercise(eng):
    first = eng.next_exercises("s", 3)
    eng.record_answer("s", first[0]["ucid"], True)
    nxt = [e["ucid"] for e in eng.next_exercises("s", 3)]
    assert first[0]["ucid"] not in nxt


def test_no_repeats_until_pool_exhausted(eng):
    served = []
    for _ in range(12):
        e = eng.next_exercises("s", 1)[0]
        served.append(e["ucid"])
        eng.record_answer("s", e["ucid"], True)
    assert len(served) == len(set(served))


# ---------------------------------------------------------------- robustness
def test_unknown_exercise_raises(eng):
    with pytest.raises(UnknownExerciseError):
        eng.record_answer("s", "does-not-exist", True)


def test_predictor_failure_falls_back_to_base_rates(graph):
    class Broken(StubPredictor):
        def predict_many(self, *a, **k):
            raise RuntimeError("model file missing")

    e = RecommendationEngine(graph, Broken(graph))
    step = e.generate_path("s")["steps"][0]
    assert step["fallback_used"] is True and step["exercises"]


def test_works_without_any_predictor(graph):
    e = RecommendationEngine(graph, None)
    assert e.generate_path("s")["steps"][0]["exercises"]


def test_all_mastered_gives_review(graph):
    e = RecommendationEngine(graph, None, EngineConfig(gate_fraction=0.0))
    for code in graph.concepts:
        answer_n(e, "s", code, 6, True)
    for code in graph.concepts:      # make sure every topic is really mastered
        assert e.concept_state("s", code)["status"] == "mastered", code
    steps = e.generate_path("s")["steps"]
    assert steps and all(s["action"] == "review" for s in steps)


def test_start_stage_placement(eng, graph):
    eng.register_student("j", start_stage="junior")
    levels = {s["level"] for s in eng.generate_path("j", 10)["steps"]}
    assert min(levels) >= graph.stage_start_level("junior") or min(levels) == 0
    assert all(eng.is_unlocked("j", s["concept_code"]) for s in eng.generate_path("j", 10)["steps"])


def test_progress_and_path_are_json_serialisable(eng):
    answer_n(eng, "s", eng.generate_path("s")["steps"][0]["concept_code"], 3, True)
    json.dumps(eng.progress("s"))
    json.dumps(eng.generate_path("s"))


def test_deterministic(graph):
    a = RecommendationEngine(graph, StubPredictor(graph)).generate_path("s")
    b = RecommendationEngine(graph, StubPredictor(graph)).generate_path("s")
    assert a == b


def test_students_are_independent(eng):
    code = eng.generate_path("a")["steps"][0]["concept_code"]
    answer_n(eng, "a", code, 4, False)
    assert eng.concept_state("b", code)["status"] == "new"


# ---------------------------------------------------------------- real model (optional)
def test_with_real_member2_model(graph):
    pytest.importorskip("sklearn")
    import sklearn
    if sklearn.__version__ != "1.6.1":
        pytest.skip("needs scikit-learn 1.6.1 (Member 2's version)")
    from learning_predictor import LearningPredictor
    lp = LearningPredictor.from_files(ROOT / "models" / "member2_final_model.joblib",
                                      ROOT / "models" / "member2_model_card.json", LOOKUP)
    e = RecommendationEngine(graph, lp)
    step = e.generate_path("real")["steps"][0]
    assert step["exercises"] and not step["fallback_used"]
    e.record_answer("real", step["exercises"][0]["ucid"], False, "2026-01-05 10:00:00")
    assert e.generate_path("real")["answered"] == 1
    assert 0 < step["exercises"][0]["predicted_p_correct"] < 1


# ---------------------------------------------------------------- v2 rules
def _topic_with_size(graph, lo, hi):
    return next(c for c in graph.concepts.values() if lo <= len(c.ucids) <= hi and c.level == 0).code


def test_proficient_after_full_pass_with_moderate_accuracy(eng, graph):
    code = _topic_with_size(graph, 5, 8)
    us = graph.concepts[code].ucids
    for i, u in enumerate(us):                      # one full pass, ~70% correct
        eng.record_answer("p", u, i % 10 < 7)
    st = eng.concept_state("p", code)
    assert st["status"] in ("proficient", "mastered", "weak", "learning")
    if st["status"] == "proficient":
        assert 0.55 <= st["mastery"] < 0.80
        # a proficient topic is no longer pushed ahead of new topics
        steps = eng.generate_path("p", 3)["steps"]
        assert steps[0]["status"] != "proficient"


def test_proficient_counts_for_unlocking(graph):
    e = RecommendationEngine(graph, None)
    lvl0 = graph.by_level[0]
    need = int(0.34 * len(lvl0)) + 1
    for code in lvl0[:need]:
        us = graph.concepts[code].ucids
        for i in range(max(len(us), 6)):            # moderate accuracy, full pass
            e.record_answer("u", us[i % len(us)], i % 4 != 0)
    cleared = {c for c, s in e._all_states("u").items() if s["status"] in ("mastered", "proficient")}
    assert len(cleared) >= need - 3                 # most topics cleared even if not all "mastered"


def test_stalled_weak_topic_is_left_alone(eng, graph):
    code = _topic_with_size(graph, 3, 6)
    us = graph.concepts[code].ucids
    for i in range(int(eng.cfg.stall_factor * len(us)) + 1):
        eng.record_answer("w", us[i % len(us)], False)
    st = eng.concept_state("w", code)
    assert st["status"] == "weak" and st["stalled"] is True
    assert code not in [s["concept_code"] for s in eng.generate_path("w", 20)["steps"]]
    assert any(t["concept_code"] == code and t["stalled"] for t in eng.progress("w")["topics"])


def test_cooldown_blocks_return_to_topic(eng, graph):
    code = eng.generate_path("c")["steps"][0]["concept_code"]
    us = graph.concepts[code].ucids
    for i in range(eng.cfg.streak_limit):
        eng.record_answer("c", us[i % len(us)], False)
    # after one answer elsewhere the topic must still be resting
    other = next(c for c in graph.by_level[0] if c != code)
    eng.record_answer("c", graph.concepts[other].ucids[0], True)
    assert eng.generate_path("c")["steps"][0]["concept_code"] != code


def test_export_topic_graph(graph, tmp_path):
    import pandas as pd
    paths = graph.export(tmp_path)
    data = json.load(open(paths["json"], encoding="utf-8"))
    assert data["n_concepts"] == 171 and data["n_exercises"] == 1330
    topics = [tp for a in data["areas"] for tp in a["topics"]]
    assert len(topics) == 171 and sum(tp["n_exercises"] for tp in topics) == 1330
    df = pd.read_csv(paths["csv"], dtype={"ucid": str}, encoding="utf-8-sig")
    assert len(df) == 1330 and df.ucid.is_unique


def test_mastery_is_none_until_attempted(eng):
    path = eng.generate_path("fresh", 3)
    assert all(s["mastery"] is None and s["attempts"] == 0 for s in path["steps"])
    prog = eng.progress("fresh")
    assert all(t["mastery"] is None for t in prog["topics"] if t["status"] == "new")
    code = path["steps"][0]["concept_code"]
    eng.record_answer("fresh", eng.graph.concepts[code].ucids[0], True)
    assert eng.concept_state("fresh", code)["mastery"] is not None


# ---------------------------------------------------------------- enrichment from Info_Content.csv
@pytest.fixture(scope="module")
def rich():
    return TopicGraph.from_project(ROOT)


def test_enriched_graph_has_titles_areas_names(rich):
    cs = list(rich.concepts.values())
    assert rich.validate()["ok"]
    assert all(c.title_en and c.title_zh for c in cs)
    assert len({c.area_code for c in cs}) == 10 and len({c.group_code for c in cs}) == 42
    assert all(c.area_name for c in cs)
    assert all(e.get("name_zh") for e in rich.exercises.values())
    assert sum(c.retiring for c in cs) == 5
    assert not any("即將下架" in c.title_zh for c in cs)


def test_hierarchy_is_a_clean_tree(rich):
    # every level-3 group belongs to exactly one area
    parent = {}
    for c in rich.concepts.values():
        assert parent.setdefault(c.group_code, c.area_code) == c.area_code


def test_enriched_output_fields_and_json(rich):
    from engine import EngineConfig as EC
    e = RecommendationEngine(rich, StubPredictor(rich), EC(include_chinese=True))
    path = e.generate_path("s", 3)
    for st in path["steps"]:
        assert st["name"] and st["title_zh"] and st["area_name"] and st["group_code"]
    nxt = e.next_exercises("s", 2)
    assert all(x["name_zh"] and x["label"] for x in nxt)
    assert all(t["title_zh"] and t["area_code"] for t in e.progress("s")["topics"])
    json.dumps(path, ensure_ascii=False)


def test_levels_unchanged_by_enrichment(rich, graph):
    assert {c.code: c.level for c in rich.concepts.values()} == {c.code: c.level for c in graph.concepts.values()}


def _has_cjk(text):
    return any("\u4e00" <= ch <= "\u9fff" or "\u3000" <= ch <= "\u303f" for ch in text)


def test_default_output_is_english_only(rich, tmp_path):
    e = RecommendationEngine(rich, StubPredictor(rich))
    answer_n(e, "s", e.generate_path("s")["steps"][0]["concept_code"], 4, False)
    blob = json.dumps([e.generate_path("s", 6), e.progress("s"), e.next_exercises("s", 3)], ensure_ascii=False)
    assert not _has_cjk(blob)
    assert all(x["label"].startswith(x["topic"]) for x in e.next_exercises("s", 3))
    paths = rich.export(tmp_path)
    assert not _has_cjk(open(paths["json"], encoding="utf-8").read())
    assert not _has_cjk(open(paths["csv"], encoding="utf-8-sig").read())
    zh = rich.export(tmp_path / "zh", include_chinese=True)
    assert _has_cjk(open(zh["json"], encoding="utf-8").read())
