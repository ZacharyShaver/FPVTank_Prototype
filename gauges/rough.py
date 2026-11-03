"""G8 rough ground (2026-11-02): the largest rocks a design drives GOAL across. Zach: "add rough terrain"; asked what
kind, he picked rocky ground (fixed rocks and bumps, a ladder like the step's) over loose rubble and washboard ripples.

The ground: a MuJoCo heightfield of scattered rocks, each half an ellipsoid, its base ROCK_R in radius (stretched
0.7-1.3x along a random direction), A x U(0.4, 1) tall; where rocks overlap the taller wins; their bases add up to
COVER of the rock zone (0.24 of it covered, net of overlaps). A try's rocks (places, bases, relative heights) come
from the seed and the try alone, never the rung or the design: at a taller rung the same field is raised, so a rung is
never easier than the one below, and every design meets the same fields. (The first draft scaled the bases with A at
fixed cover: bigger rungs had fewer, larger rocks, the path met fewer of them, and T3 passed 100 mm and failed 50.)
The robot starts on the flat, square on +-10 degrees, ramps over RAMP to V_ROUGH and holds its heading (as tow); the
tail and flippers act on a stall as on the step (gauges.Reflex). It passes when its centre of mass has come GOAL
within T_ROUGH and it ends upright; it fails over (past OVER degrees) or stuck (under STUCK_MM of progress in
STUCK_S). The reading is the step's pooled rule (gauges.ladder_pooled): the rock size where the pass rate, pooled into
a curve that never rises with size, falls to 0.9. Read at the terrain gauges' grip (crest.GRIP, x2.5): rock is grippy,
and the gauge is about the shape, not the tyres.

    python gauges/rough.py check   -> its controls (exits 1 on a failure)
"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import gauges as GG, robots as RB

AMPS = (10, 20, 30, 40, 50, 60, 80, 100, 120, 150)   # mm: the rungs, the tallest rock a field may have
CELL, FIELD_X, FIELD_Y, ROCK_X0 = 0.01, (-0.5, 2.9), 0.8, 0.35   # m: grid, field's ends in X, its half-width, rocks start
COVER, ROCK_R = 0.3, (0.05, 0.15)                     # of the rock zone's area under rocks; m, a rock's base radius
V_ROUGH, RAMP, GOAL, T_ROUGH = 0.4, 0.5, 2.0, 12.0    # m/s, s, m, s
OVER, STUCK_MM, STUCK_S = 85.0, 20.0, 3.0              # degrees; mm in s
GRIP = 2.5                                            # as crest.GRIP
N_TRY = 20
NX = int(round((FIELD_X[1] - FIELD_X[0]) / CELL)) + 1; NY = int(round(2 * FIELD_Y / CELL)) + 1


def field(a_mm, rng, fx=FIELD_X, fy=FIELD_Y, zone=None):
    """one rock field (m, rows along Y x columns along X, CELL apart): the rocks from rng, raised to at most a_mm tall.
    By default this gauge's (NY x NX); course.py's covers fx by +-fy, its rocks' centres in zone (X) only"""
    A = a_mm * 1e-3; nx, ny = int(round((fx[1] - fx[0]) / CELL)) + 1, int(round(2 * fy / CELL)) + 1
    xs = np.linspace(*fx, nx); ys = np.linspace(-fy, fy, ny); z0, z1 = zone or (ROCK_X0, fx[1])
    Z = np.zeros((ny, nx)); area = (z1 - z0) * 2 * fy; lo, hi = ROCK_R
    n = int(round(COVER * area / (math.pi * (hi ** 3 - lo ** 3) / (3 * (hi - lo)))))   # over a base's mean area
    for _ in range(n):
        h = A * rng.uniform(0.4, 1.0); r = rng.uniform(lo, hi); s = rng.uniform(0.7, 1.3); th = rng.uniform(0, math.pi)
        cx, cy = rng.uniform(z0, z1), rng.uniform(-fy, fy); rx, ry = r * s, r / s
        R = max(rx, ry); i0, i1 = np.searchsorted(ys, [cy - R, cy + R]); j0, j1 = np.searchsorted(xs, [cx - R, cx + R])
        X, Y = np.meshgrid(xs[j0:j1] - cx, ys[i0:i1] - cy); c, sn = math.cos(th), math.sin(th)
        u, v = (c * X + sn * Y) / rx, (-sn * X + c * Y) / ry
        Z[i0:i1, j0:j1] = np.maximum(Z[i0:i1, j0:j1], h * np.sqrt(np.clip(1.0 - u * u - v * v, 0.0, None)))
    return Z


class Rig(GG.Sim):
    """gauges.Sim on a heightfield of rocks up to a_mm tall (the field's data set per try, by ground())"""
    def __init__(self, sp, mu, a_mm, x_off=0.0):
        super().__init__(sp, mu)
        self.top = max(a_mm, 1) * 1e-3; cx = 0.5 * (FIELD_X[0] + FIELD_X[1]) + x_off
        f = '%.4f 0.005 0.0005' % (RB.FRICTION['floor'] * mu)
        def extra(_f, ca):
            return f'<geom name="rocks" type="hfield" hfield="rocks" pos="{cx:.4f} 0 -0.0005" friction="{f}"{ca}/>'
        x = RB.xml(sp, mu, extra=extra).replace('<asset>', f'<asset><hfield name="rocks" nrow="{NY}" ncol="{NX}" '
                                                 f'size="{(FIELD_X[1] - FIELD_X[0]) / 2:.4f} {FIELD_Y:.4f} {self.top:.5f} 0.01"/>', 1)
        self.m = self.mj.MjModel.from_xml_string(x); self.d = self.mj.MjData(self.m)   # the same bodies, joints and actuators
        self.gid = self.m.geom('rocks').id

    def ground(self, Z):
        self.m.hfield_data[:] = np.clip(Z / self.top, 0.0, 1.0).ravel()


def rough_try(sim, rng):
    """one try on the field set: 'ok', 'over' (past OVER, or not upright at the end) or 'stuck'"""
    sp, d = sim.sp, sim.d; R = sp['R'] * 1e-3; mj = sim.mj
    yaw0 = math.radians(rng.uniform(-10, 10)); sim.place(GG.yaw_quat(yaw0), 0.0005)
    dirn = np.array([math.cos(yaw0), math.sin(yaw0)]); x0 = d.xipos[sim.rid][:2].copy(); u0 = min(V_ROUGH / (sim.w0 * R), 1.0)
    rf = GG.Reflex(sim) if sim.limb or sim.flip else None; prog = []; n_stuck = int(STUCK_S * 1000 / GG.TICK)
    for k in range(int(T_ROUGH * 1000 / GG.TICK)):
        t = k * GG.TICK / 1000
        if rf is not None:
            rf.tick(t)
        Rm = sim.rot(); e = (math.atan2(Rm[1, 0], Rm[0, 0]) - yaw0 + math.pi) % (2 * math.pi) - math.pi
        u = u0 * min(1.0, t / RAMP); cs = u0 * max(-0.5, min(0.5, 2.0 * e))
        sim.drive(u + cs, u - cs)
        if math.degrees(math.acos(max(-1.0, min(1.0, Rm[2, 2])))) > OVER:
            return 'over'
        p = (d.xipos[sim.rid][:2] - x0) @ dirn; prog.append(p)
        if p >= GOAL:
            return 'ok' if GG.classify(sim.rot()) == 'upright' else 'over'
        if len(prog) > n_stuck and prog[-1] - prog[-1 - n_stuck] < STUCK_MM * 1e-3:
            return 'stuck'
    return 'stuck'


def reading(seen, n):
    """the pooled rule (gauges.ladder_pooled) over AMPS; a rung not tried counts as failed"""
    return GG.ladder_pooled({(a, False): (seen.get(a) or {}).get('ok', 0) for a in AMPS}, n, AMPS, 0.9)


def ladder(sp, mu, n, seed, amps=AMPS):
    """(mm, {rung: outcomes}): up the rungs until one passes under half its tries; try k's field and start from
    (seed, k), the same for every design and, raised, at every rung"""
    seen = {}
    for a in amps:
        sim = Rig(sp, mu, a); res = []
        for k in range(n):
            g = np.random.default_rng([seed, k]); sim.ground(field(a, g)); res.append(rough_try(sim, g))
            if sum(r == 'ok' for r in res) + n - len(res) < 0.5 * n:
                break
        seen[a] = {o: res.count(o) for o in set(res)}
        if res.count('ok') < 0.5 * n:
            break
    return reading(seen, n), seen


def check(n=6):
    """the controls: the field is where it's drawn (rays down hit each rock's top); on a flat field (every rock 0 tall)
    the box and T3 all drive GOAL; the box with its belly 15 mm lower reads below the box (it beaches sooner); T3 reads.
    At GRIP, n tries a rung. Exits 1 on a failure"""
    import knobs as K
    bad = 0
    main, _ = GG.roster(True); bx = main[0]; t3 = K.make(dict(K.T3, track=130.0), real=True)
    sim = Rig(bx, GRIP, 50); Z = field(50, np.random.default_rng([1, 0]))
    xs = np.linspace(*FIELD_X, NX); ys = np.linspace(-FIELD_Y, FIELD_Y, NY)
    pts = list(zip(*np.nonzero(Z > 0.03)))[::97][:40]
    def off(D):                                                           # mm: the worst ray's miss of Z, the field D loaded
        sim.ground(D); sim.mj.mj_forward(sim.m, sim.d); e = []
        for i, j in pts:
            gid = np.zeros(1, np.int32); dist = sim.mj.mj_ray(sim.m, sim.d, np.array([xs[j], ys[i], 0.5]), np.array([0.0, 0.0, -1.0]), None, 1, -1, gid)
            e.append(abs((0.5 - dist) - (Z[i, j] - 0.0005)) if gid[0] == sim.gid else 1.0)
        return max(e) * 1e3
    a, f = off(Z), off(Z[::-1]); ok = a < 2.0 and f > 2.0; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'the field is where it is drawn: rays down on {len(pts)} rock points, worst {a:.2f} mm off '
          f'(control, the field loaded mirrored in Y: {f:.0f} mm off)')
    for nm, sp in (('Box', bx), ('T3', t3)):
        sim = Rig(sp, GRIP, 10); sim.ground(np.zeros((NY, NX))); res = [rough_try(sim, np.random.default_rng([2, k])) for k in range(n)]
        ok = res.count('ok') == n; bad += not ok
        print(('PASS ' if ok else 'FAIL ') + f'control: {nm} on a flat field drives {GOAL} m: {res}')
    Hb = bx['hulls'][0].copy(); Hb[Hb[:, 2] <= Hb[:, 2].min() + 1e-6, 2] -= 15.0
    low = RB.dims(dict(bx, hulls=[Hb], name='Box, belly 15 mm lower'))
    b, bs = ladder(bx, GRIP, n, 3); lo, ls = ladder(low, GRIP, n, 3)
    ok = lo < b; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'control: the box with its belly 15 mm lower: {lo} mm (the box: {b} mm) {ls} | {bs}')
    t, ts = ladder(t3, GRIP, n, 3); print(f'T3 (real, track 130): {t} mm {ts}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    if 'check' in sys.argv[1:]:
        check()
    else:
        print(__doc__)
