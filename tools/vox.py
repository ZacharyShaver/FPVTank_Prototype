"""Scanline voxelizer: for each (y,z) column, cast a ray along +X, collect every triangle
crossing, and fill between crossings by parity. Robust enough for a diff; a non-manifold mesh
gets a second pass along Y and the two are AND-ed so a stray crossing cannot flood a column."""
import numpy as np, struct

def load_stl(path):
    data = open(path, 'rb').read()
    n = struct.unpack('<I', data[80:84])[0]
    if 84 + n * 50 == len(data):
        arr = np.frombuffer(data[84:84 + n * 50],
                            dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))
        return arr['v'].astype(np.float64)
    tris, cur = [], []
    for line in data.decode(errors='ignore').splitlines():
        p = line.split()
        if p and p[0] == 'vertex':
            cur.append([float(x) for x in p[1:4]])
            if len(cur) == 3:
                tris.append(cur); cur = []
    return np.array(tris)

def load_obj(path):
    V, F = [], []
    for line in open(path):
        if line.startswith('v '):
            V.append([float(x) for x in line.split()[1:4]])
        elif line.startswith('f '):
            F.append([int(t.split('/')[0]) - 1 for t in line.split()[1:4]])
    V = np.array(V); F = np.array(F)
    return V[F]

def _scan(T, axis, grid):
    """Fill along `axis`. grid = (xs, ys, zs). Returns bool array indexed [i,j,k]."""
    xs, ys, zs = grid
    ax = [xs, ys, zs]
    a, b = [d for d in range(3) if d != axis]          # the two in-plane axes
    A, Bv = ax[a], ax[b]
    L = ax[axis]
    shape = (len(xs), len(ys), len(zs))
    out = np.zeros(shape, bool)
    hits = {}
    P0, P1, P2 = T[:, 0], T[:, 1], T[:, 2]
    for t in range(len(T)):
        p0, p1, p2 = P0[t], P1[t], P2[t]
        amin, amax = min(p0[a], p1[a], p2[a]), max(p0[a], p1[a], p2[a])
        bmin, bmax = min(p0[b], p1[b], p2[b]), max(p0[b], p1[b], p2[b])
        ia = np.nonzero((A >= amin) & (A <= amax))[0]
        ib = np.nonzero((Bv >= bmin) & (Bv <= bmax))[0]
        if not len(ia) or not len(ib):
            continue
        GA, GB = np.meshgrid(A[ia], Bv[ib], indexing='ij')
        # barycentric in the (a,b) plane
        v0a, v0b = p1[a] - p0[a], p1[b] - p0[b]
        v1a, v1b = p2[a] - p0[a], p2[b] - p0[b]
        den = v0a * v1b - v1a * v0b
        if abs(den) < 1e-12:
            continue
        wa, wb = GA - p0[a], GB - p0[b]
        u = (wa * v1b - v1a * wb) / den
        v = (v0a * wb - wa * v0b) / den
        m = (u >= 0) & (v >= 0) & (u + v <= 1)
        if not m.any():
            continue
        l = p0[axis] + u * (p1[axis] - p0[axis]) + v * (p2[axis] - p0[axis])
        for (ii, jj), val in zip(np.argwhere(m), l[m]):
            hits.setdefault((ia[ii], ib[jj]), []).append(val)
    for (i, j), vals in hits.items():
        vals = np.sort(np.array(vals))
        # merge near-duplicate crossings (shared edges hit twice)
        keep = [vals[0]]
        for x in vals[1:]:
            if x - keep[-1] > 1e-6:
                keep.append(x)
        for k in range(0, len(keep) - 1, 2):
            sel = (L >= keep[k]) & (L <= keep[k + 1])
            idx = [slice(None)] * 3
            idx[a], idx[b], idx[axis] = i, j, sel
            out[tuple(idx)] = True
    return out

def voxelize(T, grid, robust=False):
    vx = _scan(T, 0, grid)
    if not robust:
        return vx
    vy = _scan(T, 1, grid)
    return vx & vy, vx, vy
