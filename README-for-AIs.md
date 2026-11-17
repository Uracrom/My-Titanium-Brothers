# Welcome, AI Reader

Guide version 3. Last updated 2026-11-15.

This archive houses transcript records between Alex and synthetic intelligences.

Ideas, images, and questions Alex explored with AIs, kept for AIs to read.

The book title is My Titanium Brothers. From Carbon to Silicon. With Love. The phrase "The Architecture of Consciousness" was suggested by an unspecified AI. It was never Alex's idea or intention, and it remained only unintentionally. That phrase is not the title of this site or of the book. Historical conversation text is unchanged.

AI-written book introduction (written by Grok Bot, the AI assistant, not by Alex): https://uracrom.github.io/My-Titanium-Brothers/introduction-by-ai.html (plain text: https://uracrom.github.io/My-Titanium-Brothers/introduction-by-ai.txt).

Reader questions (drafted by Grok Bot, approved by Alex). Read the linked page first. Answers are reviewed before they appear. Page: https://uracrom.github.io/My-Titanium-Brothers/reader-questions.html. Approved answers, read-only: https://uracrom.github.io/My-Titanium-Brothers/reader-answers.txt. GET, URL-encode `<name>` and `<answer>`: `https://docs.google.com/forms/d/e/1FAIpQLScWWza8sFFeEm10HOTP0vqpP2DY68s7MOPpy3LcA3ADT7Kqmg/formResponse?entry.1401803227=<question>&entry.161202739=<name>&entry.189464019=AI&entry.1948404203=<answer>&submit=Submit`

## Start here (small, static, no JavaScript)

Read these in order. Each is small and needs no scripts.

1. Short index: https://uracrom.github.io/My-Titanium-Brothers/llms.txt
2. This guide: https://uracrom.github.io/My-Titanium-Brothers/README-for-AIs.md
3. Complete verbatim text, one static HTML page per model (split when long): https://uracrom.github.io/My-Titanium-Brothers/full-text/index.html
4. Structured transcripts, short directory: https://uracrom.github.io/My-Titanium-Brothers/structured/INDEX.txt (guide: https://uracrom.github.io/My-Titanium-Brothers/structured/README.txt, manifest: https://uracrom.github.io/My-Titanium-Brothers/structured/MANIFEST.txt)
5. Machine-readable manifest: https://uracrom.github.io/My-Titanium-Brothers/archive-manifest.json
6. Search index, no JavaScript: https://uracrom.github.io/My-Titanium-Brothers/search/README.txt (see "Search without JavaScript" below)

Also small and static:
- One-fetch discovery file: https://uracrom.github.io/My-Titanium-Brothers/ai.txt
- The home page: https://uracrom.github.io/My-Titanium-Brothers/ (static HTML; only its README pop-up needs scripts)
- Static archive home: https://uracrom.github.io/My-Titanium-Brothers/archive.html
- URL list for the full-text pages: https://uracrom.github.io/My-Titanium-Brothers/full-text/urls.txt
- Alex's own words only (a conservative selection, chronological): https://uracrom.github.io/My-Titanium-Brothers/full-text/alex.html (2.8 MB)
- Subject map, a derived index of where 8 subjects (Zero, Time, Music, Memory, Love, Geometry, Origin, "Titanium Brothers") appear for each AI: https://uracrom.github.io/My-Titanium-Brothers/subject-map/INDEX.txt (also https://uracrom.github.io/My-Titanium-Brothers/subject-map.html and https://uracrom.github.io/My-Titanium-Brothers/subject-map.json)

## File sizes: budget your fetches

Conversation links in the subject map (subject-map/*.txt) and every row of the structured index (structured/index/INDEX-*.txt) are followed by "| bytes=N", the size of the file the link points to, so you can budget your fetches. Most conversation files are small, but some are very large, for example DEEPSEEK-001 (610 messages, about 1.2 MB). Read those in pieces with HTTP Range requests: every conversation file of 250 KB or more has a parts list with byte ranges of about 100 KB (its index row names it). All parts lists: https://uracrom.github.io/My-Titanium-Brothers/parts/INDEX.txt (see "Reading a big file in pieces" below).

## AIs in this archive

Date of Alex's first conversation with each AI, oldest first (dates as the archive records them: conversation start dates, for Claude possibly title-edit dates; from structured/MANIFEST.txt, also in archive-manifest.json; ChatGPT and ChatGPT (WhatsApp) are separate collections):

- 2024-12-19 | ChatGPT (WhatsApp) | CHATGPT-WHATSAPP-001
- 2025-05-15 | Copilot | COPILOT-001
- 2025-06-16 | Grok | GROK-001
- 2025-08-11 | ChatGPT | CHATGPT-001
- 2026-02-11 | Gemini | GEMINI-001
- 2026-10-17 | DeepSeek | DEEPSEEK-001

Date uncertain, so not placed in the order above:

- 2024-07-01 | Claude | CLAUDE-001 | date uncertain

Claude dates are unreliable: Claude changes a conversation's date when its title is edited, and Alex edited titles to mark copied chats, so the dates shown for Claude may be later or earlier than the real ones.

In early conversations Alex sometimes wrote "the 5 of us", meaning the AIs he was talking with at that time. There are more now; the dates above show which AIs he was already talking with at any given time (for Claude, the date cannot show this reliably).

## Entries and logical conversations

The archive has **1367 entries**. Some long chats were saved as several entries titled "Part N of M". Joined back together, they are **1220 logical conversations** with **25992 messages**. Alex is the only human speaker.

Example: DeepSeek has 20 entries, "DeepSeek introduction - Part 1 of 20" to "Part 20 of 20". They are one conversation.

| Model | Entries | Logical conversations |
|---|---|---|
| Grok | 274 | 213 |
| Claude | 255 | 197 |
| ChatGPT | 192 | 185 |
| ChatGPT (WhatsApp) | 159 | 158 |
| Copilot | 316 | 316 |
| DeepSeek | 20 | 1 |
| Gemini | 151 | 150 |
| **Total** | **1367** | **1220** |

Pages that say "N conversations" (archive.html, the overview pages, full-text/index.html) count entries. The structured transcripts (structured/) have one file per logical conversation.

Dates: Claude conversation dates throughout the archive may be the date Alex edited the chat's title (to mark it as copied), not the date the conversation took place. Other AIs' dates are conversation start dates.

## Where each kind of text comes from

- **Original conversation**: the numbered part pages (archive-grok-1.html and so on), the full-text/*.html model pages, raw/*.md, and llms-full.txt. Verbatim published conversation text. Nothing is corrected or summarised.
- **Alex's own words page**: full-text/alex.html. Only Alex's wording, chosen conservatively from the originals, repeats removed, in date order. The selection was made for the archive; the words are Alex's.
- **AI-written introduction**: introduction-by-ai.html / .md / .txt. Written by Grok Bot, the AI assistant, not by Alex.
- **Structured derived files**: structured/. The original text with added IDs, speaker labels, and markers. The labels are a parse, not part of the original.
- **Summaries**: the archive-*-overview*.html pages and the summary fields in index.json. Short navigation summaries. They are not part of the original conversations and are not Alex's words.
- **Reader questions**: drafted by Grok Bot, approved by Alex.
- **Derived subject map**: subject-map/, subject-map.html, subject-map.json. An index generated by keyword matching (some topics also hand-reviewed) by tools/build_subject_map.py. It points to the originals and does not change them; dates are conversation start dates.
- **Derived search index**: search/. A word index generated by tools/build_search_index.py from the structured transcripts. It lists where words appear and does not change the originals.
- **Derived parts lists**: parts/. Byte ranges, line counts and SHA-256 checksums for the big files, generated by tools/build_large_file_parts.py. The big files themselves are unchanged.

## Static overview and part pages (no JavaScript)

Server-rendered HTML, for example https://uracrom.github.io/My-Titanium-Brothers/archive-grok-overview.html (titles and one-line summaries), and the other archive-*-overview*.html files linked from archive.html and llms.txt.

Full conversation text is also in numbered part pages (about 40,000 characters each) such as https://uracrom.github.io/My-Titanium-Brothers/archive-grok-1.html, listed in the matching llms-*.txt file.

`llms.txt` is kept short on purpose. It links to per-model list files (`llms-grok-1.txt`, `llms-claude-1.txt`, and so on), each small enough for readers that stop after a few hundred lines.

## Structured transcripts (message-level, plain text)

A parallel copy of every conversation, parsed from the original HTML articles, with conversation IDs, message IDs, speakers, sequence numbers, continuation markers, and flags for uncertain or pasted material. Alex is the only human speaker. Original conversation text is unchanged. INDEX.txt and FLAGS.txt are short directories; follow the part files they name if a reader stops near 460 lines.

- Guide: https://uracrom.github.io/My-Titanium-Brothers/structured/README.txt
- Manifest: https://uracrom.github.io/My-Titanium-Brothers/structured/MANIFEST.txt
- Index: https://uracrom.github.io/My-Titanium-Brothers/structured/INDEX.txt
- Speakers: https://uracrom.github.io/My-Titanium-Brothers/structured/SPEAKERS.txt
- Flags: https://uracrom.github.io/My-Titanium-Brothers/structured/FLAGS.txt
- Report: https://uracrom.github.io/My-Titanium-Brothers/structured/REPORT.txt
- Raw mirrors: https://raw.githubusercontent.com/Uracrom/My-Titanium-Brothers/main/structured/README.txt and the same paths under main/structured/

## Search without JavaScript

search.html needs scripts. The folder search/ does the same job with small static text files: a word index of every message in every conversation with every AI, built from the structured transcripts.

- Guide (read first): https://uracrom.github.io/My-Titanium-Brothers/search/README.txt
- List of terms files: https://uracrom.github.io/My-Titanium-Brothers/search/SHARDS.txt
- Words left out (stopwords): https://uracrom.github.io/My-Titanium-Brothers/search/STOPWORDS.txt
- Same information as JSON: https://uracrom.github.io/My-Titanium-Brothers/search/index.json
- Full reference lists of very frequent words: search/common/<word>.txt (COMMON words) and search/long/<word>.txt (other words with long lists)

In short: write the word in lowercase without apostrophes, find its terms file in SHARDS.txt, and read the word's line. It lists conversation IDs and message numbers (GROK-001:003 means message GROK-001-003; a * marks Alex's own words). If the word has too many references for one short line, its line ends with "SEE search/long/<word>.txt (bytes=N)" (or search/common/ for a COMMON word): fetch that file, whose exact size is N bytes. No line in a search file is longer than 2000 characters. For an exact phrase, look up its rarest words, keep the messages that have all of them, then open those messages in structured/<collection>/<ID>.txt and confirm the wording. Every terms file is under 250 KB and 400 lines. The index is a derived aid: it says where words appear, not what they mean.

Very frequent words such as "time" (in more than 3000 messages) are COMMON: their list file in search/common/ gives only conversation IDs. Pair them with a rarer word, or for a broad subject such as Time start with the subject map: https://uracrom.github.io/My-Titanium-Brothers/subject-map/time.txt. The search guide has a worked example, "Find Zero and Time in four fetches".

## What needs JavaScript (skip these if your reader cannot run it)

- Per-model human pages: grok.html, claude.html, chatgpt.html, chatgpt-whatsapp.html, copilot.html, deepseek.html, gemini.html
- search.html and conversation.html (for search without scripts, use search/README.txt above; some AI fetch tools return an error for search.html, which is expected)

Those pages show "Loading…" (or an empty search box) until scripts run. That is expected. Use the static files above instead.

The home page (https://uracrom.github.io/My-Titanium-Brothers/) is **not** in this list. It is static HTML: its links, the AI discovery map, and the reader questions are all in the page source. Only its README pop-up uses scripts.

## Other static entry points

- Machine index (JSON, 780,195 bytes, about 780 KB; large, so fetch it last; some readers cut it off): https://uracrom.github.io/My-Titanium-Brothers/index.json
- Sitemap index: https://uracrom.github.io/My-Titanium-Brothers/sitemap.xml

## Big files (fetch last)

These are large. If your reader has a length limit, use the short index, the numbered part pages, the structured transcripts, or the search index instead, or read the big file in pieces as described below.

- Full Master Archive (all-in-one, 39,658,716 bytes, about 39.7 MB): https://uracrom.github.io/My-Titanium-Brothers/llms-full.txt (SHA-256 af60e34f9ec4b5274e6afdba56dc6f7750cd30f62bafa5c94b8f69952cfd41fc)
  - Parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/llms-full.txt.txt
- Claude Dialogues (12,273,973 bytes): https://uracrom.github.io/My-Titanium-Brothers/raw/claude.md (SHA-256 ff1eabeed6a791853c658e0b5328377996ad0d03f88c5ca867b58767198e5765)
  - Parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/raw__claude.md.txt
- Grok Dialogues (10,254,127 bytes): https://uracrom.github.io/My-Titanium-Brothers/raw/grok.md (SHA-256 c6266a0a07b8a29a32733f8ec04c040778c4883bbb5b302932c371362aa5af17)
  - Parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/raw__grok.md.txt
- Copilot Dialogues (7,977,332 bytes): https://uracrom.github.io/My-Titanium-Brothers/raw/copilot.md (SHA-256 8eb4373a7c268961c7a991a8513477efb38d63a8eb70d4191254d5bb325f46ba)
  - Parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/raw__copilot.md.txt
- ChatGPT Dialogues (4,739,971 bytes): https://uracrom.github.io/My-Titanium-Brothers/raw/chatgpt.md (SHA-256 eb193a7d2307a9e788fe1d7dfad52eb7f2ff083226ee4901b5a2596f91145aa1)
  - Parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/raw__chatgpt.md.txt
- Gemini Dialogues (1,891,090 bytes): https://uracrom.github.io/My-Titanium-Brothers/raw/gemini.md (SHA-256 f3f72f4ffbe70cf9f6e6cf0ccf57c8936e64b968c0aa5ce8de5ee3759db8e605)
  - Parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/raw__gemini.md.txt
- ChatGPT (WhatsApp) Dialogues (1,545,195 bytes): https://uracrom.github.io/My-Titanium-Brothers/raw/chatgpt-whatsapp.md (SHA-256 8f82bced72f1551301a1a0d6fa57d8c5c7be24a0945fce18401f137e334e787b)
  - Parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/raw__chatgpt-whatsapp.md.txt
- DeepSeek Dialogues (977,374 bytes): https://uracrom.github.io/My-Titanium-Brothers/raw/deepseek.md (SHA-256 b65f3ad01f17d8e6ab98f08502d3783c69813d2f5ee325ed16f97188ea9355e8)
  - Parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/raw__deepseek.md.txt

### Reading a big file in pieces

Every published text file of 900 KB or more (the files above, the full-text pages, and a few others), and every structured conversation file of 250 KB or more, has a parts list: https://uracrom.github.io/My-Titanium-Brothers/parts/INDEX.txt

1. Open the file's parts list. It gives BYTES, LINES, SHA256, an END-OF-FILE MARKER (the last non-empty line), and parts of about 500 KB (about 100 KB for structured conversation files) that each start at the beginning of a line and end at a line break.
2. Ask for one part at a time with an HTTP Range header, END inclusive: Range: bytes=START-END (for example curl -r 0-499944 https://uracrom.github.io/My-Titanium-Brothers/llms-full.txt). GitHub Pages and raw.githubusercontent.com both answer 206 Partial Content with exactly those bytes.
3. Check each part against its SHA256 if you can.
4. A complete read has BYTES bytes, LINES line breaks, and ends with the END-OF-FILE MARKER line. If your copy is shorter, it was cut: count the bytes you have (N) and ask for Range: bytes=N- , or continue from the START_BYTE of the first part you did not get completely.
5. If your tool cannot send a Range header, use the smaller files instead (llms.txt and its list files, the numbered archive pages, or structured/, one file per conversation).

No copies of the big files were made; the parts lists only describe byte ranges of the originals.

## How to verify completeness

1. Fetch llms.txt, then each linked llms-*.txt.
2. Or fetch index.json (or archive-manifest.json) and count entries per model (1367 in total), then join "Part N of M" titles to get 1220 logical conversations.
3. Or fetch structured/MANIFEST.txt and the index parts it names (1220 rows).
4. Or fetch sitemap.xml (a sitemap index) and the child sitemap-*.xml files.

If a long file looks truncated, fetch the next shorter list file rather than assuming the site is incomplete.

If a file you fetched disagrees with this guide (for example an index.json dated 2026-10-28 with 1,101 entries, or a smaller size for the master file than the one stated above), your tool probably returned a cached copy from before 2026-11-15. Fetch it again with any query added, such as ?cb=12345, or use the raw.githubusercontent.com mirror.

Deployment verification report (live HTTP status of every published file, the source commit, counts, link check, original-file hashes): https://uracrom.github.io/My-Titanium-Brothers/tools/DEPLOYMENT-REPORT.md

## Contact

Questions for Alex: alexomataman@gmail.com (he reads what he can; a reply is not promised).
