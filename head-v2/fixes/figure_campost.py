"""Camera-post picture sheet (out/camera_posts.png), drawn from the exported files: before/after outside,
head-on at the lower hole, the cut along it, and the two posts as printed."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from vox import load_stl, _scan
from zr import zrender
from campost import TUBES, H, R_BALL, u_of
from export import write_stl, rd

GREY, BLUE, ORANGE, GREEN = (205, 205, 212), (70, 115, 230), (240, 140, 35), (120, 200, 120)

def local(T, tb):
    """triangles into the tube's local frame: x along the hole, y' = v, z' = u"""
    uy, uz = u_of(tb); yt, zt = TUBES[tb]
    P = T - np.array([0, yt, zt]); y, z = P[..., 1], P[..., 2]
    return np.stack([P[..., 0], y * uz - z * uy, y * uy + z * uz], axis=-1)

def slice2d(T, axis, val, lo, hi, h):
    a, b = [d for d in range(3) if d != axis]
    u = np.arange(lo[0], hi[0], h); v = np.arange(lo[1], hi[1], h)
    g = [None] * 3; g[a] = u; g[b] = v; g[axis] = np.array([val])
    return np.squeeze(_scan(T, a, g) & _scan(T, b, g), axis=axis), u, v

def normal_view(tb):
    y, z = TUBES[tb]; x = np.sqrt(R_BALL ** 2 - y ** 2 - (z - H) ** 2)
    d = -np.array([x, y, z - H]) / R_BALL
    p = np.degrees(np.arcsin(-d[2])); cp_ = np.cos(np.radians(p))
    return float(np.degrees(np.arctan2(d[0] / cp_, d[1] / cp_))), float(p), (x, y, z)

if __name__ == '__main__':
    for tb in TUBES:
        write_stl(rd(config.out('camera_post_%s_medium.brep' % tb)), config.out('_fig_campost_%s.stl' % tb), 0.004, 0.05)
    TP = load_stl(config.out('BODY_NUMBA1_snap.stl'))
    TP2 = load_stl(config.out('BODY_NUMBA1_camposts.stl'))
    PL, PU = load_stl(config.out('_fig_campost_lower.stl')), load_stl(config.out('_fig_campost_upper.stl'))
    TC = load_stl(os.path.join(config.CAMERA, 'camera_dummy.stl')) + np.array([2.5, 0, 0])   # board on the wall, X 10.5
    PR = {tb: load_stl(os.path.join(config.PRINT, 'camera_post_%s_medium.stl' % tb)) for tb in TUBES}

    def section(ax, tb, after, title):
        lo, hi, h = (6.0, -5.0), (25.5, 5.0), 0.02
        old = slice2d(local(TP, tb), 2, 0.0, lo, hi, h)[0]
        new, us, vs = slice2d(local(TP2, tb), 2, 0.0, lo, hi, h)
        cam = slice2d(local(TC, tb), 2, 0.0, lo, hi, h)[0]
        img = np.ones(old.shape + (3,))
        if after:
            pst = slice2d(local(PL if tb == 'lower' else PU, tb), 2, 0.0, lo, hi, h)[0]
            img[new] = np.array(GREY) / 255; img[new & ~old] = np.array(GREEN) / 255
            img[cam] = np.array(BLUE) / 255; img[pst] = np.array(ORANGE) / 255
        else:
            img[old] = np.array(GREY) / 255; img[cam] = np.array(BLUE) / 255
        ax.imshow(np.transpose(img, (1, 0, 2)), origin='lower', extent=(us[0], us[-1], vs[0], vs[-1]), interpolation='nearest')
        c = local(np.array([[0.0, 0.0, H]]), tb)[0]
        for R, st, col, lw in ((R_BALL, '-', 'k', 0.6), (R_BALL + 1.5, '--', (0.75, 0.1, 0.1), 1.3)):
            yy = np.linspace(lo[1], hi[1], 400); xx = c[0] + np.sqrt(np.maximum(R ** 2 - c[2] ** 2 - (yy - c[1]) ** 2, 0))
            ax.plot(xx, yy, st, color=col, lw=lw)
        ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_aspect('equal')
        ax.set_title(title, fontsize=11, loc='left', weight='bold'); ax.tick_params(labelsize=7)
        ax.set_xlabel('mm along the hole (toward the front of the ball ->)', fontsize=8)

    fig = plt.figure(figsize=(21, 12.2))
    gs = fig.add_gridspec(2, 4, width_ratios=[0.95, 0.8, 1.45, 0.85], wspace=0.05, hspace=0.14)
    ov = dict(yaw=-116, pitch=6, size=600, center=(17, 13.5, 50.4), ext=19.5, label='')
    yl, pl_, cl = normal_view('lower')
    cv = dict(yaw=yl, pitch=pl_, size=520, center=cl, ext=4.6, label='')
    rows = [('BEFORE', [(TP, GREY), (TC, BLUE)]), ('AFTER', [(TP2, GREY), (TC, BLUE), (PL, ORANGE), (PU, ORANGE)])]
    for r, (tag, meshes) in enumerate(rows):
        ax = fig.add_subplot(gs[r, 0]); ax.imshow(zrender(meshes, **ov)); ax.axis('off')
        ax.set_title('%s: %s' % (tag, 'the two screw holes' if r == 0 else 'snap posts in both holes'), fontsize=12, loc='left', weight='bold')
        ax = fig.add_subplot(gs[r, 1]); ax.imshow(zrender(meshes, **cv)); ax.axis('off')
        ax.set_title('%s: lower hole, head-on' % tag, fontsize=12, loc='left', weight='bold')
        ax = fig.add_subplot(gs[r, 2]); section(ax, 'lower', r == 1, '%s: cut along the lower hole' % tag)
        if r == 0:
            ax.annotate('screw tube, Ø2.6', xy=(17.5, 1.45), xytext=(14.2, 3.7), fontsize=10, arrowprops=dict(arrowstyle='->'))
            ax.annotate('camera board', xy=(11.5, -3.0), xytext=(6.3, -4.5), fontsize=10, color=np.array(BLUE) / 255,
                        arrowprops=dict(arrowstyle='->', color=np.array(BLUE) / 255))
            ax.annotate('wall', xy=(9.2, 3.2), xytext=(6.3, 4.2), fontsize=10, arrowprops=dict(arrowstyle='->'))
            ax.text(22.4, -4.6, 'nest\n1.5 mm out', fontsize=9, color=(0.75, 0.1, 0.1))
        else:
            ax.annotate('pin in the\nboard hole', xy=(10.0, 0.0), xytext=(6.3, 3.3), fontsize=10, arrowprops=dict(arrowstyle='->'))
            ax.annotate('ledge holds the\nboard on the wall', xy=(12.6, 1.5), xytext=(6.3, -4.7), fontsize=10, arrowprops=dict(arrowstyle='->'))
            ax.annotate('barbs click in here', xy=(18.5, 2.15), xytext=(13.6, 4.15), fontsize=10, arrowprops=dict(arrowstyle='->'))
            ax.annotate('head 0.2 mm under\nthe ball surface', xy=(21.25, -1.3), xytext=(21.4, -4.7), fontsize=10, arrowprops=dict(arrowstyle='->'))
            ax.text(13.6, -4.7, 'green = thicker tube wall', fontsize=10, color=(0.2, 0.55, 0.2))
    sub = gs[:, 3].subgridspec(3, 1, height_ratios=[1, 1, 0.5], hspace=0.05)
    for i, (tb, ln) in enumerate((('upper', 14.6), ('lower', 12.7))):
        ax = fig.add_subplot(sub[i]); ax.axis('off')
        T = PR[tb]; c = (T.reshape(-1, 3).min(0) + T.reshape(-1, 3).max(0)) / 2
        bed = np.array([[[-9, -4, 0], [9, -4, 0], [9, 4, 0]], [[-9, -4, 0], [9, 4, 0], [-9, 4, 0]]], float) + [c[0], c[1], -0.02]
        ax.imshow(zrender([(T, ORANGE), (bed, (225, 225, 230))], yaw=-24, pitch=32, size=480, label='', center=(c[0], c[1], 1.0), ext=ln / 2 + 1.5))
        ax.set_title('%s post, %.1f mm (as printed)' % (tb.capitalize(), ln), fontsize=12, loc='left', weight='bold')
    ax = fig.add_subplot(sub[2]); ax.axis('off')
    ax.text(0.0, 0.95, 'Lying on the flat side, pin on the bed,\nangled head facing up.\n\nThe upper post is 0.4 mm thicker,\nso it will not go in the lower hole.',
            transform=ax.transAxes, fontsize=11, va='top')
    plt.savefig(config.out('camera_posts.png'), dpi=72, bbox_inches='tight')
    print('wrote camera_posts.png')
