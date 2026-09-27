"""Post-pass for a print/ directory: bring every STL to <=250k faces and zero self-intersections.

    python print_post.py          # variant A, tree-parts/print
    python print_post.py b        # variant B, tree-parts-b/print

Run after tree_parts.py / tree_parts_b.py.
"""
import os, sys, glob
import numpy as np
import tree_parts as T

OUT = T.OUT
if 'b' in sys.argv[1:]:
    import tree_parts_b as B
    OUT = B.OUT

for path in sorted(glob.glob(os.path.join(OUT, 'print', '*.stl'))):
    import pymeshlab as ml
    with T.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path); T.tidy(ms)
        best = None
        for target in (250000, 220000, 280000, 180000):
            m2 = ml.MeshSet(); m2.add_mesh(ms.current_mesh())
            if m2.current_mesh().face_number() > target:
                m2.meshing_decimation_quadric_edge_collapse(targetfacenum=target, qualitythr=0.8, preserveboundary=True,
                                                            preservenormal=True, preservetopology=True, optimalplacement=False,
                                                            planarquadric=True, planarweight=0.002, autoclean=True)
            for _ in range(4):                       # a handful of folded triangles: cut out with a ring, refill
                if T.self_intersections(m2) == 0:
                    break
                m2.compute_selection_by_self_intersections_per_face()
                m2.apply_selection_dilatation()
                m2.meshing_remove_selected_vertices_and_faces()
                m2.meshing_close_holes(maxholesize=60, newfaceselected=False)
                m2.set_selection_none()
            T.tidy(m2)
            if T.is_clean(m2):
                best = m2; break
        if best:
            best.save_current_mesh(path, binary=True)
        ok, msg = T.report(best or ms)
        V = (best or ms).current_mesh().vertex_matrix()
    size = V.max(0) - V.min(0)
    print(os.path.basename(path).ljust(18), msg, '  bed %.1f x %.1f, %.1f tall' % tuple(size),
          '' if best else '  <-- left as is')
