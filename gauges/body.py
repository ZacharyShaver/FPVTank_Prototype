"""Anchor-first bodies (2026-10-28, a prototype). Zach, on the strict search's random shapes: "those do not look good we
need to work on that code. lets see if we can find a more elegant solution", then "you could try picking the points
you need before generation instead of after ... like wheels are at xyz front at xyz height", "maybe not the top point".

The old generator built a body (the Trainer's tub, or a skin hulled round every part) and placed the wheels, packs and
tail by their own knobs, then had to repair what floated (knobs.make strict). Here the knobs pick anchor points first,
each inside the room the earlier ones leave, and the body is made to join them, so nothing can float or pass through:
  1. the wheels: radius and width, then the axles along the body (tyres 15 mm apart, each 25 mm inside the body's ends)
     and out from it (front and rear apart: room for the 37 mm motor, plus a spacer each);
  2. the ends: the nose point (how far ahead of the parts, how high the front face stands) and the rear point (how far
     behind, how high), and the ride height (the axle sits in the body's side wall, 20 mm from its belly and top);
  3. the top is not picked: the parts inside set it (Zach: "maybe not the top point").
The body is the hull of that profile, rounded in plan, round the parts it must hold; a pod joins it to each motor; the
tail's turntable sits 20 mm off the rear face at the rear point's height; its stowed and push angles are picked from the
angles where it clears the body and tyres. The wheels sit outside the body, so nothing clips them.

    python gauges/body.py sheet [seed]   -> gauges/out/body/samples.png (a Sobol sample, rendered by MuJoCo)
"""
import os, sys, math
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import robots as RB, search as S

OUT = os.path.join(config.GAUGES_OUT, 'body')
WALL = 3.0                                 # mm: the body's wall and the parts' margin inside it
PLA_WALL = 2.0                             # mm: the body's and pods' printed wall, for its mass
MOTOR = dict(m=205.0 + 34.6, half=(18.5, 40.7, 18.5), rim_in=13.0)   # the 37 mm gearmotor; its outer end 13 mm inside the tyre's outer face (the Trainer's)
MOTOR_IN = 15.0                            # mm: the most a motor may reach into the body (its wall and mount)
POD = 23.0                                 # mm: a motor pod's half-size round the axle (the box pods, superseded by MOUNT_R)
# Required shapes (Zach: "you could set things like the flat bottom requirement ... maybe like a circle for a wheel
# mount"): the body's bottom is flat from the rear's underside to the nose's; each axle has a round mount, MOUNT_R*,
# in the body's side, the motor's round housing running out from it to the tyre; the tail's turntable sits on a round
# boss, TURN_R*, on the rear face.
MOUNT_R, TURN_R = 25.0, 20.0
KNOBS = [   # (key, low, high, what it is)
    ('R', 35.0, 75.0, "the wheels' radius, mm"),
    ('TW', 25.0, 80.0, "the tyres' width, mm"),
    ('six', 0.0, 1.0, 'six wheels (above half)'),
    ('u_wb', 0.0, 1.0, 'the wheelbase: tyres 15 mm apart (0) to the longest the body allows (1)'),
    ('u_xw', 0.0, 1.0, 'where the wheelbase sits along the body: back (0) to front (1)'),
    ('a_f', 0.0, 60.0, "the front wheels' spacer past the motor's room, mm (the front width)"),
    ('a_r', 0.0, 60.0, "the rear wheels' spacer, mm (the rear width)"),
    ('w', 0.0, 40.0, "the body's width past the parts', each side, mm"),
    ('n_x', 0.0, 80.0, "the nose point's reach ahead of the parts, mm"),
    ('n_z', 0.25, 1.0, "the nose point's height, of the body's (1: a square front, lower: a sloped one)"),
    ('n_lo', 0.0, 0.5, "the nose's underside: how high its bottom edge rises at the nose, of the body's (0: flat to the nose)"),
    ('t_x', 0.0, 80.0, "the rear point's reach behind the parts, mm"),
    ('t_z', 0.25, 1.0, "the rear point's height, of the body's (the tail mounts there)"),
    ('t_lo', 0.0, 0.5, "the rear's underside, as the nose's"),
    ('u_clr', 0.0, 1.0, 'the axle in the side wall: low, the body riding high (0), to high, the body low (1)'),
    ('r_c', 5.0, 60.0, "the body's corners seen from above, radius mm"),
    ('dxp', -20.0, 60.0, 'the packs moved forward, mm'),
    ('gear', 0.4, 2.5, 'the gearing, times the stock 30:1'),
    ('limb', 0.0, 1.0, 'a tail (above half)'),
    ('L', 80.0, 350.0, "the tail's length, mm"),
    ('tq', 0.3, 4.0, "the tail servo's stall torque, N m"),
    ('u_stow', 0.0, 1.0, "the stowed angle, from the lowest clear angle (0) to the highest (1)"),
    ('u_push', 0.0, 1.0, "the step push's angle, from the steepest clear one (0) to the shallowest (1)")]
KEYS = [k for k, *_ in KNOBS]


def parts():
    """the parts inside (search.components: the head, Pi, packs, ESCs and the rest, at the Trainer's base clearance),
    their mass items and boxes (chassis3, walls and wheel modules out)"""
    import chassis3 as C3
    b = C3.base(); C = S.components()
    items = [(n, m, np.asarray(p, float)) for n, m, p in b['items'] if not n.startswith(S.STRUCT)]
    return C, items, b['box'], b['clr0']


def anchors(q):
    """the points the body must join, picked in order, each inside the room the last left: None when the wheels can't
    fit the body (too big for its length)"""
    C, _, _, clr0 = parts(); P = np.vstack(list(C.values()))
    x0, x1 = P[:, 0].min() - WALL, P[:, 0].max() + WALL; hy = np.abs(P[:, 1]).max() + WALL + q['w']
    H = P[:, 2].max() - clr0 + 2 * WALL                                  # the parts' height sets the body's (not picked)
    R, TW = q['R'], q['TW']
    xn, xt = x1 + q['n_x'], x0 - q['t_x']                               # the nose and rear points
    six = q['six'] > 0.5
    wb_lo = 2 * (2 * R + 15.0) if six else 2 * R + 15.0; wb_hi = (xn - 25.0) - (xt + 25.0)
    if wb_lo > wb_hi:
        return None
    wb = wb_lo + q['u_wb'] * (wb_hi - wb_lo); room = (xn - 25.0) - (xt + 25.0) - wb
    xr = xt + 25.0 + q['u_xw'] * room; xf = xr + wb
    lo_a = MOUNT_R + WALL                                               # the axle above the belly: its round mount inside the side,
    ha_hi = min(H - MOUNT_R - WALL, R - 5.0)                            # the belly at least 5 mm up
    if ha_hi < lo_a:
        return None
    ha = ha_hi - q['u_clr'] * (ha_hi - lo_a); clr = R - ha
    y0 = hy + 5.0 + TW / 2 + max(0.0, 2 * MOTOR['half'][1] + MOTOR['rim_in'] - MOTOR_IN - 5.0 - TW)   # the motor's room
    yf, yr = y0 + q['a_f'], y0 + q['a_r']
    axles = [(xf, yf), (xf, -yf), (xr, yr), (xr, -yr)] + ([(0.5 * (xf + xr), 0.5 * (yf + yr)), (0.5 * (xf + xr), -0.5 * (yf + yr))] if six else [])
    n_lo, t_lo = q.get('n_lo', 0.0), q.get('t_lo', 0.0)
    return dict(R=R, TW=TW, clr=clr, H=H, hy=hy, x0=x0, x1=x1, nose=(xn, clr + max(q['n_z'], n_lo + 0.1) * H), rear=(xt, clr + max(q['t_z'], t_lo + 0.1) * H),
                nose_lo=clr + n_lo * H, rear_lo=clr + t_lo * H,
                axles=axles, dz=clr - clr0)


def _plan(xc, hy, r, z, front, n=6):
    """a cross-section's end at height z, rounded in plan: points from the side to the centre line"""
    a = np.linspace(0, np.pi / 2, n); s = 1.0 if front else -1.0; r = min(r, hy)
    return np.c_[xc - s * r + s * r * np.sin(a), (hy - r + r * np.cos(a)), np.full(n, z)]


def shell(q, A, circles):
    """the body's hull: the profile through the anchors (a flat bottom, the undersides, the front and rear faces, their
    slopes to the top), rounded in plan, each (x, z, r) circle in both sides (a round mount), round the parts inside"""
    C = parts()[0]; clr, H, hy, dz = A['clr'], A['H'], A['hy'], A['dz']; (xn, zn), (xt, zt) = A['nose'], A['rear']; top = clr + H
    run_n, run_t = 1.2 * (A['nose_lo'] - clr), 1.2 * (A['rear_lo'] - clr)          # the undersides rise at about 40 degrees
    span = xn - xt - 50.0                                                           # at least 50 mm of flat bottom
    if run_n + run_t > span:
        k = span / (run_n + run_t); run_n, run_t = run_n * k, run_t * k
    prof_f = [(xn - run_n, clr), (xn, A['nose_lo']), (xn, zn), (A['x1'], top)]     # the flat bottom's front end, the nose's
    prof_r = [(xt + run_t, clr), (xt, A['rear_lo']), (xt, zt), (A['x0'], top)]     # underside, the front face, its slope to the top
    pts = [_plan(x, hy, q['r_c'], z, True) for x, z in prof_f] + [_plan(x, hy, q['r_c'], z, False) for x, z in prof_r]
    a = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    for x, z, r in circles:
        pts.append(np.c_[x + r * np.cos(a), np.full(16, hy), z + r * np.sin(a)])
    half = np.vstack(pts); body = np.vstack([half, half * [1, -1, 1]])
    inside = [Q + [q['dxp'] if k.startswith('pack') else 0.0, 0.0, dz] for k, Q in C.items()]
    return RB.hull(np.vstack([body] + inside))                            # the parts that poke past the profile round it out


def build(q, name='body'):
    """the robot spec (robots.spec's form, the gauges read it as any other) of the design q (KEYS), or None"""
    A = anchors(q)
    if A is None:
        return None
    C, items, box, _ = parts(); R, TW, clr, H, hy, dz = A['R'], A['TW'], A['clr'], A['H'], A['hy'], A['dz']
    (xn, zn), (xt, zt) = A['nose'], A['rear']
    a = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    body = shell(q, A, [(x, R, MOUNT_R) for x, y in A['axles']])        # each round mount, in the side
    pods, motors = [], []
    for x, y in A['axles']:                                             # the motor's round housing, from the side to its tyre, 3 mm clear
        sg = np.sign(y); y_in = abs(y) - TW / 2 - 3.0; ring = lambda yy: np.c_[x + MOUNT_R * np.cos(a), np.full(16, sg * yy), R + MOUNT_R * np.sin(a)]
        pods.append(np.vstack([ring(hy - 5.0), ring(y_in)]))
        motors.append((x, sg * (abs(y) + TW / 2 - MOTOR['rim_in'] - MOTOR['half'][1]), R))
    its = [(n, m, p + [q['dxp'] if n.startswith('pack') else 0.0, 0.0, dz]) for n, m, p in items]
    its += [(f'motor_{i}', MOTOR['m'], np.array(p)) for i, p in enumerate(motors)]
    bx = dict(box, **{f'motor_{i}': np.array(MOTOR['half']) for i in range(len(motors))})
    M, G, I = RB.inertia(its, bx)
    for Q in [body] + pods:                                             # the printed walls
        m, c, Ic = S.shell_mass(Q); k = PLA_WALL / S.COVER
        M2 = M + k * m; G2 = (M * G + k * m * c) / M2; d0, d1 = G - G2, c - G2
        I = I + M * (d0 @ d0 * np.eye(3) - np.outer(d0, d0)) + k * Ic + k * m * (d1 @ d1 * np.eye(3) - np.outer(d1, d1)); M, G = M2, G2
    sp = RB.spec(name, [body] + pods, M, G, I, A['axles'], R, TW=TW, notes=[f"{len(A['axles'])} wheels R {R:.0f}, anchors first"])
    mo = sp['motor']; g = q['gear']; sp['motor'] = dict(stall=mo['stall'] * g, w0=mo['w0'] / g, N=mo['N'] * g, Ir=mo['Ir'])
    sp['anchors'] = A
    if q['limb'] > 0.5:
        sp = _tail(sp, q, body, zt)
    return sp


def _clear(sp, lm, pitch):
    """the tail at a pitch (yaw 0) clears the body, pods and tyres, past its first 20 mm"""
    P = RB.limb_points(lm, 0.0, pitch, k=24); P = P[np.linalg.norm(P - np.asarray(lm['base']), axis=1) > 20.0]
    for h in sp['hulls']:
        if (RB.hull_dist(h, P) < RB.LINK_R).any():
            return False
    for x, y in sp['wheels']:
        if np.any((np.hypot(P[:, 0] - x, P[:, 2] - sp['R']) < sp['R'] + RB.LINK_R) & (np.abs(P[:, 1] - y) < sp['TW'] / 2 + RB.LINK_R)):
            return False
    for p0, p1, r in sp.get('struts', ()):
        if (seg_dist(P, p0, p1) < r + RB.LINK_R).any():
            return False
    return True


def seg_dist(P, p0, p1):
    """each point's distance to the segment p0-p1"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); e = p1 - p0
    t = np.clip(((np.asarray(P) - p0) @ e) / max(e @ e, 1e-12), 0, 1); return np.linalg.norm(P - (p0 + np.outer(t, e)), axis=1)


def _tail(sp, q, body, zt):
    """the tail's turntable 20 mm off the rear face at the rear point's height; its stowed and push angles picked from
    the clear ones (None when no stowed angle clears)"""
    xs = RB.rear_surface([body], zt); base = np.array([xs - 20.0, 0.0, zt])
    for _ in range(6):                                                  # a sloped rear: back until 20 mm clear
        d = float(RB.hull_dist(body, [base])[0])
        if d >= 19.5:
            break
        base[0] -= 20.0 - d + 0.5
    xb = float(RB.rear_surface([body], zt)); a = np.linspace(0, 2 * np.pi, 16, endpoint=False)          # the round boss: from inside
    boss = np.vstack([np.c_[np.full(16, x), TURN_R * np.cos(a), zt + TURN_R * np.sin(a)] for x in (xb + 5.0, base[0] + 12.0)])   # the face to 12 mm
    sp = dict(sp, hulls=list(sp['hulls']) + [boss])                     # short of the turntable's centre (the link's root clear)
    probe = dict(base=base.tolist(), L=q['L'], foot_r=RB.FOOT_R)
    stow = [a for a in range(20, 171, 5) if _clear(sp, probe, a)]
    push = [a for a in range(-90, -9, 5) if _clear(sp, probe, a)]
    if not stow or not push:
        return None
    ts = stow[min(len(stow) - 1, int(q['u_stow'] * len(stow)))]; tp = push[min(len(push) - 1, int(q['u_push'] * len(push)))]
    out = RB.add_limb(RB.dims(sp), q['L'], q['tq'], float(tp), float(ts), base=base)
    return dict(out, solid_tail=True)


def sample(rng):
    return {k: float(lo + rng.random() * (hi - lo)) for k, lo, hi, _ in KNOBS}


def sobol(n, seed=0):
    """n designs from a scrambled Sobol sequence over the knobs (what a search's spread starts from)"""
    from scipy.stats import qmc
    Z = qmc.Sobol(len(KNOBS), scramble=True, seed=seed).random_base2(int(math.ceil(math.log2(n))))[:n]
    return [{k: float(lo + z * (hi - lo)) for (k, lo, hi, _), z in zip(KNOBS, row)} for row in Z]


def render(sp, w=420, h=300, azim=145.0, elev=-20.0, strut_rgba=None):
    """the design at rest on the floor, rendered by MuJoCo (real depth): body tan, mounts and housings grey, tyres
    black, tail green; strut_rgba colours each printed leg segment its own (snap.py's stress), else all a light grey"""
    import mujoco
    x = RB.xml(sp, 1.0)
    for k, c in enumerate(strut_rgba or ()):
        x = x.replace(f'<geom name="strut{k}" ', f'<geom rgba="{c}" name="strut{k}" ', 1)
    x = x.replace('<mujoco>', f'<mujoco><visual><global offwidth="{w}" offheight="{h}"/><quality shadowsize="2048"/><headlight ambient=".35 .35 .35"/></visual>', 1)
    x = x.replace('<asset>', '<asset><texture name="chk" type="2d" builtin="checker" rgb1=".93 .93 .91" rgb2=".86 .86 .84" width="256" height="256"/>'
                  '<material name="floor" texture="chk" texrepeat="12 12"/>'
                  '<texture name="sky" type="skybox" builtin="gradient" rgb1=".97 .97 .96" rgb2=".85 .86 .84" width="64" height="64"/>', 1)
    x = x.replace('<worldbody>', '<worldbody><light pos=".4 -.6 1.5" dir="-.2 .4 -1" diffuse=".7 .7 .66" castshadow="true"/>', 1)
    x = x.replace('<geom type="plane"', '<geom type="plane" material="floor"', 1)
    for i in range(len(sp['hulls'])):
        x = x.replace(f'mesh="h{i}" friction', f'mesh="h{i}" rgba="{".86 .62 .48 1" if i == 0 else ".55 .58 .62 1"}" friction')
    x = x.replace('<geom type="cylinder"', '<geom type="cylinder" rgba=".13 .13 .14 1"').replace('<geom name="strut', '<geom rgba=".9 .89 .84 1" name="strut').replace('contype="2" conaffinity="0"', 'contype="2" conaffinity="0" rgba=".1 .5 .4 1"')
    m = mujoco.MjModel.from_xml_string(x); d = mujoco.MjData(m)
    E = RB.extremes(sp) * 1e-3; d.qpos[:3] = (0.0, 0.0, 0.0005 - E[:, 2].min()); d.qpos[3:7] = (1, 0, 0, 0)
    if sp.get('limb'):
        d.qpos[m.joint('lp').qposadr[0]] = math.radians(sp['limb']['th_stow'])
    mujoco.mj_forward(m, d)
    cam = mujoco.MjvCamera(); lo, hi = E.min(0), E.max(0); cam.lookat[:] = [(lo[0] + hi[0]) / 2, 0.0, 0.35 * (hi[2] - lo[2]) + d.qpos[2] + lo[2]]
    cam.distance = 1.9 * max(hi - lo); cam.azimuth = azim; cam.elevation = elev
    with mujoco.Renderer(m, h, w) as r:
        r.update_scene(d, cam); return r.render()


def sheet(seed=None, n=15, rng_mode='sobol'):
    """n designs drawn in order from a Sobol sequence over the knobs (or uniform at random), rendered by MuJoCo ->
    out/body/samples.png"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    seed = int(np.random.SeedSequence().entropy % 100000) if seed is None else seed
    os.makedirs(OUT, exist_ok=True); cols = 3; rows = math.ceil(n / cols)
    pool = sobol(4 * n, seed) if rng_mode == 'sobol' else [sample(np.random.default_rng(seed + i)) for i in range(4 * n)]
    fig = plt.figure(figsize=(12, 3.3 * rows)); fig.patch.set_facecolor('white'); drawn = tried = 0
    for q in pool:
        if drawn >= n:
            break
        tried += 1; sp = build(q)
        if sp is None:
            continue
        drawn += 1; ax = fig.add_subplot(rows, cols, drawn); ax.imshow(render(sp)); ax.set_axis_off()
        kind = f"{len(sp['wheels'])} wheels, R {sp['R']:.0f}{', tail' if sp.get('limb') else ''}"
        ax.set_title(f"{drawn}: {kind}; {sp['length']:.0f} x {sp['width']:.0f} mm, {sp['mass'] / 1000:.1f} kg", fontsize=9, loc='left')
    fig.suptitle(f'Anchor-first bodies, {"Sobol" if rng_mode == "sobol" else "random"} (seed {seed}): {drawn} of {tried} built '
                 f'(flat bottom, round wheel mounts, the tail on a round boss)', fontsize=12, x=0.02, ha='left')
    plt.tight_layout(rect=(0, 0, 1, 0.98)); p = os.path.join(OUT, 'samples.png'); plt.savefig(p, dpi=90); print(p, 'seed', seed, f'{drawn} of {tried} built')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sheet':
        sheet(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        print(__doc__)
