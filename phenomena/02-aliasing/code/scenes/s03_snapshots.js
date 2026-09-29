/*
 * Scene 03 - Snapshots. Opens the "See it" chapter.
 *
 * Idea: a video is a series of still pictures, 30 per second, with nothing
 * recorded in between. The brain joins the pictures by linking each spoke to
 * the closest spoke in the next picture.
 *
 * EVERYTHING on screen is computed from four numbers:
 *
 *   FR    real turning rate of the wheel ............ 1.5 turns per second
 *   FS    pictures per second of the video .......... 30
 *   SLOW  slow-motion factor while pictures are shown  15
 *   N     pictures in the strip = one second ........ 30
 *
 *   turn between two pictures = 360 * FR / FS = 18 degrees   (never typed)
 *   seconds between two pictures on screen = SLOW / FS = 0.5 s
 *   turning rate on screen while slowed = FR / SLOW = 0.1 turns per second
 *
 * TIME WARP. The wheel turns at the same REAL rate (FR) all the time. What
 * changes is how fast screen time runs compared with real time:
 *
 *   0 - 4.4 s      real time (the wheel is drawn at its true rate, no blur)
 *   4.4 - 5.4 s    time slows down, x1 to x15 (eased in the logarithm of the rate)
 *   5.4 - 9.5 s    x15 slow motion: one picture every 0.5 s on screen
 *   9.5 - 10.15 s  time speeds up again to real time
 *   after          real time: the rest of the second fills in one picture per
 *                  video frame (1/30 s), exactly like the film itself
 *
 * "rho(t)" is real seconds per screen second. The wheel angle is the integral
 * of FR * rho (EP.angleTable, computed once in setup). Picture n is taken when
 * the wheel has turned exactly n * 18 degrees since picture 0; the screen
 * time of every picture is found by inverting that angle. So the angles in the
 * cards are exact and the on-screen spacing is 0.5 s in slow motion, 1/30 s
 * in real time, and everything in between during the ramps.
 */

const DUR = 24.5;
const DEG = Math.PI / 180;

const FR = 1.5;                  // real turns per second
const FS = 30;                   // pictures per second
const SLOW = 15;                 // slow-motion factor
const N = 30;                    // pictures in one second
const STEP = 360 * FR / FS;      // degrees between two pictures (= 18)
const SPOKES = 5;

// screen-time schedule of the time warp
const TM = { downA: 4.4, downB: 5.4, shot1: 6.0, upA: 9.5, upB: 10.15 };

// ---------------------------------------------------------------- layout (px)
const WHEEL = { x: 370, y: 490, r: 148 };
const CAM = { x: 690, y: 490, s: 1.6 };
const STRIP = { x0: 96, x1: 1824, cy: 744, band: 80, card: 50 };
STRIP.pitch = (STRIP.x1 - STRIP.x0) / N;                 // one slot = one picture = one tick
const slotX = k => STRIP.x0 + STRIP.pitch * (k + 0.5);
const TICK = { y0: 796, len: 16 };
const NUM_Y = 838;                                       // running count under the ticks
const BR = { y: 858, cap: 9, notch: 11 };                // the "1 second" bracket
const LABEL_Y = 908;
const FOC = { s: 284, cy: 486, x: [560, 1360] };          // the two enlarged cards
const BIG = { x: 960, y: 610, r: 230 };                   // the overlay wheel (s04 starts here)
const CARD_R = 0.38;                                      // wheel radius / card side
const EJECT = { s: 74, yB: CAM.y + 24 * CAM.s };          // instant-camera slot: bottom edge of the body

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
  const { alpha = 1, frame = 1, wheel = 1, edge = PAL.paper, edgeAlpha = 0.9 } = o;
  if (alpha <= 0) return;
  ctx.save();
  ctx.globalAlpha *= alpha;
  if (frame > 0) {
    ctx.save();
    ctx.globalAlpha *= frame;
    EP.roundRect(ctx, cx - S / 2, cy - S / 2, S, S, S * 0.085);
    ctx.fillStyle = SHADE.inkLift;
    ctx.fill();
    ctx.lineWidth = Math.max(1.3, S * 0.0075);
    ctx.strokeStyle = rgba(edge, edgeAlpha);
    ctx.stroke();
    ctx.restore();
  }
  if (wheel > 0) EP.wheel(ctx, { x: cx, y: cy, r: S * CARD_R, angle: ang, opacity: wheel });
  ctx.restore();
}

/** The film band: dark strip, sprocket holes along both edges. `wipe` 0..1 runs it across the stage. */
function drawBand(ctx, EP, a, wipe) {
  const { PAL, SHADE, rgba } = EP;
  if (a <= 0 || wipe <= 0) return;
  const y0 = STRIP.cy - STRIP.band / 2, w = STRIP.x1 - STRIP.x0;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.beginPath();
  ctx.rect(0, 0, STRIP.x0 + w * wipe, 1080);
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

/** Where picture k is at time t: null before it is taken, else {x, y, S, a, clipY, landed}. */
function cardState(EP, k, t) {
  const t0 = ST.shots[k];
  if (t < t0) return null;
  const { clamp, ease, lerp } = EP;
  const px = slotX(k), py = STRIP.cy;
  if (k < ST.nFly) {
    // slow motion: the card slides out of the camera, drops, then runs along the strip into its slot
    const life = 0.56, u = (t - t0) / life, ue = 0.24;
    if (u >= 1) return { x: px, y: py, S: STRIP.card, a: 1, landed: true };
    if (u < ue) {
      const e = ease.outCubic(u / ue);
      return { x: CAM.x, y: lerp(EJECT.yB - EJECT.s / 2, EJECT.yB + EJECT.s / 2, e), S: EJECT.s, a: 1, clipY: EJECT.yB, landed: false };
    }
    const v = ease.inOutCubic((u - ue) / (1 - ue));
    const ex = CAM.x, ey = EJECT.yB + EJECT.s / 2, cx = CAM.x, cy = py;   // quadratic Bezier E -> C -> P
    const b0 = (1 - v) * (1 - v), b1 = 2 * v * (1 - v), b2 = v * v;
    return { x: b0 * ex + b1 * cx + b2 * px, y: b0 * ey + b1 * cy + b2 * py, S: lerp(EJECT.s, STRIP.card, ease.smooth(v)), a: 1, landed: false };
  }
  // real time: the card simply appears in its slot (a wave running across the strip)
  const life = 0.16, u = clamp((t - t0) / life);
  if (u >= 1) return { x: px, y: py, S: STRIP.card, a: 1, landed: true };
  return { x: px, y: py, S: STRIP.card * (0.6 + 0.4 * ease.outCubic(u)), a: ease.outCubic(clamp(u * 2)), landed: false };
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

/** One timeline tick: dim until its picture is taken, then paper (yellow for a moment while it is the newest). */
function drawTick(ctx, EP, k, t, a) {
  const { PAL, rgba, mix, clamp, ease } = EP;
  if (a <= 0) return;
  const age = t - ST.shots[k], lit = age >= 0;
  const x = slotX(k);
  let color, len = TICK.len, w = 2.2;
  if (!lit) color = rgba(PAL.steel, 0.42);
  else {
    const h = ease.smooth(clamp(age / 0.5));
    color = mix(PAL.highlight, PAL.paper, h);
    len += 7 * Math.sin(Math.PI * clamp(age / 0.3)) + 0;
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
  const { PAL, rgba, prog, ease } = EP;
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
  // the ghost sweep: the wheel at many angles between the two pictures, very faint
  const K = 18, r = FOC.s * CARD_R, th1 = thetaOf(0), th2 = thetaOf(1);
  for (let j = 1; j <= K; j++) {
    const aj = clamp(sweep * (K + 1) - j + 1);
    EP.wheelGhost(ctx, { x: cx, y: cy, r, angle: lerp(th1, th2, j / (K + 1)), color: PAL.paper, opacity: 0.11 * aj, width: 1.6 });
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

/** Legend row: icon and text, laid out from the reading-start side (icon on the right in Arabic). */
function legendRow(ctx, EP, rtl, x, y, w, icon, text, a) {
  if (a <= 0) return;
  const ix = rtl ? x + w - 34 : x + 34;
  const tx = rtl ? x + w - 82 : x + 82;
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.translate(ix, y);
  icon(ctx);
  ctx.restore();
  EP.text(ctx, text, { x: tx, y, anchor: 'middle', align: 'start', size: 30, weight: 600, color: EP.PAL.paper, opacity: a, maxWidth: w - 90, shrink: true, maxLines: 1 });
}

// ---------------------------------------------------------------- the scene
export default {
  duration: DUR,
  captions: [
    { key: 's03.c1', in: 0.8, out: 4.8 },
    { key: 's03.c2', in: 5.2, out: 10.6 },
    { key: 's03.c3', in: 11.0, out: 16.2 },
    { key: 's03.c4', in: 16.6, out: 19.3 },
    { key: 's03.c5', in: 19.5, out: 23.85 },
  ],
  cues: [
    { t: 0.45, sfx: 'whoosh', dur: 0.8, gain: -10 },
    { t: 0.95, sfx: 'pop', gain: -8 },
    { t: 4.4, sfx: 'swoosh_rev', dur: 1.0, gain: -6 },
    { t: 5.4, sfx: 'whoosh', dur: 0.9, gain: -8 },
    { t: 5.95, sfx: 'pop', gain: -6 },
    // one shutter per picture while slowed down: 2 per second, on the beat
    ...Array.from({ length: 8 }, (_, i) => ({ t: TM.shot1 + i * SLOW / FS, sfx: 'shutter' })),
    { t: 9.55, sfx: 'whoosh', dur: 1.1, gain: -5 },
    { t: 10.63, sfx: 'tick' },
    { t: 11.15, sfx: 'whoosh', dur: 1.0, gain: -8 },
    { t: 13.0, sfx: 'pop', gain: -8 },
    { t: 14.0, sfx: 'pop', gain: -10 },
    { t: 16.6, sfx: 'whoosh', dur: 1.3, gain: -8 },
    { t: 18.55, sfx: 'pop', gain: -10 },
    ...Array.from({ length: 5 }, (_, i) => ({ t: 20.0 + 0.4 * i, sfx: 'blip', gain: -6 })),
  ],
  math: [],
  music: 'explain',

  setup(EP) {
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
    const { PAL, SHADE, rgba, mix, prog, ease, win, clamp, lerp, T } = EP;
    const st = ST;
    EP.bg(ctx, W, H);

    const ang = st.phi0 + st.spin(t);            // the wheel's true angle now

    // ------------------------------------------------ chapter label
    const aEy = win(t, 0.4, 5.0, 0.5, 0.5);
    if (aEy > 0) EP.eyebrow(ctx, T('chapter.see'), { x: W / 2, y: 86, align: 'center', opacity: aEy, reveal: prog(t, 0.4, 1.1, ease.outCubic) });

    // ------------------------------------------------ wheel, camera, lines of sight
    const gOut = 1 - prog(t, 10.95, 11.65, ease.inOutSine);
    const aW = prog(t, 0.3, 0.95, ease.outCubic) * gOut;
    const kW = 0.9 + 0.1 * prog(t, 0.3, 1.3, ease.outCubic);
    const aC = prog(t, 0.75, 1.35, ease.outCubic) * gOut;
    const camX = CAM.x + 28 * (1 - prog(t, 0.75, 1.5, ease.outCubic));
    let ring = 0;
    for (let n = 0; n < st.nFly; n++) { const age = t - st.shots[n]; if (age >= 0 && age < 0.45) ring = age / 0.45; }

    const pF = prog(t, 1.2, 2.0, ease.inOutCubic);
    if (pF > 0 && gOut > 0) {
      const [A, B] = FOV;
      const pt = (P, q) => [lerp(P.x0, P.x1, q), lerp(P.y0, P.y1, q)];
      const [ax, ay] = pt(A, pF), [bx, by] = pt(B, pF);
      const pulse = ring > 0 ? 0.5 * (1 - ring) : 0;
      ctx.save();
      ctx.globalAlpha *= gOut;
      const g = ctx.createLinearGradient(A.x0, 0, WHEEL.x + WHEEL.r, 0);
      g.addColorStop(0, rgba(PAL.paper, 0.075));
      g.addColorStop(1, rgba(PAL.paper, 0.012));
      ctx.fillStyle = g;
      ctx.beginPath(); ctx.moveTo(A.x0, A.y0); ctx.lineTo(ax, ay); ctx.lineTo(bx, by); ctx.lineTo(B.x0, B.y0); ctx.closePath(); ctx.fill();
      ctx.strokeStyle = rgba(PAL.paper, 0.26 + pulse);
      ctx.lineWidth = 1.8;
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(A.x0, A.y0); ctx.lineTo(ax, ay); ctx.moveTo(B.x0, B.y0); ctx.lineTo(bx, by); ctx.stroke();
      ctx.restore();
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
    const wipe = prog(t, 5.35, 6.15, ease.outQuint);
    const aStrip = 1 - prog(t, 16.4, 17.2, ease.inOutSine);
    const dim = 1 - 0.68 * prog(t, 11.4, 12.3, ease.inOutSine);      // the strip steps back while two cards are enlarged
    if (t > 5.3 && aStrip > 0) {
      ctx.save();
      ctx.globalAlpha *= aStrip * dim;
      drawBand(ctx, EP, 1, wipe);
      for (let k = 0; k < N; k++) {
        const aK = prog(t, 5.42 + 0.02 * k, 5.85 + 0.02 * k, ease.outCubic);
        drawSlot(ctx, EP, k, aK);
      }
      for (let k = 0; k < N; k++) drawTick(ctx, EP, k, t, prog(t, 5.5 + 0.02 * k, 5.9 + 0.02 * k, ease.outCubic));
      // landed cards, then the ones still in flight (newest on top)
      const flying = [];
      for (let k = 0; k < N; k++) {
        const s = cardState(EP, k, t);
        if (!s) continue;
        if (s.landed) drawCard(ctx, EP, s.x, s.y, s.S, thetaOf(k), { alpha: s.a, edgeAlpha: 0.8 });
        else flying.push([k, s]);
      }
      for (const [k, s] of flying) {
        ctx.save();
        if (s.clipY) { ctx.beginPath(); ctx.rect(0, s.clipY, W, H); ctx.clip(); }
        drawCard(ctx, EP, s.x, s.y, s.S, thetaOf(k), { alpha: s.a });
        ctx.restore();
      }
      // running count under the newest tick
      let cnt = 0;
      for (let k = 0; k < N; k++) if (t >= st.shots[k]) cnt = k + 1;
      if (cnt > 0) {
        const aN = 1 - prog(t, 11.0, 11.5, ease.inOutSine);
        EP.textTab(ctx, EP.num(cnt), { x: slotX(cnt - 1), y: NUM_Y, size: 26, weight: 700, align: 'center', color: PAL.highlight, opacity: aN });
      }
      // bracket and label
      const done = prog(t, st.shots[N - 1], st.shots[N - 1] + 0.4, ease.inOutSine);
      const aBr = 1 - prog(t, 11.0, 11.6, ease.inOutSine);
      ctx.save();
      ctx.globalAlpha *= aBr;
      drawBracket(ctx, EP, T, prog(t, 5.7, 6.35, ease.outCubic), prog(t, 5.95, 6.5, ease.outCubic), done);
      ctx.restore();
      ctx.restore();
    }

    // ------------------------------------------------ beat 3 and 4: two consecutive pictures
    if (t > 11.0) {
      // the two source thumbnails are marked while their copies are enlarged
      const pair = [0, 1].map(i => {
        const g = prog(t, 11.2 + 0.1 * i, 12.4 + 0.1 * i, ease.inOutCubic);
        const m = prog(t, 16.6, 18.35, ease.inOutCubic);
        const gx = lerp(slotX(i), FOC.x[i], g), gy = lerp(STRIP.cy, FOC.cy, g), gS = lerp(STRIP.card, FOC.s, g);
        return { g, m, x: lerp(gx, BIG.x, m), y: lerp(gy, BIG.y, m), S: lerp(gS, BIG.r / CARD_R, m) };
      });
      const m = pair[0].m;

      // yellow marks on the two source slots
      const aMark = prog(t, 11.05, 11.5, ease.outCubic) * (1 - prog(t, 16.4, 17.0, ease.inOutSine));
      if (aMark > 0) {
        ctx.save();
        ctx.strokeStyle = rgba(PAL.highlight, aMark);
        ctx.lineWidth = 2.4;
        for (let i = 0; i < 2; i++) { EP.roundRect(ctx, slotX(i) - 29, STRIP.cy - 29, 58, 58, 6); ctx.stroke(); }
        ctx.restore();
      }

      // the gap between them
      const aGap = prog(t, 12.3, 13.0, ease.outCubic) * (1 - prog(t, 16.35, 16.9, ease.inOutSine));
      drawGap(ctx, EP, T, aGap, prog(t, 12.6, 13.8, ease.inOutSine));

      // labels under the cards, and the time between the pictures
      const aLab = prog(t, 12.4, 13.0, ease.outCubic) * (1 - prog(t, 16.35, 16.9, ease.inOutSine));
      if (aLab > 0) {
        const yD = FOC.cy + FOC.s / 2 + 36;
        for (let i = 0; i < 2; i++) EP.text(ctx, T('word.picture', { n: i + 1 }), { x: FOC.x[i], y: yD + 10, align: 'center', size: 30, weight: 600, color: PAL.paper, opacity: aLab, maxWidth: 240, shrink: true, maxLines: 1 });
      }
      const aDim = prog(t, 13.7, 14.4, ease.outCubic) * (1 - prog(t, 16.35, 16.9, ease.inOutSine));
      if (aDim > 0) {
        const yD = FOC.cy + FOC.s / 2 + 36 - 11, xa = FOC.x[0] + 96, xb = FOC.x[1] - 96;
        const lab = EP.num(1) + '/' + EP.num(N) + ' s';
        const lw = EP.measure(ctx, lab, { size: 32, weight: 600, latin: true }).w;
        ctx.save();
        ctx.globalAlpha *= aDim;
        ctx.strokeStyle = rgba(PAL.paper, 0.7);
        ctx.lineWidth = 2.2;
        ctx.lineCap = 'round';
        const xc = (xa + xb) / 2, hw = ((xb - xa) / 2) * ease.outCubic(prog(t, 13.7, 14.6));
        ctx.beginPath();
        ctx.moveTo(xc - hw, yD); ctx.lineTo(xc - lw / 2 - 14, yD);
        ctx.moveTo(xc + lw / 2 + 14, yD); ctx.lineTo(xc + hw, yD);
        ctx.moveTo(xa, yD - 9); ctx.lineTo(xa, yD + 9);
        ctx.moveTo(xb, yD - 9); ctx.lineTo(xb, yD + 9);
        ctx.stroke();
        ctx.restore();
        EP.text(ctx, lab, { x: xc, y: yD, anchor: 'middle', align: 'center', size: 32, weight: 600, latin: true, color: PAL.paper, opacity: aDim });
      }

      // the two cards (copies of the thumbnails): they grow out of the strip, then merge into one wheel
      const c0 = pair[0], c1 = pair[1];
      const fr0 = (1 - prog(m, 0.08, 0.5, ease.inOutSine)), fr1 = fr0;
      const gA0 = prog(t, 11.2, 11.3);
      if (gA0 > 0) {
        drawCard(ctx, EP, c0.x, c0.y, c0.S, thetaOf(0), { frame: fr0, wheel: 1 - prog(m, 0.28, 0.62, ease.inOutSine) });
        drawCard(ctx, EP, c1.x, c1.y, c1.S, thetaOf(1), { frame: fr1, wheel: 1 });
        // picture 1 becomes a dashed ghost as it joins picture 2
        const gh = prog(m, 0.4, 0.8, ease.inOutSine);
        if (gh > 0) EP.wheelGhost(ctx, { x: c0.x, y: c0.y, r: c0.S * CARD_R, angle: thetaOf(0), color: PAL.paper, opacity: 0.85 * gh * (1 - prog(t, 23.6, 24.3, ease.inOutSine)), width: 2.6 + 1.2 * m, dash: [9 + 4 * m, 7 + 3 * m] });
      }

      // ---- beat 4: the overlay wheel, its legend and the links between spokes
      const endFade = 1 - prog(t, 23.6, 24.3, ease.inOutSine);
      const th1 = thetaOf(0), th2 = thetaOf(1);
      const shift = EP.wrapSigned(th2 - th1, EP.TAU / SPOKES);     // the closest spoke of the next picture: shortest way round
      const aLeg = prog(t, 18.55, 19.2, ease.outCubic) * endFade;
      const LX = 300;
      legendRow(ctx, EP, rtl, LX, 566, 340, c => {
        c.translate(0, 26);
        EP.wheelGhost(c, { x: 0, y: 0, r: 70, angle: 0, only: 0, color: PAL.paper, opacity: 0.85, width: 2.2, dash: [6, 5] });
      }, T('word.picture', { n: 1 }), aLeg);
      legendRow(ctx, EP, rtl, LX, 632, 340, c => {
        c.translate(0, 26);
        const p = EP.spokePath(70, 0, 0);
        c.fillStyle = PAL.steel; c.fill(p);
        c.lineWidth = 1.2; c.strokeStyle = rgba(PAL.paper, 0.4); c.stroke(p);
      }, T('word.picture', { n: 2 }), aLeg);

      const tA = i => 20.0 + 0.4 * i;
      const aSeen = prog(t, 20.0, 20.6, ease.outCubic) * endFade;
      legendRow(ctx, EP, rtl, 1290, 598, 420, c => {
        c.beginPath();
        EP.arrow(c, -22, 0, 22, 0, { kind: 'motion', dash: [7, 6], width: 4.5, headSize: 16 });
      }, T('s03.seen'), aSeen);

      const rA = BIG.r * 0.78;
      for (let i = 0; i < SPOKES; i++) {
        const p = ease.outCubic(clamp((t - tA(i)) / 0.5));
        if (p <= 0) continue;
        const a0 = th1 + (i * EP.TAU) / SPOKES, a1 = a0 + shift;
        ctx.save();
        ctx.globalAlpha *= endFade;
        // hairline guides from the two spoke tips to the ends of the arrow
        ctx.strokeStyle = rgba(PAL.paper, 0.32 * p);
        ctx.lineWidth = 1.5;
        for (const a of [a0, a1]) {
          const [sx, sy] = EP.polar(BIG.x, BIG.y, BIG.r * 0.665, a), [ex, ey] = EP.polar(BIG.x, BIG.y, rA, a);
          ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke();
        }
        EP.arcArrow(ctx, BIG.x, BIG.y, rA, a0, a1, { kind: 'motion', dash: [7, 6], width: 10, color: PAL.ink, alpha: 0.85, headSize: 16, progress: p });
        EP.arcArrow(ctx, BIG.x, BIG.y, rA, a0, a1, { kind: 'motion', dash: [7, 6], width: 4.5, headSize: 16, progress: p });
        ctx.restore();
      }
      const aDeg = prog(t, 20.7, 21.3, ease.outCubic) * endFade;
      if (aDeg > 0) {
        const am = th1 + shift / 2, [dx, dy] = EP.polar(BIG.x, BIG.y, BIG.r + 40, am);
        EP.text(ctx, EP.num(STEP) + '°', { x: dx, y: dy, anchor: 'middle', align: 'center', size: 32, weight: 700, latin: true, color: PAL.paper, opacity: aDeg });
      }
    }
  },
};
