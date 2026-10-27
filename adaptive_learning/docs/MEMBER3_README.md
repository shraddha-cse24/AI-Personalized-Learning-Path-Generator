# Member 3: Adaptive Recommendation Engine

Turns Member 2's answer-probability model into a personalised, explainable learning path.

- Code: `engine/` | Tests: `tests/` (34) | Evaluation: `run_evaluation.py` | Examples: `demo_examples.py`
- Dataset: Junyi Academy Learning Activity Public Dataset (mathematics). See the dataset page on Kaggle for its licence terms.
- Member 2's files in `models/` are copied here unchanged, because the engine needs them.

## 0. What is in this folder

```
adaptive_learning/
  engine/        topic_graph.py, recommendation_engine.py, simulation.py   (the Member 3 code)
  models/        Member 2's model, exercise lookup, model card and learning_predictor.py
  data/          Info_Content.csv, topic_titles.csv, area_names.json       (names and hierarchy)
  tests/         test_engine.py (34 unit tests)
  results/       evaluation table, evaluation results and example outputs from my Kaggle run
  reports/       evaluation_summary.md, evaluation_results.json, example_outputs.json (made by the scripts below)
  docs/          MEMBER3_README.md (this file), member2_final_report.md
  Member3_Adaptive_Recommendation_Engine.ipynb   Kaggle notebook, cell by cell
  build_topic_titles.py   regenerates data/topic_titles.csv and data/area_names.json
  build_notebook.py       regenerates the notebook
  demo_examples.py        writes reports/example_outputs.json
  run_evaluation.py       writes reports/evaluation_summary.md
  requirements.txt
```

**Topic graph files for Members 4 and 5.** `topic_graph.json` (areas, topics, exercises) and `topic_map.csv`
(one row per exercise) are not stored in the repo. Create them from this folder with:

```bash
python -c "import sys; sys.path.insert(0,'.'); from engine import TopicGraph; TopicGraph.from_project('.').export('exports')"
```

This writes both files into a new `exports/` folder. They are also in `member3_handoff.zip` (shared by Drive).

**Running the notebook on Kaggle.** Cell 1 looks for this project folder. Upload the `adaptive_learning` folder
(or a zip named `member3_adaptive_engine.zip`) to Kaggle with Add Input, then run the cells in order.

## 1. Setup

Run everything from inside the `adaptive_learning` folder:

```bash
cd adaptive_learning
python -m venv venv
venv\Scripts\activate                             # Windows. Mac/Linux: source venv/bin/activate
pip install -r requirements.txt                   # scikit-learn MUST be 1.6.1
python -m pytest -q tests                         # expect: 34 passed
python demo_examples.py                           # writes reports/example_outputs.json
python run_evaluation.py 40 150                   # writes reports/evaluation_summary.md (about 30 seconds)
```

scikit-learn must be exactly 1.6.1, the version Member 2 trained with. Other versions fail to load the model.

## 2. Using the engine (this is what Member 5's backend calls)

```python
import sys; sys.path.insert(0, "models")
from engine import TopicGraph, RecommendationEngine, EngineConfig, UnknownExerciseError
from learning_predictor import LearningPredictor

graph = TopicGraph.from_project(".")        # lookup + Info_Content.csv + titles + areas
lp    = LearningPredictor.from_files("models/member2_final_model.joblib",
                                     "models/member2_model_card.json",
                                     "models/member2_exercise_lookup.csv")
engine = RecommendationEngine(graph, lp)          # lp may be None -> falls back to base rates

engine.register_student("stu1", start_stage="elementary")           # optional placement
engine.record_answer("stu1", ucid, is_correct=True, ts=None)        # call after EVERY answer
path = engine.generate_path("stu1", n_steps=5, exercises_per_step=3)    # roadmap + next exercises
nxt  = engine.next_exercises("stu1", k=3)                               # flat list for the quiz page
prog = engine.progress("stu1")                                          # dashboard data
engine.load_history("stu1", rows)                 # rows = [(ts, ucid, is_correct), ...] oldest first
```

**Important for Member 5:**
- Engine state lives in memory. After a server restart, rebuild every active student with
  `load_history(...)` from the database, in chronological order.
- `record_answer` raises `UnknownExerciseError` for an unknown `ucid`. Return HTTP 404.
- Run from the `adaptive_learning` folder, or add it to `sys.path`, so `import engine` works.

## 3. Output contract

`generate_path()` returns the structure below. The `//` comments are only explanations and are not part of the real JSON.

```json
{
  "student_id": "stu1", "answered": 5, "cold_start": false,
  "graph_source": "heuristic-curriculum-levels",
  "locked_topics": 139,
  "notes": ["Elementary topic 2 is resting ... will come back after about 7 more answers (current mastery 40%)."],
  "steps": [
    {
      "rank": 1, "concept_code": 2, "name": "One-to-one correspondence counting",   // English title
      "area_code": 1, "area_name": "Numbers and operations (elementary)",
      "group_code": 3, "concept_label": "L4:...",
      "stage": "elementary", "level": 0,
      "action": "revise",                 // revise | practice | advance | review
      "status": "weak",                   // new | learning | weak | proficient | mastered
      "mastery": 0.4027,                  // null until the student has attempted the topic
      "attempts": 5, "accuracy": 0.2, "priority_score": 3.15,
      "reason": "Your accuracy in this topic is 20% over 5 attempts, below the 55% level, ...",
      "exercises": [
        {"ucid": "...", "label": "One-to-one correspondence counting - exercise 1 of 3 (easy)",
         "difficulty": "easy", "predicted_p_correct": 0.8033,
         "exercise_base_rate": 0.81, "seen_before": false}
      ],
      "fallback_used": false, "model_bkt_mastery": 0.77
    }
  ]
}
```

- `mastery` is `null` for topics with 0 attempts (`prior_mastery` in `progress()` holds the historical prior). Show "not started" in the UI.
- Only the first step has `exercises` filled. Later steps are previews and are re-planned after each answer.
- `progress()` returns per-topic `{concept_code, name, area_code, area_name, group_code, stage, level, unlocked, unlock_detail,
  attempts, correct, accuracy, mastery, prior_mastery, status, stalled, n_exercises}` plus `status_counts`, ready for the dashboard.
- Suggested API mapping: `POST /attempts` -> `record_answer`; `GET /students/{id}/path` -> `generate_path`;
  `GET /exercises/next` -> `next_exercises`; `GET /students/{id}/mastery` -> `progress`.
- Use `concept_code` as the unique topic ID. A few English topic titles repeat.
- **All output is English by default.** Topic titles and the 10 area names were translated by Claude from the dataset's
  Traditional Chinese names, so have a Chinese speaker spot-check them before the final demo. Exercises carry an English
  `label` such as "Speed - exercise 2 of 5 (easy)", because the dataset has no English exercise names.
  To also get the Chinese originals (`title_zh`, `name_zh`), use `EngineConfig(include_chinese=True)` and
  `graph.export(dir, include_chinese=True)`.
- The roadmap can be grouped by `area_name` (10 areas) and `group_code` (42 groups). Both come from the real dataset hierarchy.

## 4. How it decides (explainable rules)

1. **Mastery per topic** = `(correct + 2 * base_rate) / (attempts + 2)`, where `base_rate` is the topic's historical correct rate.
2. **Status**: `new` (no attempts); `mastered` (at least min(5, topic size) attempts and mastery >= 0.80);
   `weak` (at least 3 attempts and mastery < 0.55); `proficient` (one full pass of the topic at 0.55 to 0.80);
   otherwise `learning`.
3. **Unlocking**: a level-L topic unlocks when at least 34% of the level L-1 topics are mastered or proficient.
4. **Priority**: revise weak > continue learning > start newly unlocked > review proficient.
   Mastered topics are not repeated. At most 2 revision steps per path.
5. **Fatigue and spacing**: after 6 answers in a row in one topic, it rests for 12 answers.
   A weak topic drilled 2x its pool size without recovering is marked `stalled` and left alone.
6. **Exercise choice** inside the topic: the exercise whose `predicted_p_correct` (Member 2's model) is closest to a target
   (0.80 revise, 0.70 practice, 0.75 new topic, 0.85 review). Unseen exercises come first; the last 10 answered are excluded.
7. **Fallbacks**: no history -> foundation topics; predictor missing or failing -> exercise base rates
   (`fallback_used: true`); everything done -> spaced review.

## 5. Results (read the limits before quoting numbers)

**Graph check** (`TopicGraph.validate()`): 171 topics, 1,330 exercises, no duplicate exercises and no empty topics.
The cycle check only applies if you supply prerequisite edges. The default graph has none.

**Simulated learners** (40 learners x 150 answers; the same learners for every policy; assumptions A1 to A5 are written in
`engine/simulation.py`). Source: `reports/evaluation_summary.md`; your own run is in `results/member3_evaluation_table.csv`.
Adaptive vs fixed topic sequence, mean difference with a 95% bootstrap confidence interval over learners:

| metric | adaptive | fixed | difference (95% CI) |
|---|---|---|---|
| total ability gain (all topics) | 8.91 | 8.17 | +0.74 (+0.57, +0.90) |
| topics newly learned | 4.55 | 4.55 | 0.00 (-0.55, +0.55) |
| weak topics improved | 2.08 | 1.83 | +0.25 (-0.03, +0.50) |
| too-easy questions (p > 0.9) | 22.0% | 26.3% | -4.3 pts (-6.3, -2.4) |
| too-hard questions (p < 0.4) | 1.5% | 2.0% | -0.6 pts (-2.9, +0.8) |
| repeated exercises | 2.7% | 0% | +2.7 pts (+1.4, +4.3) |
| answers in locked topics | 0% | 0% | 0 |
| mean gain per touched topic | 0.36 | 0.41 | -0.05 (-0.06, -0.04) |

Versus **random practice**: far fewer too-hard questions (-12.1 pts), more topics newly learned (+2.7), and 0% vs 80%
of answers in locked topics. Random practice has a higher total gain, because it keeps hitting mid-difficulty exercises.

**Honest reading:** in this simulation the adaptive engine is clearly better than random practice and about equal to a
well-ordered fixed sequence on topics learned. Its measurable advantages are fewer too-easy questions, a small gain in
total ability, revision of weak topics, no answers in locked topics, and an explanation for every step.
It does NOT prove that real students learn faster. That needs a real user study.

## 6. Limitations (put these in the report)

1. **No verified prerequisites.** We checked `Info_Content.csv`: its columns are ucid, content_pretty_name,
   content_kind, difficulty, subject, learning_stage and level1_id to level4_id. There is no prerequisite column,
   only a 4-level hierarchy (1 subject, 10 areas, 42 groups, 171 topics). The unlock rule is therefore a
   data-derived curriculum order (stage, then historical difficulty). If a teacher provides real prerequisite pairs,
   pass `prereq_edges=` to `TopicGraph.from_lookup` and it replaces the heuristic.
2. **Names exist, question text does not.** Exercises have names in Traditional Chinese but no question statements or answers,
   so the quiz page needs its own question content mapped to `ucid`s. English titles are machine-translated.
   5 topics are marked "being retired" by Junyi (`retiring` flag); the engine does not skip them.
3. **Strong students are held back.** A level only opens after about 11 foundation topics are cleared.
   Mitigation: `register_student(start_stage=...)` placement, or a lower `gate_fraction` in `EngineConfig`.
4. **Small question pools.** The average topic has 7.8 exercises (30 topics have fewer than 5), so some repetition is unavoidable.
5. **Member 2's model** has ROC-AUC 0.742 and drops answers from the same 15-minute window from its features.
   The engine calls it with `ts=None` (all answers visible), which differs slightly from training.
   Its BKT uses one global parameter set (p_L0 = 0.77, p_T = 0.001), so `model_bkt_mastery` is informational only;
   the engine's own smoothed accuracy drives decisions.
6. **Thresholds** (0.80, 0.55, 5 attempts, 34%) are design choices, not fitted values.
7. Simulation results depend on assumptions A1 to A5. There is no real-student validation.
