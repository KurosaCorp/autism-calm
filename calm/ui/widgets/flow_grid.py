"""A grid that picks its column count from the available width."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QGridLayout, QSizePolicy, QWidget


class FlowGrid(QWidget):
    def __init__(self, min_column_width: int = 250, spacing: int = 10, parent=None) -> None:
        super().__init__(parent)
        self._min_width = min_column_width
        self._items: list[QWidget] = []
        self._columns = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(spacing)
        self._grid.setAlignment(Qt.AlignTop)
        # Never taller than the cards need; leftover space goes to the parent's stretch.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

    def minimumSizeHint(self) -> QSize:
        # Report one column's width so the parent can shrink us; resizeEvent
        # then drops to fewer columns instead of clipping cards.
        return QSize(self._min_width, super().minimumSizeHint().height())

    def add_widget(self, widget: QWidget) -> None:
        self._items.append(widget)
        self._relayout(force=True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self, force: bool = False) -> None:
        spacing = self._grid.horizontalSpacing()
        columns = max(1, (self.width() + spacing) // (self._min_width + spacing))
        if columns == self._columns and not force:
            return
        for widget in self._items:
            self._grid.removeWidget(widget)
        for i, widget in enumerate(self._items):
            self._grid.addWidget(widget, i // columns, i % columns)
        for c in range(max(columns, self._columns)):
            self._grid.setColumnStretch(c, 1 if c < columns else 0)
        self._columns = columns
        self.updateGeometry()  # row count changed: tell the parent our new height
