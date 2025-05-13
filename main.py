import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QLineEdit, QSizePolicy
)
from onscreen_keyboard import OnScreenKeyboard

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Keyboard Test App")

        layout = QVBoxLayout()

        # Input 1
        self.input1 = QLineEdit()
        self.input1.setPlaceholderText("First input field")
        self.input1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Input 2
        self.input2 = QLineEdit()
        self.input2.setPlaceholderText("Second input field")
        self.input2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Add to layout
        layout.addWidget(self.input1)
        layout.addWidget(self.input2)
        layout.addStretch()  # pushes inputs to top

        # Set layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Fullscreen
        self.showFullScreen()

        # Keyboard
        self.keyboard = OnScreenKeyboard(self)
        self.position_keyboard_bottom()

    def position_keyboard_bottom(self):
        screen = QApplication.primaryScreen().geometry()
        height = 400
        self.keyboard.setFixedWidth(screen.width())
        self.keyboard.setFixedHeight(height)
        self.keyboard.move(0, screen.height() - height)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    sys.exit(app.exec())
