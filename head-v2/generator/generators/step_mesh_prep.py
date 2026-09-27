"""The two parts that CANNOT be rebuilt as solids, prepared so Fusion's Convert Mesh has the
easiest possible job -- plus the feature table for putting back what the blank leaves out.

`fork` and `roots` are the only genuinely organic parts in variant B. The nest is a bezier-swept
trunk smooth-min'd into a cup smooth-min'd into two collars; roots is four ellipsoid lobes
smooth-min'd into a pedestal at k=6. A smooth-min is not a fillet -- it pulls BOTH surfaces
toward each other well away from the joint -- so there is no analytic solid to rebuild, and
tree_parts_b_step.py correctly refuses to pretend otherwise.

What is left is to make the mesh easy, and the leverage there is NOT face count. It is the
small analytic features. A Ø1.7 pilot hole in a 6000-face mesh is a ragged 12-sided prism that
Convert Mesh has to recognise, and it is also the thing most likely to move when a measurement
lands. So the blank drops every analytic feature -- bearing seats, bores, flange recesses,
pilots, the pan horn pocket -- and KEEPS the two that could never be redrawn by hand: the
ribbon trough, which follows a bezier down the trunk, and the rolling-loop track, an arc band
behind the ball. Those are organic; the rest goes in features.md and is re-cut natively in
Fusion, where it stays editable when a number changes.

    python step_mesh_prep.py [fork|roots ...]

Writes tree-parts-b/fusion-solid/<part>_blank.obj and tree-parts-b/features.md.
"""
import os, sys
import numpy as np
from skimage import measure

import tree_parts as A
import tree_parts_b as B
from tree_parts import sample, project, unfold, decimate, report, quiet, U

OUT = os.path.join(B.OUT, 'fusion-solid')

# Face-count targets. Lower than fusion_convert.py's because a blank has less to describe --
# there are no bores left whose facet rings have to survive decimation.
TARGET = {'fork': 6000, 'roots': 4000}


# ------------------------------------------------------------------ the blanks
def fork_blank(p, features=True):
    """The nest with every ANALYTIC feature left out and both ORGANIC cuts kept.

    B.fork(p, False) already stops before the feature cuts, so the ribbon trough and the
    rolling-loop track have to be put back deliberately -- they are not features anyone would
    re-draw in Fusion, they are the shape.
    """
    s = B.fork(p, False)
    organic = U(B.trough(p, B.TROUGH_W / 2, B.TROUGH_T / 2), B.track(p))
    return np.maximum(s, -organic)


def roots_blank(p, features=True):
    """roots is A.roots unchanged in variant B -- same function, same parameters. All of its
    cuts are analytic, so the blank is simply the body."""
    return A.roots(p, False)


BLANKS = {'fork': fork_blank, 'roots': roots_blank}


# ------------------------------------------------------------------ feature table
def _f(x):
    return ('%.2f' % x).rstrip('0').rstrip('.')


def fork_features():
    d = lambda r: 'Ø%s' % _f(2 * r)
    rows = [
        ('+Y bearing seat (6704)', 'tilt axis, Y %s..%s' % (_f(B.BRG_P_Y0), _f(B.BRG_P_Y1)),
         '%s, teardrop roof' % d(B.BRG_OD / 2)),
        ('+Y ball-stub clearance', 'tilt axis, Y %s..%s' % (_f(B.POD_Y0 - 1), _f(B.BRG_P_Y0)),
         d(B.HUB_R + 0.45)),
        ('+Y post bore', 'tilt axis, Y %s..%s' % (_f(B.BRG_P_Y1), _f(B.POD_P_Y1 + 1)),
         d(B.POST_R + 0.3)),
        ('+Y flange recess', 'tilt axis, Y %s..%s' % (_f(B.POD_P_Y1 - B.FLANGE_REC), _f(B.POD_P_Y1)),
         '%s × %s deep -- post flange sits flush' % (d(B.FLANGE_R + 0.25), _f(B.FLANGE_REC))),
        ('+Y flange pilots ×3 (M2 thread-forming)',
         'r %s at %s (from +X toward +Z), from Y %s inboard' % (_f(B.SCREW_R), '/'.join('%g°' % x for x in B.SCREW_A), _f(B.POD_P_Y1)),
         '%s × 9' % d(B.M2_PILOT)),
        ('-Y bearing seat (6704)', 'tilt axis, Y %s..%s' % (_f(B.BRG_M_Y1), _f(B.BRG_M_Y0)),
         '%s, teardrop roof' % d(B.BRG_OD / 2)),
        ('-Y axle bore, inboard', 'tilt axis, Y %s..%s' % (_f(B.BRG_M_Y1), _f(-B.POD_Y0 + 1.5)),
         d(B.AXLE_R + 0.45)),
        ('-Y axle bore, outboard', 'tilt axis, Y %s..%s' % (_f(B.POD_M_Y1 - 1), _f(B.BRG_M_Y1)),
         d(B.AXLE_R + 0.45)),
        ('-Y flange recess', 'tilt axis, Y %s..%s' % (_f(B.POD_M_Y1), _f(B.POD_M_Y1 + B.FLANGE_REC)),
         '%s × %s deep -- cap_minus sits flush' % (d(B.FLANGE_R + 0.25), _f(B.FLANGE_REC))),
        ('-Y flange pilots ×3 (M2 thread-forming)',
         'r %s at %s (from +X toward +Z), from Y %s inboard' % (_f(B.SCREW_R), '/'.join('%g°' % x for x in B.SCREW_A), _f(B.POD_M_Y1)),
         '%s × 9' % d(B.M2_PILOT)),
        ('Pan horn pocket, up from the underside',
         'X ±%s, Y ±%s, Z %s..%s' % (_f(B.HORN_L / 2), _f(B.HORN_W / 2), _f(B.BASE_Z), _f(B.BASE_Z + B.HORN_D)),
         'plus %s boss clearance on the pan axis; corners r1' % d(B.HORN_C / 2)),
        ('Pan shaft bore', 'pan axis (X0 Y0), Z %s..%s' % (_f(B.BASE_Z), _f(B.BASE_Z + 14)),
         d(2.8)),
        ('Ribbon trough — ALREADY IN THE BLANK, do not re-cut',
         'bezier from the track exit down the trunk, Y centred %s' % _f(B.TROUGH_Y),
         '%s × %s section' % (_f(B.TROUGH_W), _f(B.TROUGH_T))),
        ('Rolling-loop track — ALREADY IN THE BLANK, do not re-cut',
         '%s° to %s° from straight back, Y ±%s' % (_f(B.TRACK_ANG_LO), _f(B.TRACK_ANG_HI), _f(B.BAND)),
         '%s mm gap outside the ball' % _f(B.TRACK_GAP)),
    ]
    return rows


def write_features():
    path = os.path.join(B.OUT, 'features.md')
    L = ['# Variant B: feature table for the two MESH parts', '',
         'Only `fork` and `roots` are here. The other five parts -- `post`, `axle`, `cap_minus`,',
         '`ball_plus`, `ball_minus` -- are not meshes at all any more: they are real solids in',
         '`step/`, with every feature already cut and editable. Nothing below applies to them.',
         '',
         'Frame: mm, X forward, Y along the tilt axis (+Y = post side), Z up from the deck top.',
         'Tilt axis at X 0, Z %s. Pan axis is the Z axis.' % _f(B.H), '',
         'Workflow: import `fusion-solid/<part>_blank.obj`, convert it to a body, then cut these',
         'natively so they stay editable when a measurement moves. Two rows are marked ALREADY IN',
         'THE BLANK -- they are organic, they could not be redrawn by hand, and they are already there.',
         '', 'Generated by `generators/step_mesh_prep.py`.', '']
    for part, rows in (('fork', fork_features()),
                       ('roots', A.FEATURES['roots'])):
        L += ['## %s' % part, '', '| Feature | Where | Size / note |', '|---|---|---|']
        L += ['| %s | %s | %s |' % r for r in rows]
        L += ['']
    open(path, 'w', encoding='utf-8').write('\n'.join(L))
    return path


# ------------------------------------------------------------------ build
def dev(fn, V):
    """Same accuracy metric fusion_convert.py uses: how far the mesh sits off the true surface."""
    return np.percentile(np.abs(fn((V[:, 0], V[:, 1], V[:, 2]), True)), 99.9)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    names = [a for a in sys.argv[1:] if a in BLANKS] or list(BLANKS)
    print('%-16s %16s %9s  %s' % ('blank', 'faces', 'max dev', 'clean?'))
    print('-' * 72)
    for name in names:
        fn = BLANKS[name]
        _, lo, hi, step, _, _ = B.PARTS[name]
        vol = sample(lambda P: fn(P, True), lo, hi, step)
        v, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(step,) * 3)
        v_raw = v + np.array(lo)
        v = project(lambda P: fn(P, True), v_raw, step)
        with quiet():
            v = unfold(v, v_raw, faces)
            n0 = len(faces)
            ms, _ = decimate(v, faces, TARGET[name])
            ok, msg = report(ms)
            V = ms.current_mesh().vertex_matrix()
            ms.save_current_mesh(os.path.join(OUT, name + '_blank.obj'), save_vertex_normal=False)
        n1 = ms.current_mesh().face_number()
        print('%-16s %7d -> %-6d %8.3f  %s' % (name + '_blank', n0, n1, dev(fn, V),
                                               'OK' if ok else msg))
    print('-' * 72)
    print('written to %s' % OUT)
    print('feature table: %s' % write_features())
