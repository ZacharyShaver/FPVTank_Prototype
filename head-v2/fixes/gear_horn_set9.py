"""Pan coil set 9 (2026-10-10): the input gear carries the servo's own horn, cut exactly.

Zach at the bench: the input gear slips on the spline (its screw turns, the gear doesn't), and it rubs the servo's
block above it, worse as the screw tightens. See pan_coil_b.HORN_GEAR. This builds the gear exactly (the generator's
tooth formula, its floor 1.0 under the block, a hole through the floor under the horn's centre) and cuts the horn's
pocket into it: the double-arm horn's outline (Arm02, solid 1 of ../generator/pan-coil-b/horn/MG90_Arm.step) from
where the spline seats it straight up through the top face, so the horn drops in from above.

As first printed, the pocket was zero offset (his horn-pocket rule) and the floor was solid under an M2 x 6. The horn
went in so tight it flew out and hit him in the eye, and the horn kit's own screw (3 mm head, 5 long) couldn't reach.
Now the outline grows HORN_FIT a side (two gears: HORN_FITS) and the floor is open (GEAR_HOLE_R), so the stock screw
seats on the horn's web as the horn was made for.

Writes ../generator/pan-coil-b/print/gear_in.stl (HORN_FITS[0]) and gear_in_loose.stl (HORN_FITS[1]), print-oriented
(bottom face down), and out/print-pan/_fig_gear_in_set9.stl + _fig_horn_set9.stl (assembled frame, for the views).

    python head-v2/fixes/gear_horn_set9.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import cadquery as cq
import pymeshlab as ml
from tree_parts import quiet, mesh_set
import pan_coil_b as P
import pan_coil_b_print as PP

HORN_STEP = os.path.join(P.OUT, 'horn', 'MG90_Arm.step')
HORN_AXIS_X = 30.0                 # solid 1's axis in its own file: x 26.55..33.45, z -15.68..15.68, height along +y
FIG = config.out('print-pan', '_fig_gear_in_set9.stl')
FIG_HORN = config.out('print-pan', '_fig_horn_set9.stl')
PRINTS = {P.HORN_FITS[0]: os.path.join(PP.OUT, 'gear_in.stl'), P.HORN_FITS[1]: os.path.join(PP.OUT, 'gear_in_loose.stl')}
HEAD_R, HEAD_H = 1.5, 1.6          # the horn kit's machine screw: his listing's 3 mm head; its height a guess


def blank():
    """The input gear without its pocket, as an exact solid in the assembled frame: pan_coil_b.gear's zero surface,
    r = R_IN_G + TOOTH cos(N_IN t + pi) about the input axis (24 points a tooth), from G_Z0 to GIN_Z1, with the hole
    through its floor under the horn's centre. (Meshing the SDF and sewing it back into a solid came out invalid, and
    the cut silently did nothing: the first run, 2026-10-10.)"""
    n = P.N_IN
    t = np.linspace(0, 2 * np.pi, n * 24, endpoint=False)
    r = P.R_IN_G + P.TOOTH * np.cos(n * t + np.pi)
    pts = [(P.CENTRE + a * np.cos(b), a * np.sin(b)) for a, b in zip(r, t)]
    g = cq.Workplane('XY', origin=(0, 0, P.G_Z0)).polyline(pts).close().extrude(P.GIN_Z1 - P.G_Z0)
    z = P.G_Z0 - 1.0
    hole = cq.Workplane('XY', origin=(P.CENTRE, 0, z)).circle(P.GEAR_HOLE_R).extrude(P.HORN_FACE_Z + 0.5 - z)
    return g.cut(hole).val()


def place(s):
    """Arm02's file frame -> the assembled frame: height (+y) up, arms along Y, flat face at HORN_FACE_Z."""
    s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90)          # y -> Z, z -> -Y
    return s.translate(cq.Vector(P.CENTRE - HORN_AXIS_X, 0, P.HORN_FACE_Z))


def horn_and_pocket(fit):
    """(the horn as seated, the pocket, the outline grown by fit and by 0): the pocket is the horn's flat-face outline,
    grown fit a side in plan, from the face up to 1 past the gear's top face."""
    h = cq.importers.importStep(HORN_STEP).solids().vals()[1]
    flats = [f for f in h.Faces() if f.geomType() == 'PLANE' and abs(f.Center().y) < 1e-6
             and abs(f.normalAt().y + 1) < 1e-6]
    flat = max(flats, key=lambda f: f.Area())
    w0 = flat.outerWire()
    w = w0.offset2D(fit, 'arc')[0] if fit > 0 else w0
    prism = cq.Solid.extrudeLinear(w, [], cq.Vector(0, P.GIN_Z1 + 1.0 - P.HORN_FACE_Z, 0))
    return place(h), place(prism.fuse(h)), cq.Face.makeFromWires(w), cq.Face.makeFromWires(w0)


def to_bed(src, dst):
    with quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(src); ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
        V = ms.current_mesh().vertex_matrix().copy(); F = ms.current_mesh().face_matrix().copy()
    V -= [(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, V[:, 2].min()]
    with quiet():
        pm = mesh_set(V, F); pm.save_current_mesh(dst, binary=True)
    return V.max(0) - V.min(0)


if __name__ == '__main__':
    from occ_load import vol
    from kit import cut, common, moved, cyl, fuse
    from export import write_stl, health
    from OCP.BRepCheck import BRepCheck_Analyzer
    b = blank(); blk = b.wrapped
    print('blank: valid %s, %.1f mm3' % (b.isValid(), b.Volume()))
    bad = 0
    for fit in P.HORN_FITS:
        horn, pocket, f_fit, f0 = horn_and_pocket(fit)
        gear = cut(blk, pocket.wrapped)
        grown = (f_fit.Area() - f0.Area()) / f0.outerWire().Length()
        # exact checks: the horn seated and on its way in from above; the stock screw's head on the horn's web, and
        # the driver's way up to it through the gear's floor
        seated, ctrl = vol(common(gear, horn.wrapped)), vol(common(blk, horn.wrapped))
        path = max(vol(common(gear, moved(horn.wrapped, dz=d))) for d in (8.0, 4.0, 2.0, 1.0, 0.5))
        head_top = P.HORN_FACE_Z + P.HORN_CB_H
        screw = fuse(cyl('z', (P.CENTRE, 0.0), HEAD_R, head_top - HEAD_H, head_top),
                     cyl('z', (P.CENTRE, 0.0), HEAD_R, P.G_Z0 - 10.0, head_top - HEAD_H))
        s_ov = vol(common(gear, screw))
        thread = head_top + P.HORN_SCREW_L - (P.SV_Z0 - P.SPLINE_REAL)       # tip minus the spline's tip
        ok = seated < 0.01 and ctrl > 50 and path < 0.01 and s_ov < 0.01 and abs(grown - fit) < 0.02
        print('fit %.2f: valid %s, %.1f mm3; outline grown %.3f a side; horn vs gear seated %.3f, coming down %.3f '
              '(control, the blank %.1f); screw head + driver vs gear %.3f; the screw %.1f mm into the spline'
              % (fit, BRepCheck_Analyzer(gear).IsValid(), vol(gear), grown, seated, path, ctrl, s_ov, thread)
              + ('' if ok else '   <== CHECK'))
        if fit == P.HORN_FIT:
            write_stl(gear, FIG, lin=0.01, ang=0.05)
            write_stl(horn.wrapped, FIG_HORN, lin=0.01, ang=0.1)
            src = FIG
        else:
            src = os.path.join(PP.OUT, '_gear_in_fig_loose.stl'); write_stl(gear, src, lin=0.01, ang=0.05)
        size = to_bed(src, PRINTS[fit])
        hok, msg = health(PRINTS[fit])
        print('  print %s: %s   %.1f x %.1f x %.1f mm, bottom face down' % (os.path.basename(PRINTS[fit]), msg, *size)
              + ('' if hok else '   <== CHECK'))
        bad += (not ok) + (not hok)
    sys.exit(1 if bad else 0)
