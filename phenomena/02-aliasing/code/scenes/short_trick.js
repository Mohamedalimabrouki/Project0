/*
 * Short (9:16, 1080 x 1920) - scene 2: the trick (22.5 s).
 *
 * One big wheel, spoke 0 painted yellow. Pictures are shown one per second
 * (slowed down x30, because the real gap is 1/30 s), each 66 degrees further
 * round: 66 degrees is 5.5 turns per second at 30 pictures per second.
 *
 *   picture n      wheel angle 66 (n - 1) degrees, exactly
 *   ghost          where the spokes were in picture n - 1
 *   solid arc      the real turn of the painted spoke, +66 degrees
 *   gap bracket    one spoke gap = 360 / 5 = 72 degrees
 *   dashed arc     the closest match = wrapSigned(66, 72) = -6 degrees (backwards)
 *
 * The annotations build up with the narration (gap, "just short", backwards),
 * replaying on every picture. At t = 18 s the same wheel runs at its real
 * rate, 66 degrees per video frame, exact: your own screen shows the creep.
 */

const TAU = Math.PI * 2, DEG = Math.PI / 180;
const SPOKES = 5;
const TURN = 66;                      // degrees per picture (5.5 turns per second at 30 pictures per second)
const GAP = 360 / SPOKES;             // 72 degrees between neighbouring spokes
const FPS = 30;
const STEP = 1.0;                     // seconds between slowed-down pictures: x30
const N_LAST = 17;                    // last slowed-down picture
const T_SWITCH = 18.0;                // real speed starts here
const T_FREEZE = 0.5;                 // the cross-fade ends: the wheel from the hook stops on picture 1
const HOOK_RATE = 6.25;               // turns per second at the end of the hook, continued through the cross-fade
const REAL_RATE = TURN * FPS / 360;   // 5.5 turns per second

// ----------------------------------------------------------------- layout (px)
const X = 540;
const Y_START = 1070, R_START = 300;  // where the hook leaves the wheel (same place, same size)
const Y_MAIN = 1000, R_MAIN = 330;
const LEFT = 60, RIGHT = 920;         // text margins; the right edge stays free for the app buttons
const ROW_TOP = 612;                  // badge and picture counter
// the "unrolled rim" ruler under the wheel: one spoke gap (72 degrees) drawn 780 px wide, so 66 and 6 degrees are readable
const RX0 = 110, RPX = 780 / 72;      // x of 0 degrees, pixels per degree (a diagram: never mirrored)
const xd = deg => RX0 + RPX * deg;
const Y_LBL1 = 1404, Y_ARROW = 1430, Y_RULER = 1458, Y_DASH = 1497, Y_LBL2 = 1514;   // all above y = 1536

// ----------------------------------------------------------------- the wheel
const pic = t => Math.max(1, Math.min(N_LAST, Math.floor(t / STEP + 1e-6)));

/** Exact wheel angle (rad, clockwise) at scene time t. */
function wheelAngle(t) {
  if (t < T_FREEZE) return TAU * HOOK_RATE * (t - T_FREEZE);          // the hook's real motion, on into the cross-fade
  if (t < T_SWITCH) return TURN * (pic(t) - 1) * DEG;                 // pictures, one per second
  return TURN * N_LAST * DEG + TAU * REAL_RATE * (t - T_SWITCH);      // real speed: 66 degrees per video frame
}

// ----------------------------------------------------------------- small drawing helpers
function arcPath(ctx, cx, cy, r, a0, a1) {
  ctx.beginPath();
  ctx.arc(cx, cy, r, a0 - Math.PI / 2, a1 - Math.PI / 2, a1 < a0);
}

/** Thin bracket along a circle from a0 to a1 with small radial ticks at both ends. p = 0..1 draws it growing. */
function bracket(EP, ctx, cx, cy, r, a0, a1, o = {}) {
  const { p = 1, alpha = 1, color = EP.PAL.paper, width = 3, tick = 9, dash = null } = o;
  if (p <= 0 || alpha <= 0) return;
  const end = a0 + (a1 - a0) * p;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round';
  if (dash) ctx.setLineDash(dash);
  arcPath(ctx, cx, cy, r, a0, end); ctx.stroke();
  ctx.setLineDash([]);
  for (const a of [a0, end]) {
    const [x1, y1] = EP.polar(cx, cy, r - tick, a), [x2, y2] = EP.polar(cx, cy, r + tick, a);
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
  }
  ctx.restore();
}

/** "+66°  Real turn": value (digits do not jitter) and a word, drawn left to right, group aligned at x. */
function tag(EP, ctx, x, y, value, word, o = {}) {
  const { align = 'center', alpha = 1, vSize = 46, wSize = 30, unit = null } = o;
  const vW = EP.textTab(ctx, value, { size: vSize, weight: 800, opacity: 0 }).w;
  const uW = unit ? EP.measure(ctx, unit, { size: 27, weight: 600 }).w : 0;
  const wW = EP.measure(ctx, word, { size: wSize, weight: 600, maxWidth: 330, shrink: true, maxLines: 1 });
  const gap = 12;
  const total = vW + (unit ? 8 + uW : 0) + gap + wW.w;
  let cx = align === 'right' ? x - total : align === 'left' ? x : x - total / 2;
  EP.textTab(ctx, value, { x: cx, y, size: vSize, weight: 800, color: EP.PAL.paper, opacity: alpha, align: 'left' }); cx += vW;
  if (unit) { EP.text(ctx, unit, { x: cx + 8, y, size: 27, weight: 600, color: EP.PAL.steel, opacity: alpha, align: 'left' }); cx += 8 + uW; }
  EP.text(ctx, word, { x: cx + gap, y, size: wSize, weight: 600, color: EP.PAL.steel, opacity: alpha, align: 'left', maxWidth: 330, shrink: true, maxLines: 1 });
  return total;
}

function dot(ctx, x, y, r, o = {}) {
  const { fill = null, stroke = null, width = 3.5, alpha = 1, dash = null } = o;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; if (dash) ctx.setLineDash(dash); ctx.stroke(); }
  ctx.restore();
}

export default {
  duration: 22.5,
  strings: ['s03_snapshots', 's04_trick'],
  captionBand: { y: 366 },
  captions: [
    { key: 's03.c2', in: 0.8, out: 5.2 },
    { key: 's04.c3', in: 5.6, out: 10.0 },
    { key: 's04.c4', in: 10.4, out: 15.2 },
    { key: 's04.c5', in: 15.6, out: 21.9 },
  ],
  cues: [
    ...Array.from({ length: N_LAST }, (_, i) => ({ t: i + 1, sfx: 'shutter' })),   // one per picture
    { t: T_SWITCH, sfx: 'click' },
    { t: T_SWITCH, sfx: 'whirr', dur: 4.5, rate: REAL_RATE },
  ],
  music: 'explain',

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, ease, prog, text, T, num } = EP;
    EP.bg(ctx, W, H);

    const stepping = t >= T_FREEZE && t < T_SWITCH;
    const n = pic(t);
    const age = t - n;                                                    // seconds since this picture was taken
    const theta = wheelAngle(t);

    // the wheel eases from the hook's place and size into the main position
    const kM = prog(t, T_FREEZE, 1.4, ease.inOutCubic);
    const R = R_START + (R_MAIN - R_START) * kM;
    const Y = Y_START + (Y_MAIN - Y_START) * kM;
    const paint = prog(t, 0.8, 1.4, ease.outCubic) * (1 - prog(t, T_SWITCH + 0.4, T_SWITCH + 1.6, ease.inOutSine));
    EP.wheel(ctx, { x: X, y: Y, r: R, angle: theta, highlight: 0, highlightAlpha: paint });

    // ---- annotations on the wheel (slowed-down pictures only)
    const env = 1 - prog(t, T_SWITCH, T_SWITCH + 0.3, ease.inOutSine);
    const seen = EP.wrapSigned(TURN, GAP);                                  // -6 degrees: the closest match
    const phB = t >= 6, phC = t >= 11, phD = t >= 16;
    let aG = 0, glide = 0;                                                  // ghost angle, glide progress (shared with the ruler)
    if (t >= 2 && env > 0) {
      const aPrev = TURN * (n - 2) * DEG, aNew = aPrev + TURN * DEG, aNext = aPrev + GAP * DEG;
      glide = phD ? prog(age, 0.45, 0.9, ease.inOutCubic) : 0;
      aG = aPrev + seen * DEG * glide;                                      // "the closest match": the ghost glides back onto the nearest new spokes
      const pSolid = prog(age, 0.05, 0.5, ease.outCubic);
      const pWedge = phB ? prog(age, 0.1, 0.5, ease.outCubic) * (1 - glide) : 0;
      const pShort = phC ? prog(age, 0.4, 0.7, ease.outCubic) * (1 - glide) : 0;
      const wedge = (a0, a1, alpha, color) => {
        ctx.save(); ctx.globalAlpha *= alpha * env; ctx.fillStyle = color;
        ctx.beginPath(); ctx.moveTo(X, Y); ctx.arc(X, Y, R * 0.66, a0 - Math.PI / 2, a1 - Math.PI / 2); ctx.closePath(); ctx.fill(); ctx.restore();
      };
      // one spoke gap: the wedge between the old painted spoke and the old next spoke; the last 6 degrees of it are "just short"
      if (pWedge > 0) wedge(aPrev, aPrev + GAP * DEG * pWedge, 0.14, PAL.paper);
      if (pShort > 0) wedge(aNew, aNext, 0.42 * pShort, PAL.highlight);

      // where the spokes were in the previous picture (outlines)
      EP.wheelGhost(ctx, { x: X, y: Y, r: R, angle: aG, color: PAL.paper, opacity: 0.24 * env, width: 1.6 });
      if (phB) EP.wheelGhost(ctx, { x: X, y: Y, r: R, angle: aG, color: PAL.paper, opacity: (phC ? 0.95 : 0.7) * prog(age, 0.1, 0.4) * env, width: phC ? 4 : 3, only: 1 });
      EP.wheelGhost(ctx, { x: X, y: Y, r: R, angle: aG, color: PAL.highlight, opacity: 0.95 * env, width: 3.5, only: 0 });

      // the real turn of the painted spoke: solid blue arc round the tyre, +66 degrees
      const rS = R + 20;
      if (pSolid > 0) {
        EP.arcArrow(ctx, X, Y, rS, aPrev, aNew, { width: 8, headSize: 30, progress: pSolid, alpha: env });
        dot(ctx, ...EP.polar(X, Y, rS, aPrev), 7.5, { fill: PAL.motion, alpha: env });
      }
    }

    // ---- top row: honest badge, camera and picture counter
    const xs = rtl ? RIGHT : LEFT, xe = rtl ? LEFT : RIGHT;
    const kSlow = prog(t, 0.6, 1.1, ease.outCubic) * (1 - prog(t, T_SWITCH - 0.05, T_SWITCH + 0.2, ease.inOutSine));
    const kReal = prog(t, T_SWITCH + 0.05, T_SWITCH + 0.4, ease.outCubic);
    EP.badge(ctx, T('badge.slowx', { n: 30 }), { x: xs, y: ROW_TOP, align: 'start', size: 26, opacity: kSlow });
    EP.badge(ctx, T('badge.real'), { x: xs, y: ROW_TOP, align: 'start', size: 26, opacity: kReal });

    const camOp = (t >= 1 ? prog(t, 1, 1.3) : 0) * (1 - prog(t, T_SWITCH - 0.05, T_SWITCH + 0.25, ease.inOutSine));
    if (camOp > 0) {
      const camX = rtl ? xe + 152 + 58 : xe - 152 - 58;                    // fixed: the number changes, the icon does not move
      const shot = age >= 0 && age < 0.55 && t >= 1 ? age / 0.55 : 0;
      EP.camera(ctx, { x: camX, y: ROW_TOP, s: 0.78, opacity: camOp, shot });
      text(ctx, T('word.picture', { n }), { x: rtl ? camX - 40 : camX + 40, y: ROW_TOP + 12, size: 34, weight: 700, color: PAL.paper, opacity: camOp, align: rtl ? 'right' : 'left' });
    }

    // ---- the ruler: one spoke gap (72 degrees) unrolled, drawn to scale
    const real = prog(t, T_SWITCH + 0.1, T_SWITCH + 0.5, ease.outCubic);     // per-second wording after the switch
    const slow = 1 - real;
    const aArrow = prog(t, 2.1, 2.6, ease.outCubic);
    const aRuler = phB ? prog(t, 6.0, 6.5, ease.outCubic) : 0;
    const aSliver = phC ? prog(t, 11.0, 11.5, ease.outCubic) : 0;
    const aDash = phD ? prog(t, 16.0, 16.5, ease.outCubic) : 0;
    const yellowGhost = { stroke: PAL.highlight }, whiteGhost = { stroke: PAL.paper };
    if (aArrow > 0) {
      // real turn: solid blue, +66 degrees (long)
      EP.arrow(ctx, xd(0), Y_ARROW, xd(TURN), Y_ARROW, { kind: 'motion', width: 8, headSize: 30, alpha: aArrow });
      dot(ctx, xd(0), Y_ARROW, 7.5, { fill: PAL.motion, alpha: aArrow });
      const cxA = (xd(0) + xd(TURN)) / 2;
      tag(EP, ctx, cxA, Y_LBL1, '+' + num(TURN) + '°', T('s04.real'), { alpha: aArrow * slow });
      tag(EP, ctx, cxA, Y_LBL1, num(REAL_RATE, 1), T('s04.real'), { alpha: aArrow * real, unit: T('unit.turns') });
    }
    if (aRuler > 0) {
      // the ruler line with its markers: old painted spoke (0), new painted spoke (66), old next spoke (72)
      ctx.save(); ctx.globalAlpha *= aRuler * slow;
      ctx.strokeStyle = EP.rgba(PAL.steel, 0.9); ctx.lineWidth = 4; ctx.lineCap = 'round';
      ctx.beginPath(); ctx.moveTo(xd(0), Y_RULER); ctx.lineTo(xd(GAP), Y_RULER); ctx.stroke();
      ctx.restore();
      if (aSliver > 0) {                                                   // just short: the last 6 degrees
        ctx.save(); ctx.globalAlpha *= aSliver * slow; ctx.strokeStyle = PAL.highlight; ctx.lineWidth = 7; ctx.lineCap = 'butt';
        ctx.beginPath(); ctx.moveTo(xd(TURN), Y_RULER); ctx.lineTo(xd(GAP), Y_RULER); ctx.stroke(); ctx.restore();
      }
      dot(ctx, xd(0), Y_RULER, 9, { stroke: PAL.highlight, width: 3.5, alpha: aRuler * slow });                     // where the painted spoke was
      dot(ctx, xd(TURN), Y_RULER, 9.5, { fill: PAL.highlight, alpha: aRuler * slow });                              // where it is now
      // where the next spoke was (72): slides back 6 degrees onto the painted spoke = the closest match
      const xNext = xd(GAP + seen * glide);
      dot(ctx, xNext, Y_RULER, 12, { stroke: PAL.paper, width: 3.5, alpha: aRuler * slow });
      tag(EP, ctx, xd(0) - 14, Y_LBL2, num(GAP) + '°', T('s04.gap'), { align: 'left', alpha: aRuler * slow });
    }
    if (aDash > 0) {
      // closest match: dashed blue, -6 degrees (short), backwards. The chart stays; only the ring above slides with the ghost.
      EP.arrow(ctx, xd(GAP), Y_DASH, xd(TURN), Y_DASH, { kind: 'motion', width: 8, headSize: 26, dash: [7, 6], alpha: slow, progress: prog(t, 16.0, 16.6, ease.outCubic) });
      tag(EP, ctx, xd(TURN) - 22, Y_LBL2, num(seen) + '°', T('s04.backwards'), { align: 'right', alpha: aDash * slow });
    }
    if (real > 0) {                                                        // the same picture, per second: 66 -> 5.5 turns, -6 -> -0.5 turns
      EP.arrow(ctx, xd(GAP), Y_DASH, xd(TURN), Y_DASH, { kind: 'motion', width: 8, headSize: 26, dash: [7, 6], alpha: real });
      tag(EP, ctx, xd(TURN) - 22, Y_LBL2, num(seen * FPS / 360, 1), T('s04.backwards'), { align: 'right', alpha: real, unit: T('unit.turns') });
    }
  },
};
