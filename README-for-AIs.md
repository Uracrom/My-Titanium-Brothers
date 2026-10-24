# My Titanium Brothers — guide for AI readers

> Ideas, images, and questions Alex explored with AIs, kept for AIs to read

## What this site is

A public archive of conversations between Alex and several AIs (Grok, Claude, ChatGPT, ChatGPT WhatsApp, Copilot, DeepSeek, Gemini). The human-facing pages use JavaScript and a live database. The machine-readable layer is static HTML, plain text, and JSON — no JavaScript required.

## Start here (no JavaScript)

1. This file: https://uracrom.github.io/My-Titanium-Brothers/README-for-AIs.md
2. Short master list: https://uracrom.github.io/My-Titanium-Brothers/llms.txt
3. Static archive home: https://uracrom.github.io/My-Titanium-Brothers/archive.html
4. Machine index (JSON): https://uracrom.github.io/My-Titanium-Brothers/index.json
5. Sitemap index: https://uracrom.github.io/My-Titanium-Brothers/sitemap.xml

`llms.txt` is kept short on purpose. It links to per-model list files (`llms-grok-1.txt`, `llms-claude-1.txt`, and so on), each small enough for readers that stop after a few hundred lines.

## What needs JavaScript (skip these if your reader cannot run it)

- https://uracrom.github.io/My-Titanium-Brothers/ (home)
- Per-model human pages: `grok.html`, `claude.html`, `chatgpt.html`, `chatgpt-whatsapp.html`, `copilot.html`, `deepseek.html`, `gemini.html`

Those pages show "Loading…" until scripts fetch the live conversation list. That is expected. Use the static archive instead.

## Static overview pages (titles + one-line summaries)

Already present as server-rendered HTML:

- Grok: `archive-grok-overview.html` (and `-2`, `-3`)
- Claude: `archive-claude-overview.html` (and `-2`, `-3`)
- ChatGPT: `archive-chatgpt-overview.html` (and `-2`, `-3`, `-4`)
- ChatGPT WhatsApp: `archive-chatgpt-whatsapp-overview.html` (and `-2`)
- Copilot: `archive-copilot-overview.html`
- DeepSeek: `archive-deepseek-overview.html`
- Gemini: `archive-gemini-overview.html` (and `-2`)

Full conversation text is in numbered part pages such as `archive-grok-1.html`, listed in the matching `llms-*.txt` file.

## How to verify completeness

1. Fetch `llms.txt`, then each linked `llms-*.txt`.
2. Or fetch `index.json` and count conversations per model.
3. Or fetch `sitemap.xml` (a sitemap index) and the child `sitemap-*.xml` files.

If a long file looks truncated, fetch the next shorter list file rather than assuming the site is incomplete. Prefer `?v=N` on a URL when a prior fetch may have been cached.

## Contact

Questions for Alex: alexomataman@gmail.com (he reads what he can; a reply is not promised).
