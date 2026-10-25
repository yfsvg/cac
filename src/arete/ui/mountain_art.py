import math
import random
import re

from PySide6.QtCore import QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtSvg import QSvgRenderer

PICTURE_WIDTH = 420
PICTURE_HEIGHT = 2182
TREE_SHAPES = ("MLLHZ", "MLHVZ")
NAMED_COLORS = {"white": "#FFFFFF", "black": "#000000"}

loadedScenes = {}


def numbersIn(text):
    return [float(number) for number in re.findall(r"-?\d+\.?\d*", text)]


def attribute(attrs, name):
    found = re.search(r'\s' + name + r'="([^"]*)"', " " + attrs)
    if found is None:
        return None
    return found.group(1)


def orderedTrail(points):
    leftOver = list(points)
    start = max(leftOver, key=lambda point: point.y())
    leftOver.remove(start)
    ordered = [start]
    while len(leftOver) > 0:
        last = ordered[-1]
        nearest = min(leftOver, key=lambda point: (point.x() - last.x()) ** 2 + (point.y() - last.y()) ** 2)
        leftOver.remove(nearest)
        ordered.append(nearest)
    return ordered


class MountainScene:
    def __init__(self, pictureFile):
        text = open(pictureFile, encoding="utf-8").read()
        self.trailPoints = []
        self.rings = []
        self.trees = []
        keptText = text

        for match in re.finditer(r"<path ([^>]*?)/>", text):
            attrs = match.group(1)
            pathText = attribute(attrs, "d")
            if pathText is None:
                continue
            letters = "".join(re.findall(r"[A-Za-z]", pathText))
            numbers = numbersIn(pathText)

            if attribute(attrs, "stroke-width") == "8" and letters.count("M") > 20:
                for subPath in re.findall(r"M([^MCLHVZ]+)", pathText):
                    pointNumbers = numbersIn(subPath)
                    self.trailPoints.append(QPointF(pointNumbers[0], pointNumbers[1]))
                continue

            if attribute(attrs, "stroke-width") == "5" and attribute(attrs, "stroke") == "white" and "C" in letters:
                xs = numbers[0::2]
                ys = numbers[1::2]
                self.rings.append(QPointF((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
                continue

            if letters in TREE_SHAPES and attribute(attrs, "fill") is not None:
                xs = numbers[0::2]
                ys = numbers[1::2]
                treeHeight = max(ys) - min(ys)
                if treeHeight < 36 and min(ys) > 950:
                    self.addTree(pathText, attrs, letters)
                    keptText = keptText.replace(match.group(0), "", 1)

        self.rings.sort(key=lambda ring: -ring.y())
        self.trailPoints = orderedTrail(self.trailPoints)
        self.renderer = QSvgRenderer(QByteArray(keptText.encode("utf-8")))
        self.trail = QPainterPath(self.trailPoints[0])
        for point in self.trailPoints[1:]:
            self.trail.lineTo(point)
        self.ringFractions = []
        for ring in self.rings:
            self.ringFractions.append(self.closestFraction(ring))

    def addTree(self, pathText, attrs, letters):
        numbers = numbersIn(pathText)
        if letters == "MLLHZ":
            points = [QPointF(numbers[0], numbers[1]), QPointF(numbers[2], numbers[3]), QPointF(numbers[4], numbers[5]), QPointF(numbers[6], numbers[5])]
        else:
            points = [QPointF(numbers[0], numbers[1]), QPointF(numbers[2], numbers[3]), QPointF(numbers[4], numbers[3]), QPointF(numbers[4], numbers[5])]
        shape = QPainterPath(points[0])
        for point in points[1:]:
            shape.lineTo(point)
        shape.closeSubpath()
        fillName = attribute(attrs, "fill")
        color = QColor(NAMED_COLORS.get(fillName, fillName))
        opacity = 1.0
        for opacityName in ("opacity", "fill-opacity"):
            opacityText = attribute(attrs, opacityName)
            if opacityText is not None:
                opacity = opacity * float(opacityText)
        color.setAlphaF(color.alphaF() * opacity)
        bounds = shape.boundingRect()
        base = QPointF(bounds.center().x(), bounds.bottom())
        self.trees.append({"shape": shape, "color": color, "base": base, "height": bounds.height(), "phase": base.x() * 0.045 + base.y() * 0.013})

    def closestFraction(self, point):
        bestFraction = 0
        bestDistance = None
        for step in range(401):
            fraction = step / 400
            trailPoint = self.trail.pointAtPercent(fraction)
            distance = (trailPoint.x() - point.x()) ** 2 + (trailPoint.y() - point.y()) ** 2
            if bestDistance is None or distance < bestDistance:
                bestDistance = distance
                bestFraction = fraction
        return bestFraction

    def trailFraction(self, percent):
        position = percent / 100 * len(self.ringFractions)
        if position <= 0:
            return 0
        if position >= len(self.ringFractions):
            return self.ringFractions[-1]
        ringNumber = int(position)
        startFraction = 0
        if ringNumber > 0:
            startFraction = self.ringFractions[ringNumber - 1]
        endFraction = self.ringFractions[ringNumber]
        return startFraction + (endFraction - startFraction) * (position - ringNumber)


def sceneFor(pictureFile):
    key = str(pictureFile)
    if key not in loadedScenes:
        loadedScenes[key] = MountainScene(pictureFile)
    return loadedScenes[key]


def partOfPath(path, fraction):
    part = QPainterPath(path.pointAtPercent(0))
    steps = max(int(fraction * 300), 1)
    for step in range(1, steps + 1):
        part.lineTo(path.pointAtPercent(fraction * step / steps))
    return part


def windAmount(seconds):
    gust = 0.55 + 0.45 * math.sin(seconds * 0.35)
    return gust


def paintTrees(painter, scene, seconds, visibleTop, visibleBottom):
    painter.setPen(Qt.PenStyle.NoPen)
    gust = windAmount(seconds)
    for tree in scene.trees:
        base = tree["base"]
        if base.y() < visibleTop - 40 or base.y() - tree["height"] > visibleBottom + 40:
            continue
        sway = math.sin(seconds * 2.1 + tree["phase"]) * 0.13 * gust + 0.05 * gust
        bend = QTransform()
        bend.translate(base.x(), base.y())
        bend.shear(-sway, 0)
        bend.translate(-base.x(), -base.y())
        painter.setBrush(tree["color"])
        painter.drawPath(bend.map(tree["shape"]))


class Flyer:
    def __init__(self, kind, startTime, top, bottom, randomNumbers):
        self.kind = kind
        self.startTime = startTime
        self.goingRight = randomNumbers.random() < 0.5
        self.height = randomNumbers.uniform(top, bottom)
        self.speed = randomNumbers.uniform(28, 42)
        self.birdCount = randomNumbers.randint(3, 5)
        self.offsets = []
        for birdNumber in range(self.birdCount):
            self.offsets.append((-birdNumber * randomNumbers.uniform(14, 20), randomNumbers.uniform(-10, 10), randomNumbers.uniform(0, 6)))
        if kind == "plane":
            self.speed = randomNumbers.uniform(55, 70)

    def x(self, seconds):
        travelled = (seconds - self.startTime) * self.speed - 60
        if self.goingRight:
            return travelled
        return PICTURE_WIDTH - travelled

    def finished(self, seconds):
        return (seconds - self.startTime) * self.speed > PICTURE_WIDTH + 180

    def paint(self, painter, seconds):
        direction = 1 if self.goingRight else -1
        leadX = self.x(seconds)
        if self.kind == "plane":
            painter.setPen(QPen(QColor(255, 255, 255, 110), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(leadX - direction * 8, self.height), QPointF(leadX - direction * 110, self.height + 2))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 235))
            body = QPainterPath()
            body.addRoundedRect(QRectF(leadX - 9, self.height - 1.6, 18, 3.2), 1.6, 1.6)
            wing = QPainterPath(QPointF(leadX + direction * 1, self.height))
            wing.lineTo(QPointF(leadX - direction * 4, self.height + 7))
            wing.lineTo(QPointF(leadX - direction * 6, self.height + 7))
            wing.lineTo(QPointF(leadX - direction * 3, self.height))
            tail = QPainterPath(QPointF(leadX - direction * 7, self.height))
            tail.lineTo(QPointF(leadX - direction * 10, self.height - 5))
            tail.lineTo(QPointF(leadX - direction * 9, self.height))
            painter.drawPath(body.united(wing).united(tail))
            return
        painter.setPen(QPen(QColor(255, 255, 255, 215), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for behind, up, flapPhase in self.offsets:
            birdX = leadX + direction * behind
            birdY = self.height + up + math.sin(seconds * 1.3 + flapPhase) * 2
            flap = math.sin(seconds * 9 + flapPhase) * 3.5
            bird = QPainterPath(QPointF(birdX - 6, birdY - flap))
            bird.quadTo(QPointF(birdX - 3, birdY - 2.5 - flap * 0.3), QPointF(birdX, birdY))
            bird.quadTo(QPointF(birdX + 3, birdY - 2.5 - flap * 0.3), QPointF(birdX + 6, birdY - flap))
            painter.drawPath(bird)


class Sky:
    def __init__(self):
        self.flyers = []
        self.randomNumbers = random.Random()
        self.nextBirdTime = 2
        self.nextPlaneTime = 12

    def update(self, seconds, visibleTop, visibleBottom):
        self.flyers = [flyer for flyer in self.flyers if not flyer.finished(seconds)]
        if visibleBottom - visibleTop < 120:
            return
        if seconds >= self.nextBirdTime:
            top = visibleTop + 40
            bottom = visibleTop + (visibleBottom - visibleTop) * 0.55
            self.flyers.append(Flyer("birds", seconds, top, bottom, self.randomNumbers))
            self.nextBirdTime = seconds + self.randomNumbers.uniform(8, 14)
        if seconds >= self.nextPlaneTime and visibleTop < 900:
            top = visibleTop + 30
            self.flyers.append(Flyer("plane", seconds, top, top + 140, self.randomNumbers))
            self.nextPlaneTime = seconds + self.randomNumbers.uniform(25, 45)

    def paint(self, painter, seconds):
        for flyer in self.flyers:
            flyer.paint(painter, seconds)
