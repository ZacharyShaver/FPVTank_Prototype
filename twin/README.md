# The real twin

Printed parts that test the sim's numbers against the real robot, so the sim can be realigned from what they show
(2026-11-03: a week of finding sim-vs-reality gaps before more search work). `tools/config.py` has the paths
(`TWIN`, `TWIN_OUT`); `twin/out/` is untracked.

## The Trainer's tub (`trainer_tub.py`), print 1

This is the sim's own housing for the inside parts, printed as drawn. Every search design carries the Trainer's parts
where this tub holds them. It's chassis-v2/rugged.py's `tub()` with wheels, as trainer.py builds it, and had never been
printed. The only change: two loose turret-deck ledges that float above the tub's top are left off.

```
python twin/trainer_tub.py      # twin/out/print/trainer_tub.stl, picture twin/out/trainer_tub.png, checks
python twin/tub_view.py         # twin/out/tub_view.html: the tub and its parts in 3D (the "Trainer Tub Fit" artifact)
```

- **Size:** 276 x 140 x 50 mm, floor down.
- **Print:** 10h23m and 236 g of PLA, with Zach's normal settings. Supports go in the belly tunnel and the aft ramp.
- **Checks:** Zach's parts placed where the sim puts them touch nothing. Each check has a control that reads nonzero.
  His ESC is placed at his caliper size, 45 x 24 x 34. It fits the 26.5 bay with 3 mm to spare, so the sim's 18 mm
  guess didn't matter here.

**Room round each part, from the sim:**

| Part | Room |
|---|---|
| Packs | 0.5 mm to the wall and 1.0 mm to the tunnel: 1.5 mm of play in all |
| ESCs | 0.5 mm to the wall, 3.0 mm to the tunnel |
| ESC length | 0.5 mm between its two stops (his 45 mm ESC); the sim's own 46 mm ESC overlaps the forward stop by 0.5 |
| Pi stack | stands 5.3 mm over the tub's top (the carapace covers it in the sim) |
| Pi and PCA | sit loose on the tunnel roof: the tub has no mounts for them; the Pi's 5 mm TPU isolators\* aren't printed |

**To record when the parts go in:**
- does each part go in, and how tight;
- where the leads go;
- whether the T-plugs reach between each pack and its ESC (they sit end to end, with only a 1.5 mm stop between);
- what has no room.

**What it showed (Zach, 2026-11-07, with a photo of the parts in):**
- Every part goes in. Nothing is tight. The packs and ESCs fit "well enough with a bit extra room".
- Nothing holds anything in place. That's fine for this test print; the next tub needs holds.
- The back is "pretty much empty". In the sim it's the power bay (x -142 to -91 here): two UBECs, the alarm, the Pi
  switch, the INA219 and the wifi dongle. On the bench it holds mostly leads.
- "The bed is probably too large": the tub is longer than its parts need.
- Not answered yet: where the leads go, and whether the T-plugs reach.

The same day Zach capped the search's bodies at 250 mm (body and wheels; the claws and the tail don't count), and took
the head out of the body box as its own module, free to move (`docs/decisions.md`). With the head in, the parts span
270 mm and a 250 mm body would have cost the back 26 mm (superseded). Without it they span 239 mm, so a 250 mm box
holds them as laid out.

## Holding the parts in (`retention.py`, 2026-11-07)

Zach: the brain box "has to be able to be dropped and rolled around without parts falling out of place", tested in
MuJoCo. `python twin/retention.py` drops the box 40 times from each of 0.3 m and 1 m, at random orientations and spins up
to 6 rad/s. Each loose part is a free body at its mass and print 1's clearances. A part is out of place when it ends
more than 3 mm from where it started, in the box's frame. The box hits hard ground with no tyres, which is harsher than
the robot will see.

| Variant | Out of place, of 80 drops | Lid load (90th pct) |
|---|---|---|
| Print 1 as it is (the control): open top, nothing holds | Pi stack 80, PCA 79, ESCs 57-59, packs 19-25 | - |
| A lid screwed on, nothing else | Pi stack 79, PCA 79, ESCs 45-49, packs 15-16 | 2,700-4,400 N |
| Bays walled to the lid, stops at both ends, Pi and PCA on standoffs, TPU pads under the lid | ESCs 13-19 (3 mm of side play), packs 0 | 3,100-5,200 N |
| **Fitted:** the same, the ESC bay narrowed to his 24 mm ESC (0.5 mm) | **none: every part within 1.6 mm** | **about 500 N** |
| **Friction fit** (Zach's idea, `pibox`): fitted, but the Pi stack and PCA loose in pockets 0.3 mm bigger all round, on TPU pads, the lid's TPU pads pressing them down; no standoffs | **none: the Pi within 0.5 mm, the PCA 0.7** | about 530-600 N |

So the mechanism is fitted bays (0.5 mm round every part, a stop at both ends), the Pi and PCA on standoffs or in
friction-fit pockets, and a screwed lid whose TPU pads press everything down. The friction fit is modelled with the Pi
stack as a box: the real pocket grips the board's edges and port block, and the pads have to miss the fan and the
Dupont plugs on the header extensions. Print 1's ESC bay is 26.5 mm wide for the sim's 18 mm ESC; his
is 24. The standoffs are modelled as rigid: their screws aren't tested. The lid's 500 N is spread over its screws and
is a hard-ground figure.

## The Pi's box (`pi_box.py`, 2026-11-08)

The friction box from Zach's last robot, ready to go into the brain box: the Printables `rpi5 base` with its rings bored for
the HAT kit's screw heads, and his updated lid with its GPIO notch moved over the pins, so the whole header comes through. Zach has the old one printed, whose
notch covers pins 1 to 16 when the clips latch; nothing is queued to print. The numbers are in `docs/decisions.md`.

```
python twin/pi_box.py      # STLs in twin/out/print/, the checks, twin/out/pi_box_view.html (the "Pi Box" artifact)
```

- **Source files:** copy `rpi5 base.STL` and `rpi5 lid.STL` into `reference/downloads/rpi5-case/`. They stay untracked: the
  licence isn't recorded.
- **Outputs:** `pi_box_base_bored.stl` and `pi_box_lid_over_header.stl` (the ones to use), `pi_box_ring_test.stl` (the base's
  bottom 9 mm, to test the seat: 33 min, 17 g in draft), `pi_box_base.stl` and `pi_box_lid_as_printed.stl` (the comparisons).
- **Mesh report:** the base is watertight but not manifold, as downloaded (54 edges at z 28.5), and stays so when bored. Zach
  printed it fine. It won't load as a valid exact solid, so the rings are widened by moving their vertices; the ring test sits
  below that height and passes.
- **Ring test, printed 2026-11-08:** Zach, "perfect fit, the little button to reset it even matches right on the tab to press
  it". So the 4.75 bores and 6.75 rings stand.
- **Guesses:** in `GUESSES` in `pi_box.py`, and listed on the page.

## A modular floor (`grid_eval.py`, 2026-11-08)

Zach's idea: one base, with a small holder for each part, like Gridfinity. `python twin/grid_eval.py` fits his parts on a grid and
slices real pieces of both kinds; `python twin/retention.py frames frames_open` drops them; `python twin/grid_eval_page.py` writes
`grid_eval.html` (the "Modular Floor" artifact). Not decided yet.

- **Real 42 mm Gridfinity:** on one floor with the packs on the walls it doesn't fit (29 cells needed, 15 there). I first called that the
  verdict; Zach pointed out layers, moved packs and smaller cells. Two full layers fit, at about 134 mm tall against 78.
- **Other layouts** (`python twin/grid_layouts.py`, checked for collisions with a control): A one level, packs on the walls (the sim's); B
  shelves over them, 217 long; C packs flat under a deck, 107 tall; D packs down the middle, the Pi box sideways. Pick for the first
  robot: A, then D on the same floor.
- **Wires** (Zach's lengths, in the same script, with controls): the ESC's red and black about 90, its yellow and blue 105, the Zeee pack's
  lead 120, Duponts as long as needed. Each pack's lead now has room to leave: A's ESCs went 19.5 back (it had about 3 mm), B's and C's packs 20
  forward, and C's deck came off its ESCs (201 to 249 long). Battery runs: A 71 and 148 of 210 mm, B 72 and 149, C 61 and 109, D 173 and 202.
  So A has 62 to 139 mm a run to tuck away, and D almost none. Yellow and blue get spliced for the two motors anyway.
- **A floor of holes with a low frame round each part fits** (126 mm across): +55 g, against +155 to +202 g, and the parts don't rise.
- **A fit change:** 6-24 min for a frame, 7 h 00 for the tub, both on draft settings.
- **Drops:** with the lid's TPU pads, no part out of place in 80 and every part within 0.5 mm. With no lid (the control), the Pi out of
  place 76 times and the PCA 72. So the lid holds them and the pegs only stop sideways movement. Frames are taken as rigid. **Withdrawn 2026-11-08:** the frames are welded to the floor, and the lid presses through solid TPU columns counted at 1 g each (about 109 g if real, and 39 to 60 mm tall on a flat floor). What holds each part is open.
- **Untested:** peg strength. The worst pack load is about 217 N a peg, 11 MPa with four 5 mm pegs.
- **Test piece** (`python twin/peg_test.py`, the "Peg Test Piece" artifact): a floor patch with hole sizes 5.1 to 5.4, a frame round his ESC,
  and blocks to break, including a loose pin printed lying down. 44 min, 21.7 g on draft settings, no supports. Printed 2026-11-08.
  Zach's results: the 5 mm peg fits best in the 5.1 row, slightly tight with a little snap; 5.2 works, looser; 5.3 and 5.4 fall out when tipped.
  The blocks don't break by thumb. The frame "works pretty well".
- **Frame v2** (`peg_test_frame_v2.stl`, supersedes `peg_test_frame.stl`): his ESC's 45.0 length with no clearance for a press fit,
  walls 12 instead of 17, solid ends, pegs centred on the row. 9 min, 3.4 g. Printed 2026-11-08: "this fits fine enough". Part of what holds
  it in the open is a wire corner wedged against a wall, which the slot wasn't sized for: 24.5 is his 24 plus 0.25 a side, and no wires were
  modelled. How much of 24 is the case and how much is fins or leads isn't measured. The sim's ESC is a plain box, so it can't see this. In the sim (`retention.py frames_short`, press fit
  not modelled), the 12 mm walls and the lid keep every part in place over 80 drops, the ESC within 0.5 mm.

## The whole brain box, assembled (`brain_box.py`, 2026-11-08)

Zach: "alright show a fully assembled brain box now". `python twin/brain_box.py` places every `part_boxes.py` box in a 250 x 139.5 body with the parts still to arrive (listing sizes), the nose camera, the wires at his lengths, walls and a lid, checks it with controls, and writes `out/brain_box_view.html` (the "Brain Box" artifact). One layout to react to. **Not printed, not decided.**

- **The layout:** the Pi crosswise at the back, its header toward the middle. A pack along each wall. Two ESCs down the middle, the PCA on one and the ESP32 on the other, with a 15.5 mm wire lane each side. The IMU between the ESCs. The Pololu and INA219 on the Pi's top, the alarm and BEC slot on the packs' tops.
- **Why the Pi is crosswise:** pack, Pi, pack in one row doesn't land on the 15 mm holes in a 139.5 wide body. The packs would have to be at 45 (too close for the Pi's 70) or 60 (past the wall).
- **It fits:** 43 pieces, no overlaps with each other, the walls or the lid, every floor peg in a hole. All stacks reach 11 units, 77 mm. The body comes to 250 x 139.5 x 82.
- **Wires, on the drawn routes:** drive pack lead 93 of 120, Pi pack lead 87 of 120, ESC red and black 43 and 61 of 90 (before the Y-harness's own length), ESC yellow and blue 83 and 99 of 105 to their splices. **The camera's 200 mm cable is 26 short**, with a guessed 25 inside his Pi box.
- **Balance:** the insides weigh 1197 g against 941 g for the same parts in the sim, centre at x 137 against 151. T3's centre moves about 4.4 mm back and 0.3 down. `noisy.py`'s earlier run read T3 fine at 5 mm back (step 150, upright 1.00, turn 432 against 448); 5 mm forward is the one that hurts. One design; this layout hasn't been simulated.
- **Problems it shows:** his Pi box can't slide out, because its SD end faces the side wall, so it comes out with its sleeve. The stacks reach the lid, so the boards' wires leave only by the side windows.
- **Not drawn:** the real body's shape, wheels and motor pods; how the lid fastens; how the camera ribbon gets out of his Pi box. Set: 265 g, about 10 h 42 one piece at a time.

## The brain box against the sim's designs (`sim_fit.py`, 2026-11-08)

Zach: "now check it against sims see how the size and height fit designs". Balance waits, since "the parts can be moved". `python twin/sim_fit.py` slides the box fore and aft and up and down in each design's hull: geometry only, no gauges read. `cap` samples the 250 mm run's ranges; `screens` samples what the realistic run built.

- **Height isn't the limit.** Every named design is at least 135 mm tall, against 82. Of the capped bodies, the 10th percentile is 113, and those that hold the contents go down to about 104.
- **Finalists:** the contents, inside a 2.6 skin, fit 24 of the 25 realistic and tow finalists; the other misses by 2 mm. The older runs' narrower bodies mostly miss by 1 to 16 mm. The whole 250 x 139.5 x 82 block fits 12 of the 25.
- **None of those bodies meets the 250 mm cap:** they're 328 mm or longer.
- **Under the cap:** random bodies from the 250 mm run's ranges, built with its own cap: 3 of 394 hold the contents, 10 % come within 5 mm, 57 % within 15; the median miss is 14 mm. The 3 that fit are about 249 long. The block as drawn fits none. So length is the limit, because the layout needs 241 and those bodies taper. Moving parts is the way out; moved layouts aren't tested yet. The `screens` sample hasn't been read: its first run filtered out every design (fixed, not rerun).

## The holders as boxes that stack (`part_boxes.py`, 2026-11-08)

Zach: "notice how gridfinity bins stack. thats the concept we are missing. some bins can be as tall as two seperate ones stacked, but each one has a piece on top to stack another like
a lego brick. the pi one does not stack neither does the pac9865. also you could reuse our pac9865 holder". `python twin/part_boxes.py` builds them, checks them with controls, and writes `partbox_*.stl`
and `out/part_boxes_view.html` (the "Part Holders" artifact). `slice` adds draft times and grams; `page` rebuilds only the page. Shown for inspecting. **Nothing printed.**

- **Every height is a whole number of 7 mm units,** Gridfinity's own: ESC 6, Pi 6, pack 8, PCA 5, ESP32 5. So ESC + PCA = Pi + ESP32 = pack + a 3-unit spacer = 11 units, 77 mm, which also leaves the Pi's plugs their guessed wire bend. The ceiling at 11 is not a decision.
- **Every box has a piece on top with the floor's holes,** and pegs in two rows 15 apart under a 2.0 flat bottom. Small boxes' pegs are 30 apart along the rows, so any small box fits any top. Checked with controls: PCA on ESC, ESP32 on Pi, ESC, PCA or a pack on a pack, ESC on ESP32, ESP32 on PCA. Unlike Gridfinity's lip, the top is a plate: 2.0 walls can't hold 5 mm holes.
- **His PCA case goes in unchanged** (`PCA9685_Simple_Case-2.stl` base, `-1-cutouts.stl` lid, in `reference/downloads/pca9685/`). Against the Adafruit model in `reference/pca9685/`, the only contact is a 0.1 mm clamp at the lid's corner blocks; all pins, the terminal and the capacitor pass through its windows. The generic model's right-angle end header would run into the base, so which headers his board has is unconfirmed. The case is exactly 5 x 2 cells of the grid.
- **The Pi's box slides into a tube,** its top a pegboard with a bite for the plugs and slots for air. An ESP32 box fits beside the plugs. It covers some slots, and nothing is heat-tested.
- **Walls 2.0, rounded corners.** The part snaps past 0.4 ridges (my design, untested). Windows let wires and air out.
- **Pegs stay 5 mm** (ESC 6, pack 10, Pi 8, boards 4): at the drop test's harsh loads, the worst root stress is 8.5 MPa on the pack, against a guessed 25 for PLA across layers. The 8 mm option from the first round is dropped for now; its STLs are in `superseded - boxes first round`, with that round's others.
- **The drop sim wasn't run for this:** it holds holders rigid and read 0 of 80 out of place on the thin version, so it can't see flimsy.
- **Set for one robot, with his case:** 233 g, about 9 h 37 one piece at a time. The Pi's tube alone is 54 g and 2 h 21, the only piece needing supports. The ESC + PCA stack, without his case: 37 g, 1 h 20. The ESC box's pegs fit his patch's 5.1 and 5.2 rows.
- **Untested:** the snaps, how the tops fit, the flat bottom's bridge (it prints last, across the opening), how hard six pegs press in, plug heights (they set the 5 units), and any peg pull-out.
- **Printed 2026-11-09:** `stack_test_orca_PLA_1h27m` (ESC box and top, PCA box and top, his case): 1 h 29, Zach: "it went well". Bench test still to come.
- **Printed 2026-11-09:** `rest1_esc_esp` (1 h 01), `rest5_small` (29 min), `rest4_pi_sleeve` (2 h 20).
- **On hold, uploaded but not to be started:** `rest2_packs` (2 h 39, 83 g) and `rest3_floor` (`brainbox_floor.stl`, 1 h 59, 66 g). They carry the joints the bench found wanting (below).
- **Bench, Zach 2026-11-09:** the ESC tops' height is "a tax too tight" (one fits, on the other the ESC is "just barely too tall": the pad had 0.3 of air, less whatever the bridged bottom sagged). The ESP32 box holds nothing: "it can fly around in there and eventually out". Pegs and holes "can warp or have defects rendering it impossible to assemble". See `print_noise.py` below.
- **Was uploaded as five plates:** `rest1` to `rest5`, 8 h 24, 244 g. The Pololu, INA219, IMU, alarm and BEC slot boxes are held back until those parts are here.

## The joint redrawn round print noise (`spring_stack.py`, 2026-11-09)

Zach: "yes draw it no boxes dont have to hold without a lid". One stack, ESC + PCA, on the patch he has. `python twin/spring_stack.py [slice|page]` builds it, checks it with controls, and writes `twin/out/print/spring_*.stl` and `twin/out/spring_stack_view.html` (the "Spring Stack" artifact). **Shown, not printed.**

- **Locate:** two 4.6 pegs on one diagonal, loose in the 5.1 holes. The rest are 4.0 and only meet a crash.
- **Seat:** the flat bottom.
- **Hold:** a soft TPU clip on the stack, squeezed 0.75 by a flat lid, and the same clip under the ESC's top where the rigid pad was.
- **Stop:** squeezed flat after 1.5, the clip's body takes the load. The pegs are still in.
- **Test set:** ESC box, ESC top and PCA box in PLA (26, 9 and 31 min; 30 g), a hoop that stands in for the lid (19 min, 15 g), and `spring_clip_strip_TPU.stl`, six clips in three blade thicknesses. His patch, PCA top, case and ESC are reused.
- **Guessed:** the clip's every number, and its force (about 4 N, half to double). The other boxes and the lid's fastening wait for this test.

## Print noise on the peg joints (`print_noise.py`, 2026-11-09)

Zach's idea, from the noisy copies in `gauges/noisy.py`: print each joint slightly wrong, many times, and see how often it still goes together. `python twin/print_noise.py` does it with geometry and dice (no physics): every peg and hole gets a random error in place and size (sd s), and the box shifts and turns to its best seat.

- **Friction pegs in 5.1 holes:** at s 0.05, four pegs go together 10 % of the time, six 1 %, eight and ten never. At s 0.02 the ten-peg pack box still only 30 %.
- **Loose pegs in 5.4 holes:** at s 0.10, two pegs seat 82 %, ten never. The count matters more than the hole.
- **`spring_stack.py`'s joint** (two 4.6 pegs locate, the rest 4.0): at s 0.10 the ESC box seats 94 %, the pack box 92 %.
- **Not measured:** s on his printer, and how far a hand can press a peg (0.05 guessed). His count of which printed joints went together places his printer in the table.
- **Left out:** warp, leaning pegs, seam blobs. They only make it worse.

## SUPERSEDED: the holders as stacking bricks (`bricks.py`, 2026-11-08)

Replaced by the boxes above before anything was printed.

Zach, on the snap caps below: "set the section heigh much smaller the battery should be multiple boxes high. they should be peg boards on the top of
these to allow stacking. the top should not be a plat with legs but a few blocks on top of things. think like a lego block kinda". `python twin/bricks.py`
builds them, checks them with controls, and writes `brick_*.stl` and `out/bricks_view.html` (the "Part Holders" artifact). `slice` adds draft times and grams;
`page` rebuilds only the page. Shown for inspecting. **Nothing printed.**

- **One joint everywhere:** a 5 mm peg under a brick, in a 5.1 hole in the floor or a 5.1 socket in the brick below.
- **One section is 12 mm**, with half sections of 6: ESC 3 (36 over its 34), pack 4 (48 over its 45.7), and 12 is the wall of the frame he OKed.
- **Three kinds of brick:** a tray with posts (part-specific), spacers (1 peg, 1 socket, 8 x 8, the same for every part), and top blocks with sockets along the top, which land on the part.
- **Heights** before spacers to the ceiling: ESC 42, pack 54, Pi 48, PCA and ESP32 18. Every column can reach a ceiling at 60 (5 sections), and another layer of spacers moves it.
- **The Pi's box stays as it is;** two bars rest on its rim. The plugs reach 57.5, so 60 clears them but not the wires' bend.
- **Stacking example:** the ESP32 on the PCA, on 2-section spacers, tops out at exactly 60 with 21.9 mm over the PCA's plugs.
- **Set for one robot:** 121 g. About 9 h 17 if each brick printed alone; a plate would cut that. ESC stack alone: 10.5 g.
- **Untested:** sockets print mouth down, unlike the floor's holes, and may come out tighter. Peg pull-out. How stiff a column of bricks is. The PCA and ESP32 sizes, and the pack's, aren't calipered.
- The printed frame v2 has no sockets, so it can't take spacers. Layouts A to D are still on hold, and their sizes predate these bricks.

## SUPERSEDED: one holder for each part, with snap caps (`holders.py`, 2026-11-08)

Replaced by the bricks above before anything was printed. Zach stopped the layouts: finish each part's fit and hold first. `python twin/holders.py` builds a tray and a snap cap for the ESC, pack, Pi, PCA and
ESP32, checks them with controls, and writes `holder_*.stl` and `out/holders_view.html` (the "Part Holders" artifact). `slice` adds draft times and
grams; `page` rebuilds only the page. Shown for inspecting. **Nothing printed.** The parts still to arrive wait for their real sizes.

- **Cap:** hooks on its legs click under catches on the tray's outside. A check proves it's locked: pulled up 1 mm, the cap hits the catches.
- **Block height:** 48 over the floor's top, set by the pack (45.7 + 0.3 air + 2.0 plate). As low as they'd go, the others stand 36 to 40. Each piece has
  both caps, except the pack. The Pi's plugs reach 57.5, so a ceiling at 48 needs a hole or hump over them.
- **Pi:** its box stays as it is. A 6 mm frame goes in the floor, and two straps hold the box into it, clear of the notch and the port windows.
- **PCA and ESP32:** plugs stand on the boards, so each cap is a plate on four columns pressing on the board's corners. The ESP32 is upside down, pins up
  (my pick). The PCA's model is the generic one in his Downloads; the ESP32's is a typical board. Neither is calipered.
- **Still open:** a cap only holds a part in its tray. The tray stays in the floor by peg friction until something presses on the cap. The snap is untested.
- **Cost:** 104 g and about 4 h 46 for all seven holders, draft. Caps add 2.55 a side, so layout A's row across goes from 126 to about 142 of 134 mm.
- The ESC's tray is frame v2 plus catches, so the printed frame v2 can't take a cap.

## The Pi's WiFi (`wifi_test.py`, 2026-11-08)

Off the wall, WiFi is the robot's only link, and in July it carried only about 2.6 Mbps with the Pi inside the old chassis
(review C7). `python twin/wifi_test.py "where the Pi is"` pulls data from the Pi for 20 s and logs it to `twin/out/wifi_test.jsonl`;
`--self-test` proves the meter on known rates, with a control. 720p30 took 4.4 Mbps on the cable, so the bar is 6 (picked).

| Pi | Band | Signal | Mean, Mbps | Worst second, Mbps |
|---|---|---|---|---|
| In the open, bench (Zach) | 5 GHz | -57 to -58 dBm | 180-188 | 150 |
| Same, after a reboot | 2.4 GHz | -38 dBm | 41-45 | 30 |
| Inside PLA (Zach) | 2.4 GHz | -34 to -35 dBm | 47-48 | 41 |
| In the box with a pack each side, far end of the driving area | | | not run yet | |

Power save was already off, saved in the Pi's settings. The first two runs were sent over WiFi for certain: the Pi's WiFi
counted 957 MB and its Ethernet port 0. Zach rebooted it with its power button, and it came back on the mesh's 2.4 GHz radio; whether the Pi also moved isn't known.
PLA costs nothing here: inside it, the Pi read no worse than in the open on the same band. These signals are strong, so this is the
easy case. July's 2.6 Mbps didn't come back, and what caused it is still unknown.

## Insides boxes (`boxes.py`): superseded before printing

Superseded 2026-11-03 before printing: Zach chose the Trainer's own tub (above), the sim's housing, over free-standing
boxes. The STLs moved to `twin/out/boxes-superseded/`.

These are the boxes the inside parts sit in, v0, printed to shake out sizing. The parts are laid out as the sim lays
them, adding the walls, clearances and lead room the sim leaves out. There are two kinds:
- **Brain box, 173 x 62 x 32:** the Pi 5 stack with its USB end aft and the end open, and the PCA9685 forward of it.
  - The Pi stands on four rings at its mounting holes; the HAT kit's screw heads drop into them.
  - A window in one long wall leaves the USB-C and HDMI side clear.
- **Side box, 221 x 31 x 48, two of them:** the ESC aft, a 25 mm lead bay for the T-plugs, then the pack, both on edge.
  - The search moves the packs. Here the ESC moves with its pack, which ends the packs-into-ESCs clash.

```
python twin/boxes.py      # STLs + plate to twin/out/boxes-superseded/, picture twin/out/boxes.png, checks
```

The boxes have open tops and flat bottoms, and no mounting yet: that waits for the fit check and the screws on hand.
Every cutout runs out through the top edge, so no supports are needed. Plate: 221 x 140; 4h14m and 166 g of PLA with
Zach's normal settings.

The guessed numbers are in `GUESSES` in `boxes.py`:
- the clearance (0.5 a side);
- the Pi rings (4 tall, 6.5 hole);
- the SD card's overhang;
- the Pi-to-PCA gap (6);
- the room for the PCA's end headers (12);
- the lead bay (25);
- the PCA's size;
- the HAT's 16 mm standoffs.

**Not in yet:**
- **Parts not bought:** the Pi regulator, the arm UBEC, the INA219, the WiFi dongle, the alarm and the switches. They
  get their own small box once bought.
- **The third pack:** the power plan in HARDWARE.md feeds the Pi from its own pack C, but the sim carries only two packs.

## Fit cups (`fit_cups.py`): superseded before printing

Superseded 2026-11-03 before printing: Zach wanted the boxes the parts sit in inside the robot (above), not a test cup per
part. Kept as a per-part size check.

One open cup per inside part Zach owns, at the size the sim gives it (`gauges/body.parts()`, the Trainer's parts that
every search design carries). The motors and the head are left out: the head's parts are already real.

```
python twin/fit_cups.py      # cups + plate STLs to twin/out/fit-cups-superseded/, picture twin/out/fit_cups.png, checks
```

- **Cup:** the sim's box plus 0.3 a side, a 3 mm rim, and four corner posts as tall as the sim says the part is. The sides
  are open above the rim, so leads come out anywhere.
- **Floor:** runs 22 mm past the box, with a raised ring every 5 mm (double at 10 and 20) counted from the sim's box
  face. A plug or lead's protrusion reads straight off the rings.
- **Each label** is the size the cup was built to, engraved on the floor.

| Cup | Size built (X x Y x Z, mm) | Where the number comes from |
|---|---|---|
| Pack | 141 x 26 x 45.7, on edge | Zach's model's box (`LeftBattery.stl`) |
| ESC | 45 x 24 x 34, on edge | Zach's caliper (2026-10-11). **The sim still has 46 x 18 x 34** |
| Pi 5 stack | 89.1 x 57.2 x 27.2 | Pi 5 + cooler (his model), M.2 HAT+ on 16 mm\* standoffs, Hailo-8L |
| PCA9685 | 62.2 x 25.7 x 12.4 | Adafruit's size\*; his is a generic clone |

\* = a guess. The 0.3 mm clearance is a pick, not a tested rule.

**What to record for each part:**
- does it drop in, go in tight, or not go in (and which way it's too big);
- how far it stands over the posts;
- how far its plugs and leads stick out, read off the rings.

That's the gap list the sim gets realigned from.

**Not printed** (not bought yet): the Pi's regulator, the arm UBEC, the INA219, the WiFi dongle, the LiPo alarm and
the switches.

**Known layout gaps** (from the sim, not this print): the sim packs the parts 0.3–1.3 mm apart with no room for walls
or leads. Those gaps are PCA to Pi 0.3 mm, ESC to pack 1.0 mm, Pi to the right pack 1.3 mm. Separately, the search's
pack shift drives the packs into the ESCs.

**Plate:** `plate_fit_cups.stl`, 282 x 179 mm, laid out by hand because Orca's arrange left two cups off. Sliced with
Zach's normal settings, not draft (the fit is the point): 2h51m, 102 g, PLA, no supports.
