"""Figure 1 of the research plan (v6): the pilot's three measured results, one panel each.

    python research/paper/make_fig1.py -> research/paper/fig1_v6.png   (fig1.png is v3's, fig1_v4.png v4's and v5's; kept as they were)

A (H1): seeded faults caught, results/mutation_summary.json; v4 splits each bar into the 14 re-created real faults and
   the 8 invented for mutation testing (the out-of-sample test; Zach, 2026-10-25).
B (H2): the surrogate against the simulator on the 280 held-out designs of H2's main fit (surrogate.py, seed 7),
   and the 6 best designs, each predicted without its own data, against their 1000-drop reruns (C15).
C (H3): Brier scores against the real drops, results/sim_vs_reality.md and drop_scores*.json (15 cm: drop_scores_15cm,
   where every model was committed before the drops). v6: the hard-floor row is the 0.31 bounce at every height, the
   model registered as the 15 cm primary (it was the 0.39 ball bounce, which left the primary out of the figure); the
   first model is labelled by its start bug, not "as registered", and "dead floor" is "default floor" as in the text.
   The dashed line is
   the expected score of a model that knew each case's true odds (estimated from the drops; sim_vs_reality notes).
"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'tumble'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt

ACC, ACC2, INK, MUTED, RULE, GRAY, WARN = '#24506b', '#8fb0c6', '#1d2328', '#5a6570', '#cfd5da', '#aab4bc', '#c0562a'
plt.rcParams.update({'font.family': 'Segoe UI', 'font.size': 7.4, 'axes.edgecolor': RULE, 'axes.labelcolor': MUTED, 'xtick.color': MUTED,
                     'ytick.color': MUTED, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.linewidth': 0.7,
                     'xtick.major.width': 0.7, 'ytick.major.width': 0.7, 'xtick.major.size': 2.5, 'ytick.major.size': 2.5})


def title(ax, letter, text):
    ax.set_title(f'{letter}   {text}', loc='left', fontsize=8.2, color=INK, fontweight='semibold', pad=6)


if __name__ == '__main__':
    fig = plt.figure(figsize=(7.1, 2.4))
    gs = fig.add_gridspec(1, 5, width_ratios=[1.12, 0.92, 0.55, 0.55, 0.55], left=0.012, right=0.968, top=0.86, bottom=0.245, wspace=0.42)

    # A: H1
    M = json.load(open(os.path.join(ROOT, 'results', 'mutation_summary.json')))
    rows = [('the first check alone (interference)', M['S0_pairs_only']), ('the suite grown from escapes', M['S1_full_suite']),
            ('+ a check for the survivor', M['S2_plus_screw_alignment'])]
    a = fig.add_subplot(gs[0]); a.spines['left'].set_visible(False); a.set_yticks([])
    nr, ni, gap = M['historical_mutants'], M['mutants'] - M['historical_mutants'], 0.5   # v4: a slot each for real and invented
    for i, (lab, r) in enumerate(rows):
        yy, kr = 2 - i, r['historical_killed']
        ki = r['killed'] - kr
        a.barh(yy, nr, height=0.36, color='#eef2f5', lw=0); a.barh(yy, ni, left=nr + gap, height=0.36, color='#eef2f5', lw=0)
        a.barh(yy, kr, height=0.36, color=ACC, lw=0); a.barh(yy, ki, left=nr + gap, height=0.36, color=ACC2, lw=0)
        a.text(0, yy + 0.3, lab, fontsize=7.2, color=INK, va='bottom')
        a.text(kr - 0.4, yy, f'{kr}', fontsize=7.4, color='white', va='center', ha='right', fontweight='semibold')
        a.text(nr + gap + ki - 0.4, yy, f'{ki}', fontsize=7.4, color=INK, va='center', ha='right', fontweight='semibold')
        a.text(nr + gap + ni + 0.6, yy, f"{r['killed']}/{M['mutants']}", fontsize=6.8, color=MUTED, va='center')
    a.set_xlim(0, nr + gap + ni + 4.2); a.set_ylim(-0.4, 2.85)
    a.set_xticks([nr / 2, nr + gap + ni / 2]); a.tick_params(axis='x', length=0)
    a.set_xticklabels([f're-created\nreal faults ({nr})', f'mutation\ntesting ({ni})'], fontsize=7.0, linespacing=1.15)
    title(a, 'A', 'H1  Checks vs seeded faults')

    # B: H2
    import surrogate as SU, sweep as SW
    T = json.load(open(os.path.join(ROOT, 'results', 'tumble_truth.json')))
    ev, g, (X, y, nn, te) = SU.evaluate(T['designs'], T['keys'], T['lo'], T['hi'], 120, np.random.default_rng(7))
    m, s = g.predict(X[te])
    b = fig.add_subplot(gs[1]); b.plot([0.2, 0.8], [0.2, 0.8], color=GRAY, lw=0.8, zorder=0)
    b.scatter(y[te], m, s=5, color=ACC2, lw=0, alpha=0.85, label=f'280 held-out designs')
    P = json.load(open(os.path.join(ROOT, 'results', 'surrogate_peak_check.json')))[0]
    bt = np.array([r['sim_1000'] for r in P['rows']]); bm = np.array([r['surrogate'] for r in P['rows']])
    b.scatter(bt, bm, s=16, marker='D', color=WARN, lw=0, zorder=3, label=f"6 best, vs 1000-drop reruns")
    b.set_xlim(0.2, 0.8); b.set_ylim(0.2, 0.8); b.set_xticks([0.2, 0.4, 0.6, 0.8]); b.set_yticks([0.2, 0.4, 0.6, 0.8])
    b.set_xlabel('simulator: P(upright)'); b.set_ylabel('surrogate', labelpad=2)
    b.text(0.215, 0.765, f"RMSE {100 * ev['rmse']:.1f} pts\n90% intervals hold {100 * ev['coverage90']:.1f}%", fontsize=6.6, color=INK, va='top')
    b.annotate(f"best 6: {P['inside']} of 6 inside,\n~{P['mean_miss_pts']:.0f} pts low (C15)", xy=(0.70, 0.62), xytext=(0.47, 0.30), fontsize=6.6, color=WARN,
               arrowprops=dict(arrowstyle='-', color=WARN, lw=0.6))
    title(b, 'B', 'H2  Surrogate vs simulator')

    # C: H3
    models = ['naive guess', 'first model (start bug)', 'start fixed, default floor', 'floor bounce, fitted at 6 cm', 'hard floor, bounce measured']
    brier = {'6 cm': [1.293, 0.578, 0.861, 0.443, 0.483], '15 cm': [1.522, None, 1.120, 0.650, 0.677], '30 cm': [1.506, 0.871, 1.156, 0.634, 0.693]}
    before = {'6 cm': [None, True, False, False, False], '15 cm': [None, None, True, True, True], '30 cm': [None, True, True, True, False]}
    floor = {'6 cm': 0.44, '15 cm': 0.61, '30 cm': 0.60}
    drops = {'6 cm': 181, '15 cm': 180, '30 cm': 180}
    for j, h in enumerate(brier):
        c = fig.add_subplot(gs[2 + j]); c.spines['left'].set_visible(False); c.set_yticks([]); c.patch.set_alpha(0)   # row labels may run into the next panel
        for i, (v, bf) in enumerate(zip(brier[h], before[h])):
            yy = 4 - i
            if v is None:                                  # the original model was never run at 15 cm
                c.text(0.04, yy, 'not run', va='center', fontsize=6.2, color=MUTED, zorder=4, bbox=dict(facecolor='white', edgecolor='none', pad=0.4)); continue
            if bf is None: c.barh(yy, v, height=0.34, color=GRAY, lw=0)
            elif bf: c.barh(yy, v, height=0.34, color=ACC, lw=0)
            else: c.barh(yy, v, height=0.34, color='white', edgecolor=ACC, lw=0.8, hatch='//////')
            c.text(v + 0.04, yy, f'{v:.2f}', va='center', fontsize=6.6, color=INK)
            if j == 0: c.text(0, yy + 0.24, models[i], fontsize=6.7, color=INK, va='bottom', zorder=4,
                              bbox=dict(facecolor='white', edgecolor='none', pad=0.6))
        c.axvline(floor[h], color=INK, lw=0.7, ls=(0, (2, 2)), ymax=0.93, zorder=3)
        c.set_xlim(0, 1.75); c.set_xticks([0, 0.5, 1.0, 1.5]); c.set_xticklabels(['0', '.5', '1', '1.5']); c.set_ylim(-0.45, 4.75)
        c.set_xlabel(f"{h} ({drops[h]} drops)")
        if j == 0: title(c, 'C', 'H3  Brier score vs real drops (lower is better)')
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    fig.legend(handles=[Patch(facecolor=ACC, label='predicted before those drops'), Patch(facecolor='white', edgecolor=ACC, hatch='//////', label='after (post hoc)'),
                        Line2D([0], [0], color=INK, lw=0.7, ls=(0, (2, 2)), label='best possible (chance)')],
               loc='lower right', bbox_to_anchor=(0.99, -0.01), ncol=3, fontsize=6.6, frameon=False, handlelength=1.6, columnspacing=1.2)
    fig.savefig(os.path.join(HERE, 'fig1_v6.png'), dpi=300)
    print('wrote paper/fig1_v6.png')
