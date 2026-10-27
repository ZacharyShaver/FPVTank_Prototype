"""The knob log (2026-10-27): every knob, one at a time, around T3, read on all five gauges, so what each knob does to
each number is on record. Zach: "log how ... the height of the body and the width of the wheels actually translate
to the numbers on the hill climbing and all that".

    SCORPION_SEARCH=search_hills python gauges/knobs.py sweep   -> gauges/out/knobs/knobs_raw.jsonl, knobs_sweep.json
    SCORPION_SEARCH=search_hills python gauges/knobs.py rebrace -> knobs_brace.jsonl (braced over five tail angles)
    SCORPION_SEARCH=search_hills python gauges/knobs.py side    -> gauges/out/knobs/side.json (a side slope, exploratory)

T3 is the shape study's best (1.00 / 150 mm / 381 mm; hills 35 / 40 stowed, 45 / 45 braced). Each knob takes 7
values across its range, the rest at T3's, 3 seeds each; T3 itself takes 8 seeds, the noise a knob's effect is read
against. Each design gets the lean screen without its cut (G1 from 60 falls, G2's ladder at x0.65 and x1.5, G3 at the
band) and both hills at x2.5 in 6 tries, tail stowed and braced (the better of -30 and -15 degrees, held).

Two knobs are new: the tyres' width (TW, 46 mm in every design so far) and the tail mount's height (pinned at T5's
since the shape study). Ride height (clr) raises the body, its insides and the tail mount together; the wheels stay.
Two switches ride along: the tail off, and a middle axle.
"""
import os, sys, json, math, time
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import gauges as GG, robots as RB, search as S, hills as H

OUT = os.path.join(config.GAUGES_OUT, 'knobs')
T3 = dict(R=44.908, xw=14.684, gap=62.052, clr=51.943, dxp=23.189, dzp=0.56, six=0.0, shell=1.0, xc=27.025, af=166.408,
          ar=156.628, b=120.606, zc=159.624, cu=71.913, cd=71.847, p=3.26, qu=2.256, qd=2.565, limb=1.0, L=279.186, tq=3.306,
          th_push=-46.177, th_stow=111.658, mz=0.431, track=113.977, msize=1.0, gear=2.091, TW=46.0, mount_z=149.6)
MOUNT = (-154.83, 0.0)                    # the tail mount's x and y (T5's, pinned); its z is mount_z
# (group, knob, low, high, what it is). The ranges are the searches' own; TW and mount_z are new.
KNOBS = [('wheels', 'R', 35.0, 95.0, "the wheels' radius, mm"),
         ('wheels', 'gap', 15.0, 150.0, 'the gap between front and rear tyres, mm (sets the wheelbase with R)'),
         ('wheels', 'xw', -80.0, 80.0, "the wheelbase's centre, mm ahead of the body's"),
         ('wheels', 'track', 110.0, 180.0, "the wheels' centre planes from the centre line, mm (the robot's width)"),
         ('wheels', 'TW', 25.0, 80.0, "the tyres' width, mm (new)"),
         ('body', 'clr', 15.0, 90.0, "ride height: the body's belly above the ground, mm (body, insides and tail mount)"),
         ('body', 'zc', 30.0, 220.0, "the skin's middle height, mm"),
         ('body', 'cu', 40.0, 250.0, "the skin's height above its middle, mm"),
         ('body', 'cd', 20.0, 150.0, "the skin's depth below its middle, mm"),
         ('body', 'af', 120.0, 260.0, "the skin's reach forward, mm"),
         ('body', 'ar', 120.0, 260.0, "the skin's reach back, mm"),
         ('body', 'b', 100.0, 200.0, "the skin's half-width, mm"),
         ('body', 'xc', -40.0, 60.0, "the skin's centre, mm ahead"),
         ('body', 'p', 1.6, 5.0, "the skin's squareness seen from above (2 round, 5 boxy)"),
         ('body', 'qu', 1.0, 4.0, "the skin's top squareness (1 pointed, 4 flat)"),
         ('body', 'qd', 1.0, 4.0, "the skin's bottom squareness"),
         ('insides', 'dxp', -80.0, 80.0, 'the battery packs moved forward, mm'),
         ('insides', 'dzp', -8.0, 15.0, 'the battery packs moved up, mm'),
         ('drive', 'gear', 0.4, 2.5, 'the gearing, times the stock 30:1 (slower and stronger up)'),
         ('drive', 'msize', 0.5, 2.0, "the motors' size, times the stock 37 mm"),
         ('tail', 'L', 80.0, 350.0, "the tail's length, mm"),
         ('tail', 'tq', 0.3, 4.0, "the tail servo's stall torque, N m"),
         ('tail', 'th_push', -90.0, -10.0, "the tail's pitch when it pushes on a step, degrees (below level)"),
         ('tail', 'th_stow', 20.0, 160.0, "the tail's stowed pitch, degrees (90 up, 180 forward over the body)"),
         ('tail', 'mount_z', 90.0, 210.0, "the tail mount's height, mm (new)")]
SWITCHES = [('tail off', dict(limb=0.0)), ('six wheels', dict(six=1.0))]
N_VAL, SEEDS, T3_SEEDS = 7, 3, 8
BRACE = (-30.0, -15.0)


def make(q):
    """the spec of a design given as T3's knobs with changes; None when it can't be built"""
    q = dict(q); wb = 2 * q['R'] + q['gap'] if q['six'] <= 0.5 else 2 * (2 * q['R'] + q['gap'])
    q['xf'], q['xr'] = q['xw'] + wb / 2, q['xw'] - wb / 2
    S.LIMB_BASE = (MOUNT[0], MOUNT[1], q['mount_z'] + q['clr'] - T3['clr'])   # the mount rides with the body
    sp = S.build(np.array([q[k] for k in S.KEYS]))
    if sp is None:
        return None
    return RB.dims(dict(sp, TW=q['TW'])) if q['TW'] != 46.0 else sp


def screen(a):
    tag, ch, seed = a
    sp = make(dict(T3, **ch))
    if sp is None:
        return tag, ch, seed, None
    s = S.screen_lean(sp, seed, cut=False); s.update(S.statics(sp))
    G = S.com_all(sp); s.update(tip_static=H.tip_static(sp), com_x=float(G[0]), com_z=float(G[2]),
                                **{k: sp[k] for k in ('mass', 'length', 'width', 'height', 'belly')})
    for down, g in ((False, 'up'), (True, 'down')):
        s['h_' + g] = H.ladder(sp, H.GRIP, down, H.N_SCREEN, seed)[0]
        s['hb_' + g] = max(H.ladder(sp, H.GRIP, down, H.N_SCREEN, seed, th)[0] for th in BRACE) if sp.get('limb') else None
    return tag, ch, seed, s


def jobs():
    J = [('T3', {}, 85000 + i) for i in range(T3_SEEDS)]
    for _, k, lo, hi, _ in KNOBS:
        for v in np.linspace(lo, hi, N_VAL):
            J += [(k, {k: float(v)}, 85000 + i) for i in range(SEEDS)]
    for nm, ch in SWITCHES:
        J += [(nm, ch, 85000 + i) for i in range(SEEDS)]
    return J


G_KEYS = ('up', 'climb', 'turn', 'h_up', 'h_down', 'hb_up', 'hb_down')


def summarise(rows):
    """per knob and value: the gauges' means over the seeds, the screen's statics, and T3's noise (sd over its seeds)"""
    by = {}
    for r in rows:
        k = r['tag']; v = r['ch'].get(k) if k in r['ch'] else None
        by.setdefault(k, {}).setdefault(v, []).append(r['s'])
    mean = lambda ss, g: (None if not ss or any(q.get(g) is None for q in ss) else float(np.mean([q[g] for q in ss])))
    res = {}
    for k, vs in by.items():
        res[k] = []
        for v, ss in sorted(vs.items(), key=lambda t: -1e9 if t[0] is None else t[0]):
            ok = [q for q in ss if q is not None]
            res[k].append(dict(v=v, built=len(ok), of=len(ss), **{g: mean(ok, g) for g in G_KEYS + ('tip_static', 'com_x', 'com_z', 'mass', 'length', 'width', 'height', 'belly')}))
    t3 = [r['s'] for r in rows if r['tag'] == 'T3']
    noise = {g: float(np.std([q[g] for q in t3])) for g in G_KEYS}
    return res, noise


def sweep():
    os.makedirs(OUT, exist_ok=True); J = jobs(); raw = os.path.join(OUT, 'knobs_raw.jsonl'); t0 = time.time()
    done = set()
    if os.path.exists(raw):                                               # resume after a stop
        done = {(r['tag'], json.dumps(r['ch'], sort_keys=True), r['seed']) for r in map(json.loads, open(raw))}
    J = [j for j in J if (j[0], json.dumps(j[1], sort_keys=True), j[2]) not in done]
    print(f'{len(J)} screens to run ({len(done)} done)', flush=True)
    with Pool(GG.WORKERS) as pool, open(raw, 'a') as f:
        for i, (tag, ch, seed, s) in enumerate(pool.imap_unordered(screen, J, chunksize=1)):
            f.write(json.dumps(dict(tag=tag, ch=ch, seed=seed, s=s), default=float) + '\n'); f.flush()
            if i % 30 == 0:
                print(f'{i + 1}/{len(J)}, {time.time() - t0:.0f} s', flush=True)
    write()


BRACE_ALL = (-75.0, -60.0, -45.0, -30.0, -15.0)


def brace_job(a):
    tag, ch = a; sp = make(dict(T3, **ch)); out = {}
    for down, g in ((False, 'up'), (True, 'down')):
        r = {th: H.ladder(sp, H.GRIP, down, H.N_SCREEN, 85000, th)[0] for th in BRACE_ALL}
        out['hb_' + g] = max(r.values()); out['hb_' + g + '_th'] = max(r, key=lambda t: (r[t], t)); out['hb_' + g + '_all'] = r
    return tag, ch, out


def rebrace():
    """the braced hills again, over BRACE_ALL, one seed (T3's hills don't move over 8 seeds). The sweep's -30 and -15
    left the foot in the air once the body or the mount rose or the tail got short. -> knobs_brace.jsonl"""
    rows = [json.loads(l) for l in open(os.path.join(OUT, 'knobs_raw.jsonl'))]
    J = [(r['tag'], r['ch']) for r in rows if r['seed'] == 85000 and r['s'] is not None and r['s'].get('hb_up') is not None]
    t0 = time.time()
    with Pool(GG.WORKERS) as pool, open(os.path.join(OUT, 'knobs_brace.jsonl'), 'w') as f:
        for i, (tag, ch, out) in enumerate(pool.imap_unordered(brace_job, J, chunksize=1)):
            f.write(json.dumps(dict(tag=tag, ch=ch, **out), default=float) + '\n'); f.flush()
    print(f'{len(J)} designs braced again, {time.time() - t0:.0f} s'); write()


def write():
    """knobs_sweep.json from the raw screens, the braced hills from knobs_brace.jsonl where it exists (the sweep's own,
    over -30 and -15, kept as hb_*_2)"""
    rows = [json.loads(l) for l in open(os.path.join(OUT, 'knobs_raw.jsonl'))]; bf = os.path.join(OUT, 'knobs_brace.jsonl')
    if os.path.exists(bf):
        B = {(b['tag'], json.dumps(b['ch'], sort_keys=True)): b for b in map(json.loads, open(bf))}
        for r in rows:
            b = B.get((r['tag'], json.dumps(r['ch'], sort_keys=True)))
            if b and r['s'] is not None:
                for g in ('up', 'down'):
                    r['s']['hb_' + g + '_2'] = r['s']['hb_' + g]; r['s']['hb_' + g] = b['hb_' + g]; r['s']['hb_' + g + '_th'] = b['hb_' + g + '_th']
    res, noise = summarise(rows)
    t3 = res['T3'][0]
    json.dump(dict(base=T3, brace=BRACE_ALL if os.path.exists(bf) else BRACE, knobs=[dict(group=g, key=k, lo=lo, hi=hi, what=w) for g, k, lo, hi, w in KNOBS],
                   switches=[n for n, _ in SWITCHES], noise=noise, results=res), open(os.path.join(OUT, 'knobs_sweep.json'), 'w'), indent=1, default=float)
    print(f"T3: {t3}\nnoise (sd over {T3_SEEDS} seeds): {noise}")
    for _, k, *_ in KNOBS:
        print(f'{k:8s} ' + '  '.join(f"{r['v']:.3g}: {r['up'] if r['up'] is None else round(r['up'], 2)}/{r['climb'] and round(r['climb'])}/{r['turn'] and round(r['turn'])} "
                                    f"h {r['h_up'] and round(r['h_up'])}/{r['h_down'] and round(r['h_down'])} b {r['hb_up'] and round(r['hb_up'])}/{r['hb_down'] and round(r['hb_down'])}"
                                    for r in res[k]), flush=True)
    for nm, _ in SWITCHES:
        r = res[nm][0]; print(f"{nm}: {r['up']:.2f}/{r['climb']:.0f}/{r['turn']:.0f} h {r['h_up']}/{r['h_down']} b {r['hb_up']}/{r['hb_down']}")


SIDE_POSES = ((None, None), (90.0, -30.0), (90.0, -45.0))               # stowed; the tail out down the slope, braced


def side_job(a):
    name, ch, mu, pose, top_kg = a
    sp = make(dict(T3, **ch))
    if top_kg:
        sp = H.add_mass(sp, 1000.0 * top_kg, (float(sp['com'][0]), 0.0, float(sp['hulls'][0][:, 2].max()) - 20.0), name)
    top, seen = H.side_ladder(sp, mu, 10, 61, *pose)
    return a, top, seen.get(top + 5), H.side_static(sp), float(S.com_all(sp)[2]), sp['width']


def side():
    """a side slope (exploratory): T3 and its width and height knobs, tail stowed and out as an outrigger, at x2.5 and
    x1. The control: 1 kg on top must read lower wherever tipping binds. -> out/knobs/side.json"""
    specs = [('T3', {}, 0), ('track 110', dict(track=110.0), 0), ('track 145', dict(track=145.0), 0), ('track 180', dict(track=180.0), 0),
             ('tyres 25 wide', dict(TW=25.0), 0), ('tyres 80 wide', dict(TW=80.0), 0), ('ride height 15', dict(clr=15.0), 0),
             ('ride height 90', dict(clr=90.0), 0), ('T3, 1 kg on top', {}, 1)]
    J = [(n, ch, mu, pose, kg) for n, ch, kg in specs for mu in (H.GRIP, 1.0) for pose in SIDE_POSES]
    t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(side_job, J, chunksize=1)
    out = []
    for (n, ch, mu, pose, kg), top, why, st, cz, w in R:
        out.append(dict(name=n, mu=mu, tail='stowed' if pose[0] is None else f'yaw {pose[0]:.0f}, pitch {pose[1]:.0f}', side=top, why=why,
                        static=st, com_z=cz, width=w))
        print(f"{n:18s} x{mu:<4} tail {out[-1]['tail']:20s} side {top:3d} (next: {why})  static {st:.1f}  CoM z {cz:.1f}  width {w:.0f}", flush=True)
    os.makedirs(OUT, exist_ok=True)
    json.dump(dict(wall_s=round(time.time() - t0), rows=out), open(os.path.join(OUT, 'side.json'), 'w'), indent=1, default=str)
    print(f'{len(J)} ladders, {time.time() - t0:.0f} s')


def check():
    """T3 rebuilt from its knobs must match the shape study's T3 (its mass and centre of mass)"""
    import pickle
    sp = make(T3); ref = {s['name']: s for s in pickle.load(open(os.path.join(config.GAUGES_OUT, 'search_shape', 'finals_specs.pkl'), 'rb'))}['T3']
    print(f"T3 rebuilt: mass {sp['mass']:.1f} (ref {ref['mass']:.1f}), CoM {np.round(S.com_all(sp), 2)} (ref {np.round(S.com_all(ref), 2)}), "
          f"tail base {sp['limb']['base']} (ref {ref['limb']['base']})")
    for k, v in (('clr', 80.0), ('TW', 70.0), ('mount_z', 200.0), ('track', 170.0)):
        q = make(dict(T3, **{k: v})); print(f"{k}={v}: mass {q['mass']:.1f}, CoM z {S.com_all(q)[2]:.1f}, belly {q['belly']:.1f}, TW {q['TW']}, base {np.round(q['limb']['base'], 1)}, width {q['width']:.0f}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'sweep': sweep, 'check': check, 'side': side, 'rebrace': rebrace, 'write': write}.get(cmd, lambda: print(__doc__))()
