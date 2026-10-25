"""E4's shell as a robot would wear it: side and front views of the shell itself (not the hull) over the wheels,
with the floor, the tub's approach and departure lines, and E4 as a 12-hoop cage.

    python research/tumble/fig_e4_ground.py  -> research/figures/e4_ground.png
"""
import os, sys, json
import numpy as np
from scipy.spatial import ConvexHull
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import shell3 as S3, tumble as T

q = json.load(open(os.path.join(ROOT, 'results', 'search3', 'winner.json')))['params']
SH = S3.shell_points(q, n=144, k=40); FL = -25.0; G4, TY, TUB, BALL = '#13824f', '#2f3439', '#8d959c', '#c8743a'
fig = plt.figure(figsize=(15, 5.2)); gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1, 1], wspace=0.08)
a = np.linspace(0, 2 * np.pi, 80)


def outline(ax, pts, edge=None, **kw):
    h = ConvexHull(pts); v = pts[h.vertices]; ax.fill(*v.T, **kw)
    if edge: ax.plot(*np.vstack([v, v[:1]]).T, color=edge, lw=2)


for i, view in enumerate(('side', 'front')):
    ax = fig.add_subplot(gs[i]); j = (0, 2) if view == 'side' else (1, 2)
    outline(ax, SH[:, j], edge=G4, facecolor=G4, alpha=0.13, lw=0)
    outline(ax, T.shell_points(66.0, 0.08)[:, j], facecolor=TUB, alpha=0.6, lw=0)
    if view == 'side':
        for x in T.AXLES: ax.fill(x + 55 * np.cos(a), T.ZA + 55 * np.sin(a), color=TY)
        for x0, ang, s in ((T.AXLES[0], 22.5, 1), (T.AXLES[1], 33.5, -1)):          # ramps tangent to the tyres
            t = np.radians(ang); px = x0 + s * 55 * np.sin(t); pz = T.ZA - 55 * np.cos(t)
            x_fl = px + (FL - pz) / (s * np.tan(t)); xs = np.array([x_fl, px + s * 150])
            ax.plot(xs, pz + (xs - px) * s * np.tan(t), color='#b9661a', lw=1.5, ls='--')
        ax.text(315, -48, 'approach 22.5°', color='#b9661a', fontsize=10, ha='right'); ax.text(-315, -48, 'departure 33.5°', color='#b9661a', fontsize=10)
        ax.set_title('side: the shell stops 32 mm off the floor, the tyres do the touching', fontsize=11)
    else:
        for y in (T.TRACK, -T.TRACK): ax.fill([y - 23, y + 23, y + 23, y - 23], [FL, FL, T.ZA + 55, T.ZA + 55], color=TY)
        ax.annotate('', xy=(185, FL), xytext=(185, T.Z0), arrowprops=dict(arrowstyle='<->', color='#333'))
        ax.text(192, -12, '32 mm', fontsize=10)
        ax.set_title('front: 27 mm of skirt past each tyre, at 32 mm up', fontsize=11)
    bx, by, bz, br = T.HEAD['ball']; ax.fill((bx if view == 'side' else by) + br * np.cos(a), bz + br * np.sin(a), color=BALL)
    ax.axhline(FL, color='#555', lw=1.2); ax.set_aspect('equal'); ax.set_xlim(-320, 320); ax.set_ylim(-60, 330); ax.axis('off')

ax = fig.add_subplot(gs[2], projection='3d')
m = S3.shell_points(q, n=12, k=60); rings = m[:-1].reshape(-1, 12, 3)             # 12 meridian hoops, base ring, widest ring
for k in range(12):
    sel = rings[:, k, :]; sel = np.vstack([sel[np.argsort(sel[:, 2])], m[-1:]]); ax.plot(*sel.T, color=G4, lw=1.6)
for zz in (SH[:, 2].min(), q['zc']):
    r = SH[np.isclose(SH[:, 2], zz, atol=0.6)]; r = r[np.argsort(np.arctan2(r[:, 1], r[:, 0] - q['xc']))]; ax.plot(*np.vstack([r, r[:1]]).T, color=G4, lw=1.6)
for x in T.AXLES:
    for y in (T.TRACK, -T.TRACK): ax.plot(x + 55 * np.cos(a), np.full_like(a, y), T.ZA + 55 * np.sin(a), color=TY, lw=2)
ax.set_xlim(-230, 230); ax.set_ylim(-230, 230); ax.set_zlim(-25, 310); ax.set_box_aspect((460, 460, 335), zoom=1.25); ax.view_init(18, -60); ax.axis('off')
ax.set_title('the same shape as 12 hoops: still one rest state\n(margin 23-45 mm vs 33 for the full skin)', fontsize=11)
out = os.path.join(ROOT, 'figures', 'e4_ground.png'); fig.savefig(out, dpi=110, bbox_inches='tight', facecolor='white'); print(out)
