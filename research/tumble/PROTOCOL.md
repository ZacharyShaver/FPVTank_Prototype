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

### Post hoc 3 (2026-10-14): simulator audit (`audit/AUDIT.md`)
- **The sweep's shell weighed the same and sat at the same height for every shape** (600 g at Z 50). If its mass
  scales with its area and sits at its area centroid, the best tall, wide designs' CoM rises about 40 mm, and their
  P(upright) falls from 0.62-0.68 to 0.33-0.37, no better than the tub (0.39).
  - D's design conclusion ("self-righting needs a tall, peaked top wider than the wheels") came from that
    weightless shell. It holds only if the shell is light for its size.
  - D's surrogate results are unaffected: they measure the GP against the simulator, whatever the simulator models.
  - E is unaffected: the printed bodies carry their real mass.
- Two naming mix-ups were found, with no numbers changed. Contact rebounds at restitution 0.08, which is dead.
- Penetration, face stability, time step, settle rule and registration all passed.

### Post hoc 4 (2026-10-14): correction to post hoc 3
Post hoc 3 overstated the shell bug. Scaling the tub's 600 g by area means 5.6 mm of solid PLA over the whole shell,
far heavier than a printed cover. In `posthoc_cover_weight.py` the tub stays the chassis and the extra shell area is
a cover of a given thickness. The best tall designs then give P(upright):
- 0.53-0.62 at 1-1.5 mm, a realistic print, against the tub's 0.39;
- 0.44-0.49 at 3 mm;
- about the tub's value at 4-5 mm.

So the design rule stands with a condition: a light cover. All of this is the dead-contact simulator and stays
provisional until the bounce is measured.

### Post hoc 5 (2026-10-14): bounce explains the miss, and a prediction for the slow-motion measurement
`posthoc_bounce_fit.py` reran the start-fixed model at six contact damping ratios and scored each against the 181
drops. This is exploratory, because it fits this data.

| Restitution | Brier score |
|---|---|
| 0.13 (the default, dead contact) | 0.861 |
| 0.35 | 0.529 |
| 0.44 | 0.465 |
| **0.56 (best)** | **0.443** |
| 0.72 | 0.575 |

At 0.56 the model matches all three signatures of the miss (predicted / seen):
- stays on its end: 0.10 / 0.09;
- stays on its side: 0.14 / 0.16;
- end drops upright: 0.41 / 0.43.

**Prediction, recorded before the slow-motion video is taken or seen.** E3, mass low, dropped flat on its base from
6 cm onto the same floor:
- the measured restitution (upward speed after the first impact over the speed before) will be **0.4-0.7**,
  most likely about 0.55;
- if it falls outside 0.4-0.7, bounce alone does not explain the miss, and the fitted value is standing in for
  something else, such as coin rattle or release spin.

**Next, also before any 30 cm data are seen:** predictions at 30 cm are committed for the start-fixed model with the
fitted bounce (damping ratio 0.2). After the video, a second set with the measured bounce follows, still before the
30 cm data.

## H4: the 30 cm drops (pre-registered 2026-10-14, before any 30 cm data are seen)
Zach dropped the bodies from 30 cm as well (no video). I haven't seen those results. Several models' predictions for
them are committed before they are shared:
1. `drop_predictions_30cm` (2026-10-13): the old start and dead contact;
2. `drop_predictions_30cm_dead`: the start fixed, dead contact (the control for the bounce);
3. **`drop_predictions_30cm_bounce_fit`: the start fixed, with the bounce fitted to the 6 cm drops (damping ratio 0.2,
   restitution 0.56). This is the main test;**
4. `drop_predictions_30cm_bounce_measured`: the start fixed, with the bounce from the slow-motion video, if the video
   comes before the 30 cm data.

Scoring follows `score_drops.py`'s rules: Brier against the naive predictor, the most likely state, and the mass
control if both masses were run.

**Hypothesis:** model 3 scores a lower Brier than both model 2 and the naive predictor, with bootstrap 95% CIs of
the differences excluding 0. If model 3 is no better than model 2, the 6 cm fit was fitting noise or something
height-specific, not bounce.

### Post hoc 6 (2026-10-14): which shape wins, with a realistic shell (`posthoc_sweep_v2.py`)
Setup: the same 400 designs and seeds, the tub as the chassis plus a 1.5 mm printed cover, with dead contact and
with bounce (damping 0.2, a sensitivity check for the full-size robot, not a measurement). The top 6 of each were
rerun at 1000 drops.

**The same design wins all three variants:** top 211 mm, round 0.13, half-width 169, dz -6.

| Variant | P(upright) | Tub (1000 drops) |
|---|---|---|
| Weightless shell (as the sweep ran) | 0.75 | 0.40 |
| Realistic cover, dead contact | 0.65 | 0.40 |
| Realistic cover, bounce | 0.67 | 0.40 |

The runner-up in all three is 196 / 0.19 / 162 / -19 (0.62-0.74). Wide domes don't place.

**Wording correction.** Earlier text here called the best tops "peaked (round 0.1-0.4)". In `shell_points`, a low
`round` is a *small edge round*: the top is a flat plateau with a steep, rounded shoulder. So the winner is a tall,
boxy shell with rounded top edges, wider than the wheels, and with the weight low. It is not a peak. A dome
(round 1.0) is the rounded one, and it does worse.

The printed E3 is this design (210 / 0.15 / 165 / -10). In the real 6 cm drops it came to rest upright more often
than the tub: weight low 15/30 vs 10/30, weight high 6/30 vs 4/30. That is consistent with the simulation, though
not significant on its own (Fisher p about 0.3).

### Post hoc 5, result (2026-10-14): the slow-motion measurement, preliminary
Video `IMG_E1630.MOV`: Apple's edited export, every 240 fps frame kept and played at 30 fps. It shows 4 flat drops
and 4 tail-down drops of E3 (weight low) from 6 cm, filmed side-on and close.
- **The bodies rock rather than hop.** Even a level release lands a few degrees tilted: one edge strikes first, the
  body pivots onto its base and rocks.
- Tracking: the body's upper face, matched by template (`measure_bounce.bottom_by_template`). Drops 3 and 4 have
  template dropouts and are not used.
- The two clean drops rise about 13 px after impact out of a 75-83 px drop, which is restitution about 0.4 if it
  were all hop. But the larger rise comes 60 ms after impact and looks like rocking. The hop at impact is about 3 px,
  restitution about 0.2.
- **Measured flat-drop restitution: roughly 0.2-0.4.** That is at or below the bottom of the predicted 0.4-0.7.
- **Reading:** the prediction is not confirmed. The fitted 0.55 is likely higher than the real normal bounce. So
  bounce alone does not explain the miss: edge-first landings that turn into rocking do part of it, and the fitted
  contact setting was standing in for that. This is the outcome recorded in advance as "something else is involved".
- **Next:** a cleaner measurement needs either a release with no tilt (a jig) or a shape that can't rock, such as a
  printed PLA sphere of the same walls and infill, dropped onto the same floor.

H4, model 4: `drop_predictions_30cm_bounce_measured` uses the start fix and the preliminary slow-motion bounce
(restitution about 0.3, damping ratio 0.48). It was committed before any 30 cm data were seen, which completes H4's
set of four models.

H4, amendment (2026-10-14, before any 30 cm data are seen or retaken): Zach says the first 30 cm session's heights
were guessed by eye, "about a foot" each time, with no mark. He will redo it with a marked 30 cm.
- **The redo is H4's primary data**, scored against the four committed models by the same rules.
- The first session, if shared, is scored as secondary data (height by eye) and reported as such.
- Redo protocol: release with the lowest point at a marked 30 cm; the same six starts x 5; Zach's nose/tail
  convention; the same floor; the pocket taped with two crossed strips, checked after each body; a drop where the
  coins come out is recorded and redone. A regular (30 fps) video if possible, for checking the readings.

## H4 results (2026-10-14): the 30 cm redo, 180 drops, against four models committed before it
Scoring: `score_30cm.py`, committed before it ran. The readings of the sheet were fixed and committed before
scoring; one mark ("c") was later corrected by Zach to x, and the run was rescored.

| Model (committed before the data) | Brier | minus naive (95% CI) | top state right |
|---|---|---|---|
| naive ("stays on the face it was dropped on") | 1.506 | | |
| 1: old start, dead contact | 0.871 | -0.63 (-0.74 to -0.53) | 0.37 |
| 2: start fixed, dead contact | 1.156 | -0.35 (-0.43 to -0.27) | 0.28 |
| **3: start fixed, bounce fitted at 6 cm** | **0.634** | **-0.87 (-1.01 to -0.73)** | **0.47** |
| 4: start fixed, bounce measured (~0.3) | 0.784 | -0.72 (-0.84 to -0.61) | 0.42 |

**H4 supported.** On drops it had never seen, from 5x the height, the bounce model beats the dead-contact model by
0.52 (95% CI 0.40 to 0.64) and the naive predictor by 0.87. The measured-bounce model also beats dead contact
(0.37, CI 0.29 to 0.46), but by less than the fitted one.

What is still wrong:
- **The mass control is weaker in reality than the model says.** P(upright) for low vs high:

  | Body | Predicted | Seen | Fisher p |
  |---|---|---|---|
  | E1 | 0.51 vs 0.32 | 10/30 vs 9/30 | 1.0 |
  | E2 | 0.61 vs 0.39 | 16/30 vs 14/30 | 0.80 |
  | E3 | 0.71 vs 0.34 | 16/30 vs 9/30 | 0.12 |

  All three point the same way, but from 30 cm the outcome depends on the mass far less than predicted.
- Mass low, the model over-predicts upright: from upside down it predicts 0.62, and 0.40 was seen. Mass high,
  it under-predicts upright after end drops: 0.30-0.39 predicted, 0.53 seen.
- Again, the old start (bug and all) scores better than the fixed start with dead contact. The randomising bug
  stands in for missing randomness in the dead model, as it did at 6 cm.

Reading: adding bounce was the right direction, and it carries to a new height. The model is now too confident
about mass. Real 30 cm drops randomise more than the model (rocking, rattling coins, hand release), which pulls
both masses toward the same outcomes.

Naming note (2026-10-14): this file's "H4" (the 30 cm drops) is part of the sprint plan's H3 (sim-to-real), and is
called H3b in the write-up. The sprint plan's H4 (the AI-in-the-loop cycle time) is unrelated. Commits before this
note say "H4" for the 30 cm test.

### Post hoc 7 (2026-10-14): a hard floor with the measured bounce explains both heights, unfitted
MuJoCo's default contact (time constant 0.02 s) lets a body sink 7.4 mm into the floor on a 6 cm drop and 17 mm at
30 cm (C13, L12, found by Zach in the viewer). `posthoc_stiff.py` makes the floor hard (time constant 0.002 s,
0.3-0.5 mm) and sets its bounce from the slow-motion measurement (restitution ~0.3, damping ratio 0.35). No part of
it is fitted to drop outcomes.

| Model | Brier, 6 cm | Brier, 30 cm |
|---|---|---|
| naive | 1.293 | 1.506 |
| soft floor, dead | 0.861 | 1.156 |
| soft floor, bounce fitted at 6 cm | 0.443 | 0.634 |
| **hard floor, bounce measured** | **0.472** | **0.638** |

Its 30 cm mass control is closer to what was seen (E2 0.54 vs 0.48 predicted, 16/30 vs 14/30 seen). Reading: the
fitted bounce worked mostly by making the floor harder. The physical fix is a hard floor plus the measured
restitution. Both data sets have been seen, so this is post hoc; H3c below tests it on new drops.

## H3c: the hard floor on new drops at 15 cm (pre-registered 2026-10-14, before any 15 cm drop)
Three models' predictions are committed for drops from a marked 15 cm, a height not yet tested:
1. `drop_predictions_15cm_hard_floor`: start fixed, hard floor (time constant 0.002 s), bounce measured (~0.3).
   **The main test.**
2. `drop_predictions_15cm_dead`: start fixed, MuJoCo's default soft, dead contact. The control.
3. `drop_predictions_15cm_bounce_fit`: start fixed, soft floor with the bounce fitted at 6 cm. For comparison.

**Protocol:** as the 30 cm redo, with the lowest point at a marked 15 cm (5.9 in); the six starts x 5; Zach's
nose/tail; the pocket taped crossed; mass low for all three bodies, then mass high if time allows; video.

**Hypothesis:** model 1 scores a lower Brier than model 2 and than naive, with paired bootstrap 95% CIs excluding 0.
No direction is predicted between models 1 and 3.

**Scoring:** `score_30cm.py`'s rules, with these files. If the PLA ball measures a different restitution before the
15 cm drops, a hard-floor set with that value is committed too, before the drops, and the slow-motion set stays the
main test.

### Post hoc 7, correction (2026-10-14): the hard floor wasn't converged at 0.5 ms (C14)
A time-step check (`audit/hard_floor_convergence.py`) showed the stiff contact injecting energy at 0.5 ms. Flips from
upside-down starts fall from 34% to 6% (E3) and from 28% to 7% (E1 at 45 degrees) at 0.1 ms. Rerun at 0.1 ms with
the same bounce (restitution 0.31, damping 0.45 at that step):

| Model | Brier, 6 cm | Brier, 30 cm |
|---|---|---|
| hard floor, 0.5 ms (as reported above) | 0.472 | 0.638 |
| **hard floor, 0.1 ms (converged)** | **0.483** | **0.693** |
| soft floor, bounce fitted | 0.443 | 0.634 |
| soft floor, dead | 0.861 | 1.156 |

The unconverged step flattered the 30 cm score by 0.055. The converged hard floor still closes most of the gap,
without fitting, but less well than the fitted bounce at 30 cm. The soft-floor bounce model (H3b's winner) is
converged at 0.5 ms (`audit/soft_bounce_convergence.py`: E3 within sampling noise, E1 within 0.13).

## H3c amendment (2026-10-14, before any 15 cm drop)
The main model committed for H3c (`drop_predictions_15cm_hard_floor`, a hard floor at 0.5 ms) is not converged
(C14). It stays recorded and will be scored, but it is no longer the primary test. Added before any 15 cm drop:
- `drop_predictions_15cm_hard_floor_converged`: hard floor at 0.1 ms, bounce 0.31 (E3 slow motion). **Now primary.**
- `drop_predictions_15cm_hard_floor_ball`: hard floor at 0.1 ms, bounce ~0.55. This is the PLA ball's slow-motion
  value, which is rough (0.45-0.65), because the camera was too close for a reliable drop height.

**Primary hypothesis:** the converged hard floor (0.31) beats the dead soft floor and naive, with paired bootstrap 95%
CIs excluding 0.

**Secondary, no direction predicted:** the 0.31 hard floor vs the 0.55 one (which bounce fits), and vs the fitted
soft bounce.

## H3c second amendment (2026-10-14, before any 15 cm drop): the PLA ball, measured
A second slow-motion video of the ball (`IMG_1642.MOV`) was filmed side-on from floor level, against a black board,
far enough back to see the whole drop. `measure_ball.py` fits each drop as one ballistic path, and the ball's own
40 mm width checks the scale: gravity comes out at 9.8-11.0 m/s^2. Results are in `results/ball_restitution.md`.
- **First impact: restitution 0.39 mean (95% CI 0.33-0.46), range 0.24-0.61, over 12 drops.** The drops were from
  7-12 cm, with impacts at 1.15-1.54 m/s. The spread is real: every fit is clean, and two centroid methods agree to
  0.005. Its cause is not known. Candidates are which part of the 2-wall, 10%-infill shell strikes, and where on the
  floor it lands.
- The rough 0.55 from the first ball video was too high. 0.39 is close to E3's 0.31.
- **Slower bounces are much livelier: median 0.78 at 0.2-0.9 m/s** (23 later bounces). MuJoCo's contact gives one
  restitution at every speed (0.31-0.32 from 6 to 30 cm at damping 0.45). So every model here under-bounces the slow
  rocking impacts after a landing. H3c does not test this; it stays an open question.

Added before any 15 cm drop:
- `drop_predictions_15cm_hard_floor_ball2`: hard floor at 0.1 ms, damping 0.35, which gives restitution 0.38-0.40
  from 6 to 30 cm (`scale_model.bounce_curve`). This is the ball's measured 0.39.

The primary test is unchanged: the 0.31 hard floor. The 0.55 set stays recorded and is scored. **Secondary, no
direction predicted:** the 0.39 hard floor against the 0.31 one, the 0.55 one and the fitted soft bounce.

### Post hoc 8 (2026-10-14): the ball's bounce on the hard floor, against the seen drops
The 0.39 hard floor (damping 0.35, 0.1 ms) run at 6 and 30 cm (`drop_predictions_6cm_hard_floor_ball2`,
`drop_predictions_30cm_hard_floor_ball2`). Both data sets have been seen, so this is not a test; nothing was fitted.
Brier: **0.456 at 6 cm, 0.672 at 30 cm**. That is between the 0.31 hard floor (0.483, 0.693) and the soft floor
fitted at 6 cm (0.443, 0.634), and the best of the unfitted models. All models side by side, by body, weight and
start: `results/sim_vs_reality.md` (`sim_vs_reality.py`). The 6 cm fitted set is now saved per drop
(`drop_predictions_6cm_bounce_fit`), and it reproduces post hoc 3's 0.443.

### Post hoc 9 (2026-10-15): past the sweep's edge, and the surrogate at the best designs (C15)
- **The sweep's range held the best design.** The best design pushed past each limit (`explore_edge.py`, cover +
  bounce, 1000 drops each): P(upright) peaks at half-width 175-200 (0.68) and falls past it (0.63 at 300-350).
  It plateaus at top 200-220 (0.67) and falls steeply past it (0.56 at 300 mm, 0.41 at 400). Width removes side rests
  up to about the body's length (339.5 mm), then makes upside down more stable. Height removes upside-down rests,
  then adds side and end rests. The dead-contact runs show the same shape.
- **H2's surrogate is overconfident at the best designs** (C15, `audit/surrogate_peak_check.py`). Its 90% intervals
  cover 86.8% of held-out designs overall, as recorded, but only 1 of the 6 best, and it puts all 6 about 5 points
  too low. A second, independent GP (`surrogate_gp.py`, Matern kernel) does the same on all three sweep variants.
  H2's recorded result stands; the overall check was the wrong place to look. The design conclusions rest on the
  1000-drop reruns, not on surrogate values. The surrogate ranks candidates well (its top two were the simulator's
  top two in every variant) but undervalues the winner.

## H3c third amendment (2026-10-17, before any 15 cm drop): released from a drop stand
The 15 cm drops will be released from a printed drop stand (`drop_stand.py`) instead of by hand. A pinch clamp holds
the body still in its start, a gauge sets its lowest point at 150 mm, and pinching the clamp's handles snaps both
jaws open together. The starts are still set by hand in the clamp. This changes the release, not the models: every
committed 15 cm prediction stays as it is, with its +-15 degree hand jitter, and the scoring is unchanged. Expected
effect: less height error and less release randomness than a hand drop. If the real release is now steadier than
the models assume, that costs every model in the same direction. It is recorded here so that any such effect is
read as a known change, not found after the fact.
