---
name: review-revision
description: Review a Fusion revision Zach sends (STL or STEP exports of the head-v2 ball, post or any printed part) — load it as exact solids, work out his intended assembly, run the fit checks with negative controls, fix with named tool bodies, and export the hand-off. Use whenever new or revised CAD exports from Zach arrive.
---

# Review a revision

His model is the source of truth. Work out what he built on its own terms before judging any of it.
Run everything with `python` (3.10, the one with cadquery). Paths live in `tools/config.py`.

1. **Load, and note the mesh faults.**
   - Copy his exports as sent into `head-v2/fusion/rev<N>-<yyyy-mm-dd>/`, with a README mapping each
     file to its part. Point `config.FUSION` and `config.ZACH` at it.
   - `python tools/occ_load.py` sews each part into an exact solid and prints free edges, validity and
     volume. `python head-v2/checks/mesh_report.py` prints self-intersections, non-manifold edges and
     bodies.
   - Write the faults down. Degenerate needle triangles get `export.tidy` on export.
2. **Read his geometry before judging it.**
   - Slice and ray every changed area: `tools/slices.py` (`draw`) and `tools/probe.py`
     (`show(tag, mesh('ball_plus'), point, axis)`). Find every stop, hole, bore and plate he added.
   - Work out his intended assembly from that: where the servo case top lands, which wall the camera
     board sits on, and what holds each part. Write it down with the numbers you measured.
   - Run `head-v2/checks/reeval.py` at those positions.
3. **Check at his assembly.**
   - Overlaps: camera, servo (`kit.servo`, and `kit.servo_trimmed` for the tabs he snips) and halves.
   - Free travel, and the servo's sliding path in.
   - Ball and lens against the nest over the whole tilt: `ball_nest.py`, `lens_clear.py`.
   - The hardware: screw heads, pins, the real servo and camera solids.
   - Every zero gets its negative control. Locate any small nonzero overlap before you name it.
4. **Report to Zach.** Use plain words, second person, brief, with a picture (a slice or a render
   from `tools/zr.py`). If an earlier verdict was wrong, say so first.
5. **Fix with named primitive tool bodies**: `ADD_*` joins and `CUT_*` cuts, in his coordinates, in a
   new script under `head-v2/fixes/`. Start from the closest one (`build_snap.py`, `post3.py`).
   - A cut overruns the face it passes through. No coincident same-part faces.
   - Keep each body something he could redraw in Fusion.
6. **Re-check with negative controls.** Run every check on the fixed parts and the same check on his
   originals. Add the new rows to `head-v2/checks/regression.py`.
7. **Export the deliverables** into `head-v2/out/`, following `head-v2/fixes/build_all.py`:
   - print-oriented STLs in `out/print/`;
   - the 3MF plate;
   - the `ADD_*` / `CUT_*` STEP for Fusion;
   - a picture sheet;
   - a README.

   Run the mesh report on every file. Mark anything superseded; never silently replace it.
8. **Hand off.** Send the files and a short summary. Drain `head-v2/NOTES.md` (remove what's done, add
   what's open). Log decisions in `docs/decisions.md` and lessons in `docs/lessons/`. Commit only when
   Zach says so.
