"""How much the Pi's WiFi really carries, Pi to desktop, the direction video goes (review C7, 2026-11-08).

Off the wall, WiFi is the robot's only link, and in July it managed only 2.5-5 Mbps with the Pi inside the old chassis
(FPVTank_Control docs/bench/2026-07-14-camera-probe-plan.md, T7). 720p30 needs 4.4 Mbps on the cable, so the bar here is 6.

    python twin/wifi_test.py "bench, power save as is"       # one 20 s run: Mbps, the worst second, signal; logged
    python twin/wifi_test.py --self-test                     # the meter against streams of known rate, with a control

It pulls zeros over ssh, as July's test did, so the Pi's end needs nothing installed. Power save is set by hand.
"""
import argparse, json, os, re, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import config

HOST = config.PI_SSH                    # user@address of the Pi, kept out of the repo (tools/config_local.py, or FPVTANK_PI_SSH)
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8', '-o', 'Compression=no']
NEED, BAR = 4.4, 6.0                    # Mbps: what 720p30 took on the cable (measured), and a margin over it (picked)
LOG = os.path.join(config.TWIN_OUT, 'wifi_test.jsonl')


def measure(cmd, seconds):
    """Reads cmd's stdout for `seconds`: (mean Mbps, list of per-second Mbps). A stall can't hang it: the read has its own thread."""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
    bins = [0] * int(seconds)
    t0 = [None]

    def pump():
        while True:
            b = p.stdout.read(65536)
            if not b:
                return
            if t0[0] is None:                 # the clock starts at the first byte, so ssh's connection time doesn't count
                t0[0] = time.monotonic()
            i = int(time.monotonic() - t0[0])
            if i < len(bins):
                bins[i] += len(b)
    th = threading.Thread(target=pump, daemon=True)
    th.start()
    start = time.monotonic()
    while time.monotonic() - start < seconds + 12:
        if t0[0] is not None and time.monotonic() - t0[0] >= seconds:
            break
        time.sleep(0.05)
    p.kill()
    per_s = [b * 8 / 1e6 for b in bins]
    return sum(per_s) / len(per_s), per_s


def verdict(mean):
    return 'carries 720p30' if mean >= BAR else ('tight: 720p30 only just fits' if mean >= NEED else 'too slow for 720p30')


def self_test():
    """A local stream of known rate must read back at that rate, and the slow one must fail the bar."""
    # paced by the clock: a fixed sleep runs slow on Windows, whose timer ticks every 15.6 ms
    src = ("import sys,time\nt0=time.monotonic();sent=0\nwhile True:\n    due=int((time.monotonic()-t0)*%d)\n"
           "    if due>sent:\n        sys.stdout.buffer.write(bytes(due-sent));sys.stdout.buffer.flush();sent=due\n    else:\n        time.sleep(0.001)\n")
    ok = True
    for name, rate, want, passes in (('1 MB/s', 1000000, 8.0, True), ('control, 0.25 MB/s', 250000, 2.0, False)):
        mean, per_s = measure([sys.executable, '-c', src % rate], 6)
        good = abs(mean - want) < want * 0.25 and (mean >= BAR) == passes
        ok &= good
        print('%-20s reads %5.2f Mbps (about %.1f expected): %-30s %s' % (name, mean, want, verdict(mean), 'ok' if good else 'WRONG'))
    return 0 if ok else 1


def link():
    r = subprocess.run(SSH + [HOST, '/usr/sbin/iw dev wlan0 link; /usr/sbin/iw dev wlan0 get power_save; cat /sys/class/thermal/thermal_zone0/temp'],
                       capture_output=True, text=True, timeout=30)
    s = r.stdout
    if r.returncode:
        raise SystemExit('the Pi did not answer over ssh: ' + r.stderr.strip()[:200])

    def g(pat):
        m = re.search(pat, s)
        return m.group(1) if m else '?'
    return dict(signal_dBm=g(r'signal: (-?\d+)'), freq_MHz=g(r'freq: (\d+)'), tx=g(r'tx bitrate: ([\d.]+)'), power_save=g(r'Power save: (\w+)'))


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    a.add_argument('label', nargs='?', help='where the Pi is and what is set, in words')
    a.add_argument('--seconds', type=int, default=20)
    a.add_argument('--self-test', action='store_true')
    o = a.parse_args()
    if o.self_test:
        sys.exit(self_test())
    if not o.label:
        a.error('say where the Pi is')
    if not HOST:
        a.error("no Pi address: write PI_SSH = '<user>@<pi-ip>' in tools/config_local.py, or set FPVTANK_PI_SSH")
    before = link()
    mean, per_s = measure(SSH + [HOST, 'cat /dev/zero'], o.seconds)
    row = dict(label=o.label, mean_Mbps=round(mean, 2), worst_s_Mbps=round(min(per_s), 2), best_s_Mbps=round(max(per_s), 2),
               seconds_under_need=sum(x < NEED for x in per_s), seconds=o.seconds, time=time.strftime('%Y-%m-%d %H:%M'), **before)
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(json.dumps(row) + '\n')
    print('%s: %.1f Mbps mean, worst second %.1f, %d of %d s under %.1f | signal %s dBm, %s MHz, PHY %s, power save %s | %s' % (
        o.label, mean, min(per_s), row['seconds_under_need'], o.seconds, NEED, before['signal_dBm'], before['freq_MHz'], before['tx'], before['power_save'], verdict(mean)))
