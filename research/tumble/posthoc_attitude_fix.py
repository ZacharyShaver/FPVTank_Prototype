"""POST HOC (2026-10-14, after the drops were scored): the committed predictions' start attitudes were wrong.

scale_model.predict turned each simulated drop to a random heading about the body's own z axis after tilting it, not
about the world's vertical. For the nose-down, tail-down and both side-down starts that axis is horizontal, so each
of those starts was an even mix of both ends and both sides. This reruns the predictions with that one fix
(world_yaw=True), everything else as committed (uniform-solid mass layout, 200 drops per start, seed 7, the same
three frictions), and scores them against the same drops with score_drops.py's rules. The printed-mass layout
(posthoc_print_mass.py) is run too, with the fix.

    python research/tumble/posthoc_attitude_fix.py
      -> research/results/drop_predictions_fixed_attitudes.json, posthoc_attitude_fix.json and .md
"""
import os, sys, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
import numpy as np
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
BODIES = ('E1_tub', 'E2_dome', 'E3_tall')


def one(args):
    name, high, mu, lay = args
    import scale_model as S, predict_drops as PD
    kw = dict(n_per=200, mu=mu, seed=7, world_yaw=True)
    if lay == 'printed':
        import posthoc_print_mass as PM
        pr = PM.body_props(name, PM.parse()[name]); kw['layout'] = PM.layout(name, pr, high)
    return (name, high, mu, lay), S.predict(name, PD.GRAMS[name], high, S.ATTITUDES, **kw)


def as_predictions(R, lay):
    out = {}
    for n in BODIES:
        for h in (False, True):
            nom = R[(n, h, 1.0, lay)]
            out[f"{n} mass {'high' if h else 'low'}"] = dict(
                mass_g=nom['mass_g'], com_mm=nom['com_mm'],
                by_attitude={a: dict(p=nom['by_attitude'][a], p_lowmu=R[(n, h, 0.65, lay)]['by_attitude'][a],
                                     p_highmu=R[(n, h, 1.5, lay)]['by_attitude'][a]) for a in nom['by_attitude']})
    return out


if __name__ == '__main__':
    import score_drops as SD
    jobs = [(n, h, mu, 'uniform') for n in BODIES for h in (False, True) for mu in (1.0, 0.65, 1.5)]
    jobs += [(n, h, 1.0, 'printed') for n in BODIES for h in (False, True)]
    with Pool(12) as pool:
        R = dict(pool.map(one, jobs))
    Pf = as_predictions(R, 'uniform')
    json.dump(Pf, open(os.path.join(ROOT, 'results', 'drop_predictions_fixed_attitudes.json'), 'w'), indent=1)
    Pp = {f"{n} mass {'high' if h else 'low'}": dict(by_attitude={a: dict(p=p) for a, p in R[(n, h, 1.0, 'printed')]['by_attitude'].items()})
          for n in BODIES for h in (False, True)}
    P0 = json.load(open(os.path.join(ROOT, 'results', 'drop_predictions.json')))
    D = SD.drops(); rng = np.random.default_rng(0)
    models = {'committed (start bug)': P0, 'start fixed': Pf, 'start fixed + printed mass': Pp}
    res = {}
    for lab, P in models.items():
        g = {}
        for b in BODIES:
            for m in ('low', 'high'):
                rows = [r for r in D if r['body'] == b and r['mass'] == m]
                s = SD.score(rows, P, rng)
                pm = np.mean([SD.predicted(P, b, m, r['start']) for r in rows], 0)
                g[f'{b} mass {m}'] = dict(brier=s['brier_model'], naive=s['brier_naive'], top=s['top_hit_model'],
                                          p=dict(zip(SD.CLS, pm.round(3).tolist())))
        a = SD.score(D, P, rng)
        res[lab] = dict(groups=g, all=a)
    res['start fixed, friction'] = {f: SD.score(D, Pf, rng, f)['brier_model'] for f in ('p_lowmu', 'p_highmu')}
    # where the misses were: by start, pooled over bodies
    st = lambda s: 'side' if s in ('left side down', 'right side down') else s
    by_start = {}
    for lab in ('committed (start bug)', 'start fixed'):
        P = models[lab]; by_start[lab] = {}
        for m in ('low', 'high'):
            for s in ('nose down', 'tail down', 'side', 'upside down', 'upside down, 45 to the left'):
                rows = [r for r in D if r['mass'] == m and st(r['start']) == s]
                pm = np.mean([SD.predicted(P, r['body'], m, r['start']) for r in rows], 0)
                ob = np.mean([SD.onehot(SD.MARK2CLS[r['mark']]) for r in rows], 0)
                by_start[lab][f'{m} / {s}'] = dict(n=len(rows), predicted=dict(zip(SD.CLS, pm.round(2).tolist())),
                                                   observed=dict(zip(SD.CLS, ob.round(2).tolist())))
    res['by_start'] = by_start; res['note'] = 'post hoc'
    json.dump(res, open(os.path.join(ROOT, 'results', 'posthoc_attitude_fix.json'), 'w'), indent=1)
    L = ['# Post hoc: the start-attitude fix', '',
         '| model | Brier, all 181 | 95% CI of (model - naive) | top state right |', '|---|---|---|---|']
    for lab in models:
        a = res[lab]['all']
        L.append(f"| {lab} | {a['brier_model']} | {a['diff_95'][0]} to {a['diff_95'][1]} | {a['top_hit_model']} |")
    L += ['', f"Naive: {res['start fixed']['all']['brier_naive']}. Start fixed at 0.65x / 1.5x friction: "
          f"{res['start fixed, friction']['p_lowmu']} / {res['start fixed, friction']['p_highmu']}.", '',
          '| group | committed | start fixed | + printed mass | P(upright) committed / fixed / seen |', '|---|---|---|---|---|']
    for g in res['start fixed']['groups']:
        c, f, p = (res[l]['groups'][g] for l in models)
        seen = np.mean([SD.MARK2CLS[r['mark']] == 'upright' for r in D if f"{r['body']} mass {r['mass']}" == g])
        L.append(f"| {g} | {c['brier']} | {f['brier']} | {p['brier']} | {c['p']['upright']} / {f['p']['upright']} / {seen:.2f} |")
    L += ['', '## By start, pooled over bodies (predicted > observed), start fixed', '']
    for k, v in by_start['start fixed'].items():
        L.append(f"- {k} (n={v['n']}): " + ', '.join(f"{c} {v['predicted'][c]:.2f}>{v['observed'][c]:.2f}" for c in SD.CLS))
    open(os.path.join(ROOT, 'results', 'posthoc_attitude_fix.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
