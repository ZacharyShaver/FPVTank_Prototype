"""Scorpion Trainer (brainstorm, 2026-10-05): the rugged body on four wheels, for training. Zach: "the side portions
covering the top of the tracks have to go. for training the robot. at least for now. we have to use wheels tracks get
too complicated and we need to be able to run en mass to train."

    python chassis-v2/trainer.py       # ~2 min -> out/trainer.html, trainer_*.png, trainer.json

The wheels are `wheels.py` (four identical corner modules); the body is `rugged.py` with `SCORPION_LEGS=wheels`: no
fenders, no cage, the v1 insides (no motors in the hull), the e-stop moved off the fender onto the right side lid.
The control is the same body on the v2 tracks without the cage or an arm (`--control`, run in its own process because
the leg choice is fixed at import): out/trainer_control.json, rebuilt when its inputs are newer.

    SCORPION_WHEELS=6 python chassis-v2/trainer.py    # six wheels -> out/trainer6.html, trainer6_*.png, trainer6.json

Six wheels (2026-10-09): the same module, three a side (`wheels.py`). Its control is the four-wheel Trainer
(out/trainer.json, rerun first when older than its inputs). Both runs also cross rough ground in side view
(`side2d`, `terrain`): a ridge and a gap, the robot resting where its centre of mass is lowest at each step.
"""
import os, sys, json, time, subprocess
os.environ.setdefault('SCORPION_LEGS', 'wheels')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rugged as R
R.CAGE = False
import tail_arms as TA
from tail_arms import C, YC, OUT
IR = TA.IR
WHEELS = R.LEGS == 'wheels'
if WHEELS: import wheels as W
SIX = WHEELS and W.SIX
STEP = WHEELS and W.STEP                     # 2026-10-25: the step layout (wheels.py), against the four-wheel Trainer
VS4 = SIX or STEP                            # variants whose control is the four-wheel Trainer
SFX = '6' if SIX else 'step' if STEP else ''
NOW = 'Six wheels' if SIX else 'Step layout'
CONTROL = os.path.join(OUT, 'trainer.json' if VS4 else 'trainer_control.json')

# ---------------------------------------------------------------- rough ground in side view (quasi-static, 2D)
def side2d(M, it):
    """the robot from the side, relative to the ground: wheels (x, z, r), the lower and upper outline of everything
    else every 2 mm in X (sliced from the triangles' edges, not their vertices), the centre of mass"""
    c, _ = R.cog(it); g0 = R.ground(M)
    T_ = np.vstack([M[k]['t'] for k in M if not M[k].get('ghost') and not k.startswith(('tire_', 'rim_'))])
    xs = np.arange(-220.0, 240.01, 2.0); lo_, hi_ = np.full(len(xs), np.inf), np.full(len(xs), -np.inf)
    for i, j in ((0, 1), (1, 2), (2, 0)):
        a, b = T_[:, i][:, [0, 2]], T_[:, j][:, [0, 2]]
        i0 = np.ceil((np.minimum(a[:, 0], b[:, 0]) - xs[0]) / 2).astype(int); i1 = np.floor((np.maximum(a[:, 0], b[:, 0]) - xs[0]) / 2).astype(int)
        n = np.clip(i1 - i0 + 1, 0, None); e = np.repeat(np.arange(len(a)), n)
        idx = np.repeat(i0, n) + np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n)
        dx = b[e, 0] - a[e, 0]; flat = np.abs(dx) < 1e-9
        z = np.where(flat, np.minimum(a[e, 1], b[e, 1]), a[e, 1] + (xs[np.clip(idx, 0, len(xs) - 1)] - a[e, 0]) / np.where(flat, 1, dx) * (b[e, 1] - a[e, 1]))
        zt = np.where(flat, np.maximum(a[e, 1], b[e, 1]), z)
        ok = (idx >= 0) & (idx < len(xs)); np.minimum.at(lo_, idx[ok], z[ok]); np.maximum.at(hi_, idx[ok], zt[ok])
    k = np.isfinite(lo_)
    return dict(xs=xs[k].tolist(), lo=(lo_[k] - g0).tolist(), hi=(hi_[k] - g0).tolist(),
                wheels=[(float(x), float(W.Z_A - g0), float(W.R_T)) for x in W.AXLES.values()], cog=[float(c[0]), float(c[2] - g0)])

DXT = 0.5; XT = np.arange(-900.0, 900.01, DXT)                         # terrain grid
PHI = np.radians(np.arange(-40.0, 40.01, 0.25))
def rest(P, h, S):
    """the pose the robot P (side2d) settles in on terrain h (heights on XT) with its centre of mass over each X in S:
    of all pitches, the one with the centre of mass lowest and nothing below the terrain. Returns per S: pitch (deg),
    the body's clearance over the terrain, and how far each wheel's centre sits below its height on flat ground"""
    r = P['wheels'][0][2]; u = np.arange(-r, r + 1e-9, DXT); n = len(u) // 2
    E = np.full(len(XT), -np.inf)                                       # E(x): the lowest a wheel's centre over x can sit
    for i, du in enumerate(u):
        sh = np.full(len(XT), -np.inf); j = i - n
        if j >= 0: sh[:len(XT) - j] = h[j:]
        else: sh[-j:] = h[:len(XT) + j]
        E = np.maximum(E, sh + np.sqrt(max(r * r - du * du, 0.0)))
    cx, cz = P['cog']; B = np.c_[np.array(P['xs']) - cx, np.array(P['lo']) - cz]; Wc = np.array([[w[0] - cx, w[1] - cz] for w in P['wheels']])
    S = np.asarray(S, float); best = np.full(len(S), np.inf); out = [None] * len(S)
    at = lambda arr, x: arr[np.clip(np.rint((x - XT[0]) / DXT).astype(int), 0, len(XT) - 1)]
    for ph in PHI:
        cs, sn = np.cos(ph), np.sin(ph); rot = lambda Q: np.c_[Q[:, 0] * cs - Q[:, 1] * sn, Q[:, 0] * sn + Q[:, 1] * cs]
        b, w = rot(B), rot(Wc)
        zb = at(h, S[:, None] + b[:, 0]) - b[:, 1]; zw = at(E, S[:, None] + w[:, 0]) - w[:, 1]
        zc = np.maximum(zb.max(1), zw.max(1)); better = zc < best - 1e-9
        for i in np.nonzero(better)[0]:
            best[i] = zc[i]; out[i] = (np.degrees(ph), float((zc[i] - zb[i]).min()), (r - (zc[i] + w[:, 1])).tolist(), zc[i])
    return out

def terrain(P):
    """the sharpest ridge it crosses with nothing but its wheels touching (bisection on the ridge's slope), and how far
    a wheel drops into gaps of every width"""
    S = np.arange(-360.0, 361.0, 4.0); ax = [w[0] for w in P['wheels']]
    res = dict(low=min(z for x, z in zip(P['xs'], P['lo']) if min(ax) <= x <= max(ax)))   # lowest point between the end axles
    def ridge(a):
        o = rest(P, -np.tan(np.radians(a)) * np.abs(XT), S); i = int(np.argmin([q[1] for q in o])); return o[i][1], float(S[i]), o[i][0]
    lo, hi = 0.0, 40.0                                                  # past 40 it can't pitch onto the side (PHI)
    for _ in range(9):
        m = (lo + hi) / 2
        if ridge(m)[0] > 0.5: lo = m
        else: hi = m
    res['ridge'] = lo; cl, s, ph = ridge(lo); res['ridge_pose'] = dict(a=lo, s=s, pitch=ph, clear=cl)
    gaps = []
    for w in range(0, 251, 10):
        h = np.where((XT > 0) & (XT < w), -400.0, 0.0); o = rest(P, h, np.arange(-360.0, 361.0 + w, 4.0))
        gaps.append(dict(w=w, drop=float(max(max(q[2]) for q in o)), clear=float(min(q[1] for q in o))))
    res['gaps'] = gaps
    ok = [g['w'] for g in gaps if g['drop'] <= GAP_DROP and g['clear'] > 0.5]
    res['gap_ok'] = max([w for w in ok if all(g['drop'] <= GAP_DROP and g['clear'] > 0.5 for g in gaps if g['w'] <= w)], default=0)
    return res
GAP_DROP = 15.0                                                         # mm a wheel may sink into a gap and still climb out*

def analyse(M, it):
    c, m = R.cog(it); g0 = R.ground(M); bel = R.belly_profile(M)
    xr, xf = (W.AXLES['R'], W.AXLES['F']) if WHEELS else (-103, 123)    # between the contacts (rugged.py's range on tracks)
    between = lambda i: min(p[i] for p in bel if p[i] is not None and xr <= p[0] <= xf)
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v.get('ghost')])
    D = dict(rests=R.rest_states(M, it), contact=R.first_contact(M), climb=R.climb(M, it),
                climb_arm=R.climb(M, it + [('arm', 300, (R.AX + R.BODY_DX, YC, R.PZ + 60))]), ends=R.ends(M), mass=m,
                belly=dict(centre=between(1), lowest=between(2)), belly_profile=bel,
                size=dict(L=float(np.ptp(A[:, 0])), W=float(np.ptp(A[:, 1])), H=float(A[:, 2].max() - g0)),
                headon=R.headon(M).tolist(), cog_og=float(c[2] - g0), legs=R.LEGS,
                drive_g=float(sum(g for k, g, _ in it if M.get(k, {}).get('grp') == 'legs')))
    if WHEELS:
        t0 = time.time(); D['side2d'] = side2d(M, it); D['terrain'] = terrain(D['side2d'])
        print('terrain: ridge %.1f deg, gaps ok to %d mm (%.0f s)' % (D['terrain']['ridge'], D['terrain']['gap_ok'], time.time() - t0))
    return D

ISO = ((820, -760, 430), (10, YC, 90))
def control():
    """the same body on the v2 tracks, no cage, no arm: its numbers and one picture"""
    M, it, O = R.assemble(); D = analyse(M, it)
    json.dump(D, open(CONTROL, 'w'), indent=1, default=float)
    IR.render(R.scene(M), ISO[0], ISO[1], os.path.join(OUT, 'trainer_before.png'), size=(1300, 860)); print('wrote', CONTROL)

def stale():
    if not os.path.exists(CONTROL): return True
    ins = [os.path.join(HERE, f) for f in ('rugged.py', 'hull.py') + (('wheels.py', 'trainer.py') if VS4 else ('legs_v2.py',))] + [os.path.join(OUT, '_hull_meshes.npz')]
    return os.path.getmtime(CONTROL) < max(os.path.getmtime(p) for p in ins)

# ---------------------------------------------------------------- fit checks: 1 mm voxels, a control for every zero
def checks(M):
    """every row compares part with part and sums: stacking parts that share a surface (the tyre on its rim) into one
    mesh merges their crossings and breaks the parity scan (docs/lessons/2026-10-05-stacked-copies-hide-overlaps.md)"""
    P = lambda *ks: [M[k]['t'] for k in ks]
    ks = lambda *pre: [k for k in M if k.startswith(pre)]
    def inb(L, d):                                                      # toward the centre line by d, each side its own way
        out = []
        for t in L:
            t = t.copy(); t[:, :, 1] -= d * np.sign(t[:, :, 1] - YC); out.append(t)
        return out
    sh = lambda L, v: [t + v for t in L]
    pods, mots, whl = P(*ks('pod_')), P(*ks('motor_')), P(*ks('rim_', 'tire_'))
    body = P(*[k for k in M if not M[k].get('ghost') and M[k]['grp'] != 'legs'])
    HX = R.Hm.HX + R.BODY_DX
    sweep = [C.T(M[k]['t'] - [HX, YC, 0], C.Rz(a), (HX, YC, 0)) for a in range(0, 360, 30) for k in ('cradle', 'ball')]
    around = P(*[k for k in ('carapace', 'tdeck', 'tdeck_lids', 'claw0', 'claw1', 'bed', 'grommet0', 'grommet1', 'estop') if k in M])
    power = ['ubec', 'arm_ubec', 'pca', 'ina219', 'wifi', 'alarm', 'pi_switch', 'esc_L', 'esc_R', 'pack_L', 'pack_R']
    def pairs(keys, shift={}):
        t = {k: M[k]['t'] + shift.get(k, [0, 0, 0]) for k in keys}
        return float(sum(C.overlap_mm3(t[a], t[b]) for i, a in enumerate(keys) for b in keys[i + 1:]))
    lift = [t + [0, 0, dz] for dz in range(2, 62, 4) for t in P('pack_L', 'pack_R')]
    e = M['estop']['t']; ec = e.reshape(-1, 3).mean(0); toward = np.array([HX - ec[0], YC - ec[1], 0]); toward /= np.linalg.norm(toward)
    gap = estop_gap(M); leads = P(*ks('seal_lead'))
    if SIX:
        def tyres(dx):                                                  # adjacent tyres, pair by pair; dx moves the middle ones
            t = lambda c, s: M['tire_' + c + s]['t'] + ([dx, 0, 0] if c == 'M' else [0, 0, 0])
            return float(sum(C.overlap_mm3(t(a, s), t(b, s)) for s in 'LR' for a, b in (('F', 'M'), ('M', 'R'))))
        ck = np.vstack([np.asarray(TA.cq_tris(cheek(y)), float).reshape(-1, 3, 3) for y in (TA.YL, TA.YR)]) + [R.BODY_DX, 0, 0]
    if STEP:
        def fr(dx):                                                     # front tyre against rear tyre, each side; dx moves the rear ones forward
            return float(sum(C.overlap_mm3(M['tire_F' + s]['t'], M['tire_R' + s]['t'] + [dx, 0, 0]) for s in 'LR'))
        gap_fr = W.AXLES['F'] - W.AXLES['R'] - 2 * W.R_T
        def screws(dz):                                                 # the drop plates' 16 M3 x 10: through the plate into the pad's inserts
            out = []
            for xa in W.AXLES.values():
                for sg in (1, -1):
                    for dx in (-17, 17):
                        for hz in W.HOLE_Z:
                            out.append(TA.cyl_tris((xa + dx, YC + sg * (W.Y_FL0 + W.FLANGE), hz + dz), (xa + dx, YC + sg * (W.WALL_Y + W.PAD - 5.5), hz + dz), 1.45, 16))
            return out
    rows = [
        ('Pods vs the tub', pods, P('tub'), 'each flange 0.2 off its pad'),
        ('Pods 2 mm inboard (control)', inb(pods, 2.0), P('tub'), 'must read > 0: into the pads'),
        ('Motors vs pods and tub', mots, pods + P('tub'), 'in the tube, the gearbox face on the lip'),
        ('Motors 1 mm outward (control)', inb(mots, -1.0), pods, 'must read > 0: the gearbox into the lip'),
        ('Wheels and tyres vs pods and motors', whl, pods + mots, 'the dish %d round the pod; the hub 2 off the lip; the shaft in the bore' % (W.RIM_R0 - W.POD_R)),
        ('Wheels 2.5 mm inboard (control)', inb(whl, 2.5), pods, 'must read > 0: the hub onto the lip'),
        ('Wheels and tyres vs the body', whl, body, 'no fenders: nothing over or beside them'),
        ('Wheels 45 mm inboard (control)', inb(whl, 45.0), body, 'must read > 0: the tyre is 42 off the hull wall'),
    ] + ([
        ('Tyres side by side (front with middle, middle with rear)', tyres(0.0), None, '%.0f mm between lug tips' % (W.PITCH - 2 * W.R_T)),
        ('Middle tyres 10 mm forward (control)', tyres(10.0), None, 'must read > 0'),
        ('Front pads\' cheeks vs claws, claw caps, lights', [ck], P(*[k for k in M if k.startswith(('claw', 'light'))]), 'the cheek fills back to the slanted nose wall, under the claws\' roots'),
        ('Cheeks 2 mm higher (control)', [ck + [0, 0, 2.0]], P(*[k for k in M if k.startswith(('claw', 'light'))]), 'must read > 0: the claws\' roots are 1 over its trimmed top'),
    ] if SIX else []) + ([
        ('Front tyre vs rear tyre, each side', fr(0.0), None, '%.0f mm between lug tips' % gap_fr),
        ('Rear tyres %.0f mm forward (control)' % (gap_fr + 4), fr(gap_fr + 4), None, 'must read > 0'),
        ('Drop plates\' 16 M3 screws vs tub and plates', screws(0.0), P('tub') + pods, 'through the plates\' holes into the pads\' inserts, all above the floor'),
        ('Screws 3 mm lower (control)', screws(-3.0), P('tub') + pods, 'must read > 0: off the holes'),
    ] if STEP else []) + [
        ('Head, 12 pan angles, vs everything round it', sweep, around, 'carapace, deck, side lids, claws, bed, grommets, e-stop'),
        ('Head 15 mm lower (control)', sh(sweep, [0, 0, -15.0]), around, 'must read > 0: the turret deck is under it'),
        ('E-stop %.0f mm toward the head (control)' % (gap + 3), sweep, [e + toward * (gap + 3)], 'must read > 0: it sits %.0f off the cradle\'s sweep' % gap),
        ('Packs, ESCs, UBECs, power parts vs each other', pairs(power), None, 'as on the v1 legs: no motors inside now'),
        ('Arm UBEC 12 mm forward (control)', pairs(power, {'arm_ubec': [12.0, 0, 0]}), None, 'must read > 0: it runs into the ESC'),
        ('All of those vs tub, carapace', P(*power), P('tub', 'carapace'), ''),
        ('Packs 3 mm lower (control)', sh(P('pack_L', 'pack_R'), [0, 0, -3.0]), P('tub'), 'must read > 0: they stand on the bay floor'),
        ('Lead grommets vs tub and packs', leads, P('tub', 'pack_L', 'pack_R'), 'in the wall\'s notches, over the packs'),
        ('Lead grommets 1 mm lower (control)', sh(leads, [0, 0, -1.0]), P('tub'), 'must read > 0: the notch\'s floor'),
        ('Pi + HAT + Hailo vs tub, PCA, carapace, bed', P('pi', 'hat', 'hailo'), P('tub', 'pca', 'carapace', 'bed'), ''),
        ('Pi 8 mm lower (control)', sh(P('pi', 'hat', 'hailo'), [0, 0, -8.0]), P('tub'), 'must read > 0'),
        ('Head base vs tub, turret deck', P('base'), P('tub', 'tdeck'), ''),
        ('Head base 3 mm lower (control)', sh(P('base'), [0, 0, -3.0]), P('tub'), 'must read > 0'),
        ('Packs lifted out (every 4 mm to 60) vs the turret deck ring', lift, P('tdeck', 'base'), 'with the carapace and the side lids off'),
        ('The same lift vs the side lids (control)', lift, P('tdeck_lids'), 'must read > 0: the lids do cover them'),
    ]
    out = []
    for what, a, b, why in rows:
        v = a if b is None else float(sum(C.overlap_mm3(x, y) for x in a for y in b))
        out.append(dict(what=what, mm3=float(v), why=why)); print('%-58s %9.0f mm3' % (what, v))
    return out

def cheek(y):
    """the front pad and its cheek on the wall at y, as rugged.tub() adds them (body frame), on their own"""
    return R.wheel_pad(W.AXLES['F'] - R.BODY_DX, y).val()

def estop_gap(M):
    """the e-stop's distance from the cradle and ball, over the 12 pan angles (plan view, nearest points)"""
    HX = R.Hm.HX + R.BODY_DX; e = M['estop']['t'].reshape(-1, 3)
    H = np.vstack([M[k]['t'].reshape(-1, 3) for k in ('cradle', 'ball')]); H = H[H[:, 2] < e[:, 2].max()] - [HX, YC, 0]
    rmax = np.hypot(H[:, 0], H[:, 1]).max(); re = np.hypot(e[:, 0] - HX, e[:, 1] - YC).min()
    return float(re - rmax)

# ---------------------------------------------------------------- pictures
def renders(M):
    P = R.scene(M); names = []
    for fn, cam, foc, lab in (('trainer%s_front.png' % SFX, ISO[0], ISO[1], 'Front 3/4'),
                              ('trainer%s_rear.png' % SFX, (-820, -700, 520), (-10, YC, 100), 'Rear 3/4'),
                              ('trainer%s_side.png' % SFX, (20, -1350, 110), (10, YC, 95), 'Side'),
                              ('trainer%s_head_on.png' % SFX, (1400, YC, 95), (0, YC, 95), 'Head-on')):
        IR.render(P, cam, foc, os.path.join(OUT, fn), size=(1300, 860)); names.append((fn, lab))
    from PIL import Image, ImageDraw, ImageFont
    try: f = ImageFont.truetype('arialbd.ttf', 34)
    except Exception: f = ImageFont.load_default()
    ims = [Image.open(os.path.join(OUT, n)) for n, _ in names]; w, h = ims[0].size
    sh = Image.new('RGB', (w * 2, h * 2), 'white'); d = ImageDraw.Draw(sh)
    for i, (im, (_, lab)) in enumerate(zip(ims, names)):
        x, y = (i % 2) * w, (i // 2) * h; sh.paste(im, (x, y)); d.text((x + 24, y + 18), lab, fill=(30, 33, 30), font=f)
    sh.resize((w, h), Image.LANCZOS).save(os.path.join(OUT, 'trainer%s_sheet.png' % SFX))
    ba = Image.new('RGB', (w * 2, h), 'white'); d = ImageDraw.Draw(ba)                                   # before / after
    pair = (('trainer_front.png', 'Before: four wheels'), ('trainer6_front.png', 'Now: six wheels')) if SIX else \
           (('trainer_front.png', 'Before: the Trainer'), ('trainerstep_front.png', 'Now: the step layout')) if STEP else \
           (('trainer_before.png', 'Before: v2 tracks, fenders over them'), ('trainer_front.png', 'Now: four wheels, no fenders'))
    for i, (fn, lab) in enumerate(pair):
        ba.paste(Image.open(os.path.join(OUT, fn)), (i * w, 0)); d.text((i * w + 24, 18), lab, fill=(30, 33, 30), font=f)
    ba.resize((w, h // 2), Image.LANCZOS).save(os.path.join(OUT, 'trainer%s_before_after.png' % SFX)); print('wrote trainer%s_sheet.png, _before_after.png' % SFX)

def side_sketch(M, B=None):
    body = np.vstack([M[k]['t'] for k in M if not M[k].get('ghost') and M[k]['grp'] in ('hull', 'head', 'tpu')])
    if VS4:                                                             # the four-wheel Trainer's wheels, dashed, on the same ground
        g0 = W.G0; circ = [(x, z + g0, r) for x, z, r in B['side2d']['wheels']]
        W.sketch(M, os.path.join(OUT, 'trainer%s_side_sketch.png' % SFX), body=body, circles=circ,
                 title=('Left side from outside: %s modules (wheel Ø%d on its pod), the body (green), the four-wheel Trainer\'s Ø%d wheels (dashed)'
                        % ('three' if SIX else 'two', 2 * W.R_T, 2 * circ[0][2])) + ('; same ground, so the body sits %.0f higher on them' % (W.BELLY - 32.4) if STEP else ''))
        return
    import legs_v2 as L2
    tr = L2.meshes()[0]['track_L']['t'] + [0, 0, W.G0 - L2.G0]                 # the v2 track, on this ground
    W.sketch(M, os.path.join(OUT, 'trainer_side_sketch.png'), body=body, before=tr)

def terrain_fig(D, B, path):
    """the ridge each robot's worst moment on the variant's limit ridge, and the drop into gaps"""
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    a = D['terrain']['ridge']; fig = plt.figure(figsize=(13, 7.6)); gs = fig.add_gridspec(2, 2, height_ratios=[1, 0.95])
    for j, (P, lab, col) in enumerate(((B['side2d'], 'Four wheels (its limit: %.0f°)' % B['terrain']['ridge'], '#7A8691'), (D['side2d'], NOW, '#2F7A5A'))):
        ax = fig.add_subplot(gs[0, j]); h = -np.tan(np.radians(a)) * np.abs(XT)
        S = np.arange(-360.0, 361.0, 4.0); o = rest(P, h, S); i = int(np.argmin([q[1] for q in o])); ph, cl = o[i][0], o[i][1]
        cx, cz = P['cog']; r = np.radians(ph); cs, sn = np.cos(r), np.sin(r)
        def pose(x, z):
            x, z = np.asarray(x) - cx, np.asarray(z) - cz; return S[i] + x * cs - z * sn, o[i][3] + x * sn + z * cs
        xl, zl = pose(P['xs'], P['lo']); xh, zh = pose(P['xs'], P['hi'])
        ax.fill(np.r_[xl, xh[::-1]], np.r_[zl, zh[::-1]], color=col, alpha=0.35, lw=0)
        ax.plot(xl, zl, color=col, lw=1.4)
        for wx, wz, wr in P['wheels']:
            x, z = pose(wx, wz); ax.add_patch(plt.Circle((x, z), wr, facecolor='#222', alpha=0.85)); ax.plot([x], [z], '+', color='w')
        xx = np.linspace(-260, 260, 3); ax.fill_between(xx, -np.tan(np.radians(a)) * np.abs(xx), -200, color='#C8B48A', alpha=0.8, lw=0)
        bx, bz = pose(P['xs'], P['lo']); k = np.argmin(bz - (-np.tan(np.radians(a)) * np.abs(bx)))
        if cl <= 0.5: ax.plot([bx[k]], [bz[k]], 'o', ms=13, mfc='none', mec='#B8332A', mew=2.4)
        ax.set_title('%s on a ridge of %.0f° sides: %s' % (lab, a, 'its belly touches' if cl <= 0.5 else '%.0f mm clear at worst' % cl), loc='left', fontsize=11)
        ax.set_xlim(-260, 260); ax.set_ylim(-150, 200); ax.set_aspect('equal'); ax.axis('off')
    ax = fig.add_subplot(gs[1, :])
    for T, lab, col in ((B['terrain'], 'Four wheels', '#7A8691'), (D['terrain'], NOW, '#2F7A5A')):
        w = [g['w'] for g in T['gaps']]; dr = [g['drop'] for g in T['gaps']]
        ax.plot(w, dr, '-o', color=col, ms=4, lw=2, label='%s: crosses gaps to %d mm' % (lab, T['gap_ok']))
    ax.axhline(GAP_DROP, color='#B8332A', ls='--', lw=1); ax.text(248, GAP_DROP - 4.5, ha='right',  s= 'a wheel %.0f mm down: about what it can climb back out of*' % GAP_DROP, color='#B8332A', fontsize=9)
    ax.set_xlabel('gap width, mm'); ax.set_ylabel('deepest a wheel drops, mm'); ax.set_ylim(0, 60); ax.grid(alpha=0.3); ax.legend(loc='upper left', frameon=False)
    ax.set_title('Driving over a gap (a trench across its path)', loc='left', fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=105); plt.close(fig); print('wrote', path)

# ---------------------------------------------------------------- page
def page(M, D):
    import base64
    tohex = lambda rgb: int(rgb[0] * 255) << 16 | int(rgb[1] * 255) << 8 | int(rgb[2] * 255)
    D['m'] = {}
    for k, v in M.items():
        if v.get('ghost'): continue
        Tk = C.decimate(v['t'], 2600 if k.startswith('tire_') else C.faces_for(k)); V, F = C.quant(Tk)
        D['m'][k] = {'v': C.b64(V), 'f': C.b64(F), 'i32': F.dtype == np.uint32, 'c': tohex(v['rgb']), 'grp': v['grp'], 'label': v['label'], 'note': v.get('note', '')}
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v.get('ghost')]); D['centre'] = ((A.min(0) + A.max(0)) / 2).round(1).tolist(); D['yc'] = YC
    figs = (('sketch', 'side_sketch'), ('ba', 'before_after')) + ((('terr', 'terrain'),) if VS4 else ()) + ((('steps', 'steps'),) if STEP else ())
    for k, fn in figs:
        D[k] = base64.b64encode(TA._small(os.path.join(OUT, 'trainer%s_%s.png' % (SFX, fn)), 1300)).decode()
    html = open(os.path.join(HERE, 'trainer%s_template.html' % SFX), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D, default=float) + ';')
    p = os.path.join(OUT, 'trainer%s.html' % SFX); open(p, 'w', encoding='utf-8').write(html); print('page %.1f MB' % (os.path.getsize(p) / 1e6))

if __name__ == '__main__':
    t0 = time.time()
    if '--control' in sys.argv:
        assert R.LEGS == 'v2', 'the control runs with SCORPION_LEGS=v2'
        control(); sys.exit()
    if stale():
        if VS4:
            print('control: the four-wheel Trainer ...')
            subprocess.run([sys.executable, os.path.abspath(__file__)], env=dict(os.environ, SCORPION_LEGS='wheels', SCORPION_WHEELS='4'), check=True)
        else:
            print('control: the same body on the v2 tracks ...')
            subprocess.run([sys.executable, os.path.abspath(__file__), '--control'], env=dict(os.environ, SCORPION_LEGS='v2'), check=True)
    B = json.load(open(CONTROL))
    M, it, O = R.assemble()
    D = analyse(M, it); D['before'] = {k: B[k] for k in ('rests', 'contact', 'climb', 'climb_arm', 'ends', 'mass', 'belly', 'size', 'drive_g')
                                       + (('terrain', 'wheels') if VS4 else ())}
    D['wheels'] = W.numbers(M); D['shop'] = W.SHOP; D['estop_gap'] = estop_gap(M)
    bj = os.path.join(HERE, '..', 'research', 'results', 'chassis3', 'built.json')    # research/tumble/built3.py: down steps
    if STEP and os.path.exists(bj):
        r_ = json.load(open(bj))['results']; D['stepres'] = {k: dict(down=v['down'], stuck=v['stuck']) for k, v in r_.items()}
    if SIX:                                                             # each motor's share, six against four (same gauge)
        def share(m, ax, cx, r):
            n = 2 * len(ax); lever = np.mean([abs(x - cx) for x in ax.values()])   # skid steer: wheels scrub sideways at their distance from the centre of mass
            return dict(n=n, hill=m * r / n, turn=m * lever / n, lever=lever)
        s6, s4 = share(D['mass'], W.AXLES, D['climb']['cog'][0], W.R_T), share(B['mass'], B['wheels']['axles'], B['climb']['cog'][0], B['wheels']['r'])
        D['per_motor'] = dict(six=s6, four=s4, hill=s6['hill'] / s4['hill'], turn=s6['turn'] / s4['turn']); print('per motor', D['per_motor'])
    print('rests', [(r['name'], round(r['tilt'], 1)) for r in D['rests']]); print('rests before', [(r['name'], round(r['tilt'], 1)) for r in B['rests']])
    for k in ('contact', 'ends', 'belly', 'size', 'mass', 'drive_g', 'estop_gap'): print(k, D[k], '| before', B.get(k))
    print('climb', {k: round(v, 1) for k, v in D['climb'].items() if isinstance(v, float)}, '| before', {k: round(v, 1) for k, v in B['climb'].items() if isinstance(v, float)})
    D['checks'] = checks(M)
    json.dump({k: v for k, v in D.items()}, open(os.path.join(OUT, 'trainer%s.json' % SFX), 'w'), indent=1, default=float)
    side_sketch(M, B)
    if VS4: terrain_fig(D, B, os.path.join(OUT, 'trainer%s_terrain.png' % SFX))
    if '--no-render' not in sys.argv: renders(M)
    if os.path.exists(os.path.join(HERE, 'trainer%s_template.html' % SFX)): page(M, D)
    print('done %.0f s' % (time.time() - t0))
