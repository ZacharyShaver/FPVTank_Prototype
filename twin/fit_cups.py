"""SUPERSEDED before printing (2026-11-03): Zach wanted the boxes the parts sit in inside the robot (twin/boxes.py), not a
test cup per part. Kept as a per-part size check.

Fit cups (2026-11-03): one open box per part the robot carries inside, at the size the sim gives it, so the real part
shows where the sim is wrong. The first print of the real twin: sizes first, layout next.

    python twin/fit_cups.py      # STLs (each cup, and the plate of all four) to twin/out/print/, picture to twin/out/fit_cups.png, checks and mesh report printed

Each cup is the sim's box for its part plus CLR a side: a RIM-high wall round the bottom, four corner posts exactly as
tall as the sim says the part is, and a floor that runs MARGIN past the box with a raised ring every 5 mm (double at 10
and 20), counted from the sim's box face. A part that won't drop in is bigger than the sim thinks; one standing over the
posts is taller; a plug or lead that sticks out reads straight off the rings. The sides are open above the rim, so
leads come out anywhere.

Sizes are gauges/body.parts(): the Trainer's parts, the ones every search design carries. Only the parts Zach owns get a
cup (HARDWARE.md in FPVTank_Control); the regulators, INA219, WiFi dongle, alarm and switches aren't bought yet.
SOURCE says where each size came from; * = a guess.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import config
import numpy as np
import cadquery as cq

OUT = config.TWIN_OUT
PRINT = os.path.join(OUT, 'fit-cups-superseded')
CLR, WALL, RIM, LEG, FLOOR, MARGIN = 0.3, 2.0, 3.0, 12.0, 1.4, 22.0   # mm; CLR a side (my pick*)
RINGS = (5, 10, 15, 20)                                                # from the sim's box face; 10 and 20 drawn double
ENGRAVE = 0.6

# cup: (the sim parts it holds, label, size override or None). X along the robot, Y across, Z up, as the sim stands them.
CUPS = {
    'pack': (('pack_L',), 'PACK', None),
    'esc': (('esc_L',), 'ESC', (45.0, 24.0, 34.0)),
    'pi': (('pi', 'hat', 'hailo'), 'PI5 STACK', None),
    'pca': (('pca',), 'PCA9685', None),
}
SOURCE = {
    'pack': "Zeee 2S 5200 on edge: Zach's model's box (LeftBattery.stl), 141 x 26 x 45.7",
    'esc': "INJORA ESC on edge: Zach's caliper 45 L x 34 W x 24 tall (2026-10-11). The sim still has 46 x 34 x 18*",
    'pi': "Pi 5 + active cooler (Zach's model) under the M.2 HAT+ on 16 mm* standoffs and the Hailo-8L: the stack's box",
    'pca': "PCA9685 at Adafruit's size*; his is a generic clone",
}


def sim_sizes():
    """the box each cup's parts fill in the sim, mm (X, Y, Z)"""
    sys.path.insert(0, config.GAUGES)
    import body as B
    C = B.parts()[0]
    out = {}
    for k, (keys, _, over) in CUPS.items():
        P = np.vstack([np.asarray(C[n], float) for n in keys])
        sim = np.ceil((P.max(0) - P.min(0)) * 10 - 1e-6) / 10                # up to 0.1, so a cup never undercuts the sim
        out[k] = dict(sim=sim, size=np.array(over if over else sim, float))
    return out


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane().box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cup(size, label):
    """the cup for a part of `size` (X, Y, Z), its box centred on the origin, sitting on the floor's top (Z FLOOR)"""
    L, W, H = size; a, b = L / 2 + CLR, W / 2 + CLR; A, B_ = L / 2 + MARGIN, W / 2 + MARGIN
    s = box(-A, A, -B_, B_, 0, FLOOR)
    s = s.union(box(-a - WALL, a + WALL, -b - WALL, b + WALL, FLOOR - 0.01, FLOOR + RIM).cut(box(-a, a, -b, b, FLOOR - 1, FLOOR + RIM + 1)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            xs = sorted((sx * (a - LEG + WALL), sx * (a + WALL))); ys = sorted((sy * b, sy * (b + WALL)))
            s = s.union(box(*xs, *ys, FLOOR - 0.01, FLOOR + H))
            xs = sorted((sx * a, sx * (a + WALL))); ys = sorted((sy * (b - LEG + WALL), sy * (b + WALL)))
            s = s.union(box(*xs, *ys, FLOOR - 0.01, FLOOR + H))
    for d in RINGS:                                                        # rings round the cup, d from the sim's face
        w = 1.2 if d % 10 == 0 else 0.6; o, i = d + w / 2, d - w / 2
        ring = box(-L / 2 - o, L / 2 + o, -W / 2 - o, W / 2 + o, FLOOR - 0.01, FLOOR + 0.6).cut(
            box(-L / 2 - i, L / 2 + i, -W / 2 - i, W / 2 + i, FLOOR - 1, FLOOR + 2))
        s = s.union(ring)
    txt = f'{label} {L:g} x {W:g} x {H:g}'
    t = (cq.Workplane().text(txt, 3.5, ENGRAVE + 1, kind='bold', halign='center', valign='center')
         .translate((0, -W / 2 - 12.8, FLOOR - ENGRAVE)))
    return s.cut(t).val()


def part_box(size, shift=(0, 0, 0)):
    L, W, H = size
    return box(-L / 2, L / 2, -W / 2, W / 2, FLOOR, FLOOR + H).translate(shift).val()


def overlap(a, b):
    return a.intersect(b).Volume()


def checks(sizes, solids):
    """each part's box sits in its cup with nothing in the way (zero overlap), and the same box pushed 0.5 mm past the
    clearance into a wall, or 0.5 mm taller than it is into nothing, reads as it should: the controls"""
    rows = []
    for k, S in solids.items():
        z = sizes[k]['size']
        rows.append((k, 'part box in its cup', overlap(S, part_box(z)), '== 0'))
        rows.append((k, f'control: pushed {CLR + 0.5:.1f} toward +X', overlap(S, part_box(z, (CLR + 0.5, 0, 0))), '> 0'))
        rows.append((k, f'control: pushed {CLR + 0.5:.1f} toward -Y', overlap(S, part_box(z, (0, -CLR - 0.5, 0))), '> 0'))
        rows.append((k, 'control: pushed 0.5 down into the floor', overlap(S, part_box(z, (0, 0, -0.5))), '> 0'))
    ok = True
    for k, what, v, want in rows:
        good = v < 1e-6 if want == '== 0' else v > 1e-3; ok &= good
        print(f'{"ok  " if good else "FAIL"} {k:5s} {what:38s} {v:9.3f} mm3 (want {want})')
    return ok


def picture(sizes, solids, path):
    """each cup drawn from above at an angle, the sim's box in it (orange); triangles painted far to near"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    az, el = np.radians(-55), np.radians(32)
    Rz = np.array([[np.cos(az), -np.sin(az), 0], [np.sin(az), np.cos(az), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(el), -np.sin(el)], [0, np.sin(el), np.cos(el)]])
    R = Rx @ np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]]) @ Rz            # world -> screen (x right, y up, z toward the eye)
    sun = np.array([0.35, -0.45, 0.82]); sun /= np.linalg.norm(sun)
    fig, axs = plt.subplots(2, 2, figsize=(14, 9.5), dpi=130, facecolor='#fcfcfb')
    for ax, (k, S) in zip(axs.ravel(), solids.items()):
        tris, cols = [], []
        for solid, rgb, a in ((S, (0.62, 0.70, 0.78), 1.0), (part_box(sizes[k]['size']), (0.92, 0.41, 0.20), 0.55)):
            V, F = solid.tessellate(0.2); V = np.array([(v.x, v.y, v.z) for v in V]); T = V[np.array(F)]
            n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            lit = 0.5 + 0.5 * np.abs(n @ sun); tris.append(T); cols.append(np.c_[np.outer(lit, rgb), np.full(len(T), a)])
        T = np.vstack(tris) @ R.T; col = np.vstack(cols); order = np.argsort(T[:, :, 2].mean(1))
        ax.add_collection(PolyCollection(T[order][:, :, :2], facecolors=col[order], edgecolors=col[order], linewidths=0.2))
        ax.autoscale_view(); ax.set_aspect('equal'); ax.set_axis_off(); ax.set_facecolor('#fcfcfb')
        L, W, H = sizes[k]['size']; sim = sizes[k]['sim']
        note = '' if np.allclose(sim, sizes[k]['size']) else f'   (the sim says {sim[0]:g} x {sim[1]:g} x {sim[2]:g})'
        ax.set_title(f'{CUPS[k][1]}: {L:g} x {W:g} x {H:g} mm{note}', fontsize=11, color='#0b0b0b', loc='left')
    fig.suptitle("Fit cups: the sim's box for each part (orange), +0.3 a side. Posts stand at the sim's height; rings every 5 mm",
                 x=0.03, ha='left', fontsize=13, color='#0b0b0b')
    fig.tight_layout(); fig.savefig(path, facecolor=fig.get_facecolor()); plt.close(fig)


def plate(solids, gap=8.0):
    """the four cups laid out by hand in two rows (Orca's arrange left two off the bed): pack + ESC, Pi + PCA"""
    placed = []; y = 0.0
    for row in (('pack', 'esc'), ('pi', 'pca')):
        x = 0.0; h = 0.0
        for k in row:
            bb = solids[k].BoundingBox()
            placed.append(solids[k].translate(cq.Vector(x - bb.xmin, y - bb.ymin, -bb.zmin))); x += bb.xlen + gap; h = max(h, bb.ylen)
        y += h + gap
    return cq.Compound.makeCompound(placed)


def main():
    from cadquery import exporters
    import export
    os.makedirs(PRINT, exist_ok=True)
    sizes = sim_sizes(); solids = {}
    for k, (_, label, _) in CUPS.items():
        z = sizes[k]['size']; solids[k] = cup(z, label)
        print(f'{k:5s} {label:10s} {z[0]:6.1f} x {z[1]:5.1f} x {z[2]:5.1f}  sim {np.round(sizes[k]["sim"], 1)}  {SOURCE[k]}')
    ok = checks(sizes, solids)
    for k, S in solids.items():
        p = os.path.join(PRINT, f'cup_{k}.stl')
        exporters.export(cq.Workplane().add(S), p, tolerance=0.02, angularTolerance=0.1)
        good, msg = export.health(p); ok &= good
        print(f'{"ok  " if good else "FAIL"} mesh {os.path.basename(p)}: {msg}')
    picture(sizes, solids, os.path.join(OUT, 'fit_cups.png'))
    pl = plate(solids); p = os.path.join(PRINT, 'plate_fit_cups.stl')
    exporters.export(cq.Workplane().add(pl), p, tolerance=0.02, angularTolerance=0.1)
    msg = export.health(p)[1]; bb = pl.BoundingBox()                  # four bodies on purpose: judged as four
    good = all(t in msg for t in ('watertight=True', 'manifold=True', 'bodies=4', 'self-int=0')); ok &= good
    print(f'{"ok  " if good else "FAIL"} mesh {os.path.basename(p)} ({bb.xlen:.0f} x {bb.ylen:.0f} on the 300 x 300 bed): {msg}')
    print('all checks pass' if ok else 'CHECKS FAILED')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
