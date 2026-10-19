"""Base class every tab derives from."""

from dataclasses import dataclass

from PySide6.QtWidgets import QWidget

from calm.ui.audio_controller import AudioController


@dataclass
class AppContext:
    """Shared services handed to every tab.

    Tabs get services from here instead of creating their own, so e.g. a future
    audio-reactive visual can read from the same engine the mixer controls.
    """

    audio: AudioController


class BaseTab(QWidget):
    #: Text shown on the tab.
    title = "Untitled"

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context

    def on_activated(self) -> None:
        """Called when this tab becomes visible (start timers/rendering here)."""

    def on_deactivated(self) -> None:
        """Called when another tab is selected (pause expensive work here)."""

    def shutdown(self) -> None:
        """Called once when the app closes."""
