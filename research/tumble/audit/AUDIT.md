# Simulator audit (2026-10-14)

Zach asked for a check of the tumble simulator after the start-attitude bug (PROTOCOL.md post hoc 2). I read every
line of tumble.py, scale_model.py, sweep.py, surrogate.py, predict_drops.py, score_drops.py and the post hoc scripts,
then ran the physics tests below. Each fix keeps the old behaviour behind a switch, and the default reproduces what
was committed.

## Bugs that change results

| # | Where | What | Effect | Status |
|---|---|---|---|---|
| B1 | `scale_model.predict` | the random heading turned the body about its own z axis after the tilt | E's end-down and side-down starts were 25/25/25/25 mixes of ends and sides; Brier 0.578 -> 0.861 when fixed | fixed (`world_yaw`), `start_check()` with a failing control |
| B2 | `tumble.mass_model` (the sweep, D) | the shell is 600 g at Z 50 for every shape: a 210 mm dome as light and as low as the 66 mm tub | **the tall-shape advantage is real but depends on a light shell.** With the tub kept as the chassis and the extra shell area a cover (`posthoc_cover_weight.py`), the best tall designs give P(upright) 0.62-0.68 weightless, 0.53-0.62 at 1-1.5 mm of solid PLA (a realistic print), 0.44-0.49 at 3 mm, and the tub's 0.39 at about 4-5 mm. The wide dome helps little at any weight (0.41-0.46). (First pass, corrected: spreading the tub's 600 g over the whole shell is 5.6 mm of solid wall, which erased the advantage; that overstated it.) | option `SHELL_MASS` ('fixed', 'area', 'cover'); default 'fixed' reproduces the sweep |

B2 does not touch E: the printed bodies are real solids, and their simulation uses their own mass. It also leaves
D's surrogate statistics standing. Those measure how well the GP stands in for the simulator, and they hold
whatever the simulator gets wrong. What changes is the design claim. It needs a condition: a tall, peaked top
helps if the cover stays light, roughly under 3 mm of solid wall. Every P(upright) here is still from the
dead-contact simulator that E showed under-predicts tumbling, so these are provisional until the bounce is measured.

## Wrong names (no number changes)

| # | Where | What |
|---|---|---|
| N1 | `tumble.classify` | +X up (the head end up) is called "nose down", and the reverse. score_drops maps by the physical end. |
| N2 | `scale_model.ATTITUDES` | "left side down" puts -Y (the right side) down, and the reverse. The bodies are mirror-symmetric; the scoring merges the two. |

## Modelling limits (documented, not bugs)

- **Dead contact.** Dropped flat from 6 cm, a body rebounds 0.4 mm (restitution 0.08). The contact damping ratio
  sets it: 0.3 gives 0.33. Real PLA on wood bounces more, and the coins rattle. This is the main suspect for E's
  remaining miss: simulated bodies stay on ends and sides that real drops knock them off.
- **Shell friction does nothing.** The engine takes the larger of two touching surfaces' frictions, so the floor's
  0.6 always beats the shell's 0.4.
- Coins, spacer and wheel modules are point masses: they have no inertia of their own, and the coins don't rattle.
- The scale-model drops start from rest. Real hands add a little spin; the sweep uses up to 3 rad/s.
- The sweep's "tumble" starts 5 mm off the floor with spin. That models a tip-over, not a fall.
- The surrogate's intervals leave out its fitted extra-noise term. Coverage still came out at 86.8%, inside the
  85-95% target.

## Tests that passed

| Test | Result |
|---|---|
| Resting penetration into the floor (`audit_sim.py pen`) | 0.02 mm at the default contact |
| Face stability, sim vs hand calculation, 3 bodies x 2 masses x 6 faces (`static`) | agree in all 36. Where the CoM is outside the support, the sim rolls to a nearby tilted rest of the same class. Ends are narrow: E1 balances on an end with 2.7 mm to spare (mass low) |
| Time step 1 / 0.5 / 0.25 ms (`audit_conv.py`) | identical |
| Settle rule: 0.12 s vs 0.5 s still; a 0.3 rad/s knock after settling | identical / within 0.03 |
| Head cradle inside the printed hull | yes, by 7-29 mm (full scale) |
| Printed-mass registration (`posthoc_print_mass.py`) | no plastic outside the hull, tops within 0.5 mm, mass within 1% |
| Defaults reproduce committed outputs | committed predictions (`world_yaw=False`); a committed sweep design (fixed shell) |
