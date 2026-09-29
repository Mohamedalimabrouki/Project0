# Recording the narration - 02 · Aliasing

The film is finished and works without a voice. A narrator makes it warmer and far more professional, and it has to be **a real person**: a synthetic (AI) voice is the first thing viewers notice as "made by AI". Everything after the recording is automatic: cleaning, timing, the music dipping under the voice, subtitles and the final videos.

The script to read is [`SCRIPT.md`](SCRIPT.md): 34 short lines in English, French and Arabic, with notes on tone and on how to say the numbers. About 2 minutes 30 of speech per language, so plan 30 to 45 minutes per language with retakes and breaks.

**Who reads:** the same person for all three languages gives the channel one recognisable voice. If one language is not comfortable, a native speaker for that language is better than a strong accent.

## Before you start

- **Room:** small and soft. A bedroom with curtains, a bed and a full wardrobe is ideal. Avoid kitchens, bathrooms and empty rooms (they echo). Switch off fans and air conditioning; move away from the fridge.
- **Microphone:** a phone is fine. A USB microphone or a clip-on (lavalier) microphone is better.
  - iPhone: Voice Memos, with *Settings > Voice Memos > Audio Quality > Lossless*.
  - Android: a recorder app set to its highest quality (WAV if it offers it).
  - Computer: Audacity (free), 48000 Hz, mono, export as WAV.
- **Phone in flight mode**, so no call or buzz can interrupt a take.
- **Position:** the microphone a hand-span from your mouth (15 to 20 cm), a little to the side rather than straight in front (this avoids pops on "p" and "b"). Keep that distance all the way through. Do not touch the phone or the table while recording.
- **Test:** record 10 seconds, listen on headphones. No hiss, no echo, no distortion? Then go.

## Recording (one file per language)

1. Start recording, then stay silent for **5 seconds** (the tool learns the sound of the room from it).
2. Read the lines of `SCRIPT.md` **in order, 1 to 34**, each once, with a pause of about **3 seconds** between lines (count to three in your head).
3. **A slip?** Stop, wait a moment, and read the whole line again. Do not delete anything: the last take of each line is used automatically.
4. **Timing:** each line shows *Aim for* (its time in the film). Speak naturally; a small overrun is fine, the finishing step handles it.
5. At the end, stay silent for 3 seconds and stop.
6. Name the files `en`, `fr` and `ar` (for example `en.m4a`).

Line 34 is the last line again, only for the 45-second Short: a little quicker (in Arabic it is a shorter sentence).

## How to sound

- Talk to **one curious person** sitting in front of you, not to an audience. Warm, clear, unhurried.
- A light smile on the light lines; slow down on the key lines (the notes say which words to lean on).
- Full stops are real stops. Lines 10 and 15 run on into the next line: keep your voice up at their end.
- Arabic: Modern Standard Arabic, numbers as the notes write them.
- Water nearby; no milk or coffee just before; a short break between languages.

## Then

Send the three files in the chat with Claude and say "voice uploaded" (or put them in `voice/raw/` as `en.m4a`, `fr.m4a`, `ar.m4a`). One command makes, for each language:

| File | What it is |
|---|---|
| `video/02-aliasing_16x9_<lang>_narrated.mp4` | The full film with your voice. No burned-in captions (the voice says them): subtitles come as a separate file, as on any professional film. |
| `video/02-aliasing_9x16_<lang>_narrated.mp4` | The Short with your voice, captions kept (people often watch Shorts without sound). |
| `subtitles/02-aliasing_narrated_<lang>.srt`, `subtitles/02-aliasing_9x16_narrated_<lang>.srt` | Subtitles timed to your real voice. |

The music-only versions stay exactly as they are. The report at the end lists any line worth re-recording a little faster (usually none).

For the technical side (what the finishing step does and how to run it), see [`../code/README.md`](../code/README.md#the-narrated-version).
