"""Interference check for pan_coil_b: does any pair of parts share space?

Written 2026-09-19 because Zach spotted the servo passing through the well BY EYE, the
way he spotted three of variant B's faults. No check could see it, because there was no
check. Same lesson as ../../lessons/2026-09-19-surface-sampling-is-a-vacuous-check.md:
a number nobody computes cannot come out wrong.

Every row is a volume in mm3 of shared solid. Rotating parts are swept over the pan
range, so a clash that only appears at one angle still shows up.

NEGATIVE CONTROL: --broken re-runs with the servo put back where it was when Zach spotted
it -- 4 mm toward the pan axis and 2.5 mm up, into the deck plate. Rows that stay at 0.00
under that are not measuring anything, and should not be trusted. The lift matters: moving
the servo sideways alone hits the bay first and leaves `servo vs well` reading zero, which
is precisely the row that needs proving.

    python pan_coil_b_check.py [--broken]
"""
import sys
import numpy as np
import pan_coil_b as P
from tree_parts import U

STEP = 0.35
PANS = (-270, -135, 0, 135, 270)

# (a, b, note). Pairs that are MEANT to touch are listed with an allowance.
PAIRS = [
    ('tab_block', 'base',   0.0, 'rails in the grooves, 0.15 each side'),
    ('tab_block', 'servo',  0.0, 'MEANT to touch: the tab sits on it'),
    ('tab_block', 'gear_in', 0.0, ''),
    ('tab_block', 'drum',   0.0, ''),
    ('servo', 'well',    0.0, 'the servo sits beside the can; it must not enter it'),
    ('servo', 'bay',     0.0, 'the bay is a shell around the gears, not around the servo'),
    ('servo', 'drum',    0.0, ''),
    ('gear_in', 'well',  0.0, ''),
    ('gear_in', 'bay',   0.0, ''),
    ('drum', 'well',     0.0, 'running clearance -- the drum turns inside this'),
    ('drum', 'bay',      0.0, ''),
    ('ribbon', 'drum',   0.0, 'the coil must not be pinched by its own drum'),
    ('ribbon', 'well',   0.0, 'nor by the wall it runs against'),
    ('ribbon', 'servo',  0.0, ''),
    # 2026-09-27: the small gear off the drum, the floor off the bay
    ('gear_out', 'drum',  0.0, 'set 8: onto the square seat, SQ_FIT a side'),
    ('gear_out', 'well',  0.0, ''),
    ('gear_out', 'bay',   0.0, ''),
    ('gear_out', 'floor', 0.0, ''),
    ('gear_out', 'servo', 0.0, ''),
    ('screw_out', 'floor', 0.0, 'the M3 head turns in the floor hole'),
    ('screw_out', 'gear_out', 0.0, 'shank through the web, head under it'),
    ('floor', 'bay',      0.0, 'MEANT to touch face to face; zero shared volume'),
    ('floor', 'gear_in',  0.0, ''),
    ('floor', 'drum',     0.0, ''),
    ('floor', 'servo',    0.0, ''),
    ('bearing', 'well',   0.0, 'the 6809 in its seat, +0.1 on the diameter'),
    ('bearing', 'drum',   0.0, 'the drum hub in the 6809, -0.1 on the diameter'),
]
if P.HORN_GEAR:   # set 9: the horn carries the gear; the spline goes into the horn, not the gear
    PAIRS += [
        ('gear_in', 'servo',  0.0, 'set 9: the spline is in the horn, the gear 1.0 under the block'),
        ('horn', 'gear_in',   1.0, 'set 9: in its pocket, zero offset (here an outline drawn at the arms\' widest)'),
        ('horn', 'base',      0.0, ''),
        ('horn', 'drum',      0.0, ''),
        ('horn', 'gear_out',  0.0, ''),
        ('horn', 'floor',     0.0, ''),
    ]
else:
    PAIRS.append(('gear_in', 'servo', 6.0, 'MEANT: set 6, the spline presses into the gear (bore 2.22 on its 2.325)'))
if P.RING_PART:   # set 7 (2026-10-04): the shelf and the cup wall are a drop-in ring (set 11: back in the base)
    PAIRS += [
        ('shelf_ring', 'well',    0.0, 'sits on the lane wall ledge, face to face; its notch on the rib'),
        ('shelf_ring', 'bay',     0.0, ''),
        ('shelf_ring', 'drum',    0.0, 'the drum turns inside it'),
        ('shelf_ring', 'ribbon',  0.0, 'the ribbon stands on its shelf'),
        ('shelf_ring', 'bearing', 0.0, ''),
        ('shelf_ring', 'servo',   0.0, ''),
    ]
if P.BARREL_688:   # set 9 (2026-10-10): a 688 in place of the journal
    PAIRS += [
        ('bearing688', 'well',     0.0, 'set 9: in its seat, +0.1 on the diameter'),
        ('bearing688', 'drum',     0.0, 'set 9: the barrel in its bore, -0.1 on the diameter'),
        ('bearing688', 'bay',      0.0, ''),
        ('bearing688', 'gear_out', 0.0, ''),
        ('bearing688', 'gear_in',  0.0, ''),
        ('bearing688', 'shelf_ring', 0.0, ''),
    ]
if P.HOLLOW_AXIS:   # set 10 (2026-10-11): a 6704 round the hollow barrel; the gear on three M2s round the wire hole
    PAIRS += [
        ('bearing6704', 'well',     0.0, 'set 10: in its seat, +0.1 on the diameter'),
        ('bearing6704', 'drum',     0.0, 'set 10: the barrel in its bore, -0.1 on the diameter'),
        ('bearing6704', 'bay',      0.0, ''),
        ('bearing6704', 'gear_out', 0.0, 'set 10: the hub stops AX_LIFT under the inner ring'),
        ('bearing6704', 'gear_in',  0.0, ''),
        ('bearing6704', 'screw_out', 0.0, ''),
        ('screw_out', 'drum',      7.0, 'MEANT: set 10, the M3s thread into the barrel (shanks drawn at the pilot)'),
        ('screw_out', 'base',      0.0, ''),
        ('screw_out', 'gear_in',   0.0, ''),
    ] + ([('bearing6704', 'shelf_ring', 0.0, '')] if P.RING_PART else [])
ROTATES = {'drum', 'ribbon', 'gear_out', 'screw_out'}


def shift_servo(fn, dx, dz):
    return lambda p, features=True: fn((p[0] - dx, p[1], p[2] - dz), features)


def at_pan(name, fns, deg):
    """Rotating parts are modelled at pan 0; turn the SAMPLE POINT the other way instead."""
    fn = fns[name]
    if name == 'ribbon':
        return lambda p, features=True: P.ribbon(p, features, pan_deg=deg)
    if name not in ROTATES:
        return fn
    a = np.radians(-deg)
    ca, sa = np.cos(a), np.sin(a)
    return lambda p, features=True: fn((p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca, p[2]), features)


def overlap(fa, fb, lo, hi, step):
    xs = [np.arange(lo[i], hi[i] + step, step) for i in range(3)]
    if min(len(x) for x in xs) < 2:
        return 0.0
    Y, Z = np.meshgrid(xs[1], xs[2], indexing='ij')
    n = 0
    for i0 in range(0, len(xs[0]), 16):
        xx = xs[0][i0:i0 + 16]
        p = (xx[:, None, None] + 0 * Y[None], np.broadcast_to(Y, (len(xx),) + Y.shape),
             np.broadcast_to(Z, (len(xx),) + Z.shape))
        n += int(np.count_nonzero((fa(p) < 0) & (fb(p) < 0)))
    return n * step ** 3


def nest():
    """Variant B's nest, read-only, for the merge check. That file belongs to another
    session and is edited live, so a failed import is reported, never worked around."""
    try:
        import tree_parts_b as B
    except Exception as e:                                    # noqa: BLE001
        print(f'  (nest rows skipped: tree_parts_b would not import -- {type(e).__name__}: {e})')
        return None, None
    fn, lo, hi = B.PARTS['fork'][0], B.PARTS['fork'][1], B.PARTS['fork'][2]
    return fn, (np.array(lo, float), np.array(hi, float))


def main(broken=False):
    fns = {k: v[0] for k, v in P.PARTS.items()}
    box = {k: (np.array(v[1], float), np.array(v[2], float)) for k, v in P.PARTS.items()}
    nfn, nbox = nest()
    if nfn is not None:
        fns['fork'], box['fork'] = nfn, nbox
        ROTATES.add('fork')
        for other in ('well', 'bay', 'servo', 'gear_in', 'bearing'):
            PAIRS.append(('fork', other, 0.0, 'the nest turns over this'))
        PAIRS.append(('fork', 'drum', 200.0, 'MEANT to touch: the nest bolts to the mating disc'))
    if broken:
        P.GEAR_GAP, P.RELIEF_D = 0.0, 0.0          # the gear pair and the race relief as they were
        fns['servo'] = shift_servo(P.servo, -4.0, 2.5)
        box['servo'] = (box['servo'][0] + [-4, 0, 2.5], box['servo'][1] + [-4, 0, 2.5])
    print(f'{"pair":<22}{"overlap mm3":>13}   note')
    bad = 0
    for a, b, allow, note in PAIRS:
        lo = np.maximum(box[a][0], box[b][0]) - 1
        hi = np.minimum(box[a][1], box[b][1]) + 1
        if np.any(hi <= lo):
            print(f'{a + " vs " + b:<22}{"0.00":>13}   bounding boxes do not meet')
            continue
        worst, where = 0.0, 0
        for deg in (PANS if (a in ROTATES or b in ROTATES) else (0,)):
            v = overlap(at_pan(a, fns, deg), at_pan(b, fns, deg), lo, hi, STEP)
            if v > worst:
                worst, where = v, deg
        flag = ''
        if worst > allow + 1.0:
            flag = '  <== CLASH'
            bad += 1
        tag = f' (worst at pan {where:+.0f})' if (a in ROTATES or b in ROTATES) and worst > 1.0 else ''
        print(f'{a + " vs " + b:<22}{worst:>13.2f}   {note}{tag}{flag}')
    print(f'\n{bad} clash(es)' + ('   [NEGATIVE CONTROL -- these SHOULD appear]' if broken else ''))
    bad += insertion(fns, box, broken)
    bad += assembly(fns, box, broken)
    bad += gear_play(broken)
    bad += bearing_races(broken)
    bad += screw_threads()
    if P.HORN_GEAR:
        bad += block_air()
    if P.HOLLOW_AXIS:
        bad += wire_axis()
    if P.SHELF_MERGED:
        bad += merged_shelf()
    return bad


def block_air():
    """Set 9: air between the servo's block (its underside, Z -30.9) and what turns under it: the input gear's top face
    and the horn's hub, read in the block's footprint. Zach found set 6's gear rubbing there, worse as its screw was
    tightened: the press bore let the screw pull the gear up the real 9.0 spline (1.0 shorter than the model) into a
    0.5 gap. Wanted: the gear 0.9+, the hub 0.5+, and the horn kit's screw (on the horn's web, up through the gear's
    open floor) with 2.5+ of thread in the spline.
    CONTROL: set 6 as Zach had it, the gear 1.0 up, must read the gear into the block."""
    zb = P.SV_Z0 - P.SV_HUMP_H
    x = np.arange(P.SV_X0 + 0.2, P.SV_X1 - 0.2, 0.2); y = np.arange(P.SV_Y0 + 0.2, P.SV_Y0 + P.SV_HUMP_L - 0.2, 0.2)
    X, Y = np.meshgrid(x, y)
    def top(fn, dz=0.0):
        for z in np.arange(zb + 1.0, zb - 3.0, -0.02):
            if (fn((X, Y, np.full_like(X, z - dz))) < 0).any():
                return z
        return -1e9
    gear, hub = zb - top(P.gear_in), zb - top(P.horn)
    thread = (P.HORN_FACE_Z + P.HORN_CB_H + P.HORN_SCREW_L) - (P.SV_Z0 - P.SPLINE_REAL)   # the horn kit's screw on the web
    P.HORN_GEAR = False
    ctrl = zb - top(P.gear_in, dz=1.0)
    P.HORN_GEAR = True
    ok = gear >= 0.9 and hub >= 0.5 and thread >= 2.5 and ctrl < 0
    print(f'{"air under the servo block: gear / horn hub":<46}   {gear:.2f} / {hub:.2f} mm (0.9 / 0.5 wanted), horn screw '
          f'thread in the spline {thread:.1f} (2.5 wanted); set 6 pulled up 1.0 control {ctrl:.2f} '
          + ('' if ok else '<== ' + ('CONTROL READS CLEAR' if ctrl >= 0 else 'TOO CLOSE')))
    return 0 if ok else 1


def screw_threads():
    """Where the small gear's screw cuts its thread. Added 2026-10-09 (set 8): the seat snapped off every time Zach
    tightened the screw, because most of the thread was in the seat, below the step the gear pushes up on, so the
    screw pulled the seat off across the layers. Reads the drum's material in the thread's ring (r 1.4, inside
    the M3's 1.5 crest, outside the 1.25 pilot) along the screw: none may be below the step, and at least 5 mm
    above it. CONTROL: set 7's drum (pilot from the seat's end, M3 x 8) must read thread in the seat."""
    if P.HOLLOW_AXIS:
        return screw_threads_6704()
    def read():
        z = np.arange(P.G_Z0, P.G_Z0 + P.SCREW_L + 0.001, 0.05)
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        m = np.array([(P.drum((1.4 * np.cos(a), 1.4 * np.sin(a), np.full_like(a, zz))) < 0).mean() > 0.5 for zz in z])
        return (m & (z < P.G_Z1)).sum() * 0.05, (m & (z >= P.G_Z1)).sum() * 0.05
    seat, barrel = read()
    keep = P.SCREW_THRU, P.SCREW_L
    P.SCREW_THRU, P.SCREW_L = False, 8.0
    c_seat, c_barrel = read()
    P.SCREW_THRU, P.SCREW_L = keep
    ok = seat == 0 and barrel >= 5.0 and c_seat > 1.0
    print(f'{"gear screw thread: in the seat / the barrel":<46}   {seat:.1f} / {barrel:.1f} mm (0 / 5+ wanted); '
          f'set 7 control {c_seat:.1f} / {c_barrel:.1f} ' + ('' if ok else '<== ' + (
              'CONTROL READS NOTHING' if c_seat <= 1.0 else 'THREAD IN THE SEAT' if seat else 'TOO LITTLE THREAD')))
    return 0 if ok else 1


def screw_threads_6704():
    """Set 10: each M3 x 16's thread in the barrel, read in its thread's ring (r 1.4, inside the M3's 1.5 crest, outside
    the 1.25 pilot) along the screw from its head (under the gear), and none in the gear and its hub (clear holes).
    Wanted 5.0+ in the barrel (set 8's M3 had 5.8 above the step). CONTROL: an M3 x 12 must read too little."""
    def read(L):
        z = np.arange(P.G_Z0, P.G_Z0 + L + 0.001, 0.05)
        a = np.linspace(0, 2 * np.pi, 24, endpoint=False)
        out = []
        for x, y in P.ax_screws():
            q = lambda fn, zz: (fn((x + 1.4 * np.cos(a), y + 1.4 * np.sin(a), np.full_like(a, zz))) < 0).mean() > 0.5
            out.append((sum(q(P.drum, zz) for zz in z) * 0.05, sum(q(P.gear_out, zz) for zz in z) * 0.05))
        return min(o[0] for o in out), max(o[1] for o in out)
    barrel, web = read(P.AX_SCREW_L)
    c_barrel, _ = read(12.0)
    ok = barrel >= 5.0 and web == 0 and c_barrel < 5.0
    print(f'{"gear M3s: thread in the barrel / in the gear":<46}   {barrel:.1f} / {web:.1f} mm (5.0+ / 0 wanted); '
          f'M3 x 12 control {c_barrel:.1f} ' + ('' if ok else '<== ' + ('CONTROL READS ENOUGH' if c_barrel >= 5.0 else 'WRONG')))
    return 0 if ok else 1


def gear_play(broken=False):
    """Free play of the gear pair, read as how far the small gear (= the drum = the head) turns
    each way against a held input gear, plus tooth overlap through one tooth pitch at 2:1.
    Added 2026-09-27: the pair had been drawn at zero clearance, 0.0 deg, and no row saw it.
    NEGATIVE CONTROL (--broken): GEAR_GAP 0 must read 0.0 deg and FAIL."""
    h = 0.02
    xs = np.arange(P.R_OUT_G - 4, P.R_OUT_G + 4, h); ys = np.arange(-5, 5, h)
    X, Y = np.meshgrid(xs, ys, indexing='ij'); Z = np.full_like(X, (P.G_Z0 + P.G_Z1) / 2)

    def turned(fn, cx, deg):
        a = np.radians(-deg); ca, sa = np.cos(a), np.sin(a)
        x = X - cx
        return fn((x * ca - Y * sa + cx, x * sa + Y * ca, Z), False)
    small = lambda t: turned(P.gear_out, 0.0, t)
    big = lambda t: turned(P.gear_in, P.CENTRE, t)
    ov = max(((small(t) < 0) & (big(-t / 2) < 0)).sum() * h * h for t in np.linspace(0, 360 / P.N_OUT, 13))
    held, play = big(0) < 0, 0.0
    for sgn in (1, -1):
        t = 0.0
        while not ((small(sgn * t) < 0) & held).any() and t < 15:
            t += 0.05
        play += t
    ok = ov == 0 and 0.5 <= play <= 4.0
    print(f'\n{"gear pair":<46}   overlap {ov:.3f} mm2 through a pitch, drum free play {play:.2f} deg '
          + ('(0.5..4 wanted)' if ok else '<== ' + ('JAMS' if play < 0.5 or ov else 'TOO LOOSE')))
    return 0 if ok else 1


def bearing_races(broken=False):
    """The 6809's inner race turns with the drum, so nothing fixed may be under it; the outer race
    must land on the ledge. Probed just below the races' bottom face, over each race's width
    (catalogue shoulders: inner 22.5..24.8, outer 26.75..29). Added 2026-09-27: the ledge ran
    solid under both. NEGATIVE CONTROL (--broken): no relief, the inner race reads 100%."""
    def frac(r0, r1):
        r = np.linspace(r0, r1, 40); a = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        R, A = np.meshgrid(r, a)
        return (P.base((R * np.cos(A), R * np.sin(A), np.full_like(R, P.BRG_Z0 - 0.05))) < 0).mean()
    inner, outer = frac(22.6, 24.7), frac(26.85, 28.9)
    ok = inner == 0 and outer > 0.95
    print(f'{"6809 races on the fixed ledge":<46}   inner (turns) {100 * inner:.0f}%, outer (fixed) {100 * outer:.0f}% '
          + ('(0 / 100 wanted)' if ok else '<== WRONG'))
    return (0 if ok else 1) + hub_face() + (races_688() if P.BARREL_688 else 0) + (races_6704() if P.HOLLOW_AXIS else 0)


def races_688():
    """Set 9: the 688's inner race turns with the barrel, so nothing fixed may be under it (r 4.1..5.0, inside its
    ~r 5.2 shoulder); its outer race must sit on the lip (r 7.2..7.95). Also: nothing turning may touch the outer
    race from above, so the drum's underside must stand clear over the whole bearing. Probed 0.05 under and over.
    CONTROL: the lip reaching in to r 4.0 must read the inner race as sitting on it."""
    def frac(fn, r0, r1, z):
        r = np.linspace(r0, r1, 20); a = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        R, A = np.meshgrid(r, a)
        return (fn((R * np.cos(A), R * np.sin(A), np.full_like(R, z))) < 0).mean()
    inner, outer = frac(P.base, 4.1, 5.0, P.B688_Z0 - 0.05), frac(P.base, 7.2, 7.95, P.B688_Z0 - 0.05)
    above = frac(P.drum, 4.1, 7.95, P.B688_Z1 + 0.05)
    keep, P.B688_LIP_R = P.B688_LIP_R, 4.0
    ctrl = frac(P.base, 4.1, 5.0, P.B688_Z0 - 0.05)
    P.B688_LIP_R = keep
    ok = inner == 0 and outer > 0.95 and above == 0 and ctrl > 0.9
    print(f'{"688 races: on the lip / drum over them":<46}   inner (turns) {100 * inner:.0f}%, outer (fixed) '
          f'{100 * outer:.0f}%, drum 0.05 over {100 * above:.0f}% (0 / 100 / 0 wanted); lip-in control '
          f'{100 * ctrl:.0f}% ' + ('' if ok else '<== WRONG'))
    return 0 if ok else 1


def races_6704():
    """Set 10: as races_688 for the 6704. Its inner ring (r 10.0..11.3) turns with the barrel, so nothing fixed may be
    under it; its outer ring (12.3..13.5) must sit on the lip; the drum must stand clear over the whole bearing; and
    the small gear's hub, which turns, may come up under the inner ring only, never the outer.
    CONTROL: the lip reaching in to r 10.0 must read the inner ring as sitting on it."""
    def frac(fn, r0, r1, z):
        r = np.linspace(r0, r1, 20); a = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        R, A = np.meshgrid(r, a)
        return (fn((R * np.cos(A), R * np.sin(A), np.full_like(R, z))) < 0).mean()
    i0, i1, o0, o1 = P.B6704_RINGS
    under = P.B6704_Z0 - 0.05
    inner, outer = frac(P.base, i0 + 0.1, i1 - 0.1, under), frac(P.base, P.B6704_LIP_R + 0.1, o1 - 0.05, under)
    above = frac(P.drum, i0 + 0.1, o1 - 0.05, P.B6704_Z1 + 0.05)
    collar_out = frac(P.gear_out, o0, o1, P.B6704_Z0 - P.AX_LIFT - 0.05)
    keep, P.B6704_LIP_R = P.B6704_LIP_R, i0
    ctrl = frac(P.base, i0 + 0.1, i1 - 0.1, under)
    P.B6704_LIP_R = keep
    ok = inner == 0 and outer > 0.95 and above == 0 and collar_out == 0 and ctrl > 0.9
    print(f'{"6704 races: on the lip / drum, hub near them":<46}   inner (turns) {100 * inner:.0f}%, outer (fixed) '
          f'{100 * outer:.0f}%, drum 0.05 over {100 * above:.0f}%, hub under the outer {100 * collar_out:.0f}% '
          f'(0 / 100 / 0 / 0 wanted); lip-in control {100 * ctrl:.0f}% ' + ('' if ok else '<== WRONG'))
    return 0 if ok else 1


def wire_axis():
    """Set 10: the wires' way straight down the pan axis, from the cone's point out under the floor plate. A probe of
    the bundle's size (three 28 AWG silicone wires twisted, ~2.6 across, so r 1.3) must find no part in its way.
    CONTROL: set 9 (HOLLOW_AXIS off: solid barrel, the M3 on the axis) must read blocked."""
    def blocked():
        z = np.arange(P.AX_WIRE_Z1 - 1.0, P.BAY_Z0 - 2.0, -0.05)
        a = np.linspace(0, 2 * np.pi, 16, endpoint=False)
        hits = []
        for name in ('drum', 'gear_out', 'screw_out', 'floor', 'base') + (('shelf_ring',) if P.RING_PART else ()):
            fn = P.PARTS[name][0]
            for r in (0.0, 0.65, 1.3):
                q = (np.multiply.outer(np.ones_like(z), r * np.cos(a)), np.multiply.outer(np.ones_like(z), r * np.sin(a)),
                     np.multiply.outer(z, np.ones_like(a)))
                if (fn(q) < 0).any():
                    hits.append(name); break
        return hits
    now = blocked()
    keep = P.HOLLOW_AXIS, P.BARREL_688
    P.HOLLOW_AXIS, P.BARREL_688 = False, True
    ctrl = blocked()
    P.HOLLOW_AXIS, P.BARREL_688 = keep
    ok = not now and bool(ctrl)
    print(f'{"wires down the axis, r 1.3, cone to under floor":<46}   blocked by {now or "nothing"}; set 9 control blocked '
          f'by {ctrl or "nothing"} ' + ('' if ok else '<== ' + ('CONTROL READS CLEAR' if not ctrl else 'BLOCKED')))
    return 0 if ok else 1


def merged_shelf():
    """Set 11: the shelf ring is part of the base. Probed in the base alone: the ribbon's floor (0.05 under it, from the
    6704's way through out to the cup wall), the old lane at its mid-height, the cup wall, all solid; the wires' old exit
    hole, along its centreline outside the lane wall, closed; the boss gone (outside the base's wall at -145).
    CONTROL: set 10's base (SHELF_MERGED off) must read the floor and the cup missing and the hole open."""
    def frac(r0, r1, z):
        r = np.linspace(r0, r1, 20); a = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        R, A = np.meshgrid(r, a)
        return (P.base((R * np.cos(A), R * np.sin(A), np.full_like(R, z))) < 0).mean()
    def read():
        floor = frac(P.PASS_R + 0.1, P.RING_IR - 0.1, P.CH_Z0 - 0.05)
        lane = frac(P.PASS_R + 0.1, P.LANE_R - 0.1, P.LANE_ZC)
        cup = frac(P.RING_IR + 0.1, P.RING_IR + P.RING_T - 0.1, (P.CH_Z0 + P.BAND_Z0) / 2)   # under the ribbon notch's sill
        rl = np.hypot(P.BASE_WIRE[:, 0], P.BASE_WIRE[:, 1])
        line = P.BASE_WIRE[(rl > P.LANE_R + 0.5) & (rl < P.SKIRT_IR + P.SKIRT_T - 0.3)]   # in the base's wall
        hole = float((P.base(tuple(line.T)) < 0).mean())
        bx, by, bz = P._pol(P.SKIRT_IR + P.SKIRT_T + 0.8, P.WIRE_EXIT_DEG, -20.0)
        boss = float((P.base((np.array([bx]), np.array([by]), np.array([bz]))) < 0).mean())
        return floor, lane, cup, hole, boss
    now = read()
    keep = P.SHELF_MERGED, P.RING_PART
    P.SHELF_MERGED, P.RING_PART = False, True
    ctrl = read()
    P.SHELF_MERGED, P.RING_PART = keep
    ok = min(now[:4]) > 0.95 and now[4] == 0 and ctrl[0] == 0 and ctrl[3] < 0.9
    print(f'{"shelf in the base: floor / lane / cup / old hole":<46}   {100 * now[0]:.0f} / {100 * now[1]:.0f} / '
          f'{100 * now[2]:.0f}% solid, the old exit hole {100 * now[3]:.0f}% filled, boss {100 * now[4]:.0f}% '
          f'(100 / 100 / 100 / 100 / 0 wanted); set 10 control: floor {100 * ctrl[0]:.0f}%, hole {100 * ctrl[3]:.0f}% filled '
          + ('' if ok else '<== ' + ('CONTROL READS MERGED' if ctrl[0] or ctrl[3] >= 0.9 else 'NOT MERGED')))
    return 0 if ok else 1


def hub_face():
    """Nothing fixed may sit under the drum's hub: its underside (Z -0.40, r 17.7..22.45) lay flush on the deck
    ring at r 19.5..20.4, so the drum stood on plastic as well as on the 6809 (found 2026-10-04, after Zach said
    the pan was finicky). Probes 0.05 under that face, against the base and set 7's ring. CONTROL: set 5's base
    (INSERT off) must read about 20%."""
    def frac(insert):
        was, P.INSERT = P.INSERT, insert
        r = np.linspace(P.FLANGE_R + 0.05, P.HUB_FIT_R - 0.05, 60); a = np.linspace(0, 2 * np.pi, 360, endpoint=False)
        R, A = np.meshgrid(r, a); q = (R * np.cos(A), R * np.sin(A), np.full_like(R, P.BRG_Z0 - 0.05))
        hit = (P.base(q) < 0) | ((P.shelf_ring(q) < 0) if insert and P.RING_PART else False)
        P.INSERT = was
        return hit.mean()
    now, ctrl = frac(P.INSERT), frac(False)
    ok = now == 0 and ctrl > 0.05
    print(f'{"fixed material under the drum hub":<46}   {100 * now:.1f}% (0 wanted); set 5 control {100 * ctrl:.0f}% '
          + ('' if ok else '<== ' + ('TOUCHES' if now else 'CONTROL READS NOTHING')))
    return 0 if ok else 1


def moved(fn, d):
    return lambda q, features=True: fn((q[0] - d[0], q[1] - d[1], q[2] - d[2]), features)


def sweep(label, movers, obstacles, fns, box, direction, travel):
    """Bring `movers` in along `direction` from `travel` mm away to seated, against the
    `obstacles` already in place. Every stop reads the shared volume; the worst is the verdict."""
    # only where the movers go can anything collide: their box, stretched over the travel
    lo = np.min([box[n][0] for n in movers], axis=0) - 1
    hi = np.max([box[n][1] for n in movers], axis=0) + 1
    d = np.array(direction, float)
    lo, hi = np.minimum(lo, lo - d * travel), np.maximum(hi, hi - d * travel)
    obs = lambda q, features=True: U(*[fns[n](q, features) for n in obstacles])
    worst, where = 0.0, 0.0
    for t in [travel * k for k in (1, .7, .5, .35, .25, .15, .1, .05)] + [1.0, 0.5, 0.0]:
        mov = lambda q, features=True, t=t: U(*[moved(fns[n], -d * t)(q, features) for n in movers])
        v = overlap(mov, obs, lo, hi, STEP)
        if v > worst:
            worst, where = v, t
    ok = worst <= 1.0
    print(f'{label:<46}{worst:>10.2f}   ' + ('clear all the way in' if ok else f'<== BLOCKED {where:.1f} mm out'))
    return 0 if ok else 1


def assembly(fns, box, broken=False):
    """Can each part reach its seat? Added 2026-09-27: the drum's gear was moulded on and
    could not pass the journal, and the bay was a closed box, with every pair check at zero.
    Seated parts in the assembly order: servo (above), then these.

    NEGATIVE CONTROL (--broken): the drum with its gear moulded back on, and the bay with its
    floor glued back on. Every row must then read BLOCKED."""
    f, b = dict(fns), dict(box)
    # The servo without its shaft for the gear's own path: since set 6 (2026-10-03) the spline presses
    # into the gear's bore, so the shaft overlaps it by design (the `gear_in vs servo` row above). Before,
    # the shaft ran 0.8 into the PLACEHOLDER horn pocket's roof, which held the gear low.
    f['servo_case'] = lambda q, features=True: U(
        P.rbox(q, (P.SV_X0, P.SV_Y0, P.SV_Z0), (P.SV_X1, P.SV_Y1, P.SV_Z1), 1.0),
        P.rbox(q, (P.SV_X0, P.SV_YC - P.TAB_SPAN / 2, P.TAB_Z0), (P.SV_X1, P.SV_YC + P.TAB_SPAN / 2, P.TAB_Z0 + P.TAB_T), 0.8),
        P.box(q, (P.SV_X0, P.SV_Y0, P.SV_Z0 - P.SV_HUMP_H), (P.SV_X1, P.SV_Y0 + P.SV_HUMP_L, P.SV_Z0 + 0.5)))   # the MG90S block
    b['servo_case'] = box['servo']
    if broken:
        f['drum'] = lambda q, features=True: U(P.drum(q, features), P.gear_out(q, features))
        b['base'] = (np.minimum(box['base'][0], box['floor'][0]), np.maximum(box['base'][1], box['floor'][1]))
        f['base'] = lambda q, features=True: U(P.base(q, features), P.floor(q, features))
    print(f'\n{"assembly, in order":<46}{"worst mm3":>10}')
    bad = 0
    # Set 10: the 6704 (27 across) can't pass the shelf ring's 25.2 hole, so it goes in first, under where the ring sits.
    # Set 11: the shelf is the base's, and its hole (PASS_R) lets the 6704 through.
    if P.HOLLOW_AXIS:
        bad += sweep('6704 down ' + ('through the shelf into its seat' if P.SHELF_MERGED else 'into its seat, before the shelf ring'),
                     ['bearing6704'], ['base', 'servo'], f, b, (0, 0, -1), 45)
    if P.RING_PART:
        if broken:   # its shelf 1 mm wider than the deck ring's hole
            f['shelf_ring'] = lambda q, features=True: U(P.shelf_ring(q, features), P.ring_z(
                q, P.SHELF_R0, P.SKIRT_IR + 1.0, P.LANE_Z1, P.CH_Z0, 0.0))
        bad += sweep('shelf ring down into the base from above', ['shelf_ring'],
                     ['base', 'servo'] + (['bearing6704'] if P.HOLLOW_AXIS else []), f, b, (0, 0, -1), 45)
    if P.BARREL_688:
        bad += sweep('688 down into its seat from above', ['bearing688'],
                     ['base', 'servo'] + (['shelf_ring'] if P.INSERT else []), f, b, (0, 0, -1), 45)
    bad += sweep('drum + 6809 down into the base from above', ['drum', 'bearing'],
                 ['base', 'servo'] + (['shelf_ring'] if P.RING_PART else []) + (['bearing688'] if P.BARREL_688 else [])
                 + (['bearing6704'] if P.HOLLOW_AXIS else []), f, b, (0, 0, -1), 45)
    bad += sweep('input gear' + (' + horn' if P.HORN_GEAR else '') + ' up onto the servo from below',
                 ['gear_in'] + (['horn'] if P.HORN_GEAR else []), ['base', 'servo_case', 'drum'], f, b, (0, 0, 1), 20)
    bad += sweep('small gear + ' + ('3 M3' if P.HOLLOW_AXIS else 'M3') + ' up onto the drum from below',
                 ['gear_out', 'screw_out'], ['base', 'drum', 'servo'] + (['bearing6704'] if P.HOLLOW_AXIS else []),
                 f, b, (0, 0, 1), 20)
    bad += sweep('tab block in through the window after the servo', ['tab_block'], ['base', 'servo', 'gear_in'],
                 f, b, (0, -1, 0), 20)
    bad += sweep('floor plate up from below', ['floor'], ['base', 'drum', 'gear_in', 'gear_out', 'screw_out', 'servo'],
                 f, b, (0, 0, 1), 15)
    print(f'{bad} blocked' + ('   [NEGATIVE CONTROL -- every row SHOULD be blocked]' if broken else ''))
    return bad


def insertion(fns, box, broken=False):
    """Can the servo actually get to its seat through the side window?

    It goes in along -Y. Slide it from clear of the tower to seated and watch for anything
    it has to pass through. A window that does not admit the part is the fault variant B's
    _insert.py was written for -- three rows there read zero while the geometry was wrong.
    """
    lo = np.minimum(box['servo'][0], box['base'][0]) - 1
    hi = np.maximum(box['servo'][1], box['base'][1]) + 1
    lo[1], hi[1] = lo[1] - 2, hi[1] + 42
    worst, where = 0.0, 0.0
    print(f'\n{"servo insertion, -Y":<22}{"overlap mm3":>13}   travel')
    for dy in (40, 30, 22, 16, 10, 6, 3, 0):
        f = shift_servo(P.servo, 0.0, 0.0) if dy == 0 else (
            lambda q, features=True, d=dy: P.servo((q[0], q[1] - d, q[2]), features))
        v = overlap(f, fns['base'], lo, hi, STEP)   # the bay fused to the well
        if v > worst:
            worst, where = v, dy
        print(f'{"  +" + str(dy) + " mm":<22}{v:>13.2f}')
    ok = worst <= 1.0
    print(f'{"worst":<22}{worst:>13.2f}   ' +
          ('clear all the way in' if ok else f'<== BLOCKED at +{where:.0f} mm'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(1 if main('--broken' in sys.argv) and '--broken' not in sys.argv else 0)
