"""CPU fallback sprite renderer (QPainter) for machines without usable OpenGL.

Soft, blurry lights don't need full resolution, so the frame is drawn into a
small image and smoothly scaled up. That keeps the CPU cost per frame low
enough to leave the audio thread plenty of room.
"""

import time
from collections.abc import Callable

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QWidget

from calm.visuals.render import sprites as sp

RESOLUTION_SCALE = 0.35  # fraction of the widget size actually rendered
_COLOR_STEPS = 24        # colour quantisation for the tinted sprite cache
_CACHE_LIMIT = 256


def _mask(shape: float) -> np.ndarray:
    if shape == sp.SHAPE_RAY:
        u, v = np.meshgrid(np.linspace(-1, 1, 128), np.linspace(-1, 1, 32))
        return sp.ray_profile(u, v)
    u, v = np.meshgrid(np.linspace(-1, 1, 64), np.linspace(-1, 1, 64))
    return sp.bokeh_profile(u, v)


class RasterSpriteCanvas(QWidget):
    def __init__(self, source: Callable[[int, int], np.ndarray], parent=None) -> None:
        super().__init__(parent)
        self._source = source
        self._masks = {sp.SHAPE_BOKEH: _mask(sp.SHAPE_BOKEH), sp.SHAPE_RAY: _mask(sp.SHAPE_RAY)}
        self._cache: dict[tuple, QImage] = {}
        self._frame: QImage | None = None
        self.last_paint_ms = 0.0
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def _sprite_image(self, shape: float, r: float, g: float, b: float) -> QImage:
        key = (shape, round(r * _COLOR_STEPS), round(g * _COLOR_STEPS), round(b * _COLOR_STEPS))
        image = self._cache.get(key)
        if image is None:
            if len(self._cache) >= _CACHE_LIMIT:
                self._cache.clear()
            mask = self._masks[shape]
            rgb = np.array(key[1:], dtype=np.float32) / _COLOR_STEPS
            # Premultiplied BGRA bytes; alpha = mask so "screen" blending behaves like the GPU path.
            px = np.empty(mask.shape + (4,), dtype=np.uint8)
            px[..., 0] = np.clip(mask * rgb[2] * 255, 0, 255)
            px[..., 1] = np.clip(mask * rgb[1] * 255, 0, 255)
            px[..., 2] = np.clip(mask * rgb[0] * 255, 0, 255)
            px[..., 3] = np.clip(mask * 255, 0, 255)
            h, w = mask.shape
            image = QImage(px.tobytes(), w, h, 4 * w, QImage.Format_ARGB32_Premultiplied).copy()
            self._cache[key] = image
        return image

    def paintEvent(self, event) -> None:
        started = time.perf_counter()
        w, h = self.width(), self.height()
        fw, fh = max(1, int(w * RESOLUTION_SCALE)), max(1, int(h * RESOLUTION_SCALE))
        if self._frame is None or self._frame.width() != fw or self._frame.height() != fh:
            self._frame = QImage(fw, fh, QImage.Format_ARGB32_Premultiplied)
        self._frame.fill(QColor(0, 0, 0))

        p = QPainter(self._frame)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.setCompositionMode(QPainter.CompositionMode_Screen)
        p.scale(fw / max(1, w), fh / max(1, h))
        for s in self._source(w, h):
            if s[sp.A] <= 0.004:
                continue
            image = self._sprite_image(float(s[sp.SHAPE]), s[sp.R], s[sp.G], s[sp.B])
            p.save()
            p.translate(float(s[sp.CX]), float(s[sp.CY]))
            p.rotate(float(np.degrees(s[sp.ANGLE])))
            p.setOpacity(float(min(1.0, s[sp.A])))
            hw, hh = float(s[sp.HW]), float(s[sp.HH])
            p.drawImage(QRectF(-hw, -hh, 2 * hw, 2 * hh), image)
            p.restore()
        p.end()

        out = QPainter(self)
        out.setRenderHint(QPainter.SmoothPixmapTransform)
        out.drawImage(self.rect(), self._frame)
        out.end()
        self.last_paint_ms = (time.perf_counter() - started) * 1000
