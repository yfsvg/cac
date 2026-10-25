import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRegion, QTransform
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget

from arete.core import climbing, mountains
from arete.ui import animations, mountain_art
from arete.ui.boss_art import drawBossCharacter
from arete.ui.boss_fight import bossName
from arete.ui.theme import getColors

CLIMB_STYLE = """
    QPushButton#MountainTab {
        color: @onSurfaceVariant;
        font-size: 13px;
        font-weight: 600;
        background-color: @surfaceContainerHigh;
        border: none;
        border-radius: 15px;
        padding: 7px 16px;
    }
    QPushButton#MountainTab:hover { background-color: @surfaceContainerHighest; }
    QPushButton#MountainTab:checked { color: @onPrimary; background-color: @primary; }
    QPushButton#MountainTab[locked="true"] { color: @outline; }
    QPushButton#MountainTab[locked="true"]:checked { color: @onPrimary; }
    QLabel#MapTitle { color: @onSurface; font-size: 18px; font-weight: 700; }
    QFrame#ClimbCard { background-color: @surfaceContainerLow; border-radius: 24px; border: 1px solid @cardBorder; }
    QLabel#ClimbLine { color: @primary; font-size: 13px; font-weight: 700; }
    QPushButton#OpenMap {
        color: @onPrimary;
        font-size: 13px;
        font-weight: 600;
        background-color: @primary;
        border: none;
        border-bottom: 3px solid @primaryShadow;
        border-radius: 14px;
        padding: 6px 14px;
    }
    QLabel#MapStage { color: @onSurface; font-size: 17px; font-weight: 800; }
    QLabel#MapPercent {
        color: @onPrimaryContainer;
        background-color: @primaryContainer;
        font-size: 13px;
        font-weight: 700;
        border-radius: 11px;
        padding: 3px 10px;
    }
    QLabel#MapInfo { color: @onSurfaceVariant; font-size: 13px; }
    QLabel#MapPercentDone {
        color: #173D08;
        background-color: #7BE3A0;
        font-size: 13px;
        font-weight: 800;
        border-radius: 11px;
        padding: 3px 10px;
    }
    QLabel#MapPercentLocked {
        color: @onSurfaceVariant;
        background-color: @surfaceContainerHighest;
        font-size: 13px;
        font-weight: 800;
        border-radius: 11px;
        padding: 3px 10px;
    }
    QProgressBar#MapBar { background-color: @surfaceContainerHighest; border: none; border-radius: 4px; }
    QProgressBar#MapBar::chunk { background-color: @trail; border-radius: 4px; }
    QPushButton#OpenMap:hover { background-color: @primaryHover; }
    QPushButton#OpenMap:pressed { border-bottom: 1px solid @primaryShadow; padding-top: 8px; }
"""

NODE_RADIUS = 13
MAP_ZOOM = 0.8
BOSS_RADIUS = 19


def climbSummary(state):
    mountain = mountains.MOUNTAINS[state["mountainNumber"]]
    return percentText(state["percent"]) + "% up " + mountain["name"]


def percentText(percent):
    return format(percent, ".1f").rstrip("0").rstrip(".")


def drawCheck(painter, center, size, color):
    painter.setPen(QPen(color, size * 0.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    check = QPainterPath(QPointF(center.x() - size * 0.45, center.y()))
    check.lineTo(QPointF(center.x() - size * 0.1, center.y() + size * 0.35))
    check.lineTo(QPointF(center.x() + size * 0.5, center.y() - size * 0.35))
    painter.drawPath(check)


def shieldPath(center, size):
    shield = QPainterPath(QPointF(center.x() - size, center.y() - size * 0.75))
    shield.quadTo(QPointF(center.x(), center.y() - size * 1.1), QPointF(center.x() + size, center.y() - size * 0.75))
    shield.lineTo(QPointF(center.x() + size, center.y() + size * 0.1))
    shield.quadTo(QPointF(center.x() + size * 0.9, center.y() + size * 0.8), QPointF(center.x(), center.y() + size * 1.15))
    shield.quadTo(QPointF(center.x() - size * 0.9, center.y() + size * 0.8), QPointF(center.x() - size, center.y() + size * 0.1))
    shield.closeSubpath()
    return shield


def drawLock(painter, center, size, color):
    painter.setPen(QPen(color, size * 0.18))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(center.x() - size * 0.38, center.y() - size * 0.85, size * 0.76, size * 0.9), 0, 180 * 16)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(QRectF(center.x() - size * 0.55, center.y() - size * 0.4, size * 1.1, size * 0.9), size * 0.15, size * 0.15)


class MountainMap(QWidget):
    def __init__(self):
        super().__init__()
        self.mountainNumber = 0
        self.state = climbing.climbState()
        self.bottomPad = 80
        self.showLabels = True
        self.zoom = 1.0
        self.shownPercent = None
        self.picture = None
        self.pictureKey = None
        self.bottomColor = QColor("#2A1F4A")
        self.startTime = time.time()
        self.sky = mountain_art.Sky()
        self.animationTimer = QTimer(self, interval=40, timeout=self.animate)

    def scene(self):
        return mountain_art.sceneFor(mountains.MOUNTAINS[self.mountainNumber]["picture"])

    def showMountain(self, mountainNumber):
        self.mountainNumber = mountainNumber
        self.state = climbing.climbState()
        self.shownPercent = self.realPercent()
        self.sky = mountain_art.Sky()
        self.update()

    def refresh(self):
        oldPercent = self.percentHere()
        self.state = climbing.climbState()
        newPercent = self.realPercent()
        if self.shownPercent is not None and abs(newPercent - oldPercent) > 0.001:
            animations.animateValue(oldPercent, newPercent, self.setShownPercent, 1200)
        else:
            self.shownPercent = newPercent
        self.update()

    def setShownPercent(self, percent):
        self.shownPercent = percent
        self.update()

    def scale(self):
        return self.width() * self.zoom / mountain_art.PICTURE_WIDTH

    def offsetX(self):
        return (self.width() - mountain_art.PICTURE_WIDTH * self.scale()) / 2

    def topCrop(self):
        return mountains.MOUNTAINS[self.mountainNumber]["topCrop"]

    def pictureHeight(self):
        return int((mountain_art.PICTURE_HEIGHT - self.topCrop()) * self.scale())

    def setBottomPad(self, bottomPad):
        self.bottomPad = bottomPad
        self.updateHeight()

    def updateHeight(self):
        if self.width() > 0:
            self.setFixedHeight(self.pictureHeight() + self.bottomPad)

    def resizeEvent(self, event):
        self.updateHeight()
        super().resizeEvent(event)

    def showEvent(self, event):
        self.animationTimer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.animationTimer.stop()
        super().hideEvent(event)

    def seconds(self):
        return time.time() - self.startTime

    def visiblePictureRange(self):
        visibleRect = self.visibleRegion().boundingRect()
        return visibleRect.top() / self.scale() + self.topCrop(), visibleRect.bottom() / self.scale() + self.topCrop()

    def animate(self):
        if self.width() == 0:
            return
        visibleTop, visibleBottom = self.visiblePictureRange()
        self.sky.update(self.seconds(), visibleTop, visibleBottom)
        self.update(self.visibleRegion().boundingRect())

    def percentHere(self):
        if self.shownPercent is not None and self.mountainNumber == self.state["mountainNumber"]:
            return self.shownPercent
        return self.realPercent()

    def realPercent(self):
        if self.mountainNumber < self.state["mountainNumber"]:
            return 100
        if self.mountainNumber > self.state["mountainNumber"]:
            return 0
        return self.state["percent"]

    def onScreen(self, picturePoint):
        return QPointF(self.offsetX() + picturePoint.x() * self.scale(), (picturePoint.y() - self.topCrop()) * self.scale())

    def markerPoint(self):
        scene = self.scene()
        return self.onScreen(scene.trail.pointAtPercent(scene.trailFraction(self.percentHere())))

    def basePicture(self):
        pixelRatio = self.devicePixelRatioF()
        key = (self.width(), self.height(), self.mountainNumber, pixelRatio)
        if self.picture is None or self.pictureKey != key:
            self.picture = QPixmap(int(self.width() * pixelRatio), int(self.height() * pixelRatio))
            self.picture.setDevicePixelRatio(pixelRatio)
            self.picture.fill(Qt.GlobalColor.transparent)
            picturePainter = QPainter(self.picture)
            picturePainter.setRenderHint(QPainter.RenderHint.Antialiasing)
            fullHeight = mountain_art.PICTURE_HEIGHT * self.scale()
            self.scene().renderer.render(picturePainter, QRectF(0, -self.topCrop() * self.scale(), self.width(), fullHeight))
            if self.zoom < 1:
                picturePainter.save()
                picturePainter.scale(self.width() / mountain_art.PICTURE_WIDTH, self.scale())
                picturePainter.translate(0, -self.topCrop())
                mountain_art.paintTrees(picturePainter, self.scene(), 0, 0, mountain_art.PICTURE_HEIGHT)
                picturePainter.restore()
                pictureWidth = int(mountain_art.PICTURE_WIDTH * self.scale())
                middle = QPixmap(int(pictureWidth * pixelRatio), int(self.height() * pixelRatio))
                middle.setDevicePixelRatio(pixelRatio)
                middle.fill(Qt.GlobalColor.transparent)
                middlePainter = QPainter(middle)
                middlePainter.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.scene().renderer.render(middlePainter, QRectF(0, -self.topCrop() * self.scale(), pictureWidth, fullHeight))
                fade = QLinearGradient(0, 0, pictureWidth, 0)
                fade.setColorAt(0, QColor(0, 0, 0, 0))
                fade.setColorAt(30 / pictureWidth, QColor(0, 0, 0, 255))
                fade.setColorAt(1 - 30 / pictureWidth, QColor(0, 0, 0, 255))
                fade.setColorAt(1, QColor(0, 0, 0, 0))
                middlePainter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                middlePainter.fillRect(QRectF(0, 0, pictureWidth, self.height()), fade)
                middlePainter.end()
                picturePainter.drawPixmap(int(self.offsetX()), 0, middle)
            picturePainter.end()
            self.bottomColor = self.picture.toImage().pixelColor(int(4 * pixelRatio), int((self.pictureHeight() - 3) * pixelRatio))
            picturePainter = QPainter(self.picture)
            picturePainter.fillRect(QRectF(0, self.pictureHeight() - 1, self.width(), self.bottomPad + 2), self.bottomColor)
            picturePainter.end()
            self.pictureKey = key
        return self.picture

    def paintEvent(self, event):
        if self.width() == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(event.rect())
        painter.drawPixmap(0, 0, self.basePicture())
        scene = self.scene()
        seconds = self.seconds()
        visibleTop = event.rect().top() / self.scale() + self.topCrop()
        visibleBottom = event.rect().bottom() / self.scale() + self.topCrop()

        painter.save()
        painter.translate(self.offsetX(), 0)
        painter.scale(self.scale(), self.scale())
        painter.translate(0, -self.topCrop())
        mountain_art.paintTrees(painter, scene, seconds, visibleTop, visibleBottom)
        self.sky.paint(painter, seconds)
        painter.restore()

        colors = getColors()
        percentHere = self.percentHere()
        if percentHere > 0:
            walked = mountain_art.partOfPath(scene.trail, scene.trailFraction(percentHere))
            walked = QTransform().translate(self.offsetX(), 0).scale(self.scale(), self.scale()).translate(0, -self.topCrop()).map(walked)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(colors["trailShadow"]), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(walked.translated(0, 2))
            painter.setPen(QPen(QColor(colors["trail"]), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(walked)

        labelFont = QFont(self.font())
        labelFont.setPixelSize(12)
        labelFont.setBold(True)
        painter.setFont(labelFont)
        mountain = mountains.MOUNTAINS[self.mountainNumber]
        bossesBefore = self.mountainNumber * len(mountains.BOSS_CHECKPOINTS)
        climberPoint = None
        if self.mountainNumber == self.state["mountainNumber"]:
            climberPoint = self.markerPoint()
        for checkpointNumber in range(mountains.CHECKPOINT_COUNT):
            nodePoint = self.onScreen(scene.rings[checkpointNumber])
            underClimber = climberPoint is not None and (nodePoint.x() - climberPoint.x()) ** 2 + (nodePoint.y() - climberPoint.y()) ** 2 < 24 ** 2
            reached = percentHere >= mountains.checkpointPercent(checkpointNumber) - 0.001
            stageText = mountain["stages"][checkpointNumber][0]
            if checkpointNumber in mountains.BOSS_CHECKPOINTS:
                bossNumber = bossesBefore + mountains.BOSS_CHECKPOINTS.index(checkpointNumber)
                isNextBoss = bossNumber == self.state["bossesBeaten"]
                if not underClimber:
                    self.drawBoss(painter, nodePoint, bossNumber < self.state["bossesBeaten"], colors, seconds, isNextBoss, bossNumber)
                self.drawLabel(painter, stageText + "  ·  " + bossName(bossNumber), nodePoint, BOSS_RADIUS + 10)
            else:
                if reached and not underClimber:
                    self.drawDoneNode(painter, nodePoint, colors)
                self.drawLabel(painter, stageText, nodePoint, NODE_RADIUS + 10)

        if self.mountainNumber == self.state["mountainNumber"]:
            self.drawClimber(painter, self.markerPoint(), colors, seconds)
        if self.mountainNumber > self.state["mountainNumber"]:
            self.drawLocked(painter)
        painter.end()

    def drawDoneNode(self, painter, point, colors):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colors["trailShadow"]))
        painter.drawEllipse(QPointF(point.x(), point.y() + 3), NODE_RADIUS, NODE_RADIUS)
        painter.setPen(QPen(QColor("white"), 2.5))
        painter.setBrush(QColor(colors["trail"]))
        painter.drawEllipse(point, NODE_RADIUS, NODE_RADIUS)
        drawCheck(painter, point, NODE_RADIUS * 0.9, QColor("white"))

    def drawBoss(self, painter, point, beaten, colors, seconds, isNextBoss, bossNumber):
        shieldColor = QColor(colors["boss"])
        if beaten:
            shieldColor = QColor(colors["trail"])
        shieldSize = BOSS_RADIUS
        if isNextBoss and not beaten:
            beat = (math.sin(seconds * 4) + 1) / 2
            shieldSize = BOSS_RADIUS * (1 + 0.1 * beat)
            glowColor = QColor(shieldColor)
            glowColor.setAlpha(int(40 + 70 * beat))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glowColor)
            painter.drawEllipse(point, BOSS_RADIUS + 10 + 6 * beat, BOSS_RADIUS + 10 + 6 * beat)
        if not beaten:
            badgeSize = shieldSize + 5
            painter.setPen(QPen(shieldColor, 3))
            painter.setBrush(QColor("#FFF6EE"))
            painter.drawEllipse(point, badgeSize, badgeSize)
            faceSize = badgeSize * 1.7
            drawBossCharacter(painter, bossNumber, QRectF(point.x() - faceSize / 2, point.y() - faceSize / 2, faceSize, faceSize))
            return
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shieldColor.darker(135))
        painter.drawPath(shieldPath(QPointF(point.x(), point.y() + 3), shieldSize))
        painter.setPen(QPen(QColor("white"), 2.5))
        painter.setBrush(shieldColor)
        painter.drawPath(shieldPath(point, shieldSize))
        drawCheck(painter, point, shieldSize * 0.8, QColor("white"))

    def drawLabel(self, painter, text, point, gap):
        if not self.showLabels:
            return
        textWidth = painter.fontMetrics().horizontalAdvance(text) + 20
        pillHeight = 24
        if point.x() < self.width() / 2:
            pillRect = QRectF(point.x() + gap, point.y() - pillHeight / 2, textWidth, pillHeight)
        else:
            pillRect = QRectF(point.x() - gap - textWidth, point.y() - pillHeight / 2, textWidth, pillHeight)
        if pillRect.left() < 6:
            pillRect.moveLeft(6)
        if pillRect.right() > self.width() - 6:
            pillRect.moveRight(self.width() - 6)
        pill = QPainterPath()
        pill.addRoundedRect(pillRect, 12, 12)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(pill, QColor(20, 16, 40, 175))
        painter.setPen(QColor("white"))
        painter.drawText(pillRect, Qt.AlignmentFlag.AlignCenter, text)

    def drawClimber(self, painter, point, colors, seconds):
        pulse = math.sin(seconds * 2.4)
        accentColor = QColor(colors["primary"])
        glowColor = QColor(accentColor)
        glowColor.setAlpha(int(70 + 50 * pulse))
        glowSize = 26 + 5 * pulse
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(glowColor)
        painter.drawEllipse(point, glowSize, glowSize)
        point = QPointF(point.x(), point.y() - abs(math.sin(seconds * 3)) * 5)
        painter.setPen(QPen(QColor("white"), 4))
        painter.setBrush(accentColor)
        painter.drawEllipse(point, 14, 14)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(QPointF(point.x(), point.y() - 3), 4, 4)
        body = QPainterPath(QPointF(point.x() - 6, point.y() + 7))
        body.quadTo(QPointF(point.x(), point.y() - 2), QPointF(point.x() + 6, point.y() + 7))
        body.closeSubpath()
        painter.drawPath(body)

    def drawLocked(self, painter):
        painter.fillRect(self.rect(), QColor(10, 8, 30, 140))


def drawTrophy(painter, center, size, color):
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    cup = QPainterPath(QPointF(center.x() - size * 0.55, center.y() - size * 0.6))
    cup.lineTo(QPointF(center.x() + size * 0.55, center.y() - size * 0.6))
    cup.quadTo(QPointF(center.x() + size * 0.55, center.y() + size * 0.25), QPointF(center.x(), center.y() + size * 0.3))
    cup.quadTo(QPointF(center.x() - size * 0.55, center.y() + size * 0.25), QPointF(center.x() - size * 0.55, center.y() - size * 0.6))
    painter.drawPath(cup)
    painter.drawRect(QRectF(center.x() - size * 0.1, center.y() + size * 0.25, size * 0.2, size * 0.3))
    painter.drawRoundedRect(QRectF(center.x() - size * 0.4, center.y() + size * 0.5, size * 0.8, size * 0.18), 3, 3)
    painter.setPen(QPen(color, size * 0.12))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(center.x() - size * 0.85, center.y() - size * 0.5, size * 0.5, size * 0.5), 90 * 16, 180 * 16)
    painter.drawArc(QRectF(center.x() + size * 0.35, center.y() - size * 0.5, size * 0.5, size * 0.5), 270 * 16, 180 * 16)


class MapBanner(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.kind = "locked"
        self.title = ""
        self.detail = ""
        self.setFixedHeight(150)

    def showBanner(self, kind, title, detail):
        wasHidden = self.isHidden() or self.title != title
        self.kind = kind
        self.title = title
        self.detail = detail
        self.show()
        self.raise_()
        self.update()
        if wasHidden:
            animations.fadeIn(self, 350)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cardRect = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        card = QPainterPath()
        card.addRoundedRect(cardRect, 26, 26)
        if self.kind == "done":
            backColor = QColor("#FFC23D")
            edgeColor = QColor("#D99A0B")
            textColor = QColor("#4A3300")
        else:
            backColor = QColor(20, 16, 50, 235)
            edgeColor = QColor(255, 255, 255, 90)
            textColor = QColor("white")
        painter.fillPath(card.translated(0, 4), edgeColor)
        painter.fillPath(card, backColor)
        painter.setPen(QPen(edgeColor, 2))
        painter.drawPath(card)
        iconCenter = QPointF(cardRect.center().x(), cardRect.top() + 38)
        if self.kind == "done":
            drawTrophy(painter, iconCenter, 28, textColor)
        else:
            drawLock(painter, iconCenter, 26, textColor)
        titleFont = QFont(self.font())
        titleFont.setPixelSize(20)
        titleFont.setBold(True)
        painter.setFont(titleFont)
        painter.setPen(textColor)
        painter.drawText(QRectF(cardRect.left(), cardRect.top() + 64, cardRect.width(), 30), Qt.AlignmentFlag.AlignCenter, self.title)
        detailFont = QFont(self.font())
        detailFont.setPixelSize(13)
        painter.setFont(detailFont)
        painter.drawText(QRectF(cardRect.left() + 12, cardRect.top() + 94, cardRect.width() - 24, 36), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.detail)


class MapFrame(QWidget):
    def __init__(self, whenResized):
        super().__init__()
        self.whenResized = whenResized

    def resizeEvent(self, event):
        self.whenResized()
        super().resizeEvent(event)


class MiniMap(QScrollArea):
    def __init__(self):
        super().__init__(widgetResizable=True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedHeight(150)
        self.mountainMap = MountainMap()
        self.mountainMap.showLabels = False
        self.setWidget(self.mountainMap)

    def wheelEvent(self, event):
        event.ignore()

    def refresh(self):
        mountainNumber = climbing.climbState()["mountainNumber"]
        if mountainNumber == self.mountainMap.mountainNumber and self.mountainMap.shownPercent is not None:
            self.mountainMap.refresh()
        else:
            self.mountainMap.showMountain(mountainNumber)
        QTimer.singleShot(0, self.centerOnClimber)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.centerOnClimber)

    def centerOnClimber(self):
        scrollBar = self.verticalScrollBar()
        targetValue = int(self.mountainMap.markerPoint().y() - self.viewport().height() / 2)
        scrollBar.setValue(max(0, min(targetValue, scrollBar.maximum())))


class ClimbCard(QFrame):
    def __init__(self, openMap):
        super().__init__(objectName="ClimbCard")
        cardLayout = QVBoxLayout(self)
        cardLayout.setContentsMargins(12, 12, 12, 12)
        cardLayout.setSpacing(10)
        self.miniMap = MiniMap()
        cardLayout.addWidget(self.miniMap)
        bottomRow = QHBoxLayout()
        bottomRow.setContentsMargins(6, 0, 0, 0)
        self.summaryLabel = QLabel("", objectName="ClimbLine")
        self.shownPercent = None
        self.shownMountain = None
        bottomRow.addWidget(self.summaryLabel)
        bottomRow.addStretch()
        openButton = QPushButton("Open map", objectName="OpenMap", cursor=Qt.CursorShape.PointingHandCursor)
        openButton.clicked.connect(openMap)
        bottomRow.addWidget(openButton)
        cardLayout.addLayout(bottomRow)

    def refresh(self):
        state = climbing.climbState()
        mountainName = mountains.MOUNTAINS[state["mountainNumber"]]["name"]
        if self.shownPercent is None or self.shownMountain != mountainName:
            self.summaryLabel.setText(climbSummary(state))
        else:
            animations.animateValue(self.shownPercent, state["percent"], lambda value: self.summaryLabel.setText(percentText(value) + "% up " + mountainName), 1200)
        self.shownPercent = state["percent"]
        self.shownMountain = mountainName
        self.miniMap.refresh()


class MapArrowButton(QPushButton):
    def __init__(self, direction):
        super().__init__(objectName="MapArrow", cursor=Qt.CursorShape.PointingHandCursor)
        self.direction = direction
        self.setFixedSize(40, 40)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        backColor = QColor(20, 16, 40, 170)
        if self.underMouse():
            backColor = QColor(20, 16, 40, 220)
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        painter.setBrush(backColor)
        painter.drawEllipse(QRectF(1, 1, 38, 38))
        painter.setPen(QPen(QColor("white"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        middle = QPointF(20 + self.direction * 2, 20)
        painter.drawLine(QPointF(middle.x() - self.direction * 5, 13), middle)
        painter.drawLine(QPointF(middle.x() - self.direction * 5, 27), middle)

    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)


class MapHome(QWidget):
    def __init__(self, goBack):
        super().__init__()
        from arete.ui.settings_window import makeBackArrow

        self.viewedMountain = climbing.climbState()["mountainNumber"]
        pageLayout = QVBoxLayout(self)
        pageLayout.setContentsMargins(20, 6, 20, 12)
        pageLayout.setSpacing(10)

        topRow = QHBoxLayout()
        backButton = QPushButton(objectName="ThemeButton", cursor=Qt.CursorShape.PointingHandCursor)
        backButton.setFixedSize(32, 32)
        backButton.setIcon(makeBackArrow())
        backButton.clicked.connect(goBack)
        topRow.addWidget(backButton)
        topRow.addSpacing(6)
        self.titleLabel = QLabel("", objectName="MapTitle")
        topRow.addWidget(self.titleLabel)
        topRow.addStretch()
        pageLayout.addLayout(topRow)


        infoCard = QFrame(objectName="ClimbCard")
        infoLayout = QVBoxLayout(infoCard)
        infoLayout.setContentsMargins(14, 10, 14, 10)
        infoLayout.setSpacing(4)
        stageRow = QHBoxLayout()
        self.stageLabel = QLabel("", objectName="MapStage")
        stageRow.addWidget(self.stageLabel)
        stageRow.addStretch()
        self.percentLabel = QLabel("", objectName="MapPercent")
        stageRow.addWidget(self.percentLabel)
        infoLayout.addLayout(stageRow)
        self.metersLabel = QLabel("", objectName="MapInfo")
        infoLayout.addWidget(self.metersLabel)
        self.progressBar = QProgressBar(objectName="MapBar")
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(8)
        self.progressBar.setRange(0, 1000)
        infoLayout.addWidget(self.progressBar)
        self.goalLabel = QLabel("", objectName="MapInfo")
        infoLayout.addWidget(self.goalLabel)
        pageLayout.addWidget(infoCard)

        self.mapFrame = MapFrame(self.placeMap)
        pageLayout.addWidget(self.mapFrame, 1)
        self.scrollArea = QScrollArea(self.mapFrame, widgetResizable=True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sideBar = self.scrollArea.horizontalScrollBar()
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sideBar.rangeChanged.connect(lambda lowest, highest: sideBar.setRange(0, 0) if highest > 0 else None)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.mountainMap = MountainMap()
        self.mountainMap.zoom = MAP_ZOOM
        self.scrollArea.setWidget(self.mountainMap)
        self.banner = MapBanner()
        self.banner.setParent(self.mapFrame)
        self.banner.hide()
        self.leftArrow = MapArrowButton(-1)
        self.leftArrow.setParent(self.mapFrame)
        self.leftArrow.clicked.connect(lambda: self.switchMountain(self.viewedMountain - 1))
        self.rightArrow = MapArrowButton(1)
        self.rightArrow.setParent(self.mapFrame)
        self.rightArrow.clicked.connect(lambda: self.switchMountain(self.viewedMountain + 1))
        self.needsFirstScroll = True
        self.switchMountain(self.viewedMountain, False)

    def placeMap(self):
        mapWidth = self.mapFrame.width()
        self.scrollArea.setGeometry(0, 0, mapWidth, self.mapFrame.height())
        arrowY = self.mapFrame.height() // 2 - 20
        self.leftArrow.move(10, arrowY)
        self.rightArrow.move(mapWidth - 50, arrowY)
        self.banner.setFixedWidth(mapWidth - 110)
        bannerY = self.mapFrame.height() // 2 - 75
        if self.banner.kind == "done":
            bannerY = 24
        self.banner.move(55, bannerY)
        roundedShape = QPainterPath()
        roundedShape.addRoundedRect(QRectF(0, 0, mapWidth, self.mapFrame.height()), 24, 24)
        self.scrollArea.setMask(QRegion(roundedShape.toFillPolygon().toPolygon()))
        if self.needsFirstScroll and self.mapFrame.height() > 100:
            self.needsFirstScroll = False
            QTimer.singleShot(50, lambda: self.scrollToClimber(900))

    def refresh(self):
        self.mountainMap.refresh()
        self.updateInfo()

    def updateInfo(self):
        state = climbing.climbState()
        mountain = mountains.MOUNTAINS[self.viewedMountain]
        bossesHere = state["bossesBeaten"] - self.viewedMountain * len(mountains.BOSS_CHECKPOINTS)
        bossesHere = max(0, min(bossesHere, len(mountains.BOSS_CHECKPOINTS)))
        bossText = "Bosses beaten " + str(bossesHere) + " of " + str(len(mountains.BOSS_CHECKPOINTS))
        percent = state["percent"]
        if self.viewedMountain < state["mountainNumber"]:
            percent = 100
        if self.viewedMountain > state["mountainNumber"]:
            percent = 0
        stageNumber = mountains.stageNumber(percent)
        stageText = "Trailhead"
        if stageNumber >= 0:
            stageText = mountain["stages"][stageNumber][0]
        heightText = format(int(mountain["heightMeters"] * percent / 100), ",") + " m of " + format(mountain["heightMeters"], ",") + " m"
        self.stageLabel.setText(stageText)
        self.percentLabel.setText(percentText(percent) + "%")
        self.metersLabel.setText(heightText + "  ·  " + bossText)
        animations.animateValue(self.progressBar.value(), int(percent * 10), lambda value: self.progressBar.setValue(int(value)), 700)
        isDone = self.viewedMountain < state["mountainNumber"] or (self.viewedMountain == state["mountainNumber"] and state["finished"])
        isLocked = self.viewedMountain > state["mountainNumber"]
        pillName = "MapPercent"
        if isDone:
            pillName = "MapPercentDone"
            self.percentLabel.setText("Completed")
            self.banner.showBanner("done", mountain["name"] + " completed!", "You beat all " + str(len(mountains.BOSS_CHECKPOINTS)) + " bosses and reached the summit.")
        elif isLocked:
            pillName = "MapPercentLocked"
            previousName = mountains.MOUNTAINS[self.viewedMountain - 1]["name"]
            self.banner.showBanner("locked", "Locked", "Beat " + previousName + " and its summit boss to unlock " + mountain["name"] + ".")
        else:
            self.banner.hide()
        if self.percentLabel.objectName() != pillName:
            self.percentLabel.setObjectName(pillName)
            self.percentLabel.style().unpolish(self.percentLabel)
            self.percentLabel.style().polish(self.percentLabel)
        self.placeMap()
        if isLocked:
            self.percentLabel.setText("Locked")
            self.goalLabel.setText("Beat " + mountains.MOUNTAINS[self.viewedMountain - 1]["shortName"] + " to unlock this mountain")
        elif self.viewedMountain < state["mountainNumber"]:
            self.goalLabel.setText("You climbed this whole mountain")
        elif state["finished"]:
            self.goalLabel.setText("You climbed all three mountains")
        elif state["atBoss"]:
            self.goalLabel.setText(bossName(state["bossesBeaten"]) + " is blocking the trail")
        elif state["nextBoss"] is not None:
            bossDistance = percentText(state["nextBoss"] - state["totalPercent"])
            self.goalLabel.setText(bossDistance + "% to " + bossName(state["bossesBeaten"]))

    def switchMountain(self, mountainNumber, animate=True):
        if animate and self.mapFrame.width() > 0:
            fadeOverlay = QLabel(self.mapFrame)
            fadeOverlay.setPixmap(self.mapFrame.grab())
            fadeOverlay.setGeometry(0, 0, self.mapFrame.width(), self.mapFrame.height())
            fadeOverlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            fadeOverlay.show()
            animations.fadeOutAndDelete(fadeOverlay, 320)
        self.viewedMountain = mountainNumber
        self.mountainMap.showMountain(mountainNumber)
        self.titleLabel.setText(mountains.MOUNTAINS[mountainNumber]["name"])
        self.leftArrow.setVisible(mountainNumber > 0)
        self.rightArrow.setVisible(mountainNumber < len(mountains.MOUNTAINS) - 1)
        self.leftArrow.raise_()
        self.rightArrow.raise_()
        self.updateInfo()
        if animate:
            QTimer.singleShot(0, lambda: self.scrollToClimber(0))

    def scrollToClimber(self, duration=900):
        scrollBar = self.scrollArea.verticalScrollBar()
        targetValue = int(self.mountainMap.markerPoint().y() - self.scrollArea.viewport().height() * 0.55)
        targetValue = max(0, min(targetValue, scrollBar.maximum()))
        if duration == 0:
            scrollBar.setValue(targetValue)
            return
        animations.animateValue(scrollBar.value(), targetValue, lambda value: scrollBar.setValue(int(value)), duration)
