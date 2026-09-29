#!/usr/bin/env node
/*
 * Engineering Phenomena 02 - subtitle maker (no dependencies).
 *
 * Reads the caption timeline of the film and writes one .srt file per language:
 *
 *     ../subtitles/02-aliasing_en.srt
 *     ../subtitles/02-aliasing_fr.srt
 *     ../subtitles/02-aliasing_ar.srt
 *
 * Every caption of the film is used, the ones burned into the picture AND the
 * ones marked burn:false (subtitles only), with their exact in and out times.
 *
 * How to run (from phenomena/02-aliasing/code/):
 *
 *     node render.mjs --comp main --lang en --timeline     # once, and after any timing change
 *     node tools/make_srt.mjs
 *
 * or in one go:
 *
 *     node tools/make_srt.mjs --refresh
 *
 * The Short (9:16) has its own captions and timing:
 *
 *     node tools/make_srt.mjs short --refresh
 *
 * reads build/short_timeline.json and writes ../subtitles/02-aliasing_9x16_en.srt, _fr.srt, _ar.srt
 *
 * Usage:  node tools/make_srt.mjs [main|short] [options]
 *
 * Options
 *   --refresh        first rebuild build/<comp>_timeline.json with render.mjs
 *   --comp <name>    same as the positional composition name (default main)
 *   --langs en,fr,ar languages to write (default all three)
 *   --out <dir>      folder for the .srt files (default ../subtitles)
 *   --width <n>      target line length in characters (default 42)
 *   --quiet          only print problems
 *
 * File names: main -> 02-aliasing_<lang>.srt, short -> 02-aliasing_9x16_<lang>.srt,
 * any other composition -> 02-aliasing_<comp>_<lang>.srt
 *
 * Rules (the same for every language)
 *   - the text of a caption comes from the string table (data/strings/*.json), for the
 *     language; if it is empty the English text is used and a warning is printed
 *   - at most 2 lines per subtitle, about 42 characters per line, balanced, broken after
 *     punctuation when possible. A typographic no-break space (after a digit, before
 *     : ; ! ? ») is never a place to break; the extra no-break spaces that only steer the
 *     layout of the big burned-in captions become plain spaces in the .srt
 *   - Arabic: every line starts with U+200F (right-to-left mark), so players show the
 *     line right to left even when it starts with a number or a Latin word
 *   - UTF-8 without BOM, LF line ends everywhere
 *   - numbering 1, 2, 3 ..., times HH:MM:SS,mmm, no overlaps: checked after writing
 *
 * The exit code is 1 when a file is not valid (numbering, overlap, time format), 0 otherwise.
 */
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const CODE = path.resolve(HERE, '..');
const NAME = '02-aliasing';

// ---------------------------------------------------------------- options
function parseArgs(argv) {
  const o = { comp: 'main', langs: ['en', 'fr', 'ar'], out: path.resolve(CODE, '../subtitles'), width: 42, refresh: false, quiet: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--refresh') o.refresh = true;
    else if (a === '--quiet') o.quiet = true;
    else if (a === '--comp') o.comp = argv[++i];
    else if (a === '--langs') o.langs = String(argv[++i]).split(',').map(s => s.trim()).filter(Boolean);
    else if (a === '--out') o.out = path.resolve(argv[++i]);
    else if (a === '--width') o.width = Number(argv[++i]);
    else if (!a.startsWith('-')) o.comp = a;                // positional: the composition
    else { console.error(`unknown option ${a}`); process.exit(2); }
  }
  return o;
}
const opt = parseArgs(process.argv.slice(2));

const RLM = '‏';
const NBSP = ' ';
// characters that take no room on screen: they do not count in the line length
const INVISIBLE = /[​-‏‪-‮⁦-⁩﻿]/g;
const visLen = s => [...s.replace(INVISIBLE, '')].length;

// ---------------------------------------------------------------- inputs
const timelinePath = path.join(CODE, 'build', `${opt.comp}_timeline.json`);

if (opt.refresh) {
  console.log(`refreshing ${path.relative(CODE, timelinePath)} ...`);
  const r = spawnSync(process.execPath, ['render.mjs', '--comp', opt.comp, '--lang', 'en', '--timeline'], { cwd: CODE, stdio: opt.quiet ? 'ignore' : 'inherit' });
  if (r.status !== 0) { console.error('render.mjs --timeline failed'); process.exit(1); }
}
if (!fs.existsSync(timelinePath)) {
  console.error(`missing ${timelinePath}\ncreate it with:  node render.mjs --comp ${opt.comp} --lang en --timeline\n(or run this tool with --refresh)`);
  process.exit(1);
}
const timeline = JSON.parse(fs.readFileSync(timelinePath, 'utf8'));
const captions = (timeline.captions || []).slice().sort((a, b) => a.in - b.in || a.out - b.out);

// the string table, read fresh from disk (the timeline keeps a copy taken when it was made)
const stringsDir = path.join(CODE, 'data', 'strings');
const table = {};
for (const f of fs.readdirSync(stringsDir).filter(f => f.endsWith('.json')).sort()) {
  Object.assign(table, JSON.parse(fs.readFileSync(path.join(stringsDir, f), 'utf8')));
}

// warn when the timeline is older than the things it was made from
{
  const t = fs.statSync(timelinePath).mtimeMs;
  const newer = [];
  for (const f of fs.readdirSync(stringsDir)) if (fs.statSync(path.join(stringsDir, f)).mtimeMs > t) newer.push(`data/strings/${f}`);
  const scenesDir = path.join(CODE, 'scenes');
  for (const f of fs.readdirSync(scenesDir)) if (f.endsWith('.js') && fs.statSync(path.join(scenesDir, f)).mtimeMs > t) newer.push(`scenes/${f}`);
  if (newer.length) console.warn(`WARNING: ${path.relative(CODE, timelinePath)} is older than ${newer.length} file(s) (${newer.slice(0, 4).join(', ')}${newer.length > 4 ? ', ...' : ''}). Caption TIMES may be out of date: run with --refresh.`);
}

// ---------------------------------------------------------------- text
/** The text of a caption in a language. Falls back to English (with a warning). */
function captionText(c, lang, warnings) {
  const fromTable = table[c.key] || {};
  const fromTimeline = c.text || {};
  let s = fromTable[lang] ?? fromTimeline[lang];
  if (s == null || String(s).trim() === '') {
    if (lang !== 'en') warnings.push(`${c.key}: no ${lang} text, English used`);
    s = fromTable.en ?? fromTimeline.en ?? '';
  }
  return String(s).replace(/\r\n?/g, '\n').replace(/[ \t]+\n/g, '\n').trim();
}

/**
 * No-break spaces in the strings have two jobs:
 *   1. typography (French: before : ; ! ? and inside guillemets; a number and its unit;
 *      "900 Hz" kept together and left-to-right in Arabic). These must never be broken.
 *   2. layout glue for the big burned-in captions (keeps "le bon sens" on one line).
 *      In a subtitle file the player wraps the lines, so this glue is turned into a plain
 *      space and may be broken.
 * A no-break space is kept when it follows a digit, precedes : ; ! ? » % × =, or follows « × =.
 */
const KEEP = '';                       // private marker for a no-break space that must stay
function relaxGlue(text) {
  return text.replace(/ /g, (m, i, all) => {
    const before = all[i - 1] || '', after = all[i + 1] || '';
    const keep = /\d/.test(before) || /[:;!?»%×=]/.test(after) || /[«×=]/.test(before);
    return keep ? KEEP : ' ';
  });
}

/**
 * Break a text into at most `maxLines` lines of about `width` characters.
 * Words are separated by plain spaces only (see relaxGlue for the no-break spaces).
 * An explicit \n in the text is respected.
 */
function wrap(text, width, maxLines = 2) {
  text = relaxGlue(text);
  const done = lines => lines.map(l => l.replace(new RegExp(KEEP, 'g'), ' '));
  if (text.includes('\n')) return done(text.split('\n').map(s => s.trim()).filter(Boolean).slice(0, maxLines));
  const words = text.split(' ').filter(Boolean);
  const whole = words.join(' ');
  if (visLen(whole) <= width || words.length < 2) return done([whole]);
  let best = null;
  for (let i = 1; i < words.length; i++) {
    const a = words.slice(0, i).join(' '), b = words.slice(i).join(' ');
    const la = visLen(a), lb = visLen(b);
    const overflow = Math.max(0, la - width) + Math.max(0, lb - width);
    let score = overflow * 1000 + Math.abs(la - lb);
    if (/[,;:.!?…،؛؟]$/.test(a)) score -= 8;          // a break after punctuation reads better
    if (la < 8 || lb < 8) score += 25;                 // never leave a tiny orphan
    if (!best || score < best.score) best = { score, lines: [a, b] };
  }
  return done(best.lines);
}

// ---------------------------------------------------------------- SRT
const pad = (n, w) => String(n).padStart(w, '0');
function stamp(sec) {
  const ms = Math.round(sec * 1000);
  return `${pad(Math.floor(ms / 3600000), 2)}:${pad(Math.floor(ms / 60000) % 60, 2)}:${pad(Math.floor(ms / 1000) % 60, 2)},${pad(ms % 1000, 3)}`;
}

function build(lang) {
  const warnings = [];
  const cues = captions.map((c, i) => {
    const text = captionText(c, lang, warnings);
    let lines = wrap(text, opt.width);
    const longest = Math.max(...lines.map(visLen));
    if (longest > opt.width + 6) warnings.push(`${c.key}: line of ${longest} characters (target ${opt.width}, 2 lines maximum)`);
    if (lang === 'ar') lines = lines.map(l => RLM + l);
    const dur = c.out - c.in;
    const chars = visLen(text.replace(/\s+/g, ' '));
    if (dur > 0 && chars / dur > 20) warnings.push(`${c.key}: ${(chars / dur).toFixed(1)} characters per second (${chars} characters in ${dur.toFixed(2)} s)`);
    return { n: i + 1, key: c.key, start: c.in, end: c.out, lines };
  });
  const body = cues.map(q => `${q.n}\n${stamp(q.start)} --> ${stamp(q.end)}\n${q.lines.join('\n')}\n`).join('\n');
  return { cues, warnings, srt: cues.length ? body + '\n' : '' };
}

/** Read a written file back and check it. Returns a list of problems (empty = valid). */
function validate(file, expectedCount) {
  const problems = [];
  const buf = fs.readFileSync(file);
  if (buf.length >= 3 && buf[0] === 0xEF && buf[1] === 0xBB && buf[2] === 0xBF) problems.push('starts with a BOM');
  const txt = buf.toString('utf8');
  if (txt.includes('\r')) problems.push('contains CR characters (LF only is expected)');
  const blocks = txt.replace(/\n+$/, '').split(/\n{2,}/);
  const TIME = /^(\d{2}):([0-5]\d):([0-5]\d),(\d{3}) --> (\d{2}):([0-5]\d):([0-5]\d),(\d{3})$/;
  const toMs = (h, m, s, ms) => ((+h * 60 + +m) * 60 + +s) * 1000 + +ms;
  let prevEnd = -1, count = 0;
  blocks.forEach((b, i) => {
    const L = b.split('\n');
    if (L.length < 3 || L.length > 4) problems.push(`cue ${i + 1}: ${L.length - 2} text lines (1 or 2 expected)`);
    if (String(i + 1) !== L[0]) problems.push(`cue ${i + 1}: numbered "${L[0]}", expected ${i + 1}`);
    const m = TIME.exec(L[1] || '');
    if (!m) { problems.push(`cue ${i + 1}: bad time line "${L[1]}"`); return; }
    const s = toMs(m[1], m[2], m[3], m[4]), e = toMs(m[5], m[6], m[7], m[8]);
    if (e <= s) problems.push(`cue ${i + 1}: ends (${m[5]}:${m[6]}:${m[7]},${m[8]}) before it starts`);
    if (s < prevEnd) problems.push(`cue ${i + 1}: overlaps the previous cue by ${prevEnd - s} ms`);
    prevEnd = e; count++;
  });
  if (count !== expectedCount) problems.push(`${count} cues in the file, ${expectedCount} captions in the timeline`);
  return problems;
}

// ---------------------------------------------------------------- run
if (!captions.length) {
  console.log(`no captions in ${path.relative(CODE, timelinePath)}: nothing to write`);
  process.exit(0);
}
fs.mkdirSync(opt.out, { recursive: true });
const SUFFIX = { main: '', short: '_9x16' };
const suffix = opt.comp in SUFFIX ? SUFFIX[opt.comp] : `_${opt.comp}`;
let failed = false;
for (const lang of opt.langs) {
  const { cues, warnings, srt } = build(lang);
  const file = path.join(opt.out, `${NAME}${suffix}_${lang}.srt`);
  fs.writeFileSync(file, srt, { encoding: 'utf8' });     // no BOM, LF only
  const problems = validate(file, cues.length);
  const last = cues[cues.length - 1];
  console.log(`${path.relative(process.cwd(), file)}  ${cues.length} cues, ${stamp(cues[0].start)} to ${stamp(last.end)}`);
  for (const w of warnings) console.warn(`  warning [${lang}]: ${w}`);
  for (const p of problems) { console.error(`  INVALID [${lang}]: ${p}`); failed = true; }
  if (!opt.quiet) {
    for (const q of cues.slice(0, 3)) console.log(`    ${q.n}  ${stamp(q.start)} --> ${stamp(q.end)}  ${q.lines.join(' / ').replace(new RegExp(NBSP, 'g'), '~')}`);
  }
}
process.exit(failed ? 1 : 0);
