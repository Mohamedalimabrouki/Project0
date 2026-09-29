#!/usr/bin/env bash
# Engineering Phenomena 02 - build every final file from the code, in one go.
#
#   ./make_film.sh            everything (3 languages, Short, stills, subtitles)
#   ./make_film.sh en         only the English full video
#   KEEP_FRAMES=1 ./make_film.sh en    keep the PNG frames afterwards (for checks)
#
# Needs: Node.js 18+, Python 3 with numpy scipy soundfile pyloudnorm pillow,
# ffmpeg, and the browser used by Playwright (npx playwright install chromium).
set -euo pipefail
cd "$(dirname "$0")"

LANGS=("${@:-en fr ar}")
LANGS=(${LANGS[@]})
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
    step "$COMP / $L: drawing every frame"
    node render.mjs --comp "$COMP" --lang "$L" --workers "$WORKERS"
    step "$COMP / $L: encoding"
    ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 \
      -i "build/${COMP}_${L}/frames/f%05d.png" -i "build/audio/${COMP}.wav" \
      -map 0:v -map 1:a \
      -vf "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p" \
      -c:v libx264 -preset slow -crf 16 -tune animation -profile:v high \
      -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv \
      -g 60 -c:a aac -b:a 320k -ar 48000 -shortest -movflags +faststart \
      "$VIDEO/${PIECE}_${SHAPE}_${L}.mp4"
    echo "video: $VIDEO/${PIECE}_${SHAPE}_${L}.mp4"
    if [ "$COMP" = main ] && [ "$L" = en ]; then
      step "accessibility: flash check"
      python3 qa/flash_check.py "build/${COMP}_${L}/frames"
    fi
    [ "${KEEP_FRAMES:-0}" = 1 ] || rm -rf "build/${COMP}_${L}/frames"
  done
done

step "stills"
node render.mjs --comp hero --at 0 --workers 1 --quiet
cp build/hero_en/frames/f00000.png "$RENDERS/${PIECE}_hero.png"
node render.mjs --comp thumb --at 0 --workers 1 --quiet
cp build/thumb_en/frames/f00000.png "$RENDERS/${PIECE}_thumb.png"

step "done"
ls -la "$VIDEO" "$SUBS" "$RENDERS"
