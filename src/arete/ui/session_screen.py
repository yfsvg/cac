from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QFontMetrics
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from arete.core import session
from arete.core.debug_mode import isDebugMode
from arete.ui import animations
from arete.ui.pause_screen import BADGE_MARGIN, BADGE_STYLE
from arete.ui.theme import applyTheme

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

PANEL_STYLE = """
QFrame#SessionPanel { background-color: @surfaceContainerLow; border-radius: 24px; border: 1px solid @cardBorder; }
QLabel#PanelTitle { color: @onSurface; font-size: 17px; font-weight: 800; }
QLabel#PanelHint { color: @onSurfaceVariant; font-size: 13px; }
QLabel#PanelClock { color: @primary; font-size: 30px; font-weight: 800; }
QPushButton#LengthChip {
    color: @onSurfaceVariant;
    font-size: 12px;
    font-weight: 700;
    background-color: @surfaceContainerHigh;
    border: 1px solid @cardBorder;
    border-radius: 14px;
    padding: 7px 0px;
}
QPushButton#LengthChip:hover { background-color: @surfaceContainerHighest; }
QPushButton#LengthChip:checked { color: @onPrimary; background-color: @primary; border: 1px solid @primary; }
QPushButton#PanelStart {
    color: @onPrimary;
    font-size: 14px;
    font-weight: 700;
    background-color: @primary;
    border: none;
    border-bottom: 4px solid @primaryShadow;
    border-radius: 16px;
    padding: 10px 16px 8px 16px;
}
QPushButton#PanelStart:hover { background-color: @primaryHover; }
QPushButton#PanelStart:pressed { border-bottom: 1px solid @primaryShadow; padding-top: 13px; }
QPushButton#PanelEnd {
    color: @onSurface;
    font-size: 14px;
    font-weight: 700;
    background-color: @surfaceContainerHigh;
    border: 1px solid @cardBorder;
    border-bottom: 4px solid @cardBorder;
    border-radius: 16px;
    padding: 10px 16px 8px 16px;
}
QPushButton#PanelEnd:hover { background-color: @errorContainer; color: @onErrorContainer; }
QProgressBar#PanelBar { background-color: @surfaceContainerHighest; border: none; border-radius: 4px; }
QProgressBar#PanelBar::chunk { background-color: @primary; border-radius: 4px; }
"""

LENGTHS = [("No timer", None), ("30 min", 30), ("1 hour", 60), ("2 hours", 120), ("3 hours", 180)]
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


class SessionPanel(QFrame):
    def __init__(self, whenStarted, whenEnded):
        super().__init__(objectName="SessionPanel")
        self.whenStarted = whenStarted
        self.whenEnded = whenEnded
        self.chosenMinutes = None
        panelLayout = QVBoxLayout(self)
        panelLayout.setContentsMargins(18, 16, 18, 16)
        panelLayout.setSpacing(10)

        self.titleLabel = QLabel("Start a focus session", objectName="PanelTitle")
        panelLayout.addWidget(self.titleLabel)
        self.hintLabel = QLabel("", objectName="PanelHint")
        self.hintLabel.setWordWrap(True)
        panelLayout.addWidget(self.hintLabel)

        self.chipRow = QWidget()
        chipLayout = QHBoxLayout(self.chipRow)
        chipLayout.setContentsMargins(0, 0, 0, 0)
        chipLayout.setSpacing(6)
        self.chips = []
        lengths = list(LENGTHS)
        if isDebugMode():
            lengths.append(("15 sec", TEST_SECONDS / 60))
        for chipName, chipMinutes in lengths:
            chip = QPushButton(chipName, objectName="LengthChip", cursor=Qt.CursorShape.PointingHandCursor)
            chip.setCheckable(True)
            chip.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            chipFont = QFont(chip.font())
            chipFont.setPixelSize(12)
            chipFont.setBold(True)
            chip.setMinimumWidth(QFontMetrics(chipFont).horizontalAdvance(chipName) + 16)
            chip.clicked.connect(lambda checked=False, m=chipMinutes, c=chip: self.pickLength(m, c))
            chipLayout.addWidget(chip)
            self.chips.append(chip)
        panelLayout.addWidget(self.chipRow)

        self.clockLabel = QLabel("", objectName="PanelClock")
        panelLayout.addWidget(self.clockLabel)
        self.progressBar = QProgressBar(objectName="PanelBar")
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(8)
        panelLayout.addWidget(self.progressBar)

        self.startButton = QPushButton("Start focusing", objectName="PanelStart", cursor=Qt.CursorShape.PointingHandCursor)
        self.startButton.clicked.connect(self.startPressed)
        panelLayout.addWidget(self.startButton)
        self.endButton = QPushButton("End session", objectName="PanelEnd", cursor=Qt.CursorShape.PointingHandCursor)
        self.endButton.clicked.connect(self.whenEnded)
        panelLayout.addWidget(self.endButton)

        self.pickLength(None, self.chips[0])
        self.showIdle()

    def pickLength(self, minutes, pickedChip):
        self.chosenMinutes = minutes
        for chip in self.chips:
            chip.setChecked(chip is pickedChip)
        if minutes is None:
            self.hintLabel.setText("Focus as long as you want and end it yourself. You climb for the time you stay focused.")
        else:
            self.hintLabel.setText("Stay focused until the timer runs out. Closing Arete or giving up early fails the session.")

    def startPressed(self):
        self.whenStarted(self.chosenMinutes)

    def showIdle(self):
        self.titleLabel.setText("Start a focus session")
        self.hintLabel.show()
        self.chipRow.show()
        self.clockLabel.hide()
        self.progressBar.hide()
        self.startButton.show()
        self.endButton.hide()
        self.pickLength(self.chosenMinutes, self.chips[[chip.isChecked() for chip in self.chips].index(True)])

    def showRunning(self, timed):
        self.hintLabel.hide()
        self.chipRow.hide()
        self.startButton.hide()
        self.clockLabel.show()
        self.progressBar.setVisible(timed)
        self.endButton.show()
        if timed:
            self.titleLabel.setText("Focus session")
            self.endButton.setText("Give up")
        else:
            self.titleLabel.setText("Focusing, no timer")
            self.endButton.setText("End session")

    def updateTimed(self, totalSeconds, secondsLeft):
        self.clockLabel.setText(session.timeLeftText(secondsLeft))
        self.progressBar.setRange(0, max(int(totalSeconds), 1))
        self.progressBar.setValue(int(totalSeconds) - secondsLeft)

    def updateFree(self, secondsPassed):
        self.clockLabel.setText(session.timePassedText(secondsPassed))


class SessionCard(QFrame):
    def __init__(self):
        super().__init__(objectName="SessionCard")
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
        self.progressBar.show()
        self.updateTime(secondsLeft)
        self.show()

    def updateTime(self, secondsLeft):
        self.timeLabel.setText("Focus  " + session.timeLeftText(secondsLeft))
        self.progressBar.setRange(0, self.totalSeconds)
        self.progressBar.setValue(secondsLeft)

    def showFree(self, secondsPassed):
        self.progressBar.hide()
        self.updateFree(secondsPassed)
        self.show()

    def updateFree(self, secondsPassed):
        self.timeLabel.setText("Focusing  " + session.timePassedText(secondsPassed))


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
