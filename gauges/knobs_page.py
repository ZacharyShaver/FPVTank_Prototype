"""The knob log's page: every knob's effect on every gauge, from knobs.py's sweep, with the side-slope probe and the
surrogate's fit (surrogate.py) beside it, and a little model of every setting (a side view on each row, a 3D view with
a slider when a row opens).

    python gauges/knobs_page.py          -> gauges/out/knobs/knobs.html (published as the "Scorpion Knobs" artifact)
    python gauges/knobs_page.py models   -> gauges/out/knobs/models.json first (every setting rebuilt; built once if missing)
"""
import os, sys, json
os.environ.setdefault('SCORPION_SEARCH', 'search_hills')
import numpy as np
from scipy.spatial import ConvexHull
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config

OUT = os.path.join(config.GAUGES_OUT, 'knobs')
TEMPLATE = os.path.join(HERE, 'knobs_page.tmpl.html')
MODELS = os.path.join(OUT, 'models.json')
KEEP = ('v', 'up', 'climb', 'turn', 'h_up', 'h_down', 'hb_up', 'hb_down', 'crest', 'push', 'com_z', 'mass', 'width', 'length', 'tip_static')


def mesh(P):
    """a hull's triangles, wound outward (as view.py's)"""
    h = ConvexHull(P); F = h.simplices.copy()
    for i, (f, e) in enumerate(zip(F, h.equations)):
        a, b, c = P[f]
        if np.cross(b - a, c - a) @ e[:3] < 0:
            F[i] = f[[0, 2, 1]]
    used = np.unique(F); idx = -np.ones(len(P), int); idx[used] = np.arange(len(used))
    return dict(v=np.round(P[used]).astype(int).ravel().tolist(), f=idx[F].ravel().tolist())


N_PAGE = 140                              # a hull's corners on the page (models.json keeps them all, ~600)


def packed(h, n=N_PAGE):
    """a hull for the page: thinned to n corners (farthest-point picks, then hulled again) and packed as base64 (corners
    as int16 mm, triangles as uint8 or uint16), about a tenth of the plain numbers (2026-10-28: the page was 2.5 MB and
    loaded badly on Zach's phone)"""
    import base64
    P = np.asarray(h['v'], float).reshape(-1, 3)
    if len(P) > n:
        pick = [int(np.argmax(P[:, 0]))]; d = np.linalg.norm(P - P[pick[0]], axis=1)
        while len(pick) < n:
            i = int(np.argmax(d)); pick.append(i); d = np.minimum(d, np.linalg.norm(P - P[i], axis=1))
        h = mesh(P[pick])
    v = np.asarray(h['v'], '<i2'); w = 1 if len(v) // 3 < 256 else 2
    f = np.asarray(h['f'], '<u1' if w == 1 else '<u2')
    b = lambda a: base64.b64encode(a.tobytes()).decode('ascii')
    return dict(v=b(v), f=b(f), w=w)


def model_job(a):
    import knobs as K, robots as RB
    tag, ch = a; sp = K.make(dict(K.T3, **ch))
    if sp is None:
        return a, None
    lm, tail = sp.get('limb'), None
    if lm:                                                                # stowed, as it drives
        p = np.radians(lm['th_stow']); B = np.asarray(lm['base'], float); tip = B + lm['L'] * np.array([-np.cos(p), 0.0, np.sin(p)])
        tail = dict(base=np.round(B).tolist(), tip=np.round(tip).tolist(), r=RB.LINK_R, foot=lm.get('foot_r', RB.FOOT_R))
    return a, dict(hulls=[mesh(np.asarray(h, float)) for h in sp['hulls']], tail=tail, wheels=np.round(sp['wheels']).tolist(),
                   R=round(sp['R'], 1), TW=round(sp['TW'], 1))


def models():
    """each knob setting's shape and the switches', its hull meshes shared where equal -> models.json"""
    import knobs as K, gauges as GG
    from multiprocessing import Pool
    d = json.load(open(os.path.join(OUT, 'knobs_sweep.json')))
    J = [('T3', {})] + [(k['key'], {k['key']: r['v']}) for k in d['knobs'] for r in d['results'][k['key']] if r['v'] is not None]
    J += [(n, ch) for n, ch in K.SWITCHES]
    with Pool(GG.WORKERS) as pool:
        R = pool.map(model_job, J, chunksize=1)
    meshes, ids, out = [], {}, {}
    for (tag, ch), m in R:
        if m is None:
            continue
        hs = []
        for h in m['hulls']:
            key = json.dumps(h, separators=(',', ':'))
            if key not in ids:
                ids[key] = len(meshes); meshes.append(h)
            hs.append(ids[key])
        v = None if not ch or tag not in ch else ch[tag]
        out.setdefault(tag, []).append(dict(m, hulls=hs, v=v))
    json.dump(dict(meshes=meshes, designs=out), open(MODELS, 'w'), separators=(',', ':'))
    print(f'{len(R)} designs, {len(meshes)} distinct hulls -> {MODELS} ({os.path.getsize(MODELS) / 1024:.0f} kB)')


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
                crestRead=crest, pushRead=push, speed=spd['rows'] if spd else [], grip=grip['rows'] if grip else [], crestCurve=curve,
                models=None)
    M = ld(MODELS)
    if M:
        data['models'] = dict(M, meshes=[packed(h) for h in M['meshes']])
    html = open(TEMPLATE, encoding='utf-8').read().replace('/*DATA*/null', json.dumps(data, separators=(',', ':')))
    path = os.path.join(OUT, 'knobs.html'); open(path, 'w', encoding='utf-8').write(html); print(path, f'{len(html) / 1024:.0f} kB')


if __name__ == '__main__':
    if (sys.argv[1:] == ['models']) or not os.path.exists(MODELS):
        models()
    main()
