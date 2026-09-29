/*
 * Short (9:16, 1080 x 1920) - scene 2: the trick (22.5 s).
 *
 * One big wheel, spoke 0 painted yellow. Pictures are shown one per second
 * (slowed down x30, because the real gap is 1/30 s), each 66 degrees further
 * round: 66 degrees per picture is 5.5 turns per second at 30 pictures per second.
 *
 * On the wheel (replayed on every picture, building up with the narration):
 *   ghost          where the spokes were in picture n - 1 (outlines; the painted one in yellow)
 *   solid arc      the real turn of the painted spoke, +66 degrees, clockwise
 *   gap wedge      one spoke gap = 360 / 5 = 72 degrees, between two neighbouring old spokes
 *   just short     the last 6 degrees of that gap, in yellow: the new spoke lands 6 degrees short of the old next one
 *   glide          the closest match = EP.wrapSigned(66, 72) = -6 degrees: the ghost slides BACK onto the nearest new spokes
 * Under the wheel, the same story to scale (the "unrolled rim": 72 degrees drawn 780 px wide, so +66 and -6 are
 * readable arrows): solid blue +66 (real turn), dashed blue -6 (backwards). At the switch the same picture is
 * restated per second: 66 x 30 / 360 = 5.5 turns per second real, -6 x 30 / 360 = -0.5 turns per second seen.
 *
 * Real speed (from 18 s): the wheel turns 66 degrees per video frame, exact, no blur, so your own screen shows
 * the backwards creep. The paint fades after the switch, so all five spokes look alike.
 *
 * The first 0.5 s continues the hook's wheel exactly (same place, size and angle) through the cross-fade,
 * then the wheel stops on picture 1 with the painted spoke at 12 o'clock.
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

/** Exact wheel angle (rad, clockwise) at scene time t. (Exported for the physics checks.) */
export function wheelAngle(t) {
  if (t < T_FREEZE) return TAU * HOOK_RATE * (t - T_FREEZE);          // the hook's real motion, on into the cross-fade
  if (t < T_SWITCH) return TURN * (pic(t) - 1) * DEG;                 // pictures, one per second
  return TURN * N_LAST * DEG + TAU * REAL_RATE * (t - T_SWITCH);      // real speed: 66 degrees per video frame
}

// ----------------------------------------------------------------- small drawing helpers
/**
 * Extras on the tyre that never betray the spin: fine sidewall rings (circles look the same at every angle),
 * the light catching the tyre's shoulder, and the arch's shadow on the top of the tyre.
 */
function tyreDetail(EP, ctx, x, y, r) {
  const { PAL, SHADE, rgba } = EP;
  ctx.save();
  ctx.lineWidth = Math.max(1, r * 0.008);
  ctx.strokeStyle = rgba(PAL.paper, 0.07);
  ctx.beginPath(); ctx.arc(x, y, r * 0.87, 0, EP.TAU); ctx.stroke();
  ctx.strokeStyle = rgba(SHADE.inkDeep, 0.45);
  ctx.beginPath(); ctx.arc(x, y, r * 0.715, 0, EP.TAU); ctx.stroke();
  const a0 = -165 * EP.DEG, span = 75 * EP.DEG, cg = ctx.createConicGradient(a0, x, y);
  cg.addColorStop(0, rgba(PAL.paper, 0));
  cg.addColorStop(span / EP.TAU / 2, rgba(PAL.paper, 0.24));
  cg.addColorStop(span / EP.TAU, rgba(PAL.paper, 0));
  cg.addColorStop(1, rgba(PAL.paper, 0));
  ctx.lineWidth = Math.max(1.5, r * 0.012);
  ctx.strokeStyle = cg;
  ctx.beginPath(); ctx.arc(x, y, r * 0.985, a0, a0 + span); ctx.stroke();
  ctx.restore();
  ctx.save();
  ctx.beginPath(); ctx.arc(x, y, r, 0, EP.TAU); ctx.arc(x, y, r * 0.70, 0, EP.TAU, true);
  ctx.clip('evenodd');
  const ao = ctx.createLinearGradient(0, y - r, 0, y - 0.2 * r);
  ao.addColorStop(0, rgba(SHADE.inkDeep, 0.5)); ao.addColorStop(1, rgba(SHADE.inkDeep, 0));
  ctx.fillStyle = ao;
  ctx.fillRect(x - r, y - r, 2 * r, 0.9 * r);
  ctx.restore();
}

/**
 * "+66°  Real turn": a value (digits do not jitter), an optional unit and a word, drawn as one group aligned at x.
 * Visual order left to right: value, unit, word in English and French; unit, value, word in Arabic
 * (read from the right: word, value, unit). Numbers and degree signs always stay left to right.
 */
function tag(EP, ctx, x, y, value, word, o = {}) {
  const { align = 'center', alpha = 1, vSize = 46, wSize = 30, unit = null, rtl = false } = o;
  const vW = EP.textTab(ctx, value, { size: vSize, weight: 800, opacity: 0 }).w;
  const uW = unit ? EP.measure(ctx, unit, { size: 27, weight: 600 }).w : 0;
  const wW = EP.measure(ctx, word, { size: wSize, weight: 600, maxWidth: 330, shrink: true, maxLines: 1 }).w;
  const gap = 12, g2 = 9;
  const total = vW + (unit ? g2 + uW : 0) + gap + wW;
  let cx = align === 'right' ? x - total : align === 'left' ? x : x - total / 2;
  const drawValue = () => { EP.textTab(ctx, value, { x: cx, y, size: vSize, weight: 800, color: EP.PAL.paper, opacity: alpha, align: 'left' }); cx += vW; };
  const drawUnit = () => { EP.text(ctx, unit, { x: cx, y, size: 27, weight: 600, color: EP.PAL.steel, opacity: alpha, align: 'left' }); cx += uW; };
  if (unit && rtl) { drawUnit(); cx += g2; drawValue(); }
  else { drawValue(); if (unit) { cx += g2; drawUnit(); } }
  EP.text(ctx, word, { x: cx + gap, y, size: wSize, weight: 600, color: EP.PAL.steel, opacity: alpha, align: 'left', maxWidth: 330, shrink: true, maxLines: 1 });
  return total;
}

function dot(ctx, x, y, r, o = {}) {
  const { fill = null, stroke = null, width = 3.5, alpha = 1 } = o;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.beginPath(); ctx.arc(x, y, r, 0, TAU);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = width; ctx.stroke(); }
  ctx.restore();
}

export default {
  duration: 22.5,
  strings: ['s03_snapshots', 's04_trick'],
  captionBand: { y: 366 },
  captions: [
    // band widths chosen so the lines break at natural places in English, French and Arabic (see the report)
    { key: 's03.c2', in: 0.8, out: 5.2, band: { maxWidth: 824 } },
    { key: 's04.c3', in: 5.6, out: 10.0, band: { maxWidth: 790 } },
    { key: 's04.c4', in: 10.4, out: 15.2, band: { maxWidth: 840 } },
    { key: 's04.c5', in: 15.6, out: 21.9, band: { maxWidth: 940 } },
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

    const n = pic(t);
    const age = t - n;                                                    // seconds since this picture was taken
    const theta = wheelAngle(t);

    // the wheel eases from the hook's place and size into the main position
    const kM = prog(t, T_FREEZE, 1.4, ease.inOutCubic);
    const R = R_START + (R_MAIN - R_START) * kM;
    const Y = Y_START + (Y_MAIN - Y_START) * kM;
    const paint = prog(t, 0.8, 1.4, ease.outCubic) * (1 - prog(t, T_SWITCH + 0.4, T_SWITCH + 1.6, ease.inOutSine));
    EP.wheel(ctx, { x: X, y: Y, r: R, angle: theta, highlight: 0, highlightAlpha: paint });
    tyreDetail(EP, ctx, X, Y, R);

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
    // the swap is sequential (old label gone, then the new one arrives), so two texts never overlap
    const kSlow = prog(t, 0.6, 1.1, ease.outCubic) * (1 - prog(t, T_SWITCH - 0.05, T_SWITCH + 0.1, ease.inOutSine));
    const kReal = prog(t, T_SWITCH + 0.12, T_SWITCH + 0.4, ease.outCubic);
    EP.badge(ctx, T('badge.slowx', { n: 30 }), { x: xs, y: ROW_TOP, align: 'start', size: 26, opacity: kSlow });
    EP.badge(ctx, T('badge.real'), { x: xs, y: ROW_TOP, align: 'start', size: 26, opacity: kReal });

    const camOp = (t >= 1 ? prog(t, 1, 1.3) : 0) * (1 - prog(t, T_SWITCH - 0.05, T_SWITCH + 0.15, ease.inOutSine));
    if (camOp > 0) {
      const camX = rtl ? xe + 152 + 58 : xe - 152 - 58;                    // fixed: the number changes, the icon does not move
      const shot = age >= 0 && age < 0.55 && t >= 1 ? age / 0.55 : 0;
      EP.camera(ctx, { x: camX, y: ROW_TOP, s: 0.78, opacity: camOp, shot });
      text(ctx, T('word.picture', { n }), { x: rtl ? camX - 40 : camX + 40, y: ROW_TOP + 12, size: 34, weight: 700, color: PAL.paper, opacity: camOp, align: rtl ? 'right' : 'left' });
    }

    // ---- the ruler: one spoke gap (72 degrees) unrolled, drawn to scale
    const slow = 1 - prog(t, T_SWITCH, T_SWITCH + 0.2, ease.inOutSine);       // per-picture wording leaves ...
    const real = prog(t, T_SWITCH + 0.25, T_SWITCH + 0.6, ease.outCubic);   // ... then the per-second wording arrives
    const aArrow = prog(t, 2.1, 2.6, ease.outCubic);
    const aRuler = phB ? prog(t, 6.0, 6.5, ease.outCubic) : 0;
    const aSliver = phC ? prog(t, 11.0, 11.5, ease.outCubic) : 0;
    const aDash = phD ? prog(t, 16.0, 16.5, ease.outCubic) : 0;
    if (aArrow > 0) {
      // real turn: solid blue, +66 degrees (long)
      EP.arrow(ctx, xd(0), Y_ARROW, xd(TURN), Y_ARROW, { kind: 'motion', width: 8, headSize: 30, alpha: aArrow });
      dot(ctx, xd(0), Y_ARROW, 7.5, { fill: PAL.motion, alpha: aArrow });
      const cxA = (xd(0) + xd(TURN)) / 2;
      tag(EP, ctx, cxA, Y_LBL1, '+' + num(TURN) + '°', T('s04.real'), { alpha: aArrow * slow });
      tag(EP, ctx, cxA, Y_LBL1, num(REAL_RATE, 1), T('s04.real'), { alpha: aArrow * real, unit: T('unit.turns'), rtl });
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
    if (aDash > 0 || real > 0) {
      // closest match: dashed blue, -6 degrees (short), backwards. The chart stays; only the ring above slides with the ghost.
      // The arrow itself is the same before and after the switch (66 : 6 = 5.5 : 0.5), so it stays put; only its words change.
      EP.arrow(ctx, xd(GAP), Y_DASH, xd(TURN), Y_DASH, { kind: 'motion', width: 8, headSize: 26, dash: [7, 6], alpha: Math.max(aDash, 0), progress: prog(t, 16.0, 16.6, ease.outCubic) });
      tag(EP, ctx, xd(TURN) - 22, Y_LBL2, num(seen) + '°', T('s04.backwards'), { align: 'right', alpha: aDash * slow });
      tag(EP, ctx, xd(TURN) - 22, Y_LBL2, num(seen * FPS / 360, 1), T('s04.backwards'), { align: 'right', alpha: real, unit: T('unit.turns'), rtl });
    }
  },
};
