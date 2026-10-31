"""Desk models (2026-10-31, Zach: "on the 3d printer lets print a mini T3 and the low winner just for fun"): a design
as one solid piece, its body (unibody's one piece, unhollowed), wheels, tail and flippers stowed, scaled down for a
print. Not a part: the rods are thickened to print at the small scale (ROD_MM), the wheels' bottoms flattened.

    python gauges/mini.py   -> gauges/out/mini/mini_T3.stl, mini_low_winner.stl (SCALE)

The low winner is the low step-and-turn run's (capability_low, best st_0.1), as grown on 2026-10-31.
"""
import os, sys, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import unibody as U, robots as RB, knobs as K

OUT = os.path.join(config.GAUGES_OUT, 'mini')
SCALE, ROD_MM, FLAT = 0.25, 3.0, 1.2      # the model's scale; its rods' least radius (mm, printed); mm flattened off the wheels (full size)


def capsule(X, Y, Z, a, b, r):
    a, b = np.asarray(a, float), np.asarray(b, float); e = b - a; L2 = max(e @ e, 1e-9)
    t = np.clip(((X - a[0]) * e[0] + (Y - a[1]) * e[1] + (Z - a[2]) * e[2]) / L2, 0.0, 1.0)
    return np.sqrt((X - a[0] - t * e[0]) ** 2 + (Y - a[1] - t * e[1]) ** 2 + (Z - a[2] - t * e[2]) ** 2) - r


def model(kq):
    """(vertices mm at SCALE, faces) of the design kq (knobs' q) as one solid desk model"""
    D = U.design_knobs(kq, packs_dz=True); sp = U.with_flippers(D['t3'], kq); rr = max(RB.LINK_R, ROD_MM / SCALE)
    E = RB.extremes(sp); lo, hi = E.min(0) - rr - 10.0, E.max(0) + rr + 10.0; lo[2] = -2.0
    a = math.ceil(max(-lo[1], hi[1]) / U.VOX) * U.VOX
    ax = [np.arange(lo[0], hi[0] + U.VOX, U.VOX), np.arange(-a, a + U.VOX / 2, U.VOX), np.arange(lo[2], hi[2] + U.VOX, U.VOX)]
    Un = U.union(D, ax)[0]; X, Y, Z = np.meshgrid(*ax, indexing='ij')
    F = np.maximum(Un, D['z_cut'] - Z)                                  # the body, unhollowed, nothing under its belly
    R, TW = sp['R'], sp['TW']; fl = sp.get('flip'); out = max([abs(p[1]) for p in fl['pivots']] if fl else [0.0])
    for x, y in sp['wheels']:
        F = np.minimum(F, np.maximum(np.hypot(X - x, Z - R) - R, np.abs(Y - y) - TW / 2))
        b = next(b for b in D['bosses'] if abs(b['x'] - x) < 1e-6)      # an axle from the pod through the wheel (the pod stops
        y1 = max(abs(y) + TW / 2, out) if fl and abs(x - max(w[0] for w in sp['wheels'])) < 1e-6 else abs(y)   # WHEEL_GAP short), out to
        F = np.minimum(F, capsule(X, Y, Z, (x, np.sign(y) * (b['y1'] - 4.0), R), (x, np.sign(y) * y1, R), rr))   # the flippers' pivots on the front axle
    lm = sp.get('limb')
    if lm:                                                              # the tail stowed, its foot
        P = RB.limb_points(lm, 0.0, lm['th_stow']); b0, b1 = P[0], P[7]
        F = np.minimum(F, capsule(X, Y, Z, b0, b1, rr)); F = np.minimum(F, capsule(X, Y, Z, b1, b1, max(lm.get('foot_r', RB.FOOT_R), rr)))
    if fl:                                                              # the flippers stowed
        d = np.array([math.cos(math.radians(fl['stow'])), 0.0, math.sin(math.radians(fl['stow']))]) * fl['L']
        for p in fl['pivots']:
            F = np.minimum(F, capsule(X, Y, Z, p, np.asarray(p) + d, rr))
    F = np.maximum(F, FLAT - Z)                                         # flats under the wheels to stand on
    from scipy.ndimage import label
    n = label(F < 0)[1]
    if n != 1:                                                          # a desk model in pieces would print loose parts
        raise RuntimeError(f'the model is {n} pieces')
    v, f = U.surface(F.astype(np.float32), ax, maxf=120000)
    v = v * SCALE; v[:, 2] -= v[:, 2].min()
    return v, f


if __name__ == '__main__':
    import pickle
    os.makedirs(OUT, exist_ok=True)
    made = pickle.load(open(os.path.join(U.OUT, 'winners', 'made.pkl'), 'rb'))
    for name, kq in (('T3', dict(K.T3)), ('low_winner', made['low step+turn']['kq'])):
        v, f = model(kq); p = os.path.join(OUT, f'mini_{name}.stl'); open(p, 'wb').write(U._stl(v, f))
        lo, hi = v.min(0), v.max(0)
        print(f'{p}: {len(f)} faces, {hi[0] - lo[0]:.0f} x {hi[1] - lo[1]:.0f} x {hi[2] - lo[2]:.0f} mm', flush=True)
