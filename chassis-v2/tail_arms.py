"""Tail arms (brainstorm, 2026-10-04): the Crawler + Workhorse mix Zach asked for, on the v1 legs, with the arm
rising out of the tail, and four arm designs to compare. Visual concepts with numbers; masses and servo
torques are guesses (listed in MASS / SERVO).

    python chassis-v2/hull.py          # first, if out/_hull_meshes.npz is older than the head meshes
    python chassis-v2/tail_arms.py     # ~3 min -> out/tail_arms.html, arms_*.png, arms_reach.png, arms.json

Body: hull.py's fit-checked tub, legs, head, packs and brain, under a new carapace: Crawler armour (sloped
glacis, chamfered sponsons, roll hoop) and a Workhorse cargo bed, with the tail rising aft into a round
pedestal that carries the arm's turntable. Zach (2026-10-04): the head camera turns 360, so the arm need not
reach over the front; the arm carries its own camera and a gripper.

A  Scorpion   two links, parallelogram elbow (his 2026-09-13 option B), wrist; stows like a scorpion's tail
B  Telescope  one luffing boom with a sliding inner tube, wrist; stows flat over the bed
C  Folder     two links with the servos at the joints, wrist; folds flat on the tail
D  Lift       a parallel four-bar from the tail; the tool stays level by geometry; one lift servo
"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import hull as Hm
_keep = {k: getattr(Hm, k) for k in ('FENDER', 'SPL', 'SPR', 'SH_X0', 'TAIL_CLEVIS')}
import ideal_render as IR                  # the VTK renderer; importing it retunes hull's globals for its own tracks
for _k, _v in _keep.items(): setattr(Hm, _k, _v)
import concept as C
from concept import cq, cq_tris, cyl_tris, rbox, T, Rz, YR, YL, YC, OUT

G0 = -18.9                                  # ground: the v1 tracks' lowest point (levelled)
IR.GROUND = G0
wp = lambda: cq.Workplane('XY')

# ---------------------------------------------------------------- body numbers (guesses unless noted)
DECK = Hm.DECK                              # 87: the ESCs set it (sponsons over the fenders)
SLOPE_X0, SLOPE_X1 = -64.0, -100.0          # the tail rises from the bed's back edge...
PZ = 108.0                                  # ...to the pedestal top (21 over 36: 30 deg)
AX = -104.0                                 # the arm's yaw axis, on the centre line (pedestal flush with the back wall)
PED_R = 33.0                                # pedestal: the turntable's lazy-susan (r 32*) sits on it
TT = PZ + 12.0                              # turntable top: 6 bearing + 6 disc
HOOP_X, HOOP_TOP, HOOP_R = 40.0, 150.0, 6.0 # roll hoop behind the head, out of the cradle's sweep (X <= 56)
BED = (-62.0, -48.0, 30.0, 55.5)            # hatch = cargo bed lid over the brain bay: X0, Y0, X1, Y1
ROLL = ((HOOP_X, HOOP_TOP + HOOP_R), (-136.0, 100.0))   # roll line: hoop top to the tail's back corner

OLIVE, OLIVE_D, STEEL, DARK, ACC, JAW = (0.42, 0.48, 0.41), (0.33, 0.38, 0.33), (0.30, 0.32, 0.35), (0.12, 0.12, 0.13), (0.88, 0.47, 0.18), (0.45, 0.47, 0.51)

def carapace():
    """Crawler armour over hull.py's tub: sloped glacis, chamfered sponsons (ESCs inside, as checked), and the
    centre rising aft into the tail hump, which ends in the pedestal."""
    prof = [(-136, Hm.TUB_TOP), (50, Hm.TUB_TOP), (50, 70), (34, DECK), (SLOPE_X0, DECK), (SLOPE_X1, PZ), (-128, PZ), (-136, PZ - 8)]
    w = YL - YR
    o = cq.Workplane('XZ').polyline(prof).close().extrude(-w).translate((0, YR, 0))
    sp = [(Hm.SH_X0, Hm.FENDER), (Hm.SH_X0, DECK - 7), (Hm.SH_X0 + 7, DECK), (34, DECK), (50, 70), (50, Hm.FENDER)]
    for y0, y1, e in ((YL, Hm.SPL, '>Y'), (Hm.SPR, YR, '<Y')):            # the outboard top edge chamfered, as hull.py
        o = o.union(cq.Workplane('XZ').polyline(sp).close().extrude(-(y1 - y0)).translate((0, y0, 0)).edges('|X and >Z and %s' % e).chamfer(7))
    o = o.union(wp().circle(PED_R).extrude(PZ - DECK).translate((AX, YC, DECK)))
    inner = cq.Workplane('XZ').polyline(prof).close().offset2D(-2.4).extrude(-(w - 4.8)).translate((0, YR + 2.4, 0))
    o = o.cut(inner).cut(wp().box(184, w - 4.8, 8, centered=False).translate((-133.6, YR + 2.4, Hm.TUB_TOP - 4)))
    o = o.cut(wp().circle(PED_R - 2.4).extrude(PZ - 2.4 - DECK + 4).translate((AX, YC, DECK - 4)))
    for y0, y1, e in ((YL, Hm.SPL - 2.4, '>Y'), (Hm.SPR + 2.4, YR, '<Y')):
        o = o.cut(cq.Workplane('XZ').polyline(sp).close().offset2D(-2.4).extrude(-(y1 - y0)).translate((0, y0, 0))
                  .edges('|X and >Z and %s' % e).chamfer(5))
    for yo in (Hm.SPL, Hm.SPR):                                         # hooded louvres, ESC LED windows
        for i in range(8):
            o = o.cut(wp().box(5, 8, 11).translate((-92 + 15 * i, yo, Hm.FENDER + 13)))
        o = o.cut(wp().workplane().transformed(rotate=(90, 0, 0)).circle(2.5).extrude(10, both=True).translate((-4, yo, Hm.FENDER + 16)))
    x0, y0, x1, y1 = BED
    o = o.cut(wp().box(x1 - x0 - 6, y1 - y0 - 6, 6, centered=False).translate((x0 + 3, y0 + 3, DECK - 4)))   # brain bay opening
    o = o.cut(wp().circle(4).extrude(10).translate((AX, YC, PZ - 5)))                                         # yaw spline
    for y, wd in ((-44, 16), (-24, 16), (28, 10), (42, 10)):                                                  # ports, back panel
        o = o.cut(wp().box(6, wd, 8, centered=False).translate((-137, y, 62)))
    return o.val()

def bed():
    """the hatch over the brain bay, as a cargo bed: vents over the Pi, a lip, 4 tie-down eyes"""
    x0, y0, x1, y1 = BED
    h = wp().box(x1 - x0, y1 - y0, 2.4, centered=False).translate((x0, y0, DECK)).edges('|Z').fillet(6)
    for i in range(6):                                                  # vents over the Pi, stopping short of the stow post
        h = h.cut(wp().box(4, 44, 6).translate((-50 + 9 * i, Hm.PI_C[1], DECK)))
    h = h.union(wp().box(x1 - x0, y1 - y0, 6, centered=False).translate((x0, y0, DECK + 2.4)).edges('|Z').fillet(6)
                .cut(wp().box(x1 - x0 - 5, y1 - y0 - 5, 6, centered=False).translate((x0 + 2.5, y0 + 2.5, DECK + 2.4)).edges('|Z').fillet(4)))
    for x in (x0 + 9, x1 - 9):
        for y in (y0 + 9, y1 - 9):
            eye = cq.Workplane('XZ').circle(5).circle(2.5).extrude(2, both=True).translate((x, y, DECK + 8.4))
            h = h.union(eye.cut(wp().box(12, 6, 10).translate((x, y, DECK + 2.4 - 5 + 4.4))))
    return h.val()

def hoop():
    """roll hoop: rollover guard over the head, carry handle, and the arm's rest (a saddle on top)"""
    half = Hm.SPL - YC - 18
    tt = np.linspace(-1, 1, 41); ys = YC + tt * half; zs = DECK - 5 + (HOOP_TOP - DECK + 5) * (1 - tt ** 2) ** 0.5
    tube = np.vstack([cyl_tris((HOOP_X, ys[i], zs[i]), (HOOP_X, ys[i + 1], zs[i + 1]), HOOP_R, 20) for i in range(40)])
    sad = wp().box(16, 30, 10).translate((HOOP_X, YC, HOOP_TOP + HOOP_R + 1)).cut(
        cq.Workplane('YZ').circle(HOOP_R).extrude(20, both=True).translate((HOOP_X, YC, HOOP_TOP))).cut(
        wp().box(18, 22, 10).translate((HOOP_X, YC, HOOP_TOP + HOOP_R + 6)))                # U: the arm drops in
    feet = [wp().box(20, 14, 4).translate((HOOP_X, y, zs[0 if y < YC else -1] - 1)).val() for y in (ys[0], ys[-1])]
    return tube, sad.val(), feet

# ---------------------------------------------------------------- arms: drawn in the arm's plane (r out along the yaw, z up), then turned
SERVO = {  # name: (stall kg.cm at 6 V*, mass g*, body L x W x H*)
    'MG996R': (11.0, 55, (40.7, 19.7, 42.9)), 'DS3218': (21.0, 60, (40, 20, 40.5)), 'MG90S': (2.0, 13.4, (22.8, 12.2, 28.5)),
    'N20+screw': (None, 20, (12, 10, 34))}
MASS = {'tool': 60, 'payload': 100, 'cam': 5}    # tool = wrist MG90S + gripper MG90S + arm camera + printed housing (all guesses)

def bar(p0, p1, w, h, r=3.0, dy=0.0):
    """a rounded bar from p0 to p1 (r, z), w across, h deep, centred at y = dy (arm frame)"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); d = p1 - p0; L = max(np.hypot(*d), 0.1)
    ang = np.degrees(np.arctan2(d[1], d[0])); c = (p0 + p1) / 2
    return wp().box(L, w, h).edges('|Y').fillet(min(r, h / 2 - 0.01, L / 2 - 0.01)).rotate((0, 0, 0), (0, 1, 0), -ang).translate((c[0], dy, c[1])).val()
def pin(p, w, r): return cq.Workplane('XZ').circle(r).extrude(w / 2, both=True).translate((p[0], 0, p[1])).val()
def tube(p0, p1, r0, r1=None):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); d = p1 - p0; L = np.hypot(*d); u = d / L
    return cq.Solid.makeCone(r0, r1 or r0, L, cq.Vector(p0[0], 0, p0[1]), cq.Vector(u[0], 0, u[1]))
U = lambda deg: np.array([np.cos(np.radians(deg)), np.sin(np.radians(deg))])

def tool(W, g):
    """wrist at W, tool pointing g deg: wrist servo housing, the arm camera on top looking along the jaws, two jaws"""
    u = U(g); n = U(g + 90); out = []
    out.append((wp().box(30, 24, 22).edges().fillet(5).rotate((0, 0, 0), (0, 1, 0), -g).translate((*(W + 12 * u)[:1], 0, (W + 12 * u)[1])).val(), ACC, 'tool'))
    cb = W + 14 * u + 14 * n
    out.append((wp().box(10, 25, 24).edges().fillet(2).rotate((0, 0, 0), (0, 1, 0), -g).translate((cb[0], 0, cb[1])).val(), DARK, 'cam'))
    lc = cb + 6 * u
    out.append((cq.Workplane('XY').add(cq.Solid.makeCylinder(5, 5, cq.Vector(lc[0], 0, lc[1]), cq.Vector(u[0], 0, u[1]))).val(), (0.2, 0.3, 0.5), 'lens'))
    for dy in (-8, 8):
        out.append((bar(W + 24 * u, W + 60 * u, 4.5, 9, 2.2, dy), JAW, 'jaw'))
    return out, W + 62 * u

class Arm:
    """one design: geometry per pose, joint limits for the reach sampling, mass items for the torques"""
    name = key = ''
    def parts(s, q): raise NotImplementedError
    def base(s, h=36):
        """bearing + turntable + a fairing round the shoulder servos (all designs share it)"""
        return [(wp().circle(32).circle(22).extrude(6).translate((0, 0, PZ)).val(), STEEL, 'bearing'),
                (wp().circle(31).extrude(6).edges('>Z').fillet(2).translate((0, 0, PZ + 6)).val(), OLIVE_D, 'turntable')]

def fairing(h, w=128, l=62, cut_w=40):
    f = wp().box(l, w, h).edges('|Z').fillet(16).edges('>Z').fillet(12).translate((2, 0, TT + h / 2))
    f = f.cut(wp().box(l - 6, w - 6, h).edges('|Z').fillet(13).translate((2, 0, TT + h / 2 - 3)))
    return f.cut(wp().box(l + 10, cut_w, 30).translate((-4, -3, TT + h))).val()

class Scorpion(Arm):
    """A: his option B, sized for the tail: shoulder and elbow servos side by side on the turntable; the elbow
    drives the forearm through a crank and pushrod (a parallelogram), so no servo rides on the arm."""
    key, name, HALF = 'A', 'Scorpion', 13
    S = np.array([0.0, TT + 28]); L1, L2, LEV = 100.0, 160.0, 26.0
    servos = ['MG996R (yaw)', 'DS3218 (shoulder)', 'DS3218 (elbow, via pushrod)', 'MG90S (wrist)', 'MG90S (gripper)']
    def limits_ok(s, q):
        a1, a2, gw = q; rel = a2 - a1
        return 15 <= a1 <= 165 and -160 <= rel <= -15 and -110 <= gw - a2 <= 110
    def fk(s, q):
        a1, a2, g = q; E = s.S + s.L1 * U(a1); W = E + s.L2 * U(a2); return dict(S=s.S, E=E, W=W, g=g)
    def parts(s, q):
        a1, a2, g = q; k = s.fk(q); S, E, W = k['S'], k['E'], k['W']
        lv = s.LEV * U(a2 + 180); C1, C2 = S + lv, E + lv
        P = s.base() + [(fairing(40), OLIVE, 'fairing')]
        for dy in (-9.5, 9.5): P.append((bar(S, E, 3, 24, 12, dy), (0.36, 0.38, 0.41), 'upper arm'))
        P += [(pin(S, 24, 8), STEEL, 'shoulder'), (pin(E, 24, 8), STEEL, 'elbow pin')]
        P += [(bar(S, C1, 7, 9, 4.4, -15), STEEL, 'crank'), (bar(C1, C2, 5, 5, 2.4, -15), DARK, 'pushrod'),
              (bar(E, C2, 9, 12, 5.9, -15), OLIVE_D, 'rear lever')]
        P.append((wp().box(30, 24, 26).edges().fillet(6).rotate((0, 0, 0), (0, 1, 0), -a2).translate((E[0], 0, E[1])).val(), OLIVE_D, 'elbow hub'))
        P.append((tube(E + 12 * U(a2), W - 4 * U(a2), 8.5, 6.5), DARK, 'forearm'))
        t, tip = tool(W, g); return P + t, tip
    def masses(s, q):
        k = s.fk(q); S, E, W = k['S'], k['E'], k['W']
        return dict(shoulder=[(30, (S + E) / 2), (20, E), (35, (E + W) / 2), (MASS['tool'], W + 18 * U(q[2])), (MASS['payload'], W + 50 * U(q[2]))],
                    elbow=[(35, (E + W) / 2), (MASS['tool'], W + 18 * U(q[2])), (MASS['payload'], W + 50 * U(q[2]))])
    def joints(s, q): k = s.fk(q); return {'shoulder': k['S'], 'elbow': k['E']}
    def sample(s):
        for a1 in np.arange(15, 166, 5):
            for a2 in np.arange(a1 - 160, a1 - 14, 5):
                for g in (a2 - 110, a2 - 55, a2, a2 + 55, a2 + 110, -90):
                    if s.limits_ok((a1, a2, g)): yield (a1, a2, g)
    def ik(s, W, g):
        for sg in (1, -1):                                              # elbow up first
            q = two_link(s.S, s.L1, s.L2, W, sg)
            if q and s.limits_ok((q[0], q[1], g)): return (q[0], q[1], g)
    def iks(s, W, g): return [(q[0], q[1], g) for q in (two_link(s.S, s.L1, s.L2, W, sg) for sg in (1, -1)) if q and s.limits_ok((q[0], q[1], g))]
    def high(s): return (100, 85, 0)

def two_link(S, L1, L2, W, sg):
    d = np.asarray(W, float) - S; D = np.hypot(*d)
    if not abs(L1 - L2) < D < L1 + L2: return None
    b = np.degrees(np.arccos((L1 ** 2 + D ** 2 - L2 ** 2) / (2 * L1 * D))); a1 = np.degrees(np.arctan2(d[1], d[0])) + sg * b
    E = S + L1 * U(a1); a2 = np.degrees(np.arctan2(*(np.asarray(W) - E)[::-1]))
    while a2 - a1 > 180: a2 -= 360
    while a2 - a1 < -180: a2 += 360
    return a1, a2

class Telescope(Arm):
    """B: one boom that luffs from forward-down, over the top, to back-down; an inner tube slides out 100 mm on a
    lead screw; a wrist at the tip. The fewest links; the slide is the hard part to print."""
    key, name, HALF = 'B', 'Telescope', 14
    S = np.array([0.0, TT + 24]); R0, EXT = 125.0, 130.0
    servos = ['MG996R (yaw)', 'DS3218 (luff, 270 deg)', 'N20 gearmotor + M3 lead screw (slide)', 'MG90S (wrist)', 'MG90S (gripper)']
    def limits_ok(s, q):
        b, e, g = q; return -50 <= b <= 225 and 0 <= e <= s.EXT and -110 <= ((g - b + 180) % 360) - 180 <= 110
    def fk(s, q):
        b, e, g = q; W = s.S + (s.R0 + e) * U(b); return dict(S=s.S, W=W, g=g)
    def parts(s, q):
        b, e, g = q; u = U(b); S = s.S; W = S + (s.R0 + e) * u
        P = s.base() + [(fairing(34, w=96, cut_w=34), OLIVE, 'fairing')]
        P.append((pin(S, 30, 11), STEEL, 'luff pivot'))
        P.append((bar(S - 30 * u, S + 108 * u, 26, 22, 5), OLIVE_D, 'outer tube'))
        P.append((bar(S + 90 * u, S + (s.R0 - 2 + e) * u, 18, 15, 4), (0.36, 0.38, 0.41), 'inner tube'))
        P.append((bar(S - 30 * u, S - 6 * u, 28, 26, 6), DARK, 'slide motor'))
        t, tip = tool(W, g); return P + t, tip
    def masses(s, q):
        b, e, g = q; u = U(b); S = s.S; W = S + (s.R0 + e) * u
        return dict(luff=[(45, S + 45 * u), (20, S - 18 * u), (22, S + (100 + s.R0 + e) / 2 * u), (MASS['tool'], W + 18 * U(g)), (MASS['payload'], W + 50 * U(g))])
    def joints(s, q): return {'luff': s.S}
    def sample(s):
        for b in np.arange(-50, 226, 4):
            for e in np.arange(0, s.EXT + 1, 10):
                for g in (b - 110, b - 55, b, b + 55, b + 110, -90, 270):
                    if s.limits_ok((b, e, g)): yield (b, e, g)
    def ik(s, W, g):
        d = np.asarray(W, float) - s.S; b = np.degrees(np.arctan2(d[1], d[0])); e = np.hypot(*d) - s.R0
        q = (b, e, g); return q if s.limits_ok(q) else None
    def iks(s, W, g): q = s.ik(W, g); return [q] if q else []
    def high(s): return (90, s.EXT, 0)
    STOW = (8.5, 40.0, 0.0)          # too long for the bed post: the inner tube rests in the hoop's saddle, the jaws forward over the head

class Folder(Arm):
    """C: plain serial arm, a servo at each joint (shoulder on the turntable, elbow on the upper arm, wrist); the
    elbow folds 165 deg each way, so the arm folds flat on the tail."""
    key, name, HALF = 'C', 'Folder', 10
    S = np.array([0.0, TT + 22]); L1, L2 = 110.0, 110.0
    servos = ['MG996R (yaw)', 'DS3218 (shoulder)', 'MG996R (elbow, on the arm)', 'MG90S (wrist)', 'MG90S (gripper)']
    def limits_ok(s, q):
        a1, a2, g = q; return 0 <= a1 <= 180 and -165 <= a2 - a1 <= 165 and -110 <= g - a2 <= 110
    def fk(s, q):
        a1, a2, g = q; E = s.S + s.L1 * U(a1); W = E + s.L2 * U(a2); return dict(S=s.S, E=E, W=W, g=g)
    def parts(s, q):
        a1, a2, g = q; k = s.fk(q); S, E, W = k['S'], k['E'], k['W']
        P = s.base() + [(fairing(30, w=90, cut_w=30), OLIVE, 'fairing')]
        P.append((bar(S, E, 22, 18, 8, 0), (0.36, 0.38, 0.41), 'upper arm'))
        P.append((wp().box(42, 22, 22).edges().fillet(4).rotate((0, 0, 0), (0, 1, 0), -a1).translate((E[0] - 8 * U(a1)[0], 22, E[1] - 8 * U(a1)[1])).val(), DARK, 'elbow servo'))
        P.append((bar(E, W, 18, 14, 6, -20), OLIVE_D, 'forearm'))
        P += [(pin(S, 30, 9), STEEL, 'shoulder'), (pin(E, 62, 7), STEEL, 'elbow')]
        t, tip = tool(W, g); return P + t, tip
    def masses(s, q):
        k = s.fk(q); S, E, W = k['S'], k['E'], k['W']; g = q[2]
        return dict(shoulder=[(35, (S + E) / 2), (SERVO['MG996R'][1], E), (25, (E + W) / 2), (MASS['tool'], W + 18 * U(g)), (MASS['payload'], W + 50 * U(g))],
                    elbow=[(25, (E + W) / 2), (MASS['tool'], W + 18 * U(g)), (MASS['payload'], W + 50 * U(g))])
    def joints(s, q): k = s.fk(q); return {'shoulder': k['S'], 'elbow': k['E']}
    def sample(s):
        for a1 in np.arange(0, 181, 5):
            for a2 in np.arange(a1 - 165, a1 + 166, 5):
                for g in (a2 - 110, a2 - 55, a2, a2 + 55, a2 + 110, -90):
                    if s.limits_ok((a1, a2, g)): yield (a1, a2, g)
    def ik(s, W, g):
        for sg in (1, -1):
            q = two_link(s.S, s.L1, s.L2, W, sg)
            if q and s.limits_ok((q[0], q[1], g)): return (q[0], q[1], g)
    def iks(s, W, g): return [(q[0], q[1], g) for q in (two_link(s.S, s.L1, s.L2, W, sg) for sg in (1, -1)) if q and s.limits_ok((q[0], q[1], g))]
    def high(s): return (90, 90, 0)

class Lift(Arm):
    """D: a parallel four-bar from the tail: two links, base pivots 30 apart, so the tool plate never tilts. The
    jaws always point down and the camera's horizon stays level, with one lift servo. No wrist."""
    key, name, HALF = 'D', 'Lift', 9
    P1 = np.array([0.0, TT + 26]); P2 = np.array([0.0, TT + 56]); L = 175.0   # pivots high enough to clear the tail's back corner
    servos = ['MG996R (yaw)', 'DS3218 (lift, 270 deg)', 'MG90S (gripper)']
    def limits_ok(s, q): return -35 <= q[0] <= 215
    def fk(s, q):
        a = q[0]; Q1 = s.P1 + s.L * U(a); W = Q1 + np.array([0, -6.0]); return dict(Q1=Q1, Q2=s.P2 + s.L * U(a), W=W, g=-90)
    def parts(s, q):
        a = q[0]; k = s.fk(q); Q1, Q2, W = k['Q1'], k['Q2'], k['W']
        P = s.base() + [(fairing(56, w=96, l=56, cut_w=26), OLIVE, 'fairing')]
        for dy in (-13, 13):
            P.append((bar(s.P1, Q1, 4, 16, 7, dy), (0.36, 0.38, 0.41), 'lower link'))
        P.append((bar(s.P2, Q2, 10, 12, 5.5, 0), OLIVE_D, 'upper link'))
        P.append((bar(Q1 + [0, -2], Q2 + [0, 6], 36, 12, 5), OLIVE_D, 'tool plate'))
        P += [(pin(s.P1, 34, 7), STEEL, 'pivot'), (pin(s.P2, 16, 6), STEEL, 'pivot'), (pin(Q1, 34, 6), STEEL, 'pivot'), (pin(Q2, 16, 5), STEEL, 'pivot')]
        t, tip = tool(W, -90); return P + t, tip
    def masses(s, q):
        k = s.fk(q); a = q[0]
        return dict(lift=[(24, s.P1 + s.L / 2 * U(a)), (14, s.P2 + s.L / 2 * U(a)), (12, k['Q1']), (MASS['tool'] - 13, k['W'] + [0, -18]), (MASS['payload'], k['W'] + [0, -50])])
    def joints(s, q): return {'lift': s.P1}
    def sample(s):
        for a in np.arange(-35, 216, 1.0): yield (a,)
    def ik(s, W, g):
        z = W[1] + 6                                                    # the tool hangs 6 under Q1; r is what the height allows
        sa = (z - s.P1[1]) / s.L
        if abs(sa) > 1: return None
        for a in (np.degrees(np.arcsin(sa)), 180 - np.degrees(np.arcsin(sa))):    # out front, or over the top
            if s.limits_ok((a,)) and abs(s.L * np.cos(np.radians(a)) - W[0]) <= 2.0: return (a,)
    def iks(s, W, g): q = s.ik(W, g); return [q] if q else []
    def high(s): return (90,)
    STOW = (135,)                                                       # sloping up and back, the tool hanging like a stinger

ARMS = [Scorpion(), Telescope(), Folder(), Lift()]

def place(sh, yaw):
    return sh.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), yaw).translate(cq.Vector(AX, YC, 0))
STOW_POST = (6.0, DECK + 2.4, DECK + 16.0)   # a knob at the bed's front: the jaws hold it while driving
TGT = {  # pose: (yaw, jaw tip r, jaw tip z), tool pointing down
    'stow': (0, STOW_POST[0] - AX, DECK + 10.0),        # jaws round the stow post
    'side': (90, 150.0, G0 + 2.0),                      # the ground, 29 outside the left sponson
    'back': (180, 90.0, G0 + 2.0),                      # the ground, 62 behind the tail
}
def pose_q(A, pose):
    if pose == 'high': return A.high(), 0
    if pose == 'stow' and hasattr(A, 'STOW'): return A.STOW, 0
    if pose in getattr(A, 'pick', {}): return A.pick[pose]
    if pose != 'stow': return None, TGT[pose][0]
    yaw, r, z = TGT[pose]
    return A.ik(np.array([r, z]) - 62 * U(-90), -90), yaw
def arm_pose(A, pose):
    q, yaw = pose_q(A, pose)
    if q is None: return None, None, None, yaw
    P, tip = A.parts(q)
    return [(place(sh, yaw), rgb, lab) for sh, rgb, lab in P], tip, q, yaw

def to_world(p_rz, yaw):
    r, z = p_rz; return np.array([AX + r * np.cos(np.radians(yaw)), YC + r * np.sin(np.radians(yaw)), z])

# ---------------------------------------------------------------- the body: hull.py's checked parts + the new ones
KEEP = ['pod_', 'of_', 'track_', 'cog_rear_', 'cog_front_', 'rollers_', 'crown_', 'motor_', 'pinion_', 'tub', 'tray', 'tdeck', 'fender0', 'fender1',
        'claw0', 'claw1', 'light0', 'light1', 'esc_L', 'esc_R', 'alarm', 'pi_switch', 'batt', 'pi', 'hat', 'hailo', 'pca',
        'base', 'drum', 'cradle', 'ball']
NEW_COMP = {  # key: (label, centre, size)   all sizes guesses
    'yaw_servo': ('Arm yaw servo (MG996R*), under the pedestal, across the hull', (AX, YC + 10.0, 80.15), (19.7, 40.7, 42.9)),
    'ubec': ('UBEC 5 V / 5 A (Pi only), 6 mm forward of where hull.py had it (it overlapped the Pi switch)', (-102.0, -27.0, 66.0), (45, 26, 12)),
    'ina219': ('INA219 pack monitor (moved: right sponson, rear)', (-60.0, -90.0, 68.0), (26, 21, 4)),
    'wifi': ('USB WiFi + RP-SMA (moved up into the tail hump)', (-113.0, 44.0, 89.0), (40, 18, 10)),
    'arm_ubec': ('Arm UBEC, 8 A* (the arm\'s own servo rail), left sponson behind its ESC', (-70.0, 96.0, 74.0), (50, 30, 15)),
}
def hexrgb(c): return tuple(((c >> s) & 255) / 255 for s in (16, 8, 0))
def body():
    t0 = time.time()
    src = np.load(os.path.join(OUT, '_hull_meshes.npz')); meta = json.load(open(os.path.join(OUT, '_hull_meta.json')))
    M = {}
    def add(k, tris, label, grp, rgb, note=''):
        M[k] = dict(t=np.asarray(tris, float).reshape(-1, 3, 3), label=label, grp=grp, rgb=rgb, note=note)
    for k in src.files:
        if any(k == p or (p.endswith('_') and k.startswith(p)) for p in KEEP):
            m = meta[k]; add(k, src[k], m['label'], m['group'], hexrgb(m['color']), m['note'])
    add('carapace', cq_tris(carapace()), 'Carapace (new)', 'hull', (0.62, 0.56, 0.44),
        'Crawler armour: sloped glacis behind the head, chamfered sponsons (the ESCs inside, as hull.py), and the centre rising aft, 30 deg, into the round pedestal the arm turns on. The power bay under the rise gets 21 mm taller.')
    add('bed', cq_tris(bed()), 'Cargo bed (the brain hatch)', 'hull', (0.50, 0.45, 0.35), 'Lifts off to reach the Pi. A lip and 4 tie-down eyes; vents over the Pi.')
    tb, sad, feet = hoop()
    add('hoop', np.vstack([tb] + [cq_tris(f) for f in feet]), 'Roll hoop', 'hull', (0.22, 0.23, 0.25),
        'Guards the head in a rollover (top 169 over the ground, the ball 151) and is the carry handle. Out of the cradle\'s sweep.')
    add('saddle', cq_tris(sad), 'Hoop saddle', 'hull', (0.22, 0.23, 0.25), 'A spare rest for a long arm.')
    post = wp().circle(4).extrude(STOW_POST[2] - STOW_POST[1]).edges('>Z').fillet(1.5).translate((STOW_POST[0], YC, STOW_POST[1]))
    add('post', cq_tris(post.val()), 'Stow post', 'hull', ACC, 'The gripper holds it while driving, so no servo fights the bumps.')
    add('antenna', np.vstack([cyl_tris((28, 112, DECK), (28, 112, DECK + 105), 4.5, 20), cq_tris(wp().circle(7).extrude(6).translate((28, 112, DECK)).val())]),
        'WiFi antenna (RP-SMA whip)', 'elec', (0.15, 0.15, 0.16), 'Front of the left sponson: out of the arm\'s way. The tail no longer carries it.')
    add('estop', np.vstack([cq_tris(wp().circle(11).extrude(10).translate((-80, -92, DECK)).val()),
                            cq_tris(wp().circle(14).extrude(7).translate((-80, -92, DECK + 10)).edges('>Z').fillet(3).val())]),
        'E-stop', 'elec', (0.78, 0.13, 0.13), 'Right sponson, rear.')
    for k, (lab, c, sz) in NEW_COMP.items():
        add(k, cq_tris(rbox(c, sz)), lab, 'elec', (0.24, 0.6, 0.3), 'Size* is a guess.')
    print('body: %d meshes, %.0f s' % (len(M), time.time() - t0))
    return M

def posed_tris(A, pose):
    P = A.posed.get(pose)
    return None if P is None else np.vstack([cq_tris(sh) for sh, _, _ in P['parts']])

HEAD_CTL = 20.0                          # the sweep first touches the hull between 16 and 20 mm aft
def pairs(M, keys, shift={}):
    t = {k: M[k]['t'] - shift.get(k, [0, 0, 0]) for k in keys}
    return float(sum(C.overlap_mm3(t[a], t[b]) for i, a in enumerate(keys) for b in keys[i + 1:]))
def checks(M, arms):
    g = lambda *ks: np.vstack([M[k]['t'] for k in ks])
    legs = [k for k in M if M[k]['grp'] == 'legs']
    HX, HY = Hm.HX, Hm.HY
    sweep = [T(g('cradle', 'ball') - [HX, HY, 0], Rz(a), (HX, HY, 0)) for a in range(0, 360, 30)]   # one copy per angle
    around = g('carapace', 'bed', 'hoop', 'saddle', 'post', 'fender0', 'fender1', 'claw0', 'claw1', 'tdeck', 'antenna')
    power = ['ubec', 'ina219', 'alarm', 'pi_switch', 'wifi', 'yaw_servo', 'arm_ubec']
    drawer = M['batt']['t'] - [170.0, 0, 0]
    rows = [
        ('Carapace vs legs', M['carapace']['t'], g(*legs), ''),
        ('Carapace 6 mm lower vs legs (control)', M['carapace']['t'] - [0, 0, 6.0], g(*legs), 'must read > 0'),
        ('ESCs vs carapace', g('esc_L', 'esc_R'), M['carapace']['t'], 'in the sponsons, as hull.py'),
        ('ESCs 3 mm higher (control)', g('esc_L', 'esc_R') + [0, 0, 3.0], M['carapace']['t'], 'must read > 0'),
        ('Power bay, yaw servo, arm UBEC vs tub, carapace, left ESC', g(*power), g('tub', 'carapace', 'esc_L'), ''),
        ('Yaw servo 6 mm higher (control)', M['yaw_servo']['t'] + [0, 0, 6.0], M['carapace']['t'], 'must read > 0: it sits under the pedestal'),
        ('Power bay parts vs each other', pairs(M, power), None, 'hull.py only checked them against the walls'),
        ("Power bay with hull.py's UBEC spot (control)", pairs(M, power, {'ubec': [6.0, 0, 0]}), None, 'must read > 0: it overlapped the Pi switch'),
        ('Pi + HAT + PCA vs carapace + bed', g('pi', 'hat', 'hailo', 'pca'), g('carapace', 'bed'), ''),
        ('Pi raised 20 mm (control)', g('pi', 'hat', 'hailo') + [0, 0, 20.0], g('carapace', 'bed'), 'must read > 0'),
        ('Head, 12 pan angles, vs carapace, hoop, bed, claws, antenna', sweep, around, ''),
        ('Head %.0f mm aft (control)' % HEAD_CTL, [t - [HEAD_CTL, 0, 0] for t in sweep], around, 'must read > 0: the closest the hull comes'),
        ('Hoop vs legs, ESCs, fenders', g('hoop'), g(*legs, 'esc_L', 'esc_R', 'fender0', 'fender1'), 'its feet stand on the sponsons'),
        ('Packs slid out the back vs tub, carapace', drawer, g('tub', 'carapace'), 'the battery drawer still works'),
    ]
    robot = g(*[k for k in M if M[k]['grp'] in ('legs', 'hull', 'head') or k in ('antenna', 'estop')])
    for A in arms:
        for pose in ('stow', 'side', 'back', 'high'):
            t = posed_tris(A, pose)
            if t is None: continue
            rows.append(('%s %s, %s, vs the robot' % (A.key, A.name, POSE_NAME[pose].lower()), t, robot, ''))
            if pose == 'stow' and A.key != 'D':                       # the moving arm only, onto what it rests on
                mv = np.vstack([cq_tris(sh) for sh, _, lab in A.posed['stow']['parts'] if lab not in ('bearing', 'turntable', 'fairing')])
                dz, why = (3.0, 'the inner tube rests 1.5 over the hoop saddle') if A.key == 'B' else (11.0, 'the jaws straddle the post, 9.6 over the bed')
                rows.append(('%s %s, arm stowed %.0f mm lower (control)' % (A.key, A.name, dz), mv - [0, 0, dz], robot, 'must read > 0: ' + why))
            elif pose == 'stow':
                rows.append(('%s %s, whole arm 8 mm lower (control)' % (A.key, A.name), t - [0, 0, 8.0], robot,
                             'must read > 0: the turntable sinks into the pedestal; stowed, nothing else is near'))
    out = []
    for what, a, b, why in rows:
        v = a if b is None else (sum(C.overlap_mm3(t, b) for t in a) if isinstance(a, list) else C.overlap_mm3(a, b)); out.append(dict(what=what, mm3=v, why=why)); print('%-62s %8.0f mm3' % (what, v))
    return out

# ---------------------------------------------------------------- reach, torque, mass
POSE_NAME = {'stow': 'Stowed', 'side': 'Ground, side', 'back': 'Ground, behind', 'high': 'Periscope'}
RLO, RW, RH = (-420.0, -60.0), 840, 560
def silhouette(M, plane, slab):
    """1 mm raster of the robot projected onto the arm's plane ('xz': yaw 0/180, 'yz': yaw 90), parts within slab of the
    plane, plus the ground; coordinates (r, z) from the yaw axis"""
    from PIL import Image, ImageDraw
    keys = [k for k in M if M[k]['grp'] in ('legs', 'hull', 'head') or k == 'antenna']
    im = Image.new('L', (RW, RH), 0); dr = ImageDraw.Draw(im)
    px = lambda r, z: (r - RLO[0], RH - (z - RLO[1]))
    for k in keys:
        t = M[k]['t']
        if plane == 'xz': keep = np.abs(t[:, :, 1].mean(1) - YC) < slab; P = t[keep][:, :, [0, 2]] - [AX, 0]
        else: keep = np.abs(t[:, :, 0].mean(1) - AX) < slab; P = t[keep][:, :, [1, 2]] - [YC, 0]
        for tri in P: dr.polygon([px(*v) for v in tri], fill=255)
    dr.rectangle([0, px(0, G0)[1], RW, RH], fill=255)
    return np.array(im) > 0

def chain_pts(A, q):
    k = A.fk(q); g = k['g']; Wp = k['W']; tip = Wp + 62 * U(g)
    end = Wp + 30 * U(g)                                                # the tool housing; the jaw tips may touch
    if isinstance(A, Lift): ch = [A.P1, k['Q1'], Wp, end]
    elif isinstance(A, Telescope): ch = [A.S - 30 * U(q[0]), Wp, end]
    else: ch = [A.S, k['E'], Wp, end]
    return ch, tip

def clear(A, q, mask, sgn):
    ch, tip = chain_pts(A, q)
    pts = np.vstack([np.linspace(a, b, 40) for a, b in zip(ch[:-1], ch[1:])]) * [sgn, 1]
    ix = np.round(pts[:, 0] - RLO[0]).astype(int); iz = np.round(RH - (pts[:, 1] - RLO[1])).astype(int)
    ok = (ix >= 0) & (ix < RW) & (iz >= 0) & (iz < RH)
    return ok.all() and not np.any(mask[iz, ix])

def reach(A, mask, sgn=1, step=4.0):
    """jaw tips (r, z; r signed by sgn) the arm reaches with the jaws pointing straight down, its centre line kept
    clear of the robot raster (dilated by the design's link half-depth, HALF); with the joint values that do it"""
    tips, qs = [], []
    for r in np.arange(-320, 330, step):
        for z in np.arange(G0 + 2, 470, step):
            for q in A.iks(np.array([r, z + 62]), -90):
                if clear(A, q, mask, sgn): tips.append((r * sgn, z)); qs.append(q); break
    return np.array(tips).reshape(-1, 2), qs

def pick_poses(A, R):
    """the ground spot nearest the robot that each arm reaches: beside the left track, and behind the tail"""
    A.pick = {}
    for pose, key, yaw, ok in (('side', 'side', 90, lambda r: r >= Hm.SPL - YC + 12), ('back', 'aft', 180, lambda r: r <= -(AX - Hm.TUB_X0) - 12)):
        tips, qs = R[A.key][key]
        cand = [(abs(t[0]), q, yaw) for t, q in zip(tips, qs) if t[1] <= G0 + 2.5 and ok(t[0])]
        if pose == 'back':                                              # or over the top, yaw 0
            tf, qf = R[A.key]['fwd']; cand += [(abs(t[0]), q, 0) for t, q in zip(tf, qf) if t[1] <= G0 + 2.5 and ok(t[0])]
        if cand: c = min(cand, key=lambda c: c[0]); A.pick[pose] = (c[1], c[2])

def torques(A):
    worst = {}
    for q in A.sample():
        J = A.joints(q)
        for j, items in A.masses(q).items():
            worst[j] = max(worst.get(j, 0), abs(sum(m / 1000 * (p[0] - J[j][0]) / 10 for m, p in items)))
    return worst

def arm_mass(A):
    servo_g = {'MG996R': 55, 'DS3218': 60, 'MG90S': 13.4, 'N20': 20}
    sv = sum(next(v for k_, v in servo_g.items() if s.startswith(k_)) for s in A.servos)
    q = A.high()
    skip = ('bearing', 'lens', 'cam', 'shoulder', 'elbow', 'elbow pin', 'pivot', 'luff pivot', 'slide motor', 'elbow servo', 'jaw')
    pr = sum(sh.Volume() for sh, _, lab in A.parts(q)[0] if lab not in skip) * 1.24e-3 * 0.35
    return sv + pr + 40 + 10      # + lazy-susan bearing 40*, camera + leads 10*

def mesh_vol(t):
    t = np.asarray(t).reshape(-1, 3, 3); return abs(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6)

def robot_mass(M):
    """items (g, centre) for the robot without the arm. Printed at 35 % of solid (walls + infill)*; packs 300*, motors 184."""
    items = []
    for k, v in M.items():
        c = v['t'].reshape(-1, 3).mean(0)
        if k.startswith('motor_'): items.append((184, c))
        elif k.startswith('track_'): items.append((mesh_vol(v['t']) * 1.21e-3 * 0.9, c))
        elif v['grp'] in ('legs', 'hull'): items.append((mesh_vol(v['t']) * 1.24e-3 * 0.35, c))
    batt = M['batt']['t'].reshape(-1, 3)
    for y in (-22.15, 28.85): items.append((300, (batt[:, 0].mean(), y, 23)))
    items += [(210, (Hm.HX, YC, 95)), (95, (-15, -3, 60)), (110, (-18, YC, 73)), (70, (-110, 0, 68)), (60, (0, YC, 50))]
    return items

def cog(items):
    m = np.array([g for g, _ in items]); c = np.array([p for _, p in items], float)
    return (m[:, None] * c).sum(0) / m.sum(), m.sum()

def arm_items(A, pose):
    """arm mass items in the world for a pose, with 100 g in the jaws"""
    q, yaw = pose_q(A, pose); items = []
    if q is None: return []
    for j, its in list(A.masses(q).items())[:1]:
        for m, p in its: items.append((m, to_world(p, yaw)))
    items.append((arm_mass(A) - sum(m for m, _ in items) + MASS['payload'], to_world((0, TT), yaw)))   # servos + base on the turntable
    return items

# ---------------------------------------------------------------- pictures
COLS = {'A': '#C05A2B', 'B': '#2F6FA8', 'C': '#4A8A3C', 'D': '#8A4FA3'}
def scene(M):
    return [(v['t'], v['rgb'], 0.5 if v['grp'] == 'head' else 0.3) for k, v in M.items() if v['grp'] != 'elec' or k in ('antenna', 'estop')]
def arm_scene(A, pose):
    P = A.posed.get(pose)
    return [] if P is None else [(np.asarray(cq_tris(sh), float).reshape(-1, 3, 3), rgb, 0.45) for sh, rgb, _ in P['parts']]

def renders(M, arms):
    base = scene(M); names = []
    for A in arms:
        pick = 'side' if 'side' in A.posed else 'back'
        for pose, cam, foc in (('stow', (-820, -700, 560), (-10, YC, 120)),
                               (pick, (560, 980, 520) if pick == 'side' else (-760, 820, 480), (-60, 70, 70) if pick == 'side' else (-150, YC, 80))):
            fn = 'arms_%s_%s.png' % (A.key, pose)
            IR.render(base + arm_scene(A, pose), cam, foc, os.path.join(OUT, fn), size=(1200, 820))
            names.append((fn, '%s  %s: %s' % (A.key, A.name, {'stow': 'stowed', 'side': 'picking up beside the left track', 'back': 'picking up behind'}[pose])))
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(os.path.join(OUT, n)) for n, _ in names]; w, h = ims[0].size
    sh = Image.new('RGB', (w * 2, h * len(arms)), 'white'); d = ImageDraw.Draw(sh)
    try: f = ImageFont.truetype('arialbd.ttf', 34)
    except Exception: f = ImageFont.load_default()
    for i, (im, (_, lab)) in enumerate(zip(ims, names)):
        x, y = (i % 2) * w, (i // 2) * h; sh.paste(im, (x, y)); d.text((x + 24, y + 18), lab, fill=(30, 33, 30), font=f)
    sh.resize((w, h * len(arms) // 2), Image.LANCZOS).save(os.path.join(OUT, 'arms_sheet.png')); print('wrote arms_sheet.png')
    return names

def reach_figure(M, arms, R):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    ctx = {'xz': silhouette(M, 'xz', 400), 'yz': silhouette(M, 'yz', 400)}
    fig, axs = plt.subplots(len(arms), 2, figsize=(13, 3.5 * len(arms)), gridspec_kw=dict(width_ratios=[1.45, 1]))
    ext = [RLO[0], RLO[0] + RW, RLO[1], RLO[1] + RH]
    for i, A in enumerate(arms):
        for j, plane in enumerate(('xz', 'yz')):
            ax = axs[i, j]; ax.imshow(np.where(ctx[plane], 0.80, 1.0), cmap='gray', vmin=0, vmax=1, extent=ext, origin='upper')
            col = COLS[A.key]
            for t in (R[A.key]['fwd'][0], R[A.key]['aft'][0]) if plane == 'xz' else (R[A.key]['side'][0],):
                if len(t): ax.scatter(t[:, 0], t[:, 1], s=2, c=col, alpha=0.18, lw=0)
            poses = (('stow', 0, 1), ('back', 180, -1), ('high', 0, 1)) if plane == 'xz' else (('side', 90, 1),)
            for pose, _, sg in poses:
                q, _ = pose_q(A, pose)
                if q is None: continue
                ch, tip = chain_pts(A, q); ch = np.array(ch) * [sg, 1]
                ax.plot(ch[:, 0], ch[:, 1], '-o', color=col, lw=2.2, ms=3.5, alpha=0.95 if pose != 'high' else 0.5)
            ax.axhline(G0, color='#444', lw=0.8)
            if plane == 'xz':
                ax.set_xlim(-330, 260); ax.set_title('%s %s: side view, forward right (reach ahead and behind)' % (A.key, A.name), fontsize=10, loc='left')
            else:
                ax.set_xlim(-60, 330); ax.set_title('across, to the left (yaw 90)', fontsize=10, loc='left')
            ax.set_ylim(-40, 460); ax.set_aspect('equal'); ax.tick_params(labelsize=7); ax.grid(alpha=0.25)
    fig.text(0.01, 0.003, 'Shaded dots: jaw-tip positions reachable with the jaws pointing down (+-15 deg), sampled; grey: the robot near the arm\'s plane. '
             'X and Y are measured from the arm\'s yaw axis (X -108).', fontsize=8.5)
    fig.tight_layout(rect=(0, 0.01, 1, 1)); p = os.path.join(OUT, 'arms_reach.png'); fig.savefig(p, dpi=110); plt.close(fig); print('wrote', p)

# ---------------------------------------------------------------- numbers
def numbers(M, arms, R):
    base_items = robot_mass(M); c0, m0 = cog(base_items); ground = G0
    track_out = M['track_L']['t'].reshape(-1, 3)[:, 1].max(); track_in_R = M['track_R']['t'].reshape(-1, 3)[:, 1].min()
    out = []
    for A in arms:
        tq = torques(A); mass = arm_mass(A)
        rows = dict(key=A.key, name=A.name, servos=A.servos, mass=mass, torques={k: round(v, 1) for k, v in tq.items()})
        drv = [s for s in A.servos if 'yaw' not in s and 'wrist' not in s and 'gripper' not in s]
        sf = {}
        for j, v in tq.items():
            s = next((s for s in drv if j in s), drv[0]); stall = SERVO[s.split(' ')[0]][0]
            if stall: sf[j] = (s.split(' ')[0], stall, stall / v)
        rows['sf'] = {k: (n, st, round(f, 1)) for k, (n, st, f) in sf.items()}
        side = R[A.key]['side'][0]; aft = R[A.key]['aft'][0]
        gs = side[(side[:, 1] <= G0 + 2.5) & (side[:, 0] >= Hm.SPL - YC)]; ga = aft[(aft[:, 1] <= G0 + 2.5) & (aft[:, 0] <= Hm.TUB_X0 - AX)]
        rows['ground_side'] = [float(gs[:, 0].min() + YC), float(gs[:, 0].max() + YC)] if len(gs) else None      # world Y of the jaw tip
        rows['ground_aft'] = [float(ga[:, 0].max() + AX), float(ga[:, 0].min() + AX)] if len(ga) else None       # world X
        q, _ = pose_q(A, 'high'); k = A.fk(q); rows['cam_high'] = float(k['W'][1] + 14 - ground)
        st = A.posed['stow']['parts']; zs = np.vstack([cq_tris(sh).reshape(-1, 3) for sh, _, _ in st])
        rows['stow_top'] = float(zs[:, 2].max() - ground); rows['stow_x'] = [float(zs[:, 0].min()), float(zs[:, 0].max())]
        (x0, z0), (x1, z1) = ROLL
        above = zs[:, 2] - (z1 + (zs[:, 0] - x1) * (z0 - z1) / (x0 - x1))
        rows['stow_above_roll'] = float(max(0, above.max()))
        tp = next(p for p in ('side', 'back', 'high') if p in A.posed); rows['tip_pose'] = tp
        items = base_items + arm_items(A, tp); c1, m1 = cog(items)
        rows['tip_side'] = float(np.degrees(np.arctan((track_out - c1[1]) / (c1[2] - ground))))
        rows['cog_shift'] = float(c1[1] - c0[1]); rows['robot_mass'] = float(m1)
        out.append(rows)
        print(A.key, {k: v for k, v in rows.items() if k not in ('servos',)})
    return dict(arms=out, robot=dict(mass=float(m0), cog=[float(c0[0]), float(c0[1]), float(c0[2] - ground)],
                                     tip_side0=float(np.degrees(np.arctan((track_out - c0[1]) / (c0[2] - ground))))))

# ---------------------------------------------------------------- page
def page(M, arms, Cks, NUM):
    import base64
    D = {'m': {}, 'arms': {}, 'checks': Cks, 'num': NUM, 'yc': YC, 'cols': COLS}
    def pack(t, faces):
        Tk = C.decimate(t, faces); V, F = C.quant(Tk); return {'v': C.b64(V), 'f': C.b64(F), 'i32': F.dtype == np.uint32}
    tohex = lambda rgb: int(rgb[0] * 255) << 16 | int(rgb[1] * 255) << 8 | int(rgb[2] * 255)
    for k, v in M.items():
        D['m'][k] = dict(pack(v['t'], C.faces_for(k)), c=tohex(v['rgb']), grp=v['grp'], label=v['label'], note=v.get('note', ''))
    for A in arms:
        D['arms'][A.key] = {'name': A.name, 'poses': {}}
        for pose in ('stow', 'side', 'back', 'high'):
            P = A.posed.get(pose)
            if P is None: continue
            byc = {}
            for sh, rgb, lab in P['parts']: byc.setdefault(tohex(rgb), []).append(cq_tris(sh))
            D['arms'][A.key]['poses'][pose] = [dict(pack(np.vstack(ts), 6000), c=c) for c, ts in byc.items()]
    A0 = np.vstack([v['t'].reshape(-1, 3) for v in M.values()]); D['centre'] = ((A0.min(0) + A0.max(0)) / 2).round(1).tolist()
    D['reach_png'] = base64.b64encode(_small(os.path.join(OUT, 'arms_reach.png'), 1300)).decode()
    html = open(os.path.join(HERE, 'tail_arms_template.html'), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D) + ';')
    p = os.path.join(OUT, 'tail_arms.html'); open(p, 'w', encoding='utf-8').write(html); print('page %.1f MB' % (os.path.getsize(p) / 1e6))

def _small(path, w):
    from PIL import Image; import io
    im = Image.open(path).convert('RGB'); im = im.resize((w, int(im.size[1] * w / im.size[0])), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True); return b.getvalue()

if __name__ == '__main__':
    t0 = time.time()
    M = body()
    from scipy.ndimage import binary_dilation
    sil = {pl: silhouette(M, pl, 22) for pl in ('xz', 'yz')}; R = {}
    for A in ARMS:                                                      # margin: each design's links' half-depth
        yy, xx = np.mgrid[-A.HALF:A.HALF + 1, -A.HALF:A.HALF + 1]; disk = xx ** 2 + yy ** 2 <= A.HALF ** 2
        mk = {pl: binary_dilation(sil[pl], disk) for pl in sil}
        R[A.key] = dict(fwd=reach(A, mk['xz'], 1), aft=reach(A, mk['xz'], -1), side=reach(A, mk['yz'], 1))
    print('reach %.0f s' % (time.time() - t0))
    for A in ARMS:
        pick_poses(A, R); A.posed = {}
        for pose in ('stow', 'side', 'back', 'high'):
            parts, tip, q, yaw = arm_pose(A, pose)
            if parts is None: print(A.key, pose, 'unreachable'); continue
            A.posed[pose] = dict(parts=parts, q=q, yaw=yaw, tip=tip)
            print(A.key, pose, 'yaw', yaw, 'q', np.round(q, 1), 'tip', np.round(to_world(tip, yaw), 1))
    reach_figure(M, ARMS, R)
    NUM = numbers(M, ARMS, R); json.dump(NUM, open(os.path.join(OUT, 'arms.json'), 'w'), indent=1, default=float)
    Cks = checks(M, ARMS); json.dump(Cks, open(os.path.join(OUT, 'arms_checks.json'), 'w'), indent=1)
    if '--no-render' not in sys.argv: renders(M, ARMS)
    if os.path.exists(os.path.join(HERE, 'tail_arms_template.html')): page(M, ARMS, Cks, NUM)
    print('done %.0f s' % (time.time() - t0))
