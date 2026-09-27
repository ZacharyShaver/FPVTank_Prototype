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
    ('gear_out', 'drum',  0.0, 'a 0.15 slide onto the D seat'),
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
    ('gear_in', 'servo', 13.0, 'KNOWN 12.6: the 4 mm shaft stub ends 0.8 below the PLACEHOLDER horn pocket'),
]
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
    return bad


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
    # The servo without its shaft stub for the gear's own path. The stub is drawn 4 mm long and
    # ends 0.8 below the PLACEHOLDER horn pocket's floor -- in the real part the shaft ends inside
    # the horn. The `gear_in vs servo` row above keeps that on record until Zach re-cuts the pocket.
    f['servo_case'] = lambda q, features=True: U(
        P.rbox(q, (P.SV_X0, P.SV_Y0, P.SV_Z0), (P.SV_X1, P.SV_Y1, P.SV_Z1), 1.0),
        P.rbox(q, (P.SV_X0, P.SV_YC - P.TAB_SPAN / 2, P.TAB_Z0), (P.SV_X1, P.SV_YC + P.TAB_SPAN / 2, P.TAB_Z0 + P.TAB_T), 0.8))
    b['servo_case'] = box['servo']
    if broken:
        f['drum'] = lambda q, features=True: U(P.drum(q, features), P.gear_out(q, features))
        b['base'] = (np.minimum(box['base'][0], box['floor'][0]), np.maximum(box['base'][1], box['floor'][1]))
        f['base'] = lambda q, features=True: U(P.base(q, features), P.floor(q, features))
    print(f'\n{"assembly, in order":<46}{"worst mm3":>10}')
    bad = 0
    bad += sweep('drum + 6809 down into the base from above', ['drum', 'bearing'], ['base', 'servo'],
                 f, b, (0, 0, -1), 45)
    bad += sweep('input gear up onto the servo from below', ['gear_in'], ['base', 'servo_case', 'drum'],
                 f, b, (0, 0, 1), 20)
    bad += sweep('small gear + M3 up onto the drum from below', ['gear_out', 'screw_out'],
                 ['base', 'drum', 'servo'], f, b, (0, 0, 1), 20)
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
