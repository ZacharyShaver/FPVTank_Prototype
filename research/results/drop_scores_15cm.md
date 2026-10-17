# H3c: the 15 cm drops (from the drop stand) against the six models committed before them

179 drops (1 with an unknown mark left out). Naive predictor Brier 1.52; best possible (a model with each cell's true odds) 0.601.

| model | Brier | minus naive (95% CI) | top state right |
|---|---|---|---|
| hard floor 0.31, converged (primary) | 0.675 | -0.845 (-0.957 to -0.722) | 0.531 |
| dead soft floor (control) | 1.118 | -0.402 (-0.481 to -0.324) | 0.313 |
| soft floor, bounce fitted at 6 cm | 0.648 | -0.872 (-0.998 to -0.739) | 0.464 |
| hard floor 0.39, the ball measured | 0.64 | -0.88 (-0.989 to -0.759) | 0.531 |
| hard floor 0.55, the ball rough | 0.592 | -0.928 (-1.047 to -0.8) | 0.559 |
| hard floor 0.31, 0.5 ms (unconverged, C14) | 0.626 | -0.893 (-1.005 to -0.771) | 0.536 |

**Primary (converged 0.31 hard floor minus dead): -0.443 (95% CI -0.538 to -0.347); minus naive CI [-0.957, -0.722]; supported: True.**

## Secondary, no direction predicted

- hard floor 0.39, the ball measured minus hard floor 0.31, converged (primary): -0.035 (95% CI -0.055 to -0.016)
- hard floor 0.39, the ball measured minus hard floor 0.55, the ball rough: 0.048 (95% CI -0.005 to 0.098)
- hard floor 0.39, the ball measured minus soft floor, bounce fitted at 6 cm: -0.008 (95% CI -0.068 to 0.052)
- hard floor 0.31, converged (primary) minus hard floor 0.55, the ball rough: 0.083 (95% CI 0.016 to 0.149)
- hard floor 0.31, converged (primary) minus soft floor, bounce fitted at 6 cm: 0.027 (95% CI -0.046 to 0.099)

| group | n | hard floor 0.31, converged (primary) | dead soft floor (control) | soft floor, bounce fitted at 6 cm | hard floor 0.39, the ball measured | hard floor 0.55, the ball rough | hard floor 0.31, 0.5 ms (unconverged, C14) | P(upright) primary / seen |
|---|---|---|---|---|---|---|---|---|
| E1_tub mass low | 30 | 0.449 | 0.941 | 0.479 | 0.439 | 0.485 | 0.452 | 0.362 / 9/30 |
| E1_tub mass high | 30 | 0.393 | 0.64 | 0.453 | 0.401 | 0.414 | 0.409 | 0.13 / 5/30 |
| E2_dome mass low | 30 | 0.675 | 1.349 | 0.668 | 0.62 | 0.618 | 0.609 | 0.448 / 15/30 |
| E2_dome mass high | 30 | 0.868 | 1.299 | 0.684 | 0.765 | 0.582 | 0.721 | 0.127 / 15/30 |
| E3_tall mass low | 29 | 0.781 | 1.13 | 0.822 | 0.759 | 0.697 | 0.715 | 0.524 / 16/29 |
| E3_tall mass high | 30 | 0.886 | 1.347 | 0.788 | 0.86 | 0.76 | 0.854 | 0.213 / 10/30 |

## Mass control (primary model)

- E1_tub: predicted P(upright) low 0.362 vs high 0.13; seen 9/30 vs 5/30; same direction True; Fisher p 0.3604
- E2_dome: predicted P(upright) low 0.448 vs high 0.127; seen 15/30 vs 15/30; same direction False; Fisher p 1.0
- E3_tall: predicted P(upright) low 0.524 vs high 0.213; seen 16/29 vs 10/30; same direction True; Fisher p 0.1188

## By start, pooled (primary model, predicted > observed)

- low / nose down (n=14): upright 0.56>0.36, inverted 0.27>0.43, side 0.11>0.07, head up 0.05>0.00, head down 0.00>0.14
- low / tail down (n=15): upright 0.63>0.47, inverted 0.26>0.27, side 0.03>0.13, head up 0.00>0.13, head down 0.08>0.00
- low / side (n=30): upright 0.52>0.63, inverted 0.39>0.20, side 0.08>0.10, head up 0.00>0.03, head down 0.00>0.03
- low / upside down (n=15): upright 0.03>0.20, inverted 0.95>0.67, side 0.02>0.13, head up 0.00>0.00, head down 0.00>0.00
- low / upside down, 45 to the left (n=15): upright 0.40>0.40, inverted 0.53>0.40, side 0.06>0.00, head up 0.01>0.13, head down 0.00>0.07
- high / nose down (n=15): upright 0.17>0.40, inverted 0.70>0.47, side 0.09>0.07, head up 0.04>0.07, head down 0.00>0.00
- high / tail down (n=15): upright 0.19>0.40, inverted 0.73>0.47, side 0.01>0.13, head up 0.00>0.00, head down 0.08>0.00
- high / side (n=30): upright 0.24>0.37, inverted 0.66>0.43, side 0.09>0.13, head up 0.00>0.00, head down 0.00>0.07
- high / upside down (n=15): upright 0.00>0.13, inverted 1.00>0.67, side 0.00>0.07, head up 0.00>0.13, head down 0.00>0.00
- high / upside down, 45 to the left (n=15): upright 0.09>0.33, inverted 0.74>0.53, side 0.10>0.07, head up 0.08>0.07, head down 0.00>0.00
