"""The capability search's page ("Scorpion Capability"): how far each gauge goes when the search pushes it alone, the
all-rounders on the seven-way front, the full readings, which knobs each champion turned, and the trade-offs across
every design screened, each design with a little model (a side view, and a 3D view with T3 as a ghost).

    python gauges/capability_page.py   -> gauges/out/capability/capability.html (works mid-run, from the screens so far)
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import capability as CA, knobs as K, knobs_page as KP, gauges as GG, robots as RB

TEMPLATE = os.path.join(HERE, 'capability_page.tmpl.html')
LABEL = dict(up='G1 upright', climb='G2 step up', turn='G3 turn', h_up='G4 hill up', h_down='G5 hill down', crest='G6 crest',
             push='G7 push', all='All-rounder', low='Low all-rounder', tow='G7 tow', rough='G8 rough',
             **{'st_0.1': 'Low: step − 0.1 × turn', 'st_0.25': 'Low: step − 0.25 × turn', 'st_0.5': 'Low: step − 0.5 × turn',
                'st_1': 'Low: step − turn', 'turn450': 'Low: most step inside a 450 mm turn'})
G_KEYS = [g for g, _ in CA.GAUGES]
FINDINGS = [   # the 2026-10-28 run's findings, read off finals.json, summary.json and the screens (gauges/README.md "The capability search")
    '<b>Each gauge’s ceiling</b>, in this sim and this family of robots: upright 1.00 (T3 already has it); step 225 mm '
    '(T3 150); turn about 389 mm, which is T3’s own (T3 reads 381–392 mm from read to read; none of the 3,280 designs that could spin beat 381); hills 60° up and '
    '65° down (T3 45° and 45°, tail braced); crest 45° on the full read (T3 40° here, 25° on the scorecard: this gauge is '
    'noisy); push 8 kg (T3 1 kg, or 4 kg with its tail mount at 170 mm). No test capped a champion: the hills go to 75°, '
    'the crest to 60°, the push to 12 kg and the step to 300 mm.',
    '<b>No design reaches more than two ceilings, and the designs split into two families.</b> Four wheels and a tail '
    'own the step and the turn. Six wheels and 5–5.5 kg own the hills, the crest and the push, and no six-wheeler of '
    '2,176 stepped more than 100 mm. In between there is nothing: no screened design steps 100 mm and turns in 450 mm, '
    'and the 152 that step 150 mm turn in 628 mm at best.',
    '<b>T3’s corner is a needle, and it holds.</b> Its 1.00 upright, 150 mm step and 381–392 mm turn sit on the front, and '
    'no other design comes close on the step and the turn together. The single-gauge streams never went near it, '
    'because no stream asked for that pair; the shape study found T3 with a step-and-turn objective.',
    '<b>The step is bought with wheel size and tail length.</b> Among four-wheel tail designs the step tracks wheel '
    'size (rank correlation 0.51), tail length (0.48), ride height (0.37), tail torque (0.33) and gearing (0.32). The '
    '225 mm champion runs 140 mm wheels (T3 90), a 71 mm ride height (T3 52) and a 324 mm tail (T3 279). It pays with '
    'twice T3’s turn (784 mm), its push (0.5 kg on the grippiest floor) and its upright (0.81). Front flippers, the next '
    'knob, might buy that height without the big wheels.',
    '<b>The hills and the push are bought with weight and wheels.</b> One design is both champions: six wheels, '
    '5.5 kg, its packs at the top of their range (2× T3’s; every six-wheel pick ran 1.7–2×). It holds 60° up and down '
    'with the tail stowed, and it pushes 8 kg. The packs’ bound capped it, so more mass would go further, at the step’s '
    'and the turn’s cost.',
    '<b>The no-weights all-rounder chased the pool, not the robot.</b> It raised a design’s worst percentile rank among '
    'everything screened, and refinement filled the pool with hill and push designs. In that pool T3 ranks 0.17, because '
    'most screened designs out-hill it, and the stream settled on the hill-and-push champion: step 50 mm, turn 659 mm, '
    'upright 0.51. A rank inside a searched pool measures the search. An all-rounder needs fixed scales, or T3 as the bar.',
    '<b>The best all-rounder is still T3 with its tail mount at 170 mm</b>, the scorecard’s 1.00 / 150 mm / 387 mm, '
    '40° / 45°, crest 25°, 4 kg. It meets every target. Against the ceilings it gives up 75 mm of step, 20° of hill each '
    'way, and 4 kg of push.',
    '<b>The screen overrated the six-wheelers’ upright.</b> Six tries a rung read the hill champion at 0.70; 200 falls '
    'at three frictions read 0.505. The other gauges held from the screen to the finals.',
    '<b>Random sampling found most ceilings; refinement found the step and the turn.</b> The 1,024 spread designs '
    'already reached the hill, crest and push ceilings. Ten rounds of refinement moved the step from 140 to 225 mm and '
    'the turn from 439 to 389 mm.',
]
FINDINGS_TAIL = [   # the wide run's (2026-10-30 night, capability_tail): finals.json, summary.json, the screens and learn.json
    '<b>A low body is the best all-rounder this time.</b> The all-rounder (the low stream’s best too) tops out at 155 mm '
    '(T3’s skin: 231), on six 39 mm wheels, with a two-link tail, the rear-up reflex and front flippers. Against T3 on the '
    'full gauges: upright 0.975 against 1.00, step 100 against 150 mm, turn 568 against 392 mm, hills 60/60 against '
    '45/45°, crest 45 against 40°, push 6 against 1 kg.',
    '<b>Low bodies stay upright as well as tall ones and turn tighter, but step less.</b> In the even sample (1,129 built), '
    'the 75 bodies under 160 mm read median upright 0.50 against 0.43, turn 723 against 841 mm, step 30 against 40 mm, '
    'crest 10 against 15°. Across all screens the low bodies reached every gauge’s best but the step (150 against 250 mm) '
    'and the turn (437 against 361 mm).',
    '<b>T3’s corner is still unmatched.</b> None of 4,145 built designs steps 150 mm, turns inside 450 mm and stays upright '
    '0.9. The nearest low bodies step 120–140 mm and turn in 500–567 mm at upright 0.87–1.00: six wheels, a two-link '
    'tail, flippers, no skin.',
    '<b>The new tail parts buy step, modestly.</b> In the even sample, tails with the rear-up reflex stepped 60 mm on '
    'average against 52 without, and reached 100 mm twice as often (15 % against 8 %); a second link, 57 against 51 mm '
    '(13 % against 5 %; only 64 single-link tails to compare). Neither moved another gauge. The step champion (250 mm, '
    'past the last run’s 225) carries a 445 mm two-link tail on 81 mm wheels, and pushes nothing.',
    '<b>What each gauge is bought with</b> (rank correlations in the even sample; a random forest agrees): upright, the '
    'skin, a low ride height, a tail and its torque; step, wheel size and gearing, then six wheels and a tail; turn, six '
    'wheels cost most (median 1,008 against 745 mm), then big wheels and a long wheelbase; hills, gearing, six wheels '
    'and small wheels; crest, gearing, small wheels and four wheels; push, small wheels and the wheelbase set back.',
    '<b>Front flippers pay across the population</b>, unlike on the one flat test bed: with them, median upright 0.50 '
    'against 0.40 and step 50 against 40 mm.',
    '<b>A third of the designs fail the strict build</b>, mostly on a motor not fixed to the body (about 400 designs each '
    'motor) and on a drive too weak for its wheels (412), then on the tail mount (359).',
    '<b>Measured short, found after the run:</b> the sims read a two-link tail’s reach as its first link alone '
    '(robots.limb_points, fixed 2026-10-31). Fourteen two-link winners screened again kept every gauge but the turn, '
    'which grew up to 25 mm, and the hill-down champion’s (a 178 mm second link) 144 mm, to 700 mm. This page shows the '
    'run as screened.',
]
FINDINGS_LOW = [   # the low step-and-turn run's (2026-10-31, capability_low): finals.json, summary.json and the screens with the wide run's
    '<b>No low body reaches T3’s corner, but the gap is down to about 80 mm of turn.</b> The tightest turn at a 150 mm '
    'step went from 558 mm in the seeds to 471 mm (T3 392), upright 1.00. Inside a 450 mm turn the best step is 120 mm. '
    'The step-and-turn champion steps 175 mm, past T3, in a 494 mm turn, upright 1.00, hills 55/55°, push 6 kg; the full '
    'gauges read it as the screen did.',
    '<b>Only the body is low: the stowed tail stands up.</b> The winners stow the tail near vertical (85–87°; T3 112°), '
    'so the champion stands 544 mm tall (T3 421) and the low bodies’ median is 399 mm. Standing the tail up keeps it out '
    'of the turn circle (height against turn, rank correlation −0.32) while a long tail buys step (+0.42). Robots under '
    '300 mm overall step 120 mm in 483 mm at best; under 250 mm, 80 mm.',
    '<b>Every low winner has six wheels.</b> 1,185 of the 1,251 low, upright designs do; the best four-wheeler steps '
    '80 mm in 500 mm. The six-wheelers’ turn grows with the gap between wheels (0.47), and the winners run the smallest.',
    '<b>The search was still moving.</b> Four rounds on 16 cores (a daytime run): the step champion appeared in the last '
    'one, and each round took 5–20 mm off the turn at a 150 mm step.',
]
FINDINGS_REAL = [   # the realistic run's (2026-10-31 night, capability_real): finals.json, the screens against capability_tail's on the
    # same 2,048 B designs, and Zach's one-click tests of 2026-11-01 (tomorrow/repeat.txt, onepiece.json)
    '<b>Half the strict run’s designs could not be built.</b> Of the 1,129 the strict build accepted among the same '
    '2,048 spread designs, the real build accepts 572. Alone, a flipper off the body refused 208, a drive too weak '
    'for the printed weight 121, a motor into the packs or ESCs 108.',
    '<b>Realism shrank the space more than it reordered it.</b> On the 572 both builds accept, the robot is 1.4 kg '
    'heavier (median) and the gauges barely move: step +1 mm, turn +10 mm, hills -5/0, push +0.5 kg; the designs '
    'rank the same way (rank agreement 0.88-0.94), upright least (0.67). The knob lessons of the earlier runs hold.',
    '<b>The ceilings hold too</b>, but for the push: step 228 mm (250 strict), turn 361 mm, hills 60/65, crest 45, '
    'upright 1.00, and push 10 kg (6 strict): the printed weight pushes.',
    '<b>T3’s corner is still T3’s alone.</b> Built real (its track widened 114 to 130 mm so its motors '
    'clear the ESCs), T3 reads 1.00 / 151 mm / 448 mm, hills 40/45, push 2 kg. None of 6,298 real designs steps 150 mm, '
    'turns inside 450 mm and stays upright 0.9.',
    '<b>Two families, as before.</b> Big-wheel four-wheelers (R 70 mm) with a long two-link tail step 228 mm but turn '
    'in 750 mm and push nothing. Low six-wheelers (R 43-48, top 150-167 mm) with a tail step 110-120 mm, turn in '
    '540-570 mm, hold hills 55/60°, crest 35-45° and push 6 kg.',
    '<b>The tail servo is the binding part.</b> Every top stepper runs its tail at the knob’s 4 N m ceiling (about a '
    '40 kg cm servo). On 2026-10-31, 19 % more servo torque gave the low winner its lost step back.',
    '<b>The cheap build now agrees with the one piece.</b> Grown as one printable piece, the best all-rounder read '
    '0.85 / 92 mm / 613 mm against the real build’s 0.80 / 85 / 631, the best turner 22 / 370 against 22 / 361, '
    'at weights within 3 %. Before the real build the floating winner and its one piece differed by 75 mm of step.',
    '<b>The gauges repeat.</b> Read with three seed sets, the step held within 3 mm (151-152, 82-85, 72, 21-22), except '
    'at the ladder’s top, where rungs are 25 mm apart (192-227); upright moves by up to 0.1 at 0.4-0.8 (the noise of '
    '200 falls, worst of three floors); turn, hills, crest and push hold.',
]
RUN_FINDINGS = {'capability': FINDINGS, 'capability_strict': FINDINGS, 'capability_tail': FINDINGS_TAIL,
                'capability_low': FINDINGS_LOW, 'capability_real': FINDINGS_REAL}
RUN_DATE = {'capability': '2026-10-28', 'capability_strict': '2026-10-28', 'capability_tail': '2026-10-30',
            'capability_low': '2026-10-31', 'capability_real': '2026-10-31'}


def packed_mesh(V, T):
    """a general mesh (a body with its wheel wells) packed as KP.packed packs a hull, not thinned"""
    import base64
    used = np.unique(T); idx = -np.ones(len(V), int); idx[used] = np.arange(len(used))
    v = np.round(V[used]).astype('<i2'); w = 1 if len(used) < 256 else 2; f = idx[T].astype('<u1' if w == 1 else '<u2')
    b = lambda a: base64.b64encode(a.tobytes()).decode('ascii')
    return dict(v=b(v), f=b(f), w=w)


def model_of(sp):
    """a design's shape for the page: hulls (thinned and packed, as the knob page's), the tail stowed, wheels. The
    strict run draws the body with its wheel wells cut (robots.with_wells)"""
    lm, tail = sp.get('limb'), None
    if lm:
        p = np.radians(lm['th_stow']); B = np.asarray(lm['base'], float); tip = B + (lm['L'] + lm.get('L2', 0.0)) * np.array([-np.cos(p), 0.0, np.sin(p)])
        tail = dict(base=np.round(B).tolist(), tip=np.round(tip).tolist(), r=RB.LINK_R, foot=lm.get('foot_r', RB.FOOT_R))
    hulls = [KP.packed(KP.mesh(np.asarray(h, float))) for h in sp['hulls']]
    if CA.STRICT:                                                         # thinned to the page's corners first, as packed()
        P = np.asarray(sp['hulls'][0], float); pick = [int(np.argmax(P[:, 0]))]; d = np.linalg.norm(P - P[pick[0]], axis=1)
        while len(pick) < min(KP.N_PAGE, len(P)):
            i = int(np.argmax(d)); pick.append(i); d = np.minimum(d, np.linalg.norm(P - P[i], axis=1))
        hulls[0] = packed_mesh(*RB.with_wells(P[pick], sp, tol=2.0))
    return dict(hulls=hulls, tail=tail,
                wheels=np.round(sp['wheels']).tolist(), R=round(sp['R'], 1), TW=round(sp['TW'], 1))


def readings(r):
    return {g: (None if r.get(g) is None else round(float(r[g]), 3)) for g in G_KEYS}


def main():
    rows = CA.load(); ok = CA.ranks(rows); F = CA.front(ok)
    fin_p = os.path.join(CA.OUT, 'finals.json'); fin = json.load(open(fin_p))['finals'] if os.path.isfile(fin_p) else []
    fin_by = {f['name']: f for f in fin}
    designs, models, first = [], {}, {}                                   # first: a design's key -> the first stream that picked it (its finals name)
    def add(id_, label, kind, r=None, sp=None, same=None):
        sp = sp or CA.build(CA.q_of(r['z']))
        models[id_] = model_of(sp)
        f = fin_by.get(f'best {same}' if same else label)
        designs.append(dict(id=id_, label=label, kind=kind, same=same, screen=readings(r) if r else None, full=readings(f) if f else None,
                            z=[round(v, 3) for v in r['z']] if r else None, rank=r and round(r['rank']['all'], 3),
                            tail=bool(sp.get('limb')), wheels=len(sp['wheels']), skin=r['q']['shell'] > 0.5 if r else None,
                            mass=round(sp['mass']), length=round(sp['length']), width=round(sp['width']), height=round(sp['height']),
                            top=round(max(np.asarray(h)[:, 2].max() for h in sp['hulls']))))
    seen = set()
    for st in CA.STREAMS:
        r = max(ok, key=lambda r: CA.score(r, st)); key = r['tag'] + str(r['z'][:3])
        add(f'c_{st}', f'best {st}', 'champion', r, same=first.get(key)); seen.add(key); first.setdefault(key, st)
    n = 0
    for r in sorted(F, key=lambda r: -r['rank']['all']):
        key = r['tag'] + str(r['z'][:3])
        if key in seen:
            continue
        n += 1; seen.add(key); add(f'f{n}', f'front {n}', 'front', r)
        if n >= 4:
            break
    main_, _ = GG.roster(True)
    t3 = CA.t3_ref(); add('T3', 'T3', 'reference', sp=t3); add('Box', 'Box', 'reference', sp=main_[0])
    sc_p = os.path.join(CA.config.GAUGES_OUT, 'dash', 'designs.json')    # the references' readings: the finals', else the scorecard's
    sc = {r['design']: r for r in json.load(open(sc_p))} if os.path.isfile(sc_p) else {}
    for d in designs:
        if d['kind'] != 'reference':
            continue
        if d['label'] in fin_by:
            d['full'] = readings(fin_by[d['label']])
        elif d['label'] in sc:
            r = sc[d['label']]
            d['full'] = dict(up=r['upright'], climb=r['step_up_mm'], turn=r['turn_mm'], h_up=r['hill_up_deg'], h_down=r['hill_down_deg'],
                             crest=r['crest_deg'], push=r['push_kg'])
            d['from'] = 'scorecard (step ladder to 150 mm)'
    meshes, ids, out = [], {}, {}
    for id_, m in models.items():                                         # meshes shared where equal
        hs = []
        for h in m['hulls']:
            k = h['v'] + h['f']
            if k not in ids:
                ids[k] = len(meshes); meshes.append(h)
            hs.append(ids[k])
        out[id_] = dict(m, hulls=hs)
    fset = {id(r) for r in F}
    scatter = [[round(r['up'], 3), r['climb'], None if r['turn'] is None else round(r['turn']), r['h_up'], r['h_down'], r['crest'], r[CA.G7],
                int(bool(r.get('tail'))), r.get('wheels', 4), int(r['q']['shell'] > 0.5), int(id(r) in fset)] + ([r['rough']] if CA.ROUGH else []) for r in ok]
    knobs = [dict(key=k, lo=lo, hi=hi, what=next((w for _, kk, _, _, w in K.KNOBS + K.FLIP_KNOBS if kk == k), {'limb': 'a tail (on above half)', 'six': 'six wheels (on above half)', 'shell': 'a skin (on above half; off: the Trainer body)',
                  'flip': 'front flippers (on above half)', 'f_tail': 'the flippers press as the tail pushes (above half)', 'f_nose': 'one flipper on the centre line ahead of the nose, instead of a pair on the front axle (above half)'}.get(k, '')),
                  t3=round((K.T3[k] - lo) / (hi - lo), 3) if k in K.T3 else None) for k, lo, hi in CA.SPACE]
    rounds = sorted({int(r['tag'].split('|')[1]) for r in rows if r['tag'].startswith('C|')})
    data = dict(n=len(rows), built=len(ok), front_n=len(F), rounds=len(rounds), heights=CA.HEIGHTS_EXT, held=list(CA.HELD_K),
                date=RUN_DATE.get(CA.RUN, ''), n_b=CA.N_B, streams=len(CA.STREAMS),
                low=dict(top=CA.LOW_TOP, up=CA.UP_MIN, cap=CA.TURN_CAP, seeds=sum(1 for _ in open(CA.SEED_FROM))) if CA.LOW else None,
                switches=sum(k in CA.KEYS for k in ('limb', 'six', 'shell', 'flip', 'f_tail', 'f_nose')),
                deadline=f'{CA.DEADLINE:%H:%M}', finals=bool(fin), findings=RUN_FINDINGS.get(CA.RUN) if fin else None, labels=LABEL, gauges=G_KEYS, designs=designs, knobs=knobs,
                scatter=scatter, models=dict(meshes=meshes, designs=out))
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/null', json.dumps(data, separators=(',', ':'), default=float))
    path = os.path.join(CA.OUT, 'capability.html'); open(path, 'w', encoding='utf-8').write(html)
    print(path, f'{len(html.encode()) / 1024:.0f} kB; {len(rows)} screened, front {len(F)}, finals {bool(fin)}')


if __name__ == '__main__':
    main()
