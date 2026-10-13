"""Workstream A of the research sprint: statistics and the figure from the retrospective iteration dataset.

    python research/analysis/iterations.py      # -> research/results/iterations_summary.json, research/figures/iterations.png

Reads research/data/iterations.csv (one row per design finding) and research/data/check_failures.csv (one row per
time an automated check itself was wrong). Retrospective data, reconstructed from transcripts, G-code and folder
timestamps, decisions.md and the lessons; `time_basis` says how exact each time is, and only 'exact' rows enter the
cycle-time statistics.
"""
import os, json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import matplotlib.dates as mdates

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = pd.read_csv(os.path.join(ROOT, 'data', 'iterations.csv'), parse_dates=['found_at', 'fix_ready_at'])
CF = pd.read_csv(os.path.join(ROOT, 'data', 'check_failures.csv'))
PRE = {'review', 'check', 'agent review', 'slicer'}          # caught before anything was printed
LOOP = D[D.id.str.startswith('P') & (D.found_by != 'print')]   # the AI-in-the-loop design period, design findings only
D['cycle_h'] = (D.fix_ready_at - D.found_at).dt.total_seconds() / 3600


def iqr(x):
    return [float(np.percentile(x, 25)), float(np.percentile(x, 75))]


def main():
    L = D.loc[LOOP.index]
    ex = L[(L.time_basis == 'exact') & L.cycle_h.notna()]
    bench = L[L.found_by == 'bench']
    S = {
        'period': [str(L.found_at.min().date()), str(L.found_at.max().date())],
        'design_findings': int(len(L)),
        'by_found_by': L.found_by.value_counts().to_dict(),
        'caught_before_printing': int(L.found_by.isin(PRE).sum()),
        'found_at_bench': int(len(bench)),
        'slipped_past_a_passing_check': int((L.check_had_passed == 'yes').sum()),
        'cycle_hours_exact': {'n': int(len(ex)), 'median': float(ex.cycle_h.median()), 'iqr': iqr(ex.cycle_h),
                              'bench_median': float(ex[ex.found_by == 'bench'].cycle_h.median()),
                              'within_3h': int((ex.cycle_h <= 3).sum())},
        'bench_categories': bench.category.value_counts().to_dict(),
        'print_failures': int((D.found_by == 'print').sum()),
        'electronics_drivetrain_escapes': int(D.id.str.startswith('E').sum()),
        'check_failures': {'n': int(len(CF)),
                           'false_pass': int(CF.failure.str.startswith('false pass').sum()),
                           'false_fail': int(CF.failure.str.startswith('false fail').sum()),
                           'weak_control': int(CF.failure.str.startswith('weak control').sum())},
        'note': 'retrospective; cycle = finding to fix ready (sliced or superseding files written); exact rows only',
    }
    os.makedirs(os.path.join(ROOT, 'results'), exist_ok=True)
    json.dump(S, open(os.path.join(ROOT, 'results', 'iterations_summary.json'), 'w'), indent=1, default=str)
    print(json.dumps(S, indent=1, default=str))
    figure(L, ex, bench)


def figure(L, ex, bench):
    ink, muted, accent = '#1d2328', '#5a6570', '#24506b'
    mk = {'bench': ('o', '#b5523b'), 'review': ('s', accent), 'check': ('D', '#3e8e6e'), 'agent review': ('^', '#3e8e6e'),
          'slicer': ('v', '#8a6d1d')}
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.3), gridspec_kw={'width_ratios': [1.65, 1]})
    ap = L[(L.time_basis == 'approx') & L.cycle_h.notna()]                 # approximate times: hollow markers
    for fb, (m, c) in mk.items():
        s = ex[ex.found_by == fb]
        a.scatter(s.found_at, s.cycle_h.clip(lower=0.05), marker=m, s=34, color=c, label=f'{fb} ({int((L.found_by == fb).sum())})',
                  edgecolor='white', linewidth=0.6, zorder=3)
        s = ap[ap.found_by == fb]
        a.scatter(s.found_at, s.cycle_h.clip(lower=0.05), marker=m, s=34, facecolor='none', edgecolor=c, linewidth=1.1, zorder=3)
    a.set_yscale('log'); a.set_yticks([0.1, 0.5, 1, 3, 10, 24, 72]); a.set_yticklabels(['0.1', '0.5', '1', '3', '10', '24', '72'])
    a.axhline(3, color=muted, lw=0.6, ls=':'); a.text(L.found_at.min(), 3.3, '3 h', color=muted, fontsize=7.5)
    a.set_ylabel('hours, finding to fix ready', fontsize=8.5); a.tick_params(labelsize=7.5)
    a.xaxis.set_major_formatter(mdates.DateFormatter('%b %d')); a.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    a.set_title('Design findings, Sep 27 to Oct 12, by how they were caught (hollow: approximate time)', fontsize=8.5, color=ink, loc='left')
    a.legend(fontsize=7, frameon=False, loc='upper right', ncol=2)
    for sp in ('top', 'right'): a.spines[sp].set_visible(False); b.spines[sp].set_visible(False)
    cats = bench.category.value_counts().sort_values()
    b.barh(cats.index, cats.values, color='#b5523b', height=0.6)
    b.set_title('Findings made at the bench, by kind', fontsize=8.5, color=ink, loc='left')
    b.tick_params(labelsize=7.5); b.set_xlabel('findings', fontsize=8.5)
    b.xaxis.set_major_locator(plt.MaxNLocator(integer=True))
    plt.tight_layout()
    os.makedirs(os.path.join(ROOT, 'figures'), exist_ok=True)
    p = os.path.join(ROOT, 'figures', 'iterations.png'); plt.savefig(p, dpi=200); plt.close(fig); print('wrote', p)


if __name__ == '__main__':
    main()
