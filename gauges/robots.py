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
FRICTION = dict(floor=0.6, tyre=0.9, body=0.4)    # at x1; MuJoCo takes the larger of a contact pair's, except that the
# tyres have contact priority (2026-10-27), so a tread grip (sp['tyre_mu']) below the floor's is not overruled. At grip 1
# the tyre's 0.9 was the larger anyway, so nothing read before changes.


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


def hull_dist(P, Q):
    """the signed distance (mm) of each point of Q from the convex hull of P: negative inside (minus the depth to the
    nearest face), else the exact distance to the nearest triangle"""
    h = ConvexHull(np.asarray(P, float)); Q = np.atleast_2d(np.asarray(Q, float))
    s = (Q @ h.equations[:, :3].T + h.equations[:, 3]).max(1); out = s.copy()
    T = h.points[h.simplices]; A, B, C = T[:, 0], T[:, 1], T[:, 2]
    for i in np.where(s > 0)[0]:                                          # outside: the closest point on each triangle
        p = Q[i]; ab, ac, ap = B - A, C - A, p - A
        d1, d2 = (ab * ap).sum(1), (ac * ap).sum(1); bp = p - B; d3, d4 = (ab * bp).sum(1), (ac * bp).sum(1)
        cp = p - C; d5, d6 = (ab * cp).sum(1), (ac * cp).sum(1)
        va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
        den = np.where(np.abs(va + vb + vc) < 1e-12, 1e-12, va + vb + vc)
        v, w = vb / den, vc / den; X = A + ab * v[:, None] + ac * w[:, None]          # inside the face
        def seg(P0, P1):
            e = P1 - P0; t = np.clip(((p - P0) * e).sum(1) / np.maximum((e * e).sum(1), 1e-12), 0, 1); return P0 + e * t[:, None]
        out_face = (va < 0) | (vb < 0) | (vc < 0)
        if out_face.any():                                                # else the nearest of the three edges
            E = np.stack([seg(A, B), seg(B, C), seg(C, A)]); k = np.linalg.norm(E - p, axis=2).argmin(0)
            X[out_face] = E[k, np.arange(len(A))][out_face]
        out[i] = float(np.linalg.norm(X - p, axis=1).min())
    return out


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
    if sp.get('flip'):
        pts.append(flip_points(sp['flip'], sp['flip']['stow']))
    for p0, p1, r in sp.get('struts', ()):                               # printed supports (body_tree), capsules
        pts.append(np.vstack([np.asarray(p0) + r * np.vstack([np.eye(3), -np.eye(3)]), np.asarray(p1) + r * np.vstack([np.eye(3), -np.eye(3)])]))
    return np.vstack(pts)


def dims(sp):
    E = extremes(sp); lo, hi = E.min(0), E.max(0); lm = sp.get('limb'); fl = sp.get('flip')
    sp.update(length=float(hi[0] - lo[0]), width=float(hi[1] - lo[1]), height=float(hi[2] - lo[2]),
              mass=float(sp['M'] + len(sp['wheels']) * sp['m_w'] + (lm['m_base'] + lm['m_link'] + lm['m_foot'] if lm else 0.0)
                         + (len(fl['pivots']) * (fl['m_link'] + fl['m_tip']) if fl else 0.0)),
              belly=float(min(h[:, 2].min() for h in sp['hulls'])))
    return sp


# ---------- the tail ----------
# A tail on a turntable at the rear (2026-10-26): yaw about Z, then one pitched link with a rubber foot. Pitch 0 points
# straight back, +90 up, 180 forward over the top; yaw turns that plane, so the link's zero points along
# (-cos yaw, -sin yaw, 0). Two position servos with a torque limit; their masses scale with it (guesses).
LIMB_PITCH, LIMB_YAW = (-120.0, 180.0), (-180.0, 180.0)   # degrees
ELBOW = (-160.0, 160.0)                                    # degrees: a two-link tail's elbow (2026-10-30)
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


def rear_surface(hulls, z):
    """the rearmost x where the centre line at height z enters the body (any hull), or None when it misses them all"""
    xs = []
    for P in hulls:
        h = ConvexHull(P); n, off = h.equations[:, :3], h.equations[:, 3]
        lim = -(n[:, 2] * z + off); back, front = n[:, 0] < -1e-9, n[:, 0] > 1e-9
        if np.all(lim[~back & ~front] >= 0) and back.any():
            x0 = (lim[back] / n[back, 0]).max()
            if not front.any() or x0 <= (lim[front] / n[front, 0]).min():
                xs.append(x0)
    return min(xs) if xs else None


def limb_points(lm, yaw, pitch, k=8):
    """points along the link and round the foot at a pose (degrees), body frame, mm. A two-link tail with its elbow
    straight (as stowed, and as every reflex but the walk holds it) reaches L + L2. Until 2026-10-31 this drew L alone,
    so the overnight wide run under-read two-link designs' turn circles, step starts and tail clearance"""
    y, p = np.radians(yaw), np.radians(pitch); h = np.array([-np.cos(y), -np.sin(y), 0.0])
    d = np.cos(p) * h + np.array([0.0, 0.0, np.sin(p)]); B = np.asarray(lm['base'], float); L = lm['L'] + lm.get('L2', 0.0)
    line = B + np.outer(np.linspace(0, 1, k), d * L)
    tip = B + d * L; foot = tip + lm.get('foot_r', FOOT_R) * np.vstack([np.eye(3), -np.eye(3)])
    return np.vstack([line, foot])


def add_limb(sp, L, tq, th_push, th_stow, mz=1.0, base=None, L2=0.0, tq2=None):
    """the spec with a tail: link L mm, servo stall tq N m, the step push's pitch and the stowed pitch (degrees), and
    the mount's height as a fraction (limb_mount); base (mm, body frame) pins the mount instead (the shape study).
    L2 > 0 (2026-10-30): a second link of L2 mm on an elbow servo of tq2 N m (tq's when None) at the first's end; the
    elbow straight, the tail is a single link L + L2 long"""
    lm = dict(base=(limb_mount(sp['hulls'], mz) if base is None else np.asarray(base, float)).tolist(), L=float(L), tq=float(tq), th_push=float(th_push), th_stow=float(th_stow), mz=float(mz),
              m_base=2 * (45.0 + 8.0 * tq), m_link=0.3 * L, m_foot=15.0)
    if L2 > 0:
        t2 = float(tq if tq2 is None else tq2); lm.update(L2=float(L2), tq2=t2, m_link2=0.3 * L2, m_elbow=45.0 + 8.0 * t2)
    out = dict(sp, limb=lm, notes=list(sp['notes']) + [f'tail {L:.0f} mm, {tq:.1f} N m'])
    return dims(out)


# ---------- front flippers ----------
# Zach, 2026-10-28: "flippers have got to be a future knob i bet they would help a lot with the steps". A flipper is a
# link with a rubber tip on a pitch servo at the front, like the tail: angle 0 points straight ahead, +90 up, 180 back
# over the top, below 0 down. Two placements: a pair on the front axle's line, outboard of the tyres and the body (the
# tracked robots' layout, chassis-v2/guard_flippers.py), or one on the centre line, 20 mm ahead of the nose. Each
# servo weighs as the tail's (45 + 8 g per N m, a guess) and rides in the body; the link is 0.3 g a mm, the tip 10 g.
# Like the tail, a flipper meets the floor and the terrain, never the robot.
FLIP_RANGE = (-100.0, 190.0)                               # degrees
FLIP_TIP, FLIP_GAP = 10.0, 6.0                             # mm: the tip's radius; the pair's gap outside the tyres and body


def nose_mount(hulls, fz=0.5):
    """the centre-line flipper's pivot: fz of the way from the belly up to the body's top at its front, 20 mm ahead of
    the outermost surface at that height (limb_mount, mirrored)"""
    body = hulls[0]; lo = float(body[:, 2].min()); hi = float(body[body[:, 0] > body[:, 0].max() - 40][:, 2].max())
    zb = lo + fz * (hi - lo); xs = []
    for P in hulls:
        h = ConvexHull(P); n, off = h.equations[:, :3], h.equations[:, 3]
        lim = -(n[:, 2] * zb + off)                                # inside: n_x x <= lim along the line (x, 0, zb)
        front, back = n[:, 0] > 1e-9, n[:, 0] < -1e-9
        if np.all(lim[~front & ~back] >= 0) and front.any():
            x1 = (lim[front] / n[front, 0]).min()                  # the line leaves the hull here
            if not back.any() or x1 >= (lim[back] / n[back, 0]).max():
                xs.append(x1)
    return np.array([(max(xs) if xs else body[:, 0].max()) + 20.0, 0.0, zb])


def flip_points(fl, ang, k=8):
    """points along each flipper and round its tip at an angle (degrees), body frame, mm"""
    a = np.radians(ang); d = np.array([np.cos(a), 0.0, np.sin(a)]); out = []
    for P in fl['pivots']:
        P = np.asarray(P, float); tip = P + d * fl['L']
        out += [P + np.outer(np.linspace(0, 1, k), d * fl['L']), tip + FLIP_TIP * np.vstack([np.eye(3), -np.eye(3)])]
    return np.vstack(out)


def _sweep_hits(hulls, fl):
    """does a centre-line flipper pass through the body anywhere between its stowed, raised and pressing angles?"""
    a0, a1 = min(fl['stow'], fl['up'], fl['press']), max(fl['stow'], fl['up'], fl['press'])
    eqs = [ConvexHull(P).equations for P in hulls]
    for a in np.arange(a0, a1 + 1e-9, 2.0):
        Q = flip_points(dict(fl, L=fl['L']), a, k=16)
        for E in eqs:
            if np.any((Q @ E[:, :3].T + E[:, 3]).max(1) < LINK_R):
                return True
    return False


def add_flippers(sp, L, tq, stow, up, press, nose=False, fz=0.5, with_tail=False):
    """the spec with front flippers: link L mm, each servo's stall tq N m, the stowed angle, the angle it lifts to
    over a step, and the angle it presses down to (degrees). nose: one on the centre line ahead of the nose (fz its
    height, as nose_mount), else a pair on the front axle; with_tail: they lift as the tail pushes (gauges.Reflex). None
    when a centre-line flipper's path crosses the body."""
    if nose:
        pivots = [nose_mount(sp['hulls'], fz)]
    else:
        xf = max(x for x, _ in sp['wheels'])
        yo = max(max(abs(y) for _, y in sp['wheels']) + sp['TW'] / 2, max(float(np.abs(h[:, 1]).max()) for h in sp['hulls'])) + FLIP_GAP + LINK_R
        pivots = [np.array([xf, yo, sp['R']]), np.array([xf, -yo, sp['R']])]
    fl = dict(pivots=[np.round(p, 3).tolist() for p in pivots], L=float(L), tq=float(tq), stow=float(stow), up=float(up),
              press=float(press), nose=bool(nose), fz=float(fz), with_tail=bool(with_tail), m_servo=45.0 + 8.0 * tq, m_link=0.3 * L, m_tip=10.0)
    if nose and _sweep_hits(sp['hulls'], fl):
        return None
    M, c, I = sp['M'], sp['com'], sp['I']
    for p in pivots:                                                     # each servo, fixed in the body at its pivot
        g = fl['m_servo']; M2 = M + g; c2 = (M * c + g * p) / M2; d0, d1 = c - c2, p - c2
        I = I + M * (d0 @ d0 * np.eye(3) - np.outer(d0, d0)) + g * (d1 @ d1 * np.eye(3) - np.outer(d1, d1)); M, c = M2, c2
    out = dict(sp, M=M, com=c, I=I, flip=fl, notes=list(sp['notes']) + [f"{'a flipper at the nose' if nose else 'flippers on the front axle'} {L:.0f} mm, {tq:.1f} N m"])
    return dims(out)


WELL_GAP = 5.0                                    # mm: a wheel well's clearance round its tyre*


def with_wells(P, sp, gap=WELL_GAP, tol=1.0):
    """the body's hull P with a well round each tyre that cuts it (gap mm clear all round), as (vertices, triangles):
    the part as it would be printed (cadquery, exact booleans). The sims keep the convex hull: what a well removes
    lies inside its tyre's reach, where the tyre meets the ground first."""
    import cadquery as cq
    P = np.asarray(P, float); h = ConvexHull(P); F = h.simplices.copy()
    for i, (f, e) in enumerate(zip(F, h.equations)):
        a, b, c = P[f]
        if np.cross(b - a, c - a) @ e[:3] < 0:
            F[i] = f[[0, 2, 1]]
    vec = [cq.Vector(*p) for p in P]
    body = cq.Solid.makeSolid(cq.Shell.makeShell([cq.Face.makeFromWires(cq.Wire.makePolygon([vec[i] for i in f], close=True)) for f in F]))
    for x, y in sp['wheels']:
        w = sp['TW'] + 2 * gap
        body = body.cut(cq.Solid.makeCylinder(sp['R'] + gap, w, cq.Vector(x, y - w / 2, sp['R']), cq.Vector(0, 1, 0)))
    vs, ts = body.tessellate(tol, 0.4)
    return np.array([(v.x, v.y, v.z) for v in vs]), np.array(ts, int)


EDGE_R = 3.0                                      # mm: the step's top edge is this round (a capsule)


def xml(sp, mu=1.0, step=None, dt=None, edge='round', extra=None):
    """MJCF: the robot (free) with its hulls and its wheels on armatured hinges (wheels3's rotor model, chassis3's
    layout); `step` (mm) a step up at X 0. mu scales every friction.

    edge 'round' (2026-10-26): the step's top edge is a capsule of EDGE_R, its face EDGE_R behind it. A sharp box edge
    met by a cylinder gets the face's normal, (1, 0, 0): the tyre hits a wall and spins in place, so the Trainer
    stalled at a 10 mm step 1 time in 5. chassis3's steps have that sharp edge. 'sharp' keeps it, for the control.

    extra (2026-10-27): a function (frictions, the tail's contact attribute) -> more worldbody XML, after the robot (so
    the robot's free joint stays first in qpos, as Sim.place assumes): a gauge's own terrain or objects (crest.py's
    ridge, push.py's box). None builds the model exactly as before."""
    dt = dt or CONTACT['dt']; M, G, I = sp['M'], sp['com'], sp['I'] * 1e-9
    full = ' '.join('%.8g' % v for v in (I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2]))
    mo = sp['motor']; Ie = sp['I_w'] + mo['N'] * mo['Ir']; arm = (mo['N'] ** 2 - mo['N']) * mo['Ir']; R = sp['R']
    mk = sp['m_w'] * 1e-3; It = max(mk * (3 * (R * S) ** 2 + (sp['TW'] * S) ** 2) / 12, 0.5 * Ie * 1.001)
    f = {k: '%.4f 0.005 0.0005' % (v * mu) for k, v in FRICTION.items()}
    f['foot'] = f['tyre']                                                 # the tail's rubber, which the tread grip doesn't change
    f['tyre'] = '%.4f 0.005 0.0005' % (FRICTION['tyre'] * mu * sp.get('tyre_mu', 1.0))   # tread grip (2026-10-27), 1: as before
    sc = ' conaffinity="3"' if sp.get('solid_tail') else ''              # strict (2026-10-28): body and tyres stop the tail (contype 2)
    ts = ''                                                               # a tyre's own spring (sp['tyre_k'], N/mm; snap.py, 2026-10-28):
    if sp.get('tyre_k'):                                                  # its priority makes its solref govern its contacts
        k = sp["tyre_k"] * 1e3; b = 2 * sp.get("tyre_zeta", 0.3) * np.sqrt(k * sp["mass"] * 1e-3 / len(sp["wheels"]))
        ts = f' solref="{-k:.1f} {-b:.2f}"'
    wb = ''.join(f'<body name="w{i}" pos="{x * S:.4f} {y * S:.4f} {R * S:.4f}"><joint name="j{i}" type="hinge" axis="0 1 0" armature="{arm:.6g}"/>'
                 f'<inertial pos="0 0 0" mass="{mk:.4f}" diaginertia="{It:.6g} {Ie:.6g} {It:.6g}"/>'
                 f'<geom type="cylinder" size="{R * S:.4f} {sp["TW"] / 2 * S:.4f}" euler="90 0 0" friction="{f["tyre"]}" priority="1"{sc}{ts}/></body>'
                 for i, (x, y) in enumerate(sp['wheels']))
    lm, fl = sp.get('limb'), sp.get('flip'); ca = ' conaffinity="3"' if lm or fl else ''   # the floor also meets the tail and flippers (contype 2)
    floor = f'<geom type="plane" size="8 8 0.1" friction="{f["floor"]}"{ca}/>'
    if step:
        r = EDGE_R * S if edge == 'round' else 0.0; h = step * S
        floor += f'<geom type="box" size="2 2 {h / 2:.5f}" pos="{2 + r:.5f} 0 {h / 2:.5f}" friction="{f["floor"]}"{ca}/>'
        if r:
            floor += f'<geom type="capsule" fromto="{r:.5f} -2 {h - r:.5f} {r:.5f} 2 {h - r:.5f}" size="{r:.5f}" friction="{f["floor"]}"{ca}/>'
    tail, act = '', ''
    if lm:                                                                # the tail meets the floor only, never the robot
        B = np.asarray(lm['base']) * S; L = lm['L'] * S; mb = lm['m_base'] * 1e-3; foot = lm.get('foot_r', FOOT_R) * S
        cap = lambda a: (f'<geom type="capsule" fromto="0 0 0 {-a:.5f} 0 0" size="{LINK_R * S:.4f}" contype="2" conaffinity="0" friction="{f["foot"]}"/>'
                         f'<geom type="sphere" pos="{-a:.5f} 0 0" size="{foot:.4f}" contype="2" conaffinity="0" friction="{f["foot"]}"/>')
        def rod(m_rod, m_end, a):                                       # a link's mass, centre and pitch inertia: rod plus a point at its end
            m = (m_rod + m_end) * 1e-3; c = -(m_rod * a / 2 + m_end * a) * 1e-3 / m
            return m, c, max((m_rod * a * a / 3 + m_end * a * a) * 1e-3 - m * c * c, 1e-6)
        if lm.get('L2'):                                                # two links (2026-10-30): the elbow's servo at the first link's end
            L2 = lm['L2'] * S; ml, cx, Iy = rod(lm['m_link'], lm['m_elbow'], L); m2, c2, I2 = rod(lm['m_link2'], lm['m_foot'], L2)
            end = (f'<geom type="capsule" fromto="0 0 0 {-L:.5f} 0 0" size="{LINK_R * S:.4f}" contype="2" conaffinity="0" friction="{f["foot"]}"/>'
                   f'<body name="lelbow" pos="{-L:.5f} 0 0"><joint name="le" type="hinge" axis="0 1 0" range="{ELBOW[0]} {ELBOW[1]}" damping="{LIMB_DAMP}" armature="{LIMB_ARM}"/>'
                   f'<inertial pos="{c2:.5f} 0 0" mass="{m2:.4f}" diaginertia="2e-6 {I2:.6g} {I2:.6g}"/>{cap(L2)}</body>')
        else:
            ml, cx, Iy = rod(lm['m_link'], lm['m_foot'], L); end = cap(L)
        tail = (f'<body name="lyaw" pos="{B[0]:.5f} {B[1]:.5f} {B[2]:.5f}"><joint name="ly" type="hinge" axis="0 0 1" range="{LIMB_YAW[0]} {LIMB_YAW[1]}" '
                f'damping="{LIMB_DAMP}" armature="{LIMB_ARM}"/><inertial pos="0 0 0" mass="{mb:.4f}" diaginertia="2e-5 2e-5 2e-5"/>'
                f'<body name="llink"><joint name="lp" type="hinge" axis="0 1 0" range="{LIMB_PITCH[0]} {LIMB_PITCH[1]}" damping="{LIMB_DAMP}" armature="{LIMB_ARM}"/>'
                f'<inertial pos="{cx:.5f} 0 0" mass="{ml:.4f}" diaginertia="2e-6 {Iy:.6g} {Iy:.6g}"/>{end}</body></body>')
        act = (f'<position name="ay" joint="ly" kp="{LIMB_KP}" forcelimited="true" forcerange="{-lm["tq"]:.3f} {lm["tq"]:.3f}"/>'
               f'<position name="ap" joint="lp" kp="{LIMB_KP}" forcelimited="true" forcerange="{-lm["tq"]:.3f} {lm["tq"]:.3f}"/>')
        if lm.get('L2'):
            act += f'<position name="ae" joint="le" kp="{LIMB_KP}" forcelimited="true" forcerange="{-lm["tq2"]:.3f} {lm["tq2"]:.3f}"/>'
    if fl:                                                                # each flipper: pitch about -Y, so a positive angle raises the tip
        L = fl['L'] * S; ml = (fl['m_link'] + fl['m_tip']) * 1e-3
        cx = (fl['m_link'] * L / 2 + fl['m_tip'] * L) * 1e-3 / ml; Iy = max((fl['m_link'] * L * L / 3 + fl['m_tip'] * L * L) * 1e-3 - ml * cx * cx, 1e-6)
        for i, P in enumerate(fl['pivots']):
            P = np.asarray(P) * S
            tail += (f'<body name="f{i}" pos="{P[0]:.5f} {P[1]:.5f} {P[2]:.5f}"><joint name="fj{i}" type="hinge" axis="0 -1 0" range="{FLIP_RANGE[0]} {FLIP_RANGE[1]}" '
                     f'damping="{LIMB_DAMP}" armature="{LIMB_ARM}"/><inertial pos="{cx:.5f} 0 0" mass="{ml:.4f}" diaginertia="2e-6 {Iy:.6g} {Iy:.6g}"/>'
                     f'<geom type="capsule" fromto="0 0 0 {L:.5f} 0 0" size="{LINK_R * S:.4f}" contype="2" conaffinity="0" friction="{f["foot"]}"/>'
                     f'<geom type="sphere" pos="{L:.5f} 0 0" size="{FLIP_TIP * S:.4f}" contype="2" conaffinity="0" friction="{f["foot"]}"/></body>')
            act += f'<position name="af{i}" joint="fj{i}" kp="{LIMB_KP}" forcelimited="true" forcerange="{-fl["tq"]:.3f} {fl["tq"]:.3f}"/>'
    act = f'<actuator>{act}</actuator>' if act else ''
    meshes = ''.join(f'<mesh name="h{i}" vertex="{" ".join("%.5f" % v for v in (P * S).ravel())}"/>' for i, P in enumerate(sp['hulls']))
    geoms = ''.join(f'<geom type="mesh" mesh="h{i}" friction="{f["body"]}"{sc}/>' for i in range(len(sp['hulls'])))
    geoms += ''.join(f'<geom name="strut{i}" type="capsule" fromto="{" ".join("%.5f" % (v * S) for v in (*p0, *p1))}" size="{r * S:.5f}" friction="{f["body"]}"{sc}/>'
                     for i, (p0, p1, r) in enumerate(sp.get('struts', ())))   # printed supports (2026-10-28, body_tree); none before
    return f"""<mujoco><option timestep="{dt}"/><default><geom solref="{CONTACT['tc']} {CONTACT['dr']}"/></default>
      <asset>{meshes}</asset><worldbody>{floor}
      <body name="robot" pos="0 0 0.5"><freejoint/>
        <inertial pos="{G[0] * S:.5f} {G[1] * S:.5f} {G[2] * S:.5f}" mass="{M * 1e-3:.4f}" fullinertia="{full}"/>
        {geoms}{wb}{tail}</body>{extra(f, ca) if extra else ''}</worldbody>{act}</mujoco>"""


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
