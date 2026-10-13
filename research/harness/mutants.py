"""Workstream C (Aim 1 pilot): seeded faults ("mutants") for the pan coil model, head-v2/generator/generators/pan_coil_b.py.

A mutant patches the model module, its part functions, its PARTS table and its constants, in a fresh process, before the
check module is imported. The checks themselves are not edited: `checks.py` calls pan_coil_b_check's functions as they
are. Each mutant copies a real mistake from this project's history (`hist`, with the record it comes from) or a
plausible one of the same kind. `expect` names the check expected to catch it; it is for reading the results only and is
never used to score them.

Fault operators: move, grow, glue (merge one part into another and delete the second), nofeat (drop a part's cuts),
dup (a stacked copy), param (change a design constant).
"""
import numpy as np


def _empty(q, features=True):
    return np.full(np.broadcast(*q).shape, 1e3)


def _set(P, name, fn, lo=None, hi=None):
    setattr(P, name, fn)
    if name in P.PARTS:
        _, lo0, hi0, step, target = P.PARTS[name]
        P.PARTS[name] = (fn, lo if lo is not None else lo0, hi if hi is not None else hi0, step, target)


def move(name, d):
    def apply(P):
        f0 = getattr(P, name); _, lo, hi, *_ = P.PARTS[name]
        _set(P, name, lambda q, features=True: f0((q[0] - d[0], q[1] - d[1], q[2] - d[2]), features),
             tuple(np.add(lo, d)), tuple(np.add(hi, d)))
    return apply


def grow(name, r):
    def apply(P):
        f0 = getattr(P, name)
        _set(P, name, lambda q, features=True: f0(q, features) - r)
    return apply


def glue(dst, src, also=()):
    """src becomes part of dst (moulded on) and stops existing as its own part"""
    def apply(P):
        for t in (dst,) + tuple(also):
            f0, fs = getattr(P, t), getattr(P, src)
            lo = np.minimum(P.PARTS[t][1], P.PARTS[src][1]); hi = np.maximum(P.PARTS[t][2], P.PARTS[src][2])
            _set(P, t, (lambda f0, fs: lambda q, features=True: np.minimum(f0(q, features), fs(q, features)))(f0, fs),
                 tuple(lo), tuple(hi))
        _set(P, src, _empty)
    return apply


def nofeat(name):
    def apply(P):
        f0 = getattr(P, name)
        _set(P, name, lambda q, features=True: f0(q, False))
    return apply


def dup(name, d):
    def apply(P):
        f0 = getattr(P, name)
        _set(P, name, lambda q, features=True: np.minimum(f0(q, features), f0((q[0] - d[0], q[1] - d[1], q[2] - d[2]), features)))
    return apply


def param(**kv):
    def apply(P):
        for k, v in kv.items():
            assert hasattr(P, k), k
            setattr(P, k, v)
        if 'SHELF_MERGED' in kv or 'INSERT' in kv:
            P.RING_PART = P.INSERT and not P.SHELF_MERGED
    return apply


def both(*ops):
    def apply(P):
        for o in ops:
            o(P)
    return apply


# id: (operator, what it does, expected catcher, historical record or None)
MUTANTS = {
    'M01': (move('servo', (2.0, 0, 0)), 'pan servo 2 mm toward the axis, into the can', 'pairs, insertion',
            '2026-09-19: the servo passed through the well; Zach saw it by eye'),
    'M02': (param(FLANGE_R=19.6), "drum's flange back to r 19.6", 'pairs', '2026-09-19: the flange ploughed 270 mm3 through the deck ring'),
    'M03': (glue('drum', 'gear_out'), 'small gear moulded onto the drum', 'assembly', '2026-09-27 set 1: could not be assembled; all seated checks read zero'),
    'M04': (glue('base', 'floor', also=('bay',)), "the gear bay's floor fused to the base (a closed box)", 'assembly', '2026-09-27 set 1'),
    'M05': (param(GEAR_GAP=0.0), 'gear pair drawn at exactly the centre distance', 'gear_play', '2026-09-27: 0.0 deg of free play'),
    'M06': (param(RELIEF_D=0.0), "deck ring's top solid under the 6809's turning inner race", 'bearing_races', '2026-09-27: the ledge ran solid under both races'),
    'M07': (param(INSERT=False), 'set 5 deck ring: the drum hub rests flush on fixed plastic', 'bearing_races',
            '2026-10-04: pan finicky; hub flush on the deck ring, zero overlap'),
    'M08': (param(B6704_LIP_R=10.0), "6704's lip reaches in under its turning inner ring", 'bearing_races', None),
    'M09': (param(AX_SCREW_L=12.0), 'gear screws M3 x 12 instead of x 16', 'screw_threads', None),
    'M10': (both(param(GIN_Z1=-31.2), param(HUMP_AIR=0.3)), "input gear 0.3 under the servo's block", 'block_air',
            '2026-10-10: the gear rubbed the block as its screw tightened'),
    'M11': (param(AX_WIRE_R=1.0), 'wire hole down the axis 2 mm across', 'wire_axis', None),
    'M12': (nofeat('gear_out'), "small gear without its wire hole and screw holes", 'wire_axis, pairs', None),
    'M13': (param(SHELF_MERGED=False), 'base regresses to set 10 (loose shelf ring, open exit hole)', 'merged_shelf', '2026-10-12'),
    'M14': (param(PASS_R=13.4), "shelf's hole smaller than the 6704 (27 mm)", 'assembly', '2026-10-11: the 6704 could not pass the shelf ring'),
    'M15': (move('drum', (0, 0, -0.6)), 'drum seated 0.6 low', 'pairs', None),
    'M16': (grow('gear_out', 0.3), "small gear's teeth 0.3 fat (printed oversize)", 'gear_play', '2026-10-10: the tight gears'),
    'M17': (grow('horn', 0.3), 'horn 0.3 larger than modelled', 'pairs', '2026-10-10: zero-offset pocket, the horn flew out'),
    'M18': (move('floor', (0, 0, 0.6)), 'floor plate 0.6 up into the gears', 'pairs', None),
    'M19': (dup('drum', (0.25, 0, 0)), 'a second copy of the drum, 0.25 off (a stacked copy)', 'pairs', '2026-10-05: stacked copies hid overlaps'),
    'M20': (move('tab_block', (0, 0.6, 0)), 'tab block 0.6 out of its grooves', 'pairs', None),
    'M21': (nofeat('bay'), "gear bay without its cuts (servo pocket, window, shaft way)", 'pairs, insertion', None),
    'M22': (param(AX_FLOOR_HOLE_R=7.0), "floor plate's middle hole too small for the gear's screw heads", 'pairs', '2026-10-11: set 9 hole vs set 10 heads'),
}
