"""A small 3D frame solver for the printed legs (2026-10-28). The sim (MuJoCo) treats a design as rigid, so it gives the
loads where the legs meet the wheels, not how they split inside a braced structure. This does: the legs as round
Euler-Bernoulli beams (axial, two bendings, torsion), clamped at the body, loaded at their nodes; the stiffness method
(12 x 12 element matrices, assembled, solved once, then each load case is a back-substitution).

    python gauges/frame.py check    # a cantilever against its textbook root moment and tip deflection, and a braced
                                    # triangle against it (control: the same load, far less bending)
"""
import math
import numpy as np


def _local_k(L, E, G, r):
    """a round beam's 12 x 12 stiffness in its own axes (x along it)"""
    A = math.pi * r * r; I = math.pi * r ** 4 / 4; J = 2 * I
    k = np.zeros((12, 12))
    a, t = E * A / L, G * J / L
    k[0, 0] = k[6, 6] = a; k[0, 6] = k[6, 0] = -a
    k[3, 3] = k[9, 9] = t; k[3, 9] = k[9, 3] = -t
    b1, b2, b3, b4 = 12 * E * I / L ** 3, 6 * E * I / L ** 2, 4 * E * I / L, 2 * E * I / L
    for (v, th, s) in ((1, 5, 1.0), (2, 4, -1.0)):                      # bending in xy (v, theta z) and in xz (w, theta y)
        idx = [v, th, v + 6, th + 6]
        m = np.array([[b1, s * b2, -b1, s * b2], [s * b2, b3, -s * b2, b4], [-b1, -s * b2, b1, -s * b2], [s * b2, b4, -s * b2, b3]])
        for i in range(4):
            for j in range(4):
                k[idx[i], idx[j]] = m[i, j]
    return k


def _frame(p0, p1):
    """the 3 x 3 rotation from global to the element's axes"""
    x = (p1 - p0) / np.linalg.norm(p1 - p0); ref = np.array([0.0, 0.0, 1.0]) if abs(x[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
    y = np.cross(ref, x); y /= np.linalg.norm(y); z = np.cross(x, y)
    return np.vstack([x, y, z])


class Frame:
    """nodes (n, 3) mm, elements [(i, j, r mm)], fixed node indices; E, G in MPa (N/mm2)"""
    def __init__(self, nodes, elems, fixed, E=2500.0, G=2500.0 / 2.7):
        self.X = np.asarray(nodes, float); self.el = [(int(i), int(j), float(r)) for i, j, r in elems]; self.E, self.G = E, G
        n = len(self.X); K = np.zeros((6 * n, 6 * n)); self.T, self.kl = [], []
        for i, j, r in self.el:
            L = float(np.linalg.norm(self.X[j] - self.X[i])); R3 = _frame(self.X[i], self.X[j])
            T = np.zeros((12, 12))
            for b in range(4):
                T[3 * b:3 * b + 3, 3 * b:3 * b + 3] = R3
            kl = _local_k(L, E, G, r); kg = T.T @ kl @ T; self.T.append(T); self.kl.append(kl)
            dof = [6 * i + d for d in range(6)] + [6 * j + d for d in range(6)]
            K[np.ix_(dof, dof)] += kg
        self.free = np.array([d for d in range(6 * n) if d // 6 not in set(fixed)])
        import scipy.linalg as sl
        self.lu = sl.lu_factor(K[np.ix_(self.free, self.free)]); self.n = n

    def solve(self, loads):
        """loads: (n, 6) per node, force N and moment N mm. Returns each element's end forces in its own axes, (m, 12):
        axial, two shears, torsion, two bendings, at each end"""
        import scipy.linalg as sl
        F = np.asarray(loads, float).reshape(-1); u = np.zeros(6 * self.n); u[self.free] = sl.lu_solve(self.lu, F[self.free])
        out = []
        for (i, j, r), T, kl in zip(self.el, self.T, self.kl):
            ue = np.concatenate([u[6 * i:6 * i + 6], u[6 * j:6 * j + 6]]); out.append(kl @ (T @ ue))
        return np.array(out), u

    def stress(self, f, eta=1.0):
        """each element's worst von Mises stress, MPa, at either end: axial plus bending over the section (bending's
        modulus scaled by eta, a print's efficiency), with torsion's shear"""
        out = []
        for (i, j, r), fe in zip(self.el, f):
            A = math.pi * r * r; Sb = math.pi * r ** 3 / 4 * eta; St = math.pi * r ** 3 / 2 * eta; s = 0.0
            for e in (0, 6):
                N, T, My, Mz = fe[e], fe[e + 3], fe[e + 4], fe[e + 5]
                sig = abs(N) / A + math.hypot(My, Mz) / Sb; tau = abs(T) / St; s = max(s, math.sqrt(sig * sig + 3 * tau * tau))
            out.append(s)
        return np.array(out)


def check():
    """a 100 mm cantilever, 10 mm round, 100 N down at its tip: root moment 10 000 N mm and tip deflection F L3 / 3EI;
    then the same tip held by a second member down to a second root (a triangle): its root moments must fall by far"""
    E = 2500.0; r = 10.0; L = 100.0; F = 100.0; I = math.pi * r ** 4 / 4
    fr = Frame([[0, 0, 0], [L, 0, 0]], [(0, 1, r)], fixed=[0], E=E); loads = np.zeros((2, 6)); loads[1, 2] = -F
    f, u = fr.solve(loads); M_root = math.hypot(f[0][4], f[0][5]); d_tip = -u[6 + 2]
    ok1 = abs(M_root - F * L) / (F * L) < 1e-6; ok2 = abs(d_tip - F * L ** 3 / (3 * E * I)) / (F * L ** 3 / (3 * E * I)) < 1e-6
    print(('PASS ' if ok1 else 'FAIL ') + f'cantilever root moment {M_root:.1f} N mm (F L = {F * L:.1f})')
    print(('PASS ' if ok2 else 'FAIL ') + f'cantilever tip deflection {d_tip:.4f} mm (F L3 / 3EI = {F * L ** 3 / (3 * E * I):.4f})')
    tri = Frame([[0, 0, 0], [L, 0, 0], [0, 0, -L]], [(0, 1, r), (2, 1, r)], fixed=[0, 2], E=E); lt = np.zeros((3, 6)); lt[1, 2] = -F
    ft, _ = tri.solve(lt); s1 = fr.stress(f).max(); s2 = tri.stress(ft).max()
    print(('PASS ' if s2 < 0.2 * s1 else 'FAIL ') + f'braced: worst stress {s2:.2f} MPa against the cantilever\'s {s1:.2f} (must be under a fifth)')


if __name__ == '__main__':
    import sys
    check() if 'check' in sys.argv[1:] else print(__doc__)
