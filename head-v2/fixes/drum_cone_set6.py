"""Pan coil set 6 (2026-10-03): the drum's bore floor as a cone, and the input gear on the spline. Moves set 5's
drum, input gear and plate into a superseded folder, and draws the before/after picture sheet into
head-v2/out/print-pan/. The print files come from pan_print_set.py (plate_pan_coil_set6.3mf).

Zach, after assembling set 5: the drum's bore needed supports he couldn't get out ("make this circular at an
angle no greater than 30deg"), and the input gear "does not fit, no screw long enough to reach". The drum
prints top face down, so set 5's flat bore floor was an 18 mm ceiling over tree supports. Set 6's floor is a
cone 30 deg off vertical with the wire hole at its point (pan_coil_b.CONE_*, DRUM_WIRE_PTS), and the notch
floor is steepened to the same 30. The gear's horn pocket was a generic placeholder whose roof stopped the
shaft; the spline now presses into the gear like post v3 (pan_coil_b.SPL_*). Checks: checks/wire_route.py
row 7, checks/pan_servo_fit.py, pan_coil_b_check.py.

    python head-v2/generator/generators/pan_coil_b.py drum gear_in
    python head-v2/generator/generators/pan_coil_b_print.py drum gear_in
    python head-v2/fixes/drum_cone_set6.py --supersede
    python head-v2/fixes/pan_print_set.py
    python head-v2/fixes/drum_cone_set6.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import shutil
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pan_coil_b as P
from pan_print_set import OUT

OLD = 'superseded - set 5 drum and input gear (bore supports, gear screw short)'
MOVE = ['drum.stl', 'input_gear.stl', 'plate_pan_coil_set5.3mf', 'drum_notch_set5.png']


def supersede():
    os.makedirs(os.path.join(OUT, OLD), exist_ok=True)
    for f in MOVE:
        src = os.path.join(OUT, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(OUT, OLD, f)); print('moved %s -> %s/' % (f, OLD))


def section(fn, axis_pt, u_dir, u_rng, z_rng, h=0.05):
    """fn sampled on the vertical plane through axis_pt spanned by u_dir (horizontal) and Z."""
    u = np.arange(*u_rng, h); z = np.arange(*z_rng, h)
    U_, Z_ = np.meshgrid(u, z, indexing='ij')
    X = axis_pt[0] + U_ * u_dir[0]; Y = axis_pt[1] + U_ * u_dir[1]
    return u, z, (fn((X, Y, Z_)) < 0)


def set5(on):
    """flip the module between set 5 (on=True) and set 6"""
    P.CONE, P.SPLINE_GEAR = not on, not on
    P.NOTCH_FLOOR_DEG = 55.0 if on else 60.0
    P.DRUM_WIRE = P._centripetal(P.DRUM_WIRE_PTS_SET5 if on else P.DRUM_WIRE_PTS)


if __name__ == '__main__':
    if '--supersede' in sys.argv:
        supersede(); sys.exit(0)
    fig, axs = plt.subplots(2, 2, figsize=(13, 11.5))
    teal, red, grey = '#3e9c8f', '#e0443e', '#8a8f88'
    # the drum: the plane through the axis and the wire holes (155 deg), as the drum sits (it prints upside down)
    a = np.radians(155.0); d = (np.cos(a), np.sin(a))
    for col, (tag, old) in enumerate((('BEFORE (set 5, printed)', True), ('AFTER (set 6)', False))):
        set5(old)
        ax = axs[0, col]
        u, z, m = section(P.drum, (0, 0), d, (-15, 15), (-26, 11))
        ax.contourf(u, z, m.T.astype(float), levels=[0.5, 2], colors=[teal])
        if old:
            ax.fill_between([-9, 9], -2.5, 10.5, color=red, alpha=0.18, lw=0)
            ax.text(0, 4.0, 'tree supports filled this\n(drum prints upside down:\nthe flat floor is a ceiling)',
                    ha='center', fontsize=9, color=red)
        else:
            t = np.tan(np.radians(P.CONE_DEG))
            ax.plot([-9, 0, 9], [P.BORE_Z0, P.CONE_APEX_Z, P.BORE_Z0], color=red, lw=1, ls='--')
            ax.text(0, 2.0, 'cone, 30 deg off vertical:\nprints with nothing under it.\nIts point is the wire hole',
                    ha='center', fontsize=9, color=red)
            ax.annotate('wires slide to\nthe hole', (-1.2, -14.5), (-13.5, -9), fontsize=9, color=red,
                        arrowprops=dict(arrowstyle='->', color=red))
        L = P.DRUM_WIRE; s = L[:, 0] * d[0] + L[:, 1] * d[1]
        ax.plot(s, L[:, 2], color=red, lw=1.2)
        ax.axhline(P.LANE_Z0, color=grey, lw=0.8, ls=':'); ax.text(14.6, P.LANE_Z0 + 0.3, 'lane floor', ha='right', fontsize=8, color=grey)
        ax.set_title('%s: drum, section through the axis at 155 deg (wire hole, red line)' % tag, fontsize=10)
        ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.set_xlim(-15, 15); ax.set_ylim(-26, 11)
    # the input gear: the plane through its axis, with his MG90S's shaft and block, and a 4 mm screw
    for col, (tag, old) in enumerate((('BEFORE (placeholder horn pocket)', True), ('AFTER (set 6: spline straight in)', False))):
        set5(old)
        ax = axs[1, col]
        u, z, m = section(P.gear_in, (P.CENTRE, 0), (1.0, 0.0), (-9, 9), (-39.5, -28.5), h=0.02)
        ax.contourf(u, z, m.T.astype(float), levels=[0.5, 2], colors=[teal])
        tip = P.SV_Z0 - P.SV_SHAFT
        ax.add_patch(plt.Rectangle((-P.SV_SHAFT_R, tip), 2 * P.SV_SHAFT_R, P.SV_Z0 - P.SV_HUMP_H - tip, color='#5a6e9e', alpha=0.8))
        ax.add_patch(plt.Rectangle((-9, P.SV_Z0 - P.SV_HUMP_H), 18, 0.8, color='#5a6e9e', alpha=0.5))
        ax.text(0, P.SV_Z0 - P.SV_HUMP_H + 1.0, 'servo block (his MG90S)', ha='center', fontsize=8, color='#334')
        if old:
            ax.text(-8.6, -38.9, 'the shaft runs 0.8 into the pocket\'s roof, so the gear\nhangs low and the screw can\'t reach', fontsize=8.5, color=red)
            ax.add_patch(plt.Rectangle((-P.SV_SHAFT_R, tip), 2 * P.SV_SHAFT_R, (P.G_Z1 - P.HORN_D) - tip,
                                       fill=False, ec=red, lw=1.5))                      # the shaft in the roof
        else:
            lip0 = tip - P.SPL_LIP
            ax.add_patch(plt.Rectangle((-1.0, lip0), 2.0, 4.0, color='#333', alpha=0.55))           # a 4 mm screw's shank
            ax.add_patch(plt.Rectangle((-2.0, lip0 - 1.4), 4.0, 1.4, color='#333', alpha=0.55))     # its head
            ax.text(-8.6, -39.2, 'spline presses in (bore 4.44, post v3\'s); a 1.5 lip under its tip;\n'
                    'the servo\'s own screw: 1.5 of lip + 2.5 into the shaft', fontsize=8.5, color=red)
        ax.set_title('%s: input gear, section through its axis' % tag, fontsize=10)
        ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.set_xlim(-9, 9); ax.set_ylim(-39.5, -28.5)
    set5(False)
    fig.text(0.01, 0.005, 'Teal: printed part. Blue: Zach\'s MG90S model (shaft 10.0 past the case face). Red: the wires\' hole '
             '(top) and notes. Z up, as assembled; the drum prints upside down.\nSet 6 guesses: the 30 deg cone (his '
             'number), the hole\'s new path, the gear bore 4.44 (post v3\'s press fit), the lip 1.5, the screw ~4 mm.',
             fontsize=9)
    plt.tight_layout(rect=(0, 0.04, 1, 1)); plt.savefig(os.path.join(OUT, 'drum_cone_set6.png'), dpi=75); plt.close(fig)
    print('wrote drum_cone_set6.png')
