from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from arete.ui import animations
from arete.ui.boss_art import BossPortrait
from arete.ui.pause_screen import BADGE_MARGIN, BADGE_STYLE
from arete.ui.theme import applyTheme

BOSS_NAMES = [
    "The Lantern Keeper",
    "The Ash Spirit",
    "The Fuji Guardian",
    "The Icefall Yeti",
    "The Death Zone Wraith",
    "Monsoon God",
    "The Hornli Troll",
    "The Ridge Eagle",
    "The Matterhorn King",
]

BOSS_TOAST_STYLE = """
QLabel#BossHeading { color: @onSurfaceVariant; font-size: 12px; font-weight: 700; }
QLabel#BossTitle { color: @boss; font-size: 19px; font-weight: 800; }
QLabel#BossDetail { color: @onSurfaceVariant; font-size: 12px; font-weight: 400; }
QPushButton#BossOk {
    color: @onPrimary;
    font-size: 12px;
    font-weight: 700;
    background-color: @primary;
    border: none;
    border-bottom: 3px solid @primaryShadow;
    border-radius: 12px;
    padding: 6px 14px;
}
QPushButton#BossOk:hover { background-color: @primaryShadow; }
QPushButton#BossOk:pressed { border-bottom: 1px solid @primaryShadow; padding-top: 8px; }
"""

TOAST_SECONDS = 10


def bossName(bossNumber):
    if bossNumber < len(BOSS_NAMES):
        return BOSS_NAMES[bossNumber]
    return "The Final Boss"


class BossToast(QWidget):
    def __init__(self, bossNumber, kind, detailText, whenDone):
        super().__init__()
        self.whenDone = whenDone
        self.kind = kind
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(BADGE_STYLE + BOSS_TOAST_STYLE))

        card = QFrame(self, objectName="Badge")
        cardLayout = QHBoxLayout(card)
        cardLayout.setContentsMargins(10, 10, 14, 12)
        cardLayout.setSpacing(10)
        self.portrait = BossPortrait(bossNumber, 84)
        cardLayout.addWidget(self.portrait, alignment=Qt.AlignmentFlag.AlignTop)

        textLayout = QVBoxLayout()
        textLayout.setSpacing(4)
        headingText = "A boss blocks the trail!"
        if kind == "defeat":
            headingText = "Boss defeated!"
        textLayout.addWidget(QLabel(headingText, objectName="BossHeading"))
        textLayout.addWidget(QLabel(bossName(bossNumber), objectName="BossTitle"))
        detail = QLabel(detailText, objectName="BossDetail")
        detail.setWordWrap(True)
        textLayout.addWidget(detail)
        buttonRow = QHBoxLayout()
        buttonRow.addStretch()
        okButton = QPushButton("Let's go" if kind == "appear" else "Keep climbing", objectName="BossOk", cursor=Qt.CursorShape.PointingHandCursor)
        okButton.clicked.connect(self.finish)
        buttonRow.addWidget(okButton)
        textLayout.addLayout(buttonRow)
        self.progressBar = QProgressBar()
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(5)
        self.progressBar.setRange(0, TOAST_SECONDS * 10)
        textLayout.addWidget(self.progressBar)
        cardLayout.addLayout(textLayout, 1)

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(card)
        self.setFixedWidth(330)
        self.fillStep = 0
        self.fillTimer = QTimer(self, interval=100, timeout=self.fillBar)

    def popUp(self):
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - BADGE_MARGIN, screen.top() + BADGE_MARGIN)
        animations.slideWindowIn(self, 40, 320)
        self.show()
        self.fillTimer.start()
        if self.kind == "defeat":
            QTimer.singleShot(400, self.portrait.hurt)
            QTimer.singleShot(1000, self.portrait.defeat)
            QTimer.singleShot(1500, lambda: animations.confetti(self))
        else:
            self.portrait.laugh()

    def fillBar(self):
        self.fillStep = self.fillStep + 1
        self.progressBar.setValue(self.fillStep)
        if self.fillStep >= TOAST_SECONDS * 10:
            self.finish()

    def finish(self):
        self.fillTimer.stop()
        self.hide()
        self.whenDone()
