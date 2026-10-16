"""Figure 1 of the research plan (v3): the pilot's three measured results, one panel each.

    python research/paper/make_fig1.py -> research/paper/fig1.png

A (H1): seeded faults caught, results/mutation_summary.json.
B (H2): the surrogate against the simulator on the 280 held-out designs of H2's main fit (surrogate.py, seed 7),
   and the 6 best designs, each predicted without its own data, against their 1000-drop reruns (C15).
C (H3): Brier scores against the real drops, results/sim_vs_reality.md and drop_scores*.json; the dashed line is
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
    fig = plt.figure(figsize=(7.1, 2.5))
    gs = fig.add_gridspec(1, 4, width_ratios=[1.0, 0.95, 0.66, 0.66], left=0.012, right=0.968, top=0.865, bottom=0.235, wspace=0.36)

    # A: H1
    M = json.load(open(os.path.join(ROOT, 'results', 'mutation_summary.json')))
    rows = [('the first check alone (interference)', M['S0_pairs_only']), ('the suite grown from escapes', M['S1_full_suite']),
            ('+ a check for the survivor', M['S2_plus_screw_alignment'])]
    a = fig.add_subplot(gs[0]); a.spines['left'].set_visible(False); a.set_yticks([])
    for i, (lab, r) in enumerate(rows):
        yy = 2 - i
        a.barh(yy, M['mutants'], height=0.36, color='#eef2f5', lw=0)
        a.barh(yy, r['killed'], height=0.36, color=ACC if i else ACC2, lw=0)
        a.text(0, yy + 0.3, lab, fontsize=7.2, color=INK, va='bottom')
        a.text(r['killed'] - 0.5, yy, f"{r['killed']}", fontsize=7.4, color='white', va='center', ha='right', fontweight='semibold')
        a.text(22.7, yy, f"real: {r['historical_killed']} of {M['historical_mutants']}", fontsize=6.6, color=MUTED, va='center')
    a.set_xlim(0, 29.5); a.set_ylim(-0.4, 2.85); a.set_xticks([0, 11, 22]); a.set_xlabel(f"seeded faults caught, of {M['mutants']}")
    title(a, 'A', 'H1  Checks against seeded faults')

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
    models = ['naive guess', 'as registered', 'start fixed, dead floor', 'floor bounce, fitted at 6 cm', 'hard floor, bounce measured']
    brier = {'6 cm': [1.293, 0.578, 0.861, 0.443, 0.456], '30 cm': [1.506, 0.871, 1.156, 0.634, 0.672]}
    before = {'6 cm': [None, True, False, False, False], '30 cm': [None, True, True, True, False]}
    floor = {'6 cm': 0.44, '30 cm': 0.60}
    for j, h in enumerate(brier):
        c = fig.add_subplot(gs[2 + j]); c.spines['left'].set_visible(False); c.set_yticks([])
        for i, (v, bf) in enumerate(zip(brier[h], before[h])):
            yy = 4 - i
            if bf is None: c.barh(yy, v, height=0.34, color=GRAY, lw=0)
            elif bf: c.barh(yy, v, height=0.34, color=ACC, lw=0)
            else: c.barh(yy, v, height=0.34, color='white', edgecolor=ACC, lw=0.8, hatch='//////')
            c.text(v + 0.04, yy, f'{v:.2f}', va='center', fontsize=6.6, color=INK)
            if j == 0: c.text(0, yy + 0.24, models[i], fontsize=6.9, color=INK, va='bottom', zorder=4,
                              bbox=dict(facecolor='white', edgecolor='none', pad=0.6))
        c.axvline(floor[h], color=INK, lw=0.7, ls=(0, (2, 2)), ymax=0.93, zorder=3)
        c.set_xlim(0, 1.75); c.set_xticks([0, 0.5, 1.0, 1.5]); c.set_xticklabels(['0', '.5', '1', '1.5']); c.set_ylim(-0.45, 4.75)
        c.set_xlabel(f"Brier score, {h} ({'180' if j else '181'} drops)")
        if j == 0: title(c, 'C', 'H3  Simulation vs real drops (lower is better)')
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    fig.legend(handles=[Patch(facecolor=ACC, label='predicted before those drops'), Patch(facecolor='white', edgecolor=ACC, hatch='//////', label='after (post hoc)'),
                        Line2D([0], [0], color=INK, lw=0.7, ls=(0, (2, 2)), label='best possible (chance)')],
               loc='lower right', bbox_to_anchor=(0.99, -0.01), ncol=3, fontsize=6.6, frameon=False, handlelength=1.6, columnspacing=1.2)
    fig.savefig(os.path.join(HERE, 'fig1.png'), dpi=300)
    print('wrote paper/fig1.png')
