# Review of draft v3 (2026-10-24)

Draft v3 as of c1fa14a (2026-10-17). Section by section: each flag was checked against the repo, and Zach's call
follows it. The changes go into v4.

## Summary and §1, The challenge

| # | Flag | Checked | Zach |
|---|---|---|---|
| 1.1 | "Fifteen checks have been caught being wrong" counts *cases*, not checks: C02 is two checks and C11 a whole suite. "A check has been caught being wrong 15 times" is exact. | `check_failures.csv`: 15 rows | **leave as is** (2026-10-25): v4 keeps "19 times" |
| 1.2 | **Count backtest 1's four check failures in the paper?** Logged as C16–C19 (a dead control, two false fails, one false pass), they move the counts from 15 / 12 / 5 to 19 / 13 / 9 (cases / false passes / during the pilot). Before and after below. | `check_failures.csv` C16–C19; backtest 1 `RESULT.md` | **counted** (2026-10-25); in v4 |
| 1.3 | "16 of 26 design flaws surfaced only at the bench" | `iterations_summary.json`: 26 findings, 16 at the bench. Holds. | |
| 1.4 | "361 hand drops took three sessions" is still true (the 15 cm drops came from the stand). All physical drops come to 541 in four sessions, which makes the cost point stronger. | `drop_scores*.json`: 181 + 180 + 180 | held for the space check |
| 1.5 | "each one costs days" sits against "a same-day loop" in the next paragraph. Either measure what an escape costs, or say what it costs ("a reprint and a bench session"). | no data on print-to-bench time | **reworded** (2026-10-25): "a reprint and a bench session" |
| 1.6 | The simulator's 80,000 tumbles were full-size sweep bodies; the 361 drops were scale models. That's fine as an order of magnitude, but a sharp reader may notice. Low priority. | `sweep.py`, `PROTOCOL.md` | |
| 1.7 | Placeholders to fill before sending: [Your name], [Org] (×6). | | |

Flag 1.2, before (v3) and after (v4):
- **Summary.** "Fifteen checks have been caught being wrong, none by the check itself." → "A check has been caught
  being wrong 19 times, never by the check itself."
- **What the pilot shows.** "15 cases of a check that was itself wrong, 12 of them passes that should have failed, and
  5 of them during the pilot: in a CAD check suite, … a cross-check or a control" → "19 cases …, 13 of them passes
  that should have failed, and 9 of them during the pilot: in a CAD check suite and its controls, … a cross-check, a
  control or a second agent".

## §2, Preliminary work

| # | Flag | Checked | Zach |
|---|---|---|---|
| 2.1 | **Zach:** "When an escape became a check, its kind stopped recurring" can be explained by the context the AI has: a curated record of past issues stops faults from being designed at all. The sentence credits the check alone, but two mechanisms are mixed: the lesson in the agent's context (prevention) and the check (detection). The data separates them a little. A lesson alone wasn't enough: the screwdriver-access rule (lesson, 2026-09-18) didn't stop P10, an access fault, from reaching the bench on 2026-10-03, and there is no access check. A lesson plus a check worked: the one assembly fault designed after Oct 3 (P21, Oct 11) was caught by the assembly sweep before printing. The evidence is thin (n = 1 each way). H1 measures detection on its own, with planted faults. Proposed wording below. | `iterations.csv` (P10, P21); `docs/lessons/2026-09-18-flat-cable-and-driver-access.md` | raised it; **wording accepted** (2026-10-25) |
| 2.2 | "What kept escaping is what no check models yet: wire routing (5 findings, the most common), friction, print tolerance, material and strength." Routing has 5 findings in all (3 at the bench). Grouped, forces are 8 of the 16 bench findings: friction 3, fit force 2, strength 1, material 1, retention 1. Retention (P23) is missing from the list. Backtest 1 shows geometric checks and mutants can't see forces, which is Aim 2's case. | `iterations_summary.json` `bench_categories`; backtest 1 | **accepted** (2026-10-25) |
| 2.3 | "Since August 2026" is right for neither start. **Zach:** the project has run on and off for about two years; AI edits probably began in July; the move out of Control may have reset file dates. **Checked:** Control's first commit is 2025-02-16. Its first Claude-co-authored commit is 2026-07-12 (54 in July, 44 in August), all software and bench tests. The agent's first design work was 2026-08-02/03: versioning the chassis STLs, a body revision brief, and the wrong bevel set (E03). The August pan/tilt was drawn by hand in Fusion (Aug 23–30). The code-based CAD generator dates from about 2026-09-17: the earliest date in the generator's own documents, and the earliest surviving CAD session (Sep 18) picks up from a hand-off. File creation dates are useless here: the CAD was never committed in Control, and the move on Sep 26–27 reset them. Proposed: "I have been building Scorpion since February 2025. Since July 2026 I have worked on it with an AI coding agent (Claude, by Anthropic): first its software, and since September its CAD." This also makes the pace claim sharper: 11 pan drive iterations in the agent's first month of CAD. | Control `git log`; session records; `head-v2/generator/*.md` | **accepted** (2026-10-25) |
| 2.4 | "parametric, code-based CAD (CadQuery)": the pan drive, which is the subject of the 11 iterations and of H1's model, is a signed-distance generator in numpy (`pan_coil_b.py`), not CadQuery. CadQuery and OpenCascade do the head's fixes, the exact booleans and the STEP export. Suggest "code-based CAD in Python (CadQuery and signed-distance models)". | `grep` for cadquery and marching_cubes | **accepted** (2026-10-25) |

Proposed wording for 2.1, about the same length:
> **Escapes.** A lesson alone did not stop a fault's kind: a screwdriver-access rule written Sep 18 did not keep an
> access fault from the bench on Oct 3. A lesson with a check did: after Oct 3 the one assembly fault designed (Oct 11)
> was caught by the assembly sweep before printing. What kept escaping is what no check models yet: forces (8 of 16
> bench findings: friction, fit, strength, retention, material) and wire routing (5 findings).

## §3, Pilot results

Every number was checked and holds. H2: 80,000 tumbles in 74 s; 3.9 pts; 86.8%; 266 of 280, 2 wrong, 14 sent, 95%;
1 of 6. H3: 361 drops; 0.58 vs 1.29; the coins moved predictions the right way for 3 of 3 bodies, 2 of them
significant; 0.86; 7–17 mm; 0.63 vs 1.16 (CI 0.40–0.64); 0.46 and 0.67 (the 0.39 bounce at 0.1 ms, converged);
15 cm 0.68 vs 1.12 (CI 0.35–0.54), 0.64, best 0.61. H4: 1.6 h (0.6–2.5, n 20); 10 of 26; 5; 17. Sources:
`mutation_summary.json`, `surrogate_summary.json`, `tumble_truth.json`, `drop_scores*.md`, `iterations_summary.json`.

| # | Flag | Checked | Zach |
|---|---|---|---|
| 3.1 | "Each hypothesis and prediction was committed to version control before its test" holds for H2 and H3: `PROTOCOL.md` was committed 10-13 09:45, before the results at 10:35, and H3b and H3c were registered before their drops. It doesn't hold for H1 or H4. H1's 22 faults and harness were committed before the run (09:45, results 11:26), but no H1 prediction was. H1 as planned (`sprint-plan.md`, outside git) was "checks with negative controls vs without", and the test run compared the first check with the grown suite. H4 is retrospective by its own text. | `git log` research/; `sprint-plan.md` | **accepted** (2026-10-25) |
| 3.2 | "Each result has a control": H4 has none. | | **accepted** (2026-10-25) |
| 3.3 | H1's "all 14 real" is partly by construction: those faults re-create the escapes the suite was grown from. The out-of-sample test is the 8 invented faults: the first check caught 5 of 8, the suite 7 of 8, and the one survivor (M20, invented) became the new check. Saying so makes H1 more convincing, not less. | `mutation_matrix.csv` `historical` column | **accepted** (2026-10-25) |
| 3.4 | H2's gate, in the decision region: of the 10 held-out designs that truly clear 60%, it accepted 3, sent 6 to simulation and wrongly rejected 1. "2 of 266 wrong" reads as under 1%; where decisions are made it is 1 of 4 decided. This fits C15 and Aim 2's "check its intervals where decisions are made". Optional, if there's room. | recomputed from `surrogate.py` (seed 7) | held for the space check |
| 3.5 | H3 at 15 cm: the text's headline, "the primary hard floor scored 0.68", isn't in Fig. 1C. The figure's "hard floor, bounce measured" bar is the 0.39 bounce (0.64) at every height. "The one above 0.64" doesn't say which model. A reader sees a hard floor at 0.68 in the text and at 0.64 in the figure. | `drop_scores_15cm.md`; `make_fig1.py` docstring | **accepted** (2026-10-25) |
| 3.6 | Naming: `PROTOCOL.md` calls the 30 cm test "H4"; the paper's H4 is cycle time. Anyone tracing a number to a file meets two H4s. A one-line map in `research/README.md` fixes it. Low priority. | commit 63fb8a0 | held for the space check |
| 3.7 | "What the pilot shows" (15 cases, 12 passes, 5 in the pilot) moves with flag 1.2. | | done with 1.2 (19 / 13 / 9) |

Proposed wording:
- **3.1 and 3.2** (replaces "Each hypothesis and prediction was committed … every number here traces to a file in the
  repository."): "H2's and H3's predictions were committed to version control before their tests [7], and H1's 22
  faults before they were run; H4 is retrospective. Each experiment has a control, a broken case that must come out
  differently, and every number here traces to a file in the repository."
- **3.3** (after "caught 21 (all 14)."): "The out-of-sample test is the 8 faults invented for the harness: the first
  check caught 5, the suite 7."
- **3.5** (replaces the 15 cm sentence): "A third blind test, at 15 cm from a printed drop stand, held: the registered
  primary, a hard floor with bounce 0.31, scored 0.68 against 1.12 for the default floor (difference 0.44, 95% CI
  0.35–0.54), and the floor with the ball's measured bounce (0.39, Fig. 1C) scored 0.64, near the best possible 0.61."

## §4, Approach

| # | Flag | Checked | Zach |
|---|---|---|---|
| 4.1 | **Aim 1 has the designer grade itself.** "The agent must deliver every design change with its checks and their mutants": the same agent writes the change, the checks and the faults that grade the checks. That is the shared blind spot the paper's own thesis warns against ("none was caught by the check itself; each was exposed by something outside it"). Backtest 1 used a separate adversary in a fresh context for exactly this reason. Proposed: a second agent, which sees the change but not the designer's reasoning, writes the mutants. | `checks/README.md` principle 4; backtest 1 | **accepted** (2026-10-25) |
| 4.2 | The agents are checks too: replay past changes whose escapes are known before trusting an agent on new ones (R11). Backtest 1's result, the mutant writer missing a force fault, shows why. One clause, if there's room. | backtest 1 | held for the space check |
| 4.3 | Citation [4] (Karniadakis, physics-informed ML) is attached to "send any case a surrogate is unsure of to full simulation or physical test". That is uncertainty gating, not physics-informed ML. [4] fits "Train surrogates on simulation sweeps" instead; the gating needs no cite, or [5]. | ref list | **accepted** (2026-10-25) |
| 4.4 | **Aim 3 can't separate prevention from detection** (Zach's point, 2.1). "AI agents alone" vs "with checks" mixes what the agent avoids designing (the escape record in its context) with what the checks catch. Cheapest fix, a measure, not new arms: count faults designed per change, and the share caught before hardware. | | **accepted** (2026-10-25) |
| 4.5 | Aim 1's "perturb a load" operator is the one the forces finding (2.2, backtest 1) says matters most, and the pilot's harness has none. Tie them in a few words: "…perturb a load, since half the bench's escapes were forces". Optional. | `research/harness/mutants.py` | held for the space check |

Proposed wording:
- **4.1** (Aim 1, replaces "The agent must deliver every design change with its checks and their mutants, and a change
  is accepted only when its checks reach a set mutation score."): "The agent must deliver every design change with its
  checks; a second agent, which sees the change but not the designer's reasoning, writes the mutants; and a change is
  accepted only when its checks reach a set mutation score."
- **4.2** (optional, after it): "Each agent is itself tested first, by replaying past changes whose escapes are known."
- **4.3:** move "[4]" to after "run on high-performance computing".
- **4.4** (Aim 3 measures): "Measures: time from a test finding to a verified change; faults designed per change and
  the share caught before hardware, which separate prevention from detection; mutation score; whether the surrogate's
  stated uncertainty holds; compute and engineer hours."

## §5–7, Schedule, Deliverables, Risks; References

| # | Flag | Checked | Zach |
|---|---|---|---|
| 7.1 | **A missing risk, the one Zach raised: the library rots.** A growing library gathers checks that stop catching anything, that cry wolf, or that no longer fit the parts. The pilot has direct evidence: a dead control in `insertion` and a fragile one in `hub_face` (backtest 1). The mitigation is what `checks/` does: each check keeps a mutation score and a bench record, and is retired only on that evidence. | `checks/README.md`; registry K02, K05 | **accepted** (2026-10-25) |
| 7.2 | A risk to Aim 3's comparison: agents remember. The memory that helps a designer leaked answers into backtest 1, and it would leak them between matched tasks too. Mitigation: hold the study's tasks out of the agents' context. Optional. | backtest 1 RESULT.md | held for the space check |
| 5.1 | Aim 3's "matched tasks" has no number. A reviewer will ask how many. Zach's call whether to commit to one. | | no number (2026-10-25) |
| 6.1 | The library deliverable has a start: the pilot's registry (37 checks), rot audit and backtest harness, committed 2026-10-24. "begun in the pilot" is accurate. Optional. | commit 9b1f7dc | held for the space check |
| R | References: all eight are correctly cited and used where they belong, apart from [4] (flag 4.3). Nothing missing that a reviewer would expect. | | |

Proposed wording:
- **7.1** (a new risk, after "Agent errors"): "Check rot. A growing library gathers checks that stop catching
  anything or cry wolf; the pilot already found a dead control. Each check keeps its mutation score and bench record,
  and is retired on that evidence, never silently."
- **7.2** (optional, at the end of Aim 3 or as a risk): "Agents remember, so the study's tasks are held out of their
  context."

## Accepted wording for v4

Applied together at the end of the review, so the three-page fit is checked once.

- **§2, first paragraph (2.3, 2.4):** "I have been building Scorpion, a tracked ground robot with a 360° pan-tilt
  camera head, as a platform for embodied AI since February 2025. Since July 2026 I have worked on it with an AI
  coding agent (Claude, by Anthropic): first its software, and since September its CAD. I build and test at the
  bench; the agent turns each finding into a change to code-based CAD in Python (CadQuery and signed-distance
  models), runs automated checks and produces print files, often the same day." It runs about 15 words longer than
  v3's.
- **§2, Escapes bullet (2.1, 2.2):** "A lesson alone did not stop a fault's kind: a screwdriver-access rule written
  Sep 18 did not keep an access fault from the bench on Oct 3. A lesson with a check did: after Oct 3 the one assembly
  fault designed (Oct 11) was caught by the assembly sweep before printing. What kept escaping is what no check models
  yet: forces (8 of 16 bench findings: friction, fit, strength, retention, material) and wire routing (5 findings)."
- **§3 intro (3.1, 3.2):** "H2's and H3's predictions were committed to version control before their tests [7],
  and H1's 22 faults before they were run; H4 is retrospective. Each experiment has a control, a broken case that must
  come out differently, and every number here traces to a file in the repository."
- **§3 H1 (3.3), after "caught 21 (all 14).":** "The out-of-sample test is the 8 faults invented for the harness: the
  first check caught 5, the suite 7."
- **§3 H3 (3.5), the 15 cm sentence:** "A third blind test, at 15 cm from a printed drop stand, held: the registered
  primary, a hard floor with bounce 0.31, scored 0.68 against 1.12 for the default floor (difference 0.44, 95% CI
  0.35–0.54), and the floor with the ball's measured bounce (0.39, Fig. 1C) scored 0.64, near the best possible
  0.61."
- **Held for the space check:** 3.4 (the gate in the decision region), 3.6 (the PROTOCOL naming map).
- **§4 Aim 1 (4.1):** "The agent must deliver every design change with its checks; a second agent, which sees the
  change but not the designer's reasoning, writes the mutants; and a change is accepted only when its checks reach a
  set mutation score."
- **§4 Aim 2 (4.3):** move "[4]" from after "full simulation or physical test" to after "run on high-performance
  computing".
- **§4 Aim 3 (4.4):** "Measures: time from a test finding to a verified change; faults designed per change and the
  share caught before hardware, which separate prevention from detection; mutation score; whether the surrogate's
  stated uncertainty holds; compute and engineer hours."
- **Held for the space check:** 4.2 (the agents tested by replay), 4.5 (tie "perturb a load" to the forces finding).
- **§7 Risks (7.1), a new risk after "Agent errors":** "Check rot. A growing library gathers checks that stop catching
  anything or cry wolf; the pilot already found a dead control. Each check keeps its mutation score and bench record,
  and is retired on that evidence, never silently."
- **Held for the space check:** 7.2 (agents remember), 6.1 (the library begun in the pilot).

## v4 written (2026-10-25)

`checks-that-can-fail-v4.html` holds every accepted change above, except where this section says otherwise. Before
the counts changed, C16–C19 were logged in `research/data/check_failures.csv`: 19 cases, 13 false passes, 9 since
Oct 13.

**3.3 changed (Zach): the figure carries it, not the text.** Figure 1A (`fig1_v4.png`) splits each bar into the 14
re-created real faults and the 8 invented for mutation testing: 7 + 5, 14 + 7, 14 + 8. H1 keeps v3's wording, minus
the trims below, and the caption names the split as the out-of-sample test. `fig1.png` stays v3's.

**Trims to fit three pages** (the accepted changes added about 150 words). Zach to check:
- Page 1, Escapes: "(Sep 18) let an access fault reach the bench (Oct 3)"; "caught by its check" for "caught by the
  assembly sweep".
- Page 1, H1: "14 re-creating real failures (Fig. 1A)"; "The first check" (was "The project's first check"); "caught
  21." (was "21 (all 14)", which the figure now shows); "a part 0.6 mm out of its grooves"; "None of the ten checks is
  vacuous: each catches a fault."
- Page 2, H3: "against a best possible near 0.44 and 0.60" (was "where the drops' own randomness sets a best possible
  score near …", which the caption explains); "from a drop stand"; "; with the ball's measured bounce (0.39, Fig. 1C)
  it scored 0.64".
- Page 3, Aim 1: "a fault-operator library"; "The agent delivers each change with its checks; a second agent, blind to
  the designer's reasoning, writes the mutants; and a change passes only when they reach a set mutation score";
  "Designs, results and logs are versioned and signed: a chain of custody for AI-generated designs."
- Page 3, Check rot: "Libraries gather checks that stop catching faults or cry wolf (the pilot found a dead control);
  each keeps its mutation score and bench record, and is retired on that evidence, never silently."
- Page 3, Schedule, months 1–2: "Evaluate SPARC foundation models and codes; pick the problem; package the toolkit."
- Page 3, ref [8]: "ACM TOG 41(6), 2022".

**Fit, corrected 2026-10-25.** The screen measurement (0.36 / 0.32 / 0.25 in) was wrong about print. Zach's
first PDFs came out at 5 pages. Those went through the *Microsoft Print to PDF* printer, which made it worse, but the
root cause was in the paper's print CSS: it reset the body's padding, not its default 8px margin, so print had 16px
less width than designed. The PDF's own page geometry shows it: the content box starts 8px in. v3 had the same bug
and fit by 0.04 in. v4's print CSS now sets `margin:0`. `pagefit.py --print` prints each page alone and measures what
it has left: **0.30 / 0.22 / 0.15 in**. The whole document is **3 pages**. `checks-that-can-fail-v4.pdf` was made with
the same engine as Save as PDF (Producer `Skia/PDF m156`).

**The space check.** Nothing held fits without cutting more of the text. Each held item costs about a line, and page
3 has a little over one (0.25 in). Not added: 1.4, 3.4, 4.2, 4.5, 6.1, 7.2. 3.6 needs no paper space, so it went into
`research/README.md` (the H4 naming map).
