# Engineering Phenomena: production playbook

How piece 01, **Resonance** (2 min 58 s, 1080p, subtitles in English, French and Arabic), was made from nothing to a finished film. The goal is that any Claude session, in the cloud or on Ali's own computer, can make the next piece at the same quality or better.

**For Claude:** read this whole file before you start, then `CLAUDE.md`, `docs/STYLE_GUIDE.md`, `docs/WORKFLOW.md` and `phenomena/01-resonance/README.md`. Piece 01 is your reference implementation: copy its structure, not just its look. Ali is a mechatronics engineer, not a software developer. Explain every step to him in plain words and define any jargon.

**For Ali:** sections 1 and 2 explain what makes the work good. Section 3 explains how to set up your computer. The rest is the detailed recipe that Claude follows.

---

## Contents

1. [The quality bar](#1-the-quality-bar)
2. [The secrets (astuces)](#2-the-secrets-astuces)
3. [Setting up a computer](#3-setting-up-a-computer)
4. [Map of the project](#4-map-of-the-project)
5. [The pipeline, step by step](#5-the-pipeline-step-by-step)
6. [Blender recipes](#6-blender-recipes)
7. [2D motion graphics recipes](#7-2d-motion-graphics-recipes)
8. [Voice](#8-voice)
9. [Music](#9-music)
10. [Sound effects and the mix](#10-sound-effects-and-the-mix)
11. [Subtitles](#11-subtitles)
12. [The final encode](#12-the-final-encode)
13. [Quality checks before calling it done](#13-quality-checks-before-calling-it-done)
14. [Delivery](#14-delivery)
15. [Pitfalls already solved](#15-pitfalls-already-solved)
16. [Time and computer budget](#16-time-and-computer-budget)
17. [How Claude should run the job](#17-how-claude-should-run-the-job)
18. [How to do even better next time](#18-how-to-do-even-better-next-time)
19. [Prompt to start a new piece](#19-prompt-to-start-a-new-piece)

---

## 1. The quality bar

What "finished" meant for Resonance. Match or beat every line.

| Area | Resonance |
|---|---|
| Length | 2 min 58 s (5335 frames), 9 chapters |
| Picture | 1920 × 1080, 30 fps, H.264 High 4.2, CRF 18, BT.709 tags |
| 3D | Blender 5.0.1 Cycles, 4 scenes, 1540 rendered frames, plus a 3840 × 2160 hero still |
| 2D | Custom Skia engine (`tools/epmotion/`): real typography, real LaTeX equations, graphs that draw themselves |
| Physics | Every motion computed from the equations in `physics.py`, one keyframe per frame, nothing animated by eye |
| Facts | 17 published sources, popular myths avoided on purpose, every exaggeration labelled on screen |
| Voice | Kokoro-82M, voice `af_heart`, speed 0.94; speech-recognition check of the final mix: 1.2 % word error rate |
| Music | Original score in D major, written as code, played with FluidSynth and the MuseScore General soundfont |
| Sound | All effects synthesised and driven by the physics; mix at -14 LUFS, peaks at -1 dBFS |
| Subtitles | English, French, Arabic, as selectable tracks inside the MP4 and as `.srt` files |
| Extras | Thumbnail, ready-to-paste YouTube description with chapters, a web watch page, a phone copy under 30 MB |

---

## 2. The secrets (astuces)

These rules made the difference. They matter more than any single tool.

### 2.1 Physics first, pictures second
- One file, `physics.py`, holds every equation and every number: the swing is a real nonlinear pendulum, `θ'' = -(g/L)·sin θ - 2ζωn·θ' + a_push(t)`, solved numerically; the spring is the exact damped free vibration; the Taipei 101 damper is a two-mass model tuned with Den Hartog's rules.
- Blender reads its motion from it (one keyframe per frame, interpolation set to LINEAR so Blender adds no easing of its own). The 2D graphs read the same functions. Even the music and the sound effects are timed from them: a celesta note on every push, a marimba note on every oscillation of the spring, strings that swell with the tower's 6.8 s sway.
- Result: the film cannot contradict itself, and an engineer can check any frame against the equation.

### 2.2 Real, buildable numbers
- Choose values an engineer could build: a 2 kg steel cube (63.4 mm side at 7850 kg/m³), a 79 N/m spring (1.5 mm wire, 30 mm coils, about 23 turns), exactly 1 Hz, 5 % damping, a 0.5 N push. Then every number on screen is to scale ("±63 mm at resonance = 10 × the 6.3 mm static stretch").
- Real systems use their published figures (Taipei 101: 660 t sphere, 5.5 m, 41 plates of 125 mm, 8 cables, 8 hydraulic dampers, about 0.15 Hz).

### 2.3 Fact-check before writing a single line
- Collect sources first (papers, operator pages, textbooks), write them into the piece README with numbers.
- Hunt the myths. Resonance avoided two: "the Millennium Bridge swayed because people marched in step" (research shows the balance behaviour alone is enough; falling into step is a result, not the cause) and "Tacoma Narrows was simple resonance" (it was aeroelastic flutter, so it is not in the film).
- Say only what the sources support: "up to about 40 % less sway (operator's figure)", not "40 % less".
- When a picture must exaggerate, say so on screen: "sway exaggerated × 100 · diagram not to scale".

### 2.4 The voice sets the clock
- Write the script first (`script.py`), generate the voice, measure each line's real length, and derive every scene's start and end from those lengths (`timeline.py`).
- A few lines have ANCHORS (earliest start times) so a visual beat has room.
- `timeline.phrase_time(line, "phrase")` finds when a given word is spoken (from the pauses in the recording), so a graph can land exactly on "ten times bigger".
- Change a sentence, regenerate that one line, and the whole film re-times itself.

### 2.5 Colour means something, everywhere
- The Okabe-Ito palette (safe for colour-blind viewers) in `assets/palette/palette.json`: vermillion = force, blue = motion, orange = energy and heat, sky blue = fluid, bluish green = "it works", yellow = "look here".
- The same meanings apply in Blender materials, in 2D arrows, in the LaTeX equations (`\cf{}` colours a force term, `\cm{}` a motion term) and on the web page.
- Never pick a colour for looks alone.

### 2.6 3D for wonder, 2D for understanding
- 3D (Blender) shows the real object beautifully: the swings, the spring, the golden damper ball.
- 2D (the epmotion engine) explains it: graphs, equations, arrows, diagrams.
- The two are joined, not just cut together. Blender exports where named points of the 3D scene land on screen, frame by frame (`export_projection` → `*_points.json`), so 2D labels and arrows stay pinned to moving 3D objects.

### 2.7 Two layers in every scene
- A plain sentence for a child ("every push goes the same way the mass is already moving") and the engineering behind it (the phase lag is 90°, so the power *P = F·v* is never negative).

### 2.8 Everything is code
- Every Blender scene is built from an empty file by a Python script (`blender_*.py`). The `.blend` files are saved as a by-product, so nothing is lost if a file breaks, and a change (a new camera move, a different number) is one edit and one re-render.
- The same is true for the music, the effects, the subtitles, the graphics and the final encode. `build.sh` rebuilds the whole film.

### 2.9 Look and listen at every step
- Render single preview frames and contact sheets (16 moments on one image) and actually look at them.
- Transcribe the final mix with speech recognition and compare it with the script.
- Measure loudness, count frames, check the length of every track.
- Many problems were found this way: labels colliding, a readout overlapping a curve, the Taipei ball drawn outside the tower, a ghost highlight from the previous scene, abrupt cuts, and a final file missing its last 6 seconds (see section 15).

### 2.10 Quiet craft that adds up
- A fixed noise pattern in Cycles (same seed every frame) so the image does not flicker.
- Soft fades (0.5 to 0.6 s) between scenes, 15 ms fades on every sound clip so nothing clicks.
- Film grain (0.6) and a light vignette (0.22) over everything, so 3D and 2D feel like one film.
- An infinity cove (floor curving up into the back wall) so there is never a horizon line, and a grid floor whose lines keep the same width on screen at any distance.
- Signs, not only colours, for colour-blind viewers: energy added is a filled chip "+", energy removed a hollow chip "-".

### 2.11 Honest status
- The README status and checklist are updated as the piece moves, and never say "done" before the final file has been checked end to end.

---

## 3. Setting up a computer

### 3.1 Get the project
```bash
git clone https://github.com/Mohamedalimabrouki/Project0.git
cd Project0
git checkout claude/focused-goldberg-r03qpj   # or main, once pull request #1 is merged
```
Then put the big files that are not in Git yet in place (Ali has them from the chat):
- `phenomena/01-resonance/video/01-resonance_16x9_en.mp4`
- the four `.blend` files in `phenomena/01-resonance/blender/`

Commit them with GitHub Desktop or `git lfs install` then `git add` and `git push`: `.gitattributes` already sends `.mp4`, `.blend`, `.wav` and similar big files through Git LFS (Large File Storage, GitHub's store for big files).

### 3.2 What the pipeline needs

| Tool | Version used | Used for |
|---|---|---|
| Python | 3.11 exactly | `bpy` 5.0.1 (Blender as a Python module) only exists for 3.11 |
| Python packages | see `phenomena/01-resonance/scripts/requirements.txt` | bpy 5.0.1, skia-python 144, uharfbuzz, svgelements, numpy 1.26 (below 2), scipy, pillow, soundfile, mido, pyloudnorm |
| Voice environment | separate venv | kokoro-onnx 0.6.1 (needs numpy 2, so it lives apart), sherpa-onnx (speech check) |
| Models | | `kokoro-v1.0.onnx`, `voices-v1.0.bin`, `sherpa-onnx-whisper-base.en` |
| ffmpeg | 6.1 | every encode |
| TeX Live + dvisvgm | | real LaTeX equations as vector outlines |
| Fonts | | Inter and Inter Display (Latin), IBM Plex Sans Arabic |
| FluidSynth + MuseScore General soundfont (`.sf3`) | | playing the score |
| Blender program | 5.0 | optional locally: opening the `.blend` files, and rendering on the graphics card |

Model downloads:
- Voice: `https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx` and `.../voices-v1.0.bin`
- Speech check: `https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-base.en.tar.bz2` (unpack it)

### 3.3 Linux, a cloud session, or Windows with WSL
One command installs everything (tested on Ubuntu 24.04 with Python 3.11). Ubuntu's own `python3` is 3.12: if `python3 --version` does not say 3.11, install 3.11 first (for example with `pyenv` or the deadsnakes PPA) and make it the `python3` the script uses.
```bash
bash tools/setup_cloud.sh
export KOKORO_DIR=~/ep-models WHISPER_DIR=~/ep-models/sherpa-onnx-whisper-base.en TTS_PYTHON=~/ep-ttsenv/bin/python
```
**On Windows, this is the easiest route:** install WSL (Windows Subsystem for Linux, a real Ubuntu inside Windows: `wsl --install` in PowerShell), clone the project inside it, run the script above, and use the normal Windows Blender program for graphics-card renders (section 3.5). Windows drives appear in WSL as `/mnt/c/...`.

### 3.4 macOS (native)
- Python 3.11 (from python.org or `pyenv`), then `python3.11 -m pip install -r phenomena/01-resonance/scripts/requirements.txt`
- `brew install ffmpeg fluid-synth`, and MacTeX or BasicTeX (both include `latex` and `dvisvgm`)
- Fonts: download Inter (github.com/rsms/inter, the `otf` folder has `Inter-*.otf` and `InterDisplay-*.otf`) and IBM Plex Sans Arabic (github.com/IBM/plex or Google Fonts); tell the engine where they are:
  `export EP_FONT_DIR=/path/to/inter/otf EP_ARABIC_FONT_DIR=/path/to/plex-arabic`
- Soundfont: download `MuseScore_General.sf3` (linked from the MuseScore handbook's soundfont page) and `export EP_SOUNDFONT=/path/to/MuseScore_General.sf3`
- Voice environment: `python3 -m venv ~/ep-ttsenv && ~/ep-ttsenv/bin/pip install kokoro-onnx==0.6.1 soundfile sherpa-onnx scipy`, then download the models (3.2)

### 3.5 Rendering with the Blender program and the graphics card
The scene scripts work both ways:
```bash
# Blender as a Python module (what the cloud used, CPU only)
python3 blender_spring.py --render --frames 250

# the Blender program, headless, on the graphics card
EP_DEVICE=OPTIX blender -b -P blender_spring.py -- --render --frames 250 --samples 64
```
- `EP_DEVICE` accepts `OPTIX` or `CUDA` (NVIDIA), `HIP` (AMD), `METAL` (Mac), `ONEAPI` (Intel). If that card is not found the script says so and renders on the CPU.
- Blender's own Python has numpy but not scipy. The swing solver needs scipy, so compute the swing data once with normal Python first (it is cached in `build/data/`):
  `cd phenomena/01-resonance/scripts && python3 -c "import physics as P; P.swing_data('../build/data'); P.pull_data('../build/data')"`
- Blender program paths: Windows `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe`, macOS `/Applications/Blender.app/Contents/MacOS/Blender`.
- To look at a scene in the Blender window instead: open the saved `.blend`, or open the script in the Scripting tab and press Run.

---

## 4. Map of the project

```
CLAUDE.md                     house rules for Claude
docs/STYLE_GUIDE.md           palette, fonts, formats, Blender settings, accuracy rules
docs/WORKFLOW.md              the ten steps from idea to published piece
docs/BACKLOG.md               the next subjects
docs/PRODUCTION_PLAYBOOK.md   this file
assets/palette/palette.json   the palette (single source of truth)
assets/brand/                 logo mark and banner
tools/epmotion/               the 2D motion graphics engine (Skia)
tools/blender_palette.py      house materials for hand-made Blender scenes
tools/qa/contact_sheet.py     16 moments of the film on one image
tools/qa/asr_check.py         transcribes the voice in the mix and compares it with the script
tools/setup_cloud.sh          installs everything on Linux
phenomena/_template/          copy this to start a new piece
phenomena/01-resonance/
  README.md                   explanation (both layers), sources, storyboard, status checklist
  scripts/                    everything that builds the film (below)
  blender/                    the saved .blend files (Git LFS)
  renders/                    hero still and thumbnail
  video/                      final MP4 (Git LFS) and the YouTube description
  subtitles/                  .srt files, EN / FR / AR
  web/index.html              the watch page (see 14.3)
  build/                      renders, audio and intermediate files, never committed
```

Scripts of a piece, in the order they run:

| Script | Job |
|---|---|
| `script.py` | The words: every narration line with `id`, `scene`, `en`, `say` (numbers spelled out for the voice), `fr`, `ar`, `gap` |
| `narration.py` | One WAV per line with Kokoro |
| `timeline.py` | Line times from the WAV lengths, scene boundaries, `phrase_time()` |
| `physics.py` | Every motion and number |
| `blender_common.py` | Render settings, world, materials, grid-floor shader, lights, camera, cove, `export_projection`, `render_frames` |
| `blender_swings.py`, `blender_spring.py`, `blender_taipei.py` | The 3D scenes (build, keyframe from physics, render, save the .blend) |
| `sc_common.py` | Shared 2D context: timing, physics data, loading 3D frames and their projected points |
| `sc_opening.py`, `sc_model.py`, `sc_bridge.py`, `sc_taipei.py` | The 2D scenes: each has `draw_*(canvas, t)` |
| `render_video.py` | The master compositor: the SCENES table, fades, logo, vignette, grain; renders preview frames or the whole film in parallel |
| `make_music.py` | The score as note events, rendered with FluidSynth |
| `make_audio.py` | Voice + music + synthesised effects, ducking, loudness |
| `make_subtitles.py` | EN / FR / AR `.srt`, timed to the voice |
| `make_final.py` | Joins the picture, adds sound, subtitles, chapters; writes the MP4 and the YouTube text |
| `make_thumbnail.py` | 1280 × 720 thumbnail from the 4K hero still |
| `build.sh` | Runs all of it in order |

---

## 5. The pipeline, step by step

Run everything from `phenomena/NN-name/scripts/`. After each step, check the result before moving on.

| # | Step | Command | Check |
|---|---|---|---|
| 1 | Research and facts | write the piece README: both layers, numbers, sources, myths to avoid | every number has a source |
| 2 | Script | edit `script.py` | read it aloud; about 150 words per minute; British spelling; no em dash |
| 3 | Voice | `$TTS_PYTHON narration.py ../build/audio/narration` (add line ids to redo only those) | listen; numbers must be spelled out in `say` |
| 4 | Timeline | `python3 timeline.py` | prints every line and scene with its length |
| 5 | Physics | `python3 -c "import physics"` plus quick plots of what matters | numbers match the README |
| 6 | 3D scenes | `python3 blender_*.py --render ...` (see 6.4) | render one frame first (`--start N --end N`) and look at it |
| 7 | 2D and compositing | `python3 render_video.py frames 1500 2400 3100` | look at each PNG in `build/preview/` |
| 8 | Contact sheets | `python3 ../../../tools/qa/contact_sheet.py render_video.py 0 180 1.0 ../build/sheets` | look at every sheet |
| 9 | Picture | `EP_WORKERS=4 python3 render_video.py video` (or `video START END` for a part) | lossless chunks in `build/video_chunks/` |
| 10 | Music | `python3 make_music.py ../build/audio/music_raw.wav` | listen through |
| 11 | Mix | `python3 make_audio.py` | prints LUFS and peak; listen to the stems |
| 12 | Subtitles | `python3 make_subtitles.py ../subtitles` | read them; Arabic by a native speaker |
| 13 | Final | `python3 make_final.py` | section 13 |
| 14 | Thumbnail | `python3 make_thumbnail.py` (needs the hero still, 6.5) | look at it small, as on YouTube |
| 15 | Status | tick the piece checklist, update the main README table, commit, push | |

---

## 6. Blender recipes

### 6.1 Render settings (`blender_common.render_settings`)
- Cycles, 1920 × 1080, 30 fps, **8 to 10 samples** with adaptive sampling (threshold 0.02) and the OpenImageDenoise denoiser (prefilter FAST, albedo and normal passes). Low samples plus a good denoiser gave clean frames in 7 to 11 s each on 4 CPU cores. With a graphics card, raise to 32 to 64 samples and use prefilter ACCURATE.
- **Fixed seed (7), not animated**: the noise pattern stays still, so nothing flickers.
- Bounces kept low (4 total, 2 diffuse, 2 glossy), caustics off, glossy blur 1.0: faster and cleaner.
- Motion blur on, shutter 0.5 (a real camera's 180° shutter).
- Colour: **AgX** view transform, look None. Output 8-bit PNG.
- Persistent data on (the scene stays in memory between frames).

### 6.2 The look
- **World**: house ink `#12161C`, so 3D and 2D share one background.
- **Infinity cove** (`cove()`): a floor that curves up into a back wall. No horizon line, like a photo studio.
- **Grid floor shader** (`grid_floor_material()`): steel lines on ink, whose width grows with distance so they stay about 1.2 pixels wide on screen, lines across the view widened by 1/|incoming.z| against foreshortening, faded out between 6 and 26 m to stop shimmering, and drawn only on the flat floor.
- **Materials**: `principled()` with real metal values (metallic 1, low roughness for polished steel); palette colours converted from sRGB to linear (`hex_linear`) so they match the 2D exactly.
- **Light**: large soft area lights (key and rim) plus a faint blue "backdrop glow" on the wall behind; spot lights for drama on the hero objects.
- **Camera**: real lens values (focal length, 36 mm sensor), depth of field with a real f-stop, and slow camera moves keyframed per frame (location, rotation and focus distance), eased by code.
- **Bevel** every hard edge (`bevel()`): real objects catch light on their edges.
- **The spring** is built with Geometry Nodes (spiral curve, circle profile, curve to mesh): when the block moves, the coils spread evenly like a real spring, instead of the whole spring being stretched.

### 6.3 Motion from physics
- `reset_scene()` sets new keyframes to LINEAR, then each script samples the physics at every frame and inserts one keyframe per frame.
- Swings: the hook has two swings. The left one is pushed once per swing, each time the seat leaves the back of its arc. The right one gets the same pushes at random moments, and the swing shown is the **median of 1000 random trials** (a typical case, not a cherry-picked one).
- Spring: pulled 55 mm and released; the exact damped free vibration.
- Taipei damper: tuned period 6.8 s (effective pendulum length about 11.5 m), a gentle 0.15 m swing (a strong wind, not a storm), with the cables and dampers re-aimed every frame so they stay attached.

### 6.4 Rendering the scenes
```bash
python3 blender_swings.py --shot hook --render --save-blend ../blender/01-resonance_swings_v001.blend
python3 blender_swings.py --shot rhythm --render --frames 400 --save-blend ../blender/01-resonance_swing_rhythm_v001.blend
python3 blender_spring.py --render --frames 250 --save-blend ../blender/01-resonance_spring_v001.blend
python3 blender_taipei.py --render --frames 250 --save-blend ../blender/01-resonance_taipei_damper_v001.blend
```
- Frames go to `build/frames/<shot>/<shot>_NNNN.png`, with `<shot>_points.json` (projected points for the 2D labels).
- **Frames that already exist are skipped**, so a stopped render resumes where it left off.
- Options: `--start`, `--end`, `--step` (for example `--step 10` for a quick look at the whole shot), `--samples`.

### 6.5 The hero still (4K)
```bash
python3 blender_spring.py --start 18 --samples 48 --width 3840 --height 2160 --still ../renders/01-resonance_hero.png
```
About 8 minutes on 4 CPU cores. Then `make_thumbnail.py` builds the thumbnail from it: the render pushed right, an ink gradient on the left, the title, "Tiny pushes. / Huge movements." (the second line in yellow), and the resonance curve with its "× 10" peak.

---

## 7. 2D motion graphics recipes

### 7.1 The engine (`tools/epmotion/`, see its README)
- Skia (Chrome's drawing library) draws into numpy arrays at 1920 × 1080.
- `text.py`: HarfBuzz shaping (real kerning and ligatures) with Inter and Inter Display, per-letter animation, small-caps labels with letter spacing.
- `tex.py`: real LaTeX (TeX Live → dvisvgm → vector paths), with colour macros by meaning (`\cf{}` force, `\cm{}` motion), and a write-on animation.
- `shapes.py`: the house vocabulary. Force arrows are thick with a filled head (vermillion); motion arrows are thin with an open head (blue). Coil and zigzag springs, dampers, steel blocks, walls, ground hatching, dimension lines.
- `graph.py`: axes, ticks and curves that draw themselves.
- `fx.py`: background, vignette, film grain, logo mark, colour bar.
- `video.py`: parallel rendering into lossless FFV1 chunks, then one H.264 encode.

### 7.2 How a 2D scene is written
- Each scene is a function `draw_x(canvas, t)` that draws the whole frame for a global time `t`. No hidden state, so any frame can be rendered alone, in any order, by any worker.
- Times come from the timeline: `at("L12")` is when line L12 starts, `at("L12", "ten times")` when those words are spoken.
- Animation helpers: `ramp(t, t0, t1)` gives 0 to 1, then `smooth`, `ease_out`, `ease_in_out`, `ease_out_back`.
- 3D frames are loaded as images and 2D is drawn on top; labels use the projected points so they follow the objects.
- Labels are short, in small caps for headings, with units upright and a space ("660 t", "0.15 Hz"), variables in italic.

### 7.3 The compositor (`render_video.py`)
- The `SCENES` table lists every scene with its start, end, draw function and fade-in length (0.5 to 0.6 s). Scenes overlap slightly, so one fades in over the end of the other.
- On top of everything: the series mark bottom right (55 % opacity, hidden during the title card), a vignette (0.22) and grain (0.6).
- `python3 render_video.py frames N N N` renders PNG previews (about 0.2 to 0.5 s each).
- `python3 render_video.py video [START END]` renders the film in parallel (`EP_WORKERS`, default 4) into chunks named after their first frame (`chunk_01356.mkv`). Rendering a part again only replaces its own chunks.

---

## 8. Voice

- **Kokoro-82M** (Apache 2.0 licence, runs offline on the CPU), voice `af_heart` (the best rated), speed **0.94** (a calm explainer pace), American English.
- The `say` field spells out what the voice must read: "two point eight seconds", "five hundred and eight metre", "Taipei one oh one". The subtitles keep the digits from `en`.
- Silence is trimmed at both ends of each line (threshold 0.006, 40 ms kept), then the timeline adds the `gap` after each line.
- One WAV per line (24-bit), so one line can be re-recorded without touching the others: `$TTS_PYTHON narration.py OUT_DIR L12 L16`.
- Check the voice with `tools/qa/asr_check.py` (section 13).

---

## 9. Music

- Written as note events in seconds (`note()`, `chord()`, `expr()` for swells), turned into a MIDI file with `mido`, played with FluidSynth and the MuseScore General soundfont.
- Key of D major; General MIDI instruments: piano, strings, cello, celesta, pad, choir, vibraphone, marimba, timpani, bass.
- **The music follows the physics**: a celesta ping on every push of the in-rhythm swing, a vibraphone note on every back-and-forth of the free swing, a marimba note per oscillation of the spring (as loud as the motion, so it dies away with it), three pitches and tempos for the three rigs (1 Hz, 2 Hz, 0.5 Hz), strings that swell with the tower's 6.8 s sway and a choir a quarter beat later.
- Big harmonic moves on the story beats (the title, "ten times bigger", the bridge closing, "Resonance, used to fight resonance").
- Gotcha: when the same pitch is played twice on one channel, the first note's "note off" can cut the second one. Track notes per (channel, pitch) and only send "note off" for the right one.

---

## 10. Sound effects and the mix

- **Every effect is synthesised** in `make_audio.py`, no sample libraries: thumps for pushes, ticks, whooshes on transitions (filtered noise with a shaped envelope), a low boom, footsteps, a river bed, wind with gusts, a small convolution reverb.
- **Effects driven by physics**: the pushes land on the physics push times, the mass "hums" as loudly as it moves, the walkers' steps, the tower's 6.8 s sway in the wind.
- Levels: voice at about -17 LUFS; music ducked by about 7 dB while the voice speaks (voice activity from the narration, smoothed); effects under both.
- Master: loudness normalised to **-14 LUFS** (YouTube's target) with pyloudnorm, peaks limited at **-1 dBFS**, a 1.2 s fade at the very end.
- A **15 ms fade** on both ends of every placed clip: no clicks.
- Stems are written too (`stem_voice.wav`, `stem_music.wav`, `stem_effects.wav`) for checking and for other language versions.

---

## 11. Subtitles

- Built from `script.py` and the real line times, so they always match the voice.
- Each line is cut at sentence ends, then into pieces of at most 2 lines of 42 (EN), 44 (FR) or 40 (AR) characters, with balanced line lengths; each piece gets a share of the line's time in proportion to its length.
- Each cue stays at least 1.2 s when there is room and never overlaps the next.
- French: French punctuation spacing ("toutes les 2,8 secondes", a space before ":").
- Arabic: right to left, but numbers and units stay left to right; numbers stay attached to their % sign. **A native speaker must check the Arabic before publishing.**
- Inside the MP4 they are three selectable tracks (mov_text, languages `eng`, `fre`, `ara`), off by default; the `.srt` files are for YouTube.

---

## 12. The final encode

`make_final.py`:
- Checks that the chunks cover every frame exactly once (each chunk is named after its first frame) and that each lasts as long as it should, then joins them with exact durations.
- Video: libx264 preset slow, **CRF 18**, tune film, `aq-mode=3:aq-strength=0.9:deblock=-1,-1` (keeps the dark gradients and fine grid lines clean), yuv420p, High profile level 4.2, BT.709 colour tags, keyframe every 2 s (`-g 60`), 3 B-frames.
- Audio: AAC 256 kb/s, 48 kHz.
- Subtitles: three mov_text tracks with language and title, off by default.
- Chapters from an FFMETADATA file built from the timeline (9 chapters).
- Metadata title, `+faststart` (the file starts playing before it is fully downloaded).
- **Length: `-t` with the picture's exact length, never `-shortest`.** `-shortest` also counts the subtitle tracks, which end with the last spoken line, and it silently cut the last 5.8 s of Resonance (see 15).
- Also writes `video/NN-name_youtube.txt`: title, description, chapter times, credits.

---

## 13. Quality checks before calling it done

Do all of them, on the final file, every time.

**Picture**
- [ ] Frame count equals the timeline: `ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 FILE`
- [ ] Video, audio and chapters all end at the film's full length (`ffprobe -show_entries stream=codec_name,duration`)
- [ ] Contact sheets of the whole film looked at, scene by scene (`tools/qa/contact_sheet.py`)
- [ ] Every scene change looked at frame by frame (fades, no ghost of the previous scene)
- [ ] The first and the last 3 seconds looked at (ident, end card)
- [ ] No text collides with anything; labels stay on their objects; exaggerations are labelled
- [ ] Palette meanings respected everywhere

**Sound**
- [ ] `python3 tools/qa/asr_check.py SCRIPTS_DIR build/audio/mix.wav`: mean word error rate below 3 % (Resonance: 1.2 %); listen to any line above 5 % (Whisper writes American spelling, so "favourite" counts as an error: ignore those)
- [ ] Loudness -14 LUFS ±1, peaks at -1 dBFS or lower (`make_audio.py` prints both)
- [ ] Listen to the whole film once with headphones: no clicks, the music never covers the voice, the ending plays out

**Facts and text**
- [ ] Every number on screen and in the voice matches the README and its source
- [ ] Subtitles read in all three languages; Arabic checked by a native speaker
- [ ] British spelling, SI units with a space, italic variables, no em dash

**Project**
- [ ] Piece README status and checklist updated; main README table updated
- [ ] Committed and pushed; big files through Git LFS

---

## 14. Delivery

### 14.1 The files
- `video/NN-name_16x9_en.mp4` (about 134 MB for 3 minutes), `renders/` hero still and thumbnail, `subtitles/*.srt`, `video/*_youtube.txt`.

### 14.2 A phone copy under 30 MB
The Claude app refuses files over 30 MB. A 720p two-pass copy of the 3-minute film is 26 MB and still looks good:
```bash
F=video/01-resonance_16x9_en.mp4
VF="scale=1280:720:flags=lanczos,hqdn3d=1.2:1.2:3:3"
ffmpeg -y -i $F -map 0:v:0 -vf "$VF" -c:v libx264 -preset slow -b:v 1100k -pass 1 -an -f null /dev/null
ffmpeg -y -i $F -map 0:v:0 -map 0:a:0 -map 0:s? -map_metadata 0 -map_chapters 0 -vf "$VF" \
  -c:v libx264 -preset slow -b:v 1100k -pass 2 -pix_fmt yuv420p -c:a aac -b:a 96k -c:s copy \
  -movflags +faststart phone_720p.mp4
```
(On Windows outside WSL, write `NUL` instead of `/dev/null`. The light denoise `hqdn3d` removes the film grain, which would otherwise eat the bit rate.) For a different length, video bit rate ≈ (27 MB × 8 / seconds) - 0.1 Mb/s.

### 14.3 A private web watch page (claude.ai Artifact)
`phenomena/01-resonance/web/index.html` is the page that was published: the film with a chapter bar drawn to scale, chapter list, subtitle buttons, both layers and the two real cases. Limits of those pages: 15 MB per file, 64 MB per publish, and only common file types (`.m3u8` and `.vtt` are refused). So:
- The film is cut into 4-second streaming pieces without re-encoding (HLS, the format YouTube and Netflix use):
  ```bash
  ffmpeg -i FILM.mp4 -map 0:v:0 -map 0:a:0 -c copy -f hls -hls_time 4 -hls_playlist_type vod \
    -hls_segment_type fmp4 -hls_fmp4_init_filename init.mp4 -hls_segment_filename 'seg_%03d.mp4' index.m3u8
  mv index.m3u8 playlist.txt
  ```
- The page plays `hls/playlist.txt` with hls.js 1.5.13 (from cdnjs, with jsdelivr and unpkg as fall-backs).
- The subtitles are written into the page as data and added with `VTTCue`, so no `.vtt` file is needed.
- Upload in batches under 60 MB to the same page (the files add up).
- Not yet confirmed: the cloud session could not play the published page itself (no browser access to the player library), so check once on a phone and a computer that it plays; if it does not, the phone copy (14.2) is the fall-back.

### 14.4 Git LFS
Cloud sessions may be blocked from `lfs.github.com` (the big-file server): then push the small files only and deliver the big ones directly, or allow that host in the environment's network settings. On a laptop, GitHub Desktop handles LFS by itself.

---

## 15. Pitfalls already solved

| Problem | Fix |
|---|---|
| `-shortest` in the final encode cut the last 5.8 s (it counts subtitle tracks, which end with the last line) | Use `-t` with the picture's exact length; check the final frame count |
| A render chunk could be missing or short and the join would not notice | Chunks named after their first frame; `make_final.py` checks coverage and lengths |
| `transform_apply(scale=True)` also applied the location | Pass `location=False, rotation=False` |
| Grid lines vanished far away and shimmered | Distance-adaptive line width, widen lines across the view, fade with distance |
| Bright floor, visible horizon | Infinity cove, darker floor base |
| Image flicker between frames | Fixed Cycles seed, not animated |
| `skia.Matrix(m)` cannot copy a matrix | `skia.Matrix.Concat(m, skia.Matrix())` |
| `lmodern.sty` missing in a minimal TeX Live | Remove `lmodern` and `T1` from the LaTeX preamble |
| Kokoro needs numpy 2, bpy needs numpy 1 | Separate venv for the voice |
| `np.trapezoid` missing in numpy 1.26 | `np.trapz` |
| Same-pitch notes cut each other in the score | Track note-offs per (channel, pitch) |
| Clicks at clip ends | 15 ms fades on every clip |
| Labels collided, a readout overlapped a curve, the ball was drawn outside the tower, a ghost highlight stayed from the last scene | Found by looking at contact sheets and single frames; fixed one by one |
| Abrupt cuts between scenes | Fade-ins of 0.5 to 0.6 s in the SCENES table |
| Colour-only signs are hard for colour-blind viewers | Add shape: filled "+" and hollow "-" chips |
| `pkill -f pattern` / `pgrep -f pattern` also matched Claude's own shell and killed it | Kill by exact process number (PID) |
| Render queues waiting on `pgrep` patterns got stuck on leftover shells | Wait on log lines or files instead |
| The cloud container restarted and background jobs stopped | `nohup` plus logs, renders that skip existing frames, a scheduled check-in |
| Blender program passes its own arguments to the script | Scripts read only what follows `--` |
| Blender's Python has no scipy | scipy imported only where the solver runs; cache the swing data first |
| Headless Chrome cannot make a window narrower than 500 px | Do not trust its "phone" screenshots below 500 px; measure the page width instead |
| Claude app upload limit 30 MB | 720p two-pass phone copy (14.2) |

---

## 16. Time and computer budget

Measured on the cloud machine: 4 CPU cores, 15 GB of memory, no graphics card.

| Job | Time |
|---|---|
| 3D hook, two swings, 640 frames, 8 samples | 110 min (about 10 s per frame) |
| 3D single swing, 400 frames | 47 min (7 s per frame) |
| 3D spring, 250 frames, 10 samples | 48 min (11 s per frame) |
| 3D Taipei damper, 250 frames | 40 min (9 s per frame) |
| 4K hero still, 48 samples | about 8 min |
| 2D compositing, whole film, 4 workers | a few minutes for 2D-only parts; slower where 3D frames are loaded |
| Final encode (x264 slow, CRF 18) | about 5.5 min (15 frames per second) |
| Phone copy, two passes | under 2 min |

A laptop with a recent NVIDIA graphics card (OptiX) is usually 5 to 20 times faster than 4 CPU cores in Cycles: use the time for more samples (32 to 64), 4K masters, or more 3D shots. Disk: the lossless chunks of a 3-minute film take about 5.5 GB; delete `build/video_chunks/` when the final is checked.

---

## 17. How Claude should run the job

- **Plan first**, as a task list: research, script, voice, timeline, physics, 3D, 2D, music, mix, subtitles, final, checks, delivery. Mark each task done only when it is checked.
- **Research before writing**; put sources and numbers in the piece README first.
- **Start long jobs in the background** (renders, encodes) with `nohup` and a log file, and do other work meanwhile (2D scenes, music, subtitles). Chain the long jobs in a small queue script that waits on log lines.
- **Render one frame before a hundred.** Look at it (open the PNG), fix, then render the rest.
- **Keep every step re-runnable**: skip frames that exist, cache slow calculations (`build/data/`), one WAV per line.
- **Look at the picture yourself**: preview frames, contact sheets, stills of every scene change. Listen with the speech check. Measure loudness, lengths, frame counts.
- **Verify the final file end to end** before telling anyone it is done (section 13). If something was wrong in an earlier message, say so plainly and correct it.
- **Update the status** (piece README checklist, main README table) as the piece moves; commit with honest messages.
- **Ask before anything destructive** (deleting files outside `build/`, overwriting a render someone may want).
- House rules at all times: palette meanings, SI units with a space, italic variables, British spelling, never the em dash, plain explanations for Ali.

---

## 18. How to do even better next time

- **Graphics card renders**: 32 to 64 samples, denoiser prefilter ACCURATE, 4K masters downscaled to 1080p for a crisper image.
- **More 3D**: the Millennium Bridge was 2D; a 3D deck with walkers, driven by the same physics, would be a showpiece.
- **Voice**: a human narrator, or French and Arabic voice versions (Kokoro has a French voice; Arabic needs another engine or a person). The stems make new language mixes easy.
- **Arabic subtitles** checked by a native speaker, and burned-in subtitle versions for social media.
- **Vertical 9:16 Short** (planned in the README): re-frame the best 45 to 60 s, bigger text, a hook in the first second.
- **Sound**: recorded foley (a real swing chain, a real spring) mixed with the synthesised effects.
- **Accessibility**: an audio-description track.
- **Automate the checks**: run `asr_check.py`, the loudness check and the frame count inside `build.sh`, and stop the build if any fails.

---

## 19. Prompt to start a new piece

Paste this into a new Claude session opened in the project folder, and change the subject:

> Read `docs/PRODUCTION_PLAYBOOK.md`, `CLAUDE.md`, `docs/STYLE_GUIDE.md`, `docs/WORKFLOW.md` and `phenomena/01-resonance/README.md` first. Then make piece 02 about **[subject from docs/BACKLOG.md]** at the same quality as Resonance or better: about 3 minutes, 16:9, 1080p, 3D in Blender plus 2D from `tools/epmotion`, every motion computed from the equations, facts checked with sources and myths avoided, narration with Kokoro, original music and synthesised sound, subtitles in English, French and Arabic, chapters, thumbnail. Copy `phenomena/_template/` and reuse the structure of `phenomena/01-resonance/scripts/`. Start with the research and the script, show me the script before recording the voice, then work through the pipeline and the quality checks in the playbook. Explain what you are doing in plain words, and render on my graphics card with `EP_DEVICE` if I have one.
