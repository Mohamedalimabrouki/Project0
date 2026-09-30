/*
 * Scene 03 - Snapshots. Opens the "See it" chapter (24.5 s).
 *
 * Idea: a video is a series of still pictures, 30 per second, with nothing
 * recorded in between. The brain joins the pictures by linking each spoke to
 * the closest spoke in the next picture.
 *
 * EVERYTHING on screen is computed from a few numbers (nothing is placed by eye):
 *
 *   FR    real turning rate of the wheel ............ 1.5 turns per second
 *   FS    pictures per second of the video .......... 30
 *   SLOW  slow-motion factor while pictures are shown  15
 *   N     pictures in the strip = one second ........ FS x 1 s = 30
 *
 *   turn between two pictures = 360 * FR / FS = 18 degrees
 *   seconds between two pictures on screen = SLOW / FS = 0.5 s
 *   turning rate on screen while slowed = FR / SLOW = 0.1 turns per second
 *   the closest spoke of the next picture = EP.wrapSigned(turn, 72 degrees) = +18 degrees
 *
 * TIME WARP. The wheel turns at the same REAL rate (FR) all the time. Only the
 * speed of screen time against real time changes ("rho" = real seconds per screen second):
 *
 *   0 - 4.4 s      real time (the wheel is drawn at its true rate, no motion blur)
 *   4.4 - 5.4 s    time slows down, x1 to x15 (eased in the logarithm of the rate)
 *   5.4 - 9.5 s    x15 slow motion: one picture every 0.5 s on screen (badge "Slowed down x15")
 *   9.5 - 10.15 s  time speeds up again to real time
 *   after          real time: the rest of the second fills in at one picture per
 *                  video frame (1/30 s), exactly as the film itself is made (badge "Real speed")
 *
 * The wheel angle is the integral of FR * rho (EP.angleTable, computed once in
 * setup). Picture n is taken when the wheel has turned exactly n * 18 degrees
 * since picture 0; the screen time of each picture is found by inverting that
 * angle (bisection). So every card shows the true angle of that instant, and the
 * spacing of pictures on screen is 0.5 s slowed down, 1/30 s in real time, and
 * everything in between during the ramps. A check is exported (_check) for tools.
 *
 * STORY (screen time)
 *   0.4 -  4.8   the wheel (real time) and a camera aimed at it; eyebrow "See it"
 *   4.4 -  6.0   time slows down; the film strip runs across the stage; timeline of 30 ticks
 *   6.0 - 10.6   pictures 1..8 one by one (shutter, card slides out and into the strip),
 *                then time speeds up and the strip fills; a bracket says "1 second"
 *  11.0 - 15.6   the strip slides so pictures 1 and 2 are in the middle, they unfold into two
 *                big cards; between them the motion nobody recorded: ghost sweep, "Not recorded", 1/30 s
 *  16.5 - 18.4   the two cards slide onto each other (double exposure) and grow into ONE big wheel:
 *                picture 2 solid, picture 1 a dashed ghost (the language scene 04 continues)
 *  19.5 - 22.0   each spoke is linked to the closest spoke of the next picture: one dashed blue arrow
 *                ("what we see") per beat, on the same ring as in scene 04; then a calm hold and a
 *                fade to the wheel alone, exactly scene 04's opening wheel (960, 606), radius 250, spoke up.
 *
 * Captions: c3 to c5 are timed for reading (about 2.5 words per second at most) and, when needed, given
 * a per-language line width in setup (fitCaptions) so that no word is left alone on a second line.
 */

const DUR = 24.5;
const DEG = Math.PI / 180;

const FR = 1.5;                  // real turns per second
const FS = 30;                   // pictures per second
const SLOW = 15;                 // slow-motion factor
const N = Math.round(FS * 1);    // pictures in one second
const STEP = 360 * FR / FS;      // degrees between two pictures (= 18)
const SPOKES = 5;

// screen-time schedule of the time warp
const TM = { downA: 4.4, downB: 5.4, shot1: 6.0, upA: 9.5, upB: 10.15 };

// screen-time schedule of the pictures shown after the strip is full
const B = {
  outA: 10.95, outB: 11.65,                 // wheel and camera leave
  slideA: 11.0, slideB: 11.9,              // the strip slides: pictures 1 and 2 come to the centre
  ringA: 11.6, ringB: 12.0,                 // yellow marks on those two
  growA: 11.85, growB: 12.9,                // the two cards unfold out of the strip
  gapA: 12.6, gapB: 13.25, sweepA: 12.9, sweepB: 14.0,
  labA: 12.75, labB: 13.35, dimA: 13.7, dimB: 14.6,
  goneA: 16.35, goneB: 16.9,                // gap, labels and time mark leave
  stripA: 16.4, stripB: 17.1,               // the strip leaves
  stackA: 16.5, stackB: 17.4,               // the two cards slide onto each other
  bigA: 17.3, bigB: 18.4,                   // and grow into one big wheel
  legA: 18.5, legB: 19.15,
  arrow0: 19.5, arrowStep: 0.5, arrowDur: 0.5,        // one arrow per beat (120 bpm)
  endA: 23.6, endB: 24.3,                   // everything but the wheel leaves (s04 starts with that wheel)
};

// ---------------------------------------------------------------- layout (px)
const WHEEL = { x: 390, y: 498, r: 158 };
const CAM = { x: 772, y: 498, s: 1.9 };
const STRIP = { x0: 96, x1: 1824, cy: 744, band: 80, card: 50 };
STRIP.pitch = (STRIP.x1 - STRIP.x0) / N;                 // one slot = one picture = one tick
const slotX = k => STRIP.x0 + STRIP.pitch * (k + 0.5);
const STRIP_DX = 960 - (slotX(0) + slotX(1)) / 2;        // slide that brings pictures 1 and 2 to the centre
const TICK = { y0: 796, len: 16 };
const NUM_Y = 838;                                       // running count under the ticks
const BR = { y: 858, cap: 9, notch: 11 };                // the "1 second" bracket
const LABEL_Y = 908;
const FOC = { s: 284, cy: 486, x: [560, 1360] };          // the two enlarged cards
const BIG = { x: 960, y: 606, r: 250 };                   // the overlay wheel: exactly where s04 starts (its CX, CY, R)
const R_SEEN = BIG.r + 60;                                // ring of the dashed "what we see" arrows (same as s04)
const CARD_R = 0.38;                                      // wheel radius / card side
const EJECT = { s: 92, yB: CAM.y + 24 * CAM.s };          // instant-camera slot: bottom edge of the body
const LEG = { leftEdge: BIG.x - 380, rightEdge: BIG.x + 380, y: BIG.y };   // legends beside the big wheel: they hug it, 380 px from its centre

/** Angle of picture n (radians). Picture 0 is 18 degrees behind vertical, so picture 1 stands upright. */
const thetaOf = n => (n - 1) * STEP * DEG;

/** Lines of sight from the camera to the wheel (tangents), starting at the camera's left face. */
const FOV = (() => {
  const ax = CAM.x, ay = CAM.y + CAM.s;
  const dx = WHEEL.x - ax, dy = WHEEL.y - ay, d = Math.hypot(dx, dy);
  const phi = Math.atan2(dy, dx), al = Math.asin(WHEEL.r / d), L = Math.sqrt(d * d - WHEEL.r * WHEEL.r);
  const xEdge = CAM.x - 34 * CAM.s;
  return [1, -1].map(sg => {
    const a = phi + sg * al, c = Math.cos(a), s = Math.sin(a), l0 = (ax - xEdge) / Math.abs(c);
    return { x0: ax + l0 * c, y0: ay + l0 * s, x1: ax + L * c, y1: ay + L * s };
  });
})();

let ST = null;

// ---------------------------------------------------------------- drawing helpers
/** A snapshot card: rounded frame, thin paper stroke, lifted ink fill, the wheel of that instant. */
function drawCard(ctx, EP, cx, cy, S, ang, o = {}) {
  const { PAL, SHADE, rgba } = EP;
  const { alpha = 1, frame = 1, fill = 1, wheel = 1, edge = PAL.paper, edgeAlpha = 0.9 } = o;
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  if (frame > 0) {
    ctx.save();
    ctx.globalAlpha *= frame;
    EP.roundRect(ctx, cx - S / 2, cy - S / 2, S, S, S * 0.085);
    ctx.save();
    ctx.globalAlpha *= fill;                   // a translucent fill lets the card underneath show through
    ctx.fillStyle = SHADE.inkLift;
    ctx.fill();
    ctx.restore();
    ctx.lineWidth = Math.max(1.3, S * 0.0075);
    ctx.strokeStyle = rgba(edge, edgeAlpha);
    ctx.stroke();
    ctx.restore();
  }
  if (wheel > 0) EP.wheel(ctx, { x: cx, y: cy, r: S * CARD_R, angle: ang, opacity: wheel });
  ctx.restore();
}

/** The film band: dark strip, sprocket holes along both edges. `wipe` 0..1 runs it across the stage. */
function drawBand(ctx, EP, wipe) {
  const { PAL, SHADE, rgba } = EP;
  if (wipe <= 0) return;
  const y0 = STRIP.cy - STRIP.band / 2, w = STRIP.x1 - STRIP.x0;
  ctx.save();
  ctx.beginPath();
  ctx.rect(-2000, 0, 2000 + STRIP.x0 + w * wipe, 1080);
  ctx.clip();
  EP.roundRect(ctx, STRIP.x0, y0, w, STRIP.band, 8);
  ctx.fillStyle = rgba(SHADE.inkDeep, 0.78);
  ctx.fill();
  ctx.lineWidth = 1.5;
  ctx.strokeStyle = rgba(PAL.steel, 0.34);
  ctx.stroke();
  // sprocket holes: 4 per picture, top and bottom
  const hp = STRIP.pitch / 4, hw = 7.5, hh = 5.5;
  ctx.beginPath();
  for (let j = 0; j < N * 4; j++) {
    const x = STRIP.x0 + hp * (j + 0.5) - hw / 2;
    ctx.roundRect(x, y0 + 5, hw, hh, 1.6);
    ctx.roundRect(x, y0 + STRIP.band - 5 - hh, hw, hh, 1.6);
  }
  ctx.fillStyle = rgba(PAL.paper, 0.13);
  ctx.fill();
  ctx.restore();
}

/** Where picture k is at time t: null before it is taken, else {x, y, S, a, clipY, landed, fly}. */
function cardState(EP, k, t) {
  const t0 = ST.shots[k];
  if (t < t0) return null;
  const { clamp, ease, lerp } = EP;
  const px = slotX(k), py = STRIP.cy;
  if (k < ST.nFly) {
    // slow motion: the card slides out of the camera, drops, then runs along the strip into its slot.
    // The flight is shortened when the next picture follows quickly (the pace picks up).
    const next = k + 1 < N ? ST.shots[k + 1] - t0 : 0.5;
    const life = clamp(1.5 * next, 0.2, 0.75), u = (t - t0) / life, ue = 0.2 / life;
    if (u >= 1) {
      const age = t - (t0 + life), press = age < 0.16 ? 0.06 * Math.sin(Math.PI * age / 0.16) : 0;   // the card presses into its slot
      return { x: px, y: py, S: STRIP.card * (1 - press), a: 1, landed: true };
    }
    if (u < ue) {
      const e = ease.outCubic(u / ue);
      return { x: CAM.x, y: lerp(EJECT.yB - EJECT.s / 2, EJECT.yB + EJECT.s / 2, e), S: EJECT.s, a: 1, clipY: EJECT.yB, landed: false, fly: true };
    }
    const v = ease.inOutSine((u - ue) / (1 - ue));
    const ex = CAM.x, ey = EJECT.yB + EJECT.s / 2, cx = CAM.x, cy = py;   // quadratic Bezier E -> C -> P
    const b0 = (1 - v) * (1 - v), b1 = 2 * v * (1 - v), b2 = v * v;
    return { x: b0 * ex + b1 * cx + b2 * px, y: b0 * ey + b1 * cy + b2 * py, S: lerp(EJECT.s, STRIP.card, ease.smooth(v)), a: 1, landed: false, fly: true };
  }
  // real time: the card simply appears in its slot (a wave running across the strip)
  const life = 0.16, u = clamp((t - t0) / life);
  if (u >= 1) return { x: px, y: py, S: STRIP.card, a: 1, landed: true };
  return { x: px, y: py, S: STRIP.card * (0.6 + 0.4 * ease.outCubic(u)), a: ease.outCubic(clamp(u * 2)), landed: false, fly: false };
}

/** Empty slot outline. */
function drawSlot(ctx, EP, k, a) {
  if (a <= 0) return;
  ctx.save();
  ctx.globalAlpha *= a;
  EP.roundRect(ctx, slotX(k) - STRIP.card / 2, STRIP.cy - STRIP.card / 2, STRIP.card, STRIP.card, STRIP.card * 0.085);
  ctx.lineWidth = 1.2;
  ctx.strokeStyle = EP.rgba(EP.PAL.steel, 0.30);
  ctx.stroke();
  ctx.restore();
}

/** One timeline tick: dim until its picture is taken, then paper; yellow while it is the newest. */
function drawTick(ctx, EP, k, t, a) {
  const { PAL, rgba, mix, clamp, ease } = EP;
  if (a <= 0) return;
  const age = t - ST.shots[k], lit = age >= 0;
  const x = slotX(k);
  const next = k + 1 < N ? ST.shots[k + 1] - ST.shots[k] : 0.5;       // time until the next picture
  let color, len = TICK.len, w = 2.2;
  if (!lit) color = rgba(PAL.steel, 0.5);
  else {
    color = mix(PAL.highlight, PAL.paper, ease.smooth(clamp(age / clamp(1.2 * next, 0.04, 0.5))));
    const pop = clamp(3 * next, 0.1, 0.3);
    len += 7 * Math.sin(Math.PI * clamp(age / pop));
    w = 3.2;
  }
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.strokeStyle = color;
  ctx.lineWidth = w;
  ctx.lineCap = 'round';
  ctx.beginPath();
  ctx.moveTo(x, TICK.y0 + TICK.len);
  ctx.lineTo(x, TICK.y0 + TICK.len - len);
  ctx.stroke();
  ctx.restore();
}

/** The "1 second" bracket, exactly as wide as the 30 slots, with the label under it. */
function drawBracket(ctx, EP, T, k, labelA, lit) {
  const { PAL } = EP;
  if (k <= 0) return;
  const xc = (STRIP.x0 + STRIP.x1) / 2, half = ((STRIP.x1 - STRIP.x0) / 2) * k;
  ctx.save();
  ctx.strokeStyle = EP.mix(EP.mix(PAL.ink, PAL.paper, 0.6), PAL.paper, lit);   // brightens when the 30th picture is in
  ctx.lineWidth = 2.6;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(xc - half, BR.y);
  ctx.lineTo(xc + half, BR.y);
  ctx.moveTo(xc, BR.y);
  ctx.lineTo(xc, BR.y + BR.notch);
  if (k > 0.985) {
    ctx.moveTo(STRIP.x0, BR.y - BR.cap); ctx.lineTo(STRIP.x0, BR.y);
    ctx.moveTo(STRIP.x1, BR.y - BR.cap); ctx.lineTo(STRIP.x1, BR.y);
  }
  ctx.stroke();
  ctx.restore();
  EP.text(ctx, T('s03.second'), { x: xc, y: LABEL_Y + 8 * (1 - labelA), align: 'center', size: 34, weight: 600, color: PAL.paper, opacity: labelA, maxWidth: 620, shrink: true, maxLines: 1 });
}

/** Ghost sweep + hatch + dashed frame: the motion between two pictures that nobody recorded. */
function drawGap(ctx, EP, T, a, sweep) {
  const { PAL, rgba, clamp, lerp } = EP;
  if (a <= 0) return;
  const gx0 = FOC.x[0] + FOC.s / 2 + 34, gx1 = FOC.x[1] - FOC.s / 2 - 34;
  const gy0 = FOC.cy - FOC.s / 2, gy1 = FOC.cy + FOC.s / 2;
  const cx = (gx0 + gx1) / 2, cy = FOC.cy, gw = gx1 - gx0, gh = gy1 - gy0;
  ctx.save();
  ctx.globalAlpha *= a;
  // hatching: nothing is drawn here because nothing was recorded
  ctx.save();
  EP.roundRect(ctx, gx0, gy0, gw, gh, 22);
  ctx.clip();
  ctx.strokeStyle = rgba(PAL.steel, 0.15);
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  for (let d = -gh; d < gw; d += 17) { ctx.moveTo(gx0 + d, gy1); ctx.lineTo(gx0 + d + gh, gy0); }
  ctx.stroke();
  ctx.restore();
  // the wheel is still there, still turning, but nobody looks: dashed tyre outline and the ghost sweep
  const K = 18, r = FOC.s * CARD_R, th1 = thetaOf(0), th2 = thetaOf(1);
  ctx.save();
  ctx.setLineDash([5, 9]);
  ctx.lineWidth = 1.6;
  ctx.strokeStyle = rgba(PAL.steel, 0.4);
  ctx.beginPath(); ctx.arc(cx, cy, r, 0, EP.TAU); ctx.stroke();
  ctx.restore();
  for (let j = 1; j <= K; j++) {
    const aj = clamp(sweep * (K + 1) - j + 1);
    EP.wheelGhost(ctx, { x: cx, y: cy, r, angle: lerp(th1, th2, j / (K + 1)), color: PAL.paper, opacity: 0.12 * aj, width: 1.6 });
  }
  // dashed frame, broken where the label sits
  const label = EP.measure(ctx, T('s03.unseen'), { size: 30, weight: 600, maxWidth: gw - 90, shrink: true, maxLines: 1 });
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, 1920, 1080);
  ctx.rect(cx - label.w / 2 - 16, gy0 - 22, label.w + 32, 44);
  ctx.clip('evenodd');
  EP.roundRect(ctx, gx0, gy0, gw, gh, 22);
  ctx.setLineDash([9, 8]);
  ctx.lineWidth = 2;
  ctx.strokeStyle = rgba(PAL.steel, 0.62);
  ctx.stroke();
  ctx.restore();
  EP.text(ctx, T('s03.unseen'), { x: cx, y: gy0 + 10, align: 'center', size: 30, weight: 600, color: PAL.paper, maxWidth: gw - 90, shrink: true, maxLines: 1 });
  ctx.restore();
}

/**
 * A legend block beside the wheel: rows of [icon, text]. The block hugs the wheel (side 'left' ends at xEdge,
 * side 'right' starts at xEdge) whatever the length of the text, and inside a row the icon sits on the
 * reading-start side (right in Arabic). Diagrams do not mirror, so the block itself never changes side.
 */
function legendBlock(ctx, EP, rtl, side, xEdge, rows, a) {
  if (a <= 0) return;
  const ICON = 88, size = 30;
  const tw = rows.map(r => EP.measure(ctx, r.text, { size, weight: 600, maxWidth: 300, shrink: true, maxLines: 1 }).w);
  const wText = Math.max(...tw), wBlock = ICON + wText;
  const x0 = side === 'left' ? xEdge - wBlock : xEdge;
  rows.forEach(r => {
    const ix = rtl ? x0 + wBlock - ICON / 2 : x0 + ICON / 2;
    const tx = rtl ? x0 + wBlock - ICON : x0 + ICON;
    ctx.save();
    ctx.globalAlpha *= a;
    ctx.translate(ix, r.y);
    r.icon(ctx);
    ctx.restore();
    EP.text(ctx, r.text, { x: tx, y: r.y, anchor: 'middle', align: 'start', size, weight: 600, color: EP.PAL.paper, opacity: a, maxWidth: 300, shrink: true, maxLines: 1 });
  });
}

// exposed for tests only (tools and checks read the numbers; the stage ignores it)
export const _check = { get state() { return ST; }, FR, FS, SLOW, N, STEP, TM, B, thetaOf, cardState, slotX, STRIP, FOC, BIG, STRIP_DX };

// ---------------------------------------------------------------- captions
// Reading time: at most about 2.5 words per second (c5 is 13 words: 5.2 s).
const CAPTIONS = [
  { key: 's03.c1', in: 0.8, out: 4.8 },
  { key: 's03.c2', in: 5.2, out: 10.6 },
  { key: 's03.c3', in: 11.0, out: 15.6 },
  { key: 's03.c4', in: 16.0, out: 18.45 },      // appears just before the two pictures join (16.5 s)
  { key: 's03.c5', in: 18.65, out: 23.85 },     // the arrows start at 19.5 s
];

/**
 * Caption line breaks. The engine wraps a caption greedily (default band: 50 px, weight 600, 1560 px wide),
 * which can strand one word on a second line. Each caption is measured once, in the language being rendered:
 * if it fits on one line inside the safe width it gets that width (one line); otherwise it gets the narrowest
 * width that reproduces the most even two-line split (never ending a line on a tiny word). Any wording works,
 * so a changed English or translated line needs no change here.
 */
function fitCaptions(EP) {
  if (typeof document === 'undefined') return;                     // only in the browser renderer
  const ctx = document.createElement('canvas').getContext('2d');
  const SIZE = 50, WEIGHT = 600, DEFAULT = 1560, SAFE = 1728;
  const width = str => EP.measure(ctx, str, { size: SIZE, weight: WEIGHT }).w;
  for (const c of CAPTIONS) {
    delete c.band;
    const str = EP.T(c.key), w = width(str);
    if (w <= DEFAULT) continue;
    if (w <= SAFE - 60) { c.band = { maxWidth: SAFE }; continue; }   // one line, still inside the safe area
    const words = str.split(' ');
    let best = null;
    for (let k = 1; k < words.length; k++) {
      const l1 = words.slice(0, k).join(' '), l2 = words.slice(k).join(' ');
      const w1 = width(l1), w2 = width(l2), mw = Math.max(w1, w2) + 10;
      if (width(l1 + ' ' + words[k]) <= mw) continue;               // the engine would pull the next word up: not reachable
      const tiny = /^\p{L}{1,3}$/u.test(words[k - 1].replace(/[^\p{L}\p{N}]/gu, ''));
      const cost = Math.max(w1, w2) + (tiny ? 250 : 0);
      if (!best || cost < best.cost) best = { cost, mw };
    }
    if (best && best.mw < DEFAULT) c.band = { maxWidth: Math.ceil(best.mw) };
  }
}

// ---------------------------------------------------------------- the scene
export default {
  duration: DUR,
  captions: CAPTIONS,
  cues: [
    { t: 0.45, sfx: 'whoosh', dur: 0.8, gain: -10 },
    { t: 0.95, sfx: 'pop', gain: -8 },
    { t: 4.4, sfx: 'swoosh_rev', dur: 1.0, gain: -6 },
    { t: 5.25, sfx: 'whoosh', dur: 0.8, gain: -8 },
    { t: 5.7, sfx: 'pop', gain: -6 },
    { t: 5.95, sfx: 'tick', gain: -6 },
    // one shutter per picture while slowed down: 2 per second, on the beat
    ...Array.from({ length: 8 }, (_, i) => ({ t: TM.shot1 + i * SLOW / FS, sfx: 'shutter' })),
    { t: 9.55, sfx: 'whoosh', dur: 1.1, gain: -5 },
    { t: 10.63, sfx: 'tick' },
    { t: B.slideA, sfx: 'whoosh', dur: 0.9, gain: -6 },        // the strip slides: pictures 1 and 2 come to the centre
    { t: B.gapA + 0.1, sfx: 'pop', gain: -8 },                  // "Not recorded"
    { t: B.dimA + 0.05, sfx: 'pop', gain: -10 },                // 1/30 s
    { t: B.stackA, sfx: 'whoosh', dur: 1.3, gain: -8 },         // the two pictures join
    { t: B.legA, sfx: 'pop', gain: -10 },                       // legend
    ...Array.from({ length: 5 }, (_, i) => ({ t: B.arrow0 + B.arrowStep * i, sfx: 'blip', gain: -6 })),
  ],
  math: [],
  music: 'explain',

  setup(EP) {
    fitCaptions(EP);
    // real seconds per screen second
    const rho = t => {
      const { downA, downB, upA, upB } = TM;
      if (t <= downA) return 1;
      if (t < downB) return Math.pow(SLOW, -EP.ease.inOutSine((t - downA) / (downB - downA)));
      if (t <= upA) return 1 / SLOW;
      if (t < upB) return Math.pow(SLOW, -(1 - EP.ease.inOutSine((t - upA) / (upB - upA))));
      return 1;
    };
    const spin = EP.angleTable(t => FR * rho(t), 0, DUR);      // radians turned since t = 0
    const a1 = spin(TM.shot1);
    // picture n is taken when the wheel has turned n * STEP degrees since picture 0 (bisection on the monotonic angle)
    const shots = [];
    for (let n = 0; n < N; n++) {
      const target = a1 + n * STEP * DEG;
      let lo = 0, hi = DUR;
      for (let i = 0; i < 60; i++) { const mid = (lo + hi) / 2; if (spin(mid) < target) lo = mid; else hi = mid; }
      shots.push((lo + hi) / 2);
    }
    const nFly = shots.filter(s => s <= TM.upA + 1e-6).length;   // pictures shown one at a time
    // wheel phase: the wheel stands 18 degrees behind vertical at picture 0
    const phi0 = thetaOf(0) - a1;
    ST = { rho, spin, phi0, shots, nFly };
  },

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, SHADE, rgba, prog, ease, win, clamp, lerp, T } = EP;
    const st = ST;
    EP.bg(ctx, W, H);

    const ang = st.phi0 + st.spin(t);            // the wheel's true angle now

    // ------------------------------------------------ chapter label
    const aEy = win(t, 0.4, 5.0, 0.5, 0.5);
    if (aEy > 0) EP.eyebrow(ctx, T('chapter.see'), { x: W / 2, y: 86, align: 'center', opacity: aEy, reveal: prog(t, 0.4, 1.1, ease.outCubic) });

    // ------------------------------------------------ wheel, camera, lines of sight
    const gOut = 1 - prog(t, B.outA, B.outB, ease.inOutSine);
    const aW = prog(t, 0.4, 1.05, ease.outCubic) * gOut;
    const kW = 0.9 + 0.1 * prog(t, 0.4, 1.4, ease.outCubic);
    const aC = prog(t, 0.85, 1.45, ease.outCubic) * gOut;
    const camX = CAM.x + 28 * (1 - prog(t, 0.85, 1.6, ease.outCubic));
    let ring = 0;
    for (let n = 0; n < st.nFly; n++) { const age = t - st.shots[n]; if (age >= 0 && age < 0.45) ring = age / 0.45; }

    const pF = prog(t, 1.3, 2.1, ease.inOutCubic);
    if (pF > 0 && gOut > 0) {
      const [A, Bq] = FOV;
      const pt = (P, q) => [lerp(P.x0, P.x1, q), lerp(P.y0, P.y1, q)];
      const [ax, ay] = pt(A, pF), [bx, by] = pt(Bq, pF);
      const pulse = ring > 0 ? 0.5 * (1 - ring) : 0;
      ctx.save();
      ctx.globalAlpha *= gOut;
      const g = ctx.createLinearGradient(A.x0, 0, WHEEL.x + WHEEL.r, 0);
      g.addColorStop(0, rgba(PAL.paper, 0.075));
      g.addColorStop(1, rgba(PAL.paper, 0.012));
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.moveTo(A.x0, A.y0); ctx.lineTo(ax, ay); ctx.lineTo(bx, by); ctx.lineTo(Bq.x0, Bq.y0); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = rgba(PAL.paper, 0.26 + pulse);
      ctx.lineWidth = 1.8;
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(A.x0, A.y0); ctx.lineTo(ax, ay); ctx.moveTo(Bq.x0, Bq.y0); ctx.lineTo(bx, by); ctx.stroke();
      ctx.restore();
    }
    if (aW > 0) {                                   // a soft light behind the wheel lifts it off the grid
      const gl = ctx.createRadialGradient(WHEEL.x, WHEEL.y, WHEEL.r * 0.7, WHEEL.x, WHEEL.y, WHEEL.r * 2.2);
      gl.addColorStop(0, rgba(PAL.steel, 0.1 * aW));
      gl.addColorStop(1, rgba(PAL.steel, 0));
      ctx.fillStyle = gl;
      ctx.fillRect(WHEEL.x - WHEEL.r * 2.3, WHEEL.y - WHEEL.r * 2.3, WHEEL.r * 4.6, WHEEL.r * 4.6);
    }
    EP.wheel(ctx, { x: WHEEL.x, y: WHEEL.y, r: WHEEL.r * kW, angle: ang, opacity: aW });
    EP.camera(ctx, { x: camX, y: CAM.y, s: CAM.s, opacity: aC, shot: ring });

    // ------------------------------------------------ badges: real speed, then x15, then real again
    const bY = 290, bx = EP.startX(96);
    const aReal1 = win(t, 0.9, 4.8, 0.45, 0.4);
    const aSlow = win(t, 5.0, 9.95, 0.45, 0.4);
    const aReal2 = win(t, 10.15, 11.5, 0.45, 0.5);
    if (aReal1 > 0) EP.badge(ctx, T('badge.real'), { x: bx, y: bY + 8 * (1 - aReal1), align: 'start', opacity: aReal1 });
    if (aSlow > 0) EP.badge(ctx, T('badge.slowx', { n: SLOW }), { x: bx, y: bY + 8 * (1 - aSlow), align: 'start', opacity: aSlow });
    if (aReal2 > 0) EP.badge(ctx, T('badge.real'), { x: bx, y: bY + 8 * (1 - aReal2), align: 'start', opacity: aReal2 });

    // ------------------------------------------------ the strip: 30 pictures = 1 second
    const wipe = prog(t, 5.25, 5.95, ease.outQuint);
    const aStrip = 1 - prog(t, B.stripA, B.stripB, ease.inOutSine);
    const slide = prog(t, B.slideA, B.slideB, ease.inOutSine);
    const dim = 1 - 0.6 * slide;                                    // the strip steps back while two cards are enlarged
    if (t > 5.2 && aStrip > 0) {
      ctx.save();
      ctx.globalAlpha *= aStrip * dim;
      ctx.translate(STRIP_DX * slide, 0);
      drawBand(ctx, EP, wipe);
      for (let k = 0; k < N; k++) drawSlot(ctx, EP, k, prog(t, 5.3 + 0.015 * k, 5.7 + 0.015 * k, ease.outCubic));
      for (let k = 0; k < N; k++) drawTick(ctx, EP, k, t, prog(t, 5.38 + 0.015 * k, 5.78 + 0.015 * k, ease.outCubic));
      // landed cards, then the ones popping in, then the ones flying (newest on top)
      const pops = [], flying = [];
      for (let k = 0; k < N; k++) {
        const s = cardState(EP, k, t);
        if (!s) continue;
        if (s.landed) drawCard(ctx, EP, s.x, s.y, s.S, thetaOf(k), { alpha: s.a, edgeAlpha: 0.8 });
        else (s.fly ? flying : pops).push([k, s]);
      }
      for (const [k, s] of pops) drawCard(ctx, EP, s.x, s.y, s.S, thetaOf(k), { alpha: s.a });
      for (const [k, s] of flying) {
        ctx.save();
        if (s.clipY) { ctx.beginPath(); ctx.rect(-2000, s.clipY, 4000, H); ctx.clip(); }
        drawCard(ctx, EP, s.x, s.y, s.S, thetaOf(k), { alpha: s.a });
        ctx.restore();
      }
      // yellow marks on pictures 1 and 2: these are the two we look at
      const aMark = prog(t, B.ringA, B.ringB, ease.outCubic);
      if (aMark > 0) {
        ctx.save();
        ctx.strokeStyle = rgba(PAL.highlight, aMark);
        ctx.lineWidth = 2.4;
        for (let i = 0; i < 2; i++) { EP.roundRect(ctx, slotX(i) - 29, STRIP.cy - 29, 58, 58, 6); ctx.stroke(); }
        ctx.restore();
      }
      // running count under the newest tick
      let cnt = 0;
      for (let k = 0; k < N; k++) if (t >= st.shots[k]) cnt = k + 1;
      const aBr = 1 - prog(t, B.slideA, B.slideA + 0.5, ease.inOutSine);
      if (cnt > 0 && aBr > 0) EP.textTab(ctx, EP.num(cnt), { x: slotX(cnt - 1), y: NUM_Y, size: 26, weight: 700, align: 'center', color: PAL.highlight, opacity: aBr });
      // bracket and label
      if (aBr > 0) {
        ctx.save();
        ctx.globalAlpha *= aBr;
        const done = prog(t, st.shots[N - 1], st.shots[N - 1] + 0.4, ease.inOutSine);
        drawBracket(ctx, EP, T, prog(t, 5.45, 5.95, ease.outCubic), prog(t, 5.65, 6.15, ease.outCubic), done);
        ctx.restore();
      }
      ctx.restore();
    }

    // ------------------------------------------------ beat 3 and 4: two consecutive pictures
    if (t > B.slideA) {
      const gone = 1 - prog(t, B.goneA, B.goneB, ease.inOutSine);

      // the gap between them: hatch, ghost sweep, label
      drawGap(ctx, EP, T, prog(t, B.gapA, B.gapB, ease.outCubic) * gone, prog(t, B.sweepA, B.sweepB, ease.inOutSine));

      // labels under the cards, and the time between the two pictures
      const yL = FOC.cy + FOC.s / 2 + 40;
      const aLab = prog(t, B.labA, B.labB, ease.outCubic) * gone;
      if (aLab > 0) for (let i = 0; i < 2; i++) EP.text(ctx, T('word.picture', { n: i + 1 }), { x: FOC.x[i], y: yL + 4 * (1 - aLab), anchor: 'middle', align: 'center', size: 30, weight: 600, color: PAL.paper, opacity: aLab, maxWidth: 240, shrink: true, maxLines: 1 });
      const aDim = prog(t, B.dimA, B.dimB, ease.outCubic) * gone;
      if (aDim > 0) {
        const xa = FOC.x[0] + 100, xb = FOC.x[1] - 100, xc = (xa + xb) / 2;
        const lab = EP.num(1) + '/' + EP.num(FS) + ' s';
        const lw = EP.measure(ctx, lab, { size: 32, weight: 600, latin: true }).w;
        const hw = ((xb - xa) / 2) * ease.outCubic(prog(t, B.dimA, B.dimB + 0.3));
        ctx.save();
        ctx.globalAlpha *= aDim;
        ctx.strokeStyle = rgba(PAL.paper, 0.7);
        ctx.lineWidth = 2.2;
        ctx.lineCap = 'round';
        ctx.beginPath();
        ctx.moveTo(xc - hw, yL); ctx.lineTo(xc - lw / 2 - 16, yL);
        ctx.moveTo(xc + lw / 2 + 16, yL); ctx.lineTo(xc + hw, yL);
        ctx.moveTo(xa, yL - 9); ctx.lineTo(xa, yL + 9);
        ctx.moveTo(xb, yL - 9); ctx.lineTo(xb, yL + 9);
        ctx.stroke();
        ctx.restore();
        EP.text(ctx, lab, { x: xc, y: yL, anchor: 'middle', align: 'center', size: 32, weight: 600, latin: true, color: PAL.paper, opacity: aDim });
      }

      // the two cards (copies of the thumbnails): they unfold out of the strip, slide onto each other, then grow into one wheel
      const m1 = prog(t, B.stackA, B.stackB, ease.inOutCubic);
      const m2 = prog(t, B.bigA, B.bigB, ease.inOutCubic);
      const g = prog(t, B.growA, B.growB, ease.inOutCubic);                 // both together: the unfolding is exactly symmetric
      const pair = [0, 1].map(i => {
        const gx = lerp(slotX(i) + STRIP_DX, FOC.x[i], g), gy = lerp(STRIP.cy, FOC.cy, g), gS = lerp(STRIP.card, FOC.s, g);
        return { x: lerp(gx, BIG.x, m1), y: lerp(gy, BIG.y, m2), S: lerp(gS, BIG.r / CARD_R, m2) };
      });
      if (t > B.growA - 0.02) {
        const frame = 1 - prog(m2, 0, 0.5, ease.inOutSine);
        const endFade = 1 - prog(t, B.endA, B.endB, ease.inOutSine);
        const [c0, c1] = pair;
        // picture 2 (the solid one) below, picture 1 on top: it turns half transparent when they overlap
        // (a double exposure), then becomes the dashed ghost of its spokes (the language s04 continues)
        drawCard(ctx, EP, c1.x, c1.y, c1.S, thetaOf(1), { frame, wheel: 1 });
        const w0 = 1 - 0.45 * prog(m1, 0.55, 1, ease.inOutSine) - 0.55 * prog(m2, 0, 0.55, ease.inOutSine);
        drawCard(ctx, EP, c0.x, c0.y, c0.S, thetaOf(0), { frame, fill: 1 - 0.92 * prog(m1, 0.5, 0.95, ease.inOutSine), wheel: w0, edgeAlpha: 0.9 - 0.3 * m1 });
        const gh = prog(m2, 0.1, 0.65, ease.inOutSine);
        if (gh > 0) EP.wheelGhost(ctx, { x: c0.x, y: c0.y, r: c0.S * CARD_R, angle: thetaOf(0), color: SHADE.steelLight, opacity: 0.85 * gh * endFade, width: 2.4, dash: [8, 6] });

        // ---- beat 4: legends and the links between spokes
        const th1 = thetaOf(0), th2 = thetaOf(1);
        // the closest spoke of the next picture = the shortest way round (spokes repeat every 72 degrees)
        const shift = EP.wrapSigned(th2 - th1, EP.TAU / SPOKES);
        const aLeg = prog(t, B.legA, B.legB, ease.outCubic) * endFade;
        const tA = i => B.arrow0 + B.arrowStep * i;
        legendBlock(ctx, EP, rtl, 'left', LEG.leftEdge, [
          { y: LEG.y - 36, text: T('word.picture', { n: 1 }), icon: c => EP.wheelGhost(c, { x: 0, y: 30, r: 104, angle: 0, only: 0, color: SHADE.steelLight, opacity: 0.9, width: 2.4, dash: [6, 5] }) },
          { y: LEG.y + 36, text: T('word.picture', { n: 2 }), icon: c => {
            c.translate(0, 30);
            const p = EP.spokePath(104, 0, 0);
            c.fillStyle = PAL.steel; c.fill(p);
            c.lineWidth = 1.4; c.strokeStyle = rgba(PAL.paper, 0.4); c.stroke(p);
          } },
        ], aLeg);
        legendBlock(ctx, EP, rtl, 'right', LEG.rightEdge, [
          { y: LEG.y, text: T('s03.seen'), icon: c => EP.arrow(c, -34, 0, 34, 0, { kind: 'motion', dash: [9, 6], width: 5.5, headSize: 17 }) },
        ], prog(t, B.arrow0, B.arrow0 + 0.6, ease.outCubic) * endFade);

        for (let i = 0; i < SPOKES; i++) {
          const u = t - tA(i);
          if (u <= 0) continue;
          const p = ease.outCubic(clamp(u / B.arrowDur));
          const a0 = th1 + (i * EP.TAU) / SPOKES, a1 = a0 + shift;
          // this link lights up while its arrow is drawn: the old spoke (dashed) and the closest new spoke (outline)
          const lit = ease.outCubic(clamp(u / 0.3)) * (0.3 + 0.7 * (1 - ease.inOutSine(clamp((u - 0.5) / 0.9)))) * endFade;
          const g0 = { x: BIG.x, y: BIG.y, r: BIG.r, only: i, color: PAL.paper, opacity: lit };
          EP.wheelGhost(ctx, { ...g0, angle: th1, width: 3.4, dash: [8, 6] });
          EP.wheelGhost(ctx, { ...g0, angle: th2, width: 4.4 });
          ctx.save();
          ctx.globalAlpha *= endFade;
          // extension lines from the two spokes out to the ends of the arrow (dashed = old picture)
          ctx.strokeStyle = rgba(PAL.paper, 0.75 * p);
          ctx.lineWidth = 2;
          ctx.lineCap = 'round';
          for (const [a, dash] of [[a0, [4, 6]], [a1, []]]) {
            const [sx, sy] = EP.polar(BIG.x, BIG.y, BIG.r * 0.7, a), [ex, ey] = EP.polar(BIG.x, BIG.y, R_SEEN + 10, a);
            ctx.setLineDash(dash);
            ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke();
          }
          ctx.setLineDash([]);
          EP.arcArrow(ctx, BIG.x, BIG.y, R_SEEN, a0, a1, { kind: 'motion', dash: [9, 6], width: 5.5, headSize: 17, progress: p });
          ctx.restore();
        }
        const aDeg = prog(t, tA(1) + 0.3, tA(1) + 0.9, ease.outCubic) * endFade;
        if (aDeg > 0) {
          const [dx, dy] = EP.polar(BIG.x, BIG.y, R_SEEN + 40, th1 + EP.TAU / SPOKES + shift / 2);
          EP.text(ctx, EP.num(STEP) + '°', { x: dx, y: dy, anchor: 'middle', align: 'center', size: 30, weight: 700, latin: true, color: PAL.paper, opacity: aDeg });
        }
      }
    }
  },
};
