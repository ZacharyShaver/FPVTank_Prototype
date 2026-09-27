"""Driver-access check for variant B.

An interference check says the parts fit. It says nothing about whether you can get a
screwdriver onto each screw at the moment that screw has to be driven -- which is what the
first printed head got wrong twice. This walks a driver shaft back from every screw head, at
the assembly step where that screw goes in, and reports the first thing it hits.

    python tree_parts_b_driver.py
"""
import numpy as np
import tree_parts_b as B
from tree_parts import box, cyl_y, U

H = B.H
SHAFT_R = 2.0        # a small driver: 4 mm shaft. A PH00 handle is fatter, but the shaft is what
                     # has to reach; anything under this is a jeweller's screwdriver at best.
REACH = 32.0         # how far back from the head the shaft has to be clear

# ------------------------------------------------------------------ the solids in play
def board(p):
    return box(p, (B.BOARD_X0, -18, H - 18), (B.BOARD_X1, 18, H + 18))

def servo(p):
    return U(box(p, (-B.SW / 2, B.SERVO_Y0, H - B.S2S), (B.SW / 2, B.SERVO_Y1, H + B.SL - B.S2S)),
             cyl_y(p, 0, H, 3.0, B.SERVO_Y1, B.SERVO_Y1 + B.SPLINE_STACK))

def half_p(p):
    return B.ball_plus(p, True)

def half_m(p):
    return B.ball_minus(p, True)

def nest(p):
    return B.fork(p, True)

# ------------------------------------------------------------------ the walk
def clearance(pos, axis, obstacles):
    """March the driver shaft back from the head. Returns how far it gets before something
    blocks it, and what blocked it."""
    axis = np.asarray(axis, float); axis /= np.linalg.norm(axis)
    # a ring of samples across the shaft, plus its centre
    perp = np.cross(axis, [0, 0, 1.0])
    if np.linalg.norm(perp) < 1e-6:
        perp = np.cross(axis, [1.0, 0, 0])
    perp /= np.linalg.norm(perp)
    perp2 = np.cross(axis, perp)
    offs = [np.zeros(3)] + [(perp * np.cos(a) + perp2 * np.sin(a)) * SHAFT_R
                            for a in np.linspace(0, 2 * np.pi, 12, endpoint=False)]
    for d in np.arange(0.5, REACH + 0.01, 0.5):
        for o in offs:
            q = np.asarray(pos, float) + axis * d + o
            pt = (np.array([q[0]]), np.array([q[1]]), np.array([q[2]]))
            for name, fn in obstacles:
                if fn(pt)[0] < -0.1:
                    return d, name
    return REACH, None

ZC = B.ZC
TAB_Z = (ZC - B.A.TAB_PITCH / 2, ZC + B.A.TAB_PITCH / 2)     # where the servo's tab holes REALLY are

ROWS = []
# --- 1. the camera board has no screws either: it slides into a rail in each half. The two on
#        the +Y side could never be reached -- a line along X through Y +14 never crosses the
#        seam at Y 0, which is the only way into that half.
# --- 2. the tilt servo's two tab screws. It used to have NO screws at all -- "captured by the
#        tab recess and the -Y pad", except the tab recess removed 0.00 mm3 and was never a
#        feature. Each M2 now goes up through the servo's own tab hole into TAB_BOSS_*, driven
#        from the seam side with ball_minus OFF. After the halves close there is no way in, so
#        a blocked row here is a hard fail, not an ordering note.
for _tz, _nm in zip(B.TAB_Z, ('near', ' far')):
    ROWS.append(('tilt servo tab screw (%s, Z %5.2f)' % (_nm, _tz), (0.0, B.TAB_Y, _tz), (0, -1, 0),
                 [('the ball shell', half_p), ('the servo', servo)], True))
# --- 3. ball seam screws, before the ball goes into the nest, and after.
for rx, rz in B.SEAM_RODS:
    y_out = np.sqrt(max(B.R_BALL ** 2 - rx ** 2 - rz ** 2, 1.0))
    pos = (rx, y_out - 2.2, H + rz)
    ROWS.append(('seam screw (X%+5.1f Z%+5.1f) -- ball out of the nest' % (rx, rz), pos, (0, 1, 0),
                 [('the ball shell', half_p)], True))
    ROWS.append(('seam screw (X%+5.1f Z%+5.1f) -- ball already in' % (rx, rz), pos, (0, 1, 0),
                 [('the NEST', nest), ('the ball shell', half_p)], False))
# --- 4. the two flange plates, with the ball in the nest.
for a in np.radians(B.SCREW_A):
    pos = (B.SCREW_R * np.cos(a), B.POD_P_Y1, H + B.SCREW_R * np.sin(a))
    ROWS.append(('post flange screw (%3.0f deg)' % np.degrees(a), pos, (0, 1, 0), [('the NEST', nest)]))
    pos = (B.SCREW_R * np.cos(a), B.POD_M_Y1, H + B.SCREW_R * np.sin(a))
    ROWS.append(('cap flange screw (%3.0f deg)' % np.degrees(a), pos, (0, -1, 0), [('the NEST', nest)]))
# --- 5. the pan horn screw, down the access bore, with and without the ball fitted.
ROWS.append(('pan horn screw -- before the ball', (0.0, 0.0, B.BASE_Z + 14.0), (0, 0, 1),
             [('the NEST', nest)], True))
# As an obstacle the ball is its OUTER ENVELOPE, not the printed shell. Using the two halves here
# meant a shaft rising from a head at Z 24.5 sat inside the hollow cavity and found no material --
# it read "clear" while being somewhere no driver can physically be. Until the -Y pad moved, an
# unrelated feature happened to sit in the ray and hid it. A solid ball is what the driver meets.
def ball_envelope(p):
    return np.maximum(B.ball_dist(p) - B.R_BALL, np.abs(p[1]) - B.FLAT)

ROWS.append(('pan horn screw -- after the ball', (0.0, 0.0, B.BASE_Z + 14.0), (0, 0, 1),
             [('the NEST', nest), ('the ball', ball_envelope)], False))

# Rows carry a flag: True = must be clear. False = EXPECTED to be blocked, and that is precisely
# why the assembly order is what it is. A False row going clear is not a pass, it is a surprise.
print('driver shaft %.1f mm dia, needs %.0f mm of clear run behind the head\n' % (2 * SHAFT_R, REACH))
bad = 0
for row in ROWS:
    name, pos, axis, obs = row[0], row[1], row[2], row[3]
    want = row[4] if len(row) > 4 else True
    d, hit = clearance(pos, axis, obs)
    if want and hit is None:
        print('%-50s  clear' % name)
    elif want:
        bad += 1
        print('%-50s  BLOCKED at %4.1f mm by %s   <-- FIX' % (name, d, hit))
    elif hit is not None:
        print('%-50s  blocked at %4.1f mm by %s (expected -- do it earlier)' % (name, d, hit))
    else:
        bad += 1
        print('%-50s  clear, but was expected to be blocked   <-- CHECK' % name)
print('\n%d problem(s)' % bad)
