"""Assembly interference check for tree_parts.py: overlap volume between part pairs,
with the ball swept through tilt and the fork through pan. Voxel estimate, 0.4 mm grid."""
import numpy as np
import tree_parts as T

STEP = 0.4

def grid(lo, hi):
    xs = [np.arange(lo[i], hi[i], STEP) for i in range(3)]
    return np.meshgrid(*xs, indexing='ij')

def rot_y(p, deg, cz):
    """Evaluate a part rotated by +deg about the tilt axis: sample at the inverse rotation."""
    a = np.radians(-deg); x, y, z = p; zr = z - cz
    return (x * np.cos(a) + zr * np.sin(a), y, -x * np.sin(a) + zr * np.cos(a) + cz)

def rot_z(p, deg):
    a = np.radians(-deg); x, y, z = p
    return (x * np.cos(a) - y * np.sin(a), x * np.sin(a) + y * np.cos(a), z)

def overlap(fa, fb, lo, hi):
    X, Y, Z = grid(lo, hi)
    tot = 0
    for i in range(0, X.shape[0], 20):
        p = (X[i:i + 20], Y[i:i + 20], Z[i:i + 20])
        tot += np.count_nonzero((fa(p) < -0.05) & (fb(p) < -0.05))
    return tot * STEP ** 3

H = T.H
fork = lambda p: T.fork(p)
ball = lambda p: np.minimum(T.ball_plus(p), T.ball_minus(p))
rows = []
for tilt in (-60, -30, 0, 30, 60, 75):
    rows.append((f'ball @ tilt {tilt:+d} vs fork', overlap(lambda p, t=tilt: ball(rot_y(p, t, H)), fork, (-34, -40, 10), (34, 40, H + 34))))
rows.append(('fork vs roots', overlap(fork, T.roots, (-48, -48, 0), (48, 48, 12))))
for pan in (45, 90):
    rows.append((f'fork @ pan {pan} vs roots', overlap(lambda p, a=pan: T.fork(rot_z(p, a)), T.roots, (-48, -48, 0), (48, 48, 12))))
rows.append(('axle vs fork', overlap(T.axle, fork, (-11, -59, H - 11), (11, -24, H + 11))))
rows.append(('axle vs ball', overlap(T.axle, ball, (-11, -34, H - 11), (11, -20, H + 11))))
rows.append(('cap_servo vs fork', overlap(T.cap_servo, fork, (-24, 58, H - 24), (24, 64, H + 34))))
rows.append(('cap_coil vs fork', overlap(T.cap_coil, fork, (-24, -64, H - 24), (24, -55, H + 34))))
rows.append(('ball halves vs each other', overlap(T.ball_plus, T.ball_minus, (-31, -2, H - 31), (33, 2, H + 31))))
for name, v in rows:
    print(f'{name:<32} {v:8.2f} mm3' + ('' if v < 1.0 else '   <-- INTERFERENCE'))
