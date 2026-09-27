import os, sys, json, base64, struct
import numpy as np
D = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(D, 'ball2.py'), encoding='utf-8-sig').read().split("size = 900")[0]
exec(src)

# regroup the concept by what moves: fixed / pan / tilt (tilt also pans)
parts = []
def add(name, group, cut, mesh, color, pod=False):
    parts.append(dict(name=name, group=group, cut=cut, mesh=mesh, color=color, pod=pod))
for b in [box(-60, -20, -55, 55, -3, 0), box(-20, -9, -55, -9, -3, 0), box(9, 12, -55, -9, -3, 0), box(-9, 9, -55, -14.5, -3, 0),
          box(-20, 12, 9, 55, -3, 0), box(12, FRONT, -55, 55, -3, 0)]:
    add('deck', 'fixed', 'both', b, col['deck'])
add('pan servo', 'fixed', 'both', box(-16.9, 5.9, -6.1, 6.1, P_ - 24.3, P_ - 1.8), col['servo'])
add('pedestal', 'fixed', 'both', cyl(0, 0, 0, 18, 'z', 0, P_), col['struct'], pod=True)
add('slide ring', 'fixed', 'both', cyl(0, 0, 0, 17, 'z', P_, P_ + 0.5), col['bearing'])
for sgn in (-1, 1):
    add('IR headlight', 'fixed', 'both', box(FRONT - 8, FRONT, sgn * 42 - 6, sgn * 42 + 6, 0, 10), col['deck'])
    add('IR lens', 'fixed', 'both', cyl(0, sgn * 42, 5, 4.5, 'x', FRONT, FRONT + 1), col['ir'])
add('turntable hub', 'pan', 'both', cyl(0, 0, 0, 20, 'z', P_ + 0.5, TT), col['struct'])
add('turntable bar', 'pan', 'both', box(-11, 11, BP1, SP1, P_ + 0.5, TT), col['struct'])
add('servo pod stem', 'pan', 'full', box(-10, 10, SP0, SP1, TT, H), col['struct'], pod=True)
add('servo pod', 'pan', 'full', cyl(0, 0, H, 20, 'y', SP0, SP1), col['struct'], pod=True)
add('bearing pod stem', 'pan', 'both', box(-10, 10, BP1, BP0, TT, H), col['struct'], pod=True)
add('bearing pod', 'pan', 'both', cyl(0, 0, H, 20, 'y', BP1, BP0), col['struct'], pod=True)
add('6704 bearing', 'pan', 'both', cyl(0, 0, H, 13.5, 'y', BP0 - 4.0, BP0 + 0.3), col['bearing'])
for m, c in ribbon_pod_parts():
    add('ribbon', 'pan', 'both', m, c)
full = camera_parts('all'); half = camera_parts('minusY')
inner = ['camera board', 'IR-cut holder', 'lens barrel', 'light sensor', 'ribbon', 'ribbon', 'ribbon', 'ribbon']
def label(lst, i, extra):
    if i < len(inner): return inner[i]
    k = i - (len(lst) - len(extra))
    return extra[k] if k >= 0 else 'post'
for i, (m, c) in enumerate(half):
    add(label(half, i, ['hollow hub', 'ball half-shell']), 'tilt', 'half', m, c)
for i, (m, c) in enumerate(full):
    add(label(full, i, ['hollow hub', 'ball', 'seam groove', 'lens bezel', 'lens', 'sensor window', 'servo horn']), 'tilt', 'full', m, c)

# three.js is Y-up: (x, y, z)_robot -> (x, z, -y)
out = []
for p in parts:
    M = p['mesh'].reshape(-1, 3)
    T = np.c_[M[:, 0], M[:, 2], -M[:, 1]].astype(np.float32)
    out.append(dict(n=p['name'], g=p['group'], c=p['cut'], pod=p['pod'], col='#%02x%02x%02x' % tuple(int(v) for v in p['color']),
                    b=base64.b64encode(T.tobytes()).decode()))
meta = dict(H=float(H), R=float(R), board=BOARD, pitch=PITCH, holder=HOLDER_H, width=float(SP1 - BP1), deckFront=FRONT, pod=POD)
with open(os.path.join(D, 'ball_parts.js'), 'w') as f:
    f.write('window.BALL_META=' + json.dumps(meta) + ';\nwindow.BALL_PARTS=' + json.dumps(out) + ';\n')

def write_stl(path, tris):
    with open(path, 'wb') as f:
        f.write(b'Scorpion ball-head concept'.ljust(80, b' ')); f.write(struct.pack('<I', len(tris)))
        for t in tris:
            n = np.cross(t[1] - t[0], t[2] - t[0]); ln = np.linalg.norm(n); n = n / ln if ln else n
            f.write(struct.pack('<12fH', *n, *t[0], *t[1], *t[2], 0))
os.makedirs(os.path.join(D, 'stl'), exist_ok=True)
for grp in ('fixed', 'pan', 'tilt'):
    tris = np.concatenate([p['mesh'] for p in parts if p['group'] == grp and p['cut'] in ('both', 'full')])
    write_stl(os.path.join(D, 'stl', f'ball_concept_{grp}.stl'), tris)
    print(grp, len(tris), 'tris')
print('js bytes', os.path.getsize(os.path.join(D, 'ball_parts.js')), 'parts', len(parts), 'H', round(H, 2), 'OD', round(2 * R, 2), 'width', SP1 - BP1)
