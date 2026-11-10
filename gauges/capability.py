"""The capability search (2026-10-28): every knob free at once, every gauge pushed as far as it goes, no weights.
Zach: "max out every single goal dont set the percentages. targets should go as high or low as they can in each direction
were shooting to test out the capability of this project so we can learn from the results" (done before 5 pm).

    python gauges/capability.py smoke    # two designs, two tries a rung: it runs end to end, and how long a screen takes
    python gauges/capability.py run      # B, then refinement until DEADLINE, then the finals -> gauges/out/capability/
    python gauges/capability.py finals   # the finals again from the screens on disk

The space is the knob log's (gauges/knobs.py), around nothing: every knob over its whole range, plus three switches (a
tail, six wheels, a skin over the Trainer's body). Held: the two dead knobs (knobs.DEAD, dropped 2026-10-28) and the
tread's grip (a property to measure, not a design choice; the sim's value is a guess and every gauge would take more).

A screen reads all seven gauges, 6 tries a rung: G1 from 60 falls (x1.5 and x0.65, no cut), G2's ladder at x0.65 and
x1.5, G3 at the band, both hills at x2.5 stowed and braced (-30 and -15, the better), the crest at x2.5, the push over
the band. **G2's ladder runs past its 150 mm top here** (to 300 mm, 25 mm rungs above 150), because T3 and T5 already
top it out; the gauge itself is unchanged. B is 1,024 Sobol designs; then eight cross-entropy streams share every
screened design: one per gauge (that gauge alone, ties broken by the all-rounder rank) and one all-rounder (the worst
of its seven percentile ranks among everything screened: a balance with no weights). Rounds run until DEADLINE. The
finals, read on the full gauges (and the same long ladder): each stream's best, the all-rounders at the top of the
seven-way front, T3 and the box.
"""
import os, sys, json, math, time, datetime, zlib
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')                # as knobs.py, whose make() builds the designs
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config, stamp
import gauges as GG, search as S, hills as H, crest as C, push as P, knobs as K, weights as W

# The strict run (SCORPION_CAP=capability_strict, 2026-10-28 evening): Zach, on the first run's shapes, "a lot of
# floating parts ... some of the shapes are impossible to make", then "it kinda needs to morph towards the wheel base"
# and "size limits on the wheels to a realistic proportion for a motor that can move this thing". The same space, seeds
# and protocol, every design built strict (knobs.make: the body grown to any part off it, the push plate faired in,
# a drive too weak for its wheels refused). The first run stays as it ran.
RUN = os.environ.get('SCORPION_CAP', 'capability')
STRICT = RUN != 'capability'
# The wide run (SCORPION_CAP=capability_tail, 2026-10-30 night): Zach, after the tail upgrades, "kick of an overnight
# search. try to use the full night. the goals to learn here so explore with a wide net". The strict run's space plus
# the new tail knobs (knobs.L2, rear_up) and the front flippers (knobs.FLIP_KNOBS and their switches), B twice as big
# (an even sample to learn from, before any stream leans on it), and a ninth stream, 'low': the all-rounder among
# bodies whose top stands under LOW_TOP (T3's skin tops out at 231 mm). The runs before keep their spaces.
# The low step-and-turn run (SCORPION_CAP=capability_low, 2026-10-31): the wide run's best all-rounder was a low body,
# but no design reached T3's corner (step 150 mm, turn inside 450 mm, upright 0.9), and T3 itself was found by a search
# that asked for the step and the turn together. Zach: "Yes, run it". The wide run's space; no B: its streams start
# from the wide run's 5,288 screens (SEED_FROM, which also stay in the pool to pick elites from, but are never this
# run's champions); five streams of step - w x turn, the body under LOW_TOP and upright at UP_MIN, a miss scored by how
# far it misses so the streams can steer back (LOW_STREAMS).
# The real run (SCORPION_CAP=capability_real, 2026-10-31): the winners grown as one piece (unibody.design_knobs) lost
# 20-120 mm of step, and the strict build had passed motors through the packs and flippers off the body. Zach: "an
# unrealistic robot in simulation ... cannot give us a workable design ... the system works if the tests can be
# trusted". The wide run's space and protocol, every design built real (knobs.make(real=True): weighed as its one-piece
# print, a skin cut back round its tyres, the motors clear of the parts inside, the flippers mounted on the body).
# The rough run (SCORPION_CAP=capability_rough, 2026-11-02): Zach, "we need to implement a system of weights for every
# test add rough terrain". The tow run plus G8 rough ground (rough.py) as an eighth gauge; the all-rounder is weighted
# by weights.WEIGHTS in every run (equal weights: the worst rank, as before).
# The 250 mm run (SCORPION_CAP=capability_250, 2026-11-07): Zach capped the body and wheels at 250 mm ("Longer prints
# are easy on pla, if we want better materials it gets more risky depending on how long it prints for"; the claws and
# tail don't count) and took the head out of the body ("We would want the flexibility to be able to move that somewhere
# else"). The rough run's protocol; the head sits on the body's top at a new knob (knobs.HEAD_KNOBS); a design whose
# body print is over CAP_MM on any side is refused (knobs.cap_problems); every body is a skin (the Trainer's own tub is
# 276 mm long); the skin's size knobs span what the cap allows (CAP_RANGES).
CAP = RUN == 'capability_250'
CAP_MM = 250.0 if CAP else None
LOW = RUN == 'capability_low'
ROUGH = RUN in ('capability_rough', 'capability_250')
TOW = RUN in ('capability_tow', 'capability_rough', 'capability_250')     # the tow run (2026-11-02): the real run with G7 tow in
REAL = RUN in ('capability_real', 'capability_tow', 'capability_rough', 'capability_250')   # place of push (tow.py); push is still read in the finals
if REAL:                                                                  # and G2 read pooled (gauges.STEP_RULE): the rung rule's
    GG.STEP_RULE = 'pooled'                                               # reading of one design swung 50-150 mm with the seeds
WIDE = RUN in ('capability_tail', 'capability_low', 'capability_real', 'capability_tow', 'capability_rough', 'capability_250')
OUT = os.path.join(config.GAUGES_OUT, RUN)
SCREENS = os.path.join(OUT, 'screens.jsonl')
SEED_FROM = os.path.join(config.GAUGES_OUT, 'capability_tail', 'screens.jsonl') if LOW else None
DEADLINES = {'capability': datetime.datetime(2026, 10, 28, 15, 15), 'capability_strict': datetime.datetime(2026, 10, 29, 0, 30),
             'capability_tail': datetime.datetime(2026, 10, 31, 6, 30), 'capability_low': datetime.datetime(2026, 10, 31, 12, 0),
             'capability_real': datetime.datetime(2026, 11, 1, 7, 0),
             'capability_tow': datetime.datetime(2026, 11, 2, 16, 10)}
DEADLINE = DEADLINES.get(RUN, DEADLINES['capability_strict'])             # the last round ends by then
if os.environ.get('SCORPION_UNTIL'):                                      # or by then ('2026-11-03 07:00')
    DEADLINE = datetime.datetime.fromisoformat(os.environ['SCORPION_UNTIL'])
WORKERS = int(os.environ.get('SCORPION_WORKERS', GG.WORKERS))
LOW_TOP = 160.0                                                           # mm: the 'low' stream's bodies (WIDE)


def build(q, why=None):
    return K.make(q, strict=STRICT, real=REAL, why=why, cap=CAP_MM)


def t3_ref():
    """T3 as this run builds it, the reference on its pages and finals: the real build refuses T3 as it is (its motors
    8-9 mm into the ESCs and packs at track 114), so there T3 at track 130, where they clear. The 250 mm run: T3's
    head on its top (T3_HEAD_F), not held to the cap (its skin is 323 mm long)"""
    if CAP:
        return K.make(dict(K.T3, track=130.0, head_f=T3_HEAD_F), strict=STRICT, real=REAL)
    return build(K.T3) or build(dict(K.T3, track=130.0))
HEIGHTS_EXT = tuple(range(10, 160, 10)) + tuple(range(175, 301, 25))    # past G2's 150 mm top, for this run only
HELD_K = (() if WIDE else K.DEAD) + ('tyre_mu',) + (('msize',) if STRICT else ()) + (() if WIDE else ('L2', 'rear_up'))   # strict: the stock 37 mm
# (the wide run frees the dead two, cu and qu, the skin's top: a low, flat body needs its top to move)
# motors (Zach, 2026-10-28: "hold the drive motors at the stock 37 mm size"; the first run's champions ran motors 1.3-2x it).
# Gearing still searches. The tail knobs of 2026-10-30 only in the wide run, so the runs before rebuild as they ran.
# strict: track is the front axle's, track_r the rear's (Zach, 2026-10-28: "two knobs for wheel width")
SPACE = [(k, lo, hi) for _, k, lo, hi, _ in K.KNOBS if k not in HELD_K] + ([('track_r', 110.0, 180.0)] if STRICT else []) \
        + [('limb', 0.0, 1.0), ('six', 0.0, 1.0), ('shell', 0.0, 1.0)] \
        + ([(k, lo, hi) for _, k, lo, hi, _ in K.FLIP_KNOBS] + [('flip', 0.0, 1.0), ('f_tail', 0.0, 1.0), ('f_nose', 0.0, 1.0)] if WIDE else [])
# The 250 mm run's ranges for the knobs that set the body's size: the old ones reached a 520 mm skin, a 400 mm width and
# a 340 mm wheelbase, and not one of 480 samples passed the cap. The parts inside span 239 mm, so the skin's reach
# fore and aft can only shape it inside that; the width keeps the skin and the motor pods under 250; the axles stay
# under the body. Picked so about half the samples pass (gauges/README.md, "The 250 mm run").
CAP_RANGES = dict(af=(40.0, 110.0), ar=(40.0, 110.0), xc=(-15.0, 10.0), b=(60.0, 125.0), zc=(30.0, 160.0), cu=(20.0, 150.0),
                  cd=(20.0, 120.0), dxp=(-80.0, 10.0), R=(35.0, 70.0), gap=(15.0, 80.0), xw=(-25.0, 15.0),
                  track=(126.0, 142.0), track_r=(126.0, 142.0))
T3_HEAD_F = 1.0
if CAP:                                                                   # every body a skin; the head's place a knob
    SPACE = [(k,) + CAP_RANGES.get(k, (lo, hi)) for k, lo, hi in SPACE if k != 'shell'] + [(k, lo, hi) for _, k, lo, hi, _ in K.HEAD_KNOBS]
KEYS = [k for k, _, _ in SPACE]; LO = np.array([a for _, a, _ in SPACE]); HI = np.array([b for _, _, b in SPACE])
GAUGES = (('up', 1), ('climb', 1), ('turn', -1), ('h_up', 1), ('h_down', 1), ('crest', 1), (('tow', 1) if TOW else ('push', 1))) \
         + ((('rough', 1),) if ROUGH else ())
G7 = GAUGES[6][0]                                                         # push, or tow in the tow run
COUNT = W.counted([g for g, _ in GAUGES])                                 # the gauges weighted above 0
LOW_STREAMS = {'st_0.1': 0.1, 'st_0.25': 0.25, 'st_0.5': 0.5, 'st_1': 1.0, 'turn450': None}   # w; turn450: the most step inside 450 mm
UP_MIN, TURN_CAP = 0.75, 450.0                                            # G1's floor; turn450's circle (mm)
STREAMS = tuple(LOW_STREAMS) if LOW else tuple(COUNT) + ('all',) + (('low',) if WIDE else ())
N_SCREEN, N_B, POP, ELITE = 6, 0 if LOW else 4096 if CAP else 2048 if WIDE else 1024, 30, 8   # CAP: ~15 % build (refusals cost ~1 s)


def q_of(z):
    """a point of [0, 1]^d as the knobs make() takes; the switches as on/off (limb above search.LIMB_ON is a tail)"""
    q = dict(K.T3); q.update({k: float(lo + v * (hi - lo)) for (k, lo, hi), v in zip(SPACE, z)})
    q['six'] = 1.0 if q['six'] > 0.5 else 0.0; q['shell'] = 1.0 if q['shell'] > 0.5 else 0.0
    q['limb'] = 1.0 if q['limb'] > 0.5 else 0.0
    return q


def _init():
    GG.HEIGHTS = HEIGHTS_EXT


def screen(sp, seed, n=N_SCREEN):
    s = S.screen_lean(sp, seed, cut=False); G0 = S.com_all(sp)
    r = dict(up=s['up'], climb=s['climb'], turn=s['turn'], mass=sp['mass'], length=sp['length'], width=sp['width'],
             height=sp['height'], belly=sp['belly'], com_x=float(G0[0]), com_z=float(G0[2]), tail=bool(sp.get('limb')),
             wheels=len(sp['wheels']), tip_static=H.tip_static(sp), grown=sp.get('grown', 0), faired=bool(sp.get('plate_merged')),
             top=float(max(np.asarray(h)[:, 2].max() for h in sp['hulls'][:len(sp['hulls']) - sp.get('head_n', 0)])),
             elbow=bool(sp.get('limb') and sp['limb'].get('L2')),
             rear_up=bool(sp.get('limb') and sp['limb'].get('rear_up')), flip=bool(sp.get('flip')))   # top: the body's, without the tail or head
    if sp.get('head'):                                                    # the 250 mm run: the head on top, the body's print
        r.update(head=sp['head'], print_size=K.body_print_size(sp), head_top=float(max(np.asarray(h)[:, 2].max() for h in K.head_hulls(sp))))
    poses = (None,) + (K.BRACE if sp.get('limb') else ())
    for down, g in ((False, 'h_up'), (True, 'h_down')):
        by = {th: H.ladder(sp, H.GRIP, down, n, seed, th)[0] for th in poses}
        r[g] = max(by.values()); r[g + '_stowed'] = by[None]
    r['crest'] = C.ladder(sp, C.GRIP, n, seed)[0]
    if TOW:
        import tow as T
        tw = {mu: T.ladder(sp, mu, n, seed)[0] for mu in GG.BAND}
        r['tow'] = min(tw.values()); r['tow_by_mu'] = {str(m): v for m, v in tw.items()}
    else:
        pu = {mu: P.ladder(sp, mu, n, seed)[0] for mu in GG.BAND}
        r['push'] = min(pu.values()); r['push_by_mu'] = {str(m): v for m, v in pu.items()}
    if ROUGH:
        import rough as RG
        r['rough'] = RG.ladder(sp, RG.GRIP, n, seed)[0]
    return r


def job(a):
    tag, z, seed, n = a
    t0 = time.time(); q = q_of(z)
    try:
        why = []; sp = build(q, why)
        r = None if sp is None else dict(screen(sp, seed, n), **({'print_g': sp['print_g']} if REAL else {}))
        if sp is None and REAL:                                           # why the real build refused it
            r = dict(built=False, why=why or ['not built'])
        elif sp is None and STRICT:                                       # why strict refused it
            loose = K.make(q); r = dict(built=False, why=K.problems(q, loose) if loose is not None else ['not built'])
    except Exception as e:                                                # one bad design must not stop the run
        return dict(tag=tag, z=list(map(float, z)), seed=seed, err=f'{type(e).__name__}: {e}'[:300])
    return dict(tag=tag, z=list(map(float, z)), seed=seed, q={k: q[k] for k in KEYS}, s=round(time.time() - t0, 1), **(r or dict(built=False)))


# ---------- scoring ----------
def val(r, g):
    """a gauge's reading, larger better; None when the design wasn't built or can't spin"""
    if r.get('built') is False or 'err' in r:
        return None
    v = r.get(g)
    return None if v is None else (-v if g == 'turn' else float(v))


def ranks(rows):
    """each design's percentile rank on each gauge among all built designs (0 worst, 1 best; ties share the mean), and
    the all-rounder rank: the worst of them, weighted (weights.allround)"""
    ok = [r for r in rows if val(r, 'up') is not None]
    R = {}
    for g, _ in GAUGES:
        v = np.array([val(r, g) if val(r, g) is not None else -1e9 for r in ok])
        order = v.argsort(kind='stable'); rk = np.empty(len(v)); rk[order] = np.arange(len(v))
        for u in np.unique(v):                                            # ties share their mean rank
            m = v == u; rk[m] = rk[m].mean()
        R[g] = rk / max(1, len(v) - 1)
    for i, r in enumerate(ok):
        r['rank'] = {g: float(R[g][i]) for g, _ in GAUGES}; r['rank']['all'] = W.allround(r['rank'], COUNT)
    return ok


def score(r, stream):
    if stream in LOW_STREAMS:
        return low_score(r, stream)
    if 'rank' not in r:
        return -1e18
    if stream == 'all':
        return r['rank']['all']
    if stream == 'low':                                                   # the all-rounder, a body under LOW_TOP first
        return r['rank']['all'] - (0.0 if r.get('top', 1e9) <= LOW_TOP else 1.0)
    v = val(r, stream)
    return -1e18 if v is None else v + 1e-3 * r['rank']['all']          # ties (the ladder tops) go to the better all-rounder


def low_score(r, stream):
    """a low step-and-turn stream's score (mm): step - w x turn, or for turn450 the step with the turn inside TURN_CAP;
    a miss (upright under UP_MIN, the body over LOW_TOP, the circle over TURN_CAP for turn450) costs by how far, so the
    stream steers back toward the bounds"""
    if val(r, 'up') is None or r.get('climb') is None:
        return -1e18
    turn = r['turn'] if r.get('turn') is not None else 3000.0
    miss = 2000.0 * max(0.0, UP_MIN - r['up']) + 20.0 * max(0.0, r.get('top', 1e3) - LOW_TOP)
    w = LOW_STREAMS[stream]
    if w is None:
        return r['climb'] - miss - 2.0 * max(0.0, turn - TURN_CAP)
    return r['climb'] - w * turn - miss


def feasible(r):
    """inside the low streams' bounds: upright, low, and spinning"""
    return val(r, 'up') is not None and r['up'] >= UP_MIN and r.get('top', 1e3) <= LOW_TOP and r.get('turn') is not None


def front(rows):
    """the designs no other beats on every gauge that counts at once (each at least as good, one better)"""
    ok = [r for r in rows if all(val(r, g) is not None for g in COUNT)]
    V = np.array([[val(r, g) for g in COUNT] for r in ok])
    keep = [i for i in range(len(ok)) if not np.any(np.all(V >= V[i], axis=1) & np.any(V > V[i], axis=1))]
    return [ok[i] for i in keep]


# ---------- the run ----------
def load():
    return [json.loads(l) for l in open(SCREENS)] if os.path.isfile(SCREENS) else []


def run_jobs(pool, J, rows, fh, label):
    t0 = time.time(); n = 0
    for r in pool.imap_unordered(job, J, chunksize=1):
        rows.append(r); fh.write(json.dumps(r, default=float) + '\n'); fh.flush(); n += 1
        if n % 60 == 0 or n == len(J):
            print(f'{label}: {n}/{len(J)} screened, {time.time() - t0:.0f} s', flush=True)
    return time.time() - t0


def best_line(rows):
    ok = ranks(rows); out = []
    if LOW:                                                               # each stream's best inside the bounds
        for st in STREAMS:
            f = [r for r in ok if feasible(r)]; b = max(f, key=lambda r: score(r, st)) if f else None
            out.append(f"{st} {'-' if b is None else '%d mm/%.0f mm/%.2f' % (b['climb'], b['turn'], b['up'])}")
        return '  '.join(out) + '  (step/turn/upright, low and upright)'
    for st in STREAMS:
        b = max(ok, key=lambda r: score(r, st))
        out.append(f"{st} {'%.2f' % b['rank']['all'] if st == 'all' else ('%.2f/%.0fmm' % (b['rank']['all'], b.get('top', 0)) if st == 'low' else (b.get(st) if st != 'up' else round(b['up'], 2)))}")
    return '  '.join(out)


def run():
    os.makedirs(OUT, exist_ok=True); stamp.check(SCREENS); rows = load(); t_start = time.time()
    seeds = [json.loads(l) for l in open(SEED_FROM)] if SEED_FROM else []   # the pool's start (LOW), never a champion here
    done = {r['tag'] for r in rows}
    with open(SCREENS, 'a') as fh, Pool(WORKERS, initializer=_init) as pool:
        if N_B:
            from scipy.stats import qmc
            Z0 = qmc.Sobol(len(KEYS), scramble=True, seed=53).random_base2(int(math.log2(N_B)))
            J = [(f'B{i}', z, 40000, N_SCREEN) for i, z in enumerate(Z0) if f'B{i}' not in done]
            if J:
                run_jobs(pool, J, rows, fh, 'B')
        print(f'B done: {len(rows)} screened, {sum(val(r, "up") is not None for r in rows)} built, {len(seeds)} seeds; best: {best_line(rows + seeds)}', flush=True)
        rng = np.random.default_rng(59); state = {}
        rnd = 1 + max([int(r['tag'].split('|')[1]) for r in rows if r['tag'].startswith('C|')] or [0])
        last = None
        while True:
            now = datetime.datetime.now()
            if last and now + datetime.timedelta(seconds=1.1 * last) > DEADLINE:
                print(f'round {rnd}: would end after {DEADLINE:%H:%M}; refinement stops', flush=True); break
            if now > DEADLINE:
                break
            ok = ranks(rows + seeds); J = []
            for st in STREAMS:
                el = sorted(ok, key=lambda r: -score(r, st))[:ELITE]; E = np.array([r['z'] for r in el])
                if st not in state:
                    state[st] = [E.mean(0), np.maximum(E.std(0), 0.05)]
                else:                                                     # as search.cem
                    mu, sd = state[st]; state[st] = [0.6 * E.mean(0) + 0.4 * mu, np.maximum(0.6 * E.std(0) + 0.4 * sd * 0.8, 0.02)]
                mu, sd = state[st]; Z = np.clip(mu + sd * rng.normal(size=(POP, len(KEYS))), 0.0, 1.0)
                J += [(f'C|{rnd}|{st}', z, 50000 + rnd, N_SCREEN) for z in Z]
            last = run_jobs(pool, J, rows, fh, f'round {rnd}')
            print(f'round {rnd} done ({last:.0f} s, {len(rows)} screened, {(time.time() - t_start) / 3600:.2f} h); best: {best_line(rows)}', flush=True)
            rnd += 1
    summarise(rows)
    finals()


def summarise(rows):
    ok = ranks(rows); F = front(ok)
    champs = {st: max(ok, key=lambda r: score(r, st)) for st in STREAMS}
    json.dump(dict(n=len(rows), built=len(ok), front_n=len(F), keys=KEYS, space=SPACE, held=list(HELD_K), heights=HEIGHTS_EXT,
                   champions={st: r for st, r in champs.items()}, front=sorted(F, key=lambda r: -r['rank']['all'])),
              open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, default=float)
    print(f'{len(rows)} screened, {len(ok)} built; the seven-way front holds {len(F)}', flush=True)
    for st, r in champs.items():
        print(f"  best {st:6s}: up {r['up']:.2f} step {r['climb']} turn {r['turn'] and round(r['turn'])} hills {r['h_up']}/{r['h_down']} "
              f"crest {r['crest']} {G7} {r[G7]}{(' rough ' + str(r['rough'])) if ROUGH else ''} | all-rank {r['rank']['all']:.2f} | tail {r['tail']} wheels {r['wheels']} {r['mass']:.0f} g", flush=True)


# ---------- the finals ----------
def _finit(sp):
    import card
    GG.HEIGHTS = HEIGHTS_EXT; card._init(sp)


def finals(n_front=4):
    """each stream's best and the n_front best all-rounders on the front (not already picked), T3 and the box, read on
    the full gauges (card.py's reads; G1-G3 at 200 falls and 20 tries, G2's ladder to 300 mm)"""
    import card
    rows = load(); ok = ranks(rows); F = sorted(front(ok), key=lambda r: -r['rank']['all'])
    pick = {}
    for st in STREAMS:
        r = max(ok, key=lambda r: score(r, st)); pick.setdefault(r['tag'] + str(r['z'][:3]), (f'best {st}', r))
    for r in F:
        if sum(1 for n, _ in pick.values() if n.startswith('front')) >= n_front:
            break
        pick.setdefault(r['tag'] + str(r['z'][:3]), (f'front {sum(1 for n, _ in pick.values() if n.startswith("front")) + 1}', r))
    names, specs = [], []
    for nm, r in pick.values():
        sp = build(q_of(r['z'])); sp = dict(sp, name=nm); names.append(nm); specs.append(sp)
    main, _ = GG.roster(True); specs += [dict(t3_ref(), name='T3'), main[0]]; names += ['T3', 'Box']
    GG.HEIGHTS = HEIGHTS_EXT
    card.TOW = TOW; card.ROUGH = ROUGH; J = card.jobs(specs, set(names)); t0 = time.time()
    print(f'finals: {len(specs)} designs, {len(J)} jobs', flush=True)
    with Pool(WORKERS, initializer=_finit, initargs=(specs,)) as pool:
        R = pool.map(card.job, J, chunksize=1)
    out = []
    for i, sp in enumerate(specs):
        g = GG.collect([x for x in R if x[0][0] in ('fall', 'climb', 'turn')], i, card.N_TRY); w = g['worst']
        r = card.row(R, i, sp)
        src = next((rr for nm, rr in pick.values() if nm == sp['name']), None)
        out.append(dict(name=sp['name'], up=w['upright'], climb=w['climb'], turn=w['turn'], h_up=r['up'], h_down=r['down'],
                        hill_pose=[r['up_pose'], r['down_pose']], h_up_stowed=r['up_stowed'], h_down_stowed=r['down_stowed'],
                        crest=r['crest'], push=r['push'], push_by_mu=r['push_by_mu'], **({'tow': r['tow'], 'tow_by_mu': r['tow_by_mu']} if TOW else {}), **({'rough': r['rough'], 'rough_seen': r['rough_seen']} if ROUGH else {}), by_mu=g['by_mu'], tip_static=r['tip_static'],
                        mass=sp['mass'], length=sp['length'], width=sp['width'], height=sp['height'], belly=sp['belly'],
                        tail=bool(sp.get('limb')), wheels=len(sp['wheels']), notes=sp['notes'],
                        q=src and src['q'], z=src and src['z'], screen=src and {k: src.get(k) for k, _ in GAUGES}))
        print(f"{sp['name']:12s} up {w['upright']:.3f} step {w['climb']} turn {w['turn'] and round(w['turn'])} hills {r['up']}/{r['down']} "
              f"crest {r['crest']} push {r['push']}{(' tow ' + str(r['tow'])) if TOW else ''}{(' rough ' + str(r['rough'])) if ROUGH else ''} | {sp['mass']:.0f} g, tail {bool(sp.get('limb'))}, {len(sp['wheels'])} wheels", flush=True)
    json.dump(dict(wall_s=round(time.time() - t0), heights=HEIGHTS_EXT, finals=out), open(os.path.join(OUT, 'finals.json'), 'w'), indent=1, default=float)


def smoke():
    """two designs (T3's point and the centre of the space), two tries a rung, in the pool: the run works end to end"""
    zT = np.array([(K.T3[k] - lo) / (hi - lo) if k in K.T3 else 1.0 for k, lo, hi in SPACE])
    J = [('smoke|T3', np.clip(zT, 0, 1), 1, 2), ('smoke|mid', np.full(len(KEYS), 0.5), 1, 2)]
    t0 = time.time()
    with Pool(2, initializer=_init) as pool:
        for r in pool.imap_unordered(job, J):
            print(json.dumps({k: r.get(k) for k in ('tag', 'up', 'climb', 'turn', 'h_up', 'h_down', 'crest', G7, 'rough', 'tail', 'wheels', 'mass', 's', 'err', 'built')}, default=float), flush=True)
    print(f'{time.time() - t0:.0f} s; {len(KEYS)} knobs: {KEYS}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    {'smoke': smoke, 'run': run, 'finals': finals}.get(cmd, lambda: print(__doc__))()
