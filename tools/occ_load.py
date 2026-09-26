"""Load an STL into OpenCascade as a solid: sew the triangles, make a solid, report validity."""
import time, os
from OCP.StlAPI import StlAPI_Reader
from OCP.TopoDS import TopoDS_Shape, TopoDS
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.TopAbs import TopAbs_SHELL, TopAbs_FACE, TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.ShapeFix import ShapeFix_Solid, ShapeFix_Shape
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

def vol(s):
    g = GProp_GProps(); BRepGProp.VolumeProperties_s(s, g); return g.Mass()

def count(s, kind):
    e = TopExp_Explorer(s, kind); n = 0
    while e.More(): n += 1; e.Next()
    return n

def load(path, tol=1e-4, unify=True):
    t = time.time()
    raw = TopoDS_Shape(); StlAPI_Reader().Read(raw, path)
    sew = BRepBuilderAPI_Sewing(tol); sew.Add(raw); sew.Perform()
    sh = sew.SewedShape()
    info = dict(free=sew.NbFreeEdges(), multiple=sew.NbMultipleEdges(), degenerated=sew.NbDegeneratedShapes())
    ex = TopExp_Explorer(sh, TopAbs_SHELL); shells = []
    while ex.More(): shells.append(TopoDS.Shell_s(ex.Current())); ex.Next()
    ms = BRepBuilderAPI_MakeSolid()
    for s in shells: ms.Add(s)
    solid = ms.Solid()
    fx = ShapeFix_Solid(solid); fx.Perform(); solid = fx.Solid()
    if unify:
        u = ShapeUpgrade_UnifySameDomain(solid, True, True, False); u.Build(); solid = u.Shape()
    info.update(shells=len(shells), faces=count(solid, TopAbs_FACE), valid=BRepCheck_Analyzer(solid).IsValid(),
                volume=vol(solid), secs=time.time() - t)
    return solid, info

if __name__ == '__main__':
    import config
    for nm in config.ZACH:
        s, info = load(config.zach(nm))
        print(nm, info)
