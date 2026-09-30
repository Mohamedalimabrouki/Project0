"""
Resonance - the master timeline (all times in seconds from the start of the video).

The voice-over sets the pace: each line starts after the previous one plus
its gap, except where a scene needs a fixed start (ANCHORS). Scene start
times are derived from the lines, so the pictures always follow the voice.
"""

import json
import os

from script import LINES

FPS = 30
HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.environ.get("EP_BUILD", os.path.join(HERE, "..", "build"))

# Lines that must not start before a given time (visual beats need room)
ANCHORS = {
    "L01": 3.0,
    "L05": 25.2,
    "L07": 37.2,
    "L09": 51.0,
    "L15": 83.6,
    "L18": 110.2,
    "L22": 141.6,
    "L25": 165.2,
}

END_HOLD = 6.0      # closing card stays on screen after the last line


def load_durations(narration_dir=None):
    """Length of each voice line, read from the WAV files (so a new recording just works)."""
    import soundfile as sf
    narration_dir = narration_dir or os.path.join(BUILD, "audio", "narration")
    return {item["id"]: sf.info(os.path.join(narration_dir, f"{item['id']}.wav")).duration for item in LINES}


def line_times(durations=None):
    durations = durations or load_durations()
    times = {}
    t = 0.0
    for item in LINES:
        start = max(t, ANCHORS.get(item["id"], 0.0))
        end = start + durations[item["id"]]
        times[item["id"]] = (start, end)
        t = end + item["gap"]
    return times


def scenes(times=None):
    """Scene boundaries (global seconds). Each scene may overlap its neighbours for transitions."""
    T = times or line_times()
    s = {}
    s["ident"] = (0.0, 2.6)
    s["hook"] = (2.0, T["L04"][0] + 1.2)              # two swings (3D)
    s["title"] = (T["L04"][0] - 0.2, T["L05"][0])     # title card (2D)
    s["rhythm_swing"] = (T["L05"][0] - 0.5, T["L07"][0] + 0.2)   # single swing (3D)
    s["spring_hero"] = (T["L07"][0] - 0.4, T["L08"][0] + 1.6)    # mass on a spring (3D)
    s["spring_model"] = (T["L08"][0] + 0.4, T["L09"][0])          # schematic, k and m (2D)
    s["sweep"] = (T["L09"][0] - 0.3, T["L15"][0])                 # push rhythm sweep (2D)
    s["damping"] = (T["L15"][0] - 0.3, T["L18"][0])               # damping curves (2D)
    s["bridge"] = (T["L18"][0] - 0.5, T["L22"][0])                # Millennium Bridge (2D)
    s["taipei"] = (T["L22"][0] - 0.5, T["L25"][0])                # Taipei 101 (3D + 2D)
    s["takeaway"] = (T["L25"][0] - 0.6, T["L25"][1] + END_HOLD)   # closing card (2D)
    return s


def total_duration():
    return scenes()["takeaway"][1]


def frame(t):
    return int(round(t * FPS))


if __name__ == "__main__":
    T = line_times()
    for k, (a, b) in T.items():
        print(f"{k}  {a:7.2f} -> {b:7.2f}")
    for k, (a, b) in scenes(T).items():
        print(f"{k:14s} {a:7.2f} -> {b:7.2f}  ({b - a:5.2f} s, {frame(b) - frame(a)} frames)")
    print(f"total {total_duration():.2f} s")


# ---------------------------------------------------------------------------
# Phrase timing inside a line: find the pauses in the voice recording and map
# the text's punctuation to them, so a picture can land exactly on a word.
# ---------------------------------------------------------------------------

import re as _re
import functools as _ft


@_ft.lru_cache(maxsize=None)
def _segments(line_id):
    import numpy as np
    import soundfile as sf
    path = os.path.join(BUILD, "audio", "narration", f"{line_id}.wav")
    x, sr = sf.read(path)
    if x.ndim > 1:
        x = x.mean(axis=1)
    win = int(0.02 * sr)
    n = len(x) // win
    rms = np.sqrt(np.mean(x[:n * win].reshape(n, win) ** 2, axis=1))
    thr = max(0.012, 0.08 * np.percentile(rms, 95))
    loud = rms > thr
    # speech segments separated by pauses of at least 140 ms
    segs = []
    start = None
    quiet = 0
    for i, v in enumerate(loud):
        if v:
            if start is None:
                start = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet * 0.02 >= 0.14:
                segs.append((start * 0.02, (i - quiet + 1) * 0.02))
                start = None
                quiet = 0
    if start is not None:
        segs.append((start * 0.02, n * 0.02))
    return segs, n * 0.02


def phrase_time(line_id, phrase, times=None):
    """Global time (s) when `phrase` starts inside line `line_id` (estimate, ±0.15 s)."""
    from script import line as _line
    T = times or line_times()
    text = _line(line_id).get("say", _line(line_id)["en"]) if phrase not in _line(line_id)["en"] else _line(line_id)["en"]
    idx = text.find(phrase)
    if idx < 0:
        raise ValueError(f"{phrase!r} not in {line_id}")
    segs, dur = _segments(line_id)
    # chunks of text between punctuation marks that usually produce a pause
    cuts = [0] + [m.end() for m in _re.finditer(r"[.,:;?!]\s+", text)]
    chunk_starts = cuts
    t0 = T[line_id][0]
    if len(segs) == len(chunk_starts):
        k = max(i for i, c in enumerate(chunk_starts) if c <= idx)
        c0 = chunk_starts[k]
        c1 = chunk_starts[k + 1] if k + 1 < len(chunk_starts) else len(text)
        s0, s1 = segs[k]
        u = (idx - c0) / max(1, (c1 - c0))
        return t0 + s0 + u * (s1 - s0)
    # fall back: proportional to characters across the whole line
    return t0 + dur * idx / max(1, len(text))
