# Zach's Fusion revision 2 (exported 2026-09-27)

These are his files as he sent them.

| File | Part |
|---|---|
| `ball_plus_revised_9_27.stl` | ball_plus: the half the servo and camera go into |
| `ball_minus_revised_27.stl` | ball_minus |

The post isn't in this export: it is still post v3 (`head-v2/out/ball_servo_post_v3.stl`).

He built this on the parts shipped as ball rev 2 (rev 1 plus the fixes in `head-v2/fixes/`), with the
fixes' booleans done in Fusion. Measured against those shipped parts (voxel diff, then slices):
- **ball_minus** is identical to the shipped `ball_minus_revised_snap.stl` (0 mm³ either way).
- **ball_plus**, three changes (Zach: "posts moved, some errors fixed, IR cutout reshaped"):
  - both camera-post tubes moved **+2.0 mm in Z**, same Y (14.8/14.9) and size: centres Z 37.85 and
    67.03 at X 14–18, from 35.85 and 65.03;
  - the rib joining the two tubes at X 14–16 is gone, and the IR-cut holder's opening at X 14 is
    now a straight edge at Y ≈ 11.3 where it was an arc;
  - the lens opening at the front did not move.

Mesh health: ball_minus is clean. ball_plus has 11 self-intersections and non-manifold edges (rev 1
had 5); OCC sews it into one valid shell with no free edges.
