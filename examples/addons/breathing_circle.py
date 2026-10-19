"""Example Autism Calm add-on: a slow breathing guide.

A soft glowing circle grows for 4 seconds (breathe in) and shrinks for
6 seconds (breathe out). Install it by copying this file into the Add-ons
folder (Visuals tab -> "Open add-ons folder") and restarting the app.

How an add-on works:
- Subclass BaseVisual. The app handles the frame timer, the Speed slider and
  the Pause button for you: tick(dt) receives speed-scaled seconds, and
  self.elapsed holds the total animation time.
- Draw in paintEvent with QPainter (fine for a few shapes), or use
  calm.visuals.render.create_canvas() for hundreds of soft lights on the GPU.
- List your visuals in VISUALS (optional: without it, every BaseVisual
  subclass in the file is used).
Keep visuals calm: dark background, soft edges, no flashing or sudden moves.
"""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QRadialGradient

from calm.visuals.base import BaseVisual

INHALE = 4.0  # seconds
EXHALE = 6.0
CYCLE = INHALE + EXHALE
TEXT_FADE = 0.8  # seconds the words take to fade at each change

BLUE = (0.42, 0.64, 0.90)
GREEN = (0.47, 0.82, 0.65)


def ease(x: float) -> float:
    """0..1 -> 0..1 with gentle start and end."""
    return 0.5 - 0.5 * math.cos(math.pi * min(max(x, 0.0), 1.0))


class BreathingCircle(BaseVisual):
    name = "Breathing circle"

    def __init__(self, context, parent=None) -> None:
        super().__init__(context, parent)
        self.setAttribute(Qt.WA_OpaquePaintEvent)  # we paint every pixel ourselves

    def tick(self, dt: float) -> None:
        self.update()  # repaint; the time is in self.elapsed

    def paintEvent(self, event) -> None:
        t = self.elapsed % CYCLE
        inhaling = t < INHALE
        fullness = ease(t / INHALE) if inhaling else 1.0 - ease((t - INHALE) / EXHALE)

        w, h = self.width(), self.height()
        base = min(w, h)
        radius = base * (0.16 + 0.18 * fullness)
        mix = 0.5 + 0.5 * math.sin(self.elapsed * 2 * math.pi / 60)  # blue <-> green every minute
        r, g, b = (BLUE[i] + (GREEN[i] - BLUE[i]) * mix for i in range(3))

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(0, 0, 0))

        # Feathered glow: bright soft core fading to fully transparent at the edge.
        centre = QPointF(w / 2, h / 2 - base * 0.04)
        glow = QRadialGradient(centre, radius * 1.6)
        brightness = 0.55 + 0.25 * fullness
        for stop, alpha in ((0.0, 0.85), (0.45, 0.55), (0.7, 0.18), (1.0, 0.0)):
            glow.setColorAt(stop, QColor.fromRgbF(r * brightness, g * brightness, b * brightness, alpha))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(centre, radius * 1.6, radius * 1.6)

        # Words fade in and out around each change, never switching abruptly.
        since_change = t if inhaling else t - INHALE
        until_change = (INHALE - t) if inhaling else (CYCLE - t)
        text_alpha = 0.55 * min(1.0, since_change / TEXT_FADE, until_change / TEXT_FADE)
        font = QFont(self.font())
        font.setPointSizeF(max(12.0, base / 32))
        p.setFont(font)
        p.setPen(QColor.fromRgbF(0.78, 0.81, 0.84, text_alpha))
        text_box = QRectF(0, h / 2 + base * 0.40, w, base * 0.1)
        p.drawText(text_box, Qt.AlignCenter, "Breathe in" if inhaling else "Breathe out")
        p.end()


VISUALS = [BreathingCircle]
