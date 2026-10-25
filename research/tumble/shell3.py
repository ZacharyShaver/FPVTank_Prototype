"""EXPLORATORY (2026-10-25): a wider shell family for the self-righting search, a static screen, and the drop
simulation of a printed body of it.

The sweep's family (tumble.shell_points: top, round, half-width, at the tub's length) peaked at P(upright) 0.65-0.68
(PROTOCOL.md post hoc 6 and 9). Its flat top and flat walls are rest states of their own. This family is a
superellipsoid that can round over in every direction, so a body can have one rest state (upright) like a weeble:

  xc        the shell's centre along X
  af, ar    its reach forward and back from xc
  b         its half-width
  zc        the height of its widest section
  cu        the top's height above zc (top = zc + cu)
  cd        the lower half's depth below zc; the shell is cut at the tub's underside (Z0 7.4) where it reaches it
  p         the plan's exponent: 2 an ellipse, 4 a rounded rectangle
  qu, qd    the upper and lower profiles' exponents: 1 a cone, 2 an ellipse, 4 boxy

Inside it is the sweep's robot: the four 110 mm wheels, the head's ball and the tub. The body is the convex hull of
all of it. Frame and units are tumble.py's: mm and g, X forward, Z up, the wheels' bottoms at Z -25.

    python research/tumble/shell3.py     # the static screen on E1-E3 (its control) and on a few weebles
"""
import os, sys, json
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import tumble as T
import scale_model as S

KEYS = ['xc', 'af', 'ar', 'b', 'zc', 'cu', 'cd', 'p', 'qu', 'qd']
LO = np.array([-40.0, 120.0, 120.0, 100.0, -10.0, 40.0, 20.0, 1.6, 1.0, 1.0])
HI = np.array([60.0, 320.0, 320.0, 300.0, 160.0, 320.0, 250.0, 5.0, 4.0, 4.0])
FLOOR = T.ZA - 55.0                       # the wheels' bottoms, Z -25: the floor when upright
GRIP_MAX = 85.0                           # the drop stand's jaws pass a grip of 87 mm (drop_stand.py); 2 mm spare
SCALE_MAX = 0.25                          # E1-E3's scale
WALL = 1.5                                # pocket wall, mm at print scale


def shell_points(q, n=72, k=14):
    """points on the shell, base ring at Z0 up to the apex"""
    th = np.linspace(0, 2 * np.pi, n, endpoint=False); c, s = np.cos(th), np.sin(th)
    e = 2.0 / q['p']; ux = np.sign(c) * np.abs(c) ** e; uy = np.sign(s) * np.abs(s) ** e
    ax = np.where(c >= 0, q['af'], q['ar'])
    phi = np.linspace(0, np.pi / 2, k)
    lev = [(q['zc'] + q['cu'] * np.sin(f) ** (2 / q['qu']), np.cos(f) ** (2 / q['qu'])) for f in phi]
    lev += [(q['zc'] - q['cd'] * np.sin(f) ** (2 / q['qd']), np.cos(f) ** (2 / q['qd'])) for f in phi[1:]]
    lev = [(z, r) for z, r in lev if z >= T.Z0]
    zc, Z0 = q['zc'], T.Z0
    if zc - q['cd'] < Z0:                  # the cut: the section at Z0
        if zc >= Z0:
            t = (zc - Z0) / q['cd']; lev.append((Z0, (1 - t ** q['qd']) ** (1 / q['qd'])))
        elif zc + q['cu'] > Z0:
            t = (Z0 - zc) / q['cu']; lev.append((Z0, (1 - t ** q['qu']) ** (1 / q['qu'])))
    pts = [np.c_[q['xc'] + ax * r * ux, q['b'] * r * uy, np.full(n, z)] for z, r in lev if r > 1e-6]
    pts.append([[q['xc'], 0.0, zc + q['cu']]])
    return np.vstack(pts)


def robot_points():
    """the robot the shell has to hold: wheels, the head's ball, the tub (tumble.py's geometry)"""
    pts = [T.shell_points(66.0, 0.08)]
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for x in T.AXLES:
        for y in (T.TRACK, -T.TRACK):
            for dy in (-T.TW / 2, T.TW / 2):
                pts.append(np.c_[x + 55.0 * np.cos(a), np.full_like(a, y + dy), T.ZA + 55.0 * np.sin(a)])
    bx, by, bz, br = T.HEAD['ball']
    i = np.arange(300) + 0.5; ph = np.arccos(1 - 2 * i / 300); th = np.pi * (1 + 5 ** 0.5) * i
    pts.append(np.c_[bx + br * np.cos(th) * np.sin(ph), by + br * np.sin(th) * np.sin(ph), bz + br * np.cos(ph)])
    return np.vstack(pts)


ROBOT = robot_points()


def body(q, n=72, k=14):
    """the convex hull's vertices, full scale, in tumble's frame"""
    P = np.vstack([shell_points(q, n, k), ROBOT]); h = ConvexHull(P)
    return P[h.vertices]


def as_dict(x):
    return {k: float(v) for k, v in zip(KEYS, x)}


# ---------- mass ----------
def solid_props(P):
    """volume, centroid and second-moment inertia (about the centroid, per unit density) of a convex hull; and its
    surface's area, centroid and inertia per unit area"""
    h = ConvexHull(P); o = P[h.vertices].mean(0); tri = P[h.simplices]
    a, b, c = tri[:, 0] - o, tri[:, 1] - o, tri[:, 2] - o
    v = np.abs(np.einsum('ij,ij->i', a, np.cross(b, c))) / 6; V = v.sum()
    cv = (v[:, None] * (a + b + c) / 4).sum(0) / V + o
    Q = tri - cv; Ssum = Q.sum(1)
    S2 = np.einsum('n,nij->ij', v, (np.einsum('nki,nkj->nij', Q, Q) + np.einsum('ni,nj->nij', Ssum, Ssum)) / 20)
    Iv = np.trace(S2) * np.eye(3) - S2
    ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1); A = ar.sum()
    g = tri.mean(1); ca = (ar[:, None] * g).sum(0) / A
    # a triangle's second moment about its centroid: (sum of e_k e_k^T)/12 over vertex offsets, plus its centroid's
    d = tri - g[:, None, :]; Sa = np.einsum('n,nij->ij', ar, np.einsum('nki,nkj->nij', d, d) / 12)
    gg = g - ca; Sa = Sa + np.einsum('n,ni,nj->ij', ar, gg, gg)
    Ia = np.trace(Sa) * np.eye(3) - Sa
    return dict(V=V, cv=cv, Iv=Iv, A=A, ca=ca, Ia=Ia, tri=tri, ar=ar)


# grams of PLA per mm2 of surface and per mm3 of volume, fitted to E1-E3's sliced bodies (posthoc_print_mass: 37.86,
# 48.06, 67.73 g at 2 walls, 3 top/bottom layers, 10% infill); see fit_pla()
PLA_A, PLA_V = None, None


def fit_pla():
    global PLA_A, PLA_V
    G = {'E1_tub': 37.86, 'E2_dome': 48.06, 'E3_tall': 67.73}
    X, y = [], []
    for n, g in G.items():
        info = json.load(open(os.path.join(ROOT, 'models', n + '.json'))); P = S.hull_points(info['params'], info['scale'])
        sp = solid_props(P); X.append([sp['A'], sp['V']]); y.append(g)
    (PLA_A, PLA_V), *_ = np.linalg.lstsq(np.array(X), np.array(y), rcond=None)
    return PLA_A, PLA_V, np.array(X) @ [PLA_A, PLA_V] - y


fit_pla()


def spacer_g(length):
    """the printed spacer's grams: E1 11.1 mm 2.20 g, E3 24.4 mm 3.92 g (G-code)"""
    return 0.76 + 0.1293 * length


def print_body(q, scale=None, coins=12):
    """the printed test body: hull points at print scale (base on Z 0), its pocket, and the scale. The scale is the
    largest up to 0.25 at which every start's grip fits the drop stand."""
    P = body(q); P = P - [0, 0, P[:, 2].min()]
    if scale is None:
        g = max(grip_widths(P).values()); scale = min(SCALE_MAX, GRIP_MAX / g)
    P = P * scale
    E = ConvexHull(P).equations
    x = (T.AXLES[0] + T.AXLES[1]) / 2 * scale                 # the pocket opens in the middle of the wheels' base
    stack = coins * S.COIN_T; H = P[:, 2].max()
    a = np.linspace(0, 2 * np.pi, 24, endpoint=False); R = S.POCKET_R + WALL
    def fits(z1):
        Z = np.linspace(0.0, z1, 12)
        C = np.vstack([np.c_[x + R * np.cos(a), R * np.sin(a), np.full(24, z)] for z in Z])
        return (C @ E[:, :3].T + E[:, 3]).max() <= 0 and (np.array([x, 0, z1 + WALL]) @ E[:, :3].T + E[:, 3]).max() <= 0
    depth = round(0.78 * H, 1)
    while depth > stack + 2 and not fits(depth):
        depth -= 0.5
    ok = fits(depth) and depth >= stack + 2
    pk = dict(name='pocket', x=float(x), y=0.0, z0=0.0, depth=float(depth), coins=coins,
              spacer=round(depth - stack - 0.4, 1), fits=bool(ok))
    return P, pk, scale


def grip_widths(P):
    from scipy.spatial.transform import Rotation as Rot
    out = {}
    for att, (r, p) in S.ATTITUDES.items():
        e = np.ptp(P @ Rot.from_euler('xyz', [r, p, 0], degrees=True).as_matrix().T, 0)
        out[att] = float(min(e[0], e[1]))
    return out


def print_layout(P, pk, high=False, grams=None):
    """(total g, CoM, inertia g mm^2) of the printed body: PLA as walls (per area) plus infill (per volume), the
    spacer and the coins in the pocket. `grams` (a slice's) rescales the PLA."""
    sp = solid_props(P)
    mA, mV = PLA_A * sp['A'], PLA_V * sp['V']
    if grams is not None:
        f = (grams - spacer_g(pk['spacer'])) / (mA + mV); mA, mV = mA * f, mV * f
    m_sp = spacer_g(pk['spacer']); n = pk['coins']; m_c = n * S.COIN_G; stack = n * S.COIN_T
    zc = (pk['depth'] - stack / 2) if high else stack / 2
    zs = (pk['spacer'] / 2) if high else (stack + pk['spacer'] / 2)
    cc, cs = np.array([pk['x'], 0, zc]), np.array([pk['x'], 0, zs])
    parts = [(mA, sp['ca'], sp['Ia'] * mA / sp['A']), (mV, sp['cv'], sp['Iv'] * mV / sp['V']),
             (m_c, cc, np.zeros((3, 3))), (m_sp, cs, np.zeros((3, 3)))]
    M = sum(m for m, _, _ in parts); com = sum(m * c for m, c, _ in parts) / M
    I = np.zeros((3, 3))
    for m, c, Ic in parts:
        d = c - com; I += Ic + m * (d @ d * np.eye(3) - np.outer(d, d))
    return M, com, I


def robot_layout(q, dz=0.0, cover=1.5):
    """(total g, CoM, inertia) of the full robot under the shell: tumble.mass_model's parts, the tub's 600 g where it
    was, and the shell's area beyond the tub's as a `cover` mm PLA cover at that area's centroid ('cover' mode)"""
    def open_surface(Q):
        h = ConvexHull(Q); tri = Q[h.simplices]
        ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        keep = ~np.all(tri[:, :, 2] < T.Z0 + 0.5, axis=1)
        return tri[keep], ar[keep]
    t0, a0 = open_surface(T.shell_points(66.0, 0.08)); t1, a1 = open_surface(shell_points(q))
    A0, A1 = a0.sum(), a1.sum(); c0 = (a0[:, None] * t0.mean(1)).sum(0) / A0
    p = T.norm(dict(dz=dz)); items = T.mass_model(dict(p, top=66.0, round=0.08, width=T.R0))
    items = [it for it in items if it[0] != 'shell'] + [('tub', 600.0, (-20.0, 0.0, 50.0), (170, 65, 30))]
    M, c, I = T.inertia(items)
    extra = A1 - A0
    if extra > 1.0:
        m_cov = 1.24e-3 * cover * extra
        g1 = t1.mean(1); w = np.r_[a1, -a0] * 1.24e-3 * cover; r = np.vstack([g1, t0.mean(1)])
        Mt = M + m_cov; ct = (M * c + (w[:, None] * r).sum(0)) / Mt
        d = c - ct; It = I + M * (d @ d * np.eye(3) - np.outer(d, d))
        dr = r - ct; It += np.einsum('n,nij->ij', w, np.einsum('n,ij->nij', (dr ** 2).sum(1), np.eye(3)) - np.einsum('ni,nj->nij', dr, dr))
        return Mt, ct, It, m_cov
    return M, c, I, 0.0


# ---------- the static screen ----------
def _sphere(N=3000):
    i = np.arange(N) + 0.5; ph = np.arccos(1 - 2 * i / N); th = np.pi * (1 + 5 ** 0.5) * i
    D = np.c_[np.cos(th) * np.sin(ph), np.sin(th) * np.sin(ph), np.cos(ph)]
    h = ConvexHull(D); nb = [set() for _ in range(N)]
    for a, b, c in h.simplices:
        nb[a] |= {b, c}; nb[b] |= {a, c}; nb[c] |= {a, b}
    return D, [np.array(sorted(s)) for s in nb]


SPH, NB = _sphere()
_W = max(len(n) for n in NB)
NBP = np.array([np.r_[n, np.full(_W - len(n), i)] for i, n in enumerate(NB)])          # padded with self
NBA = np.arccos(np.clip(np.einsum('ij,ikj->ik', SPH, SPH[NBP]), -1, 1)); NBA[NBA < 1e-9] = np.inf
LABEL ={(2, 1): 'upright', (2, -1): 'inverted', (1, 1): 'right side', (1, -1): 'left side', (0, 1): 'nose down', (0, -1): 'nose up'}


def label(n):
    """the rest state when the outward normal n points down: the body axis nearest world up is -n (T.classify)"""
    u = -n; i = int(np.argmax(np.abs(u))); return LABEL[(i, int(np.sign(u[i])))]


_SPHT = np.ascontiguousarray(SPH.T); _BLK = 250; _BUF = {}


def support(P, G):
    """h(n) = max_v (v - G).n over the 3000 directions, in blocks: one (vertices x 3000) array per call page-faults
    ~19 MB, and 30 workers doing that ran no faster than 8 (2026-10-25, 60 designs/s at 8, 16 and 30)"""
    n = len(P); buf = _BUF.get(n)
    if buf is None:
        buf = _BUF[n] = np.empty((n, _BLK))
    H = np.empty(SPH.shape[0])
    for a in range(0, SPH.shape[0], _BLK):
        b = min(a + _BLK, SPH.shape[0]); out = buf[:, :b - a]
        np.matmul(P, _SPHT[:, a:b], out=out); out.max(0, out=H[a:b])
    return H - G @ _SPHT


def static(P, G, eps=None, H=None):
    """rest states by the potential h(n) = max_v (v - G).n, the CoM's height when the body lies on the face whose
    outward normal is n, over 3000 directions. Minima are rest states; a minimum's barrier is how far its CoM must
    rise to roll out (0-dim persistence). Minima with barrier under eps (default 0.5% of the body's size) are folded
    into the basin they spill into. Returns the share of directions draining to each rest state, and the states."""
    if H is None:
        H = support(P, G)
    if eps is None:
        eps = 0.005 * np.ptp(P, 0).max()
    order = np.argsort(H); par = -np.ones(len(H), int); mn = np.zeros(len(H), int); size = np.zeros(len(H), int)
    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    dead = {}                                                   # min index -> barrier, for minima that merged
    for i in order:
        par[i] = i; mn[i] = i; size[i] = 1
        for j in NB[i]:
            if par[j] < 0:
                continue
            a, b = find(i), find(j)
            if a == b:
                continue
            hi, lo = (a, b) if H[mn[a]] > H[mn[b]] else (b, a)  # the basin with the higher minimum dies here
            if mn[hi] != i:
                dead[mn[hi]] = (H[i] - H[mn[hi]], size[hi])
            par[hi] = lo; size[lo] += size[hi]
    root = find(order[0]); barrier = dict((k, v[0]) for k, v in dead.items()); barrier[mn[root]] = np.inf
    keep = {m for m, b in barrier.items() if b >= eps}
    # second pass: merge only where one side's minimum is insignificant
    par[:] = -1
    for i in order:
        par[i] = i; mn[i] = i
        for j in NB[i]:
            if par[j] < 0:
                continue
            a, b = find(i), find(j)
            if a == b:
                continue
            ka, kb = mn[a] in keep, mn[b] in keep
            if ka and kb:
                continue
            hi, lo = (a, b) if (not ka and kb) or (ka == kb and H[mn[a]] > H[mn[b]]) else (b, a)
            par[hi] = lo
    share = {}; states = []
    roots = np.array([find(i) for i in range(len(H))])
    for r in np.unique(roots):
        m = mn[r]; f = float((roots == r).mean()); lab = label(SPH[m])
        share[lab] = share.get(lab, 0.0) + f
        states.append(dict(label=lab, share=round(f, 4), barrier=float(barrier.get(m, 0.0)), h=float(H[m])))
    return share, sorted(states, key=lambda s: -s['share'])


def stall(P, G, s0=1.0, H=None):
    """the share of directions, more than 45 degrees off upright, where the body's drive is under s0 mm: the
    horizontal offset of the CoM from the contact (h's steepest slope per radian), which has to beat rolling
    friction (MuJoCo 0.5 mm here) for the body to keep rolling"""
    if H is None:
        H = support(P, G)
    slope = ((H[:, None] - H[NBP]) / NBA).max(1)
    off = -SPH[:, 2] < np.sqrt(0.5)                                      # up = -n; more than 45 degrees from upright
    return float(np.mean(off & (slope < s0)))


def margin(P, G, eps=None, lo=-0.3, hi=0.3, it=8):
    """how far (mm) the CoM can rise with upright still the only rest state; negative: how far it must drop"""
    H0 = np.ptp(P, 0)[2]; Hs = support(P, G); eps = 0.005 * np.ptp(P, 0).max() if eps is None else eps
    def mono(dz):                                       # the CoM up by dz: h(n) - dz n_z
        st = static(P, G, eps, Hs - dz * SPH[:, 2])[1]
        return len(st) == 1 and st[0]['label'] == 'upright'
    a, b = lo * H0, hi * H0
    if mono(b): return b
    if not mono(a): return a
    for _ in range(it):
        c = (a + b) / 2
        a, b = (c, b) if mono(c) else (a, c)
    return a


def screen(x):
    """the static screen of one design (a vector over KEYS): sizes, the print's and the robot's rest-state shares,
    stall shares and CoM heights"""
    q = as_dict(x)
    try:
        P, pk, sc = print_body(q); M, G, I = print_layout(P, pk)
        Hp = support(P, G); sp, _ = static(P, G, H=Hp); st_p = stall(P, G, H=Hp)
        F = body(q); Mr, Gr, Ir, mc = robot_layout(q)
        Hr = support(F, Gr); sr, _ = static(F, Gr, H=Hr); st_r = stall(F, Gr, H=Hr)
        e = np.ptp(F, 0)
        return np.r_[x, e, sc, float(pk['fits']), sp.get('upright', 0.0), st_p, G[2] / P[:, 2].max(),
                     sr.get('upright', 0.0), st_r, Gr[2] - FLOOR, mc]
    except Exception:
        return np.r_[x, np.full(11, np.nan)]


SCREEN_COLS = KEYS + ['length', 'width', 'height', 'scale', 'pocket_fits', 'print_static_up', 'print_stall', 'print_com_frac',
                      'robot_static_up', 'robot_stall', 'robot_com_above_floor', 'cover_g']


# ---------- drops of the printed body ----------
CONTACT = {'hard39': (0.002, 0.35, 1e-4),        # hard floor, the ball's measured bounce 0.39 (H3c secondary)
           'hard31': (0.002, 0.45, 1e-4),        # hard floor, E3's slow-motion 0.31 (H3c primary)
           'hard55': (0.002, 0.20, 1e-4),        # hard floor, the ball's rough 0.55 (best at 15 cm)
           'softfit': (0.02, 0.20, 5e-4)}        # soft floor, bounce fitted at 6 cm (H3b's winner)


def drops(P, layout, contact='hard39', starts='stand', n=60, drop_mm=150.0, jitter=15.0, mu=1.0, seed=0, settle=6):
    """rest states of simulated drops of a printed body (scale_model.predict's model and starts). starts='stand':
    the six starts of DROP_TEST.md, n each, with +-jitter; 'random': n uniformly random orientations."""
    import mujoco
    M, com, I = layout; tc, dr, ts = CONTACT[contact]; s = 1e-3
    verts = ' '.join('%.5f' % v for v in (P * s).ravel()); Isi = I * 1e-9
    full = ' '.join('%.8g' % v for v in (Isi[0, 0], Isi[1, 1], Isi[2, 2], Isi[0, 1], Isi[0, 2], Isi[1, 2]))
    sr = f' solref="{tc} {dr:.4f}"'
    xml = f"""<mujoco><option timestep="{ts}"/><asset><mesh name="h" vertex="{verts}"/></asset><worldbody>
      <geom type="plane" size="2 2 .1" friction="{0.45 * mu:.3f} 0.005 0.0005"{sr}/>
      <body name="b" pos="0 0 .3"><freejoint/>
        <inertial pos="{com[0] * s:.5f} {com[1] * s:.5f} {com[2] * s:.5f}" mass="{M * 1e-3:.5f}" fullinertia="{full}"/>
        <geom type="mesh" mesh="h" friction="{0.45 * mu:.3f} 0.005 0.0005"{sr}/></body></worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
    rng = np.random.default_rng(seed); Ps = P * s; out = {}
    plan = S.ATTITUDES if starts == 'stand' else {'random': None}
    nstep = int(round(0.02 / ts))
    for att, rp in plan.items():
        cnt = {k: 0 for k in T.CLASSES}
        for _ in range(n):
            q = np.zeros(4)
            if rp is None:
                q = rng.normal(size=4); q /= np.linalg.norm(q)
            else:
                r = np.radians(rp[0] + rng.normal(0, jitter / 2)); pt = np.radians(rp[1] + rng.normal(0, jitter / 2))
                yw = rng.uniform(0, 2 * np.pi); q0 = np.zeros(4)
                mujoco.mju_euler2Quat(q0, np.array([r, pt, 0.0]), 'xyz')
                mujoco.mju_mulQuat(q, np.array([np.cos(yw / 2), 0.0, 0.0, np.sin(yw / 2)]), q0)
            R9 = np.zeros(9); mujoco.mju_quat2Mat(R9, q); R = R9.reshape(3, 3)
            mujoco.mj_resetData(m, d)
            d.qpos[:3] = (0, 0, drop_mm * s - (Ps @ R.T)[:, 2].min()); d.qpos[3:7] = q
            still = 0
            for _ in range(400):                                    # 8 s at most
                mujoco.mj_step(m, d, nstep=nstep)
                if np.abs(d.qvel).max() < 0.01:
                    still += 1
                    if still >= settle: break
                else:
                    still = 0
            cnt[T.classify(d.xmat[1].reshape(3, 3))] += 1
        out[att] = cnt
    tot = {k: sum(c[k] for c in out.values()) for k in T.CLASSES}; N = sum(tot.values())
    return dict(p_upright=tot['upright'] / N, counts=tot, by_start=out, n=N)


# ---------- the full robot ----------
def robot_trials(q, n=200, seed=0, dz=0.0, cover=1.5, dampratio=0.2, spin=3.0):
    """tumble.trials for this shell: uniformly random orientations 5 mm over the floor, spin up to 3 rad/s, soft
    contact with bounce (damping 0.2) by default, as posthoc_sweep_v2's 'cover, bounce'"""
    import mujoco
    M, c, I, m_cov = robot_layout(q, dz, cover); s = 1e-3
    Ish = shell_points(q)
    verts = ' '.join('%.5f' % v for v in (Ish * s).ravel())
    dflt = '' if dampratio is None else f'<default><geom solref="0.02 {dampratio:.4f}"/></default>'
    wheels = ''.join(f'<geom type="cylinder" size="{55 * s:.4f} {T.TW / 2 * s:.4f}" pos="{x * s:.4f} {y * s:.4f} {T.ZA * s:.4f}" '
                     f'euler="90 0 0" friction="0.9 0.01 0.001"/>' for x in T.AXLES for y in (T.TRACK, -T.TRACK))
    bx, by, bz, br = T.HEAD['ball']; Isi = I * 1e-9
    full = ' '.join('%.8g' % v for v in (Isi[0, 0], Isi[1, 1], Isi[2, 2], Isi[0, 1], Isi[0, 2], Isi[1, 2]))
    xml = f"""<mujoco><option timestep="0.001"/>{dflt}<asset><mesh name="shell" vertex="{verts}"/>
      <mesh name="tub" vertex="{' '.join('%.5f' % v for v in (T.shell_points(66.0, 0.08) * s).ravel())}"/></asset><worldbody>
      <geom type="plane" size="5 5 0.1" friction="0.6 0.005 0.0005"/>
      <body name="robot" pos="0 0 0.5"><freejoint/>
        <inertial pos="{c[0] * s:.5f} {c[1] * s:.5f} {c[2] * s:.5f}" mass="{M * 1e-3:.4f}" fullinertia="{full}"/>
        <geom type="mesh" mesh="shell" friction="0.4 0.005 0.0005"/><geom type="mesh" mesh="tub" friction="0.4 0.005 0.0005"/>
        {wheels}<geom type="sphere" size="{br * s:.4f}" pos="{bx * s:.4f} {by * s:.4f} {bz * s:.4f}" friction="0.4 0.005 0.0005"/>
      </body></worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml); d = mujoco.MjData(m)
    E = body(q, 36, 8) * s; rng = np.random.default_rng(seed); cnt = {k: 0 for k in T.CLASSES}
    for _ in range(n):
        qq = rng.normal(size=4); qq /= np.linalg.norm(qq)
        Rm = np.zeros(9); mujoco.mju_quat2Mat(Rm, qq); Rm = Rm.reshape(3, 3)
        mujoco.mj_resetData(m, d)
        d.qpos[:3] = (0.0, 0.0, 0.005 - (E @ Rm.T)[:, 2].min()); d.qpos[3:7] = qq
        d.qvel[3:6] = rng.uniform(-1, 1, 3) * spin
        still = 0
        for _ in range(160):
            mujoco.mj_step(m, d, nstep=50)
            if np.abs(d.qvel).max() < 0.02:
                still += 1
                if still >= 6: break
            else:
                still = 0
        cnt[T.classify(d.xmat[1].reshape(3, 3))] += 1
    return dict(p_upright=cnt['upright'] / n, counts=cnt, mass_g=round(M), cover_g=round(m_cov), com_z=round(float(c[2]), 1))


def size(q):
    P = body(q); e = np.ptp(P, 0)
    return dict(length=float(e[0]), width=float(e[1]), height=float(e[2]))


def build(name, q, n=144, k=36):
    """the printed body as scale_model.build makes E1-E3: the hull as an exact solid, the pocket cut from the base, the
    spacer beside it -> research/models/NAME.stl and NAME.json. A finer hull than the search's (n x k), so its facets
    are smaller than the rest states' tipping angles."""
    import cadquery as cq
    _, pk, sc = print_body(q)
    P = np.vstack([shell_points(q, n, k), ROBOT]); h0 = ConvexHull(P); P = P[h0.vertices]
    P = (P - [0, 0, P[:, 2].min()]) * sc; h = ConvexHull(P); E = h.equations
    faces = []
    for f, e in zip(h.simplices, E):
        a, b, c = P[f]
        if np.cross(b - a, c - a) @ e[:3] < 0:
            b, c = c, b
        faces.append(cq.Face.makeFromWires(cq.Wire.makePolygon([cq.Vector(*a), cq.Vector(*b), cq.Vector(*c)], close=True)))
    solid = cq.Solid.makeSolid(cq.Shell.makeShell(faces)).clean()
    bodyw = cq.Workplane('XY').add(solid)
    bodyw = bodyw.cut(cq.Workplane('XY').workplane(offset=-1.0).center(pk['x'], 0).circle(S.POCKET_R).extrude(pk['depth'] + 1.0))
    # the nose mark: a 5 mm dimple, 1 mm deep, at the front's widest point (inside the hull, so no contact changes)
    zf = q['zc'] * sc - (np.vstack([shell_points(q), ROBOT])[:, 2].min()) * sc
    zf = float(np.clip(zf, 0.3 * P[:, 2].max(), 0.7 * P[:, 2].max()))
    near = P[(np.abs(P[:, 1]) < 3) & (np.abs(P[:, 2] - zf) < 3)]
    xf = float(near[:, 0].max()) if len(near) else float(P[:, 0].max())
    bodyw = bodyw.cut(cq.Workplane('YZ').workplane(offset=xf - 1.0).center(0, zf).circle(2.5).extrude(5.0))
    sp = (cq.Workplane('XY').center(P[:, 0].max() + 20, 0).circle(S.POCKET_R - 0.25).extrude(pk['spacer'])
          .faces('>Z').workplane().rect(3.0, 2 * S.POCKET_R).cutBlind(-2.0))
    allw = bodyw.add(sp)
    stl = os.path.join(ROOT, 'models', name + '.stl')
    cq.exporters.export(allw, stl, tolerance=0.05, angularTolerance=0.1)
    v = bodyw.val()
    info = dict(name=name, family='shell3', params=q, scale=sc, size=np.ptp(P, 0).round(1).tolist(),
                hull_volume_cm3=round(h.volume / 1000, 1), body_volume_cm3=round(v.Volume() / 1000, 1), valid=bool(v.isValid()),
                pockets=[pk], coin=dict(r=S.COIN_R, t=S.COIN_T, g=S.COIN_G), coins_g=round(pk['coins'] * S.COIN_G, 2),
                hull_facets=int(len(h.simplices)), hull_points_n=n, hull_points_k=k)
    json.dump(info, open(os.path.join(ROOT, 'models', name + '.json'), 'w'), indent=1)
    np.save(os.path.join(ROOT, 'models', name + '_hull.npy'), P)
    return info, P


if __name__ == '__main__':
    print('PLA fit: %.5f g/mm2, %.6f g/mm3, residuals' % (PLA_A, PLA_V), fit_pla()[2].round(2))
    for n in ('E1_tub', 'E2_dome', 'E3_tall'):
        info = json.load(open(os.path.join(ROOT, 'models', n + '.json')))
        P = S.hull_points(info['params'], info['scale']); pk = info['pockets'][0]
        for high in (False, True):
            M, G, I = print_layout(P, pk, high)
            sh, st = static(P, G)
            print(n, 'high' if high else 'low ', 'M %.1f CoM z %.2f' % (M, G[2]), {k: round(v, 3) for k, v in sorted(sh.items(), key=lambda kv: -kv[1])})
