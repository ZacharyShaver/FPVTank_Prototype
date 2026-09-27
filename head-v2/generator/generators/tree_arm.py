"""Tree-housing test arm: the servo-side branch of the organic fork, as a printable rig.

Same frame as ball2.py: X forward, Y along the tilt axis (+Y = servo side), Z up
from the deck, mm. Built as a signed-distance field and meshed with marching
cubes (numpy + scikit-image). Writes STLs into ../tree-arm-test/.

Scratch-quality concept geometry, like the other generators. Servo and horn
dimensions are DATASHEET/GENERIC, not measured -- measure yours and edit below.
"""
import os
import struct
import numpy as np
from skimage import measure

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, '..', 'tree-arm-test')
os.makedirs(OUT, exist_ok=True)

# ---- concept numbers (ball2.py) ----
H = 46.1                     # tilt axis above deck
R_BALL = 29.6
BALL_CLEAR = 2.5             # arm keeps this far off the ball surface
POD_Y0, POD_Y1 = 32.6, 60.0  # pod inboard face .. outboard end (was 54.6; +5.4 so the servo sits fully inside)
POD_R = 22.0                 # Ø44 (was Ø40): the tab span needs it, teardrop top gives the rest
BASE_Z = 10.5                # underside of the panning part in the concept

# ---- MG90D, datasheet (NOT measured) ----
SERVO_W, SERVO_L, SERVO_H = 12.2, 22.8, 22.5
SHAFT_TO_END = 5.9           # shaft centre to the near end of the case
TAB_SPAN, TAB_T = 32.5, 2.5
TAB_FROM_TOP = 6.5           # tab underside distance below the case top (shaft face)
FIT = 0.25                   # clearance per side

SERVO_TOP_Y = 36.0           # case top (shaft face) -- boss and horn stick out inboard of this

def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)

def box(p, lo, hi):
    c = (np.array(lo) + np.array(hi)) / 2; e = (np.array(hi) - np.array(lo)) / 2
    q = [np.abs(p[i] - c[i]) - e[i] for i in range(3)]
    out = np.sqrt(sum(np.maximum(qi, 0) ** 2 for qi in q))
    return out + np.minimum(np.maximum(np.maximum(q[0], q[1]), q[2]), 0)

def rbox(p, lo, hi, r):
    lo = np.array(lo) + r; hi = np.array(hi) - r
    return box(p, lo, hi) - r

def cyl_y(p, x, z, r, y0, y1):
    d2 = np.sqrt((p[0] - x) ** 2 + (p[2] - z) ** 2) - r
    dy = np.abs(p[1] - (y0 + y1) / 2) - (y1 - y0) / 2
    return np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dy, 0) ** 2) + np.minimum(np.maximum(d2, dy), 0)

def cyl_z(p, x, y, r, z0, z1):
    d2 = np.sqrt((p[0] - x) ** 2 + (p[1] - y) ** 2) - r
    dz = np.abs(p[2] - (z0 + z1) / 2) - (z1 - z0) / 2
    return np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dz, 0) ** 2) + np.minimum(np.maximum(d2, dz), 0)

def teardrop_pod(p, rnd=3.0):
    """Horizontal Y-axis pod with a 45° pointed top: prints without supports."""
    x, z = p[0], p[2] - H
    r = POD_R - rnd
    circle = np.sqrt(x ** 2 + z ** 2) - r
    diamond = (np.abs(x) + np.abs(z)) / np.sqrt(2) - r
    d2 = np.minimum(circle, np.maximum(diamond, r / np.sqrt(2) - z))   # roof only above the 45° tangent points
    y0, y1 = POD_Y0 + rnd, POD_Y1 - rnd
    dy = np.abs(p[1] - (y0 + y1) / 2) - (y1 - y0) / 2
    return np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dy, 0) ** 2) + np.minimum(np.maximum(d2, dy), 0) - rnd

def branch(p):
    """Organic limb: a tapered, fore-aft-deepened tube along a Bezier from the saddle up into the pod."""
    P = np.array([[0, 8, 13.0], [0, 30, 13.0], [0, 44, 17.0], [0, 44, H - 8]])
    ts = np.linspace(0, 1, 36)
    pts = ((1 - ts) ** 3)[:, None] * P[0] + (3 * (1 - ts) ** 2 * ts)[:, None] * P[1] \
        + (3 * (1 - ts) * ts ** 2)[:, None] * P[2] + (ts ** 3)[:, None] * P[3]
    rad = 6.0 + 5.0 * ts ** 1.5
    XS = 1.7                                   # deeper front-to-back: that's the direction tilt torque bends it
    d = None
    for c, r in zip(pts, rad):
        di = np.sqrt(((p[0] - c[0]) / XS) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2) - r
        d = di if d is None else smin(d, di, 2.0)
    return d

def arm_sdf(p):
    saddle = rbox(p, (-16, -6, BASE_Z), (16, 26, BASE_Z + 4.5), 2.0)          # stub of the saddle (mirror side cut off)
    plate = rbox(p, (-26, -12, BASE_Z - 4.0), (26, 62, BASE_Z + 0.01), 3.0)    # TEST ONLY: bench base plate
    s = smin(saddle, branch(p), 5.0)
    s = smin(s, teardrop_pod(p), 5.0)
    s = np.minimum(s, plate)
    # keep clear of the ball
    s = np.maximum(s, -(np.sqrt(p[0] ** 2 + p[1] ** 2 + (p[2] - H) ** 2) - (R_BALL + BALL_CLEAR)))
    # servo pocket, open outboard. Shaft end DOWN so the long side + a tab go up into the teardrop.
    zb0, zb1 = H - SHAFT_TO_END - FIT, H + (SERVO_L - SHAFT_TO_END) + FIT
    body = box(p, (-SERVO_W / 2 - FIT, SERVO_TOP_Y - FIT, zb0), (SERVO_W / 2 + FIT, POD_Y1 + 1, zb1))
    zc = (zb0 + zb1) / 2
    tab_y = SERVO_TOP_Y + TAB_FROM_TOP
    tabs = box(p, (-SERVO_W / 2 - FIT, tab_y - FIT, zc - TAB_SPAN / 2 - FIT), (SERVO_W / 2 + FIT, POD_Y1 + 1, zc + TAB_SPAN / 2 + FIT))
    boss = np.minimum(cyl_y(p, 0, H, 6.6, POD_Y0 - 1, SERVO_TOP_Y + 0.1),
                      box(p, (-6.6, POD_Y0 - 1, H), (6.6, SERVO_TOP_Y + 0.1, H + 6.0)))
    s = np.maximum(s, -np.minimum(np.minimum(body, tabs), boss))
    # tab screw pilots (M2 thread-forming), into the ledge
    for zz in (zc - 13.75, zc + 13.75):
        s = np.maximum(s, -cyl_y(p, 0, zz, 0.85, tab_y - 8, tab_y + 0.1))
    # wire slot: servo lead exits the case end nearest the ledge -> groove out the back of the pod
    s = np.maximum(s, -box(p, (-26, tab_y + TAB_T, zb1 - 3.5), (0, POD_Y1 + 1, zb1 - 0.5)))
    # plate screw holes, M3 clearance
    for hx, hy in ((-20, -6), (20, -6), (-20, 56), (20, 56)):
        s = np.maximum(s, -cyl_z(p, hx, hy, 1.7, BASE_Z - 5, BASE_Z + 1))
    return s

def hub_sdf(p):
    """TEST ONLY: stand-in for the ball's hub. Captures the horn, carries a 70 mm pointer.
    Pointer points UP at level, so a +-60 deg sweep never swings it into the plate."""
    y0, y1 = 26.0, 31.5                                       # horn face sits at 31.5
    disc = cyl_y(p, 0, H, 15.0, y0, y1)
    ptr = rbox(p, (-3.0, y0, H), (3.0, y0 + 3.0, H + 70.0), 1.0)
    tip = cyl_y(p, 0, H + 66.0, 1.2, y0 - 1, y0 + 4)
    s = np.maximum(np.minimum(disc, ptr), -tip)
    # GENERIC double-arm horn pocket (MEASURE YOUR HORN): 34 long, 6 wide, Ø8 centre, 2.2 deep
    hornc = cyl_y(p, 0, H, 4.2, y1 - 2.2, y1 + 1)
    arms = rbox(p, (-3.1, y1 - 2.2, H - 17.2), (3.1, y1 + 1, H + 17.2), 1.0)
    s = np.maximum(s, -np.minimum(hornc, arms))
    s = np.maximum(s, -cyl_y(p, 0, H, 2.8, y0 - 1, y1 + 1))  # horn-screw access
    return s

def mesh(fn, lo, hi, step):
    xs = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
    X, Y, Z = np.meshgrid(*xs, indexing='ij')
    vol = fn((X, Y, Z))
    verts, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(step, step, step))
    verts += np.array(lo)
    return verts, faces

def write_stl(path, verts, faces):
    tri = verts[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    with open(path, 'wb') as f:
        f.write(b'tree-arm-test'.ljust(80, b' ')); f.write(struct.pack('<I', len(faces)))
        rec = np.zeros(len(faces), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
        rec['n'] = n; rec['v'] = tri
        f.write(rec.tobytes())

if __name__ == '__main__':
    import sys
    step = float(sys.argv[1]) if len(sys.argv) > 1 else 0.35
    v, f = mesh(arm_sdf, (-28, -14, BASE_Z - 5), (28, 64, H + POD_R * 1.45 + 2), step)
    write_stl(os.path.join(OUT, 'tree_arm_servo_side.stl'), v, f)
    print('arm', len(f), 'tris', v.min(0).round(1), v.max(0).round(1))
    v, f = mesh(hub_sdf, (-17, 24, H - 18.5), (17, 34, H + 72.0), step)
    write_stl(os.path.join(OUT, 'tree_arm_test_hub.stl'), v, f)
    print('hub', len(f), 'tris', v.min(0).round(1), v.max(0).round(1))
