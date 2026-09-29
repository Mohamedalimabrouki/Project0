#!/usr/bin/env node
/*
 * Engineering Phenomena 02 - renderer.
 *
 * Opens the stage in headless Chromium, draws the requested frames and saves
 * them as PNG. Can also make contact sheets (many frames on one image, for a
 * quick visual check) and encode the final video.
 *
 * Examples
 *   node render.mjs --comp main --lang en                         every frame of the film
 *   node render.mjs --scene s04_trick --every 15 --contact        one frame in 15 of a scene, on one sheet
 *   node render.mjs --scene s04_trick --at 3.5,12,20.25           exact moments (seconds from the scene start)
 *   node render.mjs --comp main --lang en --timeline              captions + sound cues -> build/
 *   node render.mjs --comp main --lang en --encode --audio build/audio/main.wav --video ../video/x.mp4
 *   node render.mjs --comp hero --scale 2                         4K still
 *
 * Options: --comp main|short|hero|thumb  --lang en|fr|ar  --scene id  --every k
 *          --from n --to n (global frames)  --at seconds[,seconds]  --workers n
 *          --out dir  --contact  --cols n  --debug  --scale s  --encode  --audio f  --video f  --crf n
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '../../..');

function args() {
  const a = { comp: 'main', lang: 'en', workers: 3, every: 1, cols: 4, crf: 16 };
  const v = process.argv.slice(2);
  for (let i = 0; i < v.length; i++) {
    const k = v[i].replace(/^--/, '');
    const next = v[i + 1];
    if (['contact', 'debug', 'encode', 'timeline', 'quiet', 'keep'].includes(k)) a[k] = true;
    else { a[k] = next; i++; }
  }
  for (const k of ['workers', 'every', 'cols', 'from', 'to', 'crf', 'scale']) if (a[k] != null) a[k] = Number(a[k]);
  return a;
}

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.ttf': 'font/ttf', '.woff2': 'font/woff2', '.woff': 'font/woff', '.svg': 'image/svg+xml', '.png': 'image/png', '.css': 'text/css' };
function serve() {
  const server = http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0]);
    const file = path.join(REPO, url);
    if (file.startsWith(REPO) && !fs.existsSync(file) && /\/data\/strings\/[\w-]+\.json$/.test(url)) {
      res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{}'); return;   // optional strings file
    }
    if (!file.startsWith(REPO) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise(ok => server.listen(0, '127.0.0.1', () => ok(server)));
}

async function openStage(browser, base, o) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const logs = [];
  page.on('pageerror', e => logs.push(`pageerror: ${e.message}`));
  page.on('console', m => { if (m.type() === 'error') logs.push(`console: ${m.text()}`); });
  const q = new URLSearchParams({ comp: o.comp, lang: o.lang });
  if (o.debug) q.set('debug', '1');
  if (o.scale) q.set('scale', String(o.scale));
  await page.goto(`${base}/phenomena/02-aliasing/code/engine/stage.html?${q}`);
  await page.waitForFunction(() => window.EP_ready || window.EP_failed, null, { timeout: 180000 });
  const failed = await page.evaluate(() => window.EP_failed);
  if (failed) throw new Error(`stage failed to start:\n${failed}\n${logs.join('\n')}`);
  page._logs = logs;
  return page;
}

async function main() {
  const o = args();
  const server = await serve();
  const base = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({ args: ['--disable-gpu', '--font-render-hinting=none', '--disable-lcd-text'] });
  let exit = 0;
  try {
    const first = await openStage(browser, base, o);
    const info = await first.evaluate(() => window.EP_info);
    const tag = `${o.comp}_${o.lang}${o.scene ? '_' + o.scene : ''}`;
    const outDir = path.resolve(o.out || path.join(HERE, 'build', tag));

    if (o.timeline) {
      const tl = await first.evaluate(() => window.EP_timeline());
      fs.mkdirSync(path.join(HERE, 'build'), { recursive: true });
      const f = path.join(HERE, 'build', `${o.comp}_timeline.json`);
      fs.writeFileSync(f, JSON.stringify(tl, null, 1));
      console.log(`timeline: ${f}  (${tl.duration.toFixed(2)} s, ${tl.captions.length} captions, ${tl.cues.length} cues)`);
      await report([first], o);
      return;
    }

    // which frames?
    let lo = 0, hi = info.frames, sceneStart = 0;
    if (o.scene) {
      const s = info.scenes.find(x => x.id === o.scene);
      if (!s) throw new Error(`scene ${o.scene} is not in comp ${o.comp}: ${info.scenes.map(x => x.id).join(', ')}`);
      lo = s.start; hi = s.start + s.frames; sceneStart = s.start;
    }
    if (o.from != null) lo = Math.max(lo, o.from);
    if (o.to != null) hi = Math.min(hi, o.to + 1);
    let frames = [];
    if (o.at) frames = String(o.at).split(',').map(x => sceneStart + Math.round(Number(x) * info.fps));
    else for (let n = lo; n < hi; n += o.every) frames.push(n);
    frames = frames.filter(n => n >= 0 && n < info.frames);

    const frameDir = path.join(outDir, 'frames');
    fs.mkdirSync(frameDir, { recursive: true });
    if (!o.keep && !o.at && o.every === 1 && !o.scene && o.from == null) for (const f of fs.readdirSync(frameDir)) if (f.endsWith('.png')) fs.unlinkSync(path.join(frameDir, f));

    const pages = [first];
    const nWorkers = Math.max(1, Math.min(o.workers, frames.length));
    for (let i = 1; i < nWorkers; i++) pages.push(await openStage(browser, base, o));

    const t0 = Date.now();
    let next = 0, done = 0, lastPct = -1;
    const written = [];
    await Promise.all(pages.map(async page => {
      while (next < frames.length) {
        const n = frames[next++];
        const url = await page.evaluate(k => window.EP_frame(k), n);
        const file = path.join(frameDir, `f${String(n).padStart(5, '0')}.png`);
        fs.writeFileSync(file, Buffer.from(url.slice(url.indexOf(',') + 1), 'base64'));
        written.push({ n, file });
        done++;
        const pct = Math.floor((100 * done) / frames.length);
        if (!o.quiet && pct >= lastPct + 10) { lastPct = pct; process.stdout.write(`  ${pct}% (${done}/${frames.length})\n`); }
      }
    }));
    const secs = (Date.now() - t0) / 1000;
    console.log(`rendered ${frames.length} frame(s) in ${secs.toFixed(1)} s (${(frames.length / secs).toFixed(1)} fps) -> ${frameDir}`);
    exit = await report(pages, o);

    if (o.contact) {
      written.sort((a, b) => a.n - b.n);
      const list = written.map(w => ({ file: w.file, label: `${o.scene || 'global'} t=${((w.n - sceneStart) / info.fps).toFixed(2)}s  #${w.n}` }));
      const listFile = path.join(outDir, 'contact.json');
      fs.writeFileSync(listFile, JSON.stringify(list));
      const sheet = path.join(outDir, 'contact.png');
      const r = spawnSync('python3', [path.join(HERE, 'tools/contact.py'), listFile, sheet, String(o.cols)], { stdio: 'inherit' });
      if (r.status === 0) console.log(`contact sheet: ${sheet}`);
    }

    if (o.encode) {
      const video = path.resolve(o.video || path.join(outDir, `${tag}.mp4`));
      const ff = ['-y', '-framerate', String(info.fps), '-start_number', String(lo), '-i', path.join(frameDir, 'f%05d.png')];
      if (o.audio) ff.push('-i', path.resolve(o.audio));
      ff.push('-map', '0:v');
      if (o.audio) ff.push('-map', '1:a');
      ff.push('-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', String(o.crf), '-tune', 'animation', '-profile:v', 'high',
        '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
        '-g', String(info.fps * 2), '-movflags', '+faststart');
      if (o.audio) ff.push('-c:a', 'aac', '-b:a', '320k', '-ar', '48000', '-shortest');
      ff.push(video);
      fs.mkdirSync(path.dirname(video), { recursive: true });
      const r = spawnSync('ffmpeg', ff, { stdio: ['ignore', 'ignore', 'inherit'] });
      if (r.status !== 0) throw new Error('ffmpeg failed');
      console.log(`video: ${video}`);
    }
  } catch (e) {
    console.error(e.stack || String(e));
    exit = 1;
  } finally {
    await browser.close();
    server.close();
  }
  process.exit(exit);
}

async function report(pages, o) {
  const all = new Set();
  for (const p of pages) {
    for (const m of await p.evaluate(() => window.EP_problems())) all.add(m);
    for (const m of p._logs) all.add(m);
  }
  if (all.size) {
    console.log(`PROBLEMS (${all.size}):`);
    for (const m of all) console.log('  - ' + m);
    return [...all].some(m => /error|failed/i.test(m)) ? 2 : 0;
  }
  if (!o.quiet) console.log('no problems reported');
  return 0;
}

main();
