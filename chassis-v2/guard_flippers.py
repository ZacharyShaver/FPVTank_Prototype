"""Guard arm E with the Crawler's flippers (brainstorm, 2026-10-08). Zach: "can you do guard arm e with the crawlers
flippers". Guard arm E (guard_arm.py: the rugged body on the v2 legs, no cage) with a belted flipper outboard of
each track, turning on the v2 front idler's hollow boss, where legs_v2.py left room for one.

    python chassis-v2/guard_flippers.py     # ~3 min -> out/guard_flippers.html, guard_flippers.json

The drive. legs_v2.py planned a shaft through the boss from a motor in the hull. There's no room for one: on the idler
axis, between the tub's slanted nose wall and the claw, a gear can be about 7 mm in radius, far too small for flipper
loads. So each flipper carries its own: an N20 gearmotor* turns a worm that walks round a worm wheel fixed on the
boss's outer end (behind a slip clutch). A worm can't be driven backwards, so the flipper holds its angle unpowered.
The motor's leads come in through the hollow boss. The belt rolls free (the idler isn't driven).

Its jobs, and the check for each:
- Climb: raised 20 deg forward (the Crawler's pose), turned down to lift the nose onto a step. Checked: the lift the
  flippers give, pitching the robot about the back of the tracks, and the torque it takes.
- Back up the arm's righting: if the arm can't (servos dead, software down), a flipper pushes the robot over.
  Checked: from every place it can come to rest with the arm in its guard pose, a push the drive can make.
- Fit: through a full turn and against every arm pose, part with part, with a control for each zero.
"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('SCORPION_LEGS', 'v2')
import guard_arm as GA
import rugged as R
import legs_v2 as L2
from tail_arms import cq, cq_tris, YC, OUT, C
import tail_arms as TA
from scipy.spatial import ConvexHull
wp = lambda: cq.Workplane('XY')

# ---------------------------------------------------------------- the flipper (offsets from YC, outward; mm)
LF = 132.0                              # pivot to the tip pulley: the Crawler's 112, +22 since its pincer prongs went (2026-10-09)
R_PUL, X_PUL = 14.0, 34.0               # belt pulley near the pivot: the belt doesn't wrap the pivot, the drive is there
R_TIP = 10.0
BELT_T, LUG = 3.0, 3.0
M0, M1 = 130.0, 140.0                   # N20 band (10 thick): 4.5 off the track's outer face (125.5), clear of the fender
YW = (M0 + M1) / 2                      # worm and worm-wheel plane
WHEEL = (132.5, 137.5, 14.0)            # worm wheel*, module 1, 28 teeth, fixed on the boss: drawn at its pitch circle
WORM_R, WORM_V = 3.6, 18.0              # worm*, on the motor shaft: tangent to the wheel, above the arm's centre line
BOSS_END = 144.5                        # the v2 boss (ends at 137.5) runs 7 further, through the flipper's bearing
BRG = (140.5, 144.5)                    # 6704 (20 x 27 x 4) on the boss end, in the plate's bore: the flipper turns on it
P0, P1 = 140.5, 144.5                   # flipper plate
B0, B1 = 145.5, 159.5                   # belt band (14 wide)
DRIVE = dict(motor='Pololu 150:1 micro metal gearmotor HP 6 V*', stall=3.4, rpm=210, worm=28, eff=0.4, mass=10.5)  # stall kg.cm*
STALL = DRIVE['stall'] * DRIVE['worm'] * DRIVE['eff']         # at the flipper, kg.cm*
CLEAR = 240.0                                                    # upside down, the flippers turn here first: the stowed ones block the arm's push
TOOTH = 1.0                                                      # module, for the tooth load

GRP = 'flip'
FL = (0.30, 0.32, 0.35)
PLATE, BELT, PUL, MOT, BRASS, TPU = (0.62, 0.56, 0.44), (0.11, 0.12, 0.12), (0.91, 0.64, 0.23), (0.55, 0.58, 0.62), (0.80, 0.64, 0.30), R.TPU

def side(sg):
    """one side's flipper at theta 0 (pointing forward): {key: (tris, label, rgb, moving)}"""
    IX, IZ = L2.IDLER; k = 'L' if sg > 0 else 'R'
    Yr = lambda a, b: tuple(sorted((YC + sg * a, YC + sg * b)))
    def slab(pts, a, b):
        y0, y1 = Yr(a, b)
        return cq.Workplane('XZ').polyline([(IX + u, IZ + v) for u, v in pts]).close().extrude(-(y1 - y0)).translate((0, y0, 0))
    def ring(u, v, r, ri, a, b):
        y0, y1 = Yr(a, b); w = cq.Workplane('XZ').circle(r)
        if ri: w = w.circle(ri)
        return w.extrude(-(y1 - y0)).translate((IX + u, y0, IZ + v))
    def box(u0, u1, v0, v1, a, b, r=0.0):
        y0, y1 = Yr(a, b); s = wp().box(u1 - u0, y1 - y0, v1 - v0)
        if r: s = s.edges('|Y').fillet(r)
        return s.translate((IX + (u0 + u1) / 2, (y0 + y1) / 2, IZ + (v0 + v1) / 2))
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False); circ = lambda u, v, r: np.c_[u + r * np.cos(th), v + r * np.sin(th)]
    prof = np.vstack([circ(0, 0, 19), circ(X_PUL, 0, 12), circ(LF, 0, 9),
                      [[12, 10.2], [36, 10.2], [36, 25.8], [12, 25.8]]])
    prof = prof[ConvexHull(prof).vertices]
    plate = slab(prof, P0, P1).cut(ring(0, 0, 13.5, 0, P0 - 1, P1 + 1))               # bore for the 6704
    sad = box(12, 36, WORM_V - 7.8, WORM_V + 7.8, M0, P0).cut(box(11, 37, WORM_V - 6.3, WORM_V + 6.3, M0 - 1, M1 + 0.3))   # rails over and under the motor
    plate = plate.union(sad)
    for u in (X_PUL, LF):                                                                # pulley axles across the gap
        plate = plate.union(ring(u, 0, 3, 0, P1 - 0.5, B0 + 0.6))
    gb = box(7, 16.2, WORM_V - 6, WORM_V + 6, M0, M1)                                   # N20: gearbox, can (flats), back cap
    can = box(16.2, 31.2, WORM_V - 6, WORM_V + 6, M0, M1, 2.5)
    cap = box(31.2, 33.5, WORM_V - 4.5, WORM_V + 4.5, M0 + 1, M1 - 1)
    motor = gb.union(can).union(cap)
    y0, y1 = Yr(YW - 0.01, YW + 0.01); yc = (y0 + y1) / 2
    worm = cq.Workplane('YZ').circle(WORM_R).extrude(12).translate((IX - 6, yc, IZ + WORM_V)).union(
        cq.Workplane('YZ').circle(1.5).extrude(1.2).translate((IX + 5.9, yc, IZ + WORM_V)))
    pulleys = ring(X_PUL, 0, R_PUL - 0.2, 0, B0 + 0.6, B1 - 0.6).union(ring(LF, 0, R_TIP - 0.2, 0, B0 + 0.6, B1 - 0.6))
    ya, yb = Yr(B0, B1)
    belt = C.track_loop([(IX + X_PUL, IZ, R_PUL), (IX + LF, IZ, R_TIP)], ya, yb, t=BELT_T, lug=LUG, pitch=14.0, lug_len=6.0)
    bearing = ring(0, 0, 13.5, 10, BRG[0], BRG[1])
    endcap = ring(0, 0, 12, 0, P1, P1 + 2)
    wheel = ring(0, 0, WHEEL[2], 10, WHEEL[0], WHEEL[1])
    bext = ring(0, 0, L2.BOSS_R, 4.5, 137.5, BOSS_END)
    T_ = lambda s: np.asarray(cq_tris(s.val() if hasattr(s, 'val') else s), float).reshape(-1, 3, 3)
    return {
        'fwheel_' + k: (T_(wheel), 'Worm wheel* (fixed on the boss, behind a slip clutch)', BRASS, False),
        'fboss_' + k: (T_(bext), 'Idler boss, 6 longer: the flipper turns on its end', (0.55, 0.58, 0.62), False),
        'fplate_' + k: (T_(plate), 'Flipper plate, with the motor saddle', PLATE, True),
        'fbearing_' + k: (T_(bearing), '6704 bearing: the flipper turns on the boss', (0.75, 0.77, 0.8), True),
        'fcap_' + k: (T_(endcap), 'End cap (an AS5600* reads the flipper angle off a magnet on the boss end)', PLATE, True),
        'fmotor_' + k: (T_(motor), 'Flipper motor: N20 gearmotor*', MOT, True),
        'fworm_' + k: (T_(worm), 'Worm* on the motor shaft: walks round the fixed wheel', BRASS, True),
        'fpulley_' + k: (T_(pulleys), 'Belt pulleys (roll free on 625 bearings)', PUL, True),
        'fbelt_' + k: (np.asarray(belt, float).reshape(-1, 3, 3), 'Flipper belt (TPU, rolls free)', BELT, True),
    }

def turn(t, theta, sg=None):
    """rotate tris about the flipper axis by theta deg (positive raises the tip)"""
    IX, IZ = L2.IDLER; a = np.radians(theta); c, s = np.cos(a), np.sin(a)
    t = np.array(t, float); x, z = t[..., 0] - IX, t[..., 2] - IZ
    t[..., 0] = IX + x * c - z * s; t[..., 2] = IZ + x * s + z * c; return t

class Flippers:
    def __init__(s):
        s.P = {}; [s.P.update(side(sg)) for sg in (1, -1)]
    def fixed(s): return {k: v for k, v in s.P.items() if not v[3]}
    def moving(s, theta, keys=None):
        return {k: turn(v[0], theta) for k, v in s.P.items() if v[3] and (keys is None or k in keys)}
    def into(s, M, theta):
        """M with the flippers at theta"""
        M2 = dict(M)
        for k, (t, lab, rgb, mv) in s.P.items():
            M2[k] = dict(t=turn(t, theta) if mv else t, label=lab, grp=GRP, rgb=rgb, note='')
        return M2

DENS = {'fplate': 1.24e-3 * 0.6, 'fpulley': 1.24e-3 * 0.6, 'fbelt': 1.21e-3 * 0.9, 'fprong': 1.21e-3 * 0.6, 'fcap': 1.24e-3 * 0.6,
        'fboss': 1.24e-3 * 0.6, 'fwheel': 8.5e-3 * 0.55}                    # wheel: brass*, spoked
FIXED_G = {'fmotor': DRIVE['mass'], 'fworm': 3.0, 'fbearing': 5.0}
def mass_items(M):
    out = []
    for k, v in M.items():
        if v.get('grp') != GRP: continue
        c, vol = R.centroid(v['t']); p = k.rsplit('_', 1)[0]
        out.append((k, FIXED_G[p] if p in FIXED_G else vol * DENS[p], c))
    return out

# ---------------------------------------------------------------- track covers and the e-stop (Zach, 2026-10-09)
# The fender was a 2.4 mm sheet sticking 63 out from the hull, held on one edge, with a stop button drawn on it whose
# switch body had 2-10 mm under it. Now a box over each track; the button moves to the tail slope.
SP_TOP, SP_EDGE = 92.0, 76.0           # box top at the hull and at the outer edge: deep at the root, where the load is
SKIN, SWALL, RIB, RIB_PITCH = 1.6, 2.0, 1.2, 48.0      # its bottom skin stays at R.FENDER (68), 2.1 over the track at the idler
GLACIS = 18.0                           # the front end slopes back this far from bottom to top
ESTOP = dict(x=-75.0, dy=-50.0, head_r=14.0, head_h=14.0, bezel_r=11.0, bezel_h=3.0, body_r=10.0, body_l=30.0,
             collar=(18.0, 15.5, 13.0))  # 16 mm latching mini e-stop*: head 28 x 14, body 20 x 30 under the panel
SLOPE = np.degrees(np.arctan2(R.PZ - R.DECK, 36.0))   # the tail slope (carapace(): BED[0] -> -98 in body X)

def sponson(sg, Wtop):
    """a closed box over one track, tapered like a wing: 24 deep at the hull, 8 at the outer edge. Skins top and bottom,
    ribs across, the front sloped back. Its inner wall lies 0.2 off the carapace's side and screws to it"""
    x0, x1, z0 = R.FEND_X0, R.FEND_X1, R.FENDER
    yh, ye = (R.YL + 0.2, YC + Wtop) if sg > 0 else (R.YR - 0.2, YC - Wtop)              # hull side, outer edge
    sec = [(yh, z0), (ye, z0), (ye, SP_EDGE), (yh, SP_TOP)]
    side = [(x0, z0 - 1), (x1, z0 - 1), (x1, z0 + 6), (x1 - GLACIS, SP_TOP + 1), (x0, SP_TOP + 1)]
    lo, hi = min(yh, ye), max(yh, ye)
    across = lambda S, a, b: cq.Workplane('YZ').polyline(S).close().extrude(b - a).translate((a, 0, 0))
    along = lambda P, a, b: cq.Workplane('XZ').polyline(P).close().extrude(-(b - a)).translate((0, a, 0))
    outer = across(sec, x0, x1).intersect(along(side, lo - 1, hi + 1))
    inner = cq.Workplane('YZ').polyline(sec).close().offset2D(-SKIN).extrude(x1 - x0 - 2 * SWALL).translate((x0 + SWALL, 0, 0)) \
        .intersect(cq.Workplane('XZ').polyline(side).close().offset2D(-SKIN).extrude(-(hi - lo + 2)).translate((0, lo - 1, 0)))
    box = outer.cut(inner)
    for x in np.arange(x0 + RIB_PITCH, x1 - GLACIS, RIB_PITCH):
        box = box.union(wp().box(RIB, hi - lo, SP_TOP - z0).translate((x, (lo + hi) / 2, (z0 + SP_TOP) / 2)).intersect(outer))
    box = box.cut(wp().box(80, 80, 80).rotate((0, 0, 0), (0, 0, 1), 45).translate((x1, ye, (z0 + SP_TOP) / 2)))   # front outer corner, 45 deg in plan
    return box.val()

def cover_numbers():
    """per mm of length, bending across the cover (its cantilever), at the root: the old 2.4 sheet vs the box's skins"""
    t = 2.4; I0, S0 = t ** 3 / 12, t ** 2 / 6
    h = SP_TOP - R.FENDER; d = h / 2 - SKIN / 2; I1 = 2 * (SKIN * d ** 2 + SKIN ** 3 / 12); S1 = I1 / (h / 2)
    return dict(stiffer=I1 / I0, stronger=S1 / S0, depth=h, edge=SP_EDGE - R.FENDER)

def estop_axis(x=None, dy=None):
    """the button's panel point (on the slope's outer face) and its axis, square to the slope: up and forward"""
    x = ESTOP['x'] if x is None else x; dy = ESTOP['dy'] if dy is None else dy
    xb = x - R.BODY_DX; z = R.DECK + (R.BED[0] - xb) * (R.PZ - R.DECK) / 36.0
    a = np.radians(SLOPE); return np.array([x, YC + dy, z]), np.array([np.sin(a), 0.0, np.cos(a)])

def place_estop(M):
    """search the tail slope for the button: clear of everything round it with 2 mm to spare every way (the parts
    inside, the arm's base turned to every yaw, the arm in every pose, the hatch lifting straight up), then the most
    rearward spot. Moves along the slope keep the axis, so the meshes are built once and shifted"""
    Q = GA.poses(M); x0, d0 = ESTOP['x'], ESTOP['dy']; p0, _ = estop_axis(x0, d0)
    button, collar, _ = estop_parts(x0, d0)
    B0, C0 = [np.asarray(cq_tris(s), float).reshape(-1, 3, 3) for s in (button, collar)]
    x0b, y0b, x1b, y1b = R.BED; hatch = cq_tris(wp().box(x1b - x0b, y1b - y0b, 140, centered=False).translate((x0b + R.BODY_DX, y0b, R.DECK)).val())
    inside = [M[k]['t'] for k in M if not M[k].get('ghost') and k not in ('carapace', 'estop', 'estop_collar') and M[k]['grp'] != 'armbase']
    moving = [GA.base_tris(y) for y in range(-90, 181, 15)] + [GA.arm_tris(q) for q in Q.values()] + [np.asarray(hatch, float).reshape(-1, 3, 3)]
    k = (R.PZ - R.DECK) / 36.0
    def hits(x, dy):
        v = np.array([x - x0, dy - d0, -(x - x0) * k]); B, Cl = B0 + v, C0 + v
        return any(C.overlap_mm3(B, t) > 0 or C.overlap_mm3(Cl, t) > 0 for t in inside + moving) or C.overlap_mm3(Cl, M['carapace']['t']) > 0
    ok = []
    for x in np.arange(-82.0, -55.0, 2.0):
        for dy in list(np.arange(-48.0, -27.0, 2.0)) + list(np.arange(28.0, 49.0, 2.0)):
            if not hits(x, dy) and not any(hits(x + a, dy + b) for a, b in ((2, 0), (-2, 0), (0, 2), (0, -2))): ok.append((x, dy))
    print('e-stop: %d clear spots on the slope' % len(ok))
    return min(ok, key=lambda s: (s[0], abs(s[1]))) if ok else None

def estop_parts(x=None, dy=None):
    p, n = estop_axis(x, dy); E = ESTOP
    def cyl(r, a, b, r_in=0.0):
        w = wp().circle(r)
        if r_in: w = w.circle(r_in)
        return w.extrude(b - a).translate((0, 0, a)).rotate((0, 0, 0), (0, 1, 0), SLOPE).translate(tuple(p))
    button = cyl(E['body_r'], -E['body_l'], 0).union(cyl(E['bezel_r'], 0.2, E['bezel_h'])).union(cyl(E['head_r'], E['bezel_h'], E['bezel_h'] + E['head_h']))
    collar = cyl(E['collar'][0], 0.2, E['collar'][2], E['collar'][1])                      # 0.2 off the skin: no shared face in the checks
    hole = cyl(E['body_r'] + 0.5, -E['body_l'] - 5, 3)
    return button.val(), collar.val(), hole

def robot(estop=False):
    """Guard arm E's robot with the box covers. The stop button waits for Zach's pick (2026-10-09): the tail slope has
    no spot clear of the hatch, the arm's turntable, the air intake and the power parts under it by more than ~2 mm
    (place_estop), so by default it's left off"""
    M, _ = GA.robot()
    Wtop = R.corners(M) + 3.0
    for k in ('fender0', 'fender1'): M.pop(k, None)
    for sg, k in ((1, 'cover_L'), (-1, 'cover_R')):
        M[k] = dict(t=np.asarray(cq_tris(sponson(sg, Wtop)), float).reshape(-1, 3, 3), label='Track cover: a box, %g deep' % (SP_TOP - R.FENDER),
                    grp='hull', rgb=R.OLIVE, note='Skins %.1f, walls %.1f, ribs every %g. Screws to the carapace\'s side.' % (SKIN, SWALL, RIB_PITCH))
    M.pop('estop', None)                                                                # the old one stood on the fender
    if not estop: return M, R.mass_items(M)
    spot = place_estop(M)
    if spot is None: raise SystemExit('no clear spot for the e-stop on the tail slope')
    ESTOP['x'], ESTOP['dy'] = float(spot[0]), float(spot[1]); print('e-stop at X %.0f, %+.0f off the centre line' % spot)
    button, collar, hole = estop_parts()
    car = cq.Workplane('XY').add(R.carapace()).cut(hole.translate((-R.BODY_DX, 0, 0)))          # the switch body passes the skin
    M['carapace']['t'] = np.asarray(cq_tris(car.val()), float).reshape(-1, 3, 3) + [R.BODY_DX, 0, 0]
    M['estop'] = dict(t=np.asarray(cq_tris(button), float).reshape(-1, 3, 3), label='E-stop: 16 mm latching mini button*',
                      grp='elec', rgb=(0.78, 0.13, 0.13), note='On the tail slope, %s side: opens the PCA9685\'s OE line (your hardware lockout).' % ('right' if ESTOP['dy'] < 0 else 'left'))
    M['estop_collar'] = dict(t=np.asarray(cq_tris(collar), float).reshape(-1, 3, 3), label='E-stop guard collar (TPU)', grp='tpu', rgb=R.TPU,
                             note='The head stands %g proud: you can slap it, a fall can\'t.' % (ESTOP['bezel_h'] + ESTOP['head_h'] - ESTOP['collar'][2]))
    return M, R.mass_items(M)

# ---------------------------------------------------------------- poses
def touch_angle(F, g0):
    """the angle, turning down from level, where the flipper first touches the ground"""
    for th in np.arange(0, -90, -0.25):
        if min(t[..., 2].min() for t in F.moving(th).values()) <= g0: return float(th)

def lift(F, M, it, th0):
    """turning the flippers down from first touch: the robot pitches nose-up about the back of the tracks' flat contact.
    Per step: the pitch, the ground force at the flipper tips, the torque each flipper's drive needs, the claw height"""
    g0 = R.ground(M); tr = R.feet(M); x0 = tr[tr[:, 2] < g0 + 0.6][:, 0].min(); Q = np.array([x0, g0])
    c, m = R.cog(it); Wn = m / 1000 * 9.81; IX, IZ = L2.IDLER
    claw = np.vstack([M[k]['t'].reshape(-1, 3) for k in ('claw0', 'claw1', 'claw0_tip', 'claw1_tip')])[:, [0, 2]]
    rot = lambda P, a: np.c_[Q[0] + (P[:, 0] - Q[0]) * np.cos(a) - (P[:, 1] - Q[1]) * np.sin(a), Q[1] + (P[:, 0] - Q[0]) * np.sin(a) + (P[:, 1] - Q[1]) * np.cos(a)]
    out, prev = [], -1.0
    for th in np.arange(th0, th0 - 120, -2.0):
        P = np.vstack([t.reshape(-1, 3) for k, t in F.moving(th).items() if k.endswith('_L')])[:, [0, 2]]
        lo, hi = 0.0, np.radians(70)
        if rot(P, lo)[:, 1].min() > g0: continue
        for _ in range(40):
            mid = (lo + hi) / 2
            if rot(P, mid)[:, 1].min() < g0: lo = mid
            else: hi = mid
        a = hi; Pr = rot(P, a); cp = Pr[np.argmin(Pr[:, 1])]; cg = rot(np.array([[c[0], c[2]]]), a)[0]; pv = rot(np.array([[IX, IZ]]), a)[0]
        if a < prev - 1e-4 or cg[0] <= Q[0]: break                                    # past straight down, or it would tip back
        Fv = Wn * (cg[0] - Q[0]) / (cp[0] - Q[0])                                      # both flippers' push, N
        tau = Fv / 2 * abs(cp[0] - pv[0]) / 98.1                                      # each drive, kg.cm
        idl = rot(np.array([[IX, IZ + L2.IDLER_R + L2.BAND + L2.GROUSER]]), a)[0]
        out.append(dict(theta=float(th), pitch=float(np.degrees(a)), F=float(Fv), tau=float(tau),
                        claw=float(rot(claw, a)[:, 1].min() - g0), idler=float(idl[1] - g0), tip=cp.tolist(), cog_ahead=float(cg[0] - Q[0])))
        prev = a
    return out, Q

def lift_pose(Q, pitch):
    a = np.radians(pitch); Rm = np.array([[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]])
    Q3 = np.array([Q[0], 0, Q[1]]); return Rm, Q3 - Rm @ Q3

# ---------------------------------------------------------------- righting with a flipper (the arm's backup)
def edge_towards_upright(M, rest, skip=()):
    P, H = GA.hull_of(M, [k for k in M if not M[k].get('ghost') and M[k]['grp'] not in skip])
    eq = H.equations; n = np.array(rest['normal'], float); n /= np.linalg.norm(n)
    face = [i for i, e in enumerate(eq) if np.dot(e[:3], n) > 0.9995]
    d = -max(eq[i, 3] for i in face)
    from collections import defaultdict
    ef = defaultdict(list)
    for i, s in enumerate(H.simplices):
        for a, b in ((s[0], s[1]), (s[1], s[2]), (s[2], s[0])): ef[(min(a, b), max(a, b))].append(i)
    fs = set(face); best = None
    for (a, b), fl in ef.items():
        inn = [f for f in fl if f in fs]; out = [f for f in fl if f not in fs]
        if len(inn) == 1 and len(out) == 1:
            sc = -eq[out[0], 2]
            if best is None or sc > best[0]: best = (sc, P[a], P[b])
    return n, d, best

def flipper_righting(F, M, it, rest):
    """from a rest (arm in guard, flippers stowed), turn either flipper until it meets the ground and push the robot
    over the edge towards upright at 1.2x the balancing force. Returns the lightest push: drive load vs stall"""
    n, d, be = edge_towards_upright(M, rest)
    if be is None: return dict(ok=False)
    _, A, B = be; e = (B - A) / np.linalg.norm(B - A); c, m = R.cog(it); Wn = m / 1000 * 9.81
    tau_g = np.dot(np.cross(c - A, Wn * n), e); IX, IZ = L2.IDLER; best = None
    for sk in ('_L', '_R'):
        sgn = 1 if sk == '_L' else -1; piv = np.array([IX, YC + sgn * 140.0, IZ])
        for th in np.arange(0, 360, 1.0):
            P = np.vstack([t.reshape(-1, 3) for k, t in F.moving(th).items() if k.endswith(sk)])
            s = P @ n - d
            if not (-3.0 <= s.max() <= 3.0): continue                               # touching the ground plane
            cp = P[np.argmax(s)]; arm_ = np.dot(np.cross(cp - A, -n), e)
            if arm_ * tau_g >= 0 or abs(arm_) < 1e-6: continue
            Fp = abs(tau_g / arm_) * 1.2
            tq = abs(np.dot(np.cross(cp - piv, -Fp * n), [0, 1, 0])) / 98.1             # about the flipper axis, kg.cm
            if best is None or tq < best['tau']:
                best = dict(side='left' if sk == '_L' else 'right', theta=float(th), F=float(Fp), tau=float(tq), contact=cp.tolist())
    if best is None: return dict(ok=False, why='no flipper angle reaches the ground on the right side of the edge')
    best['load'] = best['tau'] / STALL; best['ok'] = bool(best['load'] <= 0.8); return best

# ---------------------------------------------------------------- fit checks: part with part, a control for each zero
def checks(F, M, Q, poses):
    ov = lambda a, b: float(sum(C.overlap_mm3(x, y) for x in a for y in b))
    static = [M[k]['t'] for k in M if not M[k].get('ghost') and M[k]['grp'] not in ('armbase', GRP)]
    fixed = [v[0] for v in F.fixed().values()]
    mv = lambda th, skip=(): [t for k, t in F.moving(th).items() if not k.startswith(skip)]
    guard = [GA.arm_tris(Q['guard']), GA.base_tris(Q['guard'][0])]
    def inboard(L, dd):
        out = []
        for t in L:
            t = t.copy(); t[:, :, 1] -= dd * np.sign(t[:, :, 1] - YC); out.append(t)
        return out
    rows = []
    for nm, th in poses.items():                                                    # the bearing on its boss is a shared surface: its own row
        rows.append(('Flippers %s vs the robot and the guarding arm' % nm, mv(th), static + guard, ''))
    sweep = list(range(0, 360, 10))
    rows += [('Flippers through a full turn (every 10°) vs the robot', [t for th in sweep for t in mv(th)], static, 'outboard of the tracks: it turns all the way round'),
             ('The same, 6 mm inboard (control)', [t for th in sweep for t in inboard(mv(th), 6.0)], static, 'must read > 0: the motor band is 4.5 off the track'),
             ('Moving flipper vs its fixed worm wheel and boss, full turn', [t for th in sweep for t in mv(th, ('fbearing',))], fixed, 'worm and wheel drawn at their pitch circles'),
             ('Worm 2.5 mm toward the pivot (control)', [turn(t, 0) - [0, 0, 2.5] for k, t in F.moving(0).items() if k.startswith('fworm')], [v[0] for k, v in F.fixed().items() if k.startswith('fwheel')], 'must read > 0'),
             ('Motor in its saddle', [t for k, t in F.moving(0).items() if k.startswith('fmotor')], [t for k, t in F.moving(0).items() if k.startswith('fplate')], ''),
             ('Motor 1.5 mm up (control)', [t + [0, 0, 1.5] for k, t in F.moving(0).items() if k.startswith('fmotor')], [t for k, t in F.moving(0).items() if k.startswith('fplate')], 'must read > 0: the top rail'),
             ('Worm wheels and boss ends vs track, idler, fender', fixed, [M[k]['t'] for k in M if k.startswith(('track_', 'idler_', 'cover_', 'frame_'))], ''),
             ('Worm wheels 10 mm inboard (control)', inboard([v[0] for k, v in F.fixed().items() if k.startswith('fwheel')], 10.0), [M[k]['t'] for k in M if k.startswith(('track_', 'idler_'))], 'must read > 0: into the idler')]
    arms = [t for k in Q for t in (GA.arm_tris(Q[k]), GA.base_tris(Q[k][0]))]
    for nm in ('stowed', 'level'):
        rows.append(('The arm, every pose, vs the flippers %s' % nm, arms, mv(poses[nm]), ''))
    for yaw in (60.0, 50.0, 40.0, 30.0, 20.0):                                        # the brace-beside pose swung forward over the stowed flipper
        qc = (yaw,) + tuple(Q['brace_side'][1:])
        if ov([GA.arm_tris(qc)], mv(poses['stowed'])) > 0:
            rows.append(('The arm braced beside, swung forward to %.0f° (control)' % yaw, [GA.arm_tris(qc)], mv(poses['stowed']), 'must read > 0: it crosses the stowed flipper')); break
    covers = [M[k]['t'] for k in ('cover_L', 'cover_R')]
    legs = [M[k]['t'] for k in M if M[k]['grp'] == 'legs' and not M[k].get('ghost')]
    hull = [M[k]['t'] for k in ('carapace', 'tub', 'tdeck', 'tdeck_lids', 'claw0', 'claw1', 'rest_peg')]
    A = GA.arm_tris(Q['brace_side']); cl = M['cover_L']['t'].reshape(-1, 3); lo, hi = cl.min(0), cl.max(0)
    P = A.reshape(-1, 3); P = P[(P[:, 0] > lo[0]) & (P[:, 0] < hi[0]) & (P[:, 1] > lo[1]) & (P[:, 1] < hi[1])]
    gap = float(P[:, 2].min() - hi[2]) if len(P) else 99.0                           # the braced arm over the left cover
    rows += [('Track covers vs the legs and tracks', covers, legs, 'the bottom skin 2.1 over the track where it climbs to the idler'),
             ('Track covers 3 mm lower (control)', [t - [0, 0, 3.0] for t in covers], legs, 'must read > 0'),
             ('Track covers vs the flippers through a full turn', covers, [t for th in sweep for t in mv(th)], ''),
             ('Track covers vs the hull, claws and rest peg', covers, hull, 'the inner wall 0.2 off the carapace\'s side'),
             ('Track covers 2 mm inboard (control)', inboard(covers, 2.0), [M['carapace']['t']], 'must read > 0'),
             ('The arm and its base, every pose, vs the track covers', arms, covers, 'braced beside, the arm passes %.0f over the left one' % gap),
             ('The arm braced beside, %.0f mm lower (control)' % (gap + 4), [A - [0, 0, gap + 4.0]], covers, 'must read > 0')]
    if 'estop' in M:                                                                    # only once Zach picks where the button goes
        btn = [M['estop']['t'], M['estop_collar']['t']]
        near = [M[k]['t'] for k in M if not M[k].get('ghost') and k not in ('estop', 'estop_collar') and M[k]['grp'] not in ('armbase', GRP)]
        p, n = estop_axis(); toward = np.array([GA.AXW - p[0], YC - p[1], 0.0]); toward /= np.linalg.norm(toward)
        swept = [GA.base_tris(y) for y in range(-90, 181, 15)]
        rows += [('E-stop and its collar vs everything else', btn, near, 'its switch body inside the tail'),
                 ('E-stop 15 mm to the side (control)', [M['estop']['t'] + [0, 15.0, 0]], [M['carapace']['t']], 'must read > 0: the body meets the skin where there\'s no hole'),
                 ('The arm in every pose, its base at every yaw, vs the e-stop', arms + swept, btn, 'clear of the turntable and its fairing'),
                 ('E-stop 25 mm nearer the turntable (control)', [t + toward * 25.0 for t in btn], swept, 'must read > 0')]
    out = []
    for what, a, b, why in rows:
        v = ov(a, b); out.append(dict(what=what, mm3=v, why=why)); print('%-62s %9.0f mm3' % (what, v))
    return out

# ---------------------------------------------------------------- page
def pack(t, faces):
    Tk = C.decimate(t, faces); V, Fq = C.quant(Tk); return {'v': C.b64(V), 'f': C.b64(Fq), 'i32': Fq.dtype == np.uint32}
tohex = lambda rgb: int(rgb[0] * 255) << 16 | int(rgb[1] * 255) << 8 | int(rgb[2] * 255)

def page(F, M, Q, poses, D):
    D['m'] = {}
    for k, v in F.into(M, 0).items():
        if v.get('ghost') or v['grp'] == 'armbase' or (v['grp'] == GRP and F.P[k][3]): continue
        D['m'][k] = dict(pack(v['t'], C.faces_for(k)), c=tohex(v['rgb']), grp=v['grp'], label=v['label'], note=v.get('note', ''))
    D['sit'] = {}
    for k in GA.POSES:
        if k not in Q: continue
        byc = {}
        for sh, rgb, lab in GA.parts(Q[k], base=True): byc.setdefault(tohex(rgb), []).append(np.asarray(cq_tris(sh), float).reshape(-1, 3, 3))
        D['sit'][k] = dict(name=GA.POSE_NAME[k], arm=[dict(pack(np.vstack(ts), 5000), c=c) for c, ts in byc.items()])
    D['flip'] = {}
    for nm, th in list(poses.items()) + [('lift', D['lift_pose']['theta'])]:
        D['flip'][nm] = [dict(pack(t, 2500 if 'belt' in k else 1500), c=tohex(F.P[k][2]), label=F.P[k][1]) for k, t in F.moving(th).items()]
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v.get('ghost')]); D['centre'] = ((A.min(0) + A.max(0)) / 2).round(1).tolist()
    D['yc'] = YC; D['ground'] = R.ground(M)
    html = open(os.path.join(HERE, 'guard_flippers_template.html'), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D, default=float) + ';')
    p = os.path.join(OUT, 'guard_flippers.html'); open(p, 'w', encoding='utf-8').write(html); print('page %.1f MB' % (os.path.getsize(p) / 1e6))

SHOP = [
    ('Pololu 150:1 micro metal gearmotor HP 6 V (or any N20 at ~200 rpm)', 2, 'One per flipper, riding on it. Buy one and caliper it first*.'),
    ('Worm + worm wheel, module 1, 28 teeth, single start (brass or steel worm, bronze or nylon wheel)', 2, 'Self-locking: the flipper holds its angle with the power off.'),
    ('6704 bearings (20 x 27 x 4)', 2, 'The flippers on the boss ends, as legs_v2.py planned. You had 10: check what\'s left after the idlers.'),
    ('625ZZ bearings (5 x 16 x 5)', 4, 'Belt pulleys.'),
    ('AS5600L magnetic angle sensor (address settable) + diametric magnet', 2, 'Flipper angle (the N20 has no feedback). The plain AS5600 shares the yaw sensor\'s fixed address.'),
    ('DRV8833 dual H-bridge board', 1, 'Both flipper motors, from 4 PCA9685 channels.'),
    ('M10 Belleville washers + PTFE washer', 4, 'Slip clutch behind each worm wheel: a hit on a flipper slips instead of stripping it.'),
    ('TPU 95A filament', 1, 'Belts, ~%d g a side*.'),
]

if __name__ == '__main__':
    t0 = time.time()
    M, it = robot(); Q = GA.poses(M); F = Flippers()
    g0 = R.ground(M); th_down = touch_angle(F, g0)
    poses = {'stowed': 180.0, 'climbing': 20.0, 'level': 0.0, 'down': th_down}
    print('touch angle', th_down)
    G = json.load(open(os.path.join(OUT, 'guard_arm.json')))
    MG = GA.with_arm(M, Q['guard']); itG = it + GA.mass_items(Q['guard'], payload=False)
    MGF = F.into(MG, 180.0); itGF = itG + mass_items(MGF)                              # driving: arm in guard, flippers stowed
    MF = F.into(M, 180.0)                                                               # the arm left out (it moves)
    fl_g = sum(g for k, g, _ in mass_items(MGF)); print('flippers %.0f g' % fl_g)
    tpu_g = sum(g for k, g, _ in mass_items(MGF) if k == 'fbelt_L')
    Wtop = R.corners(M) + 3.0; old_g = sum(R.centroid(cq_tris(f))[1] for f in R.fenders(Wtop)) * R.DENS['hull']
    cov = dict(cover_numbers(), old_g=old_g, new_g=sum(g for k, g, _ in it if k.startswith('cover_')), estop=ESTOP, slope=SLOPE)
    print('covers', {k: (round(v, 1) if isinstance(v, float) else v) for k, v in cov.items() if k != 'estop'})
    _cat = R.category; R.category = lambda k, v: 'flippers' if v['grp'] == GRP else ('the guard arm' if v['grp'] in ('arm', 'armbase') else _cat(k, v))
    R.FRAGILE = R.FRAGILE + tuple(k for k in MG if MG[k]['grp'] == 'arm' and MG[k]['label'].startswith('Arm camera'))
    D = dict(poses=poses, shop=SHOP, drive=DRIVE, stall=STALL, LF=LF, flip_g=fl_g, tpu_g=tpu_g, cover=cov, guard={k: G[k] for k in ('mass', 'size', 'climb_guard', 'rests_guard', 'contact', 'righting')})
    D['mass'] = R.cog(itGF)[1]
    sz = lambda MM: (lambda A: dict(L=float(np.ptp(A[:, 0])), W=float(np.ptp(A[:, 1])), H=float(A[:, 2].max() - g0)))(np.vstack([v['t'].reshape(-1, 3) for v in MM.values() if not v.get('ghost')]))
    D['size'] = sz(MGF); D['size_fwd'] = sz(F.into(MG, 20.0)); print('size', D['size'], 'climbing', D['size_fwd'], 'mass', round(D['mass']))
    D['climb'] = R.climb(MGF, itGF); print('climb', {k: round(v, 1) for k, v in D['climb'].items() if isinstance(v, float)})
    D['contact'] = R.first_contact(MGF); print('first contact', D['contact'])
    D['rests'] = R.rest_states(MGF, itGF); print('rests (arm guard, flippers stowed)', [(r['name'], round(r['tilt'], 1)) for r in D['rests']])
    D['lift'], Qp = lift(F, MGF, itGF, th_down)
    top = max(D['lift'], key=lambda r: r['pitch']); D['lift_pose'] = dict(theta=top['theta'], pitch=top['pitch'])
    Rm, tv = lift_pose(Qp, top['pitch']); D['lift_pose'].update(R=Rm.tolist(), t=tv.tolist())
    D['lift_max_tau'] = max(r['tau'] for r in D['lift'])
    print('lift: max pitch %.1f deg at theta %.0f, claws %.0f over the ground (level: %.0f); worst drive torque %.1f kg.cm (stall* %.1f)' % (
        top['pitch'], top['theta'], top['claw'], D['lift'][0]['claw'], D['lift_max_tau'], STALL))
    D['f_righting'] = []
    for r in [r for r in D['rests'] if not r['name'].startswith('upright')]:
        fr = flipper_righting(F, MGF, itGF, r); fr.update(rest=r['name'], normal=r['normal']); D['f_righting'].append(fr)
        print('flipper righting from %-34s' % r['name'], {k: (round(v, 2) if isinstance(v, float) else v) for k, v in fr.items() if k in ('ok', 'side', 'theta', 'F', 'tau', 'load', 'why')})
    D['rests_bare'] = R.rest_states(MF, itGF); D['a_righting'] = []                  # the arm working: it moves, so the rests leave it out
    MF2 = F.into(M, CLEAR); itF2 = itG + mass_items(MF2); rests2 = R.rest_states(MF2, itF2)
    for r in [r for r in D['rests_bare'] if not r['name'].startswith('upright')]:
        rr = GA.righting(MF, itGF, r); fr = flipper_righting(F, MF, itGF, r); row = dict(rest=r['name'], arm=rr, flipper=fr)
        if not (rr.get('ok') or fr.get('ok')):                                       # turn the flippers out of the way first: it settles on the nearest rest
            r2 = max(rests2, key=lambda q: np.dot(q['normal'], r['normal']))
            row.update(then=r2['name'], arm2=GA.righting(MF2, itF2, r2), flipper2=flipper_righting(F, MF2, itF2, r2))
        D['a_righting'].append(row)
        print('righting from %-34s arm %s %.2f | flipper %s %.2f' % (r['name'], rr.get('ok'), rr.get('load', -1), fr.get('ok'), fr.get('load', -1)),
              ('| flippers to %d first -> %s: arm %.2f, flipper %.2f' % (CLEAR, row['then'], row['arm2'].get('load', -1), row['flipper2'].get('load', -1))) if 'then' in row else '')
    D['tooth_N'] = STALL * 98.1 / WHEEL[2]                                              # N on the wheel's teeth at stall
    D['checks'] = checks(F, M, Q, poses)
    json.dump({k: v for k, v in D.items()}, open(os.path.join(OUT, 'guard_flippers.json'), 'w'), indent=1, default=float)
    if os.path.exists(os.path.join(HERE, 'guard_flippers_template.html')): page(F, M, Q, poses, D)
    print('done %.0f s' % (time.time() - t0))
