"""Run: python run_evaluation.py   -> writes reports/evaluation_results.json and reports/evaluation_summary.md"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "models"))
from engine import TopicGraph, RecommendationEngine
from engine.simulation import run, summarize
from learning_predictor import LearningPredictor

M = ROOT / "models"
graph = TopicGraph.from_lookup(M / "member2_exercise_lookup.csv")
lp = LearningPredictor.from_files(M / "member2_final_model.joblib", M / "member2_model_card.json", M / "member2_exercise_lookup.csv")

def factory(policy):
    # only the adaptive policy uses the model; the others use the engine just to track state
    return RecommendationEngine(graph, lp if policy == "adaptive" else None)

N_LEARNERS = int(sys.argv[1]) if len(sys.argv) > 1 else 40
N_ANSWERS = int(sys.argv[2]) if len(sys.argv) > 2 else 150
t = time.time()
res = run(graph, factory, N_LEARNERS, N_ANSWERS, seed=7)
summ = summarize(res)
(ROOT / "reports").mkdir(exist_ok=True)
json.dump({"n_learners": N_LEARNERS, "n_answers": N_ANSWERS, **summ}, open(ROOT / "reports/evaluation_results.json", "w"), indent=2)

names = {"adaptive": "Adaptive engine", "fixed_sequence": "Fixed topic sequence", "random": "Random practice"}
keys = list(summ["means"]["adaptive"])
lines = [f"# Simulated-learner evaluation ({N_LEARNERS} learners x {N_ANSWERS} answers)\n",
         "Same simulated learners for every policy. See `engine/simulation.py` for the assumptions "
         "(simulation, not real students).\n", "| metric | " + " | ".join(names.values()) + " |", "|---|---|---|---|"]
for k in keys:
    lines.append(f"| {k} | " + " | ".join(f"{summ['means'][p][k]:.3f}" for p in names) + " |")
lines += ["\n## Paired differences, adaptive minus baseline (mean, 95% bootstrap CI over learners)\n",
          "| comparison | metric | mean diff | 95% CI |", "|---|---|---|---|"]
for k, (m, lo, hi) in summ["paired_differences"].items():
    comp, metric = k.split(" | ")
    lines.append(f"| {comp} | {metric} | {m:+.3f} | [{lo:+.3f}, {hi:+.3f}] |")
open(ROOT / "reports/evaluation_summary.md", "w").write("\n".join(lines))
print("\n".join(lines)); print(f"\nruntime {time.time()-t:.0f}s")
