"""
epmotion tex: real LaTeX equations turned into vector outlines.

LaTeX -> DVI -> SVG (dvisvgm, glyphs as paths) -> Skia paths.
Colours set in LaTeX with \\textcolor[HTML]{D55E00}{...} are kept, so
an equation can colour F in vermillion (force) and x in blue (motion).
Needs: latex, dvisvgm (TeX Live), and the Python package svgelements.
"""

import hashlib
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import skia
import svgelements

from .core import paint, clamp01, smooth

CACHE = os.environ.get("EP_TEX_CACHE", os.path.join(tempfile.gettempdir(), "epmotion_tex"))

PREAMBLE = r"""
\documentclass[preview,border=2pt]{standalone}
\usepackage{amsmath,amssymb}
\usepackage{xcolor}
\newcommand{\cf}[1]{\textcolor[HTML]{D55E00}{#1}}
\newcommand{\cm}[1]{\textcolor[HTML]{0072B2}{#1}}
\newcommand{\ce}[1]{\textcolor[HTML]{E69F00}{#1}}
\newcommand{\cb}[1]{\textcolor[HTML]{009E73}{#1}}
\newcommand{\ch}[1]{\textcolor[HTML]{F0E442}{#1}}
\newcommand{\cs}[1]{\textcolor[HTML]{8C96A0}{#1}}
\newcommand{\cl}[1]{\textcolor[HTML]{56B4E9}{#1}}
\newcommand{\unit}[1]{\,\mathrm{#1}}
"""

XLINK = "{http://www.w3.org/1999/xlink}href"
SVGNS = "{http://www.w3.org/2000/svg}"


def _compile(latex, math=True):
    body = f"${latex}$" if math else latex
    src = PREAMBLE + "\\begin{document}\n" + body + "\n\\end{document}\n"
    key = hashlib.sha1(src.encode()).hexdigest()[:16]
    os.makedirs(CACHE, exist_ok=True)
    svg_path = os.path.join(CACHE, key + ".svg")
    if os.path.exists(svg_path):
        return svg_path
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "eq.tex"), "w") as f:
            f.write(src)
        r = subprocess.run(["latex", "-interaction=nonstopmode", "-halt-on-error", "eq.tex"],
                           cwd=d, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"LaTeX failed for {latex!r}:\n{r.stdout[-1500:]}")
        r = subprocess.run(["dvisvgm", "--no-fonts", "--exact-bbox", "-o", svg_path, "eq.dvi"],
                           cwd=d, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"dvisvgm failed: {r.stderr[-800:]}")
    return svg_path


def _svg_path_to_skia(d, matrix):
    path = skia.Path()
    for seg in svgelements.Path(d):
        if isinstance(seg, svgelements.Move):
            p = matrix.mapXY(seg.end.x, seg.end.y)
            path.moveTo(p.x(), p.y())
        elif isinstance(seg, svgelements.Line):
            p = matrix.mapXY(seg.end.x, seg.end.y)
            path.lineTo(p.x(), p.y())
        elif isinstance(seg, svgelements.CubicBezier):
            a = matrix.mapXY(seg.control1.x, seg.control1.y)
            b = matrix.mapXY(seg.control2.x, seg.control2.y)
            c = matrix.mapXY(seg.end.x, seg.end.y)
            path.cubicTo(a.x(), a.y(), b.x(), b.y(), c.x(), c.y())
        elif isinstance(seg, svgelements.QuadraticBezier):
            a = matrix.mapXY(seg.control.x, seg.control.y)
            c = matrix.mapXY(seg.end.x, seg.end.y)
            path.quadTo(a.x(), a.y(), c.x(), c.y())
        elif isinstance(seg, svgelements.Arc):
            for cub in seg.as_cubic_curves():
                a = matrix.mapXY(cub.control1.x, cub.control1.y)
                b = matrix.mapXY(cub.control2.x, cub.control2.y)
                c = matrix.mapXY(cub.end.x, cub.end.y)
                path.cubicTo(a.x(), a.y(), b.x(), b.y(), c.x(), c.y())
        elif isinstance(seg, svgelements.Close):
            path.close()
    return path


def _parse_transform(s):
    m = skia.Matrix()
    if not s:
        return m
    for name, args in re.findall(r"(\w+)\(([^)]*)\)", s):
        v = [float(a) for a in re.split(r"[ ,]+", args.strip()) if a]
        t = skia.Matrix()
        if name == "translate":
            t.setTranslate(v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            t.setScale(v[0], v[1] if len(v) > 1 else v[0])
        elif name == "matrix":
            t.setAll(v[0], v[2], v[4], v[1], v[3], v[5], 0, 0, 1)
        elif name == "rotate":
            t.setRotate(v[0])
        m.preConcat(t)
    return m


class Tex:
    """
    A LaTeX formula as outlines. size = the pixel size of 10 pt text
    (so size=48 gives letters about as big as 48 px Inter).
    Baseline of the formula is at y=0 before placement.
    """

    def __init__(self, latex, size=48.0, math=True):
        self.latex = latex
        self.size = size
        svg = _compile(latex, math)
        tree = ET.parse(svg)
        root = tree.getroot()
        defs = {}
        for el in root.iter(SVGNS + "path"):
            if el.get("id"):
                defs[el.get("id")] = el.get("d")
        k = size / 10.0
        self.items = []    # (skia.Path, fill hex or None, x-order key)
        base = skia.Matrix()
        base.setScale(k, k)

        def walk(el, matrix, fill):
            tr = _parse_transform(el.get("transform"))
            m = skia.Matrix.Concat(matrix, skia.Matrix())
            m.preConcat(tr)
            fill = el.get("fill", fill)
            tag = el.tag.replace(SVGNS, "")
            if tag == "use":
                ref = el.get(XLINK) or el.get("href")
                d = defs.get(ref.lstrip("#")) if ref else None
                if d:
                    mm = skia.Matrix.Concat(m, skia.Matrix())
                    t = skia.Matrix()
                    t.setTranslate(float(el.get("x", 0)), float(el.get("y", 0)))
                    mm.preConcat(t)
                    self.items.append([_svg_path_to_skia(d, mm), fill])
            elif tag == "rect":
                x, y = float(el.get("x", 0)), float(el.get("y", 0))
                w, h = float(el.get("width", 0)), float(el.get("height", 0))
                p = skia.Path()
                p.addRect(skia.Rect.MakeXYWH(x, y, w, h))
                p.transform(m)
                self.items.append([p, fill])
            elif tag == "path" and not el.get("id") and el.get("d"):
                self.items.append([_svg_path_to_skia(el.get("d"), m), fill])
            elif tag == "line":
                p = skia.Path()
                p.moveTo(float(el.get("x1")), float(el.get("y1")))
                p.lineTo(float(el.get("x2")), float(el.get("y2")))
                sw = float(el.get("stroke-width", 0.4))
                stroked = skia.Path()
                pp = paint(0, stroke=True, width=sw, cap="butt")
                pp.getFillPath(p, stroked)
                stroked.transform(m)
                self.items.append([stroked, el.get("stroke", fill)])
            for child in el:
                if child.tag.replace(SVGNS, "") != "defs":
                    walk(child, m, fill)

        for child in root:
            if child.tag.replace(SVGNS, "") != "defs":
                walk(child, base, None)
        bounds = skia.Rect.MakeEmpty()
        for p, _ in self.items:
            b = p.computeTightBounds()
            bounds.join(b)
        self.bounds = bounds
        self.width = bounds.width()
        self.height = bounds.height()
        # reveal order: left to right
        self.items.sort(key=lambda it: it[0].computeTightBounds().left())

    def draw(self, canvas, x, y, color, anchor="left", progress=1.0, weight=0.35, alpha=1.0,
             glow=None, color_override=None):
        """
        Draw with the baseline-left of the formula at (x, y).
        anchor 'center' centres horizontally on x; 'right' aligns the right edge.
        progress < 1 writes the formula on, glyph by glyph (with a soft fade).
        weight: extra stroke (px) that makes the thin Computer Modern strokes read on video.
        """
        if anchor == "center":
            x -= self.bounds.left() + self.width / 2
        elif anchor == "right":
            x -= self.bounds.right()
        else:
            x -= self.bounds.left()
        n = len(self.items)
        canvas.save()
        canvas.translate(x, y)
        for i, (p, fill) in enumerate(self.items):
            if progress >= 1:
                a = 1.0
            else:
                a = smooth(clamp01(progress * (n + 3) - i) / 3.0 * 3.0 / 3.0)
                a = clamp01(progress * (n + 2.5) - i) if progress > 0 else 0.0
                a = smooth(a)
            if a <= 0:
                continue
            c = color
            if fill and fill.lower() not in ("#000", "#000000", "black") and color_override is None:
                from .core import col
                c = col(fill)
            elif color_override is not None:
                c = color_override
            final_alpha = alpha * a * skia.ColorGetA(c) / 255.0
            cc = skia.ColorSetA(c, int(255 * clamp01(final_alpha)))
            if glow:
                canvas.drawPath(p, paint(skia.ColorSetA(glow[0], int(skia.ColorGetA(glow[0]) * a * alpha)),
                                         blur=glow[1]))
            canvas.drawPath(p, paint(cc))
            if weight > 0:
                canvas.drawPath(p, paint(cc, stroke=True, width=weight))
        canvas.restore()
        return self

    def box(self, x, y, anchor="left"):
        """Screen rectangle of the formula when drawn at (x, y)."""
        if anchor == "center":
            x -= self.bounds.left() + self.width / 2
        elif anchor == "right":
            x -= self.bounds.right()
        else:
            x -= self.bounds.left()
        return skia.Rect.MakeXYWH(x + self.bounds.left(), y + self.bounds.top(), self.width, self.height)
