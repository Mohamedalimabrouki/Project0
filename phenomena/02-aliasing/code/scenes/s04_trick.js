/*
 * Scene 04 - The trick (38.5 s). The heart of the film.
 *
 * One big wheel with 5 identical spokes (72 degrees apart); spoke 0 is painted
 * yellow. The film takes 30 pictures per second, so the real turn per picture
 * decides what the video shows:
 *
 *   Part A  15 degrees per picture   seen +15 degrees (same)   forwards, correct
 *   Part B  66 degrees per picture   seen  -6 degrees          backwards
 *           then the same at REAL SPEED: 5.5 turns per second = 66 degrees per frame
 *   Part C  72 degrees per picture   seen   0 degrees          frozen
 *           the paint is on for ONE stepped picture (the yellow spoke lands exactly on the
 *           old place of the next spoke), then it fades while still stepping: from picture 3
 *           on, every picture really is identical while "every picture looks the same" shows
 *           then the same at REAL SPEED: 6 turns per second = 72 degrees per frame
 *           (the yellow spoke comes back for a moment to prove the wheel spins, then fades)
 *
 * Everything on screen is computed from those few numbers:
 *   real turn per picture     = delta
 *   what we see (the alias)   = EP.wrapSigned(delta, 72 degrees)  (nearest-spoke rule)
 *
 * Two modes, both exact:
 *   "step"  one picture per second (slowed down x30, badge). The wheel jumps from
 *           picture to picture on purpose; the previous picture stays as a ghost.
 *   "real"  the wheel is drawn at its true angle in every frame of the video
 *           (no blur, no ghosts): angle(frame) = base + delta * picture number,
 *           so the viewer's own screen does the aliasing.
 * The real runs continue the picture numbering of the step run before them, so
 * "slowed down" and "real speed" show literally the same sequence of pictures.
 *
 * render() is a pure function of t: the wheel angle comes from integer frame
 * numbers (no accumulated error), every overlay from time since its picture.
 *
 * Hand-over from scene 03: it ends on the wheel alone, at (960, 606), radius 250, spoke
 * up, still and opaque. This scene therefore has that same wheel, fully opaque, from its
 * very first frame (angle 0 = spoke up), so the cross-fade between the two scenes is
 * invisible. If scene 03 ever ends on another wheel, change A.base (a multiple of 72
 * degrees keeps the pattern identical) and the wheel position constants below.
 */

// ------------------------------------------------------------------ numbers
const DEG = Math.PI / 180;
const FPS = 30;          // pictures per second of the film = the sampling rate f_s
const GAP = 72;          // degrees between two neighbouring spokes
const SPOKES = 5;

// stage geometry (px). Caption band is y 64..260, bottom band starts at y 930.
const CX = 960, CY = 606, R = 250;
const R_REAL = R + 22;   // ring of the solid "real turn" arrow
const R_SEEN = R + 60;   // ring of the dashed "what we see" arrow

// ------------------------------------------------------------------ the runs
// Step run: picture i shows spoke 0 at  base + delta * i  (degrees, unwrapped),
// each picture lasts 1 s (a real gap of 1/30 s, slowed down x30).
const stepRun = (part, t0, n, delta, base) => {
  const f0 = Math.round(t0 * FPS);
  return { kind: 'step', part, t0, n, delta, base, f0, f1: f0 + n * FPS };
};
// Real run: the same wheel at true speed, one picture per video frame. It
// carries on numbering where the step run stopped.
const realRun = (from, t0, t1) => ({
  kind: 'real', part: from.part, from, t0, t1, delta: from.delta, base: from.base, n0: from.n,
  f0: Math.round(t0 * FPS), f1: Math.round(t1 * FPS),
});
const angleAt = (r, f) => r.base + r.delta * (r.n0 + (f - r.f0));

const A = stepRun('A', 3.4, 7, 15, 0);                              // 15 deg per picture
const B = stepRun('B', 11.0, 11, 66, A.base + A.delta * (A.n - 1)); // starts where A stopped
const Br = realRun(B, 22.0, 26.4);                                  // 5.5 turns per second
const C = stepRun('C', 26.4, 6, 72, angleAt(Br, Br.f1));            // starts where Br stopped
const Cr = realRun(C, 32.4, 38.5);                                  // 6 turns per second
const RUNS = [A, B, Br, C, Cr];

/**
 * Everything the drawing needs to know at time t, all from integer frames.
 * angle is the angle of spoke 0 in degrees (clock angle, unwrapped, so that the
 * difference between two pictures is the real turn).
 */
function model(t) {
  const f = Math.round(t * FPS);
  for (const r of RUNS) {
    if (f < r.f0 || f >= r.f1) continue;
    if (r.kind === 'step') {
      const i = Math.floor((f - r.f0) / FPS);
      return {
        mode: 'step', run: r, part: r.part, n: i, s: (f - r.f0 - i * FPS) / FPS,
        angle: r.base + r.delta * i, prev: i > 0 ? r.base + r.delta * (i - 1) : null, delta: r.delta,
      };
    }
    return { mode: 'real', run: r, part: r.part, n: r.n0 + (f - r.f0), s: t - r.t0, angle: angleAt(r, f), prev: null, delta: r.delta };
  }
  if (f < A.f0) return { mode: 'idle', part: 'A', n: -1, s: 0, angle: A.base, prev: null, delta: A.delta };
  if (f < B.f0) return { mode: 'hold', part: 'A', n: -1, s: 0, angle: A.base + A.delta * (A.n - 1), prev: null, delta: A.delta };
  return { mode: 'hold', part: 'C', n: -1, s: 0, angle: angleAt(Cr, Cr.f1 - 1), prev: null, delta: C.delta };
}

// which annotations belong to picture n of a step run (built up over the pictures)
function flagsFor(part, n) {
  if (part === 'A') return { real: n >= 1, seen: n >= 2, closest: n >= 2, gap: false, short: false };
  if (part === 'B') return { real: n >= 1, gap: n <= 1, short: n >= 5 && n <= 8, closest: n >= 8, seen: n >= 9 };
  return { real: n >= 1, seen: false, closest: n >= 1, gap: false, short: false };   // C: "frozen" is told once the paint is gone (by time)
}

// index of the spoke (in the new picture) that is closest to where the yellow spoke was
const closestSpoke = delta => ((-Math.round(delta / GAP)) % SPOKES + SPOKES) % SPOKES;

// turns per second of a real run (66 deg x 30 pictures/s / 360 = 5.5)
const turnsPerSecond = r => (r.delta * FPS) / 360;

export const _check = { RUNS, A, B, Br, C, Cr, model, closestSpoke, turnsPerSecond, FPS, DEG, GAP };

// ------------------------------------------------------------------ helpers
const mod = (x, p) => ((x % p) + p) % p;
/** point at clock angle deg (0 = up, clockwise) on a circle around the wheel centre */
const P = (r, deg) => [CX + r * Math.sin(deg * DEG), CY - r * Math.cos(deg * DEG)];
/** signed angle for the screen: +66°  -6°  0° (proper minus sign, upright degree sign) */
const signed = (EP, deg) => (deg > 0.0005 ? '+' : '') + EP.num(deg, 0) + '°';

function rayLine(ctx, deg, r0, r1) {
  const [x0, y0] = P(r0, deg), [x1, y1] = P(r1, deg);
  ctx.beginPath(); ctx.moveTo(x0, y0); ctx.lineTo(x1, y1); ctx.stroke();
}
function arcPath(ctx, r, d0, d1) {
  ctx.beginPath();
  ctx.arc(CX, CY, r, d0 * DEG - Math.PI / 2, d1 * DEG - Math.PI / 2, d1 < d0);
}

// ---------------------------------------------------------------- text rows
// A label is one or two rows of items laid out in reading order (left to right
// in English and French, right to left in Arabic; numbers stay left to right).
//   { text, size, weight, color, latin }   { line: 'solid'|'dashed'|'thin', color }
//   { check }   { gap: px }
const ICON_W = 40, CHECK_W = 30;   // width of a line sample / a tick

function measureRow(EP, ctx, items) {
  let w = 0;
  const out = items.map(it => {
    let iw;
    if (it.gap != null) iw = it.gap;
    else if (it.line || it.swatch) iw = ICON_W;
    else if (it.check) iw = CHECK_W;
    else iw = EP.measure(ctx, it.text, { size: it.size, weight: it.weight, latin: !!it.latin }).w;
    w += iw;
    return { ...it, w: iw };
  });
  return { items: out, w };
}

function drawRow(EP, ctx, row, x0, base, rtl, alpha) {
  const { PAL } = EP;
  let x = x0;
  for (const it of row.items) {
    const left = rtl ? x - it.w : x;
    if (it.text != null) {
      EP.text(ctx, it.text, { x: left, y: base, align: 'left', size: it.size, weight: it.weight, color: it.color, latin: !!it.latin, opacity: alpha });
    } else if (it.line) {
      ctx.save();
      ctx.globalAlpha *= alpha;
      ctx.strokeStyle = it.color;
      ctx.lineCap = 'round';
      ctx.lineWidth = it.lw || (it.line === 'thin' ? 2.5 : 5);
      if (it.line === 'dashed') ctx.setLineDash(it.lw ? [8, 6] : [9, 7]);
      ctx.beginPath(); ctx.moveTo(left + 3, base - 11); ctx.lineTo(left + ICON_W - 3, base - 11); ctx.stroke();
      ctx.restore();
    } else if (it.swatch) {
      ctx.save();
      ctx.globalAlpha *= alpha;
      ctx.fillStyle = EP.rgba(it.swatch, 0.75);
      EP.roundRect(ctx, left + 3, base - 21, ICON_W - 6, 20, 3);
      ctx.fill();
      ctx.restore();
    } else if (it.check) {
      ctx.save();
      ctx.globalAlpha *= alpha;
      ctx.strokeStyle = PAL.balance;
      ctx.lineWidth = 5.5; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
      ctx.beginPath(); ctx.moveTo(left + 3, base - 12); ctx.lineTo(left + 11, base - 3); ctx.lineTo(left + 26, base - 23); ctx.stroke();
      ctx.restore();
    }
    x += rtl ? -it.w : it.w;
  }
}

/**
 * A label for an arrow or a measure: [line sample] Title  VALUE  note
 *                                                Verdict (and a tick)
 * Returns {w, h, draw(ctx, x, y, alpha)} where (x, y) is the top-left corner.
 */
function makeLabel(EP, ctx, spec) {
  const { PAL } = EP;
  const rtl = EP.isRTL();
  const paper = EP.rgba(PAL.paper, 0.94);
  const row1 = [];
  if (spec.icon === 'swatch') row1.push({ swatch: spec.iconColor || PAL.motion }, { gap: 12 });
  else if (spec.icon) row1.push({ line: spec.icon, color: spec.iconColor || PAL.motion }, { gap: 12 });
  row1.push({ text: spec.title, size: 28, weight: 600, color: paper });
  if (spec.value != null) row1.push({ gap: 14 }, { text: spec.value, size: 40, weight: 800, color: spec.valueColor || PAL.motion, latin: true });
  if (spec.note) row1.push({ gap: 12 }, { text: spec.note, size: 26, weight: 500, color: PAL.steel });
  const r1 = measureRow(EP, ctx, row1);
  let r2 = null;
  if (spec.verdict) {
    const items = [];
    if (spec.icon) items.push({ gap: ICON_W + 12 });
    items.push({ text: spec.verdict, size: 32, weight: 700, color: PAL.paper });
    if (spec.check) items.push({ gap: 12 }, { check: true });
    if (spec.verdictNote) items.push({ gap: 18 }, { text: spec.verdictNote, size: 22, weight: 500, color: PAL.steel });
    r2 = measureRow(EP, ctx, items);
  }
  const w = Math.max(r1.w, r2 ? r2.w : 0);
  const h = r2 ? 92 : 46;
  return {
    w, h,
    draw(c, x, y, alpha) {
      if (alpha <= 0) return;
      const x0 = rtl ? x + w : x;
      drawRow(EP, c, r1, x0, y + 34, rtl, alpha);
      if (r2) drawRow(EP, c, r2, x0, y + 34 + 46, rtl, alpha);
    },
  };
}

// ------------------------------------------------- wheel-space drawing bits
/** thin radial guide from the spoke tips out to the arrow rings (like an extension line in a drawing) */
function guide(EP, ctx, deg, color, alpha, dash) {
  if (alpha <= 0) return;
  ctx.save();
  ctx.strokeStyle = EP.rgba(color, alpha);
  ctx.lineWidth = 2;
  ctx.lineCap = 'round';
  if (dash) ctx.setLineDash(dash);
  rayLine(ctx, deg, R * 0.7, R_SEEN + 10);
  ctx.restore();
}
/** thin reference arc with small end ticks (a measure, not a motion): "one spoke gap", "6 degrees short" */
function measureArc(EP, ctx, r, d0, d1, alpha, progress = 1, tick = 9) {
  if (alpha <= 0 || progress <= 0) return;
  const end = d0 + (d1 - d0) * progress;
  ctx.save();
  ctx.globalAlpha *= alpha;
  ctx.strokeStyle = EP.PAL.paper;
  ctx.lineWidth = 2.6;
  ctx.lineCap = 'round';
  arcPath(ctx, r, d0, end); ctx.stroke();
  rayLine(ctx, d0, r - tick, r + tick);
  if (progress >= 0.999) rayLine(ctx, d1, r - tick, r + tick);
  ctx.restore();
}
/** annular sector between two clock angles (used for the "what we see" wedge) */
function sectorPath(ctx, r0, r1, d0, d1) {
  ctx.beginPath();
  ctx.arc(CX, CY, r1, d0 * DEG - Math.PI / 2, d1 * DEG - Math.PI / 2, d1 < d0);
  ctx.arc(CX, CY, r0, d1 * DEG - Math.PI / 2, d0 * DEG - Math.PI / 2, d1 > d0);
  ctx.closePath();
}
/**
 * "Just short": the slivers left between each new spoke and the old place of the next one.
 * Each ghost spoke is filled, then the new spokes are cut out of it, so only the sliver stays.
 * alphas[j] fades sliver j in (sliver j is the ghost of spoke j+1, just clockwise of new spoke j).
 */
function slivers(EP, ctx, oldDeg, newDeg, alphas) {
  const on = alphas.some(a => a > 0);
  if (!on) return;
  ctx.save();
  ctx.translate(CX, CY);
  const cut = new Path2D();
  cut.rect(-2000, -2000, 4000, 4000);
  for (let i = 0; i < SPOKES; i++) cut.addPath(EP.spokePath(R, i, mod(newDeg, 360) * DEG, SPOKES));
  ctx.clip(cut, 'evenodd');
  for (let j = 0; j < SPOKES; j++) {
    if (alphas[j] <= 0) continue;
    ctx.fillStyle = EP.rgba(EP.PAL.motion, 0.8 * alphas[j]);
    ctx.fill(EP.spokePath(R, (j + 1) % SPOKES, mod(oldDeg, 360) * DEG, SPOKES));
  }
  ctx.restore();
}

// ------------------------------------------------------- stepping overlays
const TAU = Math.PI * 2;
const verdictKey = seen => (seen > 0.5 ? 's04.forwards' : seen < -0.5 ? 's04.backwards' : 's04.frozen');

// Labels live in two fixed slots on the reading-end side of the wheel (right in English and
// French, left in Arabic). The arrows sweep around the wheel from picture to picture; the
// labels stay where they are, so the text never jumps. Each label starts with a sample of
// its own line style (solid, dashed, thin, patch), which ties it to its arrow.
const SLOT_X = 1300, SLOT_Y = [486, 566];
const slotBox = (EP, L, i) => ({ x: EP.isRTL() ? 2 * CX - SLOT_X - L.w : SLOT_X, y: SLOT_Y[i] });
const drawSlot = (ctx, EP, L, i, a) => { if (L && a > 0) { const b = slotBox(EP, L, i); L.draw(ctx, b.x, b.y + (1 - a) * 8, a); } };
/** where the little "what we see" glyph sits at real speed: on the label's side of the wheel */
const glyphAt = EP => (EP.isRTL() ? 270 : 90);

/**
 * The visual language of the slow motion, defined once and used in every part:
 *   dashed outline   the previous picture (yellow dashed: where the yellow spoke was)
 *   solid blue arc   the real turn, from the old yellow position to the new one
 *   dashed blue arc  what we see: the old yellow position to the closest spoke of the new picture
 *   paper outline    the spoke the eye links to the old yellow spoke
 *   thin paper arc   a measure (one spoke gap), blue patch: the sliver a spoke falls short by
 */
function stepOverlays(ctx, t, EP, m, paintA) {
  const { PAL, SHADE, ease, prog, T } = EP;
  const r = m.run, s = m.s, n = m.n;
  const tEnd = r.f1 / FPS;
  const ov = 1 - prog(t, tEnd - SLOW_EDGE, tEnd, ease.inOutSine);                 // the run's overlays leave together
  const fl = flagsFor(m.part, n), fp = n > 0 ? flagsFor(m.part, n - 1) : {};
  const annK = m.part === 'C' ? 1 - prog(t, 27.9, 28.35, ease.inOutSine) : 1;     // part C: arrows leave with the paint
  const k = ov * annK;
  const a1 = m.angle, a0 = m.prev;                                                // new and old position of the yellow spoke
  const ang = mod(a1, 360) * DEG;
  const real = m.delta;                                                           // real turn per picture
  const seen = EP.wrapSigned(real * DEG, GAP * DEG) / DEG;                        // what we see: nearest-spoke rule
  const kStar = closestSpoke(real);
  const out = (x0, x1) => prog(s, x0, x1, ease.outCubic);

  // ---- previous picture (ghost), the emphasised spoke, the old yellow spoke
  if (a0 != null) {
    const g = { x: CX, y: CY, r: R };
    EP.wheelGhost(ctx, { ...g, angle: mod(a0, 360) * DEG, color: SHADE.steelLight, opacity: 0.85 * ov, width: 2.4, dash: [8, 6] });
    if (fl.closest) EP.wheelGhost(ctx, { ...g, angle: ang, only: kStar, color: PAL.paper, opacity: k * out(0.04, 0.24), width: 4.4 });
    EP.wheelGhost(ctx, { ...g, angle: mod(a0, 360) * DEG, only: 0, color: PAL.highlight, opacity: ov * paintA, width: 3.6, dash: [8, 5] });
  }

  // ---- guides (extension lines) from the spokes to the arrow rings
  if (a0 != null && fl.real) {
    const ga = k * out(0.04, 0.24);
    guide(EP, ctx, a0, PAL.highlight, 0.85 * ga, [4, 6]);
    guide(EP, ctx, a1, PAL.highlight, 0.85 * ga);
    if (fl.seen && Math.abs(seen) > 0.5 && Math.abs(seen - real) > 0.5) guide(EP, ctx, a0 + seen, PAL.paper, 0.75 * ga * prog(s, 0.3, 0.5));
  }

  // ---- part B: the reference "one spoke gap" (72 degrees): a thin arc just outside the real-turn arrow
  if (fl.gap) {
    const ga = mod(n === 0 ? a1 : a0, 360);                       // the gap starts at the yellow spoke
    const gA = (n === 0 ? out(0.2, 0.55) : 1 - prog(s, 0.62, 0.95, ease.inOutSine)) * ov;
    measureArc(EP, ctx, R_REAL + 17, ga, ga + GAP, gA, n === 0 ? out(0.2, 0.7) : 1, 10);
    guide(EP, ctx, ga + GAP, PAL.paper, 0.6 * gA, [4, 6]);         // where the next spoke is
    if (n === 0) guide(EP, ctx, ga, PAL.highlight, 0.85 * gA, [4, 6]);
  }

  // ---- part B: every spoke lands just short of where its neighbour was (five slivers)
  if (fl.short) {
    const al = [];
    for (let j = 0; j < SPOKES; j++) al.push(ov * out(0.10 + 0.08 * j, 0.30 + 0.08 * j));   // clockwise, from the yellow spoke
    slivers(EP, ctx, a0, a1, al);
  }
  // ---- part B: the closest match is 6 degrees BEHIND: the sliver between the emphasised spoke and the old yellow place
  if (a0 != null && fl.seen && Math.abs(seen) > 0.5 && Math.abs(seen - real) > 0.5) {
    const wa = k * out(0.30, 0.60);
    slivers(EP, ctx, a0, a1, [0, 0, 0, 0, wa]);                    // ghost of spoke 0 = the old yellow place
    ctx.save();
    ctx.fillStyle = EP.rgba(PAL.motion, 0.3 * wa);
    sectorPath(ctx, R * 0.665, R_SEEN + 4, mod(a0, 360) + seen, mod(a0, 360));
    ctx.fill();
    ctx.restore();
  }

  // ---- the arrows
  const a0w = a0 != null ? mod(a0, 360) : 0;
  if (a0 != null && fl.real) {
    EP.arcArrow(ctx, CX, CY, R_REAL, a0w * DEG, (a0w + real) * DEG, { kind: 'motion', width: 6, headSize: 24, progress: out(0.06, 0.36), alpha: k });
  }
  if (a0 != null && fl.seen) {
    const pr = out(0.34, 0.64);
    if (Math.abs(seen) > 0.5) {
      EP.arcArrow(ctx, CX, CY, R_SEEN, a0w * DEG, (a0w + seen) * DEG, { kind: 'motion', dash: [9, 6], width: 5.5, headSize: Math.abs(seen) < 20 ? 17 : 21, progress: pr, alpha: k });
    } else {
      seenDot(ctx, EP, a0w, k * pr);                                // an arrow of zero length
    }
  }

  // ---- labels: they stay while the pictures go on, and fade in the first time their arrow appears
  const pres = (key, x0, x1) => (fl[key] ? (fp[key] ? 1 : out(x0, x1)) : fp[key] ? 1 - prog(s, 0, 0.25, ease.inOutSine) : 0) * ov;
  const deg = v => EP.num(v, 0) + '°';
  if (fl.real || fp.real) drawSlot(ctx, EP, makeLabel(EP, ctx, { icon: 'solid', title: T('s04.real'), value: signed(EP, real) }), 0, pres('real', 0.22, 0.44));
  if (fl.gap || fp.gap) drawSlot(ctx, EP, makeLabel(EP, ctx, { icon: 'thin', iconColor: PAL.paper, valueColor: PAL.paper, title: T('s04.gap'), value: deg(GAP) }), 1, pres('gap', 0.45, 0.75));
  if (fl.short || fp.short) drawSlot(ctx, EP, makeLabel(EP, ctx, { icon: 'swatch', iconColor: PAL.motion, valueColor: PAL.paper, title: T('s04.short'), value: deg(GAP - real) }), 1, pres('short', 0.32, 0.55));
  if (fl.seen || fp.seen) {
    const L = makeLabel(EP, ctx, { icon: 'dashed', title: T('s04.seen'), value: signed(EP, seen), verdict: T(verdictKey(seen)), check: m.part === 'A' });
    drawSlot(ctx, EP, L, 1, pres('seen', 0.5, 0.72));
  }

  // ---- part C: once the paint is gone the pictures ARE identical, and only then do we say "frozen"
  if (m.part === 'C') seenFixed(ctx, EP, real, prog(t, 28.5, 29.0, ease.outCubic) * ov);
}

/** an arrow of zero length is a dot: "what we see" did not move */
function seenDot(ctx, EP, deg, a) {
  if (a <= 0) return;
  const [x, y] = P(R_SEEN, deg);
  ctx.save();
  ctx.globalAlpha *= a;
  ctx.fillStyle = EP.PAL.motion;
  ctx.beginPath(); ctx.arc(x, y, 7.5, 0, TAU); ctx.fill();
  ctx.strokeStyle = EP.rgba(EP.PAL.motion, 0.55);
  ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.arc(x, y, 14, 0, TAU); ctx.stroke();
  ctx.restore();
}

/**
 * "What we see" without a yellow spoke to anchor it: a dashed arrow (or a dot when nothing
 * moves) next to its label in slot 2. At real speed the arrow is only a direction glyph
 * (6 degrees would be 32 px), so it says "not to scale".
 */
function seenFixed(ctx, EP, delta, alpha) {
  if (alpha <= 0) return;
  const { T } = EP;
  const seen = EP.wrapSigned(delta * DEG, GAP * DEG) / DEG;
  const moving = Math.abs(seen) > 0.5;
  const at = glyphAt(EP), span = 34;
  const L = makeLabel(EP, ctx, {
    icon: 'dashed', title: T('s04.seen'), value: signed(EP, seen), note: T('s04.perpic'),
    verdict: T(verdictKey(seen)), verdictNote: moving ? T('badge.notscale') : null,
  });
  if (moving) EP.arcArrow(ctx, CX, CY, R_SEEN, at * DEG, (at + Math.sign(seen) * span) * DEG, { kind: 'motion', dash: [10, 7], width: 5.5, headSize: 22, alpha });
  else seenDot(ctx, EP, at, alpha);
  drawSlot(ctx, EP, L, 1, alpha);
}

// ---------------------------------------------------------- real speed runs
function realOverlays(ctx, t, EP, m) {
  const { ease, prog } = EP;
  const r = m.run;
  // "what we see" is told only once the paint is gone (with paint the eye follows the yellow spoke)
  const a = r === Br ? prog(t, 23.7, 24.2, ease.outCubic) * (1 - prog(t, r.t1 - 0.3, r.t1, ease.inOutSine)) : prog(t, 34.8, 35.3, ease.outCubic);
  seenFixed(ctx, EP, r.delta, a);
}

// -------------------------------------------------------------------- panel
/** badge, picture counter (with the camera), "previous picture" key, real-speed readout: reading-start side */
function panel(ctx, t, EP, m, PX) {
  const { PAL, SHADE, ease, prog, win, T } = EP;
  const rtl = EP.isRTL();
  const slow = win(t, 1.5, 22.0, 0.5, 0.35) + win(t, 26.4, 32.4, 0.4, 0.3);
  const real = win(t, 22.0, 26.4, 0.4, 0.3) + win(t, 32.4, 99, 0.4, 0);
  EP.badge(ctx, T('badge.slowx', { n: 30 }), { x: PX, y: 312, align: 'start', opacity: slow });
  EP.badge(ctx, T('badge.real'), { x: PX, y: 312, align: 'start', opacity: real });

  if (m.mode === 'step') {
    const r = m.run, tEnd = r.f1 / FPS;
    const ov = 1 - prog(t, tEnd - SLOW_EDGE, tEnd, ease.inOutSine);
    const a = ov * prog(t, r.t0, r.t0 + 0.3, ease.outCubic);
    const y = 410;
    // the camera ring pulses once for each new picture (a small ring, never a flash)
    EP.camera(ctx, { x: rtl ? PX - 29 : PX + 29, y: y - 17, s: 0.85, color: PAL.paper, opacity: a, shot: m.s < 0.5 ? m.s / 0.5 : 0 });
    EP.text(ctx, T('word.picture', { n: EP.num(m.n + 1) }), { x: rtl ? PX - 76 : PX + 76, y, size: 46, weight: 700, align: 'start', opacity: a });
    if (m.prev != null) {
      const key = measureRow(EP, ctx, [{ line: 'dashed', lw: 2.5, color: SHADE.steelLight }, { gap: 12 }, { text: T('s04.prev'), size: 26, weight: 500, color: PAL.steel }]);
      drawRow(EP, ctx, key, PX, 466, rtl, ov);
    }
  }
  if (m.mode === 'real') {
    const r = m.run;
    const fade = r === Br ? 1 - prog(t, r.t1 - 0.3, r.t1, ease.inOutSine) : 1;
    const a = prog(t, r.t0 + 0.3, r.t0 + 0.8, ease.outCubic) * fade;
    const tps = turnsPerSecond(r);
    const row = measureRow(EP, ctx, [
      { line: 'solid', color: PAL.motion }, { gap: 14 },
      { text: EP.num(tps, Number.isInteger(tps) ? 0 : 1), size: 60, weight: 800, color: PAL.paper, latin: true }, { gap: 14 },
      { text: T('unit.turns'), size: 28, weight: 500, color: PAL.steel },
    ]);
    drawRow(EP, ctx, row, PX, 414, rtl, a);
  }
}

// ------------------------------------------------------------------- sound
const CUES = [];
const ms = x => Math.round(x * 1000) / 1000;
const cue = (t, sfx, o = {}) => CUES.push({ t: ms(t), sfx, ...o, ...(o.dur != null ? { dur: ms(o.dur) } : {}), ...(o.rate != null ? { rate: ms(o.rate) } : {}) });
cue(1.5, 'pop', { gain: -6 });                          // "slowed down" badge
cue(2.3, 'pop');                                        // the yellow paint
for (const r of [A, B, C]) for (let i = 0; i < r.n; i++) cue(r.t0 + i, 'shutter');   // one per picture
cue(A.t0 + 1.25, 'pop');                                // first "real turn" label
cue(A.t0 + 2.5, 'pop');                                 // first "what we see" label, forwards
cue(B.t0 + 0.45, 'pop');                                // "one spoke gap"
cue(B.t0 + 1.3, 'pop', { gain: -6 });                   // "real turn" again, now 66 degrees
cue(B.t0 + 5.32, 'pop');                                // "just short"
cue(B.t0 + 9.5, 'pop');                                 // "what we see: backwards"
cue(Br.t0, 'click');                                    // switch to real speed
cue(Br.t0, 'whirr', { dur: Br.t1 - Br.t0, rate: turnsPerSecond(Br) });
cue(23.7, 'glitch');                                    // the paint is gone: the creep backwards is revealed
cue(C.t0 - 0.1, 'click');                               // back to slow motion
cue(C.t0 + 0.3, 'pop', { gain: -4 });                   // the paint comes back
cue(C.t0 + 1.3, 'pop', { gain: -6 });                   // "real turn +72"
cue(28.5, 'shimmer', { gain: -6, dur: 1.6 });           // the paint is gone: every picture looks the same
cue(Cr.t0, 'click');                                    // real speed again
cue(Cr.t0, 'whirr', { dur: Cr.t1 - Cr.t0, rate: turnsPerSecond(Cr) });
cue(35.0, 'shimmer', { dur: 3 });                       // the paint is gone: frozen while it spins

CUES.sort((a, b) => a.t - b.t);

const SLOW_EDGE = 0.35;   // overlays of a step run leave during its last 0.35 s

/** the yellow paint, 0..1 (highlightAlpha of the wheel) */
function paintAt(EP, t) {
  const { prog, ease } = EP;
  let a = prog(t, 2.2, 3.2, ease.inOutSine);              // "paint one spoke yellow"
  if (t >= 22.6) a = 1 - prog(t, 22.6, 24.1, ease.inOutSine);   // real speed B: paint fades, only identical spokes remain
  if (t >= 26.6) a = prog(t, 26.6, 27.2, ease.inOutSine);       // slow motion again: painted again
  if (t >= 27.95) a = 1 - prog(t, 27.95, 28.4, ease.inOutSine);    // C: after ONE painted step the paint fades, still stepping: from picture 3 all pictures are identical
  if (t >= 32.4) a = prog(t, 32.4, 32.7, ease.inOutSine);       // real speed C: the yellow spoke shows it spins...
  if (t >= 33.5) a = 1 - prog(t, 33.5, 35.0, ease.inOutSine);   // ...then the paint fades: perfectly still
  return a;
}

export default {
  duration: 38.5,
  captions: [
    { key: 's04.c1', in: 0.8, out: 5.0 },
    { key: 's04.c2', in: 5.4, out: 10.2 },
    { key: 's04.c3', in: 10.6, out: 15.4 },
    { key: 's04.c4', in: 15.8, out: 21.4 },
    { key: 's04.c5', in: 21.8, out: 26.6 },
    { key: 's04.c6', in: 27.0, out: 32.0 },
    { key: 's04.c7', in: 32.4, out: 37.8 },
  ],
  cues: CUES,
  music: 'explain',

  render(ctx, t, EP, { W, H }) {
    const { PAL } = EP;
    EP.bg(ctx, W, H);
    // Scene 03 ends on exactly this wheel (960, 606), radius 250, spoke up, still and opaque:
    // it is here from the very first frame, so the cross-fade between the scenes cannot be seen.
    const m = model(t);
    const ang = mod(m.angle, 360) * DEG;
    const paintA = paintAt(EP, t);

    // ------------------------------------------------------------- the wheel
    EP.wheel(ctx, { x: CX, y: CY, r: R, angle: ang, highlight: 0, highlightAlpha: paintA });
    if (m.mode === 'step' && m.s < 0.12) {
      // a new picture: the spokes settle from slightly brighter in 0.12 s (not a flash)
      const k = Math.pow(1 - m.s / 0.12, 1.5);
      ctx.save();
      ctx.translate(CX, CY);
      ctx.fillStyle = EP.rgba(PAL.paper, 0.32 * k);
      for (let i = 0; i < SPOKES; i++) ctx.fill(EP.spokePath(R, i, ang, SPOKES));
      ctx.restore();
    }

    // the reading-start side of the stage belongs to the panel (badge, counter, readout)
    const PX = EP.startX(96);
    if (m.mode === 'step') stepOverlays(ctx, t, EP, m, paintA);
    if (m.mode === 'real') realOverlays(ctx, t, EP, m);
    panel(ctx, t, EP, m, PX);
  },
};
