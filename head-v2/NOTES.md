# head-v2: live state

Drained, not grown: when an item is done, take it out. Its record goes to `docs/decisions.md` or git.
As of 2026-09-26.

## Current

- Ball rev 2 = Zach's Fusion rev 1 (`fusion/rev1-2026-09-24/`) + snap pins + post v3.
- The print set he has is `Downloads/head-v2-snap/`; its `README.txt` is the index (what to print
  first, assembly).
  - `python head-v2/fixes/build_all.py` regenerates it into `out/`. Every STL is byte-identical to
    that set; the STEP and 3MF differ only in timestamps.
  - `python head-v2/checks/regression.py` reproduces its checks.
  - Both verified 2026-09-26.
- Superseded, don't print: `Downloads/head-v2-fixes/` (rev 1, screws) and the pins in
  `head-v2-snap/superseded - first pins, no stop/`.
- Before changing the ball, the post or the seam, ask Zach which files he printed.

## Open

- **Pin size:** not picked yet (2026-09-26). Print two test blocks and one stop pin of each size. The
  3MF plate carries 4 medium; if he picks soft or firm, change `PIN` in `fixes/plate3mf.py`.
- **Nest SDF sheets:** the nest's SDF has zero-thickness sheets at |Y| 25.0 and 26.5 in the hub bore.
  They read as "touching" but aren't material. `lens_nest.nest_sweep` steps around the 26.5 one only.
  So `checks/ball_nest.py` reports ball_plus's nearest approach as 0.10 mm: that is its hub beside the
  25.0 sheet (Y 25.08, 8.9 from the tilt axis), not the nest. "Deepest" isn't affected. A fix in the
  generator was started from Control.
- **Seam screw heads in the generator:** `tree_parts_b.py` still has the screw-pocket bug. A task was
  started from Control.
- **The generator doesn't have Zach's revision.** Porting it was offered and hasn't been answered.
- **Phase B:** move the generator and the chassis files here (`MOVE-PLAN.md`).
