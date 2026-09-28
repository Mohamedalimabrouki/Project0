"""
epmotion text: proper typography with HarfBuzz shaping (kerning, ligatures)
and Skia glyph outlines, so text stays crisp and can be animated per letter.
"""

import functools

import skia
import uharfbuzz as hb

from .core import paint

FONT_DIR = "/usr/share/fonts/opentype/inter"
FONTS = {
    "regular": f"{FONT_DIR}/Inter-Regular.otf",
    "medium": f"{FONT_DIR}/Inter-Medium.otf",
    "semibold": f"{FONT_DIR}/Inter-SemiBold.otf",
    "bold": f"{FONT_DIR}/Inter-Bold.otf",
    "light": f"{FONT_DIR}/Inter-Light.otf",
    "italic": f"{FONT_DIR}/Inter-Italic.otf",
    "display": f"{FONT_DIR}/InterDisplay-SemiBold.otf",
    "display-bold": f"{FONT_DIR}/InterDisplay-Bold.otf",
    "display-light": f"{FONT_DIR}/InterDisplay-Light.otf",
    "display-medium": f"{FONT_DIR}/InterDisplay-Medium.otf",
    "arabic": "/usr/share/fonts/truetype/ibm-plex/IBMPlexSansArabic-Medium.ttf",
}


@functools.lru_cache(maxsize=None)
def _faces(style):
    path = FONTS.get(style, style)
    blob = hb.Blob.from_file_path(path)
    face = hb.Face(blob)
    hb_font = hb.Font(face)
    upem = face.upem
    hb_font.scale = (upem, upem)
    typeface = skia.Typeface.MakeFromFile(path)
    return hb_font, upem, typeface


@functools.lru_cache(maxsize=4096)
def _glyph_path(style, glyph_id):
    _, upem, typeface = _faces(style)
    font = skia.Font(typeface, upem)
    font.setSubpixel(True)
    font.setHinting(skia.FontHinting.kNone)
    path = font.getPath(glyph_id)
    return path if path is not None else skia.Path()


class Text:
    """
    A shaped line of text.
    size: font size in pixels; tracking: extra letter spacing in pixels.
    """

    def __init__(self, text, size, style="regular", tracking=0.0, features=None, direction=None):
        self.text = text
        self.size = size
        self.style = style
        hb_font, upem, _ = _faces(style)
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        if direction:
            buf.direction = direction
        feats = {"kern": True, "liga": True, "tnum": False}
        if features:
            feats.update(features)
        hb.shape(hb_font, buf, feats)
        k = size / upem
        self.glyphs = []
        x = 0.0
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            self.glyphs.append((info.codepoint, x + pos.x_offset * k, -pos.y_offset * k, info.cluster))
            x += pos.x_advance * k + tracking
        self.width = x - tracking if self.glyphs else 0.0
        self.k = k
        ext = hb_font.get_font_extents("ltr")
        self.ascender = ext.ascender * k
        self.descender = ext.descender * k       # negative
        # cap height of Inter is about 0.727 em
        self.cap_height = 0.727 * size

    def path(self, x=0.0, y=0.0, upto=None):
        """Outline of the text with its baseline starting at (x, y)."""
        out = skia.Path()
        m = skia.Matrix()
        for i, (gid, gx, gy, _) in enumerate(self.glyphs):
            if upto is not None and i >= upto:
                break
            m.setScale(self.k, self.k)
            m.postTranslate(x + gx, y + gy)
            out.addPath(_glyph_path(self.style, gid), m)
        return out

    def draw(self, canvas, x, y, color, anchor="left", alpha_per_glyph=None, offset_per_glyph=None,
             glow=None):
        """
        Draw at baseline y. anchor: 'left', 'center' or 'right'.
        alpha_per_glyph / offset_per_glyph: optional functions i -> alpha, i -> (dx, dy)
        for letter-by-letter animations.
        glow: optional (color, blur radius) drawn underneath.
        """
        if anchor == "center":
            x -= self.width / 2
        elif anchor == "right":
            x -= self.width
        if alpha_per_glyph is None and offset_per_glyph is None:
            path = self.path(x, y)
            if glow:
                canvas.drawPath(path, paint(glow[0], blur=glow[1]))
            canvas.drawPath(path, paint(color))
            return
        base_alpha = skia.ColorGetA(color) / 255.0
        m = skia.Matrix()
        for i, (gid, gx, gy, _) in enumerate(self.glyphs):
            a = alpha_per_glyph(i) if alpha_per_glyph else 1.0
            if a <= 0.001:
                continue
            dx, dy = offset_per_glyph(i) if offset_per_glyph else (0.0, 0.0)
            m.setScale(self.k, self.k)
            m.postTranslate(x + gx + dx, y + gy + dy)
            p = skia.Path()
            p.addPath(_glyph_path(self.style, gid), m)
            c = skia.ColorSetA(color, int(255 * base_alpha * max(0.0, min(1.0, a))))
            canvas.drawPath(p, paint(c))


def text(canvas, s, x, y, size, color, style="regular", anchor="left", tracking=0.0):
    t = Text(s, size, style, tracking)
    t.draw(canvas, x, y, color, anchor)
    return t


def caps(canvas, s, x, y, size, color, style="semibold", anchor="left", tracking=None):
    """Small caps label with wide letter spacing (house style, as in the banner)."""
    tr = tracking if tracking is not None else size * 0.2
    t = Text(s.upper(), size, style, tr)
    t.draw(canvas, x, y, color, anchor)
    return t
