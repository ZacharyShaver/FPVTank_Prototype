"""Read/write OCC shapes and STLs, and the mesh checks every export gets: health() is the generator's
own report (watertight, manifold, bodies, self-intersections); tidy() is the needle-triangle repair."""
import numpy as np
from OCP.BRepTools import BRepTools
from OCP.BRep import BRep_Builder
from OCP.TopoDS import TopoDS_Shape
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
import pymeshlab as ml
import config
import tree_parts as TP_

def rd(p):
    s = TopoDS_Shape(); BRepTools.Read_s(s, p, BRep_Builder()); return s

def wr(shape, p):
    BRepTools.Write_s(shape, p)

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
