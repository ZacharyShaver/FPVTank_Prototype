"""Draw each STEP solid beside the OBJ mesh it replaces, same view and scale.

An eyeball check, nothing more -- the numbers in tree_parts_b_step.py are what actually
verify the rebuild. This is here because a silhouette catches the kind of gross mistake a
metric can be talked out of, and because looking at it is cheap.

    python render_step_compare.py        -> ../tree-parts-b/step/step_vs_obj.png
"""
import os
import numpy as np
from PIL import Image, ImageDraw
import cadquery as cq

D = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(D, '..', 'tree-parts-b')
PARTS = ['post', 'axle', 'cap_minus', 'ball_plus', 'ball_minus']
W = H = 300


def tris_from_step(path):
    s = cq.importers.importStep(path).val()
    v, t = s.tessellate(0.03)
    return np.array([[q.x, q.y, q.z] for q in v])[np.array(t)]


def tris_from_obj(path):
    V, F = [], []
    for line in open(path):
        a = line.split()
        if not a:
            continue
        if a[0] == 'v':
            V.append([float(x) for x in a[1:4]])
        elif a[0] == 'f':
            idx = [int(x.split('/')[0]) - 1 for x in a[1:]]
            F += [[idx[0], idx[k], idx[k + 1]] for k in range(1, len(idx) - 1)]
    return np.array(V)[np.array(F)]


def render(T, lo, hi, title, sub):
    img = Image.new('RGB', (W, H), (250, 250, 248))
    d = ImageDraw.Draw(img)
    az, el = np.radians(38), np.radians(24)
    M = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]]) @ \
        np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    P = (T - (lo + hi) / 2) @ M.T
    sc = (min(W, H) - 60) / max((hi - lo).max(), 1e-6)
    xy = P[:, :, [0, 2]] * sc + np.array([W / 2, H / 2 + 10])
    xy[:, :, 1] = H - xy[:, :, 1]
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    L = np.array([0.45, -0.70, 0.55])
    L = L / np.linalg.norm(L)
    sh = 0.30 + 0.70 * np.abs(n @ L)        # two-sided + ambient, or it renders as a blob
    for i in np.argsort(P[:, :, 1].mean(1)):
        g = int(30 + 215 * sh[i])
        d.polygon([tuple(q) for q in xy[i]], fill=(int(g * .80), int(g * .86), int(g * .95)))
    d.text((10, 8), title, fill=(15, 15, 15))
    d.text((10, 22), sub, fill=(110, 110, 110))
    return img


def main():
    rows = []
    for name in PARTS:
        sp = os.path.join(OUT, 'step', name + '.step')
        op = os.path.join(OUT, 'fusion', name + '.obj')
        if not (os.path.exists(sp) and os.path.exists(op)):
            print('  skipping %s (missing STEP or OBJ)' % name)
            continue
        ts, to = tris_from_step(sp), tris_from_obj(op)
        allv = np.vstack([ts.reshape(-1, 3), to.reshape(-1, 3)])
        lo, hi = allv.min(0), allv.max(0)
        nf = len(cq.importers.importStep(sp).faces().vals())
        row = Image.new('RGB', (W * 2 + 6, H), (255, 255, 255))
        row.paste(render(ts, lo, hi, name + '  [STEP solid]', '%d faces' % nf), (0, 0))
        row.paste(render(to, lo, hi, name + '  [OBJ mesh, old]', '%d triangles' % len(to)),
                  (W + 6, 0))
        rows.append(row)
    if not rows:
        print('  nothing to render')
        return False
    out = Image.new('RGB', (W * 2 + 6, (H + 6) * len(rows)), (255, 255, 255))
    for i, r in enumerate(rows):
        out.paste(r, (0, i * (H + 6)))
    p = os.path.join(OUT, 'step', 'step_vs_obj.png')
    out.save(p)
    print('  wrote %s  %s' % (p, out.size))
    return True


if __name__ == '__main__':
    main()
