"""Application-wide cyber RPG styling."""

APP_STYLE = """
QWidget {
    color: #e8f4ff;
    font-family: "Inter", "Segoe UI Symbol";
    font-size: 13px;
}
QMainWindow, QDialog, QStackedWidget { background-color: #070b14; }
QToolTip {
    color: #e8f4ff;
    background-color: #111c2f;
    border: 1px solid #22d3ee;
    padding: 5px;
}
QFrame#sidebar {
    background-color: #0b1220;
    border-right: 1px solid #1d3852;
}
QFrame#card {
    background-color: rgba(15, 27, 45, 225);
    border: 1px solid #1c3b58;
    border-radius: 12px;
}
QFrame#card:hover {
    background-color: rgba(18, 35, 56, 235);
    border-color: #2d7896;
}
QFrame#heroCard {
    background-color: rgba(5, 12, 24, 205);
    border: 1px solid #237b9b;
    border-radius: 16px;
}
QLabel#pageTitle { font-size: 26px; font-weight: 700; color: #f4fbff; }
QLabel#sectionTitle { font-size: 17px; font-weight: 650; color: #dff8ff; }
QLabel#muted { color: #8296aa; }
QLabel#cyan { color: #45e6ff; }
QLabel#gold { color: #ffc857; }
QLabel#magenta { color: #ff56c7; }
QLabel#statValue { font-size: 25px; font-weight: 750; color: #f6fbff; }
QLabel#statLabel { color: #84a3bb; font-size: 11px; }
QPushButton {
    background-color: #13253a;
    border: 1px solid #245073;
    border-radius: 8px;
    padding: 8px 13px;
    color: #dff8ff;
    font-weight: 600;
}
QPushButton:hover { background-color: #193a54; border-color: #42dff5; }
QPushButton:pressed { background-color: #0f6f87; }
QPushButton:disabled { color: #536578; background-color: #101722; border-color: #202c3a; }
QPushButton[accent="true"] {
    background-color: #087d98;
    border-color: #45e6ff;
    color: white;
}
QPushButton[accent="true"]:hover { background-color: #0a9cbb; }
QPushButton[danger="true"] { color: #ff8fa4; border-color: #713348; }
QPushButton#navButton {
    background: transparent;
    border: 0;
    border-left: 3px solid transparent;
    border-radius: 0;
    text-align: left;
    padding: 11px 16px;
    color: #89a3b9;
}
QPushButton#navButton:hover { color: #e8fbff; background-color: #101e30; }
QPushButton#navButton:checked {
    color: #58e8ff;
    background-color: #10283b;
    border-left-color: #36dff5;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #0d1726;
    border: 1px solid #29445f;
    border-radius: 7px;
    padding: 7px;
    selection-background-color: #167b98;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
    border-color: #3ddff4;
}
QTextBrowser { background: transparent; }
QComboBox::drop-down { border: 0; width: 24px; }
QComboBox QAbstractItemView {
    color: #e8f4ff;
    background-color: #0d1726;
    border: 1px solid #29445f;
    selection-color: #ffffff;
    selection-background-color: #164f6b;
    outline: 0;
}
QComboBox QAbstractItemView::item {
    color: #e8f4ff;
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
    border-radius: 8px;
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
    border-radius: 9px;
    outline: 0;
}
QListWidget::item, QTreeWidget::item { padding: 8px; border-radius: 6px; }
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
    border-radius: 7px;
    text-align: center;
    min-height: 13px;
}
QProgressBar::chunk { background-color: #1ecde7; border-radius: 6px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QCheckBox::indicator:unchecked { background: #0d1726; border: 1px solid #42617b; border-radius: 4px; }
QCheckBox::indicator:checked { background: #16a6c2; border: 1px solid #55ecff; border-radius: 4px; }
QScrollBar:vertical { background: #0a111e; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #29465f; min-height: 28px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QTabWidget::pane { border: 1px solid #1d354d; border-radius: 8px; }
QTabBar::tab { background: #0d1726; color: #839bad; padding: 9px 16px; border: 1px solid #1d354d; }
QTabBar::tab:selected { color: #46e4fa; background: #12273a; }
QSplitter::handle { background: #152b3f; width: 2px; }
"""
