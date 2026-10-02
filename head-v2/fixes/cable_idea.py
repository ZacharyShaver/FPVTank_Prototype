"""The tilt servo cable's own route, as a picture (2026-09-30). Nothing here is cut into a part yet.

Zach's plug doesn't depin, so the lead is cut near the plug, threaded through 4.5 mm holes, and soldered
back in the tank inside a printed joint cover. The route:
  servo (in the ball) -> on the tilt axis through a fixed hollow stub (twists, doesn't bend) -> down
  inside the cradle's -Y wall -> in under the cradle to the drum's bore (beside the ribbon, no tape) ->
  down the drum's core -> its own rolling loop in a lane under the ribbon (the can gets ~4.3 deeper,
  not modelled here) -> out of the can under the ribbon's slot -> joint cover in the tank.

fit_view.py packs what this writes: the cable tube, the stub and the joint cover, and his MG90S as the
tilt servo. The points are hand-placed along material measured on the generator's fork SDF; the
tunnels themselves aren't checked yet.
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import numpy as np

CABLE_R = 1.5                       # the lead drawn round; it is ~3 x 1 flat (Zach: "3mm")
H = 52.0
# tilt servo (his MG90S): case face at Y 18 (shaft side, +Y toward the post), shaft on the tilt axis
TILT_FACE_Y = 18.0

LANE_Z = -21.9                      # middle of the new lane (drawn in today's can; it deepens ~4.3)
LANE_WALL = 21.0                    # the lane's own outer wall, past the ribbon's (18): a 9 mm gap, not 6,
                                    # so the moving U is ~3.7 mm radius instead of ~2 (Zach OK'd, 2026-10-02)
LANE_H = 3.5
RI, RO = 12.85, LANE_WALL - 0.75    # lead's inner and outer wraps (half its 1 mm + 0.25 clear)

ROUTE = [                           # (X, Y, Z), head/pan frame
    (0.0, -4.4, 62.0),              # leaves the servo's far end (exact spot on the case: his to say)
    (0.0, -10.0, 58.0), (0.0, -16.0, 53.0), (0.0, -19.0, 52.0),
    (0.0, -24.0, 52.0),             # through the stub, on the axis: the twist is here
    (-0.6, -27.6, 50.4), (-2.2, -29.3, 46.4), (-4.2, -29.2, 41.8), (-5.0, -28.9, 37.5),   # out of the stub's window, into the wall
    (-5.0, -28.6, 33.0), (-5.0, -26.8, 28.0), (-5.0, -24.6, 23.0),   # down the -Y wall
    (-5.0, -21.5, 16.0), (-3.5, -18.0, 13.2),
    (-2.0, -12.0, 13.0), (-2.0, -8.6, 12.3), (-2.0, -6.6, 9.6),       # in under the cradle to the bore
    (-2.0, -6.0, 6.0),                                                            # the bore, then the drum core
]


def lane():
    """Control points for the lane, smoothed with the rest of the route, so no hard corners. In the drum's
    core the lead spirals out and down (CW seen from above) and leaves the drum's face at a slant, already
    heading along it. It wraps the drum CW from 210 to 30 deg, makes the U (bulging on, CW), comes back CCW
    on the wall to 250 deg, and curves out through its own exit near the ribbon's slot (270)."""
    z = LANE_Z; c, r = (RI + RO) / 2, (RO - RI) / 2
    pol = lambda rr, deg, zz=z: (rr * np.cos(np.radians(deg)), rr * np.sin(np.radians(deg)), zz)
    pts = [pol(6.8, 252, -3.0), pol(8.0, 243, -10.0), pol(9.8, 232, -15.5), pol(11.3, 221, -19.4), pol(12.3, 213, -21.3)]
    pts += [pol(RI, d) for d in list(range(203, 40, -12)) + [36, 33]]
    er = np.array([np.cos(np.radians(30)), np.sin(np.radians(30)), 0]); ecw = np.array([er[1], -er[0], 0])
    pts += [tuple(c * er - r * np.cos(t) * er + r * np.sin(t) * ecw + [0, 0, z]) for t in np.pi * np.linspace(0, 1, 15)]
    pts += [pol(RO, d) for d in [33, 36] + list(range(42, 251, 12))]
    pts += [pol(RO + 1.0, 259), pol(RO + 2.6, 265), (0.0, -25.2, z - 0.4),       # curving out through the wall
            (0.0, -29.5, z - 2.0), (0.0, -33.5, z - 5.0), (0.0, -38.0, -32.0)]  # down into the joint cover
    return pts


def smooth(P, per=10):
    """Centripetal Catmull-Rom through the points (no overshoot where they bunch up)."""
    P = np.asarray(P, float); Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]]); out = []
    for i in range(1, len(Q) - 2):
        p = Q[i - 1:i + 3]; t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p, axis=0), axis=1) ** 0.5)]
        for u in np.linspace(t[1], t[2], per, endpoint=False):
            A = [((t[j + 1] - u) * p[j] + (u - t[j]) * p[j + 1]) / (t[j + 1] - t[j]) for j in range(3)]
            B = [((t[j + 2] - u) * A[j] + (u - t[j]) * A[j + 1]) / (t[j + 2] - t[j]) for j in range(2)]
            out.append(((t[2] - u) * B[0] + (u - t[1]) * B[1]) / (t[2] - t[1]))
    out.append(P[-1]); return np.array(out)


def tube(C, r, k=12):
    """Rings along the polyline (parallel-transported frame), capped."""
    T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1)[:, None]
    n = np.cross(T[0], [0, 0, 1.0]); n = n if np.linalg.norm(n) > 1e-3 else np.cross(T[0], [1.0, 0, 0]); n /= np.linalg.norm(n)
    V, F = [], []
    for i, (c, t) in enumerate(zip(C, T)):
        n = n - t * (n @ t); n /= np.linalg.norm(n); b = np.cross(t, n)
        for j in range(k):
            a = 2 * np.pi * j / k; V.append(c + r * (np.cos(a) * n + np.sin(a) * b))
    m = len(C)
    for i in range(m - 1):
        for j in range(k):
            a, b2, c2, d = i * k + j, i * k + (j + 1) % k, (i + 1) * k + (j + 1) % k, (i + 1) * k + j
            F += [(a, b2, c2), (a, c2, d)]
    V += [C[0], C[-1]]
    for j in range(k):
        F += [(m * k, (j + 1) % k, j), (m * k + 1, (m - 1) * k + j, (m - 1) * k + (j + 1) % k)]
    return np.array(V), np.array(F)


def cyl_y(x, z, r, y0, y1, k=40, r_in=None):
    """A Y-axis cylinder (or tube, with r_in) as a mesh."""
    a = np.linspace(0, 2 * np.pi, k, endpoint=False)
    ring = lambda rr, y: [(x + rr * np.cos(t), y, z + rr * np.sin(t)) for t in a]
    V = ring(r, y0) + ring(r, y1) + ring(r_in, y0) + ring(r_in, y1)
    F = []
    for j in range(k):
        j2 = (j + 1) % k
        F += [(j, j2, k + j2), (j, k + j2, k + j)]                                # outside
        F += [(2 * k + j, 3 * k + j2, 2 * k + j2), (2 * k + j, 3 * k + j, 3 * k + j2)]   # bore
        F += [(j, 2 * k + j2, j2), (j, 2 * k + j, 2 * k + j2)]                    # end y0
        F += [(k + j, k + j2, 3 * k + j2), (k + j, 3 * k + j2, 3 * k + j)]        # end y1
    return np.array(V), np.array(F)


def ring_z(r0, r1, z0, z1, k=72):
    """A Z-axis annulus as a mesh."""
    V, F = cyl_y(0.0, 0.0, r1, z0, z1, k=k, r_in=r0)
    return V[:, [0, 2, 1]], F[:, ::-1]                       # swap Y and Z (and flip the faces back outward)


def box(p0, p1):
    x0, y0, z0 = p0; x1, y1, z1 = p1
    V = np.array([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)])
    F = np.array([(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)])
    return V, F


def write_obj(path, V, F):
    with open(path, 'w') as f:
        f.writelines('v %.4f %.4f %.4f\n' % tuple(v) for v in V)
        f.writelines('f %d %d %d\n' % tuple(np.asarray(t) + 1) for t in F)


def tilt_servo(mesh_tris):
    """His MG90S (model frame: x along the case, shaft at x -5.4; y up from the far end, case face 22.4;
    z across 0..12.2) turned so the shaft is on the tilt axis pointing +Y, the case running up from it.
    (x, y, z) -> (6.1 - z, y - 22.4 + TILT_FACE_Y, H + x + 5.4): a proper rotation."""
    T = mesh_tris
    return np.stack([6.1 - T[..., 2], T[..., 1] - 22.4 + TILT_FACE_Y, H + T[..., 0] + 5.4], -1)


# Round 1 is built (2026-10-02): the servo's own lead and plug stay coiled in the ball, and three jumper wires
# run from the plug through the real stub and cradle hole (tree_parts_b.WIRE_PTS), then on as drawn above.
PLUG_C = np.array([-9.0, -15.0, 44.0])          # the servo's plug, in the free space behind the camera board
WIRES_R = 1.3                                   # three ~1.3 jumper wires, drawn as one round bundle


def servo_lead():
    """The servo's own lead, loosely coiled behind the camera board, ending at its plug (drawing only)."""
    t = np.linspace(0, 3 * 2 * np.pi, 160)
    coil = np.stack([-12.0 + 4.5 * np.cos(t), -14.0 + np.linspace(-3.5, 3.5, len(t)), 56.0 + 4.5 * np.sin(t)], 1)
    run = smooth([ROUTE[0], (-4.0, -6.0, 62.0), tuple(coil[0])], 10)
    end = smooth([tuple(coil[-1]), (-12.0, -16.0, 49.0), tuple(PLUG_C + [0, 0, 7.0])], 10)
    return np.vstack([run, coil[1:], end[1:]])


def lane_built(PC):
    """The wires' path through round 2 as built (pan_coil_b): down the drum's core hole, the inner wrap
    CW on the drum, the U, the outer wrap CCW on the lane's wall, out through the exit boss. With
    PC.WIRE_L (74 mm) in the lane, the U's angle at pan 0 follows from the lengths."""
    z = PC.LANE_ZC; ri, ro = PC.DRUM_R + WIRES_R + 0.1, PC.LANE_R - WIRES_R - 0.1
    pol = lambda r, d: (r * np.cos(np.radians(d)), r * np.sin(np.radians(d)), z)
    th_mouth, th_exit = 147.0, 360.0 + PC.WIRE_EXIT_DEG - 8.0
    thU = np.degrees((np.radians(th_mouth) * ri + np.radians(th_exit) * ro - PC.WIRE_L) / (ri + ro))
    pts = list(PC.DRUM_WIRE_PTS[:-2])
    pts += [pol(ri, d) for d in np.arange(th_mouth - 9, thU + 3, -10.0)]
    c, r = (ri + ro) / 2, (ro - ri) / 2
    er = np.array([np.cos(np.radians(thU)), np.sin(np.radians(thU)), 0.0]); ecw = np.array([er[1], -er[0], 0.0])
    pts += [tuple(c * er - r * np.cos(t) * er + r * np.sin(t) * ecw + [0, 0, z]) for t in np.pi * np.linspace(0, 1, 13)]
    pts += [pol(ro, d) for d in np.arange(thU + 6, th_exit - 4, 10.0)]
    pts += list(PC.BASE_WIRE_PTS[1:])
    out = np.array(PC.BASE_WIRE_PTS[-1]); d = out / np.hypot(out[0], out[1])
    pts += [tuple(out + d * 6 + [0, 0, -2.0]), tuple(out + d * 10 + [0, 0, -9.0]), tuple(out + d * 11 + [0, 0, -16.0])]
    return pts


def build(out):
    """Write the overlay meshes into out/; returns {key: (path, label)}."""
    import tree_parts_b as B, pan_coil_b as PC
    files = {}
    V, F = tube(servo_lead(), 1.0); p = os.path.join(out, '_servo_lead.obj'); write_obj(p, V, F)
    files['servo_lead'] = (p, 'Servo lead, coiled in the ball (stays there)')
    V, F = box(PLUG_C - [4.0, 2.0, 7.0], PLUG_C + [4.0, 2.0, 7.0]); p = os.path.join(out, '_servo_plug.obj'); write_obj(p, V, F)
    files['servo_plug'] = (p, 'Servo plug, with the jumper wires plugged in')
    route = [tuple(PLUG_C - [0, 0, 7.0]), (-5.0, -16.0, 44.0), (-1.5, -15.0, 50.0)] + list(B.WIRE_PTS)[:-1] + \
            [(-1.5, -4.6, 7.5), (-4.0, -2.0, 3.0)]
    C = smooth(route + lane_built(PC), 10)
    V, F = tube(C, WIRES_R); p = os.path.join(out, '_cable.obj'); write_obj(p, V, F)
    files['cable'] = (p, 'Jumper wires: through the stub, the cradle, the drum and their own lane')
    return files
