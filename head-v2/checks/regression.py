"""The regression table: run the checks, compare with the numbers rev 2 shipped with (2026-09-25).

    python head-v2/fixes/build_all.py        # first: regenerate head-v2/out/
    python head-v2/checks/regression.py      # runs the checks (minutes), prints the table
    python head-v2/checks/regression.py --table     # just re-print the table from the last run

Rev 2 = Zach's Fusion rev 1 plus the fixes, with the board on the front of his wall (X 10.5) and the
servo case top on his plate at Y 21.2357. Every 'fixed' number has its negative control beside it:
the same check on Zach's original parts (or on the first pins), which must read nonzero where noted.
Each check's full output is in head-v2/out/logs/."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import json, subprocess, time
from record import PATH

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = ['check_snap.py', 'freeplay.py', 'ball_nest.py', 'lens_clear.py', 'reach_check.py', 'check_campost.py', 'mesh_report.py']
NEEDS = ['ball_plus_snap.brep', 'ball_minus_snap.brep', 'post_v3.brep', 'BODY_NUMBA1_snap.stl',
         'ball_minus_revised_snap.stl', 'ball_servo_post_v3.stl', os.path.join('print', 'plate_ball_post_pins.3mf'),
         'ball_plus_camposts.brep', 'BODY_NUMBA1_camposts.stl', 'camera_post_lower_medium.brep', 'camera_post_upper_medium.brep',
         os.path.join('print', 'plate_full_camposts.3mf')]

def f(dp):
    def fmt(x):
        if x is None: return 'none'
        return '%.*f' % (dp, 0.0 if abs(x) < 0.5 * 10 ** -dp else x)
    return fmt

# (check, key in regression.json, how to read (fixed, control) from it, formatter, expected fixed, expected control)
ROWS = [
    ('camera vs ball_plus, mm3', 'camera_vs_ball_plus', lambda v: v, f(2), '0.00', '39.50'),
    ('camera vs servo (tabs snipped / as bought), mm3', 'camera_vs_servo', lambda v: v, f(2), '0.00', '8.65'),
    ('servo seated vs ball_plus, mm3', 'servo_seated_vs_ball_plus', lambda v: v, f(2), '0.00', '7.36'),
    ('servo sliding in, worst step, mm3', 'servo_sliding_worst', lambda v: v, f(2), '0.00', '8.61'),
    ('ball halves vs each other, mm3', 'halves_vs_each_other', lambda v: v, f(2), '0.00', '0.00'),
    ('3 pins seated in ball_plus (designed preload), mm3', 'pins_seated', lambda v: (v[0], None), f(2), '0.12', 'none'),
    ('3 pins seated in ball_minus (designed preload), mm3', 'pins_seated', lambda v: (v[1], None), f(2), '0.12', 'none'),
    ('air inside a 1.0 mm wall round every socket, mm3', 'socket_wall_air_1mm', lambda v: (v, None), f(3), '0.000', 'none'),
    ('pin free play after the click (control: first pins), mm', ('free_play_stop', 'free_play_first'), lambda v: v, f(2), 'none', '0.75'),
    ('ball vs nest, full tilt, deepest, mm', 'nest_deepest', lambda v: v, f(4), '0.0000', '0.0000'),
    ('lens vs nest, full tilt, clearance, mm', 'lens_vs_nest', lambda v: (v, None), f(2), '1.95', 'none'),
    ('post: spline in the post (v3 screw tight / yours pressed), mm', ('post_v3_screw_tight', 'post_yours_pressed'), lambda v: (v[0][0], v[1][0]), f(2), '3.50', '2.13'),
    ('post: gap to the servo boss (same), mm', ('post_v3_screw_tight', 'post_yours_pressed'), lambda v: (v[0][1], v[1][1]), f(2), '0.50', '1.87'),
    # camera snap posts, 2026-09-26 (checks/check_campost.py)
    ('camera posts: other parts vs new ball_plus (control: rev 2), mm3', 'campost_other_parts', lambda v: v, f(2), '0.00', '0.00'),
    ('camera posts seated vs ball_plus (designed preload), mm3', 'campost_seated', lambda v: (v, None), f(2), '0.03', 'none'),
    ('camera posts vs camera, mm3', 'campost_vs_camera', lambda v: (v, None), f(2), '0.00', 'none'),
    ('camera post sliding in, no barbs (control: with barbs), mm3', 'campost_slide', lambda v: v, f(3), '0.000', '0.649'),
    ('long post in the LOWER hole (control: short in upper), mm3', 'campost_swap', lambda v: v, f(2), '2.76', '0.51'),
    ('camera post heads from ball centre (control: ball R), mm', 'campost_head_r', lambda v: v, f(2), '30.50', '30.70'),
    ('camera post catch: thinnest wall to outside, mm', 'campost_catch_wall', lambda v: (v, None), f(2), '0.79', 'none'),
    ('ball_plus STEP round trip lost, sewn (control: BREP), mm3', 'campost_step_loss', lambda v: v, f(1), '0.0', '489.9'),
    ('every print mesh clean (control: ball_plus as exported)', 'print_meshes',
     lambda v: v, lambda x: x if isinstance(x, str) else ('clean' if x else 'NOT clean'), 'clean', '5 self-int + non-manifold'),
]

def table():
    with open(PATH) as fh:
        got = json.load(fh)
    print('\n%-62s %-12s %-12s   %-26s %-26s' % ('check', 'fixed', 'expected', 'control', 'expected'))
    bad = 0
    for label, key, read, fmt, e_fix, e_ctl in ROWS:
        try:
            v = [got[k] for k in key] if isinstance(key, tuple) else got[key]
            a, b = read(v)
            a, b = fmt(a), fmt(b)
        except KeyError:
            a = b = 'MISSING'
        ok = a == e_fix and b == e_ctl
        bad += not ok
        print('%-62s %-12s %-12s   %-26s %-26s %s' % (label, a, e_fix, b, e_ctl, '' if ok else '<-- DIFFERS'))
    print('\n%s' % ('all %d rows reproduce' % len(ROWS) if not bad else '%d of %d rows differ' % (bad, len(ROWS))))
    return bad

if __name__ == '__main__':
    if '--table' not in sys.argv:
        missing = [n for n in NEEDS if not os.path.exists(os.path.join(config.OUT, n))]
        if missing:
            sys.exit('missing in head-v2/out/: %s -- run head-v2/fixes/build_all.py first' % ', '.join(missing))
        if os.path.exists(PATH):
            os.remove(PATH)
        os.makedirs(os.path.join(config.OUT, 'logs'), exist_ok=True)
        for c in CHECKS:
            t = time.time()
            log = os.path.join(config.OUT, 'logs', c.replace('.py', '.txt'))
            with open(log, 'w') as fh:
                rc = subprocess.call([sys.executable, os.path.join(HERE, c)], stdout=fh, stderr=subprocess.STDOUT)
            print('%-16s %s  (%.0f s)  log: %s' % (c, 'ok' if rc == 0 else 'FAILED, exit %d' % rc, time.time() - t, log), flush=True)
    sys.exit(1 if table() else 0)
