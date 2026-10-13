"""Scorpion chassis concept (brainstorm, 2026-10-04): Zach's TEST-PRINT-2 body with the v1 legs bolted on
unmodified, head v2, every electronic part we know of, and the new parts that make room for them.

    python chassis-v2/concept.py            # ~3 min the first time (his body becomes an exact solid once)

Writes chassis-v2/out/: concept.html (the "Scorpion Chassis Concept" page), concept_tools_for_fusion.step
(the CUT_ bodies for his body, in his coordinates) and checks.json (the fit table the page shows).

Frame: his Fusion frame. X forward (toward the lens), Y left, Z up, mm. Nothing here is precise yet: the
legs and his body are placed exactly (by their screw holes); everything new is a concept.
"""
import os, sys, json, base64, glob, time
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))
import config
import cadquery as cq
import pymeshlab as ml
from vox import load_stl, load_obj, _scan

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
R = config.REPO
FF = os.path.join(R, 'chassis-v1', 'from_fusion', 'TEST-PRINT-2_Configuration 1_')
RV = os.path.join(R, 'reference', 'fpv-rover-v2')
G = os.path.join(R, 'head-v2', 'generator', 'pan-coil-b', 'fusion')
FORK = os.path.join(R, 'head-v2', 'generator', 'tree-parts-b', 'fusion', 'fork.obj')
BALL = [os.path.join(config.OUT, 'rev2', k) for k in ('_fig_ball_plus.stl', '_fig_ball_minus_cup.stl')]
PCA = os.path.join(R, 'reference', 'pca9685', 'PCA9685 16-Channel Servo Driver - Adafruit.step')

# ---------------------------------------------------------------- his body (TEST-PRINT-2), as exported
BAND_X0, BAND_X1, BAND_Z0, BAND_Z1 = -87.62, 119.48, 7.4, 57.4
YR, YL = -62.0, 69.5                      # the band's side faces; the pods bolt flat on them
YC = (YR + YL) / 2                        # 3.75
BATT_TOP = 36.0

# ---------------------------------------------------------------- the legs: v1 parts, unmodified
# Placed by their screw holes. The pod's 6 insert holes (file X 73.45/125/176.55, Y 76.5/118.5, on its
# closed face) land on his body's 6 side holes (X -41.56/9.99/61.54, Z 11.4/53.4). The pods go on upside
# down from their print orientation: the only proper (unmirrored) placement that puts both motors at the
# rear (the motor rib is at the drive end) and drops the track side 15 mm below the body (the "high" pod).
def podL(P): return np.stack([P[..., 0] - 115.01, YL + P[..., 2], 129.9 - P[..., 1]], -1)
def podR(P): return np.stack([134.99 - P[..., 0], YR - P[..., 2], 129.9 - P[..., 1]], -1)
# The outer frame bolts onto the pod's open side: its 6 counterbored holes on the pod's 6 bosses, a
# pattern turned 1.83 deg in the pod's file (+ on the left pod, - on the right). Flat face out, posts in.
OF_DEG = {'L': 1.83, 'R': -1.83}
def of_to_pod(P, side):
    x, y, z = P[..., 0], 210.0 - P[..., 1], -P[..., 2]
    a = np.radians(OF_DEG[side]); c, s = np.cos(a), np.sin(a)
    xr = 125 + (x - 125) * c - (y - 105) * s; yr = 110 + (x - 125) * s + (y - 105) * c
    return np.stack([xr, yr, z + 51.0], -1)
POD = {'L': podL, 'R': podR}
def axle(side, end):
    """Sprocket axle centre, pod file coords, from the outer frame's axle holes (file 46.45/203.55, 105)."""
    p = of_to_pod(np.array([[46.45 if end == 'a' else 203.55, 105.0, 0.0]]), side)[0]
    return p[:2]
def drive_end(side):  # the rear (drive) axle: pod file X min on the left pod, X max on the right
    return 'a' if side == 'L' else 'b'

# ---------------------------------------------------------------- the concept's numbers (all guesses)
HX, HY = 100.0, 3.4                       # head pan axis (the old head's Y; X from the placement page)
MEZ_Z0, MEZ_Z1 = 37.5, 40.0               # mezzanine: 1.5 over the battery tops, 2.5 thick
Z0H = MEZ_Z1 + 39.4                       # 79.4: the coil deck. The base's floor stands on the mezzanine
DECK = Z0H + 6.6                          # 86.0: hull deck flush with the well's top: a turret ring
DT = 2.4                                  # hull wall
FENDER = 61.0                             # sponson floor: >= 6 over the track's top run (54.9 at the rear)
SPL, SPR = 125.0, -117.5                  # sponson outer faces (symmetric about YC)
SH_X0, SPLIT, SP_X1 = -102.0, 40.0, 121.0 # sponsons run past both track ends; the shell splits at X 40,
                                          # just behind the head's gear bay (X 43.8)
REAR_X0 = -138.0                          # rear power bay's back face
RAIL_X0, RAIL_X1 = -80.0, 38.0            # accessory rail, on the lift-off shell only, clear of the head's
                                          # 43.7 sweep (needs X < 52)

def T(m, R3=None, t=(0, 0, 0)):
    m = np.asarray(m, float)
    if R3 is not None: m = m @ np.asarray(R3, float).T
    return m + np.asarray(t, float)
def Rz(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a); return [[c, -s, 0], [s, c, 0], [0, 0, 1]]

# ---------------------------------------------------------------- mesh helpers
def tri_obj(path): return load_obj(path)
def cq_tris(shape, tol=0.15):
    v, t = shape.tessellate(tol, 0.3); V = np.array([[p.x, p.y, p.z] for p in v]); return V[np.array(t)]
def cyl_tris(p0, p1, r, n=40):
    """closed cylinder between two points"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); a = p1 - p0; L = np.linalg.norm(a); a /= L
    u = np.cross(a, [0, 0, 1.0] if abs(a[2]) < .9 else [1.0, 0, 0]); u /= np.linalg.norm(u); w = np.cross(a, u)
    th = np.linspace(0, 2 * np.pi, n, endpoint=False); ring = np.cos(th)[:, None] * u + np.sin(th)[:, None] * w
    A = p0 + r * ring; B = p1 + r * ring; out = []
    for i in range(n):
        j = (i + 1) % n
        out += [[A[i], A[j], B[j]], [A[i], B[j], B[i]], [p0, A[j], A[i]], [p1, B[i], B[j]]]
    return np.array(out)
def box_tris(p0, p1):
    s = cq.Workplane('XY').box(*(np.subtract(p1, p0)), centered=False).translate(tuple(p0)).val()
    return cq_tris(s)

def track_loop(circles, y0, y1, t=2.0, lug=2.5, pitch=15.1, lug_len=6.0, step=0.5):
    """the TPU track: the tight loop round the sprockets and rollers (circles = [(x, z, r)]), lugs outside"""
    from scipy.spatial import ConvexHull
    th = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    S = np.vstack([np.c_[x + r * np.cos(th), z + r * np.sin(th)] for x, z, r in circles])
    H = S[ConvexHull(S).vertices]; H = np.vstack([H, H[:1]])                 # counter-clockwise
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(H, axis=0), axis=1))]
    s = np.arange(0, seg[-1], step)
    P = np.c_[np.interp(s, seg, H[:, 0]), np.interp(s, seg, H[:, 1])]
    D = np.roll(P, -1, 0) - np.roll(P, 1, 0); N = np.c_[D[:, 1], -D[:, 0]]; N /= np.linalg.norm(N, axis=1, keepdims=True)
    M = len(P)
    seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
    th_ = t + lug * ((seg % pitch) < lug_len)
    Q = P + N * th_[:, None]
    def v3(p2, y): return np.stack([p2[:, 0], np.full(len(p2), y), p2[:, 1]], -1)
    Ia, Ib, Oa, Ob = v3(P, y0), v3(P, y1), v3(Q, y0), v3(Q, y1); F = []
    for i in range(M):
        j = (i + 1) % M
        F += [[Oa[i], Oa[j], Ob[j]], [Oa[i], Ob[j], Ob[i]], [Ia[i], Ib[j], Ia[j]], [Ia[i], Ib[i], Ib[j]],
              [Ia[i], Ia[j], Oa[j]], [Ia[i], Oa[j], Oa[i]], [Ib[i], Ob[j], Ib[j]], [Ib[i], Ob[i], Ob[j]]]
    return np.array(F)

# ---------------------------------------------------------------- the legs
def legs():
    parts = {}
    podf = {'L': 'inner-frame-left-high-v10.stl', 'R': 'inner-frame-right-high-v10.stl'}
    of = load_stl(os.path.join(RV, 'outer-frame-v13.stl'))
    cogF = load_stl(os.path.join(RV, 'front-main-cog-v13.stl')); cogR = load_stl(os.path.join(RV, 'rear-main-cog-v13.stl'))
    small = load_stl(os.path.join(RV, 'small-cog-v2.stl'))
    crown = load_stl(os.path.join(RV, 'alternate-wheel-mounts', 'big-bevel-gear-41-v13.stl'))
    pin = load_stl(os.path.join(RV, 'alternate-wheel-mounts', 'small-bevel-gear-41-v11.stl'))
    for side in 'LR':
        f = POD[side]
        parts['pod_' + side] = f(load_stl(os.path.join(RV, podf[side])))
        parts['of_' + side] = f(of_to_pod(of, side))
        # rollers: 2 rings on each of the outer frame's 4 posts (file (93.55|156.45, 86|120), Z 4-9 and 9-14)
        rings = []
        for px in (93.55, 156.45):
            for py in (86.0, 120.0):
                for z0 in (4.0, 9.0):
                    m = small - [125, 105, 0] + [px, py, z0]; rings.append(f(of_to_pod(m, side)))
        parts['rollers_' + side] = np.vstack(rings)
        for end in 'ab':
            cx, cy = axle(side, end); rear = end == drive_end(side)
            cog = cogR if rear else cogF; z0 = 14.2 if rear else 20.5
            parts[('cog_rear_' if rear else 'cog_front_') + side] = f(cog - [125, 105, 0] + [cx, cy, z0])
            if rear:
                parts['crown_' + side] = f(crown - [16.21, -44.77, 0] + [cx, cy, 4.8])
        # track: tight round the sprocket tips (r 29.75) and the rollers (r 15), pod z 8..48 = 40 wide
        ca = f(np.array([[*axle(side, 'a'), 28.0]]))[0]; cb = f(np.array([[*axle(side, 'b'), 28.0]]))[0]
        rear_c, front_c = (ca, cb) if ca[0] < cb[0] else (cb, ca)
        circ = [(rear_c[0], rear_c[2], 29.9), (front_c[0], front_c[2], 29.9)]
        for px in (93.55, 156.45):
            for py in (86.0, 120.0):
                c = f(of_to_pod(np.array([[px, py, 9.0]]), side))[0]; circ.append((c[0], c[2], 15.1))
        y0, y1 = sorted([f(np.array([[0, 0, 8.0]]))[0][1], f(np.array([[0, 0, 48.0]]))[0][1]])
        parts['track_' + side] = track_loop(circ, y0, y1)
        # 540 motor: can 36 x 52 on the rear axle's height, flange at the pod's motor rib (X -44), pinion aft
        ym = f(np.array([[0, 0, 16.0]]))[0][1]; zm = rear_c[2]      # 2 mm into the body: 4 hits the band's bottom rim
        parts['motor_' + side] = np.vstack([cyl_tris((-44, ym, zm), (8, ym, zm), 18.0), cyl_tris((8, ym, zm), (13, ym, zm), 14.0),
                                            cyl_tris((-49, ym, zm), (-44, ym, zm), 16.5)])
        pp = pin - [125, 105, 0]; pp = np.stack([-pp[..., 2], pp[..., 1], pp[..., 0]], -1)   # axis along -X
        parts['pinion_' + side] = pp + [-49.5, ym, zm]
    return parts

# ---------------------------------------------------------------- his body with the concept's cuts
CUTS = {  # name: (kind, args) in his frame. He makes these booleans in Fusion; here they show what goes
    'CUT_cross_beam': ('box', (27, -63, 12.5), (40, 71, 53)),            # mid cross beam: Pi + PCA bay
    'CUT_turret_well': ('cyl', (HX, HY), 33.0, MEZ_Z1, 60.0),             # well r31 + 2, old pan boss with it
    'CUT_turret_bay': ('box', (41.8, HY - 27.7, MEZ_Z1), (116.0, HY + 27.7, 60.0)),   # gear bay + 1; leaves your
                                                                      # nose flat at Z 40: the base's front stands on it
    'CUT_pi_box': ('box', (-125, -63, 6), (-87.7, 71, 50)),               # his rear Pi box: becomes the power bay
    'CUT_battery_door': ('box', (-92, -47, 9.5), (-60, 54, 38.0)),        # batteries slide out the back
}
def cut_solid(spec):
    from kit import bx, cyl
    k = spec[0]
    if k == 'box': return bx(spec[1], spec[2])
    (x, y), r, z0, z1 = spec[1], spec[2], spec[3], spec[4]; return cyl('z', (x, y), r, z0, z1)
def body_cut():
    from occ_load import load
    from kit import cut
    from export import rd, wr
    cache = os.path.join(OUT, '_body.brep')
    if not os.path.exists(cache):
        s, info = load(FF + 'Tank_body.stl'); wr(s, cache); print('body solid', info)
    s = rd(cache)
    tools = {k: cut_solid(v) for k, v in CUTS.items()}
    c = cut(s, *tools.values())
    return cq.Shape(c), {k: cq.Shape(v) for k, v in tools.items()}

# ---------------------------------------------------------------- new parts (concept)
def mezzanine():
    """X -72..87: behind your nose structure (X 88+) and clear of the rear end's curve. Posts on your floor
    (top Z 9.8), inside your side rims (Y 62+); the spine stands on your ridge between the packs (top Z 17)."""
    p = cq.Workplane('XY').box(87 + 72, YL - YR - 8, MEZ_Z1 - MEZ_Z0, centered=False).translate((-72, YR + 4, MEZ_Z0))
    p = p.cut(cq.Workplane('XY').box(60, 30, 10).translate((-20, 30, MEZ_Z0)))      # wiring slot: Pi to rear bay
    p = p.cut(cq.Workplane('XY').box(24, 14, 10).translate((70, 40, MEZ_Z0)))       # servo leads, head to PCA
    from probe import hits
    body = load_stl(FF + 'Tank_body.stl')
    for x in (-68.0, -5.0, 83.0):
        for y in (-52.0, 57.0):
            # each post stands on whatever is under it (floor, its end curve, a rib): rays straight down
            ring = [(x, y)] + [(x + 3.9 * np.cos(a), y + 3.9 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 12, endpoint=False)]
            z0 = max(MEZ_Z0 - 1 - min(t for t in hits(body, (px, py, MEZ_Z0 - 1), (0, 0, -1)) if t > 0) for px, py in ring)
            p = p.union(cq.Workplane('XY').circle(4).extrude(MEZ_Z0 - z0).translate((x, y, z0)))
    p = p.union(cq.Workplane('XY').box(136, 3, MEZ_Z0 - 17.0, centered=False).translate((-50, 1.85, 17.0)))  # spine on your ridge
    return p.val()

def rear_bay():
    w = cq.Workplane('XY').box(-87.7 - REAR_X0, YL - YR, DECK - BAND_Z0, centered=False).translate((REAR_X0, YR, BAND_Z0))
    w = w.edges('|Z and <X').fillet(10)
    w = w.faces('>X').shell(-DT)
    w = w.cut(cq.Workplane('XY').box(6, 101, 28.5, centered=False).translate((REAR_X0 - 1, -47, 9.5)))   # battery door
    w = w.union(cq.Workplane('XY').box(48, 101, 2, centered=False).translate((REAR_X0 + 1, -47, 38)))    # shelf over the drawer
    for y, wd in ((-44, 16), (-24, 16), (28, 10), (42, 10)):                         # charge + balance ports
        w = w.cut(cq.Workplane('XY').box(6, wd, 8, centered=False).translate((REAR_X0 - 1, y, 44)))
    for i in range(7):                                                               # UBEC / ESC grille
        w = w.cut(cq.Workplane('XY').box(6, 3, 22, centered=False).translate((REAR_X0 - 1, -20 + 7 * i, 58)))
    # tail clevis: two cheeks on the deck, pin along Y
    for y in (YC - 15, YC + 11):
        w = w.union(cq.Workplane('XZ').circle(9).extrude(-4).translate((-118, y, DECK + 6)))
        w = w.union(cq.Workplane('XY').box(18, 4, 6, centered=False).translate((-127, y, DECK)))
    return w.val()

def door():
    return cq.Workplane('XY').box(3, 100, 27.5, centered=False).translate((REAR_X0 - 3, -46.5, 10)).edges('|X').fillet(2).val()

def shell():
    c = cq.Workplane('XY').box(SPLIT + 86, YL - YR, DECK - BAND_Z1, centered=False).translate((-86, YR, BAND_Z1))
    for y0, y1 in ((YL, SPL), (SPR, YR)):
        s = cq.Workplane('XY').box(SPLIT - SH_X0, y1 - y0, DECK - FENDER, centered=False).translate((SH_X0, y0, FENDER))
        c = c.union(s)
    c = c.edges('|X and >Z and (>Y or <Y)').chamfer(9)
    c = c.faces('<Z').shell(-DT)
    for i in range(8):                                                              # deck vents over the Pi
        c = c.cut(cq.Workplane('XY').box(5, 44, 6).translate((-52 + 10 * i, YC, DECK)))
    for yo in (SPL, SPR):                                                           # louvres in the sponson sides
        for i in range(9):
            c = c.cut(cq.Workplane('XY').box(6, 8, 12).translate((-84 + 15 * i, yo, FENDER + 13)))
    return c.val()

def turret():
    """Outer minus inner (a shell() with several open faces came out solid). Open underneath over your band
    and under the glacis; fenders over the tracks; the deck ring round the well."""
    prof = [(SPLIT, BAND_Z1), (SPLIT, DECK), (134, DECK), (145, 46), (141, 30), (121.5, 27), (121.5, BAND_Z1)]
    def sp_boxes(d, z0):
        return [cq.Workplane('XY').box(SP_X1 - SPLIT - 2 * d, y1 - y0, DECK - d - z0, centered=False)
                .translate((SPLIT + d, y0, z0)) for y0, y1 in ((YL, SPL - d), (SPR + d, YR))]
    o = cq.Workplane('XZ').polyline(prof).close().extrude(-(YL - YR)).translate((0, YR, 0))
    for b in sp_boxes(0, FENDER): o = o.union(b)
    o = o.edges('|X and >Z and (>Y or <Y)').chamfer(9)
    i = cq.Workplane('XZ').polyline(prof).close().offset2D(-DT).extrude(-(YL - YR - 2 * DT)).translate((0, YR + DT, 0))
    o = o.cut(i)
    for b in sp_boxes(DT, FENDER - 3):
        o = o.cut(b.edges('|X and >Z and (>Y or <Y)').chamfer(7.5))
    o = o.cut(cq.Workplane('XY').box(121.5 - SPLIT - 2 * DT, YL - YR - 2 * DT, 8, centered=False).translate((SPLIT + DT, YR + DT, BAND_Z1 - 4)))
    o = o.cut(cq.Workplane('XY').box(141 - 121.5 - 2 * DT, YL - YR - 2 * DT, 8, centered=False).translate((121.5 + DT, YR + DT, 24)))
    for y0, y1 in ((YL, SPL - DT), (SPR + DT, YR)):                                 # fenders over the tracks
        o = o.union(cq.Workplane('XY').box(SP_X1 - SPLIT - DT, y1 - y0, 2, centered=False).translate((SPLIT, y0, FENDER)))
    o = o.cut(cq.Workplane('XY').circle(32.4).extrude(10).translate((HX, HY, DECK - 5)))   # turret ring
    o = o.cut(cq.Workplane('XY').circle(33.0).extrude(DECK - DT - 0.1 - MEZ_Z1).translate((HX, HY, MEZ_Z1)))  # well's way down
    return o.val()

def lights():
    out = []
    for y in (YR + 16, YL - 16):
        out.append(cq.Workplane('YZ').circle(10).extrude(10).translate((139.5, y, 60)).val())
    return out

def rail():
    prof = [(-8, 0), (8, 0), (8, 3), (10.6, 5.6), (8, 8.2), (8, 9.5), (-8, 9.5), (-8, 8.2), (-10.6, 5.6), (-8, 3)]
    r = cq.Workplane('YZ').polyline(prof).close().extrude(RAIL_X1 - RAIL_X0).translate((RAIL_X0, YC, DECK))
    for i in range(int((RAIL_X1 - RAIL_X0 - 6) / 10)):
        r = r.cut(cq.Workplane('XY').box(5.35, 30, 3, centered=False).translate((RAIL_X0 + 4 + 10 * i, YC - 15, DECK + 6.5)))
    return r.val()

TAIL_PTS = [(-118, DECK + 6), (-134, DECK + 32), (-136, DECK + 64), (-122, DECK + 92), (-97, DECK + 106), (-72, DECK + 102)]
def tail():
    segs = []; n = len(TAIL_PTS) - 1
    for i in range(n):
        (x0, z0), (x1, z1) = TAIL_PTS[i], TAIL_PTS[i + 1]
        L = np.hypot(x1 - x0, z1 - z0) + 8; ang = np.degrees(np.arctan2(z1 - z0, x1 - x0))
        W = 30 - 3.2 * i; H = 26 - 2.6 * i
        s = cq.Workplane('XY').box(L, W, H).edges().fillet(min(W, H) * 0.42)
        s = s.rotate((0, 0, 0), (0, 1, 0), -ang).translate(((x0 + x1) / 2, YC, (z0 + z1) / 2))
        segs.append(s.val())
    pins = [cq.Workplane('XZ').circle(4).extrude(-(34 - 3 * i)).translate((x, YC - (34 - 3 * i) / 2, z)).val()
            for i, (x, z) in enumerate(TAIL_PTS[:-1])]
    (x0, z0) = TAIL_PTS[-1]
    bulb = cq.Workplane('XY').sphere(13).translate((x0, YC, z0)).val()
    cone = cq.Solid.makeCone(7, 0.8, 26, cq.Vector(x0 + 8, YC, z0 - 3), cq.Vector(0.93, 0, -0.36))
    return segs, pins, [bulb, cone]

def estop():
    return [cq.Workplane('XY').circle(11).extrude(10).translate((-126, YR + 18, DECK)).val(),
            cq.Workplane('XY').circle(14).extrude(7).translate((-126, YR + 18, DECK + 10)).edges('>Z').fillet(3).val()]

# ---------------------------------------------------------------- components (dims marked * are guesses)
def rbox(c, size, r=1.5):
    return cq.Workplane('XY').box(*size).edges('|Z').fillet(r).translate(c).val()
COMP = {  # key: (label, centre, size, note)
    'esc_L': ('ESC, left (INJORA brushed)', (-118, 33, 49), (34, 46, 18), 'size* 46 x 34 x 18; LED faces the back window'),
    'esc_R': ('ESC, right (INJORA brushed)', (-118, -26, 49), (34, 46, 18), 'size* 46 x 34 x 18'),
    'ubec': ('UBEC 5 V / 5 A (Pi only)', (-108, -27, 66), (45, 26, 12), 'size* 45 x 26 x 12; any part with 5 A continuous'),
    'ina219': ('INA219 pack monitor', (-100, 30, 62), (26, 21, 4), 'jumper off 0x40 (PCA9685 has it)'),
    'alarm': ('LiPo alarm (balance lead)', (-131, 10, 70), (8, 40, 14), 'buzzer + LEDs on the back panel'),
    'pi_switch': ('Pi power switch', (-131, -40, 70), (8, 20, 13), 'inline on the UBEC input'),
    'wifi': ('USB WiFi + RP-SMA', (-108, 44, 76), (40, 18, 10), 'external antenna in the tail'),
    'hat': ('M.2 HAT+ (Hailo-8L)', None, (65, 56.5, 1.6), 'over the active cooler on 16 mm* standoffs'),
}

# ---------------------------------------------------------------- page packing
def quant(T_):
    T_ = np.asarray(T_, float).reshape(-1, 3)
    V, inv = np.unique(np.round(T_ / 0.02).astype(np.int32), axis=0, return_inverse=True)
    return V.astype('<i2'), inv.reshape(-1, 3).astype('<u4' if len(V) > 65535 else '<u2')
def decimate(T_, faces):
    if len(T_) <= faces: return T_
    V, F = quant(T_); F = F.astype(np.int64)
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])]     # quantising makes slivers
    ms = ml.MeshSet(); ms.add_mesh(ml.Mesh(V.astype(float) * 0.02, F.astype(np.int32)))
    ms.meshing_remove_duplicate_faces(); ms.meshing_remove_unreferenced_vertices()
    ms.meshing_decimation_quadric_edge_collapse(targetfacenum=faces, preservenormal=True, planarquadric=True, autoclean=True)
    m = ms.current_mesh(); return m.vertex_matrix()[m.face_matrix()]
def b64(a): return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()

# ---------------------------------------------------------------- assembly
def head_parts():
    base = np.vstack([tri_obj(os.path.join(G, n + '.obj')) for n in ('well', 'bay', 'floor', 'gear_in', 'servo')])
    turn = np.vstack([tri_obj(os.path.join(G, n + '.obj')) for n in ('drum', 'gear_out', 'bearing')])
    return {'base': T(base, Rz(180), (HX, HY, Z0H)), 'drum': T(turn, None, (HX, HY, Z0H)),
            'cradle': T(tri_obj(FORK), None, (HX, HY, Z0H)),
            'ball': T(np.vstack([load_stl(p) for p in BALL]), None, (HX, HY, Z0H))}

PI_C = (-15.0, -3.0)      # Pi centre (X, Y); USB/Ethernet end aft, toward the power bay
PCA_C = (-8.9, 40.8, 42.95)
def pi_parts():
    P = load_stl(FF + 'RASPBERRY_PI_5_WITH_ACTIVE_COOLER.stl')
    P = np.stack([P[..., 1], -P[..., 0], P[..., 2]], -1)          # -90 deg about Z: his -Y end (tallest) aft
    lo, hi = P.reshape(-1, 3).min(0), P.reshape(-1, 3).max(0)
    P = P + [PI_C[0] - (lo[0] + hi[0]) / 2, PI_C[1] - (lo[1] + hi[1]) / 2, 44.0 - lo[2]]
    top = P[..., 2].max(); x1 = P[..., 0].max()
    hat = box_tris((x1 - 65, PI_C[1] - 28.25, top + 1.4), (x1, PI_C[1] + 28.25, top + 3.0))
    hailo = box_tris((x1 - 55, PI_C[1] - 11, top + 3.0), (x1 - 13, PI_C[1] + 11, top + 5.5))
    a = cq.importers.importStep(PCA); pca = cq_tris(a.val(), 0.2) + list(PCA_C)
    return {'pi': P, 'hat': hat, 'hailo': hailo, 'pca': pca}

def build():
    t0 = time.time()
    M = {}   # key: dict(t=tris, label, group, color, note, ex=explode vector)
    def add(k, tris, label, group, color, note='', ex=(0, 0, 0), ghost=False):
        M[k] = dict(t=np.asarray(tris, float), label=label, group=group, color=color, note=note, ex=ex, ghost=ghost)
    L = legs()
    LEG = 'Yours, unmodified (v1 leg parts)'
    for s_, dy in (('L', 70), ('R', -70)):
        nm = 'left' if s_ == 'L' else 'right'
        add('pod_' + s_, L['pod_' + s_], 'Track pod, ' + nm + ' (inner-frame-high-v10)', 'legs', 0x2B2F33, LEG + ". Its 6 inserts sit on your body's 6 side holes.", (0, dy, 0))
        add('of_' + s_, L['of_' + s_], 'Outer frame, ' + nm + ' (outer-frame-v13)', 'legs', 0x34393E, LEG + ". Its 6 holes sit on the pod's bosses, a pattern turned 1.83 deg.", (0, dy * 1.4, 0))
        add('track_' + s_, L['track_' + s_], 'TPU track, ' + nm, 'legs', 0x1E2124, 'The Luengoa flex track (CC BY-NC), drawn as a loop round the sprockets.', (0, dy * 1.2, 0))
        add('cogr_' + s_, L['cog_rear_' + s_], 'Rear drive sprocket, ' + nm, 'legs', 0xE8A33A, LEG + '.', (0, dy * 1.2, 0))
        add('cogf_' + s_, L['cog_front_' + s_], 'Front idler sprocket, ' + nm, 'legs', 0xE8A33A, LEG + '.', (0, dy * 1.2, 0))
        add('rollers_' + s_, L['rollers_' + s_], 'Road and return rollers, ' + nm, 'legs', 0xE8A33A, "8 small cogs on the outer frame's 4 posts.", (0, dy * 1.3, 0))
        add('crown_' + s_, L['crown_' + s_], '4:1 crown gear, ' + nm, 'legs', 0xC9CDD2, 'On the rear sprocket.', (0, dy * 1.1, 0))
        add('motor_' + s_, L['motor_' + s_], 'Drive motor, ' + nm + ' (INJORA 540 55T)', 'legs', 0x8A8F96,
            "Inside the pod on its rib, pinion aft. Can 36 x 52*: it stands ~4 mm into the body through the pod's window.", (0, dy, 0))
        add('pinion_' + s_, L['pinion_' + s_], '4:1 pinion, ' + nm, 'legs', 0xC9CDD2, '', (0, dy, 0))
    body, tools = body_cut()
    add('body', cq_tris(body, 0.1), 'Your body, TEST-PRINT-2, with the cuts', 'body', 0x9AA3AE,
        "Yours. Only cuts (named CUT_ in the STEP): the mid cross beam, the head's well and gear bay, the rear Pi box and the battery door.")
    for k, v in tools.items():
        add(k, cq_tris(v, 0.2), k, 'cuts', 0xD62F2F, 'A tool body for your Fusion model: cut it from TEST-PRINT-2.', ghost=True)
    add('body_orig', load_stl(FF + 'Tank_body.stl'), 'Your body as exported (before the cuts)', 'orig', 0x9AA3AE, '', ghost=True)
    bl, br = load_stl(FF + 'LeftBattery.stl'), load_stl(FF + 'RightBattery.stl')
    add('batt', np.vstack([bl, br]), '2 x Zeee 2S 5200 LiPo', 'elec', 0xE0B040,
        "Your model's boxes (141 x 45.7 x 26), where you put them. They slide out the back along the spine.", (-175, 0, 0))
    add('mezz', cq_tris(mezzanine()), 'Mezzanine (new)', 'hull', 0x6F86A3,
        "Over the batteries on 6 posts and a spine between the packs. Carries the Pi and the PCA9685; the head's base bolts to its front.", (0, 0, 30))
    add('rear', cq_tris(rear_bay()), 'Rear power bay (new)', 'hull', 0x55606B,
        'Replaces your Pi box. Battery tunnel below; ESCs, UBEC and switches above; charge and balance ports, ESC LEDs and the alarm on the back. Tail clevis on top.', (-80, 0, 0))
    add('door', cq_tris(door()), 'Battery door (new)', 'hull', 0x3F4851, 'Drops open; both packs slide out along the spine.', (-130, 0, 0))
    add('shell', cq_tris(shell()), 'Shell (new, lifts off)', 'hull', 0x7C8C7A,
        'Deck and sponsons over the tracks, X -102 to 40. Lifts off to reach the brain; the rail rides on it. Vents over the Pi, louvres in the sponsons.', (0, 0, 95))
    add('turret', cq_tris(turret()), 'Turret section (new, stays on)', 'hull', 0x6E7E6C,
        "Holds the deck ring round the well, flush with the deck, and the glacis that wraps the well's front. Headlights in the glacis.", (25, 0, 70))
    add('rail', cq_tris(rail()), 'Accessory rail (new)', 'hull', 0x3A3F44,
        'Picatinny-like, 118 long on the deck spine. An assumption: tell me what the planned rail really is.', (0, 0, 140))
    for i, s in enumerate(lights()):
        add('light%d' % i, cq_tris(s), 'Headlight / IR pod', 'elec', 0xF2F2E6, 'LED pods in the glacis.', (25, 0, 70))
    segs, pins, sting = tail()
    for i, s in enumerate(segs):
        add('tail%d' % i, cq_tris(s), 'Tail segment %d (new)' % (i + 1), 'tail', 0x7C8C7A,
            'Hollow; the antenna lead runs inside. Pinned joints, so it folds flat for transport.', (-40, 0, 110))
    add('tailpins', np.vstack([cq_tris(p) for p in pins]), 'Tail joint pins', 'tail', 0x3A3F44, '', (-40, 0, 110))
    add('stinger', np.vstack([cq_tris(s) for s in sting]), 'Stinger: antenna radome', 'tail', 0xD9622B,
        'Printed plastic passes WiFi: the antenna sits up here, 100 mm over the deck, away from the packs and motors.', (-40, 0, 110))
    (xa, za), (xb, zb) = TAIL_PTS[-3], TAIL_PTS[-1]
    add('antenna', cyl_tris((xa, YC, za), (xb, YC, zb), 4.0), 'WiFi antenna (dual band)', 'elec', 0x222222,
        'In the last tail segments; its RP-SMA lead runs down the tail to the USB adapter.', (-40, 0, 110))
    for i, s in enumerate(estop()):
        add('estop%d' % i, cq_tris(s), 'E-stop (cuts both drive packs)', 'elec', 0xC62828 if i else 0xF2C230,
            'Twist-release mushroom on the rear deck. Cuts the ESC feeds only, so the Pi stays up.', (-80, 0, 30))
    for k, (lab, c, sz, note) in COMP.items():
        if c is None: continue
        add(k, cq_tris(rbox(c, sz)), lab, 'elec', 0x2F5FB0 if k.startswith('esc') else 0x3C9A4C, note, (-80, 0, 25))
    PP = pi_parts()
    add('pi', PP['pi'], 'Raspberry Pi 5 + active cooler', 'elec', 0x3C9A4C,
        'Your model, turned so the USB/Ethernet end faces the power bay. On 4 mm standoffs on the mezzanine.', (0, 0, 55))
    add('hat', PP['hat'], 'M.2 HAT+', 'elec', 0x2E7D32, COMP['hat'][3], (0, 0, 65))
    add('hailo', PP['hailo'], 'Hailo-8L (M.2 2242)', 'elec', 0x111111, '', (0, 0, 65))
    add('pca', PP['pca'], 'PCA9685 (Adafruit model)', 'elec', 0x1F4FA0,
        'Your file, on the mezzanine beside the Pi: short I2C to the Pi, short servo leads to the head.', (0, 0, 55))
    H = head_parts()
    add('base', H['base'], 'Pan coil base (turned 180)', 'head', 0x7A90AC, 'Bolts down onto the mezzanine; the gear bay points aft.', (0, 0, 120))
    add('drum', H['drum'], 'Drum + bearing', 'head', 0xC9763A, '', (0, 0, 150))
    add('cradle', H['cradle'], 'Cradle', 'head', 0xD49A4A, '', (0, 0, 165))
    add('ball', H['ball'], 'Ball (your rev 2)', 'head', 0x4F7FBF, '', (0, 0, 165))
    add('res_rail', box_tris((RAIL_X0, YC - 35, DECK + 9.5), (RAIL_X1, YC + 35, 170)), "Kept clear: the rail's accessory or the arm",
        'reserved', 0x7FB3D5, '', (0, 0, 140), ghost=True)
    add('res_sweep', cyl_tris((HX, HY, Z0H + 10.5), (HX, HY, Z0H + 72.5), 43.7, 64), "Kept clear: the head's 360 sweep (r 43.7)",
        'reserved', 0xF0B27A, '', (0, 0, 165), ghost=True)
    print('built %d meshes in %.0f s' % (len(M), time.time() - t0))
    return M

# ---------------------------------------------------------------- fit checks (1 mm voxels; a brainstorm, not a ship check)
def _occ(T_, lo, hi, h=1.0):
    g = [np.arange(l + 0.37 * h, u, h) for l, u in zip(lo, hi)]     # off the round numbers: no cell centre on a face
    return _scan(T_, 2, g)
def overlap_mm3(A, B, margin=1.0):
    A = np.asarray(A).reshape(-1, 3, 3); B = np.asarray(B).reshape(-1, 3, 3)
    a0, a1 = A.reshape(-1, 3).min(0), A.reshape(-1, 3).max(0); b0, b1 = B.reshape(-1, 3).min(0), B.reshape(-1, 3).max(0)
    lo = np.floor(np.maximum(a0, b0) - margin); hi = np.ceil(np.minimum(a1, b1) + margin)
    if np.any(hi - lo <= 0): return 0.0
    def clip(T_):
        t0, t1 = T_.min(1), T_.max(1); keep = np.all((t1 >= lo - 2) & (t0 <= hi + 2), axis=1)
        return T_ if keep.all() else T_          # parity needs whole meshes; the scan only walks the box's columns
    return float((_occ(clip(A), lo, hi) & _occ(clip(B), lo, hi)).sum())

def checks(M):
    t0 = time.time()
    g = lambda *ks: np.vstack([M[k]['t'] for k in ks])
    legsL = ['pod_L', 'of_L', 'track_L', 'cogr_L', 'cogf_L', 'rollers_L', 'crown_L', 'motor_L', 'pinion_L']
    legsR = [k.replace('_L', '_R') for k in legsL]
    elec_rear = ['esc_L', 'esc_R', 'ubec', 'ina219', 'alarm', 'pi_switch', 'wifi']
    drawer = M['batt']['t'] - [160.0, 0, 0]                        # both packs slid out the back
    sweep = []                                                      # cradle + ball, every 10 deg of pan
    CB = np.vstack([M['cradle']['t'], M['ball']['t']]) - [HX, HY, 0]
    for a in range(0, 360, 30):
        sweep.append(T(CB, Rz(a), (HX, HY, 0)))
    rows = [
        # (what, A, B, expect zero?, why)
        ('Left leg vs your body', g(*legsL), M['body']['t'], 'pods sit flat on the side faces'),
        ('Right leg vs your body', g(*legsR), M['body']['t'], ''),
        ('Head base vs your body, with the cuts', M['base']['t'], M['body']['t'], ''),
        ('Head base vs your body as exported (control)', M['base']['t'], M['body_orig']['t'], 'must read > 0: the cuts are what make room'),
        ('Head base vs mezzanine', M['base']['t'], M['mezz']['t'], 'it stands on it'),
        ('Head base vs batteries', M['base']['t'], M['batt']['t'], ''),
        ('Head base vs turret section', M['base']['t'], M['turret']['t'], ''),
        ('Head, 12 pan angles, vs turret + shell + rail', np.vstack(sweep), g('turret', 'shell', 'rail', 'light0', 'light1'), ''),
        ('Head, 12 pan angles, 18 mm lower (control)', np.vstack(sweep) - [0, 0, 18.0], g('turret', 'shell', 'rail', 'light0', 'light1'),
         'must read > 0: the cradle clears the deck by 12.7 (its lowest point outside the ring, Z 98.7)'),
        ('Pi + HAT vs mezzanine, shell, PCA', g('pi', 'hat', 'hailo'), g('mezz', 'shell', 'pca'), ''),
        ('Pi + HAT vs your body', g('pi', 'hat', 'hailo'), M['body']['t'], ''),
        ('Pi raised 15 mm vs shell (control)', g('pi', 'hat', 'hailo') + [0, 0, 15.0], M['shell']['t'], 'must read > 0'),
        ('PCA9685 vs your body', M['pca']['t'], M['body']['t'], ''),
        ('Mezzanine vs your body', M['mezz']['t'], M['body']['t'], ''),
        ('Mezzanine vs batteries + motors', M['mezz']['t'], g('batt', 'motor_L', 'motor_R'), ''),
        ('Motors vs your body + batteries', g('motor_L', 'motor_R'), g('body', 'batt'), ''),
        ('Shell vs legs', M['shell']['t'], g(*(legsL + legsR)), 'fenders clear the tracks'),
        ('Shell 8 mm lower vs legs (control)', M['shell']['t'] - [0, 0, 8.0], g(*(legsL + legsR)), 'must read > 0'),
        ('Turret section vs legs + your body', M['turret']['t'], g(*(legsL + legsR), 'body'), ''),
        ('Shell vs your body + rear bay + turret', M['shell']['t'], g('body', 'rear', 'turret'), ''),
        ('Rear bay vs your body + legs', M['rear']['t'], g('body', *(legsL + legsR)), ''),
        ('Power bay parts vs rear bay', g(*elec_rear), M['rear']['t'], ''),
        ('Tail vs shell + rail + rail space', g('tail0', 'tail1', 'tail2', 'tail3', 'tail4', 'stinger'), g('shell', 'rail', 'res_rail'), ''),
        ('Packs slid out the back vs body, bay, mezzanine', drawer, g('body', 'rear', 'mezz'), 'the battery drawer works'),
        ('Packs slid out vs your body as exported (control)', drawer, M['body_orig']['t'], 'must read > 0'),
    ]
    out = []
    for what, A, B, why in rows:
        v = overlap_mm3(A, B); out.append(dict(what=what, mm3=v, why=why)); print('%-55s %9.0f mm3' % (what, v))
    print('checks %.0f s' % (time.time() - t0))
    return out

# ---------------------------------------------------------------- page + hand-off
FACES = {'pod_': 22000, 'of_': 7000, 'track_': 9000, 'cog': 3000, 'rollers_': 5000, 'crown_': 2000, 'pinion_': 800,
         'body_orig': 12000, 'body': 26000, 'pi': 9000, 'pca': 7000, 'base': 22000, 'drum': 9000, 'cradle': 14000,
         'ball': 22000, 'shell': 14000, 'turret': 12000, 'rear': 8000, 'mezz': 5000}
def faces_for(k):
    for p_, n in FACES.items():
        if k.startswith(p_): return n
    return 6000

def sizes(M):
    solid = [v['t'].reshape(-1, 3) for k, v in M.items() if not v['ghost']]
    A = np.vstack(solid); lo, hi = A.min(0), A.max(0)
    trk = np.vstack([M['track_L']['t'], M['track_R']['t']]).reshape(-1, 3)
    ground = trk[:, 2].min(); tr_rear = M['track_L']['t'].reshape(-1, 3)
    gauge = (M['track_L']['t'].reshape(-1, 3)[:, 1].mean() - M['track_R']['t'].reshape(-1, 3)[:, 1].mean())
    body_bottom = M['body']['t'].reshape(-1, 3)[:, 2].min()
    ball_top = M['ball']['t'].reshape(-1, 3)[:, 2].max()
    hull = np.vstack([M[k]['t'].reshape(-1, 3) for k in ('shell', 'turret', 'rear', 'body')])
    tail = np.vstack([M[k]['t'].reshape(-1, 3) for k in M if k.startswith('tail') or k == 'stinger'])
    return [('Length, nose to tail', '%.0f mm' % (hi[0] - lo[0])), ('Width over the sponsons', '%.0f mm' % (hi[1] - lo[1])),
            ('Height to the ball / stinger', '%.0f / %.0f mm' % (ball_top - ground, tail[:, 2].max() - ground)),
            ('Deck over the ground', '%.0f mm' % (DECK - ground)), ('Ground clearance (front)', '%.0f mm' % (body_bottom - ground)),
            ('Track gauge', '%.0f mm' % gauge), ('Your body as exported', '238.5 x 131.5 x 50'),
            ('Room: your body / added', '%.1f L / %.1f L' % (207.1 * (YL - YR) * 50 / 1e6, added() / 1e6))]

def added():
    """gross volume the new parts enclose: sponsons + deck, the strip over the band, the power bay, the glacis"""
    return ((SP_X1 - SH_X0) * (SPL - SPR) * (DECK - FENDER) + (121.5 + 86) * (YL - YR) * (FENDER - BAND_Z1)
            + (-87.7 - REAR_X0) * (YL - YR) * (DECK - BAND_Z0) + 0.5 * (145 - 121.5) * (YL - YR) * (DECK - 27))

def page(M, C):
    D = {'m': {}, 'checks': C, 'sizes': sizes(M), 'yc': YC}
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v['ghost']])
    D['centre'] = ((A.min(0) + A.max(0)) / 2).round(1).tolist()
    for k, v in M.items():
        Tk = decimate(v['t'], faces_for(k)); V, F = quant(Tk)
        D['m'][k] = {'v': b64(V), 'f': b64(F), 'i32': F.dtype == np.uint32, 'c': v['color'], 'grp': v['group'],
                     'label': v['label'], 'note': v['note'], 'ex': list(v['ex']), 'ghost': v['ghost']}
    html = open(os.path.join(HERE, 'concept_template.html'), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D) + ';')
    out = os.path.join(OUT, 'concept.html'); open(out, 'w', encoding='utf-8').write(html)
    print('page %.1f MB' % (os.path.getsize(out) / 1e6))

def fusion_tools():
    """The CUT_ bodies for TEST-PRINT-2, named, in his coordinates (his Fusion part: tool bodies, not a mesh)."""
    a = cq.Assembly()
    for k, spec in CUTS.items():
        a.add(cq.Shape(cut_solid(spec)), name=k)
    p = os.path.join(OUT, 'concept_tools_for_fusion.step'); a.save(p); print('wrote', p)

if __name__ == '__main__':
    M = build()
    C = checks(M); json.dump(C, open(os.path.join(OUT, 'checks.json'), 'w'), indent=1)
    page(M, C)
    fusion_tools()
    np.savez_compressed(os.path.join(OUT, '_meshes.npz'), **{k: v['t'] for k, v in M.items()})
    json.dump({k: {kk: vv for kk, vv in v.items() if kk != 't'} for k, v in M.items()}, open(os.path.join(OUT, '_meta.json'), 'w'))
