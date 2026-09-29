"""Photosensitivity screen for a rendered frame sequence (WCAG 2.3.1 style).

A "flash" is a pair of opposing changes in relative luminance of at least 10 %
of the maximum, where the darker state is below 0.80. The guideline fails when
more than 3 flashes happen within any one second over a combined area larger
than about a quarter of a 10 degree field of view (at normal viewing distance
roughly 10 % of a 16:9 screen; we flag anything over 2 %, to keep a margin).

Usage: python3 qa/flash_check.py build/main_en/frames [fps]
Works on a downscaled copy (480 x 270) for speed. Prints the worst window.
"""
import glob
import sys

import numpy as np
from PIL import Image

frames_dir = sys.argv[1]
fps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
files = sorted(glob.glob(f"{frames_dir}/f*.png"))
if not files:
    sys.exit("no frames")


def rel_lum(path):
    im = Image.open(path).convert("RGB")
    w = 480 if im.width >= im.height else 270
    im = im.resize((w, round(w * im.height / im.width)), Image.BILINEAR)
    c = np.asarray(im, dtype=np.float32) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


prev = rel_lum(files[0])
shape = prev.shape
last_dir = np.zeros(shape, np.int8)       # direction of the last significant change
ref = prev.copy()                          # luminance at the last significant change
events = []                                # per frame: map of completed opposing changes
for f in files[1:]:
    cur = rel_lum(f)
    d = cur - ref
    sig = (np.abs(d) >= 0.10) & (np.minimum(cur, ref) < 0.80)
    new_dir = np.sign(d).astype(np.int8)
    half = sig & (last_dir != 0) & (new_dir != last_dir)
    events.append(half)
    last_dir = np.where(sig, new_dir, last_dir)
    ref = np.where(sig, cur, ref)

ev = np.stack(events).astype(np.uint8)
cs = np.concatenate([np.zeros((1,) + shape, np.int32), np.cumsum(ev, axis=0, dtype=np.int32)])
worst, worst_at = 0.0, 0
for i in range(0, len(events) - fps + 1):
    count = cs[i + fps] - cs[i]            # opposing changes in this 1 s window
    area = float(np.mean(count >= 7))      # 7 opposing changes = more than 3 flashes
    if area > worst:
        worst, worst_at = area, i
print(f"frames: {len(files)}  worst 1-second window starts at frame {worst_at + 1} "
      f"({(worst_at + 1) / fps:.2f} s): {100 * worst:.2f} % of the screen flashes more than 3 times")
print("RESULT:", "PASS" if worst <= 0.02 else "CHECK" if worst <= 0.10 else "FAIL")
