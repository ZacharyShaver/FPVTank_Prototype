# Scorpion gauges: the requirements, as tests that read a number

Set up 2026-10-26. A gauge is a fixed test that reads one number off any design. The test is set in stone. The
number a design should reach is a lever, and Zach sets it each iteration (the table at the end), because the
levers pull against each other: the E4 shell that always lands upright is 436 mm wide.

Iteration 1 has three gauges, on purpose: fewer things to test, and less doubt about which part made a result
go wrong. More come after the first build and real tests.

```
python gauges/gauges.py            # every design and control under the band -> gauges/out/scorecard.json (~4 min, 30 cores)
python gauges/export.py            # the scorecard as the page's row files, gauges/out/dash/ (the page itself: dashboard.html)
python gauges/gauges.py --quick    # smoke run: 40 falls, 6 tries a step (~75 s)
python gauges/gauges.py --cached   # reuse out/roster.pkl instead of rebuilding the designs from chassis-v2 (~50 s saved)
python gauges/gauges.py port       # the step sim against chassis3's, sharp edge and round
python gauges/robots.py            # the roster: mass and size of each design
```

## Rules

1. A gauge names a capability, never a design. A design may meet it any way it can, limbs and scripted moves
   included.
2. It reads one number under every physics in the band. The reading is the worst of them.
3. Its controls show it can move: a design known to be worse must read worse. A gauge whose control fails is
   not read.
4. The box (below) is read every time, as the baseline. The Scorpion's claim is to beat it where a plain robot
   can't.
5. The sim is trusted only as far as a real test has checked it (each card's Trust line). A real test is run when
   a decision depends on a difference smaller than the gauge's known error, or when the gauge first meets new
   physics.
6. A change to a gauge gets a new ID. The old card stays here, marked superseded.

**The physics band, v1:** chassis3's hard floor (contact time 2 ms, damping 0.35, the ball's measured bounce),
time step 0.2 ms. Friction scaled x0.65, x1 and x1.5 (at x1: floor 0.6, tyres 0.9, body 0.4; MuJoCo takes the
larger of a pair). Drive: wheels3's 37 mm gearmotor* (1.0 N m stall at the wheel, 330 rpm), each side's speed held
by its encoders. * = datasheet guess.

**The box:** the built Trainer's parts and masses (chassis-v2, `SCORPION_LEGS=wheels`) in a plain box, the
bounding box of its body and pods, on the Trainer's wheels. Same mass, CoM and inertia; only the shape is plain.

## G1 Upright after a fall

- **Lever:** survive a fall.
- **Reads:** the share of falls after which it comes to rest on its wheels. Higher is better.
- **Test:** 200 falls per physics. Each starts in a uniformly random orientation, its lowest point 300 mm over a
  flat floor, spinning up to 3 rad/s about each axis, wheels unpowered. A fall ends when the body has been still
  for 0.3 s (8 s at most). The rest state is the body axis nearest world up. A design with a limb then gets 10 s to
  right itself, and the rest state after that counts (2026-10-26, rule 1: limbless designs read as before).
- **Controls:** the E4 weeble reads at least 0.2 above the box; the E4 with 1 kg 30 mm under its roof reads below
  the E4 (the drop tests' coins high).
- **Trust:** printed bodies only. E1–E3 at 6 cm scored Brier 0.58 against naive 1.29, with the real bodies righting
  more often than predicted. E4 landed upright on every drop Zach ran (about half, 2026-10-26). The real robot has
  not been dropped.

## G2 Step up

- **Lever:** vertical climb.
- **Reads:** the tallest step (mm) it drives up square on in 18 of 20 tries, with every lower step passing too.
  Higher is better.
- **Test:** steps from 10 to 150 mm in 10 mm increments. The step's top edge is rounded to 3 mm (see the lesson
  below). The leading end starts 80 mm short of the face, heading within ±10° of square, at 0.5 m/s. It tries
  forwards and in reverse, and the better direction counts at each height. A try succeeds when the CoM has risen
  0.6 of the step, is 120 mm past the face and the robot is on its wheels, within 4 s. A limb's moves count inside
  the same 4 s.
- **Controls:** the box on 70 mm wheels (belly 12 mm) reads below the box. On every design, the tyre's contact
  normal at the edge is within 5° of radial, and over 20° off with the sharp edge
  (`docs/lessons/2026-10-26-a-sharp-step-edge-is-a-wall.md`).
- **Trust:** none yet. Climbing rides on traction, and friction hasn't been measured on a real floor.
- **The tail's reflex (changed 2026-10-27, Zach's go):** stalled means under 15 mm of forward travel in the last
  0.3 s. Stalled nose up (past 12°, riding the face), the tail pushes down behind for 0.9 s and stows. Stalled level,
  it kicks for 0.3 s and looks again. Scripted; a learned policy would replace it. Designs without a limb read exactly
  as before (the box and E4, cell for cell against the scorecard).
- **Why it changed:** with a tail, the ladder had gaps. 12 of the drive finals' 42 ladders passed a height above one
  they failed: T1 at x0.65 climbed 10-30 and 80-100 mm and failed 40-70, so it read 30. Traced, these were two
  failures of the first reflex (push whenever the CoM's speed stayed under 0.05 m/s for 0.15 s), not of the body.
  At 40-50 mm the robot hung at 27-32° nose up without tripping it, so the tail never pushed. At 60-80 mm, about belly
  height, the robot arrives level with its nose caught on the step's lip, and a push lifts the rear and tips the nose
  down into the lip. A kick frees the nose and lets the robot rear up onto the face; the push then carries it over.
  On the drive finalists, worst over the band: T1 50 -> 100 mm, T2 50 -> 90, T7 50 -> 90, T8 60 -> 100. Pushing on
  any stall climbed higher at single frictions (110-140), but never across the band.

## G3 Turn-around space

- **Lever:** maneuverability.
- **Reads:** the diameter (mm) of the circle the robot sweeps while it spins 180° in place. Lower is better. A design
  that can't turn 180° in 6 s reads "can't spin".
- **Test:** flat floor, from rest, one side backward and the other forward at 60 % of no-load speed, both ways; the
  larger counts. The circle is centred where its wheels' centre started and holds every point of the body and tyres.
- **Controls:** the box stretched 1.5x along X reads above the box.
- **Trust:** none yet. How far a skid-steer spin drifts depends on the tyres' scrub on the floor.
- **Doesn't read:** speed, or the narrowest gap it fits through (its width is listed with the costs). Zach
  (2026-10-26): "a meh gauge but fine for now".

## G4 Hill up, G5 Hill down (proposed, 2026-10-27)

Zach asked "how far of a hill it can climb/descend before falling", the designs being top heavy with the tail doing
the righting. Not yet in the scorecard or the searches; read on the shape study (`gauges/hills.py`).
- **Lever:** staying on its wheels on a slope, up (G4) and down (G5).
- **Reads:** the steepest slope (degrees, 5° steps) it drives 2.5 m up (down) in at least 18 of 20 tries without
  tipping (tilt from the slope's normal past 60°, or past 30° at the end), the better direction counting, every
  gentler slope passing. Coming down it must not skid (body outrunning its wheels' rims for 0.2 s, or twice the set
  speed). With the tail stowed no reading may beat the static tip angle, which at constant speed is the exact limit
  (`static_check`).
- **Why 2.5 m:** a design just past its tip angle topples slowly. On 300 mm, T3 passed 45° down, 3° past its static
  angle (42°). On 800 mm, the hills run's search parked designs 0.3-0.9° past theirs: mid-topple at the 800 mm mark,
  over by 1-1.9 m; 90 of its 712 screens beat their static angle (`static_check`'s control). A stop and a 1 s hold
  was tried and dropped: at a set speed of 0 the wheels back-drive and creep, so it read the speed loop (lesson
  `docs/lessons/2026-10-27-a-pass-must-outlast-the-slowest-fall.md`).
- **Test:** the floor with gravity tipped by the slope, square on ±10°, from rest, the set speed (0.5 m/s) ramped up
  over 1 s, the tail stowed (or held at a pose: the tail knob below). Read on a grippy floor (friction x2.5), where
  tyres hold and tipping binds. On the band's floors every design, the box too, slides first: 25° up and 25-30° down
  at x0.65. That slide limit is read beside it and belongs to the tyres, not the design.
- **Controls:** T3 with 1 kg high on its top reads below T3 both ways (30° / 30° against 35° / 40°). Two first
  controls failed. 1 kg at one end: the better direction puts that end uphill, where it steadies the robot. A start
  at full torque: the geared-down drive reared the robot over on launch, and extra weight then helped by slowing it.
- **Tail knob:** the tail's pitch held on the hill. Braced down behind at -30° (a wheelie bar), T3 reads 45° / 45°
  against 35° / 40° stowed, the box's limits; one step steeper it stalls going up. Held level behind, 40° / 45°.
  Straight down (-90°) drops the descent to 15°. (The 300 mm hill's "50° up braced, no pose helps going down" is
  **superseded**.)
- **Grip:** the reading is on grippy ground. On ordinary ground (x1, tyre friction 0.9) T3 reads 35° / 40° and the
  box 30° / 35°: the box is held by its tyres and motor there, and T3, geared 2x down, pushes and brakes harder.
  Top-heaviness costs hills only where the tyres grip more than that.
- **Rollover in a sharp turn: not built.** The hardest skid-steer turn from full speed (one side full back, or
  stopped) tilts T3 0.1-0.3°, and a control geared 5x faster with 1 kg on top under 1°. Skid-steer turns scrub off
  before they push sideways, so the gauge would read nothing. A side slope or a kerb mid-turn is the case to build.
- **Trust:** none yet. Rests on the friction guesses, and on the tail's foot gripping like a tyre.

## Costs (read every time, no target)

Mass, length, width, height, belly clearance.

## The roster, iteration 1

Box, Trainer, Step layout and Six-wheel are chassis-v2's built meshes. The E4 weeble is the sweep's robot
(`research/tumble/tumble.py`) under the E4 shell with a 1.5 mm cover. The guard arm, the tail arms and the tracks
aren't scored yet: none has a sim model of its limb or track.

## Targets, iteration 1 (Zach's call)

The live scorecard is the "Scorpion Gauges" page (a private claude.ai page), filled by
`gauges/export.py` from `out/scorecard.json`.

| Gauge | Box reads (2026-10-26) | Best design (2026-10-26) | Target (Zach, 2026-10-26) |
|---|---|---|---|
| G1 upright after a fall | 0.61 | E4 weeble 0.995 | at least 0.75 |
| G2 step up | 30 mm | Six-wheel 50 mm | as tall as it goes |
| G3 turn-around space | 594 mm | Six-wheel 542 mm | as small as it goes |

G1 is a floor; G2 and G3 are pushed as far as they go, together. Zach on G3: "a meh gauge but fine for now", so it is
the first candidate to supersede.

No design beat the box on all three. The Trainer is a coin flip after a fall (0.45; half its falls end on its back),
below the plain box, which is 167 mm tall all over.

## The body search (current, 2026-10-27)

`SCORPION_SEARCH=search_body python gauges/search.py body`, then `... skin`, then `... finals` (results in
`out/search_body/`, which GAUGES_CURRENT now names). The lean search's process on G2's new step reflex (G2's card),
with the skin's eight shape knobs searched again, 24 in all. Zach, seeing the lean finalists: "the shape of the body
does not change much between these unless its the shell ... it could be another knob we can turn". Without a skin a
design wears the Trainer's body, which has no knobs, and the lean search held the skin's shape at T5's. B was seeded
with the lean and drive searches' fronts and finalists (33 designs).

- The search alone kept the Trainer's body. Its random skins were mostly big (median 4.1 kg, 402 mm wide, wheels
  inside), and its refinements started from skinless elites, so a tight skin was never refined.
- Its finalists put in the tightest skin were 80-130 g lighter and 55 mm shorter, but climbed about 40 mm less: the
  tail's mount follows the hull, and their tails were tuned for the Trainer's body.
- A refinement held to skinned designs (`... skin`, from those tight-skin versions, 998 s) found T5 below. It was still
  improving at its last generation. The lesson for the process: an on/off knob needs a refinement under each setting.

**Finals, against the box's 0.60 / 30 mm / 594 mm:**

| Design | G1 upright | G2 step up | G3 turn | Mass | What it is |
|---|---|---|---|---|---|
| T1 | 1.00 | 70 mm | 375 mm | 3.3 kg | the tightest turner (the lean T1); gear 1.8x, track 113 (repack) |
| T3 | 1.00 | 90 mm | 387 mm | 3.3 kg | Ø86 wheels, gear 1.8x, track 111 (repack) |
| T10 | 1.00 | 100 mm | 403 mm | 3.3 kg | the best on the Trainer's body: Ø84 wheels, gear 1.1x, tail 308 mm at 3.3 N m |
| **T5** | **0.96** | **150 mm (the ladder's top, every friction)** | **403 mm** | 3.6 kg | **the new all-rounder: a 732 g domed skin (360 x 300 x 421), Ø90 wheels, gear 2.1x, track 114 (repack), tail 279 mm at 3.3 N m mounted low (0.43)** |
| T11 | 0.995 | 150 mm | 627 mm | 3.6 kg | the best 150 mm design on the Trainer's body |
| N3 | 0.975 | 50 mm | 599 mm | 3.7 kg | the best with no tail: a skin of its own shape |
| T5, limp tail | 0.78 | 40 mm | 439 mm | | the control |

- T5 climbs 50 mm more than the best skinless design in the same 403 mm turn. Its skin also rights it on its own
  most of the time: limp, it still reads 0.78 upright, but climbs 40 mm.
- The drive search's T10 (0.945 / 90 / 405 on the new reflex, as the lean T12) is superseded as the all-rounder.
- Screen to final: upright -0.012 on average, none dropped more than 0.1.
- T5 is geared about 2x down and its track puts the motors 17 mm into the hull. G3 doesn't read speed, and "repack" is
  a guess that the parts can move.

## The shape study (2026-10-27)

`SCORPION_SEARCH=search_shape python gauges/search.py sweep`, then `... shape`, then `... finals`; then
`python gauges/shape_sheet.py` (the picture sheet) and `python gauges/view.py search_shape` (page "Scorpion Body
Shapes"). Results in `out/search_shape/`. Zach: "with the tail
covering most of what the sobol shape was giving us lets see what body shape can give us for climb and
maneuverability ... lock some knobs at a constant". So everything but the skin's ten shape knobs is held at T5's
(wheels, drive, insides, tail). The tail's mount is pinned where T5 has it, because it otherwise follows the hull: a
shape that ends short of it carries it on a bracket, and one that reaches past it has a slot. The skins run from the
tightest the parts allow to a little bigger than T5's (half-width to 200 mm; the tyres' outer faces are at 137).

**One knob at a time** (`shape_sheet.png`, the rest at T5's shape, 3 seeds each):
- Climb has a cliff at the nose. With the nose's front about 197 mm ahead of centre, T5's platform climbs 50-60 mm;
  at about 205 mm and beyond, 140-150. Reach forward and centre both show it at the same place. The nose has to meet
  the step's face ahead of the wheels and ride up it. The widest section's height also matters (best near 160), and
  so does the bottom below it (more climbs better).
- Turn grows with length: reach forward past about 210, reach back past about 160, and a boxier plan.
- Upright sags with a short nose (0.81 at 120 mm) and a very tall dome (0.89-0.90). The tail does most of the righting.

**Finals, against the box's 0.60 / 30 mm / 594 mm** (1,534 designs screened in 1,908 s):

| Design | G1 upright | G2 step up | G3 turn | Mass | What it is |
|---|---|---|---|---|---|
| **T3** | **1.00** | **150 mm (every friction)** | **381 mm** | 3.4 kg | **a 485 g skin no wider than the wheels (348 x 274), its top 232 mm up: low, with a short top (72 mm above the widest section)** |
| T2 | 1.00 | 140 mm | 379 mm | 3.4 kg | a 471 g skin |
| T5 (its own skin) | 0.96 | 150 mm | 402 mm | 3.6 kg | the reference: a 732 g dome, its top 345 mm up |
| T5 on the Trainer body | 1.00 | 90 mm | 441 mm | 3.3 kg | the same platform without a skin |
| T3, limp tail | 0.68 | 40 mm | 432 mm | | the control |

- On one platform, the shape alone is worth 60 mm of climb and 60 mm of turn over the Trainer's body. T3 beats T5's
  own skin on all three gauges and is 250 g lighter: the best design so far.
- **T3 sits on the cliff.** A nose 10 mm shorter climbs 90-100 mm, 20 mm shorter 50 mm. A nose 10-20 mm longer keeps
  150 mm and turns 19-33 mm wider. The search parks designs on the edge, because the shortest nose that still climbs
  turns tightest. A real nose wants margin: print it 10-20 mm longer, or score a design by its worst over a small
  change in shape.

**Hills** (G4, G5 above; `python gauges/hills_sheet.py` draws `hills_sheet.png`), friction x2.5, the 2.5 m hill,
tail stowed:

| Design | Up | Down |
|---|---|---|
| T3 | 35° | 40° |
| T2, T1 | 35° | 40° |
| T5 (its own skin) | 35° | 35° |
| T5 on the Trainer body | 40° | 40° |
| Box, Trainer | 45° (then they stall) | 45° (then they slide) |
| T3, 1 kg high on top | 30° | 30° |

- On grippy ground the skinned, top-heavy designs tip 5-10° before the low box stalls or slides. On ordinary ground
  (x1) they don't: T3 reads 35° / 40°, the box 30° / 35°.
- The shape moves the hills by about ±5°: across 70 one-knob shapes, 30-40° up and 35-40° down.
- The tail braced behind at -30° takes T3 to the box's 45° / 45°, and most shapes with it (63 of 71 up, 66 down).
- The first readings, on 300 mm (T3 35° / 45°, the box 45° / 50°) and 800 mm hills, are **superseded**: a design
  just past its tip angle toppled too slowly to fail in time.

## The hills run (2026-10-27)

`SCORPION_SEARCH=search_hills python gauges/hills.py sweep`, then `... search` (B, then `refine`), `... rehill` (after
the hill went to 2.5 m) and `... finals`; `python gauges/hills_run_sheet.py` draws `hills_run_sheet.png`. Results in
`out/search_hills/`. The hill gauges found the descent set by the locked wheelbase and centre of mass, and Zach said
"unlock those yes". So the wheels' size (R), the wheelbase's centre (xw) and tyre gap (gap), and the packs' place
(dxp, dzp) are searched; everything else is held at T3's (its skin, on T5's platform and tail, the tail's mount
pinned). The screen is the lean screen plus both hills at x2.5 in 6 tries, tail stowed: 712 designs. Refinements: the
descent alone; the descent keeping T3's step and turn (step at least 140 mm, turn at most 420 mm); both hills, kept.
The kept runs found one feasible design in B (T3 itself), so a miss scores by how far it misses, and they were seeded
with the sweep's bigger wheels.

**One knob at a time** (3 seeds each):
- The descent follows the static tip angle, rounded down to 5°. The packs' height moved nothing, but its range moves
  the CoM only 4 mm (83-87 mm); the CoM's height itself costs hill (below).
- Bigger wheels: Ø110 reads 40° / 40° with the step kept and the turn 26 mm wider. Past Ø130 the motor stalls uphill,
  and at Ø170 the robot stops landing upright (0.38).
- A longer wheelbase, the wheels moved off centre, or the packs moved back: 45-55° down, paid for in the step (to
  40-60 mm, the nose cliff) or the turn (to 520-620 mm).

**Finals** (full gauges; hills at 20 tries, x2.5, 2.5 m), against the box's 0.60 / 30 mm / 594 mm and 45° / 45°:

| Design | G1 upright | G2 step up | G3 turn | Hills, tail stowed | Tail braced at -30° | What changed from T3 |
|---|---|---|---|---|---|---|
| T3 | 1.00 | 150 mm | 392 mm | 35° / 40° | 45° / 45° | |
| H5 | 1.00 | 150 mm | 419 mm | 40° / 40° | 45° / 45° | Ø99 wheels (from 90), wheelbase 169 (from 152) |
| H1 | 1.00 | 60 mm | 429 mm | 40° / 45° | 45° / 45° | Ø103, wheelbase 176: its nose went onto the climb cliff (it screened 150) |
| H2 | 1.00 | 130 mm | 601 mm | 50° / 50° | 50° / 50° (held at -15°) | Ø82, wheels 26 mm forward, packs 88 mm back |
| H3 | 0.945 | 120 mm | 688 mm | 55° / 55° | | Ø93, wheelbase 179, wheels 54 mm forward, packs 102 mm back |
| H4 | 1.00 | 30 mm | 689 mm | 55° / 60° | | Ø70, wheelbase 190, wheels 72 mm back, packs 57 mm forward |
| H4, 1 kg high on top | | | | 50° / 50° | | the control |

- The tail is the cheap hill lever. Braced behind, T3 reaches the box's 45° / 45° (the motor's and tyres' limits)
  with no cost to the step or the turn.
- Hardware past that is paid for: 50° costs 210 mm of turn and 20 mm of step (H2); 55-60° costs 300 mm of turn, and
  60° the step too (H4). Keeping T3's step and turn, it buys 5° up and nothing down (H5, bigger wheels).
- On ordinary ground (x1) every finalist reads 35-40° both ways, held back by its tyres, so the hardware's gains show
  only on grippy ground.
- **The CoM's height with the tail braced** (`SCORPION_SEARCH=search_shape python gauges/hills.py height`, then
  `python gauges/hills_sheet.py height` -> `out/search_shape/hills_height.png`). Zach bet the tail makes height matter
  less. T3 with 1 kg moved from its belly to its top raises the CoM from 73 to 114 mm. Tail stowed, that costs 15° both
  ways (45° / 45° to 30° / 30°); braced (the best of -30°, -15° and 0°), 10° (45° / 50° to 35° / 40°). So the tail
  softens height but doesn't cancel it. Braced, uphill ends in a stall (the motors or grip), not a tip, and the extra
  kilogram alone takes 5° off that (T3 braced 45° up; with 1 kg at its own CoM height, 40°). The control: 1 kg on top
  reads lowest both ways. A rerun reproduced every number.
- No stowed reading beats its static tip angle (`static_check`). The run's first finals, read on the 800 mm hill, are
  **superseded** (`superseded - finals_800mm.json`): four of its five finalists passed by toppling slowly.

## The knob log (2026-10-27)

`SCORPION_SEARCH=search_hills python gauges/knobs.py sweep`, then `... rebrace` and `... side`; `python
gauges/knobs_page.py` builds the page "Scorpion Knobs", every
knob's sweep drawn on each gauge's scale. Results in `out/knobs/`. Zach asked for a log of "how ... the height of the
body and the width of the wheels actually translate to the numbers". Every knob of T3 takes 7 settings across its
search range, the rest at T3's, 3 seeds each (T3 8): the lean screen without its cut, and both hills at x2.5 in 6
tries, the tail stowed and braced. The sweep braced at -30° and -15°. `rebrace` re-read the braced hills at the best
of five angles (-75° to -15°), in case a raised body or mount left the foot in the air. It changed little, and T3 read
the same. Two knobs are new: the tyres' width (TW, 46 mm in every design so far) and the tail mount's height. Ride
height (clr) moves the body, its insides and the tail mount together.

- **Body height cuts both ways.** Below T3's 52 mm the step goes (40 mm: 50 mm; 15 mm: 30): the body's front meets
  the step face. Above it the hills go: at 90 mm, 30° / 35° stowed and 35° / 40° braced (T3 35° / 40°, 45° / 45°).
  From 15 to 90 mm the braced hills lose 10° both ways, the stowed 15° up and 10° down, so the braced tail doesn't
  cancel height. The skin's middle height (zc) has a narrow band for the step: 147 mm at 157, 110 at 125, 57 at 188.
- **Wheel width costs only the turn**: track 110 to 180 mm, 393 to 485 mm (and upright 0.87 at 180); tyres 25 to 80 mm
  wide, 382 to 441. The step and hills don't move.
- **The wheelbase is the hill lever and the step's enemy**: tyre gap 15 to 150 mm, hills 25° / 30° to 50° / 50°
  stowed; the step 150 mm at T3's 62, 40 from 82 up; turn 384 to 525.
- The stowed tail costs 10° up (no tail: 45° / 45°, but upright 0.69 and step 40). Gearing under about 1.8x, a tail
  under 260 mm or a push angle shallower than -37° loses the step; under 170 mm of tail or 2 N·m it can't right itself.
- Dead in range: p, qu, cu up to 180, dzp, msize 0.75-2x. T3's noise over 8 seeds: the step 5 mm, nothing else.
- Six wheels: 55° / 57° stowed, 55° / 60° braced, but step 37, turn 623, +790 g.
- **Side slope (a probe, `hills.side_try`)**: across a slope with a heading hold, 2.5 m. At x2.5 T3 reads 55°, track
  110 55°, 180 60°, ride height 15 60°, 90 50°; the control, 1 kg on top, 45°. At x1 every design slides at 40°. The
  tail held out as an outrigger didn't help (at -45° the foot dug in and failed every slope). The first run counted
  the start's ±10° heading as sliding and read 0° everywhere: **superseded** (`superseded - side_drift_bug.json`).

**The reel** (`SCORPION_SEARCH=search_hills python gauges/reel.py` -> `out/film/reel.mp4`, 46 s): five chapters of
side-by-side gauge tries (the gauges on T3, the braced tail, ride height, wheelbase, wheel width). Hills are drawn on
a tilted copy of the floor; the physics is the gauges'. One panel first disagreed with its gauge (ride height 90 mm
braced made 40° up in its one try; the screen reads 35°) and moved to 45°.

**A Gaussian-process surrogate** (`python gauges/surrogate.py` -> `out/surrogate/`; exploratory, no new sims): a
Matern 5/2 GP with a length scale per knob, trained on the searches' screened designs. On the hills run (5 knobs) it
predicts both hills to 1.5-1.6° and the turn to 13 mm, 95% bands holding 94-95%. Trained on the Sobol spread alone, it
ranks the refinements' designs at 0.92-0.94. At 24 knobs the turn still holds (42 mm, R2 0.89, rank 0.79). The step is weaker (R2 0.83 at 5 knobs, 0.55 at 24, where cliffs and
few spread designs sink it), and upright among screen passers is noise. Good for choosing which designs to simulate
on the hills and turn, and for a whole-range knob map; not for final readings.

## The lean search (superseded as the current run by the body search, 2026-10-27)

`SCORPION_SEARCH=search_lean python gauges/search.py lean`, then `... seed`, then `... finals` (results in
`out/search_lean/`, which `tools/config.py` GAUGES_CURRENT now names). The checks behind it: `... frozen` and
`... frozen_each`. Zach asked for the fixes the review of the drive search proposed. What each did:

| Fix | Result |
|---|---|
| Wheels as size, wheelbase centre and tyre gap | Every draw builds: 1,024 of 1,024, where the drive search built 914 of 1,500. The rear axle's -40 mm limit is gone. |
| Freeze the 14 knobs the random forest called dead | Failed its check. Redrawn together they took T10 from 0.94 / 100 / 404 to 0.76 / 54 / 505 (`docs/lessons/2026-10-27-dead-on-average-is-not-dead-at-the-front.md`). One at a time, three were dead: the middle axle, the packs' height and the motor's size, held at T10's. The skin's eight shape knobs are held at T5's by choice. 16 knobs search. |
| Falls at x1.5 and x0.65, 30 each, not 40 at x1 | Screen-to-final upright drift is -0.011 (was -0.057); no finalist dropped more than 0.1 (23 % did). A design is cut once the bar is out of reach (after 13 falls on average) and skips the climb: 891 of B's 1,024. B took 303 s, against 713. |
| Bisect the climb ladder | Dropped: 12 of the drive finals' 42 ladders aren't monotone (G2's card). |
| Stop a refinement run after 3 generations without a gain; one worker pool; 60 a generation | Three of the four runs stopped after 3 to 6 generations. |
| The same fall starts and step yaws for one generation's designs | Close neighbours (a 3 % step) share 44-52 % of their per-fall outcomes, so comparing them is about half as noisy; distant designs share none. |

**Time and reach:** unseeded, it took 1,354 s for 2,224 designs (the drive search: 2,252 s for 2,060, seeded with the
tail search's front). It beat the drive search at the low-climb end and found a 120 mm skin climber, but stopped
short in the middle: its best 100 mm design turned in 519 mm, not T10's 404. Seeded with the drive search's front and
finalists (re-screened, 413 s more), the refinements found nothing better than T10 within 3 generations.

**Finals, against the box's 0.60 / 30 mm / 594 mm** (the names are this run's):

| Design | G1 upright | G2 step up | G3 turn | Mass | What it is |
|---|---|---|---|---|---|
| T1 | 1.00 | 30 mm | 375 mm | 3.3 kg | the tightest turner; gear 1.8x, track 113 (repack) |
| T2 | 0.99 | 60 mm | 379 mm | 3.2 kg | Ø80 wheels, gear 2.0x, track 115 (repack) |
| **T12** | **0.945** | **100 mm** | **405 mm** | 3.4 kg | the drive search's T10, read again (0.97 there): still the all-rounder |
| T4 | 0.915 | 100 mm | 400 mm | 3.4 kg | the drive search's T4 |
| T5 | 1.00 | 110 mm | 504 mm | 3.8 kg | the drive search's T5, skin and tail |
| T6 | 0.995 | 120 mm | 595 mm | 4.2 kg | new: skin, Ø134 wheels, a 176 mm tail, gear 2.0x |
| T8 | 0.89 | 150 mm (the ladder's top) | 703 mm | 3.6 kg | the drive search's T6 (0.825 there) |
| N3 | 0.955 | 50 mm | 623 mm | 4.0 kg | the best with no tail: a skin |
| T8, limp tail | 0.345 | 50 mm | 710 mm | | the control |

- The new low-end designs gear down about 2x and narrow the track into the motor pods. G3 doesn't read speed, so the
  search buys a tighter circle with half the top speed.
- T7's screen read 130 mm and its finals 70: at x1.0 it passes 80 mm in only 10 of 20 tries, and every other height
  up to 140. The screen climbs at x0.65 and x1.5, and a ladder's gap can sit at x1.0 alone.
- Read again on the new step reflex (`... reclimb`; the table above is the first reflex's, kept as
  `out/search_lean/superseded - finals_reflex1.json`): T7 70 -> 130 mm, T1 30 -> 70, T9 30 -> 60, T13 120 -> 150;
  T12 and T4 100 -> 90 (at x1.0); the rest, the box, the no-tail designs and the limp control unchanged.

## The search with the drive knobs (superseded as the current run by the lean search, 2026-10-27; its finalists are read again there)

`SCORPION_SEARCH=search_drive python gauges/search.py drive`, then `... finals` (results in `out/search_drive/`, the
run `tools/config.py` GAUGES_CURRENT names for the pages). The tail search's family below plus three knobs Zach asked
for: track width (110–180 mm, the wheels' centre planes from the centre line; under the Trainer's 131 the motor goes
into the hull and is flagged "repack"), motor size (0.5–2x the 37 mm gearmotor: stall torque, rotor and 205 g scale
together) and gearing (0.4–2.5x the 30:1: torque up, speed down). 27 knobs; B was seeded with the tail search's front.

**Result, full gauges, against the box's 0.60 / 30 mm / 594 mm:** the drive barely moved. The search kept the motor
and gearing within about 5 % of the 37 mm 30:1 and narrowed the track a little (123–129 mm), for about 20 mm less
turning room. A bigger motor or a higher ratio climbed worse (30 mm on T12's design, 2x motor or 2.5x gearing), and a
wide track (165) cut the tail's righting to 0.78. The tail is the lever, not the drive.

| Design | G1 upright | G2 step up | G3 turn | Mass | What it is |
|---|---|---|---|---|---|
| T1 | 1.00 | 30 mm | 388 mm | 3.3 kg | the tightest turner, track 123 |
| T3 | 0.975 | 90 mm | 399 mm | 3.4 kg | track 126 |
| **T10** | **0.97** | **100 mm** | **404 mm** | 3.4 kg | Ø104 wheels, 123 wheelbase, track 128, tail 291 mm at 3.0 N m, motor and gearing as the Trainer's |
| T5 | 1.00 | 110 mm | 510 mm | 3.8 kg | skin (998 g) and tail |
| T6 | 0.825 | 150 mm (the ladder's top) | 699 mm | 3.6 kg | tail 272 mm at 3.1 N m |
| N1 | 0.825 | 40 mm | 504 mm | 4.1 kg | the best with no tail: six wheels and a skin |
| T6, limp tail | 0.41 | 50 mm | 691 mm | | the control |

T10 replaces T12 (0.91 / 100 / 424) as the all-rounder.

## The search with a tail (superseded by the drive search, 2026-10-27; its family is a subset)

`SCORPION_SEARCH=search_limb python gauges/search.py limb`, then `... finals`, then `python gauges/view.py` (page
"Scorpion Search") and `python gauges/export.py` (the scorecard).
Results in `out/search_limb/`. The family has 24 knobs:
- the Trainer's parts on new wheels (chassis3's six: wheel size, axles, belly, battery packs) and a middle axle;
- **a skin, which is the body** (Zach, 2026-10-26: "why have a shell and a body?"): the Trainer's walls and trim come out
  (about 416 g), and one closed 1.5 mm PLA skin wraps a superellipsoid (10 knobs) and every part inside, grown only where
  a part would poke out. The head stays inside for now (his call). Where the skin meets a tyre the sim gives it a wheel
  well. With the skin off, the design is the Trainer's own body;
- **a tail** (`robots.add_limb`): a turntable and one pitched link with a rubber foot, mounted 20 mm behind the rear
  surface at a chosen height, on two position servos with a torque limit (0.3–4 N m) and 6 rad/s; knobs: on/off,
  length, torque, push angle, stowed angle, mount height. Its moves are scripted reflexes in `gauges.py`: after a fall
  (`right`), turn its plane toward the ground or to a side and swing through the ground, for up to 10 s; on a step,
  push down behind when the robot stalls. A learned policy should do better.

Stages: 1,500 Sobol designs screened directly (the statics can't rank a tail's righting), then cross-entropy under
the four weightings, the climb screened at the worse of x0.65 and x1.5 from the start; then the finals: the best
turners at each climb level of the front, plus the best with a tail and no skin and the best with no tail, and the
best tail climber again with its servos limp (0.05 N m) as the control.

**Result (2026-10-26), full gauges, against the box's 0.60 / 30 mm / 594 mm** (righting capped at 10 s; the first
finals let an attempt that began before 10 s finish after it, kept as `out/search_limb/superseded - finals_10s_leak.json`):

| Design | G1 upright | G2 step up | G3 turn | Mass | What it is |
|---|---|---|---|---|---|
| T2 | 1.00 | 40 mm | 402 mm | 3.3 kg | Ø94 wheels, 138 wheelbase, tail 317 mm at 3.3 N m |
| **T12** | **0.91** | **100 mm** | **424 mm** | 3.4 kg | Ø98 wheels, 124 wheelbase, belly 58, tail 287 mm at 2.8 N m, stowed upright |
| T6 | 1.00 | 110 mm | 510 mm | 3.8 kg | Ø76 wheels, skin (998 g) and tail |
| T14 | 0.985 | 150 mm (the ladder's top) | 700 mm | 3.6 kg | Ø127 wheels, 179 wheelbase, tail 263 mm at 3.2 N m |
| N1 | 0.89 | 40 mm | 550 mm | 3.9 kg | the best with no tail: a skin (943 g), Ø123 wheels |
| T7, limp tail | 0.41 | 50 mm | 691 mm | | the control; T7 itself reads 0.85 / 150 / 699 |

- A tail meets all three targets and beats every tail-less design on all three. T12, a tail and no skin, beats the box
  by 0.31 on G1, 70 mm on G2 and 170 mm on G3. The control drops from 0.85 / 150 mm to 0.41 / 50 mm: the tail does it.
- The search dropped the skin almost everywhere: a tail rights the robot, so the skin's weight and width only cost.
  Short wheelbases with a tail turn tightest (about 400 mm).
- How it climbs: it drives into the step and wheelies up against it (to 56 degrees nose-up at 150 mm), then the tail
  plants behind and lifts the rear on (traced: body speed never above the drive's 0.5 m/s, the servo at its limit,
  no penetration).
- G2's ladder stops at 150 mm, and T7 and T14 reach it at every friction, so they may climb more. A stair is about
  180 mm; extending the ladder is a gauge change (a new G2), Zach's call.
- Every tail finalist wants 2.8–3.4 N m servos (the 30–35 kg cm class). Only the 9 g MG90S class is on hand.

## The first generative search (superseded 2026-10-26)

**Superseded:** its shell lay over the Trainer's whole body, counting the walls twice (about 400 g on every shell
design) and hiding the head inside. Its results stay in `out/search/` as they were; S1 rebuilt as one skin is 283 g
lighter.

`python gauges/search.py statics | calibrate | search | finals`, then `python gauges/view.py` for the 3D page
("Scorpion Search"). The family has 18 knobs: chassis3's six (the Trainer's body and insides on new wheels), a
middle axle, and a shell (shell3's superellipsoid over the body, cut at the belly, a 1.5 mm PLA skin) or none.

- **A, statics:** 2^15 Sobol designs, rest states (shell3.static), footprint and nose clearance. Checked against the
  screening sims on 240 random designs: the static upright share tracks them loosely (rank correlation 0.43); the CoM
  margin is no use here, since almost no design has a single rest state (0.2 %); the nose clearance is a ceiling
  on the climb (the sim beat it in 0.4 % of designs); a spin drifts 1.44x past the footprint (median). So the
  statics only enrich the next stage.
- **B, screening sims:** 40 falls at x1, the step ladder at x0.65 with 6 tries a direction, the turn at every
  friction; the bar for G1 is 0.85, so a design near 0.75 can't pass on luck. 1,500 designs, half from the statics'
  best and half at random.
- **C, cross-entropy:** from B's best under four weightings of climb against turn (climb, climb - 0.25 turn,
  climb - turn, turn alone), 8 generations of 40.
- **D, finals:** the best-turning few at each climb level of the feasible front, on the full gauges with the box
  beside them.
- **E, climb re-screen:** the first finals (kept as `out/search/finals_BC.json`, **superseded**) showed climbs that
  need low friction: one finalist climbed 50 mm at x0.65 and failed 40 mm at x1.5. Screening at one friction let
  the optimizer find designs good only there. The 300 best climbers were re-screened at the worse of x0.65 and
  x1.5, refined again (climb, then climb - 0.25 turn), and the finals rerun from that.

**Result (2026-10-26), full gauges, against the box's 0.61 / 30 mm / 594 mm** (page "Scorpion Search"):

| Design | G1 upright | G2 step up | G3 turn | Mass | Size (L x W x H) | What it is |
|---|---|---|---|---|---|---|
| S1 | 0.96 | 40 mm | 442 mm | 4.0 kg | 387 x 410 x 361 | Ø105 wheels, 187 wheelbase, belly 50, a tall dome shell (836 g) |
| S6 | 0.945 | 50 mm | 670 mm | 4.3 kg | 364 x 451 x 362 | Ø129 wheels, 172 wheelbase, packs 54 mm forward, a wider shell (930 g) |

- One shape meets all three targets at once: S1 meets G1 with room to spare and beats the box on G2 and G3.
- G2 tops out at 50 mm, about 0.78 of the wheel radius in both designs. More climb means bigger wheels, and
  bigger wheels mean a bigger footprint, so G2 costs G3. No shape-only design held 60 mm across the band.
- Every design that cleared G1 had a shell, and the shell costs 0.8–1.2 kg and about 400 mm of width. The
  Six-wheel, with no shell, already climbs 50 mm and turns in 542 mm; only G1 fails it (0.49).
- So the next lever is a limb: a tail that pushes on the step, or an arm that rights the robot instead of a shell.
  Neither is in the family yet.

## Change log

- 2026-10-26: v1, three gauges. Before any reading counted, the step's sharp edge was found to act as a wall and was
  rounded. The first controls picked for G1 (packs up 100 mm) and G2 (wheels up to 160 mm) didn't move their
  gauges: the packs moved the CoM 23 mm, inside the E4's margin, and bigger wheels on the same motor push less.
  They were replaced before the full run.
- 2026-10-26: targets set (G1 at least 0.75, G2 and G3 as far as they go). First generative search: the screen tried
  steps at x0.65 only and was exploited (see stage E); it now takes the worse of x0.65 and x1.5.
- 2026-10-26: a limb may act (G1: 10 s to right after the rest; G2: its moves count inside the 4 s); limbless designs
  read as before (a fixed-seed regression on the box and E4 matched exactly). The tail search added the tail and made
  the skin the body; the first search is superseded. The scorecard's check names became unique (the page keys on them).
- 2026-10-26: G1's 10 s for a limb leaked: an attempt begun before 10 s could finish after it (filming T12, one fall
  "righted" at 10.5 s). Now an attempt starts only if it can end inside 10 s. The tail finals were rerun: T12 0.955 ->
  0.91, T14 1.0 -> 0.985, T7 0.935 -> 0.85, T11 now misses; climbs and turns unchanged. `gauges/film.py` films a design.
- 2026-10-27: three drive knobs (track, motor size, gearing); the search with them is current. T10 0.97 / 100 / 404.
- 2026-10-27: the lean search (the review's fixes) is current; the drive search's T10, read again as T12 (0.945 /
  100 / 405), is still the all-rounder. The review's claim that 14 knobs were dead failed its check; three are frozen.
  The falls screen now reads x1.5 and x0.65. G2's ladder was found to have gaps: the scripted push's.
- 2026-10-27: G2's step reflex changed (Zach's go): a progress-based stall, a kick when level, a push when nose up.
  Limbless designs read identically. The body search (the skin's shape searched again) is current: T5, a domed skin
  and tail, reads 0.96 / 150 / 403 and replaces T10 as the all-rounder.
- 2026-10-27: the shape study (the body's shape alone, on T5's locked platform). T3 reads 1.00 / 150 / 381 with a
  485 g skin: the best design so far, but its nose sits within 10 mm of a climb cliff. `gauges/film.py` films the
  current search's finalists (it read the tail search's).
- 2026-10-27: G4 hill up and G5 hill down proposed (`gauges/hills.py`), read on the shape study. Tip limits on a
  grippy floor with a 1 s soft start; two first controls failed and were replaced (see the cards). A sharp-turn
  rollover gauge was checked and not built: nothing tips in a skid-steer turn.
- 2026-10-27: G4 and G5's hill went from 300 mm to 800 mm: a design just past its tip angle passed by toppling too
  slowly (`docs/lessons/2026-10-27-a-pass-must-outlast-the-slowest-fall.md`). The shape study's hills were read
  again (T3 35° / 40°, the box 45° / 45°); the 300 mm files are kept as superseded. The hills run unlocks the wheels
  and packs.
- 2026-10-27: the hill went to 2.5 m: the hills run's search parked designs just past their tip angles, which 800 mm
  passed. `static_check` now holds every stowed reading to its static tip angle (none beats it; 90 did on 800 mm).
  Everything read again; the 800 mm files kept as superseded. The hills run's finals: the tail braced gives T3 the
  box's 45° / 45° for free; hardware past that costs step or turn.
- 2026-10-27: the knob log (`knobs.py`): every knob of T3 one at a time on all five gauges, two new knobs (tyre width,
  tail mount height), a side-slope probe (its first run had a drift bug, superseded), a reel of gauge tries
  (`reel.py`) and a Gaussian-process surrogate check (`surrogate.py`). No gauge changed.
