"""Verify the camera snap posts against Zach's Fusion rev 2 (2026-09-27), with the real board (lens
centred between its holes). Controls beside each number:
  - his tubes vs the tube tools at the rev-2 axes (~0: the STL's facets) vs at rev 1's (must not be);
  - posts vs the board, with the board where the pins put it (must be 0) vs the superseded photo board
    at Z 52 (must hit: that is the 2 mm Zach fixed);
  - other parts vs rev 2's ball_plus, and the same on the shipped ball;
  - posts seated (designed preload at the step), sliding in with / without barbs, heads vs the sphere,
    swap-proofing, catch wall.
Needs out/rev2/ from fixes/campost_rev2.py. Numbers go to regression.json under r2_*.
    python head-v2/checks/check_campost_rev2.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import time
import numpy as np
from kit import camera, servo_trimmed, fuse, cut, common, moved, bx
from occ_load import load, vol
from export import rd
from record import record
import campost as C
import campost_rev2 as R
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_VERTEX
from OCP.BRep import BRep_Tool
from OCP.TopoDS import TopoDS


def gap(a, b):
    d = BRepExtrema_DistShapeShape(a, b); d.Perform(); return d.Value()


def max_r(s):
    ex = TopExp_Explorer(s, TopAbs_VERTEX); m = 0.0
    while ex.More():
        p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(ex.Current()))
        m = max(m, float(np.sqrt(p.X() ** 2 + p.Y() ** 2 + (p.Z() - C.H) ** 2))); ex.Next()
    return m


t0 = time.time()
his = load(R.BALL_PLUS)[0]                         # as exported
bp = rd(config.out('rev2', 'ball_plus_rev2.brep'))  # + the IR cutout extension (fixes/ball_plus_rev2.py)
bm = load(R.BALL_MINUS)[0]
ship = load(config.out('BODY_NUMBA1_camposts.stl'))[0]
post3 = load(config.out('ball_servo_post_v3.stl'))[0]
cam = camera(2.5, centred=True, dz=R.LENS_DZ, dy=R.LENS_DY)       # the real board, where the pins put it
cam_photo = camera(2.5)                              # superseded photo board, lens on Z 52 (control)
sv = fuse(*servo_trimmed(21.2355).values())
R.use_rev2()
P = {(tb, g): rd(config.out('rev2', 'camera_post_%s_%s.brep' % (tb, g))) for tb in C.TUBES for g in C.BARBS}
print('loaded (%.0f s); lens %+.2f above the tilt axis' % (time.time() - t0, R.LENS_DZ))

print('\nHIS TUBES vs the tube tools (bore + catch inside his plastic, mm3)   rev-2 axis   rev-1 axis')
fit = {tb: (R.leftover(his, tb, *R.TUBES_R2[tb]), R.leftover(his, tb, *R.TUBES_R1[tb])) for tb in C.TUBES}
for tb, (a, b) in fit.items():
    print('  %-5s %32s %8.3f %12.3f' % (tb, '', a, b))
record('r2_tube_fit', (sum(a for a, _ in fit.values()), sum(b for _, b in fit.values())))

import ball_plus_rev2 as IR
ir = IR.tools()['CUT_plus_ir_extend']
removed = common(ir, his)
print('\nIR CUTOUT EXTENSION: removed %.1f mm3 (all of it inside the tool: %.1f); tube walls %.3f / %.3f mm3 inside the tool'
      % (vol(his) - vol(bp), vol(removed), *[vol(common(ir, C.tools(tb)['ADD_plus_tube_' + tb])) for tb in C.TUBES]))
record('r2_ir_extend', (vol(his) - vol(bp), vol(removed)))

print('\nOTHER PARTS vs ball_plus               REV 2   SHIPPED')
tot = [0.0, 0.0]
for nm, s in (('camera (real board)', cam), ('servo (tabs snipped)', sv), ('post_v3', post3), ('ball_minus', bm)):
    a, b = vol(common(s, bp)), vol(common(s, ship)); tot[0] += a; tot[1] += b
    print('  %-28s %8.3f %8.3f' % (nm, a, b))
record('r2_other_parts', tuple(tot))

print('\nCAMERA POSTS, seated')
for (tb, g), p in P.items():
    ring = vol(common(common(p, bp), bx((C.X_EDGE - 0.05, -40, 0), (C.X_EDGE + 0.6, 40, 100))))
    print('  %-5s %-6s vs ball %.4f (at the step %.4f) | vs board %.3f, gap %.3f | vs photo board %.3f | vs ball_minus %.3f | vs servo %.3f'
          % (tb, g, vol(common(p, bp)), ring, vol(common(p, cam)), gap(p, cam), vol(common(p, cam_photo)),
             vol(common(p, bm)), vol(common(p, sv))))
record('r2_campost_seated', sum(vol(common(P[(tb, 'medium')], bp)) for tb in C.TUBES))
record('r2_campost_vs_board', (sum(vol(common(p, cam)) for p in P.values()),
                               sum(vol(common(p, cam_photo)) for p in P.values())))
heads = max(max_r(P[(tb, 'medium')]) for tb in C.TUBES)
print('  heads: farthest point from the ball centre %.3f (ball %.2f)' % (heads, C.R_BALL))
record('r2_campost_head_r', (heads, C.R_BALL))

print('\nINSERTION: each medium post slid back out along its hole by s')
STEPS = (0.1, 0.3, 0.6, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)
worst_bare = worst_barbs = 0.0
for tb in C.TUBES:
    bare = common(C.to_head(C.post_local(tb, C.R_BODY), tb), C.sphere(C.R_BALL - C.RECESS))
    a = [vol(common(moved(P[(tb, 'medium')], s_, 0, 0), bp)) for s_ in STEPS]
    b = [vol(common(moved(bare, s_, 0, 0), bp)) for s_ in STEPS]
    worst_barbs, worst_bare = max(worst_barbs, max(a)), max(worst_bare, max(b))
    print('  %-5s with barbs:    %s' % (tb, '  '.join('%.1f:%.3f' % z for z in zip(STEPS, a))))
    print('  %-5s without barbs: %s' % (tb, '  '.join('%.1f:%.3f' % z for z in zip(STEPS, b))))
record('r2_campost_slide', (worst_bare, worst_barbs))

print('\nSWAP-PROOF: each post pushed into the OTHER hole, stopped 2 mm short of seating')
sw = {}
for a_, b_ in (('upper', 'lower'), ('lower', 'upper')):
    wrong = moved(C.to_head(C.to_local(P[(a_, 'medium')], a_), b_), 2.0, 0, 0)
    sw[a_] = vol(common(wrong, bp))
    print('  %s post in the %s hole: overlap %.2f mm3' % (a_, b_, sw[a_]))
record('r2_campost_swap', (sw['upper'], sw['lower']))

print('\nWALLS')
T = C.all_tools()
out_shell = cut(C.sphere(45.0), C.sphere(C.R_BALL))
walls = [gap(T['CUT_plus_catch_' + tb], out_shell) for tb in C.TUBES]
for tb, w in zip(C.TUBES, walls):
    print('  %s catch -> outside %.2f mm | tube wall -> board %.2f mm' % (tb, w, gap(T['ADD_plus_tube_' + tb], cam)))
record('r2_campost_catch_wall', min(walls))
print('%.0f s' % (time.time() - t0))
