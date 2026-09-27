# FPVTank_Prototype: the physical design of the Scorpion robot

Fusion exports, fixes, fit checks and print sets. The robot's code is `../FPVTank_Control`, which the
Pi pulls, so no CAD goes there. This repo is never deployed, so it may hold binaries; only regenerable
output (`**/out/`, `reference/downloads/`) stays untracked. Layout and commands: `README.md`.

## Zach

- Talk to him in the second person. Documents and commit messages stay third person.
- He isn't an engineer. Use plain words, and define a term inline the first time it comes up ("spline,
  the ridged metal stub the horn grips"). Pictures help. Be brief: lead with the finding or the action.
- It's a prototype phase. Find failures; don't chase precision.
- He designs in **Fusion now; his model is the source of truth.** Blender is only for mesh surgery on
  downloaded STLs.
- Trust his caliper numbers over anything read off a photo. Tell his measurements apart from offhand
  guesses, and don't build on the guesses.
- "Ish" means fill in the exact value yourself: measure the feature, pick the number, and say what you
  measured.
- His tested horn-pocket rule is **zero offset**: subtract his real horn model as-is, and leave 1–2 mm
  of roof for the screw. Grip the arms, not the shaft. It applies to horn pockets only; a 21 mm slide
  needs 0.15 per side.
- He does booleans in Fusion himself. Give him the position, depth and orientation, or named tool
  bodies (Deliverables).
- He edits between sessions. Check file dates before trusting anything derived, and re-run the checks
  rather than trusting an earlier pass.

## Frame (head v2)

- X points toward the lens, Y along the tilt axis (+Y toward the post), Z up.
- The tilt axis is at X 0, Z 52 (`B.H` in the generator).
- Units are mm.

## Checking rules

- Every zero needs a negative control: the same check must read nonzero on the broken version.
- Before judging a revision, place parts where *his* geometry puts them: slice or ray every new
  feature first. Rev 1's first review got three verdicts wrong by assuming the old model.
- Check the hardware as well as the parts: screw heads, pins, the real servo and camera solids. The
  seam screws jammed because the pocket rule ignored the ball's curve under the head.
- Locate a small nonzero overlap before calling it anything. 3.8 mm³ dismissed as "skin" was the servo
  tabs hitting the seam posts.
- Use exact OCC booleans on his STLs (`tools/kit.py`), not voxels, for anything you ship.
- A cut must overrun the face it passes through. No coincident same-part faces.
- Run the mesh report (`export.health`) on every export. Run the needle repair (`export.tidy`) when
  his Fusion export carries degenerate triangles.

## Deliverables

Every hand-off has:
- print-oriented STLs in `out/print/` (halves seam face down, post flange down, pins flat);
- a 3MF plate;
- a Fusion STEP of named `ADD_*` / `CUT_*` tool bodies, in his coordinates;
- a picture sheet;
- a README.

Mark superseded files; don't silently replace them.

## History

- Never delete a reversed decision; mark it superseded (`docs/decisions.md`, `archive/`).
- Lessons go in `docs/lessons/`. `head-v2/NOTES.md` is the live state: drained, not grown.
- Commit only when asked. Never push without asking.

## Where things are

- `tools/config.py` holds every path. The generator is in `head-v2/generator/` (moved from Control in
  phase B, 2026-09-27). No CAD goes back into Control.
- Run with `python` (3.10; it has cadquery). `python head-v2/fixes/build_all.py` regenerates the
  hand-off; `python head-v2/checks/regression.py` must reproduce its table.
- Reviewing a new Fusion revision: the `review-revision` skill.
