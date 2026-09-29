// PLACEHOLDER - replaced by the scene author. Shows the scene id and its captions.
import strings from '../data/strings/s06_helicopter_lathe.json' with { type: 'json' };
const keys = Object.keys(strings).filter(k => /\.c\d+$/.test(k));
const n = keys.length, d = 22.5;
export default {
  duration: d,
  captions: keys.map((key, i) => ({ key, in: 0.8 + i * (d - 1.6) / n, out: 0.8 + (i + 1) * (d - 1.6) / n - 0.4 })),
  cues: [],
  render(ctx, t, EP, { W, H }) {
    EP.bg(ctx, W, H);
    EP.text(ctx, 'PLACEHOLDER  s06_helicopter_lathe', { x: W / 2, y: H / 2, align: 'center', size: 40, weight: 700, color: EP.PAL.steel, latin: true });
    EP.text(ctx, 't = ' + t.toFixed(2) + ' s', { x: W / 2, y: H / 2 + 60, align: 'center', size: 30, color: EP.PAL.steel, latin: true });
  },
};
