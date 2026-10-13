"""Three body options for Scorpion, each pushed toward one goal (brainstorm, 2026-10-04). Same robot inside
(head v2, Pi + Hailo, PCA9685, 2 packs, ESCs, power parts); the hull, tracks and add-ons change.

    python chassis-v2/variants.py      # ~3 min: renders + metrics -> chassis-v2/out/var_*.png, variants.json

Scout     low and sleek: one flat deck at the well's top, the August brief's low tail bay for the Pi, small tracks
Crawler   terrain and survival: big trapezoid tracks, pincer-tipped flippers, sloped armour, skid plate, roll hoop
Workhorse the arm and payload: the long two-joint arm mid-ship, packs aft as counterweight, a cargo bed

Visual concepts with rough numbers: masses are guesses (listed in MASS), printed weight is volume x 1.24 g/cm3 x
fill, and the interiors are laid out but not fit-checked like hull.py.
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('SCORPION_TAIL', 'arm2')
import concept as C, hull as Hm, ideal_render as IR
from concept import cq, cq_tris, cyl_tris, load_stl, T, Rz, YR, YL, YC, FF, OUT

wp = lambda: cq.Workplane('XY')
OLIVE, OLIVE_D, STEEL, RUBBER, ACC = (0.42, 0.48, 0.41), (0.33, 0.38, 0.33), (0.30, 0.32, 0.35), (0.10, 0.10, 0.11), (0.88, 0.47, 0.18)
SAND, SAND_D = (0.62, 0.56, 0.44), (0.50, 0.45, 0.35)
SLATE, SLATE_D = (0.40, 0.45, 0.52), (0.31, 0.35, 0.41)
HX = 100.0
MASS = {'pack': 300, 'motor': 170, 'head_low': 90, 'head_high': 120, 'pi': 95, 'pca': 12, 'esc': 55, 'ubec': 30,
        'power_misc': 40, 'wiring': 60, 'arm_base_servo': 55, 'arm_sh_el_servos': 115, 'arm_turntable': 60,
        'arm_upper': 30, 'arm_forearm': 40, 'arm_gripper': 30, 'payload': 100, 'flipper_drive': 2 * 60}
PLA, TPU = 1.24e-3, 1.21e-3                                # g/mm3

class Build:
    """parts to draw (tris, rgb, spec) and mass items (name, g, (x, y, z)) for the centre of mass"""
    def __init__(s, name): s.name, s.draw, s.mass, s.printed, s.posable = name, [], [], [], []
    def solid(s, sh, rgb, spec=0.3, fill=0.85, printed=True, label=''):
        s.draw.append((np.asarray(cq_tris(sh), float).reshape(-1, 3, 3), rgb, spec))
        v = sh.Volume(); c = sh.Center()
        if printed:
            g = v * PLA * fill; s.mass.append((label or 'print', g, (c.x, c.y, c.z))); s.printed.append((label, g))
    def mesh(s, tris, rgb, spec=0.3): s.draw.append((np.asarray(tris, float).reshape(-1, 3, 3), rgb, spec))
    def item(s, name, g, c): s.mass.append((name, g, tuple(map(float, c))))

def solids(x):
    return x.vals() if hasattr(x, 'vals') else [x]

# ---------------------------------------------------------------- tracks, parametric (the ideal_render ones, generalised)
def tracks(B, spec, colors=(STEEL, ACC)):
    """spec: sprocket (x, z, r), idler, wheels [], rollers [], tw, t, g, gap (from the hull side). Returns geometry facts."""
    out = {}
    for side in 'LR':
        sg = 1 if side == 'L' else -1; face = YL if side == 'L' else YR
        y = face + sg * (spec['gap'] + spec['tw'] / 2)
        circ = [spec['sprocket'], spec['idler']] + spec['wheels'] + spec['rollers']
        belt = C.track_loop(circ, y - spec['tw'] / 2, y + spec['tw'] / 2, t=spec['t'], lug=spec['g'], pitch=16.0, lug_len=7.0)
        B.mesh(belt, RUBBER, 0.08)
        hw = spec['tw'] * 0.27
        for d in (-hw, hw):
            B.solid(IR.wheel(spec['sprocket'][:2], spec['sprocket'][2] - 1, spec['tw'] * 0.27, y + d, teeth=13), colors[0], 0.5, 0.5)
            B.solid(IR.wheel(spec['idler'][:2], spec['idler'][2] - 0.5, spec['tw'] * 0.36, y + d, spokes=1), colors[0], 0.5, 0.5)
            for x, z, r in spec['wheels']:
                B.solid(IR.wheel((x, z), r - 0.3, spec['tw'] * 0.36, y + d, spokes=1 if r > 15 else 0), colors[0], 0.45, 0.5)
            for x, z, r in spec['rollers']:
                B.solid(IR.wheel((x, z), r - 0.3, spec['tw'] * 0.27, y + d), colors[0], 0.45, 0.5)
        for x, z, r in [spec['sprocket'], spec['idler']] + spec['wheels']:
            B.mesh(cq_tris(cq.Workplane('XZ').circle(r * 0.32).extrude(spec['tw'] / 2 + 3, both=True).translate((x, y, z)).val()), colors[1], 0.4)
        for x, z, r in spec['wheels']:
            B.mesh(cyl_tris((x, face, z), (x, y, z), 3.2, 16), (0.22, 0.23, 0.25), 0.5)
        sx, sz, sr = spec['sprocket']
        B.mesh(cyl_tris((sx, face, sz), (sx, y - sg * spec['tw'] * 0.4, sz), 15, 40), (0.22, 0.23, 0.25), 0.5)
        # belt mass: ring area x width (TPU)
        from scipy.spatial import ConvexHull
        th = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        S = np.vstack([np.c_[x + r * np.cos(th), z + r * np.sin(th)] for x, z, r in circ]); Hh = S[ConvexHull(S).vertices]
        per = np.sum(np.linalg.norm(np.diff(np.vstack([Hh, Hh[:1]]), axis=0), axis=1))
        B.item('track belt ' + side, per * spec['tw'] * (spec['t'] + spec['g'] * 7 / 16) * TPU, (np.mean(Hh[:, 0]), y, np.mean(Hh[:, 1])))
        B.item('motor ' + side, MASS['motor'], (sx + 32, face - sg * 14, sz))
        out[side] = dict(y=y, outer=y + sg * spec['tw'] / 2)
    ground = min(z - r for x, z, r in spec['wheels']) - spec['t'] - spec['g']
    xs = [x for x, z, r in spec['wheels']]; rr = spec['wheels'][0][2]
    out.update(ground=ground, xf=max(xs) + 0.5 * rr, xr=min(xs) - 0.5 * rr)
    return out

def head(B, floor_top, hx=HX):
    z0 = floor_top + 39.4
    base = np.vstack([C.tri_obj(os.path.join(C.G, n + '.obj')) for n in ('well', 'bay')])
    B.mesh(T(base, Rz(180), (hx, YC, z0)), (0.45, 0.52, 0.62))
    B.mesh(T(np.vstack([C.tri_obj(os.path.join(C.G, n + '.obj')) for n in ('drum', 'bearing')]), None, (hx, YC, z0)), ACC, 0.35)
    B.mesh(T(C.tri_obj(C.FORK), None, (hx, YC, z0)), (0.83, 0.62, 0.31), 0.35)
    B.mesh(T(np.vstack([load_stl(p) for p in C.BALL]), None, (hx, YC, z0)), (0.28, 0.45, 0.72), 0.55)
    B.item('head base', MASS['head_low'], (hx - 15, YC, z0 - 18)); B.item('head ball', MASS['head_high'], (hx, YC, z0 + 50))
    return z0

def insides(B, packs_x0, packs_z, brain, power):
    """mass items for what's inside: packs (X from packs_x0, 141 long), brain (Pi stack + PCA) and power parts centres"""
    for y in (-22.15, 28.85):
        B.item('pack', MASS['pack'], (packs_x0 + 70.5, y, packs_z + 13))
    B.item('pi + hailo', MASS['pi'], brain); B.item('pca', MASS['pca'], brain)
    B.item('escs', 2 * MASS['esc'], power); B.item('ubec + misc', MASS['ubec'] + MASS['power_misc'], power)
    B.item('wiring', MASS['wiring'], (0, YC, packs_z + 30))

def claws(B, dz=0.0, dx=0.0, scale=1.0, color=(0.45, 0.47, 0.51)):
    for c in Hm.claws():
        sh = c.scale(scale) if scale != 1.0 else c
        if scale != 1.0:
            cc = c.Center(); sh = sh.translate(cq.Vector(cc.x * (1 - scale), cc.y * (1 - scale), cc.z * (1 - scale)))
        B.solid(sh.translate(cq.Vector(dx, 0, dz)), color, 0.55, 0.6, label='claw')

def plan_hull(x0, x1, half_y, r_nose, extra=()):
    from scipy.spatial import ConvexHull
    th = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    pts = np.vstack([[[x0, YC - half_y], [x1, YC - half_y], [x1, YC + half_y], [x0, YC + half_y]],
                     np.c_[HX + r_nose * np.cos(th), YC + r_nose * np.sin(th)]] + list(extra))
    return [tuple(p) for p in pts[ConvexHull(pts).vertices]]

def arm(B, base_x, deck, a1d, a2d, yaw=0.0, L1=110.0, L2=290.0, lever=26.0, color=OLIVE):
    """the two-joint arm (option B), base on the deck at base_x, turned yaw deg about Z"""
    a1, a2 = np.radians(a1d), np.radians(a2d); U = IR.U
    tt = deck + 12; S = np.array([0.0, tt + 36]); E = S + L1 * U(a1); Tp = E + L2 * U(a2)
    lv = lever * U(a2 + np.pi); C1, C2 = S + lv, E + lv
    parts = []
    parts.append((cq.Workplane('XY').circle(35).circle(24).extrude(6).translate((0, 0, deck)), STEEL))
    parts.append((cq.Workplane('XY').circle(33).extrude(6).edges('>Z').fillet(2).translate((0, 0, deck + 6)), OLIVE_D))
    fair = wp().box(64, 128, 46).edges('|Z').fillet(18).edges('>Z').fillet(14).translate((4, 0, tt + 23))
    fair = fair.cut(wp().box(58, 122, 46).edges('|Z').fillet(15).translate((4, 0, tt + 20))).cut(wp().box(70, 40, 30).translate((-4, -3, tt + 46)))
    parts.append((fair, color))
    def lk(p0, p1, w, h, r, dy=0.0):
        d = p1 - p0; L = np.hypot(*d); ang = np.degrees(np.arctan2(d[1], d[0])); c = (p0 + p1) / 2
        return wp().box(L, w, h).edges('|Y').fillet(min(r, h / 2 - 0.01, L / 2 - 0.01)).rotate((0, 0, 0), (0, 1, 0), -ang).translate((c[0], dy, c[1]))
    up = lk(S, E, 3, 26, 13, -9.5).union(lk(S, E, 3, 26, 13, 9.5))
    for q in (S, E): up = up.union(cq.Workplane('XZ').circle(8).extrude(12, both=True).translate((q[0], 0, q[1])))
    parts.append((up, (0.36, 0.38, 0.41)))
    parts.append((lk(S, C1, 7, 9, 4.4, -15), STEEL))
    d = (E - S) / L1
    parts.append((wp().add(cq.Solid.makeCylinder(3, L1, cq.Vector(C1[0], -15, C1[1]), cq.Vector(d[0], 0, d[1]))), (0.12, 0.12, 0.13)))
    hub = wp().box(34, 26, 28).edges().fillet(6).rotate((0, 0, 0), (0, 1, 0), -a2d).translate((E[0], 0, E[1])).union(lk(E, C2, 9, 12, 5.9, -15))
    parts.append((hub, OLIVE_D))
    u2 = U(a2)
    parts.append((wp().add(cq.Solid.makeCone(8.5, 6.0, L2 - 22, cq.Vector(E[0] + 14 * u2[0], 0, E[1] + 14 * u2[1]), cq.Vector(u2[0], 0, u2[1]))), (0.12, 0.12, 0.13)))
    g = a2d - 55; ug = U(np.radians(g)); hc = Tp + 10 * ug
    parts.append((wp().box(30, 24, 22).edges().fillet(6).rotate((0, 0, 0), (0, 1, 0), -g).translate((hc[0], 0, hc[1])), ACC))
    jaws = lk(hc + 12 * ug, hc + 40 * ug, 5, 8, 2.5, -7).union(lk(hc + 12 * ug, hc + 40 * ug, 5, 8, 2.5, 7))
    parts.append((jaws, (0.45, 0.47, 0.51)))
    for p, rgb in parts:
        sh = p.val() if hasattr(p, 'val') else p
        sh = sh.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), yaw).translate(cq.Vector(base_x, YC, 0))
        B.mesh(cq_tris(sh), rgb, 0.4); B.posable.append(len(B.draw) - 1)
    rot = lambda p, y=0.0: (base_x + p[0] * np.cos(np.radians(yaw)) - y * np.sin(np.radians(yaw)), YC + p[0] * np.sin(np.radians(yaw)), p[1])
    B.item('arm turntable', MASS['arm_turntable'], rot((0, tt + 10))); B.item('arm base servo', MASS['arm_base_servo'], rot((0, deck - 22)))
    B.item('arm shoulder+elbow servos', MASS['arm_sh_el_servos'], rot(S)); B.item('arm upper', MASS['arm_upper'], rot((S + E) / 2))
    B.item('arm forearm', MASS['arm_forearm'], rot((E + Tp) / 2)); B.item('arm gripper', MASS['arm_gripper'], rot(Tp))
    B.item('payload', MASS['payload'], rot(Tp + 30 * ug))
    return rot(Tp)

# ================================================================ Scout: low and sleek
def scout():
    B = Build('Scout'); FL0, FL1 = 2.6, 5.0
    tk = tracks(B, dict(sprocket=(-100, 18, 22), idler=(100, 18, 22), wheels=[(x, 4, 14) for x in (-66, -33, 0, 33, 66)],
                        rollers=[], tw=46, t=3, g=3, gap=6), (STEEL, ACC))
    z0 = head(B, FL1); DK = z0 + 6.6                                   # 51.0: one flat deck at the well's top
    body = wp().polyline(plan_hull(-112, 100, (YL - YR) / 2, 34.2)).close().extrude(DK - 2.4 - FL0).translate((0, 0, FL0))
    tb = [(-205, 26), (-110, FL0), (-110, DK - 2.4), (-205, DK - 2.4)]            # tail bay: its underside rises aft
    tailbay = cq.Workplane('XZ').polyline(tb).close().extrude(-104).translate((0, YC - 52, 0))
    tub = body.union(tailbay)
    tub = tub.cut(wp().polyline(plan_hull(-112 + 2.4, 100 - 0.1, (YL - YR) / 2 - 2.4, 34.2 - 2.4)).close().extrude(80).translate((0, 0, FL1)))
    tub = tub.cut(cq.Workplane('XZ').polyline(tb).close().offset2D(-2.4).extrude(-(104 - 4.8)).translate((0, YC - 52 + 2.4, 0)))
    B.solid(tub.val(), SLATE_D, 0.3, label='tub')
    half = tk['L']['outer'] - YC + 4
    deck = wp().polyline(plan_hull(-118, 112, half, 34.2)).close().extrude(2.4).translate((0, 0, DK - 2.4))
    deck = deck.union(wp().box(92, 104, 2.4, centered=False).translate((-205, YC - 52, DK - 2.4)).edges('|Z and <X').fillet(20))
    deck = deck.cut(wp().circle(32.4).extrude(10).translate((HX, YC, DK - 5)))
    for i in range(8):
        deck = deck.cut(wp().box(4, 50, 6).translate((-190 + 9 * i, YC, DK)))           # vents over the Pi in the tail bay
    B.solid(deck.val(), SLATE, 0.35, label='deck')
    for sg in (1, -1):                                                   # skirts over the upper track, smooth sides
        yo = YC + sg * half
        sk = wp().box(230, 2.4, DK - 30, centered=False).translate((-118, yo - (2.4 if sg > 0 else 0), 30))
        nose = cq.Workplane('XZ').polyline([(112, DK), (112, 47.5), (124, 45), (131, 36), (135, 36), (132, DK)]).close().extrude(-(tk['L']['outer'] - YL + 2)) \
            .translate((0, (YL - 1) if sg > 0 else (tk['R']['outer'] - 1), 0))
        B.solid(sk.union(nose).val(), SLATE, 0.35, label='skirt')
    sting = cq.Solid.makeCone(7, 1.0, 46, cq.Vector(-205, YC, DK - 4), cq.Vector(-0.35, 0, 0.94))
    B.solid(sting, ACC, 0.5, label='stinger')                            # antenna stub
    claws(B, dz=-13, dx=-6, scale=0.85, color=(0.45, 0.47, 0.51))
    insides(B, packs_x0=-99, packs_z=FL1 + 0.2, brain=(-150, YC, FL1 + 22), power=(-128, YC, FL1 + 18))
    return B, tk, dict(deck=DK, floor0=FL0, z0=z0, inside=(212 * 131.5 + np.pi * 34.2 ** 2 / 2 + 93 * 104) * (DK - FL0))

# ================================================================ Crawler: terrain and survival
def crawler():
    B = Build('Crawler'); FL0, FL1 = 9.0, 12.0
    tk = tracks(B, dict(sprocket=(-108, 26, 30), idler=(124, 36, 26), wheels=[(x, -10, 20) for x in (-74, -38, -2, 34, 70)],
                        rollers=[(-45, 54, 7), (45, 56, 7)], tw=64, t=4, g=5, gap=6), (STEEL, ACC))
    z0 = head(B, FL1); TD = z0 + 6.6; FEN = 74.0; DK = 94.0
    # tub with a skid plate: bottom edges chamfered front and back
    tub = wp().polyline(plan_hull(-122, 100, (YL - YR) / 2, 34.2)).close().extrude(60 - FL0).translate((0, 0, FL0))
    skid = cq.Workplane('XZ').polyline([(-140, 30), (-112, FL0), (110, FL0), (142, 34), (142, 80), (-140, 80)]).close().extrude(-300).translate((0, -150, 0))
    tub = tub.intersect(skid)                                           # skid plate: bottom chamfered fore and aft
    tub = tub.cut(wp().polyline(plan_hull(-122 + 3, 100 - 0.1, (YL - YR) / 2 - 3, 34.2 - 3)).close().extrude(80).translate((0, 0, FL1)))
    B.solid(tub.val(), SAND_D, 0.3, label='tub')
    td = wp().polyline(plan_hull(56, 100, (YL - YR) / 2 - 3.3, 34.2 - 3.3)).close().extrude(2.4).translate((0, 0, TD - 2.4))
    td = td.intersect(wp().box(200, 300, 30, centered=False).translate((56, -150, TD - 10))).cut(wp().circle(32.4).extrude(10).translate((HX, YC, TD - 5)))
    B.solid(td.val(), SAND, 0.3, label='turret deck')
    # carapace: sloped armour, front face leaning back out of the cradle's sweep (X <= 56 above Z 70.7)
    half = tk['L']['outer'] - YC + 4
    prof = [(-122, 60), (-122, 78), (-106, DK), (36, DK), (56, 71), (56, 60)]
    car = cq.Workplane('XZ').polyline(prof).close().extrude(-(YL - YR)).translate((0, YR, 0))
    sp = [(-118, FEN), (-118, 84), (-108, DK), (36, DK), (56, 78), (58, FEN)]
    for y0, w in ((YL, YC + half - YL), (YC - half, YR - (YC - half))):
        car = car.union(cq.Workplane('XZ').polyline(sp).close().extrude(-w).translate((0, y0, 0)))
    car = car.edges('|X and >Z and (>Y or <Y)').chamfer(14)
    inner = cq.Workplane('XZ').polyline(prof).close().offset2D(-2.4).extrude(-(YL - YR - 4.8)).translate((0, YR + 2.4, 0))
    car = car.cut(inner).cut(wp().box(176, YL - YR - 4.8, 10, centered=False).translate((-119, YR + 2.4, 56)))
    for y0, w, e in ((YL, YC + half - YL - 2.4, '>Y'), (YC - half + 2.4, YR - (YC - half) - 2.4, '<Y')):
        car = car.cut(cq.Workplane('XZ').polyline(sp).close().offset2D(-2.4).extrude(-w).translate((0, y0, 0)).edges('|X and >Z and %s' % e).chamfer(11.5))
    for sg in (1, -1):
        for i in range(7):                                                # hooded louvres low on the sponson sides
            car = car.cut(wp().box(6, 10, 7).translate((-90 + 17 * i, YC + sg * half, FEN + 6)))
    B.solid(car.val(), SAND, 0.3, label='carapace')
    for sg in (1, -1):                                                   # front fenders over the raised idler
        y0 = YL if sg > 0 else YC - half; w = YC + half - YL if sg > 0 else YR - (YC - half)
        f = cq.Workplane('XZ').polyline([(56, FEN), (56, FEN + 2.4), (140, FEN + 2.4), (165, 52), (162, 50), (139, FEN)]).close().extrude(-w).translate((0, y0, 0))
        B.solid(f.val(), SAND, 0.3, label='fender')
    # roll hoop behind the head (X 50, out of the cradle's sweep): rollover guard and carry handle
    tt = np.linspace(-1, 1, 41); ys = YC + tt * (half - 14); zs = DK + (154 - DK) * (1 - tt ** 2) ** 0.55
    tube = [cyl_tris((44, ys[i], zs[i]), (44, ys[i + 1], zs[i + 1]), 6, 20) for i in range(40)]
    B.mesh(np.vstack(tube), (0.22, 0.23, 0.25), 0.6)
    Lh = np.sum(np.hypot(np.diff(ys), np.diff(zs))); B.item('roll hoop', Lh * np.pi * 36 * PLA, (44, YC, (DK + 154) / 2))
    # flippers: pincer-tipped sub-tracks on the idler axle, outboard of the tracks, raised 20 deg (climbing pose)
    for side in 'LR':
        sg = 1 if side == 'L' else -1; y = tk[side]['outer'] + sg * 19
        p0 = np.array([124.0, 36.0]); ang = np.radians(20); p1 = p0 + 112 * np.array([np.cos(ang), np.sin(ang)])
        belt = C.track_loop([(p0[0], p0[1], 26), (p1[0], p1[1], 13)], y - 14, y + 14, t=3, lug=3, pitch=14, lug_len=6)
        B.mesh(belt, RUBBER, 0.08)
        plate = IR.link(p0, p1, 4, 30, 12).translate((0, y - YC + sg * 16, 0))
        B.solid(plate.val(), SAND_D, 0.35, label='flipper plate')
        tipc = p1 + 8 * np.array([np.cos(ang), np.sin(ang)])
        for dz, rot in ((7, -28), (-7, 28)):                            # the pincer at the tip
            prong = wp().box(26, 8, 7).edges('|Y').fillet(3).rotate((0, 0, 0), (0, 1, 0), -(20 + rot)).translate((tipc[0] + 10, y + sg * 16, tipc[1] + dz))
            B.solid(prong.val(), (0.45, 0.47, 0.51), 0.55, label='flipper pincer')
        B.mesh(cq_tris(cq.Workplane('XZ').circle(10).extrude(26, both=True).translate((124, y, 36)).val()), ACC, 0.4)
    B.item('flipper drives', MASS['flipper_drive'], (100, YC, 40))
    segs, pins, sting = Hm.tail()
    for s in segs: B.solid(s.translate(cq.Vector(18, 0, DK - Hm.DECK)), SAND, 0.3, label='tail')      # on the flat deck
    for s in sting: B.solid(s.translate(cq.Vector(18, 0, DK - Hm.DECK)), ACC, 0.5, label='stinger')
    for sg in (1, -1):
        B.mesh(cq_tris(cq.Workplane('YZ').circle(7).extrude(5).translate((134, YC + sg * 22, 30)).val()), (1.0, 0.98, 0.88), 0.8)
    insides(B, packs_x0=-99, packs_z=FL1 + 0.2, brain=(-15, YC, 60), power=(-112, YC, 66))
    return B, tk, dict(deck=DK, floor0=FL0, z0=z0, inside=(222 * 131.5 + np.pi * 34.2 ** 2 / 2) * (60 - FL0) + 2 * 172 * 66 * (DK - FEN) + 178 * 131.5 * (DK - 60))

# ================================================================ Workhorse: the arm and payload
def workhorse():
    B = Build('Workhorse')
    sp = dict(sprocket=IR.SPROCKET, idler=IR.IDLER, wheels=IR.WHEELS, rollers=IR.ROLLERS, tw=IR.TW, t=IR.TRACK_T, g=IR.GROUSER, gap=6)
    tk = tracks(B, sp, (STEEL, ACC))
    z0 = head(B, Hm.FLOOR)
    Hm.FENDER, Hm.SPL, Hm.SPR, Hm.SH_X0, Hm.TAIL_CLEVIS = 64.0, IR.Hm.SPL, IR.Hm.SPR, Hm.TUB_X0, False
    Hm.HATCH = (-58.0, -32.0, 18.0, 40.0)                              # the brain opening, under the arm's pedestal
    B.solid(Hm.tub(), OLIVE_D, 0.3, label='tub'); B.solid(Hm.turret_deck(), OLIVE, 0.3, label='turret deck')
    car = cq.Workplane('XY').add(Hm.carapace())
    for i in range(5):                                                   # cargo bed: tie-down slots
        for j in range(5):
            car = car.cut(wp().box(3.5, 13, 8).translate((-128 + 16 * i, YC - 44 + 22 * j, Hm.DECK)))
    B.solid(car.val(), OLIVE, 0.3, label='carapace')
    for y in (YR + 5, YL - 5):                                           # bed rails
        B.solid(wp().box(78, 4, 9, centered=False).translate((-134, y - 2, Hm.DECK)).edges('|X and >Z').fillet(1.8).val(), OLIVE_D, 0.3, label='rail')
    B.solid(wp().circle(46).extrude(4).edges('>Z').fillet(1.5).translate((-20, YC, Hm.DECK)).val(), OLIVE_D, 0.3, label='pedestal')
    for f in IR.fender('L'), IR.fender('R'):
        B.solid(f, OLIVE, 0.3, label='fender')
    cl, li = IR.claws_big()
    for c in cl: B.solid(c, (0.45, 0.47, 0.51), 0.55, 0.6, label='claw')
    for c in li: B.mesh(cq_tris(c), (1.0, 0.98, 0.88), 0.8)
    B.mesh(cq_tris(cq.Solid.makeCone(2.5, 1.0, 110, cq.Vector(-128, YL - 10, Hm.DECK), cq.Vector(-0.15, 0, 1))), (0.15, 0.15, 0.16), 0.6)  # whip antenna
    # the arm mid-ship, reaching the ground in front, left of the head
    tip = arm(B, -20.0, Hm.DECK + 4, 56.5, -48.0, yaw=22.0)
    insides(B, packs_x0=-121, packs_z=Hm.FLOOR + 0.2, brain=(25, YC, 58), power=(-112, YC, 66))
    return B, tk, dict(deck=Hm.DECK, floor0=Hm.FLOOR0, z0=z0, tip=tip,
                       inside=(236 * 131.5 + np.pi * 34.2 ** 2 / 2) * 50 + 2 * 186 * 54 * 23 + 186 * 131.5 * 29.6)

# ================================================================ baseline: the redesign as rendered
def baseline():
    B = Build('Baseline')
    sp = dict(sprocket=IR.SPROCKET, idler=IR.IDLER, wheels=IR.WHEELS, rollers=IR.ROLLERS, tw=IR.TW, t=IR.TRACK_T, g=IR.GROUSER, gap=6)
    tk = tracks(B, sp, (STEEL, ACC))
    z0 = head(B, Hm.FLOOR)
    Hm.HATCH = (-98.0, -48.0, 41.0, 55.5)
    B.solid(Hm.tub(), OLIVE_D, 0.3, label='tub'); B.solid(Hm.turret_deck(), OLIVE, 0.3, label='turret deck')
    B.solid(Hm.carapace(), OLIVE, 0.3, label='carapace'); B.solid(Hm.hatch(), OLIVE_D, 0.3, label='hatch')
    for f in IR.fender('L'), IR.fender('R'):
        B.solid(f, OLIVE, 0.3, label='fender')
    cl, li = IR.claws_big()
    for c in cl: B.solid(c, (0.45, 0.47, 0.51), 0.55, 0.6, label='claw')
    for c in li: B.mesh(cq_tris(c), (1.0, 0.98, 0.88), 0.8)
    arm(B, IR.ARM_X, Hm.DECK, 60.0, -22.0)
    insides(B, packs_x0=-99, packs_z=Hm.FLOOR + 0.2, brain=(-15, -3, 58), power=(-112, YC, 66))
    return B, tk, dict(deck=Hm.DECK, floor0=Hm.FLOOR0, z0=z0,
                       inside=(236 * 131.5 + np.pi * 34.2 ** 2 / 2) * 50 + 2 * 186 * 54 * 23 + 186 * 131.5 * 29.6)

# ================================================================ metrics
def metrics(B, tk, info):
    A = np.vstack([t.reshape(-1, 3) for t, _, _ in B.draw]); lo, hi = A.min(0), A.max(0); g = tk['ground']
    A0 = np.vstack([t.reshape(-1, 3) for i, (t, _, _) in enumerate(B.draw) if i not in B.posable])   # the arm can move away
    m = np.array([w for _, w, _ in B.mass]); c = np.array([p for _, _, p in B.mass]); cog = (m[:, None] * c).sum(0) / m.sum()
    h = cog[2] - g
    front = A0[A0[:, 0] > tk['xf']]; rear = A0[A0[:, 0] < tk['xr']]
    ang = lambda P, x0, s: np.degrees(np.min(np.arctan2(P[:, 2] - g + 1e-6, s * (P[:, 0] - x0)))) if len(P) else 90.0
    half = abs(tk['L']['outer'] - cog[1]), abs(cog[1] - tk['R']['outer'])
    printed = sum(gr for _, gr in B.printed)
    return dict(name=B.name, L=hi[0] - lo[0], W=hi[1] - lo[1], H=hi[2] - g, clearance=info['floor0'] - g, deck=info['deck'] - g,
                lens=info['z0'] + 52 - g, approach=ang(front, tk['xf'], 1), departure=ang(rear, tk['xr'], -1),
                mass=m.sum(), cog=[cog[0], cog[2] - g], tip_side=np.degrees(np.arctan(min(half) / h)),
                tip_front=np.degrees(np.arctan((tk['xf'] - cog[0]) / h)), tip_back=np.degrees(np.arctan((cog[0] - tk['xr']) / h)),
                printed_g=printed, print_h=printed / 25.0, inside_L=info['inside'] / 1e6)

def views(B, name, focal_z=80):
    P = B.draw
    IR.render(P, (760, -820, 430), (10, YC, focal_z), os.path.join(OUT, 'var_%s_front.png' % name))
    IR.render(P, (20, -1300, 120), (10, YC, focal_z + 20), os.path.join(OUT, 'var_%s_side.png' % name))
    IR.render(P, (-780, -650, 520), (10, YC, focal_z), os.path.join(OUT, 'var_%s_rear.png' % name))

if __name__ == '__main__':
    res = []
    for fn in (baseline, scout, crawler, workhorse):
        B, tk, info = fn()
        mt = metrics(B, tk, info); res.append(mt)
        print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in mt.items()})
        if B.name != 'Baseline' or not os.path.exists(os.path.join(OUT, 'var_baseline_front.png')):
            views(B, B.name.lower(), 70 if B.name == 'Scout' else 90)
    json.dump(res, open(os.path.join(OUT, 'variants.json'), 'w'), indent=1, default=float)
