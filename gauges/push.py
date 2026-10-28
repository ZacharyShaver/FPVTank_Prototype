"""G7 push, proposed (2026-10-27): the heaviest box a design shoves 0.5 m. Zach chose it from the knob log's
recommended tests: moving boxes is in the purpose, and none of the other gauges reads force.

    SCORPION_SEARCH=search_hills python gauges/push.py read   # the roster, T3 and the controls -> gauges/out/push/read.json

The box: 200 mm deep, 260 wide, 150 tall, the floor's own friction (0.6 at x1, so it takes 5.9 N a kilogram to slide
at x1). A try starts square on +-10 degrees with the robot's lead 20 mm short of the box, ramps up over 0.5 s to
V_PUSH and holds its heading (a proportional steer, as an operator would). It passes when the box has gone 0.5 m within
T_PUSH with the robot upright and not up on the box. The better direction counts; the tail stays stowed. Read over
the friction band (the box's friction scales with the floor's), the worst counting.
"""
import os, sys, json, math, time
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import gauges as GG, robots as RB

OUT = os.path.join(config.GAUGES_OUT, 'push')
BOX = (0.10, 0.13, 0.075)                 # half-sizes, m
MASSES = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0)   # kg
V_PUSH, T_PUSH, RAMP, GOAL = 0.3, 6.0, 0.5, 0.5
N_TRY = 20


def box(kg):
    def xml(f, ca):
        return (f'<body name="box" pos="{BOX[0]:.4f} 0 {BOX[2] + 0.0005:.4f}"><freejoint/>'
                f'<geom name="box" type="box" size="{BOX[0]} {BOX[1]} {BOX[2]}" mass="{kg:.3f}" friction="{f["floor"]}"{ca}/></body>')
    return xml


def push_try(sim, back, rng):
    """one try: 'ok', 'stalled' (the box short of GOAL at T_PUSH), 'tipped' or 'rode up' (its front up on the box, 40 mm)"""
    sp, d, m = sim.sp, sim.d, sim.m; R = sp['R'] * 1e-3; sgn = -1.0 if back else 1.0
    yaw0 = math.radians(rng.uniform(-10, 10)) + (math.pi if back else 0.0)
    sim.place(GG.yaw_quat(yaw0), 0.0005, x=-GG.lead(sp, back) * 1e-3 - 0.02)
    bq = m.joint(m.body('box').jntadr[0]).qposadr[0]                     # the box's free joint (placed by the model)
    d.qpos[bq:bq + 7] = (BOX[0], 0.0, BOX[2] + 0.0005, 1.0, 0.0, 0.0, 0.0); sim.mj.mj_forward(m, d)
    bid = m.body('box').id; x0 = d.xipos[bid][0]; z0 = d.xipos[sim.rid][2]; u0 = sgn * min(V_PUSH / (sim.w0 * R), 1.0)
    for k in range(int(T_PUSH * 1000 / GG.TICK)):
        Rm = sim.rot(); e = (math.atan2(Rm[1, 0], Rm[0, 0]) - yaw0 + math.pi) % (2 * math.pi) - math.pi
        u = u0 * min(1.0, k * GG.TICK / 1000 / RAMP); c = abs(u0) * max(-0.5, min(0.5, 2.0 * e))
        sim.drive(u + c, u - c)
        if math.degrees(math.acos(max(-1.0, min(1.0, Rm[2, 2])))) > 60.0:
            return 'tipped'
        if d.xipos[sim.rid][2] - z0 > 0.04:
            return 'rode up'
        if d.xipos[bid][0] - x0 >= GOAL:
            return 'ok' if GG.classify(sim.rot()) == 'upright' else 'tipped'
    return 'stalled'


def ladder(sp, mu, n, seed):
    """the heaviest box pushed in at least 0.9 n of n tries in the better direction, every lighter one pushed"""
    need = math.ceil(0.9 * n); top = 0.0; seen = {}
    for kg in MASSES:
        sim = GG.Sim(sp, mu, extra=box(kg)); best = None
        for back in (False, True):
            rng = np.random.default_rng([seed, int(kg * 10), int(back)]); res = []
            for _ in range(n):
                res.append(push_try(sim, back, rng))
                if sum(r != 'ok' for r in res) > n - need:
                    break
            ok = sum(r == 'ok' for r in res) >= need; cnt = {k: res.count(k) for k in set(res)}
            if best is None or ok:
                best = (ok, cnt)
            if ok:
                break
        seen[kg] = best[1]
        if not best[0]:
            break
        top = kg
    return top, seen


def nxt(kg):
    i = MASSES.index(kg) + 1 if kg in MASSES else 0
    return MASSES[i] if i < len(MASSES) else None


SP = None


def _init(specs):
    global SP
    SP = specs


def job(a):
    i, mu, n, seed = a
    return a, ladder(SP[i], mu, n, seed)


def specs_read():
    import knobs as K
    main, ctl = GG.roster(True)
    return [dict(K.make(K.T3), name='T3'), main[0], main[1], main[2], main[3],
            dict(K.make(dict(K.T3, gear=0.4)), name='T3, geared 0.4x'),        # control: a fifth of the torque reads lower
            dict(K.make(K.T3), tyre_mu=0.5, name='T3, tyres at half grip')]   # control: half the tread grip reads lower


def read(n=N_TRY):
    specs = specs_read(); J = [(i, mu, n, 71 + i) for i in range(len(specs)) for mu in GG.BAND]; t0 = time.time()
    with Pool(GG.WORKERS, initializer=_init, initargs=(specs,)) as pool:
        R = pool.map(job, J, chunksize=1)
    out = []
    for i, sp in enumerate(specs):
        by = {mu: r for (i_, mu, _, _), r in R if i_ == i}
        w = min(by, key=lambda mu: by[mu][0]); top = by[w][0]
        out.append(dict(name=sp['name'], push=top, worst_mu=w, by_mu={str(mu): v[0] for mu, v in by.items()},
                        why=by[w][1].get(nxt(top)), mass=sp['mass']))
        print(f"{sp['name']:26s} push {top:4.1f} kg (worst at x{w}; by friction {out[-1]['by_mu']}); next: {out[-1]['why']}  robot {sp['mass'] / 1000:.2f} kg", flush=True)
    ctl = controls(out)
    for c, ok in ctl:
        print(('PASS ' if ok else 'FAIL ') + c)
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), n=n, masses=MASSES, rows=out, controls=[dict(claim=c, ok=ok) for c, ok in ctl]),
              open(os.path.join(OUT, 'read.json'), 'w'), indent=1, default=str)


def controls(out):
    """the motors bind at x1.5 (the box drags harder on a grippier floor) and the tyres at x0.65, so each control is read
    where its claim applies: a fifth of the torque, the worst over the band; half the grip, at x0.65. (Read at the
    band's worst, half grip tied T3 at 1 kg: both rode up the box at x1.5.)"""
    by = {r['name']: r for r in out}
    return [('T3 geared 0.4x reads below T3 (worst)', by['T3, geared 0.4x']['push'] < by['T3']['push']),
            ('T3 at half grip reads below T3 at x0.65', by['T3, tyres at half grip']['by_mu']['0.65'] < by['T3']['by_mu']['0.65'])]


def check():
    import knobs as K
    sp = K.make(K.T3); t0 = time.time()
    for kg in (1.0, 3.0, 6.0):
        sim = GG.Sim(sp, 1.0, extra=box(kg)); rng = np.random.default_rng(1)
        print(kg, 'kg forward', [push_try(sim, False, rng) for _ in range(3)], 'reverse', [push_try(sim, True, rng) for _ in range(2)], f'{time.time() - t0:.1f} s', flush=True)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'check': check, 'read': read}.get(cmd, lambda: print(__doc__))()
