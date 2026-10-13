"""The cradle's wire ridge, blended in (2026-10-02). The round 1 cradle printed well; as a final touch Zach
asked to even out the "snickers vein": the conduit round the wire hole stood out of the -Y wall as a narrow
ridge, with a notch where it left the collar. tree_parts_b.CONDUIT_K, the smooth-union radius between the
conduit and the wall, goes 1.5 -> 6, so the ridge swells into the wall. The +Y twin is its mirror and follows.

Looks only. Every hole and clearance (the wire hole, the ball's sweep, the ribbon's track and trough, the
plug chute, the stub's bore, the screws) is cut after the blend, so none of them changes. This script lists
every lump of plastic the new cradle adds or removes, then draws the before/after sheet.

    python head-v2/generator/generators/tree_parts_b.py fork     # ~5 min
    python head-v2/fixes/wire_route_r1.py                         # print files + plate; moves the printed cradle aside
    python head-v2/fixes/cradle_blend.py                          # this
    python head-v2/checks/wire_route.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from scipy import ndimage
import pymeshlab as ml
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import tree_parts as TP_
import tree_parts_b as B
from pan_print_set import OUT
from wire_route_r1 import OLD_DIR

K_OLD, K_NEW = 1.5, B.CONDUIT_K
OBJ = os.path.join(config.REPO, 'head-v2', 'generator', 'tree-parts-b', 'fusion', 'fork.obj')   # head frame
ST = 0.4


def fork_at(k, p):
    k0 = B.CONDUIT_K; B.CONDUIT_K = k
    try:
        return B.fork(p)
    finally:
        B.CONDUIT_K = k0


def added():
    """Every lump the new blend adds (and anything it removes), over the whole cradle at ST."""
    lo, hi = (-46.0, B.POD_M_Y1 - 3, B.BASE_Z - 0.5), (34.0, B.POD_P_Y1 + 3, B.H + 30.0)
    X, Y, Z = np.meshgrid(*[np.arange(lo[i], hi[i], ST) for i in range(3)], indexing='ij')
    f = lambda k: np.concatenate([fork_at(k, (X[i:i + 6], Y[i:i + 6], Z[i:i + 6])) for i in range(0, len(X), 6)])
    old, new = f(K_OLD), f(K_NEW)
    add, rem = (new < 0) & (old >= 0), (new >= 0) & (old < 0)
    print('blend %g -> %g: adds %.0f mm3, removes %.1f mm3' % (K_OLD, K_NEW, add.sum() * ST ** 3, rem.sum() * ST ** 3))
    lab, n = ndimage.label(add)
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() * ST ** 3 < 0.5:
            continue
        ix = np.argwhere(m); p0, p1 = np.array(lo) + ix.min(0) * ST, np.array(lo) + ix.max(0) * ST
        print('  %6.1f mm3  X %5.1f..%5.1f  Y %5.1f..%5.1f  Z %5.1f..%5.1f  surface out by up to %.2f'
              % (m.sum() * ST ** 3, p0[0], p1[0], p0[1], p1[1], p0[2], p1[2], old[m].max()))
    return rem.sum() * ST ** 3


def mesh(path, faces=90000):
    with TP_.quiet():
        m = ml.MeshSet(); m.load_new_mesh(path)
        if m.current_mesh().face_number() > faces:
            m.meshing_decimation_quadric_edge_collapse(targetfacenum=faces, preservenormal=True)
    return m.current_mesh().vertex_matrix().copy(), m.current_mesh().face_matrix().copy()


def render(ax, V, F, az, el, centre, half, title):
    """Shaded orthographic view (painter's order), zoomed on centre +- half (head frame, mm)."""
    a, e = np.radians(az), np.radians(el)
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])          # toward the viewer
    r = np.cross([0, 0, 1], d); r /= np.linalg.norm(r); u = np.cross(d, r)
    T = V[F]; n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    vis = n @ d > 0; T, n = T[vis], n[vis]
    L = d * 0.6 + u * 0.6 + r * 0.3; L /= np.linalg.norm(L)
    sh = 0.25 + 0.65 * np.clip(n @ L, 0, 1) + 0.15 * np.clip(n @ d, 0, 1)
    o = np.argsort(T.mean(1) @ d)
    P = np.stack([T @ r, T @ u], -1)[o]; c = np.clip(np.outer(sh[o], (0.80, 0.74, 0.62)), 0, 1)
    ax.add_collection(PolyCollection(P, facecolors=c, edgecolors=c, linewidths=0.5, antialiased=False))
    cx, cy = np.asarray(centre) @ r, np.asarray(centre) @ u
    ax.set_xlim(cx - half, cx + half); ax.set_ylim(cy - half, cy + half)
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title, fontsize=10)


def sheet(path):
    # The print STLs are recentred; the generator's viewer mesh is in the head frame. Same outline, so the
    # offset between their boxes puts both STLs back in the head frame.
    Vh, _ = mesh(OBJ, 20000)
    parts = {}
    for tag, stl in (('BEFORE (as printed)', os.path.join(OLD_DIR, 'cradle.stl')), ('AFTER', os.path.join(OUT, 'cradle.stl'))):
        V, F = mesh(stl)
        parts[tag] = (V - V.min(0) + Vh.min(0), F)
    fig, axs = plt.subplots(3, 3, figsize=(18, 18))
    views = [(-125, 12, (-4, -20, 30), 34, 'the -Y side'), (-90, 2, (-5, -30, 27), 16, '-Y wall, close'),
             (-165, 4, (-5, -28, 27), 16, '-Y wall from behind')]
    for row, (tag, (V, F)) in enumerate(parts.items()):
        for col, (az, el, c, h, t) in enumerate(views):
            render(axs[row, col], V, F, az, el, c, h, '%s: %s' % (tag, t))
    # row 3: what's added, in section, and the +Y twin after
    ax = axs[2, 0]; ys, zs = np.arange(-38, -8, 0.06), np.arange(9, 46, 0.06); Yg, Zg = np.meshgrid(ys, zs)
    p = (np.full_like(Yg, -5.0), Yg, Zg); o, n = fork_at(K_OLD, p), fork_at(K_NEW, p)
    ax.contourf(ys, zs, o, levels=[-99, 0], colors=['#b9b2a2'])
    ax.contourf(ys, zs, np.where((n < 0) & (o >= 0), -1.0, 1.0), levels=[-2, 0], colors=['#e0443e'])
    ax.contour(ys, zs, B.wire_tube(p), levels=[0], colors=['#1f5fbf'], linewidths=1.0)
    ax.set_title('section at X -5, through the ridge', fontsize=10); ax.set_xlabel('Y'); ax.set_ylabel('Z')
    ax = axs[2, 1]; xs, ys2 = np.arange(-24, 12, 0.06), np.arange(-38, -12, 0.06); Xg, Yg2 = np.meshgrid(xs, ys2)
    p = (Xg, Yg2, np.full_like(Xg, 25.0)); o, n = fork_at(K_OLD, p), fork_at(K_NEW, p)
    ax.contourf(xs, ys2, o, levels=[-99, 0], colors=['#b9b2a2'])
    ax.contourf(xs, ys2, np.where((n < 0) & (o >= 0), -1.0, 1.0), levels=[-2, 0], colors=['#e0443e'])
    ax.contour(xs, ys2, B.wire_tube(p), levels=[0], colors=['#1f5fbf'], linewidths=1.0)
    ax.set_title('section at Z 25, across the ridge (from above)', fontsize=10); ax.set_xlabel('X (lens ->)'); ax.set_ylabel('Y')
    for ax in axs[2, :2]:
        ax.set_aspect('equal'); ax.grid(alpha=0.3)
    render(axs[2, 2], *parts['AFTER'], 125, 12, (-4, 20, 30), 34, 'AFTER: the +Y twin (looks only, solid)')
    fig.text(0.01, 0.006, 'Grey: the cradle as printed. Red: what the blend adds (it removes nothing). Blue: the 5 mm wire hole, '
             'unchanged. The ridge\'s blend radius goes %g -> %g mm.' % (K_OLD, K_NEW), fontsize=11)
    plt.tight_layout(rect=(0, 0.015, 1, 1)); plt.savefig(path, dpi=60); plt.close(fig)


if __name__ == '__main__':
    removed = added()
    sheet(os.path.join(OUT, 'cradle_blend.png')); print('wrote cradle_blend.png')
    sys.exit(1 if removed > 0 else 0)
