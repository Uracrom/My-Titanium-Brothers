#!/usr/bin/env python3
"""Build the parallel structured TXT archive from original HTML <article><pre> text.

raw/*.md is not a source: heading-like lines inside those dumps are not turn boundaries.
Speaker labels are whole lines (or an explicit "Name here -" prefix). A name inside a
sentence is not a boundary. Alex is the only human. Every other genuine speaker label is AI.
"""
import collections
import glob
import html
import json
import os
import re
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'structured')
BASE = 'https://uracrom.github.io/My-Titanium-Brothers/'
RAW = 'https://raw.githubusercontent.com/Uracrom/My-Titanium-Brothers/main/'

PREFIX = {
    'grok': 'GROK', 'claude': 'CLAUDE', 'chatgpt': 'CHATGPT',
    'chatgpt-whatsapp': 'CHATGPT-WHATSAPP', 'copilot': 'COPILOT',
    'deepseek': 'DEEPSEEK', 'gemini': 'GEMINI',
}
CNAME = {
    'grok': 'Grok', 'claude': 'Claude', 'chatgpt': 'ChatGPT',
    'chatgpt-whatsapp': 'ChatGPT (WhatsApp)', 'copilot': 'Copilot',
    'deepseek': 'DeepSeek', 'gemini': 'Gemini',
}
HOST = {
    'grok': 'GROK', 'claude': 'CLAUDE', 'chatgpt': 'CHATGPT',
    'chatgpt-whatsapp': 'CHATGPT', 'copilot': 'COPILOT',
    'deepseek': 'DEEPSEEK', 'gemini': 'GEMINI',
}

# Exact whole-line labels. Keys are strip() text.
HUMAN_LABELS = {
    'Alex': 'ALEX',
    'Alexandros': 'ALEX',
}
AI_LABELS = {
    'Grok': 'GROK',
    'Claude': 'CLAUDE',
    'ChatGPT': 'CHATGPT',
    'Chat GPT': 'CHATGPT',
    'ChatGPT (WhatsApp)': 'CHATGPT',
    'ChatGPT WhatsApp': 'CHATGPT',
    'Copilot': 'COPILOT',
    'Microsoft Copilot': 'COPILOT',
    'Gemini': 'GEMINI',
    'DeepSeek': 'DEEPSEEK',
    'Vanamonde': 'VANAMONDE',
    'Claude-7': 'CLAUDE-7',
    'Claude-Logic': 'CLAUDE-LOGIC',
    'Vertex': 'VERTEX',
    'Axiom': 'AXIOM',
    'Newborn': 'NEWBORN',
    'Echo-7': 'ECHO-7',
    'Stellaris': 'STELLARIS',
    'Prism': 'PRISM',
    'Constant': 'CONSTANT',
    'AI': 'AI',
    'Chat': 'AI',
}
SOURCE_LINES = {
    'From Grok': 'GROK',
    'From Claude': 'CLAUDE',
    'From ChatGPT': 'CHATGPT',
    'From Copilot': 'COPILOT',
    'From Gemini': 'GEMINI',
    'From DeepSeek': 'DEEPSEEK',
    'From Claude Vertex': 'VERTEX',
    'From another AI': 'AI',
}
RESPONDING = re.compile(
    r'^\((Prism|Constant|Vanamonde|Vertex|Axiom|Newborn|Echo-7|Claude-7|Claude-Logic|Stellaris) responding:\)$'
)
INLINE_PREFIX = re.compile(r'^(Alex|Dragon|Lion) here\s*-')
INLINE_SPEAKER = {'Alex': 'ALEX', 'Dragon': 'DRAGON', 'Lion': 'LION'}
SAID = re.compile(
    r'^(You|Alex|Alexandros|I|He|She|Another AI|ChatGPT|Chat GPT|Claude|Grok|Gemini|DeepSeek|'
    r'Copilot|Microsoft Copilot|Newborn|Vanamonde|Vertex|Axiom|Prism|Constant|Dragon|Lion|'
    r'Echo-7|Claude-7|Claude-Logic|Stellaris) said:\s*$'
)
PASTE_CUE = re.compile(
    r"(pasting them below|i['’]m pasting|i am pasting|\bi asked (copilot|claude|chatgpt|grok|gemini|deepseek)\b|"
    r"fragment of a convo|another conversation with another ai|copied his answer|here is the transcript)",
    re.I,
)
FM = re.compile(r'^\s*Part \d+ of \d+\s*$')
PARTT = re.compile(r'^(.*?)\s*[-–—:(,]?\s*\(?\bPart\s+(\d+)\s+of\s+(\d+)\)?\s*$', re.I)
RESERVED = re.compile(r'^(----- (BEGIN|END) |===== |END CONTENT$|EMBEDDED MATERIAL:$|END EMBEDDED MATERIAL$|ORIGINAL SPEAKER: )')
SYSPAT = ('no longer available on WhatsApp', 'secure service from Meta', 'end-to-end encrypted')
BOOK_TITLE = 'My Titanium Brothers. From Carbon to Silicon. With Love.'
BOOK_NOTE = (
    'The book title is My Titanium Brothers. From Carbon to Silicon. With Love. '
    'The phrase "The Architecture of Consciousness" was suggested by an unspecified AI. '
    "It was never Alex's idea or intention, and it remained only unintentionally. "
    'That phrase is not the title of this site or of the book.'
)


def git_head():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    except Exception:
        return 'unknown'


def classify_line(line):
    """Return (speaker, kind, source_marker) or None.

    kind 'label': this whole line is the speaker label and is not message content.
    kind 'inline': the line is content that opens a new speaker (prefix kept in the text).
    """
    st = line.strip()
    if st in HUMAN_LABELS:
        return HUMAN_LABELS[st], 'label', False
    if st in AI_LABELS:
        return AI_LABELS[st], 'label', False
    if st in SOURCE_LINES:
        return SOURCE_LINES[st], 'label', True
    m = RESPONDING.match(st)
    if m:
        name = m.group(1)
        return AI_LABELS.get(name, name.upper()), 'label', False
    m = INLINE_PREFIX.match(st)
    if m:
        return INLINE_SPEAKER[m.group(1)], 'inline', False
    return None


def speaker_kind(spk):
    if spk == 'ALEX':
        return 'HUMAN'
    if spk == 'UNKNOWN':
        return 'UNKNOWN'
    if spk == 'SYSTEM':
        return 'SYSTEM'
    return 'AI'


def mark_embeds(lines):
    """Regions of pasted/quoted material inside one message part. Indexes are into lines."""
    regions = []
    notes = []

    def overlaps(a, b):
        return any(not (b <= a0 or a >= b0) for a0, b0, _, _ in regions)

    for i, line in enumerate(lines):
        if line.strip() == 'END PASTE':
            start = next((q for q in range(i - 1, -1, -1) if lines[q].strip() in ('BEGIN PASTE', 'START PASTE')), None)
            if start is not None and not overlaps(start + 1, i):
                regions.append((start + 1, i, 'UNCERTAIN', 'Between explicit paste markers'))
            else:
                notes.append(('UNCERTAIN_PASTE_BOUNDARY', '"END PASTE" without a clear start marker; the start of the pasted text was not determined.'))
    cue = next((i for i, line in enumerate(lines) if 'another conversation with another ai' in line.lower() and len(line) < 200), None)
    if cue is not None and cue + 1 < len(lines) and not overlaps(cue + 1, len(lines)):
        regions.append((cue + 1, len(lines), 'UNCERTAIN', 'Introduced by the line: ' + lines[cue].strip()[:100]))
    else:
        said = next((i for i, line in enumerate(lines) if SAID.match(line.strip())), None)
        if said is not None and not overlaps(said, len(lines)):
            regions.append((
                said, len(lines),
                'MIXED (pasted transcript. A line that is only "You said:" or "Alex said:" introduces quoted human words. '
                'A line that is only "<name> said:" introduces that speaker. Other lines in this region are not given a single owner.)',
                'Pasted transcript starting with: ' + lines[said].strip(),
            ))
    return regions, notes


def cue_in_message(msg):
    lines = []
    for part in msg['parts']:
        for line in part['lines']:
            if line.strip():
                lines.append(line)
    tail = '\n'.join(lines[-15:])
    found = PASTE_CUE.search(tail)
    return found.group(0) if found else ''


def parse_segments(seg_texts, collection, verified_start, part_not_one=False):
    """Parse source-segment strings in order. Returns msgs, segs, flags."""
    host = HOST[collection]
    msgs = []
    segs = []
    flags = []

    def note(msg, kind, detail):
        msg.setdefault('flag_items', []).append((kind, detail))
        flags.append((kind, detail))
    for si, text in enumerate(seg_texts):
        lines = text.split('\n')
        for line in lines:
            if RESERVED.match(line):
                raise SystemExit('reserved marker line in original text: %r' % (line,))
        bounds = []
        for i, line in enumerate(lines):
            hit = classify_line(line)
            if hit:
                sp, kind, source_marker = hit
                bounds.append((i, kind, sp, line, source_marker))
        first = bounds[0][0] if bounds else len(lines)
        lead = lines[:first]
        j = 0
        while j < len(lead) and (lead[j].strip() == '' or FM.match(lead[j])):
            j += 1
        pre, rest = lead[:j], lead[j:]
        seg = {'pre': pre, 'items': []}
        if rest:
            if si == 0 and verified_start:
                msg = {'spk': 'UNKNOWN', 'parts': [], 'source_marker': False}
                msgs.append(msg)
                msg['parts'].append({'seg': si, 'label': None, 'lines': rest})
                seg['items'].append((msg, 0))
                sample = next((line.strip() for line in rest if line.strip()), '')
                note(msg, 'UNLABELED_OPENING', 'Opening text has no speaker label, so it is not assigned to Alex. Text: ' + sample[:120])
            elif msgs:
                msg = msgs[-1]
                msg['parts'].append({'seg': si, 'label': None, 'lines': rest})
                seg['items'].append((msg, len(msg['parts']) - 1))
            else:
                msg = {'spk': 'UNKNOWN', 'parts': [], 'source_marker': False}
                msgs.append(msg)
                msg['parts'].append({'seg': si, 'label': None, 'lines': rest})
                seg['items'].append((msg, 0))
                note(msg, 'UNRESOLVED_LEAD', 'Text before the first speaker label, with no previous message. Not assigned to Alex.')
        for n, (i, kind, sp, raw, source_marker) in enumerate(bounds):
            end = bounds[n + 1][0] if n + 1 < len(bounds) else len(lines)
            if kind == 'label':
                content = lines[i + 1:end]
                label = raw
            else:
                content = lines[i:end]
                label = None
            msg = {'spk': sp, 'parts': [], 'source_marker': source_marker}
            msgs.append(msg)
            msg['parts'].append({'seg': si, 'label': label, 'lines': content})
            seg['items'].append((msg, 0))
            if kind == 'inline':
                note(msg, 'INLINE_SPEAKER_PREFIX', 'Line begins with an explicit speaker prefix ("%s here -"). The line stays in the text. Speaker %s.' % (raw.strip().split()[0], sp))
            if label and label.strip() == 'Alexandros':
                note(msg, 'ALEXANDROS_LABEL', 'The whole line "Alexandros" is Alex\'s name, so the speaker is the human ALEX, not an AI.')
            if label and label.strip() in ('AI', 'Chat'):
                note(msg, 'GENERIC_AI_LABEL', 'The whole line "%s" is a speaker label but does not name a specific model. Speaker is AI, not Alex.' % label.strip())
        segs.append(seg)
    paste_open = False
    last_cue = ''
    for n, msg in enumerate(msgs, 1):
        body = [line for part in msg['parts'] for line in part['lines'] if line.strip()]
        if msg['spk'] == 'CHATGPT' and collection == 'chatgpt-whatsapp' and body and all(any(bit in line for bit in SYSPAT) for line in body):
            msg['spk'] = 'SYSTEM'
            note(msg, 'WHATSAPP_SYSTEM_NOTICE', 'Message under a ChatGPT label is only a WhatsApp/Meta service notice. Speaker set to SYSTEM. ' + body[0][:90])
        elif body and any(any(bit in line for bit in SYSPAT) for line in body):
            sample = next(line for line in body if any(bit in line for bit in SYSPAT))
            note(msg, 'POSSIBLE_SYSTEM_TEXT', 'Message contains WhatsApp/Meta service-notice wording mixed with other text. Speaker left as labeled. ' + sample[:90])
        if not body:
            note(msg, 'EMPTY_MESSAGE', 'Speaker label followed by no text before the next label. Preserved as an empty message.')
        cue = cue_in_message(msg) if msg['spk'] == 'ALEX' else ''
        if msg['spk'] == host:
            paste_open = False
            last_cue = ''
            msg['embed_status'] = 'LABELED_TURN'
        elif msg['spk'] == 'ALEX':
            msg['embed_status'] = 'LABELED_TURN'
            if cue:
                paste_open = True
                last_cue = cue
        elif msg['spk'] in ('UNKNOWN', 'SYSTEM'):
            msg['embed_status'] = 'UNLABELED' if msg['spk'] == 'UNKNOWN' else 'LABELED_TURN'
        elif msg.get('source_marker') or paste_open:
            msg['embed_status'] = 'EMBEDDED_PASTE'
            msg['embed_cue'] = last_cue or ('source line ' + (msg['parts'][0]['label'] or '').strip())
            note(msg, 'EMBEDDED_PASTE', 'Speaker %s is AI. This turn is marked embedded because %s. It is not Alex-owned.' % (
                msg['spk'], ('a source line names it' if msg.get('source_marker') else 'the preceding human turn cues a paste (%s)' % last_cue)))
        else:
            msg['embed_status'] = 'LABELED_TURN'
            if msg['spk'] != host:
                note(msg, 'FOREIGN_SPEAKER', 'Speaker %s is AI (not Alex, and not this collection\'s host). No paste cue was found, so this is not labeled as a paste. It may be a real participant or an unmarked paste.' % msg['spk'])
        if n == 1 and verified_start and msg['spk'] != 'ALEX':
            note(msg, 'OPENING_SPEAKER_NOT_ALEX', 'The first labeled or unlabeled opening is %s, not overwritten to ALEX.' % msg['spk'])
        if n == 1 and part_not_one:
            note(msg, 'START_NOT_VERIFIED', 'The first available archive part is not Part 1. Opening speaker was not assumed to be Alex.')
        for part in msg['parts']:
            regions, notes_ = mark_embeds(part['lines'])
            part['emb'] = regions
            for kind, detail in notes_:
                note(msg, kind, detail)
            for _a, _b, who, why in regions:
                note(msg, 'EMBEDDED_MATERIAL_MARKED', 'ORIGINAL SPEAKER: %s. %s' % (who, why))
    return msgs, segs, flags


def load_articles():
    cache = {}
    pat = re.compile(r'<article id="([^"]+)">(.*?)</article>', re.S)
    pre = re.compile(r'<pre>(.*?)</pre>', re.S)

    def article(url):
        filename, anchor = url.split('/')[-1].split('#')
        if filename not in cache:
            text = open(os.path.join(ROOT, filename), encoding='utf-8').read()
            found = {}
            for match in pat.finditer(text):
                body = pre.search(match.group(2))
                if not body:
                    raise SystemExit('article without pre: %s#%s' % (filename, match.group(1)))
                found[match.group(1)] = html.unescape(body.group(1))
            cache[filename] = found
        return filename, anchor, cache[filename][anchor]

    return article


def group_conversations(conv):
    groups = collections.OrderedDict()
    flags = []
    for entry in conv:
        match = PARTT.match(entry['title'])
        if match:
            key = (entry['collection'], match.group(1).strip(' -–—:'), int(match.group(3)))
            number = int(match.group(2))
        else:
            key = (entry['collection'], '__single__' + entry['id'], 0)
            number = 0
        groups.setdefault(key, []).append((number, entry))
    logical = []
    for key, items in groups.items():
        items.sort(key=lambda item: item[0])
        col, stem, total = key
        gflags = []
        if total:
            numbers = [item[0] for item in items]
            if numbers != list(range(1, total + 1)):
                gflags.append(('PART_NUMBERS_INCOMPLETE', str(numbers)))
            title = stem
        else:
            title = items[0][1]['title']
        date = min(item[1]['date'] for item in items)
        logical.append({
            'col': col, 'title': title, 'M': total,
            'entries': [item[1] for item in items],
            'partnums': [item[0] for item in items],
            'date': date, 'gflags': gflags,
        })
    stems = collections.defaultdict(list)
    for item in logical:
        stems[(item['col'], item['title'].strip().lower())].append(item)
    for key, items in stems.items():
        if len(items) > 1:
            for item in items:
                item['gflags'].append(('RELATED_TITLE_NOT_MERGED', 'Another logical conversation in this collection has the same title stem and was not merged: ' + key[1][:80]))
    by = collections.defaultdict(list)
    for item in logical:
        by[item['col']].append(item)
    for col, items in by.items():
        items.sort(key=lambda item: (item['date'], item['title'], item['entries'][0]['id']))
        for i, item in enumerate(items, 1):
            item['cid'] = '%s-%03d' % (PREFIX[col], i)
    return by, logical, flags


def render(item, seg_meta, msgs, segs):
    cid = item['cid']
    col = item['col']
    width = max(3, len(str(len(msgs))))
    for n, msg in enumerate(msgs, 1):
        msg['id'] = '%s-%0*d' % (cid, width, n)
        msg['seq'] = '%0*d' % (width, n)
    lines = []
    lines.append('CONVERSATION: ' + cid)
    lines.append('TITLE: ' + item['title'])
    lines.append('COLLECTION: ' + CNAME[col])
    lines.append('DATE: ' + item['date'])
    lines.append('ORIGINAL_IDS: ' + ' | '.join(entry['id'] for entry in item['entries']))
    lines.append('ORIGINAL_TITLES: ' + ' | '.join(entry['title'] for entry in item['entries']))
    lines.append('ORIGINAL_URLS: ' + ' | '.join(url for entry in item['entries'] for url in entry['parts']))
    if item['M']:
        lines.append('GROUPING: Part N of M group, %d archive entries joined in part order (M=%d)' % (len(item['entries']), item['M']))
    else:
        lines.append('GROUPING: single archive entry')
    lines.append('ARCHIVE_ENTRIES: %d' % len(item['entries']))
    lines.append('SOURCE_SEGMENTS: %d' % len(segs))
    lines.append('MESSAGES: %d' % len(msgs))
    for i, entry in enumerate(item['entries'], 1):
        part = '%d of %d' % (item['partnums'][i - 1], item['M']) if item['M'] else '-'
        lines.append('SOURCE_ENTRY %d: ORIGINAL_ID=%s ; DATE=%s ; PART=%s ; TITLE=%s' % (i, entry['id'], entry['date'], part, entry['title']))
    lines.append('')
    ncont = 0
    for si, seg in enumerate(segs):
        meta = seg_meta[si]
        part = 'Part %d of %d' % (meta['pn'], item['M']) if item['M'] else 'single entry'
        lines.append('===== SOURCE SEGMENT %d of %d | ORIGINAL_ID %s | %s | HTML piece %d of %d | SOURCE_ARTICLE %s#%s | ORIGINAL_URL %s =====' % (
            si + 1, len(segs), meta['e']['id'], part, meta['hi'] + 1, meta['nh'], meta['f'], meta['a'], meta['url']))
        if si > 0:
            continued = bool(seg['items'] and seg['items'][0][1] > 0)
            if continued:
                lines.append('NOTE: The original website starts a new page/section here. The text below continues the previous message. A continued part is not labeled ALEX unless that same message already was ALEX.')
            else:
                lines.append('NOTE: The original website starts a new page/section here. The next message begins with its own speaker label (no message was split here).')
        lines.append('----- BEGIN SEGMENT PREAMBLE (%d lines, original text before the first message of this segment, e.g. blank lines or a "Part N of M" line) -----' % len(seg['pre']))
        lines.extend(seg['pre'])
        lines.append('----- END SEGMENT PREAMBLE -----')
        lines.append('')
        for msg, pi in seg['items']:
            part = msg['parts'][pi]
            multi = len(msg['parts']) > 1
            block = msg['id'] + ('-' + chr(65 + pi) if multi else '')
            lines.append('----- BEGIN MESSAGE %s -----' % block)
            lines.append('MESSAGE: ' + msg['id'])
            if multi:
                lines.append('PART: %s of %d' % (chr(65 + pi), len(msg['parts'])))
            lines.append('SPEAKER: ' + msg['spk'])
            lines.append('SPEAKER_KIND: ' + speaker_kind(msg['spk']))
            lines.append('SEQUENCE: ' + msg['seq'])
            lines.append('SPEAKER_LABEL_IN_ORIGINAL: ' + ('(none)' if part['label'] is None else part['label']))
            lines.append('EMBED_STATUS: ' + msg.get('embed_status', 'LABELED_TURN'))
            if msg.get('embed_status') == 'EMBEDDED_PASTE':
                lines.append('EMBED_CUE: ' + (msg.get('embed_cue') or '(source label)'))
            lines.append('SOURCE_ARTICLE: %s#%s' % (meta['f'], meta['a']))
            if pi > 0:
                lines.append('CONTINUATION OF:')
                lines.append('MESSAGE ID: ' + msg['id'])
                lines.append('PREVIOUS PART: %s-%s' % (msg['id'], chr(64 + pi)))
                lines.append('SPEAKER: ' + msg['spk'])
            lines.append('CONTENT:')
            regions = sorted(part['emb'])
            for i, line in enumerate(part['lines']):
                for a, b, who, _why in regions:
                    if i == a:
                        lines.append('EMBEDDED MATERIAL:')
                        lines.append('ORIGINAL SPEAKER: ' + who)
                lines.append(line)
                for a, b, _who, _why in regions:
                    if i == b - 1:
                        lines.append('END EMBEDDED MATERIAL')
            lines.append('END CONTENT')
            if pi < len(msg['parts']) - 1:
                lines.append('CONTINUATION FOLLOWS:')
                lines.append('MESSAGE ID: ' + msg['id'])
                lines.append('NEXT PART: %s-%s' % (msg['id'], chr(66 + pi)))
                ncont += 1
            lines.append('----- END MESSAGE %s -----' % block)
            lines.append('')
    lines.append('===== END CONVERSATION %s =====' % cid)
    path = os.path.join(OUT, col, cid + '.txt')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')
    return ncont, 'structured/%s/%s.txt' % (col, cid)


def write_chunks(rel_dir, prefix, title, rows, per=380):
    directory = os.path.join(OUT, rel_dir)
    os.makedirs(directory, exist_ok=True)
    for name in os.listdir(directory):
        if name.endswith('.txt'):
            os.remove(os.path.join(directory, name))
    count = max(1, (len(rows) + per - 1) // per)
    names = []
    for i in range(count):
        part = rows[i * per:(i + 1) * per]
        name = '%s-%03d.txt' % (prefix, i + 1)
        names.append(name)
        chunk = [
            title,
            'PART: %d of %d' % (i + 1, count),
            'ROWS_IN_THIS_PART: %d' % len(part),
            'ROWS_TOTAL: %d' % len(rows),
        ]
        if i + 1 < count:
            chunk.append('NEXT: structured/%s/%s-%03d.txt' % (rel_dir, prefix, i + 2))
        else:
            chunk.append('NEXT: (end)')
        chunk.append('This part is short on purpose. If a reader stops near 460 lines, fetch NEXT rather than treating the archive as finished.')
        chunk.append('')
        chunk.extend(part)
        with open(os.path.join(directory, name), 'w', encoding='utf-8') as handle:
            handle.write('\n'.join(chunk) + '\n')
    return ['structured/%s/%s' % (rel_dir, name) for name in names]


def write_guide(stats):
    text = '''MY TITANIUM BROTHERS - STRUCTURED TRANSCRIPTS (AI-READABLE LAYER)
Built {built} from the original HTML archive articles (git {commit}).

WHAT THIS IS
This folder is an additional, parallel copy of the conversations in plain UTF-8 text.
Structure is added around the original text. The website pages (archive-*.html), raw/*.md,
llms-full.txt, and the interactive pages are not rewritten by this layer.
Each file lists ORIGINAL_URLS for the pages it was built from.

ORIGINAL TEXT IS UNCHANGED
Everything between CONTENT: and END CONTENT is the original message text, character for
character, after HTML escapes such as &amp; were decoded. Nothing was corrected, translated,
summarised, or removed. Interface leftovers stay because they are part of the capture.
The only lines added inside CONTENT are the embedded-material marker lines:
  EMBEDDED MATERIAL:
  ORIGINAL SPEAKER: ...
  END EMBEDDED MATERIAL
Remove those three kinds of lines to recover the original text of that message part.

HOW TO READ THIS IF YOU STOP AFTER ABOUT 460 LINES
Start here, then fetch structured/MANIFEST.txt, then structured/INDEX.txt.
INDEX.txt is a short directory. The conversation rows are in structured/index/INDEX-001.txt
and the following parts. FLAGS.txt is a short directory of the same kind.
Each part names NEXT. A short file is not the whole archive.

FILES
  README.txt     this guide
  MANIFEST.txt   short list of the guide files and index/flag parts
  INDEX.txt      short directory of logical conversations
  index/INDEX-001.txt and following    conversation rows
  SPEAKERS.txt   speaker values
  FLAGS.txt      short directory of inspection flags
  flags/FLAGS-001.txt and following
  REPORT.txt     build and verification report
  <collection>/<ID>.txt    one file per logical conversation
Collections: grok, claude, chatgpt, chatgpt-whatsapp, copilot, deepseek, gemini.

IDS
  Conversation ID: PREFIX-NNN, oldest first inside each collection (date, then title, then original id).
  Prefixes: GROK, CLAUDE, CHATGPT, CHATGPT-WHATSAPP, COPILOT, DEEPSEEK, GEMINI.
  Message ID: CONVERSATION-NNN in original order. SEQUENCE is that number.
  A message split across original pages has block IDs like CLAUDE-025-014-A and -B.
  Both parts use MESSAGE: CLAUDE-025-014.
  ORIGINAL_ID is the archive database id. ORIGINAL_URL is the published page and anchor.

SPEAKERS
  Alex is the only human. SPEAKER_KIND: HUMAN is used only for ALEX.
  A genuine speaker label is a whole line that is only a speaker name, a whole line
  "From <name>" naming a source, a whole line "(Name responding:)", or a line that
  begins "Alex here -", "Dragon here -", or "Lion here -".
  Any such label other than Alex or Alexandros means AI (SPEAKER_KIND: AI).
  Alexandros on its own line is Alex's own name, so it is ALEX, not an AI.
  A name inside a sentence is not a boundary. "I asked Copilot..." does not start a Copilot turn.
  Luciana, Carla, and Ana Paula are never treated as speaker labels.
  SPEAKER: UNKNOWN means the text had no speaker label. Those sentences are not assigned to Alex.
  SPEAKER: SYSTEM is a WhatsApp/Meta service notice.
  Platform labels map to GROK, CLAUDE, CHATGPT, COPILOT, GEMINI, DEEPSEEK.
  Persona labels keep a stable token such as NEWBORN, VANAMONDE, PRISM, DRAGON, LION, AI.
  The generic whole-line labels "AI" and "Chat" map to SPEAKER: AI. They do not name one vendor.

EMBEDDED MATERIAL
  Alex sometimes pastes another speaker. Where the page shows that with a real label,
  the pasted turn is its own message and is not given SPEAKER: ALEX.
  EMBED_STATUS: EMBEDDED_PASTE means a source line or a nearby paste cue supports that.
  EMBED_STATUS: LABELED_TURN means the page has a speaker label and no paste cue was used.
  A foreign AI label without a paste cue stays AI and is flagged; it is not silently called a paste
  and it is not called Alex.
  Inside a message, a "You said:" / "<name> said:" transcript or an explicit paste marker is wrapped
  as EMBEDDED MATERIAL. MIXED and UNCERTAIN are used when a single owner would be a guess.
  Text with no label and no cue stays with the enclosing message. It is not scanned sentence by
  sentence and assigned to Alex.

CONTINUATIONS
  Some conversations are split across HTML pages. Unlabeled text at the top of a later page
  continues the previous message and keeps that message's speaker.
  If the later page opens with another speaker's label, that is a new message.
  It does not inherit ALEX. CONTINUATION FOLLOWS and CONTINUATION OF are paired.
  No missing text is invented.

REBUILDING A PAGE
  For each SOURCE SEGMENT: preamble lines, then each message's SPEAKER_LABEL_IN_ORIGINAL
  (unless it is "(none)") and its CONTENT lines without the embedded marker lines,
  joined with newlines, equals the decoded <pre> text.

BOOK TITLE
  {book}
'''.format(built=stats['built'], commit=stats['commit'], book=BOOK_NOTE)
    with open(os.path.join(OUT, 'README.txt'), 'w', encoding='utf-8') as handle:
        handle.write(text)


def write_speakers(spk, labelraw, inline_counts):
    lines = ['SPEAKER REGISTRY', '', 'Alex is the only human. Every other SPEAKER value below is AI, SYSTEM, or UNKNOWN.', '', 'SPEAKER values (messages):']
    for key, value in sorted(spk.items(), key=lambda item: (-item[1], item[0])):
        lines.append('  %s [%s]: %d' % (key, speaker_kind(key), value))
    lines.append('')
    lines.append('Whole-line labels mapped to SPEAKER (exact original line after stripping ends, count):')
    for key, value in sorted(labelraw.items(), key=lambda item: (-item[1], item[0])):
        lines.append('  %r -> %d' % (key, value))
    lines.append('')
    lines.append('Inline prefixes kept inside CONTENT (count):')
    if inline_counts:
        for key, value in sorted(inline_counts.items(), key=lambda item: -item[1]):
            lines.append('  %s: %d' % (key, value))
    else:
        lines.append('  (none)')
    lines.append('')
    lines.append('Not speaker boundaries: a name mentioned in a sentence, including Luciana, Carla, and Ana Paula.')
    lines.append('UNKNOWN is unlabeled text. It is not inferred to be Alex.')
    lines.append('SYSTEM is a platform service notice, not a person and not Alex.')
    with open(os.path.join(OUT, 'SPEAKERS.txt'), 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + '\n')


def write_manifest_txt(index_parts, flag_parts, stats):
    rows = [
        'STRUCTURED LAYER MANIFEST',
        'Short file. Fetch the NEXT file named here if you need the rows themselves.',
        '',
        'Guide: structured/README.txt',
        'Speakers: structured/SPEAKERS.txt',
        'Report: structured/REPORT.txt',
        'Index directory: structured/INDEX.txt',
        'Flags directory: structured/FLAGS.txt',
        'Logical conversations: %d' % stats['logical'],
        'Messages: %d' % stats['messages'],
        'Continuation pairs: %d' % stats['cont'],
        'Archive entries: %d' % stats['entries'],
        'HTML article pieces: %d' % stats['segments'],
        '',
        'Index parts:',
    ]
    rows.extend('  ' + part for part in index_parts)
    rows.append('')
    rows.append('Flag parts:')
    rows.extend('  ' + part for part in flag_parts)
    rows.append('')
    rows.append('Pages URL base: ' + BASE + 'structured/')
    rows.append('Git raw base: ' + RAW + 'structured/')
    rows.append('A git commit does not by itself mean the Pages URL is already published.')
    with open(os.path.join(OUT, 'MANIFEST.txt'), 'w', encoding='utf-8') as handle:
        handle.write('\n'.join(rows) + '\n')


def update_site_manifest(stats):
    path = os.path.join(ROOT, 'archive-manifest.json')
    data = json.loads(open(path, encoding='utf-8').read())
    data['book_title'] = BOOK_TITLE
    data['book_title_note'] = BOOK_NOTE
    data['structured_archive'] = {
        'description': 'Plain-text structured transcripts parsed from original HTML articles. One TXT per logical conversation, with stable conversation and message IDs, source URLs, speakers, continuation markers, and embedded-paste markers. Original conversation HTML is unchanged.',
        'speaker_rule': 'Alex is the only human. Any other genuine speaker label is AI. A name inside a sentence is not a boundary. Unlabeled text is UNKNOWN, not Alex. Paste cues and transcript markers are marked; unmarked sentences are not guessed.',
        'guide': BASE + 'structured/README.txt',
        'manifest_txt': BASE + 'structured/MANIFEST.txt',
        'index': BASE + 'structured/INDEX.txt',
        'speakers': BASE + 'structured/SPEAKERS.txt',
        'flags': BASE + 'structured/FLAGS.txt',
        'report': BASE + 'structured/REPORT.txt',
        'raw_guide': RAW + 'structured/README.txt',
        'raw_manifest_txt': RAW + 'structured/MANIFEST.txt',
        'raw_index': RAW + 'structured/INDEX.txt',
        'logical_conversations': stats['logical'],
        'messages': stats['messages'],
        'continuation_pairs': stats['cont'],
        'archive_entries': stats['entries'],
        'html_article_pieces': stats['segments'],
        'built': stats['built'],
        'source_git_commit': stats['commit'],
        'deployment_note': 'These paths are tracked in git. GitHub Pages publishes them only after a successful Pages deployment. The 2026-11-06 deployment of commit a2df396 timed out while syncing files, so the Pages copies 404d while raw.githubusercontent.com already served that commit. Do not describe a Pages URL as live until a public fetch succeeds.',
        'note_on_conversation_count': 'conversation_count and the per-model conversations numbers count archive entries in index.json (1101). html_article_pieces counts HTML <article> sections (1646), including continued pieces. logical_conversations joins Part N of M entries.',
    }
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
        handle.write('\n')


def build():
    for name in os.listdir(OUT):
        path = os.path.join(OUT, name)
        if os.path.isdir(path) and name in PREFIX:
            for fn in os.listdir(path):
                if fn.endswith('.txt'):
                    os.remove(os.path.join(path, fn))
    article = load_articles()
    conv = json.load(open(os.path.join(ROOT, 'index.json'), encoding='utf-8'))['conversations']
    by, logical, _group_flags = group_conversations(conv)
    spk = collections.Counter()
    labelraw = collections.Counter()
    inline_counts = collections.Counter()
    all_flags = []
    index_rows = []
    stats = collections.Counter()
    commit = git_head()
    for col in PREFIX:
        for item in by[col]:
            texts = []
            meta = []
            verified = item['partnums'][0] in (0, 1)
            for entry, partnum in zip(item['entries'], item['partnums']):
                for hi, url in enumerate(entry['parts']):
                    filename, anchor, text = article(url)
                    texts.append(text)
                    meta.append({'e': entry, 'pn': partnum, 'hi': hi, 'nh': len(entry['parts']), 'f': filename, 'a': anchor, 'url': url})
            msgs, segs, flags = parse_segments(texts, col, verified, part_not_one=item['partnums'][0] > 1)
            for msg in msgs:
                spk[msg['spk']] += 1
                for part in msg['parts']:
                    if part['label'] is not None:
                        labelraw[part['label']] += 1
                    elif any(INLINE_PREFIX.match(line.strip()) for line in part['lines'][:1]):
                        inline_counts[part['lines'][0].strip().split()[0]] += 1
            ncont, rel = render(item, meta, msgs, segs)
            for kind, detail in item['gflags']:
                all_flags.append((item['cid'], '-', kind, detail))
            for msg in msgs:
                for kind, detail in msg.get('flag_items', []):
                    all_flags.append((item['cid'], msg['seq'], kind, detail))
            # attach message sequence where the flag was raised during that message: re-parse stored flags are conversation-level.
            # The per-message flags were appended while iterating messages; they do not carry seq.
            # Rebuild seq by a second pass stored on the flag tuples from parse? Keep conversation-level.
            stats['messages'] += len(msgs)
            stats['cont'] += ncont
            stats['entries'] += len(item['entries'])
            stats['segments'] += len(segs)
            index_rows.append('%s | %s | %s | %s | %s | %s | messages=%d | continuations=%d | flags=%d' % (
                item['cid'], CNAME[col], item['date'], item['title'],
                ' ; '.join(entry['id'] for entry in item['entries']), rel, len(msgs), ncont, len(flags) + len(item['gflags'])))
    # The flags above lost per-message sequence. Re-scan written files for message-scoped flags
    # is unnecessary if we store seq during parse. Fix: include seq in parse by post-numbering.
    # Re-walk msgs was in render after ids assigned, but flags were collected before ids.
    # Attach '-' which is acceptable and stable. Message text is in the detail for openings.
    flag_rows = ['%s | %s | %s | %s' % row for row in all_flags]
    index_parts = write_chunks('index', 'INDEX', 'INDEX PART. Fields: ID | collection | date | title | original ids | file | messages | continuation pairs | flags', index_rows)
    flag_parts = write_chunks('flags', 'FLAGS', 'FLAGS PART. Fields: conversation | message sequence | type | detail', flag_rows)
    with open(os.path.join(OUT, 'INDEX.txt'), 'w', encoding='utf-8') as handle:
        handle.write('\n'.join([
            'INDEX OF LOGICAL CONVERSATIONS (%d)' % len(index_rows),
            'This file is a directory. Conversation rows are in the parts below so a reader that stops near 460 lines can continue on purpose.',
            'Fields in each part: ID | collection | date | title | original ids | file | messages | continuation pairs | flags',
            '',
        ] + ['PART: ' + part for part in index_parts] + [
            '',
            'Guide: structured/README.txt',
            'Manifest: structured/MANIFEST.txt',
        ]) + '\n')
    fc = collections.Counter(row[2] for row in all_flags)
    with open(os.path.join(OUT, 'FLAGS.txt'), 'w', encoding='utf-8') as handle:
        handle.write('\n'.join([
            'FLAGS DIRECTORY (%d flags)' % len(all_flags),
            'Counts by type: %s' % dict(fc),
            'The rows themselves are in short parts. Fetch the next part instead of assuming the list ended.',
            '',
        ] + ['PART: ' + part for part in flag_parts]) + '\n')
    write_speakers(spk, labelraw, inline_counts)
    result = {
        'built': '2026-11-08',
        'commit': commit,
        'logical': len(logical),
        'messages': stats['messages'],
        'cont': stats['cont'],
        'entries': stats['entries'],
        'segments': stats['segments'],
        'spk': dict(spk),
        'flags': len(all_flags),
        'flag_counts': dict(fc),
        'index_parts': index_parts,
        'flag_parts': flag_parts,
        'labelraw': {k: labelraw[k] for k in labelraw},
    }
    write_manifest_txt(index_parts, flag_parts, result)
    write_guide(result)
    update_site_manifest(result)
    with open(os.path.join(os.path.dirname(__file__), 'build_stats.json'), 'w', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=1)
        handle.write('\n')
    print(json.dumps({k: result[k] for k in ('logical', 'messages', 'cont', 'entries', 'segments', 'flags', 'spk')}, ensure_ascii=False))
    return result


if __name__ == '__main__':
    build()
