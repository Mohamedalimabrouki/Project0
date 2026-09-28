"""
Resonance - the London Millennium Bridge (June 2000).

Facts used (see the README sources): opened to the public 10 June 2000, closed
12 June 2000; spans 81 m, 144 m and 108 m; sideways sway up to about 70 mm on
the centre span; 37 fluid-viscous dampers plus about 60 tuned mass dampers;
lateral damping raised from about 0.5 % to about 20 %; reopened 22 February 2002.
Arup crowd test (December 2000, north span): 156 walkers, no sway; 166, sudden sway.

Mechanism, worded to be true under both the 'synchronous lateral excitation'
(Dallard et al. 2001) and the 'balancing pedestrian' (Macdonald 2009) models:
on average, the walkers' sideways push has a part in step with the deck's
sideways velocity, which feeds energy into the sway.
"""

import functools
import math

import numpy as np
import skia

from sc_common import (W, H, S, T, at, end, col, paint, ramp, smooth, fade, ease_out, ease_in_out,
                       ease_out_back, ep, fx, sh, label_box, caption, note, tex_box, exaggeration_tag)

B0, B1 = S["bridge"]
T18, T19, T20, T21 = at("L18"), at("L19"), at("L20"), at("L21")

# elevation geometry (px): 333 m of bridge over 1680 px
X_N, X_S = 120.0, 1800.0
PX_M = (X_S - X_N) / 333.0
PIER1 = X_N + 81 * PX_M
PIER2 = X_N + 225 * PX_M
DECK_Y = 610.0
WATER_Y = 700.0


def deck_y(x):
    """Deck line: shallow sags between supports (the real main-span cable sag is only 2.3 m)."""
    supports = [X_N, PIER1, PIER2, X_S]
    sags = [1.6, 2.3, 1.9]
    for (a, b), sg in zip(zip(supports[:-1], supports[1:]), sags):
        if a <= x <= b:
            u = (x - a) / (b - a)
            return DECK_Y + 4 * sg * PX_M * u * (1 - u) * 1.4
    return DECK_Y


# ------------------------------------------------------------------ backdrop

def draw_skyline(c, alpha):
    base = WATER_Y
    sil = col("#2A323C", alpha)
    # city blocks behind the north bank (left)
    rng = np.random.default_rng(3)
    x = 0
    while x < 700:
        w = rng.uniform(40, 90)
        h = rng.uniform(60, 170)
        c.drawRect(skia.Rect.MakeLTRB(x, base - h, x + w - 4, base), paint(sil))
        x += w
    # St Paul's Cathedral: drum, dome, lantern, and the two west towers
    cx, gy = 330.0, base - 120
    p = paint(col("#343D48", alpha))
    c.drawRect(skia.Rect.MakeLTRB(cx - 150, gy, cx + 150, base), p)                 # nave block
    for tx in (cx - 190, cx + 150):
        c.drawRect(skia.Rect.MakeLTRB(tx, gy - 90, tx + 40, base), p)               # towers
        path = skia.Path()
        path.moveTo(tx - 2, gy - 90)
        path.lineTo(tx + 20, gy - 135)
        path.lineTo(tx + 42, gy - 90)
        path.close()
        c.drawPath(path, p)
    c.drawRect(skia.Rect.MakeLTRB(cx - 78, gy - 95, cx + 78, gy), p)                # drum
    dome = skia.Path()
    dome.addArc(skia.Rect.MakeLTRB(cx - 88, gy - 95 - 92, cx + 88, gy - 95 + 92), 180, 180)
    dome.close()
    c.drawPath(dome, p)
    c.drawRect(skia.Rect.MakeLTRB(cx - 12, gy - 95 - 92 - 44, cx + 12, gy - 95 - 88), p)  # lantern
    c.drawRect(skia.Rect.MakeLTRB(cx - 2.5, gy - 95 - 92 - 70, cx + 2.5, gy - 95 - 92 - 40), p)
    # Tate Modern (right): the long brick hall and the tall central chimney
    tx0, tx1 = 1240, 1900
    c.drawRect(skia.Rect.MakeLTRB(tx0, base - 150, tx1, base), paint(sil))
    c.drawRect(skia.Rect.MakeLTRB(1540, base - 150 - 260, 1590, base), paint(col("#343D48", alpha)))
    for i in range(8):
        c.drawRect(skia.Rect.MakeLTRB(tx0 + 40 + i * 78, base - 120, tx0 + 44 + i * 78, base - 20),
                   paint(col("#20272F", alpha)))


def draw_water(c, t, alpha, y0=WATER_Y):
    shader = skia.GradientShader.MakeLinear([skia.Point(0, y0), skia.Point(0, H)],
                                            [col("fluid", 0.16 * alpha), col("fluid", 0.04 * alpha)])
    c.drawRect(skia.Rect.MakeLTRB(0, y0, W, H), skia.Paint(Shader=shader))
    p = paint(col("fluid", 0.22 * alpha), stroke=True, width=1.4)
    for j in range(9):
        yy = y0 + 22 + j * 40 + j * j * 3
        path = skia.Path()
        ph = t * (0.6 + 0.05 * j) + j * 1.7
        first = True
        for xx in range(0, W + 40, 40):
            y = yy + 3 * math.sin(xx * 0.012 + ph)
            if first:
                path.moveTo(xx, y)
                first = False
            else:
                path.lineTo(xx, y)
        p2 = paint(col("fluid", (0.18 - 0.012 * j) * alpha), stroke=True, width=1.4)
        p2.setPathEffect(skia.DashPathEffect.Make([60 + 10 * j, 90], (t * 30 * (1 + j * 0.1)) % 150))
        c.drawPath(path, p2)


def draw_bridge_elevation(c, alpha, damper_alpha=0.0, t=0.0):
    steel = col("steel", alpha)
    # piers with the Y-shaped arms
    for px in (PIER1, PIER2):
        c.drawRect(skia.Rect.MakeLTRB(px - 9, DECK_Y + 6, px + 9, WATER_Y + 40), paint(col("#5E6873", alpha)))
        arm = skia.Path()
        arm.moveTo(px, DECK_Y + 30)
        arm.lineTo(px - 26, DECK_Y - 18)
        arm.moveTo(px, DECK_Y + 30)
        arm.lineTo(px + 26, DECK_Y - 18)
        c.drawPath(arm, paint(steel, stroke=True, width=6))
    # deck (follows the cables)
    pts_top = [(x, deck_y(x) - 3) for x in np.linspace(X_N, X_S, 240)]
    pts_bot = [(x, deck_y(x) + 5) for x in np.linspace(X_S, X_N, 240)]
    deck = ep.polyline_path(pts_top + pts_bot, closed=True)
    c.drawPath(deck, paint(col("#AEB6BF", alpha)))
    # cables slightly above the deck edge
    cab = ep.polyline_path([(x, deck_y(x) - 9) for x in np.linspace(X_N, X_S, 240)])
    c.drawPath(cab, paint(col("paper", 0.55 * alpha), stroke=True, width=2))
    # abutments on the banks
    for x0, x1 in ((X_N - 120, X_N + 6), (X_S - 6, X_S + 120)):
        c.drawRect(skia.Rect.MakeLTRB(x0, DECK_Y - 2, x1, WATER_Y + 10), paint(col("#3A434E", alpha)))
    # retrofit dampers (bluish green = it works): one small unit every 16 m under the deck
    if damper_alpha > 0:
        for i, x in enumerate(np.arange(X_N + 8 * PX_M, X_S - 4 * PX_M, 16 * PX_M / 1.8)):
            k = ease_out_back(ramp(damper_alpha * 40 - i, 0, 1))
            if k <= 0:
                continue
            y = deck_y(x) + 12
            r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x - 7 * k, y, 14 * k, 9 * k), 3, 3)
            c.drawRRect(r, paint(col("balance", alpha)))
            c.drawRRect(r, paint(col("balance", 0.5 * alpha), blur=6))


@functools.lru_cache(maxsize=1)
def walkers():
    rng = np.random.default_rng(11)
    n = 260
    return dict(start=rng.uniform(0, 1, n), speed=rng.uniform(0.010, 0.016, n) * np.where(rng.uniform(0, 1, n) < 0.5, 1, -1),
                enter=rng.uniform(0, 4.5, n), height=rng.uniform(7.5, 9.5, n), phase=rng.uniform(0, 6.28, n),
                shade=rng.uniform(0.55, 0.95, n))


def draw_walkers(c, t, t_start, alpha, density=1.0, sway_px=0.0):
    w = walkers()
    n = int(len(w["start"]) * density)
    for i in range(n):
        if t < t_start + w["enter"][i]:
            continue
        u = (w["start"][i] + w["speed"][i] * (t - t_start)) % 1.0
        x = X_N + 10 + u * (X_S - X_N - 20)
        y = deck_y(x) - 4
        bob = 1.2 * abs(math.sin(8 * (t - t_start) + w["phase"][i]))
        h = w["height"][i]
        a = alpha * ramp(t, t_start + w["enter"][i], t_start + w["enter"][i] + 0.5)
        colr = col(ep.mix_hex("steel", "paper", w["shade"][i]), a)
        c.drawRoundRect(skia.Rect.MakeXYWH(x - 1.4, y - h - bob, 2.8, h), 1.4, 1.4, paint(colr))
        c.drawCircle(x, y - h - bob - 2.4, 2.0, paint(colr))


# ------------------------------------------------------------------ section view (end-on)

SEC_CX, SEC_Y = 960.0, 700.0
DECK_W = 720.0          # 4 m deck width drawn at 180 px/m


def draw_person_front(c, x, y, t, alpha, step_rate=1.8, stance=1.0, lean=0.0, scale=1.0):
    """A walker seen from the front: alternating steps (left, right), feet placed a little apart."""
    ph = (t * step_rate) % 2.0          # 0-1 left foot on deck, 1-2 right foot on deck
    left_down = ph < 1.0
    s = scale
    hip_w = 18 * s * stance
    body_x = x + lean * 10 * s + (-1 if left_down else 1) * 5 * s * math.sin(math.pi * (ph % 1.0))
    colr = col("paper", alpha)
    dim = col("steel", alpha)
    # legs
    for side, down in ((-1, left_down), (1, not left_down)):
        fx_ = x + side * hip_w
        lift = 0 if down else 10 * s * math.sin(math.pi * (ph % 1.0))
        c.drawLine(body_x + side * 8 * s, y - 88 * s, fx_, y - lift, paint(colr if down else dim, stroke=True,
                                                                         width=9 * s, cap="round"))
    # torso, head, arms
    c.drawLine(body_x, y - 90 * s, body_x + lean * 4, y - 150 * s, paint(colr, stroke=True, width=20 * s, cap="round"))
    c.drawCircle(body_x + lean * 5, y - 175 * s, 13 * s, paint(colr))
    for side in (-1, 1):
        c.drawLine(body_x + side * 10 * s, y - 145 * s, body_x + side * 22 * s, y - 100 * s,
                   paint(colr, stroke=True, width=7 * s, cap="round"))
    return left_down, ph


def draw_section(c, t, alpha, sway_mm=0.0, v_norm=0.0, walkers_n=1, stance=1.0, push_in_step=0.0,
                 show_dampers=0.0, exag=5.0):
    """Cross-section of the deck: 4 m wide aluminium deck, the cables at both edges, the walkers."""
    dx = sway_mm / 1000 * 180 * exag           # px, exaggerated
    cx = SEC_CX + dx
    # the transverse arm and cables
    arm = skia.Path()
    arm.moveTo(cx - DECK_W / 2 - 40, SEC_Y + 40)
    arm.lineTo(cx + DECK_W / 2 + 40, SEC_Y + 40)
    c.drawPath(arm, paint(col("steel", alpha), stroke=True, width=10))
    for side in (-1, 1):
        c.drawCircle(cx + side * (DECK_W / 2 + 40), SEC_Y + 40, 14, paint(col("#AEB6BF", alpha)))
        c.drawCircle(cx + side * (DECK_W / 2 + 40), SEC_Y + 40, 14, paint(col("paper", 0.4 * alpha), stroke=True, width=2))
    deck = skia.Rect.MakeLTRB(cx - DECK_W / 2, SEC_Y, cx + DECK_W / 2, SEC_Y + 22)
    c.drawRect(deck, paint(col("#AEB6BF", alpha)))
    # handrails
    for side in (-1, 1):
        x = cx + side * (DECK_W / 2 - 6)
        c.drawLine(x, SEC_Y, x, SEC_Y - 110, paint(col("steel", alpha), stroke=True, width=4))
    # rest position guide
    p = paint(col("steel", 0.4 * alpha), stroke=True, width=1.5)
    p.setPathEffect(skia.DashPathEffect.Make([6, 6], 0))
    c.drawLine(SEC_CX, SEC_Y - 260, SEC_CX, SEC_Y + 90, p)
    # dampers under the deck (bluish green): chevron braces
    if show_dampers > 0:
        for side in (-1, 1):
            a0 = (cx + side * 60, SEC_Y + 44)
            a1 = (SEC_CX + side * 230, SEC_Y + 190)
            sh.dashpot(c, a1, a0, body_len=70, body_w=22, width=3.4, color_hex=ep.PALETTE["balance"],
                       alpha=alpha * show_dampers, fluid=False)
        c.drawLine(SEC_CX - 300, SEC_Y + 190, SEC_CX + 300, SEC_Y + 190,
                   paint(col("steel", alpha * show_dampers), stroke=True, width=5))
    # walkers
    xs = [0.0] if walkers_n == 1 else list(np.linspace(-210, 210, walkers_n))
    feet = []
    for j, ox in enumerate(xs):
        ld, ph = draw_person_front(c, cx + ox, SEC_Y, t + j * 0.37, alpha, stance=stance,
                                   scale=1.45 if walkers_n == 1 else 1.2)
        feet.append((cx + ox, ld, ph))
    return cx, feet


# ------------------------------------------------------------------ the scene

def sway_state(t):
    """Sideways sway (mm) and normalised velocity: grows during L20, stops after the closure."""
    f = 0.8                                     # Hz, representative lateral mode (south span about 0.8 Hz)
    grow = smooth(ramp(t, T20 - 0.5, T20 + 7.5))
    stop = 1 - smooth(ramp(t, T21 + 0.2, T21 + 2.2))
    amp = 70.0 * grow * stop
    ph = 2 * math.pi * f * (t - T20)
    return amp * math.sin(ph), math.cos(ph) * (1 if amp > 1 else 0) * grow * stop


def draw_bridge(c, t):
    fx.background(c, grid_alpha=0.04)
    a_in = smooth(ramp(t, B0, B0 + 0.8))
    t_sec = T19 - 0.6                         # cut to the section view
    t_back = at("L21", "Engineers fitted") - 0.6    # back to the elevation for the retrofit
    k_sec = smooth(ramp(t, t_sec, t_sec + 0.9)) * (1 - smooth(ramp(t, t_back, t_back + 0.9)))
    # ---- elevation
    a_el = a_in * (1 - k_sec)
    if a_el > 0.001:
        zoom = 1 + 0.6 * smooth(ramp(t, t_sec - 0.4, t_sec + 0.9)) * (1 if t < t_back else 0)
        c.save()
        c.translate(1100, DECK_Y)
        c.scale(zoom, zoom)
        c.translate(-1100, -DECK_Y)
        draw_skyline(c, a_el)
        draw_water(c, t, a_el)
        damp = ramp(t, at("L21", "Engineers fitted") + 0.2, at("L21", "Engineers fitted") + 2.2)
        draw_bridge_elevation(c, a_el, damper_alpha=damp, t=t)
        reopened = t > at("L21", "In 2002") - 0.5
        if t < t_sec + 1.0:
            draw_walkers(c, t, T18 + 0.3, a_el)
        elif reopened:
            draw_walkers(c, t, at("L21", "In 2002") - 0.5, a_el)
        c.restore()
        # captions
        a_cap = a_el * fade(t, T18 - 0.2, None, 0.6)
        caption(c, "London  ·  Millennium Bridge", 96, 110, 24, "paper", a_cap)
        note(c, "opened to the public on 10 June 2000", 96, 150, 24, "steel", a_cap)
        a_sp = a_el * fade(t, T18 + 2.5, t_sec, 0.6, 0.4)
        if a_sp > 0:
            for x0, x1, lab in ((X_N, PIER1, "81 m"), (PIER1, PIER2, "144 m"), (PIER2, X_S, "108 m")):
                sh.dimension_line(c, (x0, 790), (x1, 790), lab, col("steel", a_sp), size=20, tick=7)
        if t > t_back:
            a_d = fade(t, at("L21", "Engineers fitted") + 0.4, None, 0.5)
            label_box(c, 1824, 110, "37 viscous dampers  +  about 60 tuned mass dampers", 26, "balance", 0.8,
                      "semibold", anchor="right", alpha=a_d)
            note(c, "sideways damping raised from about 0.5 % to about 20 %", 1824, 168, 22, "steel", a_d, anchor="right")
            a_r = fade(t, at("L21", "In 2002") - 0.2, None, 0.5)
            label_box(c, 1824, 230, "reopened 22 February 2002  ·  steady", 26, "paper", 0.8, "semibold",
                      anchor="right", alpha=a_r)
    # ---- section
    if k_sec > 0.001:
        a_s = k_sec * a_in
        c.saveLayerAlpha(None, int(255 * a_s))
        fx.background(c, grid_alpha=0.05)
        draw_water(c, t, 1.0, y0=SEC_Y + 260)
        sway, vn = sway_state(t)
        stance = 1.0 + 0.8 * smooth(ramp(t, T20 + 0.5, T20 + 3.0))
        n_w = 1 if t < T20 + 3.5 else 3
        cx, feet = draw_section(c, t, 1.0, sway_mm=sway, v_norm=vn, walkers_n=n_w, stance=stance)
        caption(c, "Looking along the deck", 96, 110, 24, "paper", 1.0)
        note(c, "deck 4 m wide  ·  walkers seen from the front", 96, 150, 22, "steel", 1.0)
        # each step: a small sideways push on the deck (left, right, left, right)
        in_step = smooth(ramp(t, T20 + 2.5, T20 + 5.0))
        for (fxp, left_down, ph) in feet:
            f_lat = math.sin(math.pi * (ph % 1.0))
            direction = -1 if left_down else 1
            if in_step > 0 and abs(vn) > 0.05:
                # once swaying: on average the push lines up with the deck velocity
                direction = direction * (1 - in_step) + in_step * (1 if vn > 0 else -1)
            L = 95 * f_lat
            if L > 3 and abs(direction) > 0.2:
                y = SEC_Y - 10
                x0 = fxp + (-1 if left_down else 1) * 24
                sh.arrow_force(c, (x0, y), (x0 + direction * L, y), width=12)
        a_f = fade(t, T19 + 0.4, t_back, 0.5, 0.4)
        note(c, "each step pushes the deck sideways", 96, 960, 26, "force", a_f, style="semibold")
        note(c, "sideways push: about once per second each way (half the step rate)", 96, 1000, 21, "steel", a_f)
        if abs(vn) > 0.01 and t > T20:
            yv = SEC_Y - 360
            L = 120 * vn
            if abs(L) > 4:
                sh.arrow_motion(c, (cx - L / 2, yv), (cx + L / 2, yv), width=6)
                ep.Tex(r"\cm{v}", 34).draw(c, cx - 8, yv - 22, col("motion"))
            exaggeration_tag(c, "sideways motion exaggerated × 5  ·  real: up to about 70 mm", 1824, 108,
                             alpha=fade(t, T20 + 0.5, t_back, 0.5, 0.3), anchor="right")
        a_e = fade(t, at("L20", "On average") - 0.2, t_back, 0.5, 0.4)
        if a_e > 0:
            label_box(c, 1824, 200, "on average, pushes in step with the sway: energy in", 26, "energy", 0.8,
                      "semibold", anchor="right", alpha=a_e)
            note(c, "Arup crowd test, Dec 2000: 156 walkers, no sway  ·  166 walkers, sudden sway", 1824, 262, 21,
                 "steel", a_e, anchor="right")
        a_cl = fade(t, T21 - 0.1, t_back + 0.3, 0.3, 0.3)
        if a_cl > 0:
            k = ease_out_back(ramp(t, T21 - 0.1, T21 + 0.35))
            c.save()
            c.translate(960, 380)
            c.rotate(-6)
            c.scale(0.8 + 0.2 * k, 0.8 + 0.2 * k)
            r = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-230, -60, 460, 120), 12, 12)
            c.drawRRect(r, paint(col("ink", 0.85 * a_cl)))
            c.drawRRect(r, paint(col("paper", a_cl), stroke=True, width=5))
            ep.Text("CLOSED", 64, "display-bold", 6).draw(c, 0, 8, col("paper", a_cl), anchor="center")
            ep.Text("12 June 2000", 24, "semibold").draw(c, 0, 46, col("steel", a_cl), anchor="center")
            c.restore()
        c.restore()
    a_out = smooth(ramp(t, B1 - 0.6, B1))
    if a_out > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint(col("ink", a_out)))
