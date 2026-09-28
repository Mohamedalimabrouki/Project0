"""
Resonance - subtitles in English, French and Arabic (SRT, UTF-8), timed to the voice-over.

Each narration line is cut into readable pieces (at most 2 lines of about 42
characters), and each piece gets a share of the line's time in proportion to
its length. Arabic reads right to left; numbers and units stay left to right.

  python make_subtitles.py OUT_DIR
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline as tl  # noqa: E402
from script import LINES  # noqa: E402

MAX_LINE = {"en": 42, "fr": 44, "ar": 40}


def sentences(text):
    parts = re.split(r"(?<=[.!?؟:])\s+", text.strip())
    return [p for p in parts if p]


def wrap(text, width):
    """Split into 1 or 2 balanced lines."""
    if len(text) <= width:
        return [text]
    words = text.split(" ")
    best = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        score = max(len(a), len(b))
        if best is None or score < best[0]:
            best = (score, [a, b])
    return best[1]


def chunks(text, width):
    """Pieces that each fit in 2 lines."""
    out = []
    for s in sentences(text):
        if len(s) <= 2 * width:
            out.append(s)
            continue
        # split long sentences at commas, then at word boundaries
        pieces = re.split(r"(?<=,)\s+", s)
        cur = ""
        for pc in pieces:
            if cur and len(cur) + 1 + len(pc) > 2 * width:
                out.append(cur)
                cur = pc
            else:
                cur = (cur + " " + pc).strip()
        if cur:
            out.append(cur)
    final = []
    for c in out:
        while len(c) > 2 * width:
            words = c.split(" ")
            half = len(words) // 2
            final.append(" ".join(words[:half]))
            c = " ".join(words[half:])
        final.append(c)
    # merge short neighbours so a cue is not on screen for a blink
    merged = []
    for c in final:
        if merged and len(merged[-1]) + 1 + len(c) <= 2 * width - 6 and (len(c) < 30 or len(merged[-1]) < 30):
            merged[-1] = merged[-1] + " " + c
        else:
            merged.append(c)
    return merged


def fmt(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def arabic_fix(text):
    # keep numbers with their % sign together, left to right
    return re.sub(r"(\d+(?:[.,]\d+)?)\s*%", r"\1%", text)


def build(lang, times):
    cues = []
    for item in LINES:
        a, b = times[item["id"]]
        text = item[lang]
        if lang == "ar":
            text = arabic_fix(text)
        pcs = chunks(text, MAX_LINE[lang])
        total = sum(len(p) for p in pcs)
        t = a
        for p in pcs:
            d = (b - a) * len(p) / total
            cues.append([t, t + d, wrap(p, MAX_LINE[lang])])
            t += d
    # readability: hold each cue at least 1.2 s when there is room, never overlap the next
    for i, cue in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else cue[1] + 2
        cue[1] = min(max(cue[1] + 0.25, cue[0] + 1.2), nxt - 0.04)
    return cues


def write_srt(cues, path):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for i, (a, b, lines) in enumerate(cues, 1):
            f.write(f"{i}\n{fmt(a)} --> {fmt(b)}\n" + "\n".join(lines) + "\n\n")


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    times = tl.line_times()
    for lang in ("en", "fr", "ar"):
        cues = build(lang, times)
        path = os.path.join(out, f"01-resonance_{lang}.srt")
        write_srt(cues, path)
        print(lang, len(cues), "cues ->", path)


if __name__ == "__main__":
    main()
