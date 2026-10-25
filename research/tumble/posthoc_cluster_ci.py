"""POST HOC (2026-10-25, after a cold read of draft v5 asked it): are the drop tests' CIs too narrow?

    python research/tumble/posthoc_cluster_ci.py -> research/results/posthoc_cluster_ci.json and .md

score_30cm.py and score_15cm.py resample single drops. But drops come in clusters: 5 in a row from the same start
(a cell: body, weight, start) and 30 per body and weight, run as one block. If drops in a cluster are alike, resampling
single drops makes the CIs too narrow. This reruns the paper's two blind-test differences, and each model against
naive, resampling whole clusters:
  drop    single drops (the registered method; reproduces the scored CIs)
  cell    whole cells, 36 per height (the same start, back to back)
  group   whole body-and-weight blocks, 6 per height (a stress test: with 6 clusters a percentile CI is rough)
Nothing in the registered results changes; this only says how far their CIs stretch.
"""
import os, sys, csv, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import score_drops as SD
from score_30cm import per_drop, MODELS as M30
from score_15cm import MODELS as M15, PRIMARY, CTRL

TESTS = {   # the paper's two blind tests: (height, run file, models, a, b)
    '30 cm: bounce fitted at 6 cm (main) minus default floor': ('run3_30cm.csv', M30, '3 start fixed, bounce fitted (main)', '2 start fixed, dead'),
    '15 cm: hard floor 0.31 (primary) minus default floor': ('run4_15cm.csv', M15, PRIMARY, CTRL),
}
UNITS = {'drop': lambda r, i: i, 'cell': lambda r, i: (r['body'], r['mass'], r['start']), 'group': lambda r, i: (r['body'], r['mass'])}


def cluster_ci(d, keys, n_boot=4000, seed=0):
    """95% percentile CI of mean(d), resampling whole clusters (keys[i] names drop i's cluster)"""
    ids = {}
    for i, k in enumerate(keys):
        ids.setdefault(k, []).append(i)
    C = list(ids.values()); s = np.array([d[c].sum() for c in C]); n = np.array([len(c) for c in C])
    rng = np.random.default_rng(seed); means = []
    for _ in range(n_boot):
        j = rng.integers(0, len(C), len(C)); means.append(s[j].sum() / n[j].sum())
    return [round(float(q), 3) for q in np.percentile(means, [2.5, 97.5])], len(C)


if __name__ == '__main__':
    out = {}
    for name, (run, models, a, b) in TESTS.items():
        ALL = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'drops', run), encoding='utf-8')))
        R = [r for r in ALL if r['mark'] in SD.MARK2CLS]
        Ps = {k: json.load(open(os.path.join(ROOT, 'results', models[k]))) for k in (a, b)}
        ba, bb = per_drop(R, Ps[a])[0], per_drop(R, Ps[b])[0]
        naive = np.array([((SD.naive(r['start']) - SD.onehot(SD.MARK2CLS[r['mark']])) ** 2).sum() for r in R])
        rows = {}
        for label, d in ((f'{a} minus {b}', ba - bb), (f'{a} minus naive', ba - naive)):
            rows[label] = dict(mean=round(float(d.mean()), 3))
            for u, key in UNITS.items():
                ci, k = cluster_ci(d, [key(r, i) for i, r in enumerate(R)])
                rows[label][u] = dict(ci95=ci, clusters=k)
        out[name] = dict(n=len(R), brier={a: round(float(ba.mean()), 3), b: round(float(bb.mean()), 3)}, tests=rows)
    json.dump(out, open(os.path.join(ROOT, 'results', 'posthoc_cluster_ci.json'), 'w'), indent=1)
    L = ['# Post hoc: the drop tests\' CIs, resampling clusters instead of single drops', '',
         'From `tumble/posthoc_cluster_ci.py` (2026-10-25). Drop: the registered method. Cell: whole runs of 5 drops from',
         'one start (36 per height). Group: whole body-and-weight blocks (6 per height; rough with so few).', '',
         '| test | n | mean | drop 95% CI | cell 95% CI | group 95% CI |', '|---|---|---|---|---|---|']
    for name, v in out.items():
        for label, t in v['tests'].items():
            f = lambda u: f"{t[u]['ci95'][0]} to {t[u]['ci95'][1]}"
            L.append(f"| {name.split(':')[0]}: {label} | {v['n']} | {t['mean']} | {f('drop')} | {f('cell')} | {f('group')} |")
    open(os.path.join(ROOT, 'results', 'posthoc_cluster_ci.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
