"""Verify the camera snap posts (2026-09-26). Controls beside each number:
  - other parts vs the new ball_plus, and vs rev 2's (they must not change);
  - a post sliding in with its barbs (must touch: proves the slide test sees contact) vs without (must not);
  - the long post pushed into the LOWER hole (must jam: the swap-proofing) vs the short one in the upper
    hole (only its barbs touch);
  - the heads' farthest point vs the ball's own radius;
  - the ball_plus STEP round trip from the sewn STL vs from the exact BREP (which loses volume).
Needs head-v2/out/ from build_all.py (campost.py, export_campost.py, step_models.py)."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import time
import numpy as np
from kit import camera, servo_trimmed, fuse, cut, common, moved, bx, cyl
from occ_load import load, vol
from export import rd
from record import record
from campost import (TUBES, BARBS, SRC, H, R_BALL, X_EDGE, R_BODY, to_head, to_local, post_local, sphere, all_tools,
                     RECESS)
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.STEPControl import STEPControl_Writer, STEPControl_Reader, STEPControl_AsIs
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_VERTEX
from OCP.BRep import BRep_Tool
from OCP.TopoDS import TopoDS

def gap(a, b):
    d = BRepExtrema_DistShapeShape(a, b); d.Perform(); return d.Value()

def max_r(s):
    ex = TopExp_Explorer(s, TopAbs_VERTEX); m = 0.0
    while ex.More():
        p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(ex.Current())); m = max(m, float(np.sqrt(p.X() ** 2 + p.Y() ** 2 + (p.Z() - H) ** 2))); ex.Next()
    return m

def step_loss(shape, path):
    w = STEPControl_Writer(); w.Transfer(shape, STEPControl_AsIs); w.Write(path)
    r = STEPControl_Reader(); r.ReadFile(path); r.TransferRoots()
    return vol(shape) - vol(r.OneShape())

t0 = time.time()
bp = load(SRC)[0]                                           # rev 2 ball_plus, the posts' source
bp2 = rd(config.out('ball_plus_camposts.brep'))
bm = load(config.out('ball_minus_revised_snap.stl'))[0]
post3 = load(config.out('ball_servo_post_v3.stl'))[0]
cam = camera(2.5)                                            # board on Zach's wall, back face X 10.5
sv = fuse(*servo_trimmed(21.2355).values())
P = {(tb, g): rd(config.out('camera_post_%s_%s.brep' % (tb, g))) for tb in TUBES for g in BARBS}

T = all_tools()
bp_add = fuse(bp, *[s for k, s in T.items() if k.startswith('ADD')])
print('WHAT EACH TOOL DID (mm3)')
for k, s in T.items():
    v = vol(cut(s, bp)) if k.startswith('ADD') else vol(common(s, bp_add))
    print('  %-24s %s %7.2f' % (k, 'added  ' if k.startswith('ADD') else 'removed', v))
far, far0 = bp2, bp
for tb in TUBES:
    zone = to_head(cyl('x', (0, 0), 4.5, 12.0, 40), tb)
    far = cut(far, zone); far0 = cut(far0, zone)
print('  ball away from the two tubes: %.3f mm3 changed' % abs(vol(far) - vol(far0)))

print('\nOTHER PARTS vs ball_plus             NEW      REV 2')
tot_new = tot_old = 0.0
for nm, s in (('camera', cam), ('servo (tabs snipped)', sv), ('post_v3', post3), ('ball_minus', bm)):
    a, b = vol(common(s, bp2)), vol(common(s, bp)); tot_new += a; tot_old += b
    print('  %-26s %8.3f %8.3f' % (nm, a, b))
record('campost_other_parts', (tot_new, tot_old))

print('\nCAMERA POSTS, seated')
for (tb, g), p in P.items():
    ring = vol(common(common(p, bp2), bx((X_EDGE - 0.05, -40, 0), (X_EDGE + 0.6, 40, 100))))
    print('  %-5s %-6s vs ball %.4f (at the step %.4f) | vs camera %.3f, gap %.3f | vs ball_minus %.3f | vs servo %.3f'
          % (tb, g, vol(common(p, bp2)), ring, vol(common(p, cam)), gap(p, cam), vol(common(p, bm)), vol(common(p, sv))))
record('campost_seated', sum(vol(common(P[(tb, 'medium')], bp2)) for tb in TUBES))
record('campost_vs_camera', sum(vol(common(p, cam)) for p in P.values()))
heads = max(max_r(P[(tb, 'medium')]) for tb in TUBES)
print('  heads: farthest point from the ball centre %.3f (ball %.2f, nest %.2f)' % (heads, R_BALL, R_BALL + 1.5))
record('campost_head_r', (heads, R_BALL))

print('\nINSERTION: each medium post slid back out along its hole by s')
STEPS = (0.1, 0.3, 0.6, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)
worst_bare = worst_barbs = 0.0
for tb in TUBES:
    bare = common(to_head(post_local(tb, R_BODY), tb), sphere(R_BALL - RECESS))       # same post, no barbs
    a = [vol(common(moved(P[(tb, 'medium')], s_, 0, 0), bp2)) for s_ in STEPS]
    b = [vol(common(moved(bare, s_, 0, 0), bp2)) for s_ in STEPS]
    worst_barbs, worst_bare = max(worst_barbs, max(a)), max(worst_bare, max(b))
    print('  %-5s with barbs:    %s' % (tb, '  '.join('%.1f:%.3f' % z for z in zip(STEPS, a))))
    print('  %-5s without barbs: %s' % (tb, '  '.join('%.1f:%.3f' % z for z in zip(STEPS, b))))
record('campost_slide', (worst_bare, worst_barbs))

print('\nSWAP-PROOF: each post pushed into the OTHER hole, stopped 2 mm short of seating')
sw = {}
for a_, b_ in (('upper', 'lower'), ('lower', 'upper')):
    wrong = moved(to_head(to_local(P[(a_, 'medium')], a_), b_), 2.0, 0, 0)
    sw[a_] = vol(common(wrong, bp2))
    print('  %s post in the %s hole: overlap %.2f mm3' % (a_, b_, sw[a_]))
record('campost_swap', (sw['upper'], sw['lower']))

print('\nWALLS')
out_shell = cut(sphere(45.0), sphere(R_BALL))
walls = []
for tb in TUBES:
    w = gap(T['CUT_plus_catch_' + tb], out_shell); walls.append(w)
    print('  %s catch -> outside %.2f mm | new tube wall -> camera %.2f mm' % (tb, w, gap(T['ADD_plus_tube_' + tb], cam)))
record('campost_catch_wall', min(walls))

print('\nSTEP ROUND TRIP of ball_plus (volume lost, mm3)')
sewn = load(config.out('BODY_NUMBA1_camposts.stl'))[0]
l_sewn = step_loss(sewn, config.out('logs', '_rt_sewn.step'))
l_brep = step_loss(bp2, config.out('logs', '_rt_brep.step'))
print('  sewn from the STL (shipped): %.2f   exact BREP (not shipped): %.2f' % (l_sewn, l_brep))
record('campost_step_loss', (l_sewn, l_brep))
print('%.0f s' % (time.time() - t0))
