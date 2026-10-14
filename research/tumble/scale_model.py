"""Workstream E: printable test bodies for the physical tumble test, and the matching simulation.

A body's rest state on a flat table depends only on its convex hull and its mass layout. So each test body is the
convex hull of a design (shell, wheels, head), scaled down, with pockets for stacks of US quarters (5.67 g, 24.26 mm
across, 1.75 mm thick) that set its centre of mass. The low pocket and the high pocket let the same body be dropped
with its mass low and then high: the physical negative control.

    python research/tumble/scale_model.py NAME --top 200 --round 0.3 --width 170 [--scale 0.33]
      -> research/models/NAME.stl (print it base down) and research/models/NAME.json (geometry and pockets)

The simulation side, `predict(NAME, coins_low, coins_high, print_grams)`, builds the same hull in MuJoCo with the
mass layout of the print: the PLA's mass (the slicer's estimate, or a weighed one) spread like the printed solid, and
the coins in their pockets.
"""
import os, sys, json, argparse
import numpy as np
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import tumble as T

COIN_R, COIN_T, COIN_G = 24.26 / 2, 1.75, 5.67
POCKET_R = COIN_R + 0.35


def hull_points(p, scale):
    p = T.norm(p)
    pts = [T.shell_points(p['top'], p['round'], width=p['width'])]
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for x in T.AXLES:
        for y in (p['track'], -p['track']):
            for dy in (-T.TW / 2, T.TW / 2):
                pts.append(np.c_[x + p['rw'] * np.cos(a), np.full_like(a, y + dy), T.ZA + p['rw'] * np.sin(a)])
    bx, by, bz, br = T.HEAD['ball']
    u = np.random.default_rng(0).normal(size=(400, 3)); u /= np.linalg.norm(u, axis=1, keepdims=True)
    pts.append(np.array([bx, by, bz]) + br * u)
    P = np.vstack(pts)
    P = P - [0, 0, P[:, 2].min()]                                       # base on Z 0
    return P * scale


def hull_planes(P):
    h = ConvexHull(P)
    return h.equations, h                                               # rows (nx, ny, nz, d): n.x + d <= 0 inside


def pockets(P, coins=12):
    """one pocket on the centre line, opening on the base, as deep as most of the body: `coins` quarters and a
    printed spacer of the rest of its depth go in, loaded with the body upside down. Spacer first, then the coins: the
    coins sit by the base and the mass is low. Coins first, then the spacer: the coins fall to the pocket's top end
    and the same mass is high. Tape over the opening."""
    x = (P[:, 0].min() + P[:, 0].max()) / 2; h = P[:, 2].max()
    depth = round(0.78 * h, 1)
    return [dict(name='pocket', x=float(x), y=0.0, z0=0.0, depth=depth, coins=coins,
                 spacer=round(depth - coins * COIN_T - 0.4, 1))]


def cylinder(x, y, r, z0, z1, n=64):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = np.vstack([np.c_[x + r * np.cos(a), y + r * np.sin(a), np.full(n, z0)],
                   np.c_[x + r * np.cos(a), y + r * np.sin(a), np.full(n, z1)], [[x, y, z0], [x, y, z1]]])
    F = []
    for i in range(n):
        j = (i + 1) % n
        F += [[i, j, n + j], [i, n + j, n + i], [2 * n, j, i], [2 * n + 1, n + i, n + j]]
    return V, np.array(F)


def build(name, p, scale):
    """the hull as an exact solid (CadQuery, one planar face per hull facet), the pockets cut from it, saved as STL"""
    import cadquery as cq
    P = hull_points(p, scale); E, h = hull_planes(P); pk = pockets(P)
    faces = []
    for f in h.simplices:
        a, b, c = P[f]
        if np.cross(b - a, c - a) @ E[len(faces), :3] < 0:
            b, c = c, b
        faces.append(cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(*a), cq.Vector(*b), cq.Vector(*c)], close=True)))
    solid = cq.Solid.makeSolid(cq.Shell.makeShell(faces)).clean()
    body = cq.Workplane('XY').add(solid)
    for k in pk:
        body = body.cut(cq.Workplane('XY').workplane(offset=k['z0'] - 1.0).center(k['x'], k['y']).circle(POCKET_R)
                        .extrude(k['depth'] + 1.0))
        # the spacer, printed beside the body: a plug 0.25 under the pocket's radius, with a grip slot in one end
        sp = (cq.Workplane('XY').center(P[:, 0].max() + 20, 0).circle(POCKET_R - 0.25).extrude(k['spacer'])
              .faces('>Z').workplane().rect(3.0, 2 * POCKET_R).cutBlind(-2.0))
        body = body.add(sp)
    os.makedirs(os.path.join(ROOT, 'models'), exist_ok=True)
    stl = os.path.join(ROOT, 'models', name + '.stl')
    cq.exporters.export(body, stl, tolerance=0.05, angularTolerance=0.1)
    v = body.val()
    info = dict(name=name, params=T.norm(p), scale=scale, size=(P.max(0) - P.min(0)).round(1).tolist(),
                hull_volume_cm3=round(h.volume / 1000, 1), body_volume_cm3=round(v.Volume() / 1000, 1), valid=bool(v.isValid()),
                pockets=pk, coin=dict(r=COIN_R, t=COIN_T, g=COIN_G),
                coins_g=round(pk[0]['coins'] * COIN_G, 2), hull_facets=int(len(h.simplices)))
    json.dump(info, open(os.path.join(ROOT, 'models', name + '.json'), 'w'), indent=1)
    print(name, 'valid', info['valid'], info['size'], 'facets', info['hull_facets'], 'pocket', pk[0])
    return info


def mass_layout(info, print_grams, high):
    """(total g, CoM mm, inertia g mm^2) of a printed test body: the PLA spread as the hull's solid (infill and walls
    both, a guess the weighed or sliced grams anchor), the coins at the bottom of the pocket or on the spacer"""
    P = hull_points(info['params'], info['scale']); h = ConvexHull(P)
    # the hull's volume centroid and inertia by tetrahedra from an interior point
    o = P.mean(0); vol, c, I = 0.0, np.zeros(3), np.zeros((3, 3))
    for f in h.simplices:
        a, b, cc = P[f] - o; v = abs(np.dot(a, np.cross(b, cc))) / 6
        g = (a + b + cc) / 4; vol += v; c += v * g
    c = c / vol + o
    for f in h.simplices:
        a, b, cc = P[f] - c; v = abs(np.dot(a, np.cross(b, cc))) / 6
        Q = np.array([a, b, cc]); S = (Q.T @ Q + np.outer(Q.sum(0), Q.sum(0))) / 20   # second moment of the tetrahedron
        I += v * (np.trace(S) * np.eye(3) - S)
    k = info['pockets'][0]
    # the spacer: a printed plug, mostly walls at this size (a guess: 60% solid); it sits on the other side of the coins
    sp_vol = np.pi * (POCKET_R - 0.25) ** 2 * k['spacer'] / 1000; m_sp = sp_vol * 1.24 * 0.6
    m_pla = float(print_grams) - m_sp; rho = m_pla / vol                # the body; the slice's grams include the spacer
    n = k['coins']; m_c = n * COIN_G; stack = n * COIN_T
    zc = (k['depth'] - stack / 2) if high else stack / 2
    zs = (k['spacer'] / 2) if high else (stack + k['spacer'] / 2)
    cc, cs = np.array([k['x'], k['y'], zc]), np.array([k['x'], k['y'], zs])
    M = m_pla + m_c + m_sp; com = (m_pla * c + m_c * cc + m_sp * cs) / M
    It = rho * I
    for m, r in ((m_pla, c), (m_c, cc), (m_sp, cs)):
        d = r - com; It += m * (d @ d * np.eye(3) - np.outer(d, d))
    return M, com, It, P


def predict(name, print_grams, high, attitudes, jitter_deg=15.0, n_per=60, drop_mm=60.0, mu=1.0, seed=0, layout=None):
    """P(each rest state) for each starting attitude, by simulating the printed body with hand jitter. `layout`
    (total g, CoM mm, inertia g mm^2) replaces mass_layout's uniform-solid estimate when given."""
    import mujoco
    info = json.load(open(os.path.join(ROOT, 'models', name + '.json')))
    if layout is None:
        M, com, I, P = mass_layout(info, print_grams, high)
    else:
        (M, com, I), P = layout, hull_points(info['params'], info['scale'])
    s = 1e-3
    verts = ' '.join('%.5f' % v for v in (P * s).ravel())
    Isi = I * 1e-9
    full = ' '.join('%.8g' % v for v in (Isi[0, 0], Isi[1, 1], Isi[2, 2], Isi[0, 1], Isi[0, 2], Isi[1, 2]))
    xml = f"""<mujoco><option timestep="0.0005"/><asset><mesh name="h" vertex="{verts}"/></asset><worldbody>
      <geom type="plane" size="2 2 .1" friction="{0.45 * mu:.3f} 0.005 0.0005"/>
      <body name="b" pos="0 0 .3"><freejoint/>
        <inertial pos="{com[0] * s:.5f} {com[1] * s:.5f} {com[2] * s:.5f}" mass="{M * 1e-3:.5f}" fullinertia="{full}"/>
        <geom type="mesh" mesh="h" friction="{0.45 * mu:.3f} 0.005 0.0005"/></body></worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
    rng = np.random.default_rng(seed); out = {}
    Ps = P * s
    for att, (roll, pitch) in attitudes.items():
        cnt = {k: 0 for k in T.CLASSES}
        for _ in range(n_per):
            r = np.radians(roll + rng.normal(0, jitter_deg / 2)); pt = np.radians(pitch + rng.normal(0, jitter_deg / 2))
            yw = rng.uniform(0, 2 * np.pi)
            q = np.zeros(4); mujoco.mju_euler2Quat(q, np.array([r, pt, yw]), 'xyz')
            R9 = np.zeros(9); mujoco.mju_quat2Mat(R9, q); R = R9.reshape(3, 3)
            mujoco.mj_resetData(m, d)
            d.qpos[:3] = (0, 0, drop_mm * s - (Ps @ R.T)[:, 2].min()); d.qpos[3:7] = q
            still = 0
            for _ in range(240):
                mujoco.mj_step(m, d, nstep=40)
                if np.abs(d.qvel).max() < 0.01:
                    still += 1
                    if still >= 6: break
                else:
                    still = 0
            cnt[T.classify(d.xmat[1].reshape(3, 3))] += 1
        out[att] = {k: v / n_per for k, v in cnt.items() if v}
    return dict(name=name, high=high, mass_g=round(M, 1), com_mm=com.round(1).tolist(), by_attitude=out)


ATTITUDES = {'nose down': (0, 90), 'tail down': (0, -90), 'left side down': (90, 0), 'right side down': (-90, 0),
             'upside down': (180, 0), 'upside down, 45 to the left': (135, 0)}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('name')
    for k in ('top', 'round', 'width', 'dz'):
        ap.add_argument('--' + k, type=float)
    ap.add_argument('--scale', type=float, default=0.33)
    a = ap.parse_args()
    p = {k: getattr(a, k) for k in ('top', 'round', 'width', 'dz') if getattr(a, k) is not None}
    build(a.name, p, a.scale)
