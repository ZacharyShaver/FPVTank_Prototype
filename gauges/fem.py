"""A voxel stress solver for one-piece printed shapes (2026-10-29). snap.py's frame solves round rods; a shape that is one
field has no rods, so this solves the shape itself: its voxels as 8-node bricks of linear elastic PLA, on the GPU
(torch, a Jacobi-preconditioned conjugate gradient, matrix-free, every load case at once).

A print is walls round infill, not solid: each voxel's stiffness is the share of it that is wall (WALL* deep from the
surface) at PLA's modulus plus the rest at INFILL_E* of it; its mass the wall plus INFILL_M* of the rest. The stress
read is the printed wall's: the voxel's strain at PLA's full modulus, von Mises, averaged over the voxel's 3 x 3 x 3
neighbours (a voxel model's stair steps make single-voxel peaks).

A landing is held by inertia (inertia relief): the load at a hub is balanced by the robot's mass, spread over the parts
bay's voxels, decelerating and turning it; three nodes fixed 3-2-1 only stop it drifting (their reactions read ~0).

    python gauges/fem.py check   # a cantilever against beam theory (stress and tip deflection); the same beam half as
                                 # deep (control: 4x the stress); a printed box beam against thin-wall theory; a free
                                 # beam held by inertia (its 3-2-1 reactions ~0)
"""
import math
import numpy as np

E_PLA, NU = 2500.0, 0.35                       # MPa (as frame.py)
WALL, INFILL_E, INFILL_M = 1.6, 0.06, 0.15     # mm: 4 walls of 0.4*; infill's share of PLA's stiffness* and of its mass (15 % gyroid)*
PLA = 1.24e-3                                  # g/mm3


def _D(E=1.0, nu=NU):
    l = E * nu / ((1 + nu) * (1 - 2 * nu)); m = E / (2 * (1 + nu))
    D = np.zeros((6, 6)); D[:3, :3] = l; D[np.arange(3), np.arange(3)] += 2 * m; D[3:, 3:] = np.eye(3) * m
    return D


_SGN = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])


def _B(xi):
    """the strain matrix (6 x 24) of a unit brick at natural point xi (each in -1..1)"""
    s = 2 * _SGN - 1; B = np.zeros((6, 24))
    for a in range(8):
        f = [(1 + s[a, k] * xi[k]) for k in range(3)]
        d = np.array([s[a, 0] * f[1] * f[2], s[a, 1] * f[0] * f[2], s[a, 2] * f[0] * f[1]]) / 8 * 2   # d/dx for edge 1
        bx, by, bz = d; c = 3 * a
        B[0, c], B[1, c + 1], B[2, c + 2] = bx, by, bz
        B[3, c], B[3, c + 1] = by, bx
        B[4, c + 1], B[4, c + 2] = bz, by
        B[5, c], B[5, c + 2] = bz, bx
    return B


def element():
    """the unit brick's stiffness (E 1, edge 1: scale by E h) and its strain matrix at the centre (scale by 1 / h)"""
    D = _D(); g = 1 / math.sqrt(3); K = np.zeros((24, 24))
    for xi in ((a, b, c) for a in (-g, g) for b in (-g, g) for c in (-g, g)):
        B = _B(xi); K += B.T @ D @ B / 8
    return K, _B((0.0, 0.0, 0.0))


class Mesh:
    """solid voxels (a bool grid, edge h mm, the first voxel's centre at origin) with each one's stiffness share"""
    def __init__(self, solid, share, h, origin, device=None):
        import torch
        self.torch = torch; self.dev = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.h = float(h); self.origin = np.asarray(origin, float); self.shape = solid.shape
        self.ijk = np.argwhere(solid); self.share = np.asarray(share, float)[solid]
        ny, nz = solid.shape[1] + 1, solid.shape[2] + 1
        lin = ((self.ijk[:, None, 0] + _SGN[None, :, 0]) * ny + (self.ijk[:, None, 1] + _SGN[None, :, 1])) * nz + (self.ijk[:, None, 2] + _SGN[None, :, 2])
        self.node_lin, inv = np.unique(lin, return_inverse=True); self.enode = inv.reshape(-1, 8)
        n = self.node_lin; k = n % nz; j = (n // nz) % ny; i = n // (nz * ny)
        self.X = self.origin - self.h / 2 + self.h * np.c_[i, j, k]          # node coordinates, mm
        self.nn = len(n); self.ne = len(self.ijk)
        K, B0 = element(); self.B0 = B0 / self.h
        T = lambda a: torch.as_tensor(a, dtype=torch.float64, device=self.dev); self.T = T
        import scipy.sparse as sps, warnings                               # assembled once on the CPU, multiplied on the GPU
        warnings.filterwarnings('ignore', message='Sparse invariant')
        self.edof_np = (3 * self.enode[:, :, None] + np.arange(3)).reshape(-1, 24); E = E_PLA * self.share
        rows = np.repeat(self.edof_np, 24, axis=1).ravel(); cols = np.tile(self.edof_np, (1, 24)).ravel()
        vals = (E[:, None] * (K * self.h).ravel()[None, :]).ravel()
        Ks = sps.csr_matrix((vals, (rows.astype(np.int32), cols.astype(np.int32))), shape=(3 * self.nn, 3 * self.nn)); Ks.sum_duplicates()
        self.K = torch.sparse_csr_tensor(torch.as_tensor(Ks.indptr.astype(np.int32)), torch.as_tensor(Ks.indices.astype(np.int32)),
                                         torch.as_tensor(Ks.data), size=Ks.shape).to(self.dev)
        self.diag = T(Ks.diagonal()); self.Ks = Ks

    def centres(self):
        return self.origin + self.h * self.ijk

    def Kmul(self, u):
        """K u (double: single precision's product loses a stiff-and-floppy shape's solution)"""
        return self.K @ u

    def solve(self, F, fixed, tol=1e-5, maxit=20000):
        """F: (nn, 3, nc) nodal forces N; fixed: dof indices held at zero. Returns u (nn, 3, nc) mm, iterations"""
        torch = self.torch; nc = F.shape[2]; b = self.T(F.reshape(3 * self.nn, nc)).clone()
        free = torch.ones(3 * self.nn, 1, dtype=torch.float64, device=self.dev); free[torch.as_tensor(np.asarray(fixed, int), device=self.dev)] = 0.0
        b *= free; Minv = free / self.diag[:, None].clamp_min(1e-12)
        x = torch.zeros_like(b); r = b.clone(); z = Minv * r; p = z.clone(); rz = (r * z).sum(0); bn = b.norm(dim=0).clamp_min(1e-30)
        for it in range(maxit):
            Ap = self.Kmul(p) * free; a = rz / (p * Ap).sum(0).clamp_min(1e-300)
            x += a * p; r -= a * Ap
            if it % 20 == 0 and (r.norm(dim=0) / bn).max() < tol:
                break
            z = Minv * r; rz2 = (r * z).sum(0); p = z + (rz2 / rz) * p; rz = rz2
        self.resid = float((r.norm(dim=0) / bn).max())
        return x.reshape(self.nn, 3, nc).cpu().numpy(), it

    def solve_mg(self, F, fixed, tol=1e-5, maxit=400, omega=0.6, nu=2, coarse=6000):
        # omega: the damping, of 2 / the largest eigenvalue of D^-1 A (so 1.2 / lam)
        """solve() preconditioned by geometric multigrid (2026-10-29: Jacobi alone took 4,000 iterations on a robot):
        each coarser level's nodes every other node, trilinear prolongation, Galerkin operators, damped Jacobi smoothing,
        the coarsest solved exactly (Cholesky)"""
        import scipy.sparse as sps
        torch = self.torch; free = np.ones(3 * self.nn); free[np.asarray(fixed, int)] = 0.0; Dm = sps.diags(free)
        A = (Dm @ self.Ks @ Dm + sps.diags(1.0 - free)).tocsr()
        ny, nz = self.shape[1] + 1, self.shape[2] + 1; n = self.node_lin; ijk = np.c_[n // (nz * ny), (n // nz) % ny, n % nz]
        G = lambda M: torch.sparse_csr_tensor(torch.as_tensor(M.indptr.astype(np.int64)), torch.as_tensor(M.indices.astype(np.int64)),
                                              torch.as_tensor(M.data), size=M.shape).to(self.dev)
        lev = []; first = True
        while A.shape[0] > coarse and len(lev) < 8:
            P, ijk = _prolong(ijk); P3 = sps.kron(P, sps.eye(3)).tocsr()
            if first:
                P3 = (Dm @ P3).tocsr(); first = False
            Ag, Di = G(A), self.T(1.0 / A.diagonal())[:, None]; v = torch.rand(A.shape[0], 1, dtype=torch.float64, device=self.dev)
            for _ in range(20):                                                 # the smoother's damping from D^-1 A's largest eigenvalue
                v = Di * (Ag @ v); lam = float(v.norm()); v /= lam
            lev.append((Ag, G(P3), G(P3.T.tocsr()), Di * (omega / (0.5 * lam)))); A = (P3.T @ A @ P3).tocsr()
            dz = A.diagonal() <= 0.0                                            # a coarse dof fed only by held ones: an empty row,
            if dz.any():                                                        # 1/0 in its smoother and a NaN Cholesky (2026-10-31: the
                A = (A + sps.diags(dz.astype(float))).tocsr()                  # low winner's every landing NaN); its column of P is zero,
                                                                                # so the 1 here never reaches the fine solve
        Lc = torch.linalg.cholesky(self.T(A.toarray()))
        def V(l, r):
            if l == len(lev):
                return torch.cholesky_solve(r, Lc)
            Al, P, PT, Di = lev[l]; x = Di * r
            for _ in range(nu - 1):
                x = x + Di * (r - Al @ x)
            x = x + P @ V(l + 1, PT @ (r - Al @ x))
            for _ in range(nu):
                x = x + Di * (r - Al @ x)
            return x
        A0 = lev[0][0] if lev else G(A); nc = F.shape[2]; fr = self.T(free)[:, None]
        b = self.T(F.reshape(3 * self.nn, nc)).clone() * fr; bn = b.norm(dim=0).clamp_min(1e-30)
        x = torch.zeros_like(b); r = b.clone(); z = V(0, r); p = z.clone(); rz = (r * z).sum(0)
        for it in range(maxit):
            Ap = A0 @ p; a = rz / (p * Ap).sum(0).clamp_min(1e-300); x += a * p; r -= a * Ap
            if (r.norm(dim=0) / bn).max() < tol:
                break
            z = V(0, r); rz2 = (r * z).sum(0); p = z + (rz2 / rz) * p; rz = rz2
        self.resid = float((r.norm(dim=0) / bn).max()); self.levels = len(lev) + 1
        return x.reshape(self.nn, 3, nc).cpu().numpy(), it

    def stress(self, u):
        """each voxel's von Mises (MPa) of its strain at PLA's full modulus, per load case: (ne, nc)"""
        ue = u.reshape(3 * self.nn, -1)[self.edof_np]                      # (ne, 24, nc)
        eps = np.einsum('ij,ejc->eic', self.B0, ue); s = np.einsum('ij,ejc->eic', _D(E_PLA), eps)
        sx, sy, sz, txy, tyz, tzx = s.transpose(1, 0, 2)
        return np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy ** 2 + tyz ** 2 + tzx ** 2))

    def smooth(self, s):
        """each voxel's value averaged over its solid 3 x 3 x 3 neighbours"""
        from scipy.ndimage import uniform_filter
        out = np.empty_like(s); G = np.zeros(self.shape); W = np.zeros(self.shape); W[tuple(self.ijk.T)] = 1.0
        w = uniform_filter(W, 3, mode='constant')
        for c in range(s.shape[1]):
            G[tuple(self.ijk.T)] = s[:, c]; out[:, c] = (uniform_filter(G, 3, mode='constant') / np.maximum(w, 1e-9))[tuple(self.ijk.T)]
        return out


def _prolong(ijk):
    """trilinear prolongation from every other node (scalar, fine x coarse) and the coarse nodes' grid coordinates"""
    import scipy.sparse as sps
    lo, hi = ijk // 2, (ijk + 1) // 2; odd = ijk % 2 == 1; rows, cols, w = [], [], []
    for c in range(8):
        pick = [(c >> a) & 1 for a in range(3)]
        cc = np.where(np.array(pick)[None, :] == 1, hi, lo)
        ww = np.prod(np.where(odd, 0.5, np.where(np.array(pick)[None, :] == 1, 0.0, 1.0)), axis=1)
        keep = ww > 0; rows.append(np.where(keep)[0]); cols.append(cc[keep]); w.append(ww[keep])
    C = np.vstack(cols); key = (C[:, 0] * (C[:, 1].max() + 1) + C[:, 1]) * (C[:, 2].max() + 1) + C[:, 2]

    uk, idx, inv = np.unique(key, return_index=True, return_inverse=True)
    P = sps.csr_matrix((np.concatenate(w), (np.concatenate(rows), inv.ravel())), shape=(len(ijk), len(uk)))
    return P, C[idx]


def printed(F, h):
    """a field sampled at voxel centres (mm, negative inside) -> (solid, stiffness share, mass share): each voxel's
    inside part split into wall (depth under WALL) and infill"""
    d = -np.asarray(F, float); top = d + h / 2; bot = np.maximum(d - h / 2, 0.0)
    inside = np.clip(top - bot, 0.0, h); wall = np.clip(np.minimum(top, WALL) - bot, 0.0, None); wall = np.minimum(wall, inside)
    solid = inside >= 0.1 * h
    return solid, (wall + INFILL_E * (inside - wall)) / h, (wall + INFILL_M * (inside - wall)) / h


def inertia_relief(mesh, loads, mass_nodes, M):
    """loads (nn, 3, nc) balanced by the mass M (g... only its share matters) spread evenly over mass_nodes, decelerating
    and turning as a rigid body would; returns the balanced loads and 3-2-1 fixed dofs among the mass nodes"""
    X = mesh.X[mass_nodes]; c = X.mean(0); r = X - c; m = 1.0 / len(mass_nodes)
    I = m * ((r * r).sum() * np.eye(3) - r.T @ r)
    out = loads.copy()
    for k in range(loads.shape[2]):
        f = loads[:, :, k]; Ft = f.sum(0); Mt = np.cross(mesh.X - c, f).sum(0)
        a = Ft / 1.0; al = np.linalg.solve(I, Mt)
        out[mass_nodes, :, k] -= m * (a[None, :] + np.cross(al[None, :], r))
    A = mass_nodes[np.argmin(np.linalg.norm(r, axis=1))]                          # 3-2-1 near the middle and far along x and y
    Bn = mass_nodes[np.argmax(r[:, 0] - 0.2 * np.abs(r[:, 1]))]; Cn = mass_nodes[np.argmax(r[:, 1] - 0.2 * np.abs(r[:, 0]))]
    fixed = [3 * A, 3 * A + 1, 3 * A + 2, 3 * Bn + 1, 3 * Bn + 2, 3 * Cn + 2]
    return out, fixed


def check():
    h = 2.0; L, b, d, F = 200.0, 20.0, 20.0, 100.0
    def beam(dd, wall=None, b=b):
        nx, ny, nz = int(L / h), int(b / h), int(dd / h); solid = np.ones((nx, ny, nz), bool)
        if wall is None:
            share = np.ones(solid.shape)
        else:                                                              # a printed box: depth from the nearest face
            ax = [(np.arange(n) + 0.5) * h for n in (nx, ny, nz)]; X, Y, Z = np.meshgrid(*ax, indexing='ij')
            dep = np.minimum.reduce([Y, b - Y, Z, dd - Z]); _, share, _ = printed(-dep, h)
        m = Mesh(solid, share, h, (h / 2, h / 2, h / 2))
        root = np.where(m.X[:, 0] < 1e-6)[0]; tip = np.where(np.abs(m.X[:, 0] - L) < 1e-6)[0]
        loads = np.zeros((m.nn, 3, 1)); loads[tip, 2, 0] = -F / len(tip)
        u, it = m.solve_mg(loads, np.concatenate([3 * root, 3 * root + 1, 3 * root + 2]))
        s = m.stress(u)[:, 0]; c = m.centres(); band = np.abs(c[:, 0] - L / 2) < h            # mid-span, away from both ends
        return m, u, s, c, band, tip, it
    m, u, s, c, band, tip, it = beam(d); I = b * d ** 3 / 12
    s_th = F * (L / 2) * (d / 2 - h / 2) / I                                # at the outer voxels' centres
    s_fe = s[band & (np.abs(c[:, 2] - (d - h / 2)) < 1e-6)].mean(); defl = -u[tip, 2, 0].mean(); defl_th = F * L ** 3 / (3 * E_PLA * I)
    print(('PASS ' if abs(s_fe / s_th - 1) < 0.08 else 'FAIL ') + f'cantilever mid-span stress {s_fe:.2f} MPa (beam theory {s_th:.2f}), {it} iterations')
    print(('PASS ' if abs(defl / defl_th - 1) < 0.08 else 'FAIL ') + f'tip deflection {defl:.3f} mm (F L3 / 3EI {defl_th:.3f}; shear adds a little)')
    m2, u2, s2, c2, band2, *_ = beam(d / 2); s_half = s2[band2].max() / s[band].max()
    th_half = 8 * (d / 4 - h / 2) / (d / 2 - h / 2)                        # 4x at the surface; at the outer voxels' centres
    print(('PASS ' if abs(s_half / th_half - 1) < 0.08 else 'FAIL ') + f'control: half as deep, {s_half:.2f}x the stress (theory {th_half:.2f} at the voxel centres, 4 at the surface)')
    db = 40.0; mb = beam(db, wall=True, b=db)                              # a 40 x 40 printed box beam
    di = db - 2 * WALL; Ib = (db ** 4 - di ** 4) / 12 + INFILL_E * di ** 4 / 12
    defl_b = -mb[1][mb[5], 2, 0].mean(); defl_bt = F * L ** 3 / (3 * E_PLA * Ib)
    print(('PASS ' if abs(defl_b / defl_bt - 1) < 0.15 else 'FAIL ') + f'printed 40 mm box beam ({WALL} mm walls, infill at {INFILL_E} of PLA): '
          f'tip {defl_b:.3f} mm against thin-wall theory {defl_bt:.3f} (2 mm voxels)')
    # a free beam, loaded at its tip, held by inertia: the 3-2-1 reactions must vanish
    m, *_ = beam(d); tip = np.where(np.abs(m.X[:, 0] - L) < 1e-6)[0]; loads = np.zeros((m.nn, 3, 1)); loads[tip, 2, 0] = -F / len(tip)
    mass = np.where(m.X[:, 0] < L / 2)[0]; bal, fixed = inertia_relief(m, loads, mass, 1.0)
    u, it = m.solve_mg(bal, fixed); fu = m.Kmul(m.T(u.reshape(-1, 1))).cpu().numpy()[:, 0]
    react = np.abs(fu[fixed] - bal.reshape(-1)[fixed]).max()
    print(('PASS ' if react < 0.01 * F else 'FAIL ') + f'held by inertia: the 3-2-1 reactions {react:.4f} N (load {F:.0f} N), {it} iterations')


if __name__ == '__main__':
    import sys
    check() if 'check' in sys.argv[1:] else print(__doc__)
