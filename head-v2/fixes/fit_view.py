"""The 3D fit view: the head, the cradle and the pan coil in their real positions, as one HTML page
(published as the "Head and Pan Coil Fit" artifact). Writes head-v2/out/fit-view/.

The pan-coil parts come from the generator's viewer meshes (pan_coil_b.py writes
head-v2/generator/pan-coil-b/fusion/*.obj), decimated here, and so does the cradle since the plug
chute (tree_parts_b.py writes tree-parts-b/fusion/fork.obj). The post, axle and cap are unchanged
since the first build (2026-09-27) and are carried over from the previous data.js; delete it to force
them from nothing and this script stops with the list it is missing.

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
        ('ribbon', 'ribbon', 'Ribbon coil', 8000),
        ('well', 'well', 'Base: coil well', 20000),
        ('bay', 'bay', 'Base: gear bay (one print with the well)', 14000),
        ('floor', 'floor', 'Gear bay floor plate', 3000),
        ('tab_block', 'tab_block', 'Tab block (under the servo window-end tab)', 1500)]
CARRIED = ['post', 'twist_gap']     # the -Y axle and cap dropped out 2026-10-02: the stub replaced them
FORK = os.path.join(config.REPO, 'head-v2', 'generator', 'tree-parts-b', 'fusion', 'fork.obj')
PLUG = (14.0, 8.0, 3.0)        # the servo connector, L x W calipered by Zach, T assumed (checks/plug_passage.py)
# Head rev 2 (2026-09-27): Zach's rev-2 halves (ball_plus with the IR cutout extension), the camera posts
# rebuilt for his moved tubes, and the real board where the pins put it. From fixes/figure_rev2.py's
# meshes (head frame) and the generator's centred camera. (key, stl, label, faces, colour key)
HEAD_R2 = [('ball_plus', os.path.join(config.OUT, 'rev2', '_fig_ball_plus.stl'), 'Ball, + half (rev 2)', 40000),
           ('ball_minus', os.path.join(config.REPO, 'head-v2', 'fusion', 'rev2-2026-09-27', 'ball_minus_revised_27.stl'),
            'Ball, − half (rev 2)', 40000),
           ('camera', os.path.join(config.CAMERA, 'camera_dummy_centred.stl'), 'Camera board (lens centred on its holes)', 6000),
           ('campost_upper', os.path.join(config.OUT, 'rev2', '_fig_post_upper.stl'), 'Camera post, upper', 3000),
           ('campost_lower', os.path.join(config.OUT, 'rev2', '_fig_post_lower.stl'), 'Camera post, lower', 3000)]


def pack(name, label, faces, path=None, group='coil', shift=(0.0, 0.0, 0.0)):
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path or os.path.join(GEN, name + '.obj'))
        if ms.current_mesh().face_number() > faces:
            ms.meshing_decimation_quadric_edge_collapse(targetfacenum=faces, qualitythr=0.6, preserveboundary=True,
                                                       preservenormal=True, preservetopology=True,
                                                       planarquadric=True, planarweight=0.002, autoclean=True)
    V = (ms.current_mesh().vertex_matrix() + np.array(shift)).astype('<f4'); F = ms.current_mesh().face_matrix().astype('<u4')
    return {'label': label, 'group': group, 'v': base64.b64encode(V.tobytes()).decode(),
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
    import campost_rev2 as R
    fit = {}
    for key, path, label, faces in HEAD_R2:
        shift = (2.5, R.LENS_DY, R.LENS_DZ) if key == 'camera' else (0.0, 0.0, 0.0)
        fit[key] = pack(key, label, faces, path=path, group='head', shift=shift)
    fit['post'] = old['post']
    # Round 1 of the wire route (2026-10-02): the stub replaces the -Y axle and end cap.
    fit['stub'] = pack('stub', 'Stub (replaces the -Y axle and cap; ball turns on it)', 6000,
                       path=os.path.join(config.REPO, 'head-v2', 'generator', 'tree-parts-b', 'fusion', 'stub.obj'), group='head')
    fit['fork'] = pack('fork', 'Cradle (plug chute + wire hole down the -Y wall)', 26000, path=FORK, group='cradle')
    import tree_parts_b as B
    from kit import prism_y
    from export import write_stl
    L, W, T = PLUG
    d = np.array([np.sin(np.radians(B.CHUTE_ANG)), -np.cos(np.radians(B.CHUTE_ANG))]); q = np.array([-d[1], d[0]])
    e = np.array([B.CHUTE_X, B.BASE_Z]) - d * 5.0              # part-way down the chute
    plug = os.path.join(OUT, '_plug.stl')
    write_stl(prism_y([e - L / 2 * d - T / 2 * q, e + L / 2 * d - T / 2 * q, e + L / 2 * d + T / 2 * q,
                       e - L / 2 * d + T / 2 * q], -W / 2, W / 2), plug)
    fit['plug'] = pack('plug', 'Servo connector, %g × %g × %g (thickness assumed)' % PLUG, 200, path=plug, group='cradle')
    for key, obj, label, faces in COIL:
        fit[key] = pack(obj, label, faces)
        print('%-10s %6d bytes' % (key, len(fit[key]['v']) + len(fit[key]['f'])))
    # The pan servo is Zach's own MG90S mesh (2026-09-28), placed the way checks/pan_servo_fit.py seats it,
    # not the generator's box stand-in.
    sys.path.insert(0, os.path.join(config.REPO, 'head-v2', 'checks'))
    import pan_servo_fit as SF
    import pan_coil_b as PC
    T = np.concatenate(SF.mesh())
    T = np.stack([PC.CENTRE + 6.1 - T[..., 2], T[..., 0] + 5.4, PC.SV_Z1 - T[..., 1]], -1)
    mg = os.path.join(OUT, '_mg90s.stl')
    with TP_.quiet():
        m = ml.MeshSet(); m.add_mesh(ml.Mesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3)))
        m.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5)); m.save_current_mesh(mg, binary=True)
    fit['servo'] = pack('servo', 'Pan servo (your MG90S model)', 4000, path=mg)
    fit['twist_gap'] = old['twist_gap']
    # The servo cable idea (2026-09-30): his MG90S as the tilt servo, and the route drawn as a tube.
    import cable_idea as CI
    Tt = CI.tilt_servo(np.concatenate(SF.mesh()))
    ts = os.path.join(OUT, '_tilt_servo.stl')
    with TP_.quiet():
        m = ml.MeshSet(); m.add_mesh(ml.Mesh(Tt.reshape(-1, 3), np.arange(len(Tt) * 3).reshape(-1, 3)))
        m.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5)); m.save_current_mesh(ts, binary=True)
    fit['tilt_servo'] = pack('tilt_servo', 'Tilt servo (your MG90S model)', 4000, path=ts, group='head')
    for key, (path, label) in CI.build(OUT).items():
        fit[key] = pack(key, label, 20000, path=path, group='cable')
    data = 'window.FIT=' + json.dumps(fit) + ';'
    open(p, 'w', encoding='utf-8').write(data)
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', data)
    open(os.path.join(OUT, 'head-pan-coil-fit.html'), 'w', encoding='utf-8').write(html)
    print('wrote head-pan-coil-fit.html (%.1f MB)' % (len(html) / 1e6))
