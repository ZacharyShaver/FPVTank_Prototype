"""EXPLORATORY (2026-10-15): a data-driven surrogate of the shape sweep. How far is it from the simulator?

    python research/tumble/surrogate_gp.py -> research/results/surrogate_gp.json and .md

The surrogate is a Gaussian process: 4 shape settings (top, round, width, dz; scaled to 0-1 over the sweep's range)
in, the simulator's P(upright) out. Matern 5/2 kernel with one length scale per setting, plus a noise term for the
simulator's own Monte Carlo noise; settings by maximum marginal likelihood (numpy/scipy, no extra packages).

Trained on the 400 sweep designs (posthoc_sweep_v2.json, 200 simulated drops each), for each of its three physics
variants. Checks:
  1. 5-fold cross-validation: each design is predicted by a surrogate that never saw it.
  2. The noise floor: a design's 200-drop value is itself off by sqrt(p(1-p)/200) from the simulator's true value, so
     no surrogate can show a smaller error against it than that. A surrogate near the floor is as good as the
     simulator's own 200-drop answer.
  3. Sharper truth: the top 6 designs and the tub were rerun at 1000 drops. Each is predicted by a surrogate trained
     without it. (The tub's round 0.08 is just outside the sweep's 0.1-1.0: a small extrapolation.)
  4. Its own error bars: the share of held-out designs inside the surrogate's 95% interval should be about 95%.
  Baselines: the training mean, and a straight-line fit of the 4 settings.
"""
import os, sys, json, time
import numpy as np
from scipy.optimize import minimize
from scipy.linalg import cho_factor, cho_solve
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import sweep as SW
LO, HI = np.array(SW.LO), np.array(SW.HI)


def kern(A, B, ls, sf2):
    d = np.sqrt((((A[:, None, :] - B[None, :, :]) / ls) ** 2).sum(-1)); s = np.sqrt(5) * d
    return sf2 * (1 + s + s ** 2 / 3) * np.exp(-s)


class GP:
    def fit(self, X, y):
        self.X, self.mu = X, y.mean(); r = y - self.mu
        def nll(th):
            ls, sf2, sn2 = np.exp(th[:4]), np.exp(th[4]), np.exp(th[5])
            K = kern(X, X, ls, sf2) + (sn2 + 1e-8) * np.eye(len(X))
            try: c = cho_factor(K)
            except np.linalg.LinAlgError: return 1e10
            return 0.5 * r @ cho_solve(c, r) + np.log(np.diag(c[0])).sum()
        best = None
        for s in range(6):
            th0 = np.r_[np.log(np.random.default_rng(s).uniform(0.2, 1.5, 4)), np.log(r.var()), np.log(r.var() / 10)]
            o = minimize(nll, th0, method='L-BFGS-B', bounds=[(-4, 3)] * 4 + [(-10, 2), (-14, 0)])
            if best is None or o.fun < best.fun: best = o
        self.ls, self.sf2, self.sn2 = np.exp(best.x[:4]), np.exp(best.x[4]), np.exp(best.x[5])
        self.c = cho_factor(kern(X, X, self.ls, self.sf2) + (self.sn2 + 1e-8) * np.eye(len(X))); self.a = cho_solve(self.c, r)
        return self

    def predict(self, Z):
        k = kern(Z, self.X, self.ls, self.sf2); m = self.mu + k @ self.a
        v = self.sf2 - (k * cho_solve(self.c, k.T).T).sum(1)
        return m, np.sqrt(np.maximum(v, 0) + self.sn2)                     # sd of a new 200-drop run


def scale(P):
    return (np.array([[p[k] for k in SW.KEYS] for p in P]) - LO) / (HI - LO)


def linear(Xtr, ytr, Xte):
    A = np.c_[np.ones(len(Xtr)), Xtr]; w = np.linalg.lstsq(A, ytr, rcond=None)[0]
    return np.c_[np.ones(len(Xte)), Xte] @ w


if __name__ == '__main__':
    D = json.load(open(os.path.join(ROOT, 'results', 'posthoc_sweep_v2.json')))['results']
    out = {}; L = ['# Surrogate vs simulator: a Gaussian process trained on the shape sweep (exploratory)', '',
                   'Errors in percentage points of P(upright). Every number is for designs the surrogate did not see.', '']
    for lab, v in D.items():
        X = scale([r['params'] for r in v['all']]); y = np.array([r['p_upright'] for r in v['all']])
        idx = np.random.default_rng(0).permutation(len(y)); folds = np.array_split(idx, 5)
        pg, sg, pl = np.zeros_like(y), np.zeros_like(y), np.zeros_like(y); pm = np.zeros_like(y)
        for f in folds:
            tr = np.setdiff1d(idx, f); g = GP().fit(X[tr], y[tr])
            pg[f], sg[f] = g.predict(X[f]); pl[f] = linear(X[tr], y[tr], X[f]); pm[f] = y[tr].mean()
        rmse = lambda p: float(np.sqrt(np.mean((p - y) ** 2)) * 100); mae = lambda p: float(np.mean(np.abs(p - y)) * 100)
        floor = float(np.sqrt(np.mean(y * (1 - y) / 200)) * 100)
        # sharper truth: the 1000-drop reruns, each predicted without its own design
        sharp = []
        for r in v['top_confirmed'] + [v['tub']]:
            x = scale([r['params']]); keep = [j for j, q in enumerate(v['all']) if q['i'] != r['i']]
            g = GP().fit(X[keep], y[keep]); m, s = g.predict(x)
            sharp.append(dict(design='tub' if r['i'] < 0 else '/'.join(f"{r['params'][k]:.2f}" if k == 'round' else f"{r['params'][k]:.0f}" for k in SW.KEYS),
                              sim_1000=r['p_upright'], surrogate=round(float(m[0]), 3), err_pts=round(float(m[0] - r['p_upright']) * 100, 1),
                              sim_noise_pts=round(float(np.sqrt(r['p_upright'] * (1 - r['p_upright']) / 1000)) * 100, 1)))
        # do the held-out predictions still rank the best designs near the top?
        rank = {r['i']: int((pg > pg[[j for j, q in enumerate(v['all']) if q['i'] == r['i']][0]]).sum()) + 1 for r in v['top_confirmed']}
        for s_, r in zip(sharp, v['top_confirmed']): s_['surrogate_rank_of_400'] = rank[r['i']]
        # speed: the surrogate measured here; the simulator measured once (sim_speed below)
        g = GP().fit(X, y); Z = np.random.default_rng(1).random((100000, 4)); t0 = time.perf_counter(); g.predict(Z[:20000]); dt = (time.perf_counter() - t0) / 20000
        out[lab] = dict(n=len(y), rmse_gp=round(rmse(pg), 2), mae_gp=round(mae(pg), 2), rmse_linear=round(rmse(pl), 2), rmse_mean=round(rmse(pm), 2),
                        noise_floor_rmse=round(floor, 2), corr_gp=round(float(np.corrcoef(pg, y)[0, 1]), 3),
                        in_95=round(float(np.mean(np.abs(pg - y) <= 1.96 * sg)), 3), worst_pts=round(float(np.max(np.abs(pg - y)) * 100), 1),
                        length_scales=dict(zip(SW.KEYS, [round(float(s), 2) for s in g.ls])), sharp=sharp, surrogate_s_per_design=dt)
        o = out[lab]
        L += [f'## {lab}', '',
              '| predictor | error vs the simulator (RMS, pts) |', '|---|---|',
              f"| guess the average | {o['rmse_mean']} |", f"| straight-line fit | {o['rmse_linear']} |",
              f"| **Gaussian process** | **{o['rmse_gp']}** (typical {o['mae_gp']}, worst {o['worst_pts']}) |",
              f"| noise floor: the simulator's own 200-drop answer | {o['noise_floor_rmse']} |", '',
              f"Correlation with the simulator {o['corr_gp']}. Inside its own 95% error bars: {100 * o['in_95']:.0f}% of designs. "
              f"Length scales (0-1 range; short = it matters more): {o['length_scales']}.", '',
              'Against 1000-drop reruns (each predicted without its own design):', '',
              '| design (top/round/width/dz) | simulator, 1000 drops | surrogate | off by (pts) | simulator noise (pts) | rank by the surrogate, of 400 |', '|---|---|---|---|---|---|']
        L += [f"| {s['design']} | {s['sim_1000']:.3f} | {s['surrogate']:.3f} | {s['err_pts']:+.1f} | +-{s['sim_noise_pts']} | {s.get('surrogate_rank_of_400', '-')} |" for s in sharp] + ['']
    import posthoc_sweep_v2 as PS
    t0 = time.perf_counter(); PS.one((0, [200.0, 0.3, 150.0, 0.0], 20, 'cover', 0.2, 1.5, 1)); sim_drop = (time.perf_counter() - t0) / 20
    out['speed'] = dict(simulator_s_per_drop=round(sim_drop, 3), simulator_s_per_design_200=round(200 * sim_drop, 1), surrogate_s_per_design=out[lab]['surrogate_s_per_design'])
    L += [f"Speed, one core: the simulator takes {sim_drop:.2f} s per drop, so {200 * sim_drop:.0f} s for one design at 200 drops. "
          f"The surrogate answers one design in about {1e6 * out[lab]['surrogate_s_per_design']:.0f} microseconds: "
          f"about {200 * sim_drop / out[lab]['surrogate_s_per_design']:,.0f} times faster."]
    json.dump(out, open(os.path.join(ROOT, 'results', 'surrogate_gp.json'), 'w'), indent=1)
    open(os.path.join(ROOT, 'results', 'surrogate_gp.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
