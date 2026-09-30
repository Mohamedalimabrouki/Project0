"""
epmotion video: render frames in parallel worker processes and encode with ffmpeg.

Each worker renders a contiguous chunk of frames into a lossless FFV1 file.
The chunks are then joined and encoded once to H.264 (so quality is uniform).
"""

import os
import subprocess
import sys
import time
from multiprocessing import get_context

import numpy as np

from .core import W, H


def _encode_chunk(args):
    render_fn_path, start, end, out_path, fps = args
    module_path, fn_name = render_fn_path
    sys.path.insert(0, os.path.dirname(module_path))
    import importlib.util
    spec = importlib.util.spec_from_file_location("ep_render_module", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    render = getattr(mod, fn_name)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "ffv1", "-level", "3",
           "-g", "1", "-slices", "4", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for f in range(start, end):
        rgb = render(f)
        proc.stdin.write(np.ascontiguousarray(rgb).tobytes())
        if (f - start) % 60 == 0:
            el = time.time() - t0
            print(f"[{os.path.basename(out_path)}] frame {f} ({f - start + 1}/{end - start}) "
                  f"{el / (f - start + 1):.2f} s/frame", flush=True)
    proc.stdin.close()
    proc.wait()
    return out_path


def render_parallel(module_path, fn_name, n_frames, out_dir, fps=30, workers=4, start=0):
    os.makedirs(out_dir, exist_ok=True)
    frames = list(range(start, n_frames))
    per = int(np.ceil(len(frames) / workers))
    jobs = []
    for i in range(workers):
        a = start + i * per
        b = min(n_frames, a + per)
        if a >= b:
            continue
        jobs.append(((module_path, fn_name), a, b, os.path.join(out_dir, f"chunk_{a:05d}.mkv"), fps))
    ctx = get_context("spawn")
    with ctx.Pool(len(jobs)) as pool:
        outs = pool.map(_encode_chunk, jobs)
    return outs


def concat_and_encode(chunks, audio_path, out_path, fps=30, crf=16, subtitles=None, preset="slow",
                      tune="animation"):
    """Join FFV1 chunks, add audio (+ optional soft subtitle tracks) and encode H.264/AAC MP4."""
    list_path = out_path + ".concat.txt"
    with open(list_path, "w") as f:
        for c in chunks:
            f.write(f"file '{os.path.abspath(c)}'\n")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", list_path]
    if audio_path:
        cmd += ["-i", audio_path]
    subs = subtitles or []
    for s in subs:
        cmd += ["-i", s["path"]]
    cmd += ["-map", "0:v:0"]
    if audio_path:
        cmd += ["-map", "1:a:0"]
    for i, s in enumerate(subs):
        cmd += ["-map", f"{i + (2 if audio_path else 1)}:s:0"]
    cmd += ["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-tune", tune,
            "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-color_range", "tv", "-movflags", "+faststart", "-r", str(fps)]
    if audio_path:
        cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000"]
    if subs:
        cmd += ["-c:s", "mov_text"]
        for i, s in enumerate(subs):
            cmd += [f"-metadata:s:s:{i}", f"language={s['lang']}", f"-metadata:s:s:{i}", f"title={s['title']}"]
        cmd += ["-disposition:s:0", "0"]
    cmd += ["-shortest", out_path] if audio_path else [out_path]
    subprocess.run(cmd, check=True)
    os.remove(list_path)
    return out_path
