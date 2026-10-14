# Drop predictions at 15 cm: hard floor at a converged 0.1 ms step, bounce 0.55 (the PLA ball, rough); committed before any 15 cm drop

Release height 150 mm (lowest point of the body above the table). Contact damping ratio: 0.2. Start: fixed (world heading).

Each cell: the most likely rest state and its probability at the nominal friction, then the range of that
probability across 0.65x to 1.5x friction. 200 simulated drops per cell.

## E1_tub mass low  (mass 108.5 g, CoM z 13.0 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | upright | 0.56 | 0.56-0.56 | inverted 0.40, right side 0.03, left side 0.02, nose up 0.01 |
| tail down | upright | 0.53 | 0.53-0.53 | inverted 0.39, left side 0.04, right side 0.04, nose down 0.01 |
| left side down | upright | 0.60 | 0.60-0.60 | inverted 0.38, left side 0.01, right side 0.01 |
| right side down | upright | 0.54 | 0.54-0.54 | inverted 0.44, left side 0.01, right side 0.01 |
| upside down | inverted | 0.78 | 0.78-0.78 | upright 0.15, right side 0.04, left side 0.03, nose up 0.01 |
| upside down, 45 to the left | inverted | 0.49 | 0.49-0.49 | upright 0.49, right side 0.01, nose up 0.01 |

## E1_tub mass high  (mass 108.5 g, CoM z 19.5 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | inverted | 0.97 | 0.97-0.97 | upright 0.03 |
| tail down | inverted | 0.74 | 0.74-0.74 | upright 0.24, left side 0.01, right side 0.01 |
| left side down | inverted | 0.55 | 0.55-0.55 | upright 0.43, left side 0.02, right side 0.01 |
| right side down | inverted | 0.51 | 0.51-0.51 | upright 0.48, right side 0.01 |
| upside down | inverted | 0.93 | 0.93-0.93 | right side 0.04, upright 0.03, left side 0.01 |
| upside down, 45 to the left | inverted | 0.81 | 0.81-0.81 | upright 0.17, left side 0.01, right side 0.01 |

## E2_dome mass low  (mass 118.9 g, CoM z 15.2 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | upright | 0.69 | 0.69-0.69 | inverted 0.23, right side 0.04, left side 0.03, nose up 0.01 |
| tail down | upright | 0.63 | 0.63-0.63 | inverted 0.28, left side 0.06, right side 0.03, nose up 0.01, nose down 0.01 |
| left side down | upright | 0.69 | 0.69-0.69 | inverted 0.27, right side 0.03, left side 0.01, nose down 0.01 |
| right side down | upright | 0.61 | 0.61-0.61 | inverted 0.32, left side 0.04, right side 0.02, nose down 0.01 |
| upside down | inverted | 0.47 | 0.47-0.47 | upright 0.41, left side 0.07, right side 0.03, nose down 0.01 |
| upside down, 45 to the left | upright | 0.64 | 0.64-0.64 | inverted 0.28, right side 0.04, left side 0.04, nose up 0.01 |

## E2_dome mass high  (mass 118.9 g, CoM z 21.9 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | inverted | 0.49 | 0.49-0.49 | upright 0.41, nose down 0.05, nose up 0.02, right side 0.01, left side 0.01 |
| tail down | upright | 0.47 | 0.47-0.47 | inverted 0.46, nose up 0.04, nose down 0.03, left side 0.01 |
| left side down | upright | 0.52 | 0.52-0.52 | inverted 0.41, left side 0.03, right side 0.02, nose up 0.01, nose down 0.01 |
| right side down | upright | 0.66 | 0.66-0.66 | inverted 0.33, right side 0.01, nose down 0.01 |
| upside down | inverted | 0.74 | 0.74-0.74 | upright 0.17, nose down 0.04, left side 0.02, nose up 0.01, right side 0.01 |
| upside down, 45 to the left | upright | 0.54 | 0.54-0.54 | inverted 0.43, left side 0.01, nose down 0.01, nose up 0.01 |

## E3_tall mass low  (mass 140.1 g, CoM z 20.4 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | upright | 0.64 | 0.64-0.64 | inverted 0.21, nose down 0.12, right side 0.02, left side 0.01, nose up 0.01 |
| tail down | upright | 0.58 | 0.58-0.58 | inverted 0.24, left side 0.10, right side 0.07, nose up 0.01, nose down 0.01 |
| left side down | upright | 0.62 | 0.62-0.62 | inverted 0.23, left side 0.07, nose up 0.04, right side 0.02, nose down 0.01 |
| right side down | upright | 0.67 | 0.67-0.67 | inverted 0.19, right side 0.09, nose up 0.02, nose down 0.02, left side 0.01 |
| upside down | upright | 0.68 | 0.68-0.68 | inverted 0.09, right side 0.08, nose up 0.07, left side 0.06, nose down 0.03 |
| upside down, 45 to the left | upright | 0.78 | 0.78-0.78 | inverted 0.08, nose down 0.06, right side 0.05, left side 0.03, nose up 0.01 |

## E3_tall mass high  (mass 140.1 g, CoM z 31.2 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | upright | 0.41 | 0.41-0.41 | inverted 0.33, nose down 0.12, left side 0.07, right side 0.07, nose up 0.01 |
| tail down | inverted | 0.44 | 0.44-0.44 | upright 0.29, left side 0.13, right side 0.12, nose up 0.01, nose down 0.01 |
| left side down | inverted | 0.36 | 0.36-0.36 | upright 0.34, left side 0.15, right side 0.07, nose down 0.06, nose up 0.03 |
| right side down | upright | 0.38 | 0.38-0.38 | inverted 0.30, right side 0.18, left side 0.07, nose down 0.06, nose up 0.01 |
| upside down | inverted | 0.46 | 0.46-0.46 | nose down 0.15, upright 0.12, right side 0.11, left side 0.09, nose up 0.08 |
| upside down, 45 to the left | upright | 0.48 | 0.48-0.48 | inverted 0.32, nose down 0.07, right side 0.06, left side 0.05, nose up 0.02 |
