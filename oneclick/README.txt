One-click tests for the realistic run (capability_real, started 2026-10-31 16:40, refines until 07:00 on 1 November,
then reads its winners on the full gauges, about an hour). Double-click a .bat; each opens a window, runs, opens what
it made, and waits for a key. They all run gauges\tomorrow.py; its outputs go to gauges\out\capability_real\tomorrow\.
Any of them asks before sharing the cores with the run if the run is still going.

0_status    seconds   How far the run is, its best so far, and why it refuses designs (motor into a part, a drive
                      too weak, a flipper off the body ...). Fine any time.
1_results   1-20 min  The winners on the full gauges and the run's page (opens in the browser). If the run's own
                      finals didn't finish, it runs them first (about 15-20 minutes).
2_repeat    ~15 min   The trust test: the best designs (and T3) read three times with different random tries. A
                      gauge marked "<- moves with luck" can't tell designs apart by that much. The step should
                      now hold within about 5 mm (it swung 50-150 mm before 2026-10-31).
3_onepiece  ~30 min   The best three grown into one printable piece (the unibody grower, GPU) and read again,
                      beside the realistic build. Close readings mean the search's cheap build can be trusted for
                      that design. Pictures of both in onepiece.png.
4_film      ~5 min    The best two and T3 on a 150 mm step (side view) and spinning round in place (from above):
                      steps.mp4, turns.mp4.
5_checks    ~5 min    Every check from 2026-10-31 with its control: the real build (motor fit, flipper mounts,
                      weight), the pooled step rule, parts on the body, the stress solver, the one piece's mesh.
                      Should end "5 of 5 checks pass".

Good order tomorrow: 0_status, then 1_results once the run says finished, then 2_repeat and 3_onepiece.
