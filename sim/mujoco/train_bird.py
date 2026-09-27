"""Train the bird predictor: from the last 12 sightings (0.4 s), predict where the bird will be over the
next 0.5 s. Writes out/bird_predictor.npz (plain numpy weights) and out/bird_training.png.

    python sim/mujoco/train_bird.py          # ~2 min on the RTX 5070

The data is made by flight.py: thousands of birds, seen at 30 frames a second with jitter and missed
frames. The test birds are flown separately (a different random seed) and never trained on. The
network has to beat both hand-made predictors on them: "hold" (today's tracker) and "line" (constant
velocity, with the look-back picked to suit it best).
"""
import os, sys, time
import numpy as np
import torch
import flight as F

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')


def miss_deg(pred, y, ref_el):
    """how far off each prediction is, as a real angle (deg), per horizon: (B, H)"""
    H = len(F.HORIZONS)
    daz, dee = (pred[:, :H] - y[:, :H]) * 10, (pred[:, H:] - y[:, H:]) * 10
    return np.hypot(daz * np.cos(np.radians(ref_el))[:, None], dee)


def main():
    t0 = time.time()
    rng = np.random.default_rng(0)
    print('flying the training birds...')
    X, Y, E = F.make_data(2000, 40, rng)
    Xt, Yt, Et = F.make_data(500, 40, np.random.default_rng(12345))       # test birds, never trained on
    print('  %d training examples, %d test examples (%.0f s)' % (len(X), len(Xt), time.time() - t0))

    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    torch.manual_seed(0)
    net = torch.nn.Sequential(torch.nn.Linear(X.shape[1], 256), torch.nn.ReLU(),
                              torch.nn.Linear(256, 256), torch.nn.ReLU(),
                              torch.nn.Linear(256, Y.shape[1])).to(dev)
    Xg, Yg = torch.tensor(X, device=dev), torch.tensor(Y, device=dev)
    cg = torch.tensor(np.cos(np.radians(E)), device=dev, dtype=torch.float32)[:, None]
    H = len(F.HORIZONS)
    epochs, bs = 25, 4096
    opt = torch.optim.AdamW(net.parameters(), lr=2e-3, weight_decay=1e-5)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=2e-3, total_steps=epochs * (len(X) // bs + 1))
    print('training on', dev)
    losses = []
    for ep in range(epochs):
        perm = torch.randperm(len(X), device=dev)
        tot = 0.0
        for i in range(0, len(X), bs):
            b = perm[i:i + bs]
            p = net(Xg[b]); e = p - Yg[b]
            loss = ((e[:, :H] * cg[b]) ** 2 + e[:, H:] ** 2).mean()      # miss as a real angle
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            tot += loss.item() * len(b)
        losses.append(tot / len(X))
        if ep % 5 == 4 or ep == epochs - 1:
            print('  epoch %2d  mean squared miss %.4f' % (ep + 1, losses[-1]))

    W = {}
    lin = [l for l in net if isinstance(l, torch.nn.Linear)]
    for i, l in enumerate(lin):
        W['W%d' % i] = l.weight.detach().cpu().numpy().T.astype(np.float32)
        W['b%d' % i] = l.bias.detach().cpu().numpy().astype(np.float32)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'bird_predictor.npz')
    np.savez(path, **W)

    # ---- the test: the numpy copy (what the sim and a Pi would run) against the hand-made ones
    learned = F.Learned(path)
    best_k, best = None, 1e9
    for k in range(2, F.N_HIST + 1):                     # give "line" its best look-back
        m = miss_deg(F.predict_line(Xt, k), Yt, Et)[:, 3].mean()
        if m < best:
            best, best_k = m, k
    rows = [('hold (today)', F.predict_hold(Xt)), ('line, last %d sightings' % best_k, F.predict_line(Xt, best_k)),
            ('learned', learned(Xt))]
    show = [2, 3, 4, 6, 10]
    print('\nTEST BIRDS: mean miss in degrees, predicting ahead of the newest frame')
    print('  %-24s' % '' + ''.join('%8.0f ms' % (F.HORIZONS[i] * 1000) for i in show))
    res = {}
    for name, p in rows:
        md = miss_deg(p, Yt, Et); res[name] = md.mean(0)
        print('  %-24s' % name + ''.join('%11.2f' % md[:, i].mean() for i in show))
    ok = res['learned'][3] < res[rows[1][0]][3] < res['hold (today)'][3]
    print('check: learned beats line beats hold at 150 ms:', 'OK' if ok else 'NO')

    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for (name, _), c in zip(rows, ('#b0413e', '#6b7a8f', '#2a9d8f')):
        ax[0].plot(F.HORIZONS * 1000, res[name], 'o-', color=c, label=name)
    ax[0].set_xlabel('how far ahead (ms after the newest camera frame)'); ax[0].set_ylabel('mean miss (deg)')
    ax[0].set_title('Predicting the test birds'); ax[0].legend(); ax[0].grid(alpha=0.3)
    # one test bird, 3 s: where it went, and what each predictor said 150 ms ahead
    ax[1].set_title('One bird, predicted 150 ms ahead (azimuth)')
    fl = F.Flight(1, np.random.default_rng(7)); dt = 1 / 120; az_true, preds = [], {n: [] for n, _ in rows}
    hist = []
    for i in range(int(6 / dt)):
        fl.step(dt)
        if i % 4 == 0:
            a, e = F.direction(fl.pos()[0]); rn = np.random.default_rng(i)
            hist.append((a + rn.normal(0, 0.6), e + rn.normal(0, 0.6)))
            hist = hist[-F.N_HIST:]
            if len(hist) == F.N_HIST:
                h = np.array(hist)
                x, ra, re = F.features(h[None, :, 0], h[None, :, 1], np.ones((1, F.N_HIST), bool))
                for (n, _), fn in zip(rows, (F.predict_hold, lambda x: F.predict_line(x, best_k), learned)):
                    preds[n].append((fl.t + 0.15, ra[0] + fn(x)[0, 3] * 10))
        az_true.append((fl.t, F.direction(fl.p[0])[0]))
    az_true = np.array(az_true)
    ax[1].plot(az_true[:, 0], np.degrees(np.unwrap(np.radians(az_true[:, 1]))), 'k-', lw=2, label='the bird')
    for (n, _), c in zip(rows, ('#b0413e', '#6b7a8f', '#2a9d8f')):
        p = np.array(preds[n]); ax[1].plot(p[:, 0], np.degrees(np.unwrap(np.radians(p[:, 1]))), '.', color=c, ms=4, label=n)
    ax[1].set_xlim(2, 5); ax[1].set_xlabel('time (s)'); ax[1].set_ylabel('azimuth (deg)'); ax[1].legend(); ax[1].grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, 'bird_training.png'), dpi=110)
    print('wrote', path, 'and out/bird_training.png (%.0f s)' % (time.time() - t0))
    return ok


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
