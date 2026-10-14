"""POST HOC (2026-10-14): a hard floor with the measured bounce, against the 6 cm and 30 cm drops.

MuJoCo's default contact lets a body sink 7.4 mm into the floor on a 6 cm drop and 17 mm at 30 cm (C13, L12).
The fitted bounce (damping ratio 0.2, time constant 0.02 s) partly stood in for a harder floor. This model makes the
floor hard (time constant 0.002 s: 0.3-0.5 mm at 6 cm) and sets its bounce from the slow-motion measurement
(restitution ~0.3, damping ratio 0.35), so nothing in it is fitted to drop outcomes. It is scored against both data sets
with the same rules. Both have been seen, so this is post hoc; a proper test needs new drops.

    python research/tumble/posthoc_stiff.py -> research/results/posthoc_stiff.json and .md
"""
import os, sys, csv, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
import numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
BODIES = ('E1_tub', 'E2_dome', 'E3_tall')
STIFF = dict(timeconst=0.002, dampratio=0.35)


def one(args):
    name, high, drop_mm = args
    import scale_model as S, predict_drops as PD
    return (name, high, drop_mm), S.predict(name, PD.GRAMS[name], high, S.ATTITUDES, n_per=200, mu=1.0, seed=7, drop_mm=drop_mm, **STIFF)


def as_P(R, h):
    return {f"{n} mass {'high' if hi else 'low'}": dict(by_attitude={a: dict(p=p) for a, p in R[(n, hi, h)]['by_attitude'].items()})
            for n in BODIES for hi in (False, True)}


if __name__ == '__main__':
    import score_drops as SD
    with Pool(12) as pool:
        R = dict(pool.map(one, [(n, hi, h) for h in (60.0, 300.0) for n in BODIES for hi in (False, True)]))
    rng = np.random.default_rng(0)
    six = SD.drops()
    thirty = [r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'drops', 'run3_30cm.csv'), encoding='utf-8')) if r['mark'] in SD.MARK2CLS]
    J = lambda f: json.load(open(os.path.join(ROOT, 'results', f)))
    fitted6 = {f"{n} mass {m}": v for n in BODIES for m in ('low', 'high') for v in [None]}
    bf = json.load(open(os.path.join(ROOT, 'results', 'posthoc_bounce_fit.json')))['results']
    rows = []
    for lab, P6, P30 in (('dead contact (start fixed)', J('drop_predictions_fixed_attitudes.json'), J('drop_predictions_30cm_dead.json')),
                         ('soft floor, bounce fitted at 6 cm', None, J('drop_predictions_30cm_bounce_fit.json')),
                         ('soft floor, bounce measured', None, J('drop_predictions_30cm_bounce_measured.json')),
                         ('hard floor, bounce measured (this run)', as_P(R, 60.0), as_P(R, 300.0))):
        b6 = SD.score(six, P6, rng)['brier_model'] if P6 else (bf['0.2']['brier'] if 'fitted' in lab else None)
        s30 = SD.score(thirty, P30, rng)
        rows.append(dict(model=lab, brier_6cm=b6, brier_30cm=s30['brier_model'], top_30cm=s30['top_hit_model']))
    naive6 = SD.score(six, J('drop_predictions_fixed_attitudes.json'), rng)['brier_naive']; naive30 = SD.score(thirty, as_P(R, 300.0), rng)['brier_naive']
    # the mass control at 30 cm, hard floor
    ctl = {}
    for b in BODIES:
        p = {m: float(np.mean([SD.predicted(as_P(R, 300.0), b, m, r['start'])[0] for r in thirty if r['body'] == b and r['mass'] == m])) for m in ('low', 'high')}
        ctl[b] = {m: round(v, 2) for m, v in p.items()}
    out = dict(note='post hoc', stiff=STIFF, naive=dict(six=naive6, thirty=naive30), models=rows, control_30cm_pred_upright=ctl)
    json.dump(out, open(os.path.join(ROOT, 'results', 'posthoc_stiff.json'), 'w'), indent=1)
    L = ['# Post hoc: a hard floor with the measured bounce', '', f"Naive: 6 cm {naive6}, 30 cm {naive30}.", '',
         '| model | Brier, 6 cm (181) | Brier, 30 cm (180) | top state right, 30 cm |', '|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['model']} | {r['brier_6cm'] if r['brier_6cm'] is not None else '-'} | {r['brier_30cm']} | {r['top_30cm']} |")
    L += ['', 'Hard floor, predicted P(upright) at 30 cm, mass low vs high (seen: E1 10/30 vs 9/30, E2 16/30 vs 14/30, E3 16/30 vs 9/30): '
          + '; '.join(f"{b} {v['low']} vs {v['high']}" for b, v in ctl.items())]
    open(os.path.join(ROOT, 'results', 'posthoc_stiff.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
