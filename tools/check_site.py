#!/usr/bin/env python3
"""Offline link and consistency checks for the My Titanium Brothers repository.

Standard library only. Reads the working tree, writes tools/CHECK-REPORT.md,
prints the same report, and exits 1 when it finds an error. Warnings do not
fail the run. This script does not modify conversation, raw, full-text,
structured, or introduction files.
"""
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
)


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
            # The older "conversations" field is the piece count, kept on purpose.
            self._expect('archive-manifest.json %s' % name, 'raw section count (conversations field)', row.get('conversations'), pieces[key])
            self._check_one_size('archive-manifest.json raw_transcripts %s' % name, row.get('url'), row.get('bytes'))

        for item in data.get('large_files') or []:
            self._check_one_size('archive-manifest.json large_files', item.get('url'), item.get('bytes'))

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
    checker.report(measured)
    return 1 if checker.errors else 0


if __name__ == '__main__':
    sys.exit(main())
