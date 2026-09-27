"""The 3D fit view: the head, the cradle and the pan coil in their real positions, as one HTML page
(published as the "Head and Pan Coil Fit" artifact). Writes head-v2/out/fit-view/.

The pan-coil parts come from the generator's viewer meshes (pan_coil_b.py writes
head-v2/generator/pan-coil-b/fusion/*.obj), decimated here. The head parts and the cradle are
unchanged since the first build (2026-09-27) and are carried over from the previous data.js; delete
it to force them from nothing and this script stops with the list it is missing.

    python head-v2/fixes/fit_view.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import base64, json
import numpy as np
import pymeshlab as ml
import tree_parts as TP_

GEN = os.path.join(config.REPO, 'head-v2', 'generator', 'pan-coil-b', 'fusion')
OUT = os.path.dirname(config.out('fit-view', 'x'))
TEMPLATE = os.path.join(config.FIXES, 'fit_view_template.html')
# set 2 (2026-09-27): the coil parts, rebuilt from the generator every run. (name, obj, label, faces)
COIL = [('drum', 'drum', 'Drum (turns with head)', 10000),
        ('bearing', 'bearing', 'Pan bearing 6809', 4000),
        ('gear_out', 'gear_out', 'Small gear (on the drum)', 6000),
        ('screw_out', 'screw_out', 'M3 × 8 button head', 800),
        ('gear_in', 'gear_in', 'Input gear', 8000),
        ('servo', 'servo', 'Pan servo', 4000),
        ('ribbon', 'ribbon', 'Ribbon coil', 8000),
        ('well', 'well', 'Base: coil well', 20000),
        ('bay', 'bay', 'Base: gear bay (one print with the well)', 14000),
        ('floor', 'floor', 'Gear bay floor plate', 3000)]
CARRIED = ['ball_plus', 'ball_minus', 'post', 'axle', 'cap_minus', 'fork', 'twist_gap']


def pack(name, label, faces):
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(os.path.join(GEN, name + '.obj'))
        if ms.current_mesh().face_number() > faces:
            ms.meshing_decimation_quadric_edge_collapse(targetfacenum=faces, qualitythr=0.6, preserveboundary=True,
                                                       preservenormal=True, preservetopology=True,
                                                       planarquadric=True, planarweight=0.002, autoclean=True)
    V = ms.current_mesh().vertex_matrix().astype('<f4'); F = ms.current_mesh().face_matrix().astype('<u4')
    return {'label': label, 'group': 'coil', 'v': base64.b64encode(V.tobytes()).decode(),
            'f': base64.b64encode(F.tobytes()).decode(), 'bb': [V.min(0).tolist(), V.max(0).tolist()]}


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    old = {}
    p = os.path.join(OUT, 'data.js')
    if os.path.exists(p):
        s = open(p, encoding='utf-8').read(); old = json.loads(s[s.index('{'):s.rindex('}') + 1])
    missing = [k for k in CARRIED if k not in old]
    if missing:
        sys.exit('no previous data.js entry for %s' % missing)
    fit = {k: old[k] for k in CARRIED[:5]}
    fit['fork'] = old['fork']
    for key, obj, label, faces in COIL:
        fit[key] = pack(obj, label, faces)
        print('%-10s %6d bytes' % (key, len(fit[key]['v']) + len(fit[key]['f'])))
    fit['twist_gap'] = old['twist_gap']
    data = 'window.FIT=' + json.dumps(fit) + ';'
    open(p, 'w', encoding='utf-8').write(data)
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', data)
    open(os.path.join(OUT, 'head-pan-coil-fit.html'), 'w', encoding='utf-8').write(html)
    print('wrote head-pan-coil-fit.html (%.1f MB)' % (len(html) / 1e6))
