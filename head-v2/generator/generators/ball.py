import os, sys
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(D, 'concept.py'), encoding='utf-8-sig').read().split("H = 26.5")[0])

def sphere(cx, cy, cz, r, nlat=40, nlon=72):
    th = np.linspace(0, np.pi, nlat + 1); ph = np.linspace(0, 2 * np.pi, nlon + 1)
    P = lambda i, j: [cx + r * np.sin(th[i]) * np.cos(ph[j]), cy + r * np.cos(th[i]), cz + r * np.sin(th[i]) * np.sin(ph[j])]
    t = []
    for i in range(nlat):
        for j in range(nlon):
            a, b, c, d = P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)
            if i > 0: t.append([a, b, c])
            if i < nlat - 1: t.append([a, c, d])
    return orient(np.array(t, float), np.array([cx, cy, cz]))

P_ = 10.0              # pedestal height
TT = P_ + 4.5          # turntable top
R = 25.0               # ball radius
H = TT + R + 2.0       # tilt axis height above deck
FRONT = 40.0           # deck front edge X (pan axis at X=0)
col = dict(deck=(185, 183, 175), struct=(90, 190, 160), ball=(170, 150, 225), seam=(90, 80, 120), lens=(55, 55, 65),
           bezel=(120, 110, 150), bearing=(230, 175, 70), ribbon=(235, 130, 60), ir=(215, 80, 80), servo=(95, 140, 210))
static = []
for b in [box(-60, -20, -50, 50, -3, 0), box(-20, 12, -50, -9, -3, 0), box(-20, 12, 9, 50, -3, 0), box(12, FRONT, -50, 50, -3, 0)]:
    static.append((b, col['deck']))
static += [(box(-16.9, 5.9, -6.1, 6.1, P_ - 24.3, P_ - 1.8), col['servo'])]            # pan servo (mostly inside pedestal)
static += [(cyl(0, 0, 0, 18, 'z', 0, P_), col['struct']),                              # pedestal
           (cyl(0, 0, 0, 17, 'z', P_, P_ + 0.5), col['bearing']),                      # slide ring
           (cyl(0, 0, 0, 20, 'z', P_ + 0.5, TT), col['struct']),                       # turntable hub
           (box(-11, 11, -38, 42, P_ + 0.5, TT), col['struct'])]                       # turntable bar
# servo pod (+Y): column + round pod hiding the MG90D
static += [(box(-10, 10, 28, 42, TT, H), col['struct']), (cyl(0, 0, H, 20, 'y', 28, 42), col['struct']),
           (cyl(0, 0, H, 20.5, 'y', 41.5, 42.5), col['seam'])]
# bearing pod (-Y): column + pod + 6704 bearing with hollow bore
static += [(box(-10, 10, -38, -28, TT, H), col['struct']), (cyl(0, 0, H, 16, 'y', -38, -28), col['struct']),
           (cyl(0, 0, H, 13.5, 'y', -38.3, -38), col['bearing']), (cyl(0, 0, H, 10, 'y', -38.45, -38.3), col['lens'])]
# ribbon: out of the hollow axle, down the pod column face, into the turntable/pedestal
static += [(box(-8, 8, -38.9, -38.5, TT + 2, H - 10), col['ribbon']), (box(-8, 8, -38.9, -30, TT + 1.6, TT + 2), col['ribbon'])]
# IR headlights at the deck front
for s in (-1, 1):
    static += [(box(FRONT - 8, FRONT, s * 36 - 6, s * 36 + 6, 0, 10), col['deck']), (cyl(0, s * 36, 5, 4.5, 'x', FRONT, FRONT + 1), col['ir'])]
# tilting parts
bz = np.sqrt(R ** 2 - 9 ** 2)
tilting = [(sphere(0, 0, H, R), col['ball']), (cyl(0, 0, H, R + 0.15, 'y', -0.4, 0.4), col['seam']),
           (cyl(0, 0, H, 9, 'x', bz - 1.5, bz + 1.2), col['bezel']), (cyl(0, 0, H, 6, 'x', bz + 1.2, bz + 3.5), col['lens']),
           (cyl(0, 0, H, 10, 'y', -28, -25), col['struct']), (cyl(0, 0, H, 8, 'y', 25, 28), col['horn'] if 'horn' in col else (225, 225, 215))]

def tilt_mesh(T, deg):
    t = np.radians(deg); out = T.copy(); x = T[:, :, 0]; z = T[:, :, 2] - H
    out[:, :, 0] = x * np.cos(t) + z * np.sin(t); out[:, :, 2] = H - x * np.sin(t) + z * np.cos(t)
    return out
def scene(deg): return static + [(tilt_mesh(m, deg), c) for m, c in tilting]
def project(pt, yaw, pitch, size, center, ext):
    Rm = rot(yaw, pitch); Pp = (np.array(pt) - center) @ Rm.T; sc = size / (2 * ext)
    return size / 2 + Pp[0] * sc, size / 2 - Pp[2] * sc
size = 900
c_iso, e_iso = np.array([0.0, 2.0, 28.0]), 62.0
calls = {1: (0, -12, H + R), 2: (0, 42, H + 12), 3: (0, -38.5, H + 11), 4: (0, 30, TT - 1), 5: (13, -13, P_ / 2),
         6: (0, -38.9, TT + 12), 7: (FRONT, 36, 10), 8: (bz + 2, 0, H + 7)}
tiles = []
for yaw, pitch, lbl, show in [(215, 22, 'Ball head: iso front', [1, 2, 4, 5, 7, 8]), (145, 22, 'iso, bearing side', [1, 3, 5, 6, 7])]:
    im = zrender(scene(0), yaw, pitch, size=size, label=lbl, center=c_iso, ext=e_iso)
    d = ImageDraw.Draw(im)
    for num in show:
        x, y = project(calls[num], yaw, pitch, size, c_iso, e_iso)
        d.line([(x, y), (x + 26, y - 26)], fill=(40, 40, 40), width=2)
        d.ellipse([x + 20, y - 46, x + 46, y - 20], fill=(255, 255, 255), outline=(40, 40, 40), width=2)
        d.text((x + 29, y - 39), str(num), fill=(20, 20, 20))
    tiles.append(im)
tiles.append(zrender(scene(0), 270, 0, size=size, label='front view (what you face)', center=np.array([0, 0, 30.0]), ext=e_iso))
VFOV = 41.0
c_side, e_side = np.array([10.0, 0, 35.0]), 58.0
for deg in (0, 45):
    im = zrender(scene(deg), 0, 0, size=size, label=f'side view, tilt {deg} deg down, assumed {VFOV:.0f} deg vertical FOV', center=c_side, ext=e_side)
    d = ImageDraw.Draw(im); sc = size / (2 * e_side)
    S = lambda X, Z: (size / 2 + (X - c_side[0]) * sc, size / 2 - (Z - c_side[2]) * sc)
    t = np.radians(deg); lx, lz = (bz + 3.5) * np.cos(t), H - (bz + 3.5) * np.sin(t)
    for a in (deg - VFOV / 2, deg + VFOV / 2):
        ar = np.radians(a); L = 90
        d.line([S(lx, lz), S(lx + L * np.cos(ar), lz - L * np.sin(ar))], fill=(200, 40, 40), width=2)
    enter = None
    for th in np.arange(0, 90.01, 0.5):
        tr = np.radians(th); ex, ez = (bz + 3.5) * np.cos(tr), H - (bz + 3.5) * np.sin(tr)
        if th + VFOV / 2 >= np.degrees(np.arctan2(ez, FRONT - ex)): enter = th; break
    d.text((12, size - 50), f'deck front edge enters bottom of frame at ~{enter:.0f} deg down  (axis {H:.1f} mm above deck)', fill=(200, 40, 40))
    tiles.append(im)
lg = Image.new('RGB', (size, size), (246, 245, 241)); d = ImageDraw.Draw(lg)
items = ['1  Ball (50 mm) centred on the tilt axis, split L/R, seam as a groove', '2  Servo pod: MG90D inside, stock horn drives the ball hub',
         '3  Bearing pod: 6704 thin bearing, hollow 20 mm axle', '4  Turntable bar on a slide ring', '5  Pedestal (10 mm) houses the pan servo',
         '6  Ribbon exits through the hollow axle, zero tilt drag', '7  IR pods as headlights', '8  Lens in a bezel, set into the ball surface']
for i, s_ in enumerate(items): d.text((40, 60 + i * 44), s_, fill=(30, 30, 30))
for i, (k, c_) in enumerate([('struct', 'printed structure'), ('ball', 'camera ball'), ('bearing', 'bearings / slide ring'), ('ribbon', 'CSI ribbon'), ('ir', 'IR pods'), ('deck', 'deck')]):
    y = 470 + i * 40; d.rectangle([40, y, 64, y + 24], fill=col[k]); d.text((80, y + 6), c_, fill=(30, 30, 30))
tiles.append(lg)
sheet = Image.new('RGB', (size * 3, size * 2), 'white')
for i, im in enumerate(tiles): sheet.paste(im, ((i % 3) * size, (i // 3) * size))
sheet.save(os.path.join(D, 'ball_head.png'))
print('H', H, 'width', 42 + 38.45, 'deck edge enters at', enter)
