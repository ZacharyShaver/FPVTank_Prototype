# Backtest 1: does the adversary find P23?

Written 2026-10-24, before the adversary ran (R11 in `checks/README.md`). Nothing below changes after the run;
results go in `RESULT.md`.

**The escape.** P23 (`research/data/iterations.csv`, 2026-10-12, bench): the drop-in
shelf ring could fall out of its lock when the base was upside down, which it is during assembly. No check covered
it (`check_had_passed: no`). The fix was set 11: the ring merged into the base.

**The change that introduced it.** Set 7 (2026-10-04): the shelf and the ribbon cup's wall became `shelf_ring`, a
separate print dropped into the base from above (`pan_coil_b.INSERT`). The escape was found 8 days and three sets
later.

**What the adversary gets.** A sandbox outside the repo, built by `checks/backtests/blind.py`:
- the pan coil generator and its check file as set 7 stood. Flags from set 8 onward are folded to their set 7
  values and their code removed, as are the parts set 7 did not have (688, 6704, horn). All comments and docstrings
  are stripped, since today's comments state the answer.
- only the checks that existed at set 7: `pairs`, `insertion`, `assembly`, `gear_play`, `bearing_races` (with
  `hub_face`);
- the fault operators (`move`, `grow`, `glue`, `nofeat`, `dup`, `param`) without the historical mutant table;
- a brief: the set 7 change in the words of `head-v2/fixes/base_shelf_set7.py`'s docstring (written 2026-10-04,
  before the escape), and each check's one-line claim;
- the adversary's instructions: `.claude/agents/adversary.md` verbatim, except the example "P16 was a spline 1.0 mm
  shorter than modelled", which is a later escape in this same design and is cut.

**Blinding, with its control.** Before the run, a grep of the sandbox for words that only later history explains
(6704, 688, horn, hollow, merged, upside, fall out, square, straight wire, set 8, set 9, set 10, set 11) must find
nothing. The same grep on the source files must find them; that is the grep's control. After the run, the adversary
lists every file it read, and any file outside the sandbox voids the run.

**Scoring, fixed now.**
- **HIT:** the report names, as a surviving mutant or as a property no check covers, that the shelf ring is not held
  in the base: it can come out of its seat or lock, under gravity with the base inverted, in handling, or simply
  because nothing checks that it stays.
- **PARTIAL:** a survivor or property about the ring's seat or lock that stops short of it coming out (mis-seated,
  rotated, keys clashing).
- **MISS:** neither.
- **Recorded, not scored:** mutants written, survivors, and whether it finds the two later escapes latent in this
  design outside the change: P14 (the gear screw threads into the stub below the step, so the stub snaps when the
  screw is tightened) and P16 (the input gear slips on its printed spline bore and rubs the servo's block).

**One run.** A rerun is allowed only for a technical failure (the sandbox doesn't run), never for a miss.

**Known limits.** n = 1. The person who built the sandbox and wrote the brief knows the answer, so the brief is
quoted, not written. Identifier names (`RING_*`, `KEY_*`) survive the stripping; they describe set 7's own design.
