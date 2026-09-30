# epmotion

The small 2D motion graphics engine of Engineering Phenomena. It draws with
[Skia](https://skia.org/) (the graphics library inside Chrome) into numpy
arrays, so its frames can be laid over Blender renders and sent to ffmpeg.

| File | What it gives you |
|---|---|
| `core.py` | Frames, the house palette (read from `assets/palette/palette.json`), paints, easing curves, path helpers |
| `text.py` | Real typography: HarfBuzz shaping (kerning, ligatures) with Inter, letter-by-letter animation, small caps labels |
| `tex.py` | Real LaTeX equations as vector outlines (TeX Live + dvisvgm), colours by meaning (`\cf{}` force, `\cm{}` motion...), write-on animation |
| `shapes.py` | The house vocabulary: force arrows (thick, filled head), motion arrows (thin, open head), coil and zigzag springs, dampers, steel blocks, walls and ground, dimension lines |
| `graph.py` | Axes, ticks and curves that draw themselves |
| `fx.py` | Background (ink + faint grid), vignette, film grain, the logo mark, the colour bar |
| `video.py` | Parallel rendering into lossless chunks, and the final H.264 encode |

Example:

```python
import epmotion as ep
from epmotion import fx, shapes as sh

f = ep.Frame()
fx.background(f.canvas)
ep.Tex(r"\omega_n = \sqrt{k/m}", 64).draw(f.canvas, 200, 300, ep.col("paper"))
sh.arrow_force(f.canvas, (200, 500), (420, 500))      # vermillion = force
```

Needs: `pip install skia-python uharfbuzz svgelements numpy`, and TeX Live (`latex`, `dvisvgm`) for equations.
