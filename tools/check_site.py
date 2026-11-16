#!/usr/bin/env python3
"""Offline link and consistency checks for the My Titanium Brothers repository.

Standard library only. Reads the working tree, writes tools/CHECK-REPORT.md,
prints the same report, and exits 1 when it finds an error. Warnings do not
fail the run. This script does not modify conversation, raw, full-text,
structured, or introduction files.
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPORT_PATH = os.path.join(ROOT, 'tools', 'CHECK-REPORT.md')
SITE = 'https://uracrom.github.io/My-Titanium-Brothers'
RAW = 'https://raw.githubusercontent.com/Uracrom/My-Titanium-Brothers/main'
SITE_PREFIX = '/My-Titanium-Brothers/'

MODELS = (
    ('grok', 'Grok'),
    ('claude', 'Claude'),
    ('chatgpt', 'ChatGPT'),
    ('chatgpt-whatsapp', 'ChatGPT (WhatsApp)'),
    ('copilot', 'Copilot'),
    ('deepseek', 'DeepSeek'),
    ('gemini', 'Gemini'),
)
NAME_BY_KEY = dict(MODELS)
KEY_BY_NAME = {name: key for key, name in MODELS}

PARTT = re.compile(
    r'^(.*?)\s*[-–—:(,]?\s*\(?\bPart\s+(\d+)\s+of\s+(\d+)\)?\s*$',
    re.I,
)
URL_RE = re.compile(r'https?://[^\s<>"\'`)\]}]+')
HREF_RE = re.compile(r'''(?:href|src)\s*=\s*(['"])(.*?)\1''', re.I)
BYTE_RE = re.compile(r'([\d,]{3,})\s+bytes\b')
PART_LINE_RE = re.compile(r'^(?:PART|Guide|Manifest):\s+(\S+)', re.M)
ID_RE = re.compile(r'''\bid=(['"])(.*?)\1''')

# Files whose internal links are checked. llms-full.txt is a conversation dump,
# not a part list, so it is not scanned for links.
LINK_FILES = (
    'llms.txt',
    'archive.txt',
    'ai.txt',
    'README-for-AIs.md',
    'archive-manifest.json',
    'index.html',
    'full-text/index.html',
    'structured/INDEX.txt',
    'subject-map.html',
    'subject-map.json',
    'search/README.txt',
    'parts/INDEX.txt',
)

# The subject map (derived index) is rebuilt by tools/build_subject_map.py.
SUBJECT_MAP_JSON = 'subject-map.json'
SUBJECT_MAP_MAX_LINES = 460
NEXT_RE = re.compile(r'^NEXT:\s+(\S+)', re.M)

# The search index (derived) is rebuilt by tools/build_search_index.py, and the
# large-file parts lists by tools/build_large_file_parts.py.
SEARCH_MAX_BYTES = 250000
SEARCH_MAX_LINES = 400
SHA_RE = re.compile(r'SHA-256 ([0-9a-f]{64})\b')


def read_text(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as handle:
        return handle.read()


def unescape_basic(text):
    return (
        text.replace('&amp;', '&')
        .replace('&lt;', '<')
        .replace('&gt;', '>')
        .replace('&quot;', '"')
        .replace('&#x27;', "'")
        .replace('&#39;', "'")
    )


def strip_url_tail(url):
    return url.rstrip('.,;:')


def logical_groups(entries):
    """One group per conversation. Part N of M entries in one collection share a group."""
    groups = {}
    order = []
    for entry in entries:
        match = PARTT.match(entry.get('title') or '')
        if match:
            stem = match.group(1).strip(' -–—:')
            key = (entry.get('collection'), stem, int(match.group(3)))
        else:
            key = (entry.get('collection'), '__single__' + str(entry.get('id')), 0)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(entry)
    return [(key, groups[key]) for key in order]


def load_index():
    data = json.loads(read_text('index.json'))
    entries = data.get('conversations') or []
    return data, entries


def message_counts():
    """Sum the MESSAGES header in each structured conversation file."""
    by_key = defaultdict(int)
    files = 0
    for key, _name in MODELS:
        folder = os.path.join(ROOT, 'structured', key)
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            if not name.endswith('.txt'):
                continue
            files += 1
            with open(os.path.join(folder, name), encoding='utf-8') as handle:
                for line in handle:
                    if line.startswith('MESSAGES: '):
                        by_key[key] += int(line.split()[1])
                        break
    return by_key, files, sum(by_key.values())


def article_and_page_counts():
    pieces = {}
    pages = {}
    for key, _name in MODELS:
        pieces[key] = 0
        pages[key] = 0
        prefix = 'archive-%s-' % key
        for name in os.listdir(ROOT):
            if not name.startswith(prefix) or not name.endswith('.html'):
                continue
            rest = name[len(prefix):-len('.html')]
            if not rest.isdigit():
                continue
            pages[key] += 1
            with open(os.path.join(ROOT, name), encoding='utf-8') as handle:
                pieces[key] += handle.read().count('<article ')
    return pieces, pages


def sha256_of(rel):
    import hashlib
    with open(os.path.join(ROOT, rel), 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def file_size(rel):
    path = os.path.join(ROOT, rel)
    if os.path.isfile(path):
        return os.path.getsize(path)
    return None


class Checker(object):
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.passed = []
        self._ids = {}

    def error(self, text):
        self.errors.append(text)

    def warn(self, text):
        self.warnings.append(text)

    def ok(self, text):
        self.passed.append(text)

    def ids_of(self, rel):
        if rel not in self._ids:
            path = os.path.join(ROOT, rel)
            if not os.path.isfile(path):
                self._ids[rel] = None
            else:
                text = open(path, encoding='utf-8', errors='replace').read()
                self._ids[rel] = set(match.group(2) for match in ID_RE.finditer(text))
        return self._ids[rel]

    def resolve_site_path(self, url):
        """Return a repo-relative path, or None if the URL is not one of ours."""
        bare = strip_url_tail(unescape_basic(url))
        fragment = ''
        if '#' in bare:
            bare, fragment = bare.split('#', 1)
        bare = bare.split('?', 1)[0]
        if '<' in bare or '>' in bare or '<' in fragment or '>' in fragment:
            return 'template', bare, fragment
        rel = None
        if bare.startswith(SITE):
            rel = bare[len(SITE):].lstrip('/')
        elif bare.startswith(RAW):
            rel = bare[len(RAW):].lstrip('/')
        if rel is None:
            return 'external', bare, fragment
        if rel == '' or rel.endswith('/'):
            rel = rel + 'index.html'
        rel = os.path.normpath(rel)
        if rel.startswith('..'):
            return 'outside', rel, fragment
        return 'internal', rel, fragment

    def resolve_href(self, source_rel, href):
        href = unescape_basic(href).strip()
        if not href or href.startswith(('mailto:', 'tel:', 'javascript:', 'data:')):
            return 'skip', '', ''
        if href.startswith('#'):
            return 'fragment', source_rel, href[1:]
        if href.startswith(('http://', 'https://', '//')):
            if href.startswith('//'):
                return 'external', href, ''
            return self.resolve_site_path(href)
        fragment = ''
        path = href
        if '#' in path:
            path, fragment = path.split('#', 1)
        path = path.split('?', 1)[0]
        if '<' in path or '>' in path:
            return 'template', path, fragment
        if path.startswith('/'):
            if path.startswith(SITE_PREFIX):
                rel = path[len(SITE_PREFIX):]
            else:
                return 'outside', path, fragment
        else:
            rel = os.path.normpath(os.path.join(os.path.dirname(source_rel), path))
        if rel.startswith('..'):
            return 'outside', rel, fragment
        if rel == '' or rel.endswith('/'):
            rel = rel + 'index.html'
        # A value such as "$2" is a script placeholder, not a page.
        leaf = rel.rsplit('/', 1)[-1]
        if leaf and '/' not in rel and '.' not in leaf and not leaf.endswith('.html'):
            return 'skip', rel, fragment
        return 'internal', rel, fragment

    def check_target(self, source, kind, rel, fragment, original):
        if kind == 'skip':
            return
        if kind == 'external':
            return
        if kind == 'template':
            self.warn(
                '%s contains a template link (%s). It uses a placeholder, so it was not checked as a file.'
                % (source, original or rel)
            )
            return
        if kind == 'outside':
            self.error('%s links outside the repository: %s' % (source, original or rel))
            return
        path = os.path.join(ROOT, rel)
        if os.path.isdir(path):
            index = os.path.join(path, 'index.html')
            if os.path.isfile(index):
                rel = rel.rstrip('/') + '/index.html'
                path = index
            else:
                self.error('%s links to a folder with no index.html: %s' % (source, rel))
                return
        if not os.path.isfile(path):
            self.error('%s links to %s, and that file is not in the repository.' % (source, rel))
            return
        if fragment:
            ids = self.ids_of(rel)
            if ids is None or fragment not in ids:
                self.error(
                    '%s links to %s#%s, and that page has no matching id.'
                    % (source, rel, fragment)
                )

    def iter_link_sources(self):
        names = list(LINK_FILES)
        for name in sorted(os.listdir(ROOT)):
            if name.startswith('sitemap') and name.endswith('.xml'):
                names.append(name)
            elif name.startswith('llms-') and name.endswith('.txt') and name != 'llms-full.txt':
                names.append(name)
        names.extend(sorted(
            os.path.relpath(path, ROOT).replace(os.sep, '/')
            for path in glob.glob(os.path.join(ROOT, 'subject-map', '*.txt'))
        ))
        seen = set()
        for name in names:
            if name in seen:
                continue
            seen.add(name)
            path = os.path.join(ROOT, name)
            if os.path.isfile(path):
                yield name

    def check_links(self):
        checked = 0
        for rel in self.iter_link_sources():
            text = read_text(rel)
            targets = []
            if rel.endswith(('.html', '.xml', '.md')):
                for _quote, href in HREF_RE.findall(text):
                    targets.append(self.resolve_href(rel, href))
            for match in URL_RE.finditer(text):
                targets.append(self.resolve_site_path(match.group(0)))
            if rel == 'structured/INDEX.txt':
                for match in PART_LINE_RE.finditer(text):
                    targets.append(('internal', match.group(1), ''))
            # One warning per template URL, not one per repeated copy.
            reported_templates = set()
            seen_targets = set()
            for kind, target, fragment in targets:
                key = (kind, target, fragment)
                if key in seen_targets:
                    continue
                seen_targets.add(key)
                if kind == 'external' or kind == 'skip':
                    continue
                checked += 1
                if kind == 'template':
                    key = (rel, target)
                    if key in reported_templates:
                        continue
                    reported_templates.add(key)
                self.check_target(rel, kind, target, fragment, target)
        self.ok('Checked internal links in %d guide, sitemap, and list files (%d internal targets).' % (
            len(list(self.iter_link_sources())), checked))

    def check_copies(self):
        left = read_text('llms.txt')
        right = read_text('archive.txt')
        if left == right:
            self.ok('llms.txt and archive.txt are the same file, byte for byte.')
        else:
            self.error('llms.txt and archive.txt are not identical.')

    def check_counts(self, index_data, entries, messages_by_key, message_files, message_total, pieces, pages):
        groups = logical_groups(entries)
        by_key_entries = defaultdict(int)
        by_key_logical = defaultdict(int)
        for (collection, _stem, _total), items in groups:
            by_key_entries[collection] += len(items)
            by_key_logical[collection] += 1
        measured = {
            'entries': len(entries),
            'logical': len(groups),
            'messages': message_total,
        }
        stated_count = index_data.get('count')
        if stated_count != measured['entries']:
            self.error(
                'index.json says count is %s, but it contains %d conversation entries.'
                % (stated_count, measured['entries'])
            )
        else:
            self.ok('index.json count matches its %d entries.' % measured['entries'])

        self._check_prose_totals(measured)
        self._check_model_lines(by_key_entries, by_key_logical)
        self._check_manifest(measured, by_key_entries, by_key_logical, messages_by_key, pieces, pages)
        self.ok(
            'Measured from the files: %d entries, %d logical conversations, %d messages in %d structured conversation files.'
            % (measured['entries'], measured['logical'], measured['messages'], message_files)
        )
        return measured, by_key_entries, by_key_logical

    def _expect(self, source, label, stated, measured):
        if stated != measured:
            self.error('%s says %s is %s; the files contain %s.' % (source, label, stated, measured))

    def _check_prose_totals(self, measured):
        texts = {
            'ai.txt': read_text('ai.txt'),
            'llms.txt': read_text('llms.txt'),
            'README-for-AIs.md': read_text('README-for-AIs.md'),
        }
        # Each guide states the three headline numbers in its own sentence.
        patterns = {
            'ai.txt': re.compile(
                r'The archive has (\d+) entries\..*?are (\d+) logical conversations, with (\d+) messages',
                re.S,
            ),
            'llms.txt': re.compile(
                r'(\d+) archive entries, which are (\d+) logical conversations.*?with (\d+) messages',
                re.S,
            ),
            'README-for-AIs.md': re.compile(
                r'(\d+) entries\*\*.*?(\d+) logical conversations\*\* with \*\*(\d+) messages',
                re.S,
            ),
        }
        for name, pattern in patterns.items():
            match = pattern.search(texts[name])
            if not match:
                self.error('%s does not state the archive entry, logical conversation, and message totals in the expected sentence.' % name)
                continue
            stated = tuple(int(part) for part in match.groups())
            expected = (measured['entries'], measured['logical'], measured['messages'])
            if stated != expected:
                self.error(
                    '%s says %d entries, %d logical conversations, and %d messages; '
                    'index.json and the structured files have %d, %d, and %d.'
                    % ((name,) + stated + expected)
                )
            else:
                self.ok('%s states the same entry, logical conversation, and message totals as the files.' % name)

    def _check_model_lines(self, by_entries, by_logical):
        ai = read_text('ai.txt')
        found = {}
        for match in re.finditer(r'([A-Za-z][A-Za-z ()]*?) (\d+) / (\d+)', ai):
            name = match.group(1).strip().rstrip(',')
            if name in KEY_BY_NAME:
                found[name] = (int(match.group(2)), int(match.group(3)))
        for name in KEY_BY_NAME:
            if name not in found:
                self.error('ai.txt does not state entries / logical conversations for %s.' % name)
                continue
            key = KEY_BY_NAME[name]
            entries, logical = found[name]
            self._expect('ai.txt', '%s entries' % name, entries, by_entries[key])
            self._expect('ai.txt', '%s logical conversations' % name, logical, by_logical[key])

        llms = read_text('llms.txt')
        for match in re.finditer(
            r'^## (.+)\n\n(\d+) entries, (\d+) logical conversation',
            llms,
            re.M,
        ):
            name = match.group(1).strip()
            if name not in KEY_BY_NAME:
                self.warn('llms.txt has a model heading %r that is not one of the seven collections.' % name)
                continue
            key = KEY_BY_NAME[name]
            self._expect('llms.txt', '%s entries' % name, int(match.group(2)), by_entries[key])
            self._expect('llms.txt', '%s logical conversations' % name, int(match.group(3)), by_logical[key])

        readme = read_text('README-for-AIs.md')
        seen = set()
        for line in readme.splitlines():
            if not line.startswith('|'):
                continue
            cells = [cell.strip().strip('*').strip() for cell in line.strip('|').split('|')]
            if len(cells) < 3 or not cells[1].isdigit():
                continue
            name = cells[0]
            if name not in KEY_BY_NAME:
                continue
            seen.add(name)
            key = KEY_BY_NAME[name]
            self._expect('README-for-AIs.md', '%s entries' % name, int(cells[1]), by_entries[key])
            self._expect('README-for-AIs.md', '%s logical conversations' % name, int(cells[2]), by_logical[key])
        for name in KEY_BY_NAME:
            if name not in seen:
                self.error('README-for-AIs.md has no count row for %s.' % name)

    def _check_manifest(self, measured, by_entries, by_logical, messages_by_key, pieces, pages):
        data = json.loads(read_text('archive-manifest.json'))
        counts = data.get('counts') or {}
        self._expect('archive-manifest.json counts', 'archive entries', counts.get('archive_entries'), measured['entries'])
        self._expect('archive-manifest.json counts', 'logical conversations', counts.get('logical_conversations'), measured['logical'])
        self._expect('archive-manifest.json counts', 'messages', counts.get('messages'), measured['messages'])
        self._expect('archive-manifest.json', 'conversation_count', data.get('conversation_count'), measured['entries'])
        structured = data.get('structured_archive') or {}
        self._expect('archive-manifest.json structured_archive', 'archive entries', structured.get('archive_entries'), measured['entries'])
        self._expect('archive-manifest.json structured_archive', 'logical conversations', structured.get('logical_conversations'), measured['logical'])
        self._expect('archive-manifest.json structured_archive', 'messages', structured.get('messages'), measured['messages'])
        piece_total = sum(pieces.values())
        page_total = sum(pages.values())
        self._expect('archive-manifest.json counts', 'HTML article pieces', counts.get('html_article_pieces'), piece_total)
        self._expect('archive-manifest.json counts', 'numbered part pages', counts.get('numbered_part_pages'), page_total)
        self._expect('archive-manifest.json structured_archive', 'HTML article pieces', structured.get('html_article_pieces'), piece_total)

        for row in data.get('raw_transcripts') or []:
            name = row.get('model')
            key = row.get('key')
            if key not in NAME_BY_KEY:
                self.error('archive-manifest.json has an unknown raw transcript key %r.' % key)
                continue
            self._expect('archive-manifest.json %s' % name, 'archive entries', row.get('archive_entries'), by_entries[key])
            self._expect('archive-manifest.json %s' % name, 'logical conversations', row.get('logical_conversations'), by_logical[key])
            self._expect('archive-manifest.json %s' % name, 'messages', row.get('messages'), messages_by_key[key])
            self._expect('archive-manifest.json %s' % name, 'HTML article pieces', row.get('html_article_pieces'), pieces[key])
            self._expect('archive-manifest.json %s' % name, 'numbered part pages', row.get('numbered_part_pages'), pages[key])
            # The old "conversations" field held the piece count and was removed on 2026-11-15
            # because the name was misleading. html_article_pieces (checked above) is the explicit field.
            if 'conversations' in row:
                self.error('archive-manifest.json raw_transcripts %s has a "conversations" field again; '
                           'use html_article_pieces, archive_entries or logical_conversations.' % name)
            self._check_one_size('archive-manifest.json raw_transcripts %s' % name, row.get('url'), row.get('bytes'))

        for item in data.get('large_files') or []:
            self._check_one_size('archive-manifest.json large_files', item.get('url'), item.get('bytes'))
            if item.get('sha256'):
                kind, rel, _fragment = self.resolve_site_path(item.get('url', ''))
                if kind == 'internal' and file_size(rel) is not None and sha256_of(rel) != item['sha256']:
                    self.error('archive-manifest.json large_files gives a SHA-256 for %s that does not match the file.' % rel)
            if item.get('parts_list'):
                kind, rel, _fragment = self.resolve_site_path(item['parts_list'])
                if kind != 'internal' or file_size(rel) is None:
                    self.error('archive-manifest.json large_files names a missing parts list: %s' % item['parts_list'])

    def _check_one_size(self, source, url, stated):
        if not url or stated is None:
            self.error('%s is missing a url or a byte size.' % source)
            return
        kind, rel, _fragment = self.resolve_site_path(url)
        if kind != 'internal':
            self.error('%s names a size for a URL that is not in this repository: %s' % (source, url))
            return
        actual = file_size(rel)
        if actual is None:
            self.error('%s says %s is %s bytes, and that file is missing.' % (source, rel, stated))
        elif int(stated) != actual:
            self.error('%s says %s is %s bytes; the file is %d bytes.' % (source, rel, stated, actual))

    def check_stated_byte_phrases(self):
        """Exact 'N bytes' figures next to our files must match. Rounded 'about N MB' notes are not exact."""
        sources = (
            'ai.txt', 'llms.txt', 'archive.txt', 'README-for-AIs.md', 'archive-manifest.json',
        )
        seen = set()
        for rel in sources:
            lines = read_text(rel).splitlines()
            for index, line in enumerate(lines):
                for match in BYTE_RE.finditer(line):
                    stated = int(match.group(1).replace(',', ''))
                    window = '\n'.join(lines[max(0, index - 1):index + 2])
                    urls = [strip_url_tail(item) for item in URL_RE.findall(window)]
                    internal = []
                    for url in urls:
                        kind, path, _fragment = self.resolve_site_path(url)
                        if kind == 'internal':
                            internal.append(path)
                    if not internal:
                        continue
                    # Prefer a path mentioned on the same line as the number.
                    same = []
                    for url in URL_RE.findall(line):
                        kind, path, _fragment = self.resolve_site_path(strip_url_tail(url))
                        if kind == 'internal':
                            same.append(path)
                    chosen = same[-1] if same else internal[-1]
                    key = (rel, chosen, stated)
                    if key in seen:
                        continue
                    seen.add(key)
                    actual = file_size(chosen)
                    if actual is None:
                        self.error('%s says %s is %d bytes, and that file is missing.' % (rel, chosen, stated))
                    elif actual != stated:
                        self.error('%s says %s is %d bytes; the file is %d bytes.' % (rel, chosen, stated, actual))
        if seen:
            self.ok('Checked %d exact byte figures stated next to repository files.' % len(seen))
        else:
            self.warn('No exact byte figures were found next to repository URLs in the guide files.')

    def check_stated_sha256(self):
        """'SHA-256 <hex>' next to a repository URL (other than a parts list) must match that file."""
        checked = 0
        for rel in ('ai.txt', 'llms.txt', 'archive.txt', 'README-for-AIs.md'):
            for line in read_text(rel).splitlines():
                for match in SHA_RE.finditer(line):
                    targets = []
                    for url in URL_RE.findall(line):
                        kind, path, _fragment = self.resolve_site_path(strip_url_tail(url))
                        if kind == 'internal' and not path.startswith('parts/'):
                            targets.append(path)
                    if len(targets) != 1:
                        self.error('%s states a SHA-256 on a line without exactly one repository file URL: %s' % (rel, line[:120]))
                        continue
                    checked += 1
                    if file_size(targets[0]) is None:
                        self.error('%s gives a SHA-256 for %s, and that file is missing.' % (rel, targets[0]))
                    elif sha256_of(targets[0]) != match.group(1):
                        self.error('%s gives a SHA-256 for %s that does not match the file. Update it (see parts/INDEX.txt).'
                                   % (rel, targets[0]))
        self.ok('Checked %d SHA-256 checksums stated next to repository files.' % checked)

    # ------------------------------------------------------------ search index
    def check_search_index(self, rebuild=True):
        """Check the derived search index: listed files, size and line limits, NEXT chain, manifest, rebuild."""
        if not os.path.isfile(os.path.join(ROOT, 'search', 'SHARDS.txt')):
            self.error('search/SHARDS.txt is missing.')
            return
        start = len(self.errors)
        listed = []
        keys = {}
        for line in read_text('search/SHARDS.txt').splitlines():
            parts = line.split(' | ')
            if len(parts) == 6 and parts[0].startswith('search/terms/'):
                listed.append(parts[0])
                for key in parts[1].split(' '):
                    if key in keys:
                        self.error('search/SHARDS.txt lists the key %s twice.' % key)
                    keys[key] = parts[0]
                actual = file_size(parts[0])
                if actual is None:
                    self.error('search/SHARDS.txt lists %s, and that file is missing.' % parts[0])
                elif str(actual) != parts[5]:
                    self.error('search/SHARDS.txt says %s is %s bytes; the file is %d bytes.' % (parts[0], parts[5], actual))
        folder = os.path.join(ROOT, 'search', 'terms')
        on_disk = set('search/terms/' + n for n in os.listdir(folder)) if os.path.isdir(folder) else set()
        for rel in sorted(on_disk - set(listed)):
            self.error('%s is not listed in search/SHARDS.txt.' % rel)
        words = 0
        for rel in listed:
            if rel not in on_disk:
                continue
            text = read_text(rel)
            size = len(text.encode('utf-8'))
            lines = text.count('\n')
            if size > SEARCH_MAX_BYTES or lines > SEARCH_MAX_LINES:
                self.error('%s has %d bytes and %d lines; terms files must stay under %d bytes and %d lines.'
                           % (rel, size, lines, SEARCH_MAX_BYTES, SEARCH_MAX_LINES))
            words += sum(1 for l in text.split('\n')[5:] if l)
        # NEXT chain from the first terms file reaches every listed file once.
        seen = []
        rel = listed[0] if listed else None
        while rel and len(seen) <= len(listed):
            seen.append(rel)
            found = NEXT_RE.search(read_text(rel)) if rel in on_disk else None
            if not found:
                self.error('%s has no NEXT line.' % rel)
                break
            if found.group(1) == 'none':
                break
            kind, rel, _frag = self.resolve_site_path(found.group(1))
            if kind != 'internal':
                break
        if seen != listed:
            self.error('The NEXT chain of the search terms files does not visit the files in SHARDS.txt order.')
        try:
            info = json.loads(read_text('search/index.json'))
            manifest = json.loads(read_text('archive-manifest.json')).get('search_index') or {}
        except (OSError, ValueError) as exc:
            self.error('search/index.json or archive-manifest.json could not be read: %s' % exc)
            return
        counts = info.get('counts', {})
        if counts.get('words') != words:
            self.error('search/index.json says %s words; the terms files have %d.' % (counts.get('words'), words))
        for field, key in (('words', 'words'), ('terms_files', 'shards'), ('messages_indexed', 'messages'),
                           ('conversations_indexed', 'conversations')):
            if manifest.get(field) != counts.get(key):
                self.error('archive-manifest.json search_index %s is %s; search/index.json says %s.'
                           % (field, manifest.get(field), counts.get(key)))
        if len(self.errors) == start:
            self.ok('Search index: %d terms files, %d words; every file is listed, under %d bytes and %d lines, and on the NEXT chain.'
                    % (len(listed), words, SEARCH_MAX_BYTES, SEARCH_MAX_LINES))
        if not rebuild:
            self.warn('The search index was not compared with a fresh build (--skip-search-rebuild).')
            return
        sys.path.insert(0, os.path.join(ROOT, 'tools'))
        try:
            import build_search_index
            fresh = build_search_index.build()
            stale = build_search_index.stale_files(fresh)
        except Exception as exc:  # report, do not crash the whole check
            self.error('tools/build_search_index.py failed: %s' % exc)
            return
        for rel in stale:
            self.error('%s differs from a fresh build. Run: python3 tools/build_search_index.py' % rel)
        if not stale:
            self.ok('The search index equals a fresh run of tools/build_search_index.py (%d files).' % len(fresh))

    def check_search_examples(self):
        """Worked examples in the guides ("zero" is in search/terms/y.txt, CHATGPT-007:015*) must match the index."""
        claim_re = re.compile(r'"([a-z0-9]+)" is in (search/terms/[a-z0-9_]+\.txt)')
        ref_re = re.compile(r'\b([A-Z]+(?:-[A-Z]+)*-\d{3}):(\d{3})\*')
        checked = 0
        for rel in ('ai.txt', 'README-for-AIs.md'):
            for line in read_text(rel).splitlines():
                for word, terms in claim_re.findall(line):
                    checked += 1
                    if file_size(terms) is None:
                        self.error('%s says "%s" is in %s, and that file is missing. Update the example.' % (rel, word, terms))
                        continue
                    found = [l for l in read_text(terms).splitlines() if l.startswith(word + ' | ')]
                    if not found:
                        self.error('%s says "%s" is in %s, but it is not. Update the example (see search/README.txt).'
                                   % (rel, word, terms))
                        continue
                    refs = {}
                    for item in found[0].split(' | ', 5)[5].split('; '):
                        if ':' in item:
                            cid, seqs = item.split(':', 1)
                            refs[cid] = seqs.split(',')
                    for cid, seq in ref_re.findall(line):
                        if seq + '*' not in refs.get(cid, []):
                            self.error('%s gives %s:%s* for "%s", but the index line does not list it.' % (rel, cid, seq, word))
        self.ok('Checked %d worked search examples in the guides against the index.' % checked)

    def check_large_file_parts(self):
        """The parts lists must describe the large files exactly as they are now."""
        sys.path.insert(0, os.path.join(ROOT, 'tools'))
        try:
            import build_large_file_parts
            fresh, descs = build_large_file_parts.build()
            stale = build_large_file_parts.stale_files(fresh)
        except Exception as exc:
            self.error('tools/build_large_file_parts.py failed: %s' % exc)
            return
        for rel in stale:
            self.error('%s differs from a fresh build. Run: python3 tools/build_large_file_parts.py' % rel)
        if not stale:
            self.ok('The large-file parts lists equal a fresh run of tools/build_large_file_parts.py (%d large files, %d parts).'
                    % (len(descs), sum(len(d['parts']) for d in descs)))

    def check_index_ids(self, entries):
        """index.json must list exactly the archive entries that the structured transcripts were built from."""
        from collections import Counter
        index_ids = Counter(str(entry.get('id')) for entry in entries)
        dupes = sorted(k for k, v in index_ids.items() if v > 1)
        if dupes:
            self.error('index.json repeats entry ids: %s' % ', '.join(dupes[:10]))
        structured_ids = set()
        by_collection = defaultdict(int)
        for key, _name in MODELS:
            folder = os.path.join(ROOT, 'structured', key)
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                if not name.endswith('.txt'):
                    continue
                with open(os.path.join(folder, name), encoding='utf-8') as handle:
                    for line in handle:
                        if line.startswith('ORIGINAL_IDS: '):
                            for item in line[len('ORIGINAL_IDS: '):].strip().split(' | '):
                                structured_ids.add(item.strip())
                                by_collection[key] += 1
                            break
        missing = sorted(set(index_ids) - structured_ids)
        extra = sorted(structured_ids - set(index_ids))
        if missing:
            self.error('%d index.json entries are not in any structured transcript, e.g. %s' % (len(missing), ', '.join(missing[:5])))
        if extra:
            self.error('%d structured ORIGINAL_IDS are not in index.json, e.g. %s' % (len(extra), ', '.join(extra[:5])))
        index_by_collection = Counter(entry.get('collection') for entry in entries)
        for key, _name in MODELS:
            if index_by_collection.get(key, 0) != by_collection.get(key, 0):
                self.error('index.json has %d %s entries; the structured transcripts name %d.'
                           % (index_by_collection.get(key, 0), key, by_collection.get(key, 0)))
        if not dupes and not missing and not extra:
            self.ok('index.json lists exactly the %d entry ids named in the structured transcripts (ORIGINAL_IDS), per collection.'
                    % len(index_ids))

    def check_discovery_sync(self):
        """The discovery files must describe the same current entry points, size, and JavaScript rules."""
        start = len(self.errors)
        sources = ('ai.txt', 'README-for-AIs.md', 'llms.txt', 'archive-manifest.json', 'index.html')
        must = ('llms-full.txt', 'structured/INDEX.txt', 'subject-map/INDEX.txt', 'search/README.txt', 'parts/INDEX.txt')
        texts = dict((rel, read_text(rel)) for rel in sources)
        for rel, text in texts.items():
            for needle in must:
                if needle not in text:
                    self.error('%s does not mention %s, which the other discovery files describe.' % (rel, needle))
        size = file_size('llms-full.txt')
        expected = '%.1f MB' % (size / 1e6)
        mb_re = re.compile(r'about (\d+(?:\.\d+)?) MB')
        for rel in ('ai.txt', 'README-for-AIs.md', 'llms.txt', 'archive.txt', 'index.html'):
            for line in read_text(rel).splitlines():
                if 'llms-full' in line or 'Master' in line:
                    for found in mb_re.findall(line):
                        if '%s MB' % found != expected:
                            self.error('%s gives the master file as about %s MB; it is %s (%d bytes).'
                                       % (rel, found, expected, size))
        static_phrases = {
            'ai.txt': 'The home page itself is static HTML',
            'README-for-AIs.md': 'It is static HTML',
            'llms.txt': 'Home page (static HTML; only its README pop-up needs JavaScript)',
            'archive-manifest.json': 'The home page (index.html) is static HTML',
        }
        for rel, phrase in static_phrases.items():
            if phrase not in texts[rel]:
                self.error('%s no longer says the home page is static HTML (expected: %s).' % (rel, phrase))
        bad_js = re.compile(r'(?i)(home ?page|index\.html)[^.\n]{0,40}\b(requires|needs) (javascript|scripts)\b(?![^.\n]{0,10}pop-up)')
        for rel, text in texts.items():
            for line in text.splitlines():
                if bad_js.search(line) and 'pop-up' not in line:
                    self.error('%s says the home page needs JavaScript: %s' % (rel, line.strip()[:120]))
        if len(self.errors) == start:
            self.ok('Discovery files agree: each names the master file, structured index, subject map, search and parts lists; '
                    'the master file is about %s everywhere; all say the home page is static HTML.' % expected)

    def check_index_pages(self, entries):
        missing_parts = 0
        for entry in entries:
            parts = entry.get('parts') or []
            label = '%s (%s)' % (entry.get('title'), entry.get('id'))
            if not parts:
                missing_parts += 1
                self.error('index.json entry %s has no archive page in parts.' % label)
                continue
            for url in parts:
                kind, rel, fragment = self.resolve_site_path(url)
                if kind != 'internal':
                    self.error('index.json entry %s has a part URL that is not in this repository: %s' % (label, url))
                    continue
                path = os.path.join(ROOT, rel)
                if not os.path.isfile(path):
                    self.error('index.json entry %s points at %s, and that archive page is missing.' % (label, rel))
                    continue
                if fragment:
                    ids = self.ids_of(rel)
                    if not ids or fragment not in ids:
                        self.error(
                            'index.json entry %s points at %s#%s, and that anchor is not in the page.'
                            % (label, rel, fragment)
                        )
        if missing_parts == 0:
            self.ok('Every index.json entry has at least one part URL, and each part file and anchor is present.')

    # ------------------------------------------------------------ subject map
    def check_subject_map(self, rebuild=True):
        """Check the derived subject map: files, line limits, NEXT chains, counts, IDs, quotes, rebuild."""
        if not os.path.isfile(os.path.join(ROOT, SUBJECT_MAP_JSON)):
            self.ok('No subject-map.json, so the subject map checks were skipped.')
            return
        try:
            data = json.loads(read_text(SUBJECT_MAP_JSON))
        except ValueError as exc:
            self.error('subject-map.json is not valid JSON: %s' % exc)
            return
        start = len(self.errors)
        listed = set(data.get('files', []))
        on_disk = set('subject-map/' + n for n in os.listdir(os.path.join(ROOT, 'subject-map'))) \
            if os.path.isdir(os.path.join(ROOT, 'subject-map')) else set()
        for rel in sorted(listed):
            if not os.path.isfile(os.path.join(ROOT, rel)):
                self.error('subject-map.json lists %s, and that file is not in the repository.' % rel)
        for rel in sorted(on_disk - listed):
            self.error('%s is not listed in subject-map.json "files".' % rel)
        for rel in sorted(on_disk):
            if rel.endswith('.txt'):
                count = read_text(rel).count('\n')
                if count > SUBJECT_MAP_MAX_LINES:
                    self.error('%s has %d lines; subject-map files must have at most %d.'
                               % (rel, count, SUBJECT_MAP_MAX_LINES))
        overrides = data.get('overrides')
        if overrides and not os.path.isfile(os.path.join(ROOT, overrides)):
            self.error('subject-map.json names overrides file %s, and it is missing.' % overrides)

        # NEXT chains: INDEX.txt, then each topic file through its list parts.
        index_text = read_text('subject-map/INDEX.txt') if 'subject-map/INDEX.txt' in on_disk else ''
        if not index_text:
            self.error('subject-map/INDEX.txt is missing.')
        visited = set(['subject-map/INDEX.txt'])
        topics = data.get('topics', [])
        for topic in topics:
            rel = 'subject-map/%s.txt' % topic.get('key')
            hops = 0
            while rel and hops < 100:
                if rel in visited and hops:
                    self.error('subject-map NEXT chain loops at %s.' % rel)
                    break
                visited.add(rel)
                if not os.path.isfile(os.path.join(ROOT, rel)):
                    self.error('subject-map NEXT chain reaches a missing file: %s' % rel)
                    break
                found = NEXT_RE.search(read_text(rel))
                if not found:
                    self.error('%s has no NEXT line.' % rel)
                    break
                target = found.group(1)
                if target == 'none':
                    break
                kind, target_rel, _frag = self.resolve_site_path(target)
                rel = target_rel if kind == 'internal' else None
                hops += 1
        for rel in sorted(x for x in on_disk if x.endswith('.txt')):
            if rel not in visited:
                self.error('%s is not reached by any subject-map NEXT chain.' % rel)

        # Counts: JSON totals against the conversation rows, the INDEX table, the topic files and the HTML page.
        html = read_text('subject-map.html') if os.path.isfile(os.path.join(ROOT, 'subject-map.html')) else ''
        quotes_checked = 0
        texts = {}
        for topic in topics:
            key = topic.get('key')
            rows = topic.get('conversations', [])
            totals = topic.get('totals', {})
            measured = dict(
                conversations=len(rows),
                messages=sum(r['messages'] for r in rows),
                alex_own_words=sum(r['alex_own_words'] for r in rows),
                alex_labeled=sum(r['alex_labeled'] for r in rows),
                ai_messages=sum(r['ai_messages'] for r in rows),
            )
            for name, value in measured.items():
                if totals.get(name) != value:
                    self.error('subject-map.json topic %s states %s %s, but its rows add up to %s.'
                               % (key, name, totals.get(name), value))
            if measured['messages'] != measured['alex_labeled'] + measured['ai_messages']:
                self.error('subject-map.json topic %s: messages is not Alex-labeled plus AI.' % key)
            row = '  %s | %s | %s | %d | %d | %d |' % (
                key, topic.get('label'), topic.get('method'), totals.get('conversations', -1),
                totals.get('messages', -1), totals.get('alex_own_words', -1))
            if row not in index_text:
                self.error('subject-map/INDEX.txt does not state the counts in subject-map.json for topic %s.' % key)
            topic_rel = 'subject-map/%s.txt' % key
            if os.path.isfile(os.path.join(ROOT, topic_rel)):
                topic_text = read_text(topic_rel)
                if 'Conversations with a match: %d of %d' % (totals.get('conversations', -1),
                                                            data.get('conversations_total', -1)) not in topic_text:
                    self.error('%s does not state the conversation count in subject-map.json.' % topic_rel)
                head = '\n'.join(topic_text.split('\n')[:5])
                if 'derived index' not in head or 'originals unchanged' not in head:
                    self.error('%s does not state "derived index ... originals unchanged" in its header.' % topic_rel)
            if html and ('id="%s"' % key) not in html:
                self.error('subject-map.html has no section id="%s".' % key)
            # IDs and quotes against the structured transcripts.
            for r in rows:
                rel = self.resolve_site_path(r.get('text', ''))
                if rel[0] != 'internal' or not os.path.isfile(os.path.join(ROOT, rel[1])):
                    self.error('subject-map topic %s row %s has a missing text file.' % (key, r.get('id')))
                    continue
                if rel[1] not in texts:
                    texts[rel[1]] = read_text(rel[1])
                body = texts[rel[1]]
                if 'CONVERSATION: %s\n' % r['id'] not in body and ('BEGIN MESSAGE %s-' % r['id']) not in body:
                    self.error('subject-map topic %s: %s is not the conversation in %s.' % (key, r['id'], rel[1]))
                for mid in r.get('message_ids', []):
                    if ('MESSAGE: %s\n' % mid) not in body:
                        self.error('subject-map topic %s: message %s is not in %s.' % (key, mid, rel[1]))
            quotes = list(topic.get('alex_first_mention_by_ai', []))
            if topic.get('first_in_alex_own_words'):
                quotes.append(topic['first_in_alex_own_words'])
            for q in quotes:
                rel = self.resolve_site_path(q.get('text', ''))
                if rel[0] != 'internal' or not os.path.isfile(os.path.join(ROOT, rel[1])):
                    self.error('subject-map topic %s quote %s has a missing text file.' % (key, q.get('message')))
                    continue
                body = texts.get(rel[1]) or read_text(rel[1])
                begin = body.find('----- BEGIN MESSAGE %s -----' % q['message'])
                if begin < 0:
                    begin = body.find('----- BEGIN MESSAGE %s-' % q['message'])
                end = body.find('----- END MESSAGE %s' % q['message'], begin)
                if begin < 0 or end < 0 or q['quote'] not in body[begin:end]:
                    self.error('subject-map topic %s: the quote for %s is not exact text of that message.'
                               % (key, q['message']))
                elif len(q['quote'].split()) > 25:
                    self.error('subject-map topic %s: the quote for %s has more than 25 words.' % (key, q['message']))
                quotes_checked += 1
        try:
            manifest_topics = json.loads(read_text('archive-manifest.json')).get('subject_map', {}).get('topics')
        except (OSError, ValueError):
            manifest_topics = None
        if manifest_topics is not None:
            expected = [(t.get('key'), t['totals']['conversations'], t['totals']['messages'], t['totals']['alex_own_words'])
                        for t in topics]
            stated = [(t.get('key'), t.get('conversations'), t.get('messages'), t.get('alex_own_words_messages'))
                      for t in manifest_topics]
            if stated != expected:
                self.error('archive-manifest.json subject_map topic counts differ from subject-map.json.')
        if len(self.errors) == start:
            self.ok('Subject map: %d files, %d topics; line limits, NEXT chains, counts, IDs and %d quotes agree.'
                    % (len(listed), len(topics), quotes_checked))
        if not rebuild:
            self.warn('The subject map was not compared with a fresh build (--skip-subject-map-rebuild).')
            return
        sys.path.insert(0, os.path.join(ROOT, 'tools'))
        try:
            import build_subject_map
            fresh = build_subject_map.build()
        except Exception as exc:  # report, do not crash the whole check
            self.error('tools/build_subject_map.py failed: %s' % exc)
            return
        stale = [rel for rel, text in sorted(fresh.items())
                 if not os.path.isfile(os.path.join(ROOT, rel)) or read_text(rel) != text]
        for rel in stale:
            self.error('%s differs from a fresh build. Run: python3 tools/build_subject_map.py' % rel)
        if not stale:
            self.ok('The subject map files equal a fresh run of tools/build_subject_map.py (%d files).' % len(fresh))

    def report(self, measured):
        lines = [
            '# Site link and consistency check',
            '',
            'This report was produced by tools/check_site.py from the files in the working tree. It does not use the network.',
            '',
            'Measured from index.json and the structured transcripts: %d archive entries, %d logical conversations, %d messages.'
            % (measured['entries'], measured['logical'], measured['messages']),
            '',
            'Errors: %d. Warnings: %d.' % (len(self.errors), len(self.warnings)),
            '',
            '## Errors',
            '',
        ]
        if self.errors:
            lines.extend('- %s' % item for item in self.errors)
        else:
            lines.append('None.')
        lines.extend(['', '## Warnings', ''])
        if self.warnings:
            lines.extend('- %s' % item for item in self.warnings)
        else:
            lines.append('None.')
        lines.extend(['', '## What passed', ''])
        lines.extend('- %s' % item for item in self.passed)
        lines.append('')
        lines.append('Approximate sizes such as "about 39.7 MB" or "about 3 KB" are notes, not exact byte claims, so they were not compared.')
        lines.append('')
        text = '\n'.join(lines)
        with open(REPORT_PATH, 'w', encoding='utf-8') as handle:
            handle.write(text)
        print(text)
        return text


def main():
    checker = Checker()
    _index, entries = load_index()
    messages_by_key, message_files, message_total = message_counts()
    pieces, pages = article_and_page_counts()
    measured, _by_entries, _by_logical = checker.check_counts(
        _index, entries, messages_by_key, message_files, message_total, pieces, pages,
    )
    checker.check_copies()
    checker.check_stated_byte_phrases()
    checker.check_links()
    checker.check_index_pages(entries)
    checker.check_index_ids(entries)
    checker.check_discovery_sync()
    checker.check_subject_map(rebuild='--skip-subject-map-rebuild' not in sys.argv)
    checker.check_stated_sha256()
    checker.check_search_index(rebuild='--skip-search-rebuild' not in sys.argv)
    checker.check_search_examples()
    checker.check_large_file_parts()
    checker.report(measured)
    return 1 if checker.errors else 0


if __name__ == '__main__':
    sys.exit(main())
