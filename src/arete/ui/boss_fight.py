import math
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from arete.ui import animations
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

# Boss pictures, each one is an svg in assets/bosses

BOSS_PICTURES = Path(__file__).parent / "assets" / "bosses"
# same order as BOSS_NAMES
BOSS_FILES = ["Fuji1", "Fuji2", "Fuji3", "Everest1", "Everest2", "Everest3", "Matterhorn1", "Matterhorn2", "Matterhorn3"]

loadedBosses = {}


def drawBossCharacter(painter, bossNumber, rect):
    fileName = BOSS_FILES[bossNumber % len(BOSS_FILES)]
    if fileName not in loadedBosses:
        loadedBosses[fileName] = QSvgRenderer(str(BOSS_PICTURES / (fileName + ".svg")))
    renderer = loadedBosses[fileName]
    # every picture is a different size, so fit it inside the square and keep its shape
    pictureSize = renderer.defaultSize()
    fitScale = min(rect.width() / pictureSize.width(), rect.height() / pictureSize.height())
    fitWidth = pictureSize.width() * fitScale
    fitHeight = pictureSize.height() * fitScale
    renderer.render(painter, QRectF(rect.center().x() - fitWidth / 2, rect.center().y() - fitHeight / 2, fitWidth, fitHeight))


class BossPortrait(QWidget):
    def __init__(self, bossNumber, size):
        super().__init__()
        self.bossNumber = bossNumber
        self.setFixedSize(size, size)
        self.startTime = time.time()
        self.mood = "idle"
        self.moodStart = 0
        self.timer = QTimer(self, interval=33, timeout=self.update)

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def setMood(self, mood):
        self.mood = mood
        self.moodStart = time.time()

    def hurt(self):
        self.setMood("hurt")

    def laugh(self):
        self.setMood("laugh")

    def defeat(self):
        self.setMood("defeat")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        seconds = time.time() - self.startTime
        moodSeconds = time.time() - self.moodStart
        size = self.width()
        bob = math.sin(seconds * 2.2) * size * 0.03
        angle = 0
        scale = 1.0
        offsetX = 0
        opacity = 1.0
        if self.mood == "hurt" and moodSeconds < 0.6:
            offsetX = math.sin(moodSeconds * 60) * size * 0.06 * (1 - moodSeconds / 0.6)
        if self.mood == "laugh":
            bob = -abs(math.sin(seconds * 9)) * size * 0.06
        if self.mood == "defeat":
            progress = min(moodSeconds / 1.1, 1.0)
            angle = progress * 540
            scale = 1 - progress * 0.85
            opacity = 1 - progress
            if progress >= 1:
                return
        painter.setOpacity(opacity)
        painter.translate(size / 2 + offsetX, size / 2 + bob)
        painter.rotate(angle)
        painter.scale(scale, scale)
        drawBossCharacter(painter, self.bossNumber, QRectF(-size * 0.45, -size * 0.45, size * 0.9, size * 0.9))
        if self.mood == "hurt" and moodSeconds < 0.35:
            flash = QColor(255, 80, 80, int(140 * (1 - moodSeconds / 0.35)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(flash)
            painter.drawEllipse(QPointF(0, 0), size * 0.42, size * 0.42)


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
