/*
 * Short (9:16, 1080 x 1920) - scene 3: the takeaway (7 s).
 *
 * The one sentence, the rule for engineers, and a small wheel that looks
 * frozen because it really turns 6 times a second: 6 turns per second is
 * 72 degrees per video frame, exactly one spoke gap (360 / 5), so every
 * picture is the same. It is drawn at its true rate, no blur: the viewer's
 * own screen does the sampling.
 *
 * The series line is drawn here (the engine's series mark is hidden), and
 * everything fades to ink in the last second.
 */

const SPOKES = 5;
const WHEEL_RATE = 6;                     // turns per second = 72 degrees per picture at 30 pictures per second
const CX = 505;                           // centre of the text column: the free area is x 60 to 920 (right edge kept clear of the app buttons)
const COL = 810;                          // widest line: x 100 to 910

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

export default {
  duration: 7,
  strings: ['s08_takeaway'],
  hideLogo: t => { const k = Math.min(1, Math.max(0, t / 0.5)); return k * k * (3 - 2 * k); },   // the series line below replaces the mark: it leaves during the cross-fade
  math: ['f_s > 2\\,f_{\\max}'],
  captions: [
    { key: 's08.takeaway', in: 0.6, out: 6.4, burn: false },     // subtitles only: the sentence is already on screen
  ],
  cues: [
    { t: 0.5, sfx: 'hit', gain: -4 },
  ],
  music: 'outro',

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, ease, prog, text, math, T, num } = EP;
    EP.bg(ctx, W, H);
    const out = 1 - prog(t, 6.0, 7.0, ease.inOutSine);         // fade to ink in the last second

    // ---- layout: one column, stacked from the measured height of the takeaway, so any language keeps the same rhythm
    const str = T('s08.takeaway');
    const lh = rtl ? 1.3 : 1.2;                                 // Arabic needs more line height, but not the engine default of 1.5 here
    let size = rtl ? 74 : 84, box;
    for (let i = 0; i < 24; i++) {                              // fit the width (engine shrink) AND a height budget
      box = EP.measure(ctx, str, { size, weight: 800, maxWidth: COL, maxLines: 4, shrink: true, lineHeight: lh, tracking: rtl ? 0 : -0.01 });
      if (box.h + 0.26 * box.size <= 348) break;
      size *= 0.96;
    }
    const Y_SERIES = 496, GAP = 68;
    const yTop = Y_SERIES + GAP;                                // top of the takeaway (cap height of the first line)
    const yBottom = yTop + box.h + 0.26 * box.size;             // bottom of the last line, with descenders
    const tex = 'f_s > 2\\,f_{\\max}';
    const fs = 104;
    const mbox = math(ctx, tex, { x: CX, y: 0, size: fs, align: 'center', anchor: 'middle', draw: false });
    const ph = (mbox ? mbox.h : 100) + 76;
    const fy = yBottom + GAP + ph / 2;                          // formula plaque centre
    const wr = 96, wy = fy + ph / 2 + GAP + wr;                 // wheel centre
    const by = wy + wr + 46;                                    // badge centre

    // series line, always in Latin letters (it is the brand)
    text(ctx, 'ENGINEERING PHENOMENA  ·  02', {
      x: CX, y: Y_SERIES, align: 'center', size: 30, weight: 700, tracking: 0.2, latin: true,
      color: PAL.highlight, opacity: prog(t, 0.4, 1.0, ease.outCubic) * out, reveal: prog(t, 0.4, 1.3, ease.outCubic),
    });

    // the takeaway: display size, up to 4 lines, shrinks to fit (French and Arabic are longer)
    const kT = prog(t, 0.5, 1.4, ease.outQuint);
    text(ctx, str, {
      x: CX, y: yTop + 26 * (1 - kT), anchor: 'top', align: 'center', size, weight: 800,
      maxWidth: COL, maxLines: 4, shrink: true, lineHeight: lh, tracking: rtl ? 0 : -0.01,
      color: PAL.paper, opacity: kT * out,
    });

    // the rule for engineers
    const kF = prog(t, 1.8, 2.5, ease.outCubic);
    if (mbox && kF > 0) {
      const pw = mbox.w + 110;
      ctx.save();
      ctx.globalAlpha *= kF * out;
      EP.roundRect(ctx, CX - pw / 2, fy - ph / 2, pw, ph, 14);
      ctx.fillStyle = EP.rgba(PAL.steel, 0.07); ctx.fill();
      ctx.lineWidth = 1.5; ctx.strokeStyle = EP.rgba(PAL.steel, 0.45); ctx.stroke();
      ctx.restore();
      math(ctx, tex, { x: CX, y: fy, size: fs, align: 'center', anchor: 'middle', opacity: kF * out });
    }

    // a small wheel that looks frozen: 6 turns per second = exactly 72 degrees per video frame
    const kW = prog(t, 2.6, 3.3, ease.outCubic);
    const gap = 44, iconW = 60;
    const unit = T('unit.turns');
    const vW = EP.textTab(ctx, num(WHEEL_RATE), { size: 76, weight: 800, opacity: 0 }).w;
    const uW = Math.min(300, EP.measure(ctx, unit, { size: 32, weight: 600 }).w);
    const blockW = Math.max(iconW + vW, uW);
    const rowW = 2 * wr + gap + blockW;
    const rowL = CX - rowW / 2;                                  // left edge of the whole row
    const wx = rtl ? rowL + rowW - wr : rowL + wr;
    const bl = rtl ? rowL : rowL + 2 * wr + gap;                 // text block: left edge
    EP.wheel(ctx, { x: wx, y: wy, r: wr, angle: EP.TAU * WHEEL_RATE * t, spokes: SPOKES, opacity: kW * out });
    ctx.save(); ctx.globalAlpha *= kW * out; tyreDetail(EP, ctx, wx, wy, wr); ctx.restore();

    // what it really does: solid blue forward arc + 6 turns per second
    const kR = prog(t, 3.0, 3.7, ease.outCubic);
    EP.arcArrow(ctx, bl + 28, wy - 22, 26, -135 * EP.DEG, 120 * EP.DEG, { width: 6, headSize: 21, alpha: kR * out });
    EP.textTab(ctx, num(WHEEL_RATE), { x: bl + iconW, y: wy - 2, size: 76, weight: 800, color: PAL.paper, opacity: kR * out, align: 'left' });
    text(ctx, unit, { x: bl, y: wy + 48, size: 32, weight: 600, color: PAL.steel, opacity: kR * out, align: 'left', maxWidth: 300, shrink: true, maxLines: 1 });

    // honest label: real speed, sampled by your own screen
    EP.badge(ctx, T('badge.real'), { x: CX, y: by, align: 'center', size: 30, opacity: prog(t, 3.3, 3.9, ease.outCubic) * out });
  },
};
