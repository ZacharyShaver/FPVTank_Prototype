"""Picture of the hull redesign with ideal tracks and a full-size tail (2026-10-04). A visual concept: the
tracks here are not the v1 legs, and nothing below is fit-checked. VTK offscreen render.

    python chassis-v2/ideal_render.py      # writes chassis-v2/out/ideal_front.png, ideal_rear.png, ideal_side.png
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hull as Hm, concept as C
from concept import cq, load_stl, cq_tris, cyl_tris, T, Rz, YR, YL, YC, OUT
import vtk
from vtk.util import numpy_support as ns

# ---------------------------------------------------------------- ideal tracks (concept, not the v1 legs)
TW = 60.0                                   # track width
TY = {'L': YL + 6 + TW / 2, 'R': YR - 6 - TW / 2}     # track centre lines, 6 mm off the hull's sides
SPROCKET = (-100.0, 22.0, 28.0)             # rear drive sprocket: x, z, pitch radius
IDLER = (122.0, 26.0, 24.0)                 # front idler, raised: the track climbs into obstacles
WHEELS = [(x, -8.0, 18.0) for x in (-66, -30, 6, 42, 78)]
ROLLERS = [(-40.0, 47.0, 7.0), (52.0, 47.0, 7.0)]
TRACK_T, GROUSER = 3.5, 3.5
GROUND = -8.0 - 18.0 - TRACK_T - GROUSER    # -33: 40 mm under the floor

Hm.FENDER = 64.0                            # over the new track's top run (61 with grousers)
Hm.SPL, Hm.SPR = TY['L'] + TW / 2 + 3.0, TY['R'] - TW / 2 - 3.0
Hm.SH_X0 = Hm.TUB_X0                      # flush with the back: the sprocket ends at X -135
TAIL = os.environ.get('SCORPION_TAIL', 'arm2')  # 'arm2' (the two-joint arm, long), 'arm' (tail-styled, 50 + 130), 'segments'
Hm.TAIL_CLEVIS = TAIL not in ('arm', 'arm2')

def wheel(c, r, w, y, spokes=0, teeth=0, hub=0.45):
    """a wheel (x, z) of radius r, width w, centred on y; spoked or toothed"""
    x, z = c
    if teeth:
        pts = []
        for i in range(teeth * 2):
            a = np.pi * i / teeth; rr = r + 3.0 if i % 2 == 0 else r - 2.0
            pts.append((rr * np.cos(a), rr * np.sin(a)))
        s = cq.Workplane('XZ').polyline(pts).close().extrude(w / 2, both=True)
    else:
        s = cq.Workplane('XZ').circle(r).extrude(w / 2, both=True)
        s = s.faces('>Y or <Y').edges().fillet(min(2.5, w / 4))
    if spokes:
        s = s.cut(cq.Workplane('XZ').circle(r * 0.78).extrude(w, both=True).cut(
            cq.Workplane('XZ').circle(r * hub).extrude(w, both=True)).cut(
            cq.Workplane('XZ').rect(r * 2, 4).extrude(w, both=True)).cut(
            cq.Workplane('XZ').rect(4, r * 2).extrude(w, both=True)))
    return s.translate((x, y, z)).val()

def track_side(side):
    y = TY[side]; parts = {}
    circ = [SPROCKET, IDLER] + WHEELS + ROLLERS
    y0, y1 = y - TW / 2, y + TW / 2
    parts['belt'] = C.track_loop(circ, y0, y1, t=TRACK_T, lug=GROUSER, pitch=16.0, lug_len=7.0)
    parts['sprocket'] = np.vstack([cq_tris(wheel(SPROCKET[:2], SPROCKET[2] - 1, 16, y + d, teeth=13)) for d in (-17, 17)])
    parts['hubs'] = np.vstack([cq_tris(cq.Workplane('XZ').circle(r * 0.32).extrude(TW / 2 + 3, both=True).translate((x, y, z)).val())
                               for x, z, r in [SPROCKET, IDLER] + WHEELS])
    parts['idler'] = np.vstack([cq_tris(wheel(IDLER[:2], IDLER[2] - 0.5, 22, y + d, spokes=1)) for d in (-17, 17)])
    parts['wheels'] = np.vstack([cq_tris(wheel((x, z), r - 0.3, 22, y + d, spokes=1)) for x, z, r in WHEELS for d in (-17, 17)])
    parts['rollers'] = np.vstack([cq_tris(wheel((x, z), r - 0.3, 16, y + d)) for x, z, r in ROLLERS for d in (-17, 17)])
    side_y = YL if side == 'L' else YR; sg = 1 if side == 'L' else -1
    arms = []
    for x, z, r in WHEELS:                                     # trailing arms to torsion bars in the hull's side
        p0 = np.array([x, side_y + sg * 3, z]); p1 = np.array([x + 22, side_y + sg * 3, z + 18])
        arms.append(C.cyl_tris(p0, p1, 4.5, 16)); arms.append(C.cyl_tris((x, side_y, z), (x, y, z), 3.2, 16))
        arms.append(C.cyl_tris(p1 - [0, sg * 3, 0], p1 + [0, sg * 4, 0], 6.5, 20))
    parts['arms'] = np.vstack(arms)
    parts['drive'] = C.cyl_tris((SPROCKET[0], side_y, SPROCKET[1]), (SPROCKET[0], y - sg * 22, SPROCKET[1]), 15, 40)
    return parts

def fender(side):
    y0, y1 = (YL, Hm.SPL) if side == 'L' else (Hm.SPR, YR)
    f = cq.Workplane('XY').box(146 - Hm.CAR_X1, y1 - y0, 2.4, centered=False).translate((Hm.CAR_X1, y0, Hm.FENDER))
    sk = y1 - 2.4 if side == 'L' else y0
    f = f.union(cq.Workplane('XY').box(146 - Hm.CAR_X1, 2.4, 10, centered=False).translate((Hm.CAR_X1, sk, Hm.FENDER - 7.6)))
    nose = cq.Workplane('XZ').polyline([(146, Hm.FENDER), (146, Hm.FENDER + 2.4), (166, Hm.FENDER - 14), (163, Hm.FENDER - 16)]).close() \
        .extrude(-(y1 - y0)).translate((0, y0, 0))
    return f.union(nose).val()

# ---------------------------------------------------------------- full-size tail
TAIL_BIG = [(-118, 93), (-144, 126), (-153, 166), (-144, 205), (-118, 234), (-82, 250), (-46, 246), (-20, 230)]
def tail_big():
    segs = []
    n = len(TAIL_BIG) - 1
    for i in range(n):
        (x0, z0), (x1, z1) = TAIL_BIG[i], TAIL_BIG[i + 1]
        L = np.hypot(x1 - x0, z1 - z0) + 10; ang = np.degrees(np.arctan2(z1 - z0, x1 - x0))
        W = 48 - 3.4 * i; H = 40 - 2.8 * i
        s = cq.Workplane('XY').box(L, W, H).edges().fillet(min(W, H) * 0.45)
        ridge = cq.Workplane('XY').box(L * 0.7, 5, 7).edges().fillet(2.2).translate((0, 0, H / 2 + 1.5))   # dorsal keel
        plate = cq.Workplane('XY').box(4, W + 3, H + 3).edges('|X').fillet(min(W, H) * 0.45).translate((L / 2 - 6, 0, 0))   # segment collar
        s = s.union(ridge).union(plate).rotate((0, 0, 0), (0, 1, 0), -ang).translate(((x0 + x1) / 2, YC, (z0 + z1) / 2))
        segs.append(s.val())
    x0, z0 = TAIL_BIG[-1]
    bulb = cq.Workplane('XY').sphere(19).val().scale(1.0).translate(cq.Vector(x0 + 6, YC, z0 - 12))
    barb = cq.Solid.makeCone(9, 0.6, 38, cq.Vector(x0 + 18, YC, z0 - 22), cq.Vector(0.55, 0, -0.83))
    hook = cq.Solid.makeCone(5, 0.4, 16, cq.Vector(x0 + 36, YC, z0 - 50), cq.Vector(-0.2, 0, -1))
    return segs, [bulb, barb, hook]

# ---------------------------------------------------------------- the arm as the tail (the 2026-09-13 arm, option B)
# 50 mm upper arm + 130 mm forearm. Base yaw: an MG996R inside the power bay turns a turntable on a lazy-susan
# bearing on the rear deck. Shoulder: MG996R on the U-bracket's left cheek. Elbow: DS3218 (270 deg) on the right
# cheek, coaxial with the shoulder, driving the forearm through a parallelogram (crank 22 = the forearm's rear
# lever 22, pushrod 50 = the upper arm). Gripper: an MG90D in the stinger. Masses and sizes as that session's.
ARM_X = -112.0
TT_Z = Hm.DECK + 6 + 6                       # turntable top: 6 bearing + 6 disc on the deck
SHOULDER = np.array([ARM_X, TT_Z + 36])     # shoulder axis (x, z), along Y
A1, A2 = np.radians(106), np.radians(12)    # upper arm up and back; forearm rising forward, arching over the back
U = lambda a: np.array([np.cos(a), np.sin(a)])

def link(p0, p1, w, h, r):
    """a rounded bar from p0 to p1 in the XZ plane at y = YC, w across (Y), h deep"""
    d = p1 - p0; L = np.hypot(*d) ; ang = np.degrees(np.arctan2(d[1], d[0])); c = (p0 + p1) / 2
    return cq.Workplane('XY').box(L, w, h).edges('|Y').fillet(min(r, h / 2 - 0.01, L / 2 - 0.01)).rotate((0, 0, 0), (0, 1, 0), -ang).translate((c[0], YC, c[1]))

def arm_tail():
    S = SHOULDER; E = S + 50 * U(A1); Tp = E + 130 * U(A2)
    lever = 22 * U(A2 + np.pi); C1, C2 = S + lever, E + lever        # parallelogram: crank, pushrod, rear lever
    P = {}
    P['bearing'] = cq.Workplane('XY').circle(35).circle(24).extrude(6).translate((ARM_X, YC, Hm.DECK))
    P['turntable'] = cq.Workplane('XY').circle(33).extrude(6).edges('>Z').fillet(2).translate((ARM_X, YC, Hm.DECK + 6))
    cheeks = None
    for y0 in (YC + 16, YC - 21):
        c = cq.Workplane('XY').box(46, 5, 52, centered=False).edges('|Y and >Z').fillet(14).translate((ARM_X - 23, y0, TT_Z))
        cheeks = c if cheeks is None else cheeks.union(c)
    P['bracket'] = cheeks
    # fairing: a cover on the turntable over both servos and the bracket (turns with it), slot on top for the arm
    fair = cq.Workplane('XY').box(64, 128, 46).edges('|Z').fillet(18).edges('>Z').fillet(14).translate((ARM_X + 4, YC, TT_Z + 23))
    fair = fair.cut(cq.Workplane('XY').box(64 - 6, 128 - 2 * 3, 46).edges('|Z').fillet(15).translate((ARM_X + 4, YC, TT_Z + 23 - 3)))
    fair = fair.cut(cq.Workplane('XY').box(70, 36, 30).translate((ARM_X - 8, YC - 4, TT_Z + 46)))   # slot: upper arm + pushrod
    for i in range(5):
        fair = fair.cut(cq.Workplane('XY').box(4, 128 + 4, 3).translate((ARM_X - 18 + 9 * i, YC, TT_Z + 40)))  # vents
    P['fairing'] = fair
    P['servo_sh'] = cq.Workplane('XY').box(40.7, 37, 19.7).edges('|Y').fillet(1.5).translate((S[0] + 10, YC + 21 + 18.5, S[1])) \
        .union(cq.Workplane('XY').box(54.5, 2.6, 19.7).translate((S[0] + 10, YC + 22.3, S[1])))
    P['servo_el'] = cq.Workplane('XY').box(40, 37, 20).edges('|Y').fillet(1.5).translate((S[0] + 10, YC - 21 - 18.5, S[1])) \
        .union(cq.Workplane('XY').box(54.5, 2.6, 20).translate((S[0] + 10, YC - 22.3, S[1])))
    upper = link(S, E, 14, 16, 8)
    for q in (S, E):
        upper = upper.union(cq.Workplane('XZ').circle(10).extrude(8, both=True).translate((q[0], YC, q[1])))
    P['upper'] = upper
    P['crank'] = link(S, C1, 7, 8, 4).translate((0, -10, 0))
    P['pushrod'] = cq.Workplane('XY').add(cq.Solid.makeCylinder(2.5, 50, cq.Vector(C1[0], YC - 10, C1[1]), cq.Vector(*(np.r_[E - S, 0][[0, 2, 1]] / 50))))
    # forearm: one rigid link, shaped as four tail segments arching up between the elbow and the stinger
    n = np.array([-np.sin(A2), np.cos(A2)]); segs = None
    ts = np.linspace(0, 1, 5)
    pts = [E + t * (Tp - E) + 20 * np.sin(np.pi * t) * n for t in ts]
    for i in range(4):
        w, h = 28 - 2.6 * i, 24 - 2.2 * i
        s = link(pts[i] - 5 * (pts[i + 1] - pts[i]) / np.linalg.norm(pts[i + 1] - pts[i]), pts[i + 1], w, h, h / 2)
        collar = link(pts[i + 1] - 3 * (pts[i + 1] - pts[i]) / np.linalg.norm(pts[i + 1] - pts[i]), pts[i + 1], w + 4, h + 4, h / 2 + 2)
        s = s.union(collar)
        segs = s if segs is None else segs.union(s)
    segs = segs.union(link(E, C2, 10, 12, 5).translate((0, -10, 0)))                 # rear lever, on the pushrod side
    segs = segs.union(cq.Workplane('XZ').circle(13).extrude(14, both=True).translate((E[0], YC, E[1])))
    P['forearm'] = segs
    # stinger = gripper: the MG90D sits in the bulb, two jaws hook down and forward
    bulb_c = Tp + np.array([10, -8])
    P['bulb'] = cq.Workplane('XY').sphere(17).translate((bulb_c[0], YC, bulb_c[1]))
    jaws = None
    for dy, toe in ((6.5, -1), (-6.5, 1)):
        root = bulb_c + np.array([8, -10]); mid = root + np.array([14, -24]); tip = mid + np.array([12, -6])
        j = link(root, mid, 6, 8, 3.5).union(link(mid, tip, 5, 6, 2.8)).translate((0, dy, 0))
        jaws = j if jaws is None else jaws.union(j)
    P['jaws'] = jaws
    return {k: v.val() if hasattr(v, 'val') else v for k, v in P.items()}

# ---------------------------------------------------------------- the same arm, plain and long enough to reach over the front
# Option B as chosen 2026-09-13, scaled ~2.2x so it reaches over the head and past the claws from the rear deck:
# upper arm 110, forearm 290 (carbon tube), crank = rear lever 26, pushrod 110 = the upper arm.
# Torque, held still, 100 g payload: elbow ~3.9 kg.cm (DS3218: 19), shoulder ~2.2 kg.cm (MG996R: 9.4).
L1, L2, LEVER = 110.0, 290.0, 26.0
POSES = {'reach': (60.0, -22.0), 'stance': (98.0, -4.0)}   # (upper arm, forearm) absolute angles, deg from +X

def arm2(a1d, a2d):
    a1, a2 = np.radians(a1d), np.radians(a2d)
    S = SHOULDER; E = S + L1 * U(a1); Tp = E + L2 * U(a2)
    lever = LEVER * U(a2 + np.pi); C1, C2 = S + lever, E + lever
    P = {}
    P['bearing'] = cq.Workplane('XY').circle(35).circle(24).extrude(6).translate((ARM_X, YC, Hm.DECK))
    P['turntable'] = cq.Workplane('XY').circle(33).extrude(6).edges('>Z').fillet(2).translate((ARM_X, YC, Hm.DECK + 6))
    fair = cq.Workplane('XY').box(64, 128, 46).edges('|Z').fillet(18).edges('>Z').fillet(14).translate((ARM_X + 4, YC, TT_Z + 23))
    fair = fair.cut(cq.Workplane('XY').box(58, 122, 46).edges('|Z').fillet(15).translate((ARM_X + 4, YC, TT_Z + 20)))
    fair = fair.cut(cq.Workplane('XY').box(70, 40, 30).translate((ARM_X - 4, YC - 3, TT_Z + 46)))
    P['fairing'] = fair
    plates = None                                              # upper arm: twin side plates
    for dy in (-9.5, 9.5):
        pl = link(S, E, 3, 26, 13).translate((0, dy, 0))
        plates = pl if plates is None else plates.union(pl)
    for q in (S, E):
        plates = plates.union(cq.Workplane('XZ').circle(8).extrude(12, both=True).translate((q[0], YC, q[1])))
    P['upper'] = plates
    P['crank'] = link(S, C1, 7, 9, 4.4).translate((0, -15, 0))
    d = E - S
    P['pushrod'] = cq.Workplane('XY').add(cq.Solid.makeCylinder(3, L1, cq.Vector(C1[0], YC - 15, C1[1]), cq.Vector(d[0] / L1, 0, d[1] / L1)))
    ends = None
    for q in (C1, C2):
        e_ = cq.Workplane('XZ').circle(5).extrude(4, both=True).translate((q[0], YC - 15, q[1]))
        ends = e_ if ends is None else ends.union(e_)
    P['rodends'] = ends
    hub = cq.Workplane('XY').box(34, 26, 28).edges().fillet(6).rotate((0, 0, 0), (0, 1, 0), -a2d).translate((E[0], YC, E[1]))
    hub = hub.union(link(E, C2, 9, 12, 5.9).translate((0, -15, 0)))                      # rear lever
    P['elbow'] = hub
    u2 = U(a2)
    P['forearm'] = cq.Workplane('XY').add(cq.Solid.makeCone(8.5, 6.0, L2 - 22, cq.Vector(E[0] + 14 * u2[0], YC, E[1] + 14 * u2[1]), cq.Vector(u2[0], 0, u2[1])))
    # gripper: MG90D housing at the wrist, bent 55 deg down from the forearm; two parallel jaws
    g = np.radians(a2d - 55); ug = U(np.radians(a2d - 55))
    house_c = Tp + 10 * ug
    P['gripper'] = cq.Workplane('XY').box(30, 24, 22).edges().fillet(6).rotate((0, 0, 0), (0, 1, 0), -np.degrees(g)).translate((house_c[0], YC, house_c[1]))
    jaws = None
    for dy in (-7.0, 7.0):
        j = link(house_c + 12 * ug, house_c + 40 * ug, 5, 8, 2.5).translate((0, dy, 0))
        jaws = j if jaws is None else jaws.union(j)
    P['jaws'] = jaws
    return {k: v.val() if hasattr(v, 'val') else v for k, v in P.items()}, Tp

def claws_big():
    """The pincers, scaled up and reaching past the bigger tracks so the jaws read from the side."""
    out, lights = [], []
    def lump(L, W, H, deg, c, r):
        return cq.Workplane('XY').box(L, W, H).edges().fillet(r).rotate((0, 0, 0), (0, 0, 1), deg).translate(c)
    for sg in (1, -1):
        y = lambda d: Hm.HY + sg * d
        arm = lump(66, 20, 22, -6 * sg, (138, y(52), 33), 6.0)
        palm = lump(20, 32, 24, -6 * sg, (174, y(49), 33), 6.5)
        outer = lump(38, 11, 17, -36 * sg, (194, y(47), 33), 4.5)
        inner = lump(22, 9, 14, 24 * sg, (189, y(31), 33), 3.8)
        out.append(arm.union(palm).union(outer).union(inner).val())
        lights.append(cq.Workplane('YZ').circle(7).extrude(7).translate((183, y(41), 33)).val())
    return out, lights

# ---------------------------------------------------------------- scene
def scene():
    P = []                                                     # (tris, rgb, specular, kind)
    def add(t, rgb, spec=0.25): P.append((np.asarray(t, float).reshape(-1, 3, 3), rgb, spec))
    FLOOR_Z_MID = (7.4 + 44.0) / 2
    olive, olive_d, steel, rubber, accent = (0.42, 0.48, 0.41), (0.33, 0.38, 0.33), (0.30, 0.32, 0.35), (0.10, 0.10, 0.11), (0.88, 0.47, 0.18)
    add(cq_tris(Hm.tub()), olive_d)
    add(cq_tris(Hm.turret_deck()), olive)
    add(cq_tris(Hm.carapace()), olive)
    add(cq_tris(Hm.hatch()), olive_d)
    for s_ in ('L', 'R'):
        add(cq_tris(fender(s_)), olive)
        tp = track_side(s_)
        add(tp['belt'], rubber, 0.08); add(tp['sprocket'], steel, 0.5); add(tp['idler'], steel, 0.5)
        add(tp['wheels'], steel, 0.45); add(tp['rollers'], steel, 0.45); add(tp['hubs'], accent, 0.4)
        add(tp['arms'], (0.22, 0.23, 0.25), 0.5); add(tp['drive'], (0.22, 0.23, 0.25), 0.5)
    cl, li = claws_big()
    for c in cl: add(cq_tris(c), (0.45, 0.47, 0.51), 0.55)
    for c in li: add(cq_tris(c), (1.0, 0.98, 0.88), 0.8)
    for y in (YL - 1.3, YR + 1.3):                              # the pods' motor windows, closed: no pods here
        add(cq_tris(cq.Workplane('XY').box(66, 2.6, 36.6).translate((-18, y, FLOOR_Z_MID)).val()), olive_d)
    ES = (-70.0, -80.0) if TAIL in ('arm', 'arm2') else (-120.0, YR + 18)     # outside the arm fairing's 72 mm sweep
    add(np.vstack([cq_tris(cq.Workplane('XY').circle(11).extrude(10).translate((ES[0], ES[1], Hm.DECK)).val())]), (0.95, 0.75, 0.15))
    add(cq_tris(cq.Workplane('XY').circle(14).extrude(7).translate((ES[0], ES[1], Hm.DECK + 10)).edges('>Z').fillet(3).val()), (0.78, 0.13, 0.13), 0.5)
    if TAIL == 'arm':                                         # the 2026-09-13 long-forearm arm, as the tail
        A = arm_tail()
        for k, rgb, sp in (('bearing', steel, 0.6), ('turntable', olive_d, 0.3), ('bracket', olive_d, 0.3),
                           ('servo_sh', (0.12, 0.13, 0.15), 0.4), ('servo_el', (0.12, 0.13, 0.15), 0.4), ('fairing', olive, 0.3), ('upper', olive, 0.3),
                           ('crank', steel, 0.6), ('pushrod', (0.15, 0.15, 0.16), 0.7), ('forearm', olive, 0.3),
                           ('bulb', accent, 0.5), ('jaws', (0.45, 0.47, 0.51), 0.55)):
            add(cq_tris(A[k]), rgb, sp)
    elif TAIL == 'arm2':
        pass                                                  # added per pose in __main__
    else:
        segs, sting = tail_big()
        for s in segs: add(cq_tris(s), olive)
        for s in sting: add(cq_tris(s), accent, 0.5)
        for y in (YC - 27.5, YC + 23.5):                      # a clevis wide enough for the bigger root
            add(cq_tris(cq.Workplane('XY').box(22, 4, 14, centered=False).translate((-129, y, Hm.DECK)).val()), olive_d)
    G = C.G; Z0H = Hm.Z0H; HX, HY = Hm.HX, Hm.HY
    base = np.vstack([C.tri_obj(os.path.join(G, n + '.obj')) for n in ('well', 'bay')])
    add(T(base, Rz(180), (HX, HY, Z0H)), (0.45, 0.52, 0.62))
    add(T(np.vstack([C.tri_obj(os.path.join(G, n + '.obj')) for n in ('drum', 'bearing')]), None, (HX, HY, Z0H)), accent, 0.35)
    add(T(C.tri_obj(C.FORK), None, (HX, HY, Z0H)), (0.83, 0.62, 0.31), 0.35)
    add(T(np.vstack([load_stl(p) for p in C.BALL]), None, (HX, HY, Z0H)), (0.28, 0.45, 0.72), 0.55)
    return P

def polydata(tris):
    V = tris.reshape(-1, 3); n = len(tris)
    pts = vtk.vtkPoints(); pts.SetData(ns.numpy_to_vtk(V.astype(np.float64), deep=True))
    cells = np.c_[np.full(n, 3), np.arange(3 * n).reshape(-1, 3)].ravel().astype(np.int64)
    ca = vtk.vtkCellArray(); ca.SetCells(n, ns.numpy_to_vtkIdTypeArray(cells, deep=True))
    pd = vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetPolys(ca)
    cl = vtk.vtkCleanPolyData(); cl.SetInputData(pd); cl.SetToleranceIsAbsolute(True); cl.SetAbsoluteTolerance(1e-3)
    nm = vtk.vtkPolyDataNormals(); nm.SetInputConnection(cl.GetOutputPort()); nm.SetFeatureAngle(38); nm.SplittingOn(); nm.ConsistencyOn(); nm.Update()
    return nm.GetOutput()

def render(P, cam_pos, focal, path, size=(1800, 1150), view_up=(0, 0, 1), ss=2):
    ren = vtk.vtkRenderer(); win = vtk.vtkRenderWindow(); win.SetOffScreenRendering(1); win.AddRenderer(ren); win.SetSize(size[0] * ss, size[1] * ss)
    win.SetMultiSamples(0)
    for tris, rgb, spec in P:
        m = vtk.vtkPolyDataMapper(); m.SetInputData(polydata(tris))
        a = vtk.vtkActor(); a.SetMapper(m); pr = a.GetProperty()
        pr.SetColor(*rgb); pr.SetAmbient(0.12); pr.SetDiffuse(0.86); pr.SetSpecular(spec); pr.SetSpecularPower(28)
        ren.AddActor(a)
    gp = vtk.vtkPlaneSource(); gp.SetOrigin(-1400, -1400, GROUND); gp.SetPoint1(1400, -1400, GROUND); gp.SetPoint2(-1400, 1400, GROUND); gp.SetResolution(1, 1)
    gm = vtk.vtkPolyDataMapper(); gm.SetInputConnection(gp.GetOutputPort()); ga = vtk.vtkActor(); ga.SetMapper(gm)
    ga.GetProperty().SetColor(0.86, 0.86, 0.84); ga.GetProperty().SetAmbient(0.35); ga.GetProperty().SetDiffuse(0.7); ga.GetProperty().SetSpecular(0.0)
    ren.AddActor(ga)
    ren.GradientBackgroundOn(); ren.SetBackground(0.80, 0.81, 0.80); ren.SetBackground2(0.97, 0.97, 0.96)
    ren.RemoveAllLights()
    for d, inten in (((0.45, -0.55, 0.75), 0.95), ((-0.6, 0.4, 0.55), 0.38), ((0.7, 0.5, 0.45), 0.25), ((0, 0, 1), 0.2)):
        pos = np.array(d) / np.linalg.norm(d) * 2400
        L = vtk.vtkLight(); L.SetPosition(*pos); L.SetFocalPoint(0, 0, 0); L.SetIntensity(inten); L.SetPositional(True); L.SetConeAngle(70)
        L.SetLightTypeToSceneLight(); ren.AddLight(L)
    shadows = vtk.vtkShadowMapPass(); shadows.GetShadowMapBakerPass().SetResolution(4096)
    seq = vtk.vtkSequencePass(); passes = vtk.vtkRenderPassCollection()
    passes.AddItem(shadows.GetShadowMapBakerPass()); passes.AddItem(shadows); seq.SetPasses(passes)
    camP = vtk.vtkCameraPass(); camP.SetDelegatePass(seq); ren.SetPass(camP)
    cam = ren.GetActiveCamera(); cam.SetPosition(*cam_pos); cam.SetFocalPoint(*focal); cam.SetViewUp(*view_up); cam.SetViewAngle(24)
    ren.ResetCameraClippingRange()
    win.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(win); w2i.SetScale(1); w2i.ReadFrontBufferOff(); w2i.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(path); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    from PIL import Image                                       # supersampled: scale down for clean edges
    Image.open(path).resize(size, Image.LANCZOS).save(path)
    print('wrote', path)

def arm2_parts(pose):
    A, tip = arm2(*POSES[pose])
    olive, olive_d, steel, accent = (0.42, 0.48, 0.41), (0.33, 0.38, 0.33), (0.30, 0.32, 0.35), (0.88, 0.47, 0.18)
    out = []
    for k, rgb, sp in (('bearing', steel, 0.6), ('turntable', olive_d, 0.3), ('fairing', olive, 0.3), ('upper', (0.36, 0.38, 0.41), 0.5),
                       ('crank', steel, 0.6), ('pushrod', (0.12, 0.12, 0.13), 0.8), ('rodends', steel, 0.6), ('elbow', olive_d, 0.35),
                       ('forearm', (0.12, 0.12, 0.13), 0.8), ('gripper', accent, 0.5), ('jaws', (0.45, 0.47, 0.51), 0.55)):
        out.append((np.asarray(cq_tris(A[k]), float).reshape(-1, 3, 3), rgb, sp))
    print(pose, 'tip X %.0f Z %.0f' % tuple(tip))
    return out

def sheet(names, out):
    from PIL import Image
    ims = [Image.open(os.path.join(OUT, n)) for n in names]
    w, h = ims[0].size; sh = Image.new('RGB', (w * 2, h * 2), 'white')
    for i, im in enumerate(ims): sh.paste(im, ((i % 2) * w, (i // 2) * h))
    sh.resize((w, h), Image.LANCZOS).save(os.path.join(OUT, out)); print('wrote', out)

if __name__ == '__main__':
    f = (5, YC, 70)
    if TAIL == 'arm2':
        P0 = scene(); names = []
        for pose in POSES:
            P = P0 + arm2_parts(pose)
            render(P, (760, -800, 420), (20, YC, 95), os.path.join(OUT, 'ideal_arm2_%s_front.png' % pose))
            render(P, (20, -1250, 120), (25, YC, 115), os.path.join(OUT, 'ideal_arm2_%s_side.png' % pose))
            names += ['ideal_arm2_%s_front.png' % pose, 'ideal_arm2_%s_side.png' % pose]
        sheet(names, 'ideal_arm2_sheet.png')
    else:
        PFX = 'arm_' if TAIL == 'arm' else ''
        P = scene()
        render(P, (720, -760, 360), f, os.path.join(OUT, 'ideal_%sfront.png' % PFX))
        render(P, (900, -420, 120), (30, YC, 60), os.path.join(OUT, 'ideal_%sclaws.png' % PFX))
        render(P, (-760, -640, 470), f, os.path.join(OUT, 'ideal_%srear.png' % PFX))
        render(P, (10, -1150, 95), (5, YC, 95), os.path.join(OUT, 'ideal_%sside.png' % PFX))
        sheet(['ideal_%s%s.png' % (PFX, k) for k in ('front', 'claws', 'side', 'rear')], 'ideal_%ssheet.png' % PFX)
