"""Snap pins instead of seam screws. Separate pins, printed LYING DOWN (a pin printed standing up
snaps off along its layer lines, and a pin moulded onto a half can't be printed with that half's
seam face on the bed). Each post gets a blind socket from the seam face: a lead-in, a double-D
neck the pin's flats key into, then a wider catch the barb springs out into. The barb's back is a
45 deg cone, so the halves pull apart again by hand -- the ball gets opened a lot.

Sizes are driven by the posts: the rear posts are 8.0 across, so the catch (5.6) leaves 1.2 of wall."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import cadquery as cq
from kit import B, bx, cyl, fuse, cut, common, moved
from OCP.BRepPrimAPI import BRepPrimAPI_MakeRevol, BRepPrimAPI_MakeSphere
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCP.gp import gp_Pnt, gp_Ax1, gp_Dir
H = B.H

# ---------------------------------------------------------------- the socket (same in both halves)
NECK_R = 2.35          # pin body 2.2 -> 0.15 clearance
FLAT = 1.95            # neck flats at +-1.95; pin flats at +-1.8 -> 0.15 clearance; keys the pin's rotation
CATCH_R = 2.80
CATCH_L = 1.40
CHAMFER = 0.50         # lead-in at the seam face; also eats the first-layer squish (the seam face is on the bed)
PIN_R = 2.20
PIN_FLAT = 1.80
SLOT_W = 1.20
SLOT_FROM = 1.20       # the middle 2 x 1.2 mm is solid: that's what carries the shear across the seam
S_B = 8.00             # where the barb's back cone starts, from the seam
PRELOAD = 0.10         # the back cone sits this far (radially) onto the neck's edge when seated, so the
                       # prongs stay slightly sprung and pull the two halves together -- no rattle
D_S = S_B + (NECK_R + PRELOAD - PIN_R)          # depth of the neck -> catch step = 8.25
BARBS = {'soft': 2.55, 'medium': 2.60, 'firm': 2.65}
SOCKET_DEPTH = D_S + CATCH_L + CATCH_R          # the catch closes with a 45 deg cone (no flat ceiling)

def _revolve_y(profile_rho_d, c, sign):
    """revolve a (rho, depth) profile about the Y axis through (c[0], c[1]); depth along sign*Y"""
    poly = BRepBuilderAPI_MakePolygon()
    for rho, d in profile_rho_d:
        poly.Add(gp_Pnt(c[0] + rho, sign * d, c[1]))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakeRevol(face, gp_Ax1(gp_Pnt(c[0], 0, c[1]), gp_Dir(0, 1, 0)), 2 * np.pi).Shape()

def socket(c, sign):
    """sign +1: into ball_plus (+Y), -1: into ball_minus. c = (x, z) of the post axis."""
    ov = 0.5                                                      # overrun past the seam face
    neck = _revolve_y([(0, -ov), (NECK_R + CHAMFER + ov, -ov), (NECK_R, CHAMFER), (NECK_R, D_S + 0.01), (0, D_S + 0.01)], c, sign)
    y0, y1 = sorted((sign * -ov - sign * 0.0, sign * (D_S + 0.02)))
    flats = bx((c[0] - 5, min(-ov * sign, sign * (D_S + 0.02)), c[1] - FLAT), (c[0] + 5, max(-ov * sign, sign * (D_S + 0.02)), c[1] + FLAT))
    catch = _revolve_y([(0, D_S), (CATCH_R, D_S), (CATCH_R, D_S + CATCH_L), (0, D_S + CATCH_L + CATCH_R)], c, sign)
    return fuse(common(neck, flats), catch)

# ---------------------------------------------------------------- the pin (its own frame: axis along Y)
# The stop (Zach, 2026-09-25, off the test block): once clicked, the first pin could still slide 0.75 mm
# deeper with nothing touching it -- the barb's lead-in only met the socket's end cone at +0.85. Shoved
# that deep into the first half, its far end sat short of the catch in the second half, and pressing the
# second half on just drove the pin further into the first. The ends now carry a round NOSE that reaches
# the end cone NOSE_STOP after the click position, so the pin stops where it clicks -- and if it is shoved
# past that, the cone squeezes the split ends and pushes it back out. Pin only: the sockets are unchanged,
# so halves already printed take the new pins as they are.
NOSE_R = 2.00
NOSE_STOP = 0.05
S_NOSE = SOCKET_DEPTH - NOSE_R - NOSE_STOP      # = 10.40: where the cone is NOSE_R wide, less the stop

def pin(barb_r=BARBS['medium'], nose=True):
    land = S_B + (barb_r - PIN_R)                               # barb land starts here
    if nose:
        lh = S_NOSE
        half = [(0, 0), (PIN_R, 0), (PIN_R, S_B), (barb_r, land), (barb_r, land + 0.6),
                (NOSE_R, land + 0.6 + (barb_r - NOSE_R)), (NOSE_R, lh), (0, lh)]
    else:                                                        # the first pins (no stop): SUPERSEDED, kept
        lh = land + 0.6 + (barb_r - 2.05)                        # as the negative control in checks/freeplay.py
        half = [(0, 0), (PIN_R, 0), (PIN_R, S_B), (barb_r, land), (barb_r, land + 0.6), (2.05, lh), (0, lh)]
    top = _revolve_y(half, (0.0, 0.0), +1)
    bot = _revolve_y(half, (0.0, 0.0), -1)
    body = common(fuse(top, bot), bx((-5, -lh - 1, -PIN_FLAT), (5, lh + 1, PIN_FLAT)))
    slots = []
    for sg in (1, -1):
        s0, s1 = SLOT_FROM, lh + 1
        slots.append(bx((-SLOT_W / 2, min(sg * s0, sg * s1), -3), (SLOT_W / 2, max(sg * s0, sg * s1), 3)))
        slots.append(cyl('z', (0.0, sg * SLOT_FROM), SLOT_W / 2, -3, 3))      # round the slot's root
    return cut(body, *slots), lh

if __name__ == '__main__':
    from occ_load import vol
    for nm, br in BARBS.items():
        p, lh = pin(br)
        print('pin %-6s barb r %.2f  length %.2f  vol %.1f mm3  insertion squeeze %.2f per prong'
              % (nm, br, 2 * lh, vol(p), br - NECK_R))
    print('socket depth %.2f  neck->catch step at %.2f' % (SOCKET_DEPTH, D_S))
