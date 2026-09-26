# Phase B: move the CAD out of FPVTank_Control

Written 2026-09-26, when phase A (this repo's layout, tools and rules) was done. **Not started. Don't
run it until the preconditions hold.**

Why: Control's `docs/chassis/` is 115 MB of tracked CAD in 196 files, and the Pi `git pull`s all of it.
After phase B, Control keeps its code and the robot docs it needs, and the CAD lives here.

## Preconditions

1. Zach's in-progress change in Control has landed.
2. The two open CAD tasks started from Control have landed:
   - the nest SDF's zero-thickness sheets (at |Y| 25.0 and 26.5, in the hub bore);
   - the seam screw heads in the generator.
3. ~~The `reorg` work here is committed and merged to `main`.~~ Done 2026-09-26.

## Path mapping

Move Control's `head-v2/` tree **whole** into `head-v2/generator/`. The generators find their output
folders and the camera by relative paths (`generators/../tree-parts-b`, `generators/../camera`).
Moving the tree as one keeps those paths working without code edits.

| From `FPVTank_Control` | To here | MB | Notes |
|---|---|---|---|
| `docs/chassis/head-v2/generators/` | `head-v2/generator/generators/` | 0.3 | skip `__pycache__/` |
| `docs/chassis/head-v2/{tree-parts-b, camera, pan-coil-b}/` | `head-v2/generator/` (same names) | 42 | variant B, the live one, and what it reads |
| `docs/chassis/head-v2/{tree-parts, tree-hood, pan-coil, concept, test-print-2, tree-arm-test, coil-test}/` | `head-v2/generator/` (same names) | 49 | the older forks (1) |
| `docs/chassis/head-v2/{ball-head-validation-handoff, pan-coil-360-brief}.md` | `head-v2/generator/` | | briefs |
| `docs/chassis/{parts/, img/, stl-parts.md, used-parts.md, body-revision-brief.md, render_stl_views.py}` | `chassis-v1/` | 23 | `parts/third-party/` keeps its LICENSE |
| `docs/lessons/2026-09-18-flat-cable-and-driver-access.md`, `2026-09-19-coincident-faces-and-insertion.md`, `2026-09-19-surface-sampling-is-a-vacuous-check.md` | `docs/lessons/` | | Control keeps its drivetrain lesson |
| `Downloads/head-v2-snap/` (current print set) and `Downloads/head-v2-fixes/` (superseded) | regenerate into `head-v2/out/`; copy their READMEs into `head-v2/` | | `build_all.py` already reproduces the snap set (2) |

(1) Moving the older forks to `head-v2/history/` would break their generators' relative paths. Do
that later, if at all.

(2) Every STL is byte-identical; the STEP and 3MF differ only in timestamps.

Don't copy what Control ignores: `docs/chassis/head-v2/*/print/` (the generator's print output) and
`__pycache__/`.

## Order

1. Wait for the preconditions.
2. Copy the files here with fresh history. Control keeps the old history as the record.
   - Check every copy against its source by hash.
   - Add `head-v2/generator/*/print/` to `.gitignore`, because the generator writes print STLs there.
3. Point `tools/config.py` at the copy: `GEN = head-v2/generator/generators` and
   `CAMERA = head-v2/generator/camera`.
4. Run the regression:
   - `python head-v2/fixes/build_all.py`, then `python head-v2/checks/regression.py`. It must print
     "all 14 rows reproduce".
   - Run the generator's own check from its new home: `build_b.py --solids --check`.
5. Only now, in Control:
   - remove `docs/chassis/` and the three lessons;
   - leave a one-line pointer to this repo;
   - add the rule "no CAD files here";
   - fix every reference (next section).
6. Carry the memories over (below).
7. Fold `HANDOFF.md` and this file into `docs/`.

## References to fix in Control (step 5)

- `CLAUDE.md:19`: source STLs in `../FPVTank_Prototype`, parts vendored in `docs/chassis/parts/`.
- `HARDWARE.md`:
  - line 42;
  - line 115 (the body revision brief);
  - lines 164–169, the "Related repo" section, which lists `Version 1/3D - Model Tank/`,
    `Current/raspberry-pi-5-model_files/` and `Version 1/FPVT Controller|Robot/`;
  - lines 327 and 329.
- `ROADMAP.md:590–591`: the body revision brief and used parts.
- `.gitignore:26`: `docs/chassis/head-v2/*/print/`.
- In the moved files:
  - `stl-parts.md` and `used-parts.md` point at `../FPVTank_Prototype/Version 1/3D - Model Tank/`;
  - `body-revision-brief.md:88` points at `Current/raspberry-pi-5-model_files/`;
  - the lessons link into `docs/chassis/`.

The new homes in this repo:

| Old | New |
|---|---|
| `Version 1/3D - Model Tank/` | `reference/fpv-rover-v2/` |
| `Current/raspberry-pi-5-model_files/` | `reference/raspberry-pi-5/` |
| `Version 1/FPVT Controller/`, `Version 1/FPVT Robot/` | `archive/v1-2024/controller/`, `archive/v1-2024/robot/` |

## Memories

They live in `C:\Users\<usr>\.claude\projects\C--Users-<usr>-OneDrive-Documents-GitHub-FPVTank-Control\memory\`.

- **CAD memories** go into this repo: `servo-horn-fit-zero-offset`,
  `review-revisions-on-their-own-terms`, `head-v2-*`, `v2-head-cad-parts`, `zach-can-do-cad-edits`,
  `zach-edits-generators-between-sessions`, `arm-concept-long-forearm-pushrod`.
  - Their rules are already in `CLAUDE.md`, and their decisions in `docs/decisions.md`.
  - What's left is facts: the camera board details, the arm concept, where things live.
- **Personal memories** go into Zach's global `~/.claude/CLAUDE.md`, so every repo gets them:
  `zach-is-not-an-engineer`, `talk-to-zach-not-about-him`, `be-brief-at-the-bench`,
  `ish-means-fill-in-the-blanks`, `separate-measurements-from-comfort-judgements`.
  **Ask Zach before writing to the global file.**
- Then take the moved memories out of Control's `MEMORY.md` index.

## Open questions for Zach

- The chassis part edits live in Blender (per `used-parts.md`) and were never exported. Should
  `chassis-v1/` get the as-printed versions?
- When phase B is done, may this folder become `FPVTank_Prototype`, with the old local folder archived?
  Control's docs point at `../FPVTank_Prototype`.
