"""
Resonance - the engineer's model: the mass on a spring (3D hero with labels,
then the blueprint), the natural rhythm (k and m), the push-rhythm sweep with
the live resonance curve, and damping.

All motion is exact: free vibration from physics.free_decay, and the sweep is
the steady-state solution X(ω)·cos(ωt - φ) of m·x'' + c·x' + k·x = F0·cos(ωt).
"""

import functools
import math

import numpy as np
import skia

import physics as P
from sc_common import (W, H, S, T, at, end, col, paint, ramp, smooth, fade, ease_out, ease_in_out,
                       ease_out_back, ep, fx, sh, Axes, draw_render, pt, label_box, caption, note,
                       bottom_gradient, top_gradient, tex_box, unit, leader, exaggeration_tag)

HERO0 = S["spring_hero"][0]
RELEASE_3D = 0.8                      # release time inside the 3D shot (blender_spring.RELEASE)
X0_3D = 55.0                          # mm (blender_spring.X0)
BLOCK_MM = P.BLOCK_SIDE * 1000        # 63.4 mm
REST_MM = 200.0

_tex = {}


def tex(key, latex, size):
    if key not in _tex:
        _tex[key] = ep.Tex(latex, size)
    return _tex[key]


# ------------------------------------------------------------------ the schematic rig

def lerp(a, b, u):
    return a + (b - a) * u


def geom_lerp(g0, g1, u):
    return {k: lerp(g0[k], g1[k], u) if isinstance(g0[k], (int, float)) else g1[k] for k in g0}


GEOM_3D = dict(wall_x=427.0, axis_y=561.0, s=3.33, spring_dy=-51.0, damper_dy=57.0, coil_r=50.0, wire=4.2,
               block_mm=BLOCK_MM, mass_mult=1.0, k_mult=1.0)


def rig_geom(wall_x, axis_y, s, mass_mult=1.0, k_mult=1.0):
    side = BLOCK_MM * mass_mult ** (1 / 3)
    return dict(wall_x=wall_x, axis_y=axis_y, s=s, spring_dy=-0.24 * BLOCK_MM * s,
                damper_dy=0.27 * BLOCK_MM * s, coil_r=15.0 * s, wire=max(2.2, 1.26 * s) * k_mult ** 0.25,
                block_mm=side, mass_mult=mass_mult, k_mult=k_mult)


def draw_rig(c, g, x_mm, alpha=1.0, draw=1.0, force=None, vel=None, heat=0.0, labels=True,
             label_alpha=1.0, block_label="m", k_label="k", c_label="c", damper_alpha=1.0, ghost_rest=True):
    """
    Schematic: hatched wall, coil spring on top, damper below, steel block on rollers.
    x_mm: displacement of the block from rest (mm). force/vel: normalised -1..1 for the arrows.
    draw: 0..1 progressive 'drawing on' (used for the blueprint transition).
    """
    s = g["s"]
    wall_x, ay = g["wall_x"], g["axis_y"]
    side_px = g["block_mm"] * s
    bx = wall_x + (REST_MM + x_mm) * s + side_px / 2          # block centre
    left = bx - side_px / 2
    a = alpha
    d_wall = ep.clamp01(draw * 4)
    d_spring = ep.clamp01(draw * 4 - 1)
    d_damper = ep.clamp01(draw * 4 - 1.6)
    d_block = ep.clamp01(draw * 4 - 2.4)
    ground_y = ay + side_px / 2 + 14 * s / 1.9
    # ground and wall
    if d_wall > 0:
        wall_top = ay - max(side_px, 63 * s) * 0.9
        wall_bot = ground_y
        sh.wall(c, wall_x, wall_top, wall_top + (wall_bot - wall_top) * d_wall, col("steel", a), hatch=12)
        gx1 = wall_x + (REST_MM + 110) * s + side_px
        sh.ground(c, wall_x, wall_x + (gx1 - wall_x) * d_wall, ground_y, col("steel", a), hatch=12)
    if ghost_rest and d_block > 0:
        rx = wall_x + REST_MM * s + side_px / 2
        p = paint(col("steel", 0.35 * a * d_block), stroke=True, width=1.5)
        p.setPathEffect(skia.DashPathEffect.Make([6, 6], 0))
        c.drawLine(rx, ay - side_px / 2 - 26, rx, ground_y, p)
    # spring
    if d_spring > 0:
        sy = ay + g["spring_dy"]
        end_x = wall_x + (left - wall_x) * d_spring
        coils = 14
        sh.coil_spring(c, (wall_x, sy), (end_x, sy), coils=max(2, int(coils * d_spring)), radius=g["coil_r"] * 0.62,
                       wire=g["wire"], alpha=a, end_len=10)
    # damper
    if d_damper > 0:
        dy = ay + g["damper_dy"]
        end_x = wall_x + (left - wall_x) * d_damper
        sh.dashpot(c, (wall_x, dy), (end_x, dy), body_len=REST_MM * s * 0.42, body_w=g["coil_r"] * 0.75,
                   width=max(2.2, 1.3 * s), alpha=a * damper_alpha, heat=heat)
    # block, rollers
    if d_block > 0:
        ab = a * d_block
        r = max(4.0, 3.2 * s)
        for wx in (left + side_px * 0.25, left + side_px * 0.75):
            c.drawCircle(wx, ground_y - r, r, paint(col("steel", ab), stroke=True, width=2))
        sh.mass_block(c, bx, ay - r * 0.6, side_px, side_px - r * 1.2, block_label if labels else None, alpha=ab,
                      radius=max(6, 3 * s), label_size=side_px * 0.36)
    # arrows
    if force is not None and abs(force) > 0.01:
        right = bx + side_px / 2
        L = 95 * abs(force) * (s / 1.9) ** 0.5
        yb = ay - 4
        if force > 0:
            sh.arrow_force(c, (right + 4, yb), (right + 4 + L, yb), width=12, alpha=a)
        else:
            sh.arrow_force(c, (right + 8 + L, yb), (right + 8, yb), width=12, alpha=a)
    if vel is not None and abs(vel) > 0.02:
        L = 115 * abs(vel)
        yv = ay - side_px / 2 - 34
        sgn = 1 if vel > 0 else -1
        sh.arrow_motion(c, (bx - sgn * L / 2, yv), (bx + sgn * L / 2, yv), width=6, alpha=a)
    if labels and label_alpha > 0 and draw >= 1:
        la = a * label_alpha
        tk = tex("lab_" + k_label, k_label, 40)
        tk.draw(c, wall_x + (left - wall_x) * 0.5, ay + g["spring_dy"] - g["coil_r"] * 0.62 - 22, col("paper", la),
                anchor="center")
        tc = tex("lab_" + c_label, c_label, 40)
        tc.draw(c, wall_x + (left - wall_x) * 0.22, ground_y + 44,
                col("paper", la * damper_alpha), anchor="center")
    return bx, ay, side_px


# ------------------------------------------------------------------ 3D hero with labels

def x_3d(t):
    """Block displacement (mm) of the 3D shot at global time t (same maths as blender_spring)."""
    u = t - HERO0
    if u < RELEASE_3D:
        return X0_3D
    return float(P.free_decay(u - RELEASE_3D, X0_3D))


def draw_spring_hero(c, t, alpha=1.0):
    u = t - HERO0
    fi = draw_render(c, "spring", u)
    bottom_gradient(c, 760, 0.6)
    top_gradient(c, 200, 0.5)
    t_m = at("L07", "a mass on a spring")
    t_end = S["spring_model"][0] - 0.05
    am = fade(t, t_m - 0.1, t_end, 0.4, 0.4)
    if am > 0:
        b = pt("spring", fi, "block_top")
        k = ease_out(ramp(t, t_m - 0.1, t_m + 0.4))
        lp = (b[0] + 60, b[1] - 120)
        leader(c, (b[0], b[1] - 6), (b[0] + (lp[0] - b[0]) * k, b[1] - 6 + (lp[1] - b[1] + 6) * k), alpha=am)
        if k > 0.9:
            label_box(c, lp[0] + 6, lp[1], "mass  m = 2 kg", 26, "paper", 0.82, "semibold", alpha=am)
    t_k = at("L07", "a mass on a spring") + 0.75
    ak = fade(t, t_k, t_end, 0.4, 0.4)
    if ak > 0:
        sp0 = pt("spring", fi, "spring_post")
        sp1 = pt("spring", fi, "spring_block")
        mid = ((sp0[0] + sp1[0]) / 2, (sp0[1] + sp1[1]) / 2 - 30)
        k = ease_out(ramp(t, t_k, t_k + 0.4))
        lp = (mid[0] - 80, mid[1] - 150)
        leader(c, mid, (mid[0] + (lp[0] - mid[0]) * k, mid[1] + (lp[1] - mid[1]) * k), alpha=ak)
        if k > 0.9:
            label_box(c, lp[0], lp[1], "spring  k = 79 N/m", 26, "paper", 0.82, "semibold", anchor="right", alpha=ak)
    a_note = fade(t, t_m + 0.8, t_end, 0.5, 0.4)
    if a_note > 0:
        note(c, "Real scale: a 63 mm steel cube, a spring tuned to exactly 1 Hz.", 96, 1000, 22, "steel", a_note)


# ------------------------------------------------------------------ the model: k and m set the rhythm

MODEL0 = S["spring_model"][0]
G_MODEL = rig_geom(250, 300, 1.55)


def rig_free(t, t_pluck, x0, mass_mult, k_mult):
    """Exact damped free vibration after a pluck, with the same damper c for every rig."""
    m = P.MASS * mass_mult
    k = P.STIFFNESS * k_mult
    zeta = P.DAMPING / (2 * math.sqrt(k * m))
    if t < t_pluck:
        return 0.0
    tp = t - t_pluck
    # pulled out over 0.35 s, then released
    if tp < 0.35:
        return x0 * smooth(tp / 0.35)
    return float(P.free_decay_general(tp - 0.35, x0, m, k, zeta))


def draw_spring_model(c, t):
    fx.background(c)
    t_in = MODEL0
    t_stiff = at("L08", "A stiffer spring")
    t_heavy = at("L08", "A heavier mass")
    t_two = at("L08", "just two things")
    # 1) blueprint transition from the 3D render
    k_bp = ramp(t, t_in, t_in + 0.8)
    a_render = 1 - smooth(ramp(t, t_in + 0.5, t_in + 1.2))
    if a_render > 0:
        draw_spring_hero(c, t, alpha=a_render) if False else None
        c.saveLayerAlpha(None, int(255 * a_render))
        draw_render(c, "spring", t - HERO0)
        c.restore()
        c.drawRect(skia.Rect.MakeWH(W, H), paint(col("ink", 0.25 * (1 - a_render))))
    # 2) move from the 3D layout to the model layout
    mv = ease_in_out(ramp(t, t_in + 1.2, t_in + 2.2))
    g = geom_lerp(GEOM_3D, G_MODEL, mv)
    # block motion: continues the 3D decay, then a fresh pluck once in place
    t_pluck1 = t_in + 2.3
    if t < t_pluck1:
        x = x_3d(t)
    else:
        x = rig_free(t, t_pluck1, 38.0, 1.0, 1.0) + x_3d(t) * (1 - smooth(ramp(t, t_pluck1, t_pluck1 + 0.35)))
    fade_out = 1 - smooth(ramp(t, S["sweep"][0] - 0.6, S["sweep"][0]))
    draw_rig(c, g, x, alpha=1.0, draw=smooth(k_bp) if k_bp < 1 else 1.0, labels=True,
             label_alpha=fade(t, t_in + 2.2, None, 0.4), k_label="k", c_label="c")
    note(c, "1.0 Hz", 1060, G_MODEL["axis_y"] + 10, 30, "paper", fade(t, t_pluck1, None, 0.4) * fade_out, style="semibold")
    # equation
    a_eq = fade(t, t_two - 0.2, None, 0.5) * fade_out
    if a_eq > 0:
        hk = fade(t, t_stiff - 0.1, t_heavy - 0.1, 0.3, 0.3)
        hm = fade(t, t_heavy - 0.1, None, 0.3)
        kcol = r"\ch{k}" if hk > 0.5 else "k"
        mcol = r"\ch{m}" if hm > 0.5 else "m"
        eq = tex(f"wn_{kcol}_{mcol}", r"\omega_n = \sqrt{\frac{" + kcol + "}{" + mcol + r"}}", 64)
        eq.draw(c, 1560, 330, col("paper", a_eq), anchor="center")
        note(c, "natural rhythm", 1560, 200, 24, "steel", a_eq, anchor="center", style="semibold")
        f_eq = tex("fn", r"f_n = \frac{\omega_n}{2\pi}", 40)
        f_eq.draw(c, 1560, 470, col("steel", a_eq), anchor="center")
    # 3) stiffer spring: twice as fast (the wire is 1.41x thicker: k grows as d^4)
    a2 = fade(t, t_stiff - 0.1, None, 0.5)
    if a2 > 0:
        g2 = rig_geom(250, 560, 1.55, 1.0, 4.0)
        x2 = rig_free(t, t_stiff + 0.2, 38.0, 1.0, 4.0)
        dy = 30 * (1 - ease_out(ramp(t, t_stiff - 0.1, t_stiff + 0.5)))
        g2["axis_y"] += dy
        draw_rig(c, g2, x2, alpha=a2 * fade_out, labels=True, k_label=r"4k", c_label="c", label_alpha=1.0)
        note(c, "2.0 Hz", 1060, 570 + dy, 30, "paper", a2 * fade_out, style="semibold")
        note(c, "stiffer spring: twice as fast", 1060, 610 + dy, 22, "steel", a2 * fade_out)
    # 4) heavier mass: half as fast
    a3 = fade(t, t_heavy - 0.1, None, 0.5)
    if a3 > 0:
        g3 = rig_geom(250, 830, 1.55, 4.0, 1.0)
        x3 = rig_free(t, t_heavy + 0.2, 38.0, 4.0, 1.0)
        dy = 30 * (1 - ease_out(ramp(t, t_heavy - 0.1, t_heavy + 0.5)))
        g3["axis_y"] += dy
        draw_rig(c, g3, x3, alpha=a3 * fade_out, labels=True, block_label="4m", c_label="c")
        note(c, "0.5 Hz", 1060, 840 + dy, 30, "paper", a3 * fade_out, style="semibold")
        note(c, "heavier mass: half as fast", 1060, 880 + dy, 22, "steel", a3 * fade_out)


# ------------------------------------------------------------------ the sweep

SWEEP0 = S["sweep"][0]
G_SWEEP = rig_geom(150, 420, 1.9)
AX_SWEEP = (1010, 150, 790, 560)


@functools.lru_cache(maxsize=1)
def sweep_schedule():
    knots = [(SWEEP0 - 1.0, 0.2), (at("L10") - 0.3, 0.2), (at("L11") - 0.9, 0.5), (at("L11") - 0.2, 0.5),
             (end("L11") + 0.1, 0.94), (at("L12") - 0.2, 0.94), (at("L12") + 1.6, 1.0),
             (at("L14") - 0.3, 1.0), (end("L14"), 2.0), (S["damping"][0] + 0.3, 2.0),
             (S["damping"][0] + 1.7, 1.0), (S["damping"][1] + 1.0, 1.0)]
    slow = (at("L13") + 0.5, end("L13") - 0.4)
    ts = np.arange(SWEEP0 - 1.0, S["damping"][1] + 1.0, 1 / 600)
    r = np.empty_like(ts)
    kt = [k[0] for k in knots]
    for i, tt in enumerate(ts):
        j = max(0, min(len(knots) - 2, np.searchsorted(kt, tt) - 1))
        (t0, r0), (t1, r1) = knots[j], knots[j + 1]
        u = smooth((tt - t0) / (t1 - t0)) if t1 > t0 else 1.0
        r[i] = r0 + (r1 - r0) * u
    speed = 1.0 - 0.78 * np.array([smooth(ramp(tt, slow[0], slow[0] + 0.6)) *
                                   (1 - smooth(ramp(tt, slow[1] - 0.6, slow[1]))) for tt in ts])
    psi = np.concatenate([[0.0], np.cumsum(0.5 * (r[1:] * speed[1:] + r[:-1] * speed[:-1]) * np.diff(ts))]) * P.WN
    r_max = np.maximum.accumulate(np.where(ts < S["damping"][0], r, 0))
    return ts, r, speed, psi, r_max, slow


def sweep_state(t):
    ts, r, speed, psi, r_max, slow = sweep_schedule()
    i = min(len(ts) - 1, max(0, int((t - ts[0]) * 600)))
    rr, ps = r[i], psi[i]
    env = smooth(ramp(t, at("L09") + 0.3, at("L09") + 1.6))
    A = float(P.amplification(rr))
    lag = float(P.phase_lag(rr))
    x_mm = env * P.X_STATIC * 1000 * A * math.cos(ps - lag)
    F = env * math.cos(ps)
    v = -env * A * rr * math.sin(ps - lag)          # in units of X_static·ωn
    return dict(r=rr, psi=ps, A=A, lag=lag, x=x_mm, F=F, v=v, env=env, r_max=r_max[i], speed=speed[i])


def draw_power(c, st, x0, y0, w, h, alpha, highlight=0.0):
    """Power into the mass P = F·v over the last two cycles: always >= 0 only at resonance."""
    ps = np.linspace(st["psi"] - 4 * math.pi, st["psi"], 240)
    A, lag, r = st["A"], st["lag"], st["r"]
    Pw = st["env"] * np.cos(ps) * (-A * r * np.sin(ps - lag)) / 10.0
    base = y0 + h / 2
    xs = x0 + np.linspace(0, w, len(ps))
    ys = base - Pw * h / 2
    c.drawLine(x0, base, x0 + w, base, paint(col("steel", 0.4 * alpha), stroke=True, width=1.2))
    pos = skia.Path()
    pos.moveTo(xs[0], base)
    for X, Y in zip(xs, np.minimum(ys, base)):
        pos.lineTo(X, Y)
    pos.lineTo(xs[-1], base)
    pos.close()
    c.drawPath(pos, paint(col("energy", 0.35 * alpha)))
    path = ep.polyline_path(list(zip(xs, ys)))
    c.drawPath(path, paint(col("energy", alpha), stroke=True, width=2.6))
    note(c, "energy flowing into the mass each moment  (P = F·v)", x0, y0 - 14, 19, "energy", alpha, style="semibold")
    if highlight > 0:
        note(c, "always ≥ 0: every push adds energy", x0, y0 + h + 30, 22, "highlight", alpha * highlight,
             style="semibold")


def graph_curve_points(zeta=P.ZETA):
    rs = np.linspace(0, 2.1, 900)
    return rs, P.amplification(rs, zeta)


def draw_axes_labels(c, ax, alpha):
    ax.draw_axes(c, alpha)
    ax.ticks_x(c, [0, 0.5, 1, 1.5, 2], ["0", "0.5", "1", "1.5", "2"], alpha=alpha)
    ax.ticks_y(c, [0, 1, 5, 10], ["0", "1", "5", "10"], alpha=alpha)
    ax.gridlines_y(c, [1, 5, 10], alpha=0.1 * alpha)
    note(c, "push rhythm", ax.x + ax.w, ax.y + ax.h + 78, 22, "steel", alpha, anchor="right", style="semibold")
    tex("xl", r"\omega/\omega_n", 30).draw(c, ax.x + ax.w - 150, ax.y + ax.h + 79, col("steel", alpha), anchor="right")
    note(c, "size of the motion", ax.x - 4, ax.y - 30, 22, "steel", alpha, style="semibold")
    tex("yl", r"X \,/\, (F_0/k)", 30).draw(c, ax.x + 214, ax.y - 30, col("steel", alpha))


def draw_sweep_core(c, t, st, alpha=1.0, graph_alpha=1.0, rig_alpha=1.0, ax_box=AX_SWEEP, heat=0.0,
                    show_power=True, power_alpha=1.0, cursor_alpha=1.0, peak_alpha=1.0, phase_alpha=1.0,
                    readout_alpha=1.0):
    # rig
    if rig_alpha > 0:
        draw_rig(c, G_SWEEP, st["x"], alpha=rig_alpha * alpha, force=st["F"] if st["env"] > 0.01 else None,
                 vel=st["v"] / 10.5 if st["env"] > 0.01 else None, heat=heat, labels=True,
                 k_label="k", c_label="c")
        al = rig_alpha * alpha * st["env"]
        if al > 0:
            bx = G_SWEEP["wall_x"] + (REST_MM + st["x"]) * G_SWEEP["s"] + BLOCK_MM * G_SWEEP["s"] / 2
            right = bx + BLOCK_MM * G_SWEEP["s"] / 2
            tex("F", r"\cf{F}", 36).draw(c, right + 40, G_SWEEP["axis_y"] - 32, col("force", al))
            av = al * smooth(ramp(st["A"] * st["r"], 0.5, 1.6))
            if av > 0:
                tex("v", r"\cm{v}", 36).draw(c, bx - 10, G_SWEEP["axis_y"] - BLOCK_MM * G_SWEEP["s"] / 2 - 58,
                                              col("motion", av))
        # readouts
        ra = rig_alpha * alpha * readout_alpha * fade(t, at("L09") + 0.4, None, 0.5)
        if ra > 0:
            note(c, "push rhythm", 150, 640, 22, "steel", ra, style="semibold")
            ep.Text(f"{st['r']:.2f} × natural", 34, "semibold").draw(c, 150, 686, col("paper", ra))
            note(c, "size of the motion", 520, 640, 22, "steel", ra, style="semibold")
            ep.Text(f"± {abs(P.X_STATIC * 1000 * st['A'] * st['env']):.0f} mm", 34, "semibold").draw(
                c, 520, 686, col("paper", ra))
            note(c, "drawn to scale  ·  steady motion shown at each push rhythm", 150, 735, 19, "steel", ra * 0.85)
    if show_power and rig_alpha > 0:
        pa = rig_alpha * alpha * power_alpha * fade(t, at("L10"), None, 0.6)
        if pa > 0:
            hl = fade(t, at("L13", "So every push") - 0.3, end("L13") + 0.3, 0.4, 0.4)
            draw_power(c, st, 150, 830, 700, 110, pa, highlight=hl)
    # graph
    if graph_alpha > 0:
        ga = graph_alpha * alpha
        ax = Axes(*ax_box, xlim=(0, 2.1), ylim=(0, 11))
        draw_axes_labels(c, ax, ga * fade(t, at("L09") + 0.2, None, 0.6))
        rs, amp = graph_curve_points()
        if st["r_max"] > 0.2:
            ax.fill_under(c, rs, amp, x_max=st["r_max"], alpha=0.10 * ga)
            ax.plot(c, rs, amp, x_max=st["r_max"], width=4, alpha=ga)
        # natural rhythm guide
        a_nr = ga * fade(t, at("L11") + 2.0, None, 0.5)
        if a_nr > 0:
            X = ax.px_x(1.0)
            p = paint(col("steel", 0.5 * a_nr), stroke=True, width=1.5)
            p.setPathEffect(skia.DashPathEffect.Make([5, 7], 0))
            c.drawLine(X, ax.y, X, ax.y + ax.h, p)
            note(c, "natural rhythm", X + 12, ax.y + 14, 20, "steel", a_nr, style="semibold")
        # live cursor
        if st["env"] > 0.01 and cursor_alpha > 0:
            ax.dot(c, st["r"], st["A"], "motion", r=8, alpha=ga * cursor_alpha, ring=4)
        # peak highlight
        a_pk = ga * peak_alpha * fade(t, at("L12", "the motion is ten times") - 0.2, None, 0.4)
        if a_pk > 0:
            X, Y = ax.px(1.0, 10.0)
            k = ease_out_back(ramp(t, at("L12", "the motion is ten times") - 0.2, at("L12", "the motion is ten times") + 0.4))
            c.drawCircle(X, Y, 20 * k, paint(col("highlight", a_pk), stroke=True, width=3))
            label_box(c, X + 34, Y - 6, "× 10", 30, "highlight", 0.8, "bold", alpha=a_pk)
        # phase lag readout (engineers)
        a_ph = ga * fade(t, at("L10") + 0.5, None, 0.5)
        if a_ph > 0:
            deg = math.degrees(st["lag"])
            if phase_alpha > 0:
                note(c, "the motion lags the push by", ax.x + 20, ax.y + ax.h + 140, 20, "steel", a_ph * phase_alpha)
                ep.Text(f"{deg:3.0f}°", 30, "semibold").draw(c, ax.x + 300, ax.y + ax.h + 142,
                                                            col("paper", a_ph * phase_alpha))
            tex("eom", r"m\ddot{\cm{x}} + c\dot{\cm{x}} + k\cm{x} = \cf{F_0\cos\omega t}", 38).draw(
                c, ax.x + ax.w, ax.y + ax.h + 222, col("paper", a_ph), anchor="right")


def draw_sweep(c, t):
    fx.background(c)
    st = sweep_state(t)
    a_in = smooth(ramp(t, SWEEP0, SWEEP0 + 0.6))
    # the rig slides from the model layout to the sweep layout
    mv = ease_in_out(ramp(t, SWEEP0, SWEEP0 + 1.0))
    g = geom_lerp(G_MODEL, G_SWEEP, mv)
    if mv < 1:
        draw_rig(c, g, rig_free(t, S["spring_model"][0] + 2.3, 38.0, 1.0, 1.0) * (1 - mv) + st["x"] * mv,
                 labels=True)
        return
    draw_sweep_core(c, t, st)
    # slow motion tag during the key idea
    ts, r, speed, psi, r_max, slow = sweep_schedule()
    a_sl = fade(t, slow[0], slow[1], 0.4, 0.4)
    if a_sl > 0:
        exaggeration_tag(c, "slowed down × 4", 150, 236, alpha=a_sl)
        note(c, "push and motion in step", 150, 190, 26, "highlight", a_sl, style="semibold")


# ------------------------------------------------------------------ damping

DAMP0 = S["damping"][0]


def draw_damping(c, t):
    fx.background(c)
    st = sweep_state(t)
    t_d = at("L15", "Damping:")
    t5 = at("L16", "With 5")
    t10 = at("L16", "Double the damping")
    t30 = at("L16", "At 30")
    # phase 1: rig at resonance again, the damper glows (motion turned into heat)
    grow = ease_in_out(ramp(t, at("L16") - 0.2, at("L16") + 1.2))
    rig_a = 1 - smooth(ramp(t, at("L16") - 0.4, at("L16") + 0.4))
    v2 = (st["v"] / 10.5) ** 2
    heat = fade(t, t_d - 0.3, None, 0.6) * v2
    ax0 = AX_SWEEP
    ax1 = (250, 170, 1420, 660)
    box = tuple(lerp(a, b, grow) for a, b in zip(ax0, ax1))
    draw_sweep_core(c, t, st, rig_alpha=rig_a, ax_box=box, heat=heat, power_alpha=1 - fade(t, t_d - 0.5, None, 0.5),
                    cursor_alpha=1 - smooth(ramp(t, at("L16") - 0.4, at("L16") + 0.2)),
                    peak_alpha=1 - smooth(ramp(t, t5 - 0.6, t5 - 0.1)), phase_alpha=rig_a,
                    readout_alpha=1 - smooth(ramp(t, t_d - 0.6, t_d - 0.1)))
    if rig_a > 0:
        a_l = rig_a * fade(t, t_d - 0.2, None, 0.4)
        if a_l > 0:
            dx = G_SWEEP["wall_x"] + 120
            dy = G_SWEEP["axis_y"] + G_SWEEP["damper_dy"] + 70
            label_box(c, dx, dy + 40, "damper: turns motion into heat", 24, "energy", 0.8, "semibold", alpha=a_l)
            chips = [("friction", at("L15", "like friction")), ("oil in a shock absorber", at("L15", "or the oil"))]
            x = dx
            for name, tc in chips:
                ac = rig_a * fade(t, tc - 0.1, None, 0.3)
                if ac > 0:
                    r_ = label_box(c, x, dy + 100, name, 21, "paper", 0.7, "medium", alpha=ac)
                    x = r_.right() + 14
    # phase 2: three damping levels, like the series banner (opacity 1, 0.6, 0.35 + labels)
    if grow > 0:
        ax = Axes(*box, xlim=(0, 2.1), ylim=(0, 11))
        levels = [(0.05, 1.0, t5, "ζ = 5 %", "× 10"), (0.10, 0.62, t10, "ζ = 10 %", "× 5"),
                  (0.30, 0.4, t30, "ζ = 30 %", "× 1.7")]
        for z, op, tz, name, gain in levels:
            u = ease_in_out(ramp(t, tz - 0.2, tz + 1.3))
            if z == 0.05:
                u = 1.0
            if u <= 0:
                continue
            rs, amp = graph_curve_points(z)
            path = ax.curve_path(rs, amp)
            path = ep.trim_path(path, u) if u < 1 else path
            c.drawPath(path, paint(col("motion", 0.4 * op), stroke=True, width=10, blur=6))
            c.drawPath(path, paint(col("motion", op), stroke=True, width=4.2))
            rp, pk = P.peak(z)
            la = fade(t, tz + (0.9 if z > 0.05 else 0.0), None, 0.4) * grow
            if la > 0:
                X, Y = ax.px(rp, pk)
                c.drawCircle(X, Y, 7, paint(col("highlight", la)))
                label_box(c, X + 24, Y - 4 - (0 if z < 0.3 else 36), f"{name}   {gain}", 26, "paper", 0.8, "semibold",
                          alpha=la)
        # formula
        a_f = fade(t, at("L17") - 0.3, None, 0.5)
        if a_f > 0:
            eq = tex("peak", r"\frac{X_{\mathrm{peak}}}{F_0/k} \approx \frac{1}{2\zeta}"
                             r"\qquad \zeta = \frac{c}{2\sqrt{km}}", 44)
            tex_box(c, 1180, 330, eq, alpha=a_f)
            note(c, "damping: the engineer's brake on resonance", 1180, 440, 24, "balance", a_f, style="semibold")
    a_out = smooth(ramp(t, S["damping"][1] - 0.6, S["damping"][1]))
    if a_out > 0:
        c.drawRect(skia.Rect.MakeWH(W, H), paint(col("ink", a_out)))


def push_times():
    """Times of the push peaks (F = +F0) during the sweep and damping scenes, as shown on screen."""
    ts, r, speed, psi, r_max, slow = sweep_schedule()
    t_start = at("L09") + 0.6
    t_end = at("L16") + 0.3
    k = np.floor(psi / (2 * np.pi))
    idx = np.nonzero(np.diff(k) > 0)[0] + 1
    return [(float(ts[i]), float(r[i])) for i in idx if t_start <= ts[i] <= t_end]
