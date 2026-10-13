# Stacked copies hide overlaps; corner points miss flat faces (2026-10-05)

**What happened.** The chassis checks swept the head through 12 pan angles by stacking 12 rotated copies of the
cradle and ball into one mesh, then counting its overlap with the hull in 1 mm voxels. The voxel test decides
inside or outside by parity: it counts how many surfaces a line crosses. Where two copies overlap, a point is
inside both, the crossings come in pairs, and the parity calls it outside. Most of the swept volume cancelled.
The controls still read above zero (476 and 203 mm³), so the checks looked healthy. Checked one angle at a time,
the same controls read 3420 and 741 mm³: the old checks were about a seventh and a quarter as sensitive as
reported. The same mistake in a pack-lift check read zero on its control, which is how it surfaced.

A second, related miss: a belly-clearance profile and a cross-section were built from mesh vertices near a
plane. A long flat face has vertices only at its ends, so the tunnel roof and the skirts vanished from them.

The same day it failed the other way (`chassis-v2/trainer.py`): a tyre and its rim share a surface, R 47. Stacked
into one mesh with the other wheels, each line met that surface twice at the same height, the scan merged the two
crossings as a duplicate, and the parity flipped for everything beyond. The wheels read 180 cm³ into their pods,
where each corner checked alone read zero.

**Rule.**
- Never stack overlapping copies of one closed mesh into a parity-based check. Check each copy and sum.
- Nor parts that touch: stacked, a shared surface counts once instead of twice. Check part against part and sum.
- Sample surfaces with rays or exact slices, not vertices, unless the quantity is an extreme (a convex hull or
  an extreme point is always at a vertex, so those are fine).
- A control that reads above zero is necessary, not sufficient: compare its size with what the geometry says
  it should be.
