"""Workstream D: the "ground truth" the surrogate is scored against: P(upright) at many designs by full simulation.

    python research/tumble/sweep.py [--designs 400] [--drops 200] [--workers 28]
      -> research/results/tumble_truth.json

Designs are a scrambled Sobol sample of the four design settings (tumble.py documents them); the head, wheels and
track stay at the Trainer's. Each design gets `drops` simulated tumbles (seeded per design, so the run repeats).
"""
import os, sys, json, time, argparse
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
from scipy.stats import qmc

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
KEYS = ['top', 'round', 'width', 'dz']
LO = [66.0, 0.1, 65.75, -20.0]
HI = [220.0, 1.0, 175.0, 40.0]


def one(args):
    i, x, drops = args
    sys.path.insert(0, HERE)
    import tumble as T
    p = dict(zip(KEYS, map(float, x)))
    r = T.trials(p, drops, seed=1000 + i)
    return dict(params=p, n=r['n'], counts=r['counts'], p_upright=r['p_upright'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--designs', type=int, default=400); ap.add_argument('--drops', type=int, default=200)
    ap.add_argument('--workers', type=int, default=28); a = ap.parse_args()
    X = qmc.scale(qmc.Sobol(d=len(KEYS), scramble=True, seed=3).random(a.designs), LO, HI)
    t0 = time.time()
    with Pool(a.workers) as pool:
        res = []
        for k, r in enumerate(pool.imap_unordered(one, [(i, x, a.drops) for i, x in enumerate(X)]), 1):
            res.append(r)
            if k % 50 == 0:
                print(f'{k}/{len(X)}  {time.time() - t0:.0f} s', flush=True)
    P = np.array([r['p_upright'] for r in res])
    out = dict(keys=KEYS, lo=LO, hi=HI, drops=a.drops, wall_s=round(time.time() - t0), designs=res,
               p_range=[float(P.min()), float(P.max())], p_quartiles=[float(q) for q in np.percentile(P, [25, 50, 75])])
    os.makedirs(os.path.join(ROOT, 'results'), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, 'results', 'tumble_truth.json'), 'w'))
    print('P(upright) range %.2f..%.2f, quartiles %s, %d s' % (P.min(), P.max(), out['p_quartiles'], out['wall_s']))
