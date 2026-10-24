import time

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


        self.title = QLabel("Taking a break with " + appName + "?")
        self.title.setWordWrap(True)
        self.hint = QLabel("That's okay! Just let us know what's up.", objectName="Hint")

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
        self.otherBox.setPlaceholderText("Tell us in a few words, then press Enter")
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
        # Keep the box 10px inside the screen
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
        painter.fillRect(self.rect(), QColor(29, 27, 32, 140))

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
        self.title.setText("Take a breath... " + str(self.secondsLeft) + " seconds")
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
        self.title.setText("Take a breath... " + str(self.secondsLeft) + " seconds")
        if self.secondsLeft <= 0:
            self.timer.stop()
            self.title.setText("All set, enjoy your break!")
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


TREE_REMINDER = "Saying continue won't harm your tree!"

CHECK_IN_MESSAGES = [
    "Your {minutes} minute break is up. Are you feeling alright and ready to get back to work, or still feeling down?",
    "How you feeling now? It's alright if you're still stressed, don't worry! Take your time.",
    "Are you feeling better? If not, don't worry. Studies show that forcing yourself to work while you're down doesn't actually make you more productive, so take your time!",
    "Hey, just checking in again. How are you feeling? Ready to jump back in, or need a little longer? No pressure.",
    "No rush. Feeling any better, or do you want another {minutes} minutes? It's totally natural if you feel like you need more time, and it's good for your mind to relax.",
    "It's okay if you need more time. Ready to give work another go, or still not feeling it? Either way it's ok.",
]


class CheckInScreen(QWidget):
    def __init__(self, appName, timesAsked, breakMinutes, breaksLeft, whenDone):
        super().__init__()
        self.whenDone = whenDone

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        
        self.setStyleSheet(applyTheme(STYLE))
        self.setGeometry(QApplication.primaryScreen().geometry())


        messageIndex = timesAsked % len(CHECK_IN_MESSAGES)
        title = QLabel(str(breakMinutes) + " Minute Check In")
        message = QLabel(CHECK_IN_MESSAGES[messageIndex].replace("{minutes}", str(breakMinutes)), objectName="Hint")
        message.setWordWrap(True)
        treeReminder = QLabel(TREE_REMINDER, objectName="Hint")
        treeReminder.setWordWrap(True)
        breaksLeftText = "You have " + str(breaksLeft) + " breaks left today."
        if breaksLeft == 1:
            breaksLeftText = "You have 1 break left today."
        if breaksLeft == 0:
            breaksLeftText = "That was your last break for today."
        breaksLeftLabel = QLabel(breaksLeftText, objectName="Hint")
        breaksLeftLabel.setWordWrap(True)

        readyButton = QPushButton("I'm ready, back to work", objectName="BackButton", cursor=Qt.CursorShape.PointingHandCursor)
        readyButton.clicked.connect(self.bounceBack)
        continueButton = QPushButton("Still feeling down, continue break", objectName="OpenButton", cursor=Qt.CursorShape.PointingHandCursor)
        continueButton.clicked.connect(self.continueBreak)
        if breaksLeft == 0:
            continueButton.setText("No breaks left today")
            continueButton.setEnabled(False)


        self.box = QFrame(self, objectName="Box")
        self.box.setFixedWidth(360)
        boxLayout = QVBoxLayout(self.box)
        boxLayout.setContentsMargins(24, 24, 24, 24)


        boxLayout.setSpacing(12)
        boxLayout.addWidget(title)
        boxLayout.addWidget(message)
        boxLayout.addWidget(treeReminder)
        boxLayout.addWidget(breaksLeftLabel)
        boxLayout.addStretch()
        boxLayout.addWidget(readyButton)
        boxLayout.addWidget(continueButton)


        self.box.adjustSize()
        self.box.setFixedHeight(int(self.box.height() * 1.5))


        screen = self.geometry()
        self.box.move(screen.width() // 2 - self.box.width() // 2, screen.height() // 2 - self.box.height() // 2)


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


    def bounceBack(self):
        self.hide()
        self.whenDone("bounceBack")


    def continueBreak(self):
        self.hide()
        self.whenDone("continue")

    def closeEvent(self, event):
        event.ignore()


# Break badge, tiny "Break time!" card in the top right corner with a bar that drains as the break runs out
# Never takes focus, so it doesn't interrupt whatever you're doing. The x in the corner ends the break early

BADGE_STYLE = """
QFrame#Badge {
    background-color: @surfaceContainerHigh;
    border: 1px solid @outlineVariant;
    border-radius: 16px;
}
QLabel { color: @onSurface; font-size: 13px; font-weight: 600; }
QProgressBar {
    background-color: @surfaceContainerHighest;
    border: none;
    border-radius: 3px;
}
QProgressBar::chunk { background-color: @primary; border-radius: 3px; }
QPushButton#CancelBreak {
    color: @onSurfaceVariant;
    font-size: 12px;
    font-weight: 700;
    background-color: @surfaceContainerHighest;
    border: none;
    border-radius: 10px;
    padding: 0;
}
QPushButton#CancelBreak:hover { background-color: @errorContainer; color: @onErrorContainer; }
"""

BADGE_MARGIN = 16


class BreakBadge(QWidget):
    def __init__(self, whenCancelled):
        super().__init__()
        self.whenCancelled = whenCancelled
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))

        card = QFrame(self, objectName="Badge")
        cardLayout = QVBoxLayout(card)
        cardLayout.setContentsMargins(14, 10, 14, 12)
        cardLayout.setSpacing(6)
        topRow = QHBoxLayout()
        topRow.setContentsMargins(0, 0, 0, 0)
        topRow.addWidget(QLabel("Break time!"))
        topRow.addStretch()
        cancelButton = QPushButton("✕", objectName="CancelBreak", cursor=Qt.CursorShape.PointingHandCursor)
        cancelButton.setFixedSize(20, 20)
        cancelButton.setToolTip("End break early")
        cancelButton.clicked.connect(self.cancelBreak)
        topRow.addWidget(cancelButton)
        cardLayout.addLayout(topRow)
        self.progressBar = QProgressBar()
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)
        cardLayout.addWidget(self.progressBar)

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(card)
        self.setFixedWidth(160)

        self.endTime = 0
        self.breakSeconds = 0
        self.topOffset = 0
        self.ticker = QTimer(self, interval=1000, timeout=self.updateBar)

    def startBreak(self, breakSeconds):
        # Restyle every time so it matches the current light/dark theme
        self.setStyleSheet(applyTheme(BADGE_STYLE))
        self.breakSeconds = breakSeconds
        self.endTime = time.time() + breakSeconds
        self.progressBar.setRange(0, breakSeconds * 1000)
        self.updateBar()
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - BADGE_MARGIN, screen.top() + BADGE_MARGIN + self.topOffset)
        self.show()
        self.ticker.start()

    def updateBar(self):
        # Milliseconds so the bar drains smoothly instead of jumping a second early
        millisecondsLeft = int((self.endTime - time.time()) * 1000)
        if millisecondsLeft < 0:
            millisecondsLeft = 0
        self.progressBar.setValue(millisecondsLeft)

    def stopBreak(self):
        self.ticker.stop()
        self.hide()

    def cancelBreak(self):
        self.stopBreak()
        self.whenCancelled()
