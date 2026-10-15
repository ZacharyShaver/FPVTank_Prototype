"""EXPLORATORY (2026-10-15): the best sweep design made wider than the sweep allowed (half-width past 175 mm).

    python research/tumble/explore_wider.py -> research/results/explore_wider.json and .md

The surrogate (surrogate_gp.py) put the best design in the corner of the searched range, with P(upright) still rising
with width. This runs the simulator past the edge: the best design's top, round and dz, half-width 150-350 mm (the
sweep stopped at 175: 350 mm across, wider than the 339.5 mm length), 1000 drops each, cover + bounce and cover + dead
as in posthoc_sweep_v2. It also records what the surrogate guessed for each width before these runs, as a check of
how it extrapolates.
"""
import os, sys, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
WIDTHS = [150.0, 175.0, 200.0, 225.0, 250.0, 300.0, 350.0]
VARIANTS = {'cover, bounce': ('cover', 0.2), 'cover, dead': ('cover', None)}


def one(args):
    import posthoc_sweep_v2 as PS
    lab, w, x, mode, dr = args
    return (lab, w), PS.one((0, x, 1000, mode, dr, 1.5, 777))


if __name__ == '__main__':
    import surrogate_gp as SG
    D = json.load(open(os.path.join(ROOT, 'results', 'posthoc_sweep_v2.json')))['results']
    best = D['cover, bounce']['top_confirmed'][0]['params']
    jobs = [(lab, w, [best['top'], best['round'], w, best['dz']], mode, dr) for lab, (mode, dr) in VARIANTS.items() for w in WIDTHS]
    guess = {}
    for lab in VARIANTS:
        v = D[lab]; g = SG.GP().fit(SG.scale([r['params'] for r in v['all']]), np.array([r['p_upright'] for r in v['all']]))
        m, s = g.predict(SG.scale([dict(best, width=w) for w in WIDTHS])); s = np.sqrt(np.maximum(s ** 2 - g.sn2, 0))
        guess[lab] = {w: (float(a), float(b)) for w, a, b in zip(WIDTHS, m, s)}
    with Pool(len(jobs)) as pool:
        R = dict(pool.map(one, jobs))
    out = dict(best=best, runs={lab: [dict(half_width=w, across_mm=2 * w, p_upright=R[(lab, w)]['p_upright'], mass_g=R[(lab, w)]['mass_g'],
                                           com_z=R[(lab, w)]['com_z'], counts=R[(lab, w)]['counts'], surrogate=round(guess[lab][w][0], 3),
                                           surrogate_95=round(1.96 * guess[lab][w][1], 3)) for w in WIDTHS] for lab in VARIANTS})
    json.dump(out, open(os.path.join(ROOT, 'results', 'explore_wider.json'), 'w'), indent=1)
    L = ['# The best design, wider than the sweep allowed (exploratory)', '',
         f"Top {best['top']:.0f} mm, round {best['round']:.2f}, dz {best['dz']:.0f} mm; only the shell's half-width changes. "
         'The sweep stopped at half-width 175 (350 mm across; the robot is 339.5 mm long). 1000 drops each (sampling error about +-1.5 pts). '
         'The surrogate column is what the Gaussian process predicted before these runs; past 175 it is extrapolating.', '']
    for lab in VARIANTS:
        L += [f'## {lab}', '', '| half-width (mm) | across (mm) | simulator P(upright) | surrogate guess | mass (g) | CoM height (mm) |', '|---|---|---|---|---|---|']
        L += [f"| {r['half_width']:.0f} | {r['across_mm']:.0f} | {r['p_upright']:.3f} | {r['surrogate']:.3f} +- {r['surrogate_95']:.3f} | {r['mass_g']} | {r['com_z']} |"
              for r in out['runs'][lab]] + ['']
    open(os.path.join(ROOT, 'results', 'explore_wider.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
