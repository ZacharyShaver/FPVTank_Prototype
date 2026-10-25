"""EXPLORATORY (2026-10-25): the drop-pose lab, step 1, passive poses. Guard arm E (chassis-v2/guard_arm.py) on the
four-wheel Trainer (SCORPION_LEGS=wheels): which pose, held through a fall, lands it on its wheels most often?

    python research/tumble/pose3.py cache      # the Trainer's parts and masses from chassis-v2 (CadQuery, ~10 s)
    python research/tumble/pose3.py check      # capsule arm against the real arm meshes, at the guard pose and others
    python research/tumble/pose3.py search     # statics of every pose, drops of the best, the finalists
      -> research/results/pose3/*.json

The arm is three capsules plus its parallelogram's crank and pushrod, from guard_arm's kinematics (fk, limits, link
masses); the body is the Trainer's own parts. A pose is kept only if the arm clears the body (each part's convex hull,
the arm's base and its rest peg excepted) and stays 5 mm above the floor when upright, so upright means on the wheels.
Robot drops are shell3.robot_trials' protocol (random orientation 5 mm up, spin to 3 rad/s, soft floor bounce 0.2);
the printed scale body is shell3's (the stand's six starts at 150 mm, hard floor 0.39). Frame: rugged.py's, the
centre line moved to Y 0, the floor at Z -25 when upright.
"""
import os, sys, json, pickle, time, subprocess
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
os.environ.setdefault('SCORPION_LEGS', 'wheels')
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
CHASSIS = os.path.abspath(os.path.join(ROOT, '..', 'chassis-v2'))
CACHE = os.path.join(CHASSIS, 'out', '_pose_trainer.pkl')
OUT = os.path.join(ROOT, 'results', 'pose3')
sys.path.insert(0, HERE)
import shell3 as S3
import scale_model as S
import tumble as T

WORKERS = 30
_C = None


def cache():
    """build the Trainer with the guard arm's base in a child (rugged fixes its leg choice at import)"""
    code = ("import sys, pickle; sys.path.insert(0, r'%s'); import rugged as R; R.CAGE = False; import guard_arm as GA; "
            "M, it = GA.robot(); "
            "pickle.dump(dict(parts={k: dict(t=v['t'], grp=v.get('grp'), ghost=bool(v.get('ghost'))) for k, v in M.items()}, items=it, "
            "guard_q=[float(a) for a in GA.guard_q(M)], ground=R.ground(M), yc=float(GA.YC)), open(r'%s', 'wb'))") % (CHASSIS, CACHE)
    subprocess.run([sys.executable, '-c', code], env=dict(os.environ, SCORPION_LEGS='wheels'), check=True, cwd=CHASSIS)


def C():
    """the cached Trainer: part points (centre line at Y 0), mass items, the arm module"""
    global _C
    if _C is None:
        if not os.path.exists(CACHE):
            cache()
        sys.path.insert(0, CHASSIS)
        import guard_arm as GA
        D = pickle.load(open(CACHE, 'rb')); yc = D['yc']
        pts = {k: np.unique(np.round(v['t'].reshape(-1, 3) - [0, yc, 0], 2), axis=0) for k, v in D['parts'].items() if not v['ghost']}
        tyres = [k for k in pts if k.startswith('tire_')]
        body = np.vstack([pts[k] for k in pts if k not in tyres]); body = body[ConvexHull(body).vertices]
        solid = {k: ConvexHull(p).equations for k, p in pts.items()
                 if not k.startswith(('armbase_', 'rest_peg', 'tire_', 'seal_', 'iso', 'grommet')) and len(p) > 4}
        items = [(n, m, np.asarray(c, float) - [0, yc, 0]) for n, m, c in D['items']]
        box = {k: np.ptp(p, 0) / 2 for k, p in pts.items()}
        _C = dict(GA=GA, yc=yc, pts=pts, tyres=tyres, body=body, solid=solid, items=items, box=box, guard_q=D['guard_q'], ground=D['ground'])
    return _C


# ---------------------------------------------------------------- the arm as capsules
def capsules(q):
    """(p0, p1, radius) in the body frame: upper arm (twin plates 26 tall), elbow hub, forearm tube (r 7), the tool to
    its jaw tips, the parallelogram's crank and pushrod (17 mm to the side, as guard_arm.parts draws them)"""
    c = C(); GA = c['GA']; yaw, a1, a2, g = q; k = GA.fk(q); E, Wr = k['E'], k['W']; U = GA.U
    lv = GA.LEV * U(a2 + 180); C1, C2 = GA.S + lv, E + lv
    w = lambda p, dy=0.0: np.array([GA.AXW + p[0] * np.cos(np.radians(yaw)) - dy * np.sin(np.radians(yaw)),
                                    p[0] * np.sin(np.radians(yaw)) + dy * np.cos(np.radians(yaw)), p[1]])
    return [(w(GA.S + 25 * U(a1)), w(E), 13.0), (w(E), w(E), 17.0), (w(E), w(Wr), 7.5),
            (w(Wr), w(Wr + 59 * U(g)), 14.5), (w(C1, -17), w(C2, -17), 5.0), (w(E, -17), w(C2, -17), 6.0)]


def capsule_points(caps, n=14):
    u = np.random.default_rng(1).normal(size=(n * 6, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
    out = []
    for p0, p1, r in caps:
        for f in np.linspace(0, 1, 5):
            out.append(p0 + (p1 - p0) * f + r * u)
    return np.vstack(out)


def clear(q):
    """the arm misses every body part (inflated convex hulls) and the floor"""
    c = C(); caps = capsules(q)
    for p0, p1, r in caps:
        X = p0 + (p1 - p0) * np.linspace(0, 1, 8)[:, None]
        if (X[:, 2] - r).min() < c['ground'] + 5.0:
            return False
        for eq in c['solid'].values():
            if ((X @ eq[:, :3].T + eq[:, 3]) <= r).all(1).any():
                return False
    return True


def layout(q, arm=True):
    """(g, CoM, inertia g mm^2): the Trainer's items as boxes of their parts' half-extents, plus the arm's links"""
    c = C(); GA = c['GA']; items = list(c['items'])
    if arm:
        items += [(n, m, np.asarray(p, float) - [0, c['yc'], 0]) for n, m, p in GA.mass_items(q, payload=False)]
    M = sum(m for _, m, _ in items); G = sum(m * p for _, m, p in items) / M; I = np.zeros((3, 3))
    for n, m, p in items:
        d = p - G; I += m * (d @ d * np.eye(3) - np.outer(d, d))
        h = c['box'].get(n)
        if h is not None:
            a, b, cc = (2 * h) ** 2; I += m / 12 * np.diag([b + cc, a + cc, a + b])
    return M, G, I


def hull(q, arm=True):
    c = C(); P = np.vstack([c['body']] + [c['pts'][k] for k in c['tyres']] + ([capsule_points(capsules(q))] if arm else []))
    return P[ConvexHull(P).vertices]


def static(q, arm=True):
    P = hull(q, arm); M, G, I = layout(q, arm); H = S3.support(P, G)
    sh, st = S3.static(P, G, H=H)
    return dict(share=sh, states=st, margin=S3.margin(P, G), stall=S3.stall(P, G, H=H), P=P, G=G)


# ---------------------------------------------------------------- drops
def robot_trials(q, n=200, seed=0, arm=True, dampratio=0.2, spin=3.0):
    """the full Trainer: the body's hull, the four tyres and the arm's capsules as separate geoms"""
    import mujoco
    c = C(); M, G, I = layout(q, arm); s = 1e-3; Isi = I * 1e-9
    full = ' '.join('%.8g' % v for v in (Isi[0, 0], Isi[1, 1], Isi[2, 2], Isi[0, 1], Isi[0, 2], Isi[1, 2]))
    mesh = lambda P: ' '.join('%.5f' % v for v in (P * s).ravel())
    assets = f'<mesh name="body" vertex="{mesh(c["body"])}"/>' + ''.join(f'<mesh name="{k}" vertex="{mesh(c["pts"][k][ConvexHull(c["pts"][k]).vertices])}"/>' for k in c['tyres'])
    geoms = '<geom type="mesh" mesh="body" friction="0.4 0.005 0.0005"/>' + ''.join(f'<geom type="mesh" mesh="{k}" friction="0.9 0.01 0.001"/>' for k in c['tyres'])
    if arm:
        for p0, p1, r in capsules(q):
            if np.linalg.norm(p1 - p0) < 1e-6:
                geoms += f'<geom type="sphere" size="{r * s:.4f}" pos="{p0[0] * s:.5f} {p0[1] * s:.5f} {p0[2] * s:.5f}" friction="0.4 0.005 0.0005"/>'
            else:
                geoms += (f'<geom type="capsule" size="{r * s:.4f}" fromto="{p0[0] * s:.5f} {p0[1] * s:.5f} {p0[2] * s:.5f} '
                          f'{p1[0] * s:.5f} {p1[1] * s:.5f} {p1[2] * s:.5f}" friction="0.4 0.005 0.0005"/>')
    dflt = '' if dampratio is None else f'<default><geom solref="0.02 {dampratio:.4f}"/></default>'
    xml = f"""<mujoco><option timestep="0.001"/>{dflt}<asset>{assets}</asset><worldbody>
      <geom type="plane" size="5 5 0.1" friction="0.6 0.005 0.0005"/>
      <body name="robot" pos="0 0 0.5"><freejoint/>
        <inertial pos="{G[0] * s:.5f} {G[1] * s:.5f} {G[2] * s:.5f}" mass="{M * 1e-3:.4f}" fullinertia="{full}"/>{geoms}</body></worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
    E = hull(q, arm) * s; rng = np.random.default_rng(seed); cnt = {k: 0 for k in T.CLASSES}
    for _ in range(n):
        qq = rng.normal(size=4); qq /= np.linalg.norm(qq)
        Rm = np.zeros(9); mujoco.mju_quat2Mat(Rm, qq); Rm = Rm.reshape(3, 3)
        mujoco.mj_resetData(m, d)
        d.qpos[:3] = (0.0, 0.0, 0.005 - (E @ Rm.T)[:, 2].min()); d.qpos[3:7] = qq
        d.qvel[3:6] = rng.uniform(-1, 1, 3) * spin
        still = 0
        for _ in range(160):
            mujoco.mj_step(m, d, nstep=50)
            if np.abs(d.qvel).max() < 0.02:
                still += 1
                if still >= 6: break
            else:
                still = 0
        cnt[T.classify(d.xmat[1].reshape(3, 3))] += 1
    return dict(p_upright=cnt['upright'] / n, counts=cnt, mass_g=round(M))


def print_body(P):
    """the printed scale body of a full-scale hull: the largest scale up to 0.25 that the stand grips, the pocket in
    the middle of the tyres' contact rectangle"""
    c = C(); Q = P - [0, 0, P[:, 2].min()]
    sc = min(S3.SCALE_MAX, S3.GRIP_MAX / max(S3.grip_widths(Q).values())); Q = Q * sc
    feet = np.vstack([c['pts'][k] for k in c['tyres']]); feet = feet[feet[:, 2] < feet[:, 2].min() + 1.0]
    E = ConvexHull(Q).equations; x = float((feet[:, 0].min() + feet[:, 0].max()) / 2 * sc)
    stack = 12 * S.COIN_T; H = Q[:, 2].max(); a = np.linspace(0, 2 * np.pi, 24, endpoint=False); R = S.POCKET_R + S3.WALL
    def fits(z1):
        Z = np.linspace(0.0, z1, 12)
        X = np.vstack([np.c_[x + R * np.cos(a), R * np.sin(a), np.full(24, z)] for z in Z])
        return (X @ E[:, :3].T + E[:, 3]).max() <= 0 and (np.array([x, 0, z1 + S3.WALL]) @ E[:, :3].T + E[:, 3]).max() <= 0
    depth = round(0.78 * H, 1)
    while depth > stack + 2 and not fits(depth):
        depth -= 0.5
    return Q, dict(name='pocket', x=x, y=0.0, z0=0.0, depth=float(depth), coins=12, spacer=round(depth - stack - 0.4, 1),
                   fits=bool(fits(depth) and depth >= stack + 2)), sc


# ---------------------------------------------------------------- the search
LIM = np.array([[-90.0, 180.0], [-10.0, 175.0], [-165.0, -15.0], [-120.0, 120.0]])   # yaw, a1, a2 - a1, g - a2 (guard_arm.ok)


def pose(u):
    yaw, a1, d2, dg = LIM[:, 0] + u * (LIM[:, 1] - LIM[:, 0]); a2 = a1 + d2
    return [float(yaw), float(a1), float(a2), float(a2 + dg)]


def _static(q):
    try:
        if not clear(q):
            return None
        r = static(q); P = r['P']; e = np.ptp(P, 0)
        return dict(q=q, share_up=r['share'].get('upright', 0.0), n_states=len(r['states']), margin=r['margin'], stall=r['stall'],
                    size=e.round(1).tolist())
    except Exception:
        return None


def _drops(a):
    q, n, seed, arm = a
    return robot_trials(q, n, seed=seed, arm=arm)


def _print_drops(a):
    q, n, seed, high, contact = a
    P = hull(q, q is not None) if q is not None else hull(C()['guard_q'], False)
    Q, pk, sc = print_body(P); L = S3.print_layout(Q, pk, high)
    return S3.drops(Q, L, contact, n=n, seed=seed)


def baselines():
    c = C(); g = c['guard_q']; y = g[0]
    return {'no arm (base only)': None, 'guard (stowed arch)': g, 'straight up': [y, 90.0, 75.0, 75.0],
            'up and forward': [y, 75.0, 20.0, -30.0], 'folded back, flat': [180.0, 5.0, -15.0, -60.0]}


def search(log2n=12):
    """every Sobol pose that clears the body and floor: its statics and 60 robot drops; the best 100 at 400; 12
    distinct finalists and the baselines at 2000. Statics can't rank these poses (every one is 77-90 mm of CoM from
    a single rest state, `check`), so drops do."""
    from scipy.stats import qmc
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    gy = C()['guard_q'][0]
    U4 = qmc.Sobol(4, scramble=True, seed=4).random_base2(log2n)
    U3 = qmc.Sobol(3, scramble=True, seed=5).random_base2(log2n - 1)
    Q = [pose(u) for u in U4] + [pose(np.r_[(gy - LIM[0, 0]) / (LIM[0, 1] - LIM[0, 0]), u]) for u in U3]
    sets = ['free'] * len(U4) + ['guard yaw'] * len(U3)
    with Pool(WORKERS) as pool:
        R = pool.map(_static, Q, chunksize=16)
        ok = []
        for r, src in zip(R, sets):
            if r: r['set'] = src; ok.append(r)
        t1 = time.time(); print(f'statics: {len(Q)} poses, {len(ok)} clear of the body and floor, {t1 - t0:.0f} s', flush=True)
        D = pool.map(_drops, [(r['q'], 60, 11, True) for r in ok], chunksize=2)
        for r, d in zip(ok, D):
            r['robot_up_60'] = d['p_upright']
        t2 = time.time(); print(f'drops: {len(ok)} poses x 60, {t2 - t1:.0f} s', flush=True)
        top = sorted(ok, key=lambda r: -r['robot_up_60'])[:100]
        D = pool.map(_drops, [(r['q'], 400, 23, True) for r in top], chunksize=1)
        for r, d in zip(top, D):
            r['robot_up_400'] = d['p_upright']
        pick = []
        for r in sorted(top, key=lambda r: -r['robot_up_400']):
            if all(np.abs(np.array(r['q']) - np.array(p['q'])).max() > 10 for p in pick):
                pick.append(r)
            if len(pick) >= 12: break
        B = baselines()
        D = pool.map(_drops, [(r['q'], 2000, 77, True) for r in pick] + [(q if q is not None else C()['guard_q'], 2000, 77, q is not None) for q in B.values()], chunksize=1)
        for r, d in zip(pick, D):
            r['robot_up_2000'] = d['p_upright']; r['robot_counts_2000'] = d['counts']
        base = {k: dict(q=q, robot_up_2000=d['p_upright'], counts=d['counts'], static=_static(q) if q is not None else None)
                for (k, q), d in zip(B.items(), D[len(pick):])}
        t3 = time.time(); print(f'top 100 x 400, finalists {len(pick)} + baselines {len(base)} x 2000, {t3 - t2:.0f} s', flush=True)
    json.dump(dict(wall_s=round(t3 - t0), n_poses=len(Q), n_clear=len(ok), poses=ok, finalists=pick, baselines=base,
                   drops=len(ok) * 60 + len(top) * 400 + (len(pick) + len(base)) * 2000),
              open(os.path.join(OUT, 'search.json'), 'w'), default=float)
    print('baselines:')
    for k, v in base.items():
        print(f"  {k:24s} robot upright {v['robot_up_2000']:.3f}  {v['counts']}")
    print('finalists:')
    for r in pick:
        print(f"  q {np.round(r['q'], 0)}  robot upright {r['robot_up_2000']:.3f}  (400: {r['robot_up_400']:.3f})  rests {r['n_states']}  set {r['set']}  {r['robot_counts_2000']}")


def check():
    """the capsule arm against the real arm meshes: rest states and margin at the guard pose and four others"""
    c = C(); GA = c['GA']; rng = np.random.default_rng(2); qs = [c['guard_q']]
    while len(qs) < 5:
        q = pose(rng.uniform(size=4))
        if clear(q): qs.append(q)
    for q in qs:
        real = GA.arm_tris(q).reshape(-1, 3) - [0, c['yc'], 0]
        Pr = np.vstack([c['body']] + [c['pts'][k] for k in c['tyres']] + [real]); Pr = Pr[ConvexHull(Pr).vertices]
        M, G, I = layout(q); Pc = hull(q)
        sr, tr = S3.static(Pr, G); sc, tc = S3.static(Pc, G)
        print(f"q {np.round(q, 0)}: margin real {S3.margin(Pr, G):6.1f} capsule {S3.margin(Pc, G):6.1f} mm; upright share real {sr.get('upright', 0):.3f} "
              f"capsule {sc.get('upright', 0):.3f}; rests real {len(tr)} capsule {len(tc)}; arm extent real {np.ptp(real, 0).round(0)} capsule {np.ptp(capsule_points(capsules(q)), 0).round(0)}")


from multiprocessing import Pool

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'search'
    if cmd == 'cache': cache()
    elif cmd == 'check': check()
    else: search()
