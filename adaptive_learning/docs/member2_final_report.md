# Member 2 — Final Report: Student Performance Prediction and Knowledge Tracing

Generated 2026-10-23 18:39 UTC by `member2_final_pipeline.ipynb` · data source: **junyi-real** · seed 42

## 1. Headline result
Selected model: **HistGB-A (63 leaves, lr 0.10)** (lowest validation log-loss among strict learned models).
On the untouched **test period** it reaches **74.16% accuracy** against **70.71%** for the majority baseline on the same 2,432,333 rows
(**+3.44 percentage points**; student-bootstrap 95 % CI +3.19 to +3.72 pp),
ROC-AUC **0.7421**, PR-AUC 0.8658, log-loss **0.5244** (base-rate predictor: 0.6047), ECE 0.0045.
ROC-AUC is the primary ranking metric and log-loss the primary probability-quality metric, because accuracy depends heavily on the class balance of the period.

| model | accuracy | majority_accuracy_same_rows | accuracy_gain_vs_majority_pp | roc_auc | pr_auc | log_loss | ece |
|---|---|---|---|---|---|---|---|
| Majority / base-rate | 0.7071 | 0.7071 | 0.0000 | 0.5000 | 0.7071 | 0.6047 | 0.0010 |
| Student past-accuracy heuristic | 0.7218 | 0.7071 | 1.4679 | 0.6755 | 0.8151 | 0.6226 | 0.0227 |
| Logistic Regression | 0.7389 | 0.7071 | 3.1744 | 0.7336 | 0.8592 | 0.5312 | 0.0064 |
| HistGB-A (63 leaves, lr 0.10) | 0.7416 | 0.7071 | 3.4440 | 0.7421 | 0.8658 | 0.5244 | 0.0045 |
| HistGB-B (127 leaves, lr 0.06, L2) | 0.7413 | 0.7071 | 3.4217 | 0.7421 | 0.8658 | 0.5244 | 0.0046 |
| HistGB-A LOOSE (sensitivity only) | 0.7509 | 0.7071 | 4.3730 | 0.7597 | 0.8754 | 0.5113 | 0.0020 |
| BKT (fixed guessed params) | 0.6185 | 0.7071 | -8.8661 | 0.5911 | 0.7669 | 0.7200 | 0.1929 |
| BKT (fitted on train) | 0.7219 | 0.7071 | 1.4803 | 0.6588 | 0.8012 | 0.5700 | 0.0289 |

*(Threshold 0.5 for every model. The correct-answer rate drifts between periods — validation 68.00%, test 70.71% — so accuracy must always be compared with the majority baseline of the same rows.)*

## 2. Data and split
Junyi Academy `Log_Problem.csv` + `Info_Content.csv`; 16,217,311 clean interactions, 72,758 students, 1,326 exercises in the log (1,330 in the exercise table).
Chronological split by timestamp value (70/15/15):

| split | rows | students | start_utc | end_utc | correct_rate | rows_from_unseen_students |
|---|---|---|---|---|---|---|
| train | 11352490 | 57117 | 2018-08-01 07:45 | 2019-04-16 08:15 | 0.7081 | 0.0000 |
| val | 2432488 | 23694 | 2019-04-16 08:30 | 2019-06-04 08:15 | 0.6800 | 0.1591 |
| test | 2432333 | 23270 | 2019-06-04 08:30 | 2019-08-01 00:00 | 0.7071 | 0.5260 |

Timestamp resolution in the data is 900 s, so rows sharing a timestamp have no reliable order.

## 3. Features and leakage controls
Target: `is_correct` of the interaction being predicted. Features (all available *before* answering): `stu_attempts`, `stu_acc`, `prev_correct`, `recent10_acc`, `concept_attempts`, `concept_acc`, `exercise_attempts`, `exercise_acc`, `gap_minutes`, `exercise_enc`, `concept_enc`, `difficulty_code`, `stage_code`, `concept_cat`.
History features use only the same student's answers from **strictly earlier timestamps**; one function builds them for train, validation and test (validation/test rows start from the student's accumulated history and keep updating it). `exercise_enc`/`concept_enc` are smoothed training-period correct rates (out-of-fold for training rows). Columns known only after answering (total_sec_taken, total_attempt_cnt, used_hint_cnt) are never used.

Automated audit results:
- PASS — Chronological split: train < validation < test (no shared timestamp) (train ends 2019-04-16 08:15, val 2019-04-16 08:30..2019-06-04 08:15, test starts 2019-06-04 08:30)
- PASS — No post-answer column / label copy among features (max |corr(feature, label)| = 0.292)
- PASS — Vectorised features == independent naive recomputation (120 students, 11,033 rows, max abs error 2.97e-08, NaN pattern identical: True)
- PASS — A student's features do not depend on other students (max abs diff vs full run 0.00e+00)
- PASS — Label-flip test: flipping an answer never changes its own / same-timestamp / earlier / other-student features (40 flips, violations=0; later rows changed in 37/40 flips (test has power))
- PASS — Target encoding is out-of-fold (a training label never reaches its own fold's training features) (3 flips x 2 encoders, violations=0)
- PASS — Same feature semantics in train / val / test (NaN only when there is no earlier answer)
- PASS — BKT label-flip test: an answer never changes BKT predictions at/before its own timestamp (30 flips, violations=0; later rows changed in 13/30 flips)
- PASS — Saved model reloads and reproduces in-memory predictions (max |diff| = 0.0e+00)
- PASS — Prediction interface handles cold-start, unknown exercise, missing metadata, ts=None, batches, bad order
- PASS — Online predictor reproduces offline features (train/val/test rows) (40 students, 3,818 rows, max rel. feature err 2.0e-08, encoding err 3.0e-08, NaN-pattern mismatches 0)
- PASS — Online predictor reproduces offline test probabilities (1,494 test rows, max |diff| 0.0e+00)
- PASS — Online BKT mastery == offline BKT mastery (max |diff| 5.0e-07)

## 4. Models compared (same strict features, same rows)
Majority/base-rate; student past-accuracy heuristic; Logistic Regression; HistGradientBoosting (two configurations, chosen on validation); BKT with guessed parameters and with parameters fitted on the training period (p_l0=0.766, p_t=0.001, p_g=0.450, p_s=0.196). A "loose" HistGB variant (rows may see earlier rows of their own timestamp bucket) is reported only as a sensitivity check and was never eligible for selection.

**Sensitivity check.** On test, the loose variant scores ROC-AUC 0.7597 / accuracy 75.09% versus 0.7421 / 74.16% for the strict version of the same configuration (+0.0176 AUC). The gap shows how much apparent signal depends on rows seeing same-timestamp history of unknown order; treat the loose number as an upper limit, never as a result.


### Validation (used for selection and thresholds)
| model | accuracy | majority_accuracy_same_rows | roc_auc | pr_auc | log_loss | brier | ece |
|---|---|---|---|---|---|---|---|
| Majority / base-rate | 0.6800 | 0.6800 | 0.5000 | 0.6800 | 0.6288 | 0.2184 | 0.0281 |
| Student past-accuracy heuristic | 0.6975 | 0.6800 | 0.6731 | 0.7970 | 0.6336 | 0.2012 | 0.0203 |
| Logistic Regression | 0.7205 | 0.6800 | 0.7343 | 0.8457 | 0.5498 | 0.1853 | 0.0057 |
| HistGB-A (63 leaves, lr 0.10) | 0.7241 | 0.6800 | 0.7416 | 0.8516 | 0.5435 | 0.1830 | 0.0070 |
| HistGB-B (127 leaves, lr 0.06, L2) | 0.7238 | 0.6800 | 0.7415 | 0.8517 | 0.5437 | 0.1831 | 0.0065 |
| HistGB-A LOOSE (sensitivity only) | 0.7349 | 0.6800 | 0.7588 | 0.8618 | 0.5303 | 0.1775 | 0.0035 |
| BKT (fixed guessed params) | 0.6016 | 0.6800 | 0.5906 | 0.7461 | 0.7520 | 0.2608 | 0.2048 |
| BKT (fitted on train) | 0.6992 | 0.6800 | 0.6599 | 0.7826 | 0.5927 | 0.2022 | 0.0339 |

### Test — final model at validation-tuned thresholds
| threshold_kind | threshold | accuracy | balanced_accuracy | precision | recall | precision_incorrect | recall_incorrect | roc_auc | log_loss |
|---|---|---|---|---|---|---|---|---|---|
| default_0.5 | 0.5000 | 0.7416 | 0.6190 | 0.7654 | 0.9149 | 0.6113 | 0.3230 | 0.7421 | 0.5244 |
| accuracy_opt(val) | 0.4900 | 0.7416 | 0.6144 | 0.7626 | 0.9216 | 0.6187 | 0.3071 | 0.7421 | 0.5244 |
| balanced_opt(val) | 0.6650 | 0.7003 | 0.6734 | 0.8199 | 0.7383 | 0.4906 | 0.6084 | 0.7421 | 0.5244 |

### Paired comparison (final model − reference, student-level bootstrap, 95 % CI)
| vs | accuracy_diff_pp | acc_ci95_low_pp | acc_ci95_high_pp | logloss_diff | ll_ci95_low | ll_ci95_high |
|---|---|---|---|---|---|---|
| Majority / base-rate | 3.4515 | 3.1852 | 3.7227 | -0.0804 | -0.0830 | -0.0781 |
| Student past-accuracy heuristic | 1.9766 | 1.8434 | 2.1026 | -0.0982 | -0.1012 | -0.0951 |
| BKT (fitted on train) | 1.9633 | 1.8746 | 2.0472 | -0.0457 | -0.0466 | -0.0446 |
| BKT (fixed guessed params) | 12.3127 | 12.0920 | 12.5349 | -0.1956 | -0.1980 | -0.1932 |
| Logistic Regression | 0.2698 | 0.2234 | 0.3172 | -0.0069 | -0.0072 | -0.0065 |

### Subgroups (test)
| group | rows | correct_rate | majority_accuracy | accuracy | roc_auc | log_loss |
|---|---|---|---|---|---|---|
| all test rows | 2432333 | 0.7071 | 0.7071 | 0.7416 | 0.7421 | 0.5244 |
| students seen in training | 1152950 | 0.7038 | 0.7038 | 0.7368 | 0.7375 | 0.5305 |
| students NEVER seen in training | 1279383 | 0.7101 | 0.7101 | 0.7458 | 0.7464 | 0.5188 |
| first 5 answers of the student | 93449 | 0.7701 | 0.7701 | 0.7699 | 0.7050 | 0.4924 |
| 5-49 earlier answers | 279133 | 0.7423 | 0.7423 | 0.7617 | 0.7325 | 0.5020 |
| 50-499 earlier answers | 1089624 | 0.7053 | 0.7053 | 0.7417 | 0.7449 | 0.5236 |
| 500+ earlier answers | 970127 | 0.6930 | 0.6930 | 0.7328 | 0.7420 | 0.5347 |
| difficulty = easy | 1632771 | 0.7419 | 0.7419 | 0.7663 | 0.7447 | 0.4944 |
| difficulty = hard | 236127 | 0.6266 | 0.6266 | 0.6893 | 0.7200 | 0.5872 |
| difficulty = normal | 497761 | 0.6304 | 0.6304 | 0.6827 | 0.7060 | 0.5950 |
| difficulty = unset | 65674 | 0.7148 | 0.7148 | 0.7600 | 0.7576 | 0.5072 |

## 5. Limitations (read before using the numbers)
1. **Conservative features.** Because timestamps are coarse, answers inside the same timestamp bucket are hidden. In production, same-session answers would be available; a validated session-aware feature (using `problem_number` order inside one exercise session) is a possible future improvement, but its ordering assumption could not be verified from this log.
2. **Temporal drift.** The correct-answer rate differs between validation and test; reported gains are relative to the majority baseline of the same rows.
3. **BKT** uses one global parameter set and `level4_id` as a concept proxy; it is a mastery tracker, not an optimised predictor. Mastery estimates in `bkt_mastery_estimates.csv.gz` are as of the end of the data.
4. **Cold start.** The first answers of a new student have no history; performance on them is lower (see subgroup table). Predictions for exercises never attempted rely on difficulty metadata and the training prior.
5. **Training sample.** Learned models were fitted on a 3,000,000-row random sample of the 11,352,490 training rows. Features are history-based and were computed on all rows, so this does not introduce leakage.
6. **Single split.** One chronological hold-out; no repeated rolling-origin evaluation. Confidence intervals resample students, not time periods.
7. **No causal claim.** The model predicts correctness; it does not show that recommended exercises *cause* learning.
8. The final model is trained on the training period only. For deployment it can be refitted on all data with the same code.

## 6. Reproducibility
Seed 42; libraries {"numpy": "2.1.3", "pandas": "2.3.3", "scikit-learn": "1.6.1", "scipy": "1.16.3", "joblib": "1.6.0", "matplotlib": "3.10.0", "numba": "0.61.2", "python": "3.13.15"}; BKT engine: numba; HistGB/LR fit sample 3,000,000 rows.
Re-run: attach the Junyi dataset, `SMOKE_TEST=False`, **Save & Run All** in a fresh session. All artifacts are regenerated; `member2_manifest.json` lists SHA-256 hashes.

## 7. Using the model (Member 3)
```python
from learning_predictor import LearningPredictor
lp = LearningPredictor.from_files("member2_final_model.joblib", "member2_model_card.json", "member2_exercise_lookup.csv")
lp.observe(student_id, ucid, is_correct, ts)                 # after every answer, timestamps non-decreasing per student
p  = lp.predict_proba(student_id, ucid, ts)                  # P(correct) before answering
ps = lp.predict_many(student_id, candidate_ucids, ts)        # score many exercises at once
lp.rank_by_target(student_id, candidate_ucids, target=0.7)   # challenging-but-doable ordering
lp.bkt_mastery(student_id, ucid)                             # concept mastery in [0,1]
lp.predict_label(student_id, ucid, ts, mode="balanced")      # 1 = predicted correct (thresholds in the model card)
```
