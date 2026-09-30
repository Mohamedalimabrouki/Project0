# Handover - start here in a new session

Read this instead of re-reading the whole project. Updated 30 September 2026. Work lives on the branch `claude/sharp-hawking-c8ag4s`, which is not yet merged into `main`.

## Done: 02 · Aliasing
- **Finished, music only:** the full film (3:00) and the Short (0:45) in English, French and Arabic are in `phenomena/02-aliasing/video/` (stored with Git LFS). Also in the piece folder: subtitles, the hero still and the thumbnail.
- **Private screening room:** https://claude.ai/artifact/1xw1csgRjBgJTzGaF5U8VZ (the page source is in `phenomena/02-aliasing/code/web/`).
- **Made entirely with code:** see `phenomena/02-aliasing/code/README.md`. The output is deterministic: `./make_film.sh` rebuilds identical files.
- **Narration:** ready but not recorded. `phenomena/02-aliasing/voice/` holds the script (English, French, Arabic) and the recording guide. `python3 audio/voice.py build` turns Ali's recordings into the `_narrated` versions and renders the film without burned captions. **No AI voices** (see `CLAUDE.md`).

## Next (agreed with Ali)
1. **A photoreal wheel shot in Blender for the hook of 02** (the first 18.5 s).
   - Drive the motion from the same equations as `code/scenes/s01_hook.js`: tyre radius 0.33 m, 5 spokes, 30 frames per second, rolling without slipping (x = R θ).
   - Use a short shutter (very little motion blur), so the wheel aliases on screen exactly as it does in the code version.
   - Render a PNG sequence, then lay the code engine's overlays (speed panel, badge, captions) on top.
   - Keep the house palette and fonts.
2. **Narration**, when Ali records: `python3 audio/voice.py build` (about 5 minutes per language).

## Working on the Mac
- **Blender in the background, driven by Python:** `/Applications/Blender.app/Contents/MacOS/Blender -b scene.blend -P script.py`
- **Code film:** in `phenomena/02-aliasing/code/`, run `npm install && npx playwright install chromium` once. It also needs Python 3 with numpy, scipy, soundfile, pyloudnorm and pillow, and ffmpeg.
- **Keep token use low:** check single frames (`node render.mjs --scene s01_hook --at 5`) or contact sheets before any full render. Avoid reading large files whole.
