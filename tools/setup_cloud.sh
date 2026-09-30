#!/bin/bash
# Engineering Phenomena - install everything a fresh Linux session (Ubuntu 24.04, Python 3.11)
# needs to build a piece: Blender as a Python module, the 2D engine's libraries, TeX, the fonts,
# FluidSynth and its soundfont, the voice engine and the speech checker, and their models.
#
#   bash tools/setup_cloud.sh
#
# Safe to run again: it skips what is already there. Models go to $EP_MODELS (default ~/ep-models),
# the voice engine gets its own Python environment $EP_TTSENV (default ~/ep-ttsenv), because it
# needs numpy 2 while Blender 5.0.1 needs numpy 1.
set -e
REPO="$(cd "$(dirname "$0")/.." && pwd)"
EP_MODELS=${EP_MODELS:-$HOME/ep-models}
EP_TTSENV=${EP_TTSENV:-$HOME/ep-ttsenv}
SUDO=""; [ "$(id -u)" != 0 ] && SUDO=sudo

echo "1/4 system packages"
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq --no-install-recommends \
  ffmpeg git-lfs fonts-inter fonts-ibm-plex fonts-noto-core \
  texlive-latex-base texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra dvisvgm \
  fluidsynth musescore-general-soundfont \
  libegl1 libgl1 libegl-mesa0 libgl1-mesa-dri libxxf86vm1 libxfixes3 libxi6 libxkbcommon0 \
  libsm6 libxrender1 libxext6 libx11-6 libglu1-mesa > /dev/null

echo "2/4 Python packages (bpy 5.0.1 exists for Python 3.11 only)"
python3 --version
python3 -m pip install -q -r "$REPO/phenomena/01-resonance/scripts/requirements.txt"

echo "3/4 voice engine and speech checker, in their own environment"
[ -x "$EP_TTSENV/bin/python" ] || python3 -m venv "$EP_TTSENV"
"$EP_TTSENV/bin/pip" install -q kokoro-onnx==0.6.1 soundfile sherpa-onnx scipy

echo "4/4 models"
mkdir -p "$EP_MODELS"
cd "$EP_MODELS"
K=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s kokoro-v1.0.onnx ] || curl -sSLO "$K/kokoro-v1.0.onnx"
[ -s voices-v1.0.bin ] || curl -sSLO "$K/voices-v1.0.bin"
[ -d sherpa-onnx-whisper-base.en ] || curl -sSL \
  https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.en.tar.bz2 | tar xj

python3 -c "import bpy, skia, uharfbuzz; print('check: Blender', bpy.app.version_string, '| Skia ok')"
echo "done. Use:"
echo "  export KOKORO_DIR=$EP_MODELS WHISPER_DIR=$EP_MODELS/sherpa-onnx-whisper-base.en TTS_PYTHON=$EP_TTSENV/bin/python"
