/*
 * Scene 02 - Opening card: "Engineering Phenomena 02 - Aliasing".
 *
 * Reference scene: it shows the scene contract every scene follows.
 *   - render(ctx, t, EP, info) is a pure function of t (seconds from the
 *     start of this scene). No state is kept between frames.
 *   - captions: narration lines. The engine draws them in the caption band
 *     at the top of the frame and turns them into the .srt subtitle files.
 *     burn: false = subtitle file only (here the title is already on screen).
 *   - cues: sound effects, at seconds from the start of this scene.
 *   - math: every TeX string drawn with EP.math() must be listed here.
 */

const WHEEL_RATE = 0.12; // turns per second: a calm, honest forward turn

export default {
  duration: 6.5,
  hideLogo: true, // the series name is on screen already
  captions: [
    { key: 's02.srt', in: 0.6, out: 5.9, burn: false },
  ],
  cues: [
    { t: 0.1, sfx: 'swoosh_rev', dur: 0.8 },
    { t: 0.85, sfx: 'hit' },
    { t: 1.5, sfx: 'shimmer', gain: -8 },
    { t: 5.7, sfx: 'whoosh', gain: -6 },
  ],
  music: 'title',

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, ease, prog, text, eyebrow, T } = EP;
    EP.bg(ctx, W, H);

    // everything leaves together at the end
    const out = 1 - prog(t, 5.55, 6.3, ease.inOutSine);
    const cx = W / 2;

    // wheel mark: fades and scales in, turns slowly forwards
    const kW = prog(t, 0.15, 1.1, ease.outBack);
    const aW = prog(t, 0.15, 0.7, ease.outCubic);
    if (aW > 0) {
      ctx.save();
      ctx.translate(cx, 318);
      ctx.scale(0.7 + 0.3 * kW, 0.7 + 0.3 * kW);
      EP.wheel(ctx, { x: 0, y: 0, r: 62, angle: EP.TAU * WHEEL_RATE * t, highlight: 0, highlightAlpha: prog(t, 1.2, 1.8), opacity: aW * out });
      ctx.restore();
    }

    // series line, always in Latin letters (it is the brand)
    const aE = prog(t, 0.45, 1.05, ease.outCubic);
    text(ctx, 'ENGINEERING PHENOMENA  ·  02', {
      x: cx, y: 452, align: 'center', size: 24, weight: 700, tracking: 0.2, latin: true,
      color: PAL.highlight, opacity: aE * out, reveal: prog(t, 0.45, 1.25, ease.outCubic),
    });

    // title: rises into place while its letter spacing settles
    const kT = prog(t, 0.75, 1.65, ease.outQuint);
    text(ctx, T('s02.title'), {
      x: cx, y: 590 + 26 * (1 - kT), align: 'center', size: 156, weight: 800,
      tracking: rtl ? 0 : -0.02 + 0.06 * (1 - kT), color: PAL.paper, opacity: kT * out,
    });

    // tagline
    const kG = prog(t, 1.3, 2.1, ease.outCubic);
    text(ctx, T('s02.tagline'), {
      x: cx, y: 676 + 12 * (1 - kG), align: 'center', size: 46, weight: 500,
      color: PAL.steel, opacity: kG * out, maxWidth: 1500, shrink: true, maxLines: 1,
    });

    // the house colour strip (as on the series banner), growing from the centre
    const kS = prog(t, 1.7, 2.6, ease.inOutCubic) * out;
    if (kS > 0) {
      const cols = [PAL.force, PAL.motion, PAL.energy, PAL.fluid, PAL.field, PAL.balance, PAL.highlight];
      const full = 420, seg = full / cols.length, w = full * kS;
      cols.forEach((c, i) => {
        const x0 = cx - full / 2 + i * seg;
        const vis0 = Math.max(x0, cx - w / 2), vis1 = Math.min(x0 + seg, cx + w / 2);
        if (vis1 > vis0) { ctx.fillStyle = c; ctx.fillRect(vis0, 736, vis1 - vis0, 6); }
      });
    }
  },
};
