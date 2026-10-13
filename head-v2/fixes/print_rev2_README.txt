+Y HUB AS A SLEEVE -- 2026-10-03: PRINT plate_plus_sleeve.3mf (ball_plus_sleeve + two sleeves)
  The cradle's +Y arm kept snapping: the hub on your ball_plus stood 5.8 mm past the flat face (to Y
  30.3) and the collar's face is at Y 25.1, so the arm had to spread ~5 mm to let the ball in. The hub
  is now its own part. Nothing stands past the ball's flat faces, so the ball drops straight in.
    ball_plus_sleeve.stl   your rev 2 ball_plus (with the IR cutout extension) minus the hub, plus a
                           1.5 mm socket in the flat face, keyed by a flat on the lens side. Seam face down.
    sleeve_press_200.stl   the hub: your 16.0 bore and the notch for the servo's gear bump, 8.6 long, the
    sleeve_press_201.stl   matching flat on one end and a stop lip on the other. The 6704 presses on:
                           outside 20.0 or 20.1, two to try (on a 19.9 slip the bearing never turned).
                           Each stands on its lip.
  Unchanged: the cradle you have, post v3, both 6704s, the servo, the -Y stub. No new screws.
  ASSEMBLY (+Y side; the -Y side is as before)
    0. On the bench: press the 6704 onto the 20.0 sleeve from the flat end until it stops on the lip.
       If it slides on loose, use the 20.1 one.
    1. Ball straight down into the nest.
    2. Sleeve and bearing together in from outside through the +Y collar, flat end first, the flat
       toward the lens. Turn it (or tilt the ball) until it drops the last 1.2 mm into the socket; the bearing seats in the
       collar at the same time.
    3. Post v3 on, 3 x M2 as before. Its ring holds the bearing's outer ring; its flange is 0.3 mm off
       the sleeve's end.
    4. The -Y stub, 3 x M2 x 6, as before.
  IN FUSION: CUT_plus_hub in plus_sleeve_tools_for_fusion.step, cut from ball_plus (his coordinates).
    SLEEVE_seated is the sleeve where it sits, for reference. Or redraw it: remove the hub flush with the
    flat face; cut an annulus r 7.6..10.1, 1.5 deep (Y 23.0..24.5), trimmed by a flat at X +9.0.
  CHECKED (head-v2/checks/plus_sleeve_fit.py)
    - Ball lowered straight in: today 1,520 columns of the hub hit the +Y collar; with the sleeve, 0 at
      either collar.
    - Both sleeves in place vs the cut ball, post v3, the cradle, the 6704's outer ring and your MG90S:
      0 mm3. The inner ring overlaps by the press (0.05 on the 20.1). Controls: 0.3 deeper it hits the
      socket floor; without the notch it hits the servo's gear bump; a wider lip hits the outer ring.
    - Sleeve and 6704 together slide in from +Y unblocked. Control: into the old ball, blocked.
  GAPS (your slide rule, 0.15 a side): socket wall 0.15, key flat 0.15, plate ring 0.4, the sleeve's end
    0.3 off the socket floor (the post sets where the ball sits along the axis, the bearing where the
    sleeve does), its other end 0.3 off the post's flange.
  GUESSES: the press, 20.0 / 20.1; socket depth 1.5 (your plate is only ~2.2 thick at the bottom of the
    face: 0.69 is left there, the thinnest spot); the key's flat at X 9.0; the lip r 11.0 (a 6704's
    inner ring is about 22.6 across, from typical drawings); the servo's height (from post v3's fit:
    the notch stops at Y 27.0, past the post's inner end, so the bearing presses onto a full 2 mm wall).
  ALSO FOUND, not changed: the collar's shoulder touches the 6704's inner ring as well as its outer one,
    so a fixed face rubs the turning ring (it always has). And the ribbon track's top lip at the back
    reaches ~1 mm over the ball's widest point, in both versions.
  Superseded: ball_plus_rev2.stl ("superseded - ball_plus with the hub on/"), and its copy on
    plate_rev2_full.3mf. The ball_plus you have still works, with the arm bent to fit it. Also the
    first, slip-fit sleeve and its plate, never printed ("superseded - slip-fit sleeve (never printed)/").
  3D view: https://claude.ai/artifact/35Gmu4fdxbpRQeN6P8zBok

SUPERSEDED (2026-10-02): ball_minus_rev2.stl, and its copy on plate_rev2_full.3mf. Your ball_minus now has
a 6704 cup: print ball_minus_cup.stl from head-v2/out/print-pan/ (it's on plate_wire_route_r1.3mf). The
old file is in "superseded - ball_minus before the bearing cup/". The other parts here are unchanged.

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
