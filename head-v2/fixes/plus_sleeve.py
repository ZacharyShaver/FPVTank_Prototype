"""The +Y hub as its own part (2026-10-03), so the ball drops into the cradle without bending the +Y arm.

Zach: the cradle's +Y arm "keeps snapping. it has to be bent for it to fit". Measured: his ball_plus's hub
(r 8.0..9.95, the ring the +Y 6704 rides on) stands from the ball's flat face at Y 24.5 out to 30.3,
but the collar's inboard face is at Y 25.1..25.4. The -Y side has under 1 mm to give, so the +Y arm has
to spread about 5 mm to get the ball past the hub (checks/plus_sleeve_fit.py, row 1).

So the hub comes off his ball_plus, leaving a 2 mm socket in its flat face, and is printed as a sleeve that
goes in from outside after the ball is seated, like the -Y stub. The 6704 goes into the collar's seat over
the sleeve as before, then post v3 as before. Cradle, post, servo and bearings are unchanged.
Zach chose this over moving the bearing into a cup in the ball, which would have moved the servo ~6 mm.

  CUT_plus_hub     the hub, r 7.6..10.1 from Y 24.45 out past its end (30.3), plus a 1.5 mm socket
                   (Y 23.0..24.5) keyed by a flat at X +9.0 (the lens side)
  sleeve           bore r 8.0 (his hub's), Y 23.3..31.9, with his hub's notch for the servo's gear bump (a
                   r 2.98 circle at X -5.93: r 8.9 at -X) up to Y 27.0, and a flat on the end in the socket. The 6704
                   presses on (outside 20.0 or 20.1, two to try) up to a lip at the outer end. The first,
                   slip-fit sleeve (r 9.95 all along) was superseded the same day, never printed.

Built on out/rev2/ball_plus_rev2.brep (his rev 2 + the IR cutout extension, the one he printed; run
ball_plus_rev2.py first). Writes out/plus-sleeve/ (breps for the checks and the view) and the hand-off in
out/print-rev2/: ball_plus_sleeve.stl, sleeve_press_200.stl and _201.stl,
plate_plus_sleeve.3mf, plus_sleeve_tools_for_fusion.step.
Superseded there: ball_plus_rev2.stl (moved to "superseded - ball_plus with the hub on/").
    python head-v2/fixes/plus_sleeve.py
    python head-v2/checks/plus_sleeve_fit.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import shutil
from occ_load import load, vol
from kit import cyl, bx, fuse, cut, common
import export as E

H = 52.0
FLAT_Y = 24.5                      # his ball_plus's flat +Y face
HUB_R0, HUB_R1 = 8.0, 9.95         # his hub's bore and outside (measured on his mesh)
NOTCH_X, NOTCH_R = -5.93, 2.98     # his hub's bore notch for the servo's gear bump: r 8.9 at -X (fitted)
# Re-checked 2026-10-03 (first cut: 2.0 deep, 0.10 a side, 0.05 at the key, 0.1 off the floor). His plate is
# only ~2.2 thick at the bottom (r 9.3..10.1, -Z), so a 2.0 socket left 0.19 over the servo cavity; and his
# tested slide fit is 0.15 a side (CLAUDE.md), so every sliding gap here is at least that.
SOCKET_Y0 = 23.0                   # socket floor: 1.5 deep. Thinnest plate left: 0.69 (bottom)   GUESS
SOCKET_R = HUB_R1 + 0.15           # 10.10: the sleeve's 9.95 key end slides in at 0.15 a side
KEY_X = 9.0                        # the socket's flat, at +X (the lens side)                     GUESS
SLEEVE_KEY_X = KEY_X - 0.15        # the sleeve's flat, 0.15 off the socket's
CUT_R0 = 7.6                       # inner edge of the cut: his plate's ring r 6.1..7.6 stays, 0.4 off the
                                   # sleeve's bore (r 8.0)
SLEEVE_Y0, SLEEVE_Y1 = SOCKET_Y0 + 0.3, 31.9   # 0.3 off the socket floor (a layer and a half: the post sets
                                               # the ball's axial place, the bearing the sleeve's); 0.3
                                               # short of the post's flange underside (Y 32.2)
NOTCH_Y1 = 27.0                    # the notch ends here: the servo can't reach past post v3's inner end
                                   # (Y 26.74), and beyond it the bearing presses onto a full 2.0 wall
# Press fit (Zach, 2026-10-03: "they should be press fit"): on a 19.9 slip the sleeve just turned inside
# the 6704's inner ring, so the bearing did nothing. The inner ring presses onto the sleeve on the bench,
# from the key end, until it stops on a lip at the sleeve's outer end; the pair goes in together. The lip
# puts the ring where the collar's seat has it (Y 26.5..30.5) and touches only the inner ring.
PRESS = {'200': 10.0, '201': 10.05}  # the bearing seat's radius, two sizes to try: 20.0 and 20.1      GUESS
BRG_Y0, BRG_Y1 = 26.5, 30.5          # the 6704 in the collar's seat (tree_parts_b.BRG_P_Y0, + BRG_W)
LEAD_Y = 25.5                        # r 9.95 -> press r over Y 24.5..25.5, so the ring starts square
LIP_R = 11.0                         # the stop lip: the inner ring is r 10.0..~11.3 (typical 6704), the
                                     # outer ring starts ~12.3, the post's retaining ring 12.2
OUT = os.path.dirname(config.out('plus-sleeve', 'x'))
PRINT = os.path.dirname(config.out('print-rev2', 'x'))
BALL_PLUS = config.out('rev2', 'ball_plus_rev2.brep')
SUPERSEDED = 'superseded - ball_plus with the hub on'


def ring(r0, r1, y0, y1):
    return cut(cyl('y', (0, H), r1, y0, y1), cyl('y', (0, H), r0, y0 - 1, y1 + 1))


def cut_plus_hub():
    """the hub off, flush (0.05 into the face, so no face lies on his), and the keyed socket"""
    hub = ring(CUT_R0, SOCKET_R, FLAT_Y - 0.05, 33.0)
    sock = common(ring(CUT_R0, SOCKET_R, SOCKET_Y0, FLAT_Y), bx((-20, SOCKET_Y0 - 1, H - 20), (KEY_X, FLAT_Y + 1, H + 20)))
    return fuse(hub, sock)


def sleeve(press_r=None):
    """the hub as a part; press_r: the press-fit version with its stop lip (None: the first, slip-fit one)"""
    if press_r is None:
        s = cyl('y', (0, H), HUB_R1, SLEEVE_Y0, SLEEVE_Y1)
    else:
        from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone
        from OCP.gp import gp_Pnt, gp_Ax2, gp_Dir
        lead = BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0, FLAT_Y, H), gp_Dir(0, 1, 0)), HUB_R1, press_r, LEAD_Y - FLAT_Y).Shape()
        s = fuse(cyl('y', (0, H), HUB_R1, SLEEVE_Y0, FLAT_Y + 0.01), lead, cyl('y', (0, H), press_r, LEAD_Y - 0.01, BRG_Y1),
                 cyl('y', (0, H), LIP_R, BRG_Y1, SLEEVE_Y1))
    s = cut(s, cyl('y', (0, H), HUB_R0, SLEEVE_Y0 - 1, SLEEVE_Y1 + 1))
    s = cut(s, cyl('y', (NOTCH_X, H), NOTCH_R, SLEEVE_Y0 - 1, NOTCH_Y1))
    flat = bx((SLEEVE_KEY_X, SLEEVE_Y0 - 1, H - 20), (20, FLAT_Y, H + 20))   # the key: the end in the socket
    return cut(s, flat)


if __name__ == '__main__':
    import cadquery as cq
    from print_export import rot_x, on_bed, size
    from export_campost_rev2 import plate
    os.makedirs(OUT, exist_ok=True)
    ball = E.rd(BALL_PLUS)
    tool = cut_plus_hub()
    after = cut(ball, tool)
    slip = sleeve()
    press = {k: sleeve(r) for k, r in PRESS.items()}
    sl = press['200']
    print('ball_plus rev 2: %.0f mm3; removed %.0f mm3 (hub + socket); press sleeves %s mm3'
          % (vol(ball), vol(ball) - vol(after), ', '.join('%.0f' % vol(v) for v in press.values())))
    # out/plus-sleeve: 'sleeve' is the 20.0 press sleeve (the view, the figure and the check read it)
    for name, shape in (('ball_plus_sleeve', after), ('sleeve', sl), ('sleeve_press_201', press['201']),
                        ('sleeve_slip', slip), ('CUT_plus_hub', tool), ('ball_plus_rev2', ball)):
        E.wr(shape, os.path.join(OUT, name + '.brep'))
        E.write_stl(shape, os.path.join(OUT, name + '.stl'))
    # the hand-off: ball seam face down (+Y up), sleeves standing on the lip end (-Y up)
    for old, folder in (('ball_plus_rev2.stl', SUPERSEDED),
                        ('sleeve.stl', 'superseded - slip-fit sleeve (never printed)'),
                        ('plate_plus_sleeve.3mf', 'superseded - slip-fit sleeve (never printed)')):
        if os.path.exists(os.path.join(PRINT, old)):
            os.makedirs(os.path.join(PRINT, folder), exist_ok=True)
            shutil.move(os.path.join(PRINT, old), os.path.join(PRINT, folder, old))
    bad = 0
    for nm, s, deg in (('ball_plus_sleeve', after, 90.0), ('sleeve_press_200', press['200'], -90.0),
                       ('sleeve_press_201', press['201'], -90.0)):
        s = on_bed(rot_x(s, deg)); f = os.path.join(PRINT, nm + '.stl')
        E.write_stl(s, f, lin=0.01, ang=0.05)
        moved = E.tidy(f)
        ok, msg = E.health(f)
        print('%-17s %.1f x %.1f x %.1f mm, needle repair %.4f mm | %s' % ((nm,) + size(s) + (moved, msg)))
        bad += not ok and nm != 'ball_plus_sleeve'   # his export's 11 crossed faces ride along (README)
    bad += plate(os.path.join(PRINT, 'plate_plus_sleeve.3mf'), [('ball_plus_sleeve', [(-22.0, 0.0)]),
                 ('sleeve_press_200', [(26.0, 14.0)]), ('sleeve_press_201', [(26.0, -14.0)])])
    asm = cq.Assembly(name='plus_sleeve_tools')
    asm.add(cq.Workplane(obj=cq.Shape.cast(tool)), name='CUT_plus_hub', color=cq.Color(0.85, 0.2, 0.2, 0.6))
    asm.add(cq.Workplane(obj=cq.Shape.cast(sl)), name='SLEEVE_seated', color=cq.Color(0.72, 0.2, 0.55, 1.0))
    asm.save(os.path.join(PRINT, 'plus_sleeve_tools_for_fusion.step'))
    shutil.copyfile(os.path.join(config.FIXES, 'print_rev2_README.txt'), os.path.join(PRINT, 'README.txt'))
    print('wrote plate_plus_sleeve.3mf, plus_sleeve_tools_for_fusion.step, README.txt')
    sys.exit(1 if bad else 0)
