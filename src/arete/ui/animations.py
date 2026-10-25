import random

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget

CONFETTI_COLORS = ["#FFC23D", "#5FE0B8", "#FF6FA8", "#42A0EE", "#9B6BF2", "#FF8A5B"]

runningAnimations = []


def keepAlive(animation):
    runningAnimations.append(animation)
    animation.finished.connect(lambda: forget(animation))
    animation.start()


def forget(animation):
    if animation in runningAnimations:
        runningAnimations.remove(animation)


def fadeIn(widget, duration=320, delay=0):
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(0.0)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.finished.connect(lambda: widget.setGraphicsEffect(None))
    QTimer.singleShot(delay, lambda: keepAlive(animation))


def staggerIn(widgets, gap=55, duration=360):
    delay = 0
    for widget in widgets:
        fadeIn(widget, duration, delay)
        delay = delay + gap


def slideWindowIn(window, distance=60, duration=380):
    endPosition = window.pos()
    window.move(endPosition + QPoint(distance, 0))
    window.setWindowOpacity(0.0)
    moveAnimation = QPropertyAnimation(window, b"pos")
    moveAnimation.setDuration(duration)
    moveAnimation.setStartValue(endPosition + QPoint(distance, 0))
    moveAnimation.setEndValue(endPosition)
    moveAnimation.setEasingCurve(QEasingCurve.Type.OutCubic)
    fadeAnimation = QPropertyAnimation(window, b"windowOpacity")
    fadeAnimation.setDuration(duration)
    fadeAnimation.setStartValue(0.0)
    fadeAnimation.setEndValue(1.0)
    keepAlive(moveAnimation)
    keepAlive(fadeAnimation)


def fadeWindowIn(window, duration=260):
    window.setWindowOpacity(0.0)
    animation = QPropertyAnimation(window, b"windowOpacity")
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(1.0)
    keepAlive(animation)


def slideWidgetIn(widget, distance=30, duration=380):
    endPosition = widget.pos()
    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(endPosition + QPoint(0, distance))
    animation.setEndValue(endPosition)
    animation.setEasingCurve(QEasingCurve.Type.OutBack)
    keepAlive(animation)


def countUp(label, endText, duration=600):
    try:
        endValue = float(endText)
    except ValueError:
        label.setText(endText)
        return
    # stop any count up already going on this label, otherwise the older one can finish last + leave the wrong number
    oldAnimation = getattr(label, "countAnimation", None)
    if oldAnimation is not None:
        oldAnimation.stop()
        forget(oldAnimation)
    decimals = 0
    if "." in endText:
        decimals = len(endText.split(".")[1])
    animation = QVariantAnimation()
    animation.setDuration(duration)
    animation.setStartValue(0.0)
    animation.setEndValue(endValue)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(lambda value: label.setText(numberText(value, decimals)))
    animation.finished.connect(lambda: label.setText(endText))
    label.countAnimation = animation
    keepAlive(animation)


def numberText(value, decimals):
    if decimals == 0:
        return str(int(round(value)))
    return str(round(value, decimals))


def animateValue(startValue, endValue, whenChanged, duration=500):
    animation = QVariantAnimation()
    animation.setDuration(duration)
    animation.setStartValue(float(startValue))
    animation.setEndValue(float(endValue))
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.valueChanged.connect(whenChanged)
    keepAlive(animation)


def expand(body, duration=240):
    fullHeight = body.sizeHint().height()
    body.setMaximumHeight(0)
    body.show()
    animation = QPropertyAnimation(body, b"maximumHeight")
    animation.setDuration(duration)
    animation.setStartValue(0)
    animation.setEndValue(fullHeight)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.finished.connect(lambda: body.setMaximumHeight(16777215))
    keepAlive(animation)


def collapse(body, duration=200):
    animation = QPropertyAnimation(body, b"maximumHeight")
    animation.setDuration(duration)
    animation.setStartValue(body.height())
    animation.setEndValue(0)
    animation.setEasingCurve(QEasingCurve.Type.InCubic)
    animation.finished.connect(lambda: finishCollapse(body))
    keepAlive(animation)


def finishCollapse(body):
    body.hide()
    body.setMaximumHeight(16777215)


def fadeOutAndDelete(widget, duration=300):
    effect = QGraphicsOpacityEffect(widget)
    effect.setOpacity(1.0)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(1.0)
    animation.setEndValue(0.0)
    animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
    animation.finished.connect(widget.deleteLater)
    keepAlive(animation)


def shake(widget, distance=12):
    startPosition = widget.pos()
    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(450)
    steps = [0, distance, -distance, distance * 0.7, -distance * 0.7, distance * 0.35, -distance * 0.35, 0]
    for stepNumber in range(len(steps)):
        animation.setKeyValueAt(stepNumber / (len(steps) - 1), startPosition + QPoint(int(steps[stepNumber]), 0))
    keepAlive(animation)


class Confetti(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setGeometry(parent.rect())
        self.pieces = []
        randomNumbers = random.Random()
        for pieceNumber in range(70):
            self.pieces.append({
                "x": self.width() / 2 + randomNumbers.uniform(-30, 30),
                "y": self.height() * 0.45,
                "speedX": randomNumbers.uniform(-260, 260),
                "speedY": randomNumbers.uniform(-420, -160),
                "spin": randomNumbers.uniform(-540, 540),
                "size": randomNumbers.uniform(5, 9),
                "color": QColor(randomNumbers.choice(CONFETTI_COLORS)),
            })
        self.age = 0
        self.timer = QTimer(self, interval=16, timeout=self.step)
        self.timer.start()
        self.show()
        self.raise_()

    def step(self):
        self.age = self.age + 0.016
        for piece in self.pieces:
            piece["speedY"] = piece["speedY"] + 700 * 0.016
            piece["speedX"] = piece["speedX"] * 0.985
            piece["x"] = piece["x"] + piece["speedX"] * 0.016
            piece["y"] = piece["y"] + piece["speedY"] * 0.016
        if self.age > 1.8:
            self.timer.stop()
            self.deleteLater()
            return
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        fade = 1.0
        if self.age > 1.2:
            fade = max(0.0, 1 - (self.age - 1.2) / 0.6)
        for piece in self.pieces:
            color = QColor(piece["color"])
            color.setAlphaF(fade)
            painter.save()
            painter.translate(QPointF(piece["x"], piece["y"]))
            painter.rotate(piece["spin"] * self.age)
            painter.setBrush(color)
            painter.drawRect(int(-piece["size"] / 2), int(-piece["size"] / 4), int(piece["size"]), int(piece["size"] / 2))
            painter.restore()


def confetti(widget):
    return Confetti(widget)
