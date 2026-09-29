#!/usr/bin/env python3
"""Builds the soundtrack of "Engineering Phenomena 02 - Aliasing" from code.

    python3 audio/make_audio.py                 # the 3-minute film   (from phenomena/02-aliasing/code/)
    python3 audio/make_audio.py --comp short    # the 45 s vertical Short

Reads    build/<comp>_timeline.json    scene times and sound cues; made by
                                       `node render.mjs --comp <comp> --lang en --timeline`
Writes   build/audio/main.wav          the finished mix: 48 kHz, 24 bit, stereo, exactly 180.0 s,
                                       -14 LUFS, true peak below -1 dBTP
         build/audio/music.wav         the music alone (same level as in the mix)
         build/audio/sfx.wav           the sound effects alone (music.wav + sfx.wav = main.wav)
         build/audio/short.wav         (with --comp short) the Short: exactly 45.0 s, same targets,
         build/audio/short_music.wav   its stems,
         build/audio/short_sfx.wav
         build/audio/report.json       every measurement (report_short.json for the Short)
         build/audio/plots/*.png       spectrograms, for a quick look

Everything is synthesised (no samples, nothing downloaded) and every random number comes from a
fixed seed, so the result is identical each time. See audio/README.md for a plain-language tour.
"""
from __future__ import annotations

import os

# one thread for the numerical libraries: the results are then identical on every machine and every run
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import json
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

SR = dsp.SR

COMPS = {
    "main": dict(duration=180.0, files=("main.wav", "music.wav", "sfx.wav"), report="report.json",
                 scenes=[("s01_hook", 0.0, 18.5), ("s02_title", 18.0, 24.5), ("s03_snapshots", 24.0, 48.5),
                         ("s04_trick", 48.0, 86.5), ("s05_rule", 86.0, 126.5), ("s06_helicopter_lathe", 126.0, 148.5),
                         ("s07_sensors_strobe", 148.0, 170.5), ("s08_takeaway", 170.0, 180.0)]),
    "short": dict(duration=45.0, files=("short.wav", "short_music.wav", "short_sfx.wav"), report="report_short.json",
                  scenes=[("short_hook", 0.0, 16.5), ("short_trick", 16.0, 38.5), ("short_end", 38.0, 45.0)]),
}


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


def load_timeline(comp: str, path: Path, refresh: bool, log):
    if refresh or not path.exists():
        cmd = ["node", "render.mjs", "--comp", comp, "--lang", "en", "--timeline"]
        log("running: " + " ".join(cmd))
        try:
            r = subprocess.run(cmd, cwd=CODE, capture_output=True, text=True, timeout=600)
            log("  " + (r.stdout.strip().splitlines() or ["(no output)"])[0])
            if r.returncode != 0:
                log(f"warning: the timeline command failed ({r.returncode}): {r.stderr.strip()[:300]}")
        except Exception as e:                                  # node or Chromium missing
            log(f"warning: could not run the timeline command: {e}")
    if path.exists():
        with open(path) as f:
            return json.load(f)
    log("warning: no timeline file: using the built-in scene times and no sound cues")
    spec = COMPS[comp]
    return {"comp": comp, "fps": 30, "duration": spec["duration"],
            "scenes": [dict(id=i, t0=a, t1=b, music=None) for i, a, b in spec["scenes"]], "cues": []}


def write_wav(path: Path, x):
    x = np.asarray(x, dtype=np.float64)
    assert np.isfinite(x).all(), "NaN or inf in output"
    sf.write(str(path), x, SR, subtype="PCM_24")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comp", choices=sorted(COMPS), default="main", help="which composition to score (default: main)")
    ap.add_argument("--timeline", default=None, help="timeline json (default: build/<comp>_timeline.json)")
    ap.add_argument("--out", default=str(CODE / "build" / "audio"))
    ap.add_argument("--refresh-timeline", action="store_true", help="run the node command first")
    ap.add_argument("--no-verify", action="store_true", help="skip the analysis step")
    ap.add_argument("--no-plots", action="store_true", help="skip the spectrogram pictures")
    ap.add_argument("--verify-only", action="store_true",
                    help="do not re-render the music: measure the .wav files already in build/audio/")
    args = ap.parse_args()

    spec = COMPS[args.comp]
    log = Logger()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    tpath = Path(args.timeline) if args.timeline else CODE / "build" / f"{args.comp}_timeline.json"
    tl = load_timeline(args.comp, tpath, args.refresh_timeline, log)
    scenes = tl["scenes"]
    dur = float(tl.get("duration", spec["duration"]))
    if abs(dur - spec["duration"]) > 1e-6:
        log(f"warning: the timeline says the piece lasts {dur} s but the {args.comp} build makes {spec['duration']} s")
    mixer.configure(spec["duration"])
    raw_cues = tl.get("cues", [])
    log(f"composition '{args.comp}': {len(scenes)} scenes, {len(raw_cues)} cues, duration {spec['duration']:g} s")

    log("composing the score")
    S = scorelib.build_score(scenes, log, comp=args.comp)
    log(f"  {len(S.chord_segs)} chords, {len(S.pluck)} plucks, {len(S.bell)} bells, {len(S.keys)} electric-piano notes, "
        f"{len(S.kick)} kicks, {len(S.hat)} hats, {len(S.rim)} rim clicks, {len(S.pad)} pad notes")
    fmain, fmusic, fsfx = spec["files"]
    info_path = out / f"mix_info_{args.comp}.json"
    cues = mixer.parse_cues(raw_cues, log)

    if args.verify_only:
        log("verify-only: measuring the existing files (sound cues are re-made only to know where they belong)")
        _, cue_records = mixer.render_sfx(cues, S, log)
        with open(info_path) as f:
            saved = json.load(f)
        info = dict(layers=dict(layer_gain_db=saved["layers"]), scenes=saved["scenes"],
                    duck=saved["duck"], master=saved["master"])
    else:
        log("rendering the music")
        music, minfo = mixer.mix_music(S, log)
        music, scene_report = mixer.level_contour(music, mixer.CONTOUR[args.comp], log)

        log("rendering the sound effects")
        sfx_stem, cue_records = mixer.render_sfx(cues, S, log)
        music, duck = mixer.apply_ducking(music, cues, log)

        log("mastering")
        main_mix, music_stem, sfx_stem_m, minfo2 = mastering.master(music, sfx_stem, log)

        write_wav(out / fmain, main_mix)
        write_wav(out / fmusic, music_stem)
        write_wav(out / fsfx, sfx_stem_m)
        log(f"wrote {out / fmain}, {fmusic}, {fsfx}")
        duck_small = dict(max_db=duck["max_db"], seconds_over_1db=duck["seconds_over_1db"])
        with open(info_path, "w") as f:
            json.dump(dict(layers=minfo["layer_gain_db"], scenes=scene_report, duck=duck_small, master=minfo2), f, indent=1,
                      default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
        info = dict(layers=minfo, scenes=scene_report, duck=duck_small, master=minfo2)

    if not args.no_verify:
        import verify
        log("verifying")
        report = verify.run_all(out, S, tl, cue_records, cues, info, log, plots=not args.no_plots, comp=args.comp,
                                duration=spec["duration"], names=spec["files"])
        report["warnings"] = log.warnings
        report["log"] = log.lines
        with open(out / spec["report"], "w") as f:
            json.dump(report, f, indent=1, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))
        log(f"report written to {out / spec['report']}")
    log("done")


if __name__ == "__main__":
    main()
