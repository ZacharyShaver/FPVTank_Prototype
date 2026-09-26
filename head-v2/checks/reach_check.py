"""The whole stack along the tilt axis, your post vs v3, at every position the ball can take."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import *
from post3 import FACE, LIP0, LIP1, TOP, BOSS_TOP, SPLINE_TIP
from export import health, rd
from lens_nest import surface_points
from probe import load_stl
from record import record
H = B.H
p3 = rd(config.out('post_v3.brep')); p0 = part('post')
bp = rd(config.out('ball_plus_snap.brep'))
# 1. the ball's axial range in the cradle: its two flats against the two collar faces (fork SDF, off the hub)
def face_y(sign):
    ys = np.arange(24.0, 27.0, 0.002) * sign
    best = None
    for r in np.arange(11.0, 18.1, 0.5):
        for a in np.radians(np.arange(0, 360, 15)):
            d = B.fork((np.full_like(ys, r * np.cos(a)), ys, np.full_like(ys, H + r * np.sin(a))))
            k = np.argmax(d < 0) if (d < 0).any() else None
            if k is not None:
                y = abs(ys[k]); best = y if best is None else min(best, y)
    return best
fp, fm = face_y(+1), face_y(-1)
print('cradle collar faces: +Y %.2f, -Y %.2f; ball flats +-%.2f -> the ball slides %.2f toward the post, %.2f away'
      % (fp, fm, B.FLAT, fp - B.FLAT, fm - B.FLAT))
# 2. post vs cradle: seated, is anything but the flange touching? (fork SDF on the post's surface)
for nm, T in (('yours', load_stl(config.zach('post'))), ('v3', load_stl(config.out('ball_servo_post_v3.stl')))):
    P = surface_points(T, step=0.2)
    d = B.fork((P[:, 0], P[:, 1], P[:, 2]))
    inside = d < -0.02
    print('post %-5s vs cradle: deepest %.3f mm; points inside the cradle: %d (flange sits in its recess: contact is expected there)'
          % (nm, -d.min(), inside.sum()))
    if inside.any():
        Q = P[inside]; print('      where: Y %.2f..%.2f  r %.2f..%.2f' % (Q[:, 1].min(), Q[:, 1].max(), np.hypot(Q[:, 0], Q[:, 2] - H).min(), np.hypot(Q[:, 0], Q[:, 2] - H).max()))
# 3. at each ball position: post vs ball, spline engagement, gap to the boss
lo, hi = -(fm - B.FLAT), fp - B.FLAT
print('\n%-6s %-24s %10s %12s %14s %12s' % ('post', 'ball position', 'vs ball', 'spline in', 'post end to', 'spline tip'))
print('%-6s %-24s %10s %12s %14s %12s' % ('', '', '(mm3)', 'post (mm)', 'servo boss', 'to stop'))
for nm, P, face, stop in (('yours', p0, 27.5, 31.24), ('v3', p3, FACE, LIP0)):
    for off, lab in ((lo, 'pushed away (%.2f)' % lo), (0.0, 'centred'), (hi, 'toward post (+%.2f)' % hi)):
        ov = overlap(P, moved(bp, 0, off, 0))
        tip, boss = SPLINE_TIP + off, BOSS_TOP + off
        print('%-6s %-24s %10.2f %12.2f %14.2f %12.2f' % (nm, lab, ov, max(0.0, tip - face), face - boss, stop - tip))
        if (nm, off) == ('yours', lo):
            record('post_yours_pressed', (max(0.0, tip - face), face - boss, lo))
print('\nv3 with the centre screw pulled tight: spline tip on the stop -> ball at %+.2f (centred), %.2f of spline in the post'
      % (LIP0 - SPLINE_TIP, LIP0 - FACE))
record('post_v3_screw_tight', (LIP0 - FACE, FACE - BOSS_TOP - (LIP0 - SPLINE_TIP)))
print('post v3 mesh:', health(config.out('ball_servo_post_v3.stl'))[1])
