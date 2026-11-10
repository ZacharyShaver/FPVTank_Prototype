"""The modular floor's test piece (2026-11-08). Zach: "show me first then we can print". grid_eval.py left two things only a print can
answer: what hole a printed peg really wants, and whether a peg survives the sim's worst load (about 217 N a peg).

    python twin/peg_test.py     # STLs in twin/out/print/, the checks, twin/out/peg_test_view.html (the "Peg Test Piece" artifact)

  floor patch   print 1's 2.6 mm floor, a hole every 15 mm, each row a different size
  ESC frame     round his ESC (his caliper), pegged like every holder would be, printed upside down so the pegs need no supports
  three blocks  to break: a 5 mm peg, a 6 mm peg, and a 5 mm loose pin printed lying down, so its layers run along it
  ESC frame v2  after the print (Zach): "a bit of a pressure fit on the length side", "a bit shorter height", and held "from the other side"

Frame: x along the patch, y across, z up from the floor's underside. * = picked, for Zach to OK or measure.
"""
import base64, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import numpy as np
import cadquery as cq
import config
from export import write_stl, health

PRINT = os.path.join(config.TWIN_OUT, 'print')
TEMPLATE = os.path.join(HERE, 'peg_test_view_template.html')
FLOOR = 2.6                       # print 1's floor
PITCH = 15.0                      # * mm between holes
ROWS = {-22.5: 5.1, -7.5: 5.2, 7.5: 5.3, 22.5: 5.4}   # row's y -> hole diameter: the test itself. 5.3 is his 0.15 a side slide rule
COLS = (-30.0, -15.0, 0.0, 15.0, 30.0)
BIG_HOLE, BIG_AT = 6.3, (38.5, 0.0)   # for the 6 mm peg
PATCH_X, PATCH_Y = (-46.0, 46.0), (-45.0, 30.0)
PEG, PEG_LONG, TIP = 5.0, FLOOR - 0.2, 0.4   # * the peg stops 0.2 short of the underside, its tip chamfered
ESC = (45.0, 24.0, 34.0)          # his caliper 2026-10-11: long, thick, tall, stood on edge as the sim has it
FIT, WALL = 0.25, 1.2             # * round the ESC (print 1's 0.5 read "a bit extra room"); wall
WALL_H, END_H = 17.0, 8.0         # * side walls about half the ESC; the ends drop to this, for the leads
GAP_Y = (-11.0, 2.5)              # * the gap in each end wall for the leads, across the frame. Where his leads exit isn't known
POST = 7.0                        # * mm
POST_X, POST_Y = 30.0, 7.5        # * the pegs, from the frame's centre: 60 apart, on one row
BLOCK, BLOCK_H = 16.0, 8.0        # * the blocks to break
V2_LONG_FIT, V2_THICK_FIT = 0.0, FIT   # frame v2: no clearance on the length, his press fit (his caliper's 45.0 drawn as is); the thickness unchanged
V2_H, V2_LEAD = 12.0, 0.6              # * the shorter walls; a chamfer at the mouth, which prints on the bed where the first layer squashes in
HOLE_PICK = 5.1                        # his pick


def cyl(d, z0, z1, x=0.0, y=0.0):
    return cq.Workplane('XY').workplane(offset=z0).center(x, y).circle(d / 2).extrude(z1 - z0)


def rect(x0, x1, y0, y1, z0, z1):
    return cq.Workplane('XY').workplane(offset=z0).center((x0 + x1) / 2, (y0 + y1) / 2).rect(x1 - x0, y1 - y0).extrude(z1 - z0)


def peg(d, x=0.0, y=0.0):
    """a peg down from the floor's top, its tip chamfered"""
    p = cyl(d, FLOOR - PEG_LONG, FLOOR, x, y)
    return p.faces('<Z').chamfer(TIP)


def patch():
    P = rect(*PATCH_X, *PATCH_Y, 0, FLOOR)
    for y, d in ROWS.items():
        for x in COLS:
            P = P.cut(cyl(d, -1, FLOOR + 1, x, y))           # a cut overruns both faces
        P = P.cut(cq.Workplane('XY').workplane(offset=FLOOR - 0.4).center(-39.5, y).text('%.1f' % d, 5.0, 1.0, combine=False, kind='bold'))
    P = P.cut(cyl(BIG_HOLE, -1, FLOOR + 1, *BIG_AT))
    P = P.cut(cq.Workplane('XY').workplane(offset=FLOOR - 0.4).center(39.0, 8.5).text('%.1f' % BIG_HOLE, 4.0, 1.0, combine=False, kind='bold'))
    return P


def frame():
    """seated on the floor at row y = 0: centre at (0, -POST_Y), the pegs on the row"""
    a, b = ESC[0] + 2 * FIT, ESC[1] + 2 * FIT
    z0, z1 = FLOOR, FLOOR + WALL_H
    F = rect(-a / 2 - WALL, a / 2 + WALL, -b / 2 - WALL, b / 2 + WALL, z0, z1)
    F = F.cut(rect(-a / 2, a / 2, -b / 2, b / 2, z0 - 1, z1 + 1))
    for s in (-1, 1):                                       # the lead gaps: the end wall drops to END_H across GAP_Y
        F = F.cut(rect(*sorted((s * (a / 2 - 0.5), s * (a / 2 + WALL + 0.5))), GAP_Y[0], GAP_Y[1], z0 + END_H, z1 + 1))
    for s in (-1, 1):                                       # an ear out to each post, full height, so it prints from the bed
        F = F.union(rect(*sorted((s * (a / 2 + WALL - 0.2), s * POST_X)), POST_Y - POST / 2, POST_Y + POST / 2, z0, z1))
        F = F.union(cyl(POST, z0, z1, s * POST_X, POST_Y))
        F = F.union(peg(PEG, s * POST_X, POST_Y))
    return F.translate((0, -POST_Y, 0))


def esc_box():
    a, b, h = ESC
    return rect(-a / 2, a / 2, -b / 2, b / 2, FLOOR, FLOOR + h).translate((0, -POST_Y, 0))


def frame2():
    """frame v2, seated at row y = 0, centred on its row: solid ends (his leads leave by a long face, from the photos), a press fit on the length"""
    a, b = ESC[0] + 2 * V2_LONG_FIT, ESC[1] + 2 * V2_THICK_FIT
    z0, z1 = FLOOR, FLOOR + V2_H
    F = rect(-a / 2 - WALL, a / 2 + WALL, -b / 2 - WALL, b / 2 + WALL, z0, z1)
    F = F.cut(rect(-a / 2, a / 2, -b / 2, b / 2, z0 - 1, z1 + 1))
    mouth = cq.Workplane('XY').workplane(offset=z1 - V2_LEAD).rect(a, b).workplane(offset=V2_LEAD + 0.01).rect(a + 2 * V2_LEAD + 0.02, b + 2 * V2_LEAD + 0.02).loft()
    F = F.cut(mouth)
    for s in (-1, 1):
        F = F.union(rect(*sorted((s * (a / 2 + WALL - 0.2), s * POST_X)), -POST / 2, POST / 2, z0, z1))
        F = F.union(cyl(POST, z0, z1, s * POST_X, 0.0))
        F = F.union(peg(PEG, s * POST_X, 0.0))
    return F


def esc2():
    a, b, h = ESC
    return rect(-a / 2, a / 2, -b / 2, b / 2, FLOOR, FLOOR + h)


def block(d=None):
    """a block to break: a peg of d, or (d None) a through hole for the loose pin"""
    B = rect(-BLOCK / 2, BLOCK / 2, -BLOCK / 2, BLOCK / 2, FLOOR, FLOOR + BLOCK_H)
    if d:
        return B.union(peg(d))
    return B.cut(cyl(5.3, FLOOR - 1, FLOOR + BLOCK_H + 1))


def pin():
    """the loose pin, standing in its hole: 5 mm, from 0.2 over the floor's underside to the block's top. Printed lying on a 0.4 flat"""
    p = cyl(PEG, 0.2, FLOOR + BLOCK_H - 0.2)
    return p.faces('<Z').chamfer(TIP).faces('>Z').chamfer(TIP)


def vol(a, b):
    """the overlap of two pieces, mm3, exact"""
    try:
        return float(a.intersect(b).val().Volume())
    except Exception:
        return 0.0


def check():
    P, F, E = patch(), frame(), esc_box()
    ok = True

    def line(what, good, got):
        nonlocal ok
        ok &= good
        print('  %-58s %s %s' % (what, got, 'ok' if good else 'WRONG'))
    print('Seated, each row (the pegs on their row):')
    for y, d in ROWS.items():
        v = vol(P, F.translate((0, y, 0)))
        line('frame against the patch, row %.1f mm' % d, v < 1e-3, '%.3f mm3' % v)
        v2 = vol(P, E.translate((0, y, 0)))
        line('ESC against the patch', v2 < 1e-3, '%.3f mm3' % v2)
    v = vol(F, E); line('ESC against the frame', v < 1e-3, '%.3f mm3' % v)
    v = vol(P, block(6.0).translate((*BIG_AT, 0))); line('6 mm peg in its 6.3 hole, block on the patch', v < 1e-3, '%.3f mm3' % v)
    v = vol(P, block(None).translate((0, 22.5, 0))); line('pin block on the patch', v < 1e-3, '%.3f mm3' % v)
    v = vol(block(None), pin()); line('pin in its block', v < 1e-3, '%.3f mm3' % v)
    print('Controls, which must read above zero:')
    tight = rect(*PATCH_X, *PATCH_Y, 0, FLOOR).cut(cyl(4.8, -1, FLOOR + 1, POST_X, 7.5)).cut(cyl(4.8, -1, FLOOR + 1, -POST_X, 7.5))
    v = vol(tight, F.translate((0, 7.5, 0))); line('the pegs in 4.8 holes', v > 1, '%.2f mm3' % v)
    v = vol(P, F.translate((PITCH / 3, 7.5, 0))); line('the frame 5 mm off its holes', v > 1, '%.2f mm3' % v)
    big_esc = rect(-23, 23, -12.5, 12.5, FLOOR, FLOOR + 34).translate((0, -POST_Y, 0))
    v = vol(F, big_esc); line('an ESC 1 mm bigger', v > 1, '%.2f mm3' % v)
    print('Frame v2:')
    G, E2 = frame2(), esc2()
    for y, d in ROWS.items():
        v = vol(P, G.translate((0, y, 0)))
        line('v2 against the patch, row %.1f mm' % d, v < 1e-3, '%.3f mm3' % v)
    v = vol(G, E2); line('your ESC, exactly 45.0, in v2', v < 1e-3, '%.3f mm3' % v)
    longer = rect(-22.7, 22.7, -12, 12, FLOOR, FLOOR + 34)
    v = vol(G, longer); line('control: an ESC 0.4 longer reads as the press', v > 1, '%.2f mm3' % v)
    v = vol(P, G.translate((PITCH / 3, -22.5, 0))); line('control: v2 5 mm off its holes', v > 1, '%.2f mm3' % v)
    print('Stops short of the underside: peg tip at z %.1f, floor underside at 0' % (FLOOR - PEG_LONG))
    bb = F.val().BoundingBox()
    print('Frame: %.1f x %.1f x %.1f overall, %.1f across the ESC' % (bb.xlen, bb.ylen, bb.zlen, ESC[1] + 2 * (FIT + WALL)))
    return ok


def printed():
    """print orientation, each on the bed at z 0: the patch floor down, the frame and blocks upside down, the pin on its side"""
    def bed(w):
        return w.translate((0, 0, -w.val().BoundingBox().zmin))
    flip = lambda w: bed(w.rotate((0, 0, 0), (1, 0, 0), 180))
    p = pin().rotate((0, 0, 0), (0, 1, 0), 90)
    p = p.cut(rect(-20, 20, -5, 5, -2.5 - 1, -2.5 + 0.4))            # the flat, 0.4 deep, along its length
    return dict(patch=bed(patch()), frame=flip(frame()), frame_v2=flip(frame2()), peg5=flip(block(PEG)), peg6=flip(block(6.0)), pinblock=bed(block(None)), pin=bed(p))


def mesh_of(w, tol=0.03):
    V, T = w.val().tessellate(tol, 0.2)
    return np.array([[v.x, v.y, v.z] for v in V], '<f4'), np.array(T, '<u4')


def enc(w, label, group, color, note):
    V, F = mesh_of(w)
    return dict(label=label, group=group, color=color, note=note, v=base64.b64encode(V.tobytes()).decode(), f=base64.b64encode(F.tobytes()).decode())


def page(info):
    shift = lambda w, x, y: w.translate((x, y, 0))
    SIDE = dict(peg5=(-78.0, 22.0), peg6=(-78.0, -2.0), pinblock=(-78.0, -26.0))     # where the blocks wait beside the patch
    SEAT = dict(peg5=(-30.0, -22.5), peg6=BIG_AT, pinblock=(0.0, -22.5))             # and where each one goes
    P = dict(
        patch=enc(patch(), 'Floor patch', 'floor', 0xb9c4d0, 'Printed. Your 2.6 mm floor with a hole every %.0f mm. Your verdict: 5.1 fits best, slightly tight with a little snap. 5.2 works, a bit looser. 5.3 and 5.4 fall out when tipped. The one big hole is 6.3, for the 6 mm peg.' % PITCH),
        frame=enc(frame2(), 'ESC frame v2 (printed)', 'held', 0xe0b35c, 'Printed: "this fits fine enough". The opening is your 45.0 long with no clearance, for the pressure fit you asked for. Walls %.0f mm tall, down from 17. The ends are solid now, because your leads leave by a long face. The thickness is unchanged, %.2f a side. The mouth has a %.1f mm chamfer to lead the ESC in.' % (V2_H, V2_THICK_FIT, V2_LEAD)),
        frame_v1=enc(frame(), 'ESC frame v1 (printed)', 'held', 0xa9a39a, 'What you printed: 0.25 clearance all round, walls 17 tall, gaps in the end walls. Superseded by v2, for comparing.'),
        esc=enc(esc2(), 'Your ESC', 'held', 0x4a78b5, 'Your caliper: 45 long, 34 wide, 24 tall, stood on edge as the sim has it. No model exists, so this is a plain box with no wires: the leads your frame wedges against are not drawn. You do not print this one.'),
        peg5=enc(shift(block(PEG), *SIDE['peg5']), 'Small-peg block', 'side', 0xc98a6b, 'The same 5 mm peg as the ESC frame, on a block. It goes in any row; use 5.1, your pick. It tests the peg the frame relies on, printed standing up, so a side load crosses its layer lines.'),
        peg6=enc(shift(block(6.0), *SIDE['peg6']), 'Big-peg block', 'side', 0xc98a6b, 'A 6 mm peg, 44 %% more area. It only fits the one 6.3 hole, near the edge by the rows. If the 5 mm peg breaks too easily, this says whether a bigger one is enough.' % ()),
        pinblock=enc(shift(block(None), *SIDE['pinblock']), 'Block with a hole through it', 'side', 0xc98a6b, 'No peg. Set it on the patch over a 5.1 hole, and drop the loose pin down through both.'),
        pin=enc(shift(pin(), *SIDE['pinblock']), 'Loose pin', 'side', 0x8fb37a, 'The small 5 mm stick with one flat side, about 10 mm long. It goes through the block with the hole and into a 5.1 hole. Printed lying down, so its layers run along it and a side load should not split them.'))
    meta = dict(rows={str(k): v for k, v in ROWS.items()}, info=info, side=SIDE, seat=SEAT, esc_v1_y=-POST_Y,
                notes={'5.1': 'Your pick: fits best, slightly tight, with a little snap.', '5.2': 'Works, a bit looser.', '5.3': 'Falls out when tipped.', '5.4': 'Falls out when tipped.'},
                guesses=[
        dict(name='Length fit', value='45.0, no clearance', why='Your caliper drawn as is. Printed holes came out tight on the patch, so this should press. If it binds, I add 0.1.'),
        dict(name='Wall height', value='%.0f, down from 17' % V2_H, why='My pick for "a bit shorter". The sim drop test ran with this height.'),
        dict(name='Thickness fit', value='0.25 a side', why='Unchanged. You asked for the press on the length only.'),
        dict(name='Other side', value='the lid\'s TPU pad', why='How I read "hold it from the other side": pressing down on top of the ESC. Tell me if you meant something else.'),
        dict(name='Ends', value='solid', why='From your photos, the leads leave by a long face. You haven\'t said so yet.'),
        dict(name='Mouth chamfer', value='0.6', why='My pick, so the first layer\'s squash doesn\'t block the opening.'),
        dict(name='Hole spacing', value='15', why='My pick. Sets how far a holder can shift, not how big it is.'),
        dict(name='Peg and post', value='5 x %.1f, post 7' % PEG_LONG, why='My picks, the same as v1. They fit your 5.1 row.'),
        dict(name='Break target', value='about 217 N, 22 kg', why='From the sim: a 1 m drop onto hard ground, no tyres, four pegs on a pack. Harsher than the robot will see.')])
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', 'window.PARTS=' + json.dumps(P) + ';window.META=' + json.dumps(meta) + ';')
    p = os.path.join(config.TWIN_OUT, 'peg_test_view.html')
    open(p, 'w', encoding='utf-8').write(html)
    print('wrote %s (%.1f MB)' % (p, len(html) / 1e6))


if __name__ == '__main__':
    good = check()
    print('Print pieces:')
    os.makedirs(PRINT, exist_ok=True)
    paths = []
    for k, w in printed().items():
        path = os.path.join(PRINT, 'peg_test_%s.stl' % k)
        write_stl(w.val().wrapped, path, lin=0.02, ang=0.2)
        h_ok, msg = health(path); good &= bool(h_ok)
        bb = w.val().BoundingBox()
        print('  %-10s %5.1f x %5.1f x %5.1f  %s %s' % (k, bb.xlen, bb.ylen, bb.zlen, 'ok ' if h_ok else 'BAD', msg))
        paths.append(path)
    info = json.load(open(os.path.join(config.TWIN_OUT, 'peg_test_slice.json'))) if os.path.exists(os.path.join(config.TWIN_OUT, 'peg_test_slice.json')) else {}
    if os.path.exists(TEMPLATE):
        page(info)
    print('checks:', 'all pass' if good else 'SOMETHING FAILED')
    sys.exit(0 if good else 1)
