"""The score: which chord plays when, and every note of every instrument.

Tempo 120 beats per minute, four beats to the bar: one beat = 0.5 s, one bar = 2.0 s, one
sixteenth note = 0.125 s. Scenes start on bar lines (0, 18, 24, 48, 86, 126, 148, 170 s).
Home key: D minor, with its relative F major (the film moves between the two).

The story told by the harmony (read it as a map of the film):
  hook     Dm - Bb - F, then a suspended chord (F G C) while the wheel freezes, then Bb - C
           climbing (an unresolved "dominant" chord) into the title
  title    F major: the warm "answer", then Dm - Bb - C leading back to calm
  explain  Dm - Bb - F - C looped slowly, two bars per chord (steady, curious, low density)
  rule     the same loop with brighter chords (major sevenths, ninths), a firmer rhythm, and the
           big resolution C -> F exactly at 115 s when the rule appears
  world    F - C - Dm - Bb, warmer and wider, electric piano and a little more groove
  outro    Bb - C - Dm: the closing cadence lands on the tonic (D minor) at 174 s

Pulse pattern: five notes repeated on the eighth-note grid (root, third, fifth, octave, fifth),
one note per spoke of the wheel. Five against eight makes the pattern slide against the bar,
a musical cousin of the wagon-wheel effect, while every single note stays exactly on the grid.
"""
from __future__ import annotations

import numpy as np

from instruments import Bend

BAR = 2.0
BEAT = 0.5
E8 = 0.25
S16 = 0.125
FILM = 180.0


def note(name):
    """'C#4' -> MIDI number (C4 = 60, A4 = 69 = 440 Hz)."""
    pcs = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    s = 0
    n = name[0]
    i = 1
    while i < len(name) and name[i] in "#b":
        s += 1 if name[i] == "#" else -1
        i += 1
    return 12 * (int(name[i:]) + 1) + pcs[n] + s


# name: root pitch class, triad pitch classes, bass note, pad voicing (4 notes), pluck pool
# (5 notes, ascending), electric-piano dyad
CH = {
    "Dm":     dict(root=2,  pcs=(2, 5, 9),  bass=38, pad=(57, 62, 65, 69), pool=(62, 65, 69, 74, 77), keys=(65, 69)),
    "Dm7":    dict(root=2,  pcs=(2, 5, 9),  bass=38, pad=(57, 60, 65, 69), pool=(62, 65, 69, 72, 77), keys=(65, 72)),
    "Dm9":    dict(root=2,  pcs=(2, 5, 9),  bass=38, pad=(57, 60, 64, 69), pool=(62, 65, 69, 72, 76), keys=(64, 69)),
    "Dm9b":   dict(root=2,  pcs=(2, 5, 9),  bass=38, pad=(57, 60, 65, 76), pool=(62, 65, 69, 72, 76), keys=(65, 69)),
    "Bb":     dict(root=10, pcs=(10, 2, 5), bass=34, pad=(58, 62, 65, 70), pool=(58, 62, 65, 70, 74), keys=(65, 70)),
    "Bbmaj7": dict(root=10, pcs=(10, 2, 5), bass=34, pad=(58, 62, 65, 69), pool=(58, 62, 65, 69, 74), keys=(65, 69)),
    "F":      dict(root=5,  pcs=(5, 9, 0),  bass=41, pad=(57, 60, 65, 69), pool=(60, 65, 69, 72, 77), keys=(65, 72)),
    "Fmaj7":  dict(root=5,  pcs=(5, 9, 0),  bass=41, pad=(57, 60, 64, 69), pool=(60, 64, 69, 72, 77), keys=(64, 69)),
    "Fadd9":  dict(root=5,  pcs=(5, 9, 0),  bass=41, pad=(57, 60, 67, 69), pool=(60, 65, 69, 72, 79), keys=(67, 72)),
    "Fsus2":  dict(root=5,  pcs=(5, 7, 0),  bass=41, pad=(55, 60, 65, 67), pool=(60, 65, 67, 72, 77), keys=(67, 72)),
    "C":      dict(root=0,  pcs=(0, 4, 7),  bass=36, pad=(55, 60, 64, 67), pool=(60, 64, 67, 72, 76), keys=(64, 67)),
    "Csus4":  dict(root=0,  pcs=(0, 5, 7),  bass=36, pad=(55, 60, 65, 67), pool=(60, 65, 67, 72, 77), keys=(65, 67)),
    "Cadd9":  dict(root=0,  pcs=(0, 4, 7),  bass=36, pad=(55, 62, 64, 67), pool=(60, 64, 67, 72, 74), keys=(64, 67)),
    "Gm":     dict(root=7,  pcs=(7, 10, 2), bass=43, pad=(58, 62, 67, 70), pool=(58, 62, 67, 70, 74), keys=(62, 70)),
}

# the pulse: which pool note plays at each step of the five-step cycle, and its accent (dB)
CYCLE = (0, 1, 2, 3, 2)
ACCENT = (0.0, -3.5, -2.0, -1.0, -3.0)


class Score:
    def __init__(self):
        self.chord_segs = []          # (t0, t1, chord name)
        self.pad, self.bass, self.pluck, self.bell, self.keys = [], [], [], [], []
        self.kick, self.hat, self.rim, self.swell = [], [], [], []
        self.auto = {}                # name -> [(t, value)]
        self.marks = []               # (t, kind): every rhythmic onset, for the onset check
        self.bend = None
        self.scene_moods = {}

    # ------------------------------------------------------------------ harmony
    def chord(self, t0, t1, name):
        self.chord_segs.append((float(t0), float(t1), name))

    def chord_at(self, t):
        for a, b, n in self.chord_segs:
            if a - 1e-9 <= t < b - 1e-9:
                return n
        return self.chord_segs[-1][2] if t >= self.chord_segs[-1][1] else self.chord_segs[0][2]

    def tones(self, t, lo, hi):
        """MIDI notes in [lo, hi] that belong to the chord playing at time t (used by the SFX)."""
        pcs = CH[self.chord_at(t)]["pcs"]
        return [m for m in range(int(lo), int(hi) + 1) if m % 12 in pcs] or [int(lo)]

    def root_midi(self, t, lo, hi):
        r = CH[self.chord_at(t)]["root"]
        c = [m for m in range(int(lo), int(hi) + 1) if m % 12 == r]
        return c[0] if c else int(lo)

    # ---------------------------------------------------------------- automation
    def set(self, name, points):
        self.auto[name] = sorted(points)

    def lv(self, name, t):
        """Automation value (dB or Hz) at time t (linear interpolation of the breakpoints)."""
        pts = self.auto[name]
        return float(np.interp(t, [p[0] for p in pts], [p[1] for p in pts]))

    def lv_log(self, name, t):
        pts = self.auto[name]
        return float(np.exp(np.interp(t, [p[0] for p in pts], np.log([p[1] for p in pts]))))

    # --------------------------------------------------------------------- notes
    def add_pad(self, layer, voice, t0, t1, midi, db=0.0, att=0.9, rel=1.8):
        """One pad voice for one chord. Voices with the same pitch in the next chord carry on, the others
        glide (see instruments.pad_tracks)."""
        self.pad.append(dict(layer=layer, voice=int(voice), t0=float(t0), t1=float(t1), midi=int(midi), db=db, att=att, rel=rel))

    def harmony(self, segs, att=0.9, rel=1.8, air_db=None, air_from=None):
        """Register chords and give each one its pad voicing (four voices, plus three an octave up if asked)."""
        for a, b, n in segs:
            self.chord(a, b, n)
            for v, m in enumerate(CH[n]["pad"]):
                self.add_pad("main", v, a, b, m, 0.0, att, rel)
            if air_db is not None and a >= (air_from or 0.0):
                for v, m in enumerate(CH[n]["pad"][1:]):
                    self.add_pad("air", v, a, b, m + 12, air_db, att + 0.4, rel + 0.4)

    def bass_long(self, segs, db=0.0, sub=0.32, att=0.03, rel=0.12, bar_retrigger=True, gap=0.06):
        """One bass note per bar (and per chord change): steady, precise, breathing."""
        for a, b, n in segs:
            cur = a
            while cur < b - 1e-6:
                nxt = min(b, (np.floor(cur / BAR + 1e-9) + 1) * BAR) if bar_retrigger else b
                m = CH[n]["bass"]
                self.bass.append(dict(t0=cur, t1=nxt - gap, midi=m, db=db, att=att, rel=rel,
                                      sub=sub if m >= 36 else 0.0))
                self.marks.append((cur, "bass"))
                cur = nxt

    def bass_groove(self, t0, t1, db=0.0, sub=0.0, skip_bars=()):
        """Rhythmic bass: root, root, fifth on eighth-note steps 0, 3 and 5 of each bar."""
        b = t0
        while b < t1 - 1e-6:
            if round(b / BAR) not in skip_bars:
                n = self.chord_at(b)
                m = CH[n]["bass"]
                for off, dur, dm, dd in ((0.0, 0.70, 0, 0.0), (0.75, 0.43, 0, -3.0), (1.25, 0.70, 7, -1.5)):
                    self.bass.append(dict(t0=b + off, t1=b + off + dur, midi=m + dm, db=db + dd, att=0.02,
                                          rel=0.10, sub=sub if (m + dm) >= 36 and dm == 0 and off == 0 else 0.0))
                    self.marks.append((b + off, "bass"))
            b += BAR

    def add_pulse(self, t0, t1, step=E8, unify=None, db_extra=0.0, pan_w=0.30, tau=0.34,
                  skip=None, octave_double_db=None, kind="pluck"):
        """The five-step pluck pulse on the grid `step` between t0 and t1 (t1 excluded)."""
        t = t0
        while t < t1 - 1e-9:
            if skip is None or not skip(t):
                k = int(round(t / step))
                pool = CH[self.chord_at(t)]["pool"]
                m = unify if unify is not None else pool[CYCLE[k % 5]]
                acc = 0.0 if unify is not None else ACCENT[k % 5]
                db = self.lv("pluck", t) + acc + db_extra
                fc = self.lv_log("pluck_fc", t)
                pan = -pan_w if k % 2 == 0 else pan_w
                self.pluck.append(dict(t=t, midi=m, db=db, pan=pan, fc=fc, tau=tau))
                self.marks.append((t, kind))
                if octave_double_db is not None:
                    self.pluck.append(dict(t=t, midi=m + 12, db=db + octave_double_db, pan=-pan, fc=fc * 1.2, tau=tau * 0.8))
            t += step

    def add_bell(self, t, midi, db, pan=0.0, dur=3.0):
        self.bell.append(dict(t=float(t), midi=int(midi), db=db, pan=pan, dur=dur))
        self.marks.append((float(t), "bell"))

    def add_kick(self, t, db):
        self.kick.append(dict(t=float(t), db=db))
        self.marks.append((float(t), "kick"))

    def add_hat(self, t, db, pan=0.0, open_=False):
        self.hat.append(dict(t=float(t), db=db, pan=pan, open=open_))
        self.marks.append((float(t), "hat"))

    def add_rim(self, t, db, pan=0.0):
        self.rim.append(dict(t=float(t), db=db, pan=pan))
        self.marks.append((float(t), "rim"))

    def add_keys(self, t0, dur, chord_name, db, pan=0.0):
        for m in CH[chord_name]["keys"]:
            self.keys.append(dict(t0=float(t0), t1=float(t0 + dur), midi=m, db=db, pan=pan))
        self.marks.append((float(t0), "keys"))

    def motif(self, t, tonic, db, dur_last=3.4, spacing=BEAT):
        """The five-note motif, scale degrees 5-1-3-2-1 (one note per spoke).

        tonic 'F' -> C5 F5 A5 G5 F5 ; tonic 'D' -> A4 D5 F5 E5 D5.
        """
        if tonic == "F":
            ms = (72, 77, 81, 79, 77)
        else:
            ms = (69, 74, 77, 76, 74)
        for i, m in enumerate(ms):
            last = i == 4
            self.add_bell(t + i * spacing, m, db - (0.0 if i == 0 else 1.5) + (1.5 if last else 0.0),
                          pan=(-0.22, 0.22, -0.12, 0.12, 0.0)[i], dur=dur_last if last else 2.4)

    # ---------------------------------------------------------------- tidy-ups
    COLOUR = {2: (4, 7, 0), 10: (0,), 5: (7,), 0: (2,), 7: (9,)}      # tolerated colour tones: 9th, 11th, 7th

    def allowed_pc(self, chord_name, pc):
        """Is this pitch class part of the chord (any of its voicings) or one of its tolerated colour tones?"""
        c = CH[chord_name]
        strict = {m % 12 for m in c["pad"]} | {m % 12 for m in c["pool"]} | {m % 12 for m in c["keys"]} | {c["bass"] % 12, c["root"]}
        return pc in strict or pc in self.COLOUR.get(c["root"], ())

    def finalize(self):
        """Tidy-ups that need the whole harmony: a bell never rings on into a chord it clashes with; it is
        shortened so that it fades out just before that chord starts."""
        self.chord_segs.sort()
        for e in self.bell:
            pc = e["midi"] % 12
            for a, b, name in self.chord_segs:
                if a <= e["t"] + 1e-6 or a >= e["t"] + e["dur"]:
                    continue
                if not self.allowed_pc(name, pc):
                    e["dur"] = max(0.3, a - e["t"] - 0.02)
                    break
        self.marks.sort()

    # ------------------------------------------------------------------- patterns
    def bars(self, t0, t1):
        b = t0
        while b < t1 - 1e-6:
            yield b
            b += BAR


# --------------------------------------------------------------------------------------
# Mood presets (a scene's `music` tag in the timeline can nudge the energy of the groove)
MOODS = {"hook": 0.55, "title": 0.40, "explain": 0.30, "rule": 0.60, "world": 0.80, "outro": 0.25}
MOOD_ALIASES = {"engineering": "rule", "understand": "rule", "real": "world", "realworld": "world",
                "explanation": "explain", "calm": "explain", "takeaway": "outro", "end": "outro",
                "closing": "outro", "intro": "hook", "opening": "title", "cold-open": "hook"}
DEFAULT_MOOD = {"s01_hook": "hook", "s02_title": "title", "s03_snapshots": "explain", "s04_trick": "explain",
                "s05_rule": "rule", "s06_helicopter_lathe": "world", "s07_sensors_strobe": "world",
                "s08_takeaway": "outro",
                "short_hook": "hook", "short_trick": "explain", "short_end": "outro"}


def resolve_mood(scene_id, tag, log):
    """Return the energy factor (1.0 = as designed) for a scene given its optional music tag."""
    default = DEFAULT_MOOD.get(scene_id, "explain")
    if not tag:
        return default, 1.0
    key = MOOD_ALIASES.get(str(tag).lower(), str(tag).lower())
    if key not in MOODS:
        log(f"warning: scene {scene_id} has an unknown music tag '{tag}' (known: {', '.join(MOODS)}); using '{default}'")
        return default, 1.0
    if scene_id == "s08_takeaway" and key == "title":
        return default, 1.0            # the closing card borrows the title's warmth but keeps its own ending
    if key == default:
        return key, 1.0
    f = float(np.clip(MOODS[key] / MOODS[default], 0.7, 1.35))
    log(f"note: scene {scene_id} is tagged '{tag}' (designed as '{default}'): groove energy x{f:.2f}")
    return key, f


# ---------------------------------------------------------------------------------------
def build_score(scenes, log=print, comp="main"):
    """Compose the music of one composition ('main' = the 3-minute film, 'short' = the 45 s vertical cut).

    `scenes` is the list from the timeline (id, t0, t1, music).
    """
    if comp == "short":
        return build_score_short(scenes, log)
    if comp != "main":
        raise ValueError(f"unknown composition {comp!r}")
    S = Score()
    by_id = {s["id"]: s for s in scenes}

    def t0_of(sid, default):
        s = by_id.get(sid)
        if s is None:
            log(f"warning: scene {sid} is not in the timeline, using {default:g} s")
            return float(default)
        t = float(s["t0"])
        snapped = round(t / BAR) * BAR
        if abs(t - snapped) > 1e-6:
            log(f"warning: scene {sid} starts at {t:g} s, which is not on a bar line: snapped to {snapped:g} s")
        return float(snapped)

    T = dict(
        s01=t0_of("s01_hook", 0), s02=t0_of("s02_title", 18), s03=t0_of("s03_snapshots", 24),
        s04=t0_of("s04_trick", 48), s05=t0_of("s05_rule", 86), s06=t0_of("s06_helicopter_lathe", 126),
        s07=t0_of("s07_sensors_strobe", 148), s08=t0_of("s08_takeaway", 170), end=FILM,
    )
    energy = {}
    for sid in [k for k in DEFAULT_MOOD if not k.startswith("short_")]:
        tag = (by_id.get(sid) or {}).get("music")
        mood, f = resolve_mood(sid, tag, log)
        energy[sid] = f
        S.scene_moods[sid] = mood

    _automation(S, T)
    _hook(S, T["s01"], T["s02"], energy["s01_hook"])
    _title(S, T["s02"], T["s03"], energy["s02_title"])
    _explain_a(S, T["s03"], T["s04"], energy["s03_snapshots"])
    _explain_b(S, T["s04"], T["s05"], energy["s04_trick"])
    _rule(S, T["s05"], T["s06"], energy["s05_rule"])
    _world_a(S, T["s06"], T["s07"], energy["s06_helicopter_lathe"])
    _world_b(S, T["s07"], T["s08"], energy["s07_sensors_strobe"])
    _outro(S, T["s08"], T["end"], energy["s08_takeaway"])
    S.finalize()
    S.T = T
    return S


# ============================================================================ automation
def _automation(S, T):
    """Levels (dB) and brightness (Hz) that move through the film. Times are absolute seconds."""
    a = {"s01": T["s01"], "s02": T["s02"], "s03": T["s03"], "s04": T["s04"], "s05": T["s05"],
         "s06": T["s06"], "s07": T["s07"], "s08": T["s08"]}
    # pad level and pad brightness (a low-pass cut-off)
    S.set("pad_db", [
        (0.0, -40), (0.6, -28), (2.6, -16), (4.0, -13), (7.0, -10.5), (8.0, -9.5), (11.0, -8.0), (11.5, -11.5), (13.4, -11.0),
        (13.5, -10), (14.0, -8.5), (16.0, -7.0), (17.95, -5.5),
        (18.0, -7.5), (18.9, -3.5), (21.0, -5.5), (23.9, -7.0),
        (24.0, -9.5), (47.9, -9.5),
        (48.0, -9.5), (67.9, -9.5), (70.0, -7.5), (74.0, -8.5), (78.0, -9.0), (80.0, -9.0), (85.9, -8.5),
        (86.0, -8.0), (100.0, -7.0), (110.0, -6.5), (114.9, -6.0), (115.1, -3.5), (118.0, -5.0), (125.9, -6.0),
        (126.0, -6.0), (147.9, -5.5), (148.0, -5.0), (169.9, -5.0),
        (170.0, -6.0), (174.0, -4.5), (176.0, -5.0), (177.5, -7.0), (180.0, -12.0),
    ])
    S.set("pad_fc", [
        (0.0, 200), (2.0, 240), (4.0, 330), (6.0, 520), (7.35, 720), (7.5, 480), (7.8, 380), (7.95, 430), (8.15, 820),
        (10.0, 1300), (11.0, 1700), (11.4, 1500), (11.6, 700), (12.5, 650), (13.4, 700), (13.6, 1000), (14.0, 1300),
        (16.0, 2400), (17.95, 3400),
        (18.0, 2800), (19.0, 3000), (21.0, 2200), (23.9, 1500),
        (24.0, 1000), (36.0, 1200), (47.9, 1200),
        (48.0, 1000), (64.0, 1200), (69.5, 1300), (70.0, 2100), (74.0, 1700), (78.0, 1400), (80.0, 1000), (85.9, 1200),
        (86.0, 1700), (100.0, 2100), (112.0, 2400), (114.9, 2400), (115.1, 3700), (118.0, 2800), (125.9, 2200),
        (126.0, 2300), (147.9, 2500), (148.0, 2500), (169.9, 2300),
        (170.0, 2000), (174.0, 2100), (176.0, 1500), (178.0, 900), (180.0, 600),
    ])
    S.set("bass_db", [
        (0.0, -40), (0.6, -22), (2.0, -12), (2.6, -8), (4.0, -6.5), (11.4, -6.5), (11.6, -11), (13.5, -11), (13.6, -6.5),
        (17.9, -4.5), (18.0, -5.0), (24.0, -8.5), (47.9, -8.5), (48.0, -8.5), (67.9, -8.5), (70.0, -5.5), (74.0, -7.0),
        (79.9, -8.5), (80.0, -9.5), (85.9, -8.5), (86.0, -6.5), (125.9, -6.0), (126.0, -5.5), (169.9, -5.0),
        (170.0, -6.0), (174.0, -4.5), (177.5, -6.5), (180.0, -14.0),
    ])
    # pluck level (per note) and brightness
    S.set("pluck", [
        (0.0, -26), (1.0, -26), (4.0, -22), (7.4, -15.5), (11.25, -12.5), (13.5, -26), (14.0, -17.0), (16.0, -14.5), (17.9, -11.5),
        (18.0, -22), (20.0, -25), (22.0, -21), (23.9, -20),
        (24.0, -20.5), (30.0, -18.5), (47.9, -18.5),
        (48.0, -18.5), (69.9, -18.5), (70.0, -15.5), (78.0, -16.5), (79.9, -18.0), (80.0, -18.0), (84.0, -20.0), (85.9, -19.0),
        (86.0, -14.5), (114.0, -13.5), (115.0, -11.5), (125.99, -12.5),
        (126.0, -12.0), (169.99, -11.5),
        (170.0, -20.5), (176.0, -22.0), (180.0, -26.0),
    ])
    S.set("pluck_fc", [
        (0.0, 1000), (4.0, 1500), (8.0, 2600), (11.25, 3200), (13.5, 1000), (14.0, 1900), (18.0, 4200),
        (18.1, 2300), (24.0, 2400), (69.9, 2500), (70.0, 3400), (78.0, 2900), (80.0, 2100), (85.9, 2500),
        (86.0, 3300), (126.0, 3800), (148.0, 4200), (169.9, 4200), (170.0, 2600), (180.0, 1600),
    ])
    S.set("delay_send", [(0.0, -22), (11.0, -18), (11.5, -10), (13.4, -10), (13.6, -18), (24.0, -20), (86.0, -16), (126.0, -14), (170.0, -16), (176.0, -10)])


# ==================================================================================== scenes
def _hook(S, t0, t1, en):
    """Hook 0 - 18 s: curious, building tension. Pulse quickens with the car; a tape sag at 7.4 s
    when the wheel seems to reverse; a suspended hush 11.5 - 13.5 s at the freeze; then the build."""
    segs = [(0.0, 4.0, "Dm"), (4.0, 8.0, "Bb"), (8.0, 11.5, "F"), (11.5, 13.5, "Fsus2"), (13.5, 14.0, "F"),
            (14.0, 16.0, "Bb"), (16.0, 17.5, "C"), (17.5, t1, "Csus4")]
    S.harmony(segs, att=0.9, rel=1.8)
    S.bass_long(segs, sub=0.30)
    S.bend = Bend(7.40, 8.00)

    # pulse: quarter notes while the car pulls away, eighths from 4 s, silence for the freeze
    S.add_pulse(1.0, 4.0, step=BEAT)
    S.add_pulse(4.0, 11.5, step=E8)
    S.add_pulse(13.5, 14.0, step=BEAT, db_extra=-2.0)
    S.add_pulse(14.0, 16.0, step=E8)
    S.add_pulse(16.0, t1, step=S16)          # sixteenths: the build

    # hats: offbeat brushes from 6 s, full eighths in the build, sixteenths in the last bar
    for b in S.bars(6.0, 11.5):
        for off in (0.25, 0.75, 1.25, 1.75):
            if b + off < 11.5:
                S.add_hat(b + off, -31 + 0.9 * (b - 6.0), pan=0.25 if off in (0.25, 1.25) else -0.25)
    for b in S.bars(14.0, 16.0):
        for i in range(8):
            S.add_hat(b + i * E8, -30 + (b - 14.0) * 1.5 + (2.0 if i % 2 else 0.0), pan=0.25 if i % 2 else -0.25)
    for i in range(16):
        S.add_hat(16.0 + i * S16, -28.0 + i * 0.5 + (1.5 if i % 2 else 0.0), pan=0.25 if i % 2 else -0.25)

    # kick: two soft beats, then every beat of the last bar
    S.add_kick(14.0, -18.0)
    S.add_kick(15.0, -19.0)
    for i, db in enumerate((-18.0, -16.5, -15.0, -13.5)):
        S.add_kick(16.0 + i * BEAT, db)

    # rim-click roll into the title: eighths, then sixteenths
    for t, db in ((16.5, -30), (17.0, -28), (17.25, -27), (17.5, -25.5), (17.625, -24.5), (17.75, -23.5), (17.875, -22.5)):
        S.add_rim(t, db, pan=-0.3 if int(round(t / S16)) % 2 else 0.3)

    # noise swell rising into the title downbeat
    S.swell.append(dict(t0=14.0, t1=t1 - 0.02, f0=450, f1=5200, db=-22.0, curve=1.3, power=2.2, fall=0.06))


def _title(S, t0, t1, en):
    """Title 18 - 24 s: the warm F major answer, spacious. The `hit` sound effect lands at 18.85 s."""
    segs = [(t0, t0 + 2.0, "F"), (t0 + 2.0, t0 + 4.0, "Dm"), (t0 + 4.0, t0 + 5.0, "Bb"), (t0 + 5.0, t1, "C")]
    S.harmony(segs, att=0.9, rel=2.2)
    S.bass_long(segs, sub=0.32)
    S.add_kick(t0, -14.0)                                          # the build lands on the downbeat
    S.add_bell(t0 + 0.5, 77, -14.0, pan=0.0, dur=3.2)             # F5, on the beat where the swoosh lands
    S.motif(t0 + 1.0, "F", -12.5, dur_last=2.2)                    # C5 F5 A5 G5 F5
    S.add_pulse(t0 + 2.0, t0 + 4.0, step=BEAT)
    S.add_pulse(t0 + 4.0, t1, step=E8)


def _explain_a(S, t0, t1, en):
    """Snapshots 24 - 48 s: calm, curious, low density. Room for the shutter clicks."""
    segs = [(t0, t0 + 4, "Dm"), (t0 + 4, t0 + 8, "Bb"), (t0 + 8, t0 + 12, "F"), (t0 + 12, t0 + 16, "C"),
            (t0 + 16, t0 + 20, "Dm"), (t0 + 20, t0 + 22, "Bb"), (t0 + 22, t1, "C")]
    S.harmony(segs, att=1.0, rel=2.0)
    S.bass_long(segs, sub=0.28)
    S.add_pulse(t0, t1, step=E8)
    hat_db = -31.0 + 3.0 * (en - 1.0)
    for b in S.bars(t0 + 12.0, t1):
        for off in (0.25, 0.75, 1.25, 1.75):
            S.add_hat(b + off, hat_db - (3.0 if b < t0 + 14 else 0.0), pan=0.22 if off in (0.25, 1.25) else -0.22)
    # a barely-there kick on the first beat every four bars
    for b in S.bars(t0 + 16.0, t1):
        if int(round((b - t0) / BAR)) % 2 == 0:
            S.add_kick(b, -23.0)


def _explain_b(S, t0, t1, en):
    """The trick 48 - 86 s: same calm. A small lift at 70 s (the backwards reveal), and at 80 s the
    pulse 'freezes' on one repeated note (every picture identical) inside a suspended chord."""
    lift = t0 + 22.0            # 70 s
    freeze = t0 + 32.0          # 80 s
    segs = [(t0, t0 + 4, "Dm"), (t0 + 4, t0 + 8, "Bb"), (t0 + 8, t0 + 12, "F"), (t0 + 12, t0 + 16, "C"),
            (t0 + 16, t0 + 20, "Bb"), (t0 + 20, lift, "Dm"), (lift, lift + 4, "F"), (lift + 4, lift + 8, "Bb"),
            (lift + 8, freeze, "C"), (freeze, freeze + 4, "Fsus2"), (freeze + 4, t1, "C")]
    S.harmony(segs, att=1.0, rel=2.0, air_db=-11.0, air_from=lift)
    S.bass_long(segs, sub=0.28)

    # pulse: cycle, brighter and doubled an octave up during the lift, one repeated note in the freeze
    S.add_pulse(t0, lift, step=E8)
    S.add_pulse(lift, lift + 8, step=E8, octave_double_db=-9.0)
    S.add_pulse(lift + 8, freeze, step=E8)
    S.add_pulse(freeze, freeze + 4, step=E8, unify=72, db_extra=-0.5)      # C5, again and again
    S.add_pulse(freeze + 4, t1, step=E8)

    # the pickup and the lift itself
    for i, m in enumerate((65, 69, 72, 77, 81)):
        S.pluck.append(dict(t=lift - 0.625 + i * S16, midi=m, db=-15.0 + i * 1.0, pan=-0.3 + 0.15 * i, fc=3200, tau=0.36))
        S.marks.append((lift - 0.625 + i * S16, "pluck"))
    S.add_bell(lift, 65, -16.0, pan=-0.2, dur=3.0)
    S.add_bell(lift, 72, -17.0, pan=0.0, dur=3.0)
    S.add_bell(lift, 81, -18.0, pan=0.25, dur=3.0)
    S.swell.append(dict(t0=lift - 1.0, t1=lift - 0.02, f0=800, f1=5000, db=-24.0, curve=1.2, power=2.0, fall=0.05))

    # rhythm: soft kick on the downbeat from 56 s; a firmer groove through the lift; nothing in the freeze
    hat_db = -30.0 + 3.0 * (en - 1.0)
    for b in S.bars(t0 + 8.0, t1):
        in_lift = lift <= b < lift + 8
        in_freeze = freeze <= b < freeze + 4
        if in_freeze:
            continue
        S.add_kick(b, -22.0 if not in_lift else -15.5)
        if in_lift:
            S.add_kick(b + 1.0, -18.0)
            S.add_rim(b + 1.5, -27.0, pan=0.3)
        for i in range(8):
            if not in_lift and i % 2 == 0:
                continue
            db = hat_db + (2.5 if in_lift else 0.0) + (2.0 if i % 2 else 0.0) - (3.0 if b < t0 + 14 else 0.0)
            S.add_hat(b + i * E8, db, pan=0.24 if i % 2 else -0.24)


def _rule(S, t0, t1, en):
    """The rule 86 - 126 s: brighter chords, a firmer (still soft) rhythm, and at 115 s the resolution
    C -> F while the motif plays. Then an afterglow with the first electric-piano chords."""
    res = t0 + 29.0             # 115 s
    segs = [(t0, t0 + 4, "Fmaj7"), (t0 + 4, t0 + 8, "Dm9"), (t0 + 8, t0 + 12, "Bbmaj7"), (t0 + 12, t0 + 16, "Cadd9"),
            (t0 + 16, t0 + 20, "Fmaj7"), (t0 + 20, t0 + 24, "Dm7"), (t0 + 24, t0 + 28, "Bbmaj7"),
            (t0 + 28, res, "C"), (res, res + 3, "Fadd9"), (res + 3, res + 5, "Dm"), (res + 5, res + 7, "Bb"),
            (res + 7, res + 9, "F"), (res + 9, t1, "C")]
    S.harmony(segs, att=1.0, rel=2.0, air_db=-10.5, air_from=t0 + 16.0)
    # bass: rhythmic groove, except the bar of the resolution which is written by hand
    res_bar = int(round((res - res % BAR) / BAR))
    S.bass_groove(t0, t1, sub=0.0, skip_bars=(res_bar,))
    S.bass.append(dict(t0=res - 1.0, t1=res - 0.12, midi=CH["C"]["bass"], db=0.0, att=0.02, rel=0.10, sub=0.0))
    S.bass.append(dict(t0=res, t1=res + 1.55, midi=CH["F"]["bass"], db=0.5, att=0.02, rel=0.25, sub=0.28))
    S.marks += [(res - 1.0, "bass"), (res, "bass")]

    # pulse
    S.add_pulse(t0, res - 1.0, step=E8)
    run = (60, 64, 67, 72, 76, 79, 84, 88)                     # a rising C major run (fits the chord), sixteenths, into 115 s
    for i, m in enumerate(run):
        t = res - 1.0 + i * S16
        S.pluck.append(dict(t=t, midi=m, db=-13.5 + i * 0.6, pan=-0.3 if i % 2 else 0.3, fc=3600, tau=0.32))
        S.marks.append((t, "pluck"))
    S.add_pulse(res, t1, step=E8, db_extra=0.0)

    # the resolution: motif in F major, arrival chord in bells, soft open hat and kick
    S.motif(res, "F", -11.5, dur_last=4.2)
    for m, db in ((65, -16.0), (69, -17.5)):
        S.add_bell(res, m, db, pan=0.0, dur=3.5)
    S.swell.append(dict(t0=res - 2.0, t1=res - 0.02, f0=600, f1=5600, db=-21.0, curve=1.2, power=2.2, fall=0.06))
    S.add_kick(res, -13.5)
    S.add_hat(res, -21.0, pan=0.0, open_=True)

    # rhythm
    hat_db = -27.0 + 3.0 * (en - 1.0)
    for b in S.bars(t0, t1):
        rel = b - t0
        # kick: beat 1 and the "and" of beat 3 (steps 0 and 5 of the eighth-note bar)
        if b < res - 1.0 or b >= res + 1.0:
            S.add_kick(b, -17.0)
            S.add_kick(b + 1.25, -20.0)
        if b < res - 1.0 or b >= res + 1.0:
            if rel >= 8.0:
                S.add_rim(b + 1.5, -26.0, pan=0.3)
        for i in range(8):
            t = b + i * E8
            if res - 1.0 <= t < res or abs(t - res) < 1e-9:
                continue
            db = hat_db + (2.5 if i % 2 else 0.0)
            S.add_hat(t, db, pan=0.24 if i % 2 else -0.24)
    # sixteenth hats in the second half of the run-up bar
    for i in range(8):
        S.add_hat(res - 1.0 + i * S16, -27.0 + i * 0.8, pan=0.25 if i % 2 else -0.25)
    # electric piano enters after the resolution
    for b in S.bars(res + 3.0, t1):
        n = S.chord_at(b)
        S.add_keys(b, 1.4, n, -21.0, pan=-0.25 if int(round(b / BAR)) % 2 == 0 else 0.25)


def _world_a(S, t0, t1, en):
    """Real world 1, 126 - 148 s: wider and warmer, electric piano, a little more groove."""
    segs = [(t0, t0 + 4, "F"), (t0 + 4, t0 + 8, "C"), (t0 + 8, t0 + 12, "Dm"), (t0 + 12, t0 + 16, "Bb"),
            (t0 + 16, t0 + 18, "F"), (t0 + 18, t0 + 20, "Gm"), (t0 + 20, t1, "C")]
    S.harmony(segs, att=1.0, rel=2.0, air_db=-9.0, air_from=t0)
    S.bass_groove(t0, t1, sub=0.0)
    S.add_pulse(t0, t1, step=E8, octave_double_db=None)
    _groove(S, t0, t1, en, kick=(0.0, 1.25, 0.75), hat_db=-26.0, rim=(0.5, 1.5), rim_db=-25.0)
    _keys_comp(S, t0, t1, -20.0)
    for a, b, n in segs:
        S.add_bell(a, CH[n]["pool"][3] + 12, -20.0, pan=0.3, dur=min(2.6, b - a - 0.05))


def _world_b(S, t0, t1, en):
    """Real world 2, 148 - 170 s: the same warmth with a little more energy, thinning out at the end."""
    segs = [(t0, t0 + 4, "Dm"), (t0 + 4, t0 + 8, "Bb"), (t0 + 8, t0 + 12, "F"), (t0 + 12, t0 + 16, "C"),
            (t0 + 16, t0 + 18, "Dm"), (t0 + 18, t0 + 20, "Bb"), (t0 + 20, t1, "F")]
    S.harmony(segs, att=1.0, rel=2.0, air_db=-8.5, air_from=t0)
    S.bass_groove(t0, t1, sub=0.0)
    S.add_pulse(t0, t1, step=E8, octave_double_db=-12.0)
    _groove(S, t0, t1 - 2.0, en, kick=(0.0, 1.25, 0.75), hat_db=-24.5, rim=(0.5, 1.5), rim_db=-24.0, sixteenth=True)
    _keys_comp(S, t0, t1, -19.0)
    for a, b, n in segs:
        S.add_bell(a, CH[n]["pool"][3] + 12, -19.0, pan=-0.3, dur=min(2.6, b - a - 0.05))


def _groove(S, t0, t1, en, kick, hat_db, rim, rim_db, sixteenth=False):
    hat_db = hat_db + 3.0 * (en - 1.0)
    for b in S.bars(t0, t1):
        S.add_kick(b + kick[0], -17.5)
        S.add_kick(b + kick[1], -20.5)
        S.add_kick(b + kick[2], -26.0)
        for off in rim:
            S.add_rim(b + off, rim_db, pan=0.3 if off < 1.0 else -0.3)
        for i in range(8):
            S.add_hat(b + i * E8, hat_db + (2.5 if i % 2 else 0.0), pan=0.24 if i % 2 else -0.24)
            if sixteenth and i % 2 == 1:
                S.add_hat(b + i * E8 + S16, hat_db - 6.0, pan=-0.2)


def _keys_comp(S, t0, t1, db):
    for b in S.bars(t0, t1):
        n = S.chord_at(b)
        pan = -0.25 if int(round(b / BAR)) % 2 == 0 else 0.25
        S.add_keys(b, 1.2, n, db, pan)
        S.add_keys(b + 1.25, 0.4, S.chord_at(b + 1.25), db - 4.0, -pan)


def _outro(S, t0, t1, en):
    """Takeaway 170 - 180 s: Bb - C - Dm, the motif on the tonic at 174 s, then a tail to silence."""
    arrive = t0 + 4.0           # 174 s
    segs = [(t0, t0 + 2, "Bb"), (t0 + 2, arrive, "C"), (arrive, arrive + 2.0, "Dm"), (arrive + 2.0, arrive + 3.6, "Dm9b")]
    S.harmony(segs, att=1.0, rel=2.4)
    S.bass_long(segs, sub=0.36)
    S.add_pulse(t0 + 1.0, t0 + 2.0, step=BEAT, db_extra=-1.0)
    S.add_pulse(t0 + 2.0, arrive, step=E8)
    S.add_pulse(arrive, arrive + 2.0, step=BEAT, db_extra=-2.0)
    S.add_kick(arrive, -17.0)
    S.motif(arrive, "D", -12.0, dur_last=4.0)
    S.add_bell(arrive + 2.0, 86, -20.0, pan=0.25, dur=3.8)        # D6, a glassy octave above the last note


# ================================================================================ the Short
def build_score_short(scenes, log=print):
    """The 45 s vertical cut: hook (0-16 s), the trick (16-38 s), the ending (38-45 s).

    It reuses the ideas of the film: the same chords and motif, the tape sag when the wheel seems to
    reverse, the suspended hush at the freeze, a lift at the real-speed reveal and the closing cadence.
    """
    S = Score()
    by_id = {s["id"]: s for s in scenes}

    def t0_of(sid, default):
        sc = by_id.get(sid)
        if sc is None:
            log(f"warning: scene {sid} is not in the timeline, using {default:g} s")
            return float(default)
        t = float(sc["t0"])
        snapped = round(t / BAR) * BAR
        if abs(t - snapped) > 1e-6:
            log(f"warning: scene {sid} starts at {t:g} s, which is not on a bar line: snapped to {snapped:g} s")
        return float(snapped)

    T = dict(hook=t0_of("short_hook", 0.0), trick=t0_of("short_trick", 16.0), end=t0_of("short_end", 38.0), film=45.0)
    energy = {}
    for sid in ("short_hook", "short_trick", "short_end"):
        mood, f = resolve_mood(sid, (by_id.get(sid) or {}).get("music"), log)
        energy[sid] = f
        S.scene_moods[sid] = mood
    _automation_short(S)
    _short_hook(S, T["hook"], T["trick"], energy["short_hook"])
    _short_trick(S, T["trick"], T["end"], energy["short_trick"])
    _short_end(S, T["end"], T["film"], energy["short_end"])
    S.finalize()
    S.T = dict(T)
    return S


def _automation_short(S):
    S.set("pad_db", [
        (0.0, -40), (0.6, -28), (2.6, -16), (4.0, -13), (6.4, -10.5), (7.0, -9.5), (9.25, -8.5), (9.5, -11.5), (12.0, -11.0),
        (12.05, -10.0), (12.5, -8.5), (14.0, -7.5), (15.95, -6.0),
        (16.0, -9.5), (33.9, -9.5), (34.0, -7.5), (37.9, -8.0),
        (38.0, -6.0), (41.0, -4.5), (43.0, -5.0), (44.0, -8.0), (45.0, -12.0),
    ])
    S.set("pad_fc", [
        (0.0, 200), (2.0, 240), (4.0, 330), (5.5, 520), (6.35, 720), (6.5, 480), (6.8, 380), (6.95, 430), (7.1, 820),
        (8.5, 1300), (9.25, 1700), (9.45, 1500), (9.6, 700), (10.5, 650), (11.95, 700), (12.1, 1000), (13.0, 1400), (15.95, 2300),
        (16.0, 1000), (26.0, 1200), (33.9, 1300), (34.0, 2100), (37.9, 1700),
        (38.0, 2000), (41.0, 2100), (43.0, 1500), (44.5, 700), (45.0, 600),
    ])
    S.set("bass_db", [
        (0.0, -40), (0.6, -22), (2.0, -12), (2.6, -8), (4.0, -6.5), (9.25, -6.5), (9.5, -11), (12.0, -11), (12.1, -6.5),
        (15.9, -5.0), (16.0, -8.5), (33.9, -8.5), (34.0, -5.5), (37.9, -7.5), (38.0, -6.0), (41.0, -4.5), (43.5, -6.5), (45.0, -14.0),
    ])
    S.set("pluck", [
        (0.0, -26), (1.0, -26), (4.0, -22), (6.4, -15.5), (9.25, -12.5), (12.0, -26), (12.5, -18.0), (14.0, -16.0), (15.9, -12.5),
        (16.0, -18.5), (33.9, -18.5), (34.0, -15.5), (37.9, -16.5),
        (38.0, -20.5), (43.0, -22.0), (45.0, -26.0),
    ])
    S.set("pluck_fc", [
        (0.0, 1000), (4.0, 1500), (7.0, 2600), (9.25, 3200), (12.0, 1000), (12.5, 1900), (15.9, 3800),
        (16.0, 2400), (33.9, 2500), (34.0, 3400), (37.9, 2900), (38.0, 2600), (45.0, 1600),
    ])
    S.set("delay_send", [(0.0, -22), (9.25, -18), (9.5, -10), (11.9, -10), (12.1, -18), (16.0, -20), (38.0, -16), (42.0, -10)])


def _short_hook(S, t0, t1, en):
    """Short hook 0 - 16 s: the same curious build, with the tape sag when the wheel seems to reverse
    (6.4 s, the glitch), the suspended hush during the freeze (9.5 - 12 s) and a short build (a question)."""
    sag0, sag1 = 6.4, 7.0
    freeze0, freeze1 = 9.5, 12.0
    segs = [(0.0, 4.0, "Dm"), (4.0, sag1, "Bb"), (sag1, freeze0, "F"), (freeze0, freeze1, "Fsus2"),
            (freeze1, 12.5, "F"), (12.5, 14.0, "Bb"), (14.0, 15.5, "C"), (15.5, t1, "Csus4")]
    S.harmony(segs, att=0.9, rel=1.8)
    S.bass_long(segs, sub=0.30)
    S.bend = Bend(sag0, sag1)
    S.add_pulse(1.0, 4.0, step=BEAT)
    S.add_pulse(4.0, freeze0, step=E8)
    S.add_pulse(freeze1, 12.5, step=BEAT, db_extra=-2.0)
    S.add_pulse(12.5, 14.0, step=E8)
    S.add_pulse(14.0, t1, step=S16)
    for b in S.bars(6.0, freeze0):
        for off in (0.25, 0.75, 1.25, 1.75):
            if b + off < freeze0:
                S.add_hat(b + off, -31 + 0.9 * (b - 6.0), pan=0.25 if off in (0.25, 1.25) else -0.25)
    for i in range(6):                                   # eighth-note hats while the pulse returns
        t = 12.5 + i * E8
        S.add_hat(t, -31 + (t - 12.5) * 1.2 + (2.0 if i % 2 else 0.0), pan=0.25 if i % 2 else -0.25)
    for i in range(16):
        S.add_hat(14.0 + i * S16, -29.0 + i * 0.5 + (1.5 if i % 2 else 0.0), pan=0.25 if i % 2 else -0.25)
    for i, db in enumerate((-19.0, -18.0, -17.0, -15.5)):
        S.add_kick(14.0 + i * BEAT, db)
    for t, db in ((15.0, -30), (15.25, -28.5), (15.5, -27), (15.625, -26), (15.75, -25), (15.875, -24)):
        S.add_rim(t, db, pan=-0.3 if int(round(t / S16)) % 2 else 0.3)
    S.swell.append(dict(t0=13.0, t1=t1 - 0.02, f0=450, f1=5000, db=-24.0, curve=1.3, power=2.2, fall=0.06))


def _short_trick(S, t0, t1, en):
    """Short trick 16 - 38 s: calm and steady while a picture is taken every second (the shutter clicks fall
    on beats 1 and 3, so there is no kick there); a lift at 34 s when the real-speed wheel seems to creep back."""
    lift = 34.0
    segs = [(t0, t0 + 4, "Dm"), (t0 + 4, t0 + 8, "Bb"), (t0 + 8, t0 + 12, "F"), (t0 + 12, t0 + 16, "C"),
            (t0 + 16, lift, "Dm"), (lift, t1, "F")]
    S.harmony(segs, att=1.0, rel=2.0, air_db=-11.0, air_from=lift)
    S.bass_long(segs, sub=0.28)
    S.add_pulse(t0, lift, step=E8)
    S.add_pulse(lift, t1, step=E8, octave_double_db=-9.0)
    for b in S.bars(t0 + 8.0, lift):
        for off in (0.25, 0.75, 1.25, 1.75):
            S.add_hat(b + off, -32.0 + 3.0 * (en - 1.0), pan=0.22 if off in (0.25, 1.25) else -0.22)
    # the lift: a rising pickup, a bell chord, a swell, kick and a firmer hat
    for i, m in enumerate((65, 69, 72, 77, 81)):
        S.pluck.append(dict(t=lift - 0.625 + i * S16, midi=m, db=-15.0 + i, pan=-0.3 + 0.15 * i, fc=3200, tau=0.36))
        S.marks.append((lift - 0.625 + i * S16, "pluck"))
    for m, db, pan in ((65, -16.0, -0.2), (72, -17.0, 0.0), (81, -18.0, 0.25)):
        S.add_bell(lift, m, db, pan=pan, dur=3.0)
    S.swell.append(dict(t0=lift - 1.0, t1=lift - 0.02, f0=800, f1=5000, db=-24.0, curve=1.2, power=2.0, fall=0.05))
    for b in S.bars(lift, t1):
        S.add_kick(b, -16.0)
        S.add_kick(b + 1.0, -19.0)
        S.add_rim(b + 1.5, -27.0, pan=0.3)
        for i in range(8):
            S.add_hat(b + i * E8, -29.0 + 3.0 * (en - 1.0) + (2.5 if i % 2 else 0.0), pan=0.24 if i % 2 else -0.24)


def _short_end(S, t0, t1, en):
    """Short ending 38 - 45 s: Bb - C - Dm, the motif on the tonic at 41 s, then a tail to silence."""
    arrive = t0 + 3.0           # 41 s
    segs = [(t0, t0 + 2, "Bb"), (t0 + 2, arrive, "C"), (arrive, arrive + 2.0, "Dm"), (arrive + 2.0, arrive + 3.5, "Dm9b")]
    S.harmony(segs, att=1.0, rel=2.4)
    S.bass_long(segs, sub=0.36)
    S.add_pulse(t0, t0 + 2.0, step=E8)
    S.add_pulse(t0 + 2.0, arrive, step=E8, db_extra=-1.0)
    S.add_pulse(arrive, arrive + 2.0, step=BEAT, db_extra=-2.0)
    S.add_kick(arrive, -17.0)
    S.motif(arrive, "D", -12.0, dur_last=2.5)
    S.add_bell(arrive + 2.0, 86, -20.0, pan=0.25, dur=2.6)
