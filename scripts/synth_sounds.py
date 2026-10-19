"""Offline stand-ins for the starter pack, generated with numpy.

Used when a download fails (or with ``download_assets.py --synth``), and for
sounds with no suitable free recording. Every generator is periodic over the
clip length (FFT-shaped noise, whole-cycle modulation, wrapped impulses), so
the result loops with no seam.
"""

import numpy as np

SR = 44100
SECONDS = 30
N = SR * SECONDS
T = np.arange(N) / SR


def noise(rng, shape, channels=2):
    """Noise whose amplitude spectrum is ``shape(freq_hz)``; periodic over N samples."""
    freqs = np.maximum(np.fft.rfftfreq(N, 1 / SR), 1.0)
    out = []
    for _ in range(channels):
        spec = (rng.normal(size=freqs.size) + 1j * rng.normal(size=freqs.size)) * shape(freqs)
        spec[0] = 0
        x = np.fft.irfft(spec, N)
        out.append(x / np.abs(x).max())
    return np.stack(out, axis=1)


def lowpass(fc):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** 4)


def highpass(fc):
    return lambda f: 1 / np.sqrt(1 + (fc / f) ** 4)


def lfo(cycles, phase=0.0):
    """Slow modulation with a whole number of cycles per clip (keeps the loop seamless)."""
    return 0.5 - 0.5 * np.cos(2 * np.pi * cycles * T / SECONDS + phase)


def hits(times, kernel, amps=None):
    """Mono track with ``kernel`` added at each time (seconds), wrapping at the end."""
    out = np.zeros(N)
    idx = np.arange(len(kernel))
    for i, t in enumerate(times):
        out[(int(t * SR) + idx) % N] += kernel * (1.0 if amps is None else amps[i])
    return out


def tone(freq, ms, decay_ms):
    t = np.arange(int(SR * ms / 1000)) / SR
    return np.sin(2 * np.pi * freq * t) * np.exp(-t * 1000 / decay_ms)


def burst(rng, ms, decay_ms, fc=2000):
    t = np.arange(int(SR * ms / 1000)) / SR
    b = rng.normal(size=t.size)
    b = np.diff(b, prepend=0) if fc > 1000 else b  # crude high-pass for crisp crackles
    return b * np.exp(-t * 1000 / decay_ms)


def stereo(mono):
    return np.stack([mono, mono], axis=1)


def white_noise(rng):
    return noise(rng, lambda f: np.ones_like(f))


def pink_noise(rng):
    return noise(rng, lambda f: 1 / np.sqrt(f))


def brown_noise(rng):
    return noise(rng, lambda f: (1 / f) * highpass(20)(f))


def heavy_rain(rng):
    return noise(rng, lambda f: highpass(300)(f) * lowpass(9000)(f) / (f / 1000 + 1) ** 0.3)


def light_rain(rng):
    hiss = noise(rng, lambda f: highpass(1500)(f) * lowpass(7000)(f)) * 0.35
    drops = rng.uniform(0, SECONDS, 300)
    drip = hits(drops, tone(3500, 25, 6), rng.uniform(0.2, 0.6, drops.size))
    return hiss + stereo(drip) * 0.5


def thunder(rng):
    rain = light_rain(rng)
    rumble = noise(rng, lambda f: (1 / f) * lowpass(120)(f) * highpass(25)(f))
    swells = 0.15 + 0.85 * lfo(2) ** 3  # two slow, distant rolls per loop
    return rain * 0.6 + rumble * swells[:, None]


def wind(rng):
    gust = 0.55 + 0.3 * lfo(3) + 0.15 * lfo(7, 1.3)
    return noise(rng, lambda f: lowpass(350)(f) * highpass(30)(f)) * gust[:, None]


def ocean_waves(rng):
    surf = noise(rng, lambda f: lowpass(1500)(f) / np.sqrt(f))
    swell = 0.2 + 0.8 * lfo(3) ** 2  # one wave every 10 s
    return surf * swell[:, None]


def fire_crackling(rng):
    roar = noise(rng, lambda f: (1 / f) * lowpass(400)(f) * highpass(40)(f)) * 0.5
    times = rng.uniform(0, SECONDS, 240)
    crackles = sum(
        hits(times[i::4], burst(rng, 30, 4), rng.uniform(0.1, 0.8, times[i::4].size)) for i in range(4)
    )
    return roar + stereo(crackles) * 0.25


def airplane_cabin(rng):
    cabin = noise(rng, lambda f: lowpass(500)(f) * highpass(30)(f) / np.sqrt(f))
    hum = 0.04 * np.sin(2 * np.pi * 96 * T) + 0.02 * np.sin(2 * np.pi * 192 * T)
    return cabin + stereo(hum)


def train_ride(rng):
    rumble = noise(rng, lambda f: (1 / f) * lowpass(300)(f) * highpass(25)(f))
    beats = np.arange(0, SECONDS, 1.5)  # wheel joints: clack-clack every 1.5 s
    clack = hits(np.concatenate([beats, beats + 0.18]), tone(140, 120, 30))
    sway = 0.85 + 0.15 * lfo(5)
    return (rumble * 0.8 + stereo(clack) * 0.35) * sway[:, None]


def deep_space_hum(rng):
    drones = sum(
        a * np.sin(2 * np.pi * f * T)
        for f, a in ((55.0, 1.0), (55.1, 0.8), (82.5, 0.45), (110.0, 0.25))  # 55/55.1 beat slowly
    )
    air = noise(rng, lambda f: (1 / f) * lowpass(200)(f) * highpass(20)(f)) * 0.3
    return stereo(drones / 2.5) * (0.7 + 0.3 * lfo(2))[:, None] + air


def box_fan(rng):
    whoosh = noise(rng, lambda f: lowpass(1800)(f) * highpass(60)(f) / f**0.3)
    motor = 0.03 * np.sin(2 * np.pi * 60 * T) + 0.015 * np.sin(2 * np.pi * 120 * T)
    blades = 0.92 + 0.08 * np.sin(2 * np.pi * 18 * T)  # blade-pass flutter
    return whoosh * blades[:, None] + stereo(motor)


def cat_purring(rng):
    body = noise(rng, lambda f: lowpass(250)(f) * highpass(20)(f), channels=1)[:, 0]
    pulses = (0.5 + 0.5 * np.sin(2 * np.pi * 25 * T)) ** 3  # ~25 Hz purr vibration
    breath = 0.35 + 0.65 * lfo(15)  # in/out every 2 s
    return stereo(body * pulses * breath)


def heartbeat(rng):
    beats = np.arange(0, SECONDS, 1.0)  # 60 bpm, resting
    lub = hits(beats, tone(48, 160, 45))
    dub = hits(beats + 0.32, tone(62, 120, 35), np.full(beats.size, 0.6))
    return stereo(lub + dub)


def clock_ticking(rng):
    def click(freq):
        k = tone(freq, 40, 5)
        b = burst(rng, 10, 2)
        k[: b.size] += b * 0.3
        return k

    ticks = np.arange(0, SECONDS, 1.0)
    return stereo(hits(ticks[::2], click(2600)) + hits(ticks[1::2], click(2100)))


GENERATORS = {fn.__name__: fn for fn in (
    white_noise, pink_noise, brown_noise, heavy_rain, light_rain, thunder, wind, ocean_waves,
    fire_crackling, airplane_cabin, train_ride, deep_space_hum, box_fan, cat_purring, heartbeat,
    clock_ticking,
)}


def synthesize(stem: str, seed: int = 0) -> np.ndarray:
    """Return a float32 (N, 2) clip for ``stem`` at ``SR``, peak-normalised to 0.7."""
    data = GENERATORS[stem](np.random.default_rng(seed))
    return (data / np.abs(data).max() * 0.7).astype(np.float32)
