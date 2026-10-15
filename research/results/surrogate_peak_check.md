# Surrogate intervals at the best designs (audit C15)

Each of the 6 best designs predicted without its own data; truth is the 1000-drop rerun. "Inside" counts the 90% band
widened by the rerun's own noise. A calibrated surrogate would have about 5 of 6 inside.

| surrogate | sweep variant | inside 90% band | mean miss (pts; + = surrogate too low) |
|---|---|---|---|
| surrogate.py (H2) | weightless shell, dead (as the sweep ran) | 1 of 6 | +4.9 |
| surrogate_gp.py | weightless shell, dead (as the sweep ran) | 1 of 6 | +5.1 |
| surrogate_gp.py | cover, dead | 2 of 6 | +5.1 |
| surrogate_gp.py | cover, bounce | 1 of 6 | +5.8 |

**surrogate.py (H2), weightless shell, dead (as the sweep ran)**

| design (top/round/half-width/dz) | simulator, 1000 drops | surrogate | miss (pts) | 90% band (pts) |
|---|---|---|---|---|
| 211/0.13/169/-6 | 0.750 | 0.712 | +3.8 | +-3.6 (outside) |
| 196/0.19/162/-19 | 0.739 | 0.698 | +4.1 | +-3.3 (outside) |
| 191/0.39/163/-8 | 0.698 | 0.609 | +8.9 | +-2.8 (outside) |
| 204/0.23/144/-6 | 0.674 | 0.643 | +3.1 | +-2.8 (outside) |
| 219/0.10/97/-14 | 0.660 | 0.594 | +6.6 | +-4.3 (outside) |
| 209/0.12/138/16 | 0.625 | 0.598 | +2.7 | +-3.1  |

**surrogate_gp.py, weightless shell, dead (as the sweep ran)**

| design (top/round/half-width/dz) | simulator, 1000 drops | surrogate | miss (pts) | 90% band (pts) |
|---|---|---|---|---|
| 211/0.13/169/-6 | 0.750 | 0.709 | +4.1 | +-3.9 (outside) |
| 196/0.19/162/-19 | 0.739 | 0.689 | +5.0 | +-3.6 (outside) |
| 191/0.39/163/-8 | 0.698 | 0.607 | +9.1 | +-2.9 (outside) |
| 204/0.23/144/-6 | 0.674 | 0.639 | +3.5 | +-2.9 (outside) |
| 219/0.10/97/-14 | 0.660 | 0.597 | +6.3 | +-4.5 (outside) |
| 209/0.12/138/16 | 0.625 | 0.597 | +2.8 | +-3.2  |

**surrogate_gp.py, cover, dead**

| design (top/round/half-width/dz) | simulator, 1000 drops | surrogate | miss (pts) | 90% band (pts) |
|---|---|---|---|---|
| 211/0.13/169/-6 | 0.649 | 0.533 | +11.6 | +-3.8 (outside) |
| 196/0.19/162/-19 | 0.617 | 0.564 | +5.3 | +-3.7 (outside) |
| 191/0.39/163/-8 | 0.556 | 0.506 | +5.0 | +-3.0 (outside) |
| 219/0.43/156/1 | 0.554 | 0.525 | +2.9 | +-3.3  |
| 219/0.10/97/-14 | 0.527 | 0.504 | +2.3 | +-4.3  |
| 211/0.75/133/11 | 0.469 | 0.435 | +3.4 | +-3.0 (outside) |

**surrogate_gp.py, cover, bounce**

| design (top/round/half-width/dz) | simulator, 1000 drops | surrogate | miss (pts) | 90% band (pts) |
|---|---|---|---|---|
| 211/0.13/169/-6 | 0.671 | 0.568 | +10.3 | +-4.0 (outside) |
| 196/0.19/162/-19 | 0.652 | 0.596 | +5.6 | +-3.8 (outside) |
| 191/0.39/163/-8 | 0.605 | 0.533 | +7.2 | +-3.1 (outside) |
| 219/0.43/156/1 | 0.589 | 0.553 | +3.6 | +-3.4 (outside) |
| 193/0.31/175/19 | 0.575 | 0.507 | +6.8 | +-3.3 (outside) |
| 204/0.23/144/-6 | 0.564 | 0.549 | +1.5 | +-3.1  |
