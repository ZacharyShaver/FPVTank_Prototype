"""The shape study's picture sheet: each body-shape knob's outline at the bottom and top of its range (side view, T5's
wheels and tail mount drawn in), and the screened upright, climb and turn as the knob moves with the rest at T5's.

    SCORPION_SEARCH=search_shape python gauges/shape_sheet.py   -> gauges/out/search_shape/shape_sheet.png
"""
import os, sys, json
os.environ.setdefault('SCORPION_SEARCH', 'search_shape')
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import search as S

INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
LOW, HIGH, LINE = '#86b6ef', '#1c5cab', '#2a78d6'                          # one hue: the knob's low end light, high end dark
NAMES = dict(xc='centre, back to front', af='reach forward', ar='reach back', b='half-width', zc='widest section height',
             cu='top above it', cd='bottom below it', p='plan: ellipse to box', qu='top: cone to boxy', qd='bottom: cone to boxy')


def side(z):
    """the skin's side outline (x, z) and the spec"""
    sp = S.build(S.to_x(z)); P = sp['hulls'][0][:, [0, 2]]; h = ConvexHull(P)
    return np.vstack([P[h.vertices], P[h.vertices[:1]]]), sp


def main():
    R = json.load(open(os.path.join(S.OUT, 'shape_sweep.json')))
    res, t5 = R['results'], R['results']['T5'][0]
    base = np.array([S.T5_SHAPE[k] for k in S.ZK]); ks = S.ZK
    fig, ax = plt.subplots(4, len(ks), figsize=(2.15 * len(ks), 8.6), gridspec_kw=dict(height_ratios=[1.25, 1, 1, 1]))
    plt.rcParams.update({'font.size': 8})
    for j, k in enumerate(ks):
        a = ax[0, j]
        for v, c, lw in ((S.ZLO[j], LOW, 1.6), (S.ZHI[j], HIGH, 1.6)):
            z = base.copy(); z[j] = v; out, sp = side(z); a.plot(out[:, 0], out[:, 1], color=c, lw=lw)
        for x_, _ in sp['wheels']:
            a.add_patch(plt.Circle((x_, sp['R']), sp['R'], fill=False, color=INK2, lw=0.8))
        B = sp['limb']['base']; a.plot([B[0]], [B[2]], 'o', ms=4, color=INK2)
        a.set_aspect('equal'); a.axis('off'); a.set_xlim(-330, 330); a.set_ylim(-10, 480)
        a.set_title(f'{k}: {NAMES[k]}\n{S.ZLO[j]:g} (light) to {S.ZHI[j]:g} (dark)', fontsize=7.5, color=INK)
        rows = res[k]; v = [r['v'] for r in rows]
        for i, (g, lab) in enumerate((('up', 'upright'), ('climb', 'step up, mm'), ('turn', 'turn, mm')), start=1):
            a = ax[i, j]; y = [r[g] for r in rows]
            a.plot(v, y, color=LINE, lw=2, marker='o', ms=4)
            a.axvline(S.T5_SHAPE[k], color=INK2, lw=0.8, ls=(0, (3, 3)))
            a.axhline(t5[g], color=GRID, lw=1, zorder=0)
            a.grid(axis='y', color=GRID, lw=0.6); a.tick_params(colors=INK2, labelsize=7)
            for s_ in ('top', 'right'):
                a.spines[s_].set_visible(False)
            for s_ in ('left', 'bottom'):
                a.spines[s_].set_color(GRID)
            a.set_ylim(*{'up': (0.5, 1.02), 'climb': (0, 160), 'turn': (300, 700)}[g])
            if j == 0:
                a.set_ylabel(lab, color=INK)
    fig.suptitle('Body shape on T5\'s locked platform: each knob alone, the rest at T5\'s shape (dashed: T5\'s value; '
                 'grey line: T5\'s reading). Screen readings, 3 seeds each.', fontsize=10, color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    path = os.path.join(S.OUT, 'shape_sheet.png'); fig.savefig(path, dpi=130, facecolor='#fcfcfb'); print(path)


if __name__ == '__main__':
    main()
