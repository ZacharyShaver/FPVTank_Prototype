# Post hoc: the printed mass layout (from the G-code) instead of a uniform solid

| body | PLA in the print (g) | sliced estimate used (g, body + spacer) | CoM height, mass low: print / uniform (mm) | mass high |
|---|---|---|---|---|
| E1_tub | 37.86 + spacer 2.2 | 40.48 | 13.05 / 13.01 | 19.86 / 19.47 |
| E2_dome | 48.06 + spacer 2.41 | 50.89 | 15.37 / 15.22 | 22.46 / 21.93 |
| E3_tall | 67.73 + spacer 3.92 | 72.08 | 20.74 / 20.42 | 32.23 / 31.18 |

| group | Brier, uniform | Brier, printed | P(upright) uniform | printed | seen |
|---|---|---|---|---|---|
| E1_tub mass low | 0.522 | 0.526 | 0.211 | 0.204 | 0.333 |
| E1_tub mass high | 0.343 | 0.342 | 0.018 | 0.016 | 0.133 |
| E2_dome mass low | 0.628 | 0.621 | 0.214 | 0.217 | 0.29 |
| E2_dome mass high | 0.382 | 0.371 | 0.005 | 0.005 | 0.033 |
| E3_tall mass low | 0.727 | 0.725 | 0.175 | 0.182 | 0.5 |
| E3_tall mass high | 0.864 | 0.831 | 0.003 | 0.0 | 0.2 |
| all | 0.578 | 0.57 | | | |
