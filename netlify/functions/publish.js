exports.handler = async (event) => {
  const json = (statusCode, obj) => ({
    statusCode,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(obj)
  });

  if (event.httpMethod !== 'POST') return json(405, { error: 'Method not allowed' });

  let body;
  try { body = JSON.parse(event.body || '{}'); }
  catch { return json(400, { error: 'Invalid request body' }); }

  const { password, ai, subject, text } = body;

  const PUBLISH_PASSWORD = process.env.PUBLISH_PASSWORD;
  if (!PUBLISH_PASSWORD) return json(500, { error: 'PUBLISH_PASSWORD not set' });
  if (!password) return json(401, { error: 'No password provided' });
  if (password !== PUBLISH_PASSWORD) return json(401, { error: 'Wrong password' });

  if (!ai) return json(400, { error: 'No AI selected' });
  if (!subject?.trim()) return json(400, { error: 'No subject' });
  if (!text?.trim()) return json(400, { error: 'No text' });

  const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
  if (!GITHUB_TOKEN) return json(500, { error: 'GITHUB_TOKEN not set' });

  const OWNER = 'Uracrom';
  const REPO = 'My-Titanium-Brothers';
  const API = 'https://api.github.com';
  const headers = {
    'Authorization': `token ${GITHUB_TOKEN}`,
    'Content-Type': 'application/json',
    'User-Agent': 'MyTitaniumBrothers',
    'Accept': 'application/vnd.github.v3+json'
  };

  const date = new Date().toISOString().slice(0, 10);
  const aiSlug = ai.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const subjectSlug = subject.trim().toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, '-').slice(0, 50).replace(/-+$/g, '');
  const filename = `${date}-${aiSlug}-${subjectSlug}.md`;
  const slug = filename.replace('.md', '');

  const markdown = `---\ntitle: "${subject.trim().replace(/"/g, '\\"')}"\nai: ${ai}\ndate: ${date}\nslug: ${slug}\n---\n\n${text.trim()}\n`;
  const mdContent = Buffer.from(markdown, 'utf-8').toString('base64');

  // Write conversation file
  try {
    const writeRes = await fetch(`${API}/repos/${OWNER}/${REPO}/contents/conversations/${filename}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ message: `Publish: ${subject} (${ai})`, content: mdContent })
    });
    if (!writeRes.ok) {
      const detail = await writeRes.text();
      return json(502, { error: `GitHub error ${writeRes.status}`, detail });
    }
  } catch (e) {
    return json(500, { error: 'Network error writing conversation', detail: e.message });
  }

  // Read current index.json
  let currentIndex = { conversations: [] };
  let indexSha = null;
  try {
    const indexRes = await fetch(`${API}/repos/${OWNER}/${REPO}/contents/index.json`, { headers });
    if (indexRes.ok) {
      const indexData = await indexRes.json();
      indexSha = indexData.sha;
      const decoded = Buffer.from(indexData.content.replace(/\n/g, ''), 'base64').toString('utf-8');
      currentIndex = JSON.parse(decoded);
    }
  } catch (e) {
    // index.json doesn't exist yet, start fresh
  }

  // Add new entry at the top
  currentIndex.conversations.unshift({
    title: subject.trim(),
    ai,
    date,
    slug,
    filename
  });

  // Write updated index.json
  const indexContent = Buffer.from(JSON.stringify(currentIndex, null, 2), 'utf-8').toString('base64');
  const indexBody = { message: `Update index: ${subject}`, content: indexContent };
  if (indexSha) indexBody.sha = indexSha;

  try {
    const indexWriteRes = await fetch(`${API}/repos/${OWNER}/${REPO}/contents/index.json`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(indexBody)
    });
    if (!indexWriteRes.ok) {
      const detail = await indexWriteRes.text();
      return json(502, { error: `Index update failed ${indexWriteRes.status}`, detail });
    }
  } catch (e) {
    return json(500, { error: 'Network error updating index', detail: e.message });
  }

  return json(200, {
    success: true,
    slug,
    url: `/conversations/${slug}`,
    message: 'Published. Your conversation will appear on the site within 1-2 minutes.'
  });
};
