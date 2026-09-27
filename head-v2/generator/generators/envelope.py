"""Overall head envelope from the assembled part meshes."""
import glob, os
import numpy as np, pymeshlab as ml
import tree_parts as T
lo = np.array([1e9] * 3); hi = -lo
for f in sorted(glob.glob(os.path.join(T.OUT, 'fusion', '*.obj'))):
    if f.endswith('_blank.obj'):
        continue
    with T.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(f)
    v = ms.current_mesh().vertex_matrix()
    print(os.path.basename(f).ljust(16), v.min(0).round(1), v.max(0).round(1))
    lo = np.minimum(lo, v.min(0)); hi = np.maximum(hi, v.max(0))
print('ENVELOPE', lo.round(1), hi.round(1), 'size', (hi - lo).round(1))
