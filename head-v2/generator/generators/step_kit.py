"""A CSG kit over OpenCascade that mirrors the SDF kit in tree_parts.py, primitive for primitive.

The point: tree_parts_b.py's non-organic parts are pure constructive solid geometry over
analytic primitives -- sphere, cylinder, box, rounded box, half-space. Nothing but `fork`
and `roots` uses a smooth-min blend. So those parts do not have to be MESHED at all. They
can be rebuilt as real boundary representation (BREP) solids -- a sphere stays a sphere,
a bore stays a cylinder -- and written to STEP, which Fusion opens as a solid body with no
Convert Mesh step in between.

Every helper here takes the SAME arguments as its SDF twin, so a part written against this
kit reads line for line like the one in tree_parts_b.py. The difference is that `U` fuses
instead of taking a minimum, and a cut is `.cut()` instead of `np.maximum(s, -d)`.

    from step_kit import *
    s = U(cyl_y(0, H, 7.7, 26.0, 32.4), rcyl_y(0, H, 17.5, 32.2, 34.0, 0.6))
    s = cut(s, cyl_y(0, H, 1.1, 31.2, 35.0))
"""
import cadquery as cq
from cadquery import Vector

BIG = 1e3          # stands in for an infinite half-space; every part here is < 100 mm


# ------------------------------------------------------------------ primitives
def box(lo, hi):
    """Axis-aligned box, same (lo, hi) corners as the SDF box()."""
    return cq.Solid.makeBox(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], Vector(*lo))


def rbox(lo, hi, r):
    """Box with every edge rounded to radius r -- the SDF rbox(), which shrinks by r and
    offsets back out by r. Same solid, reached the other way round."""
    return fillet_all(box(lo, hi), r)


def _cylinder(r, p0, direction, length):
    return cq.Solid.makeCylinder(r, length, Vector(*p0), Vector(*direction))


def cyl_x(y, z, r, x0, x1):
    return _cylinder(r, (x0, y, z), (1, 0, 0), x1 - x0)


def cyl_y(x, z, r, y0, y1):
    return _cylinder(r, (x, y0, z), (0, 1, 0), y1 - y0)


def cyl_z(x, y, r, z0, z1):
    return _cylinder(r, (x, y, z0), (0, 0, 1), z1 - z0)


def sphere(r, c=(0, 0, 0)):
    return cq.Solid.makeSphere(r, Vector(*c), angleDegrees1=-90, angleDegrees2=90,
                               angleDegrees3=360)


def rcyl_y(x, z, r, y0, y1, rnd):
    """Cylinder along Y with both circular end edges rounded to `rnd`.

    This is the SDF's `_cyl(hypot(..) - (r - rnd), abs(..) - (L/2 - rnd)) - rnd`, which is a
    cylinder of radius (r - rnd) and half-length (L/2 - rnd) offset outward by rnd -- i.e. the
    full radius r, the full length, and a rnd fillet where the wall meets each flat.
    """
    return fillet_all(cyl_y(x, z, r, y0, y1), rnd, circles_only=True)


# ------------------------------------------------------------------ half-spaces
# The SDF writes a half-space as a bare linear expression; here it has to be a finite box
# big enough to swallow the part. `keep_*` intersects, and passing one to cut() removes it.
def slab(axis, lo=-BIG, hi=BIG):
    """A slab bounded on `axis` (0=X, 1=Y, 2=Z) and effectively infinite on the other two."""
    a, b = [-BIG] * 3, [BIG] * 3
    a[axis], b[axis] = lo, hi
    return box(a, b)


def half_y_plus():
    return slab(1, 0.0, BIG)


def half_y_minus():
    return slab(1, -BIG, 0.0)


# ------------------------------------------------------------------ booleans
def U(*solids):
    """Union -- the SDF's U()/np.minimum."""
    out = solids[0]
    for s in solids[1:]:
        out = out.fuse(s)
    return clean(out)


def I(*solids):
    """Intersection -- the SDF's np.maximum of two positive distances."""
    out = solids[0]
    for s in solids[1:]:
        out = out.intersect(s)
    return clean(out)


def cut(s, *tools):
    """Subtraction -- the SDF's np.maximum(s, -U(*tools))."""
    for t in tools:
        s = s.cut(t)
    return clean(s)


def clean(s):
    """Merge the coplanar/cocylindrical face fragments a boolean leaves behind.

    This matters more than it looks: without it a STEP can carry a flat as six tangent
    patches, and Fusion then shows six faces where there is one surface.
    """
    try:
        return s.clean()
    except Exception:
        return s


# ------------------------------------------------------------------ fillets
def fillet_all(solid, r, circles_only=False):
    """Fillet every edge (or only the circular ones) at radius r, degrading gracefully.

    OCC will refuse a fillet that eats more than the wall it sits in. Several of these parts
    are deliberately close to that line -- the horn pocket is 2.1 mm across the Y with a
    1.0 mm round on it -- so a refusal is shrunk and retried rather than raised. The caller
    gets told through `fillet_all.last`, and the part still comes out a valid solid.
    """
    edges = solid.Edges()
    if circles_only:
        edges = [e for e in edges if e.geomType() == 'CIRCLE']
    if not edges:
        fillet_all.last = 'no edges'
        return solid
    for scale in (1.0, 0.75, 0.5, 0.25):
        try:
            out = solid.fillet(r * scale, edges)
            fillet_all.last = 'ok' if scale == 1.0 else 'reduced to %.2f' % (r * scale)
            return out
        except Exception:
            continue
    fillet_all.last = 'FAILED -- left sharp'
    return solid


fillet_all.last = 'ok'
