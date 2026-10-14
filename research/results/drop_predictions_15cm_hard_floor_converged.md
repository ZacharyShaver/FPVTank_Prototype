# Drop predictions at 15 cm: hard floor at a converged 0.1 ms step, bounce 0.31 (slow-motion of E3); committed before any 15 cm drop

Release height 150 mm (lowest point of the body above the table). Contact damping ratio: 0.45. Start: fixed (world heading).

Each cell: the most likely rest state and its probability at the nominal friction, then the range of that
probability across 0.65x to 1.5x friction. 200 simulated drops per cell.

## E1_tub mass low  (mass 108.5 g, CoM z 13.0 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | upright | 0.56 | 0.56-0.56 | inverted 0.38, nose up 0.04, left side 0.01, right side 0.01 |
| tail down | upright | 0.57 | 0.57-0.57 | inverted 0.34, nose down 0.04, left side 0.03, right side 0.03 |
| left side down | upright | 0.49 | 0.49-0.49 | inverted 0.47, right side 0.04 |
| right side down | upright | 0.48 | 0.48-0.48 | inverted 0.48, left side 0.03, nose up 0.01 |
| upside down | inverted | 1.00 | 1.00-1.00 |  |
| upside down, 45 to the left | inverted | 0.93 | 0.93-0.93 | upright 0.07 |

## E1_tub mass high  (mass 108.5 g, CoM z 19.5 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | inverted | 0.98 | 0.98-0.98 | upright 0.01, left side 0.01 |
| tail down | inverted | 0.89 | 0.89-0.89 | upright 0.05, left side 0.03, right side 0.03 |
| left side down | inverted | 0.62 | 0.62-0.62 | upright 0.34, right side 0.03, left side 0.01 |
| right side down | inverted | 0.58 | 0.58-0.58 | upright 0.37, left side 0.04, right side 0.01 |
| upside down | inverted | 1.00 | 1.00-1.00 |  |
| upside down, 45 to the left | inverted | 0.99 | 0.99-0.99 | upright 0.01 |

## E2_dome mass low  (mass 118.9 g, CoM z 15.2 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | upright | 0.72 | 0.72-0.72 | inverted 0.17, nose up 0.09, left side 0.01, right side 0.01 |
| tail down | upright | 0.59 | 0.59-0.59 | inverted 0.28, nose down 0.06, right side 0.04, left side 0.04 |
| left side down | upright | 0.49 | 0.49-0.49 | inverted 0.46, right side 0.04, left side 0.01 |
| right side down | upright | 0.56 | 0.56-0.56 | inverted 0.39, right side 0.04, left side 0.01 |
| upside down | inverted | 0.92 | 0.92-0.92 | upright 0.03, left side 0.03, right side 0.03 |
| upside down, 45 to the left | inverted | 0.58 | 0.58-0.58 | upright 0.30, right side 0.07, left side 0.04, nose down 0.01 |

## E2_dome mass high  (mass 118.9 g, CoM z 21.9 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | inverted | 0.60 | 0.60-0.60 | upright 0.23, nose up 0.17 |
| tail down | inverted | 0.72 | 0.72-0.72 | upright 0.17, nose down 0.09, left side 0.01, right side 0.01 |
| left side down | inverted | 0.73 | 0.73-0.73 | upright 0.20, left side 0.03, right side 0.03, nose down 0.01 |
| right side down | inverted | 0.74 | 0.74-0.74 | upright 0.16, left side 0.06, right side 0.03, nose up 0.01, nose down 0.01 |
| upside down | inverted | 1.00 | 1.00-1.00 |  |
| upside down, 45 to the left | inverted | 0.86 | 0.86-0.86 | left side 0.14, nose down 0.01 |

## E3_tall mass low  (mass 140.1 g, CoM z 20.4 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | upright | 0.61 | 0.61-0.61 | inverted 0.22, nose up 0.12, right side 0.03, left side 0.01 |
| tail down | upright | 0.52 | 0.52-0.52 | inverted 0.17, right side 0.12, left side 0.11, nose down 0.07 |
| left side down | upright | 0.58 | 0.58-0.58 | inverted 0.28, right side 0.12, left side 0.01, nose up 0.01, nose down 0.01 |
| right side down | upright | 0.55 | 0.55-0.55 | inverted 0.28, left side 0.14, right side 0.02, nose down 0.01, nose up 0.01 |
| upside down | inverted | 0.94 | 0.94-0.94 | upright 0.06 |
| upside down, 45 to the left | upright | 0.83 | 0.83-0.83 | inverted 0.08, left side 0.06, nose down 0.03, right side 0.01 |

## E3_tall mass high  (mass 140.1 g, CoM z 31.2 mm)

| start | most likely | p | across friction | others |
|---|---|---|---|---|
| nose down | inverted | 0.59 | 0.59-0.59 | upright 0.33, nose up 0.07, right side 0.01 |
| tail down | inverted | 0.48 | 0.48-0.48 | upright 0.29, right side 0.12, left side 0.08, nose down 0.03 |
| left side down | inverted | 0.62 | 0.62-0.62 | upright 0.21, right side 0.14, left side 0.02, nose down 0.01 |
| right side down | inverted | 0.64 | 0.64-0.64 | upright 0.18, left side 0.17, nose down 0.01, nose up 0.01 |
| upside down | inverted | 0.99 | 0.99-0.99 | right side 0.01 |
| upside down, 45 to the left | inverted | 0.35 | 0.35-0.35 | upright 0.27, nose down 0.22, left side 0.12, right side 0.03 |
