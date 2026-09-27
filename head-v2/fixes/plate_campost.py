"""The full plate with the camera posts (2026-09-26): both halves (ball_plus with the camera tubes), post v3,
4 seam pins and the 2 camera posts, one object per part, the pin placed four times. Written by hand from
the print meshes, like plate3mf.py; every object is read back through the mesh report.
Writes out/print/plate_full_camposts.3mf. The older plate (plate3mf.py) is superseded but still built:
the rev-2 checks read it."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import re, zipfile
import numpy as np
import pymeshlab as ml
import tree_parts as TP_
PIN = 'snap_pin_stop_medium'            # Zach's pick (2026-09-27, docs/decisions.md)
CAM = 'medium'                          # likewise for the camera posts

def load_mesh(path):
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path); ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
    return ms.current_mesh().vertex_matrix().copy(), ms.current_mesh().face_matrix().copy()

if __name__ == '__main__':
    P = config.PRINT
    objs = [('ball_plus_camposts', [(-36.0, 28.0)]), ('ball_minus', [(36.0, 28.0)]), ('post_v3', [(-34.0, -42.0)]),
            (PIN, [(8.0 + 9.0 * k, -42.0) for k in range(4)]),
            ('camera_post_upper_' + CAM, [(54.0, -36.0)]), ('camera_post_lower_' + CAM, [(54.0, -48.0)])]
    res, build, boxes = [], [], []
    for i, (nm, spots) in enumerate(objs, 1):
        V, F = load_mesh(os.path.join(P, nm + '.stl'))
        c = np.array([(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, V[:, 2].min()])
        V = V - c
        vs = ''.join('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % tuple(v) for v in V)
        ts = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in F)
        res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (i, nm, vs, ts))
        for x, y in spots:
            build.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.3f %.3f 0"/>' % (i, x, y))
            boxes.append((nm, V[:, 0].min() + x, V[:, 0].max() + x, V[:, 1].min() + y, V[:, 1].max() + y))
    clash = 0
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            A, Bx = boxes[a], boxes[b]
            if A[1] < Bx[2] and Bx[1] < A[2] and A[3] < Bx[4] and Bx[3] < A[4]:
                print('  !! footprints overlap:', A[0], Bx[0]); clash += 1
    xs = [v for bb in boxes for v in bb[1:3]]; ys = [v for bb in boxes for v in bb[3:5]]
    print('plate footprint %.0f x %.0f mm, %d overlaps' % (max(xs) - min(xs), max(ys) - min(ys), clash))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>%s</resources><build>%s</build></model>'
             % (''.join(res), ''.join(build)))
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    path = os.path.join(P, 'plate_full_camposts.3mf')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('3D/3dmodel.model', model)
    xml = zipfile.ZipFile(path).read('3D/3dmodel.model').decode()
    for m in re.finditer(r'<object id="(\d+)" type="model" name="([^"]+)"><mesh><vertices>(.*?)</vertices><triangles>(.*?)</triangles>', xml):
        V = np.array(re.findall(r'x="([-\d.]+)" y="([-\d.]+)" z="([-\d.]+)"', m.group(3)), float)
        F = np.array(re.findall(r'v1="(\d+)" v2="(\d+)" v3="(\d+)"', m.group(4)), int)
        with TP_.quiet():
            ok, msg = TP_.report(TP_.mesh_set(V, F))
        print('3MF object %s %-26s z0 %.3f  %s%s' % (m.group(1), m.group(2), V[:, 2].min(), msg, '' if ok else '  <-- CHECK'))
    print('3MF placements: %d   file %.1f MB' % (len(build), os.path.getsize(path) / 1e6))
