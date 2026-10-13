"""Where everything lives -- the one file to edit when a path moves.

Every script starts by importing this. It puts tools/, head-v2/fixes/ and the head-v2 generator on
sys.path, so a script runs from anywhere:  python head-v2/checks/check_snap.py

The generator lives in head-v2/generator/ (moved from FPVTank_Control in phase B, 2026-09-27). Its
scripts find their output folders by relative paths (generators/../tree-parts-b), so the tree moved
whole. Bytecode caching stays off so no .pyc files land beside the generator."""
import os, sys

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)

# The generator: tree_parts.py (variant A: servo and horn constants), tree_parts_b.py (variant B:
# the frame, the nest SDF B.fork, bearing and servo-stack numbers) and tree_parts.report (the mesh
# health report). CAMERA holds camera_dummy.step/.stl, which the generator builds.
GEN = os.path.join(REPO, 'head-v2', 'generator', 'generators')
CAMERA = os.path.join(REPO, 'head-v2', 'generator', 'camera')

# Zach's Fusion export the fixes apply to. His model is the source of truth; a new revision gets a
# new folder next to this one. FUSION stays on rev 1 because build_all.py and the rev-1 regression rows
# rebuild from it. His rev 2 (2026-09-27, fusion/rev2-2026-09-27/) already has those fixes booleaned in;
# its scripts read it directly (fixes/campost_rev2.py: BALL_PLUS, BALL_MINUS).
FUSION = os.path.join(REPO, 'head-v2', 'fusion', 'rev1-2026-09-24')
ZACH = {'ball_plus': 'BODY_NUMBA1 (1) (1).stl',
        'ball_minus': 'ball_minus_revised.stl',
        'post': 'ball_servo_post_revised.stl'}

# Everything the fixes write. Untracked: regenerate it, don't commit it.
OUT = os.path.join(REPO, 'head-v2', 'out')
PRINT = os.path.join(OUT, 'print')
FIXES = os.path.join(REPO, 'head-v2', 'fixes')


# Zach's Creality K2 Pro: its stock Moonraker (Klipper's HTTP API), on his LAN, no login. tools/k2.py
# drives it. The address is what Creality Print found (deviceInfo.json); a DHCP change moves it.
PRINTER = 'http://192.0.2.12:7125'


def zach(name):
    """path of one of Zach's parts: 'ball_plus', 'ball_minus' or 'post'"""
    return os.path.join(FUSION, ZACH[name])


def out(*parts):
    """a path under head-v2/out/, creating the folder"""
    p = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


if not os.path.isfile(os.path.join(GEN, 'tree_parts_b.py')):
    raise SystemExit('tools/config.py: no generator at %s' % GEN)
for _p in (FIXES, GEN, TOOLS):
    if _p not in sys.path:
        sys.path.insert(0, _p)
