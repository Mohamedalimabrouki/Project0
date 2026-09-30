#!/usr/bin/env bash
# Engineering Phenomena 02 - build every final file from the code, in one go.
#
#   ./make_film.sh              everything: full film and Short in en, fr, ar, stills, subtitles
#   ./make_film.sh en           only the English versions
#   WORKERS=2 ./make_film.sh    fewer parallel browser pages (slower machine)
#
# Frames are streamed straight into the video encoder (no huge PNG folders);
# one frame per second is kept as a PNG in build/ for visual checks.
#
# Needs: Node.js 18+, Python 3 with numpy scipy soundfile pyloudnorm pillow,
# ffmpeg, and the browser used by Playwright (npx playwright install chromium).
set -euo pipefail
cd "$(dirname "$0")"

LANGS=(${@:-en fr ar})
WORKERS="${WORKERS:-4}"
PIECE=02-aliasing
VIDEO=../video
SUBS=../subtitles
RENDERS=../renders
mkdir -p build/audio "$VIDEO" "$SUBS" "$RENDERS"

step() { printf '\n=== %s ===\n' "$*"; }

for COMP in main short; do
  step "$COMP: timeline (captions and sound cues)"
  node render.mjs --comp "$COMP" --lang en --timeline

  step "$COMP: music and sound effects"
  python3 audio/make_audio.py --comp "$COMP"

  step "$COMP: subtitles"
  node tools/make_srt.mjs "$COMP"

  SHAPE=16x9; [ "$COMP" = short ] && SHAPE=9x16
  for L in "${LANGS[@]}"; do
    OUT="$VIDEO/${PIECE}_${SHAPE}_${L}.mp4"
    step "$COMP / $L: drawing and encoding every frame"
    node render.mjs --comp "$COMP" --lang "$L" --workers "$WORKERS" \
      --stream --encode --audio "build/audio/${COMP}.wav" --video "$OUT" --png-every 30
    step "$COMP / $L: photosensitivity check"
    python3 qa/flash_check.py "$OUT"
  done
done

step "stills"
node render.mjs --comp hero --at 0 --workers 1 --quiet
cp build/hero_en/frames/f00000.png "$RENDERS/${PIECE}_hero.png"
node render.mjs --comp thumb --at 0 --workers 1 --quiet
cp build/thumb_en/frames/f00000.png "$RENDERS/${PIECE}_thumb.png"

step "done"
ls -la "$VIDEO" "$SUBS" "$RENDERS"
