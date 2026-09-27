"""Interference check for variant C, the hood head. Voxel estimate on a 0.5 mm grid.

Everything that moves is swept: the camera and the yoke rotate about the tilt axis, the crank and
the rod follow the four-bar, and the whole head pans on the roots. Structural rows use the hood
with NO window cut, which is the conservative solid.

The last block is the one this variant lives or dies on -- it checks the camera can actually SEE
out at every tilt, by looking for any hood or yoke material inside the view cone.
"""
import numpy as np
import tree_parts as A
import tree_hood as C

STEP = 0.5
H = C.H
TILTS = (-35, -20, 0, 20, 40)


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


hood_s = lambda p: C.hood(p, True)
spine_s = lambda p: C.spine(p, True)

SHELL = ((-34, -32, 11), (27, 32, H + 26))
LOW = ((-32, -32, 11), (26, 32, H + 4))
NOSE = ((-4, -32, 13), (27, 32, H + 26))

rows = []
for t in TILTS:
    cam = lambda p, t=t: C.camera(C.rot_y(p, t))
    yok = lambda p, t=t: C.yoke(C.rot_y(p, t), False)
    rod = lambda p, t=t: C.rod_at(p, t)
    crk = lambda p, t=t: C.crank_at(p, t)
    rows += [(f'camera @ tilt {t:+d} vs hood', overlap(cam, hood_s, *SHELL)),
             (f'camera @ tilt {t:+d} vs spine', overlap(cam, spine_s, *SHELL)),
             (f'camera @ tilt {t:+d} vs servo', overlap(cam, C.servo, *LOW)),
             (f'camera @ tilt {t:+d} vs rod', overlap(cam, rod, *SHELL)),
             (f'yoke   @ tilt {t:+d} vs hood', overlap(yok, hood_s, *SHELL)),
             (f'yoke   @ tilt {t:+d} vs spine', overlap(yok, spine_s, *SHELL)),
             (f'rod    @ tilt {t:+d} vs spine', overlap(rod, spine_s, *LOW)),
             (f'crank  @ tilt {t:+d} vs spine', overlap(crk, spine_s, *LOW)),
             (f'crank  @ tilt {t:+d} vs servo', overlap(crk, C.servo, *LOW))]

rows += [('servo vs spine', overlap(C.servo, spine_s, *LOW)),
         ('spine vs hood', overlap(spine_s, hood_s, *SHELL)),
         ('spine vs roots', overlap(spine_s, A.roots, (-40, -40, 0), (40, 40, 13)))]
for pan in (45, 90):
    rows += [(f'spine @ pan {pan} vs roots',
              overlap(lambda p, a=pan: spine_s(rot_z(p, a)), A.roots, (-40, -40, 0), (40, 40, 13))),
             (f'hood  @ pan {pan} vs roots',
              overlap(lambda p, a=pan: C.hood(rot_z(p, a), True), A.roots, (-40, -40, 0), (40, 40, 13)))]

for t in TILTS:
    rows += [(f'VIEW @ tilt {t:+d} blocked by hood',
              overlap(lambda p, t=t: C.view_cone(p, t), hood_s, *NOSE)),
             (f'VIEW @ tilt {t:+d} blocked by yoke',
              overlap(lambda p, t=t: C.view_cone(p, t), lambda p, t=t: C.yoke(C.rot_y(p, t), False), *NOSE))]

bad = 0
for name, v in rows:
    flag = '' if v < 1.0 else '   <-- INTERFERENCE'
    bad += bool(flag)
    print(f'{name:<36} {v:8.2f} mm3{flag}', flush=True)
print(f'\n{len(rows)} checks, {bad} interference(s)')
