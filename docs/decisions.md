# Decisions

Why each design went the way it did. Newest first. A reversed decision stays here, marked
**superseded**.

## 2026-10-02: The tilt servo's wires get their own route (round 1: stub and cradle hole)

Taping the tilt servo's lead to the ribbon spoiled the ribbon's fold (Zach). The lead gets its own hidden
way down instead:
- **The servo's own lead and plug stay coiled inside the ball,** behind the camera board on the −Y side
  (about 17 cm³ free, measured). Zach's Dupont jumper wires plug into it, and only they run down. This
  was his idea. His plug has no visible latches, so it can't be depinned, and this avoids cutting the
  lead. It replaced the plan to cut, solder and use a printed joint cover.
- **On the tilt axis:** a fixed hollow stub (`tree_parts_b.stub`) replaces both the −Y axle and the end
  cap. The ball turns on it, and the wires run through its middle, so they twist instead of bending.
  His socket is r 10.04 and the axle was r 9.95; that 0.09 mm is why the axle "doesn't fit". The stub
  is r 9.80. It is held by 3 × M2 × 6 in the cap's old holes, which also clock its wire hole.
- **A 5 mm hole down inside the cradle's −Y wall** (`WIRE_PTS`, `wire_tube`). It passes under the drum
  screw's head and ends in the plug chute's mouth above the drum's bore. The wall is only ~5.8 mm thick
  across its slope, so a 1.6 mm conduit ridge grows on its outside.
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
  to the step by one M3 × 8 button head through a 1.5 mm web.
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
