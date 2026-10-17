"""H3c: score the 15 cm drops (data/drops/run4_15cm.csv) against the six models committed before them (PROTOCOL.md H3c
and its three amendments).

    python research/tumble/score_15cm.py -> research/results/drop_scores_15cm.json and .md

The rules are score_30cm.py's (Brier against the naive predictor, paired bootstrap, Zach's nose/tail mapped by the
physical end, left and right merged; unknown marks left out). Primary, as amended before any 15 cm drop: the converged
hard floor (bounce 0.31) scores a lower Brier than the dead soft floor and than naive, with paired bootstrap 95% CIs
excluding 0. Secondary, no direction predicted: the 0.39 hard floor (the ball's measured bounce) against the 0.31
one, the 0.55 one and the fitted soft bounce; the 0.31 against the 0.55 and the fitted soft bounce.
The best possible score is sim_vs_reality's: the expected Brier of a model that knew each cell's true odds,
estimated without bias from the drops' own counts.
"""
import os, sys, csv, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import score_drops as SD
from score_30cm import per_drop

PRIMARY, CTRL = 'hard floor 0.31, converged (primary)', 'dead soft floor (control)'
MODELS = {PRIMARY: 'drop_predictions_15cm_hard_floor_converged.json', CTRL: 'drop_predictions_15cm_dead.json',
          'soft floor, bounce fitted at 6 cm': 'drop_predictions_15cm_bounce_fit.json',
          'hard floor 0.39, the ball measured': 'drop_predictions_15cm_hard_floor_ball2.json',
          'hard floor 0.55, the ball rough': 'drop_predictions_15cm_hard_floor_ball.json',
          'hard floor 0.31, 0.5 ms (unconverged, C14)': 'drop_predictions_15cm_hard_floor.json'}
SECONDARY = [('hard floor 0.39, the ball measured', PRIMARY), ('hard floor 0.39, the ball measured', 'hard floor 0.55, the ball rough'),
             ('hard floor 0.39, the ball measured', 'soft floor, bounce fitted at 6 cm'), (PRIMARY, 'hard floor 0.55, the ball rough'),
             (PRIMARY, 'soft floor, bounce fitted at 6 cm')]


def best_possible(R):
    """expected Brier of a model with each (body, mass, start) cell's true odds; 1 - sum p^2, unbiased from counts"""
    O = np.array([SD.onehot(SD.MARK2CLS[r['mark']]) for r in R]); cells = {}
    for i, r in enumerate(R):
        cells.setdefault((r['body'], r['mass'], r['start']), []).append(i)
    tot = 0.0
    for idx in cells.values():
        c = O[idx].sum(0); m = len(idx)
        tot += m * (1 - ((c ** 2).sum() - m) / (m * (m - 1)))
    return tot / len(R)


if __name__ == '__main__':
    ALL = list(csv.DictReader(open(os.path.join(ROOT, 'data', 'drops', 'run4_15cm.csv'), encoding='utf-8')))
    R = [r for r in ALL if r['mark'] in SD.MARK2CLS]
    Ps = {k: json.load(open(os.path.join(ROOT, 'results', f))) for k, f in MODELS.items()}
    rng = np.random.default_rng(0); B = [rng.integers(0, len(R), len(R)) for _ in range(4000)]
    naive = np.array([((SD.naive(r['start']) - SD.onehot(SD.MARK2CLS[r['mark']])) ** 2).sum() for r in R])
    br = {k: per_drop(R, P)[0] for k, P in Ps.items()}
    ci = lambda d: [round(float(q), 3) for q in np.percentile([d[i].mean() for i in B], [2.5, 97.5])]
    out = dict(n=len(R), left_out=len(ALL) - len(R), naive=round(float(naive.mean()), 3), best_possible=round(best_possible(R), 3), models={})
    for k in Ps:
        _, pm, o = per_drop(R, Ps[k])
        out['models'][k] = dict(brier=round(float(br[k].mean()), 3), minus_naive=round(float((br[k] - naive).mean()), 3),
                                minus_naive_95=ci(br[k] - naive), top_hit=round(float(np.mean(pm.argmax(1) == o.argmax(1))), 3))
    d = br[PRIMARY] - br[CTRL]
    out['primary'] = dict(primary_minus_dead=round(float(d.mean()), 3), primary_minus_dead_95=ci(d),
                          primary_minus_naive_95=out['models'][PRIMARY]['minus_naive_95'],
                          supported=bool(ci(d)[1] < 0 and out['models'][PRIMARY]['minus_naive_95'][1] < 0))
    out['secondary'] = [dict(a=a, b=b, a_minus_b=round(float((br[a] - br[b]).mean()), 3), ci95=ci(br[a] - br[b])) for a, b in SECONDARY]
    # groups and the mass control, for the primary model
    P = Ps[PRIMARY]; groups = {}
    for b in ('E1_tub', 'E2_dome', 'E3_tall'):
        for m in ('low', 'high'):
            rows = [r for r in R if r['body'] == b and r['mass'] == m]
            if not rows: continue
            _, pm, o = per_drop(rows, P)
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
    st = lambda s: 'side' if s in ('left side down', 'right side down') else s
    out['by_start'] = {}
    for m in ('low', 'high'):
        for s in ('nose down', 'tail down', 'side', 'upside down', 'upside down, 45 to the left'):
            rows = [r for r in R if r['mass'] == m and st(r['start']) == s]
            if not rows: continue
            pm = per_drop(rows, P)[1].mean(0); ob = per_drop(rows, P)[2].mean(0)
            out['by_start'][f'{m} / {s}'] = dict(n=len(rows), predicted=dict(zip(SD.CLS, pm.round(2).tolist())), observed=dict(zip(SD.CLS, ob.round(2).tolist())))
    json.dump(out, open(os.path.join(ROOT, 'results', 'drop_scores_15cm.json'), 'w'), indent=1)
    L = ['# H3c: the 15 cm drops (from the drop stand) against the six models committed before them', '',
         f"{out['n']} drops ({out['left_out']} with an unknown mark left out). Naive predictor Brier {out['naive']}; "
         f"best possible (a model with each cell's true odds) {out['best_possible']}.", '',
         '| model | Brier | minus naive (95% CI) | top state right |', '|---|---|---|---|']
    for k, v in out['models'].items():
        L.append(f"| {k} | {v['brier']} | {v['minus_naive']} ({v['minus_naive_95'][0]} to {v['minus_naive_95'][1]}) | {v['top_hit']} |")
    h = out['primary']
    L += ['', f"**Primary (converged 0.31 hard floor minus dead): {h['primary_minus_dead']} (95% CI {h['primary_minus_dead_95'][0]} to "
          f"{h['primary_minus_dead_95'][1]}); minus naive CI {h['primary_minus_naive_95']}; supported: {h['supported']}.**", '',
          '## Secondary, no direction predicted', '']
    for s in out['secondary']:
        L.append(f"- {s['a']} minus {s['b']}: {s['a_minus_b']} (95% CI {s['ci95'][0]} to {s['ci95'][1]})")
    L += ['', '| group | n | ' + ' | '.join(Ps) + ' | P(upright) primary / seen |', '|---|---|' + '---|' * len(Ps) + '---|']
    for g, v in groups.items():
        L.append(f"| {g} | {v['n']} | " + ' | '.join(str(v['brier'][k]) for k in Ps) + f" | {v['p_upright_pred']} / {v['upright_seen']}/{v['n']} |")
    L += ['', '## Mass control (primary model)', '']
    for b, c in ctl.items():
        L.append(f"- {b}: predicted P(upright) low {c['pred_low']} vs high {c['pred_high']}; seen {c['seen_low']} vs {c['seen_high']}; same direction {c['same_direction']}; Fisher p {c['fisher_p']}")
    L += ['', '## By start, pooled (primary model, predicted > observed)', '']
    for k, v in out['by_start'].items():
        L.append(f"- {k} (n={v['n']}): " + ', '.join(f"{c} {v['predicted'][c]:.2f}>{v['observed'][c]:.2f}" for c in SD.CLS))
    open(os.path.join(ROOT, 'results', 'drop_scores_15cm.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
