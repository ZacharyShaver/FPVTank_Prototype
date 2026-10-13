"""Pan coil set 8 (2026-10-09): the gear's screw squeezes the seat instead of pulling it off, the seat is a square,
and the wires go through the drum down a straight hole. Moves set 6's drum and the D-bore small gear into a
superseded folder, builds the second small gear (the loose fit), and draws the before/after sheet into
head-v2/out/print-pan/. The print files come from pan_print_set.py (plate_pan_coil_set8.3mf).

Zach: the seat at the end of the drum's barrel "keeps snapping", when he tightens the screw; threading the wires
"is a massive pain", stuck at the cone; and he asked for "a square going in so it grips better". See
pan_coil_b.SCREW_THRU, SEAT_SQUARE, STRAIGHT_WIRE. Checks: pan_coil_b_check.py (screw_threads), checks/wire_route.py
rows 4, 6 and 7.

    python head-v2/generator/generators/pan_coil_b.py drum gear_out screw_out
    python head-v2/generator/generators/pan_coil_b_print.py drum gear_out
    python head-v2/fixes/drum_set8.py --supersede
    python head-v2/fixes/drum_set8.py --loose-gear
    python head-v2/fixes/pan_print_set.py
    python head-v2/fixes/drum_set8.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import shutil
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pan_coil_b as P
from pan_print_set import OUT

OLD = 'superseded - set 6 drum and D small gear (seat snapped off, curved wire hole)'
MOVE = ['drum.stl', 'small_gear.stl', 'drum_cone_set6.png', 'plate_pan_coil_set6.3mf']   # set 6's input gear stays
LOOSE = os.path.join(P.OUT, 'print', 'gear_out_loose.stl')
RI_W, RO_W = 12.85, 20.25          # the wire bundle's centre on the drum and on the lane wall (pan_coil_b.WIRE_L)


def supersede():
    os.makedirs(os.path.join(OUT, OLD), exist_ok=True)
    for f in MOVE:
        src = os.path.join(OUT, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(OUT, OLD, f)); print('moved %s -> %s/' % (f, OLD))


def loose_gear():
    """The small gear at the second fit (SQ_FITS[1]), as its own print file."""
    import pan_coil_b_print as PP
    keep = P.SQ_FIT; P.SQ_FIT = P.SQ_FITS[1]
    ok = PP.build('gear_out'); P.SQ_FIT = keep
    shutil.move(os.path.join(PP.OUT, 'gear_out.stl'), LOOSE)
    print('wrote %s' % LOOSE)
    PP.build('gear_out')                            # and the snug one back in place
    return ok


def crossing(line, r):
    """Angle (deg) where a centreline first crosses radius r."""
    rr = np.hypot(line[:, 0], line[:, 1]); i = np.argmax(rr >= r) if rr[0] < r else np.argmax(rr <= r)
    return np.degrees(np.arctan2(line[i, 1], line[i, 0]))


def loop(a_drum, a_base, L=P.WIRE_L):
    """The wires' rolling loop in the lane: the inner wrap runs CW from the drum's exit to the U, the outer wrap
    CCW from the U to the base's exit. Every way of laying L mm that fits, as (inner, outer, pan CW, pan CCW) in
    degrees: how far the head can turn each way from straight ahead before the U reaches an exit."""
    out = []
    for k in (-1, 0, 1):
        d = np.radians(((a_drum - a_base + 180) % 360) - 180 + 360 * k)        # inner - outer
        outer = (L - RI_W * d) / (RI_W + RO_W); inner = outer + d
        if inner >= 0 and outer >= 0:
            out.append(tuple(np.degrees(v) for v in (inner, outer, inner * (RI_W + RO_W) / RO_W, outer * (RI_W + RO_W) / RI_W)))
    return out


def seat_play(seat, bore, h=0.005):
    """How far the gear turns on its seat, end to end (deg): the seat's cross-section turned both ways until some of
    it leaves the gear's bore. Both are 2D distances, negative inside."""
    x = np.arange(-5, 5, h); X, Y = np.meshgrid(x, x); m = seat((X, Y)) < 0; xs, ys = X[m], Y[m]; tot = 0.0
    for s in (1, -1):
        t = 0.0
        while t < 15 and not (bore((xs * np.cos(np.radians(s * t)) - ys * np.sin(np.radians(s * t)),
                                    xs * np.sin(np.radians(s * t)) + ys * np.cos(np.radians(s * t)))) > 0).any():
            t += 0.02
        tot += t
    return tot


def plays():
    D = lambda r, f: (lambda p: np.maximum(np.hypot(p[0], p[1]) - r, p[0] - f))
    sq = lambda f: (lambda p: P.rsquare(p, P.SQ_H + f, P.SQ_RC + f))
    print('gear turning on its seat, end to end: the D at 0.15 (set 2-7) %.1f deg' % seat_play(D(P.SEAT_R, P.SEAT_FLAT),
          D(P.SEAT_R + P.SLIDE, P.SEAT_FLAT + P.SLIDE)), end='')
    for f in P.SQ_FITS:
        print('; the square at %.2f a side %.1f' % (f, seat_play(sq(0.0), sq(f))), end='')
    print('; control, a bore 0.05 under the square: %.1f (binds)' % seat_play(sq(0.0), sq(-0.05)))


def section(fn, deg, u_rng, z_rng, h=0.05):
    a = np.radians(deg); u = np.arange(*u_rng, h); z = np.arange(*z_rng, h)
    U, Z = np.meshgrid(u, z)
    return u, z, fn((U * np.cos(a), U * np.sin(a), Z))


def setn(n):
    """flip the module between set 7 (n=7, as printed: set 6's drum and the D gear) and set 8"""
    on = n == 8
    P.SCREW_THRU = P.SEAT_SQUARE = P.STRAIGHT_WIRE = on
    P.SCREW_L = 12.0 if on else 8.0


if __name__ == '__main__':
    if '--supersede' in sys.argv:
        supersede(); sys.exit(0)
    if '--loose-gear' in sys.argv:
        sys.exit(0 if loose_gear() else 1)
    plays()
    a_base = crossing(P.BASE_WIRE, P.LANE_R - 0.5)
    for tag, line in (('set 7', P.DRUM_WIRE), ('set 8', P.GROOVE_LINE)):
        a = crossing(line, P.DRUM_R)
        for inner, outer, cw, ccw in loop(a, a_base):
            print('%s: drum exit %.0f deg, base %.0f: inner wrap %.0f, outer %.0f -> the head turns %.0f CW, %.0f CCW%s'
                  % (tag, a, a_base, inner, outer, cw, ccw, '' if min(cw, ccw) >= 180 else '   <-- short of 180'))
    teal, red, grey, blue, dark = '#3e9c8f', '#e0443e', '#8a8f88', '#4a6fa5', '#333'
    fig, axs = plt.subplots(2, 3, figsize=(16, 11))
    for col, n in enumerate((7, 8)):
        setn(n)
        # the seat, the gear and the screw, cut through the axis
        ax = axs[0, col]
        u, z, d = section(P.drum, 0.0, (-7, 7), (-40, -22), 0.02)
        ax.contourf(u, z, (d < 0).astype(float), levels=[0.5, 2], colors=[teal])
        _, _, g = section(P.gear_out, 0.0, (-7, 7), (-40, -22), 0.02)
        ax.contourf(u, z, (g < 0).astype(float), levels=[0.5, 2], colors=['#9cc9c0'])
        _, _, s = section(P.screw_out, 0.0, (-7, 7), (-40, -22), 0.02)
        ax.contourf(u, z, (s < 0).astype(float), levels=[0.5, 2], colors=[dark], alpha=0.6)
        z0, z1 = (P.G_Z1, P.G_Z0 + P.SCREW_L) if n == 8 else (P.SEAT_Z0, P.G_Z0 + P.SCREW_L)
        ax.add_patch(plt.Rectangle((-1.5, z0), 3.0, z1 - z0, color=(red if n == 7 else blue), alpha=0.35, lw=0))
        ax.axhline(P.G_Z1, color=grey, lw=0.8, ls=':')
        ax.text(6.8, P.G_Z1 + 0.25, 'the step', ha='right', fontsize=8, color=grey)
        if n == 7:
            ax.text(-6.8, -42.6, 'M3 x 8: 4.2 of its thread in the seat, below the step.\nTightening pulls the seat off '
                    'across the layers.', fontsize=8.5, color=red)
            ax.set_title('BEFORE (set 6 drum, printed): the seat snaps when the screw is tightened', fontsize=10)
        else:
            ax.text(-6.8, -42.6, 'M3 x 12: a clear hole through the seat, all 5.8 mm of thread in\nthe barrel. '
                    'Tightening squeezes the step; the seat only turns the gear.', fontsize=8.5, color=blue)
            ax.set_title('AFTER (set 8): clear hole in the seat, the thread above the step', fontsize=10)
        ax.set_aspect('equal'); ax.set_xlim(-7, 7); ax.set_ylim(-43, -22)
    # the seat across, in the gear: D before, square after
    ax = axs[0, 2]
    x = np.arange(-6, 6, 0.02); X, Y = np.meshgrid(x, x); Z = np.full_like(X, -33.5)
    for n, c, ls in ((7, red, '--'), (8, blue, '-')):
        setn(n)
        ax.contour(x, x, (P.drum((X, Y, Z)) < 0).astype(float), [0.5], colors=[c], linestyles=[ls], linewidths=1.4)
        ax.contour(x, x, (P.gear_out((X, Y, Z)) < 0).astype(float), [0.5], colors=[c], linestyles=[ls], linewidths=0.7)
    ax.add_patch(plt.Circle((0, 0), P.BARREL_R, fill=False, ec=grey, ls=':'))
    ax.text(-5.8, -5.8, 'red dashed: the D (set 6). blue: the square (set 8),\n7.0 across, corners r %.1f reach r %.2f, inside '
            'the barrel (dotted).\nThe gear\'s bore is %.2f a side bigger (a %.2f one too).'
            % (P.SQ_RC, (P.SQ_H - P.SQ_RC) * 2 ** 0.5 + P.SQ_RC, P.SQ_FITS[0], P.SQ_FITS[1]), fontsize=8)
    ax.set_title('The seat across, in the small gear (Z -33.5)', fontsize=10)
    ax.set_aspect('equal'); ax.set_xlim(-6, 6); ax.set_ylim(-6, 6)
    # the wires' way through the drum
    for col, (n, deg) in enumerate(((7, 155.0), (8, P.DROP_DEG))):
        setn(n)
        ax = axs[1, col]
        u, z, d = section(P.drum, deg, (-15, 15), (-26, 11))
        ax.contourf(u, z, (d < 0).astype(float), levels=[0.5, 2], colors=[teal])
        a = np.radians(deg); dv = (np.cos(a), np.sin(a))
        L = P.DRUM_WIRE if n == 7 else np.vstack([P.DROP_LINE, P.GROOVE_LINE])
        ax.plot(L[:, 0] * dv[0] + L[:, 1] * dv[1], L[:, 2], color=red, lw=1.4)
        ax.axhline(P.LANE_Z0, color=grey, lw=0.8, ls=':'); ax.text(14.6, P.LANE_Z0 + 0.3, 'lane floor', ha='right', fontsize=8, color=grey)
        if n == 7:
            ax.text(-14.5, -29.8, 'the hole starts at the cone\'s point and turns from\nstraight down to sideways, '
                    'out of sight:\nstiff copper jams in the bend', fontsize=8.5, color=red)
            ax.set_title('BEFORE: section at 155 deg (the hole spirals; red, its path)', fontsize=10)
        else:
            ax.text(-14.5, -29.8, 'a straight hole beside the cone, under where the\nwires come down; out through '
                    'the underside', fontsize=8.5, color=red)
            ax.set_title('AFTER: section through the axis at %.0f deg (the hole on the right)' % deg, fontsize=10)
        ax.set_aspect('equal'); ax.set_xlim(-15, 15); ax.set_ylim(-31, 11)
    # the underside: the groove takes the wires out to the lane
    setn(8)
    ax = axs[1, 2]
    x = np.arange(-15, 15, 0.05); X, Y = np.meshgrid(x, x)
    m = P.drum((X, Y, np.full_like(X, -22.5))) < 0
    ax.contourf(x, x, m.astype(float), levels=[0.5, 2], colors=[teal])
    ax.plot(P.GROOVE_LINE[:, 0], P.GROOVE_LINE[:, 1], color=red, lw=1.4)
    ax.plot(*P.DROP_XY, 'o', color=red, ms=5)
    ax.add_patch(plt.Circle((0, 0), P.BARREL_R, fill=False, ec=dark, lw=0.8))
    ax.text(0, 0, 'barrel', ha='center', va='center', fontsize=8, color='w')
    ax.text(-14.5, -19.5, 'open groove: bend the wires out of the hole into it,\nthen drop the drum in. They leave '
            'the drum heading\nclockwise (seen from above), the way they wrap.', fontsize=8.5, color=red)
    ax.set_title('AFTER: the drum cut 1.4 mm above its underside, from above', fontsize=10)
    ax.set_aspect('equal'); ax.set_xlim(-15, 15); ax.set_ylim(-21, 15)
    fig.text(0.01, 0.005, 'Teal: the drum. Pale teal: the small gear. Dark: the screw; its thread zone red (set 7) or blue '
             '(set 8). Z up, as assembled; the drum prints upside down.\nSet 8 guesses: the square %.1f across with r %.1f '
             'corners; the gear\'s fit (%.2f snug, %.2f loose, a side); M3 x 12 (from your 2026-09-27 list); the hole '
             'at r %.1f, %.0f deg; the groove %.1f wide and %.1f deep.'
             % (2 * P.SQ_H, P.SQ_RC, P.SQ_FITS[0], P.SQ_FITS[1], P.DROP_R, P.DROP_DEG, 2 * P.WIRE_R,
                P.GROOVE_Z1 - (P.LANE_Z0 + P.DRUM_LIFT)), fontsize=9)
    plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig(os.path.join(OUT, 'drum_set8.png'), dpi=72); plt.close(fig)
    print('wrote drum_set8.png')
