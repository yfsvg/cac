import math
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget


BOSS_PICTURES = Path(__file__).parent / "assets" / "bosses"
# same order as BOSS_NAMES in boss_fight.py
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
