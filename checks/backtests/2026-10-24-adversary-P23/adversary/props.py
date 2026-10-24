"""Adversary probes of the shelf ring's seating properties that no current check measures. Edits nothing.
    python props.py [my_mutants.py ID [rest,turn,slide,shelf]]
  rest   : how far the ring would drop before it meets the base (0 = it sits on something)
  turn   : smallest ring rotation that meets the base (the key stop); 'free' = nothing stops it
  slide  : per direction, the ring's travel to the base vs its travel to the drum (play must stop it first)
  shelf  : the shelf's thickness
"""
import sys, importlib.util
import numpy as np
import pan_coil_b as P

if len(sys.argv) > 2 and sys.argv[2] != 'design':
    spec = importlib.util.spec_from_file_location('mf', sys.argv[1])
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    M.MUTANTS[sys.argv[2]][0](P)
tag = sys.argv[2] if len(sys.argv) > 2 else 'design'
ONLY = sys.argv[3].split(',') if len(sys.argv) > 3 else ['rest', 'turn', 'slide', 'shelf']
ring, base, drum = P.PARTS['shelf_ring'][0], P.PARTS['base'][0], P.PARTS['drum'][0]


def annulus_pts(r0, r1, zs, h):
    xs = np.arange(-r1, r1 + h, h)
    X, Y = np.meshgrid(xs, xs, indexing='ij')
    r = np.hypot(X, Y)
    m = (r >= r0) & (r <= r1)
    x, y = X[m], Y[m]
    return (np.tile(x, len(zs)), np.tile(y, len(zs)), np.repeat(zs, len(x)))


def rest():
    h = 0.25
    xs = np.arange(-23.5, 23.5 + h, h)
    X, Y = np.meshgrid(xs, xs, indexing='ij')
    low = np.full(X.shape, np.nan)
    for z in np.arange(P.LANE_Z1 - 1.5, P.CH_Z0 + 0.6, 0.02):
        s = ring((X, Y, np.full_like(X, z))) < 0
        low = np.where(np.isnan(low) & s, z, low)
    m = ~np.isnan(low)
    x, y, zl = X[m], Y[m], low[m]
    drop = np.full(x.shape, np.inf)
    for d in np.arange(0.0, 6.0, 0.02):
        s = (base((x, y, zl - 0.03 - d)) < 0) & np.isinf(drop)
        drop = np.where(s, d, drop)
    contact = np.count_nonzero(drop <= 0.05) * h * h
    print(f'{tag}: rest  drop {np.min(drop):.2f} mm before it meets the base; contact area {contact:.0f} mm2')


def turn():
    q = annulus_pts(19.5, 23.6, np.arange(P.LANE_Z1 - 0.05, P.CH_Z0 + 0.1, 0.08), 0.06)
    B = base(q) < -0.005
    stop = 'free (nothing up to 180 deg)'
    for deg in (0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 1, 1.5, 2, 3, 5, 10, 20, 45, 90, 180):
        hit = 0
        for sgn in (1, -1):
            a = np.radians(-sgn * deg)
            rq = (q[0] * np.cos(a) - q[1] * np.sin(a), q[0] * np.sin(a) + q[1] * np.cos(a), q[2])
            hit += np.count_nonzero((ring(rq) < -0.005) & B)
        if hit:
            stop = f'{deg} deg ({np.radians(deg) * 21.45:.2f} mm at the rib)'
            break
    print(f'{tag}: turn  first meets the base at +-{stop}')


def slide():
    zs = np.r_[np.linspace(P.LANE_Z1 + 0.1, P.CH_Z0 - 0.1, 3), np.linspace(P.CH_Z1 + 0.1, P.DECK_Z1 - 0.5, 4)]
    q = annulus_pts(11.0, 23.8, zs, 0.12)
    B, D = base(q) < -0.01, drum(q) < -0.01
    res = []
    for ang in range(0, 360, 30):
        u = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        tb = td = None
        for t in np.arange(0.0, 1.21, 0.05):
            R = ring((q[0] - u[0] * t, q[1] - u[1] * t, q[2])) < -0.01
            if tb is None and np.count_nonzero(R & B):
                tb = round(float(t), 2)
            if td is None and np.count_nonzero(R & D):
                td = round(float(t), 2)
            if tb is not None and td is not None:
                break
        res.append((ang, tb, td))
    bad = [(a, tb, td) for a, tb, td in res if (tb is None) or (td is not None and td <= tb)]
    least = min((tb if tb is not None else 9.0) for _, tb, _ in res)
    dmin = min((td if td is not None else 9.0) for _, _, td in res)
    print(f'{tag}: slide least play to the base {least:.2f} mm, least travel to the drum {dmin:.2f} mm; drum met first at: '
          + (', '.join(f'{a} deg (base {tb}, drum {td})' for a, tb, td in bad) if bad else 'none'))


def shelf():
    z = np.arange(P.LANE_Z1 - 1.5, P.CH_Z0 + 1.5, 0.01)
    s = ring((np.full_like(z, 16.0), np.zeros_like(z), z)) < 0
    print(f'{tag}: shelf {s.sum() * 0.01:.2f} mm thick at r 16')


for name in ONLY:
    globals()[name]()
