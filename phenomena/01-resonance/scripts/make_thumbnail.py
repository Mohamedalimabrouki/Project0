"""
Resonance - the thumbnail (1280 x 720) built from the 4K hero still.

  python make_thumbnail.py
"""

import os
import sys

import numpy as np
import skia
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sc_common import ep, fx, col, paint  # noqa: E402
import physics as P  # noqa: E402

PIECE = os.path.abspath(os.path.join(HERE, ".."))


def main():
    hero = os.path.join(PIECE, "renders", "01-resonance_hero.png")
    img = Image.open(hero).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    f = ep.Frame()
    c = f.canvas
    c.clear(col("ink"))
    # the render, pushed to the right
    ep.draw_image(c, ep.image_from_array(np.asarray(img)), 330, 0, alpha=1.0, scale=1.0)
    shader = skia.GradientShader.MakeLinear([skia.Point(0, 0), skia.Point(1150, 0)],
                                            [col("ink", 1.0), col("ink", 0.92), col("ink", 0.0)], [0.0, 0.45, 1.0])
    c.drawRect(skia.Rect.MakeWH(1920, 1080), skia.Paint(Shader=shader))
    ep.Text("ENGINEERING PHENOMENA  ·  01", 30, "semibold", 30 * 0.3).draw(c, 96, 150, col("highlight"))
    ep.Text("Resonance", 200, "display-bold", -5).draw(c, 86, 420, col("paper"))
    ep.Text("Tiny pushes.", 74, "display-semibold" if False else "display", -1).draw(c, 96, 540, col("paper"))
    ep.Text("Huge movements.", 74, "display", -1).draw(c, 96, 630, col("highlight"))
    # the resonance curve with its peak
    x0, x1, yb, hgt = 100, 760, 960, 230
    rs = np.linspace(0, 2, 400)
    amp = P.amplification(rs, 0.05)
    pts = [(x0 + (x1 - x0) * r / 2, yb - hgt * a / 10.5) for r, a in zip(rs, amp)]
    path = ep.polyline_path(pts)
    c.drawLine(x0, yb, x1, yb, paint(col("steel", 0.7), stroke=True, width=3))
    c.drawPath(path, paint(col("motion", 0.6), stroke=True, width=16, blur=10))
    c.drawPath(path, paint(col("motion"), stroke=True, width=6))
    px, py = (x0 + x1) / 2, yb - hgt * 10 / 10.5
    c.drawCircle(px, py, 13, paint(col("highlight")))
    ep.Text("× 10", 56, "display-bold").draw(c, px + 34, py + 20, col("highlight"))
    out = os.path.join(PIECE, "renders", "01-resonance_thumb.png")
    Image.fromarray(f.rgb()).resize((1280, 720), Image.LANCZOS).save(out, optimize=True)
    print("thumbnail:", out)


if __name__ == "__main__":
    main()
