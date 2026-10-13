"""Pan coil set 11 (2026-10-12): the shelf ring back in the base. The lane, empty since set 10 sent the wires down the
axis, fills solid up to the ribbon's floor; the ring's cup wall stands on it; the rib, the boss and the wires' old exit
hole go. Moves the parts this replaces into a superseded folder and draws the before/after sheet into
head-v2/out/print-pan/.

Zach, with set 10 assembled and the pan through its full sweep: the ring "has a chance of falling out of its lock if its
gone upside down" and "doesnt need to be an extra piece if the wire just runs through the bottom now"; close the hole on
the outside. See pan_coil_b.SHELF_MERGED and docs/decisions.md. Checks: pan_coil_b_check.py (merged_shelf, and the
6704's way down through the shelf in the assembly order).

    python head-v2/generator/generators/pan_coil_b.py
    python head-v2/generator/generators/pan_coil_b_print.py base
    python head-v2/fixes/set11.py --supersede
    python head-v2/fixes/pan_print_set.py
    python head-v2/fixes/set11.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import shutil
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pan_coil_b as P
from pan_print_set import OUT
from set9 import fill, note

OLD = 'superseded - set 10 base and shelf ring (ring could fall out upside down; empty lane, old wire hole)'
MOVE = ['base.stl', 'shelf_ring.stl', 'plate_pan_coil_set10_b_base.3mf']


def supersede():
    os.makedirs(os.path.join(OUT, OLD), exist_ok=True)
    for f in MOVE:
        src = os.path.join(OUT, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(OUT, OLD, f)); print('moved %s -> %s/' % (f, OLD))


def setn(n):
    """flip the module between set 10 as printed and set 11"""
    P.SHELF_MERGED = n == 11
    P.RING_PART = n == 10


def cut(fn, deg, u_rng, z_rng, h=0.05):
    """inside (bool) on the vertical plane through the pan axis at deg, u along it (u > 0 toward deg)"""
    u = np.arange(*u_rng, h); z = np.arange(*z_rng, h)
    U_, Z = np.meshgrid(u, z)
    a = np.radians(deg)
    return u, z, fn((U_ * np.cos(a), U_ * np.sin(a), Z)) < 0


def plan(fn, z0, rng, h=0.06):
    x = np.arange(*rng, h); X, Y = np.meshgrid(x, x)
    return x, fn((X, Y, np.full_like(X, z0))) < 0


if __name__ == '__main__':
    if '--supersede' in sys.argv:
        supersede(); sys.exit(0)
    teal, red, grey, blue, gold, ring, silver = '#3e9c8f', '#e0443e', '#c9cdc6', '#4a6fa5', '#c9a227', '#d6a048', '#9aa0aa'
    fig, axs = plt.subplots(2, 2, figsize=(14, 13))
    # row 1: cut through the pan axis toward the old exit hole (-145 deg), set 10 and set 11
    for col, n in enumerate((10, 11)):
        setn(n)
        ax = axs[0, col]; ur, zr = (-32, 32), (-41, 8)
        u, z, b = cut(P.base, P.WIRE_EXIT_DEG, ur, zr); fill(ax, u, z, b, grey)
        if n == 10:
            _, _, r = cut(P.shelf_ring, P.WIRE_EXIT_DEG, ur, zr); fill(ax, u, z, r, ring)
        _, _, d = cut(P.drum, P.WIRE_EXIT_DEG, ur, zr); fill(ax, u, z, d, teal, 0.85)
        _, _, br = cut(P.bearing6704, P.WIRE_EXIT_DEG, ur, zr); fill(ax, u, z, br, gold)
        _, _, b9 = cut(P.bearing, P.WIRE_EXIT_DEG, ur, zr); fill(ax, u, z, b9, silver)
        if n == 10:
            ax.set_title('BEFORE, set 10: the shelf ring (orange) drops in; the lane under it is empty', fontsize=10)
            note(ax, -31, -41.8, ['The ring sat on a ledge, keyed by a 2.5 rib, held down by nothing. Upside down (for the',
                                  "small gear and the floor plate) it could fall out. Right of the axis: the wires' old exit",
                                  'hole through the boss, unused since they go down the middle.'], red)
        else:
            ax.set_title('AFTER, set 11: one base, the lane filled to the ribbon\'s floor', fontsize=10)
            note(ax, -31, -41.8, ["The fill and the ring's cup wall print with the base: nothing to fall out, nothing",
                                  'overhanging. The boss and the exit hole are gone. The 6704 (gold) still drops in',
                                  'from above, through a %.1f hole round the drum, before the drum goes in.' % (2 * P.PASS_R)], blue)
        ax.set_aspect('equal'); ax.set_xlim(*ur); ax.set_ylim(-52, 8)
        ax.set_xlabel('mm along the cut, through the pan axis; + toward -145 deg, where the exit hole was', fontsize=8)
    # row 2: looking down on a slice at the old lane's mid-height
    for col, n in enumerate((10, 11)):
        setn(n)
        ax = axs[1, col]; rng = (-32, 32)
        x, b = plan(P.base, P.LANE_ZC, rng); fill(ax, x, x, b, grey)
        _, d = plan(P.drum, P.LANE_ZC, rng); fill(ax, x, x, d, teal, 0.85)
        ax.add_patch(plt.Circle((0, 0), P.B6704_OD / 2, fill=False, ec=gold, lw=1.2, ls='--'))
        if n == 10:
            ax.set_title('BEFORE: from above, a slice through the lane (Z %.1f)' % P.LANE_ZC, fontsize=10)
            note(ax, -31, -33, ['The empty lane round the drum (teal), the exit hole out through the boss at lower left.',
                                "Gold dashed: the 6704's outside, under this slice."], red)
        else:
            ax.set_title('AFTER: the same slice, solid', fontsize=10)
            note(ax, -31, -33, ["Only the 6704's way through is left round the drum: %.2f clear of it, %.2f of the drum."
                                % (P.PASS_R - P.B6704_OD / 2, P.PASS_R - P.DRUM_R),
                                'The outside is round where the boss stood.'], blue)
        ax.set_aspect('equal'); ax.set_xlim(*rng); ax.set_ylim(-38, 32)
    fig.text(0.01, 0.004, "Z up as assembled. Grey: the base. Orange: set 10's shelf ring. Teal: the drum. Gold: the 6704. "
             "Silver: the 6809.\nSet 11 guesses: the 6704 drops through the %.1f hole freely (0.25 a side, holes print small); "
             "the ribbon's inner wrap rides on the drum over the %.2f gap and doesn't drop into it."
             % (2 * P.PASS_R, P.PASS_R - P.DRUM_R), fontsize=9)
    plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig(os.path.join(OUT, 'set11.png'), dpi=72); plt.close(fig)
    print('wrote set11.png')
