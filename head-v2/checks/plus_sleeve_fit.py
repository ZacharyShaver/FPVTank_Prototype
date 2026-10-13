"""The +Y hub as a sleeve (fixes/plus_sleeve.py): does the ball go in without bending the arm, does the sleeve
fit where it sits, and can it and the 6704 get there? Each row has its negative control.

  1  drop: lower the whole ball straight down into the cradle; on every vertical line through it, no cradle
     at or above its lowest point. Control: the ball with the hub on hits the +Y collar.
  2  both press sleeves in place vs the cut ball, post v3 and the 6704's outer ring (exact OCC); the inner ring
     overlaps by the press. Controls: 0.3 deeper; a lip wide enough to reach the outer ring.
  3  the sleeves vs his MG90S where post v3 seats it, and vs the cradle (voxels, 0.1). Controls: no notch; r 10.6
     through the collar's shoulder.
  4  way in: the sleeve with the 6704 pressed on slides in from +Y, the post not yet on. Control: hub-on ball.
  5  the 6704's turning (inner) ring vs the cradle: reported, not fixed (the collar's shoulder).
  6  plate left under the socket's floor. Control: the first, 2.0 deep socket (0.19).
  7  the gaps where the sleeve meets the ball: 0.15 a side (his slide rule), 0.3 to the floor.
  8  the camera board to the sleeve.
  9  post v3 slides on last through the sleeve. Control: a sleeve with a r 7.5 bore.

    python head-v2/checks/plus_sleeve_fit.py      # after fixes/plus_sleeve.py; about 1 min
"""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import export as E
from occ_load import vol
from kit import cyl, cut, common, moved
from vox import load_stl, _scan

H = 52.0
O = os.path.join(config.OUT, 'plus-sleeve')
TREE = os.path.join(config.REPO, 'head-v2', 'generator', 'tree-parts-b', 'fusion')


def obj(p):
    V, F = [], []
    for l in open(p):
        if l.startswith('v '): V.append([float(x) for x in l.split()[1:4]])
        elif l.startswith('f '): F.append([int(x.split('/')[0]) - 1 for x in l.split()[1:4]])
    V = np.array(V); return V[np.array(F)]


def ring(r0, r1, y0, y1):
    return cut(cyl('y', (0, H), r1, y0, y1), cyl('y', (0, H), r0, y0 - 1, y1 + 1))


def sweep_hits(mover, obstacles, axis, sign):
    """lines along `axis` where an obstacle lies beyond the mover's leading point, coming from sign * inf"""
    has = mover.any(axis)
    if sign > 0:   # comes from +inf: sweeps everything from its lowest index up
        first = np.where(has, mover.argmax(axis), 10**6)
        idx = np.arange(mover.shape[axis]).reshape([-1 if d == axis else 1 for d in range(3)])
        return (obstacles & (idx >= np.expand_dims(first, axis) + 1)).any(axis)
    raise ValueError


if __name__ == '__main__':
    cradle = obj(os.path.join(TREE, 'fork.obj'))
    minus = load_stl(config.out('rev2', '_fig_ball_minus_cup.stl'))
    hub_on = load_stl(os.path.join(O, 'ball_plus_rev2.stl'))
    hub_off = load_stl(os.path.join(O, 'ball_plus_sleeve.stl'))
    fails = 0

    # 1 drop
    h = 0.25
    g = (np.arange(-33, 33, h) + h / 2, np.arange(-33, 33, h) + h / 2, np.arange(15, 90, h) + h / 2)
    C = _scan(cradle, 2, g)
    X, Y = np.meshgrid(g[0], g[1], indexing='ij')
    res = {}
    for name, T in (('hub on (control)', hub_on), ('sleeve', hub_off)):
        cols = sweep_hits(_scan(np.concatenate([T, minus]), 2, g), C, 2, +1)   # it comes down from +Z
        collar = cols & (np.abs(Y) > 20) & (np.abs(X) < 14)
        back = cols & (X < -29)
        res[name] = collar.sum()
        print('1 drop, %-17s columns hitting a collar: %4d (Y %s) | ribbon track lip at the back: %d' % (
            name, collar.sum(), '%.1f..%.1f' % (Y[collar].min(), Y[collar].max()) if collar.any() else '-', back.sum()))
    fails += res['sleeve'] != 0 or res['hub on (control)'] == 0

    # 2 in place, exact: both press sleeves; the inner ring may overlap by the press, nothing else may
    ball = E.rd(os.path.join(O, 'ball_plus_sleeve.brep')); post = E.rd(config.out('post_v3.brep'))
    inner, outer = ring(10.0, 11.3, 26.5, 30.5), ring(12.3, 13.5, 26.5, 30.5)
    SLEEVES = (('sleeve', '20.0'), ('sleeve_press_201', '20.1'))
    for f, label in SLEEVES:
        sl = E.rd(os.path.join(O, f + '.brep'))
        v = [vol(common(sl, x)) for x in (ball, post, outer)]
        print('2 press %s: vs cut ball %.3f, post v3 %.3f, 6704 outer ring %.3f mm3 | inner ring (the press) %.2f mm3'
              % (label, *v, vol(common(sl, inner))))
        fails += max(v) > 1e-3
    ctl = vol(common(moved(E.rd(os.path.join(O, 'sleeve.brep')), dy=-0.5), ball))
    ctl2 = vol(common(ring(8.0, 12.5, 30.5, 31.9), outer)) + vol(common(ring(8.0, 12.5, 30.4, 31.9), post))
    print('  controls: 0.5 deeper vs the ball %.2f mm3; a lip of r 12.5 vs the outer ring and the post %.2f mm3' % (ctl, ctl2))
    fails += ctl < 1.0 or ctl2 < 1.0

    # 3 vs his MG90S (tower top Y 26.24 from post v3's fit; gear bump toward -X, his hub's notch) and the cradle
    import pan_servo_fit as SF
    M = np.concatenate(SF.mesh()); S = np.stack([-(M[..., 0] + 5.4), M[..., 1] - 2.16, H - (M[..., 2] - 6.1)], -1)
    h = 0.1; g3 = (np.arange(-14, 14, h) + h / 2, np.arange(22, 33, h) + h / 2, np.arange(H - 14, H + 14, h) + h / 2)
    mv, mc = _scan(S, 2, g3), _scan(cradle, 2, g3)
    for f, label in SLEEVES:
        ms = _scan(load_stl(os.path.join(O, f + '.stl')), 2, g3)
        a, c = (ms & mv).sum() * h ** 3, (ms & mc).sum() * h ** 3
        print('3 press %s: vs servo %.2f mm3, vs cradle %.2f mm3' % (label, a, c))
        fails += a > 0 or c > 0
    E.write_stl(ring(8.0, 10.05, 22.6, 31.9), os.path.join(O, '_plain.stl'))
    mp = _scan(load_stl(os.path.join(O, '_plain.stl')), 2, g3)
    E.write_stl(ring(8.0, 10.6, 25.2, 26.4), os.path.join(O, '_fat.stl'))
    mf = _scan(load_stl(os.path.join(O, '_fat.stl')), 2, g3)
    for t in ('_plain.stl', '_fat.stl'):
        os.remove(os.path.join(O, t))
    b, d = (mp & mv).sum() * h ** 3, (mf & mc).sum() * h ** 3
    print('  controls: no notch vs the servo %.2f mm3; r 10.6 in the collar shoulder bore vs the cradle %.2f mm3' % (b, d))
    fails += b == 0 or d == 0

    # 4 the way in: the sleeve with the 6704 pressed on, from +Y, the post not yet on
    for n, x in (('bearing_inner', inner), ('bearing_outer', outer)):
        E.write_stl(x, os.path.join(O, n + '.stl'))
    pair = np.concatenate([load_stl(os.path.join(O, n + '.stl')) for n in ('sleeve_press_201', 'bearing_inner', 'bearing_outer')])
    h = 0.15; g4 = (np.arange(-16, 16, h) + h / 2, np.arange(15, 45, h) + h / 2, np.arange(H - 16, H + 16, h) + h / 2)
    m = _scan(pair, 1, g4)
    blocked = sweep_hits(m, _scan(cradle, 1, g4) | _scan(hub_off, 1, g4), 1, +1).sum()
    c4 = sweep_hits(m, _scan(cradle, 1, g4) | _scan(hub_on, 1, g4), 1, +1).sum()
    print('4 sleeve + 6704 sliding in from +Y: %d lines blocked | control, into the hub-on ball: %d' % (blocked, c4))
    fails += blocked > 0 or c4 == 0

    from probe import hits
    # 5 the turning ring against fixed parts: the cradle's face just inboard of the seat (Y 26.5), round the axis
    from probe import hits
    y, row5 = 26.5 - 0.1, []
    for ang in range(0, 360, 30):
        d = np.array([np.cos(np.radians(ang)), 0.0, np.sin(np.radians(ang))])
        t = hits(cradle, (0.0, y, H), d); t = t[t > 0]
        row5.append('%d:%.2f' % (ang, t[0] if len(t) else np.nan))
    print('5 cradle 0.1 inboard of the seat, first solid r by angle (the inner ring is r 10.0..11.3): ' + ' '.join(row5))
    # 6 plate left under the socket floor, over the ball's inside (rays down -Y, every 2 deg)
    import plus_sleeve as PS
    hub_on_t = hub_on
    def floor(T, y):
        m = 99.0
        for r in np.arange(PS.CUT_R0 + 0.1, PS.SOCKET_R, 0.25):
            for a in np.arange(0, 360, 2):
                o = (r * np.cos(np.radians(a)), y, H + r * np.sin(np.radians(a)))
                if a < 30 or a > 330:
                    if o[0] > PS.KEY_X: continue
                t = hits(T, o, (0, -1, 0)); t = t[t > 0]
                if len(t): m = min(m, t[0])
        return m
    f6, c6 = floor(hub_off, PS.SOCKET_Y0 - 0.01), floor(hub_on_t, 22.49)
    print('6 thinnest plate under the socket floor: %.2f mm | control, the first 2.0 deep socket: %.2f mm' % (f6, c6))
    fails += f6 < 0.6 or c6 > 0.3

    # 7 open space where the sleeve meets the ball (his slide rule: 0.15 a side; 0.3 to the floor), on the meshes
    slT = load_stl(os.path.join(O, 'sleeve.stl'))
    def gap(o, d):
        ts, tb = hits(slT, o, d), hits(hub_off, o, d)
        ts, tb = ts[ts > 0], tb[tb > 0]
        return tb[0] - ts[0] if len(ts) and len(tb) else np.nan
    yk = (PS.SOCKET_Y0 + PS.FLAT_Y) / 2
    pol = lambda r, a, y: (r * np.cos(np.radians(a)), y, H + r * np.sin(np.radians(a)))
    wall = [gap(pol(9.0, a, yk), (np.cos(np.radians(a)), 0, np.sin(np.radians(a)))) for a in range(30, 331, 10)
            if not (150 <= a <= 210)]
    ring_ = [gap(pol(9.0, a, yk), (-np.cos(np.radians(a)), 0, -np.sin(np.radians(a)))) for a in range(0, 360, 15)
             if not (140 <= a <= 220)]
    key = gap((8.5, yk, H), (1, 0, 0))
    axial = [gap(pol(9.0, a, PS.SLEEVE_Y0 + 0.3), (0, -1, 0)) for a in range(30, 331, 30)]
    print('7 gaps: socket wall %.2f..%.2f, key flat %.2f, plate ring %.2f..%.2f, floor %.2f..%.2f mm'
          % (np.nanmin(wall), np.nanmax(wall), key, np.nanmin(ring_), np.nanmax(ring_), np.nanmin(axial), np.nanmax(axial)))
    fails += np.nanmin(wall) < 0.149 or key < 0.149 or np.nanmin(ring_) < 0.149 or np.nanmin(axial) < 0.29

    # 8 the camera board where the pins put it: distance to the sleeve
    import campost_rev2 as R
    from kit import camera
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    cam = camera(2.5, centred=True, dz=R.LENS_DZ, dy=R.LENS_DY)
    d8 = BRepExtrema_DistShapeShape(cam, E.rd(os.path.join(O, 'sleeve_press_201.brep'))).Value()
    print('8 camera to the sleeve: %.2f mm' % d8)
    fails += d8 < 0.5

    # 9 post v3 goes on last, from +Y, through the sleeve with the 6704 in place
    postT = load_stl(config.out('ball_servo_post_v3.stl'))
    m = _scan(postT, 1, g4)
    inplace = _scan(cradle, 1, g4) | _scan(hub_off, 1, g4) | _scan(pair, 1, g4)
    E.write_stl(ring(7.5, 9.95, 23.3, 31.9), os.path.join(O, '_tight.stl'))
    bad_sl = load_stl(os.path.join(O, '_tight.stl')); os.remove(os.path.join(O, '_tight.stl'))
    b9 = sweep_hits(m, inplace, 1, +1).sum()
    c9 = sweep_hits(m, _scan(cradle, 1, g4) | _scan(hub_off, 1, g4) | _scan(bad_sl, 1, g4), 1, +1).sum()
    print('9 post v3 sliding on last: %d lines blocked | control, a sleeve with a r 7.5 bore: %d' % (b9, c9))
    fails += b9 > 0 or c9 == 0
    print('FAIL' if fails else 'ok: rows 1-4 and 6-9 pass, each control reads')
    sys.exit(1 if fails else 0)
