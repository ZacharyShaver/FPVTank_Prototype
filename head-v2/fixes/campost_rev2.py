"""Camera snap posts for Zach's Fusion rev 2 (2026-09-27).

He did the rev-2 camera-post booleans in Fusion himself, then moved both post tubes +2.0 mm in Z so
the lens sits midway between the board's holes ("the lens is directly center to the posts", by hand).
The tubes are the same shape as campost.tools() made them, so the ball needs nothing; only the posts
change, because a post's flats are turned to its tube's direction from the lens axis and its head is
trimmed to where its tube leaves the sphere.

TUBES_R2 is fitted, not typed in: the bore and catch tools slid until they sit in his empty space
(fit_tubes() below; campost's rev-1 positions read hundreds of mm3 there, the control).

Writes out/rev2/camera_post_<upper|lower>_<grade>.brep. Export: export_campost_rev2.py.
    python head-v2/fixes/campost_rev2.py [--fit]
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import campost as C
from occ_load import load, vol
from kit import common

R2 = os.path.join(config.REPO, 'head-v2', 'fusion', 'rev2-2026-09-27')
BALL_PLUS = os.path.join(R2, 'ball_plus_revised_9_27.stl')
BALL_MINUS = os.path.join(R2, 'ball_minus_revised_27.stl')
TUBES_R1 = dict(C.TUBES)
# Z from fit_tubes(): bore + catch leave 1.24 / 2.18 mm3 inside his plastic here, 60.65 / 75.66 at the
# rev-1 axes (0.35 is the floor: the same tools against the shipped ball, whose STL they made). Y from
# the wall holes the pins go into, rayed directly: both centred on Y 14.70, Z 37.95 / 66.85. The fit's
# Y 14.85 for the lower tube was the double-D bore's facets -- it put the pin tip 0.15 into the hole's
# edge. Straight up 2.00 on both, as he moved them.
TUBES_R2 = {'lower': (14.70, 37.95), 'upper': (14.70, 66.85)}
# The pins place the board, so it settles between them: lens this far above Z 52, and across in Y.
LENS_DZ = (TUBES_R2['lower'][1] + TUBES_R2['upper'][1]) / 2 - C.H                      # +0.40
LENS_DY = (TUBES_R2['lower'][0] + TUBES_R2['upper'][0]) / 2 - TUBES_R1['upper'][0]       # 0
# His wall holes behind the board are 1.78 across (rayed); the pin is 1.80, so its tip would jam 0.01.
# Inside the wall (X < 10.5, the board's back face) the pin steps down to 1.48: 0.15 a side, the slide rule.
WALL_PIN_R = 0.74


def post(tb, grade):
    """campost.post, with the pin's tip slimmed where it enters his wall hole"""
    from kit import cyl, cut
    ring = cut(cyl('x', (0.0, 0.0), 1.5, C.PIN_TIP - 1.0, C.WALL_FACE), cyl('x', (0.0, 0.0), WALL_PIN_R, C.PIN_TIP - 2.0, C.WALL_FACE + 1.0))
    return cut(C.post(tb, grade), C.to_head(ring, tb))


def use_rev2():
    """point campost's functions at rev 2's tubes (they read C.TUBES at call time)"""
    C.TUBES.clear(); C.TUBES.update(TUBES_R2)


def leftover(ball, tb, y, z):
    """bore + catch tool volume inside the ball, with the tube at (y, z): ~0 where his tube is"""
    saved = dict(C.TUBES); C.TUBES[tb] = (y, z)
    T = C.tools(tb)
    s = vol(common(T['CUT_plus_bore_' + tb], ball)) + vol(common(T['CUT_plus_catch_' + tb], ball))
    C.TUBES.clear(); C.TUBES.update(saved)
    return s


def fit_tubes(ball):
    from kit import bx
    out = {}
    for tb, (y0, z0) in TUBES_R1.items():
        ball_tb = common(ball, bx((C.TUBE_X0 - 2, y0 - 6, z0 - 5), (32, y0 + 6, z0 + 7)))   # crop: 10x faster
        ball, full = ball_tb, ball
        best = None
        for dz in np.arange(1.7, 2.31, 0.1):
            for dy in (-0.2, -0.1, 0.0, 0.1, 0.2):
                s = leftover(ball, tb, y0 + dy, z0 + dz)
                if best is None or s < best[0]:
                    best = (s, y0 + dy, z0 + dz)
        for dz in np.arange(-0.1, 0.101, 0.025):
            for dy in np.arange(-0.1, 0.101, 0.025):
                s = leftover(ball, tb, best[1] + dy, best[2] + dz)
                if s < best[0]:
                    best = (s, best[1] + dy, best[2] + dz)
        out[tb] = best
        print('%s: axis Y %.2f Z %.2f, leftover %.4f mm3 (rev-1 position: %.2f)'
              % (tb, best[1], best[2], best[0], leftover(ball, tb, y0, z0)), flush=True)
        ball = full
    return out


if __name__ == '__main__':
    from export import wr
    from OCP.BRepCheck import BRepCheck_Analyzer
    ball = load(BALL_PLUS)[0]
    if '--fit' in sys.argv:
        fit_tubes(ball)
        sys.exit(0)
    use_rev2()
    print('tubes %s, lens %+.2f above the tilt axis' % (TUBES_R2, LENS_DZ))
    for tb in TUBES_R2:
        print('  %s tube leftover at the rev-2 axis %.4f mm3' % (tb, leftover(ball, tb, *TUBES_R2[tb])))
        for g in C.BARBS:
            p = post(tb, g)
            wr(p, config.out('rev2', 'camera_post_%s_%s.brep' % (tb, g)))
            print('  post %-5s %-6s valid %s vol %.1f' % (tb, g, BRepCheck_Analyzer(p).IsValid(), vol(p)))
