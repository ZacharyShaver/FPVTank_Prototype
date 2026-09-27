"""Variant C: no ball. One continuous hood drops over the whole head, with a window for the camera.

The ball was the enclosure AND the moving part -- that is what forced the bearings, the shroud, the
cradle and the rolling loop. Here nothing large rotates, so all of that goes away:

    roots   pan base on the deck (shared with A and B)
    spine   the chassis: pan horn foot, tilt servo cradle, two cheeks carrying the tilt pivots
    yoke    the camera cradle -- a collar round the IR-cut holder, pivots on the cheeks
    crank   on the tilt servo's shaft
    rod     crank -> yoke: a four-bar in the XZ plane, so the servo can lie flat in the neck
    hood    ONE continuous organic shell over all of it, window slot in the nose

The window is the swept union of the camera's view cone over the whole tilt range, so it is exactly
as big as it has to be and no bigger. The lens never leaves the shell.

WIDTH IS SET BY THE CAMERA BOARD, not by the optics. The board sweeps a disc of radius
hypot(-BOARD_X0, BOARD_H/2) about the tilt axis, and a straight pushrod cannot cross that disc, so
the linkage has to run outboard of the board. Everything downstream of BOARD_W follows from that:

    half-width = BOARD_W/2 + rod + crank + clearance + wall

so measuring the real board is worth about 6 mm of head width per 10 mm of board.

    python tree_hood.py [part ...]
"""
import os, json, base64
import numpy as np
from skimage import measure
import tree_parts as A
from tree_parts import (smin, box, rbox, _cyl, cyl_x, cyl_y, cyl_z, U,
                        sample, project, unfold, decimate, report, quiet)

D = A.D
OUT = os.path.join(D, '..', 'tree-hood')

# ------------------------------------------------------------------ frame
H = 50.0                     # tilt axis above the deck top
BASE_Z, PED_R, ROOT_TOP = A.BASE_Z, A.PED_R, A.ROOT_TOP
FOOT_R = 19.0                # spine foot: only has to cover the pan horn and the slide land

# ------------------------------------------------------------------ the camera, x from the TILT AXIS
# ASSUMED -- the same stack as A and B, re-referenced to a tilt axis 16 mm further forward, so the
# swept radius is set by the bezel's front corner (18.7) instead of the whole 33 mm overhang.
BOARD_X0, BOARD_X1 = -8.0, -6.4
BOARD_W, BOARD_H = 36.0, 32.0                  # ASSUMED -- big enough for A's +-14 screw pattern
HOLDER_R, HOLDER_X1 = 10.5, 2.6
BEZEL_R, BEZEL_X1 = 8.5, 16.6
LENS_R = 6.2
SWEEP_R = float(np.hypot(BEZEL_X1, BEZEL_R))            # 18.65 -- the bezel's front corner
BOARD_SWEEP = float(np.hypot(BOARD_X0, BOARD_H / 2))    # 17.89 -- the disc the board sweeps
TILT_LO, TILT_HI = -35.0, 40.0                 # look down 35, up 40

# view cone: ASSUMED 65 x 50 deg, inflated ~15% here so build tolerance cannot vignette it
FOV_H, FOV_V = 75.0, 58.0
PUPIL_X = 14.0

# ------------------------------------------------------------------ tilt four-bar (link7.py)
# transmission angle >= 51.6 deg, 92.5 deg of servo travel for 75 deg of tilt (+-46 of its +-60).
# The anchor is kept forward of x = -2.8 through the whole sweep so the cheeks can run down-BACK
# from the pivot to the spine without ever meeting it.
LK_A, LK_B, LK_TH0 = 14.0, 16.0, 295.0         # servo crank, yoke arm, yoke arm angle at tilt 0
LK_SX, LK_SZ = -8.0, -27.0                     # servo shaft, relative to the tilt axis
LK_L, LK_BR = 16.5, +1.0                       # rod length, solution branch
SX, SZ = LK_SX, H + LK_SZ                      # servo shaft, absolute
ANCHOR = (LK_B * np.cos(np.radians(LK_TH0)), LK_B * np.sin(np.radians(LK_TH0)))   # in the yoke frame

# ------------------------------------------------------------------ the width chain, outward from Y=0
# Nothing fixed can sit inside the board's swept disc, and no straight pushrod can cross it either
# (link8.py / link9.py: zero solutions), so the pivot cheeks AND the linkage all go outboard of the
# board. That makes BOARD_W the single number the head's width is built on.
CHEEK_Y0, CHEEK_Y1 = BOARD_W / 2 + 0.8, BOARD_W / 2 + 3.3    # 18.8 .. 21.3  pivot cheeks
PIVOT_R = 5.0                                  # yoke pivot boss, reaches CHEEK_Y0 - 0.4
ROD_Y0, ROD_Y1 = CHEEK_Y1 + 0.4, CHEEK_Y1 + 3.0              # 21.7 .. 24.3
CRANK_Y0, CRANK_Y1 = ROD_Y1 + 0.2, ROD_Y1 + 3.4              # 24.5 .. 27.7
HALF_IN = CRANK_Y1 + 0.5                       # 28.2
WALL = 2.4
HALF_OUT = HALF_IN + WALL                      # 30.6 -> the head is 61.2 wide at BOARD_W 36
RND = 3.0                                      # hood corner rounding

SERVO_W, SERVO_L, S2E = A.SERVO_W, A.SERVO_L, A.SHAFT_TO_END
SERVO_H = 22.5                                 # case depth along the shaft
SERVO_SY = CRANK_Y0 - 0.4                      # shaft face; the case runs SERVO_SY - SERVO_H .. SERVO_SY
SVX0, SVX1 = SX - S2E, SX + SERVO_L - S2E      # case, along X
TAB_SPAN, TAB_FROM_TOP, TAB_PITCH, FIT = A.TAB_SPAN, A.TAB_FROM_TOP, A.TAB_PITCH, A.FIT
TAB_Y = SERVO_SY - TAB_FROM_TOP                # tab flange: screws land here, driven from +Y
PLATE_Y0, PLATE_Y1 = TAB_Y - 2.5 - 4.0, TAB_Y - 2.0   # servo mount plate: the tab flange seats on it
M2_PILOT, M2_CLEAR, M3_CLEAR, M3_PILOT = A.M2_PILOT, A.M2_CLEAR, A.M3_CLEAR, 1.35
HORN_L, HORN_W, HORN_C, HORN_D = A.HORN_L, A.HORN_W, A.HORN_C, A.HORN_D
RIBBON_W, RIBBON_T = A.RIBBON_W, A.RIBBON_T    # ASSUMED -- measure the spare Arducam FPC
PIN_R = 1.1                                    # M2 link pins

TAIL_SCREW = (H - 14.0, 8.0)                   # hood -> spine back wall (z, |y|), driven along +X
NOSE_SCREW = (H - 26.0, 8.0)                   # hood -> spine front boss (z, |y|), driven along -X


# ------------------------------------------------------------------ kit
def rot_y(p, deg, about=(0.0, H)):
    """Inverse rotation: evaluating part(rot_y(p, t)) gives that part tilted by +t (nose up)."""
    a = np.radians(deg)
    x, z = p[0] - about[0], p[2] - about[1]
    return (x * np.cos(a) + z * np.sin(a) + about[0], p[1], -x * np.sin(a) + z * np.cos(a) + about[1])


def solve_phi(tilt):
    """Servo crank angle, in degrees, that puts the camera at this tilt."""
    a_ = np.array([LK_B * np.cos(np.radians(LK_TH0 + tilt)), LK_B * np.sin(np.radians(LK_TH0 + tilt))])
    d = a_ - np.array([LK_SX, LK_SZ])
    dd = float(np.hypot(*d))
    c = np.clip((dd ** 2 + LK_A ** 2 - LK_L ** 2) / (2 * LK_A * dd), -1, 1)
    return float(np.degrees(np.arctan2(d[1], d[0]) + LK_BR * np.arccos(c)))


def anchor_at(tilt):
    """The rod's yoke end, in world coords, at this tilt."""
    return (LK_B * np.cos(np.radians(LK_TH0 + tilt)), H + LK_B * np.sin(np.radians(LK_TH0 + tilt)))


def crank_tip(tilt):
    phi = np.radians(solve_phi(tilt))
    return SX + LK_A * np.cos(phi), SZ + LK_A * np.sin(phi)


def seg(p, a, b, r, y0, y1):
    """Flat bar of radius r between two XZ points, spanning y0..y1."""
    ux, uz = b[0] - a[0], b[1] - a[1]
    ln = float(np.hypot(ux, uz)); ux, uz = ux / ln, uz / ln
    t = (p[0] - a[0]) * ux + (p[2] - a[1]) * uz
    perp = np.abs((p[0] - a[0]) * uz - (p[2] - a[1]) * ux) - r
    return _cyl(perp, np.maximum(np.maximum(-t, t - ln), np.maximum(p[1] - y1, y0 - p[1])))


# ------------------------------------------------------------------ reference solids (never printed)
def camera(p):
    """The camera as it sits in the yoke frame: board, IR-cut holder, lens barrel."""
    return U(box(p, (BOARD_X0, -BOARD_W / 2, H - BOARD_H / 2), (BOARD_X1, BOARD_W / 2, H + BOARD_H / 2)),
             cyl_x(p, 0, H, HOLDER_R, BOARD_X1, HOLDER_X1),
             cyl_x(p, 0, H, BEZEL_R, HOLDER_X1, BEZEL_X1))


def servo(p):
    return U(box(p, (SVX0, SERVO_SY - SERVO_H, SZ - SERVO_W / 2), (SVX1, SERVO_SY, SZ + SERVO_W / 2)),
             box(p, ((SVX0 + SVX1) / 2 - TAB_SPAN / 2, TAB_Y - 2.5, SZ - SERVO_W / 2),
                 ((SVX0 + SVX1) / 2 + TAB_SPAN / 2, TAB_Y, SZ + SERVO_W / 2)))


def view_cone(p, tilt):
    a = np.radians(tilt); ca, sa = np.cos(a), np.sin(a)
    qx, qy, qz = p[0] - PUPIL_X * ca, p[1], p[2] - (H + PUPIL_X * sa)
    along = qx * ca + qz * sa
    up = -qx * sa + qz * ca
    cone = np.hypot(qy / np.tan(np.radians(FOV_H / 2)), up / np.tan(np.radians(FOV_V / 2))) - np.maximum(along, 0)
    return np.maximum(cone * 0.7, -along)


def window(p, n=41):
    return U(*[view_cone(p, t) for t in np.linspace(TILT_LO, TILT_HI, n)])


# ------------------------------------------------------------------ parts
def roots(p, features=True):
    return A.roots(p, features)


def cheeks(p, y0, y1, grow=0.0):
    """The two plates carrying the tilt pivots. They stop above the servo, and stay INBOARD of the
    board -- the board is 36 wide, so a cheek outboard of it would cost 5 mm of head width."""
    m = (p[0], np.abs(p[1]), p[2])
    ax, az, bx, bz = 0.0, H, -20.5, H - 17.0        # pivot -> the spine's back wall
    ux, uz = bx - ax, bz - az
    ln = float(np.hypot(ux, uz)); ux, uz = ux / ln, uz / ln
    t = np.clip((m[0] - ax) * ux + (m[2] - az) * uz, 0, ln)
    d2 = np.hypot(m[0] - (ax + t * ux), m[2] - (az + t * uz)) - (5.5 + grow)
    d2 = smin(d2, np.hypot(m[0] - ax, m[2] - az) - (9.0 + grow), 4.0)
    return _cyl(d2, np.maximum(m[1] - y1, y0 - m[1]))


def spine(p, features=True):
    """The chassis: pan horn foot, tilt servo cradle, and the two cheeks that carry the tilt pivots."""
    floor = rbox(p, (SVX0 - 2.0, -13.0, BASE_Z), (SVX1 + 2.0, 13.0, SZ + SERVO_W / 2 + 1.6), 3.0)
    backw = rbox(p, (-23.0, -19.5, BASE_Z), (-14.0, 19.5, H - 13.0), 3.0)   # wide enough to tie both cheeks in
    plate = rbox(p, (SVX0 - 6.0, PLATE_Y0, SZ - SERVO_W / 2 - 8.0), (SVX1 + 4.5, PLATE_Y1, SZ + SERVO_W / 2 + 6.0), 1.8)
    s = smin(cyl_z(p, 0, 0, FOOT_R, BASE_Z, BASE_Z + 5.0), floor, 6.0)
    s = smin(s, backw, 6.0)
    s = smin(s, plate, 3.0)
    s = smin(s, cheeks(p, 0.0, CHEEK_Y1), 8.0)
    for sy in (-NOSE_SCREW[1], NOSE_SCREW[1]):                       # hood mounting bosses, at the nose
        s = smin(s, cyl_x(p, sy, NOSE_SCREW[0], 4.0, SVX1, SVX1 + 3.1), 2.0)
    s = np.maximum(s, np.abs(p[1]) - CHEEK_Y1)
    s = np.maximum(s, BASE_Z - p[2])
    # the cheeks are plates, not a solid block: clear everything between them above the servo cradle
    s = np.maximum(s, -np.maximum(np.abs(p[1]) - CHEEK_Y0,
                                  np.maximum(SZ + SERVO_W / 2 + 0.6 - p[2], -20.0 - p[0])))
    if not features:
        return s
    cuts = [# servo: drops in from above, then the tabs screw to the plate, driven from +Y
            box(p, (SVX0 - FIT, SERVO_SY - SERVO_H - FIT, SZ - SERVO_W / 2 - FIT),
                (SVX1 + FIT, SERVO_SY + 40, SZ + SERVO_W / 2 + FIT)),
            box(p, (SVX0 - 6.5, TAB_Y - 2.5, SZ - SERVO_W / 2 - FIT),
                (SVX1 + 6.5, TAB_Y + FIT, SZ + SERVO_W / 2 + FIT)),
            # pan horn pocket and the pan shaft screw, in the foot
            U(cyl_z(p, 0, 0, HORN_C / 2, BASE_Z - 1, BASE_Z + HORN_D),
              rbox(p, (-HORN_L / 2, -HORN_W / 2, BASE_Z - 1), (HORN_L / 2, HORN_W / 2, BASE_Z + HORN_D), 1.0)),
            cyl_z(p, 0, 0, 2.8, BASE_Z - 1, BASE_Z + 14),
            # ribbon shaft: straddles the pan axis so the twist at pan is free, and no fold anywhere
            rbox(p, (-21.0, -RIBBON_W / 2 - 0.6, BASE_Z - 1), (-15.0, RIBBON_W / 2 + 0.6, H - 8.0), 1.5),
            rbox(p, (-21.5, -RIBBON_W / 2 - 1.2, BASE_Z - 1), (6.0, RIBBON_W / 2 + 1.2, BASE_Z + 4.5), 1.5)]
    for sy in (-1, 1):
        cuts.append(cyl_y(p, 0, H, M3_CLEAR, sy * (CHEEK_Y1 + 1), sy * (CHEEK_Y0 - 2.0)))     # tilt pivots
    for tx in ((SVX0 + SVX1) / 2 - TAB_PITCH / 2, (SVX0 + SVX1) / 2 + TAB_PITCH / 2):
        cuts.append(cyl_y(p, tx, SZ, M2_PILOT, PLATE_Y0 - 0.1, TAB_Y + 10.0))                 # tab screws
        cuts.append(cyl_y(p, tx, SZ, M2_CLEAR, CHEEK_Y0 - 1, CHEEK_Y1 + 1))                   # driver path
    for sy in (-TAIL_SCREW[1], TAIL_SCREW[1]):
        cuts.append(cyl_x(p, sy, TAIL_SCREW[0], M2_PILOT, -25.0, -13.0))                      # hood, tail
        cuts.append(cyl_x(p, sy, NOSE_SCREW[0], M2_PILOT, SVX1 - 2.0, SVX1 + 4.0))            # hood, nose
    return np.maximum(s, -U(*cuts))


def yoke(p, features=True):
    """Camera cradle. It grips the IR-cut holder and nothing else: the board is 36 wide, so anything
    reaching past it would have to be wider than the head. The holder slides in from the back and the
    board bolts to the holder behind it, which also keeps the whole yoke clear of the FPC tail."""
    x0, x1 = BOARD_X1 + 0.2, HOLDER_X1 + 0.4          # entirely in front of the board
    m = (p[0], np.abs(p[1]), p[2])
    collar = np.maximum(cyl_x(p, 0, H, HOLDER_R + 3.2, x0, x1),
                        -cyl_x(p, 0, H, HOLDER_R + 0.35, x0 - 4, x1 + 4))
    gusset = rbox(m, (x0, 0.0, H - 4.5), (x1, CHEEK_Y0 - 0.4, H + 4.5), 2.0)   # collar -> pivot bosses
    boss = cyl_y(p, 0, H, PIVOT_R, -CHEEK_Y0 + 0.4, CHEEK_Y0 - 0.4)
    # the chin reaches down and forward to the rod anchor, then out past the board to the rod's plane
    chin = seg(p, (0.0, H - 11.0), (ANCHOR[0], H + ANCHOR[1]), 3.4, -3.0, CHEEK_Y0 - 0.4)
    chin = smin(chin, cyl_y(p, ANCHOR[0], H + ANCHOR[1], 3.2, -3.0, ROD_Y1 + 1.2), 2.0)
    s = smin(collar, gusset, 2.5)
    s = smin(s, boss, 3.0)
    s = np.maximum(s, np.abs(p[1]) - (CHEEK_Y0 - 0.4))   # flat pivot faces: the blends bulged past them
    s = smin(s, chin, 3.0)
    s = np.maximum(s, -camera(p))                         # never occupy the camera's own volume
    if not features:
        return s
    cuts = [cyl_y(p, 0, H, M3_PILOT, -CHEEK_Y0 + 0.3, CHEEK_Y0 - 0.3),             # pivot screw pilots
            cyl_y(p, ANCHOR[0], H + ANCHOR[1], PIN_R, -4, ROD_Y1 + 2),             # rod pin
            cyl_z(p, (x0 + x1) / 2, 0, M2_CLEAR, H - HOLDER_R - 5, H - HOLDER_R + 1)]   # holder pinch screw
    return np.maximum(s, -U(*cuts))


def crank_at(p, tilt):
    tip = crank_tip(tilt)
    s = smin(cyl_y(p, SX, SZ, HORN_C / 2 + 2.4, CRANK_Y0, CRANK_Y1),
             seg(p, (SX, SZ), tip, 2.6, CRANK_Y0, CRANK_Y1), 1.5)
    return smin(s, cyl_y(p, tip[0], tip[1], 3.0, CRANK_Y0, CRANK_Y1), 1.5)


def rod_at(p, tilt):
    b, a_ = crank_tip(tilt), anchor_at(tilt)
    s = smin(seg(p, b, a_, 2.4, ROD_Y0, ROD_Y1), cyl_y(p, b[0], b[1], 3.2, ROD_Y0, ROD_Y1), 1.5)
    return smin(s, cyl_y(p, a_[0], a_[1], 3.2, ROD_Y0, ROD_Y1), 1.5)


def crank(p, features=True):
    tip = crank_tip(0.0)
    s = crank_at(p, 0.0)
    if not features:
        return s
    horn = U(cyl_y(p, SX, SZ, HORN_C / 2, CRANK_Y0 - 1, CRANK_Y1 + 1),
             rbox(p, (SX - HORN_W / 2, CRANK_Y0 - 1, SZ - HORN_L / 2),
                  (SX + HORN_W / 2, CRANK_Y0 + HORN_D, SZ + HORN_L / 2), 1.0))
    return np.maximum(s, -U(horn, cyl_y(p, tip[0], tip[1], PIN_R, CRANK_Y0 - 1, CRANK_Y1 + 1)))


def rod(p, features=True):
    b, a_ = crank_tip(0.0), anchor_at(0.0)
    s = rod_at(p, 0.0)
    if not features:
        return s
    return np.maximum(s, -U(cyl_y(p, b[0], b[1], PIN_R, ROD_Y0 - 1, ROD_Y1 + 1),
                            cyl_y(p, a_[0], a_[1], PIN_R, ROD_Y0 - 1, ROD_Y1 + 1)))


def hood_profile(x, z, grow):
    """The hood's XZ section: dome over the camera, brow forward over the window, tail back over the
    linkage, skirt down to the spine. It is extruded along Y as a barrel rather than swept as an
    ellipsoid, because an ellipsoid pinches in exactly where the 36 mm board is widest."""
    d = np.hypot(x + 1.5, z - H) - (23.0 + grow)
    d = smin(d, np.hypot(x - 12.0, z - (H + 8.0)) - (10.5 + grow), 7.0)
    d = smin(d, np.hypot(x + 16.0, z - (H - 14.0)) - (14.0 + grow), 9.0)
    d = smin(d, np.hypot(x + 5.5, z - (H - 27.0)) - (23.0 + grow), 9.0)
    return d


def hood_solid(p, grow):
    return _cyl(hood_profile(p[0], p[2], grow - RND), np.abs(p[1]) - (HALF_OUT + grow - RND)) - RND


def hood_shell(p):
    """The hood with no window cut -- the conservative solid for interference checks."""
    return np.maximum(np.maximum(hood_solid(p, 0.0), -hood_solid(p, -WALL)), (BASE_Z + 6.5) - p[2])


def hood(p, features=True):
    """One continuous shell over the whole head. Open underneath -- it drops on last."""
    s = hood_shell(p)
    if not features:
        return np.maximum(s, -window(p))
    cuts = [window(p)]
    for sy in (-TAIL_SCREW[1], TAIL_SCREW[1]):
        cuts.append(cyl_x(p, sy, TAIL_SCREW[0], M2_CLEAR, -34.0, -18.0))
        cuts.append(cyl_x(p, sy, NOSE_SCREW[0], M2_CLEAR, SVX1 + 1.0, 22.0))
    return np.maximum(s, -U(*cuts))


PARTS = {
    'roots': (roots, (-40, -40, -0.5), (40, 40, BASE_Z + 0.5), 0.30, 16000),
    'spine': (spine, (-PED_R - 2, -CHEEK_Y1 - 2, BASE_Z - 0.5), (PED_R + 2, CHEEK_Y1 + 2, H + 12), 0.26, 24000),
    'yoke':  (yoke,  (BOARD_X0 - 8, -CHEEK_Y0 - 2, H - 22), (HOLDER_X1 + 10, ROD_Y1 + 3, H + 18), 0.22, 14000),
    'crank': (crank, (SX - LK_A - 6, CRANK_Y0 - 1.5, SZ - LK_A - 6), (SX + LK_A + 6, CRANK_Y1 + 1.5, SZ + LK_A + 6), 0.16, 4000),
    'rod':   (rod,   (-28, ROD_Y0 - 1.5, SZ - 8), (20, ROD_Y1 + 1.5, H + 6), 0.16, 4000),
    'hood':  (hood,  (-33, -HALF_OUT - 2, BASE_Z + 5.5), (26, HALF_OUT + 2, H + 26), 0.34, 34000),
}

if __name__ == '__main__':
    os.makedirs(os.path.join(OUT, 'fusion'), exist_ok=True)
    names = [a for a in os.sys.argv[1:] if a in PARTS]
    lines, bundle = [], {}
    lo_all = np.array([1e9] * 3); hi_all = -lo_all
    for name, (fn, lo, hi, step, target) in PARTS.items():
        if names and name not in names:
            continue
        f = lambda P: fn(P, True)
        vol = sample(f, lo, hi, step)
        v, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(step,) * 3)
        v_raw = v + np.array(lo)
        v = unfold(project(f, v_raw, step), v_raw, faces)
        with quiet():
            ms, ok = decimate(v, faces, target)
            _, msg = report(ms)
            ms.save_current_mesh(os.path.join(OUT, 'fusion', f'{name}.obj'), save_vertex_normal=False)
            V = ms.current_mesh().vertex_matrix()
            bundle[name] = {'v': base64.b64encode(V.astype('<f4').tobytes()).decode(),
                            'f': base64.b64encode(ms.current_mesh().face_matrix().astype('<u4').tobytes()).decode()}
        lo_all = np.minimum(lo_all, V.min(0)); hi_all = np.maximum(hi_all, V.max(0))
        lines.append(f'fusion/{name}.obj'.ljust(26) + msg)
        print(lines[-1], flush=True)
    if not names:
        open(os.path.join(OUT, 'viewer_parts_c.js'), 'w').write('window.TREEC=' + json.dumps(bundle) + ';')
        open(os.path.join(OUT, 'mesh_report.txt'), 'w').write('\n'.join(lines) + '\n')
    env = f'ENVELOPE {lo_all.round(1)} -> {hi_all.round(1)}  size {(hi_all - lo_all).round(1)}'
    print(env)
