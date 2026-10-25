from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from arete.core import session
from arete.core.debug_mode import isDebugMode
from arete.platform import get_backend
from arete.ui import animations
from arete.ui.pause_screen import BADGE_MARGIN, BADGE_STYLE, STYLE
from arete.ui.theme import applyTheme

PROMPT_STYLE = """
QSlider::groove:horizontal { height: 6px; background: @surfaceContainerHighest; border-radius: 3px; }
QSlider::sub-page:horizontal { background: @primary; border-radius: 3px; }
QSlider::handle:horizontal {
    background: @primary;
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
}
QPushButton#Preset { text-align: center; }
"""

TOAST_STYLE = """
QPushButton#ToastButton {
    color: @onSecondaryContainer;
    font-size: 12px;
    font-weight: 600;
    background-color: @secondaryContainer;
    border: none;
    border-radius: 12px;
    padding: 6px 10px;
}
QPushButton#ToastMain {
    color: @onPrimary;
    font-size: 12px;
    font-weight: 600;
    background-color: @primary;
    border: none;
    border-radius: 12px;
    padding: 6px 10px;
}
QLabel#ToastHint { color: @onSurfaceVariant; font-size: 12px; font-weight: 400; }
QLabel#ToastBig { color: @primary; font-size: 20px; font-weight: 800; }
"""

PRESETS = [("30 min", 30), ("1 hour", 60), ("2 hours", 120), ("3 hours", 180)]
TEST_SECONDS = 15
TOAST_SECONDS = 12


def minutesText(minutes):
    if minutes < 60:
        return str(minutes) + " minutes"
    hours = minutes // 60
    extraMinutes = minutes % 60
    hoursText = str(hours) + " hour"
    if hours > 1:
        hoursText = hoursText + "s"
    if extraMinutes == 0:
        return hoursText
    return hoursText + " " + str(extraMinutes) + " min"


class SessionPrompt(QWidget):
    def __init__(self, whenDone):
        super().__init__()
        self.whenDone = whenDone
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(STYLE + PROMPT_STYLE))
        self.setGeometry(QApplication.primaryScreen().geometry())

        title = QLabel("How long do you want to be productive for?")
        title.setWordWrap(True)
        hint = QLabel("The more of it you spend focused, the higher you climb.", objectName="Hint")
        hint.setWordWrap(True)

        presetRow = QHBoxLayout()
        for presetName, presetMinutes in PRESETS:
            presetButton = QPushButton(presetName, objectName="Preset", cursor=Qt.CursorShape.PointingHandCursor)
            presetButton.clicked.connect(lambda checked=False, m=presetMinutes: self.slider.setValue(m // 15))
            presetRow.addWidget(presetButton)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 32)
        self.slider.setValue(4)
        self.slider.valueChanged.connect(self.updateChoice)
        self.choiceLabel = QLabel("", objectName="Hint")

        startButton = QPushButton("Start", objectName="BackButton", cursor=Qt.CursorShape.PointingHandCursor)
        startButton.clicked.connect(self.start)

        self.box = QFrame(self, objectName="Box")
        self.box.setFixedWidth(420)
        boxLayout = QVBoxLayout(self.box)
        boxLayout.setContentsMargins(24, 24, 24, 24)
        boxLayout.setSpacing(12)
        boxLayout.addWidget(title)
        boxLayout.addWidget(hint)
        boxLayout.addLayout(presetRow)
        boxLayout.addWidget(self.slider)
        boxLayout.addWidget(self.choiceLabel)
        boxLayout.addWidget(startButton)
        if isDebugMode():
            testButton = QPushButton("15 sec (testing)", objectName="Preset", cursor=Qt.CursorShape.PointingHandCursor)
            testButton.clicked.connect(self.startTest)
            boxLayout.addWidget(testButton)
        self.updateChoice()
        self.box.adjustSize()
        screen = self.geometry()
        self.box.move(screen.width() // 2 - self.box.width() // 2, screen.height() // 2 - self.box.height() // 2)

    def chosenMinutes(self):
        return self.slider.value() * 15

    def updateChoice(self):
        self.choiceLabel.setText("Focus for " + minutesText(self.chosenMinutes()))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(29, 27, 32, 140))

    def popUp(self):
        self.show()
        try:
            get_backend().float_above_everything(int(self.winId()))
        except Exception:
            pass
        self.raise_()
        self.activateWindow()
        animations.fadeWindowIn(self)
        animations.slideWidgetIn(self.box)

    def start(self):
        self.hide()
        self.whenDone(self.chosenMinutes())

    def startTest(self):
        self.hide()
        self.whenDone(TEST_SECONDS / 60)

    def closeEvent(self, event):
        event.ignore()


class SessionCard(QFrame):
    def __init__(self):
        super().__init__(objectName="SessionCard")
        self.setFixedWidth(180)
        cardLayout = QVBoxLayout(self)
        cardLayout.setContentsMargins(12, 6, 12, 8)
        cardLayout.setSpacing(4)
        self.timeLabel = QLabel("Focus session", objectName="SessionTime")
        self.timeLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cardLayout.addWidget(self.timeLabel)
        self.progressBar = QProgressBar(objectName="SessionBar")
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(4)
        cardLayout.addWidget(self.progressBar)
        self.totalSeconds = 1
        self.hide()

    def showSession(self, totalSeconds, secondsLeft):
        self.totalSeconds = max(int(totalSeconds), 1)
        self.updateTime(secondsLeft)
        self.show()

    def updateTime(self, secondsLeft):
        self.timeLabel.setText("Focus  " + session.timeLeftText(secondsLeft))
        self.progressBar.setRange(0, self.totalSeconds)
        self.progressBar.setValue(secondsLeft)


class SessionDoneToast(QWidget):
    def __init__(self, climbText, detailText, whenDone):
        super().__init__()
        self.whenDone = whenDone
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(BADGE_STYLE + TOAST_STYLE))

        card = QFrame(self, objectName="Badge")
        cardLayout = QVBoxLayout(card)
        cardLayout.setContentsMargins(14, 10, 14, 12)
        cardLayout.setSpacing(6)
        cardLayout.addWidget(QLabel("Session done!"))
        cardLayout.addWidget(QLabel(climbText, objectName="ToastBig"))
        hint = QLabel(detailText, objectName="ToastHint")
        hint.setWordWrap(True)
        cardLayout.addWidget(hint)
        buttonRow = QHBoxLayout()
        doneButton = QPushButton("Done", objectName="ToastButton", cursor=Qt.CursorShape.PointingHandCursor)
        doneButton.clicked.connect(lambda: self.finishWithChoice("done"))
        continueButton = QPushButton("Keep going " + str(session.CONTINUE_MINUTES) + " min", objectName="ToastMain", cursor=Qt.CursorShape.PointingHandCursor)
        continueButton.clicked.connect(lambda: self.finishWithChoice("continue"))
        buttonRow.addWidget(doneButton)
        buttonRow.addWidget(continueButton)
        cardLayout.addLayout(buttonRow)
        self.progressBar = QProgressBar()
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        self.progressBar.setRange(0, TOAST_SECONDS * 10)
        cardLayout.addWidget(self.progressBar)

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(card)
        self.setFixedWidth(260)
        self.fillStep = 0
        self.fillTimer = QTimer(self, interval=100, timeout=self.fillBar)

    def popUp(self):
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - BADGE_MARGIN, screen.top() + BADGE_MARGIN)
        animations.slideWindowIn(self, 40, 320)
        self.show()
        self.fillStep = 0
        self.fillTimer.start()

    def fillBar(self):
        self.fillStep = self.fillStep + 1
        self.progressBar.setValue(self.fillStep)
        if self.fillStep >= TOAST_SECONDS * 10:
            self.finishWithChoice("done")

    def finishWithChoice(self, choice):
        self.fillTimer.stop()
        self.hide()
        self.whenDone(choice)
