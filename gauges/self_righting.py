"""The body as its own roll hoop (2026-11-07): a 250 mm body, head off and a pinhole camera in the nose, its top shaped
so that wherever it lands it rolls back onto its wheels. Zach: "can the body kinda be the roll loops? ... huge roll
loops on the top are just a bad idea", then "show me what it could look like".

    python gauges/self_righting.py search   # shape the skin's top for the static upright share -> out/self_righting/search.json
    python gauges/self_righting.py page     # the 3D page (and G1 falls for both bodies) -> out/self_righting/self_righting.html

The platform is the head-options body (head_options.DESIGN, a design the 250 mm run builds): its wheels, drive, packs
and tail stay; the skin's shape knobs and the tail's stowed angle are searched, inside the 250 mm run's ranges and
the cap. The head comes off (its 210 g out); a pinhole camera, CAM_G*, sits in the nose. A concept, not in a run:
the 250 mm run still seats the head on top (docs/decisions.md, 2026-11-07).
Measures: the static upright share (search.statics: of 3,000 orientations, the share that rolls, quasi-statically, to
rest on its wheels; tail stowed) and G1 (the falls gauge in MuJoCo, 60 falls at each of x1.5 and x0.65, the tail free
to act).
"""
import os, sys, json, base64
os.environ['SCORPION_CAP'] = 'capability_250'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools'), os.path.join(HERE, '..', 'research', 'tumble')]
import numpy as np
from scipy.spatial import ConvexHull
import config
import knobs as K, search as S, robots as RB, capability as CAP, head_options as HO

OUT = os.path.join(config.GAUGES_OUT, 'self_righting')
CAM_G = 15.0                                   # g: the camera board, an M12 pinhole lens and its holder (a guess)
SHAPE = ('zc', 'cu', 'cd', 'qu', 'qd', 'p', 'b', 'af', 'ar', 'xc')
TAIL = ('th_stow', 20.0, 160.0)


def _no_head(q, sp):
    """knobs._place_head's stand-in: the head's 210 g out, the pinhole camera in, at the nose's tip on the centre line"""
    import chassis3 as C3
    b = C3.base(); dz = q['clr'] - b['clr0']
    m, p0 = next((m, np.asarray(p, float) + [0.0, 0.0, dz]) for n, m, p in b['items'] if n == 'head')
    M, cm, I = K._add_body(sp['M'], sp['com'], sp['I'], -m, p0, np.zeros((3, 3)))
    body = np.asarray(sp['hulls'][0], float); zz = np.linspace(body[:, 2].min() + 15, body[:, 2].max() - 15, 60)
    fx = np.array([HO.front_x(body, z) for z in zz]); zc = float(zz[fx >= fx.max() - 8.0].max())
    cam = np.array([HO.front_x(body, zc) - 12.0, 0.0, zc])
    M, cm, I = K._add_body(M, cm, I, CAM_G, cam, np.zeros((3, 3)))
    return RB.dims(dict(sp, M=M, com=cm, I=I, cam=cam.tolist(), notes=list(sp['notes']) + ['head off; a pinhole camera in the nose']))


def build(q, why=None):
    """the body with the head off (knobs.make's head-out path, the head's placement swapped for _no_head), held to the cap"""
    K._place_head, keep = _no_head, K._place_head
    try:
        return K.make(dict(q, head_f=0.5), real=True, why=why, cap=250.0)
    finally:
        K._place_head = keep


def base_q():
    return dict(K.T3, **HO.DESIGN)


def read(q):
    sp = build(q)
    if sp is None:
        return None
    st = S.statics(sp); L, W, H = K.body_print_size(sp)
    return dict(static_up=st['static_up'], n_rest=st['n_rest'], size=[L, W, H], height=sp['height'], mass=sp['mass'])


def _one(z):
    q = base_q()
    for k, v in zip(SHAPE, z[:len(SHAPE)]):
        lo, hi = CAP.CAP_RANGES.get(k, next((a, b) for _, kk, a, b, _ in K.KNOBS if kk == k)); q[k] = float(lo + v * (hi - lo))
    q['th_stow'] = TAIL[1] + z[-1] * (TAIL[2] - TAIL[1])
    try:
        r = read(q)
    except Exception as e:
        return dict(err=str(e)[:100])
    return None if r is None else dict(q={k: q[k] for k in SHAPE + ('th_stow',)}, **r)


def search(n=600):
    from multiprocessing import Pool
    from scipy.stats import qmc
    Z = qmc.Sobol(len(SHAPE) + 1, seed=11).random(n)
    with Pool(24) as p:
        R = [r for r in p.map(_one, list(Z), chunksize=4) if r and 'err' not in r]
    R.sort(key=lambda r: (-r['static_up'], r['height']))
    os.makedirs(OUT, exist_ok=True); json.dump(R, open(os.path.join(OUT, 'search.json'), 'w'))
    print(f'{len(R)} of {n} build under the cap; static upright share: best {R[0]["static_up"]:.3f}, '
          f'median {np.median([r["static_up"] for r in R]):.3f}; {sum(r["static_up"] >= 0.999 for r in R)} at 1.00')
    for r in R[:5]:
        print(round(r['static_up'], 3), r['n_rest'], [round(v) for v in r['size']], {k: round(v, 2) for k, v in r['q'].items()})
    print('the drawn body, head off:', read(base_q()))


# ---------- the page: what it could look like ----------
INV = dict(R=70.0, clr=22.0, gap=30.0, xw=-3.0, TW=40.0, track=130.0, track_r=130.0, af=60.0, ar=60.0, b=60.0, zc=60.0,
           cu=30.0, cd=20.0, xc=0.0)                    # wheels taller than the body: it drives either way up
CASES = {'box': dict(limb=0.0), 'tail': dict(limb=1.0), 'inv': dict(INV, limb=0.0)}


def falls(name, n=60):
    """G1's falls in MuJoCo, n at each of x1.5 and x0.65 grip: the rest-state counts (the tail acts when there is one)"""
    import gauges as GG
    q = dict(base_q()); q.update(CASES[name]); sp = build(q); tot = {}
    for mu in (1.5, 0.65):
        f = GG.falls(GG.Sim(sp, mu), n, np.random.default_rng([7, int(round(100 * mu))]))
        for k, v in f.items():
            tot[k] = tot.get(k, 0) + v
    return name, tot


def _hull2(P):
    P = np.asarray(P, float); return P[ConvexHull(P).vertices]


def drawing(sp, view, circle=None, cap=None, tail_arc=False, flip=False, X=None, Z=(-60.0, 520.0)):
    """one view to one scale: 'side' (x, z) or 'front' (y, z). circle: (centre, radius), the shell righting would need;
    cap: (lo, hi, belly), the 250 mm box; flip: drawn upside down, on its wheels' tops"""
    ax = 0 if view == 'side' else 1
    G = S.com_all(sp); R, TW = sp['R'], sp['TW']
    X = X or ((-380.0, 300.0) if view == 'side' else (-260.0, 260.0)); W = X[1] - X[0]; zmin, zmax = Z
    zf = (lambda z: 2 * R - z) if flip else (lambda z: z)
    tx = lambda x: x - X[0]; ty = lambda z: zmax - zf(z)
    pts = lambda S2: ' '.join(f'{tx(a):.1f},{ty(b):.1f}' for a, b in S2)
    g = [f'<svg viewBox="0 0 {W:.0f} {zmax - zmin:.0f}" role="img" aria-label="{view} view to scale">',
         f'<line class="ground" x1="0" y1="{zmax:.1f}" x2="{W:.0f}" y2="{zmax:.1f}"/>']
    if cap:
        lo, hi, zb = cap; g.append(f'<rect class="cap" x="{tx(lo):.1f}" y="{ty(zb + 250.0):.1f}" width="{hi - lo:.1f}" height="250"/>')
    if circle:
        c, r = circle; g.append(f'<circle class="need" cx="{tx(c[0]):.1f}" cy="{ty(c[1]):.1f}" r="{r:.1f}"/>')
    lm = sp.get('limb')
    if lm and view == 'side':
        T = RB.limb_points(lm, 0.0, lm['th_stow'], k=24)[:24]
        if tail_arc:                                              # the tip's path as the tail swings over the top
            B = np.asarray(lm['base']); Lt = lm['L'] + lm.get('L2', 0.0); a = np.radians(np.linspace(lm['th_stow'], 178.0, 40))
            arc = np.c_[B[0] - Lt * np.cos(a), B[2] + Lt * np.sin(a)]; g.append(f'<polyline class="arc" points="{pts(arc)}"/>')
            g.append(f'<circle class="tailghost" cx="{tx(arc[-1, 0]):.1f}" cy="{ty(arc[-1, 1]):.1f}" r="12"/>')
        g.append(f'<polyline class="tail" points="{pts(T[:, [0, 2]])}"/>')
        g.append(f'<circle class="tailfoot" cx="{tx(T[-1, 0]):.1f}" cy="{ty(T[-1, 2]):.1f}" r="12"/>')
    body = np.asarray(sp['hulls'][0], float)
    for P in sp['hulls'][1:1 + sp.get('pods', 0)]:
        g.append(f'<polygon class="body" points="{pts(_hull2(np.asarray(P)[:, [ax, 2]]))}"/>')
    if view == 'side':
        g.append(f'<polygon class="body" points="{pts(_hull2(body[:, [0, 2]]))}"/>')
        for x in sorted({round(x, 1) for x, _ in sp['wheels']}):
            g.append(f'<circle class="tyre" cx="{tx(x):.1f}" cy="{ty(R):.1f}" r="{R:.1f}"/><circle class="hub" cx="{tx(x):.1f}" cy="{ty(R):.1f}" r="{R * .35:.1f}"/>')
    else:
        g.append(f'<polygon class="body" points="{pts(_hull2(body[:, [1, 2]]))}"/>')
        for y in sorted({round(y, 1) for _, y in sp['wheels']}):
            g.append(f'<rect class="tyre" x="{tx(y - TW / 2):.1f}" y="{min(ty(2 * R), ty(0)):.1f}" width="{TW:.1f}" height="{2 * R:.1f}" rx="6"/>')
    if sp.get('cam'):
        c = sp['cam']; g.append(f'<circle class="lens" cx="{tx(c[0] + 12 if view == "side" else c[1]):.1f}" cy="{ty(c[2]):.1f}" r="6"/>')
    gc = G[0] if view == 'side' else G[1]
    g.append(f'<circle class="com" cx="{tx(gc):.1f}" cy="{ty(G[2]):.1f}" r="8"/>'
             f'<path class="comx" d="M{tx(gc) - 8:.1f},{ty(G[2]):.1f}h16M{tx(gc):.1f},{ty(G[2]) - 8:.1f}v16"/></svg>')
    return ''.join(g)


def page():
    from multiprocessing import Pool
    with Pool(3) as p:
        F = dict(p.map(falls, list(CASES)))
    sp = {k: build(dict(base_q(), **v)) for k, v in CASES.items()}
    box = sp['box']; G = S.com_all(box); W = box['wheels']; R, TW = box['R'], box['TW']
    ty_ = max(abs(y) for _, y in W) + TW / 2
    r_side = float(np.hypot(ty_, G[2]))                            # the CoM to a tyre's bottom outer edge, sideways and fore-aft
    r_end = float(max(np.hypot(max(x for x, _ in W) + R - G[0], G[2]), np.hypot(G[0] - min(x for x, _ in W) + R, G[2])))
    zb = float(np.asarray(box['hulls'][0])[:, 2].min())
    d = dict(need_front=drawing(box, 'front', circle=((0.0, G[2]), r_side + 5), cap=(-125.0, 125.0, zb), Z=(-120.0, 300.0), X=(-230.0, 230.0)),
             need_side=drawing(box, 'side', circle=((G[0], G[2]), r_end + 5), cap=(-125.0 + G[0], 125.0 + G[0], zb), Z=(-120.0, 300.0), X=(-230.0, 230.0)),
             tail_side=drawing(sp['tail'], 'side', tail_arc=True, Z=(-20.0, 730.0), X=(-520.0, 340.0)),
             inv_front=drawing(sp['inv'], 'front', Z=(-10.0, 160.0), X=(-200.0, 200.0)),
             inv_side=drawing(sp['inv'], 'side', Z=(-10.0, 160.0), X=(-200.0, 200.0)),
             inv_flip=drawing(sp['inv'], 'side', flip=True, Z=(-10.0, 160.0), X=(-200.0, 200.0)))
    tot = lambda k: sum(F[k].values())
    share = lambda k, *s: sum(F[k].get(x, 0) for x in s) / tot(k)
    ib = np.asarray(sp['inv']['hulls'][0]); Li, Wi, Hi = K.body_print_size(sp['inv']); Lb, Wb, Hb = K.body_print_size(box)
    data = dict(d=d, falls=F, n=tot('box'), box_up=share('box', 'upright'), box_back=share('box', 'inverted'), tail_up=share('tail', 'upright'),
                inv_either=share('inv', 'upright', 'inverted'), r_side=round(r_side), r_end=round(r_end), shell_w=round(2 * r_side + 10),
                shell_l=round(2 * r_end + 10), com_z=round(G[2]), box=[round(Lb), round(Wb), round(Hb)], inv=[round(Li), round(Wi), round(Hi)],
                inv_R=INV['R'], inv_clear=[round(float(ib[:, 2].min())), round(2 * INV['R'] - float(ib[:, 2].max()))],
                tail_len=round(sp['tail']['limb']['L'] + sp['tail']['limb'].get('L2', 0)), cam_g=CAM_G,
                mass=dict(box=round(box['mass']), inv=round(sp['inv']['mass'])))
    os.makedirs(OUT, exist_ok=True)
    tpl = open(os.path.join(HERE, 'self_righting_template.html'), encoding='utf-8').read()
    p = os.path.join(OUT, 'self_righting.html'); open(p, 'w', encoding='utf-8').write(tpl.replace('/*DATA*/', 'window.SR=' + json.dumps(data) + ';'))
    print({k: v for k, v in data.items() if k != 'd'}); print('wrote', p)


if __name__ == '__main__':
    {'search': search, 'page': page}.get(sys.argv[1] if len(sys.argv) > 1 else '', lambda: print(__doc__))()
