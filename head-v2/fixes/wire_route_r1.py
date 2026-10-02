"""The tilt servo's own wire route, round 1 (2026-10-02): the cradle with the wire hole and the fixed hollow
stub. Print files, plate, tool bodies, a picture sheet. Writes into head-v2/out/print-pan/, and moves the
cradle it replaces into "superseded - cradle before wire route/".

The servo's lead and plug stay coiled inside the ball. Zach's Dupont jumper wires plug into it and run
alone: through the middle of the stub (on the tilt axis, so they twist instead of bending), down a 5 mm
hole inside the cradle's -Y wall, and into the plug chute's mouth above the drum's bore. The stub replaces
both the -Y axle (r 9.95 in his r 10.04 socket: it never fitted) and the end cap. It is held by three
M2 x 6 through the cap's old holes. Round 2, the drum and base with the wires' own lane, comes later.

The parts are the generator's (tree_parts_b: WIRE_*, wire_tube(), stub()). Run first:
    python head-v2/generator/generators/tree_parts_b.py fork stub     # ~5 min
    python head-v2/fixes/wire_route_r1.py
    python head-v2/checks/wire_route.py                                # the check, with its controls
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
from vox import load_stl
import slices
from pan_print_set import load, fix_self_intersections, SRC, OUT

OLD_DIR = os.path.join(OUT, 'superseded - cradle before wire route')
STUB_SRC = os.path.join(config.REPO, 'head-v2', 'generator', 'tree-parts-b', 'print', 'stub.stl')
PLATE = os.path.join(OUT, 'plate_wire_route_r1.3mf')
SPOT = {'cradle': (-30, 0), 'stub': (50, 0)}
BALL_MINUS = os.path.join(config.REPO, 'head-v2', 'fusion', 'rev2-2026-09-27', 'ball_minus_revised_27.stl')


def tube_solid(line, r):
    """Cylinders and spheres along a polyline, fused: a round tube in exact solids."""
    s = None
    for a, b in zip(line[:-1], line[1:]):
        d = b - a; h = float(np.linalg.norm(d))
        if h < 1e-3:
            continue
        c = cq.Solid.makeCylinder(r, h, cq.Vector(*a), cq.Vector(*(d / h)))
        s = c if s is None else s.fuse(c)
    for p in line:
        s = s.fuse(cq.Solid.makeSphere(r, cq.Vector(*p), angleDegrees1=-90, angleDegrees2=90))
    return s.clean()


def tools():
    """Tool bodies in the head frame (X lens, Y tilt axis, Z up, tilt axis Z 52), for reference in Fusion."""
    line = B._centripetal(B.WIRE_PTS, 2)
    low = line[line[:, 2] < 40.0]
    return {'CUT_wire_hole_5mm': tube_solid(line, B.WIRE_R),
            'ADD_wire_conduit': tube_solid(low, B.WIRE_R + B.WIRE_WALL)}


def save(V, F, path):
    with TP_.quiet():
        m = ml.MeshSet(); m.add_mesh(ml.Mesh(V, F)); m.save_current_mesh(path, binary=True)


def sheet(path):
    """Before/after sections: the -Y wall (X -5), the stub in his socket (X 0), and from outside (Y -31)."""
    T = load_stl(BALL_MINUS)
    fig, axs = plt.subplots(2, 3, figsize=(18, 11.5))
    L = B.WIRE_LINE
    for row in (0, 1):
        B.WIRE_ROUTE = bool(row)
        # 1. section at X -5, looking from behind: the hole down the wall
        ax = axs[row, 0]; YS = np.arange(-38, -2, 0.1); ZS = np.arange(6, 60, 0.1); Y, Z = np.meshgrid(YS, ZS)
        p = (np.full_like(Y, -5.0), Y, Z)
        ax.contourf(YS, ZS, B.fork(p), levels=[-99, 0], colors=['#b9b2a2'])
        ax.contourf(YS, ZS, P.drum(p), levels=[-99, 0], colors=['#3e9c8f'])
        if row:
            ax.contourf(YS, ZS, B.stub(p), levels=[-99, 0], colors=['#3fae6a'])
            ax.plot(L[:, 1], L[:, 2], color='#e0443e', lw=1.4)
        else:
            ax.contourf(YS, ZS, B.axle(p), levels=[-99, 0], colors=['#8e98a3'])
            ax.contourf(YS, ZS, B.cap_minus(p), levels=[-99, 0], colors=['#6e7883'])
        ax.set_title('%s: section at X -5 (looking from behind)' % ('AFTER' if row else 'BEFORE'), fontsize=10)
        ax.set_xlim(-38, -2); ax.set_ylim(6, 60)
        ax.set_xlabel('Y'); ax.set_ylabel('Z')
        # 2. section at X 0: stub (or axle) in his ball's socket
        ax = axs[row, 1]; YS = np.arange(-38, -12, 0.05); ZS = np.arange(36, 68, 0.05); Y, Z = np.meshgrid(YS, ZS)
        p = (np.zeros_like(Y), Y, Z)
        ax.contourf(YS, ZS, B.fork(p), levels=[-99, 0], colors=['#b9b2a2'])
        m, u, v, _ = slices.slice2d(T, 0, 0.0, (-38, 36), (-12, 68), h=0.05)
        ax.contourf(u, v, m.T.astype(float), levels=[0.5, 2], colors=['#93aac2'])
        if row:
            ax.contourf(YS, ZS, B.stub(p), levels=[-99, 0], colors=['#3fae6a'])
            ax.plot(L[:, 1], L[:, 2], color='#e0443e', lw=1.4)
            ax.text(-37, 66, 'stub r %.2f in your socket r 10.04: 0.24 gap\nring fills the empty bearing seat' % B.STUB_R, fontsize=8.5, va='top')
        else:
            ax.contourf(YS, ZS, B.axle(p), levels=[-99, 0], colors=['#8e98a3'])
            ax.contourf(YS, ZS, B.cap_minus(p), levels=[-99, 0], colors=['#6e7883'])
            ax.text(-37, 66, 'old axle r 9.95 in your socket r 10.04:\n0.09 gap, why it never fitted', fontsize=8.5, va='top')
        ax.set_title('%s: section at X 0 (tilt axis), ball blue' % ('AFTER' if row else 'BEFORE'), fontsize=10)
        ax.set_xlim(-38, -12); ax.set_ylim(36, 68)
        ax.set_xlabel('Y'); ax.set_ylabel('Z')
        # 3. section at Y -28 (inside the wall), seen from outside
        ax = axs[row, 2]; XS = np.arange(-26, 22, 0.1); ZS = np.arange(6, 72, 0.1); X, Z = np.meshgrid(XS, ZS)
        yy = -28.0; p = (X, np.full_like(X, yy), Z)
        ax.contourf(XS, ZS, B.fork(p), levels=[-99, 0], colors=['#b9b2a2'])
        if row:
            ax.contourf(XS, ZS, B.stub(p), levels=[-99, 0], colors=['#3fae6a'])
            ax.plot(L[:, 0], L[:, 2], color='#e0443e', lw=1.4)
        for a in np.radians(B.SCREW_A):
            ax.plot(B.SCREW_R * np.cos(a), B.H + B.SCREW_R * np.sin(a), 'kx')
        ax.set_title('%s: section at Y -28, seen from -Y (x: cap screws)' % ('AFTER' if row else 'BEFORE'), fontsize=10)
        ax.set_xlim(-26, 22); ax.set_ylim(6, 72)
        ax.set_xlabel('X (lens ->)'); ax.set_ylabel('Z')
        for ax in axs[row]:
            ax.set_aspect('equal'); ax.grid(alpha=0.3)
    B.WIRE_ROUTE = True
    fig.text(0.01, 0.005, 'Grey: cradle. Green: the new stub (old axle and cap in slate). Teal: drum. Red: the wires\' path, '
             '5 mm hole. Where the wall was too thin for the hole, a 1.6 mm ridge grows on its outside.', fontsize=10)
    plt.tight_layout(rect=(0, 0.02, 1, 1)); plt.savefig(path, dpi=75); plt.close(fig)


def plate(meshes):
    res, build = [], []
    for i, (n, (V, F)) in enumerate(meshes.items(), 1):
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
    with zipfile.ZipFile(PLATE, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', ct); z.writestr('_rels/.rels', rels); z.writestr('3D/3dmodel.model', model)


if __name__ == '__main__':
    bad, meshes = 0, {}
    for name, src in (('cradle', SRC['cradle']), ('stub', STUB_SRC)):
        ms = fix_self_intersections(load(src))
        V = ms.current_mesh().vertex_matrix().copy(); F = ms.current_mesh().face_matrix().copy()
        V -= np.array([(V[:, 0].min() + V[:, 0].max()) / 2, (V[:, 1].min() + V[:, 1].max()) / 2, V[:, 2].min()])
        dst = os.path.join(OUT, name + '.stl'); tmp = os.path.join(OUT, '_%s_new.stl' % name)
        save(V, F, tmp)
        if name == 'cradle' and os.path.exists(dst) and not filecmp.cmp(dst, tmp, shallow=False):
            os.makedirs(OLD_DIR, exist_ok=True)
            if not os.path.exists(os.path.join(OLD_DIR, 'cradle.stl')):
                shutil.move(dst, os.path.join(OLD_DIR, 'cradle.stl'))
                for f in ('plate_cradle_chute.3mf', 'cradle_chute.png', 'cradle_chute_tools_for_fusion.step'):
                    if os.path.exists(os.path.join(OUT, f)):
                        shutil.move(os.path.join(OUT, f), os.path.join(OLD_DIR, f))
                print('moved the old cradle and its plate, picture and STEP to "%s"' % os.path.basename(OLD_DIR))
        os.replace(tmp, dst)
        ok, msg = health(dst); bad += not ok
        print('%-7s %5.1f x %5.1f x %5.1f mm  %s%s' % (name, *(V.max(0) - V.min(0)), msg, '' if ok else '  <-- CHECK'))
        meshes[name] = (V, F)
    plate(meshes); print('wrote', os.path.basename(PLATE))
    asm = cq.Assembly(name='wire_route_r1')
    for nm, s in tools().items():
        asm.add(cq.Workplane(obj=s), name=nm, color=cq.Color(0.85, 0.2, 0.2, 0.6) if nm.startswith('CUT') else cq.Color(0.2, 0.6, 0.3, 0.6))
    asm.save(os.path.join(OUT, 'wire_route_r1_tools_for_fusion.step')); print('wrote wire_route_r1_tools_for_fusion.step')
    sheet(os.path.join(OUT, 'wire_route_r1.png')); print('wrote wire_route_r1.png')
    shutil.copyfile(os.path.join(config.FIXES, 'pan_print_set_README.txt'), os.path.join(OUT, 'README.txt'))
    sys.exit(1 if bad else 0)
