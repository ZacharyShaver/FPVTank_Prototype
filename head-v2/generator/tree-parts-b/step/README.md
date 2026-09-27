# Variant B for Fusion: 5 parts as real solids, 2 as prepared meshes

**Written 2026-09-19.** Replaces `fusion-convert/` as the thing to import.

## The short version

| You want | Open | What arrives |
|---|---|---|
| `post`, `axle`, `cap_minus`, `ball_plus`, `ball_minus` | `step/<part>.step` | A solid body. **No Convert Mesh at all.** |
| `fork`, `roots` | `fusion-solid/<part>_blank.obj` | A mesh to convert, then cut the rows in `../features.md` |

## Why the old OBJs fought you

They are marching-cubes output — the shape was measured on a grid and the surface
reconstructed from triangles. A flat face in one of those is a few hundred triangles that are
all *nearly* coplanar but no two exactly so, and a bore is a ring of facets. Fusion's Convert
Mesh works by recognising surfaces — "these triangles are one plane", "these are one cylinder"
— and there is nothing there to recognise.

That is a **structure** problem, not a size problem, which is why `fusion-convert/` (the same
meshes decimated to 4–8k faces) did not help: fewer triangles, still no structure.

## What changed

Five of the seven parts never needed a mesh in the first place. Read them in
`generators/tree_parts_b.py`: `post`, `axle`, `cap_minus`, `ball_plus` and `ball_minus` are
built purely from spheres, cylinders and boxes added and subtracted — **no blended surfaces
anywhere**. So they are rebuilt from the same parameters through a real CAD kernel and written
as STEP, the format Fusion imports as solid geometry.

A sphere stays a sphere. A bore stays a cylinder you can select, dimension and change.

```
part         faces  edges     was (OBJ triangles)
post            45     98      5,000
axle            11     27      4,000
cap_minus        8     16      4,000
ball_plus       68    159     20,000
ball_minus      90    217     20,000
```

`fork` and `roots` are **not** in `step/`, and that is honest rather than unfinished. The nest
is a curve-swept trunk that blends smoothly into a cup and then into the two collars; roots is
four lobes blended into a pedestal. That blending is not a fillet — it pulls both surfaces
toward each other well away from the joint — so there is no analytic solid to rebuild. Those
two keep the mesh route, and get a blank instead.

## The blanks

`fusion-solid/fork_blank.obj` and `roots_blank.obj` have **every small analytic feature left
out** — bearing seats, bores, flange recesses, screw pilots, the pan horn pocket. Those are
exactly what Convert Mesh handles worst (a Ø1.7 pilot hole becomes a ragged 12-sided prism) and
exactly what is most likely to move when a measurement lands. Cut them natively from
[`../features.md`](../features.md) instead and they stay editable.

Two cuts are **kept in the blank** and flagged in the table: the ribbon trough, which follows a
curve down the trunk, and the rolling-loop track behind the ball. Nobody would redraw those by
hand — they are the shape, not features.

## Regenerating

```bash
cd ../../generators
python build_b.py --solids --check    # the 5 solids + the analytic checks   (seconds)
python build_b.py                     # ... and the 2 blanks + features.md   (~10 min)
```

`build_b.py` is the front door; the individual scripts still work and keep their own options.

## The one thing that will bite you

`tree_parts_b_step.py` reads every **number** straight off `tree_parts_b.py`, so changing a
parameter — a diameter, a Y position, a fit — flows through automatically. But the **shape of
the construction** is written out by hand a second time, mirroring the SDF. Change the
*structure* of a part (add a cut, move a boundary from a constant to an expression, re-order a
boolean) and the mirror does not follow.

It fails loudly rather than silently, which is the whole reason the disagreement check exists.
**This has already happened once**, on 2026-09-19: two structural edits landed in
`tree_parts_b.py` — the servo pad shortened from `24` to `BOARD_X0 - 0.1`, and the board groove
widened from `BOARD_Y - 2.6` to `3.2`. The next run reported **296.14 mm³** on `ball_minus` and
**37.31 mm³** on `ball_plus`, and the two magnitudes matched the two edits almost exactly. The
fix was the same two lines in the mirror.

So: **if `disagree` is anything but 0.00, the mirror is behind the SDF.** Find the edit in
`tree_parts_b.py`, make the same one in `tree_parts_b_step.py`, re-run. The size of the number
tells you roughly how big the missing feature is, and which part tells you where to look.

Nothing downstream is trustworthy while that column is non-zero — the STEP is then a picture of
an older part.

## How far this is verified

Each solid is checked two ways against the signed-distance field it came from:

- **Disagreement volume** — points are scattered through the part's bounding box and *both* the
  solid and the original field are asked whether each one is inside. The volume they disagree
  over is **0.00 mm³** on all five, at ~0.65 mm³ resolution.
- **Volume** against the meshed original: within **0.3 %**, which is the mesh's own error.

And by eye: [`step_vs_obj.png`](step_vs_obj.png) renders each solid beside the OBJ it replaces,
same view, same scale. They are feature-for-feature identical — the axle's slot and flat, the
three cap screws, the lens bore and hub stub on `ball_plus`, the board rails, axle socket, seam
rods and ribbon slot on `ball_minus`.

The disagreement check was **negative-controlled**, because the obvious check turned out to be
vacuous. Sampling only the surface reads a perfect zero even on a part with a Ø4 bore driven
straight through its flange, because Fusion's triangulation puts its points on face *edges* and
both ends of that bore land on faces the part already had. Against the same three deliberately
broken posts the disagreement check reads 21.99 mm³ (bogus bore), 7.01 mm³ (a screw hole left
out) and 344.12 mm³ (shaft 0.3 mm oversize). It bites.

**Not verified:** that Fusion opens these the way it should. There is no Fusion on the machine
these were built on. The STEP files re-import and validate through the CAD kernel — 1 solid
body each, `isValid` true — but the last step is yours.

**Still concept geometry.** Everything in `../HANDOFF.md` §4 about unmeasured camera numbers
applies unchanged; these are the same parts in a better format, not better parts.

---

## Update 2026-09-19, evening — 3 of 5 clean, and why

The source moved after this set was first written (servo drop, camera fixes, ball
stiffening, M3 seam, bearing retaining rings). `tree_parts_b_step.py` has been
synced and re-run:

| part | disagree | state |
|---|---|---|
| `post` | **0.00 mm³** | exact. Now carries the bearing retaining ring |
| `axle` | **0.00 mm³** | exact |
| `cap_minus` | **0.00 mm³** | exact. Now carries its retaining ring |
| `ball_plus` | 1387 mm³ (−11.7 %) | ⚠ **approximate — do not treat as the part** |
| `ball_minus` | 1452 mm³ (−11.5 %) | ⚠ **approximate — do not treat as the part** |

**The ball halves stopped being CSG.** Stiffening them on 2026-09-19 added two
features that have no analytic equivalent, and together they are the entire
shortfall:

- the **faded rear wall** (`rin()`, a smoothstep from 1.2 mm at the front to
  2.4 mm at the back) — 0.85 / 0.81 cm³ per half
- **`smin` fillets** where every internal rib meets the shell — 0.47 / 0.59 cm³

Neither is decoration. Measured on `ball_plus`, the fillets alone take the rail's
contact with the shell from 51 → 101 mm² and the hub stub's from 117 → 263 mm².
Dropping them gives back about half of the stiffening.

So the two ball halves now belong with `fork` and `roots` on the mesh route, not
here — **unless** the choice is made the other way. That decision is open:

1. **Keep the stiffening.** Ball halves import as meshes, like the other organic
   parts. Costs manual conversion for the two parts most likely to need edits.
2. **Make them CSG again.** Replace the faded rear wall with a step plus an
   explicit fillet, and rebuild the rib junctions as OCC fillet operations
   (`step_kit.fillet_all` already exists and already reports failures). Uncertain
   — fillets on a sphere-and-rib intersection are exactly the case OCC struggles
   with — but it would give solid bodies for every non-organic part.

The `.step` files for the two halves **are still written**, deliberately, so the
comparison stays reproducible. They are not the part.
