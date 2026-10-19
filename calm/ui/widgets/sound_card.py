"""Compact mixer card: name, Play/Pause toggle and a volume slider."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout

from calm.audio import Sound


class SoundCard(QFrame):
    playToggled = Signal(str, bool)   # sound id, playing
    volumeChanged = Signal(str, int)  # sound id, 0..100

    def __init__(self, sound: Sound, volume: int, parent=None) -> None:
        super().__init__(parent)
        self.sound = sound
        self.setObjectName("SoundCard")
        self.setProperty("playing", False)

        name = QLabel(sound.name)
        name.setObjectName("SoundName")
        name.setToolTip(sound.id)

        self._status = QLabel()
        self._status.setObjectName("SoundStatus")
        self._status.setWordWrap(True)
        self._status.hide()

        self.play_button = QPushButton("Play")
        self.play_button.setObjectName("PlayButton")
        self.play_button.setCheckable(True)
        self.play_button.setCursor(Qt.PointingHandCursor)
        self.play_button.setAccessibleName(f"Play or pause {sound.name}")
        self.play_button.toggled.connect(self._on_toggled)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 100)
        self.slider.setSingleStep(2)
        self.slider.setPageStep(10)
        self.slider.setValue(volume)
        self.slider.setAccessibleName(f"{sound.name} volume")
        self.slider.valueChanged.connect(self._on_volume)

        self._value = QLabel(f"{volume}%")
        self._value.setObjectName("VolumeValue")
        self._value.setMinimumWidth(40)
        self._value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(name)
        text.addWidget(self._status)

        top = QHBoxLayout()
        top.addLayout(text, 1)
        top.addWidget(self.play_button, 0, Qt.AlignTop)

        bottom = QHBoxLayout()
        bottom.addWidget(self.slider, 1)
        bottom.addWidget(self._value)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 6)
        layout.setSpacing(4)
        layout.addLayout(top)
        layout.addLayout(bottom)

    def set_playing(self, playing: bool) -> None:
        """Reflect state from elsewhere (e.g. Stop All) without re-emitting."""
        self.play_button.blockSignals(True)
        self.play_button.setChecked(playing)
        self.play_button.blockSignals(False)
        self._show_playing(playing)

    def set_status(self, text: str) -> None:
        self._status.setText(text)
        self._status.setVisible(bool(text))

    def set_error(self, message: str) -> None:
        self.set_playing(False)
        self.set_status(message)
        self.play_button.setEnabled(False)
        self.slider.setEnabled(False)

    def _show_playing(self, playing: bool) -> None:
        self.play_button.setText("Pause" if playing else "Play")
        self.setProperty("playing", playing)
        self.style().unpolish(self)  # re-apply the [playing="true"] stylesheet rule
        self.style().polish(self)

    def _on_toggled(self, checked: bool) -> None:
        self._show_playing(checked)
        self.playToggled.emit(self.sound.id, checked)

    def _on_volume(self, value: int) -> None:
        self._value.setText(f"{value}%")
        self.volumeChanged.emit(self.sound.id, value)
