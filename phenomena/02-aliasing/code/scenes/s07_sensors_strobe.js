/*
 * Scene 07 - Sensors and the strobe ("In the real world", part 2), 22.5 s.
 *
 *   Part 1   0.5 - 12.2 s   A motor with a vibration sensor. The sensor voltage is a 900 Hz
 *                           sine; the controller reads it 1000 times per second. The 21
 *                           samples of the first 20 ms trace a slow 100 Hz wave (the alias).
 *   Move     11.8 - 12.6 s  The sensor box lifts off the motor and becomes the first block.
 *   Part 2   12.3 - 16.95 s The fix: sensor -> anti-aliasing filter -> converter ->
 *                           controller, and the rule f_s > 2 f_max.
 *   Part 3   16.95 - 22.5 s Aliasing on purpose: a strobe 1 % slower than the blade passes
 *                           makes a fast 3-blade fan look almost still (simulated view).
 *
 * Every number on screen comes from the equations below. The maths is exported so it can
 * be checked in Node (see checkSamples() and strobeTable()).
 *
 * Colours keep their meaning: purple = electrical signal, paper = sample marks, steel =
 * objects, orange = light output, blue = motion (solid = real, dashed = what we see),
 * green = "it works" (the pass band of the filter), yellow = look here.
 *
 * Fades: each group (motor, plot, diagram, fan panels) is drawn as one flat layer with
 * EP.layer and faded as a whole. Captions: setup() balances their two lines (see
 * balanceCaptions), in every language.
 */

let EP = null; // the engine, handed over by the stage (the same object on every call)

const TAU = Math.PI * 2;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const lerp = (a, b, k) => a + (b - a) * k;

// =====================================================================================
// 1. THE NUMBERS
// =====================================================================================

// --- Part 1: a 900 Hz vibration read 1000 times per second ---------------------------
export const F_REAL = 900;            // Hz, the real vibration
export const F_S = 1000;              // Hz, samples per second (one every millisecond)
export const N_DOT = 21;              // t = k / 1000 s, k = 0 .. 20 (the plot shows 0 to 20 ms)
export const PHI = Math.PI / 10;      // phase of the vibration at t = 0 (18 degrees)

export const realSignal = t => Math.sin(TAU * F_REAL * t + PHI);
// At t = k / F_S:  sin(2 pi f t + phi) = sin(2 pi (f - F_S) t + phi), because 2 pi F_S t = 2 pi k.
// f - F_S = -100 Hz: a 100 Hz wave with its sign flipped (phase inverted).
export const aliasSignal = t => Math.sin(TAU * (F_REAL - F_S) * t + PHI);

// --- Part 3: a 3-blade fan under a strobe 1 % slower than the blade passes -----------
export const FAN = (() => {
  const blades = 3;
  const turns = 25;                                  // turns per second (1500 rpm)
  const passes = blades * turns;                     // 75 blade passes per second
  const strobe = 0.99 * passes;                      // 74.25 flashes per second
  // alias of the blade-passing frequency sampled at the flash rate (rule of scene 5)
  const aliasPasses = passes - strobe * Math.round(passes / strobe);   // +0.75 per second
  const apparent = aliasPasses / blades;             // +0.25 turns per second, forwards
  return { blades, turns, passes, strobe, aliasPasses, apparent, degPerFlash: 360 * apparent / strobe };
})();

/** Simulate the strobe flash by flash: apparent angle of the blades (mod 120 degrees). */
export function strobeTable(nFlash = 300) {
  const gap = 360 / FAN.blades;
  const rows = [];
  for (let k = 0; k <= nFlash; k++) {
    const t = k / FAN.strobe;                                   // instant of flash k
    const trueAngle = 360 * FAN.turns * t;                      // where the fan really is
    rows.push({ k, t, trueAngle, seen: ((trueAngle % gap) + gap) % gap });
  }
  // unwrap the seen angle (nearest-match rule): its slope is the apparent rotation
  let unwrapped = 0, prev = rows[0].seen;
  for (const r of rows) {
    let d = r.seen - prev;
    if (d < -gap / 2) d += gap;
    if (d > gap / 2) d -= gap;
    unwrapped += r.k === 0 ? 0 : d; prev = r.seen; r.unwrapped = unwrapped;
  }
  const last = rows[rows.length - 1];
  return { rows, degPerSecond: last.unwrapped / last.t, turnsPerSecond: last.unwrapped / last.t / 360 };
}

// =====================================================================================
// 2. GEOMETRY OF THE PLOT (pixels) AND PRECOMPUTED CURVES
// =====================================================================================
const PL = { x0: 452, ppm: 65, zy: 604, amp: 140, axy: 800, top: 446 };
PL.x1 = PL.x0 + 20 * PL.ppm;                          // 1300 px for 20 ms
const xOf = ms => PL.x0 + ms * PL.ppm;
const yOf = v => PL.zy - PL.amp * v;

const PPC = 90;                                       // points per cycle of the 900 Hz wave (>= 40 asked)
const N_REAL = 18 * PPC;                              // 1620 segments: a vertex at every millisecond
const REAL_X = new Float64Array(N_REAL + 1), REAL_Y = new Float64Array(N_REAL + 1);
for (let i = 0; i <= N_REAL; i++) {
  const ms = (20 * i) / N_REAL;
  REAL_X[i] = xOf(ms); REAL_Y[i] = yOf(realSignal(ms / 1000));
}
const N_ALIAS = 2 * 200;                              // 2 cycles of 100 Hz, 200 points per cycle
const ALIAS_X = new Float64Array(N_ALIAS + 1), ALIAS_Y = new Float64Array(N_ALIAS + 1);
for (let i = 0; i <= N_ALIAS; i++) {
  const ms = (20 * i) / N_ALIAS;
  ALIAS_X[i] = xOf(ms); ALIAS_Y[i] = yOf(aliasSignal(ms / 1000));
}
const DOTS = Array.from({ length: N_DOT }, (_, k) => ({ k, x: xOf(k), y: yOf(realSignal(k / F_S)) }));

/**
 * Numerical check of what is drawn: every dot (at its pixel position) must lie on both
 * polylines. The dot k sits on vertex 81 k of the real curve and vertex 20 k of the alias.
 */
export function checkSamples() {
  let eReal = 0, eAlias = 0, eWrong = 0, eValue = 0;
  for (const d of DOTS) {
    eReal = Math.max(eReal, Math.abs(d.y - REAL_Y[(N_REAL / 20) * d.k]), Math.abs(d.x - REAL_X[(N_REAL / 20) * d.k]));
    eAlias = Math.max(eAlias, Math.abs(d.y - ALIAS_Y[(N_ALIAS / 20) * d.k]), Math.abs(d.x - ALIAS_X[(N_ALIAS / 20) * d.k]));
    const t = d.k / F_S;
    eValue = Math.max(eValue, Math.abs(realSignal(t) - aliasSignal(t)));
    // control: the alias with the WRONG sign of frequency (+100 Hz) does not pass through the dots
    eWrong = Math.max(eWrong, Math.abs(realSignal(t) - Math.sin(TAU * (F_S - F_REAL) * t + PHI)));
  }
  return { dots: N_DOT, pointsPerCycle: PPC, maxErrPxReal: eReal, maxErrPxAlias: eAlias, maxErrValue: eValue, maxErrValueWrongSign: eWrong };
}

// =====================================================================================
// 3. TIMELINE (seconds from the start of the scene)
// =====================================================================================
const K = {
  // part 1
  motor: 0.5,                 // motor + sensor rise in (0.8 s)
  wire: [1.1, 2.0],           // purple wire grows from the sensor to the plot
  axis: [1.45, 2.4],          // axes and ms ticks
  realLabel: 2.45,
  real: [2.5, 4.6],           // the 900 Hz trace draws left to right
  ticks: 5.1, tickStep: 0.03, // paper sample ticks along the axis
  samplesLabel: 5.2,
  dots: 6.6, dotStep: 0.09,   // 21 dots, one after another (last one at 8.4 s)
  aliasLabel: 8.7,
  alias: [8.75, 10.55],       // the dashed 100 Hz wave draws through the dots
  dim: [10.75, 11.4],         // the real wave steps back: the controller sees only the dots
  p1Out: [11.72, 12.22],
  // part 1 -> 2: the sensor becomes the first block
  morph: [11.8, 12.6],
  // part 2
  blocks: [12.3, 13.0, 13.75, 14.5],
  equation: [15.0, 15.7],
  p2Out: [16.5, 16.95],
  // part 3
  fansIn: 16.95,              // the fans appear (blurred, as the eye sees them in normal light)
  numL: 18.0,
  strobeOn: 18.65,            // click: the strobe lamp switches on
  freeze: [18.9, 19.6],       // the blur resolves into crisp, slowly turning blades
  numR: 19.85,
};
const dotTime = k => K.dots + k * K.dotStep;
const CAPTIONS = [
  { key: 's07.c1', in: 0.8, out: 5.8 },
  { key: 's07.c2', in: 6.2, out: 11.6 },
  { key: 's07.c3', in: 12.0, out: 16.8 },
  { key: 's07.c4', in: 17.2, out: 21.9 },
];

// =====================================================================================
// 4. SMALL DRAWING HELPERS
// =====================================================================================
const P = (t, a, b, e) => EP.prog(t, a, b, e || EP.ease.outCubic);
/** Same as P but exactly 0 before the start (outBack(0) is not exactly 0 in floating point). */
const Pz = (t, a, b, e) => (t <= a ? 0 : P(t, a, b, e));

/** Polyline through (X[i], Y[i]) from the start to the fraction frac. Returns the tip. */
function tracePath(ctx, X, Y, frac) {
  const n = X.length - 1;
  const f = clamp(frac) * n, i = Math.floor(f);
  ctx.beginPath();
  ctx.moveTo(X[0], Y[0]);
  for (let k = 1; k <= Math.min(i, n); k++) ctx.lineTo(X[k], Y[k]);
  let tx = X[Math.min(i, n)], ty = Y[Math.min(i, n)];
  if (i < n) {
    const r = f - i;
    tx = X[i] + (X[i + 1] - X[i]) * r; ty = Y[i] + (Y[i + 1] - Y[i]) * r;
    ctx.lineTo(tx, ty);
  }
  return [tx, ty];
}

function vGrad(ctx, y0, y1) {
  const { PAL, SHADE } = EP;
  const g = ctx.createLinearGradient(0, y0, 0, y1);
  g.addColorStop(0, SHADE.steelMid);
  g.addColorStop(0.2, SHADE.steelLight);
  g.addColorStop(0.52, PAL.steel);
  g.addColorStop(1, SHADE.steelDark);
  return g;
}

/**
 * Captions in the engine wrap greedily, which can leave a widow ("... a slow 100 / Hz wave.").
 * For each caption that needs two lines, find the narrowest width that still gives two lines:
 * the two lines come out about equally long, whatever the language. The result is given to the
 * engine as the caption's own band width (the stage reads c.band); the size is never changed.
 */
function balanceCaptions() {
  const cv = document.createElement('canvas');
  const ctx = cv.getContext('2d');
  for (const c of CAPTIONS) {
    const str = EP.T(c.key);
    const base = { size: 50, weight: 600 };
    if (EP.measure(ctx, str, base).w <= 1560) { delete c.band; continue; }
    // narrowest width that still gives two lines AND in which every line really fits
    // (a translation may contain no-break spaces: an unbreakable chunk can be wider than the band)
    let best = 1560;
    for (let w = 1560; w >= 600; w -= 4) {
      const b = EP.measure(ctx, str, { ...base, maxWidth: w });
      if (b.lines.length > 2 || b.w > w + 0.5) break;
      best = w;
    }
    c.band = { maxWidth: best + 8 };
  }
}

/**
 * EP.layer grows its shared offscreen canvases on demand, and the browser rasterises a big
 * canvas very slightly differently from a small one (one level in one colour channel). To make
 * a frame bit-identical whatever was drawn before it, allocate them at full frame size once.
 */
function allocateLayers() {
  const cv = document.createElement('canvas');
  cv.width = 16; cv.height = 16;
  const { W, H } = EP.STAGE;
  EP.layer(cv.getContext('2d'), 1, 0, 0, W, H, h => EP.layer(h, 1, 0, 0, W, H, () => {}));
}

// =====================================================================================
// 5. PART 1 - THE MOTOR, THE SENSOR, THE WIRE
// =====================================================================================
const MS = 1.1;                                          // scale of the motor and its sensor
const MOTOR = { x: 262, y: 718 };                        // centre of the motor body (base plate on the axis line)
const SENSOR1 = { x: MOTOR.x - 8 * MS, y: MOTOR.y - 73 * MS, s: MS };
const riseAt = t => (1 - P(t, K.motor, K.motor + 0.8)) * 16;

/** Electric motor, side view, shaft to the left. Origin = centre of the body. */
function drawMotor(ctx, mx, my, s, a) {
  const { PAL, SHADE, rgba } = EP;
  if (a <= 0) return;
  ctx.save();
  ctx.translate(mx, my); ctx.scale(s, s);
  ctx.globalAlpha *= a;

  // base plate and feet
  ctx.fillStyle = SHADE.steelDark;
  EP.roundRect(ctx, -136, 60, 270, 11, 3); ctx.fill();
  for (const fx of [-60, 28]) {
    ctx.fillStyle = SHADE.steelMid;
    EP.roundRect(ctx, fx, 42, 34, 20, 3); ctx.fill();
  }
  // shaft with its key
  ctx.fillStyle = vGrad(ctx, -9, 9);
  ctx.fillRect(-150, -9, 66, 18);
  ctx.fillStyle = SHADE.steelDark;
  ctx.fillRect(-142, -13, 32, 5);
  ctx.strokeStyle = rgba(PAL.ink, 0.4); ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(-145, -9); ctx.lineTo(-145, 9); ctx.stroke();
  // drive-end shield
  ctx.fillStyle = vGrad(ctx, -40, 40);
  EP.roundRect(ctx, -98, -40, 28, 80, 6); ctx.fill();
  ctx.fillStyle = rgba(PAL.ink, 0.4);
  for (const by of [-28, 28]) { ctx.beginPath(); ctx.arc(-84, by, 2.4, 0, TAU); ctx.fill(); }
  // fan cover at the back (dome with slots)
  const dome = new Path2D();
  dome.moveTo(68, -40);
  dome.bezierCurveTo(100, -40, 124, -30, 124, -8);
  dome.lineTo(124, 8);
  dome.bezierCurveTo(124, 30, 100, 40, 68, 40);
  dome.closePath();
  ctx.fillStyle = vGrad(ctx, -40, 40);
  ctx.fill(dome);
  ctx.save(); ctx.clip(dome);
  ctx.strokeStyle = rgba(PAL.ink, 0.38); ctx.lineWidth = 2.2; ctx.lineCap = 'round';
  for (let y = -24; y <= 24; y += 12) { ctx.beginPath(); ctx.moveTo(92, y); ctx.lineTo(114, y); ctx.stroke(); }
  ctx.restore();
  // main housing with cooling fins
  ctx.fillStyle = vGrad(ctx, -46, 46);
  EP.roundRect(ctx, -78, -46, 152, 92, 10); ctx.fill();
  ctx.save();
  EP.roundRect(ctx, -78, -46, 152, 92, 10); ctx.clip();
  for (let x = -62; x <= 64; x += 12) {
    ctx.strokeStyle = rgba(PAL.ink, 0.36); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x, -46); ctx.lineTo(x, 46); ctx.stroke();
    ctx.strokeStyle = rgba(PAL.paper, 0.11); ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(x + 2, -46); ctx.lineTo(x + 2, 46); ctx.stroke();
  }
  ctx.restore();
  ctx.strokeStyle = rgba(PAL.paper, 0.2); ctx.lineWidth = 1.2;
  EP.roundRect(ctx, -78, -46, 152, 92, 10); ctx.stroke();
  ctx.restore();
}

/**
 * The vibration sensor: a small steel box on a stud, with its connector. Centre of the box
 * at (x, y). dotA = visibility of the purple contact where the wire is attached.
 */
function drawSensor(ctx, x, y, s, a, dotA) {
  const { PAL, SHADE, rgba } = EP;
  if (a <= 0) return;
  ctx.save();
  ctx.translate(x, y); ctx.scale(s, s);
  ctx.globalAlpha *= a;
  ctx.fillStyle = SHADE.steelDark;                       // stud into the housing
  EP.roundRect(ctx, -7, 14, 14, 13, 2); ctx.fill();
  ctx.fillStyle = SHADE.steelMid;                        // connector
  EP.roundRect(ctx, 9, -25, 12, 9, 2); ctx.fill();
  const g = ctx.createLinearGradient(0, -18, 0, 16);     // the box
  g.addColorStop(0, SHADE.steelLight); g.addColorStop(0.5, PAL.steel); g.addColorStop(1, SHADE.steelMid);
  EP.roundRect(ctx, -22, -18, 44, 34, 6);
  ctx.fillStyle = g; ctx.fill();
  ctx.lineWidth = 1.3; ctx.strokeStyle = rgba(PAL.paper, 0.38); ctx.stroke();
  ctx.strokeStyle = rgba(PAL.ink, 0.4); ctx.lineWidth = 1.6; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(-15, 7); ctx.lineTo(15, 7); ctx.stroke();
  ctx.fillStyle = SHADE.steelDark;
  ctx.beginPath(); ctx.arc(-11, -6, 3.4, 0, TAU); ctx.fill();
  if (dotA > 0) {                                        // where the wire is attached
    ctx.globalAlpha *= dotA;
    ctx.fillStyle = PAL.field;
    ctx.beginPath(); ctx.arc(15, -25, 2.8, 0, TAU); ctx.fill();
  }
  ctx.restore();
}

/** Faint arcs spreading from the sensor: it feels the vibration. Slow loop, never a flash. */
function drawRipples(ctx, x, y, s, t, a) {
  if (a <= 0) return;
  const { PAL, rgba } = EP;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.lineWidth = 2.6 * Math.sqrt(s);
  for (const side of [-1, 1]) for (let i = 0; i < 3; i++) {
    const ph = (t / 1.9 + i / 3) % 1;
    const r = (30 + 26 * ph) * s;
    const al = Math.pow(Math.sin(Math.PI * ph), 1.4) * 0.5 * a;
    ctx.strokeStyle = rgba(PAL.steel, al);
    ctx.beginPath();
    ctx.arc(x, y, r, side < 0 ? Math.PI - 0.5 : -0.5, side < 0 ? Math.PI + 0.5 : 0.5);
    ctx.stroke();
  }
  ctx.restore();
}

// the wire: from the connector of the sensor to the first point of the trace
function wirePoint(u, rise) {
  const p0 = [SENSOR1.x + 15 * MS, SENSOR1.y - 25 * MS + rise], p3 = [PL.x0, yOf(realSignal(0))];
  const p1 = [p0[0], p0[1] - 84], p2 = [PL.x0 - 96, p3[1]];
  const m = 1 - u;
  return [
    m * m * m * p0[0] + 3 * m * m * u * p1[0] + 3 * m * u * u * p2[0] + u * u * u * p3[0],
    m * m * m * p0[1] + 3 * m * m * u * p1[1] + 3 * m * u * u * p2[1] + u * u * u * p3[1],
  ];
}
function drawWire(ctx, t, a) {
  const { PAL, rgba } = EP;
  const k = P(t, K.wire[0], K.wire[1], EP.ease.inOutSine);
  if (k <= 0 || a <= 0) return;
  const rise = riseAt(t);
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath();
  const n = 90;
  for (let i = 0; i <= n; i++) {
    const [x, y] = wirePoint((i / n) * k, rise);
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  }
  ctx.strokeStyle = rgba(PAL.field, 0.55); ctx.lineWidth = 3.6; ctx.stroke();
  // beads of signal flowing along the wire (slow: about 45 px per second)
  ctx.setLineDash([0.1, 26]); ctx.lineDashOffset = -t * 45;
  ctx.strokeStyle = PAL.field; ctx.lineWidth = 6.2; ctx.stroke();
  ctx.restore();
}

// =====================================================================================
// 6. PART 1 - THE PLOT
// =====================================================================================
function drawAxes(ctx, t, a) {
  const { PAL, rgba } = EP;
  const kA = P(t, K.axis[0], K.axis[1], EP.ease.outCubic);
  if (kA <= 0 || a <= 0) return;
  const steel = PAL.steel;
  ctx.save();
  ctx.globalAlpha *= a;
  // zero line, faint and dotted
  ctx.strokeStyle = rgba(steel, 0.34); ctx.lineWidth = 1.5; ctx.setLineDash([2, 7]);
  ctx.beginPath(); ctx.moveTo(PL.x0, PL.zy + 0.5); ctx.lineTo(PL.x0 + (PL.x1 - PL.x0) * kA, PL.zy + 0.5); ctx.stroke();
  ctx.setLineDash([]);
  // the two axes
  ctx.strokeStyle = rgba(steel, 0.8); ctx.lineWidth = 2; ctx.lineCap = 'butt';
  ctx.beginPath();
  ctx.moveTo(PL.x0 + 0.5, PL.axy); ctx.lineTo(PL.x0 + 0.5, PL.axy - (PL.axy - PL.top) * kA);
  ctx.moveTo(PL.x0, PL.axy + 0.5); ctx.lineTo(PL.x0 + (PL.x1 - PL.x0) * kA, PL.axy + 0.5);
  ctx.stroke();
  // ticks every millisecond, numbers every 2 ms
  for (let k = 0; k <= 20; k++) {
    const ta = K.axis[0] + (k / 20) * (K.axis[1] - K.axis[0]) * 0.85;
    const q = P(t, ta, ta + 0.3);
    if (q <= 0) continue;
    const x = Math.round(xOf(k)) + 0.5, major = k % 2 === 0;
    ctx.strokeStyle = rgba(steel, 0.8 * q); ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(x, PL.axy + 1); ctx.lineTo(x, PL.axy + (major ? 13 : 7)); ctx.stroke();
    if (major) EP.text(ctx, EP.num(k), { x: xOf(k), y: PL.axy + 45 + (1 - q) * 5, align: 'center', size: 24, weight: 500, color: steel, opacity: q, latin: true });
  }
  const qU = P(t, K.axis[1] - 0.2, K.axis[1] + 0.3);
  EP.text(ctx, 'ms', { x: PL.x1 + 24, y: PL.axy + 45, align: 'left', size: 24, weight: 500, color: steel, opacity: qU, latin: true });
  ctx.restore();
}

function drawTicks(ctx, t, a) {
  const { PAL, rgba } = EP;
  if (a <= 0) return;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.lineCap = 'round';
  for (let k = 0; k < N_DOT; k++) {
    const ta = K.ticks + k * K.tickStep;
    const q = P(t, ta, ta + 0.22);
    if (q <= 0) continue;
    const x = Math.round(xOf(k)) + 0.5;
    ctx.strokeStyle = rgba(PAL.paper, 0.95); ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(x, PL.axy - 1); ctx.lineTo(x, PL.axy - 1 - 17 * q); ctx.stroke();
  }
  ctx.restore();
}

function drawGuides(ctx, t, a) {
  const { PAL, rgba } = EP;
  if (a <= 0) return;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.lineWidth = 1.5; ctx.lineCap = 'butt';
  for (const d of DOTS) {
    const ta = dotTime(d.k);
    const g = P(t, ta, ta + 0.17);
    if (g <= 0) continue;
    const x = Math.round(d.x) + 0.5, y0 = PL.axy - 18, y1 = lerp(y0, d.y, g);
    ctx.strokeStyle = rgba(PAL.paper, 0.2);
    ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, y1); ctx.stroke();
  }
  ctx.restore();
}

function drawReal(ctx, t, a, dim) {
  const { PAL, rgba } = EP;
  const k = P(t, K.real[0], K.real[1], EP.ease.inOutSine);
  if (k <= 0 || a <= 0) return;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  tracePath(ctx, REAL_X, REAL_Y, k);
  ctx.strokeStyle = rgba(PAL.field, lerp(0.95, 0.34, dim)); ctx.lineWidth = 2.3;
  ctx.stroke();
  ctx.restore();
}

function drawAlias(ctx, t, a) {
  const { PAL, rgba } = EP;
  const k = P(t, K.alias[0], K.alias[1], EP.ease.inOutSine);
  if (k <= 0 || a <= 0) return;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.lineJoin = 'round'; ctx.lineCap = 'butt';
  tracePath(ctx, ALIAS_X, ALIAS_Y, k);
  // a dark halo with the same dashes keeps the dashed wave readable over the thin one
  ctx.setLineDash([15, 10]);
  ctx.strokeStyle = rgba(PAL.ink, 0.75); ctx.lineWidth = 8; ctx.stroke();
  ctx.strokeStyle = PAL.field; ctx.lineWidth = 4.2; ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
}

/** Yellow marker at the drawing tip of the alias ("look here"); on top of the dots, gone when the wave is complete. */
function drawPen(ctx, t, a) {
  const { PAL, rgba } = EP;
  const k = P(t, K.alias[0], K.alias[1], EP.ease.inOutSine);
  const m = (1 - P(t, K.alias[1], K.alias[1] + 0.35, EP.ease.inOutSine)) * a;
  if (k <= 0 || m <= 0) return;
  const f = k * N_ALIAS, i = Math.min(Math.floor(f), N_ALIAS - 1), r = f - i;
  const tx = ALIAS_X[i] + (ALIAS_X[i + 1] - ALIAS_X[i]) * r, ty = ALIAS_Y[i] + (ALIAS_Y[i + 1] - ALIAS_Y[i]) * r;
  ctx.save();
  ctx.fillStyle = rgba(PAL.ink, 0.8 * m); ctx.beginPath(); ctx.arc(tx, ty, 9.5, 0, TAU); ctx.fill();
  ctx.fillStyle = rgba(PAL.highlight, m); ctx.beginPath(); ctx.arc(tx, ty, 6, 0, TAU); ctx.fill();
  ctx.restore();
}

function drawDots(ctx, t, a) {
  const { PAL, rgba } = EP;
  if (a <= 0) return;
  ctx.save();
  ctx.globalAlpha *= a;
  for (const d of DOTS) {
    const ta = dotTime(d.k);
    if (t <= ta + 0.12) continue;
    const q = P(t, ta + 0.12, ta + 0.4, EP.ease.outBack);
    const r = 6.4 * clamp(q, 0, 1.25);
    // a small ring "pings" outwards as the value is read
    const ping = P(t, ta + 0.14, ta + 0.62);
    if (ping > 0 && ping < 1) {
      ctx.strokeStyle = rgba(PAL.paper, 0.55 * (1 - ping)); ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(d.x, d.y, 7 + 15 * ping, 0, TAU); ctx.stroke();
    }
    ctx.fillStyle = PAL.ink; ctx.beginPath(); ctx.arc(d.x, d.y, r + 2.6 * clamp(q * 4), 0, TAU); ctx.fill();   // halo grows with the dot
    ctx.fillStyle = PAL.paper; ctx.beginPath(); ctx.arc(d.x, d.y, r, 0, TAU); ctx.fill();
  }
  ctx.restore();
}

/**
 * One legend entry: swatch (drawn the way the thing is drawn) and label; mirrored in Arabic.
 * a = opacity, k = entrance progress (0..1) for the small rise.
 */
function legendItem(ctx, o) {
  const { PAL, rgba } = EP;
  const { x, y, w, str, kind, a, k } = o;
  if (a <= 0) return;
  const rtl = EP.isRTL();
  const size = 30, sw = 62, gap = 16, maxW = w - sw - gap;
  const rise = (1 - k) * 9;
  const sx = rtl ? x + w - sw : x;
  const tx = rtl ? x + w - sw - gap : x + sw + gap;
  const cy = y - 11 + rise;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.lineCap = 'round';
  if (kind === 'line') {
    ctx.strokeStyle = rgba(PAL.field, 0.95); ctx.lineWidth = 2.3;
    ctx.beginPath(); ctx.moveTo(sx, cy); ctx.lineTo(sx + sw, cy); ctx.stroke();
  } else if (kind === 'dash') {
    ctx.lineCap = 'butt'; ctx.setLineDash([13, 8]);
    ctx.strokeStyle = PAL.field; ctx.lineWidth = 4.2;
    ctx.beginPath(); ctx.moveTo(sx, cy); ctx.lineTo(sx + sw, cy); ctx.stroke();
    ctx.setLineDash([]);
  } else {
    ctx.strokeStyle = rgba(PAL.paper, 0.95); ctx.lineWidth = 2.2;
    ctx.beginPath(); ctx.moveTo(sx + sw / 2, cy + 14); ctx.lineTo(sx + sw / 2, cy); ctx.stroke();
    ctx.fillStyle = PAL.paper; ctx.beginPath(); ctx.arc(sx + sw / 2, cy, 6.4, 0, TAU); ctx.fill();
  }
  ctx.restore();
  EP.text(ctx, str, { x: tx, y: y + rise, size, weight: 600, align: rtl ? 'right' : 'left', maxWidth: maxW, shrink: true, maxLines: 1, opacity: a });
}
const LG = { colA: PL.x0, wA: 620, colB: PL.x0 + 640, wB: PL.x1 - (PL.x0 + 640), y1: 366, y2: 412 };

// =====================================================================================
// 7. PART 2 - THE BLOCK DIAGRAM
// =====================================================================================
const DG = {
  y: 536, w: 240, h: 212, cx: [247.5, 722.5, 1197.5, 1672.5],
  tw: 150, th: 88,                                  // signal thumbnails on the connections
  labelY: 536 + 106 + 58,
  eqY: 838,
};
const SENSOR2 = { x: DG.cx[0], y: DG.y - 12, s: 2.0 };

function blockFrame(ctx, cx, cy, k) {
  const { PAL, SHADE, rgba } = EP;
  ctx.fillStyle = rgba(SHADE.inkLift, 0.97);
  EP.roundRect(ctx, cx - DG.w / 2, cy - DG.h / 2, DG.w, DG.h, 20); ctx.fill();
  ctx.lineWidth = 2.5; ctx.strokeStyle = rgba(PAL.steel, 0.85 * k);
  ctx.stroke();
}

function iconFilter(ctx, cx, cy, k) {
  const { PAL, rgba } = EP;
  const w = 150, h = 88, x0 = cx - w / 2, y0 = cy - h / 2;
  // gain of a 4th-order low-pass on a frequency axis from 0 to f_s; cut-off well below f_s / 2
  const fc = 0.3, gain = f => 1 / Math.sqrt(1 + Math.pow(f / fc, 8));
  const X = f => x0 + 6 + f * (w - 10), Y = g => y0 + h - 8 - g * (h - 22);
  ctx.save();
  ctx.strokeStyle = rgba(PAL.steel, 0.85); ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(x0, y0 - 2); ctx.lineTo(x0, y0 + h); ctx.lineTo(x0 + w, y0 + h); ctx.stroke();
  // reveal from left to right
  ctx.beginPath(); ctx.rect(x0 - 4, y0 - 12, (w + 12) * clamp(k), h + 24); ctx.clip();
  // pass band: the zone that "works" (green)
  ctx.beginPath(); ctx.moveTo(X(0), Y(0));
  for (let f = 0; f <= fc + 1e-9; f += 0.01) ctx.lineTo(X(f), Y(gain(f)));
  ctx.lineTo(X(fc), Y(0)); ctx.closePath();
  ctx.fillStyle = rgba(PAL.balance, 0.3); ctx.fill();
  ctx.setLineDash([4, 5]); ctx.strokeStyle = rgba(PAL.balance, 0.95); ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(X(fc), Y(0)); ctx.lineTo(X(fc), Y(gain(fc)) - 6); ctx.stroke();
  ctx.setLineDash([]);
  ctx.beginPath();
  for (let f = 0; f <= 1 + 1e-9; f += 0.01) f ? ctx.lineTo(X(f), Y(gain(f))) : ctx.moveTo(X(f), Y(gain(f)));
  ctx.strokeStyle = PAL.paper; ctx.lineWidth = 3.2; ctx.stroke();
  // the 900 Hz of part 1 sits far beyond the cut-off, pushed down to almost nothing
  if (k > 0.97) {
    const f = 0.9;
    ctx.fillStyle = PAL.ink; ctx.beginPath(); ctx.arc(X(f), Y(gain(f)), 7.5, 0, TAU); ctx.fill();
    ctx.fillStyle = PAL.highlight; ctx.beginPath(); ctx.arc(X(f), Y(gain(f)), 5, 0, TAU); ctx.fill();
  }
  ctx.restore();
  const qL = clamp((k - 0.95) / 0.05);
  if (qL > 0) EP.text(ctx, '900 Hz', { x: X(0.9), y: Y(gain(0.9)) - 20 - (1 - qL) * 5, align: 'center', size: 24, weight: 600, color: PAL.highlight, opacity: qL, latin: true });
}

function iconADC(ctx, cx, cy, k) {
  const { PAL, rgba } = EP;
  const w = 150, h = 88, x0 = cx - w / 2, y0 = cy - h / 2, mid = y0 + h / 2, amp = 34;
  const curve = u => -Math.sin(TAU * u);                           // one clean cycle
  const level = v => Math.round((v + 1) * 1.5) / 1.5 - 1;          // 2 bits: four levels
  ctx.save();
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.strokeStyle = rgba(PAL.steel, 0.4); ctx.lineWidth = 1.5; ctx.setLineDash([2, 6]);
  ctx.beginPath(); ctx.moveTo(x0, mid); ctx.lineTo(x0 + w, mid); ctx.stroke(); ctx.setLineDash([]);
  ctx.beginPath(); ctx.rect(x0 - 6, y0 - 12, (w + 12) * clamp(k), h + 24); ctx.clip();
  // the numbers the converter makes of the signal: held, coarse steps (paper)
  const N = 8;
  ctx.beginPath();
  for (let i = 0; i < N; i++) {
    const u0 = i / N, u1 = (i + 1) / N, y = mid - amp * level(curve((i + 0.5) / N));
    if (i) ctx.lineTo(x0 + u0 * w, y); else ctx.moveTo(x0 + u0 * w, y);
    ctx.lineTo(x0 + u1 * w, y);
  }
  ctx.lineJoin = 'miter';
  ctx.strokeStyle = PAL.paper; ctx.lineWidth = 3; ctx.stroke();
  ctx.lineJoin = 'round';
  // the analogue signal it comes from (purple), thinner, on top
  ctx.beginPath();
  for (let i = 0; i <= 120; i++) { const u = i / 120; const x = x0 + u * w, y = mid - amp * curve(u); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }
  ctx.strokeStyle = PAL.field; ctx.lineWidth = 2.4; ctx.stroke();
  ctx.restore();
}

function iconChip(ctx, cx, cy) {
  const { PAL, SHADE, rgba } = EP;
  const s = 84, pins = 5, pl = 13;
  ctx.save();
  ctx.lineCap = 'round';
  ctx.strokeStyle = rgba(PAL.steel, 0.9); ctx.lineWidth = 3;
  for (let i = 0; i < pins; i++) {
    const o = -s / 2 + (s / (pins + 1)) * (i + 1);
    ctx.beginPath(); ctx.moveTo(cx + o, cy - s / 2); ctx.lineTo(cx + o, cy - s / 2 - pl);
    ctx.moveTo(cx + o, cy + s / 2); ctx.lineTo(cx + o, cy + s / 2 + pl);
    ctx.moveTo(cx - s / 2, cy + o); ctx.lineTo(cx - s / 2 - pl, cy + o);
    ctx.moveTo(cx + s / 2, cy + o); ctx.lineTo(cx + s / 2 + pl, cy + o);
    ctx.stroke();
  }
  EP.roundRect(ctx, cx - s / 2, cy - s / 2, s, s, 10);
  const g = ctx.createLinearGradient(0, cy - s / 2, 0, cy + s / 2);
  g.addColorStop(0, SHADE.steelMid); g.addColorStop(1, SHADE.steelDark);
  ctx.fillStyle = g; ctx.fill();
  ctx.lineWidth = 2.5; ctx.strokeStyle = rgba(PAL.steel, 0.95); ctx.stroke();
  EP.roundRect(ctx, cx - 20, cy - 20, 40, 40, 6);
  ctx.strokeStyle = rgba(PAL.paper, 0.5); ctx.lineWidth = 2; ctx.stroke();
  ctx.fillStyle = rgba(PAL.paper, 0.85); ctx.beginPath(); ctx.arc(cx - 12, cy - 12, 2.8, 0, TAU); ctx.fill();
  ctx.restore();
}

// signal thumbnails: slow useful wave, fast 900 Hz ripple, samples. They scroll slowly to the right.
const TH = { slow: 88, fast: 12, sp: 11, v: 22, ampS: 20, ampF: 8.5 };
const slowAt = s => TH.ampS * Math.sin(TAU * s / TH.slow + 0.7);
const fastAt = s => TH.ampF * Math.sin(TAU * s / TH.fast + 0.4);
function thumb(ctx, cx, cy, kind, t, a) {
  const { PAL, SHADE, rgba } = EP;
  if (a <= 0) return;
  const w = DG.tw, h = DG.th;
  ctx.save();
  ctx.globalAlpha *= a;
  EP.roundRect(ctx, cx - w / 2, cy - h / 2, w, h, 12);
  ctx.fillStyle = rgba(SHADE.inkLift, 0.97); ctx.fill();
  ctx.lineWidth = 1.5; ctx.strokeStyle = rgba(PAL.steel, 0.45); ctx.stroke();
  EP.roundRect(ctx, cx - w / 2 + 5, cy - h / 2 + 5, w - 10, h - 10, 8); ctx.clip();
  const L = cx - w / 2, R = cx + w / 2, sh = t * TH.v;
  ctx.strokeStyle = rgba(PAL.steel, 0.35); ctx.lineWidth = 1.2; ctx.setLineDash([2, 5]);
  ctx.beginPath(); ctx.moveTo(L, cy); ctx.lineTo(R, cy); ctx.stroke(); ctx.setLineDash([]);
  ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  if (kind === 'dots') {
    const m = ((sh % TH.sp) + TH.sp) % TH.sp;
    ctx.lineWidth = 1.4;
    for (let x = L + m - TH.sp; x <= R + TH.sp; x += TH.sp) {
      const y = cy - slowAt(x - L - sh);
      ctx.strokeStyle = rgba(PAL.paper, 0.32);
      ctx.beginPath(); ctx.moveTo(x, cy); ctx.lineTo(x, y); ctx.stroke();
    }
    for (let x = L + m - TH.sp; x <= R + TH.sp; x += TH.sp) {
      const y = cy - slowAt(x - L - sh);
      ctx.fillStyle = PAL.paper; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, TAU); ctx.fill();
    }
  } else {
    ctx.beginPath();
    for (let x = L; x <= R; x += 1) {
      const s = x - L - sh, y = cy - slowAt(s) - (kind === 'raw' ? fastAt(s) : 0);
      x === L ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.strokeStyle = PAL.field; ctx.lineWidth = 2.4; ctx.stroke();
  }
  ctx.restore();
}

// =====================================================================================
// 8. PART 3 - THE FAN AND THE STROBE
// =====================================================================================
const FV = { cxL: 584, cxR: 1384, lampY: 352, waveY: 466, fanY: 664, R: 132, yLabel: 866, yNum: 910 };
const STROBE_HZ_ON_SCREEN = 1.5;                                   // rays and pulses: at most twice per second
const _blade = new Map();
function bladeShapes(R) {
  let s = _blade.get(R);
  if (s) return s;
  const N = 32, rRoot = 0.15 * R;
  const rad = u => rRoot + (R - rRoot) * u;
  const sweep = u => 0.34 * u * u;                          // blades trail against the turning direction
  const half = u => {
    const q = clamp(u / 0.66);
    const body = 0.052 + 0.146 * q * q * (3 - 2 * q);
    const cap = u < 0.86 ? 1 : Math.sqrt(Math.max(0, 1 - Math.pow((u - 0.86) / 0.14, 2)));
    return R * body * cap;
  };
  const C = u => { const r = rad(u), a = -sweep(u); return { x: r * Math.sin(a), y: -r * Math.cos(a), nx: Math.cos(a), ny: Math.sin(a) }; };
  const edge = (u, sgn) => { const c = C(u), h = half(u) * sgn; return [c.x + c.nx * h, c.y + c.ny * h]; };
  const outline = new Path2D(), light = new Path2D(), rib = new Path2D();
  for (let i = 0; i <= N; i++) { const p = edge(i / N, 1); i ? outline.lineTo(...p) : outline.moveTo(...p); }
  for (let i = N; i >= 0; i--) outline.lineTo(...edge(i / N, -1));
  outline.closePath();
  for (let i = 0; i <= N; i++) { const c = C(i / N); i ? light.lineTo(c.x, c.y) : light.moveTo(c.x, c.y); }
  for (let i = N; i >= 0; i--) light.lineTo(...edge(i / N, 1));
  light.closePath();
  for (let i = 4; i <= N - 5; i++) { const c = C(i / N); i > 4 ? rib.lineTo(c.x, c.y) : rib.moveTo(c.x, c.y); }
  // share of the circle of radius r that the blades cover at one instant
  const cover = r => {
    const u = clamp((r - rRoot) / (R - rRoot));
    return clamp(FAN.blades * 2 * Math.atan2(half(u), Math.max(r, 1e-6)) / TAU);
  };
  s = { outline, light, rib, cover };
  _blade.set(R, s);
  return s;
}

function drawFanCrisp(ctx, x, y, R, angle, a) {
  const { PAL, SHADE, rgba } = EP;
  if (a <= 0) return;
  const sh = bladeShapes(R);
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= a;
  for (let i = 0; i < FAN.blades; i++) {
    ctx.save();
    ctx.rotate(angle + (i * TAU) / FAN.blades);
    ctx.fillStyle = PAL.steel; ctx.fill(sh.outline);
    ctx.fillStyle = rgba(SHADE.steelLight, 0.55); ctx.fill(sh.light);
    ctx.strokeStyle = rgba(PAL.ink, 0.28); ctx.lineWidth = 1.6; ctx.stroke(sh.rib);
    ctx.lineJoin = 'round'; ctx.lineWidth = Math.max(1.2, R * 0.009); ctx.strokeStyle = rgba(PAL.paper, 0.3); ctx.stroke(sh.outline);
    ctx.restore();
  }
  ctx.restore();
}

/**
 * What the eye sees in steady light: the blades sweep every angle many times in a
 * blink, so each radius gets the share of paint the blades cover at one instant.
 */
function drawFanBlur(ctx, x, y, R, a) {
  const { SHADE, rgba } = EP;
  if (a <= 0) return;
  const sh = bladeShapes(R);
  // coverage averaged over a small window of radii, so the disc has no faint rings
  const cover = f => { let sum = 0; for (let j = -3; j <= 3; j++) sum += sh.cover(clamp(f + 0.05 * j, 0.16, 0.9) * R); return sum / 7; };
  const smooth = (e0, e1, v) => { const q = clamp((v - e0) / (e1 - e0)); return q * q * (3 - 2 * q); };
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= a;
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, R * 1.02);
  const n = 32;
  for (let i = 0; i <= n; i++) {
    const f = i / n;
    const al = clamp(0.16 + 1.5 * cover(f), 0, 0.6) * (1 - smooth(0.84, 1.0, f));
    g.addColorStop(f, rgba(SHADE.steelLight, al));
  }
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(0, 0, R * 1.02, 0, TAU); ctx.fill();
  ctx.restore();
}

/** Guard ring, hub, fixed sheen: always crisp. */
function drawFanFrame(ctx, x, y, R, a) {
  const { PAL, SHADE, rgba } = EP;
  if (a <= 0) return;
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= a;
  ctx.strokeStyle = rgba(PAL.steel, 0.5); ctx.lineWidth = 3;
  ctx.beginPath(); ctx.arc(0, 0, R * 1.13, 0, TAU); ctx.stroke();
  ctx.strokeStyle = rgba(PAL.steel, 0.18); ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.arc(0, 0, R * 1.13 + 7, 0, TAU); ctx.stroke();
  // hub
  ctx.fillStyle = SHADE.steelLight; ctx.beginPath(); ctx.arc(0, 0, R * 0.19, 0, TAU); ctx.fill();
  ctx.fillStyle = SHADE.steelDark; ctx.beginPath(); ctx.arc(0, 0, R * 0.165, 0, TAU); ctx.fill();
  ctx.fillStyle = PAL.steel; ctx.beginPath(); ctx.arc(0, 0, R * 0.135, 0, TAU); ctx.fill();
  ctx.fillStyle = SHADE.steelLight; ctx.beginPath(); ctx.arc(0, 0, R * 0.05, 0, TAU); ctx.fill();
  const sg = ctx.createRadialGradient(-R * 0.3, -R * 0.36, R * 0.05, -R * 0.1, -R * 0.1, R * 1.05);
  sg.addColorStop(0, rgba(PAL.paper, 0.1)); sg.addColorStop(1, rgba(PAL.paper, 0));
  ctx.fillStyle = sg; ctx.beginPath(); ctx.arc(0, 0, R * 1.05, 0, TAU); ctx.fill();
  ctx.restore();
}

/** Pendant lamp with rays. rays 0..1 = brightness of the rays (orange = light output). */
function drawLamp(ctx, x, y, rays, a, ring = 0) {
  const { PAL, SHADE, rgba, mix } = EP;
  if (a <= 0) return;
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha *= a;
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  // soft halo (small, never a flash)
  if (rays > 0) {
    const g = ctx.createRadialGradient(0, 4, 4, 0, 4, 58);
    g.addColorStop(0, rgba(PAL.energy, 0.26 * rays)); g.addColorStop(1, rgba(PAL.energy, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 4, 58, 0, TAU); ctx.fill();
  }
  // a ring spreads once when the lamp is switched on (small, brief)
  if (ring > 0 && ring < 1) {
    const q = 1 - Math.pow(1 - ring, 3);
    ctx.strokeStyle = rgba(PAL.energy, 0.75 * (1 - ring)); ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(0, 4, 18 + 52 * q, 0, TAU); ctx.stroke();
  }
  // cord and shade
  ctx.strokeStyle = rgba(PAL.steel, 0.8); ctx.lineWidth = 3;
  ctx.beginPath(); ctx.moveTo(0, -64); ctx.lineTo(0, -48); ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(-34, -8); ctx.lineTo(-19, -44); ctx.quadraticCurveTo(0, -52, 19, -44); ctx.lineTo(34, -8); ctx.closePath();
  const g2 = ctx.createLinearGradient(-34, 0, 34, 0);
  g2.addColorStop(0, SHADE.steelMid); g2.addColorStop(0.3, SHADE.steelLight); g2.addColorStop(1, SHADE.steelDark);
  ctx.fillStyle = g2; ctx.fill();
  ctx.lineWidth = 1.4; ctx.strokeStyle = rgba(PAL.paper, 0.3); ctx.stroke();
  // bulb
  ctx.fillStyle = mix(PAL.energy, PAL.paper, 0.15 + 0.5 * rays);
  ctx.beginPath(); ctx.arc(0, 4, 12, 0, TAU); ctx.fill();
  // rays: length and brightness follow "rays"
  const n = 7;
  for (let i = 0; i < n; i++) {
    const ang = ((i - (n - 1) / 2) * 27) * Math.PI / 180;      // 0 = straight down
    const r0 = 27, r1 = r0 + 10 + 15 * rays;
    ctx.strokeStyle = rgba(PAL.energy, 0.14 + 0.86 * rays);
    ctx.lineWidth = 4.4;
    ctx.beginPath();
    ctx.moveTo(Math.sin(ang) * r0, 4 + Math.cos(ang) * r0);
    ctx.lineTo(Math.sin(ang) * r1, 4 + Math.cos(ang) * r1);
    ctx.stroke();
  }
  ctx.restore();
}

/**
 * Light output over time (orange = light): a steady line, or short flashes moving away from
 * the lamp. New flashes leave exactly when the rays of the lamp are brightest.
 */
function drawLightWave(ctx, x0, yBase, w, kind, t, a, dir = 1) {
  const { PAL, rgba } = EP;
  if (a <= 0) return;
  const H = 34, V = 36;                                    // height (px), speed (px per second)
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.strokeStyle = rgba(PAL.steel, 0.45); ctx.lineWidth = 1.6; ctx.setLineDash([2, 6]);
  ctx.beginPath(); ctx.moveTo(x0, yBase + 0.5); ctx.lineTo(x0 + w, yBase + 0.5); ctx.stroke(); ctx.setLineDash([]);
  ctx.strokeStyle = PAL.energy; ctx.lineWidth = 3.2;
  if (kind === 'steady') {
    ctx.beginPath(); ctx.moveTo(x0, yBase - H); ctx.lineTo(x0 + w, yBase - H); ctx.stroke();
  } else {
    // a periodic train (the strobe is always pulsing): flashes leave the lamp end and drift away
    const age = t - K.strobeOn;
    const nMax = Math.floor(age * STROBE_HZ_ON_SCREEN), nMin = Math.ceil((age - w / V) * STROBE_HZ_ON_SCREEN);
    ctx.lineWidth = 5;
    for (let n = nMin; n <= nMax; n++) {
      const d = V * (age - n / STROBE_HZ_ON_SCREEN);           // distance travelled since it left the lamp end
      if (d < 0 || d > w) continue;
      const x = dir > 0 ? x0 + d : x0 + w - d;
      const al = clamp(d / 8) * clamp((w - d) / 40);
      ctx.strokeStyle = rgba(PAL.energy, al);
      ctx.beginPath(); ctx.moveTo(x, yBase); ctx.lineTo(x, yBase - H); ctx.stroke();
    }
  }
  ctx.restore();
}

/** Rotation glyph + speed in turns per second: solid blue arc = real, dashed = what we see. */
function speedLine(ctx, cx, yLabel, yNum, labelKey, value, digits, dashed, a) {
  const { PAL } = EP;
  if (a <= 0) return;
  const rtl = EP.isRTL();
  const str = EP.num(value, digits) + ' ' + EP.T('unit.turns');
  const o = { size: 38, weight: 600, maxWidth: 440, shrink: true, maxLines: 1 };
  const bw = EP.measure(ctx, str, o).w;
  const iconW = 48, gap = 16, total = iconW + gap + bw, left = cx - total / 2;
  const icx = rtl ? left + total - iconW / 2 : left + iconW / 2;
  const tx = rtl ? left + total - iconW - gap : left + iconW + gap;
  EP.text(ctx, EP.T(labelKey), { x: cx, y: yLabel, align: 'center', size: 28, weight: 500, color: PAL.steel, opacity: a, maxWidth: 560, shrink: true, maxLines: 1 });
  EP.text(ctx, str, { ...o, x: tx, y: yNum, align: rtl ? 'right' : 'left', opacity: a });
  ctx.save();
  ctx.globalAlpha *= a;
  EP.arcArrow(ctx, icx, yNum - 13, 19, -2.5, 1.55, { kind: 'motion', width: 3.6, headSize: 12, dash: dashed ? [7, 5.5] : null });
  ctx.restore();
}

// =====================================================================================
// 9. THE SCENE
// =====================================================================================
export default {
  duration: 22.5,
  captions: CAPTIONS,
  cues: [
    { t: 0.5, sfx: 'motor', dur: 11 },
    { t: K.ticks, sfx: 'tick', gain: -4 },
    // dots appear 11 per second; one blip per group of three (about 3.7 blips per second)
    ...[0, 3, 6, 9, 12, 15, 18].map(k => ({ t: +(dotTime(k) + 0.15).toFixed(3), sfx: 'blip' })),
    ...K.blocks.map(b => ({ t: b + 0.05, sfx: 'pop' })),
    { t: 17.3, sfx: 'whirr', dur: 4.6, rate: FAN.turns, gain: -8 },
    { t: K.strobeOn, sfx: 'click' },
    { t: 19.5, sfx: 'shimmer', dur: 1.8, gain: -6 },
  ],
  math: ['f_s > 2\\,f_{\\max}'],
  music: 'explain',

  setup(EPin) { EP = EPin; balanceCaptions(); allocateLayers(); },

  render(ctx, t, EPin, { W, H }) {
    EP = EPin;
    const { PAL, ease, prog } = EP;
    EP.bg(ctx, W, H);
    const rtl = EP.isRTL();
    const rise = riseAt(t);
    const aP1 = 1 - prog(t, K.p1Out[0], K.p1Out[1], ease.inOutSine);      // part 1 leaves
    const aOut2 = 1 - prog(t, K.p2Out[0], K.p2Out[1], ease.inOutSine);    // part 2 leaves

    // Every group below is drawn as one flat layer and faded as a whole (EP.layer), so that
    // overlapping parts (shaft under the end shield, dots over the curve) never show through.

    // ------------------------------------------------------------------ PART 1
    const aMotor = P(t, K.motor, K.motor + 0.8) * (1 - prog(t, 11.85, 12.35, ease.inOutSine));
    EP.layer(ctx, aMotor, MOTOR.x - 170, MOTOR.y + rise - 60, 320, 150, g => drawMotor(g, MOTOR.x, MOTOR.y + rise, MS, 1));

    EP.layer(ctx, aP1, 90, 262, 1750, 640, g => {                       // box: the badge reaches up to y = 285
      const dim = prog(t, K.dim[0], K.dim[1], ease.inOutSine);
      drawWire(g, t, 1);
      drawAxes(g, t, 1);
      drawGuides(g, t, 1);
      drawTicks(g, t, 1);
      drawReal(g, t, 1, dim);
      drawAlias(g, t, 1);
      drawDots(g, t, 1);
      drawPen(g, t, 1);
      // legend: real, samples, seen (mirrored in right-to-left languages: text hugs the reading-start side)
      const mir = (x, w) => (rtl ? PL.x0 + PL.x1 - (x + w) : x);
      const item = (t0, str, kind, x, y, w, extra = 1) => legendItem(g, { x, y, w, str, kind, a: P(t, t0, t0 + 0.4) * extra, k: P(t, t0, t0 + 0.5) });
      item(K.realLabel, EP.T('s07.real'), 'line', mir(LG.colA, LG.wA), LG.y1, LG.wA, 1 - 0.5 * dim);
      item(K.samplesLabel, EP.T('s07.samples'), 'dot', mir(LG.colA, LG.wA), LG.y2, LG.wA);
      item(K.aliasLabel, EP.T('s07.seen'), 'dash', mir(LG.colB, LG.wB), LG.y1, LG.wB);
      // 900 Hz and 1000 samples per second are an illustration, not a measurement
      EP.badge(g, EP.T('badge.example'), { x: EP.startX(96), y: 306, opacity: P(t, K.realLabel, K.realLabel + 0.5) });
    });

    // ------------------------------------------------------------------ PART 2
    if (t >= K.morph[0] - 0.1) {
      EP.layer(ctx, aOut2, 60, 380, 1800, 560, g => {                    // box down to y = 940: the rule rises from below
        // the first block is the sensor: its frame grows around the box at the end of the move
        const kB = P(t, K.morph[1] - 0.45, K.blocks[0] + 0.15, ease.outCubic);
        if (kB > 0) { g.save(); g.globalAlpha *= kB; blockFrame(g, DG.cx[0], DG.y, kB); g.restore(); }
        const names = ['s07.sensor', 's07.filter', 's07.adc', 's07.controller'];
        for (let i = 0; i < 4; i++) {
          const tb = K.blocks[i];
          const kIn = Pz(t, tb, tb + 0.55, ease.outBack), aIn = P(t, tb, tb + 0.35);
          if (i > 0 && aIn > 0) {
            g.save();
            g.translate(DG.cx[i], DG.y); g.scale(0.9 + 0.1 * kIn, 0.9 + 0.1 * kIn); g.translate(-DG.cx[i], -DG.y);
            EP.layer(g, aIn, DG.cx[i] - DG.w / 2 - 6, DG.y - DG.h / 2 - 6, DG.w + 12, DG.h + 12, h => {
              blockFrame(h, DG.cx[i], DG.y, 1);
              const kI = P(t, tb + 0.15, tb + 0.85, ease.inOutSine);
              if (i === 1) iconFilter(h, DG.cx[i], DG.y - 6, kI);
              if (i === 2) iconADC(h, DG.cx[i], DG.y - 6, kI);
              if (i === 3) iconChip(h, DG.cx[i], DG.y - 2);
            });
            g.restore();
          }
          // label under the block
          const aL = P(t, tb + 0.1, tb + 0.6) * (i === 0 ? P(t, K.morph[1] - 0.2, K.morph[1] + 0.3) : 1);
          if (aL > 0) EP.text(g, EP.T(names[i]), { x: DG.cx[i], y: DG.labelY + (1 - aL) * 8, align: 'center', size: 32, weight: 600, maxWidth: 400, maxLines: 2, shrink: true, opacity: aL });
        }
        // connections with their signal thumbnails
        for (let i = 0; i < 3; i++) {
          const xa = DG.cx[i] + DG.w / 2 + 6, xb = DG.cx[i + 1] - DG.w / 2 - 6, xm = (xa + xb) / 2;
          const t0 = K.blocks[i] + 0.25;
          const kA = P(t, t0, t0 + 0.45, ease.inOutSine);
          if (kA > 0) EP.arrow(g, xa, DG.y, xb, DG.y, { kind: 'motion', color: PAL.field, width: 4.2, progress: kA });
          thumb(g, xm, DG.y, ['raw', 'clean', 'dots'][i], t, P(t, t0 + 0.1, t0 + 0.5));
        }
        // the rule
        const kE = P(t, K.equation[0], K.equation[1], ease.outCubic);
        if (kE > 0) {
          const eq = EP.math(g, 'f_s > 2\\,f_{\\max}', { x: W / 2, y: DG.eqY + (1 - kE) * 14, size: 72, opacity: kE });
          if (eq) {
            g.save();
            g.globalAlpha *= kE;
            g.fillStyle = PAL.highlight;
            const uw = eq.w * kE;
            g.fillRect(W / 2 - uw / 2, eq.y + eq.h + 20, uw, 4);
            g.restore();
          }
        }
      });
    }

    // --------------------------------------------- the sensor: box on the motor -> first block
    {
      const kM = prog(t, K.morph[0], K.morph[1], ease.inOutCubic);
      const aSensor = P(t, K.motor + 0.25, K.motor + 0.9) * aOut2;
      const sx = lerp(SENSOR1.x, SENSOR2.x, kM), sy = lerp(SENSOR1.y + rise, SENSOR2.y, kM), ss = lerp(SENSOR1.s, SENSOR2.s, kM);
      EP.layer(ctx, aSensor, sx - 130, sy - 95, 260, 190, g => {
        drawRipples(g, sx, sy, ss, t, P(t, 1.6, 2.4));
        drawSensor(g, sx, sy, ss, 1, aP1);
      });
      // "Sensor" label: above the box on the motor (it becomes the block label under the box)
      const l1 = P(t, 1.5, 2.0) * (1 - prog(t, K.morph[0], K.morph[0] + 0.35, ease.inOutSine));
      if (l1 > 0) {
        EP.text(ctx, EP.T('s07.sensor'), { x: SENSOR1.x + 6, y: SENSOR1.y - 60 + rise, size: 28, weight: 600, color: PAL.steel, align: 'right', maxWidth: 190, shrink: true, maxLines: 1, opacity: l1 });
      }
    }

    // ------------------------------------------------------------------ PART 3
    if (t >= K.fansIn - 0.05) {
      const aFan = P(t, K.fansIn, K.fansIn + 0.75);
      EP.layer(ctx, aFan, 0, 270, W, 660, g => {
        const kF = prog(t, K.freeze[0], K.freeze[1], ease.inOutSine);
        const apparent = (t - K.freeze[0]) * TAU * FAN.apparent;            // clockwise, 0.25 turns per second
        const age = t - K.strobeOn;
        const pulse = Math.pow(0.5 + 0.5 * Math.cos(TAU * STROBE_HZ_ON_SCREEN * age), 1.6);   // 1.5 pulses per second, smooth
        const aStrobe = Pz(t, K.strobeOn - 0.15, K.strobeOn + 0.35);

        // a hairline between the two situations
        g.save();
        g.strokeStyle = EP.rgba(PAL.steel, 0.11); g.lineWidth = 1.5;
        const mid = Math.round((FV.cxL + FV.cxR) / 2) + 0.5;
        g.beginPath(); g.moveTo(mid, 300); g.lineTo(mid, 910); g.stroke();
        g.restore();

        // left: steady light, the fan is a blur
        drawFanBlur(g, FV.cxL, FV.fanY, FV.R, 1);
        drawFanFrame(g, FV.cxL, FV.fanY, FV.R, 1);
        // right: the same fan; the strobe resolves it
        drawFanBlur(g, FV.cxR, FV.fanY, FV.R, 1 - kF);
        drawFanCrisp(g, FV.cxR, FV.fanY, FV.R, apparent + 0.5, kF);
        drawFanFrame(g, FV.cxR, FV.fanY, FV.R, 1);

        // lamp and its name (a pair, mirrored in Arabic), and the light output over time under it
        const top = (cx, key, rays, kind, a, dy, ring = 0) => {
          if (a <= 0) return;
          EP.layer(g, a, cx - 260, FV.lampY - 90 + dy, 520, 220, h => {
            const o = { size: 34, weight: 600, maxWidth: 230, shrink: true, maxLines: 2 };
            const lw = EP.measure(h, EP.T(key), o).w;
            const pairW = 96 + 14 + lw, left = cx - pairW / 2;
            drawLamp(h, rtl ? left + pairW - 48 : left + 48, FV.lampY + dy, rays, 1, ring);
            EP.text(h, EP.T(key), { ...o, x: rtl ? left + pairW - 110 : left + 110, y: FV.lampY + 4 + dy, anchor: 'middle', align: rtl ? 'right' : 'left' });
            const guard = FV.R * 1.13;                              // the strip is as wide as the guard ring below it
            drawLightWave(h, cx - guard, FV.waveY + dy, 2 * guard, kind, t, 1, rtl ? -1 : 1);
          });
        };
        top(FV.cxL, 's07.normal', 0.82, 'steady', 1, 0);
        top(FV.cxR, 's07.strobe', pulse, 'pulses', aStrobe, (1 - aStrobe) * -10, age >= 0 ? age / 0.6 : 0);

        speedLine(g, FV.cxL, FV.yLabel, FV.yNum, 's07.realspeed', FAN.turns, 0, false, P(t, K.numL, K.numL + 0.55));
        speedLine(g, FV.cxR, FV.yLabel, FV.yNum, 's07.weesee', FAN.apparent, 2, true, P(t, K.numR, K.numR + 0.55));

        EP.badge(g, EP.T('badge.simulated'), { x: EP.startX(96), y: 312 });
        EP.badge(g, EP.T('badge.example'), { x: EP.startX(96), y: 362 });      // 25 turns per second: an example
      });
    }
  },
};
