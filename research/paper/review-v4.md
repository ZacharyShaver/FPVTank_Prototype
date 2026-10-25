# Review of draft v4 (2026-10-25)

Draft v4 as of 6943d2e, read cold as a reviewer would. Each flag opens with the question for Zach; his call goes in
the last column when he makes it. Spare room in print: page 1 0.30 in, page 2 0.22 in, page 3 0.15 in (a line is
about 0.19 in).

**Verified, no flag:** Pace (sets 1–11, Sep 27–Oct 12; the last four Oct 9–12); 10 cases and 7 false passes before
the pilot, 19 / 13 / 9 now; ten checks (K01–K10); 16 of 26 at the bench and 10 of 26 before printing.

## Page 1

| # | Flag | Cost | Zach |
|---|---|---|---|
| 1.1 | **Summary: say "each kind of check" instead of "every check"?** "Every check was itself tested" is too strong: the registry audit flags K02, K14 and K33 for having no working control. | none | **accepted** (2026-10-25) |
| 1.2 | **Summary: "This plan makes it routine": routine what?** "It" reads as check failures. Proposed: "This plan makes testing the checks routine." | +3 words | **accepted** (2026-10-25) |
| 1.3 | **§2 Finding: date the ten?** The Summary says 19; two paragraphs later "Ten recorded cases" has no date. Proposed: "Before the pilot, ten recorded cases…" | +3 words | **accepted** (2026-10-25) |

## Page 2

| # | Flag | Cost | Zach |
|---|---|---|---|
| 2.1 | **"Each changed how that kind of check is done" is true for 15 of 19. Reword, or fix the four first?** C16–C19's fixes are all `open` in `check_failures.csv`. Proposed: "…a control or a second agent; all but the newest four have changed how that kind of check is done." | +6 words | **reword accepted** (2026-10-25) |
| 2.2 | **H3: name the naive guess?** It is "each body stays on the face it was dropped on", a certain guess, so it scores 1.29, worse than an even guess over the five rest states (0.80). A reader who knows Brier scores sees 1.29 and suspects a straw man. The model beats the even guess too. Proposed: "beat a guess that each body stays where dropped, 0.58 against 1.29". | +5 words | **accepted** (2026-10-25) |
| 2.3 | **H2: rewrite the sentinel sentence so it says what happened?** "Sentinel runs" is never defined, and "hidden" doesn't say hidden from what. The surrogate never sees friction; the registered control cut friction to 0.4× and ran 8 spot-check simulations to see if they'd disagree with it. They didn't (0 of 8, the same as at normal friction): friction moved the answer by at most 4 points, below what 8 checks of 200 tumbles can see (`PROTOCOL.md` H2). Proposed: "A registered control failed: 8 spot-check simulations could not see a friction change the surrogate is never told about, which moved the answer by at most 4 points." | +7 words | **accepted** (2026-10-25) |
| 2.4 | **Fig. 1B: "1,000-drop reruns" → "1,000-tumble reruns"?** They are simulated; elsewhere in the paper "drops" are the physical ones. Caption and legend. | none | **accepted** (2026-10-25) |

## Page 3

| # | Flag | Cost | Zach |
|---|---|---|---|
| 3.1 | **Risks, Agent errors: "passing its mutants" is backwards. Fix?** A change doesn't pass its mutants; its checks must catch them. Proposed: "No change is accepted until its checks catch its mutants and a person has reviewed it." | +3 words | **accepted** (2026-10-25) |
| 3.2 | **Aim 1: "when they reach a set mutation score": "they" now points at the mutants. Back to "its checks"?** The v4 trim caused it. | +1 word | **accepted** (2026-10-25) |

## Low priority

| # | Flag | Cost | Zach |
|---|---|---|---|
| L1 | **Fig. 1A's axis label "mutation testing (8)": all 22 faults are mutation testing; "invented (8)" is exact.** Your call from today, so only if you want it. | none | keep as is (2026-10-25) |

## v5 written (2026-10-25)

`checks-that-can-fail-v5.html` holds every accepted change above. v4 stays as it was, superseded.

**Changed while fitting.** Zach to check:
- 1.1 dropped "itself": "each kind of check was tested".
- 1.2 reads "This plan makes such tests routine." "Testing the checks" left "routine." alone on the Summary's last line.
- 2.3 reads "8 spot-check simulations missed a friction change the surrogate never sees, which moved the answer by at
  most 4 points." It means the same and is 5 words shorter.
- 2.4 is in the caption only. Panel B's legend label is never drawn, so the figure stays `fig1_v4.png`.
- H3 trim, so page 2 keeps its margin: "Each prediction gets a Brier score [6]: 0 is perfect (Fig. 1C)." It was "is scored by
  its Brier score [6]: 0 is perfect, and lower is better". Fig. 1C's title still says lower is better.

**Fit.** `pagefit.py --print`: 0.30 / 0.22 / 0.15 in, the same as v4. Page 2 read 0.04 in before the H3 trim.
`checks-that-can-fail-v5.pdf`: 3 pages, from `pagefit.py --pdf` (Edge's Save as PDF engine).
