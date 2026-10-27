"""The generative searches as one page: the finalists in an interactive 3D view with the step each climbs and the
circle each turns in, the shape-only search (S) beside the one with a tail (T), every screened design on the
climb-against-turn chart, and the guessed numbers.

    python gauges/view.py   -> gauges/out/search/search_view.html (three.js r128 from cdnjs)
"""
import os, sys, json, pickle
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config

OUT = os.path.join(config.GAUGES_OUT, 'search')
OUT_LIMB = config.GAUGES_CURRENT                                       # the current search (tools/config.py)
if len(sys.argv) > 1:                                                     # or a named one: python gauges/view.py search_shape
    OUT_LIMB = os.path.join(config.GAUGES_OUT, sys.argv[1])
    os.environ['SCORPION_SEARCH'] = sys.argv[1]                           # search.py's knob space for that run


def mesh(P):
    h = ConvexHull(P); F = h.simplices.copy()
    for i, (f, e) in enumerate(zip(F, h.equations)):                      # outward winding
        a, b, c = P[f]
        if np.cross(b - a, c - a) @ e[:3] < 0:
            F[i] = f[[0, 2, 1]]
    used = np.unique(F); idx = -np.ones(len(P), int); idx[used] = np.arange(len(used))
    return dict(v=np.round(P[used], 1).ravel().tolist(), f=idx[F].ravel().tolist())


def entry(sp, worst, role, by_mu=None, meets=None, x=None):
    import robots as RB
    hulls = sp['hulls']; lm = sp.get('limb'); tail = None
    if lm:
        P = RB.limb_points(lm, 0.0, lm['th_stow'])
        tail = dict(base=np.round(lm['base'], 1).tolist(), tip=np.round(P[7], 1).tolist(), r=RB.LINK_R, foot=RB.FOOT_R,
                    L=lm['L'], tq=lm['tq'], th_push=lm['th_push'], th_stow=lm['th_stow'])
    return dict(name=sp['name'], role=role, body=mesh(hulls[0]), shell=[mesh(h) for h in hulls[1:]], tail=tail,
                skin=any(n.startswith('skin') for n in sp['notes']),
                wheels=[[x_, y_] for x_, y_ in sp['wheels']], R=sp['R'], TW=sp['TW'],
                upright=worst['upright'], climb=worst['climb'], turn=worst['turn'], meets=meets,
                by_mu={m: dict(upright=v['upright'], climb=v['climb'], turn=v['turn']) for m, v in (by_mu or {}).items()},
                mass=sp['mass'], length=sp['length'], width=sp['width'], height=sp['height'], belly=sp['belly'],
                notes=sp['notes'], x=x)


def load_rows(out, tags):
    rows = []
    for tag in tags:
        p = os.path.join(out, f'screen_{tag}.jsonl')
        if os.path.isfile(p):
            rows += [json.loads(l) for l in open(p)]
    return rows


def main():
    import search as SS
    card = json.load(open(os.path.join(config.GAUGES_OUT, 'scorecard.json')))
    main_, _ = pickle.load(open(os.path.join(config.GAUGES_OUT, 'roster.pkl'), 'rb'))
    designs, seen = [], set()
    for out in (OUT_LIMB,):                                               # the first shape search (OUT) counted the walls twice: superseded
        fp = os.path.join(out, 'finals.json')
        if not os.path.isfile(fp):
            continue
        specs = {sp['name']: sp for sp in pickle.load(open(os.path.join(out, 'finals_specs.pkl'), 'rb'))}
        for f in json.load(open(fp))['finals']:
            if f['name'] in seen:                                         # the box comes with each search: keep one
                continue
            seen.add(f['name'])
            role = 'baseline' if f['name'] == 'Box' else 'control' if f.get('control') else 'finalist'
            designs.append(entry(specs[f['name']], f['worst'], role, f['by_mu'], f['meets'], f['x']))
    for sp in main_:
        if sp['name'] in ('Trainer', 'Six-wheel', 'E4 weeble'):
            r = card['results'][sp['name']]
            designs.append(entry(sp, r['worst'], 'existing', r['by_mu'], r['worst']['upright'] >= SS.UP_MIN))
    rows = load_rows(OUT_LIMB, ('B', 'C', 'S', 'R', 'K')); tail = lambda r: len(r['x']) > 18 and r['x'][18] > SS.LIMB_ON   # S, R, K: seeds, refinements
    pt = lambda rs: [[r['climb'], round(r['turn']), int(r['up'] >= SS.UP_SCREEN)] for r in rs                 # a cut design has no climb
                     if r.get('turn') is not None and r.get('climb') is not None]
    run = os.path.basename(OUT_LIMB); shape = run == 'search_shape'
    lean = run in ('search_lean', 'search_body', 'search_shape'); body = run in ('search_body', 'search_shape')
    st = dict(n_screened=len(rows), n_tail=sum(tail(r) for r in rows), n_feasible=sum(r['up'] >= SS.UP_SCREEN for r in rows),
              n_cut=sum(bool(r.get('cut')) for r in rows), n_old=len(load_rows(OUT, ('B', 'C', 'E'))), up_min=SS.UP_MIN,
              up_screen=SS.UP_SCREEN, knobs=len(SS.ZK) if lean else len(SS.KEYS), n_random=1024 if lean else 1500,
              screen=('30 falls at ×1.5, then 30 at ×0.65, the worse counting, with the tail righting it for up to 10 s; '
                      'stopped as soon as the bar is out of reach, and then no climb; above the bar, the step ladder at the worse of ×0.65 and ×1.5; the turn at every friction')
              if lean else '40 falls at ×1 with the tail righting it for up to 10 s, the step ladder at the worse of ×0.65 and ×1.5, the turn at every friction',
              bar=(f'30 falls at ×1.5 and 30 at ×0.65, the worse reading at least {SS.UP_SCREEN}' if lean else f'40 falls at ×1 reading at least {SS.UP_SCREEN}'),
              frozen=(', '.join(f'{k} {v:g}' for k, v in SS.FROZEN.items()) if lean else ''), frozen_note=(
                  "One at a time, the middle axle, the packs' height and the motor's size moved no gauge on the drive finalists, or only for the worse."
                  + ("" if body else " The skin's shape is held at T5's by choice.")),
              family=("Wheel size, wheelbase centre, tyre gap, track width, belly height and the packs' place on the Trainer's parts; the "
                      "drive's gearing (the motor held at the Trainer's 37 mm); " + ("a skin (a superellipsoid, 10 knobs, grown where a part would poke out: the body's shape) "
                      if body else "a skin (a superellipsoid: its height and top free, its shape held at T5's) ") +
                      "or the Trainer's own body; and a tail (on or off, length, servo torque, push angle, stowed angle, mount height)") if lean else
                     ("Wheels, axles, track width, belly height and battery position on the Trainer's parts; the drive motor's size and gearing; "
                      "a middle axle; a skin (a superellipsoid, 10 knobs, grown where a part would poke out) or the Trainer's own body; and a tail "
                      "(on or off, length, servo torque, push angle, stowed angle, mount height)"),
              seeded=(f"Seeded from the start with {len(load_rows(OUT_LIMB, ('S',)))} designs, the lean and drive searches' fronts and finalists, "
                      f"re-screened on this screen. G2 runs on the step reflex of 2026-10-27 (a kick to free a caught nose, a push when nose up). "
                      f"Then a refinement held to skinned designs ({len(load_rows(OUT_LIMB, ('K',)))} more), from the finalists put in the tightest skin: "
                      f"the search's random skins were mostly big, and its refinements had started from skinless designs.") if body else
                     (f"Then the drive search's front and finalists, {len(load_rows(OUT_LIMB, ('S',)))} designs, re-screened on this screen and refined under "
                      f"the two middle weightings ({len(load_rows(OUT_LIMB, ('R',)))} more): the unseeded search hadn't reached the drive search's middle of the front.") if lean else '')
    if shape:                                                             # the shape study: one platform, the body's shape alone
        st.update(title='Scorpion Body Shapes', eyebrow="Scorpion · body shape on T5's locked platform",
                  h1="What does the body's shape buy?", n_random=512,
                  family=("The skin's shape alone: centre, reach forward and back, half-width, the widest section's height, the "
                          "top above it and the bottom below it, and how square the plan, top and bottom are. Held at T5's: the wheels, "
                          "drive, insides and tail, the tail's mount pinned where T5 has it"),
                  frozen_note="The skins run from the tightest the parts allow to a little bigger than T5's.",
                  seeded="Seeded with T5's own shape and the tightest skin.")
    data = dict(designs=designs, screened=dict(tail=pt([r for r in rows if tail(r)]), plain=pt([r for r in rows if not tail(r)])), stats=st)
    tpl = open(os.path.join(HERE, 'view_template.html'), encoding='utf-8').read()
    page = tpl.replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    if shape:
        page = page.replace('<title>Scorpion Search</title>', '<title>Scorpion Body Shapes</title>', 1)
    path = os.path.join(OUT_LIMB, 'shape_view.html') if shape else os.path.join(OUT, 'search_view.html')
    open(path, 'w', encoding='utf-8').write(page)
    print(path, f'{len(page) / 1e3:.0f} kB')


if __name__ == '__main__':
    main()
