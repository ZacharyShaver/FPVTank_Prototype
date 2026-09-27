"""Tidy every print STL (the same needle repair as before), then write the plate 3MF by hand from the
tidied meshes: one object per part, the pin as one object placed four times."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import zipfile, re
import numpy as np
import pymeshlab as ml
import tree_parts as TP_
from export import tidy, health
OUTP = config.PRINT
PIN = 'snap_pin_stop_medium'            # Zach's pick (2026-09-27, docs/decisions.md)
names = ['ball_plus', 'ball_minus', 'post_v3', 'snap_pin_stop_soft', 'snap_pin_stop_medium', 'snap_pin_stop_firm']
for nm in names:
    dev = tidy(os.path.join(OUTP, nm + '.stl'))
    ok, msg = health(os.path.join(OUTP, nm + '.stl'))
    print('%-24s repair moved <= %.4f mm   %s%s' % (nm + '.stl', dev, msg, '' if ok else '  <-- CHECK'))
def mesh(nm):
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(os.path.join(OUTP, nm + '.stl'))
        ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
    V = ms.current_mesh().vertex_matrix(); F = ms.current_mesh().face_matrix()
    c = np.array([(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, V[:, 2].min()])
    return V - c, F
objs = [('ball_plus', [(-36.0, 28.0)]), ('ball_minus', [(36.0, 28.0)]), ('post_v3', [(-34.0, -42.0)]),
        (PIN, [(8.0 + 9.0 * k, -42.0) for k in range(4)])]
res, build, lo, hi = [], [], np.full(2, np.inf), np.full(2, -np.inf)
for i, (nm, spots) in enumerate(objs, 1):
    V, F = mesh(nm)
    vs = ''.join('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % tuple(v) for v in V)
    ts = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in F)
    res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (i, nm, vs, ts))
    for x, y in spots:
        build.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.3f %.3f 0"/>' % (i, x, y))
        lo = np.minimum(lo, V[:, :2].min(0) + (x, y)); hi = np.maximum(hi, V[:, :2].max(0) + (x, y))
print('plate footprint %.0f x %.0f mm' % tuple(hi - lo))
model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
         'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>%s</resources><build>%s</build></model>'
         % (''.join(res), ''.join(build)))
ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
path = os.path.join(OUTP, 'plate_ball_post_pins.3mf')
with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('3D/3dmodel.model', model)
# read it back: every object's mesh through the same health report
xml = zipfile.ZipFile(path).read('3D/3dmodel.model').decode()
for m in re.finditer(r'<object id="(\d+)" type="model" name="([^"]+)"><mesh><vertices>(.*?)</vertices><triangles>(.*?)</triangles>', xml):
    V = np.array(re.findall(r'x="([-\d.]+)" y="([-\d.]+)" z="([-\d.]+)"', m.group(3)), float)
    F = np.array(re.findall(r'v1="(\d+)" v2="(\d+)" v3="(\d+)"', m.group(4)), int)
    with TP_.quiet():
        ok, msg = TP_.report(TP_.mesh_set(V, F))
    print('3MF object %s %-22s %s%s' % (m.group(1), m.group(2), msg, '' if ok else '  <-- CHECK'))
print('3MF placements:', len(build), '  file %.1f MB' % (os.path.getsize(path) / 1e6))
