"""EXPLORATORY (2026-10-25): is search3's static screen a usable surrogate? 300 random screened designs (any score)
get 60 simulated print drops each (hard floor 0.39, the stand's six starts); compare with their static upright share.

    python research/tumble/static_vs_dyn3.py  -> research/results/search3/static_vs_dyn.json
"""
import os, sys, json, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
OUT = os.path.join(ROOT, 'results', 'search3')


def one(x):
    import shell3 as S3
    q = S3.as_dict(x); P, pk, sc = S3.print_body(q); L = S3.print_layout(P, pk)
    return S3.drops(P, L, 'hard39', n=10, seed=21)['p_upright']


if __name__ == '__main__':
    Z = np.load(os.path.join(OUT, 'screen.npz')); D = Z['D']; cols = list(Z['cols']); c = cols.index('print_static_up')
    ok = np.where(np.isfinite(D[:, c]) & (D[:, cols.index('pocket_fits')] > 0))[0]
    idx = np.random.default_rng(3).choice(ok, 300, replace=False); t0 = time.time()
    with Pool(30) as pool:
        P = np.array(pool.map(one, D[idx, :10], chunksize=2))
    s = D[idx, c]; r = float(np.corrcoef(s, P)[0, 1])
    bins = [(a, b, float(P[(s >= a) & (s < b)].mean()) if ((s >= a) & (s < b)).any() else None, int(((s >= a) & (s < b)).sum()))
            for a, b in ((0, 0.25), (0.25, 0.35), (0.35, 0.5), (0.5, 0.75), (0.75, 0.999), (0.999, 1.01))]
    json.dump(dict(n=300, wall_s=round(time.time() - t0), r=r, bins=bins, static=s.tolist(), dynamic=P.tolist()), open(os.path.join(OUT, 'static_vs_dyn.json'), 'w'))
    print(f'r = {r:.2f}; by static share: ' + '; '.join(f'{a:.2f}-{b:.2f}: P {m:.2f} (n {n})' for a, b, m, n in bins if m is not None), f'{time.time() - t0:.0f} s')
