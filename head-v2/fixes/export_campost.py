"""Camera-post hand-off meshes and the Fusion tool bodies:
  out/BODY_NUMBA1_camposts.stl                      the new ball_plus in Zach's frame, needle-repaired
  out/print/ball_plus_camposts.stl                  seam face down
  out/print/camera_post_<upper|lower>_<grade>.stl   lying on the bed flat, angled head up, lowest vertex on z = 0
  out/camera_post_tools_for_fusion.step             ADD_* / CUT_* tool bodies + the two medium posts seated
The order below is the order the hand-off was made in (2026-09-26): keep it, the STLs are compared byte for byte."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import cadquery as cq
from campost import TUBES, BARBS, to_local, all_tools
from export import write_stl, health, tidy, rd, drop_to_bed
from print_export import rot_x, on_bed, size
from OCP.gp import gp_Trsf, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

def on_bed_tight(s):
    """centre on x/y, lowest point on z = 0 -- AddOptimal, because Add_s is loose on curved faces"""
    b = Bnd_Box(); BRepBndLib.AddOptimal_s(s, b, True, False); x0, y0, z0, x1, y1, z1 = b.Get()
    t = gp_Trsf(); t.SetTranslation(gp_Vec(-(x0 + x1) / 2, -(y0 + y1) / 2, -z0))
    return BRepBuilderAPI_Transform(s, t, True).Shape()

if __name__ == '__main__':
    os.makedirs(config.PRINT, exist_ok=True)
    bp2 = rd(config.out('ball_plus_camposts.brep'))
    f = config.out('BODY_NUMBA1_camposts.stl')
    write_stl(bp2, f, lin=0.01, ang=0.1)
    print('BODY_NUMBA1_camposts.stl: needle repair moved the surface %.4f mm' % tidy(f))
    s = on_bed(rot_x(bp2, 90.0))                    # +Y up: seam face on the bed, like every ball_plus before it
    f = os.path.join(config.PRINT, 'ball_plus_camposts.stl')
    write_stl(s, f, lin=0.01, ang=0.05); tidy(f)
    print('ball_plus_camposts.stl  %.1f x %.1f x %.1f mm' % size(s))
    for tb in TUBES:
        for g in BARBS:
            s = on_bed_tight(to_local(rd(config.out('camera_post_%s_%s.brep' % (tb, g))), tb))
            f = os.path.join(config.PRINT, 'camera_post_%s_%s.stl' % (tb, g))
            write_stl(s, f, lin=0.004, ang=0.05)
            drop_to_bed(f)                          # exact: the lowest vertex on z = 0
            print('camera_post_%s_%-6s %.1f x %.1f x %.1f mm' % ((tb, g) + size(s)))
    print('mesh health:')
    for fn in ['BODY_NUMBA1_camposts.stl'] + [os.path.join('print', n) for n in
               ['ball_plus_camposts.stl'] + ['camera_post_%s_%s.stl' % (tb, g) for tb in TUBES for g in BARBS]]:
        ok, msg = health(config.out(fn)); print('  %-40s %s%s' % (fn, msg, '' if ok else '   <-- CHECK'))
    asm = cq.Assembly(name='camera_posts')
    col = {'CUT': cq.Color(0.85, 0.2, 0.2, 0.6), 'ADD': cq.Color(0.2, 0.7, 0.3, 0.8)}
    for nm, s in all_tools().items():
        asm.add(cq.Workplane(obj=cq.Shape.cast(s)), name=nm, color=col[nm[:3]])
    for tb in TUBES:
        asm.add(cq.Workplane(obj=cq.Shape.cast(rd(config.out('camera_post_%s_medium.brep' % tb)))), name='POST_%s_medium' % tb,
                color=cq.Color(0.95, 0.55, 0.1, 1.0))
    asm.save(config.out('camera_post_tools_for_fusion.step'))
    print('wrote camera_post_tools_for_fusion.step')
