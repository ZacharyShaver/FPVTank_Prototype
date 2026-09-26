"""Verify the fixed parts. Every zero is paired with the same row on the unfixed part (its negative control)."""
import os, time, numpy as np
from kit import *
from build import tools, OUT, RX, RZ, Y_HEAD, Y_OUT, PILOT_Y
from OCP.BRepTools import BRepTools
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Shape
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
def rd(p):
    s = TopoDS_Shape(); BRepTools.Read_s(s, p, BRep_Builder()); return s
def gap(a, b):
    d = BRepExtrema_DistShapeShape(a, b); d.Perform(); return d.Value()
if __name__ != "__main__": raise ImportError("check.py is a script")
t0 = time.time()
bp, bm, po = part('ball_plus'), part('ball_minus'), part('post')
bp2, bm2 = rd(os.path.join(OUT, 'ball_plus_fixed.brep')), rd(os.path.join(OUT, 'ball_minus_fixed.brep'))
T = tools()
print('WHAT EACH TOOL DID (mm3 of material)')
bp_rod, bm_rod = fuse(bp, T['ADD_plus_front_rod']), fuse(bm, T['ADD_minus_front_rod'])
for nm, s in T.items():
    tgt = (bp_rod if 'front' in nm else bp) if '_plus_' in nm else (bm_rod if 'front' in nm else bm)
    v = vol(cut(s, bp if '_plus_' in nm else bm)) if nm.startswith('ADD') else overlap(s, tgt)
    print('  %-24s %s %8.2f' % (nm, 'added  ' if nm.startswith('ADD') else 'removed', v))

cam = camera(2.5)                      # board on Zach's wall: back face X 10.5
TOP = 21.2355            # the plate face is at 21.2357 (ray-cast); the case top sits on it
full = servo(TOP, parts=True)
trim = servo_trimmed(TOP)
def solid(d, keys=('body', 'ear_rear', 'ear_front')):
    return fuse(*[d[k] for k in keys])
rows = []
def row(name, fixed, before):
    rows.append((name, fixed, before))
row('camera vs ball_plus', overlap(cam, bp2), overlap(cam, bp))
row('camera vs ball_minus', overlap(cam, bm2), overlap(cam, bm))
row('camera vs servo (tabs trimmed / as bought)', overlap(cam, fuse(*trim.values())), overlap(cam, fuse(*full.values())))
row('servo seated vs ball_plus', overlap(solid(trim), bp2), overlap(solid(full), bp))
row('servo seated vs ball_minus', overlap(solid(trim), bm2), overlap(solid(full), bm))
# the servo goes in from the seam and slides up the slot to the plate: test the whole path
worst_f, worst_b = 0.0, 0.0
for dy in np.arange(0.0, 24.01, 1.0):
    worst_f = max(worst_f, overlap(moved(solid(trim), 0, -dy, 0), bp2))
    worst_b = max(worst_b, overlap(moved(solid(full), 0, -dy, 0), bp))
row('servo sliding in, worst step', worst_f, worst_b)
row('ball halves vs each other', overlap(bp2, bm2), overlap(bp, bm))
row('spline vs post (press fit, by design)', overlap(trim['spline'], po), overlap(full['spline'], po))
print('\n%-44s %10s %12s' % ('', 'FIXED', 'as you sent'))
for n, a, b in rows:
    print('%-44s %9.2f %11.2f   mm3' % (n, a, b))

print('\nCLEARANCES (exact distance between the solids, mm)')
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
holder = cyl('x', (0, B.H), 26.7 / 2, 12.5, 21.1)
print('  IR-CUT holder to ball_plus          %.2f   (was %.2f)' % (gap(holder, bp2), gap(holder, bp)))
print('  camera to the new front rod          %.2f' % gap(cam, T['ADD_plus_front_rod']))
print('  camera to ball_plus overall          %.2f' % gap(cam, bp2))
print('  trimmed front tab to the board       %.2f' % gap(trim['ear_front'], cam))

from probe import hits, load_stl, DL as _DL
TPf = load_stl(os.path.join(OUT, 'BODY_NUMBA1_fixed.stl')); TMf = load_stl(os.path.join(OUT, 'ball_minus_revised_fixed.stl'))
TP0 = load_stl(os.path.join(_DL, 'BODY_NUMBA1 (1) (1).stl')); TM0 = load_stl(os.path.join(_DL, 'ball_minus_revised.stl'))
def zline(T, x, y):
    t = np.sort(hits(T, (x, y, 0.0), (0, 0, 1.0))); t = t[t > 0]
    lo = t[t < 52].max(); hi = t[t > 52].min(); return lo, hi
print('\nSERVO SLOT, floor..ceiling (lines along Z)')
for x, y in ((-19.0, 2.0), (-10.0, 10.0), (0.0, 16.0), (5.0, 20.5), (9.25, 5.0)):
    a, b = zline(TPf, x, y); a0, b0 = zline(TP0, x, y)
    print('  X %6.2f Y %5.2f   fixed %.2f..%.2f = %.2f    yours %.2f..%.2f = %.2f' % (x, y, a, b, b - a, a0, b0, b0 - a0))
print('\nFRONT SEAM SCREW (solid met along the screw axis, X %.1f Z %.1f)' % (RX, RZ))
segs = lambda c: ', '.join('%.2f..%.2f' % (c[k], c[k + 1]) for k in range(0, len(c) - 1, 2)) or '-'
for nm, T_, T0 in (('ball_plus', TPf, TP0), ('ball_minus', TMf, TM0)):
    for r, lab in ((0.0, 'on the axis'), (1.5, 'r 1.5: outside the pilot'), (2.5, 'r 2.5: inside the head recess'), (2.9, 'r 2.9: the rod wall')):
        t = np.sort(hits(T_, (RX - r, -40.0, RZ), (0, 1.0, 0))); t = t[t > 0] - 40.0
        t0_ = np.sort(hits(T0, (RX - r, -40.0, RZ), (0, 1.0, 0))); t0_ = t0_[t0_ > 0] - 40.0
        print('  %-10s %-30s fixed: %-28s yours: %s' % (nm, lab, segs(t), segs(t0_)))
print('  (head seat Y %.2f, sphere exit Y %.2f, pilot bottom Y %.1f)' % (Y_HEAD, Y_OUT, PILOT_Y))
print('%.0f s' % (time.time() - t0))
