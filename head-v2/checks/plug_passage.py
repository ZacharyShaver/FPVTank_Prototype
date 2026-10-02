"""Can the tilt servo's plug get from the bowl down into the pan coil's chamber? (2026-09-27)

A rigid box (the plug, L x W x T, T including the 0.2 ribbon it shares the way with) is slid AND
turned through the open space the cradle and the drum leave, with the ball out, the way it is threaded
at assembly. It's a 2D configuration-space search in the XZ plane (centre x, z and angle, 0.1 mm and
3 deg steps). The plug's width spans Y +-W/2, so a spot counts as open only if it is open at every Y the
plug covers. Material is the generator's own SDFs (B.fork, the drum, the base), not meshes.

Three legs are reported: bowl -> drum bore (the cradle), bore -> coil chamber (the drum), and the whole
way. The first row is the ribbon itself, 16 wide: a 1 x 0.4 sliver of it has to get from the bowl
into the groove too. Control: the cradle as printed before the chute (a 3.0 groove, no chute) must read
blocked where the new one passes. It also blocks the ribbon: its groove met the track only in a hairline
near Y 0 (found 2026-09-27, by this check). A 1 x 1 block must pass the new cradle, or the search
itself is broken.

    python head-v2/checks/plug_passage.py                 # the plug sizes below
    python head-v2/checks/plug_passage.py 14.5 7.6 2.9    # one plug: L W T (T without the ribbon)
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from scipy import ndimage, signal
import tree_parts_b as B, pan_coil_b as P

RIBBON = 0.2                    # pan_coil_b.RIBBON_T, assumed until calipered
ST, DANG = 0.1, 3.0
XS = np.arange(-30, 22 + ST / 2, ST); ZS = np.arange(-22, 42 + ST / 2, ST)
X, Z = np.meshgrid(XS, ZS, indexing='ij')
# Plug sizes to report. Zach calipered the connector 14 long x 8 wide (2026-09-27); its thickness is not
# measured yet. Through the drum as printed, 2.8 passes and 3.0 does not.
RIBBON_ROW, TINY = (1.0, 16.0, 0.2), (1.0, 1.0, 0.8)
PLUGS = [(14.0, 8.0, 2.8), (14.0, 8.0, 3.0), (16.0, 8.0, 2.4)]


def open_mask(W):
    ok = np.ones(X.shape, bool)
    for y in np.linspace(-W / 2, W / 2, 7):
        p = (X, np.full_like(X, y), Z)
        ok &= (B.fork(p) > 0) & (P.drum(p) > 0) & (P.base(p) > 0)
    return ok


def legs(ok, L, T):
    obst = (~ok).astype(np.float32)
    fs = np.zeros(ok.shape + (int(180 / DANG),), bool)
    for k, a in enumerate(np.radians(np.arange(0, 180, DANG))):
        u = np.array([np.cos(a), np.sin(a)])
        r = int(np.ceil(np.hypot(L, T) / 2 / ST)) + 1
        g = np.arange(-r, r + 1) * ST
        GX, GZ = np.meshgrid(g, g, indexing='ij')
        ker = (np.abs(GX * u[0] + GZ * u[1]) <= L / 2) & (np.abs(-GX * u[1] + GZ * u[0]) <= T / 2)
        fs[..., k] = signal.fftconvolve(obst, ker.astype(np.float32), mode='same') < 0.5
    lab, n = ndimage.label(fs, structure=ndimage.generate_binary_structure(3, 1))
    parent = list(range(n + 1))                     # 0 deg and 180 deg are the same pose
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    a, b = lab[..., 0], lab[..., -1]
    for i, j in set(zip(a[(a > 0) & (b > 0)].tolist(), b[(a > 0) & (b > 0)].tolist())):
        parent[root(i)] = root(j)
    def comps(region):
        return {root(i) for i in np.unique(lab[fs & region[..., None]]) if i}
    bowl = comps(Z > 30)
    bore = comps((Z > -2) & (Z < 8) & (np.abs(X) < 8))
    chamber = comps((Z < -8) & (X > 13) & (X < 17))
    return bool(bowl & bore), bool(bore & chamber), bool(bowl & chamber)


def run(plugs):
    res = {}
    for W in sorted({w for _, w, _ in plugs}):
        ok = open_mask(W)
        for L, w, T in plugs:
            if w == W:
                res[(L, W, T)] = legs(ok, L, T + RIBBON)
    return res


if __name__ == '__main__':
    plugs = [tuple(map(float, sys.argv[1:4]))] if len(sys.argv) >= 4 else PLUGS
    plugs = [RIBBON_ROW, TINY] + plugs
    new = run(plugs)
    chute, t = B.chute, B.CHUTE_T                   # control: the cradle before the chute
    B.chute = lambda p, *a, **k: np.full_like(p[0], 1e3); B.CHUTE_T = B.TROUGH_T
    old = run(plugs)
    B.chute, B.CHUTE_T = chute, t
    yn = lambda v: 'passes ' if v else 'BLOCKED'
    print('plug L x W x T (+%.1f ribbon)   bowl->bore (cradle)   bore->chamber (drum)   whole way   | control: old cradle, bowl->bore' % RIBBON)
    for k in plugs:
        c, d, w = new[k]
        print('  %4.1f x %4.1f x %3.1f           %s               %s                %s     | %s'
              % (*k, yn(c), yn(d) if k != RIBBON_ROW else 'n/a    ', yn(w) if k != RIBBON_ROW else 'n/a    ',
                 yn(old[k][0])))
    print('  (the ribbon folds on edge at the drum\'s side slot, so only its cradle leg applies)')
    bad = not all(new[TINY]) or not new[RIBBON_ROW][0]
    bad |= any(old[k][0] for k in plugs if k[2] >= 2.4)
    bad |= not all(new[k][0] for k in plugs)
    print('tiny block and ribbon pass the new cradle, control blocks the plugs, every plug through the new cradle: %s'
          % ('NO' if bad else 'yes'))
    sys.exit(1 if bad else 0)
