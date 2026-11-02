# Scope: what this project is, and what it is not

## What it is
An adaptive **school-mathematics** practice system. The predictor (Member 2) and the topic structure (Member 3) are built from the
Junyi Academy mathematics dataset, so every number the app shows (mastery, chance of success, unlocked topics) is grounded in that data.

## Do
- Present it as a working prototype on Junyi mathematics, and say so in the report and demo.
- Show the adaptation: answer a few exercises wrong, then show that the topic becomes "weak" and returns for revision.
- Present the evaluation (`adaptive_learning/reports/`) as simulated learners, not real-student outcomes.
- Describe computer-science tracks as future work with the requirements below.

## Do not
- Do not label any CSE topic (DSA, ML, etc.) as personalised by this model. It has never seen CSE data, so its
  probabilities and mastery values for those topics would be invented.
- Do not make up CSE exercise IDs, questions or "predicted chance of success" values to fill the UI.
- Do not claim the system generalises across subjects. It is subject-specific because the model is.

## What adding a CSE track would actually need
1. **Content catalogue**: topics, prerequisites (e.g. arrays -> linked lists -> trees -> graphs) and exercises with stable IDs.
   The engine's `TopicGraph.from_lookup(...)` accepts prerequisite edges.
2. **Question content**: real questions and answer checking (the Junyi data has none), so correctness is measured, not self-reported.
3. **Interaction data**: needed to train a CSE predictor. Without it the engine is designed to fall back to base rates
   (`RecommendationEngine(graph, None)`), which gives a *rule-based* path rather than an ML one. If you build this, label it rule-based.
   (This fallback is documented in `MEMBER3_README.md` but has not been tested with a custom CSE graph.)
4. **Backend/frontend**: add the subject id to `SUPPORTED_SUBJECTS` (`backend/app/schemas/profile.py`) and set `available: true`
   in `frontend/src/config/subjects.js`. The UI already lists DSA and ML as "coming soon".


## Who the maths content is for
- **Source:** Junyi Academy (Taiwan), K-12 online maths practice. Exercises are tagged `elementary`, `junior` or `senior`.
- **Coverage in this repo:** 784 elementary exercises (95 topics), 543 junior exercises (74 topics), and only 3 senior exercises (2 topics).
- **Grades and ages (inferred):** the dataset does not state grades. Using Taiwan's 6-3-3 school system, elementary is about Grades 1-6
  (ages 6-12) and junior high is about Grades 7-9 (ages 12-15). Treat these as approximate and cite them that way.
- **Senior high is effectively not covered** (3 exercises), so the app offers two levels, not three.
- Topic areas: elementary = numbers and operations, geometry and measurement, tables and graphs, problem solving;
  junior = algebra and functions, geometry, numbers/ratios/radicals, statistics and probability.

## How practice works (rules shown to students)
The dataset has exercise IDs and labels but no question text or answers, so each step is: the app names a topic and difficulty,
the student finds a matching problem in their own material, solves it unaided, and reports right or wrong.
- Do: solve first, report honestly, mark "wrong" if unsure or helped, expect misses.
- Do not: tap "right" to move on, skip hard exercises, or read the chance-of-success figure as a grade.
Because correctness is self-reported, results depend on honest input. State this in the report.

## Known limitation: starting level
In `RecommendationEngine.generate_path`, ties are broken by lowest topic level, so every new student's first exercises come from the
level-0 foundation topic (e.g. "One-to-one correspondence counting") even if they placed at junior. Placement currently only
unlocks more topics (locked topics: elementary 139, junior 51, senior 0). Suggested fix for the engine owner: during cold start,
prefer candidates with `level >= start_level`, then rerun `tests/` and `run_evaluation.py`. Not applied here.

## Datasets for DSA / programming (checked online; verify licences and links before use)
No dataset is a ready-made DSA course, but real student-interaction data exists for programming practice:
- **CSEDM / CodeWorkout (2019):** about 246 college students, 50 intro-programming (CS1, Java) problems, over 65,000 submissions per semester,
  with code, pass scores and compiler messages. Real learners, but introductory programming, not data structures.
- **BePKT:** programming-knowledge-tracing dataset from an online judge, with problem text, knowledge-concept labels, code and events.
  Closest to algorithm topics. Download link is in the authors' paper (arXiv 2112.08273).
- **POJ, CodeNet (IBM), Codeforces Users Submissions (Kaggle, 2024):** large submission logs from algorithm judges. Problem tags such as
  dp or graphs can act as topics, but you must build the topic graph and prerequisites yourself, and problem statements may need separate sourcing.
Each needs a new topic graph, a retrained predictor and new frontend content. That is a project phase, not a quick swap.
If time is short, a hand-authored DSA prerequisite graph with the engine's rule-based fallback (no ML predictor) is the honest option.
Label it rule-based and do not present it as model-driven.
