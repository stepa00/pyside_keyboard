from PySide6.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QApplication, QLineEdit,
    QVBoxLayout, QDialog, QSizePolicy, QStyleFactory
)
from PySide6.QtCore import Qt, QTimer, QObject, QEvent, QPoint
from PySide6.QtGui import QCursor


class OnScreenKeyboard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("On-Screen Keyboard")
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyle(QStyleFactory.create("Fusion"))

        self.shifted = False
        self.last_input_widget = None
        self.hide_requested = False

        self.init_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_focus)
        self.timer.start(300)

        self.done_cooldown_timer = QTimer(self)
        self.done_cooldown_timer.setSingleShot(True)
        self.done_cooldown_timer.timeout.connect(self.reset_hide_flag)

        QApplication.instance().installEventFilter(self)

    def init_ui(self):
        layout = QVBoxLayout(self)
        grid = QGridLayout()

        self.keys_layout = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "Backspace"],
            ["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
            ["a", "s", "d", "f", "g", "h", "j", "k", "l"],
            ["Shift", "z", "x", "c", "v", "b", "n", "m", ",", ".", "Enter"],
            ["Space", "Done"]
        ]

        self.buttons = []
        for row_idx, row in enumerate(self.keys_layout):
            for col_idx, key in enumerate(row):
                btn = QPushButton(key)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                btn.setMinimumHeight(50)
                btn.setStyleSheet("font-size: 18px;")
                btn.clicked.connect(lambda _, k=key: self.key_pressed(k))
                self.buttons.append(btn)

                if key == "Space":
                    grid.addWidget(btn, row_idx, 0, 1, 9)
                elif key == "Done":
                    grid.addWidget(btn, row_idx, 9, 1, 2)
                else:
                    grid.addWidget(btn, row_idx, col_idx)

        layout.addLayout(grid)
        self.setLayout(layout)

    def resolve_input_target(self, widget):
        return widget

    def is_text_input(self, widget):
        widget = self.resolve_input_target(widget)
        return hasattr(widget, 'insert') and callable(widget.insert)

    def key_pressed(self, key):
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
            char = key.upper() if self.shifted else key.lower()
            widget.insert(char)

    def update_keys(self):
        for btn in self.buttons:
            key = btn.text()
            if key.isalpha():
                btn.setText(key.upper() if self.shifted else key.lower())

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
            return super().eventFilter(obj, event)

        if event.type() == QEvent.MouseButtonPress:
            widget = QApplication.widgetAt(QCursor.pos())
            if not self.is_text_input(widget) and not self.isAncestorOf(widget):
                self.hide_requested = True
                self.last_input_widget = None
                self.hide()
                self.done_cooldown_timer.start(500)
        elif event.type() == QEvent.FocusIn:
            if self.is_text_input(obj):
                self.last_input_widget = obj
        return super().eventFilter(obj, event)
