"""The holders as boxes that stack like Gridfinity bins (2026-11-08). Supersedes bricks.py and holders.py.

Zach: "notice how gridfinity bins stack. thats the concept we are missing. some bins can be as tall as two seperate ones stacked, but each one has a piece on top to stack
another like a lego brick. the pi one does not stack neither does the pac9865. also you could reuse our pac9865 holder". Before that, on the bricks: "kinda flimsy looking ... the
boxes fit the whole part that snaps in and it usually has a flat bottom to allow for more pegs".

    python twin/part_boxes.py         # builds, checks with controls, STLs in twin/out/print/, twin/out/part_boxes_view.html ("Part Holders")
    python twin/part_boxes.py slice   # the same, and slices every piece (draft, not printed) into twin/out/part_boxes_slice.json
    python twin/part_boxes.py page    # only the page

The rules, the same for every box:
  every height is a whole number of 7 mm units, Gridfinity's own, so a tall box is as tall as two short ones stacked
  pegs under a flat bottom, on the 15 mm grid, in rows 15 apart
  a piece on top with the same holes as the floor, so anything stacks on anything
  the part fits the whole box and snaps in. A part with its own proven case keeps it: the Pi's box and the PCA's case go in unchanged

Frame: x along the part, y across it, z up from the floor's underside (the floor's top at FLOOR). Built at the origin, placed by AT, which puts every peg on one 15 mm grid.
AT is a line-up for inspecting, not a layout. * = picked, for Zach to OK or measure.
"""
import json, math, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
sys.path.insert(0, HERE)
import numpy as np
import cadquery as cq
import config
from export import write_stl, health
import peg_test as PT
from peg_test import rect, cyl, vol, FLOOR, PITCH
import pi_box as PB
import kit

PRINT = os.path.join(config.TWIN_OUT, 'print')
TEMPLATE = os.path.join(HERE, 'part_boxes_view_template.html')
PCA_DIR = os.path.join(config.REPO, 'reference', 'pca9685')
PCA_STEP = os.path.join(PCA_DIR, 'PCA9685 16-Channel Servo Driver - Adafruit.step')    # * chosen because its headers stand straight up, as his lid's end slots suit
CASE_DIR = os.path.join(config.REPO, 'reference', 'downloads', 'pca9685')
CASE_BASE, CASE_LID = os.path.join(CASE_DIR, 'PCA9685_Simple_Case-2.stl'), os.path.join(CASE_DIR, 'PCA9685_Simple_Case-1-cutouts.stl')
SLICE = os.path.join(config.TWIN_OUT, 'part_boxes_slice.json')

UNIT = 7.0                        # Gridfinity's height unit
UNITS = dict(esc=6, pack=8, pi=6, pca=5, esp=5)     # * set by each part: see the rims below
HEIGHT = {k: v * UNIT for k, v in UNITS.items()}
CEILING_UNITS = 11                # 77: where the stacks below all meet. It leaves the Pi's plugs their guessed wire bend. Not a decision
CEILING = CEILING_UNITS * UNIT
PEG, HOLE = 5.0, PT.HOLE_PICK     # his bench: 5.1 for a 5 mm peg, in a 2.6 floor
PEG_LONG, TIP = PT.PEG_LONG, PT.TIP
T_W = 2.0                         # * walls
BOTTOM = 2.0                      # * the flat bottom
LID_T = 3.0                       # * the piece on top: enough for the 2.4 peg, with the floor's holes
R_OUT = 3.0                       # * the outside corners
FIT = 0.25                        # * a side, tested only on the ESC's thickness
LEAD = 0.6                        # frame v2's mouth chamfer
MOUTH = 0.3                       # * a chamfer at a hole's mouth: tops print down on the bed, where the first layer squashes in
RIDGE = 0.4                       # * how far a snap ridge stands off a wall
PLUG_DEEP, PLUG_W = 1.5, 1.2      # * the ring under a top that drops into the box's mouth
LID_FIT = 0.10                    # his whole-outline rule from pan set 9: 0.10 a side held; 0.15 was loose
GAP = 0.3                         # * air between a top's pad and the part
PLA_ACROSS = 25.0                 # * MPa, a guess at PLA pulled across its layers, which is how a standing peg bends. Only a break test settles it
E_PLA = 3000.0                    # * MPa, for the stiffness estimate

ESC = PT.ESC                      # his caliper
PACK = (141.0, 26.0, 45.7)        # his model's box, on edge. Not calipered
PI_BOX = (98.5, 65.6, PB.RIM)     # the box's outside
CASE = (75.0, 30.0, 11.7)         # his PCA case, read off his STLs: base 10.2 tall, the lid's plate 1.5 on top
ESP = (55.0, 28.0, 1.6)           # * a typical dev board. His arduino_case print is 29 x 56 inside
PLUG, PLUG_SEAT = 14.0, 2.5       # * a Dupont housing, the header's plastic under it
BEND = 15.0                       # * room for wires to turn over (the Pi box's guess)
AT = dict(esc=(-90.0, -52.5), pack=(0.0, 97.5), pi=(0.0, 22.5), pca=(0.0, -52.5), esp=(90.0, -52.5))
FLOOR_X, FLOOR_Y = (-135.0, 135.0), (-85.0, 120.0)
NAMES = dict(esc='ESC', pack='Pack', pi='Pi', pca='PCA9685', esp='ESP32')
OLD_PEGS = dict(esc=2, pack=4, pi=4, pca=4, esp=4)     # the bricks', for comparing
ROWS = (-7.5, 7.5)


def W(s):
    return cq.Workplane('XY').newObject([s])


def shift(w, x=0.0, y=0.0, z=0.0):
    return w.translate((x, y, z))


def outer(hx, hy, z0, z1, r=R_OUT):
    return rect(-hx, hx, -hy, hy, z0, z1).edges('|Z').fillet(r)


def peg_at(x, y, z):
    """a peg under a bottom at z, overrunning 0.5 up into it, its tip chamfered"""
    return cyl(PEG, z - PEG_LONG, z + 0.5, x, y).faces('<Z').chamfer(TIP)


def through(F, x, y, z0, z1):
    """a hole right through a plate, chamfered at the top"""
    F = F.cut(cyl(HOLE, z0 - 1.0, z1 + 1.0, x, y))
    return F.cut(W(cq.Solid.makeCone(HOLE / 2, HOLE / 2 + MOUTH + 0.02, MOUTH + 0.02, cq.Vector(x, y, z1 - MOUTH), cq.Vector(0, 0, 1))))


def prism(normal, s, o, c, w, pts):
    """a solid from a (distance out from a wall's inner face, z) outline: negative goes inward. w wide along the wall, centred on c"""
    if normal == 'x':
        P, v = [cq.Vector(s * (o + n), c - w / 2, z) for n, z in pts], cq.Vector(0, w, 0)
    else:
        P, v = [cq.Vector(c - w / 2, s * (o + n), z) for n, z in pts], cq.Vector(w, 0, 0)
    return W(cq.Solid.extrudeLinear(cq.Wire.makePolygon(P + [P[0]]), [], v))


def ridge(normal, s, o, c, w, zb):
    """a snap ridge inside a wall, starting just over the part's top: 45 degrees both ways, so the part presses in and pulls out"""
    return prism(normal, s, o, c, w, [(0.3, zb), (0.0, zb), (-RIDGE, zb + RIDGE), (-RIDGE, zb + RIDGE + 0.3), (0.0, zb + 2 * RIDGE + 0.3), (0.3, zb + 2 * RIDGE + 0.3)])


def box(a, b, rim, pegs, cuts=(), ridges=(), corners=None):
    """a whole box: flat bottom, walls round the opening, the rim at rim over the floor's top. cuts are windows through the walls"""
    z0, z1 = FLOOR, FLOOR + rim
    F = outer(a / 2 + T_W, b / 2 + T_W, z0, z1)
    F = F.cut(rect(-a / 2, a / 2, -b / 2, b / 2, z0 + BOTTOM, z1 + 1))
    F = F.cut(cq.Workplane('XY').workplane(offset=z1 - LEAD).rect(a, b).workplane(offset=LEAD + 0.01).rect(a + 2 * LEAD + 0.02, b + 2 * LEAD + 0.02).loft())
    for c in cuts:
        F = F.cut(rect(*c))
    for normal, s, cc, w, zb in ridges:
        F = F.union(ridge(normal, s, (a if normal == 'x' else b) / 2, cc, w, zb))
    if corners:
        dx, dy, zs = corners
        for sx in (-1, 1):
            for sy in (-1, 1):
                F = F.union(rect(*sorted((sx * (a / 2 + 0.2), sx * (a / 2 - dx))), *sorted((sy * (b / 2 + 0.2), sy * (b / 2 - dy))), z0 + BOTTOM - 0.2, z0 + BOTTOM + zs))
    for x, y in pegs:
        F = F.union(peg_at(x, y, z0))
    return F


def top_piece(a, b, rim, holes, pads=(), plug_deep=PLUG_DEEP):
    """the piece on top: the floor's own holes in a plate, a ring under it dropping into the box's mouth, pads down to the part"""
    z0, z1 = FLOOR + rim, FLOOR + rim + LID_T
    F = outer(a / 2 + T_W, b / 2 + T_W, z0, z1)
    hx, hy = a / 2 - LID_FIT, b / 2 - LID_FIT
    F = F.union(rect(-hx, hx, -hy, hy, z0 - plug_deep, z0 + 0.5).cut(rect(-hx + PLUG_W, hx - PLUG_W, -hy + PLUG_W, hy - PLUG_W, z0 - plug_deep - 1, z0)))
    for p in pads:
        F = F.union(rect(p[0], p[1], p[2], p[3], p[4], z0 + 0.5))
    for x, y in holes:
        F = through(F, x, y, z0 - 8.0, z1)
    return F


def grid(xs):
    return [(x, y) for x in xs for y in ROWS]


def spacer(h, x, z):
    """two pegs, two sockets, on the two rows every box shares. It can't spin. It's a spacer brick, for when a stack comes up short"""
    w = PEG + 3.0
    F = rect(x - w / 2, x + w / 2, -7.5 - w / 2, 7.5 + w / 2, z, z + h)
    for y in ROWS:
        F = F.union(peg_at(x, y, z))
        F = F.cut(cyl(HOLE, z + h - 2.8, z + h + 1, x, y))
        F = F.cut(W(cq.Solid.makeCone(HOLE / 2, HOLE / 2 + MOUTH + 0.02, MOUTH + 0.02, cq.Vector(x, y, z + h - MOUTH), cq.Vector(0, 0, 1))))
    return F


# ---------------------------------------------------------------- the ESC: 6 units. 2 bottom + 34 + 3 of room + 3 on top
ESC_A, ESC_B, ESC_RIM = ESC[0], ESC[1] + 2 * FIT, HEIGHT['esc'] - LID_T  # frame v2's opening
ESC_TOP = FLOOR + BOTTOM + ESC[2]
ESC_WIN = (-18.0, 18.0)                                                  # * his leads leave across most of the finned face (his photos)
ESC_PEGS = grid((-15.0, 0.0, 15.0))


def esc_box(pegs=None):
    z = FLOOR + BOTTOM + 12.0                                            # the wall below the window: the frame's 12
    cuts = [(ESC_WIN[0], ESC_WIN[1], ESC_B / 2 - 0.5, ESC_B / 2 + T_W + 1, z, FLOOR + ESC_RIM + 1)]
    rid = [('y', -1, -12.0, 14.0, ESC_TOP + 0.15), ('y', -1, 12.0, 14.0, ESC_TOP + 0.15), ('y', 1, -20.25, 4.0, ESC_TOP + 0.15), ('y', 1, 20.25, 4.0, ESC_TOP + 0.15)]
    return box(ESC_A, ESC_B, ESC_RIM, ESC_PEGS if pegs is None else pegs, cuts, rid)


def esc_top(pads=None):
    return top_piece(ESC_A, ESC_B, ESC_RIM, ESC_PEGS, pads=[(-10.0, 10.0, -11.0, 11.0, ESC_TOP + GAP)] if pads is None else pads)


def esc_solid():
    return rect(-ESC[0] / 2, ESC[0] / 2, -ESC[1] / 2, ESC[1] / 2, FLOOR + BOTTOM, ESC_TOP)


# ---------------------------------------------------------------- the pack: 8 units. 2 bottom + 45.7 + 5.3 of room + 3 on top
PACK_A, PACK_B, PACK_RIM = PACK[0] + 2 * FIT, PACK[1] + 2 * FIT, HEIGHT['pack'] - LID_T
PACK_TOP = FLOOR + BOTTOM + PACK[2]
PACK_PEGS = grid((-60.0, -30.0, 0.0, 30.0, 60.0))


def pack_box():
    z, zt = FLOOR + BOTTOM + 12.0, PACK_TOP - 1.0
    y = PACK_B / 2
    cuts = []
    for s in (-1, 1):                                                    # * windows for weight and air, under a band round the top
        for x0, x1 in ((-62.0, -8.0), (8.0, 62.0)):
            cuts.append((x0, x1, *sorted((s * (y - 0.5), s * (y + T_W + 1))), z, zt))
    for s in (-1, 1):                                                    # the lead's way out, at both ends, open at the top so it drops in
        cuts.append((*sorted((s * (PACK_A / 2 - 0.5), s * (PACK_A / 2 + T_W + 1))), -9.0, 9.0, FLOOR + BOTTOM + 10.0, FLOOR + PACK_RIM + 1))
    rid = [('y', s, c, 20.0, PACK_TOP + 0.15) for s in (-1, 1) for c in (-35.0, 35.0)]
    return box(PACK_A, PACK_B, PACK_RIM, PACK_PEGS, cuts, rid)


def pack_top():
    pads = [(c - 6.0, c + 6.0, -12.0, 12.0, PACK_TOP + GAP) for c in (-50.0, 0.0, 50.0)]
    return top_piece(PACK_A, PACK_B, PACK_RIM, grid(np.arange(-60.0, 61.0, PITCH)), pads)


def pack_solid():
    return rect(-PACK[0] / 2, PACK[0] / 2, -PACK[1] / 2, PACK[1] / 2, FLOOR + BOTTOM, PACK_TOP)


# ---------------------------------------------------------------- the Pi: 6 units. A tube his closed box slides into, its top a pegboard with a bite out for the plugs
PI_CX = -6.5                                                             # the box's centre in the sleeve, set so a stop on the x = -60 holes touches its SD end
PI_B = PI_BOX[1] + 2 * FIT
PI_X0, PI_X1 = PI_CX - PI_BOX[0] / 2 - FIT, PI_CX + PI_BOX[0] / 2 + FIT
PI_RIM = FLOOR + BOTTOM + PI_BOX[2]
PI_ROOF = FLOOR + HEIGHT['pi'] - LID_T
PI_PEGS = [(x, y) for x in (-45.0, -15.0, 15.0, 30.0) for y in (-22.5, 22.5)]
PI_HOLES = [(x, y) for x in (-45.0, -30.0, -15.0, 0.0, 15.0, 30.0) for y in (-22.5, -7.5, 7.5)] + [(30.0, 22.5)]


def pi_header():
    return (PB.HDR_X[0] - PI_BOX[0] / 2 + PI_CX, PB.HDR_X[1] - PI_BOX[0] / 2 + PI_CX, PB.HDR_Y[0] - PI_BOX[1] / 2, PB.HDR_Y[1] - PI_BOX[1] / 2)


def pi_sleeve():
    y = PI_B / 2
    top = FLOOR + HEIGHT['pi']
    x1 = PI_X1 + T_W
    F = rect(-66.0, x1, -y - T_W, y + T_W, FLOOR, FLOOR + BOTTOM)        # the flat bottom, on past the SD end for the stops
    F = F.union(rect(PI_X0, x1, -y - T_W, y + T_W, PI_ROOF, top))         # the top
    for s in (-1, 1):
        F = F.union(rect(PI_X0, x1, *sorted((s * y, s * (y + T_W))), FLOOR, top))    # the long walls
        F = F.union(rect(PI_X1, x1, *sorted((s * (y - 4.0), s * y)), FLOOR, FLOOR + BOTTOM + 12.0))   # * the far stop, at the corners, clear of the USB ports
    # the walls' windows: the ports and the box's own side vents stay open
    z, zt = FLOOR + BOTTOM + 4.0, PI_ROOF - 3.0
    bx = PI_CX - PI_BOX[0] / 2
    for s, spans in ((-1, ((bx + 9.0, bx + 54.0), (bx + 57.0, bx + 90.0))), (1, ((bx + 9.0, bx + 49.0), (bx + 52.0, bx + 90.0)))):
        for x0, x1w in spans:
            F = F.cut(rect(x0, x1w, *sorted((s * (y - 0.5), s * (y + T_W + 1))), z, zt))
    # the bite: the Pi's plugs and wires come up through the top here
    hx0, hx1, hy0, hy1 = pi_header()
    F = F.cut(rect(hx0 - 3.0, hx1 + 3.0, 18.5, y + T_W + 1, PI_ROOF - 1, top + 1))
    # * slots for air, between the rows of holes
    for y0, y1 in ((-18.5, -11.5), (-3.5, 3.5), (11.5, 18.5)):
        for x0, x1s in ((PI_X0 + 4.0, -10.5), (-4.5, PI_X1 - 2.0)):
            F = F.cut(rect(x0, x1s, y0, y1, PI_ROOF - 1, top + 1))
    for x, yy in PI_HOLES:
        F = through(F, x, yy, PI_ROOF, top)
    for x, yy in PI_PEGS:
        F = F.union(peg_at(x, yy, FLOOR))
    for yy in ROWS:                                                      # the holes the stops peg through
        F = through(F, -60.0, yy, FLOOR, FLOOR + BOTTOM)
    return F


def pi_stop(yy):
    """a stop brick at the SD end: its peg goes through the bottom into the floor. One face is on the box's end"""
    zb = FLOOR + BOTTOM
    F = rect(-64.0, PI_X0, yy - 3.5, yy + 3.5, zb, zb + 2 * UNIT)
    return F.union(cyl(PEG, zb - PEG_LONG, zb + 0.5, -60.0, yy).faces('<Z').chamfer(TIP))


def pi_solid():
    return rect(PI_CX - PI_BOX[0] / 2, PI_CX + PI_BOX[0] / 2, -PI_BOX[1] / 2, PI_BOX[1] / 2, FLOOR + BOTTOM, PI_RIM)


def pi_plugs():
    x0, x1, y0, y1 = pi_header()
    return rect(x0, x1, y0, y1, FLOOR + BOTTOM + PB.PLUG_TOP - PB.HOUSING, FLOOR + BOTTOM + PB.PLUG_TOP)


def pi_column():
    """for the check: the header and its plugs from the lid's underside up, the path the wires take out"""
    x0, x1, y0, y1 = pi_header()
    return rect(x0, x1, y0, y1, PI_RIM - 3.0, FLOOR + BOTTOM + PB.PLUG_TOP)


# ---------------------------------------------------------------- the PCA: 5 units. His own case drops in as it is, and the box goes round it
PCA_A, PCA_B, PCA_RIM = CASE[0] + 2 * FIT, CASE[1] + 2 * FIT, HEIGHT['pca'] - LID_T
CASE_Z = FLOOR + BOTTOM
CASE_TOP = CASE_Z + CASE[2]
RING_TOP = 2.7                                                           # his base's standoffs, over its underside
BOARD_T = 1.6
BOARD_UNDER = CASE_Z + RING_TOP
BOARD_TOP = BOARD_UNDER + BOARD_T
BOARD_PEGS = grid((-15.0, 15.0))


def rings_centre():
    """where his base centres the board, in its own frame, off its four locating pins"""
    V = PB.stl(CASE_BASE).reshape(-1, 3)
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            m = (V[:, 2] > 3.3) & (V[:, 2] < 5.5) & (sx * (V[:, 0] + 38.0) > 3.0) & (sx * (V[:, 0] + 38.0) < 13.0) & (sy * (V[:, 1] - 0.75) > 20.0) & (sy * (V[:, 1] - 0.75) < 31.0)
            out.append(V[m].mean(0))
    return np.array(out)


def case_tris():
    """his two STLs, assembled in this frame: x along, its V+ notch on the +y side, the base on the box's bottom, the lid's plate on top of the base"""
    B = PB.stl(CASE_BASE); L = PB.stl(CASE_LID)
    Bo = B.copy(); Bo[:, :, 0] = B[:, :, 1] - 2.011; Bo[:, :, 1] = -(B[:, :, 0] + 38.0); Bo[:, :, 2] = B[:, :, 2] + 0.2 + CASE_Z
    Lo = L.copy(); Lo[:, :, 0] = L[:, :, 1]; Lo[:, :, 1] = L[:, :, 0]; Lo[:, :, 2] = CASE_TOP - L[:, :, 2]
    return Bo, Lo


def board_xy():
    R = rings_centre()
    c = R.mean(0)
    return c[1] - 2.011, -(c[0] + 38.0), R


def pca_box(pegs=None):
    z1 = FLOOR + PCA_RIM + 1
    cuts = []
    for s in (-1, 1):                                                    # the wires' way out: both long sides, both ends, open at the top
        cuts.append((-25.0, 25.0, *sorted((s * (PCA_B / 2 - 0.5), s * (PCA_B / 2 + T_W + 1))), CASE_Z + 8.0, z1))
        cuts.append((*sorted((s * (PCA_A / 2 - 0.5), s * (PCA_A / 2 + T_W + 1))), -9.0, 9.0, CASE_Z + 8.0, z1))
    rid = [('y', s, c, 6.0, CASE_TOP + 0.15) for s in (-1, 1) for c in (-29.0, 29.0)]
    return box(PCA_A, PCA_B, PCA_RIM, BOARD_PEGS if pegs is None else pegs, cuts, rid)


def pca_top():
    return top_piece(PCA_A, PCA_B, PCA_RIM, grid((-30.0, -15.0, 0.0, 15.0, 30.0)))


def case_solid():
    return rect(-CASE[0] / 2, CASE[0] / 2, -CASE[1] / 2, CASE[1] / 2, CASE_Z, CASE_TOP)


def pca_board():
    x0, y0, _ = board_xy()
    w = cq.importers.importStep(PCA_STEP)
    return [s.moved(cq.Location(cq.Vector(x0, y0, BOARD_UNDER + 0.8))) for s in w.solids().vals()]


def pca_plugs():
    """* channels 0 and 1, and Dupont plugs on both end headers, which stand straight up through his lid's end slots"""
    x0, y0, _ = board_xy()
    t = BOARD_TOP + PLUG_SEAT
    return [rect(x0 - 25.4, x0 - 20.3, y0 - 12.7, y0 - 5.1, t, t + PLUG),
            rect(x0 - 30.5, x0 - 27.9, y0 - 7.6, y0 + 7.6, t, t + PLUG), rect(x0 + 27.9, x0 + 30.5, y0 - 7.6, y0 + 7.6, t, t + PLUG)]


# ---------------------------------------------------------------- the ESP32: 5 units. It sits upside down so the plugs go on from above
ESP_A, ESP_B, ESP_RIM = ESP[0] + 2 * FIT, ESP[1] + 2 * FIT, HEIGHT['esp'] - LID_T
ESP_SHELF = 4.0                                                          # * over the flat bottom: room for the module and USB under it
ESP_UNDER = FLOOR + BOTTOM + ESP_SHELF
ESP_TOP = ESP_UNDER + ESP[2]


def esp_box():
    z1 = FLOOR + ESP_RIM + 1
    cuts = [(ESP_A / 2 - 0.5, ESP_A / 2 + T_W + 1, -6.5, 6.5, FLOOR + BOTTOM, z1)]       # the USB end
    for s in (-1, 1):                                                    # the wires' way out, both long sides, open at the top
        cuts.append((-20.0, 20.0, *sorted((s * (ESP_B / 2 - 0.5), s * (ESP_B / 2 + T_W + 1))), ESP_TOP + 1.5, z1))
    rid = [('y', s, c, 3.0, ESP_TOP + 0.15) for s in (-1, 1) for c in (-26.0, 26.0)]
    return box(ESP_A, ESP_B, ESP_RIM, BOARD_PEGS, cuts, rid, corners=(3.0, 5.0, ESP_SHELF))


def esp_top():
    return top_piece(ESP_A, ESP_B, ESP_RIM, grid((-15.0, 0.0, 15.0)))


def esp_model():
    """* no model of his board exists"""
    return dict(board=rect(-ESP[0] / 2, ESP[0] / 2, -ESP[1] / 2, ESP[1] / 2, ESP_UNDER, ESP_TOP),
                under=rect(-24.5, -7.0, -9.0, 9.0, ESP_UNDER - 3.2, ESP_UNDER).union(rect(23.0, 28.5, -4.0, 4.0, ESP_UNDER - 3.0, ESP_UNDER)),
                pins=rect(-24.0, 24.0, 11.43, 13.97, ESP_TOP, ESP_TOP + PLUG_SEAT).union(rect(-24.0, 24.0, -13.97, -11.43, ESP_TOP, ESP_TOP + PLUG_SEAT)),
                plugs=rect(-24.0, 24.0, 11.43, 13.97, ESP_TOP + PLUG_SEAT, ESP_TOP + PLUG_SEAT + PLUG).union(rect(-24.0, 24.0, -13.97, -11.43, ESP_TOP + PLUG_SEAT, ESP_TOP + PLUG_SEAT + PLUG)))


def floor():
    pts = [(x, y) for x in np.arange(-120, 121, PITCH) for y in np.arange(-75, 106, PITCH)]
    return rect(*FLOOR_X, *FLOOR_Y, 0, FLOOR).faces('>Z').workplane(origin=(0, 0, FLOOR)).pushPoints(pts).hole(HOLE)


def many(items):
    out = None
    for w in items:
        out = w if out is None else out.union(w)
    return out


# ---------------------------------------------------------------- the pegs and the walls, in numbers
def loads():
    D = json.load(open(os.path.join(config.TWIN_OUT, 'retention.json')))['frames']['1.0']['peak_p90']
    pca = D['frame pca']
    return dict(esc=max(D['frame esc_L'], D['frame esc_R']), pack=max(D['frame pack_L'], D['frame pack_R']), pi=D['frame pi_stack'], pca=pca, esp=pca)


def bending(F, n, d=PEG):
    """MPa at a peg's root, its load shared evenly and bearing halfway down its 2.4"""
    return (F / n) * (PEG_LONG / 2) / (math.pi * d ** 3 / 32)


def peg_table():
    L = loads(); rows = []
    for k, pegs in (('esc', ESC_PEGS), ('pack', PACK_PEGS), ('pi', PI_PEGS), ('pca', BOARD_PEGS), ('esp', BOARD_PEGS)):
        rows.append(dict(name=NAMES[k], load=L[k], old_n=OLD_PEGS[k], old=bending(L[k], OLD_PEGS[k]), n_s=len(pegs), s=bending(L[k], len(pegs))))
    return rows


def stiffness():
    """an estimate, sideways at the ESC's top: the bricks' two 8 x 8 columns, 36 tall, against the box's two end walls"""
    col = 3 * E_PLA * (8.0 ** 4 / 12) / 36.0 ** 3
    b = ESC_B + 2 * T_W
    wall = 3 * E_PLA * (T_W * b ** 3 / 12) / ESC_RIM ** 3
    return dict(col=2 * col, wall=2 * wall, ratio=wall / col)


# ---------------------------------------------------------------- the stacks
STACKS = [dict(name='ESC + PCA', parts=[('ESC', 6, 'box'), ('PCA', 5, 'box')]), dict(name='Pi + ESP32', parts=[('Pi', 6, 'box'), ('ESP32', 5, 'box')]),
          dict(name='Pack', parts=[('Pack', 8, 'box'), ('spacer', 3, 'spacer')]), dict(name='ESC', parts=[('ESC', 6, 'box'), ('spacer', 5, 'spacer')])]


# ---------------------------------------------------------------- the checks
def case_solids():
    """his two parts as exact solids, in this frame"""
    Bo, Lo = case_tris()
    os.makedirs(PRINT, exist_ok=True)
    pb, pl = os.path.join(config.TWIN_OUT, 'pca_case_base_placed.stl'), os.path.join(config.TWIN_OUT, 'pca_case_lid_placed.stl')
    PB.write_tris(Bo, pb); PB.write_tris(Lo, pl)
    return W(cq.Shape.cast(kit.load(pb)[0])), W(cq.Shape.cast(kit.load(pl)[0]))


def check():
    ok = True

    def line(what, good, got=''):
        nonlocal ok
        ok &= bool(good)
        print('  %-78s %s %s' % (what, got, 'ok' if good else 'WRONG'))

    E = esp_model(); pca = pca_board(); Fl = floor()
    x0, y0, R = board_xy()
    solid = dict(esc=esc_solid(), pack=pack_solid(), pi=pi_solid(), pca=case_solid(), esp=E['board'])
    B = dict(esc=esc_box(), pack=pack_box(), pi=pi_sleeve(), pca=pca_box(), esp=esp_box())
    T = dict(esc=esc_top(), pack=pack_top(), pca=pca_top(), esp=esp_top())
    Stops = many(pi_stop(y) for y in ROWS)
    print('--- in the floor, each box')
    for p, b in B.items():
        v = vol(Fl, shift(b, *AT[p])); line('%s: the box\'s pegs in the %.1f holes' % (NAMES[p], HOLE), v < 1e-3, '%.3f mm3' % v)
        v = vol(Fl, shift(b, AT[p][0] + PITCH / 3, AT[p][1])); line('%s: control, 5 mm off its holes' % NAMES[p], v > 1, '%.2f mm3' % v)
        v = vol(b, solid[p]); line('%s: the part in the box' % NAMES[p], v < 1e-3, '%.3f mm3' % v)
    print('--- the piece on top')
    for p, t in T.items():
        v = vol(t, B[p]); line('%s: it seats on the box' % NAMES[p], v < 1e-3, '%.3f mm3' % v)
        v = vol(t, solid[p]); line('%s: it clears the part' % NAMES[p], v < 1e-3, '%.3f mm3' % v)
        h = t.val().BoundingBox().zmax - FLOOR
        line('%s: its top lands on %d units' % (NAMES[p], UNITS[p]), abs(h - UNITS[p] * UNIT) < 1e-6, '%.1f' % h)
    h = B['pi'].val().BoundingBox().zmax - FLOOR
    line('Pi: its top lands on %d units' % UNITS['pi'], abs(h - UNITS['pi'] * UNIT) < 1e-6, '%.1f' % h)
    print('--- what holds each part')
    for p in ('esc', 'pack'):
        v = vol(shift(solid[p], z=3.0 if p == 'esc' else 5.5), T[p]); line('%s: pulled up, it hits the top\'s pad' % NAMES[p], v > 1, '%.2f mm3' % v)
    for p in ('esc', 'pack', 'pca', 'esp'):
        v = vol(B[p], shift(solid[p], z=0.6)); line('%s: pulled up 0.6 mm, it rides onto the ridges' % NAMES[p], v > 0.01, '%.2f mm3' % v)
    v = vol(B['pi'], shift(solid['pi'], z=1.0)); line('Pi: pulled up 1 mm, the box hits the top', v > 1, '%.2f mm3' % v)
    print('--- the Pi slides')
    bad = [x for x in (-20.0, -60.0, -110.0) if vol(B['pi'], shift(solid['pi'], x=x)) > 1e-3]
    line('with the stops out, the box slides out its SD end: 20, 60, 110 mm', not bad, '%s' % (bad or ''))
    v = vol(Fl, shift(Stops, *AT['pi'])); line('the stops\' pegs in the floor', v < 1e-3, '%.3f mm3' % v)
    v = vol(B['pi'], Stops); line('the stops through the sleeve\'s bottom', v < 1e-3, '%.3f mm3' % v)
    v = vol(Stops, solid['pi']); line('the stops touch the box\'s end, no overlap', v < 1e-3, '%.3f mm3' % v)
    v = vol(Stops, shift(solid['pi'], x=-1.0)); line('control: the box 1 mm toward them is stopped', v > 1, '%.2f mm3' % v)
    v = vol(B['pi'], pi_column()); line('the top\'s bite clears the header and plugs', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(B['pi'], y=-8.0), pi_column()); line('control: the sleeve 8 mm over, onto the header', v > 1, '%.2f mm3' % v)
    print('--- his PCA case, as it is')
    print('  the four locating pins, in his base\'s frame:', np.round(R[:, :2], 2).tolist(), 'spacing %.2f x %.2f, the model\'s holes 55.62 x 19.05' % (np.ptp(R[:, 1]), np.ptp(R[:, 0])))
    bz = [s for s in pca if s.BoundingBox().xlen > 60 and s.BoundingBox().ylen > 20]
    print('  the model\'s board layers, z:', [(round(s.BoundingBox().zmin, 2), round(s.BoundingBox().zmax, 2)) for s in bz], '| board under %.2f, top %.2f' % (BOARD_UNDER, BOARD_TOP))
    Cb, Cl = case_solids()
    bb = Cb.val().BoundingBox(); print('  base placed: x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f' % (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
    bb = Cl.val().BoundingBox(); print('  lid placed: x %.2f..%.2f y %.2f..%.2f z %.2f..%.2f' % (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))
    v = vol(Cb, Cl); print('  base against lid: %.2f mm3' % v)
    for name, w in (('base', Cb), ('lid', Cl)):
        tot, hits = 0.0, []
        for s in pca:
            v = vol(w, W(s))
            if v > 1e-3:
                b = s.BoundingBox(); tot += v; hits.append((round(v, 1), round(b.xmin, 1), round(b.xmax, 1), round(b.ymin, 1), round(b.ymax, 1), round(b.zmin, 1), round(b.zmax, 1)))
        print('  the PCA model against his %s: %.2f mm3 in %d solids, largest:' % (name, tot, len(hits)), sorted(hits, reverse=True)[:6])
    v = vol(shift(Cl, x=4.0), many([W(s) for s in pca[:40]])); print('  control: his lid 4 mm off, against 40 of the model\'s solids: %.2f mm3' % v)
    v = vol(Cb, B['pca']); line('his base in the box', v < 1e-3, '%.3f mm3' % v)
    v = vol(Cl, B['pca']); line('his lid in the box', v < 1e-3, '%.3f mm3' % v)
    v = vol(B['pca'], rect(-38.0, 38.0, -15.0, 15.0, CASE_Z, CASE_Z + 5.0)); line('control: a case 1 mm longer', v > 1, '%.2f mm3' % v)
    for i, q in enumerate(pca_plugs()):
        for nm, w in (('box', B['pca']), ('top', T['pca']), ('his lid', Cl)):
            v = vol(w, q)
            line('plug %d clears the PCA\'s %s' % (i, nm), v < 1e-3, '%.3f mm3' % v)
    print('  room over the PCA\'s plugs, under the top\'s ring: %.1f mm' % (FLOOR + PCA_RIM - PLUG_DEEP - (BOARD_TOP + PLUG_SEAT + PLUG)))
    print('--- the ESP32')
    for nm, q in E.items():
        for k, w in (('box', B['esp']), ('top', T['esp'])):
            v = vol(w, q)
            line('its %s clears the %s' % (nm, k), v < 1e-3, '%.3f mm3' % v)
    print('  room over its plugs, under the top\'s ring: %.1f mm' % (FLOOR + ESP_RIM - PLUG_DEEP - (ESP_TOP + PLUG_SEAT + PLUG)))
    print('--- stacking, with controls')
    ez = HEIGHT['esc']
    v = vol(shift(B['pca'], z=ez), T['esc']); line('the PCA box on the ESC\'s top', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(B['pca'], x=5.0, z=ez), T['esc']); line('control: 5 mm off', v > 1, '%.2f mm3' % v)
    pz = HEIGHT['pi']
    v = vol(shift(B['esp'], z=pz), B['pi']); line('the ESP32 box on the Pi\'s top', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(B['esp'], x=5.0, z=pz), B['pi']); line('control: 5 mm off', v > 1, '%.2f mm3' % v)
    v = vol(shift(B['esp'], z=pz), pi_plugs()); line('it clears the Pi\'s plugs', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(B['esc'], x=-30.0, z=HEIGHT['pack']), T['pack']); line('an ESC box on the pack\'s top', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(B['pca'], z=HEIGHT['pack']), T['pack']); line('a PCA box on the pack\'s top', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(B['pack'], z=HEIGHT['pack']), T['pack']); line('a pack box on the pack\'s top', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(B['esc'], z=HEIGHT['esp']), T['esp']); line('an ESC box on the ESP32\'s top', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(B['esp'], z=HEIGHT['pca']), T['pca']); line('an ESP32 box on the PCA\'s top', v < 1e-3, '%.3f mm3' % v)
    sp = spacer(21.0, 60.0, FLOOR + HEIGHT['pack'])
    v = vol(sp, T['pack']); line('a spacer on the pack\'s top', v < 1e-3, '%.3f mm3' % v)
    v = vol(spacer(21.0, 60.0, FLOOR + HEIGHT['pack'] + 21.0), sp); line('a spacer on a spacer', v < 1e-3, '%.3f mm3' % v)
    print('--- the stacks reach the ceiling at %d units' % CEILING_UNITS)
    for st in STACKS:
        u = sum(x[1] for x in st['parts'])
        line('%s: %s' % (st['name'], ' + '.join('%s %d' % (a, b) for a, b, _ in st['parts'])), u == CEILING_UNITS, '= %d' % u)
    line('Pi\'s plugs under it, with %.1f for wires, guessed need %.0f' % (CEILING - BOTTOM - PB.PLUG_TOP, BEND), CEILING - BOTTOM - PB.PLUG_TOP >= BEND)
    print('--- the ESC box on the patch he already has: rows 5.1 and 5.2')
    v = vol(PT.patch(), shift(B['esc'], y=-15.0)); line('its six pegs in those rows, columns -15, 0 and 15', v < 1e-3, '%.3f mm3' % v)
    v = vol(PT.patch(), shift(B['esc'], y=-10.0)); line('control: 5 mm off the rows', v > 1, '%.2f mm3' % v)
    print('--- pegs, MPa at the root, loads from the drop test')
    for r in peg_table():
        print('  %-8s %4.0f N | bricks %d pegs: %5.1f | now %2d pegs: %5.1f' % (r['name'], r['load'], r['old_n'], r['old'], r['n_s'], r['s']))
    return ok, B, T, Stops, E, pca, Cb, Cl


def flip(w):
    f = w.rotate((0, 0, 0), (1, 0, 0), 180)
    return f.translate((0, 0, -f.val().BoundingBox().zmin))


def pieces(B, T):
    """each different piece once, and how many one robot's set needs. Everything prints upside down, so the pegs point up"""
    return dict(esc_box=(B['esc'], 2), esc_top=(T['esc'], 2), pack_box=(B['pack'], 2), pack_top=(T['pack'], 2), pi_sleeve=(B['pi'], 1), pi_stop=(pi_stop(7.5), 2),
                pca_box=(B['pca'], 1), pca_top=(T['pca'], 1), esp_box=(B['esp'], 1), esp_top=(T['esp'], 1), spacer_3=(spacer(3 * UNIT, 0.0, FLOOR), 4), spacer_5=(spacer(5 * UNIT, 0.0, FLOOR), 2))


SET_NAMES = dict(esc_box='ESC box', esc_top='ESC top', pack_box='Pack box', pack_top='Pack top', pi_sleeve='Pi sleeve', pi_stop='Pi stop', pca_box='PCA box', pca_top='PCA top', esp_box='ESP32 box', esp_top='ESP32 top', spacer_3='Spacer, 3 units', spacer_5='Spacer, 5 units', case_base='Your PCA case, base', case_lid='Your PCA case, lid')


def slice_all(paths):
    res = {}
    for k, p in paths.items():
        sup = '1' if k == 'pi_sleeve' else '0'                           # the sleeve's bottom spans 66 mm: too far to bridge
        r = subprocess.run([sys.executable, os.path.join(config.REPO, 'tools', 'orca.py'), p, '--draft', '--set', 'brim_type=outer_only', '--set', 'brim_width=5',
                            '--set', 'enable_support=' + sup, '--name', 'partbox_' + k], capture_output=True, text=True)
        m = re.search(r'^\s+(.+?), ([\d.]+) g,', r.stdout, re.M)
        res[k] = dict(time=m.group(1).strip(), g=float(m.group(2))) if m else dict(time='?', g=0.0, err=(r.stdout + r.stderr)[-300:])
        print('  %-14s %s' % (k, res[k]))
    json.dump(res, open(SLICE, 'w'), indent=1)
    return res


# ---------------------------------------------------------------- the page
def enc_vf(V, F, label, group, role, layer, color, note):
    import base64
    return dict(label=label, group=group, role=role, layer=layer, color=color, note=note, scheme=None, v=base64.b64encode(np.asarray(V, '<f4').tobytes()).decode(), f=base64.b64encode(np.asarray(F, '<u4').tobytes()).decode())


def enc_w(w, at, label, group, role, layer, color, note, tol=0.08, z=0.0):
    V, F = PT.mesh_of(w, tol)
    return enc_vf(V + np.array([at[0], at[1], z], '<f4'), F, label, group, role, layer, color, note)


def enc_t(T, at, label, group, role, layer, color, note, faces=None, z=0.0):
    T = np.array(T, float); T[:, :, 0] += at[0]; T[:, :, 1] += at[1]; T[:, :, 2] += z
    V, F = PB.mesh(T, faces)
    return enc_vf(V, F, label, group, role, layer, color, note)


def page(B, T, E, pca, info):
    BOX, TOP, SPACE, PART, PLUGC, CASEC = 0xe0b35c, 0x5fb3a1, 0x8f8fd6, 0x4a78b5, 0x3a3d43, 0xd9c39e
    P = dict(floor=enc_w(floor(), (0, 0), 'Floor', 'floor', 'floor', 0, 0xb9c4d0, 'Your 2.6 mm floor with %.1f holes every %.0f mm. These are just lined up on it to inspect. This is not a layout.' % (HOLE, PITCH), tol=0.1))
    P['esc_box'] = enc_w(B['esc'], AT['esc'], 'ESC box', 'esc', 'box', 1, BOX, 'Frame v2\'s opening, unchanged: 45.0 long, 24.5 across. Walls 2.0, a 2.0 flat bottom, six 5 mm pegs under it. The window in one long wall is for your leads, open at the top so they drop in as the ESC goes down.')
    P['esc_top'] = enc_w(T['esc'], AT['esc'], 'ESC top', 'esc', 'box', 3, TOP, 'The piece on top. The same holes as the floor, so the next box pegs in. A ring under it drops into the box\'s mouth at your 0.10 a side, and a pad lands on the ESC.')
    P['esc_part'] = enc_w(esc_solid(), AT['esc'], 'Your ESC', 'esc', 'part', 2, PART, 'Your caliper: 45 long, 34 wide, 24 tall, stood on edge. A plain box with no wires. You don\'t print this one.')
    P['pack_box'] = enc_w(B['pack'], AT['pack'], 'Pack box', 'pack', 'box', 1, BOX, 'Walls 2.0 with windows for weight and air, a 2.0 flat bottom, ten 5 mm pegs. Both ends are open at the top for the lead, so either end works.')
    P['pack_top'] = enc_w(T['pack'], AT['pack'], 'Pack top', 'pack', 'box', 3, TOP, 'The piece on top: 18 holes, two rows, and three pads on the pack. To swap a pack, pull this and lift the pack past the ridges.')
    P['pack_part'] = enc_w(pack_solid(), AT['pack'], 'Your pack', 'pack', 'part', 2, PART, 'Zeee 2S 5200 on edge, 141 x 26 x 45.7, from your model\'s box. Not calipered. You don\'t print this one.')
    P['pi_sleeve'] = enc_w(B['pi'], AT['pi'], 'Pi sleeve', 'pi', 'box', 1, BOX, 'A tube, 6 units tall: a flat bottom with eight 5 mm pegs, two walls with windows, and a top with the floor\'s holes. The bite in the top lets your plugs and wires up, and the slots let air out. Your closed box slides in from the SD end.')
    P['pi_stops'] = enc_w(many(pi_stop(y) for y in ROWS), AT['pi'], 'Stops', 'pi', 'box', 3, TOP, 'Two bricks that peg through the sleeve\'s bottom into the floor, against your box\'s SD end. Pull them, and the box slides out.')
    Bb = PB.stl(os.path.join(PRINT, 'pi_box_base_bored.stl')); Bb[:, :, 0] += PI_CX - PI_BOX[0] / 2; Bb[:, :, 1] -= PI_BOX[1] / 2; Bb[:, :, 2] += FLOOR + BOTTOM
    Lb = PB.lid_in_base(PB.stl(os.path.join(PRINT, 'pi_box_lid_over_header.stl'))); Lb[:, :, 0] += PI_CX - PI_BOX[0] / 2; Lb[:, :, 1] -= PI_BOX[1] / 2; Lb[:, :, 2] += FLOOR + BOTTOM
    P['pi_base'] = enc_t(Bb, AT['pi'], 'Your box: base', 'pi', 'part', 2, CASEC, 'The rpi5 base with the rings bored, as your ring test proved. Not changed.', 24000)
    P['pi_lid'] = enc_t(Lb, AT['pi'], 'Your box: lid, notch over the pins', 'pi', 'part', 2, 0xc9b48c, 'Your lid with the notch over the pins. Its clips hold it to the base.', 8000)
    P['pi_plugs'] = enc_w(pi_plugs(), AT['pi'], 'Dupont plugs', 'pi', 'part', 2, PLUGC, 'All 40 drawn. The top is your caliper, %.1f over the floor with the sleeve\'s 2.0 under your box.' % (BOTTOM + PB.PLUG_TOP))
    Bo, Lo = case_tris()
    tris = []
    for s in pca:
        V, Fc = s.tessellate(0.15, 0.6)
        Q = np.array([[v.x, v.y, v.z] for v in V]); tris.append(Q[np.array(Fc)])
    All = np.vstack(tris)
    note_case_b = 'Your PCA9685_Simple_Case base, not changed: 75 x 30 x 10.2, four standoffs with locating pins. It drops into the box.'
    note_case_l = 'Your cut-outs lid, not changed. It sits on the base, its four corner blocks clamp the board, and the pins come up through its windows.'
    note_board = 'The Adafruit PCA9685 model in the repo. Its end headers stand straight up, as your lid\'s end slots suit. Not checked against your own board.'
    note_plug = 'A guess: a %.0f mm Dupont housing or servo plug on a %.1f seat. Not measured.' % (PLUG, PLUG_SEAT)
    plug_names = ('Plugs on channels 0 and 1', 'Plug on one end header', 'Plug on the other end header')
    P['pca_box'] = enc_w(B['pca'], AT['pca'], 'PCA box', 'pca', 'box', 1, BOX, 'Goes round your case: four 5 mm pegs under a 2.0 flat bottom, 2.0 walls, open-topped windows on all four sides for the wires. Your case snaps in past four ridges.')
    P['pca_case_b'] = enc_t(Bo, AT['pca'], 'Your case: base', 'pca', 'part', 2, CASEC, note_case_b)
    P['pca_board'] = enc_t(All, AT['pca'], 'PCA model', 'pca', 'part', 2, 0x2f8a58, note_board, 14000)
    P['pca_case_l'] = enc_t(Lo, AT['pca'], 'Your case: lid', 'pca', 'part', 2, 0xc9b48c, note_case_l)
    for i, (p, n) in enumerate(zip(pca_plugs(), plug_names)):
        P['pca_plug%d' % i] = enc_w(p, AT['pca'], n, 'pca', 'part', 2, PLUGC, note_plug)
    P['pca_top'] = enc_w(T['pca'], AT['pca'], 'PCA top', 'pca', 'box', 3, TOP, 'The piece on top: 10 holes, on the full 5 x 2 of your case. It sits over your plugs, with room for the wires to turn and leave by the side windows.')
    esp_notes = dict(board='No model of your board exists, so this is a typical 55 x 28 dev board. It is upside down, so your factory pins point up and the plugs go on from above.', under='A guess at the module and USB port, now hanging under the board. They set the %.1f shelf.' % ESP_SHELF, pins='A guess: 48 long, 25.4 apart.', plugs='A guess: every pin plugged, the worst case.')
    esp_names = dict(board='ESP32 board, upside down', under='Module and USB, on its underside', pins='Pin rows', plugs='Dupont plugs')
    esp_col = dict(board=0x2f8a58, under=0x1d6b45, pins=0xc9a227, plugs=PLUGC)
    P['esp_box'] = enc_w(B['esp'], AT['esp'], 'ESP32 box', 'esp', 'box', 1, BOX, 'Four 5 mm pegs under a 2.0 flat bottom, 2.0 walls. The USB end is open, and both long sides have open-topped windows for the wires. The board snaps in under four ridges, past the ends of the pin rows.')
    P['esp_top'] = enc_w(T['esp'], AT['esp'], 'ESP32 top', 'esp', 'box', 3, TOP, 'The piece on top: 6 holes. It sits over the plugs.')
    for k in E:
        P['esp_' + k] = enc_w(E[k], AT['esp'], esp_names[k], 'esp', 'part', 2, esp_col[k], esp_notes[k])
    # the two stacks: the PCA on the ESC's top, the ESP32 on the Pi's top
    ez, pz = HEIGHT['esc'], HEIGHT['pi']
    P['s1_box'] = enc_w(B['pca'], AT['esc'], 'PCA box', 'stack', 'box', 4, BOX, 'The same PCA box, its pegs in the ESC top\'s holes.', z=ez)
    P['s1_case_b'] = enc_t(Bo, AT['esc'], 'Your case: base', 'stack', 'part', 5, CASEC, note_case_b, z=ez)
    P['s1_board'] = enc_t(All, AT['esc'], 'PCA model', 'stack', 'part', 5, 0x2f8a58, note_board, 14000, z=ez)
    P['s1_case_l'] = enc_t(Lo, AT['esc'], 'Your case: lid', 'stack', 'part', 5, 0xc9b48c, note_case_l, z=ez)
    for i, (p, n) in enumerate(zip(pca_plugs(), plug_names)):
        P['s1_plug%d' % i] = enc_w(p, AT['esc'], n, 'stack', 'part', 5, PLUGC, note_plug, z=ez)
    P['s1_top'] = enc_w(T['pca'], AT['esc'], 'PCA top', 'stack', 'box', 6, TOP, 'It lands at exactly %d units, %.0f over the floor.' % (CEILING_UNITS, CEILING), z=ez)
    P['s2_box'] = enc_w(B['esp'], AT['pi'], 'ESP32 box', 'stack2', 'box', 4, BOX, 'The same ESP32 box, its pegs in the Pi top\'s holes, clear of the bite for the Pi\'s plugs.', z=pz)
    for k in E:
        P['s2_' + k] = enc_w(E[k], AT['pi'], esp_names[k], 'stack2', 'part', 5, esp_col[k], esp_notes[k], z=pz)
    P['s2_top'] = enc_w(T['esp'], AT['pi'], 'ESP32 top', 'stack2', 'box', 6, TOP, 'It lands at exactly %d units, %.0f over the floor.' % (CEILING_UNITS, CEILING), z=pz)
    P['pack_ceil'] = enc_w(many(spacer(21.0, c, FLOOR + HEIGHT['pack']) for c in (-60.0, 60.0)), AT['pack'], 'Spacers, 3 units', 'pack', 'ceil', 4, SPACE, 'Two-peg spacers: they can\'t spin. Only needed if a ceiling is going to press down on this box.')
    P['esc_ceil'] = enc_w(many(spacer(35.0, c, FLOOR + HEIGHT['esc']) for c in (-15.0, 15.0)), AT['esc'], 'Spacers, 5 units', 'esc', 'ceil', 4, SPACE, 'For an ESC with nothing stacked on it. Only needed if a ceiling is going to press down on this box.')

    def ans(*qa):
        return [dict(q=q, a=a) for q, a in qa]

    def pr(*keys):
        return [dict(name=SET_NAMES[k], qty=q, **(info.get(k) or dict(time='', g=0.0))) for k, q in keys]
    joint = 'The pegs hold the box to the floor by friction until a ceiling or the next box presses down, but a flat bottom means they only stop sliding, not tipping.'
    pca_room = FLOOR + PCA_RIM - PLUG_DEEP - (BOARD_TOP + PLUG_SEAT + PLUG)
    esp_room = FLOOR + ESP_RIM - PLUG_DEEP - (ESP_TOP + PLUG_SEAT + PLUG)
    parts = dict(
        esc=dict(name='ESC', r=62, steps=['The box\'s pegs go in the floor.', 'The ESC presses in, leads through the window, and clicks past the ridges.', 'The top goes on, ready for the next box.'],
                 answers=ans(('How does it get in?', 'Straight down, with its leads going out through the window. That window is open at the top, so the leads don\'t have to thread through anything.'), ('How does it stack?', 'Six units tall. Its top has six holes, on the same two rows as every other box, so the PCA or ESP32 box pegs straight on.'), ('What holds it upside down?', 'The ridges hold the ESC with the top off. The top\'s pad is the real stop. ' + joint), ('Where do the wires go?', 'Out the window, 36 wide and from 12 up. I sized it off your photos: your leads leave across most of that face.')),
                 guesses=[('Which way round', 'finned face to the window', 'The closed wall covers the back. Your fins get the window.'), ('Window', '36 wide, from 12 up', 'Read off your photos, not measured.'), ('ESC thickness', '24', 'Still your 24. I\'m waiting on the two heights: to the case and to the fin tops.')], print=dict(small=pr(('esc_box', 1), ('esc_top', 1)))),
        pack=dict(name='Pack', r=100, steps=['The box\'s pegs go in the floor.', 'The pack drops in and clicks past the ridges, its lead out one end.', 'The top goes on, with pads on the pack.'],
                  answers=ans(('How does it get in?', 'Straight down, lead out either end. To swap, pull the top and lift the pack past the ridges. No tools, and the box stays in the floor.'), ('How does it stack?', 'Eight units tall, so it\'s as tall as a 5 and a 3. Its top has 18 holes, so two small boxes fit on it side by side.'), ('What holds it upside down?', 'The top\'s pads. The ridges only keep the pack from sliding out when the top is off. This is the hardest test of the five. ' + joint), ('Where do the wires go?', 'Out a short end, through a gap 18 wide that\'s open at the top. I\'m assuming the lead leaves by a short end.')),
                  guesses=[('Pack size', '141 x 26 x 45.7', 'From your model. Worth a caliper before printing.'), ('Lead position', 'a short end', 'Assumed. Both ends are open, so either way round works.'), ('Room over the pack', '5.3', 'What it takes to land on a whole unit, 8 x 7 = 56.'), ('Top\'s fit', '0.10 a side', 'Your rule from the horn pocket. Over 141 mm it may want more.')], print=dict(small=pr(('pack_box', 1), ('pack_top', 1)))),
        pi=dict(name='Pi', r=78, steps=['The sleeve\'s pegs go in the floor.', 'Your closed box slides in from the SD end.', 'Two stops peg in behind it.'],
                answers=ans(('How does it get in?', 'Your closed box slides in lengthwise until it hits the far stop. Two bricks peg in behind it.'), ('How does it stack?', 'Six units tall, the same as the ESC. Its top has the floor\'s holes everywhere except a bite over your plugs, so a box as wide as the ESP32\'s fits beside them.'), ('What holds it upside down?', 'The sleeve\'s top, right over your box. The lid\'s clips hold the lid. ' + joint), ('Where do the wires go?', 'Up through the bite, %.1f over the floor at the plugs\' top. A ceiling at %.0f leaves %.1f for the wires to bend, against my guessed %.0f.' % (BOTTOM + PB.PLUG_TOP, CEILING, CEILING - BOTTOM - PB.PLUG_TOP, BEND))),
                guesses=[('Air', 'slots in the top, windows in the walls', 'Picked to leave your lid\'s vents and side vents open. No heat test yet.'), ('Far stop', '4 at each corner', 'Picked to clear the USB ports, not checked against them.'), ('Clearance', '0.25 a side', 'Tested on the ESC only, and your box is itself a print.'), ('Print', 'with supports', 'The bottom spans 66 mm, too far to bridge. It\'s the one piece that needs supports.'), ('Whole box', 'not printed', 'Only the ring test has been printed since the rings were bored.')], print=dict(small=pr(('pi_sleeve', 1), ('pi_stop', 2)))),
        pca=dict(name='PCA9685', r=62, steps=['The box\'s pegs go in the floor.', 'Your case, with the board in it, snaps in past the ridges.', 'The top goes on over the plugs, ready for the next box.'],
                 answers=ans(('How does it get in?', 'Your case stays exactly as it is, board clamped inside. The whole case presses into the box and clicks past four ridges.'), ('How does it stack?', 'Five units tall. Its top sits over the plugs, with the full 5 x 2 of holes. Your case is 75 x 30, exactly 5 x 2 of the grid.'), ('What holds it upside down?', 'Your lid clamps the board in your case, and the ridges hold the case in the box. ' + joint), ('Where do the wires go?', 'They come up off the plugs and out the side windows, which are open on all four sides. There\'s %.1f over the plugs for them to turn, against a guessed %.0f if they had to go straight up.' % (pca_room, BEND))),
                 guesses=[('Your case', 'as downloaded', 'Is PCA9685_Simple_Case the one you printed? I read its fit off the file.'), ('End headers', 'straight up', 'What your lid\'s end slots suit. Tell me if yours are right-angled.'), ('Plug height', '%.0f + %.1f seat' % (PLUG, PLUG_SEAT), 'A guess. It sets this box\'s 5 units.'), ('Case ridges', '%.1f' % RIDGE, 'The case\'s corners are rounded, so the ridges sit on its straight sides.')], print=dict(small=pr(('case_base', 1), ('case_lid', 1), ('pca_box', 1), ('pca_top', 1)))),
        esp=dict(name='ESP32', r=56, steps=['The box\'s pegs go in the floor.', 'The board snaps in upside down on its corner blocks.', 'The top goes on over the plugs, ready for the next box.'],
                 answers=ans(('How does it get in?', 'Upside down, pins up. Press it past the four ridges onto the corner blocks, with the USB at the open end.'), ('How does it stack?', 'Five units tall, the same as the PCA. Its top has six holes, and it sits over the plugs.'), ('What holds it upside down?', 'The four ridges over the board\'s corners. ' + joint), ('Where do the wires go?', 'Off the plugs and out the side windows. There\'s %.1f over the plugs for them to turn.' % esp_room)),
                 guesses=[('Board size', '55 x 28', 'Typical, not yours. I need a caliper, or its model if you have one.'), ('Upside down', 'pins up', 'My pick, so the plugs go on from above. Your call.'), ('Shelf', '%.1f' % ESP_SHELF, 'Room for the module and USB, both guessed.'), ('Your old case', 'not used', 'arduino_case.gcode is 29 x 56 inside. If it\'s the ESP32\'s, it could go in a box the way your PCA case does.')], print=dict(small=pr(('esp_box', 1), ('esp_top', 1)))),
        stack=dict(name='ESC + PCA', r=72, steps=['The ESC\'s box goes in the floor.', 'The ESC clicks in.', 'The ESC\'s top goes on.', 'The PCA box\'s pegs go in that top\'s holes.', 'Your case snaps in.', 'The PCA\'s top goes on, at %d units.' % CEILING_UNITS],
                   answers=ans(('What is this showing?', 'Stacking the way Gridfinity does it. A 6-unit box and a 5-unit box come to 11 units, and a pack with a 3-unit spacer comes to the same.'), ('What holds the lower box?', 'The ceiling, when there is one, presses straight down through the walls of both.'), ('What does it cost?', 'You have to lift the PCA off to get at the ESC. Its wires need the slack for that.'), ('Is this a decision?', 'No. It\'s an example of what the tops allow.')),
                   guesses=[], print=dict(small=[])),
        stack2=dict(name='Pi + ESP32', r=78, steps=['The Pi\'s sleeve goes in the floor.', 'Your box slides in.', 'Two stops peg in behind it.', 'The ESP32 box\'s pegs go in the Pi top\'s holes, beside the plugs.', 'The ESP32 snaps in.', 'The ESP32\'s top goes on, at %d units.' % CEILING_UNITS],
                    answers=ans(('What is this showing?', 'The Pi stacking. The ESP32 box sits on the sleeve\'s top, beside the bite for your plugs.'), ('Does it block the Pi?', 'It covers some of the air slots, so the Pi could run hotter. Nothing has been heat-tested yet. The plugs stay clear.'), ('What does it cost?', 'The Pi slides out sideways, so the ESP32 can stay on it.'), ('Is this a decision?', 'No. It\'s an example of what the tops allow.')),
                    guesses=[], print=dict(small=[])))
    common = [('One unit', '%.0f' % UNIT, 'Gridfinity\'s own height unit. Each box is a whole number of them, so stacks add up: ESC 6, Pi 6, pack 8, PCA 5, ESP32 5.'),
              ('Ceiling', '%d units, %.0f' % (CEILING_UNITS, CEILING), 'Where the stacks can all meet, and enough for your Pi\'s plugs and a wire bend. Spacers change it, and the boxes don\'t. Not a decision.'),
              ('Walls', '%.1f' % T_W, 'Up from 1.2. Gridfinity bins run about 1.2 and stay stiff because they\'re closed boxes with a floor, so yours get both.'),
              ('Flat bottom', '%.1f' % BOTTOM, 'Picked. It prints last, as a bridge across the opening, so its inside may sag a little.'),
              ('Piece on top', '%.1f thick' % LID_T, 'Enough for the 2.4 peg, with the floor\'s through holes.'),
              ('Snap ridges', '%.1f' % RIDGE, 'Untested. 45 degrees both ways, so a part can be pulled out by hand.'),
              ('5 mm pegs in 5.1', 'your bench', 'Tried in a floor patch with one frame. More pegs means more force to press in, so a 5.2 floor may suit. Your patch has both.'),
              ('PLA across layers', '%.0f MPa' % PLA_ACROSS, 'A guess at the break point for a standing peg. The blocks you have can settle it.')]
    for k, d in parts.items():
        d['guesses'] = [dict(name=n, value=v, why=w) for n, v, w in d['guesses']]
        at = AT['esc'] if k == 'stack' else AT['pi'] if k == 'stack2' else AT[k]
        d['center'] = [at[0], at[1], 34.0 if k.startswith('stack') else 26.0]
    set_ = dict(small=[dict(name=SET_NAMES[k], qty=c, **(info.get(k) or dict(time='', g=0.0))) for k, c in (('esc_box', 2), ('esc_top', 2), ('pack_box', 2), ('pack_top', 2), ('pi_sleeve', 1), ('pi_stop', 2), ('pca_box', 1), ('pca_top', 1), ('case_base', 1), ('case_lid', 1), ('esp_box', 1), ('esp_top', 1), ('spacer_3', 4), ('spacer_5', 2))])
    colors = dict(box='#e0b35c', spacer='#8f8fd6')
    meta = dict(order=['esc', 'pack', 'pi', 'pca', 'esp', 'stack', 'stack2'], parts=parts, common=[dict(name=n, value=v, why=w) for n, v, w in common], ceiling=CEILING, section=UNIT, floor=FLOOR, floor_x=FLOOR_X, floor_y=FLOOR_Y,
                info=info, set=set_, pegs=peg_table(), stiff=stiffness(), pla=PLA_ACROSS, unit=UNIT, ceiling_units=CEILING_UNITS,
                stacks=[dict(name=s['name'], parts=[dict(n=a, u=b, c=colors[c]) for a, b, c in s['parts']]) for s in STACKS],
                all=dict(name='All', r=175, center=[0, 18, 34.0], steps=['Boxes.', 'Parts.', 'Tops and stops.', 'The boxes that stack on them.', 'Their parts.', 'Their tops.']))
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', 'window.PARTS=' + json.dumps(P) + ';window.META=' + json.dumps(meta) + ';')
    p = os.path.join(config.TWIN_OUT, 'part_boxes_view.html')
    open(p, 'w', encoding='utf-8').write(html)
    print('wrote %s (%.1f MB)' % (p, len(html) / 1e6))


if __name__ == '__main__':
    if 'page' in sys.argv[1:]:                  # only the page, for working on the viewer: no checks, no STLs
        B = dict(esc=esc_box(), pack=pack_box(), pi=pi_sleeve(), pca=pca_box(), esp=esp_box())
        T = dict(esc=esc_top(), pack=pack_top(), pca=pca_top(), esp=esp_top())
        page(B, T, esp_model(), pca_board(), json.load(open(SLICE)) if os.path.exists(SLICE) else {})
        sys.exit(0)
    good, B, T, Stops, E, pca, Cb, Cl = check()
    print('Print pieces (all upside down, so the pegs point up):')
    os.makedirs(PRINT, exist_ok=True)
    paths = {}
    for k, (w, q) in pieces(B, T).items():
        f = flip(w)
        p = os.path.join(PRINT, 'partbox_%s.stl' % k)
        write_stl(f.val().wrapped, p, lin=0.02, ang=0.2)
        h_ok, msg = health(p); good &= bool(h_ok)
        bb = f.val().BoundingBox()
        print('  %-14s x%d %5.1f x %5.1f x %5.1f  %s %s' % (k, q, bb.xlen, bb.ylen, bb.zlen, 'ok ' if h_ok else 'BAD', msg))
        paths[k] = p
    paths['case_base'], paths['case_lid'] = CASE_BASE, CASE_LID          # his, as they are, in case they need printing
    if 'slice' in sys.argv[1:]:
        print('Slices, draft, not sent to the printer:')
        slice_all(paths)
    info = json.load(open(SLICE)) if os.path.exists(SLICE) else {}
    if os.path.exists(TEMPLATE):
        page(B, T, E, pca, info)
    print('checks:', 'all pass' if good else 'SOMETHING FAILED')
    sys.exit(0 if good else 1)
