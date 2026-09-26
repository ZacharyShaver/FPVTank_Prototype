"""Nothing proud of the ball any more, and the old screw holes are shut: the solid met along each post's
axis, rev 2 vs Zach's, and the farthest any point of each half gets from the ball's centre.
(The same halves against the nest over the tilt range: ball_nest.py.)"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import B
from probe import load_stl, hits
from build_snap import REAR, FRONT
H = B.H
S = {'ball_plus': (load_stl(config.out('BODY_NUMBA1_snap.stl')), load_stl(config.zach('ball_plus'))),
     'ball_minus': (load_stl(config.out('ball_minus_revised_snap.stl')), load_stl(config.zach('ball_minus')))}
def segs(T, x, z, y0=-40.0):
    t = np.sort(hits(T, (x, y0, z), (0, 1.0, 0))); t = t[t > 0] + y0
    return ', '.join('%.2f..%.2f' % (t[k], t[k + 1]) for k in range(0, len(t) - 1, 2)) or '-'
print('ALONG EACH POST AXIS (solid met, Y):')
for nm, (T1, T0) in S.items():
    for c in REAR + [FRONT]:
        print('  %-10s X %5.1f Z %4.1f   snap: %-26s yours: %s' % (nm, c[0], c[1], segs(T1, *c), segs(T0, *c)))
print('\nFARTHEST POINT FROM THE BALL CENTRE (sphere %.1f):' % B.R_BALL)
for nm, (T1, T0) in S.items():
    for lab, T in (('snap', T1), ('yours', T0)):
        V = T.reshape(-1, 3)
        rr = np.sqrt(V[:, 0] ** 2 + V[:, 1] ** 2 + (V[:, 2] - H) ** 2)
        print('  %-10s %-5s %.3f' % (nm, lab, rr.max()))
