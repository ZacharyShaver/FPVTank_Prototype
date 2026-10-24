"""Run the pan coil's checks on the design, on their negative controls, or on a file of mutants.

    python run_checks.py                   # the design as it stands: each check, pass or FAIL
    python run_checks.py --control         # each check's negative control: every one must FAIL
    python run_checks.py my_mutants.py     # every mutant in the file against every check, one process each

A mutants file defines MUTANTS = {id: (operator, description)}, with operators from operators.py:
    from operators import *
    MUTANTS = {'A01': (move('servo', (0, 0, 1.0)), 'servo 1 mm high')}
Each (mutant, check) runs in a fresh process: import the generator, apply the mutant, import the checks, run one.
A check "kills" a mutant when it fails on it; a check that crashes on one has flagged it, and says so.
"""
import os, sys, io, time, contextlib, importlib.util
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = ['pairs', 'insertion', 'assembly', 'gear_play', 'bearing_races']


def task(mfile, mid, check, control=False):
    sys.path.insert(0, HERE)
    for mod in ('pan_coil_b', 'pan_coil_b_check', 'operators'):
        sys.modules.pop(mod, None)
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        import pan_coil_b as P
        if mfile:
            spec = importlib.util.spec_from_file_location('mutants_file', mfile)
            M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
            M.MUTANTS[mid][0](P)
        if control:
            P.GEAR_GAP, P.RELIEF_D = 0.0, 0.0
        import pan_coil_b_check as C
        fns = {k: v[0] for k, v in P.PARTS.items()}
        box = {k: (np.array(v[1], float), np.array(v[2], float)) for k, v in P.PARTS.items()}
        if control:
            fns['servo'] = C.shift_servo(P.servo, -4.0, 2.5)
            box['servo'] = (box['servo'][0] + [-4, 0, 2.5], box['servo'][1] + [-4, 0, 2.5])
        try:
            if check == 'pairs':
                bad, worst = 0, ''
                for a, b, allow, note in C.PAIRS:
                    lo = np.maximum(box[a][0], box[b][0]) - 1; hi = np.minimum(box[a][1], box[b][1]) + 1
                    if np.any(hi <= lo):
                        continue
                    pans = C.PANS if (a in C.ROTATES or b in C.ROTATES) else (0,)
                    w = max(C.overlap(C.at_pan(a, fns, d), C.at_pan(b, fns, d), lo, hi, C.STEP) for d in pans)
                    if w > allow + 1.0:
                        bad += 1; worst = worst or f'{a} vs {b} {w:.0f} mm3'
                r, detail = bad, worst
            elif check in ('insertion', 'assembly'):
                r, detail = getattr(C, check)(fns, box, control), ''
            else:
                r, detail = getattr(C, check)(control), ''
        except Exception as e:
            r, detail = -1, f'error: {type(e).__name__}: {e}'[:160]
    lines = [l for l in out.getvalue().splitlines() if '<==' in l]
    return mid, check, int(r != 0), detail or '; '.join(l.strip() for l in lines)[:200]


def run(jobs, workers):
    res = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for f in as_completed([ex.submit(task, *j) for j in jobs]):
            res.append(f.result())
    return {(m, c): (k, d) for m, c, k, d in res}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    control = '--control' in sys.argv
    t0 = time.time()
    if not args:
        K = run([(None, 'design', c, control) for c in CHECKS], 5)
        want = 'FAIL' if control else 'pass'
        for c in CHECKS:
            k, d = K[('design', c)]
            print(f'{c:<14} {"FAIL" if k else "pass":<5} {"" if ("FAIL" if k else "pass") == want else "<== expected " + want}  {d}')
        print(f'{time.time() - t0:.0f} s')
        return
    mfile = os.path.abspath(args[0])
    spec = importlib.util.spec_from_file_location('mutants_file', mfile)
    M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    ids = list(M.MUTANTS)
    K = run([(mfile, m, c) for m in ids for c in CHECKS], 6)
    print('mutant  ' + ' '.join(f'{c[:9]:>9}' for c in CHECKS) + '  killed  description')
    for m in ids:
        ks = [K[(m, c)][0] for c in CHECKS]
        print(f'{m:<7} ' + ' '.join(f'{"x" if k else ".":>9}' for k in ks) + f'  {"yes" if any(ks) else "NO":>6}  {M.MUTANTS[m][1]}')
        for c in CHECKS:
            if K[(m, c)][1]:
                print(f'          {c}: {K[(m, c)][1]}')
    print(f'{sum(any(K[(m, c)][0] for c in CHECKS) for m in ids)} of {len(ids)} killed; {time.time() - t0:.0f} s')


if __name__ == '__main__':
    main()
