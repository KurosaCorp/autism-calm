"""Audio engine: one output stream that mixes every looping track.

The engine is owned by the application, not by any tab, so sound keeps
playing no matter which tab is visible. It has no UI code; the Qt side talks
to it through ``calm.ui.audio_controller.AudioController``.

Sounds are decoded lazily on a small thread pool the first time they are
played, so startup stays instant and memory is only spent on sounds in use.
"""

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import sounddevice as sd

from calm import config
from calm.audio.library import Sound
from calm.audio.loader import load_loop
from calm.audio.track import LoopTrack

log = logging.getLogger(__name__)

CHANNELS = 2

# Called from a loader thread as (sound_id, error_message_or_None).
LoadedCallback = Callable[[str, str | None], None]


class AudioEngine:
    def __init__(self, on_loaded: LoadedCallback | None = None) -> None:
        self._on_loaded = on_loaded
        self._sounds: dict[str, Sound] = {}
        self._tracks: dict[str, LoopTrack] = {}
        self._loading: set[str] = set()
        self._stream: sd.OutputStream | None = None
        self._pool = ThreadPoolExecutor(config.LOADER_THREADS, thread_name_prefix="audio-load")
        self.samplerate = 48000
        self.error: str | None = None  # human-readable reason if audio is unavailable
        self.underflows = 0  # audio-thread dropouts, for diagnostics

    # --- lifecycle -----------------------------------------------------------
    def start(self) -> None:
        try:
            device = sd.query_devices(kind="output")
            self.samplerate = int(device["default_samplerate"])
            self._stream = sd.OutputStream(
                samplerate=self.samplerate,
                channels=CHANNELS,
                dtype="float32",
                # Ambient audio: a deep buffer rides out busy moments on other threads.
                latency=config.AUDIO_LATENCY_SECONDS,
                callback=self._callback,
            )
            self._stream.start()
        except Exception as exc:  # no device, driver error, etc.
            log.exception("Could not open audio output")
            self.error = f"No audio output available ({exc})."

    def stop(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    # --- sounds --------------------------------------------------------------
    def add_sound(self, sound: Sound) -> None:
        """Register a sound. Its file is decoded the first time it is played."""
        self._sounds[sound.id] = sound
        track = LoopTrack(sound.id, self.samplerate, config.FADE_SECONDS, config.STOP_ALL_FADE_SECONDS)
        # Swap in a new dict so the audio thread never iterates a dict being resized.
        self._tracks = {**self._tracks, sound.id: track}

    def is_loaded(self, sound_id: str) -> bool:
        track = self._tracks.get(sound_id)
        return bool(track and track.loaded)

    def set_playing(self, sound_id: str, playing: bool) -> None:
        track = self._tracks.get(sound_id)
        if track is None:
            return
        if playing:
            track.fast_fade = False
        track.playing = playing
        if playing and not track.loaded:
            self._load(sound_id)

    def is_playing(self, sound_id: str) -> bool:
        track = self._tracks.get(sound_id)
        return bool(track and track.playing)

    def playing_ids(self) -> list[str]:
        return [t.id for t in self._tracks.values() if t.playing]

    def set_volume(self, sound_id: str, volume: float) -> None:
        """``volume`` is 0..1 on a perceptual scale; squared to linear amplitude."""
        if track := self._tracks.get(sound_id):
            v = max(0.0, min(1.0, volume))
            track.volume = v * v

    def stop_all(self) -> None:
        """Silence everything quickly (sensory overload)."""
        for track in self._tracks.values():
            track.fast_fade = True
            track.playing = False

    # --- background loading -------------------------------------------------------
    def _load(self, sound_id: str) -> None:
        if sound_id in self._loading:
            return
        self._loading.add(sound_id)
        self._pool.submit(self._load_worker, sound_id)

    def _load_worker(self, sound_id: str) -> None:
        sound = self._sounds[sound_id]
        error = None
        try:
            buffer = load_loop(sound.path, self.samplerate, CHANNELS)
            self._tracks[sound_id].attach(buffer)
        except Exception as exc:
            log.exception("Could not load %s", sound.path)
            error = f"Could not read this file ({exc})"
            self._tracks[sound_id].playing = False
        finally:
            self._loading.discard(sound_id)
        if self._on_loaded:
            self._on_loaded(sound_id, error)

    # --- audio thread ----------------------------------------------------------
    def _callback(self, outdata: np.ndarray, frames: int, time_info, status) -> None:
        if status.output_underflow:
            self.underflows += 1
        outdata.fill(0.0)
        for track in self._tracks.values():
            track.mix_into(outdata, frames)
        np.clip(outdata, -1.0, 1.0, out=outdata)
