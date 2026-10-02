"""Zach's rev-2 ball_plus with the IR cutout extended (2026-09-27).

He test-fitted the camera: the IR-cut block's cutout is "about 2 mm short on the left side (side with
snap ins)", i.e. +Y, the side the camera posts are on. His cutout through the 2 mm plate at X 14..16 is a
32 mm circle about (Y 0, Z 52.0), so its edge sits at Y 16.0 at mid-height.

CUT_plus_ir_extend is the same 32 mm circle moved 2.0 mm toward +Y, cut through the plate (overrunning
both faces, X 13.5..16.5). It is kept to Z 42.4..62.4 so it stays 1.0 mm off each post tube's outer wall
(tube r 3.4 about Z 37.95 and 66.85): the full-height shifted circle would cut into both tubes. What it
leaves: the edge at Y 18.0 at mid-height, 6.5 mm of plate out to the side wall at Y 24.5.

Writes out/rev2/ball_plus_rev2.brep and prints what the cut did.
    python head-v2/fixes/ball_plus_rev2.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import campost as C
import campost_rev2 as R
from kit import bx, cyl, cut, common, camera
from occ_load import load, vol

IR_SHIFT, IR_R, IR_ZC = 2.0, 16.0, 52.0          # his circle: r 16 about Z 52.0; moved this far toward +Y
IR_Z0, IR_Z1 = 42.4, 62.4                        # 1.0 off the tube walls


def tools():
    c = common(cyl('x', (IR_SHIFT, IR_ZC), IR_R, 13.5, 16.5), bx((13.4, 0.0, IR_Z0), (16.6, 30.0, IR_Z1)))
    return {'CUT_plus_ir_extend': c}


def build():
    his = load(R.BALL_PLUS)[0]
    return his, cut(his, *tools().values())


if __name__ == '__main__':
    from export import wr
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    his, new = build()
    wr(new, config.out('rev2', 'ball_plus_rev2.brep'))
    t = tools()['CUT_plus_ir_extend']
    print('ball_plus rev 2 + IR extension: valid %s, removed %.1f mm3' % (BRepCheck_Analyzer(new).IsValid(), vol(his) - vol(new)))
    R.use_rev2()
    for tb in C.TUBES:
        tube = C.tools(tb)['ADD_plus_tube_' + tb]
        d = BRepExtrema_DistShapeShape(t, tube); d.Perform()
        print('  cut vs %s tube wall: overlap %.3f mm3, gap %.2f mm' % (tb, vol(common(t, tube)), d.Value()))
    cam = camera(2.5, centred=True, dz=R.LENS_DZ, dy=R.LENS_DY)
    print('  camera vs the new ball_plus %.3f mm3 (vs his %.3f)' % (vol(common(cam, new)), vol(common(cam, his))))
