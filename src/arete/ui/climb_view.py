# The climb, everything you see of the mountains. Split into five segments:
# 1. Small helpers + hand drawn icons
# 2. MountainMap, draws one mountain (picture, trail, checkpoints, bosses, climber)
# 3. The banner + frame that sit on top of the big map
# 4. Home page cards, the mini map climb card + the boss card
# 5. MapHome, the full map page with arrows to flip between mountains


import math
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QRegion, QTransform
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QScrollArea, QVBoxLayout, QWidget

from arete.core import climbing, mountains
from arete.ui import animations, mountain_art
from arete.ui.boss_fight import BossPortrait, bossName, drawBossCharacter
from arete.ui.theme import getColors


# stylesheet for the climb card, boss card and map page, @names are theme colours
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
    QLabel#MapMessage { color: @onSurface; font-size: 13px; font-style: italic; }
    QLabel#ClimbGain { color: #1F9D55; font-size: 12px; font-weight: 700; }
    QLabel#ClimbLoss { color: #D64545; font-size: 12px; font-weight: 700; }
    QFrame#BossCard { background-color: @surfaceContainerLow; border: 2px solid @boss; border-radius: 24px; }
    QLabel#BossCardHeading { color: @boss; font-size: 12px; font-weight: 800; }
    QLabel#BossCardName { color: @onSurface; font-size: 18px; font-weight: 800; }
    QLabel#BossCardHealth { color: @onSurface; font-size: 13px; font-weight: 700; }
    QLabel#BossCardHint { color: @onSurfaceVariant; font-size: 12px; }
    QProgressBar#BossBar { background-color: @surfaceContainerHighest; border: none; border-radius: 6px; }
    QProgressBar#BossBar::chunk { background-color: @boss; border-radius: 6px; }
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

# sizes of the checkpoint circles + boss badges on the map, in pixels
CHECKPOINT_RADIUS = 13
BOSS_RADIUS = 19

# map page shows the mountain a bit smaller so more of it fits, the sides get filled in
MAP_PAGE_ZOOM = 0.8






# Helpers, text

# "42.5% up Mount Fuji"
def climbSummary(state):
    return percentText(state["percent"]) + "% up " + mountains.MOUNTAINS[state["mountainNumber"]]["name"]


# 42.50 -> "42.5", 40.0 -> "40"
def percentText(percent):
    return format(percent, ".1f").rstrip("0").rstrip(".")


# Helpers, icons drawn by hand so they scale + follow the colours

# tick mark for reached checkpoints + beaten bosses
def drawCheck(painter, center, size, color):
    painter.setPen(QPen(color, size * 0.28, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    tickMark = QPainterPath(QPointF(center.x() - size * 0.45, center.y()))
    tickMark.lineTo(QPointF(center.x() - size * 0.1, center.y() + size * 0.35))
    tickMark.lineTo(QPointF(center.x() + size * 0.5, center.y() - size * 0.35))
    painter.drawPath(tickMark)


# shield outline, beaten bosses turn into one of these
def shieldPath(center, size):
    shieldOutline = QPainterPath(QPointF(center.x() - size, center.y() - size * 0.75))
    shieldOutline.quadTo(QPointF(center.x(), center.y() - size * 1.1), QPointF(center.x() + size, center.y() - size * 0.75))
    shieldOutline.lineTo(QPointF(center.x() + size, center.y() + size * 0.1))
    shieldOutline.quadTo(QPointF(center.x() + size * 0.9, center.y() + size * 0.8), QPointF(center.x(), center.y() + size * 1.15))
    shieldOutline.quadTo(QPointF(center.x() - size * 0.9, center.y() + size * 0.8), QPointF(center.x() - size, center.y() + size * 0.1))
    shieldOutline.closeSubpath()
    return shieldOutline


# padlock on the locked mountain banner
def drawLock(painter, center, size, color):
    painter.setPen(QPen(color, size * 0.18))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(center.x() - size * 0.38, center.y() - size * 0.85, size * 0.76, size * 0.9), 0, 180 * 16)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawRoundedRect(QRectF(center.x() - size * 0.55, center.y() - size * 0.4, size * 1.1, size * 0.9), size * 0.15, size * 0.15)


# trophy on the completed mountain banner
def drawTrophy(painter, center, size, color):
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    trophyCup = QPainterPath(QPointF(center.x() - size * 0.55, center.y() - size * 0.6))
    trophyCup.lineTo(QPointF(center.x() + size * 0.55, center.y() - size * 0.6))
    trophyCup.quadTo(QPointF(center.x() + size * 0.55, center.y() + size * 0.25), QPointF(center.x(), center.y() + size * 0.3))
    trophyCup.quadTo(QPointF(center.x() - size * 0.55, center.y() + size * 0.25), QPointF(center.x() - size * 0.55, center.y() - size * 0.6))
    painter.drawPath(trophyCup)
    painter.drawRect(QRectF(center.x() - size * 0.1, center.y() + size * 0.25, size * 0.2, size * 0.3))
    painter.drawRoundedRect(QRectF(center.x() - size * 0.4, center.y() + size * 0.5, size * 0.8, size * 0.18), 3, 3)

    # handles on both sides
    painter.setPen(QPen(color, size * 0.12))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawArc(QRectF(center.x() - size * 0.85, center.y() - size * 0.5, size * 0.5, size * 0.5), 90 * 16, 180 * 16)
    painter.drawArc(QRectF(center.x() + size * 0.35, center.y() - size * 0.5, size * 0.5, size * 0.5), 270 * 16, 180 * 16)






# One mountain. The svg picture is drawn once and saved, then every frame the
# moving stuff goes on top: trees swaying, birds/planes, the walked trail,
# checkpoints, bosses and the climber

class MountainMap(QWidget):
    def __init__(self):
        super().__init__()
        # which mountain this map is showing (0 fuji, 1 everest, 2 matterhorn) + the saved climb progress
        self.mountainNumber = 0
        self.savedClimb = climbing.climbState()

        # extra ground under the picture so the bottom checkpoint isnt on the edge
        self.bottomPadding = 80
        self.showLabels = True
        self.zoom = 1.0

        # how much health the current boss has left, 0 to 1, for the ring round its badge
        self.bossHealthLeftShare = 1.0

        # % the climber is drawn at, slides towards the real % when it changes
        self.shownPercent = None

        # saved picture of the mountain + what size it was made for
        self.savedMountainPicture = None
        self.savedMountainPictureKey = None
        self.bottomColor = QColor("#2A1F4A")

        self.startTime = time.time()
        self.sky = mountain_art.Sky()
        self.animationTimer = QTimer(self, interval=40, timeout=self.animate)


    # trail points, checkpoint rings + trees read out of this mountains svg
    def scene(self):
        return mountain_art.sceneFor(mountains.MOUNTAINS[self.mountainNumber]["picture"])

    # jump straight to a mountain, no sliding
    def showMountain(self, mountainNumber):
        self.mountainNumber = mountainNumber
        self.savedClimb = climbing.climbState()
        self.bossHealthLeftShare = climbing.bossMinutesLeft() / climbing.bossHealth(self.savedClimb["bossesBeaten"])
        self.shownPercent = self.realPercent()
        self.sky = mountain_art.Sky()
        self.update()

    # re-read the climb, climber slides to the new spot
    def refresh(self):
        oldPercent = self.percentHere()
        self.savedClimb = climbing.climbState()
        self.bossHealthLeftShare = climbing.bossMinutesLeft() / climbing.bossHealth(self.savedClimb["bossesBeaten"])
        newPercent = self.realPercent()
        if self.shownPercent is not None and abs(newPercent - oldPercent) > 0.001:
            animations.animateValue(oldPercent, newPercent, self.setShownPercent, 1200)
        else:
            self.shownPercent = newPercent
        self.update()

    def setShownPercent(self, percent):
        self.shownPercent = percent
        self.update()




    # Sizing, the svg is 420 wide so everything gets scaled to the widget width

    def scale(self):
        return self.width() * self.zoom / mountain_art.PICTURE_WIDTH

    # gap on the left when zoomed out, keeps the mountain centred
    def offsetX(self):
        return (self.width() - mountain_art.PICTURE_WIDTH * self.scale()) / 2

    # empty sky cut off the top of each picture
    def topCrop(self):
        return mountains.MOUNTAINS[self.mountainNumber]["topCrop"]

    def pictureHeight(self):
        return int((mountain_art.PICTURE_HEIGHT - self.topCrop()) * self.scale())

    # map is as tall as the scaled picture, the scroll area does the rest
    def updateHeight(self):
        if self.width() > 0:
            self.setFixedHeight(self.pictureHeight() + self.bottomPadding)

    def resizeEvent(self, event):
        self.updateHeight()
        super().resizeEvent(event)




    # Animation, only while you can see it

    def showEvent(self, event):
        self.animationTimer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.animationTimer.stop()
        super().hideEvent(event)

    def secondsSinceMade(self):
        return time.time() - self.startTime

    # which part of the picture is on screen, so we only animate + draw that bit
    def visiblePictureRange(self):
        visibleArea = self.visibleRegion().boundingRect()
        return visibleArea.top() / self.scale() + self.topCrop(), visibleArea.bottom() / self.scale() + self.topCrop()

    # runs every 40ms, moves the birds/planes then repaints whats visible
    def animate(self):
        if self.width() == 0:
            return
        visibleTop, visibleBottom = self.visiblePictureRange()
        self.sky.update(self.secondsSinceMade(), visibleTop, visibleBottom)
        self.update(self.visibleRegion().boundingRect())




    # Climb position

    # % to draw the climber at, uses the sliding value on the mountain ur on
    def percentHere(self):
        if self.shownPercent is not None and self.mountainNumber == self.savedClimb["mountainNumber"]:
            return self.shownPercent
        return self.realPercent()

    # finished mountains are 100%, ones you havent reached yet are 0%
    def realPercent(self):
        if self.mountainNumber < self.savedClimb["mountainNumber"]:
            return 100
        if self.mountainNumber > self.savedClimb["mountainNumber"]:
            return 0
        return self.savedClimb["percent"]

    # svg coords -> widget coords
    def onScreen(self, picturePoint):
        return QPointF(self.offsetX() + picturePoint.x() * self.scale(), (picturePoint.y() - self.topCrop()) * self.scale())

    # where the climber goes, stops a bit short of a boss thats blocking the trail
    def markerPoint(self):
        climberPercent = self.percentHere()
        if self.savedClimb["atBoss"] and self.mountainNumber == self.savedClimb["mountainNumber"]:
            climberPercent = max(climberPercent - 2.5, 0)
        return self.onScreen(self.scene().trail.pointAtPercent(self.scene().trailFraction(climberPercent)))




    # Drawing, the still picture

    # the mountain picture, only redrawn when the size or mountain changes
    def basePicture(self):
        pixelRatio = self.devicePixelRatioF()
        pictureKey = (self.width(), self.height(), self.mountainNumber, pixelRatio)
        if self.savedMountainPicture is None or self.savedMountainPictureKey != pictureKey:
            self.savedMountainPicture = QPixmap(int(self.width() * pixelRatio), int(self.height() * pixelRatio))
            self.savedMountainPicture.setDevicePixelRatio(pixelRatio)
            self.savedMountainPicture.fill(Qt.GlobalColor.transparent)
            picturePainter = QPainter(self.savedMountainPicture)
            picturePainter.setRenderHint(QPainter.RenderHint.Antialiasing)
            fullPictureHeight = mountain_art.PICTURE_HEIGHT * self.scale()
            self.scene().renderer.render(picturePainter, QRectF(0, -self.topCrop() * self.scale(), self.width(), fullPictureHeight))

            # zoomed out: the full width picture is the background, then the real
            # mountain goes in the middle with its edges faded so the sides blend in
            if self.zoom < 1:
                picturePainter.save()
                picturePainter.scale(self.width() / mountain_art.PICTURE_WIDTH, self.scale())
                picturePainter.translate(0, -self.topCrop())
                mountain_art.paintTrees(picturePainter, self.scene(), 0, 0, mountain_art.PICTURE_HEIGHT)
                picturePainter.restore()

                middlePictureWidth = int(mountain_art.PICTURE_WIDTH * self.scale())
                middlePicture = QPixmap(int(middlePictureWidth * pixelRatio), int(self.height() * pixelRatio))
                middlePicture.setDevicePixelRatio(pixelRatio)
                middlePicture.fill(Qt.GlobalColor.transparent)
                middlePainter = QPainter(middlePicture)
                middlePainter.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.scene().renderer.render(middlePainter, QRectF(0, -self.topCrop() * self.scale(), middlePictureWidth, fullPictureHeight))

                # fades the left + right 30px of the middle picture out
                edgeFade = QLinearGradient(0, 0, middlePictureWidth, 0)
                edgeFade.setColorAt(0, QColor(0, 0, 0, 0))
                edgeFade.setColorAt(30 / middlePictureWidth, QColor(0, 0, 0, 255))
                edgeFade.setColorAt(1 - 30 / middlePictureWidth, QColor(0, 0, 0, 255))
                edgeFade.setColorAt(1, QColor(0, 0, 0, 0))
                middlePainter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                middlePainter.fillRect(QRectF(0, 0, middlePictureWidth, self.height()), edgeFade)
                middlePainter.end()
                picturePainter.drawPixmap(int(self.offsetX()), 0, middlePicture)
            picturePainter.end()

            # fill the bottom padding with the colour at the bottom of the picture
            self.bottomColor = self.savedMountainPicture.toImage().pixelColor(int(4 * pixelRatio), int((self.pictureHeight() - 3) * pixelRatio))
            picturePainter = QPainter(self.savedMountainPicture)
            picturePainter.fillRect(QRectF(0, self.pictureHeight() - 1, self.width(), self.bottomPadding + 2), self.bottomColor)
            picturePainter.end()
            self.savedMountainPictureKey = pictureKey
        return self.savedMountainPicture




    # Drawing, every frame: saved picture, then trees + sky, trail, checkpoints, climber

    def paintEvent(self, event):
        if self.width() == 0:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(event.rect())
        painter.drawPixmap(0, 0, self.basePicture())
        mountainScene = self.scene()
        secondsSinceMade = self.secondsSinceMade()



        # trees + birds are in svg coords so draw them scaled the same as the picture
        painter.save()
        painter.translate(self.offsetX(), 0)
        painter.scale(self.scale(), self.scale())
        painter.translate(0, -self.topCrop())
        mountain_art.paintTrees(painter, mountainScene, secondsSinceMade, event.rect().top() / self.scale() + self.topCrop(), event.rect().bottom() / self.scale() + self.topCrop())
        self.sky.paint(painter, secondsSinceMade)
        painter.restore()



        # trail you've walked so far, shadow first then the yellow line
        themeColors = getColors()
        percentHere = self.percentHere()
        if percentHere > 0:
            walkedTrail = QTransform().translate(self.offsetX(), 0).scale(self.scale(), self.scale()).translate(0, -self.topCrop()).map(mountain_art.partOfPath(mountainScene.trail, mountainScene.trailFraction(percentHere)))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(themeColors["trailShadow"]), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(walkedTrail.translated(0, 2))
            painter.setPen(QPen(QColor(themeColors["trail"]), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(walkedTrail)



        # checkpoints, every mountain has 8 and some of them are bosses
        labelFont = QFont(self.font())
        labelFont.setPixelSize(12)
        labelFont.setBold(True)
        painter.setFont(labelFont)
        bossesOnEarlierMountains = self.mountainNumber * len(mountains.BOSS_CHECKPOINTS)
        climberPoint = None
        if self.mountainNumber == self.savedClimb["mountainNumber"]:
            climberPoint = self.markerPoint()

        for checkpointNumber in range(mountains.CHECKPOINT_COUNT):
            checkpointPoint = self.onScreen(mountainScene.rings[checkpointNumber])
            # the climber covers whatever checkpoint its standing on
            hiddenUnderClimber = climberPoint is not None and (checkpointPoint.x() - climberPoint.x()) ** 2 + (checkpointPoint.y() - climberPoint.y()) ** 2 < 24 ** 2
            stageName = mountains.MOUNTAINS[self.mountainNumber]["stages"][checkpointNumber][0]

            if checkpointNumber in mountains.BOSS_CHECKPOINTS:
                bossNumber = bossesOnEarlierMountains + mountains.BOSS_CHECKPOINTS.index(checkpointNumber)
                if not hiddenUnderClimber:
                    self.drawBoss(painter, checkpointPoint, bossNumber < self.savedClimb["bossesBeaten"], themeColors, secondsSinceMade, bossNumber == self.savedClimb["bossesBeaten"], bossNumber)
                self.drawLabel(painter, stageName + "  ·  " + bossName(bossNumber), checkpointPoint, BOSS_RADIUS + 22)
            else:
                if percentHere >= mountains.checkpointPercent(checkpointNumber) - 0.001 and not hiddenUnderClimber:
                    self.drawDoneCheckpoint(painter, checkpointPoint, themeColors)
                self.drawLabel(painter, stageName, checkpointPoint, CHECKPOINT_RADIUS + 10)



        if self.mountainNumber == self.savedClimb["mountainNumber"]:
            self.drawClimber(painter, self.markerPoint(), themeColors)
        if self.mountainNumber > self.savedClimb["mountainNumber"]:
            self.drawLocked(painter)
        painter.end()




    # Drawing, the pieces

    # yellow tick circle on a checkpoint you've passed
    def drawDoneCheckpoint(self, painter, point, themeColors):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(themeColors["trailShadow"]))
        painter.drawEllipse(QPointF(point.x(), point.y() + 3), CHECKPOINT_RADIUS, CHECKPOINT_RADIUS)
        painter.setPen(QPen(QColor("white"), 2.5))
        painter.setBrush(QColor(themeColors["trail"]))
        painter.drawEllipse(point, CHECKPOINT_RADIUS, CHECKPOINT_RADIUS)
        drawCheck(painter, point, CHECKPOINT_RADIUS * 0.9, QColor("white"))

    # boss checkpoint: beaten ones are a tick shield, the rest show the boss in a badge.
    # the next boss pulses, and once ur fighting it a ring shows how much health it has left
    def drawBoss(self, painter, point, beaten, themeColors, secondsSinceMade, isNextBoss, bossNumber):
        shieldColor = QColor(themeColors["trail"] if beaten else themeColors["boss"])
        shieldSize = BOSS_RADIUS

        # next boss beats like a heart + glows
        if isNextBoss and not beaten:
            heartbeat = (math.sin(secondsSinceMade * 4) + 1) / 2
            shieldSize = BOSS_RADIUS * (1 + 0.1 * heartbeat)
            glowColor = QColor(shieldColor)
            glowColor.setAlpha(int(40 + 70 * heartbeat))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glowColor)
            painter.drawEllipse(point, BOSS_RADIUS + 10 + 6 * heartbeat, BOSS_RADIUS + 10 + 6 * heartbeat)

        # not beaten yet, boss face in a round badge
        if not beaten:
            badgeSize = shieldSize + 5
            painter.setPen(QPen(shieldColor, 3))
            painter.setBrush(QColor("#FFF6EE"))
            painter.drawEllipse(point, badgeSize, badgeSize)

            # health ring, goes round clockwise from the top as it loses health
            if isNextBoss and self.savedClimb["atBoss"]:
                ringSize = badgeSize + 7
                painter.setPen(QPen(QColor(255, 255, 255, 90), 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(point, ringSize, ringSize)
                painter.setPen(QPen(shieldColor, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawArc(QRectF(point.x() - ringSize, point.y() - ringSize, ringSize * 2, ringSize * 2), 90 * 16, int(360 * 16 * self.bossHealthLeftShare))
            drawBossCharacter(painter, bossNumber, QRectF(point.x() - badgeSize * 1.7 / 2, point.y() - badgeSize * 1.7 / 2, badgeSize * 1.7, badgeSize * 1.7))
            return

        # beaten, shield with a tick
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shieldColor.darker(135))
        painter.drawPath(shieldPath(QPointF(point.x(), point.y() + 3), shieldSize))
        painter.setPen(QPen(QColor("white"), 2.5))
        painter.setBrush(shieldColor)
        painter.drawPath(shieldPath(point, shieldSize))
        drawCheck(painter, point, shieldSize * 0.8, QColor("white"))

    # dark pill with the checkpoint name, goes on whichever side has room
    def drawLabel(self, painter, text, point, gap):
        if not self.showLabels:
            return
        labelWidth = painter.fontMetrics().horizontalAdvance(text) + 20
        labelHeight = 24
        rightSideBox = QRectF(point.x() + gap, point.y() - labelHeight / 2, labelWidth, labelHeight)
        leftSideBox = QRectF(point.x() - gap - labelWidth, point.y() - labelHeight / 2, labelWidth, labelHeight)
        fitsOnRight = rightSideBox.right() <= self.width() - 6
        fitsOnLeft = leftSideBox.left() >= 6

        # prefers the side away from the middle, flips if it doesnt fit, goes on top if neither fits
        if point.x() < self.width() / 2:
            labelBox = rightSideBox if fitsOnRight or not fitsOnLeft else leftSideBox
        else:
            labelBox = leftSideBox if fitsOnLeft or not fitsOnRight else rightSideBox
        if not fitsOnRight and not fitsOnLeft:
            labelBox = QRectF(point.x() - labelWidth / 2, point.y() - gap - labelHeight - 2, labelWidth, labelHeight)

        # keep it 6px inside the edges
        if labelBox.left() < 6:
            labelBox.moveLeft(6)
        if labelBox.right() > self.width() - 6:
            labelBox.moveRight(self.width() - 6)

        labelPill = QPainterPath()
        labelPill.addRoundedRect(labelBox, 12, 12)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.fillPath(labelPill, QColor(20, 16, 40, 175))
        painter.setPen(QColor("white"))
        painter.drawText(labelBox, Qt.AlignmentFlag.AlignCenter, text)

    # you, a little person in a circle
    def drawClimber(self, painter, point, themeColors):
        painter.setPen(QPen(QColor("white"), 4))
        painter.setBrush(QColor(themeColors["primary"]))
        painter.drawEllipse(point, 14, 14)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(QPointF(point.x(), point.y() - 3), 4, 4)
        climberBody = QPainterPath(QPointF(point.x() - 6, point.y() + 7))
        climberBody.quadTo(QPointF(point.x(), point.y() - 2), QPointF(point.x() + 6, point.y() + 7))
        climberBody.closeSubpath()
        painter.drawPath(climberBody)

    # darkens a mountain you havent unlocked yet
    def drawLocked(self, painter):
        painter.fillRect(self.rect(), QColor(10, 8, 30, 140))






# Banner card over the map, "Locked" for mountains you cant climb yet,
# gold "completed" one for mountains you finished

class MapBanner(QWidget):
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.kind = "locked"
        self.title = ""
        self.detail = ""
        self.setFixedHeight(150)

    # fades in only when its new, so flipping back and forth doesnt keep flashing it
    def showBanner(self, kind, title, detail):
        isNewBanner = self.isHidden() or self.title != title
        self.kind = kind
        self.title = title
        self.detail = detail
        self.show()
        self.raise_()
        self.update()
        if isNewBanner:
            animations.fadeIn(self, 350)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bannerBox = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        bannerShape = QPainterPath()
        bannerShape.addRoundedRect(bannerBox, 26, 26)

        # gold for done, dark see through for locked
        if self.kind == "done":
            backColor = QColor("#FFC23D")
            edgeColor = QColor("#D99A0B")
            textColor = QColor("#4A3300")
        else:
            backColor = QColor(20, 16, 50, 235)
            edgeColor = QColor(255, 255, 255, 90)
            textColor = QColor("white")
        painter.fillPath(bannerShape.translated(0, 4), edgeColor)
        painter.fillPath(bannerShape, backColor)
        painter.setPen(QPen(edgeColor, 2))
        painter.drawPath(bannerShape)

        if self.kind == "done":
            drawTrophy(painter, QPointF(bannerBox.center().x(), bannerBox.top() + 38), 28, textColor)
        else:
            drawLock(painter, QPointF(bannerBox.center().x(), bannerBox.top() + 38), 26, textColor)

        # title + the line under it
        titleFont = QFont(self.font())
        titleFont.setPixelSize(20)
        titleFont.setBold(True)
        painter.setFont(titleFont)
        painter.setPen(textColor)
        painter.drawText(QRectF(bannerBox.left(), bannerBox.top() + 64, bannerBox.width(), 30), Qt.AlignmentFlag.AlignCenter, self.title)
        detailFont = QFont(self.font())
        detailFont.setPixelSize(13)
        painter.setFont(detailFont)
        painter.drawText(QRectF(bannerBox.left() + 12, bannerBox.top() + 94, bannerBox.width() - 24, 36), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.detail)


# holds the map + arrows + banner, tells the page when it resizes so it can place them
class MapFrame(QWidget):
    def __init__(self, whenResized):
        super().__init__()
        self.whenResized = whenResized

    def resizeEvent(self, event):
        self.whenResized()
        super().resizeEvent(event)


# round arrow buttons on the map page to flip between mountains, -1 left, 1 right
class MapArrowButton(QPushButton):
    def __init__(self, direction):
        super().__init__(objectName="MapArrow", cursor=Qt.CursorShape.PointingHandCursor)
        self.direction = direction
        self.setFixedSize(40, 40)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1))
        painter.setBrush(QColor(20, 16, 40, 220) if self.underMouse() else QColor(20, 16, 40, 170))
        painter.drawEllipse(QRectF(1, 1, 38, 38))

        # the arrow itself, a > or <
        painter.setPen(QPen(QColor("white"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        arrowTip = QPointF(20 + self.direction * 2, 20)
        painter.drawLine(QPointF(arrowTip.x() - self.direction * 5, 13), arrowTip)
        painter.drawLine(QPointF(arrowTip.x() - self.direction * 5, 27), arrowTip)

    # darker while hovered
    def enterEvent(self, event):
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.update()
        super().leaveEvent(event)






# Home page map, a short window onto the mountain that stays centred on the climber.
# no labels and no mouse wheel so it doesnt steal the dashboard's scrolling

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

    # same mountain = climber slides, new mountain = jump straight there
    def refresh(self):
        currentMountain = climbing.climbState()["mountainNumber"]
        if currentMountain == self.mountainMap.mountainNumber and self.mountainMap.shownPercent is not None:
            self.mountainMap.refresh()
        else:
            self.mountainMap.showMountain(currentMountain)
        QTimer.singleShot(0, self.centerOnClimber)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.centerOnClimber)

    def centerOnClimber(self):
        self.verticalScrollBar().setValue(max(0, min(int(self.mountainMap.markerPoint().y() - self.viewport().height() / 2), self.verticalScrollBar().maximum())))


# Home page climb card, mini map + "x% up" + the last thing that moved you up or down

class ClimbCard(QFrame):
    def __init__(self, openMap):
        super().__init__(objectName="ClimbCard")
        cardLayout = QVBoxLayout(self)
        cardLayout.setContentsMargins(12, 12, 12, 12)
        cardLayout.setSpacing(10)
        self.miniMap = MiniMap()
        cardLayout.addWidget(self.miniMap)

        # under the map, summary + last change on the left, open map button on the right
        bottomRow = QHBoxLayout()
        bottomRow.setContentsMargins(6, 0, 0, 0)
        self.summaryLabel = QLabel("", objectName="ClimbLine")
        self.shownPercent = None
        self.shownMountain = None
        summaryLayout = QVBoxLayout()
        summaryLayout.setSpacing(2)
        summaryLayout.addWidget(self.summaryLabel)
        self.changeLabel = QLabel("", objectName="ClimbGain")
        summaryLayout.addWidget(self.changeLabel)
        bottomRow.addLayout(summaryLayout)
        bottomRow.addStretch()
        openMapButton = QPushButton("Open map", objectName="OpenMap", cursor=Qt.CursorShape.PointingHandCursor)
        openMapButton.clicked.connect(openMap)
        bottomRow.addWidget(openMapButton)
        cardLayout.addLayout(bottomRow)

    # percent counts up/down to the new value, gain is green and loss is red
    def refresh(self):
        state = climbing.climbState()
        mountainName = mountains.MOUNTAINS[state["mountainNumber"]]["name"]
        if self.shownPercent is None or self.shownMountain != mountainName:
            self.summaryLabel.setText(climbSummary(state))
        else:
            animations.animateValue(self.shownPercent, state["percent"], lambda value: self.summaryLabel.setText(percentText(value) + "% up " + mountainName), 1200)
        self.shownPercent = state["percent"]
        self.shownMountain = mountainName

        lastClimbChange = state["lastChange"]
        self.changeLabel.setText(climbing.changeText(lastClimbChange))
        self.changeLabel.setVisible(lastClimbChange is not None)
        changeStyleName = "ClimbLoss" if lastClimbChange is not None and lastClimbChange["amount"] < 0 else "ClimbGain"
        if self.changeLabel.objectName() != changeStyleName:
            self.changeLabel.setObjectName(changeStyleName)
            self.changeLabel.style().unpolish(self.changeLabel)
            self.changeLabel.style().polish(self.changeLabel)
        self.miniMap.refresh()


# Home page boss card, only shows while a boss is blocking the trail.
# focus minutes in a session take away its health

class BossCard(QFrame):
    def __init__(self):
        super().__init__(objectName="BossCard")
        cardLayout = QHBoxLayout(self)
        cardLayout.setContentsMargins(12, 12, 16, 14)
        cardLayout.setSpacing(12)
        self.portraitHolder = QVBoxLayout()
        cardLayout.addLayout(self.portraitHolder)
        self.portrait = None
        self.bossNumber = None

        # name, health bar + how it works
        wordsLayout = QVBoxLayout()
        wordsLayout.setSpacing(4)
        wordsLayout.addWidget(QLabel("BOSS FIGHT", objectName="BossCardHeading"))
        self.nameLabel = QLabel("", objectName="BossCardName")
        wordsLayout.addWidget(self.nameLabel)
        self.healthBar = QProgressBar(objectName="BossBar")
        self.healthBar.setTextVisible(False)
        self.healthBar.setFixedHeight(12)
        wordsLayout.addWidget(self.healthBar)
        self.healthLabel = QLabel("", objectName="BossCardHealth")
        wordsLayout.addWidget(self.healthLabel)
        howItWorksLabel = QLabel("Every minute you stay focused in a session hits it. Opening distractions heals it.", objectName="BossCardHint")
        howItWorksLabel.setWordWrap(True)
        wordsLayout.addWidget(howItWorksLabel)
        cardLayout.addLayout(wordsLayout, 1)
        self.shownMinutesLeft = None
        self.hide()

    def refresh(self):
        state = climbing.climbState()
        if not state["atBoss"] or state["finished"]:
            self.hide()
            return

        # new boss, swap the portrait
        if state["bossesBeaten"] != self.bossNumber:
            if self.portrait is not None:
                self.portrait.deleteLater()
            self.portrait = BossPortrait(state["bossesBeaten"], 76)
            self.portraitHolder.addWidget(self.portrait, alignment=Qt.AlignmentFlag.AlignTop)
            self.bossNumber = state["bossesBeaten"]
            self.shownMinutesLeft = None

        # health bar is in tenths of a minute so it moves smoothly, jumps the first time then slides after
        bossHealth = climbing.bossHealth(state["bossesBeaten"])
        minutesLeft = climbing.bossMinutesLeft()
        self.nameLabel.setText(bossName(state["bossesBeaten"]))
        self.healthBar.setRange(0, bossHealth * 10)
        if self.shownMinutesLeft is None:
            self.healthBar.setValue(int(minutesLeft * 10))
        else:
            animations.animateValue(self.healthBar.value(), int(minutesLeft * 10), lambda value: self.healthBar.setValue(int(value)), 500)
        self.shownMinutesLeft = minutesLeft
        self.healthLabel.setText(str(int(math.ceil(minutesLeft))) + " of " + str(bossHealth) + " focus minutes left")
        self.show()

    # little hurt shake when a focus minute lands
    def hit(self):
        if self.portrait is not None:
            self.portrait.hurt()






# Full map page, swaps in where the dashboard is. Info card on top, big scrollable map under it

class MapHome(QWidget):
    def __init__(self, goBack):
        super().__init__()
        from arete.ui.settings_window import makeBackArrow

        self.viewedMountain = climbing.climbState()["mountainNumber"]
        pageLayout = QVBoxLayout(self)
        pageLayout.setContentsMargins(20, 6, 20, 12)
        pageLayout.setSpacing(10)



        # top row, back arrow + mountain name
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



        # info card, stage name + %, height climbed, progress bar, next goal + stage message
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
        self.stageMessageLabel = QLabel("", objectName="MapMessage")
        self.stageMessageLabel.setWordWrap(True)
        infoLayout.addWidget(self.stageMessageLabel)
        pageLayout.addWidget(infoCard)



        # the map, scrolls up and down only, arrows + banner float on top of it
        self.mapFrame = MapFrame(self.placeMap)
        pageLayout.addWidget(self.mapFrame, 1)
        self.scrollArea = QScrollArea(self.mapFrame, widgetResizable=True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sideScrollBar = self.scrollArea.horizontalScrollBar()
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # trackpads can still side scroll a hidden scroll bar, so lock it at 0
        sideScrollBar.rangeChanged.connect(lambda lowest, highest: sideScrollBar.setRange(0, 0) if highest > 0 else None)
        self.scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        self.mountainMap = MountainMap()
        self.mountainMap.zoom = MAP_PAGE_ZOOM
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




    # Layout

    # lays out the map, arrows + banner, rounds the corners, scrolls to you the first time
    def placeMap(self):
        mapWidth = self.mapFrame.width()
        self.scrollArea.setGeometry(0, 0, mapWidth, self.mapFrame.height())
        self.leftArrow.move(10, self.mapFrame.height() // 2 - 20)
        self.rightArrow.move(mapWidth - 50, self.mapFrame.height() // 2 - 20)

        # completed banner sits up top so the summit stays visible, locked one goes in the middle
        self.banner.setFixedWidth(mapWidth - 110)
        self.banner.move(55, 24 if self.banner.kind == "done" else self.mapFrame.height() // 2 - 75)

        roundedCorners = QPainterPath()
        roundedCorners.addRoundedRect(QRectF(0, 0, mapWidth, self.mapFrame.height()), 24, 24)
        self.scrollArea.setMask(QRegion(roundedCorners.toFillPolygon().toPolygon()))
        if self.needsFirstScroll and self.mapFrame.height() > 100:
            self.needsFirstScroll = False
            QTimer.singleShot(50, lambda: self.scrollToClimber(900))

    def refresh(self):
        self.mountainMap.refresh()
        self.updateInfo()




    # Info card + banner, for whichever mountain ur looking at

    def updateInfo(self):
        state = climbing.climbState()
        viewedMountain = mountains.MOUNTAINS[self.viewedMountain]
        bossesBeatenHere = max(0, min(state["bossesBeaten"] - self.viewedMountain * len(mountains.BOSS_CHECKPOINTS), len(mountains.BOSS_CHECKPOINTS)))

        # finished mountains show 100%, locked ones 0%
        percentUp = state["percent"]
        if self.viewedMountain < state["mountainNumber"]:
            percentUp = 100
        if self.viewedMountain > state["mountainNumber"]:
            percentUp = 0

        # stage name + message, "Trailhead" until you reach the first checkpoint
        stageNumber = mountains.stageNumber(percentUp)
        self.stageMessageLabel.setText(viewedMountain["stages"][stageNumber][1] if stageNumber >= 0 else viewedMountain["startMessage"])
        self.stageLabel.setText(viewedMountain["stages"][stageNumber][0] if stageNumber >= 0 else "Trailhead")
        self.percentLabel.setText(percentText(percentUp) + "%")
        self.metersLabel.setText(format(int(viewedMountain["heightMeters"] * percentUp / 100), ",") + " m of " + format(viewedMountain["heightMeters"], ",") + " m" + "  ·  " + "Bosses beaten " + str(bossesBeatenHere) + " of " + str(len(mountains.BOSS_CHECKPOINTS)))
        animations.animateValue(self.progressBar.value(), int(percentUp * 10), lambda value: self.progressBar.setValue(int(value)), 700)



        # completed / locked / still climbing, each gets its own pill colour + banner
        isLocked = self.viewedMountain > state["mountainNumber"]
        percentPillName = "MapPercent"
        if self.viewedMountain < state["mountainNumber"] or (self.viewedMountain == state["mountainNumber"] and state["finished"]):
            percentPillName = "MapPercentDone"
            self.percentLabel.setText("Completed")
            self.banner.showBanner("done", viewedMountain["name"] + " completed!", "You beat all " + str(len(mountains.BOSS_CHECKPOINTS)) + " bosses and reached the summit.")
        elif isLocked:
            percentPillName = "MapPercentLocked"
            self.banner.showBanner("locked", "Locked", "Beat " + mountains.MOUNTAINS[self.viewedMountain - 1]["name"] + " and its summit boss to unlock " + viewedMountain["name"] + ".")
        else:
            self.banner.hide()
        if self.percentLabel.objectName() != percentPillName:
            self.percentLabel.setObjectName(percentPillName)
            self.percentLabel.style().unpolish(self.percentLabel)
            self.percentLabel.style().polish(self.percentLabel)
        self.placeMap()



        # next goal line
        if isLocked:
            self.percentLabel.setText("Locked")
            self.goalLabel.setText("Beat " + mountains.MOUNTAINS[self.viewedMountain - 1]["shortName"] + " to unlock this mountain")
        elif self.viewedMountain < state["mountainNumber"]:
            self.goalLabel.setText("You climbed this whole mountain")
        elif state["finished"]:
            self.goalLabel.setText("You climbed all three mountains")
        elif state["atBoss"]:
            self.goalLabel.setText(bossName(state["bossesBeaten"]) + " has " + str(int(math.ceil(climbing.bossMinutesLeft()))) + " focus min of health left")
        elif state["nextBoss"] is not None:
            self.goalLabel.setText(percentText(state["nextBoss"] - state["totalPercent"]) + "% to " + bossName(state["bossesBeaten"]))




    # Switching mountains + scrolling

    # flip to another mountain, crossfades from a snapshot of the old one
    def switchMountain(self, mountainNumber, animate=True):
        if animate and self.mapFrame.width() > 0:
            oldMapSnapshot = QLabel(self.mapFrame)
            oldMapSnapshot.setPixmap(self.mapFrame.grab())
            oldMapSnapshot.setGeometry(0, 0, self.mapFrame.width(), self.mapFrame.height())
            oldMapSnapshot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            oldMapSnapshot.show()
            animations.fadeOutAndDelete(oldMapSnapshot, 320)
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

    # scroll so the climber sits just under the middle, duration 0 jumps there
    def scrollToClimber(self, duration=900):
        mapScrollBar = self.scrollArea.verticalScrollBar()
        targetScroll = max(0, min(int(self.mountainMap.markerPoint().y() - self.scrollArea.viewport().height() * 0.55), mapScrollBar.maximum()))
        if duration == 0:
            mapScrollBar.setValue(targetScroll)
            return
        animations.animateValue(mapScrollBar.value(), targetScroll, lambda value: mapScrollBar.setValue(int(value)), duration)
