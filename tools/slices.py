"""High-res planar slices of Zach's parts with the servo (turned) and camera overlaid."""
import os, sys, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import config
from vox import load_stl, _scan

def slice2d(T, axis, val, lo, hi, h=0.05):
    """solid mask on the plane coord[axis]=val; returns (mask, u, v, (ua, va)) with u,v the in-plane axes"""
    a, b = [d for d in range(3) if d != axis]
    u = np.arange(lo[0], hi[0], h); v = np.arange(lo[1], hi[1], h)
    g = [None] * 3; g[a] = u; g[b] = v; g[axis] = np.array([val])
    m = _scan(T, a, g) & _scan(T, b, g)
    return np.squeeze(m, axis=axis), u, v, (a, b)

def draw(ax, T, axis, val, lo, hi, title, overlays=(), h=0.05, color='0.55'):
    m, u, v, (a, b) = slice2d(T, axis, val, lo, hi, h)
    ax.imshow(m.T, origin='lower', extent=(u[0], u[-1], v[0], v[-1]), cmap='Greys', vmin=0, vmax=1.6,
              interpolation='nearest')
    for f in overlays:
        f(ax, axis, val)
    ax.set_title(title, fontsize=9); ax.set_aspect('equal')
    ax.set_xlabel('XYZ'[a]); ax.set_ylabel('XYZ'[b])
    ax.grid(True, lw=0.3, alpha=0.5)
    return m, u, v

if __name__ == '__main__':
    TP = load_stl(config.zach('ball_plus'))
    jobs = [(1, 12.5), (1, 14.7), (1, 17.0), (1, 19.5), (2, 36.0), (2, 52.0), (2, 65.0), (0, 9.25), (0, 15.0), (0, 20.0)]
    fig, axs = plt.subplots(2, 5, figsize=(26, 11))
    for ax, (axis, val) in zip(axs.flat, jobs):
        if axis == 1: lo, hi = (-32, 20), (32, 84)
        elif axis == 2: lo, hi = (-32, -1), (32, 26)
        else: lo, hi = (-1, 20), (26, 84)
        draw(ax, TP, axis, val, lo, hi, 'ball_plus @ %s %.2f' % ('XYZ'[axis], val))
    plt.tight_layout(); plt.savefig(config.out('slices_plus.png'), dpi=80)
