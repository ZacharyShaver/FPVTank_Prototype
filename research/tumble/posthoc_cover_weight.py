"""POST HOC, exploratory (2026-10-14): how light must a tall shell be for its shape to help self-righting?

The sweep (D) gave every shell 600 g at Z 50 (audit B2). Here the tub's 600 g stays as the chassis, and a shell that
reaches beyond the tub adds a cover: the extra area, at COVER_T mm of solid PLA, at that area's centroid
(tumble.SHELL_MASS = 'cover'). A printed cover at 2 walls and 15% infill is roughly 1-1.5 mm of solid.

    python research/tumble/posthoc_cover_weight.py -> research/results/posthoc_cover_weight.json and .md
"""
import os, sys, json
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
DESIGNS = {'tub': dict(top=66, round=0.08, width=65.75, dz=0), 'E2-like dome': dict(top=150, round=0.3, width=130, dz=0),
           'E3-like tall': dict(top=210, round=0.15, width=165, dz=-10), 'tall wide 200/0.3/170': dict(top=200, round=0.3, width=170, dz=0),
           'tall low CoM 180/0.2/150/-20': dict(top=180, round=0.2, width=150, dz=-20)}
THICK = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.6]
N = 400


def run(args):
    name, t = args
    import tumble as T
    T.SHELL_MASS = 'cover'; T.COVER_T = t
    p = DESIGNS[name]; r = T.trials(p, N, seed=11); M, c, _ = T.inertia(T.mass_model(T.norm(p)))
    return name, t, dict(p_upright=r['p_upright'], counts=r['counts'], mass_g=round(M), com_z=round(float(c[2]), 1))


if __name__ == '__main__':
    with Pool(20) as pool:
        R = pool.map(run, [(n, t) for n in DESIGNS for t in THICK])
    out = {n: {str(t): r for nn, t, r in R if nn == n} for n in DESIGNS}
    json.dump(dict(note='post hoc, exploratory', drops=N, thickness_mm=THICK, designs=DESIGNS, results=out),
              open(os.path.join(ROOT, 'results', 'posthoc_cover_weight.json'), 'w'), indent=1)
    L = ['# Post hoc: P(upright) vs the cover\'s weight (mm of solid PLA over the shell area beyond the tub)', '',
         f'{N} drops each; binomial SE about 0.024 at P = 0.4. The tub has no cover, so its row is the reference.', '',
         '| design | ' + ' | '.join(f'{t} mm' for t in THICK) + ' |', '|---|' + '---|' * len(THICK)]
    for n in DESIGNS:
        L.append(f'| {n} | ' + ' | '.join(f"{out[n][str(t)]['p_upright']:.2f} ({out[n][str(t)]['mass_g']} g, CoM {out[n][str(t)]['com_z']})" for t in THICK) + ' |')
    open(os.path.join(ROOT, 'results', 'posthoc_cover_weight.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L))
