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

- **Head rev 2 (2026-09-27):** Zach's Fusion rev 2 (`fusion/rev2-2026-09-27/`, its README), with the
  camera posts rebuilt for his moved tubes and the IR cutout extended 2 mm. The hand-off is
  `out/print-rev2/`. Build order: `fixes/campost_rev2.py`, `ball_plus_rev2.py`,
  `export_campost_rev2.py`, `figure_rev2.py`. Checks: `checks/check_campost_rev2.py`, `rev2_nest.py`
  (in `regression.py`). The 3D view shows it: https://claude.ai/artifact/NKDFgbD3YuAp3xg7JZudVj
  (`fixes/fit_view.py`).

## Open

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
- **Pan coil test print, set 2 (2026-09-27):** the cradle bolts onto the drum (`docs/decisions.md`).
  Set 1 couldn't be assembled (the gear moulded on the drum, the gear bay closed). Set 2, in
  `out/print-pan/` (`fixes/pan_print_set.py`), fuses the well and the gear bay into `base`, takes the
  bay's floor off as a plate, and makes the drum's gear its own part. Zach was part-way through printing
  set 1 (the well half done) when this was found; the cradle and the input gear carry over. Ask what
  fit before changing any of it. Open: the input gear's horn pocket is a placeholder (Zach re-cuts it in
  Fusion; the servo's shaft must end inside the horn); the ribbon thickness is uncalipered; where the
  base screws to the tank is undecided (the old deck screws sat under the bearing, brief §6.3).
- **Cradle plug chute (2026-09-27, later):** the cradle has a 4 mm groove plus a straight plug chute
  (`tree_parts_b.CHUTE_T`, `chute()`; hand-off `fixes/cradle_chute.py`; check `checks/plug_passage.py`).
  The old groove never opened into the track. Zach's servo connector: **14 long × 8 wide** (calipered);
  thickness not measured. Set 3's drum passes it (side slot top Z 2.0); set 2's jams at 3.0 thick.
- **Pan coil set 3 (2026-09-28; tab block 2026-09-29):** built on Zach's MG90S model
  (`generator/pan-coil-b/MG90S.3MF`, check `checks/pan_servo_fit.py`), plus a slide-in tab block under the
  servo's window-end tab, whose screw had nothing to bite (`pan_coil_b.tab_block`). Reprint base and
  drum, print the tab block. Open: the input gear's horn pocket is still
  the placeholder. With the horn's hub on the block face, its arms sit 2.5–4.5 mm below the gear's top
  (1.5 of roof); Zach re-cuts it in Fusion. Open too: he doesn't have the tilt axis's 2 × 6704 and asked
  to use a 6809 (he has 10). Where it goes wasn't settled: he mentioned "under the coil on the post, size
  the post to match", then dismissed the clarifying question.
- **Servo wire route, round 1 (2026-10-02):** the stub replaces the −Y axle and cap; a 5 mm wire hole runs
  down the cradle's −Y wall (`tree_parts_b.WIRE_*`, `stub`; check `checks/wire_route.py`; hand-off
  `fixes/wire_route_r1.py`). Reprint the cradle and print the stub (`out/print-pan/plate_wire_route_r1.3mf`).
  The servo's lead and plug stay coiled in the ball, and Dupont jumpers run down. Open: the 0.24 running
  gap; jumper length (~24 cm to the base bottom, so get 40 cm).
- **Pan coil set 4 = wire route round 2 (2026-10-02):** the wires' own lane under the ribbon (9 mm gap,
  shelf, drum core hole, exit boss at −145°; `pan_coil_b.LANE_*` etc., `fixes/wire_route_r2.py`, check
  `checks/wire_route.py` round 2). Reprint the base and drum (`plate_pan_coil_set4.3mf`). Set 3's are in
  `superseded - set 3 before wire lane/`. Open: lane height 3.5 and 74 mm of wire in it are guesses.
- **Rev 2 mesh faults:** his ball_plus export has 11 self-intersections (X 19–22, Z ~36, above the
  lower tube) and non-manifold edges at the back (X −21.3, Y 19.4). They ship as exported; ask him to
  clean them in Fusion on the next export.
