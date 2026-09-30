"""
epmotion fx: the house background (ink + faint grid), vignette, film grain, glow,
and transitions. Kept subtle: clarity over decoration.
"""

import functools

import numpy as np
import skia

from .core import W, H, col, paint


def background(canvas, grid=48, grid_alpha=0.07, offset=(0.0, 0.0), alpha=1.0):
    canvas.clear(col("ink"))
    if grid and grid_alpha > 0:
        p = paint(col("steel", grid_alpha * alpha), stroke=True, width=1.0, aa=False)
        ox, oy = offset[0] % grid, offset[1] % grid
        x = ox
        while x <= W:
            canvas.drawLine(x, 0, x, H, p)
            x += grid
        y = oy
        while y <= H:
            canvas.drawLine(0, y, W, y, p)
            y += grid


def grid_overlay(canvas, grid=48, grid_alpha=0.07, offset=(0.0, 0.0)):
    p = paint(col("steel", grid_alpha), stroke=True, width=1.0, aa=False)
    ox, oy = offset[0] % grid, offset[1] % grid
    x = ox
    while x <= W:
        canvas.drawLine(x, 0, x, H, p)
        x += grid
    y = oy
    while y <= H:
        canvas.drawLine(0, y, W, y, p)
        y += grid


def vignette(canvas, strength=0.45):
    shader = skia.GradientShader.MakeRadial(
        skia.Point(W / 2, H / 2), W * 0.75,
        [col("#000000", 0.0), col("#000000", 0.0), col("#000000", strength)],
        [0.0, 0.45, 1.0])
    canvas.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=shader))


@functools.lru_cache(maxsize=8)
def _grain_tile(seed, size=512, sigma=4.5):
    rng = np.random.default_rng(seed)
    n = rng.normal(0.0, sigma, (size, size)).astype(np.float32)
    return n


def grain(rgb, frame_index, amount=1.0):
    """Add fine, moving film grain to an RGB uint8 frame (in place); hides gradient banding."""
    tile = _grain_tile(frame_index % 6)
    th, tw = tile.shape
    reps = (int(np.ceil(rgb.shape[0] / th)), int(np.ceil(rgb.shape[1] / tw)))
    noise = np.tile(tile, reps)[:rgb.shape[0], :rgb.shape[1]] * amount
    # grain is stronger in the mid-tones and weaker in deep blacks (like film)
    lum = rgb.mean(axis=2, dtype=np.float32) / 255.0
    weight = 0.35 + 0.65 * np.clip(lum * 3.0, 0, 1)
    out = rgb.astype(np.float32) + (noise * weight)[:, :, None]
    np.clip(out, 0, 255, out=out)
    rgb[:] = out.astype(np.uint8)
    return rgb


def glow_path(canvas, path, color, radius=10.0, stroke_w=None):
    if stroke_w:
        canvas.drawPath(path, paint(color, stroke=True, width=stroke_w, blur=radius))
    else:
        canvas.drawPath(path, paint(color, blur=radius))


def logo_mark(canvas, x, y, size=44.0, alpha=0.6):
    """
    The series mark: a rounded square with the resonance peak inside
    (the same curve as the banner). Always bottom-right, same place.
    """
    import math
    s = size
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, s, s), s * 0.22, s * 0.22)
    canvas.drawRRect(rr, paint(col("paper", alpha * 0.9), stroke=True, width=max(1.5, s * 0.045)))
    pts = []
    zeta = 0.12
    for i in range(61):
        r = 2.0 * i / 60
        amp = 1.0 / math.sqrt((1 - r * r) ** 2 + (2 * zeta * r) ** 2)
        px = x + s * 0.16 + (s * 0.68) * (r / 2.0)
        py = y + s * 0.80 - (s * 0.58) * (amp / 4.3)
        pts.append((px, py))
    path = skia.Path()
    path.moveTo(*pts[0])
    for p in pts[1:]:
        path.lineTo(*p)
    canvas.drawPath(path, paint(col("paper", alpha), stroke=True, width=max(1.5, s * 0.05)))
    peak_x = x + s * 0.16 + s * 0.68 * 0.5
    canvas.drawCircle(peak_x, y + s * 0.80 - s * 0.58 * (1 / (2 * zeta) / 4.3), s * 0.075,
                      paint(col("highlight", alpha * 1.1)))


def colour_bar(canvas, y, h=8.0, alpha=1.0, progress=1.0):
    keys = ["force", "motion", "energy", "fluid", "field", "balance", "highlight"]
    w = W / len(keys)
    for i, k in enumerate(keys):
        u = max(0.0, min(1.0, progress * len(keys) - i))
        if u <= 0:
            continue
        canvas.drawRect(skia.Rect.MakeXYWH(i * w, y, w * u + 0.5, h), paint(col(k, alpha)))
