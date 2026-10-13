"""Pan coil set 5 (2026-10-02): the drum's wire notch and funnel, before/after picture sheet into
head-v2/out/print-pan/. The print files come from pan_print_set.py (plate_pan_coil_set5.3mf).

The printed cradle's wire hole lets the wires out in front of the ribbon; set 4's drum hole starts behind
it, and the ribbon's edge sat 0.7 from the bore wall. Set 5 notches the bore wall on -Y (pan_coil_b.NOTCH_*)
so the wires pass the edge, and funnels the hole's mouth (FUNNEL_*). Check: checks/wire_route.py row 7.
The wires' drawn path is the widest one row 7's flood fill finds (pan_coil_b.HANDOVER_PTS).

    python head-v2/generator/generators/pan_coil_b.py drum
    python head-v2/generator/generators/pan_coil_b_print.py drum
    python head-v2/fixes/pan_print_set.py
    python head-v2/fixes/drum_notch_set5.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pan_coil_b as P, tree_parts_b as B
import slices
from wire_route_r2 import objtris
from pan_print_set import OUT

OLD = os.path.join(OUT, 'superseded - set 4 drum before wire notch', '_viewer_drum_set4.obj')
NEW = os.path.join(config.REPO, 'head-v2', 'generator', 'pan-coil-b', 'fusion', 'drum.obj')

if __name__ == '__main__':
    fig, axs = plt.subplots(2, 2, figsize=(13, 12))
    route = P._centripetal(P.HANDOVER_PTS, 8)
    R = np.array(B.bezier(B.TROUGH_PATH, 200))
    mx, my = P._mouth()
    for row, (tag, path) in enumerate((('BEFORE (set 4)', OLD), ('AFTER (set 5)', NEW))):
        T = objtris(path)
        ax = axs[row, 0]                                     # top section just under the cradle
        m, u, v, _ = slices.slice2d(T, 2, 8.0, (-16, -16), (16, 16), h=0.05)
        ax.contourf(u, v, m.T.astype(float), levels=[0.5, 2], colors=['#3e9c8f'])
        ax.add_patch(plt.Rectangle((-1.0, -8.0), 0.6, 16.0, color='#e0a030'))
        ax.text(-0.4, 8.6, 'ribbon (16)', color='#b06a00', fontsize=9, ha='center')
        if row:
            ax.plot(route[:, 0], route[:, 1], color='#e0443e', lw=2)
            ax.text(1.0, -13.8, 'wires: past the ribbon\'s -Y edge, down the notch behind it', color='#e0443e', fontsize=9)
        else:
            ax.text(1.0, -13.8, 'ribbon\'s edge 0.7 from the wall: no way round', color='#e0443e', fontsize=9)
        ax.add_patch(plt.Circle((mx, my), P.WIRE_R, fill=False, ls='--', color='#e0443e'))
        ax.set_title('%s: top section at Z 8 (under the cradle). +X lens, +Y post' % tag, fontsize=10)
        ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.set_xlim(-16, 16); ax.set_ylim(-16, 16)
        ax = axs[row, 1]                                     # vertical section through the funnel, along X
        m, u, v, _ = slices.slice2d(T, 1, my, (-16, -8), (16, 12), h=0.05)
        ax.contourf(u, v, m.T.astype(float), levels=[0.5, 2], colors=['#3e9c8f'])
        ax.plot(R[:, 0], R[:, 1], color='#e0a030', lw=2.5)
        ax.text(0.5, 4.0, 'ribbon, then\non to its slot', color='#b06a00', fontsize=9)
        ax.set_title('%s: section at Y %.1f, through the wire hole\'s mouth' % (tag, my), fontsize=10)
        ax.set_aspect('equal'); ax.grid(alpha=0.3); ax.set_xlim(-16, 16); ax.set_ylim(-8, 12)
    fig.text(0.01, 0.005, 'Teal: drum. Orange: the ribbon (its groove path; below Z 5 it turns toward the slot at +X, not '
             'modelled).\nRed: the wires\' route and the drum hole\'s mouth (5 mm). Set 5: notch r 14 at -150..-72 deg, '
             'its floor 55 deg down to the bore; funnel 7 mm, 2 deep, round the hole\'s own line.', fontsize=9)
    plt.tight_layout(rect=(0, 0.035, 1, 1)); plt.savefig(os.path.join(OUT, 'drum_notch_set5.png'), dpi=75); plt.close(fig)
    print('wrote drum_notch_set5.png')
