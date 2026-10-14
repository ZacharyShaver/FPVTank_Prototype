"""Audit (2026-10-14): are the hard-floor predictions settled at the 0.5 ms time step? The same effective bounce
(restitution 0.31) run at 0.5 ms (damping 0.35, the H3c main model) and at 0.1 ms (damping 0.45); the landing
distributions at 15 cm are compared start by start.    python research/tumble/audit/hard_floor_convergence.py"""
import os, sys
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))


def one(a):
    name, ts, dr = a
    import scale_model as S, predict_drops as PD
    return a, S.predict(name, PD.GRAMS[name], False, S.ATTITUDES, n_per=200, mu=1.0, seed=7, drop_mm=150.0, timeconst=0.002, dampratio=dr, timestep=ts)


if __name__ == '__main__':
    jobs = [(n, ts, dr) for n in ('E1_tub', 'E3_tall') for ts, dr in ((0.0005, 0.35), (0.0001, 0.45))]
    with Pool(4) as p:
        R = dict(p.map(one, jobs))
    import numpy as np
    for n in ('E1_tub', 'E3_tall'):
        a, b = R[(n, 0.0005, 0.35)]['by_attitude'], R[(n, 0.0001, 0.45)]['by_attitude']
        worst = 0
        for att in a:
            ks = set(a[att]) | set(b[att]); d = max(abs(a[att].get(k, 0) - b[att].get(k, 0)) for k in ks); worst = max(worst, d)
            print(f"{n} {att:<30} 0.5 ms upright {a[att].get('upright', 0):.2f} inverted {a[att].get('inverted', 0):.2f} | 0.1 ms upright {b[att].get('upright', 0):.2f} inverted {b[att].get('inverted', 0):.2f}")
        print(f'{n}: largest change in any probability {worst:.2f} (sampling noise at 200 drops is about 0.05)')
