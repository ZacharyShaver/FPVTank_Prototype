"""Workstream C: run every check against every seeded fault and score the suites.

    python research/harness/run.py [--workers 28]
      -> research/results/mutation_matrix.csv, mutation_summary.json; research/figures/mutation.png

Each (mutant, check) runs in its own process: import pan_coil_b, apply the mutant, then import pan_coil_b_check and call
the check unchanged. The unmutated design must pass every check (the "none" row) or nothing is scored. A check "kills" a
mutant when it fails on it. Suites:
  S0  'pairs' alone: seated part-against-part interference, the first check this project had (2026-09-19);
  S1  all nine checks, the suite as it grew, each addition prompted by a check that had passed a real defect.
"""
import os, sys, json, time, io, contextlib, argparse
for _v in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):   # one thread per worker: 24 workers each
    os.environ.setdefault(_v, '1')                                         # spawning ~25 BLAS threads oversubscribed 32 cores
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GEN = os.path.abspath(os.path.join(ROOT, '..', 'head-v2', 'generator', 'generators'))
CHECKS = ['pairs', 'insertion', 'assembly', 'gear_play', 'bearing_races', 'screw_threads', 'block_air', 'wire_axis', 'merged_shelf']
S0 = ['pairs']


def task(mid, check):
    sys.path.insert(0, GEN); sys.path.insert(0, os.path.dirname(__file__))
    # A pool worker runs many tasks: drop the model, the checks and the mutants from the module cache so this task
    # starts from the unmutated model, not the last task's mutant.
    for mod in ('pan_coil_b', 'pan_coil_b_check', 'mutants'):
        sys.modules.pop(mod, None)
    out = io.StringIO()
    t0 = time.time()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        import pan_coil_b as P
        import mutants as MU
        if mid != 'none':
            MU.MUTANTS[mid][0](P)
        import pan_coil_b_check as C
        fns = {k: v[0] for k, v in P.PARTS.items()}
        box = {k: (np.array(v[1], float), np.array(v[2], float)) for k, v in P.PARTS.items()}
        try:
            if check == 'pairs':
                bad, worst_pair = 0, ''
                for a, b, allow, note in C.PAIRS:
                    lo = np.maximum(box[a][0], box[b][0]) - 1; hi = np.minimum(box[a][1], box[b][1]) + 1
                    if np.any(hi <= lo):
                        continue
                    pans = C.PANS if (a in C.ROTATES or b in C.ROTATES) else (0,)
                    w = max(C.overlap(C.at_pan(a, fns, d), C.at_pan(b, fns, d), lo, hi, C.STEP) for d in pans)
                    if w > allow + 1.0:
                        bad += 1; worst_pair = worst_pair or f'{a} vs {b} {w:.0f} mm3'
                r, detail = bad, worst_pair
            elif check == 'insertion':
                r, detail = C.insertion(fns, box), ''
            elif check == 'assembly':
                r, detail = C.assembly(fns, box), ''
            else:
                r, detail = getattr(C, check)(), ''
        except Exception as e:                       # a check that crashes on a mutant has flagged it, but say so
            r, detail = -1, f'error: {type(e).__name__}: {e}'[:160]
    return mid, check, int(r != 0), round(time.time() - t0, 1), detail


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--workers', type=int, default=28); a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(__file__))
    import mutants as MU
    ids = ['none'] + list(MU.MUTANTS)
    jobs = [(m, c) for m in ids for c in CHECKS]
    jobs.sort(key=lambda j: -{'assembly': 3, 'insertion': 2, 'pairs': 1}.get(j[1], 0))   # long ones first
    res, t0 = [], time.time()
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(task, *j) for j in jobs]
        for i, f in enumerate(as_completed(futs), 1):
            res.append(f.result())
            if i % 25 == 0:
                print(f'{i}/{len(jobs)}  {time.time() - t0:.0f} s', flush=True)
    K = {(m, c): (k, s, d) for m, c, k, s, d in res}
    base_fail = [c for c in CHECKS if K[('none', c)][0]]
    os.makedirs(os.path.join(ROOT, 'results'), exist_ok=True)
    with open(os.path.join(ROOT, 'results', 'mutation_matrix.csv'), 'w', encoding='utf-8') as fh:
        fh.write('mutant,' + ','.join(CHECKS) + ',killed_by_S0,killed_by_S1,expected,historical,description\n')
        for m in ids:
            row = [str(K[(m, c)][0]) for c in CHECKS]
            s0 = int(any(K[(m, c)][0] for c in S0)); s1 = int(any(K[(m, c)][0] for c in CHECKS))
            d = MU.MUTANTS.get(m, (None, 'unmutated design', '', None))
            fh.write(f'{m},' + ','.join(row) + f',{s0},{s1},"{d[2]}","{d[3] or ""}","{d[1]}"\n')
    M = [m for m in ids if m != 'none']
    hist = [m for m in M if MU.MUTANTS[m][3]]
    sc = lambda suite, ms: sum(any(K[(m, c)][0] for c in suite) for m in ms)
    S = {'baseline_failures': base_fail, 'mutants': len(M), 'historical_mutants': len(hist),
         'S0_pairs_only': {'killed': sc(S0, M), 'of': len(M), 'historical_killed': sc(S0, hist)},
         'S1_full_suite': {'killed': sc(CHECKS, M), 'of': len(M), 'historical_killed': sc(CHECKS, hist)},
         'survivors_S1': [m for m in M if not any(K[(m, c)][0] for c in CHECKS)],
         'kills_per_check': {c: sum(K[(m, c)][0] for m in M) for c in CHECKS},
         'vacuous_checks': [c for c in CHECKS if not any(K[(m, c)][0] for m in M)],
         'errors': {f'{m}/{c}': K[(m, c)][2] for m in ids for c in CHECKS if K[(m, c)][2].startswith('error')},
         'wall_s': round(time.time() - t0), 'cpu_s': round(sum(K[k][1] for k in K))}
    json.dump(S, open(os.path.join(ROOT, 'results', 'mutation_summary.json'), 'w'), indent=1)
    print(json.dumps(S, indent=1))
    figure(K, ids, M, MU)


def figure(K, ids, M, MU):
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    A = np.array([[K[(m, c)][0] for c in CHECKS] for m in M])
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    ax.imshow(A, cmap='Greens', vmin=0, vmax=1.4, aspect='auto')
    ax.set_xticks(range(len(CHECKS))); ax.set_xticklabels(CHECKS, rotation=40, ha='right', fontsize=8)
    lab = [f"{m}{' *' if MU.MUTANTS[m][3] else ''}  {MU.MUTANTS[m][1][:46]}" for m in M]
    ax.set_yticks(range(len(M))); ax.set_yticklabels(lab, fontsize=7)
    for i, m in enumerate(M):
        for j, c in enumerate(CHECKS):
            if A[i, j]:
                ax.text(j, i, 'x', ha='center', va='center', fontsize=8, color='#123')
    s0 = sum(any(K[(m, c)][0] for c in S0) for m in M); s1 = sum(any(K[(m, c)][0] for c in CHECKS) for m in M)
    ax.set_title(f'Seeded faults caught: pairs check alone {s0}/{len(M)}, full suite {s1}/{len(M)}  (* = a real past mistake)',
                 fontsize=8.5, loc='left')
    plt.tight_layout()
    os.makedirs(os.path.join(ROOT, 'figures'), exist_ok=True)
    p = os.path.join(ROOT, 'figures', 'mutation.png'); plt.savefig(p, dpi=200); plt.close(fig); print('wrote', p)


if __name__ == '__main__':
    main()
