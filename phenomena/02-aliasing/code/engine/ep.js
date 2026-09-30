/*
 * Engineering Phenomena - frame engine (shared library).
 *
 * Runs inside headless Chromium. Every frame is drawn on one <canvas> by the
 * scenes in ../scenes/, then read back as a PNG by ../render.mjs.
 *
 * GOLDEN RULE: a scene's render(ctx, t) is a PURE function of t.
 * Nothing is remembered between frames, so any frame can be drawn alone, in
 * any order, by several workers at once, and every motion is exactly what
 * the equations say at that instant.
 *
 * Conventions
 *   - Units: logical pixels of the composition (1920 x 1080 for the main
 *     video). The engine scales for 4K stills, scenes never need to care.
 *   - Time: seconds, local to the scene. Frame n of a scene is t = n / FPS.
 *   - Angles: "clock" angles in radians, 0 = pointing up (12 o'clock),
 *     positive = clockwise on screen. A car driving to the right turns its
 *     wheels clockwise, so its wheel angle increases.
 *   - Colours: only the house palette PAL (and mixes / transparencies of it).
 */

export const FPS = 30;
export const TAU = Math.PI * 2;
export const DEG = Math.PI / 180;

// ---------------------------------------------------------------- palette
// Same values as assets/palette/palette.json and docs/STYLE_GUIDE.md.
export const PAL = Object.freeze({
  force: '#D55E00',     // vermillion  - force, load, stress
  motion: '#0072B2',    // blue        - motion, velocity, displacement
  energy: '#E69F00',    // orange      - heat, energy, power (also light output)
  fluid: '#56B4E9',     // sky blue    - fluid, air, flow
  field: '#CC79A7',     // purple      - electricity, magnetism, signals
  balance: '#009E73',   // green       - balance, safe, "it works"
  highlight: '#F0E442', // yellow      - look here (dark backgrounds only)
  ink: '#12161C',       // background
  steel: '#8C96A0',     // structures, parts, "just the object"
  paper: '#F4F3EF',     // text on dark backgrounds
});

const _rgb = new Map();
export function hexToRgb(hex) {
  let c = _rgb.get(hex);
  if (c) return c;
  const h = hex.replace('#', '');
  c = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
  _rgb.set(hex, c);
  return c;
}
/** 'rgba(...)' string of a palette hex colour with transparency a. */
export function rgba(hex, a = 1) {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}
/** Mix two palette colours (k = 0 gives a, k = 1 gives b). Returns hex. */
export function mix(a, b, k) {
  const A = hexToRgb(a), B = hexToRgb(b);
  return '#' + A.map((v, i) => Math.round(v + (B[i] - v) * k).toString(16).padStart(2, '0')).join('');
}
/** Shades used by the shared components. All are mixes of palette colours. */
export const SHADE = Object.freeze({
  inkDeep: '#0B0E12',                    // ink, darker (vignette, wheel wells)
  inkLift: mix(PAL.ink, PAL.steel, 0.07), // panels on the background
  rubber: mix(PAL.ink, PAL.steel, 0.17),  // tyres
  steelDark: mix(PAL.steel, PAL.ink, 0.5),
  steelMid: mix(PAL.steel, PAL.ink, 0.25),
  steelLight: mix(PAL.steel, PAL.paper, 0.4),
});

// ---------------------------------------------------------------- maths
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const invLerp = (a, b, x) => (b === a ? 0 : (x - a) / (b - a));
/** Map x from [a0, a1] to [b0, b1] (clamped by default). */
export function remap(x, a0, a1, b0, b1, clamped = true) {
  let k = invLerp(a0, a1, x);
  if (clamped) k = clamp(k);
  return lerp(b0, b1, k);
}
/** x wrapped into [0, period). */
export const wrap = (x, period) => x - period * Math.floor(x / period);
/** x wrapped into [-period/2, period/2]: the "nearest match" offset. */
export const wrapSigned = (x, period) => x - period * Math.round(x / period);

export const ease = {
  linear: k => k,
  inSine: k => 1 - Math.cos((k * Math.PI) / 2),
  outSine: k => Math.sin((k * Math.PI) / 2),
  inOutSine: k => -(Math.cos(Math.PI * k) - 1) / 2,
  inQuad: k => k * k,
  outQuad: k => 1 - (1 - k) * (1 - k),
  inOutQuad: k => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2),
  inCubic: k => k * k * k,
  outCubic: k => 1 - Math.pow(1 - k, 3),
  inOutCubic: k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
  inQuint: k => k ** 5,
  outQuint: k => 1 - Math.pow(1 - k, 5),
  inOutQuint: k => (k < 0.5 ? 16 * k ** 5 : 1 - Math.pow(-2 * k + 2, 5) / 2),
  outExpo: k => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k)),
  inOutExpo: k => (k <= 0 ? 0 : k >= 1 ? 1 : k < 0.5 ? Math.pow(2, 20 * k - 10) / 2 : (2 - Math.pow(2, -20 * k + 10)) / 2),
  outBack: k => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(k - 1, 3) + c1 * Math.pow(k - 1, 2); },
  smooth: k => k * k * (3 - 2 * k),
  smoother: k => k * k * k * (k * (6 * k - 15) + 10),
};

/** Progress of t through [t0, t1], clamped to 0..1, then eased. */
export function prog(t, t0, t1, e = ease.inOutCubic) {
  if (t1 <= t0) return t >= t1 ? 1 : 0;
  return e(clamp((t - t0) / (t1 - t0)));
}
/**
 * Opacity of something visible from tIn to tOut: fades in over dIn seconds
 * starting at tIn, fades out over dOut seconds ending at tOut.
 */
export function win(t, tIn, tOut, dIn = 0.4, dOut = 0.4) {
  if (t <= tIn || t >= tOut) return 0;
  const a = dIn > 0 ? ease.outCubic(clamp((t - tIn) / dIn)) : 1;
  const b = dOut > 0 ? ease.inOutSine(clamp((tOut - t) / dOut)) : 1;
  return Math.min(a, b);
}
/** Deterministic pseudo random generator (same seed, same numbers). */
export function rng(seed = 1) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let x = s;
    x = Math.imul(x ^ (x >>> 15), x | 1);
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}
/** Point at clock angle a (0 = up, clockwise positive) on a circle. */
export const polar = (cx, cy, r, a) => [cx + r * Math.sin(a), cy - r * Math.cos(a)];

/**
 * Integrate a rotation rate into an angle table, so a scene can ask for the
 * exact angle at any t without keeping state between frames.
 *   const spin = angleTable(t => fr(t), 0, 20);   // fr in turns per second
 *   spin(t) -> angle in radians (clock angle, clockwise positive)
 */
export function angleTable(rate, t0, t1, dt = 1 / 2400) {
  const n = Math.ceil((t1 - t0) / dt) + 1;
  const table = new Float64Array(n);
  let a = 0;
  for (let i = 1; i < n; i++) {
    const ta = t0 + (i - 1) * dt, tb = t0 + i * dt;
    // Simpson's rule on each small step
    a += (TAU * dt / 6) * (rate(ta) + 4 * rate((ta + tb) / 2) + rate(tb));
    table[i] = a;
  }
  return t => {
    if (t <= t0) return TAU * rate(t0) * (t - t0);
    const x = (t - t0) / dt, i = Math.floor(x);
    if (i >= n - 1) return table[n - 1] + TAU * rate(t1) * (t - t1);
    return table[i] + (table[i + 1] - table[i]) * (x - i);
  };
}

// ---------------------------------------------------------------- languages
const LOCALES = { en: 'en-GB', fr: 'fr-FR', ar: 'ar-TN', pt: 'pt-PT' };
export const I18N = { lang: 'en', dir: 'ltr', locale: 'en-GB', strings: {}, missing: new Set() };

export function setLang(lang) {
  I18N.lang = lang;
  I18N.dir = lang === 'ar' ? 'rtl' : 'ltr';
  I18N.locale = LOCALES[lang] || 'en-GB';
}
export function addStrings(table) { Object.assign(I18N.strings, table); }
export const isRTL = () => I18N.dir === 'rtl';

/** Size of the current composition (set by the stage before any scene runs). */
export const STAGE = { W: 1920, H: 1080 };
/**
 * x measured from the reading-start edge: startX(96) is 96 px from the left
 * in English and French, 96 px from the right in Arabic. Use it with
 * align: 'start' for text that hugs the side where reading begins.
 */
export const startX = x => (isRTL() ? STAGE.W - x : x);
/** Mirror an x position for right-to-left layouts (same as startX). */
export const mirrorX = startX;

/**
 * The on-screen string for a key, in the current language. {name} parts are
 * replaced from vars. A missing translation falls back to English and is
 * reported by the renderer.
 */
export function T(key, vars = null) {
  const e = I18N.strings[key];
  if (!e) { I18N.missing.add(`${key} (no such key)`); return `[${key}]`; }
  let s = e[I18N.lang];
  if (s == null || s === '') { if (I18N.lang !== 'en') I18N.missing.add(`${key} (${I18N.lang})`); s = e.en ?? `[${key}]`; }
  if (vars) s = s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m));
  return s;
}

const _nf = new Map();
/** Number in the current language: 12.4 (en), 12,4 (fr, ar). Minus is U+2212. */
export function num(x, digits = 0) {
  const key = I18N.locale + ':' + digits;
  let f = _nf.get(key);
  if (!f) {
    f = new Intl.NumberFormat(I18N.locale, { minimumFractionDigits: digits, maximumFractionDigits: digits, numberingSystem: 'latn', useGrouping: 'min2' });
    _nf.set(key, f);
  }
  const v = Object.is(Math.round(x * 10 ** digits), -0) ? 0 : x;
  return f.format(v).replace(/-/g, '−');
}
/** Quantity with its unit, joined by a no-break space: "12.4 m/s". */
export const qty = (x, unit, digits = 0) => `${num(x, digits)} ${unit}`;

// ---------------------------------------------------------------- type
export const TYPE = Object.freeze({ latin: '"Inter"', arabic: '"IBM Plex Sans Arabic"' });

function useArabic(latin) { return !latin && I18N.lang === 'ar'; }

/** CSS font string. Arabic gets IBM Plex Sans Arabic (weights 400 to 700). */
export function fontStr(size, weight = 500, { italic = false, latin = false } = {}) {
  if (useArabic(latin)) {
    const w = clamp(Math.round(weight / 100) * 100, 400, 700);
    return `${w} ${size}px ${TYPE.arabic}, ${TYPE.latin}`;
  }
  return `${italic ? 'italic ' : ''}${weight} ${size}px ${TYPE.latin}, ${TYPE.arabic}`;
}

function layoutLines(ctx, str, maxWidth) {
  const out = [];
  for (const para of String(str).split('\n')) {
    if (!maxWidth) { out.push(para); continue; }
    const words = para.split(' ');
    let line = '';
    for (const w of words) {
      const test = line ? line + ' ' + w : w;
      if (line && ctx.measureText(test).width > maxWidth) { out.push(line); line = w; }
      else line = test;
    }
    out.push(line);
  }
  return out;
}

/**
 * Draw text (single or multi-line). Returns its box {x, y, w, h, size, lines}.
 * Options:
 *   x, y        position. y is the first baseline unless anchor says otherwise
 *   anchor      'baseline' | 'middle' | 'top' | 'bottom'  (of the whole block)
 *   align       'start' | 'center' | 'end' | 'left' | 'right'
 *               'start' follows the reading direction (right edge in Arabic)
 *   size, weight, color, opacity, italic
 *   maxWidth    wrap lines to this width (px); '\n' forces a break
 *   maxLines    with shrink: true, the size shrinks until it fits
 *   lineHeight  multiple of size (default 1.2, Arabic 1.5)
 *   tracking    letter spacing in em (ignored for Arabic)
 *   caps        upper case (ignored for Arabic)
 *   latin       true for text that is always Latin and left-to-right
 *               (symbols, units, "30 Hz"), even in the Arabic version
 *   reveal      0..1 wipe in reading direction (1 = fully shown)
 *   shadow      blur radius of a soft ink shadow for legibility (0 = none)
 *   draw        false to only measure
 */
export function text(ctx, str, o = {}) {
  let {
    x = 0, y = 0, size = 48, weight = 500, color = PAL.paper, opacity = 1,
    align = 'start', anchor = 'baseline', maxWidth = 0, maxLines = 0, shrink = false,
    lineHeight = 0, tracking = 0, caps = false, italic = false, latin = false,
    reveal = 1, shadow = 0, draw = true,
  } = o;
  if (str == null) str = '';
  const ar = useArabic(latin);
  const rtl = ar;
  if (ar) size *= 1.06;
  if (caps && !ar) str = String(str).toLocaleUpperCase(I18N.locale);
  const lh = (lineHeight || (ar ? 1.5 : 1.2));

  ctx.save();
  ctx.direction = rtl ? 'rtl' : 'ltr';
  ctx.letterSpacing = !ar && tracking ? `${tracking * size}px` : '0px';
  ctx.font = fontStr(size, weight, { italic, latin });
  let lines = layoutLines(ctx, str, maxWidth);
  if (shrink && maxWidth) {
    const minSize = size * 0.6;
    const fits = () => (!maxLines || lines.length <= maxLines) && lines.every(l => ctx.measureText(l).width <= maxWidth + 0.5);
    while (!fits() && size > minSize) {
      size *= 0.96;
      ctx.letterSpacing = !ar && tracking ? `${tracking * size}px` : '0px';
      ctx.font = fontStr(size, weight, { italic, latin });
      lines = layoutLines(ctx, str, maxWidth);
    }
  }
  const widths = lines.map(l => ctx.measureText(l).width);
  const w = Math.max(0, ...widths);
  const step = size * lh;
  const capH = size * 0.72;
  let first = y;
  if (anchor === 'middle') first = y - ((lines.length - 1) * step) / 2 + capH / 2;
  else if (anchor === 'top') first = y + capH;
  else if (anchor === 'bottom') first = y - (lines.length - 1) * step;
  let a = align;
  if (a === 'start') a = rtl ? 'right' : 'left';
  if (a === 'end') a = rtl ? 'left' : 'right';
  const left = a === 'left' ? x : a === 'right' ? x - w : x - w / 2;
  const box = { x: left, y: first - capH, w, h: (lines.length - 1) * step + capH, size, lines, step, baseline: first };

  if (draw && opacity > 0 && reveal > 0 && str !== '') {
    ctx.globalAlpha *= clamp(opacity);
    ctx.fillStyle = color;
    ctx.textAlign = a;
    ctx.textBaseline = 'alphabetic';
    if (shadow) { ctx.shadowColor = rgba(PAL.ink, 0.9); ctx.shadowBlur = shadow; }
    if (reveal < 1) {
      const pad = size;
      const cw = (w + 2 * pad) * clamp(reveal);
      ctx.beginPath();
      if (rtl) ctx.rect(left + w + pad - cw, box.y - pad, cw, box.h + 2 * pad);
      else ctx.rect(left - pad, box.y - pad, cw, box.h + 2 * pad);
      ctx.clip();
    }
    lines.forEach((l, i) => ctx.fillText(l, x, first + i * step));
  }
  ctx.restore();
  return box;
}
/** Measure without drawing. */
export const measure = (ctx, str, o = {}) => text(ctx, str, { ...o, draw: false });

/**
 * Numbers whose digits must not jitter while they change (counters, speed
 * readouts): every digit gets the same width. Always left-to-right.
 */
export function textTab(ctx, str, o = {}) {
  const { x = 0, y = 0, size = 48, weight = 600, color = PAL.paper, opacity = 1, align = 'left' } = o;
  ctx.save();
  ctx.direction = 'ltr';
  ctx.letterSpacing = '0px';
  ctx.font = fontStr(size, weight, { latin: true });
  const cell = ctx.measureText('0').width;
  const chars = [...String(str)];
  const widths = chars.map(c => (/[0-9]/.test(c) ? cell : ctx.measureText(c).width));
  const total = widths.reduce((s, v) => s + v, 0);
  let cx = align === 'right' ? x - total : align === 'center' ? x - total / 2 : x;
  ctx.globalAlpha *= clamp(opacity);
  ctx.fillStyle = color;
  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'center';
  chars.forEach((c, i) => { ctx.fillText(c, cx + widths[i] / 2, y); cx += widths[i]; });
  ctx.restore();
  return { w: total };
}

// ---------------------------------------------------------------- equations
// TeX is typeset once by MathJax (Computer Modern look, italic variables,
// upright \mathrm units) and cached as a vector image.
const MATH = new Map();
const mathKey = (tex, color) => `${color}|${tex}`;
export const MISSING_MATH = new Set();

export async function prepareMath(tex, color = PAL.paper) {
  const key = mathKey(tex, color);
  if (MATH.has(key)) return MATH.get(key);
  const node = window.MathJax.tex2svg(tex, { display: false });
  const svg = node.querySelector('svg');
  const vb = svg.getAttribute('viewBox').split(/[\s,]+/).map(Number);
  svg.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  svg.setAttribute('width', String(vb[2] / 10));
  svg.setAttribute('height', String(vb[3] / 10));
  svg.setAttribute('style', `color:${color}`);
  svg.setAttribute('color', color);
  const src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(svg));
  const img = new Image();
  img.src = src;
  await img.decode();
  const entry = { img, w: vb[2] / 1000, h: vb[3] / 1000, asc: -vb[1] / 1000 };
  MATH.set(key, entry);
  return entry;
}

/**
 * Draw a prepared TeX equation. size = font size in px (1 em). Equations are
 * always left-to-right, in every language.
 *   align: 'left' | 'center' | 'right'   anchor: 'baseline' | 'middle' | 'top' | 'bottom'
 * Returns the box {x, y, w, h} or null when the equation was not prepared.
 */
export function math(ctx, tex, o = {}) {
  const { x = 0, y = 0, size = 56, color = PAL.paper, align = 'center', anchor = 'middle', opacity = 1, draw = true } = o;
  const e = MATH.get(mathKey(tex, color));
  if (!e) { MISSING_MATH.add(`${color} ${tex}`); return null; }
  const w = e.w * size, h = e.h * size;
  const dx = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  const dy = anchor === 'baseline' ? y - e.asc * size : anchor === 'middle' ? y - h / 2 : anchor === 'top' ? y : y - h;
  if (draw && opacity > 0) {
    ctx.save();
    ctx.globalAlpha *= clamp(opacity);
    ctx.drawImage(e.img, dx, dy, w, h);
    ctx.restore();
  }
  return { x: dx, y: dy, w, h };
}

// ---------------------------------------------------------------- shapes
export function roundRect(ctx, x, y, w, h, r) {
  const rr = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rr, y);
  ctx.arcTo(x + w, y, x + w, y + h, rr);
  ctx.arcTo(x + w, y + h, x, y + h, rr);
  ctx.arcTo(x, y + h, x, y, rr);
  ctx.arcTo(x, y, x + w, y, rr);
  ctx.closePath();
}

function arrowHead(ctx, tx, ty, ang, size, filled, lw) {
  const a1 = ang + Math.PI * 0.82, a2 = ang - Math.PI * 0.82;
  const p1 = [tx + size * Math.cos(a1), ty + size * Math.sin(a1)];
  const p2 = [tx + size * Math.cos(a2), ty + size * Math.sin(a2)];
  ctx.setLineDash([]);
  if (filled) {
    ctx.beginPath();
    ctx.moveTo(tx + Math.cos(ang) * lw * 0.3, ty + Math.sin(ang) * lw * 0.3);
    ctx.lineTo(...p1);
    ctx.lineTo(tx - Math.cos(ang) * size * 0.55, ty - Math.sin(ang) * size * 0.55);
    ctx.lineTo(...p2);
    ctx.closePath();
    ctx.fill();
  } else {
    ctx.beginPath();
    ctx.moveTo(...p1);
    ctx.lineTo(tx, ty);
    ctx.lineTo(...p2);
    ctx.stroke();
  }
}

/**
 * Straight arrow following the style guide:
 *   kind 'motion' (default): blue, thinner, open head
 *   kind 'force'           : vermillion, thick, filled head
 * Options: color, width, headSize, dash (true or [on, off]), dashOffset,
 * alpha, progress (0..1 draws the arrow growing from its tail).
 */
export function arrow(ctx, x1, y1, x2, y2, o = {}) {
  const kind = o.kind || 'motion';
  const color = o.color || (kind === 'force' ? PAL.force : PAL.motion);
  const lw = o.width || (kind === 'force' ? 10 : 5);
  const hs = o.headSize || (kind === 'force' ? lw * 3 : lw * 4);
  const filled = (o.head || (kind === 'force' ? 'filled' : 'open')) === 'filled';
  const p = clamp(o.progress ?? 1);
  if (p <= 0 || (o.alpha ?? 1) <= 0) return;
  const ex = x1 + (x2 - x1) * p, ey = y1 + (y2 - y1) * p;
  const ang = Math.atan2(ey - y1, ex - x1);
  const len = Math.hypot(ex - x1, ey - y1);
  const back = filled ? hs * 0.5 : lw * 0.5;
  ctx.save();
  ctx.globalAlpha *= o.alpha ?? 1;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = lw;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  if (o.dash) ctx.setLineDash(Array.isArray(o.dash) ? o.dash : [lw * 2.4, lw * 2]);
  ctx.lineDashOffset = o.dashOffset || 0;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x1 + Math.cos(ang) * Math.max(0, len - back), y1 + Math.sin(ang) * Math.max(0, len - back));
  ctx.stroke();
  if (len > hs * 0.6) arrowHead(ctx, ex, ey, ang, hs, filled, lw);
  ctx.restore();
}

/**
 * Curved arrow along a circle, from clock angle a0 to a1 (head at a1).
 * a1 > a0 turns clockwise. Same style options as arrow().
 */
export function arcArrow(ctx, cx, cy, r, a0, a1, o = {}) {
  const kind = o.kind || 'motion';
  const color = o.color || (kind === 'force' ? PAL.force : PAL.motion);
  const lw = o.width || (kind === 'force' ? 10 : 5);
  const hs = o.headSize || (kind === 'force' ? lw * 3 : lw * 4);
  const filled = (o.head || (kind === 'force' ? 'filled' : 'open')) === 'filled';
  const p = clamp(o.progress ?? 1);
  if (p <= 0 || Math.abs(a1 - a0) < 1e-6 || (o.alpha ?? 1) <= 0) return;
  const end = a0 + (a1 - a0) * p;
  const dir = Math.sign(a1 - a0);
  const arcLen = Math.abs(end - a0) * r;
  const trim = Math.min(arcLen * 0.9, (filled ? hs * 0.5 : lw * 0.5)) / r;
  ctx.save();
  ctx.globalAlpha *= o.alpha ?? 1;
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = lw;
  ctx.lineCap = 'round';
  if (o.dash) ctx.setLineDash(Array.isArray(o.dash) ? o.dash : [lw * 2.4, lw * 2]);
  ctx.lineDashOffset = o.dashOffset || 0;
  ctx.beginPath();
  ctx.arc(cx, cy, r, a0 - Math.PI / 2, end - dir * trim - Math.PI / 2, dir < 0);
  ctx.stroke();
  if (arcLen > hs * 0.8) {
    const [tx, ty] = polar(cx, cy, r, end);
    // tangent direction at the tip, slightly corrected for the curvature
    const tang = end - Math.PI / 2 + dir * Math.PI / 2 - dir * (hs * 0.35) / r;
    arrowHead(ctx, tx, ty, tang, hs, filled, lw);
  }
  ctx.restore();
}

// ---------------------------------------------------------------- UI marks
/** Small upper-case label in a thin outlined box, e.g. "SLOWED DOWN x10". */
export function badge(ctx, str, o = {}) {
  const { x = 96, y = 290, align = 'start', color = PAL.paper, border = PAL.steel, size = 22, opacity = 1, fill = true } = o;
  if (opacity <= 0) return null;
  const ar = useArabic(false);
  const box = measure(ctx, str, { size, weight: 700, tracking: 0.12, caps: true });
  const padX = size * 0.75, padY = size * 0.55;
  const w = box.w + padX * 2, h = box.size * 0.72 + padY * 2;
  let a = align;
  if (a === 'start') a = ar ? 'right' : 'left';
  if (a === 'end') a = ar ? 'left' : 'right';
  const left = a === 'left' ? x : a === 'right' ? x - w : x - w / 2;
  ctx.save();
  ctx.globalAlpha *= clamp(opacity);
  roundRect(ctx, left, y - h / 2, w, h, 6);
  if (fill) { ctx.fillStyle = rgba(PAL.ink, 0.72); ctx.fill(); }
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = rgba(border, 0.9);
  ctx.stroke();
  ctx.restore();
  text(ctx, str, { x: left + w / 2, y, anchor: 'middle', align: 'center', size, weight: 700, tracking: 0.12, caps: true, color, opacity });
  return { x: left, y: y - h / 2, w, h };
}

/** Chapter label: short rule + spaced capitals, in highlight yellow. */
export function eyebrow(ctx, str, o = {}) {
  const { x = 96, y = 92, align = 'start', color = PAL.highlight, size = 22, opacity = 1, reveal = 1 } = o;
  if (opacity <= 0) return null;
  const ar = useArabic(false);
  const box = measure(ctx, str, { size, weight: 700, tracking: 0.16, caps: true });
  const rule = 34, gap = 14;
  const w = rule + gap + box.w;
  let a = align;
  if (a === 'start') a = ar ? 'right' : 'left';
  if (a === 'end') a = ar ? 'left' : 'right';
  const left = a === 'left' ? x : a === 'right' ? x - w : x - w / 2;
  const ruleX = ar ? left + w - rule : left;
  const textX = ar ? left + w - rule - gap : left + rule + gap;
  ctx.save();
  ctx.globalAlpha *= clamp(opacity);
  ctx.fillStyle = color;
  ctx.fillRect(ruleX + (ar ? rule * (1 - clamp(reveal)) : 0), y - size * 0.36 - 1.5, rule * clamp(reveal), 3);
  ctx.restore();
  text(ctx, str, { x: textX, y, align: ar ? 'right' : 'left', size, weight: 700, tracking: 0.16, caps: true, color, opacity, reveal });
  return { x: left, y: y - size, w, h: size };
}

/**
 * Series mark (bottom-right corner, same place in every piece): a small
 * resonance peak with its yellow dot, and the series name.
 * (x, y) is the bottom-right corner of the mark.
 */
export function logo(ctx, o = {}) {
  const { x = 1824, y = 1026, opacity = 0.62, scale = 1 } = o;
  if (opacity <= 0) return;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.globalAlpha *= opacity;
  ctx.direction = 'ltr';
  ctx.font = fontStr(15, 700, { latin: true });
  ctx.letterSpacing = '2.1px';
  const label = 'ENGINEERING PHENOMENA';
  const tw = ctx.measureText(label).width;
  ctx.fillStyle = PAL.paper;
  ctx.textAlign = 'right';
  ctx.textBaseline = 'alphabetic';
  ctx.fillText(label, 0, -6);
  // peak glyph
  const gx = -tw - 46, gy = -4;
  ctx.strokeStyle = PAL.paper;
  ctx.lineWidth = 2.2;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  for (let i = 0; i <= 40; i++) {
    const u = i / 40;
    const r = 0.25 + 1.6 * u;                          // push frequency ratio
    const amp = 1 / Math.sqrt((1 - r * r) ** 2 + (2 * 0.12 * r) ** 2);
    const px = gx + u * 34, py = gy - Math.min(amp, 4.2) / 4.2 * 18;
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  }
  ctx.stroke();
  const peakU = (Math.sqrt(1 - 2 * 0.12 ** 2) - 0.25) / 1.6;
  ctx.fillStyle = PAL.highlight;
  ctx.beginPath();
  ctx.arc(gx + peakU * 34, gy - 18, 3, 0, TAU);
  ctx.fill();
  ctx.restore();
}

/**
 * House background: ink, a faint engineering grid (like the series banner)
 * and a soft vignette.
 */
export function bg(ctx, W, H, o = {}) {
  const { grid = true, gridAlpha = 0.05, step = 48, vignette = true, offsetX = 0, offsetY = 0 } = o;
  ctx.save();
  ctx.fillStyle = PAL.ink;
  ctx.fillRect(0, 0, W, H);
  if (grid) {
    ctx.strokeStyle = rgba(PAL.steel, gridAlpha);
    ctx.lineWidth = 1;
    ctx.beginPath();
    const ox = wrap(offsetX, step), oy = wrap(offsetY, step);
    for (let x = ox + 0.5; x < W; x += step) { ctx.moveTo(x, 0); ctx.lineTo(x, H); }
    for (let y = oy + 0.5; y < H; y += step) { ctx.moveTo(0, y); ctx.lineTo(W, y); }
    ctx.stroke();
  }
  if (vignette) {
    const g = ctx.createRadialGradient(W / 2, H * 0.48, Math.min(W, H) * 0.35, W / 2, H / 2, Math.hypot(W, H) * 0.62);
    g.addColorStop(0, rgba(SHADE.inkDeep, 0));
    g.addColorStop(1, rgba(SHADE.inkDeep, 0.85));
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, W, H);
  }
  ctx.restore();
}

/**
 * Camera icon (line drawing). "shot" 0..1 draws a short ring pulse around
 * the lens when a picture is taken: small area, never a screen flash.
 */
export function camera(ctx, o = {}) {
  const { x = 0, y = 0, s = 1, color = PAL.paper, opacity = 1, shot = 0 } = o;
  if (opacity <= 0) return;
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(s, s);
  ctx.globalAlpha *= clamp(opacity);
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 3;
  ctx.lineJoin = 'round';
  roundRect(ctx, -34, -22, 68, 46, 8);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-14, -22); ctx.lineTo(-9, -30); ctx.lineTo(9, -30); ctx.lineTo(14, -22);
  ctx.stroke();
  ctx.beginPath(); ctx.arc(0, 1, 13, 0, TAU); ctx.stroke();
  ctx.beginPath(); ctx.arc(0, 1, 5, 0, TAU); ctx.fill();
  ctx.beginPath(); ctx.arc(24, -13, 2.5, 0, TAU); ctx.fill();
  if (shot > 0 && shot < 1) {
    ctx.globalAlpha *= (1 - shot) * 0.9;
    ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(0, 1, 13 + 30 * ease.outCubic(shot), 0, TAU); ctx.stroke();
  }
  ctx.restore();
}

// ---------------------------------------------------------------- layers
const _layers = [];
let _depth = 0;
/**
 * Draw something as one flat layer, then blend the layer with opacity alpha,
 * so the overlapping parts of a drawing never show through each other while
 * it fades in or out. (x0, y0, w, h) is its bounding box in current
 * coordinates. The layer is pixel-aligned: no resampling, no softening.
 */
export function layer(ctx, alpha, x0, y0, w, h, draw) {
  if (alpha <= 0) return;
  const m = ctx.getTransform();
  if (Math.abs(m.b) > 1e-6 || Math.abs(m.c) > 1e-6 || m.a <= 0 || m.d <= 0) {
    ctx.save(); ctx.globalAlpha *= alpha; draw(ctx); ctx.restore();   // rotated or mirrored: draw directly
    return;
  }
  const pad = 2;
  const cw = ctx.canvas.width, ch = ctx.canvas.height;
  // only the visible part of the box, in device pixels
  const dx = Math.max(0, Math.floor(m.e + x0 * m.a) - pad), dy = Math.max(0, Math.floor(m.f + y0 * m.d) - pad);
  const pw = Math.min(cw, Math.ceil(m.e + (x0 + w) * m.a) + pad) - dx;
  const ph = Math.min(ch, Math.ceil(m.f + (y0 + h) * m.d) + pad) - dy;
  if (pw <= 0 || ph <= 0) return;
  // one scratch canvas per nesting level, as big as the frame from its first use:
  // the same canvas size every time keeps the pixels identical in any frame order
  let c = _layers[_depth];
  if (!c || c.width < cw || c.height < ch) {
    const nw = Math.max(cw, c ? c.width : 0), nh = Math.max(ch, c ? c.height : 0);
    c = _layers[_depth] = document.createElement('canvas');
    c.width = nw;
    c.height = nh;
  }
  const g = c.getContext('2d');
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.globalAlpha = 1;
  g.globalCompositeOperation = 'source-over';
  g.shadowBlur = 0;
  g.clearRect(0, 0, pw, ph);
  g.setTransform(m.a, 0, 0, m.d, m.e - dx, m.f - dy);
  _depth++;
  try { draw(g); } finally { _depth--; }
  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.globalAlpha *= alpha;
  ctx.drawImage(c, 0, 0, pw, ph, dx, dy, pw, ph);
  ctx.restore();
}

// ---------------------------------------------------------------- the wheel
/**
 * Outline of spoke i of a star wheel, as a Path2D in wheel coordinates
 * (centre at 0,0, radius r, rotated by angle). Spokes widen towards the rim.
 */
export function spokePath(r, i, angle, spokes = 5) {
  const a = angle + (i * TAU) / spokes;
  const r0 = 0.15 * r, r1 = 0.625 * r;
  const w0 = 0.105 * r, w1 = 0.2 * r;
  const ca = Math.cos(a), sa = Math.sin(a);
  // local frame: u along the spoke (outwards), v across it
  const P = (u, v) => [u * sa + v * ca, -u * ca + v * sa];
  const p = new Path2D();
  p.moveTo(...P(r0, -w0 / 2));
  p.quadraticCurveTo(...P((r0 + r1) / 2, -w0 * 0.36), ...P(r1, -w1 / 2));
  p.lineTo(...P(r1 + 0.02 * r, 0));
  p.lineTo(...P(r1, w1 / 2));
  p.quadraticCurveTo(...P((r0 + r1) / 2, w0 * 0.36), ...P(r0, w0 / 2));
  p.closePath();
  return p;
}

/**
 * A car wheel seen from the side: tyre, 5-spoke alloy rim, brake disc and a
 * caliper that does NOT turn (it is fixed to the car).
 * Options:
 *   x, y, r      centre and tyre radius (px)
 *   angle        clock angle of spoke 0 (radians)
 *   spokes       number of identical spokes (default 5)
 *   highlight    index of a spoke painted yellow ("look here"), or null
 *   highlightAlpha 0..1 to fade that paint in and out
 *   tyre         draw the tyre (default true)
 *   caliper      draw the fixed brake caliper (default true)
 *   opacity
 */
export function wheel(ctx, o = {}) {
  const { x = 0, y = 0, r = 200, angle = 0, spokes = 5, highlight = null, highlightAlpha = 1, tyre = true, caliper = true, opacity = 1 } = o;
  if (opacity <= 0) return;
  if (ctx.globalAlpha * opacity < 0.999 && !o._flat) {
    layer(ctx, clamp(opacity), x - r - 3, y - r - 3, 2 * r + 6, 2 * r + 6, c => wheel(c, { ...o, opacity: 1, _flat: true }));
    return;
  }
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= clamp(opacity);

  if (tyre) {
    ctx.fillStyle = SHADE.rubber;
    ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill();
    const g = ctx.createRadialGradient(0, 0, r * 0.66, 0, 0, r);
    g.addColorStop(0, rgba(PAL.steel, 0.0));
    g.addColorStop(0.55, rgba(PAL.steel, 0.12));
    g.addColorStop(1, rgba(PAL.steel, 0.02));
    ctx.fillStyle = g;
    ctx.beginPath(); ctx.arc(0, 0, r, 0, TAU); ctx.fill();
    ctx.lineWidth = Math.max(1.5, r * 0.012);
    ctx.strokeStyle = rgba(PAL.steel, 0.35);
    ctx.beginPath(); ctx.arc(0, 0, r - ctx.lineWidth / 2, 0, TAU); ctx.stroke();
  }
  // rim lip and barrel
  ctx.fillStyle = SHADE.steelLight;
  ctx.beginPath(); ctx.arc(0, 0, r * 0.69, 0, TAU); ctx.fill();
  ctx.fillStyle = SHADE.steelDark;
  ctx.beginPath(); ctx.arc(0, 0, r * 0.655, 0, TAU); ctx.fill();
  // wheel well seen between the spokes, brake disc, fixed caliper
  ctx.fillStyle = SHADE.inkDeep;
  ctx.beginPath(); ctx.arc(0, 0, r * 0.635, 0, TAU); ctx.fill();
  ctx.fillStyle = mix(PAL.steel, PAL.ink, 0.72);
  ctx.beginPath(); ctx.arc(0, 0, r * 0.53, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(PAL.steel, 0.14);
  ctx.lineWidth = Math.max(1, r * 0.006);
  for (const k of [0.5, 0.44, 0.38]) { ctx.beginPath(); ctx.arc(0, 0, r * k, 0, TAU); ctx.stroke(); }
  if (caliper) {
    ctx.fillStyle = SHADE.steelMid;
    ctx.beginPath();
    ctx.arc(0, 0, r * 0.57, (65 - 90) * DEG, (115 - 90) * DEG);
    ctx.arc(0, 0, r * 0.4, (112 - 90) * DEG, (68 - 90) * DEG, true);
    ctx.closePath();
    ctx.fill();
  }
  // spokes
  for (let i = 0; i < spokes; i++) {
    const p = spokePath(r, i, angle, spokes);
    const hl = highlight === i && highlightAlpha > 0;
    ctx.fillStyle = PAL.steel;
    ctx.fill(p);
    if (hl) {
      ctx.save();
      ctx.globalAlpha *= clamp(highlightAlpha);
      ctx.fillStyle = PAL.highlight;
      ctx.fill(p);
      ctx.restore();
    }
    ctx.lineWidth = Math.max(1, r * 0.008);
    ctx.strokeStyle = rgba(PAL.paper, 0.22);
    ctx.stroke(p);
  }
  // hub, lug nuts, centre cap
  ctx.fillStyle = PAL.steel;
  ctx.beginPath(); ctx.arc(0, 0, r * 0.19, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(PAL.ink, 0.35);
  ctx.lineWidth = Math.max(1, r * 0.01);
  ctx.beginPath(); ctx.arc(0, 0, r * 0.19, 0, TAU); ctx.stroke();
  ctx.fillStyle = SHADE.steelDark;
  for (let i = 0; i < spokes; i++) {
    const [lx, ly] = polar(0, 0, r * 0.12, angle + (i + 0.5) * TAU / spokes);
    ctx.beginPath(); ctx.arc(lx, ly, r * 0.024, 0, TAU); ctx.fill();
  }
  ctx.fillStyle = SHADE.steelLight;
  ctx.beginPath(); ctx.arc(0, 0, r * 0.06, 0, TAU); ctx.fill();
  // fixed light from the top left: soft sheen over the rim
  const sh = ctx.createRadialGradient(-r * 0.3, -r * 0.35, r * 0.05, -r * 0.1, -r * 0.1, r * 0.75);
  sh.addColorStop(0, rgba(PAL.paper, 0.16));
  sh.addColorStop(1, rgba(PAL.paper, 0));
  ctx.fillStyle = sh;
  ctx.beginPath(); ctx.arc(0, 0, r * 0.69, 0, TAU); ctx.fill();
  ctx.restore();
}

/**
 * Just the spoke outlines, for "where the spokes were in the previous
 * picture" ghosts. Options: x, y, r, angle, spokes, color, opacity, width, dash.
 */
export function wheelGhost(ctx, o = {}) {
  const { x = 0, y = 0, r = 200, angle = 0, spokes = 5, color = PAL.steel, opacity = 0.6, width = 2.5, dash = null, only = null } = o;
  if (opacity <= 0) return;
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= clamp(opacity);
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineJoin = 'round';
  if (dash) ctx.setLineDash(dash);
  for (let i = 0; i < spokes; i++) if (only == null || only === i) ctx.stroke(spokePath(r, i, angle, spokes));
  ctx.restore();
}

// ---------------------------------------------------------------- the car
/**
 * Side view of a small car driving to the right, drawn around its REAR wheel.
 *   x, y    centre of the rear wheel (px);  r = tyre radius (px)
 *   rearAngle, frontAngle   wheel angles; highlight, spokes passed to wheel()
 * The front wheel centre is at x + 7.7 r. Ground is at y + r.
 * Real proportions for a 0.33 m tyre: length 4.1 m, height 1.45 m.
 * Returns {rear: [x, y], front: [x, y]}.
 */
export function car(ctx, o = {}) {
  const { x = 0, y = 0, r = 60, rearAngle = 0, frontAngle = 0, spokes = 5, highlight = null, opacity = 1, wheels = true } = o;
  const L = 7.7;
  if (opacity <= 0) return { rear: [x, y], front: [x + L * r, y] };
  if (ctx.globalAlpha * opacity < 0.999 && !o._flat) {
    layer(ctx, clamp(opacity), x - 4.2 * r, y - 3.7 * r, 16.6 * r, 5.6 * r, c => car(c, { ...o, opacity: 1, _flat: true }));
    return { rear: [x, y], front: [x + L * r, y] };
  }
  const S = (u, v) => [x + u * r, y + v * r];
  ctx.save();
  ctx.globalAlpha *= clamp(opacity);

  // soft ground shadow
  const gs = ctx.createRadialGradient(x + (L / 2) * r, y + r, r * 0.5, x + (L / 2) * r, y + r, r * 6.6);
  gs.addColorStop(0, rgba(SHADE.inkDeep, 0.85));
  gs.addColorStop(1, rgba(SHADE.inkDeep, 0));
  ctx.save();
  ctx.translate(0, y + r);
  ctx.scale(1, 0.09);
  ctx.translate(0, -(y + r));
  ctx.fillStyle = gs;
  ctx.fillRect(x - 4 * r, y + r - 7 * r, 16 * r, 14 * r);
  ctx.restore();

  const arch = 1.13;
  const body = new Path2D();
  body.moveTo(...S(-2.62, 0.5));
  body.lineTo(...S(-2.7, -0.35));
  body.bezierCurveTo(...S(-2.78, -1.2), ...S(-2.72, -1.75), ...S(-2.45, -2.2));
  body.bezierCurveTo(...S(-2.15, -2.75), ...S(-1.75, -3.25), ...S(-0.9, -3.36));
  body.lineTo(...S(3.6, -3.4));
  body.bezierCurveTo(...S(4.3, -3.38), ...S(4.75, -3.1), ...S(5.35, -2.55));
  body.bezierCurveTo(...S(5.9, -2.05), ...S(6.3, -1.9), ...S(7.1, -1.82));
  body.bezierCurveTo(...S(8.3, -1.72), ...S(9.25, -1.55), ...S(9.52, -1.05));
  body.bezierCurveTo(...S(9.72, -0.65), ...S(9.68, -0.1), ...S(9.55, 0.48));
  const sill = 0.5, aa = Math.asin(sill / arch), ax = Math.cos(aa) * arch;
  body.lineTo(...S(L + ax, sill));
  body.arc(x + L * r, y, arch * r, aa, Math.PI - aa, true);
  body.lineTo(...S(ax, sill));
  body.arc(x, y, arch * r, aa, Math.PI - aa, true);
  body.closePath();

  const g = ctx.createLinearGradient(0, y - 3.4 * r, 0, y + 0.6 * r);
  g.addColorStop(0, SHADE.steelLight);
  g.addColorStop(0.42, PAL.steel);
  g.addColorStop(1, SHADE.steelMid);
  ctx.fillStyle = g;
  ctx.fill(body);

  // windows (dark glass with a soft reflection) and pillar
  const glass = new Path2D();
  glass.moveTo(...S(-1.85, -2.12));
  glass.bezierCurveTo(...S(-1.55, -2.7), ...S(-1.2, -3.08), ...S(-0.6, -3.12));
  glass.lineTo(...S(3.5, -3.15));
  glass.bezierCurveTo(...S(4.1, -3.13), ...S(4.5, -2.85), ...S(5.05, -2.2));
  glass.lineTo(...S(5.2, -2.02));
  glass.closePath();
  ctx.fillStyle = mix(PAL.ink, PAL.steel, 0.22);
  ctx.fill(glass);
  ctx.save();
  ctx.clip(glass);
  const rg = ctx.createLinearGradient(...S(0, -3.2), ...S(1.2, -1.9));
  rg.addColorStop(0, rgba(PAL.paper, 0.14));
  rg.addColorStop(0.5, rgba(PAL.paper, 0.03));
  rg.addColorStop(1, rgba(PAL.paper, 0));
  ctx.fillStyle = rg;
  ctx.fill(glass);
  ctx.fillStyle = PAL.steel;
  ctx.fillRect(...S(1.72, -3.3), 0.28 * r, 1.4 * r);
  ctx.restore();

  // shoulder line, door seams, handles, mirror, lights
  ctx.strokeStyle = rgba(PAL.paper, 0.22);
  ctx.lineWidth = Math.max(1, r * 0.03);
  ctx.beginPath(); ctx.moveTo(...S(-2.66, -1.55)); ctx.bezierCurveTo(...S(0.5, -1.62), ...S(6, -1.66), ...S(9.4, -1.32)); ctx.stroke();
  ctx.strokeStyle = rgba(PAL.ink, 0.45);
  ctx.lineWidth = Math.max(1, r * 0.025);
  ctx.beginPath(); ctx.moveTo(...S(1.86, -1.95)); ctx.lineTo(...S(1.9, 0.52)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(...S(5.2, -2.0)); ctx.bezierCurveTo(...S(5.45, -1.2), ...S(5.5, -0.3), ...S(5.45, 0.52)); ctx.stroke();
  ctx.fillStyle = rgba(PAL.ink, 0.5);
  roundRect(ctx, ...S(0.85, -1.35), 0.55 * r, 0.13 * r, 0.06 * r); ctx.fill();
  roundRect(ctx, ...S(3.85, -1.35), 0.55 * r, 0.13 * r, 0.06 * r); ctx.fill();
  ctx.fillStyle = SHADE.steelMid;
  roundRect(ctx, ...S(5.0, -2.25), 0.5 * r, 0.32 * r, 0.1 * r); ctx.fill();
  ctx.fillStyle = rgba(PAL.paper, 0.85);
  ctx.beginPath(); ctx.moveTo(...S(9.05, -1.5)); ctx.quadraticCurveTo(...S(9.5, -1.45), ...S(9.55, -1.12)); ctx.lineTo(...S(8.75, -1.2)); ctx.closePath(); ctx.fill();
  ctx.fillStyle = SHADE.steelLight;
  ctx.beginPath(); ctx.moveTo(...S(-2.72, -1.6)); ctx.lineTo(...S(-2.35, -1.62)); ctx.lineTo(...S(-2.42, -1.2)); ctx.lineTo(...S(-2.74, -1.15)); ctx.closePath(); ctx.fill();
  ctx.fillStyle = rgba(PAL.ink, 0.35);
  ctx.fillRect(...S(-2.6, 0.3), 12.1 * r, 0.04 * r);
  ctx.restore();

  if (wheels) {
    wheel(ctx, { x, y, r, angle: rearAngle, spokes, highlight, opacity });
    wheel(ctx, { x: x + L * r, y, r, angle: frontAngle, spokes, highlight, opacity });
  }
  return { rear: [x, y], front: [x + L * r, y] };
}
