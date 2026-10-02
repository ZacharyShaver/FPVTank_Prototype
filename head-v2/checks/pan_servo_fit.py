"""Zach's MG90S model (2026-09-28) in the pan coil's servo pocket: seated, and sliding in through the side
window. The servo is his mesh (head-v2/generator/pan-coil-b/MG90S.3MF) filled with points; the parts are
the generator's own SDFs, so a point inside both is real overlap.

Placement: the tabs' shaft-side face on the pocket's tab shelf (TAB_Z0), shaft on the gear's axis.
Control: the same servo lifted 4.6 mm, where set 3's first shelf (tabs 6.5 below the case face, the
datasheet guess) would have held it. It must read nonzero against the base's deck. The slide has its own control: the servo 1.5 lower, so its
block drags through the wall under the channel cut for it.

    python head-v2/checks/pan_servo_fit.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import re, zipfile
import numpy as np
from vox import voxelize
import pan_coil_b as P

MG90S = os.path.join(config.REPO, 'head-v2', 'generator', 'pan-coil-b', 'MG90S.3MF')
STEP = 0.2


def mesh():
    """His two bodies, the case with tabs and the shaft, in the model's frame: x along the case (shaft
    at x -5.4), y up from the far end (case face 22.4), z across (0..12.2)."""
    s = zipfile.ZipFile(MG90S).read('3D/3dmodel.model').decode('utf-8')
    comp = {m[0]: np.array(m[1].split()[-3:], float) for m in
            re.findall(r'<component objectid="(\d+)" transform="([^"]+)"', s)}
    tris = []
    for oid, sub in (('6', '5'), ('3', '2')):             # body (in 5), shaft (in 2)
        o = re.search(r'<object id="%s"[^>]*>(.*?)</object>' % oid, s, re.S).group(1)
        V = np.array(re.findall(r'<vertex x="([^"]+)" y="([^"]+)" z="([^"]+)"', o), float)
        F = np.array(re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', o), int)
        tris.append(V[F] + comp[sub] - comp['5'])
    return tris


def placed_points(lift=0.0):
    """Points inside the servo, in the pan frame: model y -> Z down from SV_Z1, x -> Y (shaft on Y 0),
    z -> X across (proper rotation)."""
    pts = []
    for T in mesh():
        lo, hi = T.reshape(-1, 3).min(0) - STEP, T.reshape(-1, 3).max(0) + STEP
        grid = [np.arange(lo[i], hi[i], STEP) for i in range(3)]
        inside = voxelize(T, grid)
        I = np.argwhere(inside)
        q = np.stack([grid[i][I[:, i]] for i in range(3)], 1)
        X = P.CENTRE + 6.1 - q[:, 2]
        Y = q[:, 0] + 5.4
        Z = P.SV_Z1 - q[:, 1] + lift
        pts.append(np.stack([X, Y, Z], 1))
    return np.concatenate(pts)


def overlap(pts, fn, dy=0.0):
    return np.count_nonzero(fn((pts[:, 0], pts[:, 1] + dy, pts[:, 2])) < 0) * STEP ** 3


if __name__ == '__main__':
    pts = placed_points()
    tab_face = P.SV_Z1 - 20.5
    print('MG90S: %d points, %.2f cm3; tab face at Z %.2f, shelf TAB_Z0 %.2f; case face Z %.2f; shaft tip Z %.2f; '
          'gear top %.2f' % (len(pts), len(pts) * STEP ** 3 / 1000, tab_face, P.TAB_Z0, P.SV_Z1 - 22.4,
                             P.SV_Z1 - 32.4, P.G_Z1))
    bad = 0
    print('\n%-26s %10s' % ('seated vs', 'mm3'))
    for name in ('base', 'well', 'bay', 'drum', 'gear_in', 'gear_out', 'floor'):
        v = overlap(pts, getattr(P, name))
        note = '   (the shaft in the PLACEHOLDER horn pocket, known)' if name == 'gear_in' else ''
        bad += v > 1.0 and name != 'gear_in'
        print('%-26s %10.2f%s' % (name, v, note))
    print('\n%-26s %10s' % ('sliding in along -Y, at', 'vs base'))
    worst = 0.0
    for dy in (40, 30, 22, 16, 10, 6, 3, 1):
        v = overlap(pts, P.base, dy)             # servo moved +dy (out toward the window): base sampled at points + dy
        worst = max(worst, v)
        print('%-26s %10.2f' % ('  +%d mm' % dy, v))
    bad += worst > 1.0
    ctrl = overlap(placed_points(lift=4.6), P.base)
    print('\ncontrol, lifted 4.6 (set 3 first shelf) vs base: %.2f mm3 (must be nonzero)' % ctrl)
    bad += ctrl <= 1.0
    low = placed_points(lift=-1.5)
    ctrl2 = max(overlap(low, P.base, dy) for dy in (22, 16, 10, 6, 3))
    print('control, 1.5 lower, sliding in: worst %.2f mm3 (must be nonzero: the block drags under its channel)' % ctrl2)
    bad += ctrl2 <= 1.0
    print('\n%s' % ('FITS: seated and sliding in clear' if not bad else '<== %d problem(s)' % bad))
    sys.exit(1 if bad else 0)
