"""Audit (2026-10-15, C15): are the surrogates' intervals right at the best designs, the ones a design search picks?

    python research/tumble/audit/surrogate_peak_check.py -> research/results/surrogate_peak_check.json and .md

H2's calibration check (90% intervals cover 85-95% of held-out designs) passed at 86.8%, over all designs. This checks
it where decisions are made: the 6 best designs of each sweep variant, whose P(upright) was rerun at 1000 drops
(posthoc_sweep_v2). Each is predicted by a surrogate trained on the other 399 designs. A miss counts only if it is
outside the 90% band widened by the rerun's own sampling noise (sqrt(p(1-p)/1000)).
  - surrogate.py (H2's GP: RBF, binomial noise) on the sweep it was built for (weightless shell, dead contact);
  - surrogate_gp.py (a second GP: Matern 5/2, fitted noise) on all three variants.
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); TUMBLE = os.path.dirname(HERE); ROOT = os.path.dirname(TUMBLE)
sys.path.insert(0, TUMBLE)
import sweep as SW, surrogate as SU, surrogate_gp as SG

Z90 = 1.645


def check(name, fit_predict, designs, top):
    X = np.array([[d['params'][k] for k in SW.KEYS] for d in designs])
    rows = []
    for r in top:
        x = np.array([[r['params'][k] for k in SW.KEYS]]); j = int(np.argmin(np.abs(X - x).sum(1))); keep = np.arange(len(designs)) != j
        m, s = fit_predict(keep, x); t = r['p_upright']; band = Z90 * np.sqrt(s ** 2 + t * (1 - t) / 1000)
        rows.append(dict(design='/'.join(f"{r['params'][k]:.2f}" if k == 'round' else f"{r['params'][k]:.0f}" for k in SW.KEYS),
                         sim_1000=t, surrogate=round(m, 3), miss_pts=round(100 * (t - m), 1), band90_pts=round(100 * band, 1), inside=bool(abs(t - m) <= band)))
    return dict(surrogate=name, inside=sum(r['inside'] for r in rows), n=len(rows), mean_miss_pts=round(float(np.mean([r['miss_pts'] for r in rows])), 1), rows=rows)


if __name__ == '__main__':
    V = json.load(open(os.path.join(ROOT, 'results', 'posthoc_sweep_v2.json')))['results']
    T = json.load(open(os.path.join(ROOT, 'results', 'tumble_truth.json')))['designs']
    out = []
    y = np.array([t['p_upright'] for t in T]); nn = np.array([t.get('n', 200) for t in T]); X = np.array([[t['params'][k] for k in SW.KEYS] for t in T])
    def su(keep, x):
        g = SU.GP(SW.LO, SW.HI).fit(X[keep], y[keep], SU.binom_noise(y[keep], nn[keep])); m, s = g.predict(x); return float(m[0]), float(s[0])
    out.append(dict(variant='weightless shell, dead (as the sweep ran)', **check('surrogate.py (H2)', su, T, V['weightless shell, dead (as the sweep ran)']['top_confirmed'])))
    for lab, v in V.items():
        Xv = SG.scale([r['params'] for r in v['all']]); yv = np.array([r['p_upright'] for r in v['all']])
        def sg(keep, x, Xv=Xv, yv=yv):
            g = SG.GP().fit(Xv[keep], yv[keep]); m, s = g.predict(SG.scale([dict(zip(SW.KEYS, x[0]))]))
            return float(m[0]), float(np.sqrt(max(s[0] ** 2 - g.sn2, 0)))       # the band for the simulator's true value
        out.append(dict(variant=lab, **check('surrogate_gp.py', sg, v['all'], v['top_confirmed'])))
    json.dump(out, open(os.path.join(ROOT, 'results', 'surrogate_peak_check.json'), 'w'), indent=1)
    L = ['# Surrogate intervals at the best designs (audit C15)', '',
         'Each of the 6 best designs predicted without its own data; truth is the 1000-drop rerun. "Inside" counts the 90% band',
         "widened by the rerun's own noise. A calibrated surrogate would have about 5 of 6 inside.", '',
         '| surrogate | sweep variant | inside 90% band | mean miss (pts; + = surrogate too low) |', '|---|---|---|---|']
    L += [f"| {o['surrogate']} | {o['variant']} | {o['inside']} of {o['n']} | {o['mean_miss_pts']:+.1f} |" for o in out]
    for o in out:
        L += ['', f"**{o['surrogate']}, {o['variant']}**", '', '| design (top/round/half-width/dz) | simulator, 1000 drops | surrogate | miss (pts) | 90% band (pts) |', '|---|---|---|---|---|']
        L += [f"| {r['design']} | {r['sim_1000']:.3f} | {r['surrogate']:.3f} | {r['miss_pts']:+.1f} | +-{r['band90_pts']} {'' if r['inside'] else '(outside)'} |" for r in o['rows']]
    open(os.path.join(ROOT, 'results', 'surrogate_peak_check.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L[:12]))
