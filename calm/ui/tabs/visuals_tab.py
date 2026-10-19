"""Tab 2: host for graphics modules registered in ``calm.visuals.VISUALS``."""

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QSlider, QStackedWidget, QVBoxLayout, QWidget

from calm.ui.tabs.base import AppContext, BaseTab
from calm.visuals import VISUALS, BaseVisual

# Speed slider (0-100) maps exponentially onto these multipliers, so the slow
# end has fine control. 1.0x is the visual's natural pace.
MIN_SPEED = 0.05
MAX_SPEED = 2.0
DEFAULT_SPEED = 1.0


def slider_to_speed(value: int) -> float:
    return MIN_SPEED * (MAX_SPEED / MIN_SPEED) ** (value / 100)


def speed_to_slider(speed: float) -> int:
    return round(100 * math.log(speed / MIN_SPEED) / math.log(MAX_SPEED / MIN_SPEED))


class VisualsTab(BaseTab):
    title = "Visuals"

    def __init__(self, context: AppContext, parent=None) -> None:
        super().__init__(context, parent)
        self.setObjectName("VisualsTab")
        self.setAttribute(Qt.WA_StyledBackground)
        # Created now (before the window is shown) so an OpenGL canvas never
        # forces the window to be recreated later, which could flash.
        self._visuals: list[BaseVisual] = [cls(context) for cls in VISUALS]
        self._active: BaseVisual | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not self._visuals:
            placeholder = QLabel("Coming soon")
            placeholder.setObjectName("Placeholder")
            placeholder.setAlignment(Qt.AlignCenter)
            layout.addWidget(placeholder)
            return

        self._stack = QStackedWidget()
        for visual in self._visuals:
            self._stack.addWidget(visual)
        layout.addWidget(self._stack, 1)

        # --- controls ---
        bar = QWidget()
        bar.setObjectName("VisualsBar")
        bar.setAttribute(Qt.WA_StyledBackground)
        controls = QHBoxLayout(bar)
        controls.setContentsMargins(20, 10, 20, 12)
        controls.setSpacing(12)

        if len(self._visuals) > 1:
            picker = QComboBox()
            picker.addItems([v.name for v in self._visuals])
            picker.currentIndexChanged.connect(self._select)
            controls.addWidget(picker)

        speed_label = QLabel("Speed")
        speed_label.setObjectName("Muted")
        self._speed = QSlider(Qt.Horizontal)
        self._speed.setRange(0, 100)
        self._speed.setPageStep(10)
        self._speed.setValue(speed_to_slider(DEFAULT_SPEED))
        self._speed.setAccessibleName("Animation speed")
        self._speed.setMaximumWidth(360)
        self._speed.valueChanged.connect(self._on_speed)
        self._speed_value = QLabel()
        self._speed_value.setObjectName("Muted")
        self._speed_value.setMinimumWidth(48)

        self._pause = QPushButton("Pause")
        self._pause.setObjectName("PauseVisualsButton")
        self._pause.setCheckable(True)
        self._pause.setCursor(Qt.PointingHandCursor)
        self._pause.setToolTip("Gently stop the animation (sound keeps playing)")
        self._pause.toggled.connect(self._on_pause)

        controls.addWidget(speed_label)
        controls.addWidget(self._speed, 1)
        controls.addWidget(self._speed_value)
        controls.addStretch(0)
        controls.addWidget(self._pause)
        layout.addWidget(bar)

        self._on_speed(self._speed.value())

    # --- controls -----------------------------------------------------------------
    def _on_speed(self, value: int) -> None:
        speed = slider_to_speed(value)
        self._speed_value.setText(f"{speed:.2f}×")
        for visual in self._visuals:
            visual.set_speed(speed)

    def _on_pause(self, paused: bool) -> None:
        self._pause.setText("Resume" if paused else "Pause")
        for visual in self._visuals:
            visual.set_paused(paused)

    # --- lifecycle -----------------------------------------------------------------
    def _select(self, index: int) -> None:
        was_running = self._active is not None
        if self._active:
            self._active.stop()
            self._active = None
        self._stack.setCurrentIndex(index)
        if was_running:
            self.on_activated()

    def on_activated(self) -> None:
        if self._visuals and self._active is None:
            self._active = self._visuals[self._stack.currentIndex()]
            self._active.start()

    def on_deactivated(self) -> None:
        if self._active:
            self._active.stop()
            self._active = None

    def shutdown(self) -> None:
        self.on_deactivated()
