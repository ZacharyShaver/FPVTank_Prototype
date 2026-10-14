"""Audit (2026-10-14) of the scale-model drop simulation: physics sanity tests. See AUDIT.md.

    python research/tumble/audit/audit_sim.py [pen|static|bounce|all]
"""
import os, sys, json
import numpy as np, mujoco
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import scale_model as S, predict_drops as PD, tumble as T
from scipy.spatial import ConvexHull
from matplotlib.path import Path

ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))


def model(name, high, timestep=0.0005, solref=None, mu=1.0):
    info = json.load(open(os.path.join(ROOT, 'models', name + '.json')))
    M, com, I, P = S.mass_layout(info, PD.GRAMS[name], high)
    s = 1e-3; verts = ' '.join('%.5f' % v for v in (P * s).ravel()); Isi = I * 1e-9
    full = ' '.join('%.8g' % v for v in (Isi[0, 0], Isi[1, 1], Isi[2, 2], Isi[0, 1], Isi[0, 2], Isi[1, 2]))
    sr = f' solref="{solref[0]} {solref[1]}"' if solref else ''
    xml = f"""<mujoco><option timestep="{timestep}"/><asset><mesh name="h" vertex="{verts}"/></asset><worldbody>
      <geom type="plane" size="2 2 .1" friction="{0.45 * mu:.3f} 0.005 0.0005"{sr}/>
      <body name="b" pos="0 0 .3"><freejoint/>
        <inertial pos="{com[0] * s:.5f} {com[1] * s:.5f} {com[2] * s:.5f}" mass="{M * 1e-3:.5f}" fullinertia="{full}"/>
        <geom type="mesh" mesh="h" friction="{0.45 * mu:.3f} 0.005 0.0005"{sr}/></body></worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml)
    return m, mujoco.MjData(m), P * s, com * s


def place(m, d, Ps, R, h):
    q = np.zeros(4); mujoco.mju_mat2Quat(q, R.ravel())
    mujoco.mj_resetData(m, d); d.qpos[:3] = (0, 0, h - (Ps @ R.T)[:, 2].min()); d.qpos[3:7] = q


AX = {'+Z down (inverted)': np.diag([1, -1, -1.0]), '-Z down (upright)': np.eye(3),
      '+X down': None, '-X down': None, '+Y down': None, '-Y down': None}


def R_down(axis):
    """a rotation putting body `axis` (unit vector) pointing at world -Z"""
    a = np.asarray(axis, float); t = np.array([0, 0, -1.0]); v = np.cross(a, t); c = a @ t
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


FACES = {'base down': [0, 0, -1], 'top down': [0, 0, 1], 'head end down (+X)': [1, 0, 0], 'blunt end down (-X)': [-1, 0, 0],
         '+Y side down': [0, 1, 0], '-Y side down': [0, -1, 0]}


def static_stable(Ps, com, R, tol=0.3e-3):
    """analytic: with body axis down as R puts it, is the CoM over the support polygon of the lowest points?"""
    W = Ps @ R.T; c = R @ com; z0 = W[:, 2].min()
    sup = W[W[:, 2] < z0 + tol][:, :2]
    if len(sup) < 3: return False, 0.0
    h = ConvexHull(sup); poly = Path(sup[h.vertices])
    inside = poly.contains_point(c[:2])
    # margin: distance from the CoM projection to the polygon edge (negative outside)
    E = h.equations; marg = -(E[:, :2] @ c[:2] + E[:, 2]).max()
    return bool(inside), float(marg * 1e3)


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    names = ('E1_tub', 'E2_dome', 'E3_tall')
    if which in ('all', 'pen'):
        print('== T1 resting penetration (body at rest on its base, default contact)')
        for n in names:
            for sr in (None, (0.005, 1), (0.002, 1)):
                m, d, Ps, com = model(n, False, solref=sr); place(m, d, Ps, np.eye(3), 0.0005)
                mujoco.mj_step(m, d, nstep=6000)
                R = d.xmat[1].reshape(3, 3); W = Ps @ R.T + d.xpos[1]
                print(f'  {n} solref {sr or "default 0.02 1"}: lowest point {W[:, 2].min() * 1e3:+.2f} mm (negative = in the floor)')
    if which in ('all', 'static'):
        print('== T2 static stability of each face: analytic (CoM over support) vs simulated (placed 0.5 mm up, 3 s)')
        for n in names:
            for high in (False, True):
                m, d, Ps, com = model(n, high)
                for f, ax in FACES.items():
                    R = R_down(ax); st, marg = static_stable(Ps, com, R)
                    place(m, d, Ps, R, 0.0005); mujoco.mj_step(m, d, nstep=6000)
                    cls = T.classify(d.xmat[1].reshape(3, 3))
                    print(f'  {n} mass {"high" if high else "low"} {f:<22} analytic {"stable" if st else "tips  "} (margin {marg:+5.1f} mm)  sim -> {cls}')
    if which in ('all', 'bounce'):
        print('== T3 bounce: upright, flat, from 60 mm; rebound height after the first impact')
        for sr in (None, (0.005, 1), (0.002, 1), (0.002, 0.3), (0.002, 0.15)):
            m, d, Ps, com = model('E3_tall', False, solref=sr); place(m, d, Ps, np.eye(3), 0.060)
            zs = []
            for _ in range(800):
                mujoco.mj_step(m, d, nstep=1); zs.append(d.xpos[1][2] + (Ps @ d.xmat[1].reshape(3, 3).T)[:, 2].min())
            zs = np.array(zs); i = int(np.argmax(zs < 0.0005)); reb = zs[i:].max()
            print(f'  solref {sr or "default 0.02 1"}: rebound {reb * 1e3:.2f} mm  -> restitution {np.sqrt(max(reb, 0) / 0.06):.2f}')
