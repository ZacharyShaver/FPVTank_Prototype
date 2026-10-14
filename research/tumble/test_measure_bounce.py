"""Checks measure_bounce.measure on synthetic drops of known restitution (6 cm, 2 px/mm, 0.4 px noise).

    python research/tumble/test_measure_bounce.py
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import measure_bounce as MB


def synth(e, fps, h_mm=60.0, px_per_mm=2.0, noise=0.4, seed=1):
    rng = np.random.default_rng(seed); g = 9810.0; v_in = np.sqrt(2 * g * h_mm); t_imp = 0.15 + np.sqrt(2 * h_mm / g); floor = 400.0
    t = np.arange(0, 1.05, 1 / fps); y = np.empty_like(t)
    for k, tt in enumerate(t):
        if tt < 0.15: y[k] = floor - h_mm * px_per_mm
        elif tt < t_imp: y[k] = floor - (h_mm - 0.5 * g * (tt - 0.15) ** 2) * px_per_mm
        else:
            v, s = e * v_in, tt - t_imp
            while v > 30 and s > 2 * v / g: s -= 2 * v / g; v *= e
            y[k] = floor - max(0.0, v * s - 0.5 * g * s ** 2) * px_per_mm if v > 30 else floor
    return t, y + rng.normal(0, noise, len(t))


def valid(r, height=60.0):
    g = (r['g_fall'] + r['g_rebound']) / 2
    return abs(r['g_fall'] - r['g_rebound']) / g < 0.25 and abs(r['drop_px'] * 9810 / g - height) <= 30


if __name__ == '__main__':
    bad = []
    for e in (0.3, 0.45, 0.55, 0.7):
        r = MB.measure(*synth(e, 240))
        if r is None or not valid(r) or abs(r['e'] - e) > 0.02: bad.append(('recover', e, r and round(r['e'], 3)))
    r = MB.measure(*synth(0.0, 240))
    if r is not None and valid(r): bad.append(('no-bounce control passed as valid', r['e']))
    r = MB.measure(*synth(0.13, 240))
    if r is not None and valid(r) and abs(r['e'] - 0.13) > 0.02: bad.append(('tiny bounce passed with a wrong value', r['e']))
    print('failures:', bad or 'none')
    sys.exit(1 if bad else 0)
