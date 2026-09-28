"""
epmotion graph: clean engineering plots that draw themselves.
"""

import numpy as np
import skia

from .core import col, paint, clamp01, smooth
from .text import Text


class Axes:
    def __init__(self, x, y, w, h, xlim, ylim):
        """Pixel box (x, y is the top-left corner) and the data ranges shown."""
        self.x, self.y, self.w, self.h = x, y, w, h
        self.xlim, self.ylim = xlim, ylim

    def px(self, xv, yv):
        u = (xv - self.xlim[0]) / (self.xlim[1] - self.xlim[0])
        v = (yv - self.ylim[0]) / (self.ylim[1] - self.ylim[0])
        return self.x + u * self.w, self.y + self.h - v * self.h

    def px_x(self, xv):
        return self.x + (xv - self.xlim[0]) / (self.xlim[1] - self.xlim[0]) * self.w

    def px_y(self, yv):
        return self.y + self.h - (yv - self.ylim[0]) / (self.ylim[1] - self.ylim[0]) * self.h

    def draw_axes(self, canvas, alpha=1.0, progress=1.0, color="steel", width=2.2, arrow=True):
        """Draw the two axis lines (with a small arrow head), growing with progress."""
        c = col(color, alpha)
        p = paint(c, stroke=True, width=width, cap="round")
        u = smooth(progress)
        x0, y0 = self.x, self.y + self.h
        canvas.drawLine(x0, y0, x0 + self.w * u, y0, p)
        canvas.drawLine(x0, y0, x0, y0 - self.h * u, p)
        if arrow and u > 0.98:
            hs = 9
            path = skia.Path()
            path.moveTo(x0 + self.w - hs, y0 - hs * 0.7)
            path.lineTo(x0 + self.w + 2, y0)
            path.lineTo(x0 + self.w - hs, y0 + hs * 0.7)
            path.moveTo(x0 - hs * 0.7, self.y + hs)
            path.lineTo(x0, self.y - 2)
            path.lineTo(x0 + hs * 0.7, self.y + hs)
            canvas.drawPath(path, paint(c, stroke=True, width=width, join="round"))

    def ticks_x(self, canvas, values, labels=None, alpha=1.0, size=22, color="steel", length=8):
        c = col(color, alpha)
        for i, v in enumerate(values):
            X = self.px_x(v)
            Y = self.y + self.h
            canvas.drawLine(X, Y, X, Y + length, paint(c, stroke=True, width=2))
            lab = labels[i] if labels else f"{v:g}"
            if lab:
                Text(lab, size, "medium").draw(canvas, X, Y + length + size + 4, c, anchor="center")

    def ticks_y(self, canvas, values, labels=None, alpha=1.0, size=22, color="steel", length=8):
        c = col(color, alpha)
        for i, v in enumerate(values):
            X = self.x
            Y = self.px_y(v)
            canvas.drawLine(X - length, Y, X, Y, paint(c, stroke=True, width=2))
            lab = labels[i] if labels else f"{v:g}"
            if lab:
                t = Text(lab, size, "medium")
                t.draw(canvas, X - length - 10, Y + t.cap_height / 2, c, anchor="right")

    def gridlines_y(self, canvas, values, alpha=0.12, color="steel"):
        p = paint(col(color, alpha), stroke=True, width=1.2)
        for v in values:
            Y = self.px_y(v)
            canvas.drawLine(self.x, Y, self.x + self.w, Y, p)

    def curve_path(self, xs, ys, x_max=None, clip_y=True):
        path = skia.Path()
        started = False
        for xv, yv in zip(xs, ys):
            if x_max is not None and xv > x_max:
                break
            if clip_y:
                yv = min(max(yv, self.ylim[0] - 0.02 * (self.ylim[1] - self.ylim[0])),
                         self.ylim[1] + 0.02 * (self.ylim[1] - self.ylim[0]))
            X, Y = self.px(xv, yv)
            if not started:
                path.moveTo(X, Y)
                started = True
            else:
                path.lineTo(X, Y)
        return path

    def plot(self, canvas, xs, ys, color="motion", width=4.0, alpha=1.0, x_max=None, glow=True, dash=None):
        path = self.curve_path(xs, ys, x_max)
        c = col(color, alpha)
        if glow:
            canvas.drawPath(path, paint(col(color, 0.45 * alpha), stroke=True, width=width * 2.6, blur=width * 1.6))
        p = paint(c, stroke=True, width=width, cap="round", join="round")
        if dash:
            p.setPathEffect(skia.DashPathEffect.Make(list(dash), 0))
        canvas.drawPath(path, p)
        return path

    def fill_under(self, canvas, xs, ys, color="motion", alpha=0.12, x_max=None):
        path = self.curve_path(xs, ys, x_max)
        if path.countPoints() < 2:
            return
        last = path.getPoint(path.countPoints() - 1)
        first = path.getPoint(0)
        path.lineTo(last.x(), self.y + self.h)
        path.lineTo(first.x(), self.y + self.h)
        path.close()
        shader = skia.GradientShader.MakeLinear([skia.Point(0, self.y), skia.Point(0, self.y + self.h)],
                                                [col(color, alpha), col(color, 0.0)])
        canvas.drawPath(path, skia.Paint(AntiAlias=True, Shader=shader))

    def dot(self, canvas, xv, yv, color="motion", r=8.0, alpha=1.0, ring=None, halo=True):
        X, Y = self.px(xv, yv)
        if halo:
            canvas.drawCircle(X, Y, r * 2.4, paint(col(color, 0.35 * alpha), blur=r * 1.2))
        canvas.drawCircle(X, Y, r, paint(col(color, alpha)))
        if ring:
            canvas.drawCircle(X, Y, r + ring, paint(col("paper", 0.9 * alpha), stroke=True, width=2.2))
        return X, Y
