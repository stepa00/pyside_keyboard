from PySide6.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QApplication, QLineEdit,
    QVBoxLayout, QDialog, QSizePolicy, QStyleFactory
)
from PySide6.QtCore import Qt, QTimer, QObject, QEvent, QPoint
from PySide6.QtGui import QCursor
from functools import partial

class OnScreenKeyboard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("On-Screen Keyboard")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyle(QStyleFactory.create("Fusion"))

        self.shifted = False
        self.current_language = "EN"
        self.language_switch_locked = False
        self.last_input_widget = None
        self.hide_requested = False

        self.layouts = {
            "EN": [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "Backspace"],
                ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
                ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
                ["Shift", "z", "x", "c", "v", "b", "n", "m", ",", "."],
                ["EN", "Space", "Enter", "Done"]
            ],
            "RU": [
                ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "Backspace"],
                ["й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х"],
                ["ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э"],
                ["Shift", "я", "ч", "с", "м", "и", "т", "ь", "б", "ю", "ъ"],
                ["RU", "Space", "Enter", "Done"]
            ]
        }

        self.shift_maps = {
            "EN": {
                "1": "!", "2": "@", "3": "#", "4": "$", "5": "%",
                "6": "^", "7": "&", "8": "*", "9": "(", "0": ")",
                ",": "<", ".": ">"
            },
            "RU": {
                "1": "!", "2": "\"", "3": "№", "4": ";", "5": "%",
                "6": ":", "7": "?", "8": "*", "9": "(", "0": ")",
                ",": "<", ".": ">"
            }
        }

        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_focus)
        self.timer.start(300)

        self.done_cooldown_timer = QTimer(self)
        self.done_cooldown_timer.setSingleShot(True)
        self.done_cooldown_timer.timeout.connect(self.reset_hide_flag)

        self.lang_switch_timer = QTimer(self)
        self.lang_switch_timer.setSingleShot(True)
        self.lang_switch_timer.timeout.connect(self.unlock_language_switch)

        QApplication.instance().installEventFilter(self)

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.grid = QGridLayout()
        self.layout.addLayout(self.grid)
        self.setLayout(self.layout)
        self.build_keys()

    def build_keys(self):
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().setParent(None)
        self.buttons = []

        layout = self.layouts[self.current_language]

        for row_idx, row in enumerate(layout):
            col_pos = 0
            for key in row:
                if not isinstance(key, str):
                    continue
                btn = QPushButton(str(key))
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setMinimumHeight(50)
                btn.setStyleSheet("font-size: 18px;")
                btn.clicked.connect(partial(self.key_pressed, key))
                self.buttons.append(btn)

                span = 1
                if key == "Space":
                    span = 5
                elif key == "Done":
                    span = 2
                elif key == "Enter":
                    span = 2
                self.grid.addWidget(btn, row_idx, col_pos, 1, span)
                col_pos += span

        self.update_keys()

    def resolve_input_target(self, widget):
        return widget

    def is_text_input(self, widget):
        widget = self.resolve_input_target(widget)
        return hasattr(widget, 'insert') and callable(widget.insert)

    def key_pressed(self, key):
        if key in ("EN", "RU"):
            if not self.language_switch_locked:
                self.current_language = "RU" if self.current_language == "EN" else "EN"
                self.language_switch_locked = True
                self.build_keys()
                self.lang_switch_timer.start(200)
            return

        widget = self.resolve_input_target(self.last_input_widget)
        if not self.is_text_input(widget):
            return

        if key == "Backspace":
            if hasattr(widget, 'cursorPosition') and hasattr(widget, 'text'):
                cursor = widget.cursorPosition()
                text = widget.text()
                text = text[:max(cursor - 1, 0)] + text[cursor:]
                widget.setText(text)
                widget.setCursorPosition(max(cursor - 1, 0))

        elif key == "Enter":
            if hasattr(widget, 'returnPressed'):
                widget.returnPressed.emit()

        elif key == "Space":
            widget.insert(" ")

        elif key == "Shift":
            self.shifted = not self.shifted
            self.update_keys()

        elif key == "Done":
            self.hide_requested = True
            if self.last_input_widget:
                self.last_input_widget.clearFocus()
            self.last_input_widget = None
            self.hide()
            self.done_cooldown_timer.start(500)

        else:
            char = self.get_shifted_char(key)
            widget.insert(char)

    def get_shifted_char(self, key):
        functional_keys = ("Backspace", "Shift", "Enter", "Space", "Done", "EN", "RU")
        if key in functional_keys:
            return key

        shift_map = self.shift_maps.get(self.current_language, {})
        if self.shifted:
            return shift_map.get(key, key.upper())
        return key.lower()

    def update_keys(self):
        layout = self.layouts[self.current_language]
        for i, row in enumerate(layout):
            for j, key in enumerate(row):
                index = sum(len(r) for r in layout[:i]) + j
                if index >= len(self.buttons):
                    continue
                btn = self.buttons[index]
                label = self.get_shifted_char(key)
                if label == "&":
                    btn.setText("&&")
                else:
                    btn.setText(label)

    def check_focus(self):
        if self.hide_requested:
            return
        if self.last_input_widget and self.is_text_input(self.last_input_widget):
            if not self.isVisible():
                self.show()
        else:
            if self.isVisible():
                self.hide()

    def reset_hide_flag(self):
        self.hide_requested = False

    def unlock_language_switch(self):
        self.language_switch_locked = False

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if not isinstance(obj, QObject) or not isinstance(event, QEvent):
            return False

        if self.hide_requested:
            return False

        if event.type() == QEvent.MouseButtonPress:
            widget = QApplication.widgetAt(QCursor.pos())
            if not self.is_text_input(widget) and not self.isAncestorOf(widget):
                self.hide_requested = True
                self.last_input_widget = None
                self.hide()
                self.done_cooldown_timer.start(500)

        elif event.type() == QEvent.FocusIn:
            if isinstance(obj, QWidget) and self.is_text_input(obj):
                self.last_input_widget = obj

        return QDialog.eventFilter(self, obj, event)
