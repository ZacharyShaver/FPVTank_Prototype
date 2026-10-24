"""Integrity audit of the check library: is every check still checkable, and is every escape traced to a check?

    python checks/audit.py             # audit checks/registry.csv against the logs and the harness results
    python checks/audit.py --control   # plant one bad entry of each kind; every one must be flagged

Reads checks/registry.csv, research/data/{iterations,iterations_live,check_failures}.csv and the mutation harness's
research/results/mutation_summary.json and mutation_matrix.csv. Edits nothing.

Severity:
  BLOCK  the check can't run as registered (missing runner or function): the gate must read BLOCKED, never pass
  FLAG   rot: an active check with no control, no origin, or no kill; a dangling id; a retirement with no reason;
         an escape that no check or check-failure row cites
  INFO   unscored (never mutation-tested) and redundant (no unique kill) checks; worth knowing, not wrong

Exits 1 on any BLOCK, or any FLAG on an active check. The control exits 1 if any planted entry goes unflagged.
"""
import os, sys, csv, json, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA, RES = os.path.join(ROOT, 'research', 'data'), os.path.join(ROOT, 'research', 'results')
STATUSES = {'proposed', 'active', 'legacy', 'watch', 'broken', 'dormant', 'superseded', 'retired'}
ID = re.compile(r'^[PELCM]\d+$')


def rows(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def load():
    findings = rows(os.path.join(DATA, 'iterations.csv')) + rows(os.path.join(DATA, 'iterations_live.csv'))
    failures = rows(os.path.join(DATA, 'check_failures.csv'))
    matrix = [r for r in rows(os.path.join(RES, 'mutation_matrix.csv')) if r['mutant'] != 'none']
    kills = json.load(open(os.path.join(RES, 'mutation_summary.json')))['kills_per_check']
    checks = [c for c in matrix[0] if c in kills]
    unique = {c: [r['mutant'] for r in matrix if r[c] == '1' and sum(r[k] == '1' for k in checks) == 1] for c in checks}
    return dict(registry=rows(os.path.join(ROOT, 'checks', 'registry.csv')), findings=findings, failures=failures,
                kills=kills, unique=unique, mutants={r['mutant'] for r in matrix})


def runner_ok(runner):
    path, _, fn = runner.partition('::')
    full = os.path.join(ROOT, path)
    if not os.path.isfile(full):
        return f'runner file missing: {path}'
    if fn and not re.search(rf'^def {re.escape(fn)}\(', open(full, encoding='utf-8').read(), re.M):
        return f'function {fn} not in {path}'
    return ''


def audit(L):
    out = []                                                    # (severity, check or finding id, message)
    known = {r['id'] for r in L['findings']} | {r['id'] for r in L['failures']} | L['mutants']
    cited = set()
    for k in L['registry']:
        i, st = k['id'], k['status']
        born = [b.strip() for b in k['born_from'].split(';') if b.strip()]
        cited |= set(born)
        if st not in STATUSES:
            out.append(('FLAG', i, f'unknown status {st!r}'))
        if st in ('superseded', 'retired'):
            if not k['notes'].strip():
                out.append(('FLAG', i, f'{st} with no reason in notes'))
            continue
        bad = runner_ok(k['runner'])
        if bad:
            out.append(('BLOCK', i, bad))
        if k['control'].strip().lower() in ('', 'none'):
            out.append(('FLAG', i, 'no negative control'))
        for b in born:
            if not ID.match(b) or b not in known:
                out.append(('FLAG', i, f'born_from {b} is not in the logs or the mutant set'))
        hk = k['harness_key']
        if hk:
            if L['kills'].get(hk, 0) == 0:
                out.append(('FLAG', i, f'vacuous: kills no mutant ({hk})'))
            elif not L['unique'].get(hk):
                out.append(('INFO', i, f'redundant: no unique kill ({L["kills"][hk]} kills, all shared)'))
        elif st in ('active', 'legacy', 'watch'):
            out.append(('INFO', i, 'unscored: never run against mutants'))
        if st == 'active' and not born:
            out.append(('FLAG', i, 'active with no born_from'))
    fail_text = ' '.join(' '.join(r.values()) for r in L['failures'])
    for r in L['failures']:
        if r['id'] not in cited:
            out.append(('FLAG', r['id'], 'check failure not cited by any registry check'))
    for r in L['findings']:
        if r['check_had_passed'].strip().lower().startswith('yes') and r['id'] not in cited \
                and not re.search(rf'\b{r["id"]}\b', fail_text):
            out.append(('FLAG', r['id'], 'escape past a passing check, cited by no check and no check-failure row'))
    return out


def report(out, registry):
    status = {k['id']: k['status'] for k in registry}
    for sev in ('BLOCK', 'FLAG', 'INFO'):
        hits = [o for o in out if o[0] == sev]
        print(f'{sev} ({len(hits)})')
        for _, i, msg in hits:
            print(f'  {i:5s} {status.get(i, ""):8s} {msg}')
    n = {s: sum(k['status'] == s for k in registry) for s in sorted(STATUSES)}
    print('statuses:', ', '.join(f'{s} {c}' for s, c in n.items() if c))
    return any(o[0] == 'BLOCK' or (o[0] == 'FLAG' and status.get(o[1]) == 'active') for o in out)


def control(L):
    """Plant one bad entry of each kind into a copy of the real inputs; each must come back flagged."""
    base = dict(id='', name='planted', **{'class': 'invariant'}, claim='x', scope='pan coil',
                runner='head-v2/generator/generators/pan_coil_b_check.py::main', control='a broken copy',
                born_from='C04', harness_key='', status='active', status_since='2026-10-24', notes='')
    plant = {'X1': (dict(control='none'), 'no negative control'),
             'X2': (dict(runner='head-v2/checks/gone.py'), 'runner file missing'),
             'X3': (dict(runner='head-v2/generator/generators/pan_coil_b_check.py::gone'), 'function gone not in'),
             'X4': (dict(born_from='P99'), 'born_from P99'),
             'X5': (dict(status='retired'), 'retired with no reason'),
             'X6': (dict(harness_key='planted_vacuous'), 'vacuous'),
             'P98': (None, 'escape past a passing check')}
    L = dict(L, registry=L['registry'] + [dict(base, id=i, **d) for i, (d, _) in plant.items() if d is not None],
             kills=dict(L['kills'], planted_vacuous=0),
             findings=L['findings'] + [dict(id='P98', check_had_passed='yes', finding='planted')])
    out = audit(L)
    missed = [i for i, (_, msg) in plant.items() if not any(o[1] == i and msg in o[2] for o in out)]
    print(f'control: {len(plant) - len(missed)} of {len(plant)} planted faults flagged' + (f'; MISSED {missed}' if missed else ''))
    return bool(missed)


if __name__ == '__main__':
    L = load()
    sys.exit(1 if (control(L) if '--control' in sys.argv else report(audit(L), L['registry'])) else 0)
