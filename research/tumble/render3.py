"""The search's top designs on one sheet: a shaded 3D view and side and front silhouettes of each hull, the robot
inside, and its simulated numbers. Full scale, tumble's frame (floor at Z -25).

    python research/tumble/render3.py  -> research/figures/search3_top_designs.png
"""
import os, sys, json
import numpy as np
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import shell3 as S3, tumble as T

OUT = os.path.join(ROOT, 'results', 'search3')
NEW, OLD, ROB = '#2a7de1', '#d9822b', '#3b3f46'


def designs():
    F = json.load(open(os.path.join(OUT, 'final.json')))['designs']
    first = lambda tag: next(d for d in F if d['tag'] == tag)
    W = json.load(open(os.path.join(OUT, 'winner.json')))
    box = max(json.load(open(os.path.join(OUT, 'box_best.json'))), key=lambda d: d['print_up'])
    e3 = json.load(open(os.path.join(ROOT, 'models', 'E3_tall.json')))['params']
    lo = lambda d: min(d['print'][k]['p_upright'] for k in ('hard39', 'hard31', 'hard55', 'softfit', 'hard39_mu0.65', 'hard39_mu1.5'))
    row = lambda d, title: dict(title=title, P=S3.body(d['params']), color=NEW,
                                lines=[f"print: upright {lo(d):.3f} (worst of 6 models, 240 drops each)",
                                       f"  coins high (control): {d['print']['hard39_high']['p_upright']:.2f}",
                                       f"robot: upright {d['robot']['p_upright']:.3f} (600 drops), cover {d['robot']['cover_g']} g",
                                       f"CoM margin: print {d['margin_print_mm']:.1f} mm ({d['margin_print_mm'] / d['print_h']:.0%} of height)"])
    return [dict(title='E3, the old best (printed)', P=np.vstack([T.shell_points(e3['top'], e3['round'], width=e3['width']), S3.ROBOT]), color=OLD,
                 lines=['print: upright 0.54 sim (committed, 0.39 floor)', '  seen at 15 cm: 16/30', 'robot: upright 0.67 (sweep best, cover + bounce)',
                        'CoM margin: -17.6 mm (needs to drop that far)']),
            dict(title="Best inside the old sweep's box", P=S3.body(S3.as_dict(box['x'])), color=OLD,
                 lines=[f"print: upright {box['print_up']:.2f} (240 drops)", '', f"robot: upright {box['robot_up']:.2f} (400 drops)",
                        'not monostatic: inverted and side rests remain']),
            row(first('margin, plan 400'), 'Footprint cap 400 mm'),
            dict(row(W, 'E4_weeble: cap 450 mm (the print)'), color='#1b9e5a'),
            row(first('margin, plan 500'), 'Footprint cap 500 mm'),
            row(first('margin, any'), 'No cap (most margin)')]


def robot_parts(ax, view):
    a = np.linspace(0, 2 * np.pi, 40)
    if view == 'side':
        for x in T.AXLES:
            ax.fill(x + 55 * np.cos(a), T.ZA + 55 * np.sin(a), color=ROB, alpha=0.85, lw=0)
    else:
        for y in (T.TRACK, -T.TRACK):
            ax.fill([y - T.TW / 2, y + T.TW / 2, y + T.TW / 2, y - T.TW / 2], [T.ZA - 55, T.ZA - 55, T.ZA + 55, T.ZA + 55], color=ROB, alpha=0.85, lw=0)
    bx, by, bz, br = T.HEAD['ball']
    ax.fill((bx if view == 'side' else by) + br * np.cos(a), bz + br * np.sin(a), color='#c8743a', alpha=0.9, lw=0)
    tub = T.shell_points(66.0, 0.08); j = (0, 2) if view == 'side' else (1, 2)
    h = ConvexHull(tub[:, j]); ax.fill(*tub[h.vertices][:, j].T, color='#8a9099', alpha=0.6, lw=0)


def silhouette(ax, P, view, color):
    j = (0, 2) if view == 'side' else (1, 2)
    h = ConvexHull(P[:, j]); v = P[h.vertices][:, j]
    ax.fill(*v.T, color=color, alpha=0.18, lw=0); ax.plot(*np.vstack([v, v[:1]]).T, color=color, lw=1.6)
    robot_parts(ax, view)
    ax.axhline(-25, color='#999', lw=0.8); ax.set_aspect('equal'); ax.set_xlim(-330, 330); ax.set_ylim(-40, 420); ax.axis('off')


def shaded(ax, P, color):
    h = ConvexHull(P); tri = P[h.simplices]
    L = np.array([0.4, -0.6, 0.7]); L /= np.linalg.norm(L)
    n = h.equations[:, :3]; s = 0.45 + 0.55 * np.clip(n @ L, 0, 1)
    rgb = np.array(matplotlib.colors.to_rgb(color))
    pc = Poly3DCollection(tri, facecolors=np.clip(rgb[None] * s[:, None] + 0.15 * (1 - s[:, None]), 0, 1), edgecolor='none', alpha=0.55)
    ax.add_collection3d(pc)
    for x in T.AXLES:                                                  # the wheels, as discs
        for y in (T.TRACK, -T.TRACK):
            a = np.linspace(0, 2 * np.pi, 30)
            ax.plot(x + 55 * np.cos(a), np.full_like(a, y), T.ZA + 55 * np.sin(a), color=ROB, lw=1.2)
    ax.set_xlim(-300, 300); ax.set_ylim(-300, 300); ax.set_zlim(-25, 420); ax.set_box_aspect((600, 600, 445), zoom=1.55)
    ax.view_init(elev=22, azim=-58); ax.axis('off')


if __name__ == '__main__':
    D = designs(); n = len(D)
    fig = plt.figure(figsize=(15, 2.95 * n)); gs = fig.add_gridspec(n, 4, width_ratios=[1.15, 1, 1, 1.25], wspace=0.02, hspace=0.08)
    for i, d in enumerate(D):
        ax = fig.add_subplot(gs[i, 0], projection='3d'); shaded(ax, d['P'], d['color'])
        a1, a2 = fig.add_subplot(gs[i, 1]), fig.add_subplot(gs[i, 2])
        silhouette(a1, d['P'], 'side', d['color']); silhouette(a2, d['P'], 'front', d['color'])
        if i == 0:
            a1.set_title('side (nose right)', fontsize=10, color='#666'); a2.set_title('front', fontsize=10, color='#666')
        t = fig.add_subplot(gs[i, 3]); t.axis('off'); e = np.ptp(d['P'], 0)
        t.text(0, 0.92, d['title'], fontsize=12, weight='bold', color=d['color'], va='top')
        t.text(0, 0.74, f'{e[0]:.0f} long x {e[1]:.0f} wide x {e[2]:.0f} tall (mm)', fontsize=9.5, va='top', color='#333')
        for k, s in enumerate(d['lines']):
            t.text(0, 0.58 - 0.14 * k, s, fontsize=9.5, va='top', family='monospace' if s.startswith('  ') else None)
    fig.suptitle('Self-righting search: the top designs, the robot inside (wheels, head ball orange, tub grey)', fontsize=13, y=0.905)
    out = os.path.join(ROOT, 'figures', 'search3_top_designs.png')
    fig.savefig(out, dpi=110, bbox_inches='tight', facecolor='white'); print(out)
