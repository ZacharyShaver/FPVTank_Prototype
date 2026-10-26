# tools/tests/test_leakscan.py
import dataclasses, os, sys, time, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import leakscan as L


def rules(text, path='x.ino'):
    return sorted({f.rule for f in L.scan_text(path, text)})


class TextRules(unittest.TestCase):
    def test_wifi_credentials_found(self):
        t = 'const char *ssid = "homenet";\nconst char *password = "Hunter2!x";\n'
        self.assertEqual(rules(t), ['credential'])
        self.assertEqual(len(L.scan_text('x.ino', t)), 2)

    def test_placeholder_credentials_not_found(self):        # the near-miss: the README's example
        t = 'const char* ssid = "your-ssid";\nconst char* password = "your-password";\n'
        self.assertEqual(rules(t), [])

    def test_tokens_and_keys(self):
        self.assertEqual(rules('t = "ghp_' + 'a' * 36 + '"'), ['token'])
        self.assertEqual(rules('-----BEGIN RSA PRIVATE KEY-----'), ['token'])
        self.assertEqual(rules('AKIA' + 'B' * 16), ['token'])

    def test_base64_blob_is_not_a_token(self):               # the near-miss: mesh data in a viewer .js
        self.assertEqual(rules('window.M={"v":"s8L3wRfbsr/lCUc/c7v3wbq4u798KF9AFtT3wUr9k7+S8pRAi7P3"}', 'v.js'), [])

    def test_personal_email_but_not_noreply(self):
        self.assertEqual(rules('mail me: someone@hotmail.com'), ['email'])
        self.assertEqual(rules('Co-Authored-By: Claude <noreply@anthropic.com>'), [])
        self.assertEqual(rules('36010164+Z@users.noreply.github.com'), [])

    def test_private_ip_but_not_public(self):
        self.assertEqual(rules("PRINTER = 'http://10.0.0.99:7125'", 'config.py'), ['private_ip'])
        self.assertEqual(rules('dns 8.8.8.8 and version 10.2', 'notes.md'), [])

    def test_user_paths(self):
        self.assertEqual(rules(r'C:\Users\someone\Downloads\x.stl', 'a.md'), ['user_path'])
        self.assertEqual(rules('/c/Users/someone/Documents', 'a.md'), ['user_path'])
        self.assertEqual(rules('the users of the tool', 'a.md'), [])

    def test_private_artifact_links(self):
        self.assertEqual(rules('https://claude.ai/artifact/FakeArtifactId0123abcd', 'README.md'), ['artifact_link'])

    def test_redaction_never_shows_the_value(self):
        r = L.redact('Hunter2!x')
        self.assertNotIn('nter2', r)
        self.assertIn('9 chars', r)


# Review round 1. Every check below has a planted case it must flag and a near-miss it must not.
class CredentialShapes(unittest.TestCase):
    def test_prefixed_and_suffixed_names(self):
        for t in ('WIFI_PASSWORD = "Hunter2!x"', "wifi_password = 'Hunter2!x'", 'WIFI_SSID = "homenet"',
                  'db_passwd = "Hunter2!x"', 'wifiPassword = "Hunter2!x"', 'ROBOT_PSK="Hunter2!x"'):
            self.assertEqual(rules(t), ['credential'], t)
        for t in ('bypass = "enabled"', 'username = "someone"', 'compass_dir = "north"'):    # no credential word in the name
            self.assertEqual(rules(t), [], t)

    def test_bare_pass_name_in_quoted_form(self):            # archive/.../code.py holds PASS = "..." beside SSID
        for t in ('PASS = "Hunter2!x"', "WIFI_PASS = 'Hunter2!x'", 'wifi-pass: "Hunter2!x"'):
            self.assertEqual(rules(t), ['credential'], t)
        for t in ('PASS_R = "0.5"', 'bypass = "yes"', 'pass = get_pass()', 'PASS = 12'):
            self.assertEqual(rules(t), [], t)

    def test_separators_quotes_and_json_keys(self):
        for t in ('password: "Hunter2!x"', "'password': 'Hunter2!x'", '{"password": "Hunter2!x"}', '"wifi_password":"Hunter2!x"',
                  'password := "Hunter2!x"', 'password: str = "Hunter2!x"', 'char ssid[] = "homenet";', 'password = "it\'s Hunter2"'):
            self.assertEqual(rules(t), ['credential'], t)
        self.assertEqual([f.value for f in L.scan_text('x.ino', 'password = "it\'s Hunter2"')], ["it's Hunter2"])   # the whole quoted value
        for t in ('if (password != "")', '"password": ""', '"password": "your_password"', '<input type="password" name="pw">',
                  'password = input("Wi-Fi password")'):
            self.assertEqual(rules(t), [], t)

    def test_pwd_only_in_the_quoted_form(self):
        self.assertEqual(rules('pwd = "Hunter2!x"'), ['credential'])
        self.assertEqual(rules('pwd = os.getcwd()', 'a.py'), [])
        self.assertEqual(rules('PWD=/tmp/work', 'a.sh'), [])

    def test_unquoted_env_style(self):
        for t in ('WIFI_PASSWORD=Hunter2!x', 'export WIFI_SSID=homenet', 'DB_PASSWD = hunter2', 'ROBOT_PSK=Hunter2!x  # home',
                  'WIFI_PASSWORD=Hunter2!x\r\n'):
            self.assertEqual(rules(t, '.env'), ['credential'], t)
        for t in ('WIFI_PASSWORD=${WIFI_PASSWORD}', 'WIFI_PASSWORD=$WIFI_PASSWORD', 'WIFI_PASSWORD=<your-password>', 'WIFI_PASSWORD=',
                  'WIFI_PASSWORD=********', 'WIFI_SSID=xxxxxxxx', 'PASSWORD = None', 'password = get_password()',
                  'password = os.getenv("WIFI_PASSWORD")', 'pw = os.environ["WIFI_PASSWORD"]'):
            self.assertEqual(rules(t, '.env'), [], t)

    def test_unquoted_yaml_style(self):
        for t in ('wifi_password: Hunter2!x', '  password: hunter2', '- passwd: hunter2', 'db-password: Hunter2!x  # prod'):
            self.assertEqual(rules(t, 'c.yml'), ['credential'], t)
        for t in ('password: ${PASSWORD}', 'password: $PASSWORD', 'password: {{ vault_password }}', 'password: {{vault_password}}', 'password: [a, b]', 'password: [a,b]', 'password:',
                  'password: see the sticky note', 'password: !vault |', 'password: null'):
            self.assertEqual(rules(t, 'c.yml'), [], t)

    def test_placeholders_stay_unflagged(self):
        for t in ('ssid = "your_ssid"', 'password = "your_password"', 'password = "<your password>"', 'ssid = "<ssid>"',
                  'password = "${WIFI_PASSWORD}"', 'password = "$WIFI_PASSWORD"', 'password = "********"', 'password = "xxxxxxxx"'):
            self.assertEqual(rules(t), [], t)
        self.assertEqual(rules('password = "Hunter2!x"'), ['credential'])          # control: a real-looking value is flagged

    def test_prose_is_not_a_credential(self):                # line 142 of the WiFiClient README
        t = '* **Wi-Fi not connected:** Check the SSID and password and also that the signal has sufficient strength.'
        self.assertEqual(rules(t, 'README.md'), [])

    def test_arduino_define_macros(self):                    # no '=' in `#define WIFI_PASSWORD "..."`
        for t in ('#define WIFI_PASSWORD "Hunter2!x"', '#define WIFI_SSID "homenet"', '# define WIFI_PASS "Hunter2!x"'):
            self.assertEqual(rules(t), ['credential'], t)
        for t in ('#define WIFI_PASSWORD "your-password"', '#define PASSWORD_MAX 8', '#define WIFI_PASSWORD_H', '#define BYPASS "yes"'):
            self.assertEqual(rules(t), [], t)

    def test_wifi_begin_positional(self):
        t = 'WiFi.begin("homenet", "Hunter2!x");'
        self.assertEqual(rules(t), ['credential'])
        self.assertIn('Hunter2!x', [f.value for f in L.scan_text('x.ino', t)])      # the password argument itself
        self.assertEqual(rules('WiFi.begin(ssid, "Hunter2!x");'), ['credential'])
        for t in ('WiFi.begin(ssid, password);', 'WiFi.begin("your-ssid", "your-password");', 'WiFi.begin();'):
            self.assertEqual(rules(t), [], t)


class TokenFamilies(unittest.TestCase):
    def test_one_planted_token_per_family(self):
        for t in ('k = "sk-ant-api03-' + 'A1b2' * 11 + '"', 'k = "sk-proj-' + 'A1b2' * 10 + '"',
                  'ghp_' + 'a' * 36, 'gho_' + 'a' * 36, 'ghu_' + 'a' * 36, 'ghs_' + 'a' * 36, 'ghr_' + 'a' * 36,
                  'github_pat_' + 'a' * 30, 'sk-' + 'a' * 40, 'xoxb-1234567890-abcdefghij', 'AKIA' + 'B' * 16, 'ASIA' + 'B' * 16,
                  'key=AIza' + 'a1_-' * 8 + 'abc'):
            self.assertEqual(rules(t), ['token'], t)

    def test_near_misses_stay_unflagged(self):
        for t in ('sk-ant-api03-short', 'sk-proj-abc', 'ghp_' + 'a' * 35, 'ghx_' + 'a' * 36, 'ASIA' + 'B' * 15,
                  'AIza' + 'a' * 34, 'the AIza prefix', 'sk-learn is a library'):
            self.assertEqual(rules(t), [], t)


class MorePaths(unittest.TestCase):
    def test_onedrive_and_escaped_and_slash_forms(self):
        self.assertEqual(rules(r'cd ~/OneDrive/Documents', 'a.sh'), ['user_path'])
        self.assertEqual(rules(r'{"p": "C:\\Users\\someone\\x.stl"}', 'a.json'), ['user_path'])       # as in JSON or a Python literal
        self.assertEqual(rules('p = "C:/Users/someone/x.stl"', 'a.py'), ['user_path'])
        self.assertEqual([f.value for f in L.scan_text('a.py', 'p = "C:/Users/someone/x.stl"')], ['C:/Users/someone'])   # the drive is in the span
        self.assertEqual(rules('ssh /home/pi/robot', 'a.sh'), ['user_path'])
        for t in (r'"C:\\Windows\\System32"', 'C:/Program Files/Tool', 'https://example.com/home/page', 'https://example.com/Users/list'):
            self.assertEqual(rules(t, 'a.md'), [], t)


class MoreRules(unittest.TestCase):
    def test_private_ip_ranges(self):
        self.assertEqual(rules('router 192.168.1.20', 'a.md'), ['private_ip'])
        self.assertEqual(rules('lan 172.16.0.5', 'a.md'), ['private_ip'])
        self.assertEqual(rules('lan 172.31.255.1', 'a.md'), ['private_ip'])
        for t in ('host 172.32.0.5', 'host 172.15.0.5', 'host 192.169.1.1'):
            self.assertEqual(rules(t, 'a.md'), [], t)

    def test_email_safe_list_is_anchored(self):
        self.assertEqual(rules('contact digit@github.com'), ['email'])                       # was safe: 'git@github.com' ends 'digit@github.com'
        self.assertEqual(rules('git@github.com:someone/repo.git', 'config'), [])
        self.assertEqual(rules('someone@example.com'), [])

    def test_image_file_names_are_not_emails(self):
        for t in ('icon@2x.png', '<img src="logo@3x.JPG">', 'hero@2x.webp', 'a@2x.jpeg', 'b@2x.gif', 'c@2x.svg'):
            self.assertEqual(rules(t, 'a.html'), [], t)
        for t in ('a@b.png.com', 'x@gif.com', 'someone@hotmail.com'):                        # controls: real addresses still flagged
            self.assertEqual(rules(t, 'a.html'), ['email'], t)

    def test_line_numbers_match_git(self):                    # git counts '\n' only; splitlines() also splits on \x0c, \u2028, \x85
        t = 'a\x0cb\u2028c\r\nd\x85e\npassword = "Hunter2!x"\r\n'
        self.assertEqual([f.line for f in L.scan_text('x.ino', t)], [3])
        self.assertEqual([f.line for f in L.scan_text('x.ino', 'a\r\npassword = "Hunter2!x"\r\n')], [2])


class LongLines(unittest.TestCase):
    blob = 'Zm9vYmFy' * 300                                  # 2400 chars of base64-like text

    def test_long_line_still_finds_token_and_credential(self):
        line = self.blob + ' ghp_' + 'a' * 36 + ' ' + self.blob + ' password = "Hunter2!x" ' + self.blob
        self.assertGreater(len(line), L.LONG_LINE)
        self.assertEqual(rules(line, 'v.js'), ['credential', 'token'])

    def test_long_line_blanks_the_base64_and_reads_the_rest(self):      # final review, item 4: this was 'skips email and private_ip'
        mid = ' someone@hotmail.com 10.0.0.99 '
        self.assertGreater(len(self.blob + mid + self.blob), L.LONG_LINE)
        self.assertEqual(rules(self.blob + ' ' + self.blob, 'v.js'), [])                  # the base64-blob guard: the blobs alone fire nothing
        self.assertEqual(rules(self.blob + mid + self.blob, 'v.js'), ['email', 'private_ip'])     # the address between them is read now
        self.assertEqual(rules(mid, 'v.js'), ['email', 'private_ip'])     # control: the same text on a short line is flagged


class Pathological(unittest.TestCase):
    def test_long_runs_after_a_keyword_stay_linear(self):     # open-ended [\w-]* and stacked \s* took 30-70 s on these
        t0 = time.time()
        L.scan_text('x', 'password' * 10000)
        L.scan_text('x', 'password:' + ' ' * 20000 + 'x')
        L.scan_text('x', 'WIFI_PASSWORD=' + 'a' * 100000)
        self.assertLess(time.time() - t0, 5)

    def test_wifi_begin_whitespace_stays_linear(self):        # round 2: \s* beside [^,()"] took 7.9 s at 60 000 spaces (quadratic)
        for t in ('WiFi.begin(' + ' ' * 299000 + 'x', 'WiFi.begin(x' + ' ' * 299000, 'WiFi.begin(x(' + 'a' * 299000,
                  'WiFi.begin(' + '(x)' * 99000, 'WiFi.begin(' * 27000):
            self.assertGreater(len(t), 290000)
            t0 = time.time()
            L.scan_text('x.ino', t)
            self.assertLess(time.time() - t0, 1.0, t[:20])

    def test_many_labels_on_one_line_stay_linear(self):       # each skipped label is retried one character on
        t = 'print("password: ", end="")' * 11000
        self.assertGreater(len(t), 290000)
        t0 = time.time()
        self.assertEqual(len(L.scan_text('x.py', t)), 0)
        self.assertLess(time.time() - t0, 2.0)


class Hygiene(unittest.TestCase):
    def test_finding_repr_hides_the_value(self):
        f = L.Finding('credential', 'must', 'x.ino', 3, 'Hunter2!x', 'a note')
        self.assertNotIn('Hunter2', repr(f))
        self.assertIn('x.ino', repr(f))                      # control: the rest of the finding still shows
        self.assertEqual(f.value, 'Hunter2!x')
        self.assertEqual([x.name for x in dataclasses.fields(L.Finding)], ['rule', 'grade', 'path', 'line', 'value', 'note', 'commit'])
        self.assertEqual(f.commit, '')

    def test_redact_fully_masks_short_values(self):
        self.assertEqual(L.redact('abc12'), '… (5 chars)')
        self.assertEqual(L.redact('1234567'), '… (7 chars)')
        self.assertEqual(L.redact('Hunter2!'), 'Hu…! (8 chars)')                            # 8 and up keep first two and last one
        self.assertEqual(L.redact('Hunter2!x'), 'Hu…x (9 chars)')


# Review round 2.
class RoundTwo(unittest.TestCase):
    def values(self, t, path='x.ino'):
        return [f.value for f in L.scan_text(path, t)]

    def test_hash_inside_an_unquoted_env_value(self):          # '#' starts a comment only after whitespace (or at line start)
        for t in ('WIFI_PASSWORD=Hunter#2x', 'WIFI_PASSWORD=Hunter2x#', 'WIFI_PASSWORD=#Hunter2x', 'export WIFI_SSID=home#net  # note'):
            self.assertEqual(rules(t, '.env'), ['credential'], t)
        self.assertEqual(self.values('WIFI_PASSWORD=Hunter#2x', '.env'), ['Hunter#2x'])
        self.assertEqual(self.values('WIFI_PASSWORD=Hunter2x#', '.env'), ['Hunter2x#'])
        self.assertEqual(self.values('WIFI_PASSWORD=Hunter#2x # my note', '.env'), ['Hunter#2x'])
        self.assertEqual(self.values('WIFI_PASSWORD=Hunter2x # comment', '.env'), ['Hunter2x'])     # the comment is not the value
        for t in ('# WIFI_PASSWORD=Hunter2x', '#WIFI_PASSWORD=Hunter#2x', '  # export WIFI_PASSWORD=Hunter2x',
                  'WIFI_PASSWORD= # Hunter2x', 'WIFI_PASSWORD=   #Hunter2x', 'WIFI_PASSWORD=<#>', 'WIFI_PASSWORD='):
            self.assertEqual(rules(t, '.env'), [], t)

    def test_hash_inside_an_unquoted_yaml_value(self):
        for t in ('password: Hunter#2x', 'password: Hunter2x#', '- passwd: Hunter#2x  # prod', 'wifi_password:   Hunter#2x'):
            self.assertEqual(rules(t, 'c.yml'), ['credential'], t)
        self.assertEqual(self.values('password: Hunter#2x', 'c.yml'), ['Hunter#2x'])
        self.assertEqual(self.values('password: Hunter#2x # prod', 'c.yml'), ['Hunter#2x'])
        self.assertEqual(self.values('password: Hunter2x # comment', 'c.yml'), ['Hunter2x'])
        for t in ('# password: Hunter2x', '  # password: Hunter#2x', 'password: # Hunter2x', 'password: #Hunter2x', 'password:  # Hunter2x',
                  'password: Hun{ter#2x}', 'password: [Hunter#2x]'):
            self.assertEqual(rules(t, 'c.yml'), [], t)

    def test_wifi_begin_with_a_nested_call_in_the_first_argument(self):
        for t in ('WiFi.begin(ssid.c_str(), "Fake123x");', 'WiFi.begin( ssid.c_str() , "Fake123x" );', 'WiFi.begin(String(a).c_str(), "Fake123x");',
                  'WiFi.begin(ssid, "Fake123x");', 'WiFi.begin("homenet", "Fake123x");'):
            self.assertEqual(rules(t), ['credential'], t)
            self.assertIn('Fake123x', self.values(t), t)
        for t in ('WiFi.begin(ssid.c_str(), password.c_str());', 'WiFi.begin(ssid.c_str());', 'WiFi.begin(ssid.c_str(), "your-password");',
                  'WiFi.begin(ssid.c_str(), pass(1));', 'WiFi.begin();'):
            self.assertEqual(rules(t), [], t)

    def test_a_label_in_a_string_is_not_a_key(self):
        for t in ('print("Password: ", end="")', "print('Password: ', end='')", 'log("wifi ssid: ", ssid, ", connecting")',
                  'Serial.print("SSID: "); Serial.println("ok")', "print(f'Password: ', end='')", 'print("Enter the user\'s password: ", end="")',
                  'print("a \\" Password: ", end="")'):          # an escaped quote does not close the string
            self.assertEqual(rules(t), [], t)
        for t in ('"wifi_password": "Fake123x"', "'wifi_password': 'Fake123x'", 'password = "Fake123x"', 'password: "Fake123x"',
                  "data = '{\"password\": \"Fake123x\"}'", '{"ssid": "homenet", "password": "Fake123x"}'):
            self.assertEqual(rules(t), ['credential'], t)

    def test_a_value_in_the_other_quote_inside_a_string_is_a_credential(self):    # review round 3: the label check dropped these
        for t in (r'''echo "WIFI_PASSWORD='Fake123x'" >> .env''', r'''f.write("password = 'Fake123x'\n")''',
                  r'''cfg = "[wifi]; ssid = 'homenet'; password = 'Fake123x'"'''):
            self.assertEqual(rules(t), ['credential'], t)

    def test_a_skipped_label_does_not_hide_a_real_credential_after_it(self):
        self.assertEqual(self.values('print("Password: ", password="Fake123x")'), ['Fake123x'])
        self.assertEqual(self.values('Serial.print("SSID: "); ssid = "homenet";'), ['homenet'])
        self.assertEqual(self.values('log("wifi ssid: ", ssid, ", connecting"); password = "Fake123x"'), ['Fake123x'])

    def test_apostrophes_in_prose_do_not_open_a_string(self):  # else the name below counts as inside a string and is skipped
        for t in ("# the user's password = \"Fake123x\"", "# users' ssid = \"homenet\"", "Don't forget: password = \"Fake123x\""):
            self.assertEqual(rules(t, 'a.md'), ['credential'], t)


import io, zipfile
from PIL import Image


def jpeg(gps):
    im = Image.new('RGB', (8, 8)); ex = Image.Exif(); ex[0x010F] = 'Apple'
    if gps:
        ex[0x8825] = {1: 'N', 2: (42.0, 16.0, 30.0), 3: 'W', 4: (83.0, 44.0, 10.0)}
    b = io.BytesIO(); im.save(b, 'JPEG', exif=ex); return b.getvalue()


class Binaries(unittest.TestCase):
    def test_gps_in_a_photo(self):
        self.assertIn('gps', {f.rule for f in L.scan_binary('a.jpg', jpeg(True))})

    def test_photo_without_gps(self):                          # the near-miss: a camera make alone isn't a location
        self.assertNotIn('gps', {f.rule for f in L.scan_binary('a.jpg', jpeg(False))})

    def test_pdf_author(self):
        self.assertEqual({f.rule for f in L.scan_binary('a.pdf', b'%PDF-1.4\n<< /Author (Jane Q Public) /Creator (Word) >>')}, {'doc_author'})
        self.assertEqual(L.scan_binary('b.pdf', b'%PDF-1.4\n<< /Creator (matplotlib) >>'), [])

    def test_step_author(self):
        hdr = b"FILE_NAME('part','2026-01-01',('Jane Q Public'),('Acme Inc'),'x','y','z');"
        self.assertEqual({f.rule for f in L.scan_binary('a.step', hdr)}, {'doc_author'})
        self.assertEqual(L.scan_binary('b.step', b"FILE_NAME('part','2026',('Author'),(''),'x','y','z');"), [])

    def test_text_rules_inside_a_cad_zip(self):
        b = io.BytesIO()
        with zipfile.ZipFile(b, 'w') as z:
            z.writestr('Document.xml', '<Doc CreatedBy="x" path="C:\\Users\\jane\\Desktop\\a.FCStd"/>')
        self.assertIn('user_path', {f.rule for f in L.scan_binary('a.FCStd', b.getvalue())})


# Task 2, review round 1 (scan_binary). Every check has a planted case it must flag and a near-miss it must not.
import struct
from unittest import mock

LEAK = r'<Doc path="C:\Users\jane\Desktop\a.FCStd"/>'       # the cheapest planted leak: a user path


def zipped(members, method=None, flags=None, only=None, compression=zipfile.ZIP_DEFLATED):
    """A zip of {name: text}. method / flags, when given, are patched into the local and central header of entry `only`
    (every entry when only is None): method 93 is zstd, flags 1 is 'encrypted'. Neither is ever decoded by this test."""
    b = io.BytesIO()
    with zipfile.ZipFile(b, 'w', compression) as z:
        for name, text in members.items():
            z.writestr(name, text)
    d = bytearray(b.getvalue())
    for sig, m_off, f_off in ((b'PK\x03\x04', 8, 6), (b'PK\x01\x02', 10, 8)):
        i, n = d.find(sig), 0
        while i >= 0:
            if only is None or only == n:
                if method is not None: d[i + m_off:i + m_off + 2] = struct.pack('<H', method)
                if flags is not None: d[i + f_off:i + f_off + 2] = struct.pack('<H', flags)
            i, n = d.find(sig, i + 4), n + 1
    return bytes(d)


class UnreadableMembers(unittest.TestCase):
    """The repo's own Version_1.1.f3d holds zstd members (zip method 93); Python 3.10's zipfile raises NotImplementedError on them."""
    def test_zstd_members_are_one_finding_not_a_crash(self):
        out = L.scan_binary('a.f3d', zipped({'a.dat': 'x', 'b.dat': 'y', 'c.dat': 'z'}, method=93))
        self.assertEqual([(f.rule, f.grade) for f in out], [('unreadable', 'decide')])          # ONE for the archive
        self.assertIn('3 members', out[0].note)
        self.assertIn('zstd', out[0].note)
        self.assertEqual(L.scan_binary('a.f3d', zipped({'a.dat': 'x', 'b.dat': 'y', 'c.dat': 'z'})), [])   # control: readable and clean

    def test_readable_members_are_still_scanned(self):
        d = zipped({'a.dat': 'x', 'Document.xml': LEAK}, method=93, only=0)
        self.assertEqual(sorted(f.rule for f in L.scan_binary('a.f3d', d)), ['unreadable', 'user_path'])
        self.assertEqual(sorted(f.rule for f in L.scan_binary('a.f3d', zipped({'a.dat': 'x', 'Document.xml': LEAK}))), ['user_path'])

    def test_encrypted_member(self):
        out = L.scan_binary('a.docx', zipped({'word/document.xml': 'x'}, flags=1))
        self.assertEqual([(f.rule, f.grade) for f in out], [('unreadable', 'decide')])
        self.assertIn('1 member is encrypted', out[0].note)

    def test_damaged_member(self):                           # a flipped byte in a stored member: the CRC no longer matches
        d = zipped({'a.xml': 'hello world'}, compression=zipfile.ZIP_STORED).replace(b'hello', b'jello')
        out = L.scan_binary('a.3mf', d)
        self.assertEqual([(f.rule, f.grade) for f in out], [('unreadable', 'decide')])
        self.assertIn('damaged', out[0].note)

    def test_corrupt_or_truncated_archive(self):
        whole = zipped({'a.xml': 'x'})
        for bad in (b'PK\x03\x04garbage', whole[:-30], b''):
            out = L.scan_binary('a.fcstd', bad)
            self.assertEqual([(f.rule, f.grade) for f in out], [('unreadable', 'decide')], bad[:8])
        self.assertEqual(L.scan_binary('a.fcstd', whole), [])                                       # control: the whole archive is fine


class StepHeaders(unittest.TestCase):
    """STEP FILE_NAME: real OCC / Fusion / other writers differ in whitespace, comments and line breaks."""
    def authors(self, header):
        return sorted(f.value for f in L.scan_binary('a.step', header) if f.rule == 'doc_author')

    def test_opencascade_header_with_the_organisation_on_a_new_line(self):    # 9 of the repo's 13 STEP files
        occ = (b"ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION(('Open CASCADE Model'),'2;1');\n"
               b"FILE_NAME('Open CASCADE Shape Model','2026-01-01T00:00:00',('Author'),(\n    'Open CASCADE'),"
               b"'Open CASCADE STEP processor 7.7','Open CASCADE 7.7','Unknown');\nFILE_SCHEMA(('AUTOMOTIVE_DESIGN'));\nENDSEC;\nDATA;\nENDSEC;\n")
        self.assertEqual(L.scan_binary('a.step', occ), [])
        self.assertEqual(self.authors(occ.replace(b"'Open CASCADE'),", b"'Acme Inc'),")), ['Acme Inc'])   # control: the new-line field is read
        self.assertEqual(L.scan_binary('a.step', occ.replace(b"'Open CASCADE'),", b"'OPEN  CASCADE'),")), [])  # case and inner spaces do not matter

    def test_fusion_comments_between_the_fields(self):
        fusion = (b"FILE_NAME(\r\n/* name */ 'part.step',\r\n/* time_stamp */ '2026-01-01T00:00:00',\r\n/* author */ ('Jane Q Public'),\r\n"
                  b"/* organization */ ('Acme Inc'),\r\n/* preprocessor_version */ 'x',\r\n/* originating_system */ 'y',\r\n/* authorisation */ '');")
        self.assertEqual(self.authors(fusion), ['Acme Inc', 'Jane Q Public'])
        blank = fusion.replace(b"'Jane Q Public'", b"''").replace(b"'Acme Inc'", b"''")
        self.assertEqual(L.scan_binary('a.step', blank), [])                           # near-miss: the same shape, no names
        odd = fusion.replace(b"/* author */", b"/* it's (the) author, ('Bob') */")      # quotes and brackets inside a comment are not fields
        self.assertEqual(self.authors(odd), ['Acme Inc', 'Jane Q Public'])

    def test_spaces_after_commas_and_several_names_in_a_list(self):
        spaced = b"FILE_NAME( 'part' , '2026' , ( 'Jane Q Public' , 'John R Doe' ) , ( 'Acme Inc' ) , 'x' , 'y' , 'z' );"
        self.assertEqual(self.authors(spaced), ['Acme Inc', 'Jane Q Public', 'John R Doe'])
        self.assertEqual(L.scan_binary('a.step', spaced.replace(b"'Jane Q Public'", b"'Author'").replace(b"'John R Doe'", b"''")
                                       .replace(b"'Acme Inc'", b"$")), [])             # near-miss: placeholders and an unset ($) field

    def test_the_header_goes_through_the_text_rules(self):
        path = rb"FILE_NAME('C:\\Users\\jane\\Desktop\\a.step','2026',('Author'),('Open CASCADE'),'x','y','z');"
        self.assertEqual({f.rule for f in L.scan_binary('a.step', path)}, {'user_path'})
        self.assertEqual({f.rule for f in L.scan_binary('a.step', path.replace(rb'\\', b'\\'))}, {'user_path'})     # a single-backslash writer
        self.assertEqual(L.scan_binary('a.step', path.replace(rb'C:\\Users\\jane\\Desktop\\a.step', b'a.step')), [])     # near-miss: a bare name
        mail = b"HEADER;\nFILE_DESCRIPTION(('mail jane@hotmail.com'),'2;1');\nENDSEC;\n"
        self.assertEqual({f.rule for f in L.scan_binary('a.step', mail)}, {'email'})
        self.assertEqual(L.scan_binary('a.step', mail.replace(b'jane@hotmail.com', b'jane@example.com')), [])

    def test_only_the_header_is_scanned(self):                     # DATA holds product names; a path there is not the header's business
        t = b"HEADER;\nFILE_NAME('a','2026',('Author'),('Open CASCADE'),'x','y','z');\nENDSEC;\nDATA;\n#1=PRODUCT('" + rb"C:\\Users\\jane\\x" + b"');\nENDSEC;\n"
        self.assertEqual(L.scan_binary('a.step', t), [])

    def test_stray_quotes_brackets_and_comments_stay_linear(self):      # the walk is hand-written; a regex tokenizer backtracks on these
        for body in (b"'" * 400000, b"/*" * 200000, b"('" * 200000, b"(" * 400000, b"/* ' " * 80000):
            t0 = time.time()
            L.scan_binary('a.step', b"FILE_NAME(" + body + b"ENDSEC;")
            self.assertLess(time.time() - t0, 2.0, body[:6])


class UnreadableImages(unittest.TestCase):
    """A photo the scan cannot open is a photo it cannot vouch for: HEIC without a plugin, corrupt bytes, no Pillow at all."""
    def pairs(self, findings):
        return [(f.rule, f.grade) for f in findings]

    def test_corrupt_bytes_named_jpg(self):
        self.assertEqual(self.pairs(L.scan_binary('a.jpg', b'this is not a picture')), [('unreadable', 'decide')])
        self.assertEqual(self.pairs(L.scan_binary('a.png', jpeg(True)[:40])), [('unreadable', 'decide')])      # truncated
        self.assertEqual(L.scan_binary('a.jpg', jpeg(False)), [])                                              # control: a good photo is read

    def test_heic_that_pillow_cannot_open(self):
        heic = b'\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic' + bytes(64)
        self.assertEqual(self.pairs(L.scan_binary('a.heic', heic)), [('unreadable', 'decide')])

    def test_pillow_not_importable(self):
        photo = jpeg(True)                                                 # made before the patch: saving needs Pillow too
        with mock.patch.dict(sys.modules, {'PIL': None}):                  # `from PIL import Image` now raises ImportError
            out = L.scan_binary('a.jpg', photo)
        self.assertEqual(self.pairs(out), [('unreadable', 'decide')])
        self.assertIn('gps', {f.rule for f in L.scan_binary('a.jpg', jpeg(True))})                             # control: with Pillow back, the GPS shows


class MemberCap(unittest.TestCase):
    """The tracked .fcstd's Document.xml is 7.1 MB and holds CreatedBy, LastModifiedBy and Company: a 2 MB cap skipped it unseen."""
    def test_a_leak_after_2_5_mb_is_found(self):
        pad = ('x' * 999 + '\n') * 2600                                  # 2.6 MB of short lines
        out = L.scan_binary('a.fcstd', zipped({'Document.xml': pad + LEAK}))
        self.assertEqual([(f.rule, f.line) for f in out], [('user_path', 2601)])
        self.assertEqual(L.scan_binary('a.fcstd', zipped({'Document.xml': pad})), [])           # near-miss: the same size, no leak
        self.assertEqual(L.MEMBER_CAP, 64 * 1024 * 1024)

    def test_a_member_over_the_cap_is_reported_by_name(self):
        with mock.patch.object(L, 'MEMBER_CAP', 1000):
            out = L.scan_binary('a.fcstd', zipped({'Big.xml': LEAK * 40, 'small.xml': LEAK}))     # 1.9 KB against a 1000-byte cap
        self.assertEqual(sorted(f.rule for f in out), ['unreadable', 'user_path'])
        self.assertEqual([f.path for f in out if f.rule == 'user_path'], ['a.fcstd!small.xml'])    # the small member is still read
        [gap] = [f for f in out if f.rule == 'unreadable']
        self.assertEqual(gap.grade, 'decide')
        self.assertIn('Big.xml', gap.note)
        self.assertNotIn('small.xml', gap.note)

    def test_a_member_at_the_cap_is_still_scanned(self):          # near-miss: the limit is 'over', not 'at'
        member = LEAK + ' ' * 100
        with mock.patch.object(L, 'MEMBER_CAP', len(member)):
            out = L.scan_binary('a.fcstd', zipped({'Big.xml': member}))
        self.assertEqual([f.rule for f in out], ['user_path'])


class ZipAuthors(unittest.TestCase):
    """Who made the file: 3MF Designer, docx creator and last editor, FreeCAD CreatedBy / LastModifiedBy / Company."""
    def found(self, path, members):
        return sorted((f.path.split('!')[-1], f.value) for f in L.scan_binary(path, zipped(members)) if f.rule == 'doc_author')

    def fc(self, created='', modified='', company=''):               # the shape FreeCAD writes into Document.xml
        prop = '        <Property name="%s" type="App::PropertyString">\n            <String value="%s"/>\n        </Property>\n'
        return ('<?xml version="1.0" encoding="utf-8"?>\n<Document SchemaVersion="4">\n    <Properties Count="5">\n'
                + prop % ('Label', 'Bracket') + prop % ('Company', company) + prop % ('CreatedBy', created)
                + prop % ('Comment', 'Jane Q Public made this') + prop % ('LastModifiedBy', modified) + '    </Properties>\n</Document>\n')

    def test_3mf_designer(self):
        model = '<model><metadata name="Designer">%s</metadata><metadata name="Title">Jane Q Public bracket</metadata></model>'
        self.assertEqual(self.found('a.3mf', {'3D/3dmodel.model': model % 'Jane Q Public'}), [('3D/3dmodel.model', 'Jane Q Public')])
        self.assertEqual(self.found('a.3mf', {'3D/3dmodel.model': model % 'Jane &amp; Co'}), [('3D/3dmodel.model', 'Jane & Co')])
        for placeholder in ('', 'Unknown', ' Author '):                       # near-misses: placeholders; and Title is not a name field
            self.assertEqual(self.found('a.3mf', {'3D/3dmodel.model': model % placeholder}), [], placeholder)
        self.assertEqual(self.found('a.3mf', {'3D/3dmodel.model': '<model><metadata name="Designer"/><metadata name="Title">Bracket</metadata></model>'}), [])

    def test_docx_creator_and_last_editor(self):
        core = ('<cp:coreProperties xmlns:cp="c" xmlns:dc="d"><dc:title>Jane Q Public notes</dc:title><dc:creator>%s</dc:creator>'
                '<cp:lastModifiedBy>%s</cp:lastModifiedBy></cp:coreProperties>')
        self.assertEqual(self.found('a.docx', {'docProps/core.xml': core % ('Jane Q Public', 'John R Doe')}),
                         [('docProps/core.xml', 'Jane Q Public'), ('docProps/core.xml', 'John R Doe')])
        self.assertEqual(self.found('a.docx', {'docProps/core.xml': core % ('Unknown', '')}), [])               # near-miss: placeholders
        self.assertEqual(self.found('a.docx', {'word/document.xml': core % ('Jane Q Public', 'John R Doe')}), [])   # core.xml only

    def test_freecad_document_properties(self):
        self.assertEqual(self.found('a.FCStd', {'Document.xml': self.fc('Jane Q Public', 'John R Doe', 'Acme Inc')}),
                         [('Document.xml', 'Acme Inc'), ('Document.xml', 'Jane Q Public'), ('Document.xml', 'John R Doe')])
        notes = {f.note for f in L.scan_binary('a.FCStd', zipped({'Document.xml': self.fc('Jane Q Public', 'John R Doe', 'Acme Inc')}))}
        self.assertEqual(notes, {'FCStd CreatedBy', 'FCStd LastModifiedBy', 'FCStd Company'})
        self.assertEqual(self.found('a.FCStd', {'Document.xml': self.fc('', 'Unknown', '')}), [])            # near-miss: placeholders,
        self.assertEqual(self.found('a.FCStd', {'Document.xml': self.fc()}), [])                                # and a name in Comment is not read
        self.assertEqual(self.found('a.FCStd', {'word/document.xml': self.fc('Jane Q Public')}), [])           # Document.xml at the root only


import contextlib, re, shutil, stat, subprocess, tempfile


def git(repo, *a, env=None):
    return subprocess.run(['git', '-C', repo, *a], check=True, capture_output=True, text=True, encoding='utf-8',
                          env=None if env is None else {**os.environ, **env}).stdout


def rmtree(path):
    """shutil.rmtree that also removes read-only files (git's object files are read-only on Windows)"""
    def writable(func, p, _):
        os.chmod(p, stat.S_IWRITE); func(p)
    shutil.rmtree(path, onerror=writable)


class History(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(); self.addCleanup(rmtree, self.d)       # cleaned up even when a test fails
        git(self.d, 'init', '-q')                                           # the config below is local to this temp repo only
        git(self.d, 'config', 'user.email', 'someone@hotmail.com'); git(self.d, 'config', 'user.name', 'T')
        git(self.d, 'config', 'commit.gpgsign', 'false')
        with open(os.path.join(self.d, 'wifi.ino'), 'w') as fh:
            fh.write('const char *password = "Hunter2!x";\n')
        git(self.d, 'add', '.'); git(self.d, 'commit', '-q', '-m', 'add')
        os.remove(os.path.join(self.d, 'wifi.ino'))
        with open(os.path.join(self.d, 'ok.md'), 'w') as fh:
            fh.write('nothing\n')
        git(self.d, 'add', '-A'); git(self.d, 'commit', '-q', '-m', 'remove')

    def test_head_is_clean_but_history_is_not(self):            # the control: deleting a file doesn't remove it
        self.assertEqual([f for f in L.scan_repo(self.d, 'head') if f.rule == 'credential'], [])
        hist = [f for f in L.scan_repo(self.d, 'history') if f.rule == 'credential']
        self.assertEqual(len(hist), 1); self.assertEqual(hist[0].path, 'wifi.ino'); self.assertTrue(hist[0].commit)

    def test_commit_author_emails(self):
        self.assertIn('author_email', {f.rule for f in L.scan_repo(self.d, 'history')})

    def test_allowlist_and_report_redact(self):
        f = L.Finding('credential', 'must', 'wifi.ino', 1, 'Hunter2!x', 'n')
        self.assertTrue(L.allowed(f, ['credential wifi.*'])); self.assertFalse(L.allowed(f, ['email wifi.*']))
        self.assertTrue(L.allowed(f, ['* wifi.*  # every rule, this file']))
        self.assertNotIn('Hunter2', L.report([f]))


# Task 3, review round 1. Every value below is made up; each check has a control beside it.
MODES = ('head', 'staged', 'history')
SECRET = 'const char *password = "Hunter2!x";\n'
PDF = b'%PDF-1.4\n<< /Author (Jane Q Public) /Creator (Word) >>'


def make_repo(test):
    d = tempfile.mkdtemp(); test.addCleanup(rmtree, d)
    git(d, 'init', '-q')                                                    # config is local to this temp repo only
    for k, v in (('user.email', 'someone@hotmail.com'), ('user.name', 'T'), ('commit.gpgsign', 'false')):
        git(d, 'config', k, v)
    return d


def write(d, name, content):
    p = os.path.join(d, *name.split('/')); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'wb') as fh:
        fh.write(content if isinstance(content, bytes) else content.encode('utf-8'))


def commit(d, files=None, delete=(), env=None):
    for name, content in (files or {}).items():
        write(d, name, content)
    for name in delete:
        os.remove(os.path.join(d, *name.split('/')))
    git(d, 'add', '-A'); git(d, 'commit', '-q', '-m', 'c', env=env)
    return git(d, 'rev-parse', 'HEAD').strip()


def repo_with(test, files, mode):
    """a temp repo whose `mode` scan sees `files`: committed for head and history, only staged for staged"""
    d = make_repo(test)
    if mode == 'staged':
        for name, content in files.items():
            write(d, name, content)
        git(d, 'add', '-A')
    else:
        commit(d, files)
    return d


def make_folder(test, files):
    d = tempfile.mkdtemp(); test.addCleanup(rmtree, d)
    for name, content in files.items():
        write(d, name, content)
    return d


def scan(test, files, mode):
    """findings for `files` seen through `mode`: 'folder' or one of MODES"""
    if mode == 'folder':
        return L.scan_folder(make_folder(test, files))
    return L.scan_repo(repo_with(test, files, mode), mode)


def run_main(test, argv, allow=None, root=None):
    """(exit code, stdout text) of main(argv), with the allowlist replaced by `allow` (bytes; none when None)"""
    ad = tempfile.mkdtemp(); test.addCleanup(rmtree, ad)
    p = os.path.join(ad, 'allow.txt')
    if allow is not None:
        write(ad, 'allow.txt', allow)
    out = io.StringIO()
    with contextlib.ExitStack() as st:
        st.enter_context(mock.patch.object(L, 'ALLOW', p)); st.enter_context(contextlib.redirect_stdout(out))
        if root:
            st.enter_context(mock.patch.object(L, 'ROOT', root))
        code = L.main(argv)
    return code, out.getvalue()


class FirstCommit(unittest.TestCase):
    """The report names the commit that FIRST had a value; a later commit holding the same value must not take its place."""
    def creds(self, d):
        return [f for f in L.scan_repo(d, 'history') if f.rule == 'credential']

    def test_a_secret_kept_through_a_later_edit_is_dated_to_its_first_commit(self):
        d = make_repo(self)
        a = commit(d, {'wifi.ino': SECRET + 'int n = 1;\n'})
        b = commit(d, {'wifi.ino': SECRET + 'int n = 2;\n'})           # a new blob, the same secret
        c = commit(d, {'notes.txt': 'x\n'})                             # a later commit that keeps both in history
        found = self.creds(d)
        self.assertEqual([f.commit for f in found], [a[:10], b[:10]])   # control: both blobs reported, oldest first
        [row] = L.dedupe(found)
        self.assertEqual(row['f'].commit, a[:10])
        text = L.report(found)
        self.assertIn(a[:10], text); self.assertNotIn(b[:10], text); self.assertNotIn(c[:10], text)

    def test_the_same_blob_added_again_later_keeps_its_first_commit(self):
        d = make_repo(self)
        a = commit(d, {'wifi.ino': SECRET})
        commit(d, {'ok.md': 'x\n'}, delete=['wifi.ino'])
        c = commit(d, {'wifi.ino': SECRET})                              # the very same blob, back again
        [row] = L.dedupe(self.creds(d))
        self.assertEqual((row['f'].commit, row['n']), (a[:10], 1))
        self.assertNotEqual(a, c)

    def test_commit_dates_out_of_order_do_not_change_the_order(self):
        d = make_repo(self)
        at = lambda year: {'GIT_AUTHOR_DATE': f'{year}-01-01T00:00:00', 'GIT_COMMITTER_DATE': f'{year}-01-01T00:00:00'}
        a = commit(d, {'wifi.ino': SECRET}, env=at(2020))
        git(d, 'checkout', '-q', '-b', 'side-x')
        b = commit(d, {'copy.ino': SECRET}, env=at(2010))               # a child that is older than its parent
        git(d, 'checkout', '-q', a); git(d, 'checkout', '-q', '-b', 'side-y')
        commit(d, {'other.txt': 'x\n'}, env=at(2015))
        order = git(d, 'log', '--all', '--reverse', '--format=%H').split()
        self.assertLess(order.index(b), order.index(a))                  # control: git's default order puts the child first
        [row] = L.dedupe(self.creds(d))
        self.assertEqual(row['f'].commit, a[:10])

    def test_a_secret_that_only_a_merge_commit_has(self):                # `git log` shows a merge's changes only with -m
        d = make_repo(self)
        commit(d, {'a.txt': 'base\n'}); trunk = git(d, 'rev-parse', '--abbrev-ref', 'HEAD').strip()
        git(d, 'checkout', '-q', '-b', 'side'); commit(d, {'a.txt': 'side\n'})
        git(d, 'checkout', '-q', trunk); commit(d, {'a.txt': 'trunk\n'})
        subprocess.run(['git', '-C', d, 'merge', '-q', 'side'], capture_output=True)       # conflicts, by design
        write(d, 'a.txt', SECRET); git(d, 'add', 'a.txt'); git(d, 'commit', '-q', '-m', 'merge')
        merge = git(d, 'rev-parse', 'HEAD').strip()
        self.assertEqual(len(git(d, 'rev-list', '--parents', '-n1', merge).split()), 3)    # control: it is a merge, with two parents
        [row] = L.dedupe(self.creds(d))
        self.assertEqual(row['f'].commit, merge[:10])

    def test_author_emails_are_dated_to_the_first_commit_and_noreply_is_not_flagged(self):
        d = make_repo(self)
        git(d, 'config', 'user.email', '123+someone@users.noreply.github.com')
        commit(d, {'a.txt': '1\n'})
        git(d, 'config', 'user.email', 'someone@hotmail.com')
        first = commit(d, {'b.txt': '2\n'}); commit(d, {'c.txt': '3\n'})
        mails = [f for f in L.scan_repo(d, 'history') if f.rule == 'author_email']
        self.assertEqual([f.value for f in mails], ['someone@hotmail.com'] * 2)     # the noreply commit is skipped; the personal ones are not
        [row] = L.dedupe(mails)
        self.assertEqual((row['f'].commit, row['n']), (first[:10], 2))


class Sources(unittest.TestCase):
    def test_non_ascii_paths_are_read_unquoted(self):                    # without -z git writes "caf\303\251.pdf"
        files = {'café.pdf': PDF, 'données/note.ino': SECRET, 'plain.pdf': PDF}
        for mode in ('folder',) + MODES:
            with self.subTest(mode=mode):
                got = {(f.rule, f.path) for f in scan(self, files, mode)}
                self.assertIn(('doc_author', 'café.pdf'), got)
                self.assertIn(('credential', 'données/note.ino'), got)
                self.assertIn(('doc_author', 'plain.pdf'), got)           # control: the ASCII name behaves the same
                self.assertFalse([p for _, p in got if p.startswith('"') or '\\' in p])

    def test_oversized_files_are_reported_not_skipped(self):
        files = {'models/big.f3d': 'x' * 150, 'big.stl': 'y' * 101, 'edge.txt': 'z' * 100, 'small.txt': 'w' * 5}
        with mock.patch.object(L, 'MAX_BLOB', 100):
            for mode in ('folder',) + MODES:
                with self.subTest(mode=mode):
                    gaps = [f for f in scan(self, files, mode) if f.rule == 'unreadable']
                    self.assertEqual(sorted((f.grade, f.path) for f in gaps), [('decide', 'big.stl'), ('decide', 'models/big.f3d')])
                    self.assertIn('unscanned', gaps[0].note)             # at the limit (edge.txt) and under it are read, not reported
        by_path = {f.path: f for f in gaps}
        self.assertTrue(L.allowed(by_path['models/big.f3d'], ['unreadable *.f3d  # Fusion archives']))
        self.assertFalse(L.allowed(by_path['big.stl'], ['unreadable *.f3d']))      # control: the allowlist covers .f3d only
        self.assertEqual([f for f in scan(self, files, 'head') if 'over' in f.note], [])            # control: under the real limit no file is 'over'

    def test_a_gitlink_in_the_tree_is_not_a_blob(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                d = make_repo(self)
                write(d, 'wifi.ino', SECRET); git(d, 'add', 'wifi.ino')
                git(d, 'update-index', '--add', '--cacheinfo', '160000,' + '1234567890abcdef1234567890abcdef12345678,vendor/sub')
                if mode != 'staged':
                    git(d, 'commit', '-q', '-m', 'c')
                got = L.scan_repo(d, mode)
                self.assertEqual([f.path for f in got if f.rule in ('credential', 'unreadable')], ['wifi.ino'])     # no crash, no row for the gitlink

    def test_an_object_that_is_not_there_is_a_gap_not_a_crash(self):
        d = make_repo(self)
        commit(d, {'wifi.ino': SECRET, 'ok.txt': 'fine\n'})
        sha = git(d, 'rev-parse', 'HEAD:wifi.ino').strip()
        loose = os.path.join(d, '.git', 'objects', sha[:2], sha[2:])
        os.chmod(loose, stat.S_IWRITE); os.remove(loose)
        for mode in ('head', 'history'):
            with self.subTest(mode=mode):
                got = [(f.rule, f.path) for f in L.scan_repo(d, mode) if f.rule in ('credential', 'unreadable')]
                self.assertEqual(got, [('unreadable', 'wifi.ino')])

    def test_git_is_launched_a_few_times_not_once_per_blob(self):
        files = {f'f{i}.txt': f'n{i}\n' for i in range(40)}
        for mode in MODES:
            with self.subTest(mode=mode):
                d = repo_with(self, files, mode)
                with mock.patch.object(subprocess, 'Popen', wraps=subprocess.Popen) as popen:
                    found = L.scan_repo(d, mode)
                self.assertGreaterEqual(popen.call_count, 2)                      # control: the counter sees the launches
                self.assertLessEqual(popen.call_count, 8)
                self.assertEqual([f.rule for f in found if f.rule != 'author_email'], [])

    def test_scan_folder_finds_a_planted_file_and_skips_dot_git(self):
        d = tempfile.mkdtemp(); self.addCleanup(rmtree, d)
        write(d, 'sub/dir/wifi.ino', SECRET); write(d, '.git/hidden.ino', SECRET); write(d, 'clean.txt', 'nothing\n')
        got = [(f.rule, f.path) for f in L.scan_folder(d)]
        self.assertEqual(got, [('credential', 'sub/dir/wifi.ino')])               # the planted file, with '/' paths; .git is not read

    def test_unknown_mode_is_an_error(self):
        d = make_repo(self); commit(d, {'a.txt': 'x\n'})
        for mode in ('histroy', 'HEAD', ''):
            with self.assertRaises(ValueError):
                L.scan_repo(d, mode)
        self.assertIsInstance(L.scan_repo(d, 'head'), list)                       # control: a real mode still works

    def test_utf16_text_is_decoded_but_other_binaries_are_still_skipped(self):
        for enc in ('utf-16', 'utf-16-be'):
            data = (b'\xff\xfe' if enc == 'utf-16' else b'\xfe\xff') + SECRET.encode('utf-16-le' if enc == 'utf-16' else 'utf-16-be')
            self.assertEqual([f.rule for f in L._scan_bytes('wifi.ino', data)], ['credential'], enc)
        self.assertEqual(L._scan_bytes('wifi.ino', SECRET.encode('utf-16-le')), [])        # no BOM: left alone, as any binary
        self.assertEqual(L._scan_bytes('mesh.bin', b'\x00\x01' + SECRET.encode()), [])      # control: a binary stays skipped
        self.assertEqual([f.rule for f in L._scan_bytes('wifi.ino', SECRET.encode())], ['credential'])

    def test_obj_mesh_lines_are_blanked_but_line_numbers_stay(self):
        obj = ('# exported from C:\\Users\\jane\\Desktop\\a.f3d\nmtllib C:\\Users\\jane\\m.mtl\nv 10.1.2.3 0.5 -1e-3\nvt 0.1 0.2\n'
               'vn 0 0 1\nf 1/1/1 2/2/2 3/3/3\r\no part\n# see someone@hotmail.com\nv someone@hotmail.com\n').encode()
        got = [(f.rule, f.line) for f in L._scan_bytes('part.OBJ', obj)]
        self.assertEqual(got, [('user_path', 1), ('user_path', 2), ('email', 8), ('email', 9)])   # numbers blanked; comments, mtllib and odd 'v' lines read
        control = [(f.rule, f.line) for f in L._scan_bytes('part.txt', obj)]
        self.assertIn(('private_ip', 3), control)                                  # control: the same text in a .txt is read, mesh line and all


class StagedMode(unittest.TestCase):
    def creds(self, d, mode='staged'):
        return [f.path for f in L.scan_repo(d, mode) if f.rule == 'credential']

    def test_only_what_is_newly_staged(self):
        d = make_repo(self)
        commit(d, {'old.ino': SECRET, 'ok.txt': 'fine\n'})                          # committed: not the pre-commit hook's business
        write(d, 'new.ino', 'const char *password = "Fake456y";\n'); git(d, 'add', 'new.ino')
        write(d, 'loose.ino', SECRET)                                               # in the work tree but not staged
        self.assertEqual(self.creds(d), ['new.ino'])
        self.assertEqual(self.creds(d, 'head'), ['old.ino'])                        # control: HEAD mode sees the committed one, not the staged one

    def test_a_modified_file_is_scanned_and_a_deletion_is_not(self):
        d = make_repo(self)
        commit(d, {'old.ino': SECRET, 'ok.txt': 'fine\n'})
        git(d, 'rm', '-q', 'old.ino')                                               # a staged deletion
        self.assertEqual(self.creds(d), [])
        write(d, 'ok.txt', 'password = "Fake456y"\n'); git(d, 'add', 'ok.txt')      # control: a staged edit that adds a secret is found
        self.assertEqual(self.creds(d), ['ok.txt'])

    def test_a_first_commit_in_a_fresh_repo(self):
        d = make_repo(self)
        self.assertEqual(L.scan_repo(d, 'staged'), [])                               # nothing staged, no HEAD yet
        write(d, 'wifi.ino', SECRET); git(d, 'add', 'wifi.ino')
        self.assertEqual(self.creds(d), ['wifi.ino'])
        self.assertEqual(L.scan_repo(d, 'head'), [])                                 # control: HEAD does not exist yet, and that is not an error

    def test_a_staged_rename_keeps_the_pairs_aligned(self):     # --no-renames: a rename is one record with two paths; without it the pairs shift
        d = make_repo(self)
        commit(d, {'old.ino': 'const char *password = "Fake456y";\n'})             # the original, planted before its first commit
        git(d, 'mv', 'old.ino', 'renamed.ino')                                      # staged: the same blob, now under a new name
        write(d, 'new.ino', 'const char *password = "Fake123x";\n'); git(d, 'add', 'new.ino')
        self.assertEqual(sorted(self.creds(d)), ['new.ino', 'renamed.ino'])          # the new file, and the renamed one as added at its new path
        commit(d)
        hist = self.creds(d, 'history')
        self.assertIn('renamed.ino', hist)                                           # history reports the renamed path too
        self.assertIn('new.ino', hist)


class Cli(unittest.TestCase):
    def test_exit_code_follows_the_unallowed_musts(self):
        d = make_folder(self, {'wifi.ino': SECRET})
        self.assertEqual(run_main(self, ['--path', d])[0], 1)
        self.assertEqual(run_main(self, ['--path', d], allow=b'credential wifi.ino\n')[0], 0)
        self.assertEqual(run_main(self, ['--path', d], allow=b'credential other.ino\n')[0], 1)      # control: a glob that misses allows nothing
        self.assertEqual(run_main(self, ['--path', make_folder(self, {'ok.txt': 'fine\n'})])[0], 0)       # control: a clean folder passes

    def test_strict_fails_on_a_decide_only_scan(self):
        d = make_folder(self, {'notes.md': 'router 192.168.1.20\n'})
        self.assertEqual(run_main(self, ['--path', d])[0], 0)
        self.assertEqual(run_main(self, ['--path', d, '--strict'])[0], 1)
        self.assertEqual(run_main(self, ['--path', d, '--strict'], allow=b'private_ip notes.md\n')[0], 0)   # control: allowed, so it passes

    def test_report_is_written_into_a_new_folder(self):
        d = make_folder(self, {'wifi.ino': SECRET}); spare = make_folder(self, {})
        out = os.path.join(spare, 'new', 'sub', 'report.md')
        code, text = run_main(self, ['--path', d, '--report', out])
        self.assertEqual(code, 1)
        with open(out, encoding='utf-8') as fh:
            body = fh.read()
        self.assertIn('| must | credential |', body)
        self.assertNotIn('Hunter2', body + text)
        run_main(self, ['--path', d])                                                  # control: without --report nothing is written
        self.assertEqual(os.listdir(spare), ['new'])

    def test_report_keeps_a_finding_the_glob_does_not_cover(self):
        d = make_folder(self, {'planted/a.ino': SECRET, 'elsewhere/b.ino': SECRET})
        code, text = run_main(self, ['--path', d], allow=b'* planted/*.ino   # the planted one\n')
        self.assertEqual(code, 1)                                                    # the finding outside the glob still blocks
        self.assertIn('elsewhere/b.ino', text); self.assertNotIn('planted/a.ino', text)
        self.assertIn('2 findings, 1 allowed, 1 blocking', text)
        code, text = run_main(self, ['--path', d], allow=b'* *.ino\n')               # control: a glob that covers both leaves a header only
        self.assertEqual(code, 0); self.assertIn('2 findings, 2 allowed, 0 blocking', text); self.assertNotIn('b.ino', text)

    def test_report_has_a_row_per_finding(self):
        f = L.Finding('credential', 'must', 'wifi.ino', 1, 'Hunter2!x', 'n')
        self.assertEqual(len(L.report([f]).splitlines()), 3)                          # header, rule line, one row
        self.assertEqual(len(L.report([]).splitlines()), 2)                           # control: nothing found, no rows

    def test_a_row_names_every_path_it_covers(self):             # round 2: the 4-path cap hid the Wi-Fi strings and the user name
        found = [L.Finding('credential', 'must', f'dir{i}/wifi.ino', 1, 'Hunter2!x', 'n') for i in range(6)]
        text = L.report(found)
        self.assertEqual(len(text.splitlines()), 3)                                   # the six share one value: header, rule line, one row
        self.assertNotIn('more)', text)
        for i in range(6): self.assertIn(f'dir{i}/wifi.ino', text)                    # every path is named, the fifth and sixth included

    def test_the_mode_flags_pick_the_source(self):
        d = make_repo(self)
        commit(d, {'old.ino': SECRET}); commit(d, {'ok.txt': 'x\n'}, delete=['old.ino'])       # a secret that only history has
        self.assertEqual(run_main(self, [], root=d)[0], 0)                            # HEAD is clean
        self.assertEqual(run_main(self, ['--history'], root=d)[0], 1)
        write(d, 'new.ino', SECRET); git(d, 'add', 'new.ino')                         # a secret that only the index has
        self.assertEqual(run_main(self, ['--staged'], root=d)[0], 1)
        git(d, 'reset', '-q', 'new.ino')
        self.assertEqual(run_main(self, ['--staged'], root=d)[0], 0)                  # control: nothing staged, nothing found

    def test_a_non_ascii_path_prints_on_a_cp1252_console(self):
        d = make_folder(self, {'日本/wifi.ino': SECRET}); ad = make_folder(self, {})
        raw = io.BytesIO(); console = io.TextIOWrapper(raw, encoding='cp1252', errors='strict', newline='')
        with mock.patch.object(sys, 'stdout', console), mock.patch.object(L, 'ALLOW', os.path.join(ad, 'none.txt')):
            code = L.main(['--path', d])
        console.flush()
        self.assertEqual(code, 1)
        self.assertIn('日本/wifi.ino'.encode('utf-8'), raw.getvalue())
        self.assertIn(b'1 blocking', raw.getvalue())

    def test_a_missing_or_empty_path_is_an_error_not_a_clean_scan(self):    # --path fails open: a missing folder read as clean, '' scanned HEAD
        d = make_repo(self); commit(d, {'wifi.ino': SECRET})                    # HEAD holds a secret: a HEAD scan would find it
        missing = os.path.join(make_folder(self, {}), 'gone')                    # its parent exists, the folder itself does not
        for arg in (missing, ''):
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = run_main(self, ['--path', arg], root=d)[0]
            self.assertEqual(code, 2, repr(arg))
            self.assertIn('is not a folder', err.getvalue())                     # the error says why, on stderr
        self.assertEqual(run_main(self, ['--path', make_folder(self, {'ok.txt': 'fine\n'})], root=d)[0], 0)     # control: an existing clean folder passes
        self.assertEqual(run_main(self, ['--path', make_folder(self, {'wifi.ino': SECRET})], root=d)[0], 1)     # control: an existing folder with a secret blocks


class Allowlist(unittest.TestCase):
    f = L.Finding('credential', 'must', 'docs/C#/wifi.ino', 1, 'Hunter2!x', 'n')

    def test_a_rule_alone_on_a_line_matches_nothing_and_does_not_raise(self):
        self.assertFalse(L.allowed(self.f, ['credential', '*', '  credential   # no glob']))
        self.assertTrue(L.allowed(self.f, ['credential', '* docs/*']))               # control: later lines still count

    def test_a_hash_starts_a_comment_only_at_the_line_start_or_after_a_space(self):
        self.assertTrue(L.allowed(self.f, ['* docs/C#/wifi.ino']))                   # a '#' inside the glob
        self.assertTrue(L.allowed(self.f, ['* docs/C#/wifi.ino  # why']))
        self.assertFalse(L.allowed(self.f, ['# * docs/C#/wifi.ino']))                # a commented-out line allows nothing
        self.assertFalse(L.allowed(self.f, ['* docs/C #/wifi.ino']))                 # control: a comment cut the glob short

    def test_matching_is_case_sensitive_on_slash_paths(self):                         # fnmatch.fnmatch lower-cases on Windows
        self.assertTrue(L.allowed(self.f, ['* docs/*/wifi.ino']))
        self.assertFalse(L.allowed(self.f, ['* Docs/*/wifi.ino']))
        self.assertFalse(L.allowed(self.f, ['* docs\\C#\\wifi.ino']))                # and '\' is not a separator

    def test_the_file_may_start_with_a_byte_order_mark(self):
        d = make_folder(self, {'wifi.ino': SECRET})
        self.assertEqual(run_main(self, ['--path', d], allow=b'\xef\xbb\xbf* wifi.ino\n')[0], 0)
        self.assertEqual(run_main(self, ['--path', d], allow=b'\xef\xbb\xbf* other.ino\n')[0], 1)    # control: the first line is read as itself

    def test_gps_photos_and_gaps_get_a_row_each(self):
        photos = [L.Finding('gps', 'must', p, 0, 'GPS block', 'a photo with its location') for p in ('a.jpg', 'b.jpg')]
        self.assertEqual([r['paths'] for r in L.dedupe(photos)], [['a.jpg'], ['b.jpg']])
        gaps = [L.unreadable(p, 'over 8 MB, unscanned') for p in ('x.stl', 'y.stl')]
        self.assertEqual([r['paths'] for r in L.dedupe(gaps)], [['x.stl'], ['y.stl']])
        same = [L.Finding('credential', 'must', p, 1, 'Hunter2!x', 'n') for p in ('a.ino', 'b.ino')]
        self.assertEqual([r['paths'] for r in L.dedupe(same)], [['a.ino', 'b.ino']])              # control: one value in two files stays one row
        text = L.report(photos)
        self.assertIn('a.jpg', text); self.assertIn('b.jpg', text)

    def test_two_located_photos_in_a_folder_are_two_rows(self):
        got = scan(self, {'a.jpg': jpeg(True), 'sub/b.jpg': jpeg(True), 'c.jpg': jpeg(False)}, 'folder')
        self.assertEqual(sorted(r['paths'][0] for r in L.dedupe(got) if r['f'].rule == 'gps'), ['a.jpg', 'sub/b.jpg'])

    def test_a_row_stays_one_row(self):
        f = L.Finding('credential', 'must', 'we|ird\nname.ino', 3, 'x|y\nzHunter2!x', 'no|te\r\nnext')
        text = L.report([f])
        self.assertEqual(len(text.splitlines()), 3)
        row = text.splitlines()[2]
        self.assertEqual(len(re.split(r'(?<!\\)\|', row)), 8)                          # six cells between the outer pipes
        self.assertIn('we\\|ird name.ino', row)
        plain = L.report([L.Finding('credential', 'must', 'a.ino', 3, 'Hunter2!x', 'note')]).splitlines()[2]
        self.assertEqual(len(re.split(r'(?<!\\)\|', plain)), 8); self.assertNotIn('\\', plain)    # control: an ordinary row has no escapes


# Final review: the scan becomes the gate for the public gallery site. Every value is made up; each check has a control beside it.
import base64, struct, zlib
from PIL import PngImagePlugin

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FAKE_ID = 'Fake_id-Xyz09'
FAKE_UUID = '0123abcd-0000-4000-8000-000000000000'
FAKE_PATH = 'C:\\Users\\jane\\Desktop\\a.stl'


def blob(n, unit='Zm9vYmFy'):
    """n characters of base64-looking text"""
    return (unit * (n // len(unit) + 1))[:n]


class AuditFixes(unittest.TestCase):
    def test_a1_test_data_links_are_made_up(self):             # a real artifact id had been used as test data
        made_up = re.compile(r'fake|0000-4000-8000', re.I)
        for rel in ('tools/tests/test_leakscan.py', 'docs/superpowers/plans/2026-10-25-leak-audit.md'):
            p = os.path.join(REPO_DIR, *rel.split('/'))
            if not os.path.exists(p):
                continue
            with open(p, encoding='utf-8') as fh:
                links = [f.value for f in L.scan_text(rel, fh.read()) if f.rule == 'artifact_link']
            self.assertTrue(links, rel)                         # control: the file does hold test links, so the loop checked something
            for v in links:
                self.assertTrue(made_up.search(v), rel)         # (not assertRegex: its failure message would print the link)
        self.assertIsNone(made_up.search('Qm9vYmFyQmF6UXV4Nzc'))      # control: an id with no mark of being made up fails the test

    def test_a2_commit_messages_are_scanned_in_history(self):
        d = make_repo(self)
        write(d, 'a.txt', 'x\n'); git(d, 'add', 'a.txt')
        git(d, 'commit', '-q', '-m', 'add a', '-m', 'saved from ' + FAKE_PATH)
        first = git(d, 'rev-parse', 'HEAD').strip()
        write(d, 'b.txt', 'y\n'); git(d, 'add', 'b.txt')
        git(d, 'commit', '-q', '-m', 'add b', '-m', 'Co-Authored-By: Claude <noreply@anthropic.com>')
        found = [f for f in L.scan_repo(d, 'history') if f.path == '(commit message)']
        self.assertEqual([(f.rule, f.line, f.commit) for f in found], [('user_path', 3, first[:10])])     # the clean second message gives nothing
        self.assertEqual([f for f in L.scan_repo(d, 'head') if f.path == '(commit message)'], [])        # control: only history reads messages

    def test_a3_allowlist_names_the_rules_each_test_file_trips(self):
        lines = L.load_allow(os.path.join(REPO_DIR, 'tools', 'leakscan_allow.txt'))
        fnd = lambda rule, path: L.Finding(rule, 'decide', path, 1, 'v', 'n')
        for path in ('tools/tests/test_site.py', 'docs/superpowers/plans/2026-10-25-pages-showcase.md'):
            self.assertTrue(L.allowed(fnd('artifact_link', path), lines), path)
            for other in ('credential', 'token'):                # rules these files do not trip stay blocked: no '*' line
                self.assertFalse(L.allowed(fnd(other, path), lines), (other, path))
        self.assertTrue(L.allowed(fnd('credential', 'tools/tests/test_leakscan.py'), lines))     # control: the scanner's own tests keep their '*'


class LongLineRules(unittest.TestCase):
    def test_all_rules_run_on_a_long_line_around_base64(self):
        line = ' '.join([blob(25000), 'p="' + FAKE_PATH + '"', blob(12000), 'ip=10.0.0.99', blob(12000), 'mail=jane@hotmail.com',
                         blob(6000), 'see https://claude.ai/artifact/' + FAKE_ID])
        self.assertGreater(len(line), 50000)
        self.assertEqual(rules(line, 'v.js'), ['artifact_link', 'email', 'private_ip', 'user_path'])
        self.assertEqual([f.line for f in L.scan_text('v.js', 'a\nb\n' + line + '\nc')], [3, 3, 3, 3])     # the file's line numbers
        self.assertEqual(rules(blob(20000) + ' ' + blob(20000), 'v.js'), [])                               # control: the same line without the plants

    def test_a_pure_base64_line_finds_nothing(self):
        self.assertEqual(rules(blob(50000), 'v.js'), [])
        self.assertEqual(rules('"' + blob(50000) + '=="', 'v.js'), [])
        self.assertEqual(rules('data:image/png;base64,' + blob(50000, 's8L3wRfbsr/lCUc/c7v3wbq4u798KF9AFtT3wUr9k7+S8pRAi7P3'), 'v.html'), [])
        short = blob(150) + ' jane@hotmail.com'                  # control: a short run is not blanked, and a short line is read whole
        self.assertEqual(rules(short, 'v.js'), ['email'])

    def test_long_lines_of_every_shape_stay_linear(self):        # every rule now runs on a long line
        for t in ('a-' * 500000, 'a.' * 500000, 'a@' * 500000, 'C:' + '/' * 1000000, 'C:/' * 300000, 'claude.ai/' * 100000,
                  'www.' * 250000, ' 10.' * 250000, 'https:\\/\\/' * 100000, '%2F' * 300000, 'AIza' * 250000, 'a' * 1000000 + '@'):
            t0 = time.time()
            L.scan_text('v.js', t)
            self.assertLess(time.time() - t0, 2.0, t[:12])

    def test_an_11_mb_page_is_scanned_in_seconds(self):           # chassis-v2/out/lineup.html is one 11 MB line of embedded meshes
        line = '<script>var M="' + blob(5_000_000) + '";var p="' + FAKE_PATH + '";var M2="' + blob(6_000_000) + '";</script>'
        page = line + '\nshort line\n<a href="https://claude.ai/artifact/' + FAKE_ID + '">x</a>\n'
        self.assertGreater(len(page), 11_000_000)
        t0 = time.time()
        got = L._scan_bytes('lineup.html', page.encode())
        self.assertLess(time.time() - t0, 5.0)
        self.assertEqual(sorted((f.rule, f.line) for f in got), [('artifact_link', 3), ('user_path', 1)])
        clean = (line.replace(FAKE_PATH, 'a.stl') + '\nshort line\n').encode()                # control: the same page without the plants
        self.assertEqual(L._scan_bytes('lineup.html', clean), [])

    def test_a_text_file_over_the_binary_cap_is_still_scanned(self):       # lineup.html is 11 MB, the binary cap 8 MB
        files = {'big.html': 'x' * 100 + ' ' + FAKE_PATH + '\n', 'big.bin': b'\x00' * 150}
        with mock.patch.object(L, 'MAX_BLOB', 100):
            for mode in ('folder',) + MODES:
                with self.subTest(mode=mode):
                    got = sorted((f.rule, f.path) for f in scan(self, files, mode) if f.rule != 'author_email')
                    self.assertEqual(got, [('unreadable', 'big.bin'), ('user_path', 'big.html')])    # the page is read; the binary of the same size is not


def data_uri(b, kind='jpeg'):
    return f'data:image/{kind};base64,' + base64.b64encode(b).decode()


class DataUris(unittest.TestCase):
    page = '<html><body><img src="%s"></body></html>\n'

    def test_a_located_jpeg_in_a_page(self):
        for mode in ('folder',) + MODES:
            with self.subTest(mode=mode):
                got = [(f.rule, f.path) for f in scan(self, {'page.html': self.page % data_uri(jpeg(True))}, mode) if f.rule != 'author_email']
                self.assertEqual(got, [('gps', 'page.html!data-uri-1')])
                plain = scan(self, {'page.html': self.page % data_uri(jpeg(False))}, mode)
                self.assertEqual([f for f in plain if f.rule != 'author_email'], [])       # control: a plain jpeg gives nothing

    def test_images_are_numbered_in_order_and_other_forms_are_read(self):
        two = '<img src="%s"><img src="%s">' % (data_uri(jpeg(False)), data_uri(jpeg(True)))
        self.assertEqual([(f.rule, f.path) for f in L.scan_folder(make_folder(self, {'p.html': two}))], [('gps', 'p.html!data-uri-2')])
        escaped = 'var a = "' + data_uri(jpeg(True)).replace('/', '\\/') + '";'            # JSON / JS-escaped slashes
        self.assertEqual([(f.rule, f.path) for f in L.scan_folder(make_folder(self, {'v.js': escaped}))], [('gps', 'v.js!data-uri-1')])
        author = data_uri(png(text={'Author': 'Jane Q Public'}), 'png')
        self.assertEqual([(f.rule, f.path) for f in L.scan_folder(make_folder(self, {'p.html': author}))], [('doc_author', 'p.html!data-uri-1')])
        other = 'data:application/octet-stream;base64,' + base64.b64encode(jpeg(True)).decode()
        self.assertEqual(L.scan_folder(make_folder(self, {'p.html': other})), [])          # control: only image data URIs are decoded

    def test_a_payload_that_cannot_be_decoded_is_a_gap(self):
        bad = 'data:image/jpeg;base64,' + 'A' * 101                                        # 101 characters: no whole number of bytes
        got = L.scan_folder(make_folder(self, {'p.html': bad}))
        self.assertEqual([(f.rule, f.path, f.grade) for f in got], [('unreadable', 'p.html!data-uri-1', 'decide')])


def chunk(typ, body):
    return struct.pack('>I', len(body)) + typ + body + struct.pack('>I', zlib.crc32(typ + body))


def png(text=None, ztxt=None, itxt=None, exif=None, extra=b''):
    """a PNG with text chunks (tEXt, zTXt, iTXt) and an eXIf chunk; `extra` is spliced in right after the header chunk"""
    info = PngImagePlugin.PngInfo()
    for k, v in (text or {}).items():
        info.add_text(k, v)
    for k, v in (ztxt or {}).items():
        info.add_text(k, v, zip=True)
    for k, v in (itxt or {}).items():
        info.add_itxt(k, v)
    b = io.BytesIO()
    Image.new('RGB', (8, 8)).save(b, 'PNG', pnginfo=info, **({} if exif is None else {'exif': exif}))
    d = b.getvalue()
    return d[:33] + extra + d[33:]


def png_exif(gps):
    ex = Image.Exif(); ex[0x010F] = 'Apple'; ex[0x013B] = 'Jane Q Public'
    if gps:
        ex[0x8825] = {1: 'N', 2: (42.0, 16.0, 30.0), 3: 'W', 4: (83.0, 44.0, 10.0)}
    return ex


class PngText(unittest.TestCase):
    def rv(self, data):
        return sorted((f.rule, f.value) for f in L.scan_binary('a.png', data))

    def test_author_keys_in_every_chunk_kind(self):
        for key in ('Author', 'Artist', 'Copyright'):
            self.assertEqual(self.rv(png(text={key: 'Jane Q Public'})), [('doc_author', 'Jane Q Public')], key)
        self.assertEqual(self.rv(png(ztxt={'Author': 'Jane Q Public'})), [('doc_author', 'Jane Q Public')])        # compressed
        self.assertEqual(self.rv(png(itxt={'Author': 'Jane Q Public'})), [('doc_author', 'Jane Q Public')])        # international
        self.assertEqual(self.rv(png(text={'author': 'Jane Q Public'})), [('doc_author', 'Jane Q Public')])        # any case
        self.assertEqual(self.rv(png()), [])                                                                        # controls: a plain PNG,
        self.assertEqual(self.rv(png(text={'Author': 'Unknown'})), [])                                              # a placeholder name,
        self.assertEqual(self.rv(png(text={'Software': 'matplotlib', 'Title': 'Jane Q Public bracket'})), [])      # and keys that are not a name

    def test_every_chunks_text_goes_through_the_text_rules(self):
        self.assertEqual(self.rv(png(text={'Comment': 'from ' + FAKE_PATH}))[0][0], 'user_path')
        xmp = '<x:xmpmeta><rdf:li>' + FAKE_PATH + '</rdf:li></x:xmpmeta>'
        self.assertEqual([r for r, _ in self.rv(png(itxt={'XML:com.adobe.xmp': xmp}))], ['user_path'])
        self.assertEqual([r for r, _ in self.rv(png(ztxt={'Comment': 'mail jane@hotmail.com'}))], ['email'])
        self.assertEqual(self.rv(png(itxt={'XML:com.adobe.xmp': '<x:xmpmeta>a.stl</x:xmpmeta>'})), [])             # control: no path, nothing

    def test_exif_chunk(self):
        got = L.scan_binary('a.png', png(exif=png_exif(True)))
        self.assertEqual(sorted(f.rule for f in got), ['doc_author', 'gps'])            # located, and the Artist tag; each once
        self.assertEqual(sorted(f.rule for f in L.scan_binary('a.png', png(exif=png_exif(False)))), ['doc_author'])   # control: no GPS block
        self.assertEqual(sorted(f.rule for f in L.scan_png('a.png', png(exif=png_exif(True)))), ['doc_author', 'gps'])   # the chunk walk alone, without Pillow
        self.assertEqual(L.scan_png('a.png', png()), [])                               # control: no chunk, no finding

    def test_truncated_and_oversized_chunks(self):
        d = png(text={'Author': 'Jane Q Public'})
        cut = L.scan_binary('a.png', d[:-20])                                           # IEND and part of IDAT gone: no crash, the name is still found
        self.assertIn('doc_author', {f.rule for f in cut})
        bomb = chunk(b'zTXt', b'Comment\x00\x00' + zlib.compress(b'A' * 40_000_000))    # 40 MB from about 40 KB
        t0 = time.time()
        got = L.scan_binary('a.png', png(extra=bomb))
        self.assertLess(time.time() - t0, 2.0)
        self.assertEqual({(f.rule, f.grade) for f in got}, {('unreadable', 'decide')})        # (Pillow refuses a chunk this large too)
        self.assertTrue(any('text chunk' in f.note for f in got))                              # and the walk says which chunk, and why
        self.assertEqual(L.scan_binary('a.png', png(extra=chunk(b'zTXt', b'Comment\x00\x00' + zlib.compress(b'fine')))), [])   # control: a small one reads


def box(t, payload=b''):
    return struct.pack('>I4s', 8 + len(payload), t) + payload


def qt_atom(t, text):
    """a QuickTime user-data text atom: 2-byte length, 2-byte language, the text"""
    s = text.encode()
    return box(t, struct.pack('>HH', len(s), 0x15C7) + s)


def gpp_atom(t, text):
    """a 3GPP user-data string box: version and flags, a language, the text and a NUL"""
    return box(t, bytes(4) + struct.pack('>H', 0x15C7) + text.encode() + b'\x00')


def ilst_item(t, text):
    return box(t, box(b'data', struct.pack('>II', 1, 0) + text.encode()))


XMP_UUID = bytes.fromhex('be7acfcb97a942e89c71999491e3afac')


def mp4(*udta, moov_extra=b'', top=b''):
    return (box(b'ftyp', b'isom' + bytes(4) + b'isomiso2') + box(b'mdat', bytes(16))
            + box(b'moov', box(b'mvhd', bytes(100)) + box(b'udta', b''.join(udta)) + moov_extra) + top)


class Mp4Metadata(unittest.TestCase):
    def rv(self, data, path='c.mp4'):
        return sorted((f.rule, f.grade) for f in L.scan_binary(path, data))

    def test_gps_atoms(self):
        self.assertEqual(self.rv(mp4(qt_atom(b'\xa9xyz', '+51.5000-000.1000/'))), [('gps', 'must')])
        loci = box(b'loci', bytes(4) + bytes(2) + b'Home\x00' + b'\x00' + bytes(12) + b'\x00\x00')
        self.assertEqual(self.rv(mp4(loci)), [('gps', 'must')])
        self.assertEqual(self.rv(mp4(qt_atom(b'\xa9too', 'Lavf58.76.100'))), [])               # control: the encoder tag alone
        self.assertEqual(self.rv(mp4()), [])                                                    # and no user data at all
        for ext in ('a.MOV', 'a.m4v', 'a.3gp'):
            self.assertEqual(self.rv(mp4(qt_atom(b'\xa9xyz', '+51.5000-000.1000/')), ext), [('gps', 'must')], ext)

    def test_author_atoms(self):
        for atom in (qt_atom(b'\xa9ART', 'Jane Q Public'), qt_atom(b'\xa9aut', 'Jane Q Public'), gpp_atom(b'auth', 'Jane Q Public')):
            got = L.scan_binary('c.mp4', mp4(atom))
            self.assertEqual([(f.rule, f.value) for f in got], [('doc_author', 'Jane Q Public')], atom[4:8])
        for atom in (qt_atom(b'\xa9ART', 'Unknown'), gpp_atom(b'auth', ''), qt_atom(b'\xa9nam', 'Jane Q Public bracket')):   # controls
            self.assertEqual(self.rv(mp4(atom)), [], atom[4:8])

    def test_ilst_items_and_apple_keys(self):
        meta = box(b'meta', bytes(4) + box(b'hdlr', bytes(8) + b'mdir' + bytes(12))
                   + box(b'ilst', ilst_item(b'\xa9ART', 'Jane Q Public') + ilst_item(b'\xa9cmt', 'from ' + FAKE_PATH)))
        self.assertEqual(self.rv(mp4(meta)), [('doc_author', 'decide'), ('user_path', 'decide')])
        plain = box(b'meta', box(b'ilst', ilst_item(b'\xa9ART', 'Jane Q Public')))             # QuickTime: no version and flags
        self.assertEqual(self.rv(mp4(plain)), [('doc_author', 'decide')])
        def keyed(name):
            k = name.encode()
            keys = box(b'keys', struct.pack('>II', 0, 1) + struct.pack('>I4s', 8 + len(k), b'mdta') + k)
            return box(b'meta', keys + box(b'ilst', ilst_item(b'\x00\x00\x00\x01', '+51.5000-000.1000/')))
        self.assertEqual(self.rv(mp4(keyed('com.apple.quicktime.location.ISO6709'))), [('gps', 'must')])
        self.assertEqual(self.rv(mp4(keyed('com.apple.quicktime.software'))), [])               # control: another key

    def test_text_atoms_and_xmp_go_through_the_text_rules(self):
        self.assertEqual(self.rv(mp4(qt_atom(b'\xa9cmt', 'made on ' + FAKE_PATH))), [('user_path', 'decide')])
        self.assertEqual(self.rv(mp4(qt_atom(b'\xa9cmt', 'mail jane@hotmail.com'))), [('email', 'decide')])
        xmp = box(b'uuid', XMP_UUID + b'<x:xmpmeta><rdf:li>' + FAKE_PATH.encode() + b'</rdf:li></x:xmpmeta>')
        self.assertEqual(self.rv(mp4(top=xmp)), [('user_path', 'decide')])                     # a top-level uuid box
        self.assertEqual(self.rv(mp4(xmp)), [('user_path', 'decide')])                         # and one inside udta
        self.assertEqual(self.rv(mp4(top=box(b'uuid', XMP_UUID + b'<x:xmpmeta>clip</x:xmpmeta>'))), [])      # control: no path in the XMP
        self.assertEqual(self.rv(mp4(top=box(b'uuid', bytes(16) + FAKE_PATH.encode()))), [])                 # other uuid boxes are not read

    def test_sizes_that_lie(self):
        atom = qt_atom(b'\xa9xyz', '+51.5000-000.1000/')
        wide = struct.pack('>I4sQ', 1, b'udta', 16 + len(atom)) + atom                          # a 64-bit size
        moov = box(b'moov', box(b'mvhd', bytes(100)) + wide)
        self.assertEqual(self.rv(box(b'ftyp', b'isom' + bytes(8)) + moov), [('gps', 'must')])
        last = struct.pack('>I4s', 0, b'moov') + box(b'udta', atom)                             # size 0: to the end of the file
        self.assertEqual(self.rv(box(b'ftyp', b'isom' + bytes(8)) + last), [('gps', 'must')])
        whole = mp4(atom)
        cut = self.rv(whole[:-5])                                                                # truncated inside the atom
        self.assertEqual(cut, [('gps', 'must'), ('unreadable', 'decide')])
        self.assertEqual(self.rv(whole), [('gps', 'must')])                                      # control: the whole file has no gap
        tiny = mp4(struct.pack('>I4s', 3, b'free') + bytes(20))                                  # a size below the header's own
        self.assertEqual(self.rv(tiny), [('unreadable', 'decide')])
        self.assertEqual(self.rv(b'x' * 100), [('unreadable', 'decide')])                        # not an MP4 at all
        self.assertEqual(self.rv(b''), [('unreadable', 'decide')])

    def test_work_is_bounded(self):
        many = box(b'ftyp', b'isom' + bytes(8)) + struct.pack('>I4s', 8, b'free') * 500000
        t0 = time.time()
        got = L.scan_binary('c.mp4', many)
        self.assertLess(time.time() - t0, 3.0)
        self.assertEqual([f.rule for f in got], ['unreadable'])
        few = box(b'ftyp', b'isom' + bytes(8)) + struct.pack('>I4s', 8, b'free') * 1000
        self.assertEqual(L.scan_binary('c.mp4', few), [])                                       # control: a thousand boxes are fine
        deep = box(b'\xa9xyz', b'+1+1/')
        for _ in range(2000):
            deep = box(b'udta', deep)
        got = L.scan_binary('c.mp4', box(b'ftyp', b'isom' + bytes(8)) + box(b'moov', deep))     # nesting past the depth cap: no RecursionError
        self.assertEqual([f.rule for f in got], ['unreadable'])

    def test_the_two_real_clips_are_clean(self):
        for rel in ('research/figures/sim_drops.mp4', 'research/figures/step_down.mp4'):
            p = os.path.join(REPO_DIR, *rel.split('/'))
            if not os.path.exists(p):
                self.skipTest(rel + ' is not here')
            with open(p, 'rb') as fh:
                self.assertEqual(L.scan_binary(rel, fh.read()), [], rel)
        self.assertEqual([f.rule for f in L.scan_binary('x.mp4', mp4(qt_atom(b'\xa9xyz', '+51.5000-000.1000/')))], ['gps'])    # control


def stl(header, tris=1):
    return header.ljust(80, b'\x00') + struct.pack('<I', tris) + bytes(50 * tris)


class StlHeader(unittest.TestCase):
    def test_binary_header_is_text(self):
        for mode in ('folder',) + MODES:
            with self.subTest(mode=mode):
                got = [(f.rule, f.path) for f in scan(self, {'part.stl': stl(b'exported from ' + FAKE_PATH.encode())}, mode) if f.rule != 'author_email']
                self.assertEqual(got, [('user_path', 'part.stl!header')])
                clean = scan(self, {'part.stl': stl(b'binary STL from Blender')}, mode)
                self.assertEqual([f for f in clean if f.rule != 'author_email'], [])        # control: a clean header
        self.assertEqual([f.rule for f in L._scan_bytes('part.stl', stl(b'solid ' + FAKE_PATH.encode()))], ['user_path'])   # 'solid' headers too

    def test_ascii_stl_is_already_text(self):
        t = ('solid ' + FAKE_PATH + '\nfacet normal 0 0 1\nendsolid\n').encode()
        self.assertEqual([(f.rule, f.path) for f in L._scan_bytes('part.stl', t)], [('user_path', 'part.stl')])


class UnknownBinaries(unittest.TestCase):
    def folder(self):                                          # two binaries no reader handles, among files that a reader handles
        return {'a.bin': b'\x00\x01\x02', 'sub/b.wasm': b'\x00asm\x01', 'ok.txt': 'fine\n', 'pic.png': png(), 'mesh.stl': stl(b'x'), 'clip.mp4': mp4()}

    def test_scan_folder_reports_binaries_no_reader_handles(self):
        got = L.scan_folder(make_folder(self, self.folder()))
        self.assertEqual(sorted((f.rule, f.grade, f.path) for f in got), [('unreadable', 'decide', 'a.bin'), ('unreadable', 'decide', 'sub/b.wasm')])
        self.assertIn('binary type not read', got[0].note)
        d = make_folder(self, self.folder())
        self.assertEqual(run_main(self, ['--path', d])[0], 0)                                # a 'decide' finding: not blocking...
        self.assertEqual(run_main(self, ['--path', d, '--strict'])[0], 1)                    # ... until --strict
        self.assertEqual(run_main(self, ['--path', d, '--strict'], allow=b'unreadable *.bin\nunreadable *.wasm\n')[0], 0)   # control: allowed, so it passes

    def test_the_repo_modes_are_unchanged(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                got = scan(self, self.folder(), mode)
                self.assertEqual([f for f in got if f.rule == 'unreadable'], [])
        self.assertEqual(L._scan_bytes('mesh.bin', b'\x00\x01'), [])


class AlternateAllowlist(unittest.TestCase):
    def test_allow_flag_replaces_the_default(self):
        d = make_folder(self, {'wifi.ino': SECRET}); ad = make_folder(self, {'alt.txt': 'credential wifi.ino\n', 'other.txt': 'credential other.ino\n'})
        alt, other = os.path.join(ad, 'alt.txt'), os.path.join(ad, 'other.txt')
        self.assertEqual(run_main(self, ['--path', d])[0], 1)                                    # not allowed by the default (empty) list
        self.assertEqual(run_main(self, ['--path', d, '--allow', alt])[0], 0)                    # allowed by the alternate file alone
        self.assertEqual(run_main(self, ['--path', d, '--allow', other])[0], 1)                  # control: an alternate that misses allows nothing
        self.assertEqual(run_main(self, ['--path', d, '--allow', other], allow=b'credential wifi.ino\n')[0], 1)    # and it replaces, not adds to, the default

    def test_a_missing_allow_file_is_an_error(self):
        d = make_folder(self, {'ok.txt': 'fine\n'})
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = run_main(self, ['--path', d, '--allow', os.path.join(d, 'gone.txt')])[0]
        self.assertEqual(code, 2); self.assertIn('--allow', err.getvalue())
        self.assertEqual(run_main(self, ['--path', d])[0], 0)                                    # control: without it the folder is clean


class PrivateLinks(unittest.TestCase):
    def test_every_form_is_found(self):
        forms = ['https://claude.ai/artifact/' + FAKE_ID, 'http://claude.ai/artifact/' + FAKE_ID, 'HTTPS://CLAUDE.AI/ARTIFACT/' + FAKE_ID,
                 'https://www.claude.ai/artifact/' + FAKE_ID, 'claude.ai/artifact/' + FAKE_ID, '<img src="//claude.ai/artifact/' + FAKE_ID + '">',
                 'https://claude.ai/code/artifact/' + FAKE_UUID, 'https://claude.ai/public/artifacts/' + FAKE_ID,
                 'www.claude.ai/code/artifact/' + FAKE_UUID,
                 r'"https:\/\/claude.ai\/artifact\/' + FAKE_ID + '"', r'"https:\/\/claude.ai\/code\/artifact\/' + FAKE_UUID + '"',
                 r'"https:\/\/claude.ai\/public\/artifacts\/' + FAKE_ID + '"', r'"https:\\/\\/claude.ai\\/artifact\\/' + FAKE_ID + '"',
                 r'"https:\u002f\u002fclaude.ai\u002fartifact\u002f' + FAKE_ID + '"',
                 'https%3A%2F%2Fclaude.ai%2Fartifact%2F' + FAKE_ID, 'https%3a%2f%2fclaude.ai%2fcode%2fartifact%2f' + FAKE_UUID,
                 'href=https%3A%2F%2Fwww.claude.ai%2Fpublic%2Fartifacts%2F' + FAKE_ID]
        for t in forms:
            self.assertEqual(rules(t, 'a.html'), ['artifact_link'], t)
            [f] = L.scan_text('a.html', t)
            self.assertTrue(f.value.endswith(FAKE_ID) or f.value.endswith(FAKE_UUID), t)       # the whole id, '-' and '_' included

    def test_near_misses_are_not_found(self):
        for t in ('https://claude.ai/', 'https://claude.ai', 'https://claude.ai/login', 'https://claude.ai/artifacts', 'https://claude.ai/artifact/',
                  'https://claude.ai/public/artifacts/', 'https://example.com/artifact/' + FAKE_ID, 'https://docs.anthropic.com/en/docs/artifact/' + FAKE_ID,
                  'https://notclaude.ai/artifact/' + FAKE_ID, 'https://claude.ai.example.com/artifact/' + FAKE_ID, 'https://example.com/claude.ai-artifact/x',
                  'claude.ai is a site'):
            self.assertEqual(rules(t, 'a.html'), [], t)


class EscapedJsonCredentials(unittest.TestCase):
    def test_escaped_quotes_in_a_js_string(self):
        for t in (r'{\"password\":\"Fake123x\"}', r'{\"wifi_ssid\": \"homenet\"}', r'var s = "{\"password\":\"Fake123x\"}";',
                  r"var s = '{\'password\':\'Fake123x\'}';", r'{\"ssid\": \"homenet\", \"password\": \"Fake123x\"}'):
            self.assertEqual(rules(t, 'v.js'), ['credential'], t)
        self.assertEqual([f.value for f in L.scan_text('v.js', r'{\"password\":\"Fake123x\"}')], ['Fake123x'])      # the value, without the backslash
        for t in (r'{\"password\":\"your-password\"}', r'{\"wifi_ssid\": \"\"}', r'{\"password\":\"<your password>\"}', r'{\"user\":\"Fake123x\"}'):
            self.assertEqual(rules(t, 'v.js'), [], t)                                           # controls: placeholders, an empty value, another key


class UnreadableFiles(unittest.TestCase):
    def test_a_file_that_cannot_be_opened_is_a_finding_not_a_crash(self):
        d = make_folder(self, {'a.txt': 'fine\n', 'b.ino': SECRET})
        real_open = open
        def deny(p, *a, **k):
            if str(p).endswith('a.txt'):
                raise PermissionError(13, 'denied')
            return real_open(p, *a, **k)
        with mock.patch.object(L, 'open', deny, create=True):
            got = [(f.rule, f.path) for f in L.scan_folder(d)]
        self.assertEqual(got, [('unreadable', 'a.txt'), ('credential', 'b.ino')])               # the rest of the folder is still read
        self.assertEqual(L.scan_folder(make_folder(self, {'a.txt': 'fine\n'})), [])             # control: without the denial it is clean

    def test_a_dangling_link_is_a_finding_not_a_crash(self):    # a Windows user may not be allowed to make a symlink: mock what it does
        d = make_folder(self, {'a.txt': 'fine\n', 'dangling.txt': 'x'})
        real_size = os.path.getsize
        def size(p):
            if str(p).endswith('dangling.txt'):
                raise FileNotFoundError(2, 'no such file')
            return real_size(p)
        with mock.patch.object(L.os.path, 'getsize', size):
            fs = L.scan_folder(d)
        self.assertEqual([(f.rule, f.grade, f.path) for f in fs], [('unreadable', 'decide', 'dangling.txt')])
        self.assertNotIn('dangling', fs[0].note)                 # the note says why, never the path or the system's message
        self.assertEqual(L.scan_folder(d), [])                   # control: with the real getsize the same folder is clean

    def test_a_folder_that_cannot_be_listed_and_a_linked_folder_are_findings(self):
        d = make_folder(self, {'a.txt': 'fine\n'})
        def walk(top, onerror=None, **_):
            if onerror:
                onerror(PermissionError(13, 'denied', os.path.join(top, 'locked')))
            yield top, ['linked'], []
        with mock.patch.object(L.os, 'walk', walk), mock.patch.object(L.os.path, 'islink', lambda p: p.endswith('linked')):
            got = sorted((f.rule, f.path) for f in L.scan_folder(d))
        self.assertEqual(got, [('unreadable', 'linked'), ('unreadable', 'locked')])
        self.assertEqual(L.scan_folder(d), [])                                                  # control: the real walk finds nothing wrong


# Round 2. Every value is made up; each check has a control beside it.
class EscapedNewlines(unittest.TestCase):
    """A literal backslash-n in JSON or a JS string must not make the next word look like part of the one before."""
    def test_the_three_planted_forms_are_found(self):
        for t, rule in ((r'{"cwd":"/work\n/home/jane"}', 'user_path'), (r'{"ip":"host\n192.168.7.9"}', 'private_ip'),
                        (r'{"u":"see\nclaude.ai/artifact/' + FAKE_ID + '"}', 'artifact_link'),
                        (r'"cwd\n/home/jane"', 'user_path'), (r'\n192.168.7.9', 'private_ip'), (r'\nclaude.ai/artifact/' + FAKE_ID, 'artifact_link')):
            self.assertEqual(rules(t, 'a.json'), [rule], t)

    def test_every_escape_and_the_doubled_forms(self):
        for esc in (r'\n', r'\r', r'\t', r'\\n', r'\\r', r'\\t', r'\r\n', r'\\r\\n'):
            for tail, rule in (('/home/jane', 'user_path'), ('192.168.7.9', 'private_ip'), ('claude.ai/artifact/' + FAKE_ID, 'artifact_link'),
                               ('/Users/jane/x', 'user_path'), ('10.0.0.99', 'private_ip')):
                self.assertEqual(rules('{"k":"v' + esc + tail + '"}', 'a.json'), [rule], (esc, tail))

    def test_what_is_found_is_the_thing_not_the_escape(self):
        [f] = L.scan_text('a.json', 'ok\n{"cwd":"x\\n/home/jane"}\nok\n')
        self.assertEqual((f.rule, f.line, f.value), ('user_path', 2, '/home/jane'))          # the file's line, and no 'n' glued on

    def test_controls_a_backslash_n_before_a_non_finding_gives_nothing(self):
        for t in (r'"line one\nthe user said hello\nhome sweet home"', r'"cwd\nhome/jane"', r'"v\n10.2\n192.168"', r'"a\nclaude.ai\nartifact\nx"',
                  r'"a\nclaude.ai/artifacts"', r'"\n\r\t\\n"', r'C:\new\table\run', 'plain text, no escapes'):
            self.assertEqual(rules(t, 'a.json'), [], t)

    def test_a_user_name_that_starts_with_n_r_or_t_is_still_found(self):     # \n, \r and \t are also the start of C:\Users\nick
        for t in (r'C:\Users\nick\Desktop', r'C:\Users\ryan\x', r'C:\Users\tom', r'C:\\Users\\naomi\\x', r'C:\Users\new', r'"C:\\Users\\ted"'):
            self.assertEqual(rules(t, 'a.md'), ['user_path'], t)
        self.assertEqual([f.value for f in L.scan_text('a.md', r'C:\Users\nick\Desktop')], [r'C:\Users\nick'])

    def test_an_email_after_an_escape_is_found_once(self):
        self.assertEqual(rules(r'{"m":"x\njane@hotmail.com"}', 'a.json'), ['email'])
        self.assertEqual(len(L.scan_text('a.json', r'{"m":"x\njane@hotmail.com"}')), 1)       # not once for each reading of the line

    def test_a_long_run_of_backslashes_stays_linear(self):
        for t in ('\\' * 1000000, '\\n' * 500000, '\\' * 500000 + 'n', ('\\' * 999 + 'n') * 1000, 'x\\n/home/jane ' * 50000):
            t0 = time.time()
            L.scan_text('a.json', t)
            self.assertLess(time.time() - t0, 3.0, t[:8])


# every form below is one the gallery's PRIVATE pattern matches; the cross-check below proves that, so a drift in either is a failure
PRIVATE_FORMS = [
    'https://claude.ai/artifact/{id}', 'http://claude.ai/code/artifact/{id}', 'HTTPS://CLAUDE.AI/ARTIFACT/{id}', 'https://www.claude.ai/artifact/{id}',
    'claude.ai/artifact/{id}', '//claude.ai/artifact/{id}', 'https://claude.ai/public/artifacts/{id}', 'https://claude.ai/public/artifact/{id}',
    'https://claude.ai/artifacts/{id}', 'https://claude.ai/code/artifacts/{id}', 'https://claude.ai/code/public/artifacts/{id}',
    r'https:\/\/claude.ai\/artifact\/{id}', r'https:\\/\\/claude.ai\\/artifact\\/{id}', r'https:\/\/claude.ai\/public\/artifacts\/{id}',
    r'https%3A%2F%2Fclaude.ai%2Fartifact%2F{id}', r'https%3a%2f%2fclaude.ai%2fcode%2fartifact%2f{id}',
    r'https%253A%252F%252Fclaude.ai%252Fartifact%252F{id}', r'https%25253A%25252F%25252Fclaude.ai%25252Fartifact%25252F{id}',
    'https:@u002f@u002fclaude.ai@u002fartifact@u002f{id}'.replace('@', chr(92)), 'https:@@u002F@@u002Fclaude.ai@@u002Fcode@@u002Fartifact@@u002F{id}'.replace('@', chr(92)),
    'https&#58;&#47;&#47;claude.ai&#47;artifact&#47;{id}', 'https&#x3a;&#x2f;&#x2f;claude.ai&#x2f;artifact&#x2f;{id}',
    'https&colon;&sol;&sol;claude.ai&sol;artifact&sol;{id}', 'https&#0058;&#0047;&#0047;claude.ai&#0047;code&#0047;artifact&#0047;{id}',
    'https://claude.ai&sol;artifact&sol;{id}', 'claude.ai%2Fpublic%2Fartifacts%2F{id}', 'HTTPS%3A%2F%2FWWW.CLAUDE.AI%2FCODE%2FARTIFACT%2F{id}',
    'https://claude.ai/artifact/{id}/sub/page?a=1#frag',
]
NOT_PRIVATE_FORMS = ['https://claude.ai/', 'https://claude.ai', 'https://example.com/artifact/x', 'https://docs.anthropic.com/en/docs/claude-code',
                     'https://claude.ai/login', 'https://claude.ai/artifact/', 'https://claude.ai/artifacts', 'https://claude.ai/settings/artifact/{id}',
                     'https://claude.aix/artifact/{id}', 'https://claude.ai.example.com/artifact/{id}', 'https://www.anthropic.com/claude',
                     'https://github.com/x/claude/artifact/abc', '//example.com/artifact/{id}', 'artifact/{id}']


class OnePrivateLinkPattern(unittest.TestCase):
    """leakscan keeps its own copy of the gallery's private-link pattern (no import from tools/gallery); this is the cross-check."""
    def setUp(self):
        from gallery import build as GB
        self.private = GB.PRIVATE

    def flagged(self, text):
        return [f.rule for f in L.scan_text('a.html', text) if f.rule == 'artifact_link']

    def test_there_are_enough_forms(self):
        self.assertGreaterEqual(len(PRIVATE_FORMS), 20)

    def test_every_string_the_gallery_pattern_matches_is_flagged(self):
        for form in PRIVATE_FORMS:
            link = form.format(id=FAKE_ID)
            self.assertIsNotNone(self.private.search(link), form)                  # the form really is one the gallery strips
            for text in (link, 'see ' + link + ' now', '"' + link + '"', '<a href="' + link + '">x</a>', link + ' ' + link):
                self.assertTrue(self.flagged(text), (form, text))
                for m in self.private.finditer(text):                              # and each thing it strips, on its own, is flagged
                    self.assertTrue(self.flagged(m.group(0)), (form, m.group(0)))
            self.assertEqual(len(self.flagged(link + ' ' + link)), 2, form)       # twice for two links

    def test_the_value_is_the_whole_id(self):
        for form in PRIVATE_FORMS:
            if '/sub/' in form:
                continue
            [f] = [f for f in L.scan_text('a.html', form.format(id=FAKE_ID)) if f.rule == 'artifact_link']
            self.assertTrue(f.value.endswith(FAKE_ID), form)

    def test_non_private_links_fire_in_neither(self):                              # controls: an over-broad copy fails here
        for form in NOT_PRIVATE_FORMS:
            link = form.format(id=FAKE_ID)
            for text in (link, 'see ' + link + ' now', '"' + link + '"'):
                self.assertIsNone(self.private.search(text), text)
                self.assertEqual(self.flagged(text), [], text)

    def test_the_host_still_has_to_start_a_word(self):                             # leakscan's own near-misses (the gallery pattern is wider on the left)
        for t in ('https://notclaude.ai/artifact/' + FAKE_ID, 'https://x.claude.ai/artifact/' + FAKE_ID, 'https://x-claude.ai/artifact/' + FAKE_ID):
            self.assertEqual(self.flagged(t), [], t)

    def test_matching_stays_linear(self):
        for t in ('%252F' * 200000, '&#47;' * 200000, '&sol;' * 200000, '%25' * 300000, '%' + '25' * 500000, 'claude.ai&#47;' * 100000,
                  'claude.ai%252F' * 100000, 'claude.ai' + '\\' * 500000, 'claude.ai/code/public/' * 50000):
            t0 = time.time()
            L.scan_text('a.html', t)
            self.assertLess(time.time() - t0, 3.0, t[:12])


class OversizeStl(unittest.TestCase):
    """A binary STL's header is all that is read, so the size cap does not apply to it."""
    def files(self):
        return {'part.stl': stl(b'exported from ' + FAKE_PATH.encode(), tris=3), 'clean.stl': stl(b'binary STL from Blender', tris=3)}

    def test_a_binary_stl_over_the_cap_is_read_by_its_header_in_every_mode(self):
        self.assertGreater(len(self.files()['part.stl']), 100)
        with mock.patch.object(L, 'MAX_BLOB', 100):
            for mode in ('folder',) + MODES:
                with self.subTest(mode=mode):
                    got = sorted((f.rule, f.path) for f in scan(self, self.files(), mode) if f.rule != 'author_email')
                    self.assertEqual(got, [('user_path', 'part.stl!header')])          # the dirty header found, the clean one silent, no 'unreadable'

    def test_controls_other_oversize_files_are_still_gaps(self):
        files = {'part.stl': stl(b'x', tris=3), 'big.bin': b'\x00' * 300, 'ascii.stl': 'solid a\n' + 'facet normal 0 0 1\n' * 20 + 'endsolid a\n'}
        with mock.patch.object(L, 'MAX_BLOB', 100):
            for mode in ('folder',) + MODES:
                with self.subTest(mode=mode):
                    got = sorted((f.rule, f.path) for f in scan(self, files, mode) if f.rule != 'author_email')
                    self.assertEqual(got, [('unreadable', 'ascii.stl'), ('unreadable', 'big.bin')])     # an ASCII STL's text is not read from 4 KB, so it is a gap

    def test_only_the_start_of_an_oversize_stl_is_read(self):
        reads = []
        class Spy:
            def __init__(self, fh): self.fh = fh
            def __enter__(self): self.fh.__enter__(); return self
            def __exit__(self, *a): return self.fh.__exit__(*a)
            def read(self, n=-1): reads.append(n); return self.fh.read(n)
        real_open = open
        with mock.patch.object(L, 'MAX_BLOB', 100), mock.patch.object(L, 'open', lambda p, *a, **k: Spy(real_open(p, *a, **k)), create=True):
            got = L.scan_folder(make_folder(self, {'part.stl': stl(b'x', tris=3)}))
        self.assertEqual(got, [])
        self.assertTrue(reads and all(0 <= n <= 4096 for n in reads), reads)               # never the whole file
        reads.clear()
        with mock.patch.object(L, 'open', lambda p, *a, **k: Spy(real_open(p, *a, **k)), create=True):
            L.scan_folder(make_folder(self, {'a.txt': 'fine\n'}))
        self.assertIn(-1, reads)                                                            # control: an ordinary file is read whole, so the spy sees that

    def test_a_partial_read_leaves_the_object_stream_in_step(self):
        d = make_repo(self)
        data = b'\x00' + bytes(range(256)) * 40
        commit(d, {'a.bin': data, 'b.txt': 'hello\n'})
        sha_a, sha_b = git(d, 'rev-parse', 'HEAD:a.bin').strip(), git(d, 'rev-parse', 'HEAD:b.txt').strip()
        with L._Objects(d) as objs:
            self.assertEqual(objs.read(sha_a, 10), data[:10])
            self.assertEqual(objs.read(sha_b), b'hello\n')                                  # the rest of a.bin was drained, not left in the pipe
            self.assertEqual(objs.read(sha_a), data)                                        # control: no limit reads it all


class PngChunkCap(unittest.TestCase):
    def count(self, data):
        i, n = 8, 0
        while i + 8 <= len(data):
            i += 12 + int.from_bytes(data[i:i + 4], 'big'); n += 1
        return n

    def test_more_chunks_than_the_cap_is_one_gap(self):
        junk = b''.join(chunk(b'prVt', b'x') for _ in range(20))
        d = png(text={'Author': 'Jane Q Public'}, extra=junk)
        n = self.count(d)
        with mock.patch.object(L, 'PNG_CHUNKS', 10):
            got = L.scan_binary('a.png', d)
        self.assertEqual([(f.rule, f.grade, f.path) for f in got], [('unreadable', 'decide', 'a.png')])        # one row; the author is past the cap
        self.assertIn('chunks', got[0].note)
        with mock.patch.object(L, 'PNG_CHUNKS', n):                                         # control: a cap that fits every chunk reads them all
            self.assertEqual([(f.rule, f.value) for f in L.scan_binary('a.png', d)], [('doc_author', 'Jane Q Public')])
        with mock.patch.object(L, 'PNG_CHUNKS', n - 1):                                     # and one chunk fewer than the file has is a gap (IEND unread)
            self.assertEqual(sorted(f.rule for f in L.scan_binary('a.png', d)), ['doc_author', 'unreadable'])
        with mock.patch.object(L, 'PNG_CHUNKS', 10_000):
            self.assertEqual([f.rule for f in L.scan_binary('a.png', png())], [])           # control: an ordinary PNG under the real cap is clean

    def test_the_gap_is_reported_in_every_route_to_scan_png(self):
        d = png(extra=b''.join(chunk(b'prVt', b'x') for _ in range(20)))
        with mock.patch.object(L, 'PNG_CHUNKS', 10):
            self.assertEqual([f.rule for f in L.scan_png('a.png', d)], ['unreadable'])
            self.assertEqual([(f.rule, f.path) for f in L.scan_folder(make_folder(self, {'a.png': d}))], [('unreadable', 'a.png')])
            page = '<img src="' + data_uri(d, 'png') + '">'
            self.assertEqual([(f.rule, f.path) for f in L.scan_folder(make_folder(self, {'p.html': page}))], [('unreadable', 'p.html!data-uri-1')])


class AllowlistTidy(unittest.TestCase):
    PLAN = 'docs/superpowers/plans/2026-10-25-leak-audit.md'

    def lines(self):
        return L.load_allow(os.path.join(REPO_DIR, 'tools', 'leakscan_allow.txt'))

    def test_the_gallery_tests_planted_paths_are_allowed_as_user_path(self):
        fnd = lambda rule, path: L.Finding(rule, 'decide', path, 1, 'v', 'n')
        self.assertTrue(L.allowed(fnd('user_path', 'tools/tests/test_site.py'), self.lines()))
        self.assertFalse(L.allowed(fnd('user_path', 'tools/gallery/build.py'), self.lines()))        # control: only that file
        self.assertFalse(L.allowed(fnd('credential', 'tools/tests/test_site.py'), self.lines()))     # and only that rule

    def test_the_allowlist_file_scans_clean(self):
        with open(os.path.join(REPO_DIR, 'tools', 'leakscan_allow.txt'), 'rb') as fh:
            data = fh.read()
        self.assertEqual([(f.rule, f.path) for f in L._scan_bytes('tools/leakscan_allow.txt', data)], [])     # no sample data URI quoted in a reason
        sample = data + b'\n# a data URI as text: data:image/png;base64,AAAA\n'
        self.assertEqual([f.rule for f in L._scan_bytes('tools/leakscan_allow.txt', sample)], ['unreadable'])  # control: a quoted sample is a finding

    def test_the_leak_audit_plan_is_allowed_rule_by_rule(self):
        p = os.path.join(REPO_DIR, *self.PLAN.split('/'))
        if not os.path.exists(p):
            self.skipTest(self.PLAN + ' is not here')
        with open(p, 'rb') as fh:
            found = L._scan_bytes(self.PLAN, fh.read())
        self.assertTrue(found)                                                                       # control: the plan does trip rules, so this checked something
        self.assertTrue(all(L.allowed(f, self.lines()) for f in found), sorted({f.rule for f in found if not L.allowed(f, self.lines())}))
        for rule in sorted({f.rule for f in found}):
            self.assertTrue(any(l.split(None, 1)[:1] == [rule] and self.PLAN in l for l in self.lines()), rule)    # a line of its own, with a reason
        for rule in ('gps', 'doc_author', 'author_email'):                                           # rules the plan does not trip stay blocked: no '*' line
            self.assertFalse(L.allowed(L.Finding(rule, 'must', self.PLAN, 0, 'v', 'n'), self.lines()), rule)


if __name__ == '__main__':
    unittest.main()
