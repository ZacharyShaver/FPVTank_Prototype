"""SUPERSEDED 2026-11-08 by bricks.py, before anything was printed. Zach: "the top should not be a plat with legs". Kept for the record.

One holder for each part Zach owns, each with a cap that snaps on (2026-11-08).

Zach, after the ESC could still fall out of its frame: "generate one for each please i want to inspect them ... we may need to cap these some
how. for them to truly be held on all sides there has to be some kind of ceiling. maybe we set a block height. all parts must be able to be
printed with a lid part that snaps into another lid maybe? im iffy because some parts can actually be securely enclosed like the pi".

    python twin/holders.py         # builds, checks with controls, STLs in twin/out/print/, twin/out/holders_view.html ("Part Holders")
    python twin/holders.py slice   # the same, and slices every piece (draft, not printed) into twin/out/holders_slice.json
    python twin/holders.py page    # only the page

A holder is two pieces. The tray has the walls and the pegs, and goes in the floor. The cap comes down over the part and snaps onto the tray:
its legs carry hooks that click under small catches on the tray's outside. Each cap comes at block height (its top at BLOCK over the floor,
so one ceiling can sit on all of them) and just over its part, to compare.

Frame: x along the part, y across it, z up from the floor's underside (the floor's top at FLOOR). Built at the origin, placed by AT, which puts
every peg on one 15 mm grid. AT is a line-up for inspecting, not a layout. * = picked, for Zach to OK or measure.
"""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
sys.path.insert(0, HERE)
import numpy as np
import cadquery as cq
import config
from export import write_stl, health
import peg_test as PT
from peg_test import rect, cyl, peg, vol, FLOOR, PITCH, PEG, POST
import pi_box as PB

PRINT = os.path.join(config.TWIN_OUT, 'print')
TEMPLATE = os.path.join(HERE, 'holders_view_template.html')
PCA_STEP = os.path.join(config.REPO, 'reference', 'downloads', 'pca9685', 'generic.step')
SLICE = os.path.join(config.TWIN_OUT, 'holders_slice.json')

HOLE = PT.HOLE_PICK               # his bench, 2026-11-08
WALL = 1.2                        # frame v2's: "fits fine enough"
FIT = 0.25                        # * a side, tested only on the ESC's thickness
LEAD = 0.6                        # frame v2's mouth chamfer
CAP_T, CAP_GAP = 2.0, 0.3         # * the cap's plate; air between it and the part
LEG_T, LEG_GAP = 1.6, 0.15        # * a snap leg's thickness; the air between hook tip and tray wall
BUMP = 0.8                        # * how far a catch stands off the tray's wall
CATCH_GAP = 0.15                  # * vertical play at the hook
HOOK_FLAT = 0.8                   # * the hook's height before its lead-in
RIM_DROP = 1.8                    # * the catch's flat face, below the tray's rim
COLLAR = 3.0                      # * how far the cap's collar comes down round the part's top
N0, N1 = LEG_GAP, BUMP + LEG_GAP  # the hook's tip and the leg's inner face, out from the wall
N2 = N1 + LEG_T                   # the leg's outer face: a cap's overhang past the tray
HOOK_DEPTH = BUMP - N0            # how far the hook overlaps the catch: how far a leg bends going on
STRAIN_MAX = 0.01                 # * my limit for PLA bending across its layers

PACK = (141.0, 26.0, 45.7)        # his model's box (LeftBattery.stl), on edge. Not calipered; print 1's bay read "a bit extra room"
ESC = PT.ESC                      # his caliper: 45 long, 24 thick, 34 tall stood on edge
BLOCK = PACK[2] + CAP_GAP + CAP_T  # * the block height: set by the tallest part that has to go under the ceiling, 48.0
PLUG, PLUG_SEAT, BEND = 14.0, 2.5, 15.0   # * a Dupont housing; the header's plastic under it; room for wires to turn over (the Pi box's guess)
PCA_SHELF = 3.2                   # * the board's underside over the floor. His model's pins reach 2.1 under the board
ESP_SHELF = 5.0                   # * the same, ESP32 upside down: room for the module and USB under it
ESP = (55.0, 28.0, 1.6)           # * "typical dev board". His arduino_case print is 29 x 56 inside, so a board this size fits it
PI_BOX = (98.5, 65.6, PB.RIM)     # the box's outside
AT = dict(esc=(-90.0, -45.0), pack=(0.0, 97.5), pi=(7.5, 30.0), pca=(0.0, -52.5), esp=(90.0, -52.5))
FLOOR_X, FLOOR_Y = (-130.0, 130.0), (-85.0, 120.0)


def W(s):
    return cq.Workplane('XY').newObject([s])


def shift(w, x=0.0, y=0.0, z=0.0):
    return w.translate((x, y, z))


def prism(normal, s, o, c, w, pts):
    """a solid from a (distance out from a wall's face, z) outline, w wide along the wall, centred on c. normal x or y, s the side, o the face"""
    if normal == 'x':
        P, v = [cq.Vector(s * (o + n), c - w / 2, z) for n, z in pts], cq.Vector(0, w, 0)
    else:
        P, v = [cq.Vector(c - w / 2, s * (o + n), z) for n, z in pts], cq.Vector(w, 0, 0)
    return W(cq.Solid.extrudeLinear(cq.Wire.makePolygon(P + [P[0]]), [], v))


def catch(normal, s, o, c, w, zc):
    """a tray's catch: a flat face down for the hook, a 45 degree slope on top for the hook to ride over"""
    return prism(normal, s, o, c, w, [(-0.3, zc), (BUMP, zc), (BUMP, zc + 0.5), (0.0, zc + 0.5 + BUMP), (-0.3, zc + 0.5 + BUMP)])


def leg(normal, s, o, c, w, zc, under):
    """a cap's snap leg, from the plate down outside the wall, its hook just under the catch"""
    z1 = zc - CATCH_GAP; z2 = z1 - HOOK_FLAT; tip = z2 - (N1 - N0)
    return prism(normal, s, o, c, w, [(N1, under + 0.5), (N2, under + 0.5), (N2, tip), (N1, tip), (N0, z2), (N0, z1), (N1, z1)])


def tray(a, b, h, pegs, ears, catches, notches=(), corners=None):
    """walls round a part, ears out to posts, a peg under each post, catches on the outside, then the opening cut through everything"""
    z0, z1 = FLOOR, FLOOR + h
    zc = z1 - RIM_DROP
    F = rect(-a / 2 - WALL, a / 2 + WALL, -b / 2 - WALL, b / 2 + WALL, z0, z1)
    for normal, s, to, c, hw in ears:
        if normal == 'x':
            F = F.union(rect(*sorted((s * (a / 2 + WALL - 0.2), s * to)), c - hw, c + hw, z0, z1))
        else:
            F = F.union(rect(c - hw, c + hw, *sorted((s * (b / 2 + WALL - 0.2), s * to)), z0, z1))
    for x, y in pegs:
        F = F.union(cyl(POST, z0, z1, x, y)).union(peg(PEG, x, y))
    for normal, s, c, w in catches:
        F = F.union(catch(normal, s, (a if normal == 'x' else b) / 2 + WALL, c, w, zc))
    F = F.cut(rect(-a / 2, a / 2, -b / 2, b / 2, z0 - 1, z1 + 1))
    F = F.cut(cq.Workplane('XY').workplane(offset=z1 - LEAD).rect(a, b).workplane(offset=LEAD + 0.01).rect(a + 2 * LEAD + 0.02, b + 2 * LEAD + 0.02).loft())
    for s, hw, z in notches:                                               # a gap through an end wall, for a plug or a port
        F = F.cut(rect(*sorted((s * (a / 2 - 0.5), s * (a / 2 + WALL + 0.5))), -hw, hw, z, z1 + 1))
    if corners:                                                            # corner blocks: the board's shelf
        dx, dy, zs = corners
        for sx in (-1, 1):
            for sy in (-1, 1):
                F = F.union(rect(*sorted((sx * (a / 2 + 0.2), sx * (a / 2 - dx))), *sorted((sy * (b / 2 + 0.2), sy * (b / 2 - dy))), z0, z0 + zs))
    return F


def cap_legs(C, a, b, h, under, catches):
    zc = FLOOR + h - RIM_DROP
    for normal, s, c, w in catches:
        C = C.union(leg(normal, s, (a if normal == 'x' else b) / 2 + WALL, c, w, zc, under))
    return C


def collar(x_in, y_in, t, z, under):
    """a ring down round the part's top, hanging from the plate"""
    return rect(-x_in - t, x_in + t, -y_in - t, y_in + t, z, under + 0.5).cut(rect(-x_in, x_in, -y_in, y_in, z - 1, under))


# ---------------------------------------------------------------- the ESC
ESC_A, ESC_B, ESC_H = ESC[0], ESC[1] + 2 * FIT, 12.0        # frame v2: 45.0 with no clearance (his press fit), 0.25 a side across, 12 tall
ESC_CATCH = [('x', s, c, 6.0) for s in (-1, 1) for c in (-8.0, 8.0)]   # * on the end walls, both sides of the ear: nothing crosses a long face


def esc_tray():
    return tray(ESC_A, ESC_B, ESC_H, [(-30.0, 0.0), (30.0, 0.0)], [('x', -1, 30.0, 0.0, POST / 2), ('x', 1, 30.0, 0.0, POST / 2)], ESC_CATCH)


def esc_cap(h):
    top, under, pt = FLOOR + h, FLOOR + h - CAP_T, FLOOR + ESC[2]
    C = rect(-(ESC_A / 2 + WALL + N2), ESC_A / 2 + WALL + N2, -(ESC_B / 2 + WALL), ESC_B / 2 + WALL, under, top)
    C = C.union(collar(ESC_A / 2 + 0.25, ESC_B / 2, 1.0, pt - COLLAR, under))
    if under - pt > CAP_GAP + 0.05:                                        # at block height: two ribs reach down to the ESC's top, and the sides open up
        for x in (-12.0, 12.0):
            C = C.union(rect(x - 0.8, x + 0.8, -ESC_B / 2 - 0.2, ESC_B / 2 + 0.2, pt + CAP_GAP, under + 0.5))
        if under - pt > 4.0:
            for s in (-1, 1):
                C = C.cut(rect(-10.0, 10.0, *sorted((s * (ESC_B / 2 - 0.1), s * (ESC_B / 2 + 2.0))), pt + 1.5, under - 1.0))
    return cap_legs(C, ESC_A, ESC_B, ESC_H, under, ESC_CATCH)


def esc_part():
    return [('esc', 'Your ESC', rect(-ESC[0] / 2, ESC[0] / 2, -ESC[1] / 2, ESC[1] / 2, FLOOR, FLOOR + ESC[2]), 0x4a78b5, 'Your caliper: 45 long, 34 wide, 24 tall, stood on edge. A plain box with no wires, so your leads and the room they take are not drawn. You don\'t print this one.')]


# ---------------------------------------------------------------- the pack
PACK_A, PACK_B, PACK_H = PACK[0] + 2 * FIT, PACK[1] + 2 * FIT, 15.0    # * walls lower than the sim's 23, after the ESC's 12 worked
PACK_CATCH = [('y', s, c, 20.0) for s in (-1, 1) for c in (-45.0, 45.0)]
PACK_PEGS = [(s, t) for s in (-75.0, 75.0) for t in (-7.5, 7.5)]


def pack_tray():
    return tray(PACK_A, PACK_B, PACK_H, PACK_PEGS, [('x', -1, 75.0, 0.0, 11.0), ('x', 1, 75.0, 0.0, 11.0)], PACK_CATCH)


def pack_cap(h):
    top, under, pt = FLOOR + h, FLOOR + h - CAP_T, FLOOR + PACK[2]
    C = rect(-(PACK_A / 2 + WALL), PACK_A / 2 + WALL, -(PACK_B / 2 + WALL + N2), PACK_B / 2 + WALL + N2, under, top)
    C = C.cut(rect(8.0, 62.0, -9.5, 9.5, under - 1, top + 1)).cut(rect(-62.0, -8.0, -9.5, 9.5, under - 1, top + 1))   # * windows, for weight
    C = C.union(collar(PACK_A / 2, PACK_B / 2, WALL, pt - COLLAR, under))
    return cap_legs(C, PACK_A, PACK_B, PACK_H, under, PACK_CATCH)


def pack_part():
    return [('pack', 'Your pack', rect(-PACK[0] / 2, PACK[0] / 2, -PACK[1] / 2, PACK[1] / 2, FLOOR, FLOOR + PACK[2]), 0x4a78b5, 'Zeee 2S 5200 on edge, 141 x 26 x 45.7, from the box of your model. Not calipered. You don\'t print this one.')]


# ---------------------------------------------------------------- the Pi: its own box encloses it; the frame and straps only hold the box down
PI_A, PI_B, PI_H = PI_BOX[0] + 2 * FIT, PI_BOX[1] + 2 * FIT, 6.0       # * low, so it stays under the port windows
PI_PEGS = [(s, t) for s in (-52.5, 52.5) for t in (-15.0, 15.0)]
STRAPS = ((32.0, 16.0), (-44.0, 10.0))                                 # * centre and width: past the lid's notch at both ends
PI_CATCH = [('y', s, c, w) for s in (-1, 1) for c, w in STRAPS]
PI_DX, PI_DY = PI_BOX[0] / 2, PI_BOX[1] / 2                            # the box's own frame to this one


def pi_tray():
    return tray(PI_A, PI_B, PI_H, PI_PEGS, [('x', -1, 52.5, 0.0, 18.5), ('x', 1, 52.5, 0.0, 18.5)], PI_CATCH)


def pi_cap(h):
    """two straps over the box's ends, tied by a rail along the side away from the header, so they come off as one piece"""
    top, under, rim = FLOOR + h, FLOOR + h - CAP_T, FLOOR + PI_BOX[2]
    y = PI_B / 2 + WALL + N2
    C = rect(STRAPS[1][0] - STRAPS[1][1] / 2, STRAPS[0][0] + STRAPS[0][1] / 2, -y, -y + 8.0, under, top)
    for c, w in STRAPS:
        C = C.union(rect(c - w / 2, c + w / 2, -y, y, under, top))
        if under - rim > CAP_GAP + 0.05:                                   # at block height: feet down to the box's rim
            for s in (-1, 1):
                C = C.union(rect(c - w / 2, c + w / 2, *sorted((s * 27.0, s * 31.0)), rim + CAP_GAP, under + 0.5))
    return cap_legs(C, PI_A, PI_B, PI_H, under, PI_CATCH)


def pi_plugs():
    x0, x1 = PB.HDR_X[0] - PI_DX, PB.HDR_X[1] - PI_DX
    y0, y1 = PB.HDR_Y[0] - PI_DY, PB.HDR_Y[1] - PI_DY
    return rect(x0, x1, y0, y1, FLOOR + PB.PLUG_TOP - PB.HOUSING, FLOOR + PB.PLUG_TOP), (x0, x1, y0, y1)


def pi_box_solid():
    """the box's outside, for the checks: its real mesh isn't a valid exact solid (pi_box.py), and this outline is the widest it gets"""
    return rect(-PI_BOX[0] / 2, PI_BOX[0] / 2, -PI_BOX[1] / 2, PI_BOX[1] / 2, FLOOR, FLOOR + PI_BOX[2])


# ---------------------------------------------------------------- the boards: a shelf at the corners, four columns press on the corners from above
PCA = (62.2, 25.7, 1.6)                                                # his PCA model (the generic one in Downloads); not calipered yet
PCA_A, PCA_B, PCA_H = PCA[0] + 2 * FIT, PCA[1] + 2 * FIT, PCA_SHELF + PCA[2] + 1.2
PCA_CATCH = [('y', s, c, 10.0) for s in (-1, 1) for c in (-20.0, 20.0)]
PCA_TOP = FLOOR + PCA_SHELF + PCA[2]                                   # the board's top
PCA_COL = [(s * 28.6, t * 10.6) for s in (-1, 1) for t in (-1, 1)]


def pca_tray():
    return tray(PCA_A, PCA_B, PCA_H, [(0.0, -22.5), (0.0, 22.5)], [('y', -1, 22.5, 0.0, POST / 2), ('y', 1, 22.5, 0.0, POST / 2)], PCA_CATCH,
                notches=[(-1, 8.5, PCA_TOP - 0.2), (1, 8.5, PCA_TOP - 0.2)], corners=(4.0, 4.5, PCA_SHELF))


def columns(C, pts, w, d, z, under):
    for x, y in pts:
        C = C.union(rect(x - w / 2, x + w / 2, y - d / 2, y + d / 2, z, under + 0.5))
    return C


def pca_cap(h):
    top, under = FLOOR + h, FLOOR + h - CAP_T
    C = rect(-(PCA_A / 2 + WALL), PCA_A / 2 + WALL, -(PCA_B / 2 + WALL + N2), PCA_B / 2 + WALL + N2, under, top)
    C = C.cut(rect(-26.0, 26.0, -10.0, 10.0, under - 1, top + 1))          # * a window: air, and room for wires to bend
    C = columns(C, PCA_COL, 3.5, 3.5, PCA_TOP + 0.1, under)
    return cap_legs(C, PCA_A, PCA_B, PCA_H, under, PCA_CATCH)


def pca_board():
    """his model's 310 solids, board bottom on the shelf"""
    w = cq.importers.importStep(PCA_STEP)
    return [s.moved(cq.Location(cq.Vector(0, 0, FLOOR + PCA_SHELF + 0.8))) for s in w.solids().vals()]


def pca_plugs():
    """* channels 0 and 1, and the Dupont plugs off both end headers: the model has the header on one end, your wiring uses both"""
    return [rect(-25.4, -20.3, -12.7, -5.1, PCA_TOP + PLUG_SEAT, PCA_TOP + PLUG_SEAT + PLUG),
            rect(-47.1, -33.1, -7.6, 7.6, PCA_TOP, PCA_TOP + PLUG_SEAT), rect(33.1, 47.1, -7.6, 7.6, PCA_TOP, PCA_TOP + PLUG_SEAT)]


ESP_A, ESP_B, ESP_H = ESP[0] + 2 * FIT, ESP[1] + 2 * FIT, ESP_SHELF + ESP[2] + 1.2
ESP_CATCH = [('y', s, c, 10.0) for s in (-1, 1) for c in (-17.0, 17.0)]
ESP_TOP = FLOOR + ESP_SHELF + ESP[2]
ESP_COL = [(s * 25.95, t * 9.0) for s in (-1, 1) for t in (-1, 1)]


def esp_tray():
    return tray(ESP_A, ESP_B, ESP_H, [(0.0, -22.5), (0.0, 22.5)], [('y', -1, 22.5, 0.0, POST / 2), ('y', 1, 22.5, 0.0, POST / 2)], ESP_CATCH,
                notches=[(1, 6.5, FLOOR - 1.0)], corners=(3.0, 5.0, ESP_SHELF))


def esp_cap(h):
    top, under = FLOOR + h, FLOOR + h - CAP_T
    C = rect(-(ESP_A / 2 + WALL), ESP_A / 2 + WALL, -(ESP_B / 2 + WALL + N2), ESP_B / 2 + WALL + N2, under, top)
    C = C.cut(rect(-21.0, 21.0, -11.0, 11.0, under - 1, top + 1))
    C = columns(C, ESP_COL, 3.1, 3.5, ESP_TOP + 0.1, under)
    return cap_legs(C, ESP_A, ESP_B, ESP_H, under, ESP_CATCH)


def esp_model():
    """* no model of his board exists. Upside down, so its factory pins point up and the plugs go on from above"""
    z0 = FLOOR + ESP_SHELF
    return dict(board=rect(-ESP[0] / 2, ESP[0] / 2, -ESP[1] / 2, ESP[1] / 2, z0, z0 + ESP[2]),
                under=rect(-27.0, -9.0, -9.0, 9.0, z0 - 3.2, z0).union(rect(23.0, 28.5, -4.0, 4.0, z0 - 3.0, z0)),
                pins=rect(-24.0, 24.0, 11.43, 13.97, ESP_TOP, ESP_TOP + PLUG_SEAT).union(rect(-24.0, 24.0, -13.97, -11.43, ESP_TOP, ESP_TOP + PLUG_SEAT)),
                plugs=rect(-24.0, 24.0, 11.43, 13.97, ESP_TOP + PLUG_SEAT, ESP_TOP + PLUG_SEAT + PLUG).union(rect(-24.0, 24.0, -13.97, -11.43, ESP_TOP + PLUG_SEAT, ESP_TOP + PLUG_SEAT + PLUG)))


# ---------------------------------------------------------------- all five
OWN = dict(esc=ESC[2] + CAP_GAP + CAP_T, pack=BLOCK, pi=PI_BOX[2] + CAP_GAP + CAP_T,
           pca=PCA_TOP - FLOOR + PLUG_SEAT + PLUG + BEND + CAP_GAP + CAP_T, esp=ESP_TOP - FLOOR + PLUG_SEAT + PLUG + BEND + CAP_GAP + CAP_T)
BUILD = dict(esc=(esc_tray, esc_cap), pack=(pack_tray, pack_cap), pi=(pi_tray, pi_cap), pca=(pca_tray, pca_cap), esp=(esp_tray, esp_cap))
HT = dict(esc=ESC_H, pack=PACK_H, pi=PI_H, pca=PCA_H, esp=ESP_H)
NAMES = dict(esc='ESC', pack='Pack', pi='Pi', pca='PCA9685', esp='ESP32')


def floor():
    pts = [(x, y) for x in np.arange(-120, 121, PITCH) for y in np.arange(-75, 106, PITCH)]
    return rect(*FLOOR_X, *FLOOR_Y, 0, FLOOR).faces('>Z').workplane(origin=(0, 0, FLOOR)).pushPoints(pts).hole(HOLE)


def strain(L, t=LEG_T):
    """a straight leg's bending strain going over the catch"""
    return 1.5 * t * HOOK_DEPTH / L ** 2


def leg_len(k, h):
    return (FLOOR + h - CAP_T) - (FLOOR + HT[k] - RIM_DROP - CATCH_GAP)


def check():
    ok = True

    def line(what, good, got):
        nonlocal ok
        ok &= bool(good)
        print('  %-66s %s %s' % (what, got, 'ok' if good else 'WRONG'))

    solid = dict(esc=esc_part()[0][2], pack=pack_part()[0][2], pi=pi_box_solid(), pca=None, esp=None)
    Fl = floor()
    T = {k: BUILD[k][0]() for k in BUILD}
    C = {k: {m: BUILD[k][1](h) for m, h in (('block', BLOCK), ('own', OWN[k]))} for k in BUILD}
    E = esp_model()
    solid['esp'] = E['board'].union(E['under'])
    pca = pca_board()
    solid['pca'] = rect(-PCA[0] / 2, PCA[0] / 2, -PCA[1] / 2, PCA[1] / 2, FLOOR + PCA_SHELF, PCA_TOP)
    for k in BUILD:
        print(NAMES[k] + ':')
        v = vol(Fl, shift(T[k], *AT[k])); line('tray on the floor, pegs in the %.1f holes' % HOLE, v < 1e-3, '%.3f mm3' % v)
        v = vol(Fl, shift(T[k], AT[k][0] + PITCH / 3, AT[k][1])); line('control: 5 mm off its holes', v > 1, '%.2f mm3' % v)
        v = vol(T[k], solid[k]); line('part in the tray', v < 1e-3, '%.3f mm3' % v)
        for lift in (5.0, 15.0, 40.0):
            v = vol(T[k], shift(solid[k], z=lift))
            if v > 1e-3:
                line('part lifting straight out, %.0f mm' % lift, False, '%.3f mm3' % v)
        print('  %-66s %s' % ('part lifts straight out, 5, 15 and 40 mm', 'checked'))
        for m, cp in C[k].items():
            v = vol(cp, solid[k]); line('%s cap on the part, seated' % m, v < 1e-3, '%.3f mm3' % v)
            v = vol(cp, T[k]); line('%s cap on the tray, seated' % m, v < 1e-3, '%.3f mm3' % v)
            v = vol(shift(cp, z=1.0), T[k]); line('%s cap pulled up 1 mm hits the catches: it is locked' % m, v > 1, '%.2f mm3' % v)
            L = leg_len(k, BLOCK if m == 'block' else OWN[k]); e = strain(L)
            line('%s cap, leg %.0f mm long bends %.2f: strain %.2f %%' % (m, L, HOOK_DEPTH, 100 * e), e < STRAIN_MAX, '')
    print('Hardware, with controls:')
    v = vol(C['pi']['block'], pi_plugs()[0]); line('Pi straps clear the Dupont plugs', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(C['pi']['block'], x=-32.0), pi_plugs()[0]); line('control: a strap moved over the header', v > 1, '%.2f mm3' % v)
    v = vol(T['pi'], shift(pi_box_solid(), z=0)); line('Pi box outline in its frame', v < 1e-3, '%.3f mm3' % v)
    v = vol(T['pi'], rect(-49.6, 49.6, -33.2, 33.2, FLOOR, FLOOR + 10)); line('control: a box 0.7 bigger each way', v > 1, '%.2f mm3' % v)
    tot = dict(tray=0.0, block=0.0, own=0.0); worst = None
    for s in pca:
        b = s.BoundingBox()
        for key, w in (('tray', T['pca']), ('block', C['pca']['block']), ('own', C['pca']['own'])):
            v = vol(w, W(s))
            tot[key] += v
            if v > 1e-3:
                worst = (key, b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax, v)
    line('your PCA model (310 solids) in the tray', tot['tray'] < 1e-3, '%.3f mm3' % tot['tray'])
    line('your PCA model under the block cap', tot['block'] < 1e-3, '%.3f mm3' % tot['block'])
    line('your PCA model under the own-height cap', tot['own'] < 1e-3, '%.3f mm3' % tot['own'])
    if worst:
        print('    located:', worst)
    low = columns(rect(-40, 40, -20, 20, 40, 42), PCA_COL, 3.5, 3.5, PCA_TOP - 0.5, 40.0)
    v = vol(low, solid['pca']); line('control: the columns 0.6 lower press into the board', v > 1, '%.2f mm3' % v)
    for i, p in enumerate(pca_plugs()):
        for key, w in (('tray', T['pca']), ('block cap', C['pca']['block']), ('own cap', C['pca']['own'])):
            v = vol(w, p)
            if v > 1e-3:
                line('PCA plug %d against the %s' % (i, key), False, '%.3f mm3' % v)
    print('  %-66s %s' % ('PCA plugs clear the tray and both caps', 'checked'))
    for nm in E:
        for key, w in (('tray', T['esp']), ('block cap', C['esp']['block']), ('own cap', C['esp']['own'])):
            v = vol(w, E[nm])
            if v > 1e-3:
                line('ESP32 %s against the %s' % (nm, key), False, '%.3f mm3' % v)
    print('  %-66s %s' % ('ESP32 board, module, pins and plugs clear the tray and both caps', 'checked'))
    v = vol(T['esp'], rect(-27.75, 27.75, -14.25, 14.25, FLOOR, ESP_TOP)); line('control: a solid block filling the ESP32 opening hits the shelf', v > 1, '%.2f mm3' % v)
    v = vol(T['esc'], rect(-23.0, 23.0, -12.0, 12.0, FLOOR, FLOOR + 34)); line('control: an ESC 1 mm longer', v > 1, '%.2f mm3' % v)
    e = strain(8.0); line('control: an 8 mm leg would be over my strain limit (%.1f %%)' % (100 * e), e > STRAIN_MAX, '')
    v2 = PT.frame2().val().Volume(); v3 = T['esc'].val().Volume()
    print('  ESC tray against the printed frame v2: +%.1f mm3, the four catches' % (v3 - v2))
    return ok, T, C, E, pca


def flip(w):
    f = w.rotate((0, 0, 0), (1, 0, 0), 180)
    return f.translate((0, 0, -f.val().BoundingBox().zmin))


def pieces(T, C):
    out = {}
    for k in BUILD:
        out['%s_tray' % k] = T[k]
        out['%s_cap' % k] = C[k]['block']
        if abs(OWN[k] - BLOCK) > 0.01:
            out['%s_cap_own' % k] = C[k]['own']
    return out


def slice_all(paths):
    res = {}
    for k, p in paths.items():
        r = subprocess.run([sys.executable, os.path.join(config.REPO, 'tools', 'orca.py'), p, '--draft', '--set', 'brim_type=outer_only', '--set', 'brim_width=5',
                            '--set', 'enable_support=0', '--name', 'holder_' + k], capture_output=True, text=True)
        m = re.search(r'^\s+(.+?), ([\d.]+) g,', r.stdout, re.M)
        res[k] = dict(time=m.group(1).strip(), g=float(m.group(2))) if m else dict(time='?', g=0.0, err=(r.stdout + r.stderr)[-300:])
        print('  %-14s %s' % (k, res[k]))
    json.dump(res, open(SLICE, 'w'), indent=1)
    return res


# ---------------------------------------------------------------- the page
def enc_vf(V, F, label, group, role, color, note):
    import base64
    return dict(label=label, group=group, role=role, color=color, note=note, v=base64.b64encode(np.asarray(V, '<f4').tobytes()).decode(), f=base64.b64encode(np.asarray(F, '<u4').tobytes()).decode())


def enc_w(w, at, label, group, role, color, note, tol=0.05):
    V, F = PT.mesh_of(w, tol)
    return enc_vf(V + np.array([at[0], at[1], 0.0], '<f4'), F, label, group, role, color, note)


def enc_t(T, at, label, group, role, color, note, faces):
    T = np.array(T, float); T[:, :, 0] += at[0]; T[:, :, 1] += at[1]
    V, F = PB.mesh(T, faces)
    return enc_vf(V, F, label, group, role, color, note)


def page(T, C, E, pca, info):
    TRAY, CAP, PART, PLUGC = 0xe0b35c, 0x5fb3a1, 0x4a78b5, 0x3a3d43
    P = dict(floor=enc_w(floor(), (0, 0), 'Floor', 'floor', 'floor', 0xb9c4d0, 'Your 2.6 mm floor with %.1f holes every %.0f mm, the size you picked on the bench. These five are just lined up on it to inspect. This is not a layout.' % (HOLE, PITCH), tol=0.08))

    def holder(k, tray_note, cap_note, own_note):
        at = AT[k]
        P[k + '_tray'] = enc_w(T[k], at, NAMES[k] + ' tray', k, 'tray', TRAY, tray_note)
        same = abs(OWN[k] - BLOCK) < 0.01
        P[k + '_cap'] = enc_w(C[k]['block'], at, NAMES[k] + ' cap', k, 'cap_both' if same else 'cap_block', CAP, cap_note)
        if not same:
            P[k + '_cap_own'] = enc_w(C[k]['own'], at, NAMES[k] + ' cap, just over the part', k, 'cap_own', CAP, own_note)

    holder('esc', 'Frame v2 as you printed it, with four small catches added on the end walls. The opening is unchanged: 45.0 long, 24.5 across, walls 12 tall, solid ends. It needs a new print, because the frame you have has no catches.',
           'Snaps on from above. A collar comes %.0f mm down round the ESC\'s top, and two ribs reach down to touch it. Four legs on the end walls carry the hooks, so nothing crosses the long faces where your leads leave. The sides are open over the ESC.' % COLLAR,
           'The same cap with its plate right on the ESC, %.1f over the floor.' % OWN['esc'])
    P['esc_part'] = enc_w(esc_part()[0][2], AT['esc'], 'Your ESC', 'esc', 'part', PART, esc_part()[0][4])
    holder('pack', 'A wall round the pack, 15 tall, 0.25 clearance each side. Four pegs on two ears, 150 apart. The ears stop at the wall\'s height, so the pack\'s lead passes over them. Catches on the long walls.',
           'One cap: at %.0f it is the part that sets the block height. A collar round the pack\'s top edge, windows in the plate to save plastic, four legs on the long sides. A swap means unhooking four legs.' % BLOCK, '')
    P['pack_part'] = enc_w(pack_part()[0][2], AT['pack'], 'Your pack', 'pack', 'part', PART, pack_part()[0][4])
    holder('pi', 'A low frame, %.0f tall, so it stays under the port windows, with 0.25 clearance round your box. Four pegs. The box itself is unchanged.' % PI_H,
           'Your box already encloses the Pi, so this isn\'t a lid. Two straps hold the box down, one over each end, tied by a rail on the side away from the header. They clear the notch your plugs come through. At block height, feet reach down to the box\'s rim.',
           'The same straps resting right on the box\'s rim, %.1f over the floor.' % OWN['pi'])
    B = PB.stl(os.path.join(PRINT, 'pi_box_base_bored.stl')); B[:, :, 0] -= PI_DX; B[:, :, 1] -= PI_DY; B[:, :, 2] += FLOOR
    L = PB.lid_in_base(PB.stl(os.path.join(PRINT, 'pi_box_lid_over_header.stl'))); L[:, :, 0] -= PI_DX; L[:, :, 1] -= PI_DY; L[:, :, 2] += FLOOR
    P['pi_base'] = enc_t(B, AT['pi'], 'Your box: base', 'pi', 'part', 0xd9c39e, 'The rpi5 base with the rings bored, as your ring test proved. Not changed, and it needs no pegs of its own.', 24000)
    P['pi_lid'] = enc_t(L, AT['pi'], 'Your box: lid, notch over the pins', 'pi', 'part', 0xc9b48c, 'Your lid with the notch over the pins. Its clips hold it to the base.', 8000)
    pl, (x0, x1, y0, y1) = pi_plugs()
    P['pi_plugs'] = enc_w(pl, AT['pi'], 'Dupont plugs', 'pi', 'part', PLUGC, 'All 40 drawn. The top is your caliper, %.1f above the floor\'s top. That is %.1f through a ceiling at block height, before the wires bend.' % (PB.PLUG_TOP, PB.PLUG_TOP - BLOCK))
    holder('pca', 'A wall round the board with corner blocks for it to sit on, %.1f over the floor, because your model\'s pins reach 2.1 under the board. Notches in both end walls for the end headers. The two pegs sit on the long sides, so the end plugs have a clear way out.' % PCA_SHELF,
           'A plate on four columns. The columns press on the board\'s four corners, where nothing is mounted. The big window and the open sides leave room for plugs and wires.',
           'The same cap, as low as the plugs and wires allow: %.1f over the floor, using my guessed %.0f mm wire bend.' % (OWN['pca'], BEND))
    tris = []
    for s in pca:
        V, Fc = s.tessellate(0.15, 0.6)
        A = np.array([[v.x, v.y, v.z] for v in V]); tris.append(A[np.array(Fc)])
    P['pca_board'] = enc_t(np.vstack(tris), AT['pca'], 'Your PCA model', 'pca', 'part', 0x2f8a58, 'The generic PCA9685 model from your Downloads, board 62.2 x 25.7. It has an end header on one side only, and your wiring uses both, so the tray leaves room at both ends. Not calipered against your board.', 14000)
    for i, (p, n) in enumerate(zip(pca_plugs(), ('Plugs on channels 0 and 1', 'Plug on one end header', 'Plug on the other end header'))):
        P['pca_plug%d' % i] = enc_w(p, AT['pca'], n, 'pca', 'part', PLUGC, 'A guess: a %.0f mm Dupont housing or servo plug. Not measured.' % PLUG)
    holder('esp', 'A wall round the board with corner blocks %.1f over the floor. The USB end is open right down to the floor, so the cable plugs in. Two pegs on the long sides.' % ESP_SHELF,
           'The same style as the PCA: a plate on four columns pressing on the board\'s corners, past the ends of the pin rows.',
           'The same cap, as low as the plugs and wires allow: %.1f over the floor, using my guessed %.0f mm wire bend.' % (OWN['esp'], BEND))
    P['esp_board'] = enc_w(E['board'], AT['esp'], 'ESP32 board, upside down', 'esp', 'part', 0x2f8a58, 'No model of your board exists, so this is a typical 55 x 28 dev board. It is upside down, so your factory pins point up and the plugs go on from above. Your arduino_case print is 29 x 56 inside, so it would hold a board this size.')
    P['esp_under'] = enc_w(E['under'], AT['esp'], 'Module and USB, on its underside', 'esp', 'part', 0x1d6b45, 'A guess at the module and USB port, now hanging under the board. They set the %.1f shelf.' % ESP_SHELF)
    P['esp_pins'] = enc_w(E['pins'], AT['esp'], 'Pin rows', 'esp', 'part', 0xc9a227, 'A guess: 48 long, 25.4 apart.')
    P['esp_plugs'] = enc_w(E['plugs'], AT['esp'], 'Dupont plugs', 'esp', 'part', PLUGC, 'A guess: every pin plugged, the worst case.')

    def pr(k):
        return info.get(k) or {}
    def ans(*qa):
        return [dict(q=q, a=a) for q, a in qa]
    ceil_note = 'Until something presses on the cap, the holder stays in the floor by peg friction alone.'
    parts = dict(
        esc=dict(name='ESC', r=58, answers=ans(
            ('How does it get in?', 'Press it straight down into the tray, the same as the frame you have. Then the cap comes down and clicks on.'),
            ('Why this way?', 'The opening is the frame you said "fits fine enough". All I added are the catches on the end walls.'),
            ('What holds it upside down?', 'The cap holds the ESC in the tray, through four hooks. ' + ceil_note),
            ('Where do the wires go?', 'Out the finned face, between the tray wall and the collar: a %.0f mm tall gap. The cap\'s legs are on the ends, but they could foul your taped leads at that end.' % (ESC[2] - COLLAR - ESC_H))),
            guesses=[('ESC thickness', '24', 'Still your 24. I\'m waiting on the two heights: to the case and to the fin tops.'), ('Which way up', 'either', 'It fits both ways up. Wires can wedge differently each way, as you found.'), ('Leg spots', '8 each side of center', 'Picked to miss the ear. Check them against your taped leads.'), ('Ribs', '2 at 12 each side of center', 'Only at block height, to reach the ESC\'s top.')]),
        pack=dict(name='Pack', r=95, answers=ans(
            ('How does it get in?', 'Drop it straight into the tray with the lead end wherever you want it, then click the cap on. To swap: unhook four legs, lift the cap, lift the pack.'),
            ('Why this way?', 'On edge, as the sim has it. The walls are low because the ESC\'s 12 mm walls worked, and the collar holds the top edge.'),
            ('What holds it upside down?', 'The cap holds all 300 g through four hooks. This is the hardest test of the five. ' + ceil_note),
            ('Where do the wires go?', 'The lead leaves by a short end, over the ear. I\'m assuming that end and height; I haven\'t seen where your packs\' leads come out.')),
            guesses=[('Pack size', '141 x 26 x 45.7', 'From your model. Worth a caliper before printing: it sets the block height.'), ('Wall height', '15', 'Picked. The sim ran 23; the ESC\'s 12 worked.'), ('Lead position', 'a short end, mid height', 'Assumed. If it leaves low, the ear blocks it.'), ('Width with cap', '%.1f' % (2 * (PACK_B / 2 + WALL + N2)), 'Cap legs add %.2f a side. The side-by-side layouts will need rechecking.' % N2), ('Pegs', '4, 150 x 15', 'Picked. Four pegs have to line up at once, and they carry 300 g.')]),
        pi=dict(name='Pi', r=70, answers=ans(
            ('How does it get in?', 'Your box, closed as usual, drops into the low frame. The straps click on over its ends.'),
            ('Why this way?', 'You\'re right that the Pi doesn\'t need a new lid: its box already encloses it. It only has to be held to the floor, and the base can\'t take pegs cleanly, because it prints floor-down and its mesh won\'t union exactly.'),
            ('What holds it upside down?', 'The lid\'s clips hold the lid. The straps hold the box in the frame. ' + ceil_note),
            ('Where do the wires go?', 'Up through the lid\'s notch, between the straps. Your plugs stand %.1f over the floor, %.1f past block height, so a ceiling at %.0f needs a hole or a hump over the header.' % (PB.PLUG_TOP, PB.PLUG_TOP - BLOCK, BLOCK))),
            guesses=[('Frame height', '%.0f' % PI_H, 'Picked to stay under the port windows.'), ('Clearance', '0.25 a side', 'Tested on the ESC only, and your box is itself a print.'), ('Strap spots', '%.0f and %.0f from center' % (STRAPS[0][0], STRAPS[1][0]), 'Picked to miss the notch and your plugs. The legs miss the port windows, but one strap covers 2 side vents on each side, standing about 1 mm off them.'), ('Whole box', 'not printed', 'Only the ring test has been printed since the rings were bored.')]),
        pca=dict(name='PCA9685', r=55, answers=ans(
            ('How does it get in?', 'Lower the board onto the corner blocks with its end headers over the notches, plug it up, then click the cap on.'),
            ('Why this way?', 'Your old case is a 63.5 x 28 tray with walls, and print 1 taught us that loose fits rattle. So this is tighter, %.1f x %.1f inside. The cap can\'t be a flat lid close to the board, because your plugs stand on it.' % (PCA_A, PCA_B)),
            ('What holds it upside down?', 'Four columns press on the board\'s corners. ' + ceil_note),
            ('Where do the wires go?', 'Up and out through the window, or out the open sides. The end headers\' plugs go out through the notches.')),
            guesses=[('Board size', '62.2 x 25.7', 'From the generic model in your Downloads. Please caliper yours.'), ('Shelf', '%.1f' % PCA_SHELF, 'The model\'s pins reach 2.1 under the board.'), ('Plug height', '%.0f + %.1f seat' % (PLUG, PLUG_SEAT), 'A guess.'), ('Wire bend', '%.0f' % BEND, 'The same guess as the Pi box. Only matters for the lower cap.'), ('Columns', '3.5 square', 'Tall and thin at block height: about %.0f mm. They may wobble.' % (BLOCK - CAP_T - (PCA_TOP - FLOOR)))]),
        esp=dict(name='ESP32', r=52, answers=ans(
            ('How does it get in?', 'Upside down, pins up. Lower it onto the corner blocks with the USB end at the open end, plug it up, then click the cap on.'),
            ('Why this way?', 'Your factory pins point away from the components. Upside down, the plugs go on from above, instead of needing room under the board.'),
            ('What holds it upside down?', 'Four columns press on the board\'s corners. ' + ceil_note),
            ('Where do the wires go?', 'Up through the window, or out the sides between the legs. USB at the open end.')),
            guesses=[('Board size', '55 x 28', 'Typical, not yours. I need a caliper, or the board\'s model if you have one.'), ('Upside down', 'pins up', 'My pick, so the plugs go on from above. Your call.'), ('Shelf', '%.1f' % ESP_SHELF, 'Room for the module and USB, both guessed.'), ('Pin rows', '48 long, 25.4 apart', 'Typical. The columns have to land past their ends.'), ('Your old case', 'unconfirmed', 'arduino_case.gcode is 29 x 56 inside with its own lid. I read it from the G-code. Is it the ESP32\'s?')]))
    common = [('Block height', '%.0f' % BLOCK, 'The pack\'s 45.7, plus 0.3 of air and a 2.0 plate. Over the floor\'s top.'), ('The snap', '%.2f hook, %.1f leg' % (HOOK_DEPTH, LEG_T), 'Untested. Nothing here has been printed. Bending strain stays under my 1 %% limit, which is itself a guess for PLA bent across its layers.' % ()),
              ('Play under the cap', '%.2f' % (CAP_GAP + CATCH_GAP), 'Air over the part plus at the hook. A TPU pad could take it up.'), ('Walls', '%.1f' % WALL, 'From your ESC frame. Unproven at the pack\'s weight.'), ('Clearance', '%.2f a side' % FIT, 'Tested only on the ESC\'s thickness.'), ('Pegs', '5 x %.1f in %.1f holes' % (PT.PEG_LONG, HOLE), 'Your bench, on a 2.6 floor. Pull-out is untested.')]
    for k, d in parts.items():
        d['guesses'] = [dict(name=n, value=v, why=w) for n, v, w in d['guesses']]
        d['center'] = [AT[k][0], AT[k][1], BLOCK / 2]
        d['own'] = OWN[k]; d['same'] = abs(OWN[k] - BLOCK) < 0.01
        d['print'] = dict(tray=pr(k + '_tray'), cap=pr(k + '_cap'), own=pr(k + '_cap_own'))
    meta = dict(order=['esc', 'pack', 'pi', 'pca', 'esp'], parts=parts, common=[dict(name=n, value=v, why=w) for n, v, w in common], block=BLOCK, floor=FLOOR, floor_x=FLOOR_X, floor_y=FLOOR_Y,
                info=info, n2=N2, all=dict(name='All five', r=165, center=[0, 18, BLOCK / 2]))
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', 'window.PARTS=' + json.dumps(P) + ';window.META=' + json.dumps(meta) + ';')
    p = os.path.join(config.TWIN_OUT, 'holders_view.html')
    open(p, 'w', encoding='utf-8').write(html)
    print('wrote %s (%.1f MB)' % (p, len(html) / 1e6))


if __name__ == '__main__':
    if 'page' in sys.argv[1:]:                  # only the page, for working on the viewer: no checks, no STLs
        T = {k: BUILD[k][0]() for k in BUILD}
        C = {k: {m: BUILD[k][1](h) for m, h in (('block', BLOCK), ('own', OWN[k]))} for k in BUILD}
        page(T, C, esp_model(), pca_board(), json.load(open(SLICE)) if os.path.exists(SLICE) else {})
        sys.exit(0)
    good, T, C, E, pca = check()
    print('Print pieces (trays and caps upside down, so pegs and legs point up):')
    os.makedirs(PRINT, exist_ok=True)
    paths = {}
    for k, w in pieces(T, C).items():
        f = flip(w)
        p = os.path.join(PRINT, 'holder_%s.stl' % k)
        write_stl(f.val().wrapped, p, lin=0.02, ang=0.2)
        h_ok, msg = health(p); good &= bool(h_ok)
        bb = f.val().BoundingBox()
        print('  %-14s %5.1f x %5.1f x %5.1f  %s %s' % (k, bb.xlen, bb.ylen, bb.zlen, 'ok ' if h_ok else 'BAD', msg))
        paths[k] = p
    if 'slice' in sys.argv[1:]:
        print('Slices, draft, not sent to the printer:')
        slice_all(paths)
    info = json.load(open(SLICE)) if os.path.exists(SLICE) else {}
    print('Own heights:', {k: round(v, 1) for k, v in OWN.items()}, 'block', BLOCK)
    if os.path.exists(TEMPLATE):
        page(T, C, E, pca, info)
    print('checks:', 'all pass' if good else 'SOMETHING FAILED')
    sys.exit(0 if good else 1)
