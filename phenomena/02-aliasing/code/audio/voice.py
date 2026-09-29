"""The narration: from a raw recording of the script to the finished narrated films.

Run from phenomena/02-aliasing/code/:

    python3 audio/voice.py script                       write ../voice/SCRIPT.md, the script to read
    python3 audio/voice.py build --lang en --take ~/en.m4a
    python3 audio/voice.py build                        every language found in ../voice/raw/

A take is either ONE recording of the whole script (lines read in order, a pause of about
3 seconds between lines, a line said again after a slip), or a FOLDER with one file per line
(sorted by name). Any format ffmpeg reads is fine: wav, m4a, mp3, flac.

What `build` does, in order:
  1. cleans the recording: rumble filter, gentle noise reduction, tone (EQ), de-esser, compressor
  2. finds every line in it, drops slips and repeated lines (the last take of a line wins)
  3. places each line on its moment in the film and in the Short (the caption times); a line
     that is a little too long starts a bit earlier or is sped up by at most 10 %, never more
  4. mixes: the music dips under the voice (with a small dip in the voice band), the sound
     effects stay, then the whole is set to -14 LUFS with true peaks under -1.5 dBTP
  5. writes the subtitles of the narrated versions from the real voice times
  6. puts the sound on the picture: the film without burned captions (the voice says them),
     the Short with its captions
  7. prints a report: which part of the recording became which line, and every measurement

Outputs: ../video/02-aliasing_16x9_<lang>_narrated.mp4, ../video/02-aliasing_9x16_<lang>_narrated.mp4,
../subtitles/02-aliasing_narrated_<lang>.srt, ../subtitles/02-aliasing_9x16_narrated_<lang>.srt,
and in build/audio/voice/ the mixes, the voice alone and the report. The music-only
versions are not touched.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
from scipy import signal

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dsp  # noqa: E402
import master as mst  # noqa: E402
from dsp import SR  # noqa: E402
from make_audio import load_timeline, write_wav  # noqa: E402

CODE = Path(__file__).resolve().parents[1]
PIECE_DIR = CODE.parent
VOICE_DIR = PIECE_DIR / "voice"
OUT_AUDIO = CODE / "build" / "audio" / "voice"
OUT = {"video": PIECE_DIR / "video", "subtitles": PIECE_DIR / "subtitles"}
LANGS = ("en", "fr", "ar")
NAME = "02-aliasing"

# placement (seconds)
LEAD = 0.10          # the voice starts just after its caption moment
EARLY_MAX = 0.45     # a long line may start this much before its moment
GAP_AFTER = 0.20     # silence kept before the next line's moment
MIN_BREATH = 0.25    # shortest pause between two lines
END_PAD = 0.70       # the voice ends at least this long before the end of the film
MAX_SQUEEZE = 1.10   # at most 10 % faster: beyond that a voice stops sounding natural

# levels (dB)
TAKE_LUFS = -20.0    # every line is levelled to this before the mix
VOICE_LUFS = -16.0   # the whole voice track, before the master
MUSIC_BED_DB = -7.0  # the music under a narrated film sits lower than in the music-only film
DUCK_DB = -11.0      # extra dip of the music while the voice speaks
DUCK_MID_DB = -5.0   # and a further dip of the music's 0.7 to 4.5 kHz band (where speech lives)
SFX_DB = -2.0      # the effects under a narrated film
SFX_DUCK_DB = -8.0 # engines, rotors and motors step back while the voice speaks


def log(msg=""):
    print(msg, flush=True)


# --------------------------------------------------------------------------- the script
def load_script():
    with open(VOICE_DIR / "script.json", encoding="utf-8") as f:
        return json.load(f)


def timelines():
    return {c: load_timeline(c, CODE / "build" / f"{c}_timeline.json", False, log) for c in ("main", "short")}


def plain(s):
    return " ".join(str(s).replace(" ", " ").replace("‎", "").replace("‏", "").split())


def script_lines(lang, tls):
    """The lines to record, in order, with their text in `lang` and where they are used."""
    doc = load_script()
    text_of = {}
    for comp in ("short", "main"):
        for c in tls[comp]["captions"]:
            text_of[c["key"]] = c["text"]
    short_keys = {c["key"] for c in tls["short"]["captions"]}
    out = []
    for ln in doc["lines"]:
        say = (ln.get("say") or {}).get(lang)
        text = plain(say if say else text_of[ln["key"]].get(lang) or text_of[ln["key"]]["en"])
        only = ln.get("only")
        uses = []
        if only in (None, "main"):
            uses.append("main")
        if ln["key"] in short_keys and only in (None, "short"):
            if not any(o["key"] == ln["key"] and o.get("only") == "short" for o in doc["lines"]) or only == "short":
                uses.append("short")
        note = (ln.get("note") or {}).get(lang) or (ln.get("note") or {}).get("en", "")
        out.append(dict(n=ln["n"], key=ln["key"], text=text, note=note, uses=uses))
    return out, doc["sections"]


def windows(comp, tl):
    """caption key -> (moment, latest end) in seconds, for one composition."""
    caps = sorted(tl["captions"], key=lambda c: c["in"])
    out = {}
    for i, c in enumerate(caps):
        limit = caps[i + 1]["in"] - GAP_AFTER if i + 1 < len(caps) else tl["duration"] - END_PAD
        out[c["key"]] = (float(c["in"]), float(limit))
    return out, caps


# --------------------------------------------------------------------------- reading audio
def decode(path):
    """Any audio file -> mono float, 48 kHz (ffmpeg does the reading and the resampling)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)


def ffmpeg_filter(x, af):
    """Run a mono signal through an ffmpeg audio filter (used for rubberband time stretching)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                        "-af", af, "-f", "f32le", "-"], input=x.astype(np.float32).tobytes(),
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).astype(np.float64)


# --------------------------------------------------------------------------- cleaning
def frame_db(x, win=0.02, hop=0.01):
    w, h = int(win * SR), int(hop * SR)
    n = 1 + max(0, (len(x) - w) // h)
    idx = np.arange(w)[None, :] + h * np.arange(n)[:, None]
    return 10 * np.log10(np.mean(x[idx] ** 2, axis=1) + 1e-12), h


def denoise(x, max_cut_db=10.0):
    """Gentle noise reduction: learn the hiss from the quietest moments, lower it by at most 10 dB.

    The gain is smoothed in time and across frequency so it never 'bubbles' (musical noise).
    On a clean recording it changes almost nothing.
    """
    lev, _ = frame_db(x)
    floor = np.percentile(lev, 10)
    if floor < -72:                      # already very quiet: leave it alone
        return x, float(floor)
    f, t, X = signal.stft(x, SR, nperseg=1024, noverlap=768)
    P = np.abs(X) ** 2
    e = 10 * np.log10(P.mean(axis=0) + 1e-12)
    quiet = e < np.percentile(e, 15)
    if quiet.sum() < 20:
        return x, float(floor)
    N = P[:, quiet].mean(axis=1, keepdims=True)
    Ps = signal.lfilter([0.3], [1, -0.7], P, axis=1)            # smoothed power, per bin
    gmin = 10 ** (-max_cut_db / 20)
    G = np.clip(1 - 1.5 * N / (Ps + 1e-12), gmin, 1.0)
    G = signal.convolve2d(G, np.ones((3, 3)) / 9.0, mode="same", boundary="symm")
    # quick to open (speech onsets), slower to close
    Gs = G.copy()
    for k in range(1, G.shape[1]):
        a = 0.2 if G[:, k].mean() > Gs[:, k - 1].mean() else 0.6
        Gs[:, k] = a * Gs[:, k - 1] + (1 - a) * G[:, k]
    _, y = signal.istft(X * Gs, SR, nperseg=1024, noverlap=768)
    return np.pad(y, (0, max(0, len(x) - len(y))))[: len(x)], float(floor)


def high_shelf(x, f0, gain_db, S=0.7):
    A = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * f0 / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / 2.0 * np.sqrt((A + 1 / A) * (1 / S - 1) + 2)
    b0 = A * ((A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cw)
    b2 = A * ((A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cw)
    a2 = (A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * alpha
    return signal.lfilter([b0 / a0, b1 / a0, b2 / a0], [1.0, a1 / a0, a2 / a0], x)


def envelope_db(x, block=48, attack=0.008, release=0.12):
    """Level in dB, one value per sample, from 1 ms blocks with a fast attack and slow release."""
    n = len(x) // block * block
    rms = np.sqrt(np.mean(x[:n].reshape(-1, block) ** 2, axis=1) + 1e-12)
    lev = 20 * np.log10(rms)
    out = np.empty_like(lev)
    a_up, a_dn = math.exp(-block / (attack * SR)), math.exp(-block / (release * SR))
    s = lev[0]
    for i, v in enumerate(lev):
        s = a_up * s + (1 - a_up) * v if v > s else a_dn * s + (1 - a_dn) * v
        out[i] = s
    out = np.repeat(out, block)
    return np.r_[out, np.full(len(x) - n, out[-1] if len(out) else -120.0)]


def tone(x, speech):
    """EQ, de-esser and compressor, like a voice channel on a mixing desk."""
    y = dsp.hp(x, 70.0, 4)
    y = dsp.peaking(y, 280.0, -1.5, q=1.1)          # less boxiness
    y = dsp.peaking(y, 3400.0, +2.0, q=0.9)         # presence: words come forward
    y = high_shelf(y, 9000.0, +1.5)                 # a little air
    # de-esser: tame only the loudest "s" and "sh" sounds (5 to 9.5 kHz)
    sos = signal.butter(2, (5000.0, 9500.0), btype="bandpass", fs=SR, output="sos")
    sib = signal.sosfiltfilt(sos, y)
    env_s = envelope_db(sib, attack=0.002, release=0.06)
    thr = np.percentile(env_s[speech], 95) - 4.0 if speech.any() else -30.0
    over = np.clip(env_s - thr, 0.0, None)
    g_s = 10 ** (-np.minimum(over * 0.75, 8.0) / 20)
    y = y - sib * (1.0 - g_s)
    # compressor: 2.5:1 above the level of ordinary speech, soft knee
    env = envelope_db(y)
    T = np.percentile(env[speech], 75) if speech.any() else -24.0
    knee, ratio = 6.0, 2.5
    d = env - T
    gr = np.where(d <= -knee / 2, 0.0,
                  np.where(d >= knee / 2, d * (1 - 1 / ratio), (1 - 1 / ratio) * (d + knee / 2) ** 2 / (2 * knee)))
    return y * 10 ** (-gr / 20)


# --------------------------------------------------------------------------- finding the lines
def voiced_regions(x):
    """Stretches of speech (start, end) in samples, found with a two-threshold level detector."""
    lev, hop = frame_db(x)
    floor, peak = np.percentile(lev, 10), np.percentile(lev, 97)
    span = max(peak - floor, 12.0)
    on, off = floor + max(0.30 * span, 9.0), floor + max(0.18 * span, 6.0)
    act, state = np.zeros(len(lev), bool), False
    for i, v in enumerate(lev):
        state = v > on if not state else v > off
        act[i] = state
    edges = np.flatnonzero(np.diff(np.r_[0, act.astype(int), 0]))
    regs = [(a * hop, b * hop + int(0.02 * SR)) for a, b in zip(edges[::2], edges[1::2])]
    # join the small gaps inside a sentence, drop clicks
    out = []
    for a, b in regs:
        if out and a - out[-1][1] < 0.35 * SR:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return [(a, b) for a, b in out if b - a > 0.12 * SR]


def chunks_from(regions, gap):
    out = []
    for a, b in regions:
        if out and a - out[-1][1] < gap * SR:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def mfcc(x, n_mel=32, n_cep=13):
    f, t, X = signal.stft(x, SR, nperseg=1200, noverlap=0)    # 25 ms frames, 40 per second
    P = np.abs(X) ** 2
    mel = lambda hz: 2595 * np.log10(1 + hz / 700.0)
    edges = 700 * (10 ** (np.linspace(mel(80), mel(7600), n_mel + 2) / 2595) - 1)
    fb = np.zeros((n_mel, len(f)))
    for i in range(n_mel):
        lo, c, hi = edges[i], edges[i + 1], edges[i + 2]
        fb[i] = np.clip(np.minimum((f - lo) / (c - lo), (hi - f) / (hi - c)), 0, None)
    M = np.log(fb @ P + 1e-10)
    C = np.real(np.fft.fft(M, axis=0))[:n_cep]                   # a cosine transform, enough here
    C = C[1:] - C[1:].mean(axis=1, keepdims=True)
    return C.T


def dtw(A, B):
    n, m = len(A), len(B)
    if n == 0 or m == 0:
        return 1e9
    cost = np.sqrt(((A[:, None, :] - B[None, :, :]) ** 2).sum(axis=2))
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    for i in range(1, n + 1):
        ci, Dp = cost[i - 1], D[i - 1]
        row = D[i]
        for j in range(1, m + 1):
            row[j] = ci[j - 1] + min(Dp[j], row[j - 1], Dp[j - 1])
    return D[n, m] / (n + m)


def align(chunks, x, lines):
    """Which chunk of the recording is which line.

    A small search over every possible reading: each line is one chunk (or two or three
    chunks when there was a long pause inside it); a chunk may be dropped when it is a slip,
    a noise, or a line said again (then the LAST take is kept). The cost prefers durations
    that match the length of the text and drops that look like repeats.
    """
    M, N = len(chunks), len(lines)
    dur = np.array([(b - a) / SR for a, b in chunks])
    gaps = np.array([(chunks[i + 1][0] - chunks[i][1]) / SR for i in range(M - 1)] + [9.0])
    feats = [mfcc(x[a:b]) for a, b in chunks]
    sim = np.full(M, 9.0)                       # distance of chunk i to chunk i+1
    for i in range(M - 1):
        sim[i] = dtw(feats[i], feats[i + 1])
    ref = np.median([dtw(feats[i], feats[j]) for i in range(0, M - 2, 2) for j in (i + 2,) if j < M] or [1.0])
    simr = sim / max(ref, 1e-9)                 # below about 0.8: the same words said again
    # a false start is the beginning of the next part: compare with that beginning only
    pre = np.full(M, 9.0)
    for i in range(M - 1):
        pre[i] = dtw(feats[i], feats[i + 1][: max(4, int(1.3 * len(feats[i])))]) / max(ref, 1e-9)
    chars = np.array([max(len(l["text"]), 4) for l in lines], dtype=float)
    # a pause inside a line can be long, but clearly shorter than the pauses between lines
    join_gap = max(1.6, 0.8 * float(np.median(gaps[:-1]))) if M > 1 else 1.6
    rate = chars.sum() / max(dur.sum(), 1e-9)
    path = None
    for _ in range(3):
        d = chars / rate
        INF = 1e18
        C = np.full((M + 1, N + 1), INF)
        back = {}
        C[0, 0] = 0.0
        for i in range(M + 1):
            for j in range(N + 1):
                c0 = C[i, j]
                if c0 >= INF:
                    continue
                if i < M:                                   # drop chunk i
                    if dur[i] < 0.45:
                        k = 0.2                             # a click, a breath, a cough
                    elif simr[i] < 0.8:
                        k = 0.3                             # the same words again just after: a retake
                    elif pre[i] < 0.8 and j < N and dur[i] < 0.8 * d[j]:
                        k = 0.5                             # a false start
                    else:
                        k = 4.0 + dur[i]                    # real words: keep them unless nothing else fits
                    if c0 + k < C[i + 1, j]:
                        C[i + 1, j], back[(i + 1, j)] = c0 + k, (i, j, "drop")
                if i < M and j < N:
                    tot = 0.0
                    for g in (1, 2, 3):                    # line j = chunks i .. i+g-1
                        if i + g > M:
                            break
                        if g > 1 and gaps[i + g - 2] > join_gap:
                            break
                        tot = dur[i:i + g].sum() + gaps[i:i + g - 1].sum()
                        k = (math.log(tot / d[j]) / 0.35) ** 2 + 0.4 * (g - 1)
                        if c0 + k < C[i + g, j + 1]:
                            C[i + g, j + 1], back[(i + g, j + 1)] = c0 + k, (i, j, g)
        if C[M, N] >= INF:
            raise SystemExit(f"could not match {M} parts of the recording to {N} lines")
        path, node = [], (M, N)
        while node != (0, 0):
            i, j, what = back[node]
            path.append((i, j, what))
            node = (i, j)
        path.reverse()
        used = [(j, i, what) for i, j, what in path if what != "drop"]
        spoken = np.array([sum(dur[i:i + g]) + sum(gaps[i:i + g - 1]) for j, i, g in used])
        rate = float(np.median(chars / spoken))
    takes, dropped = [], []
    for i, j, what in path:
        if what == "drop":
            dropped.append(i)
        else:
            takes.append((chunks[i][0], chunks[i + what - 1][1], list(range(i, i + what))))
    return takes, dropped, rate


def find_takes(x, lines):
    regions = voiced_regions(x)
    for gap in (1.2, 1.0, 0.8, 0.65):
        chunks = chunks_from(regions, gap)
        if len(chunks) >= len(lines):
            break
    log(f"  {len(chunks)} parts found in the recording for {len(lines)} lines")
    takes, dropped, rate = align(chunks, x, lines)
    return takes, dropped, rate, chunks


# --------------------------------------------------------------------------- placing
def cut_take(y, a, b, pre=0.08, post=0.25):
    s, e = max(0, a - int(pre * SR)), min(len(y), b + int(post * SR))
    t = y[s:e].copy()
    t = dsp.fade_edges(t, 0.015, 0.06)
    return t, a - s, b - a                         # the take, where speech starts in it, speech length


def level(t):
    L = pyln.Meter(SR).integrated_loudness(np.pad(t, (0, max(0, int(0.5 * SR) - len(t)))))
    g = np.clip(TAKE_LUFS - L, -9.0, 9.0) if np.isfinite(L) else 0.0
    return t * 10 ** (g / 20)


def place_comp(comp, tl, items, report):
    """items: list of (key, take, onset, speech_len). Returns the voice track and the placements."""
    win, caps = windows(comp, tl)
    n = int(round(tl["duration"] * SR))
    bus = np.zeros(n)
    prev_end, rows = 0.0, []
    for k, (key, take, onset, slen) in enumerate(items):
        cue, limit = win[key]
        last = k == len(items) - 1
        D = slen / SR
        earliest = max(prev_end + MIN_BREATH, cue - (1.2 if last else EARLY_MAX), 0.3)
        start = max(cue + LEAD, earliest)
        squeeze = 1.0
        if start + D > limit:
            start = max(earliest, limit - D)
            if start + D > limit:
                room = max(limit - start, 1e-3)
                squeeze = min(D / room, 1.15 if last else MAX_SQUEEZE)
        if squeeze > 1.0005:
            take = ffmpeg_filter(take, f"rubberband=tempo={squeeze:.4f}:pitchq=quality:transients=mixed:detector=soft")
            onset, D = int(onset / squeeze), D / squeeze
        a = int(round(start * SR)) - onset
        dsp.place(bus, take, a)
        end = start + D
        rows.append(dict(key=key, cue=cue, start=round(start, 3), end=round(end, 3), limit=round(limit, 3),
                         faster_pct=round((squeeze - 1) * 100, 1), late=round(max(0.0, start - (cue + LEAD)), 2),
                         over=round(max(0.0, end - limit), 2)))
        prev_end = end
    report[comp] = rows
    return bus, rows


# --------------------------------------------------------------------------- mixing
def gate_curve(rows, n, pre=0.15, post=0.35, hold=1.6, attack=0.10, release=0.90):
    """1 while the voice speaks (a little before and after), 0 elsewhere, with smooth edges.

    Pauses shorter than `hold` between two lines keep the music down: it rises only in the
    longer breaths of the film, like a mixer riding the fader by hand, never pumping.
    """
    g = np.zeros(n)
    spans = []
    for r in rows:
        a, b = r["start"] - pre, r["end"] + post
        if spans and a - spans[-1][1] < hold:
            spans[-1][1] = b
        else:
            spans.append([a, b])
    for a, b in spans:
        g[max(0, int(a * SR)): min(n, int(b * SR))] = 1.0
    blk = 48
    m = n // blk
    gb = g[: m * blk].reshape(m, blk).max(axis=1)
    out = np.empty(m)
    a_on, a_off = math.exp(-blk / (attack * SR)), math.exp(-blk / (release * SR))
    s = 0.0
    for i, v in enumerate(gb):
        s = a_on * s + (1 - a_on) * v if v > s else a_off * s + (1 - a_off) * v
        out[i] = s
    # look ahead: the dip is complete when the first word starts
    shift = int(attack * SR / blk)
    out = np.r_[out[shift:], np.full(shift, out[-1])]
    return np.r_[np.repeat(out, blk), np.full(n - m * blk, out[-1])]


def mix(voice, music, sfx, rows):
    n = len(voice)
    music, sfx = music[:n], sfx[:n]
    g = gate_curve(rows, n)
    duck = 10 ** ((MUSIC_BED_DB + DUCK_DB * g) / 20)[:, None]
    mid_sos = signal.butter(2, (700.0, 4500.0), btype="bandpass", fs=SR, output="sos")
    mid = signal.sosfiltfilt(mid_sos, music, axis=0)
    carve = (10 ** (DUCK_MID_DB * g / 20) - 1.0)[:, None]
    bed = (music + mid * carve) * duck
    fx = sfx * (10 ** ((SFX_DB + SFX_DUCK_DB * g) / 20))[:, None]
    L = pyln.Meter(SR).integrated_loudness(voice)
    v = voice * 10 ** ((VOICE_LUFS - L) / 20)
    vst = np.stack([v, v], axis=1) * 10 ** (-3 / 20)
    return vst, bed, fx


def master_mix(v, bed, fx, target=mst.TARGET_LUFS, ceiling=mst.CEILING_DB):
    tot = v + bed + fx
    g = 10 ** ((target - mst.integrated_lufs(tot)) / 20)
    for _ in range(8):
        lim, st = mst.limiter_gain([tot], g, ceiling)
        L = mst.integrated_lufs(tot * g * lim[:, None])
        if abs(target - L) < 0.03:
            break
        g *= 10 ** ((target - L) / 20)
    k = (g * lim)[:, None]
    return tot * k, v * k, st


def speech_over_bed(v, rest, rows):
    """Median of (voice minus everything else) in 400 ms windows while the voice speaks, in dB."""
    diffs = []
    w = int(0.4 * SR)
    for r in rows:
        for a in range(int(r["start"] * SR), min(int(r["end"] * SR), len(v)) - w, w // 2):
            pv = np.mean(v[a:a + w] ** 2)
            pr = np.mean(rest[a:a + w] ** 2)
            if pv > 1e-9:
                diffs.append(10 * np.log10(pv / (pr + 1e-12)))
    return float(np.median(diffs)) if diffs else float("nan")


# --------------------------------------------------------------------------- pictures, subtitles
def run(cmd, **kw):
    log("  $ " + " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], cwd=CODE, check=True, **kw)


def picture(comp, lang):
    """The video-only master the narrated sound goes on (rendered if it is not there yet)."""
    final = CODE / "build" / "final"
    if comp == "main":
        v = final / f"main_{lang}_clean_video.mp4"
        if not v.exists():
            run(["node", "render.mjs", "--comp", "main", "--lang", lang, "--workers", "4", "--stream", "--encode",
                 "--no-captions", "--out", f"build/main_{lang}_clean", "--video", v, "--png-every", "30", "--quiet"])
        return v
    reworded = json.loads((CODE / "data" / "voice" / "short.json").read_text(encoding="utf-8"))
    if any(lang in tr for k, tr in reworded.items() if not k.startswith("_")):
        v = final / f"short_{lang}_voice_video.mp4"
        if not v.exists():
            run(["node", "render.mjs", "--comp", "short", "--lang", lang, "--workers", "4", "--stream", "--encode",
                 "--voice", "--out", f"build/short_{lang}_voice", "--video", v, "--png-every", "30", "--quiet"])
        return v
    v = final / f"short_{lang}_video.mp4"
    if not v.exists():
        run(["node", "render.mjs", "--comp", "short", "--lang", lang, "--workers", "4", "--stream", "--encode",
             "--video", v, "--png-every", "30", "--quiet"])
    return v


def subtitles(comp, lang, rows, text_of, tl):
    """Subtitles of the narrated version: the words of the voice, at the times of the voice."""
    caps = []
    for i, r in enumerate(rows):
        nxt = rows[i + 1]["start"] if i + 1 < len(rows) else tl["duration"] - 0.2
        out = min(max(r["end"] + 0.6, r["start"] + 1.2), nxt - 0.05)
        pieces = split_for_subtitles(text_of[r["key"]])
        t0, total = r["start"] - 0.05, sum(len(p) for p in pieces)
        for j, piece in enumerate(pieces):
            t1 = out if j == len(pieces) - 1 else t0 + (r["end"] - r["start"]) * len(piece) / total
            caps.append(dict(scene="voice", key=f"voice.{comp}.{len(caps) + 1:02d}", **{"in": round(t0, 3)},
                             out=round(t1, 3), burn=False, text={lang: piece}))
            t0 = t1
    tfile = OUT_AUDIO / f"timeline_{comp}_{lang}.json"
    tfile.write_text(json.dumps(dict(comp=comp, duration=tl["duration"], captions=caps), ensure_ascii=False, indent=1),
                     encoding="utf-8")
    name = "narrated" if comp == "main" else "9x16_narrated"
    run(["node", "tools/make_srt.mjs", name, "--timeline", tfile, "--langs", lang, "--out", OUT["subtitles"], "--quiet"])


def split_for_subtitles(text, width=42):
    """Two lines of about 42 characters make one subtitle; a longer line is split in two
    subtitles at the sentence end (or else the comma) nearest its middle."""
    if len(text) <= 2 * width:
        return [text]
    best = None
    for marks in ((". ", "? ", "! ", "… ", "؟ "), (": ", "; ", "، ", ", ")):
        for m in marks:
            k = text.find(m)
            while k != -1:
                cut = k + len(m) - 1
                score = abs(cut - len(text) / 2)
                if best is None or score < best[0]:
                    best = (score, cut)
                k = text.find(m, k + 1)
        if best:
            break
    if best is None:
        return [text]
    a, b = text[: best[1]].strip(), text[best[1]:].strip()
    return split_for_subtitles(a, width) + split_for_subtitles(b, width)


def mux(video, wav, out):
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "320k", "-ar", str(SR), "-shortest", "-movflags", "+faststart", out])


# --------------------------------------------------------------------------- the build
def build(lang, take_path):
    OUT_AUDIO.mkdir(parents=True, exist_ok=True)
    tls = timelines()
    lines, _ = script_lines(lang, tls)
    log(f"\n=== {lang}: narration from {take_path}")
    take_path = Path(take_path).expanduser()
    if take_path.is_dir():
        files = sorted(p for p in take_path.iterdir() if p.is_file() and not p.name.startswith("."))
        if len(files) != len(lines):
            raise SystemExit(f"{take_path} has {len(files)} files, the script has {len(lines)} lines: one file per line, please")
        parts = [decode(p) for p in files]
        pad = np.zeros(int(1.5 * SR))
        x = np.concatenate([np.r_[p, pad] for p in parts])
        bounds, pos = [], 0
        for p in parts:
            bounds.append((pos, pos + len(p)))
            pos += len(p) + len(pad)
    else:
        x, bounds = decode(take_path), None
    log(f"  recording: {len(x) / SR:.1f} s")
    x = dsp.hp(x, 60.0, 2)
    x, floor = denoise(x)
    log(f"  noise floor {floor:.0f} dB (reduced by at most 10 dB)")
    regions = voiced_regions(x)
    speech = np.zeros(len(x), bool)
    for a, b in regions:
        speech[a:b] = True
    y = tone(x, speech)
    if bounds is None:
        takes, dropped, rate, chunks = find_takes(x, lines)
    else:
        takes = []
        for a, b in bounds:
            rs = [(s, e) for s, e in regions if s >= a and e <= b] or [(a, b)]
            takes.append((rs[0][0], rs[-1][1], []))
        dropped, rate, chunks = [], None, None
    report = dict(lang=lang, recording=str(take_path), lines=[], dropped=[])
    per_line = {}
    for ln, (a, b, parts_used) in zip(lines, takes):
        t, onset, slen = cut_take(y, a, b)
        per_line[ln["n"]] = (level(t), onset, slen)
        report["lines"].append(dict(n=ln["n"], at=f"{a / SR:.1f}-{b / SR:.1f} s", seconds=round(slen / SR, 2)))
    if chunks is not None:
        report["dropped"] = [f"{chunks[i][0] / SR:.1f}-{chunks[i][1] / SR:.1f} s" for i in dropped]
        log(f"  speaking rate {rate:.1f} characters per second; parts left out (slips, repeats): "
            + (", ".join(report["dropped"]) or "none"))
    text_of = {}
    outputs = []
    for comp, stems, shape in (("main", ("music.wav", "sfx.wav"), "16x9"), ("short", ("short_music.wav", "short_sfx.wav"), "9x16")):
        tl = tls[comp]
        keys = [c["key"] for c in sorted(tl["captions"], key=lambda c: c["in"])]
        items = []
        for key in keys:
            cand = [l for l in lines if l["key"] == key and comp in l["uses"]]
            if not cand:
                raise SystemExit(f"no line of the script for {key} in {comp}")
            l = cand[-1]
            text_of[key] = l["text"]
            t, onset, slen = per_line[l["n"]]
            items.append((key, t, onset, slen))
        voice_bus, rows = place_comp(comp, tl, items, report)
        music = dsp_read(CODE / "build" / "audio" / stems[0])
        sfx = dsp_read(CODE / "build" / "audio" / stems[1])
        v, bed, fx = mix(voice_bus, music, sfx, rows)
        final, vfinal, lim = master_mix(v, bed, fx)
        L = mst.integrated_lufs(final)
        tp = dsp.true_peak_db(final)
        sob = speech_over_bed(vfinal[:, 0], (final - vfinal)[:, 0], rows)
        wav = OUT_AUDIO / f"narrated_{comp}_{lang}.wav"
        write_wav(wav, final)
        write_wav(OUT_AUDIO / f"voice_{comp}_{lang}.wav", vfinal)
        report[f"{comp}_measured"] = dict(lufs=round(L, 2), true_peak_dbtp=round(tp, 2), voice_over_rest_db=round(sob, 1),
                                          limiter_max_db=round(lim["max_reduction_db"], 2))
        subtitles(comp, lang, rows, text_of, tl)
        out = OUT["video"] / f"{NAME}_{shape}_{lang}_narrated.mp4"
        mux(picture(comp, lang), wav, out)
        outputs.append(out)
        log(f"  {comp}: {L:.1f} LUFS, true peak {tp:.1f} dBTP, voice {sob:.0f} dB above the music and effects -> {out.name}")
    (OUT_AUDIO / f"report_{lang}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print_report(report, lines)
    return outputs


def dsp_read(path):
    import soundfile as sf
    x, sr = sf.read(str(path), always_2d=True)
    assert sr == SR, path
    return x


def print_report(rep, lines):
    by_n = {l["n"]: l for l in lines}
    log("\n  line  in your recording   length   film: start (moment)  change")
    rows_main = {r["key"]: r for r in rep.get("main", [])}
    for r in rep["lines"]:
        l = by_n[r["n"]]
        pm = rows_main.get(l["key"]) if "main" in l["uses"] else None
        where = f"{pm['start']:7.2f} ({pm['cue']:.2f})" if pm else "  (Short only)  "
        ch = []
        if pm and pm["faster_pct"]:
            ch.append(f"{pm['faster_pct']:.0f} % faster")
        if pm and pm["over"]:
            ch.append(f"runs {pm['over']:.2f} s long")
        if pm and pm["late"] > 0.3:
            ch.append(f"starts {pm['late']:.2f} s late")
        log(f"  {r['n']:>4}  {r['at']:<18} {r['seconds']:5.1f} s   {where}  {', '.join(ch)}")
    for comp in ("main", "short"):
        bad = [r for r in rep.get(comp, []) if r["over"] > 0.05 or r["faster_pct"] >= 9.5]
        if bad:
            log(f"  {comp}: re-record a little faster: " + ", ".join(r["key"] for r in bad))


# --------------------------------------------------------------------------- the script to read
def write_script_md():
    tls = timelines()
    wins = {c: windows(c, tls[c])[0] for c in tls}
    titles = {"en": "English", "fr": "Français", "ar": "العربية"}
    out = ["# Narration script - 02 · Aliasing", "",
           "Generated from `voice/script.json` and the film's timing by `code/audio/voice.py script`. "
           "Do not edit by hand: change `script.json`, then run the command again.", "",
           "How to record: see [`README.md`](README.md). Read the lines in order, with a pause of about "
           "3 seconds between lines. If you slip, pause and say the whole line again: the last take wins.", "",
           "**Aim for** is the time the line has in the film. Speak naturally: the finishing step can "
           "start a line a little early or speed it up by a few per cent, so a small overrun is fine.", ""]
    for lang in LANGS:
        lines, sections = script_lines(lang, tls)
        first = {s["first"]: s for s in sections}
        out += [f"## {titles[lang]}", ""]
        for l in lines:
            if l["n"] in first:
                s = first[l["n"]]
                out += [f"### {s['name']}", "", f"*{s['tone']}*", ""]
            budget = min(wins[c][l["key"]][1] - wins[c][l["key"]][0] + EARLY_MAX * 0.5 for c in l["uses"])
            where = " (Short only)" if l["uses"] == ["short"] else ""
            out.append(f"{l['n']}. **{l['text']}**  ")
            out.append(f"   Aim for {budget:.1f} s{where}." + (f" {l['note']}" if l["note"] else ""))
            out.append("")
    (VOICE_DIR / "SCRIPT.md").write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    log(f"wrote {VOICE_DIR / 'SCRIPT.md'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("script", help="write ../voice/SCRIPT.md")
    b = sub.add_parser("build", help="make the narrated versions from the recordings")
    b.add_argument("--lang", choices=LANGS)
    b.add_argument("--take", help="the recording (a file, or a folder with one file per line)")
    b.add_argument("--out", help="put the videos, subtitles and mixes in this folder instead (for trying things out)")
    a = ap.parse_args()
    if getattr(a, "out", None):
        global OUT_AUDIO
        o = Path(a.out).resolve()
        OUT_AUDIO = o
        OUT.update(video=o, subtitles=o)
        o.mkdir(parents=True, exist_ok=True)
    if a.cmd == "script":
        write_script_md()
        return
    jobs = []
    if a.lang and a.take:
        jobs = [(a.lang, a.take)]
    else:
        raw = VOICE_DIR / "raw"
        for lang in ([a.lang] if a.lang else LANGS):
            found = sorted(p for p in raw.glob(f"{lang}*") if not p.name.startswith(".")) if raw.exists() else []
            if found:
                jobs.append((lang, found[0]))
        if not jobs:
            raise SystemExit(f"no recording found: put en.m4a, fr.m4a, ar.m4a (or folders en/, fr/, ar/) in {raw}")
    for lang, take in jobs:
        build(lang, take)


if __name__ == "__main__":
    main()
