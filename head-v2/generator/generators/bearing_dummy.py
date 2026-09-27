"""A printable stand-in for the 6704, so the head can be assembled and tested before the real
bearings arrive. It is a plain bushing, not a bearing: the ball will turn stiffly and it will
wear, which is fine for checking fits and travel. Do not leave it in.

    python bearing_dummy.py
"""
import os, struct
import numpy as np
import tree_parts_b as B

OD, ID, W, N = 27.0, 20.0, B.BRG_W, 96      # OD 0.1 under the seat; ID matches the 19.9 hub/axle
OUT = os.path.join(B.OUT, 'test-parts')
os.makedirs(OUT, exist_ok=True)

a = np.linspace(0, 2*np.pi, N, endpoint=False)
co, si = np.cos(a), np.sin(a)
ro, ri = OD/2, ID/2
tris = []
for i in range(N):
    j = (i+1) % N
    O0, O1 = (ro*co[i], ro*si[i]), (ro*co[j], ro*si[j])
    I0, I1 = (ri*co[i], ri*si[i]), (ri*co[j], ri*si[j])
    for (P, Q) in ((O0, O1), (I1, I0)):                     # outer wall, inner wall (flipped)
        tris += [[(P[0],P[1],0), (Q[0],Q[1],0), (Q[0],Q[1],W)],
                 [(P[0],P[1],0), (Q[0],Q[1],W), (P[0],P[1],W)]]
    tris += [[(I0[0],I0[1],0), (O0[0],O0[1],0), (O1[0],O1[1],0)],   # bottom annulus
             [(I0[0],I0[1],0), (O1[0],O1[1],0), (I1[0],I1[1],0)]]
    tris += [[(O0[0],O0[1],W), (I0[0],I0[1],W), (I1[0],I1[1],W)],   # top annulus
             [(O0[0],O0[1],W), (I1[0],I1[1],W), (O1[0],O1[1],W)]]

f = os.path.join(OUT, 'bearing_dummy.stl')
with open(f, 'wb') as fh:
    fh.write(b'\0'*80); fh.write(struct.pack('<I', len(tris)))
    for t in tris:
        n = np.cross(np.subtract(t[1], t[0]), np.subtract(t[2], t[0]))
        n = n/np.linalg.norm(n) if np.linalg.norm(n) else n
        fh.write(struct.pack('<3f', *n))
        for v in t:
            fh.write(struct.pack('<3f', *v))
        fh.write(b'\0\0')
print('wrote %s  --  OD %.1f x ID %.1f x %.1f, %d triangles' % (f, OD, ID, W, len(tris)))
print('print 2. Seat is r %.2f, so OD %.1f is a %.2f mm slip -- size up if it rattles.' % (B.BRG_OD/2, OD, B.BRG_OD-OD))
