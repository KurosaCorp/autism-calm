"""Bokeh tunnel: soft glowing lights drifting out of a central glow.

Lights live in a 3D tunnel and travel towards the viewer. Depth shrinks
exponentially, so on screen every light grows and spreads outward at a
constant relative rate: a steady, hypnotic "infinite zoom" with no
acceleration near the edges. Each light fades in from far away and fades out
before it gets too close, so nothing ever pops in or out. Faint light rays
rotate slowly behind them, and all colours drift through a calm palette.
"""

import logging
import math

import numpy as np
from PySide6.QtWidgets import QVBoxLayout

from calm.visuals.base import BaseVisual
from calm.visuals.render import create_canvas
from calm.visuals.render import sprites as sp
from calm.visuals.render.raster_canvas import RasterSpriteCanvas

log = logging.getLogger(__name__)

# Soft green, calm blue, deep purple, gentle yellow (kept bright enough to glow on black).
PALETTE = np.array(
    [
        (0.47, 0.84, 0.64),
        (0.39, 0.64, 0.93),
        (0.53, 0.39, 0.87),
        (0.93, 0.85, 0.52),
    ],
    dtype=np.float32,
)


def palette(t: np.ndarray) -> np.ndarray:
    """Cyclic, smoothly interpolated palette lookup; ``t`` in cycles."""
    t = np.mod(t, 1.0) * len(PALETTE)
    i = np.floor(t).astype(np.int64)
    f = t - i
    f = (f * f * (3.0 - 2.0 * f))[:, None]
    a = PALETTE[i % len(PALETTE)]
    b = PALETTE[(i + 1) % len(PALETTE)]
    return a + (b - a) * f


def smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class TunnelSimulation:
    Z_FAR = 12.0          # where lights appear (tiny, at the centre)
    Z_NEAR = 0.3          # where they are recycled (after fading out)
    ZOOM_RATE = 0.11      # 1/s: depth shrinks by e^-rate per second (~30 s per light)
    SWIRL = 0.05          # rad/s: gentle rotation of the tunnel
    RAY_SWIRL = 0.012     # rad/s
    COLOR_CYCLE = 90.0    # seconds for the palette to come full circle
    GLOW_BREATH = 14.0    # seconds per breath of the central glow

    def __init__(self, lights: int = 150, rays: int = 9, seed: int | None = None) -> None:
        self.rng = np.random.default_rng(seed)
        self.time = 0.0
        n = lights
        self.theta = np.zeros(n)
        self.radius = np.zeros(n)
        self.size = np.zeros(n)
        self.bright = np.zeros(n)
        self.hue = np.zeros(n)
        self.spin = np.zeros(n)
        self._respawn(np.arange(n))
        # Spread lights along the tunnel so the scene starts already full.
        self.z = self.Z_FAR * (self.Z_NEAR / self.Z_FAR) ** self.rng.uniform(0, 1, n)

        self.ray_angle = np.linspace(0, 2 * np.pi, rays, endpoint=False) + self.rng.uniform(-0.2, 0.2, rays)
        self.ray_phase = self.rng.uniform(0, 2 * np.pi, rays)
        self.ray_period = self.rng.uniform(25, 45, rays)
        self.ray_width = self.rng.uniform(0.07, 0.13, rays)  # wide and soft: beams, not lines

    def _respawn(self, idx: np.ndarray) -> None:
        k = len(idx)
        self.theta[idx] = self.rng.uniform(0, 2 * np.pi, k)
        self.radius[idx] = self.rng.uniform(0.12, 1.5, k)
        self.size[idx] = self.rng.uniform(0.05, 0.16, k)
        self.bright[idx] = self.rng.uniform(0.3, 0.7, k)
        self.hue[idx] = self.rng.uniform(0.0, 0.35, k)
        self.spin[idx] = self.rng.uniform(0.6, 1.4, k)

    def step(self, dt: float) -> None:
        if dt <= 0:
            return
        self.time += dt
        self.z *= math.exp(-self.ZOOM_RATE * dt)
        self.theta += self.SWIRL * self.spin * dt
        self.ray_angle += self.RAY_SWIRL * dt
        done = np.nonzero(self.z < self.Z_NEAR)[0]
        if len(done):
            # Recycle at the far end (invisible there) with a fresh look.
            self.z[done] *= self.Z_FAR / self.Z_NEAR
            self._respawn(done)

    def sprites(self, width: int, height: int) -> np.ndarray:
        cx, cy = width / 2, height / 2
        focal = 0.5 * min(width, height)
        t = self.time
        hue_t = t / self.COLOR_CYCLE

        # --- bokeh lights ---
        scale = focal / self.z
        x = cx + self.radius * np.cos(self.theta) * scale
        y = cy + self.radius * np.sin(self.theta) * scale
        r = self.size * scale
        alpha = (
            self.bright
            * smoothstep(self.Z_FAR, self.Z_FAR * 0.5, self.z)      # fade in from the distance
            * smoothstep(self.Z_NEAR, self.Z_NEAR * 3.0, self.z)    # fade out before getting close
        )
        visible = (alpha > 0.004) & (x + r > 0) & (x - r < width) & (y + r > 0) & (y - r < height)
        idx = np.nonzero(visible)[0]

        rays = len(self.ray_angle)
        out = sp.empty(len(idx) + rays + 1)
        lights = out[: len(idx)]
        lights[:, sp.CX] = x[idx]
        lights[:, sp.CY] = y[idx]
        lights[:, sp.HW] = r[idx]
        lights[:, sp.HH] = r[idx]
        lights[:, sp.R : sp.B + 1] = palette(hue_t + self.hue[idx])
        lights[:, sp.A] = alpha[idx]
        lights[:, sp.SHAPE] = sp.SHAPE_BOKEH

        # --- slow, faint light rays from the centre ---
        ray_rows = out[len(idx) : len(idx) + rays]
        half_diag = 0.5 * math.hypot(width, height)
        length = half_diag * (0.85 + 0.1 * np.sin(2 * np.pi * t / self.ray_period + self.ray_phase))
        ray_rows[:, sp.CX] = cx + np.cos(self.ray_angle) * length / 2
        ray_rows[:, sp.CY] = cy + np.sin(self.ray_angle) * length / 2
        ray_rows[:, sp.HW] = length / 2
        ray_rows[:, sp.HH] = focal * self.ray_width
        ray_rows[:, sp.ANGLE] = self.ray_angle
        ray_rows[:, sp.R : sp.B + 1] = palette(hue_t + np.arange(rays) / rays * 0.5)
        ray_rows[:, sp.A] = 0.07 * (0.5 + 0.5 * np.sin(2 * np.pi * t / self.ray_period + self.ray_phase))
        ray_rows[:, sp.SHAPE] = sp.SHAPE_RAY

        # --- the emitter: a large, dim glow breathing at the centre ---
        glow = out[-1]
        glow[sp.CX], glow[sp.CY] = cx, cy
        glow[sp.HW] = glow[sp.HH] = 0.42 * focal
        glow[sp.R : sp.B + 1] = palette(np.array([hue_t + 0.1]))[0]
        glow[sp.A] = 0.2 + 0.06 * math.sin(2 * math.pi * t / self.GLOW_BREATH)
        glow[sp.SHAPE] = sp.SHAPE_BOKEH
        return out


class BokehTunnel(BaseVisual):
    name = "Bokeh tunnel"

    def __init__(self, context, parent=None) -> None:
        super().__init__(context, parent)
        self.simulation = TunnelSimulation()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = create_canvas(self.simulation.sprites)
        if hasattr(self.canvas, "failed"):
            self.canvas.failed.connect(self._use_cpu_renderer)
        self._layout.addWidget(self.canvas)

    def tick(self, dt: float) -> None:
        self.simulation.step(dt)
        self.canvas.update()

    def _use_cpu_renderer(self, reason: str) -> None:
        log.warning("Switching the Visuals tab to the CPU renderer (%s)", reason)
        old = self.canvas
        self.canvas = RasterSpriteCanvas(self.simulation.sprites)
        self._layout.replaceWidget(old, self.canvas)
        old.deleteLater()
