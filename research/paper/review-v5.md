# Review of draft v5: a cold read (2026-10-25)

A fresh agent with no project context read v5 (its text and Figure 1 only) as a SPARC panelist would, and listed what
it questioned: 29 items. **Its score: 3 / 5**, "a 4 with those fixed and the related work added." It couldn't find a
public call for the fellowship; SPARC's listed areas include AI foundation models for simulation and design, HPC
and co-design. Each item below was checked against the repo. Zach's call goes in the last column.

Strongest, in its words: rigor and candour (controls, commitments before testing, failed controls reported); a real
end-to-end pilot that found real defects; a clear, transferable framing and a concrete transition test.

## Would lower the score (checked: real)

| # | Flag | Checked | Zach |
|---|---|---|---|
| C1 | **Fig. 1C: show the registered 15 cm primary (0.68)?** The text's headline at 15 cm isn't in the figure, whose 15 cm bars are 0.65 (never mentioned) and 0.64; and "the ball" is never introduced. v3's flag 3.5 fixed only the text. Six models were committed before the 15 cm drops; the primary held against its control but three others scored better. Proposed: the figure's 15 cm "hard floor" bar becomes the primary; the text drops the 0.39 ball clause (saves about 12 words). | `drop_scores_15cm.md` | **C1 accepted** (2026-10-25): plot the registered 0.31 at all three heights (0.48 / 0.68 / 0.69); 0.31 was the early, rough reading of E3 rocking, 0.39 the clean ball reading |
| C2 | **30 cm: say which model was registered as the main test?** The reader sees three committed models (0.87, 1.16, 0.63) and suspects the text picked the best against the worst. It didn't: `PROTOCOL.md` names the fitted bounce (model 3) the main test and the dead floor (model 2) its control. The figure's "as registered" bar (0.87) is the first model, with the start bug. Proposed: "…registered as the main test before the 30 cm drops…"; relabel that bar "first model (start bug)". | `PROTOCOL.md` H4 results | **accepted** (2026-10-25) |
| C3 | **H2: add the gate's record where it matters (v3's held flag 3.4)?** Only 10 of the 280 held-out designs clear 60%, so answering "no" every time is right 270 times. Of those 10, the gate accepted 3, sent 6 to simulation and wrongly rejected 1. The cold reader raised this unprompted. Also, "95% of the simulations saved" leaves out the 120 training runs: say "for new designs". About one line on page 2, which has one. | `surrogate.py` (seed 7); review-v3 3.4 | **accepted** (2026-10-25) |
| C4 | **The repo is private: make the evidence checkable?** "Committed to version control before their tests" and "every number here traces to a file in the repository" can't be checked by a reviewer. Options: make the repo (or a `research/` export) public; archive a snapshot with a DOI (Zenodo); or say "available to reviewers on request". | `gh repo view`: PRIVATE | **make it public** (2026-10-25), soon; the paper gets the link once it is |
| C5 | **H1: state the out-of-sample number in the text?** 14 of 14 is by construction, and 22 of 22 includes a check built for the survivor. The out-of-sample result is 7 of 8. Proposed: "caught 21 (7 of the 8 invented)". +4 words, page 1. The caption's "the out-of-sample test" is true for the first two bars only. | `mutation_summary.json` | **accepted** (2026-10-25) |
| C6 | **Aim 2: point the physics at the escapes the pilot found?** §2 says forces and wiring escaped (13 of 16); Aim 2 adds tumble and rollover physics, which models neither. One clause, e.g. "MuJoCo for mechanisms, including the contact and friction behind the pilot's force escapes", or v3's held 4.5 ("perturb a load"). Page 3 has no line free, so it costs a trim. | §2, §4 | **accepted** (2026-10-25): the MuJoCo clause |
| C7 | **Add VVUQ references?** For a LANL panel, the missing verification, validation and uncertainty quantification literature stands out: Kennedy and O'Hagan's calibration (what "bench data calibrates the physics" does), ASME V&V 40, NASA-STD-7009; and conformal prediction for checking intervals. Two references cost about two lines on page 3. | ref list | **swap [4]** (2026-10-25): Kennedy and O'Hagan replaces [4], cited at "Bench data calibrates the physics" |
| C8 | **Aim 3: a number of tasks, or a smaller study?** Three arms on an unnamed subsystem with hardware in four months, with no task or engineer count. v4's flag 5.1 was "no number". | §4, §5 | **(b)** (2026-10-25): agents alone against agents with checks; the sponsor's records as the conventional baseline |

## For the interview (answers exist; no change needed)

| # | Their question | The answer |
|---|---|---|
| I1 | Were H2's 80,000 tumbles on the floor that sank? | Yes. H2 measures the surrogate against the simulator, whatever its physics; H3 tests the simulator. |
| I2 | RMSE 3.9 points is mostly the simulator's own noise (about 3.5 at 200 tumbles). | True; it's near the floor any surrogate could reach. Check what the intervals cover before saying more. |
| I3 | Seven false passes (§2) against "5 had slipped past a check that passed" (H4). | Different sets: check failures against design findings. Some false passes (the tracker's self-test, the voxel count) weren't design findings. |
| I4 | Why n = 20 of 26 in H4? | 20 have exact times; the rest were reconstructed. |
| I5 | Can sponsor CAD go to a commercial cloud model? | Prepare an answer: on-prem or SPARC models, which is also what "evaluate SPARC foundation models" is for. |
| I6 | What needs HPC? The pilot ran on 20 cores in 74 s. | Full-size vehicle sweeps with Chrono, and many designs per change. |
| I7 | How were the CIs computed? The drops are clustered. | Checked (2026-10-25, `posthoc_cluster_ci.py`, PROTOCOL post hoc 10): resampling whole cells of 5 drops widens the CIs to 0.38–0.68 (30 cm) and 0.31–0.59 (15 cm), from 0.40–0.64 and 0.35–0.54. Both stay far from 0; by body-and-weight group they barely move. The paper keeps the registered CIs. |
| I8 | 19 out of how many? "Never by the check itself" holds by definition. | No denominator is given. Not quite by definition: a working control can catch its own check (C08). |
| I9 | Which parts are yours and which the agent's? | Be ready to say. |

## Minor (cheap fixes)

| # | Flag | Zach |
|---|---|---|
| M1 | Fig. 1B shows "(C15)", an internal ID. Remove it. | |
| M2 | Fig. 1C's legend "best possible (chance)": "chance" reads as random guessing. Make it "best possible". | |
| M3 | Fig. 1C says "dead floor", the text "default floor". Pick one. | |
| M4 | Fig. 1C's "not run" (the first model at 15 cm) is unexplained. | |
| M5 | Brier scores above 1 confuse without the range: restore "2 is certain and wrong" (cut in v5 to fit). | |

**Checked, no change:** 1.16 − 0.63 = 0.52 is rounding (1.156 − 0.634); 181 drops is 30 per group, one with 31; the
eight references exist. **Already decided:** Fig. 1A's "mutation testing" label (L1, keep).

## v6 written (2026-10-25)

`checks-that-can-fail-v6.html` holds C1, C2, C3 and C5–C8 as accepted. C4, the public repo, waits for the link. v5
stays as it was, superseded. Figure 1 is `fig1_v6.png`: the hard-floor row is the 0.31 bounce at every height
(0.48 / 0.68 / 0.69), and C2's labels are "first model (start bug)" and "start fixed, default floor". C3's numbers
were recomputed from `surrogate.py` (seed 7): 10 held-out designs truly clear 60%, and the gate accepted 3, sent 6 on
and wrongly rejected 1.

**Trims to fit.** Zach to check:
- Aim 2 (C6 made shorter): "MuJoCo for mechanisms and the forces behind half the pilot's escapes [3]"; "run on HPC";
  "send cases it is unsure of".
- Aim 3: "such as a sensor mast"; "AI agents alone against agents with…"; "with the sponsor's records as the
  conventional baseline"; "time from finding to verified change"; "whether the surrogate's uncertainty holds".
- H4: cut "During the pilot, 17 more findings were logged as they happened, with commit times." The cold reader asked
  why they weren't reported. C3 needed the line on page 2.

**Fit.** `pagefit.py --print`: 0.11 / 0.22 / 0.15 in. `checks-that-can-fail-v6.pdf`: 3 pages, from `pagefit.py --pdf`.
Before the trims, page 3 was over by 0.24 in and page 2 had 0.04 in.

**Still open:** M1, M2, M4 and M5 (figure and wording); C4's link once the repo is public; an optional clause in H3
naming the next fix (a livelier slow bounce), if room is found.
