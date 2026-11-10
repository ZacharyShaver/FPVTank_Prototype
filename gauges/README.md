# Scorpion gauges: the requirements, as tests that read a number

Set up 2026-10-26. A gauge is a fixed test that reads one number off any design. The test is set in stone. The
number a design should reach is a lever, and Zach sets it each iteration (the table at the end), because the
levers pull against each other: the E4 shell that always lands upright is 436 mm wide.

Iteration 1 has three gauges, on purpose: fewer things to test, and less doubt about which part made a result
go wrong. More come after the first build and real tests.

```
python gauges/gauges.py            # every design and control under the band -> gauges/out/scorecard.json (~4 min, 30 cores)
python gauges/card.py read         # G4-G7 on the page's designs, G1-G3 on its knob variant -> gauges/out/card/card.json (~6 min)
python gauges/export.py            # the scorecard as the page's row files, gauges/out/dash/ (the page itself: dashboard.html)
python gauges/scorecard_page.py    # a static copy of the scorecard for the public gallery (tools/gallery), gauges/out/dash/scorecard.html
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
- **What it mostly reads (2026-10-28, `card.py com`):** the spin is open-loop, so a CoM fore or aft of the wheels' centre walks the
  robot off its start. T3 with 150 g placed to move its CoM reads 394-407 mm within 1 mm, 411-440 at 3-5 mm and
  492-513 at 7-9 mm: 12-15 mm of circle for each millimetre. The same 150 g at the CoM is the control (394 against
  381). Every T design's CoM sits within about 1 mm of its wheels' centre; the roster's sit 6-18 mm off and spin
  100-190 mm wider than their outline (T3's outline 367 mm, the box's 479). So the T designs' lead on G3 is about half
  shape and half a CoM placed to the millimetre, which a camera head or a moved battery would undo. A controller
  that holds heading and position would probably win much of the drift back (unchecked).

## G4 Hill up, G5 Hill down (adopted 2026-10-27; target: as steep as it goes)

Zach asked "how far of a hill it can climb/descend before falling", the designs being top heavy with the tail doing
the righting. On the scorecard page since 2026-10-28 (`card.py`), as the better of the tail stowed and held at -30°,
-15° or 0° (rule 1); the static check and the control are read stowed. First read on the shape study
(`gauges/hills.py`) and in the hills run's search.
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

## G6 Crest (adopted 2026-10-27; target: at least 20°)

Zach picked it from the knob log's recommended tests: the other gauges only charge for body height, and a crest is
where height pays. `SCORPION_SEARCH=search_hills python gauges/crest.py read` -> `out/crest/read.json`.
- **Lever:** getting over a ridge without ending up balanced on the belly (high-centred) or tipped.
- **Reads:** the steepest ridge (degrees a side, 5° steps) it crosses in at least 18 of 20 tries, the better
  direction counting, every gentler ridge crossed. The crest bends the path by twice the reading.
- **Test:** two planks at ±the angle meeting at a peak 150 mm up (G2's top step, tall enough to reach any belly),
  the peak rounded by a 3 mm capsule tangent to both (the step's edge lesson). Square on ±10°, the lead just short of
  the foot, crawling at 0.15 m/s with the step's tail reflex. It passes with its CoM 0.1 m past the far foot, upright,
  within the drive time plus 3 s. Read at x2.5, as the hills: on the band's floors the ramps slide everything first.
- **Why a crawl:** at the step's 0.5 m/s, momentum carried a 15 mm belly over the peak, which hid high-centring. It
  also threw T3 into a nose-dive off the peak (25°, against 40° at 0.25 m/s and 35° at 0.12).
- **Controls:** the box with its belly 15 mm lower reads below the box (5° against 15°), and the box stretched 1.5x
  reads below it (10°). A first control failed: T3 at 15 mm ride height tied T3 (25°), because T3 tips before its belly
  touches. It stays as a row, not a control.
- **Readings (20 tries):** T3 25°, step layout 25°, box 15°, six-wheel 15°, Trainer 10°. The box and Trainer
  high-centre. T3 sometimes stalls teetering on the peak: the step reflex then pushes, and 3 tries in 18 at 30° went
  over the nose. A crest-aware reflex is a controller lever.
- **T3 reads on a plateau** (`crest.py curve`, 40 tries an angle and direction, no early stop): from 25° to 40° it
  crosses in 75-95% of tries, against the 90% a reading needs, so 20 tries read it 25° or 40° by luck (the knob
  sweep's T3 read 40°). Backwards it crosses 40° 40 times in 40 but 25° only 34. The knob sweep's crest column swings
  the same way; only drops to 20° or less that hold over neighbouring settings are effects (a tail foot of 23 mm or
  more, a tyre gap of 105 mm or more, gearing at 1.1x or less, a push face, no tail). A pass rate at one angle would
  read smoother; not changed (Zach's call).
- **Not only T3** (2026-10-28, `card.py`, fresh seeds): the Trainer read 20° (10° before), the step layout 35° (25°)
  and T3 40° (25°); the box and the six-wheel held at 15°, and both controls passed again. At 20 tries a crest
  difference under 15° is noise. A steadier read (a pass rate at a fixed angle, or 40 tries an angle) is a gauge
  change, Zach's call.
- **Trust:** none yet.

## G7 Push (adopted 2026-10-27; target: at least 3 kg)

Zach picked it from the same list: moving boxes is in the purpose, and nothing else reads force.
`SCORPION_SEARCH=search_hills python gauges/push.py read` -> `out/push/read.json`.
- **Lever:** shoving a load.
- **Reads:** the heaviest box (kg) it pushes 0.5 m in at least 18 of 20 tries, the better direction counting, every
  lighter box pushed; the worst over the band.
- **Test:** a box 200 mm deep, 260 wide and 150 tall on the floor's own friction (at x1 it takes 5.9 N a kilogram),
  scaled with the band. Square on ±10°, the lead 20 mm short, ramped over 0.5 s to 0.3 m/s, holding its heading. It
  fails if the box is short of 0.5 m at 6 s, the robot tips, or its front rides 40 mm up onto the box. Tail stowed.
- **Controls:** each read where its claim applies. On a grippier floor the box drags harder, so the motors bind at
  x1.5 and the tyres at x0.65. T3 at 0.4x gearing reads below T3 (0.5 against 1 kg, worst). T3 at half grip reads
  below T3 at x0.65 (2 against 4 kg). Read at the band's worst, half grip tied T3, since both rode up the box at x1.5.
- **Readings (20 tries, worst; by friction x0.65 / x1 / x1.5):** six-wheel 3 kg (5/4/3), Trainer 2.5, box 2, step
  layout 2, **T3 1 kg (4/5/1)**. T3 has the force (5 kg at x1), but at x1.5 its domed nose rides up onto the box, and
  in reverse its tail mount, 150 mm up (the box's height), catches the box's top edge and levers it up. A push face
  on the nose (knob `bumper`) pushes 4 kg but kills the step (30 mm). The tail mount at 170 mm pushes 4 kg at 20 tries
  with the step intact (150 mm), for 5° of braced hill. Its control: a 200 mm box catches the 170 mm mount again
  (0.5 kg at x1.5). The rule: nothing on the rear face below the top of what it pushes.
- **Repeatable:** read again with fresh seeds (2026-10-28, `card.py`), every design and control read the same.
- **Trust:** none yet.

## G7 Tow (2026-11-02, in place of the push from the tow run on)

Zach: step and push conflict, because a climbing nose rides up the box. `tow.py` (`python gauges/tow.py check`).
- **Reads:** the heaviest sled (kg) it drags 0.5 m on a rope from a hitch at its rear, axle high; the worst over the band.
- **Found (the tow run, 2,416 designs):** step no longer costs it (rank correlation +0.15; 0.01 at fixed weight), but it
  reads weight: r 0.88, about 1.16 kg towed per kg of robot, because the sled's friction moves with the floor's.
- **Trust:** none yet.

## G8 Rough ground (2026-11-02)

Zach: "add rough terrain"; asked, he picked rocky ground. `rough.py` (`python gauges/rough.py check`).
- **Lever:** crossing rubble without beaching or rolling.
- **Reads:** the rock size (mm) it drives 2 m across, the step's pooled rule at 0.9 of tries, at x2.5 grip.
- **Test:** a heightfield of half-ellipsoid rocks, bases 50-150 mm in radius, 0.4-1x the rung tall, over 0.3 of the
  ground. A try's field comes from the seed and the try, so a taller rung is the same field raised and every design
  meets the same fields. 0.4 m/s, holding its heading; it fails past 85° or under 20 mm of progress in 3 s.
- **Controls:** rays land on the drawn rocks to 0.00 mm (the field mirrored in Y misses). On a flat field the box and T3
  drive 2 m every time. The box with its belly 15 mm lower reads below the box (13 against 33 mm).
- **Readings (6 tries a rung):** box 33 mm, T3 46 mm (real build, track 130). T3 beaches: its belly is 25 mm.
- **Trust:** the obstacle course (below) calls it fair: of the tries that reached its 40 mm rocks, 6% stopped there where
  G8 says the design clears 40 mm, 23% where it says it doesn't (the gauge needs 9 in 10, the course one pass). Filmed on
  the gauge films page (`test_films.py --tests rough`) on the same eight designs as the rest.

## Weights (2026-11-02)

`weights.py`: one importance weight a gauge (`WEIGHTS`, all 1 to start). The all-rounder is the weighted worst rank:
1 minus the largest shortfall from the top rank, each scaled by its weight over the largest. Equal weights give the
worst rank, so the runs before re-rank exactly as they ran (checked on the tow run: the same front and champions). 0
drops a gauge from the score, the front and the streams. `python gauges/weights.py check`.

## The obstacle course and its weight vector (2026-11-02)

Zach, on the weights: "it gives us a way to tell the simulator what you want as a result ... you can score a weight
vector for how well it goes say around a obstacle course. multiple factors and their interplay needs a descriptor".

`course.py`: rocks up to 40 mm (G8's), the crest's ridge at 20 degrees a side (G6's), a 50 mm step onto a plateau (G2's
rounded edge), and a dead end 750 mm wide to turn round in and drive out of (G3). Each is about that gauge's median in
the tow run. One driver: 0.3 m/s, steering for the centre line, the step's reflex on a stall, a spin in place at the
end. The score is the share of the path covered, the mean of 8 tries (each its own rocks and start, the same for every
design). Controls (`python gauges/course.py check`): the box and T3 finish the clear course every try; each obstacle
alone, too big for the box, stops it there. T3 finishes the real course 4 in 4; the box stops at the rocks or the
ridge.

`weights.fit` finds the vector whose all-rounder ranks designs as the course does (Spearman); `weights.cv` reads it on
designs it wasn't fitted on. Its controls: a made-up test scored by known weights fits them back (held-out 0.98);
shuffled scores read 0.08.

**Reversing up the step (current).** Zach, after the first run: "backwards is fine ... knowing when to turn is something
we need to build ... lets allow it". Stalled nose first at the step for 3 s, the driver backs off, turns round, reverses
up (the rear-up reflex if the design has one, as G2 tail first) and turns to face forward on top (`course.REVERSE`; the
plateau before the corridor lengthened 0.5 -> 1.0 m to turn on). It is a hand-written rule standing in for a learned
one. Controls: T3 climbs nose first and never turns; a design that climbs 50 mm only tail first gets up 4 in 4 with the
rule and 0 in 4 without; the box still stops at a 200 mm step. Known fault: one design (of 320, a long low six-wheeler)
comes off its turn on top out of line and catches a corner on the corridor's mouth every try: the rule's, not the design's.

On 320 of the tow run's designs (`course.py run`, then `fit`; out/course/fit.json, descriptor.png; G8 as the first run
read it):

| Predicting the course, held out | reversing allowed | nose first only (superseded) |
|---|---|---|
| fitted, weighted mean | 0.78 | 0.67 |
| fitted, weakest test (as the search scores) | 0.71 | 0.57 |
| the best single gauge | 0.46 | 0.48 |
| from the course's own numbers (each obstacle 1 / (1 - share of designs short of it)) | 0.38 | 0.34 |
| equal weights (every run so far) | 0.40 | 0.28 |
| control: course scores shuffled | -0.11 | 0.03 |

The fitted vector, weighted mean: step 1, crest 1, rough 0.6, the rest 0 to 0.05. Weakest test: crest 1, step 0.99,
rough 0.82, upright 0.5, tow 0.27, turn and both hills 0. Finished: 53% of tries (nose first only: 34%).

What the course found about the gauges:
- **G2 step reads the better direction, at a rolling 0.5 m/s.** Nose first only, 39% of the tries the gauge says should
  climb the step stopped at it. Of those 53 designs, alone on the step at 0.3 m/s 2% of tries got up, so it isn't the
  obstacles before. 35 climb it only tail first (the gauge's own try at 50 mm, x1: nose first 3%, tail first 100%; 12
  of them have tails); the other 18 need the gauge's 0.5 m/s. Their controls (78 designs that climbed the course's step
  every time) climb it alone every time. Reversing allowed, the gauge calls the step: 6% stopped where it says clear,
  44% where it says fail. The 18 that need speed remain.
- **G3 reads the open floor's swept circle, drift and all; a dead end's walls stop the drift.** The gauge puts 63% of
  designs over 750 mm, yet about 1% of their tries stuck turning, unless the body's diagonal itself is over 750 mm (18
  of 68 tries stuck). It gets weight 0 in every fit, which is why the course's own numbers predict it worst.

Films: out/course/course_T3_Box.mp4 and course_n1_n14.mp4 (nose first only, now in out/course/nose_first/: a
tail-first-only climber stalling, beside one that finishes); course_n298.mp4 (the corridor-mouth fault).

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

Iteration 2 adds the hills, the crest and the push (Zach, 2026-10-27). The table is from their own reads (`hills.py`,
`crest.py`, `push.py`), 20 tries; the scorecard page reads them again on all its designs (`card.py`, 2026-10-28).

| Gauge | Box reads | Best design (2026-10-27) | Target (Zach, 2026-10-27) |
|---|---|---|---|
| G4 / G5 hill up / down (x2.5) | 45° / 45° | Box, Trainer 45° / 45°; T3 braced 45° / 45° (T3 on six wheels 55° / 57°, a 6-try screen) | as steep as it goes |
| G6 crest | 15° | T3, step layout 25° (T3 25-40° by luck) | at least 20° |
| G7 push (worst friction) | 2 kg | Six-wheel 3 kg; T3 with a 170 mm tail mount 4 kg | at least 3 kg |

On these, T3 as it stands meets the crest and misses the push (1 kg); the 170 mm tail mount meets it. On the page
(2026-10-28) two designs meet every target with a number: T3 with the 170 mm tail mount (1.00, crest 25°, 4 kg;
step 150 mm, turn 387 mm, hills 40° / 45° braced) and T5 on the Trainer body (1.00, 40°, 4 kg; but step 90 mm, turn
441 mm).

G1 is a floor; G2 and G3 are pushed as far as they go, together. Zach on G3: "a meh gauge but fine for now", so it is
the first candidate to supersede.

No design beat the box on all three. The Trainer is a coin flip after a fall (0.45; half its falls end on its back),
below the plain box, which is 167 mm tall all over.

## The body search (superseded as the current run by the shape study, 2026-10-28)

`SCORPION_SEARCH=search_body python gauges/search.py body`, then `... skin`, then `... finals` (results in
`out/search_body/`, which GAUGES_CURRENT named until 2026-10-28). The lean search's process on G2's new step reflex (G2's card),
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

## The shape study (current, 2026-10-27)

`SCORPION_SEARCH=search_shape python gauges/search.py sweep`, then `... shape`, then `... finals`; then
`python gauges/shape_sheet.py` (the picture sheet) and `python gauges/view.py search_shape` (page "Scorpion Body
Shapes"). Results in `out/search_shape/`, which GAUGES_CURRENT names since 2026-10-28 (its finalists are the
scorecard's). Zach: "with the tail
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
knob's sweep drawn on each gauge's scale, with a little model of every setting (a side view on each row, a 3D view
with a slider and T3 as a ghost in the opened row; `out/knobs/models.json`, rebuilt by `knobs_page.py models`). For phones
(2026-10-28) the page thins each hull to 140 corners and packs them, and loads three.js on the first 3D tap: 2.5 MB to
425 kB. Both pages are in the public gallery's "Requirements as tests". Results in `out/knobs/`. Zach asked for a log of "how ... the height of the
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

**G6, G7 and the candidate knobs** (`... knobs.py sweep67` reads G6 and G7 on every setting, `crest20` re-reads
the crest at 20 tries, `grip` the hills by tread grip on x0.65 and x1, `speed` the hills at 0.15-0.8 m/s, `rule` the
brace angle set by rule). Three knobs are new: the tyres' grip (`tyre_mu`; the tyres take MuJoCo contact priority, so
a tread below the floor's friction is no longer overruled by it, and at 1x nothing changed: the fixed-seed regression
matched), the tail foot's radius (`foot_r`) and a push face across the nose (`bumper`, 60 mm tall, 75 g). The first
pass's six candidate knobs, worked through:
- **K1 tyre grip: yes, the hill lever on ordinary ground.** On x1, half grip reads 20° every way, today's 35° / 40°
  stowed and braced, 1.5x 35° / 40° and 40° / 45°. On x0.65, today's 25° / 30°, 1.5x 35° / 40°. The step needs at least
  today's grip (half: 20 mm). On x2.5 nothing moves (it tips before it slides). The model's tyre friction is a guess.
- **K2 tail as a counterweight: no.** No held pose beats the brace at -30° (45° / 45°), and braced, uphill ends in a
  stall, not a tip.
- **K3 brace angle per design: a rule, not a knob.** -30° up and -15° down are best on 175 and 177 of 191 designs; the
  rule (foot just on the ground) is within 5° of the best on about 98%, the misses noise.
- **K4 tail foot: keep 12 mm.** 6 mm: 40° / 40° stowed, 40° / 45° braced. From 29 mm the hills fall to 35° / 35° and
  40° / 40°, the turn grows to 408-432 mm, the crest to 20° (from 23 mm), the step to 110 mm at 40.
- **K5 a moving ride height: probably not worth an actuator.** At 15 mm the hills read 45° / 45° and 45° / 50°, and it
  pushes 4 kg; the step needs 52 mm or more. 5-10° of hill for a lift mechanism.
- **K6 hill speed: the lever is the speed loop.** Slower is worse uphill: braced, T3 30° at 0.15 m/s, 45° at 0.5 and
  0.8. The drive is a DC motor on a duty-cycle command with a proportional speed term, so its stall torque scales with
  the speed asked for. Wheel-speed feedback with an integral term would let a crawl climb like a run (the robot's
  code). The first run timed slow drives out at 8 s and read them 0: **superseded** (`superseded - speed_timeout.json`).
- **K7 push face: no; raise the tail mount** (G7 above). The push face costs the step (143 to 30 mm; 60-80 with its
  top at 125-150), the turn about 45 mm, and upright to 0.94-0.97.

**Which knobs matter (a review, 2026-10-28).** Read off the sweep against the noise (upright 0.05, step 20 mm, turn
20 mm, hills 10°, push 1.5 kg; the crest only where it drops to 20° or less, its plateau being noise):
- **Dead:** cu (the skin's height above its middle) and qu (its top's squareness) move nothing over their whole
  range. With the tail doing the righting, the top of the body is free: room for the head or an arm. **Dropped**
  (Zach, 2026-10-28): held at T3's in every new search (`knobs.DEAD`).
- **Settled:** track, TW, b, p, ar, xc, cd, qd, dzp, msize, foot_r, th_push and th_stow only cost when moved off T3's
  value; no setting of them is better on any gauge. Most are held by the turn (track, TW, b, p, ar). af (the nose's
  reach) is settled too, though the first list missed it: T3 sits 10 mm from its climb cliff. The tread's grip
  (tyre_mu) is a property to measure, not a knob.
  **Not frozen** (the check, `knobs.py freeze`, 2026-10-28): held at T3's together they cost 17 mm of turn (378 against
  361 mm at a 150 mm step), because the free search narrowed the tyres (46 to 34 mm), the track and the skin at once,
  each by less than the bar. The check's control (the levers held) lost nothing, since it scored only step and turn,
  where T3's levers are already best (`docs/lessons/2026-10-28-small-effects-add-up.md`).
- **Floors:** gear, L and tq lose when lowered and gain nothing above a floor: gearing about 1.8x, a 260 mm tail, a
  2.2-2.8 N·m tail servo (upright 1.00 from 2.2, the full step from 2.8; the MG90S is about 0.2).
- **Levers** (better on one gauge, paid for on another): gap and xw (hills against step and turn), clr, zc and dxp
  (push or hills against the step), R (turn against step and crest), mount_z (push), the six-wheel switch (hills
  against step and turn) and bumper (push against step).
- **Caveats:** one knob at a time around T3, so another platform (six wheels, no tail) may need a settled knob back.
  The drive search's claim that 14 knobs were dead failed its check (redrawn over their range, they moved the step);
  this claim is weaker, settled at T3's value rather than dead. It failed its check too (above).
- **To add: front flippers** (Zach, 2026-10-28: "flippers have got to be a future knob i bet they would help a lot
  with the steps"). Not in the capability search; a knob for the next round. Why they should pay on G2: the tail only
  pushes from behind, and at 60-80 mm the nose catches on the step's lip (the reflex note above). A flipper reaching
  forward lifts the nose onto the top. The tracked version (`chassis-v2/guard_flippers.py`, Guard arm E) turned down
  lifts the claws 69 -> 153 mm and pitches the robot 27° at under 5 kg·cm per flipper, for +185 g and 275 -> 319 mm of
  width. On wheels: a link pair on the front axle, modelled like the tail (`robots.add_limb`), with length, torque,
  stow angle and outboard-or-centre-line as the knobs, and a front move in the step's reflex. Read it on the 300 mm
  ladder (`capability.HEIGHTS_EXT`): T3 tops out at 150 there too, and big wheels reach 225. Costs to watch: the turn (it reads the widest point), mass,
  and upright.

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

## The capability search (2026-10-28)

`python gauges/capability.py run` (about 7 h: B, then refinement rounds until 15:15, then the finals) and `python
gauges/capability_page.py` -> `out/capability/`, the page "Scorpion Capability"
(a private claude.ai page). Zach: "max out every single goal dont set the percentages ...
were shooting to test out the capability of this project so we can learn from the results". Every knob free (28 with
the tail, six-wheel and skin switches; the dead two and the tread grip held), all seven gauges screened at 6 tries a
rung, the step ladder to 300 mm. 1,024 Sobol designs, then 10 rounds of 8 CEM streams (one per gauge, and an
all-rounder that raises a design's worst percentile rank), 3,424 screened; the streams' bests and four front
all-rounders read on the full gauges (`finals.json`).
- **Ceilings:** upright 1.00 (T3's); step 225 mm (140 mm wheels, 71 mm ride height, 324 mm tail; turn 784, push
  0.5 kg); turn about 389 mm (none beat T3's 381); hills 60° up / 65° down and push 8 kg (one design: six wheels,
  5.5 kg, packs at the space's 2x bound); crest 45°. No test's top capped a champion.
- **Two families, nothing between:** four wheels and a tail own the step and the turn; six wheels and weight own the
  hills, crest and push (no six-wheeler of 2,176 stepped over 100 mm). No design stepped 100 mm and turned in 450.
  T3's corner holds: on the front, and nothing near it on step and turn together.
- **The all-rounder stream failed** (`docs/lessons/2026-10-28-a-pool-rank-measures-the-search.md`): it settled on the
  hill-and-push champion (step 50, turn 659, upright 0.51). T3 with the 170 mm mount is still the best all-rounder.
- The screen read the six-wheelers' upright high (hill champion 0.70 screened, 0.505 full).
- **Floating parts (found the same evening, below):** 55 % of its designs had a part off the body. Its champions for
  upright and crest were bare-tub six-wheelers, one with motors 42 mm off the tub, one with motors reaching only 4 mm
  into it; its 225 mm stepper had a push
  plate 19 mm off its nose (without the plate it still reads 225 mm on its own seed, 200 on another). Its hill, push
  and turn champions were whole. The strict run replaces it.

## Noisy copies (2026-11-08)

`python gauges/noisy.py check | run | table | single` -> `out/noisy/`. NASA's ST5 antenna search scored each design on 3
copies with noise added, so a design couldn't win by working only when built exactly. The gauges read a design as drawn.
This reads the tow run's 15 finals, rebuilt under today's code, on the full gauges as three slightly wrong builds, with
every copy of a design on one set of seeds. A design's noisy reading is the worst of the three. No gauge changed.

| Copy | CoM, whole robot | Also |
|---|---|---|
| nose | 5 mm forward, 2\* mm sideways | 5 %\* heavier |
| tail | 5 mm back, 2\* mm sideways | 5 %\* heavier |
| weak | 3\* mm up | motors and servos 15 %\* weaker, tyres 1.5\* mm smaller |

\* = a guess. The 5 mm rests on T3: 150 g\* of leads in the back moves its CoM 4.3 mm back, the sim counting 60 g\* of wiring,
and the power bay's 105 g, unbought, 2.8 mm forward. Print 1's 1.5 mm of pack play moves it 0.2 mm, so it's left out. The
one mass to compare is the tub: 232 g in the sim, 236 g in the slicer.

Controls (`check`): a zero error gives the same model byte for byte, each copy a different one; G3 on T3 reads 13.3 mm of
circle per mm of CoM, inside the 12-15 above (G3); `single` reproduces its copies (T3's step: x+5 alone 57, the nose copy
55). **Noise floor**, each design as drawn on a second set of seeds, largest move: upright 0.095, step 6 mm, turn 0, hills
0, crest 5, tow 2 kg, push 1 kg. So a single rung of crest or tow isn't established.

Drawn -> the worst of three (one number: no change):

| Design | Upright | Step, mm | Turn, mm | Hill up | Hill down | Crest | Tow, kg |
|---|---|---|---|---|---|---|---|
| T3 | 1.00 -> 0.77 | 150 -> 55 | 448 -> 520 | 40 -> 35 | 45 -> 40 | 25 -> 20 | 6 -> 5 |
| Box | 0.64 -> 0.59 | 31 | 594 -> 648 | 45 -> 40 | 45 | 15 | 3 |
| best all | 0.32 -> 0.30 | 46 -> 41 | 802 -> 881 | 55 | 55 | 30 -> 25 | 8 -> 6 |
| front 1 | 0.29 | 62 -> 61 | 746 -> 998 | 55 -> 50 | 55 | 25 -> 20 | 8 |
| front 2 | 0.34 | 45 -> 41 | 781 -> 817 | 55 -> 50 | 55 | 35 -> 30 | 8 -> 6 |
| front 3 | 0.36 -> 0.35 | 141 -> 132 | 826 -> 1047 | 55 | 55 | 25 | 8 |
| front 4 | 0.43 -> 0.41 | 62 -> 52 | 828 -> 844 | 55 -> 50 | 55 | 30 | 8 |
| best low | 0.40 -> 0.35 | 61 -> 51 | 831 -> 972 | 55 | 60 -> 55 | 25 | 8 |
| best up | 0.99 -> 0.48 | 45 -> 42 | 690 -> 737 | 55 | 55 | 30 | 8 -> 6 |
| best climb | 0.74 -> 0.68 | 150 | 1002 -> 1197 | 50 | 55 | 15 -> 10 | 6 |
| best turn | 0.46 -> 0.45 | 31 -> 25 | 377 -> 440 | 30 -> 25 | 30 | 20 | 4 |
| best crest | 0.86 -> 0.36 | 121 -> 91 | 727 -> 849 | 55 | 60 | 45 -> 40 | 6 |
| best h_up | 0.48 -> 0.40 | 47 -> 41 | 701 -> 773 | 60 -> 55 | 60 | 35 | 6 |
| best h_down | 0.39 | 41 | 1502 -> 1504 | 55 | 65 -> 60 | 30 -> 25 | 6 |
| best tow | 0.41 -> 0.38 | 51 | 1102 -> 1229 | 50 | 55 | 5 | 10 |

- **Hills and tow hold;** upright, step and turn don't. Across the 15 the worst copy costs a median 8 % of upright, 9 % of step
  and 11.5 % of turn, and nothing on hills, crest or tow. The all-rounder order's top group stays, with `best up` moving up to first. That rank is a
  design's worst gauge, so it doesn't see `best up` lose half its upright: its step ranks lower still.
- **Upright is the tail servo's strength** (`single`, one error at a time, upright):

  | Servo strength | 100 % | 95 % | 90 % | 85 % | 75 % |
  |---|---|---|---|---|---|
  | T3 (3.31 N m) | 1.00 | 0.995 | 0.92 | 0.755 | 0.63 |
  | best up (4.0 N m, the knob's top) | 0.995 | 0.975 | 0.505 | 0.495 | 0.48 |
  | best crest (2.56 N m) | 0.865 | 0.845 | 0.635 | 0.455 | 0.39 |

  CoM, mass, tyre and motor errors alone move these three by 0.065 at most, inside the floor. The knob is the servo's stall
  torque and the sim gives all of it for as long as asked; a real servo won't. Its mass grows with torque (`robots.add_limb`),
  so nothing rewards spare strength. Probably the search settles just above each design's cliff (not checked on more designs).
- **T3's step is a cliff too:** x+5 reads 57, motors 15 % weaker 85, servos 15 % weaker 90; x-5, y+2, z+3, 5 % heavier and the
  smaller tyre all keep 150. Why isn't traced.
- **Turn goes both ways with the CoM:** T3 reads 432 at x-5 and 514 at x+5, `best up` 728 and 625. As G3 says, it reads where the CoM
  sits against the wheels' centre. A real robot can trim that by moving a pack, unlike a servo's strength.

**Not modelled:** the belly's height, parts shifting in a fall, hulls printed out of shape, G8 rough ground. Designs of the
250 mm cap may behave otherwise: none has been read this way.

## The 250 mm run (2026-11-07, wired, not run)

`SCORPION_CAP=capability_250 SCORPION_UNTIL='2026-11-08 07:00' python gauges/capability.py run` -> `out/capability_250/`.
Without SCORPION_UNTIL its deadline is the strict run's, long past, so it would stop after B. Two calls from Zach:
- **A cap:** the body and wheels at most 250 mm; the claws and tail don't count ("Longer prints are easy on pla, if we
  want better materials it gets more risky depending on how long it prints for").
- **The head out of the body** ("Theres a good chance that is going to be blocked in some way for most bodies. We would
  want the flexibility to be able to move that somewhere else").

What changes, for a design with the new knob `head_f` only (the runs before rebuild as they ran):
- **The head on top** (`search.HEAD_OUT`, `knobs._place_head`): the skin no longer wraps the head, so the parts inside
  span 239 mm, not 270. The head's base sits flat on the body's top, on the highest point under its footprint, its pan
  axis on the centre line at `head_f` of the way from the back (0) to the front (1), the base wholly over the body. Its
  210 g moves with it. In the sims it's two hulls (base and drum, cradle and ball), part of the body: it lands in falls
  and stops the tail.
- **Refused:** the stowed tail through the head, the tail's turntable in its way, a flipper sweeping through it
  (`knobs.head_problems`); a body print over 250 mm on any side (`knobs.cap_problems`: the hull and the motor pods; not
  the head, tail or claws; the tyres may stand out past it).
- **The space:** the rough run's protocol and gauges, every body a skin (the Trainer's own tub is 276 mm), the body's
  size knobs narrowed to what 250 mm holds (`capability.CAP_RANGES`; with the old ranges not one of 480 samples passed),
  and B of 4,096 (refusals cost about a second; screens are the cost).
- **Pass rate, 480 Sobol samples:** 15 % build. Four wheels 28 %; six wheels 2 %: in 250 mm a six-wheeler fits only
  with tyres under about 45 mm radius. The other refusals: flipper pairs more than 30 mm off a narrow body (they sit
  outside the tyres), weak drives, the tail stowed onto the head. Built bodies run 216-245 long, 212-241 wide, 99-228
  tall.
- **Controls:** 51 tow-run designs rebuild identically under this code and HEAD's; with `head_f` added, 26 of them
  change. T3 (323 mm skin) is refused for size; T3 with its head at the back is refused, its tail stowing onto it.
- **Smoke** (`SCORPION_CAP=capability_250 python gauges/capability.py smoke`): the space's middle builds (body 216 x
  222 x 150, the head on top to 302 mm) and reads all eight gauges in 51 s.
- **Not modelled:** a dome or guard over the head; the cradle's 44 mm pan sweep against a body that rises past the
  base's footprint; a fall that lands on the head (G1 reads upright only).
- **Found later the same day** (`gauges/self_righting.py`): inside `CAP_RANGES` the skin's shape knobs barely move the
  body. It's the hull of the parts and the motors, a box (400 shapes, head off, no tail: static upright 0.17 to 0.17).
  A shell that rights the robot by itself would need about 385 x 347 mm round these wheels. Under 250 mm the tail rights
  it (97 % upright in 120 falls) or an invertible layout drives either way up (96 %). Zach has since moved the camera
  to a pinhole in the nose (`docs/decisions.md`), so this run needs its head knob changed before it runs.

## One body (2026-10-28)

Zach, on the capability page: "a lot of floating parts. Make a check to ensure everythings connected when sampling
these and they actually fit as a cohesive body", then "it kinda needs to morph towards the wheel base when the shapes
are further out and not connected", "merge in something like the front plate in a smooth way to the shape of it",
"there also are not enough of a smoothing for the wheels. it clips only in the middle", and "There should be size
limits on the wheels to a realistic proportion for a motor that can move this thing".

A design was a body hull plus mass items, and nothing tied the items to the hull. Without a skin the body is the
Trainer's tub (140 mm wide, 328 long, its wheel pods left out), so wheels moved by the wheel knobs could sit far from
it. `knobs.cohesion()` measures how each part meets the body; `knobs.problems()` applies the rule; `python
gauges/knobs.py cohere` runs it on T3, the Trainer's own layout and T3's 170 mm mount (all pass) and five controls
(each fails on its loose part, then builds whole under strict).
- **The rule:** a part touches the body or stands off it on at most a 10 mm bracket*. A motor reaches 5 mm* into the
  body (the Trainer's own layout: 10); the tail's turntable, about 40 mm across*, has its centre within 30 mm (T3's:
  26); the push plate within 10; a pack inside the tub within 2.
- **Strict** (`knobs.make(q, strict=True)`): the body's hull grows to take in each loose part (a motor's box out to
  2 mm short of its tyre, a pack, a 40 mm block at the tail's turntable), and the push plate always joins the hull,
  which fairs it in. The added hull weighs as the skin does (1.5 mm PLA). Whole designs don't change: T3 strict is T3
  to the gram. Searches from here sample strict; the runs before rebuild as they ran.
- **Wheels and motors:** the sim's motor gives its stall torque as long as asked; a real one runs at about a third of
  it* without cooking. Each wheel's motor, at a third of stall, must hold the robot on a 30° slope*, so the wheel's
  size is capped by the motor and gearing: with the stock 37 mm motor geared 2x, a 3.4 kg robot may run wheels to
  167 mm radius, a 5 kg one to 114. It refused 6 % of the first run's designs and none of its champions. Its
  champions ran motors 1.3-2x the stock size (msize) geared about 2x, so the strict run holds the motors at the stock
  37 mm (Zach: "hold the drive motors at the stock 37 mm size"); the gearing still searches.
- **Wheel wells:** the skin is widest at its middle, so a six-wheeler's middle tyres sat 22-56 % inside it (front and
  rear 13-30 %; T3's 14-16 %). Every tyre now gets a well, 5 mm* clear all round, cut from the body for the page and
  the picture (`robots.with_wells`, exact booleans). The sims keep the convex hull: what a well removes lies inside
  its tyre's reach. No internal part can reach a well: the narrowest track (110) with the widest tyres (80) leaves the
  packs outside the tyre's path.
- **First run, checked:** 1,549 of 3,423 designs whole (45 %). Failures: 1,115 motors short of the tub, 479 packs out
  of the tub, 956 push plates, 271 tail mounts. Skinned designs always held their motors (the skin wraps them).
- Picture: `python gauges/cohere_sheet.py` -> `out/cohere/cohere_sheet.png` (three designs, first run against strict).
- **The strict run** (`SCORPION_CAP=capability_strict python gauges/capability.py run`, `out/capability_strict/`, to
  00:30 on 2026-10-29): the capability search's space, seeds and protocol, every design strict, the motors at the
  stock size (27 knobs). A first start with the motor size free was stopped after 253 screens
  (`out/capability_strict/superseded_msize_free/`). Results: below when it ends.

## Front flippers (2026-10-28, in progress)

Zach: "flippers have got to be a future knob i bet they would help a lot with the steps", then "build front flippers as
a knob and test them on the step". `robots.add_flippers`: a pair on the front axle's line, outboard of the tyres and
the body, or one on the centre line 20 mm ahead of the nose; each a link with a rubber tip on a pitch servo
(`knobs.FLIP_KNOBS`: length, torque, stowed, lift and press angles, the nose pivot's height; switches for the
placement and for working with the tail). They meet the floor and terrain, never the robot. Their move is in the step
reflex (`gauges.Reflex`, now shared with G6): on a stall they lift over the step and press down. Designs without
flippers read exactly as before (20 of 20 climb and crest runs identical to the bit; a changed seed changes all 20).
- **First look, by hand on T3:** no gain (150 mm with or without). Lifting the front alone rears the robot to 63-65°
  and it falls back: T3's wheelbase (152 mm) is its step, and past it the back has to rise too. Lifting with the tail
  pushing raised the whole robot to the step's height, then left it bridged on the flipper tips and the tail foot,
  wheels in the air; easing the flippers to level after the press brought 150 back, not 175. Hand-set moves are the
  wrong tool here (a learned policy would choose them).
- **The search** (`python gauges/flippers.py run`, `out/flippers/`): flipper settings with the wheels' size and
  wheelbase, everything else at T3's, strict, the turn held to 450 mm; the same budget without flippers as the
  control. **No gain:** both arms top out at 150 mm (with flippers 150 mm at 410-436 mm of turn and 320-550 g more;
  without, the best is T3 itself, 150 / 392). Read under the old tail physics (the tail passed through the body).
- Guessed*: each flipper servo 45 g + 8 g per N m (as the tail's), the link 0.3 g a mm, the tip 10 g and 10 mm round,
  6 mm clear of the tyre; the move's timing (lift 0.3 s, press to 1.0-1.2 s, ease or stow after).

## Anchor-first bodies and printed trees (2026-10-28, prototypes, not in a search yet)

Zach, on the strict search's random shapes: "those do not look good ... lets see if we can find a more elegant
solution", then "you could try picking the points you need before generation instead of after". The old generator
built a body and placed parts by their own knobs, then repaired what floated; these pick the points first and make the
body join them, so nothing floats by construction.
- **`gauges/body.py`:** wheels (radius, width, the axles along the body, front and rear widths), the nose point, the
  rear point and the ride height are picked in that order; the parts inside set the top (Zach: "maybe not the top
  point"). The body is the hull of that profile with a flat bottom and a round mount (a ring of points) in its side at
  each axle, as the old skin's flat bottom was a ring at the cut (Zach: "can you basically do that with little circles
  on the sides for wheels"). The motor's round housing runs from the mount to the tyre; the tail sits on a round boss
  on the rear face, its stowed and push angles picked only from those that clear. `python gauges/body.py sheet` draws
  Sobol samples, rendered by MuJoCo (the matplotlib sheets drew wheels in front of the body: its depth sorting).
- **`gauges/body_tree.py`:** the wheels on printed legs (Zach: "like trees on 3d printed supports"): per side a
  trunk from a round root in the side, out to a fork, branching to each wheel, or a leg per wheel. The legs' angle up
  or down comes from the anchors (the ride height is its own knob). Clearances are built into the anchors (a wheel
  starts where its motor tube clears the body; a curve's controls stay between the body and the tyres): 186 of 256
  draws could be made, against 24 when clearances were only checked after. Each 37 mm motor slides into a printed
  tube (6 mm wall*); its leg lands on the tube's top and merges into it, clear of the motor (Zach: "it clips through
  the motors"); a leg flares 1.8x where it meets the body (Zach: "the width of the trunk should widen").
- **Braced legs** (Zach: "they dont have to be exactly like the supports work"): without a tree, each wheel takes 1, 2
  or 3 legs from roots spread along and up the side, each gripping the motor's tube on its own root's side, so a pair
  or a tripod clamps the tube from two or three sides. A single leg is a cantilever; a triangle carries a load along
  its members (`python gauges/frame.py check`: the same tip load, 18 times less stress braced).
- **How thick a leg must be: the sim** (`gauges/snap.py`; Zach: "can we test where it would snap? maybe we should just
  let the simulation do the thinking"). MuJoCo gives the loads where the structure meets the world (each wheel's push
  on its axle, any contact on a leg or tube), in the robot's frame, through G1's falls (24 from 300 mm, every step, a
  5 ms running mean); `gauges/frame.py` solves the legs as round beams clamped at the body, each tube a stiff link, so
  braced legs share the load by stiffness; each segment is sized to half of PLA's strength across its layers and the
  design dropped again. `python gauges/snap.py check`: the loads agree moved and turned (the world-frame reading, the
  control, differs by 1,808 %); the roots hold exactly what the wheels push.
- **What the sim says** (`python gauges/snap.py compare`, `out/body/snap.png`, four base designs): legs as first built
  snap (37-65 MPa against PLA's 25); sized from the falls every design holds, single beams needing 330-862 g of legs,
  braced pairs 17-25 % less (261-688 g), tripods no better (one tripod didn't settle: 24 MPa). In a pair the stiffer
  leg takes most of the load. The tyres' softness sets the landing loads: the gauges' contact puts 64 times the
  robot's weight on one wheel in a flat landing, a 30 N/mm* tyre 7; tumbling landings put 1.3-1.7 kN through an axle.
- **One shape, the generator's output** (`gauges/blend.py`; Zach: "blend or generate it into one shape with the motor
  attached properly", then "were not printing here were updating the generator"): the body, legs, tubes and tail boss
  as distance fields under a smooth union (8 mm* fillets), each motor's bore and each wheel's room cut sharp, marching
  cubes at 2 mm. `body_tree.sized(q)` is the generator's design: legs sized from the falls, refused when the sized legs
  no longer fit their routes or still snap; then it braces harder and tries again (Zach: "retry"): a single leg a
  wheel to 2, then 3; a tree to 2 legs a wheel, then 3. `python gauges/body_tree.py sheet`: of 15 Sobol designs, 11
  hold as one body (8-24 MPa; two of them braced from one leg to two), 4 are refused: their sized legs don't fit even
  at 3 legs a wheel (three six-wheelers, their tyres 15 mm apart, and one tree). Before the retry, 9 held
  (`out/body/trees_before_brace.png`). A slim leg's end sits by its own radius (the first blend left two tubes loose). The sims keep the
  convex pieces and capsules: the blend only adds fillets. (A clamp, bore fit and print split were drafted and dropped:
  not this stage.)
- **Superseded, the same evening:** the first snap test read the loads in the world's frame but the legs in the
  robot's (right only at rest at the origin, where its check ran), and reported 180-310 MPa: wrong lever arms.
- Guessed*: the tyre's 30 N/mm and 0.3 damping (a weight on one wheel and its squash would measure it), PLA's 25 MPa
  across layers, the 0.7 bending efficiency, the safety factor 2, the tube's 6 mm wall, the 1.8x flare over 30 mm,
  half fill for the legs' mass. Not modelled: the body's wall where a leg roots (clamped as rigid), the joints' detail.
- **Found weak where it wasn't modelled (2026-10-29):** the same designs, landed on one wheel by `gauges/fem.py` with
  the root modelled (below), read 41-136 MPa, every peak where a leg meets the body's side. "Holds" above is
  superseded for these designs (`docs/lessons/2026-10-29-a-rigid-root-hides-the-joint.md`).

## One-piece bodies (2026-10-29, a prototype, not in a search yet)

Zach, on `out/body/trees.png`: "it doesnt look right like it is a realistic thing id be able to print the shape seems
weak in key areas", "the bodies seem weakest if there dropped onto a single wheel at an angle", "it needs to feel more
like one shape and less like a shape with 3d printed trees on it. Maybe trees were the wrong path".
- **`gauges/unibody.py`:** the robot is one signed distance field from the start: body_tree's anchors (the same wheel
  layouts) give the body (its edges rounded), a boss round each motor and the parts bay; random pieces join them (an
  arm from each boss into the side, a deep oval, not a rod; a pod along each side; a beam across an end pair clear of
  the body; up to 6 blobs a side; a ripple), all under one smooth union of 15-60 mm (webs, not 8 mm fillets), mirror
  symmetric. Then the wheels' rooms, the motors' bores, the bay (the body hollow to a 6 mm* sandwich) and the ground
  are cut. Whatever the cuts leave loose is dropped, and a loose motor boss refuses the design, so every draw is one
  piece. 13 shape knobs on top of body_tree's layout knobs.
- **Fixed the same evening:** the ripple first ran both ways and dented the body's skin through to the bay: 7 of the
  first sheet's 15 had holes in the top, 6 came out in 2-34 pieces (`out/unibody/superseded_ripple_holes/`). It adds
  bumps only now; the seven read one piece, the skin whole, and with the ripple off they did before too.
- **Strength from the shape, not rods:** a print's strength is its walls far apart, so a big hollow section beats a
  solid rod per gram. `gauges/fem.py` solves the shape's own voxels (4 mm bricks, PLA, each voxel's stiffness the
  share that is wall, 1.6 mm*, plus 15 % infill at 0.06 of PLA's stiffness*), on the GPU with a multigrid
  preconditioner (29 iterations, 5 s a landing; plain Jacobi took 4,000 and 68 s). A landing is held by the robot's
  inertia on the bay's walls, not a clamp. `python gauges/fem.py check`: a cantilever's stress and tip against beam
  theory, half as deep reads 3.5x (the control), a printed box beam against thin-wall theory, the inertia's 3-2-1
  reactions zero.
- **The landing:** each left wheel pushed by 1.5x* a 300 mm drop into one tyre's 30 N/mm spring (1.3-1.4 kN, snap's
  measured range), up, 45 degrees in, out, forward and back, and flat sideways. The motor's collar (14 mm* round its
  bore) is read apart: it's the mount's number (a 25 mm collar on an 81 mm motor whose load sits 47 mm outboard).
- **Grown where it's weak:** the field swells up to 5 mm* a round where the wall passes 12.5 MPa, carried 12 mm* out
  from the voxel so a peak under the surface moves the surface, for up to 6 rounds. It's Mattheck's CAO (1990,
  shape optimization by biological growth); its partner SKO (1992) removes what carries nothing, not built yet.
- **Against the trees** (`python gauges/unibody.py compare`, `out/unibody/compare.png`): body_tree's sheet designs 2,
  5, 7, 10 and 12, the same landing, the same bay and print. Trees 41-136 MPa (roots; collars 48-134); unibodies on
  the same wheels 13-23 MPa as drawn, 12-17 grown (collars 12-21), one under 12.5 (growth stalls about 15). They
  weigh more: shape 2.1-2.9 kg against 1.6-2.1, robot 5.0-6.3 kg against 4.2-5.0. Tipping angles match (32-62
  degrees): the wheel layout sets them, not the body.
- **First sample, superseded** (`out/unibody/superseded_collar_mount/`): 15 of 15 one piece, 2 held, the rest 14-27
  MPa where growth stalled beside a short, overloaded collar (30-48 MPa); shape 1.5-3.7 kg, robot 4.5-7.4 kg.
- **The motor by its face plate** (Zach: "the motor i have has screws and a face plate"): the Trainer's corner module
  (`chassis-v2/wheels.py`). The pod ends in a 5 mm* lip the gearbox face screws to (6 M3 on a 31 circle*), the wheel
  is a dish over the pod, and a landing goes in through the gearbox face as a rigid motor would carry it. The wheel's
  centre sits within a few mm of the face, where the collar had it up to 47 mm out. A wheel too small to wrap the pod
  (R under 43) sits outboard on a shaft extension (flagged on the sheet); if that pushes the motor into the parts,
  the design is refused. `python gauges/unibody.py section [seed] [k]` draws the cut through a pod, the motor in it.
  The motor's numbers are the 37D class's datasheet* until Zach's are in.
- **SKO** (Mattheck's soft kill, 1992): each round also cuts back, up to 6 mm*, where nothing within 6 mm carries half
  the allowed, never into what must stay (the body, the pods, the bay wall). A knob, `trim` (0-40 mm), caps how far
  it may cut: fully trimmed, the blobs go and stress-shaped legs return (they're the efficient load path), so the
  search holds the trade between one blobby piece and a light one. First tried at 4 MPa within 12 mm: 7 % off in
  three rounds. On sheet design 5, full trim took the shape from 3.5 to 2.4 kg.
- **Fixed:** only the left wheels land (the shape is mirror symmetric), but the growth and trim maps weren't mirrored:
  CAO had grown only the left side, and SKO found the right side idle and cut a motor loose. Both maps now take each
  voxel's larger stress of itself and its mirror, and the grid is mirror symmetric sample for sample.
- **The solve's resolution:** the same design's first peak read 11.6 and 13.5 MPa on grids a voxel apart. Read the
  voxel solve's peaks as about 15 % either way.
- **Drops as it goes** (Zach: "test there durability as you go"; `gauges/drops.py`): each design falls as G1 drops
  it (24 from 300 mm, random orientation and spin, tyres on snap's spring). MuJoCo gives every push at each fall's
  hardest moment (a 5 ms mean): each wheel's on its axle, every floor contact on the body (the body as 40 convex
  pieces cut from its own voxels). The stress solve takes them all; a body contact is spread over the surface within
  15 mm*, and that patch is read apart like the motor seats. `python gauges/drops.py check`: at rest the pushes sum
  to the body's weight, all through the wheels (53.7 N against 53.7); mid-air, the control, they read 0.
- **Body hits, not wheel landings:** sheet design 4 holds its wheel landings (12-13 MPa) but its falls read 33 MPa, 14
  of 24 over; the worst fall puts 86 % of a 3.4 kN push on the body, and the peaks sit on the body box's top edges.
  SKO had been cutting against the wheel landings alone. Each round now grows against both. Grown against the falls
  recorded at the first round (dropped afresh each round, the hits moved and the peaks wandered 29-41), design 4 went
  33 -> 25; dropped afresh at the end it read 34, 19 of 24 over: the box's 6 mm walls are thin all round its top
  edges, not in one spot. A thicker or rounder box, or bumpers, not local growth.
- **The fall load is a guess:** a body hit is the fall's momentum over the 5 ms mean; nothing models how much a PLA
  edge or the floor gives. TPU bumpers would set that give, as the tyres' spring does (Zach prints TPU).
- Fixed on the way: a body contact first spread over its 8 nearest nodes; the voxels beside them read 74-98 MPa.
- **Hard bodies all fail their falls:** the first three of a sheet grown against falls read 42-57 MPa (19-24 of 24
  over), and growth piled on 0.1-0.5 kg chasing them; that sheet was stopped there (`out/unibody/` 2026-10-29 23:30).
- **TPU bumpers** (`python gauges/drops.py bumpers`, `out/unibody/bumpers.png`): one design, the same 24 falls, the
  body hard or on a spring as the tyres are. Hard: worst 25 MPa, 15 over, 1 past PLA's 25, the worst push 3.75 kN, 86 %
  on the body. 100 N/mm: 21, 16 over, none past. 30 N/mm: 17, 13 over, none past; the worst push 1.6 kN, now on a
  wheel. Bumpers are a knob now (`bumper`, `bumper_k` 20-150 N/mm*); their mass is 3 mm* of TPU over 30 %* of the
  surface; where they sit isn't drawn yet.
- **The falls are noisy:** the worst of 24 moves a lot with small shape changes (design 1 read 25 as drawn, 42 grown).
  Read the count over the allowed before the single worst.
- **Sample with falls and bumpers** (`python gauges/unibody.py sheet 23823 [resume]`, `out/unibody/sheet_1to7.png`
  and `sheet_from_8.png`, `falls_vs_mass.png`; 12 designs, 6 rounds each against both tests, 2 workers: three ran the
  12 GB card out at design 8). Every one is over on its falls (28-84 MPa); the landings read 10-23. Weight decides it:
  the only design that mostly survives its falls (6, 4 of 24 over) has the lightest shape, 1.65 kg; every shape over
  2.6 kg fails 13-24. Bumpers help a little at a weight (design 10, the softest at 23 N/mm: 17 over at 7.5 kg). The
  growth against falls adds 0.1-0.7 kg chasing them. The next lever is weight: trim harder, smaller blobs.
  *Corrected 2026-10-30:* the bumpered designs' shape masses counted the TPU over the whole skin, the bay's walls too
  (1.6-2.1x its hull share), so they read 0.3-0.8 kg heavy: design 12 was about 1.9 kg of PLA and still 17 over, at
  107 N/mm. Weight alone doesn't decide it; only one design (6) supports the cap.
- **Against the trees, with falls** (`python gauges/unibody.py compare`, `out/unibody/compare.png`; rows cached in
  `compare_rows.pkl`, so a crash keeps finished pairs). Falls past PLA's 25, of 24:

  | body_tree design | trees: landings, falls broken, shape | unibody grown: landings, falls broken, shape |
  |---|---|---|
  | 2 | 136 MPa, 10, 1.7 kg | 19 MPa, 13, 3.0 kg |
  | 5 | 73, 4, 1.6 | 12, 1, 3.8 |
  | 7 | 54, 7, 1.6 | 21, 7, 2.8 |
  | 10 | 75, 2, 1.7 | 11, 8, 3.8 |
  | 12 | 41, 5, 2.1 | 17, 16, 3.1 |

  The unibody cures the wheel joints every time (11-21 MPa against 41-136), but at 1.0-2.2 kg more it breaks in
  more falls (45 against 28). **Growing against the falls doesn't work:** round the fixed hits it raises warts (a lump
  ringing each contact patch, which is read apart), and on design 12 the falls got worse round by round (36 -> 47,
  53 dropped afresh). Next: the falls as the verdict only, growth against the wheel landings alone, and the body hits
  answered by weight and soft bumpers.
- **Capped, on soft bumpers (2026-10-30, Zach: "Yes, do that")**: growth answers the wheel landings alone; the falls
  are dropped on the drawn shape and the finished one, the verdict; the printed shape is capped at 2 kg* (`CAP_G`); TPU
  bumpers are always on, the knob their stiffness (`bumper_k`, 20-60 N/mm*).
  - **Trimming can't take weight off:** a print weighs its walls (area x 1.6 mm); shaving a surface moves the wall in
    and takes only infill. One 2.97 kg shape, SKO cutting all it could (everything carrying under the allowed): down
    50 g a round, 2.83 kg after 6 rounds; the same design uncapped, the control, 3.18 kg. So the cap refuses a draw
    over it as drawn (about 6 draws in 7 at today's knob ranges), and the harder cut stays for shapes that grow past it.
  - **The bumpers' mass was overcounted:** their TPU had been spread over the whole skin, the bay's walls too, 1.6-2.1x
    its share. Now 30 %* of the convex hull's area, 3 mm* thick, on the skin within 10 mm of the hull (about 400 g),
    and kept out of the shape's mass (`bumper_g`; the robot carries it).
  - The sheet (`python gauges/unibody.py sheet 1030 [resume]`, `out/unibody/sheet.png` and `sheet_from_8.png`; the
    sheet grown against the falls moved to `out/unibody/superseded_grown_against_falls/`): 12 designs made of 81 draws,
    4.7-6.7 kg robots (were 5.3-7.9). **Falls past PLA's 25 MPa: 8 of 288, 10 designs with none** (the sheet grown
    against the falls: 71, 1 design). Over the allowed still 168 of 288 (were 223): break-free, but at half the
    safety factor. Growth against the landings alone helped the falls too (broken 33 drawn -> 8 finished). None holds
    its landings (14-26 MPa; were 10-23), and 4 grew past the cap chasing them. The lighter shapes, the soft bumpers
    and the mass fix all changed at once, so the sheet can't say which did it.
- Not yet: the sims still see the pieces' convex hulls (the blend and the growth add material they don't see); the
  print split; SKO; a motor mount that isn't a collar.
- Guessed*: the 6 mm bay sandwich, 1.6 mm walls, infill's 0.06 stiffness and 15 % mass, the 1.5x landing, the 30 N/mm
  tyre (snap's; Zach will print TPU tyres of any kind, so a softer one is a lever: the load goes as its square root),
  25 MPa across layers and the factor 2 (snap's), the growth's 5 mm and 12 mm reach, SKO's half the allowed within
  6 mm at 6 mm a round, the motor (37D datasheet: gearbox 37 x 22, motor 34.5 x 33, encoder 30.5 x 11, shaft 6 x 15.5,
  6 M3 on 31), the 5 mm lip, the 8 mm seat read apart; the 2 kg cap, the bumpers' 20-60 N/mm, 3 mm and 30 % of the
  hull. The motor is a JGB37-520 (Zach, 2026-10-30; shopping list and the ESC question in `gauges/SHOPPING.md`), not
  bought yet, so its numbers are still the 37D class's datasheet; Zach's two INJORA 540 55T stay with the rover.

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
- 2026-10-27: G6 crest and G7 push proposed (`crest.py`, `push.py`), both controls passing after two first picks
  failed (T3 at 15 mm ride height for the crest; half grip read at the band's worst for the push). The knob log reads
  them on every setting and works through the six candidate knobs plus three new (tyre grip, tail foot, push face). A
  gauge's terrain or objects now go in after the robot's body, so its free joint stays first in the state; the tyres
  take contact priority. T3's crest sits on a plateau and reads 25° or 40° by luck. Raising the tail mount to 170 mm
  takes T3's push from 1 to 4 kg.
- 2026-10-27: Zach adopted G4-G7 with targets: the hills as steep as they go, the crest at least 20°, the push at
  least 3 kg. None is on the scorecard page or in a search's screen yet.
- 2026-10-28: G4-G7 on the scorecard page (`card.py read`, then `export.py`): the roster, the shape study's finalists
  and T3 with a 170 mm tail mount, each gauge's controls passing in the same pass. GAUGES_CURRENT moved from the body
  search to the shape study. The hills and the push re-read the same; the crest moved by up to 15° on three designs
  (G6). `export.py` had dropped each G1-G3 control's claim and reading from the page (a comment swallowed them);
  fixed. G3 found to read mostly the CoM's fore-aft offset from the wheels (G3). A knob review sorts the knobs into
  dead, settled, floors and levers (the knob log).
- 2026-10-28: the capability search (every knob free, every gauge maxed, no weights): each gauge's ceiling, two
  families, T3 still the all-rounder; the all-rounder stream's percentile score failed. Front flippers logged as the
  next knob (Zach).
