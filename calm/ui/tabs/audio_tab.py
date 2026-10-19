"""Tab 1: ambient sound mixer, built from whatever files are in assets/audio."""

from itertools import groupby

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from calm import config
from calm.ui.tabs.base import AppContext, BaseTab
from calm.ui.widgets.flow_grid import FlowGrid
from calm.ui.widgets.sound_card import SoundCard


class AudioTab(BaseTab):
    title = "Audio"

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        audio = context.audio
        self._cards: dict[str, SoundCard] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 16)
        layout.setSpacing(14)

        # --- header: status + Stop All (always visible, never scrolls away) ---
        self._status = QLabel()
        self._status.setObjectName("Muted")
        stop_all = QPushButton("Stop all sound   Esc")
        stop_all.setObjectName("StopAllButton")
        stop_all.setCursor(Qt.PointingHandCursor)
        stop_all.setToolTip("Immediately stop every sound (Esc works on any tab)")
        stop_all.setAccessibleName("Stop all sound")
        stop_all.clicked.connect(audio.stop_all)
        header = QHBoxLayout()
        header.addWidget(self._status, 1)
        header.addWidget(stop_all)
        layout.addLayout(header)

        if audio.error:
            notice = QLabel(audio.error)
            notice.setObjectName("Muted")
            notice.setWordWrap(True)
            layout.addWidget(notice)

        # --- scrollable, grouped grid of sound cards ---
        content = QWidget()
        content.setObjectName("ScrollContent")
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 8, 8)  # right margin keeps cards clear of the scrollbar
        body.setSpacing(10)

        if not audio.sounds:
            message = (
                "No sounds found.\n\nPut .wav, .ogg, .flac or .mp3 files in the sounds folder "
                "(Open sounds folder, below) and restart the app."
            )
            if not config.FROZEN:
                message += "\n\nDeveloping from source? Run  python scripts/download_assets.py  for the starter pack."
            empty = QLabel(message)
            empty.setObjectName("Muted")
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignCenter)
            body.addSpacing(40)
            body.addWidget(empty)

        for category, sounds in groupby(audio.sounds, key=lambda s: s.category):
            heading = QLabel(category)
            heading.setObjectName("SectionHeading")
            body.addWidget(heading)
            grid = FlowGrid()
            for sound in sounds:
                card = SoundCard(sound, config.DEFAULT_VOLUME)
                audio.set_volume(sound.id, config.DEFAULT_VOLUME)
                card.playToggled.connect(self._on_play_toggled)
                card.volumeChanged.connect(audio.set_volume)
                grid.add_widget(card)
                self._cards[sound.id] = card
            body.addWidget(grid)
            body.addSpacing(8)
        body.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        # --- footer: where to add sounds ---
        hint = QLabel(f"{len(audio.sounds)} sounds  ·  add your own audio files to the sounds folder")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        open_folder = QPushButton("Open sounds folder")
        open_folder.setObjectName("LinkButton")
        open_folder.setCursor(Qt.PointingHandCursor)
        open_folder.clicked.connect(self._open_folder)
        footer = QHBoxLayout()
        footer.addWidget(hint, 1)
        footer.addWidget(open_folder)
        layout.addLayout(footer)

        audio.playingChanged.connect(self._on_playing_changed)
        audio.loadFinished.connect(self._on_load_finished)
        audio.playingCountChanged.connect(self._update_status)
        self._update_status(0)

    def _on_play_toggled(self, sound_id: str, playing: bool) -> None:
        audio = self.context.audio
        if playing and not audio.is_loaded(sound_id):
            self._cards[sound_id].set_status("Loading…")
        audio.set_playing(sound_id, playing)

    def _on_playing_changed(self, sound_id: str, playing: bool) -> None:
        if card := self._cards.get(sound_id):
            card.set_playing(playing)

    def _on_load_finished(self, sound_id: str, error: str) -> None:
        card = self._cards.get(sound_id)
        if card is None:
            return
        if error:
            card.set_error(error)
        else:
            card.set_status("")

    def _update_status(self, count: int) -> None:
        if count == 0:
            self._status.setText("Nothing playing")
        else:
            self._status.setText(f"{count} sound{'s' if count != 1 else ''} playing")

    def _open_folder(self) -> None:
        config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.AUDIO_DIR)))
