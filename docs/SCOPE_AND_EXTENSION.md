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
