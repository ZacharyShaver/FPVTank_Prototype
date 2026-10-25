"""Does a draft fit its pages? Write a page that measures each sheet's spare room, laid out as Edge prints it.

    python research/paper/pagefit.py research/paper/checks-that-can-fail-v4.html          # writes _measure.html
    python research/paper/pagefit.py research/paper/checks-that-can-fail-v4.html --pdf    # also a headless PDF (see 3)

1. `_measure.html`, beside the draft: the figure embedded, the print styles forced on, each sheet at the printable width
   (8.5 in less the @page margins) and at the draft's 10.2 pt, so lines wrap as in print. Open it in a browser; the
   spare room of each sheet is printed at the bottom. Control: v3 measures 0.36 / 0.32 / 0.35 in, the margins its
   commits recorded, and its PDF from Edge's print dialog shows the same line breaks.
2. Keep each sheet about a line (0.19 in) or more, then make the PDF from Edge's print dialog (US Letter, default
   margins) and check it has 3 pages. Delete `_measure.html` after.
3. Headless Edge (--print-to-pdf) does NOT print this paper as the dialog does: it skips the serif's optical sizing,
   so its lines hold fewer words. v4, fitting with 0.25 in or more by (1), came out at 5 pages headless (2026-10-25).
   Use it only as a rough check. It also writes the file a few seconds after the process exits, so this waits.
"""
import os, sys, re, time, base64, subprocess, tempfile

EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
PAGE_W, PAGE_H, MX, MY, PT = 8.5, 11.0, 0.66, 0.55, 10.2   # inches and the body size; must match the draft's CSS

MEASURE = """
<style>
  :root{--paper:#fff;--ink:#111;color-scheme:light}
  body{background:#fff;padding:0;margin:0}
  .sheet{box-shadow:none;margin:0 0 40px;padding:0 !important;max-width:none;width:%(w)sin;font-size:%(pt)spt !important}
  /* !important: in a hidden or narrow browser pane the draft's phone-width rule (11pt) would apply */
  .ph{background:none;padding:0}
</style>
<script>
  window.addEventListener('load', () => document.fonts.ready.then(() => {
    const ppi = 96, out = [...document.querySelectorAll('.sheet')].map((s, i) => {
      const r = s.getBoundingClientRect(), last = [...s.querySelectorAll('*')].reduce((m, e) => Math.max(m, e.getBoundingClientRect().bottom), r.top);
      return `sheet ${i + 1}: ${((last - r.top) / ppi).toFixed(2)} in of ${%(h)s} in, spare ${(%(h)s - (last - r.top) / ppi).toFixed(2)} in`;
    });
    const pre = document.createElement('pre'); pre.id = 'FIT'; pre.textContent = out.join('\\n'); document.body.appendChild(pre);
  }));
</script>
"""


def measure_page(html):
    src = open(html, encoding='utf-8').read()
    d = os.path.dirname(html)
    src = re.sub(r'src="([^"]+\.png)"', lambda m: 'src="data:image/png;base64,' + base64.b64encode(
        open(os.path.join(d, m.group(1)), 'rb').read()).decode() + '"', src)
    out = os.path.join(d, '_measure.html')
    open(out, 'w', encoding='utf-8').write(src + MEASURE % dict(w=PAGE_W - 2 * MX, h=PAGE_H - 2 * MY, pt=PT))
    return out


def print_pdf(html, pdf, wait=90):
    if os.path.exists(pdf):
        os.remove(pdf)
    with tempfile.TemporaryDirectory() as prof:          # its own profile, or it hands the job to an open Edge
        subprocess.run([EDGE, '--headless=new', '--disable-gpu', '--no-pdf-header-footer', '--virtual-time-budget=20000',
                        f'--user-data-dir={prof}', f'--print-to-pdf={pdf}', 'file:///' + html.replace(os.sep, '/')],
                       capture_output=True, timeout=180)
        t0, last = time.time(), -1
        while time.time() - t0 < wait:                    # the file lands after the process exits
            size = os.path.getsize(pdf) if os.path.exists(pdf) else -1
            if size > 0 and size == last:
                break
            last = size; time.sleep(2)
    if not os.path.exists(pdf):
        sys.exit('Edge wrote no PDF')
    return len(re.findall(rb'/Type\s*/Page[^s]', open(pdf, 'rb').read()))


if __name__ == '__main__':
    html = os.path.abspath(sys.argv[1])
    print('open', measure_page(html), 'in a browser to read each sheet\'s spare room')
    if '--pdf' in sys.argv:
        pdf = html[:-5] + '_headless.pdf'
        print(f'{os.path.basename(pdf)}: {print_pdf(html, pdf)} pages (headless: rough only, see the docstring)')
