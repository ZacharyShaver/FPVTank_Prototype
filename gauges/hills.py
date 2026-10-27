"""Hill gauges, proposed (2026-10-27): how steep a slope a design drives up (G4) and down (G5) before it tips or slides,
read on the shape study's designs with every other knob locked; the tail's pose on the hill is the new knob.

    SCORPION_SEARCH=search_shape python gauges/hills.py rollover   # is a sharp-turn gauge worth building?
    SCORPION_SEARCH=search_shape python gauges/hills.py read       # the finalists, references and controls, both hills
    SCORPION_SEARCH=search_shape python gauges/hills.py tail       # T3 with the tail held at each pose on the hill
    SCORPION_SEARCH=search_shape python gauges/hills.py shape      # the shape knobs one at a time, on the hills
    SCORPION_SEARCH=search_shape python gauges/hills.py height     # T3 with 1 kg at four heights, stowed and braced
      -> gauges/out/search_shape/hills_*.json
    SCORPION_SEARCH=search_hills python gauges/hills.py sweep      # wheels and packs unlocked: one knob at a time
    SCORPION_SEARCH=search_hills python gauges/hills.py search     # ... searched for the descent (B, then refine)
    SCORPION_SEARCH=search_hills python gauges/hills.py rehill     # the screens' hills read again after a hill change
    SCORPION_SEARCH=search_hills python gauges/hills.py finals     # the price list on the full gauges
      -> gauges/out/search_hills/*

The slope is the floor with gravity tipped by its angle (+X uphill), so the floor, its friction and the robot's frame
are the gauges' own. "Before falling" is read on a grippy floor (friction x2.5, rock or rough ground), where the tyres
hold and the design's own limit, tipping, binds. On the band's floors (x0.65 to x1.5) every design, the box too, slid
first at 25-30 degrees (the first reading, 2026-10-27), so the band's worst can't tell designs apart: it is read beside
as the slide limit, mostly the tyres'. A try starts at rest, square on +-10 degrees, and drives at V_HILL forwards or
in reverse (the better counts, as on the step), the set speed ramped up over 1 s. Started at full torque instead, the
geared-down drive reared the robot over on launch, and 1 kg high at its back read higher (the weight slowed the
launch): the controls failed. With the soft start they read lower, as they must. It passes when it has gone HILL_MM along the slope with its tilt from the slope's
normal under 30 degrees, and, coming down, never faster than twice the set speed. A tilt past 60 degrees is a tip.
"""
import os, sys, json, math, time, pickle
os.environ.setdefault('SCORPION_SEARCH', 'search_shape')
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gauges as GG, robots as RB, search as S

ANGLES = tuple(range(5, 80, 5))           # degrees
GRIP = 2.5                                # the floor's friction scale for the tip limit: grippy enough that nothing slides first
V_HILL, T_HILL, HILL_MM, RAMP = 0.5, 8.0, 2500.0, 1.0  # m/s, s, mm, s: the set speed ramps up over RAMP (a soft start).
# 300 mm until 2026-10-27's hills run: T3 passed 45 degrees down, 3 past its static tip, toppling too slowly to finish
# in 300 mm (its uphill wheels already off). A stop and a 1 s hold instead failed every design from 35 degrees: at
# a set speed of 0 the wheels back-drive and creep (40 mm/s at 35), which reads the speed loop, not the design. Then
# 800 mm, until the hills run's finals: its search parked designs 0.3-0.9 degrees past their tip angle, mid-topple at
# 800 mm (5-20 degrees of tilt, under UP_OK) and over by 1-1.9 m. At constant speed the static tip angle is the exact
# limit with the tail stowed, so no stowed reading may beat it (static_check).
TIP, UP_OK = 60.0, 30.0                   # degrees from the slope's normal: going over; on its wheels
SP = None


def _init(specs):
    global SP
    SP = specs


def tilt(sim):
    return math.degrees(math.acos(max(-1.0, min(1.0, sim.rot()[2, 2]))))


def hill_try(sim, deg, down, back, rng, th=None):
    """one try: 'ok', 'tipped', 'slid' or 'stalled'"""
    sp, m, d = sim.sp, sim.m, sim.d; a = math.radians(deg); g = 9.81
    m.opt.gravity[:] = (-g * math.sin(a), 0.0, -g * math.cos(a))
    dx = -1.0 if down else 1.0                                            # the way it travels along X
    yaw = math.radians(rng.uniform(-10, 10)) + (0.0 if (dx > 0) != back else math.pi)
    sim.place(GG.yaw_quat(yaw), 0.0005)
    if sim.limb and th is not None:
        sim.limb_goal(0.0, math.radians(th))
    u0 = (-1.0 if back else 1.0) * min(V_HILL / (sim.w0 * sp['R'] * 1e-3), 1.0); x0 = d.xipos[sim.rid][0]; skid = 0.0
    for k in range(int(T_HILL * 1000 / GG.TICK)):
        u = u0 * min(1.0, k * GG.TICK / 1000 / RAMP)
        sim.drive(u, u); t_ = tilt(sim); gone = dx * (d.xipos[sim.rid][0] - x0)
        if t_ > TIP:
            return 'tipped'
        if down:                                                          # skidding: the body outruns its wheels' rims for 0.2 s
            skid = skid + GG.TICK / 1000 if dx * d.qvel[0] - np.abs(d.qvel[sim.jw]).mean() * sp['R'] * 1e-3 > 0.15 else 0.0
            if skid >= 0.2 or dx * d.qvel[0] > 2 * V_HILL:
                return 'slid'
        if gone >= HILL_MM * 1e-3:
            return 'ok' if t_ < UP_OK else 'tipped'
    return 'slid' if dx * (d.xipos[sim.rid][0] - x0) < -0.05 else 'stalled'


def static_check(rows):
    """the rows (tail stowed) whose hill reading beats their static tip angle: none may, since at constant speed the
    static angle is the exact limit. The control: the 800 mm readings, which do."""
    return [r for r in rows if r.get('h_down') is not None and max(r['h_up'], r['h_down']) > r['tip_static'] + 0.5]


def ladder(sp, mu, down, n, seed, th=None):
    """the steepest slope passed in n tries (at least 0.9 n) in the better direction, every gentler one passing; and
    each angle's outcomes"""
    sim = GG.Sim(sp, mu); need = math.ceil(0.9 * n); top = 0; seen = {}
    for deg in ANGLES:
        best = None
        for back in (False, True):
            rng = np.random.default_rng([seed, deg, int(back)]); res = []
            for _ in range(n):
                res.append(hill_try(sim, deg, down, back, rng, th))
                if sum(r != 'ok' for r in res) > n - need:
                    break
            ok = sum(r == 'ok' for r in res) >= need
            cnt = {k: res.count(k) for k in set(res)}
            if best is None or ok:
                best = (ok, cnt)
            if ok:
                break
        seen[deg] = best[1]
        if not best[0]:
            break
        top = deg
    return top, seen


def job(a):
    i, down, mu, n, seed, th = a
    return a, ladder(SP[i], mu, down, n, seed, th)


def add_mass(sp, g, p, name):
    """the spec with g grams at p (mm, body frame): the hills' control"""
    M, c = sp['M'], sp['com']; M2 = M + g; c2 = (M * c + g * np.asarray(p, float)) / M2; d0, d1 = c - c2, np.asarray(p, float) - c2
    I = sp['I'] + M * (d0 @ d0 * np.eye(3) - np.outer(d0, d0)) + g * (d1 @ d1 * np.eye(3) - np.outer(d1, d1))
    return RB.dims(dict(sp, name=name, M=M2, com=c2, I=I, notes=list(sp['notes']) + [f'{g:.0f} g at {np.round(p).tolist()}']))


def run(specs, ths, n, tag, bands=GG.BAND + (GRIP,)):
    """both hills for every spec, at each friction, for each tail pose in ths (None: stowed): the tip limit (at GRIP)
    and the slide limit (the band's worst)"""
    J = [(i, down, mu, n, 61 + i, th) for i in range(len(specs)) for down in (False, True) for mu in bands for th in ths]
    J.sort(key=lambda a: -SP_COST(specs[a[0]]))
    t0 = time.time()
    with Pool(GG.WORKERS, initializer=_init, initargs=(specs,)) as pool:
        R = pool.map(job, J, chunksize=1)
    out = []
    for i, sp in enumerate(specs):
        for th in ths:
            row = dict(name=sp['name'], th=th, mass=sp['mass'], com_z=float(S.com_all(sp)[2]), tip_static=tip_static(sp))
            for down, g in ((False, 'up'), (True, 'down')):
                by = {str(mu): r for (i_, d_, mu, _, _, t_), r in R if i_ == i and d_ == down and t_ == th}
                row[g + '_by_mu'] = {m: v[0] for m, v in by.items()}
                row[g + '_why'] = {m: v[1].get(v[0] + 5) for m, v in by.items()}   # how it failed the first slope it missed
                if str(GRIP) in by:
                    row[g] = by[str(GRIP)][0]                             # the gauge: the tip limit
                band = [m for m in by if m != str(GRIP)]
                if band:
                    row[g + '_slide'] = min(by[m][0] for m in band)
            out.append(row)
            print(f"{sp['name']:26s} tail {'stowed' if th is None else f'{th:.0f}':>6s}  UP {row.get('up')} ({row['up_why'].get(str(GRIP))}), "
                  f"band {row.get('up_slide')}  DOWN {row.get('down')} ({row['down_why'].get(str(GRIP))}), band {row.get('down_slide')}   "
                  f"by friction up {row['up_by_mu']} down {row['down_by_mu']}", flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), n=n, angles=ANGLES, rows=out), open(os.path.join(S.OUT, f'hills_{tag}.json'), 'w'), indent=1, default=str)
    print(f'{len(J)} ladders, {time.time() - t0:.0f} s')
    return out


def SP_COST(sp):
    return sp['mass']


def finals_specs():
    specs = {sp['name']: sp for sp in pickle.load(open(os.path.join(S.OUT, 'finals_specs.pkl'), 'rb'))}
    return specs


def read():
    """the finalists, the references and the box; the control: T3 with 1 kg high on its top over its CoM must read
    below T3 both ways. (1 kg high at the back or the nose read higher: the gauge takes the better direction, and
    with the weight at one end the robot climbs or comes down with that end uphill, where it steadies it.)"""
    sp = finals_specs(); T3 = sp['T3']
    top = float(T3['hulls'][0][:, 2].max())
    ctl = add_mass(T3, 1000.0, (float(T3['com'][0]), 0.0, top - 20.0), 'T3, 1 kg high on top')
    main, _ = GG.roster(True)
    L = [sp[k] for k in ('T3', 'T2', 'T1', 'T5 (its own skin)', 'T5 on the Trainer body')] + [main[0], main[1], ctl]
    return run(L, (None,), 20, 'read')                                      # the band and GRIP


def tail():
    """T3 with its tail held at each pose for the whole try (pitch, degrees: 0 back level, 90 up, 180 forward over the
    body, negative down behind it), against stowed"""
    T3 = finals_specs()['T3']
    return run([T3], (None, -90.0, -60.0, -45.0, -30.0, -15.0, 0.0, 30.0, 60.0, 90.0, 140.0, 170.0), 20, 'tail', (GRIP,))


def height():
    """does the braced tail make the CoM's height matter less? T3 with 1 kg over its CoM at four heights, belly to
    top, stowed and at HELD, at GRIP and x1. (The packs' knob moved the CoM only 4 mm, so it can't answer this.)"""
    T3 = finals_specs()['T3']; zs = T3['hulls'][0][:, 2]; G = S.com_all(T3)
    L = [T3] + [add_mass(T3, 1000.0, (float(T3['com'][0]), 0.0, z), f'T3, 1 kg at z {z:.0f}')
                for z in (float(zs.min()) + 10.0, float(G[2]), float(G[2]) + 50.0, float(zs.max()) - 20.0)]
    for sp in L:
        print(f"{sp['name']:22s} CoM z {S.com_all(sp)[2]:.1f}  static tip {tip_static(sp):.1f}", flush=True)
    return run(L, (None,) + HELD, 20, 'height', (1.0, GRIP))


def side_try(sim, deg, rng, yaw_t=None, th=None):
    """one try across a slope (exploratory, 2026-10-27): downhill is -Y, it drives +X holding its heading (a
    proportional steer); 'ok' after HILL_MM along its heading with its tilt under UP_OK, 'tipped', 'slid' (300 mm
    down the slope, across its heading: the first version counted the start's +-10 degree heading as sliding, and
    every design read 0) or 'stalled'. yaw_t, th: the tail held there (yaw 90 points it down the slope: an outrigger)"""
    sp, m, d = sim.sp, sim.m, sim.d; a = math.radians(deg); g = 9.81
    m.opt.gravity[:] = (0.0, -g * math.sin(a), -g * math.cos(a))
    yaw0 = math.radians(rng.uniform(-10, 10)); sim.place(GG.yaw_quat(yaw0), 0.0005)
    if sim.limb and th is not None:
        sim.limb_goal(math.radians(yaw_t), math.radians(th))
    u0 = min(V_HILL / (sim.w0 * sp['R'] * 1e-3), 1.0); x0, y0 = d.xipos[sim.rid][:2]
    for k in range(int(T_HILL * 1000 / GG.TICK)):
        Rm = sim.rot(); e = (math.atan2(Rm[1, 0], Rm[0, 0]) - yaw0 + math.pi) % (2 * math.pi) - math.pi
        u = u0 * min(1.0, k * GG.TICK / 1000 / RAMP); c = u0 * max(-0.5, min(0.5, 2.0 * e))
        sim.drive(u + c, u - c); t_ = tilt(sim)
        if t_ > TIP:
            return 'tipped'
        dx, dy = d.xipos[sim.rid][0] - x0, d.xipos[sim.rid][1] - y0         # along its heading, and across it (+ uphill)
        if dx * math.sin(yaw0) - dy * math.cos(yaw0) > 0.3:
            return 'slid'
        if dx * math.cos(yaw0) + dy * math.sin(yaw0) >= HILL_MM * 1e-3:
            return 'ok' if t_ < UP_OK else 'tipped'
    return 'stalled'


def side_ladder(sp, mu, n, seed, yaw_t=None, th=None):
    """the steepest side slope passed in at least 0.9 n of n tries, every gentler one passing; each angle's outcomes"""
    sim = GG.Sim(sp, mu); need = math.ceil(0.9 * n); top = 0; seen = {}
    for deg in ANGLES:
        rng = np.random.default_rng([seed, deg, 7]); res = []
        for _ in range(n):
            res.append(side_try(sim, deg, rng, yaw_t, th))
            if sum(r != 'ok' for r in res) > n - need:
                break
        seen[deg] = {k: res.count(k) for k in set(res)}
        if sum(r == 'ok' for r in res) < need:
            break
        top = deg
    return top, seen


def side_static(sp):
    """the static side tip angle, degrees: the CoM's reach to the downhill tyres' outer edge over its height"""
    G = S.com_all(sp); yo = max(abs(y) for _, y in sp['wheels']) + sp['TW'] / 2
    return math.degrees(math.atan2(yo - abs(G[1]), G[2]))


def shape(n_val=7, bands=(GRIP,)):
    """the shape knobs one at a time on the hills' tip limits, the rest at T3's shape, the tail stowed"""
    T3 = finals_specs()['T3']; z3 = S.to_z(T3['x']); L = [T3]
    for j, k in enumerate(S.ZK):
        for v in np.linspace(S.ZLO[j], S.ZHI[j], n_val):
            z = z3.copy(); z[j] = v; sp = S.build(S.to_x(z), name=f'{k}={v:.4g}')
            if sp is not None:
                L.append(sp)
    return run(L, (None, -30.0), 6, 'shape', bands)                       # stowed, and braced behind (the best uphill pose)


# ---------- the hills run (SCORPION_SEARCH=search_hills, 2026-10-27) ----------
# The wheels' size, centre and gap and the packs' place unlocked, the rest held at T3's (search.py). The screen is the
# lean screen and, above its bar, both hills' tip limits at GRIP in N_SCREEN tries, the tail stowed. Three refinements:
# the descent alone; the descent keeping T3's step and turn (KEEP); both hills, keeping them.
N_SCREEN = 6
KEEP = (140, 420)                         # mm: T3's step (150) within 10 mm, its turn (381) within 10 %
W_H = ('down', 'down, kept', 'both, kept')
HELD = (-30.0, -15.0, 0.0)                # the tail's hill poses the finals read: on the 800 mm hill, T3 reads 45 / 45 at each


def tip_static(sp):
    """the static tip angle, degrees: the better end, atan of the CoM's reach past that axle over its height"""
    G = S.com_all(sp); xs = [x for x, _ in sp['wheels']]
    return math.degrees(math.atan2(max(max(xs) - G[0], G[0] - min(xs)), G[2]))


def screen(a):
    """(tag, z, seed[, cut]) -> tag, x, the lean screen's row with the hills' tip limits (h_up, h_down) and how each
    failed the next slope"""
    tag, z, seed = a[:3]; cut = a[3] if len(a) > 3 else True
    _, x, s = S._screen_lean((tag, z, seed, S.FROZEN, cut))
    if s is None:
        return tag, x, None
    sp = S.build(np.array(x)); s['tip_static'] = tip_static(sp); s['com_x'], _, s['com_z'] = map(float, S.com_all(sp))
    for down, g in ((False, 'h_up'), (True, 'h_down')):
        s[g], s[g + '_why'] = None, None
        if not s['cut']:
            top, seen = ladder(sp, GRIP, down, N_SCREEN, seed)
            s[g], s[g + '_why'] = top, seen.get(top + 5)
    return tag, x, s


def score_h(r, w):
    """the refinement's score: under -1e8 is infeasible. A design that misses KEEP ranks by how far it misses (mm),
    so a kept run that starts with one feasible design (B had only T3) is steered back toward them."""
    if r['up'] < S.UP_SCREEN or r['turn'] is None or r.get('h_down') is None:
        return -1e9
    if 'kept' in w and (r['climb'] < KEEP[0] or r['turn'] > KEEP[1]):
        return -2e8 - max(0.0, KEEP[0] - r['climb']) - max(0.0, r['turn'] - KEEP[1])
    return (r['h_up'] if w.startswith('both') else 0) + r['h_down'] + 0.01 * r['tip_static']   # the static angle breaks ties


def sweep(n_val=7, seeds=3):
    """the five unlocked knobs one at a time across their ranges, the rest at T3's, without the cut, seeds seeds each.
    Writes hills_sweep.json."""
    z3 = np.array([S.T3_PLAT[k] for k in S.ZK]); jobs = [('T3|0', z3, 85000 + s_, False) for s_ in range(seeds)]
    for j, k in enumerate(S.ZK):
        for v in np.linspace(S.ZLO[j], S.ZHI[j], n_val):
            z = z3.copy(); z[j] = v; jobs += [(f'{k}|{v:.6g}', z, 85000 + s_, False) for s_ in range(seeds)]
    t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(screen, jobs, chunksize=1)
    out = {}
    for tag, x, s in R:
        k, v = tag.split('|'); out.setdefault(k, {}).setdefault(float(v), []).append(s)
    res = {}
    for k, vs in out.items():
        res[k] = []
        for v, ss in sorted(vs.items()):
            ss = [q for q in ss if q is not None]
            m = lambda g: float(np.mean([np.nan if q[g] is None else q[g] for q in ss]))
            res[k].append(dict(v=v, **{g: m(g) for g in ('up', 'climb', 'turn', 'h_up', 'h_down', 'tip_static', 'com_x', 'com_z', 'mass', 'length')},
                               h_down_min=min(q['h_down'] for q in ss), h_up_min=min(q['h_up'] for q in ss),
                               why_down=[q['h_down_why'] for q in ss], why_up=[q['h_up_why'] for q in ss]))
        print(f'{k:4s} ' + '  '.join(f"{r['v']:.3g}: {r['up']:.2f}/{r['climb']:.0f}/{r['turn']:.0f} hills {r['h_up']:.0f}/{r['h_down']:.0f} "
                                     f"(static {r['tip_static']:.0f})" for r in res[k]), flush=True)
    os.makedirs(S.OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), seeds=seeds, t3=S.T3_PLAT, ranges={k: (a, b) for k, a, b in S.SPACE}, results=res),
              open(os.path.join(S.OUT, 'hills_sweep.json'), 'w'), indent=1, default=float)
    print(f'{len(jobs)} screens, {time.time() - t0:.0f} s')


def search(n_b=256, gens=8, pop=60):
    """B: n_b Sobol designs over the five knobs and T3, on the hills screen; then refine()."""
    os.makedirs(S.OUT, exist_ok=True); t0 = time.time()
    from scipy.stats import qmc
    Z = qmc.scale(qmc.Sobol(len(S.ZK), scramble=True, seed=19).random_base2(int(math.ceil(math.log2(n_b)))), S.ZLO, S.ZHI)[:n_b]
    z3 = np.array([S.T3_PLAT[k] for k in S.ZK])
    with Pool(GG.WORKERS) as pool:
        allr = S.run_screens([('B', z, 40000) for z in Z] + [('T3', z3, 40000)], 'B', pool, screen)
    t3 = next(r for r in allr if r['tag'] == 'T3')
    print(f"B: {len(allr)} screened, {time.time() - t0:.0f} s; {sum(not r['cut'] for r in allr)} above the bar; T3 {t3['up']:.2f}/{t3['climb']}/"
          f"{round(t3['turn'])} hills {t3['h_up']}/{t3['h_down']}; best down {max((r['h_down'] or 0) for r in allr)}", flush=True)
    refine(gens, pop)


def refine(gens=8, pop=60):
    """after B: S, the sweep's best single change that keeps T3's step and turn (bigger wheels, R 50-60) as seeds;
    C, cross-entropy under each of W_H from everything screened. Writes search.json (the best five under each)."""
    t0 = time.time(); allr = [json.loads(l) for l in open(os.path.join(S.OUT, 'screen_B.jsonl'))]
    z3 = np.array([S.T3_PLAT[k] for k in S.ZK]); Zs = []
    for R in (50.0, 55.0, 60.0):
        z = z3.copy(); z[S.ZK.index('R')] = R; Zs.append(z)
    with Pool(GG.WORKERS) as pool:
        Ss = S.run_screens([('S', z, 40000) for z in Zs], 'S', pool, screen); allr += Ss
        print(f"S: {[(r['h_up'], r['h_down'], r['climb'], round(r['turn'])) for r in Ss]} (R 50, 55, 60)", flush=True)
        rng = np.random.default_rng(37); gens_run = {}
        for j, w in enumerate(W_H):
            new, gens_run[w] = S.cem(allr, w, pool, rng, 'C', 50000 + 100 * j, gens, pop, t0, fn=screen, sc=score_h); allr += new
    best = {w: sorted(allr, key=lambda r: -score_h(r, w))[:5] for w in W_H}
    json.dump(dict(wall_s=round(time.time() - t0), n=len(allr), gens=gens_run, best=best), open(os.path.join(S.OUT, 'search.json'), 'w'), indent=1, default=float)
    for w in W_H:
        print(w, [(r['h_up'], r['h_down'], r['climb'], round(r['turn']), round(r['up'], 2), np.round(r['z'], 1).tolist()) for r in best[w]])


def _rehill(a):
    t, i, x, seed = a; sp = S.build(np.array(x)); out = {}
    for down, g in ((False, 'h_up'), (True, 'h_down')):
        top, seen = ladder(sp, GRIP, down, N_SCREEN, seed)
        out[g], out[g + '_why'] = top, seen.get(top + 5)
    return t, i, out


def rehill():
    """the screened rows' hills read again on the current hill (2500 mm, 2026-10-27), in place, each design on the same
    yaws; the 800 mm readings kept as h_up_800 and h_down_800, the old files as 'superseded - screen_*_800mm.jsonl'.
    static_check must then find none."""
    import shutil
    t0 = time.time(); files = {t: [json.loads(l) for l in open(os.path.join(S.OUT, f'screen_{t}.jsonl'))] for t in ('B', 'S', 'C')}
    jobs = [(t, i, r['x'], 40000) for t, rows in files.items() for i, r in enumerate(rows) if r.get('h_down') is not None]
    with Pool(GG.WORKERS) as pool:
        R = pool.map(_rehill, jobs, chunksize=1)
    for t, i, out in R:
        r = files[t][i]; r['h_up_800'], r['h_down_800'] = r['h_up'], r['h_down']; r.update(out)
    for t, rows in files.items():
        fp = os.path.join(S.OUT, f'screen_{t}.jsonl'); shutil.copy(fp, os.path.join(S.OUT, f'superseded - screen_{t}_800mm.jsonl'))
        with open(fp, 'w') as f:
            for r in rows:
                f.write(json.dumps(r, default=float) + '\n')
    allr = [r for rows in files.values() for r in rows]
    moved = [r for r in allr if r.get('h_down') is not None and (r['h_up'], r['h_down']) != (r['h_up_800'], r['h_down_800'])]
    print(f"{len(jobs)} designs read again, {time.time() - t0:.0f} s; {len(moved)} changed; beating their static angle now "
          f"{len(static_check(allr))} (on 800 mm: {len(static_check([dict(r, h_up=r.get('h_up_800'), h_down=r.get('h_down_800')) for r in allr]))})", flush=True)


def finals(levels=(45, 50, 55, 60)):
    """the price list: at each descent in levels, the screened design that steps highest (ties: the smaller turn), and
    the best on both hills keeping T3's step and turn; on the full gauges (G1-G3: 200 falls, 20 tries a step) and both
    hills (20 tries, the band and GRIP, the tail stowed and held at each of HELD); with T3 and the box, and the steepest
    descender with 1 kg high on its top, which must read lower on the hills. Writes finals.json."""
    rows = [json.loads(l) for t in ('B', 'S', 'C') for l in open(os.path.join(S.OUT, f'screen_{t}.jsonl'))]
    ok = [r for r in rows if score_h(r, 'down') > -1e8]
    pick = []
    for lv in levels:
        c = [r for r in ok if r['h_down'] >= lv]
        if c:
            top = max(r['climb'] for r in c)
            pick.append((min((r for r in c if r['climb'] >= top - 10), key=lambda r: r['turn']), f'down {lv}, the best step'))
    both = max(rows, key=lambda r: score_h(r, 'both, kept'))
    if all(np.abs((np.array(both['z']) - np.array(o['z'])) / (S.ZHI - S.ZLO)).max() > 0.02 for o, _ in pick):
        pick.append((both, 'both, kept'))
    specs = [S.build(np.array(r['x']), name=f'H{i + 1}') for i, (r, _) in enumerate(pick)]
    T3 = S.build(S.to_x(np.array([S.T3_PLAT[k] for k in S.ZK])), name='T3'); best = specs[max(i for i, (_, w) in enumerate(pick) if w.startswith('down'))]   # the steepest descender
    top = float(best['hulls'][0][:, 2].max())
    ctl = add_mass(best, 1000.0, (float(best['com'][0]), 0.0, top - 20.0), f"{best['name']}, 1 kg high on top")
    main, _ = GG.roster(True); allsp = [main[0], T3] + specs; t0 = time.time()
    J = [j for i in range(len(allsp)) for j in GG.jobs_for(i, GG.N_DROP, GG.N_TRY, seed=31)]
    J.sort(key=lambda a: a[0] != 'climb')
    with Pool(GG.WORKERS, initializer=GG._init, initargs=(allsp,)) as pool:
        R = pool.map(GG.job, J, chunksize=1)
    H = run(allsp + [ctl], (None,) + HELD, 20, 'finals')
    out = []
    for i, sp in enumerate(allsp + [ctl]):
        g = GG.collect(R, i, GG.N_TRY) if i < len(allsp) else None
        h = {('stowed' if r['th'] is None else f"held {r['th']:.0f}"): r for r in H if r['name'] == sp['name']}
        h['held'] = max((r for r in H if r['name'] == sp['name'] and r['th'] is not None), key=lambda r: (min(r['up'], r['down']), r['up'] + r['down']))
        scr = pick[i - 2] if i >= 2 and i < len(allsp) else None
        out.append(dict(name=sp['name'], x=sp.get('x'), z=None if scr is None else scr[0]['z'], refinement=None if scr is None else scr[1],
                        screen=None if scr is None else {k: scr[0].get(k) for k in ('up', 'climb', 'turn', 'h_up', 'h_down', 'tip_static', 'tag')},
                        worst=None if g is None else g['worst'], by_mu=None if g is None else g['by_mu'], hills=h, tip_static=tip_static(sp),
                        control=sp is ctl, notes=sp['notes'], dims={k: sp[k] for k in ('mass', 'length', 'width', 'height', 'belly', 'R')}))
        w = out[-1]['worst']; hs, hb = h['stowed'], h['held']
        print(f"{sp['name']:22s} " + (f"upright {w['upright']:.3f} step {w['climb']} turn {w['turn'] and round(w['turn'])}  " if w else '') +
              f"hills {hs['up']}/{hs['down']} (tail held at {hb['th']:.0f}: {hb['up']}/{hb['down']}; slide {hs.get('up_slide')}/{hs.get('down_slide')}) static {tip_static(sp):.0f}  "
              f"{sp['mass']:.0f} g {sp['length']:.0f} x {sp['width']:.0f}  z {out[-1]['z'] and np.round(out[-1]['z'], 1).tolist()}", flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), finals=out), open(os.path.join(S.OUT, 'finals.json'), 'w'), indent=1, default=float)


def rollover():
    """the hardest turn a skid steer can make, from full speed: one side on full, the other full back, and one side on
    full, the other stopped; the most tilt and the end state. T3 against T3 geared 0.4 (5x faster) with 1 kg on its
    top, which should go over if anything does."""
    T3 = finals_specs()['T3']; top = float(T3['hulls'][0][:, 2].max())
    fast = add_mass(dict(T3, motor=dict(T3['motor'], w0=T3['motor']['w0'] * 2.091 / 0.4, stall=T3['motor']['stall'] * 0.4 / 2.091)),
                    1000.0, (0.0, 0.0, top - 20.0), 'T3 geared 0.4, 1 kg on top')
    for sp in (T3, fast):
        for mu in GG.BAND:
            for turn, (uL, uR) in (('spin', (1.0, -1.0)), ('arc', (1.0, 0.0))):
                sim = GG.Sim(sp, mu); sim.place(GG.yaw_quat(0.0), 0.0005); worst = 0.0; vmax = 0.0
                for k in range(int(3.0 * 1000 / GG.TICK)):
                    t = k * GG.TICK / 1000
                    sim.drive(*((1.0, 1.0) if t < 1.5 else (uL, uR))); worst = max(worst, tilt(sim)) if t >= 1.5 else worst
                    vmax = max(vmax, abs(sim.d.qvel[0]))
                print(f"{sp['name']:28s} x{mu} {turn:4s}: top speed {vmax:.2f} m/s, most tilt in the turn {worst:5.1f} deg, ends {GG.classify(sim.rot())}", flush=True)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'rollover': rollover, 'read': read, 'tail': tail, 'shape': shape, 'sweep': sweep, 'search': search, 'refine': refine, 'rehill': rehill,
     'finals': finals, 'height': height}.get(cmd, lambda: print(__doc__))()
