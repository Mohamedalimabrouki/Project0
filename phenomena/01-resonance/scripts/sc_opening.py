"""
Resonance - opening scenes: series ident, the two swings (hook), the title card,
and the single swing that shows its natural rhythm.
"""

import math

import numpy as np
import skia

from sc_common import (W, H, S, T, at, end, col, paint, ramp, smooth, fade, ease_out, ease_in_out,
                       ease_out_back, ep, fx, sh, draw_render, pt, swings, pull, label_box, caption, note,
                       bottom_gradient, top_gradient, tex_box, unit, leader)

HOOK0 = S["hook"][0]                  # global time of hook frame 0
RHY0 = S["rhythm_swing"][0]
PUSH_LEN = 84.0

_tex_cache = {}


def tex(key, latex, size):
    if key not in _tex_cache:
        _tex_cache[key] = ep.Tex(latex, size)
    return _tex_cache[key]


# ------------------------------------------------------------------ ident

def draw_ident(c, t):
    fx.background(c)
    a_out = 1 - smooth(ramp(t, 2.0, 2.6))
    fx.colour_bar(c, H - 8, 8, alpha=a_out, progress=ease_out(ramp(t, 0.1, 1.2)))
    name = ep.Text("ENGINEERING PHENOMENA", 30, "semibold", 30 * 0.32)
    n = len(name.glyphs)
    reveal = ramp(t, 0.25, 1.1)

    def ga(i):
        return smooth(reveal * (n + 4) / 4 - i / 4) * a_out

    name.draw(c, W / 2, H / 2 - 6, col("highlight"), anchor="center", alpha_per_glyph=ga)
    ep_no = ep.Text("Episode 01", 26, "medium")
    ep_no.draw(c, W / 2, H / 2 + 50, col("steel", fade(t, 0.8, None, 0.5) * a_out), anchor="center")
    w = 420 * ease_out(ramp(t, 0.5, 1.3))
    c.drawLine(W / 2 - w / 2, H / 2 + 14, W / 2 + w / 2, H / 2 + 14, paint(col("steel", 0.5 * a_out), stroke=True, width=1.5))


# ------------------------------------------------------------------ hook: two swings

def _push_arrows(c, u, fi, side, first_label_alpha=0.0):
    d = swings()
    pushes = d[f"{side}_pushes"]
    seat = pt("hook", fi, f"{side}_seat")
    ahead = pt("hook", fi, f"{side}_seat_ahead")
    ux, uy = unit((ahead[0] - seat[0], ahead[1] - seat[1]))
    for tp in pushes:
        if tp - 0.05 <= u < tp + 0.6:
            f = math.sin(math.pi * (u - tp) / 0.35) if tp <= u < tp + 0.35 else 0.0
            if f > 0.01:
                L = PUSH_LEN * f
                tip = (seat[0] - ux * 16, seat[1] - uy * 16)
                tail = (tip[0] - ux * (L + 10), tip[1] - uy * (L + 10))
                sh.arrow_force(c, tail, tip, width=13.0)
            # contact flash
            k = ramp(u, tp, tp + 0.5)
            if 0 < k < 1:
                r = 10 + 34 * ease_out(k)
                c.drawCircle(seat[0] - ux * 12, seat[1] - uy * 12, r,
                             paint(col("force", 0.55 * (1 - k)), stroke=True, width=2.5))
    return seat, (ux, uy)


def _strip(c, u, side, x0, x1, yb, alpha):
    d = swings()
    t = d["t"]
    th = d[f"{side}_theta"]
    pushes = d[f"{side}_pushes"]
    work = d[f"{side}_work"]
    t_max = 21.0
    sx = (x1 - x0) / t_max
    sy = 1.45 * 180 / math.pi           # px per rad (1.45 px per degree)
    c.drawLine(x0, yb, x1, yb, paint(col("steel", 0.28 * alpha), stroke=True, width=1.2))
    # angle trace
    m = t <= u
    if np.count_nonzero(m) > 2:
        idx = np.nonzero(m)[0][::3]
        path = skia.Path()
        path.moveTo(x0 + t[idx[0]] * sx, yb - th[idx[0]] * sy)
        for i in idx[1:]:
            path.lineTo(x0 + t[i] * sx, yb - th[i] * sy)
        i_last = np.nonzero(m)[0][-1]
        path.lineTo(x0 + t[i_last] * sx, yb - th[i_last] * sy)
        c.drawPath(path, paint(col("motion", 0.45 * alpha), stroke=True, width=6, blur=4))
        c.drawPath(path, paint(col("motion", alpha), stroke=True, width=2.6))
        c.drawCircle(x0 + t[i_last] * sx, yb - th[i_last] * sy, 5, paint(col("paper", alpha)))
    # pushes and the energy each one added
    w_scale = 22.0 / max(np.max(np.abs(swings()["rhythm_work"])), 1e-9)
    ye = yb + 78
    c.drawLine(x0, ye, x1, ye, paint(col("steel", 0.2 * alpha), stroke=True, width=1))
    for tp, wk in zip(pushes, work):
        if tp <= u:
            X = x0 + tp * sx
            k = ease_out(ramp(u, tp, tp + 0.35))
            c.drawLine(X, yb - 10, X, yb + 10, paint(col("force", alpha), stroke=True, width=3))
            if u > tp + 0.35:
                kk = ease_out_back(ramp(u, tp + 0.35, tp + 0.75))
                h = wk * w_scale * kk
                if abs(h) < 5 * kk:
                    h = 5 * kk * (1 if wk > 0 else -1)
                rect = skia.Rect.MakeLTRB(X - 7, ye - max(h, 0), X + 7, ye - min(h, 0))
                if wk > 0:
                    # energy added: a filled bar pointing up
                    c.drawRect(rect, paint(col("energy", alpha)))
                    ep.Text("+", 20, "bold").draw(c, X, ye - h - 8, col("energy", alpha * kk), anchor="center")
                else:
                    # energy taken away: an outlined bar pointing down
                    c.drawRect(rect, paint(col("energy", alpha), stroke=True, width=2))
                    ep.Text("−", 22, "bold").draw(c, X, ye - h + 24, col("energy", alpha * kk), anchor="center")


def draw_hook(c, t, overlay_alpha=1.0):
    u = t - HOOK0
    fi = draw_render(c, "hook", u)
    d = swings()
    top_gradient(c, 250, 0.7)
    bottom_gradient(c, 610, 0.96)
    a = overlay_alpha
    # divider
    grow = ease_in_out(ramp(t, 2.6, 3.6))
    c.drawLine(W / 2, 580 - 420 * grow, W / 2, 580 + 430 * grow, paint(col("steel", 0.35 * a), stroke=True, width=1.5))
    # captions
    a_same = fade(t, at("L01") - 0.1, at("L02") + 0.2, 0.5, 0.5) * a
    if a_same > 0:
        caption(c, "Two identical swings  ·  identical pushes", W / 2, 88, 22, "steel", a_same, anchor="center")
    for side, cx, t_in, title, sub in (
            ("rhythm", 480, at("L02"), "Pushed in rhythm", "one push per swing, always at the same moment"),
            ("random", 1440, at("L02", "On the right"), "Pushed at random", "the same pushes, at random moments")):
        al = fade(t, t_in, None, 0.5) * a
        if al > 0:
            dy = 14 * (1 - ease_out(ramp(t, t_in, t_in + 0.6)))
            caption(c, title, cx, 92 + dy, 26, "paper", al, anchor="center")
            note(c, sub, cx, 132 + dy, 22, "steel", al, anchor="center")
    # push arrows
    for side in ("rhythm", "random"):
        _push_arrows(c, u, fi, side)
    # first push: name the arrow once (house rule)
    tp0 = d["rhythm_pushes"][0]
    al = fade(u, tp0 - 0.05, tp0 + 1.9, 0.2, 0.5) * a
    if al > 0:
        for side in ("rhythm", "random"):
            seat = pt("hook", fi, f"{side}_seat")
            tex_f = ep.Tex(r"\cf{F}", 36)
            tex_f.draw(c, seat[0] - 120, seat[1] - 40, col("force", al))
            note(c, "same push", seat[0] - 128, seat[1] + 58, 20, "force", al)
    # strips
    a_strip = fade(t, 3.4, None, 0.8) * a
    if a_strip > 0:
        _strip(c, u, "rhythm", 110, 850, 905, a_strip)
        _strip(c, u, "random", 1070, 1810, 905, a_strip)
        for x0 in (110, 1070):
            note(c, "angle", x0, 836, 18, "motion", a_strip, style="semibold")
            note(c, "push", x0 + 66, 836, 18, "force", a_strip, style="semibold")
            note(c, "energy from each push:  + added,  \u2212 taken away", x0 + 124, 836, 18, "energy", a_strip, style="semibold")
    # the result
    t_res = at("L03", "A very different result")
    al = fade(t, t_res - 0.1, None, 0.4) * a
    if al > 0:
        for side, cx in (("rhythm", 480), ("random", 1440)):
            th = d[f"{side}_theta"][d["t"] <= min(u, 21.0)]
            mx = np.degrees(np.max(np.abs(th))) if len(th) else 0.0
            k = ease_out_back(ramp(t, t_res, t_res + 0.5))
            label_box(c, cx, 200, f"highest swing  {mx:.0f}°", 26, "highlight", 0.8, "semibold",
                      anchor="center", alpha=al * min(1, k))


# ------------------------------------------------------------------ title card

def draw_title(c, t):
    t0 = S["title"][0]
    hook_end = HOOK0 + 21.2
    b = 22 * smooth(ramp(t, t0, t0 + 1.0))
    p = skia.Paint()
    if b > 0.3:
        p.setImageFilter(skia.ImageFilters.Blur(b, b))
    c.saveLayer(None, p)
    overlay_a = 1 - smooth(ramp(t, t0, t0 + 0.6))
    draw_hook(c, min(t, hook_end), overlay_alpha=overlay_a)
    c.restore()
    dim = 0.62 * smooth(ramp(t, t0, t0 + 1.0)) + 0.3 * smooth(ramp(t, t0 + 2.2, t0 + 3.6))
    c.drawRect(skia.Rect.MakeWH(W, H), paint(col("ink", min(0.95, dim))))
    fx.grid_overlay(c, grid_alpha=0.05 * smooth(ramp(t, t0, t0 + 1.2)))
    a_out = 1 - smooth(ramp(t, S["title"][1] - 0.7, S["title"][1] - 0.1))
    tl = at("L04")
    # series line
    sr = ep.Text("ENGINEERING PHENOMENA  ·  EPISODE 01", 22, "semibold", 22 * 0.3)
    sr.draw(c, W / 2, 380, col("highlight", fade(t, tl - 0.3, None, 0.5) * a_out), anchor="center")
    # the word
    word = ep.Text("Resonance", 168, "display-bold", -4)
    n = len(word.glyphs)
    rv = ramp(t, tl + 0.05, tl + 0.95)

    def ga(i):
        return smooth(rv * (n + 3) / 3 - i / 3) * a_out

    def go(i):
        k = smooth(rv * (n + 3) / 3 - i / 3)
        return (0.0, 26 * (1 - k))

    word.draw(c, W / 2, 575, col("paper"), anchor="center", alpha_per_glyph=ga, offset_per_glyph=go)
    tag = ep.Text("Why tiny pushes make huge movements", 40, "regular")
    tag.draw(c, W / 2, 650, col("steel", fade(t, tl + 0.9, None, 0.6) * a_out), anchor="center")
    # the resonance curve, drawn under the title (same curve as the banner)
    x0, x1, yb = 660, 1260, 850
    u = ease_in_out(ramp(t, tl + 0.4, tl + 2.0))
    if u > 0:
        rs = np.linspace(0, 2, 400)
        amp = P_amp(rs)
        pts = [(x0 + (x1 - x0) * r / 2, yb - 150 * a_ / 10.5) for r, a_ in zip(rs, amp)]
        path = ep.polyline_path(pts)
        path = ep.trim_path(path, u)
        c.drawLine(x0, yb, x1, yb, paint(col("steel", 0.5 * a_out), stroke=True, width=2))
        c.drawPath(path, paint(col("motion", 0.5 * a_out), stroke=True, width=9, blur=6))
        c.drawPath(path, paint(col("motion", a_out), stroke=True, width=3.5))
        k = ease_out_back(ramp(t, tl + 1.7, tl + 2.2))
        if k > 0:
            c.drawCircle((x0 + x1) / 2, yb - 150 * 10.0 / 10.5, 8 * k, paint(col("highlight", a_out)))


def P_amp(r):
    import physics as P
    return P.amplification(r, 0.05)


# ------------------------------------------------------------------ one swing: its natural rhythm

def draw_rhythm(c, t):
    u = t - RHY0
    fi = draw_render(c, "rhythm", u)
    p = pull()
    rel = float(p["release"])
    bottom_gradient(c, 720, 0.9)
    seat = pt("rhythm", fi, "rhythm_seat")
    ahead = pt("rhythm", fi, "rhythm_seat_ahead")
    ux, uy = unit((ahead[0] - seat[0], ahead[1] - seat[1]))
    # the pull: a hand pulls the seat back (force arrow), then lets go
    a_pull = smooth(ramp(u, 3.2, 3.5)) * (1 - smooth(ramp(u, rel, rel + 0.12)))
    if a_pull > 0:
        base = (seat[0] - ux * 18, seat[1] - uy * 18)
        tip = (base[0] - ux * 92 * a_pull, base[1] - uy * 92 * a_pull)
        sh.arrow_force(c, base, tip, width=13, alpha=a_pull)
        note(c, "pull", tip[0] - 70, tip[1] - 16, 24, "force", a_pull, style="semibold")
    k = ramp(u, rel, rel + 0.7)
    if 0 < k < 1:
        c.drawCircle(seat[0], seat[1], 12 + 50 * ease_out(k), paint(col("paper", 0.6 * (1 - k)), stroke=True, width=2.5))
        note(c, "let go", seat[0] + 40, seat[1] - 40, 24, "paper", (1 - k), style="semibold")
    # time strip after release: angle trace + one tick per swing
    a_s = fade(u, rel - 0.2, None, 0.5)
    if a_s > 0:
        x0, x1, yb = 190, 1730, 930
        tt = p["t"]
        th = p["theta"]
        sx = (x1 - x0) / (12.9 - rel)
        sy = 1.9 * 180 / math.pi
        c.drawLine(x0, yb, x1, yb, paint(col("steel", 0.28 * a_s), stroke=True, width=1.2))
        m = (tt >= rel) & (tt <= u)
        if np.count_nonzero(m) > 2:
            idx = np.nonzero(m)[0]
            path = skia.Path()
            path.moveTo(x0 + (tt[idx[0]] - rel) * sx, yb - th[idx[0]] * sy)
            for i in idx[1::3]:
                path.lineTo(x0 + (tt[i] - rel) * sx, yb - th[i] * sy)
            i = idx[-1]
            path.lineTo(x0 + (tt[i] - rel) * sx, yb - th[i] * sy)
            c.drawPath(path, paint(col("motion", 0.45 * a_s), stroke=True, width=6, blur=4))
            c.drawPath(path, paint(col("motion", a_s), stroke=True, width=2.8))
            c.drawCircle(x0 + (tt[i] - rel) * sx, yb - th[i] * sy, 5, paint(col("paper", a_s)))
        # back turning points: the beat
        om = p["omega"]
        beats = [tt[i] for i in range(1, len(tt)) if tt[i] > rel + 0.1 and om[i - 1] < 0 <= om[i]]
        beats = [rel] + beats
        for j, tb in enumerate(beats):
            if tb <= u:
                X = x0 + (tb - rel) * sx
                kk = ease_out_back(ramp(u, tb, tb + 0.3))
                c.drawLine(X, yb + 34, X, yb + 34 - 22 * kk, paint(col("paper", 0.85 * a_s), stroke=True, width=3))
        # period brackets, named when the narrator says "2.8 seconds"
        t_per = at("L06", "2.8 seconds")
        for j in range(len(beats) - 1):
            ta, tb = beats[j], beats[j + 1]
            if tb <= u:
                Xa, Xb = x0 + (ta - rel) * sx, x0 + (tb - rel) * sx
                kk = ease_out(ramp(u, tb, tb + 0.4))
                yy = yb + 58
                c.drawLine(Xa, yy, Xa + (Xb - Xa) * kk, yy, paint(col("steel", 0.8 * a_s), stroke=True, width=2))
                for X in (Xa, Xa + (Xb - Xa) * kk):
                    c.drawLine(X, yy - 7, X, yy + 7, paint(col("steel", 0.8 * a_s), stroke=True, width=2))
                hl = fade(t, t_per - 0.1, None, 0.3)
                colr = ep.mix_hex("steel", "highlight", hl)
                ep.Text(f"{tb - ta:.2f} s", 22, "semibold").draw(c, (Xa + Xb) / 2, yy + 32,
                                                               col(colr, a_s * kk), anchor="center")
        note(c, "angle of the swing", x0, 836, 18, "motion", a_s, style="semibold")
        note(c, "one tick per back-and-forth", x0 + 190, 836, 18, "paper", a_s * 0.8, style="semibold")
    # dimension: the chain is 2 m long
    a_dim = fade(t, at("L06", "2-metre") - 0.15, S["rhythm_swing"][1] - 0.4, 0.4, 0.4)
    if a_dim > 0:
        p0 = pt("rhythm", fi, "rhythm_pivot")
        p1 = pt("rhythm", fi, "rhythm_seat")
        v = unit((p1[0] - p0[0], p1[1] - p0[1]))
        n = (-v[1], v[0])
        off = -58
        a0 = (p0[0] + n[0] * off, p0[1] + n[1] * off)
        a1 = (p1[0] + n[0] * off, p1[1] + n[1] * off)
        grow = ease_out(ramp(t, at("L06", "2-metre") - 0.15, at("L06", "2-metre") + 0.45))
        a1g = (a0[0] + (a1[0] - a0[0]) * grow, a0[1] + (a1[1] - a0[1]) * grow)
        sh.dimension_line(c, a0, a1g, None, col("paper", a_dim), tick=9)
        if grow > 0.95:
            mid = ((a0[0] + a1[0]) / 2 + n[0] * -52, (a0[1] + a1[1]) / 2 + n[1] * -52)
            label_box(c, mid[0], mid[1], "L = 2 m", 26, "paper", 0.85, "semibold", anchor="center", alpha=a_dim)
    # engineers' corner: the pendulum formula
    a_eq = fade(t, at("L06", "2.8 seconds") - 0.2, S["rhythm_swing"][1] - 0.4, 0.5, 0.4)
    if a_eq > 0:
        eq = tex_cached("pend", r"T = 2\pi\sqrt{\frac{L}{g}} = 2\pi\sqrt{\frac{2\unit{m}}{9.81\unit{m/s^2}}} \approx 2.84\unit{s}", 38)
        tex_box(c, 1180, 250, eq, alpha=a_eq)
        note(c, "ideal pendulum, small swings", 1180, 335, 20, "steel", a_eq)


def tex_cached(key, latex, size):
    return tex(key, latex, size)
