# MG90S servo model: source

`MG90S.3MF` is the MG90S model Zach has been using ("it matches well", 2026-09-28; `docs/decisions.md`). Its origin
and licence weren't recorded, so since 2026-10-26 it is kept locally and gitignored, not redistributed. The checks and
fixes that load it (for example `head-v2/checks/pan_servo_fit.py`) need a copy saved here under that name. The horns
are in `horn/` (see `horn/README.txt`).

The `fusion/*.obj` meshes are exports of Zach's own assemblies, so they stay tracked.
