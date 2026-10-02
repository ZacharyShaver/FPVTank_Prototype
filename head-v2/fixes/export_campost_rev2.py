"""Rev-2 hand-off (2026-09-27): Zach's Fusion rev 2 halves plus the camera posts regenerated for his
moved tubes. Writes head-v2/out/print-rev2/:
  ball_plus_rev2.stl, ball_minus_rev2.stl        his parts (+ the IR cutout extension), seam face down
  post_v3.stl, snap_pin_stop_medium.stl          unchanged, copied from out/print/
  camera_post_<upper|lower>_<grade>.stl          NEW: lying on the flat, angled head up
  plate_rev2_full.3mf                            both halves, post, 4 pins, the 2 medium posts
  rev2_tools_for_fusion.step                     CUT_plus_ir_extend + the two medium posts seated, his frame
  README.txt                                     (pictures: figure_rev2.py)
Run campost_rev2.py and ball_plus_rev2.py first."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import re, shutil, zipfile
import numpy as np
import cadquery as cq
import pymeshlab as ml
import tree_parts as TP_
import campost as C
import campost_rev2 as R
from occ_load import load
from export import write_stl, health, tidy, rd, drop_to_bed
from print_export import rot_x, on_bed, size
from export_campost import on_bed_tight

OUT = os.path.dirname(config.out('print-rev2', 'x'))
GRADE = 'medium'                                      # Zach's pick for the posts and pins


def mesh(path):
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path); ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
    return ms.current_mesh().vertex_matrix().copy(), ms.current_mesh().face_matrix().copy()


def plate(path, objs):
    res, build, boxes = [], [], []
    for i, (nm, spots) in enumerate(objs, 1):
        V, F = mesh(os.path.join(OUT, nm + '.stl'))
        V = V - np.array([(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, V[:, 2].min()])
        res.append('<object id="%d" type="model" name="%s"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>'
                   % (i, nm, ''.join('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % tuple(v) for v in V),
                      ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in F)))
        for x, y in spots:
            build.append('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 %.3f %.3f 0"/>' % (i, x, y))
            boxes.append((nm, V[:, 0].min() + x, V[:, 0].max() + x, V[:, 1].min() + y, V[:, 1].max() + y))
    clash = [(a[0], b[0]) for i, a in enumerate(boxes) for b in boxes[i + 1:]
             if a[1] < b[2] + 2 and b[1] < a[2] + 2 and a[3] < b[4] + 2 and b[3] < a[4] + 2]
    xs = [v for bb in boxes for v in bb[1:3]]; ys = [v for bb in boxes for v in bb[3:5]]
    print('plate: x %.0f..%.0f  y %.0f..%.0f (bed +-110), gaps under 2 mm: %s' % (min(xs), max(xs), min(ys), max(ys), clash or 'none'))
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>%s</resources><build>%s</build></model>'
             % (''.join(res), ''.join(build)))
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('3D/3dmodel.model', model)
    bad = 0
    xml = zipfile.ZipFile(path).read('3D/3dmodel.model').decode()
    for m in re.finditer(r'<object id="(\d+)" type="model" name="([^"]+)"><mesh><vertices>(.*?)</vertices><triangles>(.*?)</triangles>', xml):
        V = np.array(re.findall(r'x="([-\d.]+)" y="([-\d.]+)" z="([-\d.]+)"', m.group(3)), float)
        F = np.array(re.findall(r'v1="(\d+)" v2="(\d+)" v3="(\d+)"', m.group(4)), int)
        with TP_.quiet():
            ok, msg = TP_.report(TP_.mesh_set(V, F))
        bad += not ok
        print('  3mf %-24s %s' % (m.group(2), msg))
    return bad + len(clash)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    R.use_rev2()
    bad = 0
    # his halves: sewn exact, then the print orientation every half has had (seam face on the bed)
    for nm, solid, deg in (('ball_plus_rev2', rd(config.out('rev2', 'ball_plus_rev2.brep')), 90.0),
                           ('ball_minus_rev2', load(R.BALL_MINUS)[0], -90.0)):
        s = on_bed(rot_x(solid, deg))
        f = os.path.join(OUT, nm + '.stl')
        write_stl(s, f, lin=0.01, ang=0.05)
        print('%-16s %.1f x %.1f x %.1f mm, needle repair moved the surface %.4f mm' % ((nm,) + size(s) + (tidy(f),)))
    for nm in ('post_v3', 'snap_pin_stop_' + GRADE):
        shutil.copyfile(os.path.join(config.PRINT, nm + '.stl'), os.path.join(OUT, nm + '.stl'))
    for tb in C.TUBES:
        for g in C.BARBS:
            s = on_bed_tight(C.to_local(rd(config.out('rev2', 'camera_post_%s_%s.brep' % (tb, g))), tb))
            f = os.path.join(OUT, 'camera_post_%s_%s.stl' % (tb, g))
            write_stl(s, f, lin=0.004, ang=0.05); drop_to_bed(f)
    print('mesh health:')
    for fn in sorted(os.listdir(OUT)):
        if fn.endswith('.stl'):
            ok, msg = health(os.path.join(OUT, fn)); bad += not ok
            print('  %-32s %s%s' % (fn, msg, '' if ok else '   <-- CHECK'))
    bad += plate(os.path.join(OUT, 'plate_rev2_full.3mf'),
                 [('ball_plus_rev2', [(-36.0, 28.0)]), ('ball_minus_rev2', [(36.0, 28.0)]), ('post_v3', [(-34.0, -42.0)]),
                  ('snap_pin_stop_' + GRADE, [(8.0 + 9.0 * k, -42.0) for k in range(4)]),
                  ('camera_post_upper_' + GRADE, [(54.0, -36.0)]), ('camera_post_lower_' + GRADE, [(54.0, -48.0)])])
    import ball_plus_rev2 as IR
    asm = cq.Assembly(name='rev2_tools')
    for nm, sh in IR.tools().items():
        asm.add(cq.Workplane(obj=cq.Shape.cast(sh)), name=nm, color=cq.Color(0.85, 0.2, 0.2, 0.6))
    for tb in C.TUBES:
        asm.add(cq.Workplane(obj=cq.Shape.cast(rd(config.out('rev2', 'camera_post_%s_%s.brep' % (tb, GRADE))))),
                name='POST_%s_%s' % (tb, GRADE), color=cq.Color(0.95, 0.55, 0.1, 1.0))
    asm.save(os.path.join(OUT, 'rev2_tools_for_fusion.step'))
    print('wrote rev2_tools_for_fusion.step')
    shutil.copyfile(os.path.join(config.FIXES, 'print_rev2_README.txt'), os.path.join(OUT, 'README.txt'))
    sys.exit(1 if bad else 0)
