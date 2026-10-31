"""Front flippers on the step (2026-10-28). Zach: "flippers have got to be a future knob i bet they would help a lot with
the steps", then "build front flippers as a knob and test them on the step".

    python gauges/flippers.py run      # both arms, then their bests on the full ladder -> gauges/out/flippers/
    python gauges/flippers.py finals   # the finals again from the screens on disk

The flippers are robots.add_flippers, their move gauges.Reflex. A first look on T3 (gauges/README.md "Front flippers")
found no gain from hand-set flippers: lifting the front alone rears the robot up, and lifting it with the tail pushing
left it bridged on the flipper tips and the tail foot, wheels in the air. So the flippers' settings search instead,
with the wheels' size and wheelbase (T3 is at its wheelbase's limit, 152 mm against its 150 mm step), everything else
at T3's, every design built strict (knobs.make). Two arms on the same budget: with flippers, and without (the control:
what the wheel knobs alone buy). Score: G2's step on the ladder to 300 mm (capability.HEIGHTS_EXT, x0.65 and x1.5,
6 tries), with the turn held to TURN_CAP: big wheels buy step at the turn's cost (the capability search's 225 mm
stepper turns in 784 mm), and the question is whether flippers buy it without.
"""
import os, sys, json, math, time
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config, stamp
import gauges as GG, search as S, knobs as K, capability as CA

OUT = os.path.join(config.GAUGES_OUT, 'flippers')
PLAT = [('R', 35.0, 95.0), ('gap', 15.0, 150.0), ('xw', -80.0, 80.0)]
FLIP = [(k, lo, hi) for _, k, lo, hi, _ in K.FLIP_KNOBS] + [('f_nose', 0.0, 1.0), ('f_tail', 0.0, 1.0)]
ARMS = {'flippers': PLAT + FLIP, 'none': PLAT}
TURN_CAP = 450.0                          # mm: T3 turns in 381-392
N_B, GENS, POP, ELITE = 64, 5, 20, 6
WORKERS = int(os.environ.get('SCORPION_WORKERS', 5))


def q_of(arm, z):
    q = dict(K.T3); q.update({k: float(lo + v * (hi - lo)) for (k, lo, hi), v in zip(ARMS[arm], z)})
    if arm == 'flippers':
        q.update(flip=1.0, f_nose=float(q['f_nose'] > 0.5), f_tail=float(q['f_tail'] > 0.5))
    return q


def _init():
    GG.HEIGHTS = CA.HEIGHTS_EXT


def job(a):
    arm, tag, z, seed = a; t0 = time.time(); q = q_of(arm, z)
    try:
        sp = K.make(q, strict=True)
        if sp is None:
            return dict(arm=arm, tag=tag, z=list(map(float, z)), built=False)
        cm = {}
        for mu in S.BAND_CLIMB:
            cm[str(mu)] = S.ladder_lean(sp, mu, seed, cap=min(cm.values()) if cm else None)
        tn = [GG.turn(GG.Sim(sp, mu), sg)[0] for mu in GG.BAND for sg in (1, -1)]
        return dict(arm=arm, tag=tag, z=list(map(float, z)), q={k: q[k] for k, _, _ in ARMS[arm]}, built=True, climb=min(cm.values()),
                    climb_by_mu=cm, turn=None if any(t is None for t in tn) else max(tn), mass=sp['mass'], width=sp['width'],
                    length=sp['length'], s=round(time.time() - t0, 1))
    except Exception as e:
        return dict(arm=arm, tag=tag, z=list(map(float, z)), err=f'{type(e).__name__}: {e}'[:300])


def score(r):
    if not r.get('built') or r.get('turn') is None:
        return -1e9
    return r['climb'] - 0.5 * max(0.0, r['turn'] - TURN_CAP)              # a soft wall at the cap, for the refinement


def run():
    os.makedirs(OUT, exist_ok=True); path = os.path.join(OUT, 'screens.jsonl'); stamp.check(path)
    rows = [json.loads(l) for l in open(path)] if os.path.isfile(path) else []; done = {(r['arm'], r['tag']) for r in rows}
    from scipy.stats import qmc
    rng = np.random.default_rng(71); t0 = time.time()
    with open(path, 'a') as fh, Pool(WORKERS, initializer=_init) as pool:
        def go(J, label):
            J = [j for j in J if (j[0], j[1]) not in done]
            for r in pool.imap_unordered(job, J, chunksize=1):
                rows.append(r); fh.write(json.dumps(r, default=float) + '\n'); fh.flush()
            best = {a: max((r for r in rows if r['arm'] == a), key=score, default=None) for a in ARMS}
            print(f"{label}: {len(rows)} screened, {time.time() - t0:.0f} s; best " + '  '.join(
                f"{a}: {b and b.get('climb')} mm / {b and b.get('turn') and round(b['turn'])} mm" for a, b in best.items()), flush=True)
        J = []
        for arm, sp_ in ARMS.items():                                     # B: T3's own point, then Sobol
            zT = np.array([(K.T3[k] - lo) / (hi - lo) if k in K.T3 else 0.5 for k, lo, hi in sp_])
            if arm == 'flippers':
                zT[[i for i, (k, _, _) in enumerate(sp_) if k == 'f_tail']] = 0.75
            Z = np.vstack([np.clip(zT, 0, 1), qmc.Sobol(len(sp_), scramble=True, seed=73).random(N_B - 1)])
            J += [(arm, f'B{i}', z, 40000) for i, z in enumerate(Z)]
        go(J, 'B')
        state = {}
        for g in range(GENS):                                             # cross-entropy, as capability.run
            J = []
            for arm, sp_ in ARMS.items():
                el = sorted([r for r in rows if r['arm'] == arm], key=score, reverse=True)[:ELITE]; E = np.array([r['z'] for r in el])
                mu, sd = (E.mean(0), np.maximum(E.std(0), 0.05)) if arm not in state else \
                         (0.6 * E.mean(0) + 0.4 * state[arm][0], np.maximum(0.6 * E.std(0) + 0.4 * state[arm][1] * 0.8, 0.02))
                state[arm] = (mu, sd); Z = np.clip(mu + sd * rng.normal(size=(POP, len(sp_))), 0, 1)
                J += [(arm, f'C{g}|{i}', z, 50000 + g) for i, z in enumerate(Z)]
            go(J, f'gen {g}')
    finals()


def finals(k=2):
    """each arm's k best and T3, on the full ladder (20 tries a rung, every friction) and the turn"""
    path = os.path.join(OUT, 'screens.jsonl'); rows = [json.loads(l) for l in open(path)]
    pick = []
    for arm in ARMS:
        for r in sorted([r for r in rows if r['arm'] == arm], key=score, reverse=True)[:k]:
            pick.append((f"{arm} {len(pick) % k + 1}", q_of(arm, r['z']), r))
    pick.append(('T3', dict(K.T3), None))
    specs = [K.make(q, strict=True) for _, q, _ in pick]
    J = [(i, mu, h, b, 20, 61 + i) for i in range(len(specs)) for mu in GG.BAND for h in CA.HEIGHTS_EXT for b in (False, True)]
    with Pool(WORKERS, initializer=_init) as pool:
        R = pool.map(_climb, [(specs[i], mu, h, b, n, s) for i, mu, h, b, n, s in J], chunksize=1)
        T = pool.map(_turn, [(sp, mu, sg) for sp in specs for mu in GG.BAND for sg in (1, -1)], chunksize=1)
    out = []
    for i, (name, q, r) in enumerate(pick):
        lad = {}
        for mu in GG.BAND:
            res = {(h, b): R[j] for j, (ii, m, h, b, _, _) in enumerate(J) if ii == i and m == mu}
            lad[str(mu)] = GG.ladder(res, 20)
        tn = T[6 * i: 6 * i + 6]
        out.append(dict(name=name, q=q, climb=min(lad.values()), climb_by_mu=lad, turn=None if any(t is None for t in tn) else max(tn),
                        mass=specs[i]['mass'], width=specs[i]['width'], notes=specs[i]['notes'], screen=r and dict(climb=r['climb'], turn=r['turn'])))
        print(f"{name:12s} step {out[-1]['climb']} mm {lad}  turn {out[-1]['turn'] and round(out[-1]['turn'])} mm  {specs[i]['mass']:.0f} g", flush=True)
    json.dump(dict(turn_cap=TURN_CAP, finals=out), open(os.path.join(OUT, 'finals.json'), 'w'), indent=1, default=float)


def _climb(a):
    sp, mu, h, back, n, seed = a; GG.HEIGHTS = CA.HEIGHTS_EXT
    sim = GG.Sim(sp, mu, step=h); rng = np.random.default_rng([seed, int(100 * mu), h, int(back)])
    return sum(GG.climb_try(sim, h, back, rng) for _ in range(n))


def _turn(a):
    sp, mu, sg = a; return GG.turn(GG.Sim(sp, mu), sg)[0]


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'run': run, 'finals': finals}.get(cmd, lambda: print(__doc__))()
