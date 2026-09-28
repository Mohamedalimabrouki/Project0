"""
Resonance - every motion in the video, computed from the equations.

Nothing in the video is animated by eye. The Blender scenes and the 2D
graphics both read their motion from the functions in this file.

SI units everywhere: m, kg, s, N, rad.
"""

import numpy as np
from scipy.integrate import solve_ivp

G = 9.81          # m/s², gravitational acceleration
FPS = 30          # frames per second of the video

# ---------------------------------------------------------------------------
# 1. The swing: a nonlinear pendulum with light damping and short pushes
#
#    θ'' = -(g/L)·sin θ - 2·ζ·ωn·θ' + a_push(t)
#
#    a_push is a half-sine pulse (a hand push lasting PUSH_DURATION), the same
#    size for every push. A positive push is forward (away from the pusher).
# ---------------------------------------------------------------------------

SWING_L = 2.0                          # m, chain length (pivot to seat)
SWING_WN = np.sqrt(G / SWING_L)        # rad/s, small-angle natural frequency
SWING_T = 2 * np.pi / SWING_WN         # s, 2.84 s
SWING_ZETA = 0.01                      # air drag and chain friction, light
PUSH_DURATION = 0.35                   # s
PUSH_PEAK = 1.9                        # rad/s², peak angular acceleration of a push
PUSH_COUNT = 7


def _pendulum(push_times, t_end, theta0=0.0, omega0=0.0, dt=1 / 240):
    push_times = np.asarray(sorted(push_times), dtype=float)

    def push(t):
        active = (t >= push_times) & (t < push_times + PUSH_DURATION)
        if not np.any(active):
            return 0.0
        phase = (t - push_times[active]) / PUSH_DURATION
        return PUSH_PEAK * np.sum(np.sin(np.pi * phase))

    def rhs(t, y):
        th, om = y
        return [om, -(G / SWING_L) * np.sin(th) - 2 * SWING_ZETA * SWING_WN * om + push(t)]

    ts = np.arange(0.0, t_end + dt / 2, dt)
    sol = solve_ivp(rhs, (0.0, ts[-1]), [theta0, omega0], t_eval=ts,
                    max_step=dt, rtol=1e-9, atol=1e-11)
    return sol.t, sol.y[0], sol.y[1]


def swing_in_rhythm(first_push=2.6, count=PUSH_COUNT, t_end=24.0):
    """Push once per swing, each time the seat leaves the back of its arc."""
    pushes = [first_push]
    while len(pushes) < count:
        t, th, om = _pendulum(pushes, t_end)
        # next back turning point: angular velocity crosses zero going forward
        after = np.where((t[1:] > pushes[-1] + 0.8) & (om[:-1] < 0) & (om[1:] >= 0))[0]
        pushes.append(float(t[after[0] + 1]))
    t, th, om = _pendulum(pushes, t_end)
    return dict(t=t, theta=th, omega=om, pushes=np.array(pushes))


def swing_at_random(first_push=2.6, count=PUSH_COUNT, t_end=24.0, window_end=None,
                    trials=1000, seed=2024):
    """
    Same pushes, same count, same first push, but the other pushes land at
    random moments. To stay honest we run many random trials and show the
    one whose final amplitude is the median, i.e. a typical case, not a
    cherry-picked one.
    """
    rng = np.random.default_rng(seed)
    if window_end is None:
        window_end = first_push + (count - 1) * SWING_T * 1.02
    candidates = []
    for _ in range(trials):
        while True:
            others = np.sort(rng.uniform(first_push + 0.8, window_end, count - 1))
            gaps = np.diff(np.concatenate([[first_push], others]))
            if np.all(gaps > 0.9):     # a person cannot push faster than this
                break
        candidates.append(np.concatenate([[first_push], others]))
    finals = []
    for p in candidates:
        t, th, om = _pendulum(p, t_end, dt=1 / 60)
        finals.append(np.max(np.abs(th[t > t_end - SWING_T])))
    finals = np.array(finals)
    median_index = int(np.argsort(finals)[len(finals) // 2])
    pushes = candidates[median_index]
    t, th, om = _pendulum(pushes, t_end)
    return dict(t=t, theta=th, omega=om, pushes=pushes,
                trial_finals=finals, chosen_final=finals[median_index])


def swing_pull_and_release(pull_start=3.2, pull_time=1.3, hold=0.7,
                           theta_pull=np.radians(-22.0), t_end=14.0):
    """
    A hand pulls the seat back slowly (kinematic, eased), holds, and lets go.
    After release the swing moves freely: this shows its natural rhythm.
    """
    release = pull_start + pull_time + hold
    t_free, th_free, om_free = _pendulum([], t_end - release, theta0=theta_pull)
    dt = 1 / 240
    t = np.arange(0.0, t_end + dt / 2, dt)
    theta = np.zeros_like(t)
    omega = np.zeros_like(t)
    for i, ti in enumerate(t):
        if ti < pull_start:
            theta[i] = 0.0
        elif ti < pull_start + pull_time:
            u = (ti - pull_start) / pull_time
            theta[i] = theta_pull * (0.5 - 0.5 * np.cos(np.pi * u))
        elif ti < release:
            theta[i] = theta_pull
        else:
            theta[i] = np.interp(ti - release, t_free, th_free)
            omega[i] = np.interp(ti - release, t_free, om_free)
    return dict(t=t, theta=theta, omega=omega, release=release, theta_pull=theta_pull)


def sample(series, t_query):
    """Sample a simulated series at the given times (for example frame times)."""
    return np.interp(t_query, series["t"], series["theta"])


# ---------------------------------------------------------------------------
# 2. The mass on a spring (with a damper): the engineer's model
#
#    m·x'' + c·x' + k·x = F0·cos(ω·t)
#
#    Real, buildable numbers: a 2 kg steel block (a 63 mm cube), a spring of
#    1.5 mm wire, 30 mm coil diameter, about 23 coils (k ≈ 79 N/m), so the
#    natural frequency is exactly 1 Hz. Damping ratio 5 %.
# ---------------------------------------------------------------------------

MASS = 2.0                                   # kg
FN = 1.0                                     # Hz, natural frequency
WN = 2 * np.pi * FN                          # rad/s
STIFFNESS = MASS * WN ** 2                   # N/m, 78.96
ZETA = 0.05                                  # damping ratio of the model
DAMPING = 2 * ZETA * np.sqrt(STIFFNESS * MASS)   # N·s/m, 1.26
F0 = 0.5                                     # N, amplitude of the push
X_STATIC = F0 / STIFFNESS                    # m, 6.3 mm: what a very slow push gives
BLOCK_SIDE = (MASS / 7850.0) ** (1 / 3)      # m, 63 mm steel cube


def amplification(r, zeta=ZETA):
    """Steady-state amplitude X divided by the static deflection F0/k."""
    r = np.asarray(r, dtype=float)
    return 1.0 / np.sqrt((1 - r ** 2) ** 2 + (2 * zeta * r) ** 2)


def phase_lag(r, zeta=ZETA):
    """How far the motion lags behind the push, in rad (0 slow, π/2 at resonance, π fast)."""
    r = np.asarray(r, dtype=float)
    return np.arctan2(2 * zeta * r, 1 - r ** 2)


def peak(zeta):
    """Height and position of the true peak (exists for ζ < 1/√2)."""
    r_peak = np.sqrt(1 - 2 * zeta ** 2)
    return r_peak, 1.0 / (2 * zeta * np.sqrt(1 - zeta ** 2))


def free_decay(t, x0, zeta=ZETA, wn=WN):
    """Released from rest at x0: x(t) = x0·e^(-ζωn·t)·(cos ωd·t + ζ/√(1-ζ²)·sin ωd·t)."""
    t = np.asarray(t, dtype=float)
    wd = wn * np.sqrt(1 - zeta ** 2)
    env = np.exp(-zeta * wn * t)
    x = x0 * env * (np.cos(wd * t) + zeta / np.sqrt(1 - zeta ** 2) * np.sin(wd * t))
    return np.where(t < 0, x0, x)


def free_decay_general(t, x0, mass, stiffness, zeta=ZETA):
    wn = np.sqrt(stiffness / mass)
    return free_decay(t, x0, zeta=zeta, wn=wn)


def sweep_response(t, r_of_t, zeta=ZETA, ramp=1.2):
    """
    Steady-state motion while the push rhythm changes slowly (a sped-up
    stepped-sine test). The start-up transient is not shown, as stated in
    the README assumptions. The push fades in over `ramp` seconds.

    Returns force (N), displacement (m), velocity (m/s), drive phase ψ.
    """
    t = np.asarray(t, dtype=float)
    r = r_of_t(t)
    omega = r * WN
    # drive phase ψ(t) = ∫ ω dt, integrated on a fine grid for accuracy
    fine = np.linspace(t[0], t[-1], max(2000, 40 * len(t)))
    om_f = r_of_t(fine) * WN
    psi_f = np.concatenate([[0.0], np.cumsum(0.5 * (om_f[1:] + om_f[:-1]) * np.diff(fine))])
    psi = np.interp(t, fine, psi_f)
    env = np.clip((t - t[0]) / ramp, 0, 1)
    env = env * env * (3 - 2 * env)
    amp = X_STATIC * amplification(r, zeta)
    lag = phase_lag(r, zeta)
    force = env * F0 * np.cos(psi)
    x = env * amp * np.cos(psi - lag)
    v = -env * amp * omega * np.sin(psi - lag)
    return dict(t=t, r=r, force=force, x=x, v=v, psi=psi, amp=amp, lag=lag)


# ---------------------------------------------------------------------------
# 3. Taipei 101: a building mode with a tuned mass damper (two masses)
#
#    Building mode:  M·x'' + C·x' + K·x = F_wind(t) + k_d·(y - x) + c_d·(y' - x')
#    Damper ball:    m_d·y'' = -k_d·(y - x) - c_d·(y' - x')
#
#    Tuned with Den Hartog's classic rules. Values are representative, not
#    the exact design data (which is not public in full).
# ---------------------------------------------------------------------------

TOWER_PERIOD = 6.8                      # s, measured first sway mode (Chen et al. 2012: about 0.15 Hz)
TOWER_WN = 2 * np.pi / TOWER_PERIOD
TOWER_ZETA = 0.02                       # structural damping used in the published design model
TMD_MASS_RATIO = 0.0125                 # 660 t / about 52 700 t modal mass (Chung et al. 2013)


def tmd_parameters(mu=TMD_MASS_RATIO):
    f_opt = 1.0 / (1.0 + mu)                                   # Den Hartog tuning
    zeta_opt = np.sqrt(3 * mu / (8 * (1 + mu) ** 3))           # Den Hartog damping
    return f_opt, zeta_opt


def tmd_steady_state(r, mu=TMD_MASS_RATIO, with_damper=True):
    """
    Complex steady-state amplitudes per unit static deflection for harmonic
    wind forcing at frequency ratio r (relative to the bare tower).
    Returns (X_tower, Y_ball) as complex numbers.
    """
    f_opt, z_d = tmd_parameters(mu)
    w = np.asarray(r, dtype=float)                             # ω / ωn (ωn = 1)
    if not with_damper:
        X = 1.0 / (1 - w ** 2 + 2j * TOWER_ZETA * w)
        return X, np.zeros_like(X)
    wd = f_opt
    kd = mu * wd ** 2
    cd = 2 * z_d * mu * wd
    a11 = 1 - w ** 2 + 2j * TOWER_ZETA * w + kd + 1j * w * cd
    a12 = -(kd + 1j * w * cd)
    a22 = kd + 1j * w * cd - mu * w ** 2
    det = a11 * a22 - a12 * a12
    X = a22 / det
    Y = -a12 / det
    return X, Y


def tmd_time_series(t, r=1.0, mu=TMD_MASS_RATIO, with_damper=True, ramp=0.0):
    """Steady-state sway of the tower and the ball (arbitrary units) at forcing ratio r."""
    X, Y = tmd_steady_state(r, mu, with_damper)
    psi = r * TOWER_WN * np.asarray(t, dtype=float)
    x = np.real(X * np.exp(1j * psi))
    y = np.real(Y * np.exp(1j * psi))
    return x, y, X, Y


if __name__ == "__main__":
    print(f"Swing period (small angles): {SWING_T:.3f} s")
    rhythm = swing_in_rhythm()
    print("Rhythm pushes (s):", np.round(rhythm["pushes"], 2))
    print(f"Rhythm swing max angle: {np.degrees(np.max(np.abs(rhythm['theta']))):.1f} deg")
    rand = swing_at_random()
    print("Random pushes (s):", np.round(rand["pushes"], 2))
    print(f"Random swing max angle: {np.degrees(np.max(np.abs(rand['theta']))):.1f} deg; "
          f"median final amplitude over trials {np.degrees(rand['chosen_final']):.1f} deg; "
          f"90th percentile {np.degrees(np.percentile(rand['trial_finals'], 90)):.1f} deg")
    print(f"Mass {MASS} kg, k {STIFFNESS:.2f} N/m, c {DAMPING:.3f} N·s/m, block side {BLOCK_SIDE*1000:.1f} mm")
    print(f"Static deflection {X_STATIC*1000:.2f} mm, at resonance {X_STATIC*amplification(1.0)*1000:.1f} mm")
    for z in (0.05, 0.1, 0.3):
        rp, pk = peak(z)
        print(f"zeta {z}: at r=1 {amplification(1.0, z):.2f}, true peak {pk:.3f} at r={rp:.3f}")
    f_opt, z_d = tmd_parameters()
    X0, _ = tmd_steady_state(1.0, with_damper=False)
    X1, Y1 = tmd_steady_state(1.0)
    rs = np.linspace(0.8, 1.2, 4001)
    Xw, _ = tmd_steady_state(rs)
    X_no, _ = tmd_steady_state(rs, with_damper=False)
    print(f"TMD tuning {f_opt:.4f}, damper zeta {z_d:.4f}")
    print(f"Tower at r=1: no damper |X|={abs(X0):.1f}, with damper |X|={abs(X1):.2f}; "
          f"peak over r: no damper {np.max(abs(X_no)):.1f}, with damper {np.max(abs(Xw)):.2f}")
    print(f"Ball vs tower at r=1: |Y/X|={abs(Y1/X1):.2f}, phase of ball behind tower "
          f"{np.degrees(np.angle(X1) - np.angle(Y1)):.1f} deg")


# ---------------------------------------------------------------------------
# Cache: the random-trial search takes a couple of minutes, so the swing
# results are computed once and stored in build/data/swings.npz
# ---------------------------------------------------------------------------

def swing_data(cache_dir):
    import os
    path = os.path.join(cache_dir, "swings.npz")
    if os.path.exists(path):
        d = np.load(path)
        return {k: d[k] for k in d.files}
    os.makedirs(cache_dir, exist_ok=True)
    rhythm = swing_in_rhythm()
    rand = swing_at_random()
    pull = swing_pull_and_release()
    out = dict(
        t=rhythm["t"], rhythm_theta=rhythm["theta"], rhythm_omega=rhythm["omega"],
        rhythm_pushes=rhythm["pushes"],
        random_theta=np.interp(rhythm["t"], rand["t"], rand["theta"]),
        random_omega=np.interp(rhythm["t"], rand["t"], rand["omega"]),
        random_pushes=rand["pushes"], random_trial_finals=rand["trial_finals"],
        pull_t=pull["t"], pull_theta=pull["theta"], pull_omega=pull["omega"],
        pull_release=np.array(pull["release"]), pull_theta_pull=np.array(pull["theta_pull"]),
    )
    np.savez(path, **out)
    return out


def push_work(theta_t, omega_series, pushes):
    """
    Energy added by each push, per unit of m·L² (J per kg·m²):
    W = ∫ a_push(t)·ω(t) dt. Positive: the push helped. Negative: it fought the swing.
    """
    t = theta_t
    works = []
    for tp in pushes:
        m = (t >= tp) & (t < tp + PUSH_DURATION)
        a = PUSH_PEAK * np.sin(np.pi * (t[m] - tp) / PUSH_DURATION)
        works.append(float(np.trapz(a * omega_series[m], t[m])))
    return np.array(works)


def pull_data(cache_dir):
    """The single swing that is pulled back and let go (cached in build/data/pull.npz)."""
    import os
    path = os.path.join(cache_dir, "pull.npz")
    if os.path.exists(path):
        d = np.load(path)
        return {k: d[k] for k in d.files}
    os.makedirs(cache_dir, exist_ok=True)
    pull = swing_pull_and_release()
    out = dict(t=pull["t"], theta=pull["theta"], omega=pull["omega"],
               release=np.array(pull["release"]), theta_pull=np.array(pull["theta_pull"]))
    np.savez(path, **out)
    return out
