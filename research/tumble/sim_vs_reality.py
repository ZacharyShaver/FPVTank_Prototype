"""Simulation vs the real drops, side by side, for review: every model against the 6 cm and 30 cm drops.

    python research/tumble/sim_vs_reality.py -> research/results/sim_vs_reality.md, research/figures/sim_vs_reality.png

Scoring is score_drops.py's (Zach's nose/tail mapped by the physical end, left and right merged). Here the two end
rests ('head up', 'head down') are merged too, as 'on an end'. A model's "predicted %" for a group is the average of
its predicted probability over the drops in that group, so it is directly comparable with the share seen.
"""
import os, sys, csv, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import score_drops as SD

OUT = ['upright', 'upside down', 'on its side', 'on an end']
BODY = {'E1_tub': 'E1 (hill)', 'E2_dome': 'E2 (oval)', 'E3_tall': 'E3 (rounded square)'}
MODELS = ['Old start', 'Dead', 'Fitted', 'Hard .31', 'Hard .39']
KEY = {'Old start': "the original model: MuJoCo's default floor, with the start-heading bug (B1)",
       'Dead': "start fixed; MuJoCo's default floor: soft (sinks 7-17 mm) and dead (bounce 0.13)",
       'Fitted': 'start fixed; soft floor with its bounce fitted to the 6 cm drops (0.55)',
       'Hard .31': 'start fixed; hard floor (sinks under 2 mm), bounce 0.31 measured from the E3 video',
       'Hard .39': 'start fixed; hard floor, bounce 0.39 measured from the PLA ball video'}
FILES = {'6 cm': ['drop_predictions.json', 'drop_predictions_fixed_attitudes.json', 'drop_predictions_6cm_bounce_fit.json',
                  'drop_predictions_6cm_hard_floor_converged.json', 'drop_predictions_6cm_hard_floor_ball2.json'],
         '30 cm': ['drop_predictions_30cm.json', 'drop_predictions_30cm_dead.json', 'drop_predictions_30cm_bounce_fit.json',
                   'drop_predictions_30cm_hard_floor_converged.json', 'drop_predictions_30cm_hard_floor_ball2.json']}
WHEN = {'6 cm': ['before', 'after', 'fitted to them', 'after', 'after'], '30 cm': ['before', 'before', 'before', 'after', 'after']}
STARTS = ['nose down', 'tail down', 'left side down', 'right side down', 'upside down', 'upside down, 45 to the left']


def four(v):
    return np.r_[v[0], v[1], v[2], v[3] + v[4]]


def load():
    six = SD.drops()
    thirty = [r for r in csv.DictReader(open(os.path.join(ROOT, 'data', 'drops', 'run3_30cm.csv'), encoding='utf-8')) if r['mark'] in SD.MARK2CLS]
    H = {}
    for h, rows in (('6 cm', six), ('30 cm', thirty)):
        obs = np.array([four(SD.onehot(SD.MARK2CLS[r['mark']])) for r in rows])
        pred = {m: np.array([four(SD.predicted(json.load(open(os.path.join(ROOT, 'results', f))), r['body'], r['mass'], r['start'])) for r in rows])
                for m, f in zip(MODELS, FILES[h])}
        naive = np.array([four(SD.naive(r['start'])) for r in rows])
        full = {m: np.array([SD.predicted(json.load(open(os.path.join(ROOT, 'results', f))), r['body'], r['mass'], r['start']) for r in rows])
                for m, f in zip(MODELS, FILES[h])}
        o5 = np.array([SD.onehot(SD.MARK2CLS[r['mark']]) for r in rows]); n5 = np.array([SD.naive(r['start']) for r in rows])
        H[h] = dict(rows=rows, obs=obs, pred=pred, naive=naive,
                    brier={m: float(((full[m] - o5) ** 2).sum(1).mean()) for m in MODELS} | {'Naive': float(((n5 - o5) ** 2).sum(1).mean())},
                    top={m: float(np.mean(full[m].argmax(1) == o5.argmax(1))) for m in MODELS} | {'Naive': float(np.mean(n5.argmax(1) == o5.argmax(1)))})
    return H


def pct(x):
    return f'{100 * x:.0f}%'


def table(head, rows):
    return ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows]


if __name__ == '__main__':
    H = load()
    L = ['# Simulation vs the real drops', '',
         'Every model scored against the same real drops: **6 cm, 181 drops** (runs 1 and 2) and **30 cm, 180 drops** (run 3,',
         'the marked redo). Each drop is one body, one weight position (low or high), one of six starts, and how it came to rest.', '',
         '**The models** (columns below). "Made" says whether the model\'s predictions were committed before or after those drops:', '']
    L += table(['model', 'what it is', 'made, 6 cm', 'made, 30 cm'], [[m, KEY[m], WHEN['6 cm'][i], WHEN['30 cm'][i]] for i, m in enumerate(MODELS)])
    L += ['', 'Only predictions made before the drops are real tests. "After" means the drops had been seen, but nothing in the model',
          'was tuned to them; "fitted" means it was tuned to them.', '',
          '## 1. Overall score', '',
          '**Brier score:** how far the predicted odds were from what happened, averaged over drops. 0 is perfect; 2 is',
          'certain and wrong every time. Lower is better. **Naive** is the guess "it stays on the face it was dropped on".',
          '**Top pick right:** how often the model\'s single most likely outcome is what happened.', '']
    rows = []
    for m in ['Naive'] + MODELS:
        rows.append([m] + [f"{H[h]['brier'][m]:.3f}" for h in H] + [pct(H[h]['top'][m]) for h in H])
    L += table(['model', 'Brier, 6 cm', 'Brier, 30 cm', 'top pick right, 6 cm', 'top pick right, 30 cm'], rows)

    L += ['', '## 2. How often it lands upright, by body and weight', '',
          'Real: drops that ended upright, out of the group. Models: the predicted chance, averaged over the same drops.', '']
    for h in H:
        R = H[h]; rows = []
        for b in BODY:
            for w in ('low', 'high'):
                idx = [i for i, r in enumerate(R['rows']) if r['body'] == b and r['mass'] == w]
                k = int(R['obs'][idx, 0].sum())
                rows.append([f'{BODY[b]}, weight {w}', f'{k}/{len(idx)} = {pct(k / len(idx))}'] + [pct(R['pred'][m][idx, 0].mean()) for m in MODELS])
        allk = int(R['obs'][:, 0].sum())
        rows.append(['**all**', f'**{allk}/{len(R["rows"])} = {pct(allk / len(R["rows"]))}**'] + [f"**{pct(R['pred'][m][:, 0].mean())}**" for m in MODELS])
        L += [f'**{h}**', ''] + table(['group', 'real'] + MODELS, rows) + ['']

    L += ['## 3. Where they end up: the whole mix', '', 'Share of all drops ending in each rest state.', '']
    for h in H:
        R = H[h]
        rows = [['**real**'] + [f'**{pct(x)}**' for x in R['obs'].mean(0)]] + [[m] + [pct(x) for x in R['pred'][m].mean(0)] for m in MODELS]
        L += [f'**{h}**', ''] + table(['', *OUT], rows) + ['']

    L += ['## 4. Upright, by how it was dropped', '', 'All bodies and weights together (30 drops per start).', '']
    for h in H:
        R = H[h]; rows = []
        for s in STARTS:
            idx = [i for i, r in enumerate(R['rows']) if r['start'] == s]
            if not idx: continue
            k = int(R['obs'][idx, 0].sum())
            rows.append([s, f'{k}/{len(idx)} = {pct(k / len(idx))}'] + [pct(R['pred'][m][idx, 0].mean()) for m in MODELS])
        L += [f'**{h}**', ''] + table(['start (your nose = the blunt end)', 'real'] + MODELS, rows) + ['']

    L += ['## 5. The weight effect: upright with the weight low, minus with it high', '',
          'In percentage points: +20 means 20 points more drops upright with the weight low.', '']
    rows = []
    for h in H:
        R = H[h]
        for b in BODY:
            lo = [i for i, r in enumerate(R['rows']) if r['body'] == b and r['mass'] == 'low']; hi = [i for i, r in enumerate(R['rows']) if r['body'] == b and r['mass'] == 'high']
            d = lambda a: a[lo, 0].mean() - a[hi, 0].mean()
            rows.append([h, BODY[b], f"{100 * d(R['obs']):+.0f} pts"] + [f"{100 * d(R['pred'][m]):+.0f}" for m in MODELS])
    L += table(['height', 'body', 'real'] + MODELS, rows)

    L += ['', '## 6. Biggest single misses (Hard .31, the model the 15 cm test is built on)', '',
          'Each cell is one body, weight and start: 5 drops. With 5 drops the real share is coarse (0, 20, 40 ... 100%), and',
          'even a perfect model would miss a cell by 20-40 points by chance now and then.', '']
    for h in H:
        R = H[h]; cells = []
        for b in BODY:
            for w in ('low', 'high'):
                for s in STARTS:
                    idx = [i for i, r in enumerate(R['rows']) if r['body'] == b and r['mass'] == w and r['start'] == s]
                    if not idx: continue
                    o = R['obs'][idx].mean(0); p = R['pred']['Hard .31'][idx].mean(0)
                    cells.append((abs(o[0] - p[0]), b, w, s, len(idx), o, p))
        cells.sort(key=lambda c: -c[0])
        rows = [[BODY[b], w, s, f'{int(round(o[0] * n))}/{n} upright', pct(p[0]), ', '.join(f'{OUT[j]} {pct(o[j])}' for j in np.argsort(-o) if o[j] > 0)]
                for _, b, w, s, n, o, p in cells[:6]]
        L += [f'**{h}**', ''] + table(['body', 'weight', 'start', 'real', 'predicted upright', 'what really happened'], rows) + ['']
    L += ['Figure: `figures/sim_vs_reality.png`, predicted vs real upright share for every cell.']
    open(os.path.join(ROOT, 'results', 'sim_vs_reality.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')

    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    show = ['Dead', 'Fitted', 'Hard .31', 'Hard .39']
    fig, ax = plt.subplots(2, 4, figsize=(15, 7.6), sharex=True, sharey=True)
    for i, h in enumerate(H):
        R = H[h]
        for j, m in enumerate(show):
            a = ax[i, j]; a.plot([0, 1], [0, 1], color='0.6', lw=1, zorder=0)
            for b, c in zip(BODY, ('#1b9e77', '#d95f02', '#7570b3')):
                for w, mk in (('low', 'o'), ('high', '^')):
                    xs, ys = [], []
                    for s in STARTS:
                        idx = [k for k, r in enumerate(R['rows']) if r['body'] == b and r['mass'] == w and r['start'] == s]
                        if idx: xs.append(R['pred'][m][idx, 0].mean()); ys.append(R['obs'][idx, 0].mean())
                    a.scatter(xs, ys, c=c, marker=mk, s=34, alpha=0.8, label=f'{BODY[b]}, weight {w}' if i == 0 and j == 0 else None)
            a.set_title(f"{h}: {m}  (Brier {R['brier'][m]:.2f})", fontsize=10); a.set_xlim(-0.03, 1.03); a.set_ylim(-0.03, 1.03)
            if i == 1: a.set_xlabel('simulation: chance of landing upright')
            if j == 0: a.set_ylabel('real: share that landed upright')
    fig.legend(loc='lower center', ncol=6, fontsize=9, frameon=False)
    fig.suptitle('Each dot is one body, weight and start (5 drops). On the grey line, the simulation matched the real drops.', fontsize=11)
    fig.tight_layout(rect=(0, 0.05, 1, 0.96))
    fig.savefig(os.path.join(ROOT, 'figures', 'sim_vs_reality.png'), dpi=110)
    print('\n'.join(L))
