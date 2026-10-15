# The best design past the sweep's edge: half-width (exploratory)

The best design (211/0.13/169/-6, top/round/half-width/dz) with only the half-width changed. The sweep stopped at half-width 175 mm (half-width 175 is 350 mm across; the robot is 339.5 mm long). 1000 drops each (sampling error about +-1.5 pts). The surrogate column is what the Gaussian process predicted before these runs; past 175 it is extrapolating.

## cover, bounce

| half-width (mm) | simulator P(upright) | surrogate guess | mass (g) | CoM height (mm) | upside down | side | end |
|---|---|---|---|---|---|---|---|
| 150 | 0.588 | 0.575 +- 0.027 | 3710 | 54.9 | 129 | 197 | 86 |
| 175 | 0.675 | 0.616 +- 0.036 | 3769 | 56.5 | 145 | 93 | 87 |
| 200 | 0.680 | 0.643 +- 0.054 | 3829 | 57.9 | 159 | 55 | 106 |
| 225 | 0.655 | 0.652 +- 0.076 | 3889 | 59.4 | 168 | 51 | 126 |
| 250 | 0.637 | 0.646 +- 0.099 | 3949 | 60.8 | 176 | 48 | 139 |
| 300 | 0.630 | 0.604 +- 0.137 | 4071 | 63.5 | 193 | 54 | 123 |
| 350 | 0.633 | 0.549 +- 0.162 | 4194 | 66.0 | 238 | 11 | 118 |

## cover, dead

| half-width (mm) | simulator P(upright) | surrogate guess | mass (g) | CoM height (mm) | upside down | side | end |
|---|---|---|---|---|---|---|---|
| 150 | 0.565 | 0.550 +- 0.025 | 3710 | 54.9 | 129 | 207 | 99 |
| 175 | 0.646 | 0.578 +- 0.033 | 3769 | 56.5 | 144 | 101 | 109 |
| 200 | 0.644 | 0.600 +- 0.048 | 3829 | 57.9 | 159 | 66 | 131 |
| 225 | 0.609 | 0.610 +- 0.068 | 3889 | 59.4 | 169 | 60 | 162 |
| 250 | 0.586 | 0.610 +- 0.088 | 3949 | 60.8 | 179 | 56 | 179 |
| 300 | 0.575 | 0.586 +- 0.125 | 4071 | 63.5 | 192 | 63 | 170 |
| 350 | 0.582 | 0.547 +- 0.152 | 4194 | 66.0 | 228 | 22 | 168 |

