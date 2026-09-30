/*
 * Stage: loads a composition (a list of scenes), the fonts, the strings and
 * the equations, then draws any frame on request.
 *
 *   stage.html?comp=main&lang=en            normal use (render.mjs)
 *   stage.html?comp=main&lang=ar&debug=1    shows safe areas and timings
 *   stage.html?comp=main&lang=en&captions=0 no caption band (for the narrated version)
 *   stage.html?comp=short&lang=ar&voice=1   on-screen lines reworded for the voice (data/voice/short.json)
 *
 * Exposed to render.mjs:
 *   window.EP_ready           true when everything is loaded
 *   window.EP_info            {fps, width, height, scale, frames, scenes}
 *   window.EP_frame(n)        draws global frame n, returns a PNG data URL
 *   window.EP_timeline()      scene starts, captions and sound cues (absolute times)
 *   window.EP_problems()      missing translations / equations / errors
 */
import * as EP from './ep.js';

const params = new URLSearchParams(location.search);
// captions=0 leaves the caption band out (the narrated version: the voice says the words)
const BURN_CAPTIONS = params.get('captions') !== '0';
const COMP = params.get('comp') || 'main';
const LANG = params.get('lang') || 'en';
const DEBUG = params.get('debug') === '1';
const ROOT = '../../../../';               // repository root, seen from code/engine/
const problems = [];

const FONT_FILES = [
  ['Inter', 'assets/fonts/inter/InterVariable.ttf', { weight: '100 900', style: 'normal' }],
  ['Inter', 'assets/fonts/inter/InterVariable-Italic.ttf', { weight: '100 900', style: 'italic' }],
  ['IBM Plex Sans Arabic', 'assets/fonts/ibm-plex-sans-arabic/IBMPlexSansArabic-Regular.ttf', { weight: '400' }],
  ['IBM Plex Sans Arabic', 'assets/fonts/ibm-plex-sans-arabic/IBMPlexSansArabic-Medium.ttf', { weight: '500' }],
  ['IBM Plex Sans Arabic', 'assets/fonts/ibm-plex-sans-arabic/IBMPlexSansArabic-SemiBold.ttf', { weight: '600' }],
  ['IBM Plex Sans Arabic', 'assets/fonts/ibm-plex-sans-arabic/IBMPlexSansArabic-Bold.ttf', { weight: '700' }],
];

async function loadFonts() {
  await Promise.all(FONT_FILES.map(async ([fam, file, desc]) => {
    const f = new FontFace(fam, `url(${ROOT}${file})`, desc);
    await f.load();
    document.fonts.add(f);
  }));
  await document.fonts.ready;
}

async function loadJSON(path, optional = false) {
  const r = await fetch(path);
  if (!r.ok) { if (optional) return null; throw new Error(`cannot load ${path}`); }
  return r.json();
}

const state = { comp: null, scenes: [], total: 0, canvas: null, ctx: null, off: [], W: 0, H: 0, scale: 1 };

// Default caption band ("narration"), per composition shape
const BANDS = {
  wide: { x: 960, y: 158, maxWidth: 1560, size: 50, weight: 600, maxLines: 2 },
  tall: { x: 540, y: 330, maxWidth: 900, size: 58, weight: 650, maxLines: 3 },
};

function sceneAt(frame) {
  const out = [];
  for (const s of state.scenes) {
    const f = frame - s.start;
    if (f >= 0 && f < s.frames) out.push({ s, f, t: f / EP.FPS });
  }
  return out;
}

function drawCaptions(ctx, s, t, band) {
  for (const c of s.captions || []) {
    if (c.burn === false) continue;
    const op = EP.win(t, c.in, c.out, 0.35, 0.3);
    if (op <= 0) continue;
    const rise = (1 - EP.ease.outCubic(EP.clamp((t - c.in) / 0.45))) * 14;
    const b = { ...band, ...(s.captionBand || {}), ...(c.band || {}) };
    EP.text(ctx, EP.T(c.key), {
      x: b.x, y: b.y + rise, align: 'center', size: b.size, weight: b.weight,
      maxWidth: b.maxWidth, maxLines: b.maxLines, shrink: true, color: EP.PAL.paper,
      opacity: op, shadow: 18,
    });
  }
}

function drawDebug(ctx, frame) {
  const { W, H } = state;
  ctx.save();
  ctx.strokeStyle = 'rgba(255,0,255,0.6)';
  ctx.lineWidth = 2;
  ctx.setLineDash([10, 8]);
  ctx.strokeRect(W * 0.05, H * 0.05, W * 0.9, H * 0.9);          // 90 % safe area
  if (W > H) ctx.strokeRect(W * 0.05, 64, W * 0.9, 220);          // caption band
  else { ctx.strokeRect(W * 0.05, H * 0.8, W * 0.9, H * 0.15); ctx.strokeRect(W * 0.85, H * 0.3, W * 0.1, H * 0.5); }
  ctx.setLineDash([]);
  ctx.fillStyle = 'rgba(255,0,255,0.9)';
  ctx.font = '600 22px Inter';
  const act = sceneAt(frame).map(a => `${a.s.id} t=${a.t.toFixed(3)}s`).join(' | ');
  ctx.fillText(`frame ${frame}  ${(frame / EP.FPS).toFixed(3)} s   ${act}`, 20, H - 16);
  ctx.restore();
}

function renderSceneInto(ctx, a) {
  const { W, H } = state;
  ctx.save();
  try {
    a.s.render(ctx, a.t, EP, { W, H, frame: a.f, t: a.t, duration: a.s.duration, lang: EP.I18N.lang, rtl: EP.isRTL(), comp: COMP });
  } catch (e) {
    problems.push(`render error in ${a.s.id} at t=${a.t.toFixed(3)}: ${e && e.stack || e}`);
  }
  ctx.restore();
  ctx.save();
  if (BURN_CAPTIONS) drawCaptions(ctx, a.s, a.t, W > H ? BANDS.wide : BANDS.tall);
  ctx.restore();
}

function drawFrame(frame) {
  const { ctx, W, H, scale } = state;
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  ctx.globalAlpha = 1;
  ctx.fillStyle = EP.PAL.ink;
  ctx.fillRect(0, 0, W, H);
  const act = sceneAt(frame);
  if (act.length === 1) {
    renderSceneInto(ctx, act[0]);
  } else if (act.length >= 2) {
    // cross-fade between the outgoing and the incoming scene
    const [a, b] = act;
    const k = EP.ease.inOutSine(EP.clamp((a.s.start + a.s.frames - frame) / state.comp.overlap));
    for (const [i, x] of [[0, a], [1, b]]) {
      const o = state.off[i];
      o.ctx.setTransform(scale, 0, 0, scale, 0, 0);
      o.ctx.globalAlpha = 1;
      o.ctx.fillStyle = EP.PAL.ink;
      o.ctx.fillRect(0, 0, W, H);
      renderSceneInto(o.ctx, x);
    }
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1;
    ctx.drawImage(state.off[1].canvas, 0, 0);
    ctx.globalAlpha = k;
    ctx.drawImage(state.off[0].canvas, 0, 0);
    ctx.globalAlpha = 1;
    ctx.setTransform(scale, 0, 0, scale, 0, 0);
  }
  // series mark, bottom-right, unless the scene hides it
  let logoOp = 1;
  for (const a of act) {
    const h = typeof a.s.hideLogo === 'function' ? a.s.hideLogo(a.t) : a.s.hideLogo ? 1 : 0;
    logoOp = Math.min(logoOp, 1 - EP.clamp(h));
  }
  if (state.comp.logo !== false && logoOp > 0) {
    const L = W > H ? { x: W - 96, y: H - 52 } : { x: W - 60, y: H * 0.16 };
    EP.logo(ctx, { ...L, opacity: 0.62 * logoOp });
  }
  if (DEBUG) drawDebug(ctx, frame);
}

async function boot() {
  EP.setLang(LANG);
  document.documentElement.lang = LANG;
  document.documentElement.dir = EP.I18N.dir;
  await loadFonts();
  await window.MathJax.startup.promise;

  const comps = await loadJSON('../data/comps.json');
  const comp = comps[COMP];
  if (!comp) throw new Error(`unknown composition ${COMP}`);
  state.comp = { overlap: 15, ...comp };
  state.W = comp.width; state.H = comp.height;
  EP.STAGE.W = comp.width; EP.STAGE.H = comp.height;
  state.scale = Number(params.get('scale') || comp.scale || 1);

  const common = await loadJSON('../data/strings/common.json', true);
  if (common) EP.addStrings(common);

  let start = 0;
  for (const [i, entry] of comp.scenes.entries()) {
    const mod = await import(`../scenes/${entry.id}.js`);
    const def = mod.default;
    for (const file of [entry.id, ...(def.strings || [])]) {
      const strings = await loadJSON(`../data/strings/${file}.json`, true);
      if (strings) EP.addStrings(strings);
    }
    const duration = entry.dur ?? def.duration;
    if (def.duration && Math.abs(def.duration - duration) > 1e-6) problems.push(`${entry.id}: scene says ${def.duration}s, comps.json says ${duration}s (comps.json wins)`);
    const frames = Math.round(duration * EP.FPS);
    if (i > 0) start -= state.comp.overlap;
    const s = { ...def, id: entry.id, duration, frames, start };
    state.scenes.push(s);
    start += frames;
  }
  state.total = start;

  // narrated version: a few on-screen lines reworded to match the voice (data/voice/<comp>.json)
  if (params.get('voice') === '1') {
    const v = await loadJSON(`../data/voice/${COMP}.json`, true);
    if (v) for (const [k, tr] of Object.entries(v)) if (!k.startsWith('_')) EP.I18N.strings[k] = { ...(EP.I18N.strings[k] || {}), ...tr };
  }

  // one-off preparation: equations, precomputed tables
  const W = state.W, H = state.H;
  for (const s of state.scenes) {
    for (const m of s.math || []) {
      const [tex, color] = typeof m === 'string' ? [m, EP.PAL.paper] : [m.tex, m.color || EP.PAL.paper];
      try { await EP.prepareMath(tex, color); } catch (e) { problems.push(`${s.id}: TeX failed: ${tex}: ${e}`); }
    }
    if (s.setup) {
      try { await s.setup(EP, { W, H, lang: EP.I18N.lang, rtl: EP.isRTL(), comp: COMP }); }
      catch (e) { problems.push(`setup error in ${s.id}: ${e && e.stack || e}`); }
    }
  }

  const canvas = document.getElementById('stage');
  canvas.width = Math.round(W * state.scale);
  canvas.height = Math.round(H * state.scale);
  canvas.style.width = `${W}px`;
  canvas.style.height = `${H}px`;
  state.canvas = canvas;
  state.ctx = canvas.getContext('2d', { alpha: false });
  for (let i = 0; i < 2; i++) {
    const c = document.createElement('canvas');
    c.width = canvas.width; c.height = canvas.height;
    state.off.push({ canvas: c, ctx: c.getContext('2d', { alpha: false }) });
  }
  for (const c of [state.ctx, ...state.off.map(o => o.ctx)]) { c.imageSmoothingQuality = 'high'; c.textRendering = 'optimizeLegibility'; }

  window.EP_info = {
    comp: COMP, lang: LANG, fps: EP.FPS, width: W, height: H, scale: state.scale, frames: state.total,
    scenes: state.scenes.map(s => ({ id: s.id, start: s.start, frames: s.frames, duration: s.duration })),
  };
  window.EP_ready = true;
}

window.EP_frame = (n, format = 'image/png') => { drawFrame(n); return state.canvas.toDataURL(format); };
window.EP_draw = n => { drawFrame(n); return true; };
window.EP_timeline = () => {
  const fps = EP.FPS;
  const captions = [], cues = [];
  for (const s of state.scenes) {
    const t0 = s.start / fps;
    for (const c of s.captions || []) {
      const e = EP.I18N.strings[c.key] || {};
      captions.push({ scene: s.id, key: c.key, in: +(t0 + c.in).toFixed(3), out: +(t0 + c.out).toFixed(3), burn: c.burn !== false, text: e });
    }
    for (const q of s.cues || []) cues.push({ scene: s.id, ...q, t: +(t0 + q.t).toFixed(4) });
  }
  return {
    comp: COMP, fps, frames: state.total, duration: state.total / fps, width: state.W, height: state.H,
    scenes: state.scenes.map(s => ({ id: s.id, start: s.start, frames: s.frames, t0: s.start / fps, t1: (s.start + s.frames) / fps, music: s.music || null })),
    captions: captions.sort((a, b) => a.in - b.in),
    cues: cues.sort((a, b) => a.t - b.t),
  };
};
window.EP_problems = () => [...problems, ...[...EP.I18N.missing].map(m => `missing string: ${m}`), ...[...EP.MISSING_MATH].map(m => `equation not in scene.math: ${m}`)];

boot().catch(e => { problems.push(`boot failed: ${e && e.stack || e}`); window.EP_failed = String(e && e.stack || e); });
