"""Drops for one-piece bodies (2026-10-29). Zach: "test there durability as you go". unibody.py's landing pushes one
wheel six set ways; here each design falls as G1 drops it (N_FALL from 300 mm, random orientation and spin, the tyres
on snap.py's 30 N/mm spring*), MuJoCo gives every push on it (each wheel's on its axle, every floor contact on the
body), and fem.py solves the printed shape under each fall's hardest moment (the largest total push, a 5 ms mean:
MuJoCo's hard contact rings). The body meets the floor as convex pieces cut from its own voxels (k-means, PIECES* of
them), so a landing on the top or a side counts, which the wheel landings can't see and SKO may have cut.

A push on the body is spread over the surface within PATCH* of it (a floor hit is a patch, not a point: first spread
over the 8 nearest nodes, the voxels beside them read 74-98 MPa and moved round to round), and that patch is read apart,
as the motors' seats are: a floor corner on PLA chips locally, and that number isn't the structure's.

    python gauges/drops.py check    # at rest on the floor the pushes sum to the robot's weight, all through the wheels
                                    # (control: the same robot dropped, mid-air, reads nothing)
"""
import os, sys, math
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import gauges as GG, robots as RB, unibody as U, fem as FE

N_FALL, T_FALL, EVERY, WIN = 24, 0.8, 2, 12     # falls, s followed, steps between samples (0.4 ms), samples in the mean (~5 ms)
PIECES, PATCH = 40, 15.0                       # convex pieces the body meets the floor as*; mm round a body contact it's spread over*
TYRE_K, TYRE_ZETA = U.TYRE_K, 0.3


def pieces(mesh, k=PIECES, seed=0):
    """the shape as k convex pieces: its voxels' corners clustered (k-means), each cluster's hull"""
    from scipy.cluster.vq import kmeans2
    c = mesh.centres(); rng = np.random.default_rng(seed)
    _, lab = kmeans2(c, k, minit='++', seed=rng)
    off = np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]) * FEM_H / 2
    out = []
    for j in range(k):
        P = c[lab == j]
        if len(P) >= 4:
            out.append(RB.hull((P[:, None, :] + off[None]).reshape(-1, 3)))
    return out


FEM_H = U.FEM_H


class Rig:
    """a design in MuJoCo (sim=True) and on its stress mesh: each sample's pushes, in the robot's frame, as nodal loads"""
    def __init__(self, sp, mesh, motors, body_hulls=None, sim=True, bumper_k=None):
        import mujoco
        from scipy.spatial import cKDTree
        self.mj = mujoco; spx = dict(sp, tyre_k=TYRE_K, tyre_zeta=TYRE_ZETA); self.mesh = mesh
        if body_hulls is not None:
            spx = dict(spx, hulls=body_hulls); spx.pop('struts', None)
        if sim:
            self.sim = GG.Sim(spx); m = self.sim.m
            self.rid = m.body('robot').id; self.wb = [m.body(f'w{i}').id for i in range(len(sp['wheels']))]; self.root = m.body_rootid[self.wb[0]]
            self.body_geoms = {g for g in range(m.ngeom) if m.geom_bodyid[g] == self.rid}
            self.floor = {g for g in range(m.ngeom) if m.geom_bodyid[g] == 0}
            if bumper_k:                                                  # TPU bumpers (2026-10-29): the body meets the floor on a
                k = bumper_k * 1e3; b = 2 * TYRE_ZETA * math.sqrt(k * sp['mass'] * 1e-3)   # spring, as the tyres do (N/mm)*
                for g in self.body_geoms:
                    m.geom_solref[g] = (-k, -b); m.geom_priority[g] = 1
        self.hub = [np.array([x, y, sp['R']]) for x, y in sp['wheels']]
        self.seats = []                                                   # each wheel's motor seat (wheels in sp's order)
        for x, y in sp['wheels']:
            mo = min(motors, key=lambda mo: math.hypot(mo['x'] - x, mo['y'] - y)); self.seats.append(U.seat(mesh, mo))
        surf = np.where(np.bincount(mesh.enode.ravel(), minlength=mesh.nn) < 8)[0]   # nodes on the surface (fewer than 8 voxels)
        self.surf, self.stree = surf, cKDTree(mesh.X[surf]); self.f6 = np.zeros(6)

    def sample(self):
        """(wheel pushes (n, 6: force N, moment N mm about the hub), body pushes [(nodes, force N)])"""
        mj, m, d = self.mj, self.sim.m, self.sim.d
        mj.mj_rnePostConstraint(m, d)
        Rm = d.xmat[self.rid].reshape(3, 3); xr = d.xpos[self.rid]; c = (Rm.T @ (d.subtree_com[self.root] - xr)) * 1e3
        W = np.zeros((len(self.wb), 6))
        for i, b in enumerate(self.wb):                                    # snap.py's reading: the wheel's push on the robot,
            f = Rm.T @ -d.cfrc_int[b, 3:]; tau = (Rm.T @ -d.cfrc_int[b, :3]) * 1e3   # moved to its hub
            W[i, :3] = f; W[i, 3:] = tau + np.cross(c - self.hub[i], f)
        body = []
        for i in range(d.ncon):
            con = d.contact[i]; g1, g2 = con.geom1, con.geom2
            if not ((g1 in self.body_geoms and g2 in self.floor) or (g2 in self.body_geoms and g1 in self.floor)):
                continue
            mj.mj_contactForce(m, d, i, self.f6); fw = con.frame.reshape(3, 3).T @ self.f6[:3]
            f = Rm.T @ (fw if g2 in self.body_geoms else -fw); p = (Rm.T @ (con.pos - xr)) * 1e3
            body.append((self.patch(p), f, p))
        return W, body

    def patch(self, p):
        """the surface nodes within PATCH of p (the nearest one when none)"""
        nb = self.stree.query_ball_point(p, PATCH)
        return self.surf[nb] if len(nb) else self.surf[[self.stree.query(p)[1]]]

    def loads(self, W, body, remap=False):
        """the sample's nodal loads (nn, 3); remap: each body push spread round its point on this mesh (a fall recorded
        on an earlier shape)"""
        L = np.zeros((self.mesh.nn, 3))
        if remap:
            body = [(self.patch(p), f, p) for _, f, p in body]
        for i, (on, _) in enumerate(self.seats):
            if np.abs(W[i]).sum() > 1e-9:
                L += U.carry(self.mesh, on, self.hub[i], W[i, :3], W[i, 3:])
        for nodes, f, _ in body:
            L[nodes] += f / len(nodes)
        return L


def falls(rig, n=N_FALL, seed=0):
    """each fall's hardest moment (the largest total push, WIN samples' mean): its wheel and body pushes"""
    sim = rig.sim; d = sim.d; rng = np.random.default_rng(seed); out = []
    for k in range(n):
        q = rng.normal(size=4); q /= np.linalg.norm(q)
        sim.place(q, GG.DROP_MM * 1e-3); d.qvel[3:6] = rng.uniform(-1, 1, 3) * GG.SPIN
        ring, best, top = [], None, -1.0
        for _ in range(int(T_FALL / (sim.m.opt.timestep * EVERY))):
            sim.mj.mj_step(sim.m, d, nstep=EVERY); ring.append(rig.sample())
            if len(ring) > WIN:
                ring.pop(0)
            W = sum(r[0] for r in ring) / len(ring); tot = np.linalg.norm(W[:, :3], axis=1).sum() + sum(np.linalg.norm(f) for r in ring for _, f, _ in r[1]) / len(ring)
            if tot > top:
                top = tot; best = (W.copy(), [(nd, f / len(ring), p) for r in ring for nd, f, p in r[1]])
        out.append(dict(W=best[0], body=best[1], total=top))
    return out


def durability(sp, mesh, mass_nodes, motors, body_hulls=None, n=N_FALL, seed=0, cases=None, bumper_k=None):
    """the design dropped n times: each fall's peak stress in the structure (MPa: away from the motors' seats and the
    body's contact patches), the patches' and seats' own peaks, what the worst fall landed on, and the falls (cases).
    cases: falls recorded on an earlier shape, put on this one without dropping it again (growth needs fixed hits: with
    the falls dropped again each round, the hits moved and the peaks wandered 29-41 MPa)"""
    rig = Rig(sp, mesh, motors, body_hulls, sim=cases is None, bumper_k=bumper_k); F = falls(rig, n, seed) if cases is None else cases
    loads = np.stack([rig.loads(f['W'], f['body'], remap=cases is not None) for f in F], axis=2)
    bal, fixed = FE.inertia_relief(mesh, loads, mass_nodes, 1.0); u, it = mesh.solve_mg(bal, fixed, tol=1e-5)
    s = mesh.smooth(mesh.stress(u))
    seat_v = np.any([nr for _, nr in rig.seats], axis=0); spot = np.zeros(mesh.ne, bool)
    P = np.array([p for f in F for _, _, p in f['body']])
    if len(P):                                                          # each contact's patch, read apart
        from scipy.spatial import cKDTree
        spot = cKDTree(P).query(mesh.centres(), distance_upper_bound=PATCH + FEM_H)[0] < PATCH + FEM_H
    keep = ~(seat_v | spot); peaks = s[keep].max(0) if keep.any() else np.zeros(len(F)); w = int(np.argmax(peaks))
    on_body = np.array([sum(np.linalg.norm(fb) for _, fb, _ in f['body']) / max(f['total'], 1e-9) for f in F])
    return dict(peaks=peaks, worst=float(peaks.max()), fall=w, body_share=float(on_body[w]), over=int((peaks > U.ALLOW).sum()),
                broken=int((peaks > U.SIGMA_ULT).sum()), spot=float(s[spot].max()) if spot.any() else 0.0,
                seat=float(s[seat_v].max()) if seat_v.any() else 0.0, push=float(F[w]['total']), stress=s.max(1), keep=keep, iters=it, n=len(F),
                cases=F, heat=np.where(keep, (s > U.ALLOW).mean(1), 0.0))   # each voxel's share of the falls over the allowed
                                                                         # (2026-10-30, Zach: "a heatmap of the breakable parts")


def of_unibody(r, n=N_FALL, seed=0):
    """durability() of a unibody.make() result: its final shape, its body as convex pieces of its own voxels"""
    mesh, mass_nodes, *_ = U.fem_mesh(U.redistance(r['F'] < 0, U.VOX), r['ax'], r['bay'])
    return durability(r['sp'], mesh, mass_nodes, U.motors_of(r['D']), pieces(mesh), n, seed)


def check():
    """a unibody at rest: the pushes sum to its weight, through its wheels; mid-air (the control) they read nothing"""
    q = next(q for q in U.sobol(64, 3) if q['limb'] <= 0.5 and U.design(q) is not None)
    r = U.make(q, rounds=0, log=lambda *_: None)
    mesh, mass_nodes, *_ = U.fem_mesh(U.redistance(r['F'] < 0, U.VOX), r['ax'], r['bay'])
    rig = Rig(r['sp'], mesh, U.motors_of(r['D']), pieces(mesh)); sim = rig.sim; d = sim.d
    sim.place(np.array([1.0, 0, 0, 0]), 0.0005)
    while d.time < 0.6:
        sim.mj.mj_step(sim.m, d)
    W, body = rig.sample(); fz = W[:, 2].sum() + sum(f[2] for _, f, _ in body); wt = r['sp']['mass'] * 1e-3 * 9.81
    ok =abs(fz / ((r['sp']['mass'] - len(W) * r['sp']['m_w']) * 1e-3 * 9.81) - 1) < 0.05
    print(('PASS ' if ok else 'FAIL ') + f"at rest: the pushes on the body sum to {fz:.1f} N up; its weight less the wheels' is "
          f"{(r['sp']['mass'] - len(W) * r['sp']['m_w']) * 1e-3 * 9.81:.1f} N (the robot's {wt:.1f}); on the body itself {sum(f[2] for _, f, _ in body):.2f} N")
    sim.place(np.array([1.0, 0, 0, 0]), 0.3); sim.mj.mj_step(sim.m, d, nstep=50)
    W2, body2 = rig.sample(); tot = np.abs(W2[:, :3]).sum() + sum(np.abs(f).sum() for _, f, _ in body2)
    print(('PASS ' if tot < 0.05 * wt else 'FAIL ') + f'control: mid-air the pushes read {tot:.2f} N')


def bumpers(seed=23823, k=1, ks=(None, 100.0, 30.0)):
    """sheet design k as drawn, dropped with its body hard (MuJoCo's contact) and on TPU bumpers of each stiffness"""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    q = U.sobol(2 * 15, seed)[k - 1]; r = U.make(q, rounds=0, log=lambda *_: None)
    mesh, mass_nodes, *_ = U.fem_mesh(U.redistance(r['F'] < 0, U.VOX), r['ax'], r['bay']); P = pieces(mesh); rows = []
    for bk in ks:
        d = durability(r['sp'], mesh, mass_nodes, U.motors_of(r['D']), P, bumper_k=bk)
        name = 'hard body' if bk is None else f'TPU bumpers {bk:.0f} N/mm'; rows.append((name, d))
        print(f"{name}: falls worst {d['worst']:.1f} MPa, {d['over']} of {d['n']} over "
              f"{U.ALLOW:.1f}, {d['broken']} past {U.SIGMA_ULT:.0f}; the worst fall's push {d['push'] / 1000:.2f} kN, {d['body_share']:.0%} on the body", flush=True)
    fig = plt.figure(figsize=(12, 4.6)); fig.patch.set_facecolor('white')
    a0 = fig.add_axes([0.0, 0.05, 0.36, 0.8]); a0.set_axis_off(); v, f = U.surface(r['F'], r['ax'])
    a0.imshow(U.render(r['sp'], v, f, motors=U.motors_of(r['D']))); a0.set_title(f'sheet design {k}, as drawn', fontsize=9, loc='left')
    a1 = fig.add_axes([0.42, 0.14, 0.55, 0.7]); rng = np.random.default_rng(0)
    for i, (name, d) in enumerate(rows):
        a1.scatter(d['peaks'], i + rng.uniform(-0.15, 0.15, len(d['peaks'])), s=22, color='#3a6ea5', alpha=0.75)
        a1.text(d['worst'] + 0.6, i, f"worst {d['worst']:.0f}; {d['over']} of {d['n']} over", va='center', fontsize=8)
    a1.axvline(U.ALLOW, color='#d9a400', lw=1.2); a1.axvline(U.SIGMA_ULT, color='#c0392b', lw=1.2)
    a1.text(U.ALLOW, len(rows) - 0.45, ' allowed', color='#a07800', fontsize=8); a1.text(U.SIGMA_ULT, len(rows) - 0.45, " PLA's strength", color='#c0392b', fontsize=8)
    a1.set_yticks(range(len(rows))); a1.set_yticklabels([n for n, _ in rows]); a1.set_ylim(-0.6, len(rows) - 0.3)
    a1.set_xlabel('each fall: peak stress in the printed wall, MPa'); a1.spines[['top', 'right']].set_visible(False)
    fig.suptitle(f'{N_FALL} of G1\'s falls from 300 mm, the same design and falls: the body hard (MuJoCo\'s contact) or on TPU bumpers (a spring, as the tyres)',
                 fontsize=10, x=0.01, ha='left')
    p = os.path.join(U.OUT, 'bumpers.png'); fig.savefig(p, dpi=100); print(p)


if __name__ == '__main__':
    if 'check' in sys.argv[1:]:
        check()
    elif 'bumpers' in sys.argv[1:]:
        bumpers()
    else:
        print(__doc__)
