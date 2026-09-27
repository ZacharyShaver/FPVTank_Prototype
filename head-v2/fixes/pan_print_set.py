"""The pan-coil test print set: the cradle (bolts onto the drum) plus every printed pan-coil part, each
already turned the way it prints, a 3MF plate, a picture sheet and a README. Writes head-v2/out/print-pan/.

Set 2 (2026-09-27, later): the first set could not be assembled -- the drum's gear was moulded on and
could not pass the journal, and the gear bay was a closed box. Now the well and bay print as one `base`,
the bay's floor is a screw-on plate, and the drum's gear is its own part. The 3MF plate holds only what
changed (base, drum, floor, small gear); the cradle and the input gear are the same as set 1.

Run the generator first (both slow, both write into head-v2/generator/, untracked print/ folders):
    python head-v2/generator/generators/tree_parts_b.py fork      # the cradle, ~5 min
    python head-v2/generator/generators/pan_coil_b_print.py       # drum, base, floor, gear_in, gear_out
    python head-v2/fixes/pan_print_set.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import shutil, zipfile
import numpy as np
import pymeshlab as ml
import tree_parts as TP_
from export import health
from zr import zrender

GEN = os.path.join(config.REPO, 'head-v2', 'generator')
SRC = {'cradle': os.path.join(GEN, 'tree-parts-b', 'print', 'fork.stl'),
       'drum': os.path.join(GEN, 'pan-coil-b', 'print', 'drum.stl'),
       'base': os.path.join(GEN, 'pan-coil-b', 'print', 'base.stl'),
       'floor': os.path.join(GEN, 'pan-coil-b', 'print', 'floor.stl'),
       'small_gear': os.path.join(GEN, 'pan-coil-b', 'print', 'gear_out.stl'),
       'input_gear': os.path.join(GEN, 'pan-coil-b', 'print', 'gear_in.stl')}
# The plate: only what changed since set 1. Layout in mm from the plate centre (a 220 x 220 bed).
PLATE = ['base', 'drum', 'floor', 'small_gear']
SPOT = {'base': (-48, 45), 'drum': (58, 50), 'floor': (-40, -55), 'small_gear': (50, -45)}
COL = {'cradle': (216, 195, 154), 'drum': (62, 156, 143), 'base': (163, 168, 162), 'floor': (180, 184, 178),
       'input_gear': (79, 174, 158), 'small_gear': (79, 174, 158)}
OUT = os.path.dirname(config.out('print-pan', 'x'))


def load(path):
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path); ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
    return ms


def fix_self_intersections(ms):
    """print_post.py's loop: cut folded triangles out with a ring, refill, tidy."""
    with TP_.quiet():
        for _ in range(4):
            if TP_.self_intersections(ms) == 0:
                break
            ms.compute_selection_by_self_intersections_per_face()
            ms.apply_selection_dilatation()
            ms.meshing_remove_selected_vertices_and_faces()
            ms.meshing_close_holes(maxholesize=60, newfaceselected=False)
            ms.set_selection_none()
        TP_.tidy(ms)
    return ms


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    meshes, bad = {}, 0
    for name, src in SRC.items():
        if not os.path.exists(src):
            sys.exit('missing %s -- run the generator steps in this file\'s docstring first' % src)
        ms = fix_self_intersections(load(src))
        V = ms.current_mesh().vertex_matrix().copy(); F = ms.current_mesh().face_matrix().copy()
        V -= np.array([(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, V[:, 2].min()])
        p = os.path.join(OUT, name + '.stl')
        with TP_.quiet():
            m2 = ml.MeshSet(); m2.add_mesh(ml.Mesh(V, F)); m2.save_current_mesh(p, binary=True)
        ok, msg = health(p); bad += not ok
        size = V.max(0) - V.min(0)
        print('%-11s %5.1f x %5.1f x %5.1f mm  %s%s' % (name, *size, msg, '' if ok else '  <-- CHECK'))
        meshes[name] = (V, F)
    # footprints must fit the bed and not touch each other
    boxes = [(n, V[:, 0].min() + SPOT[n][0], V[:, 0].max() + SPOT[n][0], V[:, 1].min() + SPOT[n][1], V[:, 1].max() + SPOT[n][1])
             for n, (V, F) in meshes.items() if n in PLATE]
    clash = [(a[0], b[0]) for i, a in enumerate(boxes) for b in boxes[i + 1:]
             if a[1] < b[2] + 3 and b[1] < a[2] + 3 and a[3] < b[4] + 3 and b[3] < a[4] + 3]
    xs = [v for bb in boxes for v in bb[1:3]]; ys = [v for bb in boxes for v in bb[3:5]]
    print('plate: x %.0f..%.0f  y %.0f..%.0f (bed +-110)  gaps under 3 mm: %s' % (min(xs), max(xs), min(ys), max(ys), clash or 'none'))
    bad += bool(clash) or max(abs(v) for v in xs + ys) > 110
    res, build = [], []
    for i, n in enumerate(PLATE, 1):
        V, F = meshes[n]
        vs = ''.join('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % tuple(v) for v in V)
        ts = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in F)
        res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (i, n, vs, ts))
        build.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.3f %.3f 0"/>' % (i, *SPOT[n]))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>%s</resources><build>%s</build></model>'
             % (''.join(res), ''.join(build)))
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    plate = os.path.join(OUT, 'plate_pan_coil_set2.3mf')
    with zipfile.ZipFile(plate, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('3D/3dmodel.model', model)
    print('wrote %s (%.1f MB)' % (os.path.basename(plate), os.path.getsize(plate) / 1e6))
    # picture: the plate as it sits on the bed, from the front-left. Picture-only copies, simplified the
    # generator's way (quality threshold, planar quadric): a plain 9000-face collapse threw 78 mm spikes.
    tris = []
    for n in PLATE:
        V, F = meshes[n]
        with TP_.quiet():
            m = ml.MeshSet(); m.add_mesh(ml.Mesh(V + np.array([*SPOT[n], 0.0]), F))
            m.meshing_decimation_quadric_edge_collapse(targetfacenum=30000, qualitythr=0.6, preserveboundary=True,
                                                       preservenormal=True, preservetopology=True,
                                                       planarquadric=True, planarweight=0.002, autoclean=True)
        tris.append((m.current_mesh().vertex_matrix()[m.current_mesh().face_matrix()], COL[n]))
    img = zrender(tris, 35, 35, size=900)
    img.save(os.path.join(OUT, 'pan_coil_plate.png'))
    print('wrote pan_coil_plate.png')
    # picture 2: how it goes together, pulled apart along the way each part goes in. From the
    # generator's viewer meshes (pan_coil_b.py), which sit in the assembled frame.
    FUS = os.path.join(GEN, 'pan-coil-b', 'fusion')
    EXPLODE = [('well', (0, 0, 0), (163, 168, 162)), ('bay', (0, 0, 0), (163, 168, 162)), ('servo', (0, 45, 0), (40, 70, 140)),
               ('bearing', (0, 0, 30), (150, 150, 160)), ('drum', (0, 0, 45), (62, 156, 143)),
               ('gear_in', (0, 0, -22), (79, 174, 158)), ('gear_out', (0, 0, -22), (79, 174, 158)),
               ('screw_out', (0, 0, -36), (60, 60, 60)), ('floor', (0, 0, -48), (180, 184, 178))]
    tris = []
    for n, off, col in EXPLODE:
        with TP_.quiet():
            m = load(os.path.join(FUS, n + '.obj'))
        tris.append((m.current_mesh().vertex_matrix()[m.current_mesh().face_matrix()] + np.array(off, float), col))
    zrender(tris, 30, 20, size=1000).save(os.path.join(OUT, 'pan_coil_assembly.png'))
    print('wrote pan_coil_assembly.png')
    shutil.copyfile(os.path.join(config.FIXES, 'pan_print_set_README.txt'), os.path.join(OUT, 'README.txt'))
    sys.exit(1 if bad else 0)
