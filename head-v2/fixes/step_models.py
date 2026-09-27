"""The finished parts as STEP solids in Zach's frame, so Fusion opens them as bodies (2026-09-26):
  out/step/ball_plus_camposts.step              SEWN from out/BODY_NUMBA1_camposts.stl (see below)
  out/step/ball_minus_snap.step, post_v3.step   the rev-2 BREPs
  out/step/camera_post_<upper|lower>_<grade>.step
  out/step/head_v2_ball_full_model.step         both halves, post v3, 2 medium camera posts, 3 medium seam pins
Every file is read back: one solid per part, valid, same volume, unchanged by ShapeFix.

Why ball_plus is sewn from the STL and not written from its BREP: the BREP (Zach's facets fused with the
camera tubes' exact surfaces) passes BRepCheck and meshes to a clean, correctly-sized STL, but ShapeFix and
every STEP reader "repair" it and lose 490 mm3. The sewn STL -- all planar facets, like his own export --
round-trips exactly. checks/check_campost.py keeps both numbers as a regression row."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import cadquery as cq
from campost import TUBES, BARBS
from build_snap import POSTS, pin_seated
from export import rd
from occ_load import load, vol
from OCP.ShapeFix import ShapeFix_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.STEPControl import STEPControl_Reader
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
GREY, BLUE, ORANGE = cq.Color(0.78, 0.78, 0.82, 1.0), cq.Color(0.2, 0.4, 0.9, 1.0), cq.Color(0.95, 0.55, 0.1, 1.0)

def solids(s):
    e = TopExp_Explorer(s, TopAbs_SOLID); n = 0
    while e.More(): n += 1; e.Next()
    return n

def unify(s):
    u = ShapeUpgrade_UnifySameDomain(s, True, True, False); u.Build(); return u.Shape()

def readback(path):
    r = STEPControl_Reader(); r.ReadFile(path); r.TransferRoots(); s = r.OneShape()
    fx = ShapeFix_Shape(s); fx.Perform()
    return solids(s), BRepCheck_Analyzer(s).IsValid(), vol(s), vol(fx.Shape())

def one(name, shape, color, path):
    a = cq.Assembly(name=name + '_file'); a.add(cq.Workplane(obj=cq.Shape.cast(shape)), name=name, color=color)
    a.save(path)

if __name__ == '__main__':
    D = os.path.dirname(config.out('step', 'x'))
    parts = {'ball_plus_camposts': (load(config.out('BODY_NUMBA1_camposts.stl'))[0], GREY),
             'ball_minus_snap': (unify(rd(config.out('ball_minus_snap.brep'))), GREY),
             'post_v3': (unify(rd(config.out('post_v3.brep'))), GREY)}
    for tb in TUBES:
        for g in BARBS:
            parts['camera_post_%s_%s' % (tb, g)] = (rd(config.out('camera_post_%s_%s.brep' % (tb, g))), ORANGE)
    expect = {}
    for nm, (s, c) in parts.items():
        one(nm, s, c, os.path.join(D, nm + '.step')); expect[nm + '.step'] = (1, vol(s))
    full = cq.Assembly(name='head_v2_ball_full_model'); tot = 0.0
    for nm in ('ball_plus_camposts', 'ball_minus_snap', 'post_v3', 'camera_post_upper_medium', 'camera_post_lower_medium'):
        s, c = parts[nm]; full.add(cq.Workplane(obj=cq.Shape.cast(s)), name=nm, color=c); tot += vol(s)
    for i, c in enumerate(POSTS):
        p = pin_seated(c); full.add(cq.Workplane(obj=cq.Shape.cast(p)), name='seam_pin_%d_medium' % (i + 1), color=BLUE); tot += vol(p)
    full.save(os.path.join(D, 'head_v2_ball_full_model.step')); expect['head_v2_ball_full_model.step'] = (8, tot)
    bad = 0
    for f in sorted(expect):
        n, ok, v, vf = readback(os.path.join(D, f)); en, ev = expect[f]
        good = n == en and ok and abs(v - ev) < 0.05 and abs(vf - ev) < 0.05
        bad += not good
        print('  %-36s %5.1f MB  solids %d/%d  valid %-5s  vol %9.2f (wrote %9.2f, after ShapeFix %9.2f)%s'
              % (f, os.path.getsize(os.path.join(D, f)) / 1e6, n, en, ok, v, ev, vf, '' if good else '  <-- CHECK'))
    sys.exit(1 if bad else 0)
