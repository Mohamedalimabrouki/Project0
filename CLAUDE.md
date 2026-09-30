# CLAUDE.md

Guidance for Claude when working in this repository.

## What this is

A collection of professional visual art (Blender renders, videos, stills) that explains engineering phenomena. Every piece has two layers: **See it** for kids and curious people, **Understand it** for engineers. Owner: Ali, a mechatronics engineer who does 3D (Blender), video and subtitles. Ali is not a software developer: explain in plain language and define any jargon.

## Rules that always apply

- **Beautiful, but never wrong.** Physics must be correct. Exaggerations are labelled on screen. Never repeat popular myths (see the accuracy notes in each piece).
- **Never AI-made, in look or in sound.** Narration is a real human voice (no text-to-speech); no AI-generated images or footage. Everything must look and sound like a professional studio made it.
- **Colour means something.** Use only the palette in `docs/STYLE_GUIDE.md` and keep each colour's meaning (vermillion = force, blue = motion, and so on).
- SI units, italic variables, upright units with a space (`5 kg`).
- British spelling in English text (colour, organise).
- Never use the em dash character. Use a hyphen (-) instead.
- Subtitles in English, French and Arabic. Arabic flows right-to-left, equations and numbers stay left-to-right.

## Where things are

- `phenomena/NN-name/` - one folder per piece. Copy `phenomena/_template/` to start a new one.
- `docs/STYLE_GUIDE.md` - colours, fonts, formats, Blender settings, accuracy rules.
- `docs/WORKFLOW.md` - the ten steps from idea to published piece.
- `docs/BACKLOG.md` - subjects to make next.
- `assets/palette/palette.json` - the palette, single source of truth. `tools/blender_palette.py` and `docs/STYLE_GUIDE.md` repeat its values: keep all three in sync.
- `tools/blender_palette.py` - creates the house materials in Blender (tested in Blender 5.0).
- `phenomena/02-aliasing/code/` - a piece made entirely with code (every frame drawn in headless Chromium from the equations). Its `README.md` explains how to build it and `SCENE_GUIDE.md` holds the rules and drawing API; reuse the engine for other code-drawn pieces. `code/audio/voice.py` turns a recorded narration into the narrated versions (script and recording guide in `phenomena/02-aliasing/voice/`); `code/web/` builds the private screening-room page (a claude.ai artifact).
- `assets/fonts/` - Inter and IBM Plex Sans Arabic (SIL Open Font Licence). `assets/brand/logo-mark.svg` - the series mark for the bottom-right corner.

## When helping

- Fact-check the engineers layer and give sources.
- For exact motion, write Blender Python that drives keyframes from the equations rather than animating by eye.
- When a piece progresses, update its status checklist and the table in the main `README.md`.
