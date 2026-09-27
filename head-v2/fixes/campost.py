"""Camera snap posts for ball_plus (2026-09-26): they replace the camera board's two screws.

Each post goes in from OUTSIDE through Zach's old screw tube (the board's two +Y outer holes). From the
inside out: a 1.8 pin through the board's hole, a shoulder that presses the board onto his wall, split
prongs whose barbs click behind a step in the tube, and a head trimmed to the ball's sphere 0.2 under the
surface. The same family as the seam snap pins (double-D, printed lying down, revolved barb cut by the
flats), scaled to the tube. Why outside and not a pin from inside: docs/decisions.md, 2026-09-26.

Frames: each post and tool is built in a LOCAL frame -- x along the tube axis (= head X), z_L = u (the
direction pointing away from the lens axis in YZ), y_L = v -- then rotated about X onto the tube. The
prongs flex in v. A post prints on its -u flat, so the pin sits on the bed and the angled head faces up.

 - The UPPER post's top flat is 1.5, not 1.1, so the long post can't go in the lower hole, where it would
   stand ~1 mm proud. The short one in the upper hole just sits deep, which is harmless.
 - Every grade has its land end 0.16 inboard of the step, so all three click with the same margin; the
   grade only changes how hard the click is and the preload.

Source: out/BODY_NUMBA1_snap.stl (rev 2, from export_snap.py), sewn -- the same mesh the hand-off shipped.
Writes out/ball_plus_camposts.brep and out/camera_post_<upper|lower>_<soft|medium|firm>.brep."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import B, bx, cyl, fuse, cut, common, moved
from occ_load import load, vol
from OCP.gp import gp_Pnt, gp_Ax1, gp_Dir, gp_Trsf, gp_Vec
from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol, BRepPrimAPI_MakeSphere
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Transform

H, R_BALL = B.H, B.R_BALL                   # 52.0, 30.7 -- his halves fit centre (0.03, 0.00, 52.00) R 30.705
TUBES = {'lower': (14.7, 35.95), 'upper': (14.7, 64.85)}   # fitted exactly: the board's two +Y outer holes

WALL_FACE, BOARD_T = 10.5, 2.0              # board back face lands on the wall; caliper 2.0 (Zach)
X_SH = WALL_FACE + BOARD_T                  # 12.5 shoulder = board front face
TUBE_X0 = 13.0                              # old tube's inner end, 0.5 off the board -- kept

R_PIN, PIN_TIP, PIN_CH = 0.90, 9.5, 0.30    # 1.8 for the 2.0 holes (PHOTO value), 1.0 into the wall's 4.0 hole
R_BODY = 1.80                               # 3.6: inside the board's 4.0 pad
F_LO = 0.80                                 # bed flat (-u), just under the pin's radius so the pin prints flat
F_HI = {'lower': 1.10, 'upper': 1.50}       # top flat (+u): the difference is the swap-proofing
SLOT_W, X_ROOT = 0.80, 13.40                # slot from the head to a round end, 0.5 solid behind the shoulder
RECESS = 0.20                               # head this far under the ball surface

CLR = 0.15
R_NECK = R_BODY + CLR                       # 1.95
B_LO = F_LO + CLR                           # 0.95
B_HI = {k: v + CLR for k, v in F_HI.items()}  # 1.25 / 1.65
R_CATCH, X_CATCH0, X_EDGE = 2.30, 17.2, 19.0
R_TUBE = 3.40

BARBS = {'soft': 2.05, 'medium': 2.10, 'firm': 2.15}
TAN = np.tan(np.radians(30.0))              # both barb faces 30 deg from the axis
LAND, LAND_END = 0.60, X_EDGE - 0.16        # all grades: land passes the step 0.16 before the shoulder seats

SRC = config.out('BODY_NUMBA1_snap.stl')

def u_of(tube):
    y, z = TUBES[tube]; d = np.array([y, z - H]); return d / np.linalg.norm(d)

def trsf(tube):
    uy, uz = u_of(tube)
    r = gp_Trsf(); r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), float(np.arctan2(-uy, uz)))
    t = gp_Trsf(); t.SetTranslation(gp_Vec(0.0, *map(float, TUBES[tube])))
    return t.Multiplied(r)

def to_head(s, tube):
    return BRepBuilderAPI_Transform(s, trsf(tube), True).Shape()

def to_local(s, tube):
    return BRepBuilderAPI_Transform(s, trsf(tube).Inverted(), True).Shape()

def revolve_x(prof):
    poly = BRepBuilderAPI_MakePolygon()
    for x, r in prof:
        poly.Add(gp_Pnt(float(x), 0.0, float(r)))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakeRevol(face, gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), 2 * np.pi).Shape()

def slab(lo, hi, x0=-5.0, x1=60.0):
    return bx((x0, -9, -lo), (x1, 9, hi))

def sphere(r):
    return BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, H), float(r)).Shape()

def barb_x(rb):
    """(ramp start, land start, land end, back cone end) along x"""
    x_l1 = LAND_END
    x_l0 = x_l1 - LAND
    return x_l0 - (rb - R_BODY) / TAN, x_l0, x_l1, x_l1 + (rb - R_BODY) / TAN

def preload(rb):
    """radial squeeze left on each prong when seated (cone radius at the step minus the neck)"""
    _, _, x_l1, _ = barb_x(rb)
    return rb - (X_EDGE - x_l1) * TAN - R_NECK

def post_local(tube, rb):
    xa, x_l0, x_l1, xd = barb_x(rb)
    prof = [(PIN_TIP, 0), (PIN_TIP, R_PIN - PIN_CH), (PIN_TIP + PIN_CH, R_PIN), (X_SH, R_PIN), (X_SH, R_BODY),
            (xa, R_BODY), (x_l0, rb), (x_l1, rb), (xd, R_BODY), (40.0, R_BODY), (40.0, 0)]
    p = common(revolve_x(prof), slab(F_LO, F_HI[tube]))
    slot = fuse(bx((X_ROOT, -SLOT_W / 2, -3), (41, SLOT_W / 2, 3)), cyl('z', (X_ROOT, 0.0), SLOT_W / 2, -3, 3))
    return cut(p, slot)

def post(tube, barb='medium'):
    """seated, head frame"""
    return common(to_head(post_local(tube, BARBS[barb]), tube), sphere(R_BALL - RECESS))

def tools(tube):
    add = common(to_head(cyl('x', (0, 0), R_TUBE, TUBE_X0, 40), tube), sphere(R_BALL - 0.1))
    neck = to_head(common(cyl('x', (0, 0), R_NECK, TUBE_X0 - 0.1, 45), slab(B_LO, B_HI[tube])), tube)
    catch = to_head(common(cyl('x', (0, 0), R_CATCH, X_CATCH0, X_EDGE), slab(B_LO, B_HI[tube])), tube)
    return {'ADD_plus_tube_' + tube: add, 'CUT_plus_bore_' + tube: neck, 'CUT_plus_catch_' + tube: catch}

def all_tools():
    T = {}
    for tb in TUBES:
        T.update(tools(tb))
    return T

def build():
    bp = load(SRC)[0]
    T = all_tools()
    bp2 = fuse(bp, *[s for k, s in T.items() if k.startswith('ADD')])
    bp2 = cut(bp2, *[s for k, s in T.items() if k.startswith('CUT')])
    return bp, bp2, T

if __name__ == '__main__':
    import time
    from OCP.BRepCheck import BRepCheck_Analyzer
    from export import wr
    t0 = time.time()
    for nm, rb in BARBS.items():
        xa, x0, x1, xd = barb_x(rb)
        print('barb %-6s r %.2f: ramp %.2f  land %.2f..%.2f  cone to %.2f  squeeze %.2f  preload %.3f'
              % (nm, rb, xa, x0, x1, xd, rb - R_NECK, preload(rb)))
    bp, bp2, T = build()
    print('ball_plus valid %s  vol %.1f -> %.1f  (%.0f s)' % (BRepCheck_Analyzer(bp2).IsValid(), vol(bp), vol(bp2), time.time() - t0))
    wr(bp2, config.out('ball_plus_camposts.brep'))
    for tb in TUBES:
        for g in BARBS:
            p = post(tb, g)
            wr(p, config.out('camera_post_%s_%s.brep' % (tb, g)))
            print('post %-5s %-6s valid %s vol %.1f' % (tb, g, BRepCheck_Analyzer(p).IsValid(), vol(p)))
    print('%.0f s' % (time.time() - t0))
