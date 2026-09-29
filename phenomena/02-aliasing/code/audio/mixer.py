"""Turns the score into the music stem, and the cue list into the sound-effect stem.

Music chain (all decisions are measured, because nobody can listen while the script runs):
  1. every instrument is rendered on its own ("layer")
  2. each layer's loudness is measured (ITU-R BS.1770 K-weighting, the same as LUFS) and trimmed so
     the balance between layers follows LAYER_TARGET, whatever the synthesis details are
  3. echoes (dotted-eighth ping-pong) and the hall reverb are added
  4. each scene is levelled to SCENE_TARGET (text-heavy scenes sit lower than the others)
  5. the music is ducked by about 3 dB around dense sound-effect moments (highs mostly)
"""
from __future__ import annotations

import time

import numpy as np
import pyloudnorm as pyln
from scipy import signal

import dsp
import instruments as ins
import sfx as sfxlib
from dsp import SR, idx, db2lin

FILM_S = 180.0
N_TOTAL = int(round(FILM_S * SR))

# loudness of each layer relative to the pad (LU), measured while it plays
LAYER_TARGET = {"pad": 0.0, "bass": -6.0, "pluck": -7.5, "bell": -14.0, "keys": -13.0,
                "kick": -15.0, "hat": -18.5, "rim": -21.0, "swell": -18.0}
# how much of each layer feeds the hall reverb
REVERB_SEND = {"pad": 0.55, "pluck": 0.38, "bell": 0.85, "keys": 0.42, "hat": 0.10, "rim": 0.32, "swell": 0.35,
               "bass": 0.0, "kick": 0.0}
# The loudness contour of the music: (from s, to s, LU relative to the calm "bed" of scenes 3 and 4).
# The bed sits at BED_LUFS before the master stage; text-heavy scenes stay on the bed, the others
# rise above it. Inside each segment the arrangement keeps its own small movements.
BED_LUFS = -19.0
CONTOUR = [
    (4.0, 8.0, -2.0), (8.0, 11.5, -0.2), (11.5, 13.5, -2.8), (13.5, 16.0, 0.8), (16.0, 18.0, 3.2),   # hook
    (18.0, 21.0, 3.3), (21.0, 24.0, 1.4),                                                          # title
    (24.0, 36.0, 0.0), (36.0, 48.0, 0.0),                                                          # snapshots
    (48.0, 70.0, 0.0), (70.0, 78.0, 1.6), (78.0, 80.0, 0.2), (80.0, 86.0, -0.5),                   # the trick
    (86.0, 100.0, 0.8), (100.0, 112.0, 1.2), (112.0, 115.0, 1.8), (115.0, 118.0, 3.4), (118.0, 126.0, 2.0),   # the rule
    (126.0, 148.0, 2.4),                                                                           # real world 1
    (148.0, 168.0, 2.7), (168.0, 170.0, 2.0),                                                      # real world 2
    (170.0, 174.0, 1.2), (174.0, 177.5, 1.2),                                                      # takeaway
]
REF_LUFS = -20.0   # pad reference

DUCK_DEPTH_DB = 3.0


def _t():
    return time.time()


def curve(points, kind="db", n=N_TOTAL):
    t = np.arange(n) / SR
    tt = np.array([p[0] for p in sorted(points)])
    vv = np.array([p[1] for p in sorted(points)], dtype=float)
    if kind == "log":
        return np.exp(np.interp(t, tt, np.log(vv)))
    y = np.interp(t, tt, vv)
    return db2lin(y) if kind == "db" else y


def loudness(x, meter=None):
    """Integrated loudness in LUFS (None if the signal is silent)."""
    meter = meter or pyln.Meter(SR)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    if x.shape[0] < int(0.5 * SR) or np.max(np.abs(x)) < 1e-9:
        return None
    try:
        v = meter.integrated_loudness(x)
    except Exception:
        return None
    return None if not np.isfinite(v) else float(v)


def render_layers(S, log):
    """Render every layer of the score. Returns dict name -> (n, 2) array, before calibration."""
    t0 = _t()
    n = N_TOTAL
    bend = S.bend
    L = {}
    fc = curve(S.auto["pad_fc"], "log")
    pad = ins.render_pad(S.pad, n, bend)
    log(f"  pad notes rendered ({len(S.pad)} notes, {_t() - t0:.1f} s)")
    pad = dsp.filterbank_morph(pad, fc)
    del fc
    pad *= curve(S.auto["pad_db"], "db")[:, None]
    L["pad"] = pad

    bass = ins.render_bass(S.bass, n, bend)
    # the kick makes room for the bass: a short dip after every kick (gentle "sidechain")
    if S.kick:
        imp = np.zeros(n)
        for k in S.kick:
            imp[idx(k["t"])] = 1.0
        env = signal.lfilter([1.0], [1.0, -np.exp(-1.0 / (0.09 * SR))], imp)
        bass *= 1.0 - 0.35 * np.clip(env, 0.0, 1.0)
    bass *= curve(S.auto["bass_db"], "db")
    L["bass"] = np.stack([bass, bass], axis=1)

    L["pluck"] = ins.render_pluck(S.pluck, n, bend)
    L["bell"] = ins.render_bells(S.bell, n, bend)
    L["keys"] = ins.render_keys(S.keys, n)
    kick, hat, rim = ins.render_drums(S.kick, S.hat, S.rim, n)
    L["kick"] = np.stack([kick, kick], axis=1)
    L["hat"], L["rim"] = hat, rim
    L["swell"] = ins.render_swells(S.swell, n)
    log(f"  all layers rendered ({_t() - t0:.1f} s)")
    return L


def calibrate_layers(L, log):
    """Trim each layer so its measured loudness sits where LAYER_TARGET says (relative to the pad)."""
    meter = pyln.Meter(SR)
    gains = {}
    ref = loudness(L["pad"], meter)
    if ref is None:
        raise RuntimeError("the pad is silent: something is wrong with the score")
    g_pad = REF_LUFS - ref
    gains["pad"] = g_pad
    for name, x in L.items():
        if name == "pad":
            continue
        m = loudness(x, meter)
        if m is None:
            gains[name] = 0.0
            continue
        gains[name] = (REF_LUFS + LAYER_TARGET[name]) - m
    for name in L:
        L[name] = L[name] * db2lin(gains[name])
    return gains


def mix_music(S, log, layers=None):
    """Full music stem (n, 2) plus a small report dict."""
    t0 = _t()
    L = layers or render_layers(S, log)
    gains = calibrate_layers(L, log)
    log("  layer trims (dB): " + ", ".join(f"{k} {v:+.1f}" for k, v in gains.items()))
    n = N_TOTAL
    dry = np.zeros((n, 2))
    send = np.zeros((n, 2))
    for name, x in L.items():
        dry += x
        s = REVERB_SEND.get(name, 0.0)
        if s > 0:
            send += x * s
    # echoes: dotted-eighth ping-pong for the pluck (level follows the automation) and the bells
    echo_in = L["pluck"] * curve(S.auto["delay_send"], "db")[:, None] + L["bell"] * 0.20
    echoes = ins.ping_pong(echo_in, 0.375, 0.40, 7, 3000.0)
    dry += echoes
    send += echoes * 0.30
    log(f"  echoes done ({_t() - t0:.1f} s)")
    ir = dsp.make_reverb_ir(rt60=(3.6, 2.7, 1.3), length=3.8, predelay=0.032, lp_hz=6500.0, hp_hz=170.0, seed="music-hall")
    wet = dsp.convolve_ir(send, ir, n)
    log(f"  reverb done ({_t() - t0:.1f} s)")
    music = dry + wet * 1.0
    del dry, send, wet
    music = dsp.mono_below(music, 150.0)          # everything under 150 Hz stays in the middle
    return music, dict(layer_gain_db=gains)


def level_contour(music, log, passes=2):
    """Ride the level of the music so that its loudness follows CONTOUR (music alone, pre-master)."""
    meter = pyln.Meter(SR)
    report = []
    for p in range(passes):
        cs, gs, rep = [], [], []
        for a, b, rel in CONTOUR:
            seg = music[idx(a): idx(b)]
            m = loudness(seg, meter)
            tgt = BED_LUFS + rel
            g = 0.0 if m is None else float(np.clip(tgt - m, -9.0, 9.0))
            cs.append(0.5 * (a + b))
            gs.append(g)
            rep.append(dict(t0=a, t1=b, measured=m, target=tgt, gain_db=g))
        t = np.arange(N_TOTAL) / SR
        # the gain is linear in dB between segment centres; before the first centre (fade-in) and after
        # the last one (fade-out) it stays where it is
        gcurve = np.interp(t, cs, gs)
        music = music * db2lin(gcurve)[:, None]
        report.append(rep)
        log(f"  contour pass {p + 1}: gains (dB) " + " ".join(f"{r['gain_db']:+.1f}" for r in rep))
    return music, report[-1]


# --------------------------------------------------------------------------------- SFX stem
def parse_cues(raw_cues, log, film_s=FILM_S):
    """Turn timeline cues into Cue objects; unknown names are reported and skipped."""
    cues, counts = [], {}
    for q in raw_cues:
        name = q.get("sfx")
        if name not in sfxlib.REGISTRY:
            log(f"warning: unknown sfx '{name}' at t={q.get('t')} (scene {q.get('scene')}): ignored")
            continue
        t = float(q.get("t", 0.0))
        if not (0.0 <= t < film_s):
            log(f"warning: cue '{name}' at t={t} is outside the film: ignored")
            continue
        i = counts.get(name, 0)
        counts[name] = i + 1
        known = {"t", "sfx", "dur", "gain", "pan", "rate", "scene"}
        c = sfxlib.Cue(t=t, sfx=name, dur=(float(q["dur"]) if q.get("dur") is not None else None),
                       gain=float(q.get("gain", 0.0) or 0.0), pan=float(np.clip(q.get("pan", 0.0) or 0.0, -1, 1)),
                       rate=(float(q["rate"]) if q.get("rate") is not None else None), scene=q.get("scene", ""),
                       index=i, extra={k: v for k, v in q.items() if k not in known})
        cues.append(c)
    return cues


def render_sfx(cues, S, log):
    """Render every cue at its time. Returns (stem (n,2), reverb-free? no: with reverb, records)."""
    t0 = _t()
    n = N_TOTAL
    dry = np.zeros((n, 2))
    send = np.zeros((n, 2))
    records = []
    for c in cues:
        snd = sfxlib.REGISTRY[c.sfx](c, S)
        mode, tgt = sfxlib.LEVELS[c.sfx]
        a = sfxlib.normalise_level(snd.audio, mode, tgt + c.gain)
        a = dsp.to_stereo(a, c.pan)
        # the moment of a swell (swoosh_rev, riser) is its end: it must land on t + dur
        start = idx(c.t) if snd.anchor == 0 else idx(c.t + (c.dur or snd.duration)) - snd.anchor
        dsp.place(dry, a, start)
        if snd.send > 0:
            dsp.place(send, a, start, gain=snd.send)
        onset = _first_above(a, 0.05)
        records.append(dict(t=c.t, sfx=c.sfx, dur=c.dur, gain=c.gain, pan=c.pan, rate=c.rate, scene=c.scene,
                            start_sample=start, start_time=start / SR, kind=snd.kind, anchor=snd.anchor,
                            length_s=a.shape[0] / SR, peak_db=dsp.peak_db(a), first_sample_above_5pct_ms=onset * 1000.0 / SR))
    ir = dsp.make_reverb_ir(rt60=(1.9, 1.5, 0.8), length=2.0, predelay=0.012, lp_hz=8000.0, hp_hz=200.0, seed="sfx-room")
    wet = dsp.convolve_ir(send, ir, n)
    log(f"  {len(cues)} cues rendered ({_t() - t0:.1f} s)")
    return dry + wet, records


def _first_above(a, frac):
    m = np.max(np.abs(a), axis=1)
    thr = frac * m.max()
    i = np.argmax(m > thr)
    return int(i)


# ------------------------------------------------------------------------------- ducking
def duck_curve(cues, log=None):
    """Attention signal 0..1 built from the cue list: 1 means 'duck the music by the full 3 dB'."""
    ctrl = 1000
    m = int(FILM_S * ctrl) + 1
    a = np.zeros(m)
    for c in cues:
        w, hold = sfxlib.DUCK_WEIGHT[c.sfx]
        d = hold if hold is not None else (c.dur or sfxlib.DEFAULT_DUR.get(c.sfx, 0.5))
        d = min(d, 3.0)
        if c.sfx in ("car", "hum", "whirr", "rotor", "motor"):
            d = c.dur or sfxlib.DEFAULT_DUR[c.sfx]
        t_on = c.t - 0.03
        t_off = c.t + d
        i0 = max(0, int(t_on * ctrl))
        i1 = min(m, int(t_off * ctrl))
        a[i0:i1] += w
    a = np.clip(a, 0.0, 1.0)
    # hold-and-release: instant attack, 350 ms exponential release
    rel = np.exp(-1.0 / (0.35 * ctrl))
    y = np.empty(m)
    cur = 0.0
    for i in range(m):
        cur = max(a[i], cur * rel)
        y[i] = cur
    # soften the edges with a 20 ms Hann window
    k = np.hanning(21)
    k /= k.sum()
    y = np.convolve(y, k, mode="same")
    return y, ctrl


def apply_ducking(music, cues, log):
    y, ctrl = duck_curve(cues)
    t = np.arange(N_TOTAL) / SR
    amt = np.interp(t, np.arange(len(y)) / ctrl, y)
    lo = dsp.lp(music, 150.0, 2)
    hi = music - lo
    g_hi = db2lin(-DUCK_DEPTH_DB * amt)
    g_lo = db2lin(-0.33 * DUCK_DEPTH_DB * amt)
    out = lo * g_lo[:, None] + hi * g_hi[:, None]
    depth = -20.0 * np.log10(np.maximum(g_hi, 1e-9))
    log(f"  ducking: deepest {depth.max():.2f} dB, music ducked more than 1 dB for {np.mean(depth > 1.0) * FILM_S:.1f} s of the film")
    return out, dict(max_db=float(depth.max()), seconds_over_1db=float(np.mean(depth > 1.0) * FILM_S), curve=amt)
