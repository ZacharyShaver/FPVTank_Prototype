"""Verify rev 2 (snap pins). Negative controls: the same rows on Zach's originals."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import time
import numpy as np
from kit import *
from build_snap import tools, POSTS, FRONT, REAR, pin_seated, SEALS
from snap import _revolve_y, NECK_R, CATCH_R, CATCH_L, CHAMFER, FLAT, D_S, SOCKET_DEPTH
from export import rd
from record import record
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
def gap(a, b):
    d = BRepExtrema_DistShapeShape(a, b); d.Perform(); return d.Value()
t0 = time.time()
bp, bm = part('ball_plus'), part('ball_minus')
bp2, bm2 = rd(config.out('ball_plus_snap.brep')), rd(config.out('ball_minus_snap.brep'))
T = tools()
bp_add = fuse(bp, *[s for k, s in T.items() if k.startswith('ADD_plus')], *SEALS)
bm_add = fuse(bm, *[s for k, s in T.items() if k.startswith('ADD_minus')])
print('WHAT EACH TOOL DID (mm3)')
for nm, s in T.items():
    if nm.startswith('ADD'):
        v = vol(cut(s, bp if '_plus_' in nm else bm)); w = 'added  '
    else:
        v = overlap(s, bp_add if '_plus_' in nm else bm_add); w = 'removed'
    print('  %-24s %s %8.2f' % (nm, w, v))

cam = camera(2.5)                      # board on Zach's wall: back face X 10.5
TOP = 21.2355                          # the plate face is at 21.2357 (ray-cast); the case top sits on it
trim, full = servo_trimmed(TOP), servo(TOP, parts=True)
solid = lambda d: fuse(d['body'], d['ear_rear'], d['ear_front'])
rows = []
rows.append(('camera vs ball_plus', overlap(cam, bp2), overlap(cam, bp)))
rows.append(('camera vs ball_minus', overlap(cam, bm2), overlap(cam, bm)))
rows.append(('camera vs servo (tabs snipped / as bought)', overlap(cam, fuse(*trim.values())), overlap(cam, fuse(*full.values()))))
rows.append(('servo seated vs ball_plus (tabs snipped)', overlap(solid(trim), bp2), overlap(solid(full), bp)))
wf, wb = 0.0, 0.0
for dy in np.arange(0.0, 24.01, 1.0):
    wf = max(wf, overlap(moved(solid(trim), 0, -dy, 0), bp2)); wb = max(wb, overlap(moved(solid(full), 0, -dy, 0), bp))
rows.append(('servo sliding in, worst step', wf, wb))
rows.append(('ball halves vs each other', overlap(bp2, bm2), overlap(bp, bm)))
pins = [pin_seated(c) for c in POSTS]
pv_p = sum(overlap(p, bp2) for p in pins); pv_m = sum(overlap(p, bm2) for p in pins)
rows.append(('3 pins seated vs ball_plus (preload ring)', pv_p, float('nan')))
rows.append(('3 pins seated vs ball_minus (preload ring)', pv_m, float('nan')))
rows.append(('pins vs camera', sum(overlap(p, cam) for p in pins), float('nan')))
rows.append(('pins vs servo', sum(overlap(p, fuse(*trim.values())) for p in pins), float('nan')))
print('\n%-46s %9s %12s' % ('', 'SNAP', 'as you sent'))
for n, a, b in rows:
    print('%-46s %8.2f %11s' % (n, a, '%.2f' % b if b == b else '-'))
R = {n: (a, b) for n, a, b in rows}
record('camera_vs_ball_plus', R['camera vs ball_plus'])
record('camera_vs_servo', R['camera vs servo (tabs snipped / as bought)'])
record('servo_seated_vs_ball_plus', R['servo seated vs ball_plus (tabs snipped)'])
record('servo_sliding_worst', R['servo sliding in, worst step'])
record('halves_vs_each_other', R['ball halves vs each other'])
record('pins_seated', (pv_p, pv_m))

print('\nWALLS AROUND EACH SOCKET: grow the socket by w, keep the part past the lead-in, and see how much')
print('of it is air. 0.00 means every wall is at least w thick.')
def grown(c, sign, w):
    neck = _revolve_y([(0, 1.0), (NECK_R + w, 1.0), (NECK_R + w, D_S), (0, D_S)], c, sign)
    ylo, yhi = sorted((sign * 1.0, sign * D_S))
    neck = common(neck, bx((c[0] - 9, ylo, c[1] - FLAT - w), (c[0] + 9, yhi, c[1] + FLAT + w)))
    catch = _revolve_y([(0, D_S), (CATCH_R + w, D_S), (CATCH_R + w, D_S + CATCH_L), (0, D_S + CATCH_L + CATCH_R + w)], c, sign)
    return fuse(neck, catch)
air_1 = 0.0
for i, c in enumerate(POSTS):
    for nm, P, sgn in (('ball_plus', bp2, 1), ('ball_minus', bm2, -1)):
        sock = T['CUT_%s_socket_%d' % ('plus' if sgn > 0 else 'minus', i + 1)]
        solid_around = fuse(P, sock)
        for w in (1.0, 1.2):
            g = grown(c, sgn, w)
            air = vol(cut(g, solid_around))
            if w == 1.0: air_1 = max(air_1, air)
            print('  post %d (X %5.1f Z %4.1f) %-10s w %.1f mm -> air %.3f mm3' % (i + 1, c[0], c[1], nm, w, air))
record('socket_wall_air_1mm', air_1)

print('\nCLEARANCES (mm)')
print('  camera to the new top-front post   %.2f' % gap(cam, fuse(T['ADD_plus_front_post'], T['ADD_minus_front_post'])))
print('  trimmed servo to ball_plus          %.2f   (its case top sits on the plate: 0.00 is contact, not a clash)' % gap(solid(trim), bp2))
print('%.0f s' % (time.time() - t0))
