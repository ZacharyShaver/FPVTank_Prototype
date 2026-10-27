"""The iteration-1 gauges (gauges/README.md): upright after a fall, step up, turn-around space. Each reads one number
off a design under every physics in the band; the reading is the worst of them.

    python gauges/gauges.py             # the roster and the controls -> gauges/out/scorecard.json
    python gauges/gauges.py --quick     # a smoke run: 40 falls, 6 tries a step, no timestep check
    python gauges/gauges.py --cached    # reuse gauges/out/roster.pkl instead of rebuilding the designs (~50 s)
    python gauges/gauges.py port        # this step-up sim against chassis3's own, on chassis3's Trainer stand-in

Drive loop: chassis3.Sim's (the encoders hold each side's set speed, wheels3's motor); contact: chassis3's hard floor.
"""
import os, sys, json, time, pickle, math
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
sys.path.insert(0, config.TUMBLE)
import robots as RB

BAND = (0.65, 1.0, 1.5)                  # friction scale; contact and bounce fixed (robots.CONTACT)
TICK = 5                                 # ms per control tick
DROP_MM, SPIN, N_DROP, CHUNK = 300.0, 3.0, 200, 20
HEIGHTS = tuple(range(10, 160, 10))      # step up, mm
N_TRY, V_CLIMB, T_CLIMB = 20, 0.5, 4.0
TURN_U, T_TURN = 0.6, 6.0                # spin at 60 % of no-load speed; 180 degrees within 6 s
LIMB_W, T_RIGHT = 6.0, 10.0              # the tail's servos turn at most 6 rad/s (MG996R class*); G1 gives a tail 10 s to right it
STALL_N, STALL_MM, NOSE_UP = 60, 15.0, 12.0   # the step reflex: under 15 mm in 60 ticks (0.3 s) is stalled; nose up past 12 degrees, push
WORKERS = 30
SP = None


def classify(R):
    import tumble as T
    return T.classify(R)


class Sim:
    def __init__(self, sp, mu=1.0, step=None, dt=None, edge='round'):
        import mujoco
        self.mj = mujoco; self.sp = sp
        self.m = mujoco.MjModel.from_xml_string(RB.xml(sp, mu, step, dt, edge)); self.d = mujoco.MjData(self.m)
        self.jw = np.array([self.m.joint(f'j{i}').dofadr[0] for i in range(len(sp['wheels']))])
        self.left = np.array([y > 0 for _, y in sp['wheels']]); self.rid = self.m.body('robot').id
        self.E = RB.extremes(sp) * 1e-3
        self.w0, self.stall, self.kv = sp['motor']['w0'], sp['motor']['stall'], sp['kv']
        self.nsub = int(round(TICK * 1e-3 / self.m.opt.timestep))
        self.limb = sp.get('limb')
        if self.limb:                                                     # the tail: joint addresses, servo goals (radians)
            self.lq = [self.m.joint(n).qposadr[0] for n in ('ly', 'lp')]
            self.lo = np.radians([RB.LIMB_YAW[0], RB.LIMB_PITCH[0]]); self.hi = np.radians([RB.LIMB_YAW[1], RB.LIMB_PITCH[1]])
            self.stow = np.radians([0.0, self.limb['th_stow']])

    def place(self, quat, z_low, x=0.0):
        """reset, turned by quat, its lowest point z_low (m) over the floor; a tail starts stowed"""
        mj, m, d = self.mj, self.m, self.d
        mj.mj_resetData(m, d); R9 = np.zeros(9); mj.mju_quat2Mat(R9, np.asarray(quat, float)); R = R9.reshape(3, 3)
        d.qpos[:3] = (x, 0.0, z_low - (self.E @ R.T)[:, 2].min()); d.qpos[3:7] = quat
        if self.limb:
            d.qpos[self.lq] = self.stow; d.ctrl[:] = self.stow; self.goal = self.stow.copy()
        mj.mj_forward(m, d)

    def limb_goal(self, yaw, pitch):
        """where the tail's servos head (radians, clipped to their ranges); they get there at LIMB_W"""
        self.goal = np.clip([yaw, pitch], self.lo, self.hi)

    def limb_pose(self):
        return self.d.qpos[self.lq].copy()

    def drive(self, uL, uR):
        """one tick with each side's speed loop holding u (a fraction of no-load speed; None: unpowered), the tail's
        servos stepping toward their goals"""
        d, w = self.d, self.d.qvel[self.jw]; tau = np.zeros(len(self.jw))
        if self.limb:
            dc = np.clip(self.goal - d.ctrl, -LIMB_W * TICK * 1e-3, LIMB_W * TICK * 1e-3); d.ctrl[:] = d.ctrl + dc
        for side, u0 in ((self.left, uL), (~self.left, uR)):
            if u0 is None or not side.any():
                continue
            u = u0 + self.kv * (u0 * self.w0 - w[side].mean()) / self.w0
            tau[side] = self.stall * (np.clip(u, -1, 1) - w[side] / self.w0)
        d.qfrc_applied[:] = 0.0; d.qfrc_applied[self.jw] = tau
        self.mj.mj_step(self.m, d, nstep=self.nsub)

    def rot(self):
        return self.d.xmat[self.rid].reshape(3, 3)


def yaw_quat(yaw):
    return np.array([math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)])


# ---------- G1 upright after a fall ----------
def falls(sim, n, rng, bar=None):
    """n falls from DROP_MM, uniformly random orientation and spin, wheels unpowered: rest-state counts. With bar, it
    stops once the upright share can no longer reach bar (the screen's cut; the counts then sum to fewer than n)"""
    mj, m, d = sim.mj, sim.m, sim.d; c = {}; nst = int(round(0.05 / m.opt.timestep))
    for _ in range(n):
        if bar is not None and (n - (sum(c.values()) - c.get('upright', 0))) / n < bar:
            break
        q = rng.normal(size=4); q /= np.linalg.norm(q)
        sim.place(q, DROP_MM * 1e-3); d.qvel[3:6] = rng.uniform(-1, 1, 3) * SPIN
        still = 0
        for _ in range(160):                                              # 8 s at most
            mj.mj_step(m, d, nstep=nst)
            if np.abs(d.qvel[:6]).max() < 0.02:
                still += 1
                if still >= 6: break
            else:
                still = 0
        if sim.limb and classify(sim.rot()) != 'upright':
            right(sim)
        k = classify(sim.rot()); c[k] = c.get(k, 0) + 1
    return c


def right(sim):
    """the tail's righting reflexes (scripted; a learned policy would replace them), tried in turn for T_RIGHT s:
    turn the tail's plane toward the ground (or out to a side), swing the link through the ground's direction and
    70 degrees past it, pushing as hard as its servo allows, then stow it and let the body settle"""
    d = sim.d; t = [0.0]
    def hold(goal, T):
        sim.limb_goal(*goal)
        for _ in range(int(T * 1000 / TICK)):
            sim.drive(None, None); t[0] += TICK / 1000
    def settle(Tmax):
        still = 0
        for _ in range(int(Tmax * 1000 / TICK)):
            sim.drive(None, None); t[0] += TICK / 1000
            still = still + 1 if np.abs(d.qvel[:6]).max() < 0.02 else 0
            if still * TICK >= 150: return
    k = 0                                                                 # an attempt (2.15 s of moves, 1 s to settle) starts only if it
    while t[0] + 3.15 <= T_RIGHT and classify(sim.rot()) != 'upright':   # can end inside T_RIGHT (2026-10-26: one ran to 10.5 s)
        g = sim.rot().T @ np.array([0.0, 0.0, -1.0])                     # world down, in the body frame
        plan = ([(math.atan2(-g[1], -g[0]), 1), (math.atan2(-g[1], -g[0]), -1)] if math.hypot(g[0], g[1]) > 0.3 else []) +                [(math.pi / 2, 1), (-math.pi / 2, 1), (math.pi / 2, -1), (-math.pi / 2, -1), (0.0, 1), (math.pi, 1)]
        yaw, sg = plan[k % len(plan)]; k += 1
        tg = math.atan2(g[2], -math.cos(yaw) * g[0] - math.sin(yaw) * g[1])   # the ground's direction in that plane
        hold((yaw, sim.limb_pose()[1]), 0.4)
        hold((yaw, tg - sg * math.radians(100)), 0.45)
        hold((yaw, tg + sg * math.radians(70)), 0.7)
        hold((0.0, sim.stow[1]), 0.6)
        settle(1.0)


# ---------- G2 step up ----------
def lead(sp, back):
    E = RB.extremes(sp); return -E[:, 0].min() if back else E[:, 0].max()


def climb_try(sim, h, back, rng):
    """one try at a step of h mm, square on +-10 degrees, 0.5 m/s: True when on top and on its wheels. A tail's
    reflex (2026-10-27): stalled is under STALL_MM of forward travel in the last 0.3 s. Stalled nose up (past NOSE_UP,
    riding the face), it pushes down behind for 0.9 s and stows; stalled level (its nose caught on a lip about belly
    high, where a push only tips the nose down into it), it kicks for 0.3 s to free the nose, and looks again. The
    first reflex (a push whenever the CoM's speed stayed under 0.05 m/s for 0.15 s) left gaps in the ladder: at
    40-50 mm the robot hung without tripping it, at 60-80 mm its push wedged the nose."""
    sp, d = sim.sp, sim.d; R = sp['R'] * 1e-3; sgn = -1.0 if back else 1.0
    yaw = math.radians(rng.uniform(-10, 10)) + (math.pi if back else 0.0)
    sim.place(yaw_quat(yaw), 0.0005, x=-lead(sp, back) * 1e-3 - 0.08)
    d.qvel[0] = V_CLIMB; d.qvel[sim.jw] = sgn * V_CLIMB / R; sim.mj.mj_forward(sim.m, d)
    u0 = sgn * min(V_CLIMB / (sim.w0 * R), 1.0); z0 = d.xipos[sim.rid][2]
    move, t_move, xs = None, 0.0, []
    for k in range(int(T_CLIMB * 1000 / TICK)):
        if sim.limb and not back:                                         # a tail at the rear acts when the robot stalls
            t = k * TICK / 1000; xs.append(d.xipos[sim.rid][0])
            if move is None and t > 0.45 and len(xs) > STALL_N and xs[-1] - xs[-1 - STALL_N] < STALL_MM * 1e-3:
                Rm = sim.rot(); up = math.degrees(math.atan2(Rm[2, 0], Rm[2, 2]))   # nose up, degrees
                move, t_move = ('push' if up > NOSE_UP else 'kick'), t
            if move is not None:
                tp = t - t_move; hold, end = (0.9, 1.6) if move == 'push' else (0.3, 0.6)
                sim.limb_goal(0.0, math.radians(sp['limb']['th_push']) if tp < hold else sim.stow[1])
                if tp >= end:
                    move, xs = None, xs[-1:]
        sim.drive(u0, u0)
        if d.xipos[sim.rid][2] - z0 > 0.6 * h * 1e-3 and d.xipos[sim.rid][0] > 0.12:
            return classify(sim.rot()) == 'upright'
    return False


def ladder(res, n):
    """the tallest height passed in the better direction (>= 0.9 of tries) with every lower one passing"""
    need = math.ceil(0.9 * n); top = 0
    for h in HEIGHTS:
        if max(res.get((h, b), 0) for b in (False, True)) >= need:
            top = h
        else:
            break
    return top


# ---------- G3 turn-around space ----------
def turn(sim, sign):
    """spin in place, left side back and right forward (sign +1, turning left) at TURN_U: the swept circle's
    diameter (mm) and the time to 180 degrees, or None when it doesn't get there in T_TURN"""
    d = sim.d; sim.place(yaw_quat(0.0), 0.0005)
    wc = np.mean([[x, y, 0.0] for x, y in sim.sp['wheels']], 0) * 1e-3
    c0 = (d.xpos[sim.rid] + sim.rot() @ wc)[:2]; turned, prev, rmax = 0.0, 0.0, 0.0
    for k in range(int(T_TURN * 1000 / TICK)):
        sim.drive(-sign * TURN_U, sign * TURN_U)
        R = sim.rot(); P = d.xpos[sim.rid] + sim.E @ R.T
        rmax = max(rmax, float(np.linalg.norm(P[:, :2] - c0, axis=1).max()))
        a = math.atan2(R[1, 0], R[0, 0]); da = (a - prev + math.pi) % (2 * math.pi) - math.pi; turned += da; prev = a
        if abs(turned) >= math.pi:
            return 2e3 * rmax, (k + 1) * TICK / 1000
    return None, None


# ---------- jobs ----------
def _init(specs):
    global SP
    SP = specs


def job(a):
    kind, i, mu, arg, seed, dt = a
    sp = SP[i]; rng = np.random.default_rng(seed)
    if kind == 'fall':
        return a, falls(Sim(sp, mu, dt=dt), arg, rng)
    if kind == 'climb':
        h, back, n = arg; sim = Sim(sp, mu, step=h, dt=dt)
        return a, sum(climb_try(sim, h, back, rng) for _ in range(n))
    if kind == 'turn':
        return a, turn(Sim(sp, mu, dt=dt), arg)


def jobs_for(i, n_drop, n_try, band=BAND, dt=None, seed=0):
    J = []
    for j, mu in enumerate(band):
        s = seed + 1000 * i + 100 * j
        J += [('fall', i, mu, CHUNK, s + k, dt) for k in range(n_drop // CHUNK)]
        J += [('climb', i, mu, (h, b, n_try), s + 50 + h + int(b), dt) for h in HEIGHTS for b in (False, True)]
        J += [('turn', i, mu, sg, 0, dt) for sg in (1, -1)]
    return J


def collect(R, i, n_try, band=BAND, dt=None):
    """one design's readings by physics and their worst"""
    out = {}
    for mu in band:
        fc, cl, tn = {}, {}, []
        for (kind, k, m, arg, _, d_), r in R:
            if k != i or m != mu or d_ != dt:
                continue
            if kind == 'fall':
                for s, c in r.items(): fc[s] = fc.get(s, 0) + c
            elif kind == 'climb':
                cl[(arg[0], arg[1])] = r
            else:
                tn.append(r)
        n = sum(fc.values()); up = fc.get('upright', 0)
        spin = [t for t in tn if t[0] is not None]
        out[mu] = dict(upright=up / n, falls=fc, n=n, ci=wilson(up, n), climb=ladder(cl, n_try),
                       climb_tries={f'{h}|{int(b)}': v for (h, b), v in sorted(cl.items())},
                       turn=max(t[0] for t in tn) if len(spin) == len(tn) else None,
                       turn_s=max(t[1] for t in tn) if len(spin) == len(tn) else None)
    worst = dict(upright=min(out[m]['upright'] for m in band), climb=min(out[m]['climb'] for m in band),
                 turn=None if any(out[m]['turn'] is None for m in band) else max(out[m]['turn'] for m in band))
    return dict(by_mu={str(m): v for m, v in out.items()}, worst=worst)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 1.0)
    p = k / n; c = (p + z * z / (2 * n)) / (1 + z * z / n); h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(c - h, 4), round(c + h, 4))


def roster(cached):
    path = os.path.join(config.GAUGES_OUT, 'roster.pkl')
    if cached and os.path.isfile(path):
        return pickle.load(open(path, 'rb'))
    t = RB.trainer(); main = [RB.box(t), t, RB.step_layout(), RB.six_wheel(), RB.e4()]
    controls = {'box_R35': RB.box(t, R=35.0, name='Box, 70 mm wheels'), 'box_long': RB.box(t, stretch=1.5, name='Box, 1.5x long'),
                'e4_roof': RB.e4(roof_g=1000.0, name='E4, 1 kg on the roof')}
    os.makedirs(config.GAUGES_OUT, exist_ok=True); pickle.dump((main, controls), open(path, 'wb'))
    return main, controls


def run(quick=False, cached=False):
    t0 = time.time(); main, controls = roster(cached)
    n_drop, n_try = (40, 6) if quick else (N_DROP, N_TRY)
    specs = main + list(controls.values()); ix = {sp['name']: i for i, sp in enumerate(specs)}
    J = [j for i in range(len(specs)) for j in jobs_for(i, n_drop, n_try)]
    if not quick:                                                         # the timestep check: the box at 0.1 ms, x1 friction
        J += jobs_for(0, n_drop, n_try, band=(1.0,), dt=0.0001, seed=77)
    J.sort(key=lambda a: a[0] != 'climb')                                # the long jobs first
    with Pool(WORKERS, initializer=_init, initargs=(specs,)) as pool:
        R = pool.map(job, J, chunksize=1)
    res = {sp['name']: collect(R, i, n_try) for i, sp in enumerate(specs)}
    w = lambda name: res[name]['worst']
    ctl = [dict(gauge='upright', claim='E4 weeble reads at least 0.2 above the box', a=w('E4 weeble')['upright'], b=w('Box')['upright'],
                ok=w('E4 weeble')['upright'] >= w('Box')['upright'] + 0.2),
           dict(gauge='upright', claim='E4 with 1 kg on its roof reads below E4', a=w('E4, 1 kg on the roof')['upright'], b=w('E4 weeble')['upright'],
                ok=w('E4, 1 kg on the roof')['upright'] < w('E4 weeble')['upright']),
           dict(gauge='climb', claim='the box on 70 mm wheels (belly 12 mm) reads below the box', a=w('Box, 70 mm wheels')['climb'], b=w('Box')['climb'],
                ok=w('Box, 70 mm wheels')['climb'] < w('Box')['climb']),
           dict(gauge='turn', claim='the box 1.5x long reads above the box', a=w('Box, 1.5x long')['turn'], b=w('Box')['turn'],
                ok=(w('Box, 1.5x long')['turn'] or 1e9) > (w('Box')['turn'] or 1e9))]
    dtc = None
    if not quick:
        a = collect(R, 0, n_try, band=(1.0,), dt=0.0001)['by_mu']['1.0']; b = res['Box']['by_mu']['1.0']
        se = math.sqrt(a['upright'] * (1 - a['upright']) / a['n'] + b['upright'] * (1 - b['upright']) / b['n'])
        dtc = dict(upright=(a['upright'], b['upright']), climb=(a['climb'], b['climb']), turn=(a['turn'], b['turn']),
                   ok=bool(abs(a['upright'] - b['upright']) <= 2.5 * max(se, 1e-9) and abs(a['climb'] - b['climb']) <= 10
                           and a['turn'] is not None and b['turn'] is not None and abs(a['turn'] - b['turn']) <= 0.03 * b['turn']))
    edge = {sp['name']: dict(round=edge_normal(sp, 'round'), sharp=edge_normal(sp, 'sharp')) for sp in main}
    for e in edge.values():
        e['ok'] = bool(e['round'] is not None and e['round'] <= 5.0 and e['sharp'] is not None and e['sharp'] > 20.0)
    dims = {sp['name']: {k: sp[k] for k in ('mass', 'length', 'width', 'height', 'belly', 'R', 'notes')} | dict(wheels=len(sp['wheels']))
            for sp in specs}
    out = dict(date=time.strftime('%Y-%m-%d'), quick=quick, wall_s=round(time.time() - t0), band=BAND, contact=RB.CONTACT,
               friction=RB.FRICTION, n_drop=n_drop, n_try=n_try, heights=HEIGHTS, designs=[sp['name'] for sp in main],
               controls_designs=list(controls), dims=dims, results=res, controls=ctl, timestep=dtc, edge=edge)
    path = os.path.join(config.GAUGES_OUT, 'scorecard_quick.json' if quick else 'scorecard.json')
    json.dump(out, open(path, 'w'), indent=1, default=float)
    print(f'{len(J)} jobs, {out["wall_s"]} s -> {path}')
    for name in [sp['name'] for sp in specs]:
        r = res[name]; wv = r['worst']
        by = '  '.join(f"x{m}: {v['upright']:.2f}/{v['climb']}/{v['turn'] and round(v['turn'])}" for m, v in r['by_mu'].items())
        print(f"{name:20s} upright {wv['upright']:.3f}  step up {wv['climb']:3d} mm  turn {wv['turn'] and round(wv['turn'])} mm   [{by}]")
    for c in ctl:
        print(('PASS ' if c['ok'] else 'FAIL ') + f"{c['gauge']}: {c['claim']} ({c['a']} vs {c['b']})")
    for name, e in edge.items():
        print(('PASS ' if e['ok'] else 'FAIL ') + f"step edge on {name}: tyre normal {e['round']:.1f} deg off radial (sharp-edge control {e['sharp']:.1f})")
    if dtc:
        print(('PASS ' if dtc['ok'] else 'FAIL ') + f"timestep 0.1 vs 0.2 ms on the box: {dtc}")


def edge_normal(sp, edge, h=20, ticks=60):
    """the worst angle (degrees) between a tyre-on-step contact's normal and the radial line from the contact to the
    wheel's axle, over the first 0.3 s of contact. Right is near 0. A sharp edge starts radial, then flickers to its
    face's normal (1, 0, 0), about 50 degrees off at 20 mm: a wall."""
    sim = Sim(sp, step=h, edge=edge); m, d = sim.m, sim.d; R = sp['R'] * 1e-3
    sim.place(yaw_quat(0.0), 0.0005, x=-lead(sp, False) * 1e-3 - 0.08)
    d.qvel[0] = V_CLIMB; d.qvel[sim.jw] = V_CLIMB / R; sim.mj.mj_forward(m, d); u0 = V_CLIMB / (sim.w0 * R)
    wheel = {m.body(f'w{i}').id for i in range(len(sp['wheels']))}; worst, k0 = None, None
    for k in range(int(T_CLIMB * 1000 / TICK)):
        sim.drive(u0, u0)
        for i in range(d.ncon):
            c = d.contact[i]; b = {m.geom_bodyid[c.geom1], m.geom_bodyid[c.geom2]}
            if b & wheel and 0 in b and c.pos[2] > 0.25 * h * 1e-3:
                wb = (b & wheel).pop(); r = d.xpos[wb] - c.pos; r[1] = 0.0; r /= np.linalg.norm(r)
                a = float(np.degrees(np.arccos(min(1.0, abs(float(c.frame[:3] @ r))))))
                worst = a if worst is None else max(worst, a); k0 = k if k0 is None else k0
        if k0 is not None and k - k0 >= ticks:
            break
    return worst


def port():
    """the climb sim against chassis3's on chassis3's Trainer stand-in. With the sharp edge chassis3 has, this sim must
    agree with it; with the round edge it climbs where the sharp one stalls. Then the edge's normal, both ways."""
    import chassis3 as C3
    D = C3.design(C3.BASE); sp = RB.from_built('chassis3 baseline', D); H = (10, 20, 30, 40)
    with Pool(8) as pool:
        A = pool.map(C3.climb, [(C3.BASE, (h,), 0.5, 20, 31 + h) for h in H])
    for h, a in zip(H, A):
        row = [f'chassis3 {a[(h, False)].get("climbed", 0)}/{a[(h, True)].get("climbed", 0)}']
        for edge in ('sharp', 'round'):
            rng = np.random.default_rng(5); sim = Sim(sp, 1.0, step=h, edge=edge)
            row.append(f'{edge} {sum(climb_try(sim, h, False, rng) for _ in range(20))}/{sum(climb_try(sim, h, True, rng) for _ in range(20))}')
        print(f'{h} mm, climbed of 20 forwards/in reverse: ' + ', '.join(row))
    for edge in ('sharp', 'round'):
        print(f'{edge} edge: first tyre contact {edge_normal(sp, edge):.1f} degrees off radial')


if __name__ == '__main__':
    if 'port' in sys.argv[1:]:
        port()
    else:
        run(quick='--quick' in sys.argv, cached='--cached' in sys.argv)
