import math
import time
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QRegion, QTransform
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget

from focusguard.storage import memory
from focusguard.ui import animations, mountain_art
from focusguard.ui.theme import getColors

CLIMB_STYLE = """
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
    QProgressBar#MapBar { background-color: @surfaceContainerHighest; border: none; border-radius: 4px; }
    QProgressBar#MapBar::chunk { background-color: @trail; border-radius: 4px; }
    QPushButton#OpenMap:hover { background-color: @primaryHover; }
    QPushButton#OpenMap:pressed { border-bottom: 1px solid @primaryShadow; padding-top: 8px; }
"""

ASSETS = Path(__file__).parent / "assets"

# just looks, every mountain uses the same 8 climb stages
MOUNTAINS = [
    {"name": "Mount Everest", "picture": ASSETS / "everest_climb.svg", "topCrop": 140},
    {"name": "Mount Fuji", "picture": ASSETS / "fuji.svg", "topCrop": 150},
    {"name": "Matterhorn", "picture": ASSETS / "matterhorn.svg", "topCrop": 70},
]

NODE_RADIUS = 13


def chosenMountain():
    return memory.load().get("mountainChoice", 0) % len(MOUNTAINS)


def climbPercent(meters):
    # stage n sits on ring n of the trail, in between is a straight mix
    stages = memory.CLIMB_STAGES
    stageNumber = stages.index(memory.climbStage(meters))
    if stageNumber == len(stages) - 1:
        return 100
    stageStart = stages[stageNumber]["startMeters"]
    stageLength = stages[stageNumber + 1]["startMeters"] - stageStart
    return (stageNumber + 1 + (meters - stageStart) / stageLength) * 100 / len(stages)


def climbSummary(meters):
    goalName, metersLeft = memory.nextClimbGoal(meters)
    if metersLeft > 0:
        return format(meters, ",") + " m climbed  ·  " + format(metersLeft, ",") + " m to " + goalName
    return format(meters, ",") + " m climbed  ·  you're at the top!"


def drawCheck(painter, center, size, color):
    painter.setPen(QPen(color, size * 0.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    check = QPainterPath(QPointF(center.x() - size * 0.45, center.y()))
    check.lineTo(QPointF(center.x() - size * 0.1, center.y() + size * 0.35))
    check.lineTo(QPointF(center.x() + size * 0.5, center.y() - size * 0.35))
    painter.drawPath(check)


class MountainMap(QWidget):
    def __init__(self):
        super().__init__()
        self.mountainNumber = 0
        self.bottomPad = 80
        self.showLabels = True
        self.shownPercent = None
        self.picture = None
        self.pictureKey = None
        self.bottomColor = QColor("#2A1F4A")
        self.startTime = time.time()
        self.sky = mountain_art.Sky()
        self.animationTimer = QTimer(self, interval=40, timeout=self.animate)

    def scene(self):
        return mountain_art.sceneFor(MOUNTAINS[self.mountainNumber]["picture"])

    def showMountain(self, mountainNumber):
        self.mountainNumber = mountainNumber
        self.shownPercent = self.realPercent()
        self.sky = mountain_art.Sky()
        self.update()

    def refresh(self):
        oldPercent = self.percentHere()
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
        return self.width() / mountain_art.PICTURE_WIDTH

    def topCrop(self):
        return MOUNTAINS[self.mountainNumber]["topCrop"]

    def pictureHeight(self):
        return int((mountain_art.PICTURE_HEIGHT - self.topCrop()) * self.scale())

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
        if self.shownPercent is not None:
            return self.shownPercent
        return self.realPercent()

    def realPercent(self):
        return climbPercent(memory.climbMeters())

    def onScreen(self, picturePoint):
        return QPointF(picturePoint.x() * self.scale(), (picturePoint.y() - self.topCrop()) * self.scale())

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
            self.scene().renderer.render(picturePainter, QRectF(0, -self.topCrop() * self.scale(), self.width(), mountain_art.PICTURE_HEIGHT * self.scale()))
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
        painter.scale(self.scale(), self.scale())
        painter.translate(0, -self.topCrop())
        mountain_art.paintTrees(painter, scene, seconds, visibleTop, visibleBottom)
        self.sky.paint(painter, seconds)
        painter.restore()

        colors = getColors()
        percentHere = self.percentHere()
        if percentHere > 0:
            walked = mountain_art.partOfPath(scene.trail, scene.trailFraction(percentHere))
            walked = QTransform().scale(self.scale(), self.scale()).translate(0, -self.topCrop()).map(walked)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(colors["trailShadow"]), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(walked.translated(0, 2))
            painter.setPen(QPen(QColor(colors["trail"]), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(walked)

        labelFont = QFont(self.font())
        labelFont.setPixelSize(12)
        labelFont.setBold(True)
        painter.setFont(labelFont)
        climberPoint = self.markerPoint()
        stages = memory.CLIMB_STAGES
        for stageNumber in range(len(stages)):
            nodePoint = self.onScreen(scene.rings[stageNumber])
            underClimber = (nodePoint.x() - climberPoint.x()) ** 2 + (nodePoint.y() - climberPoint.y()) ** 2 < 24 ** 2
            if percentHere >= (stageNumber + 1) * 100 / len(stages) - 0.001 and not underClimber:
                self.drawDoneNode(painter, nodePoint, colors)
            self.drawLabel(painter, stages[stageNumber]["name"], nodePoint, NODE_RADIUS + 10)

        self.drawClimber(painter, climberPoint, colors, seconds)
        painter.end()

    def drawDoneNode(self, painter, point, colors):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colors["trailShadow"]))
        painter.drawEllipse(QPointF(point.x(), point.y() + 3), NODE_RADIUS, NODE_RADIUS)
        painter.setPen(QPen(QColor("white"), 2.5))
        painter.setBrush(QColor(colors["trail"]))
        painter.drawEllipse(point, NODE_RADIUS, NODE_RADIUS)
        drawCheck(painter, point, NODE_RADIUS * 0.9, QColor("white"))

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
        mountainNumber = chosenMountain()
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
        self.summaryLabel = QLabel("", objectName="ClimbLine", wordWrap=True)
        bottomRow.addWidget(self.summaryLabel, 1)
        openButton = QPushButton("Open map", objectName="OpenMap", cursor=Qt.CursorShape.PointingHandCursor)
        openButton.clicked.connect(openMap)
        bottomRow.addWidget(openButton)
        cardLayout.addLayout(bottomRow)

    def refresh(self):
        self.summaryLabel.setText(climbSummary(memory.climbMeters()))
        self.miniMap.refresh()


class MapHome(QWidget):
    def __init__(self, goBack):
        super().__init__()
        from focusguard.ui.settings_window import makeBackArrow

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
        self.progressBar = QProgressBar(objectName="MapBar")
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(8)
        self.progressBar.setRange(0, memory.SUMMIT_METERS)
        infoLayout.addWidget(self.progressBar)
        self.goalLabel = QLabel("", objectName="MapInfo")
        infoLayout.addWidget(self.goalLabel)
        pageLayout.addWidget(infoCard)

        self.mapFrame = MapFrame(self.placeMap)
        pageLayout.addWidget(self.mapFrame, 1)
        self.scrollArea = QScrollArea(self.mapFrame, widgetResizable=True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.mountainMap = MountainMap()
        self.scrollArea.setWidget(self.mountainMap)
        self.needsFirstScroll = True
        self.switchMountain(chosenMountain(), False)

    def placeMap(self):
        self.scrollArea.setGeometry(0, 0, self.mapFrame.width(), self.mapFrame.height())
        roundedShape = QPainterPath()
        roundedShape.addRoundedRect(QRectF(self.mapFrame.rect()), 24, 24)
        self.mapFrame.setMask(QRegion(roundedShape.toFillPolygon().toPolygon()))
        if self.needsFirstScroll and self.mapFrame.height() > 100:
            self.needsFirstScroll = False
            QTimer.singleShot(50, lambda: self.scrollToClimber(900))

    def refresh(self):
        self.mountainMap.refresh()
        self.updateInfo()

    def updateInfo(self):
        meters = memory.climbMeters()
        self.stageLabel.setText(memory.climbStage(meters)["name"])
        self.percentLabel.setText(format(meters, ",") + " m")
        animations.animateValue(self.progressBar.value(), meters, lambda value: self.progressBar.setValue(int(value)), 700)
        self.goalLabel.setText(climbSummary(meters))

    def switchMountain(self, mountainNumber, animate=True):
        if animate and self.mapFrame.width() > 0:
            fadeOverlay = QLabel(self.mapFrame)
            fadeOverlay.setPixmap(self.mapFrame.grab())
            fadeOverlay.setGeometry(0, 0, self.mapFrame.width(), self.mapFrame.height())
            fadeOverlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            fadeOverlay.show()
            animations.fadeOutAndDelete(fadeOverlay, 320)
        self.mountainMap.showMountain(mountainNumber)
        self.titleLabel.setText(MOUNTAINS[mountainNumber]["name"])
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
