"""Head options (2026-11-07): where the pan-tilt head can go, drawn to scale from the side on a body from the 250 mm
run, each read for three things: what lands first when it rolls over, how much ground ahead the camera can't see, and
how tall the robot stands. Zach: "show me options as drawings for what can happen with the head lets explore designs
for the best solution".

    python gauges/head_options.py      -> gauges/out/head_options/head_options.html (the "Scorpion Head Options" artifact)

The body, wheels and tail are a design the 250 mm run builds (DESIGN: one of 480 samples, 230 x 231 x 154). The head is
the real one (search.components: base, drum, cradle, ball). The guards, dome, mounts and the fixed camera are sketches
of mine, sized here (GUESSES); none is in the sims. Rolls are read on the convex hull, side and front views, tail left
out (it moves); the blind zone assumes the head can tilt down as far as it needs.
"""
import os, sys, json, html
os.environ['SCORPION_CAP'] = 'capability_250'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools'), os.path.join(HERE, '..', 'research', 'tumble')]
import numpy as np
from scipy.spatial import ConvexHull
from matplotlib.path import Path
import config
import knobs as K, search as S, robots as RB

OUT = os.path.join(config.GAUGES_OUT, 'head_options')
DESIGN = {"R": 49.0, "gap": 78.032, "xw": -2.944, "track": 138.68, "TW": 59.532, "clr": 83.083, "zc": 111.091, "cu": 72.348,
          "cd": 74.349, "af": 54.578, "ar": 53.956, "b": 113.936, "xc": -3.595, "p": 3.481, "qu": 3.384, "qd": 2.992,
          "dxp": -78.485, "dzp": 9.118, "gear": 1.069, "L": 295.094, "tq": 3.448, "th_push": -20.813, "th_stow": 36.325,
          "mount_z": 177.342, "foot_r": 31.02, "L2": 140.312, "rear_up": 0.769, "bumper": 94.668, "track_r": 137.429,
          "limb": 1.0, "six": 0.0, "flip": 0.0, "shell": 1.0}
GUESSES = dict(hoop_gap=8.0, hoop_bar=12.0, dome_gap=6.0, well_up=12.0, chin_out=40.0, chin_z=15.0, stinger_pitch=100.0,
               cam=(28.0, 22.0), cam_fov=160.0, cam_tilt=25.0)


def side(P):
    P = np.asarray(P, float)[:, [0, 2]]; return P[ConvexHull(P).vertices]


def front(P):
    P = np.asarray(P, float)[:, [1, 2]]; return P[ConvexHull(P).vertices]


def circle(c, r, n=48):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False); return np.c_[c[0] + r * np.cos(a), c[1] + r * np.sin(a)]


def front_x(body, z):
    """the convex hull's front surface on the centre line at height z"""
    E = ConvexHull(body).equations; f = E[:, 0] > 1e-9
    return float((-(E[f, 2] * z + E[f, 3]) / E[f, 0]).min())


def section(P, n=80):
    """a convex solid's cut on the centre line (y = 0), as an (x, z) polygon: what a lens on the centre line looks past"""
    E = ConvexHull(np.asarray(P, float)).equations; zs = np.linspace(P[:, 2].min(), P[:, 2].max(), n); F, Bk = [], []
    for z in zs:
        c = E[:, 2] * z + E[:, 3]; f, b = E[:, 0] > 1e-9, E[:, 0] < -1e-9
        if (c[np.abs(E[:, 0]) <= 1e-9] > 1e-6).any():
            continue
        xf, xb = (-c[f] / E[f, 0]).min(), (-c[b] / E[b, 0]).max()
        if xf >= xb:
            F.append((xf, z)); Bk.append((xb, z))
    return np.array(F + Bk[::-1])


def base_spec():
    """the drawn design without its head (the head is placed per option)"""
    q = {k: v for k, v in dict(K.T3, **DESIGN).items()}
    sp = K.make(dict(q, head_f=0.878), real=True)            # as the run built it; the head is replaced per option
    keep = len(sp['hulls']) - sp['head_n']
    return q, dict(sp, hulls=sp['hulls'][:keep])


def head_parts(d):
    """the head's four parts moved by d from where the Trainer had it: {name: points}"""
    import chassis3 as C3
    C = S.components(); q = dict(K.T3, **DESIGN); dz = q['clr'] - C3.base()['clr0']
    return {k: np.asarray(C[k], float) + [0.0, 0.0, dz] + d for k in S.HEAD}


def head_ref():
    """the head where the Trainer has it in this design: pan axis (x, y), base bottom z, the ball's centre and radius"""
    H = head_parts(np.zeros(3)); D = H['drum']; pan = 0.5 * (D.min(0) + D.max(0)); B = H['ball']
    return pan, float(H['base'][:, 2].min()), 0.5 * (B.min(0) + B.max(0)), float(0.5 * (B[:, 2].max() - B[:, 2].min()))


def place(body, x_pan, z_seat=None):
    """the offset that puts the pan axis at x_pan on the centre line, its base on the body's top (or at z_seat)"""
    pan, zb, _, _ = head_ref()
    if z_seat is None:
        H = head_parts(np.zeros(3)); foot = H['base'][:, :2] - pan[:2]
        zt = K._top_z(body, foot[::40] * 0.94 + [x_pan, 0.0]); z_seat = float(np.nanmax(zt))
    return np.array([x_pan - pan[0], -pan[1], z_seat - zb])


def options(q, sp):
    """each option: what is drawn (side shapes by role), the solids for the roll check (3D points), the lens, notes"""
    body = np.asarray(sp['hulls'][0], float); pods = [np.asarray(h, float) for h in sp['hulls'][1:]]
    x0, x1 = float(body[:, 0].min()), float(body[:, 0].max()); top = float(body[:, 2].max())
    pan, zb, ball_c, ball_r = head_ref(); H0 = head_parts(np.zeros(3)); f_lo = float((H0['base'][:, 0] - pan[0]).min()); f_hi = float((H0['base'][:, 0] - pan[0]).max())
    R, TW = sp['R'], sp['TW']
    wheels = [np.array([[x + a * R * np.cos(t), y + s * TW / 2, R + R * np.sin(t)] for t in np.linspace(0, 2 * np.pi, 24) for s in (-1, 1) for a in (1,)])
              for x, y in sp['wheels']]
    lm = sp.get('limb'); tail = RB.limb_points(lm, 0.0, lm['th_stow'], k=24) if lm else None
    sweep = 44.0                                                              # the cradle's pan sweep, radius
    lens_off = np.array([ball_r, 0.0, 0.0])                                   # the lens: the ball's front, tilt 0
    G = GUESSES; out = []

    def opt(key, name, head_d=None, extra=(), extra_side=(), lens=None, shell=None, tail_pts=tail, chin=False, **txt):
        hp = head_parts(head_d) if head_d is not None else {}
        L = (ball_c + head_d + lens_off) if (lens is None and head_d is not None) else lens
        out.append(dict(key=key, name=name, head=hp, extra=list(extra), extra_side=list(extra_side), lens=L, shell=shell,
                        tail=tail_pts, **txt))

    # 1 open on top: the 250 mm run as it stands (head_f 0.88 in this design)
    xp = x0 - f_lo + 0.88 * ((x1 - f_hi) - (x0 - f_lo)); d1 = place(body, xp)
    opt('open', 'On top, open', d1,
        what="What the 250 mm run builds now: the head bolted on the top, nothing round it.",
        good=["Sees all round, and down close in front", "Nothing to add"],
        bad=["It's the first thing to land when the robot rolls over its top", "Dust and rain get in at the pan and tilt joints"])

    # 2 two roll hoops, across the body, ahead of and behind the cradle's sweep, standing over the ball
    xp2 = 0.5 * (x0 + x1) - 10.0; d2 = place(body, xp2); hp2 = head_parts(d2)
    ztop = max(P[:, 2].max() for P in hp2.values()) + G['hoop_gap']; hw = float(np.abs(body[:, 1]).max()) - 6.0
    hoops = []
    for xh in (xp2 - sweep - 14.0, xp2 + sweep + 14.0):
        zs = float(np.nanmax(K._top_z(body, np.array([[xh, 0.0], [xh, hw * 0.8]])))) - 6.0
        a = np.linspace(0, np.pi, 25)
        arch = np.vstack([np.c_[np.full(25, xh + dx), hw * np.cos(a), zs + (ztop - zs) * np.sin(a) ** 0.35] for dx in (-6.0, 6.0)])
        hoops.append(arch)
    opt('hoops', 'Two roll hoops', d2, extra=[('guard', P) for P in hoops],
        what="Two hoops across the body, one ahead of the head and one behind, both standing a little over the ball. The robot rolls over on the hoops.",
        good=["The hoops land first, side and end rolls alike", "Sees forward through the front hoop's opening", "Cheap: printed, or bent rod",
              "Shaped round the centre of mass, hoops can also roll it back upright (the rugged body's idea, not checked on this body)"],
        bad=["The front hoop's bar crosses the view upward", "Taller than the open head", "Joints still open to dust (seal the ball, below)"])

    # 3 sunk: the base and the drum in a well, only the ball and the cradle's top above the body
    d3 = place(body, xp); d3[2] = top + G['well_up'] - ball_c[2]              # the ball's centre well_up over the body's top
    opt('sunk', 'Sunk in a well', d3,
        what="The base and the drum sit down in a well in the body; only the ball and the cradle's top stand above it.",
        good=["Much less of it to hit", "The body shields it from the sides", "Lower: the robot stands less tall"],
        bad=["Still the highest point: it lands first on a roll over the top", "The well takes the base's room inside (87 x 62 x 46 mm and the cradle under it): the parts inside have to move, and the 250 mm body may grow",
             "The body's top edge hides the ground close in front"])

    # 4 a bought dome over the head on top
    xp4 = xp; d4 = d1; hp4 = head_parts(d4); c4 = np.array([xp4, 0.0, zb + d4[2] + 46.0])
    rr = max(float(np.linalg.norm(P[P[:, 2] > c4[2]] - c4, axis=1).max()) for P in hp4.values() if (P[:, 2] > c4[2]).any())
    rr = max(rr, sweep) + G['dome_gap']
    a = np.linspace(0, np.pi / 2, 12); t = np.linspace(0, 2 * np.pi, 24, endpoint=False)
    dome = np.vstack([np.c_[c4[0] + rr * np.cos(ai) * np.cos(t), rr * np.cos(ai) * np.sin(t), np.full(24, c4[2] + rr * np.sin(ai))] for ai in a])
    ring = np.vstack([np.c_[c4[0] + (rr + 6) * np.cos(t), (rr + 6) * np.sin(t), np.full(24, z)] for z in (c4[2] - 8.0, c4[2])])   # the clamp ring
    opt('dome', 'Under a bought dome', d4, extra=[('dome', dome), ('guard', ring)], shell=('dome', c4, rr),
        what=f"A clear dome, {2 * rr:.0f} mm across, clamped over the head by a printed ring. Bought (a CCTV dome or a clear ornament half), not printed.",
        good=["Sealed from dust and rain", "Smooth: it slides rather than snags in a roll", "Nothing clear goes through the printer"],
        bad=["The dome lands first on a roll over the top: it scratches, and it's the window", "Light inside bounces off it into the lens (security cameras put a foam ring round the lens)",
             f"Tallest but one, and {2 * rr:.0f} mm wide on top"])

    # 5 a chin mount: ahead of the nose, low
    zs5 = float(body[:, 2].min()) + G['chin_z']                                 # low: the ball's top stays under the body's
    d5 = place(body, x1 + G['chin_out'], z_seat=zs5)
    shelf = np.array([[x, y, z] for x in (x1 - 40.0, x1 + G['chin_out'] + f_hi) for y in (-35.0, 35.0) for z in (zs5 - 6, zs5)])
    opt('chin', 'Chin mount', d5, extra=[('guard', shelf)], chin=True,
        what="The head ahead of the nose, low, on a shelf between the front wheels.",
        good=["Sees the ground right in front and under the nose", "Leaves the top clear (tail, hoops, anything)", "Low: little weight up high"],
        bad=["The first thing to hit a step or a wall", "Lengthens the robot by the shelf", "Sees nothing behind"])

    # 6 the stinger: the head on the tail's tip, the tail raised
    if lm:
        th = np.radians(G['stinger_pitch']); B = np.asarray(lm['base'], float); Lt = lm['L'] + lm.get('L2', 0.0)
        tip = B + Lt * np.array([-np.cos(th), 0.0, np.sin(th)])
        d6 = np.array([tip[0] - pan[0], -pan[1], tip[2] + 4.0 - zb])
        sting = RB.limb_points(dict(lm, foot_r=1.0), 0.0, G['stinger_pitch'], k=24)
        opt('stinger', 'On the tail (stinger cam)', d6, tail_pts=sting,
            what="The head on the tail's tip, the tail raised like a scorpion's sting: the camera looks down over the body.",
            good=["Sees over obstacles, and sees the robot itself", "Out of the way of the body in a roll if the tail swings it clear", "Fits the scorpion"],
            bad=["The tail pushes, braces and rights the robot with its tip: the camera would take those hits", "210 g at the tip: the tail servo needs far more torque",
                 "The camera's wires run through the turntable", "None of this is in the sims"])

    # 7 a fixed wide-angle camera behind a flat window in the nose, flush with the skin
    cw, ch = G['cam']; zz = np.linspace(float(body[:, 2].min()) + 15.0, top - 15.0, 60)
    fx = np.array([front_x(body, z) for z in zz]); zc = float(zz[fx >= fx.max() - 8.0].max()); xs = front_x(body, zc)   # the top of the nose's tip
    cam = np.array([[x, y, z] for x in (xs - 12.0 - cw, xs - 12.0) for y in (-14.0, 14.0) for z in (zc - ch / 2, zc + ch / 2)])
    lens7 = np.array([xs + 0.5, 0.0, zc])                                       # the window, flush with the skin
    opt('fixed', 'Fixed wide camera, no pan-tilt', None, extra=[('cam', cam)], lens=lens7,
        what=f"A {G['cam_fov']:.0f}° camera behind a flat window at the nose's tip, flush with the skin, tilted down {G['cam_tilt']:.0f}°. No head: it pans and tilts in software by cropping.",
        good=["No moving parts, nothing to break or jam", "A flat window: a watch glass or acrylic disc, easy to seal", "210 g lighter, lower, and the top is free"],
        bad=["Can't look round: the view is fixed (a second camera covers behind)", "Less detail per degree than a narrow lens on a pan-tilt", "Drops the head you've built through eleven sets"])
    return out, dict(body=body, pods=pods, wheels=wheels, sp=sp, x1=x1, top=top)


def measure(o, B):
    """roll: what's on the convex hull (side and front views; tail out); blind: ground ahead the lens can't see; height"""
    solids = [('body', B['body'])] + [('body', P) for P in B['pods']] + [('wheel', W) for W in B['wheels']] \
        + [('head', P) for P in o['head'].values()] + [(r, P) for r, P in o['extra']]
    first = {}
    for view, f in (('end', lambda P: P[:, [0, 2]]), ('side', lambda P: P[:, [1, 2]])):
        A = np.vstack([f(P) for _, P in solids]); hull = ConvexHull(A); E = hull.equations
        top_faces = E[E[:, 1] > 0.2]                                     # faces it could land on over the top (not the ground)
        on = []
        for role, P in solids:
            Q = f(P); dmax = (Q @ top_faces[:, :2].T + top_faces[:, 2]).max(0)   # per face: how close this part comes to it
            on.append((role, (dmax > -1.5).sum()))
        first[view] = sorted({r for r, n in on if n > 0} - {'body', 'wheel'}) or ['body']
    # blind zone: the nearest ground ahead of the front-most point that a line from the lens reaches past every solid.
    # The head's own parts move with its lens, and the dome is clear; a hoop is open in the middle, only its top bar in the way.
    S2 = []                                                               # on the centre line: the tyres are off to the sides
    for r, P in solids:
        if r == 'body':
            if np.abs(P[:, 1]).min() < 5.0 or P[:, 1].min() < 0 < P[:, 1].max():
                S2.append(section(P))
        elif r == 'cam' or (r == 'guard' and o['key'] != 'hoops'):
            S2.append(side(P))
        elif r == 'guard':
            S2.append(np.array([[P[:, 0].min(), P[:, 2].max() - GUESSES['hoop_bar']], [P[:, 0].max(), P[:, 2].max() - GUESSES['hoop_bar']],
                                [P[:, 0].max(), P[:, 2].max()], [P[:, 0].min(), P[:, 2].max()]]))
    paths = [Path(s) for s in S2]; L = np.array([o['lens'][0], o['lens'][2]])
    xf = max(float(side(P)[:, 0].max()) for r, P in solids if r in ('body', 'wheel', 'head', 'guard', 'cam'))
    blind = None; tt = np.linspace(0.0, 0.995, 300)
    lo = -GUESSES['cam_tilt'] - GUESSES['cam_fov'] / 2 if o['key'] == 'fixed' else -90.0
    for dd in range(0, 3000, 2):
        T = np.array([xf + dd, 0.0]); seg = L + np.outer(tt, T - L)
        ang = np.degrees(np.arctan2(T[1] - L[1], T[0] - L[0]))
        if ang < lo:
            continue
        if not any(p.contains_points(seg[2:]).any() for p in paths):
            blind = dd; break
    allp = np.vstack([P for _, P in solids])
    return dict(roll=first, blind=blind, height=float(allp[:, 2].max()), front=xf, ground_hit=(xf + (blind or 0), 0.0))


def svg(o, B, m, X=(-520.0, 330.0), pad=24.0):
    """the side view, to one scale for every option"""
    solids = [('body', B['body'])] + [('body', P) for P in B['pods']] + [('head-' + k, P) for k, P in o['head'].items()] + [(r, P) for r, P in o['extra']]
    zmax = max(m['height'], (o['tail'][:, 2].max() if o['tail'] is not None else 0)) + 40.0; zmin = -36.0
    W, Hh = X[1] - X[0], zmax - zmin
    tx = lambda x: x - X[0]; ty = lambda z: zmax - z
    pts = lambda S: ' '.join(f'{tx(a):.1f},{ty(b):.1f}' for a, b in S)
    g = [f'<svg viewBox="0 0 {W:.0f} {Hh:.0f}" role="img" aria-label="{html.escape(o["name"])}, side view to scale">']
    g.append(f'<line class="ground" x1="0" y1="{ty(0):.1f}" x2="{W:.0f}" y2="{ty(0):.1f}"/>')
    for i in range(0, int(W), 50):
        g.append(f'<line class="tick" x1="{i}" y1="{ty(0):.1f}" x2="{i}" y2="{ty(0) + 6:.1f}"/>')
    # roll hull (side view), dashed
    A = np.vstack([P[:, [0, 2]] for _, P in solids] + [W_[:, [0, 2]] for W_ in B['wheels']]); hv = A[ConvexHull(A).vertices]
    g.append(f'<polygon class="hull" points="{pts(hv)}"/>')
    if o['tail'] is not None:
        T = o['tail'][:24]; g.append(f'<polyline class="tail" points="{pts(T[:, [0, 2]])}"/>')
        tip = T[-1]; g.append(f'<circle class="tailfoot" cx="{tx(tip[0]):.1f}" cy="{ty(tip[2]):.1f}" r="{8 if o["key"] == "stinger" else 12}"/>')
    for P in B['pods']:
        g.append(f'<polygon class="body" points="{pts(side(P))}"/>')
    g.append(f'<polygon class="body" points="{pts(side(B["body"]))}"/>')
    for x, _ in sorted(set((round(x, 1), 0) for x, _ in B['sp']['wheels'])):
        g.append(f'<circle class="tyre" cx="{tx(x):.1f}" cy="{ty(B["sp"]["R"]):.1f}" r="{B["sp"]["R"]:.1f}"/>'
                 f'<circle class="hub" cx="{tx(x):.1f}" cy="{ty(B["sp"]["R"]):.1f}" r="{B["sp"]["R"] * 0.35:.1f}"/>')
    for r, P in o['extra']:
        if r == 'dome':
            continue
        g.append(f'<polygon class="{ "cam" if r == "cam" else "guard"}" points="{pts(side(P))}"/>')
    for k in ('base', 'drum', 'cradle', 'ball'):
        if k in o['head']:
            ghost = ' ghost' if o['key'] == 'sunk' and k in ('base', 'drum') else ''     # inside the body, in its well
            g.append(f'<polygon class="head {k}{ghost}" points="{pts(side(o["head"][k]))}"/>')
    if o['shell']:
        _, c, rr = o['shell']; a = np.linspace(0, np.pi, 40)
        g.append(f'<polyline class="dome" points="{pts(np.c_[c[0] + rr * np.cos(a), c[2] + rr * np.sin(a)])}"/>')
    if o['lens'] is not None:
        Lx, Lz = o['lens'][0], o['lens'][2]
        if m['blind'] is not None:
            gx = m['front'] + m['blind']
            g.append(f'<line class="sight" x1="{tx(Lx):.1f}" y1="{ty(Lz):.1f}" x2="{tx(gx):.1f}" y2="{ty(0):.1f}"/>')
            g.append(f'<line class="blind" x1="{tx(m["front"]):.1f}" y1="{ty(0) + 14:.1f}" x2="{tx(gx):.1f}" y2="{ty(0) + 14:.1f}"/>')
            g.append(f'<text class="dim" x="{tx(m["front"] + m["blind"] / 2):.1f}" y="{ty(0) + 30:.1f}" text-anchor="middle">{m["blind"]:.0f}</text>')
        if o['key'] == 'fixed':
            for a in (-GUESSES['cam_tilt'] - GUESSES['cam_fov'] / 2, -GUESSES['cam_tilt'] + GUESSES['cam_fov'] / 2):
                r_ = 120.0; e = (Lx + r_ * np.cos(np.radians(a)), Lz + r_ * np.sin(np.radians(a)))
                g.append(f'<line class="fov" x1="{tx(Lx):.1f}" y1="{ty(Lz):.1f}" x2="{tx(e[0]):.1f}" y2="{ty(e[1]):.1f}"/>')
        g.append(f'<circle class="lens" cx="{tx(Lx):.1f}" cy="{ty(Lz):.1f}" r="5"/>')
    g.append(f'<text class="dim" x="{W - 8:.0f}" y="{ty(m["height"]) - 6:.1f}" text-anchor="end">{m["height"]:.0f} tall</text>')
    g.append(f'<line class="hgt" x1="{W - 4:.0f}" y1="{ty(m["height"]):.1f}" x2="{W - 4:.0f}" y2="{ty(0):.1f}"/>')
    g.append('</svg>')
    return ''.join(g)


def main():
    q, sp = base_spec(); opts, B = options(q, sp); rows = []
    for o in opts:
        m = measure(o, B); o['m'] = m; o['svg'] = svg(o, B, m)
        lands = sorted(set(m['roll']['end']) | set(m['roll']['side']))
        o['lands'] = lands
        rows.append((o['key'], lands, m['blind'], round(m['height'])))
        print(f"{o['key']:8s} lands first: end {m['roll']['end']} side {m['roll']['side']}; blind {m['blind']} mm; {m['height']:.0f} tall")
    L, Wd, Hd = K.body_print_size(dict(sp, head_n=0)); print('body', round(L), round(Wd), round(Hd))
    os.makedirs(OUT, exist_ok=True)
    names = dict(head='the head', dome='the dome', cam='the camera', body='the body or wheels',
                 guard=dict(hoops='the hoops', dome='the dome', chin='the shelf'))
    word = lambda o, rs: ' and '.join(dict.fromkeys(names[r][o['key']] if isinstance(names[r], dict) else names[r] for r in rs))
    data = dict(body=[round(L), round(Wd), round(Hd)], R=sp['R'], tail=round(sp['limb']['L'] + sp['limb'].get('L2', 0)) if sp.get('limb') else 0,
                guesses=GUESSES, options=[{k: o[k] for k in ('key', 'name', 'what', 'good', 'bad', 'svg')}
                                          | dict(blind=o['m']['blind'], height=round(o['m']['height']), end=word(o, o['m']['roll']['end']),
                                                 side=word(o, o['m']['roll']['side']), head_lands=any(r in ('head', 'dome', 'cam') for r in o['lands']))
                                          for o in opts])
    tpl = open(os.path.join(HERE, 'head_options_template.html'), encoding='utf-8').read()
    p = os.path.join(OUT, 'head_options.html'); open(p, 'w', encoding='utf-8').write(tpl.replace('/*DATA*/', 'window.HEAD=' + json.dumps(data) + ';'))
    print('wrote', p)


if __name__ == '__main__':
    main()
