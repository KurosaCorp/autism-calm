"""A single looping sound with smoothed play/pause and volume."""

import numpy as np


class LoopTrack:
    """Holds one loop buffer and mixes it into the output stream.

    ``playing``, ``volume`` and ``fast_fade`` are set from the GUI thread; the
    audio thread only reads them, and Python attribute assignment is atomic,
    so no lock is needed. The gain ramps toward its target inside the audio
    thread, so every change is a gentle fade rather than a jump.

    The buffer arrives later from a loader thread (``attach``). Until then
    the track is silent; if ``playing`` is already set it fades in on arrival.
    """

    def __init__(self, track_id: str, samplerate: int, fade_seconds: float, fast_fade_seconds: float):
        self.id = track_id
        self.playing = False
        self.volume = 0.0  # linear amplitude 0..1
        self.fast_fade = False  # use the short "stop all" fade until silent
        self._buffer: np.ndarray | None = None
        self._pos = 0
        self._gain = 0.0
        self._step = 1.0 / max(1.0, fade_seconds * samplerate)
        self._fast_step = 1.0 / max(1.0, fast_fade_seconds * samplerate)

    @property
    def loaded(self) -> bool:
        return self._buffer is not None

    def attach(self, buffer: np.ndarray) -> None:
        self._pos = 0
        self._buffer = buffer

    @property
    def audible(self) -> bool:
        return self._gain > 0.0

    def mix_into(self, out: np.ndarray, frames: int) -> None:
        buf = self._buffer
        if buf is None:
            return
        target = self.volume if self.playing else 0.0
        start = self._gain
        if start == 0.0 and target == 0.0:
            self.fast_fade = False
            return  # silent: keep position so resume continues seamlessly

        step = self._fast_step if self.fast_fade else self._step
        max_delta = step * frames
        end = start + max(-max_delta, min(max_delta, target - start))
        self._gain = end
        if start == end:
            gain = np.float32(end)  # steady volume: cheap scalar multiply
        else:
            gain = np.linspace(start, end, frames, dtype=np.float32)[:, None]

        n = len(buf)
        pos = self._pos
        written = 0
        while written < frames:
            take = min(frames - written, n - pos)
            g = gain if gain.ndim == 0 else gain[written : written + take]
            out[written : written + take] += buf[pos : pos + take] * g
            written += take
            pos = (pos + take) % n
        self._pos = pos
