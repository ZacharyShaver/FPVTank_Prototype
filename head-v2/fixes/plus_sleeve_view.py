"""3D view of the +Y hub as a sleeve (plus_sleeve.py, chosen 2026-10-03): today's ball against the cut one, with an
assembly slider. Today the +Y arm bends ~5 mm as the hub goes past it; with the sleeve, the ball drops
straight in, then the sleeve, the 6704, the post and the -Y stub go in from outside.
Writes head-v2/out/plus-sleeve/view.html (published as the "Plus Hub Sleeve" artifact).

    python head-v2/fixes/plus_sleeve.py        # first: the cut ball and the sleeve
    python head-v2/fixes/plus_sleeve_view.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import base64, json
import numpy as np
import pymeshlab as ml
import tree_parts as TP_

O = os.path.join(config.OUT, 'plus-sleeve')
TREE = os.path.join(config.REPO, 'head-v2', 'generator', 'tree-parts-b', 'fusion')
TEMPLATE = os.path.join(config.FIXES, 'plus_sleeve_view_template.html')
H = 52.0


def servo_stl():
    """his MG90S where post v3 seats it: tower top Y 26.24, the gear bump toward -X (his hub's notch)"""
    sys.path.insert(0, os.path.join(config.REPO, 'head-v2', 'checks'))
    import pan_servo_fit as SF
    M = np.concatenate(SF.mesh())
    S = np.stack([-(M[..., 0] + 5.4), M[..., 1] - 2.16, H - (M[..., 2] - 6.1)], -1)
    p = os.path.join(O, '_servo.stl')
    with open(p, 'wb') as f:
        f.write(b'\0' * 80 + np.uint32(len(S)).tobytes())
        rec = np.zeros(len(S), dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))
        rec['v'] = S
        f.write(rec.tobytes())
    return p


def minus_bearing_stl():
    """the -Y 6704 in his ball_minus cup (Y -24.0..-20.0), rings only"""
    from kit import cyl, cut, fuse
    import export as E
    ring = lambda r0, r1: cut(cyl('y', (0, H), r1, -24.0, -20.0), cyl('y', (0, H), r0, -25, -19))
    p = os.path.join(O, '_bearing_minus.stl')
    E.write_stl(fuse(ring(10.0, 11.3), ring(12.3, 13.5)), p)
    return p


def pack(path, faces):
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path)
        ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-4))
        if ms.current_mesh().face_number() > faces:
            ms.meshing_decimation_quadric_edge_collapse(targetfacenum=faces, qualitythr=0.6, preserveboundary=True,
                                                       preservenormal=True, preservetopology=True,
                                                       planarquadric=True, planarweight=0.002, autoclean=True)
    V = ms.current_mesh().vertex_matrix().astype('<f4'); F = ms.current_mesh().face_matrix().astype('<u4')
    return {'v': base64.b64encode(V.tobytes()).decode(), 'f': base64.b64encode(F.tobytes()).decode()}


if __name__ == '__main__':
    parts = {
        'cradle': (os.path.join(TREE, 'fork.obj'), 26000),
        'ball_now': (os.path.join(O, 'ball_plus_rev2.stl'), 26000),
        'ball_new': (os.path.join(O, 'ball_plus_sleeve.stl'), 26000),
        'ball_minus': (os.path.join(config.OUT, 'rev2', '_fig_ball_minus_cup.stl'), 20000),
        'servo': (servo_stl(), 5000),
        'post': (os.path.join(config.OUT, 'ball_servo_post_v3.stl'), 5000),
        'sleeve': (os.path.join(O, 'sleeve.stl'), 4000),
        'brg_in': (os.path.join(O, 'bearing_inner.stl'), 1500),
        'brg_out': (os.path.join(O, 'bearing_outer.stl'), 1500),
        'stub': (os.path.join(TREE, 'stub.obj'), 4000),
        'brg_minus': (minus_bearing_stl(), 2000),
    }
    data = {k: pack(p, n) for k, (p, n) in parts.items()}
    for p in ('_servo.stl', '_bearing_minus.stl'):
        os.remove(os.path.join(O, p))
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', 'window.PARTS=' + json.dumps(data) + ';')
    out = os.path.join(O, 'view.html')
    open(out, 'w', encoding='utf-8').write(html)
    print(out, '%.1f MB' % (len(html) / 1e6))
