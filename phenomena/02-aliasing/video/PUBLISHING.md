# Publishing kit - 02 · Aliasing

Everything needed to upload the finals. Upload the language version that matches the channel or post, and add the other two subtitle files from `../subtitles/` as extra caption tracks.

## Files

| File | Use |
|---|---|
| `02-aliasing_16x9_en.mp4` | Full video, English on screen (YouTube, presentations) |
| `02-aliasing_16x9_fr.mp4` | Full video, French on screen |
| `02-aliasing_16x9_ar.mp4` | Full video, Arabic on screen |
| `02-aliasing_9x16_en.mp4` (and `_fr`, `_ar`) | Short: YouTube Shorts, Reels, TikTok |
| `../renders/02-aliasing_thumb.png` | YouTube thumbnail (1280 × 720) |
| `../renders/02-aliasing_hero.png` | Poster, post image (3840 × 2160) |
| `../subtitles/02-aliasing_en.srt` (and `_fr`, `_ar`) | Subtitles of the full video |
| `../subtitles/02-aliasing_9x16_en.srt` (and `_fr`, `_ar`) | Subtitles of the Short |

Technical: H.264 High profile, 30 fps, BT.709 (film 1920 × 1080, Short 1080 × 1920), AAC 320 kbit/s 48 kHz. Measured on the final files: −14.0 LUFS integrated, true peak −1.5 dBTP (the streaming target).

## Title

**Why do wheels seem to spin backwards on video? | Aliasing | Engineering Phenomena 02**

## Description

A car speeds up, but on video its wheels seem to slow down, stop, and even turn backwards. Nothing is wrong with the car: a video is a flip book of 30 still pictures per second, and a wheel that turns almost one spoke gap between two pictures fools your brain. Engineers call this aliasing.

In this film:
- why the wagon-wheel effect happens, shown for real on your own screen (every frame is drawn by code from the equations)
- the rule every engineer uses: sample more than twice as fast as the fastest change (the Nyquist-Shannon sampling theorem)
- frozen helicopter blades, the stroboscopic danger in workshops, sensors inside machines, and strobe lights used on purpose

Chapters:
0:00 The car speeds up, the wheel seems to go backwards
0:18 Aliasing
0:24 A video is a flip book
0:48 The trick
1:26 The rule: Nyquist-Shannon
2:06 Helicopters and lathes
2:28 Sensors and strobe lights
2:50 The takeaway

Sources: see the list in the repository (`phenomena/02-aliasing/sources/`).

Engineering Phenomena: see it, understand it. Made entirely with code: no filmed footage, no stock images, every motion computed from the physics.

## Short (9:16)

**Why do wheels seem to spin backwards on video? #engineering #physics**

A car speeds up, yet its wheel seems to go backwards. The answer takes 45 seconds.

## Accessibility note

The film contains no flashing: flicker and strobe lights are shown as icons and graphs only. It passed an automatic photosensitivity screen (see `../code/qa/flash_check.py`).
