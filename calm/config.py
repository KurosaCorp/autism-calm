"""Central configuration: paths and audio tuning."""

import os
import sys
from pathlib import Path

APP_NAME = "Autism Calm"
APP_VERSION = "1.0.0"
# Folder name for per-user data (no spaces: friendlier in paths and scripts).
APP_DIR_NAME = "AutismCalm"

# --- Paths -----------------------------------------------------------------------
# True inside a PyInstaller build.
FROZEN = bool(getattr(sys, "frozen", False))
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Read-only files shipped with the app. PyInstaller unpacks them to the
# temporary folder sys._MEIPASS; from source they live in the project.
BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
# Default sound library shipped with the app (copied to AUDIO_DIR on first run).
BUNDLED_AUDIO_DIR = BUNDLE_DIR / "assets" / "audio"
# Window and taskbar icon. Any image Qt can read works (.jpg, .png, .ico, .svg).
LOGO_PATH = BUNDLE_DIR / "assets" / "logo.jpg"


def _default_user_data_dir() -> Path:
    """Per-user, per-machine app data: %LOCALAPPDATA%\\AutismCalm on Windows."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / APP_DIR_NAME


# AUTISMCALM_DATA_DIR overrides the location (used by tests; handy for portable setups).
USER_DATA_DIR = Path(os.environ.get("AUTISMCALM_DATA_DIR") or _default_user_data_dir())
# The user's sound library: what the mixer shows and "Open sounds folder" opens.
AUDIO_DIR = USER_DATA_DIR / "Sounds"
# Third-party add-ons (Python files or packages) loaded at startup.
ADDONS_DIR = USER_DATA_DIR / "Addons"
LOG_DIR = USER_DATA_DIR / "Logs"

# Windows groups taskbar buttons by this ID; without it the taskbar would show
# the Python interpreter's icon instead of the logo.
WINDOWS_APP_ID = "AutismCalm.App"

# --- Sound library -----------------------------------------------------------
# Any file with one of these extensions inside AUDIO_DIR becomes a sound in the
# mixer. Sub-folders become categories (e.g. Sounds/Nature/rain.ogg).
SUPPORTED_EXTENSIONS = (".wav", ".ogg", ".oga", ".flac", ".mp3", ".aif", ".aiff")
# Label for sounds placed directly in AUDIO_DIR rather than in a sub-folder.
UNCATEGORISED_LABEL = "Other"

# --- Audio engine tuning -------------------------------------------------------
# Seconds for a track to fade fully in or out on Play/Pause and volume changes.
# Gentle fades avoid sudden changes, which can be startling.
FADE_SECONDS = 0.8
# Fade used by "Stop all sound": fast enough to feel immediate, slow enough
# to avoid an audible click.
STOP_ALL_FADE_SECONDS = 0.15
# Length of the crossfade that stitches each file's end to its start.
LOOP_CROSSFADE_SECONDS = 2.0
# Longer files are cut to this length to keep memory use and load time low.
MAX_LOOP_SECONDS = 120
# Every track is normalised to this RMS level so sounds are similarly loud at
# the same slider position.
TARGET_RMS = 0.08
# Most a sound's short peaks (crackles, ticks) may be limited to reach
# TARGET_RMS. Higher = more even loudness, lower = more natural transients.
MAX_LIMIT_DB = 12
# Soften sudden loud moments (thunder cracks, door slams) inside recordings.
# Anything louder than PEAK_THRESHOLD x the file's average level is compressed
# at PEAK_RATIO:1. Set SOFTEN_PEAKS = False to hear recordings unaltered.
SOFTEN_PEAKS = True
PEAK_THRESHOLD = 3.0
PEAK_RATIO = 4.0
# Starting slider value (0-100) for every sound.
DEFAULT_VOLUME = 50
# Files decoded in parallel in the background.
LOADER_THREADS = 2
# Output buffer length. Larger = more robust against dropouts while the UI or
# visuals are busy; the cost is that Play/Pause reacts this much later.
AUDIO_LATENCY_SECONDS = 0.15

# --- Visuals ---------------------------------------------------------------------
# "auto" uses the GPU (OpenGL) when available and falls back to a CPU renderer.
# Force one with "opengl" or "raster" (e.g. if a graphics driver misbehaves).
VISUALS_RENDERER = "auto"
# Frame rate of the Visuals tab. Lower it to save power on slow machines.
VISUALS_FPS = 60
