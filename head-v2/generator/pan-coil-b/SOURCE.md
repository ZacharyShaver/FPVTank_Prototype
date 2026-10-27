# MG90S servo model: source

`MG90S.3MF` is the MG90S model Zach has been using ("it matches well", 2026-09-28; `docs/decisions.md`). Its origin
and licence weren't recorded, so since 2026-10-26 it is kept locally and gitignored, not redistributed. The checks and
fixes that load it (for example `head-v2/checks/pan_servo_fit.py`) need a copy saved here under that name. The horns
are in `horn/` (see `horn/README.txt`).

The `fusion/*.obj` meshes are exports of Zach's own assemblies. Two of them, `fusion/servo.obj` and `fusion/horn.obj`,
are the MG90S model's servo and horn as placed in his assembly, and `viewer_pan_coil_b.js` embeds the same meshes. They
stay tracked by Zach's call (2026-10-26: "not a big deal"); only the original download files are untracked.
