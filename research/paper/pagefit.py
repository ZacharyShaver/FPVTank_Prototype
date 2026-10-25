"""Does a draft fit its pages? The test is print itself: print each sheet alone and find how much room it has left.

    python research/paper/pagefit.py research/paper/checks-that-can-fail-v4.html --print   # the test, about 3 min
    python research/paper/pagefit.py research/paper/checks-that-can-fail-v4.html --pdf     # the 3-page PDF check
    python research/paper/pagefit.py research/paper/checks-that-can-fail-v4.html           # _measure.html (screen)

--print: each sheet is printed on its own by headless Edge (the same Skia PDF engine as the print dialog's "Save as
PDF"), with a blank spacer at its foot; the tallest spacer that still fits on one page is its spare room. A sheet that
overflows is measured by shrinking the bottom margin instead. Control: v3, which fit, reads 0.04 / 0.22 / 0.07 in
with its original CSS. Keep each sheet at 0.1 in or more.

Lessons (2026-10-25):
- Screen measurement is not enough. v4 measured 0.36 / 0.32 / 0.25 in on screen but printed at 5 pages. The cause
  was the print CSS: it reset the body's padding, not its default 8px margin, so print had 16px less width and less
  height than designed. v4's print CSS sets `margin:0`; it now prints at 0.30 / 0.22 / 0.15 in.
- Make the PDF with "Save as PDF" or with --pdf. The "Microsoft Print to PDF" printer lays the page out again, with
  its own margins and headers, and adds pages.
- Headless Edge writes the PDF a few seconds after its process exits, so print_pdf waits for the file. It needs its
  own profile, or it hands the job to an open Edge and prints nothing.
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


def print_spare(html, step=0.04, top=1.2):
    """Each sheet's spare room as print lays it out: print the sheet alone with a blank spacer at its foot, and find
    the tallest spacer that still fits on one page. Negative means the sheet itself overflows (and by how much)."""
    src = open(html, encoding='utf-8').read()
    head, rest = src.split('<section', 1)
    sheets = ['<section' + s for s in rest.split('<section')]
    sheets = [s[:s.rindex('</section>')] for s in sheets]
    d = os.path.dirname(html)
    out = []
    for i, body in enumerate(sheets):
        def pages(h):                                     # h > 0: a spacer that tall; h < 0: the bottom margin |h| smaller
            tmp = os.path.join(d, f'_sheet{i + 1}.html')
            extra = (f'<div style="height:{h:.3f}in"></div>' if h > 0 else '')
            page = (f'<style>@page{{margin:{MY}in {MX}in {MY + h:.3f}in}}</style>' if h < 0 else '')
            open(tmp, 'w', encoding='utf-8').write(head + page + body + extra + '</section>\n')
            try:
                return print_pdf(tmp, tmp[:-5] + '.pdf')
            finally:
                for f in (tmp, tmp[:-5] + '.pdf'):
                    if os.path.exists(f):
                        os.remove(f)
        if pages(0) > 1:                                  # over: how much more page it needs, by shrinking the margin
            lo, hi = -MY, 0.0                             # lo fits (no bottom margin at all), hi does not
            if pages(lo) > 1:
                out.append((i + 1, -9.99)); continue
            while hi - lo > step:
                mid = (lo + hi) / 2
                lo, hi = (mid, hi) if pages(mid) == 1 else (lo, mid)
            out.append((i + 1, lo)); continue
        lo, hi = 0.0, top                                 # lo fits; find the edge
        if pages(hi) == 1:
            out.append((i + 1, hi)); continue
        while hi - lo > step:
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if pages(mid) == 1 else (lo, mid)
        out.append((i + 1, lo))
    return out


if __name__ == '__main__':
    html = os.path.abspath(sys.argv[1])
    if '--print' in sys.argv:                             # the real test: print layout, sheet by sheet
        for i, s in print_spare(html):
            print(f'sheet {i}: ' + (f'spare {s:.2f} in in print' if s >= 0 else f'OVER by about {-s:.2f} in in print'))
    else:
        print('open', measure_page(html), 'in a browser to read each sheet\'s spare room (screen layout)')
    if '--pdf' in sys.argv:
        pdf = html[:-5] + '.pdf'
        print(f'{os.path.basename(pdf)}: {print_pdf(html, pdf)} pages')
