"""Zach's Fusion rev -> the whole hand-off in head-v2/out/, in order. Stops at the first failure.
Then run head-v2/checks/regression.py."""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    'build_snap.py',     # rev 2 halves (BREP)
    'post3.py',          # post v3 (BREP)
    'export_snap.py',    # meshes in Zach's frame, pins, test block + mesh report
    'fusion_step.py',    # named ADD_/CUT_ tool bodies for Fusion (STEP)
    'print_export.py',   # print-oriented STLs in out/print/
    'plate3mf.py',       # needle repair on those, the 3MF plate, mesh report
    'figure_snap.py',    # picture sheets
    'figure_stop.py',
    'figure_post.py',
]

if __name__ == '__main__':
    t0 = time.time()
    for s in STEPS:
        t = time.time()
        print('== %s' % s, flush=True)
        if subprocess.call([sys.executable, os.path.join(HERE, s)]) != 0:
            sys.exit('%s failed' % s)
        print('   (%.0f s)' % (time.time() - t), flush=True)
    print('all done in %.0f s' % (time.time() - t0))
