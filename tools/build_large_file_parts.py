#!/usr/bin/env python3
"""Build parts lists for the large files: a reading aid for AIs with fetch limits.

Standard library only. For every published text file of LARGE_BYTES or more (and every
structured/<collection>/<ID>.txt conversation file of STRUCTURED_LARGE_BYTES or more), writes
parts/<path with / replaced by __>.txt with the exact size, line count, SHA-256, the
file's last line (an end-of-file marker), and byte ranges of about PART_BYTES (STRUCTURED_PART_BYTES for conversation files)
that end at a line break, each with its own SHA-256. Also writes parts/INDEX.txt and
parts/index.json. The large files themselves are never changed or copied.

Usage:
  python3 tools/build_large_file_parts.py                  write the files
  python3 tools/build_large_file_parts.py --check          build in memory and report files that differ
  python3 tools/build_large_file_parts.py --update-guides  also replace outdated SHA-256 values that the
                                                           guide files state for the large files (ai.txt,
                                                           llms.txt, archive.txt, README-for-AIs.md,
                                                           index.html, archive-manifest.json). Byte sizes
                                                           stated in the guides are not changed.
"""
import hashlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = 'https://uracrom.github.io/My-Titanium-Brothers/'
RAW = 'https://raw.githubusercontent.com/Uracrom/My-Titanium-Brothers/main/'
LAST_UPDATED = '2026-11-15'
OUT_DIR = 'parts'
LARGE_BYTES = 900000
PART_BYTES = 500000
# One-conversation files in structured/<collection>/ get a parts list from a lower size, with smaller
# parts, because they are the files AIs fetch most often (the structured indexes list every file's size).
STRUCTURED_LARGE_BYTES = 250000
STRUCTURED_PART_BYTES = 100000
STRUCTURED_COLLECTIONS = ('chatgpt', 'chatgpt-whatsapp', 'claude', 'copilot', 'deepseek', 'gemini', 'grok')
EXTENSIONS = ('.txt', '.md', '.html', '.json', '.xml')
SKIP_DIRS = ('.git', '.github', 'tools', OUT_DIR, 'search', 'node_modules')
SHOW = 70


def large_files():
    found = []
    for base, dirs, names in os.walk(ROOT):
        rel_base = os.path.relpath(base, ROOT).replace(os.sep, '/')
        dirs[:] = sorted(d for d in dirs if not (rel_base == '.' and d in SKIP_DIRS))
        for name in names:
            if not name.endswith(EXTENSIONS):
                continue
            rel = name if rel_base == '.' else rel_base + '/' + name
            size = os.path.getsize(os.path.join(ROOT, rel))
            if size >= threshold(rel):
                found.append((rel, size))
    found.sort(key=lambda item: (-item[1], item[0]))
    return found


def is_conversation_file(rel):
    bits = rel.split('/')
    return len(bits) == 3 and bits[0] == 'structured' and bits[1] in STRUCTURED_COLLECTIONS and rel.endswith('.txt')


def threshold(rel):
    return STRUCTURED_LARGE_BYTES if is_conversation_file(rel) else LARGE_BYTES


def part_bytes(rel):
    return STRUCTURED_PART_BYTES if is_conversation_file(rel) else PART_BYTES


def parts_name(rel):
    return '%s/%s.txt' % (OUT_DIR, rel.replace('/', '__'))


def show(raw_line):
    text = raw_line.decode('utf-8', errors='replace').rstrip('\r\n').replace('\t', ' ')
    # Words excluded from the search index at the author's request are not quoted here
    # either (see EXCLUDED_STEMS in tools/build_search_index.py). The file is unchanged.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_search_index import EXCLUDED_STEMS
    if any(stem in text.lower() for stem in EXCLUDED_STEMS):
        return '(line start not quoted; use START_BYTE)'
    if len(text) > SHOW:
        text = text[:SHOW] + '...'
    return text if text.strip() else '(blank line)'


def describe(rel):
    with open(os.path.join(ROOT, rel), 'rb') as handle:
        data = handle.read()
    lines = data.split(b'\n')
    ends_newline = data.endswith(b'\n')
    if ends_newline:
        lines = lines[:-1]
    last_nonempty = next((l for l in reversed(lines) if l.strip()), b'')
    parts = []
    start = 0
    line_no = 1
    size = part_bytes(rel)
    while start < len(data):
        end = min(start + size, len(data))
        if end < len(data):
            cut = data.rfind(b'\n', start, end)
            if cut < 0:
                cut = data.find(b'\n', end)
                cut = len(data) - 1 if cut < 0 else cut
            end = cut + 1
        chunk = data[start:end]
        n_lines = chunk.count(b'\n') + (0 if chunk.endswith(b'\n') else 1)
        first = chunk.split(b'\n', 1)[0]
        parts.append(dict(start=start, end=end - 1, bytes=end - start, first_line=line_no,
                          last_line=line_no + n_lines - 1, sha256=hashlib.sha256(chunk).hexdigest(),
                          first=show(first)))
        line_no += n_lines
        start = end
    return dict(path=rel, bytes=len(data), lines=len(lines), sha256=hashlib.sha256(data).hexdigest(),
                ends_with_newline=ends_newline, last_line=show(last_nonempty),
                tail_hex=data[-16:].hex(), part_bytes=size, parts=parts)


def parts_file(d):
    rel = d['path']
    out = [
        'LARGE FILE PARTS - %s (derived reading aid, generated by tools/build_large_file_parts.py; the file itself is unchanged)' % rel,
        'FILE: %s%s' % (SITE, rel),
        'RAW: %s%s' % (RAW, rel),
        'BYTES: %d' % d['bytes'],
        'LINES: %d' % d['lines'],
        'SHA256: %s' % d['sha256'],
        'ENDS_WITH_NEWLINE: %s' % ('yes' if d['ends_with_newline'] else 'no'),
        'LAST_16_BYTES_HEX: %s' % d['tail_hex'],
        'END-OF-FILE MARKER (last non-empty line, first %d characters): %s' % (SHOW, d['last_line']),
        'PARTS: %d (about %d bytes each, every part ends at a line break)' % (len(d['parts']), d['part_bytes']),
        '',
        'HOW TO READ THIS FILE IN PIECES',
        '  Ask for one part at a time with an HTTP Range header, END inclusive:  Range: bytes=START-END',
        '  Example: curl -r %d-%d %s%s' % (d['parts'][0]['start'], d['parts'][0]['end'], SITE, rel),
        '  GitHub Pages and raw.githubusercontent.com both answer 206 Partial Content with exactly those bytes.',
        '  A part starts at the beginning of a line and ends with a line break, so lines are never cut.',
        '  If your tool cannot send a Range header, use the smaller files instead: llms.txt, the',
        '  numbered archive pages, or structured/ (one file per conversation, most under 200 KB).',
        '',
        'HOW TO KNOW YOU HAVE IT ALL, AND HOW TO RESUME',
        '  A complete read has BYTES bytes and LINES line breaks, and ends with the END-OF-FILE MARKER line.',
        '  If your copy is shorter, it was cut. Count the bytes you have (N) and ask for Range: bytes=N- ,',
        '  or compare the end of your copy with the START OF FIRST LINE column below to find the first part',
        '  you did not get completely, and ask for that part again from its START_BYTE.',
        '  Each part has its own SHA256, so a part can be checked on its own.',
        '',
        'PART | START_BYTE | END_BYTE | BYTES | START_LINE | END_LINE | SHA256 | START OF FIRST LINE',
    ]
    for i, p in enumerate(d['parts'], 1):
        out.append('%03d | %d | %d | %d | %d | %d | %s | %s' % (
            i, p['start'], p['end'], p['bytes'], p['first_line'], p['last_line'], p['sha256'], p['first']))
    out.append('')
    out.append('END OF PARTS LIST (%d parts, %d bytes in total)' % (len(d['parts']), d['bytes']))
    return '\n'.join(out) + '\n'


def index_file(descs):
    out = [
        'LARGE FILES - PARTS LISTS FOR READING IN PIECES (derived reading aid, generated by tools/build_large_file_parts.py; the files themselves are unchanged)',
        'Last updated %s. Every published text file of %d bytes or more is listed, largest first, and so is every' % (LAST_UPDATED, LARGE_BYTES),
        'one-conversation file structured/<collection>/<ID>.txt of %d bytes or more.' % STRUCTURED_LARGE_BYTES,
        'Each PARTS LIST gives exact byte ranges (about %d bytes each; %d for one-conversation files; ending at line breaks) for HTTP Range requests,' % (PART_BYTES, STRUCTURED_PART_BYTES),
        'a SHA-256 for the whole file and for every part, and an end-of-file marker, so a reader can tell a cut-off read',
        'from a complete one and resume where it stopped. Both %s and %s support Range requests.' % (SITE, RAW),
        'No copies are made: ask for byte ranges of the original file.',
        '',
        'FILE | BYTES | LINES | PARTS | SHA256 | PARTS LIST',
    ]
    for d in descs:
        out.append('%s | %d | %d | %d | %s | %s%s' % (
            d['path'], d['bytes'], d['lines'], len(d['parts']), d['sha256'], SITE, parts_name(d['path'])))
    out.append('')
    out.append('END OF LIST (%d files)' % len(descs))
    return '\n'.join(out) + '\n'


def build():
    descs = [describe(rel) for rel, _size in large_files()]
    files = {}
    for d in descs:
        files[parts_name(d['path'])] = parts_file(d)
    files['%s/INDEX.txt' % OUT_DIR] = index_file(descs)
    files['%s/index.json' % OUT_DIR] = json.dumps(dict(
        name='My Titanium Brothers large-file parts lists',
        kind='derived reading aid, generated by tools/build_large_file_parts.py; the files themselves are unchanged',
        last_updated=LAST_UPDATED,
        threshold_bytes=LARGE_BYTES,
        part_bytes=PART_BYTES,
        structured_conversation_threshold_bytes=STRUCTURED_LARGE_BYTES,
        structured_conversation_part_bytes=STRUCTURED_PART_BYTES,
        range_requests='Send Range: bytes=START-END (END inclusive). GitHub Pages and raw.githubusercontent.com answer 206 Partial Content.',
        files=[dict(url=SITE + d['path'], raw=RAW + d['path'], bytes=d['bytes'], lines=d['lines'], sha256=d['sha256'],
                    ends_with_newline=d['ends_with_newline'], end_of_file_marker=d['last_line'],
                    parts_list=SITE + parts_name(d['path']),
                    parts=[dict(start=p['start'], end=p['end'], bytes=p['bytes'], first_line=p['first_line'],
                                last_line=p['last_line'], sha256=p['sha256']) for p in d['parts']])
               for d in descs],
    ), indent=1, ensure_ascii=False) + '\n'
    return files, descs


def stale_files(files):
    on_disk = set()
    folder = os.path.join(ROOT, OUT_DIR)
    if os.path.isdir(folder):
        on_disk = set('%s/%s' % (OUT_DIR, n) for n in os.listdir(folder))
    stale = []
    for rel, text in sorted(files.items()):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            stale.append(rel)
            continue
        with open(path, encoding='utf-8') as handle:
            if handle.read() != text:
                stale.append(rel)
    stale.extend(sorted(on_disk - set(files)))
    return stale


GUIDES = ('ai.txt', 'llms.txt', 'archive.txt', 'README-for-AIs.md', 'index.html', 'archive-manifest.json')


def update_guides(descs):
    """Replace an outdated SHA-256 stated next to a large file's URL with the current one."""
    import re
    current = dict((d['path'], d['sha256']) for d in descs)
    pattern = re.compile(r'(%s([^\s"()<>]+)[^\n]*?(?:SHA-256 |"sha256": "))([0-9a-f]{64})' % re.escape(SITE))
    changed = []
    for rel in GUIDES:
        path = os.path.join(ROOT, rel)
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        if rel == 'archive-manifest.json':
            data = json.loads(text)
            for item in data.get('large_files') or []:
                target = item.get('url', '')[len(SITE):]
                if target in current and item.get('sha256') and item['sha256'] != current[target]:
                    item['sha256'] = current[target]
            new = json.dumps(data, indent=1, ensure_ascii=True)
        else:
            new = pattern.sub(lambda m: m.group(1) + current.get(m.group(2), m.group(3)), text)
        if new != text:
            with open(path, 'w', encoding='utf-8', newline='\n') as handle:
                handle.write(new)
            changed.append(rel)
    return changed


def main(argv):
    files, descs = build()
    if '--check' in argv:
        stale = stale_files(files)
        for rel in stale:
            print('differs from a fresh build: %s' % rel)
        if stale:
            print('Run: python3 tools/build_large_file_parts.py')
            return 1
        print('The large-file parts lists equal a fresh build (%d files, %d large files).' % (len(files), len(descs)))
        return 0
    folder = os.path.join(ROOT, OUT_DIR)
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):
        if '%s/%s' % (OUT_DIR, name) not in files:
            os.remove(os.path.join(folder, name))
    for rel, text in files.items():
        with open(os.path.join(ROOT, rel), 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
    print('Wrote %d files for %d large files.' % (len(files), len(descs)))
    if '--update-guides' in argv:
        changed = update_guides(descs)
        print('Updated SHA-256 values in: %s' % (', '.join(changed) or 'nothing (all current)'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
