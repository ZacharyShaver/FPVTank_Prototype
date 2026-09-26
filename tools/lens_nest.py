"""Points on a part's surface, the tilt motion, and the nest's exact SDF (the generator's B.fork)
evaluated at those points: does a part clear the nest through the whole tilt range, and does the nest
stay out of the camera's view?"""
import numpy as np
from kit import B
H = B.H
V_HALF = 30.0

def surface_points(T, step=0.25):
    pts = []
    for tri in T:
        a, b, c = tri
        n = max(2, int(np.ceil(max(np.linalg.norm(b - a), np.linalg.norm(c - a), np.linalg.norm(c - b)) / step)))
        i, j = np.meshgrid(np.arange(n + 1), np.arange(n + 1), indexing='ij')
        m = i + j <= n
        u, v = i[m] / n, j[m] / n
        pts.append(a + np.outer(u, b - a) + np.outer(v, c - a))
    return np.unique(np.round(np.vstack(pts), 4), axis=0)

def tilt(P, deg):
    a = np.radians(deg); x, y, z = P[:, 0], P[:, 1], P[:, 2] - H
    return np.c_[x * np.cos(a) - z * np.sin(a), y, x * np.sin(a) + z * np.cos(a) + H]

def _frame(t):
    a = np.radians(t)
    return np.array([np.cos(a), 0, np.sin(a)]), np.array([-np.sin(a), 0, np.cos(a)]), np.array([0, 1.0, 0])

def view_depth(fn, tip_x, t, r_max=60.0, dr=0.7):
    ax, up, side = _frame(t); qs = []
    for half in np.radians(np.arange(0, V_HALF + 0.01, 5)):
        for th in np.radians(np.arange(0, 360, 10)):
            d = ax * np.cos(half) + (up * np.cos(th) + side * np.sin(th)) * np.sin(half)
            o = ax * tip_x
            qs += [o + d * r for r in np.arange(0.5, r_max, dr)]
    q = np.asarray(qs)
    return max(0.0, float((-fn((q[:, 0], q[:, 1], q[:, 2] + H))).max()))

def nest_sweep(T, step=0.4, every=2.5):
    """A ball half against the nest over the whole tilt range. Returns (nearest, deepest) in mm.

    Only points that can meet the nest are sampled: the outer shell (r > 28.5) and the hubs (|Y| > 22.5).
    The nest's SDF has a zero-thickness sheet on the plane |Y| = B.BRG_P_Y0 inside the hub bore (two bores
    abut there). It reads as 'touching' but is not material, so `nearest` is taken off that plane.
    `deepest` (how far any point gets inside the nest) is taken everywhere: a sheet can't make it nonzero."""
    P = surface_points(T, step=step)
    r = np.sqrt(P[:, 0] ** 2 + P[:, 1] ** 2 + (P[:, 2] - H) ** 2)
    P = P[(r > 28.5) | (np.abs(P[:, 1]) > 22.5)]
    off = ~((np.abs(np.abs(P[:, 1]) - B.BRG_P_Y0) < 0.5) & (np.hypot(P[:, 0], P[:, 2] - H) < 10.2))
    near, deep = np.inf, 0.0
    for t in np.arange(B.TILT_DOWN, B.TILT_UP + 0.01, every):
        Q = tilt(P, t); d = B.fork((Q[:, 0], Q[:, 1], Q[:, 2]))
        near = min(near, d[off].min()); deep = max(deep, -d.min())
    return near, deep
