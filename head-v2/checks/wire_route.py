"""The tilt servo's wire route, round 1 (2026-10-02): can the wires get through, is there wall round the
hole, and does the stub fit Zach's ball? Material is the generator's own SDFs (tree_parts_b.fork, .stub,
pan_coil_b.drum); his ball is his rev 2 mesh.

1. Passage: a ball of PROBE radius rides the whole route through the stub, the cradle and into the drum's
   bore. PROBE is a bare Dupont crimp beside two jumper wires. Control: the cradle without the route
   must block it.
2. Wall: the thinnest plastic round the hole, marched outward from it. Left out on purpose: the two
   open ends, and the joint where the stub's hole meets the cradle's at the collar's bore (a 0.15 gap
   by design). Control:
   no conduit (WIRE_WALL 0, no blend) must read thinner.
3. The -Y bearing joint: his ball with the 6704 cup (fixes/ball_minus_cup.py), the stub through the
   bearing. Stub vs cradle and vs the ball: 0 (control: a stub fatter than the lip's hole must hit the
   ball). The cup vs the camera board: 0 (control: a cup 1.5 deeper). Each ring of the bearing may touch
   only what turns with it, and touching reads 0 overlap, so those rows measure the GAP (at least
   GAP_MIN). The outer ring turns with the ball: its gap to the stub (control: a shoulder out to the
   outer ring) and to the cradle (control: the bearing 1.0 further out). The inner ring is fixed on the
   stub: its gap to the ball (control: a lip hole inside the inner ring).
Round 2 (the pan coil):
4. The drum's core hole and the base's exit: the same probe rides each. Control: the parts without the
   holes must block it.
5. The lane: a 2.8 wire bundle (three ~1.3 jumpers) must clear the floor, the shelf, the drum and the
   wall all the way round. Control: a lane 1.5 shallower must fail.
6. Walls round both holes, away from their mouths.
7. The handover between them (set 5): the widest round bundle that gets from the cradle's hole to the
   drum's hole past the ribbon, by flood fill. With the ribbon centred it must be 2.8. With the ribbon off
   centre (the cradle's groove lets it move 3), the drum must not be the limit. Controls: set 4's drum
   (no notch) and the first notch (r 12.3, ribbon 3 off) must block it in the drum; with no ribbon at
   all, set 4's drum must let it through (the search works).
   Set 6 (2026-10-03): the bore's floor is a cone and the hole starts at its point, so the target is the
   hole's top (0, 0, -13). Below the old floor the ribbon is drawn turning flat toward its slot at +X, which
   closes the +X side under it (the safe guess). Added control: set 5's flat floor with the new hole blocks.
   Set 8 (2026-10-09): the wires go down a straight vertical hole beside the cone and out through an open groove
   in the drum's underside. Row 4 probes the hole, and the groove with the lane's bundle (control: no groove);
   row 7's target is 1 mm down the hole (control: set 6's drum, which has no hole there).

    python head-v2/checks/wire_route.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from vox import load_stl, voxelize
import slices
import tree_parts_b as B, pan_coil_b as P
sys.path.insert(0, config.FIXES)
import ball_minus_cup as CUP
import campost_rev2 as R2

PROBE = 2.2                        # crimp ~1.8 across its corners + two 1.3 wires, half of ~4.4
WALL_MIN = 0.6
GAP_MIN = 0.3                      # a turning bearing ring to anything fixed
BALL_MINUS = os.path.join(config.REPO, 'head-v2', 'fusion', 'rev2-2026-09-27', 'ball_minus_revised_27.stl')


def at(fn, Q):
    return fn((Q[:, 0], Q[:, 1], Q[:, 2]))


def passage():
    """True clearance from each point of the route to the nearest material (cradle, stub, drum): spheres of
    points round it, growing 0.1 at a time. Not the SDF values: the drum's is a bound, not a distance
    (it read 0.70 where the nearest drum is 3.6 away)."""
    L = B.WIRE_LINE
    k = np.arange(300) + 0.5; ph = np.arccos(1 - 2 * k / 300); th = np.pi * (1 + 5 ** 0.5) * k
    D = np.stack([np.cos(th) * np.sin(ph), np.sin(th) * np.sin(ph), np.cos(ph)], 1)
    out = np.full(len(L), PROBE + 0.5)
    for i, c in enumerate(L):
        for r in np.arange(0.1, PROBE + 0.51, 0.1):
            Q = c + r * D
            if ((at(B.fork, Q) < 0) | (at(B.stub, Q) < 0) | (at(P.drum, Q) < 0)).any():
                out[i] = r - 0.1; break
    return out


def walls(z0=-99.0, z1=99.0):
    """Thinnest wall round the hole between heights z0 and z1, outside the ends and the stub joint."""
    L = B.WIRE_LINE; worst = (9.9, None)
    th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for i in range(1, len(L) - 1):
        c = L[i]
        joint = c[1] < -24.0 and abs(np.hypot(c[0], c[2] - B.H) - B.STUB_BORE_R) < B.WIRE_R + 1.0
        if c[1] > -19.0 or (c[2] < 14.5 and c[1] > -12.8) or joint or not z0 <= c[2] <= z1:
            continue
        t = L[i + 1] - L[i - 1]; t /= np.linalg.norm(t)
        a = np.cross(t, [1.0, 0, 0]); a = a if np.linalg.norm(a) > 0.1 else np.cross(t, [0, 1.0, 0])
        a /= np.linalg.norm(a); b = np.cross(t, a)
        d = np.cos(th)[:, None] * a + np.sin(th)[:, None] * b
        for w in np.arange(0.1, 3.01, 0.1):
            Q = c + (B.WIRE_R + w) * d
            air = (at(B.fork, Q) > 0) & (at(B.stub, Q) > 0)
            if air.any():
                if w < worst[0]:
                    worst = (w, c)
                break
    return worst


def probe(L, fns):
    """Like passage(), for any centreline against any parts."""
    k = np.arange(300) + 0.5; ph = np.arccos(1 - 2 * k / 300); th = np.pi * (1 + 5 ** 0.5) * k
    D = np.stack([np.cos(th) * np.sin(ph), np.sin(th) * np.sin(ph), np.cos(ph)], 1)
    out = np.full(len(L), 3.0)
    for i, c in enumerate(L):
        for r in np.arange(0.05, 3.01, 0.05):
            if any((at(f, c + r * D) < 0).any() for f in fns):
                out[i] = r - 0.05; break
    return out


def hole_walls(L, fn, keep, hole=None):
    """Thinnest wall round a hole of radius P.WIRE_R along L, at the points keep() accepts. `hole`: the hole's own
    shape where it isn't round (set 7's exit hole has a pointed top), so air inside it doesn't count as outside."""
    worst = (9.9, None); th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for i in range(1, len(L) - 1):
        c = L[i]
        if not keep(c):
            continue
        t = L[i + 1] - L[i - 1]; t /= np.linalg.norm(t)
        a = np.cross(t, [0, 0, 1.0]); a = a if np.linalg.norm(a) > 0.1 else np.cross(t, [1.0, 0, 0])
        a /= np.linalg.norm(a); b = np.cross(t, a); d = np.cos(th)[:, None] * a + np.sin(th)[:, None] * b
        for w in np.arange(0.1, 3.01, 0.1):
            q = c + (P.WIRE_R + w) * d
            out = at(fn, q) > 0
            if hole is not None:
                out &= at(hole, q) > 0
            if out.any():
                if w < worst[0]:
                    worst = (w, np.round(c, 1).tolist())
                break
    return worst


def round2():
    bad = 0
    print('4. round 2: the drum\'s core hole and the base\'s exit, probe r %.1f' % PROBE)
    # set 8: the straight hole takes the probe; the groove under the drum is open, and the wires lie in it like
    # the lane's bundle, between its roof and the base's lane floor
    drum_line = P.DROP_LINE if P.STRAIGHT_WIRE else P.DRUM_WIRE
    d1 = probe(drum_line, [P.drum]).min()
    e = P.BASE_WIRE[np.hypot(P.BASE_WIRE[:, 0], P.BASE_WIRE[:, 1]) > 21.0]   # inside r 21 it is the lane
    d2 = probe(e, [P.fixed]).min()               # set 7: with the shelf ring in place over the mouth
    print('   drum hole %.2f, base exit %.2f   %s' % (d1, d2, 'PASS' if min(d1, d2) >= PROBE else '<== BLOCKED'))
    bad += min(d1, d2) < PROBE
    hole = P.wire_hole; P.wire_hole = lambda p, line, r=P.WIRE_R: np.full(np.broadcast(*p).shape, 1e3)
    straight = P.straight_wire; P.straight_wire = lambda p: np.full(np.broadcast(*p).shape, 1e3)
    c1 = probe(drum_line, [P.drum]).min(); c2 = probe(e, [P.fixed]).min(); P.wire_hole = hole; P.straight_wire = straight
    print('   control, no holes: drum %.2f, base %.2f   %s' % (c1, c2, 'blocked, good' if max(c1, c2) < PROBE else '<== CONTROL PASSES'))
    bad += max(c1, c2) >= PROBE
    if P.STRAIGHT_WIRE:
        g = P.GROOVE_LINE[np.hypot(P.GROOVE_LINE[:, 0], P.GROOVE_LINE[:, 1]) < P.DRUM_R + 0.5]
        g1 = probe(g, [P.drum, P.fixed]).min()
        P.straight_wire = lambda p: P.cyl_z(p, P.DROP_XY[0], P.DROP_XY[1], P.WIRE_R, P.LANE_Z0 - 0.5, P.DROP_Z1)
        c3 = probe(g, [P.drum, P.fixed]).min()
        print('   set 8 groove under the drum, a %.1f bundle: %.2f   %s; control, no groove: %.2f   %s'
              % (2 * BUNDLE, g1, 'CLEAR' if g1 >= BUNDLE else '<== PINCHED', c3, 'pinched, good' if c3 < BUNDLE else '<== CONTROL CLEAR'))
        bad += (g1 < BUNDLE) + (c3 >= BUNDLE)
        P.straight_wire = straight

    bundle = 1.4
    print('5. round 2: the lane, a %.1f bundle all the way round (lane %.1f tall, r %.1f..%.1f)'
          % (2 * bundle, P.LANE_H, P.DRUM_R, P.LANE_R))
    a = np.radians(np.arange(0, 360, 2.0))
    ring = lambda R, z: np.stack([R * np.cos(a), R * np.sin(a), np.full_like(a, z)], 1)
    worst = min(probe(ring(R, P.LANE_ZC), [P.fixed, P.drum]).min()
                for R in (P.DRUM_R + bundle + 0.1, 16.5, P.LANE_R - bundle - 0.1))
    print('   tightest %.2f (needs %.1f)   %s' % (worst, bundle, 'CLEAR' if worst >= bundle else '<== PINCHED'))
    bad += worst < bundle
    z0 = P.LANE_Z0; P.LANE_Z0 = z0 + 1.5
    c = probe(ring(16.5, P.LANE_ZC), [P.fixed, P.drum]).min(); P.LANE_Z0 = z0
    print('   control, lane 1.5 shallower: %.2f   %s' % (c, 'pinched, good' if c < bundle else '<== CONTROL CLEAR'))
    bad += c >= bundle

    print('6. round 2: walls round the holes, away from their mouths')
    # set 6: away from the cone (above Z -19.3 the hole is the cone's point) and inside r 6.5 (past it the
    # hole breaks through the drum's underside into the lane on purpose)
    if P.STRAIGHT_WIRE:   # set 8: the straight hole, below where it leaves the cone (Z -8.6) and above the groove
        w1 = hole_walls(P.DROP_LINE, P.drum, lambda c: -21.5 < c[2] < -11.0)
    else:
        w1 = hole_walls(P.DRUM_WIRE, P.drum, lambda c: c[2] < -19.3 and np.hypot(c[0], c[1]) < 6.5)
    # set 7: the ring's room (above the ledge, inside r 22.65) opens the hole's top out to r 23.6, so the mouth
    # ends at the skirt and the walls start after it; the hole's pointed top is hole, not outside
    w2 = hole_walls(P.BASE_WIRE, P.base, lambda c: (23.8 if P.INSERT else 22.9) < np.hypot(c[0], c[1]) < 24.5,
                    hole=(lambda q, f=True: P.teardrop_hole(q, P.BASE_WIRE)) if P.INSERT else None)
    print('   drum %.1f at %s, base %.1f at %s   %s' % (w1[0], w1[1], w2[0], w2[1], 'ok' if min(w1[0], w2[0]) >= WALL_MIN else '<== THIN'))
    bad += min(w1[0], w2[0]) < WALL_MIN
    bad += handover()
    return bad


RIBBON_T = 0.2
BUNDLE = 1.4                        # three wires, ~2.8 across
RIBBON_PLAY = 3.0                   # the cradle's 22 groove round the 16 ribbon: it can sit 3 off centre
# Found 2026-10-02 (after rounds 1 and 2 were built): rows 1 and 4 probe the cradle's hole and the drum's
# hole each on its own, so nothing tested the bore between them, or the ribbon. The cradle's hole lets the
# wires out IN FRONT of the ribbon and the drum's hole is BEHIND it. Row 7 floods the space between them
# instead of trusting a drawn line: the widest round bundle that gets from one hole to the other.
FL_ST = 0.2
FL_G = [np.arange(-14.0, 6.2, FL_ST), np.arange(-15.4, 4.2, FL_ST), np.arange(-14.6, 17.2, FL_ST)]
_FL = {}


def _flood_grid():
    """The voxel grid over the bore's top, the cradle sampled on it once, and the ribbon's path. The ribbon
    goes down the cradle's groove, then straight down X 0 to the bore floor: below Z 5 it really turns
    toward the slot at +X, which only frees space on the side the wires go."""
    if not _FL:
        X, Y, Z = np.meshgrid(*FL_G, indexing='ij')
        k = Z >= 9.5
        cr = np.zeros(X.shape, bool); cr[k] = B.fork((X[k], Y[k], Z[k])) < 0
        R = np.array(B.bezier(B.TROUGH_PATH, 300))
        R = np.vstack([R, [[0.0, z] for z in np.arange(R[-1, 1] - 0.1, P.CH_Z1 - 0.5, -0.1)]])
        R = np.vstack([R, [[x, P.CH_Z1 - 0.5] for x in np.arange(0.1, FL_G[0][-1] + 0.1, 0.1)]])   # set 6: on to +X
        XZ = np.stack(np.meshgrid(FL_G[0], FL_G[2], indexing='ij'), -1)
        d2 = np.min(np.linalg.norm(XZ[:, :, None, :] - R[None, None], axis=-1), axis=-1)
        _FL.update(X=X, Y=Y, Z=Z, cradle=cr, ribbon_xz=d2 <= RIBBON_T / 2 + 0.15)   # thick enough to voxelize
    return _FL


def TARGET():
    """Set 6: the hole's top at the cone's point. Set 8: 1 mm down the straight hole, under its mouth."""
    if P.STRAIGHT_WIRE:
        return (P.DROP_XY[0], P.DROP_XY[1], P.CONE_APEX_Z + P.DROP_R / np.tan(np.radians(P.CONE_DEG)) - 1.0)
    return P.DRUM_WIRE[0]


def widest(ribbon_dy=0.0, ribbon=True, target=None):
    """The widest round bundle that gets from the cradle's hole (Z 13) to the drum's hole (Z -4.5): a flood
    fill on a 0.2 mm clearance map of the cradle, the drum and the ribbon (moved ribbon_dy along Y).
    Returns its radius and where it is tightest."""
    from scipy import ndimage as nd
    g = _flood_grid(); X, Y, Z = g['X'], g['Y'], g['Z']
    solid = g['cradle'].copy(); k = Z <= 11.6
    solid[k] |= P.drum((X[k], Y[k], Z[k])) < 0
    if ribbon:
        solid |= g['ribbon_xz'][:, None, :] & (np.abs(Y - ribbon_dy) <= 8.0)
    for ax in range(3):                                   # the box's faces are walls
        solid[(slice(None),) * ax + (0,)] = True; solid[(slice(None),) * ax + (-1,)] = True
    E = nd.distance_transform_edt(~solid) * FL_ST - FL_ST / 2      # low by up to half a voxel: the safe side
    near = lambda q: tuple(int(np.argmin(np.abs(FL_G[i] - q[i]))) for i in range(3))
    s = near(B.WIRE_LINE[np.argmin(np.abs(B.WIRE_LINE[:, 2] - 13.0))])
    e = near(TARGET() if target is None else target)               # the drum hole's top
    st = np.ones((3, 3, 3), bool)
    lo, hi = 0.0, min(E[s], E[e])
    for _ in range(14):
        t = (lo + hi) / 2; L = nd.label(E >= t, structure=st)[0]
        lo, hi = (t, hi) if L[s] and L[s] == L[e] else (lo, t)
    # where: the patch at the bottleneck's level that touches both sides once it closes
    L = nd.label(E >= lo, structure=st)[0]
    N = (L == L[s]) & (E < lo + 0.06)
    Lh = nd.label(E >= lo + 0.06, structure=st)[0]
    side = lambda i: nd.binary_dilation(Lh == Lh[i], st, iterations=2) if Lh[i] else np.zeros(L.shape, bool)
    a, b = side(s), side(e)
    LN, n = nd.label(N, structure=st); where = None
    for i in range(1, n + 1):
        m = LN == i
        if (m & a).any() and (m & b).any():
            where = np.round([X[m].mean(), Y[m].mean(), Z[m].mean()], 1); break
    return lo, where


def handover():
    print('7. the handover, cradle hole -> drum hole (set 8: into the straight hole): the widest bundle that gets through (flood fill)')
    # the cradle's inside is the same printed or blended (cradle_blend.py changes only its outside)
    place = lambda q: 'in the cradle' if q is not None and q[2] > P.BASE_Z else 'in the drum'
    bad = 0
    for dy, name in ((0.0, 'ribbon centred'), (-RIBBON_PLAY / 2, 'ribbon 1.5 toward -Y'),
                     (-RIBBON_PLAY, 'ribbon 3.0 toward -Y (its play)')):
        w, q = widest(dy)
        ok = w >= BUNDLE if dy == 0 else (w >= BUNDLE or place(q) == 'in the cradle')
        print('   %-34s %.1f mm, tightest at %s %s   %s' % (name, 2 * w, q, place(q),
              ('CLEAR' if w >= BUNDLE else 'the drum is not the limit') if ok else '<== BLOCKED IN THE DRUM'))
        bad += not ok
    P.NOTCH = False
    w, q = widest(0.0); P.NOTCH = True
    print('   control, set 4 drum (no notch): %.1f %s   %s' % (2 * w, place(q), 'blocked, good' if w < BUNDLE else '<== CONTROL CLEAR'))
    bad += w >= BUNDLE
    keep = P.NOTCH_R; P.NOTCH_R = 12.3
    w, q = widest(-RIBBON_PLAY); P.NOTCH_R = keep
    print('   control, the first notch (r 12.3), ribbon 3.0 toward -Y: %.1f %s   %s'
          % (2 * w, place(q), 'blocked, good' if w < BUNDLE and place(q) == 'in the drum' else '<== CONTROL CLEAR'))
    bad += not (w < BUNDLE and place(q) == 'in the drum')
    if P.STRAIGHT_WIRE:   # set 8: set 6's drum has no hole where the straight one starts
        t = TARGET(); P.STRAIGHT_WIRE = False
        w, q = widest(0.0, target=t); P.STRAIGHT_WIRE = True
        print("   control, set 6's drum, to where set 8's hole starts: %.1f   %s" % (2 * w, 'blocked, good' if w < BUNDLE else '<== CONTROL CLEAR'))
    else:
        P.CONE = False; funnel = P.wire_funnel           # (set 5's funnel sat on set 5's hole, so it stays off)
        P.wire_funnel = lambda p: np.full(np.broadcast(*p).shape, 1e3)
        w, q = widest(0.0); P.CONE = True; P.wire_funnel = funnel
        print("   control, set 5's flat floor with the new hole: %.1f   %s" % (2 * w, 'blocked, good' if w < BUNDLE else '<== CONTROL CLEAR'))
    bad += w >= BUNDLE
    P.NOTCH = False
    w, q = widest(0.0, ribbon=False); P.NOTCH = True
    print('   positive control, set 4 drum with no ribbon: %.1f   %s' % (2 * w, 'gets through, good' if w >= BUNDLE else '<== SEARCH BROKEN'))
    bad += w < BUNDLE
    # the cone's wall to the drum face the ribbon wraps (r DRUM_R, band Z BAND_Z0..BAND_Z1): thinnest at its rim
    zs = np.arange(P.BAND_Z0, min(P.BAND_Z1, P.BORE_Z0) + 0.01, 0.1)
    wall = (P.DRUM_R - np.minimum(P.BORE_R, (zs - P.CONE_APEX_Z) * np.tan(np.radians(P.CONE_DEG)))).min()
    print('   cone to the drum face: %.1f mm   %s' % (wall, 'ok' if wall >= 1.0 else '<== THIN'))
    bad += wall < 1.0
    return bad


def socket_r():
    T = load_stl(BALL_MINUS); rs = []
    for y in np.arange(-24.2, -18.8, 0.5):
        m, u, v, _ = slices.slice2d(T, 1, y, (-14, 38), (14, 66), h=0.05)
        U, V = np.meshgrid(u, v, indexing='ij'); rs.append(np.hypot(U, V - B.H)[m].min())
    return min(rs), T


def overlap(fn_a, lo, hi, inside_b, step=0.2):
    g = [np.arange(lo[i], hi[i], step) for i in range(3)]
    X, Y, Z = np.meshgrid(*g, indexing='ij')
    a = fn_a((X, Y, Z)) < 0
    return np.count_nonzero(a & inside_b(g, (X, Y, Z))) * step ** 3


if __name__ == '__main__':
    bad = 0
    print('1. passage, probe r %.1f (bare crimp beside two wires)' % PROBE)
    c = passage(); i = np.argmin(c)
    print('   tightest clearance %.2f at %s   %s' % (c[i], np.round(B.WIRE_LINE[i], 1), 'PASSES' if c[i] >= PROBE else '<== BLOCKED'))
    bad += c[i] < PROBE
    B.WIRE_ROUTE = False
    c0 = passage().min(); B.WIRE_ROUTE = True
    print('   control, cradle without the route: %.2f   %s' % (c0, 'blocked, good' if c0 < PROBE else '<== CONTROL PASSES'))
    bad += c0 >= PROBE

    print('2. wall round the hole (ends and the stub joint left out)')
    w, where = walls()
    print('   thinnest %.1f mm at %s   %s' % (w, np.round(where, 1) if where is not None else '-', 'ok' if w >= WALL_MIN else '<== THIN'))
    bad += w < WALL_MIN
    wc, _ = walls(20.0, 34.0)                      # where the conduit carries the wall
    keep = B.WIRE_WALL, B.CONDUIT_K                # no conduit and no blend: the bare wall (the 6 mm blend
    B.WIRE_WALL, B.CONDUIT_K = 0.0, 1e-3           # alone, round the bare hole, still thickens it to 0.9)
    w0, where0 = walls(20.0, 34.0); B.WIRE_WALL, B.CONDUIT_K = keep
    print('   conduit zone (Z 20-34) %.1f mm; control, no conduit: %.1f mm at %s   %s'
          % (wc, w0, np.round(where0, 1) if where0 is not None else '-', 'thinner, good' if w0 < wc else '<== CONTROL NOT THINNER'))
    bad += w0 >= wc

    print('3. the -Y bearing joint (6704 in his ball, stub through it)')
    T = load_stl(BALL_MINUS)
    cam = load_stl(os.path.join(config.CAMERA, 'camera_dummy_centred.stl')) + np.array([2.5, R2.LENS_DY, R2.LENS_DZ])
    st = 0.1
    g = [np.arange(-17, 17, st), np.arange(-26.0, -16.5, st), np.arange(B.H - 17, B.H + 17, st)]
    X, Y, Z = np.meshgrid(*g, indexing='ij'); p = (X, Y, Z)
    his = voxelize(T, g)
    ball = lambda hole_r=CUP.LIP_HOLE_R, y1=CUP.LIP_Y1: (his | (CUP.sdf_add(p, y1) < 0)) & ~(CUP.sdf_cut(p, hole_r) < 0)
    v = lambda m: np.count_nonzero(m) * st ** 3
    stub, fork = B.stub(p) < 0, B.fork(p) < 0
    inner_d, outer_d = CUP.bearing_rings(p)

    def gap(ring_d, other):
        # smallest growth of the ring that reaches the other part. The ring's field is a bound (max of its
        # radial and axial distances), so this reads LOW at corners: on the safe side for a minimum.
        for gp in np.arange(0.0, 3.0, 0.05):
            if (other & (ring_d < gp)).any():
                return gp
        return 3.0
    zero_rows = [('stub vs cradle', v(stub & fork), None),
                 ('stub vs ball', v(stub & ball()), ('stub as fat as the lip hole + 0.2', 'c1')),
                 ('cup vs camera board', v(ball() & ~his & voxelize(cam, g)), ('cup 1.5 deeper', 'c4'))]
    keep = B.STUB_R; B.STUB_R = CUP.LIP_HOLE_R + 0.2
    c1 = v((B.stub(p) < 0) & ball()); B.STUB_R = keep
    c4 = v(ball(y1=CUP.LIP_Y1 + 1.5) & ~his & voxelize(cam, g))
    cv = {'c1': c1, 'c4': c4}
    for name, val, ctrl in zero_rows:
        bad += val > 0.5
        line = '   %-30s %6.2f mm3' % (name, val)
        if ctrl:
            bad += cv[ctrl[1]] <= 0.5
            line += '   control, %s: %.2f %s' % (ctrl[0], cv[ctrl[1]], '(good)' if cv[ctrl[1]] > 0.5 else '<== CONTROL READS 0')
        print(line)
    keep = B.STUB_BODY_R; B.STUB_BODY_R = CUP.OUT_R0 + 0.3
    g1c = gap(outer_d, B.stub(p) < 0); B.STUB_BODY_R = keep
    g3c = gap(CUP.bearing_rings((X, Y + 1.0, Z))[1], fork)        # the bearing 1.0 further out (toward -Y)
    g2c = gap(inner_d, ball(hole_r=CUP.IN_R1 - 0.3))
    for name, val, cn, c in (('outer ring (turns) to stub', gap(outer_d, stub), 'shoulder out to the outer ring', g1c),
                             ('outer ring (turns) to cradle', gap(outer_d, fork), 'bearing 1.0 further out', g3c),
                             ('inner ring (fixed) to ball', gap(inner_d, ball()), 'lip hole inside the inner ring', g2c)):
        bad += val < GAP_MIN; bad += c >= GAP_MIN
        print('   %-30s gap %4.2f mm %s  control, %s: %.2f %s' % (name, val, '' if val >= GAP_MIN else '<== RUBS',
              cn, c, '(good)' if c < GAP_MIN else '<== CONTROL CLEAR'))
    bad += round2()
    print('\n%s' % ('ROUTE OK' if not bad else '<== %d problem(s)' % bad))
    sys.exit(1 if bad else 0)
