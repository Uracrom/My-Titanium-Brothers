const fs = require('fs');
const path = require('path');

const conversationsDir = path.join(__dirname, '..', 'conversations');
const outputPath = path.join(__dirname, '..', 'index.json');

if (!fs.existsSync(conversationsDir)) {
  fs.mkdirSync(conversationsDir, { recursive: true });
}

const files = fs.readdirSync(conversationsDir)
  .filter(f => f.endsWith('.md') && f !== 'README.md')
  .sort()
  .reverse();

const conversations = [];

for (const file of files) {
  try {
    const content = fs.readFileSync(path.join(conversationsDir, file), 'utf-8');
    const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
    if (!fmMatch) continue;
    const fm = fmMatch[1];
    const get = (key) => {
      const m = fm.match(new RegExp(`^${key}:\\s*"?(.+?)"?\\s*$`, 'm'));
      return m ? m[1].trim() : '';
    };
    const title = get('title') || file.replace('.md', '');
    const ai = get('ai') || 'Unknown';
    const date = get('date') || '';
    const slug = file.replace('.md', '');
    conversations.push({ title, ai, date, slug, filename: file });
  } catch (e) {
    console.warn(`Skipping ${file}: ${e.message}`);
  }
}

fs.writeFileSync(outputPath, JSON.stringify({ conversations }, null, 2));
console.log(`Index generated: ${conversations.length} conversation(s).`);
