"""The fixes as named tool bodies in Zach's coordinates, for Fusion (Insert the STEP into his design):
ADD_* = Join, CUT_* = Cut, *_plus_* on ball_plus, *_minus_* on ball_minus -- do the ADDs first.
snap_tools_for_fusion.step also carries the three pins seated in place (PIN_*); post_v3_tools_for_fusion.step
is the post's changes, on his post."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import cadquery as cq
import build_snap, post3

COL = {'CUT': cq.Color(0.85, 0.2, 0.2, 0.6), 'ADD': cq.Color(0.2, 0.7, 0.3, 0.8), 'PIN': cq.Color(0.2, 0.4, 0.9, 1.0)}

def save(name, bodies, path):
    asm = cq.Assembly(name=name)
    for nm, s in bodies.items():
        asm.add(cq.Workplane(obj=cq.Shape.cast(s)), name=nm, color=COL[nm[:3]])
    asm.save(path)
    print('wrote %s: %s' % (os.path.basename(path), ', '.join(bodies)))

if __name__ == '__main__':
    snap = dict(build_snap.tools())
    for i, c in enumerate(build_snap.POSTS):
        snap['PIN_%d_medium_with_stop' % (i + 1)] = build_snap.pin_seated(c)
    save('zach_rev2_snap', snap, config.out('snap_tools_for_fusion.step'))
    save('post_v3_changes', post3.tools(), config.out('post_v3_tools_for_fusion.step'))
