"""Other ways to fit the insides (2026-11-08). Zach, on my "42 mm doesn't fit": "also layers? ... the packs are not required to be on
the side. We can use smaller boxes than the actual real gridifintity things ... theres lots of ways to make it fit". He's right: that
verdict held only for one floor with the packs on the walls.

    python twin/grid_layouts.py       # each layout checked for fit, with a control; cells per pitch; heights and CoM

Frame: x 0 (back) to 250, y across (0 on the centre line), z up from the body's underside. A box is (x0, x1, y0, y1, z0, z1).
These are rough layouts to compare, not designs. * = sizes not measured (grid_eval.PARTS).
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

L_MAX, W_MAX = 250.0, 139.5
WALL, FLOOR, FRAME = 2.6, 2.6, 1.45    # print 1's wall and floor; a frame's wall and clearance
DECK = 2.0                             # a shelf's thickness (picked)
GAP = 1.0                              # air between a part and the shelf over it (picked)
STACK = 72.5                           # the Pi box's underside to the wire bend: his 55 + the rings + a guessed 15 mm bend (pi_box.py)
T3_G = 4651.0                          # g: the sim's T3, for the CoM's move
MASS = dict(pack=300, esc=55, pi=145, pca=12, esp=10, bec=40, alarm=8, pololu=10, ina=3, imu=3, deck=40)   # g. pi = the stack + its box; esp*, bec*, alarm*, pololu*, deck* guessed


def box(k, x0, y0, l, w, z0, h, lvl=0):
    return dict(k=k, b=(x0, x0 + l, y0, y0 + w, z0, z0 + h), lvl=lvl)


def two_sided(k, x0, l, y_in, w, z0, h, lvl=0):
    """a matching pair, either side of the centre line, y_in from it"""
    return [box(k, x0, y_in, l, w, z0, h, lvl), box(k, x0, -y_in - w, l, w, z0, h, lvl)]


def on_walls():
    """A: the sim's layout. One level, the packs on edge along the walls"""
    z = FLOOR
    return dict(name='A. One level, packs on the walls', short='The sim\'s layout', parts=two_sided('pack', 101, 141, 36.65, 26, z, 45.7) + two_sided('esc', 33.5, 45, 38.65, 24, z, 34) + [
        box('pi', 93, -32.8, 98.5, 65.6, z, STACK), box('pca', 27.5, 3.75, 62.2, 25.7, z, 12.4), box('esp', 27.5, -27.75, 55, 28, z, 12),
        box('imu', 4.1, -13.75, 20, 25, z, 4.6), box('pololu', 4.5, -65.25, 25.4, 25.4, z, 9.5), box('ina', 4.5, 40.25, 25.6, 20.4, z, 4.7),
        box('bec', 195, -31.75, 48, 30, z, 15), box('alarm', 195, 2.25, 40, 25, z, 12)], decks=[], esc_face='in', swap='Lift the lid; packs come straight out')


def shelves():
    """B: packs still on the walls, the small boards on shelves over them, so the back and nose empty out"""
    z = FLOOR; s = z + 45.7 + GAP + DECK
    return dict(name='B. Shelves over the packs', short='Same height, about 30 mm shorter', parts=two_sided('pack', 72.05, 141, 36.65, 26, z, 45.7) + two_sided('esc', 4.05, 45, 38.65, 24, z, 34) + [
        box('pi', 40, -32.8, 98.5, 65.6, z, STACK), box('imu', 145, -10, 25, 20, z, 4.6),
        box('pca', 10, 37, 62.2, 25.7, s, 12.4, 1), box('esp', 80, 36, 55, 28, s, 12, 1), box('alarm', 143, 38, 40, 25, s, 12, 1),
        box('bec', 143, -65, 48, 30, s, 15, 1), box('pololu', 10, -63, 25.4, 25.4, s, 9.5, 1), box('ina', 66, -60, 25.6, 20.4, s, 4.7, 1)],
        decks=[(4, 194, 33.25, 67, s - DECK, s), (4, 194, -67, -33.25, s - DECK, s)], esc_face='in', swap='Lid, then the shelves, then the packs')


def flat_deck():
    """C: packs flat on the floor, side by side, everything else on one deck over them"""
    z = FLOOR; s = z + 26 + GAP + DECK
    return dict(name='C. Packs flat, deck over them', short='Packs lowest, body tallest', parts=two_sided('pack', 72.05, 141, 1.45, 45.7, z, 26) + two_sided('esc', 4.05, 45, 7, 34, z, 24) + [
        box('pi', 52.05, -32.8, 98.5, 65.6, s, STACK, 1), box('pca', 153.5, 3, 62.2, 25.7, s, 12.4, 1), box('esp', 153.5, -30, 55, 28, s, 12, 1),
        box('alarm', 153.5, 32, 40, 25, s, 12, 1), box('bec', 196.5, 32, 48, 30, s, 15, 1), box('pololu', 153.5, -61, 25.4, 25.4, s, 9.5, 1),
        box('ina', 182, -58, 25.6, 20.4, s, 4.7, 1), box('imu', 211, -58, 25, 20, s, 4.6, 1)],
        decks=[(52, 245, -67, 67, s - DECK, s)], esc_face='up', swap='Lid, then the deck with everything on it, then the packs')


def spine():
    """D: packs on edge, side by side down the middle, the Pi box turned sideways behind them, the rest beside and ahead of them"""
    z = FLOOR
    return dict(name='D. Packs down the middle', short='One level, heavy parts centred', parts=two_sided('pack', 72.55, 141, 1.5, 26, z, 45.7) + two_sided('esc', 72.55, 45, 30.4, 24, z, 34) + [
        box('pi', 4.05, -49.25, 65.6, 98.5, z, STACK), box('pca', 121, 31, 62.2, 25.7, z, 12.4), box('esp', 121, -59.4, 55, 28, z, 12),
        box('pololu', 186.2, 30.4, 25.4, 25.4, z, 9.5), box('bec', 179, -60.4, 48, 30, z, 15), box('ina', 218, -27.3, 20.4, 25.6, z, 4.7),
        box('alarm', 218, 1.5, 25, 40, z, 12), box('imu', 218, 44.5, 25, 20, z, 4.6)], decks=[], esc_face='out', swap='Lift the lid; packs come straight out')


# ---------------------------------------------------------------- wires
# Zach, 2026-11-08: "boxes have a length they can sit from another box. Wire length, determines that". His lengths: the ESC's red and black,
# its yellow and blue, the Zeee pack's own lead. Duponts "can be as long as we need". The Y-harness adds to the battery's reach; its length
# isn't known, so it's left out. Each ESC feeds two motors, so yellow and blue get spliced whatever the distance: past 105 is more wire, not a block.
ESC_POWER, ESC_MOTOR, PACK_LEAD = 90.0, 105.0, 120.0
BATTERY = PACK_LEAD + ESC_POWER
AXLES = (49.0, 201.0)        # * T3's 152 wheelbase centred in a 250 body. The first robot's axles aren't drawn yet
MOTOR_Y = 67.0               # * a motor's wires come in at the body's inside wall
PACK_ROOM = 15.0             # * straight lead a pack needs before it can turn
ESC_ROOM = 10.0              # * the same, off the ESC's finned face, where the leads leave (his photos of frame v1)
UP_OVER = 15.0               # * added to each run seen from above, for climbing over a wall and coming down
LEAD_Z = 17.0                # * the leads above the ESC's lower edge, stood on edge; read off his photos, not measured


def _boxes(L, skip=None):
    return [p['b'] for p in L['parts'] if p is not skip] + [tuple(d) for d in L['decks']]


def pack_room(L, p, end):
    """free straight run off a pack's end at its lead's height. end: -1 back, +1 front. A low board doesn't block it: the lead passes over"""
    a, b, c, d, e, f = p['b']
    z = (e + f) / 2
    room = L_MAX - WALL - b if end > 0 else a - WALL
    for A, B, C, D, E, G in _boxes(L, p):
        if C < d and c < D and E < z < G:
            gap = A - b if end > 0 else a - B
            if gap >= 0:
                room = min(room, gap)
    return room


def esc_lead(L, p):
    """where an ESC's leads come off, seen from above, and the free run off that face (L['esc_face']: 'in', 'out', or 'up' when it lies flat)"""
    a, b, c, d, e, f = p['b']
    x, s, face = (a + b) / 2, (1 if c + d > 0 else -1), L['esc_face']
    if face == 'up':
        y = (c + d) / 2
        over = [E for A, B, C, D, E, G in _boxes(L, p) if A < b and a < B and C < d and c < D and E >= f]
        return x, y, (min(over) - f if over else 99.0)
    near, far = sorted((abs(c), abs(d)))
    z = e + LEAD_Z
    y = s * (near if face == 'in' else far)
    room = (2 * near if face == 'in' else W_MAX / 2 - WALL - far)    # to the other side's ESC, or to the wall
    for A, B, C, D, E, G in _boxes(L, p):
        if A < x + 10 and x - 10 < B and E < z < G:
            gap = (y - D if s > 0 else C - y) if face == 'in' else (C - y if s > 0 else y - D)
            if gap >= 0:
                room = min(room, gap)
    return x, y, room


def wires(L):
    """the drive pack (the first, +y, as on the review's wiring) to both ESCs, and each ESC to its side's two motors, along x then y"""
    P = L['parts']
    packs = [p for p in P if p['k'] == 'pack']
    escs = [p for p in P if p['k'] == 'esc']
    leads = [esc_lead(L, p) for p in escs]
    a, b, c, d, e, f = packs[0]['b']
    ym = (c + d) / 2
    room = {-1: pack_room(L, packs[0], -1), 1: pack_room(L, packs[0], 1)}
    ok = [k for k in room if room[k] >= PACK_ROOM]
    run = lambda end: [abs((b if end > 0 else a) - x) + abs(ym - y) + UP_OVER for x, y, _ in leads]
    end = min(ok, key=lambda k: max(run(k))) if ok else max(room, key=room.get)    # the shortest way out that has room
    bat = run(end)
    mot = [[abs(x - ax) + abs((MOTOR_Y if y > 0 else -MOTOR_Y) - y) + UP_OVER for ax in AXLES] for x, y, _ in leads]
    return dict(end=end, x=(b if end > 0 else a), y=ym, room=room[end], pi_room=max(pack_room(L, packs[1], -1), pack_room(L, packs[1], 1)),
                leads=leads, bat=bat, spare=[BATTERY - v for v in bat], mot=mot)


def wire_problems(L):
    w, bad = wires(L), []
    if w['room'] < PACK_ROOM:
        bad.append('drive pack lead has %.1f mm' % w['room'])
    if w['pi_room'] < PACK_ROOM:
        bad.append('Pi pack lead has %.1f mm' % w['pi_room'])
    for x, y, r in w['leads']:
        if r < ESC_ROOM:
            bad.append('ESC leads have %.1f mm' % r)
    if max(w['bat']) > BATTERY:
        bad.append('battery run %.0f mm, the wires reach %.0f' % (max(w['bat']), BATTERY))
    return bad


def problems(L):
    """frames into each other or past the body's inside. Empty is the pass"""
    bad = []
    x0, x1, y0, y1 = WALL, L_MAX - WALL, -W_MAX / 2 + WALL, W_MAX / 2 - WALL
    P = L['parts']
    for p in P:
        a, b, c, d, e, f = p['b']
        if a - FRAME < x0 - 0.1 or b + FRAME > x1 + 0.1 or c - FRAME < y0 - 0.1 or d + FRAME > y1 + 0.1:
            bad.append(p['k'] + ' past the body')
    for i, p in enumerate(P):
        for q in P[i + 1:]:
            a, b, c, d, e, f = p['b']; A, B, C, D, E, G = q['b']
            if a - FRAME < B + FRAME and A - FRAME < b + FRAME and c - FRAME < D + FRAME and C - FRAME < d + FRAME and e < G and E < f:
                bad.append(p['k'] + ' into ' + q['k'])
    for dk in L['decks']:
        a, b, c, d, e, f = dk
        for p in P:
            A, B, C, D, E, G = p['b']
            if a < B and A < b and c < D and C < d and e < G and E < f:
                bad.append('deck into ' + p['k'])
    return bad


def stats(L):
    P = L['parts']
    top = max(p['b'][5] for p in P)
    x1 = max(p['b'][1] for p in P) + FRAME + WALL
    y = max(max(abs(p['b'][2]), abs(p['b'][3])) for p in P) + FRAME + WALL
    m = sum(MASS[p['k']] for p in P) + MASS['deck'] * (1 if L['decks'] else 0) * (1 if len(L['decks']) == 1 else 0.6 * len(L['decks']) / 2 * 2)
    mz = sum(MASS[p['k']] * (p['b'][4] + p['b'][5]) / 2 for p in P if p['k'] != 'pi') + sum(MASS['pi'] * (p['b'][4] + 18) for p in P if p['k'] == 'pi')
    mz += sum(MASS['deck'] * (0.6 if len(L['decks']) == 2 else 1) * (d[4] + d[5]) / 2 for d in L['decks'])
    packs = [p for p in P if p['k'] == 'pack']
    pack_z = sum((p['b'][4] + p['b'][5]) / 2 for p in packs) / 2
    roll = sum(300 * ((p['b'][2] + p['b'][3]) / 2) ** 2 for p in packs)
    # width and length the parts need (what the body could shrink to) and the height the shell must reach, with a lid
    return dict(top=top + 2.6, long=x1, wide=2 * y, mz=mz, m=m, pack_z=pack_z, roll=roll, levels=1 + bool(L['decks']))


def cells_table():
    import grid_eval as GE
    out = []
    ix, iy = L_MAX - 2 * WALL, W_MAX - 2 * WALL
    for p in (42, 28, 21, 14, 10):
        tot = 0
        for n, a, b, h, c, _, src in GE.PARTS:
            tot += GE.cells(a, p) * GE.cells(b, p) * c
        cap = int(ix // p) * int(iy // p)
        out.append(dict(pitch=p, need=tot, cap=cap, layers=math.ceil(tot / cap)))
    return out


LAYOUTS = (on_walls, shelves, flat_deck, spine)


def report():
    res, base = [], None
    for f in LAYOUTS:
        L = f(); s = stats(L); bad = problems(L)
        if base is None:
            base = s
        w = wires(L); bad = bad + wire_problems(L)
        s['dz'] = (s['mz'] - base['mz']) / T3_G; s['bad'] = bad; s['roll_ratio'] = s['roll'] / base['roll']; L['wires'] = w
        res.append(dict(L, stats=s))
        print('%-34s %s | needs %3.0f long x %3.0f wide x %3.0f tall | packs at z %4.1f | robot CoM %+.1f mm up | packs\' roll inertia x%.2f | %s' % (
            L['name'], 'fits' if not bad else 'BAD %s' % bad, s['long'], s['wide'], s['top'], s['pack_z'], s['dz'], s['roll_ratio'], L['swap']))
        print('    drive lead out the %s, %.0f mm free | battery %.0f, %.0f of %.0f (%.0f, %.0f to stow) | ESC leads %.0f mm free | motors %s of %.0f, then spliced' % (
            'front' if w['end'] > 0 else 'back', w['room'], *w['bat'], BATTERY, *w['spare'], min(r for _, _, r in w['leads']), ' / '.join('%.0f, %.0f' % tuple(m) for m in w['mot']), ESC_MOTOR))
    # the control: push one part into its neighbour, and the check must see it
    C = on_walls(); C['parts'][4]['b'] = tuple(v + (5 if i in (0, 1) else 0) for i, v in enumerate(C['parts'][4]['b']))
    print('control, the Pi 5 mm forward in layout A:', problems(C) or 'NOTHING: THE CHECK IS BROKEN')
    # the wire check's controls: the layouts as they were before his lengths, and a run too long
    A = on_walls()
    for p in A['parts']:
        if p['k'] == 'esc':
            p['b'] = (53.0, 98.0) + p['b'][2:]
    K = flat_deck(); K['decks'] = [(4, 197, -67, 67) + K['decks'][0][4:]]
    Far = spine()
    for p in Far['parts']:
        if p['k'] == 'esc':
            p['b'] = (p['b'][0] - 20, p['b'][1] - 20) + p['b'][2:]
    ctl = (wire_problems(A), wire_problems(K), wire_problems(Far))
    print('controls: A with the ESCs where they were: %s | C with the deck over the ESCs: %s | D with the ESCs 20 mm further: %s' % tuple(c or 'NOTHING: THE CHECK IS BROKEN' for c in ctl))
    if any(r['stats']['bad'] for r in res) or not problems(C) or not all(ctl):
        raise SystemExit('layout check failed')
    return res


if __name__ == '__main__':
    report()
    print('\nCells per pitch (a lower bound: the area alone, packs on edge):')
    for r in cells_table():
        print('  %2d mm: needs %3d, a floor holds %3d -> at least %d layer%s' % (r['pitch'], r['need'], r['cap'], r['layers'], '' if r['layers'] == 1 else 's'))
    h = 6.0 + 45.7 + GAP + 6.0 + STACK
    print('\nReal 42 mm Gridfinity in two full layers: about %.0f mm of parts, %.0f with a lid; layout A needs %.0f' % (h, h + 2.6, FLOOR + STACK + 2.6))
