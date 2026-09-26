"""Exact OCC solids for the servo, the camera and the parts; volume of overlap between any two."""
import os, sys
import numpy as np
import config
from config import GEN
import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut, BRepAlgoAPI_Fuse
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Pnt, gp_Ax2, gp_Dir, gp_Trsf, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.STEPControl import STEPControl_Reader
from occ_load import load, vol
import tree_parts as A, tree_parts_b as B

CAM_STEP = os.path.join(config.CAMERA, 'camera_dummy.step')

def bx(p0, p1):
    p0, p1 = np.minimum(p0, p1), np.maximum(p0, p1)
    return BRepPrimAPI_MakeBox(gp_Pnt(*map(float, p0)), gp_Pnt(*map(float, p1))).Shape()

def cyl(axis, c, r, a0, a1):
    """cylinder along 'x'|'y'|'z'; c = the other two coords in (x,y,z) order with the axis one ignored"""
    a0, a1 = min(a0, a1), max(a0, a1)
    if axis == 'x': o, d = (a0, c[0], c[1]), (1, 0, 0)
    elif axis == 'y': o, d = (c[0], a0, c[1]), (0, 1, 0)
    else: o, d = (c[0], c[1], a0), (0, 0, 1)
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(*map(float, o)), gp_Dir(*map(float, d))), float(r), float(a1 - a0)).Shape()

def fuse(*s):
    out = s[0]
    for t in s[1:]:
        out = BRepAlgoAPI_Fuse(out, t).Shape()
    return out

def cut(a, *s):
    for t in s:
        a = BRepAlgoAPI_Cut(a, t).Shape()
    return a

def common(a, b):
    return BRepAlgoAPI_Common(a, b).Shape()

def overlap(a, b):
    return vol(common(a, b))

def moved(s, dx=0, dy=0, dz=0):
    t = gp_Trsf(); t.SetTranslation(gp_Vec(float(dx), float(dy), float(dz)))
    return BRepBuilderAPI_Transform(s, t, True).Shape()

def rotated_y(s, deg, cx=0.0, cz=B.H):
    """tilt: rotate about the tilt axis (parallel to Y through X cx, Z cz); + = lens up"""
    from OCP.gp import gp_Ax1
    t = gp_Trsf(); t.SetRotation(gp_Ax1(gp_Pnt(cx, 0, cz), gp_Dir(0, -1, 0)), np.radians(deg))
    return BRepBuilderAPI_Transform(s, t, True).Shape()

# ---- the servo, datasheet outline (A.*), MEASURED stack (B.*), turned 90 deg: long axis X
SW, SL, S2S = A.SERVO_W, A.SERVO_L, A.SHAFT_TO_END
X0, X1 = -(SL - S2S), S2S                        # -16.9 .. 5.9
XC = (X0 + X1) / 2
def servo(top=21.24, spline_r=2.4, ears=True, front_ear=True, parts=False):
    y0 = top - (B.SERVO_Y1 - B.SERVO_Y0)          # 23.5 tall case
    body = bx((X0, y0, B.H - SW / 2), (X1, top, B.H + SW / 2))
    ty0, ty1 = top - A.TAB_FROM_TOP, top - A.TAB_FROM_TOP + B.TAB_T
    ear_r = bx((XC - A.TAB_SPAN / 2, ty0, B.H - SW / 2), (X0, ty1, B.H + SW / 2))
    ear_f = bx((X1, ty0, B.H - SW / 2), (XC + A.TAB_SPAN / 2, ty1, B.H + SW / 2))
    boss = cyl('y', (0, B.H), 3.45, top, top + B.BOSS_H)
    spline = cyl('y', (0, B.H), spline_r, top + B.BOSS_H, top + B.SPLINE_STACK)
    d = dict(body=body, ear_rear=ear_r, ear_front=ear_f, boss=boss, spline=spline)
    if parts:
        return d
    keep = [body, boss, spline] + ([ear_r] if ears else []) + ([ear_f] if ears and front_ear else [])
    return fuse(*keep)

def camera(dx=0.0):
    r = STEPControl_Reader(); r.ReadFile(CAM_STEP); r.TransferRoots(); s = r.OneShape()
    return moved(s, dx=dx) if dx else s

_cache = {}
def part(name, path=None):
    """one of Zach's parts as an exact solid (see config.ZACH), or any STL by path; cached"""
    key = path or name
    if key not in _cache:
        _cache[key] = load(path or config.zach(name))[0]
    return _cache[key]

from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
def prism_y(pts_xz, y0, y1):
    poly = BRepBuilderAPI_MakePolygon()
    for x, z in pts_xz:
        poly.Add(gp_Pnt(float(x), float(y0), float(z)))
    poly.Close()
    face = BRepBuilderAPI_MakeFace(poly.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0, float(y1 - y0), 0)).Shape()

# The two tab trims Zach would make with flush cutters -- modelled so the checks see the servo he
# will actually install. Rear tab: both outer corners off, SNIP_X along the edge x SNIP_Z up the end.
# Front tab: FRONT_TRIM off the end.
SNIP_X, SNIP_Z, FRONT_TRIM = 2.0, 1.5, 0.6
def servo_trimmed(top=21.24, spline_r=2.4):
    d = servo(top, spline_r, parts=True)
    ty0, ty1 = top - A.TAB_FROM_TOP - 1, top - A.TAB_FROM_TOP + B.TAB_T + 1
    xe = XC - A.TAB_SPAN / 2                                 # rear tab end
    zl, zh = B.H - SW / 2, B.H + SW / 2
    snips = [prism_y([(xe - 1, zl - 1), (xe + SNIP_X, zl - 1), (xe + SNIP_X, zl), (xe, zl + SNIP_Z), (xe - 1, zl + SNIP_Z)], ty0, ty1),
             prism_y([(xe - 1, zh + 1), (xe + SNIP_X, zh + 1), (xe + SNIP_X, zh), (xe, zh - SNIP_Z), (xe - 1, zh - SNIP_Z)], ty0, ty1)]
    ear_r = cut(d['ear_rear'], *snips)
    xf = XC + A.TAB_SPAN / 2
    ear_f = cut(d['ear_front'], bx((xf - FRONT_TRIM, ty0, zl - 1), (xf + 1, ty1, zh + 1)))
    d.update(ear_rear=ear_r, ear_front=ear_f)
    return d
