"""
epmotion shapes: the house drawing vocabulary (see docs/STYLE_GUIDE.md, section 2).

Force:   thick solid arrow, filled head, vermillion
Motion:  thinner arrow, open head, blue
Plus springs, dampers (dashpots), masses, walls and ground in schematic style.
"""

import math

import numpy as np
import skia

from .core import col, paint, polyline_path, mix_hex


def _unit(dx, dy):
    L = math.hypot(dx, dy)
    return (dx / L, dy / L, L) if L > 1e-9 else (1.0, 0.0, 0.0)


def arrow_force(canvas, p0, p1, width=14.0, color=None, alpha=1.0, glow=True, head_scale=1.0):
    """Thick solid arrow with a filled head from p0 to p1 (pixels). Short arrows keep their head."""
    color = color if color is not None else col("force", alpha)
    ux, uy, L = _unit(p1[0] - p0[0], p1[1] - p0[1])
    if L < 1.0:
        return
    head_len = min(L * 0.55, width * 2.3 * head_scale)
    head_w = width * 2.5 * head_scale
    nx, ny = -uy, ux
    bx, by = p1[0] - ux * head_len, p1[1] - uy * head_len
    hw = width / 2
    pts = [
        (p0[0] + nx * hw, p0[1] + ny * hw),
        (bx + nx * hw, by + ny * hw),
        (bx + nx * head_w / 2, by + ny * head_w / 2),
        (p1[0], p1[1]),
        (bx - nx * head_w / 2, by - ny * head_w / 2),
        (bx - nx * hw, by - ny * hw),
        (p0[0] - nx * hw, p0[1] - ny * hw),
    ]
    path = polyline_path(pts, closed=True)
    if glow:
        canvas.drawPath(path, paint(skia.ColorSetA(color, int(skia.ColorGetA(color) * 0.45)), blur=width * 0.9))
    p = paint(color)
    canvas.drawPath(path, p)
    # rounded joins: a thin stroke of the same colour softens the corners
    canvas.drawPath(path, paint(color, stroke=True, width=1.6, join="round"))


def arrow_motion(canvas, p0, p1, width=6.0, color=None, alpha=1.0, glow=False, head_scale=1.0):
    """Thinner arrow with an open (chevron) head."""
    color = color if color is not None else col("motion", alpha)
    ux, uy, L = _unit(p1[0] - p0[0], p1[1] - p0[1])
    if L < 1.0:
        return
    head = min(L * 0.6, width * 3.2 * head_scale)
    nx, ny = -uy, ux
    tip = p1
    a = (tip[0] - ux * head + nx * head * 0.62, tip[1] - uy * head + ny * head * 0.62)
    b = (tip[0] - ux * head - nx * head * 0.62, tip[1] - uy * head - ny * head * 0.62)
    shaft_end = (tip[0] - ux * width * 0.4, tip[1] - uy * width * 0.4)
    path = skia.Path()
    path.moveTo(*p0)
    path.lineTo(*shaft_end)
    path.moveTo(*a)
    path.lineTo(*tip)
    path.lineTo(*b)
    if glow:
        canvas.drawPath(path, paint(skia.ColorSetA(color, int(skia.ColorGetA(color) * 0.4)),
                                    stroke=True, width=width * 2.2, blur=width))
    canvas.drawPath(path, paint(color, stroke=True, width=width, cap="round", join="round"))


def coil_spring(canvas, p0, p1, coils=10, radius=26.0, wire=4.0, color_hex=None, alpha=1.0,
                end_len=14.0, tilt=0.32, highlight=True):
    """
    A 2.5D helical spring from p0 to p1 (drawn as a helix seen slightly from the side):
    back half of each coil darker, front half brighter. Looks like a real spring and
    stretches uniformly, like a real one.
    """
    color_hex = color_hex or "#AEB6BF"
    ux, uy, L = _unit(p1[0] - p0[0], p1[1] - p0[1])
    nx, ny = -uy, ux
    a0 = (p0[0] + ux * end_len, p0[1] + uy * end_len)
    a1 = (p1[0] - ux * end_len, p1[1] - uy * end_len)
    body = max(1.0, L - 2 * end_len)
    n = max(24, int(coils * 36))
    th = np.linspace(0, 2 * np.pi * coils, n + 1)
    s = np.linspace(0, 1, n + 1)
    # axial position + a small axial offset from the tilt (ellipse seen from the side)
    ax = s * body + np.cos(th) * radius * tilt
    rad = np.sin(th) * radius
    depth = np.cos(th)          # +1 front, -1 back
    xs = a0[0] + ux * ax + nx * rad
    ys = a0[1] + uy * ax + ny * rad
    back = mix_hex(color_hex, "ink", 0.55)
    # ends (straight wire into the fittings)
    canvas.drawLine(p0[0], p0[1], xs[0], ys[0], paint(col(color_hex, alpha), stroke=True, width=wire))
    canvas.drawLine(xs[-1], ys[-1], p1[0], p1[1], paint(col(color_hex, alpha), stroke=True, width=wire))
    # draw back segments first, then front ones
    for front in (False, True):
        path = skia.Path()
        started = False
        for i in range(n):
            is_front = (depth[i] + depth[i + 1]) > 0
            if is_front != front:
                started = False
                continue
            if not started:
                path.moveTo(xs[i], ys[i])
                started = True
            path.lineTo(xs[i + 1], ys[i + 1])
        c = col(color_hex if front else back, alpha)
        canvas.drawPath(path, paint(c, stroke=True, width=wire * (1.0 if front else 0.85), cap="round"))
        if front and highlight:
            hl = col("#FFFFFF", 0.35 * alpha)
            canvas.drawPath(path, paint(hl, stroke=True, width=wire * 0.3, cap="round"))


def zigzag_spring(canvas, p0, p1, teeth=8, amp=18.0, width=3.0, color=None, end_len=16.0):
    color = color if color is not None else col("steel")
    ux, uy, L = _unit(p1[0] - p0[0], p1[1] - p0[1])
    nx, ny = -uy, ux
    pts = [p0, (p0[0] + ux * end_len, p0[1] + uy * end_len)]
    body = L - 2 * end_len
    for i in range(1, 2 * teeth):
        s = end_len + body * i / (2 * teeth)
        sgn = 1 if i % 2 else -1
        pts.append((p0[0] + ux * s + nx * amp * sgn, p0[1] + uy * s + ny * amp * sgn))
    pts += [(p1[0] - ux * end_len, p1[1] - uy * end_len), p1]
    canvas.drawPath(polyline_path(pts), paint(color, stroke=True, width=width, join="round"))


def dashpot(canvas, p0, p1, body_len=90.0, body_w=40.0, width=3.4, color_hex=None, alpha=1.0,
            fluid=True, heat=0.0, glow_hex=None):
    """
    Schematic damper: cylinder fixed at p0, piston rod attached to p1.
    fluid=True shows the oil (sky blue = fluid). heat 0..1 adds an orange glow (energy turned into heat).
    """
    color_hex = color_hex or "#AEB6BF"
    c = col(color_hex, alpha)
    ux, uy, L = _unit(p1[0] - p0[0], p1[1] - p0[1])
    nx, ny = -uy, ux
    cyl_start = 20.0
    cyl_end = cyl_start + body_len
    hw = body_w / 2

    def P(s, t):
        return (p0[0] + ux * s + nx * t, p0[1] + uy * s + ny * t)

    # connecting rod from p0 to cylinder bottom
    canvas.drawLine(*P(0, 0), *P(cyl_start, 0), paint(c, stroke=True, width=width))
    # oil
    if fluid:
        oil = polyline_path([P(cyl_start + 2, -hw + 2), P(cyl_end - 2, -hw + 2), P(cyl_end - 2, hw - 2),
                             P(cyl_start + 2, hw - 2)], closed=True)
        canvas.drawPath(oil, paint(col("fluid", 0.20 * alpha)))
    if heat > 0.001:
        glow = polyline_path([P(cyl_start, -hw), P(cyl_end, -hw), P(cyl_end, hw), P(cyl_start, hw)], closed=True)
        canvas.drawPath(glow, paint(col(glow_hex or "energy", 0.55 * heat * alpha), blur=16))
        canvas.drawPath(glow, paint(col(glow_hex or "energy", 0.35 * heat * alpha)))
    # cylinder: open towards p1
    cup = polyline_path([P(cyl_end, -hw), P(cyl_start, -hw), P(cyl_start, hw), P(cyl_end, hw)])
    canvas.drawPath(cup, paint(c, stroke=True, width=width, join="round"))
    # piston: inside the cylinder, rod goes out to p1
    piston_s = min(max(L - 46.0, cyl_start + 12), cyl_end - 6)
    canvas.drawLine(*P(piston_s, -hw + 7), *P(piston_s, hw - 7), paint(c, stroke=True, width=width * 1.5))
    canvas.drawLine(*P(piston_s, 0), *P(L, 0), paint(c, stroke=True, width=width))


def wall(canvas, x, y0, y1, color=None, hatch=14.0, side="left", width=3.0):
    """Vertical fixed support with engineering hatching."""
    color = color if color is not None else col("steel")
    canvas.drawLine(x, y0, x, y1, paint(color, stroke=True, width=width))
    sgn = -1 if side == "left" else 1
    p = paint(skia.ColorSetA(color, int(skia.ColorGetA(color) * 0.6)), stroke=True, width=1.6)
    y = y0 + 4
    while y < y1:
        canvas.drawLine(x, y, x + sgn * hatch, y + hatch, p)
        y += hatch


def ground(canvas, x0, x1, y, color=None, hatch=14.0, width=3.0):
    color = color if color is not None else col("steel")
    canvas.drawLine(x0, y, x1, y, paint(color, stroke=True, width=width))
    p = paint(skia.ColorSetA(color, int(skia.ColorGetA(color) * 0.6)), stroke=True, width=1.6)
    x = x0 + 4
    while x < x1:
        canvas.drawLine(x, y, x - hatch, y + hatch, p)
        x += hatch


def mass_block(canvas, cx, cy, w, h, label=None, alpha=1.0, radius=10.0, base_hex=None, label_size=None):
    """Steel block with a soft vertical gradient and a crisp edge."""
    base_hex = base_hex or "#8C96A0"
    rect = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(cx - w / 2, cy - h / 2, w, h), radius, radius)
    top = col(mix_hex(base_hex, "paper", 0.28), alpha)
    bot = col(mix_hex(base_hex, "ink", 0.35), alpha)
    shader = skia.GradientShader.MakeLinear([skia.Point(cx, cy - h / 2), skia.Point(cx, cy + h / 2)], [top, bot])
    p = skia.Paint(AntiAlias=True, Shader=shader)
    canvas.drawRRect(rect, paint(col("#000000", 0.35 * alpha), blur=18))
    canvas.drawRRect(rect, p)
    canvas.drawRRect(rect, paint(col(mix_hex(base_hex, "paper", 0.55), 0.8 * alpha), stroke=True, width=1.5))
    if label:
        from .text import Text
        t = Text(label, label_size or h * 0.42, "italic")
        t.draw(canvas, cx, cy + t.cap_height * 0.35, col("ink", 0.9 * alpha), anchor="center")


def dimension_line(canvas, p0, p1, label=None, color=None, offset=0.0, size=26, tick=10.0):
    """Engineering dimension: a line with end ticks and a centred label."""
    color = color if color is not None else col("steel")
    ux, uy, L = _unit(p1[0] - p0[0], p1[1] - p0[1])
    nx, ny = -uy, ux
    a = (p0[0] + nx * offset, p0[1] + ny * offset)
    b = (p1[0] + nx * offset, p1[1] + ny * offset)
    pp = paint(color, stroke=True, width=2.0)
    canvas.drawLine(*a, *b, pp)
    for q in (a, b):
        canvas.drawLine(q[0] - nx * tick, q[1] - ny * tick, q[0] + nx * tick, q[1] + ny * tick, pp)
    if label:
        from .text import Text
        t = Text(label, size, "medium")
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        pad = 10
        bg = skia.Rect.MakeXYWH(mx - t.width / 2 - pad, my - t.cap_height / 2 - pad, t.width + 2 * pad,
                                t.cap_height + 2 * pad)
        canvas.drawRRect(skia.RRect.MakeRectXY(bg, 8, 8), paint(col("ink", 0.85)))
        t.draw(canvas, mx, my + t.cap_height / 2, color, anchor="center")


def pill(canvas, x, y, w, h, fill, stroke=None, radius=None, stroke_w=1.5):
    r = radius if radius is not None else h / 2
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r)
    canvas.drawRRect(rr, paint(fill))
    if stroke is not None:
        canvas.drawRRect(rr, paint(stroke, stroke=True, width=stroke_w))
    return rr
