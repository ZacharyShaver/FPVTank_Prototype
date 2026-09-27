"""Put the seam-pin STLs on the bed (2026-09-26). print_export.py sizes them with BRepBndLib.Add_s, which
is loose on their curved noses, so they came out 0.50-0.59 mm above z = 0 -- in the hand-off since
2026-09-25. Most slicers drop a part to the bed anyway; this makes the files right.

Runs after plate3mf.py (which needle-repairs them) and drops the repaired meshes, in the same order the
hand-off was fixed in. The copies in out/ itself become the same files as out/print/, as in the hand-off."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import shutil
from export import drop_to_bed, health
from snap import BARBS

if __name__ == '__main__':
    for g in BARBS:
        f = os.path.join(config.PRINT, 'snap_pin_stop_%s.stl' % g)
        dz = drop_to_bed(f)
        shutil.copyfile(f, config.out('snap_pin_stop_%s.stl' % g))
        ok, msg = health(f)
        print('snap_pin_stop_%-6s dropped %.3f mm  %s%s' % (g, dz, msg, '' if ok else '  <-- CHECK'))
