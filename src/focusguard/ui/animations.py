from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect

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
