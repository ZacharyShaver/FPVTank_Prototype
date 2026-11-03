"""An obstacle course (2026-11-02), and the weight vector that describes it. Zach, on the weights: "it gives us a way to
tell the simulator what you want as a result ... it can be set for larger and more complicated tests. you can score a
weight vector for how well it goes say around a obstacle course. multiple factors and their interplay needs a
descriptor".

The course runs along +X, one obstacle after another, each made of a gauge's own terrain: rocks (rough.field, at most
ROCK mm tall, on the terrain grip), the crest's ridge (crest.ridge, CREST degrees a side, terrain grip), a step STEP mm
up onto a plateau (the step's rounded edge), and on the plateau a dead-end corridor WIDTH mm between its walls. The
robot drives it at V, steering for the course's centre line, the step's reflex (gauges.Reflex) on a stall; where the
corridor's end leaves a square WIDTH wide it spins in place (as G3) until it faces back, and drives out. At the step
(REVERSE, 2026-11-02 evening): stalled nose first for GIVE_UP s, it backs off, turns round and reverses up (the rear-up
reflex if it has one, as G2 tail first), then turns to face forward on top. Zach, after the first run: "backwards is
fine ... knowing when to turn is something we need to build ... lets allow it". G2 counts the better direction, and the
first run (out/course/nose_first/: nose first only, the corridor 0.5 m past the step) stopped 35 designs that climb only
tail first. This rule stands in for a learned one. The floor and
the plateau are at x1. Each try has its own rocks and start (square on +-10 degrees), from (seed, try) only, so every
design meets the same courses. A try's score is the share of the course's path it covered (the turn counts TURN_M); a
design's is the mean over N_TRY tries.

The descriptor: weights.fit finds the weight vector whose all-rounder (the weighted worst rank of the eight gauges) ranks
designs as the course does. The designed one comes from the course's own numbers: each obstacle's weight 1 / (1 - t),
t the share of designs whose gauge reading falls short of it (the weighted worst rank then passes exactly the designs
that clear every obstacle); a gauge with nothing on the course, 0.

    python gauges/course.py check   # the controls (exits 1 on a failure)
    python gauges/course.py grip    # just the tyres' grip on the rocks and the ridge, and its control
    python gauges/course.py run     # the course on a sample of the tow run's screens -> gauges/out/course/runs.jsonl
    python gauges/course.py fit     # its descriptor, fitted and designed -> gauges/out/course/fit.json, descriptor.png
"""
import os, sys, json, math, time
os.environ.setdefault('SCORPION_CAP', 'capability_tow')                  # the designs are the tow run's, built as it built them
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config
import gauges as GG, robots as RB, crest as C, rough as RG, weights as W

OUT = os.path.join(config.GAUGES_OUT, 'course')
COURSE = dict(rock=40, crest=20, step=50, width=750)  # mm, degrees a side, mm, mm: about each gauge's median (tow run)
V, RAMP, LOOK, TURN_M = 0.3, 0.5, 0.6, 0.5            # m/s; s; m the steering looks ahead; m of path the turn counts
OVER, STUCK_MM, STUCK_S, T_MAX = 85.0, 20.0, 4.0, 90.0   # degrees; mm of progress in s; s
REVERSE, GIVE_UP, GAP = True, 3.0, 1.0                # reverse up the step; s stalled before it does; m of plateau before
                                                      # the corridor, room to turn on top (the nose-first run: False, -, 0.5)
GRIP = RG.GRIP                                        # the rocks' and the ridge's (the terrain gauges')
N_TRY, SEED, N_SAMPLE = 8, 7, 320
GAUGES = ('up', 'climb', 'turn', 'h_up', 'h_down', 'crest', 'tow', 'rough')
SECTIONS = ('rocks', 'crest', 'step', 'corridor', 'turn', 'back', 'done')


def layout(cs):
    """the course's places along X (m): the rock field and its rocks' zone, the ridge's feet, the step's face, the
    corridor's mouth and end, where the turn starts (the wheels' centre) and the finish line"""
    far = C.ridge(cs['crest'] or 20, 2.1)[1]; xs = far + 0.7; w = cs['width'] * 1e-3; c0 = xs + GAP; end = c0 + 0.4 + w
    return dict(fx=(-0.3, 1.9), fy=0.6, zone=(0.1, 1.5), ridge=2.1, far=far, step=xs, mouth=c0, end=end, w=w,
                turn_x=end - w / 2, finish_x=c0 - 0.1, plateau=(xs, end + 0.6))


TERRAIN = ('rocks', 'plank+1', 'plank-1', 'peak')       # the geoms on GRIP (rough.Rig's and crest.ridge's names)


class Rig(GG.Sim):
    """gauges.Sim on the course cs (COURSE's keys; rock 0, crest None, step 0 leave that obstacle out).

    The rocks and the ridge meet the robot as on G8 and G6, where the whole sim runs at GRIP: the terrain at the floor's
    friction x GRIP, and the tyres, tail and flippers each at their own x GRIP, through explicit contact pairs. A
    tyre's contact priority makes its own friction win over any terrain's, so until 2026-11-03 (pairs=False, the
    control) the tyres met the rocks and the ridge at x1: 0.9, not G8's 2.25"""
    def __init__(self, sp, cs=COURSE, mu=1.0, pairs=True):
        super().__init__(sp, mu)
        self.cs, self.L = cs, layout(cs); L = self.L; h = cs['step'] * 1e-3; r = RB.EDGE_R * 1e-3
        tf = '%.4f 0.005 0.0005' % (RB.FRICTION['floor'] * GRIP if pairs else RB.FRICTION['tyre'] * GRIP)   # the terrain
        self.nx = int(round((L['fx'][1] - L['fx'][0]) / RG.CELL)) + 1; self.ny = int(round(2 * L['fy'] / RG.CELL)) + 1
        self.top = max(cs['rock'], 1) * 1e-3
        def extra(f, ca):
            s = ''
            if cs['rock']:
                s += (f'<geom name="rocks" type="hfield" hfield="rocks" pos="{(L["fx"][0] + L["fx"][1]) / 2:.4f} 0 -0.0005" '
                      f'friction="{tf}"{ca}/>')
            if cs['crest']:
                s += C.ridge(cs['crest'], L['ridge'])[0](dict(floor=tf), ca)
            b = 0.0
            if h:                                                         # the plateau, its front edge rounded (robots.xml's step)
                x0, x1 = L['plateau']; b = h
                s += (f'<geom name="plateau" type="box" size="{(x1 - x0 - r) / 2:.5f} 1 {h / 2:.5f}" pos="{(x0 + r + x1) / 2:.5f} 0 {h / 2:.5f}" '
                      f'friction="{f["floor"]}"{ca}/>'
                      f'<geom name="edge" type="capsule" fromto="{x0 + r:.5f} -1 {h - r:.5f} {x0 + r:.5f} 1 {h - r:.5f}" size="{r:.5f}" '
                      f'friction="{f["floor"]}"{ca}/>')
            c0, e, hw = L['mouth'], L['end'], L['w'] / 2                  # the corridor's walls, standing on the plateau
            for y in (-1, 1):
                s += (f'<geom name="wall{y:+d}" type="box" size="{(e - c0) / 2:.4f} 0.025 0.15" pos="{(c0 + e) / 2:.4f} {y * (hw + 0.025):.4f} {b + 0.15:.4f}" '
                      f'friction="{f["floor"]}"{ca}/>')
            return s + (f'<geom name="wall_end" type="box" size="0.025 {hw + 0.05:.4f} 0.15" pos="{e + 0.025:.4f} 0 {b + 0.15:.4f}" '
                        f'friction="{f["floor"]}"{ca}/>')
        x = RB.xml(sp, mu, extra=extra)
        if cs['rock']:
            x = x.replace('<asset>', f'<asset><hfield name="rocks" nrow="{self.ny}" ncol="{self.nx}" '
                          f'size="{(L["fx"][1] - L["fx"][0]) / 2:.4f} {L["fy"]:.4f} {self.top:.5f} 0.01"/>', 1)
        self.m = self.mj.MjModel.from_xml_string(x); self.d = self.mj.MjData(self.m)   # the same bodies, joints and actuators
        if pairs:
            names = [self.m.geom(i).name for i in range(self.m.ngeom)]; ter = [g for g in TERRAIN if g in names]
            grip = {n: RB.FRICTION['tyre'] * GRIP * (sp.get('tyre_mu', 1.0) if n.startswith('tyre') else 1.0)
                    for n in names if n.startswith(('tyre', 'tail_', 'flip'))}
            pr = ''.join(f'<pair geom1="{g}" geom2="{n}" condim="3" friction="{v:.4f} {v:.4f} 0.005 0.0005 0.0005"/>'
                         for g in ter for n, v in grip.items())
            if pr:
                x = x[:x.rindex('</mujoco>')] + f'<contact>{pr}</contact></mujoco>'
                self.m = self.mj.MjModel.from_xml_string(x); self.d = self.mj.MjData(self.m)
        self.wc = np.mean([[x, y, 0.0] for x, y in sp['wheels']], 0) * 1e-3
        self.r_body = float(np.linalg.norm(self.E[:, :2] - self.wc[:2], axis=1).max())    # m from the wheels' centre: the body,
        self.r_wheel = float(np.linalg.norm(np.array(sp['wheels']) * 1e-3 - self.wc[:2], axis=1).max()) + sp['R'] * 1e-3 + 0.03   # a tyre

    def ground(self, rng):
        """this try's rocks, from rng (rough.field over the course's rock field)"""
        if self.cs['rock']:
            L = self.L; Z = RG.field(self.cs['rock'], rng, L['fx'], L['fy'], L['zone'])
            self.m.hfield_data[:] = np.clip(Z / self.top, 0.0, 1.0).ravel()

    def centre(self):
        """the wheels' centre (world, m)"""
        return self.d.xpos[self.rid] + self.rot() @ self.wc


def course_try(sim, rng):
    """one run: (outcome 'ok', 'over' or 'stuck'; the section it ended in; the share of the path covered; seconds).
    Phases: out, then at the step (REVERSE, once) backoff, spin1, rev (reversing up), spin2 and out again; turn at the
    dead end, back. Stuck: under STUCK_MM of the phase's own progress in STUCK_S (along the path; a spin's angle as
    TURN_M per half turn)"""
    sp, d, L = sim.sp, sim.d, sim.L; R = sp['R'] * 1e-3; h = sim.cs['step']
    yaw0 = math.radians(rng.uniform(-10, 10)); sim.place(GG.yaw_quat(yaw0), 0.0005, x=-GG.lead(sp, False) * 1e-3 - 0.05)
    u0 = min(V / (sim.w0 * R), 1.0); n_stuck, n_give = int(STUCK_S * 1000 / GG.TICK), int(GIVE_UP * 1000 / GG.TICK)
    x0 = sim.centre()[0]; s_out = L['turn_x'] - x0; S = s_out + TURN_M + (L['turn_x'] - L['finish_x'])
    st = dict(phase='out', t=0.0, prev=yaw0, turned=0.0, hist=[], tried=False, best=0.0, ru=None)
    st['rf'] = GG.Reflex(sim) if sim.limb or sim.flip else None; sim.reversed = False   # whether it turned to reverse up

    def where(x):
        ph = st['phase']
        if ph in ('backoff', 'spin1', 'rev', 'spin2'):
            return 'step'
        if ph != 'out':
            return ph
        return 'rocks' if x < L['zone'][1] + 0.2 else 'crest' if x < L['far'] + 0.15 else 'step' if x < L['step'] + 0.25 else 'corridor'

    def start(ph, t, yaw):
        st.update(phase=ph, t=t, prev=yaw, turned=0.0, hist=[])
        if ph in ('backoff', 'spin1', 'spin2', 'turn'):                   # the tail and flippers stowed for a manoeuvre
            if sim.limb:
                sim.limb_goal(0.0, sim.stow[1])
            if sim.flip:
                sim.flip_goal(sim.fstow)
        if ph == 'out':
            st['rf'] = GG.Reflex(sim) if sim.limb or sim.flip else None
        if ph == 'rev':
            st['ru'] = GG.RearUp(sim, h, L['step']) if sim.limb and sim.limb.get('rear_up') else None

    def steer(path, u, rev=False):
        """hold the course's centre line travelling along path (radians), facing that way, or facing back when rev"""
        p = sim.centre(); Rm = sim.rot(); face = path + (math.pi if rev else 0.0)
        e = (math.atan2(Rm[1, 0], Rm[0, 0]) - face - math.atan2(-math.cos(path) * p[1], LOOK) + math.pi) % (2 * math.pi) - math.pi
        cs = u0 * max(-0.5, min(0.5, 2.0 * e)); sim.drive(u + cs, u - cs)

    for k in range(int(T_MAX * 1000 / GG.TICK)):
        t = k * GG.TICK / 1000; Rm = sim.rot(); p = sim.centre(); yaw = math.atan2(Rm[1, 0], Rm[0, 0]); ph = st['phase']
        if math.degrees(math.acos(max(-1.0, min(1.0, Rm[2, 2])))) > OVER:
            return 'over', where(p[0]), st['best'] / S, t
        hs = st['hist']
        if ph == 'out' and p[0] >= L['turn_x']:                          # the square at the end: turn round
            start('turn', t, yaw)
        elif (ph == 'out' and REVERSE and h and not st['tried'] and where(p[0]) == 'step' and len(hs) > n_give
              and hs[-1] - hs[-1 - n_give] < STUCK_MM * 1e-3):            # stalled nose first at the step: back off, turn round
            st['tried'] = sim.reversed = True; start('backoff', t, yaw)
        elif ph == 'backoff' and p[0] <= L['step'] - sim.r_body - 0.05:
            start('spin1', t, yaw)
        elif ph == 'rev' and p[0] >= L['step'] + sim.r_wheel and GG.classify(Rm) == 'upright':
            start('spin2', t, yaw)
        ph = st['phase']
        if ph in ('turn', 'spin1', 'spin2'):
            st['turned'] += (yaw - st['prev'] + math.pi) % (2 * math.pi) - math.pi; st['prev'] = yaw
            if st['turned'] >= math.pi - math.radians(10):
                start(dict(turn='back', spin1='rev', spin2='out')[ph], t, yaw); ph = st['phase']
        ramp = min(1.0, (t - st['t']) / RAMP)
        if ph == 'out':
            s = a = p[0] - x0
            if st['rf'] is not None:
                st['rf'].tick(t)
            steer(0.0, u0 * ramp)
        elif ph == 'backoff':
            s, a = p[0] - x0, -p[0]; steer(math.pi, -u0 * ramp, rev=True)
        elif ph == 'rev':
            s, a = p[0] - x0, p[0]
            if st['ru'] is not None:
                st['ru'].tick(t)
            steer(0.0, -u0 * ramp, rev=True)
        elif ph in ('turn', 'spin1', 'spin2'):
            a = TURN_M * max(0.0, st['turned']) / math.pi
            s = s_out + a if ph == 'turn' else p[0] - x0
            sim.drive(-GG.TURN_U, GG.TURN_U)
        else:
            s = a = s_out + TURN_M + (L['turn_x'] - p[0])
            if p[0] <= L['finish_x']:
                return ('ok' if GG.classify(Rm) == 'upright' else 'over'), 'done', 1.0, t
            steer(math.pi, u0 * ramp)
        st['best'] = max(st['best'], s); hs = st['hist']; hs.append(max(a, hs[-1]) if hs else a)   # the phase's best so far
        if len(hs) > n_stuck and hs[-1] - hs[-1 - n_stuck] < STUCK_MM * 1e-3:
            return 'stuck', where(p[0]), st['best'] / S, t
    return 'stuck', where(sim.centre()[0]), st['best'] / S, T_MAX


def tries(sp, n=N_TRY, seed=SEED, cs=COURSE):
    sim = Rig(sp, cs); out = []
    for k in range(n):
        g = np.random.default_rng([seed, k]); sim.ground(g); out.append(course_try(sim, g))
    return out


def score(tr):
    return float(np.mean([p for _, _, p, _ in tr]))


# ---------- the sample ----------
def _job(r):
    import capability as CA, rough as RG_
    t0 = time.time()
    try:
        sp = CA.build(CA.q_of(r['z']))
        if sp is None:
            return dict(tag=r['tag'], z=r['z'], err='not built')
        rough = r['rough'] if r.get('rough') is not None else RG_.ladder(sp, RG_.GRIP, 6, r['seed'])[0]; tr = tries(sp)
    except Exception as e:
        return dict(tag=r['tag'], z=r['z'], err=f'{type(e).__name__}: {e}'[:300])
    return dict(tag=r['tag'], z=r['z'], **{g: r.get(g) for g in GAUGES if g != 'rough'}, rough=rough, mass=r['mass'],
                tries=[[o, w, round(p, 4), round(t, 2)] for o, w, p, t in tr], score=score(tr),
                finish=sum(o == 'ok' for o, *_ in tr) / len(tr), s=round(time.time() - t0, 1))


def run():
    from multiprocessing import Pool
    os.makedirs(OUT, exist_ok=True)
    rows = [json.loads(l) for l in open(os.path.join(config.GAUGES_OUT, 'capability_tow', 'screens.jsonl'))]
    rows = [r for r in rows if r.get('built') is not False and 'err' not in r and r.get('up') is not None]
    pick = np.random.default_rng(SEED).choice(len(rows), N_SAMPLE, replace=False); J = [rows[i] for i in pick]
    p0 = os.path.join(OUT, 'nose_first', 'runs.jsonl')                   # G8 as the first run read it (same designs, seeds)
    if os.path.exists(p0):
        rg = {tuple(x['z']): x.get('rough') for x in map(json.loads, open(p0))}; J = [dict(r, rough=rg.get(tuple(r['z']))) for r in J]
    path = os.path.join(OUT, 'runs.jsonl'); done = set()                 # a design is its z (a stream's tag repeats each round)
    import capability, stamp                                             # (the workers' modules loaded, for the stamp)
    stamp.check(path)                                                    # only rows made by this code (2026-11-03: none was kept)
    if os.path.exists(path):
        done = {tuple(json.loads(l).get('z') or ()) for l in open(path)}
    J = [r for r in J if tuple(r['z']) not in done]; t0 = time.time()
    print(f'{len(J)} designs to run ({len(done)} on disk), course {COURSE}, {N_TRY} tries each', flush=True)
    with Pool(int(os.environ.get('SCORPION_WORKERS', 24))) as pool, open(path, 'a') as fh:
        for i, r in enumerate(pool.imap_unordered(_job, J)):
            fh.write(json.dumps(r) + '\n'); fh.flush()
            if i % 20 == 0:
                print(f'{i + 1}/{len(J)} {time.time() - t0:.0f} s  {r["tag"]}: {r.get("score", r.get("err"))}', flush=True)


# ---------- the descriptor ----------
def rank_matrix(rows):
    """each design's percentile rank on each gauge among the rows (capability.ranks' rule: turn smaller better, a
    design that can't spin worst, ties share the mean)"""
    from scipy.stats import rankdata
    M = np.zeros((len(rows), len(GAUGES)))
    for j, g in enumerate(GAUGES):
        v = np.array([(-r[g] if g == 'turn' else r[g]) if r.get(g) is not None else -1e9 for r in rows], float)
        M[:, j] = (rankdata(v) - 1) / max(1, len(v) - 1)
    return M


def short_of(rows, cs=COURSE):
    """each gauge's t: the share of rows whose reading falls short of the course's obstacle (None: not on the course)"""
    need = dict(rough=lambda r: r['rough'] < cs['rock'], crest=lambda r: r['crest'] < cs['crest'],
                climb=lambda r: r['climb'] < cs['step'], turn=lambda r: r['turn'] is None or r['turn'] > cs['width'])
    return {g: (float(np.mean([need[g](r) for r in rows])) if g in need else None) for g in GAUGES}


def designed(rows, cs=COURSE):
    t = short_of(rows, cs); w = np.array([0.0 if t[g] is None else 1.0 / max(1e-3, 1.0 - t[g]) for g in GAUGES])
    return w / w.max(), t


def fit():
    rows = [json.loads(l) for l in open(os.path.join(OUT, 'runs.jsonl'))]; rows = [r for r in rows if 'err' not in r]
    M = rank_matrix(rows); y = np.array([r['score'] for r in rows]); n = len(rows)
    wd, t = designed(rows); eq = np.ones(len(GAUGES))
    wf = W.fit(M, y); ws = W.fit(M, y, kind='sum')
    cv = {k: W.cv(M, y, **a) for k, a in (('fitted, worst', {}), ('fitted, sum', dict(kind='sum')))}
    cv['equal'] = W.cv(M, y, fixed=eq); cv['designed'] = W.cv(M, y, fixed=wd)
    cv['best one gauge'] = W.cv(M, y, kind='one')
    sh = np.random.default_rng(0).permutation(y); cv['control: course scores shuffled'] = W.cv(M, sh)
    sec = {s: sum(tr[1] == s for r in rows for tr in r['tries']) for s in SECTIONS}
    ob = {}                                                               # each obstacle: of the tries that got to it, the share
    for s, g, meets in (('rocks', 'rough', lambda r: r['rough'] >= COURSE['rock']),      # stopped there, by whether the gauge
                        ('crest', 'crest', lambda r: r['crest'] >= COURSE['crest']),     # says the design clears it: a perfect
                        ('step', 'climb', lambda r: r['climb'] >= COURSE['step']),       # gauge stops none it passes, all it fails
                        ('turn', 'turn', lambda r: r['turn'] is not None and r['turn'] <= COURSE['width'])):
        i = SECTIONS.index(s); got = [(meets(r), tr[1] == s) for r in rows for tr in r['tries'] if SECTIONS.index(tr[1]) >= i]
        ob[s] = {k: dict(tries=sum(m == v for m, _ in got), stopped=round(float(np.mean([st for m, st in got if m == v] or [np.nan])), 3))
                 for k, v in (('gauge clears it', True), ('gauge fails it', False))}
    res = dict(course=COURSE, n=n, tries=N_TRY, gauges=GAUGES, fitted=dict(zip(GAUGES, wf.round(3).tolist())),
               fitted_sum=dict(zip(GAUGES, ws.round(3).tolist())), designed=dict(zip(GAUGES, wd.round(3).tolist())),
               short=t, rho_all=dict(fitted=W.rho(W.allround_arr(M, wf), y), designed=W.rho(W.allround_arr(M, wd), y),
                                     equal=W.rho(W.allround_arr(M, eq), y)),
               cv=cv, ended=sec, by_obstacle=ob, finish=float(np.mean([r['finish'] for r in rows])),
               score_pct=np.percentile(y, [10, 25, 50, 75, 90]).round(3).tolist())
    json.dump(res, open(os.path.join(OUT, 'fit.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))
    return res, rows, M, y


def grip_check(sp):
    """sp's tyres meet the rocks and the ridge at G8's and G6's grip (the tyre's x GRIP); the control, the course
    without its contact pairs (as before 2026-11-03), at x1. The number of failures"""
    clear = dict(rock=0, crest=None, step=0, width=2000); want = RB.FRICTION['tyre'] * GRIP; bad = 0
    for what, cs in (('rocks', dict(clear, rock=COURSE['rock'])), ('ridge', dict(clear, crest=COURSE['crest']))):
        for pairs in (True, False):
            sim = Rig(sp, cs, pairs=pairs); sim.ground(np.random.default_rng([1, 0])); seen = {}
            sim.place(GG.yaw_quat(0.0), 0.0005, x=-0.1 if cs['rock'] else sim.L['ridge'] - 0.4)
            for _ in range(800):
                sim.drive(0.3, 0.3)
                for c in sim.d.contact[:sim.d.ncon]:
                    a, b = sim.m.geom(c.geom1).name, sim.m.geom(c.geom2).name
                    if (a in TERRAIN or b in TERRAIN) and (a.startswith('tyre') or b.startswith('tyre')):
                        f = round(float(c.friction[0]), 3); seen[f] = seen.get(f, 0) + 1
            ok = bool(seen) and all((abs(f - want) < 1e-3) == pairs for f in seen); bad += not ok
            print(('PASS ' if ok else 'FAIL ') + ('' if pairs else 'control (no pairs, as before 2026-11-03): ') +
                  f"the tyres on the {what} meet friction {sorted(seen)} ({sum(seen.values())} contacts; G8's and G6's {want:.2f})")
    return bad


def check(n=4):
    """the controls: the tyres meet the terrain at the terrain gauges' grip (grip_check); on the course with nothing on
    it (no rocks, ridge or step, the corridor 2 m wide) the box and T3 finish every try; each obstacle on its own, too
    big for the box, stops the box in that obstacle's section (each section binds, and is named right). Exits 1 on a
    failure"""
    import knobs as K
    bad = 0; bx = GG.roster(True)[0][0]; t3 = K.make(dict(K.T3, track=130.0), real=True)
    clear = dict(rock=0, crest=None, step=0, width=2000)
    bad += grip_check(t3)
    for nm, sp in (('Box', bx), ('T3', t3)):
        tr = tries(sp, n, 1, clear); ok = all(o == 'ok' for o, *_ in tr); bad += not ok
        print(('PASS ' if ok else 'FAIL ') + f'control: {nm} on the clear course finishes every try: {[(o, w, round(p, 2), round(t, 1)) for o, w, p, t in tr]}')
    dia = GG.turn(GG.Sim(bx), 1)[0]
    for sec, cs in (('rocks', dict(clear, rock=150)), ('crest', dict(clear, crest=60)), ('step', dict(clear, step=200)),
                    ('turn', dict(clear, width=round(max(bx['width'] + 60, 0.8 * dia))))):
        tr = tries(bx, n, 1, cs); ok = all(w == sec for _, w, _, _ in tr); bad += not ok
        print(('PASS ' if ok else 'FAIL ') + f'control: the box stops at {sec} ({cs}): {[(o, w, round(p, 2)) for o, w, p, _ in tr]}')
    if REVERSE:                                                           # the rule turns round only when stalled, and gets
        sim = Rig(t3, dict(clear, step=COURSE['step'])); r = [course_try(sim, np.random.default_rng([1, k])) + (sim.reversed,) for k in range(n)]
        ok = all(o == 'ok' and not rv for o, *_, rv in r); bad += not ok      # a tail-first climber up (the first run's #1)
        print(('PASS ' if ok else 'FAIL ') + f'control: T3 climbs the step nose first, never turning: {[(o, rv) for o, *_, rv in r]}')
        p1 = os.path.join(OUT, 'nose_first', 'runs.jsonl')
        if os.path.exists(p1):
            import capability as CA
            z = json.loads(open(p1).readlines()[1])['z']; sp1 = CA.build(CA.q_of(z))
            for rev in (False, True):
                globals()['REVERSE'] = rev; sim = Rig(sp1, dict(clear, step=COURSE['step']))
                r = [course_try(sim, np.random.default_rng([1, k])) for k in range(n)]
                want = 'ok' if rev else 'stuck'; ok = all(o == want for o, *_ in r); bad += not ok
                print(('PASS ' if ok else 'FAIL ') + f"{'' if rev else 'control: '}a design that climbs 50 mm only tail first, the step alone, "
                      f"reversing {'allowed' if rev else 'off'}: {[(o, w) for o, w, *_ in r]}")
            globals()['REVERSE'] = True
    tr = tries(t3, n, 1); print(f'T3 (real, track 130) on the course {COURSE}: score {score(tr):.2f}, {[(o, w, round(p, 2)) for o, w, p, _ in tr]}')
    tr = tries(bx, n, 1); print(f'Box on the course: score {score(tr):.2f}, {[(o, w, round(p, 2)) for o, w, p, _ in tr]}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    a = sys.argv[1:2]
    if a == ['check']:
        check()
    elif a == ['grip']:
        import knobs as K
        sys.exit(1 if grip_check(K.make(dict(K.T3, track=130.0), real=True)) else 0)
    elif a == ['run']:
        run()
    elif a == ['fit']:
        fit()
    else:
        print(__doc__)
