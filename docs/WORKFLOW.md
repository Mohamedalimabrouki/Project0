# Workflow: from idea to published piece

Ten steps. The order matters: **words and numbers first, pixels last.** It is much cheaper to fix a wrong idea in a sentence than in a 3-hour render.

---

## 1. Pick a subject and create its folder

1. Choose a phenomenon from the [backlog](BACKLOG.md).
2. Copy the folder `phenomena/_template/` and rename the copy `NN-name`, for example `02-capstan-effect`.
   - `NN` = the next free two-digit number.
   - Name in lowercase, words joined with hyphens.

## 2. Write the explanation

Fill in the `README.md` of the new folder:
- **See it** (kids layer), maximum 3 sentences.
- **Understand it** (engineers layer), with the equation, the assumptions and real numbers.
- **Accuracy notes**: what is simplified, what is exaggerated, which myths to avoid.
- **Sources**.

Get it checked before drawing anything. Claude can fact-check it, but for anything that will be published, a second engineer reading it is worth it.

## 3. Storyboard

- 5 to 7 scenes, **one idea per scene**.
- Write each scene in the table of the README: what we see, what is said, how long.
- Quick sketches (paper photos are fine) go in `sources/`.

## 4. Build in Blender

1. New file, then run [`tools/blender_palette.py`](../tools/blender_palette.py) (Scripting tab, Open, Run). All house materials are now there.
2. Scene Properties > Units: Metric, unit scale 1.0.
3. Save as `blender/NN-name_v001.blend`. Each important change gets the next number: `v002`, `v003`...
4. When a motion must be physically exact, do not "animate by eye": compute it and drive the keyframes from the numbers (Claude can write the small Python script for this).

## 5. Render

- Render **frames** (PNG image sequence) into a folder called `frames/` next to the `.blend`. This folder is never uploaded (it is too big), only the final video is.
- Settings and sizes: see the [style guide](STYLE_GUIDE.md), sections 4 and 5.

## 6. Edit and sound

- Assemble frames, voice and music in Blender's Video Sequencer or in DaVinci Resolve (free version).
- Target loudness about -14 LUFS.
- Add the opening card, the logo in the bottom-right corner and the closing takeaway card.

## 7. Subtitles

1. Write `subtitles/NN-name_en.srt` first.
2. Translate to `NN-name_fr.srt` and `NN-name_ar.srt` (Claude can draft them; have the Arabic read by a native speaker before publishing).
3. Save as UTF-8 so Arabic and French accents display correctly.

## 8. Export the finals

| What | Where | Name example |
|---|---|---|
| Full video | `video/` | `02-capstan-effect_16x9_en.mp4` |
| Short | `video/` | `02-capstan-effect_9x16_en.mp4` |
| Hero still | `renders/` | `02-capstan-effect_hero.png` |
| Thumbnail | `renders/` | `02-capstan-effect_thumb.png` |

## 9. Update the status

- In the piece's README, tick the status checklist.
- In the main [README](../README.md), update the line in "The collection" table.

## 10. Save to GitHub

The easiest tool is **GitHub Desktop** (free, no command line):

1. Open the repository in GitHub Desktop. It shows every file you changed.
2. Write a short summary, for example `Resonance: first render of scene 3`, and click **Commit**. A commit is a saved snapshot: you can always go back to it.
3. Click **Push origin**. This uploads your snapshots to GitHub.

### About big files

Blender files, videos and other heavy files are stored with **Git LFS** (Large File Storage). The list of which file types this applies to is in [`.gitattributes`](../.gitattributes). GitHub Desktop handles LFS for you; the first time, it may ask to "initialise Git LFS": say yes.

GitHub gives a limited amount of free LFS storage, and every version you push counts. So:
- Push the `.blend` at meaningful milestones, not after every small change.
- Never push the `frames/` folder (it is already excluded).
- Push final videos once they are final.

---

## Where Claude helps most

- Fact-checking the engineers layer and hunting for myths.
- Turning the engineers layer into a kids layer (and the other way round).
- Writing small Blender Python scripts that move objects exactly as the equations say.
- Drafting French and Arabic subtitles.
- Reviewing a render screenshot against the style guide.
