"""Adversary probe: downward-facing base surface steeper than 30 deg off vertical, above the well floor.

The base prints upright (the deck's support cone grows down from it), so every downward-facing face more than
30 deg off vertical inside the well needs support: the rule the set 7 note itself uses. Reads the design only.
    python overhang.py [mutant_file mutant_id]
"""
import sys, importlib.util
import numpy as np
import pan_coil_b as P

if len(sys.argv) > 2:
    spec = importlib.util.spec_from_file_location('mf', sys.argv[1])
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    M.MUTANTS[sys.argv[2]][0](P)
if '--set6' in sys.argv:
    P.INSERT = False
    P.RING_PART = False

h = 0.25
xs = np.arange(-33, 33 + h, h)
ys = np.arange(-33, 33 + h, h)
zs = np.arange(P.FLOOR_Z + 0.5 - h, P.BRG_Z1 + 1.5, h)
Y, Z = np.meshgrid(ys, zs, indexing='ij')
cnt, pts = 0, []
prev = None
for i0 in range(0, len(xs), 8):
    xx = xs[max(i0 - 1, 0):i0 + 9]  # one slice of overlap each side for the x gradient
    X3 = xx[:, None, None] + 0 * Y[None]
    S = P.base((X3, np.broadcast_to(Y, X3.shape), np.broadcast_to(Z, X3.shape)), True)
    solid = S < 0
    gz = np.gradient(S, h, axis=2)
    gy = np.gradient(S, h, axis=1)
    gx = np.gradient(S, h, axis=0)
    g = np.sqrt(gx ** 2 + gy ** 2 + gz ** 2) + 1e-9
    nz = gz / g
    down = np.zeros_like(solid)
    down[:, :, 1:] = solid[:, :, 1:] & ~solid[:, :, :-1]
    bad = down & (nz < -0.5 - 0.02)
    lo = 1 if i0 > 0 else 0
    hi = lo + min(8, len(xs) - i0)
    b = bad[lo:hi]
    cnt += int(b.sum())
    ii, jj, kk = np.nonzero(b)
    for a, bb, c in zip(ii, jj, kk):
        pts.append((xx[lo + a], ys[bb], zs[c]))
pts = np.array(pts) if pts else np.zeros((0, 3))
print(f'unsupported downward area (>30 deg off vertical, z > floor): {cnt * h * h:.1f} mm2')
if len(pts):
    r = np.hypot(pts[:, 0], pts[:, 1])
    ang = np.degrees(np.arctan2(pts[:, 1], pts[:, 0]))
    zb = np.round(pts[:, 2], 1)
    for z in sorted(set(zb)):
        m = zb == z
        if m.sum() * h * h >= 1.0:
            print(f'   z {z:6.2f}: {m.sum() * h * h:7.1f} mm2, r {r[m].min():5.1f}..{r[m].max():5.1f}, '
                  f'angle {ang[m].min():6.0f}..{ang[m].max():6.0f}')
