#!/usr/bin/env bash
# Engineering Phenomena 02 - the screening-room web page (published as a private claude.ai artifact).
#
#   ./web/make_page.sh          after ./make_film.sh: packages the six finals for streaming
#
# Output in build/web/:  index.html (web/page.html with the subtitles filled in) and, for each
# language, hls/<lang>/ (the film) and hls/short_<lang>/ (the Short): 4-second video pieces,
# their list (playlist.txt) and a poster picture. The page plays them with hls.js.
#
# Publishing: build/web/index.html with every file under build/web/hls/, at most 64 MB per
# upload, so one language (film + Short, about 44 MB) per publish, all to the same page.
# The list of pieces is called playlist.txt because the artifact host serves ordinary web
# file types only; hls.js reads it the same.
set -euo pipefail
cd "$(dirname "$0")/.."
PIECE=02-aliasing
VIDEO="$(cd ../video && pwd)"
OUT=build/web
rm -rf "$OUT"; mkdir -p "$OUT/hls"

for L in en fr ar; do
  for K in film short; do
    if [ "$K" = film ]; then
      SRC="$VIDEO/${PIECE}_16x9_$L.mp4"; D="$OUT/hls/$L"; FRAME="build/main_$L/frames/f00630.png"; AT=21
    else
      SRC="$VIDEO/${PIECE}_9x16_$L.mp4"; D="$OUT/hls/short_$L"; FRAME="build/short_$L/frames/f00990.png"; AT=33
    fi
    mkdir -p "$D"
    (cd "$D" && ffmpeg -v error -y -i "$SRC" -c copy -f hls -hls_time 4 -hls_playlist_type vod \
       -hls_segment_type fmp4 -hls_fmp4_init_filename init.mp4 -hls_segment_filename 'seg_%03d.mp4' playlist.m3u8 \
       && mv playlist.m3u8 playlist.txt)
    # poster: the title card (film) and the "closest match is backwards" moment (Short);
    # the frame kept by the build if there is one, otherwise the same moment from the video
    [ -f "$FRAME" ] || { FRAME="$D/poster.png"; ffmpeg -v error -y -ss "$AT" -i "$SRC" -frames:v 1 "$FRAME"; }
    python3 -c "import sys; from PIL import Image; Image.open(sys.argv[1]).convert('RGB').save(sys.argv[2], quality=88, optimize=True, progressive=True)" "$FRAME" "$D/poster.jpg"
    rm -f "$D/poster.png"
  done
done

# the subtitles of the six files, read from the .srt files, go inside the page
python3 - "$OUT" <<'PY'
import json, re, sys
out = sys.argv[1]
def parse(p):
    cues = []
    for b in re.split(r'\n\s*\n', open(p, encoding='utf-8').read().strip()):
        lines = b.strip().split('\n')
        g = list(map(int, re.match(r'(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)', lines[1]).groups()))
        t0 = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
        t1 = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        cues.append([round(t0, 3), round(t1, 3), '\n'.join(lines[2:])])
    return cues
cues = {'film': {L: parse(f'../subtitles/02-aliasing_{L}.srt') for L in ('en', 'fr', 'ar')},
        'short': {L: parse(f'../subtitles/02-aliasing_9x16_{L}.srt') for L in ('en', 'fr', 'ar')}}
data = json.dumps(cues, ensure_ascii=False, separators=(',', ':'))
assert '</' not in data
html = open('web/page.html', encoding='utf-8').read().replace('__CUES__', data)
assert '__CUES__' not in html and '\u2014' not in html
open(f'{out}/index.html', 'w', encoding='utf-8').write(html)
print(f'{out}/index.html', len(html.encode()), 'bytes')
PY
du -sh "$OUT"/hls/*
