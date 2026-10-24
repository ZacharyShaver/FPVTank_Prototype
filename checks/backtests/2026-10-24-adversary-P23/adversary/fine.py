"""Adversary probe: fine-grid shared volume and least gap for one pair under one mutant (pan 0).
    python fine.py my_mutants.py A04 shelf_ring well [x0 y0 z0 x1 y1 z1] [step]
Reads the design and the mutant file; edits nothing.
"""
import sys, importlib.util
import numpy as np
import pan_coil_b as P

mf, mid, a, b = sys.argv[1:5]
if mid != 'none':
    spec = importlib.util.spec_from_file_location('mf', mf)
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    M.MUTANTS[mid][0](P)
fa, fb = P.PARTS[a][0], P.PARTS[b][0]
if len(sys.argv) >= 11:
    lo = np.array([float(v) for v in sys.argv[5:8]]); hi = np.array([float(v) for v in sys.argv[8:11]])
else:
    lo = np.maximum(P.PARTS[a][1], P.PARTS[b][1]); hi = np.minimum(P.PARTS[a][2], P.PARTS[b][2])
h = float(sys.argv[11]) if len(sys.argv) >= 12 else 0.05
xs, ys, zs = (np.arange(lo[i], hi[i] + h, h) for i in range(3))
Y, Z = np.meshgrid(ys, zs, indexing='ij')
n, gap = 0, np.inf
for i0 in range(0, len(xs), 4):
    xx = xs[i0:i0 + 4]
    p = (xx[:, None, None] + 0 * Y[None], np.broadcast_to(Y, (len(xx),) + Y.shape), np.broadcast_to(Z, (len(xx),) + Z.shape))
    da, db = fa(p), fb(p)
    n += int(np.count_nonzero((da < 0) & (db < 0)))
    gap = min(gap, float(np.min(np.maximum(da, db))))
print(f'{mid}: {a} vs {b}: shared {n * h ** 3:.3f} mm3 (step {h}); min of max(sdf) {gap:+.3f} mm '
      f'({"overlap depth" if gap < 0 else "least gap"} ~ {abs(gap) * 2:.3f})')
