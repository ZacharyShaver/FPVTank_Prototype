# FPVTank_Prototype

The physical design of the Scorpion robot (FPVTank): Zach's Fusion exports, the fixes applied to them,
the fit checks, and the print sets. The robot's code is the sibling repo `../FPVTank_Control`. This repo
is never deployed to the Pi.

It began in 2024 as the first tank: an FPV-Rover V2.0 print driven over Wi-Fi. That download is now
`reference/fpv-rover-v2/`, and its code is in `archive/v1-2024/`.

## Layout

| Path | What's there |
|---|---|
| `CLAUDE.md` | the rules: frame, fits, how every change is checked |
| `head-v2/` | the pan/tilt camera head, v2: a ball in a nest. `NOTES.md` is its live state |
| `head-v2/fusion/rev1-2026-09-24/` | Zach's Fusion exports, the source of truth |
| `head-v2/fixes/` | the scripts that turn a Fusion revision into its fixed version and the hand-off |
| `head-v2/checks/` | fit checks, each with its negative control. `regression.py` runs them |
| `head-v2/generator/` | the SDF generator: the cradle, the 360° pan coil and the older forks |
| `head-v2/out/` | *(untracked)* everything the fixes write: print STLs, 3MF, STEP, pictures |
| `chassis-v1/` | the chassis parts as used on the robot |
| `reference/fpv-rover-v2/` | the original FPV-Rover V2.0 download, by Markus_p |
| `reference/raspberry-pi-5/` | Pi 5 fit-check models |
| `reference/solids/` | fit-check dummies: servo, camera, bearing, screw heads |
| `reference/downloads/` | *(untracked)* big third-party files that can be downloaded again |
| `archive/` | superseded work worth keeping: the 2024 code, the August 2026 pan/tilt, head-v2 rev 1 |
| `docs/decisions.md` | why each design went the way it did |
| `docs/lessons/` | lessons |
| `tools/` | shared Python: STL to exact solid, booleans, ray and slice probes, renders, mesh report, export |
| `docs/reorg-2026-09/` | the reorganisation: phase A (this layout) and phase B (the move out of Control), both done |

## The current print set

Head v2, ball rev 2: Zach's Fusion rev 1 plus snap pins plus post v3 (delivered 2026-09-25), plus the
camera snap posts and the finished parts as STEP solids (2026-09-26). The set is in
`Downloads/head-v2-snap/`; its `README.txt` says what to print first and how to put it together.
This repo regenerates the set into `head-v2/out/`, byte for byte for the STLs, the 3MF plates' meshes
and the pictures. The STEP files differ only in metadata (timestamp, assembly ids, colour order); their
solids match.

## Running the tools

Use `python`. On Zach's machine that's the Microsoft Store Python 3.10, which has cadquery (OCP),
pymeshlab and the rest (`tools/requirements.txt`). Every script finds its paths through
`tools/config.py`, so it runs from any folder:

```
python head-v2/fixes/build_all.py      # about 3 min: halves, post, camera posts, meshes, STEP, print set, 3MF, pictures
python head-v2/checks/regression.py    # about 6 min: the checks, and the table they must reproduce
python head-v2/checks/reeval.py        # a revision as drawn, before any fix
```

The generator lives in `head-v2/generator/` (since phase B, 2026-09-27). FPVTank_Control holds no CAD.

## Git on Windows

Commits before the 2026-09-26 reorganisation contain `3D - Model Tank/3D Printed FPV Rover V2.0 : 11
Steps (with Pictures) - Instructables.pdf`. Windows can't create a file with a colon in its name, so it
can't check those commits out.

The reorganisation renamed that file to `reference/fpv-rover-v2/FPV Rover V2.0 - Instructables guide.pdf`,
so everything since checks out normally. To check out an older commit, first skip that one file with a
sparse checkout:

```
git sparse-checkout set --no-cone "/*" "!/3D - Model Tank/*Instructables.pdf"
```
