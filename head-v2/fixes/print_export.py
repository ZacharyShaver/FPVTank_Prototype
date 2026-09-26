"""Print-ready set: every part turned to how it prints, on z = 0, centred. plate3mf.py then tidies these
and lays the plate out."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import *
from snap import pin, BARBS
from export import write_stl, health, rd
from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
H = B.H
def rot_x(s, deg):
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), np.radians(deg))
    return BRepBuilderAPI_Transform(s, t, True).Shape()
def on_bed(s, at=(0.0, 0.0)):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b, True); x0, y0, z0, x1, y1, z1 = b.Get()
    t = gp_Trsf(); t.SetTranslation(gp_Vec(at[0] - (x0 + x1) / 2, at[1] - (y0 + y1) / 2, -z0))
    return BRepBuilderAPI_Transform(s, t, True).Shape()
def size(s):
    b = Bnd_Box(); BRepBndLib.Add_s(s, b, True); x0, y0, z0, x1, y1, z1 = b.Get(); return x1 - x0, y1 - y0, z1 - z0
if __name__ == '__main__':
    os.makedirs(config.PRINT, exist_ok=True)
    # the generator's print orientations: ball_plus +Y up (seam face on the bed), ball_minus -Y up (seam face
    # on the bed), post -Y up (flange's outer face on the bed). rot_x(+90) maps +Y -> +Z; rot_x(-90) maps -Y -> +Z.
    parts = {
        'ball_plus':  rot_x(rd(config.out('ball_plus_snap.brep')), 90.0),
        'ball_minus': rot_x(rd(config.out('ball_minus_snap.brep')), -90.0),
        'post_v3':    rot_x(rd(config.out('post_v3.brep')), -90.0),
    }
    for nm, br in BARBS.items():
        parts['snap_pin_stop_%s' % nm] = pin(br, nose=True)[0]           # already lies on its flat, axis along Y
    for nm, s in parts.items():
        s = on_bed(s)
        path = os.path.join(config.PRINT, nm + '.stl')
        write_stl(s, path, lin=0.01 if nm.startswith('ball') else 0.005, ang=0.05)
        ok, msg = health(path)
        print('%-24s %5.1f x %5.1f x %5.1f mm  %s%s' % (nm + '.stl', *size(s), msg, '' if ok else '  <-- CHECK'))
