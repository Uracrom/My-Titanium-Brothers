MY TITANIUM BROTHERS - STRUCTURED TRANSCRIPTS (AI-READABLE LAYER)
Built 2026-11-06 from the published archive (source commit 4968b7e, archive index generated 2026-10-28).

WHAT THIS IS
This folder is an additional, parallel copy of the archive's conversations in plain UTF-8 text,
with explicit structure added AROUND the original text. The existing website pages
(archive-*.html, raw/*.md, llms*.txt, the interactive pages) are unchanged and remain the primary source.
Each file here lists the exact original page(s) it was built from (ORIGINAL_URLS), so any line can be checked.

ORIGINAL TEXT IS UNCHANGED
Everything between "CONTENT:" and "END CONTENT" is the original message text copied character for
character from the original page (only HTML escapes such as &amp; were decoded to the characters they
stand for). Nothing was corrected, translated, summarised, or removed. Interface leftovers (icons,
"Show less", timestamps, etc.) were kept because they are part of the original capture.
The only lines added inside CONTENT are the three embedded-material marker lines described below.

FILES
  README.txt    this guide
  INDEX.txt     every logical conversation: ID, collection, date, title, original ids, file, counts
  SPEAKERS.txt  speaker values and counts, persona names
  FLAGS.txt     everything that needs human/AI inspection or is UNCERTAIN
  REPORT.txt    build and verification report
  <collection>/<ID>.txt   one file per logical conversation
Collections/folders: grok, claude, chatgpt, chatgpt-whatsapp, copilot, deepseek, gemini.

IDS
  Conversation ID: PREFIX-NNN, e.g. CLAUDE-025. Prefixes: GROK, CLAUDE, CHATGPT, CHATGPT-WHATSAPP,
  COPILOT, DEEPSEEK, GEMINI. Numbered oldest first inside each collection (date, then title, then
  original id). So the collection files read in numeric order are in chronological order.
  Message ID: CONVERSATION-NNN, e.g. CLAUDE-025-014; SEQUENCE is NNN (001, 002, ...) in original order.
  A message split across original pages has parts with block IDs CLAUDE-025-014-A, -B, ... ;
  all parts share MESSAGE: CLAUDE-025-014.
  ORIGINAL_ID is the archive's own database id; ORIGINAL_URL the published page and anchor.

FILE LAYOUT
  Header: CONVERSATION, TITLE, COLLECTION, DATE, ORIGINAL_IDS, ORIGINAL_TITLES, ORIGINAL_URLS,
  GROUPING, counts, one SOURCE_ENTRY line per original archive entry.
  Then, for each original page section in order:
    ===== SOURCE SEGMENT k of n | ORIGINAL_ID .. | Part .. | HTML piece .. | SOURCE_ARTICLE file#anchor | ORIGINAL_URL .. =====
    ----- BEGIN SEGMENT PREAMBLE ... -----   (original lines before the first message: blank lines,
    ----- END SEGMENT PREAMBLE -----          or a "Part N of M" heading. Not a message.)
    message blocks:
    ----- BEGIN MESSAGE GROK-007-003 -----
    MESSAGE: GROK-007-003
    SPEAKER: GROK
    SEQUENCE: 003
    SPEAKER_LABEL_IN_ORIGINAL: Grok        (the exact label line from the page, or "(none)")
    SOURCE_ARTICLE: archive-grok-12.html#anchor
    CONTENT:
    ...original text...
    END CONTENT
    ----- END MESSAGE GROK-007-003 -----
  The file ends with ===== END CONVERSATION ID =====.

SPEAKERS
  In the original pages a speaker change is a line containing only a speaker name ("Alex", "Claude",
  "Grok", "ChatGPT", "Chat GPT", "Gemini", "Copilot", "DeepSeek"...). That label line is shown in
  SPEAKER_LABEL_IN_ORIGINAL and is not repeated in CONTENT.
  Values: ALEX (the human author), GROK, CLAUDE, CHATGPT (also used in the WhatsApp collection),
  COPILOT, GEMINI, DEEPSEEK, SYSTEM (platform service notice), UNKNOWN (not established).
  Only "Alex" and the collection's own AI name split messages. Other AI names and persona names
  (Axiom, Vanamonde, Claude-7, Vertex, ...) appearing on their own line inside a message were NOT
  treated as speaker changes and were NOT classified as Alex; each is listed in FLAGS.txt as UNCERTAIN.
  So: text that follows such a line is stored under the message's speaker but its authorship is flagged.

FIRST MESSAGE IS ALEX
  Archive convention: every conversation starts with a message by Alex, even if no name is shown.
  At a VERIFIED conversation start (a single entry, or Part 1 of a Part N of M group) the first message
  is SPEAKER: ALEX. If the page shows no label, SPEAKER_LABEL_IN_ORIGINAL is "(none)" and ALEX was
  assigned by this convention (the name was not inserted into the text). If a start were explicitly
  labeled as an AI, the label would be kept and flagged (none were found).
  The rule is NOT applied to the top of a later web page, an "HTML piece 2 of n", or "Part 2+" of a group:
  text there without a label is a continuation of the previous message.

CONTINUATIONS
  The website splits long conversations into page sections ("continued, piece 2 of 3") and some
  conversations were imported as several entries ("Title - Part 2 of 10"). When a section starts in the
  middle of a message, the message is stored in parts:
    end of part A:      CONTINUATION FOLLOWS: / MESSAGE ID: X-015 / NEXT PART: X-015-B
    start of part B:    CONTINUATION OF: / MESSAGE ID: X-015 / PREVIOUS PART: X-015-A / SPEAKER: ..
  Every CONTINUATION FOLLOWS has exactly one matching CONTINUATION OF. Where a new section begins with a
  speaker label, a NOTE line says so; no message was split there. No missing text was invented.

PART N OF M GROUPING
  Archive entries in the same collection whose titles are "<same title> - Part N of M" are one logical
  conversation and share one ID and one file, joined in part order. Each original entry is still listed
  (SOURCE_ENTRY lines, ORIGINAL_IDS, ORIGINAL_URLS) so nothing disappears. Example: the 20 DeepSeek
  entries "DeepSeek introduction - Part 1..20 of 20" are DEEPSEEK-001.

EMBEDDED / PASTED MATERIAL
  Alex sometimes pastes text from other AI conversations into his messages. Only strong signals were
  marked, inside CONTENT, with these added lines (not original text; remove them to get the original):
    EMBEDDED MATERIAL:
    ORIGINAL SPEAKER: UNCERTAIN | MIXED (...)
    ...original pasted text, unchanged...
    END EMBEDDED MATERIAL
  Signals used: a line like "From another conversation with another AI" (marked from the next line to
  the end of that message part, ORIGINAL SPEAKER: UNCERTAIN, because such pastes can contain Alex's own
  answers), and pasted transcripts with "You said:" / "<AI> said:" turns (ORIGINAL SPEAKER: MIXED).
  This classification is conservative and NOT complete: an ALEX message without marks may still contain
  quoted or pasted text. AI messages that quote Alex stay under the AI speaker.

REBUILDING THE ORIGINAL
  For each SOURCE SEGMENT: preamble lines, then for each message block the SPEAKER_LABEL_IN_ORIGINAL
  line (unless "(none)") followed by the CONTENT lines (minus the three embedded marker lines), all joined
  with newlines, equals the original page section text exactly. This was checked for all sections.
