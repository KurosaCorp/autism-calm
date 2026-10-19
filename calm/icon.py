"""Application icon (window title bar and taskbar)."""

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap

from calm import config

log = logging.getLogger(__name__)

ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)


def register_windows_app_id() -> None:
    """Give the process its own taskbar identity so Windows shows our icon, not Python's.

    Must run before the first window is created.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(config.WINDOWS_APP_ID)
    except Exception as exc:  # very old Windows or restricted environment: keep the default
        log.warning("Could not set the Windows app ID: %s", exc)


def load_app_icon(path: Path = config.LOGO_PATH) -> QIcon | None:
    """Build a multi-size icon from ``path``, or return None if it is missing or unreadable."""
    if not path.is_file():
        log.info("No logo found at %s; using the default icon", path)
        return None
    image = QPixmap(str(path))
    if image.isNull():
        log.warning("Could not read the logo %s; using the default icon", path)
        return None

    # Icons are square: centre the logo on a transparent square instead of squashing it.
    side = max(image.width(), image.height())
    square = QPixmap(side, side)
    square.fill(Qt.transparent)
    painter = QPainter(square)
    painter.drawPixmap(QPoint((side - image.width()) // 2, (side - image.height()) // 2), image)
    painter.end()

    # Pre-scaled sizes stay crisp in the title bar and taskbar.
    icon = QIcon()
    for size in ICON_SIZES:
        icon.addPixmap(square.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    return icon
