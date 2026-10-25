# Post hoc: the drop tests' CIs, resampling clusters instead of single drops

From `tumble/posthoc_cluster_ci.py` (2026-10-25). Drop: the registered method. Cell: whole runs of 5 drops from
one start (36 per height). Group: whole body-and-weight blocks (6 per height; rough with so few).

| test | n | mean | drop 95% CI | cell 95% CI | group 95% CI |
|---|---|---|---|---|---|
| 30 cm: 3 start fixed, bounce fitted (main) minus 2 start fixed, dead | 180 | -0.522 | -0.64 to -0.402 | -0.676 to -0.375 | -0.634 to -0.433 |
| 30 cm: 3 start fixed, bounce fitted (main) minus naive | 180 | -0.872 | -1.006 to -0.729 | -1.052 to -0.685 | -0.957 to -0.78 |
| 15 cm: hard floor 0.31, converged (primary) minus dead soft floor (control) | 180 | -0.444 | -0.537 to -0.348 | -0.587 to -0.31 | -0.553 to -0.343 |
| 15 cm: hard floor 0.31, converged (primary) minus naive | 180 | -0.846 | -0.964 to -0.724 | -1.009 to -0.668 | -0.923 to -0.762 |
