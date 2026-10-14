"""Workstream E: replacement spacers (2026-10-14). The first ones broke coming out: 0.25 mm of radial play, a grip
slot 2 mm deep, 10% infill. These have 0.5 mm of play, a 0.5 mm chamfer at both ends, and an M3 pilot hole in the
end that faces the opening: turn an M3 screw in a few turns and pull. Dots on the other end say which body (1, 2, 3).
Same lengths as before, so the coins sit where they did.

    python research/tumble/spacers_v2.py   -> research/models/spacer_v2_E1.stl, _E2.stl, _E3.stl (print standing, hole up)
"""
import os, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
import sys; sys.path.insert(0, HERE)
import scale_model as S

PLAY = 0.5                    # radial
PILOT_D, PILOT_DEPTH = 2.5, 8.0
CHAMFER = 0.5


def spacer(length, dots):
    import cadquery as cq
    r = S.POCKET_R - PLAY
    s = cq.Workplane('XY').circle(r).extrude(length).edges().chamfer(CHAMFER)
    s = s.faces('>Z').workplane().hole(PILOT_D, min(PILOT_DEPTH, length - 3.0))
    for i in range(dots):                                  # ID dots on the bottom face, which prints on the plate
        s = s.cut(cq.Workplane('XY').center(-4.0 + 4.0 * i, -6.0).circle(0.9).extrude(0.6))
    return s


if __name__ == '__main__':
    import cadquery as cq
    for i, n in enumerate(('E1_tub', 'E2_dome', 'E3_tall'), 1):
        k = json.load(open(os.path.join(ROOT, 'models', n + '.json')))['pockets'][0]
        s = spacer(k['spacer'], i)
        p = os.path.join(ROOT, 'models', f'spacer_v2_E{i}.stl')
        cq.exporters.export(s, p, tolerance=0.02, angularTolerance=0.1)
        bb = s.val().BoundingBox()
        print(f'E{i}: length {k["spacer"]} mm, diameter {2 * (S.POCKET_R - PLAY):.2f} in a {2 * S.POCKET_R:.2f} pocket, '
              f'volume {s.val().Volume() / 1000:.2f} cm3, valid {s.val().isValid()}, bbox z {bb.zmin:.1f}-{bb.zmax:.1f}')
