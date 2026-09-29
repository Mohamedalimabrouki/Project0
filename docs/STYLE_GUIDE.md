# Style guide

This guide is what makes every piece look like it belongs to the same professional series. When in doubt, choose **clarity over decoration**.

---

## 1. Colour means something

The same colour always means the same physical thing, in every piece. A viewer who has watched one episode can "read" the next one without being told.

The palette is the Okabe-Ito set, which is designed so that people with colour blindness can still tell the colours apart.

| Swatch | Name | Hex | Always means |
|---|---|---|---|
| <img src="../assets/palette/swatches/force.svg" width="24" alt=""> | Vermillion | `#D55E00` | **Force, load, stress** |
| <img src="../assets/palette/swatches/motion.svg" width="24" alt=""> | Blue | `#0072B2` | **Motion, velocity, displacement** |
| <img src="../assets/palette/swatches/energy.svg" width="24" alt=""> | Orange | `#E69F00` | **Heat, energy, power** |
| <img src="../assets/palette/swatches/fluid.svg" width="24" alt=""> | Sky blue | `#56B4E9` | **Fluid, air, flow** |
| <img src="../assets/palette/swatches/field.svg" width="24" alt=""> | Reddish purple | `#CC79A7` | **Electricity, magnetism, fields** |
| <img src="../assets/palette/swatches/balance.svg" width="24" alt=""> | Bluish green | `#009E73` | **Balance, safe, "it works"** |
| <img src="../assets/palette/swatches/highlight.svg" width="24" alt=""> | Yellow | `#F0E442` | **Look here** (highlight, on dark backgrounds only) |

Neutrals:

| Swatch | Name | Hex | Used for |
|---|---|---|---|
| <img src="../assets/palette/swatches/ink.svg" width="24" alt=""> | Ink | `#12161C` | House background, text on light backgrounds |
| <img src="../assets/palette/swatches/steel.svg" width="24" alt=""> | Steel | `#8C96A0` | Structures, parts, anything that is "just the object" |
| <img src="../assets/palette/swatches/paper.svg" width="24" alt=""> | Paper | `#F4F3EF` | Light background, text on dark backgrounds |

Ready-made palette files for Blender, Inkscape, GIMP and Krita are in [`assets/palette/`](../assets/palette/). In Blender, run [`tools/blender_palette.py`](../tools/blender_palette.py) to create all the materials at once.

**Never rely on colour alone.** Always add a label, a symbol or a shape difference, so the image still works in black and white.

## 2. Arrows and symbols

| Thing | How it is drawn |
|---|---|
| Force | Thick solid arrow, filled head, vermillion |
| Velocity / motion | Thinner arrow, open head, blue |
| Flow | Streamlines or particles, sky blue, moving in the flow direction |
| Field lines | Thin curved lines, reddish purple |
| Rotation | Curved arrow around the axis |

- Arrow length is proportional to the size of the quantity. If it cannot be, write "not to scale".
- Every arrow gets a short label the first time it appears (for example **F**, **v**, **q**).

## 3. Typography

| Use | Font | Licence |
|---|---|---|
| Latin text (English, French, Portuguese) | **Inter** | SIL Open Font Licence (free) |
| Arabic text | **IBM Plex Sans Arabic** (or Noto Sans Arabic) | SIL Open Font Licence (free) |
| Equations | Proper math typesetting (LaTeX style) | |

Equation rules (the international convention):
- Variables in *italic*: *m*, *k*, *F*.
- Units upright, with a space: `5 kg`, `9.81 m/s²`, never `5kg`.
- SI units only. If an everyday unit helps kids (for example "as heavy as 3 cars"), add it next to the SI value, not instead of it.
- Arabic text flows right-to-left, but equations and numbers stay left-to-right, exactly as in Arabic textbooks.

## 4. Formats

| Output | Size | Frame rate | Where it goes |
|---|---|---|---|
| Full video (both layers) | 1920 x 1080 (16:9) | 30 fps (60 fps for slow motion shots) | YouTube, presentations |
| Short (kids layer) | 1080 x 1920 (9:16) | 30 fps | YouTube Shorts, Reels, TikTok |
| Feed post | 1080 x 1350 (4:5) | still | Instagram, LinkedIn |
| Hero still | 3840 x 2160 (4K) | still | Posters, prints, thumbnails |

- **Length:** Short 30 to 60 s. Full video 2 to 4 min.
- **Safe area:** keep text inside the central 90 % of the frame. On vertical videos, also keep the bottom 20 % and the right edge free (the app buttons cover them).
- **Audio loudness:** about -14 LUFS, the level most streaming platforms normalise to.
- **Narration:** a real person, recorded close and dry (never a synthetic voice). The voice sits about 12 to 15 dB above the music and effects; the music dips under it and rises in the pauses. A narrated full video carries no burned-in captions (subtitles go in a separate .srt); Shorts keep their captions, since many people watch them without sound.
- **Export:** render an image sequence (PNG) first, then encode to MP4 (H.264). If Blender crashes at frame 800, you keep frames 1 to 799.

## 5. Blender settings

| Setting | Value | Why |
|---|---|---|
| Render engine | EEVEE for most shots, Cycles for hero shots | EEVEE is fast enough to iterate |
| Colour management, realistic shots | View transform **AgX** | Natural looking light |
| Colour management, diagram shots | View transform **Standard** | Palette colours come out as the hex codes |
| Camera | 50 mm for natural views, orthographic for "technical drawing" views | Avoids wide-angle distortion that makes parts look wrong |
| Units | Scene units set to Metric, unit scale 1.0 | 1 Blender unit = 1 m, so physics numbers stay honest |

## 6. The two layers

**See it (kids layer)**
- Maximum 3 sentences.
- No word a 10-year-old would not know. If a technical word is needed, explain it in the same sentence.
- Start from something they have felt or seen (a swing, a straw, a bicycle).

**Understand it (engineers layer)**
- The governing equation, every variable named with its unit.
- The assumptions (what we ignore and why it is fine).
- Typical real values (orders of magnitude).
- At least one real-world case, with a source.

## 7. Accuracy rules (non-negotiable)

1. **Numbers before pixels.** Write down the real values before animating.
2. **Label every exaggeration** ("displacement x50", "slowed down 20 times").
3. **Show the scale** with a scale bar or a familiar object.
4. **Simulations:** Blender physics is approximate. When the motion must be exact, compute it (for example in Python) and drive the keyframes from the result.
5. **No myths.** Do not repeat popular wrong explanations. Where a myth is common, it is worth showing it and correcting it.
6. **Cite sources** in the piece's README and keep copies or links in `sources/`.

## 8. Accessibility

- Subtitles on every video, in English, French and Arabic.
- Text contrast at least 4.5 : 1 against its background.
- No flashing faster than 3 times per second.
- Never use colour as the only way to tell two things apart (see section 1).

## 9. Signature

- Opening card: **Engineering Phenomena** / episode number / phenomenon name.
- Small logo mark in the bottom-right corner, same place in every piece: [`assets/brand/logo-mark.svg`](../assets/brand/logo-mark.svg) (about 60 % opacity on the ink background).
- Closing card: the one-sentence takeaway, in the kids layer wording.
