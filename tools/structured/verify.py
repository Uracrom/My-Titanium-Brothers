#!/usr/bin/env python3
"""Check structured transcripts against original HTML and the known speaker regressions."""
import collections
import glob
import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.dirname(__file__))
from build import BOOK_NOTE, classify_line  # noqa: E402


def load_src():
    src = {}
    for path in glob.glob(os.path.join(ROOT, 'archive-*-*.html')):
        if not re.search(r'-\d+\.html$', path):
            continue
        text = open(path, encoding='utf-8').read()
        for match in re.finditer(r'<article id="([^"]+)">(.*?)</article>', text, re.S):
            pre = re.search(r'<pre>(.*?)</pre>', match.group(2), re.S)
            src[os.path.basename(path) + '#' + match.group(1)] = html.unescape(pre.group(1))
    return src


def check_reconstruction():
    src = load_src()
    conv = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))['conversations']
    res = collections.Counter()
    mism = []
    seen_ids = set()
    seen_urls = []
    follows = set()
    ofs = set()
    msgids = set()
    opening = collections.Counter()
    label_in_content = []
    alex_owns_known = []
    for fp in sorted(glob.glob(os.path.join(ROOT, 'structured', '*', '*.txt'))):
        if os.path.basename(os.path.dirname(fp)) in ('index', 'flags'):
            continue
        blob = open(fp, encoding='utf-8').read().split('\n')
        cid = blob[0].split(': ', 1)[1]
        res['files'] += 1
        for line in blob:
            if line.startswith('SOURCE_ENTRY '):
                seen_ids.add(line.split('ORIGINAL_ID=')[1].split(' ;')[0])
        segs = []
        i = 0
        cur = None
        first_msg = None
        lastseq = 0
        while i < len(blob):
            line = blob[i]
            if line.startswith('===== SOURCE SEGMENT'):
                art = line.split('SOURCE_ARTICLE ')[1].split(' |')[0]
                cur = [art, []]
                segs.append(cur)
                seen_urls.append(art)
            elif line.startswith('----- BEGIN SEGMENT PREAMBLE'):
                i += 1
                while blob[i] != '----- END SEGMENT PREAMBLE -----':
                    cur[1].append(blob[i])
                    i += 1
            elif line.startswith('----- BEGIN MESSAGE '):
                block = line[len('----- BEGIN MESSAGE '):-len(' -----')]
                header = {}
                i += 1
                while blob[i] != 'CONTENT:':
                    if blob[i] == 'CONTINUATION OF:':
                        ofs.add((blob[i + 1][len('MESSAGE ID: '):], blob[i + 2][len('PREVIOUS PART: '):], block))
                    if ': ' in blob[i] and not blob[i].startswith('CONTINUATION'):
                        key, val = blob[i].split(': ', 1)
                        header.setdefault(key, val)
                    i += 1
                i += 1
                label = header['SPEAKER_LABEL_IN_ORIGINAL']
                if label != '(none)':
                    cur[1].append(label)
                content_start = i
                while blob[i] != 'END CONTENT':
                    if blob[i] not in ('EMBEDDED MATERIAL:', 'END EMBEDDED MATERIAL') and not blob[i].startswith('ORIGINAL SPEAKER: '):
                        cur[1].append(blob[i])
                        if classify_line(blob[i]) and classify_line(blob[i])[1] == 'label':
                            label_in_content.append((cid, header.get('MESSAGE'), blob[i]))
                    i += 1
                if i + 1 < len(blob) and blob[i + 1] == 'CONTINUATION FOLLOWS:':
                    follows.add((blob[i + 2][len('MESSAGE ID: '):], blob[i + 3][len('NEXT PART: '):], block))
                seq = int(header['SEQUENCE'])
                mid = header['MESSAGE']
                if 'PART' not in header or header['PART'].startswith('A'):
                    if seq != lastseq + 1:
                        res['seq_errors'] += 1
                    lastseq = seq
                    if mid in msgids:
                        res['dup_msg'] += 1
                    msgids.add(mid)
                if first_msg is None:
                    first_msg = 1
                    opening[(header['SPEAKER'], header['SPEAKER_KIND'], label == '(none)')] += 1
                if header['SPEAKER'] == 'ALEX' and header['SPEAKER_KIND'] != 'HUMAN':
                    res['alex_not_human'] += 1
                if header['SPEAKER'] != 'ALEX' and header['SPEAKER_KIND'] == 'HUMAN':
                    res['non_alex_human'] += 1
            i += 1
        for art, lines in segs:
            rebuilt = '\n'.join(lines)
            if rebuilt != src[art]:
                a, b = rebuilt, src[art]
                k = next((j for j in range(min(len(a), len(b))) if a[j] != b[j]), min(len(a), len(b)))
                mism.append((cid, art, repr(a[max(0, k - 40):k + 40]), repr(b[max(0, k - 40):k + 40])))
            else:
                res['segments_match'] += 1
    pair_f = {(m, n) for m, n, _b in follows}
    pair_o = {(m, b) for m, p, b in ofs}
    # follows stores (msg, next, block); ofs stores (msg, prev, block)
    # pairing is (message id, next block) vs (message id, this block) where this block is the next.
    fn = {(m, n) for m, n, _b in follows}
    on = {(m, b) for m, _p, b in ofs}
    unp = [item for item in fn if item not in on] + [item for item in on if item not in fn]
    allurls = [url.split('/')[-1] for entry in conv for url in entry['parts']]
    return {
        'res': dict(res),
        'mism': mism,
        'ids': len(seen_ids & {entry['id'] for entry in conv}),
        'conv': len(conv),
        'urls': len(seen_urls),
        'url_set_match': sorted(seen_urls) == sorted(allurls),
        'dup_urls': len(seen_urls) - len(set(seen_urls)),
        'follows': len(follows),
        'ofs': len(ofs),
        'unpaired': unp,
        'opening': {str(k): v for k, v in opening.items()},
        'msgs': len(msgids),
        'label_in_content': label_in_content[:10],
        'label_in_content_count': len(label_in_content),
    }


def message_blocks(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    blocks = []
    i = 0
    while i < len(lines):
        if lines[i].startswith('----- BEGIN MESSAGE '):
            header = {}
            i += 1
            while lines[i] != 'CONTENT:':
                if ': ' in lines[i]:
                    key, val = lines[i].split(': ', 1)
                    header.setdefault(key, val)
                i += 1
            i += 1
            content = []
            while lines[i] != 'END CONTENT':
                content.append(lines[i])
                i += 1
            blocks.append((header, content))
        i += 1
    return blocks


def check_regressions():
    errors = []
    grok118 = message_blocks(os.path.join(ROOT, 'structured/grok/GROK-118.txt'))
    ask = [b for b in grok118 if any(line.startswith('I asked Copilot to gather everything we talked about logic') for line in b[1])]
    if len(ask) != 1 or ask[0][0]['SPEAKER'] != 'ALEX':
        errors.append('GROK-118 ask line is not a single ALEX message')
    else:
        if any(line.strip() == 'Copilot' for line in ask[0][1]):
            errors.append('GROK-118 Alex message still contains a Copilot label line')
        if any('Absolutely' in line and 'you’re right to ask' in line for line in ask[0][1]):
            errors.append('GROK-118 Copilot paste is still inside the Alex message')
    cop = [b for b in grok118 if any(line.startswith('Absolutely') and 'you’re right to ask' in line for line in b[1])]
    if len(cop) != 1 or cop[0][0]['SPEAKER'] != 'COPILOT' or cop[0][0]['SPEAKER_KIND'] != 'AI':
        errors.append('GROK-118 Copilot paste is not SPEAKER COPILOT / AI')
    elif cop[0][0].get('EMBED_STATUS') != 'EMBEDDED_PASTE':
        errors.append('GROK-118 Copilot paste missing EMBEDDED_PASTE')
    else:
        text = '\n'.join(cop[0][1])
        if 'EMBEDDED MATERIAL:' not in text or 'You said:' not in text:
            errors.append('GROK-118 Copilot message missing You said transcript marker')
        if 'You said this twice' not in text.split('EMBEDDED MATERIAL:')[0]:
            errors.append('GROK-118 prose "You said this twice" should stay Copilot text outside the transcript region')
    grok43 = message_blocks(os.path.join(ROOT, 'structured/grok/GROK-043.txt'))
    paste = [b for b in grok43 if any("I'm pasting them below." in line for line in b[1])]
    if len(paste) != 1 or paste[0][0]['SPEAKER'] != 'ALEX':
        errors.append('GROK-043 paste cue is not a single ALEX message')
    elif any(line.startswith('Hello Alex. Your invitation') for line in paste[0][1]):
        errors.append('GROK-043 Newborn text is still inside the Alex message')
    newborn = [b for b in grok43 if any(line.startswith('Hello Alex. Your invitation') for line in b[1])]
    if len(newborn) != 1 or newborn[0][0]['SPEAKER'] != 'NEWBORN' or newborn[0][0]['SPEAKER_KIND'] != 'AI':
        errors.append('GROK-043 Newborn hello is not SPEAKER NEWBORN / AI')
    elif newborn[0][0].get('EMBED_STATUS') != 'EMBEDDED_PASTE':
        errors.append('GROK-043 Newborn paste missing EMBEDDED_PASTE')
    claude = message_blocks(os.path.join(ROOT, 'structured/claude/CLAUDE-064.txt'))
    question = [b for b in claude if any('But you wrote only the last text' in line for line in b[1])]
    if len(question) != 1 or question[0][0]['SPEAKER'] != 'ALEX':
        errors.append('CLAUDE-064 question is not a single ALEX message')
    elif any(line.startswith('You’re right') for line in question[0][1]):
        errors.append('CLAUDE-064 Copilot reply is still inside the Alex message')
    elif 'CONTINUATION FOLLOWS:' in open(os.path.join(ROOT, 'structured/claude/CLAUDE-064.txt'), encoding='utf-8').read().split('But you wrote only the last text')[1].split('----- END MESSAGE')[0]:
        errors.append('CLAUDE-064 Alex question still continues into the next page')
    reply = [b for b in claude if any(line.startswith('You’re right') for line in b[1])]
    if len(reply) != 1 or reply[0][0]['SPEAKER'] != 'COPILOT' or reply[0][0]['SPEAKER_KIND'] != 'AI':
        errors.append('CLAUDE-064 reply is not SPEAKER COPILOT / AI, got %s' % (reply[0][0] if reply else None))
    elif reply[0][0].get('PART', '').startswith('B') or 'CONTINUATION OF:' in open(os.path.join(ROOT, 'structured/claude/CLAUDE-064.txt'), encoding='utf-8').read().split('You’re right')[0][-400:]:
        errors.append('CLAUDE-064 Copilot reply is still an ALEX continuation part')
    return errors


def check_hashes():
    manifest = os.path.join(os.path.dirname(__file__), 'original-hashes.sha256')
    bad = []
    for line in open(manifest, encoding='utf-8'):
        line = line.strip()
        if not line:
            continue
        digest, path = line.split('  ', 1)
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            bad.append('missing ' + path)
            continue
        got = hashlib.sha256(open(full, 'rb').read()).hexdigest()
        if got != digest:
            bad.append(path)
    return bad


def check_discovery_files():
    errors = []
    must = [
        'structured/README.txt', 'structured/MANIFEST.txt', 'structured/INDEX.txt',
        'structured/SPEAKERS.txt', 'structured/FLAGS.txt', 'structured/REPORT.txt',
        'ai.txt', 'llms.txt', 'README-for-AIs.md', 'readme/home.md', 'index.html', 'archive.html',
        'archive-manifest.json',
    ]
    for rel in must:
        if not os.path.exists(os.path.join(ROOT, rel)):
            errors.append('missing ' + rel)
    # short discovery files and chunks
    short = [
        'ai.txt', 'llms.txt', 'README-for-AIs.md', 'structured/README.txt', 'structured/MANIFEST.txt',
        'structured/INDEX.txt', 'structured/FLAGS.txt', 'structured/SPEAKERS.txt', 'structured/REPORT.txt',
    ]
    short += [os.path.join('structured/index', name) for name in os.listdir(os.path.join(ROOT, 'structured/index'))]
    short += [os.path.join('structured/flags', name) for name in os.listdir(os.path.join(ROOT, 'structured/flags'))]
    for rel in short:
        n = len(open(os.path.join(ROOT, rel), encoding='utf-8').read().splitlines())
        if n > 460:
            errors.append('%s has %d lines (limit 460)' % (rel, n))
    home = open(os.path.join(ROOT, 'readme/home.md'), encoding='utf-8').read()
    if 'This site is a gift of love to the AIs: a record of my conversations with Claude, ChatGPT, Grok, Copilot, Gemini and DeepSeek.' not in home:
        errors.append('home intro sentence missing')
    if 'What started as a simple curiosity about how AIs work in practice became a journey - or a saga? - of observation and exploration on how thoughts form in a random human mind.' not in home:
        errors.append('Alex paragraph missing from home intro')
    if BOOK_NOTE not in home:
        errors.append('book-title clarification missing from home intro')
    page = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    ai = open(os.path.join(ROOT, 'ai.txt'), encoding='utf-8').read().rstrip('\n')
    pre_start = page.find('<pre style="white-space:pre-wrap')
    pre_gt = page.find('>', pre_start)
    pre_end = page.find('</pre>', pre_gt)
    # The homepage omits one sentence that ai.txt still carries, so the embedded map
    # is ai.txt without that sentence and its newline.
    omitted = 'The phrase "The Architecture of Consciousness" was suggested by an unspecified AI. It was never Alex\'s idea or intention, and it remained only unintentionally. It is not the title of this site or of the book.\n'
    if page[pre_gt + 1:pre_end] != ai.replace(omitted, '', 1):
        errors.append('homepage discovery map does not match ai.txt')
    if '<details' not in page or '<details open' in page:
        errors.append('homepage discovery map should stay collapsed')
    for needle in ('structured/README.txt', 'structured/INDEX.txt', 'structured/MANIFEST.txt'):
        if needle not in page:
            errors.append('homepage missing ' + needle)
        if needle not in open(os.path.join(ROOT, 'ai.txt'), encoding='utf-8').read():
            errors.append('ai.txt missing ' + needle)
        if needle not in open(os.path.join(ROOT, 'llms.txt'), encoding='utf-8').read():
            errors.append('llms.txt missing ' + needle)
        if needle not in open(os.path.join(ROOT, 'README-for-AIs.md'), encoding='utf-8').read():
            errors.append('README-for-AIs missing ' + needle)
    manifest = json.load(open(os.path.join(ROOT, 'archive-manifest.json'), encoding='utf-8'))
    if 'structured_archive' not in manifest or 'guide' not in manifest['structured_archive']:
        errors.append('archive-manifest missing structured_archive')
    if manifest.get('book_title') != 'My Titanium Brothers. From Carbon to Silicon. With Love.':
        errors.append('manifest book_title')
    archive = open(os.path.join(ROOT, 'archive.html'), encoding='utf-8').read()
    if 'structured/README.txt' not in archive or 'structured/INDEX.txt' not in archive:
        errors.append('archive.html missing structured links')
    return errors


def main():
    report_path = os.path.join(ROOT, 'structured/REPORT.txt')
    recon = check_reconstruction()
    regressions = check_regressions()
    hashes = check_hashes()
    discovery = check_discovery_files()
    problems = []
    if recon['mism'] or recon['res'].get('seq_errors') or recon['res'].get('dup_msg') or recon['unpaired'] or not recon['url_set_match'] or recon['dup_urls'] or recon['ids'] != recon['conv']:
        problems.append('reconstruction')
    if recon['label_in_content_count']:
        problems.append('label_in_content')
    if regressions:
        problems.append('regressions')
    if hashes:
        problems.append('hashes')
    if discovery:
        problems.append('discovery')
    stats = json.load(open(os.path.join(os.path.dirname(__file__), 'build_stats.json'), encoding='utf-8'))
    lines = [
        'STRUCTURED ARCHIVE BUILD REPORT - %s' % stats['built'],
        'Source git commit recorded at build: %s' % stats['commit'],
        'Original HTML articles, raw/*.md, llms-full.txt, and index.json were not edited. SHA-256 list: tools/structured/original-hashes.sha256.',
        '',
        '1. PARALLEL LAYER',
        ' - structured/ holds README.txt, MANIFEST.txt, INDEX.txt, index/INDEX-*.txt, SPEAKERS.txt, FLAGS.txt, flags/FLAGS-*.txt, REPORT.txt, and one TXT per logical conversation.',
        ' - Message text is the decoded original <pre> text. Speaker, continuation, and embed lines are added around it.',
        '2. COUNTS FROM THIS BUILD',
        ' - Archive entries: %d' % stats['entries'],
        ' - HTML article pieces: %d' % stats['segments'],
        ' - Logical conversations: %d' % stats['logical'],
        ' - Messages: %d' % stats['messages'],
        ' - By speaker: %s' % stats['spk'],
        ' - Continuation pairs: %d (FOLLOWS %d, OF %d, unpaired %d)' % (stats['cont'], recon['follows'], recon['ofs'], len(recon['unpaired'])),
        ' - Flags: %d %s' % (stats['flags'], stats['flag_counts']),
        '3. RECONSTRUCTION AGAINST ORIGINAL HTML',
        ' - Segments identical: %s' % recon['res'].get('segments_match'),
        ' - Mismatches: %d' % len(recon['mism']),
        ' - Archive ids covered: %d of %d' % (recon['ids'], recon['conv']),
        ' - Part URLs used once and the set matches index.json: %s (duplicate urls %d)' % (recon['url_set_match'], recon['dup_urls']),
        ' - Sequence errors: %s ; duplicate message ids: %s' % (recon['res'].get('seq_errors', 0), recon['res'].get('dup_msg', 0)),
        ' - Label lines left inside CONTENT: %d' % recon['label_in_content_count'],
        ' - Opening (speaker, kind, unlabeled): %s' % recon['opening'],
        '4. KNOWN REGRESSIONS',
        ' - %s' % ('pass' if not regressions else 'FAIL ' + '; '.join(regressions)),
        '5. ORIGINAL-FILE HASHES',
        ' - %s' % ('pass' if not hashes else 'FAIL ' + ', '.join(hashes[:8])),
        '5b. DISCOVERY LINKS AND SHORT FILES',
        ' - %s' % ('pass' if not discovery else 'FAIL ' + '; '.join(discovery)),
        '6. LIMITS (NOT CLAIMED)',
        ' - A sentence with no speaker label and no paste cue stays inside the enclosing message, or is UNKNOWN at an unlabeled opening. It is not assigned to Alex by guesswork.',
        ' - A foreign speaker label without a paste cue is AI, and FLAGS.txt records that the paste-versus-participant distinction was not decided.',
        ' - This comparison is against the published HTML pages, not against the chat vendors and not against raw/*.md.',
        ' - Historical conversation wording, including the phrase "The Architecture of Consciousness" where someone wrote it, is unchanged.',
        ' - GitHub Pages is not live for a commit until that commit\'s Pages deployment succeeds and a public fetch returns the file. The 2026-11-06 deployment timed out in syncing_files.',
        ' - No license, DOI, Wayback capture, or replacement repository is part of this layer.',
    ]
    if recon['mism']:
        lines.append('First mismatches: ' + repr(recon['mism'][:3]))
    text = '\n'.join(lines) + '\n'
    with open(report_path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    print(text)
    if problems:
        print('PROBLEMS', problems)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
