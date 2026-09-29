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


def fade_envelope(n, fade_in=0.35, out_start=177.0, out_end=179.5):
    """1 in the middle, a raised-cosine fade in at the start, a fade out that ends in exact silence."""
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


def limiter_gain(x, ceiling_db=CEILING_DB, half_width=2400, iterations=4, os=8):
    """Gain curve (one value per sample) that keeps the true peak of x * gain under the ceiling.

    Wherever the oversampled signal pokes above the ceiling, a smooth raised-cosine dip (50 ms each
    side) is pressed into the gain, just deep enough. Elsewhere the gain is exactly 1.
    """
    ceil = 10 ** (ceiling_db / 20.0)
    n = x.shape[0]
    g = np.ones(n)
    win = 0.5 * (1.0 + np.cos(np.pi * np.arange(-half_width, half_width + 1) / half_width))
    stats = dict(passes=0, dips=0, max_reduction_db=0.0)
    for _ in range(iterations):
        y = x * g[:, None]
        pk = np.max(np.abs(y), axis=1)
        cand = np.where(pk > ceil * 0.70)[0]
        if len(cand) == 0:
            break
        # group candidates into regions
        cuts = np.where(np.diff(cand) > 4096)[0]
        starts = np.r_[cand[0], cand[cuts + 1]]
        ends = np.r_[cand[cuts], cand[-1]]
        changed = False
        for a, b in zip(starts, ends):
            a0, b0 = max(0, a - 96), min(n, b + 97)
            tp = _true_peak_track(y[a0:b0], os)[: b0 - a0]
            peaks, _ = signal.find_peaks(tp, height=ceil)
            for p in peaks:
                need = ceil / tp[p]
                c = a0 + p
                lo, hi = max(0, c - half_width), min(n, c + half_width + 1)
                dip = 1.0 - (1.0 - need * 0.9995) * win[lo - (c - half_width): hi - (c - half_width)]
                g[lo:hi] = np.minimum(g[lo:hi], dip * (g[lo:hi] > 0))
                stats["dips"] += 1
                stats["max_reduction_db"] = max(stats["max_reduction_db"], -20 * np.log10(need))
                changed = True
        stats["passes"] += 1
        if not changed:
            break
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
        y = tot * g
        lim, st = limiter_gain(y, ceiling_db)
        z = y * lim[:, None]
        L = integrated_lufs(z)
        info["iterations"].append(dict(gain_db=float(20 * np.log10(g)), lufs=float(L), limiter=st))
        log(f"  master pass {it + 1}: gain {20 * np.log10(g):+.2f} dB -> {L:.2f} LUFS, limiter dips {st['dips']}, max reduction {st['max_reduction_db']:.2f} dB")
        err = target - L
        if abs(err) < 0.03:
            break
        g *= 10 ** (err / 20.0)
    info["gain_db"] = float(20 * np.log10(g))
    info["limiter"] = st
    main = tot * g * lim[:, None]
    return main, m * g * lim[:, None], s * g * lim[:, None], info
