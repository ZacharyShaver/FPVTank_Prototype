"""Can a Gaussian process stand in for the gauges' screen? (2026-10-27, exploratory; Zach asked about "generating the
Gaussian surrogate". The paper's tumble surrogate, research/tumble/surrogate_gp.py, did it for one gauge over 4 knobs.)

    python gauges/surrogate.py   -> gauges/out/surrogate/surrogate.json

It trains on what the searches already screened (no new sims): the hills run (5 knobs, both hills and G1-G3), the
shape study (10 skin knobs) and the body search (24 knobs). A Matern 5/2 kernel with one length scale per knob and a
noise term, fitted by marginal likelihood (scikit-learn). The knobs are scaled 0-1 over the screened range. Designs
the screen cut (G1 under its bar) are left out: they have no climb or hills.

Checks, each against a baseline (the training mean, a straight-line fit):
  1. 5-fold cross-validation: each design predicted by a surrogate that never saw it. RMSE and R2.
  2. Where a search goes: trained on the Sobol spread (B) alone, predicting the refinements' designs (C), which sit
     near the best. Rank correlation, and whether the surrogate's top fifth holds the true top tenth.
  3. Its error bars: the share of held-out designs inside its 95% interval should be about 95%.
  The noise floor is the screen's own: its fitted noise term, beside the seed noise measured on T3 (knobs.py).
Sensitivity: each knob's first-order share of the gauge's variance over the screened range (the surrogate's mean
averaged over the other knobs), and its length scale (short: the gauge turns fast with it).
"""
import os, sys, json, time, warnings
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '4')
import numpy as np
from scipy.stats import spearmanr
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold
from sklearn.exceptions import ConvergenceWarning
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
warnings.filterwarnings('ignore', category=ConvergenceWarning)

OUT = os.path.join(config.GAUGES_OUT, 'surrogate')
SETS = {   # run: (its knobs in z order, the gauges to model)
    'search_hills': (['R', 'xw', 'gap', 'dxp', 'dzp'], ['up', 'climb', 'turn', 'h_up', 'h_down']),
    'search_shape': (['xc', 'af', 'ar', 'b', 'zc', 'cu', 'cd', 'p', 'qu', 'qd'], ['up', 'climb', 'turn']),
    'search_body': (['R', 'xw', 'gap', 'clr', 'dxp', 'shell', 'zc', 'cu', 'limb', 'L', 'tq', 'th_push', 'th_stow', 'mz', 'track', 'gear',
                     'xc', 'af', 'ar', 'b', 'cd', 'p', 'qu', 'qd'], ['up', 'climb', 'turn']),
}
N_MAX = 1200                               # training designs at most (the fit is n^3)


def load(run):
    R = []
    for t in ('B', 'S', 'C', 'K'):
        f = os.path.join(config.GAUGES_OUT, run, f'screen_{t}.jsonl')
        if os.path.exists(f):
            R += [dict(json.loads(l), src=t) for l in open(f)]
    return [r for r in R if not r.get('cut') and r.get('turn') is not None and r.get('climb') is not None]


def gp(d):
    k = ConstantKernel(1.0, (1e-3, 1e3)) * Matern(np.full(d, 0.3), (1e-2, 1e2), nu=2.5) + WhiteKernel(0.1, (1e-5, 1e1))
    return GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=1, random_state=0)


def stats(y, m, s=None):
    e = m - y; out = dict(rmse=float(np.sqrt((e ** 2).mean())), r2=float(1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum()))
    if s is not None:
        out['cover95'] = float((np.abs(e) <= 1.96 * s).mean())
    return out


def first_order(model, d, n=400, m=9, seed=0):
    """each knob's first-order variance share: Var over the knob of the mean over the others, over the total"""
    rng = np.random.default_rng(seed); X = rng.uniform(0, 1, (n, d)); tot = model.predict(X).var(); sh = []
    for j in range(d):
        cur = []
        for v in np.linspace(0, 1, m):
            Xj = X.copy(); Xj[:, j] = v; cur.append(model.predict(Xj).mean())
        sh.append(float(np.var(cur) / tot) if tot > 0 else 0.0)
    return sh


def main():
    os.makedirs(OUT, exist_ok=True); res = {}; t0 = time.time()
    for run, (keys, gauges) in SETS.items():
        rows = load(run); Z = np.array([r['z'] for r in rows], float); lo, hi = Z.min(0), Z.max(0)
        X = (Z - lo) / np.where(hi > lo, hi - lo, 1.0); src = np.array([r['src'] for r in rows]); rng = np.random.default_rng(1)
        res[run] = dict(n=len(rows), knobs=keys, by_src={s: int((src == s).sum()) for s in set(src)}, gauges={})
        print(f'{run}: {len(rows)} screened designs, {X.shape[1]} knobs, {res[run]["by_src"]}', flush=True)
        for g in gauges:
            y = np.array([r[g] for r in rows], float); ok = np.isfinite(y); Xg, yg, sg = X[ok], y[ok], src[ok]
            idx = rng.permutation(len(yg))[:N_MAX * 5 // 4]; Xc, yc = Xg[idx], yg[idx]
            cv = dict(gp=[], lin=[], mean=[]); pm, ps, pl, py = [], [], [], []
            for tr, te in KFold(5, shuffle=True, random_state=0).split(Xc):
                mdl = gp(Xc.shape[1]).fit(Xc[tr], yc[tr]); m, s = mdl.predict(Xc[te], return_std=True)
                pm.append(m); ps.append(s); py.append(yc[te]); pl.append(LinearRegression().fit(Xc[tr], yc[tr]).predict(Xc[te]))
            py, pm, ps, pl = map(np.concatenate, (py, pm, ps, pl))
            cvr = dict(gp=stats(py, pm, ps), linear=stats(py, pl), mean=stats(py, np.full_like(py, py.mean())), sd=float(yc.std()))
            # where a search goes: train on the spread (B and S), predict the refinements (C, K)
            trn, tst = np.isin(sg, ('B', 'S')), np.isin(sg, ('C', 'K'))
            fwd = None
            if tst.sum() > 20:
                tri = np.where(trn)[0]; tri = tri[rng.permutation(len(tri))[:N_MAX]]
                mdl = gp(Xg.shape[1]).fit(Xg[tri], yg[tri]); m, s = mdl.predict(Xg[tst], return_std=True); yt = yg[tst]
                sign = -1.0 if g == 'turn' else 1.0                              # turn: smaller is better
                top_true = sign * yt >= np.quantile(sign * yt, 0.9); top_pred = sign * m >= np.quantile(sign * m, 0.8)
                fwd = dict(n=int(tst.sum()), **stats(yt, m, s), rho=float(spearmanr(yt, m).correlation),
                           top10_in_pred_top20=float((top_true & top_pred).sum() / max(top_true.sum(), 1)))
            full = gp(Xc.shape[1]).fit(Xc[:N_MAX], yc[:N_MAX]); kp = full.kernel_.get_params()
            ls = np.atleast_1d(kp['k1__k2__length_scale']).tolist(); noise_sd = float(np.sqrt(kp['k2__noise_level']) * full._y_train_std)
            fo = first_order(full, Xc.shape[1])
            res[run]['gauges'][g] = dict(cv=cvr, forward=fwd, noise_sd=noise_sd, length_scale=dict(zip(keys, ls)), first_order=dict(zip(keys, fo)))
            top = sorted(zip(keys, fo), key=lambda t: -t[1])[:4]
            print(f"  {g:7s} sd {cvr['sd']:.3g}  CV rmse gp {cvr['gp']['rmse']:.3g} (R2 {cvr['gp']['r2']:.2f}, 95% cover {cvr['gp']['cover95']:.2f}), "
                  f"linear {cvr['linear']['rmse']:.3g}, mean {cvr['mean']['rmse']:.3g}; noise term sd {noise_sd:.3g}"
                  + (f"; B->C rmse {fwd['rmse']:.3g} rho {fwd['rho']:.2f} top10 caught {fwd['top10_in_pred_top20']:.2f}" if fwd else '')
                  + f"; first-order {[(k, round(v, 2)) for k, v in top]}  ({time.time() - t0:.0f} s)", flush=True)
            json.dump(res, open(os.path.join(OUT, 'surrogate.json'), 'w'), indent=1)
    print(f'{time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
