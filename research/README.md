# Research sprint (2026-10-13 to 2026-10-27)

Evidence for the research plan "Checks That Can Fail" (UM-LANL SPARC AI Research Fellow application, due
2026-10-27). The plan and the sprint schedule live in the FPVTank_Control session folder (`research-plan/`).

| Path | What |
|---|---|
| `data/iterations.csv` | Workstream A: one row per design finding, Sep 27 to Oct 12 (P), plus earlier drivetrain and electronics escapes (E). Retrospective. |
| `data/check_failures.csv` | Every recorded case of an automated check itself being wrong (false pass, false fail, weak control). |
| `analysis/iterations.py` | Statistics (`results/iterations_summary.json`) and `figures/iterations.png`. |
| `paper/` | The research plan, draft v3 (2026-10-16): `checks-that-can-fail-v3.html` and its PDF (Edge, US Letter, 3 pages); Figure 1 from `make_fig1.py`. The Oct 13 draft stays in the session folder. |

**How the data was made.** Finding times come from the session transcripts (Zach's message reporting the finding) or
from the check or slicer run. Fix times come from G-code and superseded-folder timestamps, or from `docs/decisions.md`
dates. `time_basis` says which: `exact` (minute), `approx`, `day`, `reconstructed`. Only `exact` rows enter the
cycle-time statistics. The transcripts themselves stay out of the repo; findings are paraphrased.

**Categories.** `found_by`:
- `bench`: physical handling or test.
- `review`: Zach looking at a model or view before printing.
- `check`: an automated check during design.
- `agent review`: the AI noticing a fault while designing.
- `slicer`: print preparation.
- `print`: a failure while printing.

Everything except `bench` and `print` counts as caught before printing. `check_had_passed` is `yes` when an existing
automated check had passed the defect.

Prospective data, logged as findings happen from 2026-10-13, goes in `data/iterations_live.csv` and is kept separate. Its times are the times of the commits that recorded each finding (the hash is in `notes`); IDs follow the order things were logged, and are never renumbered, because commits and PROTOCOL.md cite them.
