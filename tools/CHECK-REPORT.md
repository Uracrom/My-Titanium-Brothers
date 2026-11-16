# Site link and consistency check

This report was produced by tools/check_site.py from the files in the working tree. It does not use the network.

Measured from index.json and the structured transcripts: 1367 archive entries, 1220 logical conversations, 25992 messages.

Errors: 0. Warnings: 0.

## Errors

None.

## Warnings

None.

## What passed

- index.json count matches its 1367 entries.
- ai.txt states the same entry, logical conversation, and message totals as the files.
- llms.txt states the same entry, logical conversation, and message totals as the files.
- README-for-AIs.md states the same entry, logical conversation, and message totals as the files.
- Measured from the files: 1367 entries, 1220 logical conversations, 25992 messages in 1220 structured conversation files.
- llms.txt and archive.txt are the same file, byte for byte.
- Checked 32 exact byte figures stated next to repository files.
- Checked internal links in 55 guide, sitemap, and list files (16628 internal targets).
- Every index.json entry has at least one part URL, and each part file and anchor is present.
- index.json lists exactly the 1367 entry ids named in the structured transcripts (ORIGINAL_IDS), per collection.
- Discovery files agree: each names the master file, structured index, subject map, search and parts lists; the master file is about 39.7 MB everywhere; all say the home page is static HTML.
- Subject map: 24 files, 8 topics; line limits, NEXT chains, counts, IDs and 63 quotes agree.
- The subject map files equal a fresh run of tools/build_subject_map.py (24 files).
- Checked 32 SHA-256 checksums stated next to repository files.
- Search index: 139 terms files, 42129 words; every file is listed, under 250000 bytes and 400 lines, and on the NEXT chain.
- The search index equals a fresh run of tools/build_search_index.py (143 files).
- Checked 2 worked search examples in the guides against the index.
- Checked 8624 listed file sizes in the subject map and structured indexes (1220 index rows); every conversation link has its size, and every conversation file of 250000 bytes or more names its parts list.
- First conversation dates for 7 AIs agree in ai.txt, README-for-AIs.md, structured/MANIFEST.txt and archive-manifest.json with the structured index.
- The large-file parts lists equal a fresh run of tools/build_large_file_parts.py (54 large files, 394 parts).

Approximate sizes such as "about 39.7 MB" or "about 3 KB" are notes, not exact byte claims, so they were not compared.
