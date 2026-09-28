"""
Resonance - join the rendered picture, the soundtrack and the three subtitle
tracks into the final MP4 (H.264 + AAC, subtitles as selectable tracks).

  python make_final.py            -> video/01-resonance_16x9_en.mp4
"""

import glob
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline as tl  # noqa: E402

PIECE = os.path.abspath(os.path.join(HERE, ".."))
BUILD = tl.BUILD


def main():
    chunks = sorted(glob.glob(os.path.join(BUILD, "video_chunks", "chunk_*.mkv")))
    if not chunks:
        raise SystemExit("no picture chunks: run render_video.py video first")
    out = os.path.join(PIECE, "video", "01-resonance_16x9_en.mp4")
    lst = os.path.join(BUILD, "chunks.txt")
    with open(lst, "w") as f:
        for c in chunks:
            f.write(f"file '{c}'\n")
    subs = [("en", "English"), ("fr", "Français"), ("ar", "العربية")]
    # chapters (shown by most players, and listed for YouTube in video/01-resonance_youtube.txt)
    S = tl.scenes()
    chapters = [("Two swings", 0.0), ("Resonance", S["title"][0]), ("A natural rhythm", S["rhythm_swing"][0]),
                ("The engineer's model", S["spring_hero"][0]), ("Pushing at every rhythm", S["sweep"][0]),
                ("Damping", S["damping"][0]), ("The Millennium Bridge", S["bridge"][0] + 0.5),
                ("Taipei 101", S["taipei"][0] + 0.5), ("The takeaway", S["takeaway"][0] + 0.6)]
    meta = os.path.join(BUILD, "chapters.txt")
    total_ms = int(tl.total_duration() * 1000)
    with open(meta, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")
        for i, (name, t0) in enumerate(chapters):
            t1 = chapters[i + 1][1] if i + 1 < len(chapters) else tl.total_duration()
            f.write(f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={int(t0 * 1000)}\nEND={min(int(t1 * 1000), total_ms)}\n"
                    f"title={name}\n")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats",
           "-f", "concat", "-safe", "0", "-i", lst,
           "-i", os.path.join(BUILD, "audio", "mix.wav")]
    for code, _ in subs:
        cmd += ["-i", os.path.join(PIECE, "subtitles", f"01-resonance_{code}.srt")]
    cmd += ["-i", meta, "-map_metadata", str(2 + len(subs)), "-map_chapters", str(2 + len(subs))]
    cmd += ["-map", "0:v:0", "-map", "1:a:0"]
    for i in range(len(subs)):
        cmd += ["-map", f"{2 + i}:s:0"]
    cmd += ["-c:v", "libx264", "-preset", "slow", "-crf", "18", "-tune", "film",
            "-x264-params", "aq-mode=3:aq-strength=0.9:deblock=-1,-1",
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-r", "30", "-g", "60", "-bf", "3",
            "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
            "-c:s", "mov_text"]
    for i, (code, title) in enumerate(subs):
        lang3 = {"en": "eng", "fr": "fre", "ar": "ara"}[code]
        cmd += [f"-metadata:s:s:{i}", f"language={lang3}", f"-metadata:s:s:{i}", f"title={title}"]
    cmd += ["-disposition:s", "0", "-metadata:s:a:0", "language=eng",
            "-metadata", "title=Engineering Phenomena 01 - Resonance",
            "-metadata", "artist=Engineering Phenomena",
            "-metadata", "comment=Why tiny pushes make huge movements. Physics computed, not animated by eye.",
            "-movflags", "+faststart", "-shortest", out]
    subprocess.run(cmd, check=True)
    print("final:", out, f"{os.path.getsize(out) / 1e6:.1f} MB")
    # a ready-to-paste YouTube description with the chapters
    with open(os.path.join(PIECE, "video", "01-resonance_youtube.txt"), "w", encoding="utf-8") as f:
        f.write("Resonance: why tiny pushes make huge movements | Engineering Phenomena 01\n\n")
        f.write("Push something at its favourite rhythm, and tiny pushes make huge movements. Two swings, a steel "
                "mass on a spring, the London Millennium Bridge and the 660-tonne ball inside Taipei 101: every "
                "motion in this film is computed from the equations, not animated by eye.\n\n")
        for name, t0 in chapters:
            m, sec = divmod(int(t0), 60)
            f.write(f"{m}:{sec:02d} {name}\n")
        f.write("\nSubtitles: English, French, Arabic.\n"
                "Sources and the full engineering notes: phenomena/01-resonance/README.md in the project repository.\n"
                "Voice: Kokoro-82M (Apache 2.0). Music: original, played with the MuseScore General soundfont (MIT).\n")


if __name__ == "__main__":
    main()
