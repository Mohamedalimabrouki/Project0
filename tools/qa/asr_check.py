"""
Listen to the narration like a viewer: transcribe each voice line of the final mix with Whisper
and compare it with the script. Catches mispronounced numbers and names, swallowed words, and
lines that the music or effects drown out.

  python tools/qa/asr_check.py phenomena/01-resonance/scripts phenomena/01-resonance/build/audio/mix.wav

The first argument is the piece's scripts folder (it must hold script.py with LINES and
timeline.py with line_times()). Prints the word error rate (WER) of every line and the mean.
Resonance scored 1.2 %. Anything above about 5 % on a line: listen to it.

Needs: pip install sherpa-onnx soundfile scipy numpy, and the Whisper model unpacked into
WHISPER_DIR (tools/setup_cloud.sh does both):
https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.en.tar.bz2
"""

import os
import re
import sys

import numpy as np
import scipy.signal as sg
import sherpa_onnx
import soundfile as sf

MODEL = os.environ.get("WHISPER_DIR", os.path.expanduser("~/ep-models/sherpa-onnx-whisper-base.en"))


def words(s):
    s = s.lower().replace("-", " ")
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


def wer(ref, hyp):
    r, h = words(ref), words(hyp)
    d = np.zeros((len(r) + 1, len(h) + 1), int)
    d[:, 0] = range(len(r) + 1)
    d[0, :] = range(len(h) + 1)
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (r[i - 1] != h[j - 1]))
    return d[-1, -1] / max(1, len(r))


def main():
    sys.path.insert(0, os.path.abspath(sys.argv[1]))
    import timeline as tl
    from script import LINES
    m = os.path.join(MODEL, "base.en-")
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=m + "encoder.onnx", decoder=m + "decoder.onnx",
                                                     tokens=m + "tokens.txt", num_threads=2)
    x, sr = sf.read(sys.argv[2], dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    x = sg.resample_poly(x, 16000, sr).astype("float32")
    times = tl.line_times()
    scores = []
    for item in LINES:
        a, b = times[item["id"]]
        seg = x[int(max(0.0, a - 0.1) * 16000): int((b + 0.2) * 16000)]
        st = rec.create_stream()
        st.accept_waveform(16000, seg)
        rec.decode_stream(st)
        hyp = st.result.text.strip()
        # compare with what the voice was asked to say ("say" spells numbers out)
        w = min(wer(item["en"], hyp), wer(item.get("say", item["en"]), hyp))
        scores.append(w)
        print(f"{item['id']} {w:5.1%} | {hyp}")
    print(f"mean WER {np.mean(scores):.1%}")


if __name__ == "__main__":
    main()
