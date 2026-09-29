#!/usr/bin/env python3
"""Builds the whole soundtrack of "Engineering Phenomena 02 - Aliasing" from code.

    python3 audio/make_audio.py                 # from phenomena/02-aliasing/code/

Reads    build/main_timeline.json      (scene times and sound cues; made by
                                        `node render.mjs --comp main --lang en --timeline`)
Writes   build/audio/main.wav          the finished mix: 48 kHz, 24 bit, stereo, exactly 180.0 s,
                                        -14 LUFS, true peak below -1 dBTP
         build/audio/music.wav         the music alone (same level as in the mix)
         build/audio/sfx.wav           the sound effects alone (music.wav + sfx.wav = main.wav)
         build/audio/report.json       every measurement (also printed at the end)
         build/audio/plots/*.png       spectrograms, for a quick look

Everything is synthesised (no samples, nothing downloaded) and every random number comes from a
fixed seed, so the result is identical each time. See audio/README.md for a plain-language tour.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parent
sys.path.insert(0, str(HERE))

import numpy as np                      # noqa: E402
import soundfile as sf                  # noqa: E402

import dsp                              # noqa: E402
import mixer                            # noqa: E402
import master as mastering              # noqa: E402
import score as scorelib                # noqa: E402
import sfx as sfxlib                    # noqa: E402

SR = dsp.SR

DEFAULT_SCENES = [
    ("s01_hook", 0.0, 18.5), ("s02_title", 18.0, 24.5), ("s03_snapshots", 24.0, 48.5), ("s04_trick", 48.0, 86.5),
    ("s05_rule", 86.0, 126.5), ("s06_helicopter_lathe", 126.0, 148.5), ("s07_sensors_strobe", 148.0, 170.5),
    ("s08_takeaway", 170.0, 180.0),
]


class Logger:
    def __init__(self):
        self.lines = []
        self.warnings = []
        self.t0 = time.time()

    def __call__(self, msg):
        line = f"[{time.time() - self.t0:6.1f}s] {msg}"
        print(line, flush=True)
        self.lines.append(line)
        if "warning" in msg.lower():
            self.warnings.append(msg)


def load_timeline(path: Path, refresh: bool, log):
    if refresh or not path.exists():
        log("running: node render.mjs --comp main --lang en --timeline")
        try:
            r = subprocess.run(["node", "render.mjs", "--comp", "main", "--lang", "en", "--timeline"], cwd=CODE,
                               capture_output=True, text=True, timeout=600)
            log("  " + (r.stdout.strip().splitlines() or ["(no output)"])[0])
            if r.returncode != 0:
                log(f"warning: the timeline command failed ({r.returncode}): {r.stderr.strip()[:300]}")
        except Exception as e:                                  # node or Chromium missing
            log(f"warning: could not run the timeline command: {e}")
    if path.exists():
        with open(path) as f:
            return json.load(f)
    log("warning: no timeline file: using the built-in scene times and no sound cues")
    return {"comp": "main", "fps": 30, "duration": 180.0,
            "scenes": [dict(id=i, t0=a, t1=b, music=None) for i, a, b in DEFAULT_SCENES], "cues": []}


def write_wav(path: Path, x):
    x = np.asarray(x, dtype=np.float64)
    assert np.isfinite(x).all(), "NaN or inf in output"
    sf.write(str(path), x, SR, subtype="PCM_24")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--timeline", default=str(CODE / "build" / "main_timeline.json"))
    ap.add_argument("--out", default=str(CODE / "build" / "audio"))
    ap.add_argument("--refresh-timeline", action="store_true", help="run the node command first")
    ap.add_argument("--no-verify", action="store_true", help="skip the analysis step")
    ap.add_argument("--no-plots", action="store_true", help="skip the spectrogram pictures")
    args = ap.parse_args()

    log = Logger()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tl = load_timeline(Path(args.timeline), args.refresh_timeline, log)
    scenes = tl["scenes"]
    dur = float(tl.get("duration", 180.0))
    if abs(dur - mixer.FILM_S) > 1e-6:
        log(f"warning: the timeline says the film lasts {dur} s but this script builds {mixer.FILM_S} s")
    raw_cues = tl.get("cues", [])
    log(f"timeline: {len(scenes)} scenes, {len(raw_cues)} cues, duration {dur:g} s")

    log("composing the score")
    S = scorelib.build_score(scenes, log)
    log(f"  {len(S.chord_segs)} chords, {len(S.pluck)} plucks, {len(S.bell)} bells, {len(S.keys)} electric-piano notes, "
        f"{len(S.kick)} kicks, {len(S.hat)} hats, {len(S.rim)} rim clicks, {len(S.pad)} pad notes")

    log("rendering the music")
    music, minfo = mixer.mix_music(S, log)
    music, scene_report = mixer.level_scenes(music, scenes, log)

    log("rendering the sound effects")
    cues = mixer.parse_cues(raw_cues, log)
    sfx_stem, cue_records = mixer.render_sfx(cues, S, log)
    music, duck = mixer.apply_ducking(music, cues, log)

    log("mastering")
    main_mix, music_stem, sfx_stem_m, minfo2 = mastering.master(music, sfx_stem, log)

    write_wav(out / "main.wav", main_mix)
    write_wav(out / "music.wav", music_stem)
    write_wav(out / "sfx.wav", sfx_stem_m)
    log(f"wrote {out / 'main.wav'}, music.wav, sfx.wav")

    if not args.no_verify:
        import verify
        log("verifying")
        report = verify.run_all(out, S, tl, cue_records, cues, dict(layers=minfo, scenes=scene_report, duck=duck, master=minfo2),
                                log, plots=not args.no_plots)
        report["warnings"] = log.warnings
        report["log"] = log.lines
        with open(out / "report.json", "w") as f:
            json.dump(report, f, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
        log(f"report written to {out / 'report.json'}")
    log("done")


if __name__ == "__main__":
    main()
