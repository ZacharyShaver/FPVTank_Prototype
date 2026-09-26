# Decisions

Why each design went the way it did. Newest first. A reversed decision stays here, marked
**superseded**.

## 2026-09-26: The CAD moves out of FPVTank_Control

The Pi `git pull`s Control. Its `docs/chassis/` held 115 MB of CAD, against under 1 MB of robot code,
and every regenerated mesh rode along to the Pi. Physical design now lives in this repo; Control
keeps the code and the robot docs. The plan is in `MOVE-PLAN.md`.

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
