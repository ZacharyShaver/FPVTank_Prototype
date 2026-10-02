"""Interference check for variant B: the ball through its full 180 deg window inside the nest,
the nest against the roots through pan, and every inserted part. Voxel estimate, 0.4 mm grid.
Mirrors tree_parts_check.py."""
import numpy as np
import tree_parts as A
import tree_parts_b as B
from tree_parts import box, U

STEP = 0.4
H = B.H

def overlap(fa, fb, lo, hi):
    xs = [np.arange(lo[i], hi[i], STEP) for i in range(3)]
    X, Y, Z = np.meshgrid(*xs, indexing='ij')
    tot = 0
    for i in range(0, X.shape[0], 16):
        p = (X[i:i + 16], Y[i:i + 16], Z[i:i + 16])
        tot += np.count_nonzero((fa(p) < -0.05) & (fb(p) < -0.05))
    return tot * STEP ** 3

def rot_y(p, deg):
    """+deg = the lens tilts UP. (tree_parts_check.py uses the opposite sign; B is stated the
    way the mouth is specified, so a label here means what it says.)"""
    a = np.radians(deg); x, y, z = p; zr = z - H
    return (x * np.cos(a) + zr * np.sin(a), y, -x * np.sin(a) + zr * np.cos(a) + H)

def rot_z(p, deg):
    a = np.radians(-deg); x, y, z = p
    return (x * np.cos(a) - y * np.sin(a), x * np.sin(a) + y * np.cos(a), z)

ball = lambda p: np.minimum(B.ball_plus(p), B.ball_minus(p))
NEST = ((-46, -40, 9), (36, 40, H + 32))
rows = []
# the whole 180 deg window the nest promises: 35 deg below the horizon to 145 deg up
for tilt in (B.TILT_DOWN, -20, 0, 30, 60, 90, 120, B.TILT_UP):
    rows.append((f'ball @ tilt {tilt:+.0f} vs nest',
                 overlap(lambda p, t=tilt: ball(rot_y(p, t)), B.fork, *NEST)))
rows.append(('nest vs roots', overlap(B.fork, A.roots, (-50, -50, 0), (50, 50, 12))))
for pan in (45, 90):
    rows.append((f'nest @ pan {pan} vs roots',
                 overlap(lambda p, a=pan: B.fork(rot_z(p, a)), A.roots, (-50, -50, 0), (50, 50, 12))))
rows.append(('post vs nest', overlap(B.post, B.fork, (-22, 13, H - 22), (22, 40, H + 22))))
rows.append(('post vs ball', overlap(B.post, ball, (-22, 13, H - 22), (22, 36, H + 22))))
rows.append(('axle vs nest', overlap(B.axle, B.fork, (-12, B.AXLE_Y0 - 1, H - 12), (12, -13, H + 12))))
rows.append(('cap vs nest', overlap(B.cap_minus, B.fork, (-22, B.POD_M_Y1 - 4, H - 22), (22, -20, H + 22))))
rows.append(('cap vs axle', overlap(B.cap_minus, B.axle, (-12, B.POD_M_Y1 - 2, H - 12), (12, -13, H + 12))))
# The tilt servo is a solid object, not just a pocket. The post reaches in past the bearing to
# meet its spline, so it has to stop short of the case -- this row is what caught the post's horn
# pocket sitting 9 mm inside the servo body.
def servo_solid(p):
    # boss and spline are separate now: the boss is measured 5.0 tall, the spline stands 4.0 off it.
    # The boss has to be narrower than the horn's 7.0 bore, which swallows it -- 6.9 is the ceiling.
    return U(box(p, (-B.SW / 2, B.SERVO_Y0, H - B.S2S), (B.SW / 2, B.SERVO_Y1, H + B.SL - B.S2S)),
             B.cyl_y(p, 0, H, 3.45, B.SERVO_Y1, B.SERVO_Y1 + B.BOSS_H),
             B.cyl_y(p, 0, H, 3.0, B.SERVO_Y1 + B.BOSS_H, B.SERVO_Y1 + B.SPLINE_STACK))

def horn_solid(p):
    # the disc, plus the hub that stands proud of it on the SERVO side and reaches back over the boss
    return U(B.cyl_y(p, 0, H, B.HORN_L_B / 2, B.POST_IN, B.POST_IN + B.HORN_D_B),
             B.cyl_y(p, 0, H, B.HORN_HUB_D / 2, B.POST_IN - (B.HORN_HUB_H - B.HORN_D_B), B.POST_IN))

rows.append(('post vs tilt servo', overlap(B.post, servo_solid, (-16, 14, H - 20), (16, 30, H + 20))))
rows.append(('horn vs ball', overlap(horn_solid, ball, (-12, 20, H - 12), (12, 30, H + 12))))
rows.append(('horn vs nest', overlap(horn_solid, B.fork, (-12, 20, H - 12), (12, 30, H + 12))))
# The camera was never a solid in this model -- only a flat board box used to cut the rails -- which
# is why nothing caught the axle sitting 1.95 mm inside it. Board plus the lens end, as one object.
def camera_solid(p):
    # The lens end runs to BOARD_X1 + CAM_STANDOFF, not to BEZEL_X0. It used to stop at
    # BEZEL_X0 = 26.0, which quietly assumed a 16.4 mm stand-off; Zach measured 19.0 on
    # 2026-09-19, so the real lens tip is at X 29.0 and every row below now sees it.
    return U(box(p, (B.BOARD_X0, -B.BOARD_Y, H - 19.5), (B.BOARD_X1, B.BOARD_Y, H + 19.5)),
             box(p, (B.BOARD_X1, -B.CAM_END_W / 2, H - B.CAM_END_W / 2),
                 (B.BOARD_X1 + B.CAM_STANDOFF, B.CAM_END_W / 2, H + B.CAM_END_W / 2)))

rows.append(('camera vs axle', overlap(camera_solid, B.axle, (0, -20, H - 20), (34, -12, H + 20))))
rows.append(('camera vs post', overlap(camera_solid, B.post, (0, 12, H - 20), (34, 36, H + 20))))
rows.append(('camera vs tilt servo', overlap(camera_solid, servo_solid, (0, -20, H - 20), (34, 34, H + 20))))
# THE ROW THAT WAS MISSING. Testing the camera against the axle, the post and the servo but not
# against the BALL left the -Y pad free to run through the board unnoticed -- the pad, the rails,
# the seam rods and the hub stub all live in the ball, and they are what share its space.
rows.append(('camera vs ball_plus', overlap(camera_solid, B.ball_plus, (0, -20, H - 22), (34, 34, H + 22))))
rows.append(('camera vs ball_minus', overlap(camera_solid, B.ball_minus, (0, -20, H - 22), (34, 34, H + 22))))
rows.append(('ball halves vs each other', overlap(B.ball_plus, B.ball_minus, (-33, -2, H - 33), (35, 2, H + 33))))
# the rolling-loop track has to stay open through the nest wall, and clear of the ball at both ends.
# These two rows only prove each cut exists: a cut can't overlap the part it was cut from. They read 0
# while the groove never opened into the track (docs/lessons/2026-09-27-two-clear-cuts-need-not-meet.md).
# Whether the ribbon and the servo plug can actually get through is head-v2/checks/plug_passage.py.
rows.append(('ribbon track vs nest', overlap(B.track, B.fork, *NEST)))
rows.append(('ribbon trough vs nest', overlap(lambda p: B.trough(p, B.TROUGH_W / 2, B.TROUGH_T / 2), B.fork,
                                              (-46, -14, 8), (16, 14, H + 6))))

# Clearance is not the same as a view. The nest stands off far enough that the ball is free to
# spin right round inside it -- what the 180 deg mouth has to guarantee is that nothing blocks the
# LENS. Two separate questions, so two separate rows.
V_HALF = 30.0        # assumed half field of view; the Arducam lens is not measured yet

def _frame(tilt):
    a = np.radians(tilt)
    return (np.array([np.cos(a), 0.0, np.sin(a)]),          # lens axis
            np.array([-np.sin(a), 0.0, np.cos(a)]),         # up, in the tilt plane
            np.array([0.0, 1.0, 0.0]))                      # across the tilt axis

def _depth_in(fn, qs):
    """How far the deepest of these points is inside fn, in mm (0 = all clear)."""
    q = np.asarray(qs)
    pt = (q[:, 0], q[:, 1], q[:, 2] + H)
    return max(0.0, float((-fn(pt)).max()))

def _depth(qs):
    return _depth_in(B.fork, qs)

# The `bezel clear @ tilt` rows are GONE, with the bezel tube itself (2026-09-19). They sampled
# the outer surface of a raised collar that no longer exists; the front is the plain sphere now,
# and `ball @ tilt ... vs nest` already tests every point of it at all eight angles. A row that
# tests a part which is not in the model is worse than no row -- it reads green forever.

def view_clear(tilt):
    ax, up, side = _frame(tilt)
    qs = []
    for half in np.radians(np.arange(0, V_HALF + 0.01, 5)):
        for t in np.radians(np.arange(0, 360, 10)):
            d = ax * np.cos(half) + (up * np.cos(t) + side * np.sin(t)) * np.sin(half)
            # from the LENS TIP, which is a measured position now, not from the front of a
            # bezel that no longer exists. X 29.0 sits 0.5 mm inside the shell's inner face,
            # so the cone is tested through the hole rather than from outside it.
            o = ax * B.LENS_TIP_X
            qs += [o + d * r for r in np.arange(0.5, 60.0, 0.7)]
    return _depth(qs)

def view_clear_ball():
    """Does the ball's OWN hole clip the field of view? Nothing asked this while the aperture
    was a 16 mm bore down a tube; now that the hole is the only aperture, it is the question.
    The lens is fixed in the ball, so tilt does not change it -- one row, not four."""
    ax, up, side = _frame(0.0)
    ball = lambda p: np.minimum(B.ball_plus(p), B.ball_minus(p))
    qs = []
    for half in np.radians(np.arange(0, V_HALF + 0.01, 2.5)):
        for t in np.radians(np.arange(0, 360, 10)):
            d = ax * np.cos(half) + (up * np.cos(t) + side * np.sin(t)) * np.sin(half)
            o = ax * B.LENS_TIP_X
            qs += [o + d * r for r in np.arange(0.2, 6.0, 0.15)]
    return _depth_in(ball, qs)

rows.append((f'view cone {V_HALF:.0f} deg vs the ball hole', view_clear_ball()))
for tilt in (B.TILT_DOWN, 0, 90, B.TILT_UP):
    rows.append((f'view cone {V_HALF:.0f} deg @ tilt {tilt:+.0f}', view_clear(tilt)))

for name, v in rows:
    ray = name.startswith(('bezel', 'view'))
    tol, word = (0.001, 'BLOCKED') if ray else (1.0, 'INTERFERENCE')
    print(f'{name:<32} {v:8.2f} {"mm " if ray else "mm3"}' + ('' if v < tol else f'   <-- {word}'))
