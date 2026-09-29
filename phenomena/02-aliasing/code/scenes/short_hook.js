/*
 * Short (9:16, 1080 x 1920) - scene 1: the hook (16.5 s).
 *
 * A car seen from the side, framed on its rear wheel. The car speeds up from
 * walking pace to 47 km/h. The wheel is drawn at its TRUE turning rate, one
 * exact angle per video frame, so the viewer's own screen samples it 30 times a
 * second and shows the wagon-wheel effect for real: forwards, confusion,
 * backwards, frozen at 6 turns per second, then creeping forwards.
 *
 * Everything on screen is computed:
 *   f_r(t)   wheel turns per second (smooth blend through the story knots)
 *   angle    integral of 2 pi f_r  (EP.angleTable), drawn exactly, no blur
 *   road     scrolls by  r * angle  pixels (rolling without slipping), so the
 *            road moves at exactly  v = 2 pi R f_r  metres per second, with
 *            pixels per metre = wheel radius in pixels / 0.33 m
 *   readouts m/s, km/h and turns per second, all from f_r(t)
 */

// ----------------------------------------------------------------- physics
export const R_TYRE = 0.33;           // tyre radius (m)
export const FPS = 30;
/** [time (s), turns per second]. Blended smoothly (monotone cubic, no overshoot). */
export const KNOTS = [
  [0, 0.35], [3.5, 2.0], [5.5, 4.7], [8.5, 5.86], [9.5, 6.0],
  [12.0, 6.0],                        // hold: exactly 6 turns per second (72 degrees per picture)
  [15.0, 6.25], [17.0, 6.25],
];

/** Monotone cubic Hermite (Fritsch-Carlson) through the knots: smooth, never overshoots. */
export function blend(knots) {
  const n = knots.length;
  const x = knots.map(k => k[0]), y = knots.map(k => k[1]);
  const h = [], m = [];
  for (let i = 0; i < n - 1; i++) { h[i] = x[i + 1] - x[i]; m[i] = (y[i + 1] - y[i]) / h[i]; }
  const d = new Array(n).fill(0);            // zero slope at both ends and at every flat part
  for (let i = 1; i < n - 1; i++) {
    if (m[i - 1] * m[i] > 0) {
      const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1];
      d[i] = (w1 + w2) / (w1 / m[i - 1] + w2 / m[i]);
    }
  }
  return t => {
    if (t <= x[0]) return y[0];
    if (t >= x[n - 1]) return y[n - 1];
    let i = 0;
    while (t > x[i + 1]) i++;
    const s = (t - x[i]) / h[i], s2 = s * s, s3 = s2 * s;
    return (2 * s3 - 3 * s2 + 1) * y[i] + (s3 - 2 * s2 + s) * h[i] * d[i]
      + (-2 * s3 + 3 * s2) * y[i + 1] + (s3 - s2) * h[i] * d[i + 1];
  };
}
export const rate = blend(KNOTS);

// Where the trick scene freezes the wheel (its local t = 0.5 s = this scene's 16.5 s): the wheel is
// turned so that picture 1 of the trick has the painted spoke exactly at 12 o'clock. Same constant
// in short_trick.js, so the wheel is identical in the cross-fade between the two scenes.
export const FREEZE_AT = 16.5;

// ----------------------------------------------------------------- layout (px)
const CX = 540, CY = 1070;            // rear wheel centre at full zoom
const Y_CREASE = 708;                 // the car body is cropped at its shoulder crease, just under the readouts
const R0 = 300;                       // tyre radius at full zoom
const ZOOM0 = 0.9;                    // the camera starts a little wider and settles on the wheel
const LEFT = 60, RIGHT = 920;         // text margins (right edge kept free for the app buttons)

let spin = null;                      // angle table, built once in setup
let phase = 0;                        // constant turn so the trick scene can freeze on a nice pose
let streaks = null;
let layer = null;                     // off-screen canvas for the car body (masked)

function makeStreaks(EP) {
  const rnd = EP.rng(2026);
  const P = 12000, list = [];
  for (let i = 0; i < 190; i++) {
    const depth = Math.pow(rnd(), 0.85);
    list.push({
      x0: rnd() * P,
      y: 10 + depth * 150,
      len: 26 + Math.pow(rnd(), 1.7) * 210,
      w: 1.6 + rnd() * 2.2 + depth * 1.4,
      a: 0.16 + rnd() * 0.36,
      paper: rnd() < 0.3,
    });
  }
  return { P, list };
}

/** Icon: circular arrow. dir +1 clockwise (solid = what really happens). */
function turnIcon(EP, ctx, x, y, r, dir, o = {}) {
  const a0 = dir > 0 ? -135 * EP.DEG : 135 * EP.DEG;
  const a1 = dir > 0 ? 120 * EP.DEG : -120 * EP.DEG;
  EP.arcArrow(ctx, x, y, r, a0, a1, { width: o.width || 6, headSize: o.headSize || 22, dash: o.dash || null, alpha: o.alpha ?? 1 });
}

/** Sideways space a tabular digit leaves in front of its ink (a '1' sits in a wide cell): removed so numbers line up with the text above. */
function tabIndent(EP, ctx, str, size, weight) {
  ctx.save();
  ctx.font = EP.fontStr(size, weight, { latin: true });
  ctx.textAlign = 'center';
  const cell = ctx.measureText('0').width;
  const m = ctx.measureText(String(str)[0]);
  ctx.restore();
  return Math.max(0, cell / 2 - m.actualBoundingBoxLeft);
}

/** Draw parts left to right as one group aligned at x. parts: {s, tab, size, weight, color, latin, gap}. */
function group(EP, ctx, x, y, parts, align, opacity = 1) {
  const ws = parts.map(p => (p.tab
    ? EP.textTab(ctx, p.s, { size: p.size, weight: p.weight, opacity: 0 }).w
    : EP.measure(ctx, p.s, { size: p.size, weight: p.weight, latin: p.latin, tracking: p.tracking || 0, caps: p.caps }).w));
  const total = ws.reduce((a, b, i) => a + b + (i < ws.length - 1 ? (parts[i].gap ?? 12) : 0), 0);
  let cx = align === 'right' ? x - total : align === 'center' ? x - total / 2 : x;
  if (parts[0].tab && align === 'left') cx -= tabIndent(EP, ctx, parts[0].s, parts[0].size, parts[0].weight);
  parts.forEach((p, i) => {
    if (p.tab) EP.textTab(ctx, p.s, { x: cx, y, size: p.size, weight: p.weight, color: p.color, opacity, align: 'left' });
    else EP.text(ctx, p.s, { x: cx, y, size: p.size, weight: p.weight, color: p.color, opacity, latin: p.latin, tracking: p.tracking || 0, caps: p.caps, align: 'left' });
    cx += ws[i] + (p.gap ?? 12);
  });
  return total;
}

export default {
  duration: 16.5,
  strings: ['s01_hook'],
  captionBand: { y: 366 },            // a little lower than the engine default (330): keeps the series mark (top right, y 285-305) clear
  captions: [
    { key: 's01.c1', in: 0.8, out: 3.6 },
    { key: 's01.c2', in: 4.0, out: 6.0 },
    { key: 's01.c3', in: 6.4, out: 9.0 },
    { key: 's01.c4', in: 9.4, out: 12.4 },
    { key: 's01.c5', in: 12.8, out: 15.9 },
  ],
  cues: [
    { t: 0.2, sfx: 'car', dur: 16 },
    { t: 6.4, sfx: 'glitch' },
    { t: 9.5, sfx: 'shimmer', dur: 2.5 },
  ],
  music: 'hook',

  setup(EP) {
    spin = EP.angleTable(rate, 0, 17.5);
    phase = -(spin(FREEZE_AT) % EP.TAU);
    streaks = makeStreaks(EP);
  },

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, ease, prog, text, T, num } = EP;
    EP.bg(ctx, W, H);

    const fr = rate(t);                                  // turns per second, right now
    const theta = spin(t) + phase;                       // exact wheel angle (rad), clockwise
    const v = EP.TAU * R_TYRE * fr;                      // car speed (m/s)
    const zoom = ZOOM0 + (1 - ZOOM0) * prog(t, 0, 4.2, ease.inOutSine);
    const r = R0;                                        // (world units; the zoom scales everything)
    const yg = CY + r;                                   // ground line
    const pxPerFrame = r * EP.TAU * fr / FPS;            // road movement per picture, world px

    // ---- world layer (zooms about the wheel centre)
    ctx.save();
    ctx.translate(CX, CY); ctx.scale(zoom, zoom); ctx.translate(-CX, -CY);

    // car body: dimmed and faded into the dark around the wheel (off-screen, masked)
    const s = ctx.getTransform().a / zoom;               // engine pixel scale (1 for the Short)
    if (!layer || layer.canvas.width !== Math.round(W * s)) {
      const c = document.createElement('canvas');
      c.width = Math.round(W * s); c.height = Math.round(H * s);
      layer = { canvas: c, ctx: c.getContext('2d') };
    }
    const L = layer.ctx;
    L.setTransform(1, 0, 0, 1, 0, 0);
    L.globalCompositeOperation = 'source-over';
    L.clearRect(0, 0, layer.canvas.width, layer.canvas.height);
    L.setTransform(s * zoom, 0, 0, s * zoom, s * CX * (1 - zoom), s * CY * (1 - zoom));
    EP.car(L, { x: CX, y: CY, r, wheels: false, opacity: 1 });
    // crop in screen space: the body starts at a crisp shoulder crease under the readouts
    L.setTransform(s, 0, 0, s, 0, 0);
    L.globalCompositeOperation = 'destination-in';
    const g = L.createLinearGradient(0, Y_CREASE - 6, 0, Y_CREASE + 6);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,1)');
    L.fillStyle = g; L.fillRect(0, 0, W, H);
    L.globalCompositeOperation = 'source-atop';       // light catching the crease, only on the body
    const g2 = L.createLinearGradient(0, Y_CREASE, 0, Y_CREASE + 220);
    g2.addColorStop(0, EP.rgba(PAL.paper, 0.13)); g2.addColorStop(1, EP.rgba(PAL.paper, 0));
    L.fillStyle = g2; L.fillRect(0, Y_CREASE, W, 220);
    L.fillStyle = EP.rgba(PAL.paper, 0.34); L.fillRect(0, Y_CREASE, W, 3);
    L.globalCompositeOperation = 'source-over';
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 0.62;
    ctx.drawImage(layer.canvas, 0, 0);
    ctx.restore();

    // road: ground line, a soft band, and irregular streaks moving at the true speed
    const band = ctx.createLinearGradient(0, yg, 0, yg + 210);
    band.addColorStop(0, EP.rgba(PAL.steel, 0.16));
    band.addColorStop(1, EP.rgba(PAL.steel, 0));
    ctx.fillStyle = band;
    ctx.fillRect(-600, yg, W + 1200, 210);
    ctx.strokeStyle = EP.rgba(PAL.steel, 0.5);
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(-600, yg + 1); ctx.lineTo(W + 600, yg + 1); ctx.stroke();

    const scroll = r * theta;                            // rolling without slipping: road moves r * angle
    const trail = 0.5 * pxPerFrame;                      // streak length grows with speed (half a picture)
    const right = CX + (W / 2) / zoom + 520;
    ctx.lineCap = 'round';
    for (const k of streaks.list) {
      let x = (k.x0 - scroll) % streaks.P; if (x < 0) x += streaks.P;
      x -= 520;                                          // window starts left of the screen
      if (x > right) continue;
      ctx.strokeStyle = EP.rgba(k.paper ? PAL.paper : PAL.steel, k.a);
      ctx.lineWidth = k.w;
      ctx.beginPath(); ctx.moveTo(x, yg + k.y); ctx.lineTo(x + k.len + trail, yg + k.y); ctx.stroke();
    }
    // contact shadow under the tyre
    ctx.save();
    ctx.translate(CX, yg); ctx.scale(1, 0.05);
    const cs = ctx.createRadialGradient(0, 0, 0, 0, 0, r * 0.9);
    cs.addColorStop(0, EP.rgba('#0B0E12', 0.85)); cs.addColorStop(1, EP.rgba('#0B0E12', 0));
    ctx.fillStyle = cs; ctx.beginPath(); ctx.arc(0, 0, r * 0.9, 0, EP.TAU); ctx.fill();
    ctx.restore();

    // the wheel: exact angle, no blur
    EP.wheel(ctx, { x: CX, y: CY, r, angle: theta });
    ctx.restore();

    // ---- readouts (screen space)
    const xs = rtl ? RIGHT : LEFT;                        // reading-start edge
    const xe = rtl ? LEFT : RIGHT;                        // the other edge
    const al = rtl ? 'right' : 'left';
    const aE = 1, aW = 1;                                 // present from the very first frame (it is the feed thumbnail)

    // speed
    text(ctx, T('s01.speed'), { x: xs, y: 526, size: 30, weight: 700, color: PAL.steel, tracking: 0.1, caps: true, opacity: aE, align: 'start' });
    group(EP, ctx, xs, 626, [
      { s: num(v, 1), tab: true, size: 104, weight: 800, color: PAL.paper, gap: 14 },
      { s: 'm/s', size: 44, weight: 600, color: PAL.steel, latin: true },
    ], al, aE);
    group(EP, ctx, xs, 684, [
      { s: num(v * 3.6, 1), tab: true, size: 46, weight: 700, color: PAL.paper, gap: 10 },
      { s: 'km/h', size: 32, weight: 600, color: PAL.steel, latin: true },
    ], al, aE);

    // real wheel speed: solid blue forward arc (what really happens)
    const bx = rtl ? LEFT : 520;                          // block start (left edge of the block)
    text(ctx, T('s01.wheel'), { x: rtl ? bx + 400 : bx, y: 526, size: 30, weight: 700, color: PAL.steel, tracking: 0.1, caps: true, opacity: aW, align: rtl ? 'right' : 'left', maxWidth: 400, shrink: true });
    turnIcon(EP, ctx, rtl ? bx + 400 - 32 : bx + 32, 590, 28, +1, { alpha: aW });
    group(EP, ctx, rtl ? bx + 400 - 84 : bx + 84, 626, [
      { s: num(fr, 2), tab: true, size: 80, weight: 800, color: PAL.paper, gap: 0 },
    ], rtl ? 'right' : 'left', aW);
    text(ctx, T('unit.turns'), { x: rtl ? bx + 400 : bx, y: 684, size: 32, weight: 600, color: PAL.steel, opacity: aW, align: rtl ? 'right' : 'left', maxWidth: 400, shrink: true });

    // honest label: this is the real thing, sampled by your own screen
    EP.badge(ctx, T('badge.real'), { x: xs, y: 1494, align: 'start', size: 26, opacity: 1 });
  },
};
