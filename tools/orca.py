"""Slice parts headless with OrcaSlicer's CLI for Zach's Creality K2 Pro, with his settings.

    python tools/orca.py head-v2/out/print-pan/base.stl                 # his settings, G-code in head-v2/out/gcode/
    python tools/orca.py part.stl --set layer_height=0.24 --set wall_loops=3 --name part_draft
    python tools/orca.py a.stl b.stl --draft          # PLA test parts: ~20% faster (DRAFT below)

The defaults are his own Creality Print slice of the base (2026-10-03): 0.20 Standard, 2 walls, 15 % grid,
tree supports at 30 deg, PLA 220/50 on the textured PEI plate. Change one with --set key=value (Orca's
option names, as in its preset JSON). Send the result with tools/k2.py.

Orca's CLI loads presets only as flat JSON files, so this merges each system preset's `inherits` chain
itself. The gotchas that cost runs (2026-10-03):
  - the machine must say "from": "system" with its exact system name, and the process and filament must
    list that name in compatible_printers, or the CLI exits "process not compatible with printer";
  - each file needs a "version";
  - the CLI writes its real error to 00000.log in its working directory, not to stdout;
  - it opens no window, but run it hidden anyway; Zach often has Orca open, so never kill it by name.
The start G-code is Creality Print's single-spool start (the one the printer has run all along), not
Orca's: Orca's K2 Pro profile purges along the bed's very edge (X 0, Y 0)."""
import argparse, json, os, re, shutil, subprocess, sys, tempfile
import config

ORCA = r'C:\Program Files\OrcaSlicer\orca-slicer.exe'
PROFILES = r'C:\Program Files\OrcaSlicer\resources\profiles\Creality'
MACHINE = 'Creality K2 Pro 0.4 nozzle'
PROCESS = '0.20mm Standard @Creality K2 Pro 0.4 nozzle'
FILAMENT = 'Creality Generic PLA @K2-all'
GCODE = os.path.join(config.OUT, 'gcode')

# Zach's Creality Print process for the base, 2026-10-03 ("0.20mm Standard ... - Copy(2)").
ZACH = {
    'process': {'wall_loops': '2', 'top_shell_layers': '5', 'bottom_shell_layers': '3',
                'sparse_infill_density': '15%', 'sparse_infill_pattern': 'grid',
                'enable_support': '1', 'support_type': 'tree(auto)', 'support_style': 'default',
                'support_threshold_angle': '30', 'support_on_build_plate_only': '0',
                'support_top_z_distance': '0.2', 'support_object_xy_distance': '0.35',
                'brim_type': 'auto_brim', 'seam_position': 'aligned'},
    'filament': {'filament_max_volumetric_speed': ['12'],  # Orca's Generic PLA says 18
                 'nozzle_temperature': ['220'], 'nozzle_temperature_initial_layer': ['220'],
                 'hot_plate_temp': ['50'], 'hot_plate_temp_initial_layer': ['50'],
                 'textured_plate_temp': ['50'], 'textured_plate_temp_initial_layer': ['50']},
    'machine': {'curr_bed_type': 'Textured PEI Plate',
                'before_layer_change_gcode': ';BEFORE_LAYER_CHANGE\n;[layer_z]\nG92 E0\n'},
}

# --draft: PLA test parts, speed over finish (Zach, 2026-10-03). Measured one at a time on the head set
# (cradle, ball_plus, 2 sleeves, post, drum: 3h41m with his settings): wall acceleration -11 min, tree_slim
# -16, 10% infill -5, flow 18 (Orca's own Generic PLA value) -5; together with 3 top layers 2h59m. Not used:
# normal "snug" supports (-29 min, but they pack holes and pockets: the cradle's wire hole, the drum's
# notch); wall accel past 8k (-3 min more, at the press fits' expense); small perimeters at 100% (0);
# layer 0.24 (the cradle, ball and drum together fail to slice at 0.24 in Orca 2.4.2; any two slice).
DRAFT = ['filament_max_volumetric_speed=18', 'outer_wall_acceleration=8000', 'inner_wall_acceleration=10000',
         'top_surface_acceleration=8000', 'sparse_infill_density=10%', 'support_style=tree_slim',
         'top_shell_layers=3']

# Creality Print 7.3's K2 Pro start G-code, its single-spool branch (the CFS reads "disconnect"), with the
# purge line's feed rates as Creality Print rendered them. START_PRINT's adaptive probing reads MINX..MAXY.
START = """; MINX = {first_layer_print_min[0]}
; MINY = {first_layer_print_min[1]}
; MAXX = {first_layer_print_max[0]}
; MAXY = {first_layer_print_max[1]}
M140 S0
M104 S0
START_PRINT EXTRUDER_TEMP=[nozzle_temperature_initial_layer] BED_TEMP=[bed_temperature_initial_layer_single]
T[initial_no_support_extruder]
M104 S[nozzle_temperature_initial_layer]
M204 S2000
G1 Z3 F600
M83
G1 X125 Y-1 F30000
G1 E1 F300
G1 Z0.3 F1200
G1 X150 E9 F720
G1 X155 E.3742 F1200
G1 X160 E.3742 F4800
G1 X165 E.3742 F1200
G1 X170 E.3742 F4800
G1 X175 E.3742 F1200
G91
G1 X1 Z-0.3
G1 X4
G92 E0
G1 Z1 F600
G90"""


def flat(kind, name):
    """a system preset with its inherits chain merged, parent first"""
    chain = []
    while name:
        with open(os.path.join(PROFILES, kind, name + '.json'), encoding='utf-8') as f:
            d = json.load(f)
        chain.append(d)
        name = d.get('inherits')
    out = {}
    for d in reversed(chain):
        out.update(d)
    out.pop('inherits', None)
    out['name'] = chain[0]['name']
    return out


def presets(sets):
    """the three flat presets, with Zach's settings and then the --set overrides applied"""
    m, p, f = flat('machine', MACHINE), flat('process', PROCESS), flat('filament', FILAMENT)
    m.update(ZACH['machine'], machine_start_gcode=START, **{'from': 'system'})
    p.update(ZACH['process'], compatible_printers=[MACHINE], **{'from': 'User'})
    f.update(ZACH['filament'], compatible_printers=[MACHINE], **{'from': 'User'})
    for kv in sets:
        k, v = kv.split('=', 1)
        hit = [d for d in (p, f, m) if k in d]
        if not hit:
            raise SystemExit('--set %s: no preset has that option' % k)
        hit[0][k] = [v] * len(hit[0][k]) if isinstance(hit[0][k], list) else v
    for d in (m, p, f):
        d['version'] = '2.3.2.75'
    return m, p, f


def summary(path):
    """the numbers worth reading off a G-code: time, grams, layers, height, and the start checked"""
    s = {}
    with open(path, errors='ignore') as fh:
        text = fh.read()
    for key, pat in (('time', r'; estimated printing time \(normal mode\) = (.+)'),
                     ('grams', r'; filament used \[g\] = ([\d.]+)'),
                     ('layers', r'; total layer number: (\d+)'),
                     ('height', r'; max_z_height: ([\d.]+)')):
        m = re.search(pat, text)
        s[key] = m.group(1).strip() if m else None
    start = text.find('START_PRINT ')
    first = text.find(';LAYER_CHANGE')
    head = text[start:first]
    s['start_ok'] = (start > 0 and 'G90' in head.split('G91', 1)[-1]
                     and re.search(r'START_PRINT EXTRUDER_TEMP=\d+ BED_TEMP=\d+', head) is not None)
    s['support'] = ';TYPE:Support' in text
    return s


def centred(stl, dest, bed=(150.0, 150.0)):
    """a binary STL's copy with its footprint centred on the bed, as drawn (Orca's arrange turns parts)"""
    import numpy as np
    raw = open(stl, 'rb').read()
    n = int.from_bytes(raw[80:84], 'little')
    tri = np.frombuffer(raw, dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]),
                        count=n, offset=84).copy()
    v = tri['v'].reshape(-1, 3)
    shift = np.array([bed[0], bed[1], 0.0]) - np.r_[(v[:, :2].min(0) + v[:, :2].max(0)) / 2, v[:, 2].min()]
    tri['v'] += shift.astype('<f4')
    with open(dest, 'wb') as fh:
        fh.write(raw[:84])
        fh.write(tri.tobytes())
    return dest


def creality_header(src, dest):
    """copy the G-code with its header's slicer line in Creality Print's words, as Orca's own K2 profile
    does. The K2's job parser (virtual_sdcard.cur_print_data, behind its screen) reads Creality Print's
    files as slicer "Creality" with their time; Moonraker's metadata reads every file as "Unknown",
    Creality Print's too, so it can't tell us more. The truth stays in the file, after the header."""
    with open(src, 'rb') as fi, open(dest, 'wb') as fo:
        head = fi.read(4096).decode('latin-1')
        m = re.search(r'; generated by (OrcaSlicer \S+) on (.+)\n', head)
        if m:
            head = head.replace(m.group(0), '; generated by Creality_Print V7.0.1.4212 on %s\n' % m.group(2))
            head = head.replace('; HEADER_BLOCK_END\n', '; HEADER_BLOCK_END\n; sliced by %s (tools/orca.py)\n'
                                % m.group(1), 1)
        fo.write(head.encode('latin-1'))
        shutil.copyfileobj(fi, fo)


def slice_parts(stls, name=None, sets=(), outdir=GCODE):
    """slice the STLs onto one plate; returns the G-code's path. One part keeps its drawn orientation,
    centred on the bed; several are left to Orca's arrange."""
    name = name or os.path.splitext(os.path.basename(stls[0]))[0]
    work = tempfile.mkdtemp(prefix='orca_')
    if len(stls) == 1:
        stls = [centred(stls[0], os.path.join(work, os.path.basename(stls[0])))]
    files = []
    for kind, d in zip(('machine', 'process', 'filament'), presets(sets)):
        files.append(os.path.join(work, kind + '.json'))
        with open(files[-1], 'w', encoding='utf-8') as fh:
            json.dump(d, fh, indent=1)
    cmd = [ORCA, '--datadir', os.path.join(work, 'datadir'),
           '--load-settings', files[0] + ';' + files[1], '--load-filaments', files[2],
           '--arrange', '1' if len(stls) > 1 else '0', '--orient', '0', '--slice', '0',
           '--outputdir', work] + \
          [os.path.abspath(s) for s in stls]
    r = subprocess.run(cmd, cwd=work, capture_output=True, text=True, timeout=900,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    plate = os.path.join(work, 'plate_1.gcode')
    if not os.path.isfile(plate):
        log = os.path.join(work, '00000.log')
        err = open(log, errors='ignore').read() if os.path.isfile(log) else r.stderr
        raise SystemExit('Orca failed (exit %s):\n%s' % (r.returncode, err[-2000:]))
    os.makedirs(outdir, exist_ok=True)
    s = summary(plate)
    hm = re.findall(r'(\d+)([hms])', s['time'] or '')
    tag = ''.join(n + u for n, u in hm if u in 'hm') or 'x'
    dest = os.path.join(outdir, '%s_orca_PLA_%s.gcode' % (name, tag))
    creality_header(plate, dest)
    os.remove(plate)
    shutil.rmtree(work, ignore_errors=True)
    return dest, s


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('stl', nargs='+')
    ap.add_argument('--set', action='append', default=[], metavar='KEY=VALUE')
    ap.add_argument('--name')
    ap.add_argument('--out', default=GCODE)
    ap.add_argument('--draft', action='store_true', help='PLA test parts: speed over finish (DRAFT)')
    a = ap.parse_args()
    path, s = slice_parts(a.stl, a.name, (DRAFT if a.draft else []) + a.set, a.out)
    print(path)
    print('  %(time)s, %(grams)s g, %(layers)s layers, %(height)s mm tall, supports: %(support)s, '
          'start G-code ok: %(start_ok)s' % s)
    if not s['start_ok']:
        sys.exit('start G-code check failed: read the file before sending it')
