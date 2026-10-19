"""GPU sprite renderer built on Qt's own OpenGL classes (no extra dependency).

Per frame the CPU only expands a few hundred sprites into a vertex array with
numpy and issues one draw call, so the GUI thread stays almost idle and the
audio thread is never starved. The soft falloff of every light is computed
on the GPU in the fragment shader.
"""

import logging
import time
from collections.abc import Callable

import numpy as np
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QColor, QPalette, QVector2D
from PySide6.QtOpenGL import QOpenGLBuffer, QOpenGLShader, QOpenGLShaderProgram, QOpenGLVertexArrayObject
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from calm.visuals.render.sprites import VERTEX_FLOATS, build_vertices

log = logging.getLogger(__name__)

GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_BLEND = 0x0BE2
GL_ONE = 1
GL_ONE_MINUS_SRC_COLOR = 0x0301
GL_COLOR_BUFFER_BIT = 0x4000

# GLSL 1.10 (no #version line) for the widest driver support.
VERTEX_SHADER = """
attribute vec2 a_pos;
attribute vec2 a_uv;
attribute vec4 a_color;
attribute float a_shape;
uniform vec2 u_viewport;
varying vec2 v_uv;
varying vec4 v_color;
varying float v_shape;
void main() {
    vec2 ndc = a_pos / u_viewport * 2.0 - 1.0;
    gl_Position = vec4(ndc.x, -ndc.y, 0.0, 1.0);
    v_uv = a_uv;
    v_color = a_color;
    v_shape = a_shape;
}
"""

# Mirrors bokeh_profile / ray_profile in sprites.py.
FRAGMENT_SHADER = """
varying vec2 v_uv;
varying vec4 v_color;
varying float v_shape;
void main() {
    float k;
    if (v_shape < 0.5) {
        float d2 = dot(v_uv, v_uv);
        float d = sqrt(d2);
        float disc = 1.0 - smoothstep(0.35, 1.0, d);
        float glow = exp(-d2 * 3.0);
        k = (0.55 * disc + 0.45 * glow) * (1.0 - smoothstep(0.85, 1.0, d));
    } else {
        float across = exp(-v_uv.y * v_uv.y * 3.0) * (1.0 - smoothstep(0.6, 1.0, abs(v_uv.y)));
        float along = smoothstep(-1.0, -0.7, v_uv.x) * (1.0 - smoothstep(-0.2, 1.0, v_uv.x));
        k = across * along;
    }
    gl_FragColor = vec4(v_color.rgb * (v_color.a * k), 1.0);
}
"""

ATTRIBUTES = (("a_pos", 0, 2), ("a_uv", 2, 2), ("a_color", 4, 4), ("a_shape", 8, 1))  # name, float offset, size


class GLSpriteCanvas(QOpenGLWidget):
    #: Emitted (queued) if OpenGL could not be set up; the owner should fall back.
    failed = Signal(str)

    def __init__(self, source: Callable[[int, int], np.ndarray], parent=None) -> None:
        super().__init__(parent)
        self._source = source
        self._program: QOpenGLShaderProgram | None = None
        self._vbo: QOpenGLBuffer | None = None
        self._vao: QOpenGLVertexArrayObject | None = None
        self._ok = False
        self.last_paint_ms = 0.0  # CPU time of the last frame, for diagnostics
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

    def initializeGL(self) -> None:
        try:
            program = QOpenGLShaderProgram(self)
            if not program.addShaderFromSourceCode(QOpenGLShader.Vertex, VERTEX_SHADER):
                raise RuntimeError(program.log())
            if not program.addShaderFromSourceCode(QOpenGLShader.Fragment, FRAGMENT_SHADER):
                raise RuntimeError(program.log())
            for location, (name, _, _) in enumerate(ATTRIBUTES):
                program.bindAttributeLocation(name, location)
            if not program.link():
                raise RuntimeError(program.log())
            vbo = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            if not vbo.create():
                raise RuntimeError("could not create a vertex buffer")
            vbo.setUsagePattern(QOpenGLBuffer.DynamicDraw)
            vao = QOpenGLVertexArrayObject(self)
            self._vao = vao if vao.create() else None  # required on core profiles only
            self._program, self._vbo, self._ok = program, vbo, True
        except Exception as exc:
            log.warning("OpenGL renderer unavailable, falling back: %s", exc)
            QTimer.singleShot(0, lambda: self.failed.emit(str(exc)))

    def paintGL(self) -> None:
        started = time.perf_counter()
        f = self.context().functions()
        f.glClearColor(0.0, 0.0, 0.0, 1.0)
        f.glClear(GL_COLOR_BUFFER_BIT)
        if not self._ok:
            return
        sprites = self._source(self.width(), self.height())
        if len(sprites) == 0:
            return
        vertices = build_vertices(sprites)

        program, vbo = self._program, self._vbo
        if self._vao:
            self._vao.bind()
        program.bind()
        program.setUniformValue("u_viewport", QVector2D(self.width(), self.height()))
        vbo.bind()
        vbo.allocate(vertices.tobytes(), vertices.nbytes)
        stride = VERTEX_FLOATS * 4
        for location, (_, offset, size) in enumerate(ATTRIBUTES):
            program.enableAttributeArray(location)
            program.setAttributeBuffer(location, GL_FLOAT, offset * 4, size, stride)
        f.glEnable(GL_BLEND)
        f.glBlendFunc(GL_ONE, GL_ONE_MINUS_SRC_COLOR)  # screen blend
        f.glDrawArrays(GL_TRIANGLES, 0, len(vertices))
        for location in range(len(ATTRIBUTES)):
            program.disableAttributeArray(location)
        vbo.release()
        program.release()
        if self._vao:
            self._vao.release()
        self.last_paint_ms = (time.perf_counter() - started) * 1000
