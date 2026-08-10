"""Main program loop."""

import sys

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


class SetupPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Setup page")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Setup"))
        self.setLayout(layout)


class SetupWizard(QWizard):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Setup")
        self.addPage(SetupPage())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("PyQt6 Quickstart")
        self.setGeometry(100, 100, 300, 150)  # x, y, width, height

        # 1. Create components
        self.label = QLabel("Click the button!", self)
        self.button = QPushButton("Click Me", self)

        # 2. Connect Signal to Slot (Event -> Action)
        self.button.clicked.connect(self.on_button_click)

        # 3. Arrange components in a Layout
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.button)

        # 4. Set container layout
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def on_button_click(self):
        self.label.setText("Button clicked!")


if __name__ == "__main__":

    # Get the config path from the cli args
    if len(sys.argv) <= 1:
        print("Usage: python image_tagger.py <config_path>")

    # Initialize app and pass command line args
    app = QApplication(sys.argv)

    wizard = SetupWizard()
    if wizard.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    # Run the main program
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def main():
    print("hello world")
