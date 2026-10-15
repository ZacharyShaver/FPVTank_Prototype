"""EXPLORATORY (2026-10-15): pictures of the shape-sweep surrogate (surrogate_gp.py), cover + bounce variant.

    python research/tumble/surrogate_plot.py -> research/figures/surrogate_gp.png

Top row: P(upright) as one setting varies and the other three stay at the sweep's best design, with the
surrogate's 95% band. Bottom: maps over top height and width (round and dz at the best design's): the prediction,
and the surrogate's uncertainty, with all 400 training shapes marked (at any round and dz, so only a rough guide).
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import sweep as SW
from surrogate_gp import GP, scale, LO, HI

VARIANT = 'cover, bounce'
BLUE, BAND, INK, MUTED, GRID, AXIS, SURF = '#2a78d6', '#cde2fb', '#0b0b0b', '#52514e', '#e1e0d9', '#c3c2b7', '#fcfcfb'
BLUES = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
ORANGES = ['#fde5d9', '#f8bea3', '#f2946d', '#eb6834', '#c44f1f', '#963a15', '#6b280d']
LABEL = {'top': 'top height (mm)', 'round': 'edge rounding (0 boxy, 1 dome)', 'width': 'width (mm)', 'dz': 'weight position (mm, + is higher)'}

if __name__ == '__main__':
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': AXIS, 'axes.labelcolor': MUTED, 'xtick.color': MUTED, 'ytick.color': MUTED,
                         'axes.facecolor': SURF, 'figure.facecolor': SURF, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
                         'axes.spines.top': False, 'axes.spines.right': False})
    v = json.load(open(os.path.join(ROOT, 'results', 'posthoc_sweep_v2.json')))['results'][VARIANT]
    X = scale([r['params'] for r in v['all']]); y = np.array([r['p_upright'] for r in v['all']])
    g = GP().fit(X, y)
    best = v['top_confirmed'][0]; xb = scale([best['params']])[0]

    fig = plt.figure(figsize=(14, 9.2))
    gs = fig.add_gridspec(1, 4, left=0.05, right=0.98, top=0.90, bottom=0.60, wspace=0.28)
    gb = fig.add_gridspec(1, 2, left=0.05, right=0.98, top=0.47, bottom=0.06, wspace=0.22)
    for j, k in enumerate(SW.KEYS):
        a = fig.add_subplot(gs[0, j]); u = np.linspace(0, 1, 200); Z = np.tile(xb, (200, 1)); Z[:, j] = u
        m, s = g.predict(Z); s = np.sqrt(np.maximum(s ** 2 - g.sn2, 0))       # the band for the simulator's true value
        xs = LO[j] + u * (HI[j] - LO[j])
        a.fill_between(xs, 100 * (m - 1.96 * s), 100 * (m + 1.96 * s), color=BAND, lw=0)
        a.plot(xs, 100 * m, color=BLUE, lw=2)
        a.axvline(best['params'][k], color=MUTED, lw=1, ls=(0, (3, 3)))
        a.set_xlabel(LABEL[k]); a.set_ylim(0, 100)
        if j == 0: a.set_ylabel('chance of landing upright (%)')
        a.set_title(f"vary {k} only", color=INK, fontsize=10, loc='left')
    fig.text(0.5, 0.955, f"The surrogate around the best design ({best['params']['top']:.0f}/{best['params']['round']:.2f}/"
             f"{best['params']['width']:.0f}/{best['params']['dz']:.0f}, dashed): line = its prediction, band = 95% sure the simulator's answer is inside",
             ha='center', color=INK, fontsize=11)

    fig.text(0.05, 0.515, 'Maps over height and width, with edge rounding and weight position held at the best design', color=INK, fontsize=11)
    nt, nw = 120, 120; T, Wd = np.meshgrid(np.linspace(0, 1, nt), np.linspace(0, 1, nw))
    Z = np.tile(xb, (nt * nw, 1)); Z[:, 0] = T.ravel(); Z[:, 2] = Wd.ravel()
    m, s = g.predict(Z); s = np.sqrt(np.maximum(s ** 2 - g.sn2, 0))
    ext = [LO[0], HI[0], LO[2], HI[2]]; P = np.array([[r['params']['top'], r['params']['width']] for r in v['all']])
    for col, (vals, cmap, title, unit) in enumerate(((100 * m, BLUES, 'Prediction: chance of landing upright', '%'),
                                                    (100 * 1.96 * s, ORANGES, 'Uncertainty: +- points, 95%', 'pts'))):
        a = fig.add_subplot(gb[0, col]); a.grid(False)
        im = a.imshow(vals.reshape(nw, nt), origin='lower', extent=ext, aspect='auto', cmap=LinearSegmentedColormap.from_list('r', cmap))
        cb = fig.colorbar(im, ax=a, fraction=0.04, pad=0.02); cb.set_label(unit, color=MUTED); cb.outline.set_visible(False)
        if col == 1:
            a.scatter(P[:, 0], P[:, 1], s=8, c='white', edgecolors=INK, linewidths=0.4, label='the 400 simulated shapes (any rounding, weight)')
            a.legend(loc='upper left', frameon=True, fontsize=8, facecolor=SURF, edgecolor=GRID)
        a.scatter([best['params']['top']], [best['params']['width']], s=70, marker='*', c='white', edgecolors=INK, linewidths=0.8, zorder=3)
        a.annotate('best design', (best['params']['top'], best['params']['width']), xytext=(-70, -18), textcoords='offset points', color=INK, fontsize=8,
                   arrowprops=dict(arrowstyle='-', color=INK, lw=0.6))
        a.set_xlabel(LABEL['top']); a.set_ylabel(LABEL['width']); a.set_title(title, color=INK, fontsize=10, loc='left')
    fig.savefig(os.path.join(ROOT, 'figures', 'surrogate_gp.png'), dpi=110, bbox_inches='tight')
    print('wrote figures/surrogate_gp.png')
