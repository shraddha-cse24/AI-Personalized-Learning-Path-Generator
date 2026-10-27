# Simulated-learner evaluation (40 learners x 150 answers)

Same simulated learners for every policy. See `engine/simulation.py` for the assumptions (simulation, not real students).

| metric | Adaptive engine | Fixed topic sequence | Random practice |
|---|---|---|---|
| mean_theta_gain_touched | 0.359 | 0.408 | 0.117 |
| total_theta_gain | 8.906 | 8.170 | 11.100 |
| topics_newly_learned | 4.550 | 4.550 | 1.825 |
| weak_topics_start | 69.250 | 69.250 | 69.250 |
| weak_topics_improved | 2.075 | 1.825 | 1.125 |
| distinct_topics | 25.575 | 20.000 | 94.975 |
| repeat_rate | 0.027 | 0.000 | 0.055 |
| gate_violation_rate | 0.000 | 0.000 | 0.804 |
| frustrating_rate(p<0.4) | 0.015 | 0.020 | 0.136 |
| too_easy_rate(p>0.9) | 0.220 | 0.263 | 0.094 |
| observed_correct_rate | 0.789 | 0.818 | 0.657 |

## Paired differences, adaptive minus baseline (mean, 95% bootstrap CI over learners)

| comparison | metric | mean diff | 95% CI |
|---|---|---|---|
| adaptive - fixed_sequence | mean_theta_gain_touched | -0.050 | [-0.061, -0.036] |
| adaptive - fixed_sequence | total_theta_gain | +0.737 | [+0.570, +0.895] |
| adaptive - fixed_sequence | topics_newly_learned | +0.000 | [-0.550, +0.550] |
| adaptive - fixed_sequence | weak_topics_start | +0.000 | [+0.000, +0.000] |
| adaptive - fixed_sequence | weak_topics_improved | +0.250 | [-0.025, +0.500] |
| adaptive - fixed_sequence | distinct_topics | +5.575 | [+4.775, +6.325] |
| adaptive - fixed_sequence | repeat_rate | +0.027 | [+0.014, +0.043] |
| adaptive - fixed_sequence | gate_violation_rate | +0.000 | [+0.000, +0.000] |
| adaptive - fixed_sequence | frustrating_rate(p<0.4) | -0.006 | [-0.029, +0.008] |
| adaptive - fixed_sequence | too_easy_rate(p>0.9) | -0.043 | [-0.063, -0.024] |
| adaptive - fixed_sequence | observed_correct_rate | -0.029 | [-0.040, -0.016] |
| adaptive - random | mean_theta_gain_touched | +0.242 | [+0.212, +0.277] |
| adaptive - random | total_theta_gain | -2.194 | [-2.532, -1.713] |
| adaptive - random | topics_newly_learned | +2.725 | [+1.999, +3.550] |
| adaptive - random | weak_topics_start | +0.000 | [+0.000, +0.000] |
| adaptive - random | weak_topics_improved | +0.950 | [+0.150, +1.925] |
| adaptive - random | distinct_topics | -69.400 | [-70.800, -68.000] |
| adaptive - random | repeat_rate | -0.028 | [-0.040, -0.014] |
| adaptive - random | gate_violation_rate | -0.804 | [-0.815, -0.795] |
| adaptive - random | frustrating_rate(p<0.4) | -0.121 | [-0.159, -0.087] |
| adaptive - random | too_easy_rate(p>0.9) | +0.126 | [+0.105, +0.147] |
| adaptive - random | observed_correct_rate | +0.132 | [+0.116, +0.148] |