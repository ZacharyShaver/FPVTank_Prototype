"""One-piece bodies, grown where they're weak (2026-10-29, a prototype). Zach, on body_tree's sheet: "it doesnt look right
like it is a realistic thing id be able to print the shape seems weak in key areas", "the bodies seem weakest if there
dropped onto a single wheel at an angle", "it needs to feel more like one shape and less like a shape with 3d printed
trees on it. Maybe trees were the wrong path".

body_tree built parts (a hull, rods, tubes) and blended them after. Here the robot is one signed distance field from the
start, and its strength comes from the shape's own sections, the way a print gets it (walls far apart), not from solid
rods:
  1. Required, from body_tree's anchors (the same wheel layouts): the body (body.shell's profile, its edges rounded by
     a knob), a boss round each motor, the parts bay (a cavity, 3 mm of body round it at least).
  2. Random, by the knobs: an arm from each boss into the body's side, a deep oval rather than a rod; a pod along each
     side joining its bosses; a beam across an end pair that clears the body; blobs between the body and the wheels;
     a low ripple (off since 2026-10-30). One smooth union joins them, its radius K a knob (15-60 mm: webs, not body_tree's 8 mm fillets).
     Mirror symmetric.
  3. Cut sharp: each wheel's room, each motor's bore (closed 3 mm past its inner end, open to the tyre), the cavity,
     everything under the belly or the bosses.
  The motor (2026-10-29, Zach: "the motor i have has screws and a face plate"): the Trainer's corner module. The pod
     ends in a lip the gearbox face screws to, the wheel is a dish over the pod (or, for a wheel too small to wrap it,
     outboard on a shaft extension), and a landing goes into the shape through the gearbox face.
  4. Grown: fem.py lands the robot on one wheel (each wheel on the left, the right mirrors it): 1.5x* its 300 mm drop
     into one tyre's 30 N/mm spring (snap.py's), up, 45 degrees in, out, forward and back, and flat sideways. Where the
     printed wall's stress passes the allowed (snap.py's 25 MPa over 2), the field swells, up to GROW* a round, carried
     REACH* out to the surface, then it's cut and landed again (Mattheck's CAO, 1990: shape optimization by biological
     growth); and cut where nothing within REACH carries SKO_LOW (SKO, Mattheck's soft kill, 1992). Each round does
     both, until it holds and its mass settles. The motor's seat is read apart: its peak is the mount's.
  5. Under a weight cap (2026-10-30): over CAP_G* the cut deepens, up to everything not carrying the allowed, and the
     trim knob's limit lifts. The falls (G1's, drops.py) are the verdict, dropped on the drawn shape and the finished
     one, not grown against (that made warts and broke more often); the body meets the floor on soft TPU bumpers.

    python gauges/unibody.py section [seed] [k]  -> out/unibody/section.png: a cut through a wheel's pod, the motor in it

    python gauges/unibody.py check [seed]     the drawn shape's tests, with their controls: the core meshes flat, the mesh
                                                 has no folds (exits 1 on a failure)
    python gauges/unibody.py sheet [seed]     -> out/unibody/sheet.png: Sobol designs, grown, one shape each
    python gauges/unibody.py compare          -> out/unibody/compare.png: body_tree's sheet designs (seed 23823) against
                                                 a unibody on the same wheels, the same landing on both
"""
import os, sys, math, pickle
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
os.environ.setdefault('PYTORCH_CUDA_ALLOC_CONF', 'expandable_segments:True')   # workers share one 12 GB card (2026-10-29: three ran it out)
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config, stamp
import robots as RB, body as B, body_tree as T, fem as FE

OUT = os.path.join(config.GAUGES_OUT, 'unibody')
VOX, FEM_H = 2.0, 4.0                       # mm: the field's grid, the stress solve's
WHEEL_GAP, BAY_WALL = 5.0, 6.0              # mm round each tyre; the least body round the parts bay (a printed sandwich: wall, infill, wall)*
SIGMA_ULT, SF = 25.0, 2.0                   # as snap.py: PLA across its layers*, the safety factor*
ALLOW = SIGMA_ULT / SF
LAND, DROP_M, TYRE_K = 1.5, 0.3, 30.0       # the landing: LAND* times a 300 mm drop into one tyre's spring (N/mm)*
GROW, ROUNDS, REACH = 5.0, 12, 12.0         # mm a round at most*, rounds at most, mm the growth reaches* (grow_map)
GROW_BLUR, SHAPE_BLUR = 10.0, 3.0           # mm: each round's growth blurred (4 until 2026-10-30), and the grown shape before its
                                            # cuts (none until then). Zach, on the grown sheet: "its effective but ugly. that a kind of
                                            # balooning is going to make this annoying to print. smooth it"
GROW_FROM = 0.9                             # growth starts at 0.9x the allowed (2026-10-30: from 1.0x, with 6 rounds, every
                                            # sheet design ended 14-26 MPa, the arm roots still falling 0.3-0.6 a round)
CAP_GIVE = 1.1                              # the cap gives 10 % while the landings are over
SKO_LOW, SHRINK, SKO_REACH = 0.5 * ALLOW, 6.0, 6.0   # SKO: where nothing within SKO_REACH mm carries half the allowed*, the shape
                                            # shrinks up to SHRINK mm a round* (first tried 4 MPa within 12 mm: 7 % off in 3 rounds)
SEAT = 14.0                                 # mm: body_tree's collar round its motor, read apart (the motor levers in a short collar)*
MOTOR_R = B.MOTOR['half'][0]
# The drive (2026-10-29, Zach: "the motor i have has screws and a face plate"): the Trainer's corner module
# (chassis-v2/wheels.py). A pod round the 37 mm gearmotor ends in a wall, the lip, that the gearbox face screws to (6 M3
# on a 31 circle*); the wheel is a dish whose rim wraps back over the pod, its hub on the shaft just past the lip. A
# wheel too small to wrap the pod (rim under POD_R + 2 + WHEEL_GAP) sits outboard of it instead, its hub on a shaft
# extension (flagged: a long lever on the gearbox). The numbers are the 37D class's datasheet*, not his motor's.
MOT = dict(gb_d=37.0, gb_l=22.0, m_d=34.5, m_l=33.0, enc_d=30.5, enc_l=11.0, shaft_d=6.0, shaft_l=15.5, holes=6, pcd=31.0)
MOT_L = MOT['gb_l'] + MOT['m_l'] + MOT['enc_l']             # 66: the face to the encoder's end
FACE_OUT = MOT['shaft_l'] + 1.55                            # the gearbox face in from the wheel's outer face (the Trainer's)
POD_R, POD_IR, LIP, SHAFT_HOLE = T.TUBE_R, 19.0, 5.0, 6.5   # mm: the pod (24.5: 6 mm wall*), its bore (the Trainer's 38), the lip* and its shaft hole
RIM_IN = 11.5                                               # the dish's rim this far inside the tyre's radius (the Trainer's)
MOUNT = 8.0                                                 # mm round the gearbox face's seat, read apart (where the load goes in)*
# TPU bumpers (2026-10-29: the falls' worst hits are on the body's top edges, 3.4-3.8 kN on a hard body; the same falls
# on a 30 N/mm bumper read 17 MPa against 25, drops.py bumpers): a knob, the body meeting the floor on a spring in the
# falls; their mass a TPU skin BUMPER_T* thick over BUMPER_SHARE* of the shape's surface. Not drawn: where they sit.
# 2026-10-30: always on (stiff ones barely helped), so the knob is their stiffness alone, soft.
BUMPER_T, BUMPER_SHARE, TPU = 3.0, 0.3, 1.21e-3
# The weight cap (2026-10-30): of the sheet's 12 shapes, only the lightest (1.6 kg of PLA, no bumpers) came through its
# falls, 4 of 24 over the allowed; the rest 13-24 (falls_vs_mass.png). Thin evidence (one design, and the bumpered
# shapes' TPU was overcounted), so the cap is a test: the falls' worst hits are the body landing on its edges, and
# those grow with the mass while the edges don't.
CAP_G = 2000.0                                              # g: the printed shape's cap*
LEG_KEYS = ('tree', 'members', 'spread_x', 'spread_z', 'root_x', 'fork_y', 'fork_z', 'bend')
SHAPE = [   # (key, low, high, what it is)
    ('K', 15.0, 60.0, 'the smooth union\'s radius, mm (how far one piece flows into the next)'),
    ('round', 0.0, 30.0, "the body's edges rounded, mm"),
    ('arm_d', 40.0, 120.0, "an arm's depth (up and down), mm"),
    ('arm_t', 24.0, 70.0, "an arm's thickness (along the body), mm"),
    ('rake', -1.0, 1.0, "the arm's root along the side: out toward the wheel's end (-1) to in toward the middle (1), 60 mm"),
    ('pod', 0.0, 1.0, "a pod along each side joining its wheels' bosses (above half)"),
    ('pod_r', 18.0, 45.0, "the pod's radius, mm"),
    ('beam', 0.0, 1.0, 'a beam across each end pair that clears the body (above half)'),
    ('blobs', 0.0, 6.999, 'blobs a side, between the body and the wheels'),
    ('blob_r', 15.0, 60.0, "the blobs' size, mm"),
    ('seed', 0.0, 1.0, "the blobs' and ripple's draw"),
    ('ripple', 0.0, 0.0, "the surface's ripple, mm (0-6 until 2026-10-30; off since, Zach: \"ripple off\": it only ever "
                         "added bumps. Kept at 0 so each seed's Sobol draws keep the same other knobs)"),
    ('ripple_l', 40.0, 160.0, "the ripple's wavelength, mm"),
    ('trim', 0.0, 40.0, "the most SKO may cut back from the drawn shape, mm (0: the drawn shape, grown only; 40: stress-cut, legs "
                        "return); lifted over the weight cap"),
    ('bumper_k', 20.0, 60.0, "the TPU bumpers' stiffness, N/mm (a printed lattice; the body meets the floor on them, as the tyres "
                             "do. 2026-10-29: 20-150, the stiff half barely helped)")]
KNOBS = [k for k in T.KNOBS if k[0] not in LEG_KEYS] + SHAPE
KEYS = [k for k, *_ in KNOBS]


# ---------- distance fields (torch, mm, negative inside) ----------
def _torch():
    import torch
    return torch, ('cuda' if torch.cuda.is_available() else 'cpu')


def smin(a, b, k):
    torch = _torch()[0]; h = torch.clamp(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def ellip(Px, Py, Pz, r):
    """an ellipsoid of semi-axes r at the origin, local coordinates (IQ's bound)"""
    torch = _torch()[0]
    k0 = torch.sqrt((Px / r[0]) ** 2 + (Py / r[1]) ** 2 + (Pz / r[2]) ** 2)
    k1 = torch.sqrt((Px / r[0] ** 2) ** 2 + (Py / r[1] ** 2) ** 2 + (Pz / r[2] ** 2) ** 2).clamp_min(1e-9)
    return k0 * (k0 - 1) / k1


def ecapsule(G, p0, p1, a, b):
    """a capsule from p0 to p1 whose section is an oval: a deep (toward z, or x when the axis is upright), b wide"""
    X, Y, Z = G; p0, p1 = np.asarray(p0, float), np.asarray(p1, float); e = p1 - p0; L = max(np.linalg.norm(e), 1e-6); u = e / L
    v = np.array([0.0, 0.0, 1.0]) - u[2] * u
    if np.linalg.norm(v) < 0.3:
        v = np.array([1.0, 0.0, 0.0]) - u[0] * u
    v /= np.linalg.norm(v); w = np.cross(u, v)
    rx, ry, rz = X - p0[0], Y - p0[1], Z - p0[2]
    t = ((rx * u[0] + ry * u[1] + rz * u[2]) / L).clamp(0, 1)
    qx, qy, qz = rx - t * e[0], ry - t * e[1], rz - t * e[2]
    return ellip(qx * u[0] + qy * u[1] + qz * u[2], qx * v[0] + qy * v[1] + qz * v[2], qx * w[0] + qy * w[1] + qz * w[2], (min(a, b), a, b))


def blob(G, c, r, Rm):
    X, Y, Z = G; rx, ry, rz = X - c[0], Y - c[1], Z - c[2]
    return ellip(*(rx * Rm[0, k] + ry * Rm[1, k] + rz * Rm[2, k] for k in range(3)), r)


def cyl(G, c, r, a0, a1, axis=1):
    """a capped cylinder of radius r round the line through c along axis (0 x, 1 y), from a0 to a1 on it"""
    torch = _torch()[0]; X, Y, Z = G
    if axis == 1:
        dr = torch.sqrt((X - c[0]) ** 2 + (Z - c[2]) ** 2) - r; s = Y
    else:
        dr = torch.sqrt((Y - c[1]) ** 2 + (Z - c[2]) ** 2) - r; s = X
    da = torch.abs(s - 0.5 * (a0 + a1)) - 0.5 * abs(a1 - a0)
    return torch.clamp(torch.maximum(dr, da), max=0.0) + torch.sqrt(dr.clamp_min(0) ** 2 + da.clamp_min(0) ** 2)


def planes_sdf(G, P):
    """a convex hull's plane distance (exact inside, a bound outside)"""
    from scipy.spatial import ConvexHull
    X, Y, Z = G; E = ConvexHull(P).equations; out = None
    for n0, n1, n2, d0 in E:
        d = n0 * X + n1 * Y + n2 * Z + d0; out = d if out is None else _torch()[0].maximum(out, d)
    return out


def redistance(inside, h):
    """the signed distance (mm) of a voxel set, from its Euclidean distance transforms. Its surface lies on voxel faces:
    fine for the stress solve's voxels, not for a shape that's drawn (core_field)"""
    from scipy.ndimage import distance_transform_edt as edt
    return (edt(~inside) - edt(inside)) * h + np.where(inside, 0.5 * h, -0.5 * h)


def tri_dist(P, a, b, c, chunk=8192):
    """unsigned distance from each point P (n, 3, a torch tensor) to the nearest of the triangles (a, b, c) (m, 3 each)"""
    torch, dev = _torch(); T = lambda x: torch.as_tensor(np.asarray(x), dtype=torch.float32, device=dev)[None]
    a, b, c = T(a), T(b), T(c); ba, cb, ac = b - a, c - b, a - c; nor = torch.cross(ba, ac, dim=-1)
    d2 = lambda x: (x * x).sum(-1); dot = lambda x, y: (x * y).sum(-1)
    ea, eb, ec = torch.cross(ba, nor, dim=-1), torch.cross(cb, nor, dim=-1), torch.cross(ac, nor, dim=-1)
    out = []
    for i in range(0, len(P), chunk):
        p = P[i:i + chunk, None]; pa, pb, pc = p - a, p - b, p - c
        edge = torch.sign(dot(ea, pa)) + torch.sign(dot(eb, pb)) + torch.sign(dot(ec, pc)) < 2.0   # past an edge: the edges
        de = torch.minimum(torch.minimum(d2(ba * (dot(ba, pa) / d2(ba)).clamp(0, 1)[..., None] - pa),
                                         d2(cb * (dot(cb, pb) / d2(cb)).clamp(0, 1)[..., None] - pb)),
                           d2(ac * (dot(ac, pc) / d2(ac)).clamp(0, 1)[..., None] - pc))
        out.append(torch.sqrt(torch.where(edge, de, dot(nor, pa) ** 2 / d2(nor)).min(1).values))
    return torch.cat(out)


def core_field(pts, G, rnd=0.0):
    """the exact signed distance of the convex hull of pts, its edges rounded by rnd (0: sharp): inside the hull moved
    in by rnd, its planes' distance (exact inside a convex hull); outside it, the distance to its nearest triangle;
    less rnd. A rounding past what the hull's thickness allows is capped at 0.9 of its inradius from the centroid.
    2026-10-30: replaces redistance() of the hull's voxels (and again for the rounding), which put the body's surface on
    2 mm voxel faces: flat faces came out terraced up to 1.0 mm off, rounded ones up to 3.3 mm (Zach: "a strange
    bumpyness"); growth then built on the steps. The old field is _core_voxel(), check()'s control"""
    from scipy.spatial import ConvexHull, HalfspaceIntersection
    pts = np.asarray(pts, float); h = ConvexHull(pts); E = h.equations.copy(); c0 = pts[h.vertices].mean(0)
    rnd = min(rnd, 0.9 * -(E[:, :3] @ c0 + E[:, 3]).max())
    if rnd > 0:
        E[:, 3] += rnd; V = HalfspaceIntersection(E, c0).intersections; h = ConvexHull(V)
    else:
        V = pts
    tri = V[h.simplices]; A = planes_sdf(G, V[h.vertices]); out = A > 0
    A[out] = tri_dist(_torch()[0].stack([g[out] for g in G], 1), tri[:, 0], tri[:, 1], tri[:, 2])
    return (A - rnd).cpu().numpy(), rnd


def _core_voxel(pts, G, rnd=0.0):
    """SUPERSEDED 2026-10-30 by core_field(): the hull's field from its voxels, as union() made it until then. Kept as
    check()'s negative control: it must read the terraces"""
    F0 = redistance((planes_sdf(G, pts) <= 0).cpu().numpy(), VOX)
    return (redistance(F0 < -rnd, VOX) - rnd) if rnd > 0 else F0


# ---------- the design ----------
def design(q):
    """the field's pieces for the design q (KEYS), from body_tree's anchors: None when the wheels can't be placed"""
    A = T.anchors(q)
    if A is None:
        return None
    C, items, box, _ = B.parts(); R, TW, hy, clr, H = A['R'], A['TW'], A['hy'], A['clr'], A['H']
    (xn, zn), (xt, zt) = A['nose'], A['rear']; mid = 0.5 * (xn + xt)
    core = B.shell(q, A, [])
    parts = RB.hull(np.vstack([Qp + [q['dxp'] if k.startswith('pack') else 0.0, 0.0, A['dz']] for k, Qp in C.items()]))
    rng = np.random.default_rng(int(q['seed'] * 1e6)); K = q['K']
    bosses, arms, pods, beams = [], [], [], []
    left = [(x, y) for x, y in A['axles'] if y > 0]
    dish = R - RIM_IN - WHEEL_GAP >= POD_R + 2.0
    for x, y in left:
        bosses.append(_boss(x, y, R, TW, dish)); y0, y1 = bosses[-1]['y0'], bosses[-1]['y1']
        pb = np.array([x, y0 + 0.3 * (y1 - y0), R])
        xr = float(np.clip(x + q['rake'] * 60.0 * np.sign(mid - x), xt + 25.0, xn - 25.0))
        pr = np.array([xr, max(hy - 0.5 * min(q['arm_d'], q['arm_t']), 0.0), clr + q['root_z'] * H])
        arms.append((pr, pb, q['arm_d'] / 2, q['arm_t'] / 2))
    if q['pod'] > 0.5 and len(left) > 1:
        ends = sorted(left); b0 = next(b for b in bosses if b['x'] == ends[0][0]); b1 = next(b for b in bosses if b['x'] == ends[-1][0])
        pods.append((np.array([b0['x'], b0['y0'] + 0.3 * (b0['y1'] - b0['y0']), R]), np.array([b1['x'], b1['y0'] + 0.3 * (b1['y1'] - b1['y0']), R]),
                     1.3 * q['pod_r'], q['pod_r']))
    if q['beam'] > 0.5:
        for b in bosses:
            if b['x'] - max(R, T.TUBE_R) - 5.0 >= xn or b['x'] + max(R, T.TUBE_R) + 5.0 <= xt:     # a pair clear of the body's end
                beams.append((np.array([b['x'], b['y0'] + 0.3 * (b['y1'] - b['y0']), R]), np.array([b['x'], 0.0, R]), 0.9 * q['pod_r'], 0.9 * q['pod_r']))
    a = np.linspace(0, 2 * np.pi, 12, endpoint=False)                # each motor clear of the parts inside
    for b in bosses:
        Mp = np.vstack([np.c_[b['x'] + MOTOR_R * np.cos(a), np.full(12, yy), R + MOTOR_R * np.sin(a)] for yy in (b['face'] - MOT_L, b['face'])])
        if (RB.hull_dist(parts, Mp) < 2.0).any():
            return None
    z_cut = min(clr, R - T.TUBE_R)
    blobs = []                                                          # inside the hull of the body's left half and the bosses
    from scipy.spatial import Delaunay
    reg = np.vstack([core[core[:, 1] >= 0], *[np.array([[b['x'], b['y1'], b['z']], [b['x'], b['y0'], b['z']]]) for b in bosses]])
    tri = Delaunay(reg); lo, hi = reg.min(0), reg.max(0); n_b = int(q['blobs']); tries = 0
    from scipy.spatial.transform import Rotation
    while len(blobs) < n_b and tries < 400:
        tries += 1; c = lo + rng.random(3) * (hi - lo); r = q['blob_r'] * rng.uniform(0.5, 1.4, 3)
        if tri.find_simplex(c) < 0 or c[2] < z_cut + 0.3 * r.min():
            continue
        if any(math.hypot(c[0] - x, c[2] - R) < R + WHEEL_GAP and abs(c[1] - y) < TW / 2 + WHEEL_GAP for x, y in left):
            continue
        blobs.append((c, r, Rotation.random(random_state=int(rng.integers(1 << 30))).as_matrix()))
    waves = [(rng.normal(size=3), q['ripple_l'] * rng.uniform(0.7, 1.3), rng.uniform(0, 2 * np.pi)) for _ in range(6)]
    return dict(q=q, A=A, core=core, parts=parts, items=items, box=box, bosses=bosses, arms=arms, pods=pods, beams=beams,
                blobs=blobs, waves=waves, K=K, z_cut=z_cut, tail=None)


def _boss(x, y, R, TW, dish):
    """the motor's boss for the wheel at (x, y > 0): the gearbox face where the pod's lip holds it, the boss from past
    the motor's end to the lip"""
    face = y + TW / 2 - FACE_OUT if dish else y - TW / 2 - WHEEL_GAP - LIP
    return dict(x=x, z=R, y0=face - MOT_L - 3.0, y1=face + LIP, y=y, face=face, dish=dish)


# T3 as a one-piece body (2026-10-30, Zach: "start from t3"): the overnight pass's 48 drawn bodies held their landings
# better once grown but were poor robots (upright 0.30, steps 30 mm, turns 916 mm against T3's 1.00 / 150 / 392). T3's
# skin becomes the body's core, hollowed to BAY_WALL round the parts as every unibody is; its wheels, track, ride height,
# gearing and tail as T3 has them; no arms, pods, beams or blobs. Growth then only strengthens it (trim 0: SKO cuts
# nothing back unless it's over the cap). K and bumper_k are guesses*.
T3_UNI = dict(K=25.0, round=0.0, ripple=0.0, trim=0.0, bumper=1.0, bumper_k=40.0)


def design_t3(**over):
    """the design dict (design()'s form) of T3 as a one-piece body; over: T3's knobs changed (knobs.T3's keys) or
    T3_UNI's"""
    import knobs as KN
    return design_knobs(dict(KN.T3, **{k: v for k, v in over.items() if k in KN.T3}), **{k: v for k, v in over.items() if k in T3_UNI})


def design_knobs(kq, packs_dz=False, **over):
    """any searched design (knobs.make's q, strict) as one piece, the way design_t3 makes T3 one: its body's hull the
    core, its wheels, track, ride height, gearing and tail where it has them (2026-10-31, Zach, of the search's winners:
    "link up the wheels and tail so its a cohesive body. I want to know how much that actually effects it"). The
    flippers are left off (their servos sit outside the tyres, where nothing here reaches): add them to the made spec
    with with_flippers. packs_dz: the packs at the design's dzp too (design_t3 left it out; T3's is 0.56 mm)"""
    import knobs as KN
    u = dict(T3_UNI, **{k: v for k, v in over.items() if k in T3_UNI})
    sp = KN.make(dict(kq, flip=0.0), strict=True)
    if sp is None:
        return None
    C, items, box, clr0 = B.parts(); R, TW = sp['R'], sp['TW']; core = np.asarray(sp['hulls'][0], float)
    q = dict(u, dxp=kq['dxp'], gear=kq['gear'], limb=1.0 if sp.get('limb') else 0.0, L=kq['L'], tq=kq['tq'],
             pack_dz=kq['dzp'] if packs_dz else 0.0)
    A = dict(R=R, TW=TW, clr=kq['clr'], dz=kq['clr'] - clr0, axles=[tuple(map(float, w)) for w in sp['wheels']],
             rear=(float(core[:, 0].min()), kq['clr']), nose=(float(core[:, 0].max()), kq['clr']))
    parts = RB.hull(np.vstack([Qp + ([q['dxp'], 0.0, A['dz'] + q['pack_dz']] if k.startswith('pack') else [0.0, 0.0, A['dz']]) for k, Qp in C.items()]))
    dish = R - RIM_IN - WHEEL_GAP >= POD_R + 2.0
    bosses = [_boss(x, y, R, TW, dish) for x, y in A['axles'] if y > 0]
    D = dict(q=q, A=A, core=core, parts=parts, items=items, box=box, bosses=bosses, arms=[], pods=[], beams=[], blobs=[], waves=[],
             K=q['K'], z_cut=min(kq['clr'], R - T.TUBE_R), tail=None, t3=sp)
    if sp.get('limb'):                                                  # the tail, its turntable a boss into the body's back
        lm = sp['limb']; b = np.asarray(lm['base'], float); D['limb'] = lm
        D['tail'] = dict(x0=float(b[0]) - B.TURN_R, x1=float(core[:, 0].min()) + 30.0, z=float(b[2]))
    return D


def with_flippers(sp, kq):
    """a made spec with the design kq's flippers on it, as knobs.make puts them (after the tyres' width), or as it is"""
    import knobs as KN
    if kq.get('flip', 0.0) <= 0.5:
        return sp
    f = dict(KN.FLIP0, **{k: kq[k] for k in KN.FLIP0 if k in kq})
    return RB.add_flippers(sp, f['FL'], f['ftq'], f['f_stow'], f['f_up'], f['f_press'], nose=f['f_nose'] > 0.5, fz=f['fz'], with_tail=f['f_tail'] > 0.5)


def _mirror(p):
    return np.asarray(p, float) * [1, -1, 1]


def grid(D):
    """the field's grid axes round everything the design holds"""
    R, TW = D['A']['R'], D['A']['TW']; pts = [D['core'], D['parts']]
    for b in D['bosses']:
        pts.append(np.array([[b['x'] - T.TUBE_R, b['y1'], b['z'] - T.TUBE_R], [b['x'] + T.TUBE_R, b['y0'], b['z'] + T.TUBE_R]]))
    for p0, p1, a, b in D['arms'] + D['pods'] + D['beams']:
        m = max(a, b); pts.append(np.array([p0 - m, p0 + m, p1 - m, p1 + m]))
    for c, r, _ in D['blobs']:
        pts.append(np.array([c - r.max(), c + r.max()]))
    if D['tail'] is not None:
        tb = D['tail']; pts.append(np.array([[tb['x0'], -B.TURN_R, tb['z'] - B.TURN_R], [tb['x1'], B.TURN_R, tb['z'] + B.TURN_R]]))
    P = np.vstack(pts); P = np.vstack([P, _mirror(P)]); pad = D['K'] / 2 + 10.0
    lo, hi = P.min(0) - pad, P.max(0) + pad; lo[2] = max(lo[2], D['z_cut'] - 4.0)
    ax = [np.arange(lo[i], hi[i] + VOX, VOX) for i in range(3)]
    a = math.ceil(max(-lo[1], hi[1]) / VOX) * VOX; ax[1] = np.arange(-a, a + VOX / 2, VOX)   # y mirror-symmetric, sample for sample
    return ax


def union(D, ax):
    """the smooth union of every piece before the cuts, the body's own field, and what must stay (numpy, mm)"""
    torch, dev = _torch()
    G = torch.meshgrid(*[torch.as_tensor(a, dtype=torch.float32, device=dev) for a in ax], indexing='ij')
    F0, D['round_used'] = core_field(D['core'], G, D['q']['round'] if D['q']['round'] > 0.5 else 0.0)   # exact (2026-10-30)
    F = torch.as_tensor(F0, dtype=torch.float32, device=dev); K = D['K']
    for sg in (1, -1):
        m = (lambda p: p) if sg > 0 else _mirror
        for b in D['bosses']:
            F = smin(F, cyl(G, m([b['x'], 0, b['z']]), T.TUBE_R, sg * b['y0'], sg * b['y1']), K)
        for p0, p1, a, bb in D['arms'] + D['pods'] + D['beams']:
            F = smin(F, ecapsule(G, m(p0), m(p1), a, bb), K)
        for c, r, Rm in D['blobs']:
            F = smin(F, blob(G, m(c), r, Rm if sg > 0 else np.diag([1, -1, 1]) @ Rm), K)
    if D['tail'] is not None:
        tb = D['tail']; F = smin(F, cyl(G, [0, 0, tb['z']], B.TURN_R, tb['x0'], tb['x1'], axis=0), min(K, 20.0))
    X, Y, Z = G; amp = D['q']['ripple']
    if amp > 0.2:
        rip = torch.zeros_like(F)
        for d, lam, ph in D['waves']:
            d = d / np.linalg.norm(d) * 2 * np.pi / lam; rip += torch.sin(d[0] * X + d[1] * torch.abs(Y) + d[2] * Z + ph)
        F = F - amp / math.sqrt(3.0) * torch.clamp(rip, min=0.0)      # bumps only (2026-10-29: a ripple both ways dented the body's
                                                                        # 6 mm skin through to the bay: holes, and up to 34 pieces)
    req = torch.minimum(torch.as_tensor(F0, dtype=torch.float32, device=dev), planes_sdf(G, D['parts']) - BAY_WALL)
    for sg in (1, -1):                                                  # what must stay: the body, each pod whole, the bay walled
        for b in D['bosses']:
            req = torch.minimum(req, cyl(G, [b['x'], 0, b['z']], T.TUBE_R, sg * b['y0'], sg * b['y1']))
    if D['tail'] is not None:
        tb = D['tail']; req = torch.minimum(req, cyl(G, [0, 0, tb['z']], B.TURN_R, tb['x0'], tb['x1'], axis=0))
    F = torch.minimum(F, req)
    return F.cpu().numpy(), F0, req.cpu().numpy()


def cut(D, F, ax, Fcore):
    """the wheels' rooms, the motors' bores, the bay (the body hollow to BAY_WALL, and the parts' room) and the ground,
    cut sharp: the shape's field, and the bay's (negative inside it)"""
    torch, dev = _torch(); R, TW = D['A']['R'], D['A']['TW']
    G = torch.meshgrid(*[torch.as_tensor(a, dtype=torch.float32, device=dev) for a in ax], indexing='ij')
    F = torch.as_tensor(F, device=dev)
    X, Y, Z = G; rooms = boss = None; low = lambda a, b: b if a is None else torch.minimum(a, b)
    for sg in (1, -1):
        for b in D['bosses']:
            y_in, y_out = sg * (b['y'] - TW / 2 - WHEEL_GAP), sg * (b['y'] + TW / 2 + WHEEL_GAP)
            if b['dish']:                                               # the tyre and rim's ring over the pod, then the disc past the lip
                rho = torch.sqrt((X - b['x']) ** 2 + (Z - R) ** 2); yc, hw = 0.5 * (y_in + y_out), 0.5 * abs(y_out - y_in)
                ring = torch.maximum(torch.maximum(rho - (R + WHEEL_GAP), (R - RIM_IN - WHEEL_GAP) - rho), torch.abs(Y - yc) - hw)
                room = torch.minimum(ring, cyl(G, [b['x'], 0, R], R + WHEEL_GAP, sg * (b['face'] + LIP + 2.0), y_out))
            else:
                room = cyl(G, [b['x'], 0, R], R + WHEEL_GAP, y_in, y_out)
            F = torch.maximum(F, -room); rooms = low(rooms, room); boss = low(boss, cyl(G, [b['x'], 0, b['z']], T.TUBE_R, sg * b['y0'], sg * b['y1']))
            F = torch.maximum(F, -cyl(G, [b['x'], 0, R], POD_IR, sg * (b['y0'] - 10.0), sg * b['face']))       # the motor's room, open inboard
            F = torch.maximum(F, -cyl(G, [b['x'], 0, R], SHAFT_HOLE, sg * (b['face'] - 1.0), sg * (b['y1'] + 1.0)))
    bay = torch.minimum(torch.as_tensor(Fcore, dtype=torch.float32, device=dev) + BAY_WALL, planes_sdf(G, D['parts']))
    if rooms is not None:                                               # the bay keeps BAY_WALL off each wheel's room and leaves the
        bay = torch.maximum(torch.maximum(bay, BAY_WALL - rooms), -boss)   # bosses solid (2026-10-30: T3's wheels and motors sit inside
                                                                        # its skin; the bay opened into the wheel wells and ate the bosses)
    F = torch.maximum(F, -bay); F = torch.maximum(F, D['z_cut'] - G[2]); F = F.cpu().numpy()
    from scipy.ndimage import label                                     # one piece: what the cuts left loose is dropped,
    lab, n = label(F < 0)                                               # a loose motor boss refuses the design
    if n > 1:
        main = np.bincount(lab[lab > 0]).argmax(); F[(lab > 0) & (lab != main)] = VOX / 2
        o = np.array([a[0] for a in ax])
        for sg in (1, -1):
            for b in D['bosses']:
                p = np.array([b['x'], sg * 0.5 * (b['y0'] + b['y1']), b['z'] + 0.5 * (MOTOR_R + T.TUBE_R)])
                if lab[tuple(np.clip(np.rint((p - o) / VOX).astype(int), 0, np.array(F.shape) - 1))] not in (0, main):
                    D['loose'] = True
    return F, bay.cpu().numpy()


def motors_of(D):
    """each motor (both sides): its centre, its gearbox face (where the pod's lip holds it) and its wheel's centre"""
    R = D['A']['R']; out = []
    for sg in (1, -1):
        for b in D['bosses']:
            out.append(dict(x=b['x'], z=R, yc=sg * (b['face'] - MOT_L / 2), y=sg * b['y'], face=sg * b['face'], y_out=sg * b['y1'], dish=b['dish']))
    return out


# ---------- mass, the spec ----------
def mass_of(F, ax):
    """the printed shape's mass (g), its centre and inertia, from its 2 mm voxels (walls and infill)"""
    Fr = redistance(F < 0, VOX); solid, _, share = FE.printed(Fr, VOX)
    idx = np.argwhere(solid); m = share[solid] * VOX ** 3 * FE.PLA; P = np.c_[ax[0][idx[:, 0]], ax[1][idx[:, 1]], ax[2][idx[:, 2]]]
    M = float(m.sum()); c = (m[:, None] * P).sum(0) / M; d = P - c
    I = np.eye(3) * (m * (d * d).sum(1)).sum() - (m[:, None] * d).T @ d
    return M, c, I, Fr


def spec(D, F, ax, name='unibody'):
    """the robot spec (robots.spec's form) of the shape: its printed mass, the parts, motors and wheels; hulls are the
    pieces (the body, bosses, arms, pods, beams, blobs), for the tail's clearance and the picture's extent"""
    A = D['A']; items, box = D['items'], D['box']; q = D['q']
    its = [(n, m, p + ([q['dxp'], 0.0, A['dz'] + q.get('pack_dz', 0.0)] if n.startswith('pack') else [0.0, 0.0, A['dz']])) for n, m, p in items]
    mos = motors_of(D); its += [(f'motor_{i}', B.MOTOR['m'], np.array([mo['x'], mo['yc'], mo['z']])) for i, mo in enumerate(mos)]
    bx = dict(box, **{f'motor_{i}': np.array(B.MOTOR['half']) for i in range(len(mos))})
    M, G, I = RB.inertia(its, bx); ms, cs, Is, Fr = mass_of(F, ax); mp, mb = ms, 0.0
    if q.get('bumper', 1.0) > 0.5:                                   # the bumpers' TPU on the outermost skin: BUMPER_SHARE of
        from scipy.spatial import ConvexHull                          # the hull's area, spread on the skin within 10 mm of it
        idx = np.argwhere((Fr > -VOX) & (Fr <= 0.0))[::4]; P = np.c_[ax[0][idx[:, 0]], ax[1][idx[:, 1]], ax[2][idx[:, 2]]]
        h = ConvexHull(P); E = h.equations.astype(np.float32)         # (2026-10-29/30: the whole skin, the bay's walls too,
        dh = np.concatenate([-(P[j:j + 20000].astype(np.float32) @ E[:, :3].T + E[:, 3]).max(1) for j in range(0, len(P), 20000)])
        P = P[dh < 10.0]; mb = h.area * BUMPER_SHARE * BUMPER_T * TPU; cb = P.mean(0); d = P - cb   # weighed 1.6-2.1x this)
        Ib = mb / len(P) * (np.eye(3) * (d * d).sum() - d.T @ d)
        m2 = ms + mb; c2 = (ms * cs + mb * cb) / m2; e0, e1 = cs - c2, cb - c2
        Is = Is + ms * (e0 @ e0 * np.eye(3) - np.outer(e0, e0)) + Ib + mb * (e1 @ e1 * np.eye(3) - np.outer(e1, e1)); ms, cs = m2, c2
        mb = ms - mp
    M2 = M + ms; G2 = (M * G + ms * cs) / M2; d0, d1 = G - G2, cs - G2
    I = I + M * (d0 @ d0 * np.eye(3) - np.outer(d0, d0)) + Is + ms * (d1 @ d1 * np.eye(3) - np.outer(d1, d1))
    hulls = [D['core']]; a = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    for sg in (1, -1):
        for b in D['bosses']:
            hulls.append(np.vstack([np.c_[b['x'] + T.TUBE_R * np.cos(a), np.full(12, sg * yy), b['z'] + T.TUBE_R * np.sin(a)] for yy in (b['y0'], b['y1'])]))
        for c, r, Rm in D['blobs']:
            u = np.c_[np.cos(a), np.sin(a), np.zeros(12)]; S3 = np.vstack([u, u[:, [2, 0, 1]], u[:, [1, 2, 0]]]) * r
            hulls.append((S3 @ Rm.T + c) * [1, sg, 1])
    axles = [(b['x'], b['y']) for b in D['bosses']] + [(b['x'], -b['y']) for b in D['bosses']]
    sp = RB.spec(name, hulls, M2, G2, I, axles, A['R'], TW=A['TW'], notes=[f"{len(axles)} wheels R {A['R']:.0f}, one piece"])
    mo = sp['motor']; g = q['gear']; sp['motor'] = dict(stall=mo['stall'] * g, w0=mo['w0'] / g, N=mo['N'] * g, Ir=mo['Ir'])
    sp['shape_g'] = mp                                                  # the printed PLA alone (the cap's); the robot carries both
    if q.get('bumper', 1.0) > 0.5:
        sp['bumper_k'], sp['bumper_g'] = float(q['bumper_k']), float(mb)
    return sp, Fr


def tip_angle(sp):
    """the least tilt (degrees) that tips the robot at rest over an edge of its wheels' footprint"""
    from scipy.spatial import ConvexHull
    W = np.array(sp['wheels']); mw = sp['m_w'] * len(W); G = (sp['M'] * sp['com'] + sp['m_w'] * np.c_[W, np.full(len(W), sp['R'])].sum(0)) / (sp['M'] + mw)
    h = ConvexHull(W); d = -(h.equations[:, :2] @ G[:2] + h.equations[:, 2]).max()
    return math.degrees(math.atan2(d, G[2]))


# ---------- the landing on one wheel ----------
DIRS = [('up', (0, 0, 1)), ('up, in', (0, -1, 1)), ('up, out', (0, 1, 1)), ('up, forward', (1, 0, 1)), ('up, back', (-1, 0, 1)), ('in, flat', (0, -1, 0))]


def fem_mesh(Fr, ax, bay):
    """the stress solve's mesh of a shape (a redistanced field, 2 mm): 4 mm printed voxels, the largest piece, and the
    nodes on the bay's walls, where the parts' mass is held"""
    Fd = Fr[::2, ::2, ::2]; axd = [a[::2] for a in ax]; h = FEM_H
    from scipy.ndimage import label
    solid, share, _ = FE.printed(Fd, h); lab, n = label(solid)
    if n > 1:                                                           # the solve needs one piece: the largest
        solid &= lab == np.bincount(lab[solid]).argmax()
    mesh = FE.Mesh(solid, share, h, [a[0] for a in axd]); X = mesh.X
    o = np.array([a[0] for a in ax]); ijk = np.clip(np.rint((X - o) / VOX).astype(int), 0, np.array(bay.shape) - 1)
    return mesh, np.where(bay[tuple(ijk.T)] < h)[0], axd, solid


def seat(mesh, mo):
    """where a motor's load goes into the shape: the nodes (the gearbox face on the pod's lip; body_tree's motor along
    its tube) and the voxels round them, read apart"""
    from scipy.spatial import cKDTree
    X, c, h = mesh.X, mesh.centres(), FEM_H; r = np.hypot(X[:, 0] - mo['x'], X[:, 2] - mo['z'])
    if 'face' in mo:
        on = np.where((np.abs(X[:, 1] - mo['face']) < 0.6 * h) & (r > SHAFT_HOLE - 0.6 * h) & (r < MOT['gb_d'] / 2 + 0.6 * h))[0]
        near = cKDTree(X[on]).query(c, distance_upper_bound=MOUNT)[0] < MOUNT if len(on) else np.zeros(len(c), bool)
    else:
        y0, y1 = sorted((mo['yc'] - np.sign(mo['y']) * B.MOTOR['half'][1], mo['y_out']))
        on = np.where((r < MOTOR_R + 0.6 * h) & (X[:, 1] > y0 - h) & (X[:, 1] < y1 + h))[0]
        rc = np.hypot(c[:, 0] - mo['x'], c[:, 2] - mo['z']); near = (rc < MOTOR_R + SEAT) & (c[:, 1] > y0 - h) & (c[:, 1] < y1 + h)
    return on, near


def carry(mesh, on, P, f, tau=np.zeros(3)):
    """nodal loads (nn, 3): a force f at P and a moment tau, carried by the nodes `on` as a rigid motor would"""
    rr = mesh.X[on] - mesh.X[on].mean(0); J = (rr * rr).sum() * np.eye(3) - rr.T @ rr
    al = np.linalg.solve(J, np.cross(np.asarray(P) - mesh.X[on].mean(0), f) + tau)
    L = np.zeros((mesh.nn, 3)); L[on] = np.asarray(f) / len(on) + np.cross(al[None, :], rr); return L


def landing(Fr, ax, motors, bay, mass_g):
    """the shape (a redistanced field, 2 mm) landed on each left wheel in each of DIRS, the push carried into the
    shape where the motor sits (the gearbox face on the pod's lip; body_tree's motor along its tube) as a rigid motor
    would, its mass held on the bay's walls: each voxel's printed-wall stress (MPa, smoothed, the worst case), the
    solve, and the peak away from the seat (the seat's own peak is 'mount')"""
    mesh, mass_nodes, axd, solid = fem_mesh(Fr, ax, bay)
    Fm = LAND * math.sqrt(2 * mass_g * 1e-3 * 9.81 * DROP_M * TYRE_K * 1e3)
    cases, loads, wheel_of, seats = [], [], [], []
    for mo in motors:
        if mo['y'] < 0:
            continue
        on, nr = seat(mesh, mo); seats.append(nr)
        if len(on) < 8:
            return None
        for a in range(3):                                              # a unit push at the wheel's centre along x, y, z (any
            loads.append(carry(mesh, on, [mo['x'], mo['y'], mo['z']], np.eye(3)[a]))   # direction is their sum)
        wheel_of.append(mo['x'])
    loads = np.stack(loads, axis=2); bal, fixed = FE.inertia_relief(mesh, loads, mass_nodes, 1.0)
    u1, it = mesh.solve_mg(bal, fixed, tol=1e-5)
    if not mesh.resid < 1e-3:                                           # the multigrid lost (NaN, 2026-10-31): the plain solve, slow but sure,
        u1, it = mesh.solve(bal, fixed, tol=1e-5)                       # rather than a shape grown from NaN
        if not mesh.resid < 1e-3:
            raise RuntimeError(f'landing: the solve did not converge (residual {mesh.resid:.1e})')
    us = []
    for k, xw in enumerate(wheel_of):
        for nm, d in DIRS:
            d = np.asarray(d, float) / np.linalg.norm(d) * Fm; us.append(u1[:, :, 3 * k:3 * k + 3] @ d); cases.append((xw, nm))
    u = np.stack(us, axis=2)
    s = mesh.smooth(mesh.stress(u)); worst = s.max(1); case = s.argmax(1)
    near = np.any(seats, axis=0)                                        # where the motor's load goes in: its own number
    k = np.where(~near)[0][np.argmax(worst[~near])]
    return dict(mesh=mesh, worst=worst, near=near, peak=float(worst[k]), at=mesh.centres()[k], case=cases[case[k]], F=Fm, iters=it, resid=mesh.resid,
                mount=float(worst[near].max()) if near.any() else 0.0, ay=ax[1],
                axd=axd, solid=solid, mass_nodes=mass_nodes)


def stress_grid(L, shape, ay, seat=0.0):
    """the worst stress on the 2 mm grid, each voxel the larger of its own and its mirror's (only the left wheels land;
    the right's landings are their mirror. 2026-10-29: unmirrored, SKO found the right side idle and cut a motor loose,
    and CAO had grown only the left)"""
    g = np.zeros(L['solid'].shape); v = L['worst'].copy(); v[L['near']] = seat; g[tuple(L['mesh'].ijk.T)] = v
    return _up(g, shape, ay)


def _up(g, shape, ay):
    """a value on the stress solve's 4 mm grid onto the field's 2 mm grid, each voxel the larger of its own and its
    mirror's"""
    up = np.repeat(np.repeat(np.repeat(g, 2, 0), 2, 1), 2, 2)[:shape[0], :shape[1], :shape[2]]
    up = np.pad(up, [(0, max(0, shape[i] - up.shape[i])) for i in range(3)])
    j = np.clip(np.rint((-ay - ay[0]) / VOX).astype(int), 0, len(ay) - 1)
    return np.maximum(up, up[:, j, :])


SECTION_R = (4.0, 6.0, 8.0, 11.0, 16.0, 22.0, 32.0, 45.0, 64.0, 90.0)   # mm: the balls section_d tries, about 1.4x apart


def section_d(L, fill=True):
    """each voxel's slice diameter (mm, on the stress solve's 4 mm grid): the largest ball inside the shape's outline (its
    hollows filled, so the body reads as the body, not as its bay's wall) that holds the voxel, doubled. The local
    thickness of the member it's in (Hildebrand & Ruegsegger, 1997), to SECTION_R's steps; 0 outside. fill=False: the
    hollows left open (check()'s control)"""
    from scipy.ndimage import binary_fill_holes, distance_transform_edt as edt
    env = binary_fill_holes(L['solid']) if fill else L['solid']; D = edt(env) * FEM_H; t = np.zeros(env.shape)
    for r in SECTION_R:
        C = D >= r
        if not C.any():
            break
        t[(edt(~C) * FEM_H <= r) & env] = 2 * r
    return t


def grow_map(L, shape, heat=None):
    """the growth (mm) on the 2 mm grid. Each overstressed voxel's slice grows as a beam in bending would need to bring
    its stress down to GROW_FROM x the allowed: stress goes as 1/d^3, so its radius by d/2 ((s/target)^(1/3) - 1), at
    most GROW a round. Carried REACH* out from the voxel (a peak under the surface must move the surface: the first
    version spread it 4 mm, and a peak 9 mm deep in a motor's collar never grew), then smoothed GROW_BLUR.
    2026-10-30 (Zach: "the growth step should be weighted better... diameter of the slice you are putting the growth
    on"): until then every slice grew the same GROW at 1.25x the allowed (_grow_map_flat), so a thin arm's root grew as
    much as the body, and lumps stood out on the thin parts.
    heat: the falls on this shape (drops.durability, make's heat): each voxel also grows by the same law against its
    worst fall, times its heat, the share of the falls that take it past the allowed (Zach, 2026-10-30: "a heatmap of
    the breakable parts from testing the shape"). A spot one fall in 24 overstresses gets 1/24 of that growth; grown at
    full against the worst fall (2026-10-29), the shapes grew warts and broke more often"""
    from scipy.ndimage import maximum_filter, gaussian_filter
    s = stress_grid(L, shape, L['ay']); d = _up(section_d(L), shape, L['ay'])
    law = lambda st: 0.5 * d * (np.maximum(st / (GROW_FROM * ALLOW), 1.0) ** (1.0 / 3.0) - 1.0)
    up = law(s)
    if heat is not None:
        up = np.maximum(up, _up(_grid4(L, heat['heat']), shape, L['ay']) * law(_up(_grid4(L, np.where(heat['keep'], heat['stress'], 0.0)), shape, L['ay'])))
    return gaussian_filter(maximum_filter(np.clip(up, 0.0, GROW), 2 * int(REACH / VOX) + 1), GROW_BLUR / VOX)


def _grid4(L, v):
    """a value per stress-solve voxel onto its 4 mm grid"""
    g = np.zeros(L['solid'].shape); g[tuple(L['mesh'].ijk.T)] = v
    return g


def _grow_map_flat(L, shape):
    """SUPERSEDED 2026-10-30 by grow_map (weighted by the slice's diameter): GROW at 1.25x the allowed and over, from 0
    at GROW_FROM x the allowed, whatever the slice's size. Kept to compare against"""
    from scipy.ndimage import maximum_filter, gaussian_filter
    up = GROW * np.clip((stress_grid(L, shape, L['ay']) / ALLOW - GROW_FROM) / (1.25 - GROW_FROM), 0.0, 1.0)   # (first at 2x: a 14 MPa peak crept)
    return gaussian_filter(maximum_filter(up, 2 * int(REACH / VOX) + 1), 2.0)


def shrink_map(L, shape, low=SKO_LOW, heat=None):
    """SKO (Mattheck's soft kill, 1992), on the 2 mm grid: SHRINK where nothing within REACH carries low, from 0 at
    low; the motor's seat counts as loaded. heat: the falls count as load too, so SKO can't cut what a fall needs"""
    from scipy.ndimage import maximum_filter, gaussian_filter
    s = stress_grid(L, shape, L['ay'], seat=1e3)
    if heat is not None:
        s = np.maximum(s, _up(_grid4(L, np.where(heat['keep'], heat['stress'], 1e3)), shape, L['ay']))
    near = maximum_filter(s, 2 * int(SKO_REACH / VOX) + 1)
    return gaussian_filter(SHRINK * np.clip(1.0 - near / low, 0.0, 1.0), 2.0)


def with_drops(L, sp, D, n, cases=None):
    """the landing's stresses joined by n of G1's falls (drops.py) on the same mesh: each voxel the worse of the two;
    the falls' contact patches join the seats (read apart, kept by SKO); the peak the worse. cases: falls recorded on
    an earlier round, put on this shape"""
    import drops as DR
    Dr = DR.durability(sp, L['mesh'], L['mass_nodes'], motors_of(D), DR.pieces(L['mesh']), n, cases=cases, bumper_k=sp.get('bumper_k'))
    worst = np.maximum(L['worst'], np.where(Dr['keep'], Dr['stress'], 0.0)); near = L['near'] | ~Dr['keep']
    k = np.where(~near)[0][np.argmax(worst[~near])]
    return dict(L, worst=worst, near=near, peak=float(worst[k]), at=L['mesh'].centres()[k], wheel_peak=L['peak'], drops=Dr,
                case=L['case'] if L['peak'] >= Dr['worst'] else ('fall', f"fall {Dr['fall'] + 1}, {Dr['body_share']:.0%} on the body"))


def _dropped(L, sp, D, falls):
    """G1's falls on the shape as it stands (with_drops), for the record"""
    dr = with_drops(L, sp, D, falls)['drops']
    return dict(drop_peak=dr['worst'], over=dr['over'], broken=dr['broken'], falls=dr['n'], body_share=dr['body_share'])


def make(q, name='unibody', log=print, rounds=ROUNDS, falls=0, cap=CAP_G, heat=0, D=None):
    """the design q grown until it holds its landings, and cut under the weight cap (or rounds run out): a dict with the
    spec, the shapes and stresses before and after, or None when it can't be made (the anchors, a tail that can't
    clear, the seat, the body and bosses alone over the cap). falls: G1's falls dropped on the drawn shape and on the
    finished one, the verdict (2026-10-29, Zach: "test there durability as you go"; 2026-10-30: no longer grown against,
    which made warts and broke more often). heat: that many falls each round as well, the same hits every round
    (simulated on the drawn shape), growing each voxel by its share of them over the allowed (grow_map's heat).
    A trial, off by default: on seed 1030's four (ripple off), 16-17 of 24 falls each took some spot past the allowed,
    but a different spot each (about 2 % of the shape over in any fall, no voxel in more than 5 of 24), so the heat
    stayed under 0.21 and the grown shapes moved under 1 %: the falls have no breakable part for growth to find.
    D: a design already drawn (design_t3); q is then its own D['q']"""
    D = design(q) if D is None else D
    if D is None:
        return None
    ax = grid(D); U, Fc, Freq = union(D, ax); F, bay = cut(D, U, ax, Fc)
    if D.get('loose'):
        return None
    sp, Fr = spec(D, F, ax, name)
    if q['limb'] > 0.5:
        if D.get('limb'):                                               # a tail given with the design (design_t3)
            lm = D['limb']
        else:
            st = B._tail(sp, q, D['core'], D['A']['rear'][1])
            if st is None:
                return None
            P = np.asarray(st['hulls'][-1]); D['tail'] = dict(x0=float(P[:, 0].min()), x1=float(P[:, 0].max()), z=float(P[:, 2].mean()))
            lm = st['limb']
        ax = grid(D); U, Fc, Freq = union(D, ax); F, bay = cut(D, U, ax, Fc); sp2, Fr = spec(D, F, ax, name)
        sp = RB.add_limb(sp2, q['L'], q['tq'], lm['th_push'], lm['th_stow'], base=np.asarray(lm['base']), L2=lm.get('L2', 0.0), tq2=lm.get('tq2'))
        sp['limb'].update({k: lm[k] for k in ('rear_up', 'foot_r', 'm_foot') if k in lm})   # as given (2026-10-31: until then a
        sp = RB.dims(sp); sp['shape_g'] = sp2['shape_g']; sp['solid_tail'] = True          # given two-link tail came out one link,
                                                                        # its rear-up and foot dropped: the winners' one pieces had them)
    if cap and sp['shape_g'] > cap:                                     # over the cap as drawn: trimming can't bring it down (2026-10-30:
        log(f"  drawn at {sp['shape_g']:.0f} g, over the {cap:.0f} g cap"); return None   # a print weighs its walls, area x 1.6 mm,
                                                                        # and shaving moves the wall in: SKO at full bar took a 2.97 kg
                                                                        # shape down 50 g a round, 110 g a round below the uncapped)
    from scipy.ndimage import label
    first = None; G = np.zeros_like(U); S = np.zeros_like(U); hist = []; lim = q.get('trim', 40.0); cases = H = None
    for k in range(rounds + 1):
        L = landing(Fr, ax, motors_of(D), bay, sp['mass'])
        if L is None:
            return None
        hist.append(dict(peak=L['peak'], mount=L['mount'], shape_g=sp['shape_g'], mass=sp['mass'], iters=L['iters'], case=L['case'],
                         wheel_peak=L['peak'], falls=0))
        if falls and k == 0:                                            # the drawn shape dropped, for the before
            hist[-1].update(_dropped(L, sp, D, falls))
        if heat:                                                        # the falls' heatmap on the shape as it stands
            import drops as DR
            H = DR.durability(sp, L['mesh'], L['mass_nodes'], motors_of(D), DR.pieces(L['mesh']), heat, cases=cases, bumper_k=sp.get('bumper_k'))
            cases = H['cases']; hist[-1]['heat_over'] = H['over']
        heavy = bool(cap) and sp['shape_g'] > cap * (CAP_GIVE if L['peak'] > ALLOW else 1.0)   # over the cap: SKO's bar rises to
                                                                        # the allowed at 25 % over
        low = SKO_LOW + (ALLOW - SKO_LOW) * min(max((sp['shape_g'] / cap - 1.0) / 0.25, 0.0), 1.0) if heavy else SKO_LOW
        tail = f"; drops {hist[-1]['drop_peak']:.0f}, {hist[-1]['over']} of {falls} over" if 'drop_peak' in hist[-1] else ''
        log(f"  round {k}: peak {L['peak']:.1f} MPa ({L['case'][1]}; mount {L['mount']:.0f}{tail}), shape {sp['shape_g']:.0f} g"
            f"{f' (cut below {low:.1f} MPa)' if heavy else ''}, robot {sp['mass'] / 1000:.2f} kg, {L['iters']} iterations (residual {L['resid']:.1e})")
        if first is None:
            first = dict(F=F, sp=sp, L=L, H=H)
        settled = k > 0 and abs(hist[-1]['shape_g'] - hist[-2]['shape_g']) < 0.01 * hist[-2]['shape_g']
        if (L['peak'] <= ALLOW and settled and not heavy) or k == rounds:
            break
        if heavy:
            lim = np.inf                                                # and it may cut down to what must stay
        G += grow_map(L, U.shape, H); S = np.minimum(S + shrink_map(L, U.shape, low, H), lim)   # CAO where it's over, SKO where idle
        from scipy.ndimage import gaussian_filter                       # smoothed before the cuts, which stay sharp (SHAPE_BLUR)
        Fn, bayn = cut(D, gaussian_filter(np.minimum(U - G + S, Freq), SHAPE_BLUR / VOX), ax, Fc)
        if D.pop('loose', False):
            log('  SKO cut a motor loose: kept the round before'); break
        F, bay = Fn, bayn; spn, Fr = spec(D, F, ax, name); _torch()[0].cuda.empty_cache()
        sp = dict(sp, M=spn['M'], com=spn['com'], I=spn['I'], shape_g=spn['shape_g'], bumper_k=spn.get('bumper_k'), bumper_g=spn.get('bumper_g')); sp = RB.dims(sp)
    if falls:                                                           # the verdict: the finished shape dropped
        hist.append(dict(hist[-1], fresh=True, **_dropped(L, sp, D, falls)))
        log(f"  dropped: {hist[-1]['drop_peak']:.0f} MPa, {hist[-1]['over']} of {falls} over, {hist[-1]['broken']} past {SIGMA_ULT:.0f}")
    pieces = int(label(F < 0)[1])
    return dict(D=D, ax=ax, first=first, F=F, bay=bay, sp=sp, L=L, hist=hist, pieces=pieces, holds=L['peak'] <= ALLOW, tip=tip_angle(sp),
                under=not cap or sp['shape_g'] <= cap * 1.02)


# ---------- pictures ----------
def folds(ms):
    """faces cutting through another face; None when pymeshlab can't count them (read as not clean)"""
    try:
        ms.compute_selection_by_self_intersections_per_face(); n = ms.current_mesh().selected_face_number(); ms.set_selection_none()
        return n
    except Exception:
        return None


# the decimations surface() tries in turn: (x maxf, settings). 2026-10-30: the plain one folded 6-22 faces through their
# neighbours on the sheet's designs (the mesh report; marching cubes alone leaves none), and no one setting stayed clean
# on every design. All stay under MuJoCo's 200,000-face STL limit (render() refuses more; a 1.5x try folded 292 anyway)
_PLANAR = dict(preservenormal=True, preservetopology=True, qualitythr=0.6, planarquadric=True)
DECIMATE = [(1.0, _PLANAR), (1.0, dict(preservenormal=True)), (1.2, _PLANAR), (0.8, _PLANAR), (1.2, dict(preservenormal=True))]


def surface(F, ax, maxf=150000):
    """the shape's mesh: marching cubes, decimated to about maxf faces by the first of DECIMATE that leaves no folds;
    when every one folds, the fewest folds cut out with a ring of faces round them and the holes closed (pan_print_set's
    repair), up to four times"""
    from skimage import measure
    import pymeshlab as ml
    v, f, *_ = measure.marching_cubes(F, 0.0, spacing=(VOX, VOX, VOX)); v = v + np.array([a[0] for a in ax])
    ms = ml.MeshSet(); ms.add_mesh(ml.Mesh(v, f)); ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-4))
    if ms.current_mesh().face_number() <= maxf:
        m = ms.current_mesh(); return m.vertex_matrix(), m.face_matrix()
    v, f = ms.current_mesh().vertex_matrix(), ms.current_mesh().face_matrix(); best = None
    for mult, kw in DECIMATE:
        md = ml.MeshSet(); md.add_mesh(ml.Mesh(v, f)); md.meshing_decimation_quadric_edge_collapse(targetfacenum=int(maxf * mult), **kw)
        n = folds(md)
        if n == 0:
            m = md.current_mesh(); return m.vertex_matrix(), m.face_matrix()
        if best is None or (n is not None and (best[0] is None or n < best[0])):
            best = (n, md)
    md = best[1]
    for _ in range(4):
        if folds(md) == 0:
            break
        md.compute_selection_by_self_intersections_per_face(); md.apply_selection_dilatation()
        md.meshing_remove_selected_vertices_and_faces(); md.meshing_close_holes(maxholesize=60, newfaceselected=False)
        md.set_selection_none()
    m = md.current_mesh(); return m.vertex_matrix(), m.face_matrix()


def _stl(v, f):
    tri = v[f]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(f), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]); rec['n'] = n; rec['v'] = tri
    return b'unibody'.ljust(80, b' ') + np.uint32(len(f)).tobytes() + rec.tobytes()


def face_stress(v, f, L):
    """each face's stress: the voxel 3 mm in under it (or the most stressed beside it)"""
    from scipy.ndimage import maximum_filter
    mesh = L['mesh']; Sg = np.zeros(L['solid'].shape); w = L['worst'].copy(); Sg[tuple(mesh.ijk.T)] = w
    Sx = maximum_filter(Sg, 3); tri = v[f]; c = tri.mean(1); n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12); p = c - 3.0 * n
    o = np.array([a[0] for a in L['axd']]); ijk = np.clip(np.rint((p - o) / FEM_H).astype(int), 0, np.array(Sg.shape) - 1)
    s = Sg[tuple(ijk.T)]; return np.where(s > 0, s, Sx[tuple(ijk.T)])


def colour(r):
    """green (unloaded) to yellow (the allowed) to red (PLA's strength across layers) and past it, dark red"""
    r = float(np.clip(r, 0, 1.5))
    stops = [(0.0, (0.25, 0.7, 0.35)), (0.5, (0.97, 0.8, 0.2)), (1.0, (0.85, 0.12, 0.1)), (1.5, (0.45, 0.02, 0.05))]
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if r <= b:
            t = (r - a) / (b - a); return tuple(np.array(ca) + t * (np.array(cb) - np.array(ca)))
    return stops[-1][1]


def render(sp, v, f, face_rgb=None, w=420, h=300, azim=145.0, elev=-20.0, motors=None):
    """the shape (faces grouped by colour, or all tan), the motors, wheels and tail, rendered by MuJoCo"""
    import mujoco
    S = 1e-3; files, assets, geoms = {}, [], []
    if face_rgb is None:
        groups = {(0.86, 0.62, 0.48): np.arange(len(f))}
    else:
        key = [tuple(np.round(c, 2)) for c in face_rgb]; groups = {}
        for i, k in enumerate(key):
            groups.setdefault(k, []).append(i)
        big = [k for k, v in groups.items() if len(v) >= 4]                # a colour on under 4 faces joins the nearest colour
        for k in [k for k, v in groups.items() if len(v) < 4]:              # (2026-10-30: MuJoCo refuses a mesh under 4 vertices)
            if big:
                groups[min(big, key=lambda b: sum((x - y) ** 2 for x, y in zip(b, k)))] += groups.pop(k)
    for gi, (rgb, idx) in enumerate(groups.items()):
        if len(idx) < 1:
            continue
        files[f's{gi}.stl'] = _stl(v, f[np.asarray(idx)])
        assets.append(f'<mesh name="s{gi}" file="s{gi}.stl" scale="{S} {S} {S}" inertia="shell"/>')
        geoms.append(f'<geom type="mesh" mesh="s{gi}" rgba="{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} 1"/>')
    for mo in motors or ():
        hl = MOT_L / 2 if 'face' in mo else B.MOTOR['half'][1]
        geoms.append(f'<geom type="cylinder" size="{MOTOR_R * S:.4f} {hl * S:.4f}" pos="{mo["x"] * S:.4f} {mo["yc"] * S:.4f} {mo["z"] * S:.4f}" euler="90 0 0" rgba=".62 .64 .68 1"/>')
    for x, y in sp['wheels']:
        geoms.append(f'<geom type="cylinder" size="{sp["R"] * S:.4f} {sp["TW"] / 2 * S:.4f}" pos="{x * S:.4f} {y * S:.4f} {sp["R"] * S:.4f}" euler="90 0 0" rgba=".13 .13 .14 1"/>')
    lm = sp.get('limb')
    if lm:
        P = RB.limb_points(lm, 0.0, lm['th_stow']); b0, b1 = P[0] * S, P[7] * S
        geoms.append(f'<geom type="capsule" fromto="{b0[0]:.4f} {b0[1]:.4f} {b0[2]:.4f} {b1[0]:.4f} {b1[1]:.4f} {b1[2]:.4f}" size="{RB.LINK_R * S:.4f}" rgba=".1 .5 .4 1"/>')
    fl = sp.get('flip')
    if fl:                                                              # the flippers stowed (2026-10-31)
        a = math.radians(fl['stow']); dd = np.array([math.cos(a), 0.0, math.sin(a)]) * fl['L']
        for p in fl['pivots']:
            b0, b1 = np.asarray(p, float) * S, (np.asarray(p, float) + dd) * S
            geoms.append(f'<geom type="capsule" fromto="{b0[0]:.4f} {b0[1]:.4f} {b0[2]:.4f} {b1[0]:.4f} {b1[1]:.4f} {b1[2]:.4f}" size="{RB.LINK_R * S:.4f}" rgba=".1 .5 .4 1"/>')
    xml = f"""<mujoco><visual><global offwidth="{w}" offheight="{h}"/><quality shadowsize="2048"/><headlight ambient=".35 .35 .35"/></visual>
      <default><geom contype="0" conaffinity="0"/></default>
      <asset>{''.join(assets)}
      <texture name="chk" type="2d" builtin="checker" rgb1=".93 .93 .91" rgb2=".86 .86 .84" width="256" height="256"/><material name="floor" texture="chk" texrepeat="12 12"/>
      <texture name="sky" type="skybox" builtin="gradient" rgb1=".97 .97 .96" rgb2=".85 .86 .84" width="64" height="64"/></asset>
      <worldbody><light pos=".4 -.6 1.5" dir="-.2 .4 -1" diffuse=".7 .7 .66" castshadow="true"/><geom type="plane" size="3 3 .1" material="floor"/>
      {''.join(geoms)}</worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml, files); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    E = np.vstack([RB.extremes(sp), v]); lo, hi = E.min(0), E.max(0)
    cam = mujoco.MjvCamera(); cam.lookat[:] = [(lo[0] + hi[0]) / 2 * S, 0.0, 0.35 * (hi[2] - lo[2]) * S]
    cam.distance = 1.9 * max(hi - lo) * S; cam.azimuth, cam.elevation = azim, elev
    with mujoco.Renderer(m, h, w) as r:
        r.update_scene(d, cam); return r.render()


def stress_picture(sp, F, ax, L, motors=None, **kw):
    v, f = surface(F, ax); s = face_stress(v, f, L)
    return render(sp, v, f, [colour(x / SIGMA_ULT) for x in np.round(s / SIGMA_ULT * 12) / 12 * SIGMA_ULT], motors=motors, **kw)


def section(r, path, title=''):
    """a cut through the first left wheel's pod (the y-z plane at its axle): the shape, the motor, lip, screws, shaft
    and wheel drawn in with the numbers the generator assumes; beside it the same cut's stress -> path"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.colors import LinearSegmentedColormap
    D, F, ax, L = r['D'], r['F'], r['ax'], r['L']; b = D['bosses'][0]; R, TW = D['A']['R'], D['A']['TW']; z = R; f = b['face']
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 8.2)); fig.patch.set_facecolor('white')
    i = int(np.argmin(np.abs(ax[0] - b['x'])))
    a1.contourf(ax[1], ax[2], F[i].T, levels=[-1e9, 0], colors=['#e3b08f'])
    a1.contour(ax[1], ax[2], F[i].T, levels=[0], colors=['#8a5a3c'], linewidths=0.8)
    a1.contourf(ax[1], ax[2], r['bay'][i].T, levels=[-1e9, 0], colors=['#eef1f4'])
    grey = dict(fc='#a9adb3', ec='#55595e', lw=0.8); y = f
    for nm, l, d in (('gearbox', MOT['gb_l'], MOT['gb_d']), ('motor', MOT['m_l'], MOT['m_d']), ('encoder', MOT['enc_l'], MOT['enc_d'])):
        a1.add_patch(Rectangle((y - l, z - d / 2), l, d, **grey)); a1.text(y - l / 2, z, f"{nm}\nØ{d:g} x {l:g}", ha='center', va='center', fontsize=7); y -= l
    a1.add_patch(Rectangle((f, z - MOT['shaft_d'] / 2), MOT['shaft_l'], MOT['shaft_d'], fc='#6d7278', ec='none'))
    for zz in (z + MOT['pcd'] / 2, z - MOT['pcd'] / 2):                 # two of the six M3 through the lip
        a1.add_patch(Rectangle((f - 4.0, zz - 1.5), LIP + 4.0 + 2.0, 3.0, fc='#3c4046', ec='none'))
    yo = b['y'] + TW / 2; wheel = dict(fc='#2b2c2e', ec='none', alpha=0.85)
    for top in (True, False):                                           # the tyre and rim, above and below the axle
        z0 = 2 * R - RIM_IN if top else 0.0
        a1.add_patch(Rectangle((b['y'] - TW / 2, z0), TW, RIM_IN, **wheel))
    if b['dish']:
        a1.add_patch(Rectangle((yo - 5.0, RIM_IN), 5.0, 2 * R - 2 * RIM_IN, **wheel))          # the disc
        a1.add_patch(Rectangle((f + LIP + 2.0, z - 9.0), yo - 5.0 - f - LIP - 2.0, 18.0, **wheel))   # the hub on the shaft
    else:
        a1.add_patch(Rectangle((b['y'] - TW / 2, RIM_IN), 5.0, 2 * R - 2 * RIM_IN, **wheel))
    a1.axhline(0, color='k', lw=0.8)
    notes = [f"pod Ø{2 * POD_R:g} round a Ø{2 * POD_IR:g} bore (6 mm wall*), open inboard",
             f"lip {LIP:g} mm*: the gearbox face screws to it, {MOT['holes']} x M3 on Ø{MOT['pcd']:g}*, shaft hole Ø{2 * SHAFT_HOLE:g}",
             f"shaft Ø{MOT['shaft_d']:g} x {MOT['shaft_l']:g}*; the wheel's outer face {FACE_OUT:g} past the gearbox face",
             (f"wheel R {R:.0f}, tyre {TW:.0f} wide: a dish, its rim {RIM_IN:g} inside the tyre, {WHEEL_GAP:g} clear of the pod" if b['dish'] else
              f"wheel R {R:.0f} too small to wrap the pod: hub outboard on a shaft extension"),
             f"the wheel's centre {abs(b['y'] - f):.0f} mm {'in' if b['y'] < f else 'out'}board of the gearbox face (the lever on the gearbox)"]
    a1.text(0.0, -0.13, '\n'.join(notes), transform=a1.transAxes, va='top', fontsize=8.5, family='monospace')
    a1.set_aspect('equal'); a1.set_xlim(b['y0'] - 30, yo + 15); a1.set_ylim(-5, max(2 * R, ax[2][-1]) + 10)
    a1.set_xlabel('y, out from the centre line (mm)'); a1.set_ylabel('z (mm)'); a1.set_title(f'the cut at the wheel\'s axle (x {b["x"]:.0f}); grey: the bay', fontsize=10)
    cm = LinearSegmentedColormap.from_list('s', [(0, (0.25, 0.7, 0.35)), (1 / 3, (0.97, 0.8, 0.2)), (2 / 3, (0.85, 0.12, 0.1)), (1, (0.45, 0.02, 0.05))])
    c = L['mesh'].centres(); k = np.abs(c[:, 0] - b['x']) < FEM_H / 2 + 0.01
    sc = a2.scatter(c[k, 1], c[k, 2], c=L['worst'][k], cmap=cm, vmin=0, vmax=1.5 * SIGMA_ULT, marker='s', s=14)
    plt.colorbar(sc, ax=a2, label='printed wall stress, MPa (worst landing)')
    a2.set_aspect('equal'); a2.set_xlim(a1.get_xlim()); a2.set_ylim(a1.get_ylim()); a2.set_title(f'its stress (peak {L["peak"]:.0f} MPa away from the seat, '
                                                                                                 f'seat {L["mount"]:.0f})', fontsize=10)
    fig.suptitle(title or "How a one-piece body holds a motor (* guessed: the 37D class's datasheet, the Trainer's corner module)", fontsize=11, x=0.02, ha='left')
    plt.tight_layout(); plt.savefig(path, dpi=100); plt.close(fig)


def sobol(n, seed=0):
    from scipy.stats import qmc
    Z = qmc.Sobol(len(KNOBS), scramble=True, seed=seed).random_base2(int(math.ceil(math.log2(n))))[:n]
    return [{k: float(lo + z * (hi - lo)) for (k, lo, hi, _), z in zip(KNOBS, row)} for row in Z]


# ---------- the sheets ----------
FALLS = 24                                  # G1's falls each round on the sheets (drops.py)


def _title_new(i, r):
    sp, h0, h = r['sp'], r['hist'][0], r['hist'][-1]
    held = 'holds' if r['holds'] else 'over'
    pieces = f"; {r['pieces']} pieces" if r['pieces'] != 1 else ''
    out = ('' if r['D']['bosses'][0]['dish'] else ', hubs outboard') + (f", bumpers {sp['bumper_k']:.0f} N/mm" if sp.get('bumper_k') else '')
    drops = (f"\nfalls {h0['drop_peak']:.0f} -> {h['drop_peak']:.0f} MPa, over {h0['over']} -> {h['over']} of {h['falls']}, "
             f"broken {h0['broken']} -> {h['broken']}") if h.get('falls') else ''
    cap = '' if r.get('under', True) else ' (over the cap)'
    return (f"{i}: {len(sp['wheels'])} wheels{', tail' if sp.get('limb') else ''}{out}{pieces}\n"
            f"shape {h0['shape_g']:.0f} -> {sp['shape_g']:.0f} g{cap}, robot {sp['mass'] / 1000:.1f} kg, tips {r['tip']:.0f} deg\n"
            f"landings {h['wheel_peak']:.0f} MPa, {held}{drops}")


def _sheet_job(a):
    """a worker: the design made with its falls, its picture and its record"""
    i, q = a
    try:                                                                # a GPU fault skips the design, not the sheet (2026-10-30:
        r = make(q, log=lambda *_: None, falls=FALLS)                   # a CUDA "unknown error" ended a run on its last draw)
    except Exception as e:
        print(f'draw {i}: {type(e).__name__}: {str(e).splitlines()[0]}', flush=True); return i, None
    if r is None:
        return i, None
    v, f = surface(r['F'], r['ax'])
    return i, dict(img=render(r['sp'], v, f, motors=motors_of(r['D'])), title=_title_new('{n}', r),
                   rec=dict(q=q, hist=r['hist'], holds=r['holds'], tip=r['tip'], pieces=r['pieces'], mount=r['L']['mount'], under=r['under']))


def sheet(seed=None, n=12, workers=2, resume=False):
    """n Sobol designs over KNOBS, each grown and cut (CAO + SKO) against its wheel landings, under the weight cap, and
    dropped before and after -> out/unibody/sheet.png. resume: carry on after the designs already in sheet_<seed>.pkl,
    the rest drawn on their own sheet (sheet_from_<k>.png)"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from multiprocessing import Pool
    seed = int(np.random.SeedSequence().entropy % 100000) if seed is None else seed
    os.makedirs(OUT, exist_ok=True); cols = 3; rows = math.ceil(n / cols)
    draws = sobol(16 * n, seed); drawn = tried = first = 0; rec = []; pk = os.path.join(OUT, f'sheet_{seed}.pkl')   # (2026-10-30: the cap
                                                                        # refuses about 6 draws in 7)
    stamp.check(pk, fresh=not resume)                                    # a resume only over designs made by this code
    if resume and os.path.exists(pk):
        rec = pickle.load(open(pk, 'rb')); drawn = first = len(rec)
        tried = first_draw = max(next(j for j, q in enumerate(draws) if q == r['q']) for r in rec) + 1
    else:
        first_draw = 0
    rows = math.ceil((n - first) / cols)
    fig = plt.figure(figsize=(12, 4.0 * rows)); fig.patch.set_facecolor('white')
    name = 'sheet.png' if not first else f'sheet_from_{first + 1}.png'
    with Pool(workers, maxtasksperchild=1) as pool:                     # each design in a fresh process: a clean GPU context
        for i, res in pool.imap(_sheet_job, list(enumerate(draws))[first_draw:], chunksize=1):
            if drawn >= n:
                break
            tried += 1
            if res is None:
                continue
            drawn += 1; ax = fig.add_subplot(rows, cols, drawn - first); ax.set_axis_off(); ax.imshow(res['img'])
            t = res['title'].replace('{n}', str(drawn)); ax.set_title(t, fontsize=9, loc='left'); rec.append(res['rec'])
            print(t.replace('\n', ' '), flush=True)
            fig.savefig(os.path.join(OUT, 'sheet_so_far.png'), dpi=80)   # the sheet as it fills (Zach: "keep me updated with pictures as you go")
            pickle.dump(rec, open(os.path.join(OUT, f'sheet_{seed}.pkl'), 'wb'))
            if drawn >= n:                                              # stop here, not after the next design arrives
                break
        pool.terminate()
    fig.suptitle(f'One-piece bodies (unibody.py), Sobol seed {seed}: {drawn} of {tried} draws made. Each round lands every wheel six '
                 f'ways, grows where the printed wall passes {ALLOW:.1f} MPa\nand cuts where nothing near carries half that (CAO + SKO), '
                 f'harder over the {CAP_G / 1000:.0f} kg cap. {FALLS} of G1\'s falls on soft TPU bumpers, drawn shape -> finished', fontsize=11, x=0.02, ha='left')
    plt.tight_layout(rect=(0, 0, 1, 0.97)); p = os.path.join(OUT, name); plt.savefig(p, dpi=90)
    pickle.dump(rec, open(pk, 'wb')); print(p, 'seed', seed)


# ---------- a pass through the gauges ----------
# 2026-10-30: the one-piece bodies had only been judged on strength; a pass drives them through the seven gauges as the
# capability search screens a design (capability.screen: its seed, 6 tries a rung, G2's ladder past 150 mm), T3
# screened beside them. The sims see the shape itself: the body's hull and the field's own convex pieces (drops.py),
# not the pieces it was drawn from (the arms, pods and fillets had been missing from the sims).
GAUGE_SEED, GAUGE_TRIES = 40000, 6
GAUGE_WORKERS = 4                           # CPU workers (Zach, 2026-10-30: "i wanted to be able to use my computer for things today")
GAUGE_LINE = (('up', 'upright {:.2f}'), ('climb', 'step {:.0f} mm'), ('turn', 'turn {:.0f} mm'), ('h_up', 'hills {:.0f}'),
              ('h_down', '/{:.0f} deg'), ('crest', 'crest {:.0f} deg'), ('push', 'push {:.1f} kg'))


TAIL_CLEAR = B.TURN_R + 25.0                # mm round the tail's pivot that no piece of the body reaches in the sims


def gauge_spec(r):
    """a made design's spec as the gauges' sims see it: the body's hull, then the field's convex pieces, less those
    within TAIL_CLEAR of the tail's pivot. The tail's link starts at the pivot, inside its own mount boss, and the body
    stops the tail (solid_tail): with the boss's pieces in, the tail jammed. T3 as one piece read step 0, push 0 kg,
    hills 0/0; without them 50 mm, 1.0 kg, 45/45, turn 386 mm (T3: 392). Found 2026-10-30, after the overnight pass,
    whose tailed designs had them in"""
    import drops as DR
    P = DR.pieces(r['L']['mesh']); lm = r['sp'].get('limb')
    if lm:
        b = np.asarray(lm['base'], float); P = [p for p in P if np.linalg.norm(np.asarray(p, float) - b, axis=1).min() >= TAIL_CLEAR]
    return RB.dims(dict(r['sp'], hulls=[r['sp']['hulls'][0]] + P))


def _pass_make(a):
    """a GPU worker: the design made and dropped, its picture, and its spec for the gauges"""
    i, q = a
    try:
        r = make(q, log=lambda *_: None, falls=FALLS)
    except Exception as e:
        print(f'draw {i}: {type(e).__name__}: {str(e).splitlines()[0]}', flush=True); return i, None
    if r is None:
        return i, None
    v, f = surface(r['F'], r['ax'])
    return i, dict(img=render(r['sp'], v, f, motors=motors_of(r['D'])), title=_title_new('{n}', r), sp=gauge_spec(r),
                   rec=dict(q=q, hist=r['hist'], holds=r['holds'], tip=r['tip'], pieces=r['pieces'], under=r['under']))


def _pass_gauge(a):
    """a CPU worker: the seven gauges on a spec (or on T3, the search's all-rounder, when the spec is None)"""
    i, sp = a
    import capability as CP, knobs as K
    CP._init()
    try:
        sp = K.make(K.T3, strict=True) if sp is None else sp
        return i, CP.screen(sp, GAUGE_SEED, GAUGE_TRIES)
    except Exception as e:
        return i, dict(err=f'{type(e).__name__}: {e}'[:200])


def gauge_text(g):
    if g is None:
        return 'gauges running'
    if 'err' in g:
        return 'gauges failed: ' + g['err'][:60]
    return ', '.join(f.format(g[k]) if g.get(k) is not None else f.split(' ')[0] + ' -' for k, f in GAUGE_LINE).replace(', /', '/')


def gauge_pass(seed=None, n=8):
    """n designs made (one GPU worker) and driven through the seven gauges (GAUGE_WORKERS on the CPU) -> out/unibody/
    pass_<seed>.png, .pkl; T3's gauges in the title"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from multiprocessing import Pool
    seed = int(np.random.SeedSequence().entropy % 100000) if seed is None else seed
    os.makedirs(OUT, exist_ok=True); cols = 2; draws = sobol(16 * n, seed); made, gauges, tried = [], {}, 0
    pk, png = os.path.join(OUT, f'pass_{seed}.pkl'), os.path.join(OUT, f'pass_{seed}.png')

    def draw(final=False):
        rows = max(1, math.ceil(len(made) / cols)); fig = plt.figure(figsize=(12, 4.6 * rows)); fig.patch.set_facecolor('white')
        for k, m in enumerate(made):
            ax = fig.add_subplot(rows, cols, k + 1); ax.set_axis_off(); ax.imshow(m['img'])
            ax.set_title(m['title'].replace('{n}', str(k + 1)) + '\n' + gauge_text(gauges.get(k)), fontsize=9, loc='left')
        t3 = gauge_text(gauges.get('T3'))
        fig.suptitle(f'One-piece bodies through the seven gauges (unibody.py pass), Sobol seed {seed}: {len(made)} of {tried} draws made '
                     f'(the 2 kg cap refuses the rest)\nT3, the capability search\'s all-rounder, on the same screen: {t3}', fontsize=11, x=0.02, ha='left')
        plt.tight_layout(rect=(0, 0, 1, 1 - 0.5 / (4.6 * rows))); fig.savefig(png if final else os.path.join(OUT, 'pass_so_far.png'), dpi=80 if not final else 90)
        plt.close(fig)
        pickle.dump(dict(seed=seed, tried=tried, made=[m['rec'] for m in made], gauges=gauges), open(pk, 'wb'))

    with Pool(GAUGE_WORKERS) as cpu:
        pend = [cpu.apply_async(_pass_gauge, (('T3', None),))]
        with Pool(1, maxtasksperchild=1) as gpu:                        # each design in a fresh process: a clean GPU context
            for i, res in gpu.imap(_pass_make, list(enumerate(draws)), chunksize=1):
                tried += 1
                if res is None:
                    continue
                k = len(made); made.append(res); pend.append(cpu.apply_async(_pass_gauge, ((k, res.pop('sp')),)))
                print(f"made {k + 1} (draw {i}): {res['title'].replace(chr(10), ' ')}", flush=True); draw()
                if len(made) >= n:
                    break
            gpu.terminate()
        for p in pend:                                                  # the gauges as they finish
            k, g = p.get(); gauges[k] = g
            print(f'gauges {k if k == "T3" else k + 1}: {gauge_text(g)}', flush=True); draw()
    draw(final=True); print(png, 'seed', seed)


OLD_SEED, OLD_PICKS = 23823, (1, 4, 6, 9, 11)        # body_tree's sheet (trees.png): its designs 2, 5, 7, 10 and 12


def _old_job(a):
    i, q = a
    return i, q, T.sized(q)


def old_designs():
    """body_tree's sheet designs as body_tree.sized() makes them (cached: out/unibody/old_<seed>.pkl)"""
    p = os.path.join(OUT, f'old_{OLD_SEED}.pkl')
    if os.path.exists(p):
        return pickle.load(open(p, 'rb'))['built']
    from multiprocessing import Pool
    qs = []
    for q in T.sobol(16 * 15, OLD_SEED):
        if len(qs) >= 15:
            break
        if T.build(q) is not None:
            qs.append(q)
    with Pool(len(OLD_PICKS)) as pool:
        R = pool.map(_old_job, [(i, qs[i]) for i in OLD_PICKS])
    built = {i: (q, sp) for i, q, sp in R}; pickle.dump(dict(qs=qs, built=built), open(p, 'wb')); return built


def old_landing(sp):
    """a body_tree design's blended shape (blend.py) with the same bay, the same printed walls and the same landing"""
    import blend as BL
    torch, dev = _torch(); A = sp['anchors']; q = sp['q_used']
    F, ax = BL.field(sp, VOX); G = torch.meshgrid(*[torch.as_tensor(a, dtype=torch.float32, device=dev) for a in ax], indexing='ij')
    C = B.parts()[0]; parts = RB.hull(np.vstack([Qp + [q['dxp'] if k.startswith('pack') else 0.0, 0.0, A['dz']] for k, Qp in C.items()]))
    Fc = core_field(sp['hulls'][0], G)[0]
    Ft = torch.minimum(torch.as_tensor(F, device=dev), planes_sdf(G, parts) - BAY_WALL)
    bay = torch.minimum(torch.as_tensor(Fc, dtype=torch.float32, device=dev) + BAY_WALL, planes_sdf(G, parts))
    F = torch.maximum(Ft, -bay).cpu().numpy(); bay = bay.cpu().numpy()
    pt = BL.parts_of(sp); mos = []
    for (x, y), tb in zip(sp['wheels'], pt['tubes']):
        sg = np.sign(y); mos.append(dict(x=x, z=sp['R'], yc=sg * (abs(y) + sp['TW'] / 2 - B.MOTOR['rim_in'] - B.MOTOR['half'][1]), y=y,
                                         y_out=tb['y1'] if sg > 0 else tb['y0']))
    ms, _, _, Fr = mass_of(F, ax); lm = sp.get('limb'); m_tail = lm['m_base'] + lm['m_link'] + lm['m_foot'] if lm else 0.0
    mass = sum(m for _, m, _ in B.parts()[1]) + len(mos) * (B.MOTOR['m'] + sp['m_w']) + ms + m_tail
    L = landing(Fr, ax, mos, bay, mass)
    import drops as DR                                                  # and G1's falls, in body_tree's own sim shapes
    Dr = DR.durability(dict(sp, mass=mass), L['mesh'], L['mass_nodes'], mos, None, FALLS)
    return dict(F=F, ax=ax, L=L, sp=sp, motors=mos, tip=tip_angle(sp), shape_g=ms, mass=mass, drops=Dr)


def compare(shape_seed=5):
    """body_tree's designs against unibody bodies on the same wheels (the same layout knobs, the shape's own knobs
    drawn), the same landing on both -> out/unibody/compare.png"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    os.makedirs(OUT, exist_ok=True); built = old_designs(); picks = [i for i in OLD_PICKS if built.get(i, (0, None))[1] is not None]
    draws = sobol(64, shape_seed); shape_keys = [k for k, *_ in SHAPE]
    ck = os.path.join(OUT, 'compare_rows.pkl'); rows = pickle.load(open(ck, 'rb')) if os.path.exists(ck) else {}   # finished rows survive a crash
    def draw(rows_done):
        fig = plt.figure(figsize=(13, 3.4 * len(picks))); fig.patch.set_facecolor('white')
        for row, i in enumerate(picks):
            for c, (img, t) in enumerate(rows_done.get(i, {}).get('panels', [])):
                ax = fig.add_subplot(len(picks), 3, 3 * row + c + 1); ax.set_axis_off(); ax.imshow(img); ax.set_title(t, fontsize=9, loc='left')
        return fig
    for row, i in enumerate(picks):
        if i in rows:
            continue
        q_old, sp_old = built[i]; o = old_landing(sp_old); qq = sp_old['q_used']; panels = []
        legs = 'a tree' if qq['tree'] > 0.5 else f"{int(qq['members'])} leg{'s' if int(qq['members']) > 1 else ''} a wheel"
        panels.append((stress_picture(o['sp'], o['F'], o['ax'], o['L'], motors=o['motors']),
                       f"{i + 1}, body_tree ({legs}): landings {o['L']['peak']:.0f}, falls {o['drops']['worst']:.0f} MPa "
                       f"({o['drops']['over']} of {o['drops']['n']} over, {o['drops']['broken']} past {SIGMA_ULT:.0f})\n"
                       f"shape {o['shape_g']:.0f} g, robot {o['mass'] / 1000:.1f} kg, tips at {o['tip']:.0f} deg"))
        r = None
        for k in range(len(draws)):                                    # the first shape draw that can be made on these wheels
            qn = dict({kk: v for kk, v in qq.items() if kk in KEYS}, **{kk: draws[(row * 7 + k) % len(draws)][kk] for kk in shape_keys})
            r = make(qn, log=lambda *_: None, falls=FALLS)
            if r is not None:
                break
        f0 = r['first']; h0, h = r['hist'][0], r['hist'][-1]
        panels.append((stress_picture(f0['sp'], f0['F'], r['ax'], f0['L'], motors=motors_of(r['D'])),
                       f"unibody, as drawn: landings {h0['wheel_peak']:.0f}, falls {h0['drop_peak']:.0f} MPa ({h0['over']} of {h0['falls']} over, {h0['broken']} past)\n"
                       f"shape {f0['sp']['shape_g']:.0f} g, robot {f0['sp']['mass'] / 1000:.1f} kg, tips at {tip_angle(f0['sp']):.0f} deg"))
        panels.append((stress_picture(r['sp'], r['F'], r['ax'], r['L'], motors=motors_of(r['D'])),
                       f"unibody, {len(r['hist']) - 1} rounds: landings {h['wheel_peak']:.0f}, falls {h['drop_peak']:.0f} MPa ({h['over']} of {h['falls']} over, {h['broken']} past)\n"
                       f"shape {r['sp']['shape_g']:.0f} g, robot {r['sp']['mass'] / 1000:.1f} kg, tips at {r['tip']:.0f} deg"))
        rows[i] = dict(panels=panels, rec=dict(design=i + 1, old_drops={k: v for k, v in o['drops'].items() if k not in ('stress', 'keep', 'cases')}, old_peak=o['L']['peak'],
                                                old_collar=o['L']['mount'], old_shape_g=o['shape_g'], old_mass=o['mass'], old_tip=o['tip'], old_case=o['L']['case'],
                                                new_hist=r['hist'], new_tip=r['tip'], new_pieces=r['pieces'], q_new=qn, new_mass=r['sp']['mass'], new_shape_g=r['sp']['shape_g']))
        pickle.dump(rows, open(ck, 'wb'))
        f = draw(rows); f.savefig(os.path.join(OUT, 'compare_so_far.png'), dpi=70); plt.close(f)
        print(i + 1, 'old landings', round(o['L']['peak'], 1), 'falls', round(o['drops']['worst'], 1), o['drops']['over'], 'over', o['drops']['broken'], 'broken',
              round(o['shape_g']), 'g | new', [(round(x['wheel_peak'], 1), round(x['drop_peak'], 1), x['over']) for x in r['hist']], h['broken'], 'broken',
              round(r['sp']['shape_g']), 'g', flush=True)
    fig = draw(rows); rec = [rows[i]['rec'] for i in picks if i in rows]
    fig.suptitle(f"The same tests on both: each wheel landed ({LAND}x a 300 mm drop into a 30 N/mm tyre, six ways) and {FALLS} of G1's falls; "
                 f"printed walls {FE.WALL} mm round {FE.INFILL_M:.0%} infill\ngreen unloaded, yellow at the allowed {ALLOW:.1f} MPa, red at PLA's "
                 f"{SIGMA_ULT:.0f} across its layers (the colours: the wheel landings). Same wheels, same parts bay; left body_tree's legs, right one field", fontsize=11, x=0.02, ha='left')
    plt.tight_layout(rect=(0, 0, 1, 0.965)); p = os.path.join(OUT, 'compare.png'); plt.savefig(p, dpi=85)
    pickle.dump(rec, open(os.path.join(OUT, 'compare.pkl'), 'wb')); print(p)


# ---------- the drawn shape's tests ----------
FLAT_MM, FLAT_CTRL_MM = 0.1, 0.3           # the core's mesh within FLAT_MM of its surface (95 %); the control past FLAT_CTRL_MM
                                            # (seed 1030's first three: exact 0.00-0.01, the voxel field 0.51-0.86)


def check(seed=1030, n=3):
    """the drawn shape's two tests, each with its control (2026-10-30, after Zach's "strange bumpyness" was found to be
    the mesher's), on n drawn designs of the Sobol seed (no growth: seconds each):
      flat   the body's core meshes onto its own surface, 95 % of vertices within FLAT_MM; control: the voxel field it
             replaced (_core_voxel) must read past FLAT_CTRL_MM
      folds  surface()'s mesh has no face cutting through another, no open or non-manifold edge, and few enough faces
             for render(); control: the plain decimation it replaced must fold on at least one design
      section  section_d (growth's weight) reads known shapes, a hollow one as its outline; control: the hollow left open
    Returns the failures (an empty list when all hold)"""
    import pymeshlab as ml
    from skimage import measure
    torch, dev = _torch(); bad = []; folded = 0; done = 0
    # section_d on known shapes (4 mm voxels): a 20 mm rod off an 80 mm block, and an 80 mm box with an 8 mm wall, which
    # must read as the box (control: its hollow left open reads the wall). SECTION_R's 1.4x steps read ~20 % low
    x = (np.arange(60) + 0.5) * FEM_H; X, Y, Z = np.meshgrid(x, x, x, indexing='ij')
    cube = lambda c, a: (np.abs(X - c[0]) <= a) & (np.abs(Y - c[1]) <= a) & (np.abs(Z - c[2]) <= a)
    rod = (X > 100) & (X < 200) & ((Y - 120) ** 2 + (Z - 120) ** 2 <= 100); d = section_d(dict(solid=cube((60, 120, 120), 40) | rod))
    hollow = cube((120,) * 3, 40) & ~cube((120,) * 3, 32)
    sec = dict(rod=float(np.median(d[rod & (X > 140) & (X < 180)])), block=float(d[15, 30, 30]),
               box=float(np.median(section_d(dict(solid=hollow))[hollow])), wall=float(np.median(section_d(dict(solid=hollow), fill=False)[hollow])))
    print(f"section: rod {sec['rod']:.0f} mm (20), block {sec['block']:.0f} (80), hollow box {sec['box']:.0f} (80; control, open: {sec['wall']:.0f})")
    if not (12 <= sec['rod'] <= 24 and sec['block'] >= 50 and sec['box'] >= 50):
        bad.append(f'section_d misreads its known shapes: {sec}')
    if sec['wall'] >= 20:
        bad.append(f"CONTROL: the open box reads {sec['wall']:.0f} mm, so the filled one isn't shown to matter")
    for j, q in enumerate(sobol(16 * n, seed)):
        D = design(q)
        if D is None:
            continue
        ax = grid(D); Un, Fc, _ = union(D, ax); F, _ = cut(D, Un, ax, Fc)
        if D.get('loose'):
            continue
        done += 1; rnd = D['round_used']
        G = torch.meshgrid(*[torch.as_tensor(a, dtype=torch.float32, device=dev) for a in ax], indexing='ij')
        err = {}
        for name, field in (('exact', Fc), ('voxel', _core_voxel(D['core'], G, rnd))):
            v, f, *_ = measure.marching_cubes(field, 0.0, spacing=(VOX,) * 3); v = v + np.array([a[0] for a in ax])
            Pv = [torch.as_tensor(v[:, i], dtype=torch.float32, device=dev) for i in range(3)]
            err[name] = float(np.percentile(np.abs(core_field(D['core'], Pv, rnd)[0]), 95))
        v, f = surface(F, ax); ms = ml.MeshSet(); ms.add_mesh(ml.Mesh(v, f)); nf = folds(ms); t = ms.get_topological_measures()
        holes, nonman = t['boundary_edges'], t['non_two_manifold_edges'] + t['non_two_manifold_vertices']
        raw = ml.MeshSet(); vr, fr, *_ = measure.marching_cubes(F, 0.0, spacing=(VOX,) * 3)   # surface() as it was
        raw.add_mesh(ml.Mesh(vr + np.array([a[0] for a in ax]), fr)); raw.meshing_merge_close_vertices(threshold=ml.PureValue(1e-4))
        raw.meshing_decimation_quadric_edge_collapse(targetfacenum=150000, preservenormal=True); nc = folds(raw)
        folded += bool(nc)
        print(f'design {done} (draw {j}): core off its surface {err["exact"]:.2f} mm (control {err["voxel"]:.2f}); '
              f'folds {nf} (control {nc}), open edges {holes}, non-manifold {nonman}, {len(f)} faces; round {rnd:.1f} mm', flush=True)
        if err['exact'] > FLAT_MM:
            bad.append(f'design {done}: the core meshes {err["exact"]:.2f} mm off its surface')
        if err['voxel'] <= FLAT_CTRL_MM:
            bad.append(f'design {done}: CONTROL READS FLAT ({err["voxel"]:.2f} mm): the flatness test is not measuring')
        if nf != 0 or holes or nonman or len(f) > 200000:
            bad.append(f'design {done}: the mesh has {nf} folds, {holes} open edges, {nonman} non-manifold, {len(f)} faces '
                       '(MuJoCo takes 200,000)')
        if done >= n:
            break
    if not folded:
        bad.append('CONTROL: the plain decimation folded no design here, so the folds test is not shown to measure')
    print('\n' + ('all hold, and every control fails' if not bad else '\n'.join(bad)))
    return bad


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'sheet':
        sheet(int(sys.argv[2]) if len(sys.argv) > 2 else None, resume='resume' in sys.argv[3:])
    elif cmd == 'check':
        sys.exit(1 if check(int(sys.argv[2]) if len(sys.argv) > 2 else 1030) else 0)
    elif cmd == 'compare':
        compare()
    elif cmd == 'pass':
        gauge_pass(int(sys.argv[2]) if len(sys.argv) > 2 else None, int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    elif cmd == 'section':
        seed = int(sys.argv[2]) if len(sys.argv) > 2 else 23823; k = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        pk = os.path.join(OUT, f'sheet_{seed}.pkl')                    # the sheet's own design k when it has been drawn
        q = pickle.load(open(pk, 'rb'))[k - 1]['q'] if os.path.exists(pk) else sobol(8 * 15, seed)[k - 1]
        r = make(q); os.makedirs(OUT, exist_ok=True)
        if r is None:
            print('design', k, 'could not be made')
        else:
            section(r, os.path.join(OUT, 'section.png'), f'Sheet design {k} (seed {seed}): a cut through its first left pod, the motor drawn in (* guessed)')
            print(os.path.join(OUT, 'section.png'))
    else:
        print(__doc__)
