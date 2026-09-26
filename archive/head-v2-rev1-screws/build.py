"""Apply the surviving fixes to Zach's revised parts as exact OCC booleans.
Every tool body is a primitive, named, so the same set can go to Fusion as STEP."""
import os, time
import numpy as np
from kit import *
from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere

H = B.H
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)

# ---- fix A: notch the rail so the IR-CUT holder goes in (Ø26.7 + 0.5 all round)
HOLDER_CLEAR_R = 26.7 / 2 + 0.5
# ---- fix B: servo slot 12.20 -> 12.50 (shave 0.15 off each plate face)
SHAVE = 0.15
FLOOR, CEIL = 45.89, 58.09
# ---- fix C: a front seam screw, top-front. Placed as far IN as the camera allows -- the hole has to stay
# inside the sphere, and out here the sphere curves away fast: X >= 20.3 keeps the post 0.8 clear of the
# light sensor, Z >= 69.2 keeps it 0.8 clear of the IR-CUT block. Head on the -Y side (ball_minus): on the
# +Y side the head recess would have come within 0.15 mm of the upper board-screw tube's bore.
RX, RZ, ROD_R = 20.3, 69.2, 3.0
Y_OUT = float(np.sqrt(B.R_BALL ** 2 - RX ** 2 - (RZ - H) ** 2))    # where the axis leaves the sphere
# Head seat 4.2 below the surface, not the rear rods' 2.2: out here the sphere curves away so fast that at
# 2.2 a third of the seat under the head would be air. At 4.2 an M3 x 20 still gets 8.9 mm of thread.
Y_HEAD = -(Y_OUT - 4.2)                                              # head seat, in ball_minus
PILOT_Y = 10.0                                                       # thread depth into ball_plus

def tools():
    t = {}
    t['CUT_plus_rail_notch'] = cyl('x', (0, H), HOLDER_CLEAR_R, 13.5, 16.5)
    t['CUT_plus_slot_floor'] = bx((-22.3, -0.5, FLOOR - SHAVE), (10.8, 21.4, FLOOR + 0.06))
    t['CUT_plus_slot_ceiling'] = bx((-22.3, -0.5, CEIL - 0.06), (10.8, 21.4, CEIL + SHAVE))
    sph = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, H), B.R_BALL - 0.3).Shape()
    # run the post long and let the sphere trim it: at +-16 its inboard edge stopped 0.44 mm short of the
    # shell and 0.01 mm short at r 2.5 -- a near-coincident face, the thing the house rules forbid
    rod = common(cyl('y', (RX, RZ), ROD_R, -22, 22), sph)
    t['ADD_plus_front_rod'] = common(rod, bx((-40, 0, 0), (40, 40, 100)))
    t['ADD_minus_front_rod'] = common(rod, bx((-40, -40, 0), (40, 0, 100)))
    t['CUT_minus_front_clear'] = cyl('y', (RX, RZ), B.M3_CLEAR, -(Y_OUT + 3), 0.5)
    t['CUT_minus_front_head'] = cyl('y', (RX, RZ), B.M3_HEAD, -(Y_OUT + 5), Y_HEAD)
    t['CUT_plus_front_pilot'] = cyl('y', (RX, RZ), B.M3_PILOT, -0.5, PILOT_Y)
    return t

# Mesh repair, not design: two 0.064 mm edges where the rear pad's corner meets the seam rods are
# each shared by FOUR faces in Zach's export (the shapes touch along an edge). A 0.3 mm filler around
# each makes the corner solid, so the edge is interior. Kept out of the Fusion tool set -- his model
# there is fine; the fault is in the tessellation.
SEALS = [bx((-21.46, 19.27, 57.23), (-21.14, 19.47, 57.53)),
         bx((-21.46, 19.27, 46.47), (-21.14, 19.47, 46.77))]

def build():
    t = tools()
    bp, bm = part('ball_plus'), part('ball_minus')
    bp2 = fuse(bp, t['ADD_plus_front_rod'], *SEALS)
    bp2 = cut(bp2, t['CUT_plus_rail_notch'], t['CUT_plus_slot_floor'], t['CUT_plus_slot_ceiling'],
              t['CUT_plus_front_pilot'])
    bm2 = cut(fuse(bm, t['ADD_minus_front_rod']), t['CUT_minus_front_clear'], t['CUT_minus_front_head'])
    return bp2, bm2, t

if __name__ == '__main__':
    t0 = time.time()
    bp2, bm2, t = build()
    print('built in %.0f s' % (time.time() - t0))
    print('front screw at X %.1f Z %.1f: sphere exit Y +-%.2f, head seat Y %.2f (ball_minus), pilot to Y +%.1f'
          % (RX, RZ, Y_OUT, Y_HEAD, PILOT_Y))
    for L in (16, 20, 25):
        print('  M3 x %d: tip at Y %+.1f' % (L, Y_HEAD + L))
    # how close does each hole run to the OUTSIDE of the ball, anywhere along its length?
    for nm, r, y0, y1 in (('clearance', B.M3_CLEAR, Y_HEAD, 0.0), ('pilot', B.M3_PILOT, 0.0, PILOT_Y)):
        ys = np.linspace(y0, y1, 400); rxz = np.hypot(RX, RZ - H) + r
        if nm == 'clearance': ys = ys[ys > Y_HEAD + 0.3]   # the last bit breaks into the head recess, which is open anyway
        wall = np.sqrt(np.maximum(B.R_BALL ** 2 - ys ** 2, 0)) - rxz
        print('  %-9s hole: thinnest wall to the outside %.2f mm (at Y %+.1f)' % (nm, wall.min(), ys[np.argmin(wall)]))
    from OCP.BRepCheck import BRepCheck_Analyzer
    for nm, s in (('ball_plus', bp2), ('ball_minus', bm2)):
        print('%-10s valid %s  volume %.1f mm3 (was %.1f)' % (nm, BRepCheck_Analyzer(s).IsValid(), vol(s), vol(part(nm))))
    # save the BRep for the checker and the exporter
    from OCP.BRepTools import BRepTools
    from OCP.BRep import BRep_Builder
    BRepTools.Write_s(bp2, os.path.join(OUT, 'ball_plus_fixed.brep'))
    BRepTools.Write_s(bm2, os.path.join(OUT, 'ball_minus_fixed.brep'))
    print('%.0f s' % (time.time() - t0))
