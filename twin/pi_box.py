"""The Pi's box (2026-11-08): the friction-fit box from Zach's last robot, ready to go into the brain box.

    python twin/pi_box.py        # STLs in twin/out/print/, the checks, twin/out/pi_box_view.html

The body is the Printables "rpi5 base" as downloaded (reference/downloads/rpi5-case/, Zach found it 2026-11-08). The
top is his updated lid: "rpi5 lid" with a notch cut through one long edge so the GPIO pins come through. Only its
G-code survives (raspberry_pi_top.gcode, 2025-02-02), so the lid is rebuilt from the download with the notch read off
the toolpaths. Checks read the rebuild against those toolpaths; the untouched download is the control.

The base's four rings get wider bores (2026-11-08). The HAT kit's screws stay in the Pi, and their heads can't enter the rings'
3 mm holes, so in the download they sit on the rings and lift the board. Bored, the heads drop in and the board rests on the rings
where the download meant it to, with its ports back in line with the wall's windows. `pi_box_ring_test.stl` is the base's bottom
9 mm, to test that seat before printing a whole box.

Frame: the base's own, moved down to z 0. x runs from the SD card end to the USB end, y from the HDMI side to the GPIO
side, z up. The lid's download frame has its outside face at z 0 and its clips pointing up.
"""
import base64, json, os, re, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import numpy as np
import pymeshlab as ml
from scipy.ndimage import label, find_objects
import kit
from occ_load import vol
import export as EX

SRC = os.path.join(config.REPO, 'reference', 'downloads', 'rpi5-case')
BASE_STL, LID_STL = os.path.join(SRC, 'rpi5 base.STL'), os.path.join(SRC, 'rpi5 lid.STL')
PI_STL = os.path.join(config.REPO, 'reference', 'raspberry-pi-5', 'raspberry_pi_5_with_active_cooler.stl')
PI_BARE = os.path.join(config.REPO, 'reference', 'raspberry-pi-5', 'raspberry_pi_5.stl')
GCODE = os.path.expanduser(r'~\OneDrive\Desktop\3d print files\raspberry_pi_top.gcode')     # the printed lid; not in the repo
OUT, PRINT = config.TWIN_OUT, os.path.join(config.TWIN_OUT, 'print')
TEMPLATE = os.path.join(HERE, 'pi_box_view_template.html')

# --- read off the files
BASE_DZ = 98.5                  # the download's floor sits at z 98.5
FLOOR_TOP, RING_TOP, RIM = 3.0, 5.5, 36.5     # base: floor, the four screw rings' tops, the rim
LID_X, LID_Y = 2.7, 62.4        # lid to base: x = x_lid + 2.7, y = 62.4 - y_lid, z = RIM - z_lid. The plate is centred in the
                                # 91.5 x 59.6 opening and its centre clip's nub goes in the window in the SD end wall.
LID_T = 3.0                     # the lid's plate
NOTCH_PRINTED = (30.3, 86.3)    # the printed notch along the lid's x (G-code wall lines at 30.1 and 86.5, 0.2 inside the surface)
NOTCH_Y, BAR_Y = 9.6, 14.6      # its depth from the long edge; the vents crossing it stop at 14.6 (G-code lines at 9.8, 14.41)
VENTS = [(x, x + 4.0) for x in range(9, 86, 8)]   # the lid's long vents, along its x
# The header on his Pi model: 2 x 20 pins, pin 1 at the SD end. Model frame: y up, board bottom at y 0.
HDR_MX, HDR_MZ = (-35.4, 15.4), (-27.04, -21.96)
PI_DX, PI_DY = 49.5, 32.8       # model to base: x = mx + 49.5, y = 32.8 - mz, z = my + board bottom. check_holes() proves it.
HDR_X = (HDR_MX[0] + PI_DX, HDR_MX[1] + PI_DX)
HDR_Y = (PI_DY - HDR_MZ[1], PI_DY - HDR_MZ[0])
# Zach's call on the printed notch covering pins 1 to 16 (2026-11-08): "notch over the pins". The same 56 mm, centred over the header.
NOTCH_OVER_BASE = (11.5, 67.5)   # the header is 14.1 to 64.9
NOTCH_OVER = (NOTCH_OVER_BASE[0] - LID_X, NOTCH_OVER_BASE[1] - LID_X)

# --- Zach's caliper, 2026-11-08
STACK_HAT = 25.0                # bottom of the Pi's board to the top of the M.2 HAT
STACK_ALL = 55.0                # the screw under the Pi to the top of the Dupont plug's black housing
POST_ALL = 23.0                 # the whole HAT post, bottom screw to top screw
HEAD_D, HEAD_H = 4.25, 3.0      # the screw head under the Pi ("about")
OLD_LIFT = 2.0                  # how far the board sits high in the old box, on the heads ("rough")

# --- picked, then printed: "perfect fit" (the ring test, Zach, 2026-11-08). 0.25 a side, more than his 0.15 slide rule: the head size
# is "about", four must line up at once, and printed holes come out small.
HEAD_ROOM, RING_WALL = 0.25, 1.0

# --- guesses: for him to OK or measure
GUESSES = [
    ('Dupont housing length', 14.0, 'Only sets where the drawn plug starts. Its top is your 55.'),
    ('Wire bend above the plugs', 15.0, 'Room for the leads to turn over before the brain box lid. Sets how tall the brain box must be.'),
    ('HAT board, Hailo, posts', None, 'Drawn from the HAT+ spec, 65 x 56 and 22 x 42, with the top screw head as tall as the bottom one. The Hailo block stands for everything above the HAT board. Only the 23 and the 25 are yours.'),
]
BORE_D = HEAD_D + 2 * HEAD_ROOM; RING_OD = BORE_D + 2 * RING_WALL; HOUSING = GUESSES[0][1]; BEND = GUESSES[1][1]
RINGS = [(10.5, 8.28), (10.5, 57.33), (68.47, 8.28), (68.47, 57.33)]    # the rings' centres, from check_holes()
TEST_Z = 9.0                             # the ring test's height: over the 1.6 board on the rings, so the walls still locate it
BOARD_Z = RING_TOP                       # the board's bottom, on the rings, with the heads down in the bores
HEAD_Z0 = BOARD_Z - HEAD_H               # the heads' lowest point: the lower end of his 23 and 55
HAT_TOP = BOARD_Z + STACK_HAT
POST_TOP = HEAD_Z0 + POST_ALL
PLUG_TOP = HEAD_Z0 + STACK_ALL
LID_UNDER = RIM - LID_T


def stl(path):
    b = open(path, 'rb').read(); n = struct.unpack('<I', b[80:84])[0]
    return np.frombuffer(b[84:84 + n * 50], np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))['v'].astype(float).reshape(-1, 3, 3)


def write_tris(T, path):
    T = np.asarray(T, float); n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    a = np.zeros(len(T), np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')])); a['n'] = n; a['v'] = T.reshape(-1, 9)
    with open(path, 'wb') as f:
        f.write(b'\0' * 80); f.write(struct.pack('<I', len(T))); f.write(a.tobytes())


def section(T, axis, c):
    """the segments where a plane cuts the triangles: (n, 2, 3)"""
    d = T[:, :, axis] - c; out = []
    for t, dd in zip(T[(d.min(1) < 0) & (d.max(1) > 0)], d[(d.min(1) < 0) & (d.max(1) > 0)]):
        p = [t[i] + dd[i] / (dd[i] - dd[(i + 1) % 3]) * (t[(i + 1) % 3] - t[i]) for i in range(3) if (dd[i] < 0) != (dd[(i + 1) % 3] < 0)]
        if len(p) == 2: out.append(p)
    return np.array(out)


def lid(notch):
    """the download plus a notch through the y = 0 edge. The vents the notch reaches get a solid bar across them."""
    x0, x1 = notch
    vents = [v for v in VENTS if v[1] > x0 - 1.0 and v[0] < x1 + 1.0]     # within 1 mm of the notch counts: no paper-thin wall
    a, b = min(x0, vents[0][0] - 0.5), max(x1, vents[-1][1] + 0.5)
    s = kit.fuse(kit.part('lid', LID_STL), kit.bx((a, 5.0, 0.0), (b, BAR_Y, LID_T)))
    return kit.cut(s, kit.bx((x0, -1.0, -1.0), (x1, NOTCH_Y, LID_T + 1.0)))        # the cut overruns the edge and both faces


def bored(T):
    """the rings widened by moving their vertices outward, so the mesh keeps its faces and needs no boolean: the download's 54
    four-face edges at z 28.5 make it an invalid exact solid."""
    T = np.array(T, float); moved = []
    for cx, cy in RINGS:
        dx, dy = T[:, :, 0] - cx, T[:, :, 1] - cy; r = np.hypot(dx, dy); z = T[:, :, 2]
        bore = (np.abs(r - 1.5) < 0.12) & (z > 2.45) & (z < 5.55)
        ring = (np.abs(r - 2.9) < 0.12) & (z > 2.95) & (z < 5.55)
        for m, R in ((bore, BORE_D / 2), (ring, RING_OD / 2)):
            T[:, :, 0][m] = cx + dx[m] * R / r[m]; T[:, :, 1][m] = cy + dy[m] * R / r[m]
        moved.append((int(bore.sum()), int(ring.sum())))
    return T, moved


def head_room(T):
    """the smallest gap, mm, from each head to the base over the head's height. Below zero the base is in its way."""
    out = [9.0] * len(RINGS)
    for z in np.arange(HEAD_Z0 + 0.05, BOARD_Z, 0.5):
        S = section(T, 2, z); P = np.vstack([S.reshape(-1, 3), S.mean(1)])
        for i, (cx, cy) in enumerate(RINGS):
            out[i] = min(out[i], float(np.hypot(P[:, 0] - cx, P[:, 1] - cy).min()) - HEAD_D / 2)
    return out


def below(T, z0):
    """the triangles under a plane, split where they cross it, with the cut closed flat"""
    d = T[:, :, 2] - z0; keep = [T[d.max(1) <= 0]]; extra = []
    for t, dd in zip(T[(d.max(1) > 0) & (d.min(1) < 0)], d[(d.max(1) > 0) & (d.min(1) < 0)]):
        poly = []
        for i in range(3):
            a, b, da, db = t[i], t[(i + 1) % 3], dd[i], dd[(i + 1) % 3]
            if da <= 0: poly.append(a)
            if (da < 0 < db) or (db < 0 < da): poly.append(a + da / (da - db) * (b - a))
        for i in range(1, len(poly) - 1): extra.append((poly[0], poly[i], poly[i + 1]))
    L = np.vstack(keep + [np.array(extra)])
    ms = ml.MeshSet(); ms.add_mesh(ml.Mesh(L.reshape(-1, 3), np.arange(len(L) * 3).reshape(-1, 3)))
    ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-4))
    ms.meshing_remove_duplicate_faces(); ms.meshing_remove_null_faces()
    ms.meshing_close_holes(maxholesize=1000000, selfintersection=False)
    V, F = ms.current_mesh().vertex_matrix(), ms.current_mesh().face_matrix()
    return V[F]


def check_holes():
    """place the Pi by its holes, not its outline: the base's four rings against the board's holes. Control: the Pi the other
    way round. Reads the holes as the small round loops in a slice."""
    def loops(T, axis, c, u, v, lo, hi):
        s = section(T, axis, c); R = 0.05; pts = s.reshape(-1, 3)
        x0, y0 = pts[:, u].min() - 1, pts[:, v].min() - 1
        g = np.zeros((int((pts[:, v].max() - y0) / R) + 3, int((pts[:, u].max() - x0) / R) + 3), bool)
        for a, b in s:
            k = max(2, int(np.hypot(a[u] - b[u], a[v] - b[v]) / R) + 1)
            g[((np.linspace(a[v], b[v], k) - y0) / R).astype(int), ((np.linspace(a[u], b[u], k) - x0) / R).astype(int)] = True
        lab, _ = label(g, structure=np.ones((3, 3))); out = []
        for bz, bx_ in find_objects(lab):
            w, h = (bx_.stop - bx_.start) * R, (bz.stop - bz.start) * R
            if lo < w < hi and lo < h < hi and abs(w - h) < 0.25:
                out.append((x0 + (bx_.start + bx_.stop) / 2 * R, y0 + (bz.start + bz.stop) / 2 * R))
        return np.array(out)
    B = stl(BASE_STL); B[:, :, 2] -= BASE_DZ
    rings = loops(B, 2, 4.5, 0, 1, 2.2, 3.6)
    holes = loops(stl(PI_BARE), 1, 0.2, 0, 2, 5.5, 6.5)       # the 6 mm pads round the mounting holes
    rings = rings[np.argsort(rings[:, 0] + rings[:, 1] / 100)]
    out = {}
    for name, f in (('placed', lambda h: (h[0] + PI_DX, PI_DY - h[1])), ('turned 180 (control)', lambda h: (PI_DX - h[0], PI_DY + h[1]))):
        P = np.array([f(h) for h in holes])
        d = np.array([np.min(np.hypot(*(P - r).T)) for r in rings])
        out[name] = d
    return rings, holes, out


def check_toolpaths(T, tol=0.6):
    """how much of the printed lid's outer wall misses this lid's outline, as a share: 0 is the same part"""
    x = y = z = e = 0.0; mesh = kind = None; G = []
    for l in open(GCODE, errors='ignore'):
        if l.startswith(';MESH:'): mesh = l[6:].strip()
        elif l.startswith(';TYPE:'): kind = l[6:].strip()
        elif l.startswith('G92'):
            m = re.search(r'E(-?[\d.]+)', l); e = float(m.group(1)) if m else e
        elif l.startswith(('G0', 'G1')):
            m = dict(re.findall(r'([XYZE])(-?[\d.]+)', l.split(';')[0]))
            nx, ny, nz = float(m.get('X', x)), float(m.get('Y', y)), float(m.get('Z', z)); ne = float(m.get('E', e))
            if ne > e and abs(nz - 1.4) < 0.01 and kind == 'WALL-OUTER' and mesh == 'Incredible Jaiks.stl': G.append((x, y, nx, ny))
            x, y, z, e = nx, ny, nz, ne
    G = np.array(G) - (103.7, 120.4, 103.7, 120.4)        # its outer wall's centre line is 0.2 inside the surface
    S = section(T, 2, 1.4); R = 0.05; grid = np.zeros((1300, 2000), bool)
    def dots(a0, b0, a1, b1):
        k = max(2, int(np.hypot(a1 - a0, b1 - b0) / R) + 1); return np.linspace(a0, a1, k), np.linspace(b0, b1, k)
    for a, b in S:
        u, v = dots(a[0], a[1], b[0], b[1]); grid[(v / R).astype(int) + 100, (u / R).astype(int) + 100] = True
    from scipy.ndimage import distance_transform_edt as edt
    dist = edt(~grid) * R
    tot = off = 0
    for g in G:
        u, v = dots(*g); d = dist[(v / R).astype(int) + 100, (u / R).astype(int) + 100]; tot += len(d); off += (d > tol).sum()
    return off / tot


def mesh(T, faces=None):
    T = np.asarray(T, float).reshape(-1, 3, 3)
    ms = ml.MeshSet(); ms.add_mesh(ml.Mesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3)))
    ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-4))
    if faces and ms.current_mesh().face_number() > faces:
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=faces, qualitythr=0.6, preserveboundary=True, preservenormal=True, planarquadric=True, autoclean=True)
    return ms.current_mesh().vertex_matrix().astype('<f4'), ms.current_mesh().face_matrix().astype('<u4')


def box(x0, x1, y0, y1, z0, z1):
    V = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)], '<f4')
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]], '<u4')
    return V, F


def cyls(r, z0, z1, n=32):
    """one upright cylinder at each ring: (V, F)"""
    V, F = [], []
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    for cx, cy in RINGS:
        o = len(V)
        V += [(cx + r * np.cos(t), cy + r * np.sin(t), z) for z in (z0, z1) for t in a] + [(cx, cy, z0), (cx, cy, z1)]
        for i in range(n):
            j = (i + 1) % n
            F += [(o + i, o + j, o + n + j), (o + i, o + n + j, o + n + i), (o + 2 * n, o + j, o + i), (o + 2 * n + 1, o + n + i, o + n + j)]
    return np.array(V, '<f4'), np.array(F, '<u4')


def enc(VF, label_, group, color):
    V, F = VF
    return dict(label=label_, group=group, color=color, v=base64.b64encode(V.tobytes()).decode(), f=base64.b64encode(F.tobytes()).decode())


def lid_in_base(T):
    T = np.asarray(T, float).copy(); y = T[:, :, 1].copy()
    T[:, :, 0] += LID_X; T[:, :, 1] = LID_Y - y; T[:, :, 2] = RIM - T[:, :, 2]      # a half turn about x: faces keep pointing out
    return T


def page(base, old, printed, over, f):
    pi = stl(PI_STL); pm = np.empty_like(pi)
    pm[:, :, 0] = pi[:, :, 0] + PI_DX; pm[:, :, 1] = PI_DY - pi[:, :, 2]; pm[:, :, 2] = pi[:, :, 1] + BOARD_Z
    y0, y1 = HDR_Y; x0, x1 = HDR_X; bx0, by0 = PI_DX - 42.5, PI_DY - 28.0
    def part(VF, label_, group, color, note): return dict(enc(VF, label_, group, color), note=note)
    P = dict(
        base=part(mesh(base), 'Base, rings bored', 'box', 0xd9c39e, 'The Printables rpi5 base, 98.5 x 65.6 x 36.5 outside and 91.5 x 59.6 inside, with a 3 mm floor. The only change: the four rings are bored right through to %.2f and grown to %.2f wide, so your screw heads drop in and the board rests on the rings at %.1f. Printed as the ring test: your verdict, perfect fit, with the Pi\'s button lined up on its tab.' % (BORE_D, RING_OD, BOARD_Z)),
        base_old=part(mesh(old), 'Base, as downloaded', 'box', 0xcdb78f, 'The download: 3 mm holes up through the rings, for a longer screw coming in from outside the box. Your %.2f heads sit on top, so the board rides about %.0f mm high (your rough reading).' % (HEAD_D, OLD_LIFT)),
        lid_printed=part(mesh(lid_in_base(printed)), 'Lid, as printed', 'lid', 0xc9b48c, 'rpi5 lid plus what your G-code shows: a 56 x 9.6 notch through the long edge, with the seven vents it reaches stopped at 14.6. Clips latched, the notch runs %.1f to %.1f along the box.' % f['notch_printed']),
        lid_over=part(mesh(lid_in_base(over)), 'Lid, notch over the pins', 'lid', 0xc9b48c, 'Your printed notch, the same 56 x 9.6, moved so it runs %.1f to %.1f: 2.6 past the header at each end. The eight vents it reaches stop at 14.6.' % NOTCH_OVER_BASE),
        pi=part(mesh(pm, 24000), 'Pi 5 and cooler', 'stack', 0x2f8a58, 'Your Pi model, placed by its mounting holes on the four rings (they line up to within %.2f mm). The board bottom is at %.1f, and the parts under it clear the floor by %.1f.' % (f['ring_off'], BOARD_Z, BOARD_Z - f['under'] - FLOOR_TOP)),
        heads=part(cyls(HEAD_D / 2, HEAD_Z0, BOARD_Z), 'Screw heads', 'stack', 0xb9c0c9, 'Your caliper: about %.2f wide and %.0f tall, in the %.2f bores. The bores go right through, so a shorter head changes nothing here.' % (HEAD_D, HEAD_H, BORE_D)),
        posts=part(cyls(2.5, BOARD_Z + 1.6, POST_TOP), 'HAT posts', 'stack', 0xb08d57, 'Your caliper: %.0f for the whole post, bottom screw to top screw, so its top is at %.1f. That is %.1f under the lid; the top of the HAT at %.1f is what sets the gap.' % (POST_ALL, POST_TOP, LID_UNDER - POST_TOP, HAT_TOP)),
        hat=part(box(bx0, bx0 + 65.0, by0, by0 + 56.0, POST_TOP - HEAD_H - 1.6, POST_TOP - HEAD_H), 'M.2 HAT+', 'stack', 0x3fa36f, 'Drawn from the spec, under the top screw heads.'),
        hailo=part(box(PI_DX - 21.0, PI_DX + 21.0, PI_DY - 11.0, PI_DY + 11.0, POST_TOP - HEAD_H, HAT_TOP), 'M.2 connector and Hailo', 'stack', 0x1d6b45, 'Everything above the HAT board, drawn as one block. Its top is your 25 from the bottom of the Pi board.'),
        pins=part(box(x0, x1, y0 + 0.9, y1 - 0.9, BOARD_Z + 1.6, PLUG_TOP - HOUSING), 'Header and extensions', 'stack', 0xc9a227, 'The 2 x 20 header, %.1f to %.1f along the box, %.1f to %.1f across it, read off your Pi model. Pin 1 is at the SD end.' % (x0, x1, y0, y1)),
        plugs=part(box(x0, x1, y0, y1, PLUG_TOP - HOUSING, PLUG_TOP), 'Dupont plugs', 'stack', 0x3a3d43, "All 40 drawn, the worst case. The top is your 55 from the screw head, so %.1f above the base's underside and %.1f above the lid. A head shorter than %.0f raises this by the difference." % (PLUG_TOP, PLUG_TOP - RIM, HEAD_H)),
        bend=part(box(x0 - 2, x1 + 2, y0 - 2, y1 + 2, PLUG_TOP, PLUG_TOP + BEND), 'Room for wires to bend', 'zone', 0x6ea6e6, 'A guess: 15 mm for the leads to turn over. The brain box lid has to clear this.'),
        hit=part(box(x0, min(x1, f['notch_printed'][0]), y0 + 0.9, y1 - 0.9, LID_UNDER - 0.4, RIM + 0.4), 'Pins under the printed lid', 'hit', 0xd0453a, 'Where the header runs under the printed lid: %.1f mm, pins 1 to %d. That end holds the I2C pins the PCA9685 uses (3 and 5).' % (f['blocked'], f['pins'])),
    )
    meta = dict(numbers=f['numbers'], guesses=[dict(name=n, value=v, why=w) for n, v, w in GUESSES], blocked=f['blocked'], pins=f['pins'],
                header=[x0, x1], notch_printed=f['notch_printed'], notch_over=NOTCH_OVER_BASE, gap=LID_UNDER - HAT_TOP, proud=PLUG_TOP - RIM, cut_y=(y0 + y1) / 2,
                old_lift=OLD_LIFT, head=[HEAD_D, HEAD_H], bore=BORE_D, ring=RING_OD, old_gap=LID_UNDER - HAT_TOP - OLD_LIFT, test_z=TEST_Z)
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', 'window.PARTS=' + json.dumps(P) + ';window.META=' + json.dumps(meta) + ';')
    p = os.path.join(OUT, 'pi_box_view.html'); open(p, 'w', encoding='utf-8').write(html)
    return p, len(html) / 1e6


if __name__ == '__main__':
    os.makedirs(PRINT, exist_ok=True)
    B = stl(BASE_STL); B[:, :, 2] -= BASE_DZ
    base_p = os.path.join(PRINT, 'pi_box_base.stl'); write_tris(B, base_p)
    BB, moved = bored(B)
    write_tris(BB, os.path.join(PRINT, 'pi_box_base_bored.stl'))
    write_tris(below(BB, TEST_Z), os.path.join(PRINT, 'pi_box_ring_test.stl'))
    paths = {'lid_as_printed': lid(NOTCH_PRINTED), 'lid_over_header': lid(NOTCH_OVER)}
    for k, s in paths.items():
        EX.write_stl(s, os.path.join(PRINT, 'pi_box_%s.stl' % k))
    printed, over = stl(os.path.join(PRINT, 'pi_box_lid_as_printed.stl')), stl(os.path.join(PRINT, 'pi_box_lid_over_header.stl'))

    print('--- mesh report')
    for k in ('base', 'base_bored', 'ring_test', 'lid_as_printed', 'lid_over_header'):
        ok, msg = EX.health(os.path.join(PRINT, 'pi_box_%s.stl' % k)); print('  %-16s %s %s' % (k, 'ok ' if ok else 'BAD', msg))
    print('  lid volumes (mm3): download %.0f, as printed %.0f, over the header %.0f' % (vol(kit.part('lid', LID_STL)), vol(paths['lid_as_printed']), vol(paths['lid_over_header'])))

    print('--- the rebuild against the printed lid\'s toolpaths: share of its outer wall off the outline')
    if os.path.exists(GCODE):
        print('  download, no notch (control): %.1f%%   rebuilt as printed: %.1f%%' % (100 * check_toolpaths(stl(LID_STL)), 100 * check_toolpaths(printed)))
    else:
        print('  skipped: the G-code is not on this machine')

    print('--- the Pi on the rings: each ring to the nearest board hole, mm')
    rings, holes, off = check_holes()
    print('  rings at', rings.round(1).tolist(), ' holes found', len(holes))
    for k, d in off.items(): print('  %-22s %s' % (k, d.round(2).tolist()))

    print('--- the screw heads (about %.2f wide, %.0f tall) in the rings: smallest gap to the base at each ring, mm' % (HEAD_D, HEAD_H))
    print('  vertices moved at each ring (bore, outside):', moved)
    print('  bored %s' % [round(a, 2) for a in head_room(BB)])
    print('  as downloaded (control) %s' % [round(a, 2) for a in head_room(B)])
    under = -stl(PI_BARE)[:, :, 1].min()
    print('  the parts under the board reach %.2f below it: %.2f clear of the floor, on the rings' % (under, BOARD_Z - under - FLOOR_TOP))
    TT = stl(os.path.join(PRINT, 'pi_box_ring_test.stl'))[:, :, 2]
    print('  ring test: z %.2f to %.2f' % (TT.min(), TT.max()))

    print('--- the plugs through the lid (exact overlap, mm3). Header x %.1f to %.1f, y %.2f to %.2f' % (*HDR_X, *HDR_Y))
    def plug_hit(s):       # the plug block in the lid's frame
        return vol(kit.common(s, kit.bx((HDR_X[0] - LID_X, LID_Y - HDR_Y[1], -40.0), (HDR_X[1] - LID_X, LID_Y - HDR_Y[0], 20.0))))
    hits = {k: plug_hit(s) for k, s in paths.items()}
    for k, v in hits.items(): print('  %-16s %.1f' % (k, v))
    n0, n1 = NOTCH_PRINTED[0] + LID_X, NOTCH_PRINTED[1] + LID_X
    blocked = max(0.0, n0 - HDR_X[0]); pins = int(np.ceil(blocked / 2.54)) * 2
    print('  printed notch in the base: x %.1f to %.1f. It leaves %.1f mm of the header under the lid: pins 1 to %d' % (n0, n1, blocked, pins))
    print('  chosen notch in the base: x %.1f to %.1f. Spare past the header: %.1f at the SD end, %.1f at the USB end' % (*NOTCH_OVER_BASE, HDR_X[0] - NOTCH_OVER_BASE[0], NOTCH_OVER_BASE[1] - HDR_X[1]))

    print('--- heights above the base\'s underside')
    numbers = [('Bottom of screw heads', HEAD_Z0, 'yours'), ('Floor', FLOOR_TOP, 'file'), ('Rings, board bottom', BOARD_Z, 'file'), ('Top of HAT posts', POST_TOP, 'yours'), ('HAT top', HAT_TOP, 'yours'),
               ('Lid underside', LID_UNDER, 'file'), ('Rim, lid top', RIM, 'file'), ('Plug top', PLUG_TOP, 'yours'), ('Wire bend', PLUG_TOP + BEND, 'guess')]
    for n, z, w in numbers: print('  %-14s %5.1f  (%s)' % (n, z, w))
    print('  HAT to lid %.1f; plugs above the lid %.1f; box outside 98.5 x 65.6 x 36.5' % (LID_UNDER - HAT_TOP, PLUG_TOP - RIM))
    if os.path.exists(TEMPLATE):
        f = dict(notch_printed=(n0, n1), blocked=blocked, pins=pins, numbers=numbers, under=under,
                 ring_off=float(off['placed'].max()))
        p, mb = page(BB, B, printed, over, f); print('wrote %s (%.1f MB)' % (p, mb))
