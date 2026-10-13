"""Guard arm (option E, brainstorm 2026-10-05): an arm at the tail built to replace the roll cage. Zach: "what if the
tail acted as the cage ... through software", "it can prevent a roll from even happening too", "make a purpose built
arm for this as a new option". On the rugged body with v2 legs, the hoops, brow bar and skirts removed (rugged.CAGE).

    python chassis-v2/guard_arm.py     # ~3 min -> out/guard_arm.html, guard_*.png, guard_arm.json

Its jobs, and the check for each:
- Guard: it drives around stowed as an arch from the tail over the head, its jaws gripping a peg on the left claw, the
  upper arm on a hard stop. A landing load goes peg -> claw -> hull and stop -> turntable, not through servo gears.
  Checked: the first part to touch over 4000 fall directions (the head never), and where it comes to rest.
- Prevent: it plants its TPU-capped jaws on the ground beside the track or behind the tail (a brace), and it is a
  counterweight. Checked: tip angles with the brace at the force the shoulder can hold.
- Recover: from every place the bare robot can come to rest, it reaches the ground and pushes the robot over the edge
  towards upright. Checked: a search over the arm's joints for a push the servos can make (`righting`).
- Work: camera and gripper at the tip, as before.
Servos and the yaw drive are not bought: sizes and torques are datasheet guesses (*).
"""
import os, sys, json, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault('SCORPION_LEGS', 'v2')
import rugged as R
R.CAGE = False
import tail_arms as TA
from tail_arms import cq, cq_tris, cyl_tris, YC, OUT, C
wp = lambda: cq.Workplane('XY')
U = TA.U

# ---------------------------------------------------------------- the arm
AXW = R.AX + R.BODY_DX                      # -97: yaw axis, world X
TT = R.PZ + 12.0                            # 116: turntable top (6 bearing + 6 disc on the pedestal)
S = np.array([0.0, TT + 30.0])              # shoulder (r, z): 146
L1, L2, LEV = 140.0, 175.0, 30.0            # upper arm, forearm, parallelogram crank (= the forearm's rear lever)
TOOL = 62.0                                 # wrist to jaw tip
YAW = (-90.0, 180.0)                        # worm-driven turntable: right side, front, left side, behind
SERVO = {  # joint: (part, stall kg.cm at ~7 V*, mass g*)
    'shoulder': ('DS3235 35 kg servo* behind a slip clutch', 35.0, 65.0),
    'elbow': ('DS3218 20 kg servo*, at the shoulder (parallelogram)', 21.0, 60.0),
    'yaw': ('N20 worm gearmotor* + AS5600 angle sensor (self-locking)', 20.0, 15.0),
    'wrist': ('MG90S*', 2.0, 13.4), 'grip': ('MG90S*', 2.0, 13.4)}
MASS = {'base': 60.0, 'upper': 45.0, 'elbow_hub': 25.0, 'forearm': 30.0, 'tool': 60.0, 'payload': 100.0, 'rod': 8.0}
OLIVE, OLIVE_D, STEEL, DARK, ACC, JAW, TPU = TA.OLIVE, TA.OLIVE_D, TA.STEEL, TA.DARK, TA.ACC, TA.JAW, R.TPU

def ok(q):
    yaw, a1, a2, g = q
    return YAW[0] <= yaw <= YAW[1] and -10 <= a1 <= 175 and -165 <= a2 - a1 <= -15 and -120 <= g - a2 <= 120

def fk(q):
    yaw, a1, a2, g = q; E = S + L1 * U(a1); W = E + L2 * U(a2); return dict(E=E, W=W, tip=W + TOOL * U(g))

def world(p, yaw):
    p = np.atleast_2d(p); c, s = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
    return np.c_[AXW + p[:, 0] * c, YC + p[:, 0] * s, p[:, 1]]

def place(sh, yaw): return sh.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), yaw).translate(cq.Vector(AXW, YC, 0))

def base_parts(yaw):
    P = [(wp().circle(32).circle(22).extrude(6).translate((0, 0, R.PZ)).val(), STEEL, 'Lazy-susan bearing*'),
         (wp().circle(34).circle(29).extrude(5).translate((0, 0, R.PZ + 6.5)).val(), (0.75, 0.6, 0.3), 'Worm wheel ring (on the turntable)'),
         (wp().circle(31).extrude(6).edges('>Z').fillet(2).translate((0, 0, R.PZ + 6)).val(), OLIVE_D, 'Turntable')]
    f = wp().box(60, 92, 38).edges('|Z').fillet(14).edges('>Z').fillet(10).translate((0, 0, TT + 19))
    f = f.cut(wp().box(54, 86, 38).edges('|Z').fillet(11).translate((0, 0, TT + 16))).cut(wp().box(70, 46, 50).translate((-4, -4, TT + 38)))   # slot, deep: the upper arm can lie flat
    P.append((f.val(), OLIVE, 'Fairing over the shoulder and elbow servos'))
    P.append((wp().box(14, 16, 12).translate((-38, 0, R.PZ + 6)).val(), DARK, 'Yaw drive: N20 worm gearmotor* (fixed on the pedestal)'))
    P.append((cq.Workplane('XZ').circle(13).extrude(4, both=True).translate((S[0], 22, S[1])).val(), ACC, 'Slip clutch (Belleville washers + friction disc)'))
    return [(place(sh, yaw if l not in ('Lazy-susan bearing*', 'Yaw drive: N20 worm gearmotor* (fixed on the pedestal)') else 0.0), rgb, l) for sh, rgb, l in P]

def parts(q, base=True):
    yaw, a1, a2, g = q; k = fk(q); E, W = k['E'], k['W']
    lv = LEV * U(a2 + 180); C1, C2 = S + lv, E + lv
    P = []
    for dy in (-11.0, 11.0): P.append((TA.bar(S, E, 3.5, 26, 12, dy), (0.36, 0.38, 0.41), 'Upper arm (twin plates)'))
    P += [(TA.pin(S, 26, 8), STEEL, 'Shoulder'), (TA.pin(E, 26, 8), STEEL, 'Elbow pin'),
          (TA.bar(S, C1, 7, 9, 4.4, -17), STEEL, 'Elbow crank'), (TA.bar(C1, C2, 5, 5, 2.4, -17), DARK, 'Pushrod'),
          (TA.bar(E, C2, 9, 12, 5.9, -17), OLIVE_D, 'Forearm rear lever')]
    P.append((wp().box(30, 26, 26).edges().fillet(6).rotate((0, 0, 0), (0, 1, 0), -a2).translate((E[0], 0, E[1])).val(), OLIVE_D, 'Elbow hub'))
    P.append((TA.tube(E + 12 * U(a2), W - 4 * U(a2), 7.0, 6.99), DARK, 'Forearm: 14 mm carbon tube*'))
    t, tip = TA.tool(W, g)
    lab = {'tool': 'Wrist servo + gripper housing', 'cam': 'Arm camera', 'lens': 'Arm camera lens', 'jaw': 'Gripper jaw'}
    u = U(g); nn = U(g + 90)
    for sh, rgb, l in t:
        if l in ('cam', 'lens'):                                        # the camera rides on the tool's inner face: in guard it faces the robot
            cb = W + 14 * u + 14 * nn; sh = sh.mirror(mirrorPlane=cq.Vector(nn[0], 0, nn[1]), basePointVector=cq.Vector(W[0] + 12 * u[0], 0, W[1] + 12 * u[1]))
        P.append((sh, rgb, lab.get(l, l)))
    bc = W + 12 * u + 13.5 * nn                                         # TPU bumper on the tool's outer face
    P.append((wp().box(26, 26, 4).edges('|Y').fillet(1.5).rotate((0, 0, 0), (0, 1, 0), -g).translate((bc[0], 0, bc[1])).val(), TPU, 'TPU bumper on the tool'))
    for dy in (-8, 8):                                                  # TPU caps on the jaws: the brace foot
        c = W + 59 * u; P.append((wp().box(9, 7, 11).edges().fillet(2.5).rotate((0, 0, 0), (0, 1, 0), -g).translate((c[0], dy, c[1])).val(), TPU, 'TPU jaw cap: the brace foot'))
    return (base_parts(yaw) if base else []) + [(place(sh, yaw), rgb, l) for sh, rgb, l in P]

def mass_items(q, payload=True):
    yaw, a1, a2, g = q; k = fk(q); E, W = k['E'], k['W']
    it = [('arm base + shoulder & elbow servos', MASS['base'] + SERVO['shoulder'][2] + SERVO['elbow'][2] + 40, world((0, TT + 15), yaw)[0]),
          ('upper arm', MASS['upper'], world((S + E) / 2, yaw)[0]), ('elbow hub', MASS['elbow_hub'], world(E, yaw)[0]),
          ('forearm', MASS['forearm'] + MASS['rod'], world((E + W) / 2, yaw)[0]), ('tool', MASS['tool'], world(W + 18 * U(g), yaw)[0])]
    if payload: it.append(('payload', MASS['payload'], world(W + 50 * U(g), yaw)[0]))
    return it

def chain(q, n=12):
    """points along the arm's centre line, world"""
    k = fk(q); pts = []
    for a, b in ((S, k['E']), (k['E'], k['W']), (k['W'], k['tip'])):
        pts += [a + (b - a) * f for f in np.linspace(0, 1, n)]
    return world(np.array(pts), q[0])

def ik(yaw, r, z, g):
    """jaw tip at (r, z) in the arm's plane, tool pointing g: elbow up first"""
    Wt = np.array([r, z]) - TOOL * U(g)
    for sg in (1, -1):
        s = TA.two_link(S, L1, L2, Wt, sg)
        if s and ok((yaw, s[0], s[1], g)): return (yaw, s[0], s[1], g)

# ---------------------------------------------------------------- the robot without the cage, and the rest peg
def robot():
    M, it, O = R.assemble()
    pal = palm(M)
    peg = cq.Workplane('XY').circle(4).extrude(PEG_H).translate((pal[0], pal[1], pal[2])).val()
    M['rest_peg'] = dict(t=np.asarray(cq_tris(peg), float).reshape(-1, 3, 3), label='Guard rest: a peg on the left claw',
                         grp='hull', rgb=TPU, note='The jaws hold it while driving: the arch rests on it, not on the servos.')
    M['_guard_yaw'] = None
    del M['_guard_yaw']
    for i, (sh, rgb, lab) in enumerate(base_parts(guard_q(M)[0])):
        M['armbase_%d' % i] = dict(t=np.asarray(cq_tris(sh), float).reshape(-1, 3, 3), label=lab, grp='armbase', rgb=rgb, note='The arm\'s base: always on the robot.')
    imu = cq.Workplane('XY').box(25, 20, 4).translate((-5 + R.BODY_DX, YC, R.TUN_Z + R.WALL + 2)).val()   # IMU on the tunnel roof, near the centre of mass
    M['imu'] = dict(t=np.asarray(cq_tris(imu), float).reshape(-1, 3, 3), label='IMU (BNO085*), near the centre of mass', grp='elec', rgb=(0.6, 0.2, 0.6), note='The tip monitor reads it.')
    it = R.mass_items(M)
    return M, it

PEG_H = 26.0
def palm(M):
    """top centre of the left claw's palm (world), where the guard peg stands"""
    c = M['claw0']['t'].reshape(-1, 3); x = c[:, 0].max() - 18           # forward on the palm: the arm camera clears the panning head
    s = c[np.abs(c[:, 0] - x) < 9]; return np.array([x, (s[:, 1].min() + s[:, 1].max()) / 2, s[:, 2].max()])

def guard_q(M):
    p = palm(M); tip = p + [0, 0, PEG_H * 0.35]
    yaw = np.degrees(np.arctan2(tip[1] - YC, tip[0] - AXW)); r = np.hypot(tip[0] - AXW, tip[1] - YC)
    return ik(yaw, r, tip[2], -90.0)

# ---------------------------------------------------------------- analyses
def hull_of(M, keys=None):
    from scipy.spatial import ConvexHull
    keys = keys or [k for k in M if not M[k].get('ghost')]
    P = np.unique(np.round(np.vstack([M[k]['t'].reshape(-1, 3) for k in keys]), 2), axis=0)
    return P, ConvexHull(P)

def righting(M, it, rest):
    """from a rest face, can the arm push the robot over the face's edge towards upright? Searches the joints for a
    push the servos can hold; returns the best (load as a fraction of stall, joints, tip, edge) or None"""
    P, H = hull_of(M, [k for k in M if not M[k].get('ghost') and M[k]['grp'] != 'arm'])
    eq = H.equations; n = np.array(rest['normal']); n = n / np.linalg.norm(n)
    face = [i for i, e in enumerate(eq) if np.dot(e[:3], n) > 0.9995]
    d = max(eq[i, 3] for i in face) * -1                                # plane: n.p = d
    c, m = R.cog(it); W = m / 1000 * 9.81
    # the face's boundary edges, and the face across each
    from collections import defaultdict
    edge_faces = defaultdict(list)
    for i, s in enumerate(H.simplices):
        for a, b in ((s[0], s[1]), (s[1], s[2]), (s[2], s[0])): edge_faces[(min(a, b), max(a, b))].append(i)
    fs = set(face); best_edge = None
    for (a, b), fl in edge_faces.items():
        inn = [f for f in fl if f in fs]; out = [f for f in fl if f not in fs]
        if len(inn) == 1 and len(out) == 1:
            n2 = eq[out[0], :3]; score = -n2[2]                         # closest to upright (normal straight down)
            if best_edge is None or score > best_edge[0]: best_edge = (score, P[a], P[b], n2)
    if best_edge is None: return None
    _, A, B, n2 = best_edge; e = (B - A) / np.linalg.norm(B - A)
    tau_g = np.dot(np.cross(c - A, W * n), e)                           # gravity's moment about the edge (holds it on the face)
    best = None
    for yaw in np.arange(YAW[0], YAW[1] + 1, 10):
        cy, sy = np.cos(np.radians(yaw)), np.sin(np.radians(yaw))
        nr, nz = n[0] * cy + n[1] * sy, n[2]; g = np.degrees(np.arctan2(nz, nr))     # tool pointing at the ground
        for a1 in np.arange(-10, 176, 5):
            for rel in np.arange(-165, -14, 5):
                q = (yaw, a1, a1 + rel, g)
                if not ok(q): continue
                tip = world(fk(q)['tip'], yaw)[0]
                if abs(np.dot(n, tip) - d) > 3: continue                 # the jaw caps on the ground
                ch = chain(q)
                if np.any(ch @ n > d + 1.5): continue                     # nothing of the arm through the ground
                inside = (H.equations[:, :3] @ ch[6:].T + H.equations[:, 3:4] < -2).all(0)
                if inside.any(): continue                                 # nor through the robot
                arm_ = np.dot(np.cross(tip - A, -n), e)                   # the ground's push on the jaws, per newton
                if arm_ * tau_g >= 0 or abs(arm_) < 1e-6: continue        # must turn it the other way
                F = abs(tau_g / arm_) * 1.2                               # 20 % over balance
                Fv = -F * n; tau = {}
                for j, idx in (('yaw', 0), ('shoulder', 1), ('elbow', 2)):
                    dq = np.zeros(4); dq[idx] = 0.5
                    q2 = tuple(np.array(q) + dq)
                    if idx == 1: q2 = (q2[0], q2[1], q[2], q[3])          # shoulder alone: the forearm keeps its angle (parallelogram)
                    t2 = world(fk(q2)['tip'], q2[0])[0]
                    tau[j] = abs(np.dot(Fv, (t2 - tip) / np.radians(0.5))) / 98.1   # N.mm -> kg.cm
                load = max(tau[j] / SERVO[j][1] for j in tau)
                if best is None or load < best[0]:
                    best = (load, q, tip, F, tau)
    if best is None: return dict(edge=[A.tolist(), B.tolist()], ok=False)
    load, q, tip, F, tau = best
    return dict(ok=bool(load <= 0.8), load=float(load), q=[float(v) for v in q], tip=tip.tolist(), F=float(F),
                tau={k: float(v) for k, v in tau.items()}, edge=[A.tolist(), B.tolist()], next=n2.tolist())

def brace(M, it, side=True, past=150.0):
    """tip angle with the jaw caps planted past the track (side) or behind it (back), at the force the servos can hold"""
    tr = np.vstack([M['track_L']['t'].reshape(-1, 3), M['track_R']['t'].reshape(-1, 3)]); g0 = R.ground(M)
    if side:
        yaw = 90.0; y_edge = tr[:, 1].max(); r = y_edge + past - YC; q = ik(yaw, r, g0 + 1, -90.0)
    else:
        flat = tr[tr[:, 2] < g0 + 0.6]; x_edge = flat[:, 0].min()             # the flat contact's back end: it tips over that
        r = AXW - (tr[:, 0].min() - past + 100); yaw = 180.0; q = ik(yaw, r, g0 + 1, -90.0)
    if q is None: return None
    its = it + mass_items(q, payload=False); c, m = R.cog(its); W = m / 1000 * 9.81; h = (c[2] - g0) / 1000
    tip = world(fk(q)['tip'], yaw)[0]
    # the force the shoulder and elbow can hold at the planted tip (60 % of stall), pushing straight up
    Fmax = 1e9
    for j, idx in (('shoulder', 1), ('elbow', 2)):
        dq = np.zeros(4); dq[idx] = 0.5; q2 = tuple(np.array(q) + dq)
        if idx == 1: q2 = (q2[0], q2[1], q[2], q[3])
        dz = (world(fk(q2)['tip'], yaw)[0][2] - tip[2]) / np.radians(0.5) / 1000        # m per rad
        if abs(dz) > 1e-6: Fmax = min(Fmax, 0.6 * SERVO[j][1] * 9.81 / 100 / abs(dz))
    if side: b = (y_edge - c[1]) / 1000; D = (tip[1] - y_edge) / 1000
    else: b = (c[0] - x_edge) / 1000; D = (x_edge - tip[0]) / 1000
    phi = np.degrees(np.arctan2(b, h)); Rr = np.hypot(h, b)
    a = phi + np.degrees(np.arcsin(min(1.0, Fmax * D / (W * Rr)))) if Fmax * D < W * Rr else 90.0
    return dict(q=[float(v) for v in q], free=float(phi), braced=float(a), F=float(Fmax), past=past)

def holding(samples=None):
    """worst held torque at the shoulder and elbow, 100 g in the jaws, over the reachable poses"""
    worst = {'shoulder': 0.0, 'elbow': 0.0}
    for a1 in np.arange(-10, 176, 5):
        for rel in np.arange(-165, -14, 5):
            for gd in (-90, 0, -45):
                q = (0, a1, a1 + rel, a1 + rel + gd)
                if not ok(q): continue
                its = mass_items(q)[1:]; k = fk(q)
                ts = sum(m / 1000 * (p[0] - AXW) / 10 for _, m, p in its)
                te = sum(m / 1000 * (p[0] - (AXW + k['E'][0])) / 10 for nm, m, p in its if nm not in ('upper arm', 'elbow hub'))
                worst['shoulder'] = max(worst['shoulder'], abs(ts)); worst['elbow'] = max(worst['elbow'], abs(te))
    return worst

# ---------------------------------------------------------------- run
POSES = ['guard', 'brace_side', 'brace_back', 'pick', 'periscope']
POSE_NAME = {'guard': 'Guard (driving)', 'brace_side': 'Brace beside', 'brace_back': 'Brace behind', 'pick': 'Pick up beside', 'periscope': 'Periscope'}
def poses(M):
    g0 = R.ground(M); tr = np.vstack([M['track_L']['t'].reshape(-1, 3)]); y_edge = tr[:, 1].max()
    Q = {'guard': guard_q(M), 'brace_side': brace(M, R.mass_items(M), True)['q'], 'brace_back': brace(M, R.mass_items(M), False)['q'],
         'pick': ik(90.0, y_edge + 60 - YC, g0 + 1, -90.0), 'periscope': (0.0, 98.0, 83.0, 0.0)}
    return {k: tuple(v) for k, v in Q.items() if v is not None}

def with_arm(M, q, key='arm'):
    M2 = dict(M)
    for i, (sh, rgb, lab) in enumerate(parts(q, base=False)):
        M2['%s_%02d' % (key, i)] = dict(t=np.asarray(cq_tris(sh), float).reshape(-1, 3, 3), label=lab, grp='arm', rgb=rgb, note='')
    return M2

def arm_tris(q):
    return np.vstack([np.asarray(cq_tris(sh), float).reshape(-1, 3, 3) for sh, _, _ in parts(q, base=False)])

def base_tris(yaw):
    return np.vstack([np.asarray(cq_tris(sh), float).reshape(-1, 3, 3) for sh, _, _ in base_parts(yaw)])

def checks(M, Q):
    g = lambda *ks: np.vstack([M[k]['t'] for k in ks])
    static = [k for k in M if not M[k].get('ghost') and k != 'rest_peg' and M[k]['grp'] != 'armbase']
    robot_ = g(*static)
    HX = R.Hm.HX + R.BODY_DX
    sweep = [C.T(g('cradle', 'ball') - [HX, YC, 0], C.Rz(a), (HX, YC, 0)) for a in range(0, 360, 30)]
    G = arm_tris(Q['guard'])
    rows = [('Guard: arm vs the robot and its own base', G, np.vstack([robot_, base_tris(Q['guard'][0])]), 'the jaws straddle the rest peg'),
            ('Guard 12 mm lower (control)', G - [0, 0, 12.0], g('claw0', 'rest_peg'), 'must read > 0: the jaws meet the claw (9 over it)'),
            ('Head, 12 pan angles, vs the guarding arm', sweep, G, 'the arm arches over and beside the ball'),
            ('Head 25 mm higher (control)', [t + [0, 0, 25.0] for t in sweep], G, 'must read > 0: the forearm is that close over it')]
    for k in ('brace_side', 'brace_back', 'pick', 'periscope'):
        if k in Q: rows.append(('%s: arm vs the robot and its own base' % POSE_NAME[k], arm_tris(Q[k]), np.vstack([robot_, base_tris(Q[k][0])]), ''))
    under = g('carapace', 'pca', 'ubec', 'arm_ubec', 'ina219', 'wifi', 'alarm', 'antenna', 'intake')
    rows += [('Arm base, turned to every pose, vs the carapace and the parts under it', [base_tris(Q[k][0]) for k in Q], under, 'on the pedestal'),
             ('Arm base 4 mm lower (control)', base_tris(0.0) - [0, 0, 4.0], M['carapace']['t'], 'must read > 0: it sits on the pedestal')]
    out = []
    for what, a, b, why in rows:
        v = sum(C.overlap_mm3(t, b) for t in a) if isinstance(a, list) else C.overlap_mm3(a, b)
        out.append(dict(what=what, mm3=float(v), why=why)); print('%-50s %8.0f mm3' % (what, v))
    return out

def settle(M, n, keys=None):
    """the rotation (3x3) and lift that lay the robot on the face with outward normal n, on the ground plane"""
    n = np.asarray(n, float) / np.linalg.norm(n); t = np.array([0, 0, -1.0])
    v = np.cross(n, t); s_ = np.linalg.norm(v); c = np.dot(n, t)
    if s_ < 1e-9: Rm = np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    else:
        vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]]); Rm = np.eye(3) + vx + vx @ vx * ((1 - c) / s_ ** 2)
    keys = keys or [k for k in M if not M[k].get('ghost')]
    P = np.vstack([M[k]['t'].reshape(-1, 3) for k in keys]) @ Rm.T
    return Rm, float(R.ground(M) - P[:, 2].min())

def renders(M, Q, D):
    base = [(v['t'], v['rgb'], 0.3) for k, v in M.items() if not v.get('ghost') and v['grp'] != 'armbase' and (v['grp'] != 'elec' or k in ('antenna', 'estop', 'light0', 'light1'))]
    arm = lambda q: [(np.asarray(cq_tris(sh), float).reshape(-1, 3, 3), rgb, 0.45) for sh, rgb, _ in parts(q, base=True)]
    shots = [('guard_drive.png', base + arm(Q['guard']), (820, -760, 460), (10, YC, 100), 'Driving: the arm arches over the head onto the claw'),
             ('guard_brace.png', base + arm(Q['brace_side']), (420, 1050, 380), (-60, 90, 40), 'Bracing: jaw caps planted beside the track'),
             ('guard_back.png', base + arm(Q['brace_back']), (-760, -820, 420), (-150, YC, 60), 'Bracing behind: a wheelie bar for steps')]
    up = next((r for r in D['righting'] if r.get('ok') and r['rest'].startswith('upside down')), None)
    if up:
        Mq = dict(M); Rm, dz = settle(M, up['normal'])
        Pr = [((t.reshape(-1, 3) @ Rm.T + [0, 0, dz]).reshape(-1, 3, 3), rgb, sp) for t, rgb, sp in base + arm(tuple(up['q']))]
        shots.append(('guard_right.png', Pr, (700, -900, 420), (0, YC, 60), 'Righting from upside down: the arm pushes it over'))
    for fn, P, cam, foc, lab in shots:
        IR.render(P, cam, foc, os.path.join(OUT, fn), size=(1300, 860))
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(os.path.join(OUT, s[0])) for s in shots]; w, h = ims[0].size
    sh = Image.new('RGB', (w * 2, h * 2), 'white'); d = ImageDraw.Draw(sh)
    try: f = ImageFont.truetype('arialbd.ttf', 34)
    except Exception: f = ImageFont.load_default()
    for i, (im, s_) in enumerate(zip(ims, shots)):
        x, y = (i % 2) * w, (i // 2) * h; sh.paste(im, (x, y)); d.text((x + 24, y + 18), s_[4], fill=(30, 33, 30), font=f)
    sh.resize((w, h), Image.LANCZOS).save(os.path.join(OUT, 'guard_sheet.png')); print('wrote guard_sheet.png')

def page(M, Q, D):
    import base64
    tohex = lambda rgb: int(rgb[0] * 255) << 16 | int(rgb[1] * 255) << 8 | int(rgb[2] * 255)
    def pack(t, faces):
        Tk = C.decimate(t, faces); V, F = C.quant(Tk); return {'v': C.b64(V), 'f': C.b64(F), 'i32': F.dtype == np.uint32}
    D['m'] = {}
    for k, v in M.items():
        if v.get('ghost') or v['grp'] == 'armbase': continue           # the base turns with the arm: it goes with each situation
        D['m'][k] = dict(pack(v['t'], C.faces_for(k)), c=tohex(v['rgb']), grp=v['grp'], label=v['label'], note=v.get('note', ''))
    sit = {}
    for k in POSES:
        if k in Q: sit[k] = dict(q=list(Q[k]), name=POSE_NAME[k], R=np.eye(3).tolist(), dz=0.0)
    for r in D['righting']:
        if not r.get('ok'): continue
        Rm, dz = settle(M, r['normal'])
        sit['right_' + r['rest']] = dict(q=r['q'], name='Righting: ' + r['rest'], R=Rm.tolist(), dz=dz)
    D['sit'] = {}
    for k, s_ in sit.items():
        byc = {}
        for sh, rgb, lab in parts(tuple(s_['q']), base=True): byc.setdefault(tohex(rgb), []).append(np.asarray(cq_tris(sh), float).reshape(-1, 3, 3))
        D['sit'][k] = dict(name=s_['name'], R=s_['R'], dz=s_['dz'], arm=[dict(pack(np.vstack(ts), 5000), c=c) for c, ts in byc.items()])
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v.get('ghost')]); D['centre'] = ((A.min(0) + A.max(0)) / 2).round(1).tolist()
    D['yc'] = YC; D['ground'] = R.ground(M)
    D['sheet'] = base64.b64encode(TA._small(os.path.join(OUT, 'guard_sheet.png'), 1300)).decode()
    html = open(os.path.join(HERE, 'guard_arm_template.html'), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D, default=float) + ';')
    p = os.path.join(OUT, 'guard_arm.html'); open(p, 'w', encoding='utf-8').write(html); print('page %.1f MB' % (os.path.getsize(p) / 1e6))

IR = TA.IR
SHOP = [
    ('DS3235 35 kg·cm servo (shoulder)', 1, 'Behind a slip clutch: a hit while the arm is out slips instead of stripping it.'),
    ('DS3218 20 kg·cm servo (elbow, at the shoulder)', 1, 'Drives the forearm through the parallelogram.'),
    ('MG90S micro servo (wrist, gripper)', 2, 'Or your MG90Ds.'),
    ('N20 worm gearmotor, ~30 rpm, 6 V*', 1, 'Yaw: self-locking, so a brace load can’t spin the arm.'),
    ('AS5600 magnetic angle sensor + diametric magnet', 1, 'The turntable’s angle, since the N20 has no feedback.'),
    ('BNO085 IMU breakout (I²C)', 1, 'The tip monitor. Address 0x4A: clear of the PCA9685.'),
    ('Thin lazy-susan bearing, ~64 mm', 1, 'Under the turntable.'),
    ('14 mm carbon tube, 200 mm', 1, 'Forearm.'),
    ('M5 Belleville washers + PTFE washer', 4, 'The shoulder’s slip clutch.'),
    ('Small USB or CSI camera board (~25 x 24)', 1, 'The arm’s camera.'),
]

if __name__ == '__main__':
    t0 = time.time()
    M, it = robot(); Q = poses(M); print('poses', {k: np.round(v, 1).tolist() for k, v in Q.items()})
    arm_m = sum(m for _, m, _ in mass_items(Q['guard'], payload=False))
    MG = with_arm(M, Q['guard']); itG = it + mass_items(Q['guard'], payload=False)
    _cat = R.category; R.category = lambda k, v: 'the guard arm' if v['grp'] in ('arm', 'armbase') else _cat(k, v)
    R.FRAGILE = R.FRAGILE + tuple(k for k in MG if MG[k]['grp'] == 'arm' and MG[k]['label'].startswith('Arm camera'))
    cage = json.load(open(os.path.join(OUT, 'rugged_v2.json')))
    D = dict(poses={k: list(v) for k, v in Q.items()}, arm_mass=arm_m, shop=SHOP, servos=SERVO)
    D['contact'] = R.first_contact(MG); print('first contact', D['contact'])
    D['rests_guard'] = R.rest_states(MG, itG); print('rests, arm in guard', [(r['name'], round(r['tilt'], 1)) for r in D['rests_guard']])
    D['rests_bare'] = R.rest_states(M, itG); print('rests, arm free', [(r['name'], round(r['tilt'], 1)) for r in D['rests_bare']])
    D['righting'] = []
    for r in [r for r in D['rests_bare'] if not r['name'].startswith('upright')]:
        rr = righting(M, itG, r); rr['rest'] = r['name']; rr['normal'] = r['normal']; rr['tilt'] = r['tilt']; D['righting'].append(rr)
        print('righting from', r['name'], {k: (round(v, 2) if isinstance(v, float) else v) for k, v in rr.items() if k in ('ok', 'load', 'F', 'tau')})
    D['brace_side'] = brace(M, it, True); D['brace_back'] = brace(M, it, False)
    print('brace', {k: round(v, 1) for k, v in D['brace_side'].items() if isinstance(v, float)}, {k: round(v, 1) for k, v in D['brace_back'].items() if isinstance(v, float)})
    D['holding'] = holding(); print('holding', D['holding'])
    D['climb_guard'] = R.climb(MG, itG); D['climb_cage'] = cage['climb']; D['mass'] = R.cog(itG)[1]; D['mass_cage'] = cage['mass']
    A = np.vstack([v['t'].reshape(-1, 3) for v in MG.values() if not v.get('ghost')]); g0 = R.ground(M)
    D['size'] = dict(W=float(np.ptp(A[:, 1])), H=float(A[:, 2].max() - g0), L=float(np.ptp(A[:, 0])), W0=cage['size']['W'], H0=cage['size']['H'], L0=cage['size']['L'])
    D['contact_cage'] = cage['contact']; D['rests_cage'] = cage['rests']
    print('climb guard', {k: round(v, 1) for k, v in D['climb_guard'].items() if isinstance(v, float)}, 'size', D['size'], 'mass', round(D['mass']), 'arm', round(arm_m))
    D['checks'] = checks(M, Q)
    json.dump({k: v for k, v in D.items()}, open(os.path.join(OUT, 'guard_arm.json'), 'w'), indent=1, default=float)
    if '--no-render' not in sys.argv: renders(M, Q, D)
    if os.path.exists(os.path.join(HERE, 'guard_arm_template.html')): page(M, Q, D)
    print('done %.0f s' % (time.time() - t0))
