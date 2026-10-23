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
    def __init__(self, appName, appRect, whenDone):
        super().__init__()
        self.whenDone = whenDone
        self.secondsLeft = COUNTDOWN
        self.shakeStep = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(STYLE)
        self.setGeometry(QApplication.primaryScreen().geometry())

        self.title = QLabel("Why are you opening " + appName + "?")
        self.title.setWordWrap(True)
        self.hint = QLabel("Pick a reason to use " + appName, objectName="Hint")

        self.reasonButtons = QWidget()
        reasonLayout = QVBoxLayout(self.reasonButtons)
        reasonLayout.setContentsMargins(0, 0, 0, 0)
        for reason in REASONS:
            button = QPushButton(reason)
            button.clicked.connect(lambda checked=False, r=reason: self.pickReason(r))
            reasonLayout.addWidget(button)

        self.otherBox = QLineEdit()
        self.otherBox.setPlaceholderText("Type your reason and press Enter")
        self.otherBox.returnPressed.connect(self.otherTyped)
        self.otherBox.hide()

        self.openButton = QPushButton("Open anyway")
        self.openButton.clicked.connect(self.openAnyway)
        self.openButton.setEnabled(False)
        self.openButton.hide()

        backButton = QPushButton("Back to work")
        backButton.clicked.connect(self.backToWork)

        bottomRow = QHBoxLayout()
        bottomRow.addWidget(backButton)
        bottomRow.addWidget(self.openButton)

        self.box = QFrame(self, objectName="Box")
        self.box.setFixedWidth(300)
        boxLayout = QVBoxLayout(self.box)
        boxLayout.setContentsMargins(16, 16, 16, 16)
        boxLayout.addWidget(self.title)
        boxLayout.addWidget(self.hint)
        boxLayout.addWidget(self.reasonButtons)
        boxLayout.addWidget(self.otherBox)
        boxLayout.addLayout(bottomRow)
        self.box.adjustSize()

        self.appRect = appRect
        self.placeBox()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.countDown)
        self.shakeTimer = QTimer(self)
        self.shakeTimer.timeout.connect(self.shakeMove)

    def placeBox(self):
        screen = self.geometry()
        appRect = self.appRect
        if appRect is None:
            centerX = screen.width() // 2
            centerY = screen.height() // 2
        else:
            x, y, width, height = appRect
            centerX = x - screen.x() + width // 2
            centerY = y - screen.y() + height // 2
        left = centerX - self.box.width() // 2
        top = centerY - self.box.height() // 2
        # keep the box 10px inside the screen
        if left > screen.width() - self.box.width() - 10:
            left = screen.width() - self.box.width() - 10
        if left < 10:
            left = 10
        if top > screen.height() - self.box.height() - 10:
            top = screen.height() - self.box.height() - 10
        if top < 10:
            top = 10
        self.boxX = left
        self.box.move(left, top)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 90))

    def mousePressEvent(self, event):
        if not self.box.geometry().contains(event.position().toPoint()):
            self.shakeStep = 0
            self.shakeTimer.start(30)

    def shakeMove(self):
        self.box.move(self.boxX + SHAKE[self.shakeStep], self.box.y())
        self.shakeStep = self.shakeStep + 1
        if self.shakeStep >= len(SHAKE):
            self.shakeTimer.stop()

    def popUp(self):
        self.show()
        try:
            get_backend().float_above_everything(int(self.winId()))
        except Exception:
            pass
        self.raise_()
        self.activateWindow()

    def pickReason(self, reason):
        if reason == "Emergency":
            self.finishWithChoice("emergency")
        elif reason == "Other":
            self.otherBox.show()
            self.otherBox.setFocus()
            self.box.adjustSize()
            self.placeBox()
        else:
            self.startCountdown()

    def otherTyped(self):
        if self.otherBox.text().strip() != "":
            self.startCountdown()

    def startCountdown(self):
        self.reasonButtons.hide()
        self.otherBox.hide()
        self.hint.hide()
        self.title.setText("Wait " + str(self.secondsLeft) + " seconds")
        self.openButton.show()
        self.box.adjustSize()
        self.placeBox()
        self.timer.start(1000)

    def countDown(self):
        self.secondsLeft = self.secondsLeft - 1
        self.title.setText("Wait " + str(self.secondsLeft) + " seconds")
        if self.secondsLeft <= 0:
            self.timer.stop()
            self.title.setText("You can open it now")
            self.openButton.setEnabled(True)

    def openAnyway(self):
        self.finishWithChoice("open")

    def backToWork(self):
        self.finishWithChoice("back")

    def finishWithChoice(self, choice):
        self.timer.stop()
        self.hide()
        self.whenDone(choice)

    def closeEvent(self, event):
        event.ignore()
