"""A 6704 bearing cup inside Zach's rev-2 ball_minus (2026-10-02).

With the wire route's stub screwed to the cradle, nothing turned in the -Y collar's bearing seat. Zach: "a
small divot inside of the minus of the ball to catch it ... sticking out from the edge to the inside of
the ball", for "same bearing as the other side" (a 6704, 20 x 27 x 4; he has 10). So the bearing now sits
in the ball: its outer ring turns with the ball, and the stub (tree_parts_b.stub) runs through its inner
ring and shoulders against it.

  ADD_minus_bearing_cup     a ring on the inside of his flat -Y wall, r 11..15.3, out to Y -19.0
  CUT_minus_bearing_pocket  the 27.1 pocket from outside the flat face to Y -20.0 (press the bearing in
                            from outside until it stops), then an r 11.8 hole through the lip and his
                            old hub. The lip catches the outer ring (r 12.3..13.5); the inner ring and
                            the stub stay clear of it.

Room, measured on his mesh: the flat wall is ~2 mm (Y -24.5..-22.5), his old hub is r 10.04..13.0 out to
Y -18.6, the shell starts at r 20, and the camera board starts at Y -18.1 (X 10.5). The cup stops at
Y -19.0, 0.9 short of the board.

Writes out/rev2/ball_minus_cup.brep; the print STL and the tool STEP come from wire_route_r1.py.
    python head-v2/fixes/ball_minus_cup.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import tree_parts_b as B
import campost_rev2 as R

H = B.H
POCKET_R = B.BRG_OD / 2            # 13.55: a 6704's 27.0 outside, +0.1 on the diameter like every seat here
LIP_Y0, LIP_Y1 = -20.0, -19.0      # the pocket's floor (the bearing's inner face) and the lip's inside face
LIP_HOLE_R = 11.8                  # clears the inner ring (~22.6 across, r 11.3) by 0.5; catches the outer
                                   # ring (r ~12.3..13.5) by 1.2
CUP_R = 15.3                       # 1.75 of wall round the pocket
CUP_Y0 = -23.0                     # overlaps his flat wall's inside face (~-22.5) by 0.5
BRG_Y0 = LIP_Y0 - B.BRG_W          # -24.0: the bearing's outer face, 0.5 below the ball's flat face
# a 6704's rings, for the checks: inner ring r 10.0..11.3, outer ring r 12.3..13.5 (shoulder diameters
# ~22.6 and ~24.6 -- APPROXIMATE, from typical 6704 drawings)
IN_R0, IN_R1, OUT_R0, OUT_R1 = 10.0, 11.3, 12.3, 13.5


def rr(p):
    return np.hypot(p[0], p[2] - H)


def sdf_add(p, y1=LIP_Y1):
    """The cup ring as a signed field (the checks use its sign, not its size: see the SDF-bound lesson)."""
    r = rr(p)
    return np.maximum(np.maximum(11.0 - r, r - CUP_R), np.maximum(CUP_Y0 - p[1], p[1] - y1))


def sdf_cut(p, hole_r=LIP_HOLE_R):
    r = rr(p)
    pocket = np.maximum(r - POCKET_R, np.maximum(-25.5 - p[1], p[1] - LIP_Y0))
    hole = np.maximum(r - hole_r, np.maximum((LIP_Y0 - 0.2) - p[1], p[1] - (-18.0)))
    return np.minimum(pocket, hole)


def bearing_rings(p):
    """(inner ring, outer ring) of the 6704 as seated, signed distances."""
    r, y = rr(p), p[1]
    ay = np.maximum(BRG_Y0 - y, y - LIP_Y0)
    return (np.maximum(np.maximum(IN_R0 - r, r - IN_R1), ay),
            np.maximum(np.maximum(OUT_R0 - r, r - OUT_R1), ay))


def tools():
    from kit import cyl, cut, fuse
    add = cut(cyl('y', (0.0, H), CUP_R, CUP_Y0, LIP_Y1), cyl('y', (0.0, H), 11.0, CUP_Y0 - 1, LIP_Y1 + 1))
    pocket = fuse(cyl('y', (0.0, H), POCKET_R, -25.5, LIP_Y0), cyl('y', (0.0, H), LIP_HOLE_R, LIP_Y0 - 0.2, -18.0))
    return {'ADD_minus_bearing_cup': add, 'CUT_minus_bearing_pocket': pocket}


def build():
    from kit import cut, fuse
    from occ_load import load
    his = load(R.BALL_MINUS)[0]
    t = tools()
    return his, cut(fuse(his, t['ADD_minus_bearing_cup']), t['CUT_minus_bearing_pocket'])


if __name__ == '__main__':
    from export import wr
    from occ_load import vol
    from kit import common, camera
    from OCP.BRepCheck import BRepCheck_Analyzer
    his, new = build()
    wr(new, config.out('rev2', 'ball_minus_cup.brep'))
    from export import write_stl
    write_stl(new, config.out('rev2', '_fig_ball_minus_cup.stl'), lin=0.01, ang=0.05)   # head frame, for the fit view
    print('ball_minus + 6704 cup: valid %s, volume %.1f -> %.1f mm3' % (BRepCheck_Analyzer(new).IsValid(), vol(his), vol(new)))
    cam = camera(2.5, centred=True, dz=R.LENS_DZ, dy=R.LENS_DY)
    print('  camera vs the new ball_minus %.3f mm3 (his: %.3f)' % (vol(common(cam, new)), vol(common(cam, his))))
