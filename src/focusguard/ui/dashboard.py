"""Stats, streaks and goals. Currently an empty white window."""

"""using q widget to make the window. for mac this appears in the top corner"""
from PySide6.QtWidgets import QWidget


class Dashboard(QWidget):
    def __init__(self) -> None:
        
        super().__init__()
        self.setWindowTitle("FocusGuard")
        self.setStyleSheet("background: white;")
        self.resize(480, 360)