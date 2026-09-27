"""Insertion check for variant B.

The interference check says where parts END UP. The driver check says whether a screwdriver can
reach each screw. Neither asks the third question: can the part physically GET to its seat?

That gap hid three separate faults in one day -- the axle sitting inside the camera, the -Y pad
running through the board, and a bearing seat that stepped down to a smaller bore on BOTH sides,
so the bearing could only ever have arrived there by being printed in place.

This slides each inserted part back out along its assembly path and reports the first thing it
hits. A part that cannot come out cannot go in.

    python tree_parts_b_insert.py
"""
import numpy as np
import tree_parts as A
import tree_parts_b as B
from tree_parts import U, cyl_y, box

H = B.H
STEP = 0.45
DT = 0.5

def overlap(fa, fb, lo, hi):
    xs = [np.arange(lo[i], hi[i], STEP) for i in range(3)]
    X, Y, Z = np.meshgrid(*xs, indexing='ij')
    return np.count_nonzero((fa((X, Y, Z)) < -0.05) & (fb((X, Y, Z)) < -0.05)) * STEP ** 3

def shift(fn, d, t):
    return lambda p: fn((p[0] - d[0]*t, p[1] - d[1]*t, p[2] - d[2]*t))

def bearing(y0, y1):
    """The 6704 as a solid ring: OD 27, ID 20."""
    return lambda p: np.maximum(cyl_y(p, 0, H, B.BRG_OD/2 - 0.05, y0, y1),
                                -(np.hypot(p[0], p[2] - H) - A.BRG_ID/2))

def servo_solid(p):
    return U(box(p, (-B.SW/2, B.SERVO_Y0, H - B.S2S), (B.SW/2, B.SERVO_Y1, H + B.SL - B.S2S)),
             cyl_y(p, 0, H, 3.45, B.SERVO_Y1, B.SERVO_Y1 + B.BOSS_H))

def board(p):
    return box(p, (B.BOARD_X0, -B.BOARD_Y, H - 19.5), (B.BOARD_X1, B.BOARD_Y, H + 19.5))

nest = lambda p: B.fork(p, True)
ball = lambda p: np.minimum(B.ball_plus(p), B.ball_minus(p))

#      name                          part                    dir      travel  box (seated)                     obstacles
ROWS = [
  ('6704 into the +Y collar',   bearing(B.BRG_P_Y0, B.BRG_P_Y1),  ( 0, 1, 0),  9.0, (-15, 24, H-15), (15, 36, H+15), [('the NEST', nest)]),
  ('6704 into the -Y collar',   bearing(B.BRG_M_Y1, B.BRG_M_Y0),  ( 0,-1, 0),  9.0, (-15,-36, H-15), (15,-24, H+15), [('the NEST', nest)]),
  ('post in from +Y',           B.post,                           ( 0, 1, 0), 14.0, (-19, 24, H-19), (19, 36, H+19), [('the NEST', nest), ('the ball', ball)]),
  ('axle in from -Y',           B.axle,                           ( 0,-1, 0), 14.0, (-11,-34, H-11), (11,-17, H+11), [('the NEST', nest), ('the ball', ball)]),
  ('cap_minus onto the collar', B.cap_minus,                      ( 0,-1, 0),  8.0, (-19,-36, H-19), (19,-30, H+19), [('the NEST', nest)]),
  ('tilt servo into ball_plus', servo_solid,                      ( 0,-1, 0), 26.0, (-10, -7, H-8),  (10, 25, H+19), [('ball_plus', B.ball_plus)]),
  ('camera board into its rails', board,                          ( 0,-1, 0), 22.0, (  6,  0, H-21), (12, 20, H+21), [('ball_plus', B.ball_plus)]),
]
print('sliding each part back out along its assembly path\n')
bad = 0
for name, part, d, travel, blo, bhi, obstacles in ROWS:
    hit = None
    lo = [blo[i] + min(0, d[i]*travel) - 1 for i in range(3)]
    hi = [bhi[i] + max(0, d[i]*travel) + 1 for i in range(3)]
    for t in np.arange(DT, travel + DT, DT):
        moved = shift(part, d, t)
        for oname, ofn in obstacles:
            if overlap(moved, ofn, lo, hi) > 1.0:
                hit = (t, oname); break
        if hit: break
    if hit:
        bad += 1
        print('  %-30s BLOCKED after %4.1f mm by %s   <-- CHECK' % (name, hit[0] - DT, hit[1]))
    else:
        print('  %-30s clear over %.0f mm' % (name, travel))
print('\n%d problem(s)' % bad)
