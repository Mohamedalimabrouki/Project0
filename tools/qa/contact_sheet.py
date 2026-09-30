"""
Contact sheets: many frames of a piece on one image, to review a whole stretch of the film at a glance.

  python tools/qa/contact_sheet.py phenomena/01-resonance/scripts/render_video.py 0 30 0.5 OUT_DIR

Arguments: the piece's compositor (any Python file with render_frame(frame) -> RGB array), the start
and end time in seconds, the step in seconds, and the output folder. Writes 4 x 4 grids of labelled
thumbnails (16 moments per sheet). Look at every sheet before you encode: most visual bugs
(labels colliding, a scene fading in late, a ghost of the previous scene) jump out here.
"""

import importlib.util
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FPS = 30
FONT = os.path.join(os.environ.get("EP_FONT_DIR", "/usr/share/fonts/opentype/inter"), "Inter-Bold.otf")


def load_compositor(path):
    path = os.path.abspath(path)
    sys.path.insert(0, os.path.dirname(path))
    spec = importlib.util.spec_from_file_location("ep_compositor", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.render_frame


def main():
    render_frame = load_compositor(sys.argv[1])
    t0, t1, step = float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
    out = sys.argv[5]
    os.makedirs(out, exist_ok=True)
    times = []
    t = t0
    while t < t1:
        times.append(t)
        t += step
    try:
        font = ImageFont.truetype(FONT, 22)
    except OSError:
        font = ImageFont.load_default()
    for sheet in range(0, len(times), 16):
        im = Image.new("RGB", (1920, 1080), (0, 0, 0))
        for k, tt in enumerate(times[sheet:sheet + 16]):
            th = Image.fromarray(render_frame(int(round(tt * FPS)))).resize((480, 270), Image.LANCZOS)
            d = ImageDraw.Draw(th)
            d.rectangle([0, 0, 92, 30], fill=(0, 0, 0))
            d.text((6, 3), f"{tt:.1f} s", fill=(240, 228, 66), font=font)
            im.paste(th, ((k % 4) * 480, (k // 4) * 270))
        name = os.path.join(out, f"sheet_{t0:06.1f}_{sheet // 16}.png")
        im.save(name)
        print(name)


if __name__ == "__main__":
    main()
