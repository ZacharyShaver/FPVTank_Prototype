# Decisions

Why each design went the way it did. Newest first. A reversed decision stays here, marked
**superseded**.

## 2026-10-27: The gauge search runs lean; a new step reflex; the body's shape searched

A review of the drive search found that 39 % of its random draws couldn't be built, that its screen read upright
0.05 high, and that half its refinement idled. Zach asked for the fixes (`gauges/README.md`, "The lean search"). The
wheels are now drawn as a centre and a tyre gap. Falls are screened at x1.5 and x0.65, and a design is cut once it
can't make the bar. Refinement runs stop after 3 generations without a gain. The search took 1,354 s against 2,252,
and the screen-to-final drift in upright fell from -0.057 to -0.011.

- **Not done, with evidence:** the review proposed freezing 14 knobs a random forest ranked as dead. Redrawn together
  near the front they cost T10 as much as the tail control did. Only three were dead, and only they are frozen; the
  skin's shape is held at T5's by choice (`docs/lessons/2026-10-27-dead-on-average-is-not-dead-at-the-front.md`).
  Bisecting the climb ladder was dropped too: 12 of 42 final ladders pass above a height they fail.
- **Found:** those ladder gaps are the scripted push's (the stall trigger never fires at 40-50 mm, and at 60-70 mm the
  push is too weak). G2 reads the controller as much as the body. Changing the reflex is a gauge change, Zach's call.
- Unseeded, the lean search didn't reach T10's corner. Seeded with the drive search's designs, it found nothing
  better, so T10 (T12 in the lean finals, 0.945 / 100 / 405) is still the all-rounder. (**Superseded** the same day:
  see the next two points.)
- **G2's step reflex changed** (Zach: "fix and rerun"). Stalled now means under 15 mm of travel in 0.3 s. Nose up
  past 12°, the tail pushes; level, it kicks for 0.3 s to free a nose caught on the lip, then looks again. On the
  drive finalists, worst over the band, T1 went 50 -> 100 mm, T2 and T7 50 -> 90, T8 60 -> 100. Designs without a
  limb read identically. It is still a script; a learned policy would replace it.
- **The body's shape is a knob again.** Zach noted the finalists all wore the same body unless skinned, though the
  shape could be turned. The body search frees the skin's eight shape knobs. The search alone kept the Trainer's
  body; a refinement held to skinned designs found T5: 0.96 / 150 mm / 403 mm, a 732 g domed skin with a 279 mm tail.
  It climbs 50 mm more than the best skinless design in the same turn, and is the all-rounder now.
- **Then the body's shape alone** (Zach: "lock some knobs at a constant since were testing how a new shape effects
  this"). On T5's platform, wheels, drive and tail held and the tail's mount pinned, the shape study found T3:
  1.00 / 150 mm / 381 mm with a 485 g skin, low and no wider than the wheels. It beats T5's own skin on all three. The
  same platform on the Trainer's body reads 1.00 / 90 / 441. Climb hangs on how far the nose reaches. T3's nose is
  within 10 mm of the point where the climb falls to 50-100 mm, so a real one wants margin.
- **Hills, proposed as G4 and G5** (Zach: "how far of a hill it can climb/descend before falling"). Read as the
  steepest slope before tipping, on grippy ground. On the band's floors every design slides first, at 25° up and 30°
  down, the box included. T3 reads 35° up and 45° down against the box's 45° and 50°. Its tail braced behind
  like a wheelie bar takes it to 50° up; nothing helps it down. The shape moves the hills only about ±5°. A
  sharp-turn rollover test was checked and dropped: a skid-steer turn tilts even a fast, top-weighted control under 1°.
  (The numbers are **superseded** the same day: the 300 mm hill passed designs that were toppling slowly. See the next
  point.)
- **Hills with the wheels and packs unlocked** (Zach: "unlock those yes"). The hill went to 2.5 m first: on 300 mm
  and then 800 mm, designs just past their tip angle passed by toppling slowly, and the search found that gap. Every
  stowed reading is now held to its static tip angle, the exact limit at constant speed. On it T3 reads 35° / 40°,
  the box 45° / 45°. The tail braced behind gives T3 45° / 45° at no cost. Hardware past that costs: 50° down takes
  210 mm more turn (H2), 60° the step as well (H4); keeping T3's step and turn it buys 5° up, nothing down (H5,
  bigger wheels). On ordinary ground every design is tyre-limited at 35-40°. The finding: T3's platform can stay, and
  hills can be the tail's job; G4 and G5's targets are still Zach's call (`gauges/README.md`, "The hills run").

## 2026-10-26: The Scorpion's requirements are gauges with levers, three to start

After the paper went in, Zach restarted the design from requirements: nothing built so far is final. His framing:
each requirement is a reliable test that reads a number, and the number to reach is a lever he sets each iteration,
because the levers conflict (the E4 shell's righting cost it maneuverability). Real experiments prove a gauge when a
decision needs it. He chose to start with few gauges, so fewer things are tested and a failure is easier to trace:
upright after a fall, step up and turn-around space, his three named levers. `gauges/README.md` holds the cards.

- Every reading is the worst over a friction band, and a plain box (the Trainer's parts) is read every time as the
  baseline. Each gauge has a control that must read worse.
- The purpose behind them: AI embodiment, a robot dropped anywhere that survives, gets where it needs to and moves
  things. Indoors and out, up to tall rocks. Learned policies first, scripted moves for fast reflexes.
- Constraints this iteration: every part fits the K2 Pro's bed (hard), his servos and batteries (softer), and about
  $50-100 of new parts.
- Targets (Zach, same day): G1 upright at least 0.75; G2 step up and G3 turn-around space as far as they go. G3 is
  "a meh gauge but fine for now". A generative search over 18 knobs (`gauges/search.py`) found one shape that meets all
  three (S1: 0.96 / 40 mm / 442 mm against the box's 0.61 / 30 / 594), but only with a shell of about 0.8 kg, and no
  shape-only design climbs past 50 mm. The next lever is a limb. (**Superseded** the same day: that shell lay over
  the whole body, counting the walls twice.)
- Then Zach asked for a limb in the family: a tail that pushes on steps and rights the robot instead of a shell. He
  also asked why the model had both a shell and a body: it shouldn't, so the shell became the body (the Trainer's
  walls out, the parts inside one skin; the head inside for now, his call). With the tail, the finals beat every
  tail-less design on all three gauges: T12 reads 0.91 / 100 mm / 424 mm with a 287 mm tail on 2.8 N m servos and no
  skin, and T14 climbs the ladder's top, 150 mm. With the tail limp, the best climber drops from 0.85 / 150 to
  0.41 / 50 (numbers after the 10 s righting cap was fixed).
- Zach then asked for track width, motor size and gearing as knobs (2026-10-27). The search kept the 37 mm 30:1 motor
  and a track a few mm narrower than the Trainer's: the drive guess isn't the bottleneck, the tail is. T10 reads
  0.97 / 100 mm / 404 mm. The search dropped the skin almost everywhere once a tail could right it.
- Building the step gauge found that chassis3's sharp step edge acts as a wall to a cylinder tyre
  (`docs/lessons/2026-10-26-a-sharp-step-edge-is-a-wall.md`). chassis3's climb numbers carry it; its step-down numbers
  haven't been rechecked.

## 2026-10-26: This repo is public, its history rewritten first

Zach chose to make the repo public, the leak audit's option B. Before it went public the history was rewritten:
- every commit's author and committer email became his GitHub noreply address;
- the old Wi-Fi name and password, four private IPs and his Windows user name were scrubbed from 25 files and one
  commit message;
- the third-party files not cleared for sharing were removed from every commit. They stay on disk, gitignored, and
  `THIRD_PARTY.md` records them.

The old history is archived, still private, as `ZacharyShaver/FPVTank_Prototype-private-old`, and backed up locally in
`FPVTank_Prototype-backup-2026-10-26`. The new public repo took the old name, so no old commit is reachable from it.
Every commit hash changed: an old hash, such as the one in the gallery's first commit message, points only into the
archive. Any other clone must be cloned again rather than pulled.

## 2026-10-26: The gallery is public; this repo stays private (**superseded** the same day: see above)

Zach asked for the visuals to be published on GitHub Pages. The gallery goes out from a separate public repo,
`ZacharyShaver/scorpion-gallery` (https://zacharyshaver.github.io/scorpion-gallery/). `tools/gallery/build.py` builds it from
this repo, and `tools/gallery/publish.py --yes` pushes it. ~~This repo stays private, and its history stays as it is: the
leak audit's option A (`docs/audit/2026-10-25-leak-report.md`).~~ Superseded: the repo went public after a history rewrite.

- The build is gated: every link resolves, sizes are under GitHub's limits, external loads come only from the allowed CDNs,
  no file goes out unlinked, and `leakscan` finds nothing in the built site.
- The public commits carry Zach's GitHub noreply address, never the personal one.
- The 14 chassis and head 3D pages are held. They embed third-party part meshes: FPV-Rover V2.0 (CC BY-NC-SA 4.0), a
  PCA9685 board whose licence isn't recorded, and an MG90S whose origin isn't recorded. Publishing them is Zach's
  licensing call. Releasing one means removing its `"hold"` in `tools/gallery/manifest.json`, adding a `"licence"`, and
  rerunning `publish.py --yes`.

## 2026-10-12: Bench stand v2, and the head's pocket in the body (nose section)

Zach: "more room for the gears on height and a spot to pin the black wires to the base so they dont fly in the gears"
(the tilt servo's wires, out of the bottom of the pan axis since set 10), then "the stand should be like a section out of"
the body. Stand v2 (`head-v2/fixes/bench_stand.py`, `RAISED`): the head 12 up on a hollow riser; the floor plate on a
ledge chamfered 30 deg underneath; a slotted post under the axis (bore r 2.4, inside the M3 heads' sweep from r 3.05)
takes the wires straight down; a door at its foot, an arch toward +X (the servo side, his PCA9685), a V cleat. The
ledge is trimmed clear of the M3 heads (they turn 0.35 inside the floor plate's 18.7 hole and read 0.59 off v1's ledge).
Printed 2026-10-12 (1 h 7 m). The screws are reached by lifting the head out now. Marching cubes made zero-area folds
where v2's planes fell on grid nodes, so its grid is offset 0.0371 and its print mesh isn't decimated.

The body (`chassis-v2/nose.py`, the Trainer: rugged.py on wheels) stands the base on the nose floor, so it needs the same
pocket. Two ways drawn: A, the pocket hangs 12 under the nose floor (the belly under the head 30 off the ground, was
42; level with the pack bays' 32) and the wires come up a chimney aft of the base; B, the head 12 higher on the pocket.
He said print it, so A's tub forward of X 26 prints first. Holding the head for a tumble: the turret deck ring gets a
1.8 lip over the base's rim (the bearing seat's ring) and four M3 x 12 into posts from the nose floor. Found on the way:
rugged.tub()'s turret-deck ledges floated 4.2 over the walls (the deck rose 10 with the head, the walls didn't);
nose.py raises the walls forward of the glacis to the deck. A vs B is still open.

## 2026-10-12: The shelf ring goes back into the base (set 11)

Set 10 assembled, the pan turned its full sweep at the bench ("We fixed it!", a video of 500 <-> 2500 us). Zach then
asked to merge "the piece for the cable wrap" (set 7's drop-in shelf ring) into the base: it "has a chance of falling
out of its lock if its gone upside down" (the base goes upside down for the small gear and the floor plate, and only a
2.5 mm rib keyed it), and it "doesnt need to be an extra piece if the wire just runs through the bottom now". And close
the wires' old exit hole on the outside.

Set 7 split the ring off only because the lane under the shelf needed supports that couldn't be got out. Set 10 emptied
the lane, so it fills solid up to the ribbon's floor (Z -20) and nothing overhangs inside the can; the ring's cup wall
stands on the fill, its ribbon notch and the slit unchanged. The rib, the boss at -145 deg and the exit hole go. The 6704
(27 across) still drops in from above before the drum, so the fill leaves a 27.5 hole round the drum (0.25 a side of the
bearing; 1.75 off the drum's face, where the ring's shelf left 0.6). The ribbon's bottom edge stands 1.0 over the floor
and its inner wrap rides on the drum. Set 10's drum, small gear and floor plate are unchanged; only the base reprints
(1 h 21 m, 39 g, supports on; none land inside the can).

He also wrote "im going to leave the well off for this one". Read as: he's leaving the loose ring out of this build. The
ribbon's cup wall is kept (the coil is sized to it); if he meant that wall, dropping it is the `cup` line in `_well_set7`.

Checks (`pan_coil_b_check.py`): `merged_shelf` (the floor, the old lane and the cup solid; the exit hole filled; the boss
gone; control: set 10's base reads no floor and the hole open), and the 6704's way down through the shelf in the
assembly order. **Superseded:** `shelf_ring` as a part (`RING_PART`; `SHELF_MERGED = False` gets set 10 back), the rib
(`KEY_*`), the boss and `BASE_WIRE`'s hole. `checks/wire_route.py` checks the lane route of set 10 and before.

## 2026-10-11: The servo wires go straight down the pan axis (set 10)

Set 9 at the bench: meshed, the pan moved only over 500..800 us; bare, the servo turned its full 180 deg, so the drag
is the head's. Zach found the jumper wires squashed in the lane once everything was screwed down, and the jumpers
spring back like solid wire. He asked why the wires leave the drum sideways at all, and proposed moving the axis
screw out to several screws round a plate the gear bolts to.

Both earlier rejections of the axis route fall together: set 8's (the gear's M3 sat on the axis) and set 9's of a
6704 (its 20 mm barrel ran into set 8's off-axis wire hole). The 688 was the bottleneck: hollowed out, its 7.9
barrel left no wall for screws. So the 688 becomes a 6704 (20 × 27 × 4; he has ~6) at the same height, the barrel
19.9 and hollow, a 6 mm hole from the cone's point straight down through the barrel, the small gear and the floor
plate's existing hole. The gear bolts to the barrel's end on three M3 × 16 at r 5.9. It carries a solid hub on top (22.4 across) that meets
the barrel's end face to face 0.4 under the 6704's inner ring, which is what keeps the drum in the base now; the
button heads sit under the gear and turn in an 18.7 mm hole in the floor plate. The first draft, the same day and never
printed, sank the heads into the gear (0.9 of wall to the wire hole and the teeth) and centred it with a 1.1 collar;
Zach: "the connection for the gear looks extremely flimsy". Now every hole has ~1.4 of wall for the gear's full 8.7.
M3 × 16 because he has few M2 left and "quite a few" of those: 7.3 of thread in the barrel. The wire hole is 5.5. The 6704 can't pass the shelf ring's 25.2 hole, so it goes in first.
The lane, shelf ring and exit hole stay, empty. Zach is also buying 28 AWG silicone wire to replace the springy
jumpers.

Checks (`pan_coil_b_check.py`): `wire_axis` (control: set 9 blocked by the drum and the M3), `races_6704` (control:
the lip in to r 10.0), `screw_threads_6704` (control: an M3 × 12 reads 3.3), the 6704 rows and the assembly order.
**Superseded:** the 688 (`BARREL_688`), the square stub and the axis M3 (`SEAT_SQUARE`, `SCREW_THRU`), set 8's
straight hole and groove (`STRAIGHT_WIRE`); `HOLLOW_AXIS = False` gets set 9 back. `checks/wire_route.py` still
checks the lane route.

## 2026-10-10: The input gear carries the servo's horn; the barrel runs in a 688 (set 9)

First bench run of the v2 head (FPVTank_Control `docs/bench/2026-10-10-v2-head-first-power.md`): tilt works, but the
pan servo can't turn the drum. Bare, it turns its full travel (5 teeth per 500 µs), so the fault is mechanical. Zach
found five things by hand: the input gear slips on the spline (the screw turns, the gear doesn't); it rubs the wall
above it, more as its screw tightens; there's more drag when the head leans; the drum isn't bearing-smooth with the
6809ZZ in; and every screw trades drag for slip.

**Input gear.** Set 6's press bore wore smooth: PLA doesn't hold a metal spline. And the screw set the gear's height:
set 6's own note expected the real 9.0 spline (1.0 shorter than his MG90S model) to let the screw pull the gear 1.0 up
"with room for it", but the gear's top was 0.5 under the servo's block, so the screw clamped the gear against the
servo. Now the servo's own double-arm horn sits in a pocket of its exact outline (Arm02 from Zach's measured MG90S
model; his caliper matched its length, arms, hub and height), at zero offset, the 2026-09-19 rule, which prefers
gripping the arms to the shaft. The spline stops on the horn's web, which sets the height; the gear's top is 1.0
under the block. One M2 × 6 comes up through the gear's floor and the horn's web, 3.1 mm into the spline. The gear is
an exact solid (`fixes/gear_horn_set9.py`): the generator's tooth formula, extruded, with the horn's outline cut
in OCC. Sewing the generator's mesh into a solid came out invalid, and the cut silently did nothing; the control
(the blank against the horn) caught it. **Superseded:** set 6's spline in the gear (`HORN_GEAR = False`).

**Barrel.** It ran in a PLA journal, 0.25 a side, and bore on it as the head leaned. Now it runs through a 688
(8 × 16 × 5; he has many) seated in the base, its top level with the lane's floor, on a lip under its outer ring.
The drum's underside stays 0.4 clear, so the 6809 still carries the drum and the 688 only keeps it upright. The drum
goes in from above through the bearing, so everything below it has to pass the 8 mm bore: the barrel is 7.9 and set
8's 7.0 square stub is 6.0 (corners r 3.91). Rejected: a 6704 (it needs a 20 mm barrel, which runs into the drum's
wire hole 8 mm off the axis). **Superseded:** the journal (`BARREL_688 = False`) and the 7.0 square.

Checks: `pan_coil_b_check.block_air()` (control: set 6's gear pulled 1.0 up reads −0.5) and `races_688()`.

**Reprinted the same day.** The 0.05 small gear was so tight on the 6.0 square that pulling it off tore the square
off the drum; the 0.10 was "not that bad", so 0.10 is the fit (`SQ_FIT`). The zero-offset horn pocket was so tight the
horn flew out of it and hit Zach in the eye: the pocket grows 0.10 a side now, with a 0.15 gear to try
(`HORN_FITS`). It is the horn's whole outline carried 3.4 mm deep through PLA, not the shallow pocket the zero-offset
rule was found on. And the horn kit's own screw (3 mm head, 5 long) couldn't get through the gear's floor: the floor
is open under the horn's centre now (5.0 across), the screw seats on the horn's web as designed, 4.5 mm into the
spline, and nothing clamps the gear (the floor plate sits 0.5 under it). **Superseded:** zero offset on this pocket,
the M2 × 6 under a 1.5 floor, and the 0.05 small gear.

2026-10-11, Zach: the 688 "fits beautifully, feeling very smooth"; the 0.10 pocket "fits well enough with still
being a bit tight, which is good"; the 0.15 is too loose. 0.10 is the fit, and CLAUDE.md's zero-offset rule now names
this exception.

## 2026-10-09: The small gear's screw threads above the step; a square seat; a straight wire hole (set 8)

Zach: the seat at the end of the drum's barrel "keeps snapping", when he tightens the screw (his photo: the broken
seat still on the screw inside the small gear). The M3 × 8 had 4.2 of its 6.2 mm of thread in the seat, below the
step the gear pushes up on. So tightening pulled the seat off the barrel across its layers (the drum prints upside
down) at a sharp corner. Now the seat has a clear hole, and an M3 × 12 threads 5.8 mm into the barrel above the step:
tightening squeezes the step. `pan_coil_b_check.screw_threads()` checks it, with set 7's drum as its control.
Rejected: a fillet at the step (the gear's bore would need a matching chamfer, and the seat would still be in tension).

He asked for "a square going in so it grips better". The gear could turn 7.5° on the D before its flat bit; a
square 7.0 across with r 0.8 corners turns 2.2° at 0.05 a side. The corners reach r 4.62, so the step stays all round
and the seat still passes down the journal. Two gears to try, 0.05 and 0.10 a side.

Threading was "a massive pain", stuck at the cone: set 6's hole started at the cone's point and bent from straight
down to sideways out of sight. Now a straight vertical hole starts under where the wires already come down the notch
(r 8, −127°, behind the ribbon) and leaves through the drum's underside, where an open groove takes them to the lane.
Rejected: running the wires straight down the pan axis through a hollow barrel (kinder to solid wire than the
rolling loop, but the gear's screw sits on that axis, and the screw is what keeps the drum in the base). Moving the
exit also fixed the loop's range: with 74 mm in the lane, set 6's exit let the head turn only 150° one way, however
the loop was laid; set 8's allows 214° and 325°. **Superseded:** the D seat (`SEAT_SQUARE = False`), the pilot from the
seat's end with an M3 × 8 (`SCREW_THRU = False`), and set 6's curved hole (`STRAIGHT_WIRE = False`).

## 2026-10-05: Wheels for training, at least for now; the fenders go

Zach: "the side portions covering the top of the tracks have to go. for training the robot. at least for now. we
have to use wheels tracks get too complicated and we need to be able to run en mass to train." A track in a
simulator is a closed loop of links (the v2 design: ~120 bodies and ~70 contacts); four wheels are four hinges and
four contacts, so many copies can run at once, and the real robot has to match what was trained. The chassis
brainstorm now builds the rugged body on four identical corner modules (`chassis-v2/wheels.py`, `trainer.py`): each
gearmotor rides outside the hull in a printed pod, because the nose holds the head and the packs, with a dish wheel
over it. No fenders, no suspension. The v2 tracks (`legs_v2.py`) are on hold, not dropped.

## 2026-10-04: The shelf drops into the base (set 7)

Zach: Orca's supports in the base's wire lane, under the shelf, are impossible to get out. With his settings Orca
filled the lane all round (3850 support moves): the shelf stuck 8.4 mm in over a 3.5 mm lane. He wants that
overhang support-free. A slope can't carry the shelf: at his 30° off vertical, crossing the lane needs 14.5 mm of
drop, and the lane is 3.5 tall with the ribbon's floor on top of it. He agreed to a drop-in shelf.

So the shelf and the ribbon cup's wall left the base as one part, `shelf_ring`. It prints shelf face down with no
overhang and drops in from above onto a 1.5 mm ledge on the lane wall, with a 0.15 slide. A notch in its shelf's rim
fits a rib on the ledge, which keys it against the ribbon's drag and lines its ribbon notch up with the base's slit. Its cup wall
is 0.3 wider (18.3), so the drum's flange keeps 0.45 with the ring fully off centre. For the ring to pass, the deck
ring's hole widened to r 22.65. That also took the deck ring out from under the drum's hub, which had sat flush on
it at r 19.5–20.4 since set 2: the relief stopped at r 20.5. Found the same day after Zach called the pan finicky
(he also had no 6809 in it at all). `pan_coil_b_check.hub_face()` now checks for this, with set 5 as its control.

The deck ring now stands on a skirt, with a cone 30° off vertical under its outer part, so the supports outside the
cup are gone too. The first slices still had supports under the old 17.6 window's roof, in the wires' 5 mm exit hole,
and then under the cone's free edge over a channel for a key tab. Past the ring's notch the ribbon only runs straight
out, on edge, so it leaves the base by a 2 mm slit with a pointed roof (open to the top under the bearing's inner
race, where the deck is relieved anyway), the key became a rib on the ledge, and the exit hole has a pointed top. The
boss round the hole grew 3 mm so that point stays inside it. Rejected: one piece
with a breakaway wall under the shelf's edge (bridges to 34 mm, and a cleanup edge 0.6 from the turning drum), and
printing the base upside down (the deck ring and the servo tower would start in mid-air). Not changed: the supports
under the gear bay's ceiling and round the journal, which come out from below, and over the servo pocket, which
come out through its window. **Superseded:** set 5's well (`INSERT = False` still builds it).

## 2026-10-03: The drum's bore floor is a cone; the input gear takes the spline straight in (set 6)

Zach assembled set 5. **Drum:** it prints top face down, so the bore's flat floor was an 18 mm ceiling, and
the tree supports under it couldn't be got out. He asked for it "circular at an angle no greater than
30deg". The floor is now a cone 30° off vertical, 15.6 deep. A cone that steep can't fit under set 5's hole,
whose mouth sat in the floor near the wall, so the hole now starts at the cone's point and leaves into the lane
where set 5's did. The cone is the funnel: wherever the wires drop, they slide to the hole. The notch floor
went from 55° to 60° from horizontal (30° off vertical) and now meets the cone's rim. Orca with his
settings: the bore's ceiling contacts are gone (set 5: 188), and the drum slices to 35 min with supports
off. What's still over air is the ribbon slot's roof (a 17 mm bridge, open to the side) and the 5 mm hole's
arch. The slot's roof can't slope at 30° inside the drum's height without opening the slot into the wire lane.
**Superseded:** set 5's flat floor and its funnel (`DRUM_WIRE_PTS_SET5`, `HANDOVER_PTS_SET5`). The hole from
the cone's point is itself **superseded 2026-10-09 (set 8)**: the wires jammed in its bend.

**Input gear:** "no screw long enough to reach". The horn pocket was always a placeholder of generic numbers,
to be re-cut in Fusion with his horn, and his MG90S's shaft ran 0.8 mm into its roof, so the gear hung low.
No horn model of his was found on the machine, and he said to do the usual boolean fit, "whatever". So the
spline presses straight into the gear, as it does into post v3: post v3's bore (2.22, the flats of his
faceted 4.5), a 1.5 lip under the spline's tip, and the screw through the lip from a 5.2 counterbore. This
grips the shaft, not the horn's arms (the 2026-09-19 rule's preference). The tilt post has always done the
same, and he chose speed here. If the spline strips or the head wobbles, a horn pocket cut from his real
horn model is the next step. The gear prints bottom face down (`pan_coil_b_print.WAY_UP`), so no support
can land in the bore. **Superseded:** the placeholder horn pocket (`SPLINE_GEAR = False` still builds it).

## 2026-10-03: The +Y hub becomes a sleeve, so the ball drops in

Zach: the cradle's +Y arm "keeps snapping. it has to be bent for it to fit". His ball_plus's hub (r 8.0..9.95,
the ring the +Y 6704 rides on) stood from the ball's flat face at Y 24.5 out to 30.3, while the collar's face
is at Y 25.1. The −Y side gives under 1 mm, so the arm spread ~5 mm every time the ball went in.

His idea was to move the bearing into a cup inside ball_plus, as on −Y. It doesn't fit round the servo: the
gear tower fills the axis out to Y ≈ 26 with its gear bump at r 8.9, and the 6704's bore is r 10, so the post
can't pass between them; the servo would have moved back ~6 mm. A split collar with a cap would have put a
joint where the arm breaks. **Chosen (his pick): the hub is its own part.** It is cut off his ball, leaving a
1.5 mm socket keyed by a flat on the lens side, and printed as a sleeve with his hub's sizes and notch. The
sleeve goes in from outside after the ball, like the −Y stub, then the 6704 and post v3 as before. Cradle,
post, servo and bearings are unchanged (`fixes/plus_sleeve.py`, `checks/plus_sleeve_fit.py`).
The sleeve is a press fit in the 6704 (20.0 and 20.1 to try), stopped by a lip on its outer end that
touches only the inner ring: on the 19.9 slip of his hub the sleeve just turned inside a still inner ring.
**Superseded the same day:** the first, slip-fit sleeve (never printed), and its socket: 2.0 deep left 0.19 of
plate at the bottom of the face, and its gaps were under his 0.15 slide rule (now 1.5 deep, 0.15 a side, 0.3
to the floor; `checks/plus_sleeve_fit.py` rows 6 and 7).

Found on the way, not changed: the collar's shoulder (r 10.45 out) faces the 6704's turning inner ring as
well as the outer one; and the ribbon track's top lip reaches ~1 mm over the ball's widest point at the back.

## 2026-10-02: The cradle's wire ridge blends into the wall (looks only)

The round 1 cradle printed well. As a final touch Zach asked to even out the "snickers vein": the conduit
round the wire hole stood out of the −Y wall as a narrow ridge, with a notch where it left the collar. Its
smooth-union radius (`tree_parts_b.CONDUIT_K`) went 1.5 → 6 mm, so the ridge swells into the wall, and its
+Y twin follows. Every hole and clearance is cut after the blend, so none of them moved. It adds 720 mm³ on
the outsides, the surface moving out 1.1 mm at most, and removes nothing (`fixes/cradle_blend.py` lists each
lump). `wire_tube` gained a `pad`: its shortcut for far points sat 1 mm out and cut a crease into a wider
blend.

## 2026-10-02: Set 5's drum takes the wires round the ribbon's edge

Zach saw that the wires had nowhere good to go out of the cradle. The cradle's hole (round 1) lets them
out in front of the ribbon, where the ribbon bends down into the drum's bore. Set 4's drum hole starts
behind it. The 18 mm bore leaves the 16 mm ribbon only 0.7 mm at each edge, so the wires couldn't get
round. The cradle is printed and threads well, so the fix goes in the drum:
- **A notch in the bore wall** on −Y, from −150° to −72°. The wires pass the ribbon's edge there.
  ~~Out to r 12.3, flat floor at Z 3~~ **superseded the same day, before printing:** out to r 14, its
  floor sloping 55° down to the bore. The cradle's 22 mm groove lets the 16 mm ribbon sit 3 mm off
  centre, and at r 12.3 that left room for only a 1.4 mm bundle. The flat floor was also a 3.3 mm
  overhang, since the drum prints upside down.
- **A funnel** on the drum hole's mouth (7 mm across, 2 mm deep), following the hole's own line. The
  first cut was centred on the mouth and left a 0.26 mm ledge lower down.
- **Threading before the cradle is bolted down,** by eye. This replaces "thread last, blind".

Rejected: starting the drum's hole on its top face, outside the bore. Claude suggested it first. The
bore floor's edge and the chamber's top leave 3.0 mm, and the hole is 5 mm. Check: `wire_route.py`
row 7, a flood fill for the widest bundle that gets through. Lesson: `docs/lessons/2026-09-27-two-clear-cuts-need-not-meet.md`, second section.

## 2026-10-02: Test prints in PLA, the final head and drum in ASA

Every print so far has been PLA, and PLA stays for test prints. The final head and pan drum will be ASA,
for outdoor driving. An Ashby-style comparison of printable filaments found that stiffness per gram
barely differs between them (about ±20%). Heat, UV and impact toughness are what decide:
- PLA sags at about 55 °C. PETG (about 70 °C) sits just outside what sun plus the Pi's heat needs.
- ABS meets the heat and toughness needs but degrades in sunlight.
- ASA meets all three and prints well on Zach's enclosed Creality K2 Pro. At 1.07 g/cm³ it is about 20%
  lighter than the PETG-GF the sim assumes.
- PC and nylon-CF were rejected as harder to print, and nylon goes soft when damp.

Every tested fit (the zero-offset horn pocket, 0.15 per side on the 21 mm slide) was found in PLA. ASA
shrinks more, so print an ASA test piece of those fits before any final part. The sim still weighs parts
as PETG-GF; Zach said to leave that for now.

## 2026-10-02: The tilt servo's wires get their own route (round 1: stub and cradle hole)

Taping the tilt servo's lead to the ribbon spoiled the ribbon's fold (Zach). The lead gets its own hidden
way down instead:
- **The servo's own lead and plug stay coiled inside the ball,** behind the camera board on the −Y side
  (about 17 cm³ free, measured). Zach's Dupont jumper wires plug into it, and only they run down. This
  was his idea. ~~His plug has no visible latches, so it can't be depinned~~ **superseded 2026-10-02:** the
  Dupont-style split works on his servo's plug too, so its own wires can come out of the housing and
  might run down without jumpers (lead length unmeasured). This avoids cutting the
  lead. It replaced the plan to cut, solder and use a printed joint cover.
- **On the tilt axis:** a fixed hollow stub (`tree_parts_b.stub`) replaces both the −Y axle and the end
  cap. The ball turns on it, and the wires run through its middle, so they twist instead of bending.
  His socket is r 10.04 and the axle was r 9.95; that 0.09 mm is why the axle "doesn't fit". The stub
  is r 9.80. It is held by 3 × M2 × 6 in the cap's old holes, which also clock its wire hole.
- **The −Y bearing moved into the ball** (same day). Zach caught it: with the stub screwed down, nothing
  turned in the collar's 6704 seat, so a bearing there was dead weight. His fix: "a small divot inside of
  the minus of the ball to catch it", for "same bearing as the other side" (a 6704; he has 10 now). A cup
  inside his ball_minus's flat face holds the outer ring, which turns with the ball. The bearing presses
  in from outside until it stops on a lip. The stub runs through the inner ring and shoulders on it, and
  the collar is a plain bore (`fixes/ball_minus_cup.py`: `ADD_minus_bearing_cup`,
  `CUT_minus_bearing_pocket`). The cup stops 0.9 short of the camera board. The turning ring keeps 1.5
  off the stub and 1.2 off the cradle; the fixed ring keeps 0.55 off the ball.
- **A 5 mm hole down inside the cradle's −Y wall** (`WIRE_PTS`, `wire_tube`). It passes under the drum
  screw's head and ends in the plug chute's mouth above the drum's bore. The wall is only ~5.8 mm thick
  across its slope, so a 1.6 mm conduit ridge grows on its outside. A solid mirror of the ridge sits on
  the +Y wall, for looks (Zach: "for the sake of visuals ... put one on the other side as well").
- **The holes are sized for a bare Dupont pin beside two wires** (the shell comes off the threaded end).
  With the shells on, the 14 mm rigid housings won't take the bends in a hole that fits the wall.
- **Round 2 (pan coil set 4, built the same day at Zach's "lets do the next round"):** the wires roll in
  their own lane under the ribbon (`pan_coil_b.LANE_*`, `SHELF_T`, `DRUM_WIRE_PTS`, `BASE_WIRE_PTS`).
  - The lane is 3.5 tall, with its own wall at r 21, a 9 mm gap. So the moving U is ~3.6 mm radius
    instead of ~2 (Zach OK'd).
  - The ribbon sits on a fixed 0.8 shelf over the lane.
  - The floor drops 4.3. The bay's roof under the can was 7.6 thick, so the gears, the servo, the floor
    plate and the tab block don't move. The barrel's journal grows from 5 to 6.6.
  - The drum reaches down to be the lane's inner wall, standing 0.4 off the floor (set 3's touched it). A
    5 mm hole runs down its core.
  - The wires exit through a boss at −145°, 3 mm off the ribbon's slot.
  - 74 mm of wire in the lane gives the ribbon's 540° of travel.

Check: `head-v2/checks/wire_route.py`. Hand-off: `head-v2/fixes/wire_route_r1.py`. The fit view draws the
route (`fixes/cable_idea.py`).

## 2026-09-28: Pan coil set 3 is built on Zach's MG90S model

Zach printed set 2: "servo does not fit in there". The pan servo was the datasheet box: its length
(22.8) used as its height, a 4 mm shaft stub, and nothing past the case face. He then sent the MG90S
model he has been using ("it matches well", `head-v2/generator/pan-coil-b/MG90S.3MF`):
- the case is 22.4 tall;
- a 15 × 12.2 block, 6.0 tall, sits on the shaft end of the case face;
- the shaft tip is 10.0 past the face;
- the tabs' shaft-side face is 1.9 below the case face, and the tab screws are 26.86 apart.

The base and drum follow it (`pan_coil_b.SV_*`, `TAB_*`):
- **The gear plane sits 0.5 under the block,** 5.6 lower than set 2, as Zach suggested ("make the barrel
  a bit taller or send the stem lower"). The drum's barrel and the bay grow; the gears and floor keep
  their shape.
- **The tab shelf is at the model's tabs, 4.6 higher than the datasheet guess.**
- **The block and the shaft get a pocket and a channel out through the side window.**
- **The drum's side slot top goes from Z 0.5 to 2.0,** for Zach's servo connector (14 × 8, calipered).
  It jammed at 3.0 thick turning from the bore into the slot; 2.0 passes 3.5.

**The servo's +Y tab gets a slide-in tab block** (2026-09-29, Zach: "change that now please"). The
servo slides in through the window at that end, so there was no plastic under that tab, and its M2
pilot was cut in air (0% plastic round it, set 2 as well). A 15.4 × 6.7 × 5 block
(`pan_coil_b.tab_block`) follows the servo in on two rails, in grooves in the pocket's side walls that
end blind as its stop. The tab's own M2 × 6 then goes into it: 89% plastic round the screw, 3 mm of
thread. Control: rails 0.5 too wide for the grooves read BLOCKED.

Check: `head-v2/checks/pan_servo_fit.py`, with his mesh as the servo, seated and sliding in. Controls: the
servo 4.6 higher, and 1.5 lower while sliding in.

**Superseded:**
- set 2's base and drum;
- set 3's first cut, made the same day from the tilt servo's measured numbers (a Ø6.9 boss 5.0 tall,
  tabs 6.5 below the face): its tab shelf would have held his servo 4.6 too high.

Both are in `out/print-pan/superseded - */`.

## 2026-09-27: The cradle gets a plug chute and a 4 mm groove

Zach found the cradle's way down into the drum had no room for the ribbon and the tilt servo's plug
together. Measured:
- **The groove never opened into the ribbon track.** They met at a corner, with 0.00 mm of opening
  (`docs/lessons/2026-09-27-two-clear-cuts-need-not-meet.md`).
- **A rigid plug can't turn the groove's 6.3 mm bend at any slot thickness,** 3 or 4.

The fix (generator, `tree_parts_b.py`: `CHUTE_T`, `chute()`):
- **The groove is 4.0 thick** (Zach: "wire bundle is 3mm lets make it 4 so the head comes through").
  It keeps its curve, so the ribbon still lands on the drum's axis, where the 18 bore is wide enough
  for 16 mm.
- **A straight 4.0 chute runs beside it**, 50° from vertical and 22 wide. It goes from the bowl's
  floor behind the ball into the drum's bore, exiting at X −1.5. The plug is fed down it with the ball
  out. At 40–46° the two cuts left a fin between them, held only at the sides; 50° leaves none.
- **The chute leaves the groove's inner wall**, the one the ribbon bends round, as it was.
- **`TROUGH_T` stays 3.0**, because it also sizes the ball's ribbon slot.
- Cradle volume 55.61 → 55.02 cm³.

Check: `head-v2/checks/plug_passage.py`. With the plug's thickness taken as 3.0 plus the 0.2 ribbon,
a plug up to 18 long passes the cradle. The drum then limits it to 13 long, where its bore turns into
the side slot. Raising the side slot's top from Z 0.5 to 3.0 would pass 18. That drum change is not
made: set 2 may be printing, and the plug hasn't been calipered.

**Superseded:** the cradle with the 3.0 groove (set 1 and set 2's `cradle.stl`), kept in
`out/print-pan/superseded - cradle before plug chute/`.

## 2026-09-27: Head rev 2: the lens is centred on the board's holes

Zach's Fusion rev 2 (`head-v2/fusion/rev2-2026-09-27/`) booleans in the shipped fixes. It also:
- moves both camera-post tubes up 2.00 mm;
- removes the rib between them;
- reshapes the IR opening.

He explained the move: "the lens is directly center to the posts, your camera model had it sitting off
center", centred by hand.
- **The camera model's lens is centred on its holes** (`camera_dummy.py`, `LENS_OFF` 0). The photo
  value, 1.6, is kept as `LENS_OFF_PHOTO` for `camera_dummy.*`, because the rev-1 regression rows were
  run with it. New checks use `kit.camera(centred=True)`.
- **The pins place the board**, so the lens sits 0.40 above the tilt axis. The tubes are not nudged
  to fix that: it is inside his by-hand margin, and the lens clears the nest by 1.83 (was 1.95).
- **Tube axes: Z from fitting the tube tools, Y from his wall holes** (Y 14.70, Z 37.95 / 66.85).
- **The camera posts are regenerated** (`fixes/campost_rev2.py`). The pin tip steps down to 1.48
  inside his 1.78 wall holes.
- **The IR cutout is extended 2.0 toward +Y** at his request ("about 2 mm short on the left side",
  the post side). It is his 32 mm circle shifted, trimmed to Z 42.4–62.4 so it stays 1 mm off both
  tubes (`fixes/ball_plus_rev2.py`, `CUT_plus_ir_extend`).
- His export's 11 self-intersections and 8 non-manifold edges ship as they are, and are located in
  the README. Repairing them in pymeshlab opened a hole every time.

**Superseded:** the rev-1 camera posts (`head-v2-snap`), made for tubes 2 mm lower.

## 2026-09-27: The pan coil comes apart to go together (print set 2)

Zach asked how the small gear gets into its hole. It couldn't. Set 1 (the first pan-coil print set) had
the drum's gear moulded on, 22.6 mm across, below a 10.5 mm journal and a 17.2 mm bay top hole. The
gear bay was a closed box, so the 43.3 mm input gear couldn't get in either. Every pair check read zero.
In `head-v2/generator/generators/pan_coil_b.py`:
- **The small gear is its own part** (`gear_out`). The barrel steps from r 5 to a D-shaped r 4 seat
  below the journal (flat at 3.2, 0.15 slide per side). The gear pushes up onto it from below, clamped
  to the step by one M3 × 8 button head through a 1.5 mm web. **Superseded 2026-10-09 (set 8):** the seat
  snapped when the screw was tightened; it's a square now, and an M3 × 12 threads above the step.
- **The gear bay's floor is a separate plate** (`floor`, below Z −32) on 4 × M2 × 6 into corner bosses.
  Both gears go in from underneath. Holes under both axes: the M3 head turns in one, and a driver
  reaches the horn screw through the other.
- **The well and the gear bay print as one part** (`base`). Zach picked this over keeping them
  separate: nothing on the well (2 mm walls, the coil behind them) could take a screw. The bay's cuts
  are applied to the bay alone, so the servo pocket doesn't bite the bearing seat.

Print-in-place (Zach's suggestion) doesn't work for the drum: the 6809 has to go onto the drum from below
before the drum enters the well. The input gear's horn needs the open bottom anyway.

Found in the same pass, before set 2 printed, and fixed:
- **The gear pair had zero play.** It was drawn at exactly the pitch centre distance, with teeth
  touching both flanks at every angle. `GEAR_GAP` takes 0.3 off the small gear only, so a printed
  set-1 input gear still meshes: 1.9° of drum play as drawn.
- **The 6809's inner race sat on the fixed ledge.** The deck ring's top was solid under both races.
  It is relieved 0.4 deep from r 20.5 to 26.0, so only the outer race lands.
- **Bearing fits: seat 58.1, hub 44.9.** Both were drawn at exactly 58 and 45. The values follow the
  6704 tilt seats' +0.1 / −0.1 precedent. Untested on this bearing.
- **The drum's bearing shoulder is a sharp step.** A 1.5 blend at the hub-to-disc corner stood ~1 mm
  proud all the way round, where the 6809's bore edge seats (30 mm³, the first time the bearing was
  checked against the drum).

`pan_coil_b_check.py` now slides each part in along its real path (`assembly()`), and measures gear
play (`gear_play()`) and what each race sits on (`bearing_races()`). Its negative
control, `--broken`, puts the gear back on the drum and the floor back in the bay.

**Superseded:** set 1's separate well and gear bay, and the drum with its gear moulded on
(`head-v2/out/print-pan/superseded - set 1, can't assemble/`).

## 2026-09-27: MuJoCo for simulating the head, not Isaac Sim (for now)

For moving the pan/tilt head by hand and later training on it, the head is modelled in MuJoCo
(`sim/mujoco/`). Isaac Sim was the other candidate: Control's roadmap plans a ROS 2 twin in it.
- **Isaac Sim pins old NVIDIA drivers**, rolling the machine's driver back about ten versions. Zach
  doesn't want that. MuJoCo needs only OpenGL, and the pip install touched nothing already installed.
- **It's light.** It runs on the CPU and is quick to fiddle with. The RTX 5070 has 12 GB, which is
  tight for camera-based training in Isaac.
- **Isaac isn't ruled out.** The same joints, masses and meshes can become a URDF for Isaac Sim when
  learning from rendered camera images needs it.

The first model is two servo joints plus the 2:1 pan gear pair. Its masses are guesses until the
slicer gives PETG-GF grams. A finding from it: the tilt piece balances within about 1 mm of the tilt
axis, so gravity costs the tilt servo almost nothing.

## 2026-09-27: Seam pins and camera posts are medium

Zach doesn't need the stiffness test: medium, for the seam pins and the camera posts both. The 3MF
plates already carried medium (`PIN` in `fixes/plate3mf.py`, `PIN` and `CAM` in
`fixes/plate_campost.py`), so nothing was rebuilt. The soft and firm STLs still build; they're just not
the pick.

## 2026-09-27: The cradle bolts onto the 360° pan coil's drum

The cradle (`fork`) no longer sits on a pan-servo pedestal (`roots`): it bolts straight onto the pan
coil drum's mounting disc (both Ø51, meeting at Z 10.5). In `head-v2/generator/generators/tree_parts_b.py`
(`PAN_COIL = True`):
- **3 × M3 × 12** at r 20, 0/120/240°: a 3.4 clearance through the bottom 5.5 mm, and a 6.4 head recess
  opening into the bowl. They are driven from above before the ball goes in. The cradle is 15–16 mm
  thick there and open above (probed).
- **The ribbon groove comes down on the centre line** into the drum's 18 mm bore. It used to land 9 mm
  forward, at the bore's edge. The bend finishes inside the bore, at a tightest radius of 6.3 mm, safe
  even if the ribbon calipers at 0.3. The ribbon's full 16 mm width is clear along the whole path
  (probed).
- **The pan-horn pocket and the Ø5.6 shaft hole are gone.**

Checks: `build_b.py --check` is green, including ball vs nest at every tilt. `pan_coil_b_check.py`
reads 0 clashes. The bolt and ribbon probes read open on the new cradle and closed on the old one,
their negative control.

**The ribbon needs no twist.** It lies across Y all the way down, and one soft 45° fold at the drum's
side slot turns it on edge. The fold is made by hand with the drum out. The pan-coil brief's §5.0
twist problem assumed no folds at all. The drum goes on with its side slot facing forward (+X): the
bolt pattern allows three ways round.

**Superseded:** the pedestal cradle, with the pan horn pocketed in its underside (`PAN_COIL = False`
rebuilds it).

## 2026-09-27: Mid-cable folds in the camera ribbon are allowed

Zach, clarifying what he meant on 2026-09-18 when he turned down a 45° fold. The rule is about where
a fold goes, not about folds as such:
- **Never fold the stiffened end,** the connector section with the plastic backing that must stay
  straight to plug in.
- **Don't design a fold that has to be made first and then threaded through a tight space.**
- **A fold in the middle of the cable is fine,** made in place where there is room. Keep it soft
  (rounded, not pressed flat), and only where the cable never flexes: never in the tilt loop behind
  the ball or in the pan coil.

This matters for the 360° pan coil. The ribbon has to turn from flat to on edge between the ball and
the coil, and a quarter twist wants ~40 mm of run where only 21 mm exists (pan-coil brief §5.0). A
mid-cable fold in the stretch that turns with the head does the same job in almost no length.

**Superseded:** "no folds in the flat cable, ever" (2026-09-18, in `docs/lessons/2026-09-18-flat-cable-and-driver-access.md`
rule 1 and the variant-B notes). That over-read his objection, which was about folding the stiffened
end to fit it through a hole.

## 2026-09-26: Camera board held by snap posts pushed in from outside

Zach's rev 1 holds the camera board with two screws from outside, through tubes to the board's two +Y
outer holes. The heads would have stood proud of the ball, like the seam screws that jammed it. Two
snap posts now fill those tubes instead. Each is a 1.8 pin through the board, a shoulder that presses
the board onto his wall, barbs that click behind a step in a thickened tube, and a head cut to the
sphere 0.2 under the surface (the nest is 1.5 out). The long (upper) post is 0.4 thicker, so it can't
go in the lower hole, where it would stand ~1 mm proud. (`head-v2/fixes/campost.py`)

He asked twice for other ways. What was checked:
- **A pin from inside, behind the wall:** it can only push the board forward, off the wall, onto the
  tube ends, so the board isn't clamped flat. Its snap socket would be a 7 mm cantilever off the wall,
  which can't print seam-down without a fin. And it is ~15 mm deep past the servo box to reach.
- **Posts fixed on the wall, board snapped over them:** with the front tubes and rail removed, the
  board can come ~2 mm forward (measured). But a snap tip that passes the board's 2.0 holes has
  prongs ~0.6 mm thick, too thin for FDM. This reopens if the holes calliper at 2.5 or more.
- The outside holes aren't new: they are his screw tubes, now filled flush.

## 2026-09-26: ball_plus ships as a sewn STEP

The finished parts ship as STEP solids so Fusion opens them as bodies. ball_plus's exact BREP (his
facets fused with the tubes' exact surfaces) loses 490 mm3 through ShapeFix and every STEP reader.
The ball_plus STEP is therefore sewn from the checked STL, all planar facets like his own export. It
round-trips exactly. The other parts write straight from their BREPs. (`head-v2/fixes/step_models.py`)

## 2026-09-26: Seam-pin STLs dropped onto the bed

`print_export.py` sized the pins with `BRepBndLib.Add_s`, which gives a loose box on their curved
noses. The pins shipped 0.50-0.59 mm above z = 0. `fixes/pins_on_bed.py` moves them down; new code
sizes with `AddOptimal_s`. The shapes are unchanged.

## 2026-09-26: The CAD moves out of FPVTank_Control

The Pi `git pull`s Control. Its `docs/chassis/` held 115 MB of CAD, against under 1 MB of robot code,
and every regenerated mesh rode along to the Pi. Physical design now lives in this repo; Control
keeps the code and the robot docs. The plan is in `docs/reorg-2026-09/MOVE-PLAN.md`. Done 2026-09-27
(phase B): the generator is in `head-v2/generator/`, the chassis parts are in `chassis-v1/`, and
Control holds no CAD.

## 2026-09-25: Post v3, with a stop plate and the servo's centre screw

Nothing held the ball along the tilt axis: it slides about 0.6 mm either way between the cradle's
collars. Pressing Zach's post on pushed the ball away, and only 2.1 mm of the servo's 4 mm spline got
into the post.

Post v3 reaches 0.76 mm further in and has a 1.5 mm stop plate. The servo's centre screw pulls the
spline onto the plate, which centres the ball: 3.5 mm of spline in the post, and the post's end 0.5 mm
off the servo's head. (`head-v2/fixes/post3.py`)

## 2026-09-25: The snap pins get a stop

Zach found on the test block that the first pins could slide 0.75 mm deeper after clicking. One could
end up too deep in the first half and never click into the second. The pins now have a round nose that
reaches the end of the hole. Only the pins changed; the sockets didn't.

**Superseded:** the first pins, still kept as `snap.pin(nose=False)`. They are the negative control in
`checks/freeplay.py`.

## 2026-09-25: Snap pins replace the seam screws (ball rev 2)

The ball curves away under each screw head. A head's outer edge stood about 2 mm proud of the ball,
with the nest only 1.5 mm away, so the screws jammed the ball. The screw holes are now plugged.
Three separate pins, printed lying down, snap into sockets in both halves and pull apart by hand.

**Superseded:** rev 1, seam screws plus a front M3 post (`archive/head-v2-rev1-screws/`).

## 2026-09-25: Zach's Fusion model is the source of truth for the ball

His revision (exported 2026-09-24):
- turned the tilt servo 90° and boxed it in plates;
- stops the servo's case top on a plate at Y 21.24;
- puts the camera board on the front of his wall, at X 10.5.

Fixes are applied to his STLs as exact booleans, and handed back as named tool bodies he can apply in
Fusion. The generator (`tree_parts_b.py`) doesn't have his revision. Porting it in was offered and
hasn't been answered.

## 2026-09-19: Horn pockets use zero offset

This is Zach's bench result: subtract the model of the horn he owns with no size change, and leave
1–2 mm for the screw. It prints as a tight fit. It applies to horn pockets only; a 21 mm slide needs
0.15 per side.

**Superseded:** "+0.2 mm all round", from the ball-head validation handoff. It was never tested.

## 2026-09-18: Head v2 is variant B, the ball in a nest

There were three forks:
- A: the tilt servo in an arm (`tree_parts.py`);
- B: the tilt servo inside the ball (`tree_parts_b.py`);
- C: a fixed hood (`tree_hood.py`).

Zach picked B. A and C are superseded, not deleted. Two standing constraints from him:
- No folds in the camera's flat cable, ever. Every turn is a drawn-out curve.
- The cable is paper thin, so give it space. The 8 mm rolling-loop gap is deliberate.

## 2026-08-03: Fusion for design, Blender only for mesh surgery

Zach chose Fusion 360 over Blender for the v2 design. Blender stays for editing downloaded STLs.
