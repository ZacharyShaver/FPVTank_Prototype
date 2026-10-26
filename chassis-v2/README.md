# Chassis v2: the Scorpion body

Live state of the chassis work. Started 2026-10-04 from Zach's Fusion design TEST-PRINT-2 (exports in
`../chassis-v1/from_fusion/`). Nothing here is printed yet. Picking this up in a new session: `HANDOFF.md`.

All the variations side by side: `python chassis-v2/lineup.py` -> `out/lineup.html`, the "Scorpion Chassis Line-up" page
(https://claude.ai/artifact/RqAqdoCnZVcJBjrPsQxY62, 2026-10-08). It reuses the meshes the other pages embed (rerun a
page's script first if its design changed) and builds the four body options' meshes once (`out/_lineup_variants.pkl`).
Its sizes are measured one way for all thirteen and match each page's own.

## The Trainer, step layout (2026-10-25, from a simulated search)

`SCORPION_WHEELS=step python chassis-v2/trainer.py` (~1.5 min, plus ~1.5 if the four-wheel run is stale) ->
`out/trainerstep.html`, the "Scorpion Step Trainer" page (https://claude.ai/artifact/8KVjUJZpHXWszfcMZ3DKmw),
`trainerstep.json`, `trainerstep_*.png`. Zach: "turn the best-under-380 mm layout into a chassis-v2 change". The layout
is `research/tumble/chassis3.py`'s best at the Trainer's length for driving down steps: Ø92 wheels, axles X 53 / -77
(wheelbase 130), the belly 54 off the ground (was 32). Each pod's flange is a 5 mm drop plate up the wall to the tub's
top, on a full-height pad with inserts at Z 22 and 47; the axle hangs 8 under the floor. The packs stay (the search's
+28 runs them into the nose wall). `SCORPION_STEP_R=55` builds it on the Trainer's own Ø110 wheels, which scored the
same (`research/results/chassis3/sensitivity.json`).

Down a step and onto its wheels (`research/tumble/built3.py`, these meshes, hard floor, 640 runs): 0.514 -> 0.627
(the search's stand-in: 0.641). Crests 21 -> 40+ deg, 95 g lighter, 14 shorter. Costs: tips forward on a downhill at
34 deg (was 52), back at 50 (59); the pods 23 off the ground (32); gaps 70 -> 60 mm; 7 rests besides upright (4); the
head first to land in 8.4 % of falls (5.3); 0.96 m/s at 200 rpm (1.15). 27 checks: 13 clear, 14 controls read, four
rows new (front tyre against rear, 38 mm apart; the drop plates' 16 screws in the pads' inserts; each with a control). The four-wheel
Trainer's JSON reproduces exactly after the edits to `wheels.py` and `rugged.py`. Open: the drop plate isn't
load-checked; screws assumed from the Trainer's list.

## The Trainer on six wheels (2026-10-09, a brainstorm)

`SCORPION_WHEELS=6 python chassis-v2/trainer.py` (~2 min, plus ~2.5 if the four-wheel run is stale) ->
`out/trainer6.html`, the "Scorpion Six-Wheel Trainer" page (https://claude.ai/artifact/FHjPoawZiuExTJx56TNrds),
`trainer6.json`, `trainer6_*.png`; entry 14 in the line-up. Zach: "a version of the trainer with 6 wheels". Its
control is the four-wheel Trainer (`out/trainer.json`, rerun first when older than `wheels.py`, `rugged.py`,
`trainer.py`, `hull.py` or the hull meshes).

The same module six times (`wheels.py`, `SIX`). Three Ø110 wheels don't fit the wall's straight run (232 long), so
Ø100 wheels on a 216 wheelbase: axles X 118 / 10 / -98 (the middle one under the centre of mass), Z 25 so the ground
and body stay put, 8 mm between tyres. The front pods sit past the wall's end, so their pads fill back 12 mm to the
slanted nose (`rugged.wheel_pad`, a cheek in the tub), trimmed to 1 under the claws' roots. The front leads enter at
X 105. New in both trainer runs: rough ground in side view (`trainer.side2d`, `rest`, `terrain`): the robot settles
where its centre of mass is lowest at each 4 mm step; the sharpest ridge it crosses with only the wheels touching,
and how far a wheel drops into gaps. Results against four wheels: ridges 21 -> 40+ deg sides (the middle wheel holds
the belly up; grip gives out first), tips back 59 -> 63, each motor's hill torque 74 % and turning 66 %; gaps no
better (70 mm both: one end wheel always drops in, and the wheels are smaller); 3219 -> 3937 g; lowest point under the
pods 32 -> 27; length and width unchanged (342, 308). 27 checks, part with part: 14 clear, 13 controls read. The
four-wheel and v2-control JSONs reproduce exactly, and so does `rugged.json` (v1).

## Guard arm E with the Crawler's flippers (2026-10-09, a brainstorm)

`python chassis-v2/guard_flippers.py` (~2 min) -> `out/guard_flippers.html`, the "Scorpion Guard Arm Flippers" page
(https://claude.ai/artifact/EhiwGigGnKB1c5NqWLUTFQ), `guard_flippers.json`. Zach: "can you do guard arm e with the
crawlers flippers". A belted flipper outboard of each track, turning on the v2 front idler's hollow boss (extended 7)
on a 6704. The drive legs_v2.py planned (a shaft through the boss from the hull) has no room: on the idler axis, between
the tub's slanted nose and the claw, a gear can be ~7 mm in radius. So each flipper carries an N20 gearmotor* whose worm
walks round a worm wheel fixed on the boss end (self-locking, behind a slip clutch); the leads come in through the
hollow boss. The belts roll free. Three AS5600s (yaw + 2 flippers) share a fixed I2C address: the flippers get the AS5600L.

Same day, Zach: the Crawler's pincer prongs on the flipper tips go (they were only styling; the flipper grew 110 -> 132
so the TPU belt keeps the reach), and the "green cover on the top is very thin and brittle, not large enough to carry the
little red thing". The fender (a 2.4 mm sheet 63 out from the hull, held on one edge) became a closed box over each track,
tapered like a wing: 24 deep at the hull, 8 at the outer edge (a flat 24 deep box made deep side rests: 22-24 deg to
leave). ~35x stronger and ~350x stiffer at the root (beam estimate), 85 -> 152 g for both. The red thing was the stop
button the rugged body drew; its switch body (~30 deep) never fit under the fender (2-10 mm). It's off for now:
`place_estop` searched the tail slope and found no spot clear of the hatch, the arm's turntable, the air intake and the
power parts under it by more than ~2 mm. Zach thought it was an antenna; he's open to buttons, but not there.

Results against Guard arm E: turned down, the flippers pitch the robot 27 deg and lift the claws 69 -> 153 mm off the
ground at <= 5 kg.cm a drive (~38* stall); rests with the arm guarding 5 -> 3, all shallow; with the arm dead a flipper
rights it only from the nose (1 of 3: flippers push fore and aft; the flat fender let it do one side rest too); with
the arm working all 5 right, upside down after turning the flippers to 240 deg (the stowed ones block the arm's push).
Costs 275 -> 319 wide, +185 g. 22 checks, part with part: 14 clear, 8 controls read.

## Nose section: the head's wire pocket in the body (2026-10-12)

`python chassis-v2/nose.py` (~15 s; SCORPION_LEGS=wheels by default) -> `out/nose.html` (the "Scorpion Nose Section"
page, https://claude.ai/artifact/K6qDNPDQu8XsK9gkdeZ6vA), `out/nose_section_A.stl`, `out/deck_ring_A.stl`,
`out/nose.json`. The head v2 bench stand's pocket (`head-v2/fixes/bench_stand.py`) built into the Trainer's nose floor,
two ways (A under the floor, B the head 12 up), with the current head from the fit view's data. The deck ring clamps the
base's rim and screws to four posts; the walls forward of the glacis rise to the deck (rugged.tub()'s ledges floated
4.2 over them). Sliced as one plate, G-code `nose_A_ring_orca_PLA_3h34m` (head-v2/out/gcode/), uploaded to the K2.
Open: A or B; the deck's side lids sit 1.8 under the ring's top; rugged.py itself still has the floating ledges.

## Current: the Trainer, on wheels for training (2026-10-05, a brainstorm)

`python chassis-v2/trainer.py` (~1.5 min; needs `out/_hull_meshes.npz` from `hull.py`) -> `out/trainer.html`, the
"Scorpion Trainer" page (https://claude.ai/artifact/KWmWBHLrBfb8fyQPo2zzG8), `trainer_*.png`, `trainer.json`. Its
control, the same body on the v2 tracks with no cage and no arm, runs in its own process (`--control`, with
`SCORPION_LEGS=v2`) -> `out/trainer_control.json`, `trainer_before.png`; rebuilt when `rugged.py`, `legs_v2.py`,
`hull.py` or the hull meshes are newer.

Zach: the fenders over the tracks go; for training, at least for now, wheels: tracks are too complicated, and
training has to run en masse. `wheels.py` is the geometry: four identical corner modules. The nose holds the head and
both packs, so a front motor can't lie across the hull the way the v2 rear ones did. Every motor rides outside, in a
printed pod on a pad on the hull wall (4 M3 into inserts; the gearbox face screws to the pod's lip). A dish wheel
(Ø110 × 46, printed TPU tyre with chevron lugs) wraps back over it on the 6 mm D shaft. Axles at X 91 and −93 (the
wall's straight run), Z 30; ground −25; rigid. `rugged.py` with `SCORPION_LEGS=wheels`: no fenders, no cage, the v1
insides (no motors in the hull), leads in through grommets over the packs, the e-stop on the right side lid (15 off
the cradle's sweep). Against the tracks: 5 bodies and 4 contacts in a simulator (tracks ~120 and ~70*), tips back
50 -> 59°, approach 38 -> 40° (departure clear: the rear wheels stand past the tail), belly 33 -> 32. Costs: +490 g
(four 205 g motors), 275 -> 308 wide. 4 rests besides upright, as on the tracks without the cage: it doesn't right
itself. 23 checks, part against part: 11 clear, 12 controls read. Open questions are on the page: is 308 wide OK
(narrower options listed), simulator or real fleet, 37 or 25 mm motors, drivers, arm.

Found on the way: stacking a tyre and its rim (they share a surface) in one mesh read a false 180 cm³ in the voxel
check, so the trainer's checks compare part with part (`docs/lessons/2026-10-05-stacked-copies-hide-overlaps.md`).

## The hull redesign (2026-10-04, a brainstorm; the rugged body builds on its tub, legs and head placement)

`python chassis-v2/hull.py` (about 1 minute). It writes to `out/`:
- `hull.html`: the "Scorpion Hull Redesign" page, https://claude.ai/artifact/AJsyz9mp1vGRPPhpaVqPm3
- `hull_parts.step`: every new part as a named exact solid, in his frame, to open in Fusion
- `hull_checks.json`: the fit table (1 mm voxels; 13 pairs clear, 7 controls read above zero)
- `hull_sheet.png`: four stills

A new body built round the v1 legs (fit unmodified, the only thing Zach fixed) and everything the robot carries:
- **Tub**: floor, walls, nose, the pods' pads, a spine the packs slide out on, ledges. Packs on the floor
  46.5 aft of where TEST-PRINT-2 had them (X -99..42); door in the back wall.
- **Head on the floor in the nose**: the coil base stands on the floor (coil deck Z 49.4, turret deck Z 56),
  so the ball tops out 151 over the ground (was 182) and the lens sits at 120 (was 150).
- **Carapace** behind the head (front face X 50, outside the cradle's 43.7 sweep): sponsons with the ESCs
  over their motors, brain bay under a lift-off hatch, power bay and back panel aft.
- **Level tracks**: the pods' hole pattern on the tub is turned 1.82 deg, cancelling the v1 outer frame's
  1.83 deg, so the tracks' ground run is level (Z -18.9) and the pan axis is vertical.
- **Claws**: pincer bumpers with a light between the jaws, 40 past the ball. **Tail**: WiFi antenna in the stinger.

Guesses are listed on the page (ESC and UBEC sizes, the motor can, the HAT+ height, head axis X 100).
The accessory rail is gone: Zach's "planned rail section" was most likely the tail section (the August body
brief's tail, which was to carry the Pi, the PCA9685 and the power feed). Open: is the tail an antenna boom
(as drawn) or a section that houses electronics? The base needs 4 feet added in the generator to bolt to the floor.

## Option E: the guard arm instead of the cage (2026-10-05, a brainstorm)

`python chassis-v2/guard_arm.py` (~1 min; v2 legs, `rugged.CAGE = False`) -> `out/guard_arm.html`, the "Scorpion Guard
Arm" page, `guard_*.png`, `guard_arm.json`. Compares against `out/rugged_v2.json` (the caged body on v2 legs).

Zach: let the tail be the cage, through software; it can prevent the roll too; make a purpose-built arm as a new option.
The arm (`L1 140`, `L2 175`, parallelogram elbow as his option B, 35 kg·cm* shoulder behind a slip clutch, N20 worm
yaw* + AS5600, jaw caps in TPU as the brace foot, camera on the tool's inner face) drives stowed as an arch over the
head, its jaws on a peg on the left claw. Checked: nothing fragile is ever first to touch; braced, it tips sideways at
77 deg (58 free) and back at 75 (39 with the arm out back); from all 7 rests of the bare robot the arm finds a push
within 34 % of a servo's stall (`righting`: a search over the joints, centre line kept out of the ground and the
robot); holding 100 g out is 20 % of the shoulder. Against the cage: 275 wide (296), 336 long (389), but 262 tall
driving (228) and +177 g, and righting now needs the software and the servos. The tip-monitor spec is on the page.
Without the cage the intake hood moves beside the turntable, under its sweep.

## On hold for training: v2 legs under the rugged body (2026-10-05, a brainstorm)

Zach, later the same day: wheels for training, at least for now (the Trainer, above). Kept as the tracked option.

`python chassis-v2/legs_v2.py` (the leg alone: side sketch `out/legs_v2_side.png`, `legs_v2.json`), then
`SCORPION_LEGS=v2 python chassis-v2/rugged.py` (~1.5 min) -> `out/legs_v2.html`, the "Scorpion v2 Legs" page
(https://claude.ai/artifact/5eJExsLRzBxyuhxjJs7oBq), `rugged_v2_*.png`, `rugged_v2.json`. It compares against the
v1 run's `out/rugged.json`, so run `rugged.py` (v1) first after any body change.

Zach: longer contact, wider track, suspension, flipper-ready; a new printed TPU track; open to new motors; design
first, then he buys. `legs_v2.py`: ground 7 lower than v1 (G0 -26); 46 links of 14 mm, 52 wide, 3 mm band with
centre horns (guide and drive); rear sprocket 11 teeth on the gearmotor's axis; 5 road wheel pairs on trailing arms
with TPU spring pads (12 up / 5 down); raised front idler on a hollow 20 mm boss (6704), its slot the tensioner,
flippers later on its outer end; one frame plate a side, 10 M3 screws into the hull. The motor (a 37 mm 30:1-class
gearmotor*, datasheet sizes) lies across the tail, gearbox through the hull wall; Z 30 is the only axis height
where it clears the floor and the top run clears the fender. In `rugged.py` (`LEGS='v2'`): fender 68, the tunnel
ends ahead of the motors, the power parts go over them, no tail ramp, a forked brow bar (one bar left a face-down rest
with the wider track). Results vs the same body on v1 legs: contact 77 -> 190, tip back 31 -> 48 deg (arm: 19 -> 40),
approach/departure 20/20 -> 38/34, lowest belly 26 -> 33; one extra rest (face-down, 1.6 deg to leave); costs
+510 g (tracks ~158 g each), width 270 -> 296, cage 209 -> 228. Shopping list in `legs_v2.SHOP`.

## The rugged body (2026-10-05, a brainstorm; on v1 legs by default)

`python chassis-v2/rugged.py` (~1.5 min; needs `out/_hull_meshes.npz` from `hull.py`; `--no-render` skips the stills)
-> `out/rugged.html`, the "Scorpion Rugged Body" page (https://claude.ai/artifact/YSHMrCeCHjszr5XPFwSxTq),
`rugged_sheet.png`, `rugged_fig.png`, `rugged.json`.

Zach: keep iterating the body for ruggedness (falls, rolls, knock-overs), weight placed for steep hills, dust
blockers, longer if useful, a belly shaped for tall rocks; flippers in a later round. Every claim is measured
against the tail-arms body (`tail_arms.body()`), weighed the same way:
- **Rolls back upright**: skirts outside the tracks and two roll hoops lie on one outline, a spiral round the
  centre of mass that starts past the tracks' bottom edges (`Outline`). Stable rests of the whole robot's convex
  hull (`rest_states`, knife-edges under 1.5 deg dropped): old body 9, rugged 1 (upright, 20 deg to leave).
  The outline is sized from the computed centre of mass (`assemble` iterates it), so the masses matter.
- **Falls**: the first part to touch over 4000 directions (`first_contact`): fragile (head, whip antenna, e-stop)
  16 % -> 0 %. A brow bar from the front hoop over the ball; the antenna inside the rear hoop; TPU bumpers.
- **Climbing**: packs on edge in bays along the walls, beside the head; ESCs on the floor; deck 15 lower; the body
  15 forward on the legs (`BODY_DX`: the pods' holes move aft in it). Tip back 18 -> 31 deg, forward 43 -> 32;
  the v1 track's 77 mm flat contact limits it. An arm at the tail costs 12 deg.
- **Rocks**: a tunnel down the belly (roof 47 over the ground), the nose floor raised 10 with the head, a 28 deg
  rear ramp. Approach 17 -> 20 deg, departure 14 -> 20.
- **Dust**: gaskets at both seams, a TPU wiper ring onto the drum, motor-window boots, grommets, filtered intake.
Guesses on the page: densities, a printed hoop's strength, ESC and UBEC sizes. The head is raised 10 (a change to
how the base sits, not to the head's parts).

Found on the way: voxel checks that stack copies (12 pan angles in one mesh) undercount, because the parity scan
cancels where copies overlap. hull.py and tail_arms.py now check each angle on its own (results unchanged; the
controls read 3420 and 741 mm3 instead of 476 and 203). `docs/lessons/2026-10-05-stacked-copies-hide-overlaps.md`.

## Tail arms on the Crawler + Workhorse mix (2026-10-04, a brainstorm)

`python chassis-v2/tail_arms.py` (~2 min; needs `out/_hull_meshes.npz` from `hull.py`; `--no-render` skips the
stills) -> `out/tail_arms.html`, the "Scorpion Tail Arms" page (https://claude.ai/artifact/KWbW5Huixhb2FaC8Vyh4C4),
`arms_sheet.png`, `arms_reach.png`, `arms.json`, `arms_checks.json`.

Zach: v1 legs, a mix of the Crawler and the Workhorse, the arm coming out of the tail ("almost slope up"); the
head turns 360, so the arm need not reach over the front; the arm carries its own camera and a gripper.
Body: hull.py's tub, legs, head and insides under a new carapace (sloped glacis, roll hoop, cargo bed with a stow
post, the tail rising 30 deg to a pedestal at X -104 for the arm's turntable). Four arms, every pose fit-checked
(1 mm voxels, a control each): A Scorpion (option B parallelogram), B Telescope (luffing boom + slide), C Folder
(servos at the joints), D Lift (parallel four-bar, jaws always down). Reach is an IK grid against the robot's
outline. Masses, servo torques, the arm camera and the 8 A arm UBEC are guesses (listed on the page).
Found on the way: hull.py's UBEC overlaps its Pi switch by 300 mm3 (hull.py never checked power parts against each
other); here the UBEC moves 6 mm forward, and the INA219 and WiFi dongle move to make room for the yaw servo.

## Picture: ideal tracks and a full-size tail (2026-10-04)

`python chassis-v2/ideal_render.py` (VTK, offscreen) writes `out/ideal_front.png`, `ideal_claws.png`,
`ideal_side.png`, `ideal_rear.png` and `ideal_sheet.png`. A visual only, not fit-checked: the hull redesign
with tracks that are not the v1 legs (full length, raised front idler, 5 road wheels on trailing arms, 2
return rollers, 60 wide with grousers, 40 mm under the floor), a 7-segment tail arching over the back, and
bigger pincers reaching past the tracks.

Default (`SCORPION_TAIL=arm2`): the 2026-09-13 two-joint arm, option B, plain (no tail styling) and scaled
~2.2x so it reaches over the head and past the claws from the rear deck: upper arm 110 (twin plates),
forearm 290 (carbon tube), crank = rear lever 26, pushrod 110. Held-still torque with 100 g: elbow ~3.9 kg.cm
(DS3218: 19), shoulder ~2.2 (MG996R: 9.4). Two poses: `reach` (tip X 212, Z 122, gripper down in front of the
claws) and `stance` (high over the back). Writes `ideal_arm2_*.png` and `ideal_arm2_sheet.png`.

With `SCORPION_TAIL=arm` the tail is the 2026-09-13 arm at its original size, styled as a tail: 50 mm upper
arm + 130 mm forearm, option B (elbow servo coaxial with the shoulder, parallelogram pushrod: crank 22 = the
forearm's rear lever, pushrod 50 = the upper arm). Base yaw MG996R inside the power bay under a turntable on a
lazy-susan bearing; shoulder MG996R and elbow DS3218 on the U-bracket's cheeks under a fairing that turns with
it; the forearm styled as four tail segments; an MG90D gripper in the orange stinger. Writes `ideal_arm_*.png`. Zach: not that one ("not the biometric tail").
`SCORPION_TAIL=segments` gives the plain segmented tail (`ideal_*.png`). The e-stop moves to the left sponson
top, outside the fairing's 72 mm sweep.

## Body options (2026-10-04, a brainstorm)

`python chassis-v2/variants.py` (~3 min; renders + numbers to `out/var_*.png`, `variants.json`), then
`python chassis-v2/variants_page.py` -> `out/variants.html`, the "Scorpion Body Options" page
(https://claude.ai/artifact/QkTmtQ5ynNvGW9TRn96QpJ). Same robot inside, three bodies:
- **Scout**: low and sleek; one flat deck at the well's top, the August brief's low tail bay for the Pi, small tracks.
- **Crawler**: terrain; big trapezoid tracks, pincer-tipped flippers, sloped armour, skid plate, roll hoop.
- **Workhorse**: the long two-joint arm mid-ship (reaches the ground in front), cargo bed, packs aft.
Plus the baseline (the redesign with ideal tracks and the arm at the back). Masses are guesses (listed in
`variants.py` MASS); tip angles are static; nothing in these is fit-checked.

## Superseded: the cover concept (2026-10-04)

`concept.py` -> `out/concept.html` (https://claude.ai/artifact/4dUf3XN7jVCCy4KCCQkULT), `concept_tools_for_fusion.step`.
It kept TEST-PRINT-2 and wrapped new parts round it (5 CUT_ bodies for his body). Zach: the body didn't have
to stay. Kept because `hull.py` reuses its leg placement, meshes and checks, and because it records how the
legs were registered:
- The pod's six inserts (file X 73.45/125/176.55, Y 76.5/118.5) land on TEST-PRINT-2's six side holes
  (X -41.56/9.99/61.54, Z 11.4/53.4). The pods go on upside down from their print orientation: the only
  proper placement that puts both motor ribs at the rear (drive end) and drops the track side 15 mm.
- The outer frame's six counterbored holes land on the pod's open-side bosses, a pattern turned 1.83 deg in
  the pod's file. Sprocket axles come from the outer frame's axle holes.
