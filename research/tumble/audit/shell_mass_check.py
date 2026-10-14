"""Audit (2026-10-14): the sweep's fixed 600 g shell vs a shell whose mass scales with its area (tumble.SHELL_MASS).
See AUDIT.md.    python research/tumble/audit/shell_mass_check.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import tumble as T
from multiprocessing import Pool

def run(a):
    mode, p = a; T.SHELL_MASS = mode
    r = T.trials(p, 400, seed=11); M, c, _ = T.inertia(T.mass_model(T.norm(p)))
    return mode, p, r['p_upright'], M, c[2]

designs = [dict(top=66, round=0.08, width=65.75, dz=0), dict(top=150, round=0.3, width=130, dz=0),
           dict(top=210, round=0.15, width=165, dz=-10), dict(top=200, round=0.3, width=170, dz=0), dict(top=180, round=0.2, width=150, dz=-20)]
if __name__ == '__main__':
    with Pool(10) as pool:
        R = pool.map(run, [(m, d) for d in designs for m in ('fixed', 'area')])
    for mode, p, pu, M, cz in R:
        print(f"top {p['top']:>3} round {p['round']:.2f} width {p['width']:>6} dz {p['dz']:>3}  shell {mode:<5}: mass {M:5.0f} g  CoM z {cz:5.1f}  P(upright) {pu:.2f}", flush=True)
