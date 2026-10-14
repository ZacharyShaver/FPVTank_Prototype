"""measure_ball.fit_track on synthetic drops of known restitution: held still, released, bouncing at 240 fps with
0.4 px of noise (the real tracks' fit residual is 0.2-1.5 px).

    python research/tumble/test_measure_ball.py
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from measure_ball import fit_track

G = 36000.0      # px/s^2: 9.81 m/s^2 at 0.27 mm/px, as in IMG_1642


def synthetic(drop_px, es, floor=710.0, fps=240.0, noise=0.4, seed=0):
    t = np.arange(int(1.2 * fps)) / fps; tr = 30 / fps                     # held for 30 frames
    imp = [tr + np.sqrt(2 * drop_px / G)]; v = G * (imp[0] - tr); vs = [v]
    for e in es:
        v *= e; imp.append(imp[-1] + 2 * v / G); vs.append(v)
    y = np.full_like(t, floor)
    m = t < tr; y[m] = floor - drop_px
    m = (t >= tr) & (t < imp[0]); y[m] = floor - drop_px + G / 2 * (t[m] - tr) ** 2
    for i in range(len(es)):
        m = (t >= imp[i]) & (t < imp[i + 1]); y[m] = floor - G / 2 * (t[m] - imp[i]) * (imp[i + 1] - t[m])
    return t, y + np.random.default_rng(seed).normal(0, noise, len(t)), vs


if __name__ == '__main__':
    bad = 0
    for drop_px, es in ((370, (0.60, 0.75, 0.85)), (330, (0.40, 0.70)), (300, (0.24, 0.5)), (250, (0.45, 0.8, 0.8))):
        for seed in range(3):
            t, y, vs = synthetic(drop_px, es, seed=seed); f = fit_track(t, y)
            err = [abs(a - b) for a, b in zip(f['e'], es)]
            ok = len(f['e']) >= 1 and err[0] < 0.01 and abs(f['v1_px'] / vs[0] - 1) < 0.01 and abs(f['g_px'] / G - 1) < 0.02
            bad += not ok
            print(f"drop {drop_px} px, e {es}: fitted {[round(e, 3) for e in f['e']]}, v1 {f['v1_px'] / vs[0]:.4f} of true, g {f['g_px'] / G:.4f}"
                  + ('' if ok else '  FAIL'))
    print('all pass' if not bad else f'{bad} FAILED'); sys.exit(bool(bad))
