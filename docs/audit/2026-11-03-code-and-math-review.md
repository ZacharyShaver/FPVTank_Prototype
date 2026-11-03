# Code and math review, 2026-11-03

Zach asked for bug and code-quality hunting while the Trainer's tub printed, with the math read as a physicist and a
statistician would. The review covered:
- `gauges/`: the sim's robot model, the drive and contact, G1-G8, the weights, the course and the FEM;
- `tools/`;
- the cluster-bootstrap CIs in `research/tumble`;
- pyflakes over the whole repo.

The results stored before these fixes (the course's `runs.jsonl`, the drops and durability runs) haven't been re-run.

## Fixed

Each fix has a check with a control.

| # | Bug | Fix and check | What it moves |
|---|---|---|---|
| 1 | **The tyre and bumper springs weren't in N/mm.** MuJoCo's direct `solref` is per unit mass, and `tyre_k` went in as written. A "30 N/mm" tyre was about 15 N/mm on a 2 kg robot (30 × the mass on it). The bumpers came out stiffer than labelled, and their damping ratio came out different too. | `robots.spring_solref(k, zeta, m)` divides by the mass the contact carries: each tyre's share, or the robot for a bumper. `python gauges/robots.py spring`: 0.5 and 2 kg balls stay on the contact 12.80 and 25.70 ms, as a spring's π√(m/k) says (12.83, 25.65). The control, the old conversion, gives 18.20 ms for both. | `snap`, `drops` and `unibody`'s falls (only where `tyre_k` is set; G1-G8 use the hard contact). Landings read harder: +12 % peak on the 3.2 kg box, more on lighter robots. The stored results stand as they ran. |
| 2 | **The course's rocks and ridge gave the tyres ×1 grip.** Tyres have contact priority, so their own 0.9 beat the terrain's 2.25. G8 and G6 run the whole sim at ×2.5. | `course.Rig` adds explicit contact pairs: the tyres, tail and flippers each at their own ×2.5 on the terrain, and the terrain at the floor's ×2.5, as on G6 and G8. `python gauges/course.py grip` (also inside `check`): the tyres meet 2.25 on the rocks and the ridge; the control (no pairs) reads 0.9 on both. | The course and its descriptor fit. On 4 tries the box went 0.21 → 0.25; T3 finished either way. A re-run tells how far the 0.71-0.78 fit moves. |
| 3 | **A two-link tail's elbow servo and second link (91-107 g) were missing** from the robot's mass, its CoM and `unibody`'s drop mass. The sims' bodies always carried them. | `robots.limb_mass` is the one sum; `search.com_all` places each piece along the tail. Check: `robots.py spring`'s last line (control: one link). | Two-link designs' reported mass, static upright share, CoM margin and hills `tip_static`. T3 with a 120 mm second link: 4651 → 4758 g, CoM 8 mm higher. |
| 4 | `search.search_limb` printed an undefined `tag`: a NameError in its first generation. | `C w=...`, as its sibling prints `E w=...`. | Nothing has run it since it broke. |
| 5 | `course.py run` resumed `runs.jsonl` without a code stamp, the fault `tools/stamp.py` was built for. | `stamp.check(path)` before resuming. | The old `runs.jsonl` (no stamp, old grip) now refuses to resume: move it aside, as with `nose_first/`. |

Re-run and passing: `robots.py spring`, `weights.py check`, `gauges.py steps`, `snap.py check`, `drops.py check`,
and a smoke run (T3 with one link, with two links, a climb and a turn each). `course.py check` is long; only its grip
block (`course.py grip`) was run. The geom names added in `robots.xml` (`tyre{i}`, `tail_*`, `flip{i}_*`) sit after `type=`, so the films'
string matches still find them.

## Sim-vs-reality gaps found (not changed: this week's list)

- **The motor is rated at 12 V; the packs are 2S.** `wheels3.MOTOR` (330 rpm, 1.0 N m at the wheel, times the gear
  knob) is the 12 V rating. On 7.4 V both are about 0.62 of that. T3 (gear 2.09): 158 rpm and 2.09 N m in the sim,
  about 97 rpm and 1.29 N m on 2S. That 97 rpm is 0.46 m/s on its 45 mm wheels, below G2's 0.5 m/s set speed. Grip
  needs about 0.46 N m a wheel, so T3 still slips before it stalls. Its speeds (G3's spin, the course, tow) and every
  lighter-geared design change.
- **The sim's drive holds a speed on encoders (KV 4); an RC ESC is open loop.** At a stalled wheel the loop opens the
  throttle all the way. An ESC gives only the set fraction. That matters most at a crawl: G6 runs at 0.15 m/s, where
  T3 on 2S would push 0.42 N m open loop, under the 0.46 grip needs. The JGB37-520s have Hall encoders, so the Pi
  can close the loop (FPVTank_Control), but until then the real crest and slow-speed readings will fall short of the
  sim's.

## Statistics: sound, with notes

- Sound:
  - The random orientations (normalized 4-D Gaussian: uniform on SO(3)).
  - The Wilson interval.
  - The pool-adjacent-violators fit and its interpolation.
  - The timestep check's two-proportion test.
  - The designed weights' threshold property (a design clears every obstacle exactly when its weighted worst rank is at least 1 - 1/w_max).
  - The cluster bootstrap: a ratio estimator over whole clusters, paired by drop.
- **Readings carry two selection biases.** Each takes the better of two directions (a max of two noisy rates, biased
  up) and the worst of three frictions (a min, biased down). Ranks stay fair, since every design gets the same, but a
  bench test should be compared with the per-direction, per-friction rates in the scorecards, not the reading.
- **G1 on the screens is coarse:** 30 falls a friction gives about ±0.15 (95 %) at 0.75, against the 0.75 floor.
- **The course fit reports the mean held-out rho only.** Before calling 0.71-0.78 against 0.40 a difference, report
  the folds' spread or a bootstrap CI of the paired difference.
- `rough.ladder` stops a rung early and counts its untried runs as failed. That pulls the interpolated reading
  slightly toward the lower rung: deterministic and small.
- G3 reads drift as well as the swept circle (already recorded, `course-descriptor` memory).

## Physics: checked and right

- The rotor's reflected inertia: N·Ir in the wheel body (for the gyroscopic term), (N² - N)·Ir as armature, N²·Ir in
  all.
- The motor's torque-speed line.
- Holding the drive 5 ms a tick: the wheel's time constant is about 100 ms, so it's stable.
- Tilted gravity for the hills: tilt is read from the slope's normal.
- The brick element: 2×2×2 Gauss, engineering shear.
- Inertia relief: zero net force and moment.
- The multigrid V-cycle: symmetric, as CG needs.
- The two-link IK.
- Minor, left as is: `robots._stretch_I` drops products of inertia, and it's used only for the 1.5× long control box.
