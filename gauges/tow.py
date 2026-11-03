"""G7 tow (2026-11-02), in place of G7 push in the tow run: the heaviest sled a design drags 0.5 m on a rope from a hitch
on its body. Zach, on the realistic run: "step and push ... directly conflict because of the shape of the front of a
robot. push gives a flat front while step gives a curved one for climbing. my idea is to change push into tow". The
data agreed: among four-wheelers step and push ran against each other (rank correlation -0.44), and the steppers failed
the push by riding up the box (the best climber at 4 kg, T3 at 8 kg), not by running out of grip.

The hitch: on the body's centre line at its rear surface, at axle height (the wheels' radius) or as near it as the
body's rear reaches. Not the tail's end: a load there reads the tail servo and levers the front up. The rope: a
MuJoCo tendon, slack until ROPE long (a one-sided limit). The sled: 300 x 300 x 60 mm, the floor's own friction (0.6 at
x1, so 5.9 N a kilogram to drag at x1), its eye at its front, low. A try starts square on +-10 degrees, the rope
nearly taut, ramps up over 0.5 s to V_TOW and holds its heading (as push). It passes when the sled has come GOAL
within T_TOW with the robot upright and never tilted past TILT (a wheelie onto its back fails). Forward only; the
tail and flippers stay stowed. Read over the friction band (the sled's friction scales with the floor's), the worst
counting, as push.

    python gauges/tow.py check   -> its controls (exits 1 on a failure)
"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import gauges as GG, robots as RB

SLED = (0.15, 0.15, 0.03)                 # half-sizes, m
MASSES = (0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0)   # kg
V_TOW, T_TOW, RAMP, GOAL, ROPE, SLACK, TILT = 0.3, 8.0, 0.5, 0.5, 0.25, 0.02, 45.0   # m/s, s, s, m, m, m, degrees
N_TRY = 20


def hitch(sp, z=None):
    """the hitch (mm, body frame): the body's rear surface on the centre line at axle height, or at the nearest height
    the body's rear reaches; z: another height (a control)"""
    body = np.asarray(sp['hulls'][0], float); lo, hi = body[:, 2].min() + 5.0, body[:, 2].max() - 5.0
    zh = float(np.clip(sp['R'] if z is None else z, lo, hi)); x = RB.rear_surface([body], zh)
    return np.array([body[:, 0].min() if x is None else x, 0.0, zh])


class Rig(GG.Sim):
    """gauges.Sim with a sled on a rope from the hitch (the site and the tendon added to robots.xml)"""
    def __init__(self, sp, mu, kg, z=None):
        super().__init__(sp, mu, extra=self._sled(kg))
        h = hitch(sp, z) * 1e-3; self.hitch_mm = h * 1e3
        x = RB.xml(sp, mu, extra=self._sled(kg))
        x = x.replace('<body name="robot" pos="0 0 0.5"><freejoint/>', f'<body name="robot" pos="0 0 0.5"><freejoint/><site name="hitch" pos="{h[0]:.5f} {h[1]:.5f} {h[2]:.5f}"/>', 1)
        x = x.replace('</worldbody>', f'</worldbody><tendon><spatial name="rope" limited="true" range="0 {ROPE}" width="0.002">'
                                      f'<site site="hitch"/><site site="eye"/></spatial></tendon>', 1)
        self.m = self.mj.MjModel.from_xml_string(x); self.d = self.mj.MjData(self.m)   # the same bodies, joints and actuators
        self.sid = self.m.site('hitch').id; self.bid = self.m.body('sled').id
        self.sq = self.m.joint(self.m.body('sled').jntadr[0]).qposadr[0]

    @staticmethod
    def _sled(kg):
        def xml(f, ca):
            return (f'<body name="sled" pos="-1 0 {SLED[2] + 0.0005:.4f}"><freejoint/>'
                    f'<geom type="box" size="{SLED[0]} {SLED[1]} {SLED[2]}" mass="{kg:.3f}" friction="{f["floor"]}"{ca}/>'
                    f'<site name="eye" pos="{SLED[0]:.4f} 0 {SLED[2] * 0.5:.4f}"/></body>')
        return xml


def tow_try(sim, rng):
    """one try: 'ok', 'stalled' (the sled short of GOAL at T_TOW) or 'tipped' (past TILT: a wheelie, or over)"""
    sp, d, m = sim.sp, sim.d, sim.m; R = sp['R'] * 1e-3; mj = sim.mj
    yaw0 = math.radians(rng.uniform(-10, 10)); sim.place(GG.yaw_quat(yaw0), 0.0005)
    mj.mj_forward(m, d); hp = d.site_xpos[sim.sid].copy(); dirn = np.array([math.cos(yaw0), math.sin(yaw0), 0.0])
    c = hp - dirn * (ROPE - SLACK + SLED[0]); q = sim.sq                 # the sled behind the hitch, its rope SLACK short of taut
    d.qpos[q:q + 7] = (c[0], c[1], SLED[2] + 0.0005, math.cos(yaw0 / 2), 0.0, 0.0, math.sin(yaw0 / 2)); d.qvel[:] = 0.0; mj.mj_forward(m, d)
    x0 = d.xipos[sim.bid][:2].copy(); u0 = min(V_TOW / (sim.w0 * R), 1.0)
    for k in range(int(T_TOW * 1000 / GG.TICK)):
        Rm = sim.rot(); e = (math.atan2(Rm[1, 0], Rm[0, 0]) - yaw0 + math.pi) % (2 * math.pi) - math.pi
        u = u0 * min(1.0, k * GG.TICK / 1000 / RAMP); cs = u0 * max(-0.5, min(0.5, 2.0 * e))
        sim.drive(u + cs, u - cs)
        if math.degrees(math.acos(max(-1.0, min(1.0, Rm[2, 2])))) > TILT:
            return 'tipped'
        if (d.xipos[sim.bid][:2] - x0) @ dirn[:2] >= GOAL:
            return 'ok' if GG.classify(sim.rot()) == 'upright' else 'tipped'
    return 'stalled'


def nxt(kg):
    i = MASSES.index(kg) + 1 if kg in MASSES else 0
    return MASSES[i] if i < len(MASSES) else None


def ladder(sp, mu, n, seed, z=None):
    """the heaviest sled dragged in at least 0.9 n of n tries, every lighter one dragged: (kg, {kg: outcomes})"""
    need = math.ceil(0.9 * n); top = 0.0; seen = {}
    for kg in MASSES:
        sim = Rig(sp, mu, kg, z); rng = np.random.default_rng([seed, int(kg * 10)]); res = []
        for _ in range(n):
            res.append(tow_try(sim, rng))
            if sum(r != 'ok' for r in res) > n - need:
                break
        seen[kg] = {k: res.count(k) for k in set(res)}
        if sum(r == 'ok' for r in res) < need:
            break
        top = kg
    return top, seen


def check(n=6):
    """the controls: the push plate doesn't change the tow (it isn't at the back); a kilogram of ballast over the wheels
    tows more, unless the drive runs out first; a hitch moved to the body's top makes the same pull rear the robot up
    (it tows less, failing by tipping); the best climber, which failed the push by riding up the box at 4 kg, tows as
    its grip allows. At x1, n tries a rung. Exits 1 on a failure"""
    import knobs as K, copy
    t3 = K.make(dict(K.T3, track=130.0), real=True); bad = 0
    def read(sp, z=None):
        return ladder(sp, 1.0, n, 3, z)
    base, seen = read(t3); print(f"T3 (real, track 130): tows {base} kg at x1, hitch at {np.round(hitch(t3)).tolist()} mm; next: {seen.get(nxt(base))}")
    plate = K.make(dict(K.T3, track=130.0, bumper=0.0), real=True); p, _ = read(plate)
    ok = abs(p - base) <= 1.0; bad += not ok; print(('PASS ' if ok else 'FAIL ') + f'without its push plate: {p} kg (with: {base})')
    heavy = copy.deepcopy(t3); m0 = heavy['M']; heavy['M'] = m0 + 1000.0; heavy = RB.dims(heavy); h, hs = read(heavy)
    ok = h > base or (hs.get(nxt(h)) or {}).get('stalled', 0) > 0; bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'control: +1 kg of ballast at its centre of mass: {h} kg (more grip; or the drive stalls first: {hs.get(nxt(h))})')
    top = float(np.asarray(t3['hulls'][0])[:, 2].max()) - 5.0; hi, his = read(t3, z=top)
    ok = hi < base and any((his.get(kg) or {}).get('tipped', 0) for kg in his); bad += not ok
    print(('PASS ' if ok else 'FAIL ') + f'control: the hitch at the body’s top ({top:.0f} mm): {hi} kg, failing by {his.get(nxt(hi))}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    if 'check' in sys.argv[1:]:
        check()
    else:
        print(__doc__)
