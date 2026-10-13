"""POST HOC (added 2026-10-13 after the pre-registered friction mutant came back undetected): sentinel simulations for
hidden physics changes that move P(upright) more than friction did.

The pre-registered result stands as recorded in surrogate_summary.json: friction cut to 0.4x changed P(upright) by at
most ~0.04 at the 8 sentinel designs, inside the surrogate's intervals, so the sentinels flagged 0 of 8, the same as
the control. This script asks the follow-up question, and is labelled post hoc wherever it is reported: do the same
sentinels catch a hidden change that does matter?
  spin x3   the tumbles start with up to 9 rad/s of spin, not 3 (a harder fall than the surrogate was trained on)
  rw 75     wheels 150 mm across, not 110 (a design change the surrogate's inputs don't carry)

    python research/tumble/posthoc_sentinels.py   -> research/results/posthoc_sentinels.json
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import surrogate as SG
import tumble as T

if __name__ == '__main__':
    TT = json.load(open(os.path.join(ROOT, 'results', 'tumble_truth.json')))
    keys, lo, hi, truth = TT['keys'], TT['lo'], TT['hi'], TT['designs']
    ev, g, (X, y, nn, te) = SG.evaluate(truth, keys, lo, hi, 120, np.random.default_rng(7))   # the same fit
    pick = np.random.default_rng(11).choice(len(te), 8, replace=False)                      # the same sentinels
    designs = [X[te[j]] for j in pick]
    out = {}
    for label, extra, spin in (('control', {}, 3.0), ('spin x3', {}, 9.0), ('rw 75', {'rw': 75.0}, 3.0)):
        rows, miss = [], 0
        for i, x in enumerate(designs):
            p = dict(zip(keys, x)); p.update(extra)
            r = T.trials(p, 200, seed=5000 + i, spin=spin)
            m, sd = g.predict(x[None, :])
            tot = np.sqrt(sd[0] ** 2 + SG.binom_noise(r['p_upright'], 200))
            o = bool(abs(r['p_upright'] - m[0]) > 1.645 * tot); miss += o
            rows.append(dict(pred=round(float(m[0]), 3), sim=r['p_upright'], outside=o))
        shift = float(np.mean([abs(rw['sim'] - rw['pred']) for rw in rows]))
        out[label] = dict(outside=miss, of=len(designs), mean_abs_shift=round(shift, 3), rows=rows)
        print(f'{label:<8} flagged {miss}/8, mean |sim - surrogate| {shift:.3f}', flush=True)
    out['note'] = 'post hoc; the pre-registered friction mutant result is in surrogate_summary.json'
    json.dump(out, open(os.path.join(ROOT, 'results', 'posthoc_sentinels.json'), 'w'), indent=1)
