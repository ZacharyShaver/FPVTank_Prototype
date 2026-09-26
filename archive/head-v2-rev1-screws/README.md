# Head v2 ball, rev 1 (seam screws): SUPERSEDED

These are the first fixes to Zach's Fusion rev 1 (2026-09-25):
- a rail notch for the IR-CUT holder;
- a servo-slot shave;
- two edge seals;
- a front M3 seam-screw post.

Rev 2 (`head-v2/fixes/`) replaced them the same day. The seam screws' heads stood about 2 mm proud of
the ball, with the nest only 1.5 mm away, so they jammed the ball. Rev 2 kept the notch, the shave and
the seals (`build_snap.py`). Rev 1's print set was `Downloads/head-v2-fixes/`.

The scripts are kept unmodified from the old session's scratchpad, as the record. They won't run as
they are: they expect `kit.py` and `probe.py` beside them, and Zach's files in Downloads. Don't use them.

- `build.py` builds the rev 1 halves.
- `check.py` runs the checks with their negative controls.
- `export.py` writes the STLs and the STEP. It also holds the library functions, which now live in
  `tools/export.py`.
- `figure.py` draws the picture sheet.
