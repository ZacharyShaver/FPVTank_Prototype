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

## Results (2026-10-13, after the protocol above)
Ground truth: 400 designs x 200 drops, 74 s on 20 cores. P(upright) ranged 0.26 to 0.76 (median 0.37). Top height
mattered most (r +0.67), then CoM height (-0.33), peak (-0.21) and width (+0.17). The best designs were tall
(190-220), peaked (round 0.1-0.4), wide, with a low CoM.

| H2 as recorded | Result | |
|---|---|---|
| RMSE < 0.05 at 120 training designs | 0.039 (280 held out) | met |
| 90% intervals cover 85-95% | 86.8% | met |
| Uncertainty choice beats random | 0.041 vs 0.045 RMSE at 45 designs; equal by 85 | small advantage |
| Gate at 0.6: decides >= half, <= 2% wrong | 266/280 decided, 2 wrong (0.8%), 14 sent to simulation | met |
| Out-of-range design gets a wider interval | 0.16 vs the widest in range, 0.06 | met |
| Hidden friction (0.4x) caught by 8 sentinels | 0/8 flagged (control 0/8): friction moved P by <= 0.04 | not met |

Post hoc (`posthoc_sentinels.py`, labelled as such): a 3x harder spin flagged 0/8 (mean shift 0.029) and 150 mm
wheels flagged 1/8 (0.039). In this regime P(upright) is set by geometry and mass. Eight sentinels at 200 drops
can't see a physics change smaller than about 0.05 in P. As a control, the sentinel check is weak. The same lesson
as `check_failures.csv` C10: a control has to be shown able to fail.

## H3 results (2026-10-14; `score_drops.py`, scoring choices committed before it ran)
181 drops from 6 cm: 3 bodies x mass low and high, 6 starts x 5 drops (one group has 6). Mass high was run first
(Zach loaded coins first), against the card's order; the predictions for both were committed before either run.
Deviations, all recorded in `data/drops/README.md` before scoring:
- E1's mass-high landings were read from the video (agreeing with the sheet on 24 of 27);
- Zach's nose and tail are the reverse of the model's, so they're scored by which end physically pointed down;
- left and right are merged, because the bodies are mirror-symmetric.

| Pre-registered test | Result | |
|---|---|---|
| Brier score, model vs naive (all 181) | 0.578 vs 1.293; difference -0.715 (95% CI -0.833 to -0.591) | met |
| ... in each of the 6 body x mass groups | the model is better in all 6; no CI crosses 0 | met |
| Most likely state was the one seen | 0.51 vs naive 0.36; mass high 0.37-0.80; mass low 0.30-0.40, about naive's level | partly |
| Control: P(upright) shifts low vs high the predicted way | same direction for all 3 bodies; E2 p = 0.013, E3 p = 0.029, E1 p = 0.13 (Fisher) | met, 2 of 3 significant |
| The prediction's uncertainty (friction 0.65x-1.5x) covers the misses | it moves the Brier score only 0.558-0.585; the misses below are far larger | not met |

**Where the model is wrong, in the same direction in all 6 groups:**
- **The real bodies right themselves more often than predicted.** P(upright) predicted vs observed:
  - E1: 0.21 vs 0.33 (low), 0.02 vs 0.13 (high);
  - E2: 0.21 vs 0.29 (low), 0.01 vs 0.03 (high);
  - E3: 0.17 vs 0.50 (low), 0.00 vs 0.20 (high).
- **They come to rest on a side less often:** for example E1 low, 0.25 predicted vs 0.07 observed.

**Reading:** the simulation is useful, much better than the naive guess, and it tracks a change in mass. But its
error is systematic, and its own uncertainty band (friction) doesn't contain that error, so it is overconfident.
The candidates for what it misses are untested, and post hoc from here:
- how the PLA mass sits in a print (walls and infill, not a uniform solid);
- contact softness and bounce;
- release jitter and spin;
- the real edges of the print.

### Post hoc 1 (2026-10-14): the printed mass layout does not explain the miss
`posthoc_print_mass.py` rebuilds each body's mass, centre of mass and inertia from the sliced G-code: every
extrusion line and arc, split into pieces of at most 1 mm, with supports and brim excluded.
- Registration checks: no plastic falls outside the hull, the tops agree within 0.5 mm, and the weights agree with
  the slicer's within 1%.
- Control: given the old uniform layout, the new code path reproduces the committed predictions exactly.
- Result: with the walls-and-infill layout, the centre of mass moves less than 1 mm, P(upright) moves by at most
  0.007, and the overall Brier score goes from 0.578 to 0.570. The shell-versus-solid hypothesis is ruled out.
- Still untested: bounce (MuJoCo's default contact is critically damped, so nothing rebounds; a PLA print on a
  wood floor does), release jitter and spin, and the real edges.

### Post hoc 2 (2026-10-14): the committed predictions dropped the wrong faces
Looking at where the misses were, by start (`posthoc_attitude_fix.py`), led to a bug in `scale_model.predict`. The
random heading was applied as a turn about the body's own z axis *after* the tilt. For the nose-down, tail-down and
both side starts, that axis is horizontal. Each of those four starts was really an even mix of both ends and both
sides (25% each); only upside down was right, and the 45-degree start was partly mixed. The main sweep (D) uses
uniformly random orientations and is unaffected.
- Fix: the heading turns about the world's vertical (`world_yaw=True`). `world_yaw=False` reproduces the committed
  predictions exactly. `start_check()` now asserts that the intended face is down at release. Its control, the
  committed code, fails it on 5 of 6 starts.
- **With the fix, the model gets worse: Brier 0.578 to 0.861** (naive 1.293; still better, CI -0.52 to -0.35). The
  pre-registered score was better than the model deserved, because the bug happened to mimic how much a real fall
  randomizes.
- The fixed model says a body dropped on an end or side mostly stays there: on its end 60% of the time (seen 7-13%),
  on its side 76-92% (seen 16-17%). Real drops from 6 cm knock it off its narrow ends and sides; simulated ones don't.
- Reading: the contact model is too dead. MuJoCo's default contact is critically damped and nothing rebounds, while
  the coins rattle and PLA bounces on a wood floor. The printed-mass layout still makes no difference (0.845).
- What follows has to be honest about tuning. Any bounce setting fitted to these 181 drops is exploratory. The test
  is a prediction made before new data are seen. Two such data sets are available: Zach's 30 cm drops, which aren't
  shared yet, and a slow-motion bounce measurement that sets the parameter without fitting.
