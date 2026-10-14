# H4: the 30 cm redo against the four models committed before it

180 drops (0 with an unknown mark left out). Naive predictor Brier 1.506.

| model | Brier | minus naive (95% CI) | top state right |
|---|---|---|---|
| 1 old start, dead | 0.871 | -0.634 (-0.741 to -0.525) | 0.372 |
| 2 start fixed, dead | 1.156 | -0.349 (-0.426 to -0.273) | 0.283 |
| 3 start fixed, bounce fitted (main) | 0.634 | -0.872 (-1.006 to -0.729) | 0.472 |
| 4 start fixed, bounce measured | 0.784 | -0.722 (-0.841 to -0.606) | 0.417 |

**H4 (main minus dead): -0.522 (95% CI -0.64 to -0.402); supported: True.** Measured-bounce minus dead: -0.373 (CI [-0.458, -0.292]).

| group | n | 1 | 2 | 3 | 4 | P(upright) main / seen |
|---|---|---|---|---|---|---|
| E1_tub mass low | 30 | 0.786 | 1.116 | 0.613 | 0.703 | 0.51 / 10/30 |
| E1_tub mass high | 30 | 0.598 | 1.017 | 0.501 | 0.638 | 0.323 / 9/30 |
| E2_dome mass low | 30 | 0.899 | 1.36 | 0.584 | 0.765 | 0.614 / 16/30 |
| E2_dome mass high | 30 | 0.888 | 1.14 | 0.616 | 0.833 | 0.391 / 14/30 |
| E3_tall mass low | 30 | 0.94 | 1.055 | 0.683 | 0.786 | 0.713 / 16/30 |
| E3_tall mass high | 30 | 1.115 | 1.249 | 0.807 | 0.979 | 0.338 / 9/30 |

## Mass control (main model)

- E1_tub: predicted P(upright) low 0.51 vs high 0.323; seen 10/30 vs 9/30; same direction True; Fisher p 1.0
- E2_dome: predicted P(upright) low 0.614 vs high 0.391; seen 16/30 vs 14/30; same direction True; Fisher p 0.7965
- E3_tall: predicted P(upright) low 0.713 vs high 0.338; seen 16/30 vs 9/30; same direction True; Fisher p 0.1154

## By start, pooled (main model, predicted > observed)

- low / nose down (n=15): upright 0.62>0.53, inverted 0.26>0.33, side 0.10>0.07, head up 0.01>0.07, head down 0.01>0.00
- low / tail down (n=15): upright 0.62>0.53, inverted 0.25>0.13, side 0.10>0.27, head up 0.01>0.00, head down 0.02>0.07
- low / side (n=30): upright 0.61>0.50, inverted 0.29>0.40, side 0.09>0.10, head up 0.01>0.00, head down 0.00>0.00
- low / upside down (n=15): upright 0.62>0.40, inverted 0.29>0.53, side 0.08>0.07, head up 0.01>0.00, head down 0.01>0.00
- low / upside down, 45 to the left (n=15): upright 0.60>0.33, inverted 0.29>0.47, side 0.08>0.13, head up 0.01>0.07, head down 0.01>0.00
- high / nose down (n=15): upright 0.30>0.53, inverted 0.55>0.27, side 0.09>0.13, head up 0.03>0.00, head down 0.02>0.07
- high / tail down (n=15): upright 0.39>0.53, inverted 0.48>0.20, side 0.08>0.07, head up 0.02>0.13, head down 0.02>0.07
- high / side (n=30): upright 0.36>0.33, inverted 0.52>0.47, side 0.10>0.17, head up 0.01>0.03, head down 0.01>0.00
- high / upside down (n=15): upright 0.32>0.33, inverted 0.54>0.53, side 0.07>0.07, head up 0.03>0.07, head down 0.05>0.00
- high / upside down, 45 to the left (n=15): upright 0.36>0.07, inverted 0.51>0.67, side 0.08>0.07, head up 0.02>0.13, head down 0.02>0.07
