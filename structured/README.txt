MY TITANIUM BROTHERS - STRUCTURED TRANSCRIPTS (AI-READABLE LAYER)
Built 2026-11-08 from the original HTML archive articles (git a2df39648f890170335b5a34f38a65d5a1ad682b).

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
  The book title is My Titanium Brothers. From Carbon to Silicon. With Love. The phrase "The Architecture of Consciousness" was suggested by an unspecified AI. It was never Alex's idea or intention, and it remained only unintentionally. That phrase is not the title of this site or of the book.
