"""The hills run's picture sheet: the five unlocked knobs one at a time (the rest at T3's), each on the hills, the
step and the turn, T3's setting marked; and the finalists' side views.

    python gauges/hills_run_sheet.py   -> gauges/out/search_hills/hills_run_sheet.png (after hills.py sweep and finals)
"""
import os, sys, json, pickle
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config

OUT = os.path.join(config.GAUGES_OUT, 'search_hills')
INK, INK2, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
UP, DOWN = '#2a78d6', '#eb6834'                                          # validated pair (dataviz validator, light)
KNOB = dict(R='wheel radius', xw='wheelbase centre, ahead', gap='gap between the tyres', dxp='packs moved forward', dzp='packs moved up')


def style(a, grid='y'):
    a.grid(axis=grid, color=GRID, lw=0.6); a.tick_params(colors=INK2, labelsize=7.5)
    for s in ('top', 'right'):
        a.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        a.spines[s].set_color(GRID)


def main():
    sw = json.load(open(os.path.join(OUT, 'hills_sweep.json'))); res = sw['results']; t3 = sw['t3']
    fin_p = os.path.join(OUT, 'finals.json'); fin = json.load(open(fin_p))['finals'] if os.path.isfile(fin_p) else None
    ks = [k for k in KNOB if k in res]
    fig = plt.figure(figsize=(15, 13.5 if fin else 10)); gs = fig.add_gridspec(5 if fin else 4, len(ks), height_ratios=[1.25, 0.8, 0.8, 0.55] + ([1.6] if fin else []))
    tmax = max(r['turn'] for k in ks for r in res[k])
    for j, k in enumerate(ks):
        rs = res[k]; v = [r['v'] for r in rs]
        a = fig.add_subplot(gs[0, j]); style(a)
        a.plot(v, [r['tip_static'] for r in rs], color=INK2, lw=1, ls=(0, (2, 2)), label='static tip angle')
        a.plot(v, [r['h_up'] for r in rs], color=UP, lw=2, marker='o', ms=5, mec=SURF, mew=1.2, label='drives up')
        a.plot(v, [r['h_down'] for r in rs], color=DOWN, lw=2, marker='o', ms=5, mec=SURF, mew=1.2, label='drives down')
        a.axvline(t3[k], color=INK2, lw=0.8); a.set_ylim(15, 62)
        a.set_title(f'{k}: {KNOB[k]}', color=INK, fontsize=9, loc='left')
        if j == 0:
            a.set_ylabel('steepest slope, x2.5 (deg)', color=INK2, fontsize=8); a.legend(fontsize=7, frameon=False, loc='upper left')
        b = fig.add_subplot(gs[1, j]); style(b); b.plot(v, [r['climb'] for r in rs], color=INK, lw=1.6, marker='o', ms=4, mec=SURF)
        b.axvline(t3[k], color=INK2, lw=0.8); b.set_ylim(0, 160)
        if j == 0:
            b.set_ylabel('step up (mm)', color=INK2, fontsize=8)
        c = fig.add_subplot(gs[2, j]); style(c); c.plot(v, [r['turn'] for r in rs], color=INK, lw=1.6, marker='o', ms=4, mec=SURF)
        c.axvline(t3[k], color=INK2, lw=0.8); c.set_ylim(300, tmax + 20)
        if j == 0:
            c.set_ylabel('turn space (mm)', color=INK2, fontsize=8)
        e = fig.add_subplot(gs[3, j]); style(e); e.plot(v, [r['up'] for r in rs], color=INK, lw=1.6, marker='o', ms=4, mec=SURF)
        e.axhline(0.75, color=INK2, lw=0.8, ls=(0, (3, 3))); e.axvline(t3[k], color=INK2, lw=0.8); e.set_ylim(0, 1.08)
        e.set_xlabel(f'{k} (mm); the line: T3', color=INK2, fontsize=8)
        if j == 0:
            e.set_ylabel('upright (screen)', color=INK2, fontsize=8); e.text(v[0], 0.62, 'target 0.75', color=INK2, fontsize=7)
    if fin:
        sys.path.insert(0, HERE); os.environ['SCORPION_SEARCH'] = 'search_hills'
        import search as S
        F = [f for f in fin if not f['control'] and f['name'] != 'Box']
        a = fig.add_subplot(gs[4, :]); a.set_aspect('equal'); a.axis('off'); x0 = 0.0
        for f in F:
            sp = S.build(np.array(f['x']), name=f['name']); H = np.vstack(sp['hulls']); G = S.com_all(sp)
            from scipy.spatial import ConvexHull
            P = H[:, [0, 2]]; P = P[ConvexHull(P).vertices]; P = np.vstack([P, P[:1]])
            a.fill(P[:, 0] + x0, P[:, 1], color=GRID, zorder=1); a.plot(P[:, 0] + x0, P[:, 1], color=INK2, lw=0.8, zorder=2)
            for xa in sorted({w[0] for w in sp['wheels']}):
                a.add_patch(plt.Circle((xa + x0, sp['R']), sp['R'], fill=False, color=INK, lw=1.4, zorder=3))
            a.plot([G[0] + x0], [G[2]], marker='o', ms=7, color=DOWN, mec=SURF, mew=1.5, zorder=4)
            a.plot([x0 - 260, x0 + 260], [0, 0], color=INK2, lw=0.8)
            h, w = f['hills']['stowed'], f['worst']
            a.text(x0, -45, f"{f['name']}: hills {h['up']}° up / {h['down']}° down\nstep {w['climb']} mm, turn {round(w['turn'])} mm, "
                            f"upright {w['upright']:.2f}\n{f['dims']['mass'] / 1000:.1f} kg, Ø{2 * f['dims']['R']:.0f} wheels, wheelbase "
                            f"{max(x for x, _ in sp['wheels']) - min(x for x, _ in sp['wheels']):.0f}", ha='center', va='top', fontsize=7.5, color=INK)
            x0 += 560
        a.set_xlim(-300, x0 - 260); a.set_ylim(-140, 460)
        a.set_title('Side views, nose to the right; the dot is the centre of mass (tail stowed, not drawn)', color=INK, fontsize=9, loc='left')
    fig.suptitle("Wheels and packs unlocked, the rest at T3's: each knob alone across its range (3 seeds each); hills at friction x2.5 over 2.5 m",
                 fontsize=10, color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.96)); path = os.path.join(OUT, 'hills_run_sheet.png'); fig.savefig(path, dpi=120, facecolor=SURF); print(path)


if __name__ == '__main__':
    main()
