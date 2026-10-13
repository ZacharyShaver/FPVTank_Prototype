"""Workstream E: the simulation's predictions for every physical drop, written BEFORE any drop is made.

    python research/tumble/predict_drops.py  -> research/results/drop_predictions.json and drop_predictions.md

For each test body (E1-E3), mass low and mass high, and each of the six starting attitudes in DROP_TEST.md: the
probability of each rest state, from 200 simulated drops with +-15 deg of hand jitter, from 60 mm, at the body's
sliced weight (spacer included). Friction between PLA and the table isn't known, so the predictions are also run at
0.65x and 1.5x friction; the spread is reported as the prediction's own uncertainty.
"""
import os, sys, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
GRAMS = {'E1_tub': 40.48, 'E2_dome': 50.89, 'E3_tall': 72.08}      # Orca, supports off (they come off): body + spacer


def one(args):
    name, high, mu = args
    sys.path.insert(0, HERE)
    import scale_model as S
    return (name, high, mu), S.predict(name, GRAMS[name], high, S.ATTITUDES, n_per=200, mu=mu, seed=7)


if __name__ == '__main__':
    jobs = [(n, h, mu) for n in GRAMS for h in (False, True) for mu in (1.0, 0.65, 1.5)]
    with Pool(18) as pool:
        R = dict(pool.map(one, jobs))
    out = {}
    lines = ['# Drop predictions (committed before any drop)', '',
             'Each cell: the most likely rest state and its probability at the nominal friction, then the range of that',
             "probability across 0.65x to 1.5x friction. 200 simulated drops per cell.", '']
    for n in GRAMS:
        for h in (False, True):
            key = f"{n} mass {'high' if h else 'low'}"
            nom = R[(n, h, 1.0)]
            out[key] = dict(mass_g=nom['mass_g'], com_mm=nom['com_mm'],
                            by_attitude={a: dict(p=nom['by_attitude'][a],
                                                 p_lowmu=R[(n, h, 0.65)]['by_attitude'][a], p_highmu=R[(n, h, 1.5)]['by_attitude'][a])
                                         for a in nom['by_attitude']})
            lines += [f"## {key}  (mass {nom['mass_g']} g, CoM z {nom['com_mm'][2]} mm)", '', '| start | most likely | p | across friction | others |', '|---|---|---|---|---|']
            for a, p in nom['by_attitude'].items():
                top = max(p, key=p.get)
                rng = [R[(n, h, mu)]['by_attitude'][a].get(top, 0.0) for mu in (0.65, 1.5)]
                others = ', '.join(f'{k} {v:.2f}' for k, v in sorted(p.items(), key=lambda kv: -kv[1]) if k != top)
                lines.append(f'| {a} | {top} | {p[top]:.2f} | {min(rng + [p[top]]):.2f}-{max(rng + [p[top]]):.2f} | {others} |')
            lines.append('')
    json.dump(out, open(os.path.join(ROOT, 'results', 'drop_predictions.json'), 'w'), indent=1)
    open(os.path.join(ROOT, 'results', 'drop_predictions.md'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines[:40]))
