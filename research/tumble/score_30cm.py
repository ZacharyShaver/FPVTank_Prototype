"""H4: score the 30 cm redo (data/drops/run3_30cm.csv) against the four models committed before it (PROTOCOL.md H4).

    python research/tumble/score_30cm.py -> research/results/drop_scores_30cm.json and .md

The rules are score_drops.py's (Brier against the naive predictor, most likely state, mass control, Zach's nose/tail
mapped by the physical end, left and right merged). The pre-registered hypothesis: the bounce-fit model scores a lower
Brier than both the dead-contact model and the naive predictor, with paired bootstrap 95% CIs excluding 0.
"""
import os, sys, csv, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import score_drops as SD

MODELS = {'1 old start, dead': 'drop_predictions_30cm.json', '2 start fixed, dead': 'drop_predictions_30cm_dead.json',
          '3 start fixed, bounce fitted (main)': 'drop_predictions_30cm_bounce_fit.json',
          '4 start fixed, bounce measured': 'drop_predictions_30cm_bounce_measured.json'}


def per_drop(rows, P):
    pm = np.array([SD.predicted(P, r['body'], r['mass'], r['start']) for r in rows])
    o = np.array([SD.onehot(SD.MARK2CLS[r['mark']]) for r in rows])
    return ((pm - o) ** 2).sum(1), pm, o


if __name__ == '__main__':
    ALL = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'drops', 'run3_30cm.csv'), encoding='utf-8')))
    R = [r for r in ALL if r['mark'] in SD.MARK2CLS]
    Ps = {k: json.load(open(os.path.join(ROOT, 'results', f))) for k, f in MODELS.items()}
    rng = np.random.default_rng(0); B = [rng.integers(0, len(R), len(R)) for _ in range(4000)]
    naive = np.array([((SD.naive(r['start']) - SD.onehot(SD.MARK2CLS[r['mark']])) ** 2).sum() for r in R])
    br = {k: per_drop(R, P)[0] for k, P in Ps.items()}
    ci = lambda d: [round(float(q), 3) for q in np.percentile([d[i].mean() for i in B], [2.5, 97.5])]
    out = dict(n=len(R), naive=round(float(naive.mean()), 3), models={})
    for k in Ps:
        pm = per_drop(R, Ps[k])[1]; o = per_drop(R, Ps[k])[2]
        out['models'][k] = dict(brier=round(float(br[k].mean()), 3), minus_naive=round(float((br[k] - naive).mean()), 3),
                                minus_naive_95=ci(br[k] - naive), top_hit=round(float(np.mean(pm.argmax(1) == o.argmax(1))), 3))
    main, ctrl = '3 start fixed, bounce fitted (main)', '2 start fixed, dead'
    d = br[main] - br[ctrl]
    out['H4'] = dict(main_minus_dead=round(float(d.mean()), 3), main_minus_dead_95=ci(d),
                     main_minus_naive_95=out['models'][main]['minus_naive_95'],
                     supported=bool(ci(d)[1] < 0 and out['models'][main]['minus_naive_95'][1] < 0))
    d4 = br['4 start fixed, bounce measured'] - br[ctrl]
    out['measured_minus_dead'] = dict(mean=round(float(d4.mean()), 3), ci95=ci(d4))
    # groups and the mass control, for the main model
    P = Ps[main]; groups = {}
    for b in ('E1_tub', 'E2_dome', 'E3_tall'):
        for m in ('low', 'high'):
            rows = [r for r in R if r['body'] == b and r['mass'] == m]
            if not rows: continue
            bm, pm, o = per_drop(rows, P)
            groups[f'{b} mass {m}'] = dict(n=len(rows), brier={k: round(float(per_drop(rows, Ps[k])[0].mean()), 3) for k in Ps},
                                           p_upright_pred=round(float(pm[:, 0].mean()), 3), upright_seen=int(o[:, 0].sum()))
    out['groups'] = groups
    ctl = {}
    for b in ('E1_tub', 'E2_dome', 'E3_tall'):
        lo, hi = groups.get(f'{b} mass low'), groups.get(f'{b} mass high')
        if lo and hi:
            dp = lo['p_upright_pred'] - hi['p_upright_pred']; do = lo['upright_seen'] / lo['n'] - hi['upright_seen'] / hi['n']
            ctl[b] = dict(pred_low=lo['p_upright_pred'], pred_high=hi['p_upright_pred'], seen_low=f"{lo['upright_seen']}/{lo['n']}",
                          seen_high=f"{hi['upright_seen']}/{hi['n']}", same_direction=bool(np.sign(dp) == np.sign(do)),
                          fisher_p=round(SD.fisher_p(lo['upright_seen'], lo['n'] - lo['upright_seen'], hi['upright_seen'], hi['n'] - hi['upright_seen']), 4))
    out['control'] = ctl
    # where the misses are: by start, pooled
    st = lambda s: 'side' if s in ('left side down', 'right side down') else s
    out['by_start'] = {}
    for m in ('low', 'high'):
        for s in ('nose down', 'tail down', 'side', 'upside down', 'upside down, 45 to the left'):
            rows = [r for r in R if r['mass'] == m and st(r['start']) == s]
            if not rows: continue
            pm = per_drop(rows, P)[1].mean(0); ob = per_drop(rows, P)[2].mean(0)
            out['by_start'][f'{m} / {s}'] = dict(n=len(rows), predicted=dict(zip(SD.CLS, pm.round(2).tolist())), observed=dict(zip(SD.CLS, ob.round(2).tolist())))
    json.dump(out, open(os.path.join(ROOT, 'results', 'drop_scores_30cm.json'), 'w'), indent=1)
    L = ['# H4: the 30 cm redo against the four models committed before it', '',
         f"{out['n']} drops ({len(ALL) - len(R)} with an unknown mark left out). Naive predictor Brier {out['naive']}.", '',
         '| model | Brier | minus naive (95% CI) | top state right |', '|---|---|---|---|']
    for k, v in out['models'].items():
        L.append(f"| {k} | {v['brier']} | {v['minus_naive']} ({v['minus_naive_95'][0]} to {v['minus_naive_95'][1]}) | {v['top_hit']} |")
    h = out['H4']
    L += ['', f"**H4 (main minus dead): {h['main_minus_dead']} (95% CI {h['main_minus_dead_95'][0]} to {h['main_minus_dead_95'][1]}); "
          f"supported: {h['supported']}.** Measured-bounce minus dead: {out['measured_minus_dead']['mean']} (CI {out['measured_minus_dead']['ci95']}).", '',
          '| group | n | ' + ' | '.join(k.split(' ', 1)[0] for k in Ps) + ' | P(upright) main / seen |', '|---|---|' + '---|' * len(Ps) + '---|']
    for g, v in groups.items():
        L.append(f"| {g} | {v['n']} | " + ' | '.join(str(v['brier'][k]) for k in Ps) + f" | {v['p_upright_pred']} / {v['upright_seen']}/{v['n']} |")
    L += ['', '## Mass control (main model)', '']
    for b, c in ctl.items():
        L.append(f"- {b}: predicted P(upright) low {c['pred_low']} vs high {c['pred_high']}; seen {c['seen_low']} vs {c['seen_high']}; same direction {c['same_direction']}; Fisher p {c['fisher_p']}")
    L += ['', '## By start, pooled (main model, predicted > observed)', '']
    for k, v in out['by_start'].items():
        L.append(f"- {k} (n={v['n']}): " + ', '.join(f"{c} {v['predicted'][c]:.2f}>{v['observed'][c]:.2f}" for c in SD.CLS))
    open(os.path.join(ROOT, 'results', 'drop_scores_30cm.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
