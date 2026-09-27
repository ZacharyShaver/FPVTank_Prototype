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
]
ROTATES = {'drum', 'ribbon'}


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
    return bad


def insertion(fns, box, broken=False):
    """Can the servo actually get to its seat through the side window?

    It goes in along -Y. Slide it from clear of the tower to seated and watch for anything
    it has to pass through. A window that does not admit the part is the fault variant B's
    _insert.py was written for -- three rows there read zero while the geometry was wrong.
    """
    lo = np.minimum(box['servo'][0], box['bay'][0]) - 1
    hi = np.maximum(box['servo'][1], box['bay'][1]) + 1
    lo[1], hi[1] = lo[1] - 2, hi[1] + 42
    worst, where = 0.0, 0.0
    print(f'\n{"servo insertion, -Y":<22}{"overlap mm3":>13}   travel')
    for dy in (40, 30, 22, 16, 10, 6, 3, 0):
        f = shift_servo(P.servo, 0.0, 0.0) if dy == 0 else (
            lambda q, features=True, d=dy: P.servo((q[0], q[1] - d, q[2]), features))
        v = overlap(f, fns['bay'], lo, hi, STEP)
        if v > worst:
            worst, where = v, dy
        print(f'{"  +" + str(dy) + " mm":<22}{v:>13.2f}')
    ok = worst <= 1.0
    print(f'{"worst":<22}{worst:>13.2f}   ' +
          ('clear all the way in' if ok else f'<== BLOCKED at +{where:.0f} mm'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(1 if main('--broken' in sys.argv) and '--broken' not in sys.argv else 0)
