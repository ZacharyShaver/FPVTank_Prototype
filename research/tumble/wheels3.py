"""EXPLORATORY (2026-10-25): the drop-pose lab, step 2. Can the Trainer's wheels turn it in the air? The four-wheel
Trainer (pose3's cache of chassis-v2) with each wheel on a hinge driven by a 37 mm 30:1-class DC gearmotor*, and a
controller that reads the body's attitude from an IMU* (none on the robot yet; BNO085 on the list) after a delay.

    python research/tumble/wheels3.py check     # the motor model against the momentum estimate (no contact)
    python research/tumble/wheels3.py run       # drops from height and drives off a ledge, passive against controlled
      -> research/results/wheels3/*.json

Only pitch can be steered: all four axles lie along the body's Y. Spinning the wheels one way turns the body the
other. The rotor matters twice and differently: through the gearbox it limits how fast the wheel spins up (its
inertia reflected N^2 times), but its share of the momentum that turns the body is only N times its own. So each
wheel carries I_w + N I_r about its axle (that couples to the body), the joint's armature the rest, (N^2 - N) I_r
(that doesn't), and the motor drives the joint with its full torque. (First version, 2026-10-25: the torque scaled
to 12% instead of the armature. Same in the air, but on the ground the wheels pushed with 12% of the motor.)

Contact, settle rule and classes are shell3.robot_trials' (soft floor, bounce 0.2, 1 ms). * = datasheet guess.

SUPERSEDED for steps (2026-10-25): the ledge scenarios here are wrong twice over. The body hull includes the rims,
a fake skid plate 5 mm off the ground that slid over every edge, and the soft floor sinks into a step's edge and then
throws the robot up (traced in chassis3). chassis3.py's step model replaces them. `check` and the drops from height
touch no edge and stand.
"""
import os, sys, json, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'results', 'wheels3')
sys.path.insert(0, HERE)
import pose3 as P3
import tumble as T

MOTOR = dict(stall=1.0, w0=330 * 2 * np.pi / 60, N=30.0, Ir=3e-6)    # N m at the wheel*, rad/s no-load*, ratio, rotor kg m2*
DELAY = 0.03                                                          # s: free-fall detection, IMU and driver*
KV = 4.0                                                              # wheel speed loop gain on the ground (the encoders)
R_T, TW, Z_A = 55.0, 46.0, 30.0
WHEELS = {'FL': (91.0, 131.0), 'FR': (91.0, -131.0), 'RL': (-93.0, 131.0), 'RR': (-93.0, -131.0)}   # x, y (centre line 0)


def parts():
    """the robot body's mass items (no tyres or rims) and each wheel's mass and axle inertia, from pose3's cache"""
    c = P3.C(); body, wheel = [], {k: [0.0, 0.0] for k in WHEELS}
    for n, m, p in c['items']:
        if n.startswith(('tire_', 'rim_')):
            k = n.split('_')[1]; pts = c['pts'][n]; r2 = ((pts[:, 0] - WHEELS[k][0]) ** 2 + (pts[:, 2] - Z_A) ** 2).mean()
            wheel[k][0] += m; wheel[k][1] += m * r2 * 1e-9                                       # g, kg m2 (thin-walled)
        else:
            body.append((n, m, p))
    return body, wheel


def xml(motor=MOTOR, ledge=None, arm_q=None):
    """MJCF: the robot (free) with its body hull and four wheels on hinges; `ledge` (h mm): a step down at X 0"""
    c = P3.C(); body, wheel = parts(); s = 1e-3
    if arm_q is not None:
        body = body + [(n, m, np.asarray(p, float) - [0, c['yc'], 0]) for n, m, p in c['GA'].mass_items(arm_q, payload=False)]
    M = sum(m for _, m, _ in body); G = sum(m * np.asarray(p) for _, m, p in body) / M; I = np.zeros((3, 3))
    for n, m, p in body:
        d = np.asarray(p) - G; I += m * (d @ d * np.eye(3) - np.outer(d, d))
        h = c['box'].get(n)
        if h is not None:
            a, b, cc = (2 * h) ** 2; I += m / 12 * np.diag([b + cc, a + cc, a + b])
    Isi = I * 1e-9; full = ' '.join('%.8g' % v for v in (Isi[0, 0], Isi[1, 1], Isi[2, 2], Isi[0, 1], Isi[0, 2], Isi[1, 2]))
    hull = c['body']
    if arm_q is not None:
        hull = np.vstack([hull, P3.capsule_points(P3.capsules(arm_q))]); hull = hull[ConvexHull(hull).vertices]
    verts = ' '.join('%.5f' % v for v in (hull * s).ravel())
    wb = ''
    for k, (x, y) in WHEELS.items():
        m, Ia = wheel[k]; Ie = Ia + motor['N'] * motor['Ir']; mk = m * 1e-3; It = max(mk * (3 * (R_T * s) ** 2 + (TW * s) ** 2) / 12, 0.5 * Ie * 1.001)   # A + B >= C with the rotor's share
        arm = (motor['N'] ** 2 - motor['N']) * motor['Ir']
        wb += (f'<body name="w{k}" pos="{x * s:.4f} {y * s:.4f} {Z_A * s:.4f}"><joint name="j{k}" type="hinge" axis="0 1 0" damping="0" armature="{arm:.6g}"/>'
               f'<inertial pos="0 0 0" mass="{mk:.4f}" diaginertia="{It:.6g} {Ie:.6g} {It:.6g}"/>'
               f'<geom type="cylinder" size="{R_T * s:.4f} {TW / 2 * s:.4f}" euler="90 0 0" friction="0.9 0.01 0.001"/></body>')
    floor = '<geom type="plane" size="6 6 0.1" friction="0.6 0.005 0.0005"/>'
    if ledge:
        floor += f'<geom type="box" size="2 2 {ledge / 2 * s:.4f}" pos="-2 0 {ledge / 2 * s:.4f}" friction="0.6 0.005 0.0005"/>'
    return f"""<mujoco><option timestep="0.001"/><default><geom solref="0.02 0.2"/></default>
      <asset><mesh name="body" vertex="{verts}"/></asset><worldbody>{floor}
      <body name="robot" pos="0 0 0.5"><freejoint/>
        <inertial pos="{G[0] * s:.5f} {G[1] * s:.5f} {G[2] * s:.5f}" mass="{M * 1e-3:.4f}" fullinertia="{full}"/>
        <geom type="mesh" mesh="body" friction="0.4 0.005 0.0005"/>{wb}</body></worldbody></mujoco>"""


class Sim:
    def __init__(self, motor=MOTOR, ledge=None, arm_q=None):
        import mujoco
        self.mj = mujoco; self.motor = motor; self.m = mujoco.MjModel.from_xml_string(xml(motor, ledge, arm_q)); self.d = mujoco.MjData(self.m)
        _, wheel = parts(); Iw = np.mean([v[1] for v in wheel.values()])
        self.k = 1.0                                                   # the motor's full torque (the armature takes the rotor)
        self.jw = [self.m.joint('j' + k).dofadr[0] for k in WHEELS]
        self.wheel_geoms = {self.m.body('w' + k).id for k in WHEELS}; self.robot_id = self.m.body('robot').id
        c = P3.C(); self.E = np.vstack([c['body']] + [c['pts'][k] for k in c['tyres']]) * 1e-3

    def torque(self, u):
        w = self.d.qvel[self.jw]
        return self.k * self.motor['stall'] * (np.clip(u, -1, 1) - w / self.motor['w0'])

    def contacts(self):
        return self.d.ncon > 0

    def pitch_error(self):
        """the turn about the body's Y that brings its Z axis nearest world up, and the pitch rate (body frame)"""
        R = self.d.xmat[self.robot_id].reshape(3, 3); u = R.T @ np.array([0, 0, 1.0])
        return float(np.arctan2(-u[0], u[2])), float(self.d.qvel[4])


def run(sim, q0, pos, vel, ang, ctrl, drive=0.0, t_max=6.0, hold=0.0, rec=None, fall=None):
    """one trial: ctrl(err, rate) -> u whenever the robot has been airborne for DELAY, `drive` u while it touches
    anything before it lands; landed means touching again with its CoM `fall` mm (default: the start height) x 0.4
    lower than at the start, so a hop at the edge doesn't count (2026-10-25: it did, and switched the controller off
    before the real flight). After landing, `drive` for `hold` s, then coasting (no torque). Returns the rest class
    and the flight time."""
    mj, m, d = sim.mj, sim.m, sim.d
    mj.mj_resetData(m, d); d.qpos[:3] = pos; d.qpos[3:7] = q0; d.qvel[:3] = vel; d.qvel[3:6] = ang
    d.qvel[sim.jw] = np.sign(drive) * np.linalg.norm(vel) / (R_T * 1e-3) if drive else 0.0   # rolling at the body's speed
    mj.mj_forward(m, d)
    z0 = d.xipos[sim.robot_id][2]; drop = 0.4 * (fall * 1e-3 if fall is not None else pos[2])
    hist, air, landed, t_air, still, i_land, flown = [], 0.0, False, 0.0, 0, 0, 0.0
    n = int(round(t_max / m.opt.timestep))
    for i in range(n):
        e, r = sim.pitch_error(); hist.append((e, r))
        incontact = sim.contacts()
        if not incontact:
            air += m.opt.timestep; flown += m.opt.timestep
        else:
            if not landed and z0 - d.xipos[sim.robot_id][2] > drop:
                landed = True; i_land = i; t_air = flown
            air = 0.0
        if landed: u = drive if (i - i_land) * m.opt.timestep < hold else None
        elif air >= DELAY:
            j = max(0, len(hist) - 1 - int(round(DELAY / m.opt.timestep))); u = ctrl(*hist[j])
        else: u = drive
        if u is not None and incontact and u == drive and drive:          # on the ground the encoders hold the speed
            u = drive + KV * (drive * sim.motor['w0'] - d.qvel[sim.jw].mean()) / sim.motor['w0']
        d.qfrc_applied[:] = 0.0
        if u is not None:
            d.qfrc_applied[sim.jw] = sim.torque(u)
        mj.mj_step(m, d)
        if rec is not None and i % 10 == 0:
            rec.append((i * m.opt.timestep, d.qpos[:7].copy(), None if u is None else float(np.clip(u, -1, 1)), bool(incontact)))
        if landed and i % 20 == 0:
            if np.abs(d.qvel[:6]).max() < 0.02:
                still += 1
                if still >= 6: break
            else:
                still = 0
    sim.landed = landed
    return T.classify(d.xmat[sim.robot_id].reshape(3, 3)), t_air


def passive(e, r): return 0.0
def pd(kp, kd, b=0.0): return lambda e, r: kp * e + kd * r + b


def drop_trials(args):
    """drops from height: uniformly random attitude, spin up to `spin` rad/s, the lowest point h mm over the floor"""
    h, gains, n, seed, motor, spin, arm_q = args
    sim = Sim(motor, arm_q=arm_q); rng = np.random.default_rng(seed); ctrl = passive if gains is None else pd(*gains)
    cnt = {k: 0 for k in T.CLASSES}
    for _ in range(n):
        q = rng.normal(size=4); q /= np.linalg.norm(q)
        R9 = np.zeros(9); sim.mj.mju_quat2Mat(R9, q); Rm = R9.reshape(3, 3)
        z = h * 1e-3 - (sim.E @ Rm.T)[:, 2].min()
        cls, _ = run(sim, q, (0, 0, z), (0, 0, 0), rng.uniform(-1, 1, 3) * spin, ctrl, fall=h)
        cnt[cls] += 1
    return cnt


def ledge_trials(args):
    """drives off a step h mm high at v m/s, heading within +-15 deg of square to the edge, forwards or in reverse"""
    h, v, gains, n, seed, motor, back = args
    sim = Sim(motor, ledge=h); rng = np.random.default_rng(seed)
    cnt = {k: 0 for k in T.CLASSES}
    for _ in range(n):
        yaw = np.radians(rng.uniform(-15, 15)) + (np.pi if back else 0.0)
        q = np.array([np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)])
        sim.mj.mj_resetData(sim.m, sim.d); z = h * 1e-3 - sim.E[:, 2].min() + 0.0005
        vel = np.array([v * rng.uniform(0.9, 1.1), 0, 0])
        u_drive = float(np.clip(vel[0] / (motor['w0'] * R_T * 1e-3), 0, 1)) * (-1 if back else 1)   # the throttle that holds this speed
        f = (lambda e, r, u0=u_drive: u0) if gains is None else (lambda e, r, u0=u_drive: u0 + gains[0] * e + gains[1] * r)
        x0 = -0.30 - rng.uniform(0, 0.1)
        cls, _ = run(sim, q, (x0, 0, z), vel, (0, 0, 0), f, drive=u_drive, fall=h)
        cls = cls if sim.landed else 'stuck'                           # never got down: hung on the edge
        cnt[cls] = cnt.get(cls, 0) + 1
    return cnt


SCEN = {'ledge forward': dict(h=(150, 600), v=(0.2, 1.2), back=False), 'ledge reverse': dict(h=(150, 600), v=(0.2, 1.2), back=True),
        'drop': dict(h=(200, 1000), spin=0.5)}


def policy(p, u0):
    """None: hold the throttle (or nothing, dropped). Else (kp, kd, target deg): u = u0 + kp (pitch error - target) +
    kd pitch rate, saturated by the motor"""
    if p is None:
        return lambda e, r: u0
    kp, kd, tgt = p; t = np.radians(tgt)
    return lambda e, r: u0 + kp * (e - t) + kd * r


def scenario_trials(args):
    """n trials of a scenario under policy p; returns (counts, per-trial (h, v, upright))"""
    name, p, n, seed, motor = args
    sc = SCEN[name]; rng = np.random.default_rng(seed); cnt = {k: 0 for k in T.CLASSES}; rows = []
    sims = {}
    for _ in range(n):
        h = rng.uniform(*sc['h'])
        if name == 'drop':
            sim = sims.setdefault(None, Sim(motor))
            q = rng.normal(size=4); q /= np.linalg.norm(q); R9 = np.zeros(9); sim.mj.mju_quat2Mat(R9, q)
            z = h * 1e-3 - (sim.E @ R9.reshape(3, 3).T)[:, 2].min()
            cls, _ = run(sim, q, (0, 0, z), (0, 0, 0), rng.uniform(-1, 1, 3) * sc['spin'], policy(p, 0.0), fall=h); v = 0.0
        else:
            hk = int(round(h / 25.0) * 25); sim = sims.get(hk)
            if sim is None:
                sim = sims[hk] = Sim(motor, ledge=hk)
            v = rng.uniform(*sc['v']); yaw = np.radians(rng.uniform(-15, 15)) + (np.pi if sc['back'] else 0.0)
            q = np.array([np.cos(yaw / 2), 0, 0, np.sin(yaw / 2)])
            u0 = float(np.clip(v / (motor['w0'] * R_T * 1e-3), 0, 1)) * (-1 if sc['back'] else 1)
            z = hk * 1e-3 - sim.E[:, 2].min() + 0.0005
            cls, _ = run(sim, q, (-0.30 - rng.uniform(0, 0.1), 0, z), np.array([v, 0, 0]), (0, 0, 0), policy(p, u0), drive=u0, hold=1.0, fall=hk); h = hk
            cls = cls if sim.landed else 'stuck'
        cnt[cls] = cnt.get(cls, 0) + 1; rows.append((float(h), float(v), cls == 'upright'))
    return cnt, rows


def tune(name, gens=8, pop=27, n=60, seed=0):
    """cross-entropy over (kp, kd, target) for one scenario, the passive policy alongside"""
    rng = np.random.default_rng(seed); mu, sd = np.array([0.0, 0.0, 0.0]), np.array([6.0, 1.0, 40.0])
    best = []; hist = []
    with Pool(WORKERS) as pool:
        for g in range(gens):
            X = mu + sd * rng.normal(size=(pop, 3)); X[:, 2] = np.clip(X[:, 2], -90, 90)
            R = pool.map(scenario_trials, [(name, tuple(x), n, 1000 + g, MOTOR) for x in X] + [(name, None, n, 1000 + g, MOTOR)])
            sc = [c['upright'] / n for c, _ in R[:-1]]; p0 = R[-1][0]['upright'] / n
            hist.append(dict(gen=g, passive=p0, best=max(sc), mean=float(np.mean(sc))))
            best = sorted(best + list(zip(sc, map(tuple, X))), key=lambda t: -t[0])[:6]
            E = np.array([b[1] for b in best]); mu = 0.6 * E.mean(0) + 0.4 * mu; sd = np.maximum(0.6 * E.std(0) + 0.4 * sd * 0.8, [0.3, 0.05, 3.0])
            print(f'{name} gen {g}: passive {p0:.2f}, best {max(sc):.2f}, mean {np.mean(sc):.2f}, mu {np.round(mu, 2)}', flush=True)
    return best, hist


WORKERS = 28


def check():
    """in free fall, no contact: spin all four wheels up from rest at full voltage for 0.25 s (a 30 cm fall) and
    measure the body's pitch, against the momentum estimate (I_w + N I_r) / I_body x wheel angle"""
    sim = Sim(); mj, m, d = sim.mj, sim.m, sim.d; m.opt.gravity[:] = 0
    mj.mj_resetData(m, d); d.qpos[2] = 1.0; mj.mj_forward(m, d)
    th_w = 0.0; e0 = sim.pitch_error()[0]
    for i in range(250):
        d.qfrc_applied[:] = 0; d.qfrc_applied[sim.jw] = sim.torque(1.0); mj.mj_step(m, d); th_w += d.qvel[sim.jw].mean() * m.opt.timestep
    e1 = sim.pitch_error()[0]; w = d.qvel[sim.jw].mean()
    _, wheel = parts(); Iw = np.mean([v[1] for v in wheel.values()]); Ie = 4 * (Iw + MOTOR['N'] * MOTOR['Ir'])
    Ib = m.body_inertia[sim.robot_id][1]
    print(f"wheel I_axle {Iw:.3g} kg m2 (+ N Ir {MOTOR['N'] * MOTOR['Ir']:.3g}), torque share k {sim.k:.3f}; after 0.25 s: wheels {w:.1f} rad/s "
          f"({th_w:.2f} rad turned), body pitch {np.degrees(e1 - e0):.1f} deg; estimate {np.degrees(Ie / (Ib + Ie) * th_w):.1f} deg (body I_yy {Ib:.4f})")
    # control: the same with the wheels' torque share k = 1 (all of the rotor's reflected inertia turning the body)
    return np.degrees(e1 - e0)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if cmd == 'check':
        check()
    elif cmd == 'tune':
        os.makedirs(OUT, exist_ok=True); res = {}
        for name in (sys.argv[2:] or list(SCEN)):
            best, hist = tune(name)
            with Pool(WORKERS) as pool:                                 # the top 3 and passive, 600 trials each, fresh seeds
                R = pool.map(scenario_trials, [(name, b[1], 100, 5000 + k, MOTOR) for b in best[:3] for k in range(6)] + [(name, None, 100, 5000 + k, MOTOR) for k in range(6)])
            def agg(rs):
                c = {}; rows = []
                for cc, rr in rs:
                    rows += rr
                    for k, v in cc.items(): c[k] = c.get(k, 0) + v
                return c, rows
            fin = [dict(params=b[1], tune_score=b[0], **dict(zip(('counts', 'rows'), agg(R[6 * j:6 * j + 6])))) for j, b in enumerate(best[:3])]
            pas = dict(zip(('counts', 'rows'), agg(R[18:])))
            res[name] = dict(history=hist, finalists=fin, passive=pas)
            print(name, 'passive', pas['counts']['upright'] / 600, '| finalists', [(np.round(f['params'], 2).tolist(), f['counts']['upright'] / 600) for f in fin], flush=True)
        json.dump(res, open(os.path.join(OUT, 'tune_%s.json' % '_'.join(n.split()[-1] for n in res)), 'w'), default=float)
