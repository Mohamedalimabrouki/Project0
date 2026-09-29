"""Small digital-signal-processing toolbox used by the music and the sound effects.

Everything here is plain numpy / scipy. Nothing random is left to chance: every noise
source is created with `rng_for(name, ...)`, which turns a text label into a fixed seed,
so the film sounds exactly the same every time the script runs.

Vocabulary (for readers who are not programmers)
  sample rate (SR)  how many numbers describe one second of sound: 48 000
  mono / stereo     one channel, or two channels (left, right) stored as an (n, 2) table
  filter            keeps some frequencies and removes others (low-pass keeps the lows)
  envelope          how the loudness of one sound changes with time (attack, decay ...)
  reverb            the echo of a room, made here by convolving with a synthetic room response
"""
from __future__ import annotations

import zlib

import numpy as np
from scipy import signal

SR = 48000
TAU = 2.0 * np.pi


# ----------------------------------------------------------------------------- basics
def db2lin(db):
    return 10.0 ** (np.asarray(db, dtype=float) / 20.0)


def lin2db(x, floor=1e-12):
    return 20.0 * np.log10(np.maximum(np.abs(x), floor))


def midi_hz(m):
    """Equal temperament, A4 (MIDI 69) = 440 Hz."""
    return 440.0 * 2.0 ** ((np.asarray(m, dtype=float) - 69.0) / 12.0)


def hz_midi(f):
    return 69.0 + 12.0 * np.log2(np.asarray(f, dtype=float) / 440.0)


def rng_for(*key):
    """A reproducible random generator named by its arguments (never Python's hash())."""
    seed = zlib.crc32("|".join(str(k) for k in key).encode("utf-8")) & 0xFFFFFFFF
    return np.random.default_rng(seed)


def idx(t):
    """Seconds -> sample index (rounded to the nearest sample)."""
    return int(round(float(t) * SR))


def nsamp(seconds):
    return int(round(float(seconds) * SR))


def tax(n, t0=0.0):
    """Time axis in seconds for n samples starting at t0."""
    return t0 + np.arange(n) / SR


# ----------------------------------------------------------------------------- envelopes
def ramp_up(n):
    """Raised-cosine ramp from exactly 0 towards 1 over n samples."""
    if n <= 0:
        return np.zeros(0)
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)


def ramp_down(n):
    if n <= 0:
        return np.zeros(0)
    return 0.5 + 0.5 * np.cos(np.pi * np.arange(n) / n)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def exp_decay(n, tau):
    """exp(-t / tau), tau in seconds."""
    return np.exp(-np.arange(n) / (SR * tau))


def fade_edges(x, fade_in=0.0, fade_out=0.0):
    """Apply raised-cosine fades to the ends of x (in place safe: returns new array)."""
    y = np.array(x, dtype=float, copy=True)
    n = y.shape[0]
    a = min(nsamp(fade_in), n)
    b = min(nsamp(fade_out), n)
    if a > 0:
        r = ramp_up(a)
        y[:a] *= r if y.ndim == 1 else r[:, None]
    if b > 0:
        r = ramp_down(b)
        y[n - b:] *= r if y.ndim == 1 else r[:, None]
    return y


def interp_curve(points, t, kind="linear"):
    """Value of a breakpoint curve [(time, value), ...] at times t.

    kind='linear' interpolates the values; kind='db' interpolates in decibels but
    returns a linear gain; kind='log' interpolates the logarithm (good for frequencies).
    """
    pts = sorted(points, key=lambda p: p[0])
    tt = np.array([p[0] for p in pts], dtype=float)
    vv = np.array([p[1] for p in pts], dtype=float)
    if kind == "log":
        return np.exp(np.interp(t, tt, np.log(vv)))
    out = np.interp(t, tt, vv)
    if kind == "db":
        return db2lin(out)
    return out


# ----------------------------------------------------------------------------- oscillators
def phase_from_freq(freq, phase0=0.0):
    """Phase in cycles at the start of every sample for a per-sample frequency array."""
    dt = np.asarray(freq, dtype=float) / SR
    return phase0 + np.cumsum(dt) - dt


def sine_f(freq, phase0=0.0):
    return np.sin(TAU * phase_from_freq(freq, phase0))


def saw_blep(freq, phase0=0.0):
    """Band-limited sawtooth (polyBLEP) for a per-sample frequency array.

    A plain saw folds its upper harmonics back into the audible range (aliasing, the very
    subject of this film), so the jump is smoothed with a two-sample polynomial.
    """
    freq = np.asarray(freq, dtype=float)
    dt = freq / SR
    ph = phase_from_freq(freq, phase0)
    ph -= np.floor(ph)
    y = 2.0 * ph - 1.0
    m1 = ph < dt
    if m1.any():
        t = ph[m1] / dt[m1]
        y[m1] -= t + t - t * t - 1.0
    m2 = ph > 1.0 - dt
    if m2.any():
        t = (ph[m2] - 1.0) / dt[m2]
        y[m2] -= t * t + t + t + 1.0
    return y


# ----------------------------------------------------------------------------- noise
def white(n, rng):
    return rng.standard_normal(n)


def pink(n, rng):
    """Pink noise (equal energy per octave), unit standard deviation."""
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1.0 / SR)
    f[0] = f[1] if len(f) > 1 else 1.0
    X = X / np.sqrt(f / f[1])
    y = np.fft.irfft(X, n)
    s = np.std(y)
    return y / (s if s > 0 else 1.0)


def brown(n, rng):
    x = np.cumsum(rng.standard_normal(n))
    x -= np.linspace(x[0], x[-1], n)
    s = np.std(x)
    return x / (s if s > 0 else 1.0)


# ----------------------------------------------------------------------------- filters
def butter_sos(kind, fc, order=2):
    return signal.butter(order, fc, btype=kind, fs=SR, output="sos")


def lp(x, fc, order=2, axis=0):
    return signal.sosfilt(butter_sos("lowpass", fc, order), x, axis=axis)


def hp(x, fc, order=2, axis=0):
    return signal.sosfilt(butter_sos("highpass", fc, order), x, axis=axis)


def bp(x, lo, hi, order=2, axis=0):
    return signal.sosfilt(butter_sos("bandpass", (lo, hi), order), x, axis=axis)


def onepole_lp(x, fc, axis=0):
    a = np.exp(-TAU * fc / SR)
    return signal.lfilter([1.0 - a], [1.0, -a], x, axis=axis)


def _rbj(kind, f, q):
    f = np.clip(np.asarray(f, dtype=float), 20.0, 0.45 * SR)
    w0 = TAU * f / SR
    cw, sw = np.cos(w0), np.sin(w0)
    alpha = sw / (2.0 * q)
    if kind == "lowpass":
        b0, b1, b2 = (1 - cw) / 2, 1 - cw, (1 - cw) / 2
    elif kind == "highpass":
        b0, b1, b2 = (1 + cw) / 2, -(1 + cw), (1 + cw) / 2
    elif kind == "bandpass":  # constant 0 dB peak gain
        b0, b1, b2 = alpha, 0 * alpha, -alpha
    else:
        raise ValueError(kind)
    a0, a1, a2 = 1 + alpha, -2 * cw, 1 - alpha
    return b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0


def tv_biquad(x, kind, f, q=0.8, block=32):
    """Filter with a cutoff that moves with time (f: one value per sample or a scalar).

    The coefficients are refreshed every `block` samples and the filter memory is carried
    across, which is smooth enough for sweeps such as a whoosh or a rising noise.
    """
    x = np.asarray(x, dtype=float)
    n = x.shape[0]
    f = np.broadcast_to(np.asarray(f, dtype=float), (n,))
    starts = np.arange(0, n, block)
    centres = np.minimum(starts + block // 2, n - 1)
    qv = np.broadcast_to(np.asarray(q, dtype=float), (n,))[centres]
    b0, b1, b2, a1, a2 = _rbj(kind, f[centres], qv)
    y = np.empty_like(x)
    zi = np.zeros((2,) + x.shape[1:])
    for k, s in enumerate(starts):
        e = min(s + block, n)
        seg, zi = signal.lfilter([b0[k], b1[k], b2[k]], [1.0, a1[k], a2[k]], x[s:e], axis=0, zi=zi)
        y[s:e] = seg
    return y


def filterbank_morph(x, fc_curve, cutoffs=None, order=4, axis=0):
    """Low-pass whose cutoff follows a curve, built by cross-fading fixed low-pass copies.

    Cheap and smooth for long pads: the signal is low-passed at a ladder of cutoffs (about a
    third of an octave apart) and the two neighbours of the wanted cutoff are blended in
    proportion (on a log-frequency scale).
    """
    if cutoffs is None:
        cutoffs = 150.0 * 2.0 ** (np.arange(0, 17) / 3.0)  # 150 Hz ... ~ 6.4 kHz
    cutoffs = np.asarray(cutoffs, dtype=float)
    lc = np.log(cutoffs)
    target = np.log(np.clip(fc_curve, cutoffs[0], cutoffs[-1]))
    pos = np.interp(target, lc, np.arange(len(cutoffs)))
    lo_i = np.clip(np.floor(pos).astype(int), 0, len(cutoffs) - 2)
    frac = pos - lo_i
    out = np.zeros_like(x, dtype=float)
    for j in range(len(cutoffs)):
        w = np.where(lo_i == j, 1.0 - frac, 0.0) + np.where(lo_i == j - 1, frac, 0.0)
        if not np.any(w):
            continue
        yj = signal.sosfilt(butter_sos("lowpass", cutoffs[j], order), x, axis=axis)
        out += yj * (w if x.ndim == 1 else w[:, None])
    return out


# ----------------------------------------------------------------------------- stereo
def pan_gains(pan):
    """Constant-power pan law: pan -1 (left) .. +1 (right). Centre is 0.7071 on each side."""
    th = (float(np.clip(pan, -1.0, 1.0)) + 1.0) * np.pi / 4.0
    return np.cos(th), np.sin(th)


def to_stereo(x, pan=0.0):
    x = np.asarray(x, dtype=float)
    if x.ndim == 2:
        gl, gr = pan_gains(pan)
        return np.stack([x[:, 0] * gl * np.sqrt(2.0), x[:, 1] * gr * np.sqrt(2.0)], axis=1)
    gl, gr = pan_gains(pan)
    return np.stack([x * gl, x * gr], axis=1)


def mid_side(x):
    m = 0.5 * (x[:, 0] + x[:, 1])
    s = 0.5 * (x[:, 0] - x[:, 1])
    return m, s


def from_mid_side(m, s):
    return np.stack([m + s, m - s], axis=1)


def mono_below(x, fc=160.0):
    """Make everything under fc mono (the side signal is high-passed)."""
    m, s = mid_side(x)
    s = hp(s, fc, order=2)
    return from_mid_side(m, s)


# ----------------------------------------------------------------------------- reverb
def make_reverb_ir(rt60=(3.0, 2.4, 1.2), split=(280.0, 3200.0), length=3.2, predelay=0.028,
                   lp_hz=7000.0, hp_hz=140.0, seed="hall", early=True, onset=0.025):
    """A synthetic stereo room response: decaying noise, longer decay for lows than for highs.

    rt60 is the time in seconds for each band to fall by 60 dB (low, mid, high band).
    Returns an (n, 2) array whose total energy is 1 per channel, so that a "send" of 1
    gives a wet signal of about the same loudness as the dry one.
    """
    n = nsamp(length)
    t = np.arange(n) / SR
    out = np.zeros((n, 2))
    for ch in range(2):
        rng = rng_for("ir", seed, ch)
        w = rng.standard_normal(n)
        lo = lp(w, split[0], 2)
        mid = bp(w, split[0], split[1], 2)
        hi = hp(w, split[1], 2)
        k = 6.907755 / np.asarray(rt60, dtype=float)  # ln(1000): -60 dB
        tail = lo * np.exp(-k[0] * t) + mid * np.exp(-k[1] * t) + hi * np.exp(-k[2] * t)
        tail *= 1.0 - np.exp(-t / onset)
        if early:
            er = np.zeros(n)
            tps = rng.uniform(0.004, 0.075, 14)
            amps = rng.uniform(0.35, 1.0, 14) * np.exp(-tps / 0.03) * rng.choice([-1, 1], 14)
            for tp, a in zip(tps, amps):
                er[int(tp * SR)] += a
            er = lp(er, 5500, 2)
            tail = tail * 0.55 + er * 0.9 * np.std(tail[: nsamp(0.4)]) * 3.0
        d = nsamp(predelay + 0.0015 * ch)
        y = np.concatenate([np.zeros(d), tail])[:n]
        y = lp(y, lp_hz, 2)
        y = hp(y, hp_hz, 2)
        out[:, ch] = y
    out /= np.sqrt(np.sum(out ** 2, axis=0, keepdims=True))
    return out


def convolve_ir(x, ir, out_len=None):
    """Convolve a mono or stereo signal with a stereo impulse response (true stereo out)."""
    n = x.shape[0] if out_len is None else out_len
    if x.ndim == 1:
        xm = x
    else:
        xm = 0.5 * (x[:, 0] + x[:, 1])
    wet = np.zeros((n, 2))
    for ch in range(2):
        y = signal.oaconvolve(xm, ir[:, ch], mode="full")[:n]
        wet[: len(y), ch] = y
    if x.ndim == 2:
        # keep some of the input's own stereo image: wet L/R also see the difference signal
        side = 0.5 * (x[:, 0] - x[:, 1])
        for ch, sgn in ((0, 1.0), (1, -1.0)):
            y = signal.oaconvolve(side, ir[:, 1 - ch], mode="full")[:n]
            wet[: len(y), ch] += sgn * 0.6 * y
    return wet


# ----------------------------------------------------------------------------- bus helpers
def place(bus, x, start, gain=1.0):
    """Add x (mono or stereo, matching bus) into bus at sample `start` (clipped to the bus)."""
    n = x.shape[0]
    a = max(0, start)
    b = min(bus.shape[0], start + n)
    if b <= a:
        return
    seg = x[a - start: b - start]
    if gain != 1.0:
        seg = seg * gain
    bus[a:b] += seg


def peak_db(x):
    return float(lin2db(np.max(np.abs(x))))


def rms_db(x):
    return float(lin2db(np.sqrt(np.mean(np.square(x)))))


def true_peak_db(x, oversample=8):
    """Sample peak of the oversampled signal (approximates the continuous-time peak)."""
    x = np.atleast_2d(x.T).T if x.ndim == 1 else x
    peak = 0.0
    step = SR * 10
    pad = 64
    for ch in range(x.shape[1]):
        for s in range(0, x.shape[0], step):
            a, b = max(0, s - pad), min(x.shape[0], s + step + pad)
            y = signal.resample_poly(x[a:b, ch], oversample, 1)
            ya, yb = (s - a) * oversample, (min(x.shape[0], s + step) - a) * oversample
            peak = max(peak, float(np.max(np.abs(y[ya:yb]))))
    return float(lin2db(peak))
