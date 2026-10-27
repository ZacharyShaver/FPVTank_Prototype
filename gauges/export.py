"""The scorecard as row files for the "Scorpion Gauges" page (a private claude.ai page).

    python gauges/export.py      # gauges/out/scorecard.json -> gauges/out/dash/{designs,physics,climb,checks}.json
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config

ROLE = {'Box': 'baseline'}


def main():
    S = json.load(open(os.path.join(config.GAUGES_OUT, 'scorecard.json')))
    # the generative search's finalists, as role 'finalist' (its limp-tail control as 'control'): the search with the tail
    # (search_limb); the first shape search (search) counted the Trainer's walls twice and is superseded
    fp = os.path.join(config.GAUGES_CURRENT, 'finals.json')              # the current search (tools/config.py)
    if os.path.isfile(fp):
        for f in json.load(open(fp))['finals']:
            if f['name'] == 'Box':
                continue
            S['results'][f['name']] = dict(worst=f['worst'], by_mu=f['by_mu'])
            S['dims'][f['name']] = dict(f['dims'], notes=f['notes'] or ['four wheels, the Trainer body'])
            ROLE[f['name']] = 'control' if f.get('control') else 'finalist'
    out = os.path.join(config.GAUGES_OUT, 'dash'); os.makedirs(out, exist_ok=True)
    names = list(S['results'])                                            # the roster, then the controls
    designs, physics, climb = [], [], []
    for name in names:
        r, d = S['results'][name], S['dims'][name]; w = r['worst']
        role = ROLE.get(name, 'design' if name in S['designs'] else 'control')
        lo = min(r['by_mu'], key=lambda m: r['by_mu'][m]['upright'])
        designs.append(dict(design=name, role=role, upright=round(w['upright'], 3), upright_lo=r['by_mu'][lo]['ci'][0],
                            upright_hi=r['by_mu'][lo]['ci'][1], step_up_mm=w['climb'],
                            turn_mm=None if w['turn'] is None else round(w['turn']),
                            spin_s=max(v['turn_s'] for v in r['by_mu'].values()) if w['turn'] is not None else None,
                            mass_g=round(d['mass']), length_mm=round(d['length']), width_mm=round(d['width']),
                            height_mm=round(d['height']), belly_mm=round(d['belly']), wheels=d['wheels'],
                            wheel_d_mm=round(2 * d['R']), notes='; '.join(d['notes'])))
        for m, v in r['by_mu'].items():
            physics.append(dict(design=name, friction=float(m), upright=round(v['upright'], 3), step_up_mm=v['climb'],
                                turn_mm=None if v['turn'] is None else round(v['turn'])))
            for k, n in v['climb_tries'].items():
                h, b = k.split('|')
                row = next((c for c in climb if c['design'] == name and c['friction'] == float(m) and c['height_mm'] == int(h)), None)
                if row is None:
                    row = dict(design=name, friction=float(m), height_mm=int(h), forwards=None, reverse=None, tries=S['n_try']); climb.append(row)
                row['reverse' if b == '1' else 'forwards'] = n
    checks = [dict(check=f"{c['gauge']} control: {c['claim'].split(' reads')[0]}", gauge=c['gauge'],          # unique: the page keys rows on it claim=c['claim'], reads=c['a'] if not isinstance(c['a'], float) else round(c['a'], 3),
                   against=c['b'] if not isinstance(c['b'], float) else round(c['b'], 3), result='pass' if c['ok'] else 'fail') for c in S['controls']]
    for name, e in S['edge'].items():
        checks.append(dict(check=f'step edge, {name}', gauge='climb', claim='the tyre pushes on the step along the line to its axle (within 5 degrees); the sharp edge reads over 20',
                           reads=round(e['round'], 1), against=round(e['sharp'], 1), result='pass' if e['ok'] else 'fail'))
    for name in names:                                                    # the tail's control: the same design, its servos limp
        if name.endswith(', limp tail'):
            a, b = S['results'][name]['worst'], S['results'][name[:-len(', limp tail')]]['worst']
            checks.append(dict(check=f'tail control, {name[:-len(", limp tail")]}', gauge='upright, climb',
                               claim='with its tail limp (0.05 N m) the design reads worse on both upright after a fall and step up',
                               reads=f"{a['upright']:.3f} / {a['climb']} mm", against=f"{b['upright']:.3f} / {b['climb']} mm",
                               result='pass' if (a['upright'] < b['upright'] and a['climb'] < b['climb']) else 'fail'))
    t = S.get('timestep')
    if t:
        checks.append(dict(check='time step', gauge='all', claim='the box at 0.1 ms reads as at 0.2 ms (upright within noise, step up within 10 mm, turn within 3%)',
                           reads=f"{t['upright'][0]:.3f} / {t['climb'][0]} / {round(t['turn'][0])}", against=f"{t['upright'][1]:.3f} / {t['climb'][1]} / {round(t['turn'][1])}",
                           result='pass' if t['ok'] else 'fail'))
    for name, rows in (('designs', designs), ('physics', physics), ('climb', climb), ('checks', checks)):
        json.dump(rows, open(os.path.join(out, f'{name}.json'), 'w'), indent=1)
        print(name, len(rows), 'rows')


if __name__ == '__main__':
    main()
