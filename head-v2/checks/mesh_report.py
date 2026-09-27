"""The generator's mesh report on every print mesh and every object in the 3MF plate. Control: Zach's
own exports, which carry self-intersections and non-manifold edges."""
import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tools')))
import config
import glob, re, zipfile
import numpy as np
import tree_parts as TP_
from export import health
from record import record

def faults(msg):
    si = int(re.search(r'self-int=(\d+)', msg).group(1))
    return ('%d self-int' % si if si else '') + (' + non-manifold' if 'manifold=False' in msg else '')

all_ok = True
print('PRINT SET (%s)' % config.PRINT)
for p in sorted(glob.glob(os.path.join(config.PRINT, '*.stl'))):
    ok, msg = health(p); all_ok &= ok
    print('  %-26s %s%s' % (os.path.basename(p), msg, '' if ok else '  <-- CHECK'))
xml = ''
for plate in ('plate_ball_post_pins.3mf', 'plate_full_camposts.3mf'):       # rev 2 (superseded) and with the camera posts
    plate = os.path.join(config.PRINT, plate)
    if not os.path.exists(plate):
        all_ok = False
        print('  (no %s yet: run head-v2/fixes/build_all.py)' % os.path.basename(plate))
        continue
    xml += zipfile.ZipFile(plate).read('3D/3dmodel.model').decode()
for m in re.finditer(r'<object id="(\d+)" type="model" name="([^"]+)"><mesh><vertices>(.*?)</vertices><triangles>(.*?)</triangles>', xml):
    V = np.array(re.findall(r'x="([-\d.]+)" y="([-\d.]+)" z="([-\d.]+)"', m.group(3)), float)
    F = np.array(re.findall(r'v1="(\d+)" v2="(\d+)" v3="(\d+)"', m.group(4)), int)
    with TP_.quiet():
        ok, msg = TP_.report(TP_.mesh_set(V, F))
    all_ok &= ok
    print('  3MF %-22s %s%s' % (m.group(2), msg, '' if ok else '  <-- CHECK'))
print('\nZACH\'S EXPORTS (%s)' % config.FUSION)
yours = {}
for nm in config.ZACH:
    ok, msg = health(config.zach(nm)); yours[nm] = msg
    print('  %-26s %s' % (nm, msg))
record('print_meshes', (all_ok, faults(yours['ball_plus'])))
