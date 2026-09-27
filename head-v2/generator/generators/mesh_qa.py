"""Re-check every file in tree-parts/ and rewrite mesh_report.txt."""
import glob, os
import pymeshlab as ml
import tree_parts as T

lines = ['Mesh QA for tree-parts/ -- generators/tree_parts.py, then print_post.py', '']
for path in sorted(glob.glob(os.path.join(T.OUT, 'print', '*.stl'))) + sorted(glob.glob(os.path.join(T.OUT, 'fusion', '*.obj'))):
    with T.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path); ok, msg = T.report(ms)
    rel = os.path.relpath(path, T.OUT).replace(os.sep, '/')
    lines.append(rel.ljust(30) + msg + ('' if ok else '   <-- CHECK'))
open(os.path.join(T.OUT, 'mesh_report.txt'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
