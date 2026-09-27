"""Rebuild pan-coil-b/viewer_pan_coil_b.js from the current fusion/*.obj, without re-meshing.

pan_coil_b.py writes the bundle from the parts IT built, so `python pan_coil_b.py gear_in`
leaves a bundle containing only gear_in. Rebuilding all eight to fix one part costs ~8
minutes. This reads whatever OBJs are on disk instead. Same job as viewer_bundle_b.py does
for variant B.

    python pan_coil_b.py gear_in     # one part, ~1 min
    python pan_coil_b_bundle.py      # then put the bundle back together
"""
import os, json, base64
import pymeshlab as ml
import tree_parts as T
import pan_coil_b as P

bundle = {}
for name in P.PARTS:
    path = os.path.join(P.OUT, 'fusion', f'{name}.obj')
    if not os.path.exists(path):
        print(f'{name:<12} MISSING -- run pan_coil_b.py {name}')
        continue
    with T.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path)
    m = ms.current_mesh()
    bundle[name] = {'v': base64.b64encode(m.vertex_matrix().astype('<f4').tobytes()).decode(),
                    'f': base64.b64encode(m.face_matrix().astype('<u4').tobytes()).decode()}
    print(f'{name:<12}{m.face_number():>8} faces')
bundle['_meta'] = {'travel_deg': round(float(__import__('numpy').degrees(P.TRAVEL)), 1),
                   'L_can': P.L_CAN, 'can_od': 2 * P.WELL_OR, 'stump_depth': -P.BAY_Z0,
                   'twist_have': P.TWIST_HAVE, 'twist_need': P.TWIST_NEED,
                   'ri': round(P.RI, 2), 'ro': round(P.RO, 2), 'u_r': round(P.U_R, 2)}
out = os.path.join(P.OUT, 'viewer_pan_coil_b.js')
open(out, 'w').write('window.PANCOILB=' + json.dumps(bundle) + ';')
print(f'wrote {out}  ({os.path.getsize(out) / 1e6:.1f} MB, {len(bundle) - 1} parts)')
