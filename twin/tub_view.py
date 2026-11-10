"""The tub fit page (2026-11-07): the printed Trainer tub in 3D with every inside part where the sim puts it, so Zach
can turn it round and see how things fit. One HTML page, twin/out/tub_view.html (published as the "Trainer Tub Fit"
artifact).

    python twin/tub_view.py

The tub is the printed STL (floor at z 0). The parts are chassis-v2/rugged.py's meshes (the sim's), moved into the tub's
frame, except the ESCs, which are boxes at his caliper size placed as trainer_tub.parts() places them. The power parts
at the back are the sim's guesses; none is bought yet. The head is hidden at first: Zach, 2026-11-07, it comes out of
the body box as its own module ("a good chance that is going to be blocked in some way for most bodies").
"""
import os, sys, json, base64
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trainer_tub as TT                           # sets SCORPION_LEGS=wheels and the paths
import config
import numpy as np
import pymeshlab as ml
import rugged as RG

OUT = config.TWIN_OUT
TEMPLATE = os.path.join(HERE, 'tub_view_template.html')
Z_FLOOR = 7.4                                      # the model's tub underside; the STL puts it at z 0
# (key in rugged.build(), group, label, faces kept)
PARTS = [('pack_L', 'power', 'Pack, left: Zeee 2S 5200, on edge', 200), ('pack_R', 'power', 'Pack, right', 200),
         ('pi', 'brain', 'Raspberry Pi 5 + active cooler', 9000), ('hat', 'brain', 'M.2 HAT+', 50),
         ('hailo', 'brain', 'Hailo-8L', 50), ('pca', 'brain', 'PCA9685 servo board', 50),
         ('base', 'head', 'Head base (pan coil)', 16000), ('drum', 'head', 'Drum (turns with the head)', 8000),
         ('cradle', 'head', 'Cradle', 12000), ('ball', 'head', 'Ball (your rev 2)', 10000),
         ('arm_ubec', 'unbought', 'UBEC for the arm, 8 A', 50), ('ubec', 'unbought', 'Pi regulator, 5 V', 50),
         ('ina219', 'unbought', 'INA219 current sensor', 50), ('wifi', 'unbought', 'USB wifi dongle', 50),
         ('alarm', 'unbought', 'LiPo alarm', 50), ('pi_switch', 'unbought', 'Pi power switch', 50)]
WHEELS = [k + s for s in ('FL', 'FR', 'RL', 'RR') for k in ('pod_', 'motor_', 'rim_', 'tire_')]


def mesh(V, F, faces=None):
    """vertices and faces merged and, past faces, decimated: (V float32, F uint32)"""
    ms = ml.MeshSet(); ms.add_mesh(ml.Mesh(np.asarray(V, float), np.asarray(F, np.int32)))
    ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-4))
    if faces and ms.current_mesh().face_number() > faces:
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=faces, qualitythr=0.6, preserveboundary=True,
                                                   preservenormal=True, planarquadric=True, autoclean=True)
    return ms.current_mesh().vertex_matrix().astype('<f4'), ms.current_mesh().face_matrix().astype('<u4')


def soup(T, faces=None, shift=(0.0, 0.0, 0.0)):
    T = np.asarray(T, float).reshape(-1, 3, 3) + shift
    return mesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3), faces)


def box(x0, x1, y0, y1, z0, z1):
    V = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)], float)
    F = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    return V.astype('<f4'), np.array(F, '<u4')


def enc(V, F, label, group):
    return {'label': label, 'group': group, 'v': base64.b64encode(V.tobytes()).decode(),
            'f': base64.b64encode(F.tobytes()).decode(), 'bb': [V.min(0).tolist(), V.max(0).tolist()]}


def build():
    shift = (-RG.BODY_DX, 0.0, -Z_FLOOR)          # rugged's frame -> the tub STL's
    M = RG.build(); out = {}
    b = open(os.path.join(OUT, 'print', 'trainer_tub.stl'), 'rb').read(); n = int(np.frombuffer(b[80:84], '<u4')[0])
    T = np.frombuffer(b[84:84 + 50 * n], np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))['v']
    out['tub'] = enc(*soup(T), 'Tub, print 1 (276 x 140 x 50)', 'tub')
    for k, grp, label, faces in PARTS:
        out[k] = enc(*soup(M[k]['t'], faces, shift), label, grp)
    for s, (x0, x1, y0, y1, z0, z1) in ((s, TT.parts()['esc_' + s]) for s in 'LR'):   # his ESC, 45 x 24 x 34
        out['esc_' + s] = enc(*box(x0, x1, y0, y1, z0 - Z_FLOOR, z1 - Z_FLOOR), 'ESC, %s: your 45 x 24 x 34' % ('left' if s == 'L' else 'right'), 'power')
    for k in WHEELS:
        out[k] = enc(*soup(M[k]['t'], 1500, shift), M[k]['label'].split(':')[0], 'wheels')
    D = np.asarray(M['drum']['t'], float).reshape(-1, 3) + shift
    # the 250 mm cap measured from the tub's back wall (2026-11-07: the head is its own module, out of the box)
    meta = dict(pan=[float((D[:, 0].min() + D[:, 0].max()) / 2), float((D[:, 1].min() + D[:, 1].max()) / 2)],
                cap_x=float(np.frombuffer(T.tobytes(), '<f4').reshape(-1, 3)[:, 0].min() + 250.0), rim=50.0,
                ground=float(np.asarray(M['tire_FL']['t'], float)[..., 2].min() - Z_FLOOR))   # the grid: the ground under the tyres
    return out, meta


if __name__ == '__main__':
    parts, meta = build()
    data = 'window.TUB=' + json.dumps(parts) + ';window.META=' + json.dumps(meta) + ';'
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', data)
    p = os.path.join(OUT, 'tub_view.html'); open(p, 'w', encoding='utf-8').write(html)
    for k, v in parts.items():
        print('%-10s %s' % (k, [round(a) for a in v['bb'][0] + v['bb'][1]]))
    print('pan axis', [round(a, 1) for a in meta['pan']], 'cap line x %.1f' % meta['cap_x'])
    print('wrote %s (%.1f MB)' % (p, len(html) / 1e6))
