"""Decode audio files into seamless, level-matched, sensory-safe loop buffers."""

from pathlib import Path

import numpy as np
import soundfile as sf
from numpy.lib.stride_tricks import sliding_window_view

from calm import config


def load_loop(path: Path, samplerate: int, max_channels: int = 2) -> np.ndarray:
    """Load ``path`` as a float32 (frames, 1 or 2) buffer ready to loop gaplessly.

    Mono files stay mono (half the memory); the mixer spreads them to both speakers.
    """
    with sf.SoundFile(str(path)) as f:
        file_rate = f.samplerate
        data = f.read(int(config.MAX_LOOP_SECONDS * file_rate), dtype="float32", always_2d=True)
    if len(data) == 0:
        raise ValueError("file contains no audio")
    if data.shape[1] > max_channels:
        data = data.mean(axis=1, keepdims=True)
    data = _trim_silent_edges(data, file_rate)
    if file_rate != samplerate:
        data = _resample(data, file_rate, samplerate)
    if config.SOFTEN_PEAKS:
        data = _soften_peaks(data, samplerate)
    data = _normalise(data, samplerate)
    return _make_seamless(data, samplerate)


def _block_rms(data: np.ndarray, hop: int) -> np.ndarray:
    n = len(data) // hop
    return np.sqrt((data[: n * hop] ** 2).reshape(n, -1).mean(axis=1))


def _trim_silent_edges(data: np.ndarray, sr: int) -> np.ndarray:
    """Drop fade-ins/fade-outs and silence at the ends, which would cause a dip at the loop point."""
    hop = max(1, sr // 20)
    env = _block_rms(data, hop)
    if len(env) < 8:
        return data
    loud = np.nonzero(env > np.median(env) * 0.3)[0]
    if len(loud) == 0:
        return data
    return data[loud[0] * hop : (loud[-1] + 1) * hop]


def _resample(data: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    # Linear interpolation is plenty for ambient sounds.
    n_out = int(round(len(data) * dst_rate / src_rate))
    src_t = np.arange(len(data)) / src_rate
    dst_t = np.arange(n_out) / dst_rate
    out = np.empty((n_out, data.shape[1]), dtype=np.float32)
    for c in range(data.shape[1]):
        out[:, c] = np.interp(dst_t, src_t, data[:, c])
    return out


def _moving_average(x: np.ndarray, n: int) -> np.ndarray:
    """Centred moving average with the same length as ``x`` (O(len) via cumsum)."""
    pad = n // 2
    padded = np.pad(x.astype(np.float64), (pad, n - 1 - pad), mode="edge")
    c = np.concatenate(([0.0], np.cumsum(padded)))
    return (c[n:] - c[:-n]) / n


def _soften_peaks(data: np.ndarray, sr: int) -> np.ndarray:
    """Compress moments far louder than the recording's average level."""
    power = (data.astype(np.float64) ** 2).mean(axis=1)
    average = np.sqrt(power.mean())
    if average < 1e-6:
        return data
    envelope = np.sqrt(_moving_average(power, max(1, sr // 20)))  # 50 ms
    over = np.maximum(envelope / (average * config.PEAK_THRESHOLD), 1.0)
    gain = over ** (1.0 / config.PEAK_RATIO - 1.0)
    gain = _moving_average(gain, max(1, sr // 50))  # smooth to avoid pumping clicks
    return (data * gain[:, None]).astype(np.float32)


CEILING = 0.9  # peak level no track may exceed
RHYTHM_MATCH = 0.7  # envelope similarity above which a sound is treated as rhythmic


def _normalise(data: np.ndarray, sr: int) -> np.ndarray:
    """Bring the track to TARGET_RMS, limiting short transients to stay under CEILING.

    Sparse or crackly sounds (fire, clock) have high peaks but little energy;
    limiting by up to MAX_LIMIT_DB lets them reach a similar loudness to steady
    sounds without clipping, while keeping their character.
    """
    rms = float(np.sqrt(np.mean(data**2)))
    if rms < 1e-6:
        return data
    peak = float(np.abs(data).max())
    max_gain = CEILING / peak * 10 ** (config.MAX_LIMIT_DB / 20)
    data = data * np.float32(min(config.TARGET_RMS / rms, max_gain))
    return _limit_peaks(data, sr)


def _limit_peaks(data: np.ndarray, sr: int) -> np.ndarray:
    """Fast look-ahead limiter on 2.5 ms blocks; guarantees |sample| <= CEILING."""
    peak = np.abs(data).max(axis=1)
    if peak.max() <= CEILING:
        return data
    block = max(1, sr // 400)
    n = -(-len(peak) // block)
    block_max = np.pad(peak, (0, n * block - len(peak))).reshape(n, block).max(axis=1)
    g = np.minimum(1.0, CEILING / np.maximum(block_max, 1e-9))
    # Each block also takes its neighbours' gain, so interpolating between block
    # centres never lets a sample exceed the ceiling (wraps around: it is a loop).
    g = np.minimum(g, np.minimum(np.roll(g, 1), np.roll(g, -1)))
    centres = np.arange(n) * block + block / 2
    gain = np.interp(np.arange(len(peak)), centres, g).astype(np.float32)
    return data * gain[:, None]


def _make_seamless(data: np.ndarray, sr: int) -> np.ndarray:
    """Blend a later part of the file into its start with an equal-power crossfade.

    The loop end is chosen where the sound best matches the start, so rhythmic
    sounds (clock, heartbeat) keep their beat across the seam instead of
    doubling up. Playing the result on repeat has no gap, click or jump.
    """
    crossfade = min(int(config.LOOP_CROSSFADE_SECONDS * sr), len(data) // 4)
    if crossfade < 2:
        return data
    end, match = _best_loop_end(data, sr, crossfade)
    x = np.linspace(0.0, 1.0, crossfade, dtype=np.float32)[:, None]
    if match >= RHYTHM_MATCH:
        # Head and tail line up (rhythmic sound): they add like one signal, so
        # an equal-gain fade keeps the level constant.
        fade_in, fade_out = x, 1.0 - x
    else:
        # Unrelated material (noise, rain): equal-power fade avoids a dip.
        fade_in, fade_out = np.sin(x * np.pi / 2), np.cos(x * np.pi / 2)
    looped = data[:end].copy()
    looped[:crossfade] = data[:crossfade] * fade_in + data[end : end + crossfade] * fade_out
    return _limit_peaks(looped, sr)


def _best_loop_end(data: np.ndarray, sr: int, crossfade: int) -> tuple[int, float]:
    """Return (loop end frame, similarity 0..1 of the material there to the start)."""
    latest = len(data) - crossfade
    hop = max(1, sr // 100)  # 10 ms envelope resolution
    # Move the loop point back by at most 5 s or a quarter of the file.
    search = min(5 * sr, latest - crossfade, len(data) // 4)
    if search < 4 * hop:
        return latest, 0.0
    env = _block_rms(data, hop)
    template = env[: crossfade // hop]
    template = template - template.mean()
    t_norm = np.linalg.norm(template)
    if t_norm < 1e-9:
        return latest, 0.0
    first = (latest - search) // hop
    last = min(latest // hop, len(env) - len(template))
    if last <= first:
        return latest, 0.0
    windows = sliding_window_view(env[first : last + len(template)], len(template))
    centred = windows - windows.mean(axis=1, keepdims=True)
    norms = np.linalg.norm(centred, axis=1) * t_norm
    scores = (centred @ template) / np.maximum(norms, 1e-12)
    best = int(np.argmax(scores))
    if scores[best] < RHYTHM_MATCH:
        # Not rhythmic (noise, rain): any point works, so keep the loop as long as possible.
        return latest, float(scores[-1])
    return (first + best) * hop, float(scores[best])
