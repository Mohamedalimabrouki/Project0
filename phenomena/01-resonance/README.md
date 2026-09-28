# 01 · Resonance

> **Push something at its favourite rhythm, and tiny pushes make huge movements.**

| Field | Status | Formats planned |
|---|---|---|
| Vibrations | Script written, storyboard drafted, art not started | Full 16:9, Short 9:16, Hero still |

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
```

**Why it happens, in one line:** at resonance the force is in phase with the velocity, so every push adds energy, and only damping takes it away.

**Assumptions**
- Linear spring and linear (viscous) damping.
- Steady state: we look at the motion after the start-up transient has died out.
- Single degree of freedom. Real structures have many modes; each one behaves like this near its own natural frequency.

**Typical values** (orders of magnitude)

| System | Damping ratio ζ | Amplification at resonance 1/(2ζ) |
|---|---|---|
| Very lightly damped structure | 0.01 | 50 |
| Typical building structure | 0.02 to 0.05 | 10 to 25 |
| Car suspension | 0.2 to 0.4 | about 1.3 to 2.5 |

Playground swing with 2 m chains: natural period T = 2π·√(L/g) ≈ 2.8 s.

**Real-world cases**
- **London Millennium Bridge (2000):** it swayed sideways on opening day and closed after two days. Walkers push sideways about once per second, close to one of the bridge's sway frequencies; as it swayed, people unconsciously fell into step with it and pushed even more in sync. Dampers were added and it reopened in 2002. [Source 3]
- **Taipei 101:** a steel sphere of about 660 tonnes hangs near the top as a tuned mass damper, reducing wind-driven sway. [Source to add]
- **Washing machine:** it shakes hard for a few seconds while the drum speeds up through the machine's natural frequency, then calms down at full speed. Great kids example.

## Accuracy notes

- **Pushed swing, not pumped swing.** We show someone else pushing the swing (forced oscillation). A child pumping the swing by moving their legs is a different mechanism (parametric oscillation). Do not mix the two.
- **The swing is only a hook.** A pendulum is linear only for small angles, so the explanation switches to the mass-spring model in scene 2.
- **Myth to avoid: Tacoma Narrows (1940).** It is often shown as "resonance". It was aeroelastic flutter: the wind fed energy into the deck through the deck's own motion, not through a periodic push at a matching frequency. Do not use it as a resonance example. It deserves its own piece. [Source 2]
- **Myth to soften: a singer breaking a glass.** It is possible, but it needs a very loud sound held exactly at the glass's frequency. Do not suggest that a normal voice breaks glasses.
- **Honest graphs.** The amplitude curves in scenes 3 and 4 use real ratios. If the moving object's motion is exaggerated to stay readable, show "motion exaggerated xN" on screen.

## Storyboard (draft)

| # | Scene | What we see | What is said (voice or text) | Duration |
|---|---|---|---|---|
| 1 | Hook | Split screen, two identical swings. Same tiny push (vermillion arrow). Left: pushed every 2.8 s, in rhythm. Right: pushed at random times. Left one climbs higher and higher, right one stays small. | "Same push. Different timing." | 15 s |
| 2 | The model | The swing morphs into a steel mass on a spring. Force arrow (vermillion) and motion arrow (blue). The mass bounces on its own at its natural rhythm, a metronome ticks along. | "Everything that can wiggle has its own natural rhythm." ωn = √(k/m) appears. | 25 s |
| 3 | The sweep | We push the mass slowly, then faster and faster. Beside it, a graph draws itself live: amplitude vs push frequency. A sharp peak rises where the push rhythm matches the natural rhythm (yellow highlight on the peak). | "Match the rhythm, and the motion explodes." | 35 s |
| 4 | Damping | Same sweep, three curves for ζ = 0.05, 0.1 and 0.3. The peak drops and widens as damping grows. | "Damping is the engineer's brake on resonance." Amplification 1/(2ζ) appears. | 25 s |
| 5 | Real world | Millennium Bridge swaying, then dampers highlighted (bluish green). Cut to Taipei 101 and its giant sphere swinging against the building's motion. | "Engineers do not avoid resonance by luck. They design for it." | 35 s |
| 6 | Takeaway | Closing card on ink background. | "Push something at its favourite rhythm, and tiny pushes make huge movements." | 10 s |

Total about 2 min 25 s.

**Short version (9:16, about 45 s):** scene 1, scene 3 without the equation, washing machine instead of scene 5, scene 6.

## Status checklist

- [x] Explanation written (both layers)
- [ ] Explanation fact-checked
- [ ] Storyboard done (draft above)
- [ ] Blender scene built
- [ ] Renders done
- [ ] Edit and sound done
- [ ] Subtitles: EN / FR / AR
- [ ] Finals exported to `video/` and `renders/`
- [ ] Main README status updated

## Sources

1. S. S. Rao, *Mechanical Vibrations*, Pearson (any recent edition). Chapter on harmonically excited vibration.
2. K. Y. Billah and R. H. Scanlan, "Resonance, Tacoma Narrows bridge failure, and undergraduate physics textbooks", *American Journal of Physics*, 59(2), 1991.
3. P. Dallard et al., "The London Millennium Footbridge", *The Structural Engineer*, 79(22), 2001.
4. Taipei 101 tuned mass damper: official or engineering reference still to add.

## Files

| Folder | Contents |
|---|---|
| `blender/` | `01-resonance_v001.blend`, `v002`... |
| `renders/` | `01-resonance_hero.png`, `01-resonance_thumb.png` |
| `video/` | `01-resonance_16x9_en.mp4`, `01-resonance_9x16_en.mp4` |
| `subtitles/` | `01-resonance_en.srt`, `01-resonance_fr.srt`, `01-resonance_ar.srt` |
| `sources/` | References, sketches |
