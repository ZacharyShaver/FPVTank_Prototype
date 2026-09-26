"""Post v3: reach further, and a real stop for the spline.

Zach's post ends at Y 27.5 with a 3.74 deep spline bore, a 0.76 lip, and a 2.0 hole. Nothing holds the
ball along the tilt axis -- it slides 0.93 either way between the cradle's collars -- so pressing the post
on pushes the ball to the far collar, and only ~1.8 mm of the 4.0 mm spline goes in.
v3: face 0.76 further in (Y 26.74), bore ends at a 1.5 mm STOP LIP at Y 30.24, and the lip hole is a
CLEARANCE hole for the servo's centre (horn) screw. Tightening that screw pulls the spline tip up onto
the lip; with the servo's case top on its plate, that puts the ball dead centre between the collars
(0.93 each side) and 3.5 mm of spline in the post. The post's end stays 0.5 mm off the servo's boss,
which turns with the ball.
The 0.93 and ~1.8 above are the old session's first figures. checks/reach_check.py measures the slide
from the nest's own SDF: 0.60 each way, and 2.13 mm of spline in Zach's post with the ball pushed away.
Those are the numbers in the print-set README and the regression table."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import *
H = B.H
TOP = 21.2355                                   # servo case top, on Zach's plate
SPLINE_TIP = TOP + B.SPLINE_STACK               # 30.24 with the ball centred
BOSS_TOP = TOP + B.BOSS_H                       # 26.24
FACE = BOSS_TOP + 0.50                          # post's inboard end: 0.5 off the boss
LIP0, LIP1 = SPLINE_TIP, SPLINE_TIP + 1.5       # the stop lip the spline tip is pulled onto
BORE_R = 2.22                                   # = the flats of Zach's faceted 4.5 bore: same press fit
HOLE_R = 1.35                                   # clears M2 and M2.5
CB_R = 2.60                                     # head counterbore, 5.2
POST_R = 7.69
def tools():
    t = {}
    t['ADD_extend'] = cyl('y', (0, H), POST_R, FACE, 27.6)
    t['ADD_fill_old_bore'] = cyl('y', (0, H), 2.45, 27.4, 31.30)
    t['CUT_bore'] = cyl('y', (0, H), BORE_R, FACE - 0.5, LIP0)
    from snap import _revolve_y
    t['CUT_bore_leadin'] = _revolve_y([(0, FACE - 0.5), (BORE_R + 0.4 + 0.5, FACE - 0.5), (BORE_R, FACE + 0.4), (0, FACE + 0.4)], (0, H), +1)
    t['CUT_screw_hole'] = cyl('y', (0, H), HOLE_R, LIP0 - 0.2, LIP1 + 0.2)
    t['CUT_head_counterbore'] = cyl('y', (0, H), CB_R, LIP1, 34.6)
    return t
def build():
    t = tools(); p = part('post')
    p = fuse(p, t['ADD_extend'], t['ADD_fill_old_bore'])
    return cut(p, t['CUT_bore'], t['CUT_bore_leadin'], t['CUT_screw_hole'], t['CUT_head_counterbore']), t
if __name__ == '__main__':
    p3, t = build()
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepTools import BRepTools
    BRepTools.Write_s(p3, config.out('post_v3.brep'))
    print('post v3 valid %s  vol %.1f (yours %.1f)' % (BRepCheck_Analyzer(p3).IsValid(), vol(p3), vol(part('post'))))
    print('face Y %.2f | bore to %.2f (%.2f deep) | lip %.2f..%.2f | boss top %.2f | spline tip %.2f'
          % (FACE, LIP0, LIP0 - FACE, LIP0, LIP1, BOSS_TOP, SPLINE_TIP))
