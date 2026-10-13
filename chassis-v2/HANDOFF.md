# Chassis v2 handoff (2026-10-05, evening)

For the next chassis session. Read `CLAUDE.md`, then this, then `README.md` here (a section per step, newest
first). Memories that matter: `chassis-head-integration`, `redesign-freely-in-brainstorms`,
`arm-concept-long-forearm-pushrod`, `hardware-on-hand`. This replaces the 2026-10-04 handoff; that state is in the
README's older sections.

## Start the session by asking Zach

1. What's printing and what the last print showed. Pan coil set 7 is printed and assembled: "an improvement, it's
   smoother now"; the real verdict waits for the 6809ZZ (it was due 2026-10-05). Another session owns the head; check
   `head-v2/NOTES.md` before touching head parts.
2. His answers to the open questions below. He was exploring, not deciding: every page is a brainstorm.
3. What he has now: servos, bearings, screws (CLAUDE.md: ask before sizing joints). For the legs and the guard arm he
   said "design, then I buy", so their parts are datasheet guesses with shopping lists.

## Where it stands (all pages private to Zach)

| Step | Script | Page |
|---|---|---|
| Hull redesign on the v1 legs (fit-checked) | `hull.py` | [Scorpion Hull Redesign](https://claude.ai/artifact/AJsyz9mp1vGRPPhpaVqPm3) |
| Four tail arms A–D on a Crawler + Workhorse body | `tail_arms.py` | [Scorpion Tail Arms](https://claude.ai/artifact/KWbW5Huixhb2FaC8Vyh4C4) |
| Rugged body on the v1 legs: self-righting cage, bumpers, seals | `rugged.py` | [Scorpion Rugged Body](https://claude.ai/artifact/YSHMrCeCHjszr5XPFwSxTq) |
| v2 legs under the rugged body | `legs_v2.py`, `SCORPION_LEGS=v2 rugged.py` | [Scorpion v2 Legs](https://claude.ai/artifact/5eJExsLRzBxyuhxjJs7oBq) |
| Option E: the guard arm replaces the cage | `guard_arm.py` | [Scorpion Guard Arm](https://claude.ai/artifact/7YKi72Deeouei58y1rWtzR) |
| The Trainer: four wheels, no fenders, for training | `wheels.py`, `trainer.py` | [Scorpion Trainer](https://claude.ai/artifact/KWmWBHLrBfb8fyQPo2zzG8) |
| Guard arm E with the Crawler's flippers (2026-10-09) | `guard_flippers.py` | [Scorpion Guard Arm Flippers](https://claude.ai/artifact/EhiwGigGnKB1c5NqWLUTFQ) |
| The Trainer on six wheels (2026-10-09) | `SCORPION_WHEELS=6 trainer.py` | [Scorpion Six-Wheel Trainer](https://claude.ai/artifact/FHjPoawZiuExTJx56TNrds) |
| All fourteen variations in one 3D line-up (2026-10-08, +1 on 10-09) | `lineup.py` | [Scorpion Chassis Line-up](https://claude.ai/artifact/RqAqdoCnZVcJBjrPsQxY62) |

The latest design is the last row: the rugged body (no cage, no fenders, no arm fitted) on four identical wheel
modules. The v2 tracks are on hold for training, not dropped.

## Zach's calls, this round

- Evening: "the side portions covering the top of the tracks have to go ... for training ... at least for now ... we
  have to use wheels, tracks get too complicated and we need to be able to run en masse to train." -> the Trainer.
  Whether "en masse" means simulator copies, real robots or both is asked on the page.

- Legs: first "v1 legs?", then v2 legs. Goals: longer contact, wider track, suspension, flipper-ready. A new printed
  TPU track. Open to new motors. Flippers come in a later round.
- Body: a mix of the Crawler and the Workhorse; the arm comes out of the tail; "it should almost slope up". The head
  turns 360, so the arm need not reach over the front. The arm carries its own camera and a gripper.
- Ruggedness: falls, rolling, knock-overs; weight placed for steep hills; dust blockers; longer is OK; belly room for
  rocks.
- "What if the tail acted as the cage ... through software"; "it can prevent a roll from even happening too"; "make a
  purpose built arm for this as a new option" -> option E.
- The four arm designs A–D: "good options, I'll have to think more". No arm is chosen.

## Numbers that hold (re-run before trusting)

| | Rugged, v1 legs | Rugged, v2 legs + cage | v2 legs + guard arm E |
|---|---|---|---|
| Rests after a tumble | 1 (upright) | 2 (one is 1.6 deg from a knife edge) | 7 bare rests, all righted by the arm (<= 34 % of stall) |
| Fragile first contact | 0 % | 0 % | 0 % |
| Tips back / forward | 31 / 32 deg | 48 / 56 | 44 / 53 (arm in guard); braced behind 75 |
| Width / height | 270 / 209 | 296 / 228 | 275 / 262 (the arch) |
| Mass* | 2440 g | 2950 g | 3125 g (with the arm) |

v2 legs: flat contact 77 -> 190 mm, 46 links of 14 mm, 52 wide, approach / departure 38 / 34 deg, lowest belly 33 mm.

## Open questions for Zach

- Flippers (on their page): 319 wide OK, or a belt-less flipper (~290*)? The motor on the flipper, leads through the
  hollow boss: OK? How many 6704s are left (these take 2 more)? First test: one flipper on a bench stand.
- Stop button: where? (A pod on the back facing aft; on a track cover near the back in a raised housing; the tail slope
  after moving the air intake and WiFi dongle; or none.) It's off the model until he picks; `place_estop` checks a spot.
- Trainer (on its page): 308 wide OK? (The motors ride outside the hull because the nose is full; narrower: worm
  motors along the wall ~294, a front motor box ahead of the head ~262 wide and ~40 longer, or two motors and chains.)
  Simulator or real fleet, and build its MuJoCo model next? 37 or 25 mm gearmotors (terrain)? ESC per side with the Pi
  counting 4 encoders, or a 4-channel driver? Which arm, if any? First print: one corner on the motor he buys.

- Arm: A–D or E? If E: is the guard rest (a peg on the left claw, arm down past the ball's front-left) OK in the
  camera's view? Is a worm-drive yaw (self-locking, slower) OK?
- Software: write the tip-monitor spec for `../FPVTank_Control` next? Ask before touching that repo. The robot has no
  IMU yet (BNO085 is on the arm's list).
- v2 legs: which gearmotor (Pololu 37D 30:1 with encoder, or a JGB37-520)? Buy one and caliper it before printing the
  frame. Track 52 or 44 wide (44 saves ~16 width, ~8 cage)? Rear drive (motors in the tail) OK?
- Rugged body: is the cage size OK, or let the arm / flippers do the righting? Packs out the top (carapace and
  side lids off) instead of the back: OK?
- "Slope up": the body, the arm at rest, or both? Both are drawn.
- First test prints: a road wheel arm + spring pad + 10 track links + sprocket; the guard arm's shoulder with its
  clutch and stop on a bench stand.

## Guesses (marked * on the pages)

- ESC 46 x 34 x 18: INJORA publishes no size; the Hobbywing 1060 it clones is 36.5 x 32 x 18. The INJORA 540 can is
  35.8 x 52.8 (Amazon). The UBEC isn't bought.
- Gearmotor: 37 mm gearbox 22 long, motor 34.5 x 33, encoder 11, 205 g, 200 rpm and 8–9 kg·cm at 7.4 V.
- Servos: DS3235 35, DS3218 21, MG996R 11, MG90S 2 kg·cm stall; N20 worm yaw ~20 kg·cm.
- Masses: printed walls 90 % solid, tubes 45 %, lumps 40 %; packs 300 g, head 210 g. The rugged outline is sized from
  the centre of mass, so real weights matter.
- Righting assumes the TPU jaw caps grip and ignores bounce; it follows the arm's centre line, not its solids.

## Running things

Order matters: `hull.py` writes `out/_hull_meshes.npz`, which the rest read; a v2 run compares with the v1 run's
`out/rugged.json`; `guard_arm.py` compares with `out/rugged_v2.json`.

    python chassis-v2/hull.py                                # ~1 min
    python chassis-v2/rugged.py                              # ~1.5 min, v1 legs  -> rugged.html, rugged.json
    python chassis-v2/legs_v2.py                             # the leg alone      -> legs_v2_side.png
    SCORPION_LEGS=v2 python chassis-v2/rugged.py             # ~1.5 min           -> legs_v2.html, rugged_v2.json
    python chassis-v2/guard_arm.py                           # ~1 min (v2, no cage) -> guard_arm.html
    python chassis-v2/tail_arms.py                           # ~2 min             -> tail_arms.html
    python chassis-v2/trainer.py                             # ~1.5 min (wheels; runs its v2 control itself) -> trainer.html
    python chassis-v2/guard_flippers.py                      # ~2 min (v2, no cage; reads out/guard_arm.json) -> guard_flippers.html
    SCORPION_WHEELS=6 python chassis-v2/trainer.py           # ~2 min (reruns the four-wheel one when stale) -> trainer6.html
    python chassis-v2/lineup.py                              # seconds (40 s more when variants.py changed) -> lineup.html, last

`--no-render` skips the VTK stills. `rugged.CAGE = False` drops the hoops, brow bar and skirts (`guard_arm.py` sets
it). Preview: `.claude/launch.json` `chassis-v2-out` serves `chassis-v2/out` on port 8767; the local server sends no
charset, so text looks garbled there but not on the published page.

## Gotchas found this round

- Voxel checks with stacked copies undercount: the parity scan cancels where copies overlap (12 pan angles in one
  mesh read a seventh of the truth). Check copies one by one and sum.
  `docs/lessons/2026-10-05-stacked-copies-hide-overlaps.md`. Fixed in `hull.py`, `tail_arms.py`, `rugged.py`; the
  superseded `concept.py` still stacks.
- Mesh vertices miss flat faces: profiles and sections need rays (`rugged.ray_up`) or a full projection
  (`rugged.headon`), not vertices near a plane.
- CadQuery `Workplane('XZ').extrude(-d)` goes to +Y. A belly cut built 100 mm off the side made every control read zero.
- `cq.Solid.makeCone` with equal radii throws; give the second radius a hair less.
- Rest states: a face the robot leaves with under 1.5 deg of tilt is a mesh sliver (`MIN_TILT`). A shape whose distance
  from the centre of mass grows from the track edges to the top rolls back (`rugged.Outline`, a spiral, not a circle
  centred on the centre of mass: that made every face neutral).
- `hull.py`'s UBEC overlaps its Pi switch by 300 mm³ (it never checked power parts against each other). Fixed in
  `rugged.py`'s layout, not in `hull.py`.
- The guard arm's fairing turns with the yaw: check each pose with its own base (`guard_arm.base_tris`).
- In this shell, heredocs containing `\'` broke the Bash tool: write a patch script with the Write tool and run it.
- CadQuery `cut()` on a Workplane whose stack is empty (a cut that removed everything) cuts the PARENT solid instead,
  so the next cut brought back the whole uncut box. The six-wheel cheek did this on the middle and rear pads: +72 g
  inside the hull, caught by "power parts vs tub". Check `.solids().size()` before cutting again (`rugged.wheel_pad`).
- Parts that touch (a tyre on its rim) must not be stacked into one mesh for a voxel check either: the shared surface
  merges into one crossing and the parity flips (a false 180 cm³). `trainer.checks` compares part with part.
- `rugged.py` is shared: after editing it, check that v1 and v2 still reproduce `rugged.json` / `rugged_v2.json`
  (climb, ends, belly, mass, rests). Done after the wheels edits: identical.

## Not committed

New: `chassis-v2/` (all of it, now with `wheels.py`, `trainer.py`, `trainer_template.html`; `out/` is ignored), `docs/lessons/2026-10-05-stacked-copies-hide-overlaps.md`,
`chassis-v1/from_fusion/`, `chassis-v1/head_placement.py` and its template, `reference/pca9685/`.
Edited: `README.md`, `chassis-v1/README.md`, `.claude/launch.json` (two preview entries).
The head-v2 changes in `git status` belong to other sessions. Commit only when Zach asks; never push without asking.
