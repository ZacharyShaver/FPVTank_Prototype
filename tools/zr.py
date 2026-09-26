"""Z-buffer renderer (adapted from generators/render2.py): several meshes, one colour each."""
import numpy as np
from PIL import Image, ImageDraw
def rot(yaw, pitch):
    y, p = np.radians(yaw), np.radians(pitch)
    Rz = np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    return Rx @ Rz
def zrender(meshes, yaw, pitch, size=700, label='', center=None, ext=None, clip=None):
    """meshes: [(T (n,3,3), rgb 0-255)]. View looks along rotated +Y. clip: fn(centroids)->keep mask"""
    if clip is not None:
        meshes = [(m[clip(m.mean(1))], c) for m, c in meshes]
    allv = np.concatenate([m.reshape(-1, 3) for m, _ in meshes])
    c = (allv.min(0) + allv.max(0)) / 2 if center is None else np.asarray(center, float)
    R = rot(yaw, pitch)
    Ps = [((m - c) @ R.T, col) for m, col in meshes]
    if ext is None:
        ext = max(np.abs(P[:, :, [0, 2]]).max() for P, _ in Ps) * 1.08
    sc = size / (2 * ext)
    zb = np.full((size, size), np.inf); img = np.full((size, size, 3), 248.0)
    light = np.array([-0.45, -0.75, 0.5]); light /= np.linalg.norm(light)
    for P, col in Ps:
        n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        sx = size / 2 + P[:, :, 0] * sc; sy = size / 2 - P[:, :, 2] * sc; dz = P[:, :, 1]
        shade = 0.30 + 0.55 * np.abs(n @ light) + 0.15 * np.abs(n[:, 1])
        for i in range(len(P)):
            x0, x1 = int(max(0, np.floor(sx[i].min()))), int(min(size - 1, np.ceil(sx[i].max())))
            y0, y1 = int(max(0, np.floor(sy[i].min()))), int(min(size - 1, np.ceil(sy[i].max())))
            if x1 < x0 or y1 < y0: continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, bx, cx), (ay, by, cy) = sx[i], sy[i]
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9: continue
            w0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
            w1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
            w2 = 1 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any(): continue
            z = w0 * dz[i, 0] + w1 * dz[i, 1] + w2 * dz[i, 2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]; upd = m & (z < sub)
            sub[upd] = z[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = np.array(col, float) * shade[i]
    zf = np.where(np.isinf(zb), 1e3, zb)
    edge = (np.abs(np.diff(zf, axis=0, prepend=zf[:1])) > 0.5) | (np.abs(np.diff(zf, axis=1, prepend=zf[:, :1])) > 0.5)
    img[edge] *= 0.35
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im); d.text((10, 8), label, fill=(40, 40, 40))
    px10 = 10 * sc
    d.line([(10, size - 14), (10 + px10, size - 14)], fill=(30, 30, 30), width=3)
    d.text((14 + px10, size - 22), '10 mm', fill=(30, 30, 30))
    return im
if __name__ == '__main__':
    import config
    from probe import mesh
    TP = mesh('ball_plus')
    ims = [zrender([(TP, (205, 205, 212))], -90, 0, 520, 'ball_plus from the front (+Y right)', center=(0, 12, 52), ext=33),
           zrender([(TP, (205, 205, 212))], -60, 20, 520, 'from front-right-above', center=(0, 12, 52), ext=33),
           zrender([(TP, (205, 205, 212))], -90, 0, 520, 'front, zoom on the sliver', center=(27, 2, 64), ext=5)]
    W = Image.new('RGB', (520 * 3, 520), 'white')
    for i, im in enumerate(ims): W.paste(im, (520 * i, 0))
    W.save(config.out('front_z.png'))
