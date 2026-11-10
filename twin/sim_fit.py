"""Does the brain box fit the sim's designs? (2026-11-08). Zach: "now check it against sims see how the size and height fit designs. were going to have to guess weight to get any data out of
the balance but the parts can be moved so its fine to check that later when we have everything". So this is size and height only: geometry, no physics, no new gauge reads.

    python twin/sim_fit.py              # the named designs: T3, the Trainer, every run's finalists -> twin/out/sim_fit.json
    python twin/sim_fit.py screens      # a sample of what the realistic run built, for how common a fit is
    python twin/sim_fit.py cap          # random bodies from the 250 mm run's ranges (it has never run), built with its cap
    python twin/sim_fit.py control      # only the controls

For each design, the box slides fore and aft and up and down until it fits its body's hull best (y stays on the centre line; a body's skin is taken as 2.6 thick). Two questions:
  whole box   the 250 x 139.5 x 82 block with its own floor, walls and lid, dropped inside
  contents    only what's in it: the boxes, the Pi's plugs and their wire bend, inside the body's own skin. The body can be its own walls, floor and lid
A motor or wheel inside the contents counts against the fit too: motors stand inside many of these bodies.
"""
import json, os, pickle, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'gauges'))
import numpy as np
from scipy.spatial import ConvexHull
import config

OUT = os.path.join(config.TWIN_OUT, 'sim_fit.json')
SKIN = 2.6                               # print 1's wall; the skin the search counts
STEP_X, STEP_Z = 5.0, 2.0                # mm, the placement search
LEN, WID, TALL = 250.0, 139.5, 82.2      # brain_box: the block, outside
Z_FLOOR = 2.6
RUNS = ('capability', 'capability_low', 'capability_tail', 'capability_real', 'capability_tow')


def contents():
    """[(name, x0, x1, y0, y1, z0, z1)]: every box and stack in brain_box's frame, read from brain_box's own pieces, without the spacers (they only reach a lid), the camera, or the wall switches"""
    cache = os.path.join(config.TWIN_OUT, 'sim_fit_contents.json')
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(os.path.join(HERE, 'brain_box.py')):
        return [tuple(r) for r in json.load(open(cache))]
    import brain_box as BB
    import pi_box as PB
    out = []
    for p in BB.assemble():
        if p['role'] == 'spacer' or p['key'] in ('camera', 'stop', 'switch'):
            continue
        b = p['w'].val().BoundingBox()
        out.append((p['key'], b.xmin, b.xmax, b.ymin, b.ymax, max(b.zmin, Z_FLOOR), b.zmax))
    # the Pi's plugs and the room their wires need to turn over
    b = BB.pi_place(BB.X.pi_plugs()).val().BoundingBox()
    out.append(('pi_wires', b.xmin - 2, b.xmax + 2, b.ymin - 2, b.ymax + 2, b.zmin, b.zmax + BB.X.BEND))
    json.dump(out, open(cache, 'w'))
    return out


def corners(boxes):
    return np.array([[x, y, z] for _, x0, x1, y0, y1, z0, z1 in boxes for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])


def motors_of(sp):
    """each motor and wheel as an axis-aligned box in the design's frame: [(x0, x1, y0, y1, z0, z1, kind)]"""
    import knobs as K
    U = K._uni(); R, TW = sp['R'], sp['TW']; out = []
    for x, s, b in K._bosses(sp):
        y0, y1 = sorted((s * (b['face'] - U.MOT_L), s * b['face']))
        out.append((x - U.MOTOR_R, x + U.MOTOR_R, y0, y1, R - U.MOTOR_R, R + U.MOTOR_R, 'motor'))
    for x, y in sp['wheels']:
        y0, y1 = sorted((y - TW / 2, y + TW / 2))
        out.append((x - R, x + R, y0, y1, 0.0, 2 * R, 'wheel'))
    return out


def fit(sp, boxes, skin=SKIN):
    """the best placement of these boxes in the body's hull: how far past it they stick (mm, 0 is a fit), and how far into a motor or wheel. Returns a dict"""
    body = np.asarray(sp['hulls'][0], float)
    h = ConvexHull(body)
    C = corners(boxes)
    eq = h.equations
    M = motors_of(sp)
    lo, hi = body.min(0), body.max(0)
    b0 = np.array([[r[1], r[2], r[3], r[4], r[5], r[6]] for r in boxes])
    # centred first, then out either way: far enough to find the best spot in a big body, and still a search in one smaller than the box
    span = lambda i, m: abs((hi[i] - lo[i]) - np.ptp(C[:, i])) / 2 + m
    mid = lambda i: (lo[i] + hi[i]) / 2 - (C[:, i].min() + C[:, i].max()) / 2
    xs = mid(0) + np.arange(-span(0, 60.0), span(0, 60.0) + STEP_X, STEP_X)
    zs = mid(2) + np.arange(-span(2, 10.0), span(2, 10.0) + STEP_Z, STEP_Z)
    best = None
    N = eq[:, :3]; D = eq[:, 3]
    base = C @ N.T + D                                                    # corners x faces
    for dx in xs:
        for dz in zs:
            s = (base + dx * N[:, 0] + dz * N[:, 2]).max()
            over = max(0.0, s + skin)
            if best is not None and over > best['over'] + best['into']:
                continue
            into, what = 0.0, ''
            for x0, x1, y0, y1, z0, z1, kind in M:
                ov = np.minimum.reduce([b0[:, 1] + dx - x0, x1 - b0[:, 0] - dx, b0[:, 3] - y0, y1 - b0[:, 2], b0[:, 5] + dz - z0, z1 - b0[:, 4] - dz])
                d = float(ov.max())
                if d > into:
                    into, what = d, kind
            if best is None or over + into < best['over'] + best['into'] - 1e-9:
                best = dict(over=float(over), into=float(into), what=what, dx=float(dx), dz=float(dz))
    return best


def whole_block():
    return [('block', 0.0, LEN, -WID / 2, WID / 2, 0.0, TALL)]


def whole_fit(sp):
    """the block has its own walls, so it can touch the body's outer surface: no skin allowance"""
    return fit(sp, whole_block(), skin=0.0)


def read(sp, name, run, gauges=None, boxes=None):
    import knobs as K
    body = np.asarray(sp['hulls'][0], float)
    dims = (body.max(0) - body.min(0)).tolist()
    try:
        pr = list(K.body_print_size(sp))
    except Exception:
        pr = dims
    a, b = whole_fit(sp), fit(sp, boxes)
    return dict(name=name, run=run, body=dims, print=pr, belly=float(body[:, 2].min()), whole=a, contents=b, gauges=gauges or {}, wheels=[list(w) for w in sp['wheels']], R=sp['R'], TW=sp['TW'],
                track=max(abs(w[1]) for w in sp['wheels']), outline=hull_outline(body))


def hull_outline(body):
    """side and front outlines, for the page's little pictures"""
    out = {}
    for k, (u, v) in dict(side=(0, 2), front=(1, 2)).items():
        P = body[:, [u, v]]; h = ConvexHull(P)
        out[k] = np.round(P[h.vertices], 1).tolist()
    return out


def designs():
    """the named designs: (name, run, spec, gauges)"""
    import knobs as K
    out = []
    t3 = K.make(K.T3)
    out.append(('T3', 'reference', t3, {}))
    r = K.make(dict(K.T3, track=130.0), real=True)
    if r is not None:
        out.append(('T3, track 130', 'reference, realistic', r, {}))
    try:
        tr = K.make(dict(K.T3, **K.TRAINER))
        if tr is not None:
            out.append(('Trainer', 'reference', tr, {}))
    except Exception as e:
        print('no Trainer:', e)
    for run in RUNS:
        D = json.load(open(os.path.join(config.GAUGES_OUT, run, 'finals.json')))['finals']
        real = run in ('capability_real', 'capability_tow')
        strict = run in ('capability_low', 'capability_tail') or real
        for f in D:
            if not f.get('q'):
                continue
            q = dict(K.T3, **f['q'])                                      # a run's finals only list what it searched; the rest held at T3's
            sp = K.make(q, strict=strict, real=real)
            if sp is None:
                sp = K.make(q)
            if sp is None:
                print('  could not rebuild', run, f.get('name'))
                continue
            g = {k: f.get(k) for k in ('up', 'climb', 'turn', 'h_up', 'h_down', 'crest', 'push', 'tow', 'mass')}
            out.append((f.get('name', '?'), run, sp, g))
    return out


def controls(boxes):
    """the same check must read a miss on a body too small, and a fit on one plainly big enough"""
    import knobs as K
    t3 = K.make(K.T3)
    big = dict(t3); P = np.array([[x, y, z] for x in (-400, 400) for y in (-200, 200) for z in (0, 300)], float); big['hulls'] = [P] + list(t3['hulls'][1:]); big['wheels'] = [(-300.0, 400.0), (300.0, 400.0), (-300.0, -400.0), (300.0, -400.0)]
    small = dict(t3); Q = np.array([[x, y, z] for x in (-100, 100) for y in (-50, 50) for z in (20, 60)], float); small['hulls'] = [Q] + list(t3['hulls'][1:])
    a, b = fit(big, boxes), fit(small, boxes)
    ok = a['over'] == 0.0 and a['into'] == 0.0 and b['over'] > 20.0
    print('control: a 800 x 400 x 300 body: %.1f past, %.1f into a motor or wheel. A 200 x 100 x 40 body: %.1f past. %s' % (a['over'], a['into'], b['over'], 'ok' if ok else 'WRONG'))
    # a block 1 mm past a fitting body's skin has to read about 1 mm
    tight = dict(big); e = 2.6 + 1e-6
    C = corners(boxes)
    R = np.array([[x, y, z] for x in (C[:, 0].min() - e, C[:, 0].max() + e) for y in (C[:, 1].min() - e, C[:, 1].max() + e) for z in (C[:, 2].min() - e, C[:, 2].max() + e - 1.0)], float); tight['hulls'] = [R] + list(t3['hulls'][1:])
    c = fit(tight, boxes)
    ok2 = 0.0 < c['over'] <= 1.0 + STEP_Z
    print('control: a body cut to the box less 1 mm of height reads %.2f past. %s' % (c['over'], 'ok' if ok2 else 'WRONG'))
    return ok and ok2


def _measure(sp):
    import knobs as K
    B = CONTENTS
    w, c = whole_fit(sp), fit(sp, B)
    try:
        L, W, H = K.body_print_size(sp)
    except Exception:
        body = np.asarray(sp['hulls'][0], float); L, W, H = (body.max(0) - body.min(0)).tolist()
    return dict(whole=w['over'] + w['into'], contents=c['over'] + c['into'], past=c['over'], motor=c['into'], L=float(L), W=float(W), H=float(H), belly=float(np.asarray(sp['hulls'][0])[:, 2].min()))


def _real_job(q):
    import knobs as K
    try:
        sp = K.make(q, real=True)
    except Exception:
        return None
    return _measure(sp) if sp is not None else None


def _cap_job(z):
    """a random design from the 250 mm run's ranges, built with its cap. None when the run would refuse it"""
    import capability as CA
    try:
        sp = CA.build(CA.q_of(np.array(z)))
    except Exception:
        return None
    return _measure(sp) if sp is not None else None


CONTENTS = None


def _init():
    global CONTENTS
    CONTENTS = contents()


def report(res, name):
    n = len(res)
    print('%s: %d built' % (name, n))
    if not n:
        return dict(n=0)
    out = dict(n=n)
    for lab, key in (('whole block', 'whole'), ('contents in the skin', 'contents')):
        row = {t: sum(r[key] <= t for r in res) for t in (0.0, 5.0, 15.0, 30.0)}
        out[key] = row
        print('  %-22s %s' % (lab, '   '.join('within %2.0f mm: %d (%.0f %%)' % (t, v, 100 * v / n) for t, v in row.items())))
    A = np.array([[r['L'], r['W'], r['H'], r['belly']] for r in res])
    print('  body L, W, H, belly, percentiles 10, 50, 90:', np.percentile(A, [10, 50, 90], axis=0).round(0).tolist())
    fits = [r for r in res if r['contents'] <= 0.0]
    if fits:
        F = np.array([[r['L'], r['W'], r['H'], r['belly']] for r in fits])
        print('  the ones that hold the contents, the same:', np.percentile(F, [10, 50, 90], axis=0).round(0).tolist())
    miss = [r for r in res if r['contents'] > 0.0]
    if miss:
        print('  of the misses: past the skin only %d, into a motor or wheel only %d, both %d. Median miss %.0f mm' % (sum(r['past'] > 0 and r['motor'] <= 0 for r in miss), sum(r['past'] <= 0 and r['motor'] > 0 for r in miss), sum(r['past'] > 0 and r['motor'] > 0 for r in miss), float(np.median([r['contents'] for r in miss]))))
    out['pct'] = {k: np.percentile(A, [10, 50, 90], axis=0).round(0).tolist() for k in ('all',)}
    return out


def sample(run, n, seed=1):
    """what share of a run's designs hold the box. The realistic run: a sample of those it built. The 250 mm run has never run: random points in its ranges, built with its own cap"""
    import multiprocessing as mp
    if run == 'capability_real':
        rows = [json.loads(l) for l in open(os.path.join(config.GAUGES_OUT, run, 'screens.jsonl'))]
        rows = [r for r in rows if r.get('built') is not False]     # only refusals carry the key
        print('the realistic run built %d designs' % len(rows))
        rng = np.random.default_rng(seed)
        jobs = [rows[i]['q'] for i in rng.choice(len(rows), min(n, len(rows)), replace=False)]
        fn = _real_job
    else:
        os.environ['SCORPION_CAP'] = 'capability_250'
        import capability as CA
        rng = np.random.default_rng(seed)
        jobs = rng.random((n, len(CA.KEYS))).tolist()
        fn = _cap_job
    with mp.Pool(8, initializer=_init) as P:
        res = [r for r in P.imap_unordered(fn, jobs, chunksize=4) if r]
    json.dump(res, open(os.path.join(config.TWIN_OUT, 'sim_fit_%s.json' % run), 'w'))
    return res


if __name__ == '__main__':
    B = contents()
    print('contents: %d boxes, x %.1f to %.1f, y %.1f to %.1f, z %.1f to %.1f' % (len(B), min(r[1] for r in B), max(r[2] for r in B), min(r[3] for r in B), max(r[4] for r in B), min(r[5] for r in B), max(r[6] for r in B)))
    good = controls(B)
    if 'control' in sys.argv[1:]:
        sys.exit(0 if good else 1)
    if 'screens' in sys.argv[1:]:
        report(sample('capability_real', 600), 'the realistic run, a sample of what it built')
        sys.exit(0)
    if 'cap' in sys.argv[1:]:
        res = sample('capability_250', 2400)
        report(res, 'the 250 mm run\'s ranges, random, built with the cap')
        sys.exit(0)
    D = designs()
    rows = []
    print('%-30s %-16s %-16s %5s | %-22s | %-22s | %s' % ('design', 'run', 'body L W H', 'belly', 'whole box', 'contents in the skin', 'gauges'))
    for name, run, sp, g in D:
        r = read(sp, name, run, g, B)
        rows.append(r)
        fmt = lambda f: ('FITS' if f['over'] == 0 and f['into'] == 0 else '%3.0f past, %3.0f %s' % (f['over'], f['into'], f['what'] or 'in'))
        gs = ' '.join('%s %s' % (k, ('%.0f' % g[k]) if k in ('climb', 'turn') else ('%.2f' % g[k])) for k in ('up', 'climb', 'turn') if g.get(k) is not None)
        print('%-30s %-16s %3.0f %3.0f %3.0f     %5.1f | %-22s | %-22s | %s' % (name[:30], run[:16], *r['body'], r['belly'], fmt(r['whole']), fmt(r['contents']), gs))
    json.dump(dict(contents=B, rows=rows), open(OUT, 'w'))
    print('wrote', OUT, 'controls', 'ok' if good else 'WRONG')
    sys.exit(0 if good else 1)
