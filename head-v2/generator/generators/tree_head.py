"""Whole tree-housing head for the 3D viewer: fixed roots + panning fork (both branches).

Reuses the SDF pieces in tree_arm.py. Concept geometry only -- not a print file.
Writes a compact JS mesh bundle (window.HEAD) for the viewer: python tree_head.py <out.js> [step]
"""
import sys, json, base64
import numpy as np

exec(open(__file__.replace('tree_head.py', 'tree_arm.py'), encoding='utf-8').read().split("if __name__")[0])

def mirror_y(p):
    return (p[0], np.abs(p[1]), p[2])

def tube(p, r, XS):
    """Wire channel along the same Bezier as branch(), thinner."""
    P = np.array([[0, 8, 13.0], [0, 30, 13.0], [0, 44, 17.0], [0, 44, H - 8]])
    ts = np.linspace(0, 1, 36)
    pts = ((1 - ts) ** 3)[:, None] * P[0] + (3 * (1 - ts) ** 2 * ts)[:, None] * P[1] \
        + (3 * (1 - ts) * ts ** 2)[:, None] * P[2] + (ts ** 3)[:, None] * P[3]
    d = None
    for c in pts:
        di = np.sqrt(((p[0] - c[0]) / XS) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2) - r
        d = di if d is None else np.minimum(d, di)
    return d

def fork_sdf(p):
    m = mirror_y(p)
    trunk = cyl_z(p, 0, 0, 20.0, BASE_Z, BASE_Z + 4.5) - 0.0
    saddle = rbox(p, (-14, -30, BASE_Z), (14, 30, BASE_Z + 4.5), 2.0)
    s = smin(smin(trunk, saddle, 3.0), branch(m), 5.0)
    s = smin(s, teardrop_pod(m), 5.0)
    s = np.maximum(s, -(np.sqrt(p[0] ** 2 + p[1] ** 2 + (p[2] - H) ** 2) - (R_BALL + BALL_CLEAR)))
    s = np.maximum(s, BASE_Z - p[2])            # flat underside: 0.5 mm above the roots, never on them
    # +Y: servo pocket, same as the test arm
    zb0, zb1 = H - SHAFT_TO_END - FIT, H + (SERVO_L - SHAFT_TO_END) + FIT
    zc = (zb0 + zb1) / 2
    tab_y = SERVO_TOP_Y + TAB_FROM_TOP
    body = box(p, (-SERVO_W / 2 - FIT, SERVO_TOP_Y - FIT, zb0), (SERVO_W / 2 + FIT, POD_Y1 + 1, zb1))
    tabs = box(p, (-SERVO_W / 2 - FIT, tab_y - FIT, zc - TAB_SPAN / 2 - FIT), (SERVO_W / 2 + FIT, POD_Y1 + 1, zc + TAB_SPAN / 2 + FIT))
    boss = cyl_y(p, 0, H, 6.6, POD_Y0 - 1, SERVO_TOP_Y + 0.1)
    s = np.maximum(s, -np.minimum(np.minimum(body, tabs), boss))
    # -Y: 6704 seat, hub hole, ribbon-coil chamber (closed outboard wall)
    s = np.maximum(s, -cyl_y(p, 0, H, 10.6, -POD_Y0 - 5, -POD_Y0 + 1))
    s = np.maximum(s, -cyl_y(p, 0, H, 13.6, -POD_Y0 - 4.4, -POD_Y0 - 0.4))
    s = np.maximum(s, -cyl_y(p, 0, H, 18.8, -POD_Y1 + 3, -POD_Y0 - 4.4))
    # wire channels inside both branches, dropping through the saddle
    s = np.maximum(s, -np.minimum(tube(m, 2.2, 2.0), cyl_z(m, 0, 11.0, 2.2, BASE_Z - 1, BASE_Z + 3)))
    return s

def roots_sdf(p):
    ped = cyl_z(p, 0, 0, 18.0, 0.0, 10.0)
    s = ped
    for a in np.radians([45, 135, 225, 315]):
        c, sn = np.cos(a), np.sin(a)
        u = p[0] * c + p[1] * sn - 22.0          # along the root
        v = -p[0] * sn + p[1] * c                # across
        w = p[2] - 1.2
        lobe = (np.sqrt((u / 16.0) ** 2 + (v / 6.0) ** 2 + (w / 3.2) ** 2) - 1.0) * 5.0
        s = smin(s, lobe, 6.0)
    s = np.maximum(s, -p[2])                     # flat on the deck
    s = np.maximum(s, p[2] - 10.0)
    s = np.maximum(s, -box(p, (-17.2, -6.4, -1), (6.2, 6.4, 9.0)))   # pan servo pocket
    for a in np.radians([45, 135, 225, 315]):    # root screws
        s = np.maximum(s, -cyl_z(p, 32 * np.cos(a), 32 * np.sin(a), 1.7, -1, 6))
    return s

if __name__ == '__main__':
    out_js = sys.argv[1]
    step = float(sys.argv[2]) if len(sys.argv) > 2 else 0.6
    bundle = {}
    for name, fn, lo, hi in (('fork', fork_sdf, (-30, -64, BASE_Z - 1), (30, 64, H + POD_R * 1.45 + 2)),
                             ('roots', roots_sdf, (-44, -44, -1), (44, 44, 11))):
        v, f = mesh(fn, lo, hi, step)
        bundle[name] = {'v': base64.b64encode(v.astype('<f4').tobytes()).decode(),
                        'f': base64.b64encode(f.astype('<u4').tobytes()).decode()}
        print(name, len(v), 'verts', len(f), 'tris', v.min(0).round(1), v.max(0).round(1))
    open(out_js, 'w').write('window.HEAD=' + json.dumps(bundle) + ';')
