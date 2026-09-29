/*
 * Hero still - Engineering Phenomena 02 - Aliasing.  The poster (3840 x 2160,
 * drawn on the 1920 x 1080 canvas at scale 2).
 *
 * The whole idea in one picture, a stroboscopic multi-exposure:
 *   - the wheel as it is in the LAST picture (solid, one spoke painted yellow);
 *   - the earlier pictures as fading ghosts, one every 66 degrees. Because the
 *     spokes are 72 degrees apart, every older ghost sits 6 degrees further
 *     round (clockwise) than the one after it: the trail of ghosts looks like
 *     a wheel creeping BACKWARDS, which is exactly the illusion;
 *   - the painted spoke's true path between two pictures: solid blue, +66 deg;
 *   - the apparent path (to the nearest spoke of the next picture): dashed
 *     blue, -6 deg.
 *
 * Every angle is computed from the film's numbers, none is typed by eye:
 *   5 spokes, 30 pictures per second, 5.5 turns per second (41 km/h).
 */

// ---------------------------------------------------------------- the numbers
const N = 5;                                   // identical spokes
const FS = 30;                                 // pictures per second
const FR = 5.5;                                // wheel turns per second
const GAP = 360 / N;                           // 72 deg between two spokes
const STEP = (360 * FR) / FS;                  // 66 deg turned between two pictures
const SEEN = STEP - GAP * Math.round(STEP / GAP); // -6 deg: nearest spoke, backwards
const GHOSTS = 5;                              // earlier pictures shown as ghosts

const signed = v => `${v < 0 ? '-' : '+'}${Math.abs(v)}^{\\circ}`;
const TEX_STEP = signed(STEP);                 // +66^{\circ}
const TEX_SEEN = signed(SEEN);                 // -6^{\circ}
const TEX_RULE = 'f_s > 2\\,f_{\\max}';

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
  math: [TEX_STEP, TEX_SEEN, TEX_RULE],

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, TAU, rgba, polar } = EP;
    const D = Math.PI / 180;
    const sc = ctx.getTransform().a;             // device pixels per logical pixel

    // ---------------------------------------------------------------- layout
    const R = 384;                               // tyre radius (8 grid cells of 48 px)
    const cy = 576;
    const cx = rtl ? 852 : 1344;                 // the diagram never mirrors, the layout does
    const x0 = EP.startX(144);                   // left margin (right margin in Arabic)

    const A_NOW = 0;                             // yellow spoke in the last picture: 12 o'clock
    const A_PREV = A_NOW - STEP * D;             // ... and in the picture before
    const A_NEAR = A_PREV + SEEN * D;            // nearest spoke of the last picture

    const cv = a => a - Math.PI / 2;             // clock angle -> canvas angle
    // ring sector between clock angles a0 < a1 and radii r0 < r1
    const sector = (a0, a1, r0, r1) => {
      const p = new Path2D();
      p.arc(cx, cy, r1, cv(a0), cv(a1));
      p.arc(cx, cy, r0, cv(a1), cv(a0), true);
      p.closePath();
      return p;
    };

    // ------------------------------------------------------------ background
    backdrop(ctx, EP, W, H, { cx, cy, glowR: R, glow: { a0: 0.14, a1: 0.05, reach: 2.1 } });   // a grid line runs through the hub

    // ------------------------------------------ angle wedges on the tyre
    // the 66 deg the painted spoke really turns (blue) and the 6 deg gap (paper)
    {
      const gb = ctx.createRadialGradient(cx, cy, R * 0.9, cx, cy, R * 1.115);   // deepens towards the arrow
      gb.addColorStop(0, rgba(PAL.motion, 0.07));
      gb.addColorStop(1, rgba(PAL.motion, 0.34));
      ctx.fillStyle = gb;
      ctx.fill(sector(A_PREV, A_NOW, R * 0.69, R * 1.115));
      const gp = ctx.createRadialGradient(cx, cy, R * 0.9, cx, cy, R * 1.62);
      gp.addColorStop(0, rgba(PAL.paper, 0.05));
      gp.addColorStop(1, rgba(PAL.paper, 0.16));
      ctx.fillStyle = gp;
      ctx.fill(sector(A_NEAR, A_PREV, R * 0.69, R * 1.62));
    }

    // ----------------------------------------------------------- the wheel
    EP.wheel(ctx, { x: cx, y: cy, r: R, angle: A_NOW, spokes: N, highlight: 0, caliper: false });

    // restrained polish on the tyre and rim: light from the top left (as the engine's sheen)
    {
      ctx.save();
      ctx.translate(cx, cy);
      const tyre = new Path2D();
      tyre.arc(0, 0, R * 0.995, 0, TAU);
      tyre.moveTo(R * 0.69, 0);
      tyre.arc(0, 0, R * 0.69, 0, TAU, true);
      const cg = ctx.createConicGradient(-135 * D, 0, 0);       // position 0 = top left, clockwise
      cg.addColorStop(0, rgba(PAL.paper, 0.075));
      cg.addColorStop(0.25, rgba(PAL.paper, 0.012));
      cg.addColorStop(0.5, rgba(PAL.ink, 0.22));
      cg.addColorStop(0.75, rgba(PAL.paper, 0.012));
      cg.addColorStop(1, rgba(PAL.paper, 0.075));
      ctx.fillStyle = cg;
      ctx.fill(tyre);
      // sidewall lines
      ctx.lineWidth = 1.2;
      for (const [k, a] of [[0.755, 0.10], [0.835, 0.06], [0.915, 0.06]]) {
        ctx.strokeStyle = rgba(PAL.steel, a);
        ctx.beginPath(); ctx.arc(0, 0, R * k, 0, TAU); ctx.stroke();
      }
      // specular line on the rim lip, top left
      ctx.strokeStyle = rgba(PAL.paper, 0.55);
      ctx.lineWidth = 2.4;
      ctx.lineCap = 'round';
      ctx.beginPath(); ctx.arc(0, 0, R * 0.683, cv(-128 * D), cv(-58 * D)); ctx.stroke();
      ctx.restore();
    }

    // the same light from the top left across the four steel spokes (the painted spoke stays pure)
    {
      ctx.save();
      ctx.translate(cx, cy);
      const steel = new Path2D();
      for (let i = 1; i < N; i++) steel.addPath(EP.spokePath(R, i, A_NOW, N));
      ctx.clip(steel);
      const lg = ctx.createLinearGradient(-R * 0.6, -R * 0.6, R * 0.6, R * 0.6);
      lg.addColorStop(0, rgba(PAL.paper, 0.13));
      lg.addColorStop(0.5, rgba(PAL.paper, 0));
      lg.addColorStop(1, rgba(PAL.ink, 0.3));
      ctx.fillStyle = lg;
      ctx.fillRect(-R, -R, 2 * R, 2 * R);
      ctx.restore();
    }

    // soft halo on the painted spoke (only its shadow is drawn, the shape is off-canvas)
    ctx.save();
    ctx.translate(cx - 6000, cy);
    ctx.shadowColor = rgba(PAL.highlight, 0.55);
    ctx.shadowBlur = 30 * sc;
    ctx.shadowOffsetX = 6000 * sc;
    ctx.fillStyle = PAL.highlight;
    ctx.fill(EP.spokePath(R, 0, A_NOW, N));
    ctx.restore();

    // earlier pictures, fading with age. Drawn only in the ring between hub and rim
    // and never over the spokes of the last picture, which stay crisp on top.
    ctx.save();
    ctx.translate(cx, cy);
    const ring = new Path2D();
    ring.arc(0, 0, R * 0.627, 0, TAU);
    ring.moveTo(R * 0.205, 0);
    ring.arc(0, 0, R * 0.205, 0, TAU, true);
    ctx.clip(ring);
    const notSolid = new Path2D();
    notSolid.rect(-R, -R, 2 * R, 2 * R);
    for (let i = 0; i < N; i++) notSolid.addPath(EP.spokePath(R, i, A_NOW, N));
    ctx.clip(notSolid, 'evenodd');
    for (let k = GHOSTS; k >= 1; k--) {
      const a = A_NOW - k * STEP * D;
      const op = Math.pow(0.68, k - 1);
      for (let i = 0; i < N; i++) {
        ctx.fillStyle = i === 0 ? rgba(PAL.highlight, 0.10 * op) : rgba(PAL.paper, 0.13 * op);
        ctx.fill(EP.spokePath(R, i, a, N));
      }
      EP.wheelGhost(ctx, { x: 0, y: 0, r: R, angle: a, spokes: N, color: PAL.paper, opacity: 0.6 * op, width: 1.6 });
      EP.wheelGhost(ctx, { x: 0, y: 0, r: R, angle: a, spokes: N, color: PAL.highlight, opacity: 0.95 * op, width: 2.6, only: 0 });
    }
    ctx.restore();

    // ---------------------------------------------- dimension arrows (blue)
    const rS = R * 1.115;                        // solid arc: the true path
    const rD = R * 1.62;                         // dashed arc: what the video shows
    const lw = 7;
    const ext = (ang, r0, r1, color, alpha) => {
      const [x1, y1] = polar(cx, cy, r0, ang), [x2, y2] = polar(cx, cy, r1, ang);
      const g = ctx.createLinearGradient(x1, y1, x2, y2);
      g.addColorStop(0, rgba(color, alpha * 0.25));
      g.addColorStop(0.5, rgba(color, alpha));
      g.addColorStop(1, rgba(color, alpha));
      ctx.save();
      ctx.strokeStyle = g;
      ctx.lineWidth = 1.8;
      ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
      ctx.restore();
    };
    ext(A_NOW, R * 0.70, rS + R * 0.045, PAL.highlight, 0.9);
    ext(A_PREV, R * 0.70, rD + R * 0.045, PAL.highlight, 0.9);
    ext(A_NEAR, R * 0.70, rD + R * 0.045, PAL.paper, 0.7);

    EP.arcArrow(ctx, cx, cy, rS, A_PREV, A_NOW, { kind: 'motion', width: lw, headSize: lw * 4.2 });
    EP.arcArrow(ctx, cx, cy, rD, A_PREV, A_NEAR, { kind: 'motion', width: lw * 1.2, headSize: lw * 1.2 * 3.2, dash: [lw * 1.2, lw * 2.4] });

    // numbers (TeX) with a one-word tag above, on the number's reading-start edge
    const numSize = 92, tagSize = 22;
    const tag = (ang, r, tex, word) => {
      const [px, py] = polar(cx, cy, r, ang);
      const b = EP.math(ctx, tex, { x: px, y: py, size: numSize, align: 'right', anchor: 'bottom' });
      EP.text(ctx, word, {
        x: rtl ? b.x + b.w : b.x + 4, y: b.y - (rtl ? 16 : 6), size: tagSize, weight: 700, tracking: 0.16, caps: true,
        color: PAL.steel, align: 'start',
      });
    };
    tag((A_PREV + A_NOW) / 2, rS + R * 0.1, TEX_STEP, EP.T('hero.real'));
    tag((A_PREV + A_NEAR) / 2, rD + R * 0.07, TEX_SEEN, EP.T('hero.seen'));

    // ------------------------------------------------------------ typography
    // The lockup sits on the same 48 px grid that runs through the hub: the yellow
    // rule is on the hub's horizontal grid line, the title's cap height is 3 cells.
    const mastY = cy + 24 * 0.36 + 0.5;
    ctx.fillStyle = PAL.highlight;
    ctx.fillRect(rtl ? x0 - 34 : x0, cy - 1, 34, 3);
    EP.text(ctx, 'ENGINEERING PHENOMENA  ·  02', {
      x: rtl ? x0 - 34 - 16 : x0 + 34 + 16, y: mastY, align: rtl ? 'right' : 'left',
      size: 24, weight: 700, tracking: 0.2, latin: true, color: PAL.highlight,
    });

    const title = EP.text(ctx, EP.T('hero.title'), {
      x: x0, y: cy + 240, size: 200, weight: 800, tracking: rtl ? 0 : -0.02, color: PAL.paper,
    });
    // The tagline is set exactly as wide as the title (a justified lockup) in every language:
    // its size is measured, not typed. Text is always shorter than the title box allows below 28 px.
    const tagline = EP.T('hero.tagline');
    const wide = Math.min(760, Math.max(700, title.w));
    const w100 = EP.measure(ctx, tagline, { size: 100, weight: 500 }).w;
    EP.text(ctx, tagline, {
      x: x0, y: cy + 340, size: Math.min(46, Math.max(28, (100 * wide) / w100)), weight: 500, color: PAL.steel,
    });

    ctx.fillStyle = rgba(PAL.steel, 0.55);
    ctx.fillRect(rtl ? x0 - 56 : x0, cy + 368, 56, 2);
    EP.math(ctx, TEX_RULE, { x: x0, y: cy + 428, size: 50, align: rtl ? 'right' : 'left', anchor: 'baseline' });
  },
};
