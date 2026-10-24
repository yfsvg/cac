from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from focusguard.platform import get_backend
from focusguard.ui.theme import applyTheme

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
    background-color: @surfaceContainerHigh;
    border: none;
    border-radius: 28px;
}
QLabel { color: @onSurface; font-size: 22px; font-weight: 600; }
QLabel#Hint { color: @onSurfaceVariant; font-size: 14px; font-weight: 400; }
QPushButton {
    color: @onSecondaryContainer;
    font-size: 14px;
    font-weight: 500;
    text-align: left;
    padding: 10px 16px;
    background-color: @secondaryContainer;
    border: none;
    border-radius: 16px;
}
QPushButton:hover { background-color: @primaryContainer; color: @onPrimaryContainer; }
QPushButton#Emergency { background-color: @errorContainer; color: @onErrorContainer; }
QPushButton#BackButton {
    text-align: center;
    background-color: @primary;
    color: @onPrimary;
    font-weight: 600;
}
QPushButton#BackButton:hover { background-color: @primaryHover; color: @onPrimary; }
QPushButton#OpenButton { text-align: center; background-color: @tertiaryContainer; color: @onTertiaryContainer; }
QPushButton#OpenButton:disabled { background-color: @surfaceContainerHighest; color: @outline; }
QPushButton:disabled { background-color: @surfaceContainerHighest; color: @outline; }
QProgressBar {
    background-color: @surfaceContainerHighest;
    border: none;
    border-radius: 3px;
}
QProgressBar::chunk { background-color: @primary; border-radius: 3px; }
QLineEdit {
    color: @onSurface;
    font-size: 14px;
    padding: 10px 14px;
    background-color: @surfaceContainerHighest;
    border: none;
    border-bottom: 2px solid @primary;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
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
        self.setStyleSheet(applyTheme(STYLE))
        self.setGeometry(QApplication.primaryScreen().geometry())

        self.title = QLabel("Why are you opening " + appName + "?")
        self.title.setWordWrap(True)
        self.hint = QLabel("Pick a reason to use " + appName, objectName="Hint")

        self.reasonButtons = QWidget()
        reasonLayout = QVBoxLayout(self.reasonButtons)
        reasonLayout.setContentsMargins(0, 0, 0, 0)
        for reason in REASONS:
            button = QPushButton(reason, cursor=Qt.CursorShape.PointingHandCursor)
            if reason == "Emergency":
                button.setObjectName("Emergency")
            button.clicked.connect(lambda checked=False, r=reason: self.pickReason(r))
            reasonLayout.addWidget(button)

        self.otherBox = QLineEdit()
        self.otherBox.setPlaceholderText("Type your reason and press Enter")
        self.otherBox.returnPressed.connect(self.otherTyped)
        self.otherBox.hide()

        self.openButton = QPushButton("Open anyway", objectName="OpenButton")
        self.openButton.clicked.connect(self.openAnyway)
        self.openButton.setEnabled(False)
        self.openButton.hide()

        backButton = QPushButton("Back to work", objectName="BackButton", cursor=Qt.CursorShape.PointingHandCursor)
        backButton.clicked.connect(self.backToWork)

        bottomRow = QHBoxLayout()
        bottomRow.addWidget(backButton)
        bottomRow.addWidget(self.openButton)

        self.box = QFrame(self, objectName="Box")
        self.box.setFixedWidth(340)
        boxLayout = QVBoxLayout(self.box)
        boxLayout.setContentsMargins(24, 24, 24, 24)
        boxLayout.setSpacing(12)
        boxLayout.addWidget(self.title)
        boxLayout.addWidget(self.hint)
        boxLayout.addWidget(self.reasonButtons)
        boxLayout.addWidget(self.otherBox)
        boxLayout.addLayout(bottomRow)
        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, COUNTDOWN * 10)
        self.progressBar.setValue(0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        self.progressBar.hide()
        boxLayout.addWidget(self.progressBar)
        self.box.adjustSize()

        self.appRect = appRect
        self.placeBox()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.countDown)
        self.fillTimer = QTimer(self)
        self.fillTimer.timeout.connect(self.fillOpenButton)
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
        painter.fillRect(self.rect(), QColor(29, 27, 32, 140))  # M3 scrim

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
        self.progressBar.show()
        self.box.adjustSize()
        self.placeBox()
        self.timer.start(1000)
        self.fillStep = 0
        self.fillTimer.start(100)

    def fillOpenButton(self):
        self.fillStep = self.fillStep + 1
        self.progressBar.setValue(self.fillStep)
        if self.fillStep >= COUNTDOWN * 10:
            self.fillTimer.stop()

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
        self.fillTimer.stop()
        self.hide()
        self.whenDone(choice)

    def closeEvent(self, event):
        event.ignore()
