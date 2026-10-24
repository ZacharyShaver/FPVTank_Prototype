"""Adversary's own probes of the set 7 geometry (reads the design, edits nothing)."""
import numpy as np
import pan_coil_b as P


def pt(r, deg, z):
    a = np.radians(deg)
    return (np.array(r * np.cos(a), float), np.array(r * np.sin(a), float), np.array(z, float))


def radial_profile(fn, deg, r0, r1, z, n=2000):
    r = np.linspace(r0, r1, n)
    v = fn(pt(r, deg, np.full_like(r, z)))
    inside = v < 0
    # spans of solid
    spans, start = [], None
    for i, s in enumerate(inside):
        if s and start is None:
            start = r[i]
        if not s and start is not None:
            spans.append((round(start, 2), round(r[i - 1], 2)))
            start = None
    if start is not None:
        spans.append((round(start, 2), round(r[-1], 2)))
    return spans


def vertical_profile(fn, deg, r, z0, z1, n=2000):
    z = np.linspace(z0, z1, n)
    v = fn(pt(np.full_like(z, r), deg, z))
    inside = v < 0
    spans, start = [], None
    for i, s in enumerate(inside):
        if s and start is None:
            start = z[i]
        if not s and start is not None:
            spans.append((round(start, 2), round(z[i - 1], 2)))
            start = None
    if start is not None:
        spans.append((round(start, 2), round(z[-1], 2)))
    return spans


if __name__ == '__main__':
    print('constants: SKIRT_IR', P.SKIRT_IR, 'RING_OR', P.RING_OR, 'RING_IR', P.RING_IR, 'LANE_Z1', P.LANE_Z1,
          'LANE_Z0', P.LANE_Z0, 'CH_Z0', P.CH_Z0, 'BAND', P.BAND_Z0, P.BAND_Z1, 'RI/RO', P.RI, P.RO)
    for deg in (0, 30, -60, -90, -145):
        print(f'\n== angle {deg} ==')
        for z in (-21.0, -20.4, -19.0, -10.0, -1.0, -0.45):
            print(f'  z {z:6.2f}  well {radial_profile(P.well, deg, 0, 34, z)}')
            print(f'           ring {radial_profile(P.shelf_ring, deg, 0, 34, z)}')
            print(f'           drum {radial_profile(P.drum, deg, 0, 34, z)}')
        for r in (12.3, 15.0, 19.3, 21.2, 21.8, 22.4, 22.58, 23.5, 25.0, 27.5):
            print(f'  r {r:5.2f}  well z {vertical_profile(P.well, deg, r, -32, 8)}')
            print(f'           ring z {vertical_profile(P.shelf_ring, deg, r, -32, 8)}')
            print(f'           drum z {vertical_profile(P.drum, deg, r, -32, 12)}')
