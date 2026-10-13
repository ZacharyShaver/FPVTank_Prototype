"""Pan coil set 9 (2026-10-10): the pan servo couldn't turn the drum. The input gear carries the servo's own horn and
sits 1.0 under the servo's block; the drum's barrel runs in a 688 instead of the PLA journal. Moves the parts this
replaces into a superseded folder and draws the before/after sheet into head-v2/out/print-pan/.

Zach at the bench (FPVTank_Control docs/bench/2026-10-10-v2-head-first-power.md): the bare servo turns fully, but
meshed it can't turn the drum. The gear slips on the spline (its screw turns, the gear doesn't), it rubs the wall
above it, more as the screw tightens, there's more drag when the head leans, and the drum isn't bearing-smooth.
See pan_coil_b.BARREL_688, HORN_GEAR. Checks: pan_coil_b_check.py (races_688, block_air), gear_horn_set9.py.

    python head-v2/generator/generators/pan_coil_b.py
    python head-v2/generator/generators/pan_coil_b_print.py drum base gear_out
    python head-v2/fixes/drum_set8.py --loose-gear
    python head-v2/fixes/gear_horn_set9.py
    python head-v2/fixes/set9.py --supersede
    python head-v2/fixes/pan_print_set.py
    python head-v2/fixes/set9.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import shutil
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pan_coil_b as P
from pan_print_set import OUT

OLD = 'superseded - set 7 base, set 8 drum + small gears, set 6 input gear (gear slipped and rubbed the servo)'
MOVE = ['base.stl', 'drum.stl', 'small_gear.stl', 'small_gear_loose.stl', 'input_gear.stl', 'plate_pan_coil_set7.3mf',
        'plate_pan_coil_set8.3mf', 'drum_set8.png', 'base_shelf_set7.png']


def supersede():
    os.makedirs(os.path.join(OUT, OLD), exist_ok=True)
    for f in MOVE:
        src = os.path.join(OUT, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(OUT, OLD, f)); print('moved %s -> %s/' % (f, OLD))


def setn(n):
    """flip the module between set 8 as printed (n=8: set 7's base, set 8's drum, set 6's input gear) and set 9"""
    on = n == 9
    P.HOLLOW_AXIS = False                            # set 10 (2026-10-11) is later; this sheet draws 8 and 9
    P.BARREL_688 = P.HORN_GEAR = on
    P.SQ_H = 3.0 if on else 3.5


def section(fn, u_rng, z_rng, h=0.04, dz=0.0, x_at=None):
    """inside (bool) on the plane Y = 0 with u along X, or (x_at) on the plane X = x_at with u along Y"""
    u = np.arange(*u_rng, h); z = np.arange(*z_rng, h)
    U, Z = np.meshgrid(u, z)
    p = (np.full_like(U, x_at), U, Z - dz) if x_at is not None else (U, np.zeros_like(U), Z - dz)
    return u, z, fn(p) < 0


def fill(ax, u, z, m, c, a=1.0):
    ax.contourf(u, z, m.astype(float), levels=[0.5, 2], colors=[c], alpha=a)


def note(ax, x, y, lines, color):
    ax.text(x, y, '\n'.join(lines), fontsize=8.5, color=color, va='top')


if __name__ == '__main__':
    if '--supersede' in sys.argv:
        supersede(); sys.exit(0)
    teal, pale, red, grey, blue, dark, gold, servo = '#3e9c8f', '#9cc9c0', '#e0443e', '#8a8f88', '#4a6fa5', '#333', '#c9a227', '#5a6470'
    keep_shaft = P.SV_SHAFT
    P.SV_SHAFT = P.SPLINE_REAL                       # the real spline, 9.0 (the model's is 10.0)
    fig, axs = plt.subplots(3, 2, figsize=(14, 17))
    zb = P.SV_Z0 - P.SV_HUMP_H
    # row 1: the input gear under the servo's block, cut along the horn's arms (the plane X = CENTRE)
    for col, n in enumerate((8, 9)):
        setn(n)
        ax = axs[0, col]; ur, zr = (-23, 23), (-40, -22)
        u, z, s = section(P.servo, ur, zr, x_at=P.CENTRE); fill(ax, u, z, s, servo, 0.85)
        dz = 1.0 if n == 8 else 0.0                  # set 6's gear as Zach had it: the screw pulled it 1.0 up
        _, _, g = section(P.gear_in, ur, zr, dz=dz, x_at=P.CENTRE); fill(ax, u, z, g, teal)
        fill(ax, u, z, g & s, red)
        if n == 9:
            _, _, h = section(P.horn, ur, zr, x_at=P.CENTRE); fill(ax, u, z, h, dark)
        ax.axhline(zb, color=grey, lw=0.8, ls=':'); ax.text(ur[1] - 0.5, zb + 0.3, "the servo's block", ha='right', fontsize=8, color=grey)
        if n == 8:
            ax.set_title('BEFORE: set 6 gear as you had it, pulled 1.0 into the block', fontsize=10)
            note(ax, ur[0] + 0.5, -41.3, ['The spline pressed into a PLA bore, which wore smooth: the screw',
                                          "turned, the gear didn't. The gear's top was 0.5 under the block, and",
                                          'the real 9.0 spline let the screw pull it 1.0 up, into the block (red):',
                                          'tighter screw, more drag.'], red)
        else:
            ax.set_title('AFTER, set 9: your horn (dark) in the gear, 1.0 under the block', fontsize=10)
            thread = P.HORN_FACE_Z + P.HORN_CB_H + P.HORN_SCREW_L - (P.SV_Z0 - P.SPLINE_REAL)
            note(ax, ur[0] + 0.5, -41.3, ['The spline goes into the horn and stops on its web: that sets the',
                                          "height. The gear's top is %.1f under the block, the horn's hub %.2f."
                                          % (zb - P.GIN_Z1, zb - (P.HORN_FACE_Z + P.HORN_H)),
                                          "The floor is open under the horn: its own screw seats on its web,",
                                          "%.1f mm into the spline. (Horn drawn simplified; the print's pocket is exact.)" % thread], blue)
        ax.set_aspect('equal'); ax.set_xlim(*ur); ax.set_ylim(-47, -22)
        ax.set_xlabel('Y along the horn, through the input gear\'s axis (mm)', fontsize=8)
    # row 2: the drum's barrel, cut through the pan axis
    for col, n in enumerate((8, 9)):
        setn(n)
        ax = axs[1, col]; ur, zr = (-14, 14), (-38.5, -21)
        u, z, b = section(P.base, ur, zr); fill(ax, u, z, b, '#c9cdc6')
        _, _, d = section(P.drum, ur, zr); fill(ax, u, z, d, teal)
        _, _, go = section(P.gear_out, ur, zr); fill(ax, u, z, go, pale)
        _, _, sc = section(P.screw_out, ur, zr); fill(ax, u, z, sc, dark, 0.6)
        if n == 9:
            _, _, br = section(P.bearing688, ur, zr); fill(ax, u, z, br, gold)
            ax.set_title('AFTER, set 9: the barrel through a 688 (gold)', fontsize=10)
            note(ax, -13.5, -39.3, ['The 688 drops into a seat in the base, on a lip under its',
                                    "outer ring only, its top level with the lane's floor. The drum's",
                                    'underside stays 0.4 clear: the 6809 still carries the drum,',
                                    'the 688 only keeps it upright. The barrel is 7.9 below the',
                                    'drum; the stub, 6.0 square.'], blue)
        else:
            ax.set_title('BEFORE: set 8 drum in set 7 base, a PLA journal', fontsize=10)
            note(ax, -13.5, -39.3, ["0.25 a side between the 10 mm barrel and the base's plastic.",
                                    'Leaning, the barrel bears on it: more drag the more the',
                                    'head leans.'], red)
        ax.set_aspect('equal'); ax.set_xlim(*ur); ax.set_ylim(-46, -21)
        ax.set_xlabel('X through the pan axis (mm)', fontsize=8)
    # row 3, left: the pocket from above, the gear cut 0.8 above the horn's flat face
    setn(9)
    ax = axs[2, 0]
    x = np.arange(P.CENTRE - 23, P.CENTRE + 23, 0.06); y = np.arange(-23, 23, 0.06); X, Y = np.meshgrid(x, y)
    zc = P.HORN_FACE_Z + 0.8
    fill(ax, x, y, P.gear_in((X, Y, np.full_like(X, zc))) < 0, teal)
    fill(ax, x, y, P.horn((X, Y, np.full_like(X, zc))) < 0, dark)
    ax.set_title('AFTER: the input gear from above, cut through the arms', fontsize=10)
    note(ax, x[0] + 0.5, -24.5, ['The arms grip 15 mm out, not the plastic round the spline. The horn',
                                 'presses in from the top before the gear goes on. The pocket is the',
                                 "horn's outline 0.10 a side (0.15 on the loose gear): zero offset was",
                                 'so tight the horn flew out.'], blue)
    ax.set_aspect('equal'); ax.set_xlim(x[0], x[-1]); ax.set_ylim(-33, 23)
    # row 3, right: the stub across, in the small gear, against the 688's bore
    ax = axs[2, 1]
    x = np.arange(-6, 6, 0.02); X, Y = np.meshgrid(x, x); Z = np.full_like(X, -33.5)
    for n, c, ls in ((8, red, '--'), (9, blue, '-')):
        setn(n)
        ax.contour(x, x, (P.drum((X, Y, Z)) < 0).astype(float), [0.5], colors=[c], linestyles=[ls], linewidths=1.4)
        ax.contour(x, x, (P.gear_out((X, Y, Z)) < 0).astype(float), [0.5], colors=[c], linestyles=[ls], linewidths=0.7)
    ax.add_patch(plt.Circle((0, 0), P.B688_ID / 2, fill=False, ec=gold, lw=1.4))
    setn(9)
    note(ax, -5.8, -6.6, ["red dashed: set 8's 7.0 square, its corners at r 4.62: they can't pass",
                          "the 688. blue: set 9's 6.0 square, corners at r %.2f, inside the 688's"
                          % ((P.SQ_H - P.SQ_RC) * 2 ** 0.5 + P.SQ_RC),
                          "bore (gold, r 4.0). The small gear's bore follows, 0.10 a side."], dark)
    ax.set_title('The stub across, in the small gear (Z -33.5)', fontsize=10)
    ax.set_aspect('equal'); ax.set_xlim(-6, 6); ax.set_ylim(-9.5, 6)
    P.SV_SHAFT = keep_shaft
    fig.text(0.01, 0.004, "Cut through each axis, Z up as assembled. Grey: the servo (its spline drawn at your 9.0) and the base. "
             "Teal: the drum and the input gear.\nPale: the small gear. Dark: the horn and the screw. Gold: the 688.\n"
             "Set 9 guesses: the horn's flat face 4.45 under the block (your 9.0 tilt-servo spline, the horn's 1.45 web, the 6.0 block); "
             "1.0 of air under the block;\nthe 688 seat 16.1, the barrel 7.9, the lip from r 7.1; the small gear at 0.10 (0.05 tore "
             "the stub off); the horn pocket at 0.10 / 0.15.", fontsize=9)
    plt.tight_layout(rect=(0, 0.05, 1, 1)); plt.savefig(os.path.join(OUT, 'set9.png'), dpi=72); plt.close(fig)
    print('wrote set9.png')
