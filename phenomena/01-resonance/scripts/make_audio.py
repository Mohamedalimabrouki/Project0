"""
Resonance - the soundtrack: voice-over, music, and sound effects, mixed to about -14 LUFS.

Every sound effect is synthesised here (no sample libraries), and most are
driven by the same physics as the pictures: the swing pushes, the push rhythm
of the sweep, the 'hum' of the mass (as loud as its motion), the walkers'
steps, the tower's 6.8 s sway.

  python make_audio.py            (needs build/audio/narration/*.wav and music, see make_music.py)
"""

import math
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import physics as P  # noqa: E402
import timeline as tl  # noqa: E402

SR = 48000
T = tl.line_times()
S = tl.scenes(T)
TOTAL = tl.total_duration() + 0.5
N = int(TOTAL * SR)
BUILD = tl.BUILD
RNG = np.random.default_rng(7)


def at(lid, phrase=None):
    return T[lid][0] if phrase is None else tl.phrase_time(lid, phrase, T)


# ------------------------------------------------------------------ helpers

def stereo(x, pan=0.0):
    """Equal-power pan, pan -1 (left) to +1 (right)."""
    a = (pan + 1) * math.pi / 4
    return np.stack([x * math.cos(a), x * math.sin(a)], axis=1)


def place(bus, x, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(bus) or i + len(x) <= 0:
        return
    j0 = max(0, -i)
    i0 = max(0, i)
    n = min(len(x) - j0, len(bus) - i0)
    bus[i0:i0 + n] += gain * x[j0:j0 + n]


def db(x):
    return 10 ** (x / 20)


def bandpass(x, lo, hi, order=2):
    sos = signal.butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def lowpass(x, f, order=2):
    sos = signal.butter(order, f, btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def highpass(x, f, order=2):
    sos = signal.butter(order, f, btype="high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def env_ad(n, attack, decay):
    t = np.arange(n) / SR
    e = np.where(t < attack, t / max(attack, 1e-6), np.exp(-(t - attack) / decay))
    return e


def fade_env(n, fi, fo):
    e = np.ones(n)
    a, b = int(fi * SR), int(fo * SR)
    if a > 0:
        e[:a] = np.linspace(0, 1, a) ** 2
    if b > 0:
        e[-b:] *= np.linspace(1, 0, b) ** 2
    return e


# ------------------------------------------------------------------ sound effects

def thump(gain=1.0):
    """A soft push: a short low 'whump' with a tiny contact click."""
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 50 + 70 * np.exp(-t / 0.05)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * env_ad(n, 0.004, 0.11)
    click = lowpass(RNG.normal(0, 1, n), 1800) * env_ad(n, 0.001, 0.012) * 0.35
    return (body + click) * gain


def tick(freq=2100, gain=1.0):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * freq * t) + 0.5 * np.sin(2 * np.pi * freq * 1.63 * t)) * env_ad(n, 0.0008, 0.018)
    noise = highpass(RNG.normal(0, 1, n), 3000) * env_ad(n, 0.0005, 0.006) * 0.3
    return (tone + noise) * gain * 0.5


def whoosh(dur=1.2, lo=300, hi=3000, gain=1.0, peak=0.6):
    n = int(dur * SR)
    x = RNG.normal(0, 1, n)
    x = bandpass(x, lo, hi)
    u = np.linspace(0, 1, n)
    e = np.where(u < peak, (u / peak) ** 2, ((1 - u) / (1 - peak)) ** 1.5)
    return x * e * gain * 0.35


def boom(dur=2.2, f0=48, gain=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 + 30 * np.exp(-t / 0.08)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) * env_ad(n, 0.006, 0.6)
    x += lowpass(RNG.normal(0, 1, n), 400) * env_ad(n, 0.002, 0.08) * 0.4
    return x * gain


def footstep(gain=1.0):
    n = int(0.09 * SR)
    x = RNG.normal(0, 1, n)
    x = bandpass(x, 140 + RNG.uniform(-20, 20), 1100 + RNG.uniform(-200, 200))
    return x * env_ad(n, 0.002, 0.02 + RNG.uniform(0, 0.01)) * gain * 0.6


def noise_bed(dur, lo, hi, gain, seed=0, gust_period=None, gust_depth=0.0, brown=False):
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, (n, 2))
    if brown:
        x = np.cumsum(x, axis=0)
        x = highpass(x, 25)
        x /= np.max(np.abs(x)) + 1e-9
        x *= 3
    x = bandpass(x, lo, hi)
    if gust_period:
        t = np.arange(n) / SR
        g = 1 + gust_depth * np.sin(2 * np.pi * t / gust_period + rng.uniform(0, 6))
        g *= 1 + 0.5 * gust_depth * np.sin(2 * np.pi * t / (gust_period * 0.37) + rng.uniform(0, 6))
        x *= g[:, None]
    return x * gain


def reverb_ir(dur=1.6, decay=0.45, seed=3):
    n = int(dur * SR)
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, (n, 2)) * np.exp(-t / decay)[:, None]
    # darker tail: low-pass progressively
    ir = lowpass(ir, 5000)
    ir[: int(0.012 * SR)] = 0                      # pre-delay
    ir /= np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True))
    return ir


def convolve_st(x, ir):
    return np.stack([signal.fftconvolve(x[:, i], ir[:, i])[: len(x)] for i in range(2)], axis=1)


# ------------------------------------------------------------------ the layers

def build_narration():
    vo = np.zeros(N)
    nd = os.path.join(BUILD, "audio", "narration")
    for lid, (a, b) in T.items():
        x, sr = sf.read(os.path.join(nd, f"{lid}.wav"))
        if sr != SR:
            x = signal.resample_poly(x, SR, sr)
        x = highpass(x, 70)
        x = x * fade_env(len(x), 0.015, 0.015)      # no clicks at the cut points
        place(vo, x, a)
    # voice activity (for ducking the music), smoothed
    act = np.zeros(N)
    for lid, (a, b) in T.items():
        act[int(a * SR): int(b * SR)] = 1.0
    k = int(0.25 * SR)
    kernel = np.hanning(2 * k)
    kernel /= kernel.sum()
    act = np.convolve(act, kernel, mode="same")
    return vo, np.clip(act * 1.2, 0, 1)


def build_sfx():
    fx = np.zeros((N, 2))
    d = P.swing_data(os.path.join(BUILD, "data"))
    hook0 = S["hook"][0]
    # ident whoosh
    place(fx, stereo(whoosh(2.2, 200, 2500, 0.5, peak=0.35)), 0.0)
    # the swings: a soft thump on every push (left swing left, right swing right)
    for tp in d["rhythm_pushes"]:
        place(fx, stereo(thump(0.9), -0.45), hook0 + tp)
    for tp in d["random_pushes"]:
        place(fx, stereo(thump(0.9), 0.45), hook0 + tp)
    # chains: a tiny metallic tick at each turning point of the rhythm swing (quiet)
    th, om, tt = d["rhythm_theta"], d["rhythm_omega"], d["t"]
    for i in range(1, len(tt)):
        if om[i - 1] * om[i] < 0 and abs(th[i]) > np.radians(8) and tt[i] < 18.9:
            place(fx, stereo(tick(3200, 0.10 + 0.25 * abs(th[i]) / 0.66), -0.45), hook0 + tt[i])
    # title: whoosh into a soft boom
    tt4 = at("L04")
    place(fx, stereo(whoosh(1.6, 200, 5000, 0.8, peak=0.85)), tt4 - 1.35)
    place(fx, stereo(boom(2.6, 44, 0.9)), tt4)
    # the single swing: a release whoosh, then quiet ticks at each back-and-forth
    r0 = S["rhythm_swing"][0]
    pl = P.pull_data(os.path.join(BUILD, "data"))
    rel = r0 + float(pl["release"])
    place(fx, stereo(whoosh(0.9, 400, 2400, 0.35, peak=0.3)), rel - 0.05)
    # blueprint transition
    place(fx, stereo(whoosh(1.4, 2000, 9000, 0.25, peak=0.5)), S["spring_model"][0] - 0.1)
    # the sweep: a tick at each push, and the 'hum' of the mass, as loud as its motion
    import sc_model as smp
    for tk, rr in smp.push_times():
        place(fx, stereo(tick(1400, 0.32)), tk)
    hum = np.zeros(N)
    t0, t1 = S["sweep"][0], at("L16") + 0.5
    ts = np.arange(int(t0 * SR), int(t1 * SR)) / SR
    step = 256
    tq = ts[::step]
    amp = np.array([smp.sweep_state(t)["A"] * smp.sweep_state(t)["env"] for t in tq]) / 10.0
    fade_o = 1 - np.clip((tq - (at("L16") - 0.4)) / 0.8, 0, 1)
    amp = np.interp(ts, tq, amp * fade_o)
    ph = 2 * np.pi * 73.42 * ts
    tone = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph + 0.3)
    hum[int(t0 * SR): int(t0 * SR) + len(ts)] = tone * amp ** 1.3 * 0.22
    fx += stereo(hum)
    # damping: whooshes as each curve draws
    for ph_ in ("With 5", "Double the damping", "At 30"):
        place(fx, stereo(whoosh(1.2, 600, 4000, 0.22, peak=0.4), 0.2), at("L16", ph_) - 0.1)
    # the bridge: river, crowd steps, the walker, the sway rumble, the stamp
    b0, b1 = S["bridge"]
    river = noise_bed(b1 - b0, 80, 1400, 0.03, seed=11, gust_period=5.0, gust_depth=0.3)
    river *= fade_env(len(river), 1.5, 1.5)[:, None]
    place(fx, river, b0)
    t18, t19, t20, t21 = at("L18"), at("L19"), at("L20"), at("L21")
    t_sec = t19 - 0.6
    t_back = at("L21", "Engineers fitted") - 0.6
    t_02 = at("L21", "In 2002")
    for crowd_t0, crowd_t1 in ((t18 + 0.3, t_sec + 0.8), (t_02 - 0.5, b1 - 0.3)):
        tk = crowd_t0
        while tk < crowd_t1:
            place(fx, stereo(footstep(RNG.uniform(0.15, 0.45)), RNG.uniform(-0.8, 0.8)), tk)
            tk += RNG.exponential(0.035)
    # the walker in the section view: steps at 1.8 per second (the drawn walker)
    k0 = math.ceil(t_sec * 1.8)
    k1 = int(t_back * 1.8)
    for k in range(k0, k1):
        tk = k / 1.8
        place(fx, stereo(footstep(1.2), -0.25 if k % 2 == 0 else 0.25), tk)
    # the sway: a low rumble swelling at the sway frequency
    ts = np.arange(int(t20 * SR), int((t21 + 1.5) * SR)) / SR
    grow = np.clip((ts - t20) / 8.0, 0, 1) ** 2 * (1 - np.clip((ts - t21 - 0.2) / 1.2, 0, 1))
    rum = (np.sin(2 * np.pi * 55 * ts) + 0.5 * np.sin(2 * np.pi * 82.5 * ts)) * np.abs(np.sin(np.pi * 0.8 * (ts - t20)))
    fx[int(t20 * SR): int(t20 * SR) + len(ts)] += stereo(rum * grow * 0.28)
    place(fx, stereo(boom(1.8, 60, 0.8)), t21)
    place(fx, stereo(thump(1.2)), t21)
    # dampers switched on: small pops, one per damper, left to right
    t_fit = at("L21", "Engineers fitted") + 0.2
    for i in range(37):
        place(fx, stereo(tick(2600 + 30 * i, 0.12), -0.9 + 1.8 * i / 36), t_fit + i * 2.0 / 40)
    # Taipei: wind, and the deep breathing of the ball
    ta0, ta1 = S["taipei"]
    wind = noise_bed(ta1 - ta0, 60, 900, 0.05, seed=21, gust_period=6.8, gust_depth=0.6, brown=True)
    wind *= fade_env(len(wind), 2.0, 1.5)[:, None]
    t23 = at("L23")
    tw = np.arange(len(wind)) / SR + ta0
    wind *= (0.6 + 0.8 * np.clip((tw - (t23 - 0.5)) / 1.5, 0, 1))[:, None]
    place(fx, wind, ta0)
    t3d = at("L22", "Near the top") + 1.3
    ts = np.arange(int(t3d * SR), int((t23 + 0.5) * SR)) / SR
    br = np.sin(2 * np.pi * 41.2 * ts) * (0.5 + 0.5 * np.sin(2 * np.pi * (ts - t3d) / P.TOWER_PERIOD)) ** 2
    br *= np.clip((ts - t3d) / 1.0, 0, 1) * np.clip((t23 + 0.5 - ts) / 1.0, 0, 1)
    fx[int(t3d * SR): int(t3d * SR) + len(ts)] += stereo(br * 0.35)
    # transitions
    for tt_ in (S["rhythm_swing"][0], S["spring_hero"][0], S["bridge"][0] + 0.2, S["taipei"][0] + 0.2,
                S["takeaway"][0]):
        place(fx, stereo(whoosh(1.1, 250, 3500, 0.22, peak=0.55)), tt_ - 0.55)
    # a touch of room on the effects
    fx = 0.85 * fx + 0.25 * convolve_st(fx, reverb_ir(1.2, 0.3))
    return fx


def main():
    print("narration...")
    vo, act = build_narration()
    print("music...")
    mu, sr = sf.read(os.path.join(BUILD, "audio", "music_raw.wav"))
    if sr != SR:
        mu = signal.resample_poly(mu, SR, sr, axis=0)
    mu = mu[:N] if len(mu) >= N else np.pad(mu, ((0, N - len(mu)), (0, 0)))
    mu = highpass(mu, 35)
    print("effects...")
    fx = build_sfx()

    meter = pyln.Meter(SR)
    # levels: voice at about -17 LUFS, music about 11 dB under the voice while it speaks
    vo_l = meter.integrated_loudness(np.stack([vo, vo], axis=1))
    vo_g = db(-17.0 - vo_l)
    mu_l = meter.integrated_loudness(mu)
    mu_g = db(-22.5 - mu_l)
    duck = 1 - 0.55 * act                           # about -7 dB while the voice speaks
    fx_l = meter.integrated_loudness(fx + 1e-9)
    fx_g = db(-27.0 - fx_l)
    mix = stereo(vo * vo_g) + mu * mu_g * duck[:, None] + fx * fx_g
    # master: gentle glue, loudness to -14 LUFS, peak limit at -1 dBFS
    lufs = meter.integrated_loudness(mix)
    mix *= db(-14.0 - lufs)
    peak = np.max(np.abs(mix))
    limit = db(-1.0)
    if peak > limit:
        # soft knee limiter (tanh above the knee)
        knee = limit * 0.8
        over = np.abs(mix) > knee
        mix[over] = np.sign(mix[over]) * (knee + (limit - knee) * np.tanh((np.abs(mix[over]) - knee) / (limit - knee)))
    # fade out the last second
    mix *= fade_env(N, 0.0, 1.2)[:, None]
    out = os.path.join(BUILD, "audio", "mix.wav")
    sf.write(out, mix.astype(np.float32), SR, subtype="PCM_24")
    stems = os.path.join(BUILD, "audio")
    sf.write(os.path.join(stems, "stem_voice.wav"), (vo * vo_g).astype(np.float32), SR, subtype="PCM_24")
    sf.write(os.path.join(stems, "stem_music.wav"), (mu * mu_g).astype(np.float32), SR, subtype="PCM_24")
    sf.write(os.path.join(stems, "stem_effects.wav"), (fx * fx_g).astype(np.float32), SR, subtype="PCM_24")
    print(f"mix: {meter.integrated_loudness(mix):.1f} LUFS, peak {20 * np.log10(np.max(np.abs(mix))):.1f} dBFS, "
          f"{N / SR:.1f} s -> {out}")


if __name__ == "__main__":
    main()
