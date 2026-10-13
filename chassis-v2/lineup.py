"""Scorpion chassis line-up (2026-10-08): every chassis variation so far, in one 3D page.

    python chassis-v2/lineup.py        # ~2 min the first time, seconds after -> out/lineup.html

The 3D comes from the pages already built: each out/*.html carries its meshes, so rerun a page's own script first
if its design changed. The four body options (variants.py) had pictures only: a child process builds their meshes
into out/_lineup_variants.pkl, rebuilt when variants.py, hull.py, ideal_render.py or concept.py is newer.
A shape that repeats between designs shifted by whole 0.02 mm steps (the head, the v1 legs) is stored once.
"""
import os, sys, json, base64, hashlib, pickle, subprocess, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out')
VAR = os.path.join(OUT, '_lineup_variants.pkl')
Q = 0.02                                                          # the pages' vertex step, mm

def page(fn):
    s = open(os.path.join(OUT, fn), encoding='utf-8').read(); i = s.find('const D=')
    return json.JSONDecoder().raw_decode(s, i + 8)[0]

# ---------------------------------------------------------------- the body options, in a child process
VAR_IN = ('variants.py', 'hull.py', 'ideal_render.py', 'concept.py')
FACES = {'head': 4000, 'legs': 6000, 'arm': 3000, 'hull': 5000}

def build_variants():
    """variants.py's four bodies, each part tagged with a group (by the builder that drew it) and decimated"""
    os.environ.setdefault('SCORPION_TAIL', 'arm2'); sys.path.insert(0, HERE)
    import variants as V, concept as C
    cur = ['hull']
    def tagged(fn, grp):
        def w(*a, **k):
            old, cur[0] = cur[0], grp
            try: return fn(*a, **k)
            finally: cur[0] = old
        return w
    for name, grp in (('tracks', 'legs'), ('head', 'head'), ('arm', 'arm')):
        setattr(V, name, tagged(getattr(V, name), grp))
    solid0, mesh0 = V.Build.solid, V.Build.mesh
    def tag(s, n, rgb, label):
        grp = 'legs' if label.startswith('flipper') or tuple(rgb) == V.RUBBER else cur[0]
        s.__dict__.setdefault('tags', []).extend([(grp, label)] * (len(s.draw) - n))
    def solid(s, sh, rgb, *a, **k): n = len(s.draw); solid0(s, sh, rgb, *a, **k); tag(s, n, rgb, k.get('label', ''))
    def mesh(s, tris, rgb, *a, **k): n = len(s.draw); mesh0(s, tris, rgb, *a, **k); tag(s, n, rgb, '')
    V.Build.solid, V.Build.mesh = solid, mesh
    HEAD = ['Pan coil base (turned 180)', 'Drum + bearing', 'Cradle', 'Ball (your rev 2)']
    res = []
    for fn in (V.baseline, V.scout, V.crawler, V.workhorse):        # variants.py's own order: they retune hull's globals
        t0 = time.time(); B, tk, info = fn(); mt = V.metrics(B, tk, info)
        groups, nh = {}, 0
        for (t, rgb, _), (grp, label) in zip(B.draw, B.tags):
            if grp == 'head': label = HEAD[nh]; nh += 1
            elif grp == 'legs': label = label if label.startswith('flipper') else 'Track (drawn, not the v1 legs)'
            elif grp == 'arm': label = 'Arm: the two-joint arm, option B'
            elif not label: label = 'Light' if tuple(rgb) == (1.0, 0.98, 0.88) else 'Body part'
            groups.setdefault((grp, label, tuple(rgb)), []).append(t)
        parts = []
        for (grp, label, rgb), ts in groups.items():
            Vq, F = C.quant(C.decimate(np.vstack(ts), FACES[grp]))
            parts.append((grp, label.capitalize() if label[:1].islower() else label, rgb, Vq, F))
        res.append(dict(name=B.name, ground=float(tk['ground']), metrics=mt, parts=parts))
        print('%-9s %3d parts  %.0f s' % (B.name, len(parts), time.time() - t0))
    pickle.dump(res, open(VAR, 'wb'))

def variants():
    stale = not os.path.exists(VAR) or os.path.getmtime(VAR) < max(os.path.getmtime(os.path.join(HERE, f)) for f in VAR_IN)
    if stale:
        print('building the body options\' meshes ...')
        subprocess.run([sys.executable, os.path.abspath(__file__), '--variants'], check=True)
    return {r['name']: r for r in pickle.load(open(VAR, 'rb'))}

# ---------------------------------------------------------------- one store for every design's parts
GMAP = {'legs': 'legs', 'flip': 'legs', 'hull': 'hull', 'tail': 'hull', 'body': 'hull', 'orig': 'hull', 'cage': 'cage', 'tpu': 'tpu',
        'seal': 'tpu', 'head': 'head', 'elec': 'elec', 'arm': 'arm'}
OUTSIDE = ('estop', 'antenna', 'light', 'imu')                     # 'elec' parts on the outside: drawn with the body

class Store:
    def __init__(s): s.geo, s.idx, s.txt, s.tix = [], {}, [], {}
    def t(s, x):
        if x not in s.tix: s.tix[x] = len(s.txt); s.txt.append(x)
        return s.tix[x]
    def part(s, v64, f64, i32, c, grp, label, note, pts):
        """the part as (geometry, shift); its vertices go into pts for the design's size"""
        Vi = np.frombuffer(base64.b64decode(v64), '<i2').reshape(-1, 3).astype(np.int32)
        key = hashlib.md5((Vi - Vi[0]).tobytes() + base64.b64decode(f64)).hexdigest()
        if key not in s.idx: s.idx[key] = (len(s.geo), Vi[0]); s.geo.append(dict(v=v64, f=f64, i32=bool(i32)))
        g, v0 = s.idx[key]; pts.append(Vi * Q)
        return dict(g=g, o=((Vi[0] - v0) * Q).round(2).tolist(), c=int(c), grp=grp, l=s.t(label), n=s.t(note))
    def page_part(s, k, p, pts, grp=None, label=None):
        g = grp or GMAP.get(p.get('grp'), 'hull')
        if g == 'elec' and k.startswith(OUTSIDE): g = 'hull'
        return s.part(p['v'], p['f'], p.get('i32'), p['c'], g, label or p.get('label', ''), p.get('note', ''), pts)

def size(pts, ground):
    A = np.vstack(pts); lo, hi = A.min(0), A.max(0)
    return dict(L=float(hi[0] - lo[0]), W=float(hi[1] - lo[1]), H=float(hi[2] - ground),
                box=[lo.round(1).tolist(), hi.round(1).tolist()])

def ground_of(parts, pts):
    z = [P[:, 2].min() for p, P in zip(parts, pts) if p['grp'] == 'legs']
    return float(min(z))

LINK = lambda u, t: dict(url='https://claude.ai/artifact/' + u, title=t)
DESIGNS = [  # id, name, short name, date, status, page, story, facts, link
    dict(id='tp2', name='TEST-PRINT-2', short='TEST-PRINT-2', date='2026-10-04', status='start', page='concept.html',
         story='Your Fusion body as exported, on the v1 legs registered by its six side holes. Everything after starts here.',
         facts=['The body alone is 238.5 × 131.5 × 50.', 'Shown without its old bracket head (not in this export).'],
         link=LINK('9Ck4ieRpqhiJ2qkCEffXWm', 'Scorpion Head Placement')),
    dict(id='concept', name='Cover concept', short='Cover', date='2026-10-04', status='superseded', page='concept.html',
         story='Kept your body and wrapped new parts round it: a mezzanine over the packs, a shell over the tracks, a rear power bay, a segmented antenna tail.',
         facts=['Your call: the body didn\'t have to stay. The hull redesign replaced it.'],
         link=LINK('4dUf3XN7jVCCy4KCCQkULT', 'Scorpion Chassis Concept')),
    dict(id='hull', name='Hull redesign', short='Hull', date='2026-10-04', status='brainstorm', page='hull.html',
         story='A new body round the v1 legs. The head stands on the floor in the nose; a carapace behind it holds the ESCs and the Pi.',
         facts=['Ball top 151 over the ground (was 182).', 'Pincer claws, antenna tail, level tracks.',
                'You loved the claws; the tail and the tracks were too small.'],
         link=LINK('AJsyz9mp1vGRPPhpaVqPm3', 'Scorpion Hull Redesign')),
    dict(id='ideal', name='Ideal picture', short='Ideal', date='2026-10-04', status='picture', var='Baseline',
         story='The redesign drawn with full-length tracks, bigger pincers and the long two-joint arm on the tail: the picture you liked.',
         facts=['A picture: not fit-checked.', 'The baseline for the three body options.'],
         link=LINK('QkTmtQ5ynNvGW9TRn96QpJ', 'Scorpion Body Options')),
    dict(id='scout', name='Scout', short='Scout', date='2026-10-04', status='picture', var='Scout',
         story='Low and sleek: one flat deck at the well\'s top, small tracks, the Pi in a low tail bay.',
         facts=['A picture: not fit-checked.'], link=LINK('QkTmtQ5ynNvGW9TRn96QpJ', 'Scorpion Body Options')),
    dict(id='crawler', name='Crawler', short='Crawler', date='2026-10-04', status='picture', var='Crawler',
         story='Terrain and survival: big trapezoid tracks, pincer-tipped flippers, sloped armour, a skid plate, a roll hoop.',
         facts=['A picture: not fit-checked.', 'You picked a Crawler + Workhorse mix (the tail arms body).'],
         link=LINK('QkTmtQ5ynNvGW9TRn96QpJ', 'Scorpion Body Options')),
    dict(id='workhorse', name='Workhorse', short='Workhorse', date='2026-10-04', status='picture', var='Workhorse',
         story='The arm and payload: the long arm mid-ship reaching the ground in front, a cargo bed, the packs aft.',
         facts=['A picture: not fit-checked.', 'You picked a Crawler + Workhorse mix (the tail arms body).'],
         link=LINK('QkTmtQ5ynNvGW9TRn96QpJ', 'Scorpion Body Options')),
    dict(id='arms', name='Tail arms', short='Tail arms', date='2026-10-04', status='brainstorm', page='tail_arms.html',
         story='Your Crawler + Workhorse mix, the arm out of the tail rising 30°. Four arms, every pose fit-checked.',
         facts=['A Scorpion (parallelogram), B Telescope, C Folder, D Lift.', 'You: good options, still thinking. No arm chosen.'],
         link=LINK('KWbW5Huixhb2FaC8Vyh4C4', 'Scorpion Tail Arms')),
    dict(id='rugged', name='Rugged body', short='Rugged', date='2026-10-05', status='brainstorm', page='rugged.html',
         story='Built for falls: skirts and two roll hoops on one outline round the centre of mass, so it rolls back upright. TPU bumpers, seals, a belly tunnel for rocks.',
         facts=['Rests after a tumble: 9 → 1 (upright).', 'Fragile part first to touch: 16 % → 0 %.'],
         link=LINK('YSHMrCeCHjszr5XPFwSxTq', 'Scorpion Rugged Body')),
    dict(id='v2legs', name='Rugged on v2 legs', short='v2 legs', date='2026-10-05', status='on hold', page='legs_v2.html',
         story='Your v2 legs: longer contact, a wider printed TPU track, sprung road wheels, gearmotors at the rear, ready for flippers.',
         facts=['Flat contact 77 → 190 mm.', 'On hold: wheels for training.'],
         link=LINK('5eJExsLRzBxyuhxjJs7oBq', 'Scorpion v2 Legs')),
    dict(id='guard', name='Guard arm E', short='Guard arm', date='2026-10-05', status='option', page='guard_arm.html',
         story='Your idea: the arm is the cage. It drives arched over the head, braces beside or behind, and pushes the robot back upright.',
         facts=['Rights itself from all 7 rests of the bare robot (≤ 34 % of servo stall).', 'Needs an IMU and the tip-monitor software.'],
         link=LINK('7YKi72Deeouei58y1rWtzR', 'Scorpion Guard Arm')),
    dict(id='trainer', name='Trainer', short='Trainer', date='2026-10-05', status='latest', page='trainer.html',
         story='Four wheels, no fenders, for training en masse. Each corner is the same module: a 37 mm gearmotor in a pod outside the hull, a Ø110 wheel with a TPU tyre.',
         facts=['Doesn\'t right itself: 4 rests besides upright.', '308 wide; 5 bodies in a simulator (tracks: ~120).'],
         link=LINK('KWmWBHLrBfb8fyQPo2zzG8', 'Scorpion Trainer')),
    dict(id='flippers', name='Guard arm E + flippers', short='Flippers', date='2026-10-09', status='brainstorm', page='guard_flippers.html',
         story="Guard arm E with the Crawler's flippers on the v2 front idler axle, each with its own worm drive, and box covers over the tracks. The flippers lift the nose onto steps and back up the arm's righting.",
         facts=['Turned down, they lift the claws from 69 to 153 mm off the ground.', 'Track covers: a tapered box, ~35x stronger than the old 2.4 mm sheet.',
                'No stop button yet: where it goes is an open question.', '319 wide (+44), +185 g.'],
         link=LINK('EhiwGigGnKB1c5NqWLUTFQ', 'Scorpion Guard Arm Flippers')),
    dict(id='trainer6', name='Trainer, six wheels', short='Trainer 6', date='2026-10-09', status='brainstorm', page='trainer6.html',
         story='The Trainer with a middle pair: the same module six times, on Ø100 wheels and a 216 mm wheelbase, the middle axle under the centre of mass.',
         facts=['Clears ridges with 40° sides (four wheels: 21°): the middle wheel holds the belly up.', 'Gaps: no better (70 mm). +718 g, two more motors.'],
         link=LINK('FHjPoawZiuExTJx56TNrds', 'Scorpion Six-Wheel Trainer')),
]
FLIP_NAME = {'stowed': 'Stowed', 'climbing': 'Climbing 20°', 'level': 'Level', 'down': 'Down to the ground'}
PN = {'stow': 'Stowed', 'side': 'Ground beside', 'back': 'Ground behind', 'high': 'Periscope'}
WHY = {'B/side': 'The boom would pass through the sponson: it reaches the ground only far out.',
       'D/side': 'The links would pass through the sponson: the Lift picks up behind.'}

def numbers(d, D, V):
    """mass and tip-back as each design's own page measured them (None where it didn't)"""
    i = d['id']
    if 'var' in d: m = V[d['var']]['metrics']; return dict(mass=m['mass'], tip=m['tip_back'], tip_how='static')
    if i == 'arms': return dict(mass=D['num']['robot']['mass'], tip=page('rugged.html')['climb_before']['up_flat'], tip_how='climb')
    if i == 'guard': return dict(mass=D['mass'], tip=D['climb_guard']['up_flat'], tip_how='climb')
    if i == 'flippers': return dict(mass=D['mass'], tip=D['climb']['up_flat'], tip_how='climb')
    if 'climb' in D: return dict(mass=D['mass'], tip=D['climb']['up_flat'], tip_how='climb')
    return dict(mass=None, tip=None, tip_how=None)

def build():
    S, V, cache, out = Store(), variants(), {}, []
    for d in DESIGNS:
        e = {k: d[k] for k in ('id', 'name', 'short', 'date', 'status', 'story', 'facts', 'link')}
        parts, pts = [], []
        if 'var' in d:
            r = V[d['var']]
            for grp, label, rgb, Vq, F in r['parts']:
                c = int(rgb[0] * 255) << 16 | int(rgb[1] * 255) << 8 | int(rgb[2] * 255)
                parts.append(S.part(base64.b64encode(Vq.tobytes()).decode(), base64.b64encode(F.tobytes()).decode(),
                                    F.dtype == np.uint32, c, grp, label, '', pts))
            D, ground = None, r['ground']
        else:
            D = cache.setdefault(d['page'], page(d['page']))
            if d['id'] == 'tp2':
                keep = [k for k, p in D['m'].items() if p['grp'] == 'legs' or k == 'body_orig']
            else:
                keep = [k for k, p in D['m'].items() if not p.get('ghost')]
            for k in keep:
                orig = k == 'body_orig'
                parts.append(S.page_part(k, D['m'][k], pts, *(('hull', 'Your body, TEST-PRINT-2, as exported') if orig else ())))
            ground = D.get('ground') or ground_of(parts, pts)
        dflt_pts = list(pts)
        if d['id'] == 'arms':                                           # four arms x four poses
            sets, cols = {}, D['cols']
            for a, A in D['arms'].items():
                for ps, L in A['poses'].items():
                    P = []; sets[a + '/' + ps] = [S.page_part('arm', p, P, 'arm', a + ' ' + A['name'] + ': ' + PN[ps].lower()) for p in L]
                    if a + '/' + ps == 'A/stow': dflt_pts += P
            e['pose'] = dict(dims=[dict(name='Arm', opts=[[a, a + ' ' + A['name'], cols[a]] for a, A in D['arms'].items()]),
                                   dict(name='Pose', opts=[[k, v] for k, v in PN.items()])], sets=sets, dflt='A/stow', why=WHY)
        if d['id'] == 'guard':                                          # the five named poses; the righting ones stay on its page
            sets = {}
            for k, s_ in D['sit'].items():
                if k.startswith('right_'): continue
                assert s_['R'] == [[1, 0, 0], [0, 1, 0], [0, 0, 1]] and s_['dz'] == 0, k
                P = []; sets[k] = [S.page_part('arm', p, P, 'arm', 'Guard arm: ' + s_['name'].lower()) for p in s_['arm']]
                if k == 'guard': dflt_pts += P
            e['pose'] = dict(dims=[dict(name='Doing', opts=[[k, D['sit'][k]['name']] for k in sets])], sets=sets, dflt='guard', why={})
        if d['id'] == 'flippers':                                       # flipper poses x arm poses; nose-lifting tilts the robot: its own page
            sets = {}
            for f in FLIP_NAME:
                for a, s_ in D['sit'].items():
                    P = []; key = f + '/' + a
                    sets[key] = [S.page_part('flip', p, P, 'legs', p.get('label') or 'Flipper') for p in D['flip'][f]] +                                 [S.page_part('arm', p, P, 'arm', 'Guard arm: ' + s_['name'].lower()) for p in s_['arm']]
                    if key == 'stowed/guard': dflt_pts += P
            e['pose'] = dict(dims=[dict(name='Flippers', opts=[[k, v] for k, v in FLIP_NAME.items()]),
                                   dict(name='Arm', opts=[[k, s_['name']] for k, s_ in D['sit'].items()])], sets=sets, dflt='stowed/guard', why={})
        e.update(parts=parts, ground=float(ground), **size(dflt_pts, ground), **numbers(d, D, V))
        out.append(e); print('%-18s %3d parts  L %.0f W %.0f H %.0f' % (e['name'], len(parts), e['L'], e['W'], e['H']))
    return dict(geo=S.geo, txt=S.txt, designs=out, yc=3.75)

if __name__ == '__main__':
    if '--variants' in sys.argv: build_variants(); sys.exit()
    t0 = time.time(); D = build()
    html = open(os.path.join(HERE, 'lineup_template.html'), encoding='utf-8').read().replace('/*DATA*/', 'const D=' + json.dumps(D, separators=(',', ':')) + ';')
    p = os.path.join(OUT, 'lineup.html'); open(p, 'w', encoding='utf-8').write(html)
    print('%d shapes for %d designs; page %.1f MB; %.0f s' % (len(D['geo']), len(D['designs']), os.path.getsize(p) / 1e6, time.time() - t0))
