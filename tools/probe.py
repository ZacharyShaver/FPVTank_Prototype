"""Exact surface positions in a mesh, by ray casting (Moller-Trumbore).

    from probe import mesh, show
    show('rear post axis', mesh('ball_plus'), (-23, 0, 43), 1)   # every solid run along Y through that point
"""
import numpy as np
import config
from vox import load_stl

_meshes = {}
def mesh(name):
    """one of Zach's parts ('ball_plus', 'ball_minus', 'post') as an (n, 3, 3) triangle array, cached"""
    if name not in _meshes:
        _meshes[name] = load_stl(config.zach(name))
    return _meshes[name]

def hits(T, o, d):
    o, d = np.asarray(o, float), np.asarray(d, float)
    v0, v1, v2 = T[:, 0], T[:, 1], T[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    pv = np.cross(d, e2); det = (e1 * pv).sum(1); ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    tv = o - v0; u = (tv * pv).sum(1) * inv; qv = np.cross(tv, e1); v = (d * qv).sum(1) * inv
    t = (e2 * qv).sum(1) * inv
    t = np.sort(t[ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9)])
    keep = []
    for x in t:
        if not keep or x - keep[-1] > 1e-5: keep.append(x)
    return np.array(keep)

def line(T, o, axis, lo=-60):
    """all crossings along an axis-parallel line through o, as coordinates on that axis"""
    d = np.zeros(3); d[axis] = 1.0
    o = np.array(o, float); o[axis] = lo
    return hits(T, o, d) + lo

def show(tag, T, o, axis):
    c = line(T, o, axis)
    ax = 'XYZ'[axis]
    segs = ['%s %.2f..%.2f' % (ax, c[i], c[i + 1]) for i in range(0, len(c) - 1, 2)]
    print('  %-44s solid: %s' % (tag, ', '.join(segs) if segs else '-'))
