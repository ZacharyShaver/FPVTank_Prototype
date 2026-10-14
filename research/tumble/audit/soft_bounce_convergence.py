"""Audit (2026-10-14): is the soft floor with the fitted bounce (time constant 0.02 s, damping 0.2; the model that
passed H3b at 30 cm) converged at the 0.5 ms step? Landing distributions at 0.5 ms vs 0.1 ms, 30 cm, E1 and E3 mass low.
    python research/tumble/audit/soft_bounce_convergence.py"""
import os, sys
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))


def one(a):
    name, ts = a
    import scale_model as S, predict_drops as PD
    return a, S.predict(name, PD.GRAMS[name], False, S.ATTITUDES, n_per=150, mu=1.0, seed=7, drop_mm=300.0, dampratio=0.2, timestep=ts)


if __name__ == '__main__':
    with Pool(4) as p:
        R = dict(p.map(one, [(n, ts) for n in ('E1_tub', 'E3_tall') for ts in (0.0005, 0.0001)]))
    for n in ('E1_tub', 'E3_tall'):
        a, b = R[(n, 0.0005)]['by_attitude'], R[(n, 0.0001)]['by_attitude']; worst = 0
        for att in a:
            worst = max(worst, max(abs(a[att].get(k, 0) - b[att].get(k, 0)) for k in set(a[att]) | set(b[att])))
            print(f"{n} {att:<30} 0.5 ms upright {a[att].get('upright', 0):.2f} inverted {a[att].get('inverted', 0):.2f} | 0.1 ms upright {b[att].get('upright', 0):.2f} inverted {b[att].get('inverted', 0):.2f}")
        print(f'{n}: largest change {worst:.2f} (sampling noise at 150 drops about 0.06)')
