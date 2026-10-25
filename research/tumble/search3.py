"""EXPLORATORY (2026-10-25): the self-righting search over shell3's family, in stages, each cheaper than the next.

    python research/tumble/search3.py screen [--log2n 17]   # 1: static rest states of 2^n Sobol designs (print + robot)
    python research/tumble/search3.py dyn [--top 1500]      # 2: simulated drops of the best (print 60, robot 60)
    python research/tumble/search3.py refine                # 3: cross-entropy search around the best, by simulation
    python research/tumble/search3.py margin                # 3b: cross-entropy search on the print's static margin, per size cap
    python research/tumble/search3.py final [--top 40]      # 4: the best under every contact model, mass high, friction
      -> research/results/search3/*.npz / *.json

Stage 1 is statics (shell3.static, shell3.stall); stages 2-4 are MuJoCo drops: the printed body from the drop stand at
150 mm (the six starts, +-15 degrees), and the full robot (random orientations, spin, cover 1.5 mm, bounce 0.2).
"""
import os, sys, json, time, argparse
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
OUT = os.path.join(ROOT, 'results', 'search3')
sys.path.insert(0, HERE)
import shell3 as S3

WORKERS = 30


def _screen(x):
    return S3.screen(x)


def _margins(x):
    q = S3.as_dict(x); P, pk, sc = S3.print_body(q); M, G, I = S3.print_layout(P, pk)
    F = S3.body(q); Mr, Gr, Ir, mc = S3.robot_layout(q)
    return S3.margin(P, G), S3.margin(F, Gr), float(P[:, 2].max())


def _dyn(a):
    """one design: print drops (hard39, the stand's six starts) and robot drops"""
    x, n_print, n_robot, seed, contact, high, mu = a
    q = S3.as_dict(x); P, pk, sc = S3.print_body(q); L = S3.print_layout(P, pk, high)
    r = S3.drops(P, L, contact, n=n_print, seed=seed, mu=mu) if n_print else None
    rr = S3.robot_trials(q, n_robot, seed=seed) if n_robot else None
    return r, rr


def score_static(D):
    """stage 1's ranking: both bodies' static upright share, less their stall shares"""
    c = {k: i for i, k in enumerate(S3.SCREEN_COLS)}
    ok = np.isfinite(D[:, c['print_static_up']]) & (D[:, c['pocket_fits']] > 0)
    s = (np.minimum(D[:, c['print_static_up']], D[:, c['robot_static_up']]) - D[:, c['print_stall']] - D[:, c['robot_stall']])
    return np.where(ok, s, -np.inf)


def screen(log2n):
    from scipy.stats import qmc
    X = qmc.scale(qmc.Sobol(d=len(S3.KEYS), scramble=True, seed=25).random_base2(log2n), S3.LO, S3.HI)
    t0 = time.time(); R = []
    with Pool(WORKERS) as pool:
        for k, r in enumerate(pool.imap(_screen, X, chunksize=64), 1):
            R.append(r)
            if k % 8192 == 0:
                print(f'{k}/{len(X)}  {time.time() - t0:.0f} s', flush=True)
    D = np.array(R); s = score_static(D)
    top = np.argsort(-s)[:4000]
    with Pool(WORKERS) as pool:
        mg = np.array(pool.map(_margins, D[top, :len(S3.KEYS)], chunksize=8))
    np.savez_compressed(os.path.join(OUT, 'screen.npz'), D=D, cols=np.array(S3.SCREEN_COLS), score=s, top=top, margins=mg,
                        wall_s=time.time() - t0)
    c = {k: i for i, k in enumerate(S3.SCREEN_COLS)}
    print(f'{len(X)} designs, {time.time() - t0:.0f} s; static upright share (print) quartiles',
          np.nanpercentile(D[:, c['print_static_up']], [25, 50, 75, 90, 99]).round(3),
          '; one rest state (print and robot):', int(np.sum((D[:, c['print_static_up']] > 0.999) & (D[:, c['robot_static_up']] > 0.999))))


def dyn(top_n):
    Z = np.load(os.path.join(OUT, 'screen.npz')); D, mg, top = Z['D'], Z['margins'], Z['top']
    # rank the screened top by their worse margin (as a share of height), the static score breaking ties
    H = mg[:, 2]; worst = np.minimum(mg[:, 0] / H, mg[:, 1] / (D[top, S3.SCREEN_COLS.index('height')]))
    sel = top[np.argsort(-worst)[:top_n]]
    t0 = time.time()
    with Pool(WORKERS) as pool:
        R = pool.map(_dyn, [(D[i, :len(S3.KEYS)], 10, 60, 11, 'hard39', False, 1.0) for i in sel], chunksize=2)
    res = [dict(i=int(i), x=D[i, :len(S3.KEYS)].tolist(), print_up=r['p_upright'], print_counts=r['counts'],
                robot_up=rr['p_upright'], robot_counts=rr['counts']) for i, (r, rr) in zip(sel, R)]
    json.dump(dict(wall_s=round(time.time() - t0), designs=res), open(os.path.join(OUT, 'dyn.json'), 'w'))
    P = np.array([[r['print_up'], r['robot_up']] for r in res])
    print(f'{len(res)} designs, {time.time() - t0:.0f} s; print P(up) quartiles', np.percentile(P[:, 0], [25, 50, 75, 90, 100]).round(3),
          'robot', np.percentile(P[:, 1], [25, 50, 75, 90, 100]).round(3))


def refine(gens=8, pop=60, elite=12):
    """cross-entropy search: sample around the best simulated designs, simulate, keep the elite, repeat. The score is
    the worse of the print's and the robot's P(upright) at 120 drops each, a small bonus for the print's margin."""
    Dy = json.load(open(os.path.join(OUT, 'dyn.json')))['designs']
    lo, hi = S3.LO, S3.HI; span = hi - lo
    pts = sorted(Dy, key=lambda r: -min(r['print_up'], r['robot_up']))[:elite]
    E = np.array([r['x'] for r in pts]); hist = []
    rng = np.random.default_rng(5); t0 = time.time()
    mu, sd = E.mean(0), np.maximum(E.std(0), 0.03 * span)
    with Pool(WORKERS) as pool:
        best = []
        for g in range(gens):
            X = np.clip(mu + sd * rng.normal(size=(pop, len(mu))), lo, hi)
            X = np.vstack([X, [b[1] for b in best[:4]]]) if best else X
            R = pool.map(_dyn, [(x, 20, 120, 100 + g, 'hard39', False, 1.0) for x in X], chunksize=1)
            M = pool.map(_margins, X, chunksize=2)
            sc = [min(r['p_upright'], rr['p_upright']) + 0.002 * m[0] for (r, rr), m in zip(R, M)]
            for x, s, (r, rr), m in zip(X, sc, R, M):
                hist.append(dict(gen=g, x=x.tolist(), score=s, print_up=r['p_upright'], robot_up=rr['p_upright'], margin_print=m[0], margin_robot=m[1]))
            order = np.argsort(sc)[::-1]
            best = sorted(best + [(sc[i], X[i]) for i in order[:elite]], key=lambda b: -b[0])[:elite]
            Eg = np.array([b[1] for b in best]); mu = 0.7 * Eg.mean(0) + 0.3 * mu; sd = np.maximum(0.7 * Eg.std(0) + 0.3 * sd * 0.8, 0.01 * span)
            print(f'gen {g}: best {best[0][0]:.3f}  elite mean {np.mean([b[0] for b in best]):.3f}  {time.time() - t0:.0f} s', flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), history=hist), open(os.path.join(OUT, 'refine.json'), 'w'))


def _mfrac(a):
    """the print's margin as a share of its height, -1 if the design breaks a cap or its pocket doesn't fit, and
    the robot's margin (mm)"""
    x, cap = a
    q = S3.as_dict(x)
    try:
        F = S3.body(q); e = np.ptp(F, 0)
        if max(e[0], e[1]) > cap[0] or e[2] > cap[1]:
            return -1.0, 0.0
        P, pk, sc = S3.print_body(q)
        if not pk['fits']:
            return -1.0, 0.0
        M, G, I = S3.print_layout(P, pk); Mr, Gr, Ir, mc = S3.robot_layout(q)
        mr = S3.margin(F, Gr)
        return (S3.margin(P, G) / P[:, 2].max() if mr > 0 else -1.0), mr
    except Exception:
        return -1.0, 0.0


CAPS = {'any': (700.0, 600.0), 'plan 500': (500.0, 450.0), 'plan 450': (450.0, 400.0), 'plan 400': (400.0, 350.0)}


def refine_margin(gens=14, pop=240, elite=24):
    """cross-entropy search on the print's static margin (as a share of its height), under each size cap: the
    stage-2 result says margin is what buys P(upright), and dynamic P is saturated at 1.0 for 60 drops"""
    Z = np.load(os.path.join(OUT, 'screen.npz')); D = Z['D']; cols = list(Z['cols'])
    lo, hi = S3.LO, S3.HI; span = hi - lo; rng = np.random.default_rng(9); out = {}; t0 = time.time()
    with Pool(WORKERS) as pool:
        for name, cap in CAPS.items():
            e = D[:, [cols.index('length'), cols.index('width'), cols.index('height')]]
            inside = (np.maximum(e[:, 0], e[:, 1]) <= cap[0]) & (e[:, 2] <= cap[1])
            s = np.where(inside, score_static(D), -np.inf)
            seeds = D[np.argsort(-s)[:200], :len(S3.KEYS)]
            f0 = np.array(pool.map(_mfrac, [(x, cap) for x in seeds], chunksize=4))
            E = seeds[np.argsort(-f0[:, 0])[:elite]]; best = sorted(zip(f0[:, 0], f0[:, 1], seeds), key=lambda t: -t[0])[:elite]
            mu, sd = E.mean(0), np.maximum(E.std(0), 0.03 * span); hist = []
            for g in range(gens):
                X = np.clip(mu + sd * rng.normal(size=(pop, len(mu))), lo, hi)
                f = np.array(pool.map(_mfrac, [(x, cap) for x in X], chunksize=4))
                best = sorted(best + list(zip(f[:, 0], f[:, 1], X)), key=lambda t: -t[0])[:elite]
                Eg = np.array([b[2] for b in best]); mu = 0.6 * Eg.mean(0) + 0.4 * mu; sd = np.maximum(0.6 * Eg.std(0) + 0.4 * sd * 0.85, 0.005 * span)
                hist.append(dict(gen=g, best=float(best[0][0]), elite_mean=float(np.mean([b[0] for b in best])), valid=int((f[:, 0] > -1).sum())))
            out[name] = dict(cap=cap, history=hist, best=[dict(x=b[2].tolist(), margin_frac=float(b[0]), margin_robot_mm=float(b[1])) for b in best])
            print(f'{name}: best print margin {best[0][0]:.3f} of height (robot {best[0][1]:.1f} mm), {time.time() - t0:.0f} s', flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), evals=sum(len(v['history']) for v in out.values()) * pop, caps=out),
              open(os.path.join(OUT, 'refine_margin.json'), 'w'))


def final(top_n):
    """the best designs from stages 2 and 3 under every contact model (print, 40 per start), the coins high (the
    control), friction 0.65x and 1.5x, and the robot at 600 drops"""
    X, tags = [], []
    def take(x, tag):                                                  # distinct designs only
        if all(np.abs((np.array(x) - np.array(y)) / (S3.HI - S3.LO)).max() > 0.02 for y in X):
            X.append(list(x)); tags.append(tag); return True
        return False
    if os.path.exists(os.path.join(OUT, 'refine_margin.json')):        # the margin frontier: 4 per size cap
        for name, v in json.load(open(os.path.join(OUT, 'refine_margin.json')))['caps'].items():
            k = 0
            for b in v['best']:
                k += take(b['x'], f'margin, {name}')
                if k >= 4: break
    cand = json.load(open(os.path.join(OUT, 'dyn.json')))['designs']   # stage 2's best, by P then margin
    Z = np.load(os.path.join(OUT, 'screen.npz')); top = list(Z['top']); mg = Z['margins']
    for r in sorted(cand, key=lambda r: (-min(r['print_up'], r['robot_up']), -mg[top.index(r['i']), 0])):
        if len(X) >= top_n: break
        take(r['x'], 'stage 2')
    runs = [('hard39', False, 1.0), ('hard31', False, 1.0), ('hard55', False, 1.0), ('softfit', False, 1.0),
            ('hard39', True, 1.0), ('hard39', False, 0.65), ('hard39', False, 1.5)]
    jobs = [(np.array(x), 40, 0, 300 + j, c, h, mu) for x in X for j, (c, h, mu) in enumerate(runs)]
    jobs += [(np.array(x), 0, 600, 400, 'hard39', False, 1.0) for x in X]
    t0 = time.time()
    with Pool(WORKERS) as pool:
        R = pool.map(_dyn, jobs, chunksize=1)
        M = pool.map(_margins, [np.array(x) for x in X])
    out = []
    for k, x in enumerate(X):
        rr = {f'{c}{"_high" if h else ""}{"" if mu == 1.0 else f"_mu{mu}"}': R[k * len(runs) + j][0] for j, (c, h, mu) in enumerate(runs)}
        rob = R[len(X) * len(runs) + k][1]
        out.append(dict(x=x, tag=tags[k], params=S3.as_dict(x), size=S3.size(S3.as_dict(x)), margin_print_mm=M[k][0], margin_robot_mm=M[k][1], print_h=M[k][2],
                        print={k2: dict(p_upright=v['p_upright'], counts=v['counts']) for k2, v in rr.items()},
                        robot=dict(p_upright=rob['p_upright'], counts=rob['counts'], mass_g=rob['mass_g'], cover_g=rob['cover_g'])))
    json.dump(dict(wall_s=round(time.time() - t0), designs=out), open(os.path.join(OUT, 'final.json'), 'w'), indent=1)
    for d in out:
        pr = d['print']; low = [pr[c]['p_upright'] for c in ('hard39', 'hard31', 'hard55', 'softfit')]
        print(f"{d['tag']:16s} print {min(low):.3f}-{max(low):.3f} (high {pr['hard39_high']['p_upright']:.2f}) robot {d['robot']['p_upright']:.3f} "
              f"margin {d['margin_print_mm']:.1f}/{d['margin_robot_mm']:.1f} size {d['size']['length']:.0f}x{d['size']['width']:.0f}x{d['size']['height']:.0f}")
    print(f'{time.time() - t0:.0f} s')


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    ap = argparse.ArgumentParser(); ap.add_argument('stage', choices=['screen', 'dyn', 'refine', 'margin', 'final'])
    ap.add_argument('--log2n', type=int, default=17); ap.add_argument('--top', type=int, default=None)
    a = ap.parse_args()
    if a.stage == 'screen': screen(a.log2n)
    elif a.stage == 'dyn': dyn(a.top or 1500)
    elif a.stage == 'refine': refine()
    elif a.stage == 'margin': refine_margin()
    else: final(a.top or 40)
