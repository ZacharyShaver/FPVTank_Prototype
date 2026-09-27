# head-v2: live state

Drained, not grown: when an item is done, take it out. Its record goes to `docs/decisions.md` or git.
As of 2026-09-27.

## Current

- Ball rev 2 = Zach's Fusion rev 1 (`fusion/rev1-2026-09-24/`) + snap pins + post v3, plus the
  **camera snap posts** (2026-09-26): two posts pushed in from outside through his old camera-board
  screw tubes. They replace the screws. Scripts: `fixes/campost.py` and the steps after it in
  `build_all.py`; check: `checks/check_campost.py`.
- The print set he has is `Downloads/head-v2-snap/`; its `README.txt` is the index (what to print
  first, assembly).
  - `python head-v2/fixes/build_all.py` regenerates it into `out/`. Every STL, both 3MF plates' meshes
    and the pictures are byte-identical to that set. The STEP files differ only in metadata (timestamp,
    assembly ids, colour order); their solids match. Re-verified 2026-09-26 after the camera posts.
  - `python head-v2/checks/regression.py` reproduces its checks: all 22 rows.
  - Both verified 2026-09-26, and again on 2026-09-27 after the repos moved off OneDrive to
    `C:\Users\<usr>\Documents\GitHub`.
- The hand-off also has `step/`: the finished parts as STEP solids (`fixes/step_models.py`).
- Superseded, don't print: `Downloads/head-v2-fixes/` (rev 1, screws), the pins in
  `head-v2-snap/superseded - first pins, no stop/`, and the pre-camera-post ball_plus and plate in
  `head-v2-snap/superseded - before camera posts/`. `out/` still builds those: the rev-2 checks read them.
- Before changing the ball, the post or the seam, ask Zach which files he printed.

## Open

- **Pin size:** not picked yet (2026-09-26). Print two test blocks and one stop pin of each size. The
  3MF plates carry medium; if he picks soft or firm, change `PIN` in `fixes/plate3mf.py` and `PIN` and
  `CAM` in `fixes/plate_campost.py`. The camera posts use the same grade names; he was told to match.
- **Camera board hole size:** 2.0 is a photo value, not calipered. The camera posts' pin is 1.8
  (`campost.R_PIN`). When he calipers a hole, set the pin 0.1 under it and rebuild.
- **ball_plus's exact BREP doesn't survive STEP.** With the camera tubes fused in, it passes BRepCheck
  and meshes to a clean, right-sized STL, but ShapeFix and STEP readers lose 490 mm3 from it. The
  shipped STEP is sewn from the STL instead (`fixes/step_models.py`). The root cause, somewhere where
  the new tube walls meet his facets, isn't found. Suspect it first if a Fusion boolean with
  `camera_post_tools_for_fusion.step` misbehaves.
- **Nest SDF sheets:** the nest's SDF has zero-thickness sheets at |Y| 25.0 and 26.5 in the hub bore.
  They read as "touching" but aren't material. `lens_nest.nest_sweep` steps around the 26.5 one only.
  So `checks/ball_nest.py` reports ball_plus's nearest approach as 0.10 mm: that is its hub beside the
  25.0 sheet (Y 25.08, 8.9 from the tilt axis), not the nest. "Deepest" isn't affected. Unfixed; the
  generator is here now (`generator/generators/tree_parts_b.py`).
- **Seam screw heads in the generator:** `tree_parts_b.py` still has the screw-pocket bug. Moot for
  printing (the ball is Zach's model, with snap pins), but it matters if the generator's ball is used.
- **The generator doesn't have Zach's revision.** Porting it was offered and hasn't been answered.
- **Cradle bottom onto the 360° pan coil:** `generator/pan-coil-360-brief.md` §6.2 lists the changes
  (horn pocket and centre hole out, 3 × M3 at r 20, ribbon groove onto the axis). Blocked on where the
  ribbon's quarter twist goes (§5.0): 21 mm of run against ~40 needed. Zach leans to twisting inside
  the nest (2026-09-27); not yet modelled. The cradle blank route didn't work for him: the cradle is
  edited in the generator.
