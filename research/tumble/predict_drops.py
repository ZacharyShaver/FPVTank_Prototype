"""Workstream E: the simulation's predictions for every physical drop, written BEFORE any drop is made.

    python research/tumble/predict_drops.py  -> research/results/drop_predictions.json and drop_predictions.md
    python research/tumble/predict_drops.py --drop-mm 300 --tag 30cm --title "..."
      -> drop_predictions_30cm.json and .md (the same model at another release height; nothing else changes)

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
    name, high, mu, drop_mm = args
    sys.path.insert(0, HERE)
    import scale_model as S
    return (name, high, mu), S.predict(name, GRAMS[name], high, S.ATTITUDES, n_per=200, mu=mu, seed=7, drop_mm=drop_mm)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--drop-mm', type=float, default=60.0); ap.add_argument('--tag', default='')
    ap.add_argument('--title', default='Drop predictions (committed before any drop)'); ap.add_argument('--bodies', nargs='*')
    A = ap.parse_args()
    bodies = A.bodies or list(GRAMS)
    jobs = [(n, h, mu, A.drop_mm) for n in bodies for h in (False, True) for mu in (1.0, 0.65, 1.5)]
    with Pool(min(18, len(jobs))) as pool:
        R = dict(pool.map(one, jobs))
    out = {'drop_mm': A.drop_mm}
    lines = [f'# {A.title}', '', f'Release height {A.drop_mm:.0f} mm (lowest point of the body above the table).', '',
             'Each cell: the most likely rest state and its probability at the nominal friction, then the range of that',
             "probability across 0.65x to 1.5x friction. 200 simulated drops per cell.", '']
    for n in bodies:
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
    tag = f'_{A.tag}' if A.tag else ''
    if not tag and (A.drop_mm != 60.0 or A.bodies):
        sys.exit('a non-default run needs --tag, so it cannot overwrite the committed predictions')
    json.dump(out, open(os.path.join(ROOT, 'results', f'drop_predictions{tag}.json'), 'w'), indent=1)
    open(os.path.join(ROOT, 'results', f'drop_predictions{tag}.md'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines[:40]))
