"""Pan coil set 7 (2026-10-04): the shelf drops in, so the base prints with nothing trapped in the wire lane.
Moves set 5's base into a superseded folder and draws the before/after sheet into head-v2/out/print-pan/. The
print files come from pan_print_set.py (plate_pan_coil_set7.3mf).

Zach: Orca's supports in the base's wire lane, under the shelf, are impossible to get out, and he wants that
overhang support-free. A slope can't carry the shelf (30 deg off vertical across the lane's 8.4 mm needs 14.5
mm of drop; the lane is 3.5 tall), so the shelf and the ribbon cup's wall became `shelf_ring`, which prints
shelf face down and drops in from above onto a ledge (pan_coil_b.INSERT, RING_*, SKIRT_*, KEY_*). Widening the
deck ring's hole for it also took the deck ring out from under the drum's hub, which sat flush on it. Supports
are read from Orca's own G-code with his settings: the old base's slice is the control.

    python head-v2/generator/generators/pan_coil_b.py well bay base shelf_ring
    python head-v2/generator/generators/pan_coil_b_print.py base shelf_ring
    python head-v2/fixes/base_shelf_set7.py --supersede
    python head-v2/fixes/pan_print_set.py
    python tools/orca.py head-v2/out/print-pan/base.stl --name base_set7
    python tools/orca.py head-v2/out/print-pan/shelf_ring.stl --name shelf_ring_set7
    python head-v2/fixes/base_shelf_set7.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import glob, re, shutil
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pan_coil_b as P
from pan_print_set import OUT

OLD = 'superseded - set 5 base (lane supports trapped, hub on the deck ring)'
MOVE = ['base.stl']
GCODE = os.path.join(config.OUT, 'gcode')
SLICE_OLD = os.path.join(GCODE, 'base_orca_PLA_2h51m.gcode')     # set 5's base, his settings (2026-10-03)


def supersede():
    os.makedirs(os.path.join(OUT, OLD), exist_ok=True)
    for f in MOVE:
        src = os.path.join(OUT, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(OUT, OLD, f)); print('moved %s -> %s/' % (f, OLD))


def supports(path, x_centre, z_bed):
    """Orca's support extrusions in a G-code, back in the model frame: the part's outer walls give the bed
    offset; the STL was centred on its own bounding box (x_centre) with its bed face at z_bed."""
    typ, z, x, y, sup, wall = None, 0.0, 0.0, 0.0, [], []
    for L in open(path, errors='ignore'):
        if L.startswith(';TYPE:'):
            typ = L[6:].strip()
        elif L.startswith(';Z:'):
            z = float(L[3:])
        elif L.startswith('G1') or L.startswith('G0'):
            mx = re.search(r'X(-?[\d.]+)', L); my = re.search(r'Y(-?[\d.]+)', L); me = re.search(r'E(-?[\d.]+)', L)
            nx = float(mx.group(1)) if mx else x; ny = float(my.group(1)) if my else y
            if L.startswith('G1') and me and float(me.group(1)) > 0:
                if typ and typ.startswith('Support'):
                    sup.append((nx, ny, z))
                elif typ == 'Outer wall':
                    wall.append((nx, ny))
            x, y = nx, ny
    W = np.array(wall); S = np.array(sup).reshape(-1, 3)
    cx, cy = (W[:, 0].min() + W[:, 0].max()) / 2, (W[:, 1].min() + W[:, 1].max()) / 2
    return np.c_[S[:, 0] - cx + x_centre, S[:, 1] - cy, S[:, 2] + z_bed]


def zones(S):
    r = np.hypot(S[:, 0], S[:, 1]); z = S[:, 2]
    lane = (r > 12.3) & (r < 21.3) & (z > P.LANE_Z0 - 0.1) & (z < P.LANE_Z1 + 0.2)
    deck = ~lane & (r > 20.2) & (z > P.LANE_Z1 + 0.2) & (z < 0)
    return lane, deck, ~lane & ~deck


def section(fn, deg, r_rng, z_rng, h=0.05):
    a = np.radians(deg); r = np.arange(*r_rng, h); z = np.arange(*z_rng, h)
    R, Z = np.meshgrid(r, z)
    return (fn((R * np.cos(a), R * np.sin(a), Z)) < 0), (r_rng[0], r_rng[1], z_rng[0], z_rng[1])


if __name__ == '__main__':
    if '--supersede' in sys.argv:
        supersede(); sys.exit(0)
    new = sorted(glob.glob(os.path.join(GCODE, 'base_set7_orca_PLA_*.gcode')), key=os.path.getmtime)[-1]
    ring = sorted(glob.glob(os.path.join(GCODE, 'shelf_ring_set7_orca_PLA_*.gcode')), key=os.path.getmtime)[-1]
    xc = (-P.BOSS_R - 0.0 + P.CENTRE + P.R_IN_G + P.TOOTH + 3.5) / 2      # the base's bbox centre in X
    rows = {}
    for tag, path in (('set 5 base', SLICE_OLD), ('set 7 base', new)):
        S = supports(path, xc, P.SPLIT_Z)
        lane, deck, below = zones(S)
        rows[tag] = (S, lane, deck, below)
        print('%-11s %-34s supports: wire lane %5d, under the deck ring %5d, from below %5d'
              % (tag, os.path.basename(path), lane.sum(), deck.sum(), below.sum()))
    Sr = supports(ring, 0.0, P.LANE_Z1)
    print('%-11s %-34s supports: %d' % ('shelf ring', os.path.basename(ring), len(Sr)))

    teal, ring_c, grey, red, orange, blue = '#3e9c8f', '#d6a048', '#a3a8a2', '#d0021b', '#f5a623', '#4a90d9'
    fig, axs = plt.subplots(2, 2, figsize=(13, 10.5))
    for col, (tag, insert) in enumerate((('BEFORE: set 5 base (printed)', False), ('AFTER: set 7 base + drop-in shelf ring', True))):
        P.INSERT = insert
        ax = axs[0, col]
        b, ext = section(P.base, 90.0, (0, 33), (-28, 8))
        ax.imshow(np.where(b, 0.72, 1.0), origin='lower', extent=ext, cmap='gray', vmin=0, vmax=1, interpolation='nearest')
        if insert:
            g, _ = section(P.shelf_ring, 90.0, (0, 33), (-28, 8))
            ax.contourf(np.linspace(*ext[:2], g.shape[1]), np.linspace(*ext[2:], g.shape[0]), g.astype(float),
                        levels=[0.5, 2], colors=[ring_c])
        d, _ = section(P.drum, 90.0, (0, 33), (-28, 8))
        ax.contour(np.linspace(*ext[:2], d.shape[1]), np.linspace(*ext[2:], d.shape[0]), d.astype(float), levels=[0.5],
                   colors=[teal], linewidths=0.8)
        S, lane, deck, below = rows['set 7 base' if insert else 'set 5 base']
        k = np.abs(S[:, 0]) < 1.2                                                 # the X = 0 slab, +Y side
        for m, c in ((below, blue), (deck, orange), (lane, red)):
            ax.scatter(S[k & m, 1], S[k & m, 2], s=1.5, c=c, lw=0)
        ax.set_title('%s\ncut on +Y. Orca supports (his settings) within 1.2 mm: lane %d, deck %d, below %d'
                     % (tag, lane.sum(), deck.sum(), below.sum()), fontsize=9.5)
        ax.set_xlim(0, 33); ax.set_ylim(-28, 8); ax.set_aspect('equal'); ax.set_xlabel('r mm'); ax.set_ylabel('Z mm')
        if insert:
            ax.annotate('shelf ring: prints shelf face down,\ndrops in onto the ledge', (16, -20.4), (1, -9), fontsize=8.5,
                        color='#8a5a00', arrowprops=dict(arrowstyle='->', color='#8a5a00'))
            ax.annotate('cone 30 deg off vertical', (27.5, -9), (20, 4.5), fontsize=8.5, arrowprops=dict(arrowstyle='->'))
            ax.annotate('nothing under the\ndrum hub now', (20, -0.5), (5.5, 3.5), fontsize=8.5, arrowprops=dict(arrowstyle='->'))
        else:
            ax.annotate('trapped in the lane', (16, -22.5), (1, -9), fontsize=8.5, color=red, arrowprops=dict(arrowstyle='->', color=red))
            ax.annotate('drum hub flush on the\ndeck ring, r 19.5-20.4', (20, -0.5), (3.5, 3.5), fontsize=8.5, color=red,
                        arrowprops=dict(arrowstyle='->', color=red))
    # the ribbon's way out at -90: the notch in the ring, then the slit in the base (cut down its middle)
    P.INSERT = True
    ax = axs[1, 0]
    b, ext = section(P.base, -90.0, (0, 35), (-28, 8))
    g, _ = section(P.shelf_ring, -90.0, (0, 35), (-28, 8))
    ax.imshow(np.where(b, 0.72, 1.0), origin='lower', extent=ext, cmap='gray', vmin=0, vmax=1, interpolation='nearest')
    ax.contourf(np.linspace(*ext[:2], g.shape[1]), np.linspace(*ext[2:], g.shape[0]), g.astype(float), levels=[0.5, 2], colors=[ring_c])
    ax.add_patch(plt.Rectangle((P.RO, P.BAND_Z0), 34 - P.RO, P.BAND_Z1 - P.BAND_Z0, fill=False, ec=red, lw=1, ls='--'))
    ax.text(25.5, -11, 'ribbon\nleaves here', color=red, fontsize=8.5)
    ax.annotate('2 mm slit: pointed roof under the deck\nring, open under the bearing\'s inner ring', (28, -1.6), (3, 4.6),
                fontsize=8.5, arrowprops=dict(arrowstyle='->'))
    ax.text(1, -26.8, 'The key is at -60 deg: a 2.4 mm rib on the ledge, in a notch in the ring\'s rim.', fontsize=8.5)
    ax.set_title('AFTER, cut on -Y down the middle of the ribbon\'s slit: ring notch open at the top', fontsize=9.5)
    ax.set_xlim(0, 35); ax.set_ylim(-28, 8); ax.set_aspect('equal'); ax.set_xlabel('r mm'); ax.set_ylabel('Z mm')
    # the plate render from pan_print_set.py
    ax = axs[1, 1]; ax.axis('off')
    png = os.path.join(OUT, 'pan_coil_assembly.png')
    if os.path.exists(png):
        ax.imshow(plt.imread(png)); ax.set_title('How it goes together: base, then the ring (gold), then 6809 + drum', fontsize=9.5)
    fig.text(0.01, 0.005, 'Grey: base. Gold: shelf ring. Teal outline: the drum. Dots: Orca\'s supports with Zach\'s settings '
             '(tree, 30 deg): red trapped in the wire lane, orange under the deck ring, blue reachable from below.\n'
             'Set 7 guesses: the ring\'s 0.15 slide down the skirt; the 1.5 ledge; the key\'s 0.15 a side; the 0.8 shelf as '
             'a part of its own;\nthe ring held by gravity and the key (glue if it lifts); the 2 mm slit; the 30 deg cone (his number).',
             fontsize=8.5)
    plt.tight_layout(rect=(0, 0.055, 1, 1)); plt.savefig(os.path.join(OUT, 'base_shelf_set7.png'), dpi=80); plt.close(fig)
    print('wrote base_shelf_set7.png')
