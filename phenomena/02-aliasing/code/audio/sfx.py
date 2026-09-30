"""The sound-effect vocabulary of the film (SCENE_GUIDE.md section 11), all built from maths.

Every function makes ONE sound and returns a `Sound`:
  audio    (n, 2) stereo array, already scaled to a nominal level (see LEVELS)
  send     how much of it goes to the room reverb (0 = dry)
  anchor   the sample (from the start of `audio`) where "the moment" of the sound is:
           0 for clicks and hits (the moment is the start), the end of the swell for
           `swoosh_rev` and `riser` (they build up and land on the cue time + dur)
  kind     'impulse', 'swell' or 'bed', used when checking cue placement

Pitched sounds (pop, blip, glitch, hit, shimmer, riser, motor) take their notes from the
chord the music is playing at that moment, so they can never clash with it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import signal

import dsp
from dsp import SR, nsamp, midi_hz, rng_for, ramp_up, ramp_down

# -------------------------------------------------------------------------- the cue record


@dataclass
class Cue:
    t: float                    # absolute time in the film (s)
    sfx: str
    dur: float | None = None
    gain: float = 0.0           # dB
    pan: float = 0.0            # -1 .. 1
    rate: float | None = None   # turns per second (whirr) or blade passes per second (rotor)
    scene: str = ""
    index: int = 0              # running number among the cues of the same name
    extra: dict = field(default_factory=dict)


@dataclass
class Sound:
    audio: np.ndarray
    send: float = 0.0
    anchor: int = 0
    kind: str = "impulse"
    duration: float = 0.0       # nominal length in seconds (dur, or the natural length)


# nominal levels: ('peak' | 'rms', dBFS) in the pre-master mix, where the music alone sits
# around -17 LUFS. The master stage then lifts everything together to -14 LUFS.
LEVELS = {
    "shutter": ("peak", -13.0),
    "tick": ("peak", -18.0),
    "pop": ("peak", -15.0),
    "blip": ("peak", -19.0),
    "click": ("peak", -16.0),
    "glitch": ("peak", -17.0),
    "whoosh": ("peak", -14.5),
    "swoosh_rev": ("peak", -13.5),
    "riser": ("peak", -13.5),
    "hit": ("peak", -9.0),
    "shimmer": ("rms", -28.5),
    "whirr": ("rms", -28.5),
    "car": ("rms", -26.5),
    "rotor": ("rms", -25.5),
    "hum": ("rms", -38.0),
    "motor": ("rms", -31.5),
}

# how strongly each sound draws attention (used to duck the music), and for how long a
# short sound is considered "present" (seconds); None = the whole duration of the cue
DUCK_WEIGHT = {
    "shutter": (0.30, 0.25), "tick": (0.20, 0.20), "pop": (0.25, 0.25), "blip": (0.20, 0.20),
    "click": (0.25, 0.20), "glitch": (0.55, 0.30), "whoosh": (0.55, None), "swoosh_rev": (0.60, None),
    "riser": (0.60, None), "hit": (0.85, 0.60), "shimmer": (0.35, None), "whirr": (0.25, None),
    "car": (0.12, None), "rotor": (0.30, None), "hum": (0.10, None), "motor": (0.20, None),
}

DEFAULT_DUR = {"whoosh": 0.7, "swoosh_rev": 0.8, "riser": 3.0, "shimmer": 2.5, "whirr": 3.0,
               "car": 6.0, "rotor": 3.0, "hum": 3.0, "motor": 2.0}

# ------------------------------------------------------------------------------- helpers


def _damped(f, tau, n, phase=0.0):
    t = np.arange(n) / SR
    return np.sin(dsp.TAU * f * t + phase) * np.exp(-t / tau)


def _noise_burst(n, lo, hi, tau, rng, order=2):
    w = rng.standard_normal(n + 256)
    w = dsp.bp(w, lo, hi, order)[256:]
    w /= np.std(w) + 1e-12
    return w * np.exp(-np.arange(n) / (SR * tau))


def _mono(x, send=0.0, anchor=0, kind="impulse", duration=0.0):
    return Sound(np.stack([x, x], axis=1), send, anchor, kind, duration or len(x) / SR)


def _stereo(l, r, send=0.0, anchor=0, kind="impulse", duration=0.0):
    return Sound(np.stack([l, r], axis=1), send, anchor, kind, duration or len(l) / SR)


def _env_cos(n, fade_in, fade_out):
    e = np.ones(n)
    a, b = min(nsamp(fade_in), n), min(nsamp(fade_out), n)
    if a:
        e[:a] = ramp_up(a)
    if b:
        e[n - b:] *= ramp_down(b)
    return e


def _pick(ctx, t, lo, hi, index=0):
    """A chord tone (MIDI number) between lo and hi, choosing by index (cycles upwards)."""
    tones = ctx.tones(t, lo, hi)
    return tones[index % len(tones)]


# ------------------------------------------------------------------------ clicks and blips


def shutter(c: Cue, ctx):
    """Camera shutter: two short filtered-noise clicks 40 ms apart and a tiny mechanical ring."""
    rng = rng_for("shutter", c.index)
    n = nsamp(0.17)
    y = np.zeros(n)
    var = 1.0 + 0.04 * rng.standard_normal()

    def click(t0, amp, lo, hi, tau, ring):
        i0 = nsamp(t0)
        m = nsamp(0.035)
        b = _noise_burst(m, lo, hi, tau, rng)
        b *= np.minimum(1.0, np.arange(m) / (0.0004 * SR))     # 0.4 ms rise: sharp but not a pop
        y[i0:i0 + m] += amp * b
        for f, tr, a in ring:
            y[i0:i0 + m] += amp * a * _damped(f * var, tr, m)

    click(0.000, 1.00, 1700, 6500, 0.0022, [(1150, 0.011, 0.34), (2650, 0.006, 0.20), (4300, 0.004, 0.08)])
    click(0.040, 0.70, 1100, 4300, 0.0030, [(830, 0.012, 0.30), (1900, 0.007, 0.16)])
    # tiny mechanical body resonance after the second click, and the mirror "thunk" under the first
    i = nsamp(0.043)
    m = n - i
    y[i:] += 0.10 * (_damped(310 * var, 0.028, m) + 0.6 * _damped(742 * var, 0.02, m))
    y[:nsamp(0.06)] += 0.22 * _damped(142 * var, 0.013, nsamp(0.06))
    y = dsp.lp(y, 9000, 2)
    return _mono(y, send=0.05)


def tick(c: Cue, ctx):
    """Soft clock tick (alternating a slightly higher 'tick' and lower 'tock')."""
    rng = rng_for("tick", c.index)
    f1 = 1780.0 if c.index % 2 == 0 else 1390.0
    n = nsamp(0.10)
    y = _damped(f1, 0.0065, n) + 0.42 * _damped(f1 * 1.83, 0.004, n) + 0.16 * _damped(f1 * 2.91, 0.0025, n)
    y += 0.35 * _noise_burst(n, 2200, 5200, 0.0009, rng)
    y = dsp.lp(y, 5600, 2)
    y *= np.minimum(1.0, np.arange(n) / (0.0005 * SR))
    return _mono(y, send=0.04)


def pop(c: Cue, ctx):
    """Soft UI pop: a short sine 'bloop' that rises into a chord tone, plus a tiny click."""
    rng = rng_for("pop", c.index)
    f0 = midi_hz(_pick(ctx, c.t, 69, 81, c.index))
    n = nsamp(0.22)
    t = np.arange(n) / SR
    f = f0 * (1.0 - 0.30 * np.exp(-t / 0.014))
    env = (1.0 - np.exp(-t / 0.0022)) * np.exp(-t / 0.048)
    y = (np.sin(dsp.TAU * np.cumsum(f) / SR) + 0.22 * np.sin(dsp.TAU * 2 * np.cumsum(f) / SR)) * env
    y += 0.08 * _noise_burst(n, 1500, 4000, 0.0008, rng)
    y = dsp.lp(y, 6500, 2)
    return _mono(y, send=0.18)


def blip(c: Cue, ctx):
    """Tiny high blip (a sample dot, a graph point): a chord tone two to three octaves up."""
    f0 = midi_hz(_pick(ctx, c.t, 84, 96, c.index))
    n = nsamp(0.10)
    t = np.arange(n) / SR
    f = f0 * (1.0 + 0.012 * np.exp(-t / 0.01))
    ph = dsp.TAU * np.cumsum(f) / SR
    env = (1.0 - np.exp(-t / 0.0012)) * np.exp(-t / 0.0115)
    y = (np.sin(ph) + 0.10 * np.sin(3 * ph)) * env
    return _mono(dsp.lp(y, 7000, 2), send=0.22)


def click(c: Cue, ctx):
    """Small switch click: a tiny two-stage 'k-tick' with a short plastic body."""
    rng = rng_for("click", c.index)
    n = nsamp(0.09)
    y = np.zeros(n)
    b = _noise_burst(nsamp(0.02), 2000, 6500, 0.0012, rng)
    y[: len(b)] += b
    i2 = nsamp(0.009)
    b2 = _noise_burst(nsamp(0.02), 1400, 5000, 0.0016, rng)
    y[i2:i2 + len(b2)] += 0.55 * b2
    y += 0.5 * _damped(1320, 0.0055, n)
    y[i2:] += 0.35 * _damped(430, 0.010, n - i2)
    y = dsp.lp(y, 7500, 2)
    return _mono(y, send=0.05)


# --------------------------------------------------------------------- air and movement


def whoosh(c: Cue, ctx):
    """Soft air movement: noise through a band-pass that glides upwards while it slides past."""
    dur = c.dur or DEFAULT_DUR["whoosh"]
    n = nsamp(dur)
    u = np.arange(n) / n
    chans = []
    for ch in range(2):
        x = dsp.pink(n, rng_for("whoosh", c.index, ch))
        fc = 320.0 * (2900.0 / 320.0) ** (u ** 1.25)
        y = dsp.tv_biquad(x, "bandpass", fc, 1.05)
        y = dsp.tv_biquad(y, "bandpass", fc * 1.08, 0.9)
        y += 0.10 * dsp.bp(x, 110, 260)                  # a little body underneath
        y += 0.10 * dsp.bp(x, 3800, 8200) * u            # a breath of air at the end
        y = dsp.hp(y, 110, 2)
        chans.append(y)
    env = np.sin(np.pi * u ** 0.72) ** 2
    l, r = chans[0] * env, chans[1] * env
    # gentle left-to-right travel on top of the cue's own pan
    p = np.clip(c.pan + 0.18 * (2.0 * u - 1.0), -1, 1)
    th = (p + 1.0) * np.pi / 4.0
    l, r = l * np.cos(th) * np.sqrt(2), r * np.sin(th) * np.sqrt(2)
    return _stereo(l, r, send=0.16, kind="swell", duration=dur)


def swoosh_rev(c: Cue, ctx):
    """Reversed whoosh: it swells and lands exactly at cue time + dur (the peak is at the end)."""
    dur = c.dur or DEFAULT_DUR["swoosh_rev"]
    n = nsamp(dur)
    u = np.arange(n) / n
    chans = []
    for ch in range(2):
        x = dsp.pink(n, rng_for("swoosh_rev", c.index, ch))
        fc = 240.0 * (3600.0 / 240.0) ** (u ** 0.85)
        y = dsp.tv_biquad(x, "bandpass", fc, 0.95)
        y = dsp.tv_biquad(y, "bandpass", fc * 1.1, 0.85)
        y += 0.12 * dsp.bp(x, 3600, 8200) * u ** 2
        y = dsp.hp(y, 110, 2)
        chans.append(y)
    fall = min(nsamp(0.028), n // 4)
    env = u ** 2.3
    env[n - fall:] *= ramp_down(fall)          # soft landing, no click
    l, r = chans[0] * env, chans[1] * env
    p = np.clip(c.pan + 0.12 * (1.0 - 2.0 * u), -1, 1)
    th = (p + 1.0) * np.pi / 4.0
    l, r = l * np.cos(th) * np.sqrt(2), r * np.sin(th) * np.sqrt(2)
    return _stereo(l, r, send=0.10, anchor=n, kind="swell", duration=dur)


def riser(c: Cue, ctx):
    """Rising tension: a noise band and a detuned tone that both climb, ending on a chord tone."""
    dur = c.dur or DEFAULT_DUR["riser"]
    n = nsamp(dur)
    u = np.arange(n) / n
    t = u * dur
    end_pc_note = _pick(ctx, c.t + dur + 0.05, 62, 76, 0)      # target: a chord tone of the arrival chord
    f_end = midi_hz(end_pc_note)
    f_start = f_end / 4.0
    f = f_start * (f_end / f_start) ** (u ** 1.15)
    chans = []
    for ch, det in enumerate((-6.0, 6.0)):
        rng = rng_for("riser", c.index, ch)
        x = dsp.pink(n, rng)
        fc = 260.0 * (3800.0 / 260.0) ** (u ** 1.3)
        noise = dsp.tv_biquad(x, "bandpass", fc, 1.1)
        noise = dsp.lp(noise, 7000, 2)
        tone = dsp.saw_blep(f * 2 ** (det / 1200.0)) + dsp.saw_blep(f * 2 ** ((det * 0.4) / 1200.0) * 1.0005)
        tone = dsp.lp(tone, 2400, 4)
        rate = 3.0 + 11.0 * u ** 1.5
        trem = 1.0 - 0.16 * (0.5 + 0.5 * np.sin(dsp.TAU * np.cumsum(rate) / SR))
        chans.append((0.55 * noise + 0.75 * tone) * trem)
    env = u ** 2.1
    fall = min(nsamp(0.02), n // 8)
    env[n - fall:] *= ramp_down(fall)
    return _stereo(chans[0] * env, chans[1] * env, send=0.20, anchor=n, kind="swell", duration=dur)


def hit(c: Cue, ctx):
    """Deep soft impact: a sine that drops onto the chord root, soft filtered noise, a dark tail."""
    n = nsamp(3.0)
    t = np.arange(n) / SR
    root = ctx.root_midi(c.t, 33, 42)             # the chord's root, between A1 and F#2
    f_end = float(midi_hz(root))
    f = f_end * (1.0 + 1.35 * np.exp(-t / 0.045))
    ph = dsp.TAU * np.cumsum(f) / SR
    amp = (1.0 - np.exp(-t / 0.004)) * (0.75 * np.exp(-t / 0.55) + 0.25 * np.exp(-t / 1.4))
    sub = (np.sin(ph) * amp
           + 0.34 * np.sin(2 * ph) * (1.0 - np.exp(-t / 0.004)) * np.exp(-t / 0.20)
           + 0.13 * np.sin(3 * ph) * (1.0 - np.exp(-t / 0.004)) * np.exp(-t / 0.10))
    rng = rng_for("hit", c.index)
    body = dsp.lp(dsp.pink(n, rng), 380, 2) * np.exp(-t / 0.10) * 0.55
    air = dsp.bp(dsp.white(n, rng), 800, 3200, 2) * np.exp(-t / 0.030) * 0.075
    y = sub + body + air
    y = dsp.lp(y, 5000, 2)
    y[: nsamp(0.0015)] *= np.linspace(0, 1, nsamp(0.0015))
    y[-nsamp(0.6):] *= ramp_down(nsamp(0.6))                # the tail dies away smoothly, never cut
    return _mono(y, send=0.30, kind="impulse", duration=3.0)


def shimmer(c: Cue, ctx):
    """Glassy shimmer for a frozen moment: detuned high sines on chord tones, slow swell and decay."""
    dur = c.dur or DEFAULT_DUR["shimmer"]
    n_tot = nsamp(dur)
    t = np.arange(n_tot) / SR
    u = t / dur
    tones = ctx.tones(c.t + 0.2, 74, 100)
    rng = rng_for("shimmer", c.index)
    L = np.zeros(n_tot)
    R = np.zeros(n_tot)
    for k, m in enumerate(tones[:9]):
        f = float(midi_hz(m))
        if f > 3600.0:
            continue
        for det in (-4.0, 0.0, 5.0):
            fr = f * 2 ** (det / 1200.0)
            rate = rng.uniform(0.35, 1.3)
            ph0 = rng.uniform(0, dsp.TAU)
            trem = 0.5 + 0.5 * np.sin(dsp.TAU * rate * t + ph0)
            trem = 0.20 + 0.80 * trem ** 1.5
            tw = dsp.lp(rng.standard_normal(n_tot), 5.5, 2)          # random twinkle, a few times a second
            tw = np.clip(0.55 + 1.15 * tw / (np.std(tw) + 1e-12), 0.0, 1.0) ** 2
            s = np.sin(dsp.TAU * fr * t + rng.uniform(0, dsp.TAU)) * trem * (0.30 + 0.70 * tw)
            amp = (1.0 / (1.0 + 0.45 * k)) * (0.5 if det == 0.0 else 0.35)
            pan = rng.uniform(-0.85, 0.85)
            gl, gr = dsp.pan_gains(pan)
            L += s * amp * gl * np.sqrt(2)
            R += s * amp * gr * np.sqrt(2)
    swell = np.sin(np.pi * np.clip(u / 0.42, 0, 1) / 2.0) ** 2
    decay = np.where(u < 0.42, 1.0, np.cos(np.pi * np.clip((u - 0.42) / 0.58, 0, 1) / 2.0) ** 2)
    env = swell * decay
    return _stereo(L * env, R * env, send=0.45, kind="swell", duration=dur)


def glitch(c: Cue, ctx):
    """A 150 ms digital stutter: a 25 ms grain repeated six times, pitch-stepped and bit-crushed."""
    n = nsamp(0.15)
    grain = nsamp(0.025)
    rng = rng_for("glitch", c.index)
    base = float(midi_hz(_pick(ctx, c.t, 79, 91, c.index)))
    ratios = [1.0, 1.5, 0.75, 2.0, 1.0, 1.3333]
    gates = [1.0, 0.95, 0.6, 0.9, 0.7, 0.45]
    L = np.zeros(n)
    R = np.zeros(n)
    for k in range(6):
        g = np.arange(grain) / SR
        f = base * ratios[k]
        s = np.sin(dsp.TAU * f * g) + 0.35 * np.sin(dsp.TAU * 2 * f * g + 0.7)
        s += 0.10 * (rng.standard_normal(grain))
        s *= np.minimum(1.0, np.arange(grain) / (0.0015 * SR)) * np.minimum(1.0, (grain - np.arange(grain)) / (0.002 * SR))
        # bit-crush (6 bits) and sample-and-hold at 12 kHz: a small, deliberate act of aliasing
        s = np.round(s * 24.0) / 24.0
        hold = 4
        s = np.repeat(s[::hold], hold)[:grain]
        seg = s * gates[k]
        i0 = k * grain
        pan = 0.55 if k % 2 == 0 else -0.55
        gl, gr = dsp.pan_gains(pan)
        L[i0:i0 + grain] += seg * gl * np.sqrt(2)
        R[i0:i0 + grain] += seg * gr * np.sqrt(2)
    fade = ramp_down(nsamp(0.03))
    L[-len(fade):] *= fade
    R[-len(fade):] *= fade
    L, R = dsp.lp(L, 5200, 4), dsp.lp(R, 5200, 4)
    return _stereo(L, R, send=0.12, duration=0.15)


# ------------------------------------------------------------------ machines and vehicles


# wheel rate (turns per second) versus time for each scene that has a car: the same keys as the scene code
RATE_KEYS = {
    "s01_hook": [(0.0, 0.35), (4.5, 2.0), (6.8, 4.7), (10.2, 5.86), (11.4, 6.0), (13.4, 6.0), (16.8, 6.25), (18.5, 6.25)],
    "short_hook": [(0.0, 0.35), (3.5, 2.0), (5.5, 4.7), (8.5, 5.86), (9.5, 6.0), (12.0, 6.0), (15.0, 6.25), (17.0, 6.25)],
}


def _rate_curve(t, keys):
    """The scenes' monotone cubic interpolation (Fritsch-Carlson, zero slope at both ends)."""
    xs = np.array([k[0] for k in keys])
    ys = np.array([k[1] for k in keys])
    h = np.diff(xs)
    m = np.diff(ys) / h
    d = np.zeros(len(xs))
    for i in range(1, len(xs) - 1):
        if m[i - 1] * m[i] <= 0:
            d[i] = 0.0
        else:
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            d[i] = (w1 + w2) / (w1 / m[i - 1] + w2 / m[i])
    t = np.asarray(t, dtype=float)
    tc = np.clip(t, xs[0], xs[-1])
    k = np.clip(np.searchsorted(xs, tc, side="right") - 1, 0, len(xs) - 2)
    u = (tc - xs[k]) / h[k]
    u2, u3 = u * u, u * u * u
    return ((2 * u3 - 3 * u2 + 1) * ys[k] + (u3 - 2 * u2 + u) * h[k] * d[k]
            + (-2 * u3 + 3 * u2) * ys[k + 1] + (u3 - u2) * h[k] * d[k + 1])


def _rate_for(c, t_abs):
    """Wheel rate for a car cue: its own `rate` if given, else the ramp of its scene (film time), else
    the hook ramp counted from the cue's own start."""
    if c.rate:
        return np.full(len(t_abs), float(c.rate))
    if c.scene in RATE_KEYS:
        return _rate_curve(t_abs, RATE_KEYS[c.scene])
    return _rate_curve(t_abs - c.t, RATE_KEYS["s01_hook"])


# firing frequency of the engine (Hz) = A + B * wheel rate; chosen so that the frozen moment
# (6.0 turns/s) lands on F3 = 174.61 Hz, the root of the suspended chord the music holds there
_ENGINE_B = 24.5
_ENGINE_A = 174.6141 - _ENGINE_B * 6.0


def car(c: Cue, ctx):
    """A car driving: engine orders whose pitch follows the hook's speed ramp, plus tyre noise."""
    dur = c.dur or DEFAULT_DUR["car"]
    n = nsamp(dur)
    t_abs = c.t + np.arange(n) / SR
    rate = _rate_for(c, t_abs)
    ff = _ENGINE_A + _ENGINE_B * rate                     # firing frequency, Hz
    phi = np.cumsum(ff / SR)                              # firing-cycle phase (cycles)
    orders = [(0.5, 1.0), (1.0, 1.0), (1.5, 0.7), (2.0, 0.85), (2.5, 0.25), (3.0, 0.6), (3.5, 0.10),
              (4.0, 0.40), (4.5, 0.12), (5.0, 0.28), (6.0, 0.20), (7.0, 0.10), (8.0, 0.07)]
    fc = 420.0 + 105.0 * rate                             # the exhaust note brightens with revs
    rng = rng_for("car", c.index)
    rough = dsp.lp(rng.standard_normal(n), 9.0, 2)
    rough /= np.std(rough) + 1e-12
    eng = np.zeros(n)
    for h, w in orders:
        fh = h * ff
        a = w * h ** -0.55 / np.sqrt(1.0 + (fh / fc) ** 4)
        a = a * (fh < 0.45 * SR)
        eng += a * np.sin(dsp.TAU * h * phi + 0.9 * h)
    eng *= 1.0 + 0.05 * rough                              # a little lumpiness
    load = 0.55 + 0.45 * np.clip(rate / 6.25, 0, 1)
    eng *= load
    eng = dsp.hp(eng, 25, 2)
    v = np.clip(rate / 6.25, 0.0, 1.0)                     # speed as a fraction of the top speed
    road = dsp.bp(dsp.pink(n, rng_for("car-road", c.index)), 90, 950, 2)
    road /= np.std(road) + 1e-12
    hiss = dsp.bp(dsp.white(n, rng_for("car-hiss", c.index)), 1400, 4200, 2)
    hiss /= np.std(hiss) + 1e-12
    tyre = road * 0.42 * v ** 1.4 + hiss * 0.035 * v ** 2.0
    y = eng / (np.std(eng) + 1e-12) * 0.85 + tyre
    y *= _env_cos(n, 0.6, 0.7)
    # slight stereo width from two decorrelated noise floors; the engine itself is central
    wl = dsp.lp(dsp.pink(n, rng_for("car-wl", c.index)), 900, 2)
    wr = dsp.lp(dsp.pink(n, rng_for("car-wr", c.index)), 900, 2)
    wl /= np.std(wl) + 1e-12
    wr /= np.std(wr) + 1e-12
    e = _env_cos(n, 0.6, 0.7)
    return _stereo(y + 0.10 * wl * v * e, y + 0.10 * wr * v * e, send=0.0, kind="bed", duration=dur)


def whirr(c: Cue, ctx):
    """A spinning machine: filtered noise plus harmonics of the rotation rate.

    A wheel with five identical spokes repeats itself five times per turn, so its sound is periodic at
    five times the rotation rate (the same "N times f_r" as in the film). The tone is therefore a comb of
    lines spaced 5 x rate apart (plus a weaker comb at the rotation rate itself, for the small
    differences between spokes), with random but fixed phases and a smooth spectral shape. No single
    line stands out, so the whirr is a soft rough hum with no pitch of its own to clash with the music.
    """
    dur = c.dur or DEFAULT_DUR["whirr"]
    n = nsamp(dur)
    t = np.arange(n) / SR
    r = float(c.rate) if c.rate else 5.0
    r_to = float(c.extra.get("rate_to", r))
    rr = r + (r_to - r) * np.clip(t / dur, 0, 1)
    phase = np.cumsum(rr / SR)                               # turns
    rng = rng_for("whirr", c.index)
    tone = np.zeros(n)
    f0 = 300.0                                                # centre of the soft spectral hump
    kmax = int(min(1500.0, 0.4 * SR) / max(r, 0.05) / 1.0)
    kmax = min(kmax, 400)
    for k in range(1, kmax + 1):
        fk = k * rr                                           # harmonic k of the rotation rate
        spoke = (k % 5 == 0)
        w = (fk / f0) / (1.0 + (fk / f0) ** 2) ** 1.2         # hump: weak at very low pitch, gentle fall above
        a_k = w * (1.0 if spoke else 0.28) * (fk < 1500.0)
        if not np.any(a_k > 1e-4):
            continue
        tone += a_k * np.sin(dsp.TAU * k * phase + rng.uniform(0, dsp.TAU))
    tone = dsp.hp(tone, 45, 2)
    tone /= np.std(tone) + 1e-12
    nz = dsp.bp(dsp.pink(n, rng), 380, 1900, 2)
    nz /= np.std(nz) + 1e-12
    # the rotation also shows up as a gentle pulsing at the turning rate (and at 5x for five spokes)
    pulse = 1.0 + 0.20 * np.cos(dsp.TAU * phase) + 0.07 * np.cos(dsp.TAU * 5 * phase + 0.6)
    y = (0.80 * tone + 0.42 * nz) * pulse
    y = dsp.hp(y, 45, 2) * _env_cos(n, 0.28, 0.40)
    e = _env_cos(n, 0.28, 0.4)
    l = y + 0.10 * dsp.lp(dsp.pink(n, rng_for("whirr-l", c.index)), 1300, 2) * e
    rgt = y + 0.10 * dsp.lp(dsp.pink(n, rng_for("whirr-r", c.index)), 1300, 2) * e
    return _stereo(l, rgt, send=0.06, kind="bed", duration=dur)


def rotor(c: Cue, ctx):
    """Helicopter rotor chop: a train of low thumps and blade slaps at the blade-pass rate.

    Each pass is a short broad "thump" (a damped 150 Hz burst) plus a noisy slap. Everything under 100 Hz
    is left out on purpose: the rate itself (30 passes per second) and its first harmonics would beat
    with the bass notes of the music, and the chop is carried by 120 Hz upwards anyway.
    """
    dur = c.dur or DEFAULT_DUR["rotor"]
    n = nsamp(dur)
    rate = float(c.rate) if c.rate else 30.0
    rng = rng_for("rotor", c.index)
    klen = nsamp(0.12)
    t = np.arange(klen) / SR
    kern = (0.90 * np.sin(dsp.TAU * 150.0 * t + 0.3) * np.exp(-t / 0.011)
            + 0.45 * np.sin(dsp.TAU * 310.0 * t + 1.0) * np.exp(-t / 0.008))
    slap = dsp.bp(rng.standard_normal(klen + 64), 260, 1500, 2)[64:]
    kern += 0.75 * slap / (np.std(slap) + 1e-12) * np.exp(-t / 0.0060)
    kern *= np.minimum(1.0, np.arange(klen) / (0.0012 * SR))          # soft attack
    train = np.zeros(n)
    k = 0
    while True:
        i = int(round(k / rate * SR))
        if i >= n:
            break
        train[i] += 1.0 + 0.10 * np.sin(dsp.TAU * (k / rate) * rate / 5.0)   # blade-to-blade variation
        k += 1
    y = signal.fftconvolve(train, kern)[:n]
    # a soft rush of air under the chop, pulsing with it
    wind = dsp.bp(dsp.pink(n, rng_for("rotor-wind", c.index)), 110, 700, 2)
    wind /= np.std(wind) + 1e-12
    pulse = 0.65 + 0.35 * np.cos(dsp.TAU * rate * np.arange(n) / SR)
    y = y / (np.std(y) + 1e-12) + 0.28 * wind * pulse
    y = dsp.lp(y, 2000, 2)
    y = dsp.hp(y, 100, 4) * _env_cos(n, 0.35, 0.50)
    return _mono(y, send=0.08, kind="bed", duration=dur)


def hum(c: Cue, ctx):
    """Electrical hum of a lamp: 100 Hz and its harmonics, very quiet, with a faint noise floor."""
    dur = c.dur or DEFAULT_DUR["hum"]
    n = nsamp(dur)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for k, a in enumerate([1.0, 0.55, 0.34, 0.22, 0.13, 0.08], start=1):
        y += a * np.sin(dsp.TAU * 100.0 * k * t + 0.6 * k)
    y *= 1.0 + 0.06 * np.sin(dsp.TAU * 0.23 * t)
    rng = rng_for("hum", c.index)
    y = y / (np.std(y) + 1e-12) + 0.05 * dsp.lp(dsp.pink(n, rng), 1200, 2)
    y *= _env_cos(n, 0.30, 0.45)
    return _mono(y, send=0.0, kind="bed", duration=dur)


def motor(c: Cue, ctx):
    """Electric motor whine: a tone that spins up to a chord tone, with harmonics and a faint buzz."""
    dur = c.dur or DEFAULT_DUR["motor"]
    n = nsamp(dur)
    t = np.arange(n) / SR
    f0 = float(midi_hz(_pick(ctx, c.t, 70, 82, 0)))        # a chord tone in the upper middle range
    spin = 1.0 - 0.55 * np.exp(-t / 0.22)
    f = f0 * spin
    ph = np.cumsum(f) / SR
    y = np.zeros(n)
    for k, a in enumerate([1.0, 0.42, 0.26, 0.10], start=1):
        y += a * np.sin(dsp.TAU * k * ph + 0.3 * k)
    y *= 1.0 + 0.07 * np.sin(dsp.TAU * 6.5 * t)
    rng = rng_for("motor", c.index)
    buzz = dsp.bp(rng.standard_normal(n), 1100, 4200, 2)
    y = y / (np.std(y) + 1e-12) + 0.12 * buzz / (np.std(buzz) + 1e-12)
    y = dsp.lp(y, 5200, 2) * _env_cos(n, 0.20, 0.35)
    return _mono(y, send=0.05, kind="bed", duration=dur)


REGISTRY = {
    "shutter": shutter, "tick": tick, "pop": pop, "blip": blip, "click": click,
    "whoosh": whoosh, "swoosh_rev": swoosh_rev, "riser": riser, "hit": hit, "shimmer": shimmer,
    "glitch": glitch, "car": car, "whirr": whirr, "rotor": rotor, "hum": hum, "motor": motor,
}


def normalise_level(audio, mode, target_db):
    """Scale a stereo sound so its peak or its RMS (over the audible part) equals target_db."""
    if mode == "peak":
        cur = np.max(np.abs(audio))
    else:
        a = np.abs(audio).max(axis=1)
        active = a > 0.02 * a.max()                     # ignore silent gaps and fade tails
        cur = np.sqrt(np.mean(np.square(audio[active])))
    return audio * (dsp.db2lin(target_db) / max(cur, 1e-12))
