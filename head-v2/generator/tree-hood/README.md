# Variant C — the hood head

Concept geometry, 2026-09-18. Generator `../generators/tree_hood.py`, interference check
`../generators/tree_hood_check.py`, viewer at https://claude.ai/artifact/94q1eeyW7FKFkLAPTugMSt
(variant button **C · hood**).

**This is concept level.** Fusion-ready OBJs and viewer meshes only — no print STLs, no
`features.md`, no BOM. Several driving dimensions are assumed; see *What has to be measured*.

## The idea

In variants A and B the ball is both the enclosure **and** the moving part. That single decision is
what forces everything else: a rotating sphere needs bearings, needs a shroud or cradle to sit in,
and — worst of all — makes the camera ribbon cross a rotating joint at full ball radius, which is
what the coil (A) and the rolling loop (B) exist to absorb.

C separates the two jobs. Nothing large rotates:

- the **hood** is a fixed cover that pans with the head but never tilts;
- the **camera** swings inside it on two M3 screws;
- the **ribbon** stays inside the shell and just flexes behind the board.

The bearings, the shroud, the cradle, the axle, the coil and the rolling loop all disappear.

## The window

The window is not a designed shape. It is the **swept union of the camera's view cone** over the
whole tilt range, cut through the shell:

```python
window(p) = U(view_cone(p, t) for t in linspace(TILT_LO, TILT_HI, 41))
```

So it is exactly as big as it has to be and no bigger — a tall slot in the nose, roughly 10 mm wide
and 38 mm of arc. The lens sits ~3 mm behind the shell and **never pokes out**, so there is nothing
to catch, nothing to seal around, and the barrel is protected.

The check script verifies this the honest way: it looks for any hood or yoke material inside the
view cone at every tilt. All ten of those rows read 0.00 mm³.

## Parts

| Part | Notes |
|---|---|
| `roots` | Unchanged, shared with A and B. Pan servo, screws to the deck. |
| `spine` | The chassis. Pan horn foot, tilt servo cradle, ribbon shaft, and the two cheeks that carry the tilt pivots. |
| `yoke` | Camera cradle. Grips the IR-cut holder **only**. |
| `crank` | On the tilt servo's shaft. |
| `rod` | Crank → yoke. Two M2 pins. |
| `hood` | One continuous shell over everything. Window slot, 2.4 mm wall, 4 screws. |

Hardware: 2 × MG90D, 2 × M3×10 (tilt pivots), 2 × M2 (servo tabs), 2 × M2 (link pins),
4 × M2×8 (hood), 4 × M3×10 (deck), 1 × M2 (holder pinch). **No bearings.**

## Why the yoke only grips the holder

The camera board is 36 mm wide — wider than anything else inside the head. Anything that reached
*past* the board to hold it would itself have to be wider than the board, and then the hood would
have to be wider than that. So the yoke stops in front of the board, clamps the IR-cut holder, and
the board hangs off the holder behind it — which is how the module is actually built. It also keeps
the whole yoke clear of the FPC tail, which is the mistake that bit the earlier variants.

## Why the linkage is outboard, and why the head is 61 mm wide

The board sweeps a disc of radius `hypot(8, 16) = 17.9 mm` about the tilt axis. Two separate
searches (`link8.py`, `link9.py` in the session scratchpad) found **zero** four-bar solutions whose
rod stays outside that disc across 75° of tilt. A straight pushrod cannot reach the yoke without
crossing the board's plane. So the pivot cheeks and the whole linkage run outboard of the board, and
the width is a chain built on one number:

```
half-width = BOARD_W/2 + cheek + rod + crank + clearance + wall
           = 18.0      + 3.3   + 3.0 + 3.4   + 0.5       + 2.4  = 30.6
```

**Measuring the board is worth about 6 mm of head width per 10 mm of board.** At the assumed 36 mm
the head is 61 mm wide; a 25 mm board would bring it to roughly 50.

## Numbers

| | A | B | **C** |
|---|---|---|---|
| Width | 107 | 68 | **61** |
| Height | 79 | 80 | 73 |
| Depth | 59 | 80 | 56 |
| Printed parts | 7 | 6 | **6** |
| Bearings | 1 × 6704 | 2 × 6704 | **none** |
| Ribbon across tilt | coil, R 7.3 | rolling loop, R 4.0 | **free flex, no joint crossed** |
| Tilt range | −60…+75° | 180° | −35…+40° |

Tilt four-bar: crank 14, yoke arm 16 at 295°, rod 16.5, servo shaft at (−8, H−27).
Transmission angle stays ≥ 51.6°, and 75° of tilt costs 92.5° of servo travel — ±46° of the
MG90D's ±60°, so there is real margin at both ends.

## Verification

`python tree_hood_check.py` — 62 rows, voxel overlap on a 0.5 mm grid, **all 0.00 mm³**:
camera / yoke / rod / crank against the hood, spine and servo at five tilt angles; the fixed stack;
pan at 45° and 90° against the roots; and the ten view-cone rows.

All six meshes: watertight, 2-manifold, one body, zero self-intersections.

## What has to be measured

Everything below is assumed. The first two change the head's dimensions directly.

1. **Camera board width and height** — assumed 36 × 32. Sets the head's width (see above) and the
   swept disc that the whole linkage has to dodge.
2. **Ribbon width and thickness** — assumed 16.0 × 0.3. Sets the spine's ribbon shaft.
3. **Camera field of view** — assumed 65 × 50°, inflated 15% in the cut for tolerance. Sets the
   window.
4. **MG90D case, tab and spline; the actual horn** — datasheet and generic respectively.

## Open questions

- **Print orientation for the hood.** It is a barrel shell with a slot. Nose-up on the tail is the
  obvious try; the brow will want support either way.
- **Yoke grip.** Currently an interference collar plus one pinch screw. A proper split clamp may be
  wanted once the holder's real diameter is known.
- **Link pins.** M2 through printed bosses. Fine for a concept; a real build probably wants brass
  bushes or ball links.
