"""POST HOC, exploratory (2026-10-14): how much bounce explains the 181 drops at 6 cm?

The start-fixed model (posthoc_attitude_fix.py) keeps bodies on ends and sides that real drops knock them off, and its
contact is dead (restitution 0.13 by bounce_curve). This reruns that model at several contact damping ratios (more
bounce as it falls) and scores each against the same drops. Choosing the best one here is fitting to this data, so
it proves nothing by itself. The test is a prediction of data not yet seen (the 30 cm drops), made with the bounce
fitted here and, separately, with the bounce measured by slow-motion video.

    python research/tumble/posthoc_bounce_fit.py -> research/results/posthoc_bounce_fit.json and .md
"""
import os, sys, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
import numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
BODIES = ('E1_tub', 'E2_dome', 'E3_tall')
RATIOS = [None, 0.6, 0.4, 0.3, 0.2, 0.1]


def one(args):
    name, high, dr = args
    import scale_model as S, predict_drops as PD
    return (name, high, dr), S.predict(name, PD.GRAMS[name], high, S.ATTITUDES, n_per=200, mu=1.0, seed=7, world_yaw=True, dampratio=dr)


if __name__ == '__main__':
    import scale_model as S, score_drops as SD
    curve = S.bounce_curve('E3_tall', False, ratios=tuple(RATIOS))
    with Pool(20) as pool:
        R = dict(pool.map(one, [(n, h, dr) for dr in RATIOS for n in BODIES for h in (False, True)]))
    D = SD.drops(); rng = np.random.default_rng(0)
    st = lambda s: 'side' if s in ('left side down', 'right side down') else s
    res = {}
    for dr in RATIOS:
        P = {f"{n} mass {'high' if h else 'low'}": dict(by_attitude={a: dict(p=p) for a, p in R[(n, h, dr)]['by_attitude'].items()})
             for n in BODIES for h in (False, True)}
        a = SD.score(D, P, rng)
        g = {}
        for b in BODIES:
            for m in ('low', 'high'):
                rows = [r for r in D if r['body'] == b and r['mass'] == m]
                g[f'{b} mass {m}'] = SD.score(rows, P, rng)['brier_model']
        sig = {}
        for s in ('nose down', 'tail down', 'side'):
            rows = [r for r in D if st(r['start']) == s]
            pm = np.mean([SD.predicted(P, r['body'], r['mass'], r['start']) for r in rows], 0)
            ob = np.mean([SD.onehot(SD.MARK2CLS[r['mark']]) for r in rows], 0)
            stay = {'nose down': 'head up', 'tail down': 'head down', 'side': 'side'}[s]   # stays on the face it hit
            k = SD.CLS.index(stay)
            sig[s] = dict(stays_predicted=round(float(pm[k]), 2), stays_seen=round(float(ob[k]), 2),
                          upright_predicted=round(float(pm[0]), 2), upright_seen=round(float(ob[0]), 2))
        key = 'default' if dr is None else dr
        res[str(key)] = dict(restitution=curve[key], brier=a['brier_model'], naive=a['brier_naive'], diff_95=a['diff_95'],
                             top_hit=a['top_hit_model'], groups=g, by_start=sig)
    json.dump(dict(note='post hoc, exploratory: fitted to the 6 cm drops', results=res),
              open(os.path.join(ROOT, 'results', 'posthoc_bounce_fit.json'), 'w'), indent=1)
    L = ['# Post hoc, exploratory: contact bounce vs the 181 drops (start-fixed model)', '',
         '| damping ratio | restitution | Brier (naive 1.293) | top state right | end drops: stays on end, pred / seen | side drops: stays on side | end drops: upright |',
         '|---|---|---|---|---|---|---|']
    for k, v in res.items():
        e = v['by_start']
        L.append(f"| {k} | {v['restitution']} | {v['brier']} | {v['top_hit']} | "
                 f"{(e['nose down']['stays_predicted'] + e['tail down']['stays_predicted']) / 2:.2f} / {(e['nose down']['stays_seen'] + e['tail down']['stays_seen']) / 2:.2f} | "
                 f"{e['side']['stays_predicted']:.2f} / {e['side']['stays_seen']:.2f} | "
                 f"{(e['nose down']['upright_predicted'] + e['tail down']['upright_predicted']) / 2:.2f} / {(e['nose down']['upright_seen'] + e['tail down']['upright_seen']) / 2:.2f} |")
    open(os.path.join(ROOT, 'results', 'posthoc_bounce_fit.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
