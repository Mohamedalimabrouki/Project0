/*
 * Scene 05 - "The rule". Opens the UNDERSTAND IT chapter (40.5 s).
 *
 * The engineers' layer: the trick of scene 4 becomes a law.
 *
 *   LEFT   a graph of "frequency seen on video" (f_a) against "real spoke
 *          frequency" (f). It is built step by step: axes, the true diagonal
 *          f_a = f, the green zone below the Nyquist limit, then the sawtooth
 *          f_a = f - 30 round(f / 30) drawn by a yellow marker that sweeps f
 *          from 0 to 66 Hz.
 *   RIGHT  a live wheel that turns at its REAL rate (f_r = f / 5 turns per
 *          second), with readouts. This video is itself a 30 pictures per
 *          second sampler, so the wheel on YOUR screen does exactly what the
 *          graph predicts. No motion blur, no tricks: the angle at frame n is
 *          the true angle at t = n / 30.
 *   BOTTOM the three equations, one after the other:
 *          f = N f_r,   f_a = f - f_s round(f / f_s),   f_s > 2 f_max.
 *
 * How the maths is wired (plain language):
 *   - SWEEP.f(t) is the spoke frequency f in Hz at time t. It is defined ONCE
 *               and used for everything: the marker, the readouts and the
 *               wheel. So they can never disagree.
 *   - alias(f)  is the frequency the video shows. The graph, the readouts and
 *               the check in the report all use this one function.
 *   - the wheel angle is the exact integral of f(t) / 5 (EP.angleTable).
 *
 * The scene is a pure function of t: nothing is remembered between frames.
 *
 * Key moments (seconds from the start of the scene):
 *   0.4   chapter label                1.0-4.0  axes, grid and titles build
 *   4.0   the true diagonal (blue)     6.7  wheel and badge appear, 7.0 first equation
 *   9.0   wheel starts to turn         13.4 green zone, 14.6 Nyquist line
 *   16.8  marker hits 15 Hz and falls  21.0 second equation, 21.7 frozen points
 *   22.3  frozen at 30 Hz              27.0 marker falls again at 45 Hz
 *   29.0  key equation appears         30.4 frozen at 60 Hz, 30.8 yellow box
 *   33.7  top of the sweep (66 Hz)     35.0-38.0 settles at 60 Hz (wheel still)
 *   35.4  theorem named, box and green zone breathe once
 * The four crossing times (16.8, 22.3, 27.0, 30.4 s) are computed from the
 * sweep, not typed, and drive the sound cues and the pulses on the graph.
 *
 * Named exports (alias, SWEEP, GRAPH, FS, N_SPOKES) are only for the numerical
 * check in the report; the film uses the default export.
 */

// ---------------------------------------------------------------- the physics
export const FS = 30;              // pictures per second of the video (Hz)
export const N_SPOKES = 5;         // identical spokes on the wheel
const NYQ = FS / 2;                // Nyquist limit, 15 Hz
const F_AXIS = 70;                 // graph x range: real spoke frequency 0..70 Hz
const FA_LIM = 15;                 // graph y range: frequency seen -15..+15 Hz
const DURATION = 40.5;

/** Frequency seen on the video: the alias closest to zero. In [-15, +15] Hz. */
export const alias = f => f - FS * Math.round(f / FS);

// ------------------------------------------------------------------ the sweep
/*
 * f(t): the real spoke frequency, rising smoothly from 0 to 66 Hz.
 * It is built from a velocity profile (Hz per second) that is eased between
 * a few key moments, then integrated. Slow passages near 30 Hz and 60 Hz give
 * the viewer time to see "backwards, frozen, forwards"; the fast part in
 * between is the "everything is disguised" stretch. After the top (66 Hz) it
 * settles back to 60 Hz, so the scene ends calmly on a wheel that seems still.
 */
export const SWEEP = (() => {
  const smooth = k => k * k * (3 - 2 * k);
  const VL = 2.516;                        // solved so that the top is exactly 66 Hz
  const V = [                              // [time s, speed Hz/s]
    [9.0, 0.0], [13.2, 2.3], [16.9, 3.3], [19.0, 3.4], [21.0, 2.1], [22.6, 1.3],
    [24.0, 1.12], [25.3, 1.4], [26.3, 8.0], [27.2, 10.8], [28.0, 6.5], [28.8, 2.3],
    [29.9, 1.35], [31.0, 1.4], [32.0, VL], [32.8, VL], [33.7, 0.0],
  ];
  const T_TOP = V[V.length - 1][0];
  const vel = t => {
    if (t <= V[0][0] || t >= T_TOP) return 0;
    let i = 0;
    while (V[i + 1][0] < t) i++;
    const [ta, va] = V[i], [tb, vb] = V[i + 1];
    return va + (vb - va) * smooth((t - ta) / (tb - ta));
  };
  const DT = 1 / 2400;
  const n = Math.ceil(T_TOP / DT) + 1;
  const F = new Float64Array(n);
  for (let i = 1; i < n; i++) {
    const ta = (i - 1) * DT, tb = i * DT;
    F[i] = F[i - 1] + (DT / 6) * (vel(ta) + 4 * vel((ta + tb) / 2) + vel(tb));
  }
  /** highest f reached so far (rises to the top, then stays there) */
  const up = t => {
    if (t <= 0) return 0;
    if (t >= T_TOP) return F[n - 1];
    const x = t / DT, i = Math.floor(x);
    return F[i] + (F[i + 1] - F[i]) * (x - i);
  };
  const SETTLE = { t0: 35.0, t1: 38.0, to: 60 };   // calm ending: back to the frozen speed
  const drop = F[n - 1] - SETTLE.to;
  const f = t => up(t) - drop * smooth(Math.min(1, Math.max(0, (t - SETTLE.t0) / (SETTLE.t1 - SETTLE.t0))));
  /** first time the sweep reaches frequency x (on the way up) */
  const crossTime = x => {
    let a = 0, b = T_TOP;
    for (let k = 0; k < 60; k++) { const m = (a + b) / 2; if (up(m) < x) a = m; else b = m; }
    return (a + b) / 2;
  };
  return { f, up, crossTime, T_TOP, fTop: F[n - 1] };
})();

const T15 = SWEEP.crossTime(15), T30 = SWEEP.crossTime(30);
const T45 = SWEEP.crossTime(45), T60 = SWEEP.crossTime(60);

// ---------------------------------------------------------------- the timing
const TM = {
  eyebrow: [0.4, 4.5],
  yAxis: [1.0, 1.9], xAxis: [1.2, 2.3], zero: [1.7, 2.7], grid: [2.0, 3.0],
  yTicks: 2.4, xTicks: 2.1, titles: [3.1, 3.9], sides: 3.5,
  truth: [4.0, 5.7], truthLabel: 5.5,
  wheelIn: 6.7, badgeIn: 6.9, readoutIn: 7.7, markerIn: 8.6,
  eq: [7.0, 21.0, 29.0], note1: 7.8,
  band: [13.4, 14.5], bandLabel: 14.1, nyq: [14.6, 15.4], nyqLabel: 15.3,
  aliasLabel: T15 + 0.9, frozen: 21.7,
  box: [30.8, 31.9], theorem: 35.4,
  fall: 0.42,
};

// ------------------------------------------------------------------ geometry
const G = { x0: 226, x1: 1122, top: 316, bot: 674 };
G.sx = (G.x1 - G.x0) / F_AXIS;            // pixels per Hz, across
G.sy = (G.bot - G.top) / (2 * FA_LIM);    // pixels per Hz, up
const gx = f => G.x0 + f * G.sx;
const gy = fa => G.bot - (fa + FA_LIM) * G.sy;

export const GRAPH = { G, gx, gy };       // for the numerical check in the report

const COL_X = 1507;                       // centre of the right-hand column
const WHEEL = { x: COL_X, y: 487, r: 145 };
const RO_Y = 686;                         // baseline of the readout row
const WORD_Y = 756;                       // baseline of the word under the readouts
const EQ_Y = 856;                         // baseline of the three equations
const EQ_SIZE = 60;

const EQS = [
  'f = N\\,f_r',
  'f_a = f - f_s\\,\\mathrm{round}\\!\\left(\\frac{f}{f_s}\\right)',
  'f_s > 2\\,f_{\\max}',
];
const STEEL = '#8C96A0', YELLOW = '#F0E442';

const CAPTIONS = [
  { key: 's05.c1', in: 0.8, out: 6.4 },
  { key: 's05.c2', in: 6.8, out: 12.8 },
  { key: 's05.c3', in: 13.2, out: 20.6 },
  { key: 's05.c4', in: 21.0, out: 28.4 },
  { key: 's05.c5', in: 28.8, out: 34.8 },
  { key: 's05.c6', in: 35.2, out: 39.9 },
];

/**
 * Caption line breaks. The engine wraps a caption greedily, which can leave a
 * lone word on the second line ("... pass by f / times per second."). Here each
 * caption is measured once (in the language being rendered) and given the
 * narrowest line width that reproduces the best two-line split: a sentence end
 * if that is reasonably balanced, otherwise the most even split (never ending
 * a line on a little word such as "as" or "the"). A caption that
 * fits on one line keeps the engine's default. Works for any wording, so a
 * changed translation or English line is handled without touching this file.
 * (50 px, weight 600 and 1560 px are the engine's default caption band.)
 */
function balanceCaptions(EP) {
  if (typeof document === 'undefined') return;                    // only in the browser renderer
  const ctx = document.createElement('canvas').getContext('2d');
  const SIZE = 50, WEIGHT = 600, ONE_LINE = 1560;
  const width = str => EP.measure(ctx, str, { size: SIZE, weight: WEIGHT }).w;
  for (const c of CAPTIONS) {
    delete c.band;
    const str = EP.T(c.key);
    if (width(str) <= ONE_LINE) continue;
    const words = str.split(' ');                                // no-break spaces stay glued, as in the engine
    let best = null;
    for (let k = 1; k < words.length; k++) {
      const l1 = words.slice(0, k).join(' '), l2 = words.slice(k).join(' ');
      const w1 = width(l1), w2 = width(l2), mw = Math.max(w1, w2) + 10;
      if (width(l1 + ' ' + words[k]) <= mw) continue;            // the engine would pull the next word up: split not reachable
      const sentenceEnd = /[.:;!?\u2026\u061F\u061B]$/.test(words[k - 1]);
      const shortWord = /^\p{L}{1,3}$/u.test(words[k - 1].replace(/[^\p{L}\p{N}]/gu, ''));   // "as", "the", "de", "في": a poor place to end a line
      const cost = Math.max(w1, w2) + (sentenceEnd ? 0 : 300) + (shortWord && !sentenceEnd ? 200 : 0);
      if (!best || cost < best.cost) best = { cost, mw };
    }
    if (best && best.mw < ONE_LINE) c.band = { maxWidth: Math.ceil(best.mw) };
  }
}

let spin = null;    // wheel angle table, made once in setup()

// ------------------------------------------------------------------- helpers
/** where the marker is at time t; it falls along the dotted line at each jump */
function markerAt(t) {
  const f = SWEEP.f(t);
  let fa = alias(f);
  for (const [tj] of [[T15], [T45]]) {
    const k = (t - tj) / TM.fall;
    if (k > 0 && k < 1) {
      const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      fa = FA_LIM + (fa - FA_LIM) * e;
    }
  }
  return { f, fa };
}

/**
 * A text label and a TeX symbol on one baseline. order 'text-math' reads
 * "Real spoke frequency f (Hz)", 'math-text' reads "N = 5 spokes". In Arabic
 * (right to left) the order mirrors, while the symbol itself stays left to right.
 */
function labelMath(ctx, EP, str, tex, o) {
  const { x, y, size = 28, weight = 600, color = STEEL, align = 'center', opacity = 1, maxWidth = 0, mathScale = 1.1, gap = 0.34, order = 'text-math' } = o;
  const tb = EP.text(ctx, str, { size, weight, maxWidth, maxLines: 1, shrink: !!maxWidth, draw: false });
  const msz = tb.size * mathScale;
  const mb = EP.math(ctx, tex, { size: msz, color, draw: false });
  const g = tb.size * gap;
  const total = tb.w + g + mb.w;
  const left = align === 'left' ? x : align === 'right' ? x - total : x - total / 2;
  const mathLeft = (order === 'text-math') === EP.isRTL();   // math on the left of the text?
  const tx = mathLeft ? left + mb.w + g : left;
  const mx = mathLeft ? left : left + tb.w + g;
  EP.text(ctx, str, { x: tx, y, size: tb.size, weight, color, opacity, align: 'left' });
  EP.math(ctx, tex, { x: mx, y, size: msz, color, opacity, align: 'left', anchor: 'baseline' });
  return { x: left, w: total };
}

/**
 * Reveal from left to right with a soft edge: the picture is drawn in narrow
 * slices whose opacity falls off towards the moving front (no hard cut).
 * draw(k) draws the whole thing at opacity factor k. progress 0..1.
 */
function softReveal(ctx, x0, x1, progress, draw) {
  const FEATHER = 90, N = 15;
  const front = x0 - FEATHER + (x1 - x0 + FEATHER) * progress;   // fully hidden at 0, fully shown at 1
  const cut = (lo, hi, k) => {
    lo = Math.max(Math.round(lo), Math.round(x0)); hi = Math.min(Math.round(hi), Math.round(x1) + 2);
    if (hi <= lo || k <= 0) return;
    ctx.save();
    ctx.beginPath(); ctx.rect(lo, -2000, hi - lo, 4000); ctx.clip();
    draw(k);
    ctx.restore();
  };
  cut(x0, front, 1);
  for (let j = 0; j < N; j++) cut(front + (FEATHER * j) / N, front + (FEATHER * (j + 1)) / N, 1 - (j + 0.5) / N);
}

/** a dotted line (round dots); color may be a gradient */
function dotted(ctx, x1, y1, x2, y2, color, width = 3, gap = 8) {
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  ctx.lineCap = 'round';
  ctx.setLineDash([0.01, gap]);
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  ctx.restore();
}

function ring(ctx, x, y, r, color, width, alpha = 1, fill = null) {
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  ctx.lineWidth = width;
  ctx.strokeStyle = color;
  ctx.stroke();
  ctx.restore();
}

// -------------------------------------------------------------------- graph
function drawGraph(ctx, t, EP) {
  const { PAL, prog, ease, rgba } = EP;
  const { x0, x1, top, bot } = G;
  const xs = [0, 15, 30, 45, 60];
  const zeroY = gy(0);
  const halo = 9;   // soft ink shadow so labels stay legible over faint lines

  // when the caption names the theorem, the green zone and its wall breathe once
  // (the theorem is exactly the promise of that zone); smooth, small, no flash
  const breathe = Math.sin(Math.PI * EP.clamp((t - TM.theorem) / 1.2));

  // green zone: the video tells the truth, 0 <= f < 15 Hz
  const pBand = prog(t, TM.band[0], TM.band[1], ease.outCubic);
  if (pBand > 0) {
    ctx.fillStyle = rgba(PAL.balance, 0.12 + 0.08 * breathe);
    ctx.fillRect(x0, top, (gx(NYQ) - x0) * pBand, bot - top);
  }

  // grid (paper, about 6 %), ceiling of the chart window, zero line
  const aGrid = prog(t, TM.grid[0], TM.grid[1], ease.outCubic);
  if (aGrid > 0) {
    ctx.save();
    ctx.strokeStyle = rgba(PAL.paper, 0.06 * aGrid);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (const f of xs.slice(1)) { ctx.moveTo(gx(f), top); ctx.lineTo(gx(f), bot); }
    ctx.moveTo(x1, top); ctx.lineTo(x1, bot);
    ctx.stroke();
    ctx.restore();
  }
  const pCeil = prog(t, TM.zero[0], TM.zero[1] + 0.2, ease.outCubic);
  if (pCeil > 0) {
    ctx.save();
    ctx.strokeStyle = rgba(PAL.paper, 0.16);
    ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(x0, top); ctx.lineTo(x0 + (x1 - x0) * pCeil, top); ctx.stroke();
    ctx.restore();
  }
  const pZero = prog(t, TM.zero[0], TM.zero[1], ease.outCubic);
  if (pZero > 0) {
    ctx.save();
    ctx.strokeStyle = rgba(PAL.paper, 0.5);
    ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.moveTo(x0, zeroY); ctx.lineTo(x0 + (x1 - x0) * pZero, zeroY); ctx.stroke();
    ctx.restore();
  }

  // axes (steel, 2 px) draw in
  const pY = prog(t, TM.yAxis[0], TM.yAxis[1], ease.outCubic);
  const pX = prog(t, TM.xAxis[0], TM.xAxis[1], ease.outCubic);
  ctx.save();
  ctx.strokeStyle = PAL.steel;
  ctx.lineWidth = 2;
  ctx.lineCap = 'butt';
  if (pY > 0) { ctx.beginPath(); ctx.moveTo(x0, bot + 1); ctx.lineTo(x0, bot - (bot - top) * pY); ctx.stroke(); }
  if (pX > 0) { ctx.beginPath(); ctx.moveTo(x0 - 1, bot); ctx.lineTo(x0 + (x1 - x0) * pX, bot); ctx.stroke(); }
  ctx.restore();

  // ticks and tick labels (the "15" under the Nyquist line turns yellow with it)
  xs.forEach((f, i) => {
    const a = prog(t, TM.xTicks + i * 0.09, TM.xTicks + i * 0.09 + 0.5, ease.outCubic);
    if (a <= 0) return;
    const lit = f === NYQ ? prog(t, TM.nyq[1] - 0.3, TM.nyq[1] + 0.4, ease.outCubic) : 0;
    ctx.save();
    ctx.globalAlpha *= a;
    ctx.strokeStyle = EP.mix(PAL.steel, PAL.highlight, lit); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(gx(f), bot); ctx.lineTo(gx(f), bot + 9); ctx.stroke();
    ctx.restore();
    EP.text(ctx, EP.num(f), { x: gx(f), y: bot + 42 - 6 * (1 - a), align: 'center', size: 28, weight: lit > 0.5 ? 700 : 500, color: EP.mix(PAL.steel, PAL.highlight, lit), opacity: a, latin: true });
  });
  [-15, 0, 15].forEach((fa, i) => {
    const a = prog(t, TM.yTicks + i * 0.09, TM.yTicks + i * 0.09 + 0.5, ease.outCubic);
    if (a <= 0) return;
    ctx.save();
    ctx.globalAlpha *= a;
    ctx.strokeStyle = PAL.steel; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x0 - 9, gy(fa)); ctx.lineTo(x0, gy(fa)); ctx.stroke();
    ctx.restore();
    EP.text(ctx, EP.num(fa), { x: x0 - 24 - 6 * (1 - a), y: gy(fa) + 10, align: 'right', size: 28, weight: 500, color: PAL.steel, opacity: a, latin: true });
  });

  // axis titles: text in the current language + the symbol as TeX
  const aT = prog(t, TM.titles[0], TM.titles[1], ease.outCubic);
  if (aT > 0) {
    labelMath(ctx, EP, EP.T('s05.axis_x'), 'f\\,(\\mathrm{Hz})', { x: (x0 + x1) / 2, y: bot + 84 + 6 * (1 - aT), align: 'center', size: 28, weight: 600, color: PAL.steel, opacity: aT, maxWidth: 560 });
    ctx.save();
    ctx.translate(132 - 6 * (1 - aT), (top + bot) / 2);
    ctx.rotate(-Math.PI / 2);
    labelMath(ctx, EP, EP.T('s05.axis_y'), 'f_a\\,(\\mathrm{Hz})', { x: 0, y: 0, align: 'center', size: 28, weight: 600, color: PAL.steel, opacity: aT, maxWidth: 320 });
    ctx.restore();
  }

  // Nyquist line (yellow) at f = f_s / 2
  const pN = prog(t, TM.nyq[0], TM.nyq[1], ease.outCubic);
  if (pN > 0) {
    ctx.save();
    ctx.strokeStyle = rgba(PAL.highlight, 0.92);
    ctx.lineWidth = 2.5 + 1.5 * breathe;
    ctx.beginPath(); ctx.moveTo(gx(NYQ), top); ctx.lineTo(gx(NYQ), top + (bot - top) * pN); ctx.stroke();
    ctx.restore();
  }

  // the sawtooth: what the video shows (bright paper, thick), drawn up to the marker
  const fDrawn = t >= TM.markerIn ? SWEEP.up(t) : 0;
  if (fDrawn > 0) {
    ctx.save();
    ctx.strokeStyle = PAL.paper;
    ctx.lineWidth = 8;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    for (let j = 0; j < 3; j++) {
      const a = j === 0 ? 0 : NYQ + FS * (j - 1), b = NYQ + FS * j;
      if (fDrawn <= a) break;
      const e = Math.min(fDrawn, b);
      ctx.beginPath();
      ctx.moveTo(gx(a), gy(a - FS * j));
      ctx.lineTo(gx(e), gy(e - FS * j));
      ctx.stroke();
    }
    ctx.restore();
  }

  // the truth: f_a = f, solid blue. Leaves the chart at the top and fades out.
  const pT = prog(t, TM.truth[0], TM.truth[1], ease.inOutCubic);
  if (pT > 0) {
    const x15 = gx(NYQ), stubDx = 52, stubDy = stubDx * G.sy / G.sx;
    const L1 = Math.hypot(gx(NYQ) - gx(0), gy(NYQ) - gy(0)), L2 = Math.hypot(stubDx, stubDy);
    const drawn = pT * (L1 + L2);
    ctx.save();
    ctx.strokeStyle = PAL.motion;
    ctx.lineWidth = 4.5;
    ctx.lineCap = 'round';
    const l1 = Math.min(drawn, L1);
    const ux = (gx(NYQ) - gx(0)) / L1, uy = (gy(NYQ) - gy(0)) / L1;
    ctx.beginPath(); ctx.moveTo(gx(0), gy(0)); ctx.lineTo(gx(0) + ux * l1, gy(0) + uy * l1); ctx.stroke();
    if (drawn > L1) {
      const gr = ctx.createLinearGradient(x15, top, x15 + stubDx, top - stubDy);
      gr.addColorStop(0, rgba(PAL.motion, 0.9));
      gr.addColorStop(1, rgba(PAL.motion, 0));
      ctx.strokeStyle = gr;
      ctx.lineCap = 'butt';
      ctx.setLineDash([drawn - L1, 9999]);
      ctx.beginPath(); ctx.moveTo(x15, top); ctx.lineTo(x15 + stubDx, top - stubDy); ctx.stroke();
    }
    ctx.restore();
  }

  // the jumps at 15 and 45 Hz: thin dotted vertical lines, never a solid line
  for (const [fj, tj] of [[15, T15], [45, T45]]) {
    const p = prog(t, tj, tj + TM.fall, ease.inOutCubic);
    if (p > 0) dotted(ctx, gx(fj), gy(FA_LIM), gx(fj), gy(FA_LIM) + (gy(-FA_LIM) - gy(FA_LIM)) * p, rgba(PAL.paper, 0.85), 3, 8);
    const aTop = prog(t, tj - 0.05, tj + 0.2, ease.outCubic), aBot = prog(t, tj + TM.fall, tj + TM.fall + 0.25, ease.outCubic);
    if (aTop > 0) ring(ctx, gx(fj), gy(FA_LIM), 7.5, PAL.paper, 2.5, aTop, PAL.ink);
    if (aBot > 0) ring(ctx, gx(fj), gy(-FA_LIM), 7.5, PAL.paper, 2.5, aBot, PAL.ink);
  }

  // pointers on both axes: read f and f_a off the axes (no lines across the chart)
  const kM = prog(t, TM.markerIn, TM.markerIn + 0.5, ease.outBack);
  const m = markerAt(t);
  const mx = gx(m.f), my = gy(m.fa);
  if (kM > 0) {
    ctx.save();
    ctx.globalAlpha *= Math.min(1, kM);
    ctx.fillStyle = PAL.highlight;
    ctx.beginPath(); ctx.moveTo(mx, bot + 3); ctx.lineTo(mx - 7, bot + 15); ctx.lineTo(mx + 7, bot + 15); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.moveTo(x0 - 3, my); ctx.lineTo(x0 - 14, my - 7); ctx.lineTo(x0 - 14, my + 7); ctx.closePath(); ctx.fill();
    ctx.restore();
  }

  // frozen points at f = 30 and 60 Hz (f_a = 0)
  [30, 60].forEach((f, i) => {
    const k = prog(t, TM.frozen + i * 0.25, TM.frozen + i * 0.25 + 0.5, ease.outBack);
    const a = prog(t, TM.frozen + i * 0.25, TM.frozen + i * 0.25 + 0.4, ease.outCubic);
    if (a <= 0) return;
    const px = gx(f), py = gy(0);
    ctx.save();
    ctx.globalAlpha *= a;
    ctx.beginPath(); ctx.arc(px, py, 9.5 * k, 0, Math.PI * 2);
    ctx.fillStyle = PAL.paper; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = PAL.ink; ctx.stroke();
    ctx.restore();
    EP.text(ctx, EP.T('s05.frozen'), { x: px + 16, y: py + 44 - 8 * (1 - a), align: 'left', size: 30, weight: 700, color: PAL.paper, opacity: a, maxWidth: 122, shrink: true, maxLines: 1, shadow: halo });
  });

  // labels on the curves and zones
  const aTruth = prog(t, TM.truthLabel, TM.truthLabel + 0.6, ease.outCubic);
  if (aTruth > 0) EP.text(ctx, EP.T('s05.truth'), { x: x0 + 20, y: gy(12.6) - 6 * (1 - aTruth), align: 'left', size: 32, weight: 700, color: EP.mix(PAL.motion, PAL.paper, 0.3), opacity: aTruth, maxWidth: 150, shrink: true, maxLines: 1, shadow: halo });
  const aAlias = prog(t, TM.aliasLabel, TM.aliasLabel + 0.6, ease.outCubic);
  if (aAlias > 0) {
    // set along the alias line, just above it
    const fA = 23.4, th = Math.atan2(-G.sy, G.sx);
    ctx.save();
    ctx.translate(gx(fA), gy(fA - FS));
    ctx.rotate(th);
    EP.text(ctx, EP.T('s05.alias'), { x: 0, y: -25 - 6 * (1 - aAlias), align: 'center', size: 32, weight: 700, color: PAL.paper, opacity: aAlias, maxWidth: 140, shrink: true, maxLines: 1, shadow: halo });
    ctx.restore();
  }
  const aSafe = prog(t, TM.bandLabel, TM.bandLabel + 0.7, ease.outCubic);
  if (aSafe > 0) EP.text(ctx, EP.T('s05.safe'), { x: (x0 + gx(NYQ)) / 2 - 2, y: gy(-5.4) - 6 * (1 - aSafe), align: 'center', size: 26, weight: 600, color: PAL.balance, opacity: aSafe, maxWidth: 158, shrink: true, maxLines: 3, shadow: halo });
  const aNyq = prog(t, TM.nyqLabel, TM.nyqLabel + 0.7, ease.outCubic);
  if (aNyq > 0) {
    const lx = gx(NYQ) + 26, ly = gy(FA_LIM) + 40 - 6 * (1 - aNyq);
    EP.text(ctx, EP.T('s05.nyquist'), { x: lx, y: ly, align: 'left', size: 30, weight: 700, color: PAL.highlight, opacity: aNyq, maxWidth: 260, shrink: true, maxLines: 1, shadow: halo });
    EP.math(ctx, '\\frac{f_s}{2} = 15\\ \\mathrm{Hz}', { x: lx, y: ly + 66, size: 42, color: PAL.highlight, align: 'left', anchor: 'baseline', opacity: aNyq });
  }
  // which half of the chart is which (positive = seems to turn forwards)
  const aSide = prog(t, TM.sides, TM.sides + 0.7, ease.outCubic);
  if (aSide > 0) {
    EP.text(ctx, EP.T('s05.forwards'), { x: x1 - 14, y: top + 34, align: 'right', size: 26, weight: 600, color: PAL.steel, opacity: aSide, maxWidth: 190, shrink: true, maxLines: 1 });
    EP.text(ctx, EP.T('s05.backwards'), { x: x1 - 14, y: bot - 16, align: 'right', size: 26, weight: 600, color: PAL.steel, opacity: aSide, maxWidth: 190, shrink: true, maxLines: 1, shadow: halo });
  }

  // ---------------------------------------------------------------- marker
  if (kM > 0) {
    for (const [te, fx, fy] of [[T15, 15, FA_LIM], [T30, 30, 0], [T45, 45, FA_LIM], [T60, 60, 0]]) {
      const k = (t - te) / 0.75;
      if (k > 0 && k < 1) ring(ctx, gx(fx), gy(fy), 10 + 32 * ease.outCubic(k), PAL.highlight, 3.5 - 2.5 * k, Math.pow(1 - k, 1.4) * 0.9);
    }
    ring(ctx, mx, my, 9.5 * kM + 7, PAL.highlight, 2, 0.35 * kM);
    ctx.save();
    ctx.beginPath(); ctx.arc(mx, my, 9.5 * kM, 0, Math.PI * 2);
    ctx.fillStyle = PAL.highlight; ctx.fill();
    ctx.lineWidth = 3; ctx.strokeStyle = PAL.ink; ctx.stroke();
    ctx.restore();
  }
}

// ------------------------------------------------------------- wheel column
/** small direction icon: an arc arrow, clockwise (dir > 0) or counter-clockwise; a dot when still */
function dirIcon(ctx, EP, x, y, dir, dashed, alpha, still = 0) {
  if (alpha > 0) {
    const r = 15, a0 = dir > 0 ? -2.3 : 2.3, a1 = dir > 0 ? 1.55 : -1.55;
    EP.arcArrow(ctx, x, y, r, a0, a1, { kind: 'motion', width: 4, headSize: 12, alpha, dash: dashed ? [5, 5] : false });
  }
  if (still > 0) {
    ctx.save();
    ctx.globalAlpha *= still;
    ctx.fillStyle = EP.PAL.motion;
    ctx.beginPath(); ctx.arc(x, y, 4.5, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }
}

function drawWheelColumn(ctx, t, EP) {
  const { PAL, prog, ease, clamp } = EP;
  const cx = COL_X;
  const kW = prog(t, TM.wheelIn, TM.wheelIn + 0.9, ease.outCubic);

  // honesty badge: this wheel is drawn at its real rate
  const aB = prog(t, TM.badgeIn, TM.badgeIn + 0.6, ease.outCubic);
  if (aB > 0) {
    const s = EP.T('badge.real');
    let size = 22;
    const w = EP.measure(ctx, s, { size, weight: 700, tracking: 0.12, caps: true }).w + size * 1.5;
    if (w > 624) size = Math.floor(size * 624 / w * 10) / 10;
    EP.badge(ctx, s, { x: cx, y: 302 + 6 * (1 - aB), align: 'center', size, opacity: aB });
  }

  // the wheel, at its real turning rate (angle = exact integral of f(t) / N)
  if (kW > 0) {
    ctx.save();
    ctx.translate(WHEEL.x, WHEEL.y);
    ctx.scale(0.94 + 0.06 * kW, 0.94 + 0.06 * kW);
    EP.wheel(ctx, { x: 0, y: 0, r: WHEEL.r, angle: spin(t), opacity: kW });
    ctx.restore();
  }

  // readouts: real (solid blue icon) and seen (dashed blue icon), side by side
  const aR = prog(t, TM.readoutIn, TM.readoutIn + 0.7, ease.outCubic);
  if (aR <= 0) return;
  const f = SWEEP.f(t), fa = alias(f);
  const nSize = 38, sSize = 42, uSize = 28;
  const symF = EP.math(ctx, 'f =', { size: sSize, draw: false }), symFa = EP.math(ctx, 'f_a =', { size: sSize, draw: false });
  const numFw = EP.textTab(ctx, '88.8', { size: nSize, weight: 600, opacity: 0 }).w;
  const numFaw = EP.textTab(ctx, '\u221288.8', { size: nSize, weight: 600, opacity: 0 }).w;
  const unitW = EP.text(ctx, 'Hz', { size: uSize, weight: 500, latin: true, draw: false }).w;
  const iconW = 34, gI = 10, gS = 14, gU = 8, gapBlocks = 44;
  const wF = iconW + gI + symF.w + gS + numFw + gU + unitW;
  const wFa = iconW + gI + symFa.w + gS + numFaw + gU + unitW;
  const left = cx - (wF + gapBlocks + wFa) / 2;
  const blocks = [
    { x: left, sym: 'f =', symW: symF.w, text: EP.num(f, 1), real: true },
    { x: left + wF + gapBlocks, sym: 'f_a =', symW: symFa.w, text: (fa > 0.049 ? '+' : '') + EP.num(fa, 1), real: false },
  ];
  const moving = clamp((f - 0.15) / 0.5);
  const still = moving * (1 - prog(Math.abs(fa), 0.25, 0.6, ease.smooth));
  ctx.save();
  ctx.globalAlpha *= aR;
  for (const b of blocks) {
    const xSym = b.x + iconW + gI;
    EP.math(ctx, b.sym, { x: xSym, y: RO_Y, size: sSize, align: 'left', anchor: 'baseline' });
    const xNum = xSym + b.symW + gS;
    const nw = EP.textTab(ctx, b.text, { x: xNum, y: RO_Y, size: nSize, weight: 600, align: 'left', color: PAL.paper }).w;
    EP.text(ctx, 'Hz', { x: xNum + nw + gU, y: RO_Y, size: uSize, weight: 500, color: PAL.steel, latin: true, align: 'left' });
    if (b.real) dirIcon(ctx, EP, b.x + iconW / 2, RO_Y - 12, 1, false, moving);
    else dirIcon(ctx, EP, b.x + iconW / 2, RO_Y - 12, fa >= 0 ? 1 : -1, true, moving * (1 - still), moving * still);
  }
  ctx.restore();

  // the word: what the wheel seems to do (green while the video tells the truth)
  const frozen = Math.abs(Math.round(fa * 10) / 10) < 0.5;   // same rounding as the number on screen
  const key = frozen ? 's05.frozen' : fa > 0 ? 's05.forwards' : 's05.backwards';
  const aW = prog(f, 0.9, 1.6, ease.smooth) * aR;
  const green = !frozen && fa > 0 && f < NYQ;
  EP.text(ctx, EP.T(key), { x: cx, y: WORD_Y, align: 'center', size: 48, weight: 800, color: green ? PAL.balance : PAL.paper, opacity: aW, maxWidth: 420, shrink: true, maxLines: 1 });
}

// ---------------------------------------------------------------- equations
function drawEquations(ctx, t, EP) {
  const { PAL, prog, ease, rgba } = EP;
  const boxes = EQS.map(q => EP.math(ctx, q, { size: EQ_SIZE, draw: false, align: 'left', anchor: 'baseline' }));
  const w3 = boxes[2].w;
  const left1 = G.x0, left3 = COL_X - w3 / 2;
  const gapE = (left3 - (left1 + boxes[0].w) - boxes[1].w) / 2;
  const xs = [left1, left1 + boxes[0].w + gapE, left3];

  EQS.forEach((q, i) => {
    const t0 = TM.eq[i];
    const a = prog(t, t0, t0 + 0.5, ease.outCubic);
    if (a <= 0) return;
    const wipe = prog(t, t0, t0 + 0.95, ease.outCubic);
    const rise = 14 * (1 - ease.outCubic(prog(t, t0, t0 + 0.7, ease.linear)));
    const drawEq = k => EP.math(ctx, q, { x: xs[i], y: EQ_Y + rise, size: EQ_SIZE, align: 'left', anchor: 'baseline', opacity: a * k });
    if (wipe >= 1) drawEq(1);
    else softReveal(ctx, xs[i] - 16, xs[i] + boxes[i].w + 16, wipe, drawEq);
  });

  // small note under the first equation: N = 5 spokes
  const aN = prog(t, TM.note1, TM.note1 + 0.6, ease.outCubic);
  if (aN > 0) labelMath(ctx, EP, EP.T('s05.spokes'), 'N = 5', { x: xs[0], y: EQ_Y + 58, align: 'left', size: 28, weight: 500, color: STEEL, opacity: aN, mathScale: 1.15, gap: 0.5, order: 'math-text' });

  // the key result: boxed in yellow; it pulses once when the caption names the theorem
  const padX = 30, padY = 16;
  const asc = EQ_SIZE * 0.78, desc = EQ_SIZE * 0.34;
  const bx = xs[2] - padX, bw = boxes[2].w + 2 * padX;
  const by = EQ_Y - asc - padY, bh = asc + desc + 2 * padY;
  const pBox = prog(t, TM.box[0], TM.box[1], ease.inOutCubic);
  if (pBox > 0) {
    const k = EP.clamp((t - TM.theorem) / 1.0);
    const pulse = Math.sin(Math.PI * k);          // 0 -> 1 -> 0, once
    ctx.save();
    EP.roundRect(ctx, bx, by, bw, bh, 12);
    ctx.fillStyle = rgba(PAL.highlight, (0.06 + 0.06 * pulse) * pBox);
    ctx.fill();
    const per = 2 * (bw + bh) - (8 - 2 * Math.PI) * 12;
    ctx.setLineDash([per * pBox, per]);
    ctx.lineWidth = 3 + 1.5 * pulse;
    ctx.strokeStyle = PAL.highlight;
    ctx.lineJoin = 'round';
    ctx.stroke();
    ctx.restore();
  }
  // the theorem's name, once the caption says it
  const aTh = prog(t, TM.theorem, TM.theorem + 0.8, ease.outCubic);
  if (aTh > 0) EP.text(ctx, EP.T('s05.theorem'), { x: COL_X, y: by + bh + 32 - 6 * (1 - aTh), align: 'center', size: 22, weight: 700, tracking: 0.14, caps: true, color: PAL.highlight, opacity: aTh, maxWidth: 620, shrink: true, maxLines: 1 });
}

// -------------------------------------------------------------------- scene
export default {
  duration: DURATION,
  captions: CAPTIONS,
  cues: [
    { t: TM.eq[0], sfx: 'pop' },
    { t: 13.2, sfx: 'whirr', dur: 20, rate: 6 },
    { t: T15, sfx: 'blip' },
    { t: TM.eq[1], sfx: 'pop' },
    { t: T30, sfx: 'blip' },
    { t: T45, sfx: 'blip' },
    { t: TM.eq[2], sfx: 'pop' },
    { t: TM.eq[2] + 0.08, sfx: 'hit', gain: -6 },
    { t: T60, sfx: 'blip' },
  ],
  math: [
    'f = N\\,f_r',
    'f_a = f - f_s\\,\\mathrm{round}\\!\\left(\\frac{f}{f_s}\\right)',
    'f_s > 2\\,f_{\\max}',
    { tex: 'f\\,(\\mathrm{Hz})', color: STEEL },
    { tex: 'f_a\\,(\\mathrm{Hz})', color: STEEL },
    { tex: '\\frac{f_s}{2} = 15\\ \\mathrm{Hz}', color: YELLOW },
    { tex: 'N = 5', color: STEEL },
    'f =',
    'f_a =',
  ],
  music: 'explain',

  setup(EP) {
    // exact wheel angle: the integral of the real turning rate f(t) / N
    spin = EP.angleTable(t => SWEEP.f(t) / N_SPOKES, 0, DURATION);
    balanceCaptions(EP);
  },

  render(ctx, t, EP, { W, H }) {
    EP.bg(ctx, W, H);
    const aE = EP.win(t, TM.eyebrow[0], TM.eyebrow[1], 0.5, 0.45);
    if (aE > 0) EP.eyebrow(ctx, EP.T('chapter.understand'), { x: W / 2, y: 86, align: 'center', opacity: aE, reveal: EP.prog(t, 0.4, 1.2, EP.ease.outCubic) });
    drawGraph(ctx, t, EP);
    drawWheelColumn(ctx, t, EP);
    drawEquations(ctx, t, EP);
  },
};
