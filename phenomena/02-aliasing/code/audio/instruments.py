"""The instruments of the underscore, each one a small synthesiser written from scratch.

  pad     soft analogue-style pad: four detuned band-limited saws per voice, legato (each voice glides
          to its next chord tone, so neighbouring notes never rub against each other), wide stereo
  pluck   marimba / kalimba-like pulse: a harmonic series whose upper partials die first
  bell    glassy bell for the motif: four harmonic partials, two detuned copies
  keys    warm electric-piano chords (2-operator FM with matching 1:1 ratio)
  bass    deep sub bass: a sine with a whisper of 2nd and 3rd harmonic, mono
  kick    soft heart-beat kick: a sine that falls from about 125 Hz to 47 Hz
  hat     brushed noise (a hat made of filtered noise, soft attack)
  rim     rim click: a few short damped tones plus a tiny noise tick
  swell   filtered-noise swell used for lifts and the build into the title

All of them are tuned in equal temperament with A4 = 440 Hz. Events are plain dicts (see the
`render_*` functions); a `Bend` can make every pitched voice sag together (tape-stop feel).
"""
from __future__ import annotations

import numpy as np

import dsp
from dsp import SR, idx, nsamp, midi_hz, db2lin, rng_for, ramp_up, ramp_down


# ------------------------------------------------------------------ global pitch bend
class Bend:
    """A pitch sag shared by all pitched voices: goes down `depth` semitones and springs back.

    Shape (times in seconds): falls exponentially between t0 and t0 + fall, holds, and glides
    back to zero between t1 - back and t1, with a little tape wobble (flutter) while it is away.
    """

    def __init__(self, t0, t1, depth=3.2, fall=0.38, back=0.14, tau=0.10, wobble_hz=5.2, wobble_semi=0.10):
        self.t0, self.t1 = t0, t1
        self.depth, self.fall, self.back, self.tau = depth, fall, back, tau
        self.wobble_hz, self.wobble_semi = wobble_hz, wobble_semi

    def semitones(self, t):
        t = np.asarray(t, dtype=float)
        s = np.zeros_like(t)
        x = t - self.t0
        dn = (1.0 - np.exp(-np.clip(x, 0, self.fall) / self.tau)) / (1.0 - np.exp(-self.fall / self.tau))
        up = 1.0 - dsp.smoothstep((t - (self.t1 - self.back)) / self.back)
        shape = np.where(t < self.t0, 0.0, np.where(t < self.t1 - self.back, dn, up))
        shape = np.where(t >= self.t1, 0.0, shape)
        wob = self.wobble_semi * np.sin(dsp.TAU * self.wobble_hz * x) * np.sin(np.pi * np.clip(x / (self.t1 - self.t0), 0, 1)) ** 2
        s = -self.depth * shape + np.where((t >= self.t0) & (t < self.t1), wob, 0.0)
        return s

    def mult(self, t):
        return 2.0 ** (self.semitones(t) / 12.0)

    def touches(self, ta, tb):
        return tb > self.t0 and ta < self.t1


def _freq_bend(f0, t, bend):
    if bend is not None and bend.touches(t[0], t[-1]):
        return f0 * bend.mult(t)
    return np.full(len(t), f0)


# -------------------------------------------------------------------------------- pad
_PAD_CENTS = (-11.0, -4.0, 4.0, 11.0)          # four detuned saws per voice
_PAD_PANS = (-0.85, -0.30, 0.30, 0.85)
_CHUNK = 20 * SR                                # long voices are rendered 20 s at a time (memory)


def _saw_chunk(freq, phase0):
    """Band-limited saw for one chunk; returns the wave and the phase at the end (so chunks join exactly)."""
    dt = freq / SR
    ph = phase0 + np.cumsum(dt) - dt
    end = phase0 + float(dt.sum())
    ph = ph - np.floor(ph)
    y = 2.0 * ph - 1.0
    m1 = ph < dt
    if m1.any():
        t = ph[m1] / dt[m1]
        y[m1] -= t + t - t * t - 1.0
    m2 = ph > 1.0 - dt
    if m2.any():
        t = (ph[m2] - 1.0) / dt[m2]
        y[m2] -= t * t + t + t + 1.0
    return y, end - np.floor(end)


def pad_tracks(events):
    """Group pad events (one per chord and voice) into legato tracks: one continuous voice each.

    A voice that plays the same pitch in the next chord simply carries on; a voice that changes
    pitch glides to it, so two neighbouring notes (A then B flat) are never heard at the same time.
    """
    groups = {}
    for e in events:
        groups.setdefault((e["layer"], e["voice"]), []).append(e)
    tracks = []
    for key in sorted(groups):
        cur = None
        for e in sorted(groups[key], key=lambda e: e["t0"]):
            if cur is not None and abs(cur["segs"][-1][1] - e["t0"]) < 1e-6:
                t0, t1, m = cur["segs"][-1]
                if m == e["midi"]:
                    cur["segs"][-1] = (t0, e["t1"], m)
                else:
                    cur["segs"].append((e["t0"], e["t1"], e["midi"]))
                cur["rel"] = e["rel"]
            else:
                if cur is not None:
                    tracks.append(cur)
                cur = dict(layer=key[0], voice=key[1], segs=[(e["t0"], e["t1"], e["midi"])], db=e["db"], att=e["att"], rel=e["rel"])
        if cur is not None:
            tracks.append(cur)
    return tracks


def glide_time(semitones):
    """Portamento between two chord tones: 0.10 s plus 20 ms per semitone, at most 0.24 s."""
    return float(np.clip(0.10 + 0.02 * abs(semitones), 0.10, 0.24))


def render_pad(events, n_total, bend=None):
    """The pad: every voice is one continuous track of four detuned saws. Returns (n_total, 2)."""
    out = np.zeros((n_total, 2))
    gains = [dsp.pan_gains(p) for p in _PAD_PANS]
    for k, tr in enumerate(pad_tracks(events)):
        segs = tr["segs"]
        a = idx(segs[0][0])
        n_on = max(1, idx(segs[-1][1]) - a)
        att = min(idx(tr["att"]), n_on)
        rel = idx(tr["rel"])
        n = n_on + rel
        amp0 = db2lin(tr["db"]) * 0.11
        rng = rng_for("pad", k, tr["layer"], tr["voice"])
        phases = [float(rng.uniform()) for _ in range(4)]
        lfo = [(0.083 + 0.031 * j, float(rng.uniform(0, dsp.TAU))) for j in range(4)]
        for c0 in range(0, n, _CHUNK):
            c1 = min(n, c0 + _CHUNK)
            t = (a + np.arange(c0, c1)) / SR
            m = np.full(len(t), float(segs[0][2]))
            for (s0, s1, m0), (n0, n1, m1) in zip(segs, segs[1:]):
                d = m1 - m0
                g = glide_time(d)
                m += d * dsp.smoothstep((t - (n0 - g / 2)) / g)
            f_base = 440.0 * 2.0 ** ((m - 69.0) / 12.0)
            if bend is not None and bend.touches(t[0], t[-1]):
                f_base = f_base * bend.mult(t)
            L = np.zeros(len(t))
            R = np.zeros(len(t))
            for j in range(4):
                drift = 2.4 * np.sin(dsp.TAU * lfo[j][0] * t + lfo[j][1])
                fj = f_base * 2.0 ** ((_PAD_CENTS[j] + drift) / 1200.0)
                sj, phases[j] = _saw_chunk(fj, phases[j])
                L += sj * gains[j][0] * np.sqrt(2)
                R += sj * gains[j][1] * np.sqrt(2)
            env = np.ones(c1 - c0)
            i = np.arange(c0, c1)
            if att > 0:
                ra = i < att
                env[ra] = 0.5 - 0.5 * np.cos(np.pi * i[ra] / att)
            if rel > 0:
                rr = i >= n_on
                env[rr] = 0.5 + 0.5 * np.cos(np.pi * (i[rr] - n_on) / rel)
            lo, hi = a + c0, min(n_total, a + c1)
            if hi > lo:
                out[lo:hi, 0] += (L * env * amp0)[: hi - lo]
                out[lo:hi, 1] += (R * env * amp0)[: hi - lo]
    return out


# ------------------------------------------------------------------------------- bass
def bass_note(midi, dur, db=0.0, att=0.022, rel=0.12, sub=0.0, t0=0.0, bend=None):
    f0 = float(midi_hz(midi))
    n_on = nsamp(dur)
    n = n_on + nsamp(rel)
    t = t0 + np.arange(n) / SR
    f = _freq_bend(f0, t, bend)
    ph = dsp.TAU * dsp.phase_from_freq(f)
    y = np.sin(ph) + 0.30 * np.sin(2 * ph + 0.4) + 0.09 * np.sin(3 * ph + 1.1)
    if sub > 0:
        y += sub * np.sin(0.5 * ph)
    env = np.ones(n)
    a = min(nsamp(att), n_on)
    env[:a] = ramp_up(a)
    env[n_on:] = ramp_down(n - n_on)
    return y * env * db2lin(db) * 0.5


def render_bass(notes, n_total, bend=None):
    out = np.zeros(n_total)
    for nt in notes:
        y = bass_note(nt["midi"], nt["t1"] - nt["t0"], nt.get("db", 0.0), nt.get("att", 0.022),
                      nt.get("rel", 0.12), nt.get("sub", 0.0), nt["t0"], bend)
        dsp.place(out, y, idx(nt["t0"]))
    return out


# ------------------------------------------------------------------------------ pluck
_PLUCK_CACHE = {}


def _pluck_wave(midi, fc, tau0, t_start=None, bend=None):
    f0 = float(midi_hz(midi))
    n = nsamp(1.15)
    t = np.arange(n) / SR
    K = int(min(16, (min(9000.0, 3.0 * fc)) // f0))
    K = max(K, 1)
    tau_base = tau0 * (330.0 / f0) ** 0.30
    y = np.zeros(n)
    if bend is not None and t_start is not None and bend.touches(t_start, t_start + n / SR):
        fb = f0 * bend.mult(t_start + t)
        ph0 = dsp.TAU * dsp.phase_from_freq(fb)
    else:
        ph0 = dsp.TAU * f0 * t
    norm = 0.0
    for k in range(1, K + 1):
        a = k ** -1.05 / np.sqrt(1.0 + (k * f0 / fc) ** 4)
        tau = tau_base / (1.0 + 0.75 * (k - 1))
        y += a * np.sin(k * ph0 + 0.7 * k) * np.exp(-t / tau)
        norm += a
    y /= max(norm, 1e-9)
    y *= np.minimum(1.0, np.arange(n) / (0.0018 * SR))
    tail = nsamp(0.25)
    y[-tail:] *= ramp_down(tail)
    return y


def pluck_wave(midi, fc, tau0=0.34, t_start=None, bend=None):
    """Unit-level pluck waveform (cached unless the tape bend touches it)."""
    if bend is not None and t_start is not None and bend.touches(t_start, t_start + 1.2):
        return _pluck_wave(midi, fc, tau0, t_start, bend)
    key = (int(midi), int(round(np.log2(max(fc, 100.0)) * 3)), round(tau0, 3))
    if key not in _PLUCK_CACHE:
        _PLUCK_CACHE[key] = _pluck_wave(midi, 2.0 ** (key[1] / 3.0), tau0)
    return _PLUCK_CACHE[key]


def render_pluck(notes, n_total, bend=None):
    out = np.zeros((n_total, 2))
    for nt in notes:
        w = pluck_wave(nt["midi"], nt.get("fc", 2600.0), nt.get("tau", 0.34), nt["t"], bend)
        st = dsp.to_stereo(w * db2lin(nt["db"]) * 0.5, nt.get("pan", 0.0))
        dsp.place(out, st, idx(nt["t"]))
    return out


# -------------------------------------------------------------------------------- bell
_BELL_PARTS = ((1.0, 1.00, 2.6), (2.0, 0.26, 1.5), (3.0, 0.09, 0.95), (4.0, 0.04, 0.6))


def bell_wave(midi, dur=3.0, t_start=None, bend=None):
    f0 = float(midi_hz(midi))
    n = nsamp(dur)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for det in (-3.0, 3.0):
        f = f0 * 2.0 ** (det / 1200.0)
        if bend is not None and t_start is not None and bend.touches(t_start, t_start + dur):
            ph = dsp.TAU * dsp.phase_from_freq(f * bend.mult(t_start + t))
        else:
            ph = dsp.TAU * f * t
        for k, (h, a, tau) in enumerate(_BELL_PARTS):
            if h * f0 > 9000:
                continue
            y += 0.5 * a * np.sin(h * ph + 0.5 * k) * np.exp(-t / (tau * min(1.0, 0.35 + dur / 4.0)))
    y *= np.minimum(1.0, np.arange(n) / (0.0022 * SR))
    tail = min(nsamp(0.4), n // 3)
    y[-tail:] *= ramp_down(tail)
    return y / 1.05


def render_bells(notes, n_total, bend=None):
    out = np.zeros((n_total, 2))
    for nt in notes:
        w = bell_wave(nt["midi"], nt.get("dur", 3.0), nt["t"], bend)
        st = dsp.to_stereo(w * db2lin(nt["db"]) * 0.5, nt.get("pan", 0.0))
        dsp.place(out, st, idx(nt["t"]))
    return out


# ------------------------------------------------------------------------------- keys
def keys_note(midi, dur, db=0.0, pan=0.0, t0=0.0, rel=0.35):
    """Warm electric piano: sine carrier, 1:1 self-modulation that relaxes, a soft tine on top."""
    f0 = float(midi_hz(midi))
    n_on = nsamp(dur)
    n = n_on + nsamp(rel)
    t = np.arange(n) / SR
    th = dsp.TAU * f0 * t
    index = 0.22 + 1.5 * np.exp(-t / 0.20)
    y = np.sin(th + index * np.sin(th))
    y += 0.10 * np.sin(4 * th + 1.0) * np.exp(-t / 0.05)          # tine
    env = (1.0 - np.exp(-t / 0.004)) * (0.55 * np.exp(-t / 0.35) + 0.45 * np.exp(-t / 1.6))
    env[n_on:] *= ramp_down(n - n_on)
    trem = 1.0 + 0.10 * np.sin(dsp.TAU * 4.3 * t + (0.0 if pan <= 0 else np.pi))
    y = dsp.lp(y * env * trem, 3600, 2)
    return dsp.to_stereo(y * db2lin(db) * 0.4, pan)


def render_keys(notes, n_total):
    out = np.zeros((n_total, 2))
    for nt in notes:
        st = keys_note(nt["midi"], nt["t1"] - nt["t0"], nt["db"], nt.get("pan", 0.0), nt["t0"], nt.get("rel", 0.35))
        dsp.place(out, st, idx(nt["t0"]))
    return out


# ------------------------------------------------------------------------------- drums
def kick_wave():
    n = nsamp(0.42)
    t = np.arange(n) / SR
    f = 47.0 + 80.0 * np.exp(-t / 0.026)
    ph = dsp.TAU * np.cumsum(f) / SR
    y = np.sin(ph) * (1.0 - np.exp(-t / 0.0012)) * (0.85 * np.exp(-t / 0.115) + 0.15 * np.exp(-t / 0.30))
    y += 0.05 * np.sin(2 * ph) * np.exp(-t / 0.05)
    click = dsp.lp(rng_for("kick-click").standard_normal(n), 1800, 2) * np.exp(-t / 0.0022) * 0.16
    y = np.tanh(1.5 * (y + click)) / np.tanh(1.5)
    y[-nsamp(0.06):] *= ramp_down(nsamp(0.06))
    return y


def hat_wave(variant, open_=False):
    n = nsamp(0.36 if open_ else 0.15)
    t = np.arange(n) / SR
    rng = rng_for("hat", variant, open_)
    w = rng.standard_normal(n + 512)
    w = dsp.bp(w, 2600, 8400, 2)[512:]
    w = dsp.lp(w, 8800, 2)
    tau = 0.11 if open_ else 0.030
    env = (1.0 - np.exp(-t / 0.0065)) * np.exp(-t / tau)
    y = w * env
    y /= np.max(np.abs(y)) + 1e-12
    tail = nsamp(0.03)
    y[-tail:] *= ramp_down(tail)
    return y


def rim_wave(variant=0):
    n = nsamp(0.14)
    t = np.arange(n) / SR
    y = (0.62 * np.sin(dsp.TAU * 1720 * t) * np.exp(-t / 0.0075)
         + 0.42 * np.sin(dsp.TAU * 2490 * t + 0.6) * np.exp(-t / 0.0050)
         + 0.55 * np.sin(dsp.TAU * 615 * t + 1.1) * np.exp(-t / 0.020))
    rng = rng_for("rim", variant)
    nz = dsp.bp(rng.standard_normal(n + 256), 1300, 4200, 2)[256:]
    y += 0.5 * nz / (np.std(nz) + 1e-12) * np.exp(-t / 0.0015) * 0.35
    y = dsp.lp(y, 6500, 2)
    y *= np.minimum(1.0, np.arange(n) / (0.0004 * SR))
    y /= np.max(np.abs(y)) + 1e-12
    tail = nsamp(0.03)
    y[-tail:] *= ramp_down(tail)
    return y


def render_drums(kicks, hats, rims, n_total):
    kick_bus = np.zeros(n_total)
    kw = kick_wave()
    for k in kicks:
        dsp.place(kick_bus, kw * db2lin(k["db"]) * 0.8, idx(k["t"]))
    hat_bus = np.zeros((n_total, 2))
    variants = [[hat_wave(v, False) for v in range(4)], [hat_wave(v, True) for v in range(2)]]
    for i, h in enumerate(hats):
        w = variants[1][i % 2] if h.get("open") else variants[0][i % 4]
        dsp.place(hat_bus, dsp.to_stereo(w * db2lin(h["db"]) * 0.5, h.get("pan", 0.0)), idx(h["t"]))
    rim_bus = np.zeros((n_total, 2))
    rw = [rim_wave(v) for v in range(3)]
    for i, r in enumerate(rims):
        dsp.place(rim_bus, dsp.to_stereo(rw[i % 3] * db2lin(r["db"]) * 0.6, r.get("pan", 0.0)), idx(r["t"]))
    return kick_bus, hat_bus, rim_bus


# ------------------------------------------------------------------------------- swells
def render_swells(swells, n_total):
    out = np.zeros((n_total, 2))
    for k, s in enumerate(swells):
        a, b = idx(s["t0"]), idx(s["t1"])
        n = b - a
        if n <= 0:
            continue
        u = np.arange(n) / n
        chans = []
        for ch in range(2):
            x = dsp.pink(n, rng_for("swell", k, ch))
            fc = s["f0"] * (s["f1"] / s["f0"]) ** (u ** s.get("curve", 1.3))
            y = dsp.tv_biquad(x, "bandpass", fc, 0.85)
            y = dsp.lp(y, 7000, 2)
            chans.append(y)
        env = u ** s.get("power", 2.0)
        fall = min(nsamp(s.get("fall", 0.05)), n // 4)
        env[n - fall:] *= ramp_down(fall)
        st = np.stack([chans[0] * env, chans[1] * env], axis=1) * db2lin(s["db"]) * 0.3
        dsp.place(out, st, a)
    return out


# ---------------------------------------------------------------------------- processors
def ping_pong(x, delay=0.375, feedback=0.38, taps=7, lp_hz=3200.0):
    """Tempo-synced ping-pong echoes (wet only): each repeat is darker and swaps left/right."""
    n = x.shape[0]
    d = nsamp(delay)
    wet = np.zeros_like(x)
    src = x
    for k in range(1, taps + 1):
        src = dsp.onepole_lp(src, lp_hz)
        s = src if k % 2 == 0 else src[:, ::-1]
        off = k * d
        if off >= n:
            break
        wet[off:] += (feedback ** (k - 1)) * s[: n - off]
    return wet
