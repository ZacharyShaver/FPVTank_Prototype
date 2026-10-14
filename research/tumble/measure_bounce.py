"""Workstream E: measure the coefficient of restitution from a slow-motion video of flat drops.

    python research/tumble/measure_bounce.py VIDEO --drops T1 T2 ... [--roi x0 y0 x1 y1] [--sheet]
      T: a time (s) shortly before each release; --sheet writes contact sheets to find them

For each drop, the body's lowest edge is tracked frame by frame, against a background made from the video's median.
A parabola is fitted to the free fall just before the first impact, and another to the rebound arc after it.
Restitution is the rebound's upward speed at take-off over the fall's downward speed at impact. It is a ratio, so it
needs no scale. Two checks come with each drop:
  - both parabolas' curvature is gravity in pixels/s^2 and must agree (within 25%);
  - that curvature turns pixels into mm, which gives the release height; it must be within 30 mm of --height.
A drop that fails either check is reported and left out. test_measure_bounce.py checks the method on synthetic drops
of known restitution: at 240 fps it recovers 0.3-0.7 within 0.01, a no-bounce control reads ~0 and fails the
gravity check, and a very small bounce (0.13) fails the release check rather than passing with a wrong value.
"""
import os, sys, json, argparse, subprocess
import numpy as np

W = 640


def probe(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,nb_frames',
                          '-of', 'json', path], capture_output=True, text=True).stdout
    s = json.loads(out)['streams'][0]; n, d = map(float, s['r_frame_rate'].split('/'))
    return s['width'], s['height'], n / d


def frames(path, t0, t1, w, h):
    H = int(round(h * W / w / 2) * 2)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{t0:.3f}', '-to', f'{t1:.3f}', '-i', path, '-vf', f'scale={W}:{H},format=gray',
                          '-vsync', '0', '-f', 'rawvideo', '-'], stdout=subprocess.PIPE)
    raw = p.stdout.read(); p.wait()
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W)


def frames_rgb(path, t0, t1, w, h):
    H = int(round(h * W / w / 2) * 2)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', f'{t0:.3f}', '-to', f'{t1:.3f}', '-i', path, '-vf', f'scale={W}:{H}',
                          '-vsync', '0', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    raw = p.stdout.read(); p.wait()
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def lowest_edge_color(F, roi, sat=(0.21, 0.6), val=0.35, min_px=6):
    """per frame, the lowest row (in the ROI) of the print's colour: saturation 0.21-0.6 and value over 0.35 (E3 at
    the 2026-10-14 setup: the print 0.28-0.30; the wall, board and shadows 0.06-0.16; the wood floor 0.97 but dark).
    For when the body never leaves the frame, so a background can't be made without it."""
    x0, y0, x1, y1 = roi; out = []
    for f in F:
        c = f[y0:y1, x0:x1].astype(np.float32) / 255; mx = c.max(-1); mn = c.min(-1)
        s = (mx - mn) / np.maximum(mx, 1e-3); m = (s > sat[0]) & (s < sat[1]) & (mx > val)
        rows = np.nonzero(m.sum(1) >= min_px)[0]
        out.append(y0 + rows.max() if len(rows) else np.nan)
    return np.array(out, float)


def bottom_by_template(F, roi, rest_frame=-1, dx=12, up=170, down=8, th_px=44):
    """the body's height per frame by matching a template of its upper face, taken from `rest_frame` where it lies
    still (sum of squared differences on grey levels, searched up to `up` px higher and `dx` px sideways). The
    template is the band just under the body's top edge, found as the first row where the print's colour covers 20% of
    the search columns. Its lower part isn't used: there the board's foot and a lit strip of floor pass the same colour
    test. Returned is the template's bottom row plus a constant, so differences and speeds are the body's own, which is
    all restitution and the drop height need."""
    x0, y0, x1, y1 = roi
    f = F[rest_frame].astype(np.float32) / 255; mx = f.max(-1); mn = f.min(-1); s = (mx - mn) / np.maximum(mx, 1e-3)
    m = (s > 0.21) & (s < 0.6) & (mx > 0.35)
    frac = m[:, x0:x1].mean(1); rows = np.nonzero(frac[y0:y1] > 0.2)[0]
    top = y0 + int(rows.min()); band = m[top + 4:top + th_px, x0:x1].mean(0) > 0.5
    cols = np.nonzero(band)[0]; bx0, bx1 = x0 + int(cols.min()) + 4, x0 + int(cols.max()) - 4
    ty0, ty1 = top + 3, top + 3 + th_px
    G = F.astype(np.float32).mean(-1); T = G[rest_frame, ty0:ty1, bx0:bx1]; T = T - T.mean(); th, tw = T.shape
    out = []
    for g in G:
        best, by = np.inf, np.nan
        for oy in range(-up, down + 1):
            yy = ty0 + oy
            if yy < 0 or yy + th > g.shape[0]: continue
            for ox in range(-dx, dx + 1, 3):
                xx = bx0 + ox
                if xx < 0 or xx + tw > g.shape[1]: continue
                P = g[yy:yy + th, xx:xx + tw]; d = ((P - P.mean() - T) ** 2).mean()
                if d < best: best, by = d, yy + th
        out.append(by)
    return np.array(out, float), (bx0, ty0, bx1, ty1)


def lowest_edge(F, roi, thr=28):
    """per frame, the lowest row (in the ROI) where the frame differs from the background by more than thr in at
    least 4 pixels: the body's bottom while it is the lowest thing moving"""
    x0, y0, x1, y1 = roi
    bg = np.median(F[::max(1, len(F) // 60)], 0)
    out = []
    for f in F:
        dif = np.abs(f[y0:y1, x0:x1].astype(int) - bg[y0:y1, x0:x1]) > thr
        rows = np.nonzero(dif.sum(1) >= 4)[0]
        out.append(y0 + rows.max() if len(rows) else np.nan)
    return np.array(out, float)


def fit_arc(t, y):
    """y = a + b t + c t^2 (y down, pixels); returns (a, b, c)"""
    c, b, a = np.polyfit(t, y, 2); return a, b, c


def measure(t, y, still_px=1.0):
    """The first impact is where the falling edge turns back up; contact lasts under a frame at these speeds, so no
    frame need sit on the floor. The fall arc is the frames from the release to just before that turn; the rebound
    arc is the frames after it, up to the next turn. The impact instant and the floor are where the two fitted
    parabolas meet. (First version waited for a frame on the floor, and missed every impact in its synthetic test.)"""
    ok = np.isfinite(y); t, y = t[ok], y[ok]
    dy = np.diff(y)
    r0 = next((k for k in range(len(dy) - 3) if np.all(dy[k:k + 3] > still_px)), None)   # release: 3 frames falling
    if r0 is None: return None
    i = next((k for k in range(r0 + 3, len(dy)) if dy[k] < -still_px), None)              # the first turn back up
    if i is None: return None
    k1 = next((k for k in range(i + 1, len(dy)) if dy[k] > still_px and dy[k - 1] <= still_px), len(y) - 1)  # next turn down
    k2 = next((k for k in range(k1 + 1, len(dy)) if dy[k] < -still_px or abs(dy[k]) <= still_px), len(y) - 1)  # next landing
    fall, reb = slice(r0, i), slice(i + 1, k2)
    if i - r0 < 4 or k2 - (i + 1) < 4:
        return None
    a1, b1, c1 = fit_arc(t[fall], y[fall]); a2, b2, c2 = fit_arc(t[reb], y[reb])
    r = np.roots([c1 - c2, b1 - b2, a1 - a2]); r = r[np.isreal(r)].real
    if not len(r): return None
    t_imp = r[np.argmin(np.abs(r - t[i]))]
    v_in = b1 + 2 * c1 * t_imp; v_out = b2 + 2 * c2 * t_imp                    # px/s, + is down
    floor = a1 + b1 * t_imp + c1 * t_imp ** 2
    return dict(e=float(-v_out / v_in), g_fall=float(2 * c1), g_rebound=float(2 * c2), v_in=float(v_in), t_impact=float(t_imp),
                drop_px=float(floor - np.median(y[max(0, r0 - 5):r0 + 1])), frames_fall=int(i - r0), frames_air=int(k2 - i - 1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('video'); ap.add_argument('--drops', nargs='*', type=float, default=[])
    ap.add_argument('--roi', nargs=4, type=int); ap.add_argument('--window', type=float, default=1.2); ap.add_argument('--sheet', action='store_true')
    ap.add_argument('--height', type=float, default=60.0, help='intended release height, mm')
    ap.add_argument('--color', action='store_true', help='find the body by its colour, not against a background')
    ap.add_argument('--fps', type=float, help="the capture rate, when the file's differs: an iPhone 'edited' slow-motion "
                    "export (IMG_E....MOV) keeps every 240 fps frame but plays them at 30")
    a = ap.parse_args()
    w, h, fps = probe(a.video); print(f'{a.video}: {w}x{h} at {fps:.1f} fps' + (f', measured as {a.fps:.0f} fps' if a.fps else ''))
    fps = a.fps or fps
    if a.sheet:
        from PIL import Image
        F = frames(a.video, 0, 1e6, w, h); step = max(1, int(fps / 4)); idx = list(range(0, len(F), step))
        for s in range(0, len(idx), 40):
            im = Image.new('L', (8 * 160, 5 * 90), 255)
            for q, k in enumerate(idx[s:s + 40]):
                im.paste(Image.fromarray(F[k]).resize((160, 90)), ((q % 8) * 160, (q // 8) * 90))
            im.save(f'bounce_sheet_{s // 40:02d}.png')
        print('sheets every', step, 'frames written'); sys.exit()
    res = []
    for t0 in a.drops:
        F = (frames_rgb if a.color else frames)(a.video, t0, t0 + a.window, w, h); roi = a.roi or (0, 0, F.shape[2], F.shape[1])
        y = (lowest_edge_color if a.color else lowest_edge)(F, roi); t = np.arange(len(y)) / fps
        r = measure(t, y)
        if r is None:
            print(f'drop at {t0}: could not find a clean fall and rebound'); continue
        g_px = (r['g_fall'] + r['g_rebound']) / 2; mm_per_px = 9810.0 / g_px
        r.update(t0=t0, gravity_agree=bool(abs(r['g_fall'] - r['g_rebound']) / g_px < 0.25), release_mm=round(r['drop_px'] * mm_per_px, 1))
        r['valid'] = bool(r['gravity_agree'] and abs(r['release_mm'] - a.height) <= 30.0)
        res.append(r)
        print(f"drop at {t0}: restitution {r['e']:.2f}  (fall {r['frames_fall']} frames, rebound {r['frames_air']} frames in the air; "
              f"gravity fall/rebound {r['g_fall']:.0f}/{r['g_rebound']:.0f} px/s2 {'agree' if r['gravity_agree'] else 'DISAGREE'}; release ~{r['release_mm']} mm)"
              + ('' if r['valid'] else '  -> left out'))
    if res:
        e = [r['e'] for r in res if r['valid']]
        if e:
            print(f'restitution over {len(e)} clean drops: mean {np.mean(e):.2f}, sd {np.std(e, ddof=1) if len(e) > 1 else 0:.2f}, range {min(e):.2f}-{max(e):.2f}')
