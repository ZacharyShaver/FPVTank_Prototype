"""Ribbon clock-spring coil test rig: cup, spool, lid, knob. Units mm, Z up, each part in print orientation."""
import os, sys, struct
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, 'coil_test'); os.makedirs(OUT, exist_ok=True)

def fix(tris, dirs):
    tris = np.array(tris, float); dirs = np.array(dirs, float)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    flip = np.einsum('ij,ij->i', n, dirs) < 0
    tris[flip] = tris[flip][:, [0, 2, 1]]
    return tris

def sector(r0, r1, z0, z1, a0=0.0, a1=2 * np.pi, n=96):
    """Annular sector (r0 may be 0). Full ring when a1-a0 == 2pi."""
    full = abs((a1 - a0) - 2 * np.pi) < 1e-9
    m = max(8, int(n * (a1 - a0) / (2 * np.pi)))
    A = np.linspace(a0, a1, m + 1)
    P = lambda r, a, z: [r * np.cos(a), r * np.sin(a), z]
    T, Dd = [], []
    for i in range(m):
        a, b = A[i], A[i + 1]; mid = (a + b) / 2; rad = [np.cos(mid), np.sin(mid), 0]
        T += [[P(r1, a, z0), P(r1, b, z0), P(r1, b, z1)], [P(r1, a, z0), P(r1, b, z1), P(r1, a, z1)]]; Dd += [rad, rad]
        if r0 > 0:
            T += [[P(r0, a, z0), P(r0, b, z0), P(r0, b, z1)], [P(r0, a, z0), P(r0, b, z1), P(r0, a, z1)]]; Dd += [[-rad[0], -rad[1], 0]] * 2
            T += [[P(r0, a, z1), P(r1, a, z1), P(r1, b, z1)], [P(r0, a, z1), P(r1, b, z1), P(r0, b, z1)]]; Dd += [[0, 0, 1]] * 2
            T += [[P(r0, a, z0), P(r1, a, z0), P(r1, b, z0)], [P(r0, a, z0), P(r1, b, z0), P(r0, b, z0)]]; Dd += [[0, 0, -1]] * 2
        else:
            T += [[[0, 0, z1], P(r1, a, z1), P(r1, b, z1)]]; Dd += [[0, 0, 1]]
            T += [[[0, 0, z0], P(r1, a, z0), P(r1, b, z0)]]; Dd += [[0, 0, -1]]
    if not full:
        for a, s in ((a0, -1), (a1, 1)):
            t = [-np.sin(a) * s, np.cos(a) * s, 0]
            if r0 > 0:
                T += [[P(r0, a, z0), P(r1, a, z0), P(r1, a, z1)], [P(r0, a, z0), P(r1, a, z1), P(r0, a, z1)]]; Dd += [t, t]
            else:
                T += [[[0, 0, z0], P(r1, a, z0), P(r1, a, z1)], [[0, 0, z0], P(r1, a, z1), [0, 0, z1]]]; Dd += [t, t]
    return fix(T, Dd)

def box(x0, x1, y0, y1, z0, z1):
    p = lambda i, j, k: [(x0, x1)[i], (y0, y1)[j], (z0, z1)[k]]
    T, Dd = [], []
    for ax in range(3):
        for s in (0, 1):
            q = []
            for u in (0, 1):
                for v in (0, 1):
                    idx = [0, 0, 0]; o = [a for a in range(3) if a != ax]
                    idx[ax] = s; idx[o[0]] = u; idx[o[1]] = v
                    q.append(p(*idx))
            d = [0, 0, 0]; d[ax] = 1 if s else -1
            T += [[q[0], q[1], q[3]], [q[0], q[3], q[2]]]; Dd += [d, d]
    return fix(T, Dd)

def prism(poly, z0, z1):
    """Convex polygon (x, y) extruded between z0 and z1."""
    poly = np.array(poly, float); c = poly.mean(0); n = len(poly); T, Dd = [], []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        T += [[[c[0], c[1], z1], [a[0], a[1], z1], [b[0], b[1], z1]]]; Dd += [[0, 0, 1]]
        T += [[[c[0], c[1], z0], [a[0], a[1], z0], [b[0], b[1], z0]]]; Dd += [[0, 0, -1]]
        mid = (a + b) / 2 - c
        T += [[[a[0], a[1], z0], [b[0], b[1], z0], [b[0], b[1], z1]], [[a[0], a[1], z0], [b[0], b[1], z1], [a[0], a[1], z1]]]; Dd += [[mid[0], mid[1], 0]] * 2
    return fix(T, Dd)

def seg_half(r, gap, side, n=64):
    """Circular segment of radius r on one side of a slit of width gap along the Y axis."""
    x0 = gap / 2
    t0 = np.arcsin(np.clip(x0 / r, -1, 1))
    ang = np.linspace(-np.pi / 2 + t0, np.pi / 2 - t0, n)  # measured from +X
    pts = [(side * r * np.cos(a), r * np.sin(a)) for a in ang]
    return pts if side > 0 else pts[::-1]

def watertight(tris):
    q = np.round(tris, 5); e = {}
    for t in q:
        for i, j in ((0, 1), (1, 2), (2, 0)):
            k = (tuple(t[i]), tuple(t[j]))
            e[k] = e.get(k, 0) + 1
    bad = sum(1 for (a, b), c in e.items() if e.get((b, a), 0) != c)
    return bad

def write_stl(path, shells):
    tris = np.concatenate(shells)
    with open(path, 'wb') as f:
        f.write(b'Scorpion ribbon coil test rig (mm)'.ljust(80, b' ')); f.write(struct.pack('<I', len(tris)))
        for t in tris:
            n = np.cross(t[1] - t[0], t[2] - t[0]); ln = np.linalg.norm(n); n = n / ln if ln else n
            f.write(struct.pack('<12fH', *n, *t[0], *t[1], *t[2], 0))
    return len(tris)

# ---------------- dimensions ----------------
FLOOR = 2.0
WALL_IN, WALL_OUT = 18.8, 21.0       # 37.6 mm chamber, 2.2 mm wall
CHAMBER = 21.0                       # floor top to rim (16 mm ribbon + slit headroom + lid ring)
RIM = FLOOR + CHAMBER                # 23.0
EXIT_W = 1.8                         # ribbon exit slit through the wall
SPOOL_R = 10.0                       # 20 mm spool, as on the ball hub
SLIT = 1.0                           # ribbon anchor slit through the spool
PIN_R, PIN_H = 2.0, 1.7
SEAT = 0.3                           # spool floats this far above the floor
LID_T, LID_HOLE = 2.0, 4.3
NECK = 5.0                           # square drive neck
KNOB_HOLE = 5.35

# ---------------- cup (prints on its floor) ----------------
exit_half = (EXIT_W / 2) / WALL_IN
cup = [sector(0, WALL_OUT, 0, FLOOR),
       sector(WALL_IN, WALL_OUT, FLOOR, RIM, np.pi + exit_half, 3 * np.pi - exit_half),   # exit slit at 180 deg
       sector(0, PIN_R, FLOOR, FLOOR + PIN_H)]
for deg in (-60, 0, 60):                                                                  # angle ticks on the rim
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    tick = box(WALL_OUT - 0.5, WALL_OUT + 3.0, -0.6, 0.6, RIM - 4.0, RIM)
    Rm = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]); cup.append(tick @ Rm.T)

# ---------------- spool (prints upright on its base) ----------------
post_h = RIM - FLOOR - SEAT - 0.3                                   # stops 0.3 below the rim / lid underside
spool = [sector(PIN_R + 0.25, SPOOL_R, 0, 2.0),                     # base with pin socket
         sector(0, SPOOL_R, 2.0, 3.0),                              # solid web under the slit
         prism(seg_half(SPOOL_R, SLIT, +1), 3.0, post_h),           # two halves either side of the ribbon slit
         prism(seg_half(SPOOL_R, SLIT, -1), 3.0, post_h),
         box(-NECK / 2, NECK / 2, -NECK / 2, NECK / 2, post_h - 0.5, post_h + 0.3 + LID_T + 0.5 + 4.0)]  # square neck bridges the halves
slit_h = post_h - 3.0

# ---------------- lid (prints flat, locating ring up; flip to fit) ----------------
lid = [sector(LID_HOLE, WALL_OUT, 0, LID_T), sector(WALL_IN - 0.75, WALL_IN - 0.2, LID_T, LID_T + 2.0)]

# ---------------- knob (prints flat) ----------------
h, o = KNOB_HOLE / 2, 8.0
knob = [box(-o, o, h, o, 0, 4), box(-o, o, -o, -h, 0, 4), box(-o, -h, -h, h, 0, 4), box(h, o, -h, h, 0, 4),
        box(o - 0.5, WALL_OUT + 3.5, -1.25, 1.25, 1.0, 4)]          # pointer reaches the rim ticks

parts = dict(cup=cup, spool=spool, lid=lid, knob=knob)
for name, shells in parts.items():
    bad = [watertight(s) for s in shells]
    ntri = write_stl(os.path.join(OUT, f'coil_test_{name}.stl'), shells)
    V = np.concatenate(shells).reshape(-1, 3)
    print(f'{name}: {len(shells)} shells, {ntri} tris, open edges per shell {bad}, size {np.ptp(V, 0).round(1)} mm')
print(f'spool slit height {slit_h:.1f} mm for a 16 mm ribbon; chamber ID {2*WALL_IN} mm; spool OD {2*SPOOL_R} mm')

# ---------------- preview (assembled cutaway + parts as printed) ----------------
exec(open(os.path.join(D, 'render_stl.py'), encoding='utf-8-sig').read().split("out = sys.argv[1]")[0])
exec("def zrender" + open(os.path.join(D, 'render2.py'), encoding='utf-8-sig').read().split("def zrender")[1].split("def section")[0])
def move(shells, dz=0.0, dx=0.0, flip=False):
    out = []
    for s in shells:
        t = s.copy()
        if flip: t[:, :, 2] = -t[:, :, 2]; t = t[:, [0, 2, 1]]
        t[:, :, 2] += dz; t[:, :, 0] += dx; out.append(t)
    return out
def cut(shells):  # drop triangles on the viewer's half (y < 0) for a cutaway look
    return [s[s[:, :, 1].mean(1) > 0] for s in shells]
G, B_, O_, P_ = (90, 190, 160), (120, 170, 230), (235, 150, 90), (170, 150, 225)
spool_z = FLOOR + SEAT
lid_z = RIM + LID_T
ts = np.linspace(0, 4 * np.pi, 200); rs = 10.5 + 7.0 * ts / ts[-1]
coil = []
for a0, a1, r0_, r1_ in zip(ts[:-1], ts[1:], rs[:-1], rs[1:]):
    p0 = [r0_ * np.cos(a0), r0_ * np.sin(a0)]; p1 = [r1_ * np.cos(a1), r1_ * np.sin(a1)]
    z0, z1 = spool_z + 3.5, spool_z + 3.5 + 16
    coil += [[[p0[0], p0[1], z0], [p1[0], p1[1], z0], [p1[0], p1[1], z1]], [[p0[0], p0[1], z0], [p1[0], p1[1], z1], [p0[0], p0[1], z1]]]
coil = [np.array(coil)]
asm = [(s, G) for s in cut(cup)] + [(s, B_) for s in move(spool, spool_z)] + [(s, (235, 130, 60)) for s in cut(coil)] + \
      [(s, P_) for s in cut(move(lid, lid_z, flip=True))] + [(s, O_) for s in move(knob, lid_z + 0.5)]
ims = [zrender(asm, 30, 28, size=700, label='assembled cutaway (orange = ribbon, 2 turns)', center=np.array([0, 0, 14.0]), ext=34),
       zrender([(s, G) for s in cup], 30, 35, size=700, label='cup (print on floor)', center=np.array([0, 0, 11.0]), ext=30),
       zrender([(s, B_) for s in spool], 30, 25, size=700, label=f'spool (print upright) - {slit_h:.1f} mm slit', center=np.array([0, 0, 14.0]), ext=20),
       zrender([(s, P_) for s in lid] + [(s, O_) for s in move(knob, 0, 0)], 30, 40, size=700, label='lid + knob (print flat)', center=np.array([3, 0, 2.0]), ext=30)]
sheet = Image.new('RGB', (1400, 1400), 'white')
for i, im in enumerate(ims): sheet.paste(im, ((i % 2) * 700, (i // 2) * 700))
sheet.save(os.path.join(OUT, 'coil_test_preview.png'))
print('preview ok')
