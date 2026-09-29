# Scene guide - Engineering Phenomena 02 · Aliasing

The rules and tools for everyone who writes a scene of this film. Read it all once.
The film script and storyboard are in `../README.md`. The series rules are in
`/CLAUDE.md` and `/docs/STYLE_GUIDE.md` at the repository root.

## 1. The quality bar

World-class, first time. Picture a premium engineering documentary with the clarity
of the best maths explainers: calm, precise, generous space, one idea at a time,
every movement meaningful. **Beautiful, but never wrong.** Nobody will fix this
after you, so check your own work visually until you would sign it.

## 2. How the film is made

Every frame is drawn by code on a 1920 x 1080 canvas in headless Chromium, 30
frames per second (fps). This matters for the subject: **the video itself samples
the world 30 times per second**, so a wheel drawn at a real rotation rate shows
real aliasing on the viewer's screen. Real-time demonstrations must be exact.

```
code/
  engine/ep.js          shared drawing library (import nothing else from engine/)
  engine/stage.js       loads scenes, draws captions and the series mark
  scenes/<id>.js        one file per scene  <- you write this
  data/strings/<id>.json on-screen text for your scene (EN final, FR/AR by the translator)
  data/comps.json       the timeline (scene order and durations)
  render.mjs            renderer
```

## 3. Render and look (do this constantly)

Run from `phenomena/02-aliasing/code/`:

```bash
# one frame in 10 of your scene on one contact sheet (fast overview of motion)
node render.mjs --scene s04_trick --every 10 --contact --workers 2
# exact moments, full resolution PNGs in build/main_en_s04_trick/frames/
node render.mjs --scene s04_trick --at 3.5,12,20.25 --workers 2
# same in Arabic or French (layout, direction, text length)
node render.mjs --scene s04_trick --lang ar --at 3.5,12 --workers 2
# debug overlay: safe area, caption band, time
node render.mjs --scene s04_trick --at 12 --debug
```

Then open the PNGs with the Read tool and really look: crop and zoom with Python
PIL for details (text edges, arrow heads, overlaps). File names are the global
frame number `fNNNNN.png`. The renderer prints PROBLEMS (missing strings,
equations not listed in `math`, errors). Your scene must end with none except
missing French and Arabic translations. Keep `--workers 2` (several people share
4 CPU cores). Never render the whole film.

## 4. The scene contract

```js
export default {
  duration: 38.5,                 // seconds, must match data/comps.json
  captions: [                     // narration: the engine draws these in the caption band
    { key: 's04.c1', in: 0.8, out: 5.0 },          // and makes the .srt subtitles from them
    { key: 's02.srt', in: 0.6, out: 5.9, burn: false },   // subtitles only
  ],
  cues: [ { t: 1.2, sfx: 'shutter' }, { t: 4, sfx: 'whirr', dur: 3, rate: 5.5 } ],
  math: ['f_s > 2\\,f_{\\max}', { tex: 'f = N\\,f_r', color: '#0072B2' }],
  music: 'explain',               // mood tag for the composer (optional)
  hideLogo: false,                // or (t) => 0..1
  strings: ['s01_hook'],          // optional: also load other scenes' string files (to reuse their keys)
  setup(EP, info) { },            // optional, runs once: precompute tables here
  render(ctx, t, EP, info) { },   // draws ONE frame. info = {W, H, frame, t, duration, lang, rtl}
};
```

**Golden rule: `render` is a pure function of `t`.** No variables that change
between frames, no `Date`, no `Math.random()` (use `EP.rng(seed)` created inside
render or in setup), no accumulation. Any frame can be drawn alone, in any order.
Compute positions directly from time and equations. For a rotation rate that
changes over time, integrate it once in `setup` with `EP.angleTable(rate, t0, t1)`
and read the angle in `render`.

The canvas arrives clean (state saved and restored around your call). Start by
drawing the background: `EP.bg(ctx, W, H)`.

Captions: the English text in your strings file is the final script. Keep each
key's text. You may move `in`/`out` times to match your animation, but keep them
inside `[0.6, duration - 0.6]`, never overlapping each other, and at least
0.3 s per word... in practice hold each line long enough to read it twice
(about 2.5 words per second at most). The engine fades them in and out.

You may add your own label keys to your strings file (`"s04.newlabel": {"en": "...", "fr": "", "ar": ""}`),
short and plain. Never write visible text directly in code, except symbols,
numbers and units (use `EP.qty`, `EP.num`) and TeX.

## 5. Frame layout (16:9, 1920 x 1080)

| Zone | Where | Use |
|---|---|---|
| Caption band | y 64 to 260, centred | Narration, drawn by the engine. Keep it clear of your drawings while a caption shows. |
| Chapter label | centred, baseline y = 86 | `EP.eyebrow(ctx, EP.T('chapter.see'), { x: W/2, y: 86, align: 'center' })`. Only at the start of a chapter (s03, s05, s06). |
| Stage | y 280 to 930 | Your pictures, diagrams, labels. |
| Bottom band | y 930 to 1026 | Keep important things out (platform subtitles appear here). Small badges are fine at the left. |
| Series mark | bottom-right corner | Drawn by the engine. Keep x > 1480, y > 990 empty. |
| Safe area | 96 px from left/right, 54 px from top/bottom | Nothing important outside. |

**Arabic (right to left).** Text flows right to left; equations, numbers and
graphs stay left to right (as in Arabic textbooks). Diagrams do not mirror. Text
that hugs the reading-start side uses `x: EP.startX(96), align: 'start'` (it
lands on the right in Arabic). Centred text needs nothing special. Arabic and
French strings are often 20 to 30 % longer: give labels `maxWidth` and `shrink: true`.

## 6. Colour means something

| Colour | `EP.PAL.` | Meaning in this film |
|---|---|---|
| Blue #0072B2 | `motion` | Real motion. **Solid** = what really happens. **Dashed** = what we see (the alias). |
| Yellow #F0E442 | `highlight` | Look here: the painted spoke, the key point, the marker on a graph. |
| Paper #F4F3EF | `paper` | Text, snapshot marks, sample dots, camera icon. |
| Steel #8C96A0 | `steel` | Objects: wheel, car, rotor, lathe, axes, secondary text. |
| Green #009E73 | `balance` | "It works": the zone where the video tells the truth, a correct result. |
| Purple #CC79A7 | `field` | Electrical signals (sensor voltage in s07). |
| Orange #E69F00 | `energy` | Light output of a lamp (flicker waveform in s06, strobe in s07). |
| Sky blue #56B4E9 | `fluid` | Air flow (for example rotor downwash), only if you draw air. |
| Vermillion #D55E00 | `force` | Forces only. Probably not used in this film. **Never** as "danger" or "wrong". |
| Ink #12161C | `ink` | Background. |

Only these colours, their transparencies (`EP.rgba(hex, a)`) and mixes between
them (`EP.mix(a, b, k)`, `EP.SHADE`). Never rely on colour alone: every coloured
thing also has a label, a shape or a line style (solid vs dashed). Text contrast:
paper, steel, yellow, green, sky blue, purple and orange are fine at any size on
ink; blue text only large (32 px or more, weight 600+).

Arrows (style guide): motion = `EP.arrow(... {kind: 'motion'})` thinner, open head,
blue; rotation = `EP.arcArrow`. Arrow length proportional to the quantity, or label
"not to scale". Label every arrow the first time it appears.

## 7. Typography

| Role | Call | Size / weight |
|---|---|---|
| Display (a big word or number) | `EP.text` | 96 to 160 px, 800 |
| Headline in the stage | `EP.text` | 56 to 72 px, 700 |
| Label | `EP.text` | 30 to 36 px, 600 |
| Small note / unit | `EP.text` | 24 to 28 px, 500, steel |
| Changing numbers | `EP.textTab` | digits do not jitter |
| Equations | `EP.math` | TeX, 48 to 72 px; list the TeX in `math` |
| Badge ("Slowed down x30") | `EP.badge` | fixed style |

Equations follow the convention: variables italic (TeX does it), units upright
with a space: `30\ \mathrm{Hz}`. Symbols of this film: *f* (spoke frequency, Hz),
*f*<sub>r</sub> (wheel turns per second), *N* (number of spokes), *f*<sub>s</sub>
(pictures or samples per second, 30 Hz), *f*<sub>a</sub> (frequency seen), 
*f*<sub>s</sub>/2 (Nyquist limit). Use British spelling. Never use the em dash
character; use a hyphen. SI units first; km/h may follow m/s for children.
Numbers through `EP.num` / `EP.qty` (they give 12,4 in French and Arabic).

## 8. Motion principles

- Ease everything (`EP.prog(t, t0, t1, EP.ease.outCubic)`), never linear pops.
  Entrances 0.4 to 0.8 s (outCubic / outQuint), exits 0.3 to 0.5 s (inOutSine).
- Stagger related elements by 0.08 to 0.15 s. One focal point at a time.
- Hold: after something appears, leave it still long enough to be understood.
- Text animates as a whole (fade, small rise, `reveal` wipe). Never letter by
  letter (it breaks Arabic joining).
- Start calm and end calm: at t < 0.5 and in the last 0.5 s your scene cross-fades
  with its neighbours, so do not put important action there. Your first frame
  may be just the background; elements enter after about 0.4 s.
- No camera shake, no lens flares, no particle confetti, no neon glow on
  everything, no gradient text, no emoji, no pill-shaped buttons, no fake
  "tech HUD" decoration, no drop shadows except the soft legibility shadow. A
  thin grid background is already there.

## 9. Honesty on screen (accuracy rules)

- **Slow motion** (pictures shown one by one) always carries a badge:
  `EP.badge(ctx, EP.T('badge.slowx', { n: 30 }), {...})` with the true factor
  (one picture per second when the real gap is 1/30 s = x30).
- **Real-time demonstrations** (the wheel drawn at its true rate so the viewer's
  own screen shows the aliasing) carry `EP.T('badge.real')`. They must be exact:
  angle at frame n = the true angle at t = n/30. No motion blur on these.
- Anything that shows what an eye would see under a flickering light (we cannot
  show 100 Hz on a 30 fps video) is a **simulation**: `EP.T('badge.simulated')`.
- Invented but realistic numbers: `EP.T('badge.example')`.
- Say "seems to" / "looks", never that the wheel "really" turns backwards.

**Accessibility, non-negotiable:** no flashing. No area larger than about a
tenth of the screen may change brightness strongly more than 3 times per second.
A flicker or strobe is shown with an icon and a waveform, never by flashing the
frame. Small spokes changing position is fine.

## 10. Engine reference (`EP.` = everything exported by engine/ep.js)

- `FPS` (30), `TAU`, `DEG`, `PAL`, `SHADE`, `rgba(hex, a)`, `mix(a, b, k)`
- `clamp, lerp, invLerp, remap(x, a0, a1, b0, b1)`, `wrap(x, p)`, `wrapSigned(x, p)` (nearest-match offset in [-p/2, p/2])
- `ease.*` (outCubic, inOutCubic, outQuint, outBack, inOutSine, outExpo, smooth, ...)
- `prog(t, t0, t1, ease)` -> 0..1; `win(t, tIn, tOut, dIn, dOut)` -> opacity window
- `rng(seed)`; `polar(cx, cy, r, a)` (clock angle: 0 = up, clockwise positive)
- `angleTable(ratePerSecond(t), t0, t1)` -> `angle(t)` in radians (exact integral)
- `T(key, vars)`, `num(x, digits)`, `qty(x, unit, digits)`, `isRTL()`, `startX(x)`, `STAGE.W/H`
- `text(ctx, str, {x, y, size, weight, color, opacity, align, anchor, maxWidth, maxLines, shrink, tracking, caps, latin, reveal, shadow})` -> box
- `measure(ctx, str, opts)`, `textTab(ctx, str, {x, y, size, weight, color, align})`
- `math(ctx, tex, {x, y, size, color, align, anchor, opacity})` -> box (tex must be in `math`)
- `arrow(ctx, x1, y1, x2, y2, {kind, color, width, dash, progress, alpha})`
- `arcArrow(ctx, cx, cy, r, a0, a1, {kind, dash, progress, alpha, width})` (clock angles)
- `roundRect(ctx, x, y, w, h, r)`, `badge(ctx, str, {x, y, align})`, `eyebrow(ctx, str, {x, y, align})`
- `bg(ctx, W, H, {grid, vignette, offsetX, offsetY})`, `camera(ctx, {x, y, s, shot})`
- `wheel(ctx, {x, y, r, angle, spokes=5, highlight, highlightAlpha, tyre, caliper, opacity})`
- `wheelGhost(ctx, {x, y, r, angle, spokes, color, opacity, width, dash, only})`, `spokePath(r, i, angle, spokes)`
- `car(ctx, {x, y, r, rearAngle, frontAngle, highlight, opacity, wheels})` (x, y = rear wheel centre; front wheel at x + 7.7 r; ground at y + r)

The wheel: tyre radius *R* = 0.33 m, circumference 2.0735 m, 5 identical spokes
(72° apart). Spoke 0 points up at angle 0. A car driving right turns its wheels
clockwise: the angle increases. Useful truths at 30 fps: 5.5 turns/s looks like
-0.5 turns/s (6° backwards per picture); 6 turns/s looks frozen (44.8 km/h);
3 turns/s = Nyquist limit (15 Hz spoke frequency), direction ambiguous.

If you need a helper the engine lacks, write it inside your scene file. Do not
edit anything in `engine/`, `data/comps.json`, other people's scenes or strings.
If the engine has a bug, work around it locally and report it.

## 11. Sound cues

`cues: [{ t, sfx, dur?, gain?, pan?, rate? }]` (t in seconds from your scene start,
gain in dB, default 0, pan -1..1). The composer builds these sounds:

| sfx | Sound | Parameters |
|---|---|---|
| `whoosh` | soft air movement, something slides in | dur |
| `swoosh_rev` | reversed whoosh that lands on the next beat | dur |
| `tick` | soft clock tick | |
| `shutter` | camera shutter click (a picture is taken) | |
| `pop` | soft UI pop (label or dot appears) | |
| `blip` | tiny high blip (sample dot, graph point) | |
| `riser` | rising tension | dur |
| `hit` | deep soft impact (title, big reveal) | |
| `shimmer` | glassy shimmer (frozen moment) | dur |
| `glitch` | short digital stutter (the illusion is revealed) | |
| `whirr` | spinning machine | dur, rate (turns per second) |
| `car` | car driving, pitch follows speed | dur |
| `rotor` | helicopter rotor chop | dur, rate (blade passes per second) |
| `hum` | electrical 100 Hz hum of a lamp | dur |
| `motor` | electric motor whine | dur |
| `click` | small switch click (toggle something) | |

Use sound to underline, not to decorate: one cue per meaningful event. Shutter
clicks faster than 3 per second become noise; in real-time segments use one
`whirr` instead.

## 12. Definition of done

1. The scene tells its part of the story exactly as the storyboard intends, and it
   is beautiful at every moment (check a contact sheet at `--every 10` and at
   least 8 full-size frames at key moments, in English AND Arabic, one in French).
2. Physics: every number, angle and rate on screen is computed, not typed by eye,
   and matches the equations. Real-time demos are exact.
3. Captions timed, readable, never covered by your drawings.
4. No PROBLEMS except missing FR/AR translations. No overlaps, no text outside the
   safe area, nothing clipped, no Arabic text broken or misplaced.
5. Your report: what you built, the key moments (times), any engine issue or
   workaround, and new string keys you added.
