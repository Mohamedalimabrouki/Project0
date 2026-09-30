/*
 * Scene 06 - "In the real world": a helicopter rotor that looks frozen on
 * video, then a lathe chuck that looks stopped under a flickering lamp.
 *
 * PHYSICS (everything below is drawn from these numbers, nothing by eye)
 *
 *   Main rotor      N = 5 blades, f_r = 6 turns/s
 *                   blade passes f = N f_r = 30 Hz = f_s
 *                   f_a = f - f_s round(f / f_s) = 0            -> frozen
 *                   angle per picture = 360 x 6 / 30 = 72 deg = one blade gap.
 *                   Real-time demo: the blades are drawn at the true angle
 *                   2 pi 6 t in every frame, no blur, no trick.
 *   Tail rotor      N = 2 blades, f_r = 30 turns/s (1800 rpm)
 *                   f = 60 Hz -> f_a = 60 - 30 round(60 / 30) = 0 -> frozen too.
 *                   Seen from directly above the disc is edge-on: the two
 *                   blades project onto the boom as one bar, length 2 r |sin phi|.
 *   Lathe chuck     4 jaws, f_r = 25 turns/s (1500 rpm)
 *                   jaw passes = 4 x 25 = 100 per second = flicker of a lamp on
 *                   50 Hz mains (100 Hz). Each light pulse finds the chuck turned
 *                   by exactly one jaw gap (90 deg), so the jaws look still.
 *                   We cannot show 100 Hz on 30 fps, so that panel is a SIMULATED view.
 *                   Steady light: the picture is the exact time average of the
 *                   turning chuck (built once in setup). It is rotation symmetric,
 *                   so it can never alias on our own 30 fps video.
 *
 * render() is a pure function of t. All tables are made in setup().
 */

const TAU = Math.PI * 2;
const DEG = Math.PI / 180;
const FPS = 30;

const BLADES = 5, ROTOR_RATE = 6;                            // 5 x 6 = 30 blade passes per second
const TAIL_BLADES = 2, TAIL_RATE = 30, TAIL_PHASE = 62 * DEG; // 2 x 30 = 60 = 2 per picture
const JAWS = 4, CHUCK_RATE = 25, MAINS = 50;                 // 4 x 25 = 100 = 2 x 50
const FLICKER = 2 * MAINS;                                   // light peaks per second
const SLOW = 50;                                             // the lamp graph is shown 50 times slower

/** True main rotor angle (clock angle, radians) at time t. Exported for the frame-step check. */
export const rotorAngle = t => TAU * ROTOR_RATE * t;
export const tailAngle = t => TAIL_PHASE + TAU * TAIL_RATE * t;
export const PHYSICS = { BLADES, ROTOR_RATE, TAIL_BLADES, TAIL_RATE, JAWS, CHUCK_RATE, MAINS, FLICKER, SLOW, FPS };

// ------------------------------------------------------------ engine access
// The stage hands us EP in setup() and render(); helpers below share it.
let EP = null, PAL, SHADE, rgba, mix, clamp, ease, prog, win, wrap;
function init(E) {
  if (EP === E) return;
  EP = E;
  ({ PAL, SHADE, rgba, mix, clamp, ease, prog, win, wrap } = E);
}

// ------------------------------------------------------------ layout
const HELI = { x: 600, y: 606, R: 256 };            // rotor mast (px) and rotor radius
const TEXT_X = { ltr: 1136, rtl: 1812 };            // start edge of the rotor equation block

const PANEL = { w: 660, h: 448, top: 474 };
const COL = { left: 240, right: 1020 };             // panel left edges (right panel = 1020 .. 1680)

// ============================================================================
//  HELICOPTER (top view, nose up). Local frame: origin = rotor mast, x right,
//  y down, unit = px. Fixed light from the top left, as for the wheel and car.
// ============================================================================
function drawSkids(ctx, R) {
  ctx.save();
  ctx.lineCap = 'round';
  for (const s of [-1, 1]) {
    const x = s * 0.228 * R;
    ctx.strokeStyle = SHADE.steelDark;
    ctx.lineWidth = 0.015 * R;
    for (const v of [-0.19, 0.12]) { ctx.beginPath(); ctx.moveTo(x, v * R); ctx.lineTo(s * 0.15 * R, v * R); ctx.stroke(); }
    ctx.strokeStyle = SHADE.steelMid;
    ctx.lineWidth = 0.026 * R;
    ctx.beginPath();
    ctx.moveTo(x - s * 0.028 * R, -0.425 * R);
    ctx.quadraticCurveTo(x, -0.40 * R, x, -0.335 * R);
    ctx.lineTo(x, 0.30 * R);
    ctx.stroke();
    ctx.strokeStyle = rgba(PAL.paper, 0.32);
    ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.moveTo(x - 0.008 * R, -0.33 * R); ctx.lineTo(x - 0.008 * R, 0.30 * R); ctx.stroke();
  }
  ctx.restore();
}

function fusePath(R) {
  const S = (a, b) => [a * R, b * R];
  const p = new Path2D();
  p.moveTo(...S(0, -0.56));
  p.bezierCurveTo(...S(0.095, -0.56), ...S(0.172, -0.45), ...S(0.180, -0.28));
  p.bezierCurveTo(...S(0.188, -0.12), ...S(0.182, 0.06), ...S(0.162, 0.19));
  p.bezierCurveTo(...S(0.146, 0.29), ...S(0.100, 0.345), ...S(0.070, 0.40));
  p.lineTo(...S(-0.070, 0.40));
  p.bezierCurveTo(...S(-0.100, 0.345), ...S(-0.146, 0.29), ...S(-0.162, 0.19));
  p.bezierCurveTo(...S(-0.182, 0.06), ...S(-0.188, -0.12), ...S(-0.180, -0.28));
  p.bezierCurveTo(...S(-0.172, -0.45), ...S(-0.095, -0.56), ...S(0, -0.56));
  p.closePath();
  return p;
}

function drawTail(ctx, R, t) {
  const S = (a, b) => [a * R, b * R];
  ctx.save();
  // boom: a slim cone, lit from the left
  const boom = new Path2D();
  boom.moveTo(...S(-0.064, 0.34)); boom.lineTo(...S(0.064, 0.34));
  boom.lineTo(...S(0.027, 1.0));
  boom.quadraticCurveTo(...S(0.02, 1.075), ...S(0, 1.092));
  boom.quadraticCurveTo(...S(-0.02, 1.075), ...S(-0.027, 1.0));
  boom.closePath();
  const gb = ctx.createLinearGradient(-0.064 * R, 0, 0.064 * R, 0);
  gb.addColorStop(0, SHADE.steelLight); gb.addColorStop(0.42, PAL.steel); gb.addColorStop(1, SHADE.steelMid);
  ctx.fillStyle = gb; ctx.fill(boom);
  ctx.strokeStyle = rgba(PAL.ink, 0.30); ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(...S(0, 0.42)); ctx.lineTo(...S(0, 0.79)); ctx.stroke();
  ctx.strokeStyle = rgba(PAL.ink, 0.28);
  ctx.stroke(boom);

  // horizontal stabiliser (ahead of the tail rotor), swept back, small end plates
  const st = new Path2D();
  st.moveTo(...S(-0.034, 0.620)); st.lineTo(...S(-0.215, 0.652)); st.lineTo(...S(-0.215, 0.708)); st.lineTo(...S(-0.034, 0.694));
  st.lineTo(...S(0.034, 0.694)); st.lineTo(...S(0.215, 0.708)); st.lineTo(...S(0.215, 0.652)); st.lineTo(...S(0.034, 0.620));
  st.closePath();
  const gs = ctx.createLinearGradient(-0.215 * R, 0, 0.215 * R, 0);
  gs.addColorStop(0, SHADE.steelLight); gs.addColorStop(0.5, PAL.steel); gs.addColorStop(1, SHADE.steelMid);
  ctx.fillStyle = gs; ctx.fill(st);
  ctx.strokeStyle = rgba(PAL.paper, 0.20); ctx.lineWidth = 1; ctx.stroke(st);
  ctx.fillStyle = SHADE.steelDark;
  ctx.fillRect(0.208 * R, 0.634 * R, 0.014 * R, 0.088 * R);
  ctx.fillRect(-0.222 * R, 0.634 * R, 0.014 * R, 0.088 * R);

  // vertical fin seen edge-on: a lighter strip on the centre line of the boom's end
  const fin = new Path2D();
  fin.moveTo(...S(-0.012, 0.80)); fin.lineTo(...S(0.012, 0.80)); fin.lineTo(...S(0.010, 1.06));
  fin.quadraticCurveTo(...S(0, 1.078), ...S(-0.010, 1.06)); fin.closePath();
  ctx.fillStyle = mix(PAL.steel, PAL.paper, 0.32); ctx.fill(fin);
  ctx.strokeStyle = rgba(PAL.ink, 0.30); ctx.lineWidth = 1; ctx.stroke(fin);

  // tail rotor: gearbox on the left of the fin, hub, two blades
  const hx = -0.064 * R, hy = 0.945 * R;
  ctx.fillStyle = SHADE.steelDark;
  EP.roundRect(ctx, hx - 0.012 * R, hy - 0.02 * R, 0.058 * R, 0.04 * R, 0.012 * R); ctx.fill();
  // Two blades, true angle every frame. The disc is edge-on from above, so a
  // blade at angle phi from the vertical reaches r sin(phi) along the boom.
  const phi = wrap(tailAngle(t), TAU), rt = 0.15;
  ctx.lineCap = 'round';
  ctx.strokeStyle = mix(PAL.steel, PAL.ink, 0.12); ctx.lineWidth = 0.019 * R;
  for (let i = 0; i < TAIL_BLADES; i++) {
    const along = rt * R * Math.sin(phi + (i * TAU) / TAIL_BLADES);
    ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx, hy + along); ctx.stroke();
  }
  ctx.fillStyle = SHADE.steelLight;
  ctx.beginPath(); ctx.arc(hx, hy, 0.016 * R, 0, TAU); ctx.fill();
  ctx.restore();
}

function drawFuselage(ctx, R) {
  const S = (a, b) => [a * R, b * R];
  const body = fusePath(R);
  ctx.save();
  // body shading: lit from the top left
  const g = ctx.createLinearGradient(-0.18 * R, -0.27 * R, 0.18 * R, 0.27 * R);
  g.addColorStop(0, SHADE.steelLight); g.addColorStop(0.45, PAL.steel); g.addColorStop(1, SHADE.steelMid);
  ctx.fillStyle = g; ctx.fill(body);

  ctx.save();
  ctx.clip(body);
  // engine deck: two cowling doors with vents
  for (const s of [-1, 1]) {
    ctx.fillStyle = rgba(PAL.ink, 0.10);
    EP.roundRect(ctx, (s > 0 ? 0.016 : -0.138) * R, 0.04 * R, 0.122 * R, 0.31 * R, 0.035 * R); ctx.fill();
    ctx.strokeStyle = rgba(PAL.ink, 0.30); ctx.lineWidth = 1.1; ctx.stroke();
    ctx.strokeStyle = rgba(PAL.ink, 0.36); ctx.lineWidth = 1.2;
    for (let k = 0; k < 4; k++) {
      const v = (0.15 + k * 0.05) * R;
      ctx.beginPath(); ctx.moveTo(s * 0.045 * R, v); ctx.lineTo(s * 0.118 * R, v); ctx.stroke();
    }
  }
  // roof panel
  ctx.fillStyle = rgba(PAL.paper, 0.05);
  EP.roundRect(ctx, -0.128 * R, -0.175 * R, 0.256 * R, 0.19 * R, 0.055 * R); ctx.fill();
  ctx.strokeStyle = rgba(PAL.ink, 0.28); ctx.lineWidth = 1.1; ctx.stroke();

  // windscreen: dark glass with a soft reflection
  const glass = new Path2D();
  glass.moveTo(...S(-0.134, -0.215));
  glass.bezierCurveTo(...S(-0.142, -0.33), ...S(-0.114, -0.44), ...S(0, -0.49));
  glass.bezierCurveTo(...S(0.114, -0.44), ...S(0.142, -0.33), ...S(0.134, -0.215));
  glass.bezierCurveTo(...S(0.068, -0.19), ...S(-0.068, -0.19), ...S(-0.134, -0.215));
  glass.closePath();
  ctx.fillStyle = mix(PAL.ink, PAL.steel, 0.17); ctx.fill(glass);
  const gg = ctx.createLinearGradient(-0.14 * R, -0.47 * R, 0.07 * R, -0.2 * R);
  gg.addColorStop(0, rgba(PAL.paper, 0.30)); gg.addColorStop(0.55, rgba(PAL.paper, 0.05)); gg.addColorStop(1, rgba(PAL.paper, 0));
  ctx.fillStyle = gg; ctx.fill(glass);
  ctx.strokeStyle = rgba(PAL.ink, 0.55); ctx.lineWidth = 1.4; ctx.stroke(glass);

  // fixed light from the top left: a soft sheen over the whole cabin
  const sh = ctx.createRadialGradient(-0.08 * R, -0.31 * R, 0.02 * R, -0.03 * R, -0.13 * R, 0.46 * R);
  sh.addColorStop(0, rgba(PAL.paper, 0.15)); sh.addColorStop(1, rgba(PAL.paper, 0));
  ctx.fillStyle = sh; ctx.fillRect(-0.22 * R, -0.6 * R, 0.44 * R, 1.1 * R);
  ctx.restore();

  // exhaust and the mast fairing under the hub
  ctx.fillStyle = SHADE.inkDeep;
  ctx.beginPath(); ctx.ellipse(0, 0.365 * R, 0.028 * R, 0.015 * R, 0, 0, TAU); ctx.fill();
  const mg = ctx.createRadialGradient(-0.02 * R, -0.02 * R, 0.005 * R, 0, 0, 0.09 * R);
  mg.addColorStop(0, SHADE.steelLight); mg.addColorStop(1, SHADE.steelMid);
  ctx.fillStyle = mg; ctx.beginPath(); ctx.arc(0, 0, 0.09 * R, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(PAL.paper, 0.20); ctx.lineWidth = 1; ctx.stroke();

  ctx.strokeStyle = rgba(PAL.paper, 0.24); ctx.lineWidth = 1.3; ctx.stroke(body);
  ctx.restore();
}

function bladePath(wr, wt, r0, r1, rc) {
  const p = new Path2D();
  p.moveTo(-wr / 2, -r0);
  p.lineTo(-wt / 2, -r1 + rc);
  p.quadraticCurveTo(-wt / 2, -r1, -wt / 2 + rc, -r1);
  p.lineTo(wt / 2 - rc, -r1);
  p.quadraticCurveTo(wt / 2, -r1, wt / 2, -r1 + rc);
  p.lineTo(wr / 2, -r0);
  p.closePath();
  return p;
}

/**
 * Main rotor at the TRUE angle. Every blade is drawn in its own frame, so the
 * picture repeats exactly every 72 degrees: at 6 turns/s and 30 pictures/s
 * every picture is identical, as it really is.
 */
function drawRotor(ctx, R, ang) {
  const wr = 0.064 * R, wt = 0.054 * R, r0 = 0.05 * R, r1 = R, rc = 0.02 * R;
  const blade = bladePath(wr, wt, r0, r1, rc);
  const grad = ctx.createLinearGradient(-wr / 2, 0, wr / 2, 0);   // leading edge (turning clockwise) on the right
  grad.addColorStop(0, SHADE.steelMid); grad.addColorStop(0.45, PAL.steel);
  grad.addColorStop(0.85, SHADE.steelLight); grad.addColorStop(1, PAL.steel);
  const tip = mix(PAL.steel, PAL.paper, 0.78);
  // The rotor looks the same after one blade gap, so only the angle inside one gap matters. Reducing the
  // TRUE angle modulo the gap (exactly) keeps the rotation numbers small: the canvas stores them as 32-bit
  // floats, and a large angle would round differently from picture to picture.
  const gap = TAU / BLADES;
  const phase = ang - gap * Math.round(ang / gap);
  ctx.save();
  ctx.lineJoin = 'round';
  for (let i = 0; i < BLADES; i++) {
    ctx.save();
    ctx.rotate(phase + i * gap);
    // blade grip (dark lug at the root)
    ctx.fillStyle = SHADE.steelDark;
    EP.roundRect(ctx, -0.034 * R, -0.155 * R, 0.068 * R, 0.16 * R, 0.02 * R); ctx.fill();
    ctx.strokeStyle = rgba(PAL.paper, 0.18); ctx.lineWidth = 1; ctx.stroke();
    // blade
    ctx.fillStyle = grad; ctx.fill(blade);
    ctx.save();
    ctx.clip(blade);
    ctx.fillStyle = rgba(PAL.ink, 0.34); ctx.fillRect(-wr, -0.215 * R, wr * 2, 0.06 * R);   // root cuff
    ctx.fillStyle = tip; ctx.fillRect(-wr, -r1, wr * 2, 0.062 * R);                          // tip band
    ctx.restore();
    ctx.strokeStyle = rgba(PAL.paper, 0.30); ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(wr / 2, -r0 - 0.1 * R); ctx.lineTo(wt / 2, -r1 + rc); ctx.stroke();
    ctx.restore();
  }
  // hub and mast nut
  const hg = ctx.createRadialGradient(-0.02 * R, -0.02 * R, 0.005 * R, 0, 0, 0.078 * R);
  hg.addColorStop(0, SHADE.steelLight); hg.addColorStop(1, SHADE.steelMid);
  ctx.fillStyle = hg; ctx.beginPath(); ctx.arc(0, 0, 0.078 * R, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(PAL.paper, 0.26); ctx.lineWidth = 1.2; ctx.stroke();
  ctx.fillStyle = SHADE.steelDark; ctx.beginPath(); ctx.arc(0, 0, 0.032 * R, 0, TAU); ctx.fill();
  ctx.fillStyle = SHADE.steelLight; ctx.beginPath(); ctx.arc(-0.004 * R, -0.004 * R, 0.017 * R, 0, TAU); ctx.fill();
  ctx.restore();
}

/** Yellow marker on the tip of blade 0: it lands on the next tip every picture. */
function drawMarker(ctx, R, ang, a) {
  if (a <= 0) return;
  const [mx, my] = EP.polar(0, 0, R * 0.962, ang);
  ctx.save();
  ctx.globalAlpha *= clamp(a);
  ctx.fillStyle = rgba(PAL.ink, 0.85);
  ctx.beginPath(); ctx.arc(mx, my, 12.5, 0, TAU); ctx.fill();
  ctx.fillStyle = PAL.highlight;
  ctx.beginPath(); ctx.arc(mx, my, 9.5, 0, TAU); ctx.fill();
  ctx.restore();
}

/** Faint circular downwash under the rotor (air = sky blue). Slow, calm, very subtle. */
function drawDownwash(ctx, R, t, a) {
  if (a <= 0) return;
  ctx.save();
  ctx.globalAlpha *= clamp(a);
  const g = ctx.createRadialGradient(0, 0, R * 0.3, 0, 0, R * 1.3);
  g.addColorStop(0, rgba(PAL.fluid, 0));
  g.addColorStop(0.55, rgba(PAL.fluid, 0.040));
  g.addColorStop(0.78, rgba(PAL.fluid, 0.075));
  g.addColorStop(1, rgba(PAL.fluid, 0));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, R * 1.3, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(PAL.fluid, 0.20); ctx.lineWidth = 1.6;
  ctx.beginPath(); ctx.arc(0, 0, R * 1.03, 0, TAU); ctx.stroke();
  for (let k = 0; k < 2; k++) {
    const ph = wrap(t / 3.8 + k * 0.5, 1);
    ctx.strokeStyle = rgba(PAL.fluid, 0.15 * Math.pow(1 - ph, 1.6));
    ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.arc(0, 0, R * (1.03 + 0.30 * ease.outQuad(ph)), 0, TAU); ctx.stroke();
  }
  ctx.restore();
}

/** The whole helicopter at time t. Origin = rotor mast. */
function drawHelicopter(ctx, t, R, markerAlpha) {
  drawSkids(ctx, R);
  drawTail(ctx, R, t);
  drawFuselage(ctx, R);
  const ang = rotorAngle(t);
  drawRotor(ctx, R, ang);
  drawMarker(ctx, R, ang, markerAlpha);
}

/** Slow, smooth hover: translation and a whisper of scale (never a turn: the rotor must keep its true angle). */
function hover(t) {
  return {
    dx: 5.0 * Math.sin(TAU * 0.11 * t + 0.6) + 2.2 * Math.sin(TAU * 0.27 * t + 2.0),
    dy: 3.6 * Math.sin(TAU * 0.15 * t + 1.3) + 1.8 * Math.sin(TAU * 0.33 * t + 0.2),
    s: 1 + 0.004 * Math.sin(TAU * 0.21 * t + 0.9),
  };
}

// ============================================================================
//  SMALL HELPERS
// ============================================================================
/** Debug switches for my own checks (toggled from a test page, never used in the film). */
export const DEBUG = { noHover: false, noDownwash: false };

/**
 * Draw fn() as one group and fade the group as a whole, so overlapping parts
 * (blades over the cabin) do not show through each other while it fades.
 * box = {x, y, w, h} in the current user space.
 */
let _grp = null;
function withAlpha(ctx, box, a, fn) {
  if (a <= 0.001) return;
  if (a >= 0.999) { fn(ctx); return; }
  const m = ctx.getTransform();
  const sc = Math.hypot(m.a, m.b);
  const w = Math.ceil(box.w * sc), h = Math.ceil(box.h * sc);
  if (!_grp) _grp = document.createElement('canvas');
  if (_grp.width < w || _grp.height < h) { _grp.width = Math.max(_grp.width, w); _grp.height = Math.max(_grp.height, h); }
  const g = _grp.getContext('2d');
  g.setTransform(1, 0, 0, 1, 0, 0);
  g.clearRect(0, 0, _grp.width, _grp.height);
  g.setTransform(sc, 0, 0, sc, -box.x * sc, -box.y * sc);
  fn(g);
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(_grp, 0, 0, w, h, box.x, box.y, w / sc, h / sc);
  ctx.restore();
}

/**
 * One line of text with one token (for example "100") in a second colour.
 * Start-aligned like EP.text (left edge in English and French, right edge in
 * Arabic); align 'center' centres it. The line is shrunk to maxWidth. When the
 * token is not found the line is drawn in one colour. Returns {w, size}.
 */
function rowHi(ctx, str, o) {
  const { x, y, size = 28, weight = 500, color = PAL.paper, hi = null, hiColor = PAL.highlight, hiWeight = 700, opacity = 1, maxWidth = 0, align = 'start', draw = true } = o;
  const rtl = EP.isRTL();
  let sz = size;
  const whole = () => EP.measure(ctx, str, { size: sz, weight }).w;
  let w = whole();
  if (maxWidth && w > maxWidth) { sz = size * (maxWidth / w) * 0.99; w = whole(); }
  const i = hi ? str.indexOf(hi) : -1;
  const segs = i < 0 ? [[str, color, weight]] : [[str.slice(0, i), color, weight], [hi, hiColor, hiWeight], [str.slice(i + hi.length), color, weight]];
  const widths = segs.map(([s, , wt]) => (s ? EP.measure(ctx, s, { size: sz, weight: wt }).w : 0));
  const total = widths.reduce((a, b) => a + b, 0);
  if (!draw) return { w: total, size: sz };
  // the edge where reading starts
  let edge;
  if (align === 'center') edge = rtl ? x + total / 2 : x - total / 2;
  else if (align === 'end') edge = rtl ? x + total : x - total;
  else edge = x;
  let cur = edge;
  segs.forEach(([s, col, wt], k) => {
    if (s) EP.text(ctx, s, { x: cur, y, size: sz, weight: wt, color: col, opacity, align: rtl ? 'right' : 'left' });
    cur += rtl ? -widths[k] : widths[k];
  });
  return { w: total, size: sz };
}

/** A panel on the background: slightly lifted ink, thin steel border. */
function drawPanel(ctx, x, y, w, h, a, look = 0) {
  if (a <= 0) return;
  ctx.save();
  ctx.globalAlpha *= clamp(a);
  EP.roundRect(ctx, x, y, w, h, 16);
  ctx.fillStyle = rgba(SHADE.inkLift, 0.94); ctx.fill();
  // look: 0..1 turns the thin border towards yellow ("look here")
  ctx.lineWidth = 1.5 + 0.8 * look;
  ctx.strokeStyle = rgba(mix(PAL.steel, PAL.highlight, look), 0.34 + 0.34 * look);
  ctx.stroke();
  ctx.restore();
}

/**
 * Workshop pendant lamp (line icon). (x, y) = top of the cord, height about
 * 84 px. The glow is CONSTANT: a lamp icon never flashes. The flicker lives in
 * the graph next to it.
 */
function drawLamp(ctx, x, y, a) {
  if (a <= 0) return;
  ctx.save();
  ctx.translate(x, y);
  withAlpha(ctx, { x: -62, y: -8, w: 124, h: 134 }, clamp(a), drawLampBody);
  ctx.restore();
}
function drawLampBody(ctx) {
  ctx.save();
  const g = ctx.createRadialGradient(0, 60, 3, 0, 60, 58);
  g.addColorStop(0, rgba(PAL.energy, 0.50)); g.addColorStop(0.4, rgba(PAL.energy, 0.16)); g.addColorStop(1, rgba(PAL.energy, 0));
  ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 60, 58, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(PAL.steel, 0.9); ctx.lineWidth = 2.5; ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(0, -4); ctx.lineTo(0, 14); ctx.stroke();
  // bulb, then the shade over its top
  ctx.fillStyle = PAL.energy; ctx.beginPath(); ctx.arc(0, 57, 11, 0, TAU); ctx.fill();
  ctx.fillStyle = rgba(PAL.paper, 0.40); ctx.beginPath(); ctx.arc(-3.5, 54, 3.4, 0, TAU); ctx.fill();
  const shade = new Path2D();
  shade.moveTo(-9, 13); shade.lineTo(9, 13);
  shade.bezierCurveTo(20, 19, 30, 34, 35, 50); shade.lineTo(-35, 50);
  shade.bezierCurveTo(-30, 34, -20, 19, -9, 13); shade.closePath();
  const gs = ctx.createLinearGradient(-35, 13, 35, 50);
  gs.addColorStop(0, SHADE.steelLight); gs.addColorStop(0.5, PAL.steel); gs.addColorStop(1, SHADE.steelMid);
  ctx.fillStyle = gs; ctx.fill(shade);
  ctx.strokeStyle = rgba(PAL.paper, 0.28); ctx.lineWidth = 1.2; ctx.stroke(shade);
  ctx.fillStyle = SHADE.steelDark; EP.roundRect(ctx, -36, 48, 72, 5, 2.5); ctx.fill();
  ctx.restore();
}

/**
 * Light output of the lamp, in orange (energy). k = flicker depth 0..1:
 *   0  steady light (a flat line at the average level)
 *   1  |sin(2 pi 50 s)|: 100 peaks per real second (full-wave, mains at 50 Hz)
 * Same average level for every k, so it is the same amount of light. The trace
 * scrolls SLOW times slower than reality (9 peaks in the window), the yellow dot
 * is "now". Returns nothing; draws inside the box x, y, w, h.
 */
function drawGraph(ctx, o) {
  const { x, y, w, h, t, k, a } = o;
  if (a <= 0) return;
  const base = y + h, top = y + 8, mean = 2 / Math.PI;
  const xc = x + w / 2;
  const pxPerS = w / (9 / FLICKER);                    // pixels per REAL second
  const level = s => mean + k * (Math.abs(Math.sin(TAU * MAINS * s)) - mean);
  const yy = v => base - v * (base - top);
  ctx.save();
  ctx.globalAlpha *= clamp(a);
  // axes
  ctx.strokeStyle = rgba(PAL.steel, 0.6); ctx.lineWidth = 1.6; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x, base); ctx.lineTo(x + w, base); ctx.stroke();
  // trace, fading out at both ends
  const tau = t / SLOW;
  const pts = [];
  for (let px = x + 2; px <= x + w; px += 2) pts.push([px, yy(level(tau + (px - xc) / pxPerS))]);
  const fade = ctx.createLinearGradient(x, 0, x + w, 0);
  fade.addColorStop(0, rgba(PAL.energy, 0)); fade.addColorStop(0.10, rgba(PAL.energy, 1));
  fade.addColorStop(0.90, rgba(PAL.energy, 1)); fade.addColorStop(1, rgba(PAL.energy, 0));
  const fill = ctx.createLinearGradient(x, 0, x + w, 0);
  fill.addColorStop(0, rgba(PAL.energy, 0)); fill.addColorStop(0.10, rgba(PAL.energy, 0.14));
  fill.addColorStop(0.90, rgba(PAL.energy, 0.14)); fill.addColorStop(1, rgba(PAL.energy, 0));
  ctx.beginPath();
  ctx.moveTo(pts[0][0], base);
  for (const [px, py] of pts) ctx.lineTo(px, py);
  ctx.lineTo(pts[pts.length - 1][0], base);
  ctx.closePath();
  ctx.fillStyle = fill; ctx.fill();
  ctx.beginPath();
  pts.forEach(([px, py], i) => (i ? ctx.lineTo(px, py) : ctx.moveTo(px, py)));
  ctx.strokeStyle = fade; ctx.lineWidth = 3.4; ctx.stroke();
  // average level, dotted, and the "now" dot riding the trace
  if (k > 0.02) {
    ctx.save();
    ctx.globalAlpha *= clamp(k);
    ctx.setLineDash([2, 7]); ctx.strokeStyle = rgba(PAL.steel, 0.55); ctx.lineWidth = 1.4;
    ctx.beginPath(); ctx.moveTo(x + 6, yy(mean)); ctx.lineTo(x + w - 6, yy(mean)); ctx.stroke();
    ctx.setLineDash([]);
    const ny = yy(level(tau));
    ctx.strokeStyle = rgba(PAL.highlight, 0.30); ctx.lineWidth = 1.4; ctx.setLineDash([3, 4]);
    ctx.beginPath(); ctx.moveTo(xc, ny); ctx.lineTo(xc, base); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = rgba(PAL.ink, 0.9); ctx.beginPath(); ctx.arc(xc, ny, 9, 0, TAU); ctx.fill();
    ctx.fillStyle = PAL.highlight; ctx.beginPath(); ctx.arc(xc, ny, 6.2, 0, TAU); ctx.fill();
    ctx.restore();
  }
  ctx.restore();
}

/** Warning triangle, yellow outline ("look here"), rounded corners, exclamation mark. */
function drawWarning(ctx, x, y, s, a) {
  if (a <= 0) return;
  ctx.save();
  ctx.translate(x, y); ctx.scale(s, s);
  ctx.globalAlpha *= clamp(a);
  const pts = [[0, -37], [41, 33], [-41, 33]], n = 3, r = 10;
  ctx.beginPath();
  ctx.moveTo((pts[n - 1][0] + pts[0][0]) / 2, (pts[n - 1][1] + pts[0][1]) / 2);
  for (let i = 0; i < n; i++) { const p = pts[i], q = pts[(i + 1) % n]; ctx.arcTo(p[0], p[1], q[0], q[1], r); }
  ctx.closePath();
  ctx.fillStyle = rgba(PAL.ink, 0.90); ctx.fill();
  ctx.lineJoin = 'round'; ctx.lineWidth = 5; ctx.strokeStyle = PAL.highlight; ctx.stroke();
  ctx.lineCap = 'round'; ctx.lineWidth = 6; ctx.strokeStyle = PAL.highlight;
  ctx.beginPath(); ctx.moveTo(0, -13); ctx.lineTo(0, 6); ctx.stroke();
  ctx.fillStyle = PAL.highlight; ctx.beginPath(); ctx.arc(0, 19, 3.8, 0, TAU); ctx.fill();
  ctx.restore();
}

// ============================================================================
//  LATHE CHUCK (face-on): round body, 4 radial jaws, a round bar in the centre.
//  Everything is 4-fold symmetric, so the picture repeats every 90 degrees:
//  that is why a light pulsing once per jaw pass shows it still.
// ============================================================================
const CHUCK_R = 148;

/** One jaw pointing up (radial direction = -y): concave grip, step, body. */
function jawPath(R) {
  const g = 0.080 * R, s = 0.104 * R, b = 0.122 * R, rc = 0.03 * R;
  const r0 = 0.225 * R, r1 = 0.355 * R, r2 = 0.50 * R, r3 = 0.885 * R;
  const yg = Math.sqrt(r0 * r0 - g * g);
  const p = new Path2D();
  p.moveTo(-g, -yg);
  p.arc(0, 0, r0, Math.atan2(-yg, -g), Math.atan2(-yg, g), false);   // concave tip: follows the bar
  p.lineTo(g, -r1); p.lineTo(s, -r1); p.lineTo(s, -r2); p.lineTo(b, -r2);
  p.lineTo(b, -r3 + rc); p.quadraticCurveTo(b, -r3, b - rc, -r3);
  p.lineTo(-b + rc, -r3); p.quadraticCurveTo(-b, -r3, -b, -r3 + rc);
  p.lineTo(-b, -r2); p.lineTo(-s, -r2); p.lineTo(-s, -r1); p.lineTo(-g, -r1);
  p.closePath();
  return p;
}

function hexPath(ctx, r) {
  ctx.beginPath();
  for (let i = 0; i < 6; i++) { const a = (i * TAU) / 6 + Math.PI / 6; i ? ctx.lineTo(r * Math.cos(a), r * Math.sin(a)) : ctx.moveTo(r * Math.cos(a), r * Math.sin(a)); }
  ctx.closePath();
}

/**
 * The chuck at rotation ang (clock angle) and radius R, centred on the origin.
 * sheen: the fixed light from the top left (drawn in the screen frame, so it
 * does not turn with the chuck). The blur is built without it.
 */
function drawChuck(ctx, R, ang, o = {}) {
  const { sheen = true } = o;
  ctx.save();
  ctx.lineJoin = 'round';
  // body: dark cast steel, chamfered rim, raised face
  ctx.fillStyle = mix(PAL.steel, PAL.ink, 0.70); ctx.beginPath(); ctx.arc(0, 0, R, 0, TAU); ctx.fill();
  ctx.fillStyle = SHADE.steelMid;
  ctx.beginPath(); ctx.arc(0, 0, R, 0, TAU); ctx.moveTo(0.925 * R, 0); ctx.arc(0, 0, 0.925 * R, 0, TAU, true); ctx.fill();
  ctx.fillStyle = mix(PAL.steel, PAL.ink, 0.62); ctx.beginPath(); ctx.arc(0, 0, 0.925 * R, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(PAL.ink, 0.55); ctx.lineWidth = 0.014 * R;
  ctx.beginPath(); ctx.arc(0, 0, 0.905 * R, 0, TAU); ctx.stroke();
  ctx.strokeStyle = rgba(PAL.paper, 0.10); ctx.lineWidth = 0.008 * R;
  ctx.beginPath(); ctx.arc(0, 0, 0.918 * R, 0, TAU); ctx.stroke();

  ctx.rotate(ang);
  // key sockets on the rim, slots for the jaws
  for (let k = 0; k < JAWS; k++) {
    ctx.save();
    ctx.rotate((k * TAU) / JAWS);
    ctx.fillStyle = SHADE.inkDeep;
    ctx.fillRect(-0.032 * R, -0.985 * R, 0.064 * R, 0.05 * R);
    ctx.strokeStyle = rgba(PAL.paper, 0.22); ctx.lineWidth = 1; ctx.strokeRect(-0.032 * R, -0.985 * R, 0.064 * R, 0.05 * R);
    EP.roundRect(ctx, -0.14 * R, -0.905 * R, 0.28 * R, 0.775 * R, 0.02 * R);
    ctx.fillStyle = SHADE.inkDeep; ctx.fill();
    ctx.strokeStyle = rgba(PAL.paper, 0.10); ctx.lineWidth = 1; ctx.stroke();
    ctx.restore();
  }
  // cap screws between the jaws (at 45 degrees)
  for (const [rr, sr, hr] of [[0.70, 0.056, 0.026], [0.47, 0.037, 0.017]]) {
    for (let k = 0; k < JAWS; k++) {
      const a = ((k + 0.5) * TAU) / JAWS;
      ctx.save();
      ctx.translate(rr * R * Math.sin(a), -rr * R * Math.cos(a));
      const gs = ctx.createRadialGradient(-sr * R * 0.3, -sr * R * 0.3, 0, 0, 0, sr * R);
      gs.addColorStop(0, SHADE.steelLight); gs.addColorStop(1, SHADE.steelMid);
      ctx.fillStyle = gs; ctx.beginPath(); ctx.arc(0, 0, sr * R, 0, TAU); ctx.fill();
      ctx.strokeStyle = rgba(PAL.ink, 0.5); ctx.lineWidth = 1; ctx.stroke();
      ctx.fillStyle = SHADE.inkDeep; hexPath(ctx, hr * R); ctx.fill();
      ctx.restore();
    }
  }
  // jaws, each lit from the top left in screen space
  const jaw = jawPath(R);
  for (let k = 0; k < JAWS; k++) {
    const th = ang + (k * TAU) / JAWS;                    // where this jaw points on screen
    const lx = -Math.SQRT1_2, ly = -Math.SQRT1_2;         // direction TO the light, in screen space
    const ux = lx * Math.cos(th) + ly * Math.sin(th);     // the same direction in the jaw's own frame
    const uy = -lx * Math.sin(th) + ly * Math.cos(th);
    ctx.save();
    ctx.rotate((k * TAU) / JAWS);
    ctx.lineWidth = 0.022 * R; ctx.strokeStyle = rgba(SHADE.inkDeep, 0.7); ctx.stroke(jaw);
    const gj = ctx.createLinearGradient(ux * 0.11 * R, uy * 0.11 * R, -ux * 0.11 * R, -uy * 0.11 * R);
    gj.addColorStop(0, SHADE.steelLight); gj.addColorStop(0.5, PAL.steel); gj.addColorStop(1, SHADE.steelMid);
    ctx.fillStyle = gj; ctx.fill(jaw);
    ctx.lineWidth = 1; ctx.strokeStyle = rgba(PAL.paper, 0.26); ctx.stroke(jaw);
    // grip serrations, screw line, screw head
    ctx.strokeStyle = rgba(PAL.ink, 0.38); ctx.lineWidth = 0.007 * R;
    for (const rr of [0.26, 0.295, 0.33]) { ctx.beginPath(); ctx.moveTo(-0.072 * R, -rr * R); ctx.lineTo(0.072 * R, -rr * R); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(0, -0.53 * R); ctx.lineTo(0, -0.86 * R); ctx.stroke();
    ctx.fillStyle = SHADE.steelMid; ctx.beginPath(); ctx.arc(0, -0.74 * R, 0.05 * R, 0, TAU); ctx.fill();
    ctx.strokeStyle = rgba(PAL.ink, 0.5); ctx.lineWidth = 1; ctx.stroke();
    ctx.fillStyle = SHADE.inkDeep; ctx.fillRect(-0.02 * R, -0.74 * R - 0.02 * R, 0.04 * R, 0.04 * R);
    ctx.restore();
  }
  // the workpiece: a round bar held by the jaws, a turned end face
  const br = 0.24 * R;
  const gb = ctx.createRadialGradient(0, 0, 0, 0, 0, br);
  gb.addColorStop(0, SHADE.steelLight); gb.addColorStop(0.55, PAL.steel); gb.addColorStop(0.92, SHADE.steelMid); gb.addColorStop(1, SHADE.steelDark);
  ctx.fillStyle = gb; ctx.beginPath(); ctx.arc(0, 0, br, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(SHADE.inkDeep, 0.65); ctx.lineWidth = 0.014 * R; ctx.beginPath(); ctx.arc(0, 0, br, 0, TAU); ctx.stroke();
  ctx.strokeStyle = rgba(PAL.paper, 0.10); ctx.lineWidth = 0.006 * R;
  for (const rr of [0.075, 0.135, 0.195]) { ctx.beginPath(); ctx.arc(0, 0, rr * R, 0, TAU); ctx.stroke(); }
  ctx.fillStyle = SHADE.inkDeep; ctx.beginPath(); ctx.arc(0, 0, 0.03 * R, 0, TAU); ctx.fill();
  ctx.strokeStyle = rgba(PAL.paper, 0.20); ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(0, 0, 0.05 * R, 0, TAU); ctx.stroke();
  ctx.restore();

  if (sheen) {
    ctx.save();
    ctx.beginPath(); ctx.arc(0, 0, R, 0, TAU); ctx.clip();
    const sh = ctx.createRadialGradient(-0.40 * R, -0.44 * R, 0.02 * R, -0.15 * R, -0.15 * R, 1.05 * R);
    sh.addColorStop(0, rgba(PAL.paper, 0.20)); sh.addColorStop(0.55, rgba(PAL.paper, 0.045)); sh.addColorStop(1, rgba(PAL.paper, 0));
    ctx.fillStyle = sh; ctx.fillRect(-R, -R, 2 * R, 2 * R);
    const sd = ctx.createRadialGradient(0.42 * R, 0.46 * R, 0.05 * R, 0.30 * R, 0.30 * R, 1.0 * R);
    sd.addColorStop(0, rgba(SHADE.inkDeep, 0.30)); sd.addColorStop(1, rgba(SHADE.inkDeep, 0));
    ctx.fillStyle = sd; ctx.fillRect(-R, -R, 2 * R, 2 * R);
    ctx.restore();
    ctx.save();
    ctx.strokeStyle = rgba(PAL.paper, 0.40); ctx.lineWidth = 0.014 * R; ctx.lineCap = 'round';
    ctx.beginPath(); ctx.arc(0, 0, 0.984 * R, 198 * DEG, 262 * DEG); ctx.stroke();
    ctx.restore();
  }
}

// ---------------------------------------------------------------- the blur
let BLUR = null;   // { canvas, half }

/**
 * Steady light: the eye (or a long exposure) averages the turning chuck. The
 * exact average of a turning picture is rotation symmetric, so it is a radial
 * profile: for every radius, the mean colour over the whole circle. Built once
 * from the crisp drawing itself, then softened a little radially (optics).
 */
function buildBlur(R) {
  const SS = 2, half = Math.ceil(R * 1.1), N = half * 2 * SS;
  const c = document.createElement('canvas'); c.width = c.height = N;
  const g = c.getContext('2d', { willReadFrequently: true });
  g.translate(N / 2, N / 2); g.scale(SS, SS);
  drawChuck(g, R, 0, { sheen: false });
  const d = g.getImageData(0, 0, N, N).data;
  const nb = Math.ceil(N * 0.5 * Math.SQRT2) + 2;
  const P = [0, 1, 2, 3].map(() => new Float64Array(nb)), cn = new Float64Array(nb);
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      const i = (y * N + x) * 4, a = d[i + 3] / 255;
      const b = Math.floor(Math.hypot(x + 0.5 - N / 2, y + 0.5 - N / 2));
      P[0][b] += d[i] * a; P[1][b] += d[i + 1] * a; P[2][b] += d[i + 2] * a; P[3][b] += a; cn[b] += 1;
    }
  }
  const sig = 3.2, kr = Math.ceil(sig * 3), ker = [];
  let ks = 0;
  for (let j = -kr; j <= kr; j++) { const v = Math.exp(-(j * j) / (2 * sig * sig)); ker.push(v); ks += v; }
  const prof = P.map(arr => {
    const m = Float64Array.from(arr, (v, b) => (cn[b] ? v / cn[b] : 0));
    const o = new Float64Array(nb);
    for (let b = 0; b < nb; b++) {
      let s = 0;
      for (let j = -kr; j <= kr; j++) { let q = b + j; if (q < 0) q = -q - 1; if (q >= nb) q = nb - 1; s += m[q] * ker[j + kr]; }
      o[b] = s / ks;
    }
    return o;
  });
  const c2 = document.createElement('canvas'); c2.width = c2.height = N;
  const g2 = c2.getContext('2d');
  const img = g2.createImageData(N, N);
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      const f = Math.max(0, Math.hypot(x + 0.5 - N / 2, y + 0.5 - N / 2) - 0.5);
      const b = Math.min(nb - 2, Math.floor(f)), u = f - b;
      const at = k => prof[k][b] * (1 - u) + prof[k][b + 1] * u;
      const a = at(3), i = (y * N + x) * 4;
      if (a > 1e-4) { img.data[i] = at(0) / a; img.data[i + 1] = at(1) / a; img.data[i + 2] = at(2) / a; }
      img.data[i + 3] = Math.round(255 * Math.min(1, a));
    }
  }
  g2.putImageData(img, 0, 0);
  return { canvas: c2, half };
}

function drawBlur(ctx, cx, cy, a) {
  if (a <= 0 || !BLUR) return;
  ctx.save();
  ctx.globalAlpha *= clamp(a);
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(BLUR.canvas, cx - BLUR.half, cy - BLUR.half, BLUR.half * 2, BLUR.half * 2);
  ctx.restore();
}

// ============================================================================
//  TIMELINE (seconds from the start of the scene)
// ============================================================================
const TM = {
  eyebrow: [0.4, 4.5],
  heliIn: [0.5, 1.5],
  slide: [5.5, 6.8],                 // from the centre to the left
  badgeReal: 1.1,
  rows: [6.2, 6.75, 7.3],            // blades, = passes, = pictures
  example: 6.2,
  marker: [7.7, 10.5],               // the yellow marker: about 3 s
  part1Out: [10.35, 10.9],
  leftPanel: 11.3, leftChuck: 11.45, leftMod: 11.65, arrow: [11.95, 12.75],
  rightPanel: 11.95, rightMod: 12.15,
  flicker: [12.6, 13.7],             // flicker depth 0 -> 1
  crisp: [12.9, 14.0],               // blur -> crisp, following the flicker
  lab1: 12.95, lab2: 13.9, eq: 14.4,
  warn: 16.9,
};
const VEIL = 0.22;                    // weight of the faint blur left over the crisp jaws
const CRISP_ANGLE = 0;                // where the jaws stand in the still picture

// ---------------------------------------------------------------- part 1
function renderPart1(ctx, t, W, rtl) {
  const out = 1 - prog(t, TM.part1Out[0], TM.part1Out[1], ease.inOutSine);
  if (out <= 0) return;

  // chapter label
  const eb = win(t, TM.eyebrow[0], TM.eyebrow[1], 0.5, 0.5);
  if (eb > 0) EP.eyebrow(ctx, EP.T('chapter.real'), { x: W / 2, y: 86, align: 'center', opacity: eb, reveal: prog(t, TM.eyebrow[0], TM.eyebrow[0] + 0.9, ease.outCubic) });

  // the helicopter hovers: slow smooth drift, whisper of scale, never a turn
  const R = HELI.R;
  const kIn = prog(t, TM.heliIn[0], TM.heliIn[1], ease.outCubic);
  const hv = DEBUG.noHover ? { dx: 0, dy: 0, s: 1 } : hover(t);
  const mk = win(t, TM.marker[0], TM.marker[1], 0.35, 0.35);
  ctx.save();
  const hx = EP.lerp(W / 2, HELI.x, prog(t, TM.slide[0], TM.slide[1], ease.inOutCubic));
  ctx.translate(hx + hv.dx, HELI.y + hv.dy + (1 - kIn) * 16);
  ctx.scale(hv.s, hv.s);
  withAlpha(ctx, { x: -1.36 * R, y: -1.36 * R, w: 2.72 * R, h: 2.72 * R }, kIn * out, c => {
    if (!DEBUG.noDownwash) drawDownwash(c, R, t, prog(t, 0.9, 2.0, ease.outCubic));
    drawHelicopter(c, t, R, mk);
  });
  ctx.restore();

  // badges: real-time rotor, example numbers
  EP.badge(ctx, EP.T('badge.real'), { x: EP.startX(96), y: 318, opacity: prog(t, TM.badgeReal, TM.badgeReal + 0.6, ease.outCubic) * out });
  EP.badge(ctx, EP.T('badge.example'), { x: EP.startX(96), y: 368, opacity: prog(t, TM.example, TM.example + 0.5, ease.outCubic) * out });

  // the equation-like block: blades x turns = passes = pictures
  const bx = rtl ? TEXT_X.rtl : TEXT_X.ltr;
  const parts = EP.T('s06.blades').split(/[\s\u00a0\u202f]=[\s\u00a0\u202f]/);
  const passes = String(BLADES * ROTOR_RATE);
  const rows = [{ s: parts[0], hi: null, t0: TM.rows[0] }];
  if (parts.length > 1) rows.push({ s: '= ' + parts.slice(1).join(' = '), hi: passes, t0: TM.rows[1] });
  rows.push({ s: EP.T('s06.match'), hi: String(FPS), t0: TM.rows[2] });
  rows.forEach((r, i) => {
    const k = prog(t, r.t0, r.t0 + 0.6, ease.outCubic);
    if (k <= 0) return;
    rowHi(ctx, r.s, { x: bx, y: 524 + i * 60 + (1 - k) * 14, size: 38, weight: 600, hi: r.hi, opacity: k * out, maxWidth: 670 });
  });

  // legend of the yellow marker (72 deg = 360 x 6 / 30, computed)
  if (mk > 0) {
    const ly = 734;
    ctx.save();
    ctx.globalAlpha *= mk * out;
    ctx.fillStyle = PAL.highlight; ctx.beginPath(); ctx.arc(rtl ? bx - 9 : bx + 9, ly - 9, 8.5, 0, TAU); ctx.fill();
    ctx.restore();
    EP.text(ctx, EP.T('s06.marker', { n: EP.num((360 * ROTOR_RATE) / FPS) }), {
      x: rtl ? bx - 32 : bx + 32, y: ly, size: 26, weight: 500, color: PAL.paper, opacity: mk * out,
      align: 'start', maxWidth: 630, shrink: true, maxLines: 2,
    });
  }
}

// ---------------------------------------------------------------- part 2
function renderPart2(ctx, t, W, rtl) {
  const P = PANEL, R = CHUCK_R;
  const enter = (t0, d = 0.6, e = ease.outCubic) => prog(t, t0, t0 + d, e);
  const cyOff = 218;                                  // chuck centre below the panel top
  const modY = 298;                                   // top of the lamp cord
  const startEdge = x => (rtl ? x + P.w - 26 : x + 26);

  // ------------------------------------------------ left: steady light, a blur
  const xL = COL.left;
  const kLP = enter(TM.leftPanel), kLC = enter(TM.leftChuck), kLM = enter(TM.leftMod);
  if (kLP > 0) {
    ctx.save(); ctx.translate(0, (1 - kLP) * 14);
    drawPanel(ctx, xL, P.top, P.w, P.h, kLP);
    EP.text(ctx, EP.T('s06.really'), { x: startEdge(xL), y: P.top + 46, size: 30, weight: 600, opacity: kLP, align: 'start', maxWidth: P.w - 60, shrink: true, maxLines: 1 });
    ctx.restore();
  }
  if (kLC > 0) {
    ctx.save(); ctx.translate(0, (1 - kLC) * 14);
    const cx = xL + P.w / 2, cy = P.top + cyOff;
    drawBlur(ctx, cx, cy, kLC);
    // it really turns: blue = real motion, solid
    const ka = prog(t, TM.arrow[0], TM.arrow[1], ease.inOutCubic);
    EP.arcArrow(ctx, cx, cy, R * 1.16, 30 * DEG, 128 * DEG, { kind: 'motion', progress: ka, alpha: kLC, width: 4.5 });
    const kl = enter(TM.arrow[0] + 0.25);
    EP.text(ctx, EP.num(CHUCK_RATE) + ' ' + EP.T('unit.turns'), { x: cx, y: P.top + 398, size: 27, weight: 600, align: 'center', opacity: kl, maxWidth: P.w - 60, shrink: true, maxLines: 1 });
    EP.text(ctx, (rtl ? '\u200e' : '') + EP.num(CHUCK_RATE * 60) + ' ' + EP.T('s06.rpm'), { x: cx, y: P.top + 434, size: 22, weight: 500, color: PAL.steel, align: 'center', opacity: kl, maxWidth: P.w - 60, shrink: true, maxLines: 1 });
    ctx.restore();
  }
  if (kLM > 0) {
    ctx.save(); ctx.translate(0, (1 - kLM) * 10);
    drawLamp(ctx, xL + 48, modY, kLM);
    drawGraph(ctx, { x: xL + 108, y: 310, w: 522, h: 58, t, k: 0, a: kLM });
    EP.text(ctx, EP.T('s06.steady'), { x: xL + P.w / 2, y: 410, size: 27, weight: 500, align: 'center', opacity: kLM, maxWidth: 620, shrink: true, maxLines: 1 });
    ctx.restore();
  }

  // ------------------------------------------------ right: flickering light, looks still
  const xR = COL.right;
  const kRP = enter(TM.rightPanel), kRM = enter(TM.rightMod);
  const flick = prog(t, TM.flicker[0], TM.flicker[1], ease.inOutSine);
  const crisp = prog(t, TM.crisp[0], TM.crisp[1], ease.inOutSine);
  if (kRP > 0) {
    ctx.save(); ctx.translate(0, (1 - kRP) * 14);
    drawPanel(ctx, xR, P.top, P.w, P.h, kRP, prog(t, TM.warn, TM.warn + 0.7, ease.inOutSine));
    EP.text(ctx, EP.T('s06.eye'), { x: startEdge(xR), y: P.top + 46, size: 30, weight: 600, opacity: kRP, align: 'start', maxWidth: P.w - 290, shrink: true, maxLines: 1 });
    const cx = xR + P.w / 2, cy = P.top + cyOff;
    drawBlur(ctx, cx, cy, kRP);
    if (crisp > 0) {
      // crisp, stationary jaws dominate; a faint veil of the blur stays (real lamps never go fully dark)
      ctx.save();
      ctx.translate(cx, cy);
      withAlpha(ctx, { x: -R - 4, y: -R - 4, w: 2 * R + 8, h: 2 * R + 8 }, crisp * (1 - VEIL), g => drawChuck(g, R, CRISP_ANGLE));
      ctx.restore();
    }
    const kb = enter(TM.crisp[0] + 0.1);
    EP.badge(ctx, EP.T('badge.simulated'), { x: rtl ? xR + 22 : xR + P.w - 22, y: P.top + 40, align: 'end', size: 18, opacity: kb });
    ctx.restore();
  }
  if (kRM > 0) {
    ctx.save(); ctx.translate(0, (1 - kRM) * 10);
    drawLamp(ctx, xR + 48, modY, kRM);
    drawGraph(ctx, { x: xR + 108, y: 310, w: 522, h: 58, t, k: flick, a: kRM });
    EP.badge(ctx, EP.T('badge.slowx', { n: SLOW }), { x: xR + 108 + 522, y: 296, align: 'right', size: 16, opacity: enter(TM.flicker[0] - 0.1) });
    ctx.restore();
  }

  // the two labels, one under the other, with the match between them
  const k1 = enter(TM.lab1), k2 = enter(TM.lab2), ke = enter(TM.eq);
  if (k1 > 0) {
    const hi = String(FLICKER);
    const o = { size: 27, weight: 500, hi, maxWidth: 850 };
    const s1 = EP.T('s06.flicker'), s2 = EP.T('s06.jaws');
    const w1 = rowHi(ctx, s1, { ...o, x: 0, y: 0, draw: false }).w, w2 = rowHi(ctx, s2, { ...o, x: 0, y: 0, draw: false }).w;
    const Wb = Math.max(w1, w2), cxb = xR + P.w / 2 + 22;
    let edge = rtl ? cxb + Wb / 2 : cxb - Wb / 2;
    // keep the text, the bracket and the equals sign inside the safe area (96 px margin)
    const edgeLo = rtl ? 96 + Wb : 96 + 64, edgeHi = rtl ? W - 96 - 64 : W - 96 - Wb;
    edge = Math.max(edgeLo, Math.min(edgeHi, edge));
    const y1 = 410, y2 = 446;
    rowHi(ctx, s1, { ...o, x: edge, y: y1 + (1 - k1) * 10, opacity: k1 });
    if (k2 > 0) rowHi(ctx, s2, { ...o, x: edge, y: y2 + (1 - k2) * 10, opacity: k2 });
    if (ke > 0) {
      const dir = rtl ? -1 : 1, gx = edge - dir * 22, top = y1 - 24, bot = y2 + 9;
      ctx.save();
      ctx.globalAlpha *= ke;
      ctx.strokeStyle = PAL.highlight; ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      const mid = (top + bot) / 2, half = ((bot - top) / 2) * ke;
      ctx.beginPath();
      ctx.moveTo(gx + dir * 9, mid - half); ctx.lineTo(gx, mid - half); ctx.lineTo(gx, mid + half); ctx.lineTo(gx + dir * 9, mid + half);
      ctx.stroke();
      ctx.restore();
      EP.text(ctx, '=', { x: gx - dir * 28, y: mid, anchor: 'middle', align: 'center', size: 44, weight: 700, color: PAL.highlight, latin: true, opacity: ke });
    }
  }

  // look here: the warning triangle beside the chuck that looks stopped
  const kw = prog(t, TM.warn, TM.warn + 0.55, ease.outBack), aw = prog(t, TM.warn, TM.warn + 0.3, ease.outCubic);
  if (aw > 0) {
    const pulse = 1 + 0.035 * Math.sin((TAU * (t - TM.warn)) / 2.6);
    drawWarning(ctx, xR + P.w / 2 + 240, P.top + cyOff - 6, (0.55 + 0.55 * kw) * pulse, aw);
  }
}

// ============================================================================
export default {
  duration: 22.5,
  captions: [
    { key: 's06.c1', in: 0.8, out: 5.6 },
    { key: 's06.c2', in: 6.0, out: 10.8 },
    { key: 's06.c3', in: 11.2, out: 16.2 },
    { key: 's06.c4', in: 16.6, out: 21.9 },
  ],
  cues: [
    { t: 0.5, sfx: 'rotor', dur: 10.5, rate: BLADES * ROTOR_RATE },   // blade passes per second
    { t: TM.rows[0], sfx: 'pop' },
    { t: TM.rows[2], sfx: 'pop' },
    { t: TM.marker[0], sfx: 'pop' },
    { t: 11.3, sfx: 'whirr', dur: 10.4, rate: CHUCK_RATE },
    { t: TM.leftPanel + 0.25, sfx: 'pop' },
    { t: TM.rightPanel, sfx: 'pop' },
    { t: TM.flicker[0], sfx: 'hum', dur: 9.7 },
    { t: 13.35, sfx: 'shimmer', dur: 1.6 },
    { t: TM.lab1, sfx: 'pop' },
    { t: TM.lab2, sfx: 'pop' },
    { t: TM.warn, sfx: 'pop' },
  ],
  music: 'explain',

  setup(E) {
    init(E);
    // the labels on screen are only true if these products hold
    if (BLADES * ROTOR_RATE !== FPS) throw new Error('main rotor: blade passes per second must equal the picture rate');
    if (JAWS * CHUCK_RATE !== FLICKER) throw new Error('chuck: jaw passes per second must equal the flicker rate');
    if ((TAIL_BLADES * TAIL_RATE) % FPS !== 0) throw new Error('tail rotor: blade passes must be a whole number per picture');
    BLUR = buildBlur(CHUCK_R);
  },

  render(ctx, t, E, { W, H, rtl }) {
    init(E);
    EP.bg(ctx, W, H);
    renderPart1(ctx, t, W, rtl);
    renderPart2(ctx, t, W, rtl);
  },
};
