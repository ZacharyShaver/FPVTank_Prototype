"""Make a Fusion-conversion set: the same parts, decimated to a face count Convert Mesh can
actually handle, with the accuracy cost of that reduction MEASURED against the source SDF.

Reads fusion/*.obj -- it does not re-sample, so this takes seconds, not 25 minutes.

    python fusion_convert.py
"""
import os, numpy as np, pymeshlab as ml
import tree_parts_b as B
from tree_parts import quiet, decimate, report, mesh_set

# Prismatic parts are left alone: they are already low and they convert well as they are.
TARGET = {'fork': 8000, 'ball_plus': 6000, 'ball_minus': 6000, 'roots': 6000,
          'post': 5000, 'axle': 4000, 'cap_minus': 4000}
OUT = os.path.join(B.OUT, 'fusion-convert')
os.makedirs(OUT, exist_ok=True)

def dev(fn, V):
    return np.percentile(np.abs(fn((V[:, 0], V[:, 1], V[:, 2]), True)), 99.9)

print('%-12s %14s %9s  %s' % ('part', 'faces', 'max dev', 'clean?'))
for name, (fn, lo, hi, step, target, _) in B.PARTS.items():
    with quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(os.path.join(B.OUT, 'fusion', name + '.obj'))
        n0 = ms.current_mesh().face_number()
        t = TARGET[name]
        if t < n0:
            ms, _ = decimate(ms.current_mesh().vertex_matrix(), ms.current_mesh().face_matrix(), t)
        ok, msg = report(ms)
        V = ms.current_mesh().vertex_matrix()
        ms.save_current_mesh(os.path.join(OUT, name + '.obj'), save_vertex_normal=False)
    n1 = ms.current_mesh().face_number()
    flags = [w for w in ('watertight=True', 'manifold=True', 'bodies=1', 'self-int=0') if w in msg]
    print('%-12s %6d -> %-6d %8.3f  %s' % (name, n0, n1, dev(fn, V), 'OK' if len(flags) == 4 else msg))
