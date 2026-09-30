"""
Resonance - shared context for the 2D scenes: timing, physics data, 3D frames,
and small drawing helpers used by several scenes.
"""

import functools
import json
import math
import os
import sys

import numpy as np
import skia
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools"))
sys.path.insert(0, HERE)

import epmotion as ep  # noqa: E402
from epmotion import fx, shapes as sh  # noqa: E402
from epmotion.graph import Axes  # noqa: E402
import physics as P  # noqa: E402
import timeline as tl  # noqa: E402

W, H = ep.W, ep.H
FPS = tl.FPS
T = tl.line_times()
S = tl.scenes(T)
BUILD = tl.BUILD
FRAMES = os.path.join(BUILD, "frames")
DATA = os.path.join(BUILD, "data")

col = ep.col
paint = ep.paint
ramp, smooth, fade = ep.ramp, ep.smooth, ep.fade
ease_out, ease_in_out, ease_out_back = ep.ease_out, ep.ease_in_out, ep.ease_out_back


@functools.lru_cache(maxsize=None)
def at(line_id, phrase=None):
    """Start time of a line, or of a phrase inside it (global seconds)."""
    if phrase is None:
        return T[line_id][0]
    return tl.phrase_time(line_id, phrase, T)


def end(line_id):
    return T[line_id][1]


# ------------------------------------------------------------------ 3D frames

@functools.lru_cache(maxsize=8)
def points(shot):
    path = os.path.join(FRAMES, shot, f"{shot}_points.json")
    with open(path) as f:
        raw = json.load(f)
    return {int(k): v for k, v in raw.items()}


def pt(shot, fi, name):
    pts = points(shot)
    fi = max(min(fi, max(pts)), min(pts))
    x, y, _ = pts[fi][name]
    return (x, y)


@functools.lru_cache(maxsize=6)
def _frame_image(shot, fi):
    path = os.path.join(FRAMES, shot, f"{shot}_{fi:04d}.png")
    if not os.path.exists(path):
        # while renders are still running, fall back to the closest existing frame
        d = os.path.join(FRAMES, shot)
        have = sorted(int(n.split("_")[-1][:4]) for n in os.listdir(d) if n.endswith(".png")) if os.path.isdir(d) else []
        if not have:
            return None
        fi = min(have, key=lambda k: abs(k - fi))
        path = os.path.join(FRAMES, shot, f"{shot}_{fi:04d}.png")
    arr = np.asarray(Image.open(path).convert("RGB"))
    return ep.image_from_array(arr)


def frame_count(shot):
    return {"hook": 640, "rhythm": 400, "spring": 250, "taipei": 250}[shot]


def draw_render(c, shot, local_t, alpha=1.0, blur=0.0, scale=1.0, dim=0.0):
    fi = int(round(local_t * FPS))
    fi = max(0, min(frame_count(shot) - 1, fi))
    img = _frame_image(shot, fi)
    if img is None:
        c.drawRect(skia.Rect.MakeWH(W, H), paint(col("#1d232b", alpha)))
        return fi
    if scale != 1.0:
        c.save()
        c.translate(W / 2, H / 2)
        c.scale(scale, scale)
        c.translate(-W / 2, -H / 2)
    ep.draw_image(c, img, 0, 0, alpha=alpha, blur=blur)
    if scale != 1.0:
        c.restore()
    if dim > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint(col("ink", dim * alpha)))
    return fi


# ------------------------------------------------------------------ physics data

@functools.lru_cache(maxsize=1)
def swings():
    d = P.swing_data(DATA)
    d["rhythm_work"] = P.push_work(d["t"], d["rhythm_omega"], d["rhythm_pushes"])
    d["random_work"] = P.push_work(d["t"], d["random_omega"], d["random_pushes"])
    return d


@functools.lru_cache(maxsize=1)
def pull():
    return P.pull_data(DATA)


# ------------------------------------------------------------------ drawing helpers

def label_box(c, x, y, text, size=24, color="paper", bg_alpha=0.78, style="medium", anchor="left",
              alpha=1.0, pad=12):
    """Text on a soft ink plate, so labels read on top of 3D renders."""
    t = ep.Text(text, size, style)
    w = t.width + 2 * pad
    h = t.cap_height + 2 * pad
    if anchor == "center":
        x0 = x - w / 2
    elif anchor == "right":
        x0 = x - w
    else:
        x0 = x
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x0, y - h / 2, w, h), 10, 10)
    c.drawRRect(rr, paint(col("ink", bg_alpha * alpha)))
    c.drawRRect(rr, paint(col("steel", 0.25 * alpha), stroke=True, width=1.2))
    t.draw(c, x0 + pad, y + t.cap_height / 2, col(color, alpha))
    return skia.Rect.MakeXYWH(x0, y - h / 2, w, h)


def tex_box(c, x, y, tex, alpha=1.0, pad=16, anchor="left", bg_alpha=0.78, progress=1.0, color="paper"):
    r = tex.box(x, y, anchor)
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(r.left() - pad, r.top() - pad, r.right() + pad,
                                                  r.bottom() + pad), 12, 12)
    c.drawRRect(rr, paint(col("ink", bg_alpha * alpha)))
    c.drawRRect(rr, paint(col("steel", 0.25 * alpha), stroke=True, width=1.2))
    tex.draw(c, x, y, col(color, alpha), anchor=anchor, progress=progress)
    return rr


def leader(c, p_from, p_to, alpha=1.0, color="paper", dot=True):
    c.drawLine(p_from[0], p_from[1], p_to[0], p_to[1], paint(col(color, 0.7 * alpha), stroke=True, width=1.6))
    if dot:
        c.drawCircle(p_from[0], p_from[1], 4.5, paint(col(color, alpha)))


def caption(c, text, x, y, size=22, color="steel", alpha=1.0, anchor="left", tracking=None):
    t = ep.Text(text.upper(), size, "semibold", tracking if tracking is not None else size * 0.18)
    t.draw(c, x, y, col(color, alpha), anchor=anchor)
    return t


def note(c, text, x, y, size=22, color="steel", alpha=1.0, anchor="left", style="regular"):
    t = ep.Text(text, size, style)
    t.draw(c, x, y, col(color, alpha), anchor=anchor)
    return t


def bottom_gradient(c, y0=700, alpha=0.85):
    shader = skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, H)],
                                            [col("ink", 0.0), col("ink", alpha)])
    c.drawRect(skia.Rect.MakeLTRB(0, y0, W, H), skia.Paint(Shader=shader))


def top_gradient(c, y1=260, alpha=0.8):
    shader = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(0, y1)],
                                            [col("ink", alpha), col("ink", 0.0)])
    c.drawRect(skia.Rect.MakeLTRB(0, 0, W, y1), skia.Paint(Shader=shader))


def exaggeration_tag(c, text, x, y, alpha=1.0, anchor="left"):
    """House rule: every exaggeration is labelled on screen."""
    return label_box(c, x, y, text, size=19, color="highlight", bg_alpha=0.7, style="semibold",
                     anchor=anchor, alpha=alpha, pad=9)


def unit(v):
    L = math.hypot(v[0], v[1])
    return (v[0] / L, v[1] / L) if L > 1e-9 else (1.0, 0.0)
