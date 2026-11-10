"""SUPERSEDED 2026-11-08 by part_boxes.py, before anything was printed. Zach: "kinda flimsy looking", and "the spacers on the pca are way too tall". Kept for the record.

The holders as stacking bricks (2026-11-08). Supersedes holders.py's caps.

Zach, on the caps: "set the section heigh much smaller the battery should be multiple boxes high. they should be peg boards on the top of these
to allow stacking. the top should not be a plat with legs but a few blocks on top of things. think like a lego block kinda. there can be spacer
legos placed on top essentially".

    python twin/bricks.py          # builds, checks with controls, STLs in twin/out/print/, twin/out/bricks_view.html ("Part Holders")
    python twin/bricks.py slice    # the same, and slices every brick (draft, not printed) into twin/out/bricks_slice.json
    python twin/bricks.py page     # only the page

One joint everywhere: a 5 mm peg under a brick goes into a 5.1 hole, in the floor or in the top of the brick below. Every height is a whole number
of sections, or a half.

  tray     walls round the part, posts with pegs under them and sockets on top. Part-specific
  spacer   one peg, one socket, 8 x 8. The same for every part
  top      a block across the part, pegged to the columns on both sides, with sockets along its top. It lands on the part. Part-specific

Frame: x along the part, y across it, z up from the floor's underside (the floor's top at FLOOR). Built at the origin, placed by AT, which puts every
peg on one 15 mm grid. AT is a line-up for inspecting, not a layout. * = picked, for Zach to OK or measure.
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
from peg_test import rect, cyl, vol, FLOOR, PITCH, PEG
import pi_box as PB

PRINT = os.path.join(config.TWIN_OUT, 'print')
TEMPLATE = os.path.join(HERE, 'bricks_view_template.html')
PCA_STEP = os.path.join(config.REPO, 'reference', 'downloads', 'pca9685', 'generic.step')
SLICE = os.path.join(config.TWIN_OUT, 'bricks_slice.json')

U = 12.0                          # * one section: 3 for the ESC (36 over its 34), 4 for the pack (48 over its 45.7), and the wall of the frame he OKed
HALF = U / 2
HOLE = PT.HOLE_PICK               # his bench: 5.1 for a 5 mm peg, in a 2.6 floor
PEG_LONG, TIP = PT.PEG_LONG, PT.TIP   # the floor's 2.4 peg, so any brick goes in the floor or in another brick
DEPTH = 2.8                       # * a socket's depth
MOUTH = 0.3                       # * a chamfer at a socket's mouth: bricks print top down, where the first layer squashes in
POST = 8.0                        # * a brick's width at a peg: 1.45 of wall round a socket
WALL = 1.2                        # frame v2's
FIT = 0.25                        # * a side, tested only on the ESC's thickness
LEAD = 0.6                        # frame v2's mouth chamfer
GAP = 0.3                         # * air between a top block and the part it holds
LIP = 3.0                         # * how far a top block's lips come down the part's sides
CEILING = 5 * U                   # 60: where the stacks can all meet. Change it with a layer of spacers
KIT = (3 * U, 2 * U, U, HALF)     # the spacers

ESC = PT.ESC                      # his caliper
PACK = (141.0, 26.0, 45.7)        # his model's box, on edge. Not calipered
PI_BOX = (98.5, 65.6, PB.RIM)     # the box's outside
PCA = (62.2, 25.7, 1.6)           # his PCA model; not calipered
PCA_SHELF = 3.2                   # * the board's underside over the floor: his model's pins reach 2.1 under it
ESP = (55.0, 28.0, 1.6)           # * a typical dev board. His arduino_case print is 29 x 56 inside
ESP_SHELF = 4.4                   # * upside down: room for the module and USB under it; the board's top lands level with the tray's
PLUG, PLUG_SEAT, BEND = 14.0, 2.5, 15.0   # * a Dupont housing, the header's plastic under it, room for wires to turn over
AT = dict(esc=(-90.0, -45.0), pack=(0.0, 97.5), pi=(0.0, 30.0), pca=(0.0, -52.5), esp=(90.0, -52.5))
FLOOR_X, FLOOR_Y = (-130.0, 130.0), (-85.0, 120.0)
NAMES = dict(esc='ESC', pack='Pack', pi='Pi', pca='PCA9685', esp='ESP32')


def W(s):
    return cq.Workplane('XY').newObject([s])


def shift(w, x=0.0, y=0.0, z=0.0):
    return w.translate((x, y, z))


def peg_at(x, y, z):
    """a peg under a brick whose underside is at z: it overruns 0.5 up into the brick"""
    return cyl(PEG, z - PEG_LONG, z + 0.5, x, y).faces('<Z').chamfer(TIP)


def socket(F, x, y, z):
    """a blind socket in a brick's top at z, its mouth chamfered"""
    F = F.cut(cyl(HOLE, z - DEPTH, z + 1.0, x, y))
    return F.cut(W(cq.Solid.makeCone(HOLE / 2, HOLE / 2 + MOUTH + 0.02, MOUTH + 0.02, cq.Vector(x, y, z - MOUTH), cq.Vector(0, 0, 1))))


def spacer(h, x=0.0, y=0.0, z=FLOOR):
    F = rect(x - POST / 2, x + POST / 2, y - POST / 2, y + POST / 2, z, z + h).union(peg_at(x, y, z))
    return socket(F, x, y, z + h)


def tray(a, b, h, pegs, ears=(), notches=(), corners=None):
    """walls and posts, all h tall so the whole top prints on the bed. The opening goes through last; then the posts' pegs and sockets"""
    z0, z1 = FLOOR, FLOOR + h
    F = rect(-a / 2 - WALL, a / 2 + WALL, -b / 2 - WALL, b / 2 + WALL, z0, z1)
    for x0, x1, y0, y1 in ears:
        F = F.union(rect(x0, x1, y0, y1, z0, z1))
    for x, y in pegs:
        F = F.union(rect(x - POST / 2, x + POST / 2, y - POST / 2, y + POST / 2, z0, z1))
    F = F.cut(rect(-a / 2, a / 2, -b / 2, b / 2, z0 - 1, z1 + 1))
    F = F.cut(cq.Workplane('XY').workplane(offset=z1 - LEAD).rect(a, b).workplane(offset=LEAD + 0.01).rect(a + 2 * LEAD + 0.02, b + 2 * LEAD + 0.02).loft())
    for s, hw, z in notches:
        F = F.cut(rect(*sorted((s * (a / 2 - 0.5), s * (a / 2 + WALL + 0.5))), -hw, hw, z, z1 + 1))
    if corners:
        dx, dy, zs = corners
        for sx in (-1, 1):
            for sy in (-1, 1):
                F = F.union(rect(*sorted((sx * (a / 2 + 0.2), sx * (a / 2 - dx))), *sorted((sy * (b / 2 + 0.2), sy * (b / 2 - dy))), z0, z0 + zs))
    for x, y in pegs:
        F = F.union(peg_at(x, y, z0))
        F = socket(F, x, y, z1)
    return F


def pegged(F, pegs, sockets, z0, z1):
    for x, y in pegs:
        F = F.union(peg_at(x, y, z0))
    for x, y in sockets:
        F = socket(F, x, y, z1)
    return F


def column(x, y, z0, z1):
    """spacers from z0 up to z1, the biggest first: [(height, its underside)]"""
    out, z = [], z0
    while z1 - z > 0.01:
        h = next(k for k in KIT if k <= z1 - z + 0.01)
        out.append((h, z)); z += h
    return out


# ---------------------------------------------------------------- the ESC: 1 section of tray, 2 of spacers, a half for the top block
ESC_A, ESC_B = ESC[0], ESC[1] + 2 * FIT                     # frame v2's opening: 45.0 with no clearance (his press fit), 0.25 a side across
ESC_PEGS = [(-30.0, 0.0), (30.0, 0.0)]
ESC_SPACE = 2 * U


def esc_tray():
    ears = [(-30.0, -ESC_A / 2 - WALL + 0.2, -POST / 2, POST / 2), (ESC_A / 2 + WALL - 0.2, 30.0, -POST / 2, POST / 2)]
    return tray(ESC_A, ESC_B, U, ESC_PEGS, ears)


def esc_top():
    z0, z1, pt = FLOOR + U + ESC_SPACE, FLOOR + U + ESC_SPACE + HALF, FLOOR + ESC[2]
    F = rect(-34.0, 34.0, -POST / 2, POST / 2, z0, z1).union(rect(-14.0, 14.0, -ESC_B / 2 - WALL, ESC_B / 2 + WALL, z0, z1))
    F = F.union(rect(-14.0, 14.0, -ESC_B / 2, ESC_B / 2, pt + GAP, z0 + 0.5))     # the pad down to the ESC's top
    for s in (-1, 1):
        F = F.union(rect(-14.0, 14.0, *sorted((s * ESC_B / 2, s * (ESC_B / 2 + WALL))), pt - LIP, z0 + 0.5))
    return pegged(F, ESC_PEGS, [(x, 0.0) for x in np.arange(-30.0, 31.0, PITCH)], z0, z1)


# ---------------------------------------------------------------- the pack: 1 section of tray, 3 of spacers, a half for the top block
PACK_A, PACK_B = PACK[0] + 2 * FIT, PACK[1] + 2 * FIT
PACK_PEGS = [(s, t) for s in (-75.0, 75.0) for t in (-7.5, 7.5)]
PACK_SPACE = 3 * U


def pack_tray():
    return tray(PACK_A, PACK_B, U, PACK_PEGS)


def pack_top():
    z0, z1, pt = FLOOR + U + PACK_SPACE, FLOOR + U + PACK_SPACE + HALF, FLOOR + PACK[2]
    F = rect(-79.0, 79.0, -11.5, -3.5, z0, z1).union(rect(-79.0, 79.0, 3.5, 11.5, z0, z1))
    for x in (-50.0, 0.0, 50.0):                                          # * three ties, each with a pad and lips round the pack's top
        F = F.union(rect(x - 6.0, x + 6.0, -PACK_B / 2 - WALL, PACK_B / 2 + WALL, z0, z1))
        F = F.union(rect(x - 6.0, x + 6.0, -PACK_B / 2, PACK_B / 2, pt + GAP, z0 + 0.5))
        for s in (-1, 1):
            F = F.union(rect(x - 6.0, x + 6.0, *sorted((s * PACK_B / 2, s * (PACK_B / 2 + WALL))), pt - LIP, z0 + 0.5))
    return pegged(F, PACK_PEGS, [(x, y) for x in np.arange(-75.0, 76.0, PITCH) for y in (-7.5, 7.5)], z0, z1)


# ---------------------------------------------------------------- the Pi: its box stays. A half section of frame, 3 of spacers, two bars over it
PI_A, PI_B = PI_BOX[0] + 2 * FIT, PI_BOX[1] + 2 * FIT
PI_PEGS = [(s, t) for s in (-60.0, 60.0) for t in (-15.0, 15.0)]
PI_SPACE = 3 * U
PI_DX, PI_DY = PI_BOX[0] / 2, PI_BOX[1] / 2


def pi_tray():
    x = PI_A / 2 + WALL - 0.2
    ears = [(-60.0, -x, -15.0 - POST / 2, -15.0 + POST / 2), (-60.0, -x, 15.0 - POST / 2, 15.0 + POST / 2), (x, 60.0, -15.0 - POST / 2, -15.0 + POST / 2), (x, 60.0, 15.0 - POST / 2, 15.0 + POST / 2)]
    return tray(PI_A, PI_B, HALF, PI_PEGS, ears)


def pi_bar(y=15.0):
    z0, z1, rim = FLOOR + HALF + PI_SPACE, FLOOR + HALF + PI_SPACE + HALF, FLOOR + PI_BOX[2]
    F = rect(-64.0, 64.0, y - POST / 2, y + POST / 2, z0, z1)
    for s in (-1, 1):                                                     # feet down onto the box's rim
        F = F.union(rect(*sorted((s * 45.75, s * 49.25)), y - POST / 2, y + POST / 2, rim + GAP, z0 + 0.5))
    return pegged(F, [(-60.0, y), (60.0, y)], [(x, y) for x in np.arange(-60.0, 61.0, PITCH)], z0, z1)


def pi_plugs():
    x0, x1 = PB.HDR_X[0] - PI_DX, PB.HDR_X[1] - PI_DX
    y0, y1 = PB.HDR_Y[0] - PI_DY, PB.HDR_Y[1] - PI_DY
    return rect(x0, x1, y0, y1, FLOOR + PB.PLUG_TOP - PB.HOUSING, FLOOR + PB.PLUG_TOP)


def pi_box_solid():
    """the box's outside, for the checks: its real mesh isn't a valid exact solid (pi_box.py), and this outline is the widest it gets"""
    return rect(-PI_BOX[0] / 2, PI_BOX[0] / 2, -PI_BOX[1] / 2, PI_BOX[1] / 2, FLOOR, FLOOR + PI_BOX[2])


# ---------------------------------------------------------------- the boards: a half section of tray, a half of spacers, a block across each end
BOARD_PEGS = [(s, t) for s in (-30.0, 30.0) for t in (-22.5, 22.5)]
PCA_A, PCA_B = PCA[0] + 2 * FIT, PCA[1] + 2 * FIT
PCA_TOP = FLOOR + PCA_SHELF + PCA[2]
ESP_A, ESP_B = ESP[0] + 2 * FIT, ESP[1] + 2 * FIT
ESP_TOP = FLOOR + ESP_SHELF + ESP[2]


def board_ears(b):
    y = b / 2 + WALL - 0.2
    return [(26.0, 26.0 + POST, y, 22.5), (26.0, 26.0 + POST, -22.5, -y), (-26.0 - POST, -26.0, y, 22.5), (-26.0 - POST, -26.0, -22.5, -y)]


def pca_tray():
    return tray(PCA_A, PCA_B, HALF, BOARD_PEGS, board_ears(PCA_B), notches=[(-1, 8.5, PCA_TOP - 0.2), (1, 8.5, PCA_TOP - 0.2)], corners=(4.0, 4.5, PCA_SHELF))


def board_block(s, x_in, nubs, nw, nd, board_top):
    """a block across one end of the board, on two columns. Nubs reach down to the board's corners, past whatever stands on it"""
    z0, z1 = FLOOR + HALF + HALF, FLOOR + HALF + HALF + HALF
    F = rect(*sorted((s * x_in, s * 34.0)), -26.5, 26.5, z0, z1)
    for x, y in nubs:
        F = F.union(rect(s * x - nw / 2, s * x + nw / 2, y - nd / 2, y + nd / 2, board_top + 0.1, z0 + 0.5))
    return pegged(F, [(s * 30.0, -22.5), (s * 30.0, 22.5)], [(s * 30.0, y) for y in (-22.5, -7.5, 7.5, 22.5)], z0, z1)


def pca_block(s=1):
    return board_block(s, 26.0, [(28.6, -10.6), (28.6, 10.6)], 3.5, 3.5, PCA_TOP)


def esp_tray():
    return tray(ESP_A, ESP_B, HALF, BOARD_PEGS, board_ears(ESP_B), notches=[(1, 6.5, FLOOR - 1.0)], corners=(3.0, 5.0, ESP_SHELF))


def esp_block(s=1):
    return board_block(s, 24.4, [(25.95, -9.0), (25.95, 9.0)], 3.1, 3.5, ESP_TOP)


def pca_board():
    w = cq.importers.importStep(PCA_STEP)
    return [s.moved(cq.Location(cq.Vector(0, 0, FLOOR + PCA_SHELF + 0.8))) for s in w.solids().vals()]


def pca_plugs():
    """* channels 0 and 1, and the Dupont plugs off both end headers: the model has the header on one end, his wiring uses both"""
    return [rect(-25.4, -20.3, -12.7, -5.1, PCA_TOP + PLUG_SEAT, PCA_TOP + PLUG_SEAT + PLUG),
            rect(-47.1, -34.2, -7.6, 7.6, PCA_TOP, PCA_TOP + PLUG_SEAT), rect(34.2, 47.1, -7.6, 7.6, PCA_TOP, PCA_TOP + PLUG_SEAT)]


def esp_model():
    """* no model of his board exists. Upside down, so its factory pins point up and the plugs go on from above"""
    z0 = FLOOR + ESP_SHELF
    return dict(board=rect(-ESP[0] / 2, ESP[0] / 2, -ESP[1] / 2, ESP[1] / 2, z0, z0 + ESP[2]),
                under=rect(-24.5, -7.0, -9.0, 9.0, z0 - 3.2, z0).union(rect(23.0, 28.5, -4.0, 4.0, z0 - 3.0, z0)),
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


# ---------------------------------------------------------------- every holder, assembled
def assemble():
    """for each part: its tray, spacer columns (spec), top block(s), and where the top is"""
    A = {}
    A['esc'] = dict(tray=esc_tray(), cols=[(x, y, U, ESC_SPACE) for x, y in ESC_PEGS], top=[esc_top()], top_z=U + ESC_SPACE + HALF)
    A['pack'] = dict(tray=pack_tray(), cols=[(x, y, U, PACK_SPACE) for x, y in PACK_PEGS], top=[pack_top()], top_z=U + PACK_SPACE + HALF)
    A['pi'] = dict(tray=pi_tray(), cols=[(x, y, HALF, PI_SPACE) for x, y in PI_PEGS], top=[pi_bar(15.0), pi_bar(-15.0)], top_z=HALF + PI_SPACE + HALF)
    A['pca'] = dict(tray=pca_tray(), cols=[(x, y, HALF, HALF) for x, y in BOARD_PEGS], top=[pca_block(1), pca_block(-1)], top_z=3 * HALF)
    A['esp'] = dict(tray=esp_tray(), cols=[(x, y, HALF, HALF) for x, y in BOARD_PEGS], top=[esp_block(1), esp_block(-1)], top_z=3 * HALF)
    for k, d in A.items():
        d['spacers'] = many(spacer(h, x, y, FLOOR + z) for x, y, z, h in d['cols'])
    return A


CEIL_COLS = dict(esc=ESC_PEGS, pack=PACK_PEGS, pi=PI_PEGS, pca=BOARD_PEGS, esp=BOARD_PEGS)
STACK_Z = 3 * HALF + 2 * U                                                # the ESP32's tray, on 2-section spacers on the PCA's blocks: 42


def check():
    ok = True

    def line(what, good, got=''):
        nonlocal ok
        ok &= bool(good)
        print('  %-70s %s %s' % (what, got, 'ok' if good else 'WRONG'))

    A = assemble(); E = esp_model(); pca = pca_board(); Fl = floor()
    solid = dict(esc=rect(-ESC[0] / 2, ESC[0] / 2, -ESC[1] / 2, ESC[1] / 2, FLOOR, FLOOR + ESC[2]), pack=rect(-PACK[0] / 2, PACK[0] / 2, -PACK[1] / 2, PACK[1] / 2, FLOOR, FLOOR + PACK[2]), pi=pi_box_solid(),
                 pca=rect(-PCA[0] / 2, PCA[0] / 2, -PCA[1] / 2, PCA[1] / 2, FLOOR + PCA_SHELF, PCA_TOP), esp=E['board'])
    for k, d in A.items():
        print(NAMES[k] + ':')
        T, S, Tp = d['tray'], d['spacers'], many(d['top'])
        v = vol(Fl, shift(T, *AT[k])); line('tray in the floor, pegs in the %.1f holes' % HOLE, v < 1e-3, '%.3f mm3' % v)
        v = vol(Fl, shift(T, AT[k][0] + PITCH / 3, AT[k][1])); line('control: 5 mm off its holes', v > 1, '%.2f mm3' % v)
        v = vol(T, solid[k]); line('part in the tray', v < 1e-3, '%.3f mm3' % v)
        bad = [z for z in (5.0, 15.0, 40.0) if vol(T, shift(solid[k], z=z)) > 1e-3]
        line('part lifts straight out of the tray: 5, 15, 40 mm', not bad, '%s' % (bad or ''))
        v = vol(T, S); line('spacers on the tray, pegs in the sockets', v < 1e-3, '%.3f mm3' % v)
        v = vol(shift(S, x=2.0), T); line('control: spacers 2 mm off their sockets', v > 1, '%.2f mm3' % v)
        v = vol(S, solid[k]); line('spacers clear the part', v < 1e-3, '%.3f mm3' % v)
        v = vol(S, Tp); line('top block on the spacers, pegs in the sockets', v < 1e-3, '%.3f mm3' % v)
        v = vol(Tp, solid[k]); line('top block over the part', v < 1e-3, '%.3f mm3' % v)
        v = vol(Tp, T); line('top block clear of the tray', v < 1e-3, '%.3f mm3' % v)
        bad = [z for z in (5.0, 15.0, 40.0) if vol(shift(Tp, z=z), S) > 1e-3]
        line('top block lifts straight off: 5, 15, 40 mm', not bad, '%s' % (bad or ''))
        v = vol(shift(solid[k], z=1.0), Tp); line('with it on, the part pulled up 1 mm hits it: the part is held', v > 0.5, '%.2f mm3' % v)
        line('top lands on a whole or half section: %.0f' % d['top_z'], abs(d['top_z'] / HALF - round(d['top_z'] / HALF)) < 1e-6)
    print('The stack, ESP32 on the PCA:')
    a = A['pca']; b = A['esp']
    mid = many(spacer(2 * U, x, y, FLOOR + 3 * HALF) for x, y in BOARD_PEGS)
    up = lambda w: shift(w, z=STACK_Z)
    v = vol(mid, many(a['top'])); line('2-section spacers on the PCA\'s blocks', v < 1e-3, '%.3f mm3' % v)
    v = vol(up(b['tray']), mid); line('the ESP32\'s tray on those spacers', v < 1e-3, '%.3f mm3' % v)
    pl = many(pca_plugs())
    v = vol(up(b['tray']), pl); line('its tray clears the PCA\'s plugs', v < 1e-3, '%.3f mm3' % v)
    v = vol(up(E['under']), pl); line('the ESP32\'s module clears them', v < 1e-3, '%.3f mm3' % v)
    print('  room over the PCA\'s plugs under the ESP32: %.1f mm, with a guessed %.0f needed for wires to bend' % (FLOOR + STACK_Z + ESP_SHELF - 3.2 - (PCA_TOP + PLUG_SEAT + PLUG), BEND))
    line('its top lands on the ceiling: %.0f' % (STACK_Z + 3 * HALF), abs(STACK_Z + 3 * HALF - CEILING) < 1e-6)
    print('Hardware, with controls:')
    T = many(A['pi']['top'])
    v = vol(T, pi_plugs()); line('Pi bars clear the Dupont plugs', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(T, y=9.0), pi_plugs()); line('control: the bars 9 mm over, onto the header', v > 1, '%.2f mm3' % v)
    v = vol(A['pi']['tray'], rect(-49.6, 49.6, -33.2, 33.2, FLOOR, FLOOR + 5)); line('control: a Pi box 0.7 bigger each way', v > 1, '%.2f mm3' % v)
    tot = dict(tray=0.0, spacers=0.0, top=0.0); worst = None
    bl = many(A['pca']['top'])
    for s in pca:
        for key, w in (('tray', A['pca']['tray']), ('spacers', A['pca']['spacers']), ('top', bl)):
            v = vol(w, W(s))
            tot[key] += v
            if v > 1e-3:
                b_ = s.BoundingBox(); worst = (key, round(b_.xmin, 1), round(b_.xmax, 1), round(b_.ymin, 1), round(b_.ymax, 1), round(b_.zmin, 1), round(b_.zmax, 1), round(v, 2))
    line('your PCA model (310 solids) against the tray, spacers and blocks', max(tot.values()) < 1e-3, '%.3f mm3' % max(tot.values()))
    if worst:
        print('    located:', worst)
    v = vol(shift(bl, z=-1.0), solid['pca']); line('control: the blocks 1 mm lower press into the board', v > 1, '%.2f mm3' % v)
    for i, p in enumerate(pca_plugs()):
        for key, w in (('tray', A['pca']['tray']), ('spacers', A['pca']['spacers']), ('blocks', bl)):
            v = vol(w, p)
            if v > 1e-3:
                line('PCA plug %d against the %s' % (i, key), False, '%.3f mm3' % v)
    print('  %-70s %s' % ('PCA plugs clear the tray, spacers and blocks', 'checked'))
    bl = many(A['esp']['top'])
    for nm in E:
        for key, w in (('tray', A['esp']['tray']), ('spacers', A['esp']['spacers']), ('blocks', bl)):
            v = vol(w, E[nm])
            if v > 1e-3:
                line('ESP32 %s against the %s' % (nm, key), False, '%.3f mm3' % v)
    print('  %-70s %s' % ('ESP32 board, module, pins and plugs clear the tray, spacers, blocks', 'checked'))
    v = vol(shift(bl, x=-3.0), E['plugs']); line('control: a block 3 mm in, onto the pin rows', v > 1, '%.2f mm3' % v)
    v = vol(A['esc']['tray'], rect(-23.0, 23.0, -12.0, 12.0, FLOOR, FLOOR + 34)); line('control: an ESC 1 mm longer', v > 1, '%.2f mm3' % v)
    sp = spacer(U)
    v = vol(sp, shift(sp, z=U)); line('a spacer on a spacer', v < 1e-3, '%.3f mm3' % v)
    v = vol(rect(*FLOOR_X, *FLOOR_Y, 0, FLOOR).faces('>Z').workplane(origin=(0, 0, FLOOR)).pushPoints([(0.0, 0.0)]).hole(HOLE), sp); line('a spacer in the floor', v < 1e-3, '%.3f mm3' % v)
    print('Tops, before spacers to the ceiling at %.0f:' % CEILING, {k: d['top_z'] for k, d in A.items()})
    return ok, A, E, pca, mid


def flip(w):
    f = w.rotate((0, 0, 0), (1, 0, 0), 180)
    return f.translate((0, 0, -f.val().BoundingBox().zmin))


def pieces(A):
    """each different brick once, and how many one robot's set needs"""
    out = {}
    out['esc_tray'] = (A['esc']['tray'], 2); out['esc_top'] = (A['esc']['top'][0], 2)
    out['pack_tray'] = (A['pack']['tray'], 2); out['pack_top'] = (A['pack']['top'][0], 2)
    out['pi_frame'] = (A['pi']['tray'], 1); out['pi_bar'] = (A['pi']['top'][0], 2)
    out['pca_tray'] = (A['pca']['tray'], 1); out['pca_block'] = (A['pca']['top'][0], 2)
    out['esp_tray'] = (A['esp']['tray'], 1); out['esp_block'] = (A['esp']['top'][0], 2)
    for n, h, q in (('half', HALF, 8), ('one', U, 0), ('two', 2 * U, 4 + 4), ('three', 3 * U, 8 + 4)):
        out['spacer_' + n] = (spacer(h), q)
    return out


def slice_all(paths):
    res = {}
    for k, p in paths.items():
        r = subprocess.run([sys.executable, os.path.join(config.REPO, 'tools', 'orca.py'), p, '--draft', '--set', 'brim_type=outer_only', '--set', 'brim_width=5',
                            '--set', 'enable_support=0', '--name', 'brick_' + k], capture_output=True, text=True)
        m = re.search(r'^\s+(.+?), ([\d.]+) g,', r.stdout, re.M)
        res[k] = dict(time=m.group(1).strip(), g=float(m.group(2))) if m else dict(time='?', g=0.0, err=(r.stdout + r.stderr)[-300:])
        print('  %-14s %s' % (k, res[k]))
    json.dump(res, open(SLICE, 'w'), indent=1)
    return res


# ---------------------------------------------------------------- the page
def enc_vf(V, F, label, group, role, layer, color, note, single=False):
    import base64
    return dict(label=label, group=group, role=role, layer=layer, color=color, note=note, single=single, v=base64.b64encode(np.asarray(V, '<f4').tobytes()).decode(), f=base64.b64encode(np.asarray(F, '<u4').tobytes()).decode())


def enc_w(w, at, label, group, role, layer, color, note, tol=0.05, z=0.0, single=False):
    V, F = PT.mesh_of(w, tol)
    return enc_vf(V + np.array([at[0], at[1], z], '<f4'), F, label, group, role, layer, color, note, single)


def enc_t(T, at, label, group, role, layer, color, note, faces):
    T = np.array(T, float); T[:, :, 0] += at[0]; T[:, :, 1] += at[1]
    V, F = PB.mesh(T, faces)
    return enc_vf(V, F, label, group, role, layer, color, note)


def page(A, E, pca, mid, info):
    TRAY, SPACE, TOP, PART, PLUGC, CEIL = 0xe0b35c, 0xc9825b, 0x5fb3a1, 0x4a78b5, 0x3a3d43, 0x8f8fd6
    P = dict(floor=enc_w(floor(), (0, 0), 'Floor', 'floor', 'floor', 0, 0xb9c4d0, 'Your 2.6 mm floor with %.1f holes every %.0f mm, the size you picked on the bench. These are just lined up on it to inspect. This is not a layout.' % (HOLE, PITCH), tol=0.08))

    def holder(k, tray_note, sp_note, top_note, top_label, ceil_note):
        d, at = A[k], AT[k]
        P[k + '_tray'] = enc_w(d['tray'], at, NAMES[k] + ' tray', k, 'tray', 1, TRAY, tray_note)
        P[k + '_spacers'] = enc_w(d['spacers'], at, 'Spacers', k, 'spacer', 3, SPACE, sp_note)
        P[k + '_top'] = enc_w(many(d['top']), at, top_label, k, 'top', 4, TOP, top_note)
        cols = [spacer(h, x, y, FLOOR + z) for x, y in CEIL_COLS[k] for h, z in column(x, y, d['top_z'], CEILING)]
        if cols:
            P[k + '_ceil'] = enc_w(many(cols), at, 'Spacers up to the ceiling', k, 'ceil', 5, CEIL, ceil_note, single=k in ('pca', 'esp'))

    holder('esc', 'Frame v2\'s opening, unchanged: 45.0 long, 24.5 across, one section tall (12). The posts are now 8 mm square with a socket on top, so your printed frame can\'t take spacers.',
           'Two 2-section spacers (24), one on each post. The same brick as every other spacer.',
           'Pegs onto the two columns. A wider middle lands on the ESC\'s top, with lips coming %.0f mm down its long faces. The rest stays open. Sockets along the top take the next brick.' % LIP, 'ESC top block',
           'A section and a half more to meet a ceiling at %.0f.' % CEILING)
    P['esc_part'] = enc_w(rect(-ESC[0] / 2, ESC[0] / 2, -ESC[1] / 2, ESC[1] / 2, FLOOR, FLOOR + ESC[2]), AT['esc'], 'Your ESC', 'esc', 'part', 2, PART, 'Your caliper: 45 long, 34 wide, 24 tall, stood on edge. A plain box with no wires. You don\'t print this one.')
    holder('pack', 'A one-section tray (12), 0.25 clearance each side, with four posts at the ends. The two at each end leave a 7 mm gate for the lead.',
           'Four 3-section spacers (36). So the pack stands four sections tall, plus its top block.',
           'Two long bars with sockets all along them: a pegboard, 11 x 2. Three ties cross them, each with a pad on the pack\'s top and lips down its long faces. To swap a pack, pull this off and lift the pack out.', 'Pack top block',
           'A half section more to meet a ceiling at %.0f.' % CEILING)
    P['pack_part'] = enc_w(rect(-PACK[0] / 2, PACK[0] / 2, -PACK[1] / 2, PACK[1] / 2, FLOOR, FLOOR + PACK[2]), AT['pack'], 'Your pack', 'pack', 'part', 2, PART, 'Zeee 2S 5200 on edge, 141 x 26 x 45.7, from your model\'s box. Not calipered. You don\'t print this one.')
    holder('pi', 'A half-section frame (6), so it stays under the port windows, with 0.25 clearance round your box. Four posts stand past the box\'s ends.',
           'Four 3-section spacers (36), standing past the box\'s ends.',
           'Two bars, 15 either side of center, each resting on the box\'s rim at both ends. They clear the notch and your plugs. Sockets all along the top.', 'Pi top bars',
           'One more section to meet a ceiling at %.0f.' % CEILING)
    B = PB.stl(os.path.join(PRINT, 'pi_box_base_bored.stl')); B[:, :, 0] -= PI_DX; B[:, :, 1] -= PI_DY; B[:, :, 2] += FLOOR
    L = PB.lid_in_base(PB.stl(os.path.join(PRINT, 'pi_box_lid_over_header.stl'))); L[:, :, 0] -= PI_DX; L[:, :, 1] -= PI_DY; L[:, :, 2] += FLOOR
    P['pi_base'] = enc_t(B, AT['pi'], 'Your box: base', 'pi', 'part', 2, 0xd9c39e, 'The rpi5 base with the rings bored, as your ring test proved. Not changed, and it needs no pegs of its own.', 24000)
    P['pi_lid'] = enc_t(L, AT['pi'], 'Your box: lid, notch over the pins', 'pi', 'part', 2, 0xc9b48c, 'Your lid with the notch over the pins. Its clips hold it to the base.', 8000)
    P['pi_plugs'] = enc_w(pi_plugs(), AT['pi'], 'Dupont plugs', 'pi', 'part', 2, PLUGC, 'All 40 drawn. The top is your caliper, %.1f over the floor. That clears a ceiling at %.0f by %.1f, before the wires bend.' % (PB.PLUG_TOP, CEILING, CEILING - PB.PLUG_TOP))
    holder('pca', 'A half-section tray (6) with corner blocks for the board to sit on, %.1f up, because your model\'s pins reach 2.1 under the board. Notches in both end walls for the end headers. Four posts at the corners.' % PCA_SHELF,
           'Four half-section spacers (6).', 'One block across each end, with sockets on top. Two nubs on each reach down to the board\'s corners, past the end headers. The middle of the board stays open for your plugs.', 'PCA end blocks',
           'What it would take to reach the ceiling on its own. In the stack view, the ESP32 sits up there instead.')
    tris = []
    for s in pca:
        V, Fc = s.tessellate(0.15, 0.6)
        Q = np.array([[v.x, v.y, v.z] for v in V]); tris.append(Q[np.array(Fc)])
    P['pca_board'] = enc_t(np.vstack(tris), AT['pca'], 'Your PCA model', 'pca', 'part', 2, 0x2f8a58, 'The generic PCA9685 model from your Downloads, board 62.2 x 25.7. It has an end header on one side only, and your wiring uses both, so the tray leaves room at both ends. Not calipered against your board.', 14000)
    for i, (p, n) in enumerate(zip(pca_plugs(), ('Plugs on channels 0 and 1', 'Plug on one end header', 'Plug on the other end header'))):
        P['pca_plug%d' % i] = enc_w(p, AT['pca'], n, 'pca', 'part', 2, PLUGC, 'A guess: a %.0f mm Dupont housing or servo plug. Not measured.' % PLUG)
    holder('esp', 'A half-section tray (6) with corner blocks %.1f up. The USB end is open right down to the floor. The same four post positions as the PCA, so either one stacks on the other.' % ESP_SHELF,
           'Four half-section spacers (6).', 'One block across each end, the same idea as the PCA\'s. Its nubs land past the ends of the pin rows.', 'ESP32 end blocks',
           'What it would take to reach the ceiling on its own.')
    P['esp_board'] = enc_w(E['board'], AT['esp'], 'ESP32 board, upside down', 'esp', 'part', 2, 0x2f8a58, 'No model of your board exists, so this is a typical 55 x 28 dev board. It is upside down, so your factory pins point up and the plugs go on from above.')
    P['esp_under'] = enc_w(E['under'], AT['esp'], 'Module and USB, on its underside', 'esp', 'part', 2, 0x1d6b45, 'A guess at the module and USB port, now hanging under the board. They set the %.1f shelf.' % ESP_SHELF)
    P['esp_pins'] = enc_w(E['pins'], AT['esp'], 'Pin rows', 'esp', 'part', 2, 0xc9a227, 'A guess: 48 long, 25.4 apart.')
    P['esp_plugs'] = enc_w(E['plugs'], AT['esp'], 'Dupont plugs', 'esp', 'part', 2, PLUGC, 'A guess: every pin plugged, the worst case.')
    # the stack: over the PCA, at its spot
    at = AT['pca']; b = A['esp']
    P['stack_mid'] = enc_w(mid, at, 'Spacers, two sections', 'stack', 'spacer', 5, SPACE, 'Four 2-section spacers on the PCA\'s blocks. They give %.1f mm over the PCA\'s plugs, for wires to bend.' % (FLOOR + STACK_Z + ESP_SHELF - 3.2 - (PCA_TOP + PLUG_SEAT + PLUG)))
    P['stack_tray'] = enc_w(b['tray'], at, 'ESP32 tray', 'stack', 'tray', 6, TRAY, 'The same tray as on the floor: its pegs go in the spacers\' sockets.', z=STACK_Z)
    for k, n in (('board', 'ESP32 board, upside down'), ('under', 'Module and USB, on its underside'), ('pins', 'Pin rows'), ('plugs', 'Dupont plugs')):
        P['stack_' + k] = enc_w(E[k], at, n, 'stack', 'part', 7, {'board': 0x2f8a58, 'under': 0x1d6b45, 'pins': 0xc9a227, 'plugs': PLUGC}[k], 'The same guess as the ESP32 on the floor.', z=STACK_Z)
    P['stack_sp'] = enc_w(b['spacers'], at, 'Spacers, half section', 'stack', 'spacer', 8, SPACE, 'The same spacers as on the floor.', z=STACK_Z)
    P['stack_top'] = enc_w(many(b['top']), at, 'ESP32 end blocks', 'stack', 'top', 9, TOP, 'Their top lands at exactly %.0f, the ceiling.' % CEILING, z=STACK_Z)

    def ans(*qa):
        return [dict(q=q, a=a) for q, a in qa]

    def pr(*keys):
        return [dict(name=n, qty=q, **(info.get(k) or dict(time='', g=0.0))) for k, n, q in keys]
    joint = 'Every joint up the column is the same 5 mm peg in a 5.1 hole, held by friction. You\'ve only tried that peg in the floor, and nobody has pulled on it yet. With a ceiling pressing down on the columns, the pegs only have to stop things sliding.'
    parts = dict(
        esc=dict(name='ESC', r=62, steps=['The tray\'s pegs go in the floor.', 'The ESC presses into the tray.', 'A spacer goes on each post.', 'The top block goes on, onto the ESC\'s top.'],
                 answers=ans(('How does it get in?', 'Tray, ESC, spacers, top block, each pressed straight down. Move the slider under Build it to watch.'), ('Why this way?', 'The opening is the frame you said "fits fine enough". Its 12 mm wall is now one section. The ESC is 3 sections tall: 36 over its 34.'), ('What holds it upside down?', 'The top block, with lips round the ESC\'s top. ' + joint), ('Where do the wires go?', 'Out the finned face. Between the tray wall and the lips there\'s a %.0f mm tall window, open on both long faces.' % (ESC[2] - LIP - U))),
                 guesses=[('ESC thickness', '24', 'Still your 24. I\'m waiting on the two heights: to the case and to the fin tops.'), ('Which way up', 'either', 'It fits both ways up, and your wires can wedge differently each way.'), ('Pad', '%.1f' % (3 * U - ESC[2] - GAP), 'Takes up the room between the ESC\'s 34 and the 36 of 3 sections.')], print=pr(('esc_tray', 'Tray', 1), ('spacer_two', 'Spacer, 2 sections', 2), ('esc_top', 'Top block', 1))),
        pack=dict(name='Pack', r=100, steps=['The tray\'s pegs go in the floor.', 'The pack drops into the tray.', 'A spacer goes on each post.', 'The top block goes on, onto the pack\'s top.'],
                  answers=ans(('How does it get in?', 'Tray, pack, spacers, top block, each pressed straight down. To swap: pull the top block, lift the pack. The spacers can stay.'), ('Why this way?', 'Four sections tall, as you said: 48 over its 45.7. A 150 mm top block is one long brick.'), ('What holds it upside down?', 'The top block holds all 300 g, on four pegs. This is the hardest test of the five. ' + joint), ('Where do the wires go?', 'Out a short end, through the 7 mm gate between the two columns, wires one above the other. I\'m assuming the lead leaves by a short end at mid height.')),
                  guesses=[('Pack size', '141 x 26 x 45.7', 'From your model. Worth a caliper before printing.'), ('Lead position', 'a short end, mid height', 'Assumed. It has to fit the 7 mm gate.'), ('Top block', '158 long', 'Long for a print of bars this size. It may warp.'), ('Ties', '3, 12 wide', 'Picked.')], print=pr(('pack_tray', 'Tray', 1), ('spacer_three', 'Spacer, 3 sections', 4), ('pack_top', 'Top block', 1))),
        pi=dict(name='Pi', r=78, steps=['The frame\'s pegs go in the floor.', 'Your closed box drops into the frame.', 'A spacer goes on each post.', 'The two bars go on, resting on the box\'s rim.'],
                answers=ans(('How does it get in?', 'Your closed box drops into the frame. Then spacers, then the two bars.'), ('Why this way?', 'Your box already encloses the Pi, so it gets no new lid. The bars only hold the box down, and they rest on its rim.'), ('What holds it upside down?', 'The lid\'s clips hold the lid. The two bars hold the box. ' + joint), ('Where do the wires go?', 'Up through the lid\'s notch, past the bars. Your plugs stand %.1f over the floor. A ceiling at %.0f clears them by only %.1f, so the wires need a hole there, or one more section of height.' % (PB.PLUG_TOP, CEILING, CEILING - PB.PLUG_TOP))),
                guesses=[('Frame height', 'half section, 6', 'Picked to stay under the port windows.'), ('Clearance', '0.25 a side', 'Tested on the ESC only, and your box is itself a print.'), ('Columns past the ends', '60 from center', 'They stand about 10 mm from the USB and SD ends. A USB plug would have to fit between them.'), ('Whole box', 'not printed', 'Only the ring test has been printed since the rings were bored.')], print=pr(('pi_frame', 'Frame', 1), ('spacer_three', 'Spacer, 3 sections', 4), ('pi_bar', 'Top bar', 2))),
        pca=dict(name='PCA9685', r=56, steps=['The tray\'s pegs go in the floor.', 'The board goes on its corner blocks.', 'A spacer goes on each post.', 'A block goes across each end, its nubs on the board\'s corners.'],
                 answers=ans(('How does it get in?', 'Board onto the corner blocks, with its end headers over the notches. Then spacers and the two end blocks. Plug it up before or after.'), ('Why this way?', 'Your plugs stand on the board, so a flat top won\'t work. Two blocks across the ends leave the middle open.'), ('What holds it upside down?', 'Four nubs press on the board\'s corners. ' + joint), ('Where do the wires go?', 'Up through the open middle. The end plugs go out under the end blocks.')),
                 guesses=[('Board size', '62.2 x 25.7', 'From the generic model in your Downloads. Please caliper yours.'), ('Shelf', '%.1f' % PCA_SHELF, 'The model\'s pins reach 2.1 under the board.'), ('Plug height', '%.0f + %.1f seat' % (PLUG, PLUG_SEAT), 'A guess.')], print=pr(('pca_tray', 'Tray', 1), ('spacer_half', 'Spacer, half section', 4), ('pca_block', 'End block', 2))),
        esp=dict(name='ESP32', r=56, steps=['The tray\'s pegs go in the floor.', 'The board goes on its corner blocks, upside down.', 'A spacer goes on each post.', 'A block goes across each end, its nubs on the board\'s corners.'],
                 answers=ans(('How does it get in?', 'Upside down, pins up, onto the corner blocks with the USB at the open end. Then spacers and the two end blocks.'), ('Why this way?', 'Your factory pins point away from the components. Upside down, the plugs go on from above, instead of needing room under the board.'), ('What holds it upside down?', 'Four nubs press on the board\'s corners. ' + joint), ('Where do the wires go?', 'Up through the open middle. USB at the open end.')),
                 guesses=[('Board size', '55 x 28', 'Typical, not yours. I need a caliper, or its model if you have one.'), ('Upside down', 'pins up', 'My pick, so the plugs go on from above. Your call.'), ('Shelf', '%.1f' % ESP_SHELF, 'Room for the module and USB, both guessed.'), ('Pin rows', '48 long, 25.4 apart', 'Typical. The nubs land past their ends, with only 0.4 to spare.')], print=pr(('esp_tray', 'Tray', 1), ('spacer_half', 'Spacer, half section', 4), ('esp_block', 'End block', 2))),
        stack=dict(name='Stacked', r=62, steps=['The PCA\'s tray goes in the floor.', 'The PCA goes on its corner blocks.', 'Half-section spacers.', 'The PCA\'s end blocks.', 'Two-section spacers on the blocks\' sockets.', 'The ESP32\'s tray pegs onto them.', 'The ESP32 goes on its corner blocks.', 'Half-section spacers.', 'The ESP32\'s end blocks, topping out at %.0f.' % CEILING],
                   answers=ans(('What is this showing?', 'What the pegboard tops are for. The ESP32 sits on the PCA, using one holder footprint instead of two.'), ('Does it fit?', 'Yes on my numbers: the top lands at exactly %.0f, the ceiling. There\'s %.1f mm over the PCA\'s plugs for wires to bend, against my guessed %.0f.' % (CEILING, FLOOR + STACK_Z + ESP_SHELF - 3.2 - (PCA_TOP + PLUG_SEAT + PLUG), BEND)), ('What does it cost?', 'A taller stack on four thin columns, and you have to unstack the ESP32 to reach the PCA.'), ('Is this a decision?', 'No. It\'s an example.')),
                   guesses=[('Room over the plugs', '%.1f' % (FLOOR + STACK_Z + ESP_SHELF - 3.2 - (PCA_TOP + PLUG_SEAT + PLUG)), 'From guessed plug and module heights.')], print=pr(('spacer_two', 'Spacer, 2 sections', 4))))
    common = [('One section', '%.0f' % U, 'My pick: 3 for the ESC (36 over its 34), 4 for the pack (48 over its 45.7), and it\'s the wall height of the frame you OKed. Half sections (%.0f) fill the gaps.' % HALF),
              ('Ceiling', '%.0f, 5 sections' % CEILING, 'Where the stacks can all meet. Another layer of spacers moves it, and the bricks don\'t change. Not a decision.'),
              ('Sockets', '%.1f x %.1f deep, %.1f mouth' % (HOLE, DEPTH, MOUTH), 'Your 5.1, but so far tried only through a flat floor, entered from its top. These print mouth down on the bed, so they could come out tighter. Untested.'),
              ('Pegs', '5 x %.1f' % PEG_LONG, 'Your floor\'s peg, so any brick fits the floor or another brick. Pull-out is untested. Stacks may want longer pegs.'),
              ('Brick width', '%.0f' % POST, 'Up from your frame\'s 7, for %.2f of wall round a socket.' % ((POST - HOLE) / 2)), ('Air over a part', '%.1f' % GAP, 'A TPU pad could take it up.'), ('Clearance', '%.2f a side' % FIT, 'Tested only on the ESC\'s thickness.')]
    for k, d in parts.items():
        d['guesses'] = [dict(name=n, value=v, why=w) for n, v, w in d['guesses']]
        at = AT['pca'] if k == 'stack' else AT[k]
        d['center'] = [at[0], at[1], 30.0]
    set_ = []
    for k, (w, q) in pieces(A).items():
        if q:
            set_.append(dict(name={'esc_tray': 'ESC tray', 'esc_top': 'ESC top block', 'pack_tray': 'Pack tray', 'pack_top': 'Pack top block', 'pi_frame': 'Pi frame', 'pi_bar': 'Pi top bar', 'pca_tray': 'PCA tray', 'pca_block': 'PCA end block', 'esp_tray': 'ESP32 tray', 'esp_block': 'ESP32 end block', 'spacer_half': 'Spacer, half section', 'spacer_two': 'Spacer, 2 sections', 'spacer_three': 'Spacer, 3 sections'}.get(k, k), qty=q, **(info.get(k) or dict(time='', g=0.0))))
    meta = dict(order=['esc', 'pack', 'pi', 'pca', 'esp', 'stack'], parts=parts, common=[dict(name=n, value=v, why=w) for n, v, w in common], ceiling=CEILING, section=U, floor=FLOOR, floor_x=FLOOR_X, floor_y=FLOOR_Y,
                info=info, set=set_, all=dict(name='All', r=170, center=[0, 18, 30.0], steps=['Trays.', 'Parts.', 'Spacers.', 'Top blocks.', 'Spacers for the stack.', 'The ESP32\'s tray.', 'The ESP32.', 'Spacers.', 'The ESP32\'s end blocks.']))
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', 'window.PARTS=' + json.dumps(P) + ';window.META=' + json.dumps(meta) + ';')
    p = os.path.join(config.TWIN_OUT, 'bricks_view.html')
    open(p, 'w', encoding='utf-8').write(html)
    print('wrote %s (%.1f MB)' % (p, len(html) / 1e6))


if __name__ == '__main__':
    if 'page' in sys.argv[1:]:                  # only the page, for working on the viewer: no checks, no STLs
        A = assemble()
        page(A, esp_model(), pca_board(), many(spacer(2 * U, x, y, FLOOR + 3 * HALF) for x, y in BOARD_PEGS), json.load(open(SLICE)) if os.path.exists(SLICE) else {})
        sys.exit(0)
    good, A, E, pca, mid = check()
    print('Print pieces (all upside down: top on the bed, pegs up):')
    os.makedirs(PRINT, exist_ok=True)
    paths = {}
    for k, (w, q) in pieces(A).items():
        f = flip(w)
        p = os.path.join(PRINT, 'brick_%s.stl' % k)
        write_stl(f.val().wrapped, p, lin=0.02, ang=0.2)
        h_ok, msg = health(p); good &= bool(h_ok)
        bb = f.val().BoundingBox()
        print('  %-14s x%-2d %5.1f x %5.1f x %5.1f  %s %s' % (k, q, bb.xlen, bb.ylen, bb.zlen, 'ok ' if h_ok else 'BAD', msg))
        paths[k] = p
    if 'slice' in sys.argv[1:]:
        print('Slices, draft, not sent to the printer:')
        slice_all(paths)
    info = json.load(open(SLICE)) if os.path.exists(SLICE) else {}
    if os.path.exists(TEMPLATE):
        page(A, E, pca, mid, info)
    print('checks:', 'all pass' if good else 'SOMETHING FAILED')
    sys.exit(0 if good else 1)
