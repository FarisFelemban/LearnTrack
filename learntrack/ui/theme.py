"""Application-wide cyber RPG styling."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


TITLE_BAR_COLOR = "#0b1220"

COLORS = {
    "background": "#060c17", "panel": "#0c1a2d", "panel_top": "#10253c",
    "border": "#244865", "accent": "#58baff", "text": "#ecf6ff",
    "muted": "#9aafc5", "gold": "#ffd080", "danger": "#ff8195",
}
DISPLAY_FONT = "Rajdhani"


def paint_system_panel(painter, bounds, *, fill=True, emphasis=False):
    """Paint a clipped frame and four luminous brackets without blur effects."""
    painter.save()
    rect = QRectF(bounds).adjusted(2, 2, -2, -2)
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
    cut = 8
    path = QPainterPath()
    path.moveTo(left + cut, top)
    for x, y in ((right, top), (right, bottom - cut), (right - cut, bottom),
                 (left, bottom), (left, top + cut)):
        path.lineTo(x, y)
    path.closeSubpath()
    if fill:
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor(COLORS["panel_top"]))
        gradient.setColorAt(1, QColor(COLORS["panel"]))
        painter.fillPath(path, gradient)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(COLORS["accent"] if emphasis else COLORS["border"]), 1))
    painter.drawPath(path)
    brackets = QPainterPath()
    brackets.moveTo(left, top + 20)
    brackets.lineTo(left, top + cut)
    brackets.lineTo(left + cut, top)
    brackets.lineTo(left + 26, top)
    brackets.moveTo(right - 20, top)
    brackets.lineTo(right, top)
    brackets.lineTo(right, top + 20)
    brackets.moveTo(left, bottom - 20)
    brackets.lineTo(left, bottom)
    brackets.lineTo(left + 20, bottom)
    brackets.moveTo(right - 26, bottom)
    brackets.lineTo(right - cut, bottom)
    brackets.lineTo(right, bottom - cut)
    brackets.lineTo(right, bottom - 20)
    glow = QColor(COLORS["accent"])
    glow.setAlpha(28)
    painter.setPen(QPen(glow, 5))
    painter.drawPath(brackets)
    painter.setPen(QPen(QColor(COLORS["accent"]), 1))
    painter.drawPath(brackets)
    painter.restore()


def _windows_color_ref(hex_color: str) -> int:
    """Convert #RRGGBB into the COLORREF format expected by Windows."""

    red, green, blue = bytes.fromhex(hex_color.removeprefix("#"))
    return red | (green << 8) | (blue << 16)


def _style_windows_title_bar(widget: QWidget) -> None:
    """Match a native Windows title bar to LearnTrack's sidebar."""

    if sys.platform != "win32":
        return

    try:
        window_handle = ctypes.c_void_p(int(widget.winId()))
        dwm = ctypes.windll.dwmapi

        enabled = ctypes.c_int(1)
        caption_color = ctypes.c_int(_windows_color_ref(TITLE_BAR_COLOR))
        text_color = ctypes.c_int(_windows_color_ref("#e8f4ff"))
        border_color = ctypes.c_int(_windows_color_ref("#1d3852"))

        # Windows 10 20H1 and later use attribute 20 for dark caption controls.
        dwm.DwmSetWindowAttribute(window_handle, 20, ctypes.byref(enabled), ctypes.sizeof(enabled))
        dwm.DwmSetWindowAttribute(window_handle, 35, ctypes.byref(caption_color), ctypes.sizeof(caption_color))
        dwm.DwmSetWindowAttribute(window_handle, 36, ctypes.byref(text_color), ctypes.sizeof(text_color))
        dwm.DwmSetWindowAttribute(window_handle, 34, ctypes.byref(border_color), ctypes.sizeof(border_color))
    except (AttributeError, OSError):
        # Older Windows versions may not expose DWM caption-color controls.
        return


def flash_windows_taskbar(widget: QWidget, count: int = 5) -> bool:
    """Flash a window's Windows taskbar button a finite number of times."""

    if sys.platform != "win32":
        return False

    class FlashWindowInfo(ctypes.Structure):
        _fields_ = (
            ("cbSize", wintypes.UINT),
            ("hwnd", wintypes.HWND),
            ("dwFlags", wintypes.DWORD),
            ("uCount", wintypes.UINT),
            ("dwTimeout", wintypes.DWORD),
        )

    try:
        flash_window_ex = ctypes.windll.user32.FlashWindowEx
        flash_window_ex.argtypes = (ctypes.POINTER(FlashWindowInfo),)
        flash_window_ex.restype = wintypes.BOOL
        flash_info = FlashWindowInfo(
            ctypes.sizeof(FlashWindowInfo),
            wintypes.HWND(int(widget.winId())),
            0x00000002,  # FLASHW_TRAY: flash only the taskbar button.
            max(1, int(count)),
            0,
        )
        return bool(flash_window_ex(ctypes.byref(flash_info)))
    except (AttributeError, OSError, TypeError, ValueError):
        return False


class WindowsTitleBarStyler(QObject):
    """Apply the native title-bar colors whenever a top-level window opens."""

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        if event.type() == QEvent.Type.Show and isinstance(watched, QWidget) and watched.isWindow():
            _style_windows_title_bar(watched)
        return super().eventFilter(watched, event)

APP_STYLE = """
QWidget {
    color: @text;
    font-family: "Inter", "Segoe UI Symbol";
    font-size: 13px;
}
QMainWindow, QDialog, QStackedWidget, QWidget#pageContent { background-color: @background; }
QToolTip {
    color: @text;
    background-color: #111c2f;
    border: 1px solid @accent;
    padding: 5px;
}
QFrame#sidebar {
    background-color: #0b1220;
    border-right: 1px solid @border;
}
QFrame#card, QFrame#heroCard { background: transparent; border: none; }
QLabel#pageTitle { font-family: "Rajdhani"; font-size: 30px; font-weight: 600; color: @text; }
QLabel#sectionTitle { font-family: "Rajdhani"; font-size: 18px; font-weight: 600; color: #dff8ff; }
QLabel#muted { color: @muted; }
QLabel#cyan { color: @accent; }
QLabel#gold { color: @gold; }
QLabel#magenta { color: @accent; }
QLabel#statValue { font-family: "Rajdhani"; font-size: 34px; font-weight: 700; color: @text; }
QLabel#statLabel { font-family: "Rajdhani"; font-weight: 600; color: @muted; font-size: 15px; }
QPushButton {
    background-color: #13253a;
    border: 1px solid #245073;
    border-radius: 2px;
    padding: 8px 13px;
    color: #dff8ff;
    font-weight: 600;
}
QPushButton:hover { background-color: #193a54; border-color: @accent; }
QPushButton:pressed { background-color: #123956; }
QPushButton:disabled { color: #536578; background-color: #101722; border-color: #202c3a; }
QPushButton[accent="true"] {
    background-color: #164971;
    border-color: @accent;
    color: white;
}
QPushButton[accent="true"]:hover { background-color: #22649a; }
QPushButton[danger="true"] { color: @danger; border-color: #713348; }
QPushButton#navButton {
    font-family: "Rajdhani"; font-size: 18px;
    background: transparent;
    border: 0;
    border-left: 3px solid transparent;
    border-radius: 0;
    text-align: left;
    padding: 11px 16px;
    color: @muted;
}
QPushButton#navButton:hover { color: #e8fbff; background-color: #101e30; }
QPushButton#navButton:checked {
    color: @accent;
    background-color: #10283b;
    border-left-color: @accent;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #0d1726;
    border: 1px solid #29445f;
    border-radius: 2px;
    padding: 7px;
    selection-background-color: #167b98;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: @accent;
}
QTextBrowser { background: transparent; }
QComboBox::drop-down { border: 0; width: 24px; }
QComboBox QAbstractItemView {
    color: @text;
    background-color: #0d1726;
    border: 1px solid #29445f;
    selection-color: #ffffff;
    selection-background-color: #164f6b;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    color: @text;
    background-color: #0d1726;
    min-height: 28px;
    padding: 4px 8px;
}
QComboBox QAbstractItemView::item:selected {
    color: #ffffff;
    background-color: #164f6b;
}
QLineEdit#timerEditor {
    color: #f1fbff;
    background-color: #07111f;
    border: 1px solid #3ee6fa;
    border-radius: 2px;
    padding: 3px;
    font-size: 24px;
    font-weight: 600;
    selection-background-color: #167b98;
}
QLineEdit#timerEditor[invalid="true"] { border-color: #ff637e; }
QListWidget, QTreeWidget, QTableWidget {
    background-color: #0a111e;
    alternate-background-color: #0d1725;
    border: 1px solid #1d354d;
    border-radius: 2px;
    outline: 0;
}
QListWidget::item, QTreeWidget::item { padding: 8px; border-radius: 2px; }
QListWidget::item:hover, QTreeWidget::item:hover { background-color: #13263b; }
QListWidget::item:selected, QTreeWidget::item:selected { background-color: #16405a; color: #ecfdff; }
QHeaderView::section {
    background-color: #111f31;
    color: #89a9bf;
    padding: 7px;
    border: 0;
    border-bottom: 1px solid #29445f;
}
QProgressBar {
    background-color: #101b2b;
    border: 1px solid #24435e;
    border-radius: 2px;
    text-align: center;
    min-height: 22px;
}
QProgressBar::chunk { background-color: #205d91; border-radius: 2px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked { background: #0d1726; border: 1px solid #42617b; border-radius: 2px; }
QCheckBox::indicator:checked { background: #16a6c2; border: 1px solid #55ecff; border-radius: 2px; }
QScrollBar:vertical { background: #0a111e; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #29465f; min-height: 28px; border-radius: 2px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTabWidget::pane { border: 1px solid #1d354d; border-radius: 2px; }
QTabBar::tab { background: #0d1726; color: #839bad; padding: 9px 16px; border: 1px solid #1d354d; }
QTabBar::tab:selected { color: @accent; background: #12273a; }
QSplitter::handle { background: #152b3f; width: 2px; }

QLabel#systemHeading { font-family: "Rajdhani"; font-size: 18px; font-weight: 600; color: @accent; }
QLabel#pathValue { font-family: "Rajdhani"; font-size: 23px; font-weight: 600; color: @text; }
QPushButton:focus, QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QComboBox:focus, QListWidget:focus, QTreeWidget:focus, QTableWidget:focus {
    border: 1px solid @accent;
}
QPushButton#navButton:focus { border: 1px solid @accent; border-left: 3px solid @accent; }
QCheckBox:focus { color: @accent; }
QTabBar::tab:focus { border-bottom: 2px solid @accent; }
QTableWidget { gridline-color: #183049; selection-background-color: #19476e; selection-color: @text; }
QTableWidget::item { padding: 5px; }
QWidget#tableActions QPushButton { padding: 5px 8px; }
QMenu { background: @panel; border: 1px solid @border; padding: 4px; }
QMenu::item { padding: 7px 20px; }
QMenu::item:selected { background: #19476e; }
QScrollArea { background: transparent; border: none; }
QScrollBar:horizontal { background: @background; height: 10px; }
QScrollBar::handle:horizontal { background: @border; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QWidget#miniTimerWindow { background: @background; }
QLabel#miniTimerValue { font-family: "Rajdhani"; color: @text; font-size: 30px; font-weight: 700; }
QPushButton#miniTimerToggle {
    background: #164971; border: 1px solid @accent; border-radius: 2px;
    min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; padding: 0;
}
QPushButton#miniTimerToggle:hover { background: #22649a; }
QPushButton#miniTimerHide { padding: 7px 10px; }
QPushButton:disabled, QPushButton[accent="true"]:disabled, QPushButton[danger="true"]:disabled {
    color: #8095ac; background-color: #101722; border-color: #26364a;
}
"""

# Share the same palette between Qt stylesheets and custom-painted widgets.
for _name, _color in COLORS.items():
    APP_STYLE = APP_STYLE.replace("@" + _name, _color)
