import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const files = [];
async function walk(dir) {
  for (const item of await readdir(dir, { withFileTypes: true })) {
    if (['.git', 'node_modules', '.venv', '__pycache__'].includes(item.name)) continue;
    const p = path.join(dir, item.name);
    if (item.isDirectory()) await walk(p); else files.push(p);
  }
}
await walk(root);
for (const p of files.filter(p => /\.(md|html|js|mjs|json|yml|yaml|py|css)$/.test(p))) {
  const text = await readFile(p, 'utf8');
  assert(!/\/Users\/[^/]+\//.test(text), `个人路径：${p}`);
  assert(!/sk-[A-Za-z0-9_-]{24,}/.test(text), `疑似密钥：${p}`);
  if (p.endsWith('.md')) for (const m of text.matchAll(/\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g)) {
    const link = m[1].split('#')[0];
    if (!link || /^[a-z]+:/i.test(link)) continue;
    assert(await stat(path.resolve(path.dirname(p), decodeURIComponent(link))).catch(() => false), `失效链接 ${p}: ${link}`);
  }
}
assert.equal(await readFile(path.join(root, 'cutout-tool.html'), 'utf8'), await readFile(path.join(root, 'skills/gpt-image-2-subject-assets/assets/cutout-tool.html'), 'utf8'));
const tool = await readFile(path.join(root, 'cutout-tool.html'), 'utf8');
assert(!/\b(fetch|XMLHttpRequest|WebSocket)\s*\(/.test(tool), '离线工具出现网络调用');
console.log(`检查通过：${files.length} 个文件；本地链接、路径、网页同步、离线调用。`);
