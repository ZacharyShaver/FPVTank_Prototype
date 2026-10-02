PAN COIL TEST PRINT, SET 4 -- 2026-10-02 (sets 3 and 2 below, still the base of it)
The 360-degree pan base under the v2 head, and the cradle that bolts onto it.

SET 4 = WIRE ROUTE, ROUND 2: REPRINT base.stl AND drum.stl (both on plate_pan_coil_set4.3mf)
  The tilt servo's wires get their own rolling loop in the pan coil, under the ribbon, so nothing is taped
  to the ribbon anywhere. wire_route_r2.png shows before and after.
    - The base's floor drops 4.3 mm and a lane 3.5 tall opens under the ribbon, with its own wall at
      r 21 (the ribbon's is 18): a 9 mm gap, so the wires' moving U is about 3.6 mm radius.
    - A fixed 0.8 mm shelf separates the two. The ribbon now sits on the shelf, at the same height as
      before.
    - The drum reaches 3.9 mm further down: its face is the lane's inner wall. A 5 mm hole runs from the
      bottom of the drum's hole, at the side opposite the ribbon's slot, down through the drum's core.
      It comes out of the drum's face at the lane.
    - The wires leave the base through a 5 mm hole in a boss at -145 deg (between the ribbon's exit and
      the -X side), 3 mm clear of the ribbon's slot.
    - Nothing below the floor moved: KEEP the floor plate, both gears and the tab block. The barrel's
      bearing sleeve got longer (6.6 mm, was 5). The drum now stands 0.4 mm off the floor; set 3's
      touched it.
  THREADING THE WIRES (round 2), with the drum OUT of the base:
    1. Bare ends (shells off) down the drum's hole, beside the ribbon, into the hole at the bottom on
       the side away from the ribbon's slot. Out through the drum's face at the bottom.
    2. From inside the empty base, push the bare ends out through the exit hole in the boss.
    3. Leave about 74 mm of wire in the lane: the same 540 deg of travel the ribbon has. Wrap it once
       around the drum's bottom, the opposite way to the ribbon's wrap, so it rolls the way the
       ribbon does. Lower the drum in while drawing the slack out of the exit hole.
  Superseded: set 3's base and drum ("superseded - set 3 before wire lane/"). Don't print them.
  Tool bodies for reference in Fusion: wire_route_r2_tools_for_fusion.step (CUT_base_wire_lane,
    CUT_drum_wire_hole_5mm, CUT_base_wire_exit_5mm; pan frame, Z 0 at the deck top).
  Checks: head-v2/checks/wire_route.py, round 2. The 4.4 mm probe passes the drum's hole and the base's
    exit with 2.45 to spare. A 2.8 bundle clears the lane all the way round. Walls round both holes are
    1.0+ away from their mouths. Each check has a control that has to fail. Pan checks: 0 clashes, every
    assembly step clear, gear play 1.9 deg. Your MG90S still fits.
  Guesses: the lane's 3.5 height (for three ~1.3 jumper wires twisted loosely together); the 74 mm of
    wire in it; the 0.4 mm the drum stands off the floor.

WIRE ROUTE, ROUND 1 (2026-10-02): REPRINT cradle.stl, PRINT stub.stl (both on plate_wire_route_r1.3mf)
  The tilt servo's wires get their own way down, off the ribbon. wire_route_r1.png shows before and after.
    - The servo's own lead and plug stay inside the ball, coiled loosely behind the camera board on the
      -Y side (about 17 cm3 free there). Plug three Dupont jumper wires into the servo's plug (tape or
      clip the joint so it can't pull apart). Only those wires run down.
    - stub.stl replaces BOTH the -Y axle and the -Y end cap. Your ball turns on it; it doesn't turn.
      Your ball's socket is r 10.04 and the old axle r 9.95 (0.09 gap), which is why that pin never
      fitted. The stub is r 9.80: a 0.24 gap. Its ring fills the empty bearing seat. 3 x M2 x 6 through
      the cap's old holes hold it, and also line its wire hole up with the cradle's.
    - The wires run through the middle of the stub, right on the tilt axis, so tilting twists them half a
      turn instead of bending them. Then down a 5 mm hole inside the cradle's -Y wall, past the drum
      screw (below its head), into the plug chute's mouth and down the drum's hole beside the ribbon.
      Where the wall was too thin for the hole, a 1.6 mm ridge grows on its outside.
  THREADING: slide the plastic shell off the END YOU THREAD (each shell has a small tab you lift with a
    needle; the bare metal pin stays on the wire). The 5 mm hole takes three wires with one bare pin
    going through at a time. The male ends stay in the ball, plugged into the servo. Push the shells
    back on at the bottom.
    Order: cradle bolted to the drum, ball seated, as before. Feed the bare ends from inside the ball,
    out through the empty socket and collar, into the hole at the bottom of the collar (at about 7
    o'clock seen from -Y), down until they appear in the chute's mouth, then down the drum's hole. Slide
    the stub in over the wires (its hole faces the same way once the screws line up), M2 x 6 x 3.
  WIRE LENGTH: about 24 cm from the servo plug to the bottom of the base, plus slack and the run to the
    board. 30 cm jumpers are too short to have any spare: use 40 cm or join two.
  ROUND 2 is set 4 (top): the wires' own lane in the pan coil. With set 3's drum and base, the wires go
    out the drum's side slot loose beside the ribbon, which is only good for testing the tilt.
  Superseded: the cradle you have ("superseded - cradle before wire route/"), the -Y axle and the -Y end
    cap. Don't print them.
  Tool bodies for reference in Fusion: wire_route_r1_tools_for_fusion.step (CUT_wire_hole_5mm,
    ADD_wire_conduit, head frame).
  Check: head-v2/checks/wire_route.py. A 4.4 mm probe (bare pin beside two wires) rides the whole way:
    2.4 mm of clearance at the tightest. Thinnest wall round the hole 0.6 (beside the cap's flange gap),
    1.5 in the ridge. Stub vs cradle and vs your ball 0.00 mm3. Each with a control that has to fail.
  Guesses: the 0.24 running gap (if the ball's stiff on the stub or rattles, say which); the 5 mm hole
    (sized for 26-28 AWG jumper wire, ~1.3 across); the coil fitting where it's drawn.

SET 3 (superseded by set 4's base and drum; its tab block stays): base, drum, tab_block
  Built on your MG90S model (2026-09-28), the one you've been using. The pan servo was a datasheet box
  with nothing past the case face and the tabs in the wrong place, so the servo didn't fit.
    - Tab shelf where your model's tabs are: their shaft-side face 1.9 below the case face (was 6.5).
      Tab screws 26.86 apart.
    - The 15 x 12.2 block on the case face (6.0 tall) and the shaft (tip 10.0 past the face) now have
      a pocket, and a channel out through the side window, so it slides in.
    - The gear plane sits 0.5 under that block: 5.6 mm lower than set 2. The drum's barrel is that
      much longer, and the gear bay that much deeper.
    - The drum's side slot is 1.5 mm taller, so your 14 x 8 servo connector turns from the drum's hole
      into it. No filing.
    - NEW PART, tab_block.stl: the servo's +Y tab (the window end) had no plastic under it, so its
      screw bit air (set 2 too). After the servo is in, slide the block in through the window, rails
      in the two grooves, until it stops under the tab. Then drive that tab's M2 x 6 down through the
      tab into it (3 mm of thread). Same screw as before, nothing new to buy.
  KEEP from set 2: floor, small gear, input gear (same shapes, they only sit lower).
  Superseded: set 2's base and drum ("superseded - set 2, servo didn't fit/"), and set 3's first cut,
  made from the measured tilt-servo numbers before your model arrived ("superseded - set 3 first cut,
  datasheet servo/"), and set 3's base before the tab block ("superseded - set 3 before tab block/").
  Don't print any of them.
  Checked with your MG90S mesh itself (head-v2/checks/pan_servo_fit.py): seated 0.00 mm3 against the
  base, drum, gears and floor, and clear the whole way in through the window. Both controls read
  nonzero. Pan checks: 0 clashes, every assembly step clear, gear play 1.9 deg.
  Horn: with its hub against the block's face, the horn's arms land 2.5-4.5 mm below the input gear's
  top face (1.5 of roof under them). Re-cut the placeholder pocket in Fusion to that.

The 360-degree pan base under the v2 head, and the cradle that bolts onto it.
Still a first test: this print is for finding what doesn't fit.

NEW CRADLE (2026-09-27, later) -- SUPERSEDED by the wire route above, which keeps all of this
  The plug-chute cradle, its plate, picture and STEP are now in "superseded - cradle before wire route/".
  The cradle before it is in "superseded - cradle before plug chute/". Don't print from either.
  Why: the tilt servo's plug couldn't get down into the drum, and the ribbon had no clean way in either.
    - The groove never opened into the ribbon track behind the ball; the two only touched at a corner.
    - A rigid plug can't turn the groove's 6.3 mm bend, at 3 mm or 4 mm thick.
  What changed:
    - The ribbon groove is 4 mm thick (was 3). It keeps its curve, so the ribbon still lands on the
      drum's centre line, the only place the 18 mm hole is wide enough for 16 mm of ribbon.
    - A straight 4 mm chute, 22 wide, runs from the bowl's floor behind the ball, 50 degrees down
      toward the front, into the drum's hole. It opens the groove to the track at every width.
  How it goes in: bolt the cradle onto the drum first (as before). With the ball out and held above,
    drop the servo plug into the chute from the bowl. It comes out in the drum's hole; take it on out
    through the drum's side slot. The ribbon's free end goes the same way. Once the ball is seated, the
    ribbon lies in the curved groove.
  YOUR PLUG (14 x 8): the cradle passes it, and set 3's drum does too (its side slot is 1.5 mm taller).
    On set 2's drum it jams at 3.0 thick, where the drum's hole turns into the side slot.
  Tool bodies, for reference in Fusion: cradle_chute_tools_for_fusion.step (CUT_cradle_plug_chute,
    CUT_cradle_groove_4mm, in the head's frame).
  Check: head-v2/checks/plug_passage.py (slides and turns the plug through; the old cradle is its control).

WHY SET 2
  Set 1 couldn't be put together. The small gear was moulded onto the bottom of the drum (22.6 mm
  across) and had to pass through the well's 10.5 mm hole and the gear bay's 17.2 mm top hole. The
  gear bay was also a closed box, so the big gear couldn't get in either. What changed:
    - the small gear is its own part, pushed onto the drum's shaft from below, one M3 screw;
    - the well and the gear bay are ONE part now (base.stl): there was nowhere on the well to screw
      the bay to;
    - the gear bay's floor is a separate plate (floor.stl), so both gears go in from underneath.
  Set 1's files are in "superseded - set 1, can't assemble/". Don't print from there.

  Fixed in the same pass, before printing (all three also sat in set 1):
    - the gears were drawn touching on both sides of every tooth: zero play, so they'd have jammed.
      The small gear is now 0.3 mm smaller all round (about 1.9 degrees of play at the head as
      drawn; expect less once printed). Your set 1 input gear still meshes with it;
    - the bearing's inner ring (it turns with the drum) sat flat on the fixed ledge and would have
      dragged. The ledge now has a 0.4 mm deep recess under the inner ring, so only the outer ring
      sits on it;
    - the bearing fits were drawn at exactly 58 and 45 mm. Now the seat is 58.1 and the drum's hub
      44.9, the same as the tilt bearings' seats. The rounded corner where the bearing seats against
      the drum's top disc is now a sharp step, so the bearing sits flat against it.

PRINT (plate_pan_coil_set2.3mf has these four, each already turned the way it prints)
  base.stl         the well and gear bay in one piece. Needs supports.
  drum.stl         no gear on it now; its shaft ends in a D-shaped stub (a round stub with one
                   flat side, so the gear can't spin on it).
  floor.stl        the gear bay's bottom plate.
  small_gear.stl   the drum's gear. D-shaped hole; the thin bottom web goes on the bed.
  pan_coil_plate.png is the plate; pan_coil_assembly.png shows every part pulled apart the way it
  goes in.

UNCHANGED FROM SET 1 (keep what you printed)
  input_gear.stl (a copy is here too). The cradle was unchanged too, until the plug chute (top).

BUY / HAVE
  1 x 6809 bearing (45 x 58 x 7)           on the drum, sits on the base's ledge
  1 x MG90D servo (180 degree)              drives the input gear, 2:1 step-up = 360 degrees at the head
  3 x M3 x 12 socket head                   cradle onto the drum, from above, BEFORE the ball goes in
  1 x M3 x 8 button head (NEW)              small gear onto the drum, from below. Low head: a socket
                                            head would stick 1 mm out under the base
  4 x M2 x 6 (NEW)                          floor plate onto the gear bay, from below
  2 x M2 x 6                                the servo's tabs
  1 x M2 horn screw, ~8 mm                  stock horn screws are likely too short (1.5 mm roof)
  1 x 6704 bearing (20 x 27 x 4)            the head's +Y tilt collar (the -Y one is now the stub)
  3 x M2 x 6                                the stub, through the old cap holes
  3 x Dupont jumper wire, 40 cm             the tilt servo's run (see WIRE ROUTE)

ASSEMBLY ORDER (checked: each part slides in along this path without hitting anything)
  1. Servo into the base through the side window, shaft pointing down. Slide the tab block in behind
     it under the window-end tab. Two M2 x 6 through its tabs (the window-end one into the block).
  2. Push the 6809 bearing onto the drum from below, up to the wide disc at the top.
  3. Drop the drum into the base from above. Its shaft comes out the bottom of the gear bay.
  4. Put the horn in the input gear's pocket. Push the gear up from below until the horn slides onto
     the servo's shaft. Drive the horn screw up from underneath.
  5. Small gear up onto the drum's D-shaped stub. Turn the drum until the flats line up; wiggle it
     so its teeth slide in between the big gear's teeth. M3 x 8 button head up the middle.
  6. Floor plate on, 4 x M2 x 6.
  7. Ribbon, then the cradle, as before (below).

HOW THE RIBBON GOES (decided 2026-09-27, unchanged)
  Down the cradle's groove (4 mm since the plug chute), straight down the middle of the drum's 18 mm hole, then ONE soft 45-degree
  fold at the drum's side slot turns it on edge to wrap the drum. Make that fold by hand with the drum
  out, where you can see it; nothing gets threaded after it's folded. No twist anywhere.
  Keep the connector ends straight. No folds in the tilt loop behind the ball or in the coil.

CLOCKING: bolt the cradle on with the drum's side slot facing FORWARD (the camera side). The three bolt
  holes let it go on three ways round; only that one lines the slot up with the ribbon.

STILL GUESSES -- check on this print
  - The input gear's horn pocket is a placeholder size. Re-cut it in Fusion with your real horn model
    (zero offset, 1-2 mm roof), the way you did the others. When you do: the servo's shaft must end
    inside the horn. The placeholder pocket is 0.8 mm shallower than the shaft stand-in the checks use.
  - The small gear's D-hole is 0.15 mm looser than the stub all round (the slide rule). If it's
    sloppy or won't go on, say which.
  - Gear play: 0.3 mm off the small gear is a guess at how fat your printer makes gears. If they
    bind, or the head wobbles more than you like, say which.
  - Bearing: if the 6809 won't press into the base or onto the drum, or falls out, say which.
  - Ribbon thickness 0.2 is assumed. The groove's tightest bend is 6.3 mm radius, safe even at 0.3.
  - The servo plug's length and width aren't calipered: the checks use 13-16 x 8 x 3 (see the top).
  - Where the base screws down to the tank body is still open. Nothing on this plate fixes that yet.

WHAT TO LOOK FOR
  - Assembly: does each step above go the way it says?
  - Gear pair: servo holding still, how much the drum rocks by hand (backlash; ~1 degree expected).
  - Drum turning on the bearing: smooth over the whole travel, no rubbing.
  - Ribbon: roll the drum to both ends of travel and look at the loop. Test with a SPARE ribbon first.
  - Cradle on the drum: the 3 bolts reach and pull it down flat; the ribbon drops through clean.

Rebuild: head-v2/fixes/pan_print_set.py (its docstring lists the generator steps to run first), then
  head-v2/fixes/cradle_chute.py for the cradle's plate, tool bodies and picture.
Checks: head-v2/generator/generators/pan_coil_b_check.py (and --broken, the negative control).
3D fit view, set 2 (Pull apart shows the assembly): https://claude.ai/artifact/NKDFgbD3YuAp3xg7JZudVj
  Rebuild: head-v2/fixes/fit_view.py
