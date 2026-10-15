"""EXPLORATORY (2026-10-15): the best sweep design pushed past the edge of the sweep, one setting at a time.

    python research/tumble/explore_edge.py --key width  -> research/results/explore_edge_width.json and .md
    python research/tumble/explore_edge.py --key top    -> research/results/explore_edge_top.json and .md

The surrogate (surrogate_gp.py) put the best design in the corner of the searched range: half-width near the 175 mm
limit, top near the 220 mm limit. This runs the simulator past the edge: the best design with one setting changed
(half-width 150-350 mm, or top 180-400 mm), 1000 drops each, cover + bounce and cover + dead as in posthoc_sweep_v2.
It also records what the surrogate guessed for each value before these runs, as a check of how it extrapolates.
"""
import os, sys, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
VALUES = {'width': [150.0, 175.0, 200.0, 225.0, 250.0, 300.0, 350.0], 'top': [180.0, 200.0, 220.0, 250.0, 300.0, 350.0, 400.0]}
NAME = {'width': 'half-width', 'top': 'top height'}
VARIANTS = {'cover, bounce': ('cover', 0.2), 'cover, dead': ('cover', None)}


def one(args):
    import posthoc_sweep_v2 as PS
    lab, w, x, mode, dr = args
    return (lab, w), PS.one((0, x, 1000, mode, dr, 1.5, 777))


if __name__ == '__main__':
    import argparse, surrogate_gp as SG
    ap = argparse.ArgumentParser(); ap.add_argument('--key', choices=list(VALUES), default='width'); KEY = ap.parse_args().key
    WIDTHS = VALUES[KEY]; KI = SG.SW.KEYS.index(KEY)
    D = json.load(open(os.path.join(ROOT, 'results', 'posthoc_sweep_v2.json')))['results']
    best = D['cover, bounce']['top_confirmed'][0]['params']
    jobs = [(lab, w, [w if k == KEY else best[k] for k in SG.SW.KEYS], mode, dr) for lab, (mode, dr) in VARIANTS.items() for w in WIDTHS]
    guess = {}
    for lab in VARIANTS:
        v = D[lab]; g = SG.GP().fit(SG.scale([r['params'] for r in v['all']]), np.array([r['p_upright'] for r in v['all']]))
        m, s = g.predict(SG.scale([dict(best, **{KEY: w}) for w in WIDTHS])); s = np.sqrt(np.maximum(s ** 2 - g.sn2, 0))
        guess[lab] = {w: (float(a), float(b)) for w, a, b in zip(WIDTHS, m, s)}
    with Pool(len(jobs)) as pool:
        R = dict(pool.map(one, jobs))
    out = dict(best=best, key=KEY, runs={lab: [dict(value=w, p_upright=R[(lab, w)]['p_upright'], mass_g=R[(lab, w)]['mass_g'],
                                           com_z=R[(lab, w)]['com_z'], counts=R[(lab, w)]['counts'], surrogate=round(guess[lab][w][0], 3),
                                           surrogate_95=round(1.96 * guess[lab][w][1], 3)) for w in WIDTHS] for lab in VARIANTS})
    json.dump(out, open(os.path.join(ROOT, 'results', f'explore_edge_{KEY}.json'), 'w'), indent=1)
    L = [f"# The best design past the sweep's edge: {NAME[KEY]} (exploratory)", '',
         f"The best design ({'/'.join(f'{best[k]:.2f}' if k == 'round' else f'{best[k]:.0f}' for k in SG.SW.KEYS)}, top/round/half-width/dz) "
         f"with only the {NAME[KEY]} changed. The sweep stopped at {NAME[KEY]} {SG.HI[KI]:.0f} mm "
         "(half-width 175 is 350 mm across; the robot is 339.5 mm long). 1000 drops each (sampling error about +-1.5 pts). "
         f"The surrogate column is what the Gaussian process predicted before these runs; past {SG.HI[KI]:.0f} it is extrapolating.", '']
    for lab in VARIANTS:
        L += [f'## {lab}', '', f'| {NAME[KEY]} (mm) | simulator P(upright) | surrogate guess | mass (g) | CoM height (mm) | upside down | side | end |', '|---|---|---|---|---|---|---|---|']
        L += [f"| {r['value']:.0f} | {r['p_upright']:.3f} | {r['surrogate']:.3f} +- {r['surrogate_95']:.3f} | {r['mass_g']} | {r['com_z']} | "
              f"{r['counts']['inverted']} | {r['counts']['left side'] + r['counts']['right side']} | {r['counts']['nose up'] + r['counts']['nose down']} |"
              for r in out['runs'][lab]] + ['']
    open(os.path.join(ROOT, 'results', f'explore_edge_{KEY}.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
