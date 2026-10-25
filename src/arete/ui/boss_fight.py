import random

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QPainter
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from arete.platform import get_backend
from arete.ui import animations
from arete.ui.brain_games import ALL_GAMES
from arete.ui.pause_screen import STYLE
from arete.ui.theme import applyTheme

GAMES_PER_FIGHT = 3
WINS_NEEDED = 2

BOSS_NAMES = [
    "The Lantern Keeper",
    "The Ash Spirit",
    "The Fuji Guardian",
    "The Icefall Yeti",
    "The Death Zone Wraith",
    "The Everest Guardian",
    "The Hornli Troll",
    "The Ridge Eagle",
    "The Matterhorn King",
]

FIGHT_STYLE = """
QLabel#GameTitle { color: @onSurface; font-size: 22px; font-weight: 700; }
QLabel#GameHint { color: @onSurfaceVariant; font-size: 14px; font-weight: 400; }
QLabel#GameStatus { color: @primary; font-size: 14px; font-weight: 700; }
QLabel#GameBig { color: @onSurface; font-size: 40px; font-weight: 800; }
QLabel#BossName { color: @error; font-size: 28px; font-weight: 800; }
QLabel#ScoreDot { font-size: 14px; font-weight: 700; }
QPushButton#MainChoice {
    text-align: center;
    background-color: @primary;
    color: @onPrimary;
    font-weight: 600;
}
QPushButton#MainChoice:hover { background-color: @primaryHover; color: @onPrimary; }
QPushButton#MainChoice { border-bottom: 4px solid @primaryShadow; }
QPushButton#MainChoice:pressed { border-bottom: 1px solid @primaryShadow; padding-top: 13px; }
QPushButton#SideChoice { text-align: center; }
QPushButton#LeaveButton {
    text-align: center;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 12px;
}
QPushButton#LeaveButton:hover { background-color: @errorContainer; color: @onErrorContainer; }
"""


def bossName(bossNumber):
    if bossNumber < len(BOSS_NAMES):
        return BOSS_NAMES[bossNumber]
    return "The Final Boss"


class BossFight(QWidget):
    def __init__(self, bossNumber, difficulty, whenDone, allowSkip=True):
        super().__init__()
        self.bossNumber = bossNumber
        self.difficulty = difficulty
        self.whenDone = whenDone
        self.games = random.sample(ALL_GAMES, GAMES_PER_FIGHT)
        self.gameNumber = 0
        self.results = []
        self.currentGame = None

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(STYLE + FIGHT_STYLE))
        self.setGeometry(QApplication.primaryScreen().geometry())

        self.box = QFrame(self, objectName="Box")
        self.box.setFixedWidth(460)
        self.boxLayout = QVBoxLayout(self.box)
        self.boxLayout.setContentsMargins(28, 24, 28, 24)
        self.boxLayout.setSpacing(14)

        self.scoreRow = QHBoxLayout()
        self.scoreDots = []
        for index in range(GAMES_PER_FIGHT):
            scoreDot = QLabel("Game " + str(index + 1), objectName="ScoreDot")
            scoreDot.hide()
            self.scoreDots.append(scoreDot)
            self.scoreRow.addWidget(scoreDot)
        self.scoreRow.addStretch()
        leaveButton = QPushButton("Leave", objectName="LeaveButton", cursor=Qt.CursorShape.PointingHandCursor)
        leaveButton.setToolTip("Leave the fight, you can try again after your next session (Esc)")
        leaveButton.clicked.connect(self.leaveFight)
        self.scoreRow.addWidget(leaveButton)
        self.boxLayout.addLayout(self.scoreRow)

        self.page = QWidget()
        self.pageLayout = QVBoxLayout(self.page)
        self.pageLayout.setContentsMargins(0, 0, 0, 0)
        self.pageLayout.setSpacing(12)
        self.boxLayout.addWidget(self.page)

        self.buttonRow = QHBoxLayout()
        self.sideButton = QPushButton("", objectName="SideChoice", cursor=Qt.CursorShape.PointingHandCursor)
        self.mainButton = QPushButton("", objectName="MainChoice", cursor=Qt.CursorShape.PointingHandCursor)
        self.mainAction = None
        self.sideAction = None
        self.mainButton.clicked.connect(lambda: self.mainAction())
        self.sideButton.clicked.connect(lambda: self.sideAction())
        self.buttonRow.addWidget(self.sideButton)
        self.buttonRow.addWidget(self.mainButton)
        self.boxLayout.addLayout(self.buttonRow)

        self.showIntro(allowSkip)

    def clearPage(self):
        while self.pageLayout.count() > 0:
            item = self.pageLayout.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()
                item.widget().deleteLater()

    def addText(self, text, name):
        textLabel = QLabel(text, objectName=name)
        textLabel.setWordWrap(True)
        self.pageLayout.addWidget(textLabel)
        textLabel.show()
        return textLabel

    def setButtons(self, mainText, mainAction, sideText=None, sideAction=None):
        self.mainButton.setText(mainText)
        self.mainAction = mainAction
        self.mainButton.show()
        if sideText is None:
            self.sideButton.hide()
        else:
            self.sideButton.setText(sideText)
            self.sideAction = sideAction
            self.sideButton.show()

    def showIntro(self, allowSkip):
        self.clearPage()
        self.addText("Boss fight!", "Hint")
        self.addText(bossName(self.bossNumber), "BossName")
        self.addText("It's blocking the trail. Win " + str(WINS_NEEDED) + " of " + str(GAMES_PER_FIGHT) + " brain games to get past it.", "Hint")
        self.addText("Level " + str(self.difficulty) + " of 9", "GameStatus")
        if allowSkip:
            self.setButtons("Fight!", self.startNextGame, "Not now", lambda: self.finishFight(None))
        else:
            self.setButtons("Fight!", self.startNextGame)
        self.placeBox()

    def startNextGame(self):
        for scoreDot in self.scoreDots:
            scoreDot.show()
        self.clearPage()
        self.mainButton.hide()
        self.sideButton.hide()
        gameClass = self.games[self.gameNumber]
        self.currentGame = gameClass(self.difficulty, self.gameDone)
        self.currentGame.setMinimumHeight(440)
        self.pageLayout.addWidget(self.currentGame)
        self.placeBox()
        self.currentGame.start()
        QTimer.singleShot(0, self.placeBox)

    def gameDone(self, passed):
        self.currentGame = None
        self.results.append(passed)
        scoreDot = self.scoreDots[self.gameNumber]
        if passed:
            scoreDot.setText("Game " + str(self.gameNumber + 1) + " won")
            scoreDot.setStyleSheet("color: #2FB36D;")
        else:
            scoreDot.setText("Game " + str(self.gameNumber + 1) + " lost")
            scoreDot.setStyleSheet("color: #E5534B;")
        self.gameNumber = self.gameNumber + 1
        wins = self.results.count(True)
        losses = self.results.count(False)
        self.clearPage()
        if wins >= WINS_NEEDED:
            self.showResult(True)
            return
        if losses > GAMES_PER_FIGHT - WINS_NEEDED:
            self.showResult(False)
            return
        if passed:
            self.addText("Nice, you won that one!", "GameTitle")
        else:
            self.addText("That one got away.", "GameTitle")
        winsText = str(wins) + " wins so far."
        if wins == 1:
            winsText = "1 win so far."
        self.addText(winsText + " Win " + str(WINS_NEEDED - wins) + " more to beat the boss.", "Hint")
        self.setButtons("Next game", self.startNextGame)
        self.placeBox()
        self.fadeInPage()

    def showResult(self, won):
        if won:
            self.addText("You beat " + bossName(self.bossNumber) + "!", "GameTitle")
            self.addText("The trail is open again. Keep focusing to keep climbing.", "Hint")
            self.setButtons("Keep climbing", lambda: self.finishFight(True))
            QTimer.singleShot(150, lambda: animations.confetti(self.box))
        else:
            self.addText(bossName(self.bossNumber) + " won this time.", "GameTitle")
            self.addText("No worries, you can fight it again after your next focus session.", "Hint")
            self.setButtons("OK", lambda: self.finishFight(False))
            QTimer.singleShot(150, lambda: animations.shake(self.box))
        self.placeBox()
        self.fadeInPage()

    def leaveFight(self):
        self.finishFight(None)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.leaveFight()
            return
        super().keyPressEvent(event)

    def finishFight(self, won):
        if self.currentGame is not None:
            self.currentGame.stop()
        self.hide()
        self.whenDone(won)

    def fadeInPage(self):
        animations.fadeIn(self.page, 220)

    def placeBox(self):
        self.pageLayout.activate()
        self.boxLayout.activate()
        boxHeight = max(self.box.sizeHint().height(), self.box.heightForWidth(self.box.width()))
        self.box.resize(self.box.width(), boxHeight)
        screen = self.geometry()
        self.box.move(screen.width() // 2 - self.box.width() // 2, screen.height() // 2 - self.box.height() // 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(20, 18, 26, 170))

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

    def closeEvent(self, event):
        event.ignore()
