"""
Resonance - the original score, written as note events in seconds and rendered
with FluidSynth and the MuseScore General soundfont (MIT licence).

Key of D major. The music follows the physics where it can be heard:
  - the hook: one bar per push of the rhythm swing, a celesta ping on each push
  - the natural rhythm: a vibraphone note at every back-and-forth of the free swing
  - the spring: a marimba note per oscillation, as loud as the motion (it dies away)
  - k and m: three rigs, three pitches and three tempos (1 Hz, 2 Hz, 0.5 Hz)
  - Taipei 101: strings swell with the tower's 6.8 s sway, the choir a quarter beat later

  python make_music.py OUT.wav
"""

import math
import os
import subprocess
import sys
import tempfile

import mido
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import physics as P  # noqa: E402
import timeline as tl  # noqa: E402

SOUNDFONT = os.environ.get("EP_SOUNDFONT", "/usr/share/sounds/sf3/MuseScore_General_Full.sf3")
T = tl.line_times()
S = tl.scenes(T)


def at(lid, phrase=None):
    return T[lid][0] if phrase is None else tl.phrase_time(lid, phrase, T)


# channel: (GM program, base volume 0-127, pan 0-127, reverb send 0-127)
CH = {
    "piano": (0, 0, 100, 60, 70),
    "strings": (1, 48, 92, 64, 90),
    "celesta": (2, 8, 80, 76, 100),
    "pad": (3, 89, 70, 64, 90),
    "choir": (4, 52, 78, 56, 100),
    "vibes": (5, 11, 88, 70, 90),
    "marimba": (6, 12, 96, 58, 70),
    "cello": (7, 42, 96, 50, 70),
    "timpani": (8, 47, 105, 64, 60),
    "bass": (10, 43, 90, 64, 50),
}

EVENTS = []          # (time, kind, channel, a, b, note id)
_NID = [0]


def note(t, ch, pitch, dur, vel):
    c = CH[ch][0]
    vel = int(max(1, min(127, vel)))
    _NID[0] += 1
    EVENTS.append((t, "on", c, pitch, vel, _NID[0]))
    EVENTS.append((t + dur, "off", c, pitch, 0, _NID[0]))


def chord(t, ch, pitches, dur, vel, spread=0.0):
    for i, p in enumerate(pitches):
        note(t + i * spread, ch, p, dur - i * spread, vel)


def expr(t0, t1, ch, v0, v1, steps=None):
    """Expression (CC11) ramp: swells and fades."""
    c = CH[ch][0]
    steps = steps or max(2, int((t1 - t0) * 20))
    for i in range(steps + 1):
        u = i / steps
        u = u * u * (3 - 2 * u)
        EVENTS.append((t0 + (t1 - t0) * i / steps, "cc", c, 11, int(v0 + (v1 - v0) * u), 0))


# pitches
N = {n: i for i, n in enumerate(["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"])}


def p(name):
    """'D4' -> 62"""
    n, o = name[:-1], int(name[-1])
    return 12 * (o + 1) + N[n]


def ps(*names):
    return [p(n) for n in names]


# ------------------------------------------------------------------ the score

def score():
    d_sw = P.swing_data(os.path.join(tl.BUILD, "data"))
    hook0 = S["hook"][0]
    pushes = [hook0 + x for x in d_sw["rhythm_pushes"]]

    # A. ident: a sparkle and a soft bed
    for i, n in enumerate(["D5", "F#5", "A5", "D6"]):
        note(0.15 + 0.13 * i, "celesta", p(n), 1.6, 62 + 6 * i)
    expr(0.0, 0.1, "pad", 0, 0)
    expr(0.1, 2.4, "pad", 0, 88)
    chord(0.1, "pad", ps("D3", "A3", "D4"), 4.6, 70)

    # B. hook: one bar per push of the rhythm swing (the bars follow the physics)
    bars = [(2.0, pushes[0])] + list(zip(pushes[:-1], pushes[1:])) + [(pushes[-1], at("L04"))]
    prog = [("D", "D2", ["D3", "F#3", "A3"], ["A4", "F#4", "D4", "F#4"]),
            ("D", "D2", ["D3", "F#3", "A3"], ["A4", "F#4", "D4", "F#4"]),
            ("D/F#", "F#2", ["D3", "F#3", "A3"], ["A4", "F#4", "D4", "A4"]),
            ("Bm", "B1", ["B2", "D3", "F#3"], ["B4", "F#4", "D4", "F#4"]),
            ("G", "G1", ["G2", "B2", "D3"], ["B4", "G4", "D4", "G4"]),
            ("D/F#", "F#2", ["D3", "F#3", "A3"], ["A4", "F#4", "D4", "F#4"]),
            ("Em7", "E2", ["E3", "G3", "D4"], ["B4", "G4", "E4", "G4"]),
            ("Asus", "A1", ["A2", "D3", "E3"], ["A4", "E4", "D4", "E4"])]
    expr(2.0, 2.1, "strings", 30, 30)
    expr(2.1, at("L04"), "strings", 30, 104)
    for bi, (b0, b1) in enumerate(bars):
        name, bass, mid, arp = prog[min(bi, len(prog) - 1)]
        L = b1 - b0
        grow = bi / (len(bars) - 1)
        if bi > 0:
            note(b0, "piano", p(bass), L * 0.98, 58 + 16 * grow)
            note(b0, "piano", p(bass) + 12, L * 0.98, 44 + 14 * grow)
            note(b0, "celesta", p(arp[0]) + 12, 1.2, 50 + 20 * grow)         # the push 'ping'
        chord(b0, "strings", [p(x) for x in mid], L + 0.3, 70)
        if bi > 0:
            for k in range(8):
                note(b0 + L * k / 8, "piano", p(arp[k % 4]) + (12 if (k >= 4 and grow > 0.6) else 0),
                     L / 8 * 1.6, 34 + 26 * grow + (8 if k == 0 else 0))
    # C. title: the resolution, D major add 9
    tt = at("L04")
    note(tt - 0.02, "timpani", p("D2"), 2.5, 96)
    note(tt - 0.02, "timpani", p("A1"), 2.5, 70)
    chord(tt, "strings", ps("D2", "A2", "D3", "F#3", "A3", "E4"), 4.4, 100)
    expr(tt + 0.2, tt + 4.2, "strings", 104, 50)
    chord(tt, "choir", ps("D4", "F#4", "A4"), 3.6, 70)
    expr(tt - 0.3, tt, "choir", 60, 100)
    expr(tt + 1.0, tt + 3.6, "choir", 100, 40)
    chord(tt, "piano", ps("D1", "D2", "A2", "F#3", "A3", "D4"), 3.8, 84, spread=0.01)
    for i, n in enumerate(["D5", "E5", "F#5", "A5", "D6", "E6"]):
        note(tt + 0.25 + 0.09 * i, "celesta", p(n), 1.4, 56 + 4 * i)

    # D. the natural rhythm: a quiet bed; a vibraphone note at each back-and-forth of the free swing
    r0 = S["rhythm_swing"][0]
    pl = P.pull_data(os.path.join(tl.BUILD, "data"))
    expr(r0, r0 + 0.1, "pad", 50, 50)
    expr(r0 + 0.1, r0 + 3.0, "pad", 50, 80)
    chord(r0, "pad", ps("D3", "A3", "E4", "F#4"), 6.0, 66)
    chord(r0 + 6.0, "pad", ps("G2", "D3", "B3", "F#4"), 6.4, 64)
    chord(r0 + 12.4, "pad", ps("B2", "F#3", "A3", "D4"), 6.0, 62)
    rel = r0 + float(pl["release"])
    tt_, om = pl["t"], pl["omega"]
    beats = [r0 + tt_[i] for i in range(1, len(tt_)) if tt_[i] > float(pl["release"]) + 0.1 and om[i - 1] < 0 <= om[i]]
    for j, b in enumerate([rel] + beats):
        if b < S["rhythm_swing"][1] - 0.3:
            note(b, "vibes", p("A5"), 1.8, 64 - 4 * j)
            note(b, "vibes", p("D5"), 1.8, 50 - 4 * j)
    # spring hero: a marimba note per oscillation, loudness follows the real decay
    h0 = S["spring_hero"][0]
    for k in range(0, 8):
        tk = h0 + 0.8 + k * 1.0 / math.sqrt(1 - P.ZETA ** 2)
        amp = math.exp(-P.ZETA * P.WN * (tk - h0 - 0.8))
        if tk < S["spring_model"][0] + 0.8:
            note(tk, "marimba", p("A4"), 0.8, 30 + 70 * amp)
    # k and m: three rigs, three rhythms (1 Hz A4, 2 Hz D5 higher and faster, 0.5 Hz D4 lower and slower)
    m0 = S["spring_model"][0]
    rigs = [(m0 + 2.3, 1.0, 1.0, "A4"), (at("L08", "A stiffer spring") + 0.2, 1.0, 4.0, "D5"),
            (at("L08", "A heavier mass") + 0.2, 4.0, 1.0, "D4")]
    for t_pl, mm, kk, pitch in rigs:
        mass, stiff = P.MASS * mm, P.STIFFNESS * kk
        wn = math.sqrt(stiff / mass)
        zeta = P.DAMPING / (2 * math.sqrt(stiff * mass))
        period = 2 * math.pi / (wn * math.sqrt(1 - zeta ** 2))
        k = 0
        while True:
            tk = t_pl + 0.35 + k * period
            if tk > S["sweep"][0] - 0.2:
                break
            amp = math.exp(-zeta * wn * (tk - t_pl - 0.35))
            note(tk, "marimba", p(pitch), min(0.8, period * 0.8), 24 + 64 * amp)
            k += 1
    chord(m0, "pad", ps("G2", "D3", "A3", "E4"), S["sweep"][0] - m0 + 0.5, 60)
    expr(m0, m0 + 1, "pad", 80, 64)

    # E. the sweep: the bed builds towards resonance, floats in slow motion, then falls away
    s0 = S["sweep"][0]
    t_res = at("L12")
    t_slow0, t_slow1 = at("L13") + 0.5, T["L13"][1] - 0.4
    t_fast = at("L14")
    d0 = S["damping"][0]
    secs = [(s0, at("L11") - 0.5, ps("E2", "B2", "E3", "G3", "B3"), 58),
            (at("L11") - 0.5, t_res - 0.3, ps("G2", "D3", "G3", "B3", "D4"), 66),
            (t_res - 0.3, t_slow0, ps("D2", "A2", "D3", "F#3", "A3", "E4"), 84),
            (t_slow0, t_slow1, ps("D3", "A3", "E4", "F#4", "A4"), 60),
            (t_slow1, t_fast + 1.5, ps("B1", "F#2", "B2", "D3", "F#3"), 62),
            (t_fast + 1.5, d0 + 0.3, ps("G1", "D2", "G2", "B2", "D3"), 56)]
    expr(s0, s0 + 0.1, "strings", 60, 60)
    expr(s0 + 0.1, t_res, "strings", 60, 108)
    expr(t_res + 0.5, t_slow0, "strings", 108, 88)
    expr(t_slow0, t_slow0 + 0.8, "strings", 88, 60)
    expr(t_slow1, t_fast + 3, "strings", 60, 70)
    expr(t_fast + 3, d0 + 0.3, "strings", 70, 50)
    for a, b, notes, v in secs:
        chord(a, "strings", notes, b - a + 0.4, v)
    # slow motion: time stretches, a high celesta line floats above
    for i, n in enumerate(["F#6", "E6", "D6", "A5", "E6", "D6"]):
        note(t_slow0 + 0.3 + i * 1.15, "celesta", p(n), 1.8, 50)
    note(t_res - 0.3, "timpani", p("D2"), 2.0, 72)
    # a low pulse under the sweep, one note per push (the push rhythm itself)
    import sc_model as smp  # noqa: E402 (knows the push times of the sweep)
    for tk, rr in smp.push_times():
        note(tk, "bass", p("D2"), 0.35, 42 + 20 * min(1.0, rr))

    # F. damping: a reflective line over the strings
    t15, t16, t17 = at("L15"), at("L16"), at("L17")
    b0 = S["bridge"][0]
    fprog = [(d0 + 0.3, t16 - 0.2, ps("G2", "D3", "G3", "B3")),
             (t16 - 0.2, at("L16", "Double the damping") - 0.2, ps("F#2", "D3", "F#3", "A3")),
             (at("L16", "Double the damping") - 0.2, at("L16", "At 30") - 0.2, ps("E2", "B2", "E3", "G3")),
             (at("L16", "At 30") - 0.2, t17 - 0.2, ps("A1", "E2", "A2", "C#3", "E3")),
             (t17 - 0.2, b0 + 0.2, ps("D2", "A2", "D3", "F#3", "A3"))]
    expr(d0 + 0.3, d0 + 2, "strings", 50, 72)
    expr(b0 - 2.0, b0 + 0.2, "strings", 72, 30)
    for a, b, notes in fprog:
        chord(a, "strings", notes, b - a + 0.4, 64)
        note(a, "piano", notes[0], b - a, 50)
    mel = [("B4", 0.0), ("A4", 1.2), ("F#4", 2.4), ("D4", 3.6), ("E4", 4.8)]
    for n, dt in mel:
        note(t15 + 1.0 + dt, "piano", p(n), 1.4, 46)
    for n, tz in (("A5", at("L16", "With 5")), ("F#5", at("L16", "Double the damping")), ("D5", at("L16", "At 30"))):
        note(tz + 0.1, "celesta", p(n), 1.6, 60)
    chord(t17 + 2.2, "piano", ps("D3", "A3", "D4", "F#4"), 3.0, 52, spread=0.08)

    # G. the bridge: walking pace, tension as the deck sways, the closure, the cure
    t18, t19, t20, t21 = at("L18"), at("L19"), at("L20"), at("L21")
    t_fit = at("L21", "Engineers fitted")
    t_02 = at("L21", "In 2002")
    expr(b0, b0 + 0.1, "strings", 30, 30)
    expr(b0 + 0.1, t18 + 2, "strings", 30, 70)
    chord(t18 - 0.2, "strings", ps("A1", "E2", "A2", "C#3", "E3"), t19 - t18 + 0.2, 62)
    k = 0
    tk = t18 + 0.2
    walk = ["A4", "C#5", "E5", "C#5", "B4", "D5", "E5", "D5"]
    while tk < t19 + 2.0:
        note(tk, "marimba", p(walk[k % 8]), 0.45, 44 if k % 2 == 0 else 34)
        tk += 0.5
        k += 1
    chord(t19, "pad", ps("A2", "E3", "A3", "B3"), t20 - t19 + 0.4, 58)
    # the sway grows: low cello tremolo swells, a pulse at the sway frequency (0.8 Hz)
    expr(t20 - 0.2, t20, "cello", 30, 30)
    expr(t20, t21, "cello", 30, 110)
    tk = t20
    while tk < t21 - 0.1:
        note(tk, "cello", p("E2"), 0.12, 70)
        tk += 0.125
    chord(t20, "strings", ps("E2", "B2", "E3", "A3", "B3"), t21 - t20, 66)
    expr(t20, t21 - 0.2, "strings", 60, 104)
    tk = t20 + 1.0
    k = 0
    while tk < t21 - 0.3:
        note(tk, "timpani", p("E2"), 0.6, 30 + 50 * min(1, k / 12))
        tk += 1 / 0.8
        k += 1
    # closed: a hit, then a breath of silence
    note(t21, "timpani", p("A1"), 2.2, 110)
    chord(t21, "piano", ps("A0", "A1", "E2"), 2.2, 92)
    expr(t21 + 0.1, t21 + 0.2, "strings", 104, 0)
    expr(t21 + 0.1, t21 + 0.2, "cello", 110, 0)
    # the cure: warm strings, the dampers pop in (celesta glissando), reopened in brightness
    expr(t_fit - 0.4, t_fit - 0.3, "strings", 0, 40)
    expr(t_fit - 0.3, t_fit + 3.0, "strings", 40, 92)
    chord(t_fit - 0.3, "strings", ps("D2", "A2", "D3", "F#3", "A3"), t_02 - t_fit + 0.3, 78)
    gl = ["D5", "E5", "F#5", "A5", "B5", "D6", "E6", "F#6", "A6"]
    for i in range(18):
        note(t_fit + 0.25 + i * 0.11, "celesta", p(gl[i % 9]) - (12 if i < 9 else 0), 0.9, 40 + i)
    chord(t_02, "strings", ps("A1", "E2", "A2", "C#3", "E3", "A3"), 2.2, 84)
    chord(t_02 + 1.8, "strings", ps("D2", "A2", "D3", "F#3", "A3", "D4"), S["bridge"][1] - t_02 - 1.2, 80)
    chord(t_02, "piano", ps("A2", "E3", "A3", "C#4", "E4"), 2.0, 62, spread=0.05)
    chord(t_02 + 1.8, "piano", ps("D2", "A2", "D3", "F#3", "A3", "D4"), 2.6, 66, spread=0.05)
    expr(S["bridge"][1] - 1.2, S["bridge"][1], "strings", 92, 30)

    # H. Taipei 101: majestic, then the quarter-beat canon
    ta0 = S["taipei"][0]
    t22, t23, t24 = at("L22"), at("L23"), at("L24")
    t_3d = at("L22", "Near the top") + 1.3
    expr(ta0, ta0 + 0.1, "choir", 0, 0)
    expr(ta0 + 0.1, t_3d, "choir", 0, 80)
    chord(ta0 + 0.1, "choir", ps("D3", "A3", "D4", "F4"), t_3d - ta0, 60)
    chord(ta0, "bass", ps("D1"), t_3d - ta0 + 0.3, 70)
    expr(ta0, ta0 + 0.1, "strings", 30, 30)
    expr(ta0 + 0.1, t_3d, "strings", 30, 80)
    chord(ta0, "strings", ps("D2", "A2", "D3", "F3"), t_3d - ta0, 64)
    maj = [(t_3d, ps("A#1", "F2", "A#2", "D3", "F3"), "A#3"), (t_3d + 2.6, ps("F1", "C2", "F2", "A2", "C3"), "A3"),
           (t_3d + 5.2, ps("G1", "D2", "G2", "A#2", "D3"), "D4"), (t_3d + 7.0, ps("A1", "E2", "A2", "C#3", "E3"), "C#4")]
    for i, (a, notes, top) in enumerate(maj):
        dur = (maj[i + 1][0] - a) if i + 1 < len(maj) else (t23 - a)
        chord(a, "strings", notes, dur + 0.3, 80)
        note(a, "choir", p(top), dur, 64)
        note(a, "timpani", notes[0] + 12, 1.5, 50 + 10 * i)
    # canon: strings swell with the tower (6.8 s), the choir a quarter beat (1.7 s) later
    per = P.TOWER_PERIOD
    lag = per / 4
    canon = [ps("D2", "A2", "D3", "F3", "A3"), ps("A#1", "F2", "A#2", "D3", "F3"), ps("C2", "G2", "C3", "E3", "G3"),
             ps("A1", "E2", "A2", "C#3", "E3")]
    tk = t23 - 0.2
    i = 0
    while tk < t24 - 0.1:
        notes = canon[i % 4]
        chord(tk, "strings", notes, per / 2 + 0.4, 76)
        expr(tk, tk + per / 4, "strings", 50, 104)
        expr(tk + per / 4, tk + per / 2, "strings", 104, 60)
        note(tk + lag, "choir", notes[-1] + 12, per / 2, 70)
        expr(tk + lag, tk + lag + per / 4, "choir", 40, 96)
        expr(tk + lag + per / 4, tk + lag + per / 2, "choir", 96, 50)
        tk += per / 2
        i += 1
    # resonance used to fight resonance: resolve to D major
    chord(t24, "strings", ps("D2", "A2", "D3", "F#3", "A3", "D4"), S["taipei"][1] - t24 + 0.5, 84)
    expr(t24, t24 + 0.5, "strings", 70, 96)
    chord(t24, "choir", ps("F#4", "A4", "D5"), S["taipei"][1] - t24, 70)
    for i, n in enumerate(["A5", "D6", "F#6"]):
        note(t24 + 0.3 + 0.15 * i, "celesta", p(n), 1.5, 58)
    expr(S["taipei"][1] - 1.0, S["taipei"][1], "strings", 96, 40)
    expr(S["taipei"][1] - 1.0, S["taipei"][1], "choir", 90, 30)

    # I. the takeaway: the final cadence, a bell, silence
    k0 = S["takeaway"][0]
    t25 = at("L25")
    e25 = T["L25"][1]
    expr(k0, k0 + 0.1, "strings", 40, 40)
    expr(k0 + 0.1, e25, "strings", 40, 86)
    expr(k0, k0 + 0.1, "choir", 30, 30)
    expr(k0 + 0.1, e25, "choir", 30, 70)
    chord(k0, "strings", ps("G2", "D3", "G3", "B3"), 2.2, 70)
    chord(k0 + 2.2, "strings", ps("A2", "E3", "A3", "C#4"), e25 - k0 - 2.2, 74)
    chord(e25, "strings", ps("D2", "A2", "D3", "F#3", "A3", "E4"), 6.0, 84)
    chord(e25, "choir", ps("D4", "F#4", "A4"), 5.5, 66)
    melody = [("A4", 0.0), ("B4", 0.55), ("A4", 1.1), ("F#4", 1.65), ("E4", 2.4), ("D4", 3.2)]
    for n, dt in melody:
        note(t25 + dt, "piano", p(n), 0.9, 58)
    chord(e25, "piano", ps("D2", "A2", "D3", "F#3", "A3", "D4", "E4"), 5.0, 70, spread=0.06)
    for i, n in enumerate(["D5", "F#5", "A5", "D6", "F#6", "A6"]):
        note(e25 + 0.4 + 0.12 * i, "celesta", p(n), 2.4, 60 - 2 * i)
    note(e25 + 1.4, "vibes", p("D6"), 4.0, 60)
    expr(e25 + 2.0, S["takeaway"][1], "strings", 86, 0)
    expr(e25 + 2.0, S["takeaway"][1], "choir", 70, 0)


def write_midi(path):
    mid = mido.MidiFile(ticks_per_beat=480)
    tr = mido.MidiTrack()
    mid.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=500000))      # 120 BPM: 960 ticks per second
    for name, (c, prog, vol, pan, rev) in CH.items():
        tr.append(mido.Message("program_change", channel=c, program=prog, time=0))
        tr.append(mido.Message("control_change", channel=c, control=7, value=vol, time=0))
        tr.append(mido.Message("control_change", channel=c, control=10, value=pan, time=0))
        tr.append(mido.Message("control_change", channel=c, control=91, value=rev, time=0))
        tr.append(mido.Message("control_change", channel=c, control=93, value=20, time=0))
        tr.append(mido.Message("control_change", channel=c, control=11, value=100, time=0))
    order = {"off": 0, "cc": 1, "on": 2}
    evs = sorted(EVENTS, key=lambda e: (e[0], order[e[1]]))
    last = 0
    active = {}          # (channel, pitch) -> id of the note that owns it
    for t, kind, c, a, b, nid in evs:
        tick = max(0, int(round(t * 960)))
        dt = max(0, tick - last)
        last = max(last, tick)
        if kind == "on":
            if (c, a) in active:
                # the same pitch is still sounding: re-strike it instead of letting the old note-off cut it
                tr.append(mido.Message("note_off", channel=c, note=a, velocity=0, time=dt))
                dt = 0
            active[(c, a)] = nid
            tr.append(mido.Message("note_on", channel=c, note=a, velocity=b, time=dt))
        elif kind == "off":
            if active.get((c, a)) == nid:
                del active[(c, a)]
                tr.append(mido.Message("note_off", channel=c, note=a, velocity=0, time=dt))
            elif dt:
                last -= dt          # nothing sent: keep the running time unchanged
        else:
            tr.append(mido.Message("control_change", channel=c, control=a, value=max(0, min(127, b)), time=dt))
    mid.save(path)


def main():
    out = sys.argv[1]
    score()
    with tempfile.TemporaryDirectory() as d:
        midi = os.path.join(d, "score.mid")
        write_midi(midi)
        subprocess.run(["fluidsynth", "-ni", "-g", "0.5", "-r", "48000", "-o", "synth.reverb.active=1",
                        "-o", "synth.reverb.room-size=0.75", "-o", "synth.reverb.width=0.9",
                        "-o", "synth.reverb.level=0.5", "-o", "synth.chorus.active=0",
                        "-F", out, SOUNDFONT, midi], check=True, capture_output=True)
        import shutil
        shutil.copy(midi, os.path.splitext(out)[0] + ".mid")
    print("music written:", out, len(EVENTS), "events")


if __name__ == "__main__":
    main()
