"""Importance weights for the gauges (2026-11-02). Zach: "we need to implement a system of weights for every test";
asked, he meant how much each test counts in the overall score. Edit WEIGHTS; nothing else reads a weight.

The all-rounder score stays a worst case, now weighted: each gauge's shortfall from the top (1 - its percentile rank
among the designs) is scaled by its weight over the largest weight, and the score is 1 minus the largest scaled
shortfall. Equal weights give the worst rank, the score every run before this one used, so the runs so far re-rank
exactly as they ran. A weight of 2 against 1 makes that gauge's shortfall count double; 0 drops the gauge from the
score, the seven-way front and the search's streams. A weighted average was the other way: there one great gauge buys
off a terrible one (a 300 mm climber that needs a metre to turn round), which the worst case doesn't allow.

A task's weights (2026-11-02). Zach: "it gives us a way to tell the simulator what you want as a result ... you can
score a weight vector for how well it goes say around a obstacle course. multiple factors and their interplay needs a
descriptor". fit() finds the weights whose all-rounder ranks a set of designs as a bigger test (course.py's obstacle
course) does, by Spearman's rho: that vector is the test's descriptor, and a search weighted by it chases the test
without running it. cv() reads how well a vector predicts designs it wasn't fitted on.

    python gauges/weights.py check   -> its controls (exits 1 on a failure)
"""
import sys
import numpy as np

WEIGHTS = dict(up=1.0,       # G1 upright after a fall
               climb=1.0,    # G2 step up
               turn=1.0,     # G3 turn-around space
               h_up=1.0,     # G4 hill up
               h_down=1.0,   # G5 hill down
               crest=1.0,    # G6 crest
               push=1.0,     # G7 push (the runs before the tow run)
               tow=1.0,      # G7 tow (tow.py)
               rough=1.0)    # G8 rough ground (rough.py)


def counted(gauges, w=None):
    """the gauges that count (weight above 0), in order"""
    w = WEIGHTS if w is None else w
    return [g for g in gauges if w.get(g, 1.0) > 0]


def allround(rank, gauges, w=None):
    """the weighted worst rank of a design's per-gauge ranks (0 worst, 1 best): 1 - max(w_g / w_max x (1 - rank_g))"""
    w = WEIGHTS if w is None else w; gs = counted(gauges, w); top = max(w.get(g, 1.0) for g in gs)
    if all(w.get(g, 1.0) == top for g in gs):                            # equal: the worst rank to the bit, as the runs before
        return min(rank[g] for g in gs)
    return 1.0 - max(w.get(g, 1.0) / top * (1.0 - rank[g]) for g in gs)


def allround_arr(M, w):
    """allround for many designs at once: M (designs x gauges) ranks, w the gauges' weights"""
    w = np.asarray(w, float)
    return 1.0 - (w / w.max() * (1.0 - M)).max(1)


def rho(a, b):
    """Spearman's rank correlation (0 when either is constant)"""
    from scipy.stats import spearmanr
    r = spearmanr(a, b)[0]
    return 0.0 if not np.isfinite(r) else float(r)


GRID = (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.25, 1.5, 2.0, 3.0)


def fit(M, y, kind='worst', n=3000, seed=0):
    """the weights (largest 1) whose all-rounder ranks the designs most as y does. kind 'worst': allround (the weighted
    worst rank); 'sum': a weighted mean of the ranks, for comparison (one gauge can buy off another); 'one': the single
    gauge that ranks them best. Random vectors (a third of their entries 0), then coordinate sweeps over GRID"""
    G = M.shape[1]; f = (lambda w: allround_arr(M, w)) if kind == 'worst' else (lambda w: M @ w)
    if kind == 'one':
        return np.eye(G)[int(np.argmax([rho(M[:, j], y) for j in range(G)]))]
    g = np.random.default_rng(seed); cand = g.uniform(0, 1, (n, G)) * (g.random((n, G)) > 0.33)
    cand = np.vstack([np.ones(G), np.eye(G), cand[cand.max(1) > 0]])
    sc = [rho(f(w), y) for w in cand]; w = cand[int(np.argmax(sc))].copy(); best = max(sc)
    for _ in range(3):
        for j in range(G):
            for v in GRID:
                u = w.copy(); u[j] = v
                if u.max() > 0:
                    r = rho(f(u), y)
                    if r > best + 1e-9:
                        best, w = r, u
        w = w / w.max()
    return w


def cv(M, y, k=5, fixed=None, kind='worst', seed=0):
    """the mean held-out rho over k folds: fitted on the rest (or fixed weights), read on the fold"""
    idx = np.random.default_rng(seed).permutation(len(y)); out = []
    for f in np.array_split(idx, k):
        tr = np.setdiff1d(idx, f); w = fixed if fixed is not None else fit(M[tr], y[tr], kind)
        out.append(rho(allround_arr(M[f], w) if kind == 'worst' else M[f] @ w, y[f]))
    return round(float(np.mean(out)), 3)


def check():
    """equal weights give the worst rank; a gauge weighted 0 stops counting (its rank moves nothing); weighting the
    climb down lets the poor climber win, and its control, weighting it up, doesn't"""
    bad = 0; gs = ['up', 'climb', 'turn']
    a = dict(up=0.9, climb=0.2, turn=0.8); b = dict(up=0.5, climb=0.6, turn=0.5)   # a: a poor climber; b: even
    ok = allround(a, gs) == min(a.values()) and allround(b, gs) == min(b.values()); bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'equal weights: the worst rank ({allround(a, gs):.2f}, {allround(b, gs):.2f})')
    w0 = dict(WEIGHTS, climb=0.0); ok = allround(a, gs, w0) == allround(dict(a, climb=0.0), gs, w0) == 0.8; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'climb at 0: a scores {allround(a, gs, w0):.2f} whatever its climb')
    pick = lambda w: max((('a', a), ('b', b)), key=lambda t: allround(t[1], gs, w))[0]
    up, down = dict(WEIGHTS, climb=0.25), dict(WEIGHTS, climb=4.0)
    ok = pick(WEIGHTS) == 'b' and pick(up) == 'a' and pick(down) == 'b'; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'the pick: {pick(WEIGHTS)} at equal weights, {pick(up)} with climb at 0.25 (a is the poor climber), '
          f'{pick(down)} with climb at 4')
    g = np.random.default_rng(1); M = g.uniform(0, 1, (300, 8)); wt = np.array([0, 1, 0.5, 0, 0, 0.3, 0, 0.8])
    y = allround_arr(M, wt) + g.normal(0, 0.03, 300); wf = fit(M, y); c = cv(M, y)
    ok = int(np.argmax(wf)) == 1 and wf[wt == 0].max() < 0.25 and c >= 0.85; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'fit, a known answer: a test scored by {wt.tolist()} (plus noise) fits {wf.round(2).tolist()}, '
          f'held-out rho {c:.2f}')
    c0 = cv(M, g.permutation(y)); ok = abs(c0) < 0.15; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'control: the same scores shuffled across designs: held-out rho {c0:.2f}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    if 'check' in sys.argv[1:]:
        check()
    else:
        print(__doc__)
