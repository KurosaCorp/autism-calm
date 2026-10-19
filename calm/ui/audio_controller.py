"""Qt-facing wrapper around the audio engine.

Every part of the UI (mixer cards, the Stop All button, the Esc shortcut,
future visuals) goes through this one object, and it broadcasts changes as
signals, so all views stay in sync no matter where a change came from.
"""

from PySide6.QtCore import QObject, Signal

from calm.audio import AudioEngine, Sound, scan_library


class AudioController(QObject):
    playingChanged = Signal(str, bool)  # sound id, playing
    loadFinished = Signal(str, str)     # sound id, error message ("" on success)
    playingCountChanged = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        # The engine calls on_loaded from a loader thread; emitting a signal is
        # thread-safe and Qt queues delivery onto the GUI thread.
        self.engine = AudioEngine(on_loaded=lambda sid, err: self.loadFinished.emit(sid, err or ""))
        self.loadFinished.connect(self._on_load_finished)
        self.sounds: list[Sound] = []

    @property
    def error(self) -> str | None:
        return self.engine.error

    def start(self) -> None:
        self.engine.start()
        self.sounds = scan_library()
        for sound in self.sounds:
            self.engine.add_sound(sound)

    def shutdown(self) -> None:
        self.engine.stop()

    def set_playing(self, sound_id: str, playing: bool) -> None:
        if self.engine.is_playing(sound_id) == playing:
            return
        self.engine.set_playing(sound_id, playing)
        self.playingChanged.emit(sound_id, playing)
        self.playingCountChanged.emit(self.playing_count())

    def set_volume(self, sound_id: str, volume_percent: int) -> None:
        self.engine.set_volume(sound_id, volume_percent / 100)

    def stop_all(self) -> None:
        was_playing = self.engine.playing_ids()
        self.engine.stop_all()
        for sound_id in was_playing:
            self.playingChanged.emit(sound_id, False)
        self.playingCountChanged.emit(0)

    def is_playing(self, sound_id: str) -> bool:
        return self.engine.is_playing(sound_id)

    def is_loaded(self, sound_id: str) -> bool:
        return self.engine.is_loaded(sound_id)

    def playing_count(self) -> int:
        return len(self.engine.playing_ids())

    def _on_load_finished(self, sound_id: str, error: str) -> None:
        if error:  # the engine already stopped it; tell the views
            self.playingChanged.emit(sound_id, False)
            self.playingCountChanged.emit(self.playing_count())
