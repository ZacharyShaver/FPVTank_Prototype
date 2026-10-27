"""The designs the gauges read, each as one plain robot spec, and the MuJoCo model built from it.

    python gauges/robots.py      # builds the roster, prints each design's mass and size

A spec is a dict, in mm, g and the ground frame (X forward, Y left, Z up, the floor at Z 0 with the robot on its
wheels):
  hulls    convex point sets, each its own collision geom (the body, the pods, a shell)
  M, com, I    the body's mass, centre of mass and inertia about it (g, mm, g mm2), wheels' tyres and rims excluded
  wheels   axles (x, y); R, TW the tyre's radius and width; m_w its tyre and rim (g); I_w (kg m2 about the axle)
  motor, kv    the drive (research/tumble/wheels3.MOTOR and KV), copied in so the sims needn't import the builders

The builders import the research sims (slow, ~6 s), so only the main process calls them.
"""
import os, sys
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
sys.path.insert(0, config.TUMBLE)

S = 1e-3
CONTACT = dict(tc=0.002, dr=0.35, dt=0.0002)      # hard floor, the ball's measured bounce (chassis3.CONTACT)
FRICTION = dict(floor=0.6, tyre=0.9, body=0.4)    # at x1; MuJoCo takes the larger of a contact pair's


def inertia(items, box):
    """M, CoM and inertia about it from point masses, each a box of half-size box[name] when it has one
    (chassis3.xml's sum)"""
    M = sum(m for _, m, _ in items); G = sum(m * np.asarray(q, float) for _, m, q in items) / M; I = np.zeros((3, 3))
    for n, m, q in items:
        d = np.asarray(q, float) - G; I += m * (d @ d * np.eye(3) - np.outer(d, d))
        h = box.get(n)
        if h is not None:
            a, b, c = (2 * np.asarray(h, float)) ** 2; I += m / 12 * np.diag([b + c, a + c, a + b])
    return float(M), G, I


def wheel_mass(R):
    """the Trainer's tyre and rim scaled to radius R (chassis3.design): g, kg m2 about the axle"""
    m_t, m_r = 75.7 * R / 55.0, 79.8 * (R / 55.0) ** 2
    return m_t + m_r, (m_t * (0.91 * R) ** 2 + m_r * (0.55 * R) ** 2) * 1e-9


def hull(P):
    P = np.asarray(P, float); return P[ConvexHull(P).vertices]


def spec(name, hulls, M, com, I, axles, R, TW=46.0, m_w=None, I_w=None, notes=()):
    import wheels3 as W3
    if m_w is None:
        m_w, I_w = wheel_mass(R)
    sp = dict(name=name, hulls=[hull(h) for h in hulls], M=float(M), com=np.asarray(com, float), I=np.asarray(I, float),
              wheels=[(float(x), float(y)) for x, y in axles], R=float(R), TW=float(TW), m_w=float(m_w), I_w=float(I_w),
              motor=dict(W3.MOTOR), kv=float(W3.KV), notes=list(notes))
    return dims(sp)


def extremes(sp, n=16):
    """points standing in for every geom's extent: the hulls' vertices, each tyre's rims, and the tail stowed"""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False); R = sp['R']; pts = list(sp['hulls'])
    for x, y in sp['wheels']:
        for dy in (-sp['TW'] / 2, sp['TW'] / 2):
            pts.append(np.c_[x + R * np.cos(a), np.full(n, y + dy), R + R * np.sin(a)])
    if sp.get('limb'):
        pts.append(limb_points(sp['limb'], 0.0, sp['limb']['th_stow']))
    return np.vstack(pts)


def dims(sp):
    E = extremes(sp); lo, hi = E.min(0), E.max(0); lm = sp.get('limb')
    sp.update(length=float(hi[0] - lo[0]), width=float(hi[1] - lo[1]), height=float(hi[2] - lo[2]),
              mass=float(sp['M'] + len(sp['wheels']) * sp['m_w'] + (lm['m_base'] + lm['m_link'] + lm['m_foot'] if lm else 0.0)),
              belly=float(min(h[:, 2].min() for h in sp['hulls'])))
    return sp


# ---------- the tail ----------
# A tail on a turntable at the rear (2026-10-26): yaw about Z, then one pitched link with a rubber foot. Pitch 0 points
# straight back, +90 up, 180 forward over the top; yaw turns that plane, so the link's zero points along
# (-cos yaw, -sin yaw, 0). Two position servos with a torque limit; their masses scale with it (guesses).
LIMB_PITCH, LIMB_YAW = (-120.0, 180.0), (-180.0, 180.0)   # degrees
FOOT_R, LINK_R = 12.0, 8.0                                 # mm
LIMB_KP, LIMB_DAMP, LIMB_ARM = 30.0, 0.3, 0.002            # N m/rad, N m s/rad, kg m2


def limb_mount(hulls, mz=1.0):
    """the tail's base: on the centre line, mz of the way from the belly up to the body's top at its rear (1: the top,
    as on the Trainer; a dome's top is too high for a short tail to reach the floor), 20 mm behind the outermost
    surface at that height (the skin's, when there is one), so the link clears everything behind and beside it"""
    body = hulls[0]; lo = float(body[:, 2].min()); hi = float(body[body[:, 0] < body[:, 0].min() + 40][:, 2].max())
    zb = lo + mz * (hi - lo); xs = []
    for P in hulls:
        h = ConvexHull(P); n, off = h.equations[:, :3], h.equations[:, 3]
        lim = -(n[:, 2] * zb + off)                            # inside: n_x x <= lim along the line (x, 0, zb)
        back = n[:, 0] < -1e-9
        if np.all(lim[~back & (np.abs(n[:, 0]) < 1e-9)] >= 0) and back.any():
            lo = (lim[back] / n[back, 0]).max()                # the line enters the hull here
            front = n[:, 0] > 1e-9
            if not front.any() or lo <= (lim[front] / n[front, 0]).min():
                xs.append(lo)
    return np.array([(min(xs) if xs else body[:, 0].min()) - 20.0, 0.0, zb])


def limb_points(lm, yaw, pitch, k=8):
    """points along the link and round the foot at a pose (degrees), body frame, mm"""
    y, p = np.radians(yaw), np.radians(pitch); h = np.array([-np.cos(y), -np.sin(y), 0.0])
    d = np.cos(p) * h + np.array([0.0, 0.0, np.sin(p)]); B = np.asarray(lm['base'], float)
    line = B + np.outer(np.linspace(0, 1, k), d * lm['L'])
    tip = B + d * lm['L']; foot = tip + FOOT_R * np.vstack([np.eye(3), -np.eye(3)])
    return np.vstack([line, foot])


def add_limb(sp, L, tq, th_push, th_stow, mz=1.0, base=None):
    """the spec with a tail: link L mm, servo stall tq N m, the step push's pitch and the stowed pitch (degrees), and
    the mount's height as a fraction (limb_mount); base (mm, body frame) pins the mount instead (the shape study)"""
    lm = dict(base=(limb_mount(sp['hulls'], mz) if base is None else np.asarray(base, float)).tolist(), L=float(L), tq=float(tq), th_push=float(th_push), th_stow=float(th_stow), mz=float(mz),
              m_base=2 * (45.0 + 8.0 * tq), m_link=0.3 * L, m_foot=15.0)
    out = dict(sp, limb=lm, notes=list(sp['notes']) + [f'tail {L:.0f} mm, {tq:.1f} N m'])
    return dims(out)


EDGE_R = 3.0                                      # mm: the step's top edge is this round (a capsule)


def xml(sp, mu=1.0, step=None, dt=None, edge='round'):
    """MJCF: the robot (free) with its hulls and its wheels on armatured hinges (wheels3's rotor model, chassis3's
    layout); `step` (mm) a step up at X 0. mu scales every friction.

    edge 'round' (2026-10-26): the step's top edge is a capsule of EDGE_R, its face EDGE_R behind it. A sharp box edge
    met by a cylinder gets the face's normal, (1, 0, 0): the tyre hits a wall and spins in place, so the Trainer
    stalled at a 10 mm step 1 time in 5. chassis3's steps have that sharp edge. 'sharp' keeps it, for the control."""
    dt = dt or CONTACT['dt']; M, G, I = sp['M'], sp['com'], sp['I'] * 1e-9
    full = ' '.join('%.8g' % v for v in (I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2]))
    mo = sp['motor']; Ie = sp['I_w'] + mo['N'] * mo['Ir']; arm = (mo['N'] ** 2 - mo['N']) * mo['Ir']; R = sp['R']
    mk = sp['m_w'] * 1e-3; It = max(mk * (3 * (R * S) ** 2 + (sp['TW'] * S) ** 2) / 12, 0.5 * Ie * 1.001)
    f = {k: '%.4f 0.005 0.0005' % (v * mu) for k, v in FRICTION.items()}
    wb = ''.join(f'<body name="w{i}" pos="{x * S:.4f} {y * S:.4f} {R * S:.4f}"><joint name="j{i}" type="hinge" axis="0 1 0" armature="{arm:.6g}"/>'
                 f'<inertial pos="0 0 0" mass="{mk:.4f}" diaginertia="{It:.6g} {Ie:.6g} {It:.6g}"/>'
                 f'<geom type="cylinder" size="{R * S:.4f} {sp["TW"] / 2 * S:.4f}" euler="90 0 0" friction="{f["tyre"]}"/></body>'
                 for i, (x, y) in enumerate(sp['wheels']))
    lm = sp.get('limb'); ca = ' conaffinity="3"' if lm else ''           # the floor also meets the tail (contype 2)
    floor = f'<geom type="plane" size="8 8 0.1" friction="{f["floor"]}"{ca}/>'
    if step:
        r = EDGE_R * S if edge == 'round' else 0.0; h = step * S
        floor += f'<geom type="box" size="2 2 {h / 2:.5f}" pos="{2 + r:.5f} 0 {h / 2:.5f}" friction="{f["floor"]}"{ca}/>'
        if r:
            floor += f'<geom type="capsule" fromto="{r:.5f} -2 {h - r:.5f} {r:.5f} 2 {h - r:.5f}" size="{r:.5f}" friction="{f["floor"]}"{ca}/>'
    tail, act = '', ''
    if lm:                                                                # the tail meets the floor only, never the robot
        B = np.asarray(lm['base']) * S; L = lm['L'] * S; ml = (lm['m_link'] + lm['m_foot']) * 1e-3
        cx = -(lm['m_link'] * L / 2 + lm['m_foot'] * L) * 1e-3 / ml; Iy = (lm['m_link'] * L * L / 3 + lm['m_foot'] * L * L) * 1e-3
        Iy = max(Iy - ml * cx * cx, 1e-6); mb = lm['m_base'] * 1e-3
        tail = (f'<body name="lyaw" pos="{B[0]:.5f} {B[1]:.5f} {B[2]:.5f}"><joint name="ly" type="hinge" axis="0 0 1" range="{LIMB_YAW[0]} {LIMB_YAW[1]}" '
                f'damping="{LIMB_DAMP}" armature="{LIMB_ARM}"/><inertial pos="0 0 0" mass="{mb:.4f}" diaginertia="2e-5 2e-5 2e-5"/>'
                f'<body name="llink"><joint name="lp" type="hinge" axis="0 1 0" range="{LIMB_PITCH[0]} {LIMB_PITCH[1]}" damping="{LIMB_DAMP}" armature="{LIMB_ARM}"/>'
                f'<inertial pos="{cx:.5f} 0 0" mass="{ml:.4f}" diaginertia="2e-6 {Iy:.6g} {Iy:.6g}"/>'
                f'<geom type="capsule" fromto="0 0 0 {-L:.5f} 0 0" size="{LINK_R * S:.4f}" contype="2" conaffinity="0" friction="{f["tyre"]}"/>'
                f'<geom type="sphere" pos="{-L:.5f} 0 0" size="{FOOT_R * S:.4f}" contype="2" conaffinity="0" friction="{f["tyre"]}"/></body></body>')
        act = (f'<actuator><position name="ay" joint="ly" kp="{LIMB_KP}" forcelimited="true" forcerange="{-lm["tq"]:.3f} {lm["tq"]:.3f}"/>'
               f'<position name="ap" joint="lp" kp="{LIMB_KP}" forcelimited="true" forcerange="{-lm["tq"]:.3f} {lm["tq"]:.3f}"/></actuator>')
    meshes = ''.join(f'<mesh name="h{i}" vertex="{" ".join("%.5f" % v for v in (P * S).ravel())}"/>' for i, P in enumerate(sp['hulls']))
    geoms = ''.join(f'<geom type="mesh" mesh="h{i}" friction="{f["body"]}"/>' for i in range(len(sp['hulls'])))
    return f"""<mujoco><option timestep="{dt}"/><default><geom solref="{CONTACT['tc']} {CONTACT['dr']}"/></default>
      <asset>{meshes}</asset><worldbody>{floor}
      <body name="robot" pos="0 0 0.5"><freejoint/>
        <inertial pos="{G[0] * S:.5f} {G[1] * S:.5f} {G[2] * S:.5f}" mass="{M * 1e-3:.4f}" fullinertia="{full}"/>
        {geoms}{wb}{tail}</body></worldbody>{act}</mujoco>"""


# ---------- the roster ----------
def _built(wheels):
    import built3 as B3
    return B3.design(B3.cache(wheels))


def from_built(name, D, notes=()):
    """a spec from a chassis3/built3 design dict (body hull + pods, items, boxes)"""
    M, G, I = inertia(D['items'], D['box'])
    return spec(name, [D['pts']] + list(D.get('extra', [])), M, G, I, D['axles'].values(), D['R'], m_w=D['m_w'] / 1.0,
                I_w=D['I_w'], notes=notes)


def trainer():
    return from_built('Trainer', _built('4'), ['chassis-v2 SCORPION_LEGS=wheels, built meshes'])


def step_layout():
    return from_built('Step layout', _built('step'), ['chassis-v2 SCORPION_WHEELS=step, built meshes'])


def six_wheel():
    return from_built('Six-wheel', _built('6'), ['chassis-v2 SCORPION_WHEELS=6, built meshes'])


def box(base=None, R=None, stretch=1.0, name='Box'):
    """the negative control: the Trainer's parts and masses in a plain box, its body's and pods' bounding box, on the
    Trainer's wheels. R: other wheels, the body raised by the radius's change (same belly clearance); stretch: the box
    and the axles stretched along X."""
    b = base or trainer()
    P = np.vstack(b['hulls']); lo, hi = P.min(0), P.max(0)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    k = np.diag([stretch, 1.0, 1.0]); dz = 0.0 if R is None else R - b['R']
    C = corners @ k + [0, 0, dz]; com = b['com'] @ k + [0, 0, dz]
    I = b['I'] if stretch == 1.0 else _stretch_I(b['I'], stretch)
    axles = [(x * stretch, y) for x, y in b['wheels']]
    notes = ['the Trainer\'s parts in a plain box'] + ([f'R {R:.0f}, body up {dz:.0f}'] if R else []) + ([f'stretched {stretch:g}x in X'] if stretch != 1.0 else [])
    w = dict(m_w=b['m_w'], I_w=b['I_w']) if R is None else {}
    return spec(name, [C], b['M'], com, I, axles, R or b['R'], notes=notes, **w)


def _stretch_I(I, s):
    """inertia of a mass layout stretched by s along X: the X second moment scales by s^2"""
    Sxx = 0.5 * (I[1, 1] + I[2, 2] - I[0, 0]); Syy = 0.5 * (I[0, 0] + I[2, 2] - I[1, 1]); Szz = 0.5 * (I[0, 0] + I[1, 1] - I[2, 2])
    Sxx *= s * s; return np.diag([Syy + Szz, Sxx + Szz, Sxx + Syy])


def e4(roof_g=0.0, name='E4 weeble'):
    """the E4_weeble shell (research/models/E4_weeble.json) over the sweep's robot (shell3.robot_layout: tumble's mass
    model, the tub's 600 g, a 1.5 mm cover), moved to the ground frame. Its tyres and rims come out of the body's mass
    and ride on the wheels. roof_g: a weight 30 mm under the shell's top (the upright gauge's control, like the drop
    tests' coins high)."""
    import json
    import shell3 as S3, tumble as T
    q = json.load(open(os.path.join(config.REPO, 'research', 'models', 'E4_weeble.json')))['params']
    Mt, ct, It, _ = S3.robot_layout(q, dz=0.0, cover=1.5)
    if roof_g:
        p = np.array([q['xc'], 0.0, q['zc'] + q['cu'] - 30.0]); M2 = Mt + roof_g; c2 = (Mt * ct + roof_g * p) / M2
        d0, d1 = ct - c2, p - c2
        It = It + Mt * (d0 @ d0 * np.eye(3) - np.outer(d0, d0)) + roof_g * (d1 @ d1 * np.eye(3) - np.outer(d1, d1)); Mt, ct = M2, c2
    up = np.array([0, 0, -S3.FLOOR])                                       # tumble's floor is Z -25
    R = 55.0; m_w, I_w = wheel_mass(R)
    axles = [(x, y) for x in T.AXLES for y in (T.TRACK, -T.TRACK)]
    wpos = [np.array([x, y, T.ZA]) for x, y in axles]
    Io = It + Mt * (ct @ ct * np.eye(3) - np.outer(ct, ct))                 # about the origin, then the wheels out
    M, mc = Mt, Mt * ct
    for p in wpos:
        Io -= m_w * (p @ p * np.eye(3) - np.outer(p, p)); M -= m_w; mc = mc - m_w * p
    c = mc / M; I = Io - M * (c @ c * np.eye(3) - np.outer(c, c))
    hulls = [S3.shell_points(q) + up, T.shell_points(66.0, 0.08) + up]
    return spec(name, hulls, M, c + up, I, axles, R, m_w=m_w, I_w=I_w,
                notes=['the sweep\'s robot (tumble.py) under the E4 shell, 1.5 mm cover'] + ([f'{roof_g:.0f} g on the roof'] if roof_g else []))


def roster():
    """the designs scored, the box first"""
    t = trainer()
    return [box(t), t, step_layout(), six_wheel(), e4()]


if __name__ == '__main__':
    for sp in roster():
        print(f"{sp['name']:12s} {sp['mass']:6.0f} g  {sp['length']:4.0f} x {sp['width']:4.0f} x {sp['height']:4.0f} mm  "
              f"belly {sp['belly']:5.1f}  {len(sp['wheels'])} wheels R {sp['R']:.0f}  CoM z {sp['com'][2]:.1f}  {sp['notes']}")
