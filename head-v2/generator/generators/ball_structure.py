"""Structural audit of the ball halves: how each internal feature is attached, and how thick
the shell it attaches to actually is.

The erode-and-see-what-falls-off approach does not work here -- the shell is thinner than the
features, so it shatters first. Instead, each internal feature is isolated and its CONTACT AREA
with the rest of the solid is measured. A big feature on a small contact patch is the thing we
do not want.

    python ball_structure.py
"""
import numpy as np
from scipy import ndimage
import tree_parts_b as B
from tree_parts import box, rbox, cyl_y

STEP = 0.35
H, ZC = B.H, B.ZC

FEATURES = {
  'rail +Y':        lambda p: rbox(p, (B.BOARD_X0-1.5, B.BOARD_Y-3.0, H-26.0), (B.BOARD_X1+1.5, B.BOARD_Y+2.0, H+26.0), 1.0),
  'rail -Y':        lambda p: rbox(p, (B.BOARD_X0-1.5, -B.BOARD_Y-2.0, H-26.0), (B.BOARD_X1+1.5, -B.BOARD_Y+3.0, H+26.0), 1.0),
  'pad (-Y)':       lambda p: rbox(p, (-29.5, B.SERVO_Y0-3.0, ZC-4.0), (B.BOARD_X0-0.1, B.SERVO_Y0, ZC+4.0), 1.0),
  'seam rod -23+8': lambda p: cyl_y(p, -23.0, H+8.0, 2.8, -B.FLAT, B.FLAT),
  'seam rod -23-8': lambda p: cyl_y(p, -23.0, H-8.0, 2.8, -B.FLAT, B.FLAT),
  'seam rod 17-20': lambda p: cyl_y(p, 17.0, H-20.0, 2.8, -B.FLAT, B.FLAT),
  'hub stub (+Y)':  lambda p: cyl_y(p, 0, H, B.HUB_R, B.FLAT-2.0, B.BRG_P_Y1-0.2),
  'socket hub (-Y)':lambda p: cyl_y(p, 0, H, 13.0, -B.FLAT, -19.0),
  'tab boss near':  lambda p: cyl_y(p, 0.0, B.TAB_Z[0], B.TAB_BOSS_R + 0.4, B.TAB_BOSS_Y0, B.FLAT),
  'tab boss far':   lambda p: cyl_y(p, 0.0, B.TAB_Z[1], B.TAB_BOSS_R + 0.4, B.TAB_BOSS_Y0, B.FLAT),
}

for nm, half in (('ball_plus', B.ball_plus), ('ball_minus', B.ball_minus)):
    lo, hi = B.PARTS[nm][1], B.PARTS[nm][2]
    xs = [np.arange(lo[i], hi[i], STEP) for i in range(3)]
    P = np.meshgrid(*xs, indexing='ij')
    solid = half(P) < 0
    # shell thickness: distance transform on the solid, sampled where the feature set is absent
    print('\n=== %s ===  volume %.2f cm3' % (nm, solid.sum()*STEP**3/1000))
    print('  %-17s %9s %9s %10s' % ('feature', 'volume', 'contact', 'vol/contact'))
    for fname, ffn in FEATURES.items():
        feat = (ffn(P) < 0) & solid
        v = feat.sum()*STEP**3
        if v < 5:
            continue
        rest = solid & ~feat
        # contact = feature voxels with a non-feature solid neighbour, 6-connected
        nb = np.zeros_like(feat)
        for ax in (0,1,2):
            nb |= np.roll(rest, 1, ax) | np.roll(rest, -1, ax)
        contact = (feat & nb).sum()*STEP**2
        print('  %-17s %7.0f mm3 %6.0f mm2 %8.1f mm  %s'
              % (fname, v, contact, v/max(contact,1e-9), '<-- THIN' if v/max(contact,1e-9) > 4.0 else ''))
