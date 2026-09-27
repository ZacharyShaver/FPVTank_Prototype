"""Minimal dependency-free STL viewer: binary/ASCII STL -> shaded PNG.

numpy only. Software z-buffer rasterizer + hand-rolled PNG encoder, because the
dev machine has no matplotlib/PIL.
"""
import os
import struct
import sys
import zlib

import numpy as np


# ---------------------------------------------------------------- STL loading

def load_stl(path):
    with open(path, "rb") as f:
        data = f.read()
    # Binary STL: 80-byte header + uint32 count + 50 bytes per triangle.
    if len(data) >= 84:
        n = struct.unpack("<I", data[80:84])[0]
        if 84 + n * 50 == len(data):
            raw = np.frombuffer(data[84:], dtype=np.uint8).reshape(n, 50)
            verts = raw[:, 12:48].copy().view("<f4").reshape(n, 3, 3)
            return np.asarray(verts, dtype=np.float64)
    # Fall back to ASCII.
    text = data.decode("ascii", "replace")
    pts = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("vertex"):
            pts.append([float(v) for v in s.split()[1:4]])
    tris = np.asarray(pts, dtype=np.float64)
    return tris.reshape(-1, 3, 3)


# ------------------------------------------------------------------ rendering

def view_basis(azim_deg, elev_deg):
    a, e = np.radians(azim_deg), np.radians(elev_deg)
    fwd = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    right = np.cross([0.0, 0.0, 1.0], fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    return right, up, fwd


def render(tris, width, height, azim, elev, ss=3,
           part_rgb=(0.62, 0.68, 0.76), bg_rgb=(0.97, 0.97, 0.98)):
    W, H = width * ss, height * ss
    right, up, fwd = view_basis(azim, elev)

    center = 0.5 * (tris.reshape(-1, 3).min(0) + tris.reshape(-1, 3).max(0))
    p = tris - center
    sx = p @ right
    sy = p @ up
    sz = p @ fwd

    span = max(sx.max() - sx.min(), sy.max() - sy.min(), 1e-9)
    scale = 0.86 * min(W, H) / span
    px = sx * scale + W / 2.0
    py = H / 2.0 - sy * scale

    # Flat shading from geometric normals, two-sided so flipped facets still read.
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    nrm = np.cross(e1, e2)
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm = nrm / np.where(ln == 0, 1.0, ln)
    key = right * 0.45 + up * 0.55 + fwd * 0.70
    key /= np.linalg.norm(key)
    fill = -right * 0.6 + fwd * 0.5
    fill /= np.linalg.norm(fill)
    shade = (0.30
             + 0.62 * np.abs(nrm @ key)
             + 0.16 * np.abs(nrm @ fill))
    shade = np.clip(shade, 0.0, 1.25)

    color = np.zeros((H, W, 3), dtype=np.float32)
    color[:] = bg_rgb
    zbuf = np.full((H, W), -np.inf, dtype=np.float64)

    x0 = np.clip(np.floor(px.min(1)).astype(int), 0, W - 1)
    x1 = np.clip(np.ceil(px.max(1)).astype(int), 0, W - 1)
    y0 = np.clip(np.floor(py.min(1)).astype(int), 0, H - 1)
    y1 = np.clip(np.ceil(py.max(1)).astype(int), 0, H - 1)

    base = np.asarray(part_rgb, dtype=np.float32)
    for i in range(tris.shape[0]):
        ix0, ix1, iy0, iy1 = x0[i], x1[i], y0[i], y1[i]
        if ix1 < ix0 or iy1 < iy0:
            continue
        ax, ay = px[i, 0], py[i, 0]
        bx, by = px[i, 1], py[i, 1]
        cx, cy = px[i, 2], py[i, 2]
        area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
        if abs(area) < 1e-12:
            continue
        xs = np.arange(ix0, ix1 + 1) + 0.5
        ys = np.arange(iy0, iy1 + 1) + 0.5
        gx = xs[None, :]
        gy = ys[:, None]
        w0 = ((bx - ax) * (gy - ay) - (by - ay) * (gx - ax)) / area
        w1 = ((cx - bx) * (gy - by) - (cy - by) * (gx - bx)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        # Barycentrics above are (w1_for_C, w0_for_A, ...) -> depth interp below.
        depth = w1 * sz[i, 0] + w2 * sz[i, 1] + w0 * sz[i, 2]
        sub_z = zbuf[iy0:iy1 + 1, ix0:ix1 + 1]
        win = inside & (depth > sub_z)
        if not win.any():
            continue
        sub_z[win] = depth[win]
        color[iy0:iy1 + 1, ix0:ix1 + 1][win] = base * shade[i]

    color = np.clip(color, 0.0, 1.0)
    img = (color * 255.0 + 0.5).astype(np.uint8)
    img = img.reshape(height, ss, width, ss, 3).mean(axis=(1, 3))
    return img.astype(np.uint8)


def write_png(path, img):
    h, w, _ = img.shape
    # Each scanline is prefixed with filter type 0 (None).
    rows = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(tag, payload):
        c = struct.pack(">I", len(payload)) + tag + payload
        return c + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(rows, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def hstack_pad(images, gap=14, bg=(247, 247, 250)):
    h = max(im.shape[0] for im in images)
    w = sum(im.shape[1] for im in images) + gap * (len(images) - 1)
    out = np.zeros((h, w, 3), dtype=np.uint8)
    out[:] = bg
    x = 0
    for im in images:
        out[:im.shape[0], x:x + im.shape[1]] = im
        x += im.shape[1] + gap
    return out


# ----------------------------------------------------------------------- main

def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    files = sorted(f for f in os.listdir(src) if f.lower().endswith(".stl"))
    stats = []
    for name in files:
        tris = load_stl(os.path.join(src, name))
        pts = tris.reshape(-1, 3)
        lo, hi = pts.min(0), pts.max(0)
        views = [render(tris, 460, 380, azim=-55, elev=26),
                 render(tris, 460, 380, azim=125, elev=26),
                 render(tris, 460, 380, azim=-90, elev=89.9)]
        out = os.path.join(dst, os.path.splitext(name)[0] + ".png")
        write_png(out, hstack_pad(views))
        rec = dict(file=name, tris=int(tris.shape[0]),
                   size=[round(float(v), 1) for v in (hi - lo)])
        stats.append(rec)
        print(f"{name}: {rec['tris']} tris, "
              f"{rec['size'][0]} x {rec['size'][1]} x {rec['size'][2]} mm",
              flush=True)
    import json
    with open(os.path.join(dst, "_stats.json"), "w") as f:
        json.dump(stats, f, indent=1)


if __name__ == "__main__":
    main()
