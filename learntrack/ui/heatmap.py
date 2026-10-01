"""Calendar heatmap of recorded daily focus time."""

from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import QEvent, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSizePolicy, QToolTip, QVBoxLayout, QWidget

from .theme import COLORS
from .widgets import Card


HEATMAP_COLORS = ("#102237", "#1a4264", "#246795", "#3394cc", COLORS["accent"])


def format_focus_hours(seconds: int) -> str:
    # Round whole seconds to tenths of an hour, including exact halfway values.
    tenths = (seconds + 180) // 360
    hours = f"{tenths / 10:.1f}".removesuffix(".0")
    return f"{hours} {'hour' if tenths == 10 else 'hours'}"


def focus_intensity(seconds: int) -> int:
    if seconds == 0:
        return 0
    if seconds < 3600:
        return 1
    if seconds < 7200:
        return 2
    if seconds < 14400:
        return 3
    return 4


class FocusHeatmapGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.year = date.today().year
        self.today = date.today()
        self.daily_seconds: dict[str, int] = {}
        self.setFixedHeight(154)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setAccessibleName("Daily focused hours")
        self.setAccessibleDescription("Calendar of focus time. Hover a day to see its date and focused hours.")

    def set_data(self, year: int, daily_seconds: dict[str, int], today: date) -> None:
        self.year = year
        self.daily_seconds = daily_seconds
        self.today = today
        self.update()

    def day_cells(self) -> list[tuple[date, QRectF]]:
        first = date(self.year, 1, 1)
        last = date(self.year, 12, 31)
        offset = (first.weekday() + 1) % 7  # Sunday is the top row, as on GitHub.
        days = (last - first).days + 1
        weeks = (offset + days + 6) // 7
        gap = 3
        size = max(1.0, min(12.0, (self.width() - 36 - (weeks - 1) * gap) / weeks))
        step = size + gap
        return [
            (first + timedelta(days=index), QRectF(36 + ((index + offset) // 7) * step,
                                                   21 + ((index + offset) % 7) * step, size, size))
            for index in range(days)
        ]

    def tooltip_for_day(self, day: date) -> str:
        heading = day.strftime("%A, %d %B %Y")
        if day > self.today:
            return f"{heading}\nFuture date"
        return f"{heading}\n{format_focus_hours(self.daily_seconds.get(day.isoformat(), 0))} of focus"

    def event(self, event):
        if event.type() == QEvent.Type.ToolTip:
            for day, rect in self.day_cells():
                if rect.contains(event.pos()):
                    QToolTip.showText(event.globalPos(), self.tooltip_for_day(day), self)
                    return True
            QToolTip.hideText()
            return True
        return super().event(event)

    def paintEvent(self, event):  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = painter.font()
        font.setPixelSize(11)
        painter.setFont(font)
        cells = self.day_cells()
        size = cells[0][1].width()
        for month in range(1, 13):
            rect = next(rect for day, rect in cells if day.month == month and day.day == 1)
            painter.setPen(QColor(COLORS["muted"]))
            painter.drawText(QRectF(rect.x(), 0, 33, 17), Qt.AlignmentFlag.AlignLeft, date(self.year, month, 1).strftime("%b"))
        for row, caption in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
            painter.drawText(QRectF(0, 21 + row * (size + 3), 32, size), Qt.AlignmentFlag.AlignVCenter, caption)
        for day, rect in cells:
            seconds = self.daily_seconds.get(day.isoformat(), 0)
            color = HEATMAP_COLORS[focus_intensity(seconds)] if day <= self.today else COLORS["background"]
            painter.setBrush(QColor(color))
            painter.setPen(QPen(QColor(COLORS["accent"] if day == self.today else COLORS["border"]), 1))
            painter.drawRoundedRect(rect, 2, 2)
        legend_y = 21 + 7 * (size + 3) + 4
        painter.setPen(QColor(COLORS["muted"]))
        start = self.width() - 167
        painter.drawText(QRectF(start, legend_y, 34, 18), Qt.AlignmentFlag.AlignVCenter, "Less")
        for index, color in enumerate(HEATMAP_COLORS):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(start + 37 + index * 17, legend_y + 3, 12, 12), 2, 2)
        painter.setPen(QColor(COLORS["muted"]))
        painter.drawText(QRectF(start + 126, legend_y, 40, 18), Qt.AlignmentFlag.AlignVCenter, "More")


class FocusHeatmap(Card):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        heading = QHBoxLayout()
        title = QLabel("[ FOCUS HEATMAP ]")
        title.setObjectName("sectionTitle")
        heading.addWidget(title)
        heading.addStretch()
        self.year_selector = QComboBox()
        self.year_selector.setAccessibleName("Heatmap year")
        self.year_selector.setMinimumWidth(88)
        self.year_selector.currentIndexChanged.connect(self._show_year)
        heading.addWidget(self.year_selector)
        layout.addLayout(heading)
        self.grid = FocusHeatmapGrid()
        layout.addWidget(self.grid)
        self.setToolTip("Blue intensity: zero, under 1 hour, 1–2 hours, 2–4 hours, and 4+ hours. Breaks are excluded.")
        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        daily = self.engine.daily_focus_seconds
        years = sorted({today.year} | {date.fromisoformat(day).year for day in daily
                                      if date.fromisoformat(day).year <= today.year}, reverse=True)
        selected = self.year_selector.currentData()
        if [self.year_selector.itemData(index) for index in range(self.year_selector.count())] != years:
            self.year_selector.blockSignals(True)
            self.year_selector.clear()
            for year in years:
                self.year_selector.addItem(str(year), year)
            self.year_selector.setCurrentIndex(years.index(selected) if selected in years else 0)
            self.year_selector.blockSignals(False)
        self.grid.set_data(self.year_selector.currentData(), daily, today)

    def _show_year(self) -> None:
        if self.year_selector.currentData() is not None:
            self.grid.set_data(self.year_selector.currentData(), self.engine.daily_focus_seconds, date.today())
