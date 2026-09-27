# Tree head — printable parts

**Written 2026-09-17.** The tree-housing ball head split into parts you can
print, assemble, and import into Fusion. Edit the parameters at the top of
`../generators/tree_parts.py` and regenerate:

```bash
python tree_parts.py          # all parts -> print/ and fusion/ + features.md
python print_post.py          # print STLs down to <=250k faces, no self-intersections
python mesh_qa.py             # rewrites mesh_report.txt
python tree_parts_check.py    # collision check across the tilt and pan range
```

This is concept geometry for a **test fit**, not a validated design. Servo,
horn and bearing-fit numbers are datasheet/generic until the T2 fit coupons
(`../ball-head-validation-handoff.md`) replace them.

## Parts

| Part | Qty | Prints | Supports | Notes |
|---|---|---|---|---|
| `roots` | 1 | flat on its underside | none | Fixed. Screws to the deck. Pan servo drops in from below. |
| `fork` | 1 | standing on the saddle underside | tree supports under the pod bulbs only | Pans. The part under the most load: 4+ walls. |
| `ball_plus` | 1 | seam face down | touching bed, for the 2 front board posts | +Y half: horn hub, seam screw counterbores |
| `ball_minus` | 1 | seam face down | touching bed, for the 2 front board posts | −Y half: axle D-socket, ribbon slot |
| `axle` | 1 | standing on its end | none | Hollow (slotted) idler axle that doubles as the coil spool |
| `cap_servo` | 1 | outer face down | none | Closes the +Y bulb |
| `cap_coil` | 1 | outer face down | none | Closes the −Y bulb; its spigot ring locates it |

PETG, 0.2 mm layers. The `print/` STLs are already in print orientation, each
centred with its lowest point at Z 0.

## Hardware

| Item | Qty | Where |
|---|---|---|
| MG90D servo | 2 | tilt (+Y bulb), pan (roots) |
| 6704 bearing (20 × 27 × 4) | 1 | −Y bulb seat |
| M2 × 16 | 3 | ball seam: in through the +Y half, threads into the −Y half |
| M2 × 5 | 4 | camera board onto the posts |
| M2 × 8 | 9 | 4 servo tabs, 4 on `cap_servo`, 1 on `cap_coil` |
| M2 × 6 (or the horn's own) | 2 | tilt horn into the ball hub |
| M3 × 10 | 4 | roots to deck |

All M2 holes are pilots for thread-forming screws (Ø1.7) or clearance (Ø2.2).

## Assembly order

1. **Roots:** push the pan servo in from below, with the tabs up into their recess. Screw the tabs, then screw the roots to the deck.
2. **Fork:** press the pan horn into the pocket in the fork's underside. Set the fork on the roots and seat the horn on the pan servo spline. Drive the horn screw down through the access hole in the top of the saddle. The fork should now bear on the slide land only; check for 1 mm of air elsewhere.
3. **Camera:** screw the board to the front posts of `ball_minus`. Run the FPC down under the board, back up behind it, and along the axis out through the −Y hub slot.
4. **Ball:** screw the horn into the `ball_plus` hub. Close the halves with the 3 M2 × 16 screws.
5. **Drop the ball in** between the pods from above. It clears: the ball is 48 mm across its flats, and the pods are 49 mm apart.
6. **Tilt servo:** slide it in from the +Y outboard end, shaft end down, until its spline engages the horn. Screw the tabs to the ledge. Lay the lead in the groove and push it down the branch channel — the channel is servo lead only now.
7. **Idler:** press the 6704 into its seat from the −Y outboard end. Feed the ribbon through the axle slot, push the axle through the bearing, and key its flat into the ball's D-socket.
8. **Coil:** wind 2 loose turns around the axle, then lead the outer end tangentially into the trough in the pod wall and down the stem skirt. No fold anywhere.
9. **Caps** on. The servo lead comes out of the back of the saddle; the ribbon comes out downward at the fork underside, about 42 mm from the pan axis. Leave a slack loop below deck for ±90° of pan.

## Into Fusion

Everything in `fusion/` is in the **assembly frame**, so each part lands exactly
where it belongs:
- **Units:** mm.
- **Axes:** X forward, Y along the tilt axis, Z up from the deck.
- **Tilt axis:** at X 0, Z 48.5.

Every file was checked **watertight, manifold, one body and free of
self-intersections** after cleanup (see `mesh_report.txt`). Those are the things
that make Fusion's Convert Mesh fail.

Two versions of each part:

- **`<part>_blank.obj`:** the organic body only, with no pockets or holes. **Use this one.** Convert it, then add the pockets, bores and holes as normal Fusion features from `features.md`. Every one is listed with its position and size in the same frame, so the features stay editable when a measured servo or fit-coupon number changes.
- **`<part>.obj`:** everything already cut. A reference, or a quick way to check the whole thing in Fusion.

Steps:

1. **Insert → Insert Mesh** → pick the `.obj`.
   - **Unit:** Millimeter.
   - **Leave Center unticked**, so the part keeps its assembly position.
   - If the parts come in lying on their side, your design is Y-up: tick **Flip Up Axis**, or set *Preferences → General → Design → Default modeling orientation* to Z up.
2. **Mesh tab → Prepare → Generate Face Groups** (Accurate). Every flat face is exactly planar, so the flat faces become large clean groups.
3. **Mesh tab → Modify → Convert Mesh:**
   - **Prismatic** (paid licence): turns the flat and cylindrical face groups into real planes and cylinders. Best for the caps, axle and roots.
   - **Faceted** (any licence): one flat face per triangle. Fine for the organic fork and ball, whose surfaces were never going to become clean B-rep patches.
4. Add features from `features.md`.

Face counts are kept low so conversion stays quick:
- **Blanks:** 2–14k faces.
- **Full parts:** 2.8–24k faces.
- **Print STLs:** 250k faces or fewer.

If Fusion is still slow on the fork, **Mesh → Modify → Reduce** it before converting. A smooth, editable organic surface means remodelling it in the **Form** workspace (T-splines) using this mesh as a reference body. A mesh can't be converted into one automatically.

## Size

Measured from the assembled part meshes: **107 wide × 78.9 tall × 58.7 deep**, roots footprint 51 × 51.

Compaction pass, 2026-09-17 (125.4 × 83.2 × 64 before), with the coil mechanism untouched:

| Change | Effect |
|---|---|
| Ball truncated at Y ±24 | The board is only 36 wide, so the ball's spherical sides were empty space holding both pods apart. The flats are now the horn hub and the axle hub faces. |
| Board moved back to X 4.0 | Ball Ø59.2 → Ø56.6 |
| Tilt axis 52.1 → 48.5 | The smaller ball let it come back down; the saddle keeps 2.9 mm of floor over the pan horn pocket |
| Ball clearance 4.0 → 1.5 | The lens bezel's swept band is cleared separately, only where it actually sweeps |
| Pods Ø44 → Ø43, caps 2.5 → 1.8 | |
| Root lobes and deck screws pulled in | footprint 64 → 51 |

What did **not** change: the 6704 idler, the Ø37.6 coil chamber, the ribbon width and the axle. The T1 coil rig still tests the right thing.

Interference is re-checked by `tree_parts_check.py`: zero overlap across tilt −60° to +75° and pan ±90°.

## What changed from the earlier one-piece concept

- **Tilt axis raised** from 46.1, so the saddle under the ball is thick enough to carry the pan horn pocket.
- **Pods deep enough for the servo's tabs**, which Ø40 × 22 never was.
- **The −Y ball stub is a separate keyed axle**, so the ball drops in from above and the fork stays one piece.
- **The fork never sits flat on the roots.** A slide land at r 15–18 mm carries it, with 1 mm of air everywhere else.

## Cable routing rules

From the 2026-09-18 print review (`docs/lessons/2026-09-18-flat-cable-and-driver-access.md`):
no creases in the camera ribbon, every turn a curve of at least 3 mm radius, and any
out-of-plane change made as a twist over ~40 mm in a bore about the ribbon's width.

- **Camera ribbon:** leaves the coil tangentially and drops down an enclosed trough moulded into the −Y pod wall and the stem skirt below it. It keeps its width along the tilt axis the whole way, so every turn is an in-plane curve. Minimum bend radius on the path: **7.3 mm**. It exits downward at the fork underside, about **42 mm** from the pan axis, so the deck needs an arc-shaped opening there and a slack loop below.
- **Servo leads:** the branch channel is now theirs alone, 8.3 × 5.2, and its run out of the back of the saddle is a curve instead of a box corner.
- **Still open:** the static twist where the ribbon crosses from the board inside the ball to the coil chamber outboard of it. It needs a round bore about the ribbon's width, which is what the axle/bearing question is about.

## Still unverified

- MG90D body, tab height and spline height (datasheet).
- Horn pockets (generic 34.4 × 6.2).
- 6704 seat (27.1 bore).
- Whether the servo plug fits the branch channels (it should, just).
- Seam screw length.
- **Ribbon width and thickness** — assumed 16.0 × 0.3. Everything on the −Y side scales off it.
