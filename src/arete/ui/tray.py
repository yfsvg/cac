"""Menu bar / system tray icon. Clicking it opens the dashboard."""
"""what actually appears on the widget"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from arete.ui import animations
from arete.ui.dashboard import Dashboard


def mountainIcon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    background = QLinearGradient(0, 0, 64, 64)
    background.setColorAt(0, QColor("#8B6CFF"))
    background.setColorAt(1, QColor("#4B33C9"))
    painter.setBrush(background)
    painter.drawEllipse(QPointF(32, 32), 31, 31)
    mountain = QPainterPath(QPointF(10, 50))
    mountain.lineTo(QPointF(32, 11))
    mountain.lineTo(QPointF(54, 50))
    mountain.lineTo(QPointF(42, 50))
    mountain.lineTo(QPointF(32, 32))
    mountain.lineTo(QPointF(22, 50))
    mountain.closeSubpath()
    painter.setBrush(QColor("white"))
    painter.drawPath(mountain)
    painter.drawRoundedRect(QRectF(24, 39, 16, 4), 2, 2)
    painter.end()
    return QIcon(pixmap)


def trayIcon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#7C5CFF"))
    painter.drawEllipse(QPointF(32, 32), 31, 31)
    mountain = QPainterPath(QPointF(8, 50))
    mountain.lineTo(QPointF(32, 14))
    mountain.lineTo(QPointF(56, 50))
    mountain.closeSubpath()
    painter.setBrush(QColor("white"))
    painter.drawPath(mountain)
    snow = QPainterPath(QPointF(24, 26))
    snow.lineTo(QPointF(32, 14))
    snow.lineTo(QPointF(40, 26))
    snow.lineTo(QPointF(32, 22))
    snow.closeSubpath()
    painter.setBrush(QColor("#C9D8FF"))
    painter.drawPath(snow)
    painter.end()
    return QIcon(pixmap)


class Tray(QSystemTrayIcon):

    def __init__(self) -> None:

        super().__init__(trayIcon())
        QApplication.instance().setWindowIcon(mountainIcon())
        self.dashboard = Dashboard()
        # enforcer warnings show up as tray notifs
        self.dashboard.enforcer.notify = self.showMessage
        self.activated.connect(self.openDashboard)
        self.show()


    def openDashboard(self) -> None:
        if not self.dashboard.isVisible():
            self.dashboard.show()
            animations.slideWindowIn(self.dashboard)
            self.dashboard.playEntrance()
        # show and raise only hides it but daemon keeps on going baby
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()
