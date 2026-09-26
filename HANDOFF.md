# Handoff — clean up FPVTank_Prototype and get it ready to take the CAD work

> **Status, 2026-09-26: phase A is done.** It was committed on branch `reorg` and merged into
> `main`. Tasks 1–10 are complete.
> - `head-v2/fixes/build_all.py` regenerates the Downloads print set: every STL byte for byte, the
>   STEP and 3MF differing only in timestamps.
> - `head-v2/checks/regression.py` reproduces all 14 rows of the table below.
> - Zach's answers:
>   - Pan-tilt goes to `archive/pan-tilt-2026-08/`. The files are from August 2026, not 2025.
>   - Pi 5: both STLs and the Printables page are tracked; the STEP is untracked.
>   - Pin size: not tested yet.
>   - One commit at the end, after he reviews.
> - Open questions 2 and 5 are carried in `MOVE-PLAN.md`. The next step is phase B, per `MOVE-PLAN.md`.

Written 2026-09-26 by the session that did the v2-head ball fixes (snap pins, post v3), working in
`FPVTank_Control`. For the next session, which runs **in this folder**. Zach will start you with
"read HANDOFF.md".

## Why this exists

`FPVTank_Control` is the robot's code, and the Pi `git pull`s the whole repo during development.
Its `docs/chassis/` holds **110 MB of CAD** (the robot code is under 1 MB; the YOLO models are 26 MB
and do belong there), and every regenerated mesh rides along to the Pi. All physical-design work
moves **here**. Control keeps code plus the robot docs it needs (`HARDWARE.md` pin map, `PI.md`,
bench logs, specs and plans). This repo is never deployed, so it may hold binaries; only regenerable
outputs stay untracked.

**Your job is phase A: clean this repo and build the structure. Do not move anything out of
Control yet.** Phase B (copy from Control, verify, delete there) is a later session, once
Zach's in-progress change in Control has landed.

## Hard boundaries

- **Do not modify `FPVTank_Control`.** Zach has a change in progress there. Reading it is fine.
- **Do not delete or rename `..\FPVTank_Prototype`** (the old local folder, *not* a git repo). It
  holds the only copy of some files (see below). Copy from it; ask before removing anything.
- **Git:** work on a branch (suggest `reorg`), commit only when Zach says so, never push without
  asking. Verify every commit landed (`git log --oneline -1`).
- Downloads and the old session's scratchpad are read/copy only.

## Where you are

- This folder: `C:\Users\<usr>\OneDrive\Documents\GitHub\FPVTank_Prototype-github`, a fresh clone
  of `https://github.com/ZacharyShaver/FPVTank_Prototype` (**private**, branch `main` only).
- History: 5 commits, 2024-10-14 → 2024-11-03 ("Finished Project"). It is the **first tank**:
  - `3D - Model Tank/`: the FPV-Rover V2.0 download (28 STLs and 2 build-guide PDFs).
  - `FPVT Controller/`: PC side, a tkinter WASD window that sends keypresses over Wi-Fi sockets.
  - `FPVT Robot/`: a CircuitPython `code.py` (Wi-Fi board plus Adafruit MotorKit) and Arduino
    motor-test sketches.
  - Junk: `.DS_Store` (x2) and `FPVT Controller/__pycache__/*.pyc`, committed from a Mac.
- **One file cannot exist on Windows:**
  `3D - Model Tank/3D Printed FPV Rover V2.0 : 11 Steps (with Pictures) - Instructables.pdf`
  (the colon). Its blob is `32e5f3c79b92d9afc0d911825e66198d82672f74`, byte-identical to the
  local copy saved as `..._ 11 Steps...`. To get a checkout at all, this clone has a **sparse
  checkout** that skips it (`/*`, `!/3D - Model Tank/*Instructables.pdf`), and the index was
  rebuilt with `git add -A`. So `git status` shows exactly one line: that PDF as deleted. **Do not
  commit that as-is**; task 1 turns it into a proper rename.

### The old local folder `..\FPVTank_Prototype` compared with this repo (hash-checked)

- `Version 1/`: identical to this repo, except the two 41-tooth bevel gears
  (`big-bevel-gear-41-v13.stl`, `small-bevel-gear-41-v11.stl`) sit in an
  `alternitive wheel mounts/` subfolder.
- `Version 2/`: the same STLs again, plus **`3D - Model Tank/Pan-tilt/`** with 8 STLs:
  `Body15`, `Body31`, `Body55`, `Body56`, `Pan_Tilt_pan_cap`, `pan-tilt-pan-v3`,
  `pan-tilt-x-y-v2`, `tank body section`. **This is the only copy anywhere** (not on GitHub, not in
  Control). Ask Zach what it is before deciding where it goes.
- `Current/raspberry-pi-5-model_files/`: a downloaded Pi 5 model. STEP 31 MB, two STLs 3.3 MB and
  5.9 MB, a PDF, plus a 7 MB zip of the same thing.
- Nothing local was ever pushed.

## Tasks, in order

1. **Fix the filename with git plumbing** (the file can't be checked out, so `git mv` won't work):
   ```bash
   git update-index --add --cacheinfo 100644,32e5f3c79b92d9afc0d911825e66198d82672f74,"reference/fpv-rover-v2/FPV Rover V2.0 - Instructables guide.pdf"
   ```
   The old path is already absent from the index. Commit it (with Zach's OK) as a rename. Then run
   `git sparse-checkout disable` and check that `git status` is clean and the PDF is on disk.
   Either put it straight into its final folder as above, or rename it in place first. One commit
   is fine.
2. **Remove the junk** (`git rm` the `.DS_Store` files and `__pycache__`) and add `.gitignore`:
   ```
   .DS_Store
   __pycache__/
   *.pyc
   **/out/
   reference/downloads/
   _incoming/
   ```
3. **Reorganise what's already here** with `git mv`, so history follows the files:
   - `3D - Model Tank/*` → `reference/fpv-rover-v2/`, with the 41-tooth gears in
     `reference/fpv-rover-v2/alternate-wheel-mounts/`.
   - `FPVT Controller/` → `archive/v1-2024/controller/`
   - `FPVT Robot/` → `archive/v1-2024/robot/`
4. **Bring in what exists only locally:**
   - `Pan-tilt/`: ask Zach first. Likely an early pan-tilt head; a candidate home is
     `archive/pan-tilt-2025/`.
   - Pi 5 model. Recommend tracking the plain STL in `reference/raspberry-pi-5/` (a fit-check
     dummy) and keeping the 31 MB STEP in untracked `reference/downloads/`, with a `SOURCE.md` saying
     where to re-download it. Drop the zip, which duplicates the rest. Zach's call.
5. **Build the skeleton** (next section). Empty folders get a short README saying what goes there.
6. **Write `CLAUDE.md`.** Content is outlined further down. It is the rules; keep it tight.
7. **Write the skill** `.claude/skills/review-revision/SKILL.md`. Outline further down. It is the
   step-by-step.
8. **Turn the old session's scripts into `tools/`.** They're in `_incoming/scripts-2026-09-25/`
   (copied from a temp folder that will be cleared). Details below.
9. **Write `MOVE-PLAN.md`** for phase B: the path mapping, order and verification (below).
   Don't execute it.
10. **Write `README.md`**: what this repo is, the layout, where the current print set lives, and
    how to run the tools.

## Target layout

```
FPVTank_Prototype/
├── CLAUDE.md                 rules: frames, fits, how every change is checked, how to talk to Zach
├── README.md
├── HANDOFF.md / MOVE-PLAN.md (fold into docs/ once done)
├── .gitignore
├── .claude/skills/review-revision/SKILL.md
├── tools/                    shared Python: STL→solid, booleans, fit checks, renders, print/3MF export
├── reference/                measured or downloaded hardware
│   ├── fpv-rover-v2/         the original download (from this repo's history)
│   ├── raspberry-pi-5/
│   ├── solids/               servo (turned), camera, 6704 bearing, screw heads: the fit-check dummies
│   └── downloads/            (untracked) big third-party files
├── head-v2/
│   ├── NOTES.md              live state: what's printed, what's open (drained, not grown)
│   ├── fusion/rev1-2026-09-24/   Zach's Fusion exports (in _incoming/zach-fusion-rev1-2026-09-24/)
│   ├── generator/            ← phase B: Control's docs/chassis/head-v2/generators + its docs
│   ├── fixes/                scripts that turn a Fusion rev into its fixed version
│   ├── checks/               fit checks, each with its negative control
│   └── out/                  (untracked) print STLs, 3MF, pictures
├── chassis-v1/               ← phase B: Control's docs/chassis/{parts,img,*.md}
├── archive/                  v1-2024 code, anything superseded that's worth keeping
└── docs/
    ├── decisions.md          why each design went the way it did
    └── lessons/              ← phase B: the three CAD lessons from Control's docs/lessons
```

## tools/: what the scripts are

The scripts in `_incoming/scripts-2026-09-25/` ran from the old session's scratchpad. They hardcode:
- `GEN` = Control's `docs/chassis/head-v2/generators`, imported as `tree_parts as A` and
  `tree_parts_b as B` for constants, the nest SDF `B.fork`, and the mesh report `tree_parts.report`;
- `DL` = `C:\Users\<usr>\Downloads` for Zach's STLs;
- relative `out/` and `out_snap/` folders.

Make those a single config. Until phase B, point `GEN` at Control; after it, at `head-v2/generator/`.

- **Library (goes in `tools/`):**
  - `occ_load.py`: sew STL → OCC solid, then unify.
  - `kit.py`: primitives, fuse/cut/common, `overlap()`, `moved()`, the turned-servo solid and
    `servo_trimmed`, the camera loader, and the parts cache.
  - `vox.py` + `probe.py`: STL load, ray hits.
  - `slices.py`: planar slices.
  - `zr.py`: z-buffer renderer.
  - `lens_nest.py`: surface sampling, tilt, view cone.
  - `export.py`: STL write, `health()`, and `tidy()` (the needle-triangle repair: merge 0.001,
    drop null faces).
- **Fixes (to `head-v2/fixes/`):**
  - `snap.py`: pin and socket geometry, including the stop nose.
  - `build_snap.py`: rev 2 halves.
  - `post3.py`: post v3.
  - `print_export.py` + `plate3mf.py`: the print set and the hand-written 3MF.
  - `*_step.py`: named tool bodies for Fusion.
  - `build.py` is rev 1 (screws). Superseded: keep it in history, don't use it.
- **Checks (to `head-v2/checks/`):**
  - `check_snap.py`
  - `freeplay.py`
  - `reach_check.py`
  - `ball_nest3.py`
  - `snap_surface.py`
  - `reeval.py`
- **Pictures:** `figure_snap.py`, `figure_stop.py`, `figure_post.py`.
- **Everything else** (`holes*`, `where*`, `faults`, `repair_try*`, …) was one-off probing. Leave
  it out or put it in `archive/`.

Done when the checks run from the repo and reproduce the regression numbers below.

## Regression numbers (phase B must reproduce these)

Rev 2 = Zach's Fusion rev 1 plus the fixes, with the board on the front of his wall (X 10.5) and the
servo case top on his plate at Y 21.2357.

| Check | Fixed | Zach's original (negative control) |
|---|---|---|
| camera vs ball_plus | 0.00 mm³ | 39.50 |
| camera vs servo (tabs snipped / as bought) | 0.00 | 8.65 |
| servo seated vs ball_plus | 0.00 | 7.36 |
| servo sliding in, worst step | 0.00 | 8.61 |
| ball halves vs each other | 0.00 | 0.00 |
| 3 pins seated, per half | 0.12 (designed preload) | — |
| wall round every pin socket | ≥ 1.0 mm | — |
| pin free play after the click | none | 0.75 mm (first pins) |
| ball vs nest, full tilt, deepest | 0.0000 | 0.0000 |
| lens vs nest, full tilt | 1.95 mm clear | — |
| post: spline in post / gap to boss | 3.50 / 0.50 (screw tight, ball centred) | 2.13 / 1.87 (pressed, ball 0.6 away) |
| every print mesh | watertight, manifold, 1 body, 0 self-int | ball_plus: 5 self-int + non-manifold |

The nest's SDF has zero-thickness sheets at |Y| 25.0 and 26.5 inside the hub bore. They read as
"touching" and are not material; exclude them as `ball_nest3.py` does. A task to fix this in the
generator was started from Control.

## CLAUDE.md: what goes in it

**Zach.** Speak to him in the second person. He isn't an engineer: plain words, define terms the
first time, pictures help, be brief. It's a prototype phase: find failures, don't chase precision.
He designs in **Fusion now; his model is the source of truth**. Trust his caliper numbers over
anything read off a photo. "Ish" means fill in the exact value yourself. His tested horn-pocket
rule is zero offset, and it applies to horn pockets only (a 21 mm slide needs 0.15 per side).

**Frame (head v2).**
- X points toward the lens, Y along the tilt axis (+Y toward the post), Z up.
- The tilt axis is at X 0, Z 52 (H).
- Units are mm.

**Checking rules.**
- Every zero needs a negative control: the same check must read nonzero on the broken version.
- Before judging a revision, place parts where *his* geometry puts them: slice or ray every new
  feature first. Rev 1's first review got three verdicts wrong by assuming the old model.
- Check the hardware as well as the parts: screw heads, pins, the real servo and camera solids.
  The seam screws jammed because the pocket rule ignored the ball's curve under the head.
- Locate a small nonzero overlap before calling it anything. 3.8 mm³ dismissed as "skin" was the
  servo tabs hitting the seam posts.
- Use exact OCC booleans on his STLs, not voxels, for anything you ship.
- A cut must overrun the face it passes through. No coincident same-part faces.
- Run the mesh report on every export. Run needle repair when his Fusion export carries
  degenerate triangles.

**Deliverables.** Every hand-off has:
- print-oriented STLs in `out/print/` (halves seam face down, post flange down, pins flat);
- a 3MF plate;
- a Fusion STEP of named `ADD_*` / `CUT_*` tool bodies, in his coordinates;
- a picture sheet;
- a README.

Mark superseded files; don't silently replace them.

**History.** Never delete a reversed decision; mark it superseded. Lessons go in `docs/lessons/`.
`NOTES.md` is drained, not grown. Commit only when asked.

## The skill: review-revision

The loop that worked:
1. Load his STLs as OCC solids and note the mesh faults.
2. Slice and ray every changed area. Work out his intended assembly: stops, holes, bores, where the
   servo and camera sit.
3. Run the checks at that assembly: overlaps, free travel, sliding paths, lens and ball vs nest over
   tilt, hardware.
4. Report in plain words, owning any earlier mistake, with pictures.
5. Fix with named primitive tool bodies.
6. Re-check with negative controls.
7. Export the deliverables.
8. Send files and a short summary; update `NOTES.md`.

## Phase B: path mapping (put this in MOVE-PLAN.md)

| From `FPVTank_Control` | To here |
|---|---|
| `docs/chassis/parts/`, `img/`, `stl-parts.md`, `used-parts.md`, `body-revision-brief.md`, `render_stl_views.py` | `chassis-v1/` |
| `docs/chassis/head-v2/generators/` | `head-v2/generator/` |
| `docs/chassis/head-v2/{tree-parts-b,camera,pan-coil-b,…}` and the `*.md` briefs | `head-v2/generator/` (or `head-v2/history/` for the older forks) |
| `docs/lessons/2026-09-18-flat-cable-and-driver-access.md`, `2026-09-19-coincident-faces-and-insertion.md`, `2026-09-19-surface-sampling-is-a-vacuous-check.md` | `docs/lessons/` |
| `Downloads/head-v2-snap/` (current print set) and `head-v2-fixes/` (superseded) | regenerated into `head-v2/out/`; keep their READMEs in `head-v2/` |

Order:
1. Wait until Zach's Control change and the two open CAD tasks (nest sheets; seam screw heads)
   have landed.
2. Copy the files here, with fresh history. Control keeps the old history as the record.
3. Run the regression table.
4. In Control: remove `docs/chassis/`, leave a one-line pointer, fix the references in
   `CLAUDE.md`, `HARDWARE.md` and `ROADMAP.md`, and add a rule: "no CAD files here".
5. Carry the memories over, as below.

**Memories** live in
`C:\Users\<usr>\.claude\projects\C--Users-<usr>-OneDrive-Documents-GitHub-FPVTank-Control\memory\`.
- CAD ones go into this repo's `CLAUDE.md`: `servo-horn-fit-zero-offset`,
  `review-revisions-on-their-own-terms`, `head-v2-*`, `v2-head-cad-parts`,
  `zach-can-do-cad-edits`, `zach-edits-generators-between-sessions`,
  `arm-concept-long-forearm-pushrod`.
- The personal ones go into Zach's global `~/.claude/CLAUDE.md`, so every repo gets them:
  `zach-is-not-an-engineer`, `talk-to-zach-not-about-him`, `be-brief-at-the-bench`,
  `ish-means-fill-in-the-blanks`, `separate-measurements-from-comfort-judgements`.
- Ask before writing to the global file.

## Questions for Zach

1. What is `Version 2/.../Pan-tilt/`, and where should it live?
2. The chassis part edits live in **Blender** (per Control's `used-parts.md`) and were never
   exported. Should `chassis-v1/` get the as-printed versions?
3. Pi 5 model: track the 31 MB STEP, or keep it untracked?
4. Keep the reorg on the `reorg` branch until phase B, or merge to `main` now?
5. At the end, may this folder become `FPVTank_Prototype`, with the old local folder archived?
   Control's docs point at `../FPVTank_Prototype`.
6. Which pin size (soft, medium or firm) did he settle on? The 3MF plate has 4 medium.

## Paths

- **This repo:** `C:\Users\<usr>\OneDrive\Documents\GitHub\FPVTank_Prototype-github`
- **Old local folder:** `C:\Users\<usr>\OneDrive\Documents\GitHub\FPVTank_Prototype` (not git)
- **Current print set:** `C:\Users\<usr>\Downloads\head-v2-snap\` (README.txt is the index)
- **Staging here:** `_incoming\scripts-2026-09-25\` (52 scripts) and
  `_incoming\zach-fusion-rev1-2026-09-24\` (his 3 Fusion STLs: `BODY_NUMBA1` = ball_plus,
  `ball_minus_revised`, `ball_servo_post_revised`)
