"""Zach's Fusion rev 2 (2026-09-27) against the nest through the whole tilt range: both halves, and the
lens of the real board (centred on its holes, lifted by campost_rev2.LENS_DZ because the pins place the
board). Exact: the nest's own SDF at points on each surface, as ball_nest.py and lens_clear.py do it.
Controls: the shipped halves, and the superseded photo camera at Z 52.
    python head-v2/checks/rev2_nest.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import B
from probe import load_stl
from lens_nest import nest_sweep, surface_points, tilt
from record import record
import campost_rev2 as R
H = B.H

deep = {}
for nm, r2, ship in (('ball_plus', R.BALL_PLUS, config.out('BODY_NUMBA1_camposts.stl')),
                     ('ball_minus', R.BALL_MINUS, config.out('ball_minus_revised_snap.stl'))):
    for lab, path in (('rev2', r2), ('shipped', ship)):
        near, d = nest_sweep(load_stl(path))
        deep[lab] = max(deep.get(lab, 0.0), d)
        print('%-10s %-8s nearest nest surface %.3f mm   deepest point inside the nest %.4f mm' % (nm, lab, near, d))
record('r2_nest_deepest', (deep['rev2'], deep['shipped']))

lens = {}
for lab, stl, dz in (('real board, lens %+.2f' % R.LENS_DZ, 'camera_dummy_centred.stl', R.LENS_DZ),
                     ('photo board, lens on 52 (control)', 'camera_dummy.stl', 0.0)):
    P = surface_points(load_stl(os.path.join(config.CAMERA, stl))) + [2.5, R.LENS_DY if dz else 0.0, dz]
    P = P[np.hypot(P[:, 0], P[:, 2] - H) > 24.0]
    worst = (np.inf, None)
    for t in np.arange(B.TILT_DOWN, B.TILT_UP + 0.01, 1.0):
        Q = tilt(P, t)
        d = B.fork((Q[:, 0], Q[:, 1], Q[:, 2]))
        if d.min() < worst[0]:
            worst = (d.min(), t)
    lens[lab] = worst[0]
    print('%-36s nearest nest surface %.2f mm, at tilt %+.0f' % (lab, worst[0], worst[1]))
record('r2_lens_vs_nest', tuple(lens.values()))
