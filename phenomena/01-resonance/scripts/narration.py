"""
Generate the voice-over, one WAV file per script line, with Kokoro TTS.

Kokoro (Apache 2.0 licence) runs offline on the CPU. The model files are
not stored in this repository (too big). Download them once from
https://github.com/thewh1teagle/kokoro-onnx/releases (model-files-v1.0):
    kokoro-v1.0.onnx, voices-v1.0.bin
and point KOKORO_DIR at the folder that holds them.

Run:  KOKORO_DIR=/path/to/models python narration.py OUT_DIR
Needs: pip install kokoro-onnx==0.6.1 soundfile
"""

import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import LINES  # noqa: E402

VOICE = "af_heart"   # the highest rated Kokoro voice
SPEED = 0.94         # a little slower than default, explainer pace


def trim_silence(samples, sr, threshold=0.006, pad=0.04):
    """Cut leading and trailing silence, keep a short natural pad."""
    loud = np.where(np.abs(samples) > threshold)[0]
    if len(loud) == 0:
        return samples
    start = max(0, loud[0] - int(pad * sr))
    end = min(len(samples), loud[-1] + int(pad * sr))
    return samples[start:end]


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    model_dir = os.environ.get("KOKORO_DIR", ".")
    tts = Kokoro(os.path.join(model_dir, "kokoro-v1.0.onnx"),
                 os.path.join(model_dir, "voices-v1.0.bin"))
    only = set(sys.argv[2:])
    index = {}
    index_path = os.path.join(out_dir, "narration.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    for item in LINES:
        if only and item["id"] not in only:
            continue
        text = item.get("say", item["en"])
        samples, sr = tts.create(text, voice=VOICE, speed=SPEED, lang="en-us")
        samples = trim_silence(np.asarray(samples, dtype=np.float32), sr)
        path = os.path.join(out_dir, f"{item['id']}.wav")
        sf.write(path, samples, sr, subtype="PCM_24")
        index[item["id"]] = {"file": os.path.basename(path), "duration": len(samples) / sr, "sr": sr}
        print(f"{item['id']}  {len(samples) / sr:5.2f} s  {text}")
    with open(index_path, "w") as f:
        json.dump(index, f, indent=1)


if __name__ == "__main__":
    main()
