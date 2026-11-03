"""G6 crest, proposed (2026-10-27): the steepest ridge a design drives over. Zach chose it from the knob log's
recommended tests: today's gauges only charge for body height, and a crest is where height pays (a low belly or a
long wheelbase ends up balanced on its belly, wheels in the air: high-centred).

    SCORPION_SEARCH=search_hills python gauges/crest.py check   # T3 rebuilt reads as the knob sweep did; a few tries
    SCORPION_SEARCH=search_hills python gauges/crest.py read    # the roster, T3 and the controls -> gauges/out/crest/read.json

The ridge: two planks at +-angle meeting at a peak CREST_MM tall, the peak rounded by a capsule of EDGE_R tangent to
both (the step's edge lesson: a sharp edge reads as a wall to a cylinder tyre). It runs across the whole floor. A try
starts square on +-10 degrees, its lead just short of the ridge's foot, and crawls at V_CREST with the step's tail
reflex (push when stalled nose up, kick when level). At the step's 0.5 m/s, momentum carried a 15 mm belly over the
peak (hiding high-centring) and threw T3 into a nose-dive off it (25 degrees, against 40 at 0.25 and 35 at 0.12); at a
crawl the ridge reads geometry, and a lower belly high-centres (the Box 15, 5 with its belly 15 mm lower). It passes once its CoM is 0.1 m past the far foot
with it upright, within the time to drive the ridge plus 3 s. The better direction counts, as on the step. Read on
grippy ground (x2.5, as the hills): on the band's floors the ramps alone slide every design at 25-30 degrees.

T3 reads on a plateau: from 25 to 40 degrees it crosses in 75-95% of tries, against the 90% a reading needs, so 20
tries read it 25 or 40 by luck (`curve`, 40 tries an angle and direction). Backwards it crosses 40 every time and 25
only 34 in 40.

    python gauges/crest.py curve   # T3 and a 34 mm tail foot, each angle's pass count -> gauges/out/crest/curve.json
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

OUT = os.path.join(config.GAUGES_OUT, 'crest')
CREST_MM = 150.0                          # the peak's height: G2's top step, so the ridge is tall enough to reach any belly
ANGLES = tuple(range(5, 65, 5))           # each plank's slope, degrees: the crest bends the path by twice this
V_CREST = 0.15                            # m/s, a crawl
GRIP = 2.5
N_TRY = 20


def ridge(deg, x0=0.0):
    """extra XML for robots.xml: the ridge, its near foot at X x0 (m; course.py's is down the course); and its far foot's X"""
    a = math.radians(deg); H = CREST_MM * 1e-3; r = RB.EDGE_R * 1e-3; t = 0.05
    xp = x0 + H / math.tan(a)                                             # the peak's X
    d = r / math.cos(a); C = (xp, H - d)                                  # the rounding's centre, tangent to both faces
    Tu = (xp - r * math.sin(a), H - d + r * math.cos(a))                  # where it meets each face
    def plank(x0, z0, x1, z1, sg):                                        # a slab whose top face runs (x0, z0) -> (x1, z1)
        L = math.hypot(x1 - x0, z1 - z0); nx, nz = -sg * math.sin(a), math.cos(a)
        cx, cz = (x0 + x1) / 2 - nx * t / 2, (z0 + z1) / 2 - nz * t / 2; ph = -sg * a
        return cx, cz, L, (math.cos(ph / 2), 0.0, math.sin(ph / 2), 0.0)
    def xml(f, ca):
        s = ''
        for xa, za, xb, zb, sg in ((x0, 0.0, Tu[0], Tu[1], 1), (2 * xp - Tu[0], Tu[1], 2 * xp - x0, 0.0, -1)):
            cx, cz, L, q = plank(xa, za, xb, zb, sg)
            s += (f'<geom name="plank{sg:+d}" type="box" size="{L / 2:.5f} 2 {t / 2:.5f}" pos="{cx:.5f} 0 {cz:.5f}" '
                  f'quat="{q[0]:.6f} {q[1]:.6f} {q[2]:.6f} {q[3]:.6f}" friction="{f["floor"]}"{ca}/>')
        return s + f'<geom name="peak" type="capsule" fromto="{C[0]:.5f} -2 {C[1]:.5f} {C[0]:.5f} 2 {C[1]:.5f}" size="{r:.5f}" friction="{f["floor"]}"{ca}/>'
    return xml, 2 * xp - x0


def crest_try(sim, deg, back, rng, far):
    """one try: 'ok', 'stuck' (timed out on the ridge; 'stuck, belly' when its body rests on the ridge), 'tipped'"""
    sp, d = sim.sp, sim.d; R = sp['R'] * 1e-3; sgn = -1.0 if back else 1.0
    yaw = math.radians(rng.uniform(-10, 10)) + (math.pi if back else 0.0)
    sim.place(GG.yaw_quat(yaw), 0.0005, x=-GG.lead(sp, back) * 1e-3 - 0.03)
    d.qvel[0] = V_CREST; d.qvel[sim.jw] = sgn * V_CREST / R; sim.mj.mj_forward(sim.m, d)   # toward +X either way, as climb_try
    u0 = sgn * min(V_CREST / (sim.w0 * R), 1.0); T = (far + 0.4) / V_CREST + 3.0
    rf = GG.Reflex(sim)
    for k in range(int(T * 1000 / GG.TICK)):
        t = k * GG.TICK / 1000
        if (sim.limb or sim.flip) and not back:                           # the step's reflex (gauges.Reflex), shared
            rf.tick(t)
        sim.drive(u0, u0)
        Rm = sim.rot()
        if math.degrees(math.acos(max(-1.0, min(1.0, Rm[2, 2])))) > 75.0:
            return 'tipped'
        if d.xipos[sim.rid][0] > far + 0.1:
            return 'ok' if GG.classify(Rm) == 'upright' else 'tipped'
    belly = any(sim.m.geom_bodyid[c.geom1] == sim.rid or sim.m.geom_bodyid[c.geom2] == sim.rid for c in d.contact[:d.ncon]
                if sim.m.geom(c.geom1).name in ('plank+1', 'plank-1', 'peak') or sim.m.geom(c.geom2).name in ('plank+1', 'plank-1', 'peak'))
    return 'stuck, belly' if belly else 'stuck'


def ladder(sp, mu, n, seed):
    """the steepest ridge crossed in at least 0.9 n of n tries in the better direction, every gentler one crossed;
    and each angle's outcomes"""
    need = math.ceil(0.9 * n); top = 0; seen = {}
    for deg in ANGLES:
        xml, far = ridge(deg); sim = GG.Sim(sp, mu, extra=xml); best = None
        for back in (False, True):
            rng = np.random.default_rng([seed, deg, int(back)]); res = []
            for _ in range(n):
                res.append(crest_try(sim, deg, back, rng, far))
                if sum(r != 'ok' for r in res) > n - need:
                    break
            ok = sum(r == 'ok' for r in res) >= need; cnt = {k: res.count(k) for k in set(res)}
            if best is None or ok:
                best = (ok, cnt)
            if ok:
                break
        seen[deg] = best[1]
        if not best[0]:
            break
        top = deg
    return top, seen


SP = None


def _init(specs):
    global SP
    SP = specs


def job(a):
    i, mu, n, seed = a
    return a, ladder(SP[i], mu, n, seed)


def specs_read():
    import knobs as K
    main, ctl = GG.roster(True); T3 = K.make(K.T3); bx = main[0]
    H = bx['hulls'][0].copy(); H[H[:, 2] <= H[:, 2].min() + 1e-6, 2] -= 15.0
    low = RB.dims(dict(bx, hulls=[H], name='Box, belly 15 mm lower', notes=list(bx['notes']) + ['belly 15 mm lower']))
    return [dict(T3, name='T3'), bx, main[1], main[2], main[3],
            dict(K.make(dict(K.T3, clr=15.0)), name='T3, ride height 15 mm'),   # a row, not a control: T3 tips before its belly matters
            low,                                                           # control: where high-centring binds, a lower belly reads lower
            ctl['box_long']]                                               # control: a longer wheelbase reads lower


def read(n=N_TRY):
    specs = specs_read(); J = [(i, GRIP, n, 61 + i) for i in range(len(specs))]; t0 = time.time()
    with Pool(GG.WORKERS, initializer=_init, initargs=(specs,)) as pool:
        R = pool.map(job, J, chunksize=1)
    out = []
    for (i, mu, n_, seed), (top, seen) in R:
        out.append(dict(name=specs[i]['name'], crest=top, why=seen.get(top + 5), seen=seen))
        print(f"{specs[i]['name']:28s} crest {top:3d} deg (crest angle {2 * top}); next: {seen.get(top + 5)}", flush=True)
    by = {r['name']: r['crest'] for r in out}
    ctl = [('Box, belly 15 mm lower reads below the box', by['Box, belly 15 mm lower'] < by['Box']),
           ('Box, 1.5x long reads below the box', by['Box, 1.5x long'] < by['Box'])]
    for c, ok in ctl:
        print(('PASS ' if ok else 'FAIL ') + c)
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), n=n, angles=ANGLES, crest_mm=CREST_MM, rows=out, controls=[dict(claim=c, ok=ok) for c, ok in ctl]),
              open(os.path.join(OUT, 'read.json'), 'w'), indent=1, default=str)


CURVE = {'T3': {}, 'foot 34': dict(foot_r=34.0)}


def curve_job(a):
    import knobs as K
    name, deg, back, chunk = a
    sp = K.make(dict(K.T3, **CURVE[name])); xml, far = ridge(deg); sim = GG.Sim(sp, GRIP, extra=xml)
    rng = np.random.default_rng([31337, deg, int(back), chunk])
    return a, [crest_try(sim, deg, back, rng, far) for _ in range(10)]


def curve():
    """each angle's outcomes over 40 tries a direction, no early stop: the pass rate the ladder's 20 tries sample"""
    J = [(n, d, b, c) for n in CURVE for d in (25, 30, 35, 40, 45, 50) for b in (False, True) for c in range(4)]
    with Pool(GG.WORKERS) as pool:
        R = pool.map(curve_job, J, chunksize=1)
    out = {}
    for (n, d, b, c), res in R:
        out.setdefault(n, {}).setdefault(d, {}).setdefault('back' if b else 'fwd', []).extend(res)
    for n in out:
        for d, s_ in out[n].items():
            print(n, d, '  '.join(f"{k}: {sum(r == 'ok' for r in v)}/{len(v)}" for k, v in s_.items()), flush=True)
    os.makedirs(OUT, exist_ok=True); json.dump(out, open(os.path.join(OUT, 'curve.json'), 'w'), indent=1)


def check():
    import knobs as K
    sp = K.make(K.T3); t0 = time.time()
    for deg in (20, 35, 50):
        xml, far = ridge(deg); sim = GG.Sim(sp, GRIP, extra=xml); rng = np.random.default_rng(1)
        print(deg, 'forward', [crest_try(sim, deg, False, rng, far) for _ in range(3)], 'reverse', [crest_try(sim, deg, True, rng, far) for _ in range(2)],
              f'{time.time() - t0:.1f} s', flush=True)
    low = K.make(dict(K.T3, clr=15.0))
    for deg in (20, 35):
        xml, far = ridge(deg); sim = GG.Sim(low, GRIP, extra=xml); rng = np.random.default_rng(1)
        print('ride 15', deg, [crest_try(sim, deg, False, rng, far) for _ in range(3)], flush=True)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'check': check, 'read': read, 'curve': curve}.get(cmd, lambda: print(__doc__))()
