"""Calm dark palette and application stylesheet.

Muted, low-saturation colours with soft (not stark white) text keep contrast
readable while avoiding glare. No animations or bright highlights.
"""

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

COLORS = {
    "bg": "#171b21",
    "surface": "#1f252d",
    "surface_hover": "#262d36",
    "border": "#2c343e",
    "text": "#c7cdd4",
    "text_muted": "#8a949f",
    "accent": "#7aa89f",       # soft sage teal
    "accent_dim": "#4f6f69",
    "accent_text": "#14181d",
    "stop": "#d1a99f",         # muted clay: distinct from the accent, never alarming red
    "stop_bg": "#2a2427",
    "stop_bg_hover": "#352b2e",
}

STYLESHEET = """
QWidget {{
    background-color: {bg};
    color: {text};
}}
QTabWidget::pane {{
    border: none;
    border-top: 1px solid {border};
}}
QTabBar::tab {{
    background: transparent;
    color: {text_muted};
    padding: 10px 28px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12pt;
}}
QTabBar::tab:selected {{
    color: {text};
    border-bottom: 2px solid {accent};
}}
QTabBar::tab:hover:!selected {{
    color: {text};
}}
QScrollArea, QWidget#ScrollContent {{
    background: transparent;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {border};
    border-radius: 4px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: {accent_dim};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    height: 0;
    background: none;
}}
QLabel#SectionHeading {{
    color: {text_muted};
    font-size: 10pt;
    font-weight: 600;
    letter-spacing: 1px;
    padding-top: 4px;
}}
QFrame#SoundCard {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 10px;
}}
QFrame#SoundCard[playing="true"] {{
    border-color: {accent_dim};
}}
QFrame#SoundCard QLabel {{
    background: transparent;
}}
QLabel#SoundName {{
    font-size: 12pt;
    font-weight: 600;
}}
QLabel#Muted, QLabel#SoundStatus, QLabel#VolumeValue {{
    color: {text_muted};
}}
QWidget#VisualsTab, QWidget#VisualsBar {{
    background-color: #000000;  /* the Visuals tab is pitch black */
}}
QWidget#VisualsBar QLabel {{
    background: transparent;
}}
QWidget#VisualsBar QPushButton {{
    background-color: #101317;
    border-color: #20262d;
}}
QWidget#VisualsBar QPushButton:checked {{
    background-color: {accent_dim};
    color: {text};
    border-color: {accent_dim};
}}
QLabel#Placeholder {{
    color: {text_muted};
    font-size: 16pt;
}}
QPushButton {{
    background-color: {surface_hover};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 8px 18px;
    min-width: 90px;
    font-size: 11pt;
}}
QPushButton:hover {{
    border-color: {accent_dim};
}}
QPushButton:focus {{
    border-color: {accent};
}}
QPushButton:checked {{
    background-color: {accent};
    color: {accent_text};
    border-color: {accent};
}}
QPushButton#PlayButton {{
    min-width: 72px;
    padding: 6px 12px;
}}
QPushButton#StopAllButton {{
    background-color: {stop_bg};
    color: {stop};
    border: 1px solid {stop};
    padding: 10px 22px;
    font-size: 12pt;
    font-weight: 600;
}}
QPushButton#StopAllButton:hover {{
    background-color: {stop_bg_hover};
}}
QPushButton#StopAllButton:focus {{
    border-width: 2px;
}}
QPushButton#LinkButton {{
    background: transparent;
    border: none;
    color: {accent};
    min-width: 0;
    padding: 4px 6px;
}}
QPushButton#LinkButton:hover {{
    text-decoration: underline;
}}
QPushButton:disabled {{
    color: {border};
    border-color: {border};
}}
QSlider {{
    min-height: 24px;
    background: transparent;
}}
QSlider::groove:horizontal {{
    height: 6px;
    margin: 9px 0;
    background: {border};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    margin: 9px 0;
    background: {accent_dim};
    border-radius: 3px;
}}
QSlider::add-page:horizontal {{
    margin: 9px 0;
    background: {border};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}}
QSlider::handle:horizontal:disabled {{
    background: {border};
}}
QSlider:focus {{
    outline: none;
}}
""".format(**COLORS)


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")  # consistent rendering across platforms

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["surface"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["surface_hover"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["accent"]))
    palette.setColor(QPalette.HighlightedText, QColor(COLORS["accent_text"]))
    app.setPalette(palette)

    font = QFont(app.font())
    font.setPointSize(11)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)
