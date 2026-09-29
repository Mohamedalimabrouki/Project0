"""The final stage: tidy the low and high ends, fade in and out, set the loudness, catch the peaks.

Targets (from the brief):  integrated loudness -14 LUFS (+-0.5)   true peak <= -1.0 dBTP.
A "true peak" is the highest point of the smooth curve between the samples; it can be a little
higher than the highest sample, and it is what streaming services and AAC encoders react to.
The limiter here works on an 8x oversampled copy, so it sees those hidden peaks, and it leaves a
further 0.5 dB of margin (ceiling -1.5 dBTP) because the film's audio is later encoded to AAC.
"""
from __future__ import annotations

import numpy as np
import pyloudnorm as pyln
from scipy import signal

import dsp
from dsp import SR, idx

TARGET_LUFS = -14.0
CEILING_DB = -1.5


def bus_eq(x):
    """Remove infrasonic rumble (DC, < 22 Hz) and soften anything above about 15 kHz."""
    y = dsp.hp(x, 22.0, 2)
    y = dsp.lp(y, 15000.0, 2)
    # a very gentle high shelf: -1.5 dB above about 7 kHz keeps the top end soft, never harsh
    f0, gain_db, S = 7000.0, -1.5, 0.7
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
    return signal.lfilter([b0 / a0, b1 / a0, b2 / a0], [1.0, a1 / a0, a2 / a0], y, axis=0)


def fade_envelope(n, fade_in=0.35, out_start=None, out_end=None):
    """1 in the middle, a raised-cosine fade in at the start, a fade out that ends in exact silence
    (the last 0.5 s are zero; the fade starts 3 s before the end)."""
    dur = n / SR
    out_start = dur - 3.0 if out_start is None else out_start
    out_end = dur - 0.5 if out_end is None else out_end
    e = np.ones(n)
    a = idx(fade_in)
    e[:a] = dsp.ramp_up(a)
    s, t = idx(out_start), idx(out_end)
    e[s:t] = dsp.ramp_down(t - s)
    e[t:] = 0.0
    return e


def integrated_lufs(x):
    return pyln.Meter(SR).integrated_loudness(x)


def _true_peak_track(seg, os=8):
    """Per-sample true peak (max over the oversampled points inside each sample interval)."""
    y = signal.resample_poly(seg, os, 1, axis=0)
    y = np.max(np.abs(y), axis=1)
    return y[: (len(y) // os) * os].reshape(-1, os).max(axis=1)


def limiter_gain(signals, gain, ceiling_db=CEILING_DB, half_width=2400, iterations=4, os=8):
    """Gain curve (one value per sample) that keeps the true peak of every signal, multiplied by
    `gain` and by this curve, under the ceiling.

    `signals` is a list of (n, 2) arrays (here: the mix and its two stems, so that all three files stay
    under the ceiling). Wherever an oversampled signal pokes above it, a smooth raised-cosine dip (50 ms
    each side) is pressed into the gain, just deep enough. Elsewhere the gain is exactly 1.
    """
    ceil = 10 ** (ceiling_db / 20.0)
    n = signals[0].shape[0]
    g = np.ones(n)
    pk0 = np.maximum.reduce([np.max(np.abs(x), axis=1) for x in signals]) * gain
    win = 0.5 * (1.0 + np.cos(np.pi * np.arange(-half_width, half_width + 1) / half_width))
    stats = dict(passes=0, dips=0, max_reduction_db=0.0, events=[])
    for _ in range(iterations):
        pk = pk0 * g
        cand = np.where(pk > ceil * 0.70)[0]
        if len(cand) == 0:
            break
        cuts = np.where(np.diff(cand) > 4096)[0]
        starts = np.r_[cand[0], cand[cuts + 1]]
        ends = np.r_[cand[cuts], cand[-1]]
        changed = False
        for a, b in zip(starts, ends):
            a0, b0 = max(0, a - 96), min(n, b + 97)
            seg = np.concatenate([x[a0:b0] * (gain * g[a0:b0])[:, None] for x in signals], axis=1)
            tp = _true_peak_track(seg, os)[: b0 - a0]
            peaks, _ = signal.find_peaks(tp, height=ceil)
            for p in peaks:
                need = ceil / tp[p]
                c = a0 + p
                lo, hi = max(0, c - half_width), min(n, c + half_width + 1)
                dip = 1.0 - (1.0 - need * 0.9995) * win[lo - (c - half_width): hi - (c - half_width)]
                g[lo:hi] = np.minimum(g[lo:hi], dip)
                stats["dips"] += 1
                red = -20 * np.log10(need)
                stats["max_reduction_db"] = max(stats["max_reduction_db"], red)
                stats["events"].append((round(c / SR, 3), round(float(red), 2)))
                changed = True
        stats["passes"] += 1
        if not changed:
            break
    stats["events"] = sorted(stats["events"], key=lambda e: -e[1])[:12]
    return g, stats


def master(music, sfx, log, target=TARGET_LUFS, ceiling_db=CEILING_DB):
    """Returns (main, music_stem, sfx_stem, info); the two stems add up to main."""
    m = bus_eq(music)
    s = bus_eq(sfx)
    fade = fade_envelope(m.shape[0])[:, None]
    m *= fade
    s *= fade
    tot = m + s
    lufs0 = integrated_lufs(tot)
    g = 10 ** ((target - lufs0) / 20.0)
    info = dict(pre_lufs=float(lufs0), iterations=[])
    lim = np.ones(tot.shape[0])
    for it in range(8):
        lim, st = limiter_gain([tot, m, s], g, ceiling_db)
        z = tot * g * lim[:, None]
        L = integrated_lufs(z)
        info["iterations"].append(dict(gain_db=float(20 * np.log10(g)), lufs=float(L), limiter=st))
        log(f"  master pass {it + 1}: gain {20 * np.log10(g):+.2f} dB -> {L:.2f} LUFS, limiter dips {st['dips']}, max reduction {st['max_reduction_db']:.2f} dB")
        err = target - L
        if abs(err) < 0.03:
            break
        g *= 10 ** (err / 20.0)
    info["gain_db"] = float(20 * np.log10(g))
    info["limiter"] = st
    if st["events"]:
        log("  limiter: largest reductions (time s, dB): " + ", ".join(f"{t:g} s {r:.2f}" for t, r in st["events"][:6]))
    main = tot * g * lim[:, None]
    return main, m * g * lim[:, None], s * g * lim[:, None], info
