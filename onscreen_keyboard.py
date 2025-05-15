from functools import partial

from PySide6.QtCore import Qt, QTimer, QObject, QEvent
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QApplication, QVBoxLayout, QDialog,
    QSizePolicy, QStyleFactory, QHBoxLayout
)


class OnScreenKeyboard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("On-Screen Keyboard")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyle(QStyleFactory.create("Fusion"))

        self.shifted = False
        self.symbol_mode = False
        self.language = "EN"
        self.language_switch_locked = False
        self.last_input_widget = None
        self.hide_requested = False

        self.layouts = {
            "EN": [
                ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
                ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
                ["Shift", "z", "x", "c", "v", "b", "n", "m", "Backspace"],
                ["Sym", "Lang", ",", "Space", ".", "Enter", "Done"]
            ],
            "RU": [
                ["й", "ц", "у", "к", "е", "н", "г", "ш", "щ", "з", "х", "ъ"],
                ["ф", "ы", "в", "а", "п", "р", "о", "л", "д", "ж", "э"],
                ["Shift", "я", "ч", "с", "м", "и", "т", "ь", "б", "ю", "Backspace"],
                ["Sym", "Lang", ",", "Space", ".", "Enter", "Done"]
            ]
        }

        self.symbol_layout = [
            ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")"],
            ["-", "_", "=", "+", "[", "]", "{", "}", "\\", "|"],
            ["Shift", ";", ":", "'", '"', "<", ">", "/", "?", "`", "~", "Backspace"],
            ["ABC", "Lang", ",", "Space", ".", "Enter", "Done"]
        ]

        self.numpad_layout = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
            ["0"]
        ]

        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_focus)
        self.timer.start(300)

        self.done_cooldown_timer = QTimer(self)
        self.done_cooldown_timer.setSingleShot(True)
        self.done_cooldown_timer.timeout.connect(self.reset_hide_flag)

        QApplication.instance().installEventFilter(self)

    def init_ui(self):
        self.layout = QHBoxLayout(self)
        self.letter_grid = QGridLayout()
        self.numpad_grid = QGridLayout()
        self.layout.addLayout(self.letter_grid, 3)
        self.layout.addLayout(self.numpad_grid, 1)
        self.setLayout(self.layout)
        self.build_keys()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

    def build_keys(self):
        self.clear_layout(self.letter_grid)
        self.clear_layout(self.numpad_grid)
        self.buttons = []

        layout = self.symbol_layout if self.symbol_mode else self.layouts[self.language]
        for row_idx, row in enumerate(layout):
            col_pos = 0
            for key in row:
                btn = QPushButton(key)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setMinimumHeight(50)
                btn.setStyleSheet("font-size: 18px;")
                btn.clicked.connect(partial(self.key_pressed, key))
                self.buttons.append(btn)
                span = 4 if key == "Space" else 1
                self.letter_grid.addWidget(btn, row_idx, col_pos, 1, span)
                col_pos += span

        for row_idx, row in enumerate(self.numpad_layout):
            for col_idx, key in enumerate(row):
                btn = QPushButton(key)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setMinimumHeight(50)
                btn.setStyleSheet("font-size: 18px;")
                btn.clicked.connect(partial(self.key_pressed, key))
                self.buttons.append(btn)
                self.numpad_grid.addWidget(btn, row_idx, col_idx)

        self.update_keys()


    def resolve_input_target(self, widget):
        return widget

    def is_text_input(self, widget):
        widget = self.resolve_input_target(widget)
        return hasattr(widget, 'insert') and callable(widget.insert)

    def key_pressed(self, key):
        if key == "Sym":
            self.symbol_mode = True
            self.shifted = False
            self.build_keys()
            return
        if key == "ABC":
            self.symbol_mode = False
            self.shifted = False
            self.build_keys()
            return
        if key == "Lang":
            self.language = "RU" if self.language == "EN" else "EN"
            self.build_keys()
            return

        if key == "Shift":
            self.shifted = not self.shifted
            self.update_keys()
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
            elif hasattr(widget, 'insert'):
                widget.insert("\n")

        elif key == "Space":
            widget.insert(" ")

        elif key == "Done":
            self.hide_requested = True
            if self.last_input_widget:
                self.last_input_widget.clearFocus()
            self.last_input_widget = None
            self.hide()
            self.done_cooldown_timer.start(500)

        else:
            char = key.upper() if self.shifted and not self.symbol_mode else key.lower()
            widget.insert(char)

    def update_keys(self):
        for btn in self.buttons:
            key = btn.text().replace("&&", "&")
            if key in ("Shift", "Space", "Sym", "ABC", "Lang", "Done", "Enter", "Backspace"):
                continue
            label = key.upper() if self.shifted and not self.symbol_mode else key.lower()
            btn.setText("&&" if label == "&" else label)

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

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
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
