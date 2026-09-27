import sys, os
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from render_stl import load_stl, rot  # noqa (re-runs stats; fine)

OUT = sys.argv[1]
B = load_stl(r'C:\Users\<usr>\Downloads\TEST-PRINT-2_Configuration 1_z_mount_bottom.stl')
T = load_stl(r'C:\Users\<usr>\Downloads\TEST-PRINT-2_Configuration 1_z_mount_top.stl')

def zrender(meshes, yaw, pitch, size=700, label='', center=None, ext=None):
    allv = np.concatenate([m.reshape(-1, 3) for m, _ in meshes])
    c = (allv.min(0) + allv.max(0)) / 2 if center is None else center
    R = rot(yaw, pitch)
    Ps = [((m - c) @ R.T, col) for m, col in meshes]
    if ext is None:
        ext = max(np.abs(P[:, :, [0, 2]]).max() for P, _ in Ps) * 1.12
    sc = size / (2 * ext)
    zb = np.full((size, size), np.inf)
    img = np.full((size, size, 3), 246.0)
    light = np.array([-0.45, -0.75, 0.5]); light /= np.linalg.norm(light)
    for P, col in Ps:
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        sx = size / 2 + P[:, :, 0] * sc
        sy = size / 2 - P[:, :, 2] * sc
        dz = P[:, :, 1]
        shade = 0.30 + 0.55 * np.clip(n @ light, 0, 1) + 0.15 * np.abs(n[:, 1])
        for i in range(len(P)):
            x0, x1 = int(max(0, np.floor(sx[i].min()))), int(min(size - 1, np.ceil(sx[i].max())))
            y0, y1 = int(max(0, np.floor(sy[i].min()))), int(min(size - 1, np.ceil(sy[i].max())))
            if x1 < x0 or y1 < y0:
                continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, bx, cx), (ay, by, cy) = sx[i], sy[i]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9:
                continue
            w0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
            w1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
            w2 = 1 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any():
                continue
            z = w0 * dz[i, 0] + w1 * dz[i, 1] + w2 * dz[i, 2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            upd = m & (z < sub)
            sub[upd] = z[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = np.array(col) * shade[i]
    # edge/outline pass: depth discontinuities
    zf = np.where(np.isinf(zb), 1e3, zb)
    edge = (np.abs(np.diff(zf, axis=0, prepend=zf[:1])) > 0.6) | (np.abs(np.diff(zf, axis=1, prepend=zf[:, :1])) > 0.6)
    img[edge] *= 0.35
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.text((10, 8), label, fill=(50, 50, 50))
    px10 = 10 * sc
    d.line([(10, size - 14), (10 + px10, size - 14)], fill=(30, 30, 30), width=3)
    d.text((14 + px10, size - 22), '10 mm', fill=(30, 30, 30))
    return im

def section(meshes, axis, value, size=700, label='', ext=None, center=None):
    """Slice all meshes with plane axis=value; draw segments. Returns image."""
    ax2 = [a for a in range(3) if a != axis]
    allv = np.concatenate([m.reshape(-1, 3) for m, _ in meshes])
    c = (allv.min(0) + allv.max(0)) / 2 if center is None else center
    if ext is None:
        ext = max((allv.max(0) - allv.min(0))[ax2]) / 2 * 1.15
    sc = size / (2 * ext)
    im = Image.new('RGB', (size, size), (250, 250, 248))
    d = ImageDraw.Draw(im)
    # grid 1mm / 5mm
    for g in np.arange(-60, 61, 1.0):
        colg = (215, 215, 212) if g % 5 == 0 else (236, 236, 233)
        p = size / 2 + g * sc
        d.line([(p, 0), (p, size)], fill=colg)
        d.line([(0, p), (size, p)], fill=colg)
    for M, col in meshes:
        s = M[:, :, axis] - value
        for t, ss in zip(M, s):
            pts = []
            for a, b in ((0, 1), (1, 2), (2, 0)):
                if (ss[a] > 0) != (ss[b] > 0):
                    f = ss[a] / (ss[a] - ss[b])
                    pts.append(t[a] + f * (t[b] - t[a]))
            if len(pts) == 2:
                q = [(size / 2 + (p[ax2[0]] - c[ax2[0]]) * sc, size / 2 - (p[ax2[1]] - c[ax2[1]]) * sc) for p in pts]
                d.line(q, fill=tuple(int(v * 0.7) for v in col), width=3)
    names = 'XYZ'
    d.text((10, 8), f'{label}  section {names[axis]}={value:.1f}  (h:{names[ax2[0]]}, v:{names[ax2[1]]}, grid 1mm/5mm)', fill=(40, 40, 40))
    return im

BLUE, ORANGE = (120, 170, 230), (235, 150, 90)
tile = lambda ims, cols: _sheet(ims, cols)
def _sheet(ims, cols):
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    s = Image.new('RGB', (w * cols, h * rows), 'white')
    for i, im in enumerate(ims):
        s.paste(im, ((i % cols) * w, (i // cols) * h))
    return s

which = sys.argv[2]
if which == 'views':
    both = [(B, BLUE), (T, ORANGE)]
    ims = [zrender(both, 35, 25, label='ASSEMBLED iso'), zrender(both, 215, 25, label='ASSEMBLED iso back'),
           zrender(both, 125, -35, label='ASSEMBLED from below'), zrender(both, 0, 0, label='ASSEMBLED front -Y')]
    _sheet(ims, 2).save(os.path.join(OUT, 'assembled.png'))
    for M, col, nm in [(B, BLUE, 'bottom'), (T, ORANGE, 'top')]:
        ims = [zrender([(M, col)], 35, 25, label=f'{nm} iso'), zrender([(M, col)], 215, 25, label=f'{nm} iso back'),
               zrender([(M, col)], 215, -35, label=f'{nm} iso below-back'), zrender([(M, col)], 35, -35, label=f'{nm} iso below-front'),
               zrender([(M, col)], 180, 0, label=f'{nm} from +Y'), zrender([(M, col)], 0, 0, label=f'{nm} from -Y')]
        _sheet(ims, 3).save(os.path.join(OUT, f'{nm}_z.png'))
elif which == 'sections':
    both = [(B, BLUE), (T, ORANGE)]
    allv = np.concatenate([B.reshape(-1, 3), T.reshape(-1, 3)])
    lo, hi = allv.min(0), allv.max(0); mid = (lo + hi) / 2
    ims = [section(both, 0, mid[0], label='asm'), section(both, 0, 101.2, label='asm'),
           section(both, 2, mid[2], label='asm'), section(both, 2, 80.9, label='asm'),
           section(both, 1, 10.0, label='asm'), section(both, 1, -9.0, label='asm')]
    _sheet(ims, 3).save(os.path.join(OUT, 'sections.png'))
