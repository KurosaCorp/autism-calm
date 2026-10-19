"""Discover sound files in the audio folder.

No code changes are needed to add sounds: drop a file into ``assets/audio``
(or a sub-folder, which becomes its category) and restart the app.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import soundfile as sf

from calm import config

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Sound:
    id: str        # path relative to the audio folder, e.g. "Nature/heavy_rain.mp3"
    path: Path
    name: str      # display name, e.g. "Heavy rain"
    category: str  # sub-folder name, or UNCATEGORISED_LABEL


def display_name(stem: str) -> str:
    """``heavy_rain`` / ``heavy-rain`` / ``heavy rain`` -> ``Heavy rain``."""
    words = re.sub(r"[_\-]+", " ", stem).strip()
    words = re.sub(r"\s+", " ", words)
    return words[:1].upper() + words[1:] if words else stem


def scan_library(directory: Path = config.AUDIO_DIR) -> list[Sound]:
    """Return every readable audio file under ``directory``, sorted for display."""
    if not directory.is_dir():
        return []
    sounds = []
    for path in directory.rglob("*"):
        rel = path.relative_to(directory)
        if (
            not path.is_file()
            or path.suffix.lower() not in config.SUPPORTED_EXTENSIONS
            or any(part.startswith(".") for part in rel.parts)
        ):
            continue
        try:
            sf.info(str(path))  # cheap header check; skips corrupt/unsupported files
        except Exception as exc:
            log.warning("Skipping %s: %s", rel, exc)
            continue
        category = rel.parts[0] if len(rel.parts) > 1 else config.UNCATEGORISED_LABEL
        sounds.append(Sound(rel.as_posix(), path, display_name(path.stem), category))

    def sort_key(s: Sound):
        return (s.category == config.UNCATEGORISED_LABEL, s.category.lower(), s.name.lower())

    return sorted(sounds, key=sort_key)
