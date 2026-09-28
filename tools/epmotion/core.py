"""
epmotion core: frames, colours, paints and easing.

epmotion is the small 2D motion-graphics engine of Engineering Phenomena.
It draws with Skia (the same graphics library used by Chrome) into numpy
arrays, so frames can be mixed with Blender renders and sent to ffmpeg.
"""

import json
import math
import os

import numpy as np
import skia

W, H = 1920, 1080
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))

with open(os.path.join(REPO, "assets", "palette", "palette.json")) as _f:
    PALETTE = {c["key"]: c["hex"] for c in json.load(_f)["colors"]}


# ---------------------------------------------------------------- colours

def hex_rgb(hex_code):
    h = hex_code.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def col(name_or_hex, alpha=1.0):
    """Skia colour (int) from a palette key ('force') or a hex code, with alpha 0..1."""
    hex_code = PALETTE.get(name_or_hex, name_or_hex)
    r, g, b = hex_rgb(hex_code)
    return skia.ColorSetARGB(int(round(255 * max(0.0, min(1.0, alpha)))), r, g, b)


def mix_hex(a, b, t):
    ra, ga, ba = hex_rgb(PALETTE.get(a, a))
    rb, gb, bb = hex_rgb(PALETTE.get(b, b))
    t = max(0.0, min(1.0, t))
    return "#%02X%02X%02X" % (round(ra + (rb - ra) * t), round(ga + (gb - ga) * t), round(ba + (bb - ba) * t))


def paint(color, stroke=False, width=1.0, cap="round", join="round", blur=0.0, aa=True, blend=None):
    p = skia.Paint(AntiAlias=aa, Color=color)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(width)
        p.setStrokeCap({"round": skia.Paint.kRound_Cap, "butt": skia.Paint.kButt_Cap,
                        "square": skia.Paint.kSquare_Cap}[cap])
        p.setStrokeJoin({"round": skia.Paint.kRound_Join, "miter": skia.Paint.kMiter_Join,
                         "bevel": skia.Paint.kBevel_Join}[join])
    if blur > 0:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if blend == "add":
        p.setBlendMode(skia.BlendMode.kPlus)
    elif blend == "screen":
        p.setBlendMode(skia.BlendMode.kScreen)
    return p


# ---------------------------------------------------------------- frames

class Frame:
    """An RGBA frame that Skia draws into directly (numpy array, premultiplied)."""

    def __init__(self, w=W, h=H, array=None):
        self.w, self.h = w, h
        self.array = array if array is not None else np.zeros((h, w, 4), dtype=np.uint8)
        self.surface = skia.Surface(self.array)
        self.canvas = self.surface.getCanvas()

    def clear(self, color):
        self.canvas.clear(color)

    def image(self):
        return self.surface.makeImageSnapshot()

    def rgb(self):
        return self.array[:, :, :3]


def image_from_array(arr):
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)])
    return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)


def draw_image(canvas, img, x=0.0, y=0.0, alpha=1.0, scale=1.0, blur=0.0):
    p = skia.Paint(Alpha=int(255 * max(0.0, min(1.0, alpha))))
    if blur > 0:
        p.setImageFilter(skia.ImageFilters.Blur(blur, blur))
    canvas.save()
    canvas.translate(x, y)
    canvas.scale(scale, scale)
    canvas.drawImage(img, 0, 0, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kNone), p)
    canvas.restore()


# ---------------------------------------------------------------- time and easing

def clamp01(u):
    return 0.0 if u < 0 else 1.0 if u > 1 else u


def ramp(t, t0, t1):
    """0 before t0, 1 after t1, linear in between."""
    if t1 <= t0:
        return 1.0 if t >= t1 else 0.0
    return clamp01((t - t0) / (t1 - t0))


def smooth(u):
    u = clamp01(u)
    return u * u * (3 - 2 * u)


def ease_in_out(u):
    u = clamp01(u)
    return 4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2


def ease_out(u, power=3):
    u = clamp01(u)
    return 1 - (1 - u) ** power


def ease_in(u, power=3):
    u = clamp01(u)
    return u ** power


def ease_out_back(u, s=1.4):
    u = clamp01(u)
    return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2


def ease_out_expo(u):
    u = clamp01(u)
    return 1.0 if u >= 1 else 1 - 2 ** (-10 * u)


def fade(t, t_in, t_out=None, dur_in=0.4, dur_out=0.4):
    """Opacity that fades in at t_in and (optionally) out, ending at t_out."""
    a = smooth(ramp(t, t_in, t_in + dur_in))
    if t_out is not None:
        a *= 1 - smooth(ramp(t, t_out - dur_out, t_out))
    return a


def lerp(a, b, u):
    return a + (b - a) * u


def lerp2(p, q, u):
    return (p[0] + (q[0] - p[0]) * u, p[1] + (q[1] - p[1]) * u)


# ---------------------------------------------------------------- geometry helpers

def polyline_path(points, closed=False):
    path = skia.Path()
    if len(points) == 0:
        return path
    path.moveTo(*points[0])
    for p in points[1:]:
        path.lineTo(*p)
    if closed:
        path.close()
    return path


def smooth_path(points):
    """Catmull-Rom through the points, as cubic Béziers (nice smooth curves)."""
    path = skia.Path()
    pts = [tuple(p) for p in points]
    if len(pts) < 3:
        return polyline_path(pts)
    path.moveTo(*pts[0])
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        path.cubicTo(c1[0], c1[1], c2[0], c2[1], p2[0], p2[1])
    return path


def trim_path(path, u):
    """Keep the first fraction u of a path (for 'drawing on' lines)."""
    if u >= 1:
        return path
    out = skia.Path()
    if u <= 0:
        return out
    meas = skia.PathMeasure(path, False)
    total = 0.0
    lengths = []
    while True:
        L = meas.getLength()
        lengths.append(L)
        total += L
        if not meas.nextContour():
            break
    target = total * u
    meas = skia.PathMeasure(path, False)
    for L in lengths:
        if target <= 0:
            break
        seg = min(L, target)
        meas.getSegment(0, seg, out, True)
        target -= L
        if not meas.nextContour():
            break
    return out


def dashed(paint_obj, on, off, phase=0.0):
    paint_obj.setPathEffect(skia.DashPathEffect.Make([on, off], phase))
    return paint_obj
