"""The camera, as a solid, so it can be SEEN instead of inferred from five numbers.

Until 2026-09-20 the camera existed in this model only as two boxes inside
`tree_parts_b_check.py`'s `camera_solid()` -- a flat board, symmetric about the tilt axis,
and a 15 mm square stub for the lens end. Enough to score interference, and nothing else.
A photo of the real board overturned three of its assumptions:

  * THE SENSOR IS NOT IN THE MIDDLE OF THE BOARD. It sits 5.3 mm toward the header edge,
    so with the lens on the tilt axis the board hangs 23.3 mm down on the connector side
    and reaches only 12.7 mm up. The old box was +-19.5, symmetric.
  * THE RIBBON SOCKET IS ON THE LENS SIDE, at the bottom edge -- not behind the board.
    The ribbon leaves FORWARD, into the gap between the board and the ball's front, and
    has to turn to reach the rolling-loop track at the back. Nothing here models that run.
  * THERE IS A LIGHT SENSOR, and it is the tallest thing on the board after the lens. It
    hangs over the header edge. This model had no idea it existed.

Built on the STEP kit, so it lands in Fusion as a solid body with no Convert Mesh.

    board  --  BOARD_T thick
    holder --  the motorised IR-CUT block: ROUND, dia 22.9, coaxial with the lens
    dome   --  the fisheye, a barrel capped with a sphere, out to the MEASURED lens tip
    socket --  the CSI FFC connector, on the LENS face at the bottom edge
    ldr    --  the day/night light sensor, on leads, overhanging the header edge
    holes  --  EIGHT of them: two concentric sets, both centred on the board

Frame: the head's own -- X forward, Y along the tilt axis, Z up, LENS AXIS at Z = H.
A second copy is written with the board's BACK face at the origin and the lens along +X.

    python camera_dummy.py
"""
import os
import cadquery as cq
from step_kit import box, rbox, cyl_x, sphere, U, cut
import tree_parts_b as B

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'camera')

# ------------------------------------------------- MEASURED with calipers (Zach)
BOARD_T = 2.0            # 2026-09-19. Was 1.6 assumed.
STANDOFF = 19.0          # 2026-09-19, board FRONT face -> lens tip. "21 mm off the board,
                         # -2 for the board itself." Puts the tip at X 29.0 in the head frame.
DOME_D = 14.8            # 2026-09-18 he measured the lens end at "14-15 mm". Reading the
                         # dome's extremes off the photo gives 14.83 -- the same feature,
                         # agreeing. A radial circle fit to the dome's silhouette says 16.3
                         # instead, but that fit is the poor one here (rms 6.2 px against the
                         # holder's 5.1 on a bigger circle) because the specular highlight
                         # drags it, and it is probably catching the holder's lip. The
                         # CALIPER WINS: a number Zach measured beats two off one photo.

# ------------------------------------------------- MEASURED off the photo, 2026-09-20
# SCALE. The first pass used the FFC connector's 1.00 mm pin pitch and came out 5% small,
# which Zach spotted by eye. The pins are the wrong reference: they sit ~3 mm ABOVE the
# PCB, and this photo was taken close enough (~90 mm -- the board fills a third of the
# frame) that 3 mm is a 3.2% magnification. The right reference is a feature IN the board
# plane: the 2.54 mm header pads along the top edge, which measure 45.40 px.
#
#     header pads (flat, in plane)   17.87 px/mm   <- USED
#     FFC pins (3 mm proud)          18.44 px/mm   = 17.87 x 1.032
#
# Three independent checks land on 17.87 and not on 18.44:
#   - the dome images at 14.83 mm, inside Zach's caliper "14-15"; at 18.44 it read 14.1
#   - the FFC body de-magnifies to 20.6 mm; a 15-way 1.0 mm ZIF body is 20.6
#   - the implied camera distance, ~90 mm, matches how much of the frame the board fills
# Call it +-1.5%, so about +-0.5 mm on the outline.
#
# WHERE THE LENS AXIS IS. The second pass put it on the dome's specular highlight, which
# Zach called as "camera position seems off". A fisheye's highlight is wherever the light
# source happens to reflect -- it is not the optical centre, and here it sat 66 px (3.7 mm)
# high. The axis is now the centre of a least-squares circle fitted to the IR-CUT holder's
# outer edge by radial gradient search (r 238.7 px, rms 5.1). It converges to the same
# answer from every seed, and the holder's own two fastening screws confirm it: they sit at
# 184 and 172 px from this centre, and at 155 and 238 px from the old one.
BOARD_W = 36.2           # across, along the tilt axis
BOARD_H = 36.0           # the other way. Both round to 36 x 36, which is very likely what
                         # it is -- but these are the measured numbers, not the guess.
BOARD_R = 1.0            # corner round -- ASSUMED, too small to read off the photo
LENS_OFF = 1.6           # lens axis, from the board's centre TOWARD THE HEADER EDGE.
                         # Was 5.3 while the axis sat on the highlight.
HOLE_D = 2.0             # M2 clearance
PAD_D = 4.0              # the gold annulus around it -- not modelled, recorded for the pegs
HOLE_SETS = [(29.4, 28.9),    # outer four, at the corners
             (29.4, 14.0)]    # THE SECOND SET Zach flagged. Same columns, rows pulled in.
                              # (pitch across, pitch along), both centred on the BOARD, not
                              # on the lens -- which is why neither is centred on the axis.
HOLDER_D = 26.7          # the IR-CUT holder. ROUND, not the square this model used to assume,
                         # and the circle the lens axis is taken from. It is BIG: it covers
                         # three quarters of the board's width and reaches down to the socket.
FFC_W, FFC_H = 20.6, 6.1      # connector body, on the LENS face
FFC_OFF = 16.3                # its centre, from the lens axis toward the connector edge
LDR_D = 7.0                   # the light sensor's black boot. The cell inside it measures
                              # 4.87 -- a stock 5 mm CdS cell -- and the boot's wall reads
                              # 1.1 all round, so 7.0 over a 5.0 element.
LDR_OFF_Z = 16.6              # its centre, above the lens axis. The board's edge is at 16.4,
                              # so the boot's rim clears it by 3.7 and its centre by 0.25.
LDR_OFF_Y = 4.9               # and this far across
HDR_PITCH, HDR_N = 2.54, 6    # the header row along the top edge; flat pads, nothing to model.
                              # Its pitch measures 2.537 -- which is the scale's best check of
                              # all, since 2.54 is what it was drawn to.
HDR_OFF_Z = 14.8              # the row's centre, above the lens axis
HDR_OFF_Y = -4.5              # and it is NOT centred across: it sits this far to one side

# ------------------------------------------------- still ASSUMED
HOLDER_X1 = 18.6         # holder front face, 8.6 off the board. A top-down photo cannot see
                         # height; this is the retired HOLDER_R/HOLDER_X1 pair's number.
FFC_T = 3.0              # how far the socket stands off the board -- a 1.0 mm ZIF is 2.5-3.0
# How tall the light sensor is, board FRONT FACE to the boot's tip. A top-down photo cannot
# see height at all, so this is Zach's call, 2026-09-20: about 4 mm, reaching FORWARD the
# same way the lens looks. It runs from the board face, not from a stand-off above it --
# modelled as a gap it came out a SEPARATE FLOATING BODY, 96 mm3 of disc hovering 1.5 mm off
# the board with nothing joining it. That is what "the top section is too short" was.
LDR_H = 4.0

# ------------------------------------------------- derived
H = B.H                                  # tilt axis height, 52.0 -- the LENS sits on it
X_BACK = B.BOARD_X0                      # 8.0
X_FRONT = B.BOARD_X0 + BOARD_T           # 10.0
LENS_TIP_X = X_FRONT + STANDOFF          # 29.0
CONNECTOR_DOWN = True                    # flip to put the socket at the top
SGN = -1.0 if CONNECTOR_DOWN else 1.0    # + Z toward the connector edge
Z_MID = H + SGN * LENS_OFF               # board centre: NOT on the tilt axis
Z0, Z1 = Z_MID - BOARD_H / 2, Z_MID + BOARD_H / 2


def camera():
    board = rbox((X_BACK, -BOARD_W / 2, Z0), (X_FRONT, BOARD_W / 2, Z1), BOARD_R)
    holder = cyl_x(0, H, HOLDER_D / 2, X_FRONT, HOLDER_X1)
    # the fisheye: a short barrel capped with a sphere that ENDS on the measured tip
    r = DOME_D / 2
    dome = U(cyl_x(0, H, r, HOLDER_X1, LENS_TIP_X - r),
             sphere(r, (LENS_TIP_X - r, 0, H)))
    zc = H + SGN * FFC_OFF
    socket = box((X_FRONT, -FFC_W / 2, zc - FFC_H / 2),
                 (X_FRONT + FFC_T, FFC_W / 2, zc + FFC_H / 2))
    ldr = cyl_x(LDR_OFF_Y, H - SGN * LDR_OFF_Z, LDR_D / 2, X_FRONT, X_FRONT + LDR_H)
    bores = []
    for py, pz in HOLE_SETS:
        for sy in (-1, 1):
            for sz in (-1, 1):
                bores.append(cyl_x(sy * py / 2, Z_MID + sz * pz / 2, HOLE_D / 2,
                                   X_BACK - 1.0, X_FRONT + 1.0))
    return cut(U(board, holder, dome, socket, ldr), *bores)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    s = camera()
    # A part that comes out in two pieces is a part with a gap in it, and a gap you cannot
    # see in a render is a gap you ship. The light sensor was exactly this: modelled with a
    # stand-off above the board it floated free, and nothing said so.
    bodies = cq.Workplane(obj=s).val().Solids()
    if len(bodies) != 1:
        for i, b in enumerate(bodies):
            bb = b.BoundingBox()
            print('  piece %d: %8.1f mm3   X %5.1f..%5.1f  Y %5.1f..%5.1f  Z %5.1f..%5.1f'
                  % (i, b.Volume(), bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
        raise SystemExit('camera_dummy came out in %d pieces -- something is not touching '
                         'the board. See the list above.' % len(bodies))
    for name, solid in (('camera_dummy', s),
                        ('camera_dummy_origin', s.moved(cq.Location(cq.Vector(-X_BACK, 0, -H))))):
        for ext in ('step', 'stl'):
            cq.exporters.export(cq.Workplane(obj=solid), os.path.join(OUT, name + '.' + ext))
    bb = s.BoundingBox()
    print('camera_dummy: %.1f x %.1f x %.1f mm, %.0f mm3, %d faces'
          % (bb.xlen, bb.ylen, bb.zlen, s.Volume(), len(s.Faces())))
    print('  board %.1f x %.1f, lens axis on Z %.1f, board Z %.1f .. %.1f (%+.1f / %+.1f)'
          % (BOARD_W, BOARD_H, H, Z0, Z1, Z0 - H, Z1 - H))
    zl = H - SGN * LDR_OFF_Z
    print('  light sensor centre Z %.1f -- board edge is Z %.1f, so it overhangs by %.1f'
          % (zl, Z1, (zl + LDR_D / 2) - Z1))
    print('  written to %s' % os.path.normpath(OUT))
