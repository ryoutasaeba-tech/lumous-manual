import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const OUT_DIR = process.env.LUMOUS_VIDEO_DIR || '/home/ryota/lumous-manual-public/videos';
fs.mkdirSync(OUT_DIR, { recursive: true });

const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
try {
const context = await browser.newContext();
const page = await context.newPage();

// localhost:3456 を開く (IndexedDBがそこにある)
await page.goto('http://localhost:3456/', { waitUntil: 'networkidle', timeout: 30000 });

// IndexedDBから全ての動画を取得
const videos = await page.evaluate(async () => {
  const req = indexedDB.open('lumous-videos', 1);
  const db = await new Promise((resolve, reject) => {
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = e => reject(e);
    req.onupgradeneeded = e => { e.target.result.createObjectStore('videos'); };
  });
  const tx = db.transaction('videos', 'readonly');
  const store = tx.objectStore('videos');
  const keys = await new Promise((r) => { store.getAllKeys().onsuccess = e => r(e.target.result); });
  const vals = await new Promise((r) => { store.getAll().onsuccess = e => r(e.target.result); });
  return keys.map((k, i) => ({ id: k, dataUrl: vals[i] }));
});

console.log(`Found ${videos.length} videos in IndexedDB`);

// データURLをファイルに保存
for (const v of videos) {
  const m = v.dataUrl.match(/^data:([^;]+);base64,(.+)$/);
  if (!m) { console.log(`  skip: ${v.id} (not data URL)`); continue; }
  const mime = m[1];
  const ext = mime.includes('mp4') ? 'mp4' : mime.includes('webm') ? 'webm' : mime.includes('quicktime') ? 'mov' : 'mp4';
  const buf = Buffer.from(m[2], 'base64');
  // id に ../ などが入っていても、保存先のフォルダの外に書かないようにする
  const safeId = path.basename(String(v.id)).replace(/[^A-Za-z0-9_.-]/g, '_');
  const outPath = path.join(OUT_DIR, `${safeId}.${ext}`);
  fs.writeFileSync(outPath, buf);
  console.log(`  ✓ ${v.id}.${ext} (${(buf.length/1024/1024).toFixed(1)} MB)`);
}

if (videos.length === 0) {
  console.error('動画が0件でした(localhost:3456 が起動しているか確認してください)');
  process.exitCode = 1;
}
console.log(`Done. Videos saved to ${OUT_DIR}`);
} finally {
  await browser.close();  // エラーでもブラウザを必ず閉じる
}
