"""Workstream D: a Gaussian-process surrogate for the tumble simulation, with its uncertainty used three ways.

    python research/tumble/surrogate.py     # needs research/results/tumble_truth.json (sweep.py)

1. Accuracy and calibration: fit on n simulated designs, predict held-out ones; RMSE, and how often the true value
   falls inside the 90% interval (0.90 wanted).
2. Active learning: add the design the surrogate is least sure of, against adding designs at random.
3. Uncertainty gating: for the decision "P(upright) >= threshold", the surrogate decides only when its 90% interval
   clears the threshold and sends the rest to full simulation. Reports decisions made, errors, simulations saved.
4. Mutants of the surrogate (its negative controls): a design far outside the training range must come back with a
   wide interval, and a physics change the surrogate can't see (friction) must be caught by a few sentinel
   simulations whose results fall outside the predicted intervals.

A small GP written here (numpy and scipy): an anisotropic RBF kernel on inputs scaled to [0, 1], a known per-point
noise from the binomial variance of each P estimate, a fitted extra noise term, and hyperparameters by maximising
the log marginal likelihood.
"""
import os, json
import numpy as np
from scipy.optimize import minimize
from scipy.linalg import cho_factor, cho_solve

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class GP:
    def __init__(self, lo, hi):
        self.lo, self.hi = np.asarray(lo, float), np.asarray(hi, float)

    def _x(self, X):
        return (np.asarray(X, float) - self.lo) / (self.hi - self.lo)

    def _k(self, A, B, th):
        ls, sf = np.exp(th[:-2]), np.exp(th[-2])
        d = (A[:, None, :] - B[None, :, :]) / ls
        return sf ** 2 * np.exp(-0.5 * (d ** 2).sum(-1))

    def fit(self, X, y, noise):
        self.X, self.mu = self._x(X), float(np.mean(y)); self.y = np.asarray(y, float) - self.mu
        self.noise = np.asarray(noise, float)
        D = self.X.shape[1]
        def nll(th):
            K = self._k(self.X, self.X, th) + np.diag(self.noise + np.exp(th[-1]) ** 2 + 1e-8)
            try:
                c = cho_factor(K, lower=True)
            except np.linalg.LinAlgError:
                return 1e10
            a = cho_solve(c, self.y)
            return 0.5 * self.y @ a + np.log(np.diag(c[0])).sum()
        best = None
        for s in range(4):                                              # a few restarts
            th0 = np.r_[np.log(np.full(D, 0.3 + 0.2 * s)), np.log(np.std(self.y) + 1e-3), np.log(0.02)]
            r = minimize(nll, th0, method='L-BFGS-B', bounds=[(-3, 2)] * D + [(-5, 1), (-7, -1)])
            if best is None or r.fun < best.fun:
                best = r
        self.th = best.x
        K = self._k(self.X, self.X, self.th) + np.diag(self.noise + np.exp(self.th[-1]) ** 2 + 1e-8)
        self.c = cho_factor(K, lower=True); self.a = cho_solve(self.c, self.y)
        return self

    def predict(self, X):
        Xs = self._x(X); Ks = self._k(Xs, self.X, self.th)
        m = Ks @ self.a + self.mu
        v = np.exp(self.th[-2]) ** 2 - np.einsum('ij,ji->i', Ks, cho_solve(self.c, Ks.T))
        return m, np.sqrt(np.maximum(v, 1e-10))


def binom_noise(p, n):
    p = np.clip(p, 0.02, 0.98)
    return p * (1 - p) / n


def evaluate(truth, keys, lo, hi, n_train, rng):
    X = np.array([[t['params'][k] for k in keys] for t in truth]); y = np.array([t['p_upright'] for t in truth])
    nn = np.array([t['n'] for t in truth])
    idx = rng.permutation(len(X)); tr, te = idx[:n_train], idx[n_train:]
    g = GP(lo, hi).fit(X[tr], y[tr], binom_noise(y[tr], nn[tr]))
    m, s = g.predict(X[te])
    tot = np.sqrt(s ** 2 + binom_noise(y[te], nn[te]))                  # the truth is itself an estimate
    inside = np.abs(y[te] - m) <= 1.645 * tot
    return dict(rmse=float(np.sqrt(np.mean((m - y[te]) ** 2))), coverage90=float(inside.mean()), n_test=int(len(te))), g, (X, y, nn)


def active(truth, keys, lo, hi, start, budget, rng, mode):
    X = np.array([[t['params'][k] for k in keys] for t in truth]); y = np.array([t['p_upright'] for t in truth])
    nn = np.array([t['n'] for t in truth])
    idx = rng.permutation(len(X)); pool, test = list(idx[:int(0.75 * len(X))]), idx[int(0.75 * len(X)):]
    chosen = pool[:start]; pool = pool[start:]; curve = []
    while len(chosen) <= budget:
        g = GP(lo, hi).fit(X[chosen], y[chosen], binom_noise(y[chosen], nn[chosen]))
        m, _ = g.predict(X[test]); curve.append((len(chosen), float(np.sqrt(np.mean((m - y[test]) ** 2)))))
        if not pool or len(chosen) == budget:
            break
        if mode == 'uncertainty':
            _, s = g.predict(X[pool]); j = int(np.argmax(s))
        else:
            j = int(rng.integers(len(pool)))
        chosen.append(pool.pop(j))
    return curve


def gate(g, X, y, nn, thr):
    m, s = g.predict(X)
    lo, hi = m - 1.645 * s, m + 1.645 * s
    decided = (lo >= thr) | (hi < thr)
    truth = y >= thr
    wrong = decided & ((m >= thr) != truth)
    return dict(threshold=thr, designs=int(len(X)), decided_by_surrogate=int(decided.sum()), wrong=int(wrong.sum()),
                sent_to_simulation=int((~decided).sum()))


if __name__ == '__main__':
    T = json.load(open(os.path.join(ROOT, 'results', 'tumble_truth.json')))
    keys, lo, hi, truth = T['keys'], T['lo'], T['hi'], T['designs']
    rng = np.random.default_rng(1)
    R = {'n_designs': len(truth), 'keys': keys}
    R['accuracy'] = [dict(n_train=n, **evaluate(truth, keys, lo, hi, n, np.random.default_rng(10 + n))[0]) for n in (20, 40, 80, 160)]
    ev, g, (X, y, nn) = evaluate(truth, keys, lo, hi, 120, np.random.default_rng(7))
    R['curves'] = {mode: [active(truth, keys, lo, hi, 15, 90, np.random.default_rng(s), mode) for s in range(5)]
                   for mode in ('uncertainty', 'random')}
    test = np.arange(len(X))
    R['gating'] = [gate(g, X, y, nn, thr) for thr in (0.5, 0.6, 0.7)]
    json.dump(R, open(os.path.join(ROOT, 'results', 'surrogate_summary.json'), 'w'), indent=1)
    print(json.dumps({k: R[k] for k in ('accuracy', 'gating')}, indent=1))
