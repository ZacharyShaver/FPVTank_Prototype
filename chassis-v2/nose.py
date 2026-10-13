"""Scorpion nose section (2026-10-12): the head v2 bench stand's wire pocket built into the body, and the piece of the tub
round the head as a first body print. The Trainer body (rugged.py on wheels.py's corners) as it stands.

Zach, with bench stand v2 printing: "the point of this is to simulate where it would sit in the actual body ... the stand
should be like a section out of that", then "lets start on the work to integrate this into the body i would like to see
what that looks like". The stand (head-v2/fixes/bench_stand.py, RAISED) holds the floor plate on a ledge 12 mm over a
pocket; a slotted post under the pan axis takes the tilt servo's wires straight down, inside the circle the small gear's
three M3 heads turn in, and they leave at its foot toward the gear bay's end. The body stands the base straight on the nose
floor (rugged.py, raised 10 for rocks), so it needs the same pocket. Two ways, both drawn:

  A  the pocket hangs under the nose floor; the head stays where it is. The wires come up out of a chimney just aft of the
     base, into the tub. Costs belly: under the head the bottom is 12 lower.
  B  the head stands 12 higher, on the pocket, as on the stand; the nose floor stays whole. The wires leave through an arch
     into the tub. Costs height: the ball, the turret deck and what meets them go up 12.

The head frame (head-v2: mm, Z 0 at the coil deck, the pan axis at the origin, the gear bay toward +X) goes into the body
turned 180 deg about the axis (concept.head_parts), so the bay points aft. World X = body X + rugged.BODY_DX.

    python chassis-v2/nose.py        # ~2 min -> out/nose.html, out/nose_section_A.stl, out/nose.json
"""
import os, sys, json, time, base64
os.environ.setdefault('SCORPION_LEGS', 'wheels')
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rugged as R
from rugged import cq, cq_tris, cyl_tris, Hm, YC, YL, YR, OUT, C
import wheels as W

PROTO = os.path.dirname(HERE)
FIT = os.path.join(PROTO, 'head-v2', 'out', 'fit-view', 'data.js')   # the head's meshes in the head frame (fixes/fit_view.py)

# ---- the stand's numbers (head-v2/fixes/bench_stand.py v2 and pan_coil_b), head frame -------------------------------
TIP = 31.0 * 40 / 60 + 1.0          # pan_coil_b R_IN_G + TOOTH: 21.67
BX0, BX1, BY, BRC = -14.0, 31.0 + TIP + 3.5, TIP + 4.0, 3.0    # the gear bay's outline (bay(), floor())
REST_Z = -39.4                     # the floor plate's underside = the nose floor's top in A
CLEAR, LEDGE, LEDGE_DEG = 0.4, 6.0, 30.0
RISE, SOCKET_H = 12.0, 8.0
WALL = R.WALL                      # 2.6, the tub's
POST_R, BORE_R, SLOT_W, POST_GAP = 5.0, 2.4, 2.2, 3.0
NOTCH_R = 2.6
TRIM_R = 8.5 + 0.6 + 0.25 + 1.0    # AX_FLOOR_HOLE_R + 1: clear of the M3 heads' sweep (AX_SCREW_R 5.9 + head 2.85 + 0.6)
FLOOR_SCREWS = [(x, s * (TIP + 1.5 - 1.8)) for x in (-12.0 + 1.8, BX1 - 2.0 - 1.8) for s in (-1, 1)]
DOOR_W, DOOR_H = 2 * BORE_R, 4.0
ARCH_W, ARCH_H = 8.0, 4.0
CHIM_X0, CHIM_X1, CHIM_W = BX1 + CLEAR + WALL + 0.4, BX1 + CLEAR + WALL + 6.4, 8.0   # A: the chimney past the bay's end
CUT_X = 26.0                       # body X: the printed nose section is the tub forward of this
# ---- holding the head down (2026-10-12): the turret deck ring clamps the base, on four posts --------------------------------
# On the stand the base just drops into its socket; a tumbling robot would throw it. The deck ring (rugged.turret_deck's
# band round the well) gets a lip over the base's top rim, the bearing seat's ring (r 29.05..31, its top at the coil deck's
# Z + 6.6), and four M3 x 12 hold it to posts from the nose floor. rugged.tub()'s walls stop at TUB_TOP (57.4) while the
# deck went up 10 with the head: forward of the carapace the walls now rise to the deck's underside.
LIP_R0, LIP_T = 29.6, 1.8          # the lip's inner edge (over the seat ring, clear of the 6809's r 29.0); its thickness
DECK_HOLE_R = 31.4                 # under the lip: 0.4 off the seat ring's outside (r 31.0)
RING_HW = 35.5                     # rugged.turret_deck: the ring's band, either side of the centre line
POST_RR = 3.5                      # the posts; M3 pilots 12 deep in their tops
POSTS = [(46.0, 32.0), (46.0, -32.0), (-15.0, 32.0), (-15.0, -32.0)]   # head frame: beside the bay's long sides (clear of
                                   # the packs at |y| 37.2) and, at the front, outside the seat ring (r 35.4 - 3.5 > 31.5)
CLAMP_SCREW_L = 12.0

VARIANTS = {'A': dict(dz=0.0, label='A: pocket under the nose floor'),
            'B': dict(dz=RISE, label='B: head 12 higher, pocket on the floor')}


def rr_pts(x0, x1, y0, y1, r, n=8):
    P = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)):
        for t in np.linspace(a0, a0 + 90, n):
            P.append((cx + r * np.cos(np.radians(t)), cy + r * np.sin(np.radians(t))))
    return P


def off(d):
    """the bay's outline grown by d (negative: in), as a polygon"""
    return rr_pts(BX0 - d, BX1 + d, -BY - d, BY + d, max(BRC + d, 0.8))


def prism(P, z0, z1):
    return cq.Workplane('XY').workplane(offset=z0).polyline(P).close().extrude(z1 - z0)


def loft(P0, z0, P1, z1):
    w = lambda P, z: cq.Wire.makePolygon([cq.Vector(x, y, z) for x, y in P], close=True)
    return cq.Workplane('XY').add(cq.Solid.makeLoft([w(P0, z0), w(P1, z1)], True))


def pointed_x(y0, y1, z0, z1, x0, x1):
    """a slot through X from x0 to x1: |y - yc| <= w/2, straight from z0 to z1, then a roof LEDGE_DEG off vertical"""
    w = y1 - y0; yc = (y0 + y1) / 2; top = z1 + (w / 2) / np.tan(np.radians(LEDGE_DEG))
    pts = [(y0, z0), (y1, z0), (y1, z1), (yc, top), (y0, z1)]
    return cq.Workplane('YZ').workplane(offset=x0).polyline(pts).close().extrude(x1 - x0)


def mount(variant):
    """the pocket, its ledge and socket, the post, and the wires' way out, in the head frame: (add, cut) solids"""
    fz = REST_Z - RISE                                                  # the pocket's floor (top face)
    zc = REST_Z - (LEDGE + CLEAR) / np.tan(np.radians(LEDGE_DEG))       # where the ledge's chamfer starts
    add = prism(off(CLEAR + WALL), fz - WALL, REST_Z + SOCKET_H)        # pod + socket walls
    hollow = prism(off(CLEAR), fz, zc).union(loft(off(CLEAR), zc, off(-LEDGE), REST_Z + 0.01))
    cut = hollow.union(prism(off(CLEAR), REST_Z, REST_Z + SOCKET_H + 1))   # the socket the bay drops into
    cut = cut.union(cq.Workplane('XY').workplane(offset=fz + 0.5).circle(TRIM_R).extrude(REST_Z + 0.5 - fz - 0.5))
    for x, y in FLOOR_SCREWS:
        cut = cut.union(cq.Workplane('XY').workplane(offset=fz + 0.5).center(x, y).circle(NOTCH_R).extrude(REST_Z + 1 - fz))
    if variant == 'A':   # a chimney past the bay's +X end: through the pod's wall at the floor, then up into the tub
        add = add.union(prism(rr_pts(CHIM_X0 - WALL - 1.0, CHIM_X1 + WALL, -CHIM_W / 2 - WALL, CHIM_W / 2 + WALL, 2.0),
                              fz - WALL, REST_Z + 6.0))
        cut = cut.union(pointed_x(-ARCH_W / 2, ARCH_W / 2, fz, fz + ARCH_H, BX1 - 3.0, CHIM_X0 + 1.0))
        cut = cut.union(prism(rr_pts(CHIM_X0, CHIM_X1, -CHIM_W / 2, CHIM_W / 2, 1.5), fz, REST_Z + 30))
    else:                # out through an arch in the riser's +X wall, into the tub at the nose floor
        cut = cut.union(pointed_x(-ARCH_W / 2, ARCH_W / 2, fz, fz + ARCH_H, BX1 - 3.0, BX1 + CLEAR + WALL + 1.0))
    # the post on the axis: slot toward -X (away from the wires' pull), a door at its foot toward +X
    top = REST_Z - POST_GAP
    post = cq.Workplane('XY').workplane(offset=fz - 0.5).circle(POST_R).extrude(top - fz + 0.5)
    pc = cq.Workplane('XY').workplane(offset=fz).circle(BORE_R).extrude(top - fz + 1)
    pc = pc.union(cq.Workplane('XY').workplane(offset=fz).center(-(POST_R + 1) / 2, 0).rect(POST_R + 1, SLOT_W).extrude(top - fz + 1))
    pc = pc.union(pointed_x(-DOOR_W / 2, DOOR_W / 2, fz, fz + DOOR_H, 0.0, POST_R + 1.0))
    return add, cut, post.cut(pc)


def to_body(wp_, dz):
    return wp_.rotate((0, 0, 0), (0, 0, 1), 180).translate((Hm.HX, Hm.HY, R.Z0H + dz))


def deck_z(dz):
    return R.TDECK + dz


def posts_body(dz):
    return [(Hm.HX - x, Hm.HY - y) for x, y in POSTS]


def deck_ring(dz):
    """the turret deck's ring round the head, 4.2 thick, its lip over the base's rim, four M3 clear holes"""
    zt = deck_z(dz)
    band = cq.Workplane('XY').workplane(offset=zt - 2.4).polyline(R.plan_tub(WALL + 0.3)).close().extrude(2.4 + LIP_T)
    band = band.intersect(cq.Workplane('XY').box(300, 2 * RING_HW, 50).translate((Hm.CAR_X1 + 150, YC, zt)))
    band = band.cut(cq.Workplane('XY').workplane(offset=zt - 3).center(Hm.HX, Hm.HY).circle(DECK_HOLE_R).extrude(3))
    band = band.cut(cq.Workplane('XY').workplane(offset=zt - 3).center(Hm.HX, Hm.HY).circle(LIP_R0).extrude(10))
    for x, y in posts_body(dz):
        band = band.cut(cq.Workplane('XY').workplane(offset=zt - 3).center(x, y).circle(1.7).extrude(10))
    return band


def tub(variant):
    dz = VARIANTS[variant]['dz']
    add, cut, post = (to_body(s, dz) for s in mount(variant))
    t = cq.Workplane('XY').add(R.tub())
    for x, y in ((46, Hm.HY - 30), (46, Hm.HY + 30), (110, Hm.HY - 30), (110, Hm.HY + 30)):   # the old placeholder feet
        t = t.cut(cq.Workplane('XY').workplane(offset=R.NOSE_Z + WALL - 0.01).center(x, y).circle(3.6).extrude(4.2))
    zt = deck_z(dz)
    walls = cq.Workplane('XY').workplane(offset=R.TUB_TOP - 0.5).polyline(R.plan_tub()).close().extrude(zt - 2.4 - R.TUB_TOP + 0.5)
    walls = walls.cut(cq.Workplane('XY').workplane(offset=R.TUB_TOP - 1).polyline(R.plan_tub(WALL)).close().extrude(30))
    t = t.union(walls.intersect(cq.Workplane('XY').box(300, 300, 100).translate((Hm.CAR_X1 + 150, YC, zt))))
    for x, y in posts_body(dz):
        p = cq.Workplane('XY').workplane(offset=R.NOSE_Z + WALL - 0.5).center(x, y).circle(POST_RR).extrude(zt - 2.4 - R.NOSE_Z - WALL + 0.5)
        t = t.union(p).cut(cq.Workplane('XY').workplane(offset=zt - 2.4 - CLAMP_SCREW_L).center(x, y).circle(1.25).extrude(CLAMP_SCREW_L + 1))
    t = t.union(add).cut(cut).union(post)
    return t


def wire_line(variant):
    """the tilt servo's wires below the head, a centreline in the body frame"""
    dz = VARIANTS[variant]['dz']; fz = REST_Z - RISE; z = fz + 1.5
    pts = [(0, 0, REST_Z + 2.0), (0, 0, z), (BX1 - 1.0, 0, z)]
    if variant == 'A':
        xc = (CHIM_X0 + CHIM_X1) / 2
        pts += [(xc, 0, z + 2.0), (xc, 0, REST_Z + 8.0), (xc + 14.0, 0, REST_Z + 16.0)]
    else:
        pts += [(BX1 + 8.0, 0, z), (BX1 + 20.0, 0, z + 10.0)]
    return [(Hm.HX - x, Hm.HY - y, R.Z0H + dz + zz) for x, y, zz in pts]


def head_meshes():
    """the current head, from the fit view's data (head frame)"""
    s = open(FIT, encoding='utf-8').read(); s = s[s.index('{'):s.rindex('}') + 1]; F = json.loads(s)
    keep = {'well': 'Base: coil well (set 11)', 'bay': 'Base: gear bay', 'floor': 'Gear bay floor plate', 'drum': 'Drum',
            'bearing': '6809', 'bearing6704': '6704', 'gear_in': 'Input gear', 'gear_out': 'Small gear', 'servo': 'Pan servo',
            'horn': 'Horn', 'tab_block': 'Tab block', 'fork': 'Cradle', 'ball_plus': 'Ball, + half', 'ball_minus': 'Ball, - half',
            'camera': 'Camera board', 'tilt_servo': 'Tilt servo'}
    out = {}
    for k, lab in keep.items():
        if k not in F: continue
        V = np.frombuffer(base64.b64decode(F[k]['v']), '<f4').reshape(-1, 3).astype(float)
        Fc = np.frombuffer(base64.b64decode(F[k]['f']), '<u4').reshape(-1, 3)
        out[k] = (V[Fc], lab)
    return out


def body_tris(T, dz):
    T = T.copy(); T[..., 0] = Hm.HX - T[..., 0]; T[..., 1] = Hm.HY - T[..., 1]; T[..., 2] = R.Z0H + dz + T[..., 2]
    return T


def tube(pts, r):
    return np.vstack([cyl_tris(a, b, r, 12) for a, b in zip(pts[:-1], pts[1:])])


def section(t):
    """the printed piece: the tub forward of CUT_X, up to the tub's top. rugged.tub()'s turret-deck ledges stand at
    TDECK - 4.4 = 61.6, 4.2 over the walls' top (57.4): raised with the head (RAISE) but not the walls, so they float as
    two loose strips (found 2026-10-12, slicing this). Fixed here: tub() raises the walls forward of the carapace to the
    deck ring's underside, so the ledges sit on them."""
    top = R.TDECK - 2.4 + 0.01   # the walls now rise to the deck ring's underside (tub()), which carries the ledges
    return t.intersect(cq.Workplane('XY').box(400, 400, top + 100).translate((CUT_X + 200, YC, top - (top + 100) / 2)))


def clamp_checks(M, HM):
    """the deck ring and the posts against the head, in the head frame (A; B is the same shifted). The base is the
    generator's exact solid (head-v2 pan_coil_b.base), sampled on each post's skin; the cradle from its view mesh.
    Each row has a control that must read the other way."""
    sys.path.insert(0, os.path.join(PROTO, 'head-v2', 'generator', 'generators'))
    import pan_coil_b as PC
    rows = []
    zr = R.TDECK - R.Z0H                                                 # the ring's top face (6.6), head frame
    top, lip = zr + LIP_T, (zr - 2.4, zr + LIP_T)
    fork = HM['fork'][0].reshape(-1, 3); fr = np.hypot(fork[:, 0], fork[:, 1])
    gap = float(fork[fr >= LIP_R0 - 0.5][:, 2].min() - top)
    rows.append(('cradle (turns) over the ring, nearest (mm)', gap, gap > 1.5, 'its underside 10.5; control: the lip 2.0 thicker reads %.1f'
                 % (gap - 2.0)))
    def skin(x, y, z0, z1, r):
        a = np.linspace(0, 2 * np.pi, 72, endpoint=False); z = np.arange(z0, z1, 0.25)
        A, Z = np.meshgrid(a, z)
        return (x + r * np.cos(A), y + r * np.sin(A), Z)
    z0, z1 = REST_Z - RISE, zr - 2.4
    worst = min(float(PC.base(skin(x, y, z0, z1, POST_RR)).min()) for x, y in POSTS)
    ctrl = min(float(PC.base(skin(x * 0.8, y * 0.8, z0, z1, POST_RR)).min()) for x, y in POSTS)
    rows.append(('posts vs the base: nearest (mm)', worst, worst > 0.3 and ctrl < 0, 'control: posts 20%% in reads %.1f' % ctrl))
    # the lip on the seat ring's top (r 29.05..31, Z 6.6), and the plate clear of its outside
    a = np.linspace(0, 2 * np.pi, 180, endpoint=False)
    # the rim's top is flat from r 29.65 to 30.4 (its edges are rounded 0.6): that band carries the lip
    on = np.mean([PC.base((r * np.cos(a), r * np.sin(a), np.full_like(a, zr - 0.05))) < 0 for r in np.linspace(LIP_R0 + 0.1, 30.35, 6)])
    side = float(min(PC.base((r * np.cos(a), r * np.sin(a), np.full_like(a, z))).min() for r in (DECK_HOLE_R,) for z in np.arange(zr - 2.4, zr, 0.2)))
    rows.append(('the lip on the base rim (fraction)', float(on), on > 0.95, 'its flat top (r 29.7..30.35) under the lip, 0.05 down'))
    rows.append(('the ring plate off the base, nearest (mm)', side, side > 0.2, "its hole r %.1f against the rim's r 31.0" % DECK_HOLE_R))
    packs = [M[k]['t'].reshape(-1, 3) - [R.BODY_DX, 0, 0] for k in ('pack_L', 'pack_R') if k in M]
    pk = min(min(np.abs(P_[:, 1] - y).min() for P_ in packs) for x, y in posts_body(0.0)) - POST_RR if packs else float('nan')
    rows.append(('posts vs the packs, nearest in Y (mm)', float(pk), pk > 0.5, ''))
    for r in rows:
        print('%-46s %7.2f  %s%s' % (r[0], r[1], r[3], '' if r[2] else '   <==='))
    return [dict(label=r[0], v=r[1], ok=bool(r[2]), note=r[3]) for r in rows]


def numbers(M, tubs):
    g0 = R.ground(M)
    lowest = lambda t: float(np.asarray(t).reshape(-1, 3)[:, 2].min())
    D = {'ground': g0, 'nose_belly': R.NOSE_Z - g0, 'bays_belly': R.FLOOR0 - g0}
    for v, t in tubs.items():
        T = np.asarray(cq_tris(t.val()))
        head = T.reshape(-1, 3); m = (np.abs(head[:, 0] - (Hm.HX - 20)) < 45) & (np.abs(head[:, 1] - Hm.HY) < 25)
        D[v] = dict(under_head=float(head[m][:, 2].min() - g0))
    return D


HEAD_COL = {'well': 0xa3a8a2, 'bay': 0xa3a8a2, 'floor': 0xc9b27c, 'drum': 0x3e9c8f, 'bearing': 0x9aa0aa, 'bearing6704': 0xc9a227,
            'gear_in': 0x4fae9e, 'gear_out': 0x4fae9e, 'servo': 0x5a6470, 'horn': 0x2b2b2b, 'tab_block': 0xa3a8a2,
            'fork': 0xd8c39a, 'ball_plus': 0x7f9cb8, 'ball_minus': 0x93aac2, 'camera': 0x2d7d4b, 'tilt_servo': 0x5a6470,
            'wires': 0xe0443e}


def page(M, P, D):
    tohex = lambda rgb: int(rgb[0] * 255) << 16 | int(rgb[1] * 255) << 8 | int(rgb[2] * 255)
    def enc(T, n, c, grp, body):
        Tk = C.decimate(np.asarray(T, float).reshape(-1, 3, 3), n); V, F = C.quant(Tk)
        return {'v': C.b64(V), 'f': C.b64(F), 'i32': F.dtype == np.uint32, 'c': c, 'grp': grp, 'body': body}
    out = {'m': {}, 'v': {}, 'n': D, 'yc': float(Hm.HY), 'head': [float(Hm.HX + R.BODY_DX), float(Hm.HY), float(R.Z0H)]}
    for k, v in M.items():
        if k in ('tub', 'tdeck') or v.get('ghost'): continue
        out['m'][k] = enc(v['t'], 2600 if k.startswith('tire_') else C.faces_for(k), tohex(v['rgb']), v['grp'], v['grp'] == 'hull')
    for var, parts in P.items():
        out['v'][var] = {}
        for k, T in parts.items():
            if k == 'tub': out['v'][var][k] = enc(T, 60000, tohex(R.OLIVE_D), 'hull', True)
            elif k == 'tdeck': out['v'][var][k] = enc(T, 6000, tohex(R.OLIVE), 'hull', True)
            else: out['v'][var][k] = enc(T, 8000 if k in ('well', 'bay', 'fork', 'ball_plus', 'ball_minus') else 3000,
                                          HEAD_COL.get(k, 0x999999), 'head', False)
    A = np.vstack([v['t'].reshape(-1, 3) for v in M.values() if not v.get('ghost')])
    out['centre'] = ((A.min(0) + A.max(0)) / 2).round(1).tolist()
    html = open(os.path.join(HERE, 'nose_template.html'), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(out, default=float) + ';')
    p = os.path.join(OUT, 'nose.html'); open(p, 'w', encoding='utf-8').write(html); print('page %.1f MB' % (os.path.getsize(p) / 1e6))


if __name__ == '__main__':
    t0 = time.time()
    M, it, O = R.assemble()
    print('body %.0f s' % (time.time() - t0))
    for k in ('base', 'drum', 'cradle', 'ball'):
        M.pop(k, None)
    HM = head_meshes()
    tubs, P = {}, {}
    for v, spec in VARIANTS.items():
        tubs[v] = tub(v)
        print('tub %s %.0f s, valid %s' % (v, time.time() - t0, tubs[v].val().isValid()))
        P[v] = {'tub': np.asarray(cq_tris(tubs[v].val())) + [R.BODY_DX, 0, 0]}
        for k, (T, lab) in HM.items():
            P[v][k] = body_tris(T, spec['dz']) + [R.BODY_DX, 0, 0]
        P[v]['wires'] = tube([np.array(p) + [R.BODY_DX, 0, 0] for p in wire_line(v)], 1.2)
        P[v]['tdeck'] = np.asarray(cq_tris(deck_ring(spec['dz']).val())) + [R.BODY_DX, 0, 0]   # the clamping ring
    sec = section(tubs['A'])
    cq.exporters.export(sec, os.path.join(OUT, 'nose_section_A.stl'), tolerance=0.05, angularTolerance=0.1)
    ring = deck_ring(0.0)   # printed top face down: the lip's side on the bed
    cq.exporters.export(ring.rotate((0, 0, 0), (1, 0, 0), 180), os.path.join(OUT, 'deck_ring_A.stl'), tolerance=0.05, angularTolerance=0.1)
    bb = sec.val().BoundingBox()
    D = numbers(M, tubs)
    D['clamp'] = clamp_checks(M, HM)
    bbr = ring.val().BoundingBox()
    D['ring'] = dict(x=[bbr.xmin, bbr.xmax], y=[bbr.ymin, bbr.ymax], vol=ring.val().Volume() / 1000)
    D['section'] = dict(x=[bb.xmin, bb.xmax], y=[bb.ymin, bb.ymax], z=[bb.zmin, bb.zmax], vol=sec.val().Volume() / 1000)
    print(json.dumps(D, indent=1, default=float))
    json.dump(D, open(os.path.join(OUT, 'nose.json'), 'w'), indent=1, default=float)
    # the page: the body (everything but the tub and the head) shared, each variant's tub, head and wires
    import pickle
    pickle.dump(dict(M={k: dict(t=v['t'], rgb=v['rgb'], grp=v['grp'], label=v['label']) for k, v in M.items()
                        if k not in ('tub', 'tdeck') and not v.get('ghost')}, P=P, D=D),
                open(os.path.join(OUT, '_nose.pkl'), 'wb'))
    page(M, P, D)
    print('done %.0f s' % (time.time() - t0))
