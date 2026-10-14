# Simulation vs the real drops

Every model scored against the same real drops: **6 cm, 181 drops** (runs 1 and 2) and **30 cm, 180 drops** (run 3,
the marked redo). Each drop is one body, one weight position (low or high), one of six starts, and how it came to rest.

**The models** (columns below). "Made" says whether the model's predictions were committed before or after those drops:

| model | what it is | made, 6 cm | made, 30 cm |
|---|---|---|---|
| Old start | the original model: MuJoCo's default floor, with the start-heading bug (B1) | before | before |
| Dead | start fixed; MuJoCo's default floor: soft (sinks 7-17 mm) and dead (bounce 0.13) | after | before |
| Fitted | start fixed; soft floor with its bounce fitted to the 6 cm drops (0.55) | fitted to them | before |
| Hard .31 | start fixed; hard floor (sinks under 2 mm), bounce 0.31 measured from the E3 video | after | after |
| Hard .39 | start fixed; hard floor, bounce 0.39 measured from the PLA ball video | after | after |

Only predictions made before the drops are real tests. "After" means the drops had been seen, but nothing in the model
was tuned to them; "fitted" means it was tuned to them.

## 1. Overall score

**Brier score:** how far the predicted odds were from what happened, averaged over drops. 0 is perfect; 2 is
certain and wrong every time. Lower is better. **Naive** is the guess "it stays on the face it was dropped on".
**Top pick right:** how often the model's single most likely outcome is what happened.

| model | Brier, 6 cm | Brier, 30 cm | top pick right, 6 cm | top pick right, 30 cm |
|---|---|---|---|---|
| Naive | 1.293 | 1.506 | 36% | 24% |
| Old start | 0.578 | 0.871 | 51% | 37% |
| Dead | 0.861 | 1.156 | 43% | 28% |
| Fitted | 0.443 | 0.634 | 70% | 47% |
| Hard .31 | 0.483 | 0.693 | 65% | 44% |
| Hard .39 | 0.456 | 0.672 | 69% | 43% |

## 2. How often it lands upright, by body and weight

Real: drops that ended upright, out of the group. Models: the predicted chance, averaged over the same drops.

**6 cm**

| group | real | Old start | Dead | Fitted | Hard .31 | Hard .39 |
|---|---|---|---|---|---|---|
| E1 (hill), weight low | 10/30 = 33% | 21% | 15% | 36% | 36% | 37% |
| E1 (hill), weight high | 4/30 = 13% | 2% | 1% | 8% | 4% | 8% |
| E2 (oval), weight low | 9/31 = 29% | 21% | 13% | 44% | 40% | 44% |
| E2 (oval), weight high | 1/30 = 3% | 1% | 0% | 6% | 1% | 4% |
| E3 (rounded square), weight low | 15/30 = 50% | 17% | 25% | 55% | 41% | 47% |
| E3 (rounded square), weight high | 6/30 = 20% | 0% | 1% | 16% | 8% | 12% |
| **all** | **45/181 = 25%** | **10%** | **9%** | **28%** | **22%** | **25%** |

**30 cm**

| group | real | Old start | Dead | Fitted | Hard .31 | Hard .39 |
|---|---|---|---|---|---|---|
| E1 (hill), weight low | 10/30 = 33% | 21% | 15% | 51% | 39% | 41% |
| E1 (hill), weight high | 9/30 = 30% | 2% | 1% | 32% | 19% | 28% |
| E2 (oval), weight low | 16/30 = 53% | 24% | 14% | 61% | 56% | 54% |
| E2 (oval), weight high | 14/30 = 47% | 2% | 4% | 39% | 32% | 48% |
| E3 (rounded square), weight low | 16/30 = 53% | 21% | 25% | 71% | 52% | 58% |
| E3 (rounded square), weight high | 9/30 = 30% | 1% | 2% | 34% | 32% | 39% |
| **all** | **74/180 = 41%** | **12%** | **10%** | **48%** | **38%** | **45%** |

## 3. Where they end up: the whole mix

Share of all drops ending in each rest state.

**6 cm**

|  | upright | upside down | on its side | on an end |
|---|---|---|---|---|
| **real** | **25%** | **56%** | **10%** | **8%** |
| Old start | 10% | 50% | 21% | 18% |
| Dead | 9% | 41% | 30% | 20% |
| Fitted | 28% | 61% | 8% | 4% |
| Hard .31 | 22% | 59% | 10% | 9% |
| Hard .39 | 25% | 60% | 8% | 7% |

**30 cm**

|  | upright | upside down | on its side | on an end |
|---|---|---|---|---|
| **real** | **41%** | **41%** | **12%** | **7%** |
| Old start | 12% | 50% | 25% | 14% |
| Dead | 10% | 43% | 29% | 18% |
| Fitted | 48% | 40% | 9% | 3% |
| Hard .31 | 38% | 51% | 8% | 3% |
| Hard .39 | 45% | 44% | 8% | 3% |

## 4. Upright, by how it was dropped

All bodies and weights together (30 drops per start).

**6 cm**

| start (your nose = the blunt end) | real | Old start | Dead | Fitted | Hard .31 | Hard .39 |
|---|---|---|---|---|---|---|
| nose down | 9/30 = 30% | 12% | 19% | 38% | 35% | 39% |
| tail down | 17/30 = 57% | 13% | 19% | 43% | 35% | 39% |
| left side down | 10/31 = 32% | 15% | 3% | 31% | 24% | 29% |
| right side down | 5/30 = 17% | 15% | 3% | 31% | 24% | 29% |
| upside down | 0/30 = 0% | 0% | 0% | 5% | 0% | 0% |
| upside down, 45 to the left | 4/30 = 13% | 8% | 10% | 18% | 13% | 16% |

**30 cm**

| start (your nose = the blunt end) | real | Old start | Dead | Fitted | Hard .31 | Hard .39 |
|---|---|---|---|---|---|---|
| nose down | 16/30 = 53% | 15% | 22% | 46% | 37% | 43% |
| tail down | 16/30 = 53% | 14% | 21% | 51% | 38% | 45% |
| left side down | 12/30 = 40% | 16% | 4% | 49% | 49% | 55% |
| right side down | 13/30 = 43% | 16% | 4% | 49% | 49% | 55% |
| upside down | 11/30 = 37% | 0% | 0% | 47% | 17% | 25% |
| upside down, 45 to the left | 6/30 = 20% | 10% | 10% | 48% | 40% | 45% |

## 5. The weight effect: upright with the weight low, minus with it high

In percentage points: +20 means 20 points more drops upright with the weight low.

| height | body | real | Old start | Dead | Fitted | Hard .31 | Hard .39 |
|---|---|---|---|---|---|---|---|
| 6 cm | E1 (hill) | +20 pts | +19 | +14 | +29 | +32 | +29 |
| 6 cm | E2 (oval) | +26 pts | +21 | +13 | +38 | +39 | +40 |
| 6 cm | E3 (rounded square) | +30 pts | +17 | +24 | +40 | +32 | +36 |
| 30 cm | E1 (hill) | +3 pts | +20 | +15 | +19 | +20 | +14 |
| 30 cm | E2 (oval) | +7 pts | +22 | +11 | +22 | +25 | +6 |
| 30 cm | E3 (rounded square) | +23 pts | +21 | +23 | +37 | +20 | +19 |

## 6. Biggest single misses (Hard .31, the model the 15 cm test is built on)

Each cell is one body, weight and start: 5 drops. With 5 drops the real share is coarse (0, 20, 40 ... 100%), and
even a perfect model would miss a cell by 20-40 points by chance now and then.

**6 cm**

| body | weight | start | real | predicted upright | what really happened |
|---|---|---|---|---|---|
| E3 (rounded square) | low | left side down | 5/5 upright | 42% | upright 100% |
| E3 (rounded square) | high | tail down | 4/5 upright | 28% | upright 80%, upside down 20% |
| E2 (oval) | low | left side down | 0/6 upright | 42% | upside down 83%, on its side 17% |
| E1 (hill) | high | tail down | 2/5 upright | 0% | upside down 60%, upright 40% |
| E2 (oval) | low | tail down | 5/5 upright | 76% | upright 100% |
| E2 (oval) | low | right side down | 1/5 upright | 42% | upside down 40%, upright 20%, on its side 20%, on an end 20% |

**30 cm**

| body | weight | start | real | predicted upright | what really happened |
|---|---|---|---|---|---|
| E1 (hill) | high | tail down | 4/5 upright | 2% | upright 80%, upside down 20% |
| E3 (rounded square) | low | upside down, 45 to the left | 1/5 upright | 84% | upside down 60%, upright 20%, on an end 20% |
| E2 (oval) | high | tail down | 4/5 upright | 27% | upright 80%, upside down 20% |
| E2 (oval) | low | nose down | 0/5 upright | 52% | upside down 60%, on its side 20%, on an end 20% |
| E1 (hill) | low | left side down | 0/5 upright | 50% | upside down 100% |
| E1 (hill) | high | left side down | 0/5 upright | 46% | upside down 80%, on its side 20% |

Figure: `figures/sim_vs_reality.png`, predicted vs real upright share for every cell.
