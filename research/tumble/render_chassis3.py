"""The chassis search's finalists against the Trainer: side views at one scale, where each lands off a step (height x
speed, forwards and in reverse) and how high a step each climbs.

    python research/tumble/render_chassis3.py  -> research/figures/chassis3_finalists.png
"""
import os, sys, json
import numpy as np
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import chassis3 as C3

FR = json.load(open(os.path.join(ROOT, 'results', 'chassis3', 'frontier.json')))['results']
F = [dict(FR['baseline'], name='baseline (Trainer)')] + [dict(FR[k], name=f'best under {float(k):.0f} mm long') for k in FR if k != 'baseline']
HS, VS = (100, 200, 300, 400), (0.3, 0.6, 1.0, 1.4)


def side(ax, p, color):
    d = C3.design(p); P = d['pts'][:, [0, 2]]; h = ConvexHull(P); v = P[h.vertices]
    ax.fill(*v.T, color=color, alpha=0.25, lw=0); ax.plot(*np.vstack([v, v[:1]]).T, color=color, lw=1.5)
    a = np.linspace(0, 2 * np.pi, 60)
    for x in (p['xf'], p['xr']):
        ax.fill(x + p['R'] * np.cos(a), p['R'] + p['R'] * np.sin(a), color='#2f3439')
    G = sum(m * q for _, m, q in d['items']) / sum(m for _, m, _ in d['items'])
    ax.plot(G[0], G[2], marker='o', ms=7, color='#c8743a', mec='white'); ax.axhline(0, color='#777', lw=1)
    ax.set_aspect('equal'); ax.set_xlim(-260, 260); ax.set_ylim(-10, 215); ax.axis('off')


if __name__ == '__main__':
    fig = plt.figure(figsize=(15, 3.3 * len(F))); gs = fig.add_gridspec(len(F), 4, width_ratios=[1.35, 1, 1, 0.9], wspace=0.25, hspace=0.75)
    for i, f in enumerate(F):
        base = f['name'] == 'baseline (Trainer)'; col = '#8d959c' if base else '#13824f'; p = f['p']
        ax = fig.add_subplot(gs[i, 0]); side(ax, p, col)
        cl = f['climb']
        txt = '\n'.join([f['name'], f"down a step {f['down']:.0%}, up a step {f['up']:.0%}",
                         f"{f['design']['length']:.0f} mm long, {f['design']['mass'] / 1000:.2f} kg",
                         f"wheels Ø{2 * p['R']:.0f}, axles {p['xr']:.0f} / {p['xf']:.0f}",
                         f"belly {p['clr']:.0f} mm, packs {p['dxp']:+.0f} fwd {p['dzp']:+.0f} up"] + list(f['design']['notes']))
        ax.text(0.0, 1.0, txt, transform=ax.transAxes, fontsize=9, va='bottom', ha='left', color='#1c2124')
        for k, back in enumerate((False, True)):
            ax = fig.add_subplot(gs[i, 1 + k]); A = np.zeros((len(HS), len(VS))); S_ = np.zeros_like(A)
            for a, h in enumerate(HS):
                for b, v in enumerate(VS):
                    c = f['cells'][f'{h}|{v}|{int(back)}']; n = sum(c.values()); A[a, b] = c.get('upright', 0) / n; S_[a, b] = c.get('stuck', 0) / n
            ax.imshow(A, origin='lower', cmap='RdYlGn', vmin=0, vmax=1, aspect='auto')
            for a in range(len(HS)):
                for b in range(len(VS)):
                    ax.text(b, a, f'{A[a, b]:.0%}' + (f'\n{S_[a, b]:.0%} stuck' if S_[a, b] > 0.01 else ''), ha='center', va='center', fontsize=8)
            ax.set_xticks(range(len(VS))); ax.set_xticklabels(VS, fontsize=8); ax.set_yticks(range(len(HS))); ax.set_yticklabels(HS, fontsize=8)
            ax.set_title('forwards' if not back else 'in reverse', fontsize=9.5)
            if i == len(F) - 1: ax.set_xlabel('speed at the edge (m/s)', fontsize=9)
            if k == 0: ax.set_ylabel('step down (mm)', fontsize=9)
        ax = fig.add_subplot(gs[i, 3]); hs = (40, 60, 80, 100, 120)
        for back, c_ in ((False, '#2765c2'), (True, '#13824f')):
            ax.plot(hs, [cl[f'{h}|{int(back)}'].get('climbed', 0) / sum(cl[f'{h}|{int(back)}'].values()) for h in hs], marker='o', color=c_, label='in reverse' if back else 'forwards')
        ax.set_ylim(-0.05, 1.05); ax.set_xticks(hs); ax.set_title('climbs a step up (0.5 m/s)', fontsize=9.5); ax.tick_params(labelsize=8)
        if i == 0: ax.legend(fontsize=8, frameon=False)
        if i == len(F) - 1: ax.set_xlabel('step up (mm)', fontsize=9)
    fig.suptitle('Chassis search for steps: the Trainer against the best layouts (simulated; orange dot = centre of mass)', fontsize=13, y=0.995)
    out = os.path.join(ROOT, 'figures', 'chassis3_finalists.png'); fig.savefig(out, dpi=100, bbox_inches='tight', facecolor='white'); print(out)
