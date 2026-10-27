import nbformat as nbf
nb = nbf.v4.new_notebook()
C = []
def md(t): C.append(nbf.v4.new_markdown_cell(t.strip()))
def code(t): C.append(nbf.v4.new_code_cell(t.strip()))

md("""# Member 3 — Adaptive Recommendation Engine
**AI-Based Adaptive Learning Path Recommendation System** · Junyi Academy · Mathematics

Member 1 ne data clean kiya, Member 2 ne model banaya (`HistGB-A`). Is notebook mein Member 3 ka kaam hai:
topic graph → mastery → personalised learning path → reasons → evaluation.

**Pehle ye karo:** Kaggle par `member3_adaptive_engine.zip` ko **Add Input → Upload** se attach karo (dataset ban jayega). Phir cells ko ek-ek karke run karo.""")

md("## Cell 1 — Project folder dhundho\nYe code zip ya folder ko dhundhta hai aur Python path mein add karta hai. Kuch calculate nahi karta, sirf setup.")
code('''import sys, zipfile
from pathlib import Path

def find_engine_folder():
    for root in [Path("/kaggle/input"), Path("/kaggle/working"), Path.cwd()]:
        if root.exists():
            for f in root.rglob("recommendation_engine.py"):
                return f.parent.parent
    return None

PROJECT = find_engine_folder()
if PROJECT is None:                      # sirf zip upload hui ho to extract karo
    work = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path.cwd()
    for root in [Path("/kaggle/input"), work, Path.cwd()]:
        if root.exists():
            for z in root.rglob("member3_adaptive_engine.zip"):
                zipfile.ZipFile(z).extractall(work)
    PROJECT = find_engine_folder()
if PROJECT is None:
    raise FileNotFoundError("member3_adaptive_engine.zip ko Add Input se attach karo.")

sys.path.insert(0, str(PROJECT)); sys.path.insert(0, str(PROJECT / "models"))
OUT = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path.cwd() / "outputs"
OUT.mkdir(exist_ok=True)
print("Project folder:", PROJECT)
print("Output folder :", OUT)
print("Member 2 files:", sorted(p.name for p in (PROJECT / "models").iterdir()))''')

md("## Cell 2 — scikit-learn version check\nMember 2 ka model **scikit-learn 1.6.1** par bana tha. Version alag hua to model load nahi hoga.")
code('''import sklearn
print("scikit-learn:", sklearn.__version__, "| python:", sys.version.split()[0])
if sklearn.__version__ == "1.6.1":
    print("OK: version Member 2 ke saath match karta hai.")
else:
    print("DHYAN: version alag hai. Neeche wali line run karo, phir Session restart karke Cell 1 se dobara chalao:")
    print("    !pip install -q scikit-learn==1.6.1")''')

md("## Cell 3 — Member 2 ka model load karo\n`LearningPredictor` student ki history se *agla answer sahi hone ki probability* deta hai. Yahan sirf check kar rahe hain ki load ho raha hai.")
code('''import pandas as pd
from learning_predictor import LearningPredictor

M = PROJECT / "models"
lp = LearningPredictor.from_files(M / "member2_final_model.joblib",
                                  M / "member2_model_card.json",
                                  M / "member2_exercise_lookup.csv")
lookup = pd.read_csv(M / "member2_exercise_lookup.csv", dtype={"ucid": str})
print("Exercises in lookup:", len(lookup), "| concepts:", lookup.concept_code.nunique())

sample = lookup.ucid.iloc[:5].tolist()
print("Naye student ke liye P(correct):", lp.predict_many("test_student", sample).round(3))''')

md("## Cell 4 — Topic graph banao aur validate karo\nLookup + `Info_Content.csv` se 171 topics, 1,330 exercises, 42 groups aur 10 areas ka graph banta hai (sab output English mein). **Dhyan:** `Info_Content.csv` mein prerequisite columns nahi hain (hum ne check kiya), isliye `level` ek *data-derived curriculum order* hai (heuristic).")
code('''from engine import TopicGraph, RecommendationEngine, EngineConfig

graph = TopicGraph.from_project(PROJECT)     # lookup + Info_Content + titles + areas
report = graph.validate()
for k in ["source", "n_concepts", "n_exercises", "n_levels", "ok", "cycles",
          "duplicate_exercises", "concepts_without_exercises"]:
    print(f"{k:<28}", report[k])

print()
for lv, codes in sorted(graph.by_level.items()):
    print(f"Level {lv}: {len(codes):>2} topics | stage = {graph.concepts[codes[0]].stage}")

print("\\nAreas (real level-2 hierarchy):")
areas = {}
for c in graph.concepts.values():
    areas.setdefault((c.area_code, c.area_name), []).append(c.code)
for (code, name), members in sorted(areas.items()):
    print(f"  Area {code:>2}: {name:<42} {len(members):>2} topics")
print("Groups (level-3):", len({c.group_code for c in graph.concepts.values()}))
print("Topics Junyi marks as retiring:", sum(c.retiring for c in graph.concepts.values()))''')

md("## Cell 5 — Topic graph export karo (Member 4 / 5 ke liye)\n`topic_graph.json` (topics + exercise IDs) aur `topic_map.csv` (har exercise ka topic/level) save hoti hain.")
code('''paths = graph.export(OUT / "topic_graph")
print(paths)
topic_map = pd.read_csv(paths["csv"], dtype={"ucid": str})
display(topic_map.head(5))
print("Rows:", len(topic_map), "| unique exercises:", topic_map.ucid.nunique())''')

md("## Cell 6 — Naye student (cold start) ka path\nStudent ki koi history nahi hai, isliye engine foundation topics se start karta hai aur har step ka reason deta hai.")
code('''engine = RecommendationEngine(graph, lp)

def show(path, n_ex=2):
    print(f"answered={path['answered']} | cold_start={path['cold_start']} | graph={path['graph_source']}")
    for note in path["notes"]:
        print("  NOTE:", note)
    for s in path["steps"]:
        print(f"{s['rank']}. {s['name']} | {s['area_name']}")
        print(f"   action={s['action']} status={s['status']} attempts={s['attempts']}")
        print("   reason:", s["reason"])
        for e in s["exercises"][:n_ex]:
            print(f"   {e['label']}  predicted P(correct)={e['predicted_p_correct']:.2f}")

show(engine.generate_path("new_student", n_steps=4, exercises_per_step=3))''')

md("## Cell 7 — Teen alag students (weak / improving / strong)\nSabne ek hi topic mein 5 questions kiye, bas results alag hain. Dekho engine ka decision kaise badalta hai.")
code('''patterns = {"student_A_weak":      [0, 0, 1, 0, 0],
            "student_B_improving": [0, 1, 0, 1, 1],
            "student_C_strong":    [1, 1, 1, 1, 1]}
first_topic = engine.generate_path("probe")["steps"][0]["concept_code"]
ucids = graph.concepts[first_topic].ucids

for sid, pattern in patterns.items():
    for i, y in enumerate(pattern):
        engine.record_answer(sid, ucids[i % len(ucids)], bool(y), f"2026-01-05 10:{i:02d}:00")
    st = engine.concept_state(sid, first_topic)
    top = engine.generate_path(sid, n_steps=2)["steps"][0]
    print(f"{sid:<22} first topic -> status={st['status']:<10} mastery={st['mastery']:.2f} | "
          f"next: {top['name']} ({top['action']})")
    print("    ", top["reason"][:120])''')

md("## Cell 8 — Feedback loop\nAnswer submit hone ke baad recommendation badalni chahiye. Ek naya student 3 galat answers deta hai; dekho path kaise update hota hai.")
code('''sid = "loop_student"
before = engine.generate_path(sid)["steps"][0]
print("BEFORE:", before["name"], "->", before["action"])

topic = before["concept_code"]
us = graph.concepts[topic].ucids
for i in range(3):
    engine.record_answer(sid, us[i], False, f"2026-01-06 09:0{i}:00")

after = engine.generate_path(sid)["steps"][0]
print("AFTER 3 wrong answers:", after["name"], "->", after["action"])
print("Reason:", after["reason"])
assert after["action"] == "revise" and after["concept_code"] == topic
print("\\nFeedback loop OK: kamzor topic ab revise ke liye aaya.")''')

md("## Cell 9 — Unit tests chalao\nProject ke 34 tests: graph validity, cold start, weak/mastered topics, locked topics, repeats, fallbacks, export.")
code('''import subprocess
r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--color=no", "-p", "no:cacheprovider", str(PROJECT / "tests")],
                   capture_output=True, text=True, cwd=str(PROJECT))
print(r.stdout[-1200:])
print(r.stderr[-500:])
assert r.returncode == 0, "Kuch tests fail hue — output upar dekho."''')

md("## Cell 10 — Evaluation: adaptive vs fixed sequence vs random\n40 simulated learners × 150 answers (~30 sec). **Ye simulation hai**, real students par proof nahi. Assumptions `engine/simulation.py` mein likhi hain.")
code('''from engine.simulation import run, summarize

def factory(policy):
    return RecommendationEngine(graph, lp if policy == "adaptive" else None)

results = run(graph, factory, n_learners=40, n_answers=150, seed=7)
summ = summarize(results)

names = {"adaptive": "Adaptive", "fixed_sequence": "Fixed sequence", "random": "Random"}
table = pd.DataFrame({names[p]: summ["means"][p] for p in names}).round(3)
display(table)

key = ["total_theta_gain", "topics_newly_learned", "too_easy_rate(p>0.9)", "frustrating_rate(p<0.4)", "repeat_rate"]
print("Adaptive minus Fixed (mean, 95% CI):")
for k in key:
    m, lo, hi = summ["paired_differences"][f"adaptive - fixed_sequence | {k}"]
    print(f"  {k:<26} {m:+.3f}  [{lo:+.3f}, {hi:+.3f}]")''')

md("## Cell 11 — Outputs save karo aur handoff zip banao\n`member3_handoff.zip` Member 5 (backend) aur Member 4 (frontend) ko do.")
code('''import json, shutil
table.to_csv(OUT / "member3_evaluation_table.csv")
json.dump({"means": summ["means"], "paired_differences": summ["paired_differences"]},
          open(OUT / "member3_evaluation_results.json", "w"), indent=2)

examples = {sid: engine.generate_path(sid, n_steps=4, exercises_per_step=3)
            for sid in ["new_student", "student_A_weak", "student_B_improving", "student_C_strong"]}
json.dump(examples, open(OUT / "member3_example_outputs.json", "w"), indent=2)

pack = OUT / "member3_handoff"
if pack.exists(): shutil.rmtree(pack)
pack.mkdir()
for name in ["topic_graph/topic_graph.json", "topic_graph/topic_map.csv", "member3_evaluation_table.csv",
             "member3_evaluation_results.json", "member3_example_outputs.json"]:
    shutil.copy(OUT / name, pack / Path(name).name)
shutil.copytree(PROJECT / "engine", pack / "engine", ignore=shutil.ignore_patterns("__pycache__"))
shutil.copy(PROJECT / "docs" / "MEMBER3_README.md", pack / "MEMBER3_README.md")
shutil.copy(PROJECT / "requirements.txt", pack / "requirements.txt")
shutil.make_archive(str(OUT / "member3_handoff"), "zip", pack)
print("Created:", OUT / "member3_handoff.zip")
print(sorted(p.name for p in pack.iterdir()))''')

md("""## Cell 12 — Final checklist
- [ ] Cell 2: scikit-learn `1.6.1`
- [ ] Cell 4: `ok = True`, 171 concepts, 1,330 exercises, 10 areas, 42 groups
- [ ] Cell 8: feedback loop OK
- [ ] Cell 9: tests passed
- [ ] Cell 11: `member3_handoff.zip` bana
- [ ] **Save Version → Save & Run All** (taaki outputs Kaggle par save ho jayein)

Limitations (report mein likhna): `Info_Content.csv` mein prerequisites nahi hain (heuristic levels), evaluation simulated learners par hai, English titles translated hain (verify karo), aur question text dataset mein nahi hai.""")

nb["cells"] = C
nb["metadata"] = {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}}
nbf.write(nb, "Member3_Adaptive_Recommendation_Engine.ipynb")
print("cells:", len(C))
