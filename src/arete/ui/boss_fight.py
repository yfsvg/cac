# Bosses, split into three segments:
# 1. Names + pictures (one svg per boss in assets/bosses)
# 2. The animated portrait (bobs, shakes when hit, laughs, spins away when beaten)
# 3. The popup in the corner when a boss shows up or goes down


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


# Names, 3 per mountain in climb order (fuji, everest, matterhorn)

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


def bossName(bossNumber):
    if bossNumber < len(BOSS_NAMES):
        return BOSS_NAMES[bossNumber]
    return "The Final Boss"






# Pictures, each boss is an svg. Same order as BOSS_NAMES

BOSS_PICTURE_FOLDER = Path(__file__).parent / "assets" / "bosses"
BOSS_PICTURE_FILES = ["Fuji1", "Fuji2", "Fuji3", "Everest1", "Everest2", "Everest3", "Matterhorn1", "Matterhorn2", "Matterhorn3"]

# svgs only get read once, then reused
loadedBossPictures = {}


def drawBossCharacter(painter, bossNumber, pictureBox):
    bossFileName = BOSS_PICTURE_FILES[bossNumber % len(BOSS_PICTURE_FILES)]
    if bossFileName not in loadedBossPictures:
        loadedBossPictures[bossFileName] = QSvgRenderer(str(BOSS_PICTURE_FOLDER / (bossFileName + ".svg")))
    bossPicture = loadedBossPictures[bossFileName]

    # every picture is a different size, so fit it inside the box and keep its shape
    pictureSize = bossPicture.defaultSize()
    fitScale = min(pictureBox.width() / pictureSize.width(), pictureBox.height() / pictureSize.height())
    fittedWidth = pictureSize.width() * fitScale
    fittedHeight = pictureSize.height() * fitScale
    bossPicture.render(painter, QRectF(pictureBox.center().x() - fittedWidth / 2, pictureBox.center().y() - fittedHeight / 2, fittedWidth, fittedHeight))






# Portrait, the boss on its own little square that moves around depending on its mood
# moods: idle (gentle bob), hurt (shake + red flash), laugh (bouncing), defeat (spins away)

class BossPortrait(QWidget):
    def __init__(self, bossNumber, size):
        super().__init__()
        self.bossNumber = bossNumber
        self.setFixedSize(size, size)
        self.startTime = time.time()
        self.mood = "idle"
        self.moodStartTime = 0
        self.redrawTimer = QTimer(self, interval=33, timeout=self.update)

    # only animate while you can see it
    def showEvent(self, event):
        self.redrawTimer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.redrawTimer.stop()
        super().hideEvent(event)

    def setMood(self, mood):
        self.mood = mood
        self.moodStartTime = time.time()

    def hurt(self):
        self.setMood("hurt")

    def laugh(self):
        self.setMood("laugh")

    def defeat(self):
        self.setMood("defeat")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        secondsSinceMade = time.time() - self.startTime
        secondsIntoMood = time.time() - self.moodStartTime
        size = self.width()

        # idle bob up and down, everything else starts from still
        bobAmount = math.sin(secondsSinceMade * 2.2) * size * 0.03
        spinAngle = 0
        shrinkScale = 1.0
        shakeAmount = 0
        fadeOpacity = 1.0

        # hurt, side to side shake that dies down over 0.6s
        if self.mood == "hurt" and secondsIntoMood < 0.6:
            shakeAmount = math.sin(secondsIntoMood * 60) * size * 0.06 * (1 - secondsIntoMood / 0.6)

        # laugh, quick little hops
        if self.mood == "laugh":
            bobAmount = -abs(math.sin(secondsSinceMade * 9)) * size * 0.06

        # defeat, spins + shrinks + fades out over 1.1s then stays gone
        if self.mood == "defeat":
            defeatProgress = min(secondsIntoMood / 1.1, 1.0)
            spinAngle = defeatProgress * 540
            shrinkScale = 1 - defeatProgress * 0.85
            fadeOpacity = 1 - defeatProgress
            if defeatProgress >= 1:
                return

        painter.setOpacity(fadeOpacity)
        painter.translate(size / 2 + shakeAmount, size / 2 + bobAmount)
        painter.rotate(spinAngle)
        painter.scale(shrinkScale, shrinkScale)
        drawBossCharacter(painter, self.bossNumber, QRectF(-size * 0.45, -size * 0.45, size * 0.9, size * 0.9))

        # red flash right when it gets hit
        if self.mood == "hurt" and secondsIntoMood < 0.35:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 80, 80, int(140 * (1 - secondsIntoMood / 0.35))))
            painter.drawEllipse(QPointF(0, 0), size * 0.42, size * 0.42)






# Popup, slides in top right when a boss shows up ("appear") or gets beaten ("defeat")
# closes itself after 10 seconds, the bar along the bottom fills up as it counts down

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


class BossToast(QWidget):
    def __init__(self, bossNumber, kind, detailText, whenDone):
        super().__init__()
        self.whenDone = whenDone
        self.kind = kind

        # floats on top without stealing focus from whatever ur doing
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



        # card, portrait on the left + words on the right
        toastCard = QFrame(self, objectName="Badge")
        toastCardLayout = QHBoxLayout(toastCard)
        toastCardLayout.setContentsMargins(10, 10, 14, 12)
        toastCardLayout.setSpacing(10)
        self.portrait = BossPortrait(bossNumber, 84)
        toastCardLayout.addWidget(self.portrait, alignment=Qt.AlignmentFlag.AlignTop)



        # words, heading + boss name + whatever the dashboard wants to say
        wordsLayout = QVBoxLayout()
        wordsLayout.setSpacing(4)
        wordsLayout.addWidget(QLabel("Boss defeated!" if kind == "defeat" else "A boss blocks the trail!", objectName="BossHeading"))
        wordsLayout.addWidget(QLabel(bossName(bossNumber), objectName="BossTitle"))
        detailLabel = QLabel(detailText, objectName="BossDetail")
        detailLabel.setWordWrap(True)
        wordsLayout.addWidget(detailLabel)

        buttonRow = QHBoxLayout()
        buttonRow.addStretch()
        okButton = QPushButton("Let's go" if kind == "appear" else "Keep climbing", objectName="BossOk", cursor=Qt.CursorShape.PointingHandCursor)
        okButton.clicked.connect(self.finish)
        buttonRow.addWidget(okButton)
        wordsLayout.addLayout(buttonRow)

        # countdown bar, fills in tenths of a second
        self.countdownBar = QProgressBar()
        self.countdownBar.setTextVisible(False)
        self.countdownBar.setFixedHeight(5)
        self.countdownBar.setRange(0, TOAST_SECONDS * 10)
        wordsLayout.addWidget(self.countdownBar)
        toastCardLayout.addLayout(wordsLayout, 1)



        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.addWidget(toastCard)
        self.setFixedWidth(330)
        self.countdownStep = 0
        self.countdownTimer = QTimer(self, interval=100, timeout=self.fillCountdownBar)


    # slides in top right, a beaten boss gets hit, spins away, then confetti
    def popUp(self):
        self.adjustSize()
        screenArea = QApplication.primaryScreen().availableGeometry()
        self.move(screenArea.right() - self.width() - BADGE_MARGIN, screenArea.top() + BADGE_MARGIN)
        animations.slideWindowIn(self, 40, 320)
        self.show()
        self.countdownTimer.start()
        if self.kind == "defeat":
            QTimer.singleShot(400, self.portrait.hurt)
            QTimer.singleShot(1000, self.portrait.defeat)
            QTimer.singleShot(1500, lambda: animations.confetti(self))
        else:
            self.portrait.laugh()

    def fillCountdownBar(self):
        self.countdownStep = self.countdownStep + 1
        self.countdownBar.setValue(self.countdownStep)
        if self.countdownStep >= TOAST_SECONDS * 10:
            self.finish()

    def finish(self):
        self.countdownTimer.stop()
        self.hide()
        self.whenDone()
