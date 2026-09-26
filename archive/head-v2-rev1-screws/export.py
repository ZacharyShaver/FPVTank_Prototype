"""Write the fixed parts as STL (same frame as Zach's files), the tool bodies as a named STEP for
Fusion, and run the generator's own mesh health report on everything -- originals as the control."""
import os, sys
import numpy as np
from kit import *
from build import tools, OUT
from OCP.BRepTools import BRepTools
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Shape
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
import pymeshlab as ml
import tree_parts as TP_
def rd(p):
    s = TopoDS_Shape(); BRepTools.Read_s(s, p, BRep_Builder()); return s
def write_stl(shape, path, lin=0.01, ang=0.1):
    BRepMesh_IncrementalMesh(shape, lin, False, ang, True)
    w = StlAPI_Writer(); w.ASCIIMode = False; w.Write(shape, path)
def health(path):
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path)
        ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
        ok, msg = TP_.report(ms)
    return ok, msg
def tidy(path):
    """Collapse the needle triangles inherited from the original export (two vertices < 1 um apart):
    merge at 0.001 mm, drop the null faces that leaves. Returns the max surface deviation it caused."""
    with TP_.quiet():
        ms = ml.MeshSet(); ms.load_new_mesh(path)
        ms.meshing_merge_close_vertices(threshold=ml.PureValue(1e-5))
        ref = ml.Mesh(ms.current_mesh().vertex_matrix(), ms.current_mesh().face_matrix())
        ms.meshing_merge_close_vertices(threshold=ml.PureValue(0.001))
        ms.meshing_remove_null_faces(); ms.meshing_remove_duplicate_faces(); ms.meshing_remove_unreferenced_vertices()
        ms.save_current_mesh(path, binary=True)
        ms.add_mesh(ref)
        h = ms.get_hausdorff_distance(sampledmesh=1, targetmesh=0, samplevert=True, sampleface=True, samplenum=300000)
    return h['max']

if __name__ == '__main__':
    names = {'ball_plus': 'BODY_NUMBA1_fixed.stl', 'ball_minus': 'ball_minus_revised_fixed.stl'}
    for nm, fn in names.items():
        s = rd(os.path.join(OUT, nm + '_fixed.brep'))
        write_stl(s, os.path.join(OUT, fn))
        print('  %s: needle repair moved the surface at most %.4f mm' % (fn, tidy(os.path.join(OUT, fn))))
    print('mesh health (the generator\'s own report):')
    for f in ('BODY_NUMBA1 (1) (1).stl', 'ball_minus_revised.stl'):
        ok, msg = health(os.path.join(DL, f)); print('  yours  %-30s %s' % (f[:30], msg))
    for f in names.values():
        ok, msg = health(os.path.join(OUT, f)); print('  fixed  %-30s %s%s' % (f, msg, '' if ok else '   <-- CHECK'))
    # tool bodies, named, head frame -- File > Open or Insert into the Fusion design, then Combine
    import cadquery as cq
    asm = cq.Assembly(name='zach_rev1_fixes')
    colors = {'CUT': cq.Color(0.85, 0.2, 0.2, 0.6), 'ADD': cq.Color(0.2, 0.7, 0.3, 0.8)}
    for nm, s in tools().items():
        asm.add(cq.Workplane(obj=cq.Shape.cast(s)), name=nm, color=colors[nm[:3]])
    asm.save(os.path.join(OUT, 'fix_tools_for_fusion.step'))
    print('wrote', sorted(os.listdir(OUT)))
