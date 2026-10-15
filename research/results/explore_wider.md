# The best design, wider than the sweep allowed (exploratory)

Top 211 mm, round 0.13, dz -6 mm; only the shell's half-width changes. The sweep stopped at half-width 175 (350 mm across; the robot is 339.5 mm long). 1000 drops each (sampling error about +-1.5 pts). The surrogate column is what the Gaussian process predicted before these runs; past 175 it is extrapolating.

## cover, bounce

| half-width (mm) | across (mm) | simulator P(upright) | surrogate guess | mass (g) | CoM height (mm) |
|---|---|---|---|---|---|
| 150 | 300 | 0.588 | 0.575 +- 0.027 | 3710 | 54.9 |
| 175 | 350 | 0.675 | 0.616 +- 0.036 | 3769 | 56.5 |
| 200 | 400 | 0.680 | 0.643 +- 0.054 | 3829 | 57.9 |
| 225 | 450 | 0.655 | 0.652 +- 0.076 | 3889 | 59.4 |
| 250 | 500 | 0.637 | 0.646 +- 0.099 | 3949 | 60.8 |
| 300 | 600 | 0.630 | 0.604 +- 0.137 | 4071 | 63.5 |
| 350 | 700 | 0.633 | 0.549 +- 0.162 | 4194 | 66.0 |

## cover, dead

| half-width (mm) | across (mm) | simulator P(upright) | surrogate guess | mass (g) | CoM height (mm) |
|---|---|---|---|---|---|
| 150 | 300 | 0.565 | 0.550 +- 0.025 | 3710 | 54.9 |
| 175 | 350 | 0.646 | 0.578 +- 0.033 | 3769 | 56.5 |
| 200 | 400 | 0.644 | 0.600 +- 0.048 | 3829 | 57.9 |
| 225 | 450 | 0.609 | 0.610 +- 0.068 | 3889 | 59.4 |
| 250 | 500 | 0.586 | 0.610 +- 0.088 | 3949 | 60.8 |
| 300 | 600 | 0.575 | 0.586 +- 0.125 | 4071 | 63.5 |
| 350 | 700 | 0.582 | 0.547 +- 0.152 | 4194 | 66.0 |

