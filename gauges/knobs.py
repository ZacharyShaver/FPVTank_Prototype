"""The knob log (2026-10-27): every knob, one at a time, around T3, read on all five gauges, so what each knob does to
each number is on record. Zach: "log how ... the height of the body and the width of the wheels actually translate
to the numbers on the hill climbing and all that".

    SCORPION_SEARCH=search_hills python gauges/knobs.py sweep   -> gauges/out/knobs/knobs_raw.jsonl, knobs_sweep.json
    SCORPION_SEARCH=search_hills python gauges/knobs.py rebrace -> knobs_brace.jsonl (braced over five tail angles)
    SCORPION_SEARCH=search_hills python gauges/knobs.py sweep67 -> knobs_g67.jsonl (G6 crest and G7 push for every design)
    SCORPION_SEARCH=search_hills python gauges/knobs.py rule    -> knobs_brace_rule.jsonl (a brace-angle rule against the best)
    SCORPION_SEARCH=search_hills python gauges/knobs.py speed   -> speed.json (the hills at other driving speeds)
    SCORPION_SEARCH=search_hills python gauges/knobs.py crest20 -> knobs_g67.jsonl's crest at the gauge's 20 tries
    SCORPION_SEARCH=search_hills python gauges/knobs.py grip    -> grip_hills.json (T3's hills by tread grip, x0.65 and x1)
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
          th_push=-46.177, th_stow=111.658, mz=0.431, track=113.977, msize=1.0, gear=2.091, TW=46.0, mount_z=149.6, foot_r=12.0,
          tyre_mu=1.0, bumper=0.0)
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
         ('tail', 'mount_z', 90.0, 210.0, "the tail mount's height, mm (new)"),
         ('tail', 'foot_r', 6.0, 40.0, "the tail foot's radius, mm (12 so far; a pad or skid when big; new)"),
         ('wheels', 'tyre_mu', 0.5, 1.8, "the tread's grip, times the stock tyre's (0.9 at x1; new)"),
         ('body', 'bumper', 0.0, 150.0, "a flat push face at the very front: its top, mm (60 tall, 75 g; under 40: none; new)")]
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
    if q['foot_r'] != 12.0 and sp.get('limb'):                           # a bigger foot weighs more, as a shell: 15 g at 12 mm
        sp = dict(sp, limb=dict(sp['limb'], foot_r=q['foot_r'], m_foot=15.0 * (q['foot_r'] / 12.0) ** 2))
    if q['tyre_mu'] != 1.0:
        sp = dict(sp, tyre_mu=q['tyre_mu'])
    if q['bumper'] > 40.0:                                                # a 3 mm plate and its struts, flush with the front-most point
        P = np.vstack(sp['hulls']); x0 = float(P[:, 0].max()); z1 = q['bumper']; z0 = max(30.0, z1 - 60.0)
        plate = np.array([[x, y, z] for x in (x0 - 3.0, x0 + 0.5) for y in (-100.0, 100.0) for z in (z0, z1)])
        sp = H.add_mass(dict(sp, hulls=list(sp['hulls']) + [plate]), 75.0, (x0, 0.0, (z0 + z1) / 2), sp['name'])
    return RB.dims(dict(sp, TW=q['TW'])) if (q['TW'], q['foot_r']) != (46.0, 12.0) else sp


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


G_KEYS = ('up', 'climb', 'turn', 'h_up', 'h_down', 'hb_up', 'hb_down', 'crest', 'push')


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
    noise = {g: float(np.std([q[g] for q in t3])) for g in G_KEYS if g not in ('crest', 'push')   # read once, copied to every seed
             and all(q.get(g) is not None for q in t3)}
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
    bf = os.path.join(OUT, 'knobs_brace.jsonl')
    done = {(b['tag'], json.dumps(b['ch'], sort_keys=True)) for b in map(json.loads, open(bf))} if os.path.exists(bf) else set()
    J = [(r['tag'], r['ch']) for r in rows if r['seed'] == 85000 and r['s'] is not None and r['s'].get('hb_up') is not None
         and (r['tag'], json.dumps(r['ch'], sort_keys=True)) not in done]                # only designs not braced yet
    t0 = time.time()
    with Pool(GG.WORKERS) as pool, open(bf, 'a') as f:
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
    gf = os.path.join(OUT, 'knobs_g67.jsonl')
    if os.path.exists(gf):                                                # crest and push: one seed, given to every seed's row
        Q = {(q['tag'], json.dumps(q['ch'], sort_keys=True)): q for q in map(json.loads, open(gf))}
        for r in rows:
            q = Q.get((r['tag'], json.dumps(r['ch'], sort_keys=True)))
            if q and r['s'] is not None:
                r['s'].update(crest=q['crest'], push=q['push'])
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


def g67_job(a):
    import crest as CR, push as PU
    tag, ch = a; sp = make(dict(T3, **ch))
    if sp is None:
        return tag, ch, None
    c, cs = CR.ladder(sp, CR.GRIP, H.N_SCREEN, 85000)
    P = {mu: PU.ladder(sp, mu, H.N_SCREEN, 85000) for mu in GG.BAND}; w = min(P, key=lambda mu: P[mu][0])
    return tag, ch, dict(crest=c, crest_why=cs.get(c + 5), push=P[w][0], push_mu=w, push_by_mu={str(mu): v[0] for mu, v in P.items()},
                         push_why=P[w][1].get(PU.nxt(P[w][0])))


def sweep67():
    """G6 crest and G7 push for every design of the sweep, one seed, 6 tries (the screen's): crest at x2.5, push the
    worst over the band. -> knobs_g67.jsonl, then knobs_sweep.json"""
    gf = os.path.join(OUT, 'knobs_g67.jsonl')
    done = {(q['tag'], json.dumps(q['ch'], sort_keys=True)) for q in map(json.loads, open(gf))} if os.path.exists(gf) else set()
    J = [(t, c) for t, c, sd in jobs() if sd == 85000 and (t, json.dumps(c, sort_keys=True)) not in done]; t0 = time.time()
    print(f'{len(J)} designs for crest and push', flush=True)
    with Pool(GG.WORKERS) as pool, open(gf, 'a') as f:
        for i, (tag, ch, out) in enumerate(pool.imap_unordered(g67_job, J, chunksize=1)):
            if out is not None:
                f.write(json.dumps(dict(tag=tag, ch=ch, **out), default=float) + '\n'); f.flush()
            if i % 30 == 0:
                print(f'{i + 1}/{len(J)}, {time.time() - t0:.0f} s', flush=True)
    write()


def rule_angle(sp):
    """the brace angle that puts the foot just on the ground, degrees (pitch below level), within the servo's range"""
    lm = sp['limb']; r = lm.get('foot_r', RB.FOOT_R)
    return max(-75.0, min(-5.0, math.degrees(math.asin(max(-1.0, min(1.0, (r - lm['base'][2]) / lm['L']))))))


def rule_job(a):
    tag, ch = a; sp = make(dict(T3, **ch)); th = rule_angle(sp)
    return tag, ch, dict(th=th, **{'hr_' + g: H.ladder(sp, H.GRIP, d, H.N_SCREEN, 85000, th)[0] for d, g in ((False, 'up'), (True, 'down'))})


def brace_rule():
    """K3: does a rule (the foot just on the ground) pick as well as the best of five held angles? Every braced
    design at its rule angle, one seed. -> knobs_brace_rule.jsonl"""
    B = list(map(json.loads, open(os.path.join(OUT, 'knobs_brace.jsonl')))); t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(rule_job, [(b['tag'], b['ch']) for b in B], chunksize=1)
    by = {(t, json.dumps(c, sort_keys=True)): o for t, c, o in R}; tally = {}
    with open(os.path.join(OUT, 'knobs_brace_rule.jsonl'), 'w') as f:
        for b in B:
            o = by[(b['tag'], json.dumps(b['ch'], sort_keys=True))]
            f.write(json.dumps(dict(tag=b['tag'], ch=b['ch'], best_up=b['hb_up'], best_down=b['hb_down'], **o)) + '\n')
            for g in ('up', 'down'):
                dd = o['hr_' + g] - b['hb_' + g]; tally[(g, dd)] = tally.get((g, dd), 0) + 1
    print(f'{len(B)} designs, {time.time() - t0:.0f} s; rule minus best (degrees: count):', {f'{g} {d:+d}': n for (g, d), n in sorted(tally.items())})


SPEEDS = (0.15, 0.25, 0.5, 0.8)


def speed_job(a):
    name, ch, v, down, th, mu = a; sp = make(dict(T3, **ch))
    H.V_HILL, H.T_HILL = v, max(8.0, H.HILL_MM * 1e-3 / v + H.RAMP + 2.0)   # the 2.5 m at v, with room (8 s timed out every try under 0.5)
    if th == 'rule':
        th = rule_angle(sp)
    return a, H.ladder(sp, mu, down, 20, 61, th)


def speed():
    """K6: the hills at other driving speeds (H.V_HILL, 0.5 m/s in the gauge), T3 and two knob extremes, stowed and
    braced at the rule angle, 20 tries, at x2.5 and x1. -> speed.json"""
    designs = [('T3', {}), ('ride height 90', dict(clr=90.0)), ('tyre gap 150', dict(gap=150.0))]
    J = [(n, ch, v, down, th, mu) for n, ch in designs for v in SPEEDS for down in (False, True) for th in (None, 'rule') for mu in (H.GRIP, 1.0)]
    t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(speed_job, J, chunksize=1)
    out = [dict(name=n, v=v, down=down, tail='stowed' if th is None else 'braced', mu=mu, top=top, why=seen.get(top + 5))
           for (n, ch, v, down, th, mu), (top, seen) in R]
    for n, _ in designs:
        for mu in (H.GRIP, 1.0):
            line = []
            for v in SPEEDS:
                g = {(r['down'], r['tail']): r['top'] for r in out if r['name'] == n and r['v'] == v and r['mu'] == mu}
                line.append(f"{v}: {g[(False, 'stowed')]}/{g[(True, 'stowed')]} b {g[(False, 'braced')]}/{g[(True, 'braced')]}")
            print(f'{n:15s} x{mu}: ' + '  '.join(line), flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), rows=out), open(os.path.join(OUT, 'speed.json'), 'w'), indent=1, default=str)


def crest20_job(a):
    import crest as CR
    tag, ch = a; sp = make(dict(T3, **ch)); c, cs = CR.ladder(sp, CR.GRIP, 20, 85000)
    return tag, ch, c, cs.get(c + 5)


def crest20():
    """G6 again at the gauge's 20 tries for every design: at 6, T3 (which tips about 1 try in 6 at 30 degrees) passed
    or failed by luck, and its push-angle neighbours read 40 against its 25. Rewrites knobs_g67.jsonl's crest (the
    6-try reading kept as crest_6), then knobs_sweep.json"""
    gf = os.path.join(OUT, 'knobs_g67.jsonl'); Q = [json.loads(l) for l in open(gf)]
    J = [(q['tag'], q['ch']) for q in Q if 'crest_6' not in q]; t0 = time.time()
    with Pool(GG.WORKERS) as pool:
        R = pool.map(crest20_job, J, chunksize=1)
    by = {(t, json.dumps(c, sort_keys=True)): (v, w) for t, c, v, w in R}
    with open(gf, 'w') as f:
        for q in Q:
            k = (q['tag'], json.dumps(q['ch'], sort_keys=True))
            if k in by:
                q['crest_6'], q['crest_why_6'] = q['crest'], q['crest_why']; q['crest'], q['crest_why'] = by[k]
            f.write(json.dumps(q, default=float) + '\n')
    print(f'{len(J)} designs, crest at 20 tries, {time.time() - t0:.0f} s'); write()


def grip_job(a):
    g, down, th, mu = a; sp = make(dict(T3, tyre_mu=g))
    return a, H.ladder(sp, mu, down, 20, 61, rule_angle(sp) if th else None)


def grip_hills():
    """K1: tread grip on the hills on ordinary ground (x1) and the band's slipperiest (x0.65), where the tyres bind;
    the sweep reads hills at x2.5, where they don't. T3, stowed and braced at the rule angle, 20 tries. -> grip_hills.json"""
    G_ = (0.5, 0.75, 1.0, 1.25, 1.5, 1.8); J = [(g, d, th, mu) for g in G_ for d in (False, True) for th in (False, True) for mu in (0.65, 1.0)]
    with Pool(GG.WORKERS) as pool:
        R = pool.map(grip_job, J, chunksize=1)
    out = [dict(grip=g, down=d, tail='braced' if th else 'stowed', mu=mu, top=top, why=seen.get(top + 5)) for (g, d, th, mu), (top, seen) in R]
    for mu in (0.65, 1.0):
        print(f'x{mu}: ' + '  '.join(f"grip {g}: " + '/'.join(str(next(r['top'] for r in out if r['grip'] == g and r['mu'] == mu and r['down'] == d and r['tail'] == t))
                                                       for t in ('stowed', 'braced') for d in (False, True)) for g in G_), flush=True)
    json.dump(dict(rows=out), open(os.path.join(OUT, 'grip_hills.json'), 'w'), indent=1, default=str)


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
    {'sweep': sweep, 'check': check, 'side': side, 'rebrace': rebrace, 'write': write, 'sweep67': sweep67, 'rule': brace_rule, 'speed': speed, 'crest20': crest20, 'grip': grip_hills}.get(cmd, lambda: print(__doc__))()
