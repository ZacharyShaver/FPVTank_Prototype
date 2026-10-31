"""One-click tests for a capability run (2026-10-31, Zach: "write some one click scripts that i can launch tomorrow for
targeted tests"). Each reads the run SCORPION_CAP names (default capability_real, the realistic run of 2026-10-31),
writes under gauges/out/<run>/tomorrow/, and opens what it made. Double-click the matching oneclick/*.bat.

    python gauges/tomorrow.py status     the run's progress, its best so far, what it refuses and why       (seconds)
    python gauges/tomorrow.py results    the finals (run here if the run didn't finish them), the page       (1-20 min)
    python gauges/tomorrow.py repeat     the run's best read three times with other seeds: is each reading luck?  (~15 min)
    python gauges/tomorrow.py onepiece   the run's best grown as one printable piece (unibody) and read again   (~30 min)
    python gauges/tomorrow.py film       the run's best and T3 on a 150 mm step and spinning round, filmed      (~5 min)
    python gauges/tomorrow.py checks     every check of today's builds and gauges, with its control             (~5 min)

--quick: one design, the screen's 6 tries instead of the full gauges (a smoke test of the script itself).
"""
import os, sys, json, time, copy, subprocess
os.environ.setdefault('SCORPION_CAP', 'capability_real')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import numpy as np
import capability as CP, knobs as K, gauges as GG, robots as RB

OUT = os.path.join(CP.OUT, 'tomorrow')
PICKS = ('all', 'low', 'climb', 'turn', 'up', 'push')                    # the streams whose best are read, in this order
QUICK = '--quick' in sys.argv
LINE = ('up {up:.2f}  step {climb}  turn {turn}  hills {h_up}/{h_down}  crest {crest}  push {push}')


def show(p):
    print(p, flush=True)
    if sys.platform == 'win32' and os.path.isfile(p) and not os.environ.get('TOMORROW_NO_OPEN'):
        os.startfile(p)


def running():
    """is the run still going (its log has no 'done' line yet)?"""
    log = os.path.join(CP.OUT, 'run.log')
    return os.path.isfile(log) and not any(l.startswith('done ') for l in open(log, errors='replace'))


def busy_ok():
    """the long tests use every core: ask first while the run still has them"""
    if not running():
        return True
    return input('The run is still going and this test shares its cores (both slow down). Go on anyway? [y/N] ').strip().lower() == 'y'


def picks(n=4):
    """the run's best designs, distinct: each PICKS stream's best, from its finals or else its summary (or, mid-run,
    its screens so far): [(name, knobs)]"""
    fp, sp_ = os.path.join(CP.OUT, 'finals.json'), os.path.join(CP.OUT, 'summary.json')
    if os.path.isfile(fp):
        src = {f['name'][5:]: f for f in json.load(open(fp))['finals'] if f['name'].startswith('best ') and f.get('z')}
    elif os.path.isfile(sp_):
        src = json.load(open(sp_))['champions']
    else:
        ok = CP.ranks(CP.load()); src = {st: max(ok, key=lambda r: CP.score(r, st)) for st in CP.STREAMS} if ok else {}
    out, seen = [], set()
    for st in PICKS + tuple(k for k in src if k not in PICKS):           # a run with other streams (capability_low) reads its own
        r = src.get(st)
        if r is None:
            continue
        key = tuple(np.round(r['z'], 6))
        if key not in seen:
            seen.add(key); out.append((f'best {st}', CP.q_of(r['z'])))
    return out[:1 if QUICK else n]


def read_all(specs):
    """the full gauges on each spec (card.py's reads, as the finals), or the screen when QUICK: {name: readings}"""
    if QUICK:
        CP._init(); return {sp['name']: CP.screen(sp, 40000, 2) for sp in specs}
    import card
    from multiprocessing import Pool
    GG.HEIGHTS = CP.HEIGHTS_EXT; J = card.jobs(specs, {s['name'] for s in specs}); t0 = time.time()
    print(f'{len(specs)} readings, {len(J)} jobs on {CP.WORKERS} workers ...', flush=True)
    with Pool(CP.WORKERS, initializer=CP._finit, initargs=(specs,)) as pool:
        R = pool.map(card.job, J, chunksize=1)
    out = {}
    for i, sp in enumerate(specs):
        g = GG.collect([x for x in R if x[0][0] in ('fall', 'climb', 'turn')], i, card.N_TRY); w = g['worst']; r = card.row(R, i, sp)
        out[sp['name']] = dict(up=w['upright'], climb=w['climb'], turn=w['turn'], h_up=r['up'], h_down=r['down'], crest=r['crest'], push=r['push'], mass=sp['mass'])
    print(f'read in {(time.time() - t0) / 60:.0f} min', flush=True)
    return out


def fmt(g):
    return LINE.format(**dict(g, turn=None if g['turn'] is None else round(g['turn'])))


# ---------- the tests ----------
def status():
    rows = CP.load(); built = [r for r in rows if r.get('up') is not None]; log = os.path.join(CP.OUT, 'run.log')
    print(f'{CP.RUN}: {len(rows)} designs screened, {len(built)} built, {"still running" if running() else "finished"}')
    if os.path.isfile(log):
        print('the log ends:'); [print('  ' + l.rstrip()) for l in open(log, errors='replace').readlines()[-4:]]
    from collections import Counter
    c = Counter()
    for r in rows:
        for w in r.get('why', []) if r.get('built') is False else []:
            c['motor into a part' if ' into ' in w else w.split(':')[0]] += 1
    print('refused, by reason (a design can have several):', ', '.join(f'{k} {v}' for k, v in c.most_common()))
    if built:
        print('best so far:', CP.best_line(rows))


def results():
    if not os.path.isfile(os.path.join(CP.OUT, 'summary.json')):
        print('The run has no summary yet (it writes one when refinement ends). Try again later.'); return
    if not os.path.isfile(os.path.join(CP.OUT, 'finals.json')):
        if not busy_ok():
            return
        print('The finals are missing: running them now (about 15-20 min) ...', flush=True); CP.finals()
    F = json.load(open(os.path.join(CP.OUT, 'finals.json')))['finals']
    print(f"\n{'design':14s} readings on the full gauges")
    for f in F:
        print(f"{f['name']:14s} {fmt(f)}  | {f['mass'] / 1000:.2f} kg, {f['wheels']} wheels{', tail' if f['tail'] else ''}")
    import capability_page
    capability_page.main(); show(os.path.join(CP.OUT, 'capability.html'))


def repeat():
    if not busy_ok():
        return
    P = picks(); t3 = CP.t3_ref(); specs = []
    for nm, q in P + [('T3', None)]:
        sp = t3 if q is None else CP.build(q)
        if sp is None:
            print(f'{nm}: the build refuses it now'); continue
        specs += [dict(copy.deepcopy(sp), name=f'{nm} | seeds {s}') for s in ('A', 'B', 'C')[:1 if QUICK else 3]]
    G = read_all(specs); os.makedirs(OUT, exist_ok=True); lines = []
    for nm in dict.fromkeys(s['name'].split(' | ')[0] for s in specs):
        rs = [G[k] for k in G if k.startswith(nm + ' | ')]
        lines.append(f'{nm}:')
        for g in ('up', 'climb', 'turn', 'h_up', 'h_down', 'crest', 'push'):
            v = [r[g] for r in rs]; ok = all(x is not None for x in v)
            spread = (max(v) - min(v)) if ok else None
            flag = '' if spread is None or spread <= {'up': 0.05, 'climb': 15, 'turn': 15}.get(g, 5) else '   <- moves with luck'
            lines.append(f"   {g:7s} {' / '.join('-' if x is None else (f'{x:.2f}' if g == 'up' else f'{x:.0f}') for x in v)}{flag}")
    txt = '\n'.join(lines); print(txt)
    p = os.path.join(OUT, 'repeat.txt'); open(p, 'w').write(f'{CP.RUN}, {time.strftime("%Y-%m-%d %H:%M")}: each design read with three seed sets\n' + txt + '\n')
    json.dump(G, open(os.path.join(OUT, 'repeat.json'), 'w'), indent=1, default=float); show(p)


def onepiece():
    if not busy_ok():
        return
    import unibody as U
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from scipy.spatial import ConvexHull
    os.makedirs(OUT, exist_ok=True); rows, specs = [], []
    for nm, q in picks(3):
        t = time.time(); real = CP.build(q); D = U.design_knobs(q, packs_dz=True)
        if real is None or D is None:
            print(f'{nm}: not built'); continue
        r = U.make(D['q'], name=nm, falls=0 if QUICK else U.FALLS, D=D, rounds=1 if QUICK else U.ROUNDS, log=lambda s: None)
        if r is None:
            print(f'{nm}: the one piece failed'); continue
        grown = dict(U.with_flippers(U.gauge_spec(r), q), name=f'{nm} | one piece'); real = dict(real, name=f'{nm} | real build')
        P = np.asarray(real['hulls'][0], float); h = ConvexHull(P); s = h.simplices.copy()   # its faces turned outward
        n = np.cross(P[s[:, 1]] - P[s[:, 0]], P[s[:, 2]] - P[s[:, 0]]); s[(n * h.equations[:, :3]).sum(1) < 0] = s[(n * h.equations[:, :3]).sum(1) < 0][:, [0, 2, 1]]
        v, f = U.surface(r['F'], r['ax'])
        rows.append(dict(name=nm, img_real=U.render(real, P, s), img_one=U.render(U.with_flippers(r['sp'], q), v, f, motors=U.motors_of(r['D'])),
                         pieces=r['pieces'], holds=r['holds'], shape_g=r['sp']['shape_g'], hist=r['hist'][-1]))
        specs += [real, grown]; print(f"{nm}: grown in {time.time() - t:.0f} s, {r['pieces']} piece(s), shape {r['sp']['shape_g']:.0f} g, "
                                     f"{'holds' if r['holds'] else 'over'} its landings", flush=True)
    G = read_all(specs); fig, axs = plt.subplots(len(rows), 2, figsize=(9, 3.6 * len(rows)), squeeze=False)
    for i, row in enumerate(rows):
        for j, (k, tag) in enumerate((('img_real', 'real build'), ('img_one', 'one piece'))):
            g = G[f"{row['name']} | {tag}"]; axs[i, j].imshow(row[k]); axs[i, j].axis('off')
            axs[i, j].set_title(f"{row['name']}, {tag}\n{fmt(g)}\n{g['mass'] / 1000:.2f} kg", fontsize=8, loc='left')
    fig.tight_layout(); p = os.path.join(OUT, 'onepiece.png'); fig.savefig(p, dpi=110, bbox_inches='tight')
    json.dump(G, open(os.path.join(OUT, 'onepiece.json'), 'w'), indent=1, default=float)
    print('The one piece meets the sims as its hull plus 40 convex chunks (unibody.gauge_spec), an approximation of the print.')
    show(p)


def film():
    import film as F
    os.makedirs(OUT, exist_ok=True); t3 = CP.t3_ref()
    D = [(nm, CP.build(q)) for nm, q in picks(2)] + [('T3 (real build)', t3)]
    D = [(nm, sp) for nm, sp in D if sp is not None]; climbs, turns = [], []
    for nm, sp in D:
        sim = F.Rec(sp, 1.0, step=150); sim.log = []; ok = GG.climb_try(sim, 150, False, np.random.default_rng(1))
        climbs.append(F.frames(sim, sim.log, dict(dist=1.4, az=90.0, el=-8.0, dx=0.1), lambda t, nm=nm, ok=ok: [nm, '150 mm step: ' + ('on top' if ok else 'stuck'), f'{t:.1f} s'], sim.log[-1][0] + 0.3))
        sim = F.Rec(sp, 1.0); sim.log = []; dia, t_ = GG.turn(sim, 1)
        turns.append(F.frames(sim, sim.log, dict(dist=1.3, az=90.0, el=-89.0), lambda t, nm=nm, dia=dia: [nm, f'spin in place: {dia:.0f} mm' if dia else 'spin: never got round', f'{t:.1f} s'], sim.log[-1][0] + 0.3))
    a = F.write(os.path.join(OUT, 'steps'), climbs, len(climbs))[0]; b = F.write(os.path.join(OUT, 'turns'), turns, len(turns))[0]
    print(a); show(b); show(a)


def checks():
    cmds = [('the real build: motor fit, flipper mounts, weight (knobs.py real)', ['knobs.py', 'real']),
            ("G2's pooled step rule (gauges.py steps)", ['gauges.py', 'steps']),
            ('one body: parts on the body (knobs.py cohere)', ['knobs.py', 'cohere']),
            ('the stress solver (fem.py check)', ['fem.py', 'check']),
            ("the one piece's mesh (unibody.py check)", ['unibody.py', 'check'])]
    res = []
    for name, c in cmds:
        p = subprocess.run([sys.executable, os.path.join(HERE, c[0])] + c[1:], capture_output=True, text=True, cwd=HERE)
        out = p.stdout.splitlines(); fails = [l for l in out if l.startswith('FAIL')]; passes = sum(l.startswith('PASS') for l in out)
        ok = p.returncode == 0 and not fails; res.append(ok)
        said = f'{passes} passed' if passes else (out[-1].strip() if out else 'no output')   # (unibody's check sums up on its last line)
        print(f"{'OK  ' if ok else 'FAIL'} {name}: {said}{', ' + str(len(fails)) + ' failed' if fails else ''}{'' if p.returncode == 0 else f' (exit {p.returncode})'}")
        for l in fails + ([p.stderr.strip().splitlines()[-1]] if p.returncode and p.stderr.strip() else []):
            print('     ' + l)
    print(f"\n{sum(res)} of {len(res)} checks pass")


if __name__ == '__main__':
    cmd = next((a for a in sys.argv[1:] if not a.startswith('--')), '')
    {'status': status, 'results': results, 'repeat': repeat, 'onepiece': onepiece, 'film': film, 'checks': checks}.get(cmd, lambda: print(__doc__))()
