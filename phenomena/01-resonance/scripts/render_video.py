"""
Resonance - the master compositor: puts every scene on the timeline and renders the film.

  python render_video.py frames 1200 1260      # render a few frames to PNG for checking
  python render_video.py video                  # render the whole picture (4 processes, FFV1 chunks)

The sound and the final MP4 are made by make_audio.py and make_final.py.
"""

import os
import sys
import time

import numpy as np
import skia

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from sc_common import W, H, S, FPS, BUILD, ep, fx, col, paint, ramp, smooth  # noqa: E402
import sc_opening as op  # noqa: E402
import sc_model as md  # noqa: E402
import sc_bridge as br  # noqa: E402
import sc_taipei as tp  # noqa: E402
import timeline as tl  # noqa: E402

TOTAL = tl.total_duration()
N_FRAMES = int(round(TOTAL * FPS))

# (name, start, end, draw function, fade-in seconds)
SCENES = [
    ("ident", 0.0, 2.6, op.draw_ident, 0.0),
    ("hook", 2.0, S["title"][0], op.draw_hook, 0.6),
    ("title", S["title"][0], S["title"][1], op.draw_title, 0.0),
    ("rhythm", S["rhythm_swing"][0], S["rhythm_swing"][1], op.draw_rhythm, 0.6),
    ("spring_hero", S["spring_hero"][0], S["spring_model"][0], md.draw_spring_hero, 0.6),
    ("spring_model", S["spring_model"][0], S["sweep"][0], md.draw_spring_model, 0.0),
    ("sweep", S["sweep"][0], S["damping"][0], md.draw_sweep, 0.0),
    ("damping", S["damping"][0], S["damping"][1], md.draw_damping, 0.0),
    ("bridge", S["bridge"][0], S["bridge"][1], br.draw_bridge, 0.0),
    ("taipei", S["taipei"][0], S["taipei"][1], tp.draw_taipei, 0.5),
    ("takeaway", S["takeaway"][0], S["takeaway"][1] + 0.5, tp.draw_takeaway, 0.0),
]

LOGO_ON = (2.6, S["takeaway"][0])


def render_frame(f):
    t = f / FPS
    frame = ep.Frame()
    c = frame.canvas
    c.clear(col("ink"))
    for name, t0, t1, fn, fin in SCENES:
        if t0 <= t < t1:
            a = smooth(ramp(t, t0, t0 + fin)) if fin > 0 else 1.0
            if a < 0.999:
                c.saveLayerAlpha(None, int(255 * a))
                fn(c, t)
                c.restore()
            else:
                fn(c, t)
    # the series mark, always bottom-right (style guide, section 9)
    la = smooth(ramp(t, LOGO_ON[0], LOGO_ON[0] + 0.6)) * (1 - smooth(ramp(t, LOGO_ON[1] - 0.6, LOGO_ON[1])))
    in_title = smooth(ramp(t, S["title"][0], S["title"][0] + 0.5)) * (1 - smooth(ramp(t, S["title"][1] - 0.5, S["title"][1])))
    la *= 1 - in_title
    if la > 0:
        fx.logo_mark(c, W - 40 - 38, H - 40 - 38, 38, alpha=0.55 * la)
    fx.vignette(c, 0.22)
    rgb = frame.rgb().copy()
    fx.grain(rgb, f, amount=0.6)
    return rgb


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "frames"
    if mode == "frames":
        from PIL import Image
        out = os.path.join(BUILD, "preview")
        os.makedirs(out, exist_ok=True)
        for a in sys.argv[2:]:
            f = int(a)
            t0 = time.time()
            Image.fromarray(render_frame(f)).save(os.path.join(out, f"frame_{f:05d}.png"))
            print(f"frame {f} ({f / FPS:.2f} s) in {time.time() - t0:.2f} s")
    elif mode == "video":
        from epmotion import video
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        end = int(sys.argv[3]) if len(sys.argv) > 3 else N_FRAMES
        workers = int(os.environ.get("EP_WORKERS", "4"))
        out = os.path.join(BUILD, "video_chunks")
        t0 = time.time()
        chunks = video.render_parallel(os.path.abspath(__file__), "render_frame", end, out, fps=FPS,
                                       workers=workers, start=start)
        print("chunks:", chunks, f"{time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
