"""The whole brain box, assembled (2026-11-08). Zach: "alright show a fully assembled brain box now".

    python twin/brain_box.py         # builds, checks with controls, twin/out/brain_box_view.html (the "Brain Box" artifact)
    python twin/brain_box.py slice   # the same, and slices the small boxes too (draft, not printed) into twin/out/brain_box_slice.json

Every box from part_boxes.py, on one floor, inside a 250 x 139.5 body, with the parts still to arrive as boxes of their listing sizes, the nose camera, the wires at his measured
lengths, the body's walls and a lid. Nothing here is printed or decided: this is one layout, drawn to find out what breaks.

Frame: x 0 at the back to 250 at the nose, y across (0 on the centre line, +y the drive pack's side), z up from the floor's underside. * = picked, for Zach to OK or measure.
"""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
sys.path.insert(0, HERE)
import numpy as np
import cadquery as cq
import config
from export import write_stl, health
import part_boxes as X
from part_boxes import rect, cyl, vol, FLOOR, PITCH, UNIT, HEIGHT, LID_T, T_W, BOTTOM, FIT, shift, many
import pi_box as PB
import peg_test as PT
import grid_layouts as GL

PRINT = X.PRINT
TEMPLATE = os.path.join(HERE, 'brain_box_view_template.html')
SLICE = os.path.join(config.TWIN_OUT, 'brain_box_slice.json')
LEN, WID = 250.0, 139.5                  # the body: the 250 cap and print 1's width
SHELL = 2.6                              # print 1's wall and floor
X_IN = (SHELL, LEN - SHELL)
Y_IN = WID / 2 - SHELL
CEILING = X.CEILING                      # 77 over the floor's top
GRID_X0 = 0.5                            # * the floor's holes: x = 0.5 + 15 i, y = 7.5 + 15 j, so the Pi's sleeve stands 0.35 off the back wall

# where everything goes
PI_AT = (38.0, -7.5)                     # the sleeve turned so its long way runs across the body, its header toward the middle, its SD end to +y
PACK_X = 165.5                           # * forward of the Pi by a clear lane for the packs' leads
PACK_Y = 45.0                            # +y the drive pack, -y the Pi's pack
ESC_AT = ((120.5, 0.0), (195.5, 0.0))    # * down the middle, with a wire lane each side between them and the packs
IMU_AT = (158.0, 0.0)                    # between the ESCs, near the middle of the body
POLOLU_AT = (38.0, -30.0)                # on the Pi's top
INA_AT = (38.0, 0.0)
ALARM_AT = (113.0, -45.0)                # on the Pi pack's top
BEC_AT = (113.0, 45.0)                   # on the drive pack's top
AXLES = (49.0, 201.0)                    # * T3's 152 wheelbase centred in the body. The first robot's axles aren't drawn yet
ROBOT_COM = (170.5, -0.3, 55.2)          # T3's centre of mass in this frame (knobs.make: x 28.5 + 142, z 80.1 - its 24.9 belly), for the balance
RIBBON = 200.0                           # the IMX219's cable, from the listing
RIBBON_LONG = 300.0                      # the 30 cm ribbon he has for the Arducam
PACK_LEAD, ESC_POWER, ESC_MOTOR = 120.0, 90.0, 105.0     # his lengths
SIZES = dict(pololu=(25.4, 25.4, 9.5, 3), ina=(25.6, 20.4, 4.7, 2), imu=(20.0, 25.0, 4.6, 2), alarm=(40.0, 25.0, 12.0, 3), bec=(48.0, 30.0, 15.0, 3))   # listing sizes, as grid_eval.PARTS, and units tall
SIZE_NOTE = dict(pololu='Pololu 5 V regulator', ina='INA219 battery meter', imu='BNO085 IMU', alarm='LiPo alarm', bec='Servo BEC slot')
SMALL_PEGS = [(s, t) for s in (-7.5, 7.5) for t in (-7.5, 7.5)]


def pi_place(w, z=0.0):
    """the Pi's sleeve frame to this one: a quarter turn, so its long way runs across"""
    return w.rotate((0, 0, 0), (0, 0, 1), -90).translate((PI_AT[0], PI_AT[1], z))


def pi_tris(T):
    T = np.array(T, float); x = T[:, :, 0].copy(); y = T[:, :, 1].copy()
    T[:, :, 0] = y + PI_AT[0]; T[:, :, 1] = -x + PI_AT[1]
    return T


def small_box(k):
    a, b, h, u = SIZES[k]
    A, B = a + 2 * FIT, b + 2 * FIT
    rim = u * UNIT - LID_T
    z1 = FLOOR + rim + 1
    cuts = [(-A / 2 + 3.0, A / 2 - 3.0, *sorted((s * (B / 2 - 0.5), s * (B / 2 + T_W + 1))), FLOOR + BOTTOM + h * 0.6, z1) for s in (-1, 1)]   # the wires' way out
    room = rim - BOTTOM - h                                              # the ring under the top has to stop above the part: the BEC slot's 15 leaves only 1.0
    return X.box(A, B, rim, SMALL_PEGS, cuts), X.top_piece(A, B, rim, SMALL_PEGS, plug_deep=min(X.PLUG_DEEP, room - 0.1))


def small_part(k):
    a, b, h, u = SIZES[k]
    return rect(-a / 2, a / 2, -b / 2, b / 2, FLOOR + BOTTOM, FLOOR + BOTTOM + h)


def assemble():
    """every solid in place: [(key, label, role, layer, workplane)]"""
    E = X.esp_model()
    P = []

    def add(key, label, role, layer, w):
        P.append(dict(key=key, label=label, role=role, layer=layer, w=w))
    # the first layer: boxes in the floor
    add('pi_sleeve', 'Pi sleeve', 'box', 1, pi_place(X.pi_sleeve()))
    for y, n, name in ((PACK_Y, 'drive', 'Drive pack'), (-PACK_Y, 'pi', 'Pi pack')):
        add('pack_box_' + n, name + ' box', 'box', 1, shift(X.pack_box(), PACK_X, y))
        add('pack_' + n, name, 'part', 2, shift(X.pack_solid(), PACK_X, y))
        add('pack_top_' + n, name + ' top', 'top', 3, shift(X.pack_top(), PACK_X, y))
    for i, (x, y) in enumerate(ESC_AT):
        add('esc_box_%d' % i, 'ESC %d box' % (i + 1), 'box', 1, shift(X.esc_box(), x, y))
        add('esc_%d' % i, 'ESC %d' % (i + 1), 'part', 2, shift(X.esc_solid(), x, y))
        add('esc_top_%d' % i, 'ESC %d top' % (i + 1), 'top', 3, shift(X.esc_top(), x, y))
    add('pi_box', 'Your Pi box', 'part', 2, pi_place(X.pi_solid()))
    add('pi_stops', 'Pi stops', 'top', 3, pi_place(many(X.pi_stop(y) for y in X.ROWS)))
    ib, it = small_box('imu')
    add('imu_box', 'IMU box', 'box', 1, shift(ib, *IMU_AT)); add('imu', 'BNO085 IMU', 'part', 2, shift(small_part('imu'), *IMU_AT)); add('imu_top', 'IMU top', 'top', 3, shift(it, *IMU_AT))
    # the second layer: boxes on tops
    ez, pz, kz = HEIGHT['esc'], HEIGHT['pi'], HEIGHT['pack']
    x0, y0 = ESC_AT[0]
    add('pca_box', 'PCA box', 'box', 4, shift(X.pca_box(), x0, y0, ez))
    add('pca_case', 'Your PCA case', 'part', 5, shift(X.case_solid(), x0, y0, ez))
    add('pca_top', 'PCA top', 'top', 6, shift(X.pca_top(), x0, y0, ez))
    x1, y1 = ESC_AT[1]
    add('esp_box', 'ESP32 box', 'box', 4, shift(X.esp_box(), x1, y1, ez))
    add('esp_board', 'ESP32 board', 'part', 5, shift(E['board'].union(E['under']), x1, y1, ez))
    add('esp_plugs', 'ESP32 pins and plugs', 'part', 5, shift(E['pins'].union(E['plugs']), x1, y1, ez))
    add('esp_top', 'ESP32 top', 'top', 6, shift(X.esp_top(), x1, y1, ez))
    for k, at, z in (('pololu', POLOLU_AT, pz), ('ina', INA_AT, pz), ('alarm', ALARM_AT, kz), ('bec', BEC_AT, kz)):
        b, t = small_box(k)
        add(k + '_box', SIZE_NOTE[k] + ' box', 'box', 4, shift(b, at[0], at[1], z))
        add(k, SIZE_NOTE[k], 'part', 5, shift(small_part(k), at[0], at[1], z))
        add(k + '_top', SIZE_NOTE[k] + ' top', 'top', 6, shift(t, at[0], at[1], z))
    # spacers up to the ceiling, where a stack comes up short
    add('sp_drive', 'Spacer, drive pack', 'spacer', 7, shift(X.spacer(3 * UNIT, 60.0, FLOOR + kz), PACK_X, PACK_Y))
    add('sp_pi', 'Spacer, Pi pack', 'spacer', 7, shift(X.spacer(3 * UNIT, 60.0, FLOOR + kz), PACK_X, -PACK_Y))
    add('sp_top', 'Spacer on the Pi', 'spacer', 7, pi_place(X.spacer(5 * UNIT, -45.0, FLOOR + pz)))
    # the rest
    add('camera', 'IMX219 camera, in the nose', 'part', 2, rect(X_IN[1] - 6.0, X_IN[1], -12.5, 12.5, FLOOR + 38.0, FLOOR + 62.0))
    add('stop', 'Stop button', 'part', 2, W_cyl(84.0, Y_IN + SHELL, Y_IN - 28.0, 8.0, FLOOR + 33.0))
    add('switch', 'Pi power switch', 'part', 2, W_cyl(84.0, -Y_IN - SHELL, -Y_IN + 14.0, 3.5, FLOOR + 33.0))
    return P


def W_cyl(x, y0, y1, r, z):
    """a part through a side wall: a cylinder along y"""
    a, b = sorted((y0, y1))
    return cq.Workplane('XZ').workplane(offset=-b).center(x, z).circle(r).extrude(b - a)


def floor():
    xs = [GRID_X0 + PITCH * i for i in range(1, 17)]
    ys = [7.5 + PITCH * j for j in range(-4, 4)]
    return rect(0.0, LEN, -WID / 2, WID / 2, 0, FLOOR).faces('>Z').workplane(origin=(0, 0, FLOOR)).pushPoints([(x, y) for x in xs for y in ys]).hole(X.HOLE)


def shell():
    """the body's four walls, up to the lid"""
    z0, z1 = FLOOR - 0.5, FLOOR + CEILING
    F = rect(0.0, LEN, -WID / 2, WID / 2, z0, z1).cut(rect(X_IN[0], X_IN[1], -Y_IN, Y_IN, z0 - 1, z1 + 1))
    return F


def lid():
    return rect(0.0, LEN, -WID / 2, WID / 2, FLOOR + CEILING, FLOOR + CEILING + SHELL)


# ---------------------------------------------------------------- the wires, at his lengths
def plug_top():
    """where the PCA's channel plugs and end-header plugs top out, stacked on the first ESC"""
    x0, y0, _ = X.board_xy()
    z = X.BOARD_TOP + X.PLUG_SEAT + X.PLUG + HEIGHT['esc']
    return ESC_AT[0][0] + x0, y0, z


def wires():
    """name, kind, colour, points, budget mm (None: Dupont or spare wire, as long as needed). His photos put the leads across the finned face; both ESCs have it toward +y, and stand so their
    red and black come out at the end nearest the Y-harness. * every route"""
    e0, e1 = ESC_AT[0][0], ESC_AT[1][0]
    wy = X.ESC_B / 2 + T_W                                               # the face of an ESC box's window
    Y = (135.0, 22.0, 15.0)                                              # * the Y-harness, in the drive side's lane, between the ESCs' leads
    lane = 84.0                                                          # the lane behind the packs
    px, py, pz = plug_top()
    W_ = []
    W_.append(dict(name='Drive pack lead', group='Power', color=0xd8392b, budget=PACK_LEAD, r=2.0, pts=[(PACK_X - 72.75, PACK_Y, 25.0), (lane, PACK_Y, 25.0), (lane, PACK_Y, 15.0), (lane, 22.0, 15.0), Y]))
    W_.append(dict(name='ESC 1 red and black', group='Power', color=0xd8392b, budget=ESC_POWER, r=2.0, pts=[(e0 - 14.0, wy, 30.0), (e0 - 14.0, 22.0, 18.0), Y]))
    W_.append(dict(name='ESC 2 red and black', group='Power', color=0xd8392b, budget=ESC_POWER, r=2.0, pts=[(e1 - 14.0, wy, 30.0), (e1 - 14.0, 22.0, 18.0), Y]))
    W_.append(dict(name='Pi pack lead', group='Power', color=0xd8392b, budget=PACK_LEAD, r=2.0, pts=[(PACK_X - 72.75, -PACK_Y, 25.0), (lane, -PACK_Y, 25.0), (lane - 4.0, -PACK_Y, 50.0), (58.0, -10.0, 50.0), (53.0, 0.0, 50.0)]))
    W_.append(dict(name='INA219 to Pololu', group='Power', color=0xb0342a, budget=None, r=1.2, pts=[(38.0, -12.5, 50.0), (38.0, -15.0, 50.0)]))
    W_.append(dict(name='Pololu to the Pi\'s pins', group='Signal', color=0xe07b39, budget=None, r=1.0, pts=[(53.0, -30.0, 54.0), (60.0, -25.0, 62.0), (62.5, -16.0, 62.0)]))
    W_.append(dict(name='ESC 1 yellow and blue', group='Motor', color=0xe0b000, budget=ESC_MOTOR, r=1.8, pts=[(e0 - 9.0, wy, 26.0), (e0 - 9.0, 22.0, 15.0), (lane, 22.0, 15.0), (lane, Y_IN - 3.0, 15.0)]))
    # ESC 2's run to the far side is longer than its leads, so its splice sits where they end: the two motors' wires have to split somewhere anyway
    W_.append(dict(name='ESC 2 yellow and blue', group='Motor', color=0xe0b000, budget=ESC_MOTOR, r=1.8, pts=[(e1 - 9.0, wy, 26.0), (e1 - 9.0, 22.0, 15.0), (232.0, 22.0, 15.0), (232.0, -18.0, 15.0)]))
    for ax, which in zip(AXLES, ('rear', 'front')):
        W_.append(dict(name='Spliced on, to the %s left motor' % which, group='Motor', color=0x9c7b00, budget=None, r=1.4, pts=[(lane, Y_IN - 3.0, 15.0), (ax, Y_IN - 3.0, 15.0), (ax, Y_IN, 20.0)]))
        W_.append(dict(name='Spliced on, to the %s right motor' % which, group='Motor', color=0x9c7b00, budget=None, r=1.4, pts=[(232.0, -18.0, 15.0), (242.0, -24.0, 15.0), (242.0, -Y_IN + 3.0, 15.0), (ax, -Y_IN + 3.0, 15.0), (ax, -Y_IN, 20.0)]))
    W_.append(dict(name='ESC 1 signal to the PCA', group='Signal', color=0xf2f2f2, budget=None, r=1.0, pts=[(e0 + 2.0, wy, 34.0), (e0 + 2.0, 19.0, 62.0), (px + 6.0, 4.0, pz + 3.0), (px, py, pz)]))
    W_.append(dict(name='ESC 2 signal to the PCA', group='Signal', color=0xf2f2f2, budget=None, r=1.0, pts=[(e1 - 20.0, wy, 34.0), (e1 - 28.0, 22.0, 62.0), (e0 + 27.0, 22.0, 62.0), (e0 + 20.0, 2.0, pz + 2.0), (px + 2.0, py, pz)]))
    W_.append(dict(name='Pi to the PCA', group='Signal', color=0x4a90d9, budget=None, r=1.0, pts=[(64.5, 0.0, 62.0), (75.0, 0.0, 70.0), (88.0, 0.0, pz + 3.0), (ESC_AT[0][0] + X.board_xy()[0] - 29.2, 0.0, pz)]))
    W_.append(dict(name='Pi to the ESP32', group='Signal', color=0x4a90d9, budget=None, r=1.0, pts=[(64.5, 20.0, 62.0), (75.0, 24.0, 70.0), (150.0, 24.0, 70.0), (168.0, 10.0, 70.0), (172.0, 8.0, 68.0)]))
    W_.append(dict(name='Camera ribbon', group='Ribbon', color=0xc9cdd3, budget=RIBBON, r=1.0, extra=25.0, pts=[(X_IN[1] - 6.0, 0.0, FLOOR + 50.0), (232.0, -5.0, 45.0), (225.0, -22.0, 40.0), (90.0, -22.0, 40.0), (76.0, -22.0, 40.0), (73.05, -10.0, 25.0)]))
    for w in W_:
        p = np.array(w['pts'])
        w['len'] = float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) + w.get('extra', 0.0)
        w['bad'] = bool(w['budget'] and w['len'] > w['budget'])
    return W_


# ---------------------------------------------------------------- the balance
def balance(info):
    """the insides' mass and centre, against the sim's layout (grid_layouts' A), and what that does to the robot's"""
    M = GL.MASS
    box_g = lambda k, q=1: q * (info.get(k) or dict(g=0.0))['g']
    items = []

    def add(name, g, x, y, z):
        items.append((name, g, x, y, z))
    pz, ez, kz = HEIGHT['pi'], HEIGHT['esc'], HEIGHT['pack']
    for y in (PACK_Y, -PACK_Y):
        add('pack', M['pack'], PACK_X, y, FLOOR + BOTTOM + 22.85)
        add('pack box and top', box_g('pack_box') + box_g('pack_top'), PACK_X, y, FLOOR + 26.0)
    for x, y in ESC_AT:
        add('esc', M['esc'], x, y, FLOOR + BOTTOM + 17.0)
        add('esc box and top', box_g('esc_box') + box_g('esc_top'), x, y, FLOOR + 19.0)
    add('pi', M['pi'], PI_AT[0], PI_AT[1], FLOOR + BOTTOM + 18.0)
    add('pi sleeve', box_g('pi_sleeve'), PI_AT[0], PI_AT[1], FLOOR + 21.0)
    add('pca', M['pca'], ESC_AT[0][0], 0.0, FLOOR + ez + 8.0)
    add('pca box, top, case', box_g('pca_box') + box_g('pca_top') + box_g('case_base') + box_g('case_lid'), ESC_AT[0][0], 0.0, FLOOR + ez + 15.0)
    add('esp', M['esp'], ESC_AT[1][0], 0.0, FLOOR + ez + 8.0)
    add('esp box and top', box_g('esp_box') + box_g('esp_top'), ESC_AT[1][0], 0.0, FLOOR + ez + 15.0)
    for k, at, z, g in (('pololu', POLOLU_AT, pz, M['pololu']), ('ina', INA_AT, pz, M['ina']), ('alarm', ALARM_AT, kz, M['alarm']), ('bec', BEC_AT, kz, M['bec']), ('imu', IMU_AT, 0.0, M['imu'])):
        add(k, g, at[0], at[1], FLOOR + z + 8.0)
        add(k + ' box and top', box_g(k + '_box') + box_g(k + '_top'), at[0], at[1], FLOOR + z + 8.0)
    A = np.array([i[1:] for i in items], float)
    g = A[:, 0].sum(); c = (A[:, 0, None] * A[:, 1:]).sum(0) / g
    ref = [(p['k'], p['b']) for p in GL.on_walls()['parts']]
    R = np.array([[M[k], (b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2] for k, b in ref], float)
    rg = R[:, 0].sum(); rc = (R[:, 0, None] * R[:, 1:]).sum(0) / rg
    # the robot's centre moves by the change in the insides' moment about it, over the robot's mass with the boxes added
    robot = GL.T3_G + g - rg
    move = ((A[:, 0, None] * (A[:, 1:] - np.array(ROBOT_COM))).sum(0) - (R[:, 0, None] * (R[:, 1:] - np.array(ROBOT_COM))).sum(0)) / robot
    return dict(grams=g, centre=c.tolist(), ref_grams=rg, ref_centre=rc.tolist(), added=g - rg, robot=robot, move=move.tolist())


# ---------------------------------------------------------------- the checks
def check():
    ok = True

    def line(what, good, got=''):
        nonlocal ok
        ok &= bool(good)
        print('  %-78s %s %s' % (what, got, 'ok' if good else 'WRONG'))

    P = assemble(); Fl = floor(); Sh = shell(); Li = lid()
    S = [dict(p, bb=p['w'].val().BoundingBox()) for p in P]
    print('--- every piece against every other, exact, and the body')
    hits = []
    for i, a in enumerate(S):
        for b in S[i + 1:]:
            A, B = a['bb'], b['bb']
            if A.xmin < B.xmax and B.xmin < A.xmax and A.ymin < B.ymax and B.ymin < A.ymax and A.zmin < B.zmax and B.zmin < A.zmax:
                v = vol(a['w'], b['w'])
                if v > 1e-3:
                    hits.append((a['key'], b['key'], round(v, 2)))
    line('no two pieces overlap (%d pieces)' % len(S), not hits, '%s' % (hits or ''))
    bad = [p['key'] for p in P if p['key'] not in ('stop', 'switch') and vol(p['w'], Sh) > 1e-3]
    line('nothing runs into the body\'s walls', not bad, '%s' % (bad or ''))
    bad = [p['key'] for p in P if vol(p['w'], Li) > 1e-3]
    line('nothing runs into the lid at %.0f' % CEILING, not bad, '%s' % (bad or ''))
    bad = [p['key'] for p in P if p['layer'] in (1,) and vol(p['w'], Fl) > 1e-3]
    line('every peg in the floor is in a hole', not bad, '%s' % (bad or ''))
    print('--- controls')
    pca = next(p for p in P if p['key'] == 'pca_box')['w']
    v = vol(shift(pca, x=45.0), next(p for p in P if p['key'] == 'esp_box')['w']); line('the PCA box 45 mm forward hits the ESP32 box', v > 1, '%.1f mm3' % v)
    pk = next(p for p in P if p['key'] == 'pack_box_drive')['w']
    v = vol(shift(pk, x=15.0), Sh); line('a pack 15 mm forward hits the nose wall', v > 1, '%.1f mm3' % v)
    v = vol(Fl, shift(next(p for p in P if p['key'] == 'esc_box_0')['w'], x=5.0)); line('an ESC box 5 mm off the grid hits the floor', v > 1, '%.1f mm3' % v)
    print('--- wires, at his lengths')
    W_ = wires()
    for w in W_:
        if w['budget']:
            print('  %-34s %5.0f of %3.0f mm  %s' % (w['name'], w['len'], w['budget'], 'SHORT by %.0f' % (w['len'] - w['budget']) if w['bad'] else 'reaches, %.0f spare' % (w['budget'] - w['len'])))
    print('  (the camera ribbon being short is a finding, not a failed check: it is on the page)')
    fake = dict(W_[0]); fake['pts'] = [(0, 0, 0), (200, 0, 0)]; p_ = np.array(fake['pts']); L = float(np.linalg.norm(np.diff(p_, axis=0), axis=1).sum())
    line('control: a 200 mm run reads as over a %.0f lead' % PACK_LEAD, L > PACK_LEAD, '%.0f' % L)
    print('--- where the stacks top out, over the floor\'s top')
    print('  ESC + PCA %.0f, ESC + ESP32 %.0f, pack + spacer %.0f, Pi %.0f, Pi plugs %.1f, ceiling %.0f' % (HEIGHT['esc'] + HEIGHT['pca'], HEIGHT['esc'] + HEIGHT['esp'], HEIGHT['pack'] + 3 * UNIT, HEIGHT['pi'], BOTTOM + PB.PLUG_TOP, CEILING))
    print('--- room')
    print('  across at the packs: %.2f to the wall, %.2f between each pack box and the ESC box\'s lane edge' % (Y_IN - (PACK_Y + X.PACK_B / 2 + T_W), PACK_Y - X.PACK_B / 2 - T_W - X.ESC_B / 2 - T_W))
    print('  along: Pi sleeve front at %.2f, pack back at %.2f, pack front at %.2f, nose wall at %.1f' % (PI_AT[0] + X.PI_B / 2 + T_W, PACK_X - X.PACK_A / 2 - T_W, PACK_X + X.PACK_A / 2 + T_W, X_IN[1]))
    return ok, P, W_


def enc_w(w, label, group, role, layer, color, note, tol=0.08):
    return X.enc_w(w, (0, 0), label, group, role, layer, color, note, tol=tol)


def page(P, W_, info):
    COL = dict(box=0xe0b35c, top=0x5fb3a1, spacer=0x8f8fd6)
    PART = dict(pack_drive=0x4a78b5, pack_pi=0x4a78b5, esc_0=0x4a78b5, esc_1=0x4a78b5, camera=0x2f8a58, stop=0xc0392b, switch=0x3a3d43)
    NOTES = dict(
        pi_sleeve='Your closed Pi box slides into this, turned so its long way runs across the body and its header faces the middle. Its top is a pegboard with a bite for your plugs.',
        pack_box_drive='One pack runs both ESCs. Its lead comes out the back end, into the lane behind the packs.', pack_box_pi='The Pi\'s own pack. Its lead comes out the back end and goes up to the INA219 on the Pi\'s top.',
        esc_box_0='Down the middle of the body. The finned face looks across a 15.5 mm lane toward the drive pack, where the leads run.', esc_box_1='The same as ESC 1, further forward.',
        imu_box='Between the two ESCs, near the middle of the body, where an IMU reads least of the body\'s rocking. Its size is from the listing.',
        pca_box='On ESC 1\'s top. Your case goes in unchanged, and its plugs face up into the space under its own top.', esp_box='On ESC 2\'s top.',
        pololu_box='On the Pi\'s top, right next to the Pi\'s pins. Not bought yet: its size is from the listing.', ina_box='On the Pi\'s top, in the Pi pack\'s lead. Not bought yet: its size is from the listing.',
        alarm_box='On the Pi pack\'s top, so its balance lead is short. It comes off with that top in a swap. Its size is from the review.', bec_box='The slot kept for the tail\'s servo BEC, on the drive pack\'s top. Nothing is bought. Its size is from the sims.',
        camera='Your IMX219, in the nose at about mid height. Its size is from the listing, and the funnel in the nose wall isn\'t drawn.', stop='The latching stop button, through the +y side wall where you can hit it. Not bought. Its size is from the listing.', switch='The Pi\'s power switch, through the -y side wall. A guess at its size.',
        sp_drive='Reaches the lid at the front of the pack. The BEC slot reaches it at the back.', sp_pi='Reaches the lid at the front of the pack. The alarm reaches it at the back.', sp_top='On the Pi\'s top, so the lid has something to press on over the Pi.')
    Pg = dict(floor=enc_w(floor(), 'Body floor', 'body', 'floor', 0, 0xb9c4d0, 'Print 1\'s 2.6 mm floor with your %.1f holes every %.0f mm.' % (X.HOLE, PITCH), tol=0.1))
    Pg['shell'] = enc_w(shell(), 'Body walls', 'body', 'shell', 9, 0xaab4c0, 'A plain 250 x 139.5 box with 2.6 walls, up to the lid. Your real body has its own shape, with wheels and motor pods. Those aren\'t drawn.')
    Pg['lid'] = enc_w(lid(), 'Lid', 'body', 'lid', 10, 0x8fa8c8, 'A flat plate at 11 units, 77 over the floor. It presses straight down on every stack. How it fastens isn\'t decided.')
    Bb = pi_tris(_pi_mesh('pi_box_base_bored.stl', False)); Lb = pi_tris(_pi_mesh('pi_box_lid_over_header.stl', True))
    case_b, case_l = X.case_tris()
    for p in P:
        k = p['key']
        if k in ('pi_box', 'pca_case'):
            continue
        color = COL.get(p['role']) or PART.get(k) or 0x2f8a58
        if k == 'esp_plugs':
            color = 0x3a3d43
        Pg[k] = enc_w(p['w'], p['label'], 'part' if p['role'] == 'part' else 'brick', p['role'], p['layer'], color, NOTES.get(k, NOTES.get(k.replace('_top', '_box'), p['label'] + '.')))
    Pg['pi_base'] = X.enc_t(Bb, (0, 0), 'Your Pi box: base', 'part', 'part', 2, 0xd9c39e, 'Your rpi5 base, with the rings bored. Not changed.', 16000)
    Pg['pi_lid'] = X.enc_t(Lb, (0, 0), 'Your Pi box: lid', 'part', 'part', 2, 0xc9b48c, 'Your lid, with the notch over the pins. Not changed.', 6000)
    Pg['pi_plugs'] = enc_w(pi_place(X.pi_plugs()), 'Pi\'s Dupont plugs', 'part', 'part', 2, 0x3a3d43, 'All 40 drawn. Their top is your caliper. They stand up through the bite in the sleeve\'s top.')
    Pg['case_b'] = X.enc_t(case_b, ESC_AT[0], 'Your PCA case: base', 'part', 'part', 5, 0xd9c39e, 'Your case, not changed.', None, z=HEIGHT['esc'])
    Pg['case_l'] = X.enc_t(case_l, ESC_AT[0], 'Your PCA case: lid', 'part', 'part', 5, 0xc9b48c, 'Your cut-outs lid, not changed.', None, z=HEIGHT['esc'])
    x0, y0, _ = X.board_xy()
    for i, (q, n) in enumerate(zip(X.pca_plugs(), ('PCA plugs, channels 0 and 1', 'PCA plug, one end', 'PCA plug, the other end'))):
        Pg['pca_plug%d' % i] = X.enc_w(q, ESC_AT[0], n, 'part', 'part', 5, 0x3a3d43, 'A guess at the plug\'s size. Not measured.', z=HEIGHT['esc'])
    bal = balance(info)
    order = ['pi_sleeve', 'pack_box_drive', 'pack_box_pi', 'esc_box_0', 'esc_box_1', 'pca_box', 'esp_box', 'pololu_box', 'ina_box', 'imu_box', 'alarm_box', 'bec_box']
    qty = (('esc_box', 'ESC box', 2), ('esc_top', 'ESC top', 2), ('pack_box', 'Pack box', 2), ('pack_top', 'Pack top', 2), ('pi_sleeve', 'Pi sleeve', 1), ('pi_stop', 'Pi stop', 2), ('pca_box', 'PCA box', 1), ('pca_top', 'PCA top', 1), ('case_base', 'Your PCA case, base', 1), ('case_lid', 'Your PCA case, lid', 1), ('esp_box', 'ESP32 box', 1), ('esp_top', 'ESP32 top', 1),
           ('pololu_box', 'Pololu box', 1), ('pololu_top', 'Pololu top', 1), ('ina_box', 'INA219 box', 1), ('ina_top', 'INA219 top', 1), ('imu_box', 'IMU box', 1), ('imu_top', 'IMU top', 1), ('alarm_box', 'Alarm box', 1), ('alarm_top', 'Alarm top', 1), ('bec_box', 'BEC slot box', 1), ('bec_top', 'BEC slot top', 1), ('spacer_3', 'Spacer, 3 units', 2), ('spacer_5', 'Spacer, 5 units', 1))
    set_ = [dict(name=n, qty=q, **(info.get(k) or dict(time='', g=0.0))) for k, n, q in qty]
    guesses = [('The layout', 'one of many', 'Picked to fit and keep the leads short. The body, lid and wire routes are all guesses to react to.'),
               ('Wire routes', 'along the lanes', 'I drew each one. Bends, plugs and the Y-harness\'s own length aren\'t counted.'),
               ('Small parts', 'listing sizes', 'Pololu, INA219, IMU, alarm and BEC slot aren\'t here yet, so their boxes are drawn from listing sizes. They wait for the real parts.'),
               ('Motors', 'T3\'s axles, centered', 'Rear at x %.0f, front at x %.0f. The first robot\'s axles aren\'t drawn yet.' % AXLES),
               ('Motor wires', 'round the packs', 'They run along the lanes to the side walls. A slot through the floor under the lanes might be shorter.'),
               ('Pack lead', 'the back end', 'Assumed to leave by a short end. Both ends of the box are open, so it can turn round.'),
               ('Pi ribbon', '+%.0f inside the box' % 25.0, 'I guessed the run inside your Pi box, and I don\'t know how the ribbon gets out of it.'),
               ('Body', '250 x 139.5 x %.0f' % (FLOOR + CEILING + SHELL), 'The 250 cap and print 1\'s width. The body\'s real shape, wheels and pods aren\'t drawn.'),
               ('Masses', 'grid_layouts\' list', 'Pi stack and packs from your parts. The small parts are guesses. Bricks from the slicer. The floor, walls, lid and wires aren\'t counted.')]
    meta = dict(floor=FLOOR, ceiling=CEILING, unit=UNIT, wires=[dict(name=w['name'], group=w['group'], color=w['color'], r=w['r'], pts=w['pts'], len=w['len'], budget=w['budget'], bad=w['bad']) for w in W_],
                bal=bal, set=set_, guesses=[dict(name=n, value=v, why=w) for n, v, w in guesses], size=[LEN, WID, FLOOR + CEILING + SHELL], center=[LEN / 2, 0, 42.0], axles=AXLES,
                ribbon_long=RIBBON_LONG, steps=['The boxes\' pegs go in the floor.', 'The parts go in: packs, ESCs, IMU, and your Pi box slides into its sleeve.', 'Their tops go on, and the Pi\'s stops go in.', 'The second layer pegs onto those tops.', 'Its parts go in, including your PCA case.', 'Its tops go on.', 'Spacers fill up to 11 units where a stack comes up short.', 'The wires.', 'The body\'s walls.', 'The lid.'])
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', 'window.PARTS=' + json.dumps(Pg) + ';window.META=' + json.dumps(meta) + ';')
    p = os.path.join(config.TWIN_OUT, 'brain_box_view.html')
    open(p, 'w', encoding='utf-8').write(html)
    print('wrote %s (%.1f MB)' % (p, len(html) / 1e6))
    print('balance:', {k: (np.round(v, 2).tolist() if isinstance(v, list) else round(v, 1)) for k, v in bal.items()})


def _pi_mesh(name, is_lid):
    T = PB.stl(os.path.join(PRINT, name))
    if is_lid:
        T = PB.lid_in_base(T)
    T = np.array(T, float); T[:, :, 0] += X.PI_CX - X.PI_BOX[0] / 2; T[:, :, 1] -= X.PI_BOX[1] / 2; T[:, :, 2] += FLOOR + BOTTOM
    return T


def slice_small():
    res = {}
    os.makedirs(PRINT, exist_ok=True)
    for k in SIZES:
        b, t = small_box(k)
        for nm, w in (('box', b), ('top', t)):
            f = X.flip(w)
            p = os.path.join(PRINT, 'partbox_%s_%s.stl' % (k, nm))
            write_stl(f.val().wrapped, p, lin=0.02, ang=0.2)
            h_ok, msg = health(p)
            r = subprocess.run([sys.executable, os.path.join(config.REPO, 'tools', 'orca.py'), p, '--draft', '--set', 'brim_type=outer_only', '--set', 'brim_width=5', '--set', 'enable_support=0', '--name', 'partbox_%s_%s' % (k, nm)], capture_output=True, text=True)
            m = re.search(r'^\s+(.+?), ([\d.]+) g,', r.stdout, re.M)
            res['%s_%s' % (k, nm)] = dict(time=m.group(1).strip(), g=float(m.group(2))) if m else dict(time='?', g=0.0)
            print('  %-14s %s %s %s' % ('%s_%s' % (k, nm), 'ok' if h_ok else 'BAD', msg[:60], res['%s_%s' % (k, nm)]))
    json.dump(res, open(SLICE, 'w'), indent=1)
    return res


if __name__ == '__main__':
    good, P, W_ = check()
    if 'slice' in sys.argv[1:]:
        print('Slices of the small boxes, draft, not sent to the printer:')
        slice_small()
    info = json.load(open(X.SLICE)) if os.path.exists(X.SLICE) else {}
    if os.path.exists(SLICE):
        info.update(json.load(open(SLICE)))
    if os.path.exists(TEMPLATE):
        page(P, W_, info)
    print('checks:', 'all pass' if good else 'SOMETHING FAILED')
    sys.exit(0 if good else 1)
