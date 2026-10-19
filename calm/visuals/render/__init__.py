"""Sprite canvases: draw a batch of soft lights described by a numpy array.

``create_canvas(source)`` returns the GPU canvas when OpenGL works and the
CPU fallback otherwise. ``source(width, height)`` is called on every repaint
and returns the sprite array (see ``sprites.py``).
"""

import logging
from collections.abc import Callable

import numpy as np
from PySide6.QtGui import QGuiApplication, QOpenGLContext
from PySide6.QtWidgets import QWidget

from calm import config
from calm.visuals.render.raster_canvas import RasterSpriteCanvas

log = logging.getLogger(__name__)

SpriteSource = Callable[[int, int], np.ndarray]


def opengl_available() -> bool:
    if QGuiApplication.platformName() in ("offscreen", "minimal"):
        return False
    context = QOpenGLContext()
    return context.create()


def create_canvas(source: SpriteSource, parent: QWidget | None = None) -> QWidget:
    mode = config.VISUALS_RENDERER
    if mode == "opengl" or (mode == "auto" and opengl_available()):
        from calm.visuals.render.gl_canvas import GLSpriteCanvas

        return GLSpriteCanvas(source, parent)
    log.info("Visuals: using the CPU renderer")
    return RasterSpriteCanvas(source, parent)


__all__ = ["RasterSpriteCanvas", "SpriteSource", "create_canvas", "opengl_available"]
