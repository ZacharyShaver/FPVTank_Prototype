"""The tilt servo's wire route, round 1 (2026-10-02): can the wires get through, is there wall round the
hole, and does the stub fit Zach's ball? Material is the generator's own SDFs (tree_parts_b.fork, .stub,
pan_coil_b.drum); his ball is his rev 2 mesh.

1. Passage: a ball of PROBE radius rides the whole route through the stub, the cradle and into the drum's
   bore. PROBE is a bare Dupont crimp beside two jumper wires. Control: the cradle without the route
   must block it.
2. Wall: the thinnest plastic round the hole, marched outward from it. Left out on purpose: the two
   open ends, and the joint where the stub's hole meets the cradle's (a 0.15 gap by design). Control:
   no conduit (WIRE_WALL 0) must read thinner.
3. Stub in his socket: the running gap, measured on his mesh. Control: the old axle (r 9.95), the pin
   that didn't fit. Plus overlap of the stub with the cradle and with his ball: both must be 0.
   Control: a stub 0.4 fatter must overlap his ball.
Round 2 (the pan coil):
4. The drum's core hole and the base's exit: the same probe rides each. Control: the parts without the
   holes must block it.
5. The lane: a 2.8 wire bundle (three ~1.3 jumpers) must clear the floor, the shelf, the drum and the
   wall all the way round. Control: a lane 1.5 shallower must fail.
6. Walls round both holes, away from their mouths.

    python head-v2/checks/wire_route.py
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import numpy as np
from vox import load_stl, voxelize
import slices
import tree_parts_b as B, pan_coil_b as P

PROBE = 2.2                        # crimp ~1.8 across its corners + two 1.3 wires, half of ~4.4
WALL_MIN = 0.6
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
        if c[1] > -19.0 or (c[2] < 14.5 and c[1] > -12.8) or 38.0 < c[2] < 41.0 or not z0 <= c[2] <= z1:
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


def hole_walls(L, fn, keep):
    """Thinnest wall round a hole of radius P.WIRE_R along L, at the points keep() accepts."""
    worst = (9.9, None); th = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for i in range(1, len(L) - 1):
        c = L[i]
        if not keep(c):
            continue
        t = L[i + 1] - L[i - 1]; t /= np.linalg.norm(t)
        a = np.cross(t, [0, 0, 1.0]); a = a if np.linalg.norm(a) > 0.1 else np.cross(t, [1.0, 0, 0])
        a /= np.linalg.norm(a); b = np.cross(t, a); d = np.cos(th)[:, None] * a + np.sin(th)[:, None] * b
        for w in np.arange(0.1, 3.01, 0.1):
            if (at(fn, c + (P.WIRE_R + w) * d) > 0).any():
                if w < worst[0]:
                    worst = (w, np.round(c, 1).tolist())
                break
    return worst


def round2():
    bad = 0
    print('4. round 2: the drum\'s core hole and the base\'s exit, probe r %.1f' % PROBE)
    d1 = probe(P.DRUM_WIRE, [P.drum]).min()
    e = P.BASE_WIRE[np.hypot(P.BASE_WIRE[:, 0], P.BASE_WIRE[:, 1]) > 21.0]   # inside r 21 it is the lane
    d2 = probe(e, [P.base]).min()
    print('   drum hole %.2f, base exit %.2f   %s' % (d1, d2, 'PASS' if min(d1, d2) >= PROBE else '<== BLOCKED'))
    bad += min(d1, d2) < PROBE
    hole = P.wire_hole; P.wire_hole = lambda p, line, r=P.WIRE_R: np.full(np.broadcast(*p).shape, 1e3)
    c1 = probe(P.DRUM_WIRE, [P.drum]).min(); c2 = probe(e, [P.base]).min(); P.wire_hole = hole
    print('   control, no holes: drum %.2f, base %.2f   %s' % (c1, c2, 'blocked, good' if max(c1, c2) < PROBE else '<== CONTROL PASSES'))
    bad += max(c1, c2) >= PROBE

    bundle = 1.4
    print('5. round 2: the lane, a %.1f bundle all the way round (lane %.1f tall, r %.1f..%.1f)'
          % (2 * bundle, P.LANE_H, P.DRUM_R, P.LANE_R))
    a = np.radians(np.arange(0, 360, 2.0))
    ring = lambda R, z: np.stack([R * np.cos(a), R * np.sin(a), np.full_like(a, z)], 1)
    worst = min(probe(ring(R, P.LANE_ZC), [P.base, P.drum]).min()
                for R in (P.DRUM_R + bundle + 0.1, 16.5, P.LANE_R - bundle - 0.1))
    print('   tightest %.2f (needs %.1f)   %s' % (worst, bundle, 'CLEAR' if worst >= bundle else '<== PINCHED'))
    bad += worst < bundle
    z0 = P.LANE_Z0; P.LANE_Z0 = z0 + 1.5
    c = probe(ring(16.5, P.LANE_ZC), [P.base, P.drum]).min(); P.LANE_Z0 = z0
    print('   control, lane 1.5 shallower: %.2f   %s' % (c, 'pinched, good' if c < bundle else '<== CONTROL CLEAR'))
    bad += c >= bundle

    print('6. round 2: walls round the holes, away from their mouths')
    w1 = hole_walls(P.DRUM_WIRE, P.drum, lambda c: c[2] < -4.5 and np.hypot(c[0], c[1]) < 9.2)
    w2 = hole_walls(P.BASE_WIRE, P.base, lambda c: 22.9 < np.hypot(c[0], c[1]) < 24.5)
    print('   drum %.1f at %s, base %.1f at %s   %s' % (w1[0], w1[1], w2[0], w2[1], 'ok' if min(w1[0], w2[0]) >= WALL_MIN else '<== THIN'))
    bad += min(w1[0], w2[0]) < WALL_MIN
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
    keep = B.WIRE_WALL; B.WIRE_WALL = 0.0
    w0, where0 = walls(20.0, 34.0); B.WIRE_WALL = keep
    print('   conduit zone (Z 20-34) %.1f mm; control, no conduit: %.1f mm at %s   %s'
          % (wc, w0, np.round(where0, 1) if where0 is not None else '-', 'thinner, good' if w0 < wc else '<== CONTROL NOT THINNER'))
    bad += w0 >= wc

    print('3. the stub in his ball')
    r, T = socket_r()
    print('   his socket r %.2f: stub r %.2f -> gap %.2f;  control, old axle r %.2f -> gap %.2f (the pin that didn\'t fit)'
          % (r, B.STUB_R, r - B.STUB_R, B.AXLE_R, r - B.AXLE_R))
    bad += (r - B.STUB_R) < 0.15
    lo, hi = (-19, B.POD_M_Y1 - 1.5, B.H - 19), (19, B.STUB_Y1 + 1, B.H + 19)
    in_fork = lambda g, p: B.fork(p) < 0
    in_ball = lambda g, p: voxelize(T, g)
    v1 = overlap(B.stub, lo, hi, in_fork); v2 = overlap(B.stub, lo, hi, in_ball)
    print('   stub vs cradle %.2f mm3, stub vs his ball %.2f mm3' % (v1, v2))
    bad += (v1 > 0.5) + (v2 > 0.5)
    keep = B.STUB_R; B.STUB_R = keep + 0.4
    v3 = overlap(B.stub, lo, hi, in_ball); B.STUB_R = keep
    print('   control, stub 0.4 fatter vs his ball: %.2f mm3   %s' % (v3, 'overlaps, good' if v3 > 0.5 else '<== CONTROL READS 0'))
    bad += v3 <= 0.5
    bad += round2()
    print('\n%s' % ('ROUTE OK' if not bad else '<== %d problem(s)' % bad))
    sys.exit(1 if bad else 0)
