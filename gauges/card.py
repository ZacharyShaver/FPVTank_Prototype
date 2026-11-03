"""G4-G7 on the scorecard's designs (2026-10-28): Zach adopted the hills, the crest and the push on 2026-10-27 and asked
for them on the "Scorpion Gauges" page. Each gauge read as its own card says, in one pass over the page's designs, with
each gauge's controls read in the same pass.

    python gauges/card.py check   # the designs build; T3 rebuilt from its knobs matches the shape study's T3
    python gauges/card.py read    # -> gauges/out/card/card.json (export.py merges it into the page's rows)
    python gauges/card.py com     # G3 against the CoM's fore-aft offset (T3 plus 150 g) -> gauges/out/card/com_turn.json

The designs: the roster and its controls (gauges.py), the shape study's finalists and limp-tail control (the current
search, tools/config.py), and T3 with its tail mount raised to 170 mm, the knob log's fix for G7 (README, K7), which
gets G1-G3 here too, on the full gauges (200 falls, 20 tries, every friction).

G4 / G5 is the better of the tail stowed and held at hills.HELD (a design may use its limbs, rule 1); the stowed reading
is kept beside it, since the static check and the hill control are read stowed. G6 at x2.5, G7 over the band.
"""
import os, sys, json, time, pickle, zlib
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')                # as knobs.py, whose make() builds T3's variants
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import gauges as GG, robots as RB, hills as H, crest as C, push as P

OUT = os.path.join(config.GAUGES_OUT, 'card')
TOW = False                               # also read G7 tow (tow.py; the tow run sets it, 2026-11-02)
ROUGH = False                             # also read G8 rough ground (rough.py; the rough run sets it, 2026-11-02)
MOUNT_FIX = 170.0                         # mm: the tail mount the knob log found pushes 4 kg (README, G7)
N_TRY = 20                                # every gauge's tries, as its card


def specs():
    """(designs, controls): the page's rows, then the G4-G7 controls' designs (read, not shown as rows)"""
    import knobs as K
    main, ctl = GG.roster(True)
    fin = pickle.load(open(os.path.join(config.GAUGES_CURRENT, 'finals_specs.pkl'), 'rb'))
    fin = [sp for sp in fin if sp['name'] != 'Box']                       # the roster's box is the baseline
    T3 = next(sp for sp in fin if sp['name'] == 'T3')
    fix = dict(K.make(dict(K.T3, mount_z=MOUNT_FIX)), name=f'T3, tail mount {MOUNT_FIX:.0f} mm')
    fix['notes'] = list(fix['notes']) + [f'tail mount raised to {MOUNT_FIX:.0f} mm (knob log, G7)']
    designs = main + list(ctl.values()) + fin + [fix]
    bx = main[0]; Hb = bx['hulls'][0].copy(); Hb[Hb[:, 2] <= Hb[:, 2].min() + 1e-6, 2] -= 15.0
    top = float(T3['hulls'][0][:, 2].max())
    controls = [H.add_mass(T3, 1000.0, (float(T3['com'][0]), 0.0, top - 20.0), 'T3, 1 kg high on top'),     # G4 / G5
                RB.dims(dict(bx, hulls=[Hb], name='Box, belly 15 mm lower', notes=list(bx['notes']) + ['belly 15 mm lower'])),  # G6
                dict(K.make(dict(K.T3, gear=0.4)), name='T3, geared 0.4x'),                           # G7
                dict(T3, tyre_mu=0.5, name='T3, tyres at half grip')]                                 # G7
    return designs, controls


SP = None


def _init(sp):
    global SP
    SP = sp; GG._init(sp)


def job(a):
    if a[0] in ('fall', 'climb', 'turn'):
        return GG.job(a)
    kind, i, arg, seed = a; sp = SP[i]
    if kind == 'hill':
        down, th = arg
        return a, H.ladder(sp, H.GRIP, down, N_TRY, seed, th)
    if kind == 'crest':
        return a, C.ladder(sp, C.GRIP, N_TRY, seed)
    if kind == 'tow':
        import tow as T
        return a, T.ladder(sp, arg, N_TRY, seed)
    if kind == 'rough':
        import rough as RG
        return a, RG.ladder(sp, RG.GRIP, N_TRY, seed)
    return a, P.ladder(sp, arg, N_TRY, seed)


def seed_of(name):
    return zlib.crc32(name.encode()) % 100000


def jobs(allsp, full):
    J = []
    for i, sp in enumerate(allsp):
        s = seed_of(sp['name'])
        poses = (None,) + (H.HELD if sp.get('limb') else ())
        J += [('hill', i, (down, th), s) for down in (False, True) for th in poses]
        J += [('crest', i, None, s + 1)]
        J += [('push', i, mu, s + 2) for mu in GG.BAND]
        J += [('tow', i, mu, s + 3) for mu in GG.BAND] if TOW else []
        J += [('rough', i, None, s + 4)] if ROUGH else []
        if sp['name'] in full:
            J += GG.jobs_for(i, GG.N_DROP, GG.N_TRY, seed=31)
    J.sort(key=lambda a: a[0] not in ('climb', 'crest', 'hill', 'rough'))    # the long ladders first
    return J


def row(R, i, sp):
    hills = {(a[2][0], a[2][1]): r for a, r in R if a[0] == 'hill' and a[1] == i}
    out = dict(name=sp['name'], mass=sp['mass'], tip_static=H.tip_static(sp), limb=bool(sp.get('limb')))
    for down, g in ((False, 'up'), (True, 'down')):
        st = hills[(down, None)]; out[g + '_stowed'] = st[0]; out[g + '_why'] = st[1].get(st[0] + 5)
        best = max(((th, r[0]) for (d, th), r in hills.items() if d == down), key=lambda t: (t[1], t[0] is None))
        out[g], out[g + '_pose'] = best[1], best[0]
        out[g + '_by_pose'] = {('stowed' if th is None else f'{th:.0f}'): r[0] for (d, th), r in hills.items() if d == down}
    cr = next(r for a, r in R if a[0] == 'crest' and a[1] == i)
    out.update(crest=cr[0], crest_why=cr[1].get(cr[0] + 5), crest_seen=cr[1])
    pu = {a[2]: r for a, r in R if a[0] == 'push' and a[1] == i}
    w = min(pu, key=lambda mu: pu[mu][0])
    out.update(push=pu[w][0], push_worst_mu=w, push_by_mu={str(mu): v[0] for mu, v in pu.items()}, push_why=pu[w][1].get(P.nxt(pu[w][0])))
    tw = {a[2]: r for a, r in R if a[0] == 'tow' and a[1] == i}
    if tw:
        import tow as T
        w = min(tw, key=lambda mu: tw[mu][0])
        out.update(tow=tw[w][0], tow_worst_mu=w, tow_by_mu={str(mu): v[0] for mu, v in tw.items()}, tow_why=tw[w][1].get(T.nxt(tw[w][0])))
    rg = next((r for a, r in R if a[0] == 'rough' and a[1] == i), None)
    if rg:
        out.update(rough=rg[0], rough_seen={str(k): v for k, v in rg[1].items()})
    return out


def read():
    designs, controls = specs(); allsp = designs + controls
    full = {f'T3, tail mount {MOUNT_FIX:.0f} mm'}
    J = jobs(allsp, full); t0 = time.time()
    print(f'{len(allsp)} designs, {len(J)} jobs', flush=True)
    with Pool(GG.WORKERS, initializer=_init, initargs=(allsp,)) as pool:
        R = pool.map(job, J, chunksize=1)
    rows = []
    for i, sp in enumerate(allsp):
        r = row(R, i, sp); r['role'] = 'design' if i < len(designs) else 'control'
        if sp['name'] in full:
            g = GG.collect([x for x in R if x[0][0] in ('fall', 'climb', 'turn')], i, GG.N_TRY)
            r['g123'] = dict(worst=g['worst'], by_mu=g['by_mu'], notes=sp['notes'],
                             dims={k: sp[k] for k in ('mass', 'length', 'width', 'height', 'belly', 'R')} | dict(wheels=len(sp['wheels'])))
            print(f"{sp['name']:28s} G1 {g['worst']['upright']:.3f}  G2 {g['worst']['climb']} mm  G3 {g['worst']['turn'] and round(g['worst']['turn'])} mm", flush=True)
        rows.append(r)
        print(f"{sp['name']:28s} hill up {r['up']} ({r['up_pose']}; stowed {r['up_stowed']})  down {r['down']} ({r['down_pose']}; stowed {r['down_stowed']})"
              f"  static {r['tip_static']:.1f}  crest {r['crest']} (next {r['crest_why']})  push {r['push']} kg at x{r['push_worst_mu']} {r['push_by_mu']}", flush=True)
    by = {r['name']: r for r in rows}
    T3 = by['T3']; bx = by['Box']
    ctl = [dict(gauge='hills', claim='T3 with 1 kg high on its top reads below T3 both ways, tail stowed',
                a=f"{by['T3, 1 kg high on top']['up_stowed']} / {by['T3, 1 kg high on top']['down_stowed']}", b=f"{T3['up_stowed']} / {T3['down_stowed']}",
                ok=by['T3, 1 kg high on top']['up_stowed'] < T3['up_stowed'] and by['T3, 1 kg high on top']['down_stowed'] < T3['down_stowed']),
           dict(gauge='hills', name='hills static check', claim='no design reads above its static tip angle with its tail stowed',
                a=', '.join(r['name'] for r in rows if max(r['up_stowed'], r['down_stowed']) > r['tip_static'] + 0.5) or 'none', b='none',
                ok=all(max(r['up_stowed'], r['down_stowed']) <= r['tip_static'] + 0.5 for r in rows)),
           dict(gauge='crest', claim='the box with its belly 15 mm lower reads below the box',
                a=by['Box, belly 15 mm lower']['crest'], b=bx['crest'], ok=by['Box, belly 15 mm lower']['crest'] < bx['crest']),
           dict(gauge='crest', claim='the box 1.5x long reads below the box', a=by['Box, 1.5x long']['crest'], b=bx['crest'],
                ok=by['Box, 1.5x long']['crest'] < bx['crest']),
           dict(gauge='push', claim='T3 geared 0.4x reads below T3 (worst over the band)', a=by['T3, geared 0.4x']['push'], b=T3['push'],
                ok=by['T3, geared 0.4x']['push'] < T3['push']),
           dict(gauge='push', claim='T3 at half grip reads below T3 at x0.65', a=by['T3, tyres at half grip']['push_by_mu']['0.65'],
                b=T3['push_by_mu']['0.65'], ok=by['T3, tyres at half grip']['push_by_mu']['0.65'] < T3['push_by_mu']['0.65'])]
    for c in ctl:
        print(('PASS ' if c['ok'] else 'FAIL ') + c['claim'], c['a'], 'against', c['b'])
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), source=os.path.basename(config.GAUGES_CURRENT), rows=rows, controls=ctl),
              open(os.path.join(OUT, 'card.json'), 'w'), indent=1, default=str)
    print(f'{len(J)} jobs, {time.time() - t0:.0f} s')


def com():
    """does G3 read the CoM's fore-aft offset from the wheels' centre? T3 with 150 g at its CoM's height, placed to move
    the CoM by s mm; s = 0 is the control (the same mass, the CoM unmoved). -> out/card/com_turn.json"""
    import search as S
    T3 = next(sp for sp in pickle.load(open(os.path.join(config.GAUGES_CURRENT, 'finals_specs.pkl'), 'rb')) if sp['name'] == 'T3')
    g, M = 150.0, T3['M']; W = np.array(T3['wheels']).mean(0)
    specs = [H.add_mass(T3, g, (float(T3['com'][0]) + s * (M + g) / g, 0.0, float(T3['com'][2])), f'shift {s:+.0f}')
             for s in (-10.0, -5.0, -2.0, 0.0, 2.0, 5.0, 10.0)]
    J = [('turn', i, mu, sg, 0, None) for i in range(len(specs)) for mu in GG.BAND for sg in (1, -1)]
    with Pool(GG.WORKERS, initializer=GG._init, initargs=(specs,)) as pool:
        R = pool.map(GG.job, J, chunksize=1)
    rows = []
    for i, sp in enumerate(specs):
        t = [r[0] for a, r in R if a[1] == i]; off = float(S.com_all(sp)[0] - W[0])
        rows.append(dict(name=sp['name'], offset=off, turn=max(t) if all(t) else None))
        print(f"{sp['name']:9s} CoM {off:+5.1f} mm from the wheels' centre  turn {rows[-1]['turn'] and round(rows[-1]['turn'])} mm", flush=True)
    os.makedirs(OUT, exist_ok=True); json.dump(rows, open(os.path.join(OUT, 'com_turn.json'), 'w'), indent=1)


def check():
    import knobs as K
    designs, controls = specs()
    for sp in designs + controls:
        print(f"{sp['name']:28s} {sp['mass']:7.0f} g  {sp['length']:4.0f} x {sp['width']:4.0f} x {sp['height']:4.0f}  belly {sp['belly']:4.1f}  "
              f"tail {'yes' if sp.get('limb') else 'no '}  static tip {H.tip_static(sp):.1f}")
    T3 = next(sp for sp in designs if sp['name'] == 'T3'); k3 = K.make(K.T3)
    d = {k: (round(T3[k], 2), round(k3[k], 2)) for k in ('mass', 'length', 'width', 'height', 'belly')}
    print('T3 from the finals vs rebuilt from its knobs:', d, 'limb base', T3['limb']['base'], k3['limb']['base'])


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'check': check, 'read': read, 'com': com}.get(cmd, lambda: print(__doc__))()
