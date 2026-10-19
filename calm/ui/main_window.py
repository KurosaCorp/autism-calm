"""Main window: a tab bar whose tabs come from the ``TABS`` list."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QTabWidget

from calm import config
from calm.ui.tabs.audio_tab import AudioTab
from calm.ui.tabs.base import AppContext, BaseTab
from calm.ui.tabs.visuals_tab import VisualsTab

# Add new tabs here; each is a BaseTab subclass constructed with the AppContext.
TABS: list[type[BaseTab]] = [AudioTab, VisualsTab]


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self.context = context
        self.setWindowTitle(config.APP_NAME)
        self.resize(920, 720)
        self.setMinimumSize(420, 480)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.tabBar().setDrawBase(False)  # no bright base line under the tabs
        self._pages: list[BaseTab] = []
        for tab_cls in TABS:
            page = tab_cls(context)
            self._pages.append(page)
            self._tabs.addTab(page, page.title)
        self._current = self._pages[0]
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)
        self._current.on_activated()

        # Esc stops all sound from anywhere in the window (sensory overload).
        stop_all = QShortcut(QKeySequence(Qt.Key_Escape), self)
        stop_all.setContext(Qt.WindowShortcut)
        stop_all.activated.connect(context.audio.stop_all)

    def _on_tab_changed(self, index: int) -> None:
        self._current.on_deactivated()
        self._current = self._pages[index]
        self._current.on_activated()

    def closeEvent(self, event) -> None:
        for page in self._pages:
            page.shutdown()
        self.context.audio.shutdown()
        super().closeEvent(event)
