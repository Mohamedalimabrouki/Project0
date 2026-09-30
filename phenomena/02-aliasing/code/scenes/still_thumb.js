/*
 * Thumbnail - Engineering Phenomena 02 - Aliasing (1280 x 720).
 *
 * Built to be read at 320 px wide on a phone: three things only.
 *   1. a huge wheel with its yellow painted spoke, cropped by the frame;
 *   2. a bold DASHED blue arrow going round the wrong way (dashed = what the
 *      video shows, the alias; the wheel itself turns the other way);
 *   3. one word, BACKWARDS?, in very heavy type, plus a small speed hint.
 * The hint is computed, not typed: 5.5 turns per second of a 0.33 m tyre is
 * 41 km/h, the speed at which this 5-spoke wheel seems to creep backwards on a
 * 30 pictures-per-second video (at 44.8 km/h it would look frozen instead).
 */

const TYRE_RADIUS = 0.33;                       // m
const FR = 5.5;                                 // wheel turns per second
const KMH = 2 * Math.PI * TYRE_RADIUS * FR * 3.6; // 41.05 km/h

// ------------------------------------------------------------ dithered backdrop
// EP.bg (ink + grid) and then the house vignette and a soft glow behind the wheel,
// computed in floating point and rounded with a fixed, deterministic dither. Very
// dark gradients drawn straight into an 8-bit canvas show faint bands; dithering
// them removes the bands and costs nothing visible. Same two circles as EP.bg.
function backdrop(ctx, EP, W, H, { cx, cy, glowR, glow }) {
  EP.bg(ctx, W, H, { vignette: false, offsetX: cx - 0.5, offsetY: cy - 0.5 });
  const s = ctx.getTransform().a;
  const Wp = Math.round(W * s), Hp = Math.round(H * s);
  const img = ctx.getImageData(0, 0, Wp, Hp), d = img.data;
  const [vr, vg, vb] = EP.hexToRgb(EP.SHADE.inkDeep);
  const [gr, gg, gb] = EP.hexToRgb(EP.PAL.steel);
  // vignette circles (as EP.bg) and glow circles (concentric on the hub)
  const x0 = W / 2, y0 = H * 0.48, r0 = Math.min(W, H) * 0.35, y1 = H / 2, r1 = Math.hypot(W, H) * 0.62;
  const dy = y1 - y0, dr = r1 - r0, qa = dy * dy - dr * dr;
  const g0 = glowR * 0.2, g1 = glowR * glow.reach;
  const rand = EP.rng(20260929);
  for (let py = 0; py < Hp; py++) {
    const ly = (py + 0.5) / s;
    for (let px = 0; px < Wp; px++) {
      const lx = (px + 0.5) / s;
      // vignette: parameter t of the circle through this point (canvas radial gradient)
      const ax = lx - x0, ay = ly - y0;
      const qb = ay * dy + r0 * dr, qc = ax * ax + ay * ay - r0 * r0;
      const disc = qb * qb - qa * qc;
      let t = 1;
      if (disc >= 0) {
        const sq = Math.sqrt(disc);
        const t1 = (qb + sq) / qa, t2 = (qb - sq) / qa;
        const ok1 = r0 + t1 * dr >= 0, ok2 = r0 + t2 * dr >= 0;
        t = ok1 && ok2 ? Math.max(t1, t2) : ok1 ? t1 : ok2 ? t2 : 1;
      }
      const av = 0.85 * (t < 0 ? 0 : t > 1 ? 1 : t);
      // glow behind the wheel
      const dist = Math.hypot(lx - cx, ly - cy);
      const tg = Math.min(1, Math.max(0, (dist - g0) / (g1 - g0)));
      const ag = tg < 0.5 ? glow.a0 + (glow.a1 - glow.a0) * (tg / 0.5) : glow.a1 * (1 - (tg - 0.5) / 0.5);
      const u = rand() - 0.5;
      const i = (py * Wp + px) * 4;
      for (let k = 0; k < 3; k++) {
        let c = d[i + k];
        c += av * ((k === 0 ? vr : k === 1 ? vg : vb) - c);
        c += ag * ((k === 0 ? gr : k === 1 ? gg : gb) - c);
        d[i + k] = Math.round(c + u);
      }
    }
  }
  ctx.putImageData(img, 0, 0);
}

export default {
  duration: 1,
  captions: [],
  math: [],

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, rgba } = EP;
    const D = Math.PI / 180;
    const M = 64;                               // outer margin: 5 % of the width (style guide safe area)

    // ------------------------------------------------------------ layout
    const R = 470;
    const cx = 860, cy = 580;
    const A = -50 * D;                          // the painted spoke, upper left

    backdrop(ctx, EP, W, H, { cx, cy, glowR: R, glow: { a0: 0.16, a1: 0.05, reach: 1.9 } });

    // ------------------------------------------------------------ wheel
    EP.wheel(ctx, { x: cx, y: cy, r: R, angle: A, highlight: 0, caliper: false });
    {   // restrained polish: soft light from the top left on the tyre, sidewall lines, rim highlight
      ctx.save();
      ctx.translate(cx, cy);
      const tyre = new Path2D();
      tyre.arc(0, 0, R * 0.995, 0, EP.TAU);
      tyre.moveTo(R * 0.69, 0);
      tyre.arc(0, 0, R * 0.69, 0, EP.TAU, true);
      const cg = ctx.createConicGradient(-135 * D, 0, 0);
      cg.addColorStop(0, rgba(PAL.paper, 0.075));
      cg.addColorStop(0.25, rgba(PAL.paper, 0.012));
      cg.addColorStop(0.5, rgba(PAL.ink, 0.22));
      cg.addColorStop(0.75, rgba(PAL.paper, 0.012));
      cg.addColorStop(1, rgba(PAL.paper, 0.075));
      ctx.fillStyle = cg;
      ctx.fill(tyre);
      ctx.lineWidth = 1.4;
      for (const [k, a] of [[0.755, 0.10], [0.835, 0.06], [0.915, 0.06]]) {
        ctx.strokeStyle = rgba(PAL.steel, a);
        ctx.beginPath(); ctx.arc(0, 0, R * k, 0, EP.TAU); ctx.stroke();
      }
      ctx.strokeStyle = rgba(PAL.paper, 0.5);
      ctx.lineWidth = 3;
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.arc(0, 0, R * 0.683, -128 * D - Math.PI / 2, -58 * D - Math.PI / 2); ctx.stroke();
      ctx.restore();
    }

    {   // same light from the top left across the four steel spokes; small halo on the painted one
      ctx.save();
      ctx.translate(cx, cy);
      const steel = new Path2D();
      for (let i = 1; i < 5; i++) steel.addPath(EP.spokePath(R, i, A, 5));
      ctx.clip(steel);
      const lg = ctx.createLinearGradient(-R * 0.6, -R * 0.6, R * 0.6, R * 0.6);
      lg.addColorStop(0, rgba(PAL.paper, 0.13));
      lg.addColorStop(0.5, rgba(PAL.paper, 0));
      lg.addColorStop(1, rgba(PAL.ink, 0.3));
      ctx.fillStyle = lg;
      ctx.fillRect(-R, -R, 2 * R, 2 * R);
      ctx.restore();

      ctx.save();
      ctx.translate(cx - 6000, cy);                 // only the shadow lands on the canvas
      ctx.shadowColor = rgba(PAL.highlight, 0.5);
      ctx.shadowBlur = 34 * ctx.getTransform().a;
      ctx.shadowOffsetX = 6000 * ctx.getTransform().a;
      ctx.fillStyle = PAL.highlight;
      ctx.fill(EP.spokePath(R, 0, A, 5));
      ctx.restore();
    }

    // ------------------------------------------ the backwards dashed arrow
    // Counter-clockwise (backwards) round the left of the wheel: three dashes,
    // then a solid stem that runs through the open head (no stray cap in the V).
    // The angular span follows from the pattern, so dashes always fit exactly.
    const lw = 28, rA = R * 1.175;
    const a0 = -60 * D;
    const on = lw * 1.2, off = lw * 1.8, dashes = 3, stem = lw * 3.9;
    const total = dashes * (on + off) + stem;                  // arc length in px
    const a1 = a0 - total / rA;
    const aStem = a0 - (dashes * (on + off)) / rA;
    ctx.save();
    ctx.strokeStyle = PAL.motion;
    ctx.lineWidth = lw;
    ctx.lineCap = 'round';
    ctx.setLineDash([on, off]);
    ctx.beginPath();
    ctx.arc(cx, cy, rA, a0 - Math.PI / 2, aStem - Math.PI / 2, true);
    ctx.stroke();
    ctx.restore();
    EP.arcArrow(ctx, cx, cy, rA, aStem, a1, { kind: 'motion', width: lw, headSize: lw * 3.2 });

    // ------------------------------------------------------------ the word
    const full = EP.T('thumb.word');
    const m = full.match(/^(.*?)(\s*[?!؟]+)$/);
    const body = m ? m[1] : full, punct = m ? m[2] : '';
    const opt = { weight: 900, tracking: rtl ? 0 : -0.01, latin: false };
    const w100 = EP.measure(ctx, full, { ...opt, size: 100 }).w;
    const S = Math.min(rtl ? 190 : 200, (100 * (W - 2 * M)) / w100);
    const base = rtl ? 240 : 196;                // Arabic ascenders and descenders need more room
    const wBody = EP.measure(ctx, body, { ...opt, size: S }).w;
    if (!rtl) {
      EP.text(ctx, body, { ...opt, size: S, x: M, y: base, align: 'left', color: PAL.paper });
      if (punct) EP.text(ctx, punct, { ...opt, size: S, x: M + wBody, y: base, align: 'left', color: PAL.highlight });
    } else {
      EP.text(ctx, body, { ...opt, size: S, x: W - M, y: base, align: 'right', color: PAL.paper });
      if (punct) EP.text(ctx, punct, { ...opt, size: S, x: W - M - wBody, y: base, align: 'right', color: PAL.highlight });
    }

    // ------------------------------------------------------------ the hint
    EP.text(ctx, EP.qty(KMH, 'km/h', 0), {
      x: M, y: 304, size: 78, weight: 800, color: PAL.paper, latin: true, align: 'left',   // left in every language: that side is free
    });
  },
};
