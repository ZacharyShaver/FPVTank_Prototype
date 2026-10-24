"""Adversary probe: what pairs would have read for the ribbon pairs if it had not crashed on a moved ribbon.

Same overlap(), boxes, pans and threshold as pan_coil_b_check; only the ribbon is lowered with a wrapper that keeps
the pan_deg argument the check passes. Reads the design and the check; edits neither.
    python ribbon_low.py dz
"""
import sys
import numpy as np
import pan_coil_b as P
import pan_coil_b_check as C

dz = float(sys.argv[1]) if len(sys.argv) > 1 else -1.0
orig = P.ribbon
P.ribbon = lambda q, features=True, pan_deg=0.0: orig((q[0], q[1], q[2] - dz), features, pan_deg)
fns = {k: v[0] for k, v in P.PARTS.items()}
fns['ribbon'] = P.ribbon
box = {k: (np.array(v[1], float), np.array(v[2], float)) for k, v in P.PARTS.items()}
box['ribbon'] = (box['ribbon'][0] + [0, 0, dz], box['ribbon'][1] + [0, 0, dz])
for a, b, allow, note in C.PAIRS:
    if 'ribbon' not in (a, b):
        continue
    lo = np.maximum(box[a][0], box[b][0]) - 1
    hi = np.minimum(box[a][1], box[b][1]) + 1
    w = max(C.overlap(C.at_pan(a, fns, d), C.at_pan(b, fns, d), lo, hi, C.STEP) for d in C.PANS)
    print(f'ribbon dz {dz:+.1f}: {a} vs {b}: {w:.2f} mm3 ' + ('CLASH' if w > allow + 1.0 else 'pass'))
