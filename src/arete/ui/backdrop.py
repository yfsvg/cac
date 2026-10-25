import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPixmap, QRadialGradient

savedPictures = {}


def backdropPicture(width, height, dark, pixelRatio):
    key = (width, height, dark, pixelRatio)
    if key not in savedPictures:
        savedPictures.clear()
        picture = QPixmap(int(width * pixelRatio), int(height * pixelRatio))
        picture.setDevicePixelRatio(pixelRatio)
        picture.fill(Qt.GlobalColor.transparent)
        painter = QPainter(picture)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if dark:
            paintNight(painter, width, height)
        else:
            paintDay(painter, width, height)
        painter.end()
        savedPictures[key] = picture
    return savedPictures[key]


def paintDay(painter, width, height):
    sky = QLinearGradient(0, 0, 0, height)
    sky.setColorAt(0, QColor("#8FD0FF"))
    sky.setColorAt(0.35, QColor("#D4EDFF"))
    sky.setColorAt(1, QColor("#F1F8FF"))
    painter.fillRect(QRectF(0, 0, width, height), sky)

    sunCenter = QPointF(width * 0.6, 36)
    sunGlow = QRadialGradient(sunCenter, 140)
    sunGlow.setColorAt(0, QColor(255, 226, 130, 150))
    sunGlow.setColorAt(1, QColor(255, 226, 130, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(sunGlow)
    painter.drawEllipse(sunCenter, 140, 140)
    painter.setBrush(QColor("#FFD84D"))
    painter.drawEllipse(sunCenter, 15, 15)

    painter.setBrush(QColor(255, 255, 255, 210))
    for cloudX, cloudY, cloudSize in ((width * 0.25, 24, 13), (width * 0.66, 38, 10)):
        drawCloud(painter, cloudX, cloudY, cloudSize)

    hillColors = ("#CDEBD8", "#B6E0C4", "#A2D6B3")
    for hillNumber in range(3):
        hillTop = height - 150 + hillNumber * 45
        hill = QPainterPath(QPointF(0, hillTop))
        hill.quadTo(QPointF(width * 0.25, hillTop - 50 + hillNumber * 10), QPointF(width * 0.5, hillTop - 10))
        hill.quadTo(QPointF(width * 0.75, hillTop + 25), QPointF(width, hillTop - 30))
        hill.lineTo(QPointF(width, height))
        hill.lineTo(QPointF(0, height))
        hill.closeSubpath()
        painter.setBrush(QColor(hillColors[hillNumber]))
        painter.drawPath(hill)


def paintNight(painter, width, height):
    sky = QLinearGradient(0, 0, 0, height)
    sky.setColorAt(0, QColor("#0B0824"))
    sky.setColorAt(0.5, QColor("#171139"))
    sky.setColorAt(1, QColor("#261D5A"))
    painter.fillRect(QRectF(0, 0, width, height), sky)

    randomNumbers = random.Random(9)
    painter.setPen(Qt.PenStyle.NoPen)
    for starNumber in range(160):
        starColor = QColor(255, 255, 255, randomNumbers.randint(60, 220))
        painter.setBrush(starColor)
        starSize = randomNumbers.choice([0.7, 0.9, 1.2, 1.6])
        painter.drawEllipse(QPointF(randomNumbers.random() * width, randomNumbers.random() * height * 0.75), starSize, starSize)

    moonCenter = QPointF(width * 0.6, 36)
    moonGlow = QRadialGradient(moonCenter, 120)
    moonGlow.setColorAt(0, QColor(220, 210, 255, 70))
    moonGlow.setColorAt(1, QColor(220, 210, 255, 0))
    painter.setBrush(moonGlow)
    painter.drawEllipse(moonCenter, 120, 120)
    moon = QPainterPath()
    moon.addEllipse(moonCenter, 15, 15)
    moonBite = QPainterPath()
    moonBite.addEllipse(QPointF(moonCenter.x() + 7, moonCenter.y() - 5), 13, 13)
    painter.setBrush(QColor("#F5E9C8"))
    painter.drawPath(moon.subtracted(moonBite))

    ridgeColors = ("#2A2163", "#211A50", "#191340")
    for ridgeNumber in range(3):
        ridgeBase = height - 130 + ridgeNumber * 45
        ridge = QPainterPath(QPointF(0, ridgeBase))
        ridgeX = 0
        peakNumber = 0
        while ridgeX < width:
            peakWidth = 70 + (peakNumber * 37 + ridgeNumber * 23) % 60
            peakHeight = 35 + (peakNumber * 29 + ridgeNumber * 17) % 40
            ridge.lineTo(QPointF(ridgeX + peakWidth / 2, ridgeBase - peakHeight))
            ridge.lineTo(QPointF(ridgeX + peakWidth, ridgeBase))
            ridgeX = ridgeX + peakWidth
            peakNumber = peakNumber + 1
        ridge.lineTo(QPointF(width, height))
        ridge.lineTo(QPointF(0, height))
        ridge.closeSubpath()
        painter.setBrush(QColor(ridgeColors[ridgeNumber]))
        painter.drawPath(ridge)


def drawCloud(painter, cloudX, cloudY, cloudSize):
    cloud = QPainterPath()
    cloud.addRoundedRect(QRectF(cloudX, cloudY, cloudSize * 3.4, cloudSize), cloudSize / 2, cloudSize / 2)
    puff = QPainterPath()
    puff.addEllipse(QPointF(cloudX + cloudSize * 1.2, cloudY + cloudSize * 0.1), cloudSize * 0.75, cloudSize * 0.75)
    smallPuff = QPainterPath()
    smallPuff.addEllipse(QPointF(cloudX + cloudSize * 2.2, cloudY + cloudSize * 0.2), cloudSize * 0.55, cloudSize * 0.55)
    painter.drawPath(cloud.united(puff).united(smallPuff))
