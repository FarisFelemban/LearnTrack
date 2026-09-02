"""Reusable visual widgets and lightweight animations."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QEvent, QEasingCurve, QPointF, QPropertyAnimation, QRect, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..constants import BACKDROP_PATH
from ..engine import next_level_progress
from .dialogs import TimerPresetsDialog


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, hero: bool = False):
        super().__init__(parent)
        self.setObjectName("heroCard" if hero else "card")


class StatCard(Card):
    def __init__(self, label: str, value: str = "0", color_name: str = "cyan"):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 13, 16, 13)
        self.value_label = QLabel(value)
        self.value_label.setObjectName("statValue")
        if color_name in ("cyan", "gold", "magenta"):
            self.value_label.setStyleSheet(
                {"cyan": "color:#45e6ff", "gold": "color:#ffc857", "magenta": "color:#ff56c7"}[color_name]
            )
        caption = QLabel(label.upper())
        caption.setObjectName("statLabel")
        layout.addWidget(self.value_label)
        layout.addWidget(caption)
        self._number_animation = QVariantAnimation(self)
        self._number_animation.setDuration(450)
        self._number_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._number_animation.valueChanged.connect(self._show_animated_number)
        self._number_target: int | None = None
        self._number_suffix = ""

    def set_value(self, value: object) -> None:
        self._number_animation.stop()
        self._number_target = None
        self.value_label.setText(str(value))

    def set_number(self, value: int, suffix: str = "", animate: bool = True) -> None:
        value = int(value)
        if self._number_target == value and self._number_suffix == suffix:
            return
        try:
            current = int(self.value_label.text().replace(",", "").removesuffix(self._number_suffix))
        except ValueError:
            current = 0
        self._number_target = value
        self._number_suffix = suffix
        self._number_animation.stop()
        if not animate:
            self._show_animated_number(value)
            return
        self._number_animation.setStartValue(current)
        self._number_animation.setEndValue(value)
        self._number_animation.start()

    def _show_animated_number(self, value: object) -> None:
        self.value_label.setText(f"{int(value):,}{self._number_suffix}")


class AnimatedXPBar(QProgressBar):
    def __init__(self):
        super().__init__()
        self._animation = QPropertyAnimation(self, b"value", self)
        self._animation.setDuration(550)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def show_xp(self, xp: int, animate: bool = True) -> None:
        within, span, next_level = next_level_progress(xp)
        maximum = span or max(1, within)
        self.setRange(0, maximum)
        self.setFormat(
            f"{xp:,} XP • MAX DEFINED LEVEL" if next_level is None else f"{within:,} / {span:,} XP to Level {next_level}"
        )
        if animate:
            self._animation.stop()
            self._animation.setStartValue(self.value())
            self._animation.setEndValue(within)
            self._animation.start()
        else:
            self.setValue(within)


class BackdropPanel(QWidget):
    """Paint the bundled art with a dark readability veil."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.pixmap = QPixmap(str(BACKDROP_PATH))
        self.artwork_visible = True

    def set_artwork_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if self.artwork_visible != visible:
            self.artwork_visible = visible
            self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt API
        super().paintEvent(event)
        painter = QPainter(self)
        if self.artwork_visible and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation
            )
            x = (scaled.width() - self.width()) // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
            painter.fillRect(self.rect(), QColor(3, 8, 17, 130))
        else:
            painter.fillRect(self.rect(), QColor("#070b14"))


class CircularTimer(QWidget):
    edit_requested = Signal()
    outside_clicked = Signal()
    value_submitted = Signal(str)

    def __init__(self):
        super().__init__()
        self.setMinimumSize(170, 170)
        self.setAccessibleName("Timer countdown")
        self.setAccessibleDescription("Click the time to edit it in minutes and seconds")
        self.duration = 1
        self.remaining = 0
        self.mode = "focus"
        self.editor = QLineEdit(self)
        self.editor.setObjectName("timerEditor")
        self.editor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.editor.setMaxLength(8)
        self.editor.setToolTip("Enter minutes:seconds, for example 45:00")
        self.editor.installEventFilter(self)
        self.editor.returnPressed.connect(self._submit_edit)
        self.editor.editingFinished.connect(self._submit_edit)
        self.editor.hide()

    def set_time(self, remaining: int, duration: int, mode: str) -> None:
        self.remaining = max(0, remaining)
        self.duration = max(1, duration)
        self.mode = mode
        self.update()

    def _text_rect(self) -> QRect:
        return QRect((self.width() - 124) // 2, (self.height() - 52) // 2, 124, 52)

    def resizeEvent(self, event):  # noqa: N802 - Qt API
        self.editor.setGeometry(self._text_rect())
        super().resizeEvent(event)

    def mouseReleaseEvent(self, event):  # noqa: N802 - Qt API
        if event.button() == Qt.MouseButton.LeftButton and self._text_rect().contains(event.position().toPoint()):
            self.edit_requested.emit()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):  # noqa: N802 - Qt API
        cursor = (
            Qt.CursorShape.PointingHandCursor
            if self._text_rect().contains(event.position().toPoint())
            else Qt.CursorShape.ArrowCursor
        )
        self.setCursor(cursor)
        super().mouseMoveEvent(event)

    def enter_edit_mode(self) -> None:
        minutes, seconds = divmod(self.remaining, 60)
        self.editor.setProperty("invalid", False)
        self.editor.style().unpolish(self.editor)
        self.editor.style().polish(self.editor)
        self.editor.setToolTip("Enter minutes:seconds, for example 45:00")
        self.editor.setText(f"{minutes:02d}:{seconds:02d}")
        self.editor.show()
        self.editor.setFocus()
        self.editor.selectAll()
        QApplication.instance().installEventFilter(self)
        self.update()

    def leave_edit_mode(self) -> None:
        application = QApplication.instance()
        if application is not None:
            application.removeEventFilter(self)
        self.editor.hide()
        self.update()

    def show_edit_error(self) -> None:
        self.editor.setProperty("invalid", True)
        self.editor.style().unpolish(self.editor)
        self.editor.style().polish(self.editor)
        self.editor.setToolTip("Use minutes:seconds (for example 45:00). Seconds must be 00–59.")
        self.editor.setFocus()
        self.editor.selectAll()

    def _submit_edit(self) -> None:
        if not self.editor.isHidden():
            self.value_submitted.emit(self.editor.text())

    def eventFilter(self, watched, event):  # noqa: N802 - Qt API
        if watched is self.editor and event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.leave_edit_mode()
            return True
        if not self.editor.isHidden() and event.type() == QEvent.Type.MouseButtonPress:
            clicked_inside_editor = watched is self.editor or (
                isinstance(watched, QWidget) and self.editor.isAncestorOf(watched)
            )
            if not clicked_inside_editor:
                self.outside_clicked.emit()
        return super().eventFilter(watched, event)

    def paintEvent(self, event):  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 18
        rect = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        painter.setPen(QPen(QColor("#1c3047"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(rect, 0, 360 * 16)
        color = QColor("#ff56c7" if self.mode == "break" else "#3ee6fa")
        painter.setPen(QPen(color, 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        span = int(360 * 16 * self.remaining / self.duration)
        painter.drawArc(rect, 90 * 16, -span)
        minutes, seconds = divmod(self.remaining, 60)
        painter.setPen(QColor("#f1fbff"))
        font = QFont(self.font())
        font.setPointSize(24)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        if not self.editor.isVisible():
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{minutes:02d}:{seconds:02d}")


class TimerPanel(Card):
    timer_saved = Signal()

    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.clock = QTimer(self)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self._tick)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        title_row = QHBoxLayout()
        title = QLabel("TIMER")
        title.setObjectName("sectionTitle")
        self.presets_button = QPushButton("Presets…")
        self.presets_button.clicked.connect(self.edit_presets)
        title_row.addWidget(title)
        title_row.addWidget(self.presets_button)
        layout.addLayout(title_row)
        self.dial = CircularTimer()
        self.dial.setMouseTracking(True)
        self.dial.edit_requested.connect(self.begin_duration_edit)
        self.dial.outside_clicked.connect(self.finish_duration_edit)
        self.dial.value_submitted.connect(self.apply_edited_duration)
        layout.addWidget(self.dial, alignment=Qt.AlignmentFlag.AlignHCenter)
        duration_row = QHBoxLayout()
        self.focus_buttons = []
        for index in range(3):
            button = QPushButton()
            button.clicked.connect(lambda checked=False, preset_index=index: self.choose_focus_preset(preset_index))
            duration_row.addWidget(button)
            self.focus_buttons.append(button)
        self.break_button = QPushButton()
        self.break_button.clicked.connect(self.choose_break_preset)
        duration_row.addWidget(self.break_button)
        layout.addLayout(duration_row)
        control_row = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.setProperty("accent", True)
        self.start_button.clicked.connect(self.toggle)
        reset_button = QPushButton("Reset")
        reset_button.clicked.connect(self.reset)
        control_row.addWidget(self.start_button)
        control_row.addWidget(reset_button)
        layout.addLayout(control_row)
        self.refresh_preset_buttons()
        self.refresh()

    def refresh_preset_buttons(self) -> None:
        focus_minutes, break_minutes = self.engine.timer_presets
        for button, minutes in zip(self.focus_buttons, focus_minutes):
            button.setText(f"{minutes}m")
        self.break_button.setText(f"{break_minutes}m break")

    def choose_focus_preset(self, index: int) -> None:
        focus_minutes, _ = self.engine.timer_presets
        self.choose("focus", focus_minutes[index])

    def choose_break_preset(self) -> None:
        _, break_minutes = self.engine.timer_presets
        self.choose("break", break_minutes)

    def edit_presets(self) -> None:
        focus_minutes, break_minutes = self.engine.timer_presets
        dialog = TimerPresetsDialog(focus_minutes, break_minutes, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        focus_minutes, break_minutes = dialog.data()
        self.engine.set_timer_presets(focus_minutes, break_minutes)
        self.refresh_preset_buttons()
        self.timer_saved.emit()

    def refresh(self) -> None:
        timer = self.engine.progress["timer"]
        self.dial.set_time(timer["remaining_seconds"], timer["duration_seconds"], timer["mode"])
        self.start_button.setText("Pause" if timer["running"] else "Start")
        if timer["running"] and not self.clock.isActive():
            self.clock.start()
        elif not timer["running"]:
            self.clock.stop()

    def choose(self, mode: str, minutes: int) -> None:
        self.clock.stop()
        self.engine.set_timer(mode, minutes)
        self.refresh()
        self.timer_saved.emit()

    def begin_duration_edit(self) -> None:
        timer = self.engine.progress["timer"]
        self.clock.stop()
        self.engine.update_timer(timer["remaining_seconds"], False)
        self.timer_saved.emit()
        self.dial.enter_edit_mode()

    def finish_duration_edit(self) -> None:
        self.apply_edited_duration(self.dial.editor.text(), discard_invalid=True)

    def apply_edited_duration(self, text: str, discard_invalid: bool = False) -> None:
        parts = text.strip().split(":")
        try:
            if len(parts) == 1:
                total_seconds = int(parts[0]) * 60
            elif len(parts) == 2:
                minutes, seconds = (int(part) for part in parts)
                if not 0 <= seconds < 60:
                    raise ValueError
                total_seconds = minutes * 60 + seconds
            else:
                raise ValueError
        except ValueError:
            if discard_invalid:
                self.dial.leave_edit_mode()
                self.refresh()
                return
            self.dial.show_edit_error()
            return
        if not 1 <= total_seconds <= 24 * 60 * 60:
            if discard_invalid:
                self.dial.leave_edit_mode()
                self.refresh()
                return
            self.dial.show_edit_error()
            return
        mode = self.engine.progress["timer"]["mode"]
        self.engine.set_timer_seconds(mode, total_seconds)
        self.dial.leave_edit_mode()
        self.refresh()
        self.timer_saved.emit()

    def toggle(self) -> None:
        timer = self.engine.progress["timer"]
        if timer["remaining_seconds"] == 0:
            timer["remaining_seconds"] = timer["duration_seconds"]
        self.engine.update_timer(timer["remaining_seconds"], not timer["running"])
        self.refresh()
        self.timer_saved.emit()

    def reset(self) -> None:
        timer = self.engine.progress["timer"]
        self.clock.stop()
        self.engine.update_timer(timer["duration_seconds"], False)
        self.refresh()
        self.timer_saved.emit()

    def _tick(self) -> None:
        timer = self.engine.progress["timer"]
        remaining = max(0, timer["remaining_seconds"] - 1)
        # Save on each tick so closing at any moment preserves the remainder.
        self.engine.update_timer(remaining, remaining > 0)
        self.refresh()
        if remaining == 0:
            self.clock.stop()
        self.timer_saved.emit()


class CelebrationOverlay(QWidget):
    """Short code-drawn particle burst for quest and level completion."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._particles: list[dict] = []
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._advance)
        self.hide()

    def burst(self, level_up: bool = False) -> None:
        self.setGeometry(self.parentWidget().rect())
        center = QPointF(self.width() / 2, self.height() / 2)
        colors = [QColor("#43e8ff"), QColor("#ff56c7"), QColor("#ffc857")]
        count = 65 if level_up else 38
        self._particles = []
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(2.0, 7.0)
            self._particles.append(
                {
                    "pos": QPointF(center),
                    "vel": QPointF(math.cos(angle) * speed, math.sin(angle) * speed - 2),
                    "life": random.randint(32, 62),
                    "color": random.choice(colors),
                    "size": random.uniform(2.5, 6.5),
                }
            )
        self.show()
        self.raise_()
        self.timer.start()

    def _advance(self) -> None:
        for particle in self._particles:
            particle["pos"] += particle["vel"]
            particle["vel"].setY(particle["vel"].y() + 0.11)
            particle["life"] -= 1
        self._particles = [particle for particle in self._particles if particle["life"] > 0]
        if not self._particles:
            self.timer.stop()
            self.hide()
        self.update()

    def paintEvent(self, event):  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for particle in self._particles:
            color = QColor(particle["color"])
            color.setAlpha(min(255, particle["life"] * 6))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            size = particle["size"]
            painter.drawEllipse(particle["pos"], size, size)
