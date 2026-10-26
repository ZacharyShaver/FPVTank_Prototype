import struct, sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

def load_stl(path):
    data = open(path, 'rb').read()
    n = struct.unpack('<I', data[80:84])[0]
    if 84 + n * 50 == len(data):
        arr = np.frombuffer(data[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))
        return arr['v'].astype(np.float64)
    tris, cur = [], []
    for line in data.decode(errors='ignore').splitlines():
        p = line.split()
        if p and p[0] == 'vertex':
            cur.append([float(x) for x in p[1:4]])
            if len(cur) == 3:
                tris.append(cur); cur = []
    return np.array(tris)

def stats(name, V):
    lo, hi = V.reshape(-1, 3).min(0), V.reshape(-1, 3).max(0)
    e1, e2 = V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]
    cr = np.cross(e1, e2)
    area = np.linalg.norm(cr, axis=1) / 2
    nrm = cr / np.maximum(np.linalg.norm(cr, axis=1, keepdims=True), 1e-12)
    vol = np.einsum('ij,ij->i', V[:, 0], np.cross(V[:, 1], V[:, 2])).sum() / 6
    # edge manifoldness
    q = np.round(V, 4)
    edges = {}
    for t in q:
        for a, b in ((0, 1), (1, 2), (2, 0)):
            k = tuple(sorted((tuple(t[a]), tuple(t[b]))))
            edges[k] = edges.get(k, 0) + 1
    bad = sum(1 for c in edges.values() if c != 2)
    print(f'== {name}: {len(V)} tris, bbox {lo.round(2)} -> {hi.round(2)}, size {(hi-lo).round(2)} mm')
    print(f'   volume {abs(vol)/1000:.2f} cm^3, surface {area.sum()/100:.1f} cm^2, non-manifold edges {bad}')
    for ax, lbl in enumerate('XYZ'):
        for s in (-1, 1):
            m = nrm[:, ax] * s > 0.999
            if area[m].sum() > 1:
                pos = V[m][:, :, ax].mean(1)
                vals, cnt = np.unique(np.round(pos, 1), return_counts=True)
                w = {v: area[m][np.round(pos, 1) == v].sum() for v in vals}
                top = sorted(w.items(), key=lambda kv: -kv[1])[:6]
                print(f'   {"+" if s>0 else "-"}{lbl} planar faces @', ', '.join(f'{k:.1f}({v:.0f}mm2)' for k, v in top))
    return lo, hi, nrm, area

def rot(yaw, pitch):
    y, p = np.radians(yaw), np.radians(pitch)
    Rz = np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    return Rx @ Rz

def render(V, yaw, pitch, size, color, label):
    c = V.reshape(-1, 3)
    c = (c.min(0) + c.max(0)) / 2
    R = rot(yaw, pitch)
    # view: camera looks along +Y in rotated frame; screen x = X, screen y = Z
    P = (V - c) @ R.T
    e1, e2 = P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]
    n = np.cross(e1, e2)
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    ext = np.abs(P[:, :, [0, 2]]).max() * 1.1
    S = 4  # supersample
    W = size * S
    sc = W / (2 * ext)
    depth = P[:, :, 1].mean(1)
    light = np.array([-0.4, -0.8, 0.55]); light /= np.linalg.norm(light)
    view = np.array([0, -1, 0])
    img = Image.new('RGB', (W, W), (246, 245, 241))
    d = ImageDraw.Draw(img)
    order = np.argsort(-depth)  # far first (larger y = farther)
    col = np.array(color, float)
    for i in order:
        ni = n[i]
        facing = ni @ view
        diff = abs(ni @ light)
        k = 0.35 + 0.65 * diff
        if facing < 0:
            k *= 0.55  # back face seen (shouldn't normally show)
        rgb = tuple(int(min(255, v)) for v in col * k)
        pts = [(W / 2 + p[0] * sc, W / 2 - p[2] * sc) for p in P[i]]
        d.polygon(pts, fill=rgb, outline=rgb)
    img = img.resize((size, size), Image.LANCZOS)
    dr = ImageDraw.Draw(img)
    dr.text((10, 8), label, fill=(60, 60, 60))
    # scale bar 10mm
    px10 = 10 * sc / S
    dr.line([(10, size - 14), (10 + px10, size - 14)], fill=(40, 40, 40), width=3)
    dr.text((14 + px10, size - 22), '10 mm', fill=(40, 40, 40))
    return img

out = sys.argv[1]
parts = []
for path, name, color in [
    (os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test-print-2', 'z_mount_bottom.stl'), 'bottom', (120, 170, 230)),
    (os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test-print-2', 'z_mount_top.stl'), 'top', (235, 150, 90)),
]:
    V = load_stl(path)
    stats(name, V)
    views = [(30, 25, 'iso front-right'), (210, 25, 'iso back-left'), (120, -30, 'iso from below'),
             (0, 0, 'front (-Y)'), (90, 0, 'side (+X)'), (0, 90, 'top (+Z)'), (0, -90, 'bottom (-Z)'), (300, 55, 'iso high')]
    tiles = [render(V, y, p, 520, color, f'{name}: {l}') for y, p, l in views]
    sheet = Image.new('RGB', (520 * 4, 520 * 2), 'white')
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 4) * 520, (i // 4) * 520))
    sheet.save(os.path.join(out, f'{name}_sheet.png'))
    parts.append((V, color))
