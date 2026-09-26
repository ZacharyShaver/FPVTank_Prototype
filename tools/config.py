"""Where everything lives -- the one file to edit when a path moves.

Every script starts by importing this. It puts tools/, head-v2/fixes/ and the head-v2 generator on
sys.path, so a script runs from anywhere:  python head-v2/checks/check_snap.py

Phase B moves the generator from FPVTank_Control into head-v2/generator/. Until then GEN and CAMERA
point into Control, which is READ ONLY from here: nothing may be written under it. That is why
bytecode caching is off (importing the generator would otherwise drop .pyc files in Control)."""
import os, sys

sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(TOOLS)
CONTROL = os.path.join(os.path.dirname(REPO), 'FPVTank_Control')

# The generator: tree_parts.py (variant A: servo and horn constants), tree_parts_b.py (variant B:
# the frame, the nest SDF B.fork, bearing and servo-stack numbers) and tree_parts.report (the mesh
# health report). CAMERA holds camera_dummy.step/.stl, which the generator builds.
# Phase B: GEN = os.path.join(REPO, 'head-v2', 'generator'), CAMERA = wherever camera/ lands.
GEN = os.path.join(CONTROL, 'docs', 'chassis', 'head-v2', 'generators')
CAMERA = os.path.join(CONTROL, 'docs', 'chassis', 'head-v2', 'camera')

# Zach's Fusion export the fixes apply to. His model is the source of truth; a new revision gets a
# new folder next to this one, and FUSION moves to it.
FUSION = os.path.join(REPO, 'head-v2', 'fusion', 'rev1-2026-09-24')
ZACH = {'ball_plus': 'BODY_NUMBA1 (1) (1).stl',
        'ball_minus': 'ball_minus_revised.stl',
        'post': 'ball_servo_post_revised.stl'}

# Everything the fixes write. Untracked: regenerate it, don't commit it.
OUT = os.path.join(REPO, 'head-v2', 'out')
PRINT = os.path.join(OUT, 'print')
FIXES = os.path.join(REPO, 'head-v2', 'fixes')


def zach(name):
    """path of one of Zach's parts: 'ball_plus', 'ball_minus' or 'post'"""
    return os.path.join(FUSION, ZACH[name])


def out(*parts):
    """a path under head-v2/out/, creating the folder"""
    p = os.path.join(OUT, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


if not os.path.isfile(os.path.join(GEN, 'tree_parts_b.py')):
    raise SystemExit('tools/config.py: no generator at %s -- if phase B moved it, update GEN and CAMERA' % GEN)
for _p in (FIXES, GEN, TOOLS):
    if _p not in sys.path:
        sys.path.insert(0, _p)
