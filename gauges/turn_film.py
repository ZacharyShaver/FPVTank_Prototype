"""What G3 (the turn gauge) does, filmed from above, beside the two other ways a skid-steer robot turns, with each
turn's slip measured (Zach, 2026-10-31: "visually show me what you mean by turn things. in videos"). The physics is
the gauges' (film.Rec is gauges.Sim on the visual model); the rings and the trace are drawn into the scene only.

    spin  : left side back, right side forward at 60 % (G3 exactly: gauges.turn; a control checks the two agree)
    pivot : left side held still, right side forward at 60 %
    arc   : both forward, left 30 %, right 60 %

chi is the turn the wheels' roll would give with no sideways scrub (the two-speed formula, (sR - sL) / track) over the
turn the body made. Published skid-steer measurements put it near 1.5.

    python gauges/turn_film.py   -> gauges/out/film/turn/turn_g3.mp4, turn_kinds.mp4 (and .gif), turns.json

The designs are T3 and the low step-and-turn run's champion (capability_low).
"""
import os, sys, json, math
import numpy as np
os.environ['SCORPION_CAP'] = 'capability_low'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capability as CP, knobs as K, gauges as G, film as F
import mujoco
from scipy.optimize import minimize

OUT = os.path.join(CP.config.GAUGES_OUT, 'film', 'turn'); os.makedirs(OUT, exist_ok=True)
PS = 480
KINDS = {'spin': (-G.TURN_U, G.TURN_U), 'pivot': (0.0, G.TURN_U), 'arc': (0.5 * G.TURN_U, G.TURN_U)}
S = json.load(open(os.path.join(CP.OUT, 'summary.json')))
DES = {'T3': CP.build(K.T3), 'Low winner': CP.build(CP.q_of(S['champions']['st_0.1']['z']))}


def run(sp, uL, uR, mu=1.0, T=10.0):
    """gauges.turn's loop with any pair of side speeds; also the spin centre's path, the wheels' roll and the body's
    sweep"""
    sim = F.Rec(sp, mu); d = sim.d; sim.place(G.yaw_quat(0.0), 0.0005)
    wc = np.mean([[x, y, 0.0] for x, y in sim.sp['wheels']], 0) * 1e-3
    c0 = (d.xpos[sim.rid] + sim.rot() @ wc)[:2]
    wq = np.array([sim.m.joint(f'j{i}').qposadr[0] for i in range(len(sp['wheels']))]); phi0 = d.qpos[wq].copy()
    turned, prev, rmax, pts, ctr, hist = 0.0, 0.0, 0.0, [], [c0.copy()], [(d.time, 0.0, 0.0)]
    sim.log = [(d.time, d.qpos.copy())]; t0 = d.time
    for k in range(int(T * 1000 / G.TICK)):
        sim.drive(uL, uR)
        R = sim.rot(); P = d.xpos[sim.rid] + sim.E @ R.T
        rmax = max(rmax, float(np.linalg.norm(P[:, :2] - c0, axis=1).max()))
        a = math.atan2(R[1, 0], R[0, 0]); da = (a - prev + math.pi) % (2 * math.pi) - math.pi; turned += da; prev = a
        pts.append(P[:, :2].copy()); ctr.append((d.xpos[sim.rid] + R @ wc)[:2].copy()); hist.append((d.time, turned, rmax))
        if abs(turned) >= math.pi:
            break
    Lm = sim.left; Rw = sp['R'] * 1e-3; ys = np.array([y for _, y in sp['wheels']]) * 1e-3
    B = ys[Lm].mean() - ys[~Lm].mean()
    roll = (d.qpos[wq] - phi0) * Rw; sL, sR = roll[Lm].mean(), roll[~Lm].mean()
    A = np.concatenate(pts); f = lambda c: np.linalg.norm(A - c, axis=1).max()
    cm = minimize(f, A.mean(0), method='Nelder-Mead', options=dict(xatol=1e-4, fatol=1e-5)).x
    return dict(sim=sim, c0=c0, done=abs(turned) >= math.pi, gauge=2e3 * rmax, t=d.time - t0, chi=((sR - sL) / B) / turned if turned else None,
                drift=1e3 * float(np.linalg.norm(np.array(ctr) - c0, axis=1).max()), ctr=np.array(ctr), hist=hist,
                cmin=cm, dmin=2e3 * f(cm), B=B * 1e3, sL=sL, sR=sR)


def seg(scn, p0, p1, rgba, w):
    if scn.ngeom >= scn.maxgeom:
        return
    g = scn.geoms[scn.ngeom]
    mujoco.mjv_initGeom(g, mujoco.mjtGeom.mjGEOM_CAPSULE, np.zeros(3), np.zeros(3), np.zeros(9), np.array(rgba, np.float32))
    mujoco.mjv_connector(g, mujoco.mjtGeom.mjGEOM_CAPSULE, w, np.array(p0, float), np.array(p1, float)); scn.ngeom += 1


def ring(scn, c, r, rgba, w=0.004, dashed=False, n=96):
    for k in range(n):
        if dashed and k % 2:
            continue
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        seg(scn, (c[0] + r * math.cos(a0), c[1] + r * math.sin(a0), 0.002), (c[0] + r * math.cos(a1), c[1] + r * math.sin(a1), 0.002), rgba, w)


def frames(res, title, sub, dist, look, circle='gauge'):
    sim = res['sim']; m, d = sim.m, sim.d
    for i in range(m.ngeom):                                              # the robot see-through, so the trace shows under it
        if m.geom_bodyid[i] != 0:
            m.geom_rgba[i, 3] = min(m.geom_rgba[i, 3], 0.55)
    r = mujoco.Renderer(m, PS, PS, max_geom=20000); log = sim.log; ts = np.array([t for t, _ in log]); out = []
    for t in np.arange(ts[0], ts[-1] + 1e-9, 1.0 / F.FPS):
        i = min(int(np.searchsorted(ts, t)), len(log) - 1); d.qpos[:] = log[i][1]; mujoco.mj_forward(m, d)
        cam = mujoco.MjvCamera(); cam.type = mujoco.mjtCamera.mjCAMERA_FREE
        cam.lookat[:] = (look[0], look[1], 0.0); cam.distance, cam.azimuth, cam.elevation = dist, 90.0, -89.9
        r.update_scene(d, cam); scn = r.scene
        _, turned, rmax = res['hist'][i]
        if circle == 'gauge':                                             # G3's circle: round where the spin started
            ring(scn, res['c0'], res['gauge'] / 2e3, (0.9, 0.45, 0.1, 1.0), dashed=True)
            ring(scn, res['c0'], max(rmax, 1e-3), (0.9, 0.45, 0.1, 1.0), w=0.006)
        else:                                                             # the smallest circle round everything it swept
            ring(scn, res['cmin'], res['dmin'] / 2e3, (0.9, 0.45, 0.1, 1.0), dashed=True)
        C = res['ctr'][:i + 1]
        for a, b in zip(C[:-1:2], C[2::2]):
            seg(scn, (*a, 0.003), (*b, 0.003), (0.1, 0.35, 0.85, 1.0), 0.004)
        seg(scn, (*res['c0'], 0.0), (*res['c0'], 0.004), (0.1, 0.35, 0.85, 1.0), 0.01)
        out.append((r.render().copy(), [title, sub, f'{abs(math.degrees(turned)):3.0f}°   {t - ts[0]:.1f} s']))
    r.close()
    return out


if __name__ == '__main__':
    # control: this loop's spin reads what gauges.turn reads
    for nm, sp in DES.items():
        g_dia, g_t = G.turn(G.Sim(sp, 1.0), 1); mine = run(sp, *KINDS['spin'])
        print(f'control {nm}: gauges.turn {g_dia:.1f} mm in {g_t:.2f} s; this loop {mine["gauge"]:.1f} mm in {mine["t"]:.2f} s')
    rows, R = [], {}
    for nm, sp in DES.items():
        for kind, (uL, uR) in KINDS.items():
            for mu in (0.65, 1.0, 1.5):
                x = run(sp, uL, uR, mu); R[(nm, kind, mu)] = x
                rows.append(dict(design=nm, kind=kind, mu=mu, done=x['done'], t=round(x['t'], 2), gauge=round(x['gauge']), smallest=round(x['dmin']),
                                 chi=None if x['chi'] is None else round(x['chi'], 2), drift=round(x['drift']), track=round(x['B'])))
                print(f"{nm:10s} {kind:5s} mu {mu:4.2f}: {'180 deg' if x['done'] else 'NOT ROUND'} in {x['t']:.2f} s; circle round the start {x['gauge']:.0f} mm, "
                      f"smallest round the sweep {x['dmin']:.0f} mm; centre drift {x['drift']:.0f} mm; chi {x['chi']:.2f} (track {x['B']:.0f} mm)", flush=True)
    json.dump(rows, open(os.path.join(OUT, 'turns.json'), 'w'), indent=1)
    # film 1: G3 itself on both designs, same scale
    a, b = R[('T3', 'spin', 1.0)], R[('Low winner', 'spin', 1.0)]
    dist = 1.45
    F.PW = F.PH = PS
    p1 = frames(a, 'T3: G3 turn (spin in place)', f'left wheels back, right forward (60 %): {a["gauge"]:.0f} mm', dist, a['c0'])
    p2 = frames(b, 'Low winner: G3 turn', f'left wheels back, right forward (60 %): {b["gauge"]:.0f} mm', dist, b['c0'])
    print(F.write(os.path.join(OUT, 'turn_g3'), [p1, p2], 2))
    # film 2: three ways to turn, both designs, same scale
    big = max(R[(nm, k, 1.0)]['dmin'] for nm in DES for k in KINDS) / 1e3
    dist = (big + 0.2) / (2 * math.tan(math.radians(22.5)))
    P = []
    for nm in DES:
        for kind, (uL, uR) in KINDS.items():
            x = R[(nm, kind, 1.0)]
            P.append(frames(x, f'{nm}: {kind}', f'left {uL * 100:+.0f} %, right {uR * 100:+.0f} %: needs {x["dmin"]:.0f} mm', dist, x['cmin'], circle='min'))
    print(F.write(os.path.join(OUT, 'turn_kinds'), P, 3))
