"""Focused data-entry dialogs used across the application."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ..constants import DIFFICULTIES, PATH_STATUSES
from ..engine import GameRuleError
from ..quest_import import build_boss_prompt, build_quest_prompt, parse_boss_batch, parse_quest_batch


def _buttons(dialog: QDialog, save_text: str = "Save") -> QDialogButtonBox:
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Save).setText(save_text)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons


def _parse_bonuses(text: str, existing: list[dict] | None = None) -> list[dict]:
    """Parse one `title | xp | gold` bonus per line."""
    existing_by_title = {item["title"]: item for item in (existing or [])}
    result = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        parts = [part.strip() for part in raw.split("|")]
        if len(parts) != 3:
            raise GameRuleError(f"Bonus line {line_number} must be: title | XP | Gold")
        try:
            xp, gold = int(parts[1]), int(parts[2])
        except ValueError as exc:
            raise GameRuleError(f"Bonus line {line_number} needs whole-number XP and Gold.") from exc
        if xp < 0 or gold < 0 or not parts[0]:
            raise GameRuleError(f"Bonus line {line_number} is invalid.")
        item = {"title": parts[0], "xp": xp, "gold": gold}
        if parts[0] in existing_by_title:
            item["id"] = existing_by_title[parts[0]]["id"]
        result.append(item)
    return result


class NameSetupDialog(QDialog):
    def __init__(self, parent=None, current_name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Create your player profile")
        self.setMinimumWidth(390)
        layout = QVBoxLayout(self)
        heading = QLabel("WELCOME TO THE LEARNING GUILD")
        heading.setObjectName("pageTitle")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        note = QLabel("Choose the name shown on your player sheet. You can change it later.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.name_edit = QLineEdit(current_name)
        self.name_edit.setPlaceholderText("Player name")
        self.name_edit.setMaxLength(60)
        layout.addWidget(self.name_edit)
        buttons = _buttons(self, "Enter the guild")
        layout.addWidget(buttons)
        self.name_edit.returnPressed.connect(self.accept)

    @property
    def player_name(self) -> str:
        return self.name_edit.text().strip()

    def accept(self) -> None:
        if not self.player_name:
            QMessageBox.warning(self, "Name required", "Enter a player name to continue.")
            return
        super().accept()


class PathDialog(QDialog):
    def __init__(self, parent=None, item: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit learning path" if item else "Add learning path")
        self.setMinimumWidth(500)
        form = QFormLayout(self)
        self.name = QLineEdit(item.get("name", "") if item else "")
        self.status = QComboBox()
        for status in PATH_STATUSES:
            self.status.addItem(status.title(), status)
        if item:
            self.status.setCurrentIndex(max(0, self.status.findData(item.get("status"))))
        self.objective = QLineEdit(item.get("objective", "") if item else "")
        self.goal = QPlainTextEdit(item.get("goal", "") if item else "")
        self.goal.setMaximumHeight(110)
        form.addRow("Name", self.name)
        form.addRow("Status", self.status)
        form.addRow("Current objective", self.objective)
        form.addRow("Goal", self.goal)
        form.addRow(_buttons(self))

    def data(self) -> dict:
        return {
            "name": self.name.text(),
            "status": self.status.currentData(),
            "objective": self.objective.text(),
            "goal": self.goal.toPlainText(),
        }


class QuestDialog(QDialog):
    def __init__(self, paths: list[dict], parent=None, item: dict | None = None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Edit quest" if item else "Add quest")
        self.resize(600, 580)
        form = QFormLayout(self)
        self.path = QComboBox()
        for path in paths:
            if not path.get("archived") or (item and path["id"] == item.get("path_id")):
                self.path.addItem(path["name"], path["id"])
        self.title = QLineEdit(item.get("title", "") if item else "")
        self.stage = QLineEdit(item.get("stage", "") if item else "Stage 1 — Foundations")
        self.difficulty = QComboBox()
        for key, details in DIFFICULTIES.items():
            if key != "boss":
                self.difficulty.addItem(details["label"], key)
        self.xp = QSpinBox()
        self.xp.setRange(0, 100000)
        self.gold = QSpinBox()
        self.gold.setRange(0, 100000)
        self.definition = QPlainTextEdit(item.get("definition_of_done", "") if item else "")
        self.definition.setMaximumHeight(120)
        self.bonuses = QPlainTextEdit()
        self.bonuses.setPlaceholderText("Optional: one bonus per line\nRepeat without notes | 10 | 5")
        self.bonuses.setMaximumHeight(110)
        if item:
            self.path.setCurrentIndex(max(0, self.path.findData(item.get("path_id"))))
            self.difficulty.setCurrentIndex(max(0, self.difficulty.findData(item.get("difficulty"))))
            self.xp.setValue(item.get("xp", 0))
            self.gold.setValue(item.get("gold", 0))
            self.bonuses.setPlainText(
                "\n".join(f"{bonus['title']} | {bonus['xp']} | {bonus['gold']}" for bonus in item.get("bonuses", []))
            )
        else:
            self.xp.setValue(25)
            self.gold.setValue(10)
        form.addRow("Learning path", self.path)
        form.addRow("Title", self.title)
        form.addRow("Stage", self.stage)
        form.addRow("Difficulty", self.difficulty)
        reward_row = QHBoxLayout()
        reward_row.addWidget(QLabel("XP"))
        reward_row.addWidget(self.xp)
        reward_row.addWidget(QLabel("Gold"))
        reward_row.addWidget(self.gold)
        form.addRow("Base reward", reward_row)
        form.addRow("Definition of done", self.definition)
        form.addRow("Bonuses (title | XP | Gold)", self.bonuses)
        form.addRow(_buttons(self))

    def data(self) -> dict:
        return {
            "path_id": self.path.currentData(),
            "title": self.title.text(),
            "stage": self.stage.text(),
            "difficulty": self.difficulty.currentData(),
            "xp": self.xp.value(),
            "gold": self.gold.value(),
            "definition_of_done": self.definition.toPlainText(),
            "bonuses": _parse_bonuses(self.bonuses.toPlainText(), self.item.get("bonuses", []) if self.item else []),
        }


class QuestImportDialog(QDialog):
    """Copy an AI prompt, preview its JSON response, and import it safely."""

    def __init__(self, engine, parent=None, preferred_path_id: str | None = None):
        super().__init__(parent)
        self.engine = engine
        self._preview_quests: list[dict] | None = None
        self.imported_count = 0
        self.setWindowTitle("Generate & Import Quests")
        self.resize(780, 680)
        self.setMinimumSize(680, 600)

        outer = QVBoxLayout(self)
        heading = QLabel("GENERATE QUESTS WITH YOUR AI")
        heading.setObjectName("sectionTitle")
        outer.addWidget(heading)
        note = QLabel(
            "LearnTrack does not contact an AI. Copy the prompt into your preferred AI, then paste its JSON response below."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        outer.addWidget(note)

        inputs = QFormLayout()
        self.path = QComboBox()
        available_paths = [path for path in engine.state["paths"] if not path.get("archived")]
        for path in available_paths:
            self.path.addItem(path["name"], path["id"])
        selected_path_id = preferred_path_id
        if self.path.findData(selected_path_id) < 0:
            selected_path_id = next((path["id"] for path in available_paths if path.get("status") == "active"), None)
        if selected_path_id is not None:
            self.path.setCurrentIndex(max(0, self.path.findData(selected_path_id)))
        self.topic = QLineEdit()
        self.topic.setPlaceholderText("For example: Python data structures")
        inputs.addRow("Learning path", self.path)
        inputs.addRow("Learning topic", self.topic)
        outer.addLayout(inputs)

        prompt_label = QLabel("1. COPY THIS PROMPT")
        prompt_label.setObjectName("sectionTitle")
        outer.addWidget(prompt_label)
        self.prompt = QPlainTextEdit()
        self.prompt.setReadOnly(True)
        self.prompt.setMaximumHeight(205)
        outer.addWidget(self.prompt)
        self.copy_button = QPushButton("Copy AI prompt")
        self.copy_button.clicked.connect(self.copy_prompt)
        outer.addWidget(self.copy_button)

        response_label = QLabel("2. PASTE THE AI RESPONSE")
        response_label.setObjectName("sectionTitle")
        outer.addWidget(response_label)
        self.response = QPlainTextEdit()
        self.response.setPlaceholderText('Paste the JSON object containing the "quests" list here…')
        self.response.setMinimumHeight(120)
        outer.addWidget(self.response, 1)

        preview_row = QHBoxLayout()
        self.preview_button = QPushButton("Preview quests")
        self.preview_button.setProperty("accent", True)
        self.preview_button.clicked.connect(self.preview_import)
        self.preview_summary = QLabel("No batch previewed yet")
        self.preview_summary.setObjectName("muted")
        preview_row.addWidget(self.preview_button)
        preview_row.addWidget(self.preview_summary)
        preview_row.addStretch()
        outer.addLayout(preview_row)

        self.preview_table = QTableWidget(0, 4)
        self.preview_table.setHorizontalHeaderLabels(["Stage", "Quest", "Difficulty", "Reward"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.verticalHeader().hide()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setMaximumHeight(180)
        outer.addWidget(self.preview_table)

        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.import_button = actions.addButton("Import quests", QDialogButtonBox.ButtonRole.AcceptRole)
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_preview)
        actions.rejected.connect(self.reject)
        outer.addWidget(actions)

        self.topic.textChanged.connect(self._update_prompt)
        self.path.currentIndexChanged.connect(self._path_changed)
        self.response.textChanged.connect(self._invalidate_preview)
        self._update_prompt()

    @property
    def custom_rewards_enabled(self) -> bool:
        return self.engine.state["profile"].get("allow_custom_import_rewards", False)

    def _update_prompt(self) -> None:
        self.prompt.setPlainText(
            build_quest_prompt(self.topic.text(), self.path.currentText(), self.custom_rewards_enabled)
        )

    def _path_changed(self) -> None:
        self._update_prompt()
        self._invalidate_preview()

    def _invalidate_preview(self) -> None:
        self._preview_quests = None
        self.import_button.setEnabled(False)
        self.preview_summary.setText("No batch previewed yet")
        self.preview_table.setRowCount(0)

    def copy_prompt(self) -> None:
        if not self.topic.text().strip():
            QMessageBox.warning(self, "Learning topic required", "Enter the topic you want the AI to build quests for.")
            self.topic.setFocus()
            return
        QApplication.clipboard().setText(self.prompt.toPlainText())
        self.copy_button.setText("Copied")

    def preview_import(self) -> None:
        if self.path.currentData() is None:
            QMessageBox.warning(self, "Learning path required", "Create or select a non-archived learning path first.")
            return
        if not self.topic.text().strip():
            QMessageBox.warning(self, "Learning topic required", "Enter the topic used to generate this quest batch.")
            self.topic.setFocus()
            return
        try:
            raw_quests = parse_quest_batch(self.response.toPlainText())
            prepared = self.engine.prepare_quest_import(self.path.currentData(), raw_quests)
        except GameRuleError as exc:
            QMessageBox.warning(self, "Cannot preview quests", str(exc))
            return

        self._preview_quests = raw_quests
        self.preview_table.setRowCount(len(prepared))
        for row, quest in enumerate(prepared):
            values = (
                quest["stage"],
                quest["title"],
                quest["difficulty"].title(),
                f"{quest['xp']} XP / {quest['gold']} Gold",
            )
            for column, value in enumerate(values):
                self.preview_table.setItem(row, column, QTableWidgetItem(value))
        mode = "custom rewards" if self.custom_rewards_enabled else "balanced rewards"
        self.preview_summary.setText(f"{len(prepared)} quests ready · {mode}")
        self.import_button.setEnabled(True)

    def import_preview(self) -> None:
        if self._preview_quests is None:
            return
        count = len(self._preview_quests)
        answer = QMessageBox.question(
            self,
            "Import quest batch?",
            f"Add {count} quests to “{self.path.currentText()}”?\n\nAll quests will begin as Available.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            imported = self.engine.import_quests(self.path.currentData(), self._preview_quests)
        except GameRuleError as exc:
            QMessageBox.warning(self, "Cannot import quests", str(exc))
            self._invalidate_preview()
            return
        self.imported_count = len(imported)
        super().accept()


class BossImportDialog(QDialog):
    """Copy an AI prompt, preview its boss JSON response, and import it safely."""

    def __init__(self, engine, parent=None, preferred_path_id: str | None = None):
        super().__init__(parent)
        self.engine = engine
        self._preview_bosses: list[dict] | None = None
        self.imported_count = 0
        self.setWindowTitle("Generate & Import Bosses")
        self.resize(780, 680)
        self.setMinimumSize(680, 600)

        outer = QVBoxLayout(self)
        heading = QLabel("GENERATE BOSSES WITH YOUR AI")
        heading.setObjectName("sectionTitle")
        outer.addWidget(heading)
        note = QLabel(
            "LearnTrack does not contact an AI. Copy the prompt into your preferred AI, then paste its JSON response below."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        outer.addWidget(note)

        inputs = QFormLayout()
        self.path = QComboBox()
        available_paths = [path for path in engine.state["paths"] if not path.get("archived")]
        for path in available_paths:
            self.path.addItem(path["name"], path["id"])
        selected_path_id = preferred_path_id
        if self.path.findData(selected_path_id) < 0:
            selected_path_id = next((path["id"] for path in available_paths if path.get("status") == "active"), None)
        if selected_path_id is not None:
            self.path.setCurrentIndex(max(0, self.path.findData(selected_path_id)))
        self.topic = QLineEdit()
        self.topic.setPlaceholderText("For example: Build and test a complete FastAPI service")
        inputs.addRow("Learning path", self.path)
        inputs.addRow("Boss topic", self.topic)
        outer.addLayout(inputs)

        prompt_label = QLabel("1. COPY THIS PROMPT")
        prompt_label.setObjectName("sectionTitle")
        outer.addWidget(prompt_label)
        self.prompt = QPlainTextEdit()
        self.prompt.setReadOnly(True)
        self.prompt.setMaximumHeight(205)
        outer.addWidget(self.prompt)
        self.copy_button = QPushButton("Copy AI prompt")
        self.copy_button.clicked.connect(self.copy_prompt)
        outer.addWidget(self.copy_button)

        response_label = QLabel("2. PASTE THE AI RESPONSE")
        response_label.setObjectName("sectionTitle")
        outer.addWidget(response_label)
        self.response = QPlainTextEdit()
        self.response.setPlaceholderText('Paste the JSON object containing the "bosses" list here…')
        self.response.setMinimumHeight(120)
        outer.addWidget(self.response, 1)

        preview_row = QHBoxLayout()
        self.preview_button = QPushButton("Preview bosses")
        self.preview_button.setProperty("accent", True)
        self.preview_button.clicked.connect(self.preview_import)
        self.preview_summary = QLabel("No batch previewed yet")
        self.preview_summary.setObjectName("muted")
        preview_row.addWidget(self.preview_button)
        preview_row.addWidget(self.preview_summary)
        preview_row.addStretch()
        outer.addLayout(preview_row)

        self.preview_table = QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels(["Boss", "Requirements", "Reward"])
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.verticalHeader().hide()
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setMaximumHeight(180)
        outer.addWidget(self.preview_table)

        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.import_button = actions.addButton("Import bosses", QDialogButtonBox.ButtonRole.AcceptRole)
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.import_preview)
        actions.rejected.connect(self.reject)
        outer.addWidget(actions)

        self.topic.textChanged.connect(self._update_prompt)
        self.path.currentIndexChanged.connect(self._path_changed)
        self.response.textChanged.connect(self._invalidate_preview)
        self._update_prompt()

    @property
    def custom_rewards_enabled(self) -> bool:
        return self.engine.state["profile"].get("allow_custom_import_rewards", False)

    def _update_prompt(self) -> None:
        self.prompt.setPlainText(
            build_boss_prompt(self.topic.text(), self.path.currentText(), self.custom_rewards_enabled)
        )

    def _path_changed(self) -> None:
        self._update_prompt()
        self._invalidate_preview()

    def _invalidate_preview(self) -> None:
        self._preview_bosses = None
        self.import_button.setEnabled(False)
        self.preview_summary.setText("No batch previewed yet")
        self.preview_table.setRowCount(0)

    def copy_prompt(self) -> None:
        if not self.topic.text().strip():
            QMessageBox.warning(self, "Boss topic required", "Enter the topic you want the AI to build bosses for.")
            self.topic.setFocus()
            return
        QApplication.clipboard().setText(self.prompt.toPlainText())
        self.copy_button.setText("Copied")

    def preview_import(self) -> None:
        if self.path.currentData() is None:
            QMessageBox.warning(self, "Learning path required", "Create or select a non-archived learning path first.")
            return
        if not self.topic.text().strip():
            QMessageBox.warning(self, "Boss topic required", "Enter the topic used to generate this boss batch.")
            self.topic.setFocus()
            return
        try:
            raw_bosses = parse_boss_batch(self.response.toPlainText())
            prepared = self.engine.prepare_boss_import(self.path.currentData(), raw_bosses)
        except GameRuleError as exc:
            QMessageBox.warning(self, "Cannot preview bosses", str(exc))
            return

        self._preview_bosses = raw_bosses
        self.preview_table.setRowCount(len(prepared))
        for row, boss in enumerate(prepared):
            required_count = sum(requirement["mandatory"] for requirement in boss["requirements"])
            values = (
                boss["title"],
                f"{required_count} mandatory / {len(boss['requirements'])} total",
                f"{boss['xp']} XP / {boss['gold']} Gold",
            )
            for column, value in enumerate(values):
                self.preview_table.setItem(row, column, QTableWidgetItem(value))
        mode = "custom rewards" if self.custom_rewards_enabled else "standard boss rewards"
        self.preview_summary.setText(f"{len(prepared)} bosses ready · {mode}")
        self.import_button.setEnabled(True)

    def import_preview(self) -> None:
        if self._preview_bosses is None:
            return
        count = len(self._preview_bosses)
        answer = QMessageBox.question(
            self,
            "Import boss batch?",
            f"Add {count} bosses to “{self.path.currentText()}”?\n\nAll bosses will begin as Available.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            imported = self.engine.import_bosses(self.path.currentData(), self._preview_bosses)
        except GameRuleError as exc:
            QMessageBox.warning(self, "Cannot import bosses", str(exc))
            self._invalidate_preview()
            return
        self.imported_count = len(imported)
        super().accept()


class TimerPresetsDialog(QDialog):
    """Edit the three focus shortcuts and one break shortcut."""

    def __init__(self, focus_minutes: tuple[int, int, int], break_minutes: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timer Presets")
        self.setMinimumWidth(390)
        form = QFormLayout(self)
        note = QLabel("Choose the minute values shown beside the timer. You can still click the timer itself for a custom duration.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        form.addRow(note)
        self.focus_inputs = []
        for index, minutes in enumerate(focus_minutes, start=1):
            value = QSpinBox()
            value.setRange(1, 1440)
            value.setSuffix(" min")
            value.setValue(minutes)
            form.addRow(f"Focus preset {index}", value)
            self.focus_inputs.append(value)
        self.break_input = QSpinBox()
        self.break_input.setRange(1, 1440)
        self.break_input.setSuffix(" min")
        self.break_input.setValue(break_minutes)
        form.addRow("Break preset", self.break_input)
        form.addRow(_buttons(self, "Save presets"))

    def data(self) -> tuple[tuple[int, int, int], int]:
        focus = tuple(value.value() for value in self.focus_inputs)
        return focus, self.break_input.value()


class BossDialog(QDialog):
    def __init__(self, paths: list[dict], parent=None, item: dict | None = None):
        super().__init__(parent)
        self.item = item
        self.setWindowTitle("Edit boss" if item else "Add boss")
        self.resize(620, 650)
        form = QFormLayout(self)
        self.path = QComboBox()
        for path in paths:
            if not path.get("archived") or (item and path["id"] == item.get("path_id")):
                self.path.addItem(path["name"], path["id"])
        self.title = QLineEdit(item.get("title", "") if item else "")
        self.victory = QPlainTextEdit(item.get("victory_condition", "") if item else "")
        self.victory.setMaximumHeight(100)
        self.requirements = QPlainTextEdit()
        self.requirements.setPlaceholderText("One mandatory requirement per line. Prefix optional ones with [optional].")
        self.bonuses = QPlainTextEdit()
        self.bonuses.setPlaceholderText("Optional: title | XP | Gold")
        self.bonuses.setMaximumHeight(100)
        self.xp = QSpinBox()
        self.xp.setRange(0, 100000)
        self.gold = QSpinBox()
        self.gold.setRange(0, 100000)
        if item:
            self.path.setCurrentIndex(max(0, self.path.findData(item.get("path_id"))))
            self.requirements.setPlainText(
                "\n".join(
                    ("" if requirement.get("mandatory", True) else "[optional] ") + requirement["text"]
                    for requirement in item.get("requirements", [])
                )
            )
            self.bonuses.setPlainText(
                "\n".join(f"{bonus['title']} | {bonus['xp']} | {bonus['gold']}" for bonus in item.get("bonuses", []))
            )
            self.xp.setValue(item.get("xp", 0))
            self.gold.setValue(item.get("gold", 0))
        else:
            self.xp.setValue(150)
            self.gold.setValue(50)
        form.addRow("Learning path", self.path)
        form.addRow("Title", self.title)
        form.addRow("Victory condition", self.victory)
        form.addRow("Requirements", self.requirements)
        reward_row = QHBoxLayout()
        reward_row.addWidget(QLabel("XP"))
        reward_row.addWidget(self.xp)
        reward_row.addWidget(QLabel("Gold"))
        reward_row.addWidget(self.gold)
        form.addRow("Base reward", reward_row)
        form.addRow("Bonuses (title | XP | Gold)", self.bonuses)
        form.addRow(_buttons(self))

    def data(self) -> dict:
        existing = {item["text"]: item for item in self.item.get("requirements", [])} if self.item else {}
        requirements = []
        for raw in self.requirements.toPlainText().splitlines():
            text = raw.strip()
            if not text:
                continue
            mandatory = True
            if text.lower().startswith("[optional]"):
                mandatory = False
                text = text[len("[optional]") :].strip()
            requirement = {"text": text, "mandatory": mandatory}
            if text in existing:
                requirement["id"] = existing[text]["id"]
            requirements.append(requirement)
        return {
            "path_id": self.path.currentData(),
            "title": self.title.text(),
            "victory_condition": self.victory.toPlainText(),
            "requirements": requirements,
            "xp": self.xp.value(),
            "gold": self.gold.value(),
            "bonuses": _parse_bonuses(self.bonuses.toPlainText(), self.item.get("bonuses", []) if self.item else []),
        }


class RewardDialog(QDialog):
    def __init__(self, parent=None, item: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit shop reward" if item else "Add shop reward")
        form = QFormLayout(self)
        self.title = QLineEdit(item.get("title", "") if item else "")
        self.cost = QSpinBox()
        self.cost.setRange(0, 1000000)
        self.cost.setValue(item.get("cost", 30) if item else 30)
        self.level = QSpinBox()
        self.level.setRange(1, 10)
        self.level.setValue(item.get("level_required", 1) if item else 1)
        form.addRow("Reward", self.title)
        form.addRow("Gold cost", self.cost)
        form.addRow("Level required", self.level)
        form.addRow(_buttons(self))

    def data(self) -> dict:
        return {"title": self.title.text(), "cost": self.cost.value(), "level_required": self.level.value()}


class CompletionDialog(QDialog):
    def __init__(self, item: dict, parent=None, boss: bool = False, replay: bool = False):
        super().__init__(parent)
        self.setWindowTitle("Complete quest replay" if replay else "Claim boss victory" if boss else "Claim quest completion")
        self.resize(560, 520 if boss else 400)
        layout = QVBoxLayout(self)
        title = QLabel(item["title"])
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        if replay:
            replay_note = QLabel("This is a replay. Your evidence will be saved, but it grants 0 XP and 0 Gold.")
            replay_note.setObjectName("muted")
            replay_note.setWordWrap(True)
            layout.addWidget(replay_note)
        self.requirement_checks: list[tuple[str, QCheckBox]] = []
        if boss:
            label = QLabel("Victory requirements")
            label.setObjectName("muted")
            layout.addWidget(label)
            for requirement in item.get("requirements", []):
                suffix = "" if requirement.get("mandatory", True) else " (optional)"
                check = QCheckBox(requirement["text"] + suffix)
                layout.addWidget(check)
                self.requirement_checks.append((requirement["id"], check))
        evidence_label = QLabel("Evidence of learning or the working result")
        evidence_label.setObjectName("muted")
        layout.addWidget(evidence_label)
        self.evidence = QPlainTextEdit()
        self.evidence.setPlaceholderText("Describe what you completed, tested, explained, or built…")
        layout.addWidget(self.evidence)
        self.bonus_checks: list[tuple[str, QCheckBox]] = []
        if item.get("bonuses") and not replay:
            bonus_label = QLabel("Optional objectives completed")
            bonus_label.setObjectName("muted")
            layout.addWidget(bonus_label)
            for bonus in item["bonuses"]:
                check = QCheckBox(f"{bonus['title']}  (+{bonus['xp']} XP, +{bonus['gold']} Gold)")
                layout.addWidget(check)
                self.bonus_checks.append((bonus["id"], check))
        buttons = _buttons(self, "Review replay" if replay else "Review claim")
        layout.addWidget(buttons)

    @property
    def evidence_text(self) -> str:
        return self.evidence.toPlainText().strip()

    @property
    def checked_requirements(self) -> list[str]:
        return [item_id for item_id, check in self.requirement_checks if check.isChecked()]

    @property
    def selected_bonuses(self) -> list[str]:
        return [item_id for item_id, check in self.bonus_checks if check.isChecked()]

    def accept(self) -> None:
        if not self.evidence_text:
            QMessageBox.warning(self, "Evidence required", "Add non-empty evidence before reviewing the claim.")
            return
        super().accept()
