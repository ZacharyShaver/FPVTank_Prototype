# Surrogate vs simulator: a Gaussian process trained on the shape sweep (exploratory)

A second, independent GP; the sprint's surrogate is `surrogate.py` (H2). Both undervalue the best designs (C15).

Errors in percentage points of P(upright). Every number is for designs the surrogate did not see.

## weightless shell, dead (as the sweep ran)

| predictor | error vs the simulator (RMS, pts) |
|---|---|
| guess the average | 8.23 |
| straight-line fit | 4.98 |
| **Gaussian process** | **3.67** (typical 2.93, worst 10.6) |
| noise floor: the simulator's own 200-drop answer | 3.44 |

Correlation with the simulator 0.895. Inside its own 95% error bars: 95% of designs. Length scales (0-1 range; short = it matters more): {'top': 0.82, 'round': 2.08, 'width': 1.94, 'dz': 2.18}.

Against 1000-drop reruns (each predicted without its own design):

| design (top/round/width/dz) | simulator, 1000 drops | surrogate | off by (pts) | simulator noise (pts) | rank by the surrogate, of 400 |
|---|---|---|---|---|---|
| 211/0.13/169/-6 | 0.750 | 0.709 | -4.1 | +-1.4 | 1 |
| 196/0.19/162/-19 | 0.739 | 0.689 | -5.0 | +-1.4 | 2 |
| 191/0.39/163/-8 | 0.698 | 0.607 | -9.1 | +-1.5 | 11 |
| 204/0.23/144/-6 | 0.674 | 0.639 | -3.5 | +-1.5 | 5 |
| 219/0.10/97/-14 | 0.660 | 0.597 | -6.3 | +-1.5 | 10 |
| 209/0.12/138/16 | 0.625 | 0.597 | -2.8 | +-1.5 | 8 |
| tub | 0.401 | 0.356 | -4.5 | +-1.5 | - |

## cover, dead

| predictor | error vs the simulator (RMS, pts) |
|---|---|
| guess the average | 5.76 |
| straight-line fit | 4.32 |
| **Gaussian process** | **3.55** (typical 2.83, worst 14.2) |
| noise floor: the simulator's own 200-drop answer | 3.42 |

Correlation with the simulator 0.786. Inside its own 95% error bars: 96% of designs. Length scales (0-1 range; short = it matters more): {'top': 0.65, 'round': 1.73, 'width': 1.56, 'dz': 1.52}.

Against 1000-drop reruns (each predicted without its own design):

| design (top/round/width/dz) | simulator, 1000 drops | surrogate | off by (pts) | simulator noise (pts) | rank by the surrogate, of 400 |
|---|---|---|---|---|---|
| 211/0.13/169/-6 | 0.649 | 0.533 | -11.6 | +-1.5 | 2 |
| 196/0.19/162/-19 | 0.617 | 0.564 | -5.3 | +-1.5 | 1 |
| 191/0.39/163/-8 | 0.556 | 0.506 | -5.0 | +-1.6 | 8 |
| 219/0.43/156/1 | 0.554 | 0.525 | -2.9 | +-1.6 | 6 |
| 219/0.10/97/-14 | 0.527 | 0.504 | -2.3 | +-1.6 | 7 |
| 211/0.75/133/11 | 0.469 | 0.435 | -3.4 | +-1.6 | 58 |
| tub | 0.401 | 0.359 | -4.2 | +-1.5 | - |

## cover, bounce

| predictor | error vs the simulator (RMS, pts) |
|---|---|
| guess the average | 6.27 |
| straight-line fit | 4.58 |
| **Gaussian process** | **3.68** (typical 2.89, worst 12.5) |
| noise floor: the simulator's own 200-drop answer | 3.42 |

Correlation with the simulator 0.809. Inside its own 95% error bars: 94% of designs. Length scales (0-1 range; short = it matters more): {'top': 0.6, 'round': 1.36, 'width': 1.37, 'dz': 1.4}.

Against 1000-drop reruns (each predicted without its own design):

| design (top/round/width/dz) | simulator, 1000 drops | surrogate | off by (pts) | simulator noise (pts) | rank by the surrogate, of 400 |
|---|---|---|---|---|---|
| 211/0.13/169/-6 | 0.671 | 0.568 | -10.3 | +-1.5 | 2 |
| 196/0.19/162/-19 | 0.652 | 0.596 | -5.6 | +-1.5 | 1 |
| 191/0.39/163/-8 | 0.605 | 0.533 | -7.2 | +-1.5 | 8 |
| 219/0.43/156/1 | 0.589 | 0.553 | -3.6 | +-1.6 | 3 |
| 193/0.31/175/19 | 0.575 | 0.507 | -6.8 | +-1.6 | 14 |
| 204/0.23/144/-6 | 0.564 | 0.549 | -1.5 | +-1.6 | 5 |
| tub | 0.401 | 0.358 | -4.3 | +-1.5 | - |

Speed, one core: the simulator takes 0.01 s per drop, so 3 s for one design at 200 drops. The surrogate answers one design in about 19 microseconds: about 141,594 times faster.
