"""POST HOC (2026-10-14, after the drops were scored): does the printed plastic's real layout explain the miss?

The pre-registered predictions spread each body's PLA as a uniform solid (scale_model.mass_layout). The bodies were
printed at 10% grid infill with 2 walls and 3 top and bottom layers, so most of the plastic is in the skin. This
script rebuilds each body's mass, centre of mass and inertia from the sliced G-code itself (every extrusion move,
supports, brim and purge excluded), reruns the same predictions with that layout (same hull, drops, seed and
friction), and scores them against the same drops with score_drops.py's rules.

    python research/tumble/posthoc_print_mass.py
      -> research/results/posthoc_print_mass.json and .md
"""
import os, sys, re, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
import numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
GCODE = os.path.join(ROOT, '..', 'head-v2', 'out', 'gcode', 'tumble_bodies_E123_orca_PLA_4h23m.gcode')
SKIP = ('Support', 'Support interface', 'Brim', 'Skirt', 'Custom', 'Prime tower')
G_PER_MM = np.pi * (1.75 / 2) ** 2 * 1.24e-3                          # grams per mm of 1.75 mm PLA
# bed -> model frame, from each object's EXCLUDE_OBJECT polygon: its centre, and which way the spacer (model +X,
# beyond the body) points on the bed. Model bounding-box centre is x 18.865, y 0 for all three STLs.
PLACE = {'E1_tub': ((184.928, 96.75), 180), 'E2_dome': ((79.4567, 183.207), 90), 'E3_tall': ((200.5, 200.5), 0)}
CXM = 18.865
SPACER_X = 50.0                                                         # model x beyond the body: the spacer


def to_model(name, X, Y):
    (cx, cy), rot = PLACE[name]; u, v = X - cx, Y - cy
    if rot == 0: x, y = u, v
    elif rot == 90: x, y = v, -u
    elif rot == 180: x, y = -u, -v
    return x + CXM, y


def parse():
    """point masses (x, y, z, g) per object in the bed frame: each extrusion move (line or arc) is split into pieces
    of at most 1 mm, and its plastic shared equally among them"""
    pts = {}; obj = None; typ = ''; x = y = z = 0.0
    num = re.compile(r'([XYZEIJ])(-?\d*\.?\d+)')
    for line in open(GCODE, encoding='utf-8', errors='ignore'):
        if line.startswith(';TYPE:'):
            typ = line[6:].strip(); continue
        if line.startswith('EXCLUDE_OBJECT_START'):
            obj = line.split('NAME=')[1].split('.stl')[0]; continue
        if line.startswith('EXCLUDE_OBJECT_END'):
            obj = None; continue
        g = line[:3]
        if g not in ('G0 ', 'G1 ', 'G2 ', 'G3 '):
            continue
        c = dict((k, float(v)) for k, v in num.findall(line.split(';')[0]))
        nx, ny, nz = c.get('X', x), c.get('Y', y), c.get('Z', z)
        e = c.get('E', 0.0)
        if obj and e > 0 and typ not in SKIP and (nx != x or ny != y):     # not a bare un-retract
            if g in ('G2 ', 'G3 '):
                cx, cy = x + c.get('I', 0.0), y + c.get('J', 0.0); r = np.hypot(x - cx, y - cy)
                a0, a1 = np.arctan2(y - cy, x - cx), np.arctan2(ny - cy, nx - cx)
                sweep = (a1 - a0) % (2 * np.pi) if g == 'G3 ' else -((a0 - a1) % (2 * np.pi))
                k = max(1, int(np.ceil(abs(sweep) * r)))
                t = a0 + sweep * (np.arange(k) + 0.5) / k
                px, py = cx + r * np.cos(t), cy + r * np.sin(t)
            else:
                k = max(1, int(np.ceil(np.hypot(nx - x, ny - y))))
                f = (np.arange(k) + 0.5) / k; px, py = x + (nx - x) * f, y + (ny - y) * f
            pts.setdefault(obj, []).append(np.c_[px, py, np.full(k, nz - 0.1), np.full(k, e * G_PER_MM / k)])
        x, y, z = nx, ny, nz
    return {k: np.vstack(v) for k, v in pts.items()}


def body_props(name, A):
    xm, ym = to_model(name, A[:, 0], A[:, 1]); zm, g = A[:, 2], A[:, 3]
    body = xm < SPACER_X
    out = {}
    for part, m in (('body', body), ('spacer', ~body)):
        M = g[m].sum(); r = np.c_[xm[m], ym[m], zm[m]]; c = (g[m, None] * r).sum(0) / M
        d = r - c; I = np.einsum('i,ij,ik->jk', g[m], d, d); I = np.trace(I) * np.eye(3) - I
        out[part] = dict(g=float(M), com=c, I=I, xr=(float(xm[m].min()), float(xm[m].max())), zr=float(zm[m].max()))
    return out


def layout(name, props, high):
    """total mass, CoM and inertia with the printed body, the printed spacer in the pocket, and the coins"""
    import scale_model as S
    info = json.load(open(os.path.join(ROOT, 'models', name + '.json'))); k = info['pockets'][0]
    b, sp = props['body'], props['spacer']
    n = k['coins']; m_c = n * S.COIN_G; stack = n * S.COIN_T
    zc = (k['depth'] - stack / 2) if high else stack / 2
    zs = (k['spacer'] / 2) if high else (stack + k['spacer'] / 2)
    cc, cs = np.array([k['x'], k['y'], zc]), np.array([k['x'], k['y'], zs])
    M = b['g'] + m_c + sp['g']; com = (b['g'] * b['com'] + m_c * cc + sp['g'] * cs) / M
    It = b['I'].copy()
    for m, r in ((b['g'], b['com']), (m_c, cc), (sp['g'], cs)):
        d = r - com; It += m * (d @ d * np.eye(3) - np.outer(d, d))
    return M, com, It


def one(args):
    name, high, props = args
    import scale_model as S
    lay = layout(name, props, high)
    return (name, high), S.predict(name, None, high, S.ATTITUDES, n_per=200, mu=1.0, seed=7, layout=lay)


if __name__ == '__main__':
    import scale_model as S, score_drops as SD
    A = parse(); P0 = json.load(open(os.path.join(ROOT, 'results', 'drop_predictions.json')))
    props = {n: body_props(n, A[n]) for n in ('E1_tub', 'E2_dome', 'E3_tall')}
    rep = {}
    for n, pr in props.items():
        info = json.load(open(os.path.join(ROOT, 'models', n + '.json')))
        import predict_drops as PD
        M0, c0, I0, _ = S.mass_layout(info, PD.GRAMS[n], False)
        rep[n] = dict(body_g=round(pr['body']['g'], 2), spacer_g=round(pr['spacer']['g'], 2),
                      body_com_mm=pr['body']['com'].round(2).tolist(), body_x_range=[round(v, 1) for v in pr['body']['xr']],
                      body_top_z=round(pr['body']['zr'], 1), sliced_grams_used_before=PD.GRAMS[n])
        for high in (False, True):
            M, com, I = layout(n, pr, high); Mu, cu, Iu, _ = S.mass_layout(info, PD.GRAMS[n], high)
            rep[n]['mass ' + ('high' if high else 'low')] = dict(
                print_layout=dict(g=round(M, 1), com_z=round(float(com[2]), 2), I_diag=np.diag(I).round(0).tolist()),
                uniform_solid=dict(g=round(Mu, 1), com_z=round(float(cu[2]), 2), I_diag=np.diag(Iu).round(0).tolist()))
    jobs = [(n, h, props[n]) for n in props for h in (False, True)]
    with Pool(6) as pool:
        R = dict(pool.map(one, jobs))
    P1 = {}
    for (n, h), r in R.items():
        P1[f"{n} mass {'high' if h else 'low'}"] = dict(mass_g=r['mass_g'], com_mm=r['com_mm'],
                                                        by_attitude={a: dict(p=p) for a, p in r['by_attitude'].items()})
    D = SD.drops(); rng = np.random.default_rng(0)
    sc = {'uniform solid (pre-registered)': {}, 'printed layout (post hoc)': {}}
    for lab, P in (('uniform solid (pre-registered)', P0), ('printed layout (post hoc)', P1)):
        for b in ('E1_tub', 'E2_dome', 'E3_tall'):
            for m in ('low', 'high'):
                rows = [r for r in D if r['body'] == b and r['mass'] == m]
                s = SD.score(rows, P, rng)
                up = float(np.mean([SD.predicted(P, b, m, r['start'])[0] for r in rows]))
                sc[lab][f'{b} mass {m}'] = dict(brier=s['brier_model'], p_upright=round(up, 3),
                                               seen_upright=round(float(np.mean([SD.MARK2CLS[r['mark']] == 'upright' for r in rows])), 3))
        sc[lab]['all'] = SD.score(D, P, rng)['brier_model']
    out = dict(note='post hoc', bodies=rep, scores=sc)
    json.dump(out, open(os.path.join(ROOT, 'results', 'posthoc_print_mass.json'), 'w'), indent=1, default=float)
    L = ['# Post hoc: the printed mass layout (from the G-code) instead of a uniform solid', '',
         '| body | PLA in the print (g) | sliced estimate used (g, body + spacer) | CoM height, mass low: print / uniform (mm) | mass high |',
         '|---|---|---|---|---|']
    for n, r in rep.items():
        L.append(f"| {n} | {r['body_g']} + spacer {r['spacer_g']} | {r['sliced_grams_used_before']} | "
                 f"{r['mass low']['print_layout']['com_z']} / {r['mass low']['uniform_solid']['com_z']} | "
                 f"{r['mass high']['print_layout']['com_z']} / {r['mass high']['uniform_solid']['com_z']} |")
    L += ['', '| group | Brier, uniform | Brier, printed | P(upright) uniform | printed | seen |', '|---|---|---|---|---|---|']
    for g in sc['printed layout (post hoc)']:
        if g == 'all': continue
        a, b = sc['uniform solid (pre-registered)'][g], sc['printed layout (post hoc)'][g]
        L.append(f"| {g} | {a['brier']} | {b['brier']} | {a['p_upright']} | {b['p_upright']} | {b['seen_upright']} |")
    L.append(f"| all | {sc['uniform solid (pre-registered)']['all']} | {sc['printed layout (post hoc)']['all']} | | | |")
    open(os.path.join(ROOT, 'results', 'posthoc_print_mass.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
