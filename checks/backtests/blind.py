"""Build a blind sandbox for an adversary backtest (checks/README.md, R11): the pan coil generator and its checks as
they stood at set 7, with every trace of later history removed, so an agent can be tested on an escape whose answer
is already known.

    python checks/backtests/blind.py <sandbox> [brief.md]   # build, grep for leaks, verify the checks

All on the syntax tree, never by hand:
  - fold the flags of sets 8 to 11 to their set 7 values and delete the code they guard; set 7's own constants back;
  - drop the checks and the parts set 7 did not have;
  - delete every comment and docstring (today's comments state the answers), blank any string that names later
    history, and prune every definition nothing uses any more.
Then two checks, each with its control:
  - leaks: a grep for later history must find nothing in the sandbox, and must find plenty in the sources;
  - the checks: set 7 as built must pass all five, and their negative control must fail all five.
"""
import os, sys, re, ast, shutil, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GEN = os.path.join(ROOT, 'head-v2', 'generator', 'generators')
OPS = os.path.join(ROOT, 'research', 'harness', 'mutants.py')
RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'run_checks.py')

FOLD = dict(SCREW_THRU=False, SEAT_SQUARE=False, STRAIGHT_WIRE=False, BARREL_688=False, HORN_GEAR=False,
            HORN_SDF_POCKET=True, HOLLOW_AXIS=False, SHELF_MERGED=False,             # sets 8-11, as set 7 had them
            CONE=True, NOTCH=True, SPLINE_GEAR=True)          # sets 5-6: no check toggles them, so their dead code goes
SET7 = dict(SCREW_L=8.0, SQ_H=3.5)                                                  # constants later sets changed
LATER_PARTS = {'bearing688', 'horn', 'bearing6704'}
LATER_CHECKS = {'block_air', 'screw_threads', 'screw_threads_6704', 'races_688', 'races_6704', 'wire_axis',
                'merged_shelf', 'screw_alignment'}
NO_CONTROL = {'insertion'}      # its `broken` flag is unused in the live suite too (found 2026-10-24; registry K02)
LEAK = re.compile(r'6704|(?<![\d.])688(?!\d)|horn|hollow|merged|upside|fall(s|ing)? out|square|straight'
                  r'|set ?(8|9|10|11)\b|2026-10-(0[5-9]|[123]\d)', re.I)


class Fold(ast.NodeTransformer):
    """Replace flags (bare, or as P.FLAG) by constants and fold the expressions and branches they decide."""
    def __init__(self, c):
        self.c = c

    def visit_Name(self, n):
        return ast.copy_location(ast.Constant(self.c[n.id]), n) if isinstance(n.ctx, ast.Load) and n.id in self.c else n

    def visit_Attribute(self, n):
        self.generic_visit(n)
        if isinstance(n.ctx, ast.Load) and isinstance(n.value, ast.Name) and n.value.id == 'P' and n.attr in self.c:
            return ast.copy_location(ast.Constant(self.c[n.attr]), n)
        return n

    def visit_UnaryOp(self, n):
        self.generic_visit(n)
        return ast.Constant(not n.operand.value) if isinstance(n.op, ast.Not) and isinstance(n.operand, ast.Constant) else n

    def visit_BoolOp(self, n):
        self.generic_visit(n)
        decisive = isinstance(n.op, ast.Or)               # Or is decided by a true constant, And by a false one
        if any(isinstance(v, ast.Constant) and bool(v.value) == decisive for v in n.values):
            return ast.Constant(decisive)
        vals = [v for v in n.values if not isinstance(v, ast.Constant)]
        return vals[0] if len(vals) == 1 else (ast.Constant(not decisive) if not vals else ast.BoolOp(n.op, vals))

    def visit_IfExp(self, n):
        self.generic_visit(n)
        return (n.body if n.test.value else n.orelse) if isinstance(n.test, ast.Constant) else n

    def visit_If(self, n):
        self.generic_visit(n)
        return ((n.body if n.test.value else n.orelse) or None) if isinstance(n.test, ast.Constant) else n

    def visit_Assign(self, n):                            # the flags' own definitions go
        self.generic_visit(n)
        names = [t.id for t in n.targets if isinstance(t, ast.Name)]
        return None if names and all(x in self.c for x in names) else n


def names_in(node):
    return {x.id for x in ast.walk(node) if isinstance(x, ast.Name)}


def drop(node, gone):
    """Delete definitions named in `gone`, and every simple statement that uses one."""
    for field in ('body', 'orelse', 'finalbody'):
        lst = getattr(node, field, None)
        if not isinstance(lst, list):
            continue
        keep = []
        for s in lst:
            if isinstance(s, (ast.FunctionDef, ast.ClassDef)) and s.name in gone:
                continue
            if hasattr(s, 'body'):
                drop(s, gone)
            elif names_in(s) & gone:
                continue
            keep.append(s)
        setattr(node, field, keep or ([ast.Pass()] if field == 'body' and not isinstance(node, ast.Module) else []))


def targets(s):
    out = []
    for t in s.targets:
        if isinstance(t, ast.Name):
            out.append(t.id)
        elif isinstance(t, ast.Tuple) and all(isinstance(e, ast.Name) for e in t.elts):
            out += [e.id for e in t.elts]
        else:
            return None                                   # an attribute or item: keep it
    return out


def prune(tree, roots):
    """Remove top-level definitions and imports nothing uses, to a fixed point."""
    def base(t):                                          # X in X[k] = v or X.a = v: written, not used
        while isinstance(t, (ast.Subscript, ast.Attribute)):
            t = t.value
        return t if isinstance(t, ast.Name) else None
    while True:
        written = {id(base(t)) for s in tree.body if isinstance(s, ast.Assign) for t in s.targets if base(t) is not None}
        used = set(roots) | {x.id for x in ast.walk(tree)
                             if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and id(x) not in written}
        body, changed = [], False
        for s in tree.body:
            if isinstance(s, ast.FunctionDef) and s.name not in used:
                changed = True; continue
            if isinstance(s, ast.Assign):
                t = targets(s)
                if t is None:
                    t = [base(x).id for x in s.targets if base(x) is not None] or None
                if t is not None and not set(t) & used:
                    changed = True; continue
            if isinstance(s, ast.ImportFrom):
                n0 = len(s.names); s.names = [a for a in s.names if (a.asname or a.name) in used]
                changed |= len(s.names) != n0
                if not s.names:
                    continue
            body.append(s)
        tree.body = body
        if not changed:
            return tree


class Clean(ast.NodeTransformer):
    """No docstrings, no __main__ blocks, no string that names later history."""
    def _body(self, n):
        self.generic_visit(n)
        b = n.body
        if b and isinstance(b[0], ast.Expr) and isinstance(b[0].value, ast.Constant) and isinstance(b[0].value.value, str):
            b = b[1:]
        if isinstance(n, ast.Module):
            b = [s for s in b if not (isinstance(s, ast.If) and '__main__' in ast.unparse(s.test))]
        n.body = b or [ast.Pass()]
        return n
    visit_Module = visit_FunctionDef = visit_ClassDef = _body

    def visit_Constant(self, n):
        return ast.Constant('') if isinstance(n.value, str) and LEAK.search(n.value) else n


def attrs(tree, mod):
    return {x.attr for x in ast.walk(tree) if isinstance(x, ast.Attribute) and isinstance(x.value, ast.Name) and x.value.id == mod}


def build(out):
    src = lambda p: ast.parse(open(p, encoding='utf-8').read())
    fold = Fold(FOLD)
    # the checks: set 7's five, and their helpers
    chk = fold.visit(src(os.path.join(GEN, 'pan_coil_b_check.py')))
    drop(chk, LATER_CHECKS)
    chk = Clean().visit(prune(chk, {'main', 'insertion', 'assembly', 'gear_play', 'bearing_races', 'shift_servo', 'at_pan',
                                    'overlap', 'PAIRS', 'PANS', 'ROTATES', 'STEP'}))
    # the fault operators, without the historical mutant table
    ops = fold.visit(src(OPS))
    ops.body = [s for s in ops.body if not (isinstance(s, ast.Assign) and targets(s) == ['MUTANTS'])]
    ops = Clean().visit(ops)
    runner = src(RUNNER)
    # the generator: set 7's flags and constants, set 7's parts, and only what the checks and operators reach
    gen = src(os.path.join(GEN, 'pan_coil_b.py'))
    for s in gen.body:
        if isinstance(s, ast.Assign) and targets(s) and len(targets(s)) == 1 and targets(s)[0] in SET7:
            s.value = ast.Constant(SET7[targets(s)[0]])
        if isinstance(s, ast.Assign) and targets(s) == ['PARTS']:
            d = s.value
            keep = [i for i, k in enumerate(d.keys) if not (isinstance(k, ast.Constant) and k.value in LATER_PARTS)]
            d.keys, d.values = [d.keys[i] for i in keep], [d.values[i] for i in keep]
    gen = fold.visit(gen)
    gen = Clean().visit(gen)
    gen = prune(gen, {'PARTS'} | attrs(chk, 'P') | attrs(ops, 'P') | attrs(runner, 'P'))
    # tree_parts: only what the generator imports from it
    tp = src(os.path.join(GEN, 'tree_parts.py'))
    imported = {a.name for s in gen.body if isinstance(s, ast.ImportFrom) and s.module == 'tree_parts' for a in s.names}
    tp = prune(Clean().visit(tp), imported | attrs(gen, 'A'))
    os.makedirs(out, exist_ok=True)
    for name, tree in (('pan_coil_b.py', gen), ('pan_coil_b_check.py', chk), ('operators.py', ops), ('tree_parts.py', tp)):
        open(os.path.join(out, name), 'w', encoding='utf-8').write(ast.unparse(ast.fix_missing_locations(tree)) + '\n')
    shutil.copy(RUNNER, os.path.join(out, 'run_checks.py'))


def leaks(out, brief):
    """The grep, and its control: the sources must be full of what the sandbox must not contain."""
    bad = {}
    for f in sorted(os.listdir(out)) + ([brief] if brief else []):
        p = f if os.path.isabs(f) else os.path.join(out, f)
        if p.endswith(('.py', '.md')):
            hits = sorted({m.group(0) for m in LEAK.finditer(open(p, encoding='utf-8').read())})
            if hits:
                bad[os.path.basename(p)] = hits
    ctrl = {os.path.basename(p): len(LEAK.findall(open(p, encoding='utf-8').read()))
            for p in (os.path.join(GEN, 'pan_coil_b.py'), os.path.join(GEN, 'pan_coil_b_check.py'), OPS)}
    print('leaks in the sandbox:', bad or 'none')
    print('control, the same grep on the sources:', ctrl, '' if all(ctrl.values()) else '<== CONTROL READS NOTHING')
    return not bad and all(ctrl.values())


if __name__ == '__main__':
    out = os.path.abspath(sys.argv[1]); brief = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else None
    build(out)
    if brief:
        shutil.copy(brief, os.path.join(out, 'BRIEF.md'))
    ok = leaks(out, brief)
    for flag in ([], ['--control']):
        print(f'\n$ python run_checks.py {" ".join(flag)}', flush=True)
        r = subprocess.run([sys.executable, 'run_checks.py'] + flag, cwd=out, capture_output=True, text=True)
        print(r.stdout + r.stderr[-2000:])
        miss = [l.split()[0] for l in r.stdout.splitlines() if '<== expected' in l]
        ok &= r.returncode == 0 and not [c for c in miss if not (flag and c in NO_CONTROL)]
    print('sandbox', 'READY' if ok else 'NOT READY')
    sys.exit(0 if ok else 1)
