# Workstream D and E protocol (written 2026-10-13, before any surrogate or physical results)

## Question
After a tumble, does the robot come to rest upright? How does that depend on its shell (top height, how peaked
the top is, how wide the shell is relative to the wheels) and on its centre-of-mass height?

## What we already learned building the simulation (2026-10-13, exploratory, 200 drops per design)
- With the Trainer's 110 mm wheels, outside the body, the pill shell's top shape made no difference. P(upright)
  stayed at 0.34–0.38 for tops from 66 to 140 mm. The wheels (top at 85) and the head's ball (top at 142) form the
  hull, and the robot lands on whichever big face it falls toward.
- A wide, gently rounded dome is stable upside down, like a weeble: its top's centre of curvature lies beyond the
  centre of mass. Tops up to 180 mm, even 170 mm wide, still came to rest inverted.
- Only a tall, peaked top on a shell wide enough to cover the wheels changed the outcome: top 200, round 0.3,
  width 170 gave 0.68 (40 drops). A lower floor friction (mu 0.3) cut it to 0.55.

## H2: the surrogate (recorded before fitting)
- The ground truth is 400 Sobol-sampled designs over top 66–220, round 0.1–1.0, width 65.75–175, dz −20..+40, at
  200 drops each (`sweep.py`).
- A Gaussian process trained on 120 designs will predict the held-out designs with RMSE below 0.05, and its 90%
  intervals will contain the truth 85–95% of the time.
- Choosing designs by uncertainty will reach a given RMSE with fewer simulations than choosing them at random.
- Gated on P(upright) >= 0.6, the surrogate will decide at least half the designs itself, with at most 2% of them
  wrong.
- The surrogate's own controls:
  - a design far outside the training range must come back with a wider interval than any in-range design;
  - with friction changed (which the surrogate isn't given), sentinel simulations at 8 designs must fall outside
    its intervals more often than with the friction it was trained on.

## H3: physical validation (E)
- Three printed scale models, chosen after the sweep to span low, middle and high predicted P(upright).
- **The predictions for each model and each starting orientation are committed before Zach drops anything.**
- The protocol for each model:
  - 30 drops: five each from six starting attitudes (nose down, tail down, left side down, right side down,
    upside down, and 45° between upside down and left side), released from a fixed height onto the same table.
  - The simulation runs the same six attitudes with ±15° of hand jitter, at the scale model's own mass properties.
- Scoring:
  - the Brier score of the predicted outcome probabilities against what happened;
  - compared with a naive predictor ("it stays on the face it was dropped on");
  - and the share of trials where the most likely predicted state is the one observed.
- The physical control: move the quarters to raise the centre of mass and repeat. The prediction has to shift the
  way the simulation says, and the observed outcomes have to follow.

## Change log
- 2026-10-13, before the sweep: fixed the shell's ends. They were half-circles of radius equal to the half-width, so
  widening the shell to cover the wheels also lengthened it, to 548 mm at width 170. Now the ends are half-ellipses
  that keep the tub's 339.5 mm length at any width. The exploratory width-170 numbers above used the old shape. With
  the new one, top 200 / round 0.3 / width 170 gave 0.72 (40 drops). The sweep and everything after use the fixed
  shape.
