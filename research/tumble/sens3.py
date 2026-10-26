"""EXPLORATORY (2026-10-25): which parts of chassis3's best-under-380 layout carry its gain? Each variant changes one
thing from it (or from the Trainer), 20 runs a cell over chassis3.CELLS, hard floor.

    python research/tumble/sens3.py  -> research/results/chassis3/sensitivity.json
"""
import os, sys, json, time
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import chassis3 as C3

BEST = dict(R=46.0, xf=53.0, xr=-77.0, clr=54.0, dxp=28.0, dzp=6.0)
V = {'best under 380 (search)': BEST,
     'packs not moved': dict(BEST, dxp=0.0, dzp=0.0),
     'belly 48': dict(BEST, dxp=0.0, dzp=0.0, clr=48.0),
     'belly 60': dict(BEST, dxp=0.0, dzp=0.0, clr=60.0),
     'wheels Ø100': dict(BEST, dxp=0.0, dzp=0.0, R=50.0),
     'Trainer wheels Ø110 on the short wheelbase': dict(BEST, dxp=0.0, dzp=0.0, R=55.0),
     'Trainer, belly raised to 54 only': dict(C3.BASE, clr=54.0),
     'Trainer': C3.BASE}


def job(a):
    name, cell, seed = a
    return a, C3.descend((V[name], [cell], 20, seed))[cell]


if __name__ == '__main__':
    t0 = time.time()
    jobs = [(n, c, 300 + i) for n in V for i, c in enumerate(C3.CELLS)]
    with Pool(30) as pool:
        R = pool.map(job, jobs, chunksize=1)
    out = {}
    for (n, c, _), r in R:
        out.setdefault(n, {})['|'.join(map(str, (c[0], c[1], int(c[2]))))] = r
    res = {n: dict(p=V[n], down=float(np.mean([v.get('upright', 0) / sum(v.values()) for v in cells.values()])),
                   stuck=float(np.mean([v.get('stuck', 0) / sum(v.values()) for v in cells.values()])), cells=cells) for n, cells in out.items()}
    json.dump(dict(wall_s=round(time.time() - t0), runs_per_cell=20, variants=res), open(os.path.join(ROOT, 'results', 'chassis3', 'sensitivity.json'), 'w'), indent=1)
    for n, r in res.items():
        print(f"{n:44s} down a step {r['down']:.3f}  stuck {r['stuck']:.3f}")
    print(f'{time.time() - t0:.0f} s')
