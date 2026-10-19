"""The sprite batch format shared by all renderers.

A visual describes a frame as a float32 array with one row per sprite:

    cx, cy   centre in widget pixels (logical, y down)
    hw, hh   half width / half height in pixels (before rotation)
    angle    rotation in radians
    r, g, b  colour 0..1
    a        intensity 0..1
    shape    SHAPE_BOKEH or SHAPE_RAY

Sprites are combined with "screen" blending (result = src + dst * (1 - src)),
so overlapping lights brighten softly and never clip harshly to white. The
falloff profiles below are mirrored in the GLSL fragment shader in
gl_canvas.py; keep them in sync.
"""

import numpy as np

CX, CY, HW, HH, ANGLE, R, G, B, A, SHAPE = range(10)
COLUMNS = 10
SHAPE_BOKEH = 0.0
SHAPE_RAY = 1.0


def empty(n: int) -> np.ndarray:
    return np.zeros((n, COLUMNS), dtype=np.float32)


def _smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def bokeh_profile(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Out-of-focus light: soft disc plus glow, fully feathered to 0 at the edge."""
    d2 = u * u + v * v
    d = np.sqrt(d2)
    disc = 1.0 - _smoothstep(0.35, 1.0, d)
    glow = np.exp(-d2 * 3.0)
    return (0.55 * disc + 0.45 * glow) * (1.0 - _smoothstep(0.85, 1.0, d))


def ray_profile(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Light ray along u (-1 = origin end, +1 = far end), soft across v."""
    across = np.exp(-v * v * 3.0) * (1.0 - _smoothstep(0.6, 1.0, np.abs(v)))
    along = _smoothstep(-1.0, -0.7, u) * (1.0 - _smoothstep(-0.2, 1.0, u))
    return across * along


# Two triangles per sprite, as (u, v) corner coordinates in -1..1.
_CORNERS = np.array([(-1, -1), (1, -1), (1, 1), (-1, -1), (1, 1), (-1, 1)], dtype=np.float32)
VERTEX_FLOATS = 9  # x, y, u, v, r, g, b, a, shape


def build_vertices(s: np.ndarray) -> np.ndarray:
    """Expand sprites into a triangle list: (N*6, VERTEX_FLOATS) float32."""
    n = len(s)
    u = _CORNERS[None, :, 0]
    v = _CORNERS[None, :, 1]
    lx = u * s[:, None, HW]
    ly = v * s[:, None, HH]
    cos = np.cos(s[:, None, ANGLE])
    sin = np.sin(s[:, None, ANGLE])
    out = np.empty((n, 6, VERTEX_FLOATS), dtype=np.float32)
    out[..., 0] = s[:, None, CX] + lx * cos - ly * sin
    out[..., 1] = s[:, None, CY] + lx * sin + ly * cos
    out[..., 2] = u
    out[..., 3] = v
    out[..., 4:8] = s[:, None, R : A + 1]
    out[..., 8] = s[:, None, SHAPE]
    return out.reshape(-1, VERTEX_FLOATS)
