"""The capability search (2026-10-28): every knob free at once, every gauge pushed as far as it goes, no weights.
Zach: "max out every single goal dont set the percentages. targets should go as high or low as they can in each direction
were shooting to test out the capability of this project so we can learn from the results" (done before 5 pm).

    python gauges/capability.py smoke    # two designs, two tries a rung: it runs end to end, and how long a screen takes
    python gauges/capability.py run      # B, then refinement until DEADLINE, then the finals -> gauges/out/capability/
    python gauges/capability.py finals   # the finals again from the screens on disk

The space is the knob log's (gauges/knobs.py), around nothing: every knob over its whole range, plus three switches (a
tail, six wheels, a skin over the Trainer's body). Held: the two dead knobs (knobs.DEAD, dropped 2026-10-28) and the
tread's grip (a property to measure, not a design choice; the sim's value is a guess and every gauge would take more).

A screen reads all seven gauges, 6 tries a rung: G1 from 60 falls (x1.5 and x0.65, no cut), G2's ladder at x0.65 and
x1.5, G3 at the band, both hills at x2.5 stowed and braced (-30 and -15, the better), the crest at x2.5, the push over
the band. **G2's ladder runs past its 150 mm top here** (to 300 mm, 25 mm rungs above 150), because T3 and T5 already
top it out; the gauge itself is unchanged. B is 1,024 Sobol designs; then eight cross-entropy streams share every
screened design: one per gauge (that gauge alone, ties broken by the all-rounder rank) and one all-rounder (the worst
of its seven percentile ranks among everything screened: a balance with no weights). Rounds run until DEADLINE. The
finals, read on the full gauges (and the same long ladder): each stream's best, the all-rounders at the top of the
seven-way front, T3 and the box.
"""
import os, sys, json, math, time, datetime, zlib
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')                # as knobs.py, whose make() builds the designs
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import gauges as GG, search as S, hills as H, crest as C, push as P, knobs as K

OUT = os.path.join(config.GAUGES_OUT, 'capability')
SCREENS = os.path.join(OUT, 'screens.jsonl')
DEADLINE = datetime.datetime(2026, 10, 28, 15, 15)                       # the last refinement round must end by then
HEIGHTS_EXT = tuple(range(10, 160, 10)) + tuple(range(175, 301, 25))    # past G2's 150 mm top, for this run only
HELD_K = K.DEAD + ('tyre_mu',)
SPACE = [(k, lo, hi) for _, k, lo, hi, _ in K.KNOBS if k not in HELD_K] + [('limb', 0.0, 1.0), ('six', 0.0, 1.0), ('shell', 0.0, 1.0)]
KEYS = [k for k, _, _ in SPACE]; LO = np.array([a for _, a, _ in SPACE]); HI = np.array([b for _, _, b in SPACE])
GAUGES = (('up', 1), ('climb', 1), ('turn', -1), ('h_up', 1), ('h_down', 1), ('crest', 1), ('push', 1))
STREAMS = tuple(g for g, _ in GAUGES) + ('all',)
N_SCREEN, N_B, POP, ELITE = 6, 1024, 30, 8


def q_of(z):
    """a point of [0, 1]^d as the knobs make() takes; the switches as on/off (limb above search.LIMB_ON is a tail)"""
    q = dict(K.T3); q.update({k: float(lo + v * (hi - lo)) for (k, lo, hi), v in zip(SPACE, z)})
    q['six'] = 1.0 if q['six'] > 0.5 else 0.0; q['shell'] = 1.0 if q['shell'] > 0.5 else 0.0
    q['limb'] = 1.0 if q['limb'] > 0.5 else 0.0
    return q


def _init():
    GG.HEIGHTS = HEIGHTS_EXT


def screen(sp, seed, n=N_SCREEN):
    s = S.screen_lean(sp, seed, cut=False); G0 = S.com_all(sp)
    r = dict(up=s['up'], climb=s['climb'], turn=s['turn'], mass=sp['mass'], length=sp['length'], width=sp['width'],
             height=sp['height'], belly=sp['belly'], com_x=float(G0[0]), com_z=float(G0[2]), tail=bool(sp.get('limb')),
             wheels=len(sp['wheels']), tip_static=H.tip_static(sp))
    poses = (None,) + (K.BRACE if sp.get('limb') else ())
    for down, g in ((False, 'h_up'), (True, 'h_down')):
        by = {th: H.ladder(sp, H.GRIP, down, n, seed, th)[0] for th in poses}
        r[g] = max(by.values()); r[g + '_stowed'] = by[None]
    r['crest'] = C.ladder(sp, C.GRIP, n, seed)[0]
    pu = {mu: P.ladder(sp, mu, n, seed)[0] for mu in GG.BAND}
    r['push'] = min(pu.values()); r['push_by_mu'] = {str(m): v for m, v in pu.items()}
    return r


def job(a):
    tag, z, seed, n = a
    t0 = time.time(); q = q_of(z)
    try:
        sp = K.make(q)
        r = None if sp is None else screen(sp, seed, n)
    except Exception as e:                                                # one bad design must not stop the run
        return dict(tag=tag, z=list(map(float, z)), seed=seed, err=f'{type(e).__name__}: {e}'[:300])
    return dict(tag=tag, z=list(map(float, z)), seed=seed, q={k: q[k] for k in KEYS}, s=round(time.time() - t0, 1), **(r or dict(built=False)))


# ---------- scoring ----------
def val(r, g):
    """a gauge's reading, larger better; None when the design wasn't built or can't spin"""
    if r.get('built') is False or 'err' in r:
        return None
    v = r.get(g)
    return None if v is None else (-v if g == 'turn' else float(v))


def ranks(rows):
    """each design's percentile rank on each gauge among all built designs (0 worst, 1 best; ties share the mean), and
    the all-rounder rank: the worst of its seven"""
    ok = [r for r in rows if val(r, 'up') is not None]
    R = {}
    for g, _ in GAUGES:
        v = np.array([val(r, g) if val(r, g) is not None else -1e9 for r in ok])
        order = v.argsort(kind='stable'); rk = np.empty(len(v)); rk[order] = np.arange(len(v))
        for u in np.unique(v):                                            # ties share their mean rank
            m = v == u; rk[m] = rk[m].mean()
        R[g] = rk / max(1, len(v) - 1)
    for i, r in enumerate(ok):
        r['rank'] = {g: float(R[g][i]) for g, _ in GAUGES}; r['rank']['all'] = min(r['rank'].values())
    return ok


def score(r, stream):
    if 'rank' not in r:
        return -1e18
    if stream == 'all':
        return r['rank']['all']
    v = val(r, stream)
    return -1e18 if v is None else v + 1e-3 * r['rank']['all']          # ties (the ladder tops) go to the better all-rounder


def front(rows):
    """the designs no other beats on all seven gauges at once (each at least as good, one better)"""
    ok = [r for r in rows if all(val(r, g) is not None for g, _ in GAUGES)]
    V = np.array([[val(r, g) for g, _ in GAUGES] for r in ok])
    keep = [i for i in range(len(ok)) if not np.any(np.all(V >= V[i], axis=1) & np.any(V > V[i], axis=1))]
    return [ok[i] for i in keep]


# ---------- the run ----------
def load():
    return [json.loads(l) for l in open(SCREENS)] if os.path.isfile(SCREENS) else []


def run_jobs(pool, J, rows, fh, label):
    t0 = time.time(); n = 0
    for r in pool.imap_unordered(job, J, chunksize=1):
        rows.append(r); fh.write(json.dumps(r, default=float) + '\n'); fh.flush(); n += 1
        if n % 60 == 0 or n == len(J):
            print(f'{label}: {n}/{len(J)} screened, {time.time() - t0:.0f} s', flush=True)
    return time.time() - t0


def best_line(rows):
    ok = ranks(rows); out = []
    for st in STREAMS:
        b = max(ok, key=lambda r: score(r, st))
        out.append(f"{st} {'%.2f' % b['rank']['all'] if st == 'all' else (b.get(st) if st != 'up' else round(b['up'], 2))}")
    return '  '.join(out)


def run():
    os.makedirs(OUT, exist_ok=True); rows = load(); t_start = time.time()
    from scipy.stats import qmc
    Z0 = qmc.Sobol(len(KEYS), scramble=True, seed=53).random_base2(int(math.log2(N_B)))
    done = {r['tag'] for r in rows}
    with open(SCREENS, 'a') as fh, Pool(GG.WORKERS, initializer=_init) as pool:
        J = [(f'B{i}', z, 40000, N_SCREEN) for i, z in enumerate(Z0) if f'B{i}' not in done]
        if J:
            run_jobs(pool, J, rows, fh, 'B')
        print(f'B done: {len(rows)} screened, {sum(val(r, "up") is not None for r in rows)} built; best: {best_line(rows)}', flush=True)
        rng = np.random.default_rng(59); state = {}
        rnd = 1 + max([int(r['tag'].split('|')[1]) for r in rows if r['tag'].startswith('C|')] or [0])
        last = None
        while True:
            now = datetime.datetime.now()
            if last and now + datetime.timedelta(seconds=1.1 * last) > DEADLINE:
                print(f'round {rnd}: would end after {DEADLINE:%H:%M}; refinement stops', flush=True); break
            if now > DEADLINE:
                break
            ok = ranks(rows); J = []
            for st in STREAMS:
                el = sorted(ok, key=lambda r: -score(r, st))[:ELITE]; E = np.array([r['z'] for r in el])
                if st not in state:
                    state[st] = [E.mean(0), np.maximum(E.std(0), 0.05)]
                else:                                                     # as search.cem
                    mu, sd = state[st]; state[st] = [0.6 * E.mean(0) + 0.4 * mu, np.maximum(0.6 * E.std(0) + 0.4 * sd * 0.8, 0.02)]
                mu, sd = state[st]; Z = np.clip(mu + sd * rng.normal(size=(POP, len(KEYS))), 0.0, 1.0)
                J += [(f'C|{rnd}|{st}', z, 50000 + rnd, N_SCREEN) for z in Z]
            last = run_jobs(pool, J, rows, fh, f'round {rnd}')
            print(f'round {rnd} done ({last:.0f} s, {len(rows)} screened, {(time.time() - t_start) / 3600:.2f} h); best: {best_line(rows)}', flush=True)
            rnd += 1
    summarise(rows)
    finals()


def summarise(rows):
    ok = ranks(rows); F = front(ok)
    champs = {st: max(ok, key=lambda r: score(r, st)) for st in STREAMS}
    json.dump(dict(n=len(rows), built=len(ok), front_n=len(F), keys=KEYS, space=SPACE, held=list(HELD_K), heights=HEIGHTS_EXT,
                   champions={st: r for st, r in champs.items()}, front=sorted(F, key=lambda r: -r['rank']['all'])),
              open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=float)
    print(f'{len(rows)} screened, {len(ok)} built; the seven-way front holds {len(F)}', flush=True)
    for st, r in champs.items():
        print(f"  best {st:6s}: up {r['up']:.2f} step {r['climb']} turn {r['turn'] and round(r['turn'])} hills {r['h_up']}/{r['h_down']} "
              f"crest {r['crest']} push {r['push']} | all-rank {r['rank']['all']:.2f} | tail {r['tail']} wheels {r['wheels']} {r['mass']:.0f} g", flush=True)


# ---------- the finals ----------
def _finit(sp):
    import card
    GG.HEIGHTS = HEIGHTS_EXT; card._init(sp)


def finals(n_front=4):
    """each stream's best and the n_front best all-rounders on the front (not already picked), T3 and the box, read on
    the full gauges (card.py's reads; G1-G3 at 200 falls and 20 tries, G2's ladder to 300 mm)"""
    import card
    rows = load(); ok = ranks(rows); F = sorted(front(ok), key=lambda r: -r['rank']['all'])
    pick = {}
    for st in STREAMS:
        r = max(ok, key=lambda r: score(r, st)); pick.setdefault(r['tag'] + str(r['z'][:3]), (f'best {st}', r))
    for r in F:
        if sum(1 for n, _ in pick.values() if n.startswith('front')) >= n_front:
            break
        pick.setdefault(r['tag'] + str(r['z'][:3]), (f'front {sum(1 for n, _ in pick.values() if n.startswith("front")) + 1}', r))
    names, specs = [], []
    for nm, r in pick.values():
        sp = K.make(q_of(r['z'])); sp = dict(sp, name=nm); names.append(nm); specs.append(sp)
    main, _ = GG.roster(True); specs += [dict(K.make(K.T3), name='T3'), main[0]]; names += ['T3', 'Box']
    GG.HEIGHTS = HEIGHTS_EXT
    J = card.jobs(specs, set(names)); t0 = time.time()
    print(f'finals: {len(specs)} designs, {len(J)} jobs', flush=True)
    with Pool(GG.WORKERS, initializer=_finit, initargs=(specs,)) as pool:
        R = pool.map(card.job, J, chunksize=1)
    out = []
    for i, sp in enumerate(specs):
        g = GG.collect([x for x in R if x[0][0] in ('fall', 'climb', 'turn')], i, card.N_TRY); w = g['worst']
        r = card.row(R, i, sp)
        src = next((rr for nm, rr in pick.values() if nm == sp['name']), None)
        out.append(dict(name=sp['name'], up=w['upright'], climb=w['climb'], turn=w['turn'], h_up=r['up'], h_down=r['down'],
                        hill_pose=[r['up_pose'], r['down_pose']], h_up_stowed=r['up_stowed'], h_down_stowed=r['down_stowed'],
                        crest=r['crest'], push=r['push'], push_by_mu=r['push_by_mu'], by_mu=g['by_mu'], tip_static=r['tip_static'],
                        mass=sp['mass'], length=sp['length'], width=sp['width'], height=sp['height'], belly=sp['belly'],
                        tail=bool(sp.get('limb')), wheels=len(sp['wheels']), notes=sp['notes'],
                        q=src and src['q'], z=src and src['z'], screen=src and {k: src.get(k) for k, _ in GAUGES}))
        print(f"{sp['name']:12s} up {w['upright']:.3f} step {w['climb']} turn {w['turn'] and round(w['turn'])} hills {r['up']}/{r['down']} "
              f"crest {r['crest']} push {r['push']} | {sp['mass']:.0f} g, tail {bool(sp.get('limb'))}, {len(sp['wheels'])} wheels", flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), heights=HEIGHTS_EXT, finals=out), open(os.path.join(OUT, 'finals.json'), 'w'), indent=1, default=float)


def smoke():
    """two designs (T3's point and the centre of the space), two tries a rung, in the pool: the run works end to end"""
    zT = np.array([(K.T3[k] - lo) / (hi - lo) if k in K.T3 else 1.0 for k, lo, hi in SPACE])
    J = [('smoke|T3', np.clip(zT, 0, 1), 1, 2), ('smoke|mid', np.full(len(KEYS), 0.5), 1, 2)]
    t0 = time.time()
    with Pool(2, initializer=_init) as pool:
        for r in pool.imap_unordered(job, J):
            print(json.dumps({k: r.get(k) for k in ('tag', 'up', 'climb', 'turn', 'h_up', 'h_down', 'crest', 'push', 'tail', 'wheels', 'mass', 's', 'err', 'built')}, default=float), flush=True)
    print(f'{time.time() - t0:.0f} s; {len(KEYS)} knobs: {KEYS}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'smoke': smoke, 'run': run, 'finals': finals}.get(cmd, lambda: print(__doc__))()
