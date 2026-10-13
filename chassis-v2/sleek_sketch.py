"""Rough sketches (2026-10-12): the Trainer body's insides and today's head under a uniform curved shell, after the
original FPV Rover v2 body (reference/fpv-rover-v2/body-rover-v13.stl: a pill, a stadium in plan, 207 x 110, 50 tall).
Zach: "a more uniform curved body like the original design i like that a lot it looked sleek", "use the pill shaped
grey for reference". Looks only: no fit checks, nothing here prints.

Three shells, all a pill in plan as wide as the tub (131.5), the nose's half-circle centred on the pan axis (the turret is
the nose) and the tail's on the rear axle:
  1  pill tub: straight walls and a flat top, as the original
  2  pill, crowned: the same outline, the top domed with big round shoulders
  3  two pills: the original's 50 tall pill tub with a narrower pill deck on top, the head in the lower pill's nose

    python chassis-v2/sleek_sketch.py      # needs out/_nose.pkl (nose.py) -> out/sleek_sketch.png
"""
import os, sys, pickle
import numpy as np
from skimage import measure
HERE = os.path.dirname(os.path.abspath(__file__)); PROTO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROTO, 'tools'))
from zr import zrender
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(HERE, 'out')
D = pickle.load(open(os.path.join(OUT, '_nose.pkl'), 'rb'))
HX, YC = 115.0, 3.75                # the pan axis, world X; the centre line
R0 = (69.5 + 62.0) / 2              # 65.75: half the tub's width
XN, XT = HX, -93.0                  # the half-circles' centres: the pan axis, the rear axle
Z0, ZDECK = 7.4, 66.0               # the bays' floor, the turret deck (rugged.TDECK)


def stadium(x, y, r):
    """2D signed distance to a pill in plan, its half-circles centred at XT and XN"""
    xc = np.clip(x, XT, XN)
    return np.hypot(x - xc, y - YC) - r


def rounded_slab(d2, z, z0, z1, rr):
    """extrude a 2D distance from z0 to z1 with its top edge rounded rr"""
    q = np.stack([d2 + rr, z - (z1 - rr)], 0)
    top = np.where((q[0] > 0) & (q[1] > 0), np.hypot(q[0], q[1]) - rr, np.maximum(d2, z - z1))
    return np.maximum(top, z0 - z)


def shell(n, P):
    x, y, z = P
    turret = np.hypot(x - HX, y - YC) - 33.0                                           # the head drops in here
    if n == 1:
        s = rounded_slab(stadium(x, y, R0), z, Z0, ZDECK, 5.0)
    elif n == 2:
        # the top falls from 78 on the centre line to the wall's 46 along a quarter-ellipse; flat at the turret
        d = stadium(x, y, R0); t = np.clip(-d / 38.0, 0, 1)
        top = 46.0 + 32.0 * np.sqrt(1 - (1 - t) ** 2)
        top = np.where(np.hypot(x - HX, y - YC) < 44, np.minimum(top, ZDECK), top)
        s = np.maximum(np.maximum(d, z - top), Z0 - z)
    else:
        low = rounded_slab(stadium(x, y, R0), z, Z0, 57.4, 6.0)
        hi = rounded_slab(np.maximum(stadium(x, y, 46.0), x - (HX - 40.0)), z, 50.0, 80.0, 12.0)   # stops behind the head
        s = np.minimum(low, hi)
    return np.maximum(s, -np.maximum(turret, ZDECK - 6.0 - z))


def mesh(n, step=1.5):
    lo, hi = np.array([XT - R0 - 3, YC - R0 - 3, Z0 - 2]), np.array([XN + R0 + 3, YC + R0 + 3, 90.0])
    g = [np.arange(lo[i], hi[i], step) for i in range(3)]
    X, Y, Z = np.meshgrid(*g, indexing='ij')
    v, f, _, _ = measure.marching_cubes(shell(n, (X, Y, Z)), 0.0, spacing=(step,) * 3)
    return (v + lo)[f]


HEAD = ('well', 'bay', 'drum', 'bearing', 'fork', 'ball_plus', 'ball_minus', 'camera', 'gear_in', 'servo')
HCOL = {'well': (163, 168, 162), 'bay': (163, 168, 162), 'drum': (62, 156, 143), 'bearing': (154, 160, 170),
        'fork': (216, 195, 154), 'ball_plus': (127, 156, 184), 'ball_minus': (147, 170, 194), 'camera': (45, 125, 75),
        'gear_in': (79, 174, 158), 'servo': (90, 100, 112)}
GREY = (196, 200, 204)
NAMES = {1: 'Pill tub: straight walls, flat top (as the original)', 2: 'Pill, crowned: domed top, round shoulders',
         3: 'Two pills: the original 50 tall tub, a pill deck on top'}

if __name__ == '__main__':
    common = [(D['P']['A'][k], HCOL[k]) for k in HEAD]
    common += [(v['t'], (40, 40, 44) if k.startswith('tire') else (110, 112, 116)) for k, v in D['M'].items() if v['grp'] == 'legs']
    rows = []
    for n in (1, 2, 3):
        m = [(mesh(n), GREY)] + common
        views = [zrender(m, 38, 24, size=560), zrender(m, 0, 2, size=560), zrender(m, 0, 88, size=560)]   # 3/4, side, top
        row = Image.new('RGB', (1680, 560 + 40), (255, 255, 255))
        for i, im in enumerate(views):
            row.paste(im, (560 * i, 40))
        ImageDraw.Draw(row).text((16, 10), '%d. %s' % (n, NAMES[n]), fill=(30, 30, 30), font=ImageFont.load_default(size=22))
        rows.append(row); print('sketch', n)
    sheet = Image.new('RGB', (1680, sum(r.height for r in rows)), (255, 255, 255))
    yy = 0
    for r in rows:
        sheet.paste(r, (0, yy)); yy += r.height
    p = os.path.join(OUT, 'sleek_sketch.png'); sheet.save(p); print('wrote', p)
