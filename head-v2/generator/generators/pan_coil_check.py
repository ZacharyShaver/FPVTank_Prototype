"""Interference check for the pan coil. Voxel estimate, 0.35 mm grid.

Three questions:
  1. does the rotating drum ever touch the fixed servo island, over the full pan range?
  2. does any of the drum stick outside the cavity the body gives it?
  3. does the ribbon loop stay clear of the drum, the anchor boss and the well wall?
"""
import numpy as np
import pan_coil as P

STEP = 0.35

def overlap(fa, fb, lo, hi):
    xs = [np.arange(lo[i], hi[i], STEP) for i in range(3)]
    X, Y, Z = np.meshgrid(*xs, indexing='ij')
    tot = 0
    for i in range(0, X.shape[0], 16):
        p = (X[i:i + 16], Y[i:i + 16], Z[i:i + 16])
        tot += np.count_nonzero((fa(p) < -0.05) & (fb(p) < -0.05))
    return tot * STEP ** 3

def rot_z(p, deg):
    a = np.radians(-deg); x, y, z = p
    return (x * np.cos(a) - y * np.sin(a), x * np.sin(a) + y * np.cos(a), z)

LO = (-P.FLANGE_R - 2, -P.FLANGE_R - 2, P.CAN_Z0 - 1)
HI = (P.FLANGE_R + 2, P.FLANGE_R + 2, P.BARREL_Z + 2)

rows = []
for pan in (-90, -45, 0, 45, 90):
    rows.append((f'drum @ pan {pan:+d} vs servo island',
                 overlap(lambda p, q=pan: P.drum(rot_z(p, q)), P.island,
                         (-24, -16, P.CAN_Z0 - 1), (16, 16, P.SERVO_PROUD + P.HORN_D + 2))))

# the drum must live entirely inside the cavity the cut tool carves
rows.append(('drum outside the body cavity',
             overlap(P.drum, lambda p: -P.well_cut(p), LO, (P.FLANGE_R + 2, P.FLANGE_R + 2, P.FLANGE_Z))))

# the ribbon, as a swept slab on its centreline, against the hardware it runs between
def loop_solid(pan):
    pts = P.loop_points(pan, 200)
    half_t = P.RIBBON_T / 2 + 0.05          # the ribbon itself; RUN_CLR is already in R_IN/R_OUT
    def f(p):
        d = None
        for c in pts:
            r = np.hypot(p[0] - c[0], p[1] - c[1]) - half_t
            di = np.maximum(r, np.abs(p[2] - (P.BAND_Z0 + P.BAND_Z1) / 2) - P.RIBBON_W / 2)
            d = di if d is None else np.minimum(d, di)
        return d
    return f

for pan in (-90, 0, 90):
    rows.append((f'ribbon loop @ pan {pan:+d} vs drum',
                 overlap(loop_solid(pan), lambda p, q=pan: P.drum(rot_z(p, q)),
                         (-32, -32, P.CAN_Z0 - 1), (32, 32, P.FLANGE_Z))))

for name, v in rows:
    print(f'{name:<36} {v:8.2f} mm3' + ('' if v < 1.0 else '   <-- INTERFERENCE'))

# clearances that matter, stated rather than sampled
print()
print(f'drum bore r {P.DRUM_IR}  vs servo far corner {P.CORNER_R:.2f}   clearance {P.DRUM_IR - P.CORNER_R:.2f} mm')
print(f'anchor boss r {P.BOSS_R}  vs outer ribbon layer r {P.R_OUT:.2f}   clearance {P.R_OUT - P.BOSS_R:.2f} mm')
wrap_in = [P.U0 + P.DU_DPAN * q - (P.A_IN0 + q) for q in (-90, 90)]
print(f'U to drum anchor: {min(wrap_in):.1f}..{max(wrap_in):.1f} deg  (boss is +-17 deg wide)')
