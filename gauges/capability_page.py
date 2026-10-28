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
             push='G7 push', all='All-rounder')
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


def model_of(sp):
    """a design's shape for the page: hulls (thinned and packed, as the knob page's), the tail stowed, wheels"""
    lm, tail = sp.get('limb'), None
    if lm:
        p = np.radians(lm['th_stow']); B = np.asarray(lm['base'], float); tip = B + lm['L'] * np.array([-np.cos(p), 0.0, np.sin(p)])
        tail = dict(base=np.round(B).tolist(), tip=np.round(tip).tolist(), r=RB.LINK_R, foot=lm.get('foot_r', RB.FOOT_R))
    return dict(hulls=[KP.packed(KP.mesh(np.asarray(h, float))) for h in sp['hulls']], tail=tail,
                wheels=np.round(sp['wheels']).tolist(), R=round(sp['R'], 1), TW=round(sp['TW'], 1))


def readings(r):
    return {g: (None if r.get(g) is None else round(float(r[g]), 3)) for g in G_KEYS}


def main():
    rows = CA.load(); ok = CA.ranks(rows); F = CA.front(ok)
    fin_p = os.path.join(CA.OUT, 'finals.json'); fin = json.load(open(fin_p))['finals'] if os.path.isfile(fin_p) else []
    fin_by = {f['name']: f for f in fin}
    designs, models, first = [], {}, {}                                   # first: a design's key -> the first stream that picked it (its finals name)
    def add(id_, label, kind, r=None, sp=None, same=None):
        sp = sp or K.make(CA.q_of(r['z']))
        models[id_] = model_of(sp)
        f = fin_by.get(f'best {same}' if same else label)
        designs.append(dict(id=id_, label=label, kind=kind, same=same, screen=readings(r) if r else None, full=readings(f) if f else None,
                            z=[round(v, 3) for v in r['z']] if r else None, rank=r and round(r['rank']['all'], 3),
                            tail=bool(sp.get('limb')), wheels=len(sp['wheels']), skin=r['q']['shell'] > 0.5 if r else None,
                            mass=round(sp['mass']), length=round(sp['length']), width=round(sp['width']), height=round(sp['height'])))
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
    t3 = K.make(K.T3); add('T3', 'T3', 'reference', sp=t3); add('Box', 'Box', 'reference', sp=main_[0])
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
    scatter = [[round(r['up'], 3), r['climb'], None if r['turn'] is None else round(r['turn']), r['h_up'], r['h_down'], r['crest'], r['push'],
                int(bool(r.get('tail'))), r.get('wheels', 4), int(r['q']['shell'] > 0.5), int(id(r) in fset)] for r in ok]
    knobs = [dict(key=k, lo=lo, hi=hi, what=next((w for _, kk, _, _, w in K.KNOBS if kk == k), {'limb': 'a tail (on above half)', 'six': 'six wheels (on above half)', 'shell': 'a skin (on above half; off: the Trainer body)'}.get(k, '')),
                  t3=round((K.T3[k] - lo) / (hi - lo), 3) if k in K.T3 else None) for k, lo, hi in CA.SPACE]
    rounds = sorted({int(r['tag'].split('|')[1]) for r in rows if r['tag'].startswith('C|')})
    data = dict(n=len(rows), built=len(ok), front_n=len(F), rounds=len(rounds), heights=CA.HEIGHTS_EXT, held=list(CA.HELD_K),
                deadline=f'{CA.DEADLINE:%H:%M}', finals=bool(fin), findings=FINDINGS if fin else None, labels=LABEL, gauges=G_KEYS, designs=designs, knobs=knobs,
                scatter=scatter, models=dict(meshes=meshes, designs=out))
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/null', json.dumps(data, separators=(',', ':'), default=float))
    path = os.path.join(CA.OUT, 'capability.html'); open(path, 'w', encoding='utf-8').write(html)
    print(path, f'{len(html.encode()) / 1024:.0f} kB; {len(rows)} screened, front {len(F)}, finals {bool(fin)}')


if __name__ == '__main__':
    main()
