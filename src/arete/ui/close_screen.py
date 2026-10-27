import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from arete.ui import animations
from arete.ui.pause_screen import STYLE
from arete.ui.theme import applyTheme

# Close popup from the tray menu. 1 min wait before u can quit, arete keeps running the whole time

WAIT_SECONDS = 60

# no dark tint behind this one so the box needs a border
CLOSE_STYLE = STYLE + """
QFrame#Box { border: 1px solid @outlineVariant; }
QLabel#Warning { color: @error; font-size: 14px; font-weight: 600; }
"""


def timeText(seconds):
    return str(seconds // 60) + ":" + str(seconds % 60).zfill(2)


class CloseScreen(QWidget):

    def __init__(self, isInSession, whenResumed, whenQuit):
        super().__init__()
        self.isInSession = isInSession
        self.whenResumed = whenResumed
        self.whenQuit = whenQuit
        self.secondsLeft = None
        self.quitting = False

        self.setWindowTitle("Close Arete")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(CLOSE_STYLE))

        self.title = QLabel()
        self.hint = QLabel("Arete keeps running until you quit. Changed your mind? Hit resume.", objectName="Hint")
        self.hint.setWordWrap(True)
        self.warning = QLabel("You're in a focus session, quitting will count it as failed.", objectName="Warning")
        self.warning.setWordWrap(True)

        self.progressBar = QProgressBar()
        self.progressBar.setRange(0, WAIT_SECONDS * 1000)
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(6)

        self.resumeButton = QPushButton("Resume", objectName="BackButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.resumeButton.clicked.connect(self.close)
        self.quitButton = QPushButton("Quit anyway", objectName="OpenButton")
        self.quitButton.clicked.connect(self.quitAnyway)
        self.quitButton.setEnabled(False)
        buttonRow = QHBoxLayout()
        buttonRow.addWidget(self.resumeButton)
        buttonRow.addWidget(self.quitButton)

        self.box = QFrame(objectName="Box")
        self.box.setFixedWidth(340)
        boxLayout = QVBoxLayout(self.box)
        boxLayout.setContentsMargins(24, 24, 24, 24)
        boxLayout.setSpacing(12)
        boxLayout.addWidget(self.title)
        boxLayout.addWidget(self.hint)
        boxLayout.addWidget(self.warning)
        boxLayout.addWidget(self.progressBar)
        boxLayout.addLayout(buttonRow)

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(self.box)

        self.startedAt = time.monotonic()
        self.timer = QTimer(self, interval=50, timeout=self.countDown)
        self.timer.start()
        self.countDown()

    def popUp(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2, screen.center().y() - self.height() // 2)
        animations.fadeWindowIn(self)
        self.show()
        self.raise_()
        self.activateWindow()

    # already counting, just show it again
    def bringBack(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()


    # bar fills smoothly, text only changes once a sec

    def countDown(self):
        secondsPassed = time.monotonic() - self.startedAt
        self.progressBar.setValue(min(int(secondsPassed * 1000), WAIT_SECONDS * 1000))
        secondsLeft = max(WAIT_SECONDS - int(secondsPassed), 0)
        if secondsLeft == self.secondsLeft:
            return
        self.secondsLeft = secondsLeft

        # checked every sec in case u start a session mid countdown
        self.warning.setVisible(self.isInSession())
        if secondsLeft > 0:
            self.title.setText("Closing Arete in " + timeText(secondsLeft))
        else:
            self.timer.stop()
            self.title.setText("Still want to quit?")
            self.hint.setText("You waited it out. Quit now, or resume and keep going.")
            self.quitButton.setEnabled(True)
            self.quitButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adjustSize()


    # resume, esc and alt+f4 all just close it. quit only once the wait is over

    def quitAnyway(self):
        self.quitting = True
        self.close()

    def closeEvent(self, event):
        self.timer.stop()
        self.deleteLater()
        if self.quitting:
            self.whenQuit()
        else:
            self.whenResumed()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()

    # no title bar so drag it around by the box
    def mousePressEvent(self, event):
        self.windowHandle().startSystemMove()
