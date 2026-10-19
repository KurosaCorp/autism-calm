"""Application bootstrap."""

import json
import logging
import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from calm import config
from calm.addons import load_addons
from calm.icon import load_app_icon, register_windows_app_id
from calm.theme import apply_theme
from calm.ui.audio_controller import AudioController
from calm.ui.main_window import MainWindow
from calm.ui.tabs.base import AppContext
from calm.user_data import ensure_sound_library, setup_logging

log = logging.getLogger(__name__)


def run() -> int:
    log_file = setup_logging()
    log.info(
        "%s %s starting (frozen=%s, bundle=%s, data=%s, log=%s)",
        config.APP_NAME, config.APP_VERSION, config.FROZEN, config.BUNDLE_DIR, config.USER_DATA_DIR, log_file,
    )
    # The audio callback runs on its own thread but needs Python's GIL. A short
    # switch interval (default 5 ms) lets it get the GIL back quickly while the
    # UI, visuals or file loaders are busy.
    sys.setswitchinterval(0.001)

    try:
        ensure_sound_library()  # first run: copy the default sounds to the user's folder
    except Exception:
        log.exception("Could not set up the sound library in %s", config.AUDIO_DIR)

    register_windows_app_id()  # before any window exists
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    if icon := load_app_icon():
        app.setWindowIcon(icon)  # used by every window and the taskbar
    apply_theme(app)

    audio = AudioController()
    audio.start()
    addons = load_addons()  # before the window: visuals are created with it

    window = MainWindow(AppContext(audio=audio, addons=addons))
    window.show()
    if report := os.environ.get("AUTISMCALM_SMOKE_TEST"):
        _schedule_smoke_test(window, audio, report)
    try:
        return app.exec()
    finally:
        audio.shutdown()


def _schedule_smoke_test(window: MainWindow, audio: AudioController, report_path: str) -> None:
    """Automated check for packaged builds: play every sound, show the visuals,
    write a JSON report to ``report_path`` and quit. Enabled by setting the
    AUTISMCALM_SMOKE_TEST environment variable to the report path."""
    audio_tab, visuals_tab = window._pages[0], window._pages[1]
    visuals = visuals_tab._visuals

    def play_and_switch() -> None:
        for sound in audio.sounds:
            audio.set_playing(sound.id, True)
            audio.engine.set_volume(sound.id, 0.005)  # ~-90 dB: mixes for real, inaudibly
        window._tabs.setCurrentIndex(1)
        show_visual(0)

    def show_visual(i: int) -> None:
        """Show each visual (built-in first, then add-ons) in turn via the picker."""
        if i >= len(visuals):
            finish()
            return
        if i > 0:
            visuals_tab.picker.setCurrentIndex(i)
        QTimer.singleShot(5000 if i == 0 else 3000, lambda: show_visual(i + 1))

    def finish() -> None:
        visual = visuals[0] if visuals else None
        result = {
            "frozen": config.FROZEN,
            "bundle_dir": str(config.BUNDLE_DIR),
            "audio_dir": str(config.AUDIO_DIR),
            "audio_error": audio.error,
            "sounds_found": len(audio.sounds),
            "sounds_loaded": sum(audio.is_loaded(s.id) for s in audio.sounds),
            "audio_underflows": audio.engine.underflows,
            "renderer": type(visual.canvas).__name__ if visual else None,
            "visual_time": round(visual.simulation.time, 2) if visual else None,
            "icon_loaded": not QApplication.windowIcon().isNull(),
            "mixer_cards": len(audio_tab._cards),
            "addons_dir": str(config.ADDONS_DIR),
            "addons": [
                {"name": a.name, "visuals": [v.name for v in a.visuals], "error": a.error}
                for a in window.context.addons
            ],
            "visuals_shown": [{"name": v.name, "animated_seconds": round(v.elapsed, 2)} for v in visuals],
            "visuals_tab_problems": visuals_tab._problems,
        }
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        audio.stop_all()
        window.close()

    QTimer.singleShot(1500, play_and_switch)
