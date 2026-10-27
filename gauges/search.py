"""Generative design against the iteration-1 targets (gauges/README.md): G1 upright after a fall at least 0.75, then
G2 step up as tall and G3 turn-around space as small as they go. In stages, each dearer than the last:

    python gauges/search.py statics      # A: rest states, footprint and nose clearance of 2^15 Sobol designs (no sim)
    python gauges/search.py calibrate    # B0: A's numbers against the screening sims, on 240 random designs
    python gauges/search.py search       # B + C: screening sims of A's best, then cross-entropy on four weightings
    python gauges/search.py finals       # D: designs from the front on the full gauges
      -> gauges/out/search/*

The family, 18 knobs: chassis3's (the Trainer's body and insides on new wheels: R, xf, xr, clr, dxp, dzp), a middle
axle (six > 0.5), and a shell (shell > 0.5: shell3's superellipsoid in the ground frame, cut at the belly, a 1.5 mm
PLA cover over the body) or none. The shell is solid to the sim where a real one would have wheel wells; the tyres
are its own bodies, so nothing collides there. Screening sims: 40 falls at friction x1, the step ladder at x0.65 (the
worst for climbing in the first scorecard) with 6 tries a direction, the turn at all three frictions.
"""
import os, sys, json, time, math
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
sys.path.insert(0, config.TUMBLE)
import robots as RB
import gauges as GG

RUN = os.environ.get('SCORPION_SEARCH', 'search')                       # 'search': shapes only; 'search_limb': with the tail;
                                                                          # 'search_drive': with the tail, track and motor
OUT = os.path.join(config.GAUGES_OUT, RUN)
# the tail's six knobs came 2026-10-26 (search_limb); an 18-knob vector from the shape search is read with the tail off
KEYS = ['R', 'xf', 'xr', 'clr', 'dxp', 'dzp', 'six', 'shell', 'xc', 'af', 'ar', 'b', 'zc', 'cu', 'cd', 'p', 'qu', 'qd',
        'limb', 'L', 'tq', 'th_push', 'th_stow', 'mz', 'track', 'msize', 'gear']
LO = np.array([35.0, 40.0, -200.0, 15.0, -80.0, -8.0, 0.0, 0.0, -40.0, 120.0, 120.0, 100.0, 30.0, 40.0, 20.0, 1.6, 1.0, 1.0,
               0.0, 80.0, 0.3, -90.0, 20.0, 0.2, 110.0, 0.5, 0.4])
HI = np.array([95.0, 200.0, -40.0, 90.0, 80.0, 15.0, 1.0, 1.0, 60.0, 320.0, 320.0, 300.0, 200.0, 320.0, 250.0, 5.0, 4.0, 4.0,
               1.0, 350.0, 4.0, -10.0, 160.0, 1.0, 180.0, 2.0, 2.5])
NO_LIMB = [0.0, 200.0, 1.0, -60.0, 150.0, 1.0, 131.0, 1.0, 1.0]           # knobs 18 on, for shorter vectors: no tail, the Trainer's drive
TRACK0 = 131.0                                                            # chassis3.Y_W: the wheels' centre planes from the centre line
LIMB_ON = 0.3                                                             # limb > 0.3: a tail (seven designs in ten)
BASE = dict(R=55.0, xf=91.0, xr=-93.0, clr=32.4, dxp=0.0, dzp=0.0, six=0.0, shell=0.0, xc=0.0, af=200.0, ar=200.0, b=200.0,
            zc=100.0, cu=200.0, cd=150.0, p=2.0, qu=2.0, qd=2.0, **dict(zip(KEYS[18:], NO_LIMB)))   # chassis3's Trainer stand-in
COVER, PLA = 1.5, 1.24e-3                                                 # mm, g/mm3
UP_MIN, UP_SCREEN = 0.75, 0.85                                           # Zach's G1 floor; the screen's bar (40 falls: SE ~0.06)
N_FALL, N_TRY, MU_CLIMB = 40, 6, 0.65
WORKERS = 30
W = (0.0, 0.25, 1.0, None)                                               # climb - w * turn; None: turn alone


# ---------- the family ----------
def shell_points(q, z0, n=48, k=12):
    """shell3.shell_points in the ground frame, cut at z0; None if nothing is left above the cut"""
    th = np.linspace(0, 2 * np.pi, n, endpoint=False); c, s = np.cos(th), np.sin(th)
    e = 2.0 / q['p']; ux = np.sign(c) * np.abs(c) ** e; uy = np.sign(s) * np.abs(s) ** e
    ax = np.where(c >= 0, q['af'], q['ar']); phi = np.linspace(0, np.pi / 2, k); zc = q['zc']
    lev = [(zc + q['cu'] * np.sin(f) ** (2 / q['qu']), np.cos(f) ** (2 / q['qu'])) for f in phi]
    lev += [(zc - q['cd'] * np.sin(f) ** (2 / q['qd']), np.cos(f) ** (2 / q['qd'])) for f in phi[1:]]
    lev = [(z, r) for z, r in lev if z >= z0]
    if zc - q['cd'] < z0:
        if zc >= z0:
            t = (zc - z0) / q['cd']; lev.append((z0, (1 - t ** q['qd']) ** (1 / q['qd'])))
        elif zc + q['cu'] > z0:
            t = (z0 - zc) / q['cu']; lev.append((z0, (1 - t ** q['qu']) ** (1 / q['qu'])))
    pts = [np.c_[q['xc'] + ax * r * ux, q['b'] * r * uy, np.full(n, z)] for z, r in lev if r > 1e-6]
    if len(pts) < 2:
        return None
    pts.append([[q['xc'], 0.0, zc + q['cu']]])
    return np.vstack(pts)


def shell_mass(Q, z0=None):
    """a COVER mm PLA skin over the convex hull of Q, open at the cut z0 (None: closed, floor and all): g, centroid,
    inertia about it (g mm2)"""
    tri = Q[ConvexHull(Q).simplices]
    if z0 is not None:
        tri = tri[~np.all(tri[:, :, 2] < z0 + 0.5, axis=1)]
    ar = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1); A = ar.sum()
    g = tri.mean(1); c = (ar[:, None] * g).sum(0) / A
    d = tri - g[:, None, :]; Sa = np.einsum('n,nij->ij', ar, np.einsum('nki,nkj->nij', d, d) / 12)
    gg = g - c; Sa = Sa + np.einsum('n,ni,nj->ij', ar, gg, gg); rho = PLA * COVER
    return rho * A, c, (np.trace(Sa) * np.eye(3) - Sa) * rho


# The shell is the body (Zach, 2026-10-26: "why have a shell and a body?"). With a shell, the Trainer's walls and trim
# come out, mass and outline (about 416 g: tub, carapace, bed, deck, claws and their lights, corners, seals, intake),
# and one closed 1.5 mm skin wraps the searched shape and every part inside: the head (inside, for now: Zach), the Pi
# stack, packs, ESCs, UBECs and the rest, and a box round each motor out to its tyre. Without a shell, the design is
# the Trainer's own body, as before. The first shape search ("search", 2026-10-26) laid the shell over the whole body
# instead, counting the walls twice: superseded.
STRUCT = ('tub', 'carapace', 'bed', 'tdeck', 'claw', 'corner', 'seal_', 'intake', 'rest_peg', 'light', 'grommet')
_COMP = None


def components():
    """the Trainer's parts that stay inside a skin, each as its hull's vertices, ground frame at the base clearance"""
    global _COMP
    if _COMP is None:
        import chassis3 as C3, pose3 as P3
        skip = C3.MOD + ('armbase_', 'rest_peg') + STRUCT; _COMP = {}
        for k, v in P3.C()['pts'].items():
            if k.startswith(skip):
                continue
            P = np.asarray(v, float) - [0, 0, C3.G0]
            _COMP[k] = P[ConvexHull(P).vertices] if len(P) > 8 else P
    return _COMP


def build_x(x):
    """a knob vector padded to the current KEYS with the defaults"""
    x = list(map(float, x)); return x + NO_LIMB[len(x) - 18:] if len(x) < len(KEYS) else x


def build(x, name='gen'):
    """the robot spec of one design (a vector over KEYS), or None when it can't be built"""
    import chassis3 as C3
    x = build_x(x)
    p = dict(zip(KEYS, x))
    D = C3.design({k: p[k] for k in C3.KEYS})
    if not D['ok']:
        return None
    R = p['R']; items = list(D['items']); axles = list(D['axles'].values()); notes = []
    if p['six'] > 0.5:
        if p['xf'] - p['xr'] < 2 * (2 * R + 15):
            return None
        xm = 0.5 * (p['xf'] + p['xr'])
        for y in (C3.Y_W, -C3.Y_W):
            items.append(('motor_M' + ('L' if y > 0 else 'R'), 205.0 + 34.6, np.array([xm, np.sign(y) * 100.0, R]))); axles.append((xm, y))
        notes.append('six wheels')
    tr, msz, gr = p['track'], p['msize'], p['gear']                      # the drive's knobs (2026-10-26); at their defaults, as before
    if (tr, msz, gr) != (TRACK0, 1.0, 1.0):
        axles = [(xa, np.sign(ya) * tr) for xa, ya in axles]
        items = [(n, 205.0 * msz + 34.6, np.array([q[0], np.sign(q[1]) * (tr - 31.0), q[2]])) if n.startswith('motor_') else (n, m, q)
                 for n, m, q in items]                                    # each motor scales its mass and rides with its wheel
        if tr < TRACK0:                                                   # the Trainer's pods just fit at 131
            notes.append(f'motor {TRACK0 - tr:.0f} mm into the hull: repack')
    body = D['pts']; z0 = float(body[:, 2].min()); hulls = [body]
    if p['shell'] > 0.5:                                                  # the skin replaces the walls
        dz = p['clr'] - C3.base()['clr0']; pts = []
        for k, P in components().items():
            pts.append(P + [p['dxp'] if k.startswith('pack') else 0.0, 0.0, dz + (p['dzp'] if k.startswith('pack') else 0.0)])
        for xa, ya in axles:                                              # each motor, out to its tyre's inner face
            sg = np.sign(ya); yi = abs(ya) - 23.0
            pts.append(np.array([[xa + a, sg * b, R + c] for a in (-20.0, 20.0) for b in (70.0, yi) for c in (-20.0, 20.0)]))
        Q = shell_points(p, z0)
        skin = RB.hull(np.vstack(pts + ([Q] if Q is not None else [])))
        items = [it for it in items if not it[0].startswith(STRUCT)]
        M, G, I = RB.inertia(items, D['box'])
        ms, cs, Is = shell_mass(skin); M2 = M + ms; G2 = (M * G + ms * cs) / M2; d0, d1 = G - G2, cs - G2
        I = I + M * (d0 @ d0 * np.eye(3) - np.outer(d0, d0)) + Is + ms * (d1 @ d1 * np.eye(3) - np.outer(d1, d1)); M, G = M2, G2
        hulls = [skin]; notes.append(f'skin {ms:.0f} g, walls out')
    else:
        M, G, I = RB.inertia(items, D['box'])
    sp = RB.spec(name, hulls, M, G, I, axles, R, m_w=D['m_w'], I_w=D['I_w'], notes=notes)
    if (msz, gr) != (1.0, 1.0):                                           # a motor msize times the 37 mm one, geared gear times 30:1
        mo = sp['motor']; sp['motor'] = dict(stall=mo['stall'] * msz * gr, w0=mo['w0'] / gr, N=mo['N'] * gr, Ir=mo['Ir'] * msz)
        sp['notes'] = sp['notes'] + [f'motor x{msz:.2f}, gear x{gr:.2f}']
    if tr != TRACK0:
        sp['notes'] = sp['notes'] + [f'track {tr:.0f}']
    if p['limb'] > LIMB_ON:
        sp = RB.add_limb(sp, p['L'], p['tq'], p['th_push'], p['th_stow'], p['mz'], base=LIMB_BASE)
    sp['x'] = [float(v) for v in x]
    return sp


def nose(sp):
    """the tallest step (mm, 5 mm steps, at most R) a leading tyre can reach before any hull point below that height
    meets the step's face: the better of the two ends"""
    R = sp['R']; H = np.vstack(sp['hulls']); best = 0
    for sg in (1.0, -1.0):
        xa = max(sg * x for x, _ in sp['wheels']); X, Z = sg * H[:, 0], H[:, 2]; top = 0
        for h in range(5, int(R) + 1, 5):
            if np.any((X > xa + math.sqrt(max(R * R - (R - h) ** 2, 0.0)) - 1.0) & (Z < h)):
                break
            top = h
        best = max(best, top)
    return best


def com_all(sp):
    """the whole robot's centre of mass, ground frame: body, wheels and the tail stowed (its servos at its base, link
    and foot along it)"""
    G = sp['M'] * sp['com'] + sum(sp['m_w'] * np.array([x, y, sp['R']]) for x, y in sp['wheels']); lm = sp.get('limb')
    if lm:
        pts = RB.limb_points(lm, 0.0, lm['th_stow']); B, tip = np.asarray(lm['base']), pts[7]
        G = G + lm['m_base'] * B + lm['m_link'] * (B + tip) / 2 + lm['m_foot'] * tip
    return G / sp['mass']


def statics(sp):
    """cheap proxies: the static upright share and CoM margin (shell3), the footprint's diameter about the wheels'
    centre (G3 before drift) and the nose's step limit (G2 before traction)"""
    import shell3 as S3
    E = RB.extremes(sp, n=24); P = E[ConvexHull(E).vertices]; G = com_all(sp)
    share, states = S3.static(P, G)
    wc = np.mean(np.array(sp['wheels']), 0)
    return dict(static_up=float(share.get('upright', 0.0)), n_rest=len(states), margin=float(S3.margin(P, G)),
                turn_geo=float(2 * np.linalg.norm(E[:, :2] - wc, axis=1).max()), nose=float(nose(sp)), mass=sp['mass'],
                length=sp['length'], width=sp['width'], height=sp['height'])


def ladder_screen(sp, mu, rng):
    """the step ladder at one friction, 6 tries: a direction stops at its first miss, a height at its first passing
    direction, the ladder at its first failing height"""
    top = 0
    for h in GG.HEIGHTS:
        sim = GG.Sim(sp, mu, step=h); passed = False
        for back in (False, True):
            if all(GG.climb_try(sim, h, back, rng) for _ in range(N_TRY)):
                passed = True; break
        if not passed:
            break
        top = h
    return top


def screen_sim(sp, seed, climb_mus=(MU_CLIMB,)):
    """the screening sims: falls at x1, the ladder at each of climb_mus (the worst counts), the turn at every
    friction. climb_mus was x0.65 alone for stages B and C; the finals showed climbs that need low friction (S5: 50 mm
    at x0.65, 30 at x1.5), so stage E screens x0.65 and x1.5 (2026-10-26)."""
    rng = np.random.default_rng(seed)
    f = GG.falls(GG.Sim(sp, 1.0), N_FALL, rng); up = f.get('upright', 0) / N_FALL
    cm = {str(mu): ladder_screen(sp, mu, rng) for mu in climb_mus}
    tn = [GG.turn(GG.Sim(sp, mu), sg)[0] for mu in GG.BAND for sg in (1, -1)]
    return dict(up=up, falls=f, climb=min(cm.values()), climb_by_mu=cm, turn=None if any(t is None for t in tn) else max(tn))


# ---------- workers ----------
def _statics(a):
    i, x = a
    try:
        sp = build(x)
        return i, None if sp is None else statics(sp)
    except Exception as e:                                                # a degenerate hull: skip it, say how many
        return i, dict(error=repr(e)[:200])


def _screen(a):
    tag, x, seed = a[:3]; mus = a[3] if len(a) > 3 else (MU_CLIMB,)
    sp = build(x)
    if sp is None:
        return tag, list(map(float, x)), None
    s = screen_sim(sp, seed, mus); s.update(statics(sp))
    return tag, list(map(float, x)), s


def sobol(log2n, seed=7):
    from scipy.stats import qmc
    return qmc.scale(qmc.Sobol(len(KEYS), scramble=True, seed=seed).random_base2(log2n), LO, HI)


def stage_statics(log2n=15):
    os.makedirs(OUT, exist_ok=True); t0 = time.time(); X = sobol(log2n)
    with Pool(WORKERS) as pool:
        R = pool.map(_statics, list(enumerate(X)), chunksize=16)
    cols = ['static_up', 'n_rest', 'margin', 'turn_geo', 'nose', 'mass', 'length', 'width', 'height']
    A = np.full((len(X), len(cols)), np.nan); err = 0
    for i, r in R:
        if r is None:
            continue
        if 'error' in r:
            err += 1; continue
        A[i] = [r[c] for c in cols]
    np.savez(os.path.join(OUT, 'statics.npz'), X=X, A=A, cols=np.array(cols), keys=np.array(KEYS))
    ok = ~np.isnan(A[:, 0])
    print(f'statics: {len(X)} designs, {ok.sum()} built, {err} hull errors, {time.time() - t0:.0f} s; '
          f'one rest state {np.mean(A[ok, 1] == 1):.3f}, static up >= 0.75 {np.mean(A[ok, 0] >= 0.75):.3f}')


def load_statics():
    z = np.load(os.path.join(OUT, 'statics.npz')); return z['X'], z['A'], list(z['cols'])


def run_screens(jobs, tag, pool=None, fn=None):
    """jobs on the pool (a new one when None), appended to screen_<tag>.jsonl"""
    fn = fn or _screen
    if pool is None:
        with Pool(WORKERS) as p:
            R = p.map(fn, jobs, chunksize=1)
    else:
        R = pool.map(fn, jobs, chunksize=1)
    rows = [dict(tag=t, x=x, **s) for t, x, s in R if s is not None]
    with open(os.path.join(OUT, f'screen_{tag}.jsonl'), 'a') as f:
        for r in rows:
            f.write(json.dumps(r, default=float) + '\n')
    return rows


def calibrate(n=240):
    """the cheap proxies against the screening sims, on built designs drawn at random from A, plus the Trainer
    stand-in (its readings should sit near the built Trainer's: 0.45, 40 mm, 594 mm)"""
    X, A, cols = load_statics(); ok = np.where(~np.isnan(A[:, 0]))[0]
    pick = np.random.default_rng(1).choice(ok, n, replace=False)
    jobs = [('cal', X[i], 100 + int(i)) for i in pick] + [('base', np.array([BASE[k] for k in KEYS]), 7)]
    t0 = time.time(); rows = run_screens(jobs, 'calibrate'); print(f'{len(rows)} screened, {time.time() - t0:.0f} s')
    report(rows)


def report(rows):
    from scipy.stats import spearmanr
    cal = [r for r in rows if r['tag'] == 'cal']
    up = np.array([r['up'] for r in cal]); su = np.array([r['static_up'] for r in cal]); mg = np.array([r['margin'] for r in cal])
    one = np.array([r['n_rest'] == 1 for r in cal])
    cl = np.array([r['climb'] for r in cal]); ns = np.array([r['nose'] for r in cal])
    tn = np.array([np.nan if r['turn'] is None else r['turn'] for r in cal]); tg = np.array([r['turn_geo'] for r in cal])
    print(f'upright: sim vs static share rho {spearmanr(up, su)[0]:.2f}, vs margin rho {spearmanr(up, mg)[0]:.2f}; '
          f'sim >= {UP_SCREEN}: {np.mean(up >= UP_SCREEN):.3f} of all, {np.mean(up[one] >= UP_SCREEN) if one.any() else float("nan"):.3f} of '
          f'{one.sum()} with one rest state, {np.mean(up[~one] >= UP_SCREEN):.3f} of the rest')
    for t in (0.0, 0.3, 0.5, 0.7):
        sel = su >= t
        print(f'  static share >= {t}: {sel.sum()} designs, {np.mean(up[sel] >= UP_SCREEN) if sel.any() else 0:.3f} pass the screen bar; '
              f'it keeps {np.sum(sel & (up >= UP_SCREEN))} of {np.sum(up >= UP_SCREEN)} passers')
    print(f'climb: sim vs nose rho {spearmanr(cl, ns)[0]:.2f}; sim above nose in {np.mean(cl > ns + 5):.3f}; mean sim {cl.mean():.0f}, nose {ns.mean():.0f}')
    k = ~np.isnan(tn)
    print(f'turn: sim vs footprint rho {spearmanr(tn[k], tg[k])[0]:.2f}; drift (sim / footprint) {np.median(tn[k] / tg[k]):.3f} '
          f'[{np.percentile(tn[k] / tg[k], 5):.3f}, {np.percentile(tn[k] / tg[k], 95):.3f}]; can\'t spin {np.mean(~k):.3f}')
    for r in rows:
        if r['tag'] == 'base':
            print(f"Trainer stand-in: up {r['up']:.2f}, climb {r['climb']}, turn {r['turn'] and round(r['turn'])}, static up {r['static_up']:.2f}, nose {r['nose']}")


def front(rows, bar=UP_SCREEN):
    """the designs no other feasible one beats on both climb and turn"""
    F = [r for r in rows if r['up'] >= bar and r['turn'] is not None]
    return [r for r in F if not any((o['climb'] >= r['climb'] and o['turn'] <= r['turn']) and (o['climb'] > r['climb'] or o['turn'] < r['turn']) for o in F)]


def score(r, w):
    if r['up'] < UP_SCREEN or r['turn'] is None:
        return -1e9
    return -r['turn'] if w is None else r['climb'] - w * r['turn']


def search(n_b=1500, gens=8, pop=40):
    """B: screen the half of n_b that A's static upright share ranks highest and a random half (calibrate: the share
    tracks the sim only loosely, rho 0.43, so it enriches, it doesn't decide); C: cross-entropy from the best of B
    under each weighting"""
    X, A, cols = load_statics(); t0 = time.time()
    ok = np.where(~np.isnan(A[:, 0]))[0]; rng0 = np.random.default_rng(5)
    top = ok[np.argsort(-A[ok, 0])][:n_b // 2]
    rest = np.setdiff1d(ok, top); pool_ix = list(top) + list(rng0.choice(rest, n_b - len(top), replace=False))
    rows = run_screens([('B', X[i], 1000 + int(i)) for i in pool_ix], 'B')
    print(f'B: {len(rows)} screened of {len(ok)} built, {time.time() - t0:.0f} s; feasible {sum(r["up"] >= UP_SCREEN for r in rows)}; '
          f'front {[(r["climb"], round(r["turn"])) for r in sorted(front(rows), key=lambda r: r["climb"])]}', flush=True)
    allr = list(rows); rng = np.random.default_rng(11); span = HI - LO
    for w in W:
        el = sorted(allr, key=lambda r: -score(r, w))[:8]
        E = np.array([r['x'] for r in el]); mu, sd = E.mean(0), np.maximum(E.std(0), 0.05 * span)
        for g in range(gens):
            P = np.clip(mu + sd * rng.normal(size=(pop, len(KEYS))), LO, HI)
            new = run_screens([(f'C{w}', x, 5000 + 97 * g + i + int(1e4 * (0 if w is None else w + 1))) for i, x in enumerate(P)], 'C')
            allr += new
            el = sorted(el + new, key=lambda r: -score(r, w))[:8]
            Eg = np.array([r['x'] for r in el]); mu = 0.6 * Eg.mean(0) + 0.4 * mu; sd = np.maximum(0.6 * Eg.std(0) + 0.4 * sd * 0.8, 0.01 * span)
            b = el[0]
            print(f'C w={w}: gen {g} best climb {b["climb"]} turn {b["turn"] and round(b["turn"])} up {b["up"]:.2f}; '
                  f'{sum(score(r, w) > -1e8 for r in new)} of {len(new)} feasible; {time.time() - t0:.0f} s', flush=True)
    F = sorted(front(allr), key=lambda r: r['climb'])
    json.dump(dict(wall_s=round(time.time() - t0), n=len(allr), front=F), open(os.path.join(OUT, 'front.json'), 'w'), indent=1, default=float)
    print('front:', [(r['climb'], round(r['turn']), round(r['up'], 2), r['n_rest']) for r in F])


BAND_CLIMB = (0.65, 1.5)


def search_band(n_top=300, gens=8, pop=40):
    """E: B and C's best climbers re-screened with the climb at the worst of x0.65 and x1.5, then cross-entropy
    under the climb-heavy weightings with that screen"""
    rows = [json.loads(l) for tag in ('B', 'C') for l in open(os.path.join(OUT, f'screen_{tag}.jsonl'))]
    feas = sorted([r for r in rows if r['up'] >= UP_SCREEN and r['turn'] is not None], key=lambda r: (-r['climb'], r['turn']))
    pick = []
    for r in feas:
        if all(np.abs((np.array(r['x']) - np.array(o['x'])) / (HI - LO)).max() > 0.02 for o in pick):
            pick.append(r)
        if len(pick) >= n_top:
            break
    t0 = time.time()
    allr = run_screens([('E', np.array(r['x']), 20000 + i, BAND_CLIMB) for i, r in enumerate(pick)], 'E')
    print(f'E: {len(allr)} re-screened, {time.time() - t0:.0f} s; climb then {[r["climb"] for r in pick[:10]]}, now '
          f'{[r["climb"] for r in sorted(allr, key=lambda r: -r["climb"])[:10]]}; front {[(r["climb"], round(r["turn"])) for r in sorted(front(allr), key=lambda r: r["climb"])]}', flush=True)
    rng = np.random.default_rng(13); span = HI - LO
    for w in (0.0, 0.25):
        el = sorted(allr, key=lambda r: -score(r, w))[:8]
        E = np.array([r['x'] for r in el]); mu, sd = E.mean(0), np.maximum(E.std(0), 0.05 * span)
        for g in range(gens):
            P = np.clip(mu + sd * rng.normal(size=(pop, len(KEYS))), LO, HI)
            new = run_screens([(f'E{w}', x, 30000 + 97 * g + i + int(1e4 * w), BAND_CLIMB) for i, x in enumerate(P)], 'E')
            allr += new; el = sorted(el + new, key=lambda r: -score(r, w))[:8]
            Eg = np.array([r['x'] for r in el]); mu = 0.6 * Eg.mean(0) + 0.4 * mu; sd = np.maximum(0.6 * Eg.std(0) + 0.4 * sd * 0.8, 0.01 * span)
            b = el[0]
            print(f'E w={w}: gen {g} best climb {b["climb"]} {b.get("climb_by_mu")} turn {b["turn"] and round(b["turn"])} up {b["up"]:.2f}; {time.time() - t0:.0f} s', flush=True)
    F = sorted(front(allr), key=lambda r: r['climb'])
    json.dump(dict(wall_s=round(time.time() - t0), n=len(allr), front=F), open(os.path.join(OUT, 'front_band.json'), 'w'), indent=1, default=float)
    print('front (band-screened):', [(r['climb'], round(r['turn']), round(r['up'], 2)) for r in F])


def search_limb(n_b=1500, gens=8, pop=40):
    """the family with the tail (run with SCORPION_SEARCH=search_limb): B, 1500 Sobol designs screened directly (a
    tail's righting is a motion, so the rest-state statics can't rank them), then cross-entropy under the four
    weightings; the climb screened at the worse of x0.65 and x1.5 from the start"""
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    X = list(sobol(int(math.ceil(math.log2(n_b))), seed=17)[:n_b])
    prev = os.path.join(config.GAUGES_OUT, 'search_limb', 'front.json')   # a later family starts with the last one's front in it
    if RUN != 'search_limb' and os.path.isfile(prev):
        X += [np.array(build_x(r['x'])) for r in json.load(open(prev))['front']]
    allr = run_screens([('B', x, 40000 + i, BAND_CLIMB) for i, x in enumerate(X)], 'B')
    feas = [r for r in allr if r['up'] >= UP_SCREEN]
    print(f'B: {len(allr)} screened, {time.time() - t0:.0f} s; feasible {len(feas)} ({sum(r["x"][18] > LIMB_ON for r in feas)} with a tail); '
          f'front {[(r["climb"], round(r["turn"])) for r in sorted(front(allr), key=lambda r: r["climb"])]}', flush=True)
    rng = np.random.default_rng(23); span = HI - LO
    for w in W:
        el = sorted(allr, key=lambda r: -score(r, w))[:8]
        E = np.array([r['x'] for r in el]); mu, sd = E.mean(0), np.maximum(E.std(0), 0.05 * span)
        for g in range(gens):
            P = np.clip(mu + sd * rng.normal(size=(pop, len(KEYS))), LO, HI)
            new = run_screens([(f'C{w}', x, 50000 + 97 * g + i + int(1e4 * (0 if w is None else w + 1)), BAND_CLIMB) for i, x in enumerate(P)], 'C')
            allr += new; el = sorted(el + new, key=lambda r: -score(r, w))[:8]
            Eg = np.array([r['x'] for r in el]); mu = 0.6 * Eg.mean(0) + 0.4 * mu; sd = np.maximum(0.6 * Eg.std(0) + 0.4 * sd * 0.8, 0.01 * span)
            b = el[0]
            print(f'{tag} w={w}: gen {g} best climb {b["climb"]} turn {b["turn"] and round(b["turn"])} up {b["up"]:.2f} tail {b["x"][18] > LIMB_ON}; '
                  f'{sum(score(r, w) > -1e8 for r in new)} of {len(new)} feasible; {time.time() - t0:.0f} s', flush=True)
    F = sorted(front(allr), key=lambda r: r['climb'])
    json.dump(dict(wall_s=round(time.time() - t0), n=len(allr), front=F), open(os.path.join(OUT, 'front.json'), 'w'), indent=1, default=float)
    print('front:', [(r['climb'], round(r['turn']), round(r['up'], 2), r['x'][18] > LIMB_ON) for r in F])


# ---------- the lean search (2026-10-27) ----------
# The review of search_drive (docs/decisions.md, 2026-10-27): 39 % of its Sobol draws couldn't be built (tyres
# overlapping), its short-wheelbase winners sat on xr's -40 limit, the screen read upright 0.05 high (40 falls at x1;
# the finals' worst was x1.5 in 9 of 14), and two of the four cross-entropy runs never improved. So the lean search
# draws the wheels as a centre and a tyre gap (every draw builds), screens falls at x1.5 and x0.65, and stops each
# cross-entropy run after 3 generations without a gain. The vectors it stores are still the 27 KEYS, so build() and the
# pages read them as before.
# The review also called 14 knobs dead (random-forest importance under 1 % on random designs). frozen_check says not
# near the front: redrawn together, T10 went 0.94 / 100 / 404 to 0.76 / 54 / 505. frozen_each, one at a time, cleared
# three: the middle axle (every six-wheel draw hurt all three finalists), the packs' height, and the motor's size (held
# at the stock motor: the drive search's ~1x). Those stay frozen at T10's; the packs' place, the push angle and the
# tail's mount height came back. The skin's eight shape knobs move a skinned design's climb (T5), but are held at T5's
# (the skin and tail finalist) by choice: the search drops the skin once a tail rights it.
# Bisecting the climb ladder was dropped: 12 of the drive finals' 42 ladders aren't monotone (T1 at x0.65 climbs
# 10-30 and 80-100 mm, fails 40-70).
SPACE = [('R', 35.0, 95.0), ('xw', -80.0, 80.0), ('gap', 15.0, 150.0), ('clr', 15.0, 90.0), ('dxp', -80.0, 80.0), ('shell', 0.0, 1.0),
         ('zc', 30.0, 200.0), ('cu', 40.0, 320.0), ('limb', 0.0, 1.0), ('L', 80.0, 350.0), ('tq', 0.3, 4.0), ('th_push', -90.0, -10.0),
         ('th_stow', 20.0, 160.0), ('mz', 0.2, 1.0), ('track', 110.0, 180.0), ('gear', 0.4, 2.5)]
FROZEN = dict(dzp=0.56, six=0.0, msize=1.0,                                                     # T10's; the stock motor
              xc=1.76, af=240.7, ar=206.9, b=197.4, cd=122.2, p=2.74, qu=2.43, qd=1.74)          # T5's skin
# frozen_check and frozen_each read the first frozen set (14 knobs: these and dxp, th_push, mz at T10's -> out/search_lean)
# The body search (SCORPION_SEARCH=search_body, 2026-10-27): Zach, seeing the finalists, "the shape of the body does not
# change much between these unless its the shell ... it could be another knob we can turn". Without a skin a design
# wears the Trainer's body, which has no knobs; the skin's shape was held. So the skin's eight shape knobs search again
# (24 knobs). The smallest skin they allow wraps T12's parts in 312 g, against the Trainer's walls' 416 and T5's 971.
# It runs on G2's new step reflex (gauges.climb_try), seeded from the start with the lean and drive searches' designs.
if RUN == 'search_body':
    SPACE = SPACE + [('xc', -40.0, 60.0), ('af', 120.0, 320.0), ('ar', 120.0, 320.0), ('b', 100.0, 300.0), ('cd', 20.0, 250.0),
                     ('p', 1.6, 5.0), ('qu', 1.0, 4.0), ('qd', 1.0, 4.0)]
    FROZEN = dict(dzp=0.56, six=0.0, msize=1.0)
# The shape study (SCORPION_SEARCH=search_shape, 2026-10-27): Zach, after T5: "lets try to refine tight skins. with
# the tail covering most of what the sobol shape was giving us lets see what body shape can give us for climb and
# maneuverability ... lock some knobs at a constant since were testing how a new shape effects this". Everything but
# the skin's ten shape knobs is held at T5's: wheels, drive, insides, tail. The tail's mount is pinned where T5 has
# it (it otherwise follows the hull: the tight-skin test moved it 73 mm down and lost about 40 mm of climb), so a
# shape that ends short of it carries it on a bracket and one that reaches past it has a slot. The ranges stop at
# skins a little bigger than T5's, not the wheel-covering shells (b to 200 mm: the tyres' outer faces are at 137).
LIMB_BASE = None
if RUN == 'search_shape':
    FROZEN = dict(R=44.908, xw=14.684, gap=62.052, clr=51.943, dxp=23.189, dzp=0.56, six=0.0, shell=1.0, limb=1.0, L=279.186,
                  tq=3.306, th_push=-46.177, th_stow=111.658, mz=0.431, track=113.977, msize=1.0, gear=2.091)   # T5's
    SPACE = [('xc', -40.0, 60.0), ('af', 120.0, 260.0), ('ar', 120.0, 260.0), ('b', 100.0, 200.0), ('zc', 30.0, 220.0),
             ('cu', 40.0, 250.0), ('cd', 20.0, 150.0), ('p', 1.6, 5.0), ('qu', 1.0, 4.0), ('qd', 1.0, 4.0)]
    LIMB_BASE = (-154.83, 0.0, 149.6)                                     # T5's mount, mm
# The hills run (SCORPION_SEARCH=search_hills, 2026-10-27): the hill gauges found the descent set by the locked
# wheelbase and centre of mass. Zach: "unlock those yes". So the wheels' size, centre and gap and the packs' place
# search, the rest held at the shape study's T3 (its skin, on T5's platform and tail), the tail's mount pinned as there.
if RUN == 'search_hills':
    FROZEN = dict(clr=51.943, six=0.0, shell=1.0, xc=27.025, af=166.408, ar=156.628, b=120.606, zc=159.624, cu=71.913, cd=71.847,
                  p=3.26, qu=2.256, qd=2.565, limb=1.0, L=279.186, tq=3.306, th_push=-46.177, th_stow=111.658, mz=0.431,
                  track=113.977, msize=1.0, gear=2.091)                   # T3's
    SPACE = [('R', 35.0, 95.0), ('xw', -80.0, 80.0), ('gap', 15.0, 150.0), ('dxp', -80.0, 80.0), ('dzp', -8.0, 15.0)]
    LIMB_BASE = (-154.83, 0.0, 149.6)
T3_PLAT = dict(R=44.908, xw=14.684, gap=62.052, dxp=23.189, dzp=0.56)    # T3's wheels and packs
T5_SHAPE =dict(xc=7.319, af=197.941, ar=146.141, b=149.966, zc=177.329, cu=167.509, cd=72.181, p=3.0, qu=2.771, qd=2.023)
ZK = [k for k, _, _ in SPACE]; ZLO = np.array([a for _, a, _ in SPACE]); ZHI = np.array([b for _, _, b in SPACE])
SEED_FROM = {'search_body': ('search_lean', 'search_drive')}.get(RUN, ())  # earlier runs whose fronts and finalists seed B
FALL_MU, N_FALL_MU = (1.5, 0.65), 30                                      # falls: the worst friction first, 30 at each
PATIENCE, MIN_GAIN = 3, 2.0                                               # a run stops after 3 generations without a 2-point gain


def to_x(z, frozen=FROZEN):
    """a lean vector (ZK) as the 27 KEYS: xf and xr from the wheelbase centre xw and the tyre gap"""
    q = dict(zip(ZK, map(float, z))); q.update(frozen)
    wb = 2 * q['R'] + q['gap'] if q['six'] <= 0.5 else 2 * (2 * q['R'] + q['gap'])
    q['xf'], q['xr'] = q['xw'] + wb / 2, q['xw'] - wb / 2
    return np.array([q[k] for k in KEYS])


def to_z(x):
    """a 27-KEY vector in the lean space, clipped to its ranges (the frozen knobs dropped)"""
    q = dict(zip(KEYS, build_x(x))); wb = q['xf'] - q['xr']
    q['xw'] = (q['xf'] + q['xr']) / 2; q['gap'] = (wb / 2 if q['six'] > 0.5 else wb) - 2 * q['R']
    return np.clip([q[k] for k in ZK], ZLO, ZHI)


def ladder_lean(sp, mu, seed, cap=None):
    """the step ladder at one friction, 6 tries, as ladder_screen; it stops past cap (the climb is the worst over the
    frictions, so the second needn't go higher than the first). Each height's tries draw from (seed, mu, height): the
    same yaws for every design given one seed."""
    top = 0
    for h in GG.HEIGHTS:
        if cap is not None and h > cap:
            break
        sim = GG.Sim(sp, mu, step=h); rng = np.random.default_rng([seed, int(round(100 * mu)), h]); passed = False
        for back in (False, True):
            if all(GG.climb_try(sim, h, back, rng) for _ in range(N_TRY)):
                passed = True; break
        if not passed:
            break
        top = h
    return top


def screen_lean(sp, seed, cut=True):
    """the lean screen: 30 falls at x1.5, then 30 at x0.65 (each from (seed, friction): the same starts for every design
    given one seed), the worse counting; cut once the bar can't be met, and then no climb. Above the bar, the ladder at
    x0.65 and x1.5, the second no higher than the first; the turn at every friction."""
    up, falls = {}, {}
    for mu in FALL_MU:
        rng = np.random.default_rng([seed, int(round(100 * mu))])
        f = GG.falls(GG.Sim(sp, mu), N_FALL_MU, rng, bar=UP_SCREEN if cut else None)
        n = sum(f.values()); falls[str(mu)] = f
        up[str(mu)] = (f.get('upright', 0) + N_FALL_MU - n) / N_FALL_MU   # a cut run: the most it could have read, under the bar
        if cut and up[str(mu)] < UP_SCREEN:
            break
    u = min(up.values()); cm = {}
    if u >= UP_SCREEN or not cut:
        for mu in BAND_CLIMB:
            cm[str(mu)] = ladder_lean(sp, mu, seed, cap=min(cm.values()) if cm else None)
    tn = [GG.turn(GG.Sim(sp, mu), sg)[0] for mu in GG.BAND for sg in (1, -1)]
    return dict(up=u, up_by_mu=up, falls=falls, cut=bool(u < UP_SCREEN and cut), climb=min(cm.values()) if cm else None,
                climb_by_mu=cm, turn=None if any(t is None for t in tn) else max(tn))


def _screen_lean(a):
    tag, z, seed = a[:3]; frozen = a[3] if len(a) > 3 else FROZEN; cut = a[4] if len(a) > 4 else True
    x = to_x(z, frozen); sp = build(x)
    if sp is None:
        return tag, list(map(float, x)), None
    s = screen_lean(sp, seed, cut); s.update(statics(sp)); s['z'] = list(map(float, z))
    return tag, list(map(float, x)), s


def cem(allr, w, pool, rng, tag, seed0, gens=8, pop=40, t0=0.0, lo=None, hi=None, fn=None, sc=None):
    """one cross-entropy run in the lean space under weighting w, from the best 8 of allr; it stops after PATIENCE
    generations without a MIN_GAIN gain. Each generation's designs share one seed (the same falls and climb yaws).
    fn and sc swap the screen and the score (hills.py)."""
    lo = ZLO if lo is None else lo; hi = ZHI if hi is None else hi                  # narrower bounds hold a knob (skin_refine)
    fn = fn or _screen_lean; sc = sc or score
    span = ZHI - ZLO; el = sorted(allr, key=lambda r: -sc(r, w))[:8]; new_all = []
    E = np.array([r['z'] for r in el]); mu, sd = E.mean(0), np.maximum(E.std(0), 0.05 * span)
    best, idle = sc(el[0], w), 0
    for g in range(gens):
        Z = np.clip(mu + sd * rng.normal(size=(pop, len(ZK))), lo, hi)
        new = run_screens([(f'{tag}{w}', z, seed0 + g) for z in Z], tag, pool, fn)
        new_all += new; el = sorted(el + new, key=lambda r: -sc(r, w))[:8]
        Eg = np.array([r['z'] for r in el]); mu = 0.6 * Eg.mean(0) + 0.4 * mu; sd = np.maximum(0.6 * Eg.std(0) + 0.4 * sd * 0.8, 0.01 * span)
        b = el[0]; s = sc(b, w)
        idle = 0 if s > best + MIN_GAIN else idle + 1; best = max(best, s)
        hills = f' hills {b["h_up"]}/{b["h_down"]}' if b.get('h_down') is not None else ''
        print(f'{tag} w={w}: gen {g} best climb {b["climb"]} turn {b["turn"] and round(b["turn"])} up {b["up"]:.2f} tail {b["x"][18] > LIMB_ON}{hills}; '
              f'{sum(sc(r, w) > -1e8 for r in new)} of {len(new)} feasible; {time.time() - t0:.0f} s', flush=True)
        if idle >= PATIENCE:
            print(f'{tag} w={w}: no gain in {PATIENCE} generations, stopped', flush=True); break
    return new_all, g + 1


def search_lean(n_b=1024, gens=8, pop=60):
    """B: n_b Sobol designs in the lean space, screened on the lean screen; C: cross-entropy under the four weightings.
    One worker pool for the whole run (a new one each generation cost ~8 s); 60 a generation, two rounds of the 30
    workers, where 40 left 20 idle in the second. Run with SCORPION_SEARCH=search_lean."""
    os.makedirs(OUT, exist_ok=True); t0 = time.time()
    from scipy.stats import qmc
    Z = qmc.scale(qmc.Sobol(len(ZK), scramble=True, seed=17).random_base2(int(math.ceil(math.log2(n_b)))), ZLO, ZHI)[:n_b]
    with Pool(WORKERS) as pool:
        allr = run_screens([('B', z, 40000) for z in Z], 'B', pool, _screen_lean)
        if SEED_FROM:                                                     # the seeds, on the same falls
            X = []
            for run in SEED_FROM:
                d = os.path.join(config.GAUGES_OUT, run)
                X += [r['x'] for r in json.load(open(os.path.join(d, 'front.json')))['front']]
                X += [f['x'] for f in json.load(open(os.path.join(d, 'finals.json')))['finals'] if f.get('x') is not None and not f.get('control')]
            Zs = []
            for x in X:
                z = to_z(x)
                if all(np.abs((z - o) / (ZHI - ZLO)).max() > 1e-6 for o in Zs):
                    Zs.append(z)
            S_ = run_screens([('S', z, 40000) for z in Zs], 'S', pool, _screen_lean); allr += S_
            print(f'S: {len(S_)} seeds from {SEED_FROM}', flush=True)
        if RUN == 'search_shape':                                         # T5's own shape and the tightest skin
            Zs = [np.array([T5_SHAPE[k] for k in ZK]), np.array([TIGHT[k] for k in ZK])]
            S_ = run_screens([('S', z, 40000) for z in Zs], 'S', pool, _screen_lean); allr += S_
            print(f'S: T5 {[(round(r["up"], 2), r["climb"], r["turn"] and round(r["turn"])) for r in S_]} (T5, tightest)', flush=True)
        feas = [r for r in allr if r['up'] >= UP_SCREEN]
        print(f'B: {len(allr)} screened of {len(Z)}, {time.time() - t0:.0f} s; feasible {len(feas)} ({sum(r["x"][18] > LIMB_ON for r in feas)} with a tail), '
              f'{sum(r["cut"] for r in allr)} cut; front {[(r["climb"], round(r["turn"])) for r in sorted(front(allr), key=lambda r: r["climb"])]}', flush=True)
        rng = np.random.default_rng(23); gens_run = {}
        for j, w in enumerate(W):
            new, gens_run[str(w)] = cem(allr, w, pool, rng, 'C', 50000 + 100 * j, gens, pop, t0); allr += new
    F = sorted(front(allr), key=lambda r: r['climb'])
    json.dump(dict(wall_s=round(time.time() - t0), n=len(allr), gens=gens_run, front=F), open(os.path.join(OUT, 'front.json'), 'w'), indent=1, default=float)
    print(f'front ({time.time() - t0:.0f} s, {len(allr)} screened):', [(r['climb'], round(r['turn']), round(r['up'], 2), r['x'][18] > LIMB_ON) for r in F])


def seed_refine(gens=8, pop=60):
    """after search_lean: S, the drive search's front and finalists in the lean family (its frozen knobs set to FROZEN),
    on the lean screen; R, cross-entropy under w=0.25 and w=1 (the middle of the front, where the unseeded search
    stopped short of T10) from everything screened. Writes front_seeded.json."""
    src = os.path.join(config.GAUGES_OUT, 'search_drive'); t0 = time.time()
    X = [r['x'] for r in json.load(open(os.path.join(src, 'front.json')))['front']]
    X += [f['x'] for f in json.load(open(os.path.join(src, 'finals.json')))['finals'] if f.get('x') is not None and not f.get('control')]
    Z = []
    for x in X:
        z = to_z(x)
        if all(np.abs((z - o) / (ZHI - ZLO)).max() > 1e-6 for o in Z):
            Z.append(z)
    allr = [json.loads(l) for t in ('B', 'C') for l in open(os.path.join(OUT, f'screen_{t}.jsonl'))]
    with Pool(WORKERS) as pool:
        S = run_screens([('S', z, 40000) for z in Z], 'S', pool, _screen_lean); allr += S
        print(f'S: {len(S)} seeds re-screened, {time.time() - t0:.0f} s: {[(round(r["up"], 2), r["climb"], r["turn"] and round(r["turn"])) for r in S]}', flush=True)
        rng = np.random.default_rng(29); gens_run = {}
        for j, w in enumerate((0.25, 1.0)):
            new, gens_run[str(w)] = cem(allr, w, pool, rng, 'R', 60000 + 100 * j, gens, pop, t0); allr += new
    F = sorted(front(allr), key=lambda r: r['climb'])
    json.dump(dict(wall_s=round(time.time() - t0), n=len(allr), gens=gens_run, front=F), open(os.path.join(OUT, 'front_seeded.json'), 'w'), indent=1, default=float)
    print(f'front, seeded ({time.time() - t0:.0f} s):', [(r['climb'], round(r['turn']), round(r['up'], 2), r['tag']) for r in F])


TIGHT = dict(shell=1.0, xc=10.0, af=120.0, ar=120.0, b=100.0, zc=60.0, cu=40.0, cd=20.0, p=3.0, qu=3.0, qd=3.0)   # the smallest skin


def skin_refine(gens=8, pop=60):
    """after search_body: K, cross-entropy with the skin on (shell held at 0.6 and up) under w=0.25 and w=1, from the
    best skinned designs and the body finalists put in the tightest skin. The body search kept the Trainer's body:
    its random skins were mostly big (median 4.1 kg, 402 mm wide), and its refinements started from skinless designs.
    The finalists in a tight skin were 80-130 g lighter and 55 mm shorter but climbed about 40 mm less, their tails
    tuned for the Trainer's body. Writes front_skin.json."""
    t0 = time.time(); allr = [json.loads(l) for t in ('B', 'C', 'S') for l in open(os.path.join(OUT, f'screen_{t}.jsonl'))]
    F = json.load(open(os.path.join(OUT, 'finals.json')))['finals']
    Zt = [to_z([dict(zip(KEYS, build_x(f['x'])), **TIGHT)[k] for k in KEYS]) for f in F if f.get('x') and not f.get('control') and f['x'][18] > LIMB_ON]
    lo = ZLO.copy(); lo[ZK.index('shell')] = 0.6
    with Pool(WORKERS) as pool:
        K = run_screens([('K', z, 40000) for z in Zt], 'K', pool, _screen_lean)
        skins = [r for r in allr if r['x'][7] > 0.5] + K
        print(f'K: {len(K)} finalists in a tight skin: {[(round(r["up"], 2), r["climb"], r["turn"] and round(r["turn"])) for r in K]}', flush=True)
        rng = np.random.default_rng(31); gens_run = {}
        for j, w in enumerate((0.25, 1.0)):
            new, gens_run[str(w)] = cem(skins, w, pool, rng, 'K', 90000 + 100 * j, gens, pop, t0, lo=lo); skins += new
    Fk = sorted(front(skins), key=lambda r: r['climb'])
    json.dump(dict(wall_s=round(time.time() - t0), n=len(skins), gens=gens_run, front=Fk), open(os.path.join(OUT, 'front_skin.json'), 'w'), indent=1, default=float)
    print(f'skinned front ({time.time() - t0:.0f} s):', [(r['climb'], round(r['turn']), round(r['up'], 2), round(r['mass'])) for r in Fk])


def shape_sweep(n=7, seeds=3):
    """the shape study's knobs one at a time: each at n values across its range, the rest at T5's shape, on the lean
    screen without its cut, seeds seeds each, T5 beside them. Writes shape_sweep.json."""
    base = np.array([T5_SHAPE[k] for k in ZK]); jobs = [('T5|0', base, 85000 + s_, FROZEN, False) for s_ in range(seeds)]
    for j, k in enumerate(ZK):
        for v in np.linspace(ZLO[j], ZHI[j], n):
            z = base.copy(); z[j] = v
            jobs += [(f'{k}|{v:.6g}', z, 85000 + s_, FROZEN, False) for s_ in range(seeds)]
    t0 = time.time()
    with Pool(WORKERS) as pool:
        R = pool.map(_screen_lean, jobs, chunksize=1)
    out = {}
    for tag, x, s in R:
        k, v = tag.split('|'); out.setdefault(k, {}).setdefault(float(v), []).append(s)
    res = {}
    for k, vs in out.items():
        res[k] = []
        for v, ss in sorted(vs.items()):
            ss = [q for q in ss if q is not None]
            res[k].append(dict(v=v, up=float(np.mean([q['up'] for q in ss])), climb=float(np.mean([q['climb'] for q in ss])), climb_min=min(q['climb'] for q in ss),
                               turn=float(np.mean([q['turn'] or np.nan for q in ss])), mass=float(np.mean([q['mass'] for q in ss])),
                               length=float(np.mean([q['length'] for q in ss])), width=float(np.mean([q['width'] for q in ss])), height=float(np.mean([q['height'] for q in ss]))))
        print(f'{k:4s} ' + '  '.join(f"{r['v']:.3g}: {r['up']:.2f}/{r['climb']:.0f}/{r['turn']:.0f}" for r in res[k]), flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), seeds=seeds, t5=T5_SHAPE, ranges={k: (a, b) for k, a, b in SPACE}, results=res),
              open(os.path.join(OUT, 'shape_sweep.json'), 'w'), indent=1, default=float)
    print(f'{len(jobs)} screens, {time.time() - t0:.0f} s')


def frozen_check(src=None, names=('T10', 'T5', 'T6', 'T3'), n=8):
    """are the frozen knobs dead? Each finalist of src (the drive search) re-screened n times in four ways, on the
    lean screen without its cut: as it is with fresh seeds (the screen's noise); in the lean space (its frozen knobs
    set to FROZEN, its wheels through xw and gap: the lean family's version of it); with every frozen knob redrawn at
    random over its old range (the claim: no gauge moves past the noise); with L and tq redrawn (the control: they
    must move one). Writes frozen_check.json."""
    src = src or os.path.join(config.GAUGES_OUT, 'search_drive')
    F = {f['name']: f for f in json.load(open(os.path.join(src, 'finals.json')))['finals']}
    rng = np.random.default_rng(3); jobs = []
    lo = dict(zip(KEYS, LO)); hi = dict(zip(KEYS, HI))
    for nm in names:
        x = np.array(build_x(F[nm]['x'])); z = to_z(x); own = {k: v for k, v in zip(KEYS, x) if k in FROZEN}
        for i in range(n):
            s = 70000 + i                                                 # the four ways share their seeds
            jobs.append((f'{nm}|noise', z, s, own, False))
            jobs.append((f'{nm}|lean', z, s, FROZEN, False))
            jobs.append((f'{nm}|frozen', z, s, {k: float(rng.uniform(lo[k], hi[k])) for k in FROZEN}, False))
            zc = z.copy()
            for k in ('L', 'tq'):
                j = ZK.index(k); zc[j] = rng.uniform(ZLO[j], ZHI[j])
            jobs.append((f'{nm}|control', zc, s, own, False))
    t0 = time.time()
    with Pool(WORKERS) as pool:
        R = pool.map(_screen_lean, jobs, chunksize=1)
    out = {}
    for tag, x, s in R:
        nm, way = tag.split('|'); out.setdefault(nm, {}).setdefault(way, []).append(
            None if s is None else dict(up=s['up'], climb=s['climb'], turn=s['turn'], x=x))
    res = {}
    for nm, ways in out.items():
        res[nm] = {}
        for way, rs in ways.items():
            ok = [r for r in rs if r is not None]
            st = {}
            for g in ('up', 'climb', 'turn'):
                v = np.array([np.nan if r[g] is None else r[g] for r in ok], float)
                st[g] = dict(mean=float(np.nanmean(v)) if np.isfinite(v).any() else None, sd=float(np.nanstd(v)) if np.isfinite(v).any() else None,
                             n=int(np.isfinite(v).sum()))
            res[nm][way] = dict(built=len(ok), of=len(rs), **st)
        print(nm, '  '.join(f"{way}: up {d['up']['mean'] and round(d['up']['mean'], 3)}±{d['up']['sd'] and round(d['up']['sd'], 3)} "
                            f"climb {d['climb']['mean'] and round(d['climb']['mean'])}±{d['climb']['sd'] and round(d['climb']['sd'])} "
                            f"turn {d['turn']['mean'] and round(d['turn']['mean'])} ({d['built']}/{d['of']})" for way, d in res[nm].items()), flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), n=n, frozen=FROZEN, results=res, raw=out), open(os.path.join(OUT, 'frozen_check.json'), 'w'), indent=1, default=float)
    print(f'{len(jobs)} screens, {time.time() - t0:.0f} s')


SKIN = ('xc', 'af', 'ar', 'b', 'cd', 'p', 'qu', 'qd')


def frozen_each(src=None, names=('T10', 'T6', 'T5'), n=6):
    """frozen_check one knob at a time: each finalist with one frozen knob redrawn over its old range (the skin's
    only on a design with a skin; without one they aren't read), beside its noise. Writes frozen_each.json."""
    src = src or os.path.join(config.GAUGES_OUT, 'search_drive')
    F = {f['name']: f for f in json.load(open(os.path.join(src, 'finals.json')))['finals']}
    rng = np.random.default_rng(4); jobs = []; lo = dict(zip(KEYS, LO)); hi = dict(zip(KEYS, HI))
    for nm in names:
        x = np.array(build_x(F[nm]['x'])); z = to_z(x); own = {k: v for k, v in zip(KEYS, x) if k in FROZEN}
        knobs = [k for k in FROZEN if x[7] > 0.5 or k not in SKIN]
        for i in range(n):
            jobs.append((f'{nm}|noise', z, 71000 + i, own, False))
            for k in knobs:
                jobs.append((f'{nm}|{k}', z, 71000 + i, dict(own, **{k: float(rng.uniform(lo[k], hi[k]))}), False))
    t0 = time.time()
    with Pool(WORKERS) as pool:
        R = pool.map(_screen_lean, jobs, chunksize=1)
    out = {}
    for (tag, x, s), j in zip(R, jobs):
        nm, k = tag.split('|')
        out.setdefault(nm, {}).setdefault(k, []).append(None if s is None else dict(v=None if k == 'noise' else j[3][k], up=s['up'], climb=s['climb'], turn=s['turn']))
    for nm, ks in out.items():
        print(nm)
        for k, rs in ks.items():
            ok = [r for r in rs if r is not None]
            print(f"  {k:8s} up {np.mean([r['up'] for r in ok]):.3f} (min {min(r['up'] for r in ok):.2f})  climb {np.mean([r['climb'] for r in ok]):.0f} "
                  f"(min {min(r['climb'] for r in ok)})  turn {np.mean([r['turn'] or 9999 for r in ok]):.0f} (max {max(r['turn'] or 9999 for r in ok):.0f})  "
                  f"{len(ok)}/{len(rs)} built" + ('' if k == 'noise' else f"  values {[round(r['v'], 2) for r in ok]}"), flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), n=n, results=out), open(os.path.join(OUT, 'frozen_each.json'), 'w'), indent=1, default=float)
    print(f'{len(jobs)} screens, {time.time() - t0:.0f} s')


def reclimb(tag='reflex1'):
    """the finals' G2 read again after a change to the climb (2026-10-27: the step reflex), the same designs and seeds;
    the old finals.json kept as 'superseded - finals_<tag>.json'"""
    import pickle, shutil
    fp = os.path.join(OUT, 'finals.json'); F = json.load(open(fp)); allsp = pickle.load(open(os.path.join(OUT, 'finals_specs.pkl'), 'rb'))
    J = [j for i in range(len(allsp)) for j in GG.jobs_for(i, GG.N_DROP, GG.N_TRY, seed=31) if j[0] == 'climb']
    t0 = time.time()
    with Pool(WORKERS, initializer=GG._init, initargs=(allsp,)) as pool:
        R = pool.map(GG.job, J, chunksize=1)
    shutil.copy(fp, os.path.join(OUT, f'superseded - finals_{tag}.json'))
    for i, f in enumerate(F['finals']):
        old = f['worst']['climb']
        for mu in GG.BAND:
            cl = {(a[3][0], a[3][1]): r for a, r in R if a[1] == i and a[2] == mu}
            v = f['by_mu'][str(mu)]; v['climb'] = GG.ladder(cl, GG.N_TRY)
            v['climb_tries'] = {f'{h}|{int(b)}': c for (h, b), c in sorted(cl.items())}
        f['worst']['climb'] = min(f['by_mu'][str(mu)]['climb'] for mu in GG.BAND)
        print(f"{f['name']:14s} step up {old} -> {f['worst']['climb']} mm  ({', '.join(str(f['by_mu'][str(mu)]['climb']) for mu in GG.BAND)})", flush=True)
    F['reclimb'] = dict(tag=tag, wall_s=round(time.time() - t0))
    json.dump(F, open(fp, 'w'), indent=1, default=float)


def finals(k=8):
    """D: the best-turning few at each climb level on the screened front (k in all), read on the full gauges (every friction, 200 falls, 20
    tries), the box beside them as the baseline. A finalist meets the targets when its worst G1 is at least 0.75."""
    import pickle
    tags = ('E',) if os.path.isfile(os.path.join(OUT, 'screen_E.jsonl')) else         tuple(t for t in ('B', 'C', 'S', 'R', 'K') if os.path.isfile(os.path.join(OUT, f'screen_{t}.jsonl')))   # E's band-screened climbs when there
    rows = [json.loads(l) for tag in tags for l in open(os.path.join(OUT, f'screen_{tag}.jsonl'))]
    tail = lambda r: len(r['x']) > 18 and r['x'][18] > LIMB_ON
    F = []
    def pick(pool, n):
        levels = sorted({r['climb'] for r in front(pool)}); per = max(1, n // max(1, len(levels)))
        for c in levels:                                                  # the front has one design a 10 mm climb level:
            cand = sorted([r for r in pool if r['climb'] == c and r['up'] >= UP_SCREEN and r['turn'] is not None], key=lambda r: r['turn'])
            got = 0
            for r in cand:                                                # take the best few turners at each, unlike one another
                if all(np.abs((np.array(r['x']) - np.array(o['x'])) / (HI - LO))[:len(r['x'])].max() > 0.05 for o in F):
                    F.append(r); got += 1
                if got >= per:
                    break
    shell = lambda r: r['x'][7] > 0.5
    if RUN != 'search':                                                   # the whole front, then the best of each answer beside it:
        pick(rows, k - 4)                                                 # a tail instead of a shell, and a shell with no tail
        pick([r for r in rows if tail(r) and not shell(r)], 2); pick([r for r in rows if not tail(r)], 2)
    else:
        pick(rows, k)
    count = {'T': 0, 'N': 0, 'S': 0}; specs = []
    for r in F:
        g = ('T' if tail(r) else 'N') if RUN != 'search' else 'S'; count[g] += 1
        specs.append(build(np.array(r['x']), name=f'{g}{count[g]}'))
    main, controls = GG.roster(True); allsp = [main[0]] + specs; t0 = time.time()
    if RUN == 'search_shape':                                             # the references: T5's own shape, and its platform on the Trainer's body
        z5 = np.array([T5_SHAPE[k] for k in ZK])
        for nm, fr in (('T5 (its own skin)', FROZEN), ('T5 on the Trainer body', dict(FROZEN, shell=0.0))):
            sp = build(to_x(z5, fr), name=nm); sp['notes'] = sp['notes'] + ['reference']; allsp.append(sp)
    tails = [(r, sp) for r, sp in zip(F, specs) if sp.get('limb')]
    if tails:                                                             # the control: the best tail climber, its servos limp
        best = max(tails, key=lambda t: t[0]['climb'])[1]; lm = best['limb']
        limp = RB.add_limb(dict(best, limb=None, notes=[n for n in best['notes'] if not n.startswith('tail')]), lm['L'], 0.05,
                           lm['th_push'], lm['th_stow'], lm['mz'])
        limp['name'] = best['name'] + ', limp tail'; limp['x'] = best['x']; allsp.append(limp)
    J = [j for i in range(len(allsp)) for j in GG.jobs_for(i, GG.N_DROP, GG.N_TRY, seed=31)]
    J.sort(key=lambda a: a[0] != 'climb')
    with Pool(WORKERS, initializer=GG._init, initargs=(allsp,)) as pool:
        R = pool.map(GG.job, J, chunksize=1)
    out = []
    for i, sp in enumerate(allsp):
        r = GG.collect(R, i, GG.N_TRY); w = r['worst']
        out.append(dict(name=sp['name'], x=sp.get('x'), screen=None if (i == 0 or i > len(F)) else {k_: F[i - 1].get(k_) for k_ in ('up', 'climb', 'turn', 'static_up', 'n_rest', 'nose', 'turn_geo', 'tag')},
                        limb=sp.get('limb'), control=sp['name'].endswith('limp tail'),
                        worst=w, by_mu=r['by_mu'], meets=bool(w['upright'] >= UP_MIN), notes=sp['notes'],
                        dims={k_: sp[k_] for k_ in ('mass', 'length', 'width', 'height', 'belly', 'R')} | dict(wheels=len(sp['wheels']))))
        print(f"{sp['name']:4s} upright {w['upright']:.3f} {'meets' if w['upright'] >= UP_MIN else 'MISSES'}  step up {w['climb']} mm  turn {w['turn'] and round(w['turn'])} mm  "
              f"| screen {out[-1]['screen'] and (round(out[-1]['screen']['up'], 2), out[-1]['screen']['climb'], round(out[-1]['screen']['turn']))}  "
              f"| {sp['mass']:.0f} g {sp['length']:.0f} x {sp['width']:.0f} x {sp['height']:.0f}  {sp['notes']}", flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), finals=out), open(os.path.join(OUT, 'finals.json'), 'w'), indent=1, default=float)
    pickle.dump(allsp, open(os.path.join(OUT, 'finals_specs.pkl'), 'wb'))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'statics':
        stage_statics()
    elif cmd == 'calibrate':
        calibrate()
    elif cmd == 'search':
        search()
    elif cmd == 'band':
        search_band()
    elif cmd in ('limb', 'drive'):
        search_limb()
    elif cmd in ('lean', 'body'):
        search_lean()
    elif cmd == 'shape':
        search_lean(n_b=512)
    elif cmd == 'sweep':
        shape_sweep()
    elif cmd == 'reclimb':
        reclimb()
    elif cmd == 'skin':
        skin_refine()
    elif cmd == 'seed':
        seed_refine()
    elif cmd == 'frozen':
        frozen_check()
    elif cmd == 'frozen_each':
        frozen_each()
    elif cmd == 'finals':
        finals()
    else:
        print(__doc__)
