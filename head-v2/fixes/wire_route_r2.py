"""The tilt servo's wire route, round 2 (2026-10-02): the wires' own lane in the pan coil. Tool bodies and a
before/after picture sheet, into head-v2/out/print-pan/. The print files are pan coil set 4
(fixes/pan_print_set.py: base.stl, drum.stl, plate_pan_coil_set4.3mf).

The wires come down the drum's bore beside the ribbon, down a 5 mm hole in the drum's core, and roll in a
lane of their own under the ribbon: 3.5 tall, its own wall at r 21 (a 9 mm gap, so the moving U is ~3.6
radius), under a fixed 0.8 shelf the ribbon now sits on. They leave through a boss at -145 deg. The floor
dropped 4.3; the gears, the servo, the floor plate and the tab block didn't move.

    python head-v2/generator/generators/pan_coil_b.py            # viewer meshes
    python head-v2/generator/generators/pan_coil_b_print.py drum base
    python head-v2/fixes/pan_print_set.py
    python head-v2/fixes/wire_route_r2.py
    python head-v2/checks/wire_route.py                           # rounds 1 and 2, with controls
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
import cadquery as cq
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import pan_coil_b as P
from vox import load_stl
import slices
from wire_route_r1 import tube_solid
from pan_print_set import OUT

OLD = os.path.join(OUT, 'superseded - set 3 before wire lane')
NEW = os.path.join(config.REPO, 'head-v2', 'generator', 'pan-coil-b', 'fusion')


def objtris(path):
    V, F = [], []
    for l in open(path):
        if l.startswith('v '):
            V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('f '):
            F.append([int(x.split('/')[0]) - 1 for x in l.split()[1:4]])
    return np.array(V)[np.array(F)]


def tools():
    """Tool bodies in the pan frame (Z 0 at the deck top, pan axis at the origin), for reference in Fusion."""
    lane = (cq.Workplane('XY').workplane(offset=P.LANE_Z0).circle(P.LANE_R).circle(P.DRUM_R)
            .extrude(P.LANE_H).val())
    return {'CUT_base_wire_lane': lane,
            'CUT_drum_wire_hole_5mm': tube_solid(P._centripetal(P.DRUM_WIRE_PTS, 2), P.WIRE_R),
            'CUT_base_wire_exit_5mm': tube_solid(P._centripetal(P.BASE_WIRE_PTS, 2), P.WIRE_R)}


def sheet(path):
    before = {'well': objtris(os.path.join(OLD, '_viewer_well_set3.obj')),
              'drum': objtris(os.path.join(OLD, '_viewer_drum_set3.obj'))}
    after = {'well': objtris(os.path.join(NEW, 'well.obj')), 'drum': objtris(os.path.join(NEW, 'drum.obj'))}
    col = {'well': '#a3a8a2', 'drum': '#3e9c8f'}
    fig, axs = plt.subplots(2, 2, figsize=(16, 13))
    a = np.radians(P.WIRE_EXIT_DEG)
    for row, (tag, M) in enumerate((('BEFORE (set 3)', before), ('AFTER (set 4)', after))):
        # 1. a vertical section through the exit's direction: radius along -145 deg, Z up
        ax = axs[row, 0]
        for k, T in M.items():
            R = np.array([[np.cos(-a), -np.sin(-a), 0], [np.sin(-a), np.cos(-a), 0], [0, 0, 1]])
            Tr = T @ R.T                                    # the exit's direction onto +X
            m, u, v, _ = slices.slice2d(Tr, 1, 0.0, (-32, -32), (32, 4), h=0.1)
            ax.contourf(u, v, m.T.astype(float), levels=[0.5, 2], colors=[col[k]])
        ax.axhspan(P.BAND_Z0, P.BAND_Z1, xmin=0, xmax=1, color='#e07a2f', alpha=0.08)
        ax.text(-31, -11, 'ribbon band', color='#c05a10', fontsize=8)
        if row:
            ax.add_patch(plt.Circle((16.5, P.LANE_ZC), 1.4, color='#e0443e'))
            ax.add_patch(plt.Circle((-16.5, P.LANE_ZC), 1.4, color='#e0443e'))
            ax.text(13, P.LANE_ZC - 4.5, 'wires\' lane', color='#e0443e', fontsize=9)
            ax.text(-31, P.LANE_ZC + 2.3, 'shelf: the ribbon sits on it', fontsize=8)
        ax.set_title('%s: section through the pan axis, along the wires\' exit (-145 deg; exit to the right)' % tag, fontsize=10)
        ax.set_xlabel('radius along the exit'); ax.set_ylabel('Z'); ax.set_aspect('equal'); ax.grid(alpha=0.3)
        ax.set_xlim(-32, 32); ax.set_ylim(-32, 4)
        # 2. top section at the lane's height
        ax = axs[row, 1]
        for k, T in M.items():
            m, u, v, _ = slices.slice2d(T, 2, P.LANE_ZC, (-32, -32), (32, 32), h=0.1)
            ax.contourf(u, v, m.T.astype(float), levels=[0.5, 2], colors=[col[k]])
        if row:
            for L in (P.DRUM_WIRE, P.BASE_WIRE):
                ax.plot(L[:, 0], L[:, 1], color='#e0443e', lw=1.5)
            ax.add_patch(plt.Circle((0, 0), P.LANE_R, fill=False, ls='--', color='#e0443e', lw=0.8))
        ax.add_patch(plt.Circle((0, 0), P.WELL_IR, fill=False, ls=':', color='k', lw=0.8))
        ax.set_title('%s: top section at Z %.1f (the lane\'s middle). Dotted: the ribbon\'s wall' % (tag, P.LANE_ZC), fontsize=10)
        ax.set_xlabel('X'); ax.set_ylabel('Y'); ax.set_aspect('equal'); ax.grid(alpha=0.3)
        ax.set_xlim(-32, 32); ax.set_ylim(-32, 32)
    fig.text(0.01, 0.005, 'Grey: base (well). Teal: drum. Red: the wires and their holes (5 mm). The lane is 3.5 tall with its own wall '
             'at r 21 (9 mm gap); the floor dropped 4.3 mm, nothing below it moved.', fontsize=10)
    plt.tight_layout(rect=(0, 0.02, 1, 1)); plt.savefig(path, dpi=75); plt.close(fig)


if __name__ == '__main__':
    asm = cq.Assembly(name='wire_route_r2')
    for nm, s in tools().items():
        asm.add(cq.Workplane(obj=s), name=nm, color=cq.Color(0.85, 0.2, 0.2, 0.6))
    asm.save(os.path.join(OUT, 'wire_route_r2_tools_for_fusion.step')); print('wrote wire_route_r2_tools_for_fusion.step')
    sheet(os.path.join(OUT, 'wire_route_r2.png')); print('wrote wire_route_r2.png')
