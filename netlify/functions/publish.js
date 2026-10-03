exports.handler = async (event) => {
  const json = (statusCode, obj) => ({
    statusCode,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(obj)
  });

  if (event.httpMethod !== 'POST') return json(405, { error: 'Method not allowed' });

  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return json(400, { error: 'Invalid request' }); }

  const { password, ai, subject, text } = body;

  const PUBLISH_PASSWORD = process.env.PUBLISH_PASSWORD;
  if (!PUBLISH_PASSWORD) return json(500, { error: 'Server not configured: PUBLISH_PASSWORD missing' });
  if (!password || password !== PUBLISH_PASSWORD) return json(401, { error: 'Wrong password' });

  if (!ai)              return json(400, { error: 'No AI selected' });
  if (!subject?.trim()) return json(400, { error: 'Subject is required' });
  if (!text?.trim() || text.trim().length < 10) return json(400, { error: 'Conversation text is too short' });

  const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
  if (!GITHUB_TOKEN) return json(500, { error: 'Server not configured: GITHUB_TOKEN missing' });

  const OWNER = 'Uracrom';
  const REPO  = 'My-Titanium-Brothers';
  const GH    = `https://api.github.com/repos/${OWNER}/${REPO}/contents`;
  const ghHeaders = {
    'Authorization': `token ${GITHUB_TOKEN}`,
    'Content-Type':  'application/json',
    'User-Agent':    'MyTitaniumBrothers',
    'Accept':        'application/vnd.github.v3+json'
  };

  const date       = new Date().toISOString().slice(0, 10);
  const aiSlug     = ai.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const subjectSlug = subject.trim().toLowerCase()
    .replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, '-').slice(0, 50).replace(/-+$/g, '');

  const filename = `${date}-${aiSlug}-${subjectSlug}.md`;
  const slug     = filename.replace('.md', '');

  const markdown = `---
title: "${subject.trim().replace(/"/g, '\\"')}"
ai: ${ai}
date: ${date}
slug: ${slug}
---

${text.trim()}
`;

  const content = Buffer.from(markdown, 'utf-8').toString('base64');

  const writeRes = await fetch(
    `${GH}/conversations/${filename}`,
    {
      method: 'PUT',
      headers: ghHeaders,
      body: JSON.stringify({
        message: `Publish: ${subject} (${ai})`,
        content
      })
    }
  );
