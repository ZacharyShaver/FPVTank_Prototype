# An SDF value is a bound, not a distance

2026-10-02, the wire route check. The passage test took each part's SDF value at the route's centreline as
the clearance. At the drum's bore lip it read 0.70 mm, BLOCKED. The nearest drum material was really
3.6 mm away. The generator's SDFs are built with max/min/smooth-min. Inside a union or a cut they bound
the distance; they don't equal it, and they can read far smaller than the real gap.

Rule: measure clearance by probing for material (points on growing spheres, or a voxel test), not by
reading an SDF value as a distance. An SDF's sign is trustworthy; its size isn't. `checks/wire_route.py`
probes with spheres.
