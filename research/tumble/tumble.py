"""Workstream D (Aim 2 pilot): does the robot land upright after a tumble? A MuJoCo drop simulation of the Trainer-
style robot under a pill-shaped shell (chassis-v2/sleek_sketch.py), as a function of its shape and mass layout.

    python research/tumble/tumble.py --demo          # three shapes, 200 drops each
    from tumble import trials; trials(params, n)     # counts of each rest state

Parameters (all in mm and g, body frame: X forward, Z up, ground clear of everything, the pan axis at X 115):
  top     the shell's highest point, 66 (the pill tub's flat top) .. 160 (a dome over the wheels and the head)
  round   how much of the half-width the top's curve takes, 0.1 (a small edge round) .. 1.0 (a full dome)
          (crown, the first version's one shape knob, survives as an alias: crown c -> top 66 + 12c, round 0.08 + 0.5c)
  dz      packs and electronics moved up (+) or down (-) inside the hull; the CoM height's main lever
  m_head  the head's mass (ball, servos, drum, base) at the nose, default 360
  rw      wheel radius, default 55 (the Trainer's 110 mm wheels); axles fixed at Z 30
  track   the wheels' centre-plane distance from the centre line, 131 (the Trainer's, wheels outside) .. 70 (tucked in)
  width   the shell's half-width, 65.75 (the tub's) .. 175 (wide enough to enclose the wheels, a skirt or cage)
  mu      every friction coefficient scaled by this (1.0 = floor 0.6, tyres 0.9, shell 0.4): the physics the surrogate
          is not given, used for its mutant

The mass model is a component list (4 wheel modules, 2 packs, head, electronics, shell); at the defaults its CoM is
~20 mm lower than chassis-v2/out/trainer.json's estimate, and the dz sweep covers both. A drop starts from a uniformly
random orientation with its lowest point 5 mm over the floor and a random spin up to 3 rad/s, and runs until the robot
has been still for 0.3 s (8 s at most). The rest state is the body axis nearest world up.
"""
import os, sys, json, argparse
import numpy as np
import mujoco

XN, XT, R0 = 115.0, -93.0, 65.75          # the pill: half-circle centres (the pan axis, the rear axle) and half-width
Z0 = 7.4                                  # its underside
AXLES, TRACK, ZA, TW = (91.0, -93.0), 131.0, 30.0, 46.0
HEAD = dict(ball=(115.0, 0.0, 111.4, 30.7), cradle=(115.0, 0.0, 70.0, 95.0, 36.0))
DEFAULT = dict(top=66.0, round=0.08, dz=0.0, m_head=360.0, rw=55.0, track=131.0, width=R0, mu=1.0)
WALL = 46.0                               # the walls' height before the top's curve starts (the crowned sketch's)


def norm(p):
    p = dict(DEFAULT, **(p or {}))
    if 'crown' in p:                                                    # the first version's knob
        c = p.pop('crown'); p['top'] = 66.0 + 12.0 * c; p['round'] = 0.08 + 0.5 * c
    return p
CLASSES = ('upright', 'inverted', 'left side', 'right side', 'nose up', 'nose down')


def shell_points(top, rnd, n=48, k=9, width=R0):
    """points on the shell's convex hull: the outline at the floor, the walls, then rings up a quarter-ellipse that
    takes `rnd` of the half-width and rises from the walls (or from 5 under the top, if the top is lower) to `top`"""
    R = width; hw = min(WALL, top - 5.0); b = top - hw; a = max(rnd, 0.02) * R
    def ring(r, z):
        """the outline inset to half-width r: its ends are half-ellipses reaching R0 * r / R past XN and XT, so the
        body stays the tub's length (339.5) whatever its width (first version: half-circles of radius r, which made a
        wide shell long too)"""
        c = R0 * r / R
        th = np.linspace(-np.pi / 2, np.pi / 2, n)
        f = np.c_[XN + c * np.cos(th), r * np.sin(th)]
        rear = np.c_[XT - c * np.cos(th), -r * np.sin(th)]
        P = np.vstack([f, rear]); return np.c_[P, np.full(len(P), z)]
    pts = [ring(R, Z0), ring(R, hw)]
    for phi in np.linspace(0, np.pi / 2, k)[1:]:
        pts.append(ring(R - a * (1 - np.cos(phi)), hw + b * np.sin(phi)))
    return np.vstack(pts)


SHELL_MASS = 'fixed'     # 'fixed': 600 g at Z 50 for every shape (as the sweep ran, 2026-10-13); 'area': the shell's
                         # mass scales with its surface area (600 g at the tub's) and sits at its area centroid
SHELL_FACTOR = 1.0       # 'area' only: the shell's mass per area as a fraction of the tub's (1.0 = 5.6 mm of solid PLA)
COVER_T = 1.0            # 'cover': the tub's 600 g stays where it was, and the shell area beyond the tub's is a cover of
                         # this many mm of solid PLA (1.24 g/cm3) at that extra area's centroid


def shell_mass(p):
    """(g, (x, y, z)) of the shell: SHELL_MASS 'fixed', or 'area' (added 2026-10-14: the fixed shell left a 210 mm dome
    as light and as low as the 66 mm tub, which understates a tall shell's CoM by ~40 mm)"""
    if SHELL_MASS == 'fixed':
        return 600.0, (-20.0, 0.0, 50.0)
    from scipy.spatial import ConvexHull
    def area(top, rnd, width):
        pts = shell_points(top, rnd, width=width); h = ConvexHull(pts); tri = pts[h.simplices]
        ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        keep = ~np.all(tri[:, :, 2] < Z0 + 0.5, axis=1)                  # no floor: the shell is open underneath
        c = (tri[keep].mean(1) * ar[keep, None]).sum(0) / ar[keep].sum()
        return ar[keep].sum(), c
    a0, c0 = area(66.0, 0.08, R0); a, c = area(p['top'], p['round'], p['width'])
    if SHELL_MASS == 'cover':
        extra = max(a - a0, 0.0); m_cov = 1.24e-3 * COVER_T * extra                 # mm2 x mm x g/mm3
        if extra < 1.0:
            return 600.0, (-20.0, 0.0, 50.0)
        ce = (a * c - a0 * c0) / extra
        M = 600.0 + m_cov; z = (600.0 * np.array([-20.0, 0.0, 50.0]) + m_cov * ce) / M
        return M, (float(z[0]), 0.0, float(z[2]))
    return SHELL_FACTOR * 600.0 * a / a0, (float(c[0]), 0.0, float(c[2]))


def mass_model(p):
    """(name, mass g, position mm, half-size mm or None) for the inertia; a box when half-size is given"""
    dz = p['dz']
    items = []
    for x in AXLES:
        for y in (p['track'], -p['track']):
            items.append(('wheel module', 361.0, (x, y, ZA), None))     # motor 205, tyre 76, rim 40, pod 40
    items += [('head', p['m_head'], (115.0, 0.0, 95.0), (30, 30, 30)),
              ('pack L', 300.0, (44.5, 53.0, 33.0 + dz), (70, 13, 23)), ('pack R', 300.0, (44.5, -53.0, 33.0 + dz), (70, 13, 23)),
              ('electronics', 300.0, (-40.0, 0.0, 45.0 + dz), (40, 30, 15)),
              ('shell', *shell_mass(p), (170, 65, 30))]
    return items


def inertia(items):
    M = sum(m for _, m, _, _ in items); c = sum(m * np.array(r) for _, m, r, _ in items) / M
    I = np.zeros((3, 3))
    for _, m, r, h in items:
        d = np.array(r) - c
        I += m * (d @ d * np.eye(3) - np.outer(d, d))
        if h is not None:
            a, b, cc = (2 * np.array(h)) ** 2
            I += m / 12 * np.diag([b + cc, a + cc, a + b])
    return M, c, I                                                      # g, mm, g mm^2


def xml(p):
    M, c, I = inertia(mass_model(p))
    s = 1e-3                                                            # mm -> m, g -> kg below
    pts = shell_points(p['top'], p['round'], width=p['width']) * s
    verts = ' '.join('%.5f' % v for v in pts.ravel())
    rw, mu = p['rw'] * s, p['mu']
    wheels = ''.join(f'<geom type="cylinder" size="{rw:.4f} {TW / 2 * s:.4f}" pos="{x * s:.4f} {y * s:.4f} {ZA * s:.4f}" '
                     f'euler="90 0 0" friction="{0.9 * mu:.3f} 0.01 0.001" rgba=".15 .15 .16 1"/>'
                     for x in AXLES for y in (p['track'], -p['track']))
    bx, by, bz, br = HEAD['ball']; cx, cy, cz0, cz1, cr = HEAD['cradle']
    I_si = I * 1e-3 * 1e-6                                              # g mm^2 -> kg m^2
    full = ' '.join('%.8g' % v for v in (I_si[0, 0], I_si[1, 1], I_si[2, 2], I_si[0, 1], I_si[0, 2], I_si[1, 2]))
    return f"""<mujoco model="tumble">
  <option timestep="0.001" gravity="0 0 -9.81"/>
  <asset><mesh name="shell" vertex="{verts}"/></asset>
  <worldbody>
    <geom type="plane" size="5 5 0.1" friction="{0.6 * p['mu']:.3f} 0.005 0.0005"/>
    <body name="robot" pos="0 0 0.5">
      <freejoint/>
      <inertial pos="{c[0] * s:.5f} {c[1] * s:.5f} {c[2] * s:.5f}" mass="{M * 1e-3:.4f}" fullinertia="{full}"/>
      <geom type="mesh" mesh="shell" friction="{0.4 * p['mu']:.3f} 0.005 0.0005" rgba=".72 .74 .76 1"/>
      {wheels}
      <geom type="sphere" size="{br * s:.4f}" pos="{bx * s:.4f} {by * s:.4f} {bz * s:.4f}" friction="{0.4 * p['mu']:.3f} 0.005 0.0005"/>
      <geom type="cylinder" size="{cr * s:.4f} {(cz1 - cz0) / 2 * s:.4f}" pos="{cx * s:.4f} {cy * s:.4f} {(cz0 + cz1) / 2 * s:.4f}"/>
    </body>
  </worldbody>
</mujoco>"""


def _extremes(p):
    """points standing in for every geom's extent, for placing the drop just over the floor"""
    pts = [shell_points(p['top'], p['round'], n=24, k=5, width=p['width'])]
    a = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    for x in AXLES:
        for y in (p['track'], -p['track']):
            for dy in (-TW / 2, TW / 2):
                pts.append(np.c_[x + p['rw'] * np.cos(a), np.full_like(a, y + dy), ZA + p['rw'] * np.sin(a)])
    bx, by, bz, br = HEAD['ball']
    g = np.random.default_rng(0).normal(size=(200, 3)); g /= np.linalg.norm(g, axis=1, keepdims=True)
    pts.append(np.array([bx, by, bz]) + br * g)
    return np.vstack(pts) * 1e-3


def classify(R):
    u = R.T @ np.array([0, 0, 1.0])                                      # world up, in the body frame
    i = int(np.argmax(np.abs(u)))
    return {(2, 1): 'upright', (2, -1): 'inverted', (1, 1): 'right side', (1, -1): 'left side',
            (0, 1): 'nose down', (0, -1): 'nose up'}[(i, int(np.sign(u[i])))]


def trials(p=None, n=200, seed=0, spin=3.0, return_tilts=False):
    p = norm(p)
    m = mujoco.MjModel.from_xml_string(xml(p)); d = mujoco.MjData(m)
    E = _extremes(p); rng = np.random.default_rng(seed)
    counts = {k: 0 for k in CLASSES}; tilts = []
    for _ in range(n):
        q = rng.normal(size=4); q /= np.linalg.norm(q)                  # uniform random orientation
        Rm = np.zeros(9); mujoco.mju_quat2Mat(Rm, q); Rm = Rm.reshape(3, 3)
        zmin = (E @ Rm.T)[:, 2].min()
        mujoco.mj_resetData(m, d)
        d.qpos[:3] = (0.0, 0.0, 0.005 - zmin); d.qpos[3:7] = q
        d.qvel[3:6] = rng.uniform(-1, 1, 3) * spin
        still = 0
        for _ in range(160):                                            # 160 x 50 ms = 8 s
            mujoco.mj_step(m, d, nstep=50)
            if np.abs(d.qvel).max() < 0.02:
                still += 1
                if still >= 6: break
            else:
                still = 0
        R = d.xmat[1].reshape(3, 3)
        counts[classify(R)] += 1
        tilts.append(float(np.degrees(np.arccos(np.clip(R[2, 2], -1, 1)))))
    out = dict(params=p, n=n, counts=counts, p_upright=counts['upright'] / n)
    if return_tilts:
        out['tilts'] = tilts
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--demo', action='store_true'); ap.add_argument('--n', type=int, default=200)
    a = ap.parse_args()
    for q in (dict(), dict(top=110, round=1.0), dict(top=160, round=1.0)):
        r = trials(q, a.n)
        M, c, _ = inertia(mass_model(norm(q)))
        print('%s  mass %.0f g  CoM z %.1f  P(upright) %.2f  %s' % (q, M, c[2], r['p_upright'], r['counts']), flush=True)
