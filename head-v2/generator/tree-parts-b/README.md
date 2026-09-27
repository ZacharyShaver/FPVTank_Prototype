# Tree head, variant B — the ball in a nest

**Written 2026-09-18.** Variant B puts the tilt servo *inside the ball* and
replaces variant A's fork + two caps + bolted shroud with **one continuous
nest**: the trunk rises out of the pan pedestal, flares into a cup that wraps
the ball, and the cup's side walls draw in past the ball's flats and become the
two bearing collars. Trunk, cup and both collars are a single printed body.

**For Fusion, do not import `fusion/*.obj`** — read [`step/README.md`](step/README.md). Five of
the seven parts are now real solids in `step/*.step` and need no Convert Mesh at all; `fork`
and `roots`, the only organic ones, get stripped-down blanks in `fusion-solid/` plus
[`features.md`](features.md). Added 2026-09-19.

```bash
python tree_parts_b_step.py         # the 5 solids -> step/*.step, verified  (seconds)
python step_mesh_prep.py            # fork + roots blanks, and features.md   (~10 min)
```

Regenerate the meshes from `../generators/tree_parts_b.py`:

```bash
python tree_parts_b.py              # every part -> print/*.stl and fusion/*.obj  (~25 min)
python tree_parts_b.py fork         # just one part (leaves the viewer bundle alone)
python print_post.py b              # print STLs down to <=250k faces, no self-intersections
python mesh_qa_b.py                 # rewrites mesh_report.txt from what is on disk
python tree_parts_b_check.py        # interference + view cone, 32 rows
python tree_parts_b_driver.py       # can a driver reach each screw, at its step
python viewer_bundle_b.py           # refresh viewer_parts_b.js from the fusion OBJs
```

Every part must come back **watertight, manifold, bodies = 1, self-int = 0**,
and both check scripts at zero.

**This is concept geometry for a test fit, not a validated design.** Servo, horn
and ribbon numbers are datasheet/generic/assumed — see *Still unverified* at the
bottom, and read it before you cut anything to length.

## What it has to do

| | |
|---|---|
| Tilt travel | **180°**, rolled down 35°: from 35° below the horizon to 145° up |
| Mouth | cut 8° wider at the bottom and **7.5°** wider at the top than the travel, because at the end of the swing the lens looks *along* the rim. The top went 5.0 → 7.5 when the bezel came off and the view cone started being launched from the measured lens tip |
| Unvignetted view | a 60° lens is clear across the whole −35°…+145° |
| Pan | ±90° |
| Envelope | 68 wide × 75 deep × 83 tall (A: 107 × 79 × 58) |
| Tilt take-up | rolling loop behind the ball, 8 mm gap → 4.0 mm U-turn radius |

The ribbon's U rides at **half** the tilt angle, so 180° of tilt walks it 90°
around the back. The track runs from 19° above straight-back to 76° below, and
at neutral the loop is seated 2° *below* straight back — that's a ribbon-length
choice you make at assembly, and it's what balances the margin at the two ends.

## Parts

| Part | Qty | Prints | Supports | Notes |
|---|---|---|---|---|
| `roots` | 1 | flat on its underside | none | Fixed. Screws to the deck, pan servo drops in from below. Unchanged from A. |
| `fork` (the nest) | 1 | **deck plate flat on the bed** | tree supports under the cup flare, the two collar undersides, and the lower lip | The whole mount. 4+ walls. |
| `ball_plus` | 1 | seam face down | inside the servo pocket if it does not seat flat | +Y half: servo pocket **and tab recess**, board rail, hub stub, seam counterbores |
| `ball_minus` | 1 | seam face down | none known | −Y half: board rail, **the pad that closes on the servo's base**, axle socket, rear ribbon slot |
| `post` | 1 | flange down | none | Fixed drive post. Inboard face at **Y 24.5, seated on the horn disc**; blind pocket captures the horn, with a Ø6.5 bore behind it for the spline tip |
| `axle` | 1 | outer end down | none | Plain idler at the −Y end of the tilt axis |
| `cap_minus` | 1 | outer face down | none | Flush plate; traps the axle |

PETG, 0.2 mm layers. The `print/` STLs are already in print orientation, each
centred with its lowest point at Z 0.

**The nest's orientation was measured, not guessed.** Overhang area and bed
contact were scored for every candidate:

| Orientation | Needs support | Bed contact |
|---|---|---|
| **deck plate down (used)** | **11.8 %** | **1606 mm²** |
| standing on a collar | 22 % | 85 mm² |
| mouth up | 14 % | 1 mm² |

Mouth-up looks like the natural way to print a bowl and it would fall over.

## Hardware

| Item | Qty | Where |
|---|---|---|
| MG90D servo | 2 | tilt (inside the ball), pan (roots) |
| 6704 bearing (20 × 27 × 4) | **2** | one per collar |
| **M3 × 30** | 3 | ball seam: head recessed in the +Y half, threads into the −Y half |
| M2 × 8 | **8** | post flange ×3, cap flange ×3, **tilt servo tabs ×2** |
| M2 × 6 | **2** | pan servo tabs ×2 |
| M3 × 10 | 4 | roots to deck |
| A servo horn, **trimmed to 13.5 mm across** | 1 | captured in the post |

**13 M2 screws.** The camera board's four are gone: it is **captured**, sliding
into a rail in each ball half, which also means the fit depends on the board's
**outline** rather than its hole pattern — the easier thing to measure. See
`docs/lessons/2026-09-18-flat-cable-and-driver-access.md`.

**The tilt servo's two tab screws are back, and this is why.** They were dropped
on the grounds that the servo was captured instead: *"the tabs drop into a
`TAB_T = 3.0` recess that stops it moving +Y."* Measured, that recess removed
**0.00 mm³** of a 1452 mm³ box — it was cut entirely inside the ball's cavity and
never touched solid material, so the capture it described did not exist. The servo
was located in X and Z by its pocket, sat on the −Y pad, and had **nothing above
it**: it could float 4 mm toward the post and take the load on the horn. Two
bosses now rise to the tabs' underside and each takes an M2 up through the servo's
own tab hole, driven from the seam face before the halves close — the same way the
pan servo is held in `roots`. `tree_parts_b_driver.py` carries a row for each.

M2 holes are pilots for thread-forming screws (Ø1.7) or clearance (Ø2.2).
**The seam went M2 × 25 → M3 × 30 on 2026-09-19.** Not a design preference: an M2
long enough to cross the ball does not exist in Zach's box and M3 × 30 does. The
rods grew with it, 2.8 → **4.0 mm radius**, because an M3 clearance hole in a 2.8
rod leaves 1.1 mm of wall; at 4.0 it leaves 2.3.

The three rods sit at (x, z−H) of **(−23, +9), (−23, −9)** and (17, −20). The rear
pair has moved twice and both moves are worth knowing: out from (−20, ±14), which
was in the old board screws' line, and then from ±8 to ±9 when the rods grew — at
r 4.0 the lower one's edge sat exactly on the ribbon exit slot's edge, and a
tangency like that is what put a zero-thickness skin on `ball_minus` once already.

Heads seat **16.0 mm** out on the two rear rods and **13.7 mm** on the front one.
The pilot runs to Y −18.0, which is deeper than it looks like it needs to be: at
−16.0 the front rod's screw **bottomed out 0.28 mm before it clamped**. All three
now engage 15–17 mm of thread with 1.7–4.0 mm of hole to spare.

## Assembly order

Every screw below is reachable **at the moment you need it**, which is the thing
the first printed head got wrong.

1. **Roots.** Pan servo in from below, tabs up into their recess, 2 × M2 × 6.
   Roots to the deck, 4 × M3 × 10.
2. **Nest onto the pan servo — do this before the ball goes anywhere near it.**
   Press the pan horn into the pocket in the nest's underside, set the nest down
   and seat the horn on the spline, then drive the horn screw down the Ø5.6
   access bore. You reach it from *inside the cup*, through the mouth. Once the
   ball is in, that path is gone.
3. **Bearings.** Press a 6704 into each collar **from the outside**, through the
   flange recess and the pass bore behind it. This only became possible on
   2026-09-19: both seats used to step down to a smaller bore on *both* sides, so
   they were sealed pockets and no bearing could ever have reached them. Nothing
   holds a bearing at this stage — the post (step 9) and `cap_minus` (step 8)
   each carry a ring that traps it, and those rings land on the **outer race
   only**, because the inner race turns with the ball.

   *Waiting on the real bearings?* Print two of
   `test-parts/bearing_dummy.stl` — Ø27.0 × Ø20.0 × 4.0. It is a plain bushing,
   not a bearing: the ball turns stiffly and it wears. For checking fits and
   travel only; do not leave it in.
4. **Build the ball, off the machine.**
   a. Tilt servo into the `ball_plus` half through the open seam face, shaft
      facing +Y. It should not need forcing; the pocket is cut 0.25 mm oversize
      all round. Then **2 × M2 × 8 up through its own tab holes** into the two
      bosses — `TAB_Z` 43.75 and 71.25, both on X 0, 5.4 mm of thread each.
      **Drive these now.** Once `ball_minus` is on there is no way in at all.
      The tab is clamped between the screw head underneath and the boss face
      above; the pocket's flat sides still take the torque.
   b. Camera board **slides into its two rails**, one in each half. **No
      screws.** Check it seats before you close up: the groove is cut for a
      1.6 mm board 36 mm across, gripping 2.6 mm of each edge.
   c. Ribbon out through the rear slot, with the three servo leads taped
      alongside it — they roll with the ribbon, there is no second channel.
   d. Close with `ball_minus`, **3 × M3 × 30** driven from the +Y side (this said
      M2 × 25 until 2026-09-19; the seam went M3 in commit c36022c and the step
      was not updated with the BOM). Its pad lands on the servo's base as it
      closes, but the tab screws in 4a are now what hold the servo — if the
      halves will not meet, the pad is still the first suspect.
5. **Horn into the post.** Trim a horn to 13.5 mm across and press it into the
   post's blind pocket. Nothing screws it down: the servo's own boss holds it on
   one side, the pocket floor on the other, and the spline carries the torque.
6. **Drop the ball into the nest through the mouth**, +Y stub into the +Y
   bearing.
7. **Axle** in from the −Y side, through the bearing into the ball's socket.
8. **`cap_minus`** over the −Y recess, 3 × M2 × 8. It sits flush and lands
   0.2 mm off the axle's end, so the axle is trapped without the two touching.
9. **Post** in from the +Y side, through the bearing and the stub bore, until
   the horn meets the servo spline. Its inboard face is drawn to stop at **Y
   24.5**, sitting on the horn disc, with the spline tip running on into the
   blind Ø6.5 bore behind the pocket. 3 × M2 × 8 through the flange.
10. **Ribbon.** Feed the free end up the back of the ball, round the U, and back
    down the shroud into the trough. It leaves the underside about 9 mm forward
    of the pan axis. Leave a slack loop below deck for ±90° of pan.

## Fits to check on this print

This is what the print is *for*. Measure these before you assume anything.

| Fit | Nominal | What it means |
|---|---|---|
| 6704 seat in each collar | Ø27.10 × 4.0 deep | Should be a light press. Both seats have a 45° self-supporting crown, so the bore is a full circle with a notch above it — the bearing still locates. |
| Ball hub stub | Ø19.9 in a Ø20.0 bore | Light slip. **This was Ø20.0 and would not have gone in at all.** |
| Printed axle | Ø19.9 in a Ø20.0 bore | Same fit, other end of the axis. |
| Post through the stub | Ø15.4 in Ø16.0 | The post is fixed; the stub turns around it. |
| Flange recesses | Ø35.0 × 1.8 deep | Both plates should sit flush, not proud. |
| Ribbon slot | 22.0 × 3.0 | Sized for a 16 mm ribbon **plus** the servo leads beside it. `RIBBON_W` is still assumed. |
| **Lens hole** | Ø23.0, plain bore through the shell | No bezel, no tunnel — deliberately oversize so the front fits whatever the camera is. Lens tip sits at X 29.0, 0.5 mm inside the shell. Check the view is not clipped at full up-tilt. |
| Rolling-loop gap | 8.0 | U-turn radius 4.0 mm. |
| **Servo tab bosses** | 2 × M2 pilot, Ø1.7 × 5.4 deep, at Z 43.75 and 71.25 on X 0 | The tab should land flat on the boss face at Y 14.5 and pull up tight. If it bottoms before it clamps, the boss face is proud. |
| **Board rails** | **2.3 slot for a 2.0 board**, at Y ±18 | The board is captured, not screwed. Thickness is measured now; **`BOARD_Y = 18.0` is still assumed and is the last load-bearing guess.** |
| **Seam screw bottoming** | 1.7–4.0 mm of spare pilot | The front rod is the tight one. If a screw stops turning before the halves close, it is bottoming, not tight. |
| **Post seat on the horn** | inboard face at Y 24.5 | Rests on `SPLINE_STACK`/`HORN_SEAT`, which are *inferred, not measured* — see below. |

Two internal channels bridge about 22 mm flat (the trough roof and the bottom of
the track). Expect some droop; both are oversize for it, but look.

## Still unverified

- **Ribbon width and thickness are ASSUMED at 16.0 × 0.30.** Everything on the
  ribbon side scales off them — slot, track, U-turn radius. A 0.5 mm ribbon
  wants a 5 mm U radius and the 8 mm gap becomes 10.
- **Where the post stops is an inference, and it is the open question.**
  `SPLINE_STACK = 6.0` (case top → spline tip) and `HORN_SEAT = 1.5` (case top →
  underside of the horn disc) are derived from the MG90 family being quoted
  28.5 mm tall on a ~22.5 mm body. Zach measured something Ø15 × 7 mm tall; read
  as the *round horn*, the numbers fit — but that was never confirmed. **If that
  Ø15 is the servo's own boss, the coupling does not fit as drawn** and the servo
  has to drop ~5 mm deeper into the ball, moving the pocket, the tab recess, the
  −Y pad and the post together. Measure, on a servo standing on its base: height
  to the top of the splined shaft, and height to the shoulder the horn rests on.
- **The rest of the servo is still datasheet/generic.** `TAB_T = 3.0` is
  **measured** (the published MG90S figure is ~1.2 — Zach's are thicker), but the
  body, tab span and pitch are not, and the horn pocket assumes a horn trimmed
  to 13.5 mm.
- **The tilt coupling is the weak point.** Everything the post carries has to
  pass through the hub stub, so the horn pocket lives in a Ø15.4 head and leaves
  **0.95 mm of wall at each arm tip**. If that splits on the bench, the answer is
  probably a printed spline in the post rather than a captured metal horn — this
  print is how we find out.
- The trough leaves the nest's underside 9 mm forward of the pan axis, so
  panning drags the ribbon. Routing it *down* the pan axis is unsolved.
- No `features.md` yet. `fusion/*.obj` are the full parts with every cut already
  made; there are no `_blank.obj` bodies for variant B.

## Into Fusion

**Read `step/README.md` — it supersedes what used to be here.** The old advice was
to import `fusion/*.obj` and run Convert Mesh, with `fusion-convert/` as a
reduced set to make that easier. That premise was wrong: what defeats Convert
Mesh on a marching-cubes mesh is that it has no structure to recognise — a flat
face is a few hundred nearly-coplanar triangles, a bore is a ring of facets — so
lowering the face count does not help. `fusion-convert/` is kept, marked
superseded, because it records what was tried.

| You want | Open | What arrives |
|---|---|---|
| `post`, `axle`, `cap_minus` | `step/<part>.step` | A solid body. **No Convert Mesh at all.** Verified exact — 0.00 mm³ disagreement |
| `fork`, `roots` | `fusion-solid/<part>_blank.obj` | A mesh to convert, then cut the rows in `features.md` |
| `ball_plus`, `ball_minus` | `fusion/<part>.obj` | ⚠ Mesh route. Their `.step` files exist but are **11.6 % short** — see `step/README.md` |

Everything is in the shared assembly frame (mm; X forward, Y along the tilt axis
with +Y the post side, Z up from the deck top), so each part lands where it
belongs. **Tilt axis at X 0, Z 52.0.** Every mesh is watertight, 2-manifold, one
body and free of self-intersections — see `mesh_report.txt`. For the meshes:
Insert → Insert Mesh, Millimeter, *Center unticked*.
