"""Independent physics check: a wheel that should look frozen must give
identical pixels from one frame to the next inside its box.

Usage: python3 qa/frozen_check.py frames_dir first_frame last_frame x0 y0 x1 y1
Prints the largest pixel change between consecutive frames in the box
(0 = perfectly frozen; a few units = anti-aliasing noise only).
"""
import sys

import numpy as np
from PIL import Image

d, a, b, x0, y0, x1, y1 = sys.argv[1], *map(int, sys.argv[2:])
prev = None
worst = 0
for n in range(a, b + 1):
    im = np.asarray(Image.open(f"{d}/f{n:05d}.png").convert("RGB"), dtype=np.int16)[y0:y1, x0:x1]
    if prev is not None:
        worst = max(worst, int(np.abs(im - prev).max()))
    prev = im
print(f"frames {a}-{b}, box ({x0},{y0})-({x1},{y1}): largest change between consecutive frames = {worst}")
print("RESULT:", "FROZEN" if worst <= 8 else "MOVING")
