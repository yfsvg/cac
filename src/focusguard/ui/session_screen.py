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

from focusguard.core import session
from focusguard.platform import get_backend
from focusguard.ui.pause_screen import BADGE_MARGIN, BADGE_STYLE, STYLE
from focusguard.ui.theme import applyTheme

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
"""

PRESETS = [("30 min", 30), ("1 hour", 60), ("2 hours", 120), ("3 hours", 180)]
TEST_SECONDS = 15
TOAST_SECONDS = 10


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


def floatingWindowFlags():
    return (
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.WindowDoesNotAcceptFocus
        | Qt.WindowType.Window
    )


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
        hint = QLabel("FocusGuard keeps you on track until the time is up.", objectName="Hint")
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
        testButton = QPushButton("15 sec (testing)", objectName="Preset", cursor=Qt.CursorShape.PointingHandCursor)
        testButton.clicked.connect(self.startTest)

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

    def start(self):
        self.hide()
        self.whenDone(self.chosenMinutes())

    def startTest(self):
        self.hide()
        self.whenDone(TEST_SECONDS / 60)

    def closeEvent(self, event):
        event.ignore()


class SessionCard(QFrame):
    def __init__(self, whenBailOut):
        super().__init__(objectName="SessionCard")
        cardLayout = QVBoxLayout(self)
        cardLayout.setContentsMargins(20, 12, 20, 14)
        cardLayout.setSpacing(8)
        topRow = QHBoxLayout()
        topRow.setContentsMargins(0, 0, 0, 0)
        self.timeLabel = QLabel("Focus session", objectName="SessionTime")
        topRow.addWidget(self.timeLabel)
        topRow.addStretch()
        bailOutButton = QPushButton("Bail out", objectName="BailOutButton", cursor=Qt.CursorShape.PointingHandCursor)
        bailOutButton.setToolTip("Use a bail-out to end the session early")
        bailOutButton.clicked.connect(whenBailOut)
        topRow.addWidget(bailOutButton)
        cardLayout.addLayout(topRow)
        self.progressBar = QProgressBar(objectName="SessionBar")
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        cardLayout.addWidget(self.progressBar)
        self.totalSeconds = 1
        self.hide()

    def showSession(self, secondsLeft):
        if secondsLeft > self.totalSeconds:
            self.totalSeconds = secondsLeft
        self.updateTime(secondsLeft)
        self.show()

    def updateTime(self, secondsLeft):
        self.timeLabel.setText("Focus session: " + session.timeLeftText(secondsLeft))
        self.progressBar.setRange(0, self.totalSeconds)
        self.progressBar.setValue(secondsLeft)


class TimesUpToast(QWidget):
    def __init__(self, whenDone):
        super().__init__()
        self.whenDone = whenDone
        self.setWindowFlags(floatingWindowFlags())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(BADGE_STYLE + TOAST_STYLE))

        card = QFrame(self, objectName="Badge")
        cardLayout = QVBoxLayout(card)
        cardLayout.setContentsMargins(14, 10, 14, 12)
        cardLayout.setSpacing(8)
        cardLayout.addWidget(QLabel("Your time's up!"))
        hint = QLabel("Close FocusGuard or keep going for " + str(session.CONTINUE_MINUTES) + " more minutes?", objectName="ToastHint")
        hint.setWordWrap(True)
        cardLayout.addWidget(hint)
        buttonRow = QHBoxLayout()
        closeButton = QPushButton("Close app", objectName="ToastButton", cursor=Qt.CursorShape.PointingHandCursor)
        closeButton.clicked.connect(self.closeApp)
        continueButton = QPushButton("Continue " + str(session.CONTINUE_MINUTES) + " min", objectName="ToastMain", cursor=Qt.CursorShape.PointingHandCursor)
        continueButton.clicked.connect(self.keepGoing)
        buttonRow.addWidget(closeButton)
        buttonRow.addWidget(continueButton)
        cardLayout.addLayout(buttonRow)
        self.progressBar = QProgressBar()
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        self.progressBar.setRange(0, TOAST_SECONDS * 10)
        self.progressBar.setValue(0)
        cardLayout.addWidget(self.progressBar)

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(card)
        self.setFixedWidth(240)
        self.fillStep = 0
        self.fillTimer = QTimer(self, interval=100, timeout=self.fillBar)

    def popUp(self):
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - BADGE_MARGIN, screen.top() + BADGE_MARGIN)
        self.show()
        self.fillStep = 0
        self.fillTimer.start()

    def fillBar(self):
        self.fillStep = self.fillStep + 1
        self.progressBar.setValue(self.fillStep)
        if self.fillStep >= TOAST_SECONDS * 10:
            self.keepGoing()

    def closeApp(self):
        self.finishWithChoice("close")

    def keepGoing(self):
        self.finishWithChoice("continue")

    def finishWithChoice(self, choice):
        self.fillTimer.stop()
        self.hide()
        self.whenDone(choice)
