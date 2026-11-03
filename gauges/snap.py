"""Where a printed leg would snap, from the sim (2026-10-28). Zach: "can we test where it would snap? maybe we should
just let the simulation do the thinking here instead of guessing", the legs should "support the body after a fall", and
"they dont have to be exactly like the supports work".

Two parts. MuJoCo, where a design is one rigid body on hinged wheels, gives the loads where the structure meets the
world: each wheel's push on its axle (the interaction force between wheel and robot, mj_rnePostConstraint) and any
contact on a leg or a motor tube, all turned into the robot's own frame. frame.py then solves the printed legs as round
beams clamped at the body, each motor tube a stiff link from its axle to where its legs grip it, so a braced pair or
tripod shares a load the way its stiffnesses say. A leg breaks where its von Mises stress, with the bending modulus
scaled by the print's efficiency ETA*, reaches PLA's strength across its layers, SIGMA_ULT*.

The loads come from G1's falls: n drops from 300 mm in random orientations and spins, each followed for a second, every
0.2 ms step, as a 5 ms running mean (MuJoCo's hard contact rings for a step or two), solved every 1 ms. The tyres get a
spring for these drops (TYRE_K*): the gauges' contact (2 ms, the printed ball's bounce) puts 64 times the robot's
weight on one wheel in a flat landing, where rubber squashes; 30 N/mm makes it 7. Legs and tubes still land as PLA.
(That 7 was read with 30 handed to MuJoCo as it was, which MuJoCo takes per unit mass: about 15 N/mm on a 2 kg
robot's tyre. Since 2026-11-03 robots.spring_solref makes it a physical 30 N/mm, so the same landings read harder.)

Sizing: every segment to SIGMA_ULT / SF, never under R_FLOOR (fully stressed: each radius scaled by the cube root of its
stress over the allowed, the frame solved again, until it settles), the worst load cases kept; then the design is
rebuilt at those sizes (heavier legs, heavier landings) and dropped again.

The first version (superseded the same evening) read the loads in the world's frame but the legs in the robot's: right
only at rest at the origin, where its check ran. In a fall it gave lever arms of the robot's whole drop.

    python gauges/snap.py check          # the loads don't depend on where the robot is or how it's turned (control:
                                         # the world-frame reading does); the frame's root reactions balance the wheels
    python gauges/snap.py compare [seed] # base designs with 1, 2 and 3 legs per wheel, sized from the falls
                                         #  -> gauges/out/body/snap.png, snap.json
"""
import os, sys, math, json, time
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import gauges as GG, robots as RB, body as B, body_tree as T, frame as FR

SIGMA_ULT, SF, ETA = 25.0, 2.0, 0.7       # MPa (printed PLA across its layers*), safety factor*, bending efficiency at half fill*
R_FLOOR, R_CAP = 6.0, 45.0                # mm: the thinnest and thickest a segment may be sized
N_FALL, T_FALL, WIN, EVERY = 24, 1.0, 25, 5   # falls, s followed, steps in the running mean (5 ms), steps between solves (1 ms)
TYRE_K, TYRE_ZETA = 30.0, 0.3             # N/mm, damping ratio
LINK_R = 40.0                             # mm: a motor tube as a beam in the frame (stiff)


class Model:
    """a design's sim and its frame: the loads at the current step as node loads in the robot's frame (N, N mm)"""
    def __init__(self, sp, mu=1.0):
        import mujoco
        self.mj, self.sp = mujoco, sp; self.sim = GG.Sim(dict(sp, tyre_k=TYRE_K, tyre_zeta=TYRE_ZETA), mu); m = self.sim.m
        X, idx = [], {}
        def node(p):
            key = tuple(np.round(p, 2))
            if key not in idx:
                idx[key] = len(X); X.append(np.asarray(p, float))
            return idx[key]
        self.seg = [(node(p0), node(p1)) for p0, p1, r in sp['struts']]; elems = [(i, j, r) for (i, j), (_, _, r) in zip(self.seg, sp['struts'])]
        self.hub = [node(h) for h in sp['hubs']]
        for w, g in sp['grips']:
            elems.append((self.hub[w], node(g), LINK_R))
        self.fixed = sorted({node(r) for r in sp['roots3']})
        self.X = np.array(X); self.elems = elems; self.nseg = len(sp['struts'])
        self.rid = m.body('robot').id; self.wb = [m.body(f'w{i}').id for i in range(len(sp['wheels']))]; self.root = m.body_rootid[self.wb[0]]
        self.owner = {m.geom(f'strut{k}').id: ('seg', k) for k in range(self.nseg)}
        for g in range(m.ngeom):
            if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH:
                h = int(m.mesh(m.geom_dataid[g]).name[1:])
                if h in sp.get('tube_of', {}):
                    self.owner[g] = ('tube', sp['tube_of'][h])
        self.f6 = np.zeros(6)

    def frame(self, radii=None):
        el = self.elems if radii is None else [(i, j, r) for (i, j, _), r in zip(self.elems[:self.nseg], radii)] + self.elems[self.nseg:]
        return FR.Frame(self.X, el, self.fixed)

    def node_loads(self, world=False):
        """(nodes, 6): each wheel's push at its tube's hub node, each contact on a leg at its segment's nearer end, on a
        tube at its hub; forces N, moments N mm, in the robot's frame (world: the superseded reading, for the control)"""
        mj, m, d = self.mj, self.sim.m, self.sim.d
        mj.mj_rnePostConstraint(m, d)
        Rm = d.xmat[self.rid].reshape(3, 3); xr = d.xpos[self.rid]
        to_b = (lambda v: v) if world else (lambda v: Rm.T @ v)
        at_b = (lambda p: p * 1e3) if world else (lambda p: (Rm.T @ (p - xr)) * 1e3)   # mm
        L = np.zeros((len(self.X), 6)); c = at_b(d.subtree_com[self.root])
        for w, b in enumerate(self.wb):                                 # the wheel's push on the robot, moved to its hub
            f = to_b(-d.cfrc_int[b, 3:]); tau = to_b(-d.cfrc_int[b, :3]) * 1e3; H = self.X[self.hub[w]]
            L[self.hub[w], :3] += f; L[self.hub[w], 3:] += tau + np.cross(c - H, f)
        for i in range(d.ncon):                                         # the ground on a leg or a tube
            con = d.contact[i]; hit = self.owner.get(con.geom2) or self.owner.get(con.geom1)
            if hit is None:
                continue
            mj.mj_contactForce(m, d, i, self.f6); fw = con.frame.reshape(3, 3).T @ self.f6[:3]
            f = to_b(fw if con.geom2 in self.owner else -fw); p = at_b(con.pos)
            if hit[0] == 'seg':
                a, b2 = self.seg[hit[1]]; n_ = a if np.linalg.norm(p - self.X[a]) < np.linalg.norm(p - self.X[b2]) else b2
            else:
                n_ = self.hub[hit[1]]
            L[n_, :3] += f; L[n_, 3:] += np.cross(p - self.X[n_], f)
        return L


def falls(sp, n=N_FALL, seed=0, keep=None):
    """each segment's peak stress (MPa) over n falls, and the load cases (node loads) that set each segment's peak"""
    md = Model(sp); fr = md.frame(); sim, d = md.sim, md.sim.d; rng = np.random.default_rng(seed)
    peak = np.zeros(md.nseg); cases = [None] * md.nseg; steps = int(T_FALL / sim.m.opt.timestep)
    for fall in range(n):
        q = rng.normal(size=4); q /= np.linalg.norm(q)
        sim.place(q, GG.DROP_MM * 1e-3); d.qvel[3:6] = rng.uniform(-1, 1, 3) * GG.SPIN
        ring = np.zeros((WIN, len(md.X), 6))
        for k in range(steps):
            sim.mj.mj_step(sim.m, d); ring[k % WIN] = md.node_loads()
            if k >= WIN and k % EVERY == 0:
                Lm = ring.mean(0); s = fr.stress(fr.solve(Lm)[0], ETA)[:md.nseg]; up = s > peak
                if up.any():
                    peak = np.where(up, s, peak)
                    for j in np.where(up)[0]:
                        cases[j] = Lm.copy()
    return peak, cases, md


def fsd(md, cases, radii, iters=12):
    """fully stressed sizing against fixed load cases: each segment's radius times the cube root of its worst stress
    over the allowed, the frame solved again; a segment no thinner than R_FLOOR nor thicker than R_CAP"""
    allow = SIGMA_ULT / SF; r = np.array(radii, float); uniq = []
    for c in cases:
        if c is not None and not any(c is u for u in uniq):
            uniq.append(c)
    for _ in range(iters):
        fr = md.frame(r); s = np.max([fr.stress(fr.solve(c)[0], ETA)[:md.nseg] for c in uniq], axis=0)
        r = np.clip(r * (s / allow) ** (1.0 / 3.0), R_FLOOR, R_CAP)
    fr = md.frame(r); s = np.max([fr.stress(fr.solve(c)[0], ETA)[:md.nseg] for c in uniq], axis=0)
    return r, s


def legs_g(sp):
    return sum(math.pi * st[2] ** 2 * np.linalg.norm(np.subtract(st[1], st[0])) for st in sp['struts']) * 1.24e-3 * T.FILL


def size(q, rounds=3, n=N_FALL, seed=0, log=print):
    """the design dropped, its legs sized to its loads, rebuilt and dropped again: (first spec, its peak stress, final
    spec, its peak stress, history); None when it can't be built, or its sized legs clash"""
    sp = T.build(q)
    if sp is None:
        return None
    s0, cases, md = falls(sp, n, seed); first = (sp, s0); hist = []
    for k in range(rounds):
        r, s_pred = fsd(md, cases, [st[2] for st in sp['struts']])
        nxt = T.build(q, radii=list(r), flare=False)
        if nxt is None:
            log(f'  round {k + 1}: the sized legs clash; stopped'); hist.append(dict(clash=True)); break
        sp = nxt; s, cases, md = falls(sp, n, seed)
        hist.append(dict(worst=float(s.max()), legs_g=legs_g(sp), mass=sp['mass']))
        log(f'  round {k + 1}: worst {s.max():.1f} MPa, legs {legs_g(sp):.0f} g, robot {sp["mass"]:.0f} g')
        if s.max() <= 1.1 * SIGMA_ULT / SF:
            break
    return first[0], first[1], sp, s if hist and not hist[-1].get('clash') else first[1], hist


def check():
    """the same design at rest, at the origin and moved and turned: its node loads in its own frame must agree (the
    superseded world-frame reading must not); and the frame's reactions at the roots must balance the wheels' pushes"""
    for q in T.sobol(64, 3):
        sp = T.build(dict(q, tree=0.0, members=2.0, spread_x=0.6, spread_z=0.6))
        if sp is not None and not sp.get('limb'):
            break
    out = {}
    for name, x, yaw in (('at the origin', 0.0, 0.0), ('moved 0.8 m and turned 70 degrees', 0.8, 70.0)):
        md = Model(sp); sim, d = md.sim, md.sim.d; sim.place(GG.yaw_quat(math.radians(yaw)), 0.0005, x=x)
        while d.time < 0.5:
            sim.mj.mj_step(sim.m, d)
        out[name] = (md.node_loads(), md.node_loads(world=True), md)
    (a, aw, md), (b, bw, _) = out.values()
    rel = np.abs(a - b).max() / np.abs(a).max(); relw = np.abs(aw - bw).max() / np.abs(aw).max()
    print(('PASS ' if rel < 0.02 else 'FAIL ') + f'node loads in the robot\'s frame agree moved and turned within {100 * rel:.2f} % (2 % allowed)')
    print(('PASS ' if relw > 0.2 else 'FAIL ') + f'control: the world-frame reading differs by {100 * relw:.0f} %')
    fr = md.frame(); f, u = fr.solve(a)
    push = a[md.hub].sum(0)[:3]; react = np.zeros(3)                    # the roots hold what the hubs push (+ legs' contacts: none at rest)
    for e, (i, j, r) in enumerate(fr.el):
        if i in md.fixed or j in md.fixed:
            R3 = FR._frame(fr.X[i], fr.X[j]); fl = f[e][0:3] if i in md.fixed else f[e][6:9]
            react += R3.T @ fl
    bal = np.linalg.norm(react + push) / np.linalg.norm(push)               # the roots push back what the hubs push: equal, opposite
    print(('PASS ' if bal < 0.01 else 'FAIL ') + f'the roots hold the hubs\' push: {np.round(react, 1)} N against {np.round(push, 1)} N, off by {100 * bal:.2f} %')


def colours(ratio):
    """green (no load) to yellow (the allowed: half of PLA's strength) to red (snaps)"""
    out = []
    for r in np.clip(ratio, 0.0, 1.0):
        a, b = (np.array([0.25, 0.7, 0.35]), np.array([0.97, 0.8, 0.2])) if r < 0.5 else (np.array([0.97, 0.8, 0.2]), np.array([0.85, 0.12, 0.1]))
        t = r / 0.5 if r < 0.5 else (r - 0.5) / 0.5; c = a + (b - a) * t; out.append(f'{c[0]:.3f} {c[1]:.3f} {c[2]:.3f} 1')
    return out


def _job(a):
    i, nm, q = a; t0 = time.time(); lines = []
    res = size(q, log=lines.append)
    if res is None:
        return i, nm, None, lines, time.time() - t0
    sp0, s0, sp, s, hist = res
    return i, nm, dict(sp0=sp0, s0=s0, sp=sp, s=s, hist=hist), lines, time.time() - t0


def compare(seed=0, k=4):
    """k base designs, each with 1, 2 and 3 legs per wheel, sized from the falls -> out/body/snap.png, snap.json"""
    from multiprocessing import Pool
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    bases = []
    for q in T.sobol(128, seed):
        qs = [dict(q, tree=0.0, members=float(m), spread_x=0.6, spread_z=0.6) for m in (1, 2, 3)]
        if all(T.build(x) is not None for x in qs):
            bases.append(qs)
        if len(bases) >= k:
            break
    J = [(i, m + 1, qs[m]) for i, qs in enumerate(bases) for m in range(3)]
    with Pool(min(len(J), 24)) as pool:
        R = pool.map(_job, J, chunksize=1)
    fig = plt.figure(figsize=(14, 3.4 * k)); fig.patch.set_facecolor('white'); out = []
    for i, nm, res, lines, dt in sorted(R, key=lambda r: (r[0], r[1])):
        ax = fig.add_subplot(k, 3, 3 * i + nm); ax.set_axis_off()
        if res is None:
            ax.set_title(f'{i + 1}, {nm} per wheel: could not be built', fontsize=9, loc='left'); continue
        sp, s, hist = res['sp'], res['s'], res['hist']; ok = s.max() <= SIGMA_ULT
        ax.imshow(B.render(sp, strut_rgba=colours(s / SIGMA_ULT)))
        clash = bool(hist and hist[-1].get('clash'))
        ax.set_title(f"{i + 1}, {nm} leg{'s' if nm > 1 else ''} a wheel{' (sized legs clash: as first built)' if clash else ''}: "
                     f"{'holds' if ok else 'snaps'}, worst {s.max():.0f} MPa\nlegs {legs_g(sp):.0f} g, robot {sp['mass'] / 1000:.1f} kg; "
                     f"first built {res['s0'].max():.0f} MPa, {legs_g(res['sp0']):.0f} g", fontsize=9, loc='left')
        out.append(dict(design=i + 1, legs_per_wheel=nm, worst_mpa=float(s.max()), legs_g=legs_g(sp), mass=sp['mass'], first_worst=float(res['s0'].max()),
                        first_legs_g=legs_g(res['sp0']), rounds=hist, log=lines, s=round(dt), radii=[st[2] for st in sp['struts']]))
        print(f"design {i + 1}, {nm} per wheel: {s.max():.1f} MPa, legs {legs_g(sp):.0f} g (first {res['s0'].max():.0f} MPa, {legs_g(res['sp0']):.0f} g); {dt:.0f} s", flush=True)
    fig.suptitle(f'Legs sized from {N_FALL} falls from 300 mm: one beam, a braced pair, a tripod per wheel\n'
                 f'(green safe, yellow at the allowed {SIGMA_ULT / SF:.1f} MPa, red snaps at PLA\'s {SIGMA_ULT:.0f})', fontsize=12, x=0.02, ha='left')
    plt.tight_layout(rect=(0, 0, 1, 0.97)); p = os.path.join(B.OUT, 'snap.png'); plt.savefig(p, dpi=85)
    json.dump(out, open(os.path.join(B.OUT, 'snap.json'), 'w'), indent=1, default=float); print(p)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'check':
        check()
    elif cmd == 'compare':
        compare(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
    else:
        print(__doc__)
