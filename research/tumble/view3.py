"""The self-righting search as one page: the top designs in an interactive 3D view (the robot inside), the stages,
the margin-against-size chart, tonight's predictions and the guessed numbers.

    python research/tumble/view3.py  -> research/tumble/out/weeble_search.html (three.js r128 from cdnjs)

Full scale, tumble's frame (floor at Z -25).
"""
import os, sys, json, html
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import shell3 as S3, tumble as T
import render3 as R3

OUT = os.path.join(ROOT, 'results', 'search3')


def mesh(P):
    h = ConvexHull(P); F = h.simplices.copy()
    for i, (f, e) in enumerate(zip(F, h.equations)):                      # outward winding
        a, b, c = P[f]
        if np.cross(b - a, c - a) @ e[:3] < 0: F[i] = f[[0, 2, 1]]
    used = np.unique(F); idx = -np.ones(len(P), int); idx[used] = np.arange(len(used))
    return dict(v=np.round(P[used], 1).ravel().tolist(), f=idx[F].ravel().tolist())


def robot_meshes():
    out = []; a = np.linspace(0, 2 * np.pi, 32, endpoint=False)
    for x in T.AXLES:
        for y in (T.TRACK, -T.TRACK):
            out.append(('wheel', mesh(np.vstack([np.c_[x + 55 * np.cos(a), np.full_like(a, y + dy), T.ZA + 55 * np.sin(a)] for dy in (-T.TW / 2, T.TW / 2)]))))
    bx, by, bz, br = T.HEAD['ball']; u = np.random.default_rng(0).normal(size=(300, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
    out.append(('ball', mesh(np.array([bx, by, bz]) + br * u)))
    out.append(('tub', mesh(T.shell_points(66.0, 0.08))))
    return out


def chart():
    """SVG: each stage-2 design's print margin (share of height) against its footprint, coloured by its simulated
    P(upright); the margin search's best per cap as the frontier"""
    Z = np.load(os.path.join(OUT, 'screen.npz')); D = Z['D']; cols = list(Z['cols']); c = {k: i for i, k in enumerate(cols)}
    mg = Z['margins']; top = list(Z['top']); Dy = json.load(open(os.path.join(OUT, 'dyn.json')))['designs']
    W, H, l, r, t, b = 640, 330, 58, 18, 16, 46
    X = lambda v: l + (v - 360) / (660 - 360) * (W - l - r); Y = lambda v: t + (0.18 - v) / (0.18 + 0.04) * (H - t - b)
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Print CoM margin against footprint">']
    for v in np.arange(-0.04, 0.181, 0.02):
        s.append(f'<line x1="{l}" x2="{W - r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="{"zero" if abs(v) < 1e-9 else "grid"}"/>')
        s.append(f'<text x="{l - 8}" y="{Y(v) + 4:.1f}" text-anchor="end" class="tick">{v * 100:.0f}%</text>')
    for v in range(375, 661, 50):
        s.append(f'<text x="{X(v):.1f}" y="{H - b + 18}" text-anchor="middle" class="tick">{v}</text>')
    s.append(f'<text x="{(l + W - r) / 2:.0f}" y="{H - 8}" text-anchor="middle" class="axis">footprint, the larger of length and width (mm, full scale)</text>')
    s.append(f'<text x="14" y="{(t + H - b) / 2:.0f}" text-anchor="middle" class="axis" transform="rotate(-90 14 {(t + H - b) / 2:.0f})">CoM margin, share of print height</text>')
    for rr in Dy:
        j = top.index(rr['i']); i = rr['i']; x = max(D[i, c['length']], D[i, c['width']]); y = mg[j, 0] / mg[j, 2]; p = rr['print_up']
        k = 'p1' if p >= 1 else 'p2' if p >= 0.95 else 'p3'
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(max(y, -0.04)):.1f}" r="2.6" class="{k}"/>')
    Rm = json.load(open(os.path.join(OUT, 'refine_margin.json')))['caps']
    fr = []
    for name in ('plan 400', 'plan 450', 'plan 500', 'any'):
        bst = Rm[name]['best'][0]; sz = S3.size(S3.as_dict(bst['x'])); fr.append((max(sz['length'], sz['width']), bst['margin_frac'], name))
    s.append('<polyline class="front" points="' + ' '.join(f'{X(x):.1f},{Y(y):.1f}' for x, y, _ in fr) + '"/>')
    for x, y, name in fr:
        e4 = name == 'plan 450'
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{6 if e4 else 4.5}" class="{"e4" if e4 else "fp"}"/>')
        lab = 'E4 (cap 450)' if e4 else {'plan 400': 'cap 400', 'plan 500': 'cap 500', 'any': 'no cap'}[name]
        s.append(f'<text x="{X(x) + (-10 if name == "any" else 9):.1f}" y="{Y(y) - 9:.1f}" text-anchor="{"end" if name == "any" else "start"}" class="lab">{lab} {y * 100:.0f}%</text>')
    s.append('</svg>')
    return '\n'.join(s)


PAGE = open(os.path.join(HERE, 'view3_template.html'), encoding='utf-8').read() if os.path.exists(os.path.join(HERE, 'view3_template.html')) else None


def write(out=None):
    rows = R3.designs()
    keys = ['e3', 'box', 'c400', 'e4', 'c500', 'any']
    data = dict(designs=[dict(key=k, title=r['title'], lines=r['lines'], size=np.ptp(r['P'], 0).round(0).tolist(),
                              old=r['color'] != R3.NEW and k in ('e3', 'box'), hull=mesh(r['P'])) for k, r in zip(keys, rows)],
                robot=robot_meshes())
    page = PAGE.replace('/*DATA*/null', json.dumps(data, separators=(',', ':'))).replace('<!--CHART-->', chart())
    out = out or os.path.join(HERE, 'out', 'weeble_search.html')
    os.makedirs(os.path.dirname(out), exist_ok=True); open(out, 'w', encoding='utf-8').write(page)
    return out


if __name__ == '__main__':
    print(write())
