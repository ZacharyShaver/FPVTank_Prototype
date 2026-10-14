# Drop scores (physical drops against the predictions committed before them)

181 drops: 3 bodies x mass low and high, 6 starts x 5 drops, from 6 cm. Brier score: 0 is perfect, 2 is certain and wrong; lower is better. The naive predictor says it stays on the face it was dropped on.

| group | drops | Brier, model | Brier, naive | model - naive (95% CI) | top state right, model | naive |
|---|---|---|---|---|---|---|
| E1_tub mass low | 30 | 0.522 | 1.217 | -0.695 (-0.949 to -0.413) | 0.4 | 0.433 |
| E1_tub mass high | 30 | 0.343 | 1.283 | -0.941 (-1.275 to -0.579) | 0.8 | 0.4 |
| E2_dome mass low | 31 | 0.628 | 1.306 | -0.679 (-0.894 to -0.453) | 0.387 | 0.355 |
| E2_dome mass high | 30 | 0.382 | 1.217 | -0.835 (-1.218 to -0.43) | 0.8 | 0.4 |
| E3_tall mass low | 30 | 0.727 | 1.35 | -0.623 (-0.859 to -0.379) | 0.3 | 0.267 |
| E3_tall mass high | 30 | 0.864 | 1.383 | -0.519 (-0.718 to -0.31) | 0.367 | 0.3 |
| all | 181 | 0.578 | 1.293 | -0.715 (-0.833 to -0.591) | 0.508 | 0.359 |

At 0.65x and 1.5x friction (all drops): p_lowmu: Brier 0.585, p_highmu: Brier 0.558

## The physical control: P(upright), mass low vs high

| body | predicted low | predicted high | observed low | observed high | same direction | Fisher p |
|---|---|---|---|---|---|---|
| E1_tub | 0.211 | 0.017 | 10/30 | 4/30 | True | 0.1253 |
| E2_dome | 0.214 | 0.005 | 9/31 | 1/30 | True | 0.0125 |
| E3_tall | 0.175 | 0.003 | 15/30 | 6/30 | True | 0.0292 |

## Rest states, predicted vs observed (averaged over the drops as made)

- E1_tub mass low: upright 0.21 / 0.33, inverted 0.43 / 0.53, side 0.25 / 0.07, head up 0.04 / 0.03, head down 0.06 / 0.03
- E1_tub mass high: upright 0.02 / 0.13, inverted 0.86 / 0.80, side 0.12 / 0.07, head up 0.00 / 0.00, head down 0.00 / 0.00
- E2_dome mass low: upright 0.21 / 0.29, inverted 0.34 / 0.55, side 0.28 / 0.13, head up 0.09 / 0.03, head down 0.08 / 0.00
- E2_dome mass high: upright 0.01 / 0.03, inverted 0.76 / 0.80, side 0.05 / 0.07, head up 0.08 / 0.07, head down 0.12 / 0.03
- E3_tall mass low: upright 0.17 / 0.50, inverted 0.26 / 0.23, side 0.28 / 0.17, head up 0.16 / 0.07, head down 0.13 / 0.03
- E3_tall mass high: upright 0.00 / 0.20, inverted 0.37 / 0.47, side 0.30 / 0.13, head up 0.17 / 0.10, head down 0.16 / 0.10
