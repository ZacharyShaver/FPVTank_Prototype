# tools/tests/test_site.py
import os, re, sys, unittest
import numpy as np
from html.parser import HTMLParser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from gallery import build as B   # tools/gallery: not 'site', which is a standard-library module


class Pages(unittest.TestCase):
    def test_wrap_adds_a_head_once(self):
        w = B.wrap_page('<title>T</title><div>x</div>', '../index.html')
        self.assertTrue(w.lower().startswith('<!doctype html>'))
        self.assertIn('<meta charset="utf-8">', w)
        self.assertIn('href="../index.html"', w)
        self.assertEqual(B.wrap_page(w, '../index.html').count('<!doctype html>'), 1)   # idempotent

    def test_page_with_its_own_head_is_left_alone(self):
        p = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>T</title></head><body>x</body></html>'
        self.assertEqual(B.wrap_page(p, '../index.html').count('<meta charset'), 1)

    def test_private_links_are_stripped(self):
        h = '<a href="https://claude.ai/artifact/0123abcd-4567-89ab-cdef-0123456789ab">the hull page</a> and https://claude.ai/code/artifact/abc-123'
        s = B.strip_private_links(h)
        self.assertNotIn('claude.ai', s); self.assertIn('the hull page', s)

    def test_local_refs(self):
        h = ('<script src="https://cdnjs.cloudflare.com/x.js"></script><img src="thumbs/a.jpg">'
             '<a href="#top">t</a><a href="pages/b.html">b</a><img src="data:image/png;base64,AAAA">')
        self.assertEqual(sorted(B.local_refs(h)), ['pages/b.html', 'thumbs/a.jpg'])


BOM = chr(0xFEFF)                                 # a byte-order mark, as a file saved by some editors starts
ID = '0123abcd-4567-89ab-cdef-0123456789ab'      # fake ids only
ID2 = 'Ab_Cd-Ef_12'                              # letters, digits, '-' and '_'
FORMS = [                                        # every shape a private artifact link can take
    r'https://claude.ai/artifact/{id}', r'https://claude.ai/code/artifact/{id}', r'http://claude.ai/artifact/{id}',
    r'http://claude.ai/code/artifact/{id}', r'HTTPS://CLAUDE.AI/ARTIFACT/{id}', r'Https://Claude.Ai/Code/Artifact/{id}',
    r'https://www.claude.ai/artifact/{id}', r'http://www.claude.ai/code/artifact/{id}',
    r'claude.ai/artifact/{id}', r'www.claude.ai/code/artifact/{id}', r'//claude.ai/artifact/{id}', r'//www.claude.ai/code/artifact/{id}',
    r'https:\/\/claude.ai\/artifact\/{id}', r'https:\/\/claude.ai\/code\/artifact\/{id}',
    r'https:\\/\\/claude.ai\\/artifact\\/{id}',
    r'https%3A%2F%2Fclaude.ai%2Fartifact%2F{id}', r'https%3a%2f%2fclaude.ai%2fcode%2fartifact%2f{id}',
    r'https%253A%252F%252Fclaude.ai%252Fartifact%252F{id}',
    'https:@u002f@u002fclaude.ai@u002fartifact@u002f{id}'.replace('@', chr(92)),     # JS unicode escapes
    'https:@u002F@u002Fclaude.ai@u002Fcode@u002Fartifact@u002F{id}'.replace('@', chr(92)),
    r'https&#58;&#47;&#47;claude.ai&#47;artifact&#47;{id}', r'https&#x3a;&#x2f;&#x2f;claude.ai&#x2f;artifact&#x2f;{id}',
    r'https://claude.ai/public/artifacts/{id}', r'https://claude.ai/public/artifact/{id}', r'HTTPS://CLAUDE.AI/PUBLIC/ARTIFACTS/{id}',
    r'claude.ai/public/artifacts/{id}', r'https%3A%2F%2Fclaude.ai%2Fpublic%2Fartifacts%2F{id}',
    r'https:\/\/claude.ai\/public\/artifacts\/{id}',
]
TAILS = ['', '/', '/sub/page', '?a=1&b=2', '#frag', '/sub?a=1#frag']
NOT_PRIVATE = [                                  # controls: none of these may change
    'https://example.com/artifact/x', 'http://example.com/code/artifact/' + ID, 'https://claude.ai/', 'https://claude.ai',
    'https://claude.ai/login', 'https://claude.ai/new', 'https://claude.ai/artifact/', 'https://claude.ai/artifacts',
    'https://claude.ai/settings/artifact/' + ID, 'https://claude.aix/artifact/' + ID, 'https://claude.ai.example.com/artifact/' + ID,
    'https://docs.anthropic.com/en/docs/claude-code', 'https://www.anthropic.com/claude', 'https://github.com/x/claude/artifact/abc',
    '//example.com/artifact/' + ID, 'artifact/' + ID,
]


class PrivateLinks(unittest.TestCase):
    def test_every_form_is_removed_in_plain_text(self):
        for f in FORMS:
            for i in (ID, ID2):
                for t in TAILS:
                    with self.subTest(form=f.replace('{id}', 'ID'), id=i, tail=t):
                        s = B.strip_private_links('see ' + f.format(id=i) + t + ' now')
                        self.assertEqual(s, 'see  now')                 # the whole URL, path/query/fragment too

    def test_removed_inside_json_and_js_strings(self):
        for f in FORMS:
            for q, j in (('"', '{"u":%s,"k":1}'), ("'", "var u=[%s,2];")):
                with self.subTest(form=f.replace('{id}', 'ID'), quote=q):
                    s = B.strip_private_links(j % (q + f.format(id=ID2) + '/x?y=1' + q))
                    self.assertEqual(s, j % (q + q))

    def test_anchor_is_unwrapped_and_text_kept(self):
        for f in FORMS:
            for a in ('<a href="%s">the hull page</a>', "<a href='%s'>the hull page</a>",
                      '<a class="c" href="%s" target="_blank">the hull page</a>', '<A HREF="%s">the hull page</A>',
                      '<a href="%s"><b>the</b> hull page</a>'):
                with self.subTest(form=f.replace('{id}', 'ID'), a=a):
                    s = B.strip_private_links('x ' + a % (f.format(id=ID) + '/p?q=1#f') + ' y')
                    self.assertNotIn('<a', s.lower()); self.assertNotIn('</a', s.lower())      # the tag is gone, not just the URL
                    self.assertEqual(re.sub(r'</?b>', '', s), 'x the hull page y')

    def test_markdown_link_keeps_its_text(self):
        for f in FORMS:
            with self.subTest(form=f.replace('{id}', 'ID')):
                self.assertEqual(B.strip_private_links('see [the hull page](%s) now' % f.format(id=ID)), 'see the hull page now')
                self.assertEqual(B.strip_private_links('see [t](%s "a title") now' % f.format(id=ID2)), 'see t now')

    def test_many_links_in_one_page_all_go(self):
        sep = ' and claude.ai is a site, https://claude.ai/ too; '
        for h in (sep.join(f.format(id=ID) for f in FORMS), sep.join(f.format(id=ID2) + '/p?q=1' for f in FORMS)):
            s = B.strip_private_links(h)
            self.assertEqual(s, sep.join([''] * len(FORMS)))                 # every one removed, the neighbours kept
            self.assertNotIn(ID, s); self.assertNotIn(ID2, s)
        self.assertEqual(B.strip_private_links('x https://claude.ai/artifact/%s y https://claude.ai/artifact/%s z' % (ID, ID2)), 'x  y  z')

    def test_two_links_on_one_line_and_neighbours_survive(self):
        h = ('<a href="https://claude.ai/artifact/%s">A</a> keep https://example.com/artifact/x <a href="https://example.com/p">B</a> '
             'and https://claude.ai/code/artifact/%s' % (ID, ID2))
        self.assertEqual(B.strip_private_links(h), 'A keep https://example.com/artifact/x <a href="https://example.com/p">B</a> and ')

    def test_non_private_links_are_unchanged(self):                      # controls: an over-broad pattern fails here
        for u in NOT_PRIVATE:
            for h in ('%s', 'see %s now', '<a href="%s">t</a>', '{"u":"%s"}', '[t](%s)'):
                with self.subTest(u=u, h=h):
                    self.assertEqual(B.strip_private_links(h % u), h % u)

    def test_big_data_uri_and_minified_js_are_unchanged(self):
        big = '<img src="data:image/png;base64,' + 'QUJDREVG' * 262144 + '">'                       # 2 MB
        self.assertEqual(B.strip_private_links(big), big)
        js = '<script>function n(e){var claude=e.claude||{};return claude.ai&&claude.artifact(e)?claude.ai:"claude"}</script>'
        self.assertEqual(B.strip_private_links(js), js)
        self.assertEqual(B.strip_private_links(big + js), big + js)


class Anchors(HTMLParser):
    """Collects every start tag as (tag, attrs dict) and the text inside <a>."""
    def __init__(self):
        super().__init__(); self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def tags(html_text, tag):
    p = Anchors(); p.feed(html_text)
    return [a for t, a in p.tags if t == tag]


class Wrap(unittest.TestCase):
    P = '<title>T</title><div>x</div>'

    def test_double_wrap_gives_one_doctype_and_one_back_link(self):
        once = B.wrap_page(self.P, '../index.html')
        twice = B.wrap_page(once, '../index.html')
        for w in (once, twice, B.wrap_page(twice, '../index.html')):
            self.assertEqual(w.lower().count('<!doctype'), 1)
            self.assertEqual(w.count('data-gallery-back'), 1)
        self.assertEqual(twice, once)                                    # and byte-for-byte idempotent

    def test_a_leading_bom_counts_as_nothing_before_the_doctype(self):
        w = B.wrap_page(BOM + '<!doctype html><title>T</title>', 'i.html')
        self.assertEqual(w.lower().count('<!doctype'), 1)
        self.assertEqual(w.lower().count('<meta charset'), 0)            # it had a doctype: left alone
        c = B.wrap_page(BOM + '<div>x</div>', 'i.html')                   # control: no doctype, so one is added
        self.assertEqual(c.lower().count('<!doctype'), 1); self.assertIn('<meta charset="utf-8">', c)
        self.assertTrue(c.startswith('<!doctype html>'))

    def test_leading_comments_count_as_nothing_before_the_doctype(self):
        for pre in ('<!-- x -->', '<!-- a --><!-- b -->', BOM + '<!-- x -->\n  <!-- multi\nline -->\n', '  <!-- x -->  '):
            with self.subTest(pre=pre):
                w = B.wrap_page(pre + '<!DOCTYPE html><html><head></head><body>x</body></html>', 'i.html')
                self.assertEqual(w.lower().count('<!doctype'), 1)
                self.assertTrue(w.startswith(pre))                       # nothing was put in front of it
        c = B.wrap_page('<!-- x --><div>x</div>', 'i.html')              # control: a comment is no doctype
        self.assertEqual(c.lower().count('<!doctype'), 1); self.assertTrue(c.startswith('<!doctype html>'))
        c = B.wrap_page('<div>x</div><!doctype html>', 'i.html')         # control: a doctype later on is no doctype
        self.assertTrue(c.startswith('<!doctype html>')); self.assertEqual(c.lower().count('<!doctype'), 2)

    def test_rewrapping_with_a_different_back_replaces_the_link(self):
        w = B.wrap_page(B.wrap_page(self.P, 'a/one.html'), 'b/two.html')
        self.assertEqual(w.count('data-gallery-back'), 1)
        self.assertIn('href="b/two.html"', w); self.assertNotIn('a/one.html', w)
        w = B.wrap_page(B.wrap_page(B.wrap_page(self.P, '1.html'), '2.html'), '3.html')
        self.assertEqual([a['href'] for a in tags(w, 'a')], ['3.html'])
        self.assertTrue(w.startswith('<!doctype html>') and w.count('<title>') == 1 and '<div>x</div>' in w)   # the page is intact

    def test_back_is_escaped_for_the_attribute(self):
        for back in ('a"b onmouseover="x', "a'b", 'a&b=1', 'a<b>c', 'x".html?q=1&r="2'):
            with self.subTest(back=back):
                a = tags(B.wrap_page(self.P, back), 'a')
                self.assertEqual(len(a), 1); self.assertEqual(a[0]['href'], back)      # one attribute, value intact
                self.assertNotIn('onmouseover', a[0])
        self.assertEqual(len(tags(B.wrap_page(self.P, '../index.html'), 'a')), 1)    # control

    def test_link_is_labelled_and_the_arrow_is_hidden_from_screen_readers(self):
        w = B.wrap_page(self.P, 'i.html')
        a = tags(w, 'a')[0]
        self.assertEqual(a['aria-label'], 'Back to the gallery')
        self.assertIn('position:fixed', a['style']); self.assertIn('env(safe-area-inset-bottom', a['style'])
        self.assertIn('env(safe-area-inset-left', a['style'])
        spans = tags(w, 'span'); self.assertEqual(len(spans), 1); self.assertEqual(spans[0]['aria-hidden'], 'true')
        self.assertRegex(w, r'<span aria-hidden="true">&larr;</span>')   # the arrow is inside the hidden span


class LocalRefs(unittest.TestCase):
    KEEP = '<img src="keep.png">'

    def test_attribute_forms_quoted_unquoted_any_case(self):
        for h, want in (('<img src="a.png">', 'a.png'), ("<img src='b.png'>", 'b.png'), ('<img src=c.png>', 'c.png'),
                        ('<IMG SRC="d.png">', 'd.png'), ("<A HREF='e.html'>e</A>", 'e.html'), ('<a href=f.html>f</a>', 'f.html'),
                        ('<a href = "g.html">g</a>', 'g.html'), ('<a\nhref\n=\n\'h.html\'>h</a>', 'h.html'),
                        ('<link rel=stylesheet href=i.css>', 'i.css'), ('<script src=j.js></script>', 'j.js'),
                        ('<a HrEf="k.html">k</a>', 'k.html'), ('<image xlink:href="l.png"/>', 'l.png')):
            with self.subTest(h=h):
                self.assertEqual(B.local_refs(h), [want])
                self.assertEqual(B.local_refs(h + self.KEEP), [want, 'keep.png'])           # in page order, with a neighbour

    def test_srcset_candidates(self):
        for h, want in (('<img srcset="s1.png 1x, s2.png 2x">', ['s1.png', 's2.png']),
                        ("<source SRCSET='s3.png 100w,s4.png 200w'>", ['s3.png', 's4.png']),
                        ('<img srcset="s5.png, s6.png 2x">', ['s5.png', 's6.png']),
                        ('<img src="s0.png" srcset=s7.png>', ['s0.png', 's7.png']),
                        ('<img srcset="https://x.example/a.png 1x, s8.png 2x, data:image/png;base64,AAAA 3x, //x.example/b.png 4x">', ['s8.png']),
                        ('<img srcset="dir/s9.png?v=1 1x, my%20s10.png 2x">', ['dir/s9.png', 'my s10.png'])):
            with self.subTest(h=h):
                self.assertEqual(B.local_refs(h), want)

    def test_css_urls_in_style_blocks_and_attributes(self):
        css = ('.a{background:url(u1.png)} .b{background:url("u2.png")} .c{background:url( \'u3.png\' )} @import url(u4.css); '
               '.d{background:URL(u5.png?v=1#x)} .e{background:url(data:image/png;base64,AAAA)} .f{background:url(https://x.example/f.png)} '
               '.g{background:url(//x.example/g.png)} .h{background:url(#frag)}')
        self.assertEqual(B.local_refs('<style>' + css + '</style>'), ['u1.png', 'u2.png', 'u3.png', 'u4.css', 'u5.png'])
        self.assertEqual(B.local_refs('<STYLE media="print">' + css + '</STYLE>' + self.KEEP),
                         ['u1.png', 'u2.png', 'u3.png', 'u4.css', 'u5.png', 'keep.png'])
        for h, want in (('<div style="background:url(a1.png)">', 'a1.png'), ("<div style='background:url(\"a2.png\")'>", 'a2.png'),
                        ('<div STYLE="background:url(\'a3.png\') no-repeat">', 'a3.png'),
                        ('<div style="background:url(&quot;a4.png&quot;)">', 'a4.png'),
                        ('<div style="background:url(a5.png?v=1)">', 'a5.png')):
            with self.subTest(h=h):
                self.assertEqual(B.local_refs(h), [want])
        for h in ('<div style="background:url(data:image/png;base64,AAAA)">', '<div style="background:url(https://x.example/a.png)">',
                  '<div style="color:red">', '<script>var u = new URL(location.href); var s = "url(js.png)";</script>',
                  '<p>url(prose.png) in text</p>'):                                              # controls: not CSS, or not local
            with self.subTest(h=h):
                self.assertEqual(B.local_refs(h), [])

    def test_external_data_and_anchor_refs_are_excluded(self):
        TAB = chr(9)
        for v in ('http://x.example/a', 'HTTP://x.example/a', 'https://x.example/a', 'HTTPS://X.EXAMPLE/a', 'Https://x.example/a',
                  'javascript:void(0)', 'JavaScript:alert(1)', 'java' + TAB + 'script:alert(1)', 'tel:+15550100', 'TEL:+15550100',
                  'blob:https://x.example/0123abcd', 'BLOB:null/0123', 'file:///C:/x.html', 'FILE:///x.html',
                  'mailto:a@b.example', 'MAILTO:a@b.example', 'Mailto:a@b.example', '//cdn.example/x.js', '///cdn.example/x.js',
                  'data:text/plain;base64,AAAA', 'DATA:image/png;base64,AAAA', 'Data:,hi', '#top', '#', '#a%20b',
                  'ftp://x.example/f', 'ws://x.example/s', 'wss://x.example/s', 'sms:+15550100', ' https://x.example/a ',
                  '?only=query', '?', '', chr(92) * 2 + 'cdn.example/x.js', chr(92) + '/cdn.example/x.js', '/' + chr(92) + 'cdn.example/x.js',
                  '&#104;ttps://x.example/a', 'ht&#116;ps://x.example/a', 'mail&#116;o:a@b.example'):          # entities decode to a scheme
            for tmpl in ('<a href="%s">t</a>', "<img src='%s'>", '<style>.a{background:url("%s")}</style>'):
                if tmpl.startswith('<style') and ('"' in v or v == ''):
                    continue
                with self.subTest(v=v, tmpl=tmpl):
                    self.assertEqual(B.local_refs(tmpl % v), [])
                    self.assertEqual(B.local_refs(tmpl % v + self.KEEP), ['keep.png'])          # control: the neighbour is found
        big = '<img src="data:image/png;base64,' + 'QUJDREVG' * 262144 + '">'                  # 2 MB, still excluded
        self.assertEqual(B.local_refs(big + self.KEEP), ['keep.png'])

    def test_only_real_href_and_src_attributes_count(self):
        for h in ('<img xsrc="no.png" nohref="no.html" my_src="no2.png" data_href=no3.html>',
                  '<script>var src = foo; el.src = bar; a.href=location.hash; var href = base + "x";</script>',
                  '<p>the src=foo and href=bar words</p>', '<img alt="src=no.png">', '<img onload=this.src=foo.png>'):         # controls: nothing here is a reference
            with self.subTest(h=h):
                self.assertEqual(B.local_refs(h), [])
                self.assertEqual(B.local_refs(h + self.KEEP), ['keep.png'])

    def test_js_string_building_is_not_a_reference(self):                          # lineup.html builds anchors this way
        for h in ("""<script>h = '<a href="' + u + '">x</a>';</script>""", """<script>h='<a href="'+e.link.url+'">';</script>""",
                  """<script>h = `<img src="${path}/a.png">`;</script>""", """<script>h = "<img src='" + v + "'>";</script>"""):
            with self.subTest(h=h):
                self.assertEqual(B.local_refs(h), [])
                self.assertEqual(B.local_refs(h + self.KEEP), ['keep.png'])
        self.assertEqual(B.local_refs('<img\n  alt=x\n  src=ml.png\n  >'), ['ml.png'])        # control: an unquoted one in a real tag

    def test_refs_inside_comments_are_ignored(self):
        for h in ('<!-- <img src="gone.png"> -->', '<!--<a href="gone.html">x</a>-->', '<!--\n<img src="gone.png">\n<a href="gone2.html">\n-->',
                  '<!-- a --><!-- <img src="gone.png"> --><!-- b -->', '<!-- <style>.a{background:url(gone.png)}</style> -->'):
            with self.subTest(h=h):
                self.assertEqual(B.local_refs(h), [])
                self.assertEqual(B.local_refs(h + self.KEEP), ['keep.png'])
                self.assertEqual(B.local_refs(self.KEEP + h + '<a href="after.html">a</a>'), ['keep.png', 'after.html'])

    def test_query_and_fragment_are_stripped_and_percent_decoded(self):
        for v, want in (('pages/b.html?x=1#top', 'pages/b.html'), ('pages/b.html#top', 'pages/b.html'), ('pages/b.html?x=1', 'pages/b.html'),
                        ('my%20file.html', 'my file.html'), ('a%2Fb.html#f', 'a/b.html'), ('x.png?v=1&amp;w=2', 'x.png'),
                        ('caf%C3%A9.html', 'caf' + chr(0xE9) + '.html'), ('a%23b.html', 'a#b.html'), ('a%3Fb.html?x', 'a?b.html'),
                        ('a&amp;b.html', 'a&b.html'), ('a&#46;html', 'a.html'),
                        ('../up/x.html', '../up/x.html'), ('/root/x.html', '/root/x.html'), ('plain.html', 'plain.html')):
            for tmpl in ('<a href="%s">t</a>', "<img src='%s'>", '<img srcset="%s 2x">', '<div style="background:url(%s)">'):
                with self.subTest(v=v, tmpl=tmpl):
                    self.assertEqual(B.local_refs(tmpl % v), [want])


import json, struct, tempfile
from PIL import Image


def read(*p):
    with open(os.path.join(*p), encoding='utf-8') as fh:
        return fh.read()


def put(path, data):
    with open(path, 'wb' if isinstance(data, bytes) else 'w', **({} if isinstance(data, bytes) else {'encoding': 'utf-8'})) as fh:
        fh.write(data)


def tiny_repo():
    d = tempfile.mkdtemp(); os.makedirs(os.path.join(d, 'a', 'out'))
    put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><div>3D</div>')
    Image.new('RGB', (900, 600), 'white').save(os.path.join(d, 'a', 'f.png'))
    m = {'title': 'T', 'intro': 'I', 'sections': [{'name': 'S', 'items': [
        {'id': 'p', 'kind': 'page', 'title': 'Page', 'src': 'a/out/p.html', 'thumb': 'a/f.png', 'make': 'x', 'caption': 'c1'},
        {'id': 'f', 'kind': 'figure', 'title': 'Fig', 'src': 'a/f.png', 'make': 'y', 'caption': 'c2'}]}]}
    return d, m


def box(kind, body):
    return struct.pack('>I', 8 + len(body)) + kind + body


MP4 = box(b'ftyp', b'isom\0\0\2\0isomiso2mp41') + box(b'free', b'') + box(b'mdat', bytes(16))     # a file the leak scan can read


def add_item(d, m, **item):
    m['sections'][0]['items'].append(dict(dict(kind='page', title=item['id'], make='z', caption='c'), **item))


class Build(unittest.TestCase):
    def test_a_clean_build(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site')
        r = B.build(m, d, out)
        self.assertEqual(r['problems'], []); self.assertEqual(r['items'], 2)
        idx = read(out, 'index.html')
        self.assertIn('Page', idx); self.assertIn('Fig', idx); self.assertIn('c1', idx)
        self.assertTrue(os.path.exists(os.path.join(out, 'pages', 'p.html')))
        self.assertTrue(os.path.exists(os.path.join(out, 'thumbs', 'p.jpg')))
        self.assertTrue(os.path.exists(os.path.join(out, '.nojekyll')))

    def test_missing_source_names_its_rebuild_command(self):
        d, m = tiny_repo(); os.remove(os.path.join(d, 'a', 'out', 'p.html'))
        r = B.build(m, d, os.path.join(d, 'site'), allow_missing=True)
        self.assertEqual(r['missing'], [('p', 'x')])

    def test_broken_link_fails_the_gate(self):                      # the control on the link check
        d, m = tiny_repo()
        put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><img src="nothere.png">')
        self.assertTrue(any('nothere.png' in p for p in B.build(m, d, os.path.join(d, 'site'))['problems']))

    def test_leak_fails_the_gate(self):                             # the control on the leak check
        d, m = tiny_repo()
        put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><p>C:\\Users\\jane\\Desktop</p>')
        self.assertTrue(any('user_path' in p for p in B.build(m, d, os.path.join(d, 'site'))['problems']))

    def test_size_limit_fails_the_gate(self):                       # the control on the size check
        d, m = tiny_repo()
        self.assertTrue(any('MB' in p for p in B.build(m, d, os.path.join(d, 'site'), limit_mb=0.0001)['problems']))

    def test_cards_open_their_pages_and_every_card_link_resolves(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site'); B.build(m, d, out)
        idx = read(out, 'index.html')
        hrefs = [a['href'] for a in tags(idx, 'a')]
        self.assertEqual(hrefs, ['pages/p.html', 'media/f.png'])
        for h in hrefs + B.local_refs(idx):
            self.assertTrue(os.path.exists(os.path.join(out, h)), h)
        self.assertIn('href="../index.html"', read(out, 'pages', 'p.html'))          # the way back

    def test_a_page_that_loads_siblings_keeps_them(self):
        d, m = tiny_repo(); os.makedirs(os.path.join(d, 'w'))
        put(os.path.join(d, 'w', 'v.html'), '<title>V</title><script src="data.js"></script>')
        put(os.path.join(d, 'w', 'data.js'), 'var x=1;')
        add_item(d, m, id='v', src='w/v.html', dir=True); out = os.path.join(d, 'site')
        r = B.build(m, d, out)
        self.assertEqual(r['problems'], []); self.assertTrue(os.path.exists(os.path.join(out, 'pages', 'v', 'data.js')))
        self.assertIn('href="../../index.html"', read(out, 'pages', 'v', 'v.html'))
        os.remove(os.path.join(d, 'w', 'data.js'))                                   # control: without the sibling the gate fails
        self.assertTrue(any('data.js' in p for p in B.build(m, d, out)['problems']))

    def test_private_links_are_gone_from_a_built_page(self):
        d, m = tiny_repo()
        put(os.path.join(d, 'a', 'out', 'p.html'), 
            '<title>P</title><a href="https://claude.ai/artifact/' + ID + '">the hull</a>')
        out = os.path.join(d, 'site'); r = B.build(m, d, out)
        self.assertEqual(r['problems'], []); self.assertNotIn('claude.ai', read(out, 'pages', 'p.html'))
        self.assertIn('the hull', read(out, 'pages', 'p.html'))

    def test_stripping_runs_to_a_fixed_point(self):
        nested = 'claudehttps://claude.ai/artifact/Z.ai/artifact/FAKEQ'                  # one pass leaves a new private link
        self.assertIn('claude.ai/artifact', B.strip_private_links(nested))               # control: a single pass is not enough
        self.assertNotIn('claude.ai', B.strip_all(nested))
        self.assertNotIn('claude.ai', B.strip_all(nested * 3 + 'x'))
        self.assertEqual(B.strip_all('plain <b>text</b>'), 'plain <b>text</b>')
        d, m = tiny_repo()
        put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><p>' + nested + '</p>')
        out = os.path.join(d, 'site'); r = B.build(m, d, out)
        self.assertEqual(r['problems'], []); self.assertNotIn('claude.ai', read(out, 'pages', 'p.html'))


LINKS = ('<title>L</title><script>const D={"designs":[{"id":"a","link":{"url":"https://claude.ai/artifact/%s","title":"Scorpion Hull Redesign"}},'
         '{"id":"b","link":{"url":"https:\\/\\/claude.ai\\/code\\/artifact\\/%s","title":"Scorpion Head Placement"}},'
         '{"id":"c","link":{"url":"https://claude.ai/artifact/%s","title":"Scorpion Elsewhere"}},{"id":"d","link":null}]};</script>' % (ID, ID2, ID))


class LinkPages(unittest.TestCase):
    def setUp(self):
        self.d, self.m = tiny_repo(); self.out = os.path.join(self.d, 'site')
        add_item(self.d, self.m, id='hull', src='a/out/p.html')                          # the page the first link points to
        put(os.path.join(self.d, 'a', 'out', 'l.html'), LINKS)
        add_item(self.d, self.m, id='lineup', src='a/out/l.html')
        self.m['link_pages'] = {'Scorpion Hull Redesign': 'hull', 'Scorpion Head Placement': 'nowhere'}

    def links(self):
        page = read(self.out, 'pages', 'lineup.html'); i = page.find('const D=')
        return [d['link'] for d in json.JSONDecoder().raw_decode(page, i + 8)[0]['designs']]

    def test_a_mapped_link_points_at_its_site_page_and_the_rest_are_null(self):
        r = B.build(self.m, self.d, self.out)
        self.assertEqual(r['problems'], [])
        self.assertEqual(self.links(), [{'url': 'hull.html', 'title': 'Scorpion Hull Redesign'}, None, None, None])
        self.assertTrue(os.path.exists(os.path.join(self.out, 'pages', 'hull.html')))     # and the target is in the site
        self.assertNotIn('claude.ai', read(self.out, 'pages', 'lineup.html'))

    def test_a_link_to_an_item_that_is_not_built_is_null(self):                          # control: no link into a hole
        os.remove(os.path.join(self.d, 'a', 'out', 'p.html'))                            # 'p' and 'hull' both read this file
        r = B.build(self.m, self.d, self.out, allow_missing=True)
        self.assertEqual(sorted(i for i, _ in r['missing']), ['hull', 'p'])
        self.assertEqual(self.links(), [None, None, None, None])

    def test_without_the_map_every_private_link_is_null(self):
        del self.m['link_pages']; B.build(self.m, self.d, self.out)
        self.assertEqual(self.links(), [None, None, None, None])

    def test_an_empty_json_url_is_rewritten_like_a_stripped_one(self):
        put(os.path.join(self.d, 'a', 'out', 'l.html'), 
            '<title>L</title><script>const D={"designs":[{"link":{"url":"","title":"Scorpion Hull Redesign"}}]};</script>')
        B.build(self.m, self.d, self.out)
        self.assertEqual(self.links(), [{'url': 'hull.html', 'title': 'Scorpion Hull Redesign'}])


class Video(unittest.TestCase):
    def setUp(self):
        self.d, self.m = tiny_repo(); self.out = os.path.join(self.d, 'site')
        put(os.path.join(self.d, 'a', 'v.mp4'), MP4)
        add_item(self.d, self.m, id='v', kind='video', src='a/v.mp4', thumb='a/f.png', caption='the clip')

    def test_a_video_card_opens_a_page_with_the_player(self):
        r = B.build(self.m, self.d, self.out)
        self.assertEqual(r['problems'], []); self.assertEqual(r['items'], 3)
        self.assertIn('href="pages/v.html"', read(self.out, 'index.html'))
        self.assertTrue(os.path.exists(os.path.join(self.out, 'media', 'v.mp4')))
        self.assertTrue(os.path.exists(os.path.join(self.out, 'media', 'v.png')))         # the poster
        page = read(self.out, 'pages', 'v.html')
        v = tags(page, 'video')[0]
        for k in ('controls', 'muted', 'loop', 'playsinline'):
            self.assertIn(k, v)
        self.assertEqual(v['preload'], 'metadata'); self.assertEqual(v['poster'], '../media/v.png')
        self.assertIn('../media/v.mp4', B.local_refs(page)); self.assertIn('the clip', page)
        self.assertIn('href="../index.html"', page)
        for ref in B.local_refs(page):
            self.assertTrue(os.path.exists(os.path.normpath(os.path.join(self.out, 'pages', ref))), ref)

    def test_a_video_without_a_thumb_has_no_poster_and_a_text_card(self):
        for it in self.m['sections'][0]['items']:
            if it['id'] == 'v':
                del it['thumb']
        r = B.build(self.m, self.d, self.out)
        self.assertEqual(r['problems'], [])
        self.assertNotIn('poster', tags(read(self.out, 'pages', 'v.html'), 'video')[0])
        self.assertFalse(os.path.exists(os.path.join(self.out, 'media', 'v.png')))

    def test_a_missing_video_is_listed_not_built(self):
        os.remove(os.path.join(self.d, 'a', 'v.mp4'))
        r = B.build(self.m, self.d, self.out, allow_missing=True)
        self.assertEqual(r['missing'], [('v', 'z')]); self.assertFalse(os.path.exists(os.path.join(self.out, 'pages', 'v.html')))


import contextlib, datetime, io, shutil, subprocess, types, urllib.parse
from unittest import mock


def _png():
    b = io.BytesIO(); Image.new('RGB', (4, 4), 'white').save(b, 'PNG'); return b.getvalue()


PNG = _png()


def write_files(d, files):
    for rel, data in files.items():
        p = os.path.join(d, *rel.split('/')); os.makedirs(os.path.dirname(p), exist_ok=True); put(p, data)


def gate(files, **kw):
    """The gates' problems for a hand-built site, without the leak scan's (these tests are about the other gates)."""
    with tempfile.TemporaryDirectory() as d:
        write_files(d, dict(files, **{'.nojekyll': ''}))
        return [p for p in B.gates(d, **kw) if not p.startswith('leakscan')]


def one_page(text, name='index.html', extra=None):
    """A site whose index is `text`, or whose index links to page `name` holding it."""
    files = {'index.html': text} if name == 'index.html' else {'index.html': '<a href="%s">x</a>' % name, name: text}
    files.update(extra or {})
    return files


# ------------------------------------------------------------------ review round 1

class PosterRef(unittest.TestCase):
    def test_a_video_poster_is_a_local_reference(self):                       # so the link and orphan gates see it
        self.assertEqual(B.local_refs('<video controls poster="../media/v.png" src="../media/v.mp4"></video>'),
                         ['../media/v.png', '../media/v.mp4'])
        self.assertEqual(B.local_refs('<video poster=p.png></video>'), ['p.png'])
        self.assertEqual(B.local_refs('<video poster="https://cdn.jsdelivr.net/p.png"></video>'), [])      # control: external
        self.assertEqual(B.local_refs('<p>the poster=no.png in prose</p>'), [])                              # control: not a tag


class Orphans(unittest.TestCase):
    SITE = {'index.html': '<a href="a.html">a</a><link rel=stylesheet href="s.css">',
            'a.html': '<title>A</title><img src="img/p.png">',
            's.css': '@import "t.css"; .x{background:url(img/q.png)}', 't.css': 'body{margin:0}',
            'img/p.png': PNG, 'img/q.png': PNG, '.gallery-build': ''}

    def test_a_site_where_everything_is_linked_passes(self):                    # the control
        self.assertEqual(gate(self.SITE), [])

    def test_an_unlinked_file_fails_the_gate(self):
        for extra, data in (('extra.txt', 'hello'), ('deep/er/x.json', '{}'), ('img/r.png', PNG), ('.secret', 'x')):
            with self.subTest(extra=extra):
                probs = gate(dict(self.SITE, **{extra: data}))
                self.assertEqual(len(probs), 1, probs); self.assertIn(extra, probs[0])

    def test_a_file_only_an_unlinked_page_uses_is_unreachable_too(self):
        probs = gate(dict(self.SITE, **{'o.html': '<img src="img/r.png">', 'img/r.png': PNG}))
        self.assertEqual(len(probs), 2, probs)
        self.assertTrue(any('o.html' in p for p in probs) and any('img/r.png' in p for p in probs))
        linked = dict(self.SITE, **{'o.html': '<img src="img/r.png">', 'img/r.png': PNG})        # control: link the page and both are reachable
        linked['index.html'] += '<a href="o.html">o</a>'
        self.assertEqual(gate(linked), [])

    def test_the_two_marker_files_are_not_orphans(self):
        self.assertIn('.gallery-build', self.SITE)
        self.assertEqual(gate({k: v for k, v in self.SITE.items() if k != '.gallery-build'}), [])

    def test_a_dir_page_with_an_unlinked_sibling_fails_the_build(self):         # the head-fit bug: 13 files nothing links to
        d, m = tiny_repo(); os.makedirs(os.path.join(d, 'w'))
        put(os.path.join(d, 'w', 'v.html'), '<title>V</title><script src="data.js"></script>')
        put(os.path.join(d, 'w', 'data.js'), 'var x=1;'); put(os.path.join(d, 'w', 'handover.html'), '<title>H</title>')
        add_item(d, m, id='v', src='w/v.html', dir=True)
        probs = B.build(m, d, os.path.join(d, 'site'))['problems']
        self.assertTrue(any('handover.html' in p for p in probs), probs); self.assertFalse(any('data.js' in p for p in probs))
        os.remove(os.path.join(d, 'w', 'handover.html'))                         # control: without it the build is clean
        self.assertEqual(B.build(m, d, os.path.join(d, 'site'))['problems'], [])

    def test_the_manifest_has_no_dir_item_for_head_fit(self):
        with open(B.MANIFEST, encoding='utf-8') as fh:
            items = {i['id']: i for s in json.load(fh)['sections'] for i in s['items']}
        self.assertNotIn('dir', items['head-fit'])


class Hold(unittest.TestCase):
    def setUp(self):
        self.d, self.m = tiny_repo(); self.out = os.path.join(self.d, 'site')
        put(os.path.join(self.d, 'a', 'out', 'h.html'), '<title>H</title><p>held</p>')
        add_item(self.d, self.m, id='h', title='Held title', src='a/out/h.html', hold='why not yet', caption='held caption')

    def unhold(self):
        for it in self.m['sections'][0]['items']:
            it.pop('hold', None)

    def test_a_held_item_is_not_built_and_is_reported(self):
        r = B.build(self.m, self.d, self.out)
        self.assertEqual(r['held'], [('h', 'why not yet')]); self.assertEqual(r['items'], 2)
        self.assertEqual(r['problems'], []); self.assertEqual(r['missing'], [])
        self.assertFalse(os.path.exists(os.path.join(self.out, 'pages', 'h.html')))
        idx = read(self.out, 'index.html'); self.assertNotIn('Held title', idx); self.assertNotIn('held caption', idx)

    def test_without_hold_the_same_item_is_built(self):                          # the control
        self.unhold(); r = B.build(self.m, self.d, self.out)
        self.assertEqual(r['held'], []); self.assertEqual(r['items'], 3)
        self.assertTrue(os.path.exists(os.path.join(self.out, 'pages', 'h.html'))); self.assertIn('Held title', read(self.out, 'index.html'))

    def test_a_held_item_whose_source_is_gone_is_held_not_missing(self):
        os.remove(os.path.join(self.d, 'a', 'out', 'h.html'))
        r = B.build(self.m, self.d, self.out)
        self.assertEqual(r['missing'], []); self.assertEqual(r['held'], [('h', 'why not yet')])
        self.unhold()                                                              # control: not held, so missing
        self.assertEqual(B.build(self.m, self.d, self.out, allow_missing=True)['missing'], [('h', 'z')])

    def test_held_items_come_in_manifest_order_and_any_kind_can_be_held(self):
        add_item(self.d, self.m, id='g', kind='figure', src='a/f.png', hold='second')
        self.m['sections'].append({'name': 'S2', 'items': [dict(id='k', kind='figure', title='k', src='a/f.png', make='z', caption='c', hold='third')]})
        r = B.build(self.m, self.d, self.out)
        self.assertEqual(r['held'], [('h', 'why not yet'), ('g', 'second'), ('k', 'third')])
        self.assertFalse(os.path.exists(os.path.join(self.out, 'media', 'g.png')))

    def test_a_link_to_a_held_page_is_null(self):
        put(os.path.join(self.d, 'a', 'out', 'l.html'),
            '<title>L</title><script>const D={"designs":[{"link":{"url":"https://claude.ai/artifact/%s","title":"Scorpion Hull Redesign"}}]};</script>' % ID)
        add_item(self.d, self.m, id='lineup', src='a/out/l.html'); self.m['link_pages'] = {'Scorpion Hull Redesign': 'h'}
        B.build(self.m, self.d, self.out)
        page = read(self.out, 'pages', 'lineup.html'); self.assertNotIn('h.html', page); self.assertIn('"link":null', page)
        self.unhold()                                                              # control: built, the link points at it
        B.build(self.m, self.d, self.out); self.assertIn('"url":"h.html"', read(self.out, 'pages', 'lineup.html'))

    def test_every_held_item_has_a_reason(self):
        with open(B.MANIFEST, encoding='utf-8') as fh:
            items = [i for s in json.load(fh)['sections'] for i in s['items']]
        for it in items:
            if 'hold' in it:
                self.assertTrue(it['hold'].strip(), it['id'])

class ThirdPartyScope(unittest.TestCase):
    def test_a_figure_or_video_is_not_scanned_as_a_page(self):
        d, m = tiny_repo(); put(os.path.join(d, 'a', 'v.mp4'), MP4); add_item(d, m, id='v', kind='video', src='a/v.mp4', caption='MG90S bench')
        self.assertEqual(B.build(m, d, os.path.join(d, 'site'))['problems'], [])

    def test_words_in_a_plain_page_are_not_parts(self):                           # the gate reads meshes, not prose
        d, m = tiny_repo(); put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><p>MG90S, PCA9685, a sprocket and the Raspberry Pi 5</p>')
        self.assertEqual(B.build(m, d, os.path.join(d, 'site'))['problems'], [])

HOSTS = ['cdnjs.cloudflare.com', 'cdn.jsdelivr.net', 'unpkg.com', 'fonts.googleapis.com', 'fonts.gstatic.com']
LOADS = [                                                  # every way an HTML, CSS or JS file loads a resource; {u} is the URL
    '<script src="{u}"></script>', "<img src='{u}'>", '<img src={u}>', '<iframe src="{u}"></iframe>',
    '<img srcset="https://cdn.jsdelivr.net/a.png 1x, {u} 2x">', '<img srcset="{u}">',
    '<link rel="stylesheet" href="{u}">', '<link rel=preload as=script href="{u}">', '<link href="{u}" rel="modulepreload">',
    '<link rel="preload stylesheet" href="{u}">', '<LINK REL="Stylesheet" HREF="{u}">',
    '<style>@import url({u});</style>', '<style>@import url("{u}");</style>', '<style>@import "{u}";</style>', "<style>@import '{u}';</style>",
    '<style>.a{{background:url({u})}}</style>', '<style>.a{{background:url("{u}")}}</style>', '<div style="background:url({u})">x</div>',
    '<script>import * as T from "{u}";</script>', "<script>import T from '{u}'</script>", '<script>import {{A,B}} from "{u}";</script>',
    '<script>import"{u}";</script>', '<script>import{{A}}from"{u}";</script>', '<script>export * from "{u}";</script>',
    '<script>import("{u}").then(f);</script>', "<script>fetch('{u}').then(f);</script>", '<script>fetch(`{u}`);</script>',
    '<script>new Worker("{u}");</script>', '<script>loader.load("{u}", f);</script>', '<script>s.src = "{u}";</script>',
    '<script>importScripts("{u}");</script>', '<script>fetch("{u}" + name);</script>',
]


class ExternalHosts(unittest.TestCase):
    def test_every_allowed_host_loads_in_every_way(self):                        # the controls
        for h in HOSTS:
            for t in LOADS:
                with self.subTest(host=h, t=t):
                    self.assertEqual(gate(one_page(t.format(u='https://%s/x/y.js' % h))), [])

    def test_the_allowed_list_is_the_cdn_constant(self):
        self.assertEqual(sorted(B.ALLOWED_HOSTS), sorted(HOSTS))
        self.assertEqual(sorted(urllib.parse.urlsplit(u).hostname for u in B.CDN), sorted(HOSTS))

    def test_any_other_host_fails_in_every_way(self):
        for t in LOADS:
            for u in ('https://evil.example/x.js', 'http://evil.example/x.js', '//evil.example/x.js', 'HTTPS://EVIL.EXAMPLE/x.js',
                      'https://cdn.jsdelivr.net@evil.example/x.js', 'https://cdn.jsdelivr.net.evil.example/x.js',
                      'https://notcdnjs.cloudflare.com/x.js', 'https://sub.unpkg.com/x.js', 'https://evil.example:8443/x.js'):
                with self.subTest(t=t, u=u):
                    probs = gate(one_page(t.format(u=u)))
                    self.assertTrue(any(x in p.lower() for p in probs for x in ('evil.example', 'notcdnjs', 'sub.unpkg')), probs)

    def test_css_and_js_files_are_checked_too(self):
        for name, text in (('s.css', '@import url(https://evil.example/a.css); .a{background:url(https://evil.example/b.png)}'),
                           ('s.css', '@import "https://evil.example/a.css";'), ('app.js', 'fetch("https://evil.example/d.json")'),
                           ('app.js', 'import x from "https://evil.example/m.js"'), ('app.js', 'new Worker("https://evil.example/w.js")')):
            with self.subTest(name=name, text=text):
                probs = gate(one_page('<script src="app.js"></script><link rel=stylesheet href="s.css">', extra={'app.js': 'x', 's.css': 'a{}', name: text}))
                self.assertTrue(any('evil.example' in p and name in p for p in probs), probs)

    def test_links_to_other_sites_load_nothing_and_pass(self):
        for t in ('<a href="https://other.example/page">x</a>', '<a href="//other.example/">x</a>', '<a href=http://other.example>x</a>',
                  '<link rel="canonical" href="https://other.example/">', '<p>see https://evil.example/x.js for details</p>',
                  '<img src="data:image/png;base64,AAAA">', '<script>var u = "https://evil.example/x.js";</script>',
                  '<a href="mailto:a@b.example">m</a>', '<script>fetch(url); import(name);</script>'):
            with self.subTest(t=t):
                self.assertEqual(gate(one_page(t)), [])

    def test_the_problem_names_the_file_and_the_url(self):
        probs = gate(one_page('<script src="https://evil.example/x.js"></script>', 'pages/a.html'))
        self.assertTrue(any('pages/a.html' in p and 'https://evil.example/x.js' in p for p in probs), probs)


class JsLoads(unittest.TestCase):
    SINKS = ['fetch("{p}")', "fetch('{p}')", 'loader.load("{p}", onLoad)', 'import("{p}")', 'new Worker("{p}")', 'new Worker( "{p}" , {{type:"module"}})',
             'import x from "{p}"', 'fetch(`{p}`)']
    EXTS = ['json', 'obj', 'stl', 'glb', 'gltf', 'bin', 'png', 'jpg', 'jpeg', 'webp', 'mp4', 'css', 'js']

    def test_a_load_of_a_file_that_is_not_in_the_site_fails(self):
        for sink in self.SINKS:
            for ext in self.EXTS:
                p = 'data/m.%s' % ext
                with self.subTest(sink=sink, ext=ext):
                    probs = gate(one_page('<script>%s;</script>' % sink.format(p=p)))
                    self.assertTrue(any(p in x and 'not in the site' in x for x in probs), probs)

    def test_the_same_load_passes_when_the_file_is_there_and_counts_as_linked(self):          # the controls
        for sink in self.SINKS:
            for ext in self.EXTS:
                p = 'data/m.%s' % ext
                with self.subTest(sink=sink, ext=ext):
                    self.assertEqual(gate(one_page('<script>%s;</script>' % sink.format(p=p), extra={p: 'x'})), [])

    def test_in_a_js_file_relative_to_the_file_and_in_a_page_relative_to_the_page(self):
        site = one_page('<script src="js/app.js"></script>', extra={'js/app.js': 'fetch("m.json")'})
        self.assertTrue(any('js/app.js' in p and 'm.json' in p and 'not in the site' in p for p in gate(site)))
        self.assertEqual(gate(dict(site, **{'js/m.json': '{}'})), [])
        site = one_page('<script>fetch("../data/m.json")</script>', 'pages/a.html')
        self.assertTrue(any('data/m.json' in p for p in gate(site)))
        self.assertEqual(gate(dict(site, **{'data/m.json': '{}'})), [])

    def test_loads_that_are_not_asset_files_or_not_literals_are_left_alone(self):
        for t in ('fetch("api/items")', 'fetch("notes.txt")', 'fetch(url)', 'fetch("data:application/json,{}")', 'fetch("m.json" + id)',
                  'x.load(name + ".png")', 'fetch("#frag")', 'fetch("https://cdn.jsdelivr.net/npm/m.json")', 'foo("m.json")', 'x.fetch2("m.png")',
                  'var s = "m.json";'):
            with self.subTest(t=t):
                self.assertEqual(gate(one_page('<script>%s;</script>' % t)), [])

    def test_query_and_fragment_do_not_hide_a_missing_file_and_case_of_the_extension_does_not_either(self):
        self.assertTrue(any('data/m.json' in p for p in gate(one_page('<script>fetch("data/m.json?v=2#x")</script>'))))
        self.assertEqual(gate(one_page('<script>fetch("data/m.json?v=2#x")</script>', extra={'data/m.json': '{}'})), [])
        self.assertTrue(any('data/M.JSON' in p for p in gate(one_page('<script>fetch("data/M.JSON")</script>'))))


class CaseExact(unittest.TestCase):                  # GitHub Pages is case-sensitive; Windows and macOS are not
    def test_a_ref_in_the_wrong_case_fails(self):
        for t, extra, bad in (('<link rel=stylesheet href="S.CSS">', {'s.css': 'a{}'}, 'S.CSS'),
                              ('<a href="Pages/a.html">a</a>', {'pages/a.html': '<title>A</title>'}, 'Pages/a.html'),
                              ('<a href="pages/A.html">a</a>', {'pages/a.html': '<title>A</title>'}, 'pages/A.html'),
                              ('<script>fetch("Data/M.json")</script>', {'data/M.json': '{}'}, 'Data/M.json'),
                              ('<img src="img/P.PNG">', {'img/p.png': PNG}, 'img/P.PNG'),
                              ('<style>.a{background:url(IMG/p.png)}</style>', {'img/p.png': PNG}, 'IMG/p.png')):
            with self.subTest(t=t):
                probs = gate(one_page(t, extra=extra))
                self.assertTrue(any(bad in p and 'not in the site' in p for p in probs), probs)

    def test_the_same_refs_in_the_right_case_pass(self):                          # the controls
        for t, extra in (('<link rel=stylesheet href="s.css">', {'s.css': 'a{}'}), ('<a href="pages/a.html">a</a>', {'pages/a.html': '<title>A</title>'}),
                         ('<script>fetch("data/M.json")</script>', {'data/M.json': '{}'}), ('<img src="img/p.png">', {'img/p.png': PNG}),
                         ('<style>.a{background:url(img/p.png)}</style>', {'img/p.png': PNG}),
                         ('<a href="./pages/../pages/a.html">a</a>', {'pages/a.html': '<title>A</title>'})):
            with self.subTest(t=t):
                self.assertEqual(gate(one_page(t, extra=extra)), [])

    def test_a_ref_that_climbs_out_of_the_site_still_fails(self):
        self.assertTrue(any('not in the site' in p for p in gate(one_page('<a href="../x.html">x</a>'))))      # from the top folder
        self.assertTrue(any('not in the site' in p for p in gate(one_page('<a href="../../x.html">x</a>', 'pages/a.html'))))


class Main(unittest.TestCase):
    CLEAN = dict(items=3, missing=[], held=[], problems=[])

    def run_main(self, result, *argv):
        with tempfile.TemporaryDirectory() as d:
            mf = os.path.join(d, 'manifest.json'); put(mf, json.dumps({'title': 'T', 'intro': 'I', 'sections': []}))
            buf = io.StringIO()
            with mock.patch.object(B, 'MANIFEST', mf), mock.patch.object(B, 'build', return_value=result), contextlib.redirect_stdout(buf):
                code = B.main(list(argv))
        return code, buf.getvalue()

    def test_exit_codes(self):
        miss = dict(self.CLEAN, missing=[('a', 'python make_a.py')]); bad = dict(self.CLEAN, problems=['a link is broken'])
        for name, result, argv, want in (('clean', self.CLEAN, (), 0), ('a problem', bad, (), 1), ('a problem, allow-missing', bad, ('--allow-missing',), 1),
                                         ('missing', miss, (), 1), ('missing, allowed', miss, ('--allow-missing',), 0),
                                         ('both', dict(miss, problems=['x']), ('--allow-missing',), 1)):
            with self.subTest(name):
                self.assertEqual(self.run_main(result, *argv)[0], want)

    def test_output_lines(self):
        code, out = self.run_main(dict(items=3, missing=[('a', 'python make_a.py')], held=[('h', 'a reason'), ('g', 'another')], problems=['p1']))
        self.assertIn('missing a: rebuild with  python make_a.py', out); self.assertIn('PROBLEM p1', out)
        self.assertIn('held h: a reason', out); self.assertIn('held g: another', out)
        self.assertIn('3 items', out); self.assertIn('1 missing', out); self.assertIn('2 held', out); self.assertIn('1 problems', out)

    def test_held_items_alone_are_not_a_failure(self):
        code, out = self.run_main(dict(self.CLEAN, held=[('h', 'r')]))
        self.assertEqual(code, 0); self.assertIn('0 problems', out); self.assertIn('1 held', out)

    def test_on_a_real_tiny_repo(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site'); mf = os.path.join(d, 'manifest.json')
        put(os.path.join(d, 'a', 'out', 'h.html'), '<title>H</title>'); add_item(d, m, id='h', src='a/out/h.html', hold='later')

        def go(*argv):
            put(mf, json.dumps(m)); buf = io.StringIO()
            with mock.patch.object(B, 'MANIFEST', mf), mock.patch.object(B, 'ROOT', d), mock.patch.object(B, 'OUT', out), contextlib.redirect_stdout(buf):
                return B.main(list(argv)), buf.getvalue()
        code, text = go(); self.assertEqual(code, 0, text); self.assertIn('2 items', text); self.assertIn('held h: later', text)
        put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><img src="nothere.png">')
        code, text = go(); self.assertEqual(code, 1); self.assertIn('nothere.png', text)
        put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title>'); add_item(d, m, id='m', src='a/out/m.html')      # its source is not on disk
        code, text = go(); self.assertEqual(code, 1); self.assertIn('missing m: rebuild with  z', text)
        self.assertEqual(go('--allow-missing')[0], 0)

    def test_a_refused_out_folder_exits_1_and_keeps_its_files(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site'); os.makedirs(out); put(os.path.join(out, 'mine.txt'), 'keep'); mf = os.path.join(d, 'manifest.json')
        put(mf, json.dumps(m)); buf = io.StringIO()
        with mock.patch.object(B, 'MANIFEST', mf), mock.patch.object(B, 'ROOT', d), mock.patch.object(B, 'OUT', out), contextlib.redirect_stdout(buf):
            code = B.main([])
        self.assertEqual(code, 1); self.assertTrue(os.path.exists(os.path.join(out, 'mine.txt'))); self.assertIn('refusing', buf.getvalue())


EVIL = '<script>alert(1)</script>'


class Escaping(unittest.TestCase):
    def test_card_escapes_title_caption_and_href(self):
        c = B.card(dict(kind='page', title=EVIL, caption=EVIL + ' "q"'), 'pages/x".html', None)
        self.assertNotIn('<script', c.lower()); self.assertIn('&lt;script&gt;', c); self.assertNotIn('x".html', c)
        c = B.card(dict(kind='figure', title=EVIL, caption='c'), 'media/x.png', 'thumbs/x.jpg')
        self.assertNotIn('<script', c.lower()); self.assertIn('thumbs/x.jpg', c)
        ok = B.card(dict(kind='page', title='Plain title', caption='plain caption'), 'pages/x.html', None)         # control
        self.assertIn('Plain title', ok); self.assertIn('plain caption', ok)
        self.assertEqual([a['href'] for a in tags(ok, 'a')], ['pages/x.html'])

    def test_index_html_escapes_title_intro_and_section_names(self):
        m = {'title': EVIL, 'intro': EVIL, 'sections': [{'name': EVIL, 'items': [{'id': 'p'}]}]}
        out = B.index_html(m, {'p': B.card(dict(kind='page', title=EVIL, caption=EVIL), 'pages/p.html', None)})
        self.assertNotIn('<script', out.lower()); self.assertIn('&lt;script&gt;', out)
        ok = B.index_html(dict(m, title='Plain', intro='Intro text', sections=[{'name': 'Sect', 'items': [{'id': 'p'}]}]), {'p': 'CARD'})
        for s in ('Plain', 'Intro text', 'Sect', 'CARD'):
            self.assertIn(s, ok)

    def test_the_video_page_escapes_title_caption_and_urls(self):
        p = B.video_page(dict(title=EVIL, caption=EVIL), '../media/v".mp4', '../media/v".png')
        self.assertNotIn('<script', p.lower()); self.assertIn('&lt;script&gt;', p); self.assertEqual(len(tags(p, 'video')), 1)
        self.assertEqual(tags(p, 'video')[0]['src'], '../media/v".mp4')
        ok = B.video_page(dict(title='Plain title', caption='plain caption'), '../media/v.mp4')
        self.assertIn('Plain title', ok); self.assertIn('plain caption', ok)

    def test_a_whole_build_with_hostile_text_has_no_script_from_the_manifest(self):
        d, m = tiny_repo(); put(os.path.join(d, 'a', 'v.mp4'), MP4)
        add_item(d, m, id='v', kind='video', src='a/v.mp4', title=EVIL, caption=EVIL); out = os.path.join(d, 'site')
        for it in m['sections'][0]['items']:
            it['title'] = EVIL; it['caption'] = EVIL
        m['title'] = EVIL; m['intro'] = EVIL; m['sections'][0]['name'] = EVIL
        r = B.build(m, d, out)
        self.assertEqual(r['problems'], [])
        self.assertNotIn('<script', read(out, 'index.html').lower()); self.assertNotIn('<script', read(out, 'pages', 'v.html').lower())


class Placeholder(unittest.TestCase):
    """A card with no picture shows the item's title in the empty picture area; the kind line under it says what the item is, once."""
    @staticmethod
    def thumb_text(card):
        return re.search(r'<div class="thumb"[^>]*>(.*?)</div>', card, re.S).group(1)

    def test_the_empty_picture_shows_the_title_not_the_kind(self):
        for kind in ('page', 'figure', 'video', 'link'):
            with self.subTest(kind):
                c = B.card(dict(kind=kind, title='My <b>title</b> & "more"', caption='cap'), 'x', None)
                self.assertEqual(html.unescape(self.thumb_text(c)), 'My <b>title</b> & "more"')
                self.assertNotIn('<b>title', c)                                              # escaped
                self.assertEqual(c.count(B.KIND[kind]), 1)                                   # the kind line only: not twice

    def test_a_card_with_a_picture_has_an_empty_picture_area(self):                          # the control
        c = B.card(dict(kind='page', title='T1', caption='c'), 'x', 'thumbs/x.jpg')
        self.assertEqual(self.thumb_text(c), ''); self.assertIn('url(thumbs/x.jpg)', c); self.assertEqual(c.count('T1'), 1)

    def test_in_a_whole_build_a_page_card_without_a_thumb_names_itself_once(self):
        d, m = tiny_repo(); del m['sections'][0]['items'][0]['thumb']; m['sections'][0]['items'][0]['title'] = 'Plain page'
        out = os.path.join(d, 'site'); self.assertEqual(B.build(m, d, out)['problems'], [])
        idx = read(out, 'index.html'); self.assertEqual(idx.count('3D, drag to turn'), 1)
        self.assertEqual(re.findall(r'<div class="thumb"[^>]*>(.*?)</div>', idx), ['Plain page', ''])     # the figure has its picture


class TotalSize(unittest.TestCase):
    def test_the_whole_site_over_its_limit_fails(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site')
        with mock.patch.object(B, 'TOTAL_MB', 0.0001):
            self.assertTrue(any('the site is' in p and 'limit' in p for p in B.build(m, d, out)['problems']))
        self.assertFalse(any('the site is' in p for p in B.build(m, d, out)['problems']))          # control: the real limit


class OnePass(unittest.TestCase):
    def test_placeholders_in_the_text_stay_literal(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site')
        m['intro'] = 'intro {{BUILT}}'; m['sections'][0]['name'] = 'sect {{SECTIONS}}'
        m['sections'][0]['items'][0]['caption'] = 'cap {{BUILT}} {{TITLE}} {{INTRO}}'
        B.build(m, d, out); idx = read(out, 'index.html')
        self.assertEqual(idx.count('{{BUILT}}'), 2); self.assertEqual(idx.count('sect {{SECTIONS}}'), 1)
        self.assertIn('cap {{BUILT}} {{TITLE}} {{INTRO}}', idx); self.assertIn('intro {{BUILT}}', idx)

    def test_the_real_placeholders_are_still_filled(self):                       # the control
        d, m = tiny_repo(); out = os.path.join(d, 'site'); B.build(m, d, out); idx = read(out, 'index.html')
        self.assertNotIn('{{', idx); self.assertIn('Built ' + datetime.date.today().isoformat(), idx)
        self.assertEqual(idx.count('<h1>T</h1>'), 1); self.assertIn('<title>T</title>', idx)


class ThumbMissing(unittest.TestCase):
    def test_a_thumb_that_is_not_on_disk_is_a_problem(self):
        d, m = tiny_repo(); m['sections'][0]['items'][0]['thumb'] = 'a/nothere.png'
        probs = B.build(m, d, os.path.join(d, 'site'))['problems']
        self.assertTrue(any('a/nothere.png' in p and "'p'" in p for p in probs), probs)
        d2, m2 = tiny_repo()                                                       # control: it exists
        self.assertEqual(B.build(m2, d2, os.path.join(d2, 'site'))['problems'], [])

    def test_a_video_thumb_that_is_not_on_disk_is_a_problem(self):
        d, m = tiny_repo(); put(os.path.join(d, 'a', 'v.mp4'), MP4); add_item(d, m, id='v', kind='video', src='a/v.mp4', thumb='a/nothere.png')
        self.assertTrue(any('a/nothere.png' in p for p in B.build(m, d, os.path.join(d, 'site'))['problems']))
        m['sections'][0]['items'][-1].pop('thumb')                                # control: no thumb asked for, none missing
        self.assertEqual(B.build(m, d, os.path.join(d, 'site'))['problems'], [])


def focus_ok(css):
    """True when a rule for a focused card draws an outline (not none, not 0)."""
    for sel, body in re.findall(r'([^{}]*:focus-visible[^{}]*)\{([^{}]*)\}', css):
        m = re.search(r'outline\s*:\s*([^;}]*)', body)
        if 'card' in sel and m and not re.match(r'\s*(none|0)\b', m.group(1)):
            return True
    return False


class Focus(unittest.TestCase):
    def test_the_checker_itself(self):                                            # controls on the check
        self.assertFalse(focus_ok('a.card:hover,a.card:focus-visible{border-color:#1;outline:none}'))
        self.assertFalse(focus_ok('a.card:focus-visible{outline:0}')); self.assertFalse(focus_ok('a.card:hover{outline:2px solid red}'))
        self.assertFalse(focus_ok('a.card{outline:none}')); self.assertTrue(focus_ok('a.card:focus-visible{outline:2px solid #000}'))

    def test_cards_show_a_keyboard_focus_outline(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site'); B.build(m, d, out)
        css = re.search(r'<style>(.*?)</style>', read(out, 'index.html'), re.S).group(1)
        self.assertTrue(focus_ok(css), css)


class Remux(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.src = os.path.join(self.d, 's.mp4'); self.dst = os.path.join(self.d, 'o', 'd.mp4')
        os.makedirs(os.path.dirname(self.dst)); put(self.src, MP4)

    def test_it_runs_ffmpeg_with_faststart(self):
        calls = []

        def fake(cmd, *a, **k):
            calls.append(cmd); put(cmd[-1], b'REMUXED'); return types.SimpleNamespace(returncode=0, stderr=b'')
        with mock.patch.object(B.subprocess, 'run', side_effect=fake):
            self.assertTrue(B.copy_video(self.src, self.dst))
        self.assertEqual(calls, [['ffmpeg', '-v', 'error', '-y', '-i', self.src, '-c', 'copy', '-movflags', '+faststart', self.dst]])
        with open(self.dst, 'rb') as fh:
            self.assertEqual(fh.read(), b'REMUXED')

    def test_a_failed_or_missing_ffmpeg_falls_back_to_a_plain_copy(self):          # the controls
        def partial(cmd, *a, **k):
            put(cmd[-1], b'PARTIAL'); return types.SimpleNamespace(returncode=1, stderr=b'boom')
        for name, kw in (('exit 1 after a partial file', dict(side_effect=partial)), ('not installed', dict(side_effect=FileNotFoundError())),
                         ('timeout', dict(side_effect=subprocess.TimeoutExpired('ffmpeg', 1))), ('os error', dict(side_effect=OSError()))):
            with self.subTest(name):
                with mock.patch.object(B.subprocess, 'run', **kw):
                    self.assertFalse(B.copy_video(self.src, self.dst))
                with open(self.dst, 'rb') as fh:
                    self.assertEqual(fh.read(), MP4)
                os.remove(self.dst)

    def test_only_mp4_goes_through_ffmpeg(self):
        webm = os.path.join(self.d, 's.webm'); put(webm, b'W'); dst = os.path.join(self.d, 'o', 'd.webm')
        with mock.patch.object(B.subprocess, 'run', side_effect=AssertionError('ffmpeg must not run')):
            self.assertFalse(B.copy_video(webm, dst))
        with open(dst, 'rb') as fh:
            self.assertEqual(fh.read(), b'W')

    def test_a_video_item_is_remuxed_on_build(self):
        d, m = tiny_repo(); put(os.path.join(d, 'a', 'v.mp4'), MP4); add_item(d, m, id='v', kind='video', src='a/v.mp4')
        with mock.patch.object(B, 'copy_video', wraps=B.copy_video) as cv:
            B.build(m, d, os.path.join(d, 'site'))
        self.assertEqual(cv.call_count, 1); self.assertTrue(cv.call_args[0][0].endswith('v.mp4'))

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg is not installed')
    def test_with_the_real_ffmpeg_the_moov_box_comes_first(self):
        def order(path):
            with open(path, 'rb') as fh:
                data = fh.read()
            i, kinds = 0, []
            while i + 8 <= len(data):
                size = struct.unpack('>I', data[i:i + 4])[0]; kinds.append(data[i + 4:i + 8]); i += size if size >= 8 else len(data)
            return kinds
        src = os.path.join(self.d, 'real.mp4')
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc=duration=0.4:size=64x64:rate=10', '-pix_fmt', 'yuv420p', src],
                           capture_output=True)
        if r.returncode != 0:
            self.skipTest('this ffmpeg cannot make a test clip')
        before = order(src); self.assertLess(before.index(b'mdat'), before.index(b'moov'))      # the control: the source has moov last
        self.assertTrue(B.copy_video(src, self.dst))
        after = order(self.dst); self.assertLess(after.index(b'moov'), after.index(b'mdat'))


class Refuse(unittest.TestCase):
    def test_a_folder_that_is_not_a_gallery_build_is_not_deleted(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site'); os.makedirs(os.path.join(out, 'sub')); put(os.path.join(out, 'sub', 'mine.txt'), 'keep')
        with self.assertRaises(RuntimeError) as cm:
            B.build(m, d, out)
        self.assertEqual(os.listdir(os.path.join(out, 'sub')), ['mine.txt']); self.assertFalse(os.path.exists(os.path.join(out, 'index.html')))
        self.assertIn('.gallery-build', str(cm.exception))

    def test_an_empty_folder_or_a_previous_build_is_replaced(self):                # the controls
        d, m = tiny_repo(); out = os.path.join(d, 'site'); os.makedirs(out)
        B.build(m, d, out); self.assertTrue(os.path.exists(os.path.join(out, '.gallery-build')))
        put(os.path.join(out, 'stale.txt'), 'old'); r = B.build(m, d, out)
        self.assertEqual(r['problems'], []); self.assertFalse(os.path.exists(os.path.join(out, 'stale.txt')))
        self.assertTrue(os.path.exists(os.path.join(out, 'index.html')))

    def test_a_missing_folder_is_created(self):
        d, m = tiny_repo(); out = os.path.join(d, 'new', 'site'); self.assertEqual(B.build(m, d, out)['problems'], [])


class Credits(unittest.TestCase):
    LINE = ('Some renders show parts from FPV-Rover V2.0 by Markus_p (CC BY-NC-SA 4.0), the Luengoa tracks (CC BY-NC) and the '
            'Raspberry Pi 5 model from Printables 727155 (CC0).')

    def test_the_footer(self):
        d, m = tiny_repo(); out = os.path.join(d, 'site'); B.build(m, d, out); idx = read(out, 'index.html')
        foot = re.search(r'<footer>(.*?)</footer>', idx, re.S).group(1)
        self.assertIn(self.LINE, foot); self.assertIn("from the Scorpion project's design repository", foot)
        self.assertIn('three.js and fonts from public CDNs', foot); self.assertNotIn('FPVTank', idx)
        self.assertIn('Built ' + datetime.date.today().isoformat(), foot)


from gallery import publish as Pub


class Publish(unittest.TestCase):
    """publish.main with no network: subprocess.run is faked, the build is faked, site/out is a temp folder."""
    BAD = 'someone@example.org'                                  # a stand-in for the private address

    def setUp(self):
        self.out = tempfile.mkdtemp(); self.calls = []; self.seen = {}; os.makedirs(os.path.join(self.out, 'pages'))
        put(os.path.join(self.out, 'index.html'), '<title>G</title>'); put(os.path.join(self.out, '.nojekyll'), '')
        put(os.path.join(self.out, '.gallery-build'), ''); put(os.path.join(self.out, 'pages', 'a.html'), '<div>a</div>')
        self.exists, self.pages_on, self.changed, self.emails, self.failing = False, False, True, [Pub.EMAIL] * 2, None
        man = os.path.join(tempfile.mkdtemp(), 'manifest.json')
        put(man, json.dumps({'sections': [{'items': [
            {'id': 'ok', 'kind': 'figure'}, {'id': 'h1', 'kind': 'page', 'hold': 'a licensing call'},
            {'id': 'h2', 'kind': 'page', 'hold': 'a licensing call'}, {'id': 'h3', 'kind': 'page', 'hold': 'another reason'}]}]}))
        self.build = mock.Mock(return_value=0)
        for p in (mock.patch.object(Pub.B, 'OUT', self.out), mock.patch.object(Pub.B, 'MANIFEST', man),
                  mock.patch.object(Pub.B, 'main', self.build), mock.patch.object(Pub.subprocess, 'run', side_effect=self.fake_run)):
            p.start(); self.addCleanup(p.stop)

    def fake_run(self, cmd, *a, **k):
        cmd = list(cmd); self.calls.append(cmd); cwd = k.get('cwd')
        ok = lambda out='': types.SimpleNamespace(returncode=0, stdout=out, stderr='')
        if self.failing and cmd[:len(self.failing)] == self.failing:
            raise subprocess.CalledProcessError(2, cmd, output='', stderr='remote: denied to ' + self.BAD + '\ntoken ghp_' + 'A' * 36)
        if cmd[:3] == ['gh', 'repo', 'view']:
            return types.SimpleNamespace(returncode=0 if self.exists else 1, stdout='', stderr='')
        if cmd[:3] == ['gh', 'repo', 'clone']:
            os.makedirs(os.path.join(cmd[4], '.git')); put(os.path.join(cmd[4], 'stale.html'), 'old'); return ok()
        if cmd[:2] == ['gh', 'api'] and '-X' not in cmd:
            return types.SimpleNamespace(returncode=0 if self.pages_on else 1, stdout='', stderr='')
        if 'rev-parse' in cmd:
            return ok('abc1234')
        if cmd[-2:] == ['status', '--porcelain']:
            self.seen['tree'] = sorted(os.path.relpath(os.path.join(b, f), cwd).replace(os.sep, '/')
                                       for b, ds, fs in os.walk(cwd) if '.git' not in b.split(os.sep) for f in fs)
            return ok('A  index.html' if self.changed else '')
        if cmd[:2] == ['git', 'log']:
            return ok('\n'.join(self.emails))
        return ok()

    def go(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = Pub.main(['--repo', 'nobody/none', *argv])
        return rc, buf.getvalue()

    def called(self, word):
        return [c for c in self.calls if word in c]

    def test_refuses_without_yes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(Pub.main(['--repo', 'nobody/none', '--dry-run-dir', tempfile.mkdtemp()]), 2)
        self.assertEqual(self.calls, [])

    def test_without_yes_it_rebuilds_says_where_and_runs_no_command(self):
        rc, said = self.go()
        self.assertEqual(rc, 2); self.build.assert_called_once_with([])
        self.assertIn('would push 3 files', said)                                  # index.html, pages/a.html, .nojekyll; not the marker
        self.assertIn('https://github.com/nobody/none', said); self.assertIn('https://nobody.github.io/none/', said)
        self.assertIn('not published', said); self.assertEqual(self.calls, [])

    def test_with_yes_the_commands_the_dry_run_lacks_do_run(self):                 # the negative control for the test above
        self.assertEqual(self.go('--yes')[0], 0)
        for word in ('create', 'clone', 'commit', 'push', '-X'):
            self.assertTrue(self.called(word), word)

    def test_the_dry_run_lists_what_is_held_back(self):
        rc, said = self.go()
        self.assertIn('3 held back', said); self.assertIn('h1, h2: a licensing call', said); self.assertIn('h3: another reason', said)
        self.assertNotIn('ok:', said)

    def test_with_nothing_held_the_list_is_not_printed(self):                      # the control
        put(Pub.B.MANIFEST, json.dumps({'sections': [{'items': [{'id': 'ok', 'kind': 'figure'}]}]}))
        self.assertNotIn('held back', self.go()[1])

    def test_yes_creates_clones_commits_pushes_and_turns_pages_on_in_order(self):
        rc, said = self.go('--yes'); self.assertEqual(rc, 0)
        words = ('create', 'clone', 'commit', 'log', 'push', '-X')
        verbs = [next(w for w in words if w in c) for c in self.calls if any(w in c for w in words)]
        self.assertEqual(verbs, ['create', 'clone', 'commit', 'log', 'push', '-X'])
        self.assertIn('--public', self.called('create')[0]); self.assertEqual(self.called('push')[0][-3:], ['push', 'origin', 'HEAD:main'])
        self.assertIn('published: https://nobody.github.io/none/', said)

    def test_the_commit_carries_the_noreply_identity_and_nothing_is_configured(self):
        self.go('--yes'); commit = self.called('commit')[0]
        self.assertEqual(commit[:commit.index('commit')],                         # before the verb, where git reads them
                         ['git', '-c', 'user.name=' + Pub.NAME, '-c', 'user.email=' + Pub.EMAIL])
        self.assertTrue(Pub.EMAIL.endswith('@users.noreply.github.com'))
        self.assertNotIn('FPVTank', ' '.join(commit))                              # the private repo's name stays out of the public log
        self.assertFalse(self.called('config'))                                    # never git config

    def test_the_marker_and_old_files_are_not_pushed(self):
        self.go('--yes')
        self.assertEqual(self.seen['tree'], ['.nojekyll', 'index.html', 'pages/a.html'])      # no .gallery-build, no stale.html

    def test_a_commit_with_another_address_stops_the_push(self):
        self.emails = [Pub.EMAIL, self.BAD]; rc, said = self.go('--yes')
        self.assertEqual(rc, 1); self.assertIn('refusing to push: a commit carries a non-noreply email', said)
        self.assertIn('1 of 2', said); self.assertNotIn(self.BAD, said)             # a count, never the address
        self.assertFalse(self.called('push')); self.assertFalse(self.called('-X'))

    def test_noreply_addresses_in_any_case_pass(self):                             # the control for the test above
        self.emails = [Pub.EMAIL.upper(), '49+x@users.noreply.github.com']
        self.assertEqual(self.go('--yes')[0], 0); self.assertTrue(self.called('push'))

    def test_a_failed_build_returns_1_before_any_command(self):
        self.build.return_value = 1
        for argv in ((), ('--yes',)):
            with self.subTest(argv):
                rc, said = self.go(*argv); self.assertEqual(rc, 1); self.assertIn('nothing published', said)
        self.assertEqual(self.calls, [])

    def test_an_existing_repo_and_pages_are_left_alone(self):
        self.exists = self.pages_on = True; self.assertEqual(self.go('--yes')[0], 0)
        self.assertFalse(self.called('create')); self.assertFalse(self.called('-X')); self.assertTrue(self.called('push'))

    def test_no_change_means_no_commit_and_no_push(self):
        self.changed = False; rc, said = self.go('--yes'); self.assertEqual(rc, 0)
        self.assertFalse(self.called('commit')); self.assertFalse(self.called('push')); self.assertIn('nothing changed', said)

    def test_a_failing_command_ends_cleanly_with_nothing_secret_printed(self):
        for fail, shown in ((['gh', 'repo', 'clone'], 'gh repo'), (['git', '-c'], 'git commit'), (['git', 'push'], 'git push')):
            with self.subTest(shown):
                self.failing, self.calls = fail, []; rc, said = self.go('--yes')
                self.assertEqual(rc, 1); self.assertIn(f'stopped: `{shown}` failed (exit 2)', said)
                for secret in (self.BAD, 'ghp_', 'user.email', Pub.EMAIL):
                    self.assertNotIn(secret, said)

    def test_a_missing_gh_ends_cleanly(self):
        with mock.patch.object(Pub.subprocess, 'run', side_effect=FileNotFoundError()):
            rc, said = self.go('--yes')
        self.assertEqual(rc, 1); self.assertIn('stopped', said)

    def test_a_bad_repo_name_or_a_skipped_build_with_yes_is_refused(self):
        for argv in (['--repo', 'nobody'], ['--repo', 'a/b/c'], ['--repo', 'a b/c'], ['--yes', '--dry-run-dir', self.out]):
            with self.subTest(argv):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(Pub.main(argv), 1)
        self.assertEqual(self.calls, []); self.build.assert_not_called()

class Rotate(unittest.TestCase):
    """A figure with "rotate" is published turned (counter-clockwise, in degrees), thumbnail too; without it, as is."""
    def tall(self, **extra):
        d, m = tiny_repo()
        Image.new('RGB', (300, 900), 'white').save(os.path.join(d, 'a', 'tall.jpg'))
        add_item(d, m, id='t', kind='figure', src='a/tall.jpg', **extra)
        out = os.path.join(d, 'site'); r = B.build(m, d, out)
        self.assertEqual(r['problems'], [])
        return Image.open(os.path.join(out, 'media', 't.jpg')).size, Image.open(os.path.join(out, 'thumbs', 't.jpg')).size

    def test_rotated_figure_and_its_thumb_lie_flat(self):
        (w, h), (tw, th) = self.tall(rotate=90)
        self.assertEqual((w, h), (900, 300)); self.assertGreater(tw, th)

    def test_without_rotate_the_figure_is_untouched(self):                  # the control
        (w, h), (tw, th) = self.tall()
        self.assertEqual((w, h), (300, 900)); self.assertLess(tw, th)

    # Which way it turns: a red 40 x 40 block in the top-left corner of a tall image, then where the block ends up.
    def marked(self, **extra):
        d, m = tiny_repo(); im = Image.new('RGB', (300, 900), 'white'); im.paste((255, 0, 0), (0, 0, 40, 40)); im.save(os.path.join(d, 'a', 'mark.png'))
        add_item(d, m, id='t', kind='figure', src='a/mark.png', **extra)
        out = os.path.join(d, 'site'); self.assertEqual(B.build(m, d, out)['problems'], [])
        return [Image.open(os.path.join(out, sub, name)).convert('RGB') for sub, name in (('media', 't.png'), ('thumbs', 't.jpg'))]

    @staticmethod
    def corner(im):
        """'top-left' ... 'bottom-right': which quarter of the picture holds the red block's centre."""
        a = np.asarray(im).astype(int); red = (a[..., 0] > 180) & (a[..., 1] < 110) & (a[..., 2] < 110)
        ys, xs = np.nonzero(red); assert len(xs) > 20, 'no red block found'
        return ('top' if ys.mean() < im.height / 2 else 'bottom') + '-' + ('left' if xs.mean() < im.width / 2 else 'right')

    def test_rotate_90_turns_it_counter_clockwise(self):
        for im, what in zip(self.marked(rotate=90), ('figure', 'thumbnail')):
            with self.subTest(what):
                self.assertEqual(self.corner(im), 'bottom-left')                # the top-left corner goes down the left side

    def test_the_other_way_and_not_at_all_put_the_block_elsewhere(self):      # the controls: a wrong turn direction would fail the test above
        for extra, want in (({'rotate': -90}, 'top-right'), ({'rotate': 180}, 'bottom-right'), ({}, 'top-left')):
            for im, what in zip(self.marked(**extra), ('figure', 'thumbnail')):
                with self.subTest(extra=extra, what=what):
                    self.assertEqual(self.corner(im), want)


if __name__ == '__main__':
    unittest.main()


# ------------------------------------------------------------------ stand-in boxes, the geometry-aware third-party gate, credits, link cards, section intros

import base64, html
import numpy as np

SERVO = (12.2, 33.0, 32.4)                           # the MG90S model's bounding box as the pages show it (mm)
HORN = (3.7, 6.9, 31.35)                             # the MG90S horn's


def chamfered(lo, hi, a=1.0):
    """A closed prism with chamfered corners filling the box lo..hi: 16 vertices (so not a box) and exact bounds."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    ring = [(x0 + a, y0), (x1 - a, y0), (x1, y0 + a), (x1, y1 - a), (x1 - a, y1), (x0 + a, y1), (x0, y1 - a), (x0, y0 + a)]
    V = [(x, y, z0) for x, y in ring] + [(x, y, z1) for x, y in ring]
    F = []
    for i in range(8):
        j = (i + 1) % 8
        F += [(i, j, 8 + j), (i, 8 + j, 8 + i)]
    for i in range(1, 7):
        F += [(0, i + 1, i), (8, 8 + i, 8 + i + 1)]
    return np.array(V, float), np.array(F)


def cuboid(lo, hi):
    """The 8-vertex, 12-triangle box lo..hi."""
    (x0, y0, z0), (x1, y1, z1) = lo, hi
    V = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    F = [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (3, 7, 6), (3, 6, 2), (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5)]
    return np.array(V, float), np.array(F)


def sized(dims, at=(0, 0, 0), a=2.0):
    return chamfered(at, tuple(at[i] + dims[i] for i in range(3)), a)


def merged(*ms):
    V, F, off = [], [], 0
    for v, f in ms:
        V.append(v); F.append(np.asarray(f) + off); off += len(v)
    return np.vstack(V), np.vstack(F)


SERVO_PROFILE = [(0, 0), (23.18, 0), (23.18, 16.54), (29.56, 16.54), (29.56, 19.38), (23.18, 19.38), (23.18, 20.92), (13.05, 20.92), (13.05, 27.57),
                 (11.6, 27.57), (11.6, 33), (5.15, 33), (5.15, 27.57), (2.72, 27.57), (2.72, 20.92), (0, 20.92), (0, 19.38), (-2.84, 19.38),
                 (-2.84, 16.54), (0, 16.54)]      # an MG90S side view: body, tabs, gear boss, spline. Extruded 12.2 mm: box 36.8 x 33.9 x 12.2 about its principal axes, 7,500 mm3
CROSS_PROFILE = [(15.9, 0), (20.9, 0), (20.9, 14.45), (36.8, 14.45), (36.8, 19.45), (20.9, 19.45), (20.9, 33.9), (15.9, 33.9), (15.9, 19.45),
                 (0, 19.45), (0, 14.45), (15.9, 14.45)]      # a plus sign filling the servo's 36.8 x 33.9 box: the same box, 4,000 mm3


def horn_profile(w=0.57, r=3.45, half=15.675, n=17):
    """The double-arm horn seen from above: a round hub 6.9 wide and two thin arms to 31.35 across. Extruded 3.7 mm: that box, 241 mm3."""
    th = np.linspace(np.arcsin(w / r), np.pi - np.arcsin(w / r), n); top = [(r * np.cos(a), r * np.sin(a)) for a in th]
    return [(half, -w), (half, w)] + top + [(-half, w), (-half, -w)] + [(-x, -y) for x, y in top]


def prism(profile, thickness, at=(0.0, 0.0, 0.0)):
    """A closed solid with outward faces: the simple polygon `profile` (x, y, either winding) extruded `thickness` along z, moved by `at`."""
    P = np.asarray(profile, float); n = len(P)
    if 0.5 * np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]) < 0:
        P = P[::-1]
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    idx, tris = list(range(n)), []
    while len(idx) > 3:                                                                     # ear clipping
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = P[i0], P[i1], P[i2]
            if cross(a, b, c) > 1e-12 and not any(cross(a, b, P[j]) >= 0 and cross(b, c, P[j]) >= 0 and cross(c, a, P[j]) >= 0
                                                  for j in idx if j not in (i0, i1, i2)):
                tris.append((i0, i1, i2)); idx.pop(k); break
        else:
            raise ValueError('the profile is not a simple polygon')
    tris.append(tuple(idx))
    V = np.vstack([np.c_[P, np.zeros(n)], np.c_[P, np.full(n, float(thickness))]]) + np.asarray(at, float)
    F = [(a, c, b) for a, b, c in tris] + [(n + a, n + b, n + c) for a, b, c in tris]
    for i in range(n):
        j = (i + 1) % n; F += [(i, j, n + j), (i, n + j, n + i)]
    return V, np.array(F)


def servo_piece(at=(0, 0, 0)):
    return prism(SERVO_PROFILE, 12.2, at)


def horn_piece(at=(0, 0, 0)):
    return prism(horn_profile(), 3.7, at)


def roller(d, h, at=(0, 0, 0)):
    """A solid wheel of diameter d and width h (a track roller)."""
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    return prism(np.c_[d / 2 * np.cos(a), d / 2 * np.sin(a)], h, at)


def turned(m, *turns):
    """The mesh turned by each (axis 'x', 'y' or 'z', degrees) in turn, about its own centre."""
    V, F = m; c = V.mean(0)
    for ax, deg in turns:
        a = np.radians(deg); s, k = np.sin(a), np.cos(a)
        R = {'x': [[1, 0, 0], [0, k, -s], [0, s, k]], 'y': [[k, 0, s], [0, 1, 0], [-s, 0, k]], 'z': [[k, -s, 0], [s, k, 0], [0, 0, 1]]}[ax]
        V = (V - c) @ np.asarray(R).T + c
    return V, F


def aabb_fused(V, F, tol=0.2):
    """The check this replaced, as it was, kept for comparison: the connected pieces whose axis-aligned box has the sides of a known part
    (12.2 x 32.4 x 33.0 the servo, 3.7 x 6.9 x 31.35 the horn). [(name, mask of its triangles)]"""
    if not F.size or len(V) <= 8:
        return []
    ext = np.sort(np.ptp(V, axis=0))[::-1]
    shapes = [(n, np.sort(np.asarray(s, float))[::-1]) for n, s in (('MG90S servo', (12.2, 32.4, 33.0)), ('MG90S servo horn', (3.7, 6.9, 31.35)))]
    shapes = [(n, s) for n, s in shapes if np.all(ext >= s - tol)]
    if not shapes:
        return []
    if len(V) > 1.5 * len(F):
        V, inv = np.unique(V, axis=0, return_inverse=True); F = inv.reshape(-1)[F]
    lab = B._components(len(V), F)
    order = np.argsort(lab, kind='stable'); sl = lab[order]; first = np.flatnonzero(np.r_[True, sl[1:] != sl[:-1]])
    P = V[order]; size = np.sort(np.maximum.reduceat(P, first) - np.minimum.reduceat(P, first), axis=1)[:, ::-1]
    count = np.diff(np.r_[first, len(sl)]); ids = sl[first]; tri = lab[F[:, 0]]
    return [(name, tri == ids[h]) for name, s in shapes for h in np.flatnonzero(np.all(np.abs(size - s) <= tol, axis=1) & (count > 8))]


def enc16(m):
    """A mesh the way the chassis pages store it: int16 at 0.02 mm, uint16 (or uint32) indices."""
    V, F = m; q = np.rint(np.asarray(V, float) / 0.02).astype('<i2'); i32 = len(V) > 65535
    return {'v': base64.b64encode(q.tobytes()).decode(), 'f': base64.b64encode(np.asarray(F).astype('<u4' if i32 else '<u2').tobytes()).decode(), 'i32': i32}


def enc32(m):
    """A mesh the way the fit view stores it: float32 and uint32 indices."""
    V, F = m
    return {'v': base64.b64encode(np.asarray(V, '<f4').tobytes()).decode(), 'f': base64.b64encode(np.asarray(F, '<u4').tobytes()).decode()}


def dec_node(n):
    """(vertices in mm, triangles) read the way each page's own JavaScript reads them."""
    if 'i32' in n:
        V = np.frombuffer(base64.b64decode(n['v']), '<i2').astype(float).reshape(-1, 3) * 0.02
        F = np.frombuffer(base64.b64decode(n['f']), '<u4' if n['i32'] else '<u2').reshape(-1, 3)
    else:
        V = np.frombuffer(base64.b64decode(n['v']), '<f4').astype(float).reshape(-1, 3); F = np.frombuffer(base64.b64decode(n['f']), '<u4').reshape(-1, 3)
    return V, F.astype(int)


def distinct(n):
    V, F = dec_node(n); return len(np.unique(V[np.unique(F)], axis=0))


def volume(n):
    V, F = dec_node(n); return float(np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() / 6)


def part(m, label, **kw):
    return dict(enc16(m), c=2236962, grp='elec', label=label, note='a note', ex=[0, 0, 0], ghost=False, **kw)


THREE = '<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>'


def data_page(var, data, prose='', code='', sep=None):
    js = json.dumps(data, **({'separators': sep} if sep else {}))
    return '<!doctype html><title>T</title><p>%s</p>%s<script>%s=%s;</script><script>%s</script>' % (prose, THREE, var, js, code)


def chassis(parts, prose='', code='', sep=None, **more):
    return data_page('const D', dict({'m': parts, 'yc': 1.5}, **more), prose, code, sep)


def data_of(page, var='const D'):
    m = re.search(re.escape(var) + r'=(.*?);</script>', page, re.S); return json.loads(m.group(1))


def outside(page, var='const D'):
    return re.sub(re.escape(var) + r'=.*?;</script>', '</script>', page, flags=re.S)


PCA = chamfered((0, 30, 40), (60, 55, 52), 2.0)
TUB = chamfered((100, 0, 0), (140, 20, 10), 2.0)
SUFFIX = ' (stand-in box)'


class StandIn(unittest.TestCase):
    def parts(self):
        return {'pca': part(PCA, 'PCA9685 (Adafruit model)'), 'tub': part(TUB, 'Tub (new)')}

    def test_a_matching_part_becomes_a_closed_box_of_the_same_bounds(self):
        page = chassis(self.parts()); out = B.standin_page(page, ['PCA9685']); a, b = data_of(page)['m'], data_of(out)['m']
        self.assertEqual(distinct(a['pca']), 16)                                       # control: it was no box
        V0, _ = dec_node(a['pca']); V1, F1 = dec_node(b['pca'])
        self.assertEqual(distinct(b['pca']), 8); self.assertEqual(len(F1), 12)
        np.testing.assert_allclose(V1.min(0), V0.min(0), atol=1e-9); np.testing.assert_allclose(V1.max(0), V0.max(0), atol=1e-9)
        self.assertAlmostEqual(volume(b['pca']), 60 * 25 * 12, places=4)               # watertight, faces outward: the volume is the box's
        self.assertEqual(b['pca']['label'], 'PCA9685 (Adafruit model)' + SUFFIX)
        for k in ('c', 'grp', 'note', 'ex', 'ghost'):
            self.assertEqual(b['pca'][k], a['pca'][k])
        self.assertEqual(list(b['pca']), list(a['pca']))                                 # same keys, same order
        self.assertEqual(b['tub'], a['tub'])                                             # the neighbour is untouched

    def test_nothing_else_in_the_page_changes(self):
        page = chassis(self.parts(), prose='MG90S is prose', code='var x = "PCA9685";'); out = B.standin_page(page, ['PCA9685'])
        self.assertEqual(outside(out), outside(page)); self.assertNotEqual(out, page)
        self.assertEqual(B.standin_page(page, ['nothing matches this']), page)          # control: no match, same bytes
        self.assertEqual(B.standin_page('<p>MG90S</p>', ['MG90']), '<p>MG90S</p>')       # no data, no change
        self.assertEqual(data_of(out)['yc'], 1.5)

    def test_a_box_is_left_alone_and_standing_in_twice_is_the_same_as_once(self):
        once = B.standin_page(chassis(self.parts()), ['PCA9685']); self.assertEqual(B.standin_page(once, ['PCA9685']), once)
        box = {'pca': part(cuboid((0, 0, 0), (60, 25, 12)), 'PCA9685 (Adafruit model)')}                 # already a box: no new label, no change
        page = chassis(box); self.assertEqual(B.standin_page(page, ['PCA9685']), page)
        merged_page = chassis({'base': part(merged(chamfered((0, 0, 0), (80, 60, 40), 3), servo_piece((200, 0, 0))), 'Pan coil base')})
        once = B.standin_page(merged_page, []); self.assertNotEqual(once, merged_page); self.assertEqual(B.standin_page(once, []), once)

    def test_separators_survive(self):
        for sep, head in ((None, 'const D={"m": {"pca": {"v": '), ((',', ':'), 'const D={"m":{"pca":{"v":')):
            with self.subTest(sep=sep):
                out = B.standin_page(chassis(self.parts(), sep=sep), ['PCA9685'])
                self.assertIn(head, out)

    def test_patterns_are_regexes_matched_anywhere_in_any_case(self):
        out = data_of(B.standin_page(chassis(self.parts()), ['pca9685', r'^tub\b']))['m']
        self.assertEqual((distinct(out['pca']), distinct(out['tub'])), (8, 8))
        out = data_of(B.standin_page(chassis(self.parts()), []))['m']                   # control: no pattern, no stand-in
        self.assertEqual((distinct(out['pca']), distinct(out['tub'])), (16, 16))

    def test_a_part_of_more_than_65535_vertices_is_replaced_by_a_small_box(self):
        rng = np.random.default_rng(1); big = (rng.uniform(0, 100, (70000, 3)), rng.integers(0, 70000, (30000, 3)))
        page = chassis({'pca': part(big, 'PCA9685')}); self.assertTrue(data_of(page)['m']['pca']['i32'])
        n = data_of(B.standin_page(page, ['PCA9685']))['m']['pca']
        self.assertEqual((distinct(n), len(dec_node(n)[1])), (8, 12)); self.assertFalse(n['i32'])
        V0, F0 = dec_node(data_of(page)['m']['pca']); used = V0[np.unique(F0)]
        self.assertAlmostEqual(volume(n), float(np.prod(used.max(0) - used.min(0))), delta=1e-6 * 100 ** 3)

    # a lineup page stores each shape once in D.geo; the labels live in D.txt and are used by the designs' parts
    def lineup(self, extra_parts=()):
        geo = [enc16(PCA), enc16(TUB)]; txt = ['PCA9685 (Adafruit model)', 'a note', 'Tub (new)']
        pt = lambda g, l, o=(0, 0, 0): {'g': g, 'o': list(o), 'c': 1, 'grp': 'elec', 'l': l, 'n': 1}
        d = [{'id': 'a', 'parts': [pt(0, 0), pt(1, 2)]}, {'id': 'b', 'parts': [pt(0, 0, (5, 0, 0))] + list(extra_parts)}]
        return data_page('const D', {'geo': geo, 'txt': txt, 'designs': d, 'yc': 0}, sep=(',', ':'))

    def test_lineup_geometry_shared_only_by_matching_parts_is_replaced_in_place(self):
        page = self.lineup(); D0 = data_of(page); D = data_of(B.standin_page(page, ['PCA9685']))
        self.assertEqual(len(D['geo']), 2); self.assertEqual(distinct(D['geo'][0]), 8); self.assertEqual(D['geo'][1], D0['geo'][1])
        names = [D['txt'][p['l']] for d in D['designs'] for p in d['parts']]
        self.assertEqual(names, ['PCA9685 (Adafruit model)' + SUFFIX, 'Tub (new)', 'PCA9685 (Adafruit model)' + SUFFIX])
        self.assertEqual([p['g'] for d in D['designs'] for p in d['parts']], [0, 1, 0]); self.assertEqual(D['designs'][1]['parts'][0]['o'], [5, 0, 0])
        self.assertEqual(D['txt'][:3], D0['txt'][:3])                                    # the old strings stay where they were

    def test_lineup_geometry_shared_with_a_part_that_does_not_match_is_copied_not_changed(self):
        page = self.lineup([{'g': 0, 'o': [9, 0, 0], 'c': 1, 'grp': 'hull', 'l': 2, 'n': 1}]); D0 = data_of(page)
        D = data_of(B.standin_page(page, ['PCA9685']))
        self.assertEqual(len(D['geo']), 3); self.assertEqual(D['geo'][0], D0['geo'][0])   # the shape the other part uses is intact
        self.assertEqual(distinct(D['geo'][2]), 8)
        self.assertEqual([p['g'] for p in D['designs'][1]['parts']], [2, 0])
        self.assertEqual([D['txt'][p['l']] for p in D['designs'][1]['parts']], ['PCA9685 (Adafruit model)' + SUFFIX, 'Tub (new)'])

    # nose.html stores meshes by key only; the page has no labels, so a key is named as nose.py names it
    def nose(self):
        m = {'pca': dict(enc16(PCA), c=1, grp='elec', body=False), 'pi': dict(enc16(TUB), c=1, grp='elec', body=False), 'tub': dict(enc16(TUB), c=1, grp='hull', body=True)}
        v = {s: {k: dict(enc16(PCA), c=1, grp='head', body=False) for k in ('servo', 'tilt_servo', 'horn', 'well')} for s in 'AB'}
        return data_page('const D', {'m': m, 'v': v, 'yc': 0})

    def test_keys_without_labels_are_named_for_matching(self):
        D = data_of(B.standin_page(self.nose(), ['PCA9685', 'MG90', 'servo horn']))
        self.assertEqual(distinct(D['m']['pca']), 8)
        for s in 'AB':
            self.assertEqual([distinct(D['v'][s][k]) for k in ('servo', 'tilt_servo', 'horn', 'well')], [8, 8, 8, 16])
        self.assertEqual((distinct(D['m']['pi']), distinct(D['m']['tub'])), (16, 16))     # control: not named by the patterns
        self.assertNotIn('label', D['m']['pca'])                                          # there is no label to add the suffix to
        D = data_of(B.standin_page(self.nose(), ['Raspberry']))
        self.assertEqual((distinct(D['m']['pi']), distinct(D['m']['pca'])), (8, 16))

    def test_the_fit_view_format_float32_and_uint32(self):
        fit = {'servo': dict(enc32(chamfered((0, 0, 0), SERVO, 2)), label='Pan servo (your MG90S model)', group='coil', bb=[[0, 0, 0], list(SERVO)]),
               'horn': dict(enc32(chamfered((0, 0, 0), HORN, 0.5)), label='Servo horn, double arm (set 9; carries the torque)', group='coil'),
               'post': dict(enc32(TUB), label='Servo post v3', group='head')}
        page = data_page('window.FIT', fit); D = data_of(B.standin_page(page, ['MG90', 'servo horn']), 'window.FIT')
        for k, size in (('servo', SERVO), ('horn', HORN)):
            V, F = dec_node(D[k]); self.assertEqual((distinct(D[k]), len(F)), (8, 12)); self.assertNotIn('i32', D[k])
            np.testing.assert_allclose(V.max(0) - V.min(0), size, atol=1e-5)
            self.assertTrue(D[k]['label'].endswith(SUFFIX))
        self.assertEqual(D['servo']['bb'], [[0, 0, 0], list(SERVO)]); self.assertEqual(D['post'], fit['post'])         # 'Servo post v3' is no horn

    def test_labels_kept_in_the_pages_javascript(self):                           # plus-sleeve/view.html: window.PARTS plus a LOOK table
        parts = {'servo': enc32(chamfered((0, 0, 0), SERVO, 2)), 'post': enc32(TUB)}
        code = "const LOOK = {servo: ['Tilt servo (your MG90S)', '#3B4046'], post: ['Post v3', '#D9622B']};"
        out = B.standin_page(data_page('window.PARTS', parts, code=code), ['MG90']); D = data_of(out, 'window.PARTS')
        self.assertEqual((distinct(D['servo']), distinct(D['post'])), (8, 16))
        self.assertIn("servo: ['Tilt servo (your MG90S)" + SUFFIX + "', '#3B4046']", out); self.assertIn("post: ['Post v3', '#D9622B']", out)

    def test_a_servo_fused_into_a_bigger_mesh_is_boxed_alone(self):
        wall = chamfered((0, 0, 0), (80, 60, 40), 3); gear = chamfered((0, 0, 100), (43, 43, 106), 3)
        servo = servo_piece((200, 0, 0)); odd = sized((36.8, 33.9, 12.2), (300, 0, 0))                    # control: the servo's box as a solid block, twice the volume
        base = merged(wall, gear, servo, odd)
        page = chassis({'base': part(base, 'Pan coil base (turned 180)')}); D0 = data_of(page)['m']['base']
        D = data_of(B.standin_page(page, ['PCA9685']))['m']['base']                                      # the label matches no pattern
        V0, F0 = dec_node(D0); V, F = dec_node(D)
        rows = lambda V, lo, hi: {tuple(r) for r in V if lo <= r[0] <= hi}
        self.assertEqual(len(rows(V, 190, 235)), 8); self.assertEqual(len(rows(V0, 190, 235)), 40)         # the servo's vertices: 40 become the box's 8
        for lo, hi in ((0, 80), (299, 340)):                                                               # the other parts keep every vertex
            self.assertEqual(rows(V, lo, hi), rows(V0, lo, hi))
        self.assertEqual(len(F), len(F0) - len(servo_piece()[1]) + 12)
        self.assertEqual(D['label'], 'Pan coil base (turned 180) (servo shown as a stand-in box)')
        np.testing.assert_allclose(V.max(0), V0.max(0), atol=1e-9)

    def test_a_fused_servo_horn_is_boxed_too(self):
        page = chassis({'gear': part(merged(chamfered((0, 0, 0), (43, 43, 6), 3), horn_piece((100, 0, 0))), 'Input gear')})
        D = data_of(B.standin_page(page, ['PCA9685']))['m']['gear']; V, F = dec_node(D)
        self.assertEqual(len({tuple(r) for r in V if r[0] > 60}), 8)

    def test_a_mesh_that_is_only_the_servos_shape_is_boxed_whatever_it_is_called(self):
        page = chassis({'x': part(servo_piece(), 'Something else')}); D = data_of(B.standin_page(page, ['nothing']))['m']['x']
        self.assertEqual(distinct(D), 8)


TURNS = [(('x', 10), ('z', 37)), (('y', 37), ('x', 10)), (('z', 10), ('y', 37)), (('x', 37), ('z', 10)), (('y', 10), ('z', 37)), (('z', 45),)]
FUSED = [('MG90S servo', servo_piece), ('MG90S servo horn', horn_piece)]
MEASURED = [('MG90S servo', (37.14, 33.38, 12.20), 7762.1), ('MG90S servo', (37.47, 34.17, 12.20), 7414.9), ('MG90S servo', (36.04, 34.46, 12.20), 7248.3),
            ('MG90S servo horn', (31.35, 6.90, 3.70), 240.9), ('MG90S servo horn', (31.35, 6.90, 3.70), 242.1)]      # (box about the principal axes, volume) read off the real pages:
# the chassis pages' servo; the nose and fit views' (whole, and its larger connected piece); the horn in the nose and fit views


class TurnedParts(unittest.TestCase):
    """An MG90S fused into a bigger mesh is found whichever way it is turned: by the box about its principal axes and by its volume."""
    wall = chamfered((0, 0, 0), (80, 60, 40), 3)

    def base(self, piece, name='Pan coil base (turned 180)'):
        return chassis({'base': part(merged(self.wall, piece), name)})

    def test_the_old_axis_aligned_check_is_blind_to_a_turned_part(self):                       # the control for the tests below
        for what, make in FUSED:
            V, F = merged(self.wall, make((200, 0, 0)))
            self.assertEqual([n for n, _ in aabb_fused(V, F)], [what])                           # square on, the old check sees it
            for turns in TURNS[:5]:
                V, F = merged(self.wall, turned(make((200, 0, 0)), *turns))
                self.assertEqual(aabb_fused(V, F), [], (what, turns))                            # turned, it does not

    def test_a_turned_servo_or_horn_is_boxed_and_gated(self):
        for what, make in FUSED:
            for turns in TURNS:
                with self.subTest(what=what, turns=turns):
                    page = self.base(turned(make((200, 0, 0)), *turns))
                    p = problems(page, licence=True); self.assertEqual(len(p), 1, p); self.assertIn(what, p[0]); self.assertIn('not a box', p[0])
                    out = B.standin_page(page, [])
                    self.assertEqual(problems(out, licence=True), [])
                    V0, F0 = dec_node(data_of(page)['m']['base']); V, F = dec_node(data_of(out)['m']['base'])
                    piece = lambda V: V[V[:, 0] > 100]
                    self.assertEqual(len({tuple(r) for r in piece(V)}), 8)                       # the part is 8 vertices now ...
                    np.testing.assert_allclose(piece(V).min(0), piece(V0).min(0), atol=0.03)     # ... the bounds of what it replaced
                    np.testing.assert_allclose(piece(V).max(0), piece(V0).max(0), atol=0.03)
                    self.assertEqual({tuple(r) for r in V if r[0] <= 100}, {tuple(r) for r in V0 if r[0] <= 100})       # and the wall is whole
                    self.assertEqual(len(F), len(F0) - len(make()[1]) + 12)

    def test_a_mirrored_part_is_found_too(self):                                                 # a left-hand head: a mirror image reads as inside out
        for what, make in FUSED:
            V, F = make((0, 0, 0)); M = (V * [-1, 1, 1] + [230, 0, 0], F)
            for name, m in (('inside out', M), ('faces turned back', (M[0], M[1][:, ::-1]))):
                with self.subTest(what=what, how=name):
                    page = self.base(turned(m, ('y', 37), ('z', 10))); p = problems(page, licence=True)
                    self.assertEqual(len(p), 1, p); self.assertIn(what, p[0]); self.assertEqual(problems(B.standin_page(page, []), licence=True), [])

    def test_look_alikes_are_left_alone(self):                                                   # the controls: same size, another volume; or another part
        v, f = servo_piece()
        solids = {'a solid block of the servo box': sized((36.8, 33.9, 12.2), (200, 0, 0)), 'a plus sign in the servo box': prism(CROSS_PROFILE, 12.2, (200, 0, 0)),
                  'a 52 mm track roller': roller(52, 12.2, (200, 0, 0)), 'a thin 52 mm roller': roller(52, 7.0, (200, 0, 0)),
                  'a servo 14 mm thick': prism(SERVO_PROFILE, 14.0, (200, 0, 0)), 'a servo 10% longer': (v * [1.1, 1, 1] + [200, 0, 0], f),
                  'a horn-sized block': sized((31.35, 6.9, 3.7), (200, 0, 0), 0.5),
                  'a 28 mm roller of the servo volume': roller(28, 12.2, (200, 0, 0)), 'a block of the servo volume': sized((30, 20.8, 12.2), (200, 0, 0), 0.5),
                  'a block of the horn volume': sized((10, 6.8, 3.7), (200, 0, 0), 0.3)}
        for name, m in solids.items():
            for turns in ((), (('x', 10), ('z', 37)), (('y', 37), ('x', 10))):
                with self.subTest(name=name, turns=turns):
                    page = self.base(turned(m, *turns))
                    self.assertEqual(problems(page, licence=True), []); self.assertEqual(B.standin_page(page, []), page)

    def test_the_servo_and_horn_models_the_pages_carry_are_inside_the_tolerances(self):
        for name, ext, vol in MEASURED:
            s = next(x for x in B.SHAPES if x[0] == name)
            with self.subTest(name=name, vol=vol):
                self.assertTrue(all(abs(a - b) <= s[3] for a, b in zip(ext, s[1])), (ext, s[1])); self.assertLessEqual(abs(vol - s[2]) / s[2], s[4])
        for name, make in FUSED:                                                                 # and so are the test's own pieces
            ext, vol = B._piece_size(*make())
            s = next(x for x in B.SHAPES if x[0] == name)
            self.assertTrue(np.all(np.abs(ext - np.asarray(s[1])) <= s[3] / 4), (name, ext)); self.assertLessEqual(abs(vol - s[2]) / s[2], s[4] / 4)

    def test_what_the_two_checks_measure_is_turn_invariant(self):
        for name, make in FUSED:
            e0, v0 = B._piece_size(*make())
            for turns in TURNS:
                e1, v1 = B._piece_size(*turned(make(), *turns))
                np.testing.assert_allclose(e1, e0, atol=1e-6); self.assertAlmostEqual(v1, v0, delta=1e-6 * v0)
        e, v = B._piece_size(*prism([(0, 0), (10, 0), (10, 20), (0, 20)], 30))                  # a block 10 x 20 x 30: the sides and the volume exactly
        np.testing.assert_allclose(e, [30, 20, 10], atol=1e-9); self.assertAlmostEqual(v, 6000, places=6)


PAY = 'QUJD' * 100                                   # 400 characters of base64: the payload of a mesh in a format the gate cannot read
UNCLEARED_NAMES = ['PCA9685 (Adafruit model)', 'PCA9685 (Adafruit size), over the motors', 'Pan servo (your MG90S model)',
                   'Tilt servo (your MG90S model)', 'MG90D wrist servo', 'mg90s', 'Servo horn, double arm (set 9; carries the torque)',
                   'servo-horn', 'Servo_Horn', 'Horn']
CLEAR_NAMES = ['Servo post v3', 'Servo connector, 14 x 8 x 3 (thickness assumed)', 'Servo lead, coiled in the ball (stays there)',
               'Servo plug, with the jumper wires plugged in', 'Input gear (set 9: your horn in its pocket, 1.0 under the servo block)',
               'Tub (new)', 'Cradle', 'Ball (your rev 2)', 'Tab block (under the servo window-end tab)', 'Wheel (printed): dish, disc and hub',
               'Motor pod (printed)', 'Gearmotor* (37 mm gearbox, 30:1 class)', 'TPU spring pads (printed)', 'Camera board (lens centred on its holes)',
               'Drive motor, left (INJORA 540 55T)', 'Pack, left (Zeee 2S 5200), on edge', 'Bed gasket (TPU cord)', 'Hailo-8L (M.2 2242)']
CREDITED_NAMES = ['Outer frame, left (outer-frame-v13)', 'Track pod, left (inner-frame-high-v10)', 'Track pod, left', 'Rear drive sprocket, left',
                  'Drive sprocket: 11 teeth, 14 pitch, between the horns', 'Road and return rollers, left', '4:1 crown gear, left', '4:1 pinion, left',
                  'Track cover: a box, 24 deep', 'TPU track, left', 'Big bevel gear', 'body-rover-v13', 'Motor mount', 'Luengoa flex track',
                  'Raspberry Pi 5 + active cooler', 'raspberry_pi_5']
def problems(page, ext='.html', licence=False):
    return B.geometry_problems(page, ext, licence)


class Names(unittest.TestCase):
    def test_uncleared_names(self):
        for n in UNCLEARED_NAMES:
            with self.subTest(n=n):
                self.assertTrue(B.is_uncleared(n))
        for n in CLEAR_NAMES + CREDITED_NAMES:                                             # controls
            with self.subTest(n=n):
                self.assertFalse(B.is_uncleared(n))

    def test_credited_names(self):
        for n in CREDITED_NAMES:
            with self.subTest(n=n):
                self.assertTrue(B.credited_kinds(n), n)
        for n in CLEAR_NAMES + UNCLEARED_NAMES:                                            # controls
            with self.subTest(n=n):
                self.assertEqual(B.credited_kinds(n), [])
        self.assertEqual(B.credited_kinds('Raspberry Pi 5 + active cooler'), ['Raspberry Pi 5'])
        self.assertIn('FPV-Rover V2.0', B.credited_kinds('Outer frame, left')); self.assertIn('Luengoa flex track', B.credited_kinds('TPU track, left'))


class GeometryGate(unittest.TestCase):
    def test_an_uncleared_part_must_be_a_box(self):
        for n in UNCLEARED_NAMES:
            with self.subTest(n=n):
                p = problems(chassis({'x': part(PCA, n)}), licence=True)                     # a licence does not excuse it
                self.assertEqual(len(p), 1, p); self.assertIn('not a box', p[0]); self.assertIn(n, p[0])
                self.assertEqual(problems(chassis({'x': part(cuboid((0, 0, 0), (60, 25, 12)), n)}), licence=True), [])        # the control: a box
                self.assertEqual(problems(chassis({'x': part(merged(*[cuboid((0, 0, 0), (1, 1, 1))] * 2), n)})), [])          # two boxes on the same 8 corners: still 8 distinct vertices

    def test_the_boundary_is_eight_distinct_vertices(self):
        V, F = cuboid((0, 0, 0), (1, 1, 1)); V = np.vstack([V, [[0.5, 0.5, 2.0]]]); F = np.vstack([F, [[8, 0, 1]]])
        self.assertEqual(distinct(enc16((V, F))), 9)
        self.assertEqual(len(problems(chassis({'x': part((V, F), 'PCA9685')}))), 1)
        self.assertEqual(problems(chassis({'x': part(cuboid((0, 0, 0), (1, 1, 1)), 'PCA9685')})), [])

    def test_other_names_may_be_any_shape(self):                                             # the controls
        for n in CLEAR_NAMES:
            with self.subTest(n=n):
                self.assertEqual(problems(chassis({'x': part(PCA, n)})), [])

    def test_credited_parts_need_a_licence(self):
        for n in CREDITED_NAMES:
            for m in (PCA, cuboid((0, 0, 0), (1, 1, 1))):                                  # drawn in full or as a box
                with self.subTest(n=n, boxed=len(m[0]) == 8):
                    p = problems(chassis({'x': part(m, n)}))
                    self.assertEqual(len(p), 1, p); self.assertIn('licence', p[0])
                    self.assertEqual(problems(chassis({'x': part(m, n)}), licence=True), [])

    def test_the_problem_names_the_credited_projects(self):
        p = problems(chassis({'a': part(PCA, 'Outer frame, left'), 'b': part(PCA, 'Raspberry Pi 5'), 'c': part(PCA, 'Tub')}))
        self.assertEqual(len(p), 1); self.assertIn('FPV-Rover V2.0', p[0]); self.assertIn('Raspberry Pi 5', p[0]); self.assertNotIn('Luengoa', p[0])

    def test_prose_in_a_page_with_readable_data_is_fine(self):
        page = chassis({'x': part(PCA, 'Tub (new)')}, prose='MG90S, PCA9685, Raspberry Pi 5, a sprocket and a servo horn', code='var s = "PCA9685 MG90S";',
                       shop=[['MG90S micro servo', 2, 'or your MG90Ds']], servos={'wrist': ['MG90S*', 2.0]})
        self.assertEqual(problems(page), [])
        for ext in ('.js', '.json'):                                                         # data files too: only meshes count
            self.assertEqual(problems('window.D=' + json.dumps({'m': {'x': part(PCA, 'Tub')}, 'shop': ['MG90S', 'PCA9685']}) + ';', ext), [])

    def test_a_servo_shaped_part_inside_a_bigger_mesh_is_a_problem(self):
        wall = chamfered((0, 0, 0), (80, 60, 40), 3)
        for what, make in FUSED:
            with self.subTest(what=what):
                V, F = make((200, 0, 0))
                base = part(merged(wall, (V, F)), 'Pan coil base (turned 180)')
                p = problems(chassis({'base': base}), licence=True)
                self.assertEqual(len(p), 1, p); self.assertIn(what, p[0]); self.assertIn('not a box', p[0]); self.assertIn('Pan coil base', p[0])
                boxed = part(merged(wall, cuboid(V.min(0), V.max(0))), 'Pan coil base')
                self.assertEqual(problems(chassis({'base': boxed}), licence=True), [])            # the same size as a box passes
                other = part(merged(wall, (V * [1.15, 1, 1], F)), 'Pan coil base')
                self.assertEqual(problems(chassis({'base': other}), licence=True), [])            # a part of another size passes
                quarter = part(merged(wall, turned((V, F), ('z', 90))), 'Base')
                self.assertEqual(len(problems(chassis({'base': quarter}))), 1)                    # turned a quarter: still found

    def test_meshes_stored_by_key_only_are_named_by_their_key(self):
        page = self.nose_page()
        p = problems(page)
        self.assertEqual(len(p), 4 + 1, p)                                                     # servo, tilt_servo, horn (A and B count once each), pca; and the licence
        for k in ('servo', 'tilt_servo', 'horn', 'pca'):
            self.assertTrue(any(k in x and 'not a box' in x for x in p), (k, p))
        self.assertTrue(any('licence' in x for x in p))
        out = B.standin_page(page, ['PCA9685', 'MG90', 'servo horn'])
        self.assertEqual(problems(out, licence=True), []); self.assertEqual(len(problems(out)), 1)       # only the Pi's credit is left

    def nose_page(self):
        m = {'pca': dict(enc16(PCA), c=1, grp='elec', body=False), 'pi': dict(enc16(TUB), c=1, grp='elec', body=False)}
        v = {s: {k: dict(enc16(PCA), c=1, grp='head', body=False) for k in ('servo', 'tilt_servo', 'horn', 'well')} for s in 'AB'}
        return data_page('const D', {'m': m, 'v': v, 'yc': 0})

    def test_a_lineup_geometry_takes_the_names_of_the_parts_that_use_it(self):
        geo = [enc16(PCA), enc16(TUB)]; txt = ['PCA9685 (Adafruit model)', 'note', 'Tub (new)']
        parts = lambda ls: [{'g': g, 'o': [0, 0, 0], 'c': 1, 'grp': 'x', 'l': l, 'n': 1} for g, l in ls]
        page = data_page('const D', {'geo': geo, 'txt': txt, 'designs': [{'id': 'a', 'parts': parts([(0, 0), (1, 2)])}], 'yc': 0}, sep=(',', ':'))
        p = problems(page); self.assertEqual(len(p), 1, p); self.assertIn('PCA9685', p[0])
        self.assertEqual(problems(B.standin_page(page, ['PCA9685'])), [])
        ok = data_page('const D', {'geo': geo, 'txt': txt, 'designs': [{'id': 'a', 'parts': parts([(1, 2)])}], 'yc': 0}, sep=(',', ':'))       # the control: only the tub uses a shape
        self.assertEqual(problems(ok), [])
        mixed = data_page('const D', {'geo': geo, 'txt': txt, 'designs': [{'id': 'a', 'parts': parts([(0, 0), (0, 2)])}], 'yc': 0}, sep=(',', ':'))
        self.assertEqual(len(problems(mixed)), 1)                                              # a part called PCA9685 uses it: it must be a box
        self.assertEqual(problems(B.standin_page(mixed, ['PCA9685'])), [])

    def test_the_fit_view_and_the_sleeve_formats(self):
        fit = {'servo': dict(enc32(chamfered((0, 0, 0), SERVO, 2)), label='Pan servo (your MG90S model)', group='coil'),
               'post': dict(enc32(TUB), label='Servo post v3', group='head')}
        page = data_page('window.FIT', fit); p = problems(page); self.assertEqual(len(p), 1, p); self.assertIn('Pan servo', p[0])
        self.assertEqual(problems(B.standin_page(page, ['MG90'])), [])
        code = "const LOOK = {servo: ['Tilt servo (your MG90S)', '#3B4046'], post: ['Post v3', '#D9622B']};"
        page = data_page('window.PARTS', {'servo': enc32(chamfered((0, 0, 0), SERVO, 2)), 'post': enc32(TUB)}, code=code)
        p = problems(page); self.assertEqual(len(p), 1, p); self.assertIn('Tilt servo', p[0])
        self.assertEqual(problems(B.standin_page(page, ['MG90'])), [])

    def test_a_mesh_that_cannot_be_decoded_is_a_problem_when_it_is_named_like_one(self):
        bad = {'m': {'x': {'v': '!!!', 'f': 'AAAA', 'i32': False, 'label': 'PCA9685 board'}, 'y': {'v': '!!!', 'f': 'AAAA', 'i32': False, 'label': 'Tub'}}}
        p = problems(data_page('const D', bad)); self.assertEqual(len(p), 1, p); self.assertIn('PCA9685', p[0])

    # a 3D page in a format the gate cannot read: a name in a mesh-like context is a problem, so the item stays held
    def opaque(self, label, payload=PAY):
        return '<!doctype html><title>T</title><script>const P=[{name:"mount",col:"#e07a2e",label:\'%s\',b64:"%s"}];\nfunction stl(b){}</script>' % (label, payload)

    def test_unreadable_3d_data_that_shows_an_uncleared_name_is_a_problem(self):
        for n in ('PCA9685 board', 'Pan servo (MG90S)', 'servo horn'):
            with self.subTest(n=n):
                p = problems(self.opaque(n), licence=True); self.assertEqual(len(p), 1, p); self.assertIn('cannot read', p[0])
        self.assertEqual(problems(self.opaque('Adapter (prints as shown, lying flat)')), [])               # the control
        self.assertEqual(problems('<script>document.title = "MG90S bench";</script>'), [])                  # a name in code that carries no mesh
        self.assertEqual(problems('<p>PCA9685</p><script>var a = [1, 2, 3];</script>'), [])

    def test_unreadable_3d_data_that_shows_a_credited_name_needs_a_licence(self):
        p = problems(self.opaque('Outer frame, left')); self.assertEqual(len(p), 1); self.assertIn('licence', p[0])
        self.assertEqual(problems(self.opaque('Outer frame, left'), licence=True), [])

    def test_a_name_inside_the_base64_payload_does_not_count(self):
        self.assertEqual(problems(self.opaque('Adapter', 'A' * 300 + 'PCA9685' + 'A' * 300 + '/MG90S/' + 'A' * 200)), [])           # control

    def test_json_whose_meshes_are_in_another_encoding(self):                                               # ball_parts.js
        js = lambda n: 'window.BALL_META={"H":1};\nwindow.BALL_PARTS=' + json.dumps([{'n': n, 'g': 'tilt', 'b': PAY}]) + ';\n'
        p = problems(js('servo horn'), '.js', True); self.assertEqual(len(p), 1, p); self.assertIn('cannot read', p[0])
        self.assertEqual(problems(js('ball'), '.js', True), [])
        self.assertEqual(len(problems(js('Raspberry Pi 5'), '.js')), 1)

    def test_mesh_files_are_scanned_as_a_whole(self):
        obj = lambda n: 'o %s\nv 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n' % n
        for ext in ('.obj', '.gltf', '.mtl'):
            with self.subTest(ext=ext):
                self.assertEqual(len(problems(obj('PCA9685'), ext)), 1); self.assertEqual(problems(obj('plate'), ext), [])
        self.assertEqual(problems(obj('PCA9685'), '.txt'), [])                                              # prose files are not mesh-like
        self.assertEqual(problems('<p>PCA9685</p>', '.html'), [])

    def test_the_gate_knows_the_servo_and_the_horn(self):
        self.assertEqual([s[0] for s in B.SHAPES], ['MG90S servo', 'MG90S servo horn'])
        for name, ext, vol, e_tol, v_tol in B.SHAPES:                                              # sides large to small, a volume, tolerances that are tight but not zero
            self.assertEqual(list(ext), sorted(ext, reverse=True)); self.assertGreater(vol, 0); self.assertTrue(0 < e_tol <= 1.0 and 0 < v_tol <= 0.1)


NOTE = "These pages began as design notes written to Zach during development, so 'you' and 'your' mean him."
LIST_URL = 'https://github.com/ZacharyShaver/FPVTank_Prototype/blob/research-sprint/THIRD_PARTY.md'
FPV_URL, LUENGOA_URL, PI_URL = ('https://www.printables.com/model/3150-fpv-rover-v20-tank', 'https://www.thingiverse.com/thing:7127065',
                                'https://printables.com/model/727155-raspberry-pi-5')
LIC_ALL = ('Shows parts from FPV-Rover V2.0 by Markus_p (CC BY-NC-SA 4.0), the flexible TPU track by Luengoa (CC BY-NC) and the Raspberry Pi 5 '
           'model (Printables 727155, CC0), credited in THIRD_PARTY.md. The PCA9685 board is a stand-in box.')


def luminance(hex_colour):
    c = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class CreditFooter(unittest.TestCase):
    """The credit is a small footer at the end of the page, in the page's flow; only the way back stays fixed."""
    P = '<title>T</title><div>x</div>'
    WITH_BODY = '<!doctype html><html><head><title>T</title></head><body><div>x</div></body></html>'
    CREDIT = 'Shows parts by A (CC BY-NC-SA 4.0) & "B" (CC0).'

    def footer(self, w):
        m = re.findall(r'<footer data-gallery-footer\b[^>]*>(.*?)</footer>', w, re.S)
        self.assertEqual(len(m), 1, m); return m[0]

    def credit_text(self, w):
        m = re.findall(r'<p data-gallery-credit\b[^>]*>(.*?)</p>', self.footer(w), re.S)
        self.assertEqual(len(m), 1, m); return html.unescape(m[0])

    def hrefs(self, w):
        return [a['href'] for a in tags(self.footer(w), 'a')]

    def test_the_footer_follows_the_page_content_and_is_not_fixed(self):
        for page in (self.P, self.WITH_BODY):
            with self.subTest(page=page[:20]):
                w = B.wrap_page(page, '../index.html', credit=self.CREDIT)
                self.assertEqual(self.credit_text(w), self.CREDIT)
                self.assertLess(w.index('<div>x</div>'), w.index('<footer')); self.assertLess(w.index('</footer>'), w.index('data-gallery-back'))
                f = re.search(r'<footer data-gallery-footer.*?</footer>', w, re.S).group(0)
                self.assertIsNone(re.search(r'position\s*:\s*(fixed|absolute|sticky)', f, re.I), f)         # in flow: it covers nothing
                self.assertEqual(w.count('position:fixed'), 1)                                                # the way back is the only fixed thing
                self.assertEqual(w.count('<div>x</div>'), 1)                                                  # the page is intact
        w = B.wrap_page(self.WITH_BODY, 'i.html', credit=self.CREDIT)
        self.assertLess(w.index('<footer'), w.index('</body>')); self.assertEqual(w.lower().count('</body>'), 1)       # inside the body, at its end

    def test_a_body_end_inside_a_script_is_not_where_the_footer_goes(self):
        page = '<script>var s = "</body>";</script><div>x</div>'
        w = B.wrap_page(page, 'i.html', credit=self.CREDIT)
        self.assertIn('var s = "</body>";</script><div>x</div>\n<footer', w)                          # after everything, the script untouched
        self.assertEqual(w.count('</body>'), 1)
        w = B.wrap_page(page + '</body>\n</HTML>\n', 'i.html', credit=self.CREDIT)                     # a real end of body, in any case: before that one
        self.assertEqual(w.lower().count('</body>'), 2); self.assertLess(w.index('<footer'), w.rindex('</body>'))
        self.assertIn('var s = "</body>";</script><div>x</div>\n<footer', w)

    def test_the_footer_has_the_licence_the_sources_and_the_list(self):
        w = B.wrap_page(self.P, 'i.html', credit=LIC_ALL)
        self.assertEqual(self.credit_text(w), LIC_ALL); self.assertEqual(self.hrefs(w), [FPV_URL, LUENGOA_URL, PI_URL, LIST_URL])
        for a in tags(self.footer(w), 'a'):
            self.assertEqual(list(a), ['href'])                                                           # plain links to other sites
        text = html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<style.*?</style>', '', self.footer(w), flags=re.S)))
        for words in ('FPV-Rover V2.0', 'Luengoa tracks', 'Raspberry Pi 5 model', 'THIRD_PARTY.md'):
            self.assertIn(words, text)

    def test_only_the_sources_the_licence_names_are_linked(self):                                         # the controls
        for lic, want in (('Shows the Raspberry Pi 5 model (Printables 727155, CC0), credited in THIRD_PARTY.md.', [PI_URL, LIST_URL]),
                          ('Shows FPV-Rover V2.0 parts and the Luengoa track.', [FPV_URL, LUENGOA_URL, LIST_URL]),
                          ('The MG90S servos are stand-in boxes: their licences are not recorded.', [LIST_URL])):
            with self.subTest(lic=lic[:30]):
                self.assertEqual(self.hrefs(B.wrap_page(self.P, 'i.html', credit=lic)), want)

    def test_the_note_alone_makes_a_footer_with_no_credit_and_no_links(self):
        w = B.wrap_page(self.P, 'i.html', note=NOTE)
        self.assertEqual(html.unescape(re.search(r'<p data-gallery-note\b[^>]*>(.*?)</p>', self.footer(w), re.S).group(1)), NOTE)
        self.assertNotIn('data-gallery-credit', w); self.assertEqual(tags(self.footer(w), 'a'), [])
        w = B.wrap_page(self.P, 'i.html', credit=LIC_ALL, note=NOTE)                                       # both: one footer, credit above the note
        self.assertLess(w.index('data-gallery-credit'), w.index('data-gallery-note')); self.assertEqual(self.credit_text(w), LIC_ALL)

    def test_no_credit_and_no_note_means_no_footer(self):                                                  # the controls
        for credit in (None, ''):
            self.assertNotIn('<footer', B.wrap_page(self.P, 'i.html', credit=credit, note=None))
        self.assertEqual(B.wrap_page(self.P, 'i.html'), B.wrap_page(self.P, 'i.html', credit=None, note=''))

    def test_the_text_is_escaped(self):
        w = B.wrap_page(self.P, 'i.html', credit='<script>alert(1)</script> "q" & <b>', note='<img src=x onerror=alert(1)>')
        self.assertNotIn('<script', w.lower()); self.assertNotIn('<b>', w); self.assertNotIn('<img', w)
        self.assertEqual(self.credit_text(w), '<script>alert(1)</script> "q" & <b>')

    def test_wrapping_again_changes_nothing_and_a_new_credit_replaces_the_old(self):
        for page in (self.P, self.WITH_BODY):
            with self.subTest(page=page[:20]):
                once = B.wrap_page(page, 'i.html', credit=self.CREDIT, note=NOTE)
                self.assertEqual(B.wrap_page(once, 'i.html', credit=self.CREDIT, note=NOTE), once)
                self.assertEqual(B.wrap_page(B.wrap_page(once, 'i.html', credit=self.CREDIT, note=NOTE), 'i.html', credit=self.CREDIT, note=NOTE), once)
                self.assertEqual(self.credit_text(B.wrap_page(once, 'i.html', credit='Another credit.', note=NOTE)), 'Another credit.')
                self.assertEqual(B.wrap_page(once, 'i.html'), B.wrap_page(page, 'i.html'))                  # none given: the footer goes
                self.assertEqual(B.wrap_page(once, 'i.html', note=NOTE).count('<footer'), 1)

    def test_the_back_link_is_the_same_with_or_without_a_footer(self):
        back = lambda w: [a for a in tags(w, 'a') if 'data-gallery-back' in a]
        self.assertEqual(back(B.wrap_page(self.P, 'i.html')), back(B.wrap_page(self.P, 'i.html', credit=LIC_ALL, note=NOTE)))
        self.assertEqual(len(back(B.wrap_page(self.P, 'i.html', credit=LIC_ALL, note=NOTE))), 1)

    def css(self, w):
        return re.search(r'<footer data-gallery-footer[^>]*><style>(.*?)</style>', w, re.S).group(1)

    def test_it_is_readable_in_light_and_dark_and_clear_of_the_back_link(self):
        css = self.css(B.wrap_page(self.P, 'i.html', credit=LIC_ALL)); light, dark = css.split('@media', 1)
        self.assertIn('prefers-color-scheme:dark', dark.replace(' ', ''))
        for name, part in (('light', light), ('dark', dark)):
            bg = re.search(r'footer\[data-gallery-footer\]\{[^}]*?background:(#[0-9a-f]{6})', part).group(1)
            fg = re.search(r'footer\[data-gallery-footer\]\{[^}]*?[; {]color:(#[0-9a-f]{6})', part).group(1)
            link = re.search(r'footer\[data-gallery-footer\] a\{[^}]*?color:(#[0-9a-f]{6})', part).group(1)
            self.assertGreaterEqual(contrast(fg, bg), 7, (name, fg, bg)); self.assertGreaterEqual(contrast(link, bg), 4.5, (name, link, bg))
        self.assertNotEqual(re.search(r'background:(#[0-9a-f]{6})', light).group(1), re.search(r'background:(#[0-9a-f]{6})', dark).group(1))
        pad = re.search(r'padding:[^;}]*calc\((\d+)px', light)                                              # room under the text for the fixed back link
        self.assertIsNotNone(pad); self.assertGreaterEqual(int(pad.group(1)), 56)

    def test_the_contrast_check_itself(self):                                                               # controls on the check
        self.assertAlmostEqual(contrast('#000000', '#ffffff'), 21, places=3); self.assertLess(contrast('#777777', '#888888'), 1.5)
        self.assertLess(contrast('#1c2124', '#1c2224'), 1.1)


class CardCredits(unittest.TestCase):
    """An item with a licence has a short Credits line under its caption that links the list of third-party files."""
    ITEM = dict(kind='page', title='A page', caption='The caption.', licence=LIC_ALL)

    class Nesting(HTMLParser):
        def __init__(self):
            super().__init__(); self.depth = self.deepest = 0
        def handle_starttag(self, tag, attrs):
            if tag == 'a':
                self.depth += 1; self.deepest = max(self.deepest, self.depth)
        def handle_endtag(self, tag):
            if tag == 'a':
                self.depth -= 1

    def credits(self, c):
        m = re.findall(r'<p class="credits">(.*?)</p>', c, re.S); self.assertEqual(len(m), 1, c); return m[0]

    def test_the_card_has_a_credits_line_under_the_caption_with_a_link_to_the_list(self):
        c = B.card(self.ITEM, 'pages/x.html', None); line = self.credits(c)
        self.assertLess(c.index('The caption.'), c.index('class="credits"'))
        text = html.unescape(re.sub(r'<[^>]+>', '', line)); self.assertTrue(text.startswith('Credits: '), text)
        for words in ('FPV-Rover V2.0 (CC BY-NC-SA 4.0)', 'Luengoa tracks (CC BY-NC)', 'Raspberry Pi 5 model (CC0)'):
            self.assertIn(words, text)
        self.assertEqual([a['href'] for a in tags(line, 'a')], [LIST_URL])
        self.assertEqual(tags(c, 'a')[0]['href'], 'pages/x.html')                                          # the card itself still opens the page

    def test_no_link_sits_inside_another(self):
        for item, thumb in ((self.ITEM, None), (self.ITEM, 'thumbs/x.jpg'), (dict(self.ITEM, kind='figure'), 'thumbs/x.jpg')):
            p = self.Nesting(); p.feed(B.card(item, 'pages/x.html', thumb)); self.assertEqual(p.deepest, 1)

    def test_only_the_named_sources_and_a_line_even_for_a_licence_that_names_none(self):
        text = lambda lic: html.unescape(re.sub(r'<[^>]+>', '', self.credits(B.card(dict(self.ITEM, licence=lic), 'x', None))))
        t = text('Shows the Raspberry Pi 5 model (Printables 727155, CC0).')
        self.assertIn('Raspberry Pi 5 model (CC0)', t); self.assertNotIn('FPV-Rover', t); self.assertNotIn('Luengoa', t)
        t = text('The MG90S servos are stand-in boxes: their licences are not recorded.')
        self.assertTrue(t.startswith('Credits: ')); self.assertNotIn('FPV-Rover', t)

    def test_the_text_from_the_manifest_cannot_reach_the_page(self):
        c = B.card(dict(self.ITEM, licence=EVIL + ' FPV-Rover', title=EVIL, caption=EVIL), 'pages/x.html', None)
        self.assertNotIn('<script', c.lower()); self.assertIn('FPV-Rover V2.0 (CC BY-NC-SA 4.0)', self.credits(c))

    def test_without_a_licence_the_card_is_as_it_was(self):                                               # the controls
        for lic in (None, ''):
            item = dict(self.ITEM); item['licence'] = lic
            c = B.card(item, 'pages/x.html', None)
            self.assertNotIn('credits', c); self.assertEqual(c, B.card({k: v for k, v in item.items() if k != 'licence'}, 'pages/x.html', None))
            self.assertTrue(c.startswith('<a class="card"') and c.endswith('</a>'))

    def test_in_a_whole_build_the_index_shows_the_line_only_on_items_with_a_licence(self):
        d, m = tiny_repo(); m['sections'][0]['items'][1]['licence'] = 'Shows FPV-Rover V2.0 parts.'; out = os.path.join(d, 'site')
        self.assertEqual(B.build(m, d, out)['problems'], []); idx = read(out, 'index.html')
        self.assertEqual(idx.count('class="credits"'), 1); self.assertEqual([a['href'] for a in tags(idx, 'a')], ['pages/p.html', 'media/f.png', LIST_URL])
        p = self.Nesting(); p.feed(idx); self.assertEqual(p.deepest, 1)
        self.assertTrue(re.search(r'<a class="card" href="media/f.png".*?</a>\s*<p class="credits">', idx, re.S))   # the line follows its own card
        self.assertIn('.credits{', idx)                                                                      # and the page styles it


class PageFooters(unittest.TestCase):
    """The footers a build gives its pages: every 3D page carries the note about 'you'; a licence adds the credit; figures and clips get none."""
    def build(self, **licences):
        d, m = tiny_repo(); put(os.path.join(d, 'a', 'v.mp4'), MP4)
        add_item(d, m, id='q', src='a/out/p.html'); add_item(d, m, id='v', kind='video', src='a/v.mp4')
        for it in m['sections'][0]['items']:
            if it['id'] in licences:
                it['licence'] = licences[it['id']]
        out = os.path.join(d, 'site'); r = B.build(m, d, out); self.assertEqual(r['problems'], [], r['problems']); return out

    def test_every_page_has_the_note_and_only_the_licensed_one_has_a_credit(self):
        out = self.build(p='Shows the Raspberry Pi 5 model (Printables 727155, CC0).')
        a, b = read(out, 'pages', 'p.html'), read(out, 'pages', 'q.html')
        for w in (a, b):
            self.assertEqual(html.unescape(re.search(r'<p data-gallery-note\b[^>]*>(.*?)</p>', w, re.S).group(1)), NOTE)
            self.assertEqual(w.count('<footer'), 1); self.assertEqual(w.count('data-gallery-back'), 1)
        self.assertIn('data-gallery-credit', a); self.assertIn(PI_URL, a); self.assertIn(LIST_URL, a)
        self.assertNotIn('data-gallery-credit', b); self.assertNotIn('<a href="https://', b.split('<footer')[1])         # no licence: no credit, no links

    def test_figures_and_clips_get_no_footer(self):
        out = self.build(p='Shows FPV-Rover V2.0 parts.', f='A figure credit.')
        self.assertNotIn('<footer', read(out, 'pages', 'v.html'))                                              # the clip's page
        self.assertEqual(sorted(os.listdir(os.path.join(out, 'pages'))), ['p.html', 'q.html', 'v.html'])       # the figure has no page to put one on

    def test_a_dir_page_and_its_siblings_still_link_and_pass_the_gates(self):                       # the footer's links are links, not loads
        d, m = tiny_repo(); os.makedirs(os.path.join(d, 'w')); put(os.path.join(d, 'w', 'v.html'), '<title>V</title><script src="data.js"></script>')
        put(os.path.join(d, 'w', 'data.js'), 'var x=1;'); add_item(d, m, id='v', src='w/v.html', dir=True, licence=LIC_ALL, standin=[])
        out = os.path.join(d, 'site'); r = B.build(m, d, out)
        self.assertEqual(r['problems'], [])
        self.assertIn(LIST_URL, read(out, 'pages', 'v', 'v.html'))


def stand_repo(**item):
    """A tiny repo whose page p is a chassis page with a PCA9685, an outer frame, a pan coil base with an MG90S fused in, and a tub."""
    d, m = tiny_repo()
    parts = {'pca': part(PCA, 'PCA9685 (Adafruit model)'), 'of': part(TUB, 'Outer frame, left (outer-frame-v13)'),
             'base': part(merged(chamfered((0, 0, 0), (80, 60, 40), 3), servo_piece((200, 0, 0))), 'Pan coil base (turned 180)'),
             'tub': part(TUB, 'Tub (new)')}
    put(os.path.join(d, 'a', 'out', 'p.html'), chassis(parts))
    m['sections'][0]['items'][0].update(item)
    return d, m


LIC = 'Shows parts from FPV-Rover V2.0 by Markus_p (CC BY-NC-SA 4.0). The PCA9685 board and MG90S servo are stand-in boxes: licences not recorded.'


class StandInBuild(unittest.TestCase):
    def build(self, **item):
        d, m = stand_repo(**item); out = os.path.join(d, 'site'); return d, out, B.build(m, d, out)

    def test_without_stand_ins_the_page_is_refused(self):
        d, out, r = self.build(licence=LIC)
        probs = [p for p in r['problems']]
        self.assertTrue(any('PCA9685' in p and 'not a box' in p for p in probs), probs)
        self.assertTrue(any('Pan coil base' in p and 'MG90S servo' in p for p in probs), probs)                                          # the fused one
        self.assertFalse(any('licence' in p for p in probs), probs)                                                                      # it has its licence

    def test_without_a_licence_the_credited_part_is_refused(self):
        d, out, r = self.build(standin=['PCA9685', 'MG90'])
        self.assertEqual(len(r['problems']), 1, r['problems']); self.assertIn('licence', r['problems'][0]); self.assertIn('p.html', r['problems'][0])

    def test_with_stand_ins_and_a_licence_the_build_is_clean_and_the_page_changed_only_there(self):
        d, out, r = self.build(standin=['PCA9685', 'MG90'], licence=LIC)
        self.assertEqual(r['problems'], [])
        built = read(out, 'pages', 'p.html'); D = data_of(built)['m']; D0 = data_of(read(d, 'a', 'out', 'p.html'))['m']
        self.assertEqual(distinct(D['pca']), 8); self.assertTrue(D['pca']['label'].endswith(SUFFIX))
        self.assertEqual(D['of'], D0['of']); self.assertEqual(D['tub'], D0['tub'])                                                       # the credited part and the tub are whole
        V, F = dec_node(D['base']); self.assertEqual(len({tuple(x) for x in V if 190 <= x[0] <= 235}), 8)                                  # the fused servo is a box
        self.assertEqual(sorted(D), sorted(D0))
        self.assertEqual(self.credit(built), LIC); self.assertIn('href="../index.html"', built)
        self.assertEqual(len(r['held']), 0); self.assertEqual(r['items'], 2)

    def credit(self, built):
        m = re.findall(r'<p data-gallery-credit\b[^>]*>(.*?)</p>', built, re.S); self.assertEqual(len(m), 1); return html.unescape(m[0])

    def test_the_source_page_is_not_touched(self):
        d, out, r = self.build(standin=['PCA9685'], licence=LIC)
        self.assertEqual(distinct(data_of(read(d, 'a', 'out', 'p.html'))['m']['pca']), 16)

    def test_a_licence_alone_adds_the_credit_line_and_no_stand_in(self):
        d, m = tiny_repo(); m['sections'][0]['items'][0]['licence'] = 'Credit <me>'
        out = os.path.join(d, 'site'); r = B.build(m, d, out)
        self.assertEqual(r['problems'], []); self.assertIn('Credit &lt;me&gt;', read(out, 'pages', 'p.html'))
        d, m = tiny_repo(); out = os.path.join(d, 'site'); B.build(m, d, out)
        self.assertNotIn('data-gallery-credit', read(out, 'pages', 'p.html'))                                                            # control

    def test_a_bad_standin_is_a_problem_not_a_crash(self):
        for bad in (['('], 'PCA9685', [1], {'a': 1}, ['ok', None]):
            with self.subTest(bad=bad):
                d, out, r = self.build(standin=bad, licence=LIC)
                self.assertTrue(any("item 'p'" in p and 'standin' in p for p in r['problems']), r['problems'])

    def test_an_empty_standin_still_boxes_the_fused_servo(self):
        d, out, r = self.build(standin=[], licence=LIC)
        self.assertFalse(any('Pan coil base' in p for p in r['problems']), r['problems'])
        self.assertTrue(any('PCA9685' in p for p in r['problems']))

    def test_a_sibling_file_of_a_dir_page_is_stood_in_and_checked(self):
        d, m = tiny_repo(); os.makedirs(os.path.join(d, 'w'))
        put(os.path.join(d, 'w', 'v.html'), '<title>V</title><script src="part.js"></script>')
        fit = {'servo': dict(enc32(sized(SERVO)), label='Pan servo (your MG90S model)', group='coil')}
        put(os.path.join(d, 'w', 'part.js'), 'window.FIT=' + json.dumps(fit) + ';')
        add_item(d, m, id='v', src='w/v.html', dir=True); out = os.path.join(d, 'site')
        probs = B.build(m, d, out)['problems']
        self.assertTrue(any('part.js' in p and 'not a box' in p for p in probs), probs)
        m['sections'][0]['items'][-1]['standin'] = ['MG90']
        self.assertEqual(B.build(m, d, out)['problems'], [])
        js = read(out, 'pages', 'v', 'part.js'); self.assertTrue(js.startswith('window.FIT=') and js.rstrip().endswith(';'))
        self.assertEqual(distinct(json.loads(js[len('window.FIT='):].rstrip().rstrip(';'))['servo']), 8)

    def test_a_file_named_like_an_uncleared_part_is_still_refused(self):
        d, m = tiny_repo(); os.makedirs(os.path.join(d, 'w'))
        put(os.path.join(d, 'w', 'v.html'), '<title>V</title><a href="mg90s.json">m</a>'); put(os.path.join(d, 'w', 'mg90s.json'), '{}')
        add_item(d, m, id='v', src='w/v.html', dir=True, standin=['MG90'])
        probs = B.build(m, d, os.path.join(d, 'site'))['problems']
        self.assertTrue(any('mg90s.json' in p for p in probs), probs)

    def test_a_held_item_with_stand_ins_is_still_not_built(self):
        d, m = stand_repo(standin=['PCA9685'], licence=LIC, hold='later'); out = os.path.join(d, 'site')
        r = B.build(m, d, out); self.assertEqual(r['held'], [('p', 'later')]); self.assertFalse(os.path.exists(os.path.join(out, 'pages', 'p.html')))

    def test_a_figure_with_a_standin_field_is_just_copied(self):
        d, m = tiny_repo(); m['sections'][0]['items'][1]['standin'] = ['x']; m['sections'][0]['items'][1]['licence'] = 'L'
        self.assertEqual(B.build(m, d, os.path.join(d, 'site'))['problems'], [])


class LinkItems(unittest.TestCase):
    HREF = 'https://example.org/paper?id=1&x=2'

    def link(self, **kw):
        return dict(dict(id='ext', kind='link', title='A paper', href=self.HREF, caption='cap'), **kw)

    def test_the_card_opens_in_a_new_tab_without_the_opener(self):
        c = B.card(self.link(), self.HREF, None); a = tags(c, 'a')[0]
        self.assertEqual(a['href'], self.HREF); self.assertEqual(a['target'], '_blank'); self.assertEqual(a['rel'], 'noopener')
        self.assertIn('A paper', c); self.assertIn('cap', c)
        for kind in ('page', 'figure', 'video'):                                                                                           # the controls
            a = tags(B.card(dict(kind=kind, title='t', caption='c'), 'pages/x.html', None), 'a')[0]
            self.assertNotIn('target', a); self.assertNotIn('rel', a)

    def test_the_card_escapes_its_text_and_href(self):
        c = B.card(self.link(title=EVIL, caption=EVIL, href='https://example.org/a"b'), 'https://example.org/a"b', None)
        self.assertNotIn('<script', c.lower()); self.assertEqual(tags(c, 'a')[0]['href'], 'https://example.org/a"b')

    def test_a_build_lists_the_link_without_copying_anything(self):
        d, m = tiny_repo(); add_item(d, m, **self.link()); out = os.path.join(d, 'site')
        m['sections'][0]['items'][-1].pop('make')
        r = B.build(m, d, out); self.assertEqual(r['problems'], []); self.assertEqual(r['items'], 3)
        cards = [a for a in tags(read(out, 'index.html'), 'a') if a.get('target') == '_blank']
        self.assertEqual([a['href'] for a in cards], [self.HREF]); self.assertEqual(cards[0]['rel'], 'noopener')
        self.assertEqual(sorted(os.listdir(os.path.join(out, 'pages'))), ['p.html'])

    def test_a_link_can_have_a_thumb(self):
        d, m = tiny_repo(); add_item(d, m, **self.link(thumb='a/f.png')); out = os.path.join(d, 'site')
        r = B.build(m, d, out); self.assertEqual(r['problems'], []); self.assertTrue(os.path.exists(os.path.join(out, 'thumbs', 'ext.jpg')))
        self.assertIn('thumbs/ext.jpg', read(out, 'index.html'))

    def test_an_external_link_is_not_a_load_and_does_not_trip_the_host_gate(self):
        d, m = tiny_repo(); add_item(d, m, **self.link(href='https://some-other-host.example/p')); out = os.path.join(d, 'site')
        self.assertEqual(B.build(m, d, out)['problems'], [])

    def test_only_a_plain_https_link_is_accepted(self):
        ok = [self.HREF, 'https://example.org', 'HTTPS://Example.ORG/x', 'https://example.org:8443/x#f']
        bad = ['http://example.org/', 'javascript:alert(1)', 'data:text/html,hi', '//example.org/x', 'example.org/x', '/pages/x.html', '', 'https://',
               'https:///x', 'https://example.org/a b', 'https://example.org/a"b', "https://example.org/a'b", 'https://example.org/<x>',
               'https://user:pw@example.org/', 'ftp://example.org/', 'https://example.org/\nx',
               'https://claude.ai/artifact/' + ID, 'https://www.claude.ai/code/artifact/' + ID2 + '/x']
        for href in ok + bad:
            with self.subTest(href=href):
                d, m = tiny_repo(); add_item(d, m, **self.link(href=href)); r = B.build(m, d, os.path.join(d, 'site'))
                want = href in ok
                self.assertEqual(r['problems'] == [], want, r['problems'])
                if not want:
                    self.assertTrue(any("'ext'" in p and 'href' in p for p in r['problems']), r['problems'])
                    if href.strip():
                        self.assertNotIn(href.strip(), read(d, 'site', 'index.html'))                                                    # a refused link is not in the index
        d, m = tiny_repo(); add_item(d, m, id='ext', kind='link', title='t', caption='c')                                                # no href at all
        self.assertTrue(any("'ext'" in p and 'href' in p for p in B.build(m, d, os.path.join(d, 'site'))['problems']))

    def test_a_held_link_is_not_shown(self):
        d, m = tiny_repo(); add_item(d, m, **self.link(hold='not yet')); out = os.path.join(d, 'site')
        r = B.build(m, d, out); self.assertEqual(r['held'], [('ext', 'not yet')]); self.assertNotIn(self.HREF.replace('&', '&amp;'), read(out, 'index.html'))


class SectionIntro(unittest.TestCase):
    def test_the_intro_sits_under_the_heading_and_is_escaped(self):
        m = {'title': 'T', 'intro': 'I', 'sections': [{'name': 'Sect', 'intro': EVIL + ' & more', 'items': [{'id': 'p'}]}]}
        out = B.index_html(m, {'p': 'CARD'})
        self.assertNotIn('<script', out.lower()); self.assertRegex(out, r'<h2>Sect</h2><p class="sect-intro">&lt;script&gt;alert\(1\)&lt;/script&gt; &amp; more</p><div class="grid">CARD</div>')

    def test_no_intro_no_paragraph(self):                                                                                                # the controls
        for sec in ({'name': 'Sect', 'items': [{'id': 'p'}]}, {'name': 'Sect', 'intro': '', 'items': [{'id': 'p'}]}):
            out = B.index_html({'title': 'T', 'intro': 'I', 'sections': [sec]}, {'p': 'CARD'})
            self.assertNotIn('sect-intro"', out.split('</style>')[1]); self.assertIn('<h2>Sect</h2><div class="grid">CARD</div>', out)

    def test_an_intro_does_not_make_an_empty_section_appear(self):
        m = {'title': 'T', 'intro': 'I', 'sections': [{'name': 'Empty', 'intro': 'words', 'items': [{'id': 'gone'}]}]}
        out = B.index_html(m, {}); self.assertNotIn('Empty', out); self.assertNotIn('words', out)

    def test_placeholders_in_an_intro_stay_literal(self):
        out = B.index_html({'title': 'T', 'intro': 'I', 'sections': [{'name': 'S', 'intro': 'about {{BUILT}} and {{TITLE}}', 'items': [{'id': 'p'}]}]}, {'p': 'C'})
        self.assertIn('about {{BUILT}} and {{TITLE}}', out)

    def test_a_whole_build_shows_the_intro_and_the_template_styles_it(self):
        d, m = tiny_repo(); m['sections'][0]['intro'] = 'What this section is.'; out = os.path.join(d, 'site')
        self.assertEqual(B.build(m, d, out)['problems'], []); idx = read(out, 'index.html')
        self.assertIn('<p class="sect-intro">What this section is.</p>', idx); self.assertIn('.sect-intro{', idx)


class RealPages(unittest.TestCase):
    """The manifest's 3D pages as they are on disk (regenerable output: skipped where it is absent)."""
    def items(self):
        with open(B.MANIFEST, encoding='utf-8') as fh:
            return [i for s in json.load(fh)['sections'] for i in s['items']]

    def test_every_released_page_passes_the_gate_once_its_stand_ins_are_made(self):
        for it in self.items():
            src = os.path.join(B.ROOT, it.get('src', ''))
            if it['kind'] != 'page' or it.get('hold') or it.get('dir') or not os.path.isfile(src):
                continue
            with self.subTest(item=it['id']):
                text = read(src); self.assertIsInstance(it.get('standin', []), list)
                if 'standin' in it:
                    text = B.standin_page(text, it['standin'])
                self.assertEqual(B.geometry_problems(text, '.html', bool(it.get('licence'))), [])

    def test_the_gate_still_finds_what_the_stand_ins_cover(self):                       # the negative control on the test above
        for it in self.items():
            src = os.path.join(B.ROOT, it.get('src', ''))
            if it.get('standin') and not it.get('hold') and os.path.isfile(src) and it['id'] in ('hull', 'head-fit'):
                with self.subTest(item=it['id']):
                    self.assertTrue(B.geometry_problems(read(src), '.html', True))

    def test_the_fourteen_pages_once_held_for_third_party_parts_are_released(self):
        ids = {'trainerstep', 'lineup', 'concept', 'hull', 'rugged', 'legs-v2', 'tail-arms', 'guard-arm', 'guard-flippers', 'trainer', 'trainer6',
               'nose', 'variants', 'head-fit'}
        by = {i['id']: i for i in self.items()}
        for i in sorted(ids):
            with self.subTest(item=i):
                self.assertNotIn('hold', by[i]); self.assertTrue(by[i]['standin']); self.assertTrue(by[i]['licence'].strip())
        for i in ids - {'trainerstep', 'trainer', 'trainer6', 'nose', 'head-fit'}:                 # the pages that show FPV-Rover parts say so
            self.assertIn('FPV-Rover V2.0 by Markus_p (CC BY-NC-SA 4.0)', by[i]['licence'])
        for i in ('trainerstep', 'trainer', 'trainer6', 'nose'):                                      # the pages that show the Pi say so
            self.assertIn('Raspberry Pi 5 model (Printables 727155, CC0)', by[i]['licence'])

    def test_released_items_carry_what_the_build_needs(self):
        for it in self.items():
            if it.get('standin') is not None:
                with self.subTest(item=it['id']):
                    self.assertEqual(it['kind'], 'page'); self.assertFalse(it.get('hold')); self.assertTrue(it.get('licence', '').strip())
                    self.assertTrue(all(isinstance(p, str) and p for p in it['standin']))

    def test_the_captions_the_final_review_corrected(self):
        by = {i['id']: i['caption'] for i in self.items()}
        self.assertEqual(by['body-options'], 'Three body options on the same head: the low Scout, the Crawler with a tail and a hoop over the head, and the Workhorse with a crane arm.')
        self.assertTrue(by['h2-surrogate-detail'].endswith(" (the right panel's 'peak' is an edge-rounding setting, not a probability)"))
        self.assertIn('H3: the pen-and-paper tally of the first 6 cm hand-drop session', by['h3-tally-sheet'])
        self.assertEqual(by['sim-drops'], 'H3: scale bodies dropped in MuJoCo, default floor beside bouncing floor; at 30 cm the bouncing floor scored a Brier score of 0.63 against 1.16 for the default.')
        for old in ('on the same head and tracks', 'the paper tally', 'the difference that moved'):                      # what they replaced
            self.assertFalse(any(old in c for c in by.values()), old)
        self.assertEqual(sum('peak' in c for c in by.values()), 1)                                                          # the note sits on one figure only

    def real_meshes(self):
        for it in self.items():
            src = os.path.join(B.ROOT, it.get('src', ''))
            if it['kind'] == 'page' and not it.get('hold') and not it.get('dir') and os.path.isfile(src):
                for blk in B._scan(read(src)).blocks:
                    for m in blk.meshes:
                        d = B._decode(m.node)
                        if d is not None and d[1].size:
                            yield it['id'], m, d

    def test_the_turn_proof_check_finds_exactly_the_pieces_the_axis_aligned_one_found(self):
        pieces = 0
        for pid, m, (V, F) in self.real_meshes():
            if any(B.is_uncleared(x) for x in m.names if isinstance(x, str)):
                continue                                                                            # named parts are boxed by name, not by size
            old = sorted((n, mask.tobytes()) for n, mask in aabb_fused(V, F)); new = sorted((n, mask.tobytes()) for n, mask in B._fused(V, F))
            self.assertEqual(new, old, (pid, m.path)); pieces += len(new)
        if not pieces:
            self.skipTest('the 3D pages are not built here')
        self.assertGreater(pieces, 10)                                                              # the servos fused into the pan coil bases

    def test_the_real_servo_and_horn_are_found_whichever_way_they_are_turned(self):
        fit = os.path.join(B.ROOT, 'head-v2', 'out', 'fit-view', 'head-pan-coil-fit.html')
        if not os.path.isfile(fit):
            self.skipTest('the fit view is not built here')
        parts = {m.node.get('label', ''): B._decode(m.node) for blk in B._scan(read(fit)).blocks for m in blk.meshes}
        servo = next(d for k, d in parts.items() if 'Pan servo' in k); horn = next(d for k, d in parts.items() if 'horn' in k.lower())
        wall = chamfered((0, 0, 0), (80, 60, 40), 3)
        for what, (V, F) in (('MG90S servo', servo), ('MG90S servo horn', horn)):
            shifted = (V - V.mean(0) + [200, 0, 0], F)
            for turns in [()] + TURNS:
                with self.subTest(what=what, turns=turns):
                    page = chassis({'base': part(merged(wall, turned(shifted, *turns)), 'Pan coil base')})
                    p = problems(page, licence=True); self.assertEqual(len(p), 1, p); self.assertIn(what, p[0])
                    self.assertEqual(problems(B.standin_page(page, []), licence=True), [])
        for what, other in (('the PCA9685', PCA), ('a roller', roller(52, 12.2))):                    # the controls: other parts of the robot are not boxed
            page = chassis({'base': part(merged(wall, turned(other, ('x', 10), ('z', 37))), 'Pan coil base')})
            self.assertEqual(problems(page, licence=True), [], what)
