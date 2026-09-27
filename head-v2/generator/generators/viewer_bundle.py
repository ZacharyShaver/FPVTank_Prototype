"""Rebuild tree-parts/viewer_parts.js from the current fusion/*.obj, without re-meshing."""
import os, json, base64
import numpy as np, pymeshlab as ml
import tree_parts as T

bundle = {}
for name in T.PARTS:
    path = os.path.join(T.OUT, 'fusion', f'{name}.obj')
    with T.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path)
    m = ms.current_mesh()
    bundle[name] = {'v': base64.b64encode(m.vertex_matrix().astype('<f4').tobytes()).decode(),
                    'f': base64.b64encode(m.face_matrix().astype('<u4').tobytes()).decode()}
    print(name, m.vertex_number(), 'verts', m.face_number(), 'faces')
open(os.path.join(T.OUT, 'viewer_parts.js'), 'w').write('window.TREE=' + json.dumps(bundle) + ';')
