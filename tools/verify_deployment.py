#!/usr/bin/env python3
"""Check what GitHub Pages actually serves, and write a deployment verification report.

Standard library only. Needs network access, so it is not part of CI. It:
  1. lists every file in the working tree that GitHub Pages publishes (everything except
     .git and .github; the site has .nojekyll, so nothing else is hidden),
  2. requests each one from the live site (HEAD, with a cache-busting query) and records the
     real HTTP status, Content-Type and Content-Length, comparing the length with the local file,
  3. downloads the guide files in full and compares their SHA-256 with the local files,
  4. reads the public GitHub Actions runs for the commit (Pages deployment and the checks),
  5. runs tools/check_site.py and tools/structured/verify.py locally,
and writes tools/DEPLOYMENT-REPORT.md plus a full table, tools/DEPLOYMENT-URLS.tsv.

The live site should be the same commit as the working tree; give that commit with --commit.

Usage:
  python3 tools/verify_deployment.py --commit <sha> [--root <repo dir>] [--workers 16]
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import random
import subprocess
import sys
import urllib.parse
import urllib.request

SITE = 'https://uracrom.github.io/My-Titanium-Brothers/'
API = 'https://api.github.com/repos/Uracrom/My-Titanium-Brothers'
FULL_COMPARE = (
    '', 'index.html', 'ai.txt', 'llms.txt', 'archive.txt', 'README-for-AIs.md', 'archive-manifest.json',
    'index.json', 'sitemap.xml', 'sitemap-site.xml', 'robots.txt', 'introduction-by-ai.txt',
    'structured/README.txt', 'structured/INDEX.txt', 'structured/MANIFEST.txt',
    'subject-map/INDEX.txt', 'subject-map.json', 'search/README.txt', 'search/SHARDS.txt',
    'search/index.json', 'parts/INDEX.txt', 'parts/index.json', 'full-text/index.html', 'full-text/urls.txt',
)
GROUPS = (
    ('structured/', 'structured transcripts'), ('subject-map', 'subject map'), ('search/', 'search index'),
    ('parts/', 'parts lists'), ('raw/', 'raw transcripts'), ('full-text/', 'full-text pages'),
    ('archive-', 'archive pages (archive-*.html)'), ('readme/', 'readme pop-up texts'), ('tools/', 'tools'),
    ('docs/', 'docs'), ('conversations/', 'conversations folder'),
)


def published_files(root):
    out = []
    for base, dirs, names in os.walk(root):
        rel_base = os.path.relpath(base, root).replace(os.sep, '/')
        if rel_base == '.':
            dirs[:] = [d for d in dirs if d not in ('.git', '.github')]
        dirs[:] = [d for d in dirs if d != '__pycache__']  # local Python cache, not in git
        for name in names:
            rel = name if rel_base == '.' else rel_base + '/' + name
            if rel.startswith('.git'):
                continue
            out.append(rel)
    return sorted(out)


def group_of(rel):
    for prefix, label in GROUPS:
        if prefix == 'archive-' and not rel.endswith('.html'):
            continue
        if rel.startswith(prefix):
            return label
    return 'root files'


def fetch(url, method='HEAD', tries=3):
    last = None
    for _ in range(tries):
        req = urllib.request.Request('%s?cb=%d' % (url, random.randint(1, 10 ** 9)), method=method,
                                     headers={'User-Agent': 'mtb-deployment-check'})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = resp.read() if method == 'GET' else b''
                return resp.status, resp.headers.get('Content-Type', ''), resp.headers.get('Content-Length'), body
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get('Content-Type', ''), exc.headers.get('Content-Length'), b''
        except Exception as exc:  # network hiccup: retry
            last = exc
    return 0, 'error: %s' % last, None, b''


def check_one(root, rel):
    url = SITE + urllib.parse.quote(rel)
    status, ctype, length, _ = fetch(url)
    local = os.path.getsize(os.path.join(root, rel)) if rel else None
    size_ok = (length is not None and local is not None and int(length) == local)
    return dict(path=rel or '(home page)', url=url, status=status, content_type=ctype,
                length=length, local=local, size_ok=size_ok)


def full_sha(commit):
    try:
        with urllib.request.urlopen(urllib.request.Request(
                '%s/commits/%s' % (API, commit), headers={'User-Agent': 'mtb-deployment-check'}), timeout=60) as resp:
            return json.load(resp)['sha']
    except Exception:
        return commit


def actions(commit):
    try:
        with urllib.request.urlopen(urllib.request.Request(
                '%s/actions/runs?head_sha=%s&per_page=50' % (API, commit),
                headers={'User-Agent': 'mtb-deployment-check'}), timeout=60) as resp:
            runs = json.load(resp).get('workflow_runs', [])
    except Exception as exc:
        return None, str(exc)
    return [dict(name=r['name'], event=r['event'], status=r['status'], conclusion=r['conclusion'],
                 created=r['created_at'], url=r['html_url']) for r in runs], None


def run(root, args):
    proc = subprocess.run([sys.executable] + args, cwd=root, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', required=True)
    ap.add_argument('--root', default=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    ap.add_argument('--workers', type=int, default=16)
    ap.add_argument('--out-dir', default=None, help='where to write the report (default: <root>/tools)')
    opts = ap.parse_args(argv)
    root = os.path.abspath(opts.root)
    out_dir = os.path.abspath(opts.out_dir or os.path.join(root, 'tools'))
    opts.commit = full_sha(opts.commit)
    files = published_files(root)
    started = datetime.datetime.now(datetime.timezone.utc)
    with concurrent.futures.ThreadPoolExecutor(opts.workers) as pool:
        rows = list(pool.map(lambda rel: check_one(root, rel), [''] + files))
    full = []
    for rel in FULL_COMPARE:
        status, ctype, _length, body = fetch(SITE + rel, 'GET')
        path = os.path.join(root, rel or 'index.html')
        same = status == 200 and hashlib.sha256(body).hexdigest() == hashlib.sha256(open(path, 'rb').read()).hexdigest()
        full.append((rel or '(home page)', status, same))
    runs, run_error = actions(opts.commit)
    cs_code, cs_out = run(root, ['-B', 'tools/check_site.py'])
    vf_code, vf_out = run(root, ['-B', 'tools/structured/verify.py'])
    finished = datetime.datetime.now(datetime.timezone.utc)

    with open(os.path.join(out_dir, 'DEPLOYMENT-URLS.tsv'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('path\tstatus\tcontent_type\tlive_bytes\tlocal_bytes\tsize_matches\n')
        for r in rows:
            handle.write('%s\t%s\t%s\t%s\t%s\t%s\n' % (r['path'], r['status'], r['content_type'], r['length'],
                                                       r['local'], 'yes' if r['size_ok'] or r['local'] is None else 'NO'))

    by_status = {}
    for r in rows:
        by_status[r['status']] = by_status.get(r['status'], 0) + 1
    groups = {}
    for r in rows[1:]:
        g = groups.setdefault(group_of(r['path']), dict(files=0, ok=0, size_ok=0, types=set()))
        g['files'] += 1
        g['ok'] += r['status'] == 200
        g['size_ok'] += bool(r['size_ok'])
        g['types'].add(r['content_type'].split(';')[0])
    bad = [r for r in rows if r['status'] != 200 or (r['local'] is not None and not r['size_ok'])]
    manifest = json.load(open(os.path.join(root, 'archive-manifest.json'), encoding='utf-8'))
    counts = manifest.get('counts', {})
    cs_summary = [l for l in cs_out.splitlines() if l.startswith(('Errors:', 'Measured', '- Checked', '- The ', '- Search', '- Subject'))]
    vf_lines = vf_out.splitlines()
    hashes = 'unknown'
    for i, line in enumerate(vf_lines):
        if 'ORIGINAL-FILE HASHES' in line and i + 1 < len(vf_lines):
            hashes = vf_lines[i + 1].strip(' -')

    out = ['# Deployment verification report', '',
           'Generated by tools/verify_deployment.py. Started %s, finished %s (UTC).' % (
               started.strftime('%Y-%m-%d %H:%M:%S'), finished.strftime('%Y-%m-%d %H:%M:%S')),
           'This report describes the commit named below, as served by GitHub Pages at the time of the run.', '',
           '## Source', '',
           '- Repository: https://github.com/Uracrom/My-Titanium-Brothers',
           '- Commit checked: %s' % opts.commit,
           '- Site: %s' % SITE, '',
           '## Deployment status (public GitHub Actions runs for this commit)', '']
    if runs is None:
        out.append('- Could not read the Actions API: %s' % run_error)
    elif not runs:
        out.append('- No runs found for this commit.')
    else:
        for r in runs:
            out.append('- %s (%s): %s, %s, started %s. %s' % (r['name'], r['event'], r['status'], r['conclusion'], r['created'], r['url']))
    out += ['', '## Live HTTP check of every published file', '',
            '%d URLs requested (the home page plus %d files; everything in the repository except .git and .github, '
            'because the site has .nojekyll). Each request used HEAD with a cache-busting query.' % (len(rows), len(files)), '',
            'Status codes: %s.' % ', '.join('%s: %d' % (k, v) for k, v in sorted(by_status.items(), key=lambda kv: str(kv[0]))),
            'Files whose live Content-Length equals the local file size: %d of %d.' % (sum(1 for r in rows[1:] if r['size_ok']), len(files)), '',
            '| Group | Files | HTTP 200 | Size matches | Content types |', '|---|---|---|---|---|']
    for name in sorted(groups):
        g = groups[name]
        out.append('| %s | %d | %d | %d | %s |' % (name, g['files'], g['ok'], g['size_ok'], ', '.join(sorted(g['types']))))
    out += ['', 'Full table (path, status, content type, live and local bytes): tools/DEPLOYMENT-URLS.tsv', '']
    if bad:
        out.append('Problems (%d):' % len(bad))
        for r in bad[:200]:
            out.append('- %s: status %s, live %s bytes, local %s bytes' % (r['path'], r['status'], r['length'], r['local']))
    else:
        out.append('No problems: every URL answered 200 and every size matched.')
    out += ['', '## Full-content comparison of the guide files (GET, SHA-256 against the local file)', '',
            '| File | Status | Same bytes |', '|---|---|---|']
    for rel, status, same in full:
        out.append('| %s | %s | %s |' % (rel, status, 'yes' if same else 'NO'))
    out += ['', '## Final counts (archive-manifest.json, checked against the files by tools/check_site.py)', '',
            '- Archive entries: %s' % counts.get('archive_entries'),
            '- Logical conversations: %s' % counts.get('logical_conversations'),
            '- Messages: %s' % counts.get('messages'),
            '- HTML article pieces: %s' % counts.get('html_article_pieces'),
            '- Numbered part pages: %s' % counts.get('numbered_part_pages'), '',
            '## Local link and consistency check (tools/check_site.py)', '',
            'Exit code %d.' % cs_code, '']
    out += ['    ' + l for l in cs_summary]
    out += ['', '## Original-file hashes and preservation (tools/structured/verify.py)', '',
            'Exit code %d. Original-file hashes: %s.' % (vf_code, hashes),
            'verify.py compares %s against tools/structured/original-hashes.sha256 and rebuilds every page from the structured transcripts.' % 'the original conversation files', '']
    with open(os.path.join(out_dir, 'DEPLOYMENT-REPORT.md'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(out) + '\n')
    print('\n'.join(out))
    return 0 if not bad and cs_code == 0 and vf_code == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
