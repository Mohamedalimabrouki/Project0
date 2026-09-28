# 01 · Resonance

> **Push something at its favourite rhythm, and tiny pushes make huge movements.**

| Field | Status | Formats planned |
|---|---|---|
| Vibrations | Video v1 in production (16:9, 2 min 58 s): everything built, final 3D renders running | Full 16:9, Short 9:16, Hero still |

**Watch:** [`video/01-resonance_16x9_en.mp4`](video/01-resonance_16x9_en.mp4). The file has three subtitle tracks (English, French, Arabic) that you can switch on in any player; the same subtitles are also in [`subtitles/`](subtitles/) as `.srt` files for YouTube, and [`video/01-resonance_youtube.txt`](video/01-resonance_youtube.txt) is a ready-to-paste description with chapters.

> The video and the Blender files are big files, stored with Git LFS. This version was made in a cloud session that could not reach GitHub's LFS server, so they were delivered directly instead: see [Adding the big files](#adding-the-big-files).

---

## See it (kids layer)

When you push a swing at just the right moments, small pushes add up and the swing goes higher and higher. Everything that can wiggle, from a swing to a bridge, has its own favourite rhythm. Push it at that rhythm and a tiny force can make a huge movement: that is resonance.

## Understand it (engineers layer)

**Governing equation** (forced, damped, single degree of freedom oscillator)

```
m·x'' + c·x' + k·x = F0·cos(ω·t)
```

| Symbol | Meaning | Unit |
|---|---|---|
| *m* | Mass | kg |
| *c* | Damping coefficient | N·s/m |
| *k* | Stiffness | N/m |
| *F0* | Amplitude of the driving force | N |
| *ω* | Driving angular frequency | rad/s |
| *x* | Displacement | m |

**Key quantities**

```
Natural frequency     ωn = √(k/m)
Damping ratio         ζ  = c / (2·√(k·m))
Frequency ratio       r  = ω / ωn

Steady-state amplitude
    X = (F0/k) / √( (1 - r²)² + (2·ζ·r)² )

At r = 1:  X = (F0/k) / (2·ζ)      → amplification factor 1/(2ζ)
Peak at r = √(1 - 2ζ²)  (exists only if ζ < 1/√2),  peak value 1 / (2ζ·√(1 - ζ²))
Phase lag of the motion behind the push:  φ = atan2(2ζr, 1 - r²)   (0° slow, 90° at r = 1, 180° fast)
```

**Why it happens, in one line:** at resonance the motion lags the push by 90°, so the force is in phase with the velocity: the power *P = F·v* is never negative, every push adds energy, and only damping takes it away.

**The model in the video uses real, buildable numbers** (see `scripts/physics.py`)

| Quantity | Value | Where it comes from |
|---|---|---|
| Mass *m* | 2 kg | a 63.4 mm steel cube (7850 kg/m³) |
| Stiffness *k* | 79 N/m | spring of 1.5 mm wire, 30 mm coil diameter, about 23 coils |
| Natural frequency | exactly 1 Hz | *ωn* = √(*k*/*m*) = 2π rad/s |
| Damping ratio *ζ* | 5 % | *c* = 1.26 N·s/m |
| Push *F0* | 0.5 N | static stretch *F0/k* = 6.3 mm |
| Motion at resonance | ±63 mm | 10 × 6.3 mm, drawn to scale on screen |

**Assumptions**
- Linear spring and linear (viscous) damping.
- Steady state: the sweep shows the motion after the start-up transient has died out, at each push rhythm (a sped-up "stepped-sine" test). This is written on screen.
- Single degree of freedom. Real structures have many modes; each one behaves like this near its own natural frequency.

**Typical values** (orders of magnitude)

| System | Damping ratio ζ | Amplification at resonance 1/(2ζ) |
|---|---|---|
| Very lightly damped structure | 0.01 | 50 |
| Typical building structure (tall buildings in wind: 1 to 2 %) | 0.01 to 0.05 | 10 to 50 |
| Car suspension | 0.2 to 0.4 | about 1.3 to 2.5 |

Playground swing with 2 m chains: natural period T = 2π·√(L/g) ≈ 2.84 s (ideal pendulum, small swings; big swings are a little slower: +1.7 % at 30°). [Sources 1, 15]

**Real-world cases**

- **London Millennium Bridge (2000).** Opened to the public on 10 June 2000 and closed on 12 June 2000 because of sideways sway: up to about 70 mm on the centre span and 50 mm on the south span, with accelerations of 0.20 to 0.25 g [3, 4]. Walkers push the deck sideways once per stride, at about half their step rate (about 0.9 to 1 Hz) [17], which is close to several of the bridge's sideways modes (south span about 0.8 Hz, centre span 2nd mode about 0.95 Hz, north span about 1.0 Hz; the centre span's 1st mode is lower, about 0.5 Hz) [3, 8]. Once the deck moves, walkers shift their feet to keep their balance, and on average part of their sideways force is in step with the deck's velocity: the crowd acts as a **negative damper** (Arup measured about 300 N·s/m per person) [3]. In Arup's crowd test of December 2000 on the north span, 156 walkers caused no visible sway, while 166 caused sudden large sway [9]. Arup called it "synchronous lateral excitation"; later research shows that the balance behaviour alone is enough, and that walkers falling into step is a result of large sway, not its cause [5, 6]. The retrofit added **37 fluid-viscous dampers** (mostly against sideways sway) and **about 60 tuned mass dampers** (52 against vertical motion, 8 sideways), raising sideways damping from about 0.5 % to about 20 %; the bridge reopened on **22 February 2002** [7, 8, 10].
- **Taipei 101 (508 m, 2004).** A **660 t** steel sphere, **5.5 m** wide, made of **41 steel plates of 125 mm**, hangs from the 92nd floor between floors 87 and 92, on **8 cables**, with **8 hydraulic viscous dampers** underneath and a bumper ring that limits its travel to 1.5 m [11, 12]. The tower's first sway mode is about 0.15 Hz (a period of about 6.8 s), and the ball's own swing is tuned to it, which means an effective pendulum length of about 11.5 m (the cables themselves are longer) [13]. The operator quotes up to about **40 % less sway** [11]. The largest recorded swing is **1 m**, during Typhoon Soudelor on 8 August 2015 [16]. It is designed for comfort in wind, not for earthquakes.
- **Why a tuned mass damper works (the phase):** tuned with Den Hartog's rules [15] (for a 1.25 % mass ratio [14]: tuning 0.988, damper ratio 6.7 %), at the tower's own rhythm the ball swings about a **quarter of a cycle (90°) behind** the tower. Its pull on the tower then points against the tower's velocity, so it acts like a brake, and its own dampers turn the energy into heat. Our model in `scripts/physics.py` gives a lag of 93°.
- **Washing machine:** it shakes hard for a few seconds while the drum speeds up through the machine's natural frequency, then calms down at full speed. Great kids example (kept for the Short).

## Accuracy notes

- **Pushed swing, not pumped swing.** We show pushes from outside (forced oscillation). A child pumping the swing with their legs is a different mechanism (parametric oscillation).
- **Same pushes, honest comparison.** Both swings get the same 7 pushes of the same size; only the timing differs. The random timing shown is **not cherry-picked**: `physics.py` runs 1000 random trials and shows the one whose final swing is the median (about 17°, against 38° in rhythm). The energy chips under each trace show the work done by each push (some random pushes remove energy).
- **The swing is only a hook.** A pendulum is linear only for small angles, so the explanation switches to the mass-spring model. The swing motion itself is the full nonlinear pendulum.
- **Steady state in the sweep.** The motion shown at each push rhythm is the steady-state solution, and the screen says so. In a real fast sweep, the amplitude would lag behind.
- **Labelled exaggerations:** slowed down ×4 (the key idea at resonance), bridge sway ×5 (real: up to about 70 mm), Taipei 101 sway ×100 and "diagram not to scale". The mass-spring motion is **drawn to scale**.
- **Myth avoided: Tacoma Narrows (1940).** It was aeroelastic flutter (self-excited, negative aerodynamic damping), not a periodic push at a matching frequency [2]. Not used as a resonance example.
- **Myth avoided: "people marched in step".** The Millennium Bridge wording follows both published explanations (see above).
- **Myth avoided: "the ball swings opposite to the building".** It lags about a quarter cycle (90°); 180° only happens for an undamped absorber at one frequency.
- **Not claimed:** that the Taipei 101 damper saved the tower in an earthquake, or that it is the world's largest (the Shanghai Tower's 1000 t damper is heavier).
- **Myth to soften: a singer breaking a glass.** Possible, but it needs a very loud sound held exactly at the glass's frequency. Not in this video.

## Storyboard (as made)

| # | Time | Scene | What we see | What is said |
|---|---|---|---|---|
| 0 | 0:00 | Ident | Series name, episode 01, the colour bar | (music) |
| 1 | 0:02 | Hook (3D) | Two swings, split screen. Identical pushes (vermillion *F*). Live traces of the angle, push ticks and the energy each push added. "Highest swing 38° / 18°". | "Two identical swings... Same push. Different timing. A very different result." |
| 2 | 0:21 | Title | The swings blur away, "Resonance", the resonance curve draws itself | "This is resonance." |
| 3 | 0:25 | Natural rhythm (3D) | One swing is pulled back and let go. *L* = 2 m, period brackets 2.86 s, *T* = 2π√(*L*/*g*) | "Anything that can wiggle has a natural rhythm..." |
| 4 | 0:37 | The model (3D to 2D) | The steel mass on a spring with its damper, real scale; the render turns into the engineering drawing; three rigs at 1 Hz, 2 Hz (4*k*) and 0.5 Hz (4*m*); ωn = √(*k*/*m*) | "Engineers study this... A stiffer spring makes it faster. A heavier mass makes it slower." |
| 5 | 0:51 | The sweep | The push rhythm rises from 0.2 to 2 × natural; the resonance curve draws live; ×10 at the peak; slow motion shows *F* and *v* in step; the power *F·v* never goes negative | "Now let's push it... every push goes the same way the mass is already moving. So every push adds energy." |
| 6 | 1:23 | Damping | The damper glows (heat); curves for ζ = 5 %, 10 %, 30 % (×10, ×5, ×1.7), peak ≈ 1/(2ζ) | "Damping sets the height of the peak..." |
| 7 | 1:50 | Millennium Bridge | London skyline, crowds; cross-section with walkers' sideways steps; the sway grows; CLOSED; 37 dampers light up (bluish green); reopened 2002 | "London, June 2000..." |
| 8 | 2:24 | Taipei 101 (2D, 3D, 2D) | The tower draws itself (508 m); the 660 t ball in 3D; the ¼-beat diagram: tower and ball waves, *F* against *v* | "Taipei 101 goes one step further... Resonance, used to fight resonance." |
| 9 | 2:47 | Takeaway | The closing sentence, the curve, the signature | "Push something at its favourite rhythm, and tiny pushes make huge movements." |

The full narration (with French and Arabic) is in [`scripts/script.py`](scripts/script.py).

**Short version (9:16, about 45 s), still to make:** scene 1, scene 5 without the equation, washing machine instead of scenes 7 and 8, scene 9.

## How this video is made (and how to change it)

Everything is made by scripts, so every part can be changed and rebuilt. Nothing is animated by eye: every motion comes from the equations in `physics.py`.

| Step | Script (in `scripts/`) | What it does |
|---|---|---|
| Words | `script.py` | The narration in English, French and Arabic, line by line |
| Voice | `narration.py` | Reads the English lines with the Kokoro voice engine (runs offline) |
| Timing | `timeline.py` | Places every line and every scene on the timeline, from the voice lengths |
| Physics | `physics.py` | The swings, the spring, the sweep, the damping curves, the Taipei 101 damper |
| 3D | `blender_swings.py`, `blender_spring.py`, `blender_taipei.py` | Build the Blender scenes, keyframe them from the physics, render with Cycles |
| 2D | `sc_opening.py`, `sc_model.py`, `sc_bridge.py`, `sc_taipei.py`, `render_video.py` | Draw the graphics on top of the renders and assemble the picture |
| Music | `make_music.py` | The original score, rendered with FluidSynth and the MuseScore General soundfont |
| Sound | `make_audio.py` | Sound effects (all synthesised), the mix, loudness -14 LUFS |
| Subtitles | `make_subtitles.py` | The `.srt` files in English, French and Arabic |
| Final | `make_final.py` | The MP4: picture, sound, 3 subtitle tracks |

`build.sh` runs them in order. The Blender files in `blender/` open in Blender 5.0 like any other scene: the keyframes are already in them, so you can re-render them on your own computer (with your graphics card this is much faster), change the lights or the camera, or render the 4K hero still.

**To use your own voice:** record each line of `script.py` as a WAV file named like the line (`L01.wav`, `L02.wav`...), put them in `build/audio/narration/` (replacing the synthetic ones), then run `build.sh` again: the timeline is recomputed from the lengths of your recordings, so the pictures follow your voice automatically.

**Tools needed:** Python 3.11, `pip install bpy==5.0.1 skia-python uharfbuzz svgelements scipy numpy pillow soundfile mido pyloudnorm`, plus `kokoro-onnx==0.6.1` in its own environment, and from the system: ffmpeg, TeX Live (`latex`, `dvisvgm`), FluidSynth and the MuseScore General soundfont. The 2D engine is in [`tools/epmotion/`](../../tools/epmotion/).

## Adding the big files

Copy `01-resonance_16x9_en.mp4` into `video/` and the four `.blend` files into `blender/`, then commit and push with GitHub Desktop: it sends them through Git LFS automatically (the list of LFS file types is in `.gitattributes`). You can also rebuild them from scratch with `scripts/build.sh`.

## Status checklist

- [x] Explanation written (both layers)
- [x] Explanation fact-checked (sources below; figures corrected where needed)
- [x] Storyboard done (as made, above)
- [x] Blender scene built (`blender/`: swings, single swing, mass-spring, Taipei 101 damper)
- [ ] Renders done (Cycles, 1920 × 1080, 30 fps): running
- [x] Edit and sound done (original music, synthesised effects, -14 LUFS)
- [x] Subtitles: EN / FR / AR (Arabic draft: have a native speaker read it before publishing)
- [ ] Finals exported to `video/` and `renders/`
- [x] Main README status updated

## Sources

1. S. S. Rao, *Mechanical Vibrations*, Pearson (any recent edition). Chapter on harmonically excited vibration.
2. K. Y. Billah and R. H. Scanlan, "Resonance, Tacoma Narrows bridge failure, and undergraduate physics textbooks", *American Journal of Physics*, 59(2), 118-124, 1991. doi:10.1119/1.16590
3. P. Dallard et al., "The London Millennium Footbridge", *The Structural Engineer*, 79(22), 17-33, 2001.
4. P. Dallard et al., "London Millennium Bridge: Pedestrian-Induced Lateral Vibration", *Journal of Bridge Engineering*, 6(6), 412-417, 2001.
5. J. H. G. Macdonald, "Lateral excitation of bridges by balancing pedestrians", *Proc. R. Soc. A*, 465, 1055-1073, 2009. doi:10.1098/rspa.2008.0367
6. I. Belykh et al., "Emergence of the London Millennium Bridge instability without synchronisation", *Nature Communications*, 12, 7223, 2021. doi:10.1038/s41467-021-27568-y
7. D. P. Taylor, "Damper retrofit of the London Millennium Footbridge: a case study in biodynamic design", 73rd Shock and Vibration Symposium, 2002. https://www.taylordevices.com/wp-content/uploads/66-Damper-Retrofit-of-London.pdf
8. D. E. Newland, "Vibration of the London Millennium Bridge: cause and cure", *International Journal of Acoustics and Vibration*, 8(1), 2003.
9. New Civil Engineer, "All large footbridges face Millennium Bridge sway problem", 15 February 2001. https://www.newcivilengineer.com/archive/all-large-footbridges-face-millennium-bridge-sway-problem-15-02-2001/
10. City Bridge Foundation, "It's 25 up for London's iconic Millennium Bridge". https://www.citybridgefoundation.org.uk/news-and-blog/its-25-up-for-londons-iconic-millennium-bridge
11. Taipei 101, official damper page. https://www.taipei-101.com.tw/en/observatory/feature/damper
12. D. Poon, S.-S. Shieh, L. M. Joseph, C.-C. Chang, "Structural Design of Taipei 101, the World's Tallest Building", CTBUH 2004 Seoul Conference, 271-278. https://global.ctbuh.org/resources/papers/1650-Poon_2004_StructuralDesignTaipei.pdf
13. K.-C. Chen et al., *Earth, Planets and Space*, 64, 1277-1286, 2012 (measured sway frequency about 0.15 Hz). doi:10.5047/eps.2012.04.004
14. L.-L. Chung et al., "Semi-active tuned mass dampers with phase control", *Journal of Sound and Vibration*, 332(15), 3610-3625, 2013.
15. J. P. Den Hartog, *Mechanical Vibrations*, 4th ed., McGraw-Hill, 1956 (Dover reprint 1985), chapter 3.
16. Taiwan News, 1 November 2024 (Typhoon Soudelor record, 100 cm). https://www.taiwannews.com.tw/news/5963038
17. A. Pachi and T. Ji, "Frequency and velocity of people walking", *The Structural Engineer*, 83(3), 2005.

**Credits for the tools inside the video:** voice by Kokoro-82M (Apache 2.0 licence, voice "af_heart"), music played with the MuseScore General soundfont (MIT licence), fonts Inter (SIL Open Font Licence) and Computer Modern (TeX), 3D in Blender 5.0 (Cycles). All pictures, music and code are original.

## Files

| Folder | Contents |
|---|---|
| `blender/` | `01-resonance_swings_v001.blend`, `01-resonance_swing_rhythm_v001.blend`, `01-resonance_spring_v001.blend`, `01-resonance_taipei_damper_v001.blend` |
| `video/` | `01-resonance_16x9_en.mp4` (1920 × 1080, 30 fps, H.264, AAC, subtitles EN / FR / AR) |
| `subtitles/` | `01-resonance_en.srt`, `01-resonance_fr.srt`, `01-resonance_ar.srt` |
| `scripts/` | Everything that builds the video (see the table above) |
| `renders/` | Hero still and thumbnail (to do) |
| `sources/` | References (links above) |
