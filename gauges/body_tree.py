"""Bodies on printed trees (2026-10-28, a prototype). Zach: "lets see if we can up the complexity of how the wheels sit.
can we generate wheels thats attach points can angle up, down, are there more organic like shapes that you can randomly
sample? like trees on 3d printed supports or something".

body.py's anchor-first body, with the wheels held out on printed legs instead of pods. On each side a trunk grows from
the body's side, curves out to a fork, and branches to each wheel's motor tube (or, with the tree switch off, each wheel
gets its own leg from its own root). The legs are smooth curves of capsules, which the sims feel. Their angle is not a
knob: it comes from the anchors, the roots' height on the side against the wheels' axles, and the body's ride height
(its own knob, not tied to the wheel's radius): a high body hangs on legs angled down to its wheels, a low one sits
between wheels whose legs climb to them. The wheels may sit past the nose or the rear, and out to the sides (tucked
under a high body was tried: every one failed its clearances).

Each wheel's 37 mm gearmotor slides into a printed tube, TUBE_WALL* thick, that runs from 3 mm past the motor's inner
end to 3 mm short of the tyre; its leg comes down onto the tube's top and merges into it, its end held clear of the
motor (Zach: "it clips through the motors", "it should look like something that can easily fit the motor"). Where a
leg leaves the body it flares, FLARE* thicker at the side and back to its own size over its first FLARE_LEN* (Zach:
"when attaching to the body the width of the trunk should widen to give a stronger shape").

How thick a leg is: here, a first guess by rule (each wheel's contact loaded by LOAD* times half the robot's weight, and
MU* of that sideways and along, kept under SIGMA*; bent no more than DEFL* by half its weight; never under R_MIN*).
snap.py then drops the design and sizes every segment from the loads the sim measures (Zach: "can we test where it
would snap? maybe we should just let the simulation do the thinking here instead of guessing"); build(q, radii) takes
those sizes. Every design must pass: no tyre in the body; no leg through the body (past its root), a tyre, a motor's
tube or the ground; each tube clear of the body. Printed legs weigh as PLA at half fill*.

    python gauges/body_tree.py sheet [seed]   -> gauges/out/body/trees.png (Sobol designs: legs sized from the falls,
                                                blended into one shape, rendered by MuJoCo)
"""
import os, sys, math
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import robots as RB, search as S, body as B

FILL = 0.5                                       # printed legs: the fraction of solid PLA*
SIGMA, LOAD, MU, R_MIN = 6.0, 3.0, 0.9, 14.0     # the first guess: MPa, times, -, mm
E_PLA, DEFL = 2500.0, 1.0                        # MPa, mm
FLARE, FLARE_LEN = 1.8, 30.0                     # times, mm
TUBE_WALL = 6.0                                  # mm: the motor tube's wall round the 37 mm motor*
TUBE_R = B.MOTOR['half'][0] + TUBE_WALL
T_SEG = np.array([0.0, 0.03, 0.08, 0.15, 0.25, 0.38, 0.53, 0.7, 0.86, 1.0])   # a leg's points, close at its root (the flare)
KNOBS = [   # (key, low, high, what it is)
    ('w', 0.0, 40.0, "the body's width past the parts', each side, mm"),
    ('n_x', 0.0, 80.0, "the nose point's reach ahead of the parts, mm"),
    ('n_z', 0.25, 1.0, "the nose point's height, of the body's"),
    ('n_lo', 0.0, 0.5, "the nose's underside: how high its bottom edge rises at the nose, of the body's"),
    ('t_x', 0.0, 80.0, "the rear point's reach behind the parts, mm"),
    ('t_z', 0.25, 1.0, "the rear point's height, of the body's (the tail mounts there)"),
    ('t_lo', 0.0, 0.5, "the rear's underside, as the nose's"),
    ('r_c', 5.0, 60.0, "the body's corners seen from above, radius mm"),
    ('clr', 10.0, 160.0, "the body's belly above the ground, mm (the legs bridge it to the wheels)"),
    ('R', 35.0, 75.0, "the wheels' radius, mm"),
    ('TW', 25.0, 80.0, "the tyres' width, mm"),
    ('six', 0.0, 1.0, 'six wheels (above half)'),
    ('x_f', 0.0, 1.0, "the front wheels: from just ahead of the body's middle (0) to 80 mm past the nose (1)"),
    ('x_r', 0.0, 1.0, "the rear wheels: from just behind the middle (0) to 80 mm behind the rear (1)"),
    ('d_f', 0.0, 1.0, "the front wheels' width: the narrowest their tube allows (0) to 40 mm wider beside the body, 60 past its end (1)"),
    ('d_r', 0.0, 1.0, "the rear wheels', as the front's"),
    ('tree', 0.0, 1.0, 'one trunk per side forking to its wheels (above half), else each wheel its own legs'),
    ('members', 1.0, 3.999, "each wheel's legs (without a tree): 1 a single beam, 2 a braced pair, 3 a tripod"),
    ('spread_x', 0.0, 1.0, "a wheel's legs' roots spread along the side: together (0) to 150 mm apart (1)"),
    ('spread_z', 0.0, 1.0, "and up and down: together (0) to 70 % of the body's height apart (1)"),
    ('root_x', 0.0, 1.0, "the trunk's root along the side, back (0) to front (1)"),
    ('root_z', 0.15, 0.85, "the roots' height on the side, of the body's"),
    ('fork_y', 15.0, 90.0, 'the fork out from the side, mm'),
    ('fork_z', 0.0, 1.0, "the fork's height: at the axles' (0) to the root's (1)"),
    ('bend', -1.0, 1.0, 'how the branches arch: down (-1) to up (1)'),
    ('dxp', -20.0, 60.0, 'the packs moved forward, mm'),
    ('gear', 0.4, 2.5, 'the gearing, times the stock 30:1'),
    ('limb', 0.0, 1.0, 'a tail (above half)'),
    ('L', 80.0, 350.0, "the tail's length, mm"),
    ('tq', 0.3, 4.0, "the tail servo's stall torque, N m"),
    ('u_stow', 0.0, 1.0, 'the stowed angle, within the clear ones'),
    ('u_push', 0.0, 1.0, "the step push's angle, within the clear ones")]
KEYS = [k for k, *_ in KNOBS]


def tube_ends(x, y, R, TW, r=0.0):
    """a motor's tube: from 3 mm past the motor's inner end (or further in, for a leg r wide to land on) to 3 mm short
    of the tyre, |y|"""
    y_out = abs(y) - TW / 2 - 3.0; y_in = min(abs(y) + TW / 2 - B.MOTOR['rim_in'] - 2 * B.MOTOR['half'][1] - 3.0, y_out - 25.0)
    return min(y_in, y_out - 2 * r - 2.0), y_out


def anchors(q):
    """the body's anchors (body.anchors' ends and parts), the ride height as given, and the hubs"""
    C, _, _, clr0 = B.parts(); P = np.vstack(list(C.values()))
    x0, x1 = P[:, 0].min() - B.WALL, P[:, 0].max() + B.WALL; hy = np.abs(P[:, 1]).max() + B.WALL + q['w']
    H = P[:, 2].max() - clr0 + 2 * B.WALL; clr = q['clr']; R, TW = q['R'], q['TW']
    xn, xt = x1 + q['n_x'], x0 - q['t_x']; mid = 0.5 * (xn + xt); six = q['six'] > 0.5
    gap = 2 * R + 15.0 if six else R + 7.5                              # each hub's least distance from the middle
    xf = mid + gap + q['x_f'] * max(0.0, xn + 80.0 - mid - gap); xr = mid - gap - q['x_r'] * max(0.0, mid - gap - xt + 80.0)
    # the width: a wheel beside the body sits out far enough for its motor's tube (inb of it inboard of the wheel's
    # middle), plus up to 40 mm; one clear of the body's end may come inboard, its tube 8 mm from the other side's
    inb = abs(tube_ends(0.0, 0.0, R, TW)[0])
    clear_end = lambda x: x - max(R, TUBE_R) - 5.0 >= xn or x + max(R, TUBE_R) + 5.0 <= xt
    def width(x, u):
        return (8.0 + inb + 60.0 * u) if clear_end(x) else (hy + 3.0 + inb + 40.0 * u)
    yf, yr = width(xf, q['d_f']), width(xr, q['d_r'])
    hubs = [(xf, yf), (xf, -yf), (xr, yr), (xr, -yr)]
    if six:
        ym = max(0.5 * (yf + yr), hy + 3.0 + inb); hubs += [(mid, ym), (mid, -ym)]
    n_lo, t_lo = q['n_lo'], q['t_lo']
    return dict(R=R, TW=TW, clr=clr, H=H, hy=hy, x0=x0, x1=x1, nose=(xn, clr + max(q['n_z'], n_lo + 0.1) * H),
                rear=(xt, clr + max(q['t_z'], t_lo + 0.1) * H), nose_lo=clr + n_lo * H, rear_lo=clr + t_lo * H,
                axles=hubs, dz=clr - clr0)


THETA_MIN = math.radians(-20.0)                 # a leg grips its tube from no lower than this (the ground below)


def landing(x, y, R, TW, r, theta=math.pi / 2):
    """where a leg of end radius r meets its wheel's tube, on the side at angle theta round the axle (pi / 2 the top,
    toward +X 0): its end's centre r plus 2 mm out from the motor (so it merges into the tube's wall without reaching
    the motor), as far inboard on the tube as it fits"""
    y_in, y_out = tube_ends(x, y, R, TW, r); d = B.MOTOR['half'][0] + 2.0 + r; th = max(theta, THETA_MIN) if math.cos(theta) >= 0 else min(theta, math.pi - THETA_MIN)
    return np.array([x + d * math.cos(th), np.sign(y) * min(y_in + r, y_out - r - 2.0), R + d * math.sin(th)])


def layout(q, A, r_route, r_land):
    """the legs' centre lines: segments (p0, p1, wheels carried, chain, its place in the chain), chains (parent chain or
    None), and the roots' points. A chain runs root to wheel (a leg, or a trunk), or fork to wheel (a branch). r_route
    sets the clearances; r_land the legs' end radius (landing()): one for all, or a list by chain (the order chains are
    made in), so a slim leg's end still reaches into its tube's wall"""
    R, TW, hy, clr, H = A['R'], A['TW'], A['hy'], A['clr'], A['H']; (xn, _), (xt, _) = A['nose'], A['rear']
    z_root = clr + q['root_z'] * H; segs, chains, roots3, grips = [], [], [], []
    side_tyres = [abs(y) - TW / 2 for x, y in A['axles'] if xt - 15.0 <= x <= xn + 15.0]
    def band(r):                                                        # |y| a control beside the body may take: off its side,
        lo = hy + r + 5.0; hi = (min(side_tyres) if side_tyres else 1e9) - r - 5.0      # inboard of the tyres beside it (a
        return (lo, hi) if hi > lo else (0.5 * (lo + hi), 0.5 * (lo + hi))             # Bezier curve stays within its controls)
    def add_chain(P, carried, parent):
        ci = len(chains); chains.append(parent)
        segs.extend((P[k], P[k + 1], carried, ci, k) for k in range(len(P) - 1)); return ci
    def grow(p0, p1, t0, arch, carried, parent, t1=np.array([0.0, 0.0, 1.0])):
        """a cubic curve from p0 leaving along t0, arriving at p1 from along t1 (from above, or straight into the side of
        its tube), arched by arch in z"""
        sg = np.sign(p1[1]); lo, hi = band(r_route); reach = 0.35 * np.linalg.norm(p1 - p0)
        c1 = p0 + t0 * reach + np.array([0.0, 0.0, arch]); c2 = p1 + t1 * max(reach, 30.0) + np.array([0.0, 0.0, arch])
        for c in (c1, c2):
            if xt - 15.0 <= c[0] <= xn + 15.0:
                c[1] = sg * float(np.clip(abs(c[1]), lo, hi))
        t = T_SEG[:, None]
        return add_chain((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * p1, carried, parent)
    out = lambda sg: np.array([0.0, sg, 0.0])                            # square off the body's side
    for sg in (1.0, -1.0):
        side = [i for i, h in enumerate(A['axles']) if np.sign(h[1]) == sg]
        rl = lambda: r_land[len(chains)] if isinstance(r_land, (list, tuple)) else r_land   # the next chain's end radius
        ends = [landing(*A['axles'][i], R, TW, rl() if not isinstance(r_land, (list, tuple)) else max(r_land)) for i in side]
        if q['tree'] > 0.5:
            xr0 = xt + 30.0 + q['root_x'] * (xn - xt - 60.0); P0 = np.array([xr0, sg * hy, z_root])
            lo, hi = band(r_route)                                      # the fork too, in the band
            F = np.array([0.5 * (xr0 + np.mean([e[0] for e in ends])), sg * float(np.clip(hy + q['fork_y'], lo, hi)), R + q['fork_z'] * (z_root - R)])
            c1 = P0 + out(sg) * 0.4 * np.linalg.norm(F - P0); t = T_SEG[:, None]
            trunk = add_chain((1 - t) ** 2 * P0 + 2 * (1 - t) * t * c1 + t ** 2 * F, side, None); roots3.append(P0)
            tf = (F - c1) / max(np.linalg.norm(F - c1), 1e-9)
            for e, i in zip(ends, side):                                # the branches carry on from the trunk's direction
                e = landing(*A['axles'][i], R, TW, rl())
                grow(F, e, tf, q['bend'] * 0.25 * np.linalg.norm(e - F), [i], trunk); grips.append((i, e))
        else:                                                           # each wheel its own legs, braced when more than one
            nm = int(q.get('members', 1.0)); dx = 150.0 * q.get('spread_x', 0.0); dz = 0.7 * H * q.get('spread_z', 0.0)
            if nm > 1 and math.hypot(dx, dz) < 40.0:                    # roots at least 40 mm apart, or they are one leg
                dx, dz = (dx, dz) if math.hypot(dx, dz) > 1e-6 else (1.0, 1.0); k = 40.0 / math.hypot(dx, dz); dx, dz = dx * k, dz * k
            offs = {1: [(0.0, 0.0)], 2: [(-0.5, 0.5), (0.5, -0.5)], 3: [(-0.5, 0.5), (0.5, 0.5), (0.0, -0.5)]}[nm]
            for e, i in zip(ends, side):
                xw = A['axles'][i][0]; x0 = float(np.clip(xw, xt + 30.0, xn - 30.0))
                for ox, oz in offs:
                    P0 = np.array([float(np.clip(x0 + ox * dx, xt + 20.0, xn - 20.0)), sg * hy, float(np.clip(z_root + oz * dz, clr + 15.0, clr + H - 15.0))])
                    th = math.pi / 2 if nm == 1 else math.atan2(P0[2] - R, P0[0] - xw)   # a braced leg grips the tube on its root's side
                    e2 = landing(*A['axles'][i], R, TW, rl(), th); t1 = np.array([math.cos(th), 0.0, math.sin(th)]) if nm > 1 else np.array([0.0, 0.0, 1.0])
                    grow(P0, e2, out(sg), q['bend'] * 0.25 * np.linalg.norm(e2 - P0), [i], None, t1); roots3.append(P0); grips.append((i, e2))
    return segs, chains, roots3, grips


def downstream(segs, chains):
    """for each segment, the segments beyond it (itself, the rest of its chain, and every chain that grows from it)"""
    kids = {}
    for ci, parent in enumerate(chains):
        if parent is not None:
            kids.setdefault(parent, []).append(ci)
    def below(ci):
        out = [ci]
        for k in kids.get(ci, []):
            out += below(k)
        return out
    return [[j for j, s in enumerate(segs) if (s[3] == ci and s[4] >= k) or (s[3] != ci and s[3] in below(ci))]
            for ci, k in ((s[3], s[4]) for s in segs)]


def rule_radii(A, segs, mass):
    """the first guess at each segment's radius (the module's rule)"""
    Fz = LOAD * mass * 9.81 / 2.0
    forces = [np.array([sx * MU * Fz, sy * MU * Fz, Fz]) for sx in (-1, 1) for sy in (-1, 1)]
    def strength(p, carried):
        M = sum(max(np.linalg.norm(np.cross(np.array([*A['axles'][i], 0.0]) - p, F)) for F in forces) for i in carried)
        return (4.0 * M / (math.pi * SIGMA)) ** (1.0 / 3.0)
    path = {}
    for p0, p1, c, *_ in segs:
        for i in c:
            path[i] = path.get(i, 0.0) + float(np.linalg.norm(p1 - p0))
    Fs = mass * 9.81 / 2.0
    stiff = lambda c: max((4.0 * Fs * path[i] ** 3 / (3.0 * math.pi * E_PLA * DEFL)) ** 0.25 for i in c)
    return [max(R_MIN, strength(p0, c), strength(p1, c), stiff(c)) for p0, p1, c, *_ in segs]


def flared(segs, roots3, radii):
    """the radii with each leg's root flared: FLARE times at the body's side, back to its own over FLARE_LEN; and no
    segment thinner than any beyond it"""
    out = list(radii)
    for j, (p0, p1, c, ci, k) in enumerate(segs):
        root = next((rp for rp in roots3 if any(s[3] == ci and s[4] == 0 and np.allclose(s[0], rp) for s in segs)), None)
        if root is not None:
            s0 = float(np.linalg.norm(p0 - root)) if k else 0.0
            out[j] = radii[j] * (1.0 + (FLARE - 1.0) * math.exp(-s0 / FLARE_LEN))
    return out


def faults(sp, body, caps, tubes, roots3, ends):
    """why the design can't be made, or []: a leg's segment near a root starts in the side wall, so only its points 2.5
    radii past every root are tested against the body; a leg's points near a landing are where it meets its tube, so
    only the rest are tested against tyres and tubes"""
    R, TW = sp['R'], sp['TW']
    for x, y in sp['wheels']:
        if (RB.hull_dist(body, _tyre_pts(x, y, R, TW)) < 3.0).any():
            return ['a tyre in the body']
    for Hh in tubes:
        if (RB.hull_dist(body, Hh) < 2.0).any():
            return ["a motor's tube in the body"]
    for p0, p1, r in caps:
        P = np.linspace(p0, p1, 6)
        if (P[:, 2] - r < 5.0).any():
            return ['a leg on the ground']
        far = P[np.min([np.linalg.norm(P - rp, axis=1) for rp in roots3], axis=0) > 2.5 * r]
        if len(far) and (RB.hull_dist(body, far) < r - 1.0).any():
            return ['a leg through the body']
        Q = P[np.min([np.linalg.norm(P - e, axis=1) for e in ends], axis=0) > r + 20.0]
        for x, y in sp['wheels']:
            if len(Q) and np.any((np.hypot(Q[:, 0] - x, Q[:, 2] - R) < R + r + 3.0) & (np.abs(Q[:, 1] - y) < TW / 2 + r + 3.0)):
                return ['a leg through a tyre']
        for Hh in tubes:
            if len(Q) and (RB.hull_dist(Hh, Q) < r - 1.0).any():
                return ["a leg through a motor's tube"]
    return []


def _tyre_pts(x, y, R, TW, n=20):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.vstack([np.c_[x + rr * np.cos(a), np.full(n, y + w), R + rr * np.sin(a)] for rr in (0.5 * R, R) for w in (-TW / 2, 0.0, TW / 2)])


def assemble(q, A, segs, radii, roots3, r_land, name='tree'):
    """the spec from the anchors and the sized legs: body with each root's round mount, motor tubes, masses"""
    C, items, box, _ = B.parts(); R, TW, dz = A['R'], A['TW'], A['dz']
    caps = [(p0, p1, r) for (p0, p1, *_), r in zip(segs, radii)]
    roots = [(rp[0], rp[2], next(r for (p0, _, r) in caps if np.allclose(p0, rp)) + 6.0) for rp in roots3]   # round mounts
    body = B.shell(q, A, roots)
    a = np.linspace(0, 2 * np.pi, 20, endpoint=False); tubes, motors = [], []
    for x, y in A['axles']:
        y0, y1 = tube_ends(x, y, R, TW, r_land); sg = np.sign(y)
        tubes.append(np.vstack([np.c_[x + TUBE_R * np.cos(a), np.full(20, sg * yy), R + TUBE_R * np.sin(a)] for yy in (y0, y1)]))
        motors.append((x, sg * (abs(y) + TW / 2 - B.MOTOR['rim_in'] - B.MOTOR['half'][1]), R))
    its = [(n, m, p + [q['dxp'] if n.startswith('pack') else 0.0, 0.0, dz]) for n, m, p in items]
    its += [(f'motor_{i}', B.MOTOR['m'], np.array(p)) for i, p in enumerate(motors)]
    bx = dict(box, **{f'motor_{i}': np.array(B.MOTOR['half']) for i in range(len(motors))})
    M, G, I = RB.inertia(its, bx)
    def add(m, c, Ic):
        nonlocal M, G, I
        M2 = M + m; G2 = (M * G + m * c) / M2; d0, d1 = G - G2, c - G2
        I = I + M * (d0 @ d0 * np.eye(3) - np.outer(d0, d0)) + Ic + m * (d1 @ d1 * np.eye(3) - np.outer(d1, d1)); M, G = M2, G2
    m, c, Ic = S.shell_mass(body); k = B.PLA_WALL / S.COVER; add(k * m, c, k * Ic)          # the body's walls
    for Q, (x, y) in zip(tubes, A['axles']):                            # the tubes: their walls, solid, less the motor's bore
        y0, y1 = tube_ends(x, y, R, TW, r_land); Lt = y1 - y0
        m = math.pi * (TUBE_R ** 2 - B.MOTOR['half'][0] ** 2) * Lt * S.PLA; add(m, Q.mean(0), m * TUBE_R ** 2 / 2 * np.eye(3))
    for p0, p1, r in caps:                                              # printed legs: rods
        Lc = float(np.linalg.norm(p1 - p0)); m = math.pi * r * r * Lc * S.PLA * FILL; u = (p1 - p0) / max(Lc, 1e-9)
        add(m, 0.5 * (p0 + p1), m * Lc * Lc / 12 * (np.eye(3) - np.outer(u, u)))
    sp = RB.spec(name, [body] + tubes, M, G, I, A['axles'], R, TW=TW,
                 notes=[f"{len(A['axles'])} wheels R {R:.0f} on {'trees' if q['tree'] > 0.5 else 'legs'}"])
    sp['struts'] = [(np.asarray(p0).tolist(), np.asarray(p1).tolist(), float(r)) for p0, p1, r in caps]
    sp = RB.dims(sp)
    mo = sp['motor']; g = q['gear']; sp['motor'] = dict(stall=mo['stall'] * g, w0=mo['w0'] / g, N=mo['N'] * g, Ir=mo['Ir'])
    return sp, body, tubes


def land_r(segs, base):
    """the legs' end radius: the thickest last segment of a chain that ends at a wheel"""
    return max(base[j] for j, sg in enumerate(segs) if len(sg[2]) == 1 and sg[4] == len(T_SEG) - 2)


def chain_ends(segs, base):
    """each chain's end radius (its last segment's), in chain order"""
    n = max(sg[3] for sg in segs) + 1; out = [0.0] * n
    for j, sg in enumerate(segs):
        if sg[4] == len(T_SEG) - 2:
            out[sg[3]] = base[j]
    return out


def build(q, name='tree', radii=None, flare=True):
    """the robot spec of the design q (KEYS), or None when it can't be made (faults()). radii: each segment's radius
    before the flare (snap.py's, from the sim), else the rule's, sized at a guessed 5 kg, then at the mass that gives.
    The legs are laid out again once their sizes are known: their clearances by the thickest, their ends by the end
    radius, so each end merges into its tube"""
    A = anchors(q)
    if A is None:
        return None
    if radii is None:
        segs, chains, roots3, grips = layout(q, A, 16.0, 16.0); base = rule_radii(A, segs, 5.0)
        sp, *_ = assemble(q, A, segs, flared(segs, roots3, base), roots3, land_r(segs, base), name)
        segs, chains, roots3, grips = layout(q, A, max(base), land_r(segs, base)); base = rule_radii(A, segs, 1.05 * sp['mass'] / 1000.0)
    else:
        base = list(radii); segs, chains, roots3, grips = layout(q, A, max(base), 16.0)
    r_land = land_r(segs, base)                                          # the tubes reach in for the thickest end
    segs, chains, roots3, grips = layout(q, A, max(base), chain_ends(segs, base))
    rad = flared(segs, roots3, base) if flare else list(base)          # snap.py's sizes are final (they size the flare's segments too)
    sp, body, tubes = assemble(q, A, segs, rad, roots3, r_land, name)
    ends = [g for _, g in grips]
    if faults(sp, body, [(p0, p1, r) for (p0, p1, *_), r in zip(segs, rad)], tubes, roots3, ends):
        return None
    sp.update(anchors=A, strut_wheels=[list(sg[2]) for sg in segs], strut_down=downstream(segs, chains), strut_base=base,
              strut_root=[sg[4] == 0 and any(np.allclose(sg[0], rp) for rp in roots3) for sg in segs], tube_of={i + 1: i for i in range(len(A['axles']))},
              grips=[(i, np.asarray(g).tolist()) for i, g in grips], roots3=[np.asarray(r).tolist() for r in roots3],
              hubs=[[x, np.sign(y) * 0.5 * sum(abs(v) for v in tube_ends(x, y, A['R'], A['TW'], r_land)), A['R']] for x, y in A['axles']])
    if q['limb'] > 0.5:
        sp = B._tail(sp, q, body, A['rear'][1])
    return sp


def sobol(n, seed=0):
    from scipy.stats import qmc
    Z = qmc.Sobol(len(KNOBS), scramble=True, seed=seed).random_base2(int(math.ceil(math.log2(n))))[:n]
    return [{k: float(lo + z * (hi - lo)) for (k, lo, hi, _), z in zip(KNOBS, row)} for row in Z]


def braces(q):
    """the designs to try, in order: q, then braced harder (Zach, when a leg can't be sized to fit: "retry"): a single leg
    a wheel to 2, then 3; a tree to 2 legs a wheel, then 3"""
    m = 0 if q['tree'] > 0.5 else int(q['members'])
    return [q] + [dict(q, tree=0.0, members=float(k)) for k in range(max(m, 1) + 1, 4)]


def sized(q, n_falls=None):
    """the generator's design: its legs sized from G1's falls (snap.size), braced harder and tried again when they can't
    be (the sized legs no longer fit their routes, or still snap); None when even 3 legs a wheel can't. The spec carries
    the design it ended as (q_used) and how many times it was braced (braced)"""
    import snap as SN
    for k, qq in enumerate(braces(q)):
        res = SN.size(qq, n=n_falls or SN.N_FALL, log=lambda *_: None)
        if res is None:
            continue
        sp0, s0, sp, s, hist = res
        if not (hist and hist[-1].get('clash')) and s.max() <= SN.SIGMA_ULT:
            return dict(sp, peak_mpa=float(s.max()), q_used=qq, braced=k)
    return None


def _made(a):
    """a worker: the generator's design (sized()), then its one shape (blend.shape)"""
    i, q, path = a
    import blend as BL
    sp = sized(q)
    if sp is None:
        return i, None
    n, bodies = BL.shape(sp, path)
    return i, dict(sp=sp, q=sp['q_used'], worst=sp['peak_mpa'], braced=sp['braced'], tris=n, bodies=bodies)


def sheet(seed=None, n=15):
    """n Sobol designs as the generator makes them: legs sized from G1's falls (snap.py), blended into one shape (blend.py),
    motors in their tubes -> out/body/trees.png"""
    from multiprocessing import Pool
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import snap as SN, blend as BL
    seed = int(np.random.SeedSequence().entropy % 100000) if seed is None else seed
    os.makedirs(os.path.join(B.OUT, 'shapes'), exist_ok=True); qs, tried = [], 0
    for q in sobol(16 * n, seed):
        if len(qs) >= n:
            break
        tried += 1
        if build(q) is not None:
            qs.append(q)
    J = [(i, q, os.path.join(B.OUT, 'shapes', f'{seed}_{i}.stl')) for i, q in enumerate(qs)]
    with Pool(min(len(J), 24)) as pool:
        R = dict(pool.map(_made, J, chunksize=1))
    cols = 3; rows = math.ceil(len(J) / cols); fig = plt.figure(figsize=(12, 3.3 * rows)); fig.patch.set_facecolor('white')
    for i, q, path in J:
        ax = fig.add_subplot(rows, cols, i + 1); ax.set_axis_off(); r = R.get(i)
        if r is None:
            ax.set_title(f'{i + 1}: refused (even 3 legs a wheel could not be sized to fit)', fontsize=9, loc='left'); continue
        sp = r['sp']; ax.imshow(BL.render(sp, path))
        name = lambda qq: 'a tree' if qq['tree'] > 0.5 else f"{int(qq['members'])} leg{'s' if int(qq['members']) > 1 else ''} a wheel"
        legs = name(r['q']) if not r['braced'] else f"{name(r['q'])} (braced from {name(q)})"
        held = f"holds"
        pieces = '' if r['bodies'] == 1 else f"; {r['bodies']} pieces"
        ax.set_title(f"{i + 1}: {len(sp['wheels'])} wheels on {legs}{', tail' if sp.get('limb') else ''}; {held} ({r['worst']:.0f} MPa)\n"
                     f"legs {SN.legs_g(sp):.0f} g, {sp['mass'] / 1000:.1f} kg{pieces}", fontsize=9, loc='left')
    fig.suptitle(f'The generator: Sobol designs (seed {seed}), legs sized from {SN.N_FALL} falls from 300 mm (braced harder when they\'d clash),\n'
                 f'blended into one shape, motors in their tubes', fontsize=12, x=0.02, ha='left')
    plt.tight_layout(rect=(0, 0, 1, 0.98)); p = os.path.join(B.OUT, 'trees.png'); plt.savefig(p, dpi=90)
    print(p, 'seed', seed, f'{len(J)} of {tried} draws built;', ', '.join(f"{i + 1}: {'none' if R.get(i) is None else str(R[i]['bodies']) + ' body'}" for i, *_ in J))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sheet':
        sheet(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        print(__doc__)
