"""POST HOC (2026-10-14): which shape wins once the shell has a realistic weight?

The sweep (sweep.py, D) ran with a weightless shell (audit B2). This reruns the same 400 Sobol designs and drop seeds
with the tub kept as the chassis plus a printed cover of COVER mm of solid PLA (tumble.SHELL_MASS = 'cover'), twice:
dead contact (as the sweep ran) and with bounce (contact damping ratio 0.2, the value the 6 cm scale-model drops
fitted, restitution ~0.56). Bounce on the full-size robot is a sensitivity check, not a measurement: its tyres are
rubber and its shell is printed. The top designs of each variant are rerun at 1000 drops to separate winners from noise.

    python research/tumble/posthoc_sweep_v2.py [--cover 1.5]
      -> research/results/posthoc_sweep_v2.json and .md
"""
import os, sys, json, time, argparse
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
from scipy.stats import qmc
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import sweep as SW
VARIANTS = {'weightless shell, dead (as the sweep ran)': ('fixed', None), 'cover, dead': ('cover', None), 'cover, bounce': ('cover', 0.2)}


def one(args):
    i, x, drops, mode, dr, cover, seed = args
    import tumble as T
    T.SHELL_MASS = mode; T.COVER_T = cover; T.DAMPRATIO = dr
    p = dict(zip(SW.KEYS, map(float, x)))
    r = T.trials(p, drops, seed=seed)
    M, c, _ = T.inertia(T.mass_model(T.norm(p)))
    return dict(i=i, params=p, p_upright=r['p_upright'], counts=r['counts'], mass_g=round(M), com_z=round(float(c[2]), 1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--cover', type=float, default=1.5); ap.add_argument('--workers', type=int, default=24)
    a = ap.parse_args()
    X = qmc.scale(qmc.Sobol(d=len(SW.KEYS), scramble=True, seed=3).random(400), SW.LO, SW.HI)
    out = {}; t0 = time.time()
    with Pool(a.workers) as pool:
        for lab, (mode, dr) in VARIANTS.items():
            if lab.startswith('weightless'):
                T0 = json.load(open(os.path.join(ROOT, 'results', 'tumble_truth.json')))       # the committed sweep
                res = [dict(i=int(np.argmin(np.abs(X - np.array([d['params'][k] for k in SW.KEYS])).sum(1))), **d) for d in T0['designs']]
            else:
                res = pool.map(one, [(i, x, 200, mode, dr, a.cover, 1000 + i) for i, x in enumerate(X)])
            res.sort(key=lambda r: -r['p_upright'])
            top = res[:6]
            conf = pool.map(one, [(r['i'], X[r['i']], 1000, mode, dr, a.cover, 777) for r in top])
            out[lab] = dict(all=res, top_confirmed=sorted(conf, key=lambda r: -r['p_upright']),
                            tub=next(iter(pool.map(one, [(-1, [66.0, 0.08, 65.75, 0.0], 1000, mode, dr, a.cover, 777)]))))
            print(f'{lab}: done, {time.time() - t0:.0f} s', flush=True)
    json.dump(dict(note='post hoc', cover_mm=a.cover, variants={k: dict(mode=v[0], dampratio=v[1]) for k, v in VARIANTS.items()}, results=out),
              open(os.path.join(ROOT, 'results', 'posthoc_sweep_v2.json'), 'w'), indent=1)
    L = [f'# Post hoc: the sweep again, with a {a.cover} mm printed cover, dead contact and with bounce', '',
         'Top 6 of 400 designs (200 drops each) rerun at 1000 drops; the tub (66/0.08/65.75/0) at 1000 drops for reference. '
         'top, round, width, dz in mm except round (the share of the half-width the top curve takes).', '']
    for lab, v in out.items():
        L += [f'## {lab}', '', f"Tub: P(upright) {v['tub']['p_upright']:.3f}", '', '| top | round | width | dz | P(upright), 1000 drops | mass g | CoM z |', '|---|---|---|---|---|---|---|']
        for r in v['top_confirmed']:
            p = r['params']
            L.append(f"| {p['top']:.0f} | {p['round']:.2f} | {p['width']:.0f} | {p['dz']:.0f} | {r['p_upright']:.3f} | {r['mass_g']} | {r['com_z']} |")
        P = np.array([[r['params'][k] for k in SW.KEYS] + [r['p_upright']] for r in v['all']])
        cors = {k: round(float(np.corrcoef(P[:, j], P[:, 4])[0, 1]), 2) for j, k in enumerate(SW.KEYS)}
        L += ['', f"Correlation of each setting with P(upright) over the 400: {cors}", '']
    open(os.path.join(ROOT, 'results', 'posthoc_sweep_v2.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
