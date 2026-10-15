# The best design past the sweep's edge: top height (exploratory)

The best design (211/0.13/169/-6, top/round/half-width/dz) with only the top height changed. The sweep stopped at top height 220 mm (half-width 175 is 350 mm across; the robot is 339.5 mm long). 1000 drops each (sampling error about +-1.5 pts). The surrogate column is what the Gaussian process predicted before these runs; past 220 it is extrapolating.

## cover, bounce

| top height (mm) | simulator P(upright) | surrogate guess | mass (g) | CoM height (mm) | upside down | side | end |
|---|---|---|---|---|---|---|---|
| 180 | 0.655 | 0.557 +- 0.029 | 3688 | 52.2 | 184 | 90 | 71 |
| 200 | 0.670 | 0.594 +- 0.029 | 3731 | 54.6 | 155 | 95 | 80 |
| 220 | 0.669 | 0.611 +- 0.039 | 3773 | 57.3 | 135 | 101 | 95 |
| 250 | 0.642 | 0.598 +- 0.077 | 3838 | 61.5 | 106 | 119 | 133 |
| 300 | 0.562 | 0.530 +- 0.141 | 3946 | 69.4 | 78 | 166 | 194 |
| 350 | 0.495 | 0.467 +- 0.173 | 4054 | 78.2 | 58 | 213 | 234 |
| 400 | 0.410 | 0.428 +- 0.184 | 4162 | 87.8 | 40 | 260 | 290 |

## cover, dead

| top height (mm) | simulator P(upright) | surrogate guess | mass (g) | CoM height (mm) | upside down | side | end |
|---|---|---|---|---|---|---|---|
| 180 | 0.625 | 0.524 +- 0.026 | 3688 | 52.2 | 185 | 102 | 88 |
| 200 | 0.635 | 0.558 +- 0.026 | 3731 | 54.6 | 158 | 111 | 96 |
| 220 | 0.635 | 0.579 +- 0.036 | 3773 | 57.3 | 135 | 117 | 113 |
| 250 | 0.624 | 0.581 +- 0.071 | 3838 | 61.5 | 105 | 128 | 143 |
| 300 | 0.539 | 0.533 +- 0.134 | 3946 | 69.4 | 78 | 176 | 207 |
| 350 | 0.462 | 0.475 +- 0.169 | 4054 | 78.2 | 63 | 218 | 257 |
| 400 | 0.378 | 0.434 +- 0.183 | 4162 | 87.8 | 48 | 261 | 313 |

