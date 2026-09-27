# The head-v2 generator

FPVTank_Control's `docs/chassis/head-v2/` tree, moved here whole in phase B (2026-09-27). The
generators find their output folders and the camera by relative paths
(`generators/../tree-parts-b`, `generators/../camera`), so keep the tree together.

- `generators/`: the SDF generators. `tree_parts_b.py` is variant B, the live one (the ball in a nest).
  `build_b.py --solids --check` rebuilds its STEP solids and runs its checks.
- `tree-parts-b/`: variant B's output (the cradle `fork`, Fusion OBJs, STEP solids) and its README.
- `camera/`: the camera dummy that `tools/config.py` reads as `CAMERA`.
- `pan-coil-b/` and `pan-coil-360-brief.md`: the 360-degree pan coil with the 2:1 gear.
- `tree-parts/`, `tree-hood/`, `pan-coil/`, `concept/`, `test-print-2/`, `tree-arm-test/`, `coil-test/`:
  older forks and test rigs, kept for the record.
- `ball-head-validation-handoff.md`: the camera measurements and the ribbon path.

The ball itself is Zach's Fusion model now (`head-v2/fusion/`), not `tree_parts_b.py`'s ball. The
generator still owns the cradle (`fork`), the axle, the post and the caps. Its `*/print/` output is
untracked.
