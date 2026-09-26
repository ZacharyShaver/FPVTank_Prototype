"""Both ball halves against the nest through the whole tilt range: rev 2, and Zach's originals as the
control. Exact: the nest's own SDF from the generator, at points on each half's surface (see
lens_nest.nest_sweep for the zero-thickness sheet it steps around)."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
from probe import load_stl
from lens_nest import nest_sweep
from record import record
deep = {'snap': 0.0, 'yours': 0.0}
for nm, fixed in (('ball_plus', 'BODY_NUMBA1_snap.stl'), ('ball_minus', 'ball_minus_revised_snap.stl')):
    for lab, path in (('snap', config.out(fixed)), ('yours', config.zach(nm))):
        near, d = nest_sweep(load_stl(path))
        deep[lab] = max(deep[lab], d)
        print('%-10s %-5s nearest nest surface %.3f mm   deepest point inside the nest %.4f mm' % (nm, lab, near, d))
record('nest_deepest', (deep['snap'], deep['yours']))
