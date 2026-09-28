"""
Resonance - Taipei 101 and its tuned mass damper, then the closing card.

Facts (see README sources): 508 m to the tip, completed 2004; a 660 t steel
ball, 5.5 m wide, 41 plates of 125 mm, hanging from the 92nd floor between
floors 87 and 92, on 8 cables, with 8 hydraulic dampers underneath; the tower
sways at about 0.15 Hz (6.8 s). The operator quotes up to about 40 % less sway.

The phase diagram uses physics.tmd_steady_state (Den Hartog tuning, mass
ratio 1.25 %): at the tower's own rhythm the ball lags by about 90°, so the
force it puts on the tower points against the tower's velocity.
"""

import functools
import math

import numpy as np
import skia

import physics as P
from sc_common import (W, H, S, T, at, end, col, paint, ramp, smooth, fade, ease_out, ease_in_out,
                       ease_out_back, ep, fx, sh, draw_render, pt, label_box, caption, note, tex_box,
                       exaggeration_tag, leader, unit)

TA0, TA1 = S["taipei"]
T22, T23, T24 = at("L22"), at("L23"), at("L24")
T_NEAR = at("L22", "Near the top")
T_TUNED = at("L22", "tuned to")
T_3D0 = T_NEAR + 1.3                  # the 3D shot starts here
T_3D1 = T23 + 0.1                     # and hands over to the diagram here

# ------------------------------------------------------------------ the tower outline (metres)


@functools.lru_cache(maxsize=1)
def tower_outline():
    """Stylised Taipei 101 elevation in metres: podium base, 8 flared blocks, top, spire."""
    left, right = [], []

    def seg(z0, z1, w0, w1):
        left.extend([(-w0 / 2, z0), (-w1 / 2, z1)])
        right.extend([(w0 / 2, z0), (w1 / 2, z1)])

    seg(0, 100, 62, 44)                      # tapered base (floors 1 to 25)
    z = 100
    for i in range(8):                       # 8 blocks of 8 floors, each flaring outward
        seg(z, z + 34, 38, 50)
        z += 34
    seg(z, z + 18, 34, 30)                   # top floors
    seg(z + 18, z + 40, 24, 20)
    seg(z + 40, z + 76, 10, 6)
    seg(z + 76, 508, 3.2, 1.0)               # spire
    return left, right


def tower_path(cx, ground_y, px_per_m, bend_top_px=0.0, clip_h=None):
    left, right = tower_outline()
    Hm = 508.0

    def X(x, z):
        d = bend_top_px * (1 - math.cos(math.pi * z / (2 * Hm)))
        return cx + x * px_per_m + d

    pts = []
    for x, z in left:
        if clip_h is not None and z > clip_h:
            z = clip_h
        pts.append((X(x, z), ground_y - z * px_per_m))
    for x, z in reversed(right):
        if clip_h is not None and z > clip_h:
            z = clip_h
        pts.append((X(x, z), ground_y - z * px_per_m))
    return ep.polyline_path(pts, closed=True)


def draw_tower(c, cx, ground_y, pxm, alpha, bend=0.0, clip_h=None, fill_alpha=0.28, window=None):
    path = tower_path(cx, ground_y, pxm, bend, clip_h)
    c.drawPath(path, paint(col("steel", fill_alpha * alpha)))
    c.drawPath(path, paint(col("paper", 0.8 * alpha), stroke=True, width=2.2))
    # floor bands of the 8 blocks
    for i in range(1, 9):
        z = 100 + 34 * i
        if clip_h is not None and z > clip_h:
            break
        d = bend * (1 - math.cos(math.pi * z / (2 * 508)))
        y = ground_y - z * pxm
        c.drawLine(cx - 25 * pxm + d, y, cx + 25 * pxm + d, y, paint(col("paper", 0.35 * alpha), stroke=True, width=1.2))


# ------------------------------------------------------------------ part A: the tower

def draw_part_tower(c, t, alpha):
    fx.background(c)
    ground_y, pxm, cx = 960.0, 1.6, 960.0
    grow = ease_in_out(ramp(t, TA0 + 0.2, TA0 + 2.4))
    c.drawLine(560, ground_y, 1360, ground_y, paint(col("steel", 0.7 * alpha), stroke=True, width=2))
    draw_tower(c, cx, ground_y, pxm, alpha, clip_h=508 * grow)
    a_cap = fade(t, T22 - 0.1, None, 0.5) * alpha
    caption(c, "Taipei 101", 96, 110, 24, "paper", a_cap)
    note(c, "508 m to the tip  ·  completed 2004", 96, 150, 24, "steel", a_cap)
    a_d = fade(t, TA0 + 2.2, None, 0.5) * alpha
    if a_d > 0:
        sh.dimension_line(c, (1110, ground_y), (1110, ground_y - 508 * pxm * ease_out(ramp(t, TA0 + 2.2, TA0 + 3.2))),
                          None, col("steel", a_d), tick=8)
        label_box(c, 1140, ground_y - 254 * pxm, "508 m", 26, "paper", 0.8, "semibold", alpha=a_d)
    a_b = fade(t, T_NEAR - 0.1, None, 0.4) * alpha
    if a_b > 0:
        z0, z1 = 360, 395
        r = skia.Rect.MakeLTRB(cx - 50, ground_y - z1 * pxm, cx + 50, ground_y - z0 * pxm)
        k = ease_out_back(ramp(t, T_NEAR - 0.1, T_NEAR + 0.4))
        c.drawRect(r, paint(col("highlight", a_b), stroke=True, width=2.5 * k))
        label_box(c, cx - 70, ground_y - 378 * pxm, "the damper: floors 87 to 92", 24, "highlight", 0.8,
                  "semibold", anchor="right", alpha=a_b)


def draw_taipei_intro(c, t):
    zoom_k = ease_in_out(ramp(t, T_NEAR + 0.5, T_3D0 + 0.7))
    if zoom_k > 0:
        s = 1 + 9 * zoom_k
        fx_, fy = 960.0, 960.0 - 378 * 1.6
        c.save()
        c.translate(fx_, fy)
        c.scale(s, s)
        c.translate(-fx_, -fy)
        draw_part_tower(c, t, 1.0 - zoom_k * 0.6)
        c.restore()
    else:
        draw_part_tower(c, t, 1.0)


# ------------------------------------------------------------------ part B: the ball (3D)

def draw_ball(c, t, alpha=1.0):
    u = t - T_3D0
    fi = draw_render(c, "taipei", u)
    from sc_common import bottom_gradient, top_gradient
    top_gradient(c, 220, 0.55)
    a1 = fade(t, T_3D0 + 0.8, None, 0.5)
    if a1 > 0:
        top = pt("taipei", fi, "right")
        lp = (top[0] + 120, top[1] - 170)
        leader(c, top, lp, alpha=a1)
        label_box(c, lp[0] + 6, lp[1], "660 t steel ball", 30, "paper", 0.82, "semibold", alpha=a1)
        note(c, "5.5 m wide  ·  41 steel plates, 125 mm each", lp[0] + 8, lp[1] + 52, 22, "steel", a1)
    a2 = fade(t, T_3D0 + 2.0, None, 0.5)
    if a2 > 0:
        L = pt("taipei", fi, "left")
        R = pt("taipei", fi, "right")
        y = max(L[1], R[1]) + 40
        grow = ease_out(ramp(t, T_3D0 + 2.0, T_3D0 + 2.7))
        sh.dimension_line(c, (L[0], y), (L[0] + (R[0] - L[0]) * grow, y), None, col("paper", a2), tick=9)
        if grow > 0.95:
            label_box(c, (L[0] + R[0]) / 2, y, "5.5 m", 24, "paper", 0.85, "semibold", anchor="center", alpha=a2)
    a3 = fade(t, T_3D0 + 3.1, None, 0.5)
    if a3 > 0:
        cab = pt("taipei", fi, "cable_top")
        leader(c, cab, (cab[0] - 160, cab[1] - 40), alpha=a3)
        label_box(c, cab[0] - 166, cab[1] - 40, "hung on 8 steel cables", 24, "paper", 0.82, "semibold",
                  anchor="right", alpha=a3)
        d = pt("taipei", fi, "damper")
        leader(c, d, (d[0] - 60, d[1] - 120), alpha=a3)
        label_box(c, d[0] - 66, d[1] - 120, "8 hydraulic dampers", 24, "balance", 0.82, "semibold",
                  anchor="right", alpha=a3)
    a4 = fade(t, T_TUNED - 0.1, None, 0.5)
    if a4 > 0:
        label_box(c, 960, 990, "tuned to the tower's own sway: about 6.8 s per swing", 28, "highlight", 0.82,
                  "semibold", anchor="center", alpha=a4)


# ------------------------------------------------------------------ part C: the quarter beat

@functools.lru_cache(maxsize=1)
def tmd_phasors():
    X, Y = P.tmd_steady_state(1.0)
    return X, Y


def tmd_state(t):
    X, Y = tmd_phasors()
    w = P.TOWER_WN
    ph = w * (t - T23)
    env = smooth(ramp(t, T23 - 0.3, T23 + 1.5))
    x = env * np.real(X * np.exp(1j * ph)) / abs(X)
    y = env * np.real(Y * np.exp(1j * ph)) / abs(X)
    xd = env * np.real(1j * w * X * np.exp(1j * ph)) / (abs(X) * w)
    # force of the damper on the tower: -m_d * (ball acceleration), normalised
    fb = env * np.real(-(1j * w) ** 2 * Y * np.exp(1j * ph) * -1) / (abs(Y) * w * w)
    return x, y, xd, -fb


def draw_quarter_beat(c, t, alpha):
    fx.background(c)
    x, y, xd, fb = tmd_state(t)
    ground_y, pxm, cx = 980.0, 1.35, 520.0
    bend_px = 60 * x                                     # exaggerated
    # wind (sky blue = air flow)
    for j in range(7):
        yy = 260 + j * 95
        ph = (t * 0.55 + j * 0.37) % 1.0
        x0 = 60 + ph * 300
        path = skia.Path()
        path.moveTo(x0, yy)
        path.cubicTo(x0 + 60, yy - 10, x0 + 120, yy + 10, x0 + 180, yy)
        a_w = alpha * math.sin(math.pi * ph) * 0.7 * fade(t, T23 - 0.2, None, 0.6)
        c.drawPath(path, paint(col("fluid", a_w), stroke=True, width=3, cap="round"))
    note(c, "wind", 70, 225, 24, "fluid", alpha * fade(t, T23 - 0.2, None, 0.6), style="semibold")
    c.drawLine(300, ground_y, 740, ground_y, paint(col("steel", 0.7 * alpha), stroke=True, width=2))
    draw_tower(c, cx, ground_y, pxm, alpha, bend=bend_px, fill_alpha=0.18)
    # the ball hangs inside the tower near the top (cutaway), pendulum from a pivot
    zb = 378
    d_b = bend_px * (1 - math.cos(math.pi * zb / (2 * 508)))
    piv = (cx + d_b, ground_y - (zb + 30) * pxm)
    X_, Y_ = tmd_phasors()
    rel_scale = 42.0 / abs(Y_ - X_) * abs(X_)            # relative swing drawn at +-42 px (not to scale)
    ball = (cx + d_b + rel_scale * (y - x), ground_y - zb * pxm + 6)
    win = skia.RRect.MakeRectXY(skia.Rect.MakeLTRB(piv[0] - 78, piv[1] - 14, piv[0] + 78, piv[1] + 84), 10, 10)
    c.drawRRect(win, paint(col("ink", 0.9 * alpha)))
    c.drawRRect(win, paint(col("highlight", 0.6 * alpha), stroke=True, width=1.8))
    c.drawLine(piv[0], piv[1], ball[0], ball[1], paint(col("paper", 0.8 * alpha), stroke=True, width=2))
    glow = fade(t, T24 - 0.2, None, 0.5)
    if glow > 0:
        c.drawCircle(ball[0], ball[1], 34, paint(col("highlight", 0.5 * glow * alpha), blur=14))
    c.drawCircle(ball[0], ball[1], 20, paint(col("#D9A93A", alpha)))
    c.drawCircle(ball[0], ball[1], 20, paint(col("paper", 0.6 * alpha), stroke=True, width=1.5))
    # arrows at the pivot: tower velocity (blue) and the ball's pull on the tower (vermillion)
    a_ar = alpha * fade(t, at("L23", "so its pull") - 0.2, None, 0.5)
    if a_ar > 0:
        ax_ = piv[0] + 190
        c.drawLine(piv[0] + 70, piv[1] + 30, ax_ - 70, piv[1] + 30, paint(col("steel", 0.5 * a_ar), stroke=True, width=1.5))
        vy = piv[1] - 10
        Lv = 150 * xd
        if abs(Lv) > 4:
            sh.arrow_motion(c, (ax_ - Lv / 2, vy), (ax_ + Lv / 2, vy), width=7, alpha=a_ar)
        ep.Tex(r"\cm{v}", 34).draw(c, ax_ + 95, vy + 10, col("motion", a_ar))
        note(c, "tower", ax_ + 130, vy + 8, 20, "motion", a_ar, style="semibold")
        Lf = 150 * fb
        yf = piv[1] + 70
        if abs(Lf) > 4:
            sh.arrow_force(c, (ax_ - Lf / 2, yf), (ax_ + Lf / 2, yf), width=12, alpha=a_ar)
        ep.Tex(r"\cf{F}", 34).draw(c, ax_ + 95, yf + 10, col("force", a_ar))
        note(c, "pull of the ball", ax_ + 130, yf + 8, 20, "force", a_ar, style="semibold")
    exaggeration_tag(c, "sway exaggerated × 100  ·  diagram not to scale", 96, 1010,
                     alpha=alpha * fade(t, T23 - 0.2, None, 0.5))
    # the beat plot: tower and ball, a quarter of a beat apart
    X, Y = tmd_phasors()
    lag = (np.angle(X) - np.angle(Y)) % (2 * np.pi)
    x0, x1, yc, amp = 1010, 1810, 520, 115
    period_px = 380.0
    a_p = alpha * fade(t, T23 + 0.2, None, 0.6)
    if a_p > 0:
        c.drawLine(x0, yc, x1, yc, paint(col("steel", 0.3 * a_p), stroke=True, width=1.2))
        w = P.TOWER_WN
        ph_now = w * (t - T23)
        xs = np.linspace(x0, x1, 400)
        # time runs right to left: the right edge is 'now'
        ph = ph_now - (x1 - xs) / period_px * 2 * np.pi
        tower_tr = np.real(np.exp(1j * ph))
        ball_tr = np.real((Y / X) * np.exp(1j * ph)) / abs(Y / X)
        p1 = ep.polyline_path(list(zip(xs, yc - amp * tower_tr)))
        c.drawPath(p1, paint(col("motion", a_p), stroke=True, width=3.5))
        p2 = ep.polyline_path(list(zip(xs, yc - amp * ball_tr)))
        pp = paint(col("highlight", a_p), stroke=True, width=3.5)
        pp.setPathEffect(skia.DashPathEffect.Make([14, 8], 0))
        c.drawPath(p2, pp)
        note(c, "tower sway", x0, yc - amp - 70, 24, "motion", a_p, style="semibold")
        note(c, "ball swing", x0 + 190, yc - amp - 70, 24, "highlight", a_p, style="semibold")
        note(c, "time  →", x1, yc + amp + 60, 20, "steel", a_p, anchor="right")
        # quarter-beat bracket between a tower peak and the next ball peak
        a_q = alpha * fade(t, at("L23", "a quarter of a beat") - 0.2, None, 0.5)
        if a_q > 0:
            # find the rightmost tower peak inside the plot
            k = math.floor(ph_now / (2 * np.pi))
            for kk in (k, k - 1):
                ph_peak = 2 * np.pi * kk
                xp = x1 - (ph_now - ph_peak) / (2 * np.pi) * period_px
                xb = xp + lag / (2 * np.pi) * period_px
                if x0 + 20 < xp and xb < x1 - 10:
                    yb = yc - amp - 20
                    c.drawLine(xp, yb, xb, yb, paint(col("paper", a_q), stroke=True, width=2.2))
                    for xx in (xp, xb):
                        c.drawLine(xx, yb - 8, xx, yb + 8, paint(col("paper", a_q), stroke=True, width=2.2))
                    label_box(c, (xp + xb) / 2, yb - 36, "¼ beat", 24, "paper", 0.85, "semibold", anchor="center",
                              alpha=a_q)
                    break
        lagd = math.degrees(lag)
        a_t = alpha * fade(t, at("L23", "a quarter of a beat") - 0.2, None, 0.5)
        note(c, f"the ball lags the tower by about {lagd:.0f}°", x0, yc + amp + 110, 24, "paper", a_t)
        a_f = alpha * fade(t, at("L23", "so its pull") - 0.2, None, 0.5)
        note(c, "so the ball's pull F points against the tower's velocity v:", x0, yc + amp + 160, 24, "steel", a_f)
        note(c, "it acts like a brake, and its own dampers turn the energy into heat", x0, yc + amp + 196, 24,
             "steel", a_f)
        a_40 = alpha * fade(t, T24 - 0.2, None, 0.5)
        label_box(c, x0, yc + amp + 262, "sway reduced by up to about 40 %  (operator's figure)", 24, "balance", 0.8,
                  "semibold", alpha=a_40)


def draw_taipei(c, t):
    if t < T_3D0 + 0.8:
        draw_taipei_intro(c, t)
    if t >= T_3D0:
        a = smooth(ramp(t, T_3D0, T_3D0 + 0.8)) * (1 - smooth(ramp(t, T_3D1 - 0.2, T_3D1 + 0.6)))
        if a > 0:
            c.saveLayerAlpha(None, int(255 * a))
            draw_ball(c, t)
            c.restore()
    if t >= T_3D1 - 0.2:
        a = smooth(ramp(t, T_3D1 - 0.2, T_3D1 + 0.6))
        c.saveLayerAlpha(None, int(255 * a))
        draw_quarter_beat(c, t, 1.0)
        c.restore()
    a_out = smooth(ramp(t, TA1 - 0.6, TA1))
    if a_out > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint(col("ink", a_out)))


# ------------------------------------------------------------------ closing card

K0, K1 = S["takeaway"]
T25 = at("L25")


def draw_takeaway(c, t):
    fx.background(c)
    a_in = smooth(ramp(t, K0, K0 + 0.6))
    words = "Push something at its favourite rhythm, and tiny pushes make huge movements.".split(" ")
    line1 = " ".join(words[:6])
    line2 = " ".join(words[6:])
    L1 = ep.Text(line1, 64, "display-medium", -0.5)
    L2 = ep.Text(line2, 64, "display-medium", -0.5)
    dur = end("L25") - T25
    # reveal word by word, following the voice
    t1 = T25
    n1, n2 = len(line1), len(line2)
    tot = n1 + n2

    def per_glyph(line_text, offset):
        def fa(i):
            tc = t1 + dur * (offset + i) / tot
            return smooth(ramp(t, tc - 0.25, tc + 0.15)) * a_in
        return fa

    L1.draw(c, W / 2, 470, col("paper"), anchor="center", alpha_per_glyph=per_glyph(line1, 0))
    L2.draw(c, W / 2, 560, col("paper"), anchor="center", alpha_per_glyph=per_glyph(line2, n1))
    # the resonance curve and the series signature
    x0, x1, yb = 760, 1160, 780
    u = ease_in_out(ramp(t, end("L25") - 0.3, end("L25") + 1.4))
    if u > 0:
        rs = np.linspace(0, 2, 300)
        amp = P.amplification(rs, 0.05)
        pts = [(x0 + (x1 - x0) * r / 2, yb - 110 * a_ / 10.5) for r, a_ in zip(rs, amp)]
        path = ep.trim_path(ep.polyline_path(pts), u)
        c.drawLine(x0, yb, x1, yb, paint(col("steel", 0.5), stroke=True, width=2))
        c.drawPath(path, paint(col("motion", 0.5), stroke=True, width=8, blur=6))
        c.drawPath(path, paint(col("motion"), stroke=True, width=3))
        k = ease_out_back(ramp(t, end("L25") + 1.2, end("L25") + 1.6))
        if k > 0:
            c.drawCircle((x0 + x1) / 2, yb - 110 * 10 / 10.5, 7 * k, paint(col("highlight")))
    a_sig = fade(t, end("L25") + 1.0, None, 0.8)
    sig = ep.Text("ENGINEERING PHENOMENA  ·  01  RESONANCE", 22, "semibold", 22 * 0.3)
    sig.draw(c, W / 2, 900, col("highlight", a_sig), anchor="center")
    fx.colour_bar(c, H - 8, 8, alpha=a_sig, progress=ease_out(ramp(t, end("L25") + 1.0, end("L25") + 2.2)))
    a_out = smooth(ramp(t, K1 - 1.2, K1))
    if a_out > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint(col("#000000", a_out)))
