"""Zach's design as he drew it: servo pushed up against the plate at Y 21.24, board in front of the wall.
Run this on a new revision BEFORE judging it: it places the parts where his geometry puts them."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np, time
from kit import *
t0 = time.time()
bp, bm, po = part('ball_plus'), part('ball_minus'), part('post')
print('loaded in %.0f s' % (time.time() - t0))
TOP = 21.24
sv = servo(TOP)
sp = servo(TOP, parts=True)
print('\nSERVO, case top at Y %.2f (on the plate), turned, datasheet outline:' % TOP)
for nm, s in sp.items():
    print('  %-10s vs ball_plus %7.2f  ball_minus %7.2f  post %7.2f mm3' % (nm, overlap(s, bp), overlap(s, bm), overlap(s, po)))
print('  ear top face at Y %.2f; ear bosses start at Y 18.60 -> gap %.2f' % (TOP - A.TAB_FROM_TOP + B.TAB_T, 18.60 - (TOP - A.TAB_FROM_TOP + B.TAB_T)))
print('  spline Y %.2f..%.2f in the post bore from 27.50 -> engaged %.2f of %.1f'
      % (TOP + B.BOSS_H, TOP + B.SPLINE_STACK, TOP + B.SPLINE_STACK - 27.5, B.SPLINE_PROUD))
print('  boss top Y %.2f vs post face 27.50 -> gap %.2f' % (TOP + B.BOSS_H, 27.5 - TOP - B.BOSS_H))
print('\nfree travel of the servo body+ears (no screws) in the two halves:')
both = fuse(bp, bm)
base = overlap(fuse(sp['body'], sp['ear_rear'], sp['ear_front']), both)
for ax, nm in ((0, 'X'), (1, 'Y'), (2, 'Z')):
    for sg in (-1, 1):
        free = None
        for step in np.arange(0.1, 6.01, 0.1):
            d = [0, 0, 0]; d[ax] = sg * step
            if overlap(moved(fuse(sp['body'], sp['ear_rear'], sp['ear_front']), *d), both) > base + 0.5:
                free = step - 0.1; break
        print('  %s%s  %s' % (nm, '+' if sg > 0 else '-', ('%.1f mm' % free) if free is not None else '> 6 mm'))
print('\nCAMERA:')
for dx, lab in ((0.0, 'board at X 8.0 (my model)'), (2.5, 'board at X 10.5 (on your wall)')):
    c = camera(dx)
    print('  %-32s ball_plus %7.2f  ball_minus %7.2f  servo(ears) %6.2f  servo(no front ear) %6.2f mm3'
          % (lab, overlap(c, bp), overlap(c, bm), overlap(c, sv), overlap(c, servo(TOP, front_ear=False))))
print('\n%.0f s' % (time.time() - t0))
