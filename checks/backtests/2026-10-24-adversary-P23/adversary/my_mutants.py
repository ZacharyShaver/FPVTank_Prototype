from operators import *

MUTANTS = {
    # printability: the reason set 7 exists
    'A01': (glue('well', 'shelf_ring'), 'shelf ring moulded back onto the base (set 6 lane roof, needs supports)'),
    'A02': (param(CONE_OUT_DEG=60.0), '30 deg read from horizontal: deck cone, slit and teardrop roofs 60 deg off vertical'),
    # the drop-in slide fits (real part differs: the ring prints shelf face down)
    'A03': (param(RING_OR=22.65), 'ring edge +0.15 (bed-face elephant foot): zero slide in the skirt'),
    'A04': (param(KEY_SLIDE=-0.1), 'key notch prints 0.25 narrow a side: 0.1 interference on the rib'),
    'A05': (param(KEY_H=0.0), 'rib flush with the ledge (as if the room cut ate it): nothing keys the ring'),
    'A06': (param(LANE_R=22.6), 'lane widened 1.6 mm for the wires: ledge gone, ring sits on nothing'),
    'A07': (param(RING_OR=21.8), 'ring 0.7 smaller in radius: 0.85 play a side, more than its 0.6 drum clearance'),
    'A08': (param(LANE_Z1=-20.3), 'ledge and shelf bottom raised 0.5: the ring shelf is 0.3 mm thick'),
    'A09': (nofeat('shelf_ring'), 'ring loses its ribbon window and wire mouth'),
    'A10': (move('shelf_ring', (0, 0, -0.3)), 'ring modelled 0.3 low, into its ledge'),
    'A11': (move('shelf_ring', (0, 0, 0.4)), 'ring rides 0.4 high: cup top meets the drum hub'),
    'A12': (move('ribbon', (0, 0, -1.0)), 'ribbon resting on the shelf, as the pair note says (1 mm below the drawn band)'),
    'A13': (param(WINDOW_W=2.0), 'ring ribbon window cut to the 2 mm slit width (model ribbon turns a sharp corner)'),
    'A14': (move('shelf_ring', (0.2, 0, 0)), 'ring 0.2 off centre: a 0.05 crescent into the skirt'),
    'A15': (param(DECK_IR=23.0), 'dead set 5 constant (no effect on the set 7 design)'),
}
