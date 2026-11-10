"""Noisy copies (2026-11-08): the finalists read as slightly wrong builds, not only as drawn.

NASA's ST5 antenna search (2003) scored every design on 3 copies with noise added, so a design couldn't win by working
only when built exactly. The search here reads each design as drawn; only the falls' starts and the friction vary. Zach,
after reading that history: "Yes, run it". This reads the tow run's finals, the last finished run, on the full gauges.

    python gauges/noisy.py check   # the controls, no gauge runs: the copies reach the sim, a zero error changes nothing
    python gauges/noisy.py smoke   # T3 and the box, 1 chunk of falls and 2 tries a rung -> out/noisy/smoke.pkl
    python gauges/noisy.py run     # every finalist, 5 reads each (~75 min, 28 workers); resumes -> out/noisy/rows.pkl
    python gauges/noisy.py table   # what's finished so far -> out/noisy/rows.json
    python gauges/noisy.py single  # one error at a time on the three that dropped most (~15 min) -> out/noisy/single.json

The designs rebuild under today's code, so "drawn" is read here, not taken from finals.json: their tails weigh 84-138 g
more since 2026-11-03, and the tyre springs changed that day too.

Five reads per design, sharing seeds so a difference is the error and not the dice:
  drawn    as the search built it
  reseed   as drawn on other seeds: how far a reading moves with no error at all (the noise floor)
  nose, tail, weak   the three wrong builds below
A design's noisy reading on a gauge is the worst of the three, as ST5 took the worse.

Not modelled: the belly's height (a smaller tyre keeps it, the axle moves), loose parts shifting in a fall, hulls printed
out of shape, and G8 rough ground (the tow run has none).
"""
import os, sys, json, time, pickle
os.environ.setdefault('SCORPION_CAP', 'capability_tow')                   # the run whose finals these are; capability.py reads it
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config, stamp
import capability as C, gauges as GG, search as S, robots as RB, hills as H, card, tow as T, rough  # noqa: F401 (loaded for the stamp)

OUT = os.path.join(config.GAUGES_OUT, 'noisy')
WORKERS = int(os.environ.get('SCORPION_WORKERS', 28))                     # of 32: other sessions share this machine

# The errors, and where each size comes from. * = a guess, for Zach to OK or measure.
CG_X = 5.0    # mm fore-aft. T3 (4,651 g): 150 g* of leads in the back moves the CoM 4.3 mm back, the sim counting 60 g* of wiring;
              # the power bay's 105 g, still unbought and "pretty much empty" on the 2026-11-07 tub, 2.8 mm forward.
CG_Y = 2.0    # mm sideways*. About 90 g of leads to one side.
CG_Z = 3.0    # mm up*. Those leads move it 1.1 mm; the rest is the printed skin, whose mass no print has checked.
MASS = 0.05   # of the whole robot, added*. The one print to compare: the tub, 232 g in the sim, 236 g in the slicer (no scale reading).
              # So the plastic alone looks close; this is leads, screws and glue.
DRIVE = 0.15  # weaker motors and servos*. The JGB37-520's and the servos' torques are datasheet guesses, none measured; a low pack too.
TYRE = 1.5    # mm off the tyre's radius*.
# Left out as too small to matter: the packs' 1.5 mm of play in print 1 moves T3's CoM 0.2 mm.
COPIES = dict(nose=dict(d=(CG_X, CG_Y, 0.0), mass=MASS),
              tail=dict(d=(-CG_X, -CG_Y, 0.0), mass=MASS),
              weak=dict(d=(0.0, 0.0, CG_Z), drive=DRIVE, tyre=TYRE))
RESEED = 500000
READS = ('drawn', 'reseed') + tuple(COPIES)
ORDER = ('T3', 'Box', 'best all', 'front 1', 'front 2', 'front 3', 'front 4', 'best low', 'best up', 'best climb', 'best turn',
         'best crest', 'best h_up', 'best h_down', 'best tow')             # the ones that matter finish first
GAUGES = (('up', 1), ('climb', 1), ('turn', -1), ('h_up', 1), ('h_down', 1), ('crest', 1), ('tow', 1), ('push', 1))


def wonky(sp, name, d=(0.0, 0.0, 0.0), mass=0.0, drive=0.0, tyre=0.0, motor=None, servo=None):
    """the spec built wrong: the whole robot's CoM moved d (mm), mass (a share of the whole robot) added at the body,
    motors and servos weaker by drive (or motor and servo apart), tyres smaller by tyre (mm; the axle comes down with
    them, the belly stays)"""
    motor, servo = drive if motor is None else motor, drive if servo is None else servo
    M, total = sp['M'], sp['mass']; dm = mass * total; M2 = M + dm
    c2 = np.asarray(sp['com'], float) + np.asarray(d, float) * (total + dm) / M2   # the body carries the move for the whole robot
    q = dict(sp, name=name, M=M2, com=c2, I=sp['I'] * (M2 / M), R=sp['R'] - tyre, notes=list(sp['notes']) + [f'wrong build: {d} {mass} {motor} {servo} {tyre}'])
    if motor:
        q['motor'] = dict(sp['motor'], stall=sp['motor']['stall'] * (1.0 - motor))
    if servo:
        k = 1.0 - servo
        if sp.get('limb'):
            lm = dict(sp['limb'], tq=sp['limb']['tq'] * k)
            if lm.get('tq2') is not None:
                lm['tq2'] = lm['tq2'] * k
            q['limb'] = lm
        if sp.get('flip'):
            q['flip'] = dict(sp['flip'], tq=sp['flip']['tq'] * k)
    return RB.dims(q)


# One error at a time (noisy.py single), on the same seeds as the run: which part of a copy did the damage, for the
# designs that dropped most. The servo's other sizes ask how much of its strength a design can lose.
SINGLE = {'x+5': dict(d=(CG_X, 0.0, 0.0)), 'x-5': dict(d=(-CG_X, 0.0, 0.0)), 'y+2': dict(d=(0.0, CG_Y, 0.0)), 'z+3': dict(d=(0.0, 0.0, CG_Z)),
          'mass+5%': dict(mass=MASS), 'motor-15%': dict(motor=DRIVE), 'tyre-1.5': dict(tyre=TYRE), 'servo-5%': dict(servo=0.05),
          'servo-10%': dict(servo=0.10), 'servo-15%': dict(servo=DRIVE), 'servo-25%': dict(servo=0.25)}
SINGLE_DESIGNS = ('T3', 'best up', 'best crest')


def single():
    """G1-G3 for each single error on SINGLE_DESIGNS -> out/noisy/single.json, beside the run's drawn reading"""
    path = os.path.join(OUT, 'single.pkl'); D = designs(); cs = []
    for name in SINGLE_DESIGNS:
        cs += [dict(design=name, k=ORDER.index(name), read=e, sp=dict(wonky(D[name], name, **v), name=name)) for e, v in SINGLE.items()]
    J = []
    for i, c in enumerate(cs):
        J += GG.jobs_for(i, GG.N_DROP, card.N_TRY, seed=31 + 1000 * (c['k'] - i))   # the run's seeds for this design
    stamp.check(path); done = {a for a, _ in load(path)}; todo = [a for a in J if a not in done]
    print(f'{len(cs)} reads, {len(todo)} of {len(J)} jobs to do, {WORKERS} workers', flush=True); t0 = time.time()
    with Pool(WORKERS, initializer=_finit, initargs=([c['sp'] for c in cs], card.N_TRY)) as pool, open(path, 'ab') as fh:
        for n, (a, r) in enumerate(pool.imap_unordered(card.job, todo, chunksize=1), 1):
            pickle.dump((a, r), fh); fh.flush()
            if n % 500 == 0 or n == len(todo):
                print(f'{n}/{len(todo)} jobs, {(time.time() - t0) / 60:.1f} min', flush=True)
    R = load(path); base = json.load(open(os.path.join(OUT, 'rows.json')))['designs']; out = {}
    for i, c in enumerate(cs):
        w = GG.collect([x for x in R if x[0][1] == i], i, card.N_TRY)['worst']
        out.setdefault(c['design'], dict(drawn={k: base[c['design']]['drawn'][k] for k in ('up', 'climb', 'turn')},
                                         tail_N_m=D[c['design']]['limb']['tq'] if D[c['design']].get('limb') else None))[c['read']] = dict(up=w['upright'], climb=w['climb'], turn=w['turn'])
    json.dump(out, open(os.path.join(OUT, 'single.json'), 'w'), indent=1, default=float)
    for name, r in out.items():
        print(f"\n{name}   tail servo {r['tail_N_m']} N m\n  {'':10s}{'up':>7s}{'climb':>7s}{'turn':>7s}")
        for e, v in r.items():
            if e != 'tail_N_m':
                print(f"  {e:10s}{v['up']:7.2f}{v['climb']:7.0f}{(v['turn'] or 0):7.0f}")


def designs():
    """the tow run's finals, rebuilt, in ORDER: name -> spec"""
    fin = {f['name']: f for f in json.load(open(os.path.join(config.GAUGES_OUT, 'capability_tow', 'finals.json')))['finals']}
    out = {}
    for name in ORDER:
        f = fin[name]
        if name == 'T3':
            sp = C.t3_ref()
        elif name == 'Box':
            sp = GG.roster(True)[0][0]
        else:
            sp = C.build(C.q_of(np.array(f['z'])))
        if sp is None:
            raise SystemExit(f'{name} no longer builds')
        out[name] = dict(sp, name=name)
    return out


def copies(names=ORDER):
    D = designs(); out = []
    for k, name in enumerate(n for n in ORDER if n in names):
        for read in READS:
            sp = D[name] if read in ('drawn', 'reseed') else wonky(D[name], name, **COPIES[read])
            out.append(dict(design=name, k=k, read=read, sp=dict(sp, name=name)))
    return out


def jobs(cs, n_drop, n_try):
    """card.jobs' reads for every copy; every copy of a design on one set of seeds, the reseed on another"""
    J = []
    for i, c in enumerate(cs):
        sp = c['sp']; off = RESEED if c['read'] == 'reseed' else 0; s = card.seed_of(c['design']) + off
        poses = (None,) + (H.HELD if sp.get('limb') else ())
        J += [('hill', i, (down, th), s) for down in (False, True) for th in poses]
        J += [('crest', i, None, s + 1)]
        J += [('push', i, mu, s + 2) for mu in GG.BAND] + [('tow', i, mu, s + 3) for mu in GG.BAND]
        J += GG.jobs_for(i, n_drop, n_try, seed=31 + off + 1000 * (c['k'] - i))   # jobs_for adds 1000 * i: the design's own seed
    return J


def _finit(specs, n_try):
    C._finit(specs); card.N_TRY = n_try


def load(path):
    R = []
    if os.path.isfile(path):
        with open(path, 'rb') as fh:
            while True:
                try:
                    R.append(pickle.load(fh))
                except EOFError:
                    break
    return R


def run(path, names, n_drop, n_try):
    os.makedirs(OUT, exist_ok=True); cs = copies(names); J = jobs(cs, n_drop, n_try)
    stamp.check(path); done = {a for a, _ in load(path)}; todo = [a for a in J if a not in done]
    print(f'{len(cs)} reads of {len(cs) // len(READS)} designs: {len(J)} jobs, {len(todo)} to do, {WORKERS} workers', flush=True)
    t0 = time.time()
    with Pool(WORKERS, initializer=_finit, initargs=([c['sp'] for c in cs], n_try)) as pool, open(path, 'ab') as fh:
        for n, (a, r) in enumerate(pool.imap_unordered(card.job, todo, chunksize=1), 1):
            pickle.dump((a, r), fh); fh.flush()
            if n % 200 == 0 or n == len(todo):
                print(f'{n}/{len(todo)} jobs, {(time.time() - t0) / 60:.1f} min, about {(time.time() - t0) * (len(todo) - n) / n / 60:.0f} min left', flush=True)


def reading(R, i, sp, n_try):
    g = GG.collect([x for x in R if x[0][0] in ('fall', 'climb', 'turn')], i, n_try)['worst']; r = card.row(R, i, sp)
    return dict(up=g['upright'], climb=g['climb'], turn=g['turn'], h_up=r['up'], h_down=r['down'], crest=r['crest'], tow=r['tow'], push=r['push'])


def better(g, sign, a, b):
    """the worse of two readings; a None turn (can't spin) is the worst there is"""
    if g == 'turn' and (a is None or b is None):
        return None
    return min(a, b) if sign > 0 else max(a, b)


def table(path, names, n_drop, n_try):
    cs = copies(names); J = jobs(cs, n_drop, n_try); R = load(path); by = {}
    for a, r in R:
        by.setdefault(a[1], []).append((a, r))
    want = {}
    for a in J:
        want[a[1]] = want.get(a[1], 0) + 1
    rows = {}
    for i, c in enumerate(cs):
        if len(by.get(i, [])) == want[i]:                                 # this read finished
            rows.setdefault(c['design'], {})[c['read']] = reading(by[i], i, c['sp'], n_try)
    out = {}
    for name, rr in rows.items():
        row = dict(rr)
        if all(k in rr for k in COPIES):
            w = {}
            for g, sg in GAUGES:
                v = rr['nose'][g]
                for k in ('tail', 'weak'):
                    v = better(g, sg, v, rr[k][g])
                w[g] = v
            row['worst'] = w
        out[name] = row
    # the finalists' all-rounder order, drawn against the worst of three (capability.ranks: the worst weighted rank among these)
    whole = {n: r for n, r in out.items() if 'worst' in r}
    if len(whole) >= 2:
        for key in ('drawn', 'worst'):
            L = [dict(whole[n][key], name=n) for n in whole]; C.ranks(L)
            for r in L:
                whole[r['name']].setdefault('rank', {})[key] = r['rank']['all']
    floor = {}
    for g, sg in GAUGES:
        d = [abs((r['drawn'][g] or 0) - (r['reseed'][g] or 0)) for r in out.values() if 'drawn' in r and 'reseed' in r and r['drawn'][g] is not None and r['reseed'][g] is not None]
        if d:
            floor[g] = dict(median=float(np.median(d)), p90=float(np.percentile(d, 90)), max=float(max(d)))
    json.dump(dict(errors=dict(CG_X=CG_X, CG_Y=CG_Y, CG_Z=CG_Z, MASS=MASS, DRIVE=DRIVE, TYRE=TYRE), copies={k: {a: b for a, b in v.items()} for k, v in COPIES.items()},
                   floor=floor, designs=out), open(path.rsplit('.', 1)[0] + '.json', 'w'), indent=1, default=float)
    fmt = lambda g, v: 'none' if v is None else (f'{v:.2f}' if g == 'up' else f'{v:.0f}' if g in ('climb', 'turn') else f'{v:g}')
    for name, r in out.items():
        print(f'\n{name}' + (f"   all-rounder rank {r['rank']['drawn']:.2f} -> {r['rank']['worst']:.2f}" if 'rank' in r else ''))
        print('  ' + ' ' * 7 + ''.join(f'{g:>8s}' for g, _ in GAUGES))
        for k in READS + ('worst',):
            if k in r:
                print(f'  {k:7s}' + ''.join(f'{fmt(g, r[k][g]):>8s}' for g, _ in GAUGES))
    print('\nnoise floor, drawn against reseed (median, 90th pct, max):')
    for g, v in floor.items():
        print(f"  {g:7s} {v['median']:g} {v['p90']:g} {v['max']:g}")


def check():
    """the controls. Each error reaches what it should, a zero error changes nothing, and a bigger error moves G3 further"""
    D = designs(); sp = D['T3']; fails = 0
    def ok(what, good, got):
        nonlocal fails
        fails += not good; print(f"  {'ok  ' if good else 'FAIL'} {what}: {got}")
    print('a zero error is the design itself; each copy is not (its control)')
    for name in ('T3', 'Box', 'best all', 'best up'):
        z = wonky(D[name], name); same = RB.xml(z, 1.0) == RB.xml(D[name], 1.0); ok(f'{name} zero error: the same model', same, same)
        for k, e in COPIES.items():
            diff = RB.xml(wonky(D[name], name, **e), 1.0) != RB.xml(D[name], 1.0); ok(f'{name} {k}: a different model', diff, diff)
    print('the whole robot\'s CoM moves by what was asked (T3, mm)')
    G0 = S.com_all(sp)
    for k, e in COPIES.items():
        G1 = S.com_all(wonky(sp, 'T3', **e)); want = np.asarray(e['d'])
        ok(f'{k}: moved {np.round(G1 - G0, 2).tolist()}, asked {want.tolist()}', np.abs(G1 - G0 - want).max() < 0.6, f"{wonky(sp, 'T3', **e)['mass'] - sp['mass']:.0f} g added")
    print('the weak copy\'s motor and servos reach the sim')
    w = wonky(sp, 'T3', **COPIES['weak']); s0, s1 = GG.Sim(sp, 1.0), GG.Sim(w, 1.0)
    ok('stall x0.85', abs(s1.stall / s0.stall - 0.85) < 1e-9, f'{s0.stall:.3f} -> {s1.stall:.3f}')
    ok('tail servo x0.85', f'{sp["limb"]["tq"] * 0.85:.3f}' in RB.xml(w, 1.0), f'{sp["limb"]["tq"]:.3f} -> {w["limb"]["tq"]:.3f}')
    ok('tyre 1.5 mm smaller', abs(sp['R'] - w['R'] - TYRE) < 1e-9, f"{sp['R']:.1f} -> {w['R']:.1f}")
    print('G3 on T3 (README: 12-15 mm of circle per mm of fore-aft CoM). Deterministic, so drawn twice must match')
    circle = lambda s: max(GG.turn(GG.Sim(s, mu), sg)[0] or 1e9 for mu in GG.BAND for sg in (1, -1))
    a, b = circle(sp), circle(sp); c5, c15 = circle(wonky(sp, 'T3', d=(CG_X, 0, 0))), circle(wonky(sp, 'T3', d=(3 * CG_X, 0, 0)))
    ok('drawn twice', a == b, f'{a:.1f} and {b:.1f} mm')
    ok(f'{CG_X:.0f} mm forward reads wider', c5 > a, f'{a:.0f} -> {c5:.0f} mm, {(c5 - a) / CG_X:.1f} mm per mm')
    ok(f'{3 * CG_X:.0f} mm forward reads wider still', c15 > c5, f'{c5:.0f} -> {c15:.0f} mm')
    print('the static tip angle moves with the CoM (T3, degrees)')
    t0, tn, tt = H.tip_static(sp), H.tip_static(wonky(sp, 'T3', d=(CG_X, 0, 0))), H.tip_static(wonky(sp, 'T3', d=(-CG_X, 0, 0)))
    ok('nose against tail differ', tn != tt, f'drawn {t0}, nose {tn}, tail {tt}')
    print(f'{fails} failed'); return fails


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    FULL = (os.path.join(OUT, 'rows.pkl'), ORDER, GG.N_DROP, card.N_TRY)
    SMOKE = (os.path.join(OUT, 'smoke.pkl'), ('T3', 'Box'), GG.CHUNK, 2)
    if cmd == 'check':
        sys.exit(1 if check() else 0)
    elif cmd == 'smoke':
        run(*SMOKE); table(*SMOKE)
    elif cmd == 'run':
        run(*FULL); table(*FULL)
    elif cmd == 'table':
        table(*FULL)
    elif cmd == 'single':
        single()
    else:
        print(__doc__)
