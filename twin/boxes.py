"""SUPERSEDED before printing (2026-11-03): Zach chose the Trainer's own tub (twin/trainer_tub.py), the sim's housing,
over these free-standing boxes. Its helpers (box, render) are still used there.

Insides boxes (2026-11-03): the boxes the robot's inside parts sit in, v0, printed to shake out sizing before the
sim is realigned. Three boxes, laid out as the sim lays the parts (gauges/body.parts(), the Trainer's, which every search
design carries), with the walls, clearances and lead room the sim leaves out:

- the brain box: the Pi 5 stack (USB end aft, open) and the PCA9685 forward of it, in the sim's narrow strip;
- two side boxes, identical: an ESC, a lead bay for the T-plugs, and a pack, both on edge as the sim stands them. The
  search moves the packs (dxp); here the ESC moves with its pack, which ends the packs-into-ESCs clash.

    python twin/boxes.py      # STLs and the plate to twin/out/print/, picture twin/out/boxes.png, checks and mesh report

Open tops, flat bottoms, nothing to mount them yet (that waits for the fit and his screw stock). Every cut runs out
through the top edge, so nothing needs supports. * = a guess; GUESSES lists them.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
import config
import numpy as np
import cadquery as cq

OUT = config.TWIN_OUT
PRINT = os.path.join(OUT, 'boxes-superseded')
CLR, WALL, FLOOR = 0.5, 2.0, 2.0                  # drop-in clearance a side*, wall, floor
ESC = (45.0, 24.0, 34.0)                           # Zach's caliper 2026-10-11 (L, tall, W), on edge: X, Y, Z. The sim: 46 x 18 x 34*
BOARD = (85.0, 56.0, 1.6)                          # Pi 5 board (Raspberry Pi's drawing)
HOLES = ((3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5))   # Pi 5 mounting holes from the board's SD-end corner
PAD, PAD_OD, PAD_ID = 4.0, 8.0, 6.5                # rings the Pi stands on; the HAT kit's screw heads drop into them*
SD_OUT = 2.5                                       # the microSD card past the board's front edge*
UNDER = 2.0                                        # pins under the Pi board, inside the sim's stack box*
GAP_PI_PCA, PCA_END = 6.0, 12.0                    # Pi front to PCA; PCA to the front wall, for its end headers' plugs*
FENCE = (1.2, 3.0)                                 # rib round the PCA: thick, tall
BAY = 25.0                                         # side box: lead bay for the pack's and ESC's T-plugs*
RIB = (2.0, 10.0)                                  # side box: ribs either side of the bay
GUESSES = [
    ('Clearance round each part', f'{CLR} a side', 'my pick; drop-in, lifts out'),
    ('ESC', '45 x 24 x 34', "Zach's caliper (the sim still has 18 thick)"),
    ('Pack', '141 x 26 x 45.7', "Zach's model's box"),
    ('Pi 5 stack (Pi + cooler + HAT+ + Hailo)', '89.1 x 57.2 x 27.2', "the sim's: his Pi model, HAT on 16 mm* standoffs"),
    ('PCA9685', '62.2 x 25.7 x 12.4', "Adafruit's size*; his is a clone"),
    ('Pi rings: tall, hole', f'{PAD} / {PAD_ID}', "the HAT kit's M2.5 screw heads under the Pi*"),
    ('Pi hole pattern', '58 x 49, 3.5 in', "Raspberry Pi's drawing"),
    ('SD card past the board', f'{SD_OUT}', '*'),
    ('Pi front to PCA', f'{GAP_PI_PCA}', '*'),
    ('PCA to the front wall (end-header plugs)', f'{PCA_END}', '*'),
    ('Lead bay, pack to ESC (T-plugs)', f'{BAY}', '*'),
]


def sim_sizes():
    """the box each group of the sim's parts fills, mm (X, Y, Z), rounded up to 0.1"""
    sys.path.insert(0, config.GAUGES)
    import body as B
    C = B.parts()[0]
    size = lambda *ks: np.ceil(np.ptp(np.vstack([np.asarray(C[k], float) for k in ks]), 0) * 10 - 1e-6) / 10
    return dict(pi=size('pi', 'hat', 'hailo'), pca=size('pca'), pack=size('pack_L'), esc=size('esc_L'))


def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane().box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def shell(L, W, H, open_aft=False):
    """an open-top box, inner X 0..L, Y -W/2..W/2, floor top at Z FLOOR, walls H over the floor; aft end left off if asked"""
    s = box(0 if open_aft else -WALL, L + WALL, -W / 2 - WALL, W / 2 + WALL, 0, FLOOR + H)
    return s.cut(box(-WALL - 1 if open_aft else 0, L, -W / 2, W / 2, FLOOR, FLOOR + H + 1))


def brain(S):
    """the brain box and where its parts sit: {'solid', 'parts': {name: (x0, x1, y0, y1, z0, z1)}}"""
    pi, pca = S['pi'], S['pca']
    Lpi = pi[0] + 2 * CLR; W = max(pi[1], pca[1]) + 2 * CLR
    xp = Lpi + GAP_PI_PCA; L = xp + pca[0] + 2 * CLR + PCA_END
    zb = FLOOR + PAD                                                    # the board's underside
    H = PAD - UNDER + pi[2] + 1.0                                       # walls 1 over the stack's top
    s = shell(L, W, H, open_aft=True)
    bx1 = Lpi - CLR - SD_OUT; bx0 = bx1 - BOARD[0]                      # the board, SD end forward
    for hx, hy in HOLES:
        c = (bx1 - hx, -BOARD[1] / 2 + hy)
        s = s.union(cq.Workplane().circle(PAD_OD / 2).circle(PAD_ID / 2).extrude(PAD + 0.01).translate((c[0], c[1], FLOOR - 0.01)))
    a0, a1, b = xp, xp + pca[0] + 2 * CLR, pca[1] / 2 + CLR             # the PCA's fence
    t, h = FENCE
    s = s.union(box(a0 - t, a1 + t, -b - t, b + t, FLOOR - 0.01, FLOOR + h).cut(box(a0, a1, -b, b, FLOOR - 1, FLOOR + h + 1)))
    s = s.cut(box(bx0 + 2, bx0 + 57, -W / 2 - WALL - 1, -W / 2 + 0.5, zb - 0.5, FLOOR + H + 1))   # USB-C + HDMI side window
    s = s.cut(box(L - 0.5, L + WALL + 1, -10, 10, FLOOR + 5, FLOOR + H + 1))                    # front: a slot for leads
    parts = dict(pi_board=(bx0, bx1, -BOARD[1] / 2, BOARD[1] / 2, zb, zb + BOARD[2]),
                 pi_stack=(CLR, CLR + pi[0], -pi[1] / 2, pi[1] / 2, zb - UNDER, zb - UNDER + pi[2]),
                 pca=(a0 + CLR, a1 - CLR, -pca[1] / 2, pca[1] / 2, FLOOR, FLOOR + pca[2]))
    return dict(solid=s.val(), parts=parts, size=(L + WALL, W + 2 * WALL, FLOOR + H), H=H)


def side(S):
    """a side box: ESC aft, the lead bay, the pack forward, all on edge"""
    pack = S['pack']; W = pack[1] + 2 * CLR
    e1 = ESC[0] + 2 * CLR; r0 = e1; b0 = r0 + RIB[0]; b1 = b0 + BAY; p0 = b1 + RIB[0]; L = p0 + pack[0] + 2 * CLR
    H = pack[2] + CLR
    s = shell(L, W, H)
    for x in (r0, b1):
        s = s.union(box(x, x + RIB[0], -W / 2 - 0.01, W / 2 + 0.01, FLOOR - 0.01, FLOOR + RIB[1]))
    s = s.cut(box(-WALL - 1, 0.5, -8, 8, FLOOR + 4, FLOOR + H + 1))                            # aft: the motor leads
    for x in (e1 / 2, p0 + 0.25 * (L - p0), p0 + 0.75 * (L - p0)):                             # finger notches, both walls
        z = FLOOR + (14.0 if x < r0 else H - 22.0)
        s = s.cut(box(x - 12, x + 12, -W / 2 - WALL - 1, W / 2 + WALL + 1, z, FLOOR + H + 1))
    parts = dict(esc=(CLR, CLR + ESC[0], -ESC[1] / 2, ESC[1] / 2, FLOOR, FLOOR + ESC[2]),
                 pack=(p0 + CLR, p0 + CLR + pack[0], -pack[1] / 2, pack[1] / 2, FLOOR, FLOOR + pack[2]))
    return dict(solid=s.val(), parts=parts, size=(L + 2 * WALL, W + 2 * WALL, FLOOR + H), H=H)


def pbox(b, shift=(0, 0, 0)):
    return box(*b).translate(shift).val()


def checks(B):
    """each part in its box touches nothing (zero), and the controls: the part pushed past the clearance into a wall, or
    the Pi board 0.5 lower into its rings, must read > 0"""
    rows = []
    for name, D in B.items():
        S = D['solid']
        for k, b in D['parts'].items():
            pb = b if k != 'pi_stack' else b[:4] + (b[4] + UNDER + BOARD[2] + 0.01, b[5])  # the stack over the board
            rows.append((f'{name}: {k} in its place', S.intersect(pbox(pb)).Volume(), '== 0'))
        ctl = {'brain': [('pi_board', (0, 0, -0.5), 'Pi board 0.5 lower'), ('pca', (CLR + 1.0, 0, 0), 'PCA pushed 1.5 forward'),
                         ('pi_stack', (0, CLR + 0.5, 0), 'Pi stack pushed 1.0 sideways')],
               'side': [('pack', (0, CLR + 0.5, 0), 'pack pushed 1.0 sideways'), ('pack', (CLR + 0.5, 0, 0), 'pack pushed 1.0 forward'),
                        ('esc', (CLR + 0.5, 0, 0), 'ESC pushed 1.0 forward, into the rib')]}[name]
        for k, sh, what in ctl:
            b = D['parts'][k]
            pb = b if k != 'pi_stack' else b[:4] + (b[4] + UNDER + BOARD[2] + 0.01, b[5])
            rows.append((f'{name}: control, {what}', S.intersect(pbox(pb, sh)).Volume(), '> 0'))
    ok = True
    for what, v, want in rows:
        good = v < 1e-6 if want == '== 0' else v > 1e-3; ok &= good
        print(f'{"ok  " if good else "FAIL"} {what:45s} {v:9.3f} mm3 (want {want})')
    return ok


def render(ax, items, az=-55, el=30):
    """solids drawn at an angle, triangles painted far to near: items = [(solid, rgb, alpha)]"""
    from matplotlib.collections import PolyCollection
    a, e = np.radians(az), np.radians(el)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    R = Rx @ np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]]) @ Rz
    sun = np.array([0.35, -0.45, 0.82]); sun /= np.linalg.norm(sun); tris, cols = [], []
    for solid, rgb, al in items:
        V, F = solid.tessellate(0.2); V = np.array([(v.x, v.y, v.z) for v in V]); T = V[np.array(F)]
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        lit = 0.5 + 0.5 * np.abs(n @ sun); tris.append(T); cols.append(np.c_[np.outer(lit, rgb), np.full(len(T), al)])
    T = np.vstack(tris) @ R.T; col = np.vstack(cols); o = np.argsort(T[:, :, 2].mean(1))
    ax.add_collection(PolyCollection(T[o][:, :, :2], facecolors=col[o], edgecolors=col[o], linewidths=0.2))
    ax.autoscale_view(); ax.set_aspect('equal'); ax.set_axis_off()


def picture(B, S, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    BOX, PART = (0.62, 0.70, 0.78), (0.92, 0.41, 0.20)
    fig, axs = plt.subplots(1, 2, figsize=(15, 6.2), dpi=130, facecolor='#fcfcfb', gridspec_kw=dict(width_ratios=[1, 1.25]))
    for ax, name in zip(axs, ('brain', 'side')):
        D = B[name]; ax.set_facecolor('#fcfcfb')
        keep = [k for k in D['parts'] if k != 'pi_board']
        render(ax, [(D['solid'], BOX, 1.0)] + [(pbox(D['parts'][k]), PART, 0.5) for k in keep])
        L, W, H = D['size']
        t = {'brain': f'Brain box: {L:.0f} x {W:.0f} x {H:.0f} mm\nPi 5 stack (USB end aft, open) + PCA9685',
             'side': f'Side box, print 2: {L:.0f} x {W:.0f} x {H:.0f} mm\nESC (aft), lead bay, pack: both on edge'}[name]
        ax.set_title(t, fontsize=11, color='#0b0b0b', loc='left')
    fig.suptitle("Insides boxes v0: the sim's parts in orange, in the boxes they sit in", x=0.03, ha='left', fontsize=13, color='#0b0b0b')
    fig.tight_layout(); fig.savefig(path, facecolor=fig.get_facecolor()); plt.close(fig)


def plate(B, gap=8.0):
    """print layout, floors down: the two side boxes in a row, the brain box beside them"""
    out = []; y = 0.0
    for name in ('side', 'side', 'brain'):
        s = B[name]['solid']; bb = s.BoundingBox()
        out.append(s.translate(cq.Vector(-bb.xmin, y - bb.ymin, -bb.zmin))); y += bb.ylen + gap
    return cq.Compound.makeCompound(out)


def main():
    from cadquery import exporters
    import export
    os.makedirs(PRINT, exist_ok=True)
    S = sim_sizes(); B = dict(brain=brain(S), side=side(S))
    for name, D in B.items():
        L, W, H = D['size']; print(f'{name:5s} box {L:6.1f} x {W:5.1f} x {H:5.1f} mm (walls {D["H"]:.1f} over the floor)')
    ok = checks(B)
    for name, D in B.items():
        p = os.path.join(PRINT, f'{name}_box.stl')
        exporters.export(cq.Workplane().add(D['solid']), p, tolerance=0.02, angularTolerance=0.1)
        good, msg = export.health(p); ok &= good
        print(f'{"ok  " if good else "FAIL"} mesh {os.path.basename(p)}: {msg}')
    pl = plate(B); p = os.path.join(PRINT, 'plate_boxes.stl')
    exporters.export(cq.Workplane().add(pl), p, tolerance=0.02, angularTolerance=0.1)
    msg = export.health(p)[1]; bb = pl.BoundingBox()                   # three bodies on purpose
    good = all(t in msg for t in ('watertight=True', 'manifold=True', 'bodies=3', 'self-int=0')); ok &= good
    print(f'{"ok  " if good else "FAIL"} mesh {os.path.basename(p)} ({bb.xlen:.0f} x {bb.ylen:.0f} on the 300 x 300 bed): {msg}')
    picture(B, S, os.path.join(OUT, 'boxes.png'))
    print('all checks pass' if ok else 'CHECKS FAILED')
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
