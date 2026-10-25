"""PRE-REGISTERED (2026-10-25): the simulation's predictions for a shell3 body's drops from the stand (15 cm), written
before it is dropped. The same starts, jitter, release height and scoring format as H3c (drop_predictions_15cm_*), so
score_15cm.py's rules apply unchanged.

    python research/tumble/predict3.py NAME [--gcode PATH] [--n 200]
      -> research/results/drop_predictions_15cm_NAME_<model>.json and .md, one per contact model

The mass layout comes from the sliced G-code when given (every extrusion move, supports and brim excluded, as
posthoc_print_mass.py), else from shell3.print_layout's walls-plus-infill estimate. Coins: 12 US quarters in the
centre pocket, spacer first (mass low) or coins first (mass high), as DROP_TEST.md.
"""
import os, sys, re, json, argparse
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import shell3 as S3
import scale_model as S

SKIP = ('Support', 'Support interface', 'Brim', 'Skirt', 'Custom', 'Prime tower')
G_PER_MM = np.pi * (1.75 / 2) ** 2 * 1.24e-3
TITLES = {'hard39': 'hard floor 0.39 (the ball, measured)', 'hard31': 'hard floor 0.31 (E3 slow motion; H3c primary)',
          'hard55': 'hard floor 0.55 (the ball, rough; best at 15 cm)', 'softfit': 'soft floor, bounce fitted at 6 cm'}


def gcode_points(path, name):
    """point masses (x, y, z, g) of one object's extrusion in the bed frame"""
    pts = []; obj = None; typ = ''; x = y = z = 0.0
    num = re.compile(r'([XYZEIJ])(-?\d*\.?\d+)')
    for line in open(path, encoding='utf-8', errors='ignore'):
        if line.startswith(';TYPE:'):
            typ = line[6:].strip(); continue
        if line.startswith('EXCLUDE_OBJECT_START'):
            obj = line.split('NAME=')[1].strip(); continue
        if line.startswith('EXCLUDE_OBJECT_END'):
            obj = None; continue
        g = line[:3]
        if g not in ('G0 ', 'G1 ', 'G2 ', 'G3 '):
            continue
        c = dict((k, float(v)) for k, v in num.findall(line.split(';')[0]))
        nx, ny, nz = c.get('X', x), c.get('Y', y), c.get('Z', z); e = c.get('E', 0.0)
        if obj and name in obj and e > 0 and typ not in SKIP and (nx != x or ny != y):
            if g in ('G2 ', 'G3 '):
                cx, cy = x + c.get('I', 0.0), y + c.get('J', 0.0); r = np.hypot(x - cx, y - cy)
                a0, a1 = np.arctan2(y - cy, x - cx), np.arctan2(ny - cy, nx - cx)
                sw = (a1 - a0) % (2 * np.pi) if g == 'G3 ' else -((a0 - a1) % (2 * np.pi))
                k = max(1, int(np.ceil(abs(sw) * r))); t = a0 + sw * (np.arange(k) + 0.5) / k
                px, py = cx + r * np.cos(t), cy + r * np.sin(t)
            else:
                k = max(1, int(np.ceil(np.hypot(nx - x, ny - y)))); f = (np.arange(k) + 0.5) / k
                px, py = x + (nx - x) * f, y + (ny - y) * f
            pts.append(np.c_[px, py, np.full(k, nz - 0.1), np.full(k, e * G_PER_MM / k)])
        x, y, z = nx, ny, nz
    return np.vstack(pts)


def gcode_layout(path, name, info, P, high):
    """the printed body's own layout, registered to the model by bounding box (no rotation: checked), the spacer
    told apart by X, then the coins and the spacer in the pocket"""
    A = gcode_points(path, name)
    sp_x = P[:, 0].max() + 20.0                                    # the spacer's centre in the model frame
    mx = np.array([P[:, 0].min(), sp_x + S.POCKET_R]); my = np.array([P[:, 1].min(), P[:, 1].max()])
    gx = np.array([A[:, 0].min(), A[:, 0].max()]); gy = np.array([A[:, 1].min(), A[:, 1].max()])
    if abs(np.ptp(gx) - np.ptp(mx)) > 2.0 or abs(np.ptp(gy) - np.ptp(my)) > 2.0:
        raise SystemExit(f'G-code extent {np.ptp(gx):.1f} x {np.ptp(gy):.1f} does not match the model {np.ptp(mx):.1f} x {np.ptp(my):.1f}: rotated?')
    xm = A[:, 0] - gx.mean() + mx.mean(); ym = A[:, 1] - gy.mean() + my.mean(); zm, g = A[:, 2], A[:, 3]
    body = xm < P[:, 0].max() + 5.0
    rb = np.c_[xm[body], ym[body], zm[body]]; Mb = g[body].sum(); cb = (g[body, None] * rb).sum(0) / Mb
    d = rb - cb; Ib = np.einsum('i,ij,ik->jk', g[body], d, d); Ib = np.trace(Ib) * np.eye(3) - Ib
    m_sp = float(g[~body].sum()); pk = info['pockets'][0]
    n = pk['coins']; m_c = n * S.COIN_G; stack = n * S.COIN_T
    zc = (pk['depth'] - stack / 2) if high else stack / 2
    zs = (pk['spacer'] / 2) if high else (stack + pk['spacer'] / 2)
    cc, cs = np.array([pk['x'], 0, zc]), np.array([pk['x'], 0, zs])
    M = Mb + m_c + m_sp; com = (Mb * cb + m_c * cc + m_sp * cs) / M; I = Ib.copy()
    for m, r in ((Mb, cb), (m_c, cc), (m_sp, cs)):
        dd = r - com; I += m * (dd @ dd * np.eye(3) - np.outer(dd, dd))
    return (M, com, I), dict(body_g=round(float(Mb), 2), spacer_g=round(m_sp, 2), body_com=cb.round(2).tolist(),
                             registration_mm=[round(float(np.ptp(gx) - np.ptp(mx)), 2), round(float(np.ptp(gy) - np.ptp(my)), 2)])


def one(a):
    name, model, high, mu, att, n, seed, layout = a
    P = np.load(os.path.join(ROOT, 'models', name + '_hull.npy'))
    r = S3.drops(P, layout, model, starts='stand', n=n, seed=seed, mu=mu) if att is None else None
    if att is not None:
        sub = {att: S.ATTITUDES[att]}
        saved = S.ATTITUDES.copy(); S.ATTITUDES.clear(); S.ATTITUDES.update(sub)
        try:
            r = S3.drops(P, layout, model, starts='stand', n=n, seed=seed, mu=mu)
        finally:
            S.ATTITUDES.clear(); S.ATTITUDES.update(saved)
    return (model, high, mu, att), r['by_start'][att]


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('name'); ap.add_argument('--gcode'); ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--models', nargs='*', default=list(TITLES))
    A = ap.parse_args()
    info = json.load(open(os.path.join(ROOT, 'models', A.name + '.json'))); P = np.load(os.path.join(ROOT, 'models', A.name + '_hull.npy'))
    lay, src = {}, {}
    for high in (False, True):
        if A.gcode:
            lay[high], src[high] = gcode_layout(A.gcode, A.name, info, P, high)
        else:
            lay[high] = S3.print_layout(P, info['pockets'][0], high); src[high] = 'shell3.print_layout (walls + infill estimate)'
    jobs = [(A.name, m, h, mu, att, A.n, 7 + 31 * k, lay[h]) for m in A.models for h in (False, True)
            for mu in ((1.0, 0.65, 1.5) if m == 'hard39' else (1.0,)) for k, att in enumerate(S.ATTITUDES)]
    with Pool(min(30, len(jobs))) as pool:
        R = dict(pool.map(one, jobs, chunksize=1))
    for m in A.models:
        tc, dr, ts = S3.CONTACT[m]
        out = dict(drop_mm=150.0, dampratio=dr, timeconst=tc, timestep=ts, old_start=False, model=TITLES[m],
                   layout_source=src[False] if isinstance(src[False], str) else dict(gcode=os.path.basename(A.gcode), **src[False]),
                   n_per_start=A.n)
        lines = [f'# Drop predictions, {A.name}, 15 cm from the stand: {TITLES[m]}', '',
                 f'Committed before the body is dropped. {A.n} simulated drops per start, +-15 deg jitter, release height 150 mm.',
                 f"Mass layout: {out['layout_source']}.", '']
        for high in (False, True):
            M, com, I = lay[high]; key = f"{A.name} mass {'high' if high else 'low'}"
            ba = {}
            for att in S.ATTITUDES:
                c = R[(m, high, 1.0, att)]; p = {k: v / A.n for k, v in c.items() if v}
                e = dict(p=p)
                if m == 'hard39':
                    for mu, lab in ((0.65, 'p_lowmu'), (1.5, 'p_highmu')):
                        cc = R[(m, high, mu, att)]; e[lab] = {k: v / A.n for k, v in cc.items() if v}
                ba[att] = e
            up = np.mean([ba[a]['p'].get('upright', 0.0) for a in ba])
            out[key] = dict(mass_g=round(float(M), 1), com_mm=np.round(com, 1).tolist(), p_upright_mean=round(float(up), 3), by_attitude=ba)
            lines += [f"## {key} (mass {M:.1f} g, CoM z {com[2]:.1f} mm): P(upright) over the six starts {up:.3f}", '',
                      '| start | upright | inverted | side | on an end |', '|---|---|---|---|---|']
            for att, e in ba.items():
                p = e['p']; lines.append(f"| {att} | {p.get('upright', 0):.3f} | {p.get('inverted', 0):.3f} | "
                                         f"{p.get('left side', 0) + p.get('right side', 0):.3f} | {p.get('nose up', 0) + p.get('nose down', 0):.3f} |")
            lines.append('')
        base = os.path.join(ROOT, 'results', f'drop_predictions_15cm_{A.name}_{m}')
        json.dump(out, open(base + '.json', 'w'), indent=1)
        open(base + '.md', 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
        print('\n'.join(lines))
