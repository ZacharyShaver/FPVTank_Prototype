"""The hills' picture sheet: each design's tip limits up and down (friction x2.5) with the slide limit every design
shares on the band's slipperiest floor, and T3's limits with its tail held at each pose.

    python gauges/hills_sheet.py          -> gauges/out/search_shape/hills_sheet.png (after hills.py read and tail)
    python gauges/hills_sheet.py height   -> gauges/out/search_shape/hills_height.png (after hills.py height)
"""
import os, sys, json
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config

OUT = os.path.join(config.GAUGES_OUT, 'search_shape')
INK, INK2, GRID, SURF = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
UP, DOWN = '#2a78d6', '#eb6834'                                          # validated pair (dataviz validator, light)


def style(a):
    a.grid(axis='x', color=GRID, lw=0.6); a.tick_params(colors=INK2, labelsize=8)
    for s in ('top', 'right'):
        a.spines[s].set_visible(False)
    for s in ('left', 'bottom'):
        a.spines[s].set_color(GRID)


def main():
    rows = json.load(open(os.path.join(OUT, 'hills_read.json')))['rows']
    tail = json.load(open(os.path.join(OUT, 'hills_tail.json')))['rows']
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw=dict(width_ratios=[1.15, 1]))
    names = [r['name'] for r in rows][::-1]; y = np.arange(len(names)); by = {r['name']: r for r in rows}
    up = [by[n]['up'] for n in names]; dn = [by[n]['down'] for n in names]
    a.axvline(by[names[0]]['up_slide'], color=UP, lw=1, ls=(0, (3, 3))); a.axvline(by[names[0]]['down_slide'], color=DOWN, lw=1, ls=(0, (3, 3)))
    a.text(by[names[0]]['up_slide'], len(names) - 0.35, f"slides up at {by[names[0]]['up_slide']}°\n(x0.65 floor, every design)", color=INK2, fontsize=7, ha='right')
    a.text(by[names[0]]['down_slide'], len(names) - 0.35, f"slides down\nat {by[names[0]]['down_slide']}°", color=INK2, fontsize=7, ha='left')
    for yy, u, d in zip(y, up, dn):
        a.plot([u, d], [yy, yy], color=GRID, lw=2, zorder=1)
    a.scatter(up, y, s=70, color=UP, zorder=3, edgecolors=SURF, linewidths=2, label='drives up')
    a.scatter(dn, y, s=70, color=DOWN, zorder=3, edgecolors=SURF, linewidths=2, label='drives down')
    for yy, u, d in zip(y, up, dn):
        a.text(u - 1.2, yy, f'{u}°', color=INK2, fontsize=7.5, va='center', ha='right'); a.text(d + 1.2, yy, f'{d}°', color=INK2, fontsize=7.5, va='center')
    a.set_yticks(y, names, color=INK, fontsize=8.5); a.set_xlim(15, 60); a.set_ylim(-0.7, len(names) + 0.4); style(a)
    a.set_xlabel('steepest slope it drives, friction x2.5 (degrees): one step on, the box and Trainer stall (up) or slide (down); the rest tip', color=INK2, fontsize=8)
    a.legend(loc='lower right', fontsize=8, frameon=False)
    a.set_title('Hill limits, tail stowed', color=INK, fontsize=10, loc='left')
    poses = [r for r in tail if r['th'] is not None]; poses.sort(key=lambda r: r['th']); st = next(r for r in tail if r['th'] is None)
    th = [r['th'] for r in poses]
    b.axhline(st['up'], color=UP, lw=1, ls=(0, (3, 3))); b.axhline(st['down'], color=DOWN, lw=1, ls=(0, (3, 3)))
    b.plot(th, [r['up'] for r in poses], color=UP, lw=2, marker='o', ms=6, mec=SURF, mew=1.5)
    b.plot(th, [r['down'] for r in poses], color=DOWN, lw=2, marker='o', ms=6, mec=SURF, mew=1.5)
    b.text(th[-1] + 4, poses[-1]['up'] - 2, 'drives up', color=INK2, fontsize=8, va='center'); b.text(th[-1] + 4, poses[-1]['down'] + 1.5, 'drives down', color=INK2, fontsize=8, va='center')
    b.text(-95, st['up'] + 0.8, 'stowed', color=INK2, fontsize=7); b.text(-95, st['down'] + 0.8, 'stowed', color=INK2, fontsize=7)
    held = [r for r in poses if min(r['up'], r['down']) == max(min(q['up'], q['down']) for q in poses)]
    span = f"{held[0]['th']:.0f}°" if len(held) == 1 else f"{held[0]['th']:.0f}° to {held[-1]['th']:.0f}°"
    b.annotate(f"braced behind, {span}: {held[0]['up']}° up, {held[0]['down']}° down", (held[len(held) // 2]['th'], held[0]['up']),
               (held[0]['th'] + 40, held[0]['up'] + 6), color=INK, fontsize=8, arrowprops=dict(arrowstyle='-', color=INK2, lw=0.8))
    b.set_xlim(-100, 215); b.set_ylim(10, 58); style(b); b.grid(axis='y', color=GRID, lw=0.6)
    b.set_xlabel("tail pitch held on the hill, degrees (-90 down, 0 level behind, 90 up, 180 forward)", color=INK2, fontsize=8)
    b.set_ylabel('steepest slope, x2.5 (degrees)', color=INK2, fontsize=8)
    b.set_title("The tail's pose on the hill: T3", color=INK, fontsize=10, loc='left')
    fig.suptitle('Hills on the shape study\'s designs: 2.5 m of slope, 20 tries a slope, 5° steps, the better direction, a 1 s soft start', fontsize=10, color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.94)); path = os.path.join(OUT, 'hills_sheet.png'); fig.savefig(path, dpi=130, facecolor=SURF); print(path)


def height():
    """T3 with 1 kg at four heights: the steepest slope against the CoM's height, tail stowed and braced (the best of
    the held poses), with the static tip angle, the stowed ceiling"""
    rows = [r for r in json.load(open(os.path.join(OUT, 'hills_height.json')))['rows'] if r['name'] != 'T3']
    zs = sorted({round(r['com_z'], 1) for r in rows}); at = lambda z: [r for r in rows if round(r['com_z'], 1) == z]
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for a, g, title in ((axs[0], 'up', 'Drives up'), (axs[1], 'down', 'Drives down')):
        st = [next(r[g] for r in at(z) if r['th'] is None) for z in zs]
        br = [max(r[g] for r in at(z) if r['th'] is not None) for z in zs]
        ts = [at(z)[0]['tip_static'] for z in zs]
        a.plot(zs, ts, color=INK2, lw=1, ls=(0, (2, 2)))
        a.plot(zs, st, color=INK2, lw=2, marker='o', ms=7, mec=SURF, mew=1.5)
        a.plot(zs, br, color=UP, lw=2, marker='o', ms=7, mec=SURF, mew=1.5)
        a.text(zs[-1] + 1.5, st[-1] - 1, 'tail stowed', color=INK2, fontsize=8, va='center')
        a.text(zs[-1] + 1.5, br[-1] + 1, 'tail braced', color=INK, fontsize=8, va='center')
        for z, u, v in zip(zs, st, br):
            a.text(z, v + 1.4, f'{v}°' + (' both' if u == v else ''), color=INK, fontsize=7.5, ha='center')
            if u != v:
                a.text(z, u - 2.6, f'{u}°', color=INK2, fontsize=7.5, ha='center')
        a.set_xlim(zs[0] - 5, zs[-1] + 22); a.set_ylim(22, 56); style(a); a.grid(axis='y', color=GRID, lw=0.6)
        a.set_xlabel('centre of mass above the ground, mm (1 kg moved from the belly to the top)', color=INK2, fontsize=8)
        a.set_title(title, color=INK, fontsize=10, loc='left')
    axs[0].set_ylabel('steepest slope, friction x2.5 (degrees)', color=INK2, fontsize=8)
    axs[0].text(zs[0], 53, 'braced, it stalls (motors or grip) before it tips', color=INK2, fontsize=7.5)
    axs[1].text(zs[0], 53, "dotted: the static tip angle, the stowed ceiling", color=INK2, fontsize=7.5)
    fig.suptitle("T3 + 1 kg: the CoM's height still costs hill, the braced tail softens it (15° stowed, 10° braced, over 40 mm)",
                 fontsize=10, color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0, 1, 0.93)); path = os.path.join(OUT, 'hills_height.png'); fig.savefig(path, dpi=130, facecolor=SURF); print(path)


if __name__ == '__main__':
    height() if sys.argv[1:] == ['height'] else main()
