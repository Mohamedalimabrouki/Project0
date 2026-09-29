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

FILM_S = 180.0
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
def detect_onsets(x, lo, hi, rise_db=7.0, min_gap=0.035):
    """Times (s) where the band-passed signal jumps up quickly (a struck or plucked sound)."""
    y = dsp.bp(x, lo, hi, 2)
    env = np.abs(y)
    k = int(0.0015 * SR)
    env = np.convolve(env, np.ones(k) / k, mode="same")
    envdb = 20 * np.log10(env + 1e-9)
    lag = int(0.004 * SR)
    d = envdb[lag:] - envdb[:-lag]
    d = np.concatenate([np.zeros(lag), d])
    floor = np.percentile(envdb, 20)
    cand = np.where((d > rise_db) & (envdb > floor + 6))[0]
    if len(cand) == 0:
        return np.array([])
    groups = np.split(cand, np.where(np.diff(cand) > int(min_gap * SR))[0] + 1)
    times = []
    for g in groups:
        a = g[0]
        b = min(len(d), g[-1] + int(0.01 * SR))
        seg = np.diff(envdb[max(0, a - lag): b])           # steepest rise inside the group
        times.append((max(0, a - lag) + int(np.argmax(seg)) + 0.5) / SR)
    return np.array(times)


def onset_check(music, score, log):
    mono = _mono(music)
    res = {}
    marks = {}
    for t, kind in score.marks:
        marks.setdefault(kind, []).append(t)
    # by construction: every scheduled onset sits on the sixteenth-note grid, every scene on a bar line
    dev = []
    for kind in ("pluck", "kick", "hat", "rim", "bell", "keys", "bass"):
        for t in marks.get(kind, []):
            dev.append(abs(t / GRID - round(t / GRID)) * GRID)
    res["scheduled_events"] = int(len(dev))
    res["scheduled_max_off_grid_ms"] = float(max(dev) * 1000.0) if dev else 0.0
    scene_off = [abs(s["t0"] / 2.0 - round(s["t0"] / 2.0)) * 2.0 for s in score.T_scenes] if hasattr(score, "T_scenes") else []
    res["scene_starts_max_off_bar_ms"] = float(max(scene_off) * 1000.0) if scene_off else 0.0
    # measured: kick from the low band, the rest from the mid/high band
    bands = {"kick": (35, 140), "pluck": (900, 6000), "hat": (3000, 9000), "rim": (1200, 5000)}
    detail = {}
    for kind, (lo, hi) in bands.items():
        ts = np.array(marks.get(kind, []))
        if len(ts) == 0:
            continue
        # isolate crowded regions: only judge marks that have no other mark of any kind within 40 ms
        allt = np.array(sorted(t for t, k in score.marks))
        det = detect_onsets(mono, lo, hi, rise_db=(5.0 if kind == "kick" else 7.0))
        errs = []
        for t in ts:
            near = allt[(np.abs(allt - t) < 0.04) & (np.abs(allt - t) > 1e-6)]
            if len(near):
                continue
            j = det[np.abs(det - t) < 0.03]
            if len(j):
                errs.append(float(j[np.argmin(np.abs(j - t))] - t) * 1000.0)
        if errs:
            e = np.array(errs)
            detail[kind] = dict(judged=int(len(e)), of=int(len(ts)), median_ms=float(np.median(e)), p05_ms=float(np.percentile(e, 5)),
                                p95_ms=float(np.percentile(e, 95)), max_abs_ms=float(np.abs(e).max()))
    res["by_kind"] = detail
    # blind check: onsets found in the audio versus the nearest sixteenth-note gridline
    det = detect_onsets(mono, 900, 6000, rise_db=8.0)
    if len(det):
        off = np.abs((det / GRID) - np.round(det / GRID)) * GRID * 1000.0
        # subtract the typical detection lag of soft attacks so it is not counted as timing error
        lagged = np.abs(((det - 0.0015) / GRID) - np.round((det - 0.0015) / GRID)) * GRID * 1000.0
        res["blind_onsets"] = dict(count=int(len(det)), within_5ms_pct=float(100.0 * np.mean(lagged <= 5.0)),
                                   within_10ms_pct=float(100.0 * np.mean(lagged <= 10.0)), median_off_grid_ms=float(np.median(lagged)),
                                   raw_median_ms=float(np.median(off)))
    # the scene starts: is there an audible event (pluck / kick / bell / bass note) on every scene start?
    starts = {}
    for s in score.T_scenes if hasattr(score, "T_scenes") else []:
        t = s["t0"]
        near = [(k, round((tt - t) * 1000.0, 2)) for tt, k in score.marks if abs(tt - t) < 0.02]
        starts[s["id"]] = near[:6]
    res["events_on_scene_starts"] = starts
    return res


# ---------------------------------------------------------------------------- cues
def cue_check(sfx_stem, records, log):
    """Independent look at every cue in the finished sfx.wav (not the bookkeeping of the renderer)."""
    x = _mono(sfx_stem)
    xh = dsp.hp(x, 200.0, 2)
    env = np.sqrt(np.convolve(xh ** 2, np.ones(int(0.0005 * SR)) / int(0.0005 * SR), mode="same"))
    out = []
    times = sorted(r["t"] for r in records)
    for r in records:
        t = r["t"]
        row = dict(t=t, sfx=r["sfx"], dur=r["dur"], gain=r["gain"], scene=r["scene"], kind=r["kind"])
        row["placed_error_ms"] = float((r["start_sample"] + r["anchor"] - dsp.idx(t + ((r["dur"] or 0.0) if r["anchor"] else 0.0))) * 1000.0 / SR)
        if r["kind"] == "impulse":
            crowded = any(0 < abs(t2 - t) < 0.08 for t2 in times)
            a, b = dsp.idx(t - 0.02), dsp.idx(t + 0.06)
            seg = env[a:b]
            if crowded or seg.max() <= 1e-9:
                row["detected_onset_ms"] = None
                row["note"] = "crowded" if crowded else "silent"
            else:
                thr = 0.12 * seg.max() if r["sfx"] != "hit" else 0.25 * seg.max()
                k = int(np.argmax(seg > thr))
                row["detected_onset_ms"] = float((a + k) / SR * 1000.0 - t * 1000.0)
        elif r["kind"] == "swell" and r["anchor"]:
            a, b = dsp.idx(t + (r["dur"] or 0.0) - 0.15), dsp.idx(t + (r["dur"] or 0.0) + 0.15)
            k = int(np.argmax(env[a:b]))
            row["detected_peak_ms_from_end"] = float((a + k) / SR * 1000.0 - (t + (r["dur"] or 0.0)) * 1000.0)
        out.append(row)
    return out


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
def _peak_freq(x, f_lo, f_hi, t0, dur=1.0):
    seg = x[dsp.idx(t0): dsp.idx(t0 + dur)]
    seg = seg * np.hanning(len(seg))
    n = 1 << 20
    S = np.abs(np.fft.rfft(seg, n))
    f = np.fft.rfftfreq(n, 1.0 / SR)
    m = (f >= f_lo) & (f <= f_hi)
    i = np.argmax(np.where(m, S, 0))
    # parabolic interpolation on the log magnitude
    a, b, c = np.log(S[i - 1] + 1e-12), np.log(S[i] + 1e-12), np.log(S[i + 1] + 1e-12)
    d = 0.5 * (a - c) / (a - 2 * b + c)
    return float(f[i] + d * (f[1] - f[0]))


def tuning_check(music):
    x = _mono(music)
    out = {}
    # D2 bass (Dm chord, 174.6 - 175.6 s): 73.416 Hz
    f = _peak_freq(dsp.lp(x, 200, 4), 60, 90, 174.6, 1.0)
    out["bass_D2_hz"] = f
    out["bass_D2_cents"] = float(1200 * np.log2(f / 73.4162))
    # Dm chord bell D5 after the motif (176.2 - 176.8 s): 587.33 Hz
    f = _peak_freq(x, 570, 605, 176.15, 0.6)
    out["bell_D5_hz"] = f
    out["bell_D5_cents"] = float(1200 * np.log2(f / 587.3295))
    # A4 pad partial in the F major chord 19.0 - 20.0 (A4 = 440 Hz is a chord tone of F)
    f = _peak_freq(x, 425, 455, 19.2, 0.8)
    out["pad_A4_hz"] = f
    out["pad_A4_cents"] = float(1200 * np.log2(f / 440.0))
    return out


# ---------------------------------------------------------------------------- main
def run_all(out_dir, S, timeline, cue_records, cues, info, log, plots=True):
    out_dir = Path(out_dir)
    rep = {}
    main, sr = sf.read(str(out_dir / "main.wav"), dtype="float64")
    music, _ = sf.read(str(out_dir / "music.wav"), dtype="float64")
    sfxs, _ = sf.read(str(out_dir / "sfx.wav"), dtype="float64")
    S.T_scenes = timeline["scenes"]

    # ---- format
    inf = sf.info(str(out_dir / "main.wav"))
    rep["format"] = dict(sample_rate=sr, channels=inf.channels, subtype=inf.subtype, samples=int(main.shape[0]),
                         duration_s=main.shape[0] / sr, ok=(sr == 48000 and inf.channels == 2 and inf.subtype == "PCM_24"
                                                             and main.shape[0] == int(FILM_S * 48000)))
    for name, x in (("music", music), ("sfx", sfxs)):
        i2 = sf.info(str(out_dir / f"{name}.wav"))
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
                              peak_179_0_to_179_5_dbfs=float(dsp.lin2db(np.max(np.abs(main[int(179.0 * sr):int(179.5 * sr)])))))
    rep["stems_sum_max_abs_diff"] = float(np.max(np.abs(main - (music + sfxs))))

    # ---- loudness and peaks
    meter = pyln.Meter(sr)
    rep["loudness"] = dict(main_lufs=float(meter.integrated_loudness(main)), music_lufs=float(meter.integrated_loudness(music)),
                           sfx_lufs=float(meter.integrated_loudness(sfxs)))
    rep["true_peak_own_8x_dbtp"] = dict(main=dsp.true_peak_db(main), music=dsp.true_peak_db(music), sfx=dsp.true_peak_db(sfxs))
    rep["ffmpeg"] = _run_ffmpeg(out_dir / "main.wav")
    # loudness through time (3 s windows, every 3 s) for the report
    track = []
    for t in range(0, 180, 3):
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
                                above_12k_db_rel_total=float(10 * np.log10(max(shares["12000-24000.0"], 1e-9) / 100.0)),
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
    rep["tuning"] = tuning_check(music)

    # ---- music onsets and cues
    rep["music_onsets"] = onset_check(music, S, log)
    rep["cues"] = cue_check(sfxs, cue_records, log)
    rep["sfx_vs_music"] = sfx_vs_music(sfxs, music, cue_records)
    rep["mix_info"] = dict(layer_gain_db=info["layers"]["layer_gain_db"], contour=info["scenes"], duck_max_db=info["duck"]["max_db"],
                           duck_seconds_over_1db=info["duck"]["seconds_over_1db"], master=dict(gain_db=info["master"]["gain_db"],
                           pre_lufs=info["master"]["pre_lufs"], limiter=info["master"]["limiter"]))
    rep["sha256"] = {n: hashlib.sha256(open(out_dir / f"{n}.wav", "rb").read()).hexdigest() for n in ("main", "music", "sfx")}

    if plots:
        pd = out_dir / "plots"
        pd.mkdir(exist_ok=True)
        spectrogram_png(main, pd / "film.png", 0.0, 12000, 4096, 4096, 80, 1700, "main.wav, whole film")
        spectrogram_png(main[:24 * sr], pd / "hook_and_title.png", 0.0, 6000, 4096, 1024, 80, 1500, "0 to 24 s")
        spectrogram_png(music[int(6.5 * sr):int(9 * sr)], pd / "tape_sag_music.png", 6.5, 3000, 4096, 256, 80, 1400, "music only, 6.5 to 9 s (tape sag from 7.4 s)")
        spectrogram_png(main[int(108 * sr):int(122 * sr)], pd / "resolution_115s.png", 108.0, 8000, 4096, 512, 80, 1500, "108 to 122 s (resolution at 115 s)")
        spectrogram_png(main[int(166 * sr):], pd / "ending.png", 166.0, 8000, 4096, 512, 80, 1500, "166 to 180 s")
        spectrogram_png(sfxs, pd / "sfx_stem.png", 0.0, 8000, 4096, 4096, 70, 1700, "sfx.wav")

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
        f"end: last 0.5 s peak {se['last_0p5s_peak_dbfs']:.1f} dBFS (all zero: {se['last_0p5s_all_zero']}), 179.0-179.5 s peak {se['peak_179_0_to_179_5_dbfs']:.1f} dBFS")
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
    log(f"tuning: bass D2 {t['bass_D2_hz']:.2f} Hz ({t['bass_D2_cents']:+.2f} cents), bell D5 {t['bell_D5_hz']:.2f} Hz ({t['bell_D5_cents']:+.2f} c), pad A4 {t['pad_A4_hz']:.2f} Hz ({t['pad_A4_cents']:+.2f} c)")
    o = rep["music_onsets"]
    log(f"music onsets: {o['scheduled_events']} scheduled events, largest distance from the sixteenth grid {o['scheduled_max_off_grid_ms']:.3f} ms; "
        f"scenes off bar line: {o['scene_starts_max_off_bar_ms']:.3f} ms")
    for k, v in o["by_kind"].items():
        log(f"  {k}: {v['judged']}/{v['of']} judged, detected - scheduled: median {v['median_ms']:+.1f} ms, 5-95 % {v['p05_ms']:+.1f}..{v['p95_ms']:+.1f} ms, worst {v['max_abs_ms']:.1f} ms")
    if "blind_onsets" in o:
        b = o["blind_onsets"]
        log(f"  blind check: {b['count']} onsets found in the audio, {b['within_5ms_pct']:.1f} % within 5 ms of the sixteenth grid, {b['within_10ms_pct']:.1f} % within 10 ms")
    log(f"scene start events: " + "; ".join(f"{k.split('_')[0]}: {[e[0] for e in v]}" for k, v in o["events_on_scene_starts"].items()))
    cues = rep["cues"]
    worst = max((abs(c["placed_error_ms"]) for c in cues), default=0.0)
    det = [c["detected_onset_ms"] for c in cues if c.get("detected_onset_ms") is not None]
    log(f"cues: {len(cues)} placed; largest placement error {worst:.3f} ms; measured onsets of {len(det)} impulsive cues: "
        + (f"within {max(abs(d) for d in det):.2f} ms of their time" if det else "n/a"))
    for c in cues:
        extra = ""
        if c.get("detected_onset_ms") is not None:
            extra = f" onset {c['detected_onset_ms']:+.2f} ms"
        if c.get("detected_peak_ms_from_end") is not None:
            extra = f" peak {c['detected_peak_ms_from_end']:+.1f} ms from cue end"
        log(f"  t={c['t']:8.3f}  {c['sfx']:11s} dur={c['dur']}  gain={c['gain']:+.0f}  error {c['placed_error_ms']:+.3f} ms{extra}")
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
