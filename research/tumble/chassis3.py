"""EXPLORATORY (2026-10-25): a chassis search for steps. The Trainer's own body (pose3's cache of chassis-v2, the wheel
modules and the arm's base taken off), with its wheel layout and weight as the knobs, scored on driving down a step
and landing on its wheels, and on climbing one.

    python research/tumble/chassis3.py check    # the baseline against wheels3's Trainer, cell by cell
    python research/tumble/chassis3.py search   # Sobol screen, cross-entropy, finalists -> research/results/chassis3/*.json

Knobs (mm): R wheel radius; xf, xr the front and rear axles' X; clr the belly's height over the ground; dxp, dzp the
battery packs (600 g) moved forward and up. Same motor (wheels3.MOTOR: 1.0 N m stall, 330 rpm at the wheel*), so a
bigger wheel is faster and pushes less. Tyre mass scales with R, rim with R^2. Frame: X forward, Z up, the ground
at Z 0 when upright. Axles past the hull wall's straight run (X -117..115) or outside its height band would need a
bracket; `notes` says so, it isn't a constraint.

Driving: the encoders hold the set speed (wheels3.KV); the wheels coast 1 s after landing. A run that never gets down
the step is 'stuck'. * = datasheet guess.
"""
import os, sys, json, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'results', 'chassis3')
sys.path.insert(0, HERE)
import pose3 as P3
import wheels3 as W3
import tumble as T

KEYS = ['R', 'xf', 'xr', 'clr', 'dxp', 'dzp']
LO = np.array([45.0, 40.0, -200.0, 15.0, -80.0, -8.0])
HI = np.array([95.0, 200.0, -40.0, 90.0, 80.0, 15.0])
BASE = dict(R=55.0, xf=91.0, xr=-93.0, clr=32.4, dxp=0.0, dzp=0.0)
Y_W, TW, G0 = 131.0, 46.0, -25.0                                      # wheel centre-plane offset, tyre width, the cache's ground
MOD = ('tire_', 'rim_', 'pod_', 'motor_')
CELLS = [(h, v, b) for h in (100, 200, 300, 400) for v in (0.3, 0.6, 1.0, 1.4) for b in (False, True)]
TICK = 5                                                               # ms per control tick
CONTACT = dict(tc=0.002, dr=0.35, dt=0.0002)                           # hard floor, the ball's bounce; 0.2 ms agreed with 0.1 within ~0.1 on 8 cells x 40
# runs (C14 says check: the hard floor wasn't converged at 0.5 ms).
# The first runs (2026-10-25) used the soft floor (0.02 s, damping 0.2, 1 ms): at a step's edge it sank and then threw
# the robot 100-300 mm up (a 40-60 mm climb, traced), so every step result before this line is suspect.
WORKERS = 30
_B = None


def base():
    """the Trainer's body without its wheel modules: hull points and mass items, ground frame"""
    global _B
    if _B is None:
        c = P3.C(); keep = [k for k in c['pts'] if not k.startswith(MOD + ('armbase_', 'rest_peg'))]
        pts = np.vstack([c['pts'][k] for k in keep]); pts = pts[ConvexHull(pts).vertices] - [0, 0, G0]
        items = [(n, m, np.asarray(p, float) - [0, 0, G0]) for n, m, p in c['items'] if not n.startswith(MOD)]
        box = {k: v for k, v in c['box'].items()}
        _B = dict(pts=pts, items=items, box=box, clr0=float(pts[:, 2].min()))
    return _B


def design(p):
    """geometry and masses of one chassis; ok False if the tyres overlap"""
    b = base(); dz = p['clr'] - b['clr0']; R = p['R']
    pts = b['pts'] + [0, 0, dz]
    items = []
    for n, m, q in b['items']:
        q = q + [0, 0, dz]
        if n.startswith('pack'):
            q = q + [p['dxp'], 0, p['dzp']]
        items.append((n, m, q))
    m_t, m_r = 75.7 * R / 55.0, 79.8 * (R / 55.0) ** 2
    I_w = (m_t * (0.91 * R) ** 2 + m_r * (0.55 * R) ** 2) * 1e-9         # kg m2 about the axle (the Trainer's: 2.6e-4)
    axles = {'FL': (p['xf'], Y_W), 'FR': (p['xf'], -Y_W), 'RL': (p['xr'], Y_W), 'RR': (p['xr'], -Y_W)}
    for k, (x, y) in axles.items():                                    # motor + pod ride on the body at each axle
        items.append(('motor_' + k, 205.0 + 34.6, np.array([x, np.sign(y) * 100.0, R])))
    ok = p['xf'] - p['xr'] >= 2 * R + 15
    notes = []
    if p['xf'] > 115 or p['xr'] < -117: notes.append('axle past the wall: bracket')
    if not (p['clr'] - 5 <= R <= p['clr'] + 55): notes.append('axle outside the wall band: drop bracket')
    return dict(pts=pts, items=items, box=b['box'], R=R, m_w=(m_t + m_r), I_w=I_w, axles=axles, ok=bool(ok), notes=notes,
                length=float(max(pts[:, 0].max(), p['xf'] + R) - min(pts[:, 0].min(), p['xr'] - R)),
                height=float(max(pts[:, 2].max(), 2 * R)), mass=float(sum(m for _, m, _ in items) + 4 * (m_t + m_r)))


def xml(D, step=None, up=False):
    """MJCF: robot (free), body hull, four wheels on armatured hinges (wheels3's rotor model). `step` (mm): a step at
    X 0, down from a platform (X < 0) or, `up`, up onto one (X > 0)"""
    s = 1e-3; M = sum(m for _, m, _ in D['items']); G = sum(m * q for _, m, q in D['items']) / M; I = np.zeros((3, 3))
    for n, m, q in D['items']:
        d = q - G; I += m * (d @ d * np.eye(3) - np.outer(d, d))
        h = D['box'].get(n)
        if h is not None:
            a, bb, cc = (2 * h) ** 2; I += m / 12 * np.diag([bb + cc, a + cc, a + bb])
    Isi = I * 1e-9; full = ' '.join('%.8g' % v for v in (Isi[0, 0], Isi[1, 1], Isi[2, 2], Isi[0, 1], Isi[0, 2], Isi[1, 2]))
    mo = W3.MOTOR; Ie = D['I_w'] + mo['N'] * mo['Ir']; arm = (mo['N'] ** 2 - mo['N']) * mo['Ir']; R = D['R']
    mk = D['m_w'] * 1e-3; It = max(mk * (3 * (R * s) ** 2 + (TW * s) ** 2) / 12, 0.5 * Ie * 1.001)
    wb = ''.join(f'<body name="w{k}" pos="{x * s:.4f} {y * s:.4f} {R * s:.4f}"><joint name="j{k}" type="hinge" axis="0 1 0" armature="{arm:.6g}"/>'
                 f'<inertial pos="0 0 0" mass="{mk:.4f}" diaginertia="{It:.6g} {Ie:.6g} {It:.6g}"/>'
                 f'<geom type="cylinder" size="{R * s:.4f} {TW / 2 * s:.4f}" euler="90 0 0" friction="0.9 0.01 0.001"/></body>' for k, (x, y) in D['axles'].items())
    floor = '<geom type="plane" size="6 6 0.1" friction="0.6 0.005 0.0005"/>'
    if step:
        cx = 2.0 if up else -2.0
        floor += f'<geom type="box" size="2 2 {step / 2 * s:.4f}" pos="{cx} 0 {step / 2 * s:.4f}" friction="0.6 0.005 0.0005"/>'
    verts = ' '.join('%.5f' % v for v in (D['pts'] * s).ravel())
    return f"""<mujoco><option timestep="{CONTACT['dt']}"/><default><geom solref="{CONTACT['tc']} {CONTACT['dr']}"/></default>
      <asset><mesh name="body" vertex="{verts}"/></asset><worldbody>{floor}
      <body name="robot" pos="0 0 0.5"><freejoint/>
        <inertial pos="{G[0] * s:.5f} {G[1] * s:.5f} {G[2] * s:.5f}" mass="{M * 1e-3:.4f}" fullinertia="{full}"/>
        <geom type="mesh" mesh="body" friction="0.4 0.005 0.0005"/>{wb}</body></worldbody></mujoco>"""


class Sim:
    def __init__(self, D, step=None, up=False):
        import mujoco
        self.mj = mujoco; self.D = D; self.m = mujoco.MjModel.from_xml_string(xml(D, step, up)); self.d = mujoco.MjData(self.m)
        self.jw = [self.m.joint('j' + k).dofadr[0] for k in D['axles']]; self.rid = self.m.body('robot').id
        self.w0 = W3.MOTOR['w0']; self.stall = W3.MOTOR['stall']

    def drive(self, x0, z0, yaw, v, back, hold=1.0, t_max=5.0, fall=None, rise=None):
        """drive at v (m/s) toward +X from X x0; returns 'stuck', 'climbed', or the rest class after getting down"""
        mj, m, d = self.mj, self.m, self.d; R = self.D['R'] * 1e-3
        mj.mj_resetData(m, d); q = np.array([np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)])
        d.qpos[:3] = (x0, 0, z0); d.qpos[3:7] = q; d.qvel[0] = v
        sgn = -1.0 if back else 1.0; d.qvel[self.jw] = sgn * v / R; mj.mj_forward(m, d)
        u0 = sgn * min(v / (self.w0 * R), 1.0); zc0 = d.xipos[self.rid][2]; landed = False; t_land = None; still = 0
        for k in range(int(t_max * 1000 / TICK)):
            t = k * TICK / 1000
            if landed and t - t_land > hold:
                u = None
            else:
                u = u0 + W3.KV * (u0 * self.w0 - d.qvel[self.jw].mean()) / self.w0
            d.qfrc_applied[:] = 0.0
            if u is not None:
                d.qfrc_applied[self.jw] = self.stall * (np.clip(u, -1, 1) - d.qvel[self.jw] / self.w0)
            mj.mj_step(m, d, nstep=int(round(TICK * 1e-3 / m.opt.timestep)))
            zc = d.xipos[self.rid][2]
            if rise is not None:
                if zc - zc0 > rise and d.xipos[self.rid][0] > 0.12:
                    return 'climbed' if T.classify(d.xmat[self.rid].reshape(3, 3)) == 'upright' else 'climbed, ' + T.classify(d.xmat[self.rid].reshape(3, 3))
                continue
            if not landed and zc0 - zc > fall and d.ncon > 0:
                landed, t_land = True, t
            if landed and k % 4 == 0:
                if np.abs(d.qvel[:6]).max() < 0.02:
                    still += 1
                    if still >= 6: break
                else:
                    still = 0
        if rise is not None:
            return 'stuck'
        return T.classify(d.xmat[self.rid].reshape(3, 3)) if landed else 'stuck'


def lead(D, back):
    """how far the leading end (body or tyre, whichever reaches further) sits ahead of the origin, mm (2026-10-25:
    the body's alone put big wheels inside the step at the start)"""
    xs = [x for x, _ in D['axles'].values()]
    return max(abs(D['pts'][:, 0].min()), abs(min(xs)) + D['R']) if back else max(D['pts'][:, 0].max(), max(xs) + D['R'])


def descend(args):
    """n runs per cell over `cells` (h mm, v m/s, reverse): {cell: {outcome: count}}"""
    p, cells, n, seed = args
    D = design(p); rng = np.random.default_rng(seed); out = {}
    if not D['ok']:
        return None
    sims = {}
    for h, v, back in cells:
        sim = sims.get(h) or sims.setdefault(h, Sim(D, step=h)); c = {}
        for _ in range(n):
            yaw = np.radians(rng.uniform(-15, 15)) + (np.pi if back else 0.0)
            x0 = -lead(D, back) * 1e-3 - rng.uniform(0.05, 0.15)                     # the leading end starts 5-15 cm short of the edge
            r = sim.drive(x0, h * 1e-3 + 0.0005, yaw, v * rng.uniform(0.9, 1.1), back, fall=0.4 * h * 1e-3)
            c[r] = c.get(r, 0) + 1
        out[(h, v, back)] = c
    return out


def climb(args):
    """n runs per height of driving up a step at v, forwards and in reverse: {(h, reverse): {outcome: count}}"""
    p, heights, v, n, seed = args
    D = design(p); rng = np.random.default_rng(seed); out = {}
    if not D['ok']:
        return None
    for h in heights:
        sim = Sim(D, step=h, up=True)
        for back in (False, True):
            c = {}
            for _ in range(n):
                yaw = np.radians(rng.uniform(-10, 10)) + (np.pi if back else 0.0)
                x0 = -lead(D, back) * 1e-3 - 0.08
                r = sim.drive(x0, 0.0005, yaw, v, back, t_max=4.0, rise=0.6 * h * 1e-3)
                c[r] = c.get(r, 0) + 1
            out[(h, back)] = c
    return out


CLIMB_H = (40, 60, 80, 100, 120)


def both(args):
    """down (n per cell) and up (m per height and direction) for one design under a length cap: (score, down, up)"""
    p, n, m, seed, cap = args
    D = design(p)
    if not D['ok'] or D['length'] > cap:
        return -1.0, None, None
    dn = descend((p, CELLS, n, seed)); up = climb((p, CLIMB_H, 0.5, m, seed + 1))
    s_up = float(np.mean([c.get('climbed', 0) / sum(c.values()) for c in up.values()]))
    return 0.5 * score(dn) + 0.5 * s_up, dn, up


def score(res):
    """the share of runs that got down and landed on its wheels, over the cells"""
    if res is None:
        return -1.0
    return float(np.mean([c.get('upright', 0) / sum(c.values()) for c in res.values()]))


def as_p(x):
    return {k: float(v) for k, v in zip(KEYS, x)}


def check():
    """the baseline chassis against wheels3's Trainer on a few cells (same seeds can't match: the start differs)"""
    cells = [(200, 0.6, False), (200, 1.4, False), (300, 0.6, True), (300, 1.4, True)]
    with Pool(8) as pool:
        A = pool.map(descend, [(BASE, [c], 40, 3 + i) for i, c in enumerate(cells)])
        B = pool.map(W3.ledge_trials, [(h, v, None, 40, 3 + i, W3.MOTOR, b) for i, (h, v, b) in enumerate(cells)])
    for c, a, b in zip(cells, A, B):
        a = a[c]; print(f'{c}: chassis3 upright {a.get("upright", 0) / 40:.2f} stuck {a.get("stuck", 0) / 40:.2f} | wheels3 upright {b["upright"] / 40:.2f} stuck {b.get("stuck", 0) / 40:.2f}')
    D = design(BASE); print('baseline mass %.0f g (Trainer 3221), length %.0f, height %.0f, notes %s' % (D['mass'], D['length'], D['height'], D['notes']))


def search():
    from scipy.stats import qmc
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    X = qmc.scale(qmc.Sobol(len(KEYS), scramble=True, seed=7).random_base2(8), LO, HI)
    with Pool(WORKERS) as pool:
        R0 = pool.map(descend, [(as_p(x), CELLS, 2, 100 + i) for i, x in enumerate(X)], chunksize=1)
        S0 = [score(r) for r in R0]; t1 = time.time()
        print(f'screen: {len(X)} designs x {2 * len(CELLS)} runs, {sum(s >= 0 for s in S0)} valid, best {max(S0):.3f}, {t1 - t0:.0f} s', flush=True)
        rng = np.random.default_rng(3); order = np.argsort(S0)[::-1]; E = X[order[:10]]
        mu, sd = E.mean(0), np.maximum(E.std(0), 0.04 * (HI - LO)); best = [(S0[i], X[i]) for i in order[:10]]; hist = []
        for g in range(8):
            P = np.clip(mu + sd * rng.normal(size=(30, len(KEYS))), LO, HI)
            R = pool.map(descend, [(as_p(x), CELLS, 4, 500 + 31 * g + i) for i, x in enumerate(P)], chunksize=1)
            S = [score(r) for r in R]
            best = sorted(best + list(zip(S, P)), key=lambda t: -t[0])[:10]
            Eg = np.array([b[1] for b in best]); mu = 0.6 * Eg.mean(0) + 0.4 * mu; sd = np.maximum(0.6 * Eg.std(0) + 0.4 * sd * 0.8, 0.01 * (HI - LO))
            hist.append(dict(gen=g, best=max(S), mean=float(np.mean([s for s in S if s >= 0]))))
            print(f'gen {g}: best {max(S):.3f}, elite {np.mean([b[0] for b in best]):.3f}, mu {np.round(mu, 0)}', flush=True)
        t2 = time.time()
        fin, seen = [], []
        for s, x in best:
            if all(np.abs((x - y) / (HI - LO)).max() > 0.05 for y in seen):
                seen.append(x); fin.append(x)
            if len(fin) >= 5: break
        cand = [as_p(x) for x in fin] + [BASE]
        F = pool.map(descend, [(p, CELLS, 20, 9000 + j) for j, p in enumerate(cand)], chunksize=1)
        C = pool.map(climb, [(p, (40, 60, 80, 100, 120), 0.5, 10, 9500 + j) for j, p in enumerate(cand)], chunksize=1)
        t3 = time.time(); print(f'finalists: {len(cand)} x {20 * len(CELLS)} runs + climbs, {t3 - t2:.0f} s', flush=True)
    out = dict(wall_s=round(t3 - t0), screen=[dict(p=as_p(x), score=s) for x, s in zip(X, S0)], history=hist,
               finalists=[dict(p=p, name='baseline (Trainer)' if p is BASE else f'F{j + 1}', design={k: v for k, v in design(p).items() if k in ('length', 'height', 'mass', 'notes', 'ok')},
                               score=score(f), cells={f'{h}|{v}|{int(b)}': c for (h, v, b), c in f.items()},
                               climb={f'{h}|{int(b)}': c for (h, b), c in cl.items()}) for j, (p, f, cl) in enumerate(zip(cand, F, C))])
    json.dump(out, open(os.path.join(OUT, 'search.json'), 'w'), indent=1, default=float)
    for f in out['finalists']:
        cl = f['climb']; climbs = {h: sum(cl[f'{h}|{b}'].get('climbed', 0) for b in (0, 1)) / 20 for h in (40, 60, 80, 100, 120)}
        print(f"{f['name']:20s} steps down {f['score']:.3f}  climbs {climbs}  {np.round([f['p'][k] for k in KEYS], 0)}  {f['design']}")


CAPS = (380.0, 450.0, 600.0)


def frontier(gens=5, pop=26):
    """per length cap: Sobol screen and cross-entropy on going down and climbing up together, then the best at
    20 runs a cell and 10 a climb, the Trainer alongside"""
    from scipy.stats import qmc
    os.makedirs(OUT, exist_ok=True); t0 = time.time(); res = {}
    X0 = qmc.scale(qmc.Sobol(len(KEYS), scramble=True, seed=11).random_base2(7), LO, HI)
    with Pool(WORKERS) as pool:
        for cap in CAPS:
            S0 = [r[0] for r in pool.map(both, [(as_p(x), 1, 1, 200 + i, cap) for i, x in enumerate(X0)], chunksize=1)]
            order = np.argsort(S0)[::-1]; best = [(S0[i], X0[i]) for i in order[:8] if S0[i] >= 0]
            E = np.array([b[1] for b in best]); mu, sd = E.mean(0), np.maximum(E.std(0), 0.05 * (HI - LO)); rng = np.random.default_rng(int(cap))
            for g in range(gens):
                P = np.clip(mu + sd * rng.normal(size=(pop, len(KEYS))), LO, HI)
                S = [r[0] for r in pool.map(both, [(as_p(x), 2, 2, 700 + 37 * g + i, cap) for i, x in enumerate(P)], chunksize=1)]
                best = sorted(best + [(s_, x) for s_, x in zip(S, P) if s_ >= 0], key=lambda t: -t[0])[:8]
                Eg = np.array([b[1] for b in best]); mu = 0.6 * Eg.mean(0) + 0.4 * mu; sd = np.maximum(0.6 * Eg.std(0) + 0.4 * sd * 0.8, 0.01 * (HI - LO))
                print(f'cap {cap:.0f}: gen {g} best {max(S):.3f} elite {np.mean([b[0] for b in best]):.3f} mu {np.round(mu, 0)}', flush=True)
            top = [as_p(b[1]) for b in best[:3]]
            R = pool.map(both, [(p, 20, 10, 9100 + j, 1e9) for j, p in enumerate(top)], chunksize=1)
            j = int(np.argmax([r[0] for r in R])); s_, dn, up = R[j]
            res[cap] = dict(p=top[j], score=s_, down=score(dn), up=float(np.mean([c.get('climbed', 0) / sum(c.values()) for c in up.values()])),
                            cells={f'{h}|{v}|{int(b)}': c for (h, v, b), c in dn.items()}, climb={f'{h}|{int(b)}': c for (h, b), c in up.items()},
                            design={k: v for k, v in design(top[j]).items() if k in ('length', 'height', 'mass', 'notes')})
            print(f'cap {cap:.0f}: {np.round([top[j][k] for k in KEYS], 0)} down {res[cap]["down"]:.3f} up {res[cap]["up"]:.3f} {res[cap]["design"]}  {time.time() - t0:.0f} s', flush=True)
        s_, dn, up = pool.map(both, [(BASE, 20, 10, 9100, 1e9)])[0]
        res['baseline'] = dict(p=BASE, score=s_, down=score(dn), up=float(np.mean([c.get('climbed', 0) / sum(c.values()) for c in up.values()])),
                               cells={f'{h}|{v}|{int(b)}': c for (h, v, b), c in dn.items()}, climb={f'{h}|{int(b)}': c for (h, b), c in up.items()},
                               design={k: v for k, v in design(BASE).items() if k in ('length', 'height', 'mass', 'notes')})
        print(f'baseline: down {res["baseline"]["down"]:.3f} up {res["baseline"]["up"]:.3f}', flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), caps=list(CAPS), results={str(k): v for k, v in res.items()}),
              open(os.path.join(OUT, 'frontier.json'), 'w'), indent=1, default=float)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'search'
    {'check': check, 'frontier': frontier}.get(cmd, search)()
