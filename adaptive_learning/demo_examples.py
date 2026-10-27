"""Run: python demo_examples.py -> reports/example_outputs.json (weak / improving / strong learner, real Member 2 model)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "models"))
from engine import TopicGraph, RecommendationEngine
from learning_predictor import LearningPredictor

M = ROOT / "models"
graph = TopicGraph.from_project(ROOT)
lp = LearningPredictor.from_files(M / "member2_final_model.joblib", M / "member2_model_card.json", M / "member2_exercise_lookup.csv")
eng = RecommendationEngine(graph, lp)

# explicit answer patterns for the first topic (1 = correct)
profiles = {"student_A_weak": [0, 0, 1, 0, 0],            # 20% correct
            "student_B_improving": [0, 1, 0, 1, 1],       # 60% and rising
            "student_C_strong": [1, 1, 1, 1, 1]}          # 100%
out = {}
for sid, pattern in profiles.items():
    topic = eng.generate_path(sid)["steps"][0]["concept_code"]        # same first topic for everyone
    us = graph.concepts[topic].ucids
    for i, y in enumerate(pattern):
        eng.record_answer(sid, us[i % len(us)], bool(y), f"2026-01-05 10:{i:02d}:00")
    out[sid] = {"answers": pattern, "topic_state": eng.concept_state(sid, topic),
                "path": eng.generate_path(sid, n_steps=4, exercises_per_step=3)}
json.dump(out, open(ROOT / "reports/example_outputs.json", "w"), indent=2)
for sid, o in out.items():
    st = o["topic_state"]
    print(f"\n{sid}: first-topic status={st['status']} mastery={st['mastery']} accuracy={st['accuracy']}")
    for s in o["path"]["steps"]:
        print(f"  {s['rank']}. {s['name'][:34]:<34} {s['action']:<8} p~{s['exercises'][0]['predicted_p_correct'] if s['exercises'] else '-'}  | {s['reason'][:95]}")
