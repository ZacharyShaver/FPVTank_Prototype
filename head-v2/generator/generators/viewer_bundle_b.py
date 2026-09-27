"""Rebuild tree-parts-b/viewer_parts_b.js from the current fusion/*.obj."""
import os, json, base64
import pymeshlab as ml
import tree_parts as T
import tree_parts_b as B

bundle = {}
for name in B.PARTS:
    with T.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(os.path.join(B.OUT, 'fusion', f'{name}.obj'))
    m = ms.current_mesh()
    bundle[name] = {'v': base64.b64encode(m.vertex_matrix().astype('<f4').tobytes()).decode(),
                    'f': base64.b64encode(m.face_matrix().astype('<u4').tobytes()).decode()}
    print(name, m.face_number(), 'faces')
open(os.path.join(B.OUT, 'viewer_parts_b.js'), 'w').write('window.TREEB=' + json.dumps(bundle) + ';')
