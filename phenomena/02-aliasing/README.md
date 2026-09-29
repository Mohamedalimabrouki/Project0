# 02 · Aliasing (the wagon-wheel effect)

> **Take pictures too slowly, and fast things can look slow, stopped, or even backwards.**

| Field | Status | Formats planned |
|---|---|---|
| Vibrations and waves · Mechatronics (sampling) | In production: script, storyboard, code engine done | Full 16:9 (EN, FR, AR), Hero still, Thumbnail |

This piece is made **entirely with code**: every frame is drawn by a small program from the equations (see [`code/`](code/)). Nothing is animated by eye. That matters here more than anywhere, because a video is itself a sampling machine: when the film shows a wheel turning at 5.5 turns per second, your own screen shows it creeping backwards. The demonstrations are real, not simulated.

---

## See it (kids layer)

A video is not smooth movement: it is a fast flip book of still pictures, 30 every second. If a wheel turns almost exactly from one spoke to the next between two pictures, each spoke lands just behind where its neighbour was, and your brain links it to the closest one, so the wheel seems to turn slowly backwards. Engineers call this aliasing, and they avoid it by taking pictures (samples) more than twice as fast as the fastest thing they want to see.

## Understand it (engineers layer)

**Sampling.** A camera, or any digital system, does not see a continuous signal *x*(*t*). It records samples *x*(*n*/*f*<sub>s</sub>), where *f*<sub>s</sub> is the sampling rate (30 Hz for this video).

**Aliasing.** A sinusoid of frequency *f* and one of frequency *f* − *k*·*f*<sub>s</sub> (any whole number *k*) give exactly the same samples. After sampling they cannot be told apart. The frequency we perceive is the one closest to zero:

```
f_a = f − f_s · round(f / f_s)          with  −f_s/2 ≤ f_a ≤ f_s/2
```

A negative *f*<sub>a</sub> means the motion appears reversed.

**The wheel.** A wheel with *N* identical spokes looks the same after 1/*N* of a turn, so what the camera samples is the spoke-passing frequency, not the turning rate:

```
f = N · f_r
```

| Symbol | Meaning | Unit |
|---|---|---|
| *f*<sub>r</sub> | Wheel turning rate | turns per second (Hz) |
| *N* | Number of identical spokes | - |
| *f* | Spoke-passing frequency | Hz |
| *f*<sub>s</sub> | Sampling rate (pictures per second) | Hz |
| *f*<sub>a</sub> | Frequency seen after sampling (alias) | Hz |
| *f*<sub>s</sub>/2 | Nyquist frequency | Hz |

**Nyquist-Shannon sampling theorem.** A signal whose highest frequency is *f*<sub>max</sub> is captured without ambiguity only if

```
f_s > 2 · f_max
```

Exactly at *f*<sub>s</sub> = 2·*f*<sub>max</sub> the direction is ambiguous (the spokes jump half a gap each picture).

**Worked numbers (this film's wheel):** tyre radius 0.33 m, circumference 2.0735 m, 5 spokes, 30 pictures per second.

| Car speed | *f*<sub>r</sub> | *f* = 5·*f*<sub>r</sub> | Turn per picture | *f*<sub>a</sub> | What the video shows |
|---|---|---|---|---|---|
| 14.9 km/h | 2.0 Hz | 10 Hz | 24° | +10 Hz | Correct, forwards |
| 22.4 km/h | 3.0 Hz | 15 Hz | 36° | ±15 Hz | Nyquist limit, ambiguous |
| 37.3 km/h | 5.0 Hz | 25 Hz | 60° | −5 Hz | Backwards, 1 turn per second |
| 41.1 km/h | 5.5 Hz | 27.5 Hz | 66° | −2.5 Hz | Backwards, slowly (6° per picture) |
| 44.8 km/h | 6.0 Hz | 30 Hz | 72° | 0 | Frozen |
| 47.0 km/h | 6.3 Hz | 31.5 Hz | 75.6° | +1.5 Hz | Forwards, slowly |
| 89.6 km/h | 12.0 Hz | 60 Hz | 144° | 0 | Frozen again |

**Assumptions**
- Instant snapshots (very short exposure). Real cameras blur the image during the exposure, which softens the effect but does not remove it.
- Identical, evenly spaced spokes. A single marked spoke has *N* = 1 and aliases only above 15 turns per second.
- The viewer's brain matches each spoke to the nearest spoke in the next picture (the shortest-path rule of apparent motion).

**Typical values**
- Video: 24, 25, 30, 50 or 60 pictures per second.
- Electric lighting on 50 Hz mains: light output can ripple at 100 Hz (120 Hz on 60 Hz mains) with some ballasts and LED drivers.
- Industrial data acquisition: sampling 5 to 10 times the highest frequency of interest is common, with an analogue anti-aliasing low-pass filter before the converter, because real filters are not perfectly sharp.

**Real-world cases**
- **Helicopter rotors that look frozen on video:** the blade-passing frequency equals the frame rate (for example 5 blades × 6 turns per second = 30 passes per second, example values).
- **The stroboscopic hazard in workshops:** under light flickering at 100 Hz, a 4-jaw lathe chuck turning at 1500 rpm (25 turns per second, 100 jaw passes per second) can look stopped. Lighting guidance warns about this effect. [Sources 5, 6]
- **Sensors and controllers (mechatronics):** a 900 Hz vibration read 1000 times per second produces exactly the same samples as a (phase-inverted) 100 Hz wave. The controller cannot tell. Fix: filter out frequencies above *f*<sub>s</sub>/2 before the analogue-to-digital converter, and sample fast enough. Encoders read too slowly miscount in the same way.
- **Aliasing on purpose:** a stroboscope or an ignition timing light flashes at (or near) the rotation rate, so a fast machine looks still or slow, for inspection while it runs.

## Accuracy notes

- **"Seems to", never "is".** The wheel never turns backwards. The film always says it *seems* to.
- **Video versus your own eyes.** In film and video the effect is pure sampling: it is in the recorded frames and can be measured. A similar illusion is sometimes reported with the naked eye in continuous light; its cause is debated and it is a different mechanism. The film is only about the camera. [Sources 3, 4]
- **Real-time demos are real.** Scenes 1, 4 (second half) and 5 draw the wheel at its true turning rate; the viewer's screen does the aliasing. They are labelled "Real speed: 30 pictures per second".
- **Slow-motion steps** (pictures shown one per second) are labelled "Slowed down ×30".
- **Under flickering light** we cannot show a 100 Hz flicker on a 30 fps video, so the lathe scene is labelled "Simulated view".
- **Twice is the theoretical minimum**, not a design target. Real systems sample much faster and filter first.
- **Different effect, not aliasing:** bent or wobbly propellers in phone videos come from the rolling shutter (the picture is read line by line), not from aliasing. Not shown, to keep one idea per piece.
- **No flashing on screen.** A film about strobes must not strobe: flicker is shown as icons and waveforms only (accessibility rule, [Source 7]).

## Storyboard

30 fps, 1920 × 1080. Music at 120 beats per minute: every scene starts on a bar line. Narration is on-screen text in the caption band at the top (the bottom stays free for platform subtitles). Total 3:00.

| # | Scene | Time | What we see | What is said (on screen) | Duration |
|---|---|---|---|---|---|
| 1 | Hook | 0:00 | A car accelerates from walking pace to 47 km/h. Speed shown in m/s and km/h. The wheels, drawn at their true rate, first turn forwards, then blur into confusion, then seem to spin backwards and slow down, then freeze at 44.8 km/h, then creep forwards. The camera pushes in on the rear wheel. | "This car is speeding up." / "Now watch the wheel." / "It seems to turn backwards!" / "Now it seems to stand still." / "The car never slowed down. So what is going on?" | 18.5 s |
| 2 | Opening card | 0:18 | Wheel mark, ENGINEERING PHENOMENA · 02, **Aliasing**, tagline, colour strip. | "Why wheels spin backwards on video" | 6.5 s |
| 3 | Snapshots | 0:24 | SEE IT. The wheel and a camera. A film strip of stills, 30 ticks in one second, the empty gap between two pictures, then the brain linking each spoke to the closest spoke in the next picture. | "A video is not smooth motion." / "It is a flip book: 30 still pictures every second." / "Between two pictures, the camera sees nothing at all." / "Your brain joins the pictures together..." / "...by linking each spoke to the closest spoke in the next picture." | 24.5 s |
| 4 | The trick | 0:48 | One big wheel, one spoke painted yellow, pictures shown one per second (×30 slow). 15° per picture: forwards, correct. 66° per picture: each spoke lands 6° short of where the next one was, the closest match is backwards; then the same at real speed, and the painted spoke fades so all spokes look alike. 72° per picture: every picture identical, frozen. | "Let's slow it right down, and paint one spoke yellow." / "A small turn between pictures: it looks like it turns forwards. Correct!" / "Now it turns almost one spoke gap between pictures." / "Every spoke lands just short of where the next one was..." / "...so the closest match is backwards. The wheel seems to turn backwards!" / "Turn exactly one gap per picture, and every picture looks the same." / "The wheel seems frozen, even though it is spinning fast." | 38.5 s |
| 5 | The rule | 1:26 | UNDERSTAND IT. Graph of frequency seen versus real spoke frequency: the true diagonal, the sawtooth of the alias, the green zone below the Nyquist limit (15 Hz), frozen points at 30 and 60 Hz. A live marker sweeps while a wheel beside it spins at the matching real rate. *f* = *N*·*f*<sub>r</sub>, *f*<sub>a</sub> = *f* − *f*<sub>s</sub>·round(*f*/*f*<sub>s</sub>), *f*<sub>s</sub> > 2·*f*<sub>max</sub>. | "Engineers call this aliasing: a fast motion that shows up under a false name, an alias." / "The camera takes 30 pictures per second. The spokes pass by f times per second." / "Up to 15 per second, the video tells the truth. Faster than that, the motion is disguised." / "At exactly 30 or 60 per second the wheel looks frozen. Just below, it looks backwards." / "The rule: take samples more than twice as fast as the fastest change you want to see." / "Engineers call it the Nyquist-Shannon sampling theorem." | 40.5 s |
| 6 | Real world 1 | 2:06 | IN THE REAL WORLD. Helicopter seen from above, its 5-blade rotor frozen on video (really spinning at 6 turns per second). Then a lathe chuck: a blur in steady light, apparently still under light flickering 100 times per second (simulated view), with a warning. | "Helicopter blades can look frozen on video." / "Between two pictures, each blade moves exactly into the next blade's place." / "Flickering lights can play the same trick on machines." / "A spinning lathe can look stopped. That is why workshop lights must not flicker." | 22.5 s |
| 7 | Real world 2 | 2:28 | A vibration sensor on a motor: a 900 Hz signal, samples every millisecond, the false 100 Hz wave the samples trace. The fix: sensor, anti-aliasing filter, converter, controller. Then a strobe light freezing a fan for inspection. | "Machines sample the world too: their sensors are read many times per second." / "A 900 Hz vibration read 1000 times per second looks like a slow 100 Hz wave." / "So engineers filter out what is too fast, then sample more than twice as fast." / "And a strobe light uses aliasing on purpose, to freeze fast machines for inspection." | 22.5 s |
| 8 | Takeaway | 2:50 | Closing card on ink. | "Take pictures too slowly, and fast things can look slow, stopped, or even backwards." *f*<sub>s</sub> > 2·*f*<sub>max</sub> | 10 s |

Neighbouring scenes cross-fade over 0.5 s.

## Status checklist

- [x] Explanation written (both layers)
- [ ] Explanation fact-checked
- [x] Storyboard done
- [x] Code engine built (replaces the Blender scene for this piece)
- [ ] Scenes built
- [ ] Renders done
- [ ] Edit and sound done
- [ ] Subtitles: EN / FR / AR
- [ ] Finals exported to `video/` and `renders/`
- [ ] Main README status updated

## Sources

1. C. E. Shannon, "Communication in the presence of noise", *Proceedings of the IRE*, 37(1), 1949.
2. A. V. Oppenheim and R. W. Schafer, *Discrete-Time Signal Processing*, Pearson (sampling, aliasing, anti-aliasing filters).
3. D. Purves, J. A. Paydarfar and T. J. Andrews, "The wagon wheel illusion in movies and reality", *PNAS*, 93(8), 1996.
4. J. S. Kline, A. O. Holcombe and D. M. Eagleman, "Illusory motion reversal is caused by rivalry, not by perceptual snapshots of the visual field", *Vision Research*, 44(23), 2004.
5. Health and Safety Executive, *Lighting at work* (HSG38).
6. IEEE Std 1789-2015, recommended practices for modulating current in high-brightness LEDs (flicker and stroboscopic effects).
7. W3C, WCAG 2.2, success criterion 2.3.1 "Three flashes or below threshold".

## Files

| Folder | Contents |
|---|---|
| `code/` | The program that draws every frame, the scenes, the sound and the subtitle tools. How to render: `code/README.md` |
| `renders/` | `02-aliasing_hero.png`, `02-aliasing_thumb.png` |
| `video/` | `02-aliasing_16x9_en.mp4`, `02-aliasing_16x9_fr.mp4`, `02-aliasing_16x9_ar.mp4` |
| `subtitles/` | `02-aliasing_en.srt`, `02-aliasing_fr.srt`, `02-aliasing_ar.srt` |
| `sources/` | References and notes |
