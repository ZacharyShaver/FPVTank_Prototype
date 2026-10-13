"""Drive Zach's Creality K2 Pro through its stock Moonraker API (config.PRINTER).

    python tools/k2.py status                    # state, job, progress, temperatures
    python tools/k2.py files [N]                 # the newest G-codes on the printer
    python tools/k2.py history [N]               # past jobs: completed, cancelled
    python tools/k2.py upload FILE.gcode         # copy to the printer; doesn't start it
    python tools/k2.py start NAME --bed-clear    # start a G-code already on the printer
    python tools/k2.py pause | resume | cancel
    python tools/k2.py watch [SECONDS]           # print status lines until the job ends

Nothing here can see the bed: the printer's camera isn't on Moonraker. So `start` wants --bed-clear,
said only after Zach has said the last part is off the plate. It also refuses unless the printer is idle
and the filament sensor sees filament. Pause and cancel run Creality's own PAUSE and CANCEL_PRINT macros.
Slice with tools/orca.py."""
import argparse, datetime, os, sys, time
import requests
import config

IDLE = ('standby', 'complete', 'cancelled', 'error')


def api(method, path, **kw):
    r = requests.request(method, config.PRINTER + path, timeout=kw.pop('timeout', 10), **kw)
    if not r.ok:
        raise SystemExit('%s %s -> %s %s' % (method, path, r.status_code, r.text[:300]))
    j = r.json()
    return j.get('result', j)  # the upload's reply isn't wrapped in 'result'


def query(*objs):
    return api('GET', '/printer/objects/query?' + '&'.join(o.replace(' ', '%20') for o in objs))['status']


def status():
    s = query('print_stats', 'virtual_sdcard', 'extruder', 'heater_bed', 'display_status',
              'filament_switch_sensor filament_sensor')
    ps, sd = s['print_stats'], s['virtual_sdcard']
    line = '%s' % ps['state']
    if ps['filename']:
        done = sd['progress']
        el = ps['print_duration']
        eta = ' (~%s left)' % fmt(el / done - el) if done > 0.02 else ''
        line += ', %s: %.1f %%, layer %s/%s, %s in%s' % (
            ps['filename'], 100 * done, ps['info'].get('current_layer'), ps['info'].get('total_layer'),
            fmt(ps['total_duration']), eta)
    line += ' | nozzle %.0f/%.0f, bed %.0f/%.0f, filament %s' % (
        s['extruder']['temperature'], s['extruder']['target'], s['heater_bed']['temperature'],
        s['heater_bed']['target'],
        'in' if s['filament_switch_sensor filament_sensor']['filament_detected'] else 'OUT')
    if ps['message']:
        line += ' | ' + ps['message']
    return ps['state'], line


def fmt(sec):
    sec = int(sec)
    return '%dh%02dm' % (sec // 3600, sec // 60 % 60)


def when(t):
    return datetime.datetime.fromtimestamp(t).strftime('%m-%d %H:%M') if t else '-'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('cmd', choices=['status', 'files', 'history', 'upload', 'start', 'pause', 'resume',
                                    'cancel', 'watch'])
    ap.add_argument('arg', nargs='?')
    ap.add_argument('--bed-clear', action='store_true', help='Zach has said the plate is empty')
    a = ap.parse_args()

    if a.cmd == 'status':
        print(status()[1])
    elif a.cmd == 'files':
        fs = sorted(api('GET', '/server/files/list?root=gcodes'), key=lambda f: -f['modified'])
        for f in fs[:int(a.arg or 10)]:
            print(when(f['modified']), '%6.1f MB' % (f['size'] / 1e6), f['path'])
    elif a.cmd == 'history':
        for j in api('GET', '/server/history/list?limit=%d' % int(a.arg or 10))['jobs']:
            print(when(j['start_time']), when(j.get('end_time')), '%-9s' % j['status'],
                  fmt(j.get('print_duration') or 0), j['filename'])
    elif a.cmd == 'upload':
        with open(a.arg, 'rb') as fh:
            r = api('POST', '/server/files/upload', files={'file': (os.path.basename(a.arg), fh)},
                    data={'root': 'gcodes'}, timeout=300)
        print('uploaded', r['item']['path'])
    elif a.cmd == 'start':
        state, line = status()
        names = [f['path'] for f in api('GET', '/server/files/list?root=gcodes')]
        if a.arg not in names:
            sys.exit('not on the printer: %s (upload it first)' % a.arg)
        if state not in IDLE:
            sys.exit('printer is busy: ' + line)
        if 'filament OUT' in line:
            sys.exit('no filament: ' + line)
        if not a.bed_clear:
            sys.exit('say --bed-clear, once Zach has said the plate is empty')
        api('POST', '/printer/print/start', params={'filename': a.arg})
        time.sleep(3)
        print(status()[1])
    elif a.cmd in ('pause', 'resume', 'cancel'):
        # Moonraker answers only once the macro has run: CANCEL_PRINT took over 10 s (2026-10-04), and the
        # cancel went through while the call timed out
        api('POST', '/printer/print/' + a.cmd, timeout=60)
        time.sleep(2)
        print(status()[1])
    elif a.cmd == 'watch':
        every, last = int(a.arg or 60), None
        while True:
            state, line = status()
            if line != last:
                print(time.strftime('%H:%M:%S'), line, flush=True)
                last = line
            if state in IDLE:
                break
            time.sleep(every)


if __name__ == '__main__':
    main()
