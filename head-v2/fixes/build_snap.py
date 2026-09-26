"""Rev 2: the seam screws go, snap pins come in. Built from Zach's ORIGINAL two halves.
Kept from rev 1: rail notch, servo-slot shave (now stopping short of the rear posts), the two edge seals.
Dropped from rev 1: the front M3 screw post (a snap pin at the top front replaces it).
New: fill the old screw holes, a third post top-front, a socket in every post in both halves.
Rev 1 (screws) is in archive/head-v2-rev1-screws/ -- superseded, don't use it."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import time
import numpy as np
from kit import *
from snap import socket, pin, BARBS, NECK_R, CATCH_R, SOCKET_DEPTH, FLAT
from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere

H = B.H
# ---- carried over from rev 1
# the rail notch, so the IR-CUT holder goes in (dia 26.7 + 0.5 all round)
HOLDER_CLEAR_R = 26.7 / 2 + 0.5
# servo slot 12.20 -> 12.50 (shave 0.15 off each plate face)
SHAVE = 0.15
FLOOR, CEIL = 45.89, 58.09
# Mesh repair, not design: two 0.064 mm edges where the rear pad's corner meets the seam rods are
# each shared by FOUR faces in Zach's export (the shapes touch along an edge). A 0.3 mm filler around
# each makes the corner solid, so the edge is interior. Kept out of the Fusion tool set -- his model
# there is fine; the fault is in the tessellation.
SEALS = [bx((-21.46, 19.27, 57.23), (-21.14, 19.47, 57.53)),
         bx((-21.46, 19.27, 46.47), (-21.14, 19.47, 46.77))]

REAR = [(-23.0, 43.0), (-23.0, 61.0)]          # Zach's two rear posts, r 4.0 -- unchanged
FRONT = (6.3, 75.0)                             # new third post: top front, above the servo box ceiling,
POST_R = 4.0                                    # behind the board (its front face 0.2 inside the wall)
POSTS = REAR + [FRONT]
# The shave stops at X -19.8. Past that the rear posts rise into the slot's floor and ceiling, and a
# shave there left 0.03 mm between the posts' snap catches and the servo slot. The servo does not
# need it: its rear tab corners are snipped, and clear the posts by 0.4 mm without it.
SHAVE_X0 = -19.8

def tools():
    t = {}
    t['CUT_plus_rail_notch'] = cyl('x', (0, H), HOLDER_CLEAR_R, 13.5, 16.5)
    t['CUT_plus_slot_floor'] = bx((SHAVE_X0, -0.5, FLOOR - SHAVE), (10.8, 21.4, FLOOR + 0.06))
    t['CUT_plus_slot_ceiling'] = bx((SHAVE_X0, -0.5, CEIL - 0.06), (10.8, 21.4, CEIL + SHAVE))
    # 0.1 below the surface, not flush: flush, the plug's cap lay within 0.02 of Zach's faceted
    # sphere and the mesh cracked at the tangent. It leaves a 0.1 mm dimple where the hole was.
    sph_fill = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, H), B.R_BALL - 0.1).Shape()
    sph_post = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, H), B.R_BALL - 0.3).Shape()
    plus, minus = bx((-40, 0, 0), (40, 40, 100)), bx((-40, -40, 0), (40, 0, 100))
    # plug the old screw holes (r 1.7 / 1.25) and the head pockets (r 3.0) -- flush with the sphere
    for i, (x, z) in enumerate(REAR):
        t['ADD_plus_fill_%d' % (i + 1)] = common(cyl('y', (x, z), 3.1, 0.3, 25), sph_fill)
        t['ADD_minus_fill_%d' % (i + 1)] = common(cyl('y', (x, z), 3.1, -25, -0.3), sph_fill)
    post = common(cyl('y', FRONT, POST_R, -22, 22), sph_post)
    t['ADD_plus_front_post'] = common(post, plus)
    t['ADD_minus_front_post'] = common(post, minus)
    for i, c in enumerate(POSTS):
        t['CUT_plus_socket_%d' % (i + 1)] = socket(c, +1)
        t['CUT_minus_socket_%d' % (i + 1)] = socket(c, -1)
    return t

def build():
    t = tools()
    bp, bm = part('ball_plus'), part('ball_minus')
    adds_p = [s for k, s in t.items() if k.startswith('ADD_plus')]
    adds_m = [s for k, s in t.items() if k.startswith('ADD_minus')]
    bp2 = fuse(bp, *adds_p, *SEALS)
    bp2 = cut(bp2, *[s for k, s in t.items() if k.startswith('CUT_plus')])
    bm2 = cut(fuse(bm, *adds_m), *[s for k, s in t.items() if k.startswith('CUT_minus')])
    return bp2, bm2, t

def pin_seated(c, barb='medium'):
    """a pin in the assembly frame at post c: axis along Y, centred on the seam, flats horizontal"""
    p, _ = pin(BARBS[barb])
    return moved(p, c[0], 0, c[1])

if __name__ == '__main__':
    t0 = time.time()
    bp2, bm2, t = build()
    from OCP.BRepCheck import BRepCheck_Analyzer
    from OCP.BRepTools import BRepTools
    for nm, s in (('ball_plus', bp2), ('ball_minus', bm2)):
        print('%-10s valid %s  volume %.1f mm3 (yours %.1f)' % (nm, BRepCheck_Analyzer(s).IsValid(), vol(s), vol(part(nm))))
        BRepTools.Write_s(s, config.out(nm + '_snap.brep'))
    print('%.0f s' % (time.time() - t0))
