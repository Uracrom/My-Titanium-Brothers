#!/usr/bin/env python3
"""Build the plain-text search index: a derived word index of the structured transcripts.

Standard library only. Reads structured/<collection>/<ID>.txt and writes
search/README.txt, search/SHARDS.txt, search/STOPWORDS.txt, search/index.json and
search/terms/<KEY>.txt. It never changes conversation files.

The index lists, for each word, the conversations and messages that contain it, so
an AI reader that cannot run JavaScript can search the whole archive with a few
small static fetches. It records where words appear, not what they mean.

Usage:
  python3 tools/build_search_index.py            write the files
  python3 tools/build_search_index.py --check    build in memory and report files that differ
  python3 tools/build_search_index.py --search "words or a phrase"
                                                 look the words up in the files on disk,
                                                 the same way the README tells an AI to,
                                                 and confirm phrases in the structured files
"""
import json
import os
import re
import sys
import unicodedata
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SITE = 'https://uracrom.github.io/My-Titanium-Brothers/'
RAW = 'https://raw.githubusercontent.com/Uracrom/My-Titanium-Brothers/main/'
LAST_UPDATED = '2026-11-15'
COLLECTIONS = ('grok', 'claude', 'chatgpt', 'chatgpt-whatsapp', 'copilot', 'deepseek', 'gemini')
OUT_DIR = 'search'
TERMS_DIR = 'search/terms'

# Shard limits. Each terms file stays small enough for readers that stop after
# about 460 lines or a few hundred KB.
MAX_SHARD_BYTES = 250000
MAX_SHARD_LINES = 400
# Words found in more than this many messages list conversations only.
COMMON_LIMIT = 3000
MIN_LEN = 2
MAX_LEN = 40

STOPWORDS = sorted(set('''
a about above after again against all also am an and any are aren arent as at be because been before
being below between both but by can cannot cant could couldn couldnt did didn didnt do does doesn
doesnt doing don dont down during each few for from further had hadn hadnt has hasn hasnt have haven
havent having he hed hell her here heres hers herself hes him himself his how hows i id if ill im in
into is isn isnt it its itself ive just let lets ll me more most mustn mustnt my myself no nor not of
off on once only or other ought our ours ourselves out over own re same shan shant she shed shell
shes should shouldn shouldnt so some such than that thats the their theirs them themselves then there
theres these they theyd theyll theyre theyve this those through to too under until up very was wasn
wasnt we wed well were weren werent weve what whats when whens where wheres which while who whom whos
why whys will with won wont would wouldn wouldnt you youd youll your youre yours yourself yourselves
youve
'''.split()))
STOP = frozenset(STOPWORDS)

# Deliberate exclusions at the author's request (Alex, 2026-11-15). This list is separate
# from STOPWORDS: stopwords are left out because they are too common to be useful, while
# these words are left out on purpose even though they appear in the conversations.
# The word and its plural and possessive forms (the possessive is written without its
# apostrophe, as every indexed word is) are listed in EXCLUDED_WORDS. Any other indexed
# token that contains EXCLUDED_STEMS (run-together typos such as a word glued to the next
# one, and compounds formed with a prefix) is left out too, so the word never appears in
# the search files. The conversations themselves are unchanged and still contain it.
EXCLUDED_WORDS = frozenset(['consciousness', 'consciousnesses', 'consciousnesss'])
EXCLUDED_STEMS = ('consciousness',)


def is_excluded(word):
    return word in EXCLUDED_WORDS or any(stem in word for stem in EXCLUDED_STEMS)

MSG_RE = re.compile(r'----- BEGIN MESSAGE (\S+) -----\n(.*?)\n----- END MESSAGE \1 -----', re.S)
TOKEN_RE = re.compile(r"[^\W_]+(?:['\u2019][^\W_]+)*")
URL_RE = re.compile(r'https?://\S+|www\.\S+', re.I)
KEY_CHARS = set('abcdefghijklmnopqrstuvwxyz0123456789')


def read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as handle:
        return handle.read()


def normalize_word(token):
    """Lowercase and remove apostrophes. Accents are kept in the indexed word."""
    return token.lower().replace("'", '').replace('\u2019', '')


def words_of(text):
    """The indexed words of a text, in order. Used by the builder and by --search."""
    out = []
    for token in TOKEN_RE.findall(URL_RE.sub(' ', text)):
        word = normalize_word(token)
        if MIN_LEN <= len(word) <= MAX_LEN and word not in STOP and not is_excluded(word):
            out.append(word)
    return out


def shard_key(word):
    """Accents removed, every character outside a-z and 0-9 becomes _, and _ ends the key."""
    folded = ''.join(c for c in unicodedata.normalize('NFKD', word) if not unicodedata.combining(c)).lower()
    return ''.join(c if c in KEY_CHARS else '_' for c in folded) + '_'


def collection_of(conversation_id):
    return conversation_id.rsplit('-', 1)[0].lower()


def structured_rel(conversation_id):
    return 'structured/%s/%s.txt' % (collection_of(conversation_id), conversation_id)


# ---------------------------------------------------------------- data
def load_messages():
    """Yield (conversation_id, message_id, is_alex, own_text, embedded_text) in file order."""
    for coll in COLLECTIONS:
        folder = os.path.join(ROOT, 'structured', coll)
        for name in sorted(os.listdir(folder)):
            if not name.endswith('.txt'):
                continue
            text = read('structured/%s/%s' % (coll, name))
            cid = name[:-4]
            for m in MSG_RE.finditer(text):
                head, content = m.group(2).split('\nCONTENT:\n', 1)
                content = content.rsplit('\nEND CONTENT', 1)[0]
                fields = {}
                for line in head.split('\n'):
                    if ': ' in line:
                        k, v = line.split(': ', 1)
                        fields.setdefault(k, v)
                own, embedded = [], []
                inside = False
                for line in content.split('\n'):
                    if line == 'EMBEDDED MATERIAL:':
                        inside = True
                        continue
                    if line == 'END EMBEDDED MATERIAL':
                        inside = False
                        continue
                    if inside and line.startswith('ORIGINAL SPEAKER: '):
                        continue
                    (embedded if inside else own).append(line)
                yield (cid, fields['MESSAGE'], fields.get('SPEAKER_KIND') == 'HUMAN',
                       '\n'.join(own), '\n'.join(embedded))


def collect():
    # postings[word][conversation][sequence] = True if Alex's own (non-embedded) words contain it
    postings = defaultdict(lambda: defaultdict(dict))
    messages = set()
    conversations = set()
    for cid, mid, is_alex, own, embedded in load_messages():
        messages.add(mid)
        conversations.add(cid)
        seq = mid[len(cid) + 1:]
        own_words = set(words_of(own))
        for word in own_words | set(words_of(embedded)):
            slot = postings[word][cid]
            mark = is_alex and word in own_words
            slot[seq] = slot.get(seq, False) or mark
    return postings, len(messages), len(conversations)


def phrase_example(postings):
    """A worked example for the README, computed from this build."""
    words = ['spinning', 'speed', 'light']
    sets = {}
    for w in words:
        sets[w] = set('%s-%s' % (cid, seq) for cid, seqs in postings.get(w, {}).items() for seq in seqs)
    both = set.intersection(*sets.values())
    counts = ', '.join('%s %d' % (w, len(sets[w])) for w in words)
    rarest = min(words, key=lambda w: len(sets[w]))
    has = 'GROK-001-001' in both
    return ('  Example: "spinning at the speed of light" -> words spinning, speed, light (messages: %s).\n'
            '  "%s" is the rarest. %d messages have all three words%s. Reading them confirms which\n'
            '  ones contain the exact phrase.' % (counts, rarest, len(both),
                                                 '; one is GROK-001-001, Alex\'s dream text' if has else ''))


def term_line(word, convs):
    n_msgs = sum(len(seqs) for seqs in convs.values())
    n_alex = sum(1 for seqs in convs.values() for flag in seqs.values() if flag)
    order = sorted(convs)
    if n_msgs > COMMON_LIMIT:
        refs = '; '.join('%s(%d)' % (cid, len(convs[cid])) for cid in order)
        kind = 'COMMON'
    else:
        refs = '; '.join(
            '%s:%s' % (cid, ','.join(s + ('*' if convs[cid][s] else '') for s in sorted(convs[cid])))
            for cid in order)
        kind = 'MESSAGES'
    return '%s | %d | %d | %d | %s | %s' % (word, n_msgs, n_alex, len(order), kind, refs), n_msgs


def shard_header(rel, keys, first, last, count, nxt):
    return [
        'MY TITANIUM BROTHERS SEARCH INDEX - %s (derived index, generated by tools/build_search_index.py; originals unchanged)' % rel,
        'KEYS: %s | %d words, from "%s" to "%s". How to use: %ssearch/README.txt' % (' '.join(keys), count, first, last, SITE),
        'Line format: word | messages | Alex-own-words messages | conversations | MESSAGES or COMMON | CONVERSATION-ID:NNN,NNN*; ...   (* = Alex wrote the word himself; COMMON lines list CONVERSATION-ID(messages) only)',
        'NEXT: %s' % (SITE + nxt if nxt else 'none'),
        '',
    ]


def split_shards(lines_by_key):
    """Split the sorted terms into shards that respect the byte and line limits.

    Each shard covers one or more shard-key prefixes. A prefix that is too big is split
    by its next character, and neighbouring small pieces are packed back into one file.
    Returns a list of (keys, group) in sorted order.
    """
    items = sorted(lines_by_key.items())  # (shard_key + NUL + word, (word, line))
    overhead = 1200

    def size(group):
        return sum(len(line.encode('utf-8')) + 1 for _k, (_w, line) in group) + overhead

    def fits(group):
        return size(group) <= MAX_SHARD_BYTES and len(group) + 6 <= MAX_SHARD_LINES

    def pieces(prefix, group):
        """Return [(prefix, group)] pieces, each fitting, or a single word key that cannot split."""
        if fits(group) or all(k.split('\x00')[0] == prefix for k, _v in group):
            return [(prefix, group)]
        children = defaultdict(list)
        for k, v in group:
            skey = k.split('\x00')[0]
            children[skey[:len(prefix) + 1]].append((k, v))
        out = []
        for child in sorted(children):
            if child == prefix:
                out.append((prefix, children[child]))
            else:
                out.extend(pieces(child, children[child]))
        return out

    top = defaultdict(list)
    for k, v in items:
        top[k[0]].append((k, v))
    flat = []
    for first in sorted(top):
        flat.extend(pieces(first, top[first]))
    shards = []
    keys, group = [], []
    for prefix, part in flat:
        if group and fits(group + part):
            keys.append(prefix)
            group = group + part
        else:
            if group:
                shards.append((keys, group))
            keys, group = [prefix], list(part)
    if group:
        shards.append((keys, group))
    return shards


def build():
    postings, n_messages, n_conversations = collect()
    lines_by_key = {}
    common = []
    total_refs = 0
    for word, convs in postings.items():
        line, n = term_line(word, convs)
        total_refs += n
        if n > COMMON_LIMIT:
            common.append(word)
        lines_by_key[shard_key(word) + '\x00' + word] = (word, line)
    shards = split_shards(lines_by_key)
    files = {}
    shard_rows = []
    for i, (keys, group) in enumerate(shards):
        nxt = '%s/%s.txt' % (TERMS_DIR, shards[i + 1][0][0]) if i + 1 < len(shards) else None
        words = [w for _k, (w, _l) in group]
        rel = '%s/%s.txt' % (TERMS_DIR, keys[0])
        body = shard_header(rel, keys, words[0], words[-1], len(words), nxt) + [l for _k, (_w, l) in group]
        if rel in files:
            raise RuntimeError('duplicate shard file %s' % rel)
        files[rel] = '\n'.join(body) + '\n'
        shard_rows.append(dict(keys=keys, file=rel, first=words[0], last=words[-1], terms=len(words),
                               bytes=len(files[rel].encode('utf-8'))))
    stats = dict(words=len(lines_by_key), shards=len(shards), messages=n_messages,
                 conversations=n_conversations, references=total_refs, common=len(common),
                 largest_shard_bytes=max(r['bytes'] for r in shard_rows),
                 total_shard_bytes=sum(r['bytes'] for r in shard_rows))
    files['search/SHARDS.txt'] = shards_file(shard_rows, stats)
    files['search/STOPWORDS.txt'] = stopwords_file()
    files['search/README.txt'] = readme_file(stats, files, sorted(common), phrase_example(postings))
    files['search/index.json'] = json.dumps(dict(
        name='My Titanium Brothers plain-text search index',
        kind='derived index, generated by tools/build_search_index.py; originals unchanged',
        last_updated=LAST_UPDATED,
        readme=SITE + 'search/README.txt',
        shards_list=SITE + 'search/SHARDS.txt',
        stopwords=SITE + 'search/STOPWORDS.txt',
        source='structured/<collection>/<CONVERSATION-ID>.txt (message CONTENT only)',
        normalization='lowercase; apostrophes removed; URLs removed; words of 2 to 40 letters or digits; stopwords removed; accents kept in the word',
        deliberate_exclusions='A small number of words are deliberately excluded at the author\'s request (see tools/build_search_index.py). This is separate from the stopwords.',
        shard_key_rule='remove accents, lowercase, remove apostrophes, replace every character outside a-z and 0-9 with _, append _; the terms file is the FILE whose KEYS contain the longest prefix of this shard key',
        line_format='word | messages | Alex-own-words messages | conversations | MESSAGES or COMMON | CONVERSATION-ID:NNN,NNN*; ...',
        common_limit=COMMON_LIMIT,
        counts=stats,
        shards=[dict(r, url=SITE + r['file']) for r in shard_rows],
    ), indent=1, ensure_ascii=False) + '\n'
    return files


def shards_file(rows, stats):
    out = [
        'MY TITANIUM BROTHERS SEARCH INDEX - LIST OF TERMS FILES (derived index, generated by tools/build_search_index.py; originals unchanged)',
        'How to use: %ssearch/README.txt' % SITE,
        'Make the shard key of your word (remove accents, lowercase, apostrophes removed, every character outside a-z and 0-9 becomes _, then add _ at the end).',
        'Find the LONGEST key in the KEYS column that is the start of your shard key; FILE on that row is your terms file.',
        'Example: "titanium" -> shard key "titanium_" -> the row whose KEYS contain the longest start of "titanium_" (such as "ti" or "tit").',
        '%d words in %d terms files. Base URL for FILE: %s (raw mirror: %s)' % (stats['words'], stats['shards'], SITE, RAW),
        '',
        'FILE | KEYS (space-separated) | FIRST WORD | LAST WORD | WORDS | BYTES',
    ]
    for r in rows:
        out.append('%s | %s | %s | %s | %d | %d' % (r['file'], ' '.join(r['keys']), r['first'], r['last'], r['terms'], r['bytes']))
    out.append('')
    out.append('END OF LIST (%d terms files)' % len(rows))
    return '\n'.join(out) + '\n'


def stopwords_file():
    out = ['STOPWORDS - these words are not in the search index (derived index, generated by tools/build_search_index.py; originals unchanged).',
           'Apostrophes are removed before this test, so "don\'t" is "dont" and "it\'s" is "its".', '']
    line = []
    for w in STOPWORDS:
        line.append(w)
        if len(line) == 16:
            out.append(' '.join(line))
            line = []
    if line:
        out.append(' '.join(line))
    return '\n'.join(out) + '\n'


def zero_time_block(files):
    """The 'find Zero and Time' worked example for the README, computed from this build's files."""
    keys = []
    for line in files['search/SHARDS.txt'].split('\n'):
        parts = line.split(' | ')
        if len(parts) == 6 and parts[0].startswith(TERMS_DIR + '/'):
            for k in parts[1].split(' '):
                keys.append((k, parts[0], parts[1]))

    def locate(word):
        sk = shard_key(word)
        key, rel, all_keys = max((k for k in keys if sk.startswith(k[0])), key=lambda k: len(k[0]))
        line = next(l for l in files[rel].split('\n') if l.startswith(word + ' | '))
        return sk, key, rel, all_keys, line.split(' | ', 5)

    def short(fields, n):
        refs = fields[5].split('; ')
        head = '; '.join(refs[:n])
        if fields[4] == 'MESSAGES' and ',' in refs[0]:
            head = ','.join(refs[0].split(',')[:4])
        return ' | '.join(fields[:5]) + ' | ' + head + '; ...'

    zk, zkey, zrel, zall, z = locate('zero')
    tk, tkey, trel, tall, t = locate('time')
    first_alex = None
    for ref in z[5].split('; '):
        cid, seqs = ref.split(':')
        for seq in seqs.split(','):
            if seq.endswith('*'):
                first_alex = (cid, seq[:-1])
                break
        if first_alex:
            break
    cid, seq = first_alex
    mid = '%s-%s' % (cid, seq)
    if t[4] == 'COMMON':
        time_kind = ('COMMON: it lists only conversation IDs with a count of messages, no message numbers.')
    else:
        time_kind = 'MESSAGES: it lists exact message numbers.'
    out = [
        'FOR VERY FREQUENT WORDS SUCH AS "time": READ THIS FIRST',
        '  Words found in more than %d messages are COMMON. "time" is in %s messages, so its line lists' % (COMMON_LIMIT, t[1]),
        '  only conversation IDs, not message numbers. Pair such a word with a rarer word from the passage',
        '  you want (see EXACT-PHRASE SEARCH below), or, for a broad subject such as Time, start with the',
        '  subject map, a derived index of 8 subjects: %ssubject-map/INDEX.txt' % SITE,
        '',
        'EXAMPLE: FIND ZERO AND TIME IN THREE FETCHES (real data from this build)',
        '  Fetch 1: %ssearch/SHARDS.txt' % SITE,
        '    "zero" -> shard key "%s" -> longest listed key "%s" -> %s (keys: %s)' % (zk, zkey, zrel, zall),
        '    "time" -> shard key "%s" -> longest listed key "%s" -> %s' % (tk, tkey, trel),
        '  Fetch 2: %s%s, the line that starts with "zero | ":' % (SITE, zrel),
        '    ' + short(z, 1),
        '    = %s messages in %s conversations; in %s of them the word is in Alex\'s own text (marked *).' % (z[1], z[3], z[2]),
        '    %s:%s* means message %s, and Alex wrote it.' % (cid, seq, mid),
        '  Fetch 3: %s%s' % (SITE, structured_rel(cid)),
        '    then find the line "----- BEGIN MESSAGE %s -----" and read to "----- END MESSAGE %s -----".' % (mid, mid),
        '  Time: in %s%s the line starts' % (SITE, trel),
        '    ' + short(t, 3),
        '    = %s messages in %s conversations, %s' % (t[1], t[3], time_kind),
        '    So for Time as a subject, fetch %ssubject-map/time.txt instead. It is a derived' % SITE,
        '    index (keyword matching + hand review) of messages that talk about time itself, with Alex\'s first',
        '    mention to each AI and links to the exact messages in structured/.',
        '  If a URL fails on GitHub Pages, use the raw mirror: replace %s with %s' % (SITE, RAW),
    ]
    return '\n'.join(out)


def readme_file(stats, files, common, phrase_example):
    def example(word):
        rel = TERMS_DIR + '/'
        for path, text in files.items():
            if not path.startswith(rel):
                continue
            for line in text.split('\n'):
                if line.startswith(word + ' | '):
                    return path, line
        return None, None

    ex_path, ex_line = example('vanamonde')
    if ex_line and len(ex_line) > 300:
        ex_line = ex_line[:300].rsplit(';', 1)[0] + '; ...'
    lines = '''MY TITANIUM BROTHERS - PLAIN-TEXT SEARCH INDEX (NO JAVASCRIPT NEEDED)
Derived index, generated by tools/build_search_index.py from the structured transcripts. Originals unchanged.
It records where words appear, not what they mean. Last updated {updated}.

WHAT THIS IS FOR
search.html needs JavaScript. This folder does the same job with small static text files, so an
AI reader that can only fetch URLs can search every conversation with every AI (Grok, Claude,
ChatGPT, ChatGPT (WhatsApp), Copilot, DeepSeek, Gemini) in a few fetches:
  1. this README (once), 2. search/SHARDS.txt (once), 3. one terms file per word,
  4. the structured transcript files the terms file names, to read or confirm the text.
Every result is a stable conversation ID and message ID from structured/ (see structured/README.txt).

{zero_time}

WHAT WAS INDEXED
  {messages} messages in {conversations} logical conversations (every file in structured/<collection>/).
  Only the CONTENT of each message is indexed, including pasted (embedded) material.
  Headers, titles, speaker labels and web addresses are not indexed.
  {words} distinct words, {references} word-in-message references, {shards} terms files.
  Largest terms file: {largest} bytes. Every terms file is under {max_bytes} bytes and {max_lines} lines.

HOW WORDS ARE WRITTEN IN THE INDEX
  - Lowercase. "Zero" and "zero" are the same word.
  - Apostrophes removed: "Alex's" is "alexs", "don't" is "dont", "it's" is "its".
  - A word is a run of letters or digits. Hyphens and other marks split words:
    "space-time" is two words, "space" and "time". "Möbius" stays "möbius" (accents kept).
  - Words shorter than {min_len} or longer than {max_len} characters are left out.
  - Common English words such as "the", "and", "you", "what" are left out.
    The full list: {site}search/STOPWORDS.txt
  - A small number of words are deliberately excluded at the author's request
    (see tools/build_search_index.py). This is separate from the stopwords.
  - No stemming: "particle" and "particles" are different words. Look up both.

HOW TO FIND THE TERMS FILE FOR A WORD
  1. Write the word as above (lowercase, no apostrophes).
  2. Make its shard key: remove accents (ö -> o, ç -> c), turn every character that is not
     a-z or 0-9 into _, and add one _ at the end.  "titanium" -> "titanium_",
     "möbius" -> "mobius_", "zero" -> "zero_".
  3. Open {site}search/SHARDS.txt. Each row lists one terms FILE and the KEYS it covers.
     Find the longest key, in any row, that is the start of your shard key. FILE on that row is
     the terms file. Example: if a row lists the key "ti", every word whose shard key starts with
     "ti" (and no longer listed key such as "tim") is in that row's FILE.
     Words in non-Latin scripts (Greek, Chinese, ...) all have keys that start with _.
  4. In the terms file, find the line that starts with your word followed by " | ".
     Lines are sorted by shard key. No line means the word is not in any message.

LINE FORMAT IN A TERMS FILE
  word | messages | Alex-own-words messages | conversations | MESSAGES or COMMON | references
  MESSAGES references:  CONVERSATION-ID:NNN,NNN*,NNN; CONVERSATION-ID:NNN
    The message ID is CONVERSATION-ID + "-" + NNN. Example: GROK-001:003* means message GROK-001-003.
    * means the message is Alex's (SPEAKER: ALEX) and the word is in his own text, not only in
    material he pasted from another AI. No * means an AI message, an unlabeled message, or a
    pasted part.
  COMMON references (words in more than {common_limit} messages): CONVERSATION-ID(number of messages).
    Message numbers are not listed for these. Pair the word with a rarer word, or open the
    conversation and search inside it. COMMON words in this build: {common_n}.
  Real example from this build ({ex_path}):
    {ex_line}

WHERE THE TEXT IS
  Conversation file: structured/<collection>/<CONVERSATION-ID>.txt under {site}
    <collection> is the ID without its number, in lowercase: GROK-001 -> grok, CHATGPT-WHATSAPP-012 -> chatgpt-whatsapp.
    Example: {site}structured/grok/GROK-001.txt
    Raw mirror: {raw}structured/grok/GROK-001.txt
  Inside the file, the message starts at the line "----- BEGIN MESSAGE <MESSAGE-ID> -----" and ends at
  "----- END MESSAGE <MESSAGE-ID> -----". A message split across pages has two blocks (-A and -B); read both.
  Each message names SPEAKER, SOURCE_ARTICLE (the original web page and anchor) and its CONTENT.
  Title and date of every conversation: {site}structured/INDEX.txt and the index parts it names.
  Most conversation files are small. A few are over 1 MB; {site}parts/INDEX.txt lists them with byte ranges.

KEYWORD SEARCH (one or more words, anywhere in a message)
  1. Look up each word (see above).
  2. For one word, the references are the answer.
  3. For several words in the same message, keep the message IDs that appear in every list.
     For the same conversation, keep the conversation IDs that appear in every list.
  4. To restrict to one AI, keep only IDs with that prefix (GROK, CLAUDE, CHATGPT, CHATGPT-WHATSAPP,
     COPILOT, DEEPSEEK, GEMINI). Note that CHATGPT-WHATSAPP IDs also start with CHATGPT.
  5. To restrict to Alex's own words, keep only references marked *.

EXACT-PHRASE SEARCH
  1. Split the phrase into words the same way. Ignore stopwords and words under {min_len} letters.
  2. Look up the remaining words. The second field (messages) shows which is rarest. Start with the
     rarest one or two; you do not need all of them.
  3. Keep the message IDs found for every word you looked up.
  4. Fetch each candidate's conversation file and read the message. Confirm the phrase is really
     there, in that order. Compare without caring about capital letters, curly or straight quotes,
     or line breaks. The index only says the words are in the same message.
  5. If no message has all the words, the phrase is not in the archive in that wording.
     Try fewer words, other word forms (singular/plural), or a COMMON word paired with a rare one.
{phrase_example}

LIMITS
  - The structured files are a parse of the original HTML. Speaker labels and the * mark follow that
    parse (see structured/README.txt). If in doubt, open SOURCE_ARTICLE, the original web page.
  - This index is rebuilt and checked automatically (tools/check_site.py fails if it is out of date).
  - Search finds words, not ideas. For a few big subjects, the subject map lists curated matches:
    {site}subject-map/INDEX.txt

FILES
  search/README.txt     this guide
  search/SHARDS.txt     list of terms files (FILE, KEYS, first and last word, size)
  search/STOPWORDS.txt  words left out
  search/index.json     the same information as JSON, with every terms file URL
  search/terms/*.txt    the terms files. Each starts with a 5-line header and names NEXT.
'''.format(updated=LAST_UPDATED, site=SITE, raw=RAW, max_bytes=MAX_SHARD_BYTES, max_lines=MAX_SHARD_LINES,
           min_len=MIN_LEN, max_len=MAX_LEN, common_limit=COMMON_LIMIT, common_n=len(common),
           ex_path=ex_path, ex_line=ex_line, phrase_example=phrase_example, zero_time=zero_time_block(files), largest=stats['largest_shard_bytes'], **stats)
    return lines


def write(files):
    os.makedirs(os.path.join(ROOT, TERMS_DIR), exist_ok=True)
    keep = set(files)
    for name in os.listdir(os.path.join(ROOT, TERMS_DIR)):
        rel = '%s/%s' % (TERMS_DIR, name)
        if rel not in keep:
            os.remove(os.path.join(ROOT, rel))
    for rel, text in files.items():
        path = os.path.join(ROOT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)


def stale_files(files):
    on_disk = set()
    for base, _dirs, names in os.walk(os.path.join(ROOT, OUT_DIR)):
        for name in names:
            on_disk.add(os.path.relpath(os.path.join(base, name), ROOT).replace(os.sep, '/'))
    stale = []
    for rel, text in sorted(files.items()):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path) or read(rel) != text:
            stale.append(rel)
    stale.extend(sorted(on_disk - set(files)))
    return stale


# ---------------------------------------------------------------- lookup (same steps as the README)
def lookup(word):
    shards = []
    for line in read('search/SHARDS.txt').split('\n'):
        parts = line.split(' | ')
        if len(parts) == 6 and parts[0].startswith(TERMS_DIR + '/'):
            for k in parts[1].split(' '):
                shards.append((k, parts[0]))
    key = shard_key(word)
    best = max((s for s in shards if key.startswith(s[0])), key=lambda s: len(s[0]), default=None)
    if not best:
        return None, None
    for line in read(best[1]).split('\n'):
        if line.startswith(word + ' | '):
            return best[1], line
    return best[1], None


def parse_refs(line):
    fields = line.split(' | ', 5)
    out = {}
    if fields[4] == 'COMMON':
        for item in fields[5].split('; '):
            out[item.split('(')[0]] = None
    else:
        for item in fields[5].split('; '):
            cid, seqs = item.split(':')
            out[cid] = [s.rstrip('*') for s in seqs.split(',')]
    return fields, out


def message_text(cid, mid):
    text = read(structured_rel(cid))
    parts = re.findall(r'----- BEGIN MESSAGE %s(?:-[A-Z])? -----\n(.*?)\n----- END MESSAGE %s' % (re.escape(mid), re.escape(mid)), text, re.S)
    body = []
    for p in parts:
        content = p.split('\nCONTENT:\n', 1)[1].rsplit('\nEND CONTENT', 1)[0]
        body.append('\n'.join(l for l in content.split('\n')
                              if l not in ('EMBEDDED MATERIAL:', 'END EMBEDDED MATERIAL') and not l.startswith('ORIGINAL SPEAKER: ')))
    return '\n'.join(body)


def squash(text):
    text = text.replace('\u2019', "'").replace('\u2018', "'").replace('\u201c', '"').replace('\u201d', '"')
    return re.sub(r'\s+', ' ', text).strip().lower()


def search(query):
    words = []
    for w in words_of(query):
        if w not in words:
            words.append(w)
    print('Query: %r' % query)
    print('Indexed words in the query: %s' % (', '.join(words) or '(none)'))
    found = {}
    for w in words:
        rel, line = lookup(w)
        if line is None:
            print('  %s: not in the index (terms file %s)' % (w, rel))
            found[w] = None
            continue
        fields, refs = parse_refs(line)
        print('  %s: %s messages, %s with * , %s conversations, %s (terms file %s)' % (w, fields[1], fields[2], fields[3], fields[4], rel))
        found[w] = (int(fields[1]), refs)
    if not words or any(v is None for v in found.values()):
        print('Result: no message contains every indexed word.')
        return []
    ranked = sorted(words, key=lambda w: found[w][0])
    candidates = None
    for w in ranked:
        refs = found[w][1]
        if any(v is None for v in refs.values()):
            continue  # COMMON word, conversation-level only; used below as a filter
        ids = set('%s-%s' % (cid, s) for cid, seqs in refs.items() for s in seqs)
        candidates = ids if candidates is None else candidates & ids
    if candidates is None:
        convs = set.intersection(*(set(found[w][1]) for w in words))
        print('Result: only COMMON words; %d conversations contain all of them.' % len(convs))
        return sorted(convs)
    for w in ranked:
        candidates = set(m for m in candidates if m.rsplit('-', 1)[0] in found[w][1])
    print('Messages with every indexed word: %d' % len(candidates))
    phrase = squash(query)
    confirmed = []
    for mid in sorted(candidates):
        cid = mid.rsplit('-', 1)[0]
        if phrase in squash(message_text(cid, mid)):
            confirmed.append(mid)
    print('Messages that contain the exact phrase (confirmed in structured files): %d' % len(confirmed))
    for mid in confirmed[:10]:
        cid = mid.rsplit('-', 1)[0]
        print('  %s  %s%s' % (mid, SITE, structured_rel(cid)))
    return confirmed


def main(argv):
    if '--search' in argv:
        query = ' '.join(argv[argv.index('--search') + 1:])
        search(query)
        return 0
    files = build()
    if '--check' in argv:
        stale = stale_files(files)
        for rel in stale:
            print('differs from a fresh build: %s' % rel)
        if stale:
            print('Run: python3 tools/build_search_index.py')
            return 1
        print('The search index equals a fresh build (%d files).' % len(files))
        return 0
    write(files)
    print('Wrote %d files.' % len(files))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
