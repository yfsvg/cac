import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QTransform
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from arete.core import climbing, mountains
from arete.ui import animations, mountain_art
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
    QPushButton#OpenMap:hover { background-color: @primaryHover; }
    QPushButton#OpenMap:pressed { border-bottom: 1px solid @primaryShadow; padding-top: 8px; }
"""

NODE_RADIUS = 13
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


def drawBolt(painter, center, size):
    bolt = QPainterPath(QPointF(center.x() + size * 0.15, center.y() - size * 0.7))
    bolt.lineTo(QPointF(center.x() - size * 0.4, center.y() + size * 0.1))
    bolt.lineTo(QPointF(center.x() - size * 0.02, center.y() + size * 0.1))
    bolt.lineTo(QPointF(center.x() - size * 0.15, center.y() + size * 0.75))
    bolt.lineTo(QPointF(center.x() + size * 0.4, center.y() - size * 0.12))
    bolt.lineTo(QPointF(center.x() + size * 0.02, center.y() - size * 0.12))
    bolt.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("white"))
    painter.drawPath(bolt)


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
        self.sky = mountain_art.Sky()
        self.update()

    def refresh(self):
        self.state = climbing.climbState()
        self.update()

    def scale(self):
        return self.width() / mountain_art.PICTURE_WIDTH

    def pictureHeight(self):
        return int(mountain_art.PICTURE_HEIGHT * self.scale())

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
        return visibleRect.top() / self.scale(), visibleRect.bottom() / self.scale()

    def animate(self):
        if self.width() == 0:
            return
        visibleTop, visibleBottom = self.visiblePictureRange()
        self.sky.update(self.seconds(), visibleTop, visibleBottom)
        self.update(self.visibleRegion().boundingRect())

    def percentHere(self):
        if self.mountainNumber < self.state["mountainNumber"]:
            return 100
        if self.mountainNumber > self.state["mountainNumber"]:
            return 0
        return self.state["percent"]

    def onScreen(self, picturePoint):
        return QPointF(picturePoint.x() * self.scale(), picturePoint.y() * self.scale())

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
            self.scene().renderer.render(picturePainter, QRectF(0, 0, self.width(), self.pictureHeight()))
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
        visibleTop = event.rect().top() / self.scale()
        visibleBottom = event.rect().bottom() / self.scale()

        painter.save()
        painter.scale(self.scale(), self.scale())
        mountain_art.paintTrees(painter, scene, seconds, visibleTop, visibleBottom)
        self.sky.paint(painter, seconds)
        painter.restore()

        colors = getColors()
        percentHere = self.percentHere()
        if percentHere > 0:
            walked = mountain_art.partOfPath(scene.trail, scene.trailFraction(percentHere))
            walked = QTransform().scale(self.scale(), self.scale()).map(walked)
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
        for checkpointNumber in range(mountains.CHECKPOINT_COUNT):
            nodePoint = self.onScreen(scene.rings[checkpointNumber])
            reached = percentHere >= mountains.checkpointPercent(checkpointNumber) - 0.001
            stageText = mountain["stages"][checkpointNumber][0]
            if checkpointNumber in mountains.BOSS_CHECKPOINTS:
                bossNumber = bossesBefore + mountains.BOSS_CHECKPOINTS.index(checkpointNumber)
                self.drawBoss(painter, nodePoint, bossNumber < self.state["bossesBeaten"], colors)
                self.drawLabel(painter, stageText + "  ·  " + bossName(bossNumber), nodePoint, BOSS_RADIUS + 10)
            else:
                if reached:
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

    def drawBoss(self, painter, point, beaten, colors):
        shieldColor = QColor(colors["boss"])
        if beaten:
            shieldColor = QColor(colors["trail"])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shieldColor.darker(135))
        painter.drawPath(shieldPath(QPointF(point.x(), point.y() + 3), BOSS_RADIUS))
        painter.setPen(QPen(QColor("white"), 2.5))
        painter.setBrush(shieldColor)
        painter.drawPath(shieldPath(point, BOSS_RADIUS))
        if beaten:
            drawCheck(painter, point, BOSS_RADIUS * 0.8, QColor("white"))
        else:
            drawBolt(painter, point, BOSS_RADIUS * 0.8)

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
        painter.fillRect(self.rect(), QColor(10, 8, 30, 110))
        cardRect = QRectF(30, self.pictureHeight() * 0.69 - 60, self.width() - 60, 120)
        card = QPainterPath()
        card.addRoundedRect(cardRect, 22, 22)
        painter.fillPath(card, QColor(20, 16, 50, 215))
        drawLock(painter, QPointF(cardRect.center().x(), cardRect.top() + 34), 22, QColor("white"))
        textFont = QFont(self.font())
        textFont.setPixelSize(14)
        textFont.setBold(True)
        painter.setFont(textFont)
        painter.setPen(QColor("white"))
        previousName = mountains.MOUNTAINS[self.mountainNumber - 1]["name"]
        painter.drawText(QRectF(cardRect.left(), cardRect.top() + 58, cardRect.width(), 50), Qt.AlignmentFlag.AlignCenter, "Reach the top of " + previousName + "\nand beat its boss to unlock")


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
        self.mountainMap.showMountain(climbing.climbState()["mountainNumber"])
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
        bottomRow.addWidget(self.summaryLabel)
        bottomRow.addStretch()
        openButton = QPushButton("Open map", objectName="OpenMap", cursor=Qt.CursorShape.PointingHandCursor)
        openButton.clicked.connect(openMap)
        bottomRow.addWidget(openButton)
        cardLayout.addLayout(bottomRow)

    def refresh(self):
        state = climbing.climbState()
        self.summaryLabel.setText(climbSummary(state))
        self.miniMap.refresh()


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

        tabRow = QHBoxLayout()
        tabRow.setSpacing(6)
        self.tabs = []
        for mountainNumber in range(len(mountains.MOUNTAINS)):
            tab = QPushButton(mountains.MOUNTAINS[mountainNumber]["shortName"], objectName="MountainTab", cursor=Qt.CursorShape.PointingHandCursor)
            tab.setCheckable(True)
            tab.clicked.connect(lambda checked=False, n=mountainNumber: self.switchMountain(n))
            self.tabs.append(tab)
            tabRow.addWidget(tab)
        tabRow.addStretch()
        pageLayout.addLayout(tabRow)

        self.mapFrame = MapFrame(self.placeMap)
        pageLayout.addWidget(self.mapFrame, 1)
        self.scrollArea = QScrollArea(self.mapFrame, widgetResizable=True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.mountainMap = MountainMap()
        self.scrollArea.setWidget(self.mountainMap)
        self.needsFirstScroll = True
        self.switchMountain(self.viewedMountain, False)

    def placeMap(self):
        self.scrollArea.setGeometry(0, 0, self.mapFrame.width(), self.mapFrame.height())
        if self.needsFirstScroll and self.mapFrame.height() > 100:
            self.needsFirstScroll = False
            QTimer.singleShot(50, lambda: self.scrollToClimber(900))

    def refresh(self):
        self.mountainMap.refresh()

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
        state = climbing.climbState()
        for tabNumber in range(len(self.tabs)):
            tab = self.tabs[tabNumber]
            tab.setChecked(tabNumber == mountainNumber)
            isLocked = tabNumber > state["mountainNumber"]
            if tab.property("locked") != isLocked:
                tab.setProperty("locked", isLocked)
                tab.style().unpolish(tab)
                tab.style().polish(tab)
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
