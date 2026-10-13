"""Print meshes for the pan coil's printed parts (2026-09-27). pan_coil_b.py only writes viewer
meshes (fusion/*.obj, decimated hard; its well and bay carried self-intersections), so the parts had
never been print files. This builds each one at print resolution, cleans it to watertight, manifold,
one body, zero self-intersections, and lays it on the bed whichever way up leaves the least
unsupported overhang -- measured on the mesh, both ways, not guessed.

    python pan_coil_b_print.py [part ...]      # default: drum base floor gear_in gear_out

Writes ../pan-coil-b/print/<part>.stl (untracked). The bearing (6809) and the servo (MG90D) are
bought, and the ribbon is the real cable, so none of them is printed.
"""
import os, sys
import numpy as np
from skimage import measure
import pymeshlab as ml
import tree_parts as T
from tree_parts import sample, project, unfold, decimate, report, quiet, mesh_set, tidy, is_clean
import pan_coil_b as P

# 2026-09-27: well + bay print fused as `base`, with the floor and the drum's gear as their own parts.
# Superseded: 'well', 'bay' printed separately -- the gears could not get into the closed bay.
PRINTED = ['drum', 'base', 'floor', 'gear_in', 'gear_out', 'tab_block', 'shelf_ring']   # shelf_ring: set 7
if not P.RING_PART:   # set 11 (2026-10-12): the shelf ring is part of the base again
    PRINTED.remove('shelf_ring')
OUT = os.path.join(P.OUT, 'print')
MAX_STEP = 0.28                    # finer than the viewer's 0.30-0.34 where the part table is coarser
OVERHANG = np.cos(np.radians(45))  # a face pointing down more steeply than 45 degrees needs support
# Parts whose way up is set by a fit, not by the overhang count. Set 6's input gear (2026-10-03) takes the
# servo's spline in a press bore: bottom face down, the bore opens upward and its lip bridges the screw head's
# counterbore, as post v3's does (flange down). Flipped scores less overhang, but its lip would bridge over
# the spline bore, and a support in there spoils the press.
WAY_UP = {'gear_in': 'as modelled'}


def score(V, F):
    """(overhang area needing support, area resting on the bed), both mm2."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    n = np.cross(b - a, c - a); area = np.linalg.norm(n, axis=1) / 2
    nz = n[:, 2] / np.maximum(2 * area, 1e-12)
    zc = (a[:, 2] + b[:, 2] + c[:, 2]) / 3
    z0 = V[:, 2].min()
    bed = (nz < -0.99) & (zc < z0 + 0.05)
    over = (nz < -OVERHANG) & ~bed
    return area[over].sum(), area[bed].sum()


def clean(ms):
    """print_post.py's loop: cut out any folded triangles with a ring, refill, re-tidy."""
    for _ in range(4):
        if T.self_intersections(ms) == 0:
            break
        ms.compute_selection_by_self_intersections_per_face()
        ms.apply_selection_dilatation()
        ms.meshing_remove_selected_vertices_and_faces()
        ms.meshing_close_holes(maxholesize=60, newfaceselected=False)
        ms.set_selection_none()
    tidy(ms)
    return ms


def build(name):
    if name == 'gear_in' and P.HORN_GEAR:   # set 9: an exact solid with the horn's exact pocket, not this mesh
        print('gear_in  skipped: set 9 builds it exactly, python head-v2/fixes/gear_horn_set9.py', flush=True)
        return True
    fn, lo, hi, step = P.PARTS[name][:4]
    step = min(step, MAX_STEP)
    f = lambda Q: fn(Q, True)
    vol = sample(f, lo, hi, step)
    v, faces, _, _ = measure.marching_cubes(vol, 0.0, spacing=(step,) * 3)
    v_raw = v + np.array(lo)
    v = project(f, v_raw, step)
    with quiet():
        v = unfold(v, v_raw, faces)
        ms, _ = decimate(v, faces, 250000)
        ms = clean(ms)
    V, F = ms.current_mesh().vertex_matrix(), ms.current_mesh().face_matrix()
    ways = {'as modelled': V, 'flipped': V * np.array([1, -1, -1])}
    scored = {k: score(W, F) for k, W in ways.items()}
    best = WAY_UP.get(name) or min(scored, key=lambda k: (round(scored[k][0], 0), -scored[k][1]))
    W = ways[best]
    W = W - np.array([(W[:, 0].min() + W[:, 0].max()) / 2, (W[:, 1].min() + W[:, 1].max()) / 2, W[:, 2].min()])
    with quiet():
        pm = mesh_set(W, F)
        ok, msg = report(pm)
        pm.save_current_mesh(os.path.join(OUT, name + '.stl'), binary=True)
    size = W.max(0) - W.min(0)
    alt = [k for k in ways if k != best][0]
    print('%-8s %s%s' % (name, msg, '' if ok else '   <-- CHECK'), flush=True)
    print('         %s: overhang %.0f mm2, on the bed %.0f mm2 (%s: %.0f / %.0f)   %.1f x %.1f x %.1f mm'
          % (best, scored[best][0], scored[best][1], alt, scored[alt][0], scored[alt][1], *size), flush=True)
    return ok


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    names = [a for a in sys.argv[1:] if a in P.PARTS] or PRINTED
    bad = sum(not build(n) for n in names)
    sys.exit(1 if bad else 0)
