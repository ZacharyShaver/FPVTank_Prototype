# A voxel mask terraces the surface

2026-10-30, the one-piece bodies (`gauges/unibody.py`).

**What happened.** Zach called the sheets' shapes bumpy and unrealistic. Part of that was the knobs (blobs, the
ripple) and the growth, which add lumps on purpose. The striping was not. The body's core is a convex hull with an
exact field, but union() thresholded it to 2 mm voxels and rebuilt a distance from the mask (twice, for the rounding).
That put the surface on voxel faces: flat faces came out in 2 mm terraces up to 1.0 mm off, rounded ones up to 3.3 mm.
Growth then built on the steps. With the core's field exact (core_field), the stripes went, before and after growth,
and the masses and stresses moved under 1 %. Separately, the 150k-face decimation folded 6-32 faces through their
neighbours on every design; the mesh report had never been run on these meshes.

**Why it slipped.** The renders were small, the steps read as texture, and nothing measured a flat face's flatness or
ran the mesh report on the generator's own output.

**How to apply.** Keep a field exact where its surface is drawn; voxelize only for the stress solve. Test a mesher on
a shape whose answer is known (a convex hull must mesh flat), with the old method as the control. Run the mesh report
on every generator's meshes, not only on print exports. `python gauges/unibody.py check` does both. Related:
`2026-10-29-a-rigid-root-hides-the-joint.md`.
