"""Workstream E: the PLA ball's restitution on the drop-test floor, from a slow-motion video.

    python research/tumble/measure_ball.py VIDEO   -> research/results/ball_restitution.json and .md

The 40 mm ball (models/ball_pla_40.stl, printed like the bodies: 2 walls, 10% infill) is dropped by hand in front of
a black board, filmed side-on from floor level at 240 fps. A ball can't land tilted and rock, which is what spoiled
the E3 measurement (PROTOCOL.md, post hoc 5). Steps:
1. Find the drops: per frame at 480 px wide, the lowest bright row over the board. A drop is 6 frames in a row
   falling, 25+ rows in all.
2. Track the ball at full resolution: the lowest bright blob (grey > 150, over 4000 px). Its centre is the
   brightness-weighted centroid of the blob grown by 12 px. Motion blur spreads the ball equally up and down, so this
   centroid isn't biased by it. The plain blob centroid is kept as a check.
3. Fit each drop as one ballistic path: the free fall, then the arcs between impacts, sharing one gravity and one
   floor level (the centre's height at contact). Impact times are free parameters. Frames within 4.5 ms of an impact
   are left out (they may contain the contact). Restitution needs no length scale: a rebound's take-off speed is
   g x (its duration) / 2, so the first impact's is that over the fall's speed at impact, and each later one is the
   ratio of successive arc durations.
Each frame's own timestamp is used (the file averages 239.5 fps, not 240).
Checks per drop: gravity in px/s^2, turned into mm by the ball's width (40 mm), within 15% of 9.81 m/s^2 (the width
is measured on the lit part of the ball, so it reads a few percent small and gravity a few percent large); fit
residual under 2 px rms. test_measure_ball.py checks the fit on synthetic drops of known restitution.
"""
import os, sys, json, subprocess
import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
D_MM = 40.0
CW, CH = 480, 270          # the coarse pass's frame size
GREY = 150                 # the ball over the black board (board ~35, wood ~100, ball ~220)


def timestamps(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'packet=pts_time', '-of', 'csv=p=0', path],
                         capture_output=True, text=True).stdout
    return np.sort(np.array([float(s.strip(',')) for s in out.split()]))


def coarse(path):
    """per frame: board columns x0, x1, the board's base row, and the lowest bright row over the board (480x270)"""
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'scale={CW}:{CH}', '-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         stdout=subprocess.PIPE, bufsize=CW * CH * 3 * 8)
    rows = []
    while True:
        raw = p.stdout.read(CW * CH * 3)
        if len(raw) < CW * CH * 3: break
        g = np.frombuffer(raw, np.uint8).reshape(CH, CW, 3).mean(-1)
        dark = np.nonzero(np.median(g[20:180], 0) < 70)[0]
        if len(dark) < 50:
            rows.append((np.nan,) * 4); continue
        x0, x1 = dark.min() + 4, dark.max() - 4
        prof = np.median(g[:, x0:x1], 1)
        base = next((r for r in range(150, CH - 1) if prof[r] > 70 and prof[r - 1] <= 70), np.nan)
        lit = np.nonzero((g[:, x0:x1] > 140).sum(1)[:int(base) + 25 if np.isfinite(base) else CH] >= 3)[0]
        rows.append((x0, x1, base, lit.max() if len(lit) else np.nan))
    p.wait()
    return np.array(rows, float)


def find_drops(C):
    y = C[:, 3]; k = 0; out = []
    while k < len(y) - 10:
        d = np.diff(y[k:k + 6])
        if np.all(np.isfinite(d)) and np.all(d > 1.0):
            j = k
            while j < len(y) - 1 and np.isfinite(y[j + 1]) and y[j + 1] >= y[j] - 0.5: j += 1
            if y[j] - y[k] > 25 and not (out and k - out[-1] < 120): out.append(k)   # a re-fall after a bounce isn't a drop
            k = j + 1
        else:
            k += 1
    return out


def track(path, k, pts, C, fw=1920, fh=1080):
    """full-resolution track of the ball for frames k-30 .. k+330: t, cy (weighted), cy (blob), cx, width"""
    k0, k1 = k - 30, min(k + 330, len(pts))
    x0 = int(max(0, C[k, 0] * fw / CW - 8)); x1 = int(min(fw, C[k, 1] * fw / CW + 8)); h = int(min(fh, np.nanmedian(C[k0:k1, 2]) * fh / CH + 80))
    w = (x1 - x0) // 2 * 2
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{pts[k0] - 0.001:.4f}', '-i', path, '-frames:v', str(k1 - k0),
                          '-vf', f'crop={w}:{h}:{x0}:0,format=gray', '-vsync', '0', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    out = []
    for j in range(k1 - k0):
        raw = p.stdout.read(w * h)
        if len(raw) < w * h: break
        g = np.frombuffer(raw, np.uint8).reshape(h, w).astype(np.float32)
        lab, n = ndi.label(g > GREY); best = None
        if n:
            areas = ndi.sum(np.ones_like(g), lab, range(1, n + 1)); sl = ndi.find_objects(lab)
            for i, a in enumerate(areas):
                if a >= 4000 and (best is None or sl[i][0].stop > sl[best][0].stop): best = i
        if best is None:
            out.append((pts[k0 + j],) + (np.nan,) * 4); continue
        ys = sl[best][0]; m = lab == best + 1; rr, cc = np.nonzero(m)
        g0, g1 = max(0, ys.start - 14), min(h, ys.stop + 14)
        wgt = np.clip(g[g0:g1] - 50, 0, None) * ndi.binary_dilation(m[g0:g1], iterations=12)
        cyw = g0 + (wgt.sum(1) * np.arange(g1 - g0)).sum() / wgt.sum()
        out.append((pts[k0 + j], cyw, rr.mean(), cc.mean() + x0, m[ys].sum(1).max()))
    p.stdout.close(); p.wait()
    return np.array(out, float)


def model(p, t, n):
    """y (down) of the ball's centre: free fall into impact 1, then ballistic arcs between impacts 1..n"""
    yf, g, v1 = p[:3]; ti = p[3:3 + n]
    y = np.full_like(t, np.nan)
    m = t < ti[0]; y[m] = yf + v1 * (t[m] - ti[0]) + g / 2 * (t[m] - ti[0]) ** 2
    for i in range(n - 1):
        m = (t >= ti[i]) & (t < ti[i + 1]); y[m] = yf - g / 2 * (t[m] - ti[i]) * (ti[i + 1] - t[m])
    return y


def fit_track(t, y):
    """the joint fit of one drop. Returns g (px/s^2), the fall's impact speed v1 (px/s), the impact times, the
    restitution of each impact and the speed it was at (px/s), rms residual (px), frames used"""
    ok = np.isfinite(y); hold = np.nanmedian(y[:15])
    i0 = np.nonzero(ok & (y > hold + 30))[0][0]                         # 30 px below the hand: clear of the fingers
    yfl = np.nanmax(y[i0:i0 + 120])
    dd = np.full(len(y), np.nan); dd[1:-1] = y[2:] - 2 * y[1:-1] + y[:-2]  # free flight: +g dt^2 (~0.6 px); an impact: far below 0
    imp = []
    for i in range(i0 + 2, len(y) - 2):
        if ok[i] and dd[i] < -2.0 and y[i] > yfl - 40 and y[i] > y[i - 2] + 1.5:   # it came down into it: not noise at rest
            if imp and i - imp[-1] <= 2:
                if dd[i] < dd[imp[-1]]: imp[-1] = i
            else:
                imp.append(i)
    keep = [imp[0]]
    for b in imp[1:]:
        gap = b - keep[-1]
        if gap < 6 or (len(keep) > 1 and gap > 1.1 * (keep[-1] - keep[-2])): break   # arcs only shrink; stop at the hand
        if not np.nanmin(y[keep[-1]:b + 1]) < min(y[keep[-1]], y[b]) - 3: break     # an arc rises 3+ px: not noise at rest
        keep.append(b)
    n = len(keep); sel = np.arange(i0, keep[-1] + 1); tt, yy = t[sel], y[sel]; okk = np.isfinite(yy)
    p = np.r_[yfl, 3.6e4, (yfl - y[keep[0] - 4]) / (t[keep[0]] - t[keep[0] - 4]), t[keep]]
    for _ in range(3):                                                   # refit as the impact times settle
        use = okk & (np.min(np.abs(tt[:, None] - p[None, 3:]), 1) >= 0.0045) & (tt < p[-1])
        r = least_squares(lambda q: model(q, tt[use], n) - yy[use], p, x_scale='jac'); p = r.x
    yf, g, v1 = p[:3]; ti = p[3:]
    up = [g * (ti[i + 1] - ti[i]) / 2 for i in range(n - 1)]; vin = [v1] + up[:-1]
    return dict(g_px=float(g), v1_px=float(v1), floor_px=float(yf), t_impacts=[float(x) for x in ti], e=[float(u / v) for u, v in zip(up, vin)],
                v_in_px=[float(v) for v in vin], rms_px=float(np.sqrt(np.mean(r.fun ** 2))), frames=int(use.sum()), i0=int(i0), last=int(keep[-1]))


if __name__ == '__main__':
    path = sys.argv[1]; name = os.path.basename(path)
    pts = timestamps(path); C = coarse(path); drops = find_drops(C)
    print(f'{name}: {len(pts)} frames, {len(drops)} drops at', ', '.join(f'{pts[k]:.2f}' for k in drops), 's', flush=True)
    R = []
    for k in drops:
        T = track(path, k, pts, C); t = T[:, 0]
        f = fit_track(t, T[:, 1]); f2 = fit_track(t, T[:, 2])
        width = float(np.nanmedian(T[f['i0']:f['last'] + 1, 4])); mmpx = D_MM / width; s = 9.81 / f['g_px']   # m/s per px/s, by gravity
        r = dict(t_video=round(float(pts[k]), 2), release_mm=round(f['v1_px'] ** 2 / (2 * f['g_px']) * s * 1000, 1),
                 impacts=[dict(v_in=round(v * s, 2), e=round(e, 3)) for v, e in zip(f['v_in_px'], f['e'])],
                 e_blob_centroid=round(f2['e'][0], 3), g_by_ball_width=round(f['g_px'] * mmpx / 1000, 2), ball_width_px=round(width, 1),
                 rms_px=round(f['rms_px'], 2), frames=f['frames'])
        r['valid'] = bool(abs(r['g_by_ball_width'] / 9.81 - 1) < 0.15 and r['rms_px'] < 2.0)
        R.append(r)
        print(f"{r['t_video']:6.2f} s  from {r['release_mm']:5.1f} mm  e1 {r['impacts'][0]['e']:.3f} at {r['impacts'][0]['v_in']:.2f} m/s"
              f"  (blob centroid {r['e_blob_centroid']:.3f}); later: " + ' '.join(f"{i['e']:.2f}@{i['v_in']:.2f}" for i in r['impacts'][1:])
              + f"  g {r['g_by_ball_width']} m/s2, rms {r['rms_px']} px" + ('' if r['valid'] else '  -> left out'), flush=True)
    e1 = np.array([r['impacts'][0]['e'] for r in R if r['valid']])
    boot = np.random.default_rng(0).choice(e1, (10000, len(e1))).mean(1)
    later = [i for r in R if r['valid'] for i in r['impacts'][1:]]
    S = dict(n=len(e1), mean=round(float(e1.mean()), 3), median=round(float(np.median(e1)), 3), sd=round(float(e1.std(ddof=1)), 3),
             range=[float(e1.min()), float(e1.max())], mean_ci95=[round(float(x), 3) for x in np.percentile(boot, [2.5, 97.5])],
             v_in_range=[min(r['impacts'][0]['v_in'] for r in R), max(r['impacts'][0]['v_in'] for r in R)],
             later_bounces=dict(n=len(later), median=round(float(np.median([i['e'] for i in later])), 3) if later else None,
                                v_in_range=[min(i['v_in'] for i in later), max(i['v_in'] for i in later)] if later else None))
    json.dump(dict(video=name, summary=S, drops=R), open(os.path.join(ROOT, 'results', 'ball_restitution.json'), 'w'), indent=1)
    L = [f'# The PLA ball\'s restitution on the drop-test floor ({name})', '',
         f"{S['n']} drops by hand from {min(r['release_mm'] for r in R):.0f}-{max(r['release_mm'] for r in R):.0f} mm, impact at "
         f"{S['v_in_range'][0]}-{S['v_in_range'][1]} m/s. `tumble/measure_ball.py`.", '',
         f"**First impact: restitution {S['mean']} mean (95% CI {S['mean_ci95'][0]}-{S['mean_ci95'][1]}), median {S['median']}, "
         f"sd {S['sd']}, range {S['range'][0]}-{S['range'][1]}.**", '',
         f"Later, slower bounces ({S['later_bounces']['v_in_range'][0]}-{S['later_bounces']['v_in_range'][1]} m/s): median "
         f"{S['later_bounces']['median']} over {S['later_bounces']['n']}.", '',
         '| video time (s) | release (mm) | impact speed (m/s) | restitution | blob-centroid check | later bounces (e @ m/s) | gravity by ball width (m/s^2) | rms (px) |',
         '|---|---|---|---|---|---|---|---|']
    for r in R:
        i0 = r['impacts'][0]
        L.append(f"| {r['t_video']} | {r['release_mm']} | {i0['v_in']} | {i0['e']} | {r['e_blob_centroid']} | "
                 + (', '.join(f"{i['e']:.2f} @ {i['v_in']:.2f}" for i in r['impacts'][1:]) or '-') + f" | {r['g_by_ball_width']} | {r['rms_px']} |")
    open(os.path.join(ROOT, 'results', 'ball_restitution.md'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('\n'.join(L[:8]))
