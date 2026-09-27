import os, sys
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], D, "none"]
exec(open(os.path.join(D, 'render_stl.py'), encoding='utf-8-sig').read().split("out = sys.argv[1]")[0])
exec(open(os.path.join(D, 'render2.py'), encoding='utf-8-sig').read().split("OUT = sys.argv[1]")[1].split("B = load_stl(")[0].replace("OUT = sys.argv[1]", ""))
exec("def zrender" + open(os.path.join(D, 'render2.py'), encoding='utf-8-sig').read().split("def zrender")[1].split("def section")[0])
from PIL import Image, ImageDraw

def orient(tris, center):
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    c = tris.mean(1)
    flip = np.einsum('ij,ij->i', n, c - center) < 0
    tris[flip] = tris[flip][:, [0, 2, 1]]
    return tris

def box(x0, x1, y0, y1, z0, z1):
    p = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)], float)
    q = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    t = []
    for a, b, c, d in q:
        t += [[p[a], p[b], p[c]], [p[a], p[c], p[d]]]
    return orient(np.array(t), p.mean(0))

def cyl(cx, cy, cz, r, axis, h0, h1, n=48):
    a = np.linspace(0, 2 * np.pi, n + 1)
    def P(ang, h):
        u, v = r * np.cos(ang), r * np.sin(ang)
        if axis == 'z': return [cx + u, cy + v, h]
        if axis == 'y': return [cx + u, h, cz + v]
        return [h, cy + u, cz + v]
    t = []
    for i in range(n):
        p0, p1, p2, p3 = P(a[i], h0), P(a[i + 1], h0), P(a[i + 1], h1), P(a[i], h1)
        t += [[p0, p1, p2], [p0, p2, p3]]
        c0 = P(0, h0); c0 = [cx, cy, cz];
        if axis == 'z': c0, c1 = [cx, cy, h0], [cx, cy, h1]
        elif axis == 'y': c0, c1 = [cx, h0, cz], [cx, h1, cz]
        else: c0, c1 = [h0, cy, cz], [h1, cy, cz]
        t += [[c0, p1, p0], [c1, p3, p2]]
    T = np.array(t, float)
    ctr = np.array({'z': [cx, cy, (h0 + h1) / 2], 'y': [cx, (h0 + h1) / 2, cz], 'x': [(h0 + h1) / 2, cy, cz]}[axis])
    return orient(T, ctr)

H = 26.5          # tilt axis height above deck top (Z=0)
TT = 4.5          # turntable top
cols = dict(deck=(185, 183, 175), turn=(90, 190, 160), servo=(95, 140, 210), shroud=(170, 150, 225),
            lens=(70, 70, 80), bearing=(230, 175, 70), ribbon=(235, 130, 60), ir=(215, 80, 80), horn=(225, 225, 215))
static, tilting = [], []
# deck with pan-servo cutout and ribbon slot
static += [(box(-50, 46, -40, 40, -3, 0), 'deck_placeholder')]
static = []
for b in [box(-56, -44, -40, 40, -3, 0), box(-36, -18, -40, 40, -3, 0), box(-44, -36, -40, -9, -3, 0), box(-44, -36, 9, 40, -3, 0),
          box(7, 46, -40, 40, -3, 0), box(-18, 7, -40, -7, -3, 0), box(-18, 7, 7, 40, -3, 0)]:
    static.append((b, cols['deck']))
# pan servo under deck (MG90D), output at origin
static += [(box(-16.9, 5.9, -6.1, 6.1, -24.3, -1.8), cols['servo']), (box(-21.6, 10.6, -6.1, 6.1, -11, -8.5), cols['servo']),
           (cyl(0, 0, 0, 3, 'z', -1.8, 2.5), cols['servo'])]
# pan slide ring + turntable
static += [(cyl(0, 0, 0, 33, 'z', 0, 0.5), cols['bearing']), (cyl(0, 0, 0, 35, 'z', 0.5, TT), cols['turn'])]
# tilt servo tower (+Y side): mounting plate + gusset + servo lying with shaft along -Y
static += [(box(-9, 9, 29.5, 32.5, TT, H + 13), cols['turn']), (box(-9, 9, 19.5, 32.5, TT, TT + 3), cols['turn']),
           (box(-6.1, 6.1, 20.5, 43, H - 16.9, H + 5.9), cols['servo']), (box(-6.1, 6.1, 26.5, 29, H - 21.6, H + 10.6), cols['servo']),
           (cyl(0, 0, H, 3, 'y', 18.5, 20.5), cols['servo'])]
# bearing upright (-Y side) with 688 boss
static += [(box(-9, 9, -22.5, -19.5, TT, H), cols['turn']), (cyl(0, 0, H, 10, 'y', -24.5, -19.5), cols['turn']),
           (cyl(0, 0, H, 8, 'y', -24.7, -24.5), cols['bearing']), (box(-9, 9, -22.5, -19.5, TT, TT + 3), cols['turn'])]
# IR headlights on deck front
for s in (-1, 1):
    static += [(box(36, 44, s * 28 - 6, s * 28 + 6, 0, 10), cols['deck']), (cyl(0, s * 28, 5, 4.5, 'x', 44, 45), cols['ir'])]
# ribbon: fixed part (deck slot drop)
static += [(box(-40.3, -39.7, -8, 8, -14, 5.2), cols['ribbon'])]
# tilting: camera block centred on axis, lens, hubs, horn, ribbon exit loop
tilting += [(box(-8, 8, -18, 18, H - 18, H + 18), cols['shroud']), (cyl(0, 0, H - 1, 8, 'x', 8, 10), cols['shroud']),
            (cyl(0, 0, H - 1, 6, 'x', 10, 17), cols['lens']), (cyl(0, 0, H, 5, 'y', 18, 19.5), cols['horn']),
            (cyl(0, 0, H, 4, 'y', -19.5, -18), cols['shroud']), (box(-10, -8, -12, -8, H + 12, H + 16), cols['shroud']),
            (box(-6.3, -5.7, -8, 8, H - 23, H - 18), cols['ribbon'])]
static += [(box(-39.7, -6.3, -8, 8, 4.6, 5.2), cols['ribbon'])]

def tilt_mesh(T, deg):
    t = np.radians(deg); out = T.copy(); x = T[:, :, 0]; z = T[:, :, 2] - H
    out[:, :, 0] = x * np.cos(t) + z * np.sin(t); out[:, :, 2] = H - x * np.sin(t) + z * np.cos(t)
    return out

def project(pt, yaw, pitch, size, center, ext):
    R = rot(yaw, pitch); P = (np.array(pt) - center) @ R.T; sc = size / (2 * ext)
    return size / 2 + P[0] * sc, size / 2 - P[2] * sc

center = np.array([-2.0, 2.0, 12.0]); ext = 56.0; size = 900
def scene(deg): return static + [(tilt_mesh(m, deg), c) for m, c in tilting]
tiles = []
calls = [(1, (0, -10, H + 18)), (2, (0, 43, H + 2)), (3, (0, -24.7, H + 6)), (4, (22, -26, 2.5)), (5, (-10, 0, -20)), (6, (-22, 0, 5.2)), (7, (44, 28, 10))]
for yaw, pitch, lbl, show in [(215, 24, 'Concept: iso front', [1, 2, 4, 7]), (145, 24, 'iso front, other side', [1, 2, 6, 7]),
                              (35, -28, 'from below', [3, 5, 6])]:
    im = zrender(scene(0), yaw, pitch, size=size, label=lbl, center=center, ext=ext)
    d = ImageDraw.Draw(im)
    for num, pt in calls:
        if num not in show: continue
        if pitch < 0 and num == 6: pt = (-40, 0, -8)
        if pitch < 0 and num == 3: pt = (0, -24.7, H - 4)
        x, y = project(pt, yaw, pitch, size, center, ext)
        d.line([(x, y), (x + 26, y - 26)], fill=(40, 40, 40), width=2)
        d.ellipse([x + 20, y - 46, x + 46, y - 20], fill=(255, 255, 255), outline=(40, 40, 40), width=2)
        d.text((x + 29, y - 39), str(num), fill=(20, 20, 20))
    tiles.append(im)
sv = []
for deg in (0, 30):
    im = zrender(scene(deg), 0, 0, size=size, label=f'side view, tilt {deg} deg down (camera faces right)', center=center, ext=ext)
    d = ImageDraw.Draw(im); sc = size / (2 * ext)
    ax = (size / 2 + (0 - center[0]) * sc, size / 2 - (H - center[2]) * sc)
    d.ellipse([ax[0] - 5, ax[1] - 5, ax[0] + 5, ax[1] + 5], outline=(200, 40, 40), width=2)
    rr = 19.7 * sc
    d.ellipse([ax[0] - rr, ax[1] - rr, ax[0] + rr, ax[1] + rr], outline=(200, 40, 40), width=1)
    d.text((ax[0] + rr + 6, ax[1] - 8), 'swing radius 19.7 mm', fill=(200, 40, 40))
    sv.append(im)
w = size
sheet = Image.new('RGB', (w * 3, w * 2), 'white')
for i, im in enumerate(tiles): sheet.paste(im, (i * w, 0))
sheet.paste(sv[0], (0, w)); sheet.paste(sv[1], (w, w))
# legend tile
lg = Image.new('RGB', (w, w), (246, 245, 241)); d = ImageDraw.Draw(lg)
items = ['1  Camera block centred ON the tilt axis', '2  Tilt servo on a side tower, stock horn in block hub', '3  688 bearing idler on the other side',
         '4  Turntable on a slide ring: carries head weight', '5  Pan servo under deck, horn captured in turntable', '6  Ribbon: slack loop off the back, into a deck slot',
         '7  IR pods as headlights on the deck']
for i, s in enumerate(items): d.text((40, 60 + i * 44), s, fill=(30, 30, 30))
for i, (k, c) in enumerate([('deck', 'deck'), ('turn', 'printed structure'), ('servo', 'MG90D servos'), ('shroud', 'camera block'), ('bearing', 'bearings / slide ring'), ('ribbon', 'CSI ribbon'), ('ir', 'IR pods')]):
    y = 420 + i * 40; d.rectangle([40, y, 64, y + 24], fill=cols[k]); d.text((80, y + 6), c, fill=(30, 30, 30))
sheet.paste(lg, (2 * w, w))
sheet.save(os.path.join(D, 'concept_pantilt.png'))
print('ok')
