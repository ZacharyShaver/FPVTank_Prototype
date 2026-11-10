"""The holders' joint, redrawn round print noise (2026-11-09). The boxes of part_boxes.py stay; how they join changes.

Zach's bench on the first box plates: an ESC top "a tax too tight", and "the pla inside of the connection holes and stubs can warp or have defects rendering it impossible
to assemble". print_noise.py showed why: friction pegs need every printed feature right within about 0.05 mm. His call: "yes draw it no boxes dont have to hold without a lid".

    python twin/spring_stack.py          # builds, checks with controls, STLs in twin/out/print/, twin/out/spring_stack_view.html ("Spring Stack")
    python twin/spring_stack.py slice    # the same, and slices the PLA pieces (draft, not printed) into twin/out/spring_stack_slice.json
    python twin/spring_stack.py page     # only the page

The rules:
  locate   two slim pegs on one diagonal, loose in the floor's 5.1 holes. The other pegs are slimmer still and only meet a crash
  seat     the box's flat bottom carries the weight
  hold     a soft clip (TPU) on each stack, squeezed by a flat lid. Its travel is several times the print noise
  stop     squeezed flat, the clip's solid body takes a crash, before the pegs can lift out

Drawn on one stack, ESC + PCA, on the patch he has, under a hoop that stands in for the lid. The other boxes follow once this one has been on the bench.
Supersedes, for these pieces: partbox_esc_box, partbox_esc_top and partbox_pca_box (six and four friction pegs, a rigid pad). partbox_pca_top and his case are used as they are.

Frame: part_boxes.py's. x along the ESC, y across, z up from the floor's underside. * = picked, for Zach to OK or measure.
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
from peg_test import rect, cyl, vol, FLOOR
import part_boxes as BX
from part_boxes import shift
import print_noise as PN

PRINT = BX.PRINT
TEMPLATE = os.path.join(HERE, 'spring_stack_view_template.html')
SLICE = os.path.join(config.TWIN_OUT, 'spring_stack_slice.json')

LOC, BACK = 4.6, 4.0              # * peg diameters in the 5.1 holes: 0.25 and 0.55 of room a side, picked on the noise screen (4.7 and 4.4 jammed more). His bench: a 5.0 peg in the 5.4 row, 0.2 a side, "will fall out when tipped"
CLIP_D = 4.6                      # * the clip's depth. It prints lying on this face, so its outline is drawn by the nozzle
CLIP_L = 21.6                     # its length: inside the ring under the ESC's top (21.9), 0.15 a side
CLIP_BODY = 2.25                  # * its solid part, which is the stop
CLIP_RISE = 1.5                   # * how far the blades stand over the body, free: the travel
SQUEEZE = 0.75                    # * how far a lid presses them as drawn, so a stack may be 0.75 tall or short
BLADES = (0.8, 1.2, 1.6)          # * blade thickness: the test strip's three
BLADE = 1.2                       # * the one drawn
WEB = 0.8                         # * half the web between the two blades
PRONG = 3.0                       # * a prong across; CLIP_D deep. Corner to corner 5.49 in a 5.1 hole: the corners squeeze, soft
E_TPU = 40.0                      # * MPa, a guess for printed 95A. Half to double
ROOM = (FLOOR + BX.ESC_RIM) - BX.ESC_TOP          # 3.0: between the ESC and its top's underside. The clip lives in it
LID_Z = FLOOR + BX.CEILING + CLIP_BODY + CLIP_RISE - SQUEEZE     # the lid's underside: the same 3.0 over the stack
AT = (0.0, -15.0)                 # on the patch: the pegs land in its 5.1 and 5.2 rows
H_ESC = BX.HEIGHT['esc']
HOOP_WALL, HOOP_DEEP, HOOP_SIDE = 4.0, 16.0, 0.5  # * the test hoop: a closed ring round the patch and the stack
assert abs(CLIP_BODY + CLIP_RISE - SQUEEZE - ROOM) < 1e-9


def peg(d, x, y, z):
    return cyl(d, z - BX.PEG_LONG, z + 0.5, x, y).faces('<Z').chamfer(BX.TIP)


def with_pegs(F, pegs, z=FLOOR):
    """the two on one diagonal locate, the rest back them up"""
    P = sorted(pegs)
    for i, (x, y) in enumerate(P):
        F = F.union(peg(LOC if i in (0, len(P) - 1) else BACK, x, y, z))
    return F


def esc_box():
    return with_pegs(BX.esc_box(pegs=()), BX.ESC_PEGS)


def esc_top():
    """no pad: the clip under it does that job"""
    return BX.esc_top(pads=())


def pca_box():
    return with_pegs(BX.pca_box(pegs=()), BX.BOARD_PEGS)


def outline(pts):
    """a solid from a (y, z) outline, CLIP_D deep along x"""
    P = [cq.Vector(-CLIP_D / 2, y, z) for y, z in pts]
    return BX.W(cq.Solid.extrudeLinear(cq.Wire.makePolygon(P + [P[0]]), [], cq.Vector(CLIP_D, 0, 0)))


def clip(t=BLADE):
    """the soft clip, its seat at z 0, prongs down, blades up. Each blade leans out at 45 degrees from the floor of a notch t deep, so squeezed flat it lies in the
    notch and the body's top is the stop"""
    w, rise, h, d = t * math.sqrt(2), CLIP_RISE + t, CLIP_L / 2, CLIP_D / 2
    zb = CLIP_BODY - t
    y1 = WEB + w + rise * math.sqrt(2) + 0.3
    F = rect(-d, d, -h, h, 0.0, CLIP_BODY)
    for s in (-1, 1):
        F = F.cut(rect(-d - 1, d + 1, *sorted((s * WEB, s * y1)), zb, CLIP_BODY + 1))
    for s in (-1, 1):
        pts = [(s * (WEB - 0.2), zb - 0.2), (s * (WEB - 0.2 + w), zb - 0.2), (s * (WEB + w + rise), zb + rise), (s * (WEB + rise), zb + rise)]
        F = F.union(outline(pts if s > 0 else pts[::-1]))
        F = F.union(rect(-d, d, *sorted((s * (7.5 - PRONG / 2), s * (7.5 + PRONG / 2))), -BX.PEG_LONG, 0.3))
    return F


def clip_force(t, d):
    """N at d of squeeze: two blades as beams bent at 45 degrees. Rough, and E is a guess: it sizes the test strip, nothing more"""
    L = (CLIP_RISE + t) * math.sqrt(2)
    return 2 * (2 * E_TPU * CLIP_D * t ** 3 / (4 * L ** 3)) * d


def clip_at(z, x=0.0, up=True, t=BLADE):
    c = clip(t)
    if not up:
        c = c.rotate((0, 0, 0), (0, 1, 0), 180)
    return shift(c, AT[0] + x, AT[1], z)


def hoop():
    """the test's stand-in for the lid: the patch sits on its bottom bar, and its top bar is the lid's underside. It slides on along x, the way the blades run"""
    y0, y1, d = PT.PATCH_Y[0] - HOOP_SIDE, PT.PATCH_Y[1] + HOOP_SIDE, HOOP_DEEP / 2
    F = rect(-d, d, y0 - HOOP_WALL, y1 + HOOP_WALL, -HOOP_WALL, LID_Z + HOOP_WALL)
    F = F.cut(rect(-d - 1, d + 1, y0, y1, 0.0, LID_Z))
    for s in (-1, 1):                                                    # a lead-in under the top bar, so it rides up onto the blades
        P = [cq.Vector(s * (d + 0.1), y0 - 0.1, LID_Z - 0.1), cq.Vector(s * (d - 1.6), y0 - 0.1, LID_Z - 0.1), cq.Vector(s * (d + 0.1), y0 - 0.1, LID_Z + 1.6)]
        F = F.cut(BX.W(cq.Solid.extrudeLinear(cq.Wire.makePolygon((P if s > 0 else P[::-1]) + [P[0] if s > 0 else P[-1]]), [], cq.Vector(0, y1 - y0 + 0.2, 0))))
    return F


def build():
    A = dict(patch=PT.patch(), esc_box=shift(esc_box(), *AT), esc=shift(BX.esc_solid(), *AT), esc_top=shift(esc_top(), *AT),
             clip_esc=clip_at(FLOOR + BX.ESC_RIM, up=False), pca_box=shift(pca_box(), *AT, z=H_ESC), case=shift(BX.case_solid(), *AT, z=H_ESC),
             pca_top=shift(BX.pca_top(), *AT, z=H_ESC), clip_top=clip_at(FLOOR + BX.CEILING), hoop=hoop())
    return A


# ---------------------------------------------------------------- the checks
def slide(P, box, step=0.02, far=0.6):
    """how far the box slides along x before a peg touches a hole's wall"""
    for d in np.arange(step, far, step):
        if vol(P, shift(box, x=float(d))) > 1e-4:
            return float(d)
    return far


def noise():
    """the screen, on these two boxes: friction pegs as printed, against two that locate and the rest clear"""
    rows = []
    for key, name, n in (('esc', 'ESC box', 6), ('board', 'PCA box', 4)):
        xy = PN.JOINTS[key]
        rows.append(dict(name='%s, %d friction pegs' % (name, n), new=False, share=[PN.share(xy, 0.0, s, PN.PRESS) for s in (0.05, 0.10, 0.15)]))
        rows.append(dict(name='%s, 2 locate + %d clear' % (name, n - 2), new=True, share=[PN.share(xy, PN.two_locate, s) for s in (0.05, 0.10, 0.15)]))
    return rows


def check(A):
    ok = True

    def line(what, good, got=''):
        nonlocal ok
        ok &= bool(good)
        print('  %-84s %s %s' % (what, got, 'ok' if good else 'WRONG'))

    P = A['patch']
    print('--- loose pegs')
    v = vol(P, A['esc_box']); line('the ESC box\'s pegs in the patch\'s 5.1 and 5.2 rows', v < 1e-3, '%.3f mm3' % v)
    v = vol(P, shift(A['esc_box'], x=5.0)); line('control: 5 mm off its holes', v > 1, '%.2f mm3' % v)
    r = slide(P, A['esc_box']); line('it slides before a peg touches: the room drawn, %.2f' % ((BX.HOLE - LOC) / 2), abs(r - (BX.HOLE - LOC) / 2) < 0.03, '%.2f mm' % r)
    r = slide(P, shift(BX.esc_box(), *AT)); line('control: the six-peg box he printed slides only its 0.05', r < 0.08, '%.2f mm' % r)
    v = vol(A['pca_box'], A['esc_top']); line('the PCA box on the ESC\'s top', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(A['pca_box'], x=5.0), A['esc_top']); line('control: 5 mm off', v > 1, '%.2f mm3' % v)
    print('--- the parts in their boxes')
    v = vol(A['esc_box'], A['esc']); line('the ESC in its box, frame v2\'s opening', v < 1e-3, '%.3f mm3' % v)
    v = vol(A['esc_top'], A['esc']); line('the top, with no pad, clears the ESC', v < 1e-3, '%.3f mm3' % v)
    v = vol(shift(A['esc_top'], z=-ROOM - 0.5), A['esc']); line('control: the top %.1f lower sits in the ESC' % (ROOM + 0.5), v > 1, '%.2f mm3' % v)
    v = vol(A['pca_box'], A['case']); line('his case in the PCA box', v < 1e-3, '%.3f mm3' % v)
    print('--- the clip under the ESC\'s top')
    v = vol(A['clip_esc'], A['esc_top']); line('only its prongs\' corners squeeze into the top\'s holes', 0.02 < v < 8, '%.2f mm3' % v)
    v2 = vol(shift(A['clip_esc'], y=1.0), A['esc_top']); line('control: 1 mm across, it runs into the ring', v2 > v + 1, '%.2f mm3' % v2)
    sq = BX.ESC_TOP - A['clip_esc'].val().BoundingBox().zmin
    line('its blades reach into the ESC by the squeeze, %.2f' % SQUEEZE, abs(sq - SQUEEZE) < 1e-6, '%.2f mm' % sq)
    v = vol(shift(A['clip_esc'], z=SQUEEZE + 0.01), A['esc']); line('control: lifted by the squeeze, it only touches', v < 1e-3, '%.3f mm3' % v)
    print('--- the clip on the stack, under the lid')
    v = vol(A['clip_top'], A['pca_top']); line('only its prongs\' corners squeeze into the PCA top\'s holes', 0.02 < v < 8, '%.2f mm3' % v)
    top = A['pca_top'].val().BoundingBox().zmax
    line('the stack\'s top is at %d units' % BX.CEILING_UNITS, abs(top - FLOOR - BX.CEILING) < 1e-6, '%.1f' % (top - FLOOR))
    sq = A['clip_top'].val().BoundingBox().zmax - LID_Z
    line('its blades reach into the hoop\'s bar by the squeeze, %.2f' % SQUEEZE, abs(sq - SQUEEZE) < 1e-6, '%.2f mm' % sq)
    v = vol(A['clip_top'], A['hoop']); line('so the bar squeezes it', v > 0.5, '%.2f mm3' % v)
    v = vol(shift(A['clip_top'], z=-SQUEEZE - 0.01), A['hoop']); line('control: lowered by the squeeze, it only touches', v < 1e-3, '%.3f mm3' % v)
    print('--- the stop')
    worst = CLIP_RISE                                                    # a stack short by the whole squeeze: the clip only touching, all its travel left
    line('squeezed flat, the stack has lifted %.2f as drawn, %.2f at worst; the pegs\' straight part is %.1f' % (CLIP_RISE - SQUEEZE, worst, BX.PEG_LONG - BX.TIP), worst < BX.PEG_LONG - BX.TIP)
    line('control: a 2.5 travel would let them out', not (2.5 < BX.PEG_LONG - BX.TIP))
    print('--- the hoop')
    rigid = BX.many([A[k] for k in ('patch', 'esc_box', 'esc_top', 'pca_box', 'pca_top')])
    v = vol(A['hoop'], rigid); line('it clears the patch and the stack', v < 1e-3, '%.3f mm3' % v)
    v = vol(A['hoop'], shift(rigid, z=4.0)); line('control: a stack 4 mm taller is in the bar', v > 1, '%.2f mm3' % v)
    print('--- the clip\'s force: an estimate, E guessed at %.0f MPa' % E_TPU)
    for t in BLADES:
        print('  blade %.1f: about %.1f N as drawn, %.1f N squeezed flat' % (t, clip_force(t, SQUEEZE), clip_force(t, CLIP_RISE)))
    print('--- print noise, the share that goes together at 0.05, 0.10, 0.15 mm of error a feature')
    N = noise()
    for r in N:
        print('  %-34s %s' % (r['name'], '  '.join('%3.0f %%' % (100 * x) for x in r['share'])))
    line('the two-peg joint beats the friction pegs at every error', all(N[i + 1]['share'][j] >= N[i]['share'][j] for i in (0, 2) for j in range(3)))
    return ok, N


# ---------------------------------------------------------------- the print files
def lay_clips():
    """the test strip: two of each blade, lying on their sides, thin to thick along x"""
    out, x = None, 0.0
    for t in BLADES:
        for _ in range(2):
            c = clip(t).rotate((0, 0, 0), (0, 1, 0), 90)
            b = c.val().BoundingBox()
            c = c.translate((x - b.xmin, 0, -b.zmin))
            out = c if out is None else out.add(c)
            x += b.xlen + 3.0
    return out


def export():
    good, paths = True, {}
    os.makedirs(PRINT, exist_ok=True)
    h = hoop().rotate((0, 0, 0), (0, 1, 0), 90)
    items = dict(esc_box=BX.flip(esc_box()), esc_top=BX.flip(esc_top()), pca_box=BX.flip(pca_box()), hoop=h.translate((0, 0, -h.val().BoundingBox().zmin)))
    for k, w in items.items():
        p = os.path.join(PRINT, 'spring_%s.stl' % k)
        write_stl(w.val().wrapped, p, lin=0.02, ang=0.2)
        h_ok, msg = health(p); good &= bool(h_ok)
        b = w.val().BoundingBox()
        print('  %-10s %5.1f x %5.1f x %5.1f  %s %s' % (k, b.xlen, b.ylen, b.zlen, 'ok ' if h_ok else 'BAD', msg))
        paths[k] = p
    p = os.path.join(PRINT, 'spring_clip_strip_TPU.stl')
    S = lay_clips()
    write_stl(cq.Compound.makeCompound(S.vals()).wrapped, p, lin=0.01, ang=0.2)
    h_ok, msg = health(p)
    b = cq.Compound.makeCompound(S.vals()).BoundingBox()
    print('  %-10s %5.1f x %5.1f x %5.1f  %s (six bodies, as meant)' % ('clip strip', b.xlen, b.ylen, b.zlen, msg))
    return good, paths


def slice_all(paths):
    res = {}
    for k, p in paths.items():
        r = subprocess.run([sys.executable, os.path.join(config.REPO, 'tools', 'orca.py'), p, '--draft', '--set', 'brim_type=outer_only', '--set', 'brim_width=5',
                            '--set', 'enable_support=0', '--name', 'spring_' + k], capture_output=True, text=True)
        m = re.search(r'^\s+(.+?), ([\d.]+) g,', r.stdout, re.M)
        res[k] = dict(time=m.group(1).strip(), g=float(m.group(2))) if m else dict(time='?', g=0.0, err=(r.stdout + r.stderr)[-300:])
        print('  %-10s %s' % (k, res[k]))
    json.dump(res, open(SLICE, 'w'), indent=1)
    return res


# ---------------------------------------------------------------- the page
def page(A, N, info):
    BOX, TOP, PART, CASEC, CLIP, HOOP = 0xe0b35c, 0x5fb3a1, 0x4a78b5, 0xd9c39e, 0xd9604a, 0x8f8fd6
    rl, rb = (BX.HOLE - LOC) / 2, (BX.HOLE - BACK) / 2
    P = dict(patch=BX.enc_w(A['patch'], (0, 0), 'Your floor patch', 'all', 'floor', 1, 0xb9c4d0, 'The patch you already printed, as it is. The stack sits on its 5.1 and 5.2 rows.', tol=0.1))
    P['esc_box'] = BX.enc_w(A['esc_box'], (0, 0), 'ESC box, loose pegs', 'all', 'box', 1, BOX, 'The same box, with new pegs. Two on one diagonal are %.1f and locate it, with %.2f of room a side. The other four are %.1f and stand %.2f clear, so they can\'t jam; they only meet a crash. To print.' % (LOC, rl, BACK, rb))
    P['esc'] = BX.enc_w(A['esc'], (0, 0), 'Your ESC', 'all', 'part', 2, PART, 'Your caliper: 45 x 24 x 34, stood on edge. One of your two is a hair taller.')
    P['esc_top'] = BX.enc_w(A['esc_top'], (0, 0), 'ESC top, no pad', 'all', 'top', 3, TOP, 'The same top with the rigid pad taken off. That leaves %.1f over the ESC for the clip. To print.' % ROOM)
    P['clip_esc'] = BX.enc_w(A['clip_esc'], (0, 0), 'Clip on the ESC', 'all', 'clip', 3, CLIP, 'The soft clip, plugged into the top\'s two middle holes from below, blades down. It presses the ESC, squeezed %.2f as drawn, with %.2f more before it\'s solid.' % (SQUEEZE, CLIP_RISE - SQUEEZE), tol=0.02)
    P['pca_box'] = BX.enc_w(A['pca_box'], (0, 0), 'PCA box, loose pegs', 'all', 'box', 4, BOX, 'The same box, with two %.1f pegs that locate and two %.1f that stand clear. To print.' % (LOC, BACK))
    Bo, Lo = BX.case_tris()
    P['case_base'] = BX.enc_t(Bo, AT, 'Your PCA case, base', 'all', 'part', 5, CASEC, 'Your own case, not changed.', z=H_ESC)
    P['case_lid'] = BX.enc_t(Lo, AT, 'Your PCA case, lid', 'all', 'part', 5, 0xc9b48c, 'Your own lid, not changed.', z=H_ESC)
    P['pca_top'] = BX.enc_w(A['pca_top'], (0, 0), 'PCA top', 'all', 'top', 6, TOP, 'The top you already printed, as it is.')
    P['clip_top'] = BX.enc_w(A['clip_top'], (0, 0), 'Clip under the lid', 'all', 'clip', 6, CLIP, 'The same clip, plugged into the top of the stack, blades up. The lid squeezes it %.2f. It prints lying on its side, so the blades are drawn by the nozzle and need no supports.' % SQUEEZE, tol=0.02)
    P['hoop'] = BX.enc_w(A['hoop'], (0, 0), 'Test hoop', 'all', 'lid', 7, HOOP, 'A ring for the bench test. Your patch sits on its bottom bar, and its top bar is where the robot\'s lid would be: %.1f over the stack. It slides on from the end. To print.' % ROOM, tol=0.1)
    steps = ['The ESC box drops onto your patch. Its pegs are loose, so nothing presses.', 'The ESC clicks in past the ridges, as it does now.',
             'The ESC\'s top goes on, with a soft clip plugged in under it. The clip presses the ESC down.', 'The PCA box drops onto that top. Loose pegs again.',
             'Your case snaps in.', 'The PCA\'s top goes on, and a second clip plugs into it, blades up.',
             'The hoop slides on from the end. Its top bar stands in for the lid and squeezes the clip %.2f mm.' % SQUEEZE]
    f = {t: (clip_force(t, SQUEEZE), clip_force(t, CLIP_RISE)) for t in BLADES}
    answers = [('How does it get in?', 'Everything drops in. The only things that press are the ESC past its ridges, as now, and the clips\' soft prongs.'),
               ('What holds it?', 'The lid, through the clip on top of the stack: about %.0f N by my estimate, which could be half or double. With the lid off nothing holds it, as you said it needn\'t.' % f[BLADE][0]),
               ('What happens upside down?', 'The stack hangs on the clip. If the stack weighs less than the clip pushes, it doesn\'t move. A harder knock squeezes the clip %.2f further, then its solid body takes the load. The pegs are still %.1f in their holes.' % (CLIP_RISE - SQUEEZE, BX.PEG_LONG - (CLIP_RISE - SQUEEZE))),
               ('Why does it go this way?', 'A spring with %.1f of travel doesn\'t notice 0.2 of print error. A friction peg has to be right within about 0.05, and six of them have to be right together.' % CLIP_RISE),
               ('What stops it sliding?', 'Two %.1f pegs in your %.1f holes, with %.2f of room a side: a little more than your 5.0 peg had in the 5.4 row. The slimmer pegs only touch after those two give.' % (LOC, BX.HOLE, rl)),
               ('What about the ESC that was too tall?', 'The pad it hit is gone. The clip under the top has %.2f of travel left as drawn, so a taller ESC squeezes it a little more.' % (CLIP_RISE - SQUEEZE))]
    guesses = [('Locating pegs', '%.1f in %.1f' % (LOC, BX.HOLE), '%.2f of room a side, picked on the noise screen. Your bench: 5.0 in the 5.4 row had 0.20 and "will fall out when tipped".' % rl),
               ('Backup pegs', '%.1f' % BACK, '%.2f clear. Whether they share a crash load after the first two give is untested.' % rb),
               ('Squeeze', '%.2f' % SQUEEZE, 'How far the lid presses a clip as drawn. A stack can be %.2f tall or short and still be held.' % SQUEEZE),
               ('Travel', '%.1f' % CLIP_RISE, 'Blade tip to the clip\'s solid body. It must stay under the pegs\' %.1f.' % BX.PEG_LONG),
               ('Blade thickness', '%.1f' % BLADE, 'The strip prints %s. My estimates as drawn: %s N. Squeezed flat: %s N.' % (', '.join('%.1f' % t for t in BLADES), ', '.join('%.0f' % f[t][0] for t in BLADES), ', '.join('%.0f' % f[t][1] for t in BLADES))),
               ('TPU stiffness', '%.0f MPa' % E_TPU, 'A guess for printed 95A. It sets every force above, so a kitchen scale on the strip is the real number.'),
               ('Prongs', '%.1f x %.1f' % (PRONG, CLIP_D), 'Corner to corner %.2f in a %.1f hole. Soft, so the corners squeeze. Untested.' % (math.hypot(PRONG, CLIP_D), BX.HOLE)),
               ('Clip length', '%.1f' % CLIP_L, '0.15 a side inside the ring under the ESC\'s top.'),
               ('Room over the ESC', '%.1f' % ROOM, 'From your 34.0 caliper. Print sag in the box\'s bottom comes off it.'),
               ('Stack height', '%d units, %.0f' % (BX.CEILING_UNITS, BX.CEILING), 'Four printed pieces stacked. Each can be a little off, which is what the squeeze is for.'),
               ('Hoop', '%.1f inside' % LID_Z, 'Patch underside to the bar. It sets the squeeze in the test.'),
               ('One clip a stack', '1', 'Drawn with one. A heavier stack, like a pack, may want two or three.')]
    prints = [dict(name='ESC box, loose pegs', mat='PLA', **(info.get('esc_box') or dict(time='', g=0.0))), dict(name='ESC top, no pad', mat='PLA', **(info.get('esc_top') or dict(time='', g=0.0))),
              dict(name='PCA box, loose pegs', mat='PLA', **(info.get('pca_box') or dict(time='', g=0.0))), dict(name='Test hoop', mat='PLA', **(info.get('hoop') or dict(time='', g=0.0))),
              dict(name='Clip strip: six, three blades', mat='TPU', time='', g=0.0)]
    tests = ['Drop the boxes on the patch a few times. Do they go in with no force, every time?',
             'Press each clip flat on a kitchen scale with something flat. Read the grams as the blades go flat. Thin, middle and thick: which feels right?',
             'Build the stack, slide the hoop on, flip it and shake it. Does anything move or rattle?',
             'Leave it in the hoop overnight. Does the clip still push back in the morning?']
    meta = dict(steps=steps, answers=[dict(q=q, a=a) for q, a in answers], guesses=[dict(name=n, value=v, why=w) for n, v, w in guesses], prints=prints, tests=tests, noise=N,
                center=[AT[0], AT[1], 42.0], r=78.0, n=dict(loc=LOC, back=BACK, hole=BX.HOLE, room=rl, squeeze=SQUEEZE, rise=CLIP_RISE, peg=BX.PEG_LONG, lid=ROOM, pad=BX.GAP, press=PN.PRESS))
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/', 'window.PARTS=' + json.dumps(P) + ';window.META=' + json.dumps(meta) + ';')
    p = os.path.join(config.TWIN_OUT, 'spring_stack_view.html')
    open(p, 'w', encoding='utf-8').write(html)
    print('wrote %s (%.1f MB)' % (p, len(html) / 1e6))


if __name__ == '__main__':
    A = build()
    info = json.load(open(SLICE)) if os.path.exists(SLICE) else {}
    if 'page' in sys.argv[1:]:
        page(A, noise(), info)
        sys.exit(0)
    good, N = check(A)
    print('Print pieces (boxes and top upside down, pegs up; the hoop and the clips on their sides):')
    g2, paths = export(); good &= g2
    if 'slice' in sys.argv[1:]:
        print('Slices, draft, not sent to the printer:')
        info = slice_all(paths)
    if os.path.exists(TEMPLATE):
        page(A, N, info)
    print('checks:', 'all pass' if good else 'SOMETHING FAILED')
    sys.exit(0 if good else 1)
