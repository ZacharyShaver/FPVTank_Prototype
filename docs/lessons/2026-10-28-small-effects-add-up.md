# Small effects add up

2026-10-28, the knob review (`gauges/knobs.py freeze`, `gauges/README.md` "Which knobs matter").

**What happened.** The knob sweep moved each of T3's knobs alone across its range. Fourteen knobs only cost when moved
off T3's value, each by less than the noise bar the review set (20 mm on the turn), so the review called them settled
and proposed freezing them. The check ran three searches from T3's neighbourhood: every knob free, the settled ones
held at T3's, the levers held instead (the control). Held, the settled knobs cost the best design 17 mm of turn (378
against 361 mm, both stepping 150 mm). The free search narrowed the tyres (46 to 34 mm), the track and the skin
together: four changes of under 20 mm each, worth more than the bar together.

**Why.** A noise bar on one knob at a time hides effects that are small but point the same way. The turn reads the
robot's widest point, so every knob that trims width pulls together.

**The control failed too.** Holding the levers lost nothing (357 mm), because the check scored only the step and the
turn, and T3's levers already sit at that objective's best; what they trade, the hills and the push, wasn't read. A
control has to be able to move under the objective the check uses.

**How to apply.** Before freezing a knob, check it jointly with the others it might pull with, under every gauge the
search will use; the one-at-a-time sweep only says where a knob is not worth searching alone. Related:
`2026-10-27-dead-on-average-is-not-dead-at-the-front.md`.
