"""Rewrite tree-parts-b/mesh_report.txt from the files that are actually on disk,
after print_post.py has had its pass. Reports both the print STLs and the Fusion OBJs."""
import os, glob
import numpy as np
import pymeshlab as ml
import tree_parts as T
import tree_parts_b as B

lines, lo_all, hi_all = [], np.array([1e9] * 3), np.array([-1e9] * 3)
for sub, pat in (('print', '*.stl'), ('fusion', '*.obj')):
    for path in sorted(glob.glob(os.path.join(B.OUT, sub, pat))):
        with T.quiet():
            ms = ml.MeshSet(); ms.load_new_mesh(path)
            ok, msg = T.report(ms)
            V = ms.current_mesh().vertex_matrix()
        size = V.max(0) - V.min(0)
        extra = '  bed %.1f x %.1f, %.1f tall' % tuple(size) if sub == 'print' else ''
        # A part that blew past its decimation target did not decimate -- the mesher choked on
        # something degenerate. Both coincident-face bugs showed up here first, as a face count
        # nobody looked at, so it is a hard flag now rather than a number in a column.
        name = os.path.splitext(os.path.basename(path))[0]
        target = B.PARTS[name][4] if name in B.PARTS else None
        n = ms.current_mesh().face_number()
        stalled = target is not None and sub == 'fusion' and n > target * 1.2
        if stalled:
            extra += '   <-- DECIMATOR STALLED: %d faces against a %d target' % (n, target)
        lines.append(('%s/%s' % (sub, os.path.basename(path))).ljust(28) + msg + extra +
                     ('' if ok and not stalled else '   <-- CHECK'))
        if sub == 'fusion':
            lo_all = np.minimum(lo_all, V.min(0)); hi_all = np.maximum(hi_all, V.max(0))
        print(lines[-1], flush=True)

env = 'ENVELOPE (assembled) %s -> %s  size %s' % (lo_all.round(1), hi_all.round(1), (hi_all - lo_all).round(1))
print(env)
open(os.path.join(B.OUT, 'mesh_report.txt'), 'w').write('\n'.join(lines) + '\n' + env + '\n')
