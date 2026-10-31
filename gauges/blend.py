"""The generator's one shape (2026-10-28). Zach, on the braced legs: "your last piece here is figuring out how to either
blend or generate it into one shape with the motor attached properly", then "were not printing here were updating the
generator".

A body_tree design is a body hull, leg segments (capsules), motor tubes and a tail boss: separate solids that only
touch. Here they become one: each is a signed distance field, joined by a smooth union (a polynomial smooth minimum of
radius BLEND*, so every joint gets a fillet: the legs flow out of the body and into the tubes), then cut sharp so the
blend can't fill them: each motor's bore (the motor sits in its tube) and each wheel's room. The surface comes out by
marching cubes. The sims keep the parts as they were (convex pieces and capsules): the blend only adds fillets.
"""
import os, sys
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
from scipy.spatial import ConvexHull
import body as B, body_tree as T, robots as RB

BLEND = 8.0                       # mm: the smooth union's radius (the fillets)*
WHEEL_GAP = 5.0                   # mm round each tyre
MOTOR_R, MOTOR_HL = B.MOTOR['half'][0], B.MOTOR['half'][1]


def smin(a, b, k):
    """polynomial smooth minimum: min(a, b) with a fillet of radius about k where they meet"""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def parts_of(sp):
    """the design's solids, in mm, the robot's frame: body (convex), segments, tubes (axis along y), motors, the boss"""
    nt = len(sp['wheels']); tubes, motors = [], []
    for w, (x, y) in enumerate(sp['wheels']):
        P = np.asarray(sp['hulls'][1 + w]); ys = P[:, 1]; sg = np.sign(y)
        tubes.append(dict(x=x, z=sp['R'], y0=float(ys.min()), y1=float(ys.max())))
        yc = sg * (abs(y) + sp['TW'] / 2 - B.MOTOR['rim_in'] - MOTOR_HL); motors.append(dict(x=x, z=sp['R'], y0=yc - MOTOR_HL, y1=yc + MOTOR_HL))
    return dict(body=np.asarray(sp['hulls'][0]), extra=[np.asarray(h) for h in sp['hulls'][1 + nt:]], caps=sp['struts'], tubes=tubes, motors=motors)


def _planes(P):
    """a convex hull's distinct faces (n, d): inside where n.p + d <= 0"""
    E = ConvexHull(P).equations; return E[np.unique(np.round(E, 4), axis=0, return_index=True)[1]]


def field(sp, vox=2.0):
    """the signed distance (mm, negative inside) on a grid over the design: (F, axes)"""
    pt = parts_of(sp); R, TW = sp['R'], sp['TW']
    P = np.vstack([pt['body']] + pt['extra'] + [np.array(c[:2]) for c in pt['caps']] +
                  [np.array([[t['x'], t['y0'], t['z']], [t['x'], t['y1'], t['z']]]) for t in pt['tubes']])
    lo, hi = P.min(0) - 40.0, P.max(0) + 40.0; lo[2] = max(lo[2], -5.0)
    ax = [np.arange(lo[i], hi[i] + vox, vox) for i in range(3)]; F = np.full([len(a) for a in ax], 1e3, np.float32)
    def region(blo, bhi):
        """index slices and coordinates of the grid inside a box"""
        sl, co = [], []
        for i in range(3):
            a = np.searchsorted(ax[i], blo[i]); b = np.searchsorted(ax[i], bhi[i], side='right'); sl.append(slice(a, b)); co.append(ax[i][a:b])
        if any(len(c) == 0 for c in co):
            return None, (None, None, None)
        return tuple(sl), np.meshgrid(*co, indexing='ij')
    def put(d, sl, op):
        F[sl] = op(F[sl], d.astype(np.float32))
    def add_convex(Pc):
        sl, (X, Y, Z) = region(Pc.min(0) - BLEND - 2 * vox, Pc.max(0) + BLEND + 2 * vox)
        if sl is None:
            return
        d = np.full(X.shape, -1e3)
        for n0, n1, n2, d0 in _planes(Pc):
            d = np.maximum(d, n0 * X + n1 * Y + n2 * Z + d0)
        put(d, sl, lambda a, b: smin(a, b, BLEND))
    for Pc in [pt['body']] + pt['extra']:
        add_convex(Pc)
    for p0, p1, r in pt['caps']:                                        # the legs: capsules
        p0, p1 = np.asarray(p0), np.asarray(p1); sl, (X, Y, Z) = region(np.minimum(p0, p1) - r - BLEND, np.maximum(p0, p1) + r + BLEND)
        if sl is None:
            continue
        e = p1 - p0; t = np.clip(((X - p0[0]) * e[0] + (Y - p0[1]) * e[1] + (Z - p0[2]) * e[2]) / max(e @ e, 1e-9), 0, 1)
        put(np.sqrt((X - p0[0] - t * e[0]) ** 2 + (Y - p0[1] - t * e[1]) ** 2 + (Z - p0[2] - t * e[2]) ** 2) - r, sl, lambda a, b: smin(a, b, BLEND))
    TR = T.TUBE_R
    for tb in pt['tubes']:                                              # the motor tubes
        sl, (X, Y, Z) = region((tb['x'] - TR - BLEND, tb['y0'] - 2, tb['z'] - TR - BLEND), (tb['x'] + TR + BLEND, tb['y1'] + 2, tb['z'] + TR + BLEND))
        if sl is None:
            continue
        put(np.maximum(np.sqrt((X - tb['x']) ** 2 + (Z - tb['z']) ** 2) - TR, np.maximum(tb['y0'] - Y, Y - tb['y1'])), sl, lambda a, b: smin(a, b, BLEND))
    for mo, tb in zip(pt['motors'], pt['tubes']):                       # cut sharp: each motor's bore, through its tube
        sl, (X, Y, Z) = region((tb['x'] - TR, min(tb['y0'], mo['y0']) - 10, tb['z'] - TR), (tb['x'] + TR, max(tb['y1'], mo['y1']) + 10, tb['z'] + TR))
        if sl is not None:
            put(-(np.sqrt((X - tb['x']) ** 2 + (Z - tb['z']) ** 2) - MOTOR_R), sl, np.maximum)
    for x, y in sp['wheels']:                                           # and each wheel's room
        sl, (X, Y, Z) = region((x - R - WHEEL_GAP, y - TW / 2 - WHEEL_GAP, -5), (x + R + WHEEL_GAP, y + TW / 2 + WHEEL_GAP, 2 * R + WHEEL_GAP))
        if sl is not None:
            put(-np.maximum(np.sqrt((X - x) ** 2 + (Z - R) ** 2) - (R + WHEEL_GAP), np.abs(Y - y) - (TW / 2 + WHEEL_GAP)), sl, np.maximum)
    return F, ax


def mesh(F, ax):
    """the zero surface as (vertices mm, triangles)"""
    from skimage import measure
    v, f, *_ = measure.marching_cubes(F, 0.0, spacing=tuple(float(a[1] - a[0]) for a in ax))
    return v + np.array([a[0] for a in ax]), f


def write_stl(path, v, f):
    tri = v[f]; n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(f), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]); rec['n'] = n; rec['v'] = tri
    with open(path, 'wb') as fh:
        fh.write(b'blend.py'.ljust(80, b' ')); fh.write(np.uint32(len(f)).tobytes()); fh.write(rec.tobytes())


def shape(sp, path, vox=2.0):
    """the design's one shape, written to path (STL, at most 180,000 triangles: MuJoCo reads 200,000): triangles, bodies"""
    F, ax = field(sp, vox); v, f = mesh(F, ax); write_stl(path, v, f)
    import pymeshlab as ml
    ms = ml.MeshSet(); ms.load_new_mesh(path); ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
    if ms.current_mesh().face_number() > 180000:
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=180000, preservenormal=True)
    ms.save_current_mesh(path, binary=True)
    n = ms.current_mesh().face_number(); ms.generate_splitting_by_connected_components(); bodies = ms.mesh_number() - 1
    return n, bodies


def render(sp, stl, w=420, h=300, azim=145.0, elev=-20.0):
    """the design's shape (its STL) with its motors in their tubes, its wheels and its tail, rendered by MuJoCo"""
    import mujoco
    pt = parts_of(sp); S = 1e-3
    geoms = ['<geom type="mesh" mesh="shape" rgba=".86 .62 .48 1"/>']
    for mo in pt['motors']:
        geoms.append(f'<geom type="cylinder" size="{MOTOR_R * S:.4f} {MOTOR_HL * S:.4f}" pos="{mo["x"] * S:.4f} {0.5 * (mo["y0"] + mo["y1"]) * S:.4f} {mo["z"] * S:.4f}" euler="90 0 0" rgba=".62 .64 .68 1"/>')
    for x, y in sp['wheels']:
        geoms.append(f'<geom type="cylinder" size="{sp["R"] * S:.4f} {sp["TW"] / 2 * S:.4f}" pos="{x * S:.4f} {y * S:.4f} {sp["R"] * S:.4f}" euler="90 0 0" rgba=".13 .13 .14 1"/>')
    lm = sp.get('limb')
    if lm:
        P = RB.limb_points(lm, 0.0, lm['th_stow']); b0, b1 = P[0] * S, P[7] * S
        geoms.append(f'<geom type="capsule" fromto="{b0[0]:.4f} {b0[1]:.4f} {b0[2]:.4f} {b1[0]:.4f} {b1[1]:.4f} {b1[2]:.4f}" size="{RB.LINK_R * S:.4f}" rgba=".1 .5 .4 1"/>')
    xml = f"""<mujoco><visual><global offwidth="{w}" offheight="{h}"/><quality shadowsize="2048"/><headlight ambient=".35 .35 .35"/></visual>
      <default><geom contype="0" conaffinity="0"/></default>
      <asset><mesh name="shape" file="shape.stl" scale="{S} {S} {S}"/>
      <texture name="chk" type="2d" builtin="checker" rgb1=".93 .93 .91" rgb2=".86 .86 .84" width="256" height="256"/><material name="floor" texture="chk" texrepeat="12 12"/>
      <texture name="sky" type="skybox" builtin="gradient" rgb1=".97 .97 .96" rgb2=".85 .86 .84" width="64" height="64"/></asset>
      <worldbody><light pos=".4 -.6 1.5" dir="-.2 .4 -1" diffuse=".7 .7 .66" castshadow="true"/><geom type="plane" size="3 3 .1" material="floor"/>
      {''.join(geoms)}</worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml, {'shape.stl': open(stl, 'rb').read()}); d = mujoco.MjData(m); mujoco.mj_forward(m, d)
    E = RB.extremes(sp); lo, hi = E.min(0), E.max(0)
    cam = mujoco.MjvCamera(); cam.lookat[:] = [(lo[0] + hi[0]) / 2 * S, 0.0, 0.35 * (hi[2] - lo[2]) * S]
    cam.distance = 1.9 * max(hi - lo) * S; cam.azimuth, cam.elevation = azim, elev
    with mujoco.Renderer(m, h, w) as r:
        r.update_scene(d, cam); return r.render()
