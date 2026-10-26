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
  - Both verified 2026-09-26, and again on 2026-09-27 after the repos moved off the cloud-synced folder to
    `Documents\GitHub`.
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

- **Pan coil set 11 (2026-10-12, sliced, not printed): the shelf ring back in the base** (`pan_coil_b.SHELF_MERGED`,
  `docs/decisions.md`). Zach: the drop-in ring could fall out upside down and needn't be a part now the wires go down the
  middle; close the old exit hole. The empty lane fills to the ribbon's floor, the cup wall is built on, the rib, boss and
  hole go; the 6704 drops through a 27.5 hole. Only the base reprints: `out/print-pan/plate_pan_coil_set11_base.3mf`,
  G-code `pan_set11_base_orca_PLA_1h21m` (supports on). Open: "leave the well off for this one" read as leaving the
  loose ring out; the ribbon's cup wall is kept.

- **Pan coil set 10 (2026-10-11, built; the pan turns its full sweep, 2026-10-12): the servo wires straight down the pan axis**
  (`pan_coil_b.HOLLOW_AXIS`, `docs/decisions.md`). Set 9 meshed only moved over 500..800 us; the bare servo turned fully;
  Zach found the wires squashed in the lane. Now a 6704 replaces the 688, the barrel is 19.9 and hollow (6 mm wire hole),
  and the small gear (a solid hub on top) bolts on with 3 × M3 × 16, heads under it in an 18.7 mm floor-plate hole. Checks
  (`pan_coil_b_check.py`); the fit view shows it. Reprint: drum, base, small gear, floor plate. Guesses: the 6704's rings
  (lip from r 12.4), seat 27.1 / barrel 19.9, the 5.5 mm hole, the hub 0.4 under the inner ring, button heads on the
  M3 × 16. **His M3 × 16 turned out to be black nylon (from a standoff kit; one bent under his finger).** For
  testing: cut the three pilots with a steel M3 × 12 first, then the nylon ones; for keeps he needs steel M3 × 16.
  Both plates printed 2026-10-11 and built; meshed, the pan turns its full 500..2500 us (Zach's video, 2026-10-12). Set
  11 replaces the base. `checks/wire_route.py` still checks set 8's lane route.

- **Pan coil set 9 (2026-10-10, built, not printed): the pan servo couldn't turn the drum** (first bench run,
  FPVTank_Control `docs/bench/2026-10-10-v2-head-first-power.md`). The input gear carries the servo's double-arm horn
  in an exact pocket (`fixes/gear_horn_set9.py`, Arm02 in `generator/pan-coil-b/horn/`), 1.0 under the servo's block;
  the barrel runs in a 688 seated in the base (`pan_coil_b.BARREL_688`, `HORN_GEAR`). Hand-off `fixes/set9.py` +
  `pan_print_set.py` (`plate_pan_coil_set9.3mf`: base, drum, input gear, two small gears); fit view Version 24.
  Checks: `pan_coil_b_check.py` (`races_688`, `block_air`). Guesses: the horn's face 4.4 under the block (his 9.0 spline
  is the tilt servo's), 1.0 of air, the 688 seat 16.1 / barrel 7.9 / lip r 7.1, the 6.0 square at 0.05 / 0.10. Ask how
  it turns before touching the drag hunt: the drum was still "not bearing smooth" with the 6809ZZ in.
  Reprinted the same day (drum + 0.10 small gear + input gears with the pocket 0.10 / 0.15 and an open floor for the
  horn's own screw): the 0.05 gear tore the stub off; zero offset threw the horn out. Base (plate B, supports on) next.

- **+Y hub as a sleeve (2026-10-03, printed, the press held):** the hub is off ball_plus (a 2 mm keyed socket
  instead) and is its own part, so the ball drops in without bending the +Y arm. `fixes/plus_sleeve.py`
  (on `out/rev2/ball_plus_rev2.brep`), check `checks/plus_sleeve_fit.py`, picture `plus_sleeve_figure.py`,
  view `plus_sleeve_view.py` (https://claude.ai/artifact/35Gmu4fdxbpRQeN6P8zBok). Print
  `out/print-rev2/plate_plus_sleeve.3mf`; Fusion tool body `CUT_plus_hub`. `ball_plus_rev2.stl` is
  superseded (`export_campost_rev2.py` still writes it). The 6704 presses onto the sleeve
  (two to try: 20.0 and 20.1) up to a lip, so it turns. Guesses: the press, socket depth 1.5 (0.69 of plate left at the bottom),
  key flat X 9.0, lip r 11.0, servo height from post v3. Not fixed: the collar's shoulder rubs the 6704's inner ring; the
  ribbon track's back lip overhangs the ball ~1 mm.
- **Final material is ASA; every fit so far was tested in PLA** (`docs/decisions.md`, 2026-10-02).
  Before the final ASA print, print an ASA test piece of the horn pocket and the 21 mm slide. The sim's
  masses are still PETG-GF (1.35 g/cm³); ASA is 1.07. Update them when Zach asks.
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
  fit before changing any of it. Open: the ribbon thickness is uncalipered; where the
  base screws to the tank is undecided (the old deck screws sat under the bearing, brief §6.3).
- **Cradle plug chute (2026-09-27, later):** the cradle has a 4 mm groove plus a straight plug chute
  (`tree_parts_b.CHUTE_T`, `chute()`; hand-off `fixes/cradle_chute.py`; check `checks/plug_passage.py`).
  The old groove never opened into the track. Zach's servo connector: **14 long × 8 wide** (calipered);
  thickness not measured. Set 3's drum passes it (side slot top Z 2.0); set 2's jams at 3.0 thick.
- **Pan coil set 3 (2026-09-28; tab block 2026-09-29):** built on Zach's MG90S model
  (`generator/pan-coil-b/MG90S.3MF`, check `checks/pan_servo_fit.py`), plus a slide-in tab block under the
  servo's window-end tab, whose screw had nothing to bite (`pan_coil_b.tab_block`). Reprint base and
  drum, print the tab block. Open: he doesn't have the tilt axis's 2 × 6704 and asked
  to use a 6809 (he has 10; **wrong:** on 2026-10-04 he said he has no 6809 at all, so the pan drum has run
  with no bearing in its seat. He is ordering 6809ZZ). Where it goes wasn't settled: he mentioned "under the coil on the post, size
  the post to match", then dismissed the clarifying question.
- **Servo wire route, round 1 (2026-10-02):** the stub replaces the −Y axle and cap; a 5 mm wire hole runs
  down the cradle's −Y wall (`tree_parts_b.WIRE_*`, `stub`; check `checks/wire_route.py`; hand-off
  `fixes/wire_route_r1.py`). The cradle is printed (2026-10-02) and the wires thread it well; the stub and the cup aren't printed yet.
  Since then its ridge is blended into the wall (`CONDUIT_K` 6, `fixes/cradle_blend.py`), looks only.
  The servo's lead and plug stay coiled in the ball, and Dupont jumpers run down. The −Y 6704 sits in a
  cup in his ball_minus (`fixes/ball_minus_cup.py`; print `ball_minus_cup.stl`, also on the round 1
  plate). The collar is a plain bore. Open: the cup's 27.1 press fit; jumper length (~24 cm to the base
  bottom, so get 40 cm).
- **Pan coil set 7 (2026-10-04, printing the same day) = set 6 + a new base and a drop-in shelf ring:** Orca's supports in
  the wire lane, under the shelf, couldn't be got out. The shelf and the ribbon cup's wall are `shelf_ring` now
  (`pan_coil_b.INSERT`, `RING_*`, `SKIRT_*`, `KEY_*`, `SLIT_W`, `teardrop_hole`); the deck ring stands on a skirt and
  a 30° cone; the ribbon leaves by a 2 mm slit; a rib on the ledge keys the ring; the exit hole has a pointed top. Nothing sits under
  the drum's hub any more (it sat on the deck ring at r 19.5-20.4). `plate_pan_coil_set7.3mf` (base + ring) went
  on the printer before the 6809ZZ arrived, so the bearing's seat (58.1) is still untried. `fixes/base_shelf_set7.py`;
  checks `pan_coil_b_check.py` (ring pairs, ring sweep, `hub_face`), `wire_route.py` rows 4-6 (with the ring),
  `plug_passage.py` (base + ring). Guesses: the ring's 0.15 slide, the 1.5 ledge, the key's 0.15 a side, the
  0.8 shelf as its own part, gravity holding it, the 2 mm slit. Left: supports under the gear bay's ceiling and
  round the journal (out from below) and over the servo pocket (out through its window).
- **Pan coil set 6 (2026-10-03, printed 2026-10-04) = set 5 + a coned drum bore + the gear on the spline** (its
  input gear superseded by set 9: the press bore wore smooth and the screw pulled the gear into the servo): Zach
  assembled set 5 (base, drum, head set). The drum's flat bore floor printed over supports he couldn't get out,
  so it is a cone 30° off vertical with the wire hole at its point, and the notch floor is 30° too
  (`pan_coil_b.CONE_*`, `DRUM_WIRE_PTS`, `NOTCH_FLOOR_DEG`). No screw reached the servo through the input gear:
  the placeholder horn pocket's roof stopped the shaft. The spline now presses into the gear like post v3
  (`SPL_*`; it prints bottom face down, `pan_coil_b_print.WAY_UP`). Print `plate_pan_coil_set6.3mf` (drum +
  input gear), supports off; set 5's base is current. `fixes/drum_cone_set6.py`, checks `wire_route.py` row 7,
  `pan_servo_fit.py`, `pan_coil_b_check.py`. Guesses: the hole's new path, the gear's 4.44 bore and 1.5 lip,
  the servo screw's ~4 mm. The ribbon below the old floor isn't modelled (row 7 draws it turning to +X).
  2026-10-04: the input gear works (the press is nice and tight, the screw catches). The drum waits for the
  6809ZZ (due 2026-10-05). Next base: the wire lane's supports are trapped under the shelf (Orca, his settings);
  Zach wants the base support-free there.
- **Pan coil set 5 (2026-10-02) = set 4 + a drum notch and funnel:** the printed round 1 cradle lets the
  wires out in front of the ribbon and the drum's hole is behind it. The fix is a bore-wall notch on −Y and a
  funnel on the mouth (`pan_coil_b.NOTCH_*`, `FUNNEL_*`; `fixes/drum_notch_set5.py`; check
  `checks/wire_route.py` row 7). Its base is printed and current; its drum and funnel are superseded by set
  6. Threading now happens before the cradle is bolted (README).
  The cradle's groove lets the ribbon sit 3 mm off centre: pushed toward −Y, it leaves a 2.4 mm bundle
  at the cradle's mouth, so thread with the ribbon held toward +Y (the drum is never the limit).
  Open: the lane's 3.5 height and the 74 mm of wire in it are guesses, as are the notch and funnel
  sizes; which side of the ribbon the wires come out on (Zach is testing); the ribbon's fold into the
  slot isn't modelled. The servo's own wires depin, so they may replace the jumpers; the lead length
  is unmeasured.
- **Rev 2 mesh faults:** his ball_plus export has 11 self-intersections (X 19–22, Z ~36, above the
  lower tube) and non-manifold edges at the back (X −21.3, Y 19.4). They ship as exported; ask him to
  clean them in Fusion on the next export.
