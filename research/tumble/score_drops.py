"""Workstream E: score the physical drops against the predictions committed before them (drop_predictions.json, 6 cm).

    python research/tumble/score_drops.py  -> research/results/drop_scores.json and drop_scores.md

Data: run 1, mass high (coins first): E1 from the video (data/drops/video_E1.csv; Zach: go with the video), plus
the 3 nose-down drops before the video started, from the sheet; E2 and E3 from the sheet (data/drops/run1.csv).
Run 2, mass low (spacer first): data/drops/run2.csv.

Scoring as pre-registered in PROTOCOL.md: the Brier score of the predicted rest-state probabilities against what
happened, against a naive predictor ("it stays on the face it was dropped on"); the share of drops whose most likely
predicted state was the one seen; and the physical control (mass low vs high). Choices made at scoring time, all
written down before the scores were computed:
  1. Nose and tail by the physical end. Zach's "nose" is the blunt end (seen in the E1 video), the model's is the
     head end (+X). So his nose-down start is the model's tail-down start and vice versa. For the rest states the
     names are dropped: 'head up' (+X up) and 'head down'. tumble.classify calls +X up 'nose down', which is
     Zach's N as well (blunt end down).
  2. Left and right merged into 'side', for starts and for rest states. All three bodies are mirror-symmetric, so the
     two are the same physics, and the model's left/right start names don't match its own rest names. A side start is
     predicted by the average of the model's two side starts (400 simulated drops).
  3. The naive predictor for the 45-degree start (halfway between upside down and on its side) splits 0.5/0.5
     between inverted and side.
  4. A group with 6 marks (E2, mass low, left side down) keeps all 6.
"""
import os, csv, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
CLS = ['upright', 'inverted', 'side', 'head up', 'head down']
SIM2CLS = {'upright': 'upright', 'inverted': 'inverted', 'left side': 'side', 'right side': 'side',
           'nose down': 'head up', 'nose up': 'head down'}            # tumble.classify's names -> physical
MARK2CLS = {'O': 'upright', 'X': 'inverted', 'L': 'side', 'R': 'side', 'N': 'head up', 'F': 'head up', 'T': 'head down'}
START2SIM = {'nose down': ['tail down'], 'tail down': ['nose down'], 'left side down': ['left side down', 'right side down'],
             'right side down': ['left side down', 'right side down'], 'upside down': ['upside down'],
             'upside down, 45 to the left': ['upside down, 45 to the left']}
NAIVE = {'nose down': {'head up': 1.0}, 'tail down': {'head down': 1.0}, 'left side down': {'side': 1.0},
         'right side down': {'side': 1.0}, 'upside down': {'inverted': 1.0},
         'upside down, 45 to the left': {'inverted': 0.5, 'side': 0.5}}


def drops():
    D = os.path.join(ROOT, 'data', 'drops'); out = []
    vid = list(csv.DictReader(open(os.path.join(D, 'video_E1.csv'), encoding='utf-8')))
    sheet = list(csv.DictReader(open(os.path.join(D, 'run1.csv'), encoding='utf-8')))
    for r in sheet:
        if r['body'] == 'E1_tub' and r['start'] == 'nose down' and int(r['drop']) <= 3:
            out.append(dict(body='E1_tub', mass='high', start=r['start'], mark=r['mark'], src='sheet (before the video)'))
    for r in vid:
        out.append(dict(body='E1_tub', mass='high', start=r['start_as_dropped'], mark=r['video_rest'], src='video'))
    for r in sheet:
        if r['body'] != 'E1_tub':
            out.append(dict(body=r['body'], mass='high', start=r['start'], mark=r['mark'], src='sheet'))
    for r in csv.DictReader(open(os.path.join(D, 'run2.csv'), encoding='utf-8')):
        out.append(dict(body=r['body'], mass='low', start=r['start'], mark=r['mark'], src='sheet'))
    return out


def predicted(P, body, mass, start, field='p'):
    v = np.zeros(len(CLS)); sims = START2SIM[start]
    for a in sims:
        for k, p in P[f'{body} mass {mass}']['by_attitude'][a][field].items():
            v[CLS.index(SIM2CLS[k])] += p / len(sims)
    return v


def onehot(c):
    v = np.zeros(len(CLS)); v[CLS.index(c)] = 1; return v


def naive(start):
    v = np.zeros(len(CLS))
    for k, p in NAIVE[start].items(): v[CLS.index(k)] = p
    return v


def score(rows, P, rng, field='p'):
    pm = np.array([predicted(P, r['body'], r['mass'], r['start'], field) for r in rows])
    pn = np.array([naive(r['start']) for r in rows]); o = np.array([onehot(MARK2CLS[r['mark']]) for r in rows])
    bm, bn = ((pm - o) ** 2).sum(1), ((pn - o) ** 2).sum(1)
    boot = [np.mean((bm - bn)[i]) for i in (rng.integers(0, len(rows), len(rows)) for _ in range(4000))]
    return dict(n=len(rows), brier_model=round(float(bm.mean()), 3), brier_naive=round(float(bn.mean()), 3),
                diff=round(float((bm - bn).mean()), 3), diff_95=[round(float(q), 3) for q in np.percentile(boot, [2.5, 97.5])],
                top_hit_model=round(float(np.mean(pm.argmax(1) == o.argmax(1))), 3),
                top_hit_naive=round(float(np.mean(pn.argmax(1) == o.argmax(1))), 3))


def fisher_p(a, b, c, d):
    """two-sided Fisher exact test on [[a, b], [c, d]]"""
    from scipy.stats import fisher_exact
    return float(fisher_exact([[a, b], [c, d]])[1])


if __name__ == '__main__':
    P = json.load(open(os.path.join(ROOT, 'results', 'drop_predictions.json')))
    R = drops(); rng = np.random.default_rng(0)
    out = {'n_drops': len(R), 'classes': CLS, 'groups': {}, 'friction': {}, 'control': {}}
    groups = [(b, m) for b in ('E1_tub', 'E2_dome', 'E3_tall') for m in ('low', 'high')]
    for b, m in groups:
        out['groups'][f'{b} mass {m}'] = score([r for r in R if r['body'] == b and r['mass'] == m], P, rng)
    out['all'] = score(R, P, rng)
    for f in ('p_lowmu', 'p_highmu'):
        out['friction'][f] = score(R, P, rng, f)
    for b in ('E1_tub', 'E2_dome', 'E3_tall'):
        c = {}
        for m in ('low', 'high'):
            rows = [r for r in R if r['body'] == b and r['mass'] == m]
            pm = np.mean([predicted(P, b, m, r['start']) for r in rows], 0)
            ob = np.mean([onehot(MARK2CLS[r['mark']]) for r in rows], 0)
            c[m] = dict(n=len(rows), predicted={k: round(float(v), 3) for k, v in zip(CLS, pm)},
                        observed={k: round(float(v), 3) for k, v in zip(CLS, ob)},
                        upright=int(sum(MARK2CLS[r['mark']] == 'upright' for r in rows)))
        dp = c['low']['predicted']['upright'] - c['high']['predicted']['upright']
        do = c['low']['observed']['upright'] - c['high']['observed']['upright']
        c['predicted_shift_upright'] = round(dp, 3); c['observed_shift_upright'] = round(do, 3)
        c['same_direction'] = bool(np.sign(dp) == np.sign(do))
        c['fisher_p_upright'] = round(fisher_p(c['low']['upright'], c['low']['n'] - c['low']['upright'],
                                               c['high']['upright'], c['high']['n'] - c['high']['upright']), 4)
        out['control'][b] = c
    json.dump(out, open(os.path.join(ROOT, 'results', 'drop_scores.json'), 'w'), indent=1)

    L = ['# Drop scores (physical drops against the predictions committed before them)', '',
         f"{len(R)} drops: 3 bodies x mass low and high, 6 starts x 5 drops, from 6 cm. Brier score: 0 is perfect, "
         "2 is certain and wrong; lower is better. The naive predictor says it stays on the face it was dropped on.", '',
         '| group | drops | Brier, model | Brier, naive | model - naive (95% CI) | top state right, model | naive |',
         '|---|---|---|---|---|---|---|']
    for k, s in list(out['groups'].items()) + [('all', out['all'])]:
        L.append(f"| {k} | {s['n']} | {s['brier_model']} | {s['brier_naive']} | {s['diff']} ({s['diff_95'][0]} to {s['diff_95'][1]}) | "
                 f"{s['top_hit_model']} | {s['top_hit_naive']} |")
    L += ['', 'At 0.65x and 1.5x friction (all drops): ' + ', '.join(
        f"{f}: Brier {s['brier_model']}" for f, s in out['friction'].items()), '',
          '## The physical control: P(upright), mass low vs high', '',
          '| body | predicted low | predicted high | observed low | observed high | same direction | Fisher p |', '|---|---|---|---|---|---|---|']
    for b, c in out['control'].items():
        L.append(f"| {b} | {c['low']['predicted']['upright']} | {c['high']['predicted']['upright']} | "
                 f"{c['low']['upright']}/{c['low']['n']} | {c['high']['upright']}/{c['high']['n']} | {c['same_direction']} | {c['fisher_p_upright']} |")
    L += ['', '## Rest states, predicted vs observed (averaged over the drops as made)', '']
    for b, c in out['control'].items():
        for m in ('low', 'high'):
            L.append(f"- {b} mass {m}: " + ', '.join(f"{k} {c[m]['predicted'][k]:.2f} / {c[m]['observed'][k]:.2f}" for k in CLS))
    open(os.path.join(ROOT, 'results', 'drop_scores.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
