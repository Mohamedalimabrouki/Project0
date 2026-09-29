/*
 * Scene 08 - Closing card: the takeaway (10 s).
 *
 * The bookend of the opening card (s02_title): the same wheel mark, the same
 * colour strip, the same calm. It leaves the viewer with the one sentence to
 * remember, the engineers' rule behind it, and one last wink: the small wheel
 * looks frozen because it really turns 6 times per second. At 30 pictures per
 * second that is 72 degrees per picture, exactly one gap between two spokes,
 * so every picture is identical. For a moment a yellow spoke gives the game
 * away, then it fades and the wheel looks frozen again.
 *
 *   0.0 - 0.5   cross-fade from the previous scene (ink and grid only)
 *   0.2         sound: reversed swoosh that lands on the hit at 0.8
 *   0.5 - 1.2   wheel mark fades in (it looks frozen from its first picture)
 *   0.55 - 1.7  the takeaway sentence, line by line, fades and rises in
 *   1.75 - 2.6  the engineers' rule: equation, then one plain sentence
 *   2.2 - 3.15  colour strip grows from the centre, series line is revealed
 *   3.0         sound: shimmer (the frozen moment)
 *   3.9 - 6.1   the wink: a yellow spoke shows the wheel is spinning. It arrives
 *               with the music's resolving chord (4.0) and leaves with its bell (6.0)
 *   6.1 - 8.5   calm hold
 *   8.5 - 9.8   everything fades to plain ink: the film ends on ink
 *
 * Honesty: the wheel angle is computed, never typed by eye: angle = 2 pi * 6 * t.
 * At picture n (t = n / 30) that is exactly n * 72 degrees. The wheel has five
 * spokes 72 degrees apart, so the picture never changes: the alias is real, on
 * the viewer's own screen. No motion blur.
 */

const TURNS_PER_SECOND = 6;   // the small wheel really turns 6 times per second
const WHEEL_R = 56;           // tyre radius of the mark (px)
const RULE_TEX = 'f_s > 2\\,f_{\\max}';
const YELLOW = '#F0E442';     // EP.PAL.highlight (the math list needs the plain value)

export default {
  duration: 10,
  // The series name is on screen, so the corner mark leaves during the 0.5 s
  // cross-fade (a plain `true` would make it vanish in one picture).
  hideLogo: t => { const k = Math.min(1, Math.max(0, t / 0.5)); return k * k * (3 - 2 * k); },
  captions: [
    // the sentence is already on screen: subtitles only
    { key: 's08.takeaway', in: 0.8, out: 9.2, burn: false },
  ],
  cues: [
    { t: 0.2, sfx: 'swoosh_rev', dur: 0.6 },
    { t: 0.8, sfx: 'hit', gain: -4 },
    { t: 3.0, sfx: 'shimmer', gain: -10, dur: 3 },
  ],
  math: [{ tex: RULE_TEX, color: YELLOW }],
  music: 'outro',

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, ease, prog, text, math, T, TAU } = EP;
    const cx = W / 2;

    // ------------------------------------------------------------ fade to ink
    // content leaves first, then the faint grid and vignette: the last frames
    // are plain ink (#12161C), nothing else.
    const out = 1 - prog(t, 8.5, 9.4, ease.inOutSine);
    const bgOut = prog(t, 8.6, 9.8, ease.inOutSine);
    EP.bg(ctx, W, H);
    if (bgOut > 0) { ctx.fillStyle = EP.rgba(PAL.ink, bgOut); ctx.fillRect(0, 0, W, H); }

    // ------------------------------------------------------------ layout
    // Measured, not guessed: the sentence is broken into balanced lines (at
    // most 3), then the stack is centred a little above the middle of the
    // frame, like the opening card. Arabic lines are taller; if the stack
    // would run too low the gaps between the groups shrink a little.
    const para = breakParagraph(ctx, EP, T('s08.takeaway'), { size: 80, floorSize: 64, minSize: 46, weight: 700, maxWidth: 1440, wideWidth: 1600, maxLines: 3, tracking: rtl ? 0 : -0.01 });
    const arK = rtl ? 1.06 : 1;                       // the engine sets Arabic 6 % larger
    const step = Math.round(para.size * arK * (rtl ? 1.3 : 1.2));
    const capH = para.size * arK * 0.72;
    const sentH = capH + (para.lines.length - 1) * step + para.size * arK * 0.22;

    const EQ_SIZE = 68, RULE_SIZE = 32, SERIES_SIZE = 24;
    const eqBox = math(ctx, RULE_TEX, { x: 0, y: 0, size: EQ_SIZE, anchor: 'top', color: PAL.highlight, draw: false });
    const eqH = eqBox ? eqBox.h : EQ_SIZE * 1.1;
    const ruleCap = RULE_SIZE * arK * 0.72;
    const seriesCap = SERIES_SIZE * arK * 0.72;
    const wheelH = 2 * WHEEL_R;

    const gaps = { wheel: 60, sent: 78, eq: 30, rule: 80, strip: 32 };
    const fixedH = wheelH + sentH + eqH + ruleCap + 6 + seriesCap;
    const gapSum = gaps.wheel + gaps.sent + gaps.eq + gaps.rule + gaps.strip;
    const squeeze = Math.min(1, (895 - 100 - fixedH) / gapSum);
    const G = Object.fromEntries(Object.entries(gaps).map(([k, v]) => [k, v * squeeze]));
    const total = fixedH + gapSum * squeeze;
    const top = Math.round(Math.max(100, 505 - total / 2));

    const wheelY = top + WHEEL_R;
    const sentTop = top + wheelH + G.wheel;
    const firstBase = Math.round(sentTop + capH);
    const eqTop = Math.round(sentTop + sentH + G.sent);
    const ruleBase = Math.round(eqTop + eqH + G.eq + ruleCap);
    const stripY = Math.round(ruleBase + G.rule);
    const seriesBase = Math.round(stripY + 6 + G.strip + seriesCap);

    // ------------------------------------------------------------ wheel mark
    // It really turns 6 times per second: 72 degrees per picture.
    const wA = prog(t, 0.5, 1.15, ease.outCubic);
    const wK = prog(t, 0.5, 1.5, ease.outCubic);
    const spin = TAU * TURNS_PER_SECOND * t;
    // the wink: a yellow spoke fades in, goes round with the wheel, and fades out.
    // It arrives with the resolving chord and the small kick of the music at 4.0 s
    // and is gone when the bell rings at 6.0 s: the wheel is frozen again.
    const wink = prog(t, 3.92, 4.42, ease.outCubic) * (1 - prog(t, 5.5, 6.1, ease.inOutSine));
    if (wA > 0) {
      const s = 0.88 + 0.12 * wK;
      ctx.save();
      ctx.translate(cx, wheelY);
      ctx.scale(s, s);
      EP.wheel(ctx, { x: 0, y: 0, r: WHEEL_R, angle: spin, highlight: wink > 0 ? 0 : null, highlightAlpha: wink, opacity: wA * out });
      ctx.restore();
    }
    // the true rate, named while the yellow spoke shows it. It sits beside the
    // wheel on the side where reading continues (right, or left in Arabic).
    if (wink > 0) {
      const LABEL_SIZE = 26;
      text(ctx, spinLabel(EP), {
        x: cx + (rtl ? -1 : 1) * (WHEEL_R + 30), y: wheelY + LABEL_SIZE * 0.36, align: 'start',
        size: LABEL_SIZE, weight: 500, color: PAL.steel, opacity: wink * out,
      });
    }

    // ------------------------------------------------------------ the sentence
    // line by line, 0.08 s apart: each line fades in and rises into place. The
    // rise is fastest just before the hit at 0.8 s and has landed a moment later.
    const S0 = 0.55, ST = 0.08;
    para.lines.forEach((line, i) => {
      const a = S0 + i * ST;
      const k = prog(t, a, a + 1.0, ease.outQuint);
      const o = prog(t, a, a + 0.65, ease.outCubic);
      text(ctx, line, {
        x: cx, y: firstBase + i * step + 32 * (1 - k), align: 'center', size: para.size, weight: 700,
        tracking: rtl ? 0 : -0.01 + 0.025 * (1 - k), color: PAL.paper, opacity: o * out,
      });
    });

    // ------------------------------------------------------------ the rule
    const kE = prog(t, 1.75, 2.45, ease.outCubic);
    if (kE > 0) math(ctx, RULE_TEX, { x: cx, y: eqTop + 16 * (1 - kE), size: EQ_SIZE, anchor: 'top', align: 'center', color: PAL.highlight, opacity: kE * out });
    const kR = prog(t, 1.9, 2.6, ease.outCubic);
    text(ctx, T('s08.rule'), {
      x: cx, y: ruleBase + 12 * (1 - kR), align: 'center', size: RULE_SIZE, weight: 500, color: PAL.steel,
      opacity: kR * out, maxWidth: 1400, shrink: true, maxLines: 1,
    });

    // ------------------------------------------------------------ colour strip and series line
    // the strip grows from the centre (as on the opening card) and, at the end,
    // draws itself back in
    const kS = prog(t, 2.2, 3.0, ease.inOutCubic) * (1 - prog(t, 8.5, 9.3, ease.inOutCubic));
    if (kS > 0) {
      const cols = [PAL.force, PAL.motion, PAL.energy, PAL.fluid, PAL.field, PAL.balance, PAL.highlight];
      const full = 420, seg = full / cols.length, w = full * kS;
      ctx.save();
      ctx.globalAlpha = 1 - prog(t, 9.0, 9.6, ease.inOutSine);
      cols.forEach((c, i) => {
        const x0 = cx - full / 2 + i * seg;
        const vis0 = Math.max(x0, cx - w / 2), vis1 = Math.min(x0 + seg, cx + w / 2);
        if (vis1 > vis0) { ctx.fillStyle = c; ctx.fillRect(vis0, stripY, vis1 - vis0, 6); }
      });
      ctx.restore();
    }
    drawSeries(ctx, EP, T('s08.series'), {
      x: cx, y: seriesBase, size: SERIES_SIZE, color: PAL.highlight, maxWidth: 1500,
      opacity: prog(t, 2.35, 3.0, ease.outCubic) * out, reveal: prog(t, 2.35, 3.15, ease.outCubic),
    });
  },
};

// ---------------------------------------------------------------------------
// The label that names the wheel's true rate while the yellow spoke shows it.
// It has its own key, "{n} turns per second", so a translator can inflect it
// for this number (Arabic wants a plural after 6). Until that key is translated
// (or if it is missing) we fall back to the shared unit, which is always there:
// the film is never wrong, only less polished.
// ---------------------------------------------------------------------------
function spinLabel(EP) {
  const own = EP.I18N.strings['s08.spin'];
  if (own && own.en) {
    const label = EP.T('s08.spin', { n: EP.num(TURNS_PER_SECOND) });   // also reports a missing translation
    if (EP.I18N.lang === 'en' || own[EP.I18N.lang]) return label;
  }
  return EP.qty(TURNS_PER_SECOND, EP.T('unit.turns'));
}

// ---------------------------------------------------------------------------
// The series line under the colour strip: "Engineering Phenomena · 02 · Aliasing".
// Normally one Latin string in spaced capitals, like the opening card. A
// translation can mix scripts (the brand words stay Latin, the name of the
// phenomenon is Arabic). The engine cannot space or capitalise part of a
// string, so then each part is drawn in its own style: Latin words as spaced
// capitals in Inter, Arabic words in the Arabic font with their letters joined.
// Latin parts stay in their own left-to-right order, as in the brand line;
// the groups follow the reading direction.
// ---------------------------------------------------------------------------
const ARABIC_LETTER = /[؀-ۿ]/;

function drawSeries(ctx, EP, str, { x, y, size, color, opacity, reveal, maxWidth }) {
  const { text, measure } = EP;
  if (!ARABIC_LETTER.test(str)) {
    text(ctx, str, { x, y, align: 'center', size, weight: 700, tracking: 0.2, caps: true, color, opacity, reveal, maxWidth, shrink: true, maxLines: 1 });
    return;
  }
  const rtl = EP.isRTL();
  const parts = String(str).split(/\s*·\s*/).filter(Boolean).map(p => ({ p, ar: ARABIC_LETTER.test(p) }));
  const groups = [];
  for (const o of parts) {
    const g = groups[groups.length - 1];
    if (g && g.ar === o.ar) g.items.push(o); else groups.push({ ar: o.ar, items: [o] });
  }
  const items = (rtl ? groups.slice().reverse() : groups).flatMap(g => (g.ar && rtl ? g.items.slice().reverse() : g.items));
  const style = o => (o.ar ? { weight: 700 } : { weight: 700, tracking: 0.2, caps: true, latin: true });
  const dot = { weight: 700, latin: true };

  let s = size, widths, sepW, gap, total;
  const sizeOf = o => (o.ar ? s * 1.2 : s);           // Arabic letters read smaller at the same size
  const layout = () => {
    widths = items.map(o => measure(ctx, o.p, { size: sizeOf(o), ...style(o) }).w - (o.ar ? 0 : 0.2 * s));   // without the trailing letter space
    sepW = measure(ctx, '·', { size: s, ...dot }).w;
    gap = s * 0.7;
    total = widths.reduce((a, b) => a + b, 0) + (items.length - 1) * (sepW + 2 * gap);
  };
  layout();
  while (total > maxWidth && s > size * 0.6) { s *= 0.96; layout(); }

  ctx.save();
  if (reveal < 1) {                                   // wipe in the reading direction
    const pad = s, cw = (total + 2 * pad) * Math.min(1, Math.max(0, reveal));
    ctx.beginPath();
    if (rtl) ctx.rect(x + total / 2 + pad - cw, y - 3 * s, cw, 4 * s);
    else ctx.rect(x - total / 2 - pad, y - 3 * s, cw, 4 * s);
    ctx.clip();
  }
  let px = x - total / 2;
  items.forEach((o, i) => {
    text(ctx, o.p, { x: px, y, align: 'left', size: sizeOf(o), color, opacity, ...style(o) });
    px += widths[i];
    if (i < items.length - 1) {
      text(ctx, '·', { x: px + gap, y, align: 'left', size: s, color, opacity, ...dot });
      px += sepW + 2 * gap;
    }
  });
  ctx.restore();
}

// ---------------------------------------------------------------------------
// Line breaking for a short, important sentence.
//
// The engine wraps text greedily (fill each line, then start the next), which
// leaves a ragged block and a lonely last word. For a headline we do better:
// try every way to cut the sentence into at most `maxLines` lines that fit,
// and pick the most balanced one, preferring to break after a comma and never
// ending a line on a small joining word ("and", "or", "de", "et", ...).
// Works the same for English, French and Arabic (words are cut in reading
// order; the engine draws each line in the right direction). If nothing fits,
// the type size shrinks a little and we try again.
// ---------------------------------------------------------------------------
const PHRASE_END = /[,;:.!?،؛…]$/;
const SMALL_WORDS = new Set([
  'a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'with', 'but', 'as', 'than',
  'le', 'la', 'les', 'un', 'une', 'des', 'du', 'de', 'et', 'ou', 'au', 'aux', 'en', 'sur', 'par', 'pour', 'avec', 'que',
  'و', 'في', 'من', 'على', 'إلى', 'عن', 'أن', 'إن', 'أو', 'ثم', 'حتى', 'لا',
]);
const endsOnSmallWord = w => {
  const bare = w.replace(/[,;:.!?،؛…]+$/, '').toLowerCase();
  return bare.length <= 2 || SMALL_WORDS.has(bare) || /['’]$/.test(bare);
};

function breakParagraph(ctx, EP, str, { size, floorSize, minSize, weight, maxWidth, wideWidth, maxLines, tracking }) {
  const words = String(str).split(' ').filter(Boolean);
  const n = words.length;
  if (n < 2) return { lines: [String(str)], size };
  // The ladder of attempts, best look first: shrink from `size` down to
  // `floorSize` inside `maxWidth`; then let the block widen to `wideWidth`;
  // only then go below the floor. The type stays large as long as it can.
  const attempts = [];
  for (let s = size; s >= floorSize; s *= 0.97) attempts.push([s, maxWidth]);
  for (let s = Math.min(size, floorSize); s >= minSize; s *= 0.97) attempts.push([s, wideWidth]);
  for (const [s, limit] of attempts) {
    const cache = new Map();
    const width = (i, j) => {
      const key = i * 1000 + j;
      let w = cache.get(key);
      if (w === undefined) { w = EP.measure(ctx, words.slice(i, j).join(' '), { size: s, weight, tracking }).w; cache.set(key, w); }
      return w;
    };
    let best = null;
    for (let K = 1; K <= Math.min(maxLines, n); K++) {
      const target = width(0, n) / K;               // an equal share of the text
      const cuts = [];
      const visit = (from, left) => {
        if (left === 1) {
          if (width(from, n) > limit) return;
          const bounds = [0, ...cuts, n];
          let cost = (K - 1) * 1.5;
          for (let l = 0; l < K; l++) {
            const a = bounds[l], b = bounds[l + 1];
            cost += 100 * ((width(a, b) - target) / target) ** 2;
            if (l < K - 1) {
              const last = words[b - 1];
              if (PHRASE_END.test(last)) cost -= 7;
              if (endsOnSmallWord(last)) cost += 9;
            }
          }
          if (!best || cost < best.cost) best = { cost, bounds };
          return;
        }
        for (let c = from + 1; c <= n - (left - 1); c++) {
          if (width(from, c) > limit) break;        // longer only gets wider
          cuts.push(c);
          visit(c, left - 1);
          cuts.pop();
        }
      };
      visit(0, K);
    }
    if (best) {
      const lines = [];
      for (let l = 0; l < best.bounds.length - 1; l++) lines.push(words.slice(best.bounds[l], best.bounds[l + 1]).join(' '));
      return { lines, size: s };
    }
  }
  // last resort (not expected): plain greedy wrap at the smallest size,
  // rather than letting a line run off the frame
  const lines = [];
  let line = '';
  for (const w of words) {
    const test = line ? line + ' ' + w : w;
    if (line && EP.measure(ctx, test, { size: minSize, weight, tracking }).w > wideWidth) { lines.push(line); line = w; }
    else line = test;
  }
  lines.push(line);
  return { lines, size: minSize };
}
