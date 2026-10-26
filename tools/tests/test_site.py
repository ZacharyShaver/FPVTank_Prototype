# tools/tests/test_site.py
import os, re, sys, unittest
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

    def test_the_real_manifest_holds_the_pages_with_third_party_parts(self):
        with open(B.MANIFEST, encoding='utf-8') as fh:
            items = [i for s in json.load(fh)['sections'] for i in s['items']]
        for it in items:
            src = os.path.join(B.ROOT, it['src'])
            if it['kind'] != 'page' or not os.path.exists(src):
                continue
            with open(src, encoding='utf-8', errors='replace') as fh:
                hits = B.third_party(fh.read())
            with self.subTest(item=it['id']):
                self.assertEqual(bool(hits), 'hold' in it and 'licence' not in it, hits)       # held exactly when it has third-party parts
        self.assertEqual(len([i for i in items if 'hold' in i]), 14)
        for it in items:
            if 'hold' in it:
                self.assertIn('Zach', it['hold']); self.assertIn('FPV-Rover V2.0 CC BY-NC-SA 4.0', it['hold'])


class ThirdParty(unittest.TestCase):
    LABELS = ['outer-frame', 'Outer_Frame', 'outer frame', 'sprocket', 'Sprocket_L', 'PCA9685', 'pca9685', 'MG90S', 'mg90s',
              'RASPBERRY_PI', 'Raspberry Pi 5', 'raspberry-pi']
    CLEAN = ['camera', 'Scorpion tank', 'frame', 'wheel', 'servo', 'raspberry jam', 'hull', 'outer shell', 'rocket']

    def test_the_patterns_match_every_known_label(self):
        for t in self.LABELS:
            with self.subTest(t=t):
                self.assertTrue(any(rx.search(t) for rx in B.THIRD_PARTY)); self.assertTrue(B.third_party('{"name":"%s"}' % t))
        for t in self.CLEAN:                                                       # controls
            with self.subTest(t=t):
                self.assertFalse(any(rx.search(t) for rx in B.THIRD_PARTY)); self.assertEqual(B.third_party('<p>%s</p>' % t), [])

    def test_a_page_with_a_third_party_label_fails_the_build(self):
        for t in self.LABELS:
            with self.subTest(t=t):
                d, m = tiny_repo(); put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><p>%s</p>' % t)
                probs = B.build(m, d, os.path.join(d, 'site'))['problems']
                self.assertTrue(any(h in p.lower() for h in B.third_party(t) for p in probs if 'licence' in p and 'p.html' in p), probs)

    def test_a_licence_field_lets_it_through(self):
        d, m = tiny_repo(); put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><p>MG90S and sprocket</p>')
        self.assertEqual(len(B.build(m, d, os.path.join(d, 'site'))['problems']), 1)       # reported once per page
        m['sections'][0]['items'][0]['licence'] = 'MG90S servo (origin unrecorded); sprocket from FPV-Rover V2.0 (CC BY-NC-SA 4.0)'
        self.assertEqual(B.build(m, d, os.path.join(d, 'site'))['problems'], [])
        d2, m2 = tiny_repo()                                                       # control: a clean page
        self.assertEqual(B.build(m2, d2, os.path.join(d2, 'site'))['problems'], [])

    def test_the_licence_covers_only_its_own_item(self):
        d, m = tiny_repo()
        put(os.path.join(d, 'a', 'out', 'p.html'), '<title>P</title><p>PCA9685</p>')
        put(os.path.join(d, 'a', 'out', 'q.html'), '<title>Q</title><p>PCA9685</p>')
        m['sections'][0]['items'][0]['licence'] = 'PCA9685 board (licence unrecorded)'; add_item(d, m, id='q', src='a/out/q.html')
        probs = B.build(m, d, os.path.join(d, 'site'))['problems']
        self.assertEqual(len(probs), 1); self.assertIn('q.html', probs[0])

    def test_a_sibling_file_of_a_dir_page_is_checked_by_name_and_by_text(self):
        d, m = tiny_repo(); os.makedirs(os.path.join(d, 'w'))
        put(os.path.join(d, 'w', 'v.html'), '<title>V</title><script src="part.js"></script><a href="mg90s.json">m</a>')
        put(os.path.join(d, 'w', 'part.js'), '// RASPBERRY_PI mesh'); put(os.path.join(d, 'w', 'mg90s.json'), '{}')
        add_item(d, m, id='v', src='w/v.html', dir=True)
        probs = B.build(m, d, os.path.join(d, 'site'))['problems']
        self.assertTrue(any('part.js' in p for p in probs), probs); self.assertTrue(any('mg90s.json' in p for p in probs), probs)
        m['sections'][0]['items'][-1]['licence'] = 'Raspberry Pi 5 (CC0), MG90S (unrecorded)'
        self.assertEqual(B.build(m, d, os.path.join(d, 'site'))['problems'], [])

    def test_a_figure_or_video_is_not_scanned_as_a_page(self):
        d, m = tiny_repo(); put(os.path.join(d, 'a', 'v.mp4'), MP4); add_item(d, m, id='v', kind='video', src='a/v.mp4', caption='MG90S bench')
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
    LINE = ('Some renders show parts from FPV-Rover V2.0 by Markus_p (CC BY-NC-SA 4.0) and the Raspberry Pi 5 model from '
            'Printables 727155 (CC0).')

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


if __name__ == '__main__':
    unittest.main()
