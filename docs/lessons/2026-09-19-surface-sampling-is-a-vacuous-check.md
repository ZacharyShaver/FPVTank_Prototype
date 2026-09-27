# Sampling a surface does not check a solid

**2026-09-19.** Found while rebuilding variant B's parts as STEP solids
(`generators/tree_parts_b_step.py`).

## What happened

The five non-organic parts were rebuilt from the SDF source as real BREP solids. To prove the
rebuild matched, the obvious check was reused from `fusion_convert.py`: sample points on the
surface, feed them back through the signed-distance field, report the 99.9th percentile of
|distance|.

All five read **0.0000**, max and all. That was believed for about a minute, and it was the
exactness that made it suspect — a number that clean usually means the test is not connected
to anything.

A negative control settled it. A Ø4 bore was driven straight through the post's flange,
removing **22.6 mm³** of real material — confirmed by volume, and it added a face. The surface
check still read **0.0000**.

## Why it is vacuous

OpenCascade puts most of a tessellation's vertices on face **boundaries**. A bore straight
through a plate has both of its boundary circles lying in faces the part already had — the two
flange flats. So every vertex that bore contributes sits exactly on the original surface, and
the field says zero at all of them. The material between them is never sampled, because
nothing puts a sample point there.

Adding triangle interiors makes it bite, but buys a second problem: a flat triangle chords
*inside* a curved face, so the two ball halves read ~0.09 while being exact and the
mostly-planar post reads ~0.005. The number then measures the tessellation, not the part — and
those triangles are not even in the STEP file, which stores the analytic sphere.

## What replaced it

A Monte-Carlo **set difference**: scatter points through the bounding box and ask *both* the
solid and the field whether each one is inside. Report the volume they disagree over. That
sees material wherever it is, not only where a vertex happened to land.

Against three deliberately broken posts:

| Fault | surface check | set difference |
|---|---|---|
| correct part (control) | 0.0053 | **0.00 mm³** |
| bogus Ø4 bore through the flange | 0.7200 | **21.99 mm³** |
| one screw hole left out | 0.0053 — blind | **7.01 mm³** |
| shaft 0.3 mm oversize | 0.3000 | **344.12 mm³** |

Row three is the one that matters. A **missing** cut leaves every remaining surface exactly
where it belongs, so no surface metric of any sampling density can ever see it. Only a test
that asks about volume can.

## The general form

A check that samples a **boundary** cannot see an error in the **interior**, and a missing
feature is always an interior error. This is the same shape of mistake as the
`tree_parts_b_driver.py` row that passed by accident (HANDOFF §4b): it modelled the ball as two
hollow halves, so a driver shaft sat in the cavity and read "clear" from somewhere no driver
could be. Both passed because the thing being asked about was never in the sampled set.

**Every zero gets a negative control before it is believed.** Breaking the part on purpose and
watching the number move costs a minute and is the only thing that distinguishes "correct" from
"not connected".
