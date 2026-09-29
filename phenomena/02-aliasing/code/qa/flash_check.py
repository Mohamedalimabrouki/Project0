"""Photosensitivity screen for a rendered frame sequence.

Follows the WCAG 2.3.1 "general flash" definition, measured the way analysers
such as PEAT do it:
  - a transition is a change in relative luminance of at least 0.10 between two
    consecutive frames, where the darker of the two is below 0.80;
  - a window the size of a 10 degree field of view (a third of the screen
    width by a third of its height, like 341 x 256 px on 1024 x 768) registers
    a transition when at least 25 % of its pixels rise together (or fall
    together);
  - a flash is a pair of opposing transitions; more than 3 flashes in any
    one-second period, in any window, fails.
It also reports the broadcast view (ITU-R BT.1702: the whole screen as one
window, same 25 % rule).

A spinning wheel changes many pixels, but half of them get brighter while the
other half get darker in the same frame, and each frame moves only a small
area: that is motion, not a flash, and this method treats it that way.

Usage: python3 qa/flash_check.py build/main_en/frames [fps]
"""
import glob
import sys

import numpy as np
from PIL import Image

frames_dir = sys.argv[1]
fps = int(sys.argv[2]) if len(sys.argv) > 2 else 30
files = sorted(glob.glob(f"{frames_dir}/f*.png"))
if len(files) < 2:
    sys.exit("not enough frames")


def rel_lum(path):
    im = Image.open(path).convert("RGB")
    w = 480 if im.width >= im.height else 270
    im = im.resize((w, round(w * im.height / im.width)), Image.BILINEAR)
    c = np.asarray(im, dtype=np.float32) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]


def box_sums(mask, wh, ww, stride):
    ii = np.pad(mask.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    ys = np.arange(0, mask.shape[0] - wh + 1, stride)
    xs = np.arange(0, mask.shape[1] - ww + 1, stride)
    Y, X = np.meshgrid(ys, xs, indexing="ij")
    return ii[Y + wh, X + ww] - ii[Y, X + ww] - ii[Y + wh, X] + ii[Y, X]


prev = rel_lum(files[0])
H, W = prev.shape
wh, ww = H // 3, W // 3
area = wh * ww
trans_win, trans_full, worst_frac = [], [], 0.0
for f in files[1:]:
    cur = rel_lum(f)
    d = cur - prev
    ok = np.minimum(cur, prev) < 0.80
    rise = (d >= 0.10) & ok
    fall = (d <= -0.10) & ok
    r, fl = box_sums(rise, wh, ww, 10) / area, box_sums(fall, wh, ww, 10) / area
    worst_frac = max(worst_frac, float(r.max()), float(fl.max()))
    t = np.where(r >= 0.25, 1, 0) + np.where(fl >= 0.25, -1, 0)
    trans_win.append(t.astype(np.int8))
    fr, ff = rise.mean(), fall.mean()
    trans_full.append(1 if fr >= 0.25 else -1 if ff >= 0.25 else 0)
    prev = cur


def worst_flash_rate(seq):
    """seq: (n, ...) transitions per frame pair. Returns the largest number of
    flashes (opposing transition pairs) in any 1 s window, per window cell."""
    seq = np.asarray(seq)
    n = seq.shape[0]
    last = np.zeros(seq.shape[1:], np.int8)
    flash_at = np.zeros(seq.shape, np.uint8)
    for i in range(n):
        s = seq[i]
        completes = (s != 0) & (last != 0) & (s != last)
        flash_at[i] = completes
        last = np.where(s != 0, s, last)
    cs = np.concatenate([np.zeros((1,) + seq.shape[1:], np.int32), flash_at.cumsum(0, dtype=np.int32)])
    best = 0
    for i in range(0, max(1, n - fps + 1)):
        best = max(best, int((cs[min(n, i + fps)] - cs[i]).max()))
    return best


wf = worst_flash_rate(trans_win)
ff = worst_flash_rate(np.array(trans_full)[:, None])
print(f"frames: {len(files)}")
print(f"largest share of a 10-degree window changing together in one frame: {100 * worst_frac:.1f} % (flash needs 25 %)")
print(f"most flashes in any 1 s, any 10-degree window (WCAG): {wf} (limit 3)")
print(f"most flashes in any 1 s, whole screen (ITU-R BT.1702): {ff} (limit 3)")
print("RESULT:", "PASS" if wf <= 3 and ff <= 3 else "FAIL")
