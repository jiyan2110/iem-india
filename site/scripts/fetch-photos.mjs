// Looks up one product photo link per IEM from the store page that lists it.
// Writes src/data/photos.json as { "<product url>": "<image url>" }. The site links to the
// store's own image; nothing is downloaded or re-hosted.
//
// Run: node scripts/fetch-photos.mjs
// It is slow on purpose (one request every few seconds per store), obeys Retry-After, and
// resumes from the existing file, so it is safe to stop and run again.
import { readFile, writeFile, mkdir } from 'node:fs/promises';

const OUT = new URL('../src/data/photos.json', import.meta.url);
const GAP_MS = 3000;
const UA = 'iem-india-site-build (personal project; one photo link per product)';

const iems = JSON.parse(await readFile(new URL('../data/iems.json', import.meta.url), 'utf8'));
let photos = {};
try {
  photos = JSON.parse(await readFile(OUT, 'utf8'));
} catch {}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const save = async () => {
  await mkdir(new URL('.', OUT), { recursive: true });
  const sorted = Object.fromEntries(Object.entries(photos).sort(([a], [b]) => a.localeCompare(b)));
  await writeFile(OUT, JSON.stringify(sorted, null, 1) + '\n');
};

async function lookup(url) {
  for (let attempt = 0; attempt < 6; attempt++) {
    const res = await fetch(url + '.js', { headers: { 'user-agent': UA, accept: 'application/json' } });
    if (res.status === 429 || res.status === 503) {
      const wait = Number(res.headers.get('retry-after')) || 60;
      await sleep((wait + 5) * 1000);
      continue;
    }
    if (!res.ok) return { error: `HTTP ${res.status}` };
    const p = await res.json();
    const src = p.featured_image || p.images?.[0];
    if (!src) return { error: 'no image' };
    return { src: src.startsWith('//') ? 'https:' + src : src };
  }
  return { error: 'rate limited' };
}

const byHost = new Map();
for (const url of new Set(iems.map((i) => i.url))) {
  if (photos[url]) continue;
  const host = new URL(url).host;
  byHost.set(host, [...(byHost.get(host) ?? []), url]);
}

const failed = [];
await Promise.all(
  [...byHost.entries()].map(async ([host, urls]) => {
    let done = 0;
    for (const url of urls) {
      try {
        const r = await lookup(url);
        if (r.src) photos[url] = r.src;
        else failed.push(`${url}: ${r.error}`);
      } catch (e) {
        failed.push(`${url}: ${e.message}`);
      }
      if (++done % 10 === 0) {
        await save();
        console.log(`${host}: ${done}/${urls.length}`);
      }
      await sleep(GAP_MS);
    }
  }),
);
await save();
console.log(`Photos: ${Object.keys(photos).length}. Failed: ${failed.length}`);
for (const f of failed) console.log('  ' + f);
