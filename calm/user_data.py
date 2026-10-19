"""Per-user data folder: first-run sound library setup and log files."""

import logging
import os
import shutil
import sys
import tempfile
from logging.handlers import RotatingFileHandler
from pathlib import Path

from calm import config

log = logging.getLogger(__name__)

# Build/download leftovers that must not be copied to the user.
_SKIP = shutil.ignore_patterns(".standins", "*.part")


def has_files(folder: Path) -> bool:
    """True if ``folder`` contains at least one file (at any depth)."""
    return folder.is_dir() and any(p.is_file() for p in folder.rglob("*"))


def ensure_sound_library(target: Path = config.AUDIO_DIR, source: Path = config.BUNDLED_AUDIO_DIR) -> bool:
    """Copy the bundled default sounds into ``target`` if it is missing or empty.

    A folder that already has files is never touched, so the user's own sounds,
    deletions and re-arrangements are kept. Files are copied into a temporary
    sibling folder first and renamed into place at the end, so an interrupted
    first run can't leave a half-filled library behind.

    Returns True if the defaults were copied.
    """
    if has_files(target):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    if not has_files(source):
        log.warning("No bundled sounds found at %s; starting with an empty library", source)
        target.mkdir(exist_ok=True)
        return False

    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    try:
        shutil.copytree(source, staging, ignore=_SKIP, dirs_exist_ok=True)
        if target.exists():
            shutil.rmtree(target)  # contains no files (checked above), only empty folders
        staging.rename(target)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    log.info("Copied the default sound library to %s", target)
    return True


def setup_logging() -> Path | None:
    """Log to the console when there is one, and always to a rotating file.

    A windowed (--noconsole) build has no console, so the log file is the only
    place errors show up. Returns the log file path, or None if it can't be written.
    """
    # Windowed builds have no stdout/stderr; give stray prints somewhere harmless to go.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")

    handlers: list[logging.Handler] = []
    if not config.FROZEN:
        handlers.append(logging.StreamHandler())
    log_file = config.LOG_DIR / "autism-calm.log"
    try:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        handlers.append(RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=2, encoding="utf-8"))
    except OSError:
        log_file = None
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers or [logging.NullHandler()],
    )

    def log_uncaught(exc_type, exc, tb):
        logging.getLogger("calm").critical("Uncaught error", exc_info=(exc_type, exc, tb))

    sys.excepthook = log_uncaught
    return log_file
