"""Head v2 placement explorer: Zach's TEST-PRINT-2 body + head v2 on sliders, one HTML page
(published as the "Scorpion Head Placement" artifact). Writes chassis-v1/out/head_placement.html.

    python chassis-v1/head_placement.py

Data:
  - meshes (decimated): his body, batteries, Pi, old head (tank frame, as exported); head v2 parts in the
    head frame (pan axis at X 0 Y 0, Z 0 = the coil deck), moved live in the page.
  - the body as a 1 mm occupancy grid, and the head's base and turning parts as filled vertical columns
    (x, y, zmin, zmax at 1 mm), so the page counts the body material inside them for any placement.
"""
import os, sys, glob, json, base64
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tools')))
import config
from vox import load_stl, load_obj, _scan
import pymeshlab as ml

HERE = os.path.dirname(os.path.abspath(__file__)); R = config.REPO
OUT = os.path.join(HERE, 'out'); os.makedirs(OUT, exist_ok=True)
FF = os.path.join(R, 'chassis-v1', 'from_fusion', 'TEST-PRINT-2_Configuration 1_')
G = os.path.join(R, 'head-v2', 'generator', 'pan-coil-b', 'fusion')
FORK = os.path.join(R, 'head-v2', 'generator', 'tree-parts-b', 'fusion', 'fork.obj')
BALL = [os.path.join(config.OUT, 'rev2', k) for k in ('_fig_ball_plus.stl', '_fig_ball_minus_cup.stl')]

def b64(a): return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()

def pack(path, faces, label, group):
    ms = ml.MeshSet(); ms.load_new_mesh(path)
    if ms.current_mesh().face_number() > faces:
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=faces, qualitythr=0.6, preserveboundary=True,
                                                   preservenormal=True, planarquadric=True, autoclean=True)
    V = ms.current_mesh().vertex_matrix().astype('<f4'); F = ms.current_mesh().face_matrix().astype('<u4')
    return {'label': label, 'group': group, 'v': b64(V), 'f': b64(F)}

def grid(lo, hi):
    return [np.arange(l + 0.5, h, 1.0) for l, h in zip(lo, hi)]

def occupancy(T, g):
    return _scan(T, 2, g) & _scan(T, 0, g)

def columns(tris, lo, hi, dz=0.1):
    """Union of the parts, filled per vertical column: (x, y, zmin, zmax) of each occupied column.
    1 mm in plan, dz in Z, so a column's bottom and top are good to dz."""
    g = grid(lo[:2], hi[:2]) + [np.arange(lo[2] + dz / 2, hi[2], dz)]
    U = np.zeros((len(g[0]), len(g[1]), len(g[2])), bool)
    for T in tris: U |= _scan(T, 2, g)
    any_ = U.any(2); i, j = np.nonzero(any_)
    k0 = U.argmax(2)[i, j]; k1 = len(g[2]) - 1 - U[:, :, ::-1].argmax(2)[i, j]
    C = np.stack([g[0][i], g[1][j], g[2][k0], g[2][k1]], 1).astype('<f4')
    return C

if __name__ == '__main__':
    M = {}
    M['body'] = pack(FF + 'Tank_body.stl', 30000, 'Your body (TEST-PRINT-2)', 'tank')
    M['batt_l'] = pack(FF + 'LeftBattery.stl', 100, 'Left battery', 'tank')
    M['batt_r'] = pack(FF + 'RightBattery.stl', 100, 'Right battery', 'tank')
    M['pi'] = pack(FF + 'RASPBERRY_PI_5_WITH_ACTIVE_COOLER.stl', 9000, 'Raspberry Pi 5 + cooler', 'tank')
    olds = [p for p in glob.glob(FF + '*.stl') if any(k in p for k in ('pan_cap', 'brearing', 'tilt', 'z_mount'))]
    ms = ml.MeshSet()
    for p in olds: ms.load_new_mesh(p)
    ms.generate_by_merging_visible_meshes(); tmp = os.path.join(OUT, '_old_head.stl'); ms.save_current_mesh(tmp)
    M['old'] = pack(tmp, 12000, 'Old head (as exported)', 'old')
    for k, n, lab, grp in [('well', 'well', 'Base: coil well', 'base'), ('bay', 'bay', 'Base: gear bay', 'base'),
                           ('floor', 'floor', 'Base: floor plate', 'base'), ('gear_in', 'gear_in', 'Input gear', 'base'),
                           ('servo', 'servo', 'Pan servo (MG90S)', 'base'), ('drum', 'drum', 'Drum', 'turn'),
                           ('bearing', 'bearing', 'Pan bearing', 'turn'), ('gear_out', 'gear_out', 'Small gear', 'turn')]:
        M[k] = pack(os.path.join(G, n + '.obj'), {'well': 14000, 'bay': 9000, 'drum': 8000}.get(k, 3000), lab, grp)
    M['cradle'] = pack(FORK, 14000, 'Cradle', 'turn')
    M['ball_p'] = pack(BALL[0], 12000, 'Ball, + half', 'turn')
    M['ball_m'] = pack(BALL[1], 12000, 'Ball, − half', 'turn')

    body = load_stl(FF + 'Tank_body.stl')
    VLO, VHI = (-20, -66, 4), (126, 72, 62)
    g = grid(VLO, VHI); occ = occupancy(body, g)
    vox = {'lo': VLO, 'n': list(occ.shape), 'bits': b64(np.packbits(occ.ravel(), bitorder='little'))}

    base_t = [load_obj(os.path.join(G, n + '.obj')) for n in ('well', 'bay', 'floor', 'gear_in', 'servo', 'drum', 'bearing', 'gear_out')]
    turn_t = [load_obj(FORK)] + [load_stl(p) for p in BALL]
    CB = columns(base_t, (-46, -36, -41), (60, 36, 12))
    CH = columns(turn_t, (-46, -36, 9), (33, 36, 85))
    batt = []
    for n in ('LeftBattery', 'RightBattery'):
        T = load_stl(FF + n + '.stl').reshape(-1, 3); batt.append([T.min(0).round(2).tolist(), T.max(0).round(2).tolist()])
    bodyV = body.reshape(-1, 3)
    D = {'meshes': M, 'vox': vox, 'colsBase': b64(CB), 'colsHead': b64(CH), 'batt': batt,
         'baseZmin': float(min(T[..., 2].min() for T in base_t)), 'nose': float(bodyV[:, 0].max()), 'deck': 57.4,
         'oldAxis': [106.9, 3.4], 'tiltZ': 52.0, 'ballTop': float(max(T[..., 2].max() for T in turn_t))}
    html = open(os.path.join(HERE, 'head_placement_template.html'), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D) + ';')
    out = os.path.join(OUT, 'head_placement.html'); open(out, 'w', encoding='utf-8').write(html)
    print('columns base %d head %d  vox %s (%d set)  baseZmin %.1f  html %.1f MB'
          % (len(CB), len(CH), occ.shape, occ.sum(), D['baseZmin'], os.path.getsize(out) / 1e6))
