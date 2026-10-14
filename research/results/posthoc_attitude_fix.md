# Post hoc: the start-attitude fix

| model | Brier, all 181 | 95% CI of (model - naive) | top state right |
|---|---|---|---|
| committed (start bug) | 0.578 | -0.833 to -0.591 | 0.508 |
| start fixed | 0.861 | -0.518 to -0.347 | 0.431 |
| start fixed + printed mass | 0.845 | -0.537 to -0.357 | 0.425 |

Naive: 1.293. Start fixed at 0.65x / 1.5x friction: 0.886 / 0.859.

| group | committed | start fixed | + printed mass | P(upright) committed / fixed / seen |
|---|---|---|---|---|
| E1_tub mass low | 0.522 | 0.835 | 0.839 | 0.211 / 0.152 / 0.33 |
| E1_tub mass high | 0.343 | 0.566 | 0.554 | 0.017 / 0.008 / 0.13 |
| E2_dome mass low | 0.628 | 0.898 | 0.905 | 0.214 / 0.128 / 0.29 |
| E2_dome mass high | 0.382 | 0.813 | 0.756 | 0.005 / 0.001 / 0.03 |
| E3_tall mass low | 0.727 | 0.876 | 0.873 | 0.175 / 0.249 / 0.50 |
| E3_tall mass high | 0.864 | 1.177 | 1.14 | 0.003 / 0.005 / 0.20 |

## By start, pooled over bodies (predicted > observed), start fixed

- low / nose down (n=15): upright 0.37>0.53, inverted 0.04>0.20, side 0.00>0.20, head up 0.60>0.07, head down 0.00>0.00
- low / tail down (n=15): upright 0.37>0.67, inverted 0.03>0.07, side 0.00>0.07, head up 0.00>0.07, head down 0.60>0.13
- low / side (n=31): upright 0.07>0.39, inverted 0.01>0.39, side 0.92>0.16, head up 0.00>0.06, head down 0.00>0.00
- low / upside down (n=15): upright 0.00>0.00, inverted 1.00>1.00, side 0.00>0.00, head up 0.00>0.00, head down 0.00>0.00
- low / upside down, 45 to the left (n=15): upright 0.20>0.27, inverted 0.69>0.60, side 0.11>0.13, head up 0.00>0.00, head down 0.00>0.00
- high / nose down (n=15): upright 0.02>0.07, inverted 0.37>0.67, side 0.00>0.13, head up 0.60>0.07, head down 0.00>0.07
- high / tail down (n=15): upright 0.01>0.47, inverted 0.33>0.40, side 0.00>0.00, head up 0.00>0.07, head down 0.66>0.07
- high / side (n=30): upright 0.00>0.10, inverted 0.24>0.67, side 0.76>0.17, head up 0.00>0.03, head down 0.00>0.03
- high / upside down (n=15): upright 0.00>0.00, inverted 1.00>1.00, side 0.00>0.00, head up 0.00>0.00, head down 0.00>0.00
- high / upside down, 45 to the left (n=15): upright 0.00>0.00, inverted 0.97>0.73, side 0.03>0.07, head up 0.00>0.13, head down 0.00>0.07
