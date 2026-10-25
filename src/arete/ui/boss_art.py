import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


OUTLINE = QColor("#2A1B3D")


def outlinePen(width=3):
    return QPen(OUTLINE, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)


def drawEye(painter, center, size, eyeColor, angry, blink):
    painter.setPen(outlinePen(2.5))
    painter.setBrush(QColor("white"))
    if blink:
        painter.drawLine(QPointF(center.x() - size, center.y()), QPointF(center.x() + size, center.y()))
        return
    painter.drawEllipse(center, size, size)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(eyeColor)
    painter.drawEllipse(QPointF(center.x(), center.y() + size * 0.15), size * 0.55, size * 0.55)
    painter.setBrush(QColor("white"))
    painter.drawEllipse(QPointF(center.x() - size * 0.2, center.y() - size * 0.1), size * 0.18, size * 0.18)
    if angry:
        painter.setPen(outlinePen(3.5))
        side = 1 if center.x() < 50 else -1
        painter.drawLine(QPointF(center.x() - size * 1.1 * side, center.y() - size * 1.3), QPointF(center.x() + size * 0.9 * side, center.y() - size * 0.75))


def drawFace(painter, leftEye, rightEye, eyeSize, eyeColor, mouthCenter, mouthWidth, blink, laughing):
    drawEye(painter, leftEye, eyeSize, eyeColor, True, blink)
    drawEye(painter, rightEye, eyeSize, eyeColor, True, blink)
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#5A1A2A"))
    mouth = QPainterPath(QPointF(mouthCenter.x() - mouthWidth, mouthCenter.y()))
    depth = mouthWidth * (0.9 if laughing else 0.55)
    mouth.quadTo(QPointF(mouthCenter.x(), mouthCenter.y() + depth), QPointF(mouthCenter.x() + mouthWidth, mouthCenter.y()))
    mouth.closeSubpath()
    painter.drawPath(mouth)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("white"))
    fang = QPainterPath(QPointF(mouthCenter.x() - mouthWidth * 0.5, mouthCenter.y() + 0.5))
    fang.lineTo(QPointF(mouthCenter.x() - mouthWidth * 0.3, mouthCenter.y() + mouthWidth * 0.35))
    fang.lineTo(QPointF(mouthCenter.x() - mouthWidth * 0.1, mouthCenter.y() + 0.5))
    fang.closeSubpath()
    painter.drawPath(fang)
    fang = QPainterPath(QPointF(mouthCenter.x() + mouthWidth * 0.1, mouthCenter.y() + 0.5))
    fang.lineTo(QPointF(mouthCenter.x() + mouthWidth * 0.3, mouthCenter.y() + mouthWidth * 0.35))
    fang.lineTo(QPointF(mouthCenter.x() + mouthWidth * 0.5, mouthCenter.y() + 0.5))
    fang.closeSubpath()
    painter.drawPath(fang)


def drawLanternKeeper(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#FFD27A"))
    flame = QPainterPath(QPointF(50, 4))
    flame.quadTo(QPointF(60, 14), QPointF(50, 20))
    flame.quadTo(QPointF(40, 14), QPointF(50, 4))
    painter.drawPath(flame)
    painter.setBrush(QColor("#3A2A2A"))
    painter.drawRoundedRect(QRectF(34, 18, 32, 8), 3, 3)
    painter.drawRoundedRect(QRectF(34, 86, 32, 8), 3, 3)
    painter.setBrush(QColor("#E5484D"))
    painter.drawEllipse(QRectF(18, 22, 64, 68))
    painter.setPen(QPen(QColor("#B8323A"), 2))
    for ribY in (38, 56, 74):
        painter.drawLine(QPointF(22, ribY), QPointF(78, ribY))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 220, 120, 120))
    painter.drawEllipse(QRectF(30, 40, 40, 36))
    drawFace(painter, QPointF(40, 52), QPointF(60, 52), 7, QColor("#2A1B3D"), QPointF(50, 66), 10, blink, laughing)


def drawAshSpirit(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#5B5566"))
    cloud = QPainterPath()
    for puffX, puffY, puffSize in ((30, 50, 22), (50, 38, 26), (70, 50, 22), (40, 66, 22), (60, 66, 22)):
        puff = QPainterPath()
        puff.addEllipse(QPointF(puffX, puffY), puffSize, puffSize)
        cloud = cloud.united(puff)
    painter.drawPath(cloud)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#FF8A3D"))
    for emberX, emberY in ((14, 24), (86, 30), (20, 86), (82, 82)):
        painter.drawEllipse(QPointF(emberX, emberY), 3, 3)
    drawFace(painter, QPointF(40, 50), QPointF(60, 50), 8, QColor("#FF6A00"), QPointF(50, 66), 11, blink, laughing)


def drawFujiGuardian(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#FFF4E0"))
    for side in (-1, 1):
        horn = QPainterPath(QPointF(50 + side * 18, 26))
        horn.quadTo(QPointF(50 + side * 34, 16), QPointF(50 + side * 30, 4))
        horn.quadTo(QPointF(50 + side * 24, 18), QPointF(50 + side * 8, 24))
        horn.closeSubpath()
        painter.drawPath(horn)
    painter.setBrush(QColor("#D9363E"))
    painter.drawEllipse(QRectF(16, 18, 68, 74))
    painter.setBrush(QColor("#F2C14E"))
    painter.drawRoundedRect(QRectF(30, 28, 40, 7), 3, 3)
    drawFace(painter, QPointF(38, 50), QPointF(62, 50), 8, QColor("#2A1B3D"), QPointF(50, 70), 14, blink, laughing)


def drawIcefallYeti(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#F4FAFF"))
    fur = QPainterPath(QPointF(50, 8))
    for step in range(1, 25):
        angle = step / 24 * math.pi * 2
        radius = 42 if step % 2 == 0 else 36
        fur.lineTo(QPointF(50 + math.sin(angle) * radius, 52 - math.cos(angle) * radius))
    fur.closeSubpath()
    painter.drawPath(fur)
    painter.setBrush(QColor("#9FD3F5"))
    painter.drawEllipse(QRectF(26, 32, 48, 44))
    drawFace(painter, QPointF(41, 48), QPointF(59, 48), 7, QColor("#1B6FC1"), QPointF(50, 63), 10, blink, laughing)
    painter.setPen(outlinePen(2))
    painter.setBrush(QColor("white"))
    for side in (-1, 1):
        tusk = QPainterPath(QPointF(50 + side * 9, 64))
        tusk.lineTo(QPointF(50 + side * 13, 76))
        tusk.lineTo(QPointF(50 + side * 5, 66))
        tusk.closeSubpath()
        painter.drawPath(tusk)


def drawDeathZoneWraith(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#6B4FC4"))
    ghost = QPainterPath(QPointF(16, 92))
    ghost.lineTo(QPointF(16, 46))
    ghost.cubicTo(QPointF(16, 6), QPointF(84, 6), QPointF(84, 46))
    ghost.lineTo(QPointF(84, 92))
    for waveNumber in range(4):
        waveRight = 84 - waveNumber * 17
        ghost.quadTo(QPointF(waveRight - 8.5, 80), QPointF(waveRight - 17, 92))
    ghost.closeSubpath()
    painter.drawPath(ghost)
    painter.setBrush(QColor("#241A4A"))
    painter.drawEllipse(QRectF(26, 26, 48, 44))
    drawFace(painter, QPointF(41, 46), QPointF(59, 46), 7, QColor("#5FE0B8"), QPointF(50, 60), 9, blink, laughing)


def drawEverestGuardian(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#F2A93B"))
    mane = QPainterPath(QPointF(50, 4))
    for step in range(1, 33):
        angle = step / 32 * math.pi * 2
        radius = 46 if step % 2 == 0 else 38
        mane.lineTo(QPointF(50 + math.sin(angle) * radius, 50 - math.cos(angle) * radius))
    mane.closeSubpath()
    painter.drawPath(mane)
    painter.setBrush(QColor("#FFF6E5"))
    painter.drawEllipse(QRectF(24, 24, 52, 52))
    drawFace(painter, QPointF(40, 46), QPointF(60, 46), 7, QColor("#2A1B3D"), QPointF(50, 64), 10, blink, laughing)
    painter.setPen(outlinePen(2))
    painter.setBrush(QColor("#E5484D"))
    painter.drawEllipse(QRectF(46, 52, 8, 6))


def drawHornliTroll(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#C9B79C"))
    for side in (-1, 1):
        horn = QPainterPath(QPointF(50 + side * 16, 24))
        horn.lineTo(QPointF(50 + side * 26, 8))
        horn.lineTo(QPointF(50 + side * 28, 26))
        horn.closeSubpath()
        painter.drawPath(horn)
    painter.setBrush(QColor("#6FB34A"))
    painter.drawEllipse(QRectF(14, 20, 72, 74))
    for side in (-1, 1):
        painter.drawEllipse(QRectF(50 + side * 38 - 8, 44, 16, 20))
    drawFace(painter, QPointF(39, 46), QPointF(61, 46), 7, QColor("#2A1B3D"), QPointF(50, 74), 13, blink, laughing)
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#5A9A38"))
    painter.drawEllipse(QRectF(42, 52, 16, 16))


def drawRidgeEagle(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#8A5A3B"))
    for featherNumber in range(3):
        feather = QPainterPath(QPointF(40 + featherNumber * 10, 22))
        feather.lineTo(QPointF(34 + featherNumber * 12, 4))
        feather.lineTo(QPointF(48 + featherNumber * 10, 20))
        feather.closeSubpath()
        painter.drawPath(feather)
    painter.drawEllipse(QRectF(16, 16, 68, 70))
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawEllipse(QRectF(24, 22, 52, 34))
    drawEye(painter, QPointF(39, 42), 7, QColor("#2A1B3D"), True, blink)
    drawEye(painter, QPointF(61, 42), 7, QColor("#2A1B3D"), True, blink)
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#FFC23D"))
    beak = QPainterPath(QPointF(38, 56))
    beak.lineTo(QPointF(62, 56))
    beak.quadTo(QPointF(58, 72), QPointF(50, 84 if not laughing else 78))
    beak.quadTo(QPointF(42, 72), QPointF(38, 56))
    painter.drawPath(beak)


def drawMatterhornKing(painter, blink, laughing):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#8C7A6E"))
    rock = QPainterPath(QPointF(10, 94))
    rock.lineTo(QPointF(42, 22))
    rock.lineTo(QPointF(56, 30))
    rock.lineTo(QPointF(90, 94))
    rock.closeSubpath()
    painter.drawPath(rock)
    painter.setBrush(QColor("#F4FAFF"))
    snow = QPainterPath(QPointF(32, 46))
    snow.lineTo(QPointF(42, 22))
    snow.lineTo(QPointF(56, 30))
    snow.lineTo(QPointF(66, 46))
    snow.lineTo(QPointF(58, 40))
    snow.lineTo(QPointF(50, 48))
    snow.lineTo(QPointF(42, 40))
    snow.closeSubpath()
    painter.drawPath(snow)
    painter.setBrush(QColor("#FFC23D"))
    crown = QPainterPath(QPointF(32, 22))
    crown.lineTo(QPointF(36, 6))
    crown.lineTo(QPointF(43, 16))
    crown.lineTo(QPointF(50, 2))
    crown.lineTo(QPointF(57, 16))
    crown.lineTo(QPointF(64, 6))
    crown.lineTo(QPointF(68, 22))
    crown.closeSubpath()
    painter.drawPath(crown)
    drawFace(painter, QPointF(40, 62), QPointF(60, 62), 7, QColor("#E5484D"), QPointF(50, 78), 11, blink, laughing)


BOSS_DRAWINGS = [
    drawLanternKeeper,
    drawAshSpirit,
    drawFujiGuardian,
    drawIcefallYeti,
    drawDeathZoneWraith,
    drawEverestGuardian,
    drawHornliTroll,
    drawRidgeEagle,
    drawMatterhornKing,
]


def drawBossCharacter(painter, bossNumber, rect, blink=False, laughing=False):
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(rect.left(), rect.top())
    painter.scale(rect.width() / 100, rect.height() / 100)
    BOSS_DRAWINGS[bossNumber % len(BOSS_DRAWINGS)](painter, blink, laughing)
    painter.restore()


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
        laughing = False
        if self.mood == "hurt" and moodSeconds < 0.6:
            offsetX = math.sin(moodSeconds * 60) * size * 0.06 * (1 - moodSeconds / 0.6)
        if self.mood == "laugh":
            laughing = True
            bob = -abs(math.sin(seconds * 9)) * size * 0.06
        if self.mood == "defeat":
            progress = min(moodSeconds / 1.1, 1.0)
            angle = progress * 540
            scale = 1 - progress * 0.85
            opacity = 1 - progress
            if progress >= 1:
                return
        blink = (seconds % 3.6) < 0.12
        painter.setOpacity(opacity)
        painter.translate(size / 2 + offsetX, size / 2 + bob)
        painter.rotate(angle)
        painter.scale(scale, scale)
        drawBossCharacter(painter, self.bossNumber, QRectF(-size * 0.45, -size * 0.45, size * 0.9, size * 0.9), blink, laughing)
        if self.mood == "hurt" and moodSeconds < 0.35:
            flash = QColor(255, 80, 80, int(140 * (1 - moodSeconds / 0.35)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(flash)
            painter.drawEllipse(QPointF(0, 0), size * 0.42, size * 0.42)
