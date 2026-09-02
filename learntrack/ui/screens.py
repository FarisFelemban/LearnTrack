"""Main application screens."""

from __future__ import annotations

from datetime import datetime
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..constants import DIFFICULTIES, PATH_STATUSES
from ..engine import GameRuleError
from .dialogs import BossDialog, CompletionDialog, PathDialog, QuestDialog, QuestImportDialog, RewardDialog
from .widgets import AnimatedXPBar, BackdropPanel, Card, StatCard, TimerPanel


def _friendly_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%d %b %Y, %H:%M")
    except (TypeError, ValueError):
        return str(value)


def _path_name(engine, path_id: str) -> str:
    return next((path["name"] for path in engine.state["paths"] if path["id"] == path_id), "Unknown path")


def _message(parent, title: str, error: Exception) -> None:
    QMessageBox.warning(parent, title, str(error))


def _confirm_start(parent, engine, kind: str, item: dict) -> bool:
    current = engine.progress.get("current_run")
    if current and not (current["kind"] == kind and current["item_id"] == item["id"]):
        collection = "quests" if current["kind"] == "quest" else "bosses"
        old = next((entry for entry in engine.state[collection] if entry["id"] == current["item_id"]), None)
        old_title = old["title"] if old else "the current run"
        answer = QMessageBox.question(
            parent,
            "Switch current run?",
            f"Switch from “{old_title}” to “{item['title']}”?\n\nNo XP or Gold will be awarded or removed.",
        )
        return answer == QMessageBox.StandardButton.Yes
    return True


class Page(QWidget):
    changed = Signal()

    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def refresh(self) -> None:
        pass


class DashboardScreen(Page):
    navigate = Signal(str)

    def __init__(self, engine):
        super().__init__(engine)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        heading = QHBoxLayout()
        title_box = QVBoxLayout()
        self.greeting = QLabel()
        self.greeting.setObjectName("pageTitle")
        title_box.addWidget(self.greeting)
        heading.addLayout(title_box)
        heading.addStretch()
        outer.addLayout(heading)
        outer.addSpacing(14)

        stats = QHBoxLayout()
        self.level_card = StatCard("Level", color_name="cyan")
        self.xp_card = StatCard("Total XP", color_name="magenta")
        self.gold_card = StatCard("Available Gold", color_name="gold")
        self.path_card = StatCard("Active path", color_name="cyan")
        for card in (self.level_card, self.xp_card, self.gold_card, self.path_card):
            stats.addWidget(card)
        outer.addLayout(stats)

        self.xp_bar = AnimatedXPBar()
        outer.addWidget(self.xp_bar)

        main_row = QHBoxLayout()
        self.hero = BackdropPanel()
        self.hero.setMinimumHeight(310)
        hero_layout = QVBoxLayout(self.hero)
        hero_layout.setContentsMargins(24, 24, 24, 24)
        current_caption = QLabel("CURRENT RUN")
        current_caption.setObjectName("cyan")
        hero_layout.addWidget(current_caption)
        self.current_title = QLabel()
        self.current_title.setObjectName("pageTitle")
        self.current_title.setWordWrap(True)
        hero_layout.addWidget(self.current_title)
        self.current_details = QLabel()
        self.current_details.setWordWrap(True)
        self.current_details.setMaximumWidth(620)
        hero_layout.addWidget(self.current_details)
        hero_layout.addStretch()
        quick_row = QHBoxLayout()
        self.current_action = QPushButton("Open current run")
        self.current_action.setProperty("accent", True)
        self.current_action.clicked.connect(self._open_current)
        board = QPushButton("Quest board")
        board.clicked.connect(lambda: self.navigate.emit("quests"))
        paths = QPushButton("Learning paths")
        paths.clicked.connect(lambda: self.navigate.emit("paths"))
        quick_row.addWidget(self.current_action)
        quick_row.addWidget(board)
        quick_row.addWidget(paths)
        quick_row.addStretch()
        hero_layout.addLayout(quick_row)
        main_row.addWidget(self.hero, 3)
        self.timer_panel = TimerPanel(engine)
        self.timer_panel.timer_saved.connect(self.changed)
        main_row.addWidget(self.timer_panel, 2)
        outer.addLayout(main_row)

        activity_card = Card()
        activity_layout = QVBoxLayout(activity_card)
        activity_title = QLabel("RECENT ACTIVITY")
        activity_title.setObjectName("sectionTitle")
        activity_layout.addWidget(activity_title)
        self.activity = QLabel()
        self.activity.setWordWrap(True)
        self.activity.setTextFormat(Qt.TextFormat.RichText)
        activity_layout.addWidget(self.activity)
        outer.addWidget(activity_card)
        self.refresh()

    def _open_current(self) -> None:
        current = self.engine.progress.get("current_run")
        self.navigate.emit("bosses" if current and current["kind"] == "boss" else "quests")

    def refresh(self) -> None:
        profile = self.engine.state["profile"]
        animate = profile.get("animations_enabled", True)
        self.greeting.setText(f"Welcome back, {profile['player_name']}")
        self.level_card.set_value(self.engine.level)
        self.xp_card.set_number(self.engine.progress["xp"], animate=animate)
        self.gold_card.set_number(self.engine.progress["gold"], animate=animate)
        active_paths = [path for path in self.engine.state["paths"] if path["status"] == "active" and not path.get("archived")]
        self.path_card.set_value(active_paths[0]["name"] if active_paths else "None")
        self.xp_bar.show_xp(self.engine.progress["xp"], animate)
        self.hero.set_artwork_visible(profile.get("show_current_run_background", True))
        current = self.engine.progress.get("current_run")
        if current:
            collection = "quests" if current["kind"] == "quest" else "bosses"
            item = next((entry for entry in self.engine.state[collection] if entry["id"] == current["item_id"]), None)
            if item:
                self.current_title.setText(item["title"])
                details = item.get("definition_of_done") or item.get("victory_condition", "")
                self.current_details.setText(f"{_path_name(self.engine, item['path_id'])}\n\n{details}")
                self.current_action.setText("Open current run")
                self.current_action.setEnabled(True)
            else:
                self.current_title.setText("Current content is unavailable")
                self.current_details.clear()
        else:
            self.current_title.setText("Choose one focused quest")
            self.current_details.setText("Start a quest from the board. Only evidence of a completed definition of done earns rewards.")
            self.current_action.setText("Choose a quest")
            self.current_action.setEnabled(True)
        entries = self.engine.progress["activity"][:5]
        if not entries:
            self.activity.setText("<span style='color:#8296aa'>No activity yet. Start your first quest.</span>")
        else:
            self.activity.setText(
                "<br>".join(
                    f"<span style='color:#4be2f5'>•</span> {escape(entry['message'])} "
                    f"<span style='color:#62788d'>— {escape(_friendly_time(entry['timestamp']))}</span>"
                    for entry in entries
                )
            )
        self.timer_panel.refresh()


class QuestBoardScreen(Page):
    completed = Signal(bool)

    def __init__(self, engine):
        super().__init__(engine)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        title_row = QHBoxLayout()
        title = QLabel("Quest Board")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        add = QPushButton("+ Add quest")
        add.setProperty("accent", True)
        add.clicked.connect(self.add_quest)
        import_button = QPushButton("Generate and import quests…")
        import_button.clicked.connect(self.import_quests)
        title_row.addWidget(import_button)
        title_row.addWidget(add)
        outer.addLayout(title_row)
        filters = QHBoxLayout()
        self.path_filter = QComboBox()
        self.stage_filter = QComboBox()
        self.difficulty_filter = QComboBox()
        self.status_filter = QComboBox()
        for label, widget in (
            ("Path", self.path_filter),
            ("Stage", self.stage_filter),
            ("Difficulty", self.difficulty_filter),
            ("Status", self.status_filter),
        ):
            filters.addWidget(QLabel(label))
            filters.addWidget(widget)
            widget.currentIndexChanged.connect(self.populate_list)
        filters.addStretch()
        outer.addLayout(filters)
        splitter = QSplitter()
        self.list = QListWidget()
        self.list.setMinimumWidth(340)
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.currentItemChanged.connect(self.show_details)
        splitter.addWidget(self.list)
        detail = Card()
        detail_layout = QVBoxLayout(detail)
        self.detail_title = QLabel("Select a quest")
        self.detail_title.setObjectName("pageTitle")
        self.detail_title.setWordWrap(True)
        self.detail_meta = QLabel()
        self.detail_meta.setObjectName("cyan")
        self.detail_body = QTextBrowser()
        self.detail_body.setOpenExternalLinks(False)
        self.detail_body.setFrameShape(QFrame.Shape.NoFrame)
        detail_layout.addWidget(self.detail_title)
        detail_layout.addWidget(self.detail_meta)
        detail_layout.addWidget(self.detail_body, 1)
        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start quest")
        self.start_button.setProperty("accent", True)
        self.start_button.clicked.connect(self.start_selected)
        self.complete_button = QPushButton("Complete")
        self.complete_button.clicked.connect(self.complete_selected)
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_selected)
        self.reset_button = QPushButton("Reset quest")
        self.reset_button.clicked.connect(self.reset_selected)
        self.archive_button = QPushButton("Archive")
        self.archive_button.setProperty("danger", True)
        self.archive_button.clicked.connect(self.archive_selected)
        for button in (self.start_button, self.complete_button):
            buttons.addWidget(button)
        detail_layout.addLayout(buttons)
        management_buttons = QHBoxLayout()
        for button in (self.edit_button, self.reset_button, self.archive_button):
            management_buttons.addWidget(button)
        detail_layout.addLayout(management_buttons)
        splitter.addWidget(detail)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)
        self.refresh()

    def selected(self) -> dict | None:
        item = self.list.currentItem()
        if not item:
            return None
        quest_id = item.data(Qt.ItemDataRole.UserRole)
        return next((quest for quest in self.engine.state["quests"] if quest["id"] == quest_id), None)

    def refresh(self) -> None:
        selected_id = self.selected()["id"] if self.selected() else None
        current_path = self.path_filter.currentData()
        current_stage = self.stage_filter.currentData()
        self.path_filter.blockSignals(True)
        self.path_filter.clear()
        self.path_filter.addItem("All paths", None)
        for path in self.engine.state["paths"]:
            self.path_filter.addItem(path["name"], path["id"])
        self.path_filter.setCurrentIndex(max(0, self.path_filter.findData(current_path)))
        self.path_filter.blockSignals(False)
        self.stage_filter.blockSignals(True)
        self.stage_filter.clear()
        self.stage_filter.addItem("All stages", None)
        for stage in dict.fromkeys(quest["stage"] for quest in self.engine.state["quests"]):
            self.stage_filter.addItem(stage, stage)
        self.stage_filter.setCurrentIndex(max(0, self.stage_filter.findData(current_stage)))
        self.stage_filter.blockSignals(False)
        if self.difficulty_filter.count() == 0:
            self.difficulty_filter.addItem("All difficulties", None)
            for key, data in DIFFICULTIES.items():
                if key != "boss":
                    self.difficulty_filter.addItem(data["label"], key)
        if self.status_filter.count() == 0:
            self.status_filter.addItem("All statuses", None)
            for status in ("available", "in_progress", "completed", "archived"):
                self.status_filter.addItem(status.replace("_", " ").title(), status)
        self.populate_list(selected_id)

    def populate_list(self, selected_id: str | int | None = None) -> None:
        if isinstance(selected_id, int):
            selected_id = self.selected()["id"] if self.selected() else None
        filters = {
            "path_id": self.path_filter.currentData(),
            "stage": self.stage_filter.currentData(),
            "difficulty": self.difficulty_filter.currentData(),
            "status": self.status_filter.currentData(),
        }
        self.list.clear()
        for quest in self.engine.state["quests"]:
            if any(value is not None and quest.get(field) != value for field, value in filters.items()):
                continue
            icon = {"available": "◇", "in_progress": "▶", "completed": "✓", "archived": "—"}.get(quest["status"], "◇")
            item = QListWidgetItem(f"{icon}  {quest['title']}\n     {_path_name(self.engine, quest['path_id'])}  •  {quest['stage']}")
            item.setData(Qt.ItemDataRole.UserRole, quest["id"])
            color = DIFFICULTIES.get(quest["difficulty"], {}).get("color", "#9cb2c4")
            item.setForeground(QColor(color))
            self.list.addItem(item)
            if quest["id"] == selected_id:
                self.list.setCurrentItem(item)
        if self.list.currentItem() is None and self.list.count():
            self.list.setCurrentRow(0)
        if not self.list.count():
            self.show_details(None)

    def show_details(self, current, previous=None) -> None:
        quest = self.selected()
        enabled = quest is not None
        for button in (self.start_button, self.complete_button, self.edit_button, self.reset_button, self.archive_button):
            button.setEnabled(enabled)
        if not quest:
            self.detail_title.setText("No quests match these filters")
            self.detail_meta.clear()
            self.detail_body.clear()
            return
        self.detail_title.setText(quest["title"])
        diff = DIFFICULTIES.get(quest["difficulty"], {"label": quest["difficulty"]})["label"]
        self.detail_meta.setText(
            f"{_path_name(self.engine, quest['path_id'])}  •  {quest['stage']}  •  {diff}  •  {quest['status'].replace('_', ' ').title()}"
        )
        bonus_html = "".join(
            f"<li>{escape(bonus['title'])} — +{bonus['xp']} XP, +{bonus['gold']} Gold</li>" for bonus in quest.get("bonuses", [])
        ) or "<li>No optional bonuses</li>"
        self.detail_body.setHtml(
            f"<h3 style='color:#dff8ff'>Definition of done</h3><p>{escape(quest['definition_of_done'])}</p>"
            f"<h3 style='color:#ffc857'>Base reward</h3><p>+{quest['xp']} XP &nbsp; +{quest['gold']} Gold</p>"
            f"<h3 style='color:#ff71cf'>Optional objectives</h3><ul>{bonus_html}</ul>"
        )
        current_run = self.engine.progress.get("current_run")
        is_current = bool(current_run and current_run["kind"] == "quest" and current_run["item_id"] == quest["id"])
        claimable = is_current and quest["status"] != "completed" and not quest.get("archived")
        self.start_button.setText("Current quest" if is_current else "Start quest")
        self.start_button.setEnabled(not is_current and quest["status"] not in ("completed", "archived"))
        self.complete_button.setEnabled(claimable)
        self.reset_button.setEnabled(quest["status"] in ("in_progress", "completed") and not quest.get("archived"))
        self.archive_button.setEnabled(not quest.get("archived"))

    def start_selected(self) -> None:
        quest = self.selected()
        if not quest or not _confirm_start(self, self.engine, "quest", quest):
            return
        try:
            self.engine.start_run("quest", quest["id"])
            self.changed.emit()
        except GameRuleError as exc:
            _message(self, "Cannot start quest", exc)

    def complete_selected(self) -> None:
        quest = self.selected()
        if not quest:
            return
        replay = any(claim["item_id"] == quest["id"] for claim in self.engine.progress["quest_claims"])
        dialog = CompletionDialog(quest, self, replay=replay)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        xp = 0 if replay else quest["xp"] + sum(
            bonus["xp"] for bonus in quest.get("bonuses", []) if bonus["id"] in dialog.selected_bonuses
        )
        gold = 0 if replay else quest["gold"] + sum(
            bonus["gold"] for bonus in quest.get("bonuses", []) if bonus["id"] in dialog.selected_bonuses
        )
        answer = QMessageBox.question(
            self,
            "Confirm quest replay" if replay else "Confirm quest claim",
            (
                f"Record this replay of “{quest['title']}”?\n\nIt grants no additional XP or Gold."
                if replay
                else f"Claim “{quest['title']}” for +{xp} XP and +{gold} Gold?\n\nThis reward can only be claimed once."
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            claim = self.engine.complete_quest(
                quest["id"], dialog.evidence_text, [] if replay else dialog.selected_bonuses
            )
            self.changed.emit()
            self.completed.emit(claim["level_after"] > claim["level_before"])
        except GameRuleError as exc:
            _message(self, "Cannot claim quest", exc)

    def add_quest(self) -> None:
        dialog = QuestDialog(self.engine.state["paths"], self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.engine.add_quest(dialog.data())
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot add quest", exc)

    def edit_selected(self) -> None:
        quest = self.selected()
        if not quest:
            return
        dialog = QuestDialog(self.engine.state["paths"], self, quest)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.engine.update_quest(quest["id"], dialog.data())
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot edit quest", exc)

    def import_quests(self) -> None:
        dialog = QuestImportDialog(self.engine, self, self.path_filter.currentData())
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.changed.emit()

    def archive_selected(self) -> None:
        quest = self.selected()
        if not quest:
            return
        if QMessageBox.question(self, "Archive quest?", f"Archive “{quest['title']}”? Its history will be preserved.") == QMessageBox.StandardButton.Yes:
            self.engine.archive("quests", quest["id"])
            self.changed.emit()

    def reset_selected(self) -> None:
        quest = self.selected()
        if not quest or quest["status"] not in ("in_progress", "completed") or quest.get("archived"):
            return
        explanation = (
            "Its original Journal entry and rewards will stay. The next completion is recorded as a 0-reward replay."
            if quest["status"] == "completed"
            else "It will return to Available and stop being the current quest."
        )
        answer = QMessageBox.question(self, "Reset quest?", f"Reset “{quest['title']}”?\n\n{explanation}")
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self.engine.reset_quest(quest["id"])
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot reset quest", exc)


class PathsScreen(Page):
    def __init__(self, engine):
        super().__init__(engine)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        title_row = QHBoxLayout()
        title = QLabel("Learning Paths")
        title.setObjectName("pageTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        add = QPushButton("+ Add path")
        add.setProperty("accent", True)
        add.clicked.connect(self.add_path)
        title_row.addWidget(add)
        outer.addLayout(title_row)
        splitter = QSplitter()
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.currentItemChanged.connect(self.show_details)
        splitter.addWidget(self.tree)
        card = Card()
        card_layout = QVBoxLayout(card)
        self.title = QLabel("Select a path")
        self.title.setObjectName("pageTitle")
        self.status = QLabel()
        self.status.setObjectName("cyan")
        self.goal = QLabel()
        self.goal.setWordWrap(True)
        self.objective = QLabel()
        self.objective.setWordWrap(True)
        self.xp = QLabel()
        self.xp.setObjectName("gold")
        card_layout.addWidget(self.title)
        card_layout.addWidget(self.status)
        card_layout.addSpacing(10)
        card_layout.addWidget(QLabel("GOAL"))
        card_layout.addWidget(self.goal)
        card_layout.addWidget(QLabel("CURRENT OBJECTIVE"))
        card_layout.addWidget(self.objective)
        card_layout.addWidget(self.xp)
        card_layout.addStretch()
        controls = QHBoxLayout()
        edit = QPushButton("Edit")
        edit.clicked.connect(self.edit_path)
        archive = QPushButton("Archive")
        archive.setProperty("danger", True)
        archive.clicked.connect(self.archive_path)
        self.edit_button, self.archive_button = edit, archive
        controls.addWidget(edit)
        controls.addWidget(archive)
        card_layout.addLayout(controls)
        splitter.addWidget(card)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)
        self.refresh()

    def selected(self) -> dict | None:
        item = self.tree.currentItem()
        if not item or item.data(0, Qt.ItemDataRole.UserRole) is None:
            return None
        path_id = item.data(0, Qt.ItemDataRole.UserRole)
        return next((path for path in self.engine.state["paths"] if path["id"] == path_id), None)

    def refresh(self) -> None:
        selected = self.selected()
        selected_id = selected["id"] if selected else None
        self.tree.clear()
        first = None
        for status in PATH_STATUSES:
            root = QTreeWidgetItem([status.upper()])
            root.setForeground(0, QColor("#6f8ca3"))
            self.tree.addTopLevelItem(root)
            for path in self.engine.state["paths"]:
                if path["status"] == status and not path.get("archived"):
                    child = QTreeWidgetItem([f"{path['name']}  •  {self.engine.path_xp(path['id'])} XP"])
                    child.setData(0, Qt.ItemDataRole.UserRole, path["id"])
                    root.addChild(child)
                    first = first or child
                    if path["id"] == selected_id:
                        self.tree.setCurrentItem(child)
            root.setExpanded(True)
        if not self.tree.currentItem() and first:
            self.tree.setCurrentItem(first)
        self.show_details()

    def show_details(self, current=None, previous=None) -> None:
        path = self.selected()
        self.edit_button.setEnabled(path is not None)
        self.archive_button.setEnabled(path is not None and not path.get("archived"))
        if not path:
            self.title.setText("Select a learning path")
            self.status.clear(); self.goal.clear(); self.objective.clear(); self.xp.clear()
            return
        self.title.setText(path["name"])
        self.status.setText(path["status"].upper())
        self.goal.setText(path["goal"] or "No goal written yet.")
        self.objective.setText(path["objective"] or "No current objective.")
        self.xp.setText(f"{self.engine.path_xp(path['id']):,} XP earned on this path")

    def add_path(self) -> None:
        dialog = PathDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.engine.add_path(**dialog.data())
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot add path", exc)

    def edit_path(self) -> None:
        path = self.selected()
        if not path:
            return
        dialog = PathDialog(self, path)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.engine.update_path(path["id"], **dialog.data())
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot edit path", exc)

    def archive_path(self) -> None:
        path = self.selected()
        if path and QMessageBox.question(self, "Archive path?", "The path and its earned history will remain in the save.") == QMessageBox.StandardButton.Yes:
            self.engine.archive("paths", path["id"])
            self.changed.emit()


class BossesScreen(Page):
    completed = Signal(bool)

    def __init__(self, engine):
        super().__init__(engine)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        header = QHBoxLayout()
        title = QLabel("Bosses")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        add = QPushButton("+ Add boss")
        add.setProperty("accent", True)
        add.clicked.connect(self.add_boss)
        header.addWidget(add)
        outer.addLayout(header)
        splitter = QSplitter()
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.currentItemChanged.connect(self.show_details)
        splitter.addWidget(self.list)
        card = Card()
        layout = QVBoxLayout(card)
        self.title = QLabel("Select a boss")
        self.title.setObjectName("pageTitle")
        self.meta = QLabel()
        self.meta.setObjectName("magenta")
        self.body = QTextBrowser()
        self.body.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(self.title)
        layout.addWidget(self.meta)
        layout.addWidget(self.body, 1)
        controls = QHBoxLayout()
        self.start = QPushButton("Start boss")
        self.start.setProperty("accent", True)
        self.start.clicked.connect(self.start_boss)
        self.complete = QPushButton("Claim victory")
        self.complete.clicked.connect(self.complete_boss)
        self.edit = QPushButton("Edit")
        self.edit.clicked.connect(self.edit_boss)
        self.archive = QPushButton("Archive")
        self.archive.setProperty("danger", True)
        self.archive.clicked.connect(self.archive_boss)
        for button in (self.start, self.complete, self.edit, self.archive):
            controls.addWidget(button)
        layout.addLayout(controls)
        splitter.addWidget(card)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)
        self.refresh()

    def selected(self) -> dict | None:
        row = self.list.currentItem()
        if not row:
            return None
        item_id = row.data(Qt.ItemDataRole.UserRole)
        return next((boss for boss in self.engine.state["bosses"] if boss["id"] == item_id), None)

    def refresh(self) -> None:
        selected = self.selected()
        selected_id = selected["id"] if selected else None
        self.list.clear()
        for boss in self.engine.state["bosses"]:
            icon = {"available": "◆", "in_progress": "▶", "completed": "✓", "archived": "—"}.get(boss["status"], "◆")
            item = QListWidgetItem(f"{icon}  {boss['title']}\n     {_path_name(self.engine, boss['path_id'])}")
            item.setData(Qt.ItemDataRole.UserRole, boss["id"])
            item.setForeground(QColor("#ff637e" if boss["status"] != "completed" else "#52e08b"))
            self.list.addItem(item)
            if boss["id"] == selected_id:
                self.list.setCurrentItem(item)
        if not self.list.currentItem() and self.list.count():
            self.list.setCurrentRow(0)
        self.show_details()

    def show_details(self, current=None, previous=None) -> None:
        boss = self.selected()
        for button in (self.start, self.complete, self.edit, self.archive):
            button.setEnabled(boss is not None)
        if not boss:
            self.title.setText("No bosses yet")
            self.meta.clear(); self.body.clear()
            return
        self.title.setText(boss["title"])
        self.meta.setText(f"{_path_name(self.engine, boss['path_id'])} • {boss['status'].replace('_', ' ').title()} • +{boss['xp']} XP • +{boss['gold']} Gold")
        requirements = "".join(
            f"<li>{escape(req['text'])}{'' if req.get('mandatory', True) else ' <em>(optional)</em>'}</li>" for req in boss["requirements"]
        )
        bonuses = "".join(
            f"<li>{escape(bonus['title'])} — +{bonus['xp']} XP, +{bonus['gold']} Gold</li>" for bonus in boss.get("bonuses", [])
        ) or "<li>No optional objectives</li>"
        self.body.setHtml(
            f"<h3 style='color:#e8f4ff'>Victory condition</h3><p>{escape(boss['victory_condition'])}</p>"
            f"<h3 style='color:#ff8ca0'>Requirements</h3><ul>{requirements}</ul>"
            f"<h3 style='color:#ffc857'>Optional objectives</h3><ul>{bonuses}</ul>"
        )
        current_run = self.engine.progress.get("current_run")
        is_current = bool(current_run and current_run["kind"] == "boss" and current_run["item_id"] == boss["id"])
        self.start.setText("Current boss" if is_current else "Start boss")
        self.start.setEnabled(not is_current and boss["status"] not in ("completed", "archived"))
        self.complete.setEnabled(is_current and boss["status"] != "completed" and not boss.get("archived"))
        self.archive.setEnabled(not boss.get("archived"))

    def start_boss(self) -> None:
        boss = self.selected()
        if not boss or not _confirm_start(self, self.engine, "boss", boss):
            return
        try:
            self.engine.start_run("boss", boss["id"])
            self.changed.emit()
        except GameRuleError as exc:
            _message(self, "Cannot start boss", exc)

    def complete_boss(self) -> None:
        boss = self.selected()
        if not boss:
            return
        dialog = CompletionDialog(boss, self, boss=True)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        xp = boss["xp"] + sum(b["xp"] for b in boss.get("bonuses", []) if b["id"] in dialog.selected_bonuses)
        gold = boss["gold"] + sum(b["gold"] for b in boss.get("bonuses", []) if b["id"] in dialog.selected_bonuses)
        answer = QMessageBox.question(
            self,
            "Confirm boss victory",
            f"Claim victory over “{boss['title']}” for +{xp} XP and +{gold} Gold?\n\nThis reward can only be claimed once.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            claim = self.engine.complete_boss(
                boss["id"], dialog.evidence_text, dialog.checked_requirements, dialog.selected_bonuses
            )
            self.changed.emit()
            self.completed.emit(claim["level_after"] > claim["level_before"])
        except GameRuleError as exc:
            _message(self, "Cannot claim boss", exc)

    def add_boss(self) -> None:
        dialog = BossDialog(self.engine.state["paths"], self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.engine.add_boss(dialog.data())
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot add boss", exc)

    def edit_boss(self) -> None:
        boss = self.selected()
        if not boss:
            return
        dialog = BossDialog(self.engine.state["paths"], self, boss)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.engine.update_boss(boss["id"], dialog.data())
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot edit boss", exc)

    def archive_boss(self) -> None:
        boss = self.selected()
        if boss and QMessageBox.question(self, "Archive boss?", "Its completion history will be preserved.") == QMessageBox.StandardButton.Yes:
            self.engine.archive("bosses", boss["id"])
            self.changed.emit()


class ShopScreen(Page):
    def __init__(self, engine):
        super().__init__(engine)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        header = QHBoxLayout()
        title = QLabel("Reward Shop")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()
        self.balance = QLabel()
        self.balance.setObjectName("gold")
        header.addWidget(self.balance)
        add = QPushButton("+ Add reward")
        add.setProperty("accent", True)
        add.clicked.connect(self.add_reward)
        header.addWidget(add)
        outer.addLayout(header)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Reward", "Cost", "Unlock", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        outer.addWidget(self.table, 2)
        history_title = QLabel("PURCHASE HISTORY")
        history_title.setObjectName("sectionTitle")
        outer.addWidget(history_title)
        self.history = QTableWidget(0, 4)
        self.history.setHorizontalHeaderLabels(["Date", "Reward", "Gold spent", "Gold remaining"])
        self.history.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history.verticalHeader().hide()
        outer.addWidget(self.history, 1)
        self.refresh()

    def refresh(self) -> None:
        self.balance.setText(f"LEVEL {self.engine.level}  •  {self.engine.progress['gold']:,} GOLD")
        rewards = [item for item in self.engine.state["shop_rewards"] if not item.get("archived")]
        self.table.setRowCount(len(rewards))
        for row, reward in enumerate(rewards):
            unlocked = self.engine.level >= reward["level_required"]
            affordable = self.engine.progress["gold"] >= reward["cost"]
            self.table.setItem(row, 0, QTableWidgetItem(reward["title"]))
            self.table.setItem(row, 1, QTableWidgetItem(f"{reward['cost']:,} Gold"))
            self.table.setItem(row, 2, QTableWidgetItem(f"Level {reward['level_required']}"))
            status = "Ready" if unlocked and affordable else "Need Gold" if unlocked else "Locked"
            self.table.setItem(row, 3, QTableWidgetItem(status))
            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(0, 2, 0, 2)
            buy = QPushButton("Buy")
            buy.setEnabled(unlocked and affordable)
            buy.clicked.connect(lambda checked=False, item_id=reward["id"]: self.buy_reward(item_id))
            edit = QPushButton("Edit")
            edit.clicked.connect(lambda checked=False, item_id=reward["id"]: self.edit_reward(item_id))
            archive = QPushButton("Archive")
            archive.clicked.connect(lambda checked=False, item_id=reward["id"]: self.archive_reward(item_id))
            action_layout.addWidget(buy); action_layout.addWidget(edit); action_layout.addWidget(archive)
            self.table.setCellWidget(row, 4, actions)
        self.history.setRowCount(len(self.engine.progress["purchases"]))
        for row, purchase in enumerate(self.engine.progress["purchases"]):
            values = (
                _friendly_time(purchase["purchased_at"]),
                purchase["snapshot"]["title"],
                str(purchase["gold_spent"]),
                str(purchase["gold_remaining"]),
            )
            for column, value in enumerate(values):
                self.history.setItem(row, column, QTableWidgetItem(value))

    def _reward(self, item_id: str) -> dict:
        return next(item for item in self.engine.state["shop_rewards"] if item["id"] == item_id)

    def buy_reward(self, item_id: str) -> None:
        reward = self._reward(item_id)
        answer = QMessageBox.question(
            self,
            "Confirm purchase",
            f"Spend {reward['cost']} Gold on “{reward['title']}”?\n\nYou will have {self.engine.progress['gold'] - reward['cost']} Gold remaining.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self.engine.purchase_reward(item_id)
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot purchase reward", exc)

    def add_reward(self) -> None:
        dialog = RewardDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.engine.add_shop_reward(**dialog.data())
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot add reward", exc)

    def edit_reward(self, item_id: str) -> None:
        reward = self._reward(item_id)
        dialog = RewardDialog(self, reward)
        if dialog.exec() == dialog.DialogCode.Accepted:
            try:
                self.engine.update_shop_reward(item_id, **dialog.data())
                self.changed.emit()
            except GameRuleError as exc:
                _message(self, "Cannot edit reward", exc)

    def archive_reward(self, item_id: str) -> None:
        reward = self._reward(item_id)
        if QMessageBox.question(self, "Archive reward?", f"Archive “{reward['title']}”? Purchase history remains unchanged.") == QMessageBox.StandardButton.Yes:
            self.engine.archive("shop_rewards", item_id)
            self.changed.emit()


class JournalScreen(Page):
    def __init__(self, engine):
        super().__init__(engine)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        self.title = QLabel()
        self.title.setObjectName("pageTitle")
        outer.addWidget(self.title)
        self.stats = QLabel()
        self.stats.setTextFormat(Qt.TextFormat.RichText)
        self.stats.setWordWrap(True)
        outer.addWidget(self.stats)
        tabs = QTabWidget()
        self.claims_table = QTableWidget(0, 6)
        self.claims_table.setHorizontalHeaderLabels(["Date", "Path", "Type", "Quest / Boss", "Reward", "Evidence"])
        self.claims_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.claims_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.claims_table.verticalHeader().hide()
        tabs.addTab(self.claims_table, "Completed quests & bosses")
        self.reward_table = QTableWidget(0, 4)
        self.reward_table.setHorizontalHeaderLabels(["Date", "Earned reward", "Gold spent", "Remaining"])
        self.reward_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.reward_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.reward_table.verticalHeader().hide()
        tabs.addTab(self.reward_table, "Earned rewards")
        self.activity = QListWidget()
        tabs.addTab(self.activity, "Activity history")
        outer.addWidget(tabs, 1)
        self.refresh()

    def refresh(self) -> None:
        progress = self.engine.progress
        rewarded_quests = sum(not claim.get("is_replay", False) for claim in progress["quest_claims"])
        replay_count = sum(claim.get("is_replay", False) for claim in progress["quest_claims"])
        self.title.setText(f"{self.engine.state['profile']['player_name']} — Player Journal")
        self.stats.setText(
            f"<b style='color:#45e6ff'>Level {self.engine.level}</b> &nbsp;•&nbsp; "
            f"{progress['xp']:,} total XP &nbsp;•&nbsp; "
            f"<span style='color:#ffc857'>{progress['gold']:,} available Gold</span> &nbsp;•&nbsp; "
            f"{progress['total_gold_earned']:,} total Gold earned &nbsp;•&nbsp; "
            f"{rewarded_quests} quests &nbsp;•&nbsp; {replay_count} replays &nbsp;•&nbsp; "
            f"{len(progress['boss_claims'])} bosses defeated"
        )
        claims = sorted(progress["quest_claims"] + progress["boss_claims"], key=lambda item: item["completed_at"], reverse=True)
        self.claims_table.setRowCount(len(claims))
        for row, claim in enumerate(claims):
            values = (
                _friendly_time(claim["completed_at"]),
                _path_name(self.engine, claim["path_id"]),
                "Quest Replay" if claim.get("is_replay", False) else claim["kind"].title(),
                claim["snapshot"]["title"],
                f"+{claim['xp_awarded']} XP, +{claim['gold_awarded']} Gold",
                claim["evidence"],
            )
            for column, value in enumerate(values):
                self.claims_table.setItem(row, column, QTableWidgetItem(value))
        self.reward_table.setRowCount(len(progress["purchases"]))
        for row, purchase in enumerate(progress["purchases"]):
            values = (
                _friendly_time(purchase["purchased_at"]), purchase["snapshot"]["title"],
                str(purchase["gold_spent"]), str(purchase["gold_remaining"]),
            )
            for column, value in enumerate(values):
                self.reward_table.setItem(row, column, QTableWidgetItem(value))
        self.activity.clear()
        for entry in progress["activity"]:
            self.activity.addItem(f"{_friendly_time(entry['timestamp'])}  •  {entry['message']}")


class SettingsScreen(Page):
    export_requested = Signal()
    import_requested = Signal()
    reset_requested = Signal()

    def __init__(self, engine):
        super().__init__(engine)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(22, 18, 22, 22)
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        outer.addWidget(title)
        profile = Card()
        form = QGridLayout(profile)
        heading = QLabel("PLAYER PROFILE")
        heading.setObjectName("sectionTitle")
        form.addWidget(heading, 0, 0, 1, 3)
        form.addWidget(QLabel("Player name"), 1, 0)
        self.name = QLineEdit()
        form.addWidget(self.name, 1, 1)
        save_name = QPushButton("Save name")
        save_name.clicked.connect(self.save_name)
        form.addWidget(save_name, 1, 2)
        self.animations = QCheckBox("Enable restrained interface animations")
        self.animations.toggled.connect(self.save_animations)
        form.addWidget(self.animations, 2, 0, 1, 3)
        self.current_run_background = QCheckBox("Show artwork behind Current Run")
        self.current_run_background.toggled.connect(self.save_current_run_background)
        form.addWidget(self.current_run_background, 3, 0, 1, 3)
        outer.addWidget(profile)
        quest_import = Card()
        import_layout = QVBoxLayout(quest_import)
        heading = QLabel("QUEST IMPORT")
        heading.setObjectName("sectionTitle")
        import_layout.addWidget(heading)
        import_note = QLabel(
            "Build a copyable prompt for your preferred AI, then preview and import its generated quests."
        )
        import_note.setObjectName("muted")
        import_note.setWordWrap(True)
        import_layout.addWidget(import_note)
        self.custom_import_rewards = QCheckBox("Allow AI-generated imports to set custom XP, Gold, and bonuses")
        self.custom_import_rewards.toggled.connect(self.save_custom_import_rewards)
        import_layout.addWidget(self.custom_import_rewards)
        import_quests = QPushButton("Generate and import quests…")
        import_quests.clicked.connect(self.import_quests)
        import_layout.addWidget(import_quests)
        outer.addWidget(quest_import)
        data = Card()
        layout = QVBoxLayout(data)
        heading = QLabel("SAVE DATA")
        heading.setObjectName("sectionTitle")
        layout.addWidget(heading)
        note = QLabel("Exports are readable JSON. Imports are validated and require confirmation before replacing progress.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        row = QHBoxLayout()
        export = QPushButton("Export save…")
        export.clicked.connect(self.export_requested)
        import_button = QPushButton("Import save…")
        import_button.clicked.connect(self.import_requested)
        reset = QPushButton("Reset all progress…")
        reset.setProperty("danger", True)
        reset.clicked.connect(self.reset_requested)
        row.addWidget(export); row.addWidget(import_button); row.addStretch(); row.addWidget(reset)
        layout.addLayout(row)
        outer.addWidget(data)
        about = Card()
        about_layout = QVBoxLayout(about)
        about_layout.addWidget(QLabel("LEARNTRACK 1.0"))
        details = QLabel("Single-player • Offline • Evidence-based rewards • No audio\nXP never decreases. Gold changes only through earned rewards and confirmed purchases.")
        details.setObjectName("muted")
        about_layout.addWidget(details)
        outer.addWidget(about)
        outer.addStretch()
        self.refresh()

    def refresh(self) -> None:
        self.name.setText(self.engine.state["profile"]["player_name"])
        self.animations.blockSignals(True)
        self.animations.setChecked(self.engine.state["profile"].get("animations_enabled", True))
        self.animations.blockSignals(False)
        self.current_run_background.blockSignals(True)
        self.current_run_background.setChecked(
            self.engine.state["profile"].get("show_current_run_background", True)
        )
        self.current_run_background.blockSignals(False)
        self.custom_import_rewards.blockSignals(True)
        self.custom_import_rewards.setChecked(
            self.engine.state["profile"].get("allow_custom_import_rewards", False)
        )
        self.custom_import_rewards.blockSignals(False)

    def save_name(self) -> None:
        try:
            self.engine.set_player_name(self.name.text())
            self.changed.emit()
        except GameRuleError as exc:
            _message(self, "Cannot save name", exc)

    def save_animations(self, enabled: bool) -> None:
        self.engine.set_animations(enabled)
        self.changed.emit()

    def save_custom_import_rewards(self, enabled: bool) -> None:
        self.engine.set_custom_import_rewards(enabled)
        self.changed.emit()

    def save_current_run_background(self, enabled: bool) -> None:
        self.engine.set_current_run_background(enabled)
        self.changed.emit()

    def import_quests(self) -> None:
        dialog = QuestImportDialog(self.engine, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.changed.emit()
