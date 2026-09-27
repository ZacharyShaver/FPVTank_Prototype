"""Tree-housing ball head, split into printable, assemblable parts.

Frame (all parts share it, so the Fusion imports land assembled): mm, X forward,
Y along the tilt axis (+Y = servo side), Z up from the deck top.

Builds every part as a signed-distance field, meshes it (marching cubes),
projects vertices back onto the true surface, repairs + decimates with
pymeshlab, and writes:

  tree-parts/print/<part>.stl        fine mesh, PRINT orientation (flat face on the bed)
  tree-parts/fusion/<part>.obj       light mesh, ASSEMBLY frame, all features
  tree-parts/fusion/<part>_blank.obj light mesh, ASSEMBLY frame, organic body only --
                                     add the pockets/holes as native Fusion features
  tree-parts/features.md             every cut, with position and size, for doing that

Run from anywhere:  python tree_parts.py [part ...]
Needs numpy, scikit-image, pymeshlab.

Scratch-quality concept geometry like the other generators. Servo, horn and fit
numbers are DATASHEET/GENERIC until the T2 fit coupons replace them.
"""
import os, sys, io, contextlib
import numpy as np
from skimage import measure

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, '..', 'tree-parts')

# ------------------------------------------------------------------ parameters
# Compaction pass 2026-09-17: 125.4 x 83.2 x 64 -> ~102 x 79 x 58, coil mechanism unchanged.
H = 48.5            # tilt axis above deck (52.1 before; the smaller ball let it come back down)
R_BALL, R_IN = 28.3, 27.1
FLAT_Y = 24.0       # the ball is truncated on both sides: the board is only 36 wide, so the spherical
                    # sides were empty space holding the pods apart. The flats are the hub faces, and
                    # they sit 6 mm clear of the board edge so the horn pocket has a solid hub behind it.
BOARD_X0, BOARD_X1 = 4.0, 5.6          # camera board back / front face (8.5 before: the run behind it shrank)
HOLDER_R, HOLDER_X1 = 10.5, 14.6       # IR-cut holder
BEZEL_R, BEZEL_X0, BEZEL_X1 = 8.5, 24.0, 30.4
LENS_R = 6.2
BALL_CLEAR = 1.5    # fork to ball surface; the bezel sweep is cleared separately, only where it sweeps
BEZEL_SWEEP = 32.4  # sqrt(BEZEL_X1^2 + BEZEL_R^2) + 0.8: the swept radius of the bezel corner
POD_R, POD_RND = 21.5, 3.0             # set by the servo tab span inside the teardrop roof
POD_Y0, POD_Y1 = 24.5, 51.5            # pod inboard face (just off the ball flat) .. outboard face
CAP_T = 1.8
BASE_Z = 10.5       # fork underside
ROOT_TOP = 9.5      # roots top: 1.0 mm air under the fork ...
LAND_R0, LAND_R1 = 15.0, 18.0   # ... except this slide land, which touches at BASE_Z
PED_R = 25.5        # roots pedestal / fork trunk radius (pan servo tabs need it)
LOBE_U, LOBE_A, LOBE_B, LOBE_C = 20.0, 14.0, 6.0, 3.2   # root lobes
DECK_SCREW_R = 30.0

SERVO_W, SERVO_L = 12.2, 22.8   # MG90D datasheet -- MEASURE
SHAFT_TO_END = 5.9
TAB_SPAN, TAB_FROM_TOP, TAB_PITCH = 32.5, 6.5, 27.5
FIT = 0.25
SERVO_TOP_Y = 27.7              # tilt servo case top: the horn boss reaches Y 27.5 out of the ball flat
PAN_TOP_Z = 8.2                 # pan servo case top

HORN_L, HORN_W, HORN_C, HORN_D = 34.4, 6.2, 8.4, 2.7   # generic double-arm horn pocket -- MEASURE
BRG_OD, BRG_ID, BRG_W = 27.1, 20.0, 4.0                # 6704 seat (27.0 nominal, +0.1)
BRG_Y0, BRG_Y1 = -(POD_Y0 + 0.5), -(POD_Y0 + 0.5 + BRG_W)
AXLE_R = 9.95
AXLE_Y0, AXLE_Y1 = -(POD_Y1 - 4.0), -17.4              # spool end .. inside the ball socket
RIBBON_W, RIBBON_T = 16.0, 0.3  # ASSUMED -- measure the spare Arducam FPC; everything below scales off it
SLOT_W, SLOT_T = RIBBON_W + 1.2, 2.0                   # ribbon slot through the axle and the ball hub
TROUGH_W, TROUGH_T = RIBBON_W + 1.2, 2.2               # enclosed ribbon trough down the -Y pod and stem
TROUGH_Y = -39.0                                       # its centre: the same band the coil sits in
MIN_BEND_R = 3.0                                       # no creases: every ribbon turn is a curve of at least this
LEAD_R, LEAD_XS = 2.6, 1.6                             # servo lead channel: 8.3 x 5.2, fits the plug
CHAMBER_R = 18.8
M2_PILOT, M2_CLEAR, M2_HEAD = 0.85, 1.1, 2.1           # radii
M3_CLEAR = 1.7

ZC = H + (SERVO_L / 2 - SHAFT_TO_END)                  # tilt servo body centre (shaft end DOWN)
TAB_Y = SERVO_TOP_Y + TAB_FROM_TOP
CAP_SERVO_HOLES = [(14.5, -6), (-14.5, -6), (11, 12.5), (-11, 12.5)]   # (x, z-H)
CAP_COIL_HOLES = [(0, 23.6)]
SEAM_RODS = [(-18.0, 13.0), (-18.0, -13.0), (15.0, -19.0)]   # (x, z-H), M2 through +Y into -Y
BRANCH_P = np.array([[0, 13, BASE_Z + 3.5], [0, 26, BASE_Z + 3.5], [0, 36, BASE_Z + 8.5], [0, 36, H - 8]])

# ------------------------------------------------------------------ SDF kit
def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)

def box(p, lo, hi):
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]; e = [(hi[i] - lo[i]) / 2 for i in range(3)]
    q = [np.abs(p[i] - c[i]) - e[i] for i in range(3)]
    return np.sqrt(sum(np.maximum(qi, 0) ** 2 for qi in q)) + np.minimum(np.maximum(np.maximum(q[0], q[1]), q[2]), 0)

def rbox(p, lo, hi, r):
    return box(p, [v + r for v in lo], [v - r for v in hi]) - r

def _cyl(d2, dl):
    return np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dl, 0) ** 2) + np.minimum(np.maximum(d2, dl), 0)

def cyl_y(p, x, z, r, y0, y1):
    return _cyl(np.hypot(p[0] - x, p[2] - z) - r, np.abs(p[1] - (y0 + y1) / 2) - (y1 - y0) / 2)

def cyl_z(p, x, y, r, z0, z1):
    return _cyl(np.hypot(p[0] - x, p[1] - y) - r, np.abs(p[2] - (z0 + z1) / 2) - (z1 - z0) / 2)

def cyl_x(p, y, z, r, x0, x1):
    return _cyl(np.hypot(p[1] - y, p[2] - z) - r, np.abs(p[0] - (x0 + x1) / 2) - (x1 - x0) / 2)

def ring_z(p, r0, r1, z0, z1, rnd):
    d2 = np.abs(np.hypot(p[0], p[1]) - (r0 + r1) / 2) - ((r1 - r0) / 2 - rnd)
    dz = np.abs(p[2] - (z0 + z1) / 2) - ((z1 - z0) / 2 - rnd)
    return _cyl(d2, dz) - rnd

def U(*ds):
    out = ds[0]
    for d in ds[1:]:
        out = np.minimum(out, d)
    return out

def mirror(p):
    return (p[0], np.abs(p[1]), p[2])

def teardrop2d(x, zr, r):
    """Circle with a 45° pointed roof: horizontal bores and pods print without supports."""
    circle = np.hypot(x, zr) - r
    diamond = (np.abs(x) + np.abs(zr)) / np.sqrt(2) - r
    return np.minimum(circle, np.maximum(diamond, r / np.sqrt(2) - zr))

def pod(p, y0=POD_Y0, y1=POD_Y1, r=POD_R, rnd=POD_RND):
    d2 = teardrop2d(p[0], p[2] - H, r - rnd)
    return _cyl(d2, np.abs(p[1] - (y0 + y1) / 2) - ((y1 - y0) / 2 - rnd)) - rnd

def bezier_pts(n=36):
    t = np.linspace(0, 1, n)[:, None]
    P = BRANCH_P
    return (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3], t[:, 0]

def branch(p, xs=1.7):
    pts, t = bezier_pts()
    rad = 6.0 + 5.0 * t ** 1.5
    d = None
    for c, r in zip(pts, rad):
        di = np.sqrt(((p[0] - c[0]) / xs) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2) - r
        d = di if d is None else smin(d, di, 2.0)
    return d

def bezier(P, n=40):
    P = np.asarray(P, float)
    t = np.linspace(0, 1, n)[:, None]
    return (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]

def channel(p, r=None, xs=None):
    """Servo lead channel along the branch centreline."""
    r = LEAD_R if r is None else r
    xs = LEAD_XS if xs is None else xs
    pts, _ = bezier_pts()
    d = None
    for c in pts:
        di = np.sqrt(((p[0] - c[0]) / xs) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2) - r
        d = di if d is None else np.minimum(d, di)
    return d

def tube(p, ctrl, r, xs=1.0, n=40):
    """Round (or X-stretched) tube swept along a cubic Bezier given by 4 control points."""
    d = None
    for c in bezier(ctrl, n):
        di = np.sqrt(((p[0] - c[0]) / xs) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2) - r
        d = di if d is None else np.minimum(d, di)
    return d

# The ribbon's path down the -Y side, as a curve in the XZ plane. The ribbon keeps its width
# along the tilt axis the whole way, so every one of these turns is a free in-plane bend.
TROUGH_PATH = [(-12.0, H - 12.0), (-21.0, H - 26.0), (-20.0, 26.0), (-15.0, BASE_Z - 1.0)]

def trough(p, half_w, perp_r, n=44):
    """Band swept along TROUGH_PATH: circular in XZ, flat across Y (the ribbon's width)."""
    P = np.asarray(TROUGH_PATH, float)
    t = np.linspace(0, 1, n)[:, None]
    pts = (1 - t) ** 3 * P[0] + 3 * (1 - t) ** 2 * t * P[1] + 3 * (1 - t) * t ** 2 * P[2] + t ** 3 * P[3]
    d2 = None
    for cx, cz in pts:
        di = np.hypot(p[0] - cx, p[2] - cz) - perp_r
        d2 = di if d2 is None else np.minimum(d2, di)
    return _cyl(d2, np.abs(p[1] - TROUGH_Y) - half_w)

def horn_pocket_y(p, y0, y1):
    """Double-arm horn, arms along Z, lying in an XZ plane."""
    return U(cyl_y(p, 0, H, HORN_C / 2, y0, y1),
             rbox(p, (-HORN_W / 2, y0, H - HORN_L / 2), (HORN_W / 2, y1, H + HORN_L / 2), 1.0))

def horn_pocket_z(p, z0, z1):
    """Double-arm horn, arms along X, lying in an XY plane."""
    return U(cyl_z(p, 0, 0, HORN_C / 2, z0, z1),
             rbox(p, (-HORN_L / 2, -HORN_W / 2, z0), (HORN_L / 2, HORN_W / 2, z1), 1.0))

def ball_dist(p):
    return np.sqrt(p[0] ** 2 + p[1] ** 2 + (p[2] - H) ** 2)

# ------------------------------------------------------------------ parts
FEATURES = {}   # part -> list of (feature, where, size) for features.md

def roots(p, features=True):
    s = cyl_z(p, 0, 0, PED_R, 0.0, ROOT_TOP)
    for a in np.radians([45, 135, 225, 315]):
        u = p[0] * np.cos(a) + p[1] * np.sin(a) - LOBE_U
        v = -p[0] * np.sin(a) + p[1] * np.cos(a)
        lobe = (np.sqrt((u / LOBE_A) ** 2 + (v / LOBE_B) ** 2 + ((p[2] - 1.2) / LOBE_C) ** 2) - 1.0) * 5.0
        s = smin(s, lobe, 6.0)
    s = np.maximum(np.maximum(s, -p[2]), p[2] - ROOT_TOP)
    s = np.minimum(s, ring_z(p, LAND_R0, LAND_R1, ROOT_TOP - 0.5, BASE_Z, 0.4))
    if not features:
        return s
    cuts = [box(p, (-(SERVO_L - SHAFT_TO_END) - FIT, -SERVO_W / 2 - FIT, -1), (SHAFT_TO_END + FIT, SERVO_W / 2 + FIT, BASE_Z + 1)),
            box(p, (-(SERVO_L / 2 - SHAFT_TO_END) - TAB_SPAN / 2 - FIT, -SERVO_W / 2 - FIT, -1),
                (-(SERVO_L / 2 - SHAFT_TO_END) + TAB_SPAN / 2 + FIT, SERVO_W / 2 + FIT, PAN_TOP_Z - TAB_FROM_TOP))]
    for tx in (-(SERVO_L / 2 - SHAFT_TO_END) - TAB_PITCH / 2, -(SERVO_L / 2 - SHAFT_TO_END) + TAB_PITCH / 2):
        cuts.append(cyl_z(p, tx, 0, M2_PILOT, PAN_TOP_Z - TAB_FROM_TOP - 0.1, PAN_TOP_Z - TAB_FROM_TOP + 6))
    for a in np.radians([45, 135, 225, 315]):
        cuts.append(cyl_z(p, DECK_SCREW_R * np.cos(a), DECK_SCREW_R * np.sin(a), M3_CLEAR, -1, ROOT_TOP + 1))
    return np.maximum(s, -U(*cuts))

FEATURES['roots'] = [
    ('Pan servo body pocket, through', f'X {-(SERVO_L - SHAFT_TO_END) - FIT:.2f}..{SHAFT_TO_END + FIT:.2f}, Y ±{SERVO_W / 2 + FIT:.2f}, Z 0..top', 'shaft on the Z axis'),
    ('Pan servo tab recess, from below', f'X {-(SERVO_L / 2 - SHAFT_TO_END) - TAB_SPAN / 2 - FIT:.2f}..{-(SERVO_L / 2 - SHAFT_TO_END) + TAB_SPAN / 2 + FIT:.2f}, Y ±{SERVO_W / 2 + FIT:.2f}', f'Z 0..{PAN_TOP_Z - TAB_FROM_TOP:.1f}'),
    ('Tab screw pilots ×2 (M2 thread-forming)', f'X {-(SERVO_L / 2 - SHAFT_TO_END) - TAB_PITCH / 2:.2f} and {-(SERVO_L / 2 - SHAFT_TO_END) + TAB_PITCH / 2:.2f}, Y 0, up from Z {PAN_TOP_Z - TAB_FROM_TOP:.1f}', f'Ø{2 * M2_PILOT:.1f} × 6'),
    ('Deck screw holes ×4 (M3 clearance)', f'r {DECK_SCREW_R:.0f} on the 45° diagonals', f'Ø{2 * M3_CLEAR:.1f} through'),
    ('Slide land (keep as solid)', f'ring r {LAND_R0}..{LAND_R1}', f'top at Z {BASE_Z} = fork underside; rest of roots top at Z {ROOT_TOP}'),
]

def fork(p, features=True):
    m = mirror(p)
    s = smin(cyl_z(p, 0, 0, PED_R, BASE_Z, BASE_Z + 6), rbox(p, (-14, -30, BASE_Z), (14, 30, BASE_Z + 11), 2.0), 3.0)
    s = smin(s, branch(m), 5.0)
    s = smin(s, pod(m), 5.0)
    # skirt on the -Y side: it encloses the ribbon trough, and is the cover moulded into the stem
    s = smin(s, np.where(p[1] < 0, trough(p, TROUGH_W / 2 + 1.5, TROUGH_T / 2 + 1.5), 1e3), 3.0)
    s = np.maximum(s, BASE_Z - p[2])
    # swept volume of the tilting ball: the truncated sphere, plus the band the lens bezel corner sweeps
    swept = np.maximum(np.minimum(np.minimum(ball_dist(p) - (R_BALL + BALL_CLEAR),
                                             cyl_y(p, 0, H, BEZEL_SWEEP, -9.5, 9.5)),
                                  cyl_y(p, 0, H, 18.5, -FLAT_Y - 0.5, FLAT_Y + 0.5)),   # the hub discs
                       np.abs(p[1]) - (FLAT_Y + 0.5))
    s = np.maximum(s, -swept)
    if not features:
        return s
    y = p[1]
    plus = y > 0
    cuts = []
    # +Y: tilt servo, shaft end down, dropped in from outboard
    servo = U(box(p, (-SERVO_W / 2 - FIT, SERVO_TOP_Y - FIT, H - SHAFT_TO_END - FIT), (SERVO_W / 2 + FIT, POD_Y1 + 1, H + SERVO_L - SHAFT_TO_END + FIT)),
              box(p, (-SERVO_W / 2 - FIT, TAB_Y - FIT, ZC - TAB_SPAN / 2 - FIT), (SERVO_W / 2 + FIT, POD_Y1 + 1, ZC + TAB_SPAN / 2 + FIT)),
              cyl_y(p, 0, H, 6.6, POD_Y0 - 1.5, SERVO_TOP_Y + 0.1),
              box(p, (-6.6, POD_Y0 - 1.5, H), (6.6, SERVO_TOP_Y + 0.1, H + 6.0)),
              box(p, (-9.6, POD_Y1 - 5.0, ZC - TAB_SPAN / 2 - FIT), (-6.0, POD_Y1 + 1, H + SERVO_L - SHAFT_TO_END + FIT)))   # lead groove
    for zz in (ZC - TAB_PITCH / 2, ZC + TAB_PITCH / 2):
        servo = np.minimum(servo, cyl_y(p, 0, zz, M2_PILOT, TAB_Y - 8, TAB_Y + 0.1))
    for hx, hz in CAP_SERVO_HOLES:
        servo = np.minimum(servo, cyl_y(p, hx, H + hz, M2_PILOT, POD_Y1 - 8, POD_Y1 + 1))
    # -Y: axle hole, 6704 seat, coil chamber (all entered from outboard)
    coil = U(cyl_y(p, 0, H, AXLE_R + 0.45, BRG_Y1, -POD_Y0 + 1.5),
             cyl_y(p, 0, H, BRG_OD / 2, BRG_Y1, BRG_Y0),
             cyl_y(p, 0, H, CHAMBER_R, -POD_Y1 - 1, BRG_Y1))
    for hx, hz in CAP_COIL_HOLES:
        coil = np.minimum(coil, cyl_y(p, hx, H + hz, M2_PILOT, -POD_Y1 - 1, -POD_Y1 + 8))
    cuts.append(np.where(plus, servo, coil))
    # +Y only: servo lead channel down the branch, then a curved run out the back of the saddle
    lead = np.minimum(channel(p), tube(p, [(0, 13, BASE_Z + 3.5), (-8, 13, BASE_Z + 3.5),
                                           (-17, 13, BASE_Z + 4.0), (-26, 13, BASE_Z + 4.5)], LEAD_R, LEAD_XS))
    cuts.append(np.where(plus, lead, 1e3))
    # -Y only: the enclosed ribbon trough, through the skirt added below
    cuts.append(np.where(plus, 1e3, trough(p, TROUGH_W / 2, TROUGH_T / 2)))
    # pan horn, captured in the underside; screw access from above
    cuts.append(horn_pocket_z(p, BASE_Z - 1, BASE_Z + HORN_D))
    cuts.append(cyl_z(p, 0, 0, 2.8, BASE_Z - 1, H))
    return np.maximum(s, -U(*cuts))

FEATURES['fork'] = [
    ('+Y tilt servo body pocket, open outboard', f'X ±{SERVO_W / 2 + FIT:.2f}, Y {SERVO_TOP_Y - FIT:.2f}..{POD_Y1}, Z {H - SHAFT_TO_END - FIT:.2f}..{H + SERVO_L - SHAFT_TO_END + FIT:.2f}', 'shaft end DOWN, shaft on the tilt axis'),
    ('+Y tab slot', f'X ±{SERVO_W / 2 + FIT:.2f}, Y {TAB_Y - FIT:.2f}..{POD_Y1}, Z {ZC - TAB_SPAN / 2 - FIT:.2f}..{ZC + TAB_SPAN / 2 + FIT:.2f}', 'tabs land on the Y ledge'),
    ('+Y spline boss hole', f'Ø13.2 on the tilt axis + 13.2 × 6 slot upward, Y {POD_Y0 - 1.5:.1f}..{SERVO_TOP_Y}', ''),
    ('+Y tab screw pilots ×2', f'X 0, Z {ZC - TAB_PITCH / 2:.2f} and {ZC + TAB_PITCH / 2:.2f}, from Y {TAB_Y:.1f} inboard', f'Ø{2 * M2_PILOT:.1f} × 8'),
    ('+Y servo lead groove', f'X -9.6..-6.0, Y {POD_Y1 - 5:.1f}..{POD_Y1}, full pocket height', 'leads down into the branch channel'),
    ('+Y cap pilots ×4', ', '.join(f'(X {x}, Z {H + z:.1f})' for x, z in CAP_SERVO_HOLES) + f', from Y {POD_Y1}', f'Ø{2 * M2_PILOT:.1f} × 8'),
    ('-Y axle hole', f'Ø{2 * (AXLE_R + 0.45):.1f} on the tilt axis, Y {-POD_Y0 + 1.5:.1f}..{BRG_Y1:.1f}', ''),
    ('-Y 6704 seat', f'Ø{BRG_OD} × {BRG_W}, Y {BRG_Y0:.1f}..{BRG_Y1:.1f}', '2 mm inboard lip holds the outer race'),
    ('-Y coil chamber, open outboard', f'Ø{2 * CHAMBER_R:.1f}, Y {BRG_Y1:.1f}..{-POD_Y1}', ''),
    ('-Y cap pilot', ', '.join(f'(X {x}, Z {H + z:.1f})' for x, z in CAP_COIL_HOLES), f'Ø{2 * M2_PILOT:.1f} × 8'),
    ('+Y servo lead channel', f'elliptical {2 * LEAD_R * LEAD_XS:.1f} × {2 * LEAD_R:.1f} along the branch centreline, then a curved run out the back of the saddle at Y +13', 'servo plug passes; no sharp corner anywhere'),
    ('-Y ribbon trough, enclosed', f'{TROUGH_W:.1f} × {TROUGH_T:.1f} swept down the pod wall and the stem skirt, band centred on Y {TROUGH_Y}', f'every turn an in-plane curve, R >= {MIN_BEND_R}; opens into the coil chamber at the top and downward at Z {BASE_Z}'),
    ('Pan horn pocket, underside', f'{HORN_L} × {HORN_W} arms along X + Ø{HORN_C} centre, {HORN_D} deep from Z {BASE_Z}', 'GENERIC -- measure your horn'),
    ('Pan horn screw access', f'Ø5.6 on the Z axis, through the saddle', ''),
]

def ball_body(p):
    d = ball_dist(p)
    s = np.maximum(np.maximum(d - R_BALL, R_IN - d), np.abs(p[1]) - FLAT_Y)   # shell, truncated both sides
    s = np.minimum(s, cyl_x(p, 0, H, BEZEL_R, BEZEL_X0, BEZEL_X1))            # lens bezel
    s = np.minimum(s, np.maximum(cyl_y(p, 0, H, 18.0, 18.6, FLAT_Y), -p[1]))  # +Y hub: solid behind the horn pocket
    s = np.minimum(s, np.maximum(cyl_y(p, 0, H, 13.0, -FLAT_Y, -18.6), p[1])) # -Y hub: solid around the axle socket
    for sy in (-14.0, 14.0):
        for sz in (-14.0, 14.0):
            s = np.minimum(s, np.maximum(cyl_x(p, sy, H + sz, 2.6, BOARD_X1, 26.0), d - R_IN - 0.6))   # board posts
    for rx, rz in SEAM_RODS:
        s = np.minimum(s, np.maximum(cyl_y(p, rx, H + rz, 2.8, -FLAT_Y, FLAT_Y), d - R_IN - 0.6))      # seam screw rods
    return s

def ball_cuts(p):
    cuts = [cyl_x(p, 0, H, LENS_R, 0.0, 40.0),                                             # lens
            cyl_x(p, 2.7, H + 20.5, 3.0, 12.0, 40.0),                                      # light sensor window
            horn_pocket_y(p, FLAT_Y - HORN_D, FLAT_Y + 1),
            np.maximum(cyl_y(p, 0, H, AXLE_R + 0.1, -FLAT_Y - 1, -17.8), (p[2] - H) - 8.05),   # axle D socket
            box(p, (-SLOT_W / 2, -FLAT_Y - 1, H - SLOT_T / 2), (SLOT_W / 2, -8.0, H + SLOT_T / 2))]
    for hz in (-10.0, 10.0):
        cuts.append(cyl_y(p, 0, H + hz, M2_PILOT, FLAT_Y - 7, FLAT_Y + 0.5))               # horn screws
    for sy in (-14.0, 14.0):
        for sz in (-14.0, 14.0):
            cuts.append(cyl_x(p, sy, H + sz, M2_PILOT, BOARD_X1 - 0.1, BOARD_X1 + 5.5))    # board post pilots
    for rx, rz in SEAM_RODS:
        y_out = np.sqrt(R_BALL ** 2 - rx ** 2 - rz ** 2)
        cuts.append(np.where(p[1] > 0,
                             U(cyl_y(p, rx, H + rz, M2_CLEAR, -1, FLAT_Y), cyl_y(p, rx, H + rz, M2_HEAD, y_out - 2.2, FLAT_Y)),
                             cyl_y(p, rx, H + rz, M2_PILOT, -10.0, 1)))
    return U(*cuts)

def ball_plus(p, features=True):
    s = np.maximum(ball_body(p), -p[1])
    return np.maximum(s, -ball_cuts(p)) if features else s

def ball_minus(p, features=True):
    s = np.maximum(ball_body(p), p[1])
    return np.maximum(s, -ball_cuts(p)) if features else s

FEATURES['ball_plus'] = [
    ('Lens hole', f'Ø{2 * LENS_R:.1f} along X on the tilt axis', 'through the bezel'),
    ('Light-sensor window', f'Ø6 along X at Y 2.7, Z {H + 20.5:.1f}', ''),
    ('Board post pilots ×2 (this half)', f'Y +14, Z {H - 14:.1f} / {H + 14:.1f}, from X {BOARD_X1} forward', f'Ø{2 * M2_PILOT:.1f} × 6; board back face at X {BOARD_X0}, front at {BOARD_X1}'),
    ('Horn pocket', f'{HORN_L} × {HORN_W} arms along Z + Ø{HORN_C} centre, {HORN_D} deep into the ball flat at Y {FLAT_Y}', 'GENERIC -- measure your horn'),
    ('Horn screw pilots ×2', f'X 0, Z {H - 10:.1f} / {H + 10:.1f}', f'Ø{2 * M2_PILOT:.1f} × 6'),
    ('Seam screw holes ×3 (M2 clearance + head counterbore)', ', '.join(f'(X {x}, Z {H + z:.1f})' for x, z in SEAM_RODS), f'Ø{2 * M2_CLEAR:.1f} through, Ø{2 * M2_HEAD:.1f} × 2.2 from outside'),
]
FEATURES['ball_minus'] = [
    ('Lens hole', f'Ø{2 * LENS_R:.1f} along X on the tilt axis', ''),
    ('Board post pilots ×2 (this half)', f'Y -14, Z {H - 14:.1f} / {H + 14:.1f}, from X {BOARD_X1} forward', f'Ø{2 * M2_PILOT:.1f} × 6'),
    ('Axle D-socket', f'Ø{2 * (AXLE_R + 0.1):.1f}, flat on top at Z axis+8.05, Y {-FLAT_Y}..-17.8', 'keys the axle so the coil turns with the ball'),
    ('Ribbon slot', f'{SLOT_W} × {SLOT_T} (width along X), Y {-FLAT_Y}..-8', ''),
    ('Seam screw pilots ×3', ', '.join(f'(X {x}, Z {H + z:.1f})' for x, z in SEAM_RODS), f'Ø{2 * M2_PILOT:.1f} × 10 from the seam'),
]

def axle(p, features=True):
    s = cyl_y(p, 0, H, AXLE_R, AXLE_Y0, AXLE_Y1)
    s = np.maximum(s, -np.maximum(7.95 - (p[2] - H), (-FLAT_Y - 0.1) - p[1]))          # D flat (top), inside the socket
    if not features:
        return s
    slot = box(p, (-SLOT_W / 2, AXLE_Y0 + 1.5, H - SLOT_T / 2), (SLOT_W / 2, AXLE_Y1 + 5, H + SLOT_T / 2))
    exit_slit = box(p, (-0.6, AXLE_Y0 + 1.5, H - AXLE_R - 1), (0.6, AXLE_Y0 + 17.5, H))
    return np.maximum(s, -U(slot, exit_slit))

FEATURES['axle'] = [
    ('Ribbon slot', f'{SLOT_W} × {SLOT_T} (width along X), Y {AXLE_Y0 + 1.5:.1f}..{AXLE_Y1 + 5:.1f} (open at the ball end)', ''),
    ('Coil exit slit', f'1.2 wide in X, Y {AXLE_Y0 + 1.5:.1f}..{AXLE_Y0 + 17.5:.1f}, from the slot out through the -Z wall', 'ribbon folds 90° here and starts the coil'),
    ('D flat', f'top, at Z axis+7.95, Y {-FLAT_Y - 0.1:.1f}..{AXLE_Y1}', ''),
]

def cap_servo(p, features=True):
    d2 = teardrop2d(p[0], p[2] - H, POD_R - 1.0) - 1.0
    s = _cyl(d2, np.abs(p[1] - (POD_Y1 + 0.2 + CAP_T / 2)) - CAP_T / 2)
    if not features:
        return s
    return np.maximum(s, -U(*[cyl_y(p, x, H + z, M2_CLEAR, POD_Y1, POD_Y1 + 4) for x, z in CAP_SERVO_HOLES]))

def cap_coil(p, features=True):
    d2 = teardrop2d(p[0], p[2] - H, POD_R - 1.0) - 1.0
    face = -(POD_Y1 + 0.2)
    s = _cyl(d2, np.abs(p[1] - (face - CAP_T / 2)) - CAP_T / 2)
    ring = _cyl(np.abs(np.hypot(p[0], p[2] - H) - (CHAMBER_R - 0.5)) - 0.3, np.abs(p[1] - (face + 0.75)) - 0.75)
    stub = cyl_y(p, 0, H, 3.0, face, AXLE_Y0 + 0.3)                                   # stops the axle walking out
    s = U(s, ring, stub)
    if not features:
        return s
    return np.maximum(s, -U(*[cyl_y(p, x, H + z, M2_CLEAR, face - 4, face + 1) for x, z in CAP_COIL_HOLES]))

FEATURES['cap_servo'] = [('Screw holes ×4 (M2 clearance)', ', '.join(f'(X {x}, Z {H + z:.1f})' for x, z in CAP_SERVO_HOLES), f'Ø{2 * M2_CLEAR:.1f}')]
FEATURES['cap_coil'] = [('Screw hole (M2 clearance)', ', '.join(f'(X {x}, Z {H + z:.1f})' for x, z in CAP_COIL_HOLES), f'Ø{2 * M2_CLEAR:.1f}; spigot ring locates it, stub stops the axle walking out')]

# name: (sdf, bbox lo, bbox hi, grid step, print transform, fusion faces blank/full, print face cap)
def rx(sign):
    """Rotate about X by ±90°: sign=+1 maps +Y up, sign=-1 maps -Y up."""
    return lambda v: np.c_[v[:, 0], -sign * v[:, 2], sign * v[:, 1]]

PARTS = {
    'roots':      (roots,      (-40, -40, -0.5), (40, 40, BASE_Z + 0.5), 0.28, lambda v: v, (8000, 16000)),
    'fork':       (fork,       (-30, -53, BASE_Z - 0.5), (30, 53, H + POD_R * 1.5 + 1), 0.30, lambda v: v, (14000, 24000)),
    'ball_plus':  (ball_plus,  (-31, -0.5, H - 30.5), (33, 25.5, H + 30.5), 0.22, rx(+1), (9000, 18000)),
    'ball_minus': (ball_minus, (-31, -25.5, H - 30.5), (33, 0.5, H + 30.5), 0.22, rx(-1), (9000, 18000)),
    'axle':       (axle,       (-10.5, AXLE_Y0 - 1, H - 10.5), (10.5, AXLE_Y1 + 1, H + 10.5), 0.15, rx(-1), (2500, 5000)),
    'cap_servo':  (cap_servo,  (-23, POD_Y1 - 0.5, H - 23), (23, POD_Y1 + CAP_T + 1, H + 33), 0.15, rx(-1), (2000, 3500)),
    'cap_coil':   (cap_coil,   (-23, -POD_Y1 - CAP_T - 1, H - 23), (23, AXLE_Y0 + 1.5, H + 33), 0.15, rx(+1), (2500, 4500)),
}

# ------------------------------------------------------------------ meshing
def sample(fn, lo, hi, step):
    xs = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
    vol = np.empty((len(xs[0]), len(xs[1]), len(xs[2])), np.float32)
    Y, Z = np.meshgrid(xs[1], xs[2], indexing='ij')
    for i0 in range(0, len(xs[0]), 16):
        xx = xs[0][i0:i0 + 16]
        vol[i0:i0 + len(xx)] = fn((xx[:, None, None] + 0 * Y[None], np.broadcast_to(Y, (len(xx),) + Y.shape),
                                   np.broadcast_to(Z, (len(xx),) + Z.shape)))
    vol[0], vol[-1], vol[:, 0], vol[:, -1], vol[:, :, 0], vol[:, :, -1] = 1, 1, 1, 1, 1, 1   # always closed
    return vol

def project(fn, v, step, iters=3):
    """Newton-project marching-cubes vertices onto the zero set: cuts the grid error to near zero on smooth areas."""
    e = step * 0.25
    for _ in range(iters):
        P = (v[:, 0], v[:, 1], v[:, 2])
        f = fn(P)
        g = np.stack([(fn((v[:, 0] + e, v[:, 1], v[:, 2])) - fn((v[:, 0] - e, v[:, 1], v[:, 2]))) / (2 * e),
                      (fn((v[:, 0], v[:, 1] + e, v[:, 2])) - fn((v[:, 0], v[:, 1] - e, v[:, 2]))) / (2 * e),
                      (fn((v[:, 0], v[:, 1], v[:, 2] + e)) - fn((v[:, 0], v[:, 1], v[:, 2] - e))) / (2 * e)], 1)
        g2 = (g ** 2).sum(1)
        ok = g2 > 0.25                               # skip creases, where the gradient is ambiguous
        stepv = np.zeros_like(v)
        stepv[ok] = -(f[ok] / g2[ok])[:, None] * g[ok]
        n = np.linalg.norm(stepv, axis=1, keepdims=True)
        stepv *= np.minimum(1, (step * 0.5) / np.maximum(n, 1e-12))
        v = v + stepv
    return v

def quiet():
    return contextlib.redirect_stderr(io.StringIO())

def mesh_set(v, f):
    import pymeshlab as ml
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(vertex_matrix=np.asarray(v, np.float64), face_matrix=np.asarray(f, np.int32)))
    return ms

def self_intersections(ms):
    try:
        ms.compute_selection_by_self_intersections_per_face()
        n = ms.current_mesh().selected_face_number()
        ms.set_selection_none()
        return n
    except Exception:
        return 0

def tidy(ms):
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_null_faces()
    ms.meshing_remove_unreferenced_vertices()
    ms.meshing_repair_non_manifold_edges()
    ms.meshing_repair_non_manifold_vertices()
    ms.meshing_close_holes(maxholesize=30)          # marching cubes leaves the odd 3-edge pinhole at crossing cuts
    ms.meshing_re_orient_faces_coherently()
    if ms.get_geometric_measures().get('mesh_volume', 0) < 0:
        ms.meshing_invert_face_orientation(forceflip=True)

def is_clean(ms):
    t = ms.get_topological_measures()
    return (t['boundary_edges'] == 0 and t['non_two_manifold_edges'] == 0 and t['non_two_manifold_vertices'] == 0
            and t['connected_components_number'] == 1 and self_intersections(ms) == 0)

def decimate(v, f, target):
    """Quadric decimation that keeps flat faces flat (planar quadric), in passes, and retries with
    gentler settings / more faces until the result is watertight, manifold, one body, no self-intersections."""
    tries = [(1.00, True), (1.00, False), (1.15, True), (1.15, False), (1.35, False), (1.7, False), (2.2, False)]
    last = None
    for mult, optimal in tries:
        ms = mesh_set(v, f)
        tidy(ms)
        goal = int(target * mult)
        n = ms.current_mesh().face_number()
        while n > goal:
            n = max(goal, n // 3)
            ms.meshing_decimation_quadric_edge_collapse(targetfacenum=n, qualitythr=0.6, preserveboundary=True,
                                                        preservenormal=True, preservetopology=True,
                                                        optimalplacement=optimal, planarquadric=True,
                                                        planarweight=0.002, autoclean=True)
        tidy(ms)
        if is_clean(ms):
            return ms, True
        last = ms
    return last, False

def unfold(v, v_raw, faces, rounds=4):
    """Projection can pull a crease vertex onto the wrong face and fold a triangle through its neighbour.
    Put the vertices of any self-intersecting face (plus a ring around them) back where marching cubes had them."""
    for _ in range(rounds):
        ms = mesh_set(v, faces)
        try:
            ms.compute_selection_by_self_intersections_per_face()
        except Exception:
            return v
        if ms.current_mesh().selected_face_number() == 0:
            return v
        ms.apply_selection_dilatation()
        sel = ms.current_mesh().face_selection_array()
        idx = np.unique(faces[sel].ravel())
        v = v.copy()
        v[idx] = v_raw[idx]
    return v

def report(ms):
    t = ms.get_topological_measures()
    g = ms.get_geometric_measures()
    si = self_intersections(ms)
    ok = t['boundary_edges'] == 0 and t['non_two_manifold_edges'] == 0 and t['non_two_manifold_vertices'] == 0 \
        and t['connected_components_number'] == 1 and si == 0
    return ok, (f"{t['faces_number']:>7} faces  watertight={t['boundary_edges'] == 0}  "
                f"manifold={t['non_two_manifold_edges'] == 0 and t['non_two_manifold_vertices'] == 0}  "
                f"bodies={t['connected_components_number']}  self-int={si}  vol={g.get('mesh_volume', float('nan')) / 1000:.2f} cm3")

def build(name, lines):
    fn, lo, hi, step, to_print, (fz_blank, fz_full) = PARTS[name]
    results = {}
    for feats in (True, False):
        f = lambda P, feats=feats: fn(P, feats)
        vol = sample(f, lo, hi, step)
        v, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(step,) * 3)
        v_raw = v + np.array(lo)
        v = project(f, v_raw, step)
        with quiet():
            v = unfold(v, v_raw, faces)
            if feats:
                ms, _ = decimate(v, faces, 250000)         # print mesh: plenty for a slicer, and checked clean
                pv = to_print(ms.current_mesh().vertex_matrix())
                pv = pv - np.array([(pv[:, 0].min() + pv[:, 0].max()) / 2, (pv[:, 1].min() + pv[:, 1].max()) / 2, pv[:, 2].min()])
                pm = mesh_set(pv, ms.current_mesh().face_matrix())
                ok, msg = report(pm)
                pm.save_current_mesh(os.path.join(OUT, 'print', f'{name}.stl'), binary=True)
                lines.append(f'print/{name}.stl'.ljust(30) + msg + ('' if ok else '   <-- CHECK'))
            ms, _ = decimate(v, faces, fz_full if feats else fz_blank)
            ok, msg = report(ms)
            fname = f'{name}.obj' if feats else f'{name}_blank.obj'
            ms.save_current_mesh(os.path.join(OUT, 'fusion', fname), save_vertex_normal=False)
            lines.append(f'fusion/{fname}'.ljust(30) + msg + ('' if ok else '   <-- CHECK'))
            if feats:
                results['viewer'] = (ms.current_mesh().vertex_matrix().astype(np.float32), ms.current_mesh().face_matrix().astype(np.uint32))
    print('\n'.join(lines[-3:]), flush=True)
    return results

def write_features():
    L = ['# Tree head parts: feature table', '',
         'Every pocket, bore and hole in the printable parts, in the shared assembly frame',
         '(mm; X forward, Y along the tilt axis with +Y the servo side, Z up from the deck top).',
         'Import a `_blank.obj`, convert it, then rebuild these as native Fusion features so they stay',
         'editable when the fit coupons change a number. Generated by `generators/tree_parts.py`.', '',
         f'Tilt axis: X 0, Z {H}. Pan axis: the Z axis.', '']
    for part, rows in FEATURES.items():
        L += [f'## {part}', '', '| Feature | Where | Size / note |', '|---|---|---|']
        L += [f'| {a} | {b} | {c} |' for a, b, c in rows]
        L.append('')
    open(os.path.join(OUT, 'features.md'), 'w', encoding='utf-8').write('\n'.join(L))

if __name__ == '__main__':
    os.makedirs(os.path.join(OUT, 'print'), exist_ok=True)
    os.makedirs(os.path.join(OUT, 'fusion'), exist_ok=True)
    names = sys.argv[1:] or list(PARTS)
    lines, viewer = [], {}
    for n in names:
        viewer[n] = build(n, lines).get('viewer')
    write_features()
    open(os.path.join(OUT, 'mesh_report.txt'), 'w').write('\n'.join(lines) + '\n')
    if viewer and all(viewer.values()):
        import json, base64
        bundle = {n: {'v': base64.b64encode(v.tobytes()).decode(), 'f': base64.b64encode(f.tobytes()).decode()} for n, (v, f) in viewer.items()}
        open(os.path.join(OUT, 'viewer_parts.js'), 'w').write('window.TREE=' + json.dumps(bundle) + ';')
