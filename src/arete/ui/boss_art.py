import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget


OUTLINE = QColor("#1E1530")


def outlinePen(width=4):
    return QPen(OUTLINE, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)


def drawGlow(painter, center, radius, color, strength):
    glow = QRadialGradient(center, radius)
    inner = QColor(color)
    inner.setAlpha(int(200 * strength))
    outer = QColor(color)
    outer.setAlpha(0)
    glow.setColorAt(0, inner)
    glow.setColorAt(1, outer)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(glow)
    painter.drawEllipse(center, radius, radius)


def drawAngryEye(painter, center, size, eyeColor, side, mood):
    if mood["hurt"]:
        painter.setPen(outlinePen(3.5))
        painter.drawLine(QPointF(center.x() - size * 0.7, center.y() - size * 0.5), QPointF(center.x() + size * 0.7, center.y() + size * 0.5))
        painter.drawLine(QPointF(center.x() - size * 0.7, center.y() + size * 0.5), QPointF(center.x() + size * 0.7, center.y() - size * 0.5))
        return
    squint = 1.0
    if mood["blink"]:
        squint = 0.15
    elif mood["laughing"]:
        squint = 0.55
    drawGlow(painter, center, size * 1.7, eyeColor, 0.35 + 0.25 * mood["pulse"])
    eye = QPainterPath(QPointF(center.x() - size, center.y() - size * 0.55 * side * squint))
    eye.quadTo(QPointF(center.x(), center.y() + size * 1.2 * squint), QPointF(center.x() + size, center.y() + size * 0.55 * side * squint))
    eye.quadTo(QPointF(center.x(), center.y() - size * 0.35 * squint), QPointF(center.x() - size, center.y() - size * 0.55 * side * squint))
    painter.setPen(outlinePen(3))
    painter.setBrush(eyeColor.lighter(100 + int(30 * mood["pulse"])))
    painter.drawPath(eye)
    if not mood["blink"]:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 200))
        painter.drawEllipse(QPointF(center.x() - size * 0.25 * side, center.y() + size * 0.1), size * 0.18, size * 0.18)
    painter.setPen(outlinePen(4.5))
    painter.drawLine(QPointF(center.x() - size * 1.2 * side, center.y() - size * 1.1), QPointF(center.x() + size * 0.9 * side, center.y() - size * 0.25))


def drawEyes(painter, leftEye, rightEye, size, eyeColor, mood):
    drawAngryEye(painter, leftEye, size, eyeColor, 1, mood)
    drawAngryEye(painter, rightEye, size, eyeColor, -1, mood)


def drawMouth(painter, center, width, mood, fangs=True):
    painter.setPen(outlinePen(3))
    if mood["hurt"]:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        wobble = QPainterPath(QPointF(center.x() - width, center.y()))
        for step in range(1, 7):
            wobble.lineTo(QPointF(center.x() - width + step * width / 3, center.y() + (3 if step % 2 else -3)))
        painter.drawPath(wobble)
        return
    if mood["laughing"]:
        painter.setBrush(QColor("#3A0F1A"))
        mouthOpen = width * (0.6 + 0.25 * abs(math.sin(mood["time"] * 14)))
        mouth = QPainterPath(QPointF(center.x() - width, center.y()))
        mouth.quadTo(QPointF(center.x(), center.y() + mouthOpen * 1.6), QPointF(center.x() + width, center.y()))
        mouth.closeSubpath()
        painter.drawPath(mouth)
    else:
        painter.setBrush(Qt.BrushStyle.NoBrush)
        frown = QPainterPath(QPointF(center.x() - width * 0.7, center.y() + width * 0.25))
        frown.quadTo(QPointF(center.x(), center.y() - width * 0.2), QPointF(center.x() + width * 0.7, center.y() + width * 0.25))
        painter.drawPath(frown)
    if fangs:
        painter.setPen(outlinePen(1.5))
        painter.setBrush(QColor("white"))
        for side in (-1, 1):
            fang = QPainterPath(QPointF(center.x() + side * width * 0.45, center.y() + 1))
            fang.lineTo(QPointF(center.x() + side * width * 0.3, center.y() + width * 0.45))
            fang.lineTo(QPointF(center.x() + side * width * 0.15, center.y() + 1))
            fang.closeSubpath()
            painter.drawPath(fang)


def drawLanternKeeper(painter, mood):
    flicker = math.sin(mood["time"] * 11) * 2
    drawGlow(painter, QPointF(50, 55), 46, QColor("#FF5A3C"), 0.4 + 0.3 * mood["pulse"])
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#FFB23D"))
    flame = QPainterPath(QPointF(50 + flicker, 2))
    flame.quadTo(QPointF(58, 12), QPointF(50, 16))
    flame.quadTo(QPointF(42, 12), QPointF(50 + flicker, 2))
    painter.drawPath(flame)
    painter.setBrush(QColor("#2B1F2E"))
    painter.drawRoundedRect(QRectF(26, 14, 48, 12), 4, 4)
    painter.drawRoundedRect(QRectF(26, 84, 48, 12), 4, 4)
    painter.setBrush(QColor("#D8262E"))
    painter.drawEllipse(QRectF(14, 20, 72, 70))
    painter.setPen(QPen(QColor("#9E1620"), 2))
    for ribX in (30, 50, 70):
        painter.drawLine(QPointF(ribX, 23), QPointF(ribX, 87))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 170, 80, int(110 + 60 * mood["pulse"])))
    painter.drawEllipse(QRectF(32, 38, 36, 34))
    drawEyes(painter, QPointF(37, 50), QPointF(63, 50), 9, QColor("#FF2E2E"), mood)
    drawMouth(painter, QPointF(50, 70), 10, mood, False)


def drawAshSpirit(painter, mood):
    drawGlow(painter, QPointF(50, 55), 48, QColor("#3A3540"), 0.6)
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#4A4552"))
    cloud = QPainterPath()
    for index, (puffX, puffY, puffSize) in enumerate(((28, 52, 20), (50, 36, 24), (72, 50, 20), (38, 68, 20), (62, 68, 20), (50, 56, 24))):
        swell = puffSize + math.sin(mood["time"] * 2.5 + index) * 2
        puff = QPainterPath()
        puff.addEllipse(QPointF(puffX, puffY), swell, swell)
        cloud = cloud.united(puff)
    painter.drawPath(cloud)
    painter.setPen(Qt.PenStyle.NoPen)
    for index, (emberX, emberY) in enumerate(((12, 26), (88, 30), (18, 88), (84, 84))):
        rise = (mood["time"] * 8 + index * 9) % 16
        painter.setBrush(QColor(255, 130, 40, int(255 * (1 - rise / 16))))
        painter.drawEllipse(QPointF(emberX, emberY - rise), 2.5, 2.5)
    drawEyes(painter, QPointF(39, 50), QPointF(61, 50), 9, QColor("#FF8A1E"), mood)
    drawMouth(painter, QPointF(50, 67), 9, mood, False)


def drawFujiGuardian(painter, mood):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#F3E6C8"))
    for side in (-1, 1):
        horn = QPainterPath(QPointF(50 + side * 16, 26))
        horn.quadTo(QPointF(50 + side * 36, 18), QPointF(50 + side * 34, 2))
        horn.quadTo(QPointF(50 + side * 26, 16), QPointF(50 + side * 6, 22))
        horn.closeSubpath()
        painter.drawPath(horn)
    painter.setBrush(QColor(214 + int(30 * mood["pulse"]), 38, 46))
    painter.drawEllipse(QRectF(14, 18, 72, 76))
    painter.setBrush(QColor("#F2A92E"))
    painter.drawRoundedRect(QRectF(18, 30, 64, 10), 4, 4)
    drawEyes(painter, QPointF(37, 54), QPointF(63, 54), 9, QColor("#FFD21E"), mood)
    drawMouth(painter, QPointF(50, 74), 13, mood)


def drawIcefallYeti(painter, mood):
    drawGlow(painter, QPointF(50, 50), 48, QColor("#7FD8FF"), 0.3 + 0.3 * mood["pulse"])
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#E8F4FF"))
    spin = mood["time"] * 0.6
    spikes = QPainterPath()
    for step in range(25):
        angle = step / 24 * math.pi * 2 + spin
        radius = 44 if step % 2 == 0 else 36
        point = QPointF(50 + math.sin(angle) * radius, 50 - math.cos(angle) * radius)
        if step == 0:
            spikes.moveTo(point)
        else:
            spikes.lineTo(point)
    painter.drawPath(spikes)
    painter.setBrush(QColor("#8ECDF2"))
    painter.drawEllipse(QRectF(22, 22, 56, 56))
    drawEyes(painter, QPointF(39, 48), QPointF(61, 48), 9, QColor("#1747C9"), mood)
    drawMouth(painter, QPointF(50, 66), 9, mood, False)


def drawDeathZoneWraith(painter, mood):
    drawGlow(painter, QPointF(50, 50), 50, QColor("#9B6BFF"), 0.35 + 0.3 * mood["pulse"])
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#6E44D6"))
    wave = math.sin(mood["time"] * 5) * 4
    ghost = QPainterPath(QPointF(14, 90))
    ghost.lineTo(QPointF(14, 46))
    ghost.cubicTo(QPointF(14, 4), QPointF(86, 4), QPointF(86, 46))
    ghost.lineTo(QPointF(86, 90))
    for waveNumber in range(4):
        waveRight = 86 - waveNumber * 18
        tip = 78 + (wave if waveNumber % 2 else -wave)
        ghost.quadTo(QPointF(waveRight - 9, tip), QPointF(waveRight - 18, 90))
    ghost.closeSubpath()
    painter.drawPath(ghost)
    drawEyes(painter, QPointF(38, 44), QPointF(62, 44), 9, QColor("#FF5AE0"), mood)
    drawMouth(painter, QPointF(50, 62), 8, mood)


def drawStormCloud(painter, offsetX, offsetY, scale, mood):
    cloud = QPainterPath()
    for puffX, puffY, puffSize in ((-14, 4, 12), (0, -4, 15), (14, 4, 12)):
        puff = QPainterPath()
        puff.addEllipse(QPointF(offsetX + puffX * scale, offsetY + puffY * scale), puffSize * scale, puffSize * scale)
        cloud = cloud.united(puff)
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#F2F6FF"))
    painter.drawPath(cloud)
    drawEyes(painter, QPointF(offsetX - 7 * scale, offsetY + 2 * scale), QPointF(offsetX + 7 * scale, offsetY + 2 * scale), 5 * scale, QColor("#2C6BE0"), mood)


def drawEverestGuardian(painter, mood):
    painter.setPen(QPen(QColor("#2E9BFF"), 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for drop in range(6):
        fall = (mood["time"] * 40 + drop * 7) % 22
        dropX = 26 + drop * 10
        painter.drawLine(QPointF(dropX - fall * 0.3, 66 + fall), QPointF(dropX - fall * 0.3 - 2, 72 + fall))
    if mood["pulse"] > 0.85:
        painter.setPen(QPen(QColor("#FFE14A"), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        bolt = QPainterPath(QPointF(52, 60))
        bolt.lineTo(QPointF(46, 74))
        bolt.lineTo(QPointF(54, 74))
        bolt.lineTo(QPointF(48, 90))
        painter.drawPath(bolt)
    drift = math.sin(mood["time"] * 1.5) * 3
    drawStormCloud(painter, 34 + drift, 40, 1.25, mood)
    drawStormCloud(painter, 66 - drift, 52, 1.25, mood)


def drawHornliTroll(painter, mood):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#1E1E1E"))
    for side in (-1, 1):
        horn = QPainterPath(QPointF(50 + side * 18, 30))
        horn.quadTo(QPointF(50 + side * 40, 24), QPointF(50 + side * 42, 6))
        horn.quadTo(QPointF(50 + side * 32, 22), QPointF(50 + side * 10, 22))
        horn.closeSubpath()
        painter.drawPath(horn)
    painter.setBrush(QColor("#2FA51E"))
    painter.drawEllipse(QRectF(14, 18, 72, 76))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#4BD236"))
    painter.drawEllipse(QRectF(26, 24, 30, 16))
    drawEyes(painter, QPointF(37, 54), QPointF(63, 54), 10, QColor("#E8F01E"), mood)
    drawMouth(painter, QPointF(50, 76), 12, mood)


def drawRidgeEagle(painter, mood):
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#8A5530"))
    tuftLift = math.sin(mood["time"] * 4) * 3
    for side in (-1, 1):
        tuft = QPainterPath(QPointF(50 + side * 12, 22))
        tuft.lineTo(QPointF(50 + side * 34, 4 - tuftLift))
        tuft.lineTo(QPointF(50 + side * 32, 28))
        tuft.closeSubpath()
        painter.drawPath(tuft)
    painter.drawEllipse(QRectF(14, 14, 72, 80))
    painter.setBrush(QColor("#F3E9DA"))
    face = QPainterPath(QPointF(50, 40))
    face.cubicTo(QPointF(30, 28), QPointF(16, 50), QPointF(30, 66))
    face.cubicTo(QPointF(40, 76), QPointF(50, 86), QPointF(50, 90))
    face.cubicTo(QPointF(50, 86), QPointF(60, 76), QPointF(70, 66))
    face.cubicTo(QPointF(84, 50), QPointF(70, 28), QPointF(50, 40))
    painter.drawPath(face)
    drawEyes(painter, QPointF(37, 52), QPointF(63, 52), 9, QColor("#FFB21E"), mood)
    painter.setPen(outlinePen(2.5))
    painter.setBrush(QColor("#F2A21E"))
    beakOpen = 5 if mood["laughing"] else 0
    beak = QPainterPath(QPointF(44, 60))
    beak.lineTo(QPointF(56, 60))
    beak.lineTo(QPointF(50, 74 + beakOpen))
    beak.closeSubpath()
    painter.drawPath(beak)


def drawMatterhornKing(painter, mood):
    drawGlow(painter, QPointF(50, 20), 30, QColor("#FFD23D"), 0.3 + 0.4 * mood["pulse"])
    painter.setPen(outlinePen(3))
    painter.setBrush(QColor("#F4DBC0"))
    painter.drawEllipse(QRectF(16, 24, 68, 72))
    painter.setBrush(QColor("#FFC21E"))
    crown = QPainterPath(QPointF(18, 34))
    crown.lineTo(QPointF(20, 8))
    crown.lineTo(QPointF(35, 20))
    crown.lineTo(QPointF(50, 2))
    crown.lineTo(QPointF(65, 20))
    crown.lineTo(QPointF(80, 8))
    crown.lineTo(QPointF(82, 34))
    crown.closeSubpath()
    painter.drawPath(crown)
    painter.setPen(outlinePen(2))
    for gemX, gemY, gemColor in ((20, 8, "#E23B3B"), (50, 3, "#2E7BFF"), (80, 8, "#2FBF4A"), (50, 26, "#E23B3B")):
        painter.setBrush(QColor(gemColor).lighter(100 + int(40 * mood["pulse"])))
        painter.drawEllipse(QPointF(gemX, gemY), 4, 4)
    drawEyes(painter, QPointF(37, 58), QPointF(63, 58), 9, QColor("#1E1530"), mood)
    drawMouth(painter, QPointF(50, 80), 11, mood)


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


def drawBossCharacter(painter, bossNumber, rect, blink=False, laughing=False, hurt=False, seconds=None):
    if seconds is None:
        seconds = time.time()
    mood = {
        "time": seconds,
        "blink": blink,
        "laughing": laughing,
        "hurt": hurt,
        "pulse": (math.sin(seconds * 3) + 1) / 2,
    }
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(rect.left(), rect.top())
    painter.scale(rect.width() / 100, rect.height() / 100)
    BOSS_DRAWINGS[bossNumber % len(BOSS_DRAWINGS)](painter, mood)
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
        hurting = False
        if self.mood == "hurt" and moodSeconds < 0.8:
            offsetX = math.sin(moodSeconds * 60) * size * 0.06 * (1 - moodSeconds / 0.8)
            hurting = True
        if self.mood == "laugh":
            laughing = True
            bob = -abs(math.sin(seconds * 9)) * size * 0.06
        if self.mood == "defeat":
            hurting = True
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
        drawBossCharacter(painter, self.bossNumber, QRectF(-size * 0.45, -size * 0.45, size * 0.9, size * 0.9), blink, laughing, hurting, seconds)
        if hurting and moodSeconds < 0.35:
            flash = QColor(255, 80, 80, int(140 * (1 - moodSeconds / 0.35)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(flash)
            painter.drawEllipse(QPointF(0, 0), size * 0.42, size * 0.42)
