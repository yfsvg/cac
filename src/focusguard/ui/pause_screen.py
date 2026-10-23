from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from focusguard.platform import get_backend

COUNTDOWN = 15

REASONS = [
    "Taking a short break",
    "Done with my work for now",
    "Need it for school",
    "Other",
    "Emergency",
]

SHAKE = [12, -12, 9, -9, 5, -5, 0]

STYLE = """
QFrame#Box {
    background-color: #1c1c1c;
    border: 1px solid rgba(255, 255, 255, 100);
    border-radius: 12px;
}
QLabel { color: white; font-size: 17px; }
QLabel#Hint { color: rgba(255, 255, 255, 150); font-size: 13px; }
QPushButton {
    color: white;
    font-size: 14px;
    text-align: left;
    padding: 8px 12px;
    background-color: #262626;
    border: 1px solid rgba(255, 255, 255, 60);
    border-radius: 8px;
}
QPushButton:hover { background-color: #333333; }
QPushButton:disabled { color: rgba(255, 255, 255, 80); }
QLineEdit {
    color: white;
    font-size: 14px;
    padding: 8px;
    background-color: #262626;
    border: 1px solid rgba(255, 255, 255, 60);
    border-radius: 8px;
}
"""


class PauseScreen(QWidget):
    def __init__(self, app_name, app_rect, when_done):
        super().__init__()
        self.when_done = when_done
        self.seconds_left = COUNTDOWN
        self.shake_step = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(STYLE)
        self.setGeometry(QApplication.primaryScreen().geometry())

        self.title = QLabel("Why are you opening " + app_name + "?")
        self.title.setWordWrap(True)
        self.hint = QLabel("Pick a reason to use " + app_name, objectName="Hint")

        self.reason_buttons = QWidget()
        reason_layout = QVBoxLayout(self.reason_buttons)
        reason_layout.setContentsMargins(0, 0, 0, 0)
        for reason in REASONS:
            button = QPushButton(reason)
            button.clicked.connect(lambda checked=False, r=reason: self.pick(r))
            reason_layout.addWidget(button)

        self.other_box = QLineEdit()
        self.other_box.setPlaceholderText("Type your reason and press Enter")
        self.other_box.returnPressed.connect(self.other_typed)
        self.other_box.hide()

        self.open_button = QPushButton("Open anyway")
        self.open_button.clicked.connect(self.open_anyway)
        self.open_button.setEnabled(False)
        self.open_button.hide()

        back_button = QPushButton("Back to work")
        back_button.clicked.connect(self.back_to_work)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(back_button)
        bottom_row.addWidget(self.open_button)

        self.box = QFrame(self, objectName="Box")
        self.box.setFixedWidth(300)
        box_layout = QVBoxLayout(self.box)
        box_layout.setContentsMargins(16, 16, 16, 16)
        box_layout.addWidget(self.title)
        box_layout.addWidget(self.hint)
        box_layout.addWidget(self.reason_buttons)
        box_layout.addWidget(self.other_box)
        box_layout.addLayout(bottom_row)
        self.box.adjustSize()

        self.app_rect = app_rect
        self.place_box()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.count_down)
        self.shake_timer = QTimer(self)
        self.shake_timer.timeout.connect(self.shake_move)

    def place_box(self):
        screen = self.geometry()
        app_rect = self.app_rect
        if app_rect is None:
            center_x = screen.width() // 2
            center_y = screen.height() // 2
        else:
            x, y, width, height = app_rect
            center_x = x - screen.x() + width // 2
            center_y = y - screen.y() + height // 2
        left = center_x - self.box.width() // 2
        top = center_y - self.box.height() // 2
        left = max(10, min(left, screen.width() - self.box.width() - 10))
        top = max(10, min(top, screen.height() - self.box.height() - 10))
        self.box_x = left
        self.box.move(left, top)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

    def mousePressEvent(self, event):
        if not self.box.geometry().contains(event.position().toPoint()):
            self.shake_step = 0
            self.shake_timer.start(30)

    def shake_move(self):
        self.box.move(self.box_x + SHAKE[self.shake_step], self.box.y())
        self.shake_step = self.shake_step + 1
        if self.shake_step >= len(SHAKE):
            self.shake_timer.stop()

    def popup(self):
        self.show()
        try:
            get_backend().float_above_everything(int(self.winId()))
        except Exception:
            pass
        self.raise_()
        self.activateWindow()

    def pick(self, reason):
        if reason == "Emergency":
            self.finish("emergency")
        elif reason == "Other":
            self.other_box.show()
            self.other_box.setFocus()
            self.box.adjustSize()
            self.place_box()
        else:
            self.start_countdown()

    def other_typed(self):
        if self.other_box.text().strip() != "":
            self.start_countdown()

    def start_countdown(self):
        self.reason_buttons.hide()
        self.other_box.hide()
        self.hint.hide()
        self.title.setText("Wait " + str(self.seconds_left) + " seconds")
        self.open_button.show()
        self.box.adjustSize()
        self.place_box()
        self.timer.start(1000)

    def count_down(self):
        self.seconds_left = self.seconds_left - 1
        self.title.setText("Wait " + str(self.seconds_left) + " seconds")
        if self.seconds_left <= 0:
            self.timer.stop()
            self.title.setText("You can open it now")
            self.open_button.setEnabled(True)

    def open_anyway(self):
        self.finish("open")

    def back_to_work(self):
        self.finish("back")

    def finish(self, choice):
        self.timer.stop()
        self.hide()
        self.when_done(choice)

    def closeEvent(self, event):
        event.ignore()
