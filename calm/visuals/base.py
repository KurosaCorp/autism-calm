"""Base class for graphics modules shown in the Visuals tab.

To add a visual, write a ``BaseVisual`` subclass that implements ``tick(dt)``
to advance the animation and repaint (``self.update()`` and a
``paintEvent``). For heavy drawing, put a canvas from ``calm.visuals.render``
(GPU sprite renderer with a QPainter fallback) inside the visual; see
``bokeh_tunnel.py``. Then either:

* built in: add the class to ``VISUALS`` in ``calm/visuals/__init__.py``, or
* as an add-on: put the module in the user's Add-ons folder (see
  ``calm/addons.py``); no change to the app's code is needed.

The base class owns the frame timer and the user's speed / pause settings.
Every change is eased: speed changes glide, pausing slows the motion to a
stop, and the visual starts gently each time the tab is shown. When fully
paused or hidden, the timer stops, so the visual costs nothing.

Visuals should not control audio; ``self.context.audio`` (the
AudioController) is available if a visual wants to react to what is playing,
e.g. via its playingChanged signal.
"""

import math
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QWidget

from calm import config


class BaseVisual(QWidget):
    #: Name shown to the user when choosing a visual.
    name = "Untitled visual"
    #: Time constant for speed changes, pausing and resuming (≈3x this to settle).
    ease_seconds = 0.8
    #: Below this fraction of normal speed, a pausing visual is treated as still.
    rest_threshold = 0.01

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.PreciseTimer)  # even frame spacing = smoother motion
        self._timer.setInterval(max(1, round(1000 / config.VISUALS_FPS)))
        self._timer.timeout.connect(self._on_timer)
        self._last = 0.0
        self._active = False
        self.speed = 1.0     # user's speed multiplier
        self.paused = False
        self.elapsed = 0.0   # animation time so far (sum of the dt passed to tick)
        self._scale = 0.0    # eased playback rate actually applied

    # --- called by the Visuals tab ---------------------------------------------
    def start(self) -> None:
        """The visual became visible."""
        self._active = True
        self._scale = 0.0  # ease in from stillness rather than appearing mid-motion
        self._resume_timer()

    def stop(self) -> None:
        """The visual was hidden."""
        self._active = False
        self._timer.stop()

    def set_speed(self, multiplier: float) -> None:
        self.speed = max(0.0, multiplier)

    def set_paused(self, paused: bool) -> None:
        self.paused = paused
        if not paused:
            self._resume_timer()

    # --- for subclasses -----------------------------------------------------------
    def tick(self, dt: float) -> None:
        """Advance animation state by ``dt`` (already speed-scaled) seconds and repaint."""

    # --- internals ------------------------------------------------------------------
    def _resume_timer(self) -> None:
        if self._active and not self._timer.isActive():
            self._last = time.perf_counter()
            self._timer.start()

    def _on_timer(self) -> None:
        now = time.perf_counter()
        real_dt = min(now - self._last, 0.1)  # after a stall, continue rather than jump
        self._last = now
        target = 0.0 if self.paused else self.speed
        self._scale += (target - self._scale) * (1.0 - math.exp(-real_dt / self.ease_seconds))
        if self.paused and self._scale < self.rest_threshold:
            self._scale = 0.0
            self._timer.stop()  # fully still: no more frames until resumed
        dt = real_dt * self._scale
        self.elapsed += dt
        self.tick(dt)
