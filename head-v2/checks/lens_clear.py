"""With the board on Zach's wall (X 10.5) the lens tip is at X 31.5, 0.8 proud of the ball.
Does it clear the NEST through the whole tilt range, and does the nest stay out of the view?
Exact: the fork's own SDF evaluated at points on the real camera's surface.
Control: the board where the generator put it (X 8.0)."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import B
from probe import load_stl
from lens_nest import surface_points, tilt, view_depth, V_HALF
from record import record
H = B.H

if __name__ == '__main__':
    T = load_stl(os.path.join(config.CAMERA, 'camera_dummy.stl'))
    P0 = surface_points(T)
    print('camera surface points: %d' % len(P0))
    for dx, lab in ((0.0, 'board X 8.0 (tip 29.0)'), (2.5, 'board X 10.5 (tip 31.5)')):
        P = P0 + [dx, 0, 0]
        r = np.hypot(P[:, 0], P[:, 2] - H)
        P = P[r > 24.0]
        worst = (np.inf, None)
        for t in np.arange(B.TILT_DOWN, B.TILT_UP + 0.01, 1.0):
            Q = tilt(P, t)
            d = B.fork((Q[:, 0], Q[:, 1], Q[:, 2]))
            if d.min() < worst[0]:
                worst = (d.min(), t, Q[np.argmin(d)])
        print('%-26s nearest nest surface %.2f mm, at tilt %+.0f (point %s)'
              % (lab, worst[0], worst[1], np.round(worst[2], 1)))
        if dx == 2.5:
            record('lens_vs_nest', float(worst[0]))
        tip = 29.0 + dx
        for t in (B.TILT_DOWN, 0, 90, B.TILT_UP):
            print('    view cone %.0f deg @ tilt %+4.0f from tip X %.1f: nest depth in view %.3f mm'
                  % (V_HALF, t, tip, view_depth(B.fork, tip, t)))
        ball = lambda p: np.minimum(B.ball_plus(p), B.ball_minus(p))
        print('    view cone vs MY ball hole: %.3f mm' % view_depth(ball, tip, 0.0, r_max=6.0, dr=0.15))
