"""One command to rebuild everything variant B hands to Fusion.

This is the front door. The individual scripts still work and still carry their own options;
this just runs them in the right order, checks the dependencies first, and refuses to report
success if a verification step failed.

    python build_b.py              # solids + blanks + feature table   (~10 min)
    python build_b.py --solids     # just the 5 STEP solids            (seconds)
    python build_b.py --check      # ... and re-run the two analytic check scripts
    python build_b.py --render     # ... and redraw step_vs_obj.png
    python build_b.py --all        # everything, checks and render included

Typical loop after a measurement lands: edit the number at the top of tree_parts_b.py, then

    python build_b.py --solids --check

which is seconds, not the 25-minute mesh build -- the five STEP parts do not go through
marching cubes at all. Only `fork` and `roots` do, and only they need the slow path.

WHAT THIS DOES NOT DO: pull changes back OUT of Fusion. Nothing here can read a .f3d. The
moment a part is edited in Fusion, that part's truth lives in Fusion and re-running this would
overwrite it. See the note at the bottom of ../tree-parts-b/step/README.md.
"""
import os, sys, subprocess, importlib

D = os.path.dirname(os.path.abspath(__file__))

# (module to import, pip name) -- import name and install name differ for two of them
DEPS = [('numpy', 'numpy'), ('skimage', 'scikit-image'), ('pymeshlab', 'pymeshlab'),
        ('cadquery', 'cadquery')]

STEPS = [
    ('solids', 'tree_parts_b_step.py', [], 'the 5 STEP solids, with verification'),
    ('blanks', 'step_mesh_prep.py', [], 'fork + roots blanks and features.md  (SLOW, ~10 min)'),
    ('check', 'tree_parts_b_check.py', [], 'interference, bezel and view cone'),
    ('check', 'tree_parts_b_driver.py', [], 'driver access per screw'),
]


def deps_ok(need_cad=True):
    missing = []
    for mod, pip in DEPS:
        if mod == 'cadquery' and not need_cad:
            continue
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pip)
    if missing:
        print('Missing: %s' % ', '.join(missing))
        print('  pip install -r %s' % os.path.join(D, 'requirements-cad.txt'))
        return False
    return True


def run(script, args):
    print('\n' + '=' * 78)
    print('>> %s %s' % (script, ' '.join(args)))
    print('=' * 78, flush=True)
    r = subprocess.run([sys.executable, script] + args, cwd=D)
    return r.returncode == 0


def render():
    """Redraw the STEP-vs-OBJ sheet. Kept here rather than as its own repo script because it
    is an eyeball aid, not part of the build."""
    try:
        from render_step_compare import main
    except ImportError:
        print('\n(no render_step_compare.py -- skipping the render)')
        return True
    return main()


if __name__ == '__main__':
    a = sys.argv[1:]
    want_all = '--all' in a or not [x for x in a if x.startswith('--')]
    do_solids = want_all or '--solids' in a
    do_blanks = want_all or '--blanks' in a
    do_check = want_all or '--check' in a
    do_render = want_all or '--render' in a
    if '--solids' in a and '--all' not in a:
        do_blanks = False

    if not deps_ok(need_cad=do_solids):
        sys.exit(1)

    failed = []
    for tag, script, args, _ in STEPS:
        if tag == 'solids' and not do_solids:
            continue
        if tag == 'blanks' and not do_blanks:
            continue
        if tag == 'check' and not do_check:
            continue
        if not os.path.exists(os.path.join(D, script)):
            print('\n(missing %s -- skipped)' % script)
            continue
        if not run(script, args):
            failed.append(script)

    if do_render and not render():
        failed.append('render')

    print('\n' + '=' * 78)
    if failed:
        print('FAILED: %s' % ', '.join(failed))
        print('Nothing downstream should be trusted until these are green.')
        sys.exit(1)
    print('All green.')
    print('Fusion imports:  ../tree-parts-b/step/*.step          (5 parts, solid bodies)')
    print('                 ../tree-parts-b/fusion-solid/*.obj   (fork + roots, convert these)')
    print('                 ../tree-parts-b/features.md          (what the blanks leave out)')
