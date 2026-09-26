"""Rev 2 as meshes. In Zach's frame (to overlay on his design, and for the checks): both halves, needle-
repaired, and post v3. The pins with the stop and the test block, lying the way they print. The three
meshes the pin-stop picture cuts through. Then the mesh report on everything a person gets."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from kit import *
from snap import socket, pin, BARBS, SOCKET_DEPTH
from export import write_stl, health, tidy, rd
from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib

def xform(s, rot_deg=0.0, axis=(1, 0, 0), dz_to_bed=True):
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(*axis)), np.radians(rot_deg))
    s = BRepBuilderAPI_Transform(s, t, True).Shape()
    b = Bnd_Box(); BRepBndLib.Add_s(s, b); x0, y0, z0, x1, y1, z1 = b.Get()
    t2 = gp_Trsf(); t2.SetTranslation(gp_Vec(-(x0 + x1) / 2, -(y0 + y1) / 2, -z0))
    return BRepBuilderAPI_Transform(s, t2, True).Shape()

def test_block():
    """a 14 x 14 x 2 plate (stands in for the seam face) with an 8.0 post, the ball's socket up the post
    from the plate's underside; socket along +Y"""
    plate = bx((-7, 0, -7), (7, 2.0, 7))
    postc = cyl('y', (0.0, 0.0), 4.0, 0, SOCKET_DEPTH + 1.5)
    return cut(fuse(plate, postc), socket((0.0, 0.0), +1))

if __name__ == '__main__':
    # the halves, in Zach's frame
    halves = {'BODY_NUMBA1_snap.stl': 'ball_plus_snap.brep', 'ball_minus_revised_snap.stl': 'ball_minus_snap.brep'}
    for fn, br in halves.items():
        write_stl(rd(config.out(br)), config.out(fn))
        print('  %s: needle repair moved the surface at most %.4f mm' % (fn, tidy(config.out(fn))))
    # post v3, in Zach's frame
    write_stl(rd(config.out('post_v3.brep')), config.out('ball_servo_post_v3.stl'), lin=0.005, ang=0.05)
    # pins with the stop, lying on a flat (their flats are +-Z already), long axis along the bed
    for nm, br in BARBS.items():
        p, lh = pin(br, nose=True)
        write_stl(xform(p), config.out('snap_pin_stop_%s.stl' % nm), lin=0.005, ang=0.05)
    # the test block, printed like the halves: socket opening on the bed
    write_stl(xform(test_block(), 90.0), config.out('snap_test_block.stl'), lin=0.005, ang=0.05)
    # for figure_stop.py: the block, the first pin and the pin with the stop, one frame (socket along +Y, flats +-Z)
    write_stl(test_block(), config.out('_fig_block.stl'), lin=0.005, ang=0.05)
    write_stl(pin(BARBS['medium'], nose=False)[0], config.out('_fig_pin_old.stl'), lin=0.005, ang=0.05)
    write_stl(pin(BARBS['medium'], nose=True)[0], config.out('_fig_pin_new.stl'), lin=0.005, ang=0.05)
    print('mesh health:')
    for fn in list(halves) + ['ball_servo_post_v3.stl'] + ['snap_pin_stop_%s.stl' % n for n in BARBS] + ['snap_test_block.stl']:
        ok, msg = health(config.out(fn)); print('  %-30s %s%s' % (fn, msg, '' if ok else '   <-- CHECK'))
