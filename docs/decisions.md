# Decisions

Why each design went the way it did. Newest first. A reversed decision stays here, marked
**superseded**.

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
