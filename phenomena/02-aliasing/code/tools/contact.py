"""Contact sheet: many frames on one image, each labelled, for a quick visual check.

Usage: python3 contact.py frames.json out.png [columns]
frames.json is a list of {"file": path, "label": text}.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

items = json.load(open(sys.argv[1]))
out = sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 4
if not items:
    sys.exit("no frames")

first = Image.open(items[0]["file"])
w0, h0 = first.size
tw = 640 if w0 >= h0 else 360
th = round(tw * h0 / w0)
pad, lab = 8, 26
rows = (len(items) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + lab + pad) + pad), (40, 44, 52))
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("DejaVuSans.ttf", 16)
except OSError:
    font = ImageFont.load_default()
for i, it in enumerate(items):
    r, c = divmod(i, cols)
    x, y = pad + c * (tw + pad), pad + r * (th + lab + pad)
    im = Image.open(it["file"]).convert("RGB").resize((tw, th), Image.LANCZOS)
    sheet.paste(im, (x, y + lab))
    draw.text((x + 2, y + 4), it["label"], fill=(230, 230, 230), font=font)
sheet.save(out)
