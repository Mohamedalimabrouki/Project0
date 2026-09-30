#!/bin/bash
# Resonance - rebuild the whole video, step by step.
# Usage:  KOKORO_DIR=/path/to/kokoro/models ./build.sh
# Heavy steps (3D renders) skip frames that already exist, so you can stop and resume.
set -e
cd "$(dirname "$0")"
B=../build
mkdir -p $B/audio/narration $B/data
PY=${PYTHON:-python3}
TTS_PY=${TTS_PYTHON:-$PY}

echo "1/8 voice-over";        [ -n "$KOKORO_DIR" ] && $TTS_PY narration.py $B/audio/narration || echo "   (KOKORO_DIR not set: keeping the existing voice files)"
echo "2/8 timeline";          $PY timeline.py | tail -1
echo "3/8 3D renders";        $PY blender_swings.py --shot hook --render --save-blend ../blender/01-resonance_swings_v001.blend
                              $PY blender_swings.py --shot rhythm --render --frames 400 --save-blend ../blender/01-resonance_swing_rhythm_v001.blend
                              $PY blender_spring.py --render --frames 250 --save-blend ../blender/01-resonance_spring_v001.blend
                              $PY blender_taipei.py --render --frames 250 --save-blend ../blender/01-resonance_taipei_damper_v001.blend
echo "4/8 picture";           $PY render_video.py video
echo "5/8 music";             $PY make_music.py $B/audio/music_raw.wav
echo "6/8 sound mix";         $PY make_audio.py
echo "7/8 subtitles";         $PY make_subtitles.py ../subtitles
echo "8/8 final MP4";         $PY make_final.py
