"""Pan coil set 10 (2026-10-11): the servo wires straight down the pan axis. A 6704 replaces the 688, the drum's barrel
is 19.9 and hollow, and the small gear (a solid hub on top) bolts to the barrel's end on three M3 x 16. Moves the parts
this replaces into a superseded folder and draws the before/after sheet into head-v2/out/print-pan/.

Zach at the bench: set 9 meshed moved only over 500..800 us, the bare servo turned its full 180 deg, and the jumper
wires were squashed in the lane once everything was screwed down. See pan_coil_b.HOLLOW_AXIS and docs/decisions.md.
Checks: pan_coil_b_check.py (wire_axis, races_6704, screw_threads_6704, the 6704 rows and the assembly order).

    python head-v2/generator/generators/pan_coil_b.py
    python head-v2/generator/generators/pan_coil_b_print.py drum base gear_out floor
    python head-v2/fixes/set10.py --supersede
    python head-v2/fixes/pan_print_set.py
    python head-v2/fixes/set10.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import shutil
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pan_coil_b as P
from pan_print_set import OUT
from set9 import section, fill, note

OLD = 'superseded - set 9 drum, base, small gear, floor (688; wires squashed in the lane)'
MOVE = ['base.stl', 'drum.stl', 'small_gear.stl', 'floor.stl', 'plate_pan_coil_set9.3mf', 'set9.png']


def supersede():
    os.makedirs(os.path.join(OUT, OLD), exist_ok=True)
    for f in MOVE:
        src = os.path.join(OUT, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(OUT, OLD, f)); print('moved %s -> %s/' % (f, OLD))


def setn(n):
    """flip the module between set 9 as printed and set 10"""
    P.HOLLOW_AXIS = n == 10
    P.BARREL_688 = n == 9


if __name__ == '__main__':
    if '--supersede' in sys.argv:
        supersede(); sys.exit(0)
    teal, pale, red, grey, blue, dark, gold = '#3e9c8f', '#9cc9c0', '#e0443e', '#c9cdc6', '#4a6fa5', '#333', '#c9a227'
    fig, axs = plt.subplots(2, 2, figsize=(14, 13))
    # row 1: cut through the pan axis, set 9 and set 10
    for col, n in enumerate((9, 10)):
        setn(n)
        ax = axs[0, col]; ur, zr = (-17, 17), (-41, -13)
        u, z, b = section(P.base, ur, zr); fill(ax, u, z, b, grey)
        _, _, fl = section(P.floor, ur, zr); fill(ax, u, z, fl, '#b8b39a')
        _, _, d = section(P.drum, ur, zr); fill(ax, u, z, d, teal)
        _, _, go = section(P.gear_out, ur, zr); fill(ax, u, z, go, pale)
        _, _, sc = section(P.screw_out, ur, zr); fill(ax, u, z, sc, dark, 0.7)
        _, _, br = section(P.bearing6704 if n == 10 else P.bearing688, ur, zr); fill(ax, u, z, br, gold)
        if n == 10:
            ax.plot([0, 0], [-13, -41], color=red, lw=3.5, solid_capstyle='butt')
            ax.set_title('AFTER, set 10: the wires (red) straight down the axis', fontsize=10)
            note(ax, -16.5, -41.6, ['A 6704 (gold) where the 688 was, the barrel 19.9 and hollow: a 5.5 hole from the',
                                    "cone's point down through the barrel, the small gear and the floor plate. The gear's",
                                    "solid hub meets the barrel's end 0.4 under the 6704's inner ring (that stops the",
                                    'drum lifting out). Three M3 x 16 go up through gear and hub, %.1f into the barrel;'
                                    % (P.G_Z0 + P.AX_SCREW_L - P.AX_JOINT_Z),
                                    'their heads turn in a %.1f hole in the floor plate.' % (2 * P.AX_FLOOR_HOLE_R)], blue)
        else:
            ax.set_title('BEFORE, set 9: solid barrel in a 688, one M3 on the axis', fontsize=10)
            note(ax, -16.5, -41.6, ['The M3 sat on the axis and held the drum in, so the wires went down an',
                                    'off-axis hole (not in this cut) and rolled round the lane under the ribbon,',
                                    'where they were squashed once everything was screwed down.'], red)
        ax.set_aspect('equal'); ax.set_xlim(*ur); ax.set_ylim(-50, -13)
        ax.set_xlabel('X through the pan axis (mm)', fontsize=8)
    # row 2, left: the small gear across, through its teeth, with the walls round each hole
    setn(10)
    ax = axs[1, 0]
    x = np.arange(-12.5, 12.5, 0.03); X, Y = np.meshgrid(x, x)
    fill(ax, x, x, P.gear_out((X, Y, np.full_like(X, (P.G_Z0 + P.G_Z1) / 2))) < 0, pale)
    ax.add_patch(plt.Circle((0, 0), P.AX_HUB_R, fill=False, ec=teal, lw=1.0, ls='--'))
    w_in = P.AX_SCREW_R - P.AX_CLEAR_R - P.AX_WIRE_R
    w_out = (P.R_OUT_G - P.GEAR_GAP - P.TOOTH) - P.AX_SCREW_R - P.AX_CLEAR_R
    ax.set_title('AFTER: the small gear across, through its teeth', fontsize=10)
    note(ax, -12.3, -13.0, ['The wire hole (5.5) and the three M3 clear holes (3.4). Each hole has %.2f of' % w_in,
                            "wall to the wire hole and %.2f to the teeth's roots, the gear's full 8.7. Dashed:" % w_out,
                            "the hub on top, 22.4 across. The first draft (never printed) sank M2 heads into",
                            'the gear: 0.9 of wall. Zach: "looks extremely flimsy".'], blue)
    ax.set_aspect('equal'); ax.set_xlim(-12.5, 12.5); ax.set_ylim(-18.5, 12.5)
    # row 2, right: the floor plate's middle hole, set 9 and set 10, with the heads' sweep
    ax = axs[1, 1]
    x = np.arange(-15, 15, 0.04); X, Y = np.meshgrid(x, x); Z = np.full_like(X, (P.BAY_Z0 + P.SPLIT_Z) / 2)
    for n, c, ls in ((9, red, '--'), (10, blue, '-')):
        setn(n)
        ax.contour(x, x, (P.floor((X, Y, Z)) < 0).astype(float), [0.5], colors=[c], linestyles=[ls], linewidths=1.4)
    setn(10)
    for sx, sy in P.ax_screws():
        ax.add_patch(plt.Circle((sx, sy), P.AX_HEAD_R, color=dark, alpha=0.7))
    ax.add_patch(plt.Circle((0, 0), P.AX_SCREW_R + P.AX_HEAD_R, fill=False, ec=dark, lw=0.8, ls=':'))
    ax.add_patch(plt.Circle((0, 0), P.AX_WIRE_R, color=red, alpha=0.8))
    ax.set_title("The floor plate's middle hole, from below", fontsize=10)
    note(ax, -14.5, -15.8, ["red dashed: set 9's 7 mm hole. blue: set 10's %.1f; the button heads (dark, 5.7 across)"
                            % (2 * P.AX_FLOOR_HOLE_R),
                            'turn inside it with 0.6 to spare (dotted), and stand 0.35 inside the plate\'s',
                            'underside. The wires (red) come out of the middle.'], dark)
    ax.set_aspect('equal'); ax.set_xlim(-15, 15); ax.set_ylim(-21, 15)
    fig.text(0.01, 0.004, "Cut through the pan axis, Z up as assembled. Grey: the base. Khaki: the floor plate. Teal: the drum. "
             "Pale: the small gear. Dark: the screws. Gold: the 688 / 6704. Red: the wires.\n"
             "Set 10 guesses: the 6704's rings (inner r 10.0-11.3, outer 12.3-13.5; the lip from r 12.4); its seat 27.1 and the "
             "barrel 19.9; the hub 0.4 under the inner ring; the 5.5 wire hole;\nbutton heads on the M3 x 16 (5.7 x 1.65; socket "
             "caps, 3.0 tall, would stand 1.0 below the base).", fontsize=9)
    plt.tight_layout(rect=(0, 0.05, 1, 1)); plt.savefig(os.path.join(OUT, 'set10.png'), dpi=72); plt.close(fig)
    print('wrote set10.png')
