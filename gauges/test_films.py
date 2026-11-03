"""Every gauge filmed on the realistic run's top designs (Zach, 2026-11-02: "a page with videos of each test running
for our top models. this will help me evaluate each of our tests"). Each clip runs the gauge's own try function
(film.fall + gauges.right, gauges.climb_try, gauges.turn, hills.hill_try, crest.crest_try, push.push_try, tow.tow_try,
rough.rough_try)
at the design's reading and at the next rung up, at the friction that set the reading: a pass beside a fail. Only the
look is added: robots.xml gets film.py's colours, floor and lights (nothing that touches the physics), and every tick's
pose is logged. A hill is gravity tilted over a flat floor (hills.py), so its frames are turned by the slope.

    python gauges/test_films.py [--only T3] [--tests climb,turn] [--workers 6]  -> gauges/out/test_films/*.mp4, *.jpg, films.json
    python gauges/test_films.py page                                             -> gauges/out/test_films/index.html

The designs are capability_real's finalists (its finals.json), T3 at its real build (track 130) and the box. Tow is
new (tow.py) and not in that run: its reading here is a quick one, 6 tries a rung at x1. So is rough ground (G8, rough.py,
added 2026-11-02 evening): 6 tries a rung at its x2.5 grip.
"""
import os, sys, re, json, math, time, subprocess
import numpy as np
os.environ.setdefault('SCORPION_CAP', 'capability_real')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import capability as CP, gauges as GG, robots as RB, hills as H, crest as C, push as P, tow as T, rough as RG, film as F

OUT = os.path.join(CP.config.GAUGES_OUT, 'test_films')
PW, PH, FPS, SQ = 400, 300, 30, 640                     # a panel; a hill's frames render SQ square, turn, then crop
DESIGNS = (('T3', 'T3 (real build)'), ('best all', 'Best all-rounder'), ('front 1', 'Front 1'), ('best climb', 'Best climber'),
           ('best turn', 'Best turner'), ('best push', 'Best pusher'), ('best up', 'Most upright'), ('Box', 'Box (baseline)'))
TESTS = ('up', 'climb', 'turn', 'h_up', 'h_down', 'crest', 'push', 'tow', 'rough')
SEEDS = 16                                              # tries searched for a pass (or a fail) to show


# ---------- the look, and the log ----------
_xml = RB.xml


def _visual(*a, **k):
    x = _xml(*a, **k); sp = a[0] if a else k['sp']
    x = x.replace('<mujoco>', f'<mujoco><visual><global offwidth="{SQ * 2}" offheight="{SQ * 2}"/><quality shadowsize="2048"/></visual>', 1)
    x = x.replace('<asset>', '<asset><texture name="chk" type="2d" builtin="checker" rgb1=".78 .79 .76" rgb2=".72 .73 .70" width="256" height="256"/>'
                  '<material name="floor" texture="chk" texrepeat="16 16" reflectance="0"/>'
                  '<texture name="sky" type="skybox" builtin="gradient" rgb1=".96 .96 .94" rgb2=".82 .83 .80" width="64" height="64"/>', 1)
    x = x.replace('<worldbody>', '<worldbody><light directional="true" pos="0 0 3" dir="-.2 .4 -1" diffuse=".75 .75 .7" castshadow="false"/>'   # directional:
                  '<light directional="true" pos="0 0 3" dir=".5 -.3 -1" diffuse=".3 .3 .3" castshadow="false"/>', 1)                      # lit 2.5 m out (no shadows: their map speckles)
    x = x.replace('<geom type="plane"', '<geom type="plane" material="floor"', 1)
    x = x.replace('<geom type="box"', '<geom type="box" rgba=".55 .6 .7 1"').replace('<geom type="capsule" fromto="0.0', '<geom type="capsule" rgba=".55 .6 .7 1" fromto="0.0')
    x = x.replace('<geom type="mesh"', '<geom type="mesh" rgba=".83 .55 .2 .95"' if any(n.startswith('skin') for n in sp['notes']) else '<geom type="mesh" rgba=".62 .66 .7 1"')
    x = x.replace('<geom type="cylinder"', '<geom type="cylinder" rgba=".13 .13 .14 1"')
    x = x.replace('contype="2" conaffinity="0"', 'contype="2" conaffinity="0" rgba=".07 .55 .43 1"')
    x = x.replace('<geom name="box" type="box"', '<geom name="box" type="box" rgba=".86 .64 .3 1"')              # push's box
    x = re.sub(r'(<body name="sled"[^>]*><freejoint/><geom type="box" rgba=")[^"]*', r'\g<1>.86 .64 .3 1', x)      # tow's sled
    x = re.sub(r'(<geom name="(?:plank[+-]1|peak)"[^/]*?)(/>)', r'\1 rgba=".66 .6 .52 1"\2', x)                 # crest's ridge
    x = x.replace('<geom name="rocks"', '<geom name="rocks" rgba=".62 .55 .45 1"')                                   # rough's rocks
    return x


RB.xml = _visual
_drive = GG.Sim.drive


def _logged(self, uL, uR):
    _drive(self, uL, uR); self.__dict__.setdefault('log', []).append((self.d.time, self.d.qpos.copy()))


GG.Sim.drive = _logged


def fresh(sim):
    sim.log = []
    return sim


# ---------- frames ----------
def seg(scn, p0, p1, rgba, w):
    import mujoco
    if scn.ngeom >= scn.maxgeom:
        return
    g = scn.geoms[scn.ngeom]
    mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_CAPSULE, np.zeros(3), np.zeros(3), np.zeros(9), np.array(rgba, np.float32))
    mujoco.mjv_connector(g, mujoco.mjtGeom.mjGEOM_CAPSULE, w, np.array(p0, float), np.array(p1, float)); scn.ngeom += 1


def ring(scn, c, r, rgba, w=0.004, dashed=False, n=96):
    """a circle on the floor (turn_film.py's)"""
    for k in range(n):
        if dashed and k % 2:
            continue
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        seg(scn, (c[0] + r * math.cos(a0), c[1] + r * math.sin(a0), 0.002), (c[0] + r * math.cos(a1), c[1] + r * math.sin(a1), 0.002), rgba, w)



def render(sim, log, view, label, rot=0.0, hold=1.0, draw=None):
    """the logged poses at FPS, from view (follow: dist, az, el, dz; or fixed: lookat), each stamped with label(t)"""
    import mujoco
    from PIL import Image
    big = rot != 0.0; w, h = (SQ, SQ) if big else (PW, PH)
    r = mujoco.Renderer(sim.m, h, w, max_geom=20000); ts = np.array([t for t, _ in log]); t0 = ts[0]; out = []
    for t in np.arange(t0, ts[-1] + hold + 1e-9, 1.0 / FPS):
        i = min(int(np.searchsorted(ts, t)), len(log) - 1); sim.d.qpos[:] = log[i][1]; mujoco.mj_forward(sim.m, sim.d)
        cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        if 'lookat' in view:
            cam.lookat[:] = view['lookat']
        else:
            p = sim.d.xpos[sim.rid]; cam.lookat[:] = (p[0] + view.get('dx', 0.0), p[1], max(0.08, p[2] * 0.6) + view.get('dz', 0.0))
        cam.distance, cam.azimuth, cam.elevation = view['dist'], view['az'], view['el']
        r.update_scene(sim.d, cam)
        if draw:
            draw(r.scene, i)
        img = r.render().copy()
        if big:                                                           # the slope: uphill (+X, screen right) turned up
            im = Image.fromarray(img).rotate(rot, resample=Image.BICUBIC, fillcolor=(235, 235, 232))
            img = np.asarray(im.crop(((SQ - PW) // 2, (SQ - PH) // 2, (SQ + PW) // 2, (SQ + PH) // 2)))
        out.append(F.stamp(img, label(min(t, ts[-1]) - t0)))
    r.close()
    return out


def write(path, panels):
    """panels side by side; the shorter holds its last frame; mp4 (H.264) and a poster jpg"""
    n = max(len(p) for p in panels); W = PW * len(panels)
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{PH}', '-r', str(FPS), '-i', '-',
                           '-an', '-vcodec', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '25', '-preset', 'slow', '-movflags', '+faststart', path + '.mp4'],
                          stdin=subprocess.PIPE)
    poster = None
    for k in range(n):
        canvas = np.full((PH, W, 3), 245, np.uint8)
        for j, p in enumerate(panels):
            canvas[:, j * PW:(j + 1) * PW] = p[min(k, len(p) - 1)]
            if j:
                canvas[:, j * PW:j * PW + 2] = 255
        ff.stdin.write(canvas.tobytes())
        if k == int(n * 0.6):
            poster = canvas.copy()
    ff.stdin.close(); ff.wait()
    from PIL import Image
    Image.fromarray(poster).save(path + '.jpg', quality=82)
    return os.path.basename(path) + '.mp4', n / FPS


def search(make, want, n=SEEDS):
    """run make(seed) -> (outcome, sim) until want(outcome); the last one when none does"""
    last = None
    for s in range(n):
        o, sim = make(s); last = (o, sim, s)
        if want(o):
            return o, sim, s, True
    return last + (False,)


def pair(try_at, lo, hi, n=8):
    """a pass at rung lo in the better direction (nose first, then tail first, as the ladders try them), then a fail at
    rung hi in that same direction: [(rung, outcome, sim, seed, back, found)]; try_at(rung, back, seed) -> (outcome, sim)"""
    out, back = [], False
    if lo:
        hit = None
        for b in (False, True):
            for s in range(n):
                o, sim = try_at(lo, b, s)
                if o == 'ok':
                    hit = (lo, o, sim, s, b, True); break
            if hit:
                break
        out.append(hit or (lo, o, sim, s, False, False)); back = out[-1][4]
    if hi:
        hit = None
        for s in range(n):
            o, sim = try_at(hi, back, s)
            if o != 'ok':
                hit = (hi, o, sim, s, back, True); break
        out.append(hit or (hi, o, sim, s, back, False))
    return out


# ---------- the gauges ----------
SIDE = dict(dist=1.4, az=90.0, el=-8.0)
THREE = dict(dist=1.5, az=135.0, el=-22.0)


def worst_mu(r, key, low=True):
    bm = r.get('by_mu') or {}
    v = {float(m): (x.get(key) if isinstance(x, dict) else None) for m, x in bm.items()}
    v = {m: x for m, x in v.items() if x is not None}
    return (min(v, key=v.get) if low else max(v, key=v.get)) if v else 1.0


def g_up(sp, r, name):
    mu = worst_mu(r, 'upright'); out = []
    def make(s):
        sim = fresh(GG.Sim(sp, mu)); rest, end, tr, te = F.fall(sim, np.random.default_rng([31, s]))
        return (rest, end, tr, te), sim
    for want, what in ((lambda o: o[0] != 'upright' and o[1] == 'upright', 'righted'), (lambda o: o[1] != 'upright', 'stays down')):
        if not sp.get('limb') and what == 'righted':
            want = lambda o: o[0] == 'upright'
        o, sim, s, found = search(make, want, 60)
        rest, end, tr, te = o; log = list(sim.log); t0 = log[0][0]
        def lab(t, rest=rest, end=end, tr=tr - t0, te=te - t0, s=s):
            a = f'fall {s + 1}: ' + (f'landed {rest}' if t >= tr else 'falling')
            b = '' if t < tr else ('tail righting...' if t < te and rest != 'upright' else ('on its wheels: pass' if end == 'upright' else f'{end}: fail'))
            return [f'{name}: upright (G1), x{mu:g} grip', a, b]
        out.append(dict(panel=render(sim, log, THREE, lab), seed=s, outcome=end, rest=rest, found=found, mu=mu))
    return out, f"{r['up']:.0%} of 200 falls end upright (worst grip)"


def g_climb(sp, r, name, heights):
    mu = worst_mu(r, 'climb'); tries = r['by_mu'][str(mu) if str(mu) in r['by_mu'] else f'{mu}']['climb_tries'] if r.get('by_mu') else {}
    reading = r['climb']; lo = max((h for h in heights if h <= reading), default=None)
    hi = min((h for h in heights if h > reading), default=heights[-1])
    def passes(h, b):
        return tries.get(f'{h}|{b}', 0)
    back = (passes(lo, 1) > passes(lo, 0)) if lo else (passes(hi, 1) > passes(hi, 0))
    out = []
    for h, want in ((lo, True), (hi, False)):
        if h is None:
            continue
        def make(s, h=h):
            sim = fresh(GG.Sim(sp, mu, step=h)); ok = GG.climb_try(sim, h, back, np.random.default_rng([5, s]))
            for _ in range(int(0.6 * 1000 / GG.TICK)):                     # a moment after the gauge's success line
                sim.drive(None, None)
            return ok, sim
        ok, sim, s, found = search(make, lambda o, want=want: o == want)
        n = passes(h, int(back))
        lab = lambda t, h=h, ok=ok, n=n: [f'{name}: {h} mm step (G2), x{mu:g} grip, {"tail first" if back else "nose first"}',
                                          f'the gauge: {n}/20 passed this rung', 'on top: pass' if ok else 'not on top: fail']
        out.append(dict(panel=render(sim, list(sim.log), dict(dist=1.7, az=65.0, el=-20.0, dx=0.1, dz=0.05), lab), h=h, outcome='on top' if ok else 'fail', found=found, seed=s, n=n))
    return out, f"{reading} mm (pooled 90 % crossing, worst grip x{mu:g})"


def g_turn(sp, r, name):
    import mujoco
    mu = worst_mu(r, 'turn', low=False); sim = fresh(GG.Sim(sp, mu)); dia, t_ = GG.turn(sim, 1); log = list(sim.log)
    sim.d.qpos[:] = log[0][1]; mujoco.mj_forward(sim.m, sim.d)
    wc = np.mean([[x, y, 0.0] for x, y in sp['wheels']], 0) * 1e-3; c0 = (sim.d.xpos[sim.rid] + sim.rot() @ wc)[:2]
    rm = []
    for _, q in log:                                                      # the sweep so far, as gauges.turn measures it
        sim.d.qpos[:] = q; mujoco.mj_forward(sim.m, sim.d); R = sim.rot(); Pp = sim.d.xpos[sim.rid] + sim.E @ R.T
        rm.append(max(rm[-1] if rm else 0.0, float(np.linalg.norm(Pp[:, :2] - c0, axis=1).max())))
    def draw(scn, i):
        if dia:
            ring(scn, c0, dia / 2e3, (0.9, 0.45, 0.1, 1.0), dashed=True)
        ring(scn, c0, max(rm[i], 1e-3), (0.9, 0.45, 0.1, 1.0), w=0.006)
    lab = lambda t: [f'{name}: spin in place (G3), x{mu:g} grip', 'left wheels back, right forward, 60 %',
                     (f'180° in {t_:.2f} s: {dia:.0f} mm circle' if t >= t_ - 0.01 else f'{t:.2f} s') if dia else 'never got round: fail']
    top = render(sim, log, dict(lookat=(c0[0], c0[1], 0.0), dist=1.15, az=90.0, el=-89.9), lab, hold=1.5, draw=draw)
    three = render(sim, log, dict(lookat=(c0[0], c0[1], 0.05), dist=1.5, az=135.0, el=-28.0), lambda t: [], hold=1.5, draw=draw)
    return [dict(panel=top, outcome=dia), dict(panel=three)], (f'{dia:.0f} mm circle (worst grip x{mu:g})' if dia else 'never got round')


def g_hill(sp, r, name, down):
    key = 'h_down' if down else 'h_up'; reading = r[key]; th = (r.get('hill_pose') or [None, None])[int(down)]
    pose = '' if th is None or not sp.get('limb') else f', tail braced {th:g}°'
    def try_at(deg, back, s):
        sim = fresh(GG.Sim(sp, H.GRIP)); return H.hill_try(sim, deg, down, back, np.random.default_rng([61, deg, s, int(back)]), th), sim
    out = []
    for deg, o, sim, s, back, found in pair(try_at, reading, min(reading + 5, H.ANGLES[-1]) if reading < H.ANGLES[-1] else None):
        lab = lambda t, deg=deg, o=o, back=back: [f'{name}: {deg}° hill {"down" if down else "up"} ({"G5" if down else "G4"}){pose}',
                                                   f'grip x{H.GRIP:g}, {"tail first" if back else "nose first"}, 2.5 m at 0.5 m/s',
                                                   'got there on its wheels: pass' if o == 'ok' else f'{o}: fail']
        out.append(dict(panel=render(sim, list(sim.log), dict(dist=2.3, az=90.0, el=-7.0, dz=0.03), lab, rot=float(deg)), deg=deg, outcome=o, found=found, back=back))
    return out, f'{reading}° (5° rungs, grip x{H.GRIP:g})'


def g_crest(sp, r, name):
    reading = r['crest']; R = {}
    def try_at(deg, back, s):
        xml, far = R.setdefault(deg, C.ridge(deg))
        sim = fresh(GG.Sim(sp, C.GRIP, extra=xml)); return C.crest_try(sim, deg, back, np.random.default_rng([7, deg, s, int(back)]), far), sim
    out = []
    for deg, o, sim, s, back, found in pair(try_at, reading, reading + 5 if reading < C.ANGLES[-1] else None):
        lab = lambda t, deg=deg, o=o, back=back: [f'{name}: ridge of two {deg}° planks, 150 mm high (G6)',
                                                   f'grip x{C.GRIP:g}, {"tail first" if back else "nose first"}, 0.15 m/s',
                                                   'over on its wheels: pass' if o == 'ok' else f'{o}: fail']
        out.append(dict(panel=render(sim, list(sim.log), dict(dist=1.7, az=125.0, el=-22.0, dz=0.03), lab), deg=deg, outcome=o, found=found, back=back))
    return out, f'{reading}° planks (5° rungs, grip x{C.GRIP:g})'


def g_push(sp, r, name):
    bm = r.get('push_by_mu') or {'1.0': r['push']}; mu = float(min(bm, key=bm.get)); reading = r['push']
    def try_at(kg, back, s):
        sim = fresh(GG.Sim(sp, mu, extra=P.box(kg))); return P.push_try(sim, back, np.random.default_rng([11, int(kg * 10), s, int(back)])), sim
    out = []
    for kg, o, sim, s, back, found in pair(try_at, reading, P.nxt(reading)):
        lab = lambda t, kg=kg, o=o, back=back: [f'{name}: push a {kg:g} kg box 0.5 m (G7 push)', f'x{mu:g} grip, {"tail first" if back else "nose first"}, 0.3 m/s',
                                                 'pushed it 0.5 m: pass' if o == 'ok' else f'{o}: fail']
        out.append(dict(panel=render(sim, list(sim.log), dict(dist=1.5, az=120.0, el=-18.0, dx=0.15), lab), kg=kg, outcome=o, found=found, back=back))
    return out, f'{reading:g} kg (worst grip x{mu:g})'


def g_tow(sp, r, name):
    mu = 1.0; top, seen = T.ladder(sp, mu, 6, 3); out = []
    for kg, want in ((top, True), (T.nxt(top), False)):
        if not kg:
            continue
        def make(s, kg=kg):
            sim = fresh(T.Rig(sp, mu, kg)); o = T.tow_try(sim, np.random.default_rng([3, int(kg * 10), s]))
            return o, sim
        o, sim, s, found = search(make, lambda o, want=want: (o == 'ok') == want, 8)
        lab = lambda t, kg=kg, o=o: [f'{name}: tow a {kg:g} kg sled 0.5 m (G7 tow, new)', 'x1 grip, rope from the rear at axle height, 0.3 m/s',
                                      'dragged it 0.5 m: pass' if o == 'ok' else f'{o}: fail']
        out.append(dict(panel=render(sim, list(sim.log), dict(dist=1.6, az=115.0, el=-20.0, dx=-0.25), lab), kg=kg, outcome=o, found=found))
    return out, f'{top:g} kg (quick: 6 tries a rung at x1)'


def g_rough(sp, r, name):
    top, seen = RG.ladder(sp, RG.GRIP, 6, 3); out = []
    lo = max([a for a in RG.AMPS if a <= top], default=None); hi = next((a for a in RG.AMPS if a > top), None)
    for a, want in ((lo, True), (hi, False)):
        if not a:
            continue
        def make(s, a=a):
            sim = fresh(RG.Rig(sp, RG.GRIP, a)); g = np.random.default_rng([3, s]); sim.ground(RG.field(a, g))
            return RG.rough_try(sim, g), sim
        o, sim, s, found = search(make, lambda o, want=want: (o == 'ok') == want, 8)
        lab = lambda t, a=a, o=o: [f'{name}: rocks to {a} mm, 2 m (G8 rough)', f'grip x{RG.GRIP:g}, 0.4 m/s, holding its heading',
                                    'across: pass' if o == 'ok' else f'{o}: fail']
        out.append(dict(panel=render(sim, list(sim.log), dict(dist=1.6, az=120.0, el=-24.0, dx=0.15), lab), mm=a, outcome=o, found=found))
    return out, f'{top:g} mm (quick: 6 tries a rung at x{RG.GRIP:g})'


# ---------- run ----------
_SPECS = {}


def spec(key):
    """(label, spec, its finals row, the step heights), built once a process"""
    if key not in _SPECS:
        fin = json.load(open(os.path.join(CP.OUT, 'finals.json'))); r = next(x for x in fin['finals'] if x['name'] == key)
        sp = CP.t3_ref() if key == 'T3' else GG.roster(True)[0][0] if key == 'Box' else CP.build(CP.q_of(r['z']))
        _SPECS[key] = (dict(DESIGNS)[key], sp, r, fin['heights'])
    return _SPECS[key]


def job(a):
    key, test = a
    label, sp, r, heights = spec(key); t0 = time.time()
    try:
        fn = {'up': lambda: g_up(sp, r, label), 'climb': lambda: g_climb(sp, r, label, heights), 'turn': lambda: g_turn(sp, r, label),
              'h_up': lambda: g_hill(sp, r, label, False), 'h_down': lambda: g_hill(sp, r, label, True), 'crest': lambda: g_crest(sp, r, label),
              'push': lambda: g_push(sp, r, label), 'tow': lambda: g_tow(sp, r, label),
              'rough': lambda: g_rough(sp, r, label)}[test]
        clips, reading = fn()
        stem = f"{key.replace(' ', '_')}_{test}"; src, dur = write(os.path.join(OUT, stem), [c['panel'] for c in clips])
        meta = [{k: (v if not isinstance(v, (np.floating, np.integer)) else v.item()) for k, v in c.items() if k != 'panel'} for c in clips]
        print(f'{key:10s} {test:6s} {time.time() - t0:5.0f} s  {reading}', flush=True)
        return dict(key=key, label=label, test=test, src=src, poster=stem + '.jpg', secs=round(dur, 1), reading=reading, clips=meta)
    except Exception as e:
        import traceback; traceback.print_exc()
        return dict(key=key, label=label, test=test, err=f'{type(e).__name__}: {e}'[:300])


def main():
    from multiprocessing import Pool
    os.makedirs(OUT, exist_ok=True); arg = sys.argv[1:]
    only = arg[arg.index('--only') + 1].split(',') if '--only' in arg else [k for k, _ in DESIGNS]
    tests = arg[arg.index('--tests') + 1].split(',') if '--tests' in arg else list(TESTS)
    nw = int(arg[arg.index('--workers') + 1]) if '--workers' in arg else 6
    J = [(k, t) for k in only for t in tests]; t0 = time.time()
    with Pool(nw) as pool:
        R = pool.map(job, J, chunksize=1)
    p = os.path.join(OUT, 'films.json'); old = json.load(open(p)) if os.path.exists(p) else []
    keep = {(x['key'], x['test']): x for x in old}; keep.update({(x['key'], x['test']): x for x in R})
    json.dump(list(keep.values()), open(p, 'w'), indent=1, default=float)
    print(f'{len(R)} clips in {time.time() - t0:.0f} s; {sum("err" in x for x in R)} failed')


if __name__ == '__main__':
    if sys.argv[1:2] == ['page']:
        import test_films_page; test_films_page.main()
    else:
        main()
