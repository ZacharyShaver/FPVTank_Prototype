PRINTING (2026-10-12) -- set 11, the base only:
    plate_pan_coil_set11_base.3mf    the base on its own, supports ON (none land inside the can)
    G-code: head-v2/out/gcode/pan_set11_base_orca_PLA_1h21m.gcode (39 g)
  Everything else is set 10's and stays: drum, small gear, floor plate, the 6704 and three M3 x 16, set 9's input gear
  and horn, the tab block, the cradle. The shelf ring is no longer a part. Never print from a "superseded - ..." folder.

PAN COIL SET 11 -- 2026-10-12: the shelf ring back in the base
  Set 10 worked: the pan turned its full sweep. You asked to merge the shelf ring in (it could fall out of its lock
  upside down, and with the wires down the middle it needn't be separate) and to close the old wire hole outside.
  set11.png shows it, cut through the axis and from above.
  BASE (base.stl)
    - The empty wire lane is filled solid up to the ribbon's floor, and the ring's wall stands on it: one piece, no
      rib, nothing overhanging inside the can.
    - The wires' old exit hole and the bump it ran through are gone.
    - The 6704 still drops in from above, through a 27.5 hole in the new floor, before the drum.
  ASSEMBLY: as set 10, minus the shelf ring. 6704 down into its seat; drum + 6809; input gear + horn; wires down the
    axis; small gear + three M3 x 16 from below; floor plate.
  GUESSES: the 6704 drops through the 27.5 hole freely; the ribbon's inner wrap doesn't drop into the 1.75 gap round
    the drum. The ribbon's own wall is kept as it was.

PRINTED (2026-10-11) -- set 10, two plates, as set 9 had to go (plate B superseded by set 11):
    plate_pan_coil_set10_a.3mf       drum + small gear + floor plate, supports OFF (Orca would fill the drum's bore)
    plate_pan_coil_set10_b_base.3mf  the base on its own, supports ON
  Hardware: one 6704 (20 x 27 x 4) and three M3 x 16 button heads. The 688 and the M3 x 12 on the axis come out.
  Everything else stays: set 7's shelf ring, set 9's input gear and horn, the tab block, the cradle, the stub and the
  cup. Never print from a "superseded - ..." folder.

PAN COIL SET 10 -- 2026-10-11: the servo wires straight down the pan axis
  Set 9 at the bench: meshed, the pan moved only over 500..800 us; the bare servo turned its full 180 deg. The jumper
  wires were squashed in the lane once everything was screwed down. You asked why they leave the drum sideways at all,
  and proposed screws round a plate instead of one on the axis. set10.png shows each change, cut through the axis.
  DRUM (drum.stl)
    - The barrel is 19.9 across and hollow: a 5.5 mm hole from the cone's point straight down. It ends 0.4 under the
      6704, with three M3 pilots in its end.
  BASE (base.stl)
    - A 6704 seat where the 688 was, its top level with the lane's floor, on a lip under its outer ring only. The
      lane, the shelf ring and the old exit hole stay, just empty.
  SMALL GEAR (small_gear.stl, prints hub down)
    - A solid hub on top, 22.4 across, meets the barrel's end face to face; its top stops 0.4 under the 6704's inner
      ring, which keeps the drum in the base. Three clear holes for the M3 x 16 and the wire hole, ~1.4 of wall
      round each for the full 8.7. (A first draft the same day sank M2 heads into the gear with 0.9 of wall; you
      said it looked flimsy. Never printed.)
  FLOOR PLATE (floor.stl)
    - The middle hole is 18.7 across (was 7), so the gear's three button heads turn in it.
  ASSEMBLY (what changes)
    - The 6704 goes in FIRST, before the shelf ring: it's wider than the ring's hole. Then the shelf ring, then the
      drum + 6809 down through the 6704.
    - Thread the wires down the cone to its point and straight down the barrel before the small gear goes on.
    - Input gear + horn as set 9 (servo held at 1500 us, head facing front).
    - Small gear up onto the barrel's end from below, the wires through its middle, three M3 x 16 up through it.
      Snug, not hard: they thread into PLA.
    - Floor plate on, the wires out of its middle hole. Leave a few cm of slack under the head before tying them
      down: that's where they twist as the head turns.
  Checks: pan_coil_b_check.py: 0 clashes; every assembly step clear (the 6704 before the shelf ring); the wires' way
    down the axis clear (r 1.3 probe; set 9 control: blocked by the drum and the M3); the 6704 sits on its outer ring
    only (control: the lip in to r 10.0 reads 100%); 7.3 mm of thread per screw in the barrel (control: an M3 x 12
    reads 3.3); gear play 1.9 deg, as before.
  GUESSES: the 6704's rings (inner r 10.0-11.3, outer 12.3-13.5; the lip from r 12.4); its seat 27.1 and the barrel
    19.9 (the tilt seats' fits); the hub 0.4 under the inner ring; the 5.5 wire hole; button heads on the M3 x 16
    (socket caps, 3.0 tall, would stand 1.0 below the base).

BENCH STAND -- 2026-10-11 (bench_stand.stl, fixes/bench_stand.py; G-code bench_stand_orca_PLA_45m, draft PLA, no
  supports, 31 g)
  Somewhere to stand the head on the bench until the body is printed, without anything pressing on the gears.
    - The base drops into a socket round the gear bay's outline, 0.4 a side, 8 deep; its top stays 5.1 under the
      well's overhang. Prints plate down: 130 x 120 x 3, its edge 55 mm or more from the pan axis.
    - The floor plate rests on a ledge round its edge (679 mm2). Inside the ledge it is open: nothing under the
      gears or the screw heads, a notch round each of the four M2 heads, and a driver (4 across) reaches the horn
      screw and the small gear's screw from below while the head stands in it.
  Checks: the whole head seated and dropping in from 15 mm, 0.000 mm3 (controls: the stand 1.0 toward +X 139.0;
    no notches, against the M2 heads, 90.4). Turning parts 2.0 from it with the floor plate on, 0.5 with it off
    (control, no window: 0.35; read point to point on a 0.2 grid, which adds 0.2: 2.2, 0.7, 0.55). Both driver
    paths clear (control, no window: 74.4).
  GUESSES: 0.4 a side; the M2 heads 3.8 x 2.0 (standard socket heads); the footprint, for a head whose weight sits
    about 40 mm over the deck (not weighed).

PRINTING (2026-10-10, evening) -- set 9's reprint: pan_set9_reprint_orca_PLA_57m (drum + small gear + both input
  gears, supports off). The base is its own plate, not printed yet: pan_set9_b_base_orca_PLA_1h18m (supports on).
  Set 9 has to go as two plates: with supports on, Orca fills the drum's bore with them (set 6 made it print without),
  and the input gear's hole would catch one. plate_pan_coil_set9.3mf holds all five parts for the record.
  Hardware: one 688 (8 x 16 x 5) for the barrel; the servo's double-arm horn (the 31 mm one) and the horn kit's own
  machine screw (3 mm head, 5 long); the 6809ZZ and the M3 x 12 as before.
  Everything else stays: set 7's shelf ring, the floor plate, the tab block, the cradle, the stub and the cup.
  Never print from a "superseded - ..." folder.

PAN COIL SET 9 -- 2026-10-10: the servo can turn the drum
  First bench run: the bare servo turns its full travel (5 teeth per 500 us), but meshed it can't turn the drum.
  Zach found: the input gear slips on the spline (the screw turns, the gear doesn't); it rubs the wall above it,
  more as its screw tightens; more drag when the head leans; the drum isn't bearing-smooth with the 6809ZZ in.
  set9.png shows each change, cut through its axis.
  INPUT GEAR (input_gear.stl: pocket 0.10 a side. 2026-10-11: it fits, a bit tight, as wanted; the 0.15 was too
  loose and is in the superseded folder)
    - Your horn carries it: the double-arm horn presses into a pocket of its own outline from the top, so the arms
      grip 15 mm out instead of PLA round the spline. The outline is Arm02 from your measured MG90S download (your
      caliper matched it), cut exactly, not meshed.
    - Its height: the spline stops on the horn's web, so the horn sets where the gear sits. The gear's top is 1.0
      under the servo's block (it was 0.5, and the screw pulled the gear 1.0 up your 9.0 spline into the block:
      that was the rubbing). The horn's hub is 0.75 under the block.
    - The floor is open under the horn's centre (5.0 across): the horn kit's own screw goes up through it, seats on
      the horn's web the way the horn was made for, and gets 4.5 mm into the spline. Nothing clamps the gear now; it
      rides on the horn, and the floor plate sits 0.5 under it.
    - First print of this gear (superseded the same day): zero offset, so tight the horn flew out and hit you in
      the eye; and a solid floor under an M2 x 6, which the horn's own screw couldn't get through.
  DRUM (drum.stl)
    - The barrel is 7.9 below the drum (was 10) and runs through the 688. The square stub is 6.0 across (was 7.0)
      so it passes through the 688's bore on the way in. The gear screw still threads 5.8 mm into the barrel above
      the step.
  BASE (base.stl; printed 2026-10-10, the 688 "fits beautifully, very smooth")
    - The PLA journal is gone; a seat holds the 688, its top level with the wire lane's floor, on a lip under its
      outer ring only. The drum's underside stays 0.4 clear of it, so the 6809 still carries the drum and the 688
      only keeps the barrel upright when the head leans.
  SMALL GEAR (small_gear.stl: 0.10 a side)
    - The 6.0 square bore. The first print had a 0.05 one too: so tight that pulling it off tore the stub off the
      drum. 0.10 was "not that bad".
  ASSEMBLY (what changes)
    - After the shelf ring: drop the 688 into its seat from the top, then the drum + 6809 down through it.
    - Press the horn into the input gear from the top (the gear's top is the side with the pocket). Hold the
      servo at 1500 us (FPVTank_Control: bench.py servo --channel pan --tune --fresh --engage-us 1500) and turn the
      head to face front, then push gear + horn up onto the spline, and the horn's screw up through the floor
      plate's hole and the gear's. That keeps the head's range even both ways (the drum turns 2 deg per servo deg).
  Checks: pan_coil_b_check.py: 0 clashes; every assembly step clear, the 688 dropping in and the drum going down
    through it included; gear play 1.9 deg. New rows: the 688's turning inner ring has nothing fixed under it, its
    outer ring sits on the lip, the drum's underside is clear over it (control, the lip reaching in to r 4.0: 100%
    under the inner ring); air under the servo's block, gear 1.02 / horn hub 0.76, the horn's screw 4.5 into the
    spline (control, set 6's gear pulled 1.0 up: -0.48, into the block). The new zero rows read nonzero when broken:
    the 688's seat 0.15 tight 43.9 mm3, the barrel at 8.4 28.4, the gear without its pocket against the horn 322.9,
    the gear's top 0.5 into the block 34.4. gear_horn_set9.py (exact solids), both fits: the outline grown 0.100 /
    0.151, the horn seated and coming down from above 0.000 mm3 against the gear (control, no pocket: 235.0), the
    screw's head and driver through the floor 0.000.
    The --broken control still clashes and blocks; checks/wire_route.py (ROUTE OK) and plug_passage.py pass
    unchanged with the 688 and the new barrel.
  GUESSES to OK or measure: the horn's flat face 4.45 under the block (your 9.0 spline from the tilt servo, the
    horn's 1.45 web, the 6.0 block; the pan servo's spline isn't calipered); 1.0 of air under the block; the 688
    seat 16.1 and the barrel 7.9; the lip from r 7.1; the pocket at 0.10 / 0.15; the small gear at 0.10; the horn
    screw's head 3 mm (your listing).

PAN COIL SET 8 (superseded by set 9 for the drum and small gears; printed 2026-10-09)
  plate_pan_coil_set8.3mf   drum + the small gear at two fits. Drum: supports OFF, as set 6's. The gears
                            need none.
  Hardware: one M3 x 12 button head for the small gear (was M3 x 8). An x 8 would reach only 1.8 mm into the
  barrel now, so don't reuse it.

PAN COIL SET 8 -- 2026-10-09: the stub stops snapping, a square drive, a straight wire hole
  Zach: the stub at the end of the drum's barrel snapped every time the screw was tightened (his photo: the
  broken stub still on the screw inside the small gear). Threading the wires was "a massive pain", stuck at the
  cone. And he asked for "a square going in so it grips better".
  DRUM (drum.stl)
    - The screw: the M3 x 8 had 4.2 of its 6.2 mm of thread in the stub, below the step the gear pushes up on.
      Tightening pulled the stub down off the barrel, across its layers (the drum prints upside down, so the
      layers run across the barrel), at a sharp corner. Now the stub has a 3.4 clear hole and an M3 x 12
      threads 5.8 mm into the barrel above the step. Tightening squeezes the step; the stub only turns the gear.
    - The square: the stub is a square 7.0 across with r 0.8 corners (it was a D: r 4, flat at 3.2). Its
      corners reach r 4.62, inside the barrel's 5, so the step stays all round and the stub still passes down
      through the journal. Wall round the screw's hole: 1.8 (the D had 1.5 at its flat).
    - The wires: set 6's hole started at the cone's point and turned from straight down to sideways, out of
      sight. Now a straight vertical 5 mm hole starts right under where the wires come down the notch (r 8,
      -127 deg, behind the ribbon) and comes out of the drum's underside. An open groove in the underside
      takes them out to the lane, leaving the drum heading clockwise (seen from above), the way they wrap. The
      cone stays as the bore's floor. Both print without support, so the arch Orca supported in set 6's
      curved hole is gone too.
  SMALL GEAR (small_gear.stl: 0.05 a side; small_gear_loose.stl: 0.10)
    - A square bore for the square stub. The D let the gear turn 7.5 deg on it, end to end, before the flat bit;
      only the screw's clamp held it. The square at 0.05 a side: 2.2 deg; at 0.10: 4.4.
    - Try small_gear first; the screw draws it on. If it won't go on, use small_gear_loose. Any of its four
      ways round fits.
  THE RIBBON: ONE WRAP, NOT A COIL (2026-10-09; Zach had been winding it round and round inside)
    Head facing front, so the drum's slot faces the servo. From the slot, lay the ribbon clockwise seen from
    above (toward the exit slit's side), about half a turn round the drum, fold it back once (the U), and run it
    along the cup wall to the slit. About 70 mm stays inside; pull the rest out through the slit. Laid this way
    the head turns 317 deg one way and 235 the other before the U runs out; laid the other way round from the
    slot, only 137 one way. Wound into several turns, the layers rub and wind tighter as the head pans. The fit
    view's "Laying the ribbon" card shows it, with a slider. (The fit view's ribbon used to be drawn centred on
    paper, with its drum end at -139 deg instead of at the slot.)
  THREADING (replaces set 6's step 4)
    1. Cradle off the drum (not bolted yet). Down the cradle as before, round the ribbon's -Y edge, down the
       notch.
    2. Straight down the hole at the notch's foot, on the far side of the ribbon from the lens. With the drum
       out you can see light through it.
    3. Out of the drum's underside: bend them into the groove. They come out of the drum's side at the lane's
       height.
    4. In the lane: clockwise round the drum (seen from above) about a third of a turn (~130 deg), the U-turn,
       then anticlockwise along the lane wall to the exit hole. About 74 mm of wire in the lane, as before.
       With 74 mm the head turns 214 deg clockwise and 325 anticlockwise from straight ahead before the loop
       runs out (with 65 mm: 189 / 285). With set 6's exit, 74 mm allowed only 150 deg one way, whichever way
       the loop was laid.
    Then the shelf ring, the 6809 and the drum, as in set 7.
  Checks: pan_coil_b_check.py: 0 clashes, every assembly step clear (the --broken control blocks them), gear
    play 1.9 deg. New row: the screw's thread in the stub 0.0 mm, in the barrel 5.8 (control, set 7's drum:
    4.2 in the stub). drum_set8.py: the gear turns 7.5 deg on the D, 2.2 on the square at 0.05, 4.4 at 0.10
    (control: a bore 0.05 under the square binds, 0.0).
    checks/wire_route.py: the straight hole takes the 4.4 mm probe (2.50 clear); the groove takes a 2.8
    bundle (1.55; control without the groove: 0.00). Handover from the cradle into the hole: 3.1 mm with the
    ribbon centred, 2.4 with it 3 off (the cradle's mouth is the limit, not the drum); control, set 6's drum
    has no way into that spot (0.0). Walls: 1.6 round the hole, 1.5 to the drum's face, 0.5 to the barrel.
    Meshes clean. No Fusion tool bodies: these are generator parts.
  Guesses: the square (7.0 across, r 0.8 corners); the gear's fit (0.05 / 0.10 a side); the M3 x 12 (from
    the 2026-09-27 list, not checked today); the hole's place (r 8, -127 deg); the groove (5 wide, 2.9 deep,
    roof at Z -21.0); the wires staying up in the groove (if they rub the lane's floor, push them up into it).
  Superseded: set 6's drum, its plate, and the D small gear ("superseded - set 6 drum and D small gear (seat
    snapped off, curved wire hole)/"). Set 6's input gear stays.
  Picture: drum_set8.png. 3D: the fit view's "Set 8" card.

PRINTED (2026-10-04) -- pan coil set 7, one plate, before the 6809ZZ arrived (it was due 2026-10-05: the first
real test of the bearing's seat).
  plate_pan_coil_set7.3mf   base + shelf ring. Your usual settings (tree supports on) are fine: Orca puts none
                            in the wire lane now. What it still adds comes out from below (the gear bay's
                            ceiling, round the journal) or through the servo window (over the servo pocket).
                            The shelf ring needs none at all.
  Everything else stays: set 6's drum and input gear, the floor plate, the small gear, the tab block, the
  cradle, the stub and the cup. Never print from a "superseded - ..." folder.

PAN COIL SET 7 -- 2026-10-04: the shelf drops in
  Zach: the supports Orca puts in the base's wire lane, under the shelf, are impossible to get out. A 30 deg
  slope can't carry the shelf: across the lane's 8.4 mm it needs 14.5 mm of drop, and the lane is 3.5 tall.
  SHELF RING (shelf_ring.stl, new part, about 12 min)
    - The shelf the ribbon stands on and the ribbon cup's wall, as one ring. It prints shelf face down and
      nothing overhangs.
    - It drops into the base from above onto a 1.5 mm ledge on the lane wall, with 0.15 mm of slide all round.
    - A notch in its rim fits a small rib on the ledge (at -60 deg). Turn the ring until the notch finds the
      rib, then let it drop: that lines its ribbon notch up with the base's slit and stops the ribbon's drag
      turning it.
    - The inside of its wall is 0.3 mm wider than set 5's (18.3), so the drum's top rim keeps 0.45 mm even
      with the ring a full 0.15 off centre.
    - Gravity and the rib hold it. If it lifts, a dab of CA glue on the ledge.
    - It's cut over the wires' exit hole (outside its wall only), as set 5's shelf was.
    - Bonus: it lifts out, so you can see and tidy the wire loop in the lane.
  BASE (base.stl; printed 2026-10-10, the 688 "fits beautifully, very smooth")
    - No shelf and no cup wall now. The deck ring's hole is wider (r 22.65) so the ring passes, and that also
      takes the deck ring out from under the drum's hub: set 5's sat flush under it at r 19.5-20.4, so the
      drum rested on plastic as well as on the bearing.
    - The deck ring stands on a skirt, with a cone 30 deg off vertical under its outer part.
    - The ribbon leaves through a 2 mm slit (it runs straight out there, on edge), with a pointed roof; under
      the bearing's turning inner ring the slit is open to the top.
    - The wires' exit hole has a pointed top, and the boss round it is 3 mm taller.
    - Orca, your settings: supports in the wire lane 3850 moves -> 0; under the deck ring, outside, 15041 ->
      1319 (1264 over the servo pocket, out through its window; 47 in the wires' exit hole's mouth, which is
      open to the ring's space until the ring goes in; 8 at the servo tower's corner); time 2h51 -> 1h57.
  ASSEMBLY: after the servo and the tab block, drop the shelf ring in (notch on the rib), THEN the 6809 and
    the drum.
  Checks: pan_coil_b_check.py: 0 clashes; every assembly step clear, the ring's drop-in too (control: a
    ring 1 mm too wide is blocked 11 mm out); gear play 1.9 deg; nothing fixed under the drum's hub (set 5's
    base reads 23%). The ring vs the base: 0 overlap (control: the ring without its key notch hits the rib).
    checks/wire_route.py rows 4-6 with the ring in place: the exit hole 2.25 (2.2 wanted), the lane 1.50
    (1.4 wanted), the hole's wall 1.0. checks/plug_passage.py passes.
  Guesses: the ring's 0.15 slide; the 1.5 ledge; the key's 0.15 a side; the 0.8 shelf as a part of its own
    (it was fused to the base); gravity holding it; the 2 mm slit; the 30 deg cone (your number).
  Superseded: set 5's base ("superseded - set 5 base (lane supports trapped, hub on the deck ring)").
  Picture: base_shelf_set7.png. 3D: the fit view's "Set 7" card.

PRINT NOW (2026-10-03) -- pan coil set 6, one plate (printed 2026-10-04; the input gear works):
  plate_pan_coil_set6.3mf   drum + input gear. Slice both with supports OFF.
  Everything else stays: the base printed from set 5 is unchanged (byte-identical), and so are the floor
  plate, the small gear, the tab block, the cradle, the stub and the cup. Never print from a
  "superseded - ..." folder.
  Hardware for the gear: the servo's own horn screw (about 4 mm; an M2 x 4 or x 6 also reaches).

PAN COIL SET 6 -- 2026-10-03: the drum prints without supports; the input gear goes on the spline
  Zach assembled set 5. The drum's bore needed supports that couldn't be got out, and no screw was long
  enough to reach the servo through the input gear.
  DRUM (drum.stl)
    - The drum prints top face down, so set 5's flat bore floor was an 18 mm ceiling over tree supports.
      It is now a cone 30 deg off vertical (Zach's limit), point down, 15.6 deep (Z -2.5 to -18.1), which
      prints with nothing under it.
    - The cone's point is the wire hole's mouth: wherever the wires drop into the bore, they slide to it.
      The hole bends out under the ribbon's band and leaves the drum's face into the lane where set 5's
      did, breaking through the drum's underside on the way as set 5's did. Set 5's funnel is gone: the
      cone is the funnel.
    - The notch's floor is steepened from 55 to 60 deg (30 off vertical) and now runs into the cone's rim.
    - Supports OFF. Left over air: the ribbon slot's roof (a 17 mm bridge, open to the side) and the arch
      over the 5 mm hole. Orca with supports off: 35 min, 12.7 g. With tree supports on, Orca still runs
      4 m of support up the bore to those two, so turn them off.
    - Threading as set 5's steps below, except step 4: once past the ribbon's edge and down the notch,
      let the wires drop; the cone leads them to the hole.
  INPUT GEAR (input_gear.stl)
    - The horn pocket was a placeholder from generic numbers (no horn model of Zach's could be found).
      His MG90S's shaft ran 0.8 mm into the pocket's roof, so the gear hung low and no screw reached.
    - Now the spline presses straight into the gear, the way post v3 takes the tilt servo's: post v3's
      bore (4.44, from his faceted 4.5), a 1.5 mm lip under the spline's tip, the screw up through the
      lip's 2.7 hole from a 5.2 counterbore. The servo's own horn screw is made for a horn's thin floor,
      which the lip stands in for: a 4 mm screw gets 2.5 mm into the shaft, a 6 mm one 4.5.
    - It prints bottom face down, counterbore on the bed (as post v3 prints flange down). Supports OFF:
      the lip bridges the counterbore. With supports on, Orca fills the 1 mm counterbore.
    - If the real spline is 9.0 long (the caliper number on the tilt servo) rather than the model's
      10.0, the screw pulls the gear 1 mm up. There is room: 0.8 under the bay's roof, 0.5 off the
      servo's block, and the gears still mesh over 5 of their 6 mm.
    - Assembly as before: push the gear up onto the spline from below (it's a press), drive the screw up,
      then the small gear and the floor plate.
  Checks: pan_coil_b_check.py: 0 clashes, every assembly step clear, gear play 1.9 deg. The gear against
    his MG90S reads 3.5 mm3, all of it the spline's press ring (r 2.23-2.31); the old gear read 9.6, with
    the shaft in its roof (the control). checks/pan_servo_fit.py: fits. checks/wire_route.py rows 1-7
    pass; row 7 now aims at the hole at the cone's point: a 3.0 mm bundle with the ribbon centred, 2.4
    with it 3 off centre (at the cradle's mouth, not the drum). Controls block: set 4's drum (1.6), the
    first notch (1.4), and set 5's flat floor with the new hole (0.0). The cone keeps 3.3 mm of wall to
    the drum face the ribbon wraps; the hole keeps 1.2 mm under it. checks/plug_passage.py passes. Meshes
    clean. No Fusion tool bodies: both are generator parts.
  Guesses: the 30 deg (his number); the hole's new path; the gear's 4.44 bore (post v3's press, in PLA);
    the 1.5 lip; the servo screw's length (about 4 mm, not measured). The ribbon's path below the old
    floor isn't modelled: row 7 draws it turning flat toward its slot, which closes the cone's +X side.
  Superseded: set 5's drum, input gear and plate ("superseded - set 5 drum and input gear (bore supports,
    gear screw short)/"). Set 5's base stays current.
  Picture: drum_cone_set6.png.
  Post v3 (+Y) does reach the tilt servo's spline: it only needs pushing all the way in (Zach,
    2026-10-04). It's a press, as the CAD has it (3.5 mm of spline). No change.

CRADLE, BLENDED RIDGE -- 2026-10-02 (looks only): cradle.stl, also on plate_wire_route_r1.3mf
  The ridge round the wire hole stood out of the -Y wall as a narrow vein, with a notch where it left the
  collar. Its blend radius went 1.5 -> 6 mm, so it swells into the wall now; the +Y twin too.
  cradle_blend.png shows before and after.
    - Only the outside grows, by 1.1 mm at most (720 mm3, both sides). Nothing is removed. The wire hole,
      the ball's clearance, the ribbon's groove, the stub's bore and the screws are cut after the blend,
      so none of them moved. The foot of the swelling stays 4 mm above the base, which the cradle turns
      over.
    - The one you printed works the same. Print this one when you want the look (the ASA print, say).
  Superseded: the cradle you printed ("superseded - cradle before the blended ridge (printed 2026-10-02)/",
    with the plate and picture it was on).

PAN COIL TEST PRINT, SET 5 -- 2026-10-02 (its drum superseded by set 6 above; sets 4, 3 and 2 below)
The 360-degree pan base under the v2 head, and the cradle that bolts onto it.

SET 5 = SET 4 + A WIRE NOTCH AND FUNNEL IN THE DRUM (base printed and current; drum superseded by set 6)
  REBUILT 2026-10-02 18:27 after a second check. If you sliced set 5's plate before then, slice it again.
  The cradle's wire hole lets the wires out IN FRONT of the ribbon, where it bends down into the drum's
  bore. Set 4's drum hole starts BEHIND it, and the ribbon's edge sat 0.7 mm from the bore wall, so the
  wires couldn't get round. Nothing checked that gap (it is row 7 of the check now).
    - A notch in the drum's bore wall on the -Y side: out to r 14, from -150 to -72 deg, open at the top
      face. Its floor slopes 55 deg down toward the bore (Z 6 at the outer wall, Z -1 at the bore), so it
      prints without support (the drum prints top face down) and tips the wires back into the bore.
    - A funnel on the drum hole's mouth: 7 mm across at the bore floor, down to the 5 mm hole 2 mm lower.
      It follows the hole's own line, so it leaves no ledge where it meets it.
    - Only the drum changed; base.stl is byte-identical to set 4's. Set 4 was never printed, so the plate
      keeps both. The drum's overhang is slightly less than set 4's (327 mm2, was 339).
  THREADING (replaces set 4's and round 1's order; UNTESTED, report where it snags). The handover needs
    eyes, so it happens BEFORE the cradle is bolted down:
    1. Pan side built: base, 6809, drum, gears, floor. Ribbon through the cradle's groove and into the
       drum. Rest the cradle on the drum, NOT bolted.
    2. Turn the drum until its wire hole faces the exit boss (about -145 deg).
    3. Jumpers: shells off the bare ends. Thread them through the stub (in at its inner end, out of its
       side hole), then into the hole at the bottom of the collar (about 7 o'clock seen from -Y), down
       until they come out under the cradle. The stub hangs on the wires for now.
    4. Lift the cradle a little (as far as the ribbon allows) and push the ribbon toward +Y (the post
       side). Lead the wires past the ribbon's -Y edge as they leave the cradle (its groove has 3 mm
       beside the edge), down the notch behind the ribbon, into the funnel. Push on down the core, round
       the lane and out the exit boss; a stiff fish wire up from the exit, with the jumpers taped to it,
       may be easier. If the bundle jams at the cradle's mouth, feed the wires one at a time.
    5. Lower the cradle, drawing the slack down; bolt it (3 x M3 x 12 from above, before the ball goes in).
    6. Press the 6704 into ball_minus_cup. With the ball open, plug the jumpers' male ends into the servo
       plug, close it, seat it. Push the stub into the collar and the bearing, drawing the slack down;
       M2 x 6 x 3.
    7. Pull out all but about 74 mm in the lane, then turn the drum back to centre: turning winds the loop.
    If it's easier, the servo's own wires (pins out of the plug, as you found works) can run instead of
    jumpers. Measure the lead first: the route needs about 24 cm to the bottom of the base, plus slack.
  Superseded: set 4's drum ("superseded - set 4 drum before wire notch/", with set 4's plate). Don't
    print it. Also superseded, never printed: set 5's first cut (notch r 12.3 with a flat floor; a
    funnel that left a 0.26 mm ledge), replaced by this one at 18:27.
  Check: head-v2/checks/wire_route.py row 7 floods the space between the cradle's hole and the drum's
    hole: the widest round bundle that gets from one to the other past the ribbon. Ribbon centred: 3.1 mm.
    The cradle's 22 mm groove lets the 16 mm ribbon sit up to 3 mm off centre; pushed toward -Y it leaves
    2.4 mm at the cradle's mouth (printed or blended, the same inside), hence step 4. The drum is never
    the tightest place. Controls: set 4's drum blocks it (1.6 mm), and so does the first notch with the
    ribbon off centre (1.4 mm, in the drum); with no ribbon, set 4's drum lets 4.6 mm through, so the
    search works. The funnel keeps 1.9 mm of wall to the drum face the ribbon wraps; the notch's floor
    keeps 2.95 mm to the ribbon's chamber. Rows 1-6 still pass. No Fusion tool bodies: the drum is a
    generator part.
  Guesses: the notch's and the funnel's sizes (picked, not tried with real wire); the bundle's 2.8; the
    ribbon's path (its fold into the drum's slot below Z 5 isn't modelled); which side of the ribbon the
    wires come out on (in front, by reasoning; you're testing it on the printed cradle).
  Picture: drum_notch_set5.png. 3D view: https://claude.ai/artifact/835mQ49eee7jyEU7Xzgzek

SET 4 = WIRE ROUTE, ROUND 2 (superseded by set 5's drum; its base carries on): base.stl AND drum.stl
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
  ~~THREADING THE WIRES (round 2)~~ SUPERSEDED by set 5's THREADING (above). It said: do it LAST, with the pan side built and the cradle and ball on. Don't
    wrap the loop on the drum before it goes in: the shelf sits 0.6 mm from the drum, and a wrapped loop
    can't pass it. After the tilt side (round 1 below):
    1. Turn the drum until its wire hole faces the exit boss (about -145 deg).
    2. Push the bare ends down the drum's hole, on the side away from the ribbon's slot, into the core hole
       and out through the exit boss. A stiff fish wire pushed up from the exit, with the jumpers taped
       to it, may be easier.
    3. Pull out all but about 74 mm in the lane (the same 540 deg of travel the ribbon has), then turn
       the drum back to centre: turning winds the loop.
    UNTESTED: this order is the plan; report where it snags.
  Superseded: set 3's base and drum ("superseded - set 3 before wire lane/"). Don't print them.
  Tool bodies for reference in Fusion: wire_route_r2_tools_for_fusion.step (CUT_base_wire_lane,
    CUT_drum_wire_hole_5mm, CUT_base_wire_exit_5mm; pan frame, Z 0 at the deck top).
  Checks: head-v2/checks/wire_route.py, round 2. The 4.4 mm probe passes the drum's hole and the base's
    exit with 2.45 to spare. A 2.8 bundle clears the lane all the way round. Walls round both holes are
    1.0+ away from their mouths. Each check has a control that has to fail. Pan checks: 0 clashes, every
    assembly step clear, gear play 1.9 deg. Your MG90S still fits.
  Guesses: the lane's 3.5 height (for three ~1.3 jumper wires twisted loosely together); the 74 mm of
    wire in it; the 0.4 mm the drum stands off the floor.

WIRE ROUTE, ROUND 1 (2026-10-02): REPRINT cradle.stl, PRINT stub.stl AND ball_minus_cup.stl
  (all three on plate_wire_route_r1.3mf)
  The tilt servo's wires get their own way down, off the ribbon. wire_route_r1.png shows before and after.
    - The servo's own lead and plug stay inside the ball, coiled loosely behind the camera board on the
      -Y side (about 17 cm3 free there). Plug three Dupont jumper wires into the servo's plug (tape or
      clip the joint so it can't pull apart). Only those wires run down.
    - stub.stl replaces BOTH the -Y axle and the -Y end cap. It doesn't turn. 3 x M2 x 6 through the
      cap's old holes hold it, and also line its wire hole up with the cradle's. (The old axle was r 9.95
      in your r 10.04 socket, which is why that pin never fitted.)
    - THE -Y 6704 IS IN YOUR BALL NOW: with the stub screwed down, nothing turned in the cradle's seat
      (your catch). ball_minus_cup.stl is your rev 2 ball_minus with a cup inside its flat face: press
      the bearing in from outside until it stops on the lip. Its outer ring turns with the ball; the stub
      goes through its inner ring and shoulders against it. The cradle's -Y collar is a plain bore now.
      To keep your Fusion model the source of truth, boolean ADD_minus_bearing_cup and
      CUT_minus_bearing_pocket (in the STEP) into it; ball_minus_cup.stl is the same result.
    - The wires run through the middle of the stub, right on the tilt axis, so tilting twists them half a
      turn instead of bending them. Then down a 5 mm hole inside the cradle's -Y wall, past the drum
      screw (below its head), into the plug chute's mouth and down the drum's hole beside the ribbon.
      Where the wall was too thin for the hole, a 1.6 mm ridge grows on its outside. A solid twin of it
      sits on the +Y wall, for looks only (2026-10-02).
  THREADING: slide the plastic shell off the END YOU THREAD (each shell has a small tab you lift with a
    needle; the bare metal pin stays on the wire). The 5 mm hole takes three wires with one bare pin
    going through at a time. The male ends stay in the ball, plugged into the servo. Push the shells
    back on at the bottom.
    ~~Order~~ SUPERSEDED by set 5's THREADING (top). It said: pan side built, cradle bolted to the drum. Press the 6704 into ball_minus_cup. With the ball
    open, plug the jumpers' male ends into the servo plug, then close it: the jumpers come out through
    the bearing's bore. Seat the ball. Thread the bare ends THROUGH THE STUB first (in at its inner end,
    out of its side hole; the hole is closed, so the stub can't slide on over wires already in place).
    Then feed them into the hole at the bottom of the collar (about 7 o'clock seen from -Y), down until
    they show in the chute's mouth. Push the stub into the collar and the bearing, drawing the slack
    down; M2 x 6 x 3. Then the pan lane (set 4's THREADING, above).
  WIRE LENGTH: about 24 cm from the servo plug to the bottom of the base, plus slack and the run to the
    board. 30 cm jumpers are too short to have any spare: use 40 cm or join two.
  ROUND 2 is set 4 (top): the wires' own lane in the pan coil. With set 3's drum and base, the wires go
    out the drum's side slot loose beside the ribbon, which is only good for testing the tilt.
  Superseded: the cradle you have ("superseded - cradle before wire route/"), the -Y axle and the -Y end
    cap, your ball_minus without the cup (print-rev2), and this round's first cuts, which kept the
    bearing seat in the cradle ("superseded - wire route first cuts, bearing seat in the cradle (never
    printed)/"). Don't print them.
  Tool bodies for reference in Fusion: wire_route_r1_tools_for_fusion.step (CUT_wire_hole_5mm,
    ADD_wire_conduit, ADD_ridge_plus_y_for_looks, ADD_minus_bearing_cup, CUT_minus_bearing_pocket; head
    frame).
  Check: head-v2/checks/wire_route.py. A 4.4 mm probe (bare pin beside two wires) rides the whole way:
    2.4 mm of clearance at the tightest. Thinnest wall round the hole 0.6 (beside the cap's flange gap),
    1.5 in the ridge. Stub vs cradle and vs your ball 0.00 mm3; the cup 0.9 short of the camera board.
    The bearing's turning outer ring stays 1.5 off the stub and 1.2 off the cradle; its fixed inner ring
    stays 0.55 off the ball. Each with a control that has to fail.
  Guesses: the 27.1 pocket (if the 6704 drops in loose or won't press in, say which); the stub's 19.9
    through the bearing; the 5 mm hole (sized for 26-28 AWG jumper wire, ~1.3 across); the coil fitting
    where it's drawn.

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
  2 x 6704 bearing (20 x 27 x 4)            one in the +Y collar, one in the cup in ball_minus (you have 10)
  3 x M2 x 6                                the stub, through the old cap holes
  3 x Dupont jumper wire, 40 cm             the tilt servo's run (see WIRE ROUTE)

ASSEMBLY ORDER (checked: each part slides in along this path without hitting anything)
  1. Servo into the base through the side window, shaft pointing down. Slide the tab block in behind
     it under the window-end tab. Two M2 x 6 through its tabs (the window-end one into the block).
  1b. (set 7) Drop the shelf ring into the base from above, its rim's notch on the ledge's rib.
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
