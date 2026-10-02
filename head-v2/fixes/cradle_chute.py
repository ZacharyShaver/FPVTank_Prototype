"""The cradle with the servo plug's chute (2026-09-27, later): print file, plate, tool bodies, pictures.
Writes into head-v2/out/print-pan/ next to set 2, and moves the cradle it replaces into
"superseded - cradle before plug chute/".

The cradle is the generator's (tree_parts_b.fork; CHUTE_T and chute() are the change). Run first:
    python head-v2/generator/generators/tree_parts_b.py fork      # ~5 min
    python head-v2/fixes/cradle_chute.py
    python head-v2/checks/plug_passage.py                          # the check, with its control
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import filecmp, shutil, zipfile
import numpy as np
import pymeshlab as ml
import cadquery as cq
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import tree_parts as TP_
import tree_parts_b as B, pan_coil_b as P
from export import health
from kit import cyl, fuse, prism_y
from pan_print_set import load, fix_self_intersections, SRC, OUT

OLD_DIR = os.path.join(OUT, 'superseded - cradle before plug chute')
PLATE = os.path.join(OUT, 'plate_cradle_chute.3mf')


def tools():
    """CUT_ bodies in the head frame (X lens, Y tilt axis, Z up, tilt axis Z 52), for reference in Fusion."""
    s, c = np.sin(np.radians(B.CHUTE_ANG)), -np.cos(np.radians(B.CHUTE_ANG))
    a = np.array([B.CHUTE_X + s * (B.CHUTE_Z1 - B.BASE_Z) / c, B.CHUTE_Z1])
    b = np.array([B.CHUTE_X + s * (B.CHUTE_Z0 - B.BASE_Z) / c, B.CHUTE_Z0])
    r, hw = B.CHUTE_T / 2, B.TROUGH_W / 2
    n = np.array([-(b - a)[1], (b - a)[0]]) / np.linalg.norm(b - a) * r
    chute = fuse(prism_y([a + n, b + n, b - n, a - n], -hw, hw), cyl('y', a, r, -hw, hw), cyl('y', b, r, -hw, hw))
    path = B.bezier(B.TROUGH_PATH, 60)
    t = np.gradient(path, axis=0); t /= np.linalg.norm(t, axis=1)[:, None]
    m = np.stack([-t[:, 1], t[:, 0]], 1) * r
    groove = fuse(prism_y(list(path + m) + list((path - m)[::-1]), -hw, hw),
                  cyl('y', path[0], r, -hw, hw), cyl('y', path[-1], r, -hw, hw))
    return {'CUT_cradle_plug_chute': chute, 'CUT_cradle_groove_4mm': groove}


def section_sheet(path):
    XS = np.arange(-28, 12.05, 0.08); ZS = np.arange(0, 34.05, 0.08)
    X, Z = np.meshgrid(XS, ZS)
    chute, t = B.chute, B.CHUTE_T
    fig, axs = plt.subplots(2, 3, figsize=(16, 10.5))
    for row, tag in enumerate(('BEFORE (as printed): 3.0 groove', 'AFTER: 4.0 groove + plug chute')):
        if row == 0:
            B.chute = lambda p, *a, **k: np.full_like(p[0], 1e3); B.CHUTE_T = B.TROUGH_T
        else:
            B.chute, B.CHUTE_T = chute, t
        for ax, y in zip(axs[row], (0.0, 5.0, 9.0)):
            p = (X, np.full_like(X, y), Z)
            ax.contourf(XS, ZS, B.fork(p), levels=[-99, 0], colors=['#a8a8a8'])
            ax.contourf(XS, ZS, P.drum(p), levels=[-99, 0], colors=['#3e9c8f'])
            c = B.bezier(B.TROUGH_PATH, 200); ax.plot(c[:, 0], c[:, 1], color='#1f6fd0', lw=1.2)
            ax.add_patch(plt.Circle((0, B.H), B.R_BALL, fill=False, ls='--', lw=0.8, color='k'))
            if row == 1:
                d = np.array([np.sin(np.radians(B.CHUTE_ANG)), -np.cos(np.radians(B.CHUTE_ANG))])
                e = np.array([B.CHUTE_X, B.BASE_Z]) - d * 5.0
                q = np.array([-d[1], d[0]])
                box = np.array([e - 6.5 * d - 1.5 * q, e + 6.5 * d - 1.5 * q, e + 6.5 * d + 1.5 * q, e - 6.5 * d + 1.5 * q])
                ax.fill(box[:, 0], box[:, 1], color='#e0443e', alpha=0.7)
            ax.set_xlim(-28, 12); ax.set_ylim(0, 34); ax.set_aspect('equal'); ax.grid(alpha=0.3)
            ax.set_title('%s -- section at Y %.0f' % (tag, y), fontsize=10)
    B.chute, B.CHUTE_T = chute, t
    fig.text(0.01, 0.005, 'Side sections, +X toward the lens. Grey cradle, green drum, dashed ball, blue ribbon. '
             'Red: a 13 x 3 plug in the chute. Before, the groove met the ribbon track only as a hairline near Y 0.',
             fontsize=10)
    plt.tight_layout(rect=(0, 0.02, 1, 1)); plt.savefig(path, dpi=80); plt.close(fig)


def plate(V, F):
    vs = ''.join('<vertex x="%.5f" y="%.5f" z="%.5f"/>' % tuple(v) for v in V)
    ts = ''.join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in F)
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources><object id="1" type="model" '
             'name="cradle"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object></resources><build>'
             '<item objectid="1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/></build></model>' % (vs, ts))
    ct = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(PLATE, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('3D/3dmodel.model', model)


if __name__ == '__main__':
    dst = os.path.join(OUT, 'cradle.stl')
    ms = fix_self_intersections(load(SRC['cradle']))
    V = ms.current_mesh().vertex_matrix().copy(); F = ms.current_mesh().face_matrix().copy()
    V -= np.array([(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, V[:, 2].min()])
    tmp = os.path.join(OUT, '_cradle_new.stl')
    with TP_.quiet():
        m2 = ml.MeshSet(); m2.add_mesh(ml.Mesh(V, F)); m2.save_current_mesh(tmp, binary=True)
    if os.path.exists(dst) and not filecmp.cmp(dst, tmp, shallow=False):
        os.makedirs(OLD_DIR, exist_ok=True)
        if not os.path.exists(os.path.join(OLD_DIR, 'cradle.stl')):
            shutil.move(dst, os.path.join(OLD_DIR, 'cradle.stl'))
            print('moved the old cradle.stl to "%s"' % os.path.basename(OLD_DIR))
    os.replace(tmp, dst)
    ok, msg = health(dst)
    print('cradle.stl  %5.1f x %5.1f x %5.1f mm  %s%s' % (*(V.max(0) - V.min(0)), msg, '' if ok else '  <-- CHECK'))
    plate(V, F); print('wrote', os.path.basename(PLATE))
    asm = cq.Assembly(name='cradle_plug_chute')
    for nm, s in tools().items():
        asm.add(cq.Workplane(obj=cq.Shape.cast(s)), name=nm, color=cq.Color(0.85, 0.2, 0.2, 0.6))
    asm.save(os.path.join(OUT, 'cradle_chute_tools_for_fusion.step')); print('wrote cradle_chute_tools_for_fusion.step')
    section_sheet(os.path.join(OUT, 'cradle_chute.png')); print('wrote cradle_chute.png')
    sys.exit(0 if ok else 1)
