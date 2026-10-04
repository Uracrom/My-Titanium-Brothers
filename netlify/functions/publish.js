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
  if (!PUBLISH_PASSWORD) return json(500, { error: 'PUBLISH_PASSWORD not set in environment' });
  if (!password) return json(401, { error: 'No password provided' });
  if (password !== PUBLISH_PASSWORD) return json(401, { error: 'Wrong password' });

  if (!ai) return json(400, { error: 'No AI selected' });
  if (!subject?.trim()) return json(400, { error: 'No subject' });
  if (!text?.trim()) return json(400, { error: 'No text' });

  const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
  if (!GITHUB_TOKEN) return json(500, { error: 'GITHUB_TOKEN not set in environment' });

  const date = new Date().toISOString().slice(0, 10);
  const aiSlug = ai.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const subjectSlug = subject.trim().toLowerCase().replace(/[^a-z0-9\s]/g, '').replace(/\s+/g, '-').slice(0, 50).replace(/-+$/g, '');
  const filename = `${date}-${aiSlug}-${subjectSlug}.md`;
  const slug = filename.replace('.md', '');

  const markdown = `---\ntitle: "${subject.trim().replace(/"/g, '\\"')}"\nai: ${ai}\ndate: ${date}\nslug: ${slug}\n---\n\n${text.trim()}\n`;
  const content = Buffer.from(markdown, 'utf-8').toString('base64');

  try {
    const writeRes = await fetch(
      `https://api.github.com/repos/Uracrom/My-Titanium-Brothers/contents/conversations/${filename}`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `token ${GITHUB_TOKEN}`,
          'Content-Type': 'application/json',
          'User-Agent': 'MyTitaniumBrothers',
          'Accept': 'application/vnd.github.v3+json'
        },
        body: JSON.stringify({ message: `Publish: ${subject} (${ai})`, content })
      }
    );

    const responseText = await writeRes.text();

    if (!writeRes.ok) {
      return json(502, { error: `GitHub API error ${writeRes.status}`, detail: responseText });
    }

    return json(200, { success: true, slug, url: `/conversations/${slug}` });

  } catch (e) {
    return json(500, { error: 'Network error calling GitHub', detail: e.message });
  }
};
