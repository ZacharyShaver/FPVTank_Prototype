"""Variant B's non-organic parts, rebuilt as REAL SOLIDS and written to STEP.

Why this exists: `fusion/*.obj` is marching-cubes output. A flat face in it is a spray of a
few hundred near-coplanar triangles and a bore is a facet ring, so Fusion's Convert Mesh has
nothing to recognise -- decimating it (`fusion-convert/`) lowers the count without giving the
recogniser any more structure, which is why that set did not help.

But five of the seven parts never needed a mesh. Read them in tree_parts_b.py: `post`, `axle`,
`cap_minus`, `ball_plus` and `ball_minus` are pure CSG over analytic primitives -- sphere,
cylinder, box, rounded box, half-space -- with NO smooth-min blend anywhere. Only `fork` (the
nest: a bezier-swept trunk smin'd into a cup smin'd into two collars) and `roots` (four
ellipsoid lobes smin'd into a pedestal at k=6) are genuinely organic.

So those five are rebuilt here against the same parameters, through OpenCascade, and exported
as STEP. Fusion opens a STEP as a solid body directly: no Convert Mesh, no facet count, and a
bore that is still a cylinder you can select, measure and change.

Each part is checked against the SDF it came from -- surface points are sampled off the solid
and fed back through tree_parts_b's own distance function, and the volume is compared with the
meshed original. A deviation near zero means the rebuild IS the part, not a likeness of it.

    python tree_parts_b_step.py [part ...]

Needs cadquery (`pip install cadquery`), which brings the OpenCascade kernel with it. That is
a new dependency for this repo and it is a big one (~400 MB), but it is dev-machine only --
nothing on the Pi imports it, and requirements.txt stays as it is.
"""
import os, sys
import numpy as np
import cadquery as cq
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN

import tree_parts as A
import tree_parts_b as B
from step_kit import (box, rbox, cyl_x, cyl_y, cyl_z, sphere, rcyl_y, slab,
                      half_y_plus, half_y_minus, U, I, cut, fillet_all)

OUT = os.path.join(B.OUT, 'step')

# Pull the parameters straight off the SDF module -- nothing is retyped, so these solids
# cannot drift from the meshes when a number changes upstream.
H, R_IN, R_BALL, FLAT = B.H, B.R_IN, B.R_BALL, B.FLAT
BOARD_X0, BOARD_X1, BOARD_Y = B.BOARD_X0, B.BOARD_X1, B.BOARD_Y
LENS_R = B.LENS_R                        # the bezel tube is gone; the front is a plain bore
SW, SL, S2S, FIT = B.SW, B.SL, B.S2S, B.FIT
SERVO_Y0, SERVO_Y1, TAB_T, TAB_Y, ZC = B.SERVO_Y0, B.SERVO_Y1, B.TAB_T, B.TAB_Y, B.ZC
POST_R, POST_BORE, POST_IN = B.POST_R, B.POST_BORE, B.POST_IN
HORN_D_B, HORN_HUB_D, HORN_L_B = B.HORN_D_B, B.HORN_HUB_D, B.HORN_L_B
HORN_W, HORN_C = B.HORN_W, B.HORN_C
HUB_R, BRG_P_Y1, POD_P_Y1, POD_M_Y1 = B.HUB_R, B.BRG_P_Y1, B.POD_P_Y1, B.POD_M_Y1
FLANGE_R, FLANGE_REC, SCREW_R = B.FLANGE_R, B.FLANGE_REC, B.SCREW_R
AXLE_R, AXLE_Y0, AXLE_Y1, SLOT_W, SLOT_T = B.AXLE_R, B.AXLE_Y0, B.AXLE_Y1, B.SLOT_W, B.SLOT_T
M2_PILOT, M2_CLEAR, M2_HEAD = B.M2_PILOT, B.M2_CLEAR, B.M2_HEAD
M3_PILOT, M3_CLEAR, M3_HEAD = B.M3_PILOT, B.M3_CLEAR, B.M3_HEAD
BAND, TROUGH_T, SEAM_RODS = B.BAND, B.TROUGH_T, B.SEAM_RODS
# added 2026-09-19 with the seam's move to M3, the bearing retaining rings and the stiffening
SEAM_R, FACE_T, SEAM_PILOT_Y, AXLE_BORE_Y = B.SEAM_R, B.FACE_T, B.SEAM_PILOT_Y, B.AXLE_BORE_Y
BRG_RING_R0, BRG_RING_R1, BRG_P_Y0, BRG_M_Y0, BRG_M_Y1 = (
    B.BRG_RING_R0, B.BRG_RING_R1, B.BRG_P_Y0, B.BRG_M_Y0, B.BRG_M_Y1)
BALL_C = (0.0, 0.0, H)
SCREW_A = np.radians(B.SCREW_A)          # from the source, never re-typed here


# ------------------------------------------------------------------ parts
def post():
    """Fixed drive post -- shaft through the bearing, flange in the collar recess, blind pocket
    on the end that captures the trimmed horn. Mirrors tree_parts_b.post()."""
    face = POD_P_Y1 - FLANGE_REC
    # the ring that traps the bearing: fills the bore it came in through, lands on the OUTER
    # race only -- the inner race turns with the ball and a solid boss would rub on it
    ring = cut(cyl_y(0, H, BRG_RING_R1, BRG_P_Y1 - 0.1, face + 0.1),
               cyl_y(0, H, BRG_RING_R0, BRG_P_Y1 - 1, face + 1))
    s = U(cyl_y(0, H, POST_R, POST_IN, face + 0.2), ring,
          rcyl_y(0, H, FLANGE_R, face, face + FLANGE_REC, 0.6))
    cuts = [U(cyl_y(0, H, HORN_C / 2, POST_IN - 0.1, POST_IN + HORN_D_B),
              rbox((-HORN_W / 2, POST_IN - 0.1, H - HORN_L_B / 2),
                   (HORN_W / 2, POST_IN + HORN_D_B, H + HORN_L_B / 2), 1.0)),
            # relief for the 1.0 mm the spline tip stops short -- insurance, not a feature
            cyl_y(0, H, HORN_HUB_D / 2 + 0.2, POST_IN + HORN_D_B - 0.1, POST_IN + HORN_D_B + 1.5)]
    cuts += [cyl_y(SCREW_R * np.cos(a), H + SCREW_R * np.sin(a), M2_CLEAR, face - 1, POD_P_Y1 + 1)
             for a in SCREW_A]
    return cut(s, *cuts)


def axle():
    """Plain idler at the -Y end of the tilt axis, with the flat that clears the camera board."""
    s = cyl_y(0, H, AXLE_R, AXLE_Y0, AXLE_Y1)
    # the flat: the SDF cuts the quadrant x >= BOARD_X0-0.4 AND y >= -FLAT-0.1, so the
    # bearing journal outboard of the ball stays fully round
    s = cut(s, box((BOARD_X0 - 0.4, -FLAT - 0.1, -1e3), (1e3, 1e3, 1e3)))
    slot = box((-SLOT_W / 2, AXLE_Y0 + 1.5, H - SLOT_T / 2),
               (SLOT_W / 2, AXLE_Y1 + 5, H + SLOT_T / 2))
    return cut(s, slot)


def cap_minus():
    """Flush plate that closes the -Y collar and traps the axle."""
    face = POD_M_Y1
    ring = cut(cyl_y(0, H, BRG_RING_R1, face + FLANGE_REC - 0.1, BRG_M_Y1 + 0.1),
               cyl_y(0, H, BRG_RING_R0, face + FLANGE_REC - 1, BRG_M_Y1 + 1))
    s = U(rcyl_y(0, H, FLANGE_R, face, face + FLANGE_REC, 0.6), ring)
    return cut(s, *[cyl_y(SCREW_R * np.cos(a), H + SCREW_R * np.sin(a), M2_CLEAR,
                          face - 1, face + FLANGE_REC + 1) for a in SCREW_A])


def _ball_body():
    """The shared ball: spherical shell, truncated at both flats, plus every boss welded to it."""
    inner = sphere(R_IN + 0.6, BALL_C)          # the SDF's `d - R_IN - 0.6`: keeps a boss
    parts = [I(cut(sphere(R_BALL, BALL_C), sphere(R_IN, BALL_C)), slab(1, -FLAT, FLAT))]
    for sgn in (1.0, -1.0):                      # the two rails the camera board slides into
        y0, y1 = sgn * (BOARD_Y - 3.0), sgn * (BOARD_Y + 2.0)
        parts.append(I(rbox((BOARD_X0 - 1.5, min(y0, y1), H - 26.0),
                            (BOARD_X1 + 1.5, max(y0, y1), H + 26.0), 1.0), inner))
    for rx, rz in SEAM_RODS:
        parts.append(I(cyl_y(rx, H + rz, SEAM_R, -FLAT, FLAT), inner))
    face_r = np.sqrt(R_BALL ** 2 - FLAT ** 2)
    parts += [cyl_y(0, H, face_r, FLAT - FACE_T, FLAT),         # +Y flat face plate
              cyl_y(0, H, face_r, -FLAT, -FLAT + FACE_T),       # -Y flat face plate
              cyl_y(0, H, HUB_R, FLAT - 2.0, BRG_P_Y1 - 0.2),   # +Y hollow stub, rides the 6704
              cyl_y(0, H, 13.0, -FLAT, -19.0)]                  # -Y axle socket hub
    # The floor the tilt servo's base lands on. It stops at the camera board's face, NOT at +24 --
    # it used to run the full width and pass straight through the board (the bar Zach could see
    # crossing the middle). It still reaches -24, which is how it stays attached: the (-23, +8)
    # seam rod carries it back to the shell.
    parts.append(I(rbox((-29.5, SERVO_Y0 - 3.0, ZC - 4.0), (BOARD_X0 - 0.1, SERVO_Y0, ZC + 4.0), 1.0),
                   inner))
    return U(*parts)


def _ball_cuts(side):
    """Every cut through the ball. Two of them are side-dependent in the SDF's `np.where`:
    the tab recess is +Y only, and a seam rod is a clearance bore with a counterbore in the
    +Y half but a thread-forming pilot in the -Y half."""
    cuts = [cyl_x(0, H, LENS_R, 0.0, 44.0),
            cyl_x(2.7, H + 20.5, 3.0, 14.0, 44.0),
            box((-SW / 2 - FIT, SERVO_Y0, H - S2S - FIT),
                (SW / 2 + FIT, SERVO_Y1 + FIT, H + SL - S2S + FIT))]
    if side > 0:
        cuts.append(box((-SW / 2 - FIT, TAB_Y - FIT, ZC - A.TAB_SPAN / 2 - FIT),
                        (SW / 2 + FIT, TAB_Y + TAB_T + FIT, ZC + A.TAB_SPAN / 2 + FIT)))
    cuts += [cyl_y(0, H, POST_BORE, SERVO_Y1 - 0.6, FLAT + 10.5),
             cyl_y(0, H, AXLE_R + 0.1, -FLAT - 1, AXLE_BORE_Y),
             box((-R_BALL - 2, -BAND, H - TROUGH_T - 1.0), (-R_IN + 4, BAND, H - 1.0))]
    for sgn in (1.0, -1.0):                      # the groove the board's last edge sits in
        # 3.2, not 2.6: the rail starts at BOARD_Y - 3.0, so a slot starting at 2.6 left 0.4 mm
        # of rail inboard of its own opening -- in the path of the board it holds.
        y0, y1 = sgn * (BOARD_Y - 3.2), sgn * (BOARD_Y + 0.3)
        cuts.append(box((BOARD_X0 - 0.15, min(y0, y1), H - 19.5),
                        (BOARD_X1 + 0.15, max(y0, y1), H + 19.5)))
    for rx, rz in SEAM_RODS:
        y_out = np.sqrt(max(R_BALL ** 2 - rx ** 2 - rz ** 2, 1.0))
        if side > 0:
            cuts += [cyl_y(rx, H + rz, M3_CLEAR, -1, FLAT),
                     cyl_y(rx, H + rz, M3_HEAD, y_out - 2.2, FLAT)]
        else:
            cuts.append(cyl_y(rx, H + rz, M3_PILOT, SEAM_PILOT_Y, 1))
    return cuts


def ball_plus():
    return cut(I(_ball_body(), half_y_plus()), *_ball_cuts(+1))


def ball_minus():
    return cut(I(_ball_body(), half_y_minus()), *_ball_cuts(-1))


PARTS = {'post': post, 'axle': axle, 'cap_minus': cap_minus,
         'ball_plus': ball_plus, 'ball_minus': ball_minus}

# fork and roots are NOT here, and that is the honest line, not an omission: `fork` is a
# bezier-swept trunk smoothly blended into a cup and two collars, `roots` is four ellipsoid
# lobes blended into a pedestal at k=6. A smooth-min is not a fillet and there is no analytic
# solid to rebuild. They go the mesh route -- see step_mesh_prep.py.
ORGANIC = ['fork', 'roots']


# ------------------------------------------------------------------ verification
# Two checks, because the obvious one does not bite on its own.
#
# The obvious one is fusion_convert.py's: sample the surface, ask the SDF how far off it is.
# On a BREP that check is close to VACUOUS, and it was caught being so. OCC puts most of a
# tessellation's vertices on face BOUNDARIES, and a bore straight through a plate has both of
# its boundaries lying on faces the part already had -- so every vertex it contributes sits
# exactly on the original surface. A deliberately bogus Ø4 bore through the post's flange
# removed 22.6 mm3 of real material and the vertex check still read 0.0000, max and all.
#
# So the check that decides is `agreement`: sample the bounding box and ask BOTH the solid and
# the SDF whether each point is inside. That sees material wherever it is, not just where a
# vertex happened to land. `deviation` is kept, sampling triangle INTERIORS as well as corners,
# because it still answers a different question cheaply -- is the surface where it should be.
def deviation(solid, sdf, tol=0.02):
    """99.9th percentile of |SDF| over the solid's surface, sampled at triangle corners AND
    interiors. Informational only -- do NOT gate on it, for two opposite reasons.

    Corners alone read a perfect 0.0000 on all five parts, and would read it on a wrong part
    too (see above). Adding interiors makes it bite, but gives it a FLOOR that has nothing to
    do with the geometry: a flat triangle chords inside a curved face, so the balls measure
    ~0.09 and the mostly-planar post ~0.005 on solids that are both exact. Those triangles are
    not in the STEP anyway -- the file stores the analytic sphere; the mesh only exists here to
    sample it. `agreement` is the check that decides.
    """
    verts, tris = solid.tessellate(tol)
    V = np.array([[v.x, v.y, v.z] for v in verts])
    T = np.array(tris)
    pts = [V]
    if len(T):
        a, b, c = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
        for w in ((1 / 3, 1 / 3, 1 / 3), (0.6, 0.2, 0.2), (0.2, 0.6, 0.2), (0.2, 0.2, 0.6)):
            pts.append(w[0] * a + w[1] * b + w[2] * c)
    P = np.vstack(pts)
    d = np.abs(sdf((P[:, 0], P[:, 1], P[:, 2]), True))
    return np.percentile(d, 99.9), d.max(), len(P)


def agreement(solid, sdf, n=160000, seed=0, pad=0.5):
    """Monte-Carlo set difference between the rebuilt solid and the SDF it came from.

    Returns the volume the two disagree over, in mm3. Zero means the STEP encloses the same
    space as the field -- not a likeness of it, the same solid. Any feature that moved, grew,
    vanished or was never cut shows up here as volume, wherever it is.
    """
    bb = solid.BoundingBox()
    lo = np.array([bb.xmin, bb.ymin, bb.zmin]) - pad
    hi = np.array([bb.xmax, bb.ymax, bb.zmax]) + pad
    P = np.random.default_rng(seed).uniform(lo, hi, (n, 3))
    in_sdf = sdf((P[:, 0], P[:, 1], P[:, 2]), True) < 0
    cl = BRepClass3d_SolidClassifier(solid.wrapped)
    in_brep = np.empty(n, bool)
    for i in range(n):
        cl.Perform(gp_Pnt(P[i, 0], P[i, 1], P[i, 2]), 1e-7)
        in_brep[i] = cl.State() == TopAbs_IN
    mism = int((in_sdf ^ in_brep).sum())
    bbvol = float(np.prod(hi - lo))
    return mism / n * bbvol, bbvol / n          # (disagreement mm3, mm3 per sample point)


def mesh_volumes():
    """Volumes the meshed originals reported, for a second, independent check."""
    out = {}
    path = os.path.join(B.OUT, 'mesh_report.txt')
    if not os.path.exists(path):
        return out
    for line in open(path):
        if line.startswith('fusion/') and 'vol=' in line:
            out[line.split('/')[1].split('.obj')[0]] = float(line.split('vol=')[1].split()[0])
    return out


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    names = [a for a in sys.argv[1:] if a in PARTS] or list(PARTS)
    vols = mesh_volumes()
    print('%-11s %5s %5s %9s %11s %s'
          % ('part', 'faces', 'edges', 'surf dev', 'disagree', 'volume vs mesh'))
    print('-' * 80)
    bad = 0
    for name in names:
        fillet_all.last = 'ok'
        solid = PARTS[name]()
        note = '' if fillet_all.last == 'ok' else '  [fillet %s]' % fillet_all.last
        sdf = getattr(B, name)
        p999, dmax, _ = deviation(solid, sdf)
        dis, res = agreement(solid, sdf)
        v = solid.Volume() / 1000.0
        vm = vols.get(name)
        cmp = '%5.2f cm3' % v + ('  (mesh %.2f, %+.1f%%)' % (vm, 100 * (v - vm) / vm) if vm else '')
        cq.exporters.export(solid, os.path.join(OUT, name + '.step'))
        flag = ''
        if dis > 2.0 or (vm and abs(v - vm) / vm > 0.02):
            flag = '   <-- CHECK'
            bad += 1
        print('%-11s %5d %5d %9.4f %8.2f mm3 %s%s%s'
              % (name, len(solid.Faces()), len(solid.Edges()), p999, dis, cmp, note, flag))
    print('-' * 80)
    print('disagree = volume the STEP and the SDF classify differently; resolution ~%.2f mm3.'
          % res)
    print('            This is the check that decides, and it was negative-controlled:')
    print('            a bogus bore reads 21.99, a MISSING screw hole 7.01, a 0.3 mm')
    print('            oversize shaft 344.12 -- none of which surface deviation catches.')
    print('surf dev  = informational. Its floor is chord sag where a flat triangle cuts')
    print('            inside a curved face, so a curvy part reads higher while being exact.')
    print('%d/%d clean. STEP written to %s' % (len(names) - bad, len(names), OUT))
    print('Organic, no analytic rebuild: %s -- mesh route instead' % ', '.join(ORGANIC))
