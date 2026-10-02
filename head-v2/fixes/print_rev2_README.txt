HEAD REV 2 -- 2026-09-27
Zach's Fusion rev 2 halves, the IR cutout extended 2 mm, and the camera posts regenerated for his moved
tubes. Supersedes the posts in the snap set (head-v2-snap): those were made for tubes 2 mm lower.

PRINT (plate_rev2_full.3mf has one of each, in medium)
  ball_plus_rev2.stl          his rev 2 + the IR cutout extension. Seam face down.
  ball_minus_rev2.stl         his rev 2, unchanged (it is the snap version). Seam face down.
  post_v3.stl                 unchanged.
  snap_pin_stop_medium.stl    x4, unchanged.
  camera_post_upper_medium.stl, camera_post_lower_medium.stl   NEW. Lying on the flat, head up.
    The upper post is the longer one; its top flat is wider, so it won't go in the lower hole.
    soft / firm versions are here too if the click is wrong.

WHAT CHANGED FROM THE LAST SET
  - Camera posts: your tubes are 2.00 mm higher (Z 37.95 and 66.85, both at Y 14.70), so the lens
    sits centred between them. The posts are rebuilt for that: the flats turn with the tube and the
    head is trimmed to where the tube now leaves the ball.
  - The pin tip is 1.48 across where it enters your wall hole (1.78). At 1.80 it would jam.
  - The lower tube is straight up too (Y 14.70). Both were measured off your wall holes.
  - IR cutout: your 32 mm circle moved 2.0 mm toward the post side (+Y), through the 2 mm plate at
    X 14-16, between Z 42.4 and 62.4. That keeps it 1 mm off both post tubes; the full-height shifted
    circle would cut into them. The edge is at Y 18.0 at mid-height now (was 16.0).
    In Fusion: CUT_plus_ir_extend in rev2_tools_for_fusion.step, or redraw it: a 32 mm circle
    centred (Y 2.0, Z 52.0), extruded through the plate, trimmed to Z 42.4..62.4.

CHECKED (head-v2/checks/check_campost_rev2.py, rev2_nest.py; logs in head-v2/out/logs/)
  - camera, servo, post, the other half vs ball_plus: 0; the posts through the board's holes: 0
    (control: the old photo board reads 4.98 -- the 2 mm you fixed)
  - posts seated, sliding in, heads 0.2 under the ball, swap-proofing, catch walls
  - both halves vs the nest through the full tilt: 0 inside; lens to nest 1.83 mm
  - the IR cut: 1.05 / 1.08 mm clear of the tube walls, camera still 0

ONE MESH NOTE (from your export, not fixed here)
  ball_plus_rev2.stl carries 11 crossed faces and 8 non-manifold edges from the Fusion export. Your
  slicer repairs faults this small on import. To clean them at the source:
  - 11 crossed faces at X 19-22, Y 11-15, Z 35.8-36.4: just above the lower tube, where it used to be.
    Probably a sliver left from the move.
  - 8 non-manifold edges at the back, X -21.3, Y 19.4, Z 46-58: two bodies touching along an edge.
    Combine them before exporting.
  The mesh repair here couldn't fix them without opening a hole, so the file is left as exported.

ON THE CAMERA MODEL
  The lens is centred on the board's holes now (your call; the photo had it 1.6 off). The pins place
  the board, so the lens ends up 0.40 above the tilt axis -- your "by hand" margin. Harmless.
