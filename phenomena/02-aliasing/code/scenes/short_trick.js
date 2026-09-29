// PLACEHOLDER - replaced by the Short's author.
export default {
  duration: 22.5,
  captions: [],
  render(ctx, t, EP, { W, H }) {
    EP.bg(ctx, W, H);
    EP.text(ctx, 'PLACEHOLDER  short_trick', { x: W / 2, y: H / 2, align: 'center', size: 40, weight: 700, color: EP.PAL.steel, latin: true });
  },
};
