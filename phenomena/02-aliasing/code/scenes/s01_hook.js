/*
 * Scene 01 - Hook (cold open, 18.5 s): "This car is speeding up. Now watch the wheel."
 *
 * Story
 *    0.0 -  4.8  Wide tracking shot. The whole car (tyre radius 108 px) speeds up from 0.7 to about 4.7 m/s.
 *    4.8 -  6.8  Eased push-in (a pure zoom, x2.43) onto the rear wheel (tyre radius 262 px).
 *    6.8 - 16.8  Hold. The wheel is drawn at its TRUE turning rate, so the viewer's own 30 fps screen does the
 *                aliasing: forwards, confusing (Nyquist limit 3.0 turns/s at 5.40 s), backwards and slowing,
 *                frozen at exactly 6.0 turns/s (72 degrees per picture, 11.4 to 13.4 s), then creeping forwards.
 *   13.6         Badge "Real speed: 30 pictures per second" and the note about pictures per second.
 *   16.8 - 18.5  Settle; the last 0.5 s cross-fades into the title card.
 *
 * Physics (computed, nothing is placed by eye)
 *   - f_r(t), turns per second: monotone cubic Hermite (C1) through the key values, zero slope on the holds.
 *   - theta(t) = 2 pi * integral of f_r dt, integrated ONCE in setup (EP.angleTable). Both wheels use it
 *     (the front wheel has a fixed phase offset). Nothing on the wheel breaks its 5-fold symmetry and there is
 *     no blur, so at 6.0 turns/s every picture is identical.
 *   - Rolling without slipping: distance x(t) = R theta(t), speed v = f_r C with R = 0.33 m, C = 2 pi R = 2.0735 m.
 *   - The camera follows the car. A road mark at world position X is drawn at
 *     wheel_x + (X - x(t)) * (tyre radius in px / R): the road moves at exactly v * (pixels per metre).
 *   - The far layers (skyline, hills) move at a small fraction of that (parallax) and scale less when the camera zooms.
 *
 * Drawing order: glow, far layers, road (+ a faint reflection), road marks, shadows, car body (+ light falloff
 * that keeps the caption band and the wheel clear), wheels, vignette, fade-in, speed panel, badge.
 */
const R_TYRE = 0.33;                 // tyre radius, m
const CIRC = 2 * Math.PI * R_TYRE;   // 2.0735 m
const DUR = 18.5;
const DEG = Math.PI / 180;
const TAU = Math.PI * 2;

// rotation rate keys: [t (s), turns per second]
const KEYS = [[0, 0.35], [4.5, 2.0], [6.8, 4.7], [10.2, 5.86], [11.4, 6.0], [13.4, 6.0], [16.8, 6.25], [DUR, 6.25]];

function makeRate(keys) {
  const n = keys.length, h = [], m = [];
  for (let i = 0; i < n - 1; i++) { h.push(keys[i + 1][0] - keys[i][0]); m.push((keys[i + 1][1] - keys[i][1]) / h[i]); }
  const d = new Array(n).fill(0);
  for (let i = 1; i < n - 1; i++) {
    if (m[i - 1] * m[i] <= 0) d[i] = 0;
    else {
      const w1 = 2 * h[i] + h[i - 1], w2 = h[i] + 2 * h[i - 1];
      d[i] = (w1 + w2) / (w1 / m[i - 1] + w2 / m[i]);
    }
  }
  return t => {
    if (t <= keys[0][0]) return keys[0][1];
    if (t >= keys[n - 1][0]) return keys[n - 1][1];
    let i = 0; while (t > keys[i + 1][0]) i++;
    const u = (t - keys[i][0]) / h[i], u2 = u * u, u3 = u2 * u;
    return (2 * u3 - 3 * u2 + 1) * keys[i][1] + (u3 - 2 * u2 + u) * h[i] * d[i]
      + (-2 * u3 + 3 * u2) * keys[i + 1][1] + (u3 - u2) * h[i] * d[i + 1];
  };
}

// ------------------------------------------------------------------ camera
// Wide shot: rear wheel centre (X0, Y0), tyre radius R0 (px). Close shot: (X1, Y1), R1.
// The push-in is a pure zoom about the pivot P that maps one onto the other.
const CAM = { R0: 108, X0: 722, Y0: 772, R1: 262, X1: 1210, Y1: 598, T0: 4.8, T1: 6.8 };
CAM.S = CAM.R1 / CAM.R0;
CAM.PX = (CAM.S * CAM.X0 - CAM.X1) / (CAM.S - 1);
CAM.PY = (CAM.S * CAM.Y0 - CAM.Y1) / (CAM.S - 1);

// ------------------------------------------------------------------ the car
const WB = 7.7;       // wheelbase in tyre radii (same as EP.car)
const ARCH = 1.13;    // wheel arch radius in tyre radii
const SILL = 0.52;    // underside of the body, below the axle line (tyre radii)

/** Silhouette of the car body (with the two wheel arches cut out), as a Path2D. */
function bodyPath(x, y, r) {
  const S = (u, v) => [x + u * r, y + v * r];
  const p = new Path2D();
  p.moveTo(...S(-2.40, SILL));
  p.quadraticCurveTo(...S(-2.74, SILL - 0.02), ...S(-2.77, 0.10));
  p.bezierCurveTo(...S(-2.80, -0.50), ...S(-2.81, -1.05), ...S(-2.75, -1.42));
  p.bezierCurveTo(...S(-2.71, -1.75), ...S(-2.66, -2.02), ...S(-2.58, -2.16));
  // fastback rear window and roof
  p.bezierCurveTo(...S(-2.30, -2.50), ...S(-1.55, -3.02), ...S(-0.45, -3.24));
  p.bezierCurveTo(...S(0.60, -3.42), ...S(1.50, -3.47), ...S(2.50, -3.46));
  p.bezierCurveTo(...S(3.60, -3.44), ...S(4.55, -3.05), ...S(5.55, -2.33));
  p.bezierCurveTo(...S(5.76, -2.19), ...S(6.05, -2.08), ...S(6.55, -2.04));
  p.bezierCurveTo(...S(7.55, -1.96), ...S(8.65, -1.86), ...S(9.20, -1.63));
  p.bezierCurveTo(...S(9.56, -1.48), ...S(9.73, -1.20), ...S(9.77, -0.85));
  p.bezierCurveTo(...S(9.81, -0.45), ...S(9.79, -0.10), ...S(9.68, 0.22));
  p.quadraticCurveTo(...S(9.62, SILL), ...S(9.40, SILL));
  const aa = Math.asin(SILL / ARCH), ax = Math.cos(aa) * ARCH;
  p.lineTo(...S(WB + ax, SILL));
  p.arc(x + WB * r, y, ARCH * r, aa, Math.PI - aa, true);
  p.lineTo(...S(ax, SILL));
  p.arc(x, y, ARCH * r, aa, Math.PI - aa, true);
  p.closePath();
  return p;
}

function drawCarBody(ctx, EP, x, y, r) {
  const { PAL, SHADE, rgba, mix } = EP;
  const S = (u, v) => [x + u * r, y + v * r];
  const lw = k => Math.max(1, r * k);
  const body = bodyPath(x, y, r);

  // wheel wells: dark, only above the sill line
  ctx.save();
  ctx.beginPath(); ctx.rect(x - 3 * r, y - 3 * r, 20 * r, (3 + SILL) * r); ctx.clip();
  ctx.fillStyle = SHADE.inkDeep;
  for (const cx of [x, x + WB * r]) { ctx.beginPath(); ctx.arc(cx, y, ARCH * r, 0, Math.PI * 2); ctx.fill(); }
  ctx.restore();

  // paint: vertical light-to-dark, plus a soft sheen from the top left
  const g = ctx.createLinearGradient(0, y - 3.5 * r, 0, y + SILL * r);
  g.addColorStop(0, SHADE.steelLight);
  g.addColorStop(0.26, mix(PAL.steel, PAL.paper, 0.14));
  g.addColorStop(0.56, PAL.steel);
  g.addColorStop(0.86, mix(PAL.steel, PAL.ink, 0.32));
  g.addColorStop(1, mix(PAL.steel, PAL.ink, 0.55));
  ctx.fillStyle = g;
  ctx.fill(body);

  ctx.save();
  ctx.clip(body);
  const sh = ctx.createLinearGradient(...S(-2.5, -3.2), ...S(6.5, 0.3));
  sh.addColorStop(0, rgba(PAL.paper, 0.13));
  sh.addColorStop(0.45, rgba(PAL.paper, 0.0));
  sh.addColorStop(1, rgba(PAL.ink, 0.22));
  ctx.fillStyle = sh;
  ctx.fillRect(x - 4 * r, y - 4 * r, 16 * r, 6 * r);
  // the flared arch shades the panel around it
  for (const cx of [x, x + WB * r]) {
    const ao = ctx.createRadialGradient(cx, y, ARCH * r, cx, y, (ARCH + 0.34) * r);
    ao.addColorStop(0, rgba(PAL.ink, 0.30)); ao.addColorStop(1, rgba(PAL.ink, 0));
    ctx.fillStyle = ao;
    ctx.fillRect(cx - 2 * r, y - 2 * r, 4 * r, (2 + SILL) * r);
  }

  // glass: dark, with a soft reflection and a fine light trim along the belt line
  const gl = new Path2D();
  gl.moveTo(...S(5.12, -2.30));
  gl.bezierCurveTo(...S(4.75, -2.72), ...S(4.1, -3.15), ...S(3.35, -3.25));
  gl.bezierCurveTo(...S(2.4, -3.32), ...S(1.4, -3.32), ...S(0.5, -3.24));
  gl.bezierCurveTo(...S(-0.2, -3.17), ...S(-1.2, -2.85), ...S(-2.12, -2.42));
  const belt = new Path2D();
  belt.moveTo(...S(-2.12, -2.42));
  belt.bezierCurveTo(...S(-0.5, -2.36), ...S(2.0, -2.32), ...S(5.12, -2.30));
  gl.bezierCurveTo(...S(-0.5, -2.36), ...S(2.0, -2.32), ...S(5.12, -2.30));
  gl.closePath();
  ctx.fillStyle = mix(PAL.ink, PAL.steel, 0.16);
  ctx.fill(gl);
  ctx.save();
  ctx.clip(gl);
  const rg = ctx.createLinearGradient(...S(-1.5, -3.3), ...S(3.6, -2.2));
  rg.addColorStop(0, rgba(PAL.paper, 0.20));
  rg.addColorStop(0.45, rgba(PAL.paper, 0.05));
  rg.addColorStop(1, rgba(PAL.paper, 0));
  ctx.fillStyle = rg;
  ctx.fill(gl);
  // pillars: blacked out, like the glass
  ctx.fillStyle = mix(PAL.ink, PAL.steel, 0.26);
  ctx.beginPath();
  ctx.moveTo(...S(3.52, -3.4)); ctx.lineTo(...S(3.86, -3.4)); ctx.lineTo(...S(3.92, -2.2)); ctx.lineTo(...S(3.58, -2.2)); ctx.closePath(); ctx.fill();
  ctx.beginPath();
  ctx.moveTo(...S(1.44, -3.4)); ctx.lineTo(...S(1.60, -3.4)); ctx.lineTo(...S(1.64, -2.2)); ctx.lineTo(...S(1.48, -2.2)); ctx.closePath(); ctx.fill();
  ctx.restore();
  ctx.lineCap = 'round';
  ctx.strokeStyle = rgba(PAL.ink, 0.45); ctx.lineWidth = lw(0.014); ctx.stroke(gl);
  ctx.strokeStyle = rgba(PAL.paper, 0.38); ctx.lineWidth = lw(0.016);
  ctx.save(); ctx.translate(0, r * 0.02); ctx.stroke(belt); ctx.restore();

  // shoulder line: light above, soft shade below
  const sl = new Path2D();
  sl.moveTo(...S(-2.70, -1.52)); sl.bezierCurveTo(...S(-1.2, -1.66), ...S(0.5, -1.72), ...S(2.2, -1.68));
  sl.bezierCurveTo(...S(5, -1.62), ...S(7.6, -1.60), ...S(9.3, -1.48));
  ctx.strokeStyle = rgba(PAL.ink, 0.20); ctx.lineWidth = lw(0.06);
  ctx.save(); ctx.translate(0, r * 0.05); ctx.stroke(sl); ctx.restore();
  ctx.strokeStyle = rgba(PAL.paper, 0.34); ctx.lineWidth = lw(0.028); ctx.stroke(sl);
  // lower character line between the wheels
  const cl = new Path2D();
  cl.moveTo(...S(1.80, -0.68)); cl.bezierCurveTo(...S(3.2, -0.61), ...S(4.6, -0.61), ...S(5.95, -0.68));
  ctx.strokeStyle = rgba(PAL.ink, 0.22); ctx.lineWidth = lw(0.05);
  ctx.save(); ctx.translate(0, r * 0.045); ctx.stroke(cl); ctx.restore();
  ctx.strokeStyle = rgba(PAL.paper, 0.20); ctx.lineWidth = lw(0.02); ctx.stroke(cl);

  // door cuts
  ctx.strokeStyle = rgba(PAL.ink, 0.55); ctx.lineWidth = lw(0.022);
  for (const [a, b, c, d2] of [[3.60, -2.30, 3.80, 0.55], [1.52, -2.30, 1.66, 0.55], [6.12, -2.20, 6.30, 0.55]]) {
    ctx.beginPath(); ctx.moveTo(...S(a, b)); ctx.lineTo(...S(c, d2)); ctx.stroke();
  }
  ctx.strokeStyle = rgba(PAL.paper, 0.10); ctx.lineWidth = lw(0.012);
  for (const [a, b, c, d2] of [[3.60, -2.30, 3.80, 0.55], [1.52, -2.30, 1.66, 0.55], [6.12, -2.20, 6.30, 0.55]]) {
    ctx.beginPath(); ctx.moveTo(...S(a + 0.03, b)); ctx.lineTo(...S(c + 0.03, d2)); ctx.stroke();
  }
  // handles
  for (const hx of [2.05, 4.15]) {
    ctx.fillStyle = rgba(PAL.ink, 0.5);
    EP.roundRect(ctx, ...S(hx, -1.42), 0.55 * r, 0.12 * r, 0.06 * r); ctx.fill();
    ctx.fillStyle = rgba(PAL.paper, 0.16);
    EP.roundRect(ctx, ...S(hx + 0.02, -1.42), 0.51 * r, 0.035 * r, 0.02 * r); ctx.fill();
  }

  // rocker panel: darker, with a fine light edge
  const rk = ctx.createLinearGradient(0, y + 0.0 * r, 0, y + SILL * r);
  rk.addColorStop(0, rgba(PAL.ink, 0));
  rk.addColorStop(1, rgba(PAL.ink, 0.36));
  ctx.fillStyle = rk;
  ctx.fillRect(x - 4 * r, y, 16 * r, SILL * r);
  ctx.fillStyle = rgba(PAL.paper, 0.10);
  ctx.fillRect(x - 4 * r, y + (SILL - 0.16) * r, 16 * r, lw(0.012));

  // tail lamp: dark housing with a thin light strip
  ctx.fillStyle = rgba(PAL.ink, 0.55);
  ctx.beginPath(); ctx.moveTo(...S(-2.80, -1.45)); ctx.lineTo(...S(-2.64, -2.02)); ctx.lineTo(...S(-2.28, -1.98)); ctx.lineTo(...S(-2.42, -1.62)); ctx.closePath(); ctx.fill();
  ctx.strokeStyle = rgba(PAL.paper, 0.55); ctx.lineWidth = lw(0.03);
  ctx.beginPath(); ctx.moveTo(...S(-2.70, -1.62)); ctx.lineTo(...S(-2.62, -1.88)); ctx.lineTo(...S(-2.36, -1.86)); ctx.stroke();
  // headlamp: dark housing, bright lens
  ctx.fillStyle = rgba(PAL.ink, 0.5);
  ctx.beginPath(); ctx.moveTo(...S(8.62, -1.72)); ctx.quadraticCurveTo(...S(9.45, -1.64), ...S(9.72, -1.16)); ctx.lineTo(...S(8.95, -1.24)); ctx.closePath(); ctx.fill();
  ctx.fillStyle = rgba(PAL.paper, 0.88);
  ctx.beginPath(); ctx.moveTo(...S(8.85, -1.62)); ctx.quadraticCurveTo(...S(9.4, -1.55), ...S(9.64, -1.22)); ctx.lineTo(...S(9.05, -1.30)); ctx.closePath(); ctx.fill();
  // front air intake (fine bars) and lower valance line
  ctx.fillStyle = rgba(SHADE.inkDeep, 0.62);
  EP.roundRect(ctx, ...S(8.92, -0.60), 0.78 * r, 0.26 * r, 0.09 * r); ctx.fill();
  ctx.strokeStyle = rgba(PAL.paper, 0.10); ctx.lineWidth = lw(0.012);
  for (const vy of [-0.53, -0.47, -0.41]) { ctx.beginPath(); ctx.moveTo(...S(9.0, vy)); ctx.lineTo(...S(9.62, vy)); ctx.stroke(); }
  ctx.strokeStyle = rgba(PAL.ink, 0.35); ctx.lineWidth = lw(0.016);
  ctx.beginPath(); ctx.moveTo(...S(9.25, -0.05)); ctx.lineTo(...S(9.72, -0.05)); ctx.stroke();
  // mirror
  ctx.fillStyle = SHADE.steelMid;
  EP.roundRect(ctx, ...S(4.98, -2.52), 0.5 * r, 0.28 * r, 0.09 * r); ctx.fill();
  ctx.fillStyle = rgba(PAL.paper, 0.22);
  EP.roundRect(ctx, ...S(5.03, -2.50), 0.40 * r, 0.05 * r, 0.03 * r); ctx.fill();
  ctx.restore(); // clip(body)

  // top edge light
  ctx.save();
  ctx.clip(body);
  const rim = ctx.createLinearGradient(0, y - 3.5 * r, 0, y - 1.9 * r);
  rim.addColorStop(0, rgba(PAL.paper, 0.6));
  rim.addColorStop(1, rgba(PAL.paper, 0));
  ctx.strokeStyle = rim; ctx.lineWidth = lw(0.05);
  ctx.stroke(body);
  ctx.restore();

  // arch lips
  ctx.lineWidth = lw(0.04);
  const al = ctx.createLinearGradient(x - ARCH * r, y - ARCH * r, x + ARCH * r, y);
  al.addColorStop(0, rgba(PAL.paper, 0.45)); al.addColorStop(1, rgba(PAL.paper, 0.05));
  ctx.strokeStyle = al;
  const aa = Math.asin(SILL / ARCH);
  for (const cx of [x, x + WB * r]) { ctx.beginPath(); ctx.arc(cx, y, ARCH * r, aa, Math.PI - aa, true); ctx.stroke(); }
  return body;
}

/**
 * Both wheels, drawn with the true angles (no blur). Extras that never betray the spin:
 * fine sidewall rings (circles look the same at every angle) and the arch's shadow on the tyre top.
 */
function drawWheels(ctx, EP, wx, wy, r, angles) {
  const { PAL, SHADE, rgba } = EP;
  const xs = [wx, wx + WB * r];
  xs.forEach((x, i) => EP.wheel(ctx, { x, y: wy, r, angle: angles[i] }));
  for (const x of xs) {
    ctx.save();
    ctx.lineWidth = Math.max(1, r * 0.008);
    ctx.strokeStyle = rgba(PAL.paper, 0.07);
    ctx.beginPath(); ctx.arc(x, wy, r * 0.87, 0, Math.PI * 2); ctx.stroke();
    ctx.strokeStyle = rgba(SHADE.inkDeep, 0.45);
    ctx.beginPath(); ctx.arc(x, wy, r * 0.715, 0, Math.PI * 2); ctx.stroke();
    // the light from the top left catches the shoulder of the tyre (fades out at both ends)
    {
      const a0 = -165 * DEG, span = 75 * DEG, cg = ctx.createConicGradient(a0, x, wy);
      cg.addColorStop(0, rgba(PAL.paper, 0));
      cg.addColorStop(span / TAU / 2, rgba(PAL.paper, 0.24));
      cg.addColorStop(span / TAU, rgba(PAL.paper, 0));
      cg.addColorStop(1, rgba(PAL.paper, 0));
      ctx.lineWidth = Math.max(1.5, r * 0.012);
      ctx.strokeStyle = cg;
      ctx.beginPath(); ctx.arc(x, wy, r * 0.985, a0, a0 + span); ctx.stroke();
    }
    ctx.restore();
    ctx.save();
    ctx.beginPath(); ctx.arc(x, wy, r, 0, Math.PI * 2); ctx.arc(x, wy, r * 0.70, 0, Math.PI * 2, true);
    ctx.clip('evenodd');
    const ao = ctx.createLinearGradient(0, wy - r, 0, wy - 0.2 * r);
    ao.addColorStop(0, rgba(SHADE.inkDeep, 0.5)); ao.addColorStop(1, rgba(SHADE.inkDeep, 0));
    ctx.fillStyle = ao;
    ctx.fillRect(x - r, wy - r, 2 * r, 0.9 * r);
    ctx.restore();
  }
}

// ------------------------------------------------------------------ world
/** Far skyline: thin irregular towers, in layer pixels. */
function makeSkyline(rnd, length, hMin, hMax) {
  const blocks = [];
  let x = 0;
  while (x < length) {
    const w = 16 + rnd() * 54;
    const h = hMin + Math.pow(rnd(), 1.8) * (hMax - hMin);
    blocks.push({ x, w, h });
    if (rnd() < 0.35) blocks.push({ x: x + w * 0.15, w: w * 0.6, h: h + 10 + rnd() * 34 });   // set-back top
    if (rnd() < 0.12) blocks.push({ x: x + w * 0.5 - 1.5, w: 3, h: h + 40 + rnd() * 90 });     // mast
    x += w + (rnd() < 0.3 ? 30 + rnd() * 120 : rnd() * 10);
  }
  return blocks;
}

/** Near layer: rolling hills (sum of incommensurate sines) and a few poles, in layer pixels. */
function makeHills(rnd, length) {
  const wave = [0, 1, 2].map(i => ({ lam: [640, 260, 110][i] * (0.8 + rnd() * 0.5), ph: rnd() * 6.283, amp: [34, 15, 6][i] }));
  const poles = [];
  let x = 60 + rnd() * 200;
  while (x < length) { poles.push({ x, h: 84 + rnd() * 50, arm: 26 + rnd() * 14 }); x += 260 + rnd() * 900; }
  return { wave, poles, h0: 62 };
}
const hillY = (H, x) => H.h0 + H.wave.reduce((a, w) => a + w.amp * Math.sin(x / w.lam * 6.283 + w.ph), 0);

const PPM0 = CAM.R0 / R_TYRE;   // pixels per metre in the wide shot

/** Far silhouette layers (steel, low alpha); parallax k of the road speed. */
function drawLayer(ctx, EP, layer, xc, s, W, fade) {
  const { PAL, rgba } = EP;
  const sL = Math.pow(s, layer.e);
  const groundWS = CAM.Y0 + CAM.R0;
  const base = CAM.PY + sL * (groundWS - CAM.PY);
  const scroll = layer.k * xc * PPM0;
  const toX = b => CAM.PX + sL * (b - scroll - 200 - CAM.PX);
  const p = new Path2D();
  if (layer.blocks) {
    for (const b of layer.blocks) {
      const x0 = toX(b.x), w = b.w * sL;
      if (x0 > W + 4 || x0 + w < -4) continue;
      p.rect(x0, base - b.h * sL, w, b.h * sL + 2);
    }
  } else {
    const H = layer.hills, step = 10;
    const bx0 = (0 - CAM.PX) / sL + CAM.PX + scroll + 200, bx1 = (W - CAM.PX) / sL + CAM.PX + scroll + 200;
    let first = true;
    for (let bx = Math.floor(bx0 / step) * step - step; bx <= bx1 + step; bx += step) {
      const X = toX(bx), Y = base - hillY(H, bx) * sL;
      if (first) { p.moveTo(X, base + 4); p.lineTo(X, Y); first = false; } else p.lineTo(X, Y);
    }
    p.lineTo(W + 20, base + 4); p.closePath();
    for (const pl of H.poles) {
      const X = toX(pl.x);
      if (X < -60 || X > W + 60) continue;
      const top = base - (hillY(H, pl.x) + pl.h) * sL;
      p.rect(X - 1.5 * sL, top, 3 * sL, pl.h * sL + 6);
      p.rect(X - pl.arm * sL, top + 10 * sL, 2 * pl.arm * sL, 2.6 * sL);
    }
  }
  const g = ctx.createLinearGradient(0, base - 330 * sL, 0, base);
  g.addColorStop(0, rgba(PAL.steel, layer.a * 0.4 * fade));
  g.addColorStop(1, rgba(PAL.steel, layer.a * fade));
  ctx.fillStyle = g;
  ctx.save();
  ctx.filter = `blur(${layer.blur}px)`;   // atmosphere: far things are soft
  ctx.fill(p);
  ctx.restore();
}

/**
 * Sparse road marks. They move exactly with the road:
 * screen x = wheel + (X - x_car) * (pixels per metre), pixels per metre = tyre radius (px) / 0.33 m.
 * Each mark trails a streak that grows with the speed (motion-streak look).
 */
function drawMarks(ctx, EP, st, xc, v, s, gy, W, fineK, calm) {
  const { PAL, rgba } = EP;
  const SMEAR_T = 0.05;                         // s of streak behind each mark
  const f = 1 + 0.30 * (s - 1) / (CAM.S - 1);
  for (const m of st.marks) {
    const k = m.fine ? fineK : 1;
    if (k <= 0.001) continue;
    const wsx = CAM.X0 + (m.X - xc) * PPM0;
    const x0 = CAM.PX + s * (wsx - CAM.PX);
    const L = m.len * PPM0 * s, sm = v * PPM0 * s * SMEAR_T * m.sm, tot = L + sm;
    if (x0 > W + 20 || x0 + tot < -20) continue;
    const yy = gy + (7 + 41 * m.depth) * f;
    const th = m.th * (0.65 + 0.85 * m.depth) * Math.pow(s, 0.3);
    const a = m.a * (0.6 + 0.7 * m.depth) * 1.25 * calm * k;
    const col = m.kind === 'dash' ? PAL.paper : PAL.steel;
    const g = ctx.createLinearGradient(x0, 0, x0 + tot, 0);
    g.addColorStop(0, rgba(col, a));
    g.addColorStop(Math.min(0.999, L / tot), rgba(col, a * 0.8));
    g.addColorStop(1, rgba(col, 0));
    ctx.fillStyle = g;
    EP.roundRect(ctx, x0, yy - th / 2, tot, th, th / 2);
    ctx.fill();
  }
}

function drawShadows(ctx, EP, wx, wy, r) {
  const { SHADE, rgba } = EP;
  const gy = wy + r, cx = wx + (WB / 2) * r;
  ctx.save();
  ctx.translate(0, gy); ctx.scale(1, 0.1); ctx.translate(0, -gy);
  const g = ctx.createRadialGradient(cx, gy, r * 0.5, cx, gy, r * 7.4);
  g.addColorStop(0, rgba(SHADE.inkDeep, 0.9));
  g.addColorStop(1, rgba(SHADE.inkDeep, 0));
  ctx.fillStyle = g;
  ctx.fillRect(cx - 7.4 * r, gy - 7.4 * r, 14.8 * r, 14.8 * r);
  ctx.restore();
  for (const x of [wx, wx + WB * r]) {
    ctx.save();
    ctx.translate(x, gy); ctx.scale(1, 0.09);
    const g2 = ctx.createRadialGradient(0, 0, 0, 0, 0, r * 1.5);
    g2.addColorStop(0, rgba(SHADE.inkDeep, 0.95));
    g2.addColorStop(1, rgba(SHADE.inkDeep, 0));
    ctx.fillStyle = g2;
    ctx.fillRect(-1.5 * r, -1.5 * r, 3 * r, 3 * r);
    ctx.restore();
  }
}

// ------------------------------------------------------------------ readouts
function tabWidth(ctx, EP, str, size, weight) {
  ctx.save();
  ctx.direction = 'ltr'; ctx.letterSpacing = '0px';
  ctx.font = EP.fontStr(size, weight, { latin: true });
  const cell = ctx.measureText('0').width;
  let w = 0;
  for (const c of str) w += /[0-9]/.test(c) ? cell : ctx.measureText(c).width;
  ctx.restore();
  return w;
}

/** Number in a fixed-width tabular field: missing leading digits are drawn unlit, so nothing shifts. */
function tabNumber(ctx, EP, x, y, value, digits, intDigits, size, weight) {
  const str = EP.num(value, digits);
  const pad = Math.max(0, intDigits - str.split(/[.,]/)[0].length);
  const cell = tabWidth(ctx, EP, '0', size, weight);
  if (pad) EP.textTab(ctx, '0'.repeat(pad), { x, y, size, weight, align: 'left', color: EP.rgba(EP.PAL.steel, 0.2) });
  EP.textTab(ctx, str, { x: x + pad * cell, y, size, weight, align: 'left', color: EP.PAL.paper });
}

/** The speed panel: speed in m/s and km/h, real wheel speed in turns per second. */
function drawPanel(ctx, EP, t, fr, W, rtl) {
  const { PAL, SHADE, rgba, prog, ease, T, num } = EP;
  const k = prog(t, 0.55, 1.2, ease.outCubic);
  if (k <= 0) return;
  const PW = 340, PH = 208, PAD = 20, TOP = 292;
  const edge = EP.startX(96);
  const left = rtl ? edge - PW : edge;
  const y0 = TOP + 14 * (1 - k);
  const inner0 = rtl ? left + PW - PAD : left + PAD;         // inner start edge
  const leftOf = (d, w) => (rtl ? inner0 - d - w : inner0 + d);
  const v = fr * CIRC;

  ctx.save();
  ctx.globalAlpha *= k;
  EP.roundRect(ctx, left, y0, PW, PH, 12);
  ctx.fillStyle = rgba(SHADE.inkDeep, 0.84); ctx.fill();
  ctx.lineWidth = 1.5; ctx.strokeStyle = rgba(PAL.steel, 0.30); ctx.stroke();

  const label = { size: 18, weight: 700, tracking: 0.16, caps: true, color: PAL.steel, align: 'start', maxWidth: PW - 2 * PAD, shrink: true, maxLines: 1 };
  EP.text(ctx, T('s01.speed'), { ...label, x: inner0, y: y0 + 38 });

  // speed: m/s (big), then km/h (smaller). Fixed-width numeric fields (unlit leading zero), units follow.
  const bigS = 58, kmS = 35;
  const fA = tabWidth(ctx, EP, '00.0', bigS, 600), fB = tabWidth(ctx, EP, '00', kmS, 600);
  const uA = EP.measure(ctx, 'm/s', { size: 25, weight: 500, latin: true }).w;
  const uB = EP.measure(ctx, 'km/h', { size: 20, weight: 600, latin: true }).w;
  const wA = fA + 8 + uA, wB = fB + 6 + uB, gap = 20;
  const yN = y0 + 94;
  const lA = leftOf(0, wA), lB = leftOf(wA + gap, wB);
  tabNumber(ctx, EP, lA, yN, v, 1, 2, bigS, 600);
  EP.text(ctx, 'm/s', { x: lA + fA + 8, y: yN, size: 25, weight: 500, color: PAL.steel, align: 'left', latin: true });
  tabNumber(ctx, EP, lB, yN, v * 3.6, 0, 2, kmS, 600);
  EP.text(ctx, 'km/h', { x: lB + fB + 6, y: yN, size: 20, weight: 600, color: PAL.steel, align: 'left', latin: true });

  // divider
  ctx.strokeStyle = rgba(PAL.steel, 0.28); ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(left + PAD, y0 + 118.5); ctx.lineTo(left + PW - PAD, y0 + 118.5); ctx.stroke();

  // real wheel speed: solid blue forward arrow (the truth), turns per second
  EP.text(ctx, T('s01.wheel'), { ...label, x: inner0, y: y0 + 144 });
  const icon = 28, numS = 38;
  const slotC = tabWidth(ctx, EP, '0.0', numS, 600);
  const yV = y0 + 184;
  const iL = leftOf(0, icon);
  EP.arcArrow(ctx, iL + icon / 2, yV - 13, 12, -2.5, 2.0, { kind: 'motion', width: 3.4, headSize: 10 });
  const cL = leftOf(icon + 12, slotC);
  tabNumber(ctx, EP, cL, yV, fr, 1, 1, numS, 600);
  const dU = icon + 12 + slotC + 10;
  EP.text(ctx, T('unit.turns'), {
    x: rtl ? inner0 - dU : inner0 + dU, y: yV, size: 21, weight: 500, color: PAL.steel, align: 'start',
    maxWidth: PW - 2 * PAD - dU, shrink: true, maxLines: 1,
  });
  ctx.restore();
}

/** "Real speed" badge and the note that says why the picture is not smooth: one calm row on the road. */
function drawBadge(ctx, EP, t, W, rtl) {
  const { prog, ease, T, PAL } = EP;
  const k = prog(t, 13.6, 14.2, ease.outCubic), k2 = prog(t, 13.75, 14.35, ease.outCubic);
  if (k <= 0) return;
  const yc = 902;
  // a soft dark plate keeps the streaks of the road out from behind the text
  ctx.save();
  ctx.filter = 'blur(14px)';
  ctx.globalAlpha *= k;
  ctx.fillStyle = EP.rgba(EP.PAL.ink, 0.66);
  const px0 = rtl ? W - 96 - 1120 : 96 - 30;
  ctx.fillRect(px0, yc - 30, 1150, 60);
  ctx.restore();
  const box = EP.badge(ctx, T('badge.real'), { x: EP.startX(96), y: yc + 10 * (1 - k), align: 'start', opacity: k });
  const nx = rtl ? box.x - 22 : box.x + box.w + 22;
  EP.text(ctx, T('s01.fps'), {
    x: nx, y: yc + 10 * (1 - k2), anchor: 'middle', size: 24, weight: 500, color: PAL.paper, opacity: 0.86 * k2, align: 'start',
    maxWidth: 700, shrink: true, maxLines: 1, shadow: 10,
  });
}

let ST = null;

export default {
  duration: DUR,
  captions: [
    { key: 's01.c1', in: 0.8, out: 4.6 },
    { key: 's01.c2', in: 5.0, out: 7.0 },
    { key: 's01.c3', in: 7.4, out: 10.2 },
    { key: 's01.c4', in: 10.6, out: 13.2 },
    { key: 's01.c5', in: 13.6, out: 17.6 },
  ],
  cues: [
    { t: 0.2, sfx: 'car', dur: 17.8 },
    { t: 4.9, sfx: 'whoosh', dur: 1.8 },
    { t: 7.4, sfx: 'glitch' },
    { t: 11.4, sfx: 'shimmer', dur: 2 },
    { t: 17.6, sfx: 'swoosh_rev', dur: 0.9 },
  ],
  math: [],
  music: 'hook',
  // the series mark fades in with the picture and is gone before the title card takes over
  hideLogo: t => (t < 1.2 ? 1 - Math.max(0, (t - 0.4) / 0.8) : t > 17.2 ? Math.min(1, (t - 17.2) / 0.6) : 0),

  setup(EP, info = {}) {
    // Right-to-left: the speed panel sits on the right, so the close-up wheel moves a little left to stay clear of it.
    CAM.X1 = info.rtl ? 1170 : 1210;
    CAM.PX = (CAM.S * CAM.X0 - CAM.X1) / (CAM.S - 1);

    const rate = makeRate(KEYS);
    const spin = EP.angleTable(rate, 0, DUR);
    const dist = R_TYRE * spin(DUR);            // metres driven in the whole scene

    // fixed wheel phase: at t = 12 s (frozen) one spoke sits at 10 degrees from the vertical
    const a12 = spin(12), per = 72 * DEG;
    const wrapTo = (x, p) => x - p * Math.floor(x / p);
    const phaseRear = 10 * DEG - wrapTo(a12, per);
    const phaseFront = phaseRear + 0.43 * per;

    // sparse, irregular road marks (deterministic). Two families: coarse marks (always on)
    // and fine flecks that appear with the push-in (they are only visible up close).
    const rnd = EP.rng(20260929);
    const marks = [];
    let X = -8;
    while (X < dist + 16) {
      X += 0.30 + rnd() * 1.5;
      const seam = rnd() < 0.4;
      marks.push({
        X, kind: seam ? 'seam' : 'dash', fine: false,
        len: seam ? 0.20 + rnd() * 0.45 : 0.04 + rnd() * 0.10,
        depth: rnd(), sm: 0.8 + rnd() * 0.6,
        th: seam ? 1.6 + rnd() * 1.2 : 2.8 + rnd() * 2.4,
        a: seam ? 0.20 + rnd() * 0.12 : 0.34 + rnd() * 0.22,
      });
    }
    X = -8;
    while (X < dist + 16) {
      X += 0.10 + rnd() * 0.5;
      marks.push({ X, kind: 'seam', fine: true, len: 0.03 + rnd() * 0.08, depth: rnd(), sm: 0.8 + rnd() * 0.9, th: 1.4 + rnd() * 1.0, a: 0.16 + rnd() * 0.12 });
    }

    X = -8;                                      // soft, wide streaks of the nearest road: only felt at speed
    while (X < dist + 16) {
      X += 0.45 + rnd() * 1.5;
      marks.push({ X, kind: 'haze', fine: true, len: 0.2 + rnd() * 0.5, depth: 0.5 + rnd() * 0.5, sm: 1.2 + rnd() * 0.8, th: 4 + rnd() * 4, a: 0.05 + rnd() * 0.05 });
    }

    const farLen = 5200, nearLen = 7000;
    const layers = [
      { k: 0.030, e: 0.30, a: 0.07, blur: 1.6, blocks: makeSkyline(EP.rng(11), farLen, 60, 230) },
      { k: 0.085, e: 0.45, a: 0.11, blur: 1.0, hills: makeHills(EP.rng(23), nearLen) },
    ];
    ST = { rate, spin, dist, phaseRear, phaseFront, marks, layers };
  },

  render(ctx, t, EP, { W, H, rtl }) {
    const { PAL, SHADE, rgba, mix, prog, ease } = EP;
    const st = ST;
    EP.bg(ctx, W, H);

    const fr = st.rate(t), th = st.spin(t), xc = R_TYRE * th, v = fr * CIRC;
    const u = prog(t, CAM.T0, CAM.T1, ease.smooth);
    const s = Math.pow(CAM.S, u);
    const [wx, wy] = [CAM.PX + s * (CAM.X0 - CAM.PX), CAM.PY + s * (CAM.Y0 - CAM.PY)];
    const r = CAM.R0 * s, gy = wy + r;
    const settle = prog(t, 16.8, 18.3, ease.inOutSine);

    // soft glow behind the car, horizon haze, far silhouettes
    const gc = [wx + 3.4 * r, gy - 2.2 * r];
    const glow = ctx.createRadialGradient(gc[0], gc[1], 0, gc[0], gc[1], 9 * r);
    glow.addColorStop(0, rgba(PAL.steel, 0.085));
    glow.addColorStop(1, rgba(PAL.steel, 0));
    ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);
    const hz = ctx.createLinearGradient(0, gy - 2.4 * r, 0, gy);
    hz.addColorStop(0, rgba(PAL.steel, 0));
    hz.addColorStop(1, rgba(PAL.steel, 0.05));
    ctx.fillStyle = hz; ctx.fillRect(0, gy - 2.4 * r, W, 2.4 * r);
    for (const L of st.layers) drawLayer(ctx, EP, L, xc, s, W, 1 - 0.55 * u);

    // the road (dark, slightly wet: the car is reflected a little way into it)
    const roadTop = mix(PAL.ink, PAL.steel, 0.105), roadMid = mix(PAL.ink, PAL.steel, 0.055);
    const rd = ctx.createLinearGradient(0, gy, 0, H);
    rd.addColorStop(0, roadTop);
    rd.addColorStop(0.3, roadMid);
    rd.addColorStop(1, SHADE.inkDeep);
    ctx.fillStyle = rd;
    ctx.fillRect(0, gy, W, H - gy);
    const angles = [th + st.phaseRear, th + st.phaseFront];
    {
      const Hr = Math.min(0.62 * r, 84);
      ctx.save();
      ctx.beginPath(); ctx.rect(0, gy, W, Hr); ctx.clip();
      ctx.globalAlpha = 0.5;
      ctx.translate(0, 2 * gy); ctx.scale(1, -1);
      drawCarBody(ctx, EP, wx, wy, r);
      drawWheels(ctx, EP, wx, wy, r, angles);
      ctx.restore();
      const roadAt = y => { const k = (y - gy) / (H - gy); return k < 0.3 ? mix(roadTop, roadMid, k / 0.3) : mix(roadMid, SHADE.inkDeep, (k - 0.3) / 0.7); };
      const fg = ctx.createLinearGradient(0, gy, 0, gy + Hr);
      for (const [k, a] of [[0, 0.2], [0.3, 0.5], [0.6, 0.85], [0.8, 1], [1, 1]]) fg.addColorStop(k, rgba(roadAt(gy + k * Hr), a));
      ctx.fillStyle = fg;
      ctx.fillRect(0, gy, W, Hr + 1);
    }
    ctx.fillStyle = rgba(PAL.steel, 0.24);
    ctx.fillRect(0, gy - 0.5, W, 1.5);
    drawMarks(ctx, EP, st, xc, v, s, gy, W, u, 1 - 0.4 * settle);
    drawShadows(ctx, EP, wx, wy, r);

    // the car: body, then light falloff so the wheel and the caption band stay clear
    const body = drawCarBody(ctx, EP, wx, wy, r);
    ctx.save();
    ctx.clip(body);
    ctx.fillStyle = rgba(PAL.ink, 0.26 * u);
    ctx.fillRect(0, 0, W, H);
    const fo = ctx.createRadialGradient(wx, wy, r * 1.25, wx, wy, r * 1.25 + 860);
    fo.addColorStop(0, rgba(PAL.ink, 0));
    fo.addColorStop(1, rgba(PAL.ink, 0.55 * u));
    ctx.fillStyle = fo;
    ctx.fillRect(0, 0, W, H);
    const tf = ctx.createLinearGradient(0, 0, 0, 400);
    tf.addColorStop(0, rgba(PAL.ink, 0.97));
    tf.addColorStop(0.5, rgba(PAL.ink, 0.9));
    tf.addColorStop(0.72, rgba(PAL.ink, 0.55));
    tf.addColorStop(1, rgba(PAL.ink, 0));
    ctx.fillStyle = tf;
    ctx.fillRect(0, 0, W, 400);
    ctx.restore();
    drawWheels(ctx, EP, wx, wy, r, angles);

    // a soft vignette keeps the eye on the wheel
    const vg = ctx.createRadialGradient(W * 0.56, H * 0.52, H * 0.42, W * 0.5, H * 0.5, Math.hypot(W, H) * 0.56);
    vg.addColorStop(0, rgba(SHADE.inkDeep, 0));
    vg.addColorStop(1, rgba(SHADE.inkDeep, 0.4));
    ctx.fillStyle = vg; ctx.fillRect(0, 0, W, H);

    // open from black
    const kIn = prog(t, 0, 0.9, ease.inOutSine);
    if (kIn < 1) { ctx.fillStyle = rgba(PAL.ink, 1 - kIn); ctx.fillRect(0, 0, W, H); }

    drawPanel(ctx, EP, t, fr, W, rtl);
    drawBadge(ctx, EP, t, W, rtl);
  },
};
