"""The knob log's page: every knob's effect on every gauge, from knobs.py's sweep, with the side-slope probe and the
surrogate's fit (surrogate.py) beside it.

    python gauges/knobs_page.py   -> gauges/out/knobs/knobs.html (published as the "Scorpion Knobs" artifact)
"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config

OUT = os.path.join(config.GAUGES_OUT, 'knobs')
TEMPLATE = os.path.join(HERE, 'knobs_page.tmpl.html')
KEEP = ('v', 'up', 'climb', 'turn', 'h_up', 'h_down', 'hb_up', 'hb_down', 'crest', 'push', 'com_z', 'mass', 'width', 'length', 'tip_static')


def main():
    d = json.load(open(os.path.join(OUT, 'knobs_sweep.json'))); res = d['results']
    rnd = lambda x: None if x is None else round(x, 3)
    knobs = [dict(k, t3v=d['base'][k['key']], rows=[{q: rnd(r.get(q)) for q in KEEP} for r in res[k['key']]]) for k in d['knobs']]
    sw = [dict(name=n, row={q: rnd(res[n][0].get(q)) for q in KEEP}) for n in d['switches']]
    side = json.load(open(os.path.join(OUT, 'side.json')))['rows'] if os.path.exists(os.path.join(OUT, 'side.json')) else []
    sf = os.path.join(config.GAUGES_OUT, 'surrogate', 'surrogate.json')
    sur = json.load(open(sf)) if os.path.exists(sf) else {}
    ld = lambda f: json.load(open(f)) if os.path.exists(f) else None
    cr, pu, spd = ld(os.path.join(config.GAUGES_OUT, 'crest', 'read.json')), ld(os.path.join(config.GAUGES_OUT, 'push', 'read.json')), ld(os.path.join(OUT, 'speed.json'))
    crest = cr and dict(rows=[{k: r[k] for k in ('name', 'crest', 'why')} for r in cr['rows']], controls=cr['controls'])
    push = pu and dict(rows=[{k: r[k] for k in ('name', 'push', 'by_mu', 'why')} for r in pu['rows']], controls=pu['controls'])
    grip, curve = ld(os.path.join(OUT, 'grip_hills.json')), ld(os.path.join(config.GAUGES_OUT, 'crest', 'curve.json'))
    curve = curve and {n: {a: {k: sum(r == 'ok' for r in v) for k, v in s.items()} for a, s in c.items()} for n, c in curve.items()}
    data = dict(base={q: rnd(res['T3'][0].get(q)) for q in KEEP}, noise=d['noise'], knobs=knobs, switches=sw, side=side, surrogate=sur,
                crestRead=crest, pushRead=push, speed=spd['rows'] if spd else [], grip=grip['rows'] if grip else [], crestCurve=curve)
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    path = os.path.join(OUT, 'knobs.html'); open(path, 'w', encoding='utf-8').write(html); print(path, f'{len(html) / 1024:.0f} kB')


if __name__ == '__main__':
    main()
