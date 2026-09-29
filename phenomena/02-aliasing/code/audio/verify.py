"""Checks the finished files by measurement, because nobody can listen while the script runs.

Run automatically at the end of make_audio.py, or on its own:  python3 audio/verify.py
It re-reads the three .wav files from build/audio/ and reports:
  format and length, NaN / inf, clipping, DC offset, fade-in and the silence at the end,
  loudness (pyloudnorm and ffmpeg ebur128 / loudnorm) and true peak (own 8x oversampling and ffmpeg),
  spectral balance (share above 12 kHz, sub-bass share), stereo width and low-end mono-ness,
  tuning of the bass and a bell against A4 = 440 Hz,
  music onsets against the beat grid, every sound-effect cue against its time,
  how loud the sound effects are compared with the music around them.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from PIL import Image, ImageDraw
from scipy import signal

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dsp                      # noqa: E402
from dsp import SR              # noqa: E402

GRID = 0.125                    # a sixteenth note at 120 BPM


# ---------------------------------------------------------------------------- helpers
def _mono(x):
    return x.mean(axis=1) if x.ndim == 2 else x


def band_shares(x, sr=SR):
    f, P = signal.welch(_mono(x), sr, nperseg=8192)
    tot = float(P.sum())
    edges = [0, 40, 60, 120, 250, 500, 1000, 2000, 4000, 8000, 12000, sr / 2]
    out = {}
    for lo, hi in zip(edges[:-1], edges[1:]):
        out[f"{int(lo)}-{int(hi)}"] = 100.0 * float(P[(f >= lo) & (f < hi)].sum()) / tot
    centroid = float((f * P).sum() / tot)
    return out, centroid, f, P


def _run_ffmpeg(path):
    res = {}
    try:
        r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=300)
        txt = r.stderr
        tail = txt[txt.rfind("Summary:"):] if "Summary:" in txt else txt[-1500:]
        m = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
        res["ebur128_integrated_lufs"] = float(m.group(1)) if m else None
        m = re.search(r"LRA:\s+(-?[\d.]+) LU", tail)
        res["ebur128_lra_lu"] = float(m.group(1)) if m else None
        m = re.search(r"True peak:\s*\n\s*Peak:\s+(-?[\d.]+) dBFS", tail)
        res["ebur128_true_peak_dbtp"] = float(m.group(1)) if m else None
        r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-af",
                            "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True, timeout=300)
        m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S)
        if m:
            j = json.loads(m.group(0))
            res["loudnorm_input_i"] = float(j["input_i"])
            res["loudnorm_input_tp"] = float(j["input_tp"])
            res["loudnorm_input_lra"] = float(j["input_lra"])
    except Exception as e:                      # ffmpeg missing
        res["ffmpeg_error"] = str(e)
    return res


def _colormap(v):
    stops = np.array([0.0, 0.25, 0.5, 0.75, 1.0])
    cols = np.array([[8, 8, 24], [40, 40, 150], [170, 40, 150], [240, 140, 40], [255, 245, 200]], float)
    out = np.zeros(v.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(v, stops, cols[:, c])
    return out.astype(np.uint8)


def spectrogram_png(x, path, t0=0.0, fmax=8000, nfft=4096, hop=1024, dyn=80, width=1600, title=""):
    x = _mono(x)
    f, t, S = signal.stft(x, SR, nperseg=nfft, noverlap=nfft - hop, window="hann")
    P = 20 * np.log10(np.abs(S) + 1e-10)
    P = P[f <= fmax]
    P = np.clip((P - (P.max() - dyn)) / dyn, 0, 1)
    im = Image.fromarray(_colormap(P[::-1])).resize((width, 380), Image.BILINEAR)
    canvas = Image.new("RGB", (width + 70, 380 + 50), (20, 20, 20))
    canvas.paste(im, (60, 10))
    d = ImageDraw.Draw(canvas)
    dur = len(x) / SR
    step = 10 if dur > 60 else 5 if dur > 30 else 2 if dur > 12 else 1 if dur > 5 else 0.5 if dur > 2 else 0.1
    tt = 0.0
    while tt <= dur + 1e-9:
        px = 60 + tt / dur * width
        d.line([(px, 390), (px, 396)], fill=(200, 200, 200))
        d.text((px - 10, 398), f"{t0 + tt:g}", fill=(200, 200, 200))
        tt += step
    for fk in (100, 500, 1000, 2000, 4000, 8000, 12000):
        if fk <= fmax:
            py = 10 + 380 - fk / fmax * 380
            d.line([(54, py), (60, py)], fill=(200, 200, 200))
            d.text((4, py - 6), str(fk), fill=(200, 200, 200))
    d.text((70, 12), title, fill=(255, 255, 255))
    canvas.save(path)


# ---------------------------------------------------------------------------- onsets
def detect_onsets(x, lo, hi, smooth_ms=1.5, ratio=2.2, min_gap=0.03):
    """Blind onset detector: times (s) where the level of a frequency band jumps to more than `ratio`
    times its average of the previous 5 to 25 ms. It works well on noisy percussion (hats); for tonal
    plucks a matched filter is used instead."""
    from scipy import ndimage
    y = dsp.bp(x, lo, hi, 2)
    e = ndimage.uniform_filter1d(np.abs(y), max(1, int(smooth_ms * 1e-3 * SR)))
    n = len(e)
    cs = np.concatenate([[0.0], np.cumsum(e)])
    i = np.arange(n)
    a = np.clip(i - int(0.025 * SR), 0, n)
    b = np.clip(i - int(0.005 * SR), 0, n)
    mean = (cs[b] - cs[a]) / np.maximum(b - a, 1)
    ok = (e > ratio * mean) & (e > 1.5 * np.percentile(e, 40))
    edge = np.where(ok & ~np.concatenate([[False], ok[:-1]]))[0]
    out, last = [], -10 ** 9
    for c in edge:
        if c - last > min_gap * SR:
            out.append(c)
        last = c
    return np.array(out) / SR


def _judge(det, times, detail, name, tol=0.02):
    """Compare detected onsets with the scheduled times and store the statistics."""
    times = np.asarray(times, dtype=float)
    errs = []
    for t in times:
        j = det[np.abs(det - t) < tol]
        if len(j):
            errs.append(float(j[np.argmin(np.abs(j - t))] - t) * 1000.0)
    if not errs:
        return
    e = np.array(errs)
    near = np.array([np.min(np.abs(times - t)) for t in det]) * 1000.0 if len(det) else np.array([0.0])
    detail[name] = dict(found=int(len(e)), of=int(len(times)), median_ms=float(np.median(e)), p05_ms=float(np.percentile(e, 5)),
                        p95_ms=float(np.percentile(e, 95)), max_abs_ms=float(np.abs(e).max()), detections=int(len(det)),
                        detections_within_5ms_of_an_event_pct=float(100 * np.mean(near < 5.0)))


def onset_check(music, score, log):
    """Are the music's onsets on the beat?
    (a) by construction: every scheduled event is a multiple of a sixteenth note (0.125 s) and every scene
        starts on a bar line;
    (b) measured: the noisy hats are found blind in the finished music.wav; the kick, rim clicks and plucks
        (whose onsets are buried in pad and reverb) are found blind in their own dry tracks, which the
        same script renders again for this check."""
    import instruments as ins
    mono = _mono(music)
    n = music.shape[0]
    res = {}
    marks = {}
    for t, kind in score.marks:
        marks.setdefault(kind, []).append(t)
    dev = []
    for kind in ("pluck", "kick", "hat", "rim", "bell", "keys", "bass"):
        for t in marks.get(kind, []):
            dev.append(abs(t / GRID - round(t / GRID)) * GRID)
    res["scheduled_events"] = int(len(dev))
    res["scheduled_max_off_grid_ms"] = float(max(dev) * 1000.0) if dev else 0.0
    scene_off = [abs(s["t0"] / 2.0 - round(s["t0"] / 2.0)) * 2.0 for s in score.T_scenes]
    res["scene_starts_max_off_bar_ms"] = float(max(scene_off) * 1000.0) if scene_off else 0.0
    detail = {}
    if score.hat:
        _judge(detect_onsets(mono, 4500, 9500), [h["t"] for h in score.hat], detail, "hat, in the finished music.wav")
    kick, hat, rim = ins.render_drums(score.kick, [], score.rim, n)
    if score.kick:
        _judge(detect_onsets(kick, 35, 250, smooth_ms=4.0, ratio=2.0), [k["t"] for k in score.kick], detail, "kick, dry track")
    if score.rim:
        _judge(detect_onsets(_mono(rim), 1200, 5000, smooth_ms=1.0), [r["t"] for r in score.rim], detail, "rim click, dry track")
    if score.pluck:
        pl = _mono(ins.render_pluck(score.pluck, n, score.bend))
        # the octave doublings and the pickup notes are separate notes on the same grid: judge all of them
        _judge(detect_onsets(pl, 700, 6000, smooth_ms=1.5, ratio=1.8), sorted({round(e["t"], 6) for e in score.pluck}), detail, "pluck, dry track")
    res["by_kind"] = detail
    starts = {}
    for sc in score.T_scenes:
        t = sc["t0"]
        near = [(k, round((tt - t) * 1000.0, 2)) for tt, k in score.marks if abs(tt - t) < 0.02]
        starts[sc["id"]] = near[:6]
    res["events_on_scene_starts"] = starts
    return res


# ---------------------------------------------------------------------------- cues
def cue_check(sfx_stem, cues, records, score, log):
    """Where is every cue really? Each sound is re-made and slid along the finished sfx.wav (a matched
    filter): the position of the best match, within 25 ms of the intended time, is the true placement.
    This does not use the renderer's own bookkeeping, and overlapping sounds do not fool it. A steady tone
    (hum, a shimmer, a blip) matches equally well one period away; among matches within 2 % of the best
    the one nearest to the intended time is taken."""
    import sfx as sfxlib
    x = dsp.hp(_mono(sfx_stem), 150.0, 2)
    rows = []
    for c, r in zip(cues, records):
        snd = sfxlib.REGISTRY[c.sfx](c, score)
        ref = dsp.hp(_mono(snd.audio), 150.0, 2)
        expect = dsp.idx(c.t)
        pad = int(0.025 * SR)
        a, b = max(0, expect - pad), min(len(x), expect + len(ref) + pad)
        seg = x[a:b]
        row = dict(t=r["t"], sfx=r["sfx"], dur=r["dur"], gain=r["gain"], scene=r["scene"], kind=r["kind"],
                   bookkeeping_error_ms=float((r["start_sample"] + r["anchor"] - dsp.idx(r["t"] + ((r["dur"] or 0.0) if r["anchor"] else 0.0))) * 1000.0 / SR))
        e_ref = float(np.sum(ref ** 2))
        if len(seg) < len(ref) or e_ref < 1e-20:
            row.update(lag_ms=None, match=None)
            rows.append(row)
            continue
        corr = signal.fftconvolve(seg, ref[::-1], mode="valid")
        cs = np.concatenate([[0.0], np.cumsum(seg ** 2)])
        win_e = cs[len(ref):] - cs[:-len(ref)]
        nc = corr / (np.sqrt(np.maximum(win_e, 0.0) * e_ref) + 1e-18)
        best = float(nc.max())
        near = np.where(nc >= 0.98 * best)[0]
        k = int(near[np.argmin(np.abs((a + near) - expect))])
        lag = (a + k) - expect
        row.update(lag_samples=int(lag), lag_ms=float(lag * 1000.0 / SR), match=float(nc[k]))
        if r["kind"] == "swell" and r["anchor"]:
            row["lands_at_s"] = float((expect + lag + r["anchor"]) / SR)
        rows.append(row)
    return rows


def sfx_vs_music(sfx_stem, music_stem, records):
    """How loud is each cue against the music at the same moment (RMS in 200 Hz - 6 kHz)."""
    xs = dsp.bp(_mono(sfx_stem), 200, 6000, 2)
    xm = dsp.bp(_mono(music_stem), 200, 6000, 2)
    rows = []
    for r in records:
        length = r["dur"] if r["dur"] else min(r["length_s"], 0.25)
        length = min(max(length, 0.05), 3.0)
        a, b = dsp.idx(r["t"]), dsp.idx(r["t"] + length)
        if r["kind"] == "impulse":
            b = a + int(0.12 * SR)
        es = np.sqrt(np.mean(xs[a:b] ** 2) + 1e-14)
        em = np.sqrt(np.mean(xm[a:b] ** 2) + 1e-14)
        pk = np.max(np.abs(xs[a:b])) + 1e-9
        rows.append(dict(t=r["t"], sfx=r["sfx"], rms_vs_music_db=float(20 * np.log10(es / em)),
                         peak_vs_music_rms_db=float(20 * np.log10(pk / em))))
    return rows


# ---------------------------------------------------------------------------- tuning
def _peak_freq_sig(seg, f_lo, f_hi):
    seg = seg * np.hanning(len(seg))
    n = 1 << 20
    S_ = np.abs(np.fft.rfft(seg, n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    m = (f >= f_lo) & (f <= f_hi)
    i = int(np.argmax(np.where(m, S_, 0)))
    a, b, c = np.log(S_[i - 1] + 1e-12), np.log(S_[i] + 1e-12), np.log(S_[i + 1] + 1e-12)
    d = 0.5 * (a - c) / (a - 2 * b + c)
    return float(f[i] + d * (f[1] - f[0]))


def _centroid(seg, f0, span_cents=60):
    seg = seg * np.hanning(len(seg))
    n = 1 << 20
    S_ = np.abs(np.fft.rfft(seg, n)) ** 2
    f = np.fft.rfftfreq(n, 1.0 / SR)
    m = (f >= f0 * 2 ** (-span_cents / 1200)) & (f <= f0 * 2 ** (span_cents / 1200))
    return float(np.sum(f[m] * S_[m]) / np.sum(S_[m]))


def tuning_check(music, S):
    """Equal temperament with A4 = 440 Hz: (1) each instrument alone, (2) a bass note inside the finished mix."""
    import instruments as ins
    out = {}
    cents = lambda f, ref: float(1200 * np.log2(f / ref))
    a4, a1, d5 = 440.0, 55.0, 587.3295
    w = ins.pluck_wave(69, 3000.0)[: int(0.5 * SR)]
    out["pluck_A4_cents"] = cents(_peak_freq_sig(w, 400, 480), a4)
    w = ins.bell_wave(69, 2.0)[: int(1.0 * SR)]
    out["bell_A4_cents"] = cents(_centroid(w, a4, 30), a4)          # two copies detuned by -3 / +3 cents
    w = ins.bass_note(33, 1.6, 0.0, t0=0.0)[int(0.2 * SR): int(1.4 * SR)]
    out["bass_A1_cents"] = cents(_peak_freq_sig(w, 45, 65), a1)
    k = ins.keys_note(69, 1.2, 0.0)[:, 0][int(0.3 * SR): int(1.0 * SR)]
    out["keys_A4_cents"] = cents(_peak_freq_sig(k, 400, 480), a4)
    pad = ins.render_pad([dict(layer="main", voice=0, t0=0.0, t1=3.0, midi=69, db=0.0, att=0.5, rel=0.5)], int(3.6 * SR)).mean(axis=1)[int(1.0 * SR): int(2.6 * SR)]
    out["pad_A4_centroid_cents"] = cents(_centroid(pad, a4), a4)
    out["definition_A4_hz"] = float(dsp.midi_hz(69))
    # a bass note inside the mix: the longest one with no other bass note and no tape bend near it
    best = None
    for e in S.bass:
        dur = e["t1"] - e["t0"]
        if dur < 1.4 or e["midi"] >= 45:
            continue
        clash = any(o is not e and abs(o["t0"] - e["t0"]) < dur + 0.3 for o in S.bass)
        bent = S.bend is not None and S.bend.touches(e["t0"] - 0.5, e["t1"] + 0.5)
        if not clash and not bent and e["t0"] > 5.0:
            best = e if best is None or dur > best["t1"] - best["t0"] else best
    if best is not None:
        f_ref = float(dsp.midi_hz(best["midi"]))
        seg = _mono(music)[dsp.idx(best["t0"] + 0.3): dsp.idx(best["t0"] + 1.3)]
        seg = dsp.lp(seg, 200, 4)
        f = _peak_freq_sig(seg, f_ref * 0.95, f_ref * 1.05)
        out["mix_bass_note_midi"] = int(best["midi"])
        out["mix_bass_note_hz"] = f
        out["mix_bass_note_cents"] = cents(f, f_ref)
    return out


def harmony_audit(S):
    """Every pitched note in the score against the chord that is playing: no wrong notes."""
    from score import CH
    extra = {2: (4, 7, 0), 10: (0,), 5: (7,), 0: (2,), 7: (9,)}   # tolerated colour tones: 9th, 11th and 7th over Dm
    counts = dict(total=0, chord_tone=0, colour_tone=0, outside=0)
    outside = []
    for kind, ev, key in (("pad", S.pad, "t0"), ("pluck", S.pluck, "t"), ("bell", S.bell, "t"), ("keys", S.keys, "t0"), ("bass", S.bass, "t0")):
        for e in ev:
            t = e[key]
            c = CH[S.chord_at(t + (0.01 if kind in ("pad", "keys") else 0.0))]
            strict = {m % 12 for m in c["pad"]} | {m % 12 for m in c["pool"]} | {m % 12 for m in c["keys"]} | {c["bass"] % 12, c["root"]}
            pc = e["midi"] % 12
            counts["total"] += 1
            if pc in strict:
                counts["chord_tone"] += 1
            elif pc in extra.get(c["root"], ()):
                counts["colour_tone"] += 1
            else:
                counts["outside"] += 1
                outside.append((round(t, 3), kind, int(e["midi"]), S.chord_at(t)))
    counts["outside_list"] = outside[:12]
    return counts


# ---------------------------------------------------------------------------- main
def run_all(out_dir, S, timeline, cue_records, cues, info, log, plots=True, comp="main", duration=180.0,
            names=("main.wav", "music.wav", "sfx.wav")):
    out_dir = Path(out_dir)
    rep = {}
    fmain, fmusic, fsfx = names
    FILM_S = float(duration)
    main, sr = sf.read(str(out_dir / fmain), dtype="float64")
    music, _ = sf.read(str(out_dir / fmusic), dtype="float64")
    sfxs, _ = sf.read(str(out_dir / fsfx), dtype="float64")
    S.T_scenes = timeline["scenes"]

    # ---- format
    inf = sf.info(str(out_dir / fmain))
    rep["format"] = dict(sample_rate=sr, channels=inf.channels, subtype=inf.subtype, samples=int(main.shape[0]),
                         duration_s=main.shape[0] / sr, ok=(sr == 48000 and inf.channels == 2 and inf.subtype == "PCM_24"
                                                             and main.shape[0] == int(round(FILM_S * 48000))))
    for name, x, fn in (("music", music, fmusic), ("sfx", sfxs, fsfx)):
        i2 = sf.info(str(out_dir / fn))
        rep["format"][f"{name}_ok"] = bool(i2.samplerate == 48000 and i2.channels == 2 and i2.subtype == "PCM_24" and x.shape[0] == main.shape[0])
    rep["finite"] = {n: bool(np.isfinite(x).all()) for n, x in (("main", main), ("music", music), ("sfx", sfxs))}

    # ---- clipping, dc, fades
    pk = float(np.max(np.abs(main)))
    rep["clipping"] = dict(sample_peak_dbfs=float(dsp.lin2db(pk)), samples_at_or_above_0p999=int(np.sum(np.abs(main) >= 0.999)))
    rep["dc_offset"] = dict(main=[float(v) for v in main.mean(axis=0)], music=[float(v) for v in music.mean(axis=0)],
                            sfx=[float(v) for v in sfxs.mean(axis=0)])
    first = main[:int(0.35 * sr)]
    rep["fade_in"] = dict(first_sample=[float(v) for v in main[0]], first_10ms_peak_dbfs=float(dsp.lin2db(np.max(np.abs(main[:int(0.01 * sr)])))),
                          peak_first_0p35s_dbfs=float(dsp.lin2db(np.max(np.abs(first)))))
    last = main[-int(0.5 * sr):]
    rep["silence_end"] = dict(last_0p5s_peak_dbfs=float(dsp.lin2db(np.max(np.abs(last)))), last_sample=[float(v) for v in main[-1]],
                              last_0p5s_all_zero=bool(not last.any()),
                              peak_1s_to_0p5s_before_end_dbfs=float(dsp.lin2db(np.max(np.abs(main[int((FILM_S - 1.0) * sr):int((FILM_S - 0.5) * sr)])))))
    rep["stems_sum_max_abs_diff"] = float(np.max(np.abs(main - (music + sfxs))))

    # ---- loudness and peaks
    meter = pyln.Meter(sr)
    rep["loudness"] = dict(main_lufs=float(meter.integrated_loudness(main)), music_lufs=float(meter.integrated_loudness(music)),
                           sfx_lufs=float(meter.integrated_loudness(sfxs)))
    rep["true_peak_own_8x_dbtp"] = dict(main=dsp.true_peak_db(main), music=dsp.true_peak_db(music), sfx=dsp.true_peak_db(sfxs))
    rep["ffmpeg"] = _run_ffmpeg(out_dir / "main.wav")
    # loudness through time (3 s windows, every 3 s) for the report
    track = []
    for t in range(0, int(FILM_S), 3):
        seg = main[t * sr:(t + 3) * sr]
        try:
            track.append(round(float(meter.integrated_loudness(seg)), 1))
        except Exception:
            track.append(None)
    rep["short_term_lufs_3s"] = track
    per_scene = {}
    for s in timeline["scenes"]:
        a, b = int(s["t0"] * sr), int(min(s["t1"], FILM_S) * sr)
        try:
            per_scene[s["id"]] = dict(lufs=round(float(meter.integrated_loudness(main[a:b])), 2),
                                      peak_dbfs=round(float(dsp.lin2db(np.max(np.abs(main[a:b])))), 2))
        except Exception:
            per_scene[s["id"]] = None
    rep["per_scene"] = per_scene

    # ---- spectrum
    shares, centroid, f, P = band_shares(main)
    rep["spectrum_main"] = dict(band_share_pct=shares, centroid_hz=centroid,
                                above_12k_db_rel_total=float(10 * np.log10(max(shares["12000-24000"], 1e-9) / 100.0)),
                                below_60_pct=shares["0-40"] + shares["40-60"])
    sm, cm, _, _ = band_shares(music)
    ss, cs, _, _ = band_shares(sfxs)
    rep["spectrum_music"] = dict(band_share_pct=sm, centroid_hz=cm)
    rep["spectrum_sfx"] = dict(band_share_pct=ss, centroid_hz=cs)

    # ---- stereo
    L, R = main[:, 0], main[:, 1]
    mid, side = 0.5 * (L + R), 0.5 * (L - R)
    corr = float(np.corrcoef(L, R)[0, 1])
    lowm, lows = dsp.lp(mid, 150, 4), dsp.lp(side, 150, 4)
    rep["stereo"] = dict(correlation=corr, side_to_mid_db=float(10 * np.log10(np.sum(side ** 2) / np.sum(mid ** 2))),
                         below_150hz_side_to_mid_db=float(10 * np.log10((np.sum(lows ** 2) + 1e-20) / np.sum(lowm ** 2))))

    # ---- tuning
    rep["tuning"] = tuning_check(music, S)
    rep["harmony_audit"] = harmony_audit(S)

    # ---- music onsets and cues
    rep["music_onsets"] = onset_check(music, S, log)
    rep["cues"] = cue_check(sfxs, cues, cue_records, S, log)
    rep["sfx_vs_music"] = sfx_vs_music(sfxs, music, cue_records)
    rep["mix_info"] = dict(layer_gain_db=info["layers"]["layer_gain_db"], contour=info["scenes"], duck_max_db=info["duck"]["max_db"],
                           duck_seconds_over_1db=info["duck"]["seconds_over_1db"], master=dict(gain_db=info["master"]["gain_db"],
                           pre_lufs=info["master"]["pre_lufs"], limiter=info["master"]["limiter"]))
    rep["sha256"] = {fn: hashlib.sha256(open(out_dir / fn, "rb").read()).hexdigest() for fn in names}

    if plots:
        pd = out_dir / ("plots" if comp == "main" else f"plots_{comp}")
        pd.mkdir(exist_ok=True)
        spectrogram_png(main, pd / "film.png", 0.0, 12000, 4096, 4096 if FILM_S > 100 else 1024, 80, 1700, f"{fmain}, whole piece")
        if comp == "main":
            spectrogram_png(main[:24 * sr], pd / "hook_and_title.png", 0.0, 6000, 4096, 1024, 80, 1500, "0 to 24 s")
            spectrogram_png(music[int(6.5 * sr):int(9 * sr)], pd / "tape_sag_music.png", 6.5, 3000, 4096, 256, 80, 1400, "music only, 6.5 to 9 s (tape sag from 7.4 s)")
            spectrogram_png(main[int(108 * sr):int(122 * sr)], pd / "resolution_115s.png", 108.0, 8000, 4096, 512, 80, 1500, "108 to 122 s (resolution at 115 s)")
            spectrogram_png(main[int(166 * sr):], pd / "ending.png", 166.0, 8000, 4096, 512, 80, 1500, "166 to 180 s")
        else:
            spectrogram_png(music[int(5.5 * sr):int(8 * sr)], pd / "tape_sag_music.png", 5.5, 3000, 4096, 256, 80, 1400, "music only, 5.5 to 8 s (tape sag from 6.4 s)")
            spectrogram_png(main[int(30 * sr):], pd / "reveal_and_ending.png", 30.0, 8000, 4096, 512, 80, 1500, "30 to 45 s")
        spectrogram_png(sfxs, pd / "sfx_stem.png", 0.0, 8000, 4096, 4096 if FILM_S > 100 else 1024, 70, 1700, f"{fsfx}")

    summarise(rep, log)
    return rep


def summarise(rep, log):
    f = rep["format"]
    log("---- measurements ----")
    log(f"format: {f['sample_rate']} Hz, {f['channels']} ch, {f['subtype']}, {f['samples']} samples = {f['duration_s']:.4f} s "
        f"(main ok={f['ok']}, music ok={f['music_ok']}, sfx ok={f['sfx_ok']})")
    log(f"finite (no NaN/inf): {rep['finite']}")
    c = rep["clipping"]
    log(f"clipping: sample peak {c['sample_peak_dbfs']:.2f} dBFS, samples >= 0.999: {c['samples_at_or_above_0p999']}")
    log(f"dc offset (main): {rep['dc_offset']['main'][0]:.2e}, {rep['dc_offset']['main'][1]:.2e}")
    fi, se = rep["fade_in"], rep["silence_end"]
    log(f"fade-in: first sample {fi['first_sample']}, first 10 ms peak {fi['first_10ms_peak_dbfs']:.1f} dBFS; "
        f"end: last 0.5 s peak {se['last_0p5s_peak_dbfs']:.1f} dBFS (all zero: {se['last_0p5s_all_zero']}), the 0.5 s before that peaks at {se['peak_1s_to_0p5s_before_end_dbfs']:.1f} dBFS")
    l = rep["loudness"]
    log(f"loudness (pyloudnorm BS.1770-4): main {l['main_lufs']:.2f} LUFS, music {l['music_lufs']:.2f}, sfx {l['sfx_lufs']:.2f}")
    fm = rep["ffmpeg"]
    log(f"ffmpeg ebur128: I {fm.get('ebur128_integrated_lufs')} LUFS, LRA {fm.get('ebur128_lra_lu')} LU, true peak {fm.get('ebur128_true_peak_dbtp')} dBTP; "
        f"loudnorm: I {fm.get('loudnorm_input_i')}, TP {fm.get('loudnorm_input_tp')}, LRA {fm.get('loudnorm_input_lra')}")
    tp = rep["true_peak_own_8x_dbtp"]
    log(f"true peak (own 8x oversampling): main {tp['main']:.2f} dBTP, music {tp['music']:.2f}, sfx {tp['sfx']:.2f}")
    log(f"stems: music + sfx differs from main by at most {rep['stems_sum_max_abs_diff']:.2e}")
    sp = rep["spectrum_main"]
    log("spectrum share of power (%): " + ", ".join(f"{k}: {v:.2f}" for k, v in sp["band_share_pct"].items()) + f"; centroid {sp['centroid_hz']:.0f} Hz")
    log(f"  above 12 kHz: {sp['above_12k_db_rel_total']:.1f} dB relative to the total; below 60 Hz: {sp['below_60_pct']:.1f} % of the power")
    st = rep["stereo"]
    log(f"stereo: L/R correlation {st['correlation']:.2f}, side/mid {st['side_to_mid_db']:.1f} dB, below 150 Hz side/mid {st['below_150hz_side_to_mid_db']:.1f} dB")
    t = rep["tuning"]
    log("tuning against A4 = 440 Hz (cents): " + ", ".join(f"{k.replace('_cents', '')} {v:+.2f}" for k, v in t.items() if k.endswith("cents")))
    h = rep["harmony_audit"]
    log(f"harmony: {h['total']} pitched notes, {h['chord_tone']} chord tones, {h['colour_tone']} colour tones (9th), {h['outside']} outside the chord {h['outside_list']}")
    o = rep["music_onsets"]
    log(f"music onsets: {o['scheduled_events']} scheduled events, largest distance from the sixteenth grid {o['scheduled_max_off_grid_ms']:.3f} ms; "
        f"scenes off bar line: {o['scene_starts_max_off_bar_ms']:.3f} ms")
    for k, v in o["by_kind"].items():
        extra = ""
        if "detections" in v:
            extra = f"; {v['detections']} onsets detected in total, {v['detections_within_5ms_of_an_event_pct']:.1f} % within 5 ms of a scheduled event"
        log(f"  {k}: {v['found']}/{v['of']} found in the audio, measured - scheduled: median {v['median_ms']:+.2f} ms, 5-95 % {v['p05_ms']:+.2f}..{v['p95_ms']:+.2f} ms, worst {v['max_abs_ms']:.2f} ms{extra}")
    log("scene start events: " + "; ".join(f"{k.split('_')[0]}: {sorted({e[0] for e in v})}" for k, v in o["events_on_scene_starts"].items()))
    cues = rep["cues"]
    lags = [abs(c["lag_ms"]) for c in cues if c.get("lag_ms") is not None]
    log(f"cues: {len(cues)} placed; matched-filter position of each sound in sfx.wav: largest offset from its time {max(lags) if lags else float('nan'):.3f} ms "
        f"(weakest match {min((c['match'] for c in cues if c.get('match') is not None), default=float('nan')):.2f}); renderer bookkeeping error {max((abs(c['bookkeeping_error_ms']) for c in cues), default=0.0):.3f} ms")
    for c in cues:
        lag = "n/a" if c.get("lag_ms") is None else f"{c['lag_ms']:+.3f} ms (match {c['match']:.2f})"
        land = f", lands at {c['lands_at_s']:.3f} s" if c.get("lands_at_s") else ""
        log(f"  t={c['t']:8.3f}  {c['sfx']:11s} dur={c['dur']}  gain={c['gain']:+.0f}  offset {lag}{land}")
    sv = rep["sfx_vs_music"]
    if sv:
        d = np.array([r["rms_vs_music_db"] for r in sv])
        log(f"sfx against the music at the same moment (200 Hz - 6 kHz RMS): median {np.median(d):+.1f} dB, range {d.min():+.1f}..{d.max():+.1f} dB")
    mi = rep["mix_info"]
    log(f"ducking: deepest {mi['duck_max_db']:.2f} dB; music ducked by more than 1 dB for {mi['duck_seconds_over_1db']:.1f} s")
    log("per scene (LUFS / sample peak dBFS): " + "; ".join(f"{k.split('_')[0]} {v['lufs']:.1f}/{v['peak_dbfs']:.1f}" for k, v in rep["per_scene"].items() if v))


if __name__ == "__main__":
    # stand-alone: re-measure the files that are already on disk (uses the score for the onset check)
    import score as scorelib
    code = HERE.parent
    tl = json.load(open(code / "build" / "main_timeline.json"))
    S = scorelib.build_score(tl["scenes"], print)
    print("stand-alone verification is available through make_audio.py (it needs the cue bookkeeping); "
          "run: python3 audio/make_audio.py")
