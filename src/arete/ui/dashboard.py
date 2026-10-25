# Using QWidget to make the window. For mac this appears in the top corner
# Dashboard is split into four segments:
# 1. Streak + welcome msg, then the climb card
# 2. Daily stats
# 3. Weekly stats
# 4. Settings and config (read figma doc for more)
#
# BEFORE MAKING EDITS READ GDOC SECTION "Dashboard priorities"


import math
import os
import threading
import time
from datetime import date, timedelta

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QPainter, QPainterPath, QPaintEvent, QPen, QPixmap, QTransform

from arete.ai import vision
from arete.ai.site_memory import siteCategory
from arete.core.classifier import classifyTypeOfApp, isIgnoredApp, isUnproductiveSite, siteRoot
from arete.core import climbing, enforcement, keep_alive, mountains, policy, session, setting_changes
from arete.core.enforcement import Enforcer
from arete.storage import memory, time_tracking
from arete.ui import animations, backdrop
from arete.ui.boss_fight import BossToast, bossName
from arete.ui.climb_view import CLIMB_STYLE, BossCard, ClimbCard, MapHome, climbSummary
from arete.ui.settings_window import SettingsPage
from arete.ui.pause_screen import BreakBadge, CheckInScreen, PauseScreen
from arete.ui.session_screen import PANEL_STYLE, SessionCard, SessionDoneToast, SessionPanel
from arete.ui.theme import applyTheme, choiceFor, getColors, getTheme, resolveTheme, setTheme, systemTheme
from arete.platform import get_backend


# Status chip text colours (theme tokens)
GOOD = "@green"
PERFECT = "@green"
OK = "@orange"
NO_DATA = "@onSurfaceVariant"

STYLE = """
    QWidget#Dashboard {
        background-color: transparent;
        border-radius: 28px;
        border: 1px solid @outlineVariant;
    }

    QScrollArea, QWidget#Content { background: transparent; border: none; }
    QScrollBar:vertical { background: transparent; width: 14px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { height: 0; background: none; }

    QLabel { color: @onSurface; }
    QLabel#AppName { color: @onSurface; font-size: 15px; font-weight: 800; }
    QLabel#Hello { color: @onPrimaryContainer; font-size: 32px; font-weight: 700; }
    QLabel#CurrentMountain { color: @onPrimaryContainer; font-size: 14px; }

    QLabel#Section { color: @onSurface; font-size: 22px; font-weight: 600; }
    QLabel#BigNumber { font-size: 44px; font-weight: 800; }
    QLabel#Caption { font-size: 12px; }

    QLabel#Chip {
        font-size: 12px;
        font-weight: 600;
        background-color: @chipBackground;
        border-radius: 10px;
        padding: 3px 10px;
    }

    QLabel#EmptyText { font-size: 13px; color: @onSurfaceVariant; padding: 4px 0 4px 0; }

    QFrame#Hero { background-color: @primaryContainer; border-radius: 28px; border: 1px solid @cardBorder; }
    QFrame#StatCard { border-radius: 24px; border: 1px solid @cardBorder; }

    QFrame#TimeCard { background-color: @surfaceContainerLow; border-radius: 24px; border: 1px solid @cardBorder; }
    QLabel#SplitTitle { color: @onSurface; font-size: 15px; font-weight: 600; }

    QLabel#RowName { color: @onSurface; font-size: 13px; font-weight: 600; }
    QLabel#RowKind { color: @onSurfaceVariant; font-size: 12px; }
    QLabel#RowTime { color: @onSurface; font-size: 13px; }
    QLabel#DotNeutral { background-color: @secondary; border-radius: 5px; }
    QLabel#DotBrowser { background-color: @blue; border-radius: 5px; }
    QLabel#DotUnproductive { background-color: @error; border-radius: 5px; }
    QLabel#DotProductive { background-color: @green; border-radius: 5px; }


    QPushButton#DropdownHeader {
        color: @onPrimary;
        font-size: 15px;
        font-weight: 600;
        text-align: left;
        background-color: @primary;
        border: none;
        border-bottom: 4px solid @primaryShadow;
        border-radius: 16px;
        padding: 12px 16px 10px 40px;
    }
    QPushButton#DropdownHeader:hover { background-color: @primaryHover; }
    QPushButton#DropdownHeader:pressed { border-bottom: 1px solid @primaryShadow; padding-top: 15px; }

    QPushButton#ThemeButton {
        color: @onSurface;
        font-size: 16px;
        background-color: @surfaceContainerHigh;
        border: none;
        border-radius: 16px;
    }
    QPushButton#ThemeButton:hover { background-color: @surfaceContainerHighest; }

    QFrame#SessionCard { background-color: @surfaceContainerLow; border-radius: 14px; border: 1px solid @cardBorder; }
    QLabel#SessionTime { color: @onSurface; font-size: 12px; font-weight: 700; }
    QProgressBar#SessionBar { background-color: @surfaceContainerHighest; border: none; border-radius: 2px; }
    QProgressBar#SessionBar::chunk { background-color: @primary; border-radius: 2px; }
""" + CLIMB_STYLE + PANEL_STYLE

DOT_NAMES = {
    "neutral": "DotNeutral",
    "browser": "DotBrowser",
    "unproductive": "DotUnproductive",
    "productive": "DotProductive",
}

MAX_NAME_LENGTH = 30
STAT_ICONS = ["target", "clock", "bounce"]


# small widgets, labels + stat cards

class RoundScrollBar(QScrollBar):
    def __init__(self) -> None:
        super().__init__(Qt.Orientation.Vertical)
        self.setFixedWidth(14)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        colors = getColors()
        trackRect = QRectF(self.rect()).adjusted(3, 6, -3, -6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(colors["surfaceContainerHigh"]))
        painter.drawRoundedRect(trackRect, trackRect.width() / 2, trackRect.width() / 2)
        if self.maximum() <= self.minimum():
            return
        visibleShare = self.pageStep() / (self.maximum() - self.minimum() + self.pageStep())
        handleHeight = max(trackRect.height() * visibleShare, 40)
        movedShare = (self.value() - self.minimum()) / (self.maximum() - self.minimum())
        handleTop = trackRect.top() + (trackRect.height() - handleHeight) * movedShare
        handleRect = QRectF(trackRect.left(), handleTop, trackRect.width(), handleHeight)
        handleColor = QColor(colors["primary"])
        if self.underMouse() or self.isSliderDown():
            handleColor = QColor(colors["primaryHover"])
        painter.setBrush(handleColor)
        painter.drawRoundedRect(handleRect, handleRect.width() / 2, handleRect.width() / 2)

    def enterEvent(self, event) -> None:
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.update()
        super().leaveEvent(event)


def stopSideScrolling(scrollArea) -> None:
    scrollArea.setVerticalScrollBar(RoundScrollBar())
    scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    sideBar = scrollArea.horizontalScrollBar()
    sideBar.rangeChanged.connect(lambda lowest, highest: sideBar.setRange(0, 0) if highest > 0 else None)


def label(text: str, name: str, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft) -> QLabel:
    newLabel = QLabel(text, objectName=name, alignment=align)
    newLabel.setWordWrap(True)
    return newLabel


class AppNameLabel(QLabel):
    def __init__(self) -> None:
        super().__init__("Arete", objectName="AppName")
        self.clicks = 0
        self.lastClick = 0
        self.popup = None

    def mousePressEvent(self, event) -> None:
        if time.time() - self.lastClick > 1:
            self.clicks = 0
        self.lastClick = time.time()
        self.clicks = self.clicks + 1
        if self.clicks == 5:
            self.clicks = 0
            self.showSurprise()

    def showSurprise(self) -> None:
        picture = QPixmap(os.path.join(os.path.dirname(__file__), "parth.png"))
        self.popup = QLabel(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.popup.setPixmap(picture)
        center = self.window().geometry().center()
        self.popup.move(center.x() - picture.width() // 2, center.y() - picture.height() // 2)
        self.popup.show()
        animations.fadeWindowIn(self.popup)
        QTimer.singleShot(2000, self.popup.close)


class StatCard(QFrame):
    def __init__(self, number: str, caption: str, status: str, statusColor: str, colorFamily: str) -> None:
        super().__init__(objectName="StatCard")

        # Each card is a tonal container, text uses the matching "on" colour
        containerColor = "@" + colorFamily + "Container"
        onContainerColor = "@on" + colorFamily[0].upper() + colorFamily[1:] + "Container"
        self.cardStyle = f"QFrame#StatCard {{ background-color: {containerColor}; }} QLabel {{ color: {onContainerColor}; }}"
        self.setStyleSheet(applyTheme(self.cardStyle))
        self.setFixedHeight(150)

        # Ignore caption width so all 3 cards split the row evenly
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

        centerAlign = Qt.AlignmentFlag.AlignHCenter
        cardLayout = QVBoxLayout(self)
        cardLayout.setContentsMargins(8, 14, 8, 14)
        cardLayout.setSpacing(0)
        self.numberLabel = label(number, "BigNumber", centerAlign)
        # the number its counting up to, can be different from whats on screen mid animation
        self.numberTarget = number
        cardLayout.addWidget(self.numberLabel)
        cardLayout.addWidget(label(caption, "Caption", centerAlign))
        cardLayout.addStretch()

        self.iconName = ""
        self.iconColor = onContainerColor
        self.hoverAmount = 0

        self.statusChip = QLabel(status, objectName="Chip")
        self.chipStyle = f"color: {statusColor};"
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))
        cardLayout.addWidget(self.statusChip, alignment=centerAlign)

    def restyle(self) -> None:
        self.setStyleSheet(applyTheme(self.cardStyle))
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        iconColor = QColor(applyTheme(self.iconColor))
        if self.hoverAmount > 0:
            glowColor = QColor(iconColor)
            glowColor.setAlpha(int(90 * self.hoverAmount))
            painter.setPen(QPen(glowColor, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5), 23, 23)
        iconColor.setAlpha(int(150 + 100 * self.hoverAmount))
        painter.translate(24, 24)
        painter.rotate(-15 * self.hoverAmount)
        painter.scale(1 + 0.2 * self.hoverAmount, 1 + 0.2 * self.hoverAmount)
        drawStatIcon(painter, self.iconName, iconColor)

    def enterEvent(self, event) -> None:
        animations.animateValue(self.hoverAmount, 1, self.setHover, 220)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        animations.animateValue(self.hoverAmount, 0, self.setHover, 260)
        super().leaveEvent(event)

    def setHover(self, amount) -> None:
        self.hoverAmount = amount
        self.update()


    def setValues(self, number: str, status: str, statusColor: str) -> None:
        self.numberTarget = number
        if number != self.numberLabel.text() and self.isVisible():
            animations.countUp(self.numberLabel, number)
        else:
            self.numberLabel.setText(number)
        self.statusChip.setText(status)
        self.chipStyle = f"color: {statusColor};"
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))




# Stat card wording, always encouraging so it never feels like a punishment

class HeroCard(QFrame):
    def __init__(self) -> None:
        super().__init__(objectName="Hero")
        self.startTime = time.time()
        self.bobTimer = QTimer(self, interval=50, timeout=self.update)

    def showEvent(self, event) -> None:
        self.bobTimer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self.bobTimer.stop()
        super().hideEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        heroShape = QPainterPath()
        heroShape.addRoundedRect(QRectF(self.rect()), 28, 28)
        painter.setClipPath(heroShape)
        colors = getColors()
        sunColor = QColor(colors["trail"])
        sunColor.setAlpha(200)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(sunColor)
        seconds = time.time() - self.startTime
        sunBob = math.sin(seconds * 1.6) * 3
        painter.drawEllipse(QPointF(self.width() - 70, 34 + sunBob), 16, 16)
        cloudColor = QColor("white")
        cloudColor.setAlpha(170)
        painter.setBrush(cloudColor)
        for cloudSpeed, cloudY, cloudSize, cloudStart in ((9, 22, 9, 0), (6, 52, 7, 170)):
            cloudX = (cloudStart + seconds * cloudSpeed) % (self.width() + 120) - 60
            cloudShape = QPainterPath()
            cloudShape.addRoundedRect(QRectF(cloudX, cloudY, cloudSize * 3.4, cloudSize), cloudSize / 2, cloudSize / 2)
            cloudPuff = QPainterPath()
            cloudPuff.addEllipse(QPointF(cloudX + cloudSize * 1.3, cloudY + cloudSize * 0.1), cloudSize * 0.75, cloudSize * 0.75)
            painter.drawPath(cloudShape.united(cloudPuff))
        backColor = QColor(colors["primary"])
        backColor.setAlpha(60)
        frontColor = QColor(colors["primary"])
        frontColor.setAlpha(110)
        bottom = self.height()
        for mountainColor, peaks in ((backColor, ((-150, 60), (-95, 30), (-40, 55))), (frontColor, ((-120, 75), (-60, 45), (0, 80)))):
            ridge = QPainterPath(QPointF(self.width() - 200, bottom))
            for peakX, peakY in peaks:
                ridge.lineTo(QPointF(self.width() + peakX, peakY))
            ridge.lineTo(QPointF(self.width(), bottom))
            ridge.closeSubpath()
            painter.setBrush(mountainColor)
            painter.drawPath(ridge)
        snowColor = QColor("white")
        snowColor.setAlpha(150)
        snowCap = QPainterPath(QPointF(self.width() - 60 - 11, 45 + 9))
        snowCap.lineTo(QPointF(self.width() - 60, 45))
        snowCap.lineTo(QPointF(self.width() - 60 + 12, 45 + 9))
        snowCap.closeSubpath()
        painter.setBrush(snowColor)
        painter.drawPath(snowCap)


def drawStatIcon(painter: QPainter, iconName: str, color: QColor) -> None:
    painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if iconName == "target":
        painter.drawEllipse(QPointF(0, 0), 8, 8)
        painter.drawEllipse(QPointF(0, 0), 4, 4)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(0, 0), 1.2, 1.2)
    elif iconName == "clock":
        painter.drawEllipse(QPointF(0, 0), 8, 8)
        painter.drawLine(QPointF(0, 0), QPointF(0, -5))
        painter.drawLine(QPointF(0, 0), QPointF(3.5, 2))
    elif iconName == "bounce":
        bounce = QPainterPath(QPointF(-8, -6))
        bounce.quadTo(QPointF(-4, 10), QPointF(0, 2))
        bounce.quadTo(QPointF(4, -8), QPointF(8, -4))
        painter.drawPath(bounce)
        painter.drawLine(QPointF(8, -4), QPointF(4, -6))
        painter.drawLine(QPointF(8, -4), QPointF(7, 0))


def focusedStatus(percent):
    if percent is None:
        return "No data yet", NO_DATA
    if percent >= 90:
        return "Perfect!", PERFECT
    if percent >= 75:
        return "Looking good!", GOOD
    if percent >= 50:
        return "Doing OK", OK
    return "Keep going!", OK


def hoursStatus(hours, goodHours):
    if hours == 0:
        return "Just getting started", NO_DATA
    if hours >= goodHours:
        return "Perfect!", PERFECT
    if hours >= goodHours / 3:
        return "Looking good!", GOOD
    return "Doing OK", OK


def reboundStatus(averageBreaks):
    if averageBreaks is None:
        return "No breaks yet", NO_DATA
    if averageBreaks <= 1.5:
        return "Perfect!", PERFECT
    if averageBreaks <= 2.5:
        return "Looking good!", GOOD
    return "Doing OK", OK


def numberText(value):
    if value is None:
        return "–"
    return str(value)





# time tracked helpers, formatting names + times

def isSiteName(name):
    return "." in name and " " not in name


def durationText(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return str(hours) + "h " + str(minutes) + "m"
    return str(minutes) + "m " + str(seconds % 60) + "s"


def dayText(dayName, today):
    dayDate = date.fromisoformat(dayName)
    if dayDate == today:
        return "Today"
    if dayDate == today - timedelta(days=1):
        return "Yesterday"
    return dayDate.strftime("%a %b ") + str(dayDate.day)


def shownRows(rows, limit):
    sortedRows = sorted(rows, key=lambda row: -row[3])
    returnVal = []
    for name, kindText, dotKind, seconds in sortedRows[:limit]:
        returnVal.append((name, kindText, dotKind, durationText(seconds)))
    return returnVal





# productive vs unproductive bar up top

class SplitBar(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedHeight(14)
        self.productiveSeconds = 0
        self.shownFraction = 0.0
        self.unproductiveSeconds = 0

    def setTimes(self, productiveSeconds: int, unproductiveSeconds: int) -> None:
        oldFraction = self.shownFraction
        self.productiveSeconds = productiveSeconds
        self.unproductiveSeconds = unproductiveSeconds
        totalSeconds = productiveSeconds + unproductiveSeconds
        newFraction = 0.0
        if totalSeconds > 0:
            newFraction = productiveSeconds / totalSeconds
        if abs(newFraction - oldFraction) > 0.01 and self.isVisible():
            animations.animateValue(oldFraction, newFraction, self.setFraction, 450)
        else:
            self.setFraction(newFraction)

    def setFraction(self, fraction) -> None:
        self.shownFraction = fraction
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        colors = getColors()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        barShape = QPainterPath()
        barShape.addRoundedRect(QRectF(self.rect()), 7, 7)
        painter.setClipPath(barShape)
        painter.fillRect(self.rect(), QColor(colors["surfaceContainerHighest"]))
        totalSeconds = self.productiveSeconds + self.unproductiveSeconds
        if totalSeconds == 0:
            return
        productiveWidth = int(self.width() * self.shownFraction)
        painter.fillRect(0, 0, productiveWidth, self.height(), QColor(colors["green"]))
        painter.fillRect(productiveWidth, 0, self.width() - productiveWidth, self.height(), QColor(colors["error"]))
        if 0 < productiveWidth < self.width():
            painter.fillRect(productiveWidth - 1, 0, 2, self.height(), QColor(colors["surfaceContainerLow"]))





# one row, dot + name + time

class TimeRow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        rowLayout = QHBoxLayout(self)
        rowLayout.setContentsMargins(0, 4, 0, 4)
        rowLayout.setSpacing(8)

        self.dotKind = "neutral"
        self.dot = QLabel(objectName=DOT_NAMES[self.dotKind])
        self.dot.setFixedSize(10, 10)
        self.nameLabel = QLabel(objectName="RowName")
        self.kindLabel = QLabel(objectName="RowKind")
        self.timeLabel = QLabel(objectName="RowTime", alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        for rowLabel in (self.nameLabel, self.kindLabel, self.timeLabel):
            rowLabel.setTextFormat(Qt.TextFormat.PlainText)

        rowLayout.addWidget(self.dot, alignment=Qt.AlignmentFlag.AlignVCenter)
        rowLayout.addWidget(self.nameLabel)
        rowLayout.addWidget(self.kindLabel)
        rowLayout.addStretch()
        rowLayout.addWidget(self.timeLabel)

    def setRow(self, name: str, kindText: str, dotKind: str, timeText: str) -> None:
        shownName = name
        if len(name) > MAX_NAME_LENGTH:
            shownName = name[:MAX_NAME_LENGTH - 3] + "..."
        self.nameLabel.setText(shownName)
        self.kindLabel.setText(kindText)
        self.timeLabel.setText(timeText)
        if dotKind != self.dotKind:
            self.dotKind = dotKind
            self.dot.setObjectName(DOT_NAMES[dotKind])
            self.dot.style().unpolish(self.dot)
            self.dot.style().polish(self.dot)


class TimeList(QWidget):
    def __init__(self, emptyText: str) -> None:
        super().__init__()
        self.listLayout = QVBoxLayout(self)
        self.listLayout.setContentsMargins(16, 4, 16, 8)
        self.listLayout.setSpacing(0)

        self.emptyLabel = QLabel(emptyText, objectName="EmptyText")
        self.emptyLabel.setTextFormat(Qt.TextFormat.PlainText)
        self.emptyLabel.setIndent(0)
        self.listLayout.addWidget(self.emptyLabel)
        self.timeRows = []

    def setRows(self, rows: list[tuple[str, str, str, str]]) -> None:
        self.emptyLabel.setVisible(len(rows) == 0)
        while len(self.timeRows) < len(rows):
            newRow = TimeRow()
            self.listLayout.addWidget(newRow)
            self.timeRows.append(newRow)

        for rowNumber in range(len(self.timeRows)):
            timeRow = self.timeRows[rowNumber]
            if rowNumber >= len(rows):
                if not timeRow.isHidden():
                    timeRow.hide()
                continue
            if timeRow.isHidden():
                timeRow.show()
            name, kindText, dotKind, timeText = rows[rowNumber]
            timeRow.setRow(name, kindText, dotKind, timeText)





# dropdowns w/ chevron, opens and closes whatevers under it

class DropdownHeader(QPushButton):
    def __init__(self) -> None:
        super().__init__(objectName="DropdownHeader", cursor=Qt.CursorShape.PointingHandCursor)
        self.isOpen = False
        self.angle = 0

    def setOpen(self, isOpen: bool) -> None:
        if isOpen != self.isOpen:
            self.isOpen = isOpen
            endAngle = 90 if isOpen else 0
            animations.animateValue(self.angle, endAngle, self.setAngle, 220)

    def setAngle(self, angle) -> None:
        self.angle = angle
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(24, self.height() / 2)
        painter.rotate(self.angle)
        chevronPen = QPen(QColor(getColors()["onPrimary"]), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(chevronPen)
        painter.drawLine(QPointF(-2, -4), QPointF(2, 0))
        painter.drawLine(QPointF(2, 0), QPointF(-2, 4))


class Dropdown(QWidget):
    def __init__(self, title: str, body=None) -> None:
        super().__init__()
        self.title = title
        dropdownLayout = QVBoxLayout(self)
        dropdownLayout.setContentsMargins(0, 0, 0, 0)
        dropdownLayout.setSpacing(4)

        self.header = DropdownHeader()
        self.header.clicked.connect(self.toggle)
        if body is None:
            body = QWidget()
        self.body = body
        self.body.hide()

        dropdownLayout.addWidget(self.header)
        dropdownLayout.addWidget(self.body)
        self.updateHeader()

    def toggle(self) -> None:
        if self.body.isHidden():
            animations.expand(self.body)
            if isinstance(self.body, TimeList):
                shownRows = [timeRow for timeRow in self.body.timeRows if not timeRow.isHidden()]
                animations.staggerIn(shownRows, 35, 260)
        else:
            animations.collapse(self.body)
        self.header.setOpen(self.body.isHidden())

    def updateHeader(self) -> None:
        self.header.setText(self.title)
        self.header.setOpen(not self.body.isHidden())






# Icons, drawn by hand so they follow the theme colours

def drawSun(painter: QPainter, color: QColor) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(0, 0), 4, 4)
    painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for rayNumber in range(8):
        painter.drawLine(QPointF(0, -6.5), QPointF(0, -8.5))
        painter.rotate(45)


def drawMoon(painter: QPainter, color: QColor) -> None:
    moonShape = QPainterPath()
    moonShape.addEllipse(QPointF(0, 0), 7, 7)
    moonBite = QPainterPath()
    moonBite.addEllipse(QPointF(3.5, -3), 6, 6)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(moonShape.subtracted(moonBite))


def drawCog(painter: QPainter, color: QColor) -> None:
    cogShape = QPainterPath()
    cogShape.addEllipse(QPointF(0, 0), 5.6, 5.6)
    for toothNumber in range(8):
        cogTooth = QPainterPath()
        cogTooth.addRoundedRect(QRectF(-1.7, -8.2, 3.4, 4), 0.8, 0.8)
        cogShape = cogShape.united(QTransform().rotate(45 * toothNumber).map(cogTooth))

    cogHole = QPainterPath()
    cogHole.addEllipse(QPointF(0, 0), 2.4, 2.4)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(cogShape.subtracted(cogHole))






# Top row buttons, settings cog + sun/moon theme toggle

class SettingsButton(QPushButton):
    def __init__(self) -> None:
        super().__init__(objectName="ThemeButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self.angle = 0
        self.clicked.connect(self.spin)

    def spin(self) -> None:
        animations.animateValue(0, 180, self.setAngle, 600)

    def setAngle(self, angle) -> None:
        self.angle = angle
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        drawCog(painter, QColor(getColors()["onSurface"]))


class ThemeToggle(QPushButton):
    def __init__(self, usingDarkTheme: bool) -> None:
        super().__init__(objectName="ThemeButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self.usingDarkTheme = usingDarkTheme

        self.spinProgress = 1.0
        self.spinAnimation = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=450)
        self.spinAnimation.setEasingCurve(QEasingCurve.Type.OutBack)
        self.spinAnimation.valueChanged.connect(self.setProgress)

    def setDark(self, usingDarkTheme: bool, animate: bool) -> None:
        self.usingDarkTheme = usingDarkTheme
        if animate:
            self.spinAnimation.start()
        else:
            self.setProgress(1.0)

    def setProgress(self, value: float) -> None:
        self.spinProgress = value
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        iconColor = QColor(getColors()["onSurface"])

        if self.spinProgress < 1:
            self.drawIcon(painter, not self.usingDarkTheme, iconColor, -120 * self.spinProgress, 1 - self.spinProgress)
        self.drawIcon(painter, self.usingDarkTheme, iconColor, 120 * (1 - self.spinProgress), self.spinProgress)

    def drawIcon(self, painter: QPainter, usingDarkTheme: bool, color: QColor, angle: float, amount: float) -> None:
        painter.save()
        iconOpacity = amount
        if iconOpacity > 1.0:
            iconOpacity = 1.0
        if iconOpacity < 0.0:
            iconOpacity = 0.0
        painter.setOpacity(iconOpacity)
        painter.rotate(angle)
        iconScale = 0.5 + 0.5 * amount
        painter.scale(iconScale, iconScale)

        if usingDarkTheme:
            drawSun(painter, color)
        else:
            drawMoon(painter, color)
        painter.restore()






# Main dashboard window

class Dashboard(QWidget):
    def __init__(self) -> None:
        super().__init__()

        # No close tabs
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)



        # Init window & styling & layout
        self.setWindowTitle("Arete")
        windowPropertiesSize = QApplication.primaryScreen().availableGeometry()
        self.resize(500, windowPropertiesSize.height() - 50) # padding boy

        # Set to right corner
        x = windowPropertiesSize.x() + (windowPropertiesSize.width() - 500) - 25
        y = windowPropertiesSize.y() + 25  # Top boundary of usable space
        self.move(x, y)

        self.setObjectName("Dashboard")
        self.themeChoice = memory.load()["themeChoice"]
        setTheme(resolveTheme(self.themeChoice, systemTheme()))
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.systemThemeChanged)
        self.statCards = []

        # Apple system font (SF Pro on mac), everything inside inherits it
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(STYLE)) # blurless now

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(10, 4, 10, 10)



        topRow = QHBoxLayout()
        topRow.setContentsMargins(20, 6, 20, 0)
        topRow.addWidget(AppNameLabel())
        topRow.addSpacing(12)
        self.sessionCard = SessionCard()
        topRow.addWidget(self.sessionCard, 1)
        topRow.addStretch()
        topRow.addSpacing(12)

        self.themeButton = ThemeToggle(getTheme() == "dark")
        self.themeButton.clicked.connect(self.toggleTheme)
        topRow.addWidget(self.themeButton)

        self.settingsButton = SettingsButton()
        self.settingsButton.clicked.connect(self.openSettings)
        topRow.addWidget(self.settingsButton)
        mainLayout.addLayout(topRow)



        # Everything scrolls since the config list + time list
        scrollArea = QScrollArea(widgetResizable=True)
        stopSideScrolling(scrollArea)

        scrollContent = QWidget(objectName="Content")
        scrollArea.setWidget(scrollContent)
        self.pages = QStackedWidget()
        self.pages.addWidget(scrollArea)
        mainLayout.addWidget(self.pages)
        self.settingsPage = None
        self.mountainPage = None

        layout = QVBoxLayout(scrollContent)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(12)



        heroCard = HeroCard()
        heroLayout = QVBoxLayout(heroCard)
        heroLayout.setContentsMargins(24, 20, 24, 22)
        heroLayout.setSpacing(6)
        heroLayout.addWidget(label("Hello!", "Hello"))
        self.currentMountain = label("", "CurrentMountain")
        heroLayout.addWidget(self.currentMountain)
        heroLayout.addWidget(label(memory.streakText(memory.markOpenedToday()), "Streak"))
        layout.addWidget(heroCard)
        self.showCurrentMountain()
        self.sessionPanel = SessionPanel(self.sessionChosen, self.endPressed)
        layout.addWidget(self.sessionPanel)
        self.bossCard = BossCard()
        layout.addWidget(self.bossCard)
        self.climbCard = ClimbCard(self.openMountain)
        self.climbCard.refresh()
        layout.addWidget(self.climbCard)
        self.entranceWidgets = [heroCard, self.climbCard]
        layout.addSpacing(8)



        layout.addWidget(label("Today’s Stats", "Section"))
        todayCard, todayLayout = self.sectionCard()
        todayLayout.addLayout(self.cardRow(["primary", "green", "tertiary"], [
            ("–", "% time focused", "No data yet", NO_DATA),
            ("–", "Hours spent productive", "No data yet", NO_DATA),
            ("–", "Average rebounding speed", "No data yet", NO_DATA),
        ]))
        self.todayCards = self.statCards[-3:]
        self.todayList = TimeList("Nothing tracked yet")
        todayLayout.addWidget(Dropdown("Show more stats", self.todayList))
        layout.addWidget(todayCard)
        layout.addSpacing(8)

        layout.addWidget(label("Weekly Stats", "Section"))
        weekCard, weekLayout = self.sectionCard()
        weekLayout.addLayout(self.cardRow(["blue", "orange", "secondary"], [
            ("–", "% time focused", "No data yet", NO_DATA),
            ("–", "Hours spent productive", "No data yet", NO_DATA),
            ("–", "Average rebounding speed", "No data yet", NO_DATA),
        ]))
        self.weekCards = self.statCards[-3:]
        self.weekList = TimeList("Nothing tracked yet")
        weekLayout.addWidget(Dropdown("Show more stats", self.weekList))
        layout.addWidget(weekCard)
        layout.addSpacing(8)



        layout.addWidget(label("Time Tracked", "Section"))
        self.backend = get_backend()
        self.trackedTimes: dict[tuple[str, str], int] = time_tracking.loadToday()
        self.trackedDay = time_tracking.todayName()
        self.enforcer = Enforcer(self.backend)

        self.pauseScreen = None
        self.pausedWindow = None
        self.pausedName = None
        self.pausedSite = None

        self.lastBrowserWindow = None
        self.lastReadSite = None
        self.siteReadAt = 0

        self.checkInScreen = None
        self.breakWindow = None
        self.breakName = None
        self.breakSite = None
        self.timesAsked = 0
        self.breakTimer = QTimer(self, singleShot=True, timeout=self.showCheckIn)
        self.breakBadge = BreakBadge(self.cancelBreak)

        self.currentWindow = None
        self.currentName = None
        self.currentSite = None
        self.currentKind = None

        self.lastApp = None
        self.emergencyApp = None
        self.passedAt = {}
        self.usedSeconds = {}
        self.unknownSeconds = {}
        self.askedSites = []

        timeCard = QFrame(objectName="TimeCard")
        timeCardLayout = QVBoxLayout(timeCard)
        timeCardLayout.setContentsMargins(20, 16, 20, 16)
        timeCardLayout.setSpacing(6)
        self.timeList = QLabel("Nothing tracked yet", alignment=Qt.AlignmentFlag.AlignTop)
        timeCardLayout.addWidget(self.timeList)
        self.splitTitle = label("Productive vs unproductive", "SplitTitle")
        self.splitBar = SplitBar()
        self.splitLegend = TimeList("")
        self.splitLegend.listLayout.setContentsMargins(0, 0, 0, 0)
        for splitPart in (self.splitTitle, self.splitBar, self.splitLegend):
            splitPart.hide()
            timeCardLayout.addWidget(splitPart)
        timeCardLayout.addSpacing(4)
        self.appsDropdown = Dropdown("Apps", TimeList(""))
        self.sitesDropdown = Dropdown("Websites", TimeList(""))
        for timeDropdown in (self.appsDropdown, self.sitesDropdown):
            timeDropdown.hide()
            timeCardLayout.addWidget(timeDropdown)
        layout.addWidget(timeCard)
        layout.addStretch()



        self.tickTimer = QTimer(self, interval=1000, timeout=self.tick)
        self.tickTimer.start()
        self.saveTimer = QTimer(self, interval=10000, timeout=self.saveTimes)
        self.saveTimer.start()
        QApplication.instance().aboutToQuit.connect(self.saveTimes)
        self.showTimes()
        self.refreshStats()

        self.lastKind = None

        self.sessionToast = None
        self.bossToast = None
        self.fightingBoss = climbing.climbState()["atBoss"]
        self.bossSeconds = 0
        self.sessionBossMinutes = 0
        self.bossCard.refresh()
        self.inSession = False
        self.scheduleStarted = None
        self.isAway = False
        self.sessionTimed = False
        self.sessionSeconds = 0
        self.productiveSeconds = 0
        QTimer.singleShot(0, self.checkLastSession)


    def sectionCard(self):
        sectionFrame = QFrame(objectName="TimeCard")
        sectionLayout = QVBoxLayout(sectionFrame)
        sectionLayout.setContentsMargins(14, 14, 14, 14)
        sectionLayout.setSpacing(10)
        return sectionFrame, sectionLayout

    def cardRow(self, colorFamilies, cards: list[tuple[str, str, str, str]]) -> QHBoxLayout:
        cardRowLayout = QHBoxLayout()
        cardRowLayout.setSpacing(8)

        cardIndex = 0
        for number, caption, status, statusColor in cards:
            statCard = StatCard(number, caption, status, statusColor, colorFamilies[cardIndex])
            statCard.iconName = STAT_ICONS[cardIndex]
            self.statCards.append(statCard)
            cardRowLayout.addWidget(statCard)
            cardIndex = cardIndex + 1
        return cardRowLayout






    # Tracking, runs every second

    def tick(self) -> None:
        for settingName in setting_changes.applyDueChanges():
            self.enforcer.sendNotification("Your " + settingName + " change is on now.")
        self.checkSchedule()
        self.checkIdle()
        self.sessionTick()
        window = self.backend.get_active_window()
        while len(vision.notices) > 0:
            self.enforcer.sendNotification(vision.notices.pop(0))

        if window is None or window.pid == os.getpid() or isIgnoredApp(window):
            return
        if self.pauseScreen is not None:
            return
        if self.checkInScreen is not None:
            return

        appKind = classifyTypeOfApp(self.backend, window)
        appName = window.app_name
        site = None
        if appKind == "browser":
            site = self.browserSite(window)
        if site is not None:
            appName = site
            if isUnproductiveSite(site):
                appKind = "unproductive"

        switchedApp = appName != self.lastApp
        justSorted = appKind == "unproductive" and self.lastKind != "unproductive"
        self.lastApp = appName
        self.lastKind = appKind
        if switchedApp:
            self.emergencyApp = None
        self.currentWindow = window
        self.currentName = appName
        self.currentSite = site
        self.currentKind = appKind

        onBreakRightNow = self.breakName is not None or not enforcement.blockingOn

        if appKind == "unproductive" and not onBreakRightNow:
            if enforcement.breaksLeftToday() == 0:
                self.enforcer.closeForToday(window, site)
                self.lastApp = None
                self.lastBrowserWindow = None
                return

        if appKind == "unproductive" and (switchedApp or justSorted) and not onBreakRightNow:
            secondsSincePassed = time.time() - self.passedAt.get(appName, 0)
            if secondsSincePassed > 600:
                self.showPause(window, appName, site)
                return
        if appName == self.emergencyApp:
            return

        timeKey = (appName, appKind)
        if appKind == "browser" and site is not None:
            self.checkUnknownSite(window, site)
        self.trackedTimes[timeKey] = self.trackedTimes.get(timeKey, 0) + 1
        self.usedSeconds[appName] = self.usedSeconds.get(appName, 0) + 1

        if not onBreakRightNow and self.enforcer.checkApp(window, appKind, self.usedSeconds[appName], site):
            self.usedSeconds[appName] = 0
            self.passedAt.pop(appName, None)
            self.lastApp = None
            self.lastBrowserWindow = None
        self.showTimes()

    def checkUnknownSite(self, window, site):
        if siteCategory(site) is not None or site in self.askedSites:
            return
        self.unknownSeconds[site] = self.unknownSeconds.get(site, 0) + 1
        if self.unknownSeconds[site] < 60:
            return

        self.askedSites.append(site)
        threading.Thread(target=vision.classifySite, args=(site,), daemon=True).start()

    def browserSite(self, window):
        browserWindow = (window.window_handle, window.title)
        retrySeconds = 10
        if self.lastReadSite is None:
            retrySeconds = 2
        needsRecheck = window.title == "" or self.lastReadSite is None
        if needsRecheck and time.time() - self.siteReadAt < retrySeconds:
            needsRecheck = False
        if browserWindow != self.lastBrowserWindow or needsRecheck:
            self.lastBrowserWindow = browserWindow
            self.lastReadSite = siteRoot(self.backend.get_browser_url(window))
            self.siteReadAt = time.time()
        return self.lastReadSite






    # Saving times every 10 sec + on quit

    def saveTimes(self) -> None:
        time_tracking.saveDay(self.trackedDay, self.trackedTimes)
        if self.inSession:
            session.saveProgress(self.sessionSeconds, self.productiveSeconds)
        if time_tracking.todayName() != self.trackedDay:
            self.trackedDay = time_tracking.todayName()
            self.trackedTimes = {}
            self.showTimes()
        self.refreshStats()

    def memoryCleared(self) -> None:
        self.trackedTimes = {}
        self.timeList.setText("Nothing tracked yet")
        self.timeList.show()
        for timePart in (self.splitTitle, self.splitBar, self.splitLegend, self.appsDropdown, self.sitesDropdown):
            timePart.hide()
        self.todayList.setRows([])
        self.refreshStats()
        self.climbCard.refresh()




    # Stats cards, refreshed every 10 seconds when times save + after every rebound

    def refreshStats(self) -> None:
        today = date.today()
        allRebounds = memory.savedRebounds()
        weekTimes = memory.weekTimes(self.trackedTimes, today)

        todayPercent = memory.percentFocused(self.trackedTimes)
        todayHours = memory.hoursProductive(self.trackedTimes)
        todayRebound = memory.averageRebound(allRebounds, [today.isoformat()])
        self.setCardRow(self.todayCards, todayPercent, todayHours, todayRebound, 3)

        weekPercent = memory.percentFocused(weekTimes)
        weekHours = memory.hoursProductive(weekTimes)
        weekRebound = memory.averageRebound(allRebounds, memory.lastSevenDays(today))
        self.setCardRow(self.weekCards, weekPercent, weekHours, weekRebound, 15)
        self.fillWeekList(today)

    # weekly list, time per day for last 7 days
    def fillWeekList(self, today) -> None:
        allDays = time_tracking.loadAllDays()
        weekRows = []
        hasTime = False
        for dayName in memory.lastSevenDays(today):
            if dayName == today.isoformat():
                dayTimes = self.trackedTimes
            else:
                dayTimes = time_tracking.dayTimes(allDays.get(dayName, {}))
            productiveSeconds = memory.focusedSeconds(dayTimes)
            unproductiveSeconds = memory.unproductiveSeconds(dayTimes)
            if productiveSeconds + unproductiveSeconds == 0:
                weekRows.append((dayText(dayName, today), "Nothing tracked", "neutral", ""))
                continue
            hasTime = True
            dotKind = "productive"
            if unproductiveSeconds > productiveSeconds:
                dotKind = "unproductive"
            weekRows.append((
                dayText(dayName, today),
                durationText(productiveSeconds) + " productive",
                dotKind,
                durationText(unproductiveSeconds) + " unproductive",
            ))
        if not hasTime:
            weekRows = []
        self.weekList.setRows(weekRows)

    def setCardRow(self, cards, percent, hours, averageBreaks, goodHours) -> None:
        focusedText, focusedColor = focusedStatus(percent)
        cards[0].setValues(numberText(percent), focusedText, focusedColor)
        hoursText, hoursColor = hoursStatus(hours, goodHours)
        cards[1].setValues(numberText(hours), hoursText, hoursColor)
        reboundText, reboundColor = reboundStatus(averageBreaks)
        cards[2].setValues(numberText(averageBreaks), reboundText, reboundColor)




    # Time tracked display, split bar + apps/sites dropdowns

    def showTimes(self) -> None:
        appRows = []
        siteRows = []
        productiveSeconds = 0
        unproductiveSeconds = 0
        for (name, rowKind), seconds in self.trackedTimes.items():
            if name.startswith("Browser "):
                continue
            if rowKind == "unproductive":
                unproductiveSeconds = unproductiveSeconds + seconds
            else:
                productiveSeconds = productiveSeconds + seconds
            if isSiteName(name):
                siteKind = "productive"
                if rowKind == "unproductive":
                    siteKind = "unproductive"
                siteRows.append((name, siteKind, rowKind, seconds))
            else:
                appRows.append((name, rowKind, rowKind, seconds))
        self.todayList.setRows(shownRows(appRows + siteRows, 5))
        if productiveSeconds + unproductiveSeconds == 0:
            return
        self.timeList.hide()
        self.splitBar.setTimes(productiveSeconds, unproductiveSeconds)
        totalSeconds = productiveSeconds + unproductiveSeconds
        productivePercent = round(100 * productiveSeconds / totalSeconds)
        self.splitLegend.setRows([
            ("Productive", str(productivePercent) + "%", "productive", durationText(productiveSeconds)),
            ("Unproductive", str(100 - productivePercent) + "%", "unproductive", durationText(unproductiveSeconds)),
        ])
        for splitPart in (self.splitTitle, self.splitBar, self.splitLegend):
            splitPart.show()
        self.fillTimeDropdown(self.appsDropdown, "Apps", appRows)
        self.fillTimeDropdown(self.sitesDropdown, "Websites", siteRows)

    def fillTimeDropdown(self, timeDropdown, title, rows):
        totalSeconds = 0
        for row in rows:
            totalSeconds = totalSeconds + row[3]
        timeDropdown.title = title + "   " + durationText(totalSeconds)
        timeDropdown.updateHeader()
        timeDropdown.setVisible(len(rows) > 0)
        timeDropdown.body.setRows(shownRows(rows, len(rows)))




    def playEntrance(self) -> None:
        self.climbCard.refresh()
        animations.staggerIn(self.entranceWidgets + self.statCards)
        for statCard in self.statCards:
            animations.countUp(statCard.numberLabel, statCard.numberTarget, 700)



    # Settings page

    def openSettings(self) -> None:
        self.settingsPage = SettingsPage(STYLE, self.closeSettings, self.memoryCleared, self.quitArete, self.climbChanged, self.beatBossNow)
        self.pages.addWidget(self.settingsPage)
        self.pages.setCurrentWidget(self.settingsPage)
        animations.fadeIn(self.settingsPage, 260)

    def closeSettings(self) -> None:
        self.pages.setCurrentIndex(0)
        animations.fadeIn(self.pages.widget(0), 260)
        self.pages.removeWidget(self.settingsPage)
        self.settingsPage.deleteLater()
        self.settingsPage = None



    # The climb, mountain page swaps in like settings does

    def openMountain(self) -> None:
        self.mountainPage = MapHome(self.closeMountain)
        self.pages.addWidget(self.mountainPage)
        self.fadeToPage(self.mountainPage)

    def closeMountain(self) -> None:
        self.fadeToPage(self.pages.widget(0))
        self.pages.removeWidget(self.mountainPage)
        self.mountainPage.deleteLater()
        self.mountainPage = None
        self.climbCard.refresh()

    def showCurrentMountain(self) -> None:
        mountainName = mountains.MOUNTAINS[climbing.climbState()["mountainNumber"]]["name"]
        self.currentMountain.setText("Currently climbing: <b>" + mountainName + "</b>")

    def fadeToPage(self, newPage) -> None:
        oldLook = QLabel(self.pages)
        oldLook.setPixmap(self.grab(QRect(self.pages.mapTo(self, QPoint(0, 0)), self.pages.size())))
        oldLook.setGeometry(0, 0, self.pages.width(), self.pages.height())
        oldLook.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        oldLook.show()
        oldLook.raise_()
        animations.fadeOutAndDelete(oldLook, 260)
        self.pages.setCurrentWidget(newPage)

    def climbChanged(self) -> None:
        self.climbCard.refresh()
        self.showCurrentMountain()
        self.bossCard.refresh()
        state = climbing.climbState()
        if state["atBoss"] and not self.fightingBoss and not state["finished"]:
            health = climbing.bossHealth(state["bossesBeaten"])
            self.showBossToast(state["bossesBeaten"], "appear", "It has " + str(health) + " focus minutes of health. Every minute you stay focused in a session hits it.")
        self.fightingBoss = state["atBoss"]
        if self.mountainPage is not None:
            self.mountainPage.refresh()



    # Focus sessions, started from the home panel, closing Arete mid session fails it

    def checkLastSession(self):
        if session.failLastSession():
            self.enforcer.sendNotification("Your last focus session ended when Arete closed, so it didn't count.")

    def sessionChosen(self, minutes):
        if self.inSession:
            return
        session.startSession(minutes)
        self.sessionSeconds = 0
        self.productiveSeconds = 0
        self.sessionBossMinutes = 0
        self.inSession = True
        self.sessionTimed = minutes is not None
        if self.sessionTimed:
            self.sessionCard.showSession(minutes * 60, session.sessionSecondsLeft())
            self.sessionPanel.updateTimed(minutes * 60, session.sessionSecondsLeft())
        else:
            self.sessionCard.showFree(0)
            self.sessionPanel.updateFree(0)
        self.sessionPanel.showRunning(self.sessionTimed)

    def checkSchedule(self):
        schedule = policy.activeSchedule()
        if schedule is None:
            self.scheduleStarted = None
            return
        if self.scheduleStarted == schedule or self.inSession:
            return
        self.scheduleStarted = schedule
        minutes = policy.minutesLeftInSchedule(schedule)
        self.sessionChosen(minutes)
        self.enforcer.sendNotification("Your study time just started, so Arete started a " + str(minutes) + " minute focus session. You got this!")

    def checkIdle(self):
        try:
            idleSeconds = self.backend.get_idle_seconds()
        except Exception:
            idleSeconds = 0
        if policy.isIdle(idleSeconds):
            self.isAway = True
            return
        if self.isAway:
            self.isAway = False
            if self.inSession:
                self.enforcer.sendNotification("Welcome back! Your session was paused while you were away.")

    def sessionTick(self):
        if not self.inSession or self.sessionToast is not None:
            return
        if self.isAway:
            return
        self.sessionSeconds = self.sessionSeconds + 1
        onBreak = self.breakName is not None or self.pauseScreen is not None
        if self.currentKind != "unproductive" and not onBreak:
            self.productiveSeconds = self.productiveSeconds + 1
            if self.fightingBoss:
                self.hitBoss()
        if not self.sessionTimed:
            self.sessionCard.updateFree(self.sessionSeconds)
            self.sessionPanel.updateFree(self.sessionSeconds)
            return
        secondsLeft = session.sessionSecondsLeft()
        if secondsLeft > 0:
            self.sessionCard.updateTime(secondsLeft)
            self.sessionPanel.updateTimed(self.sessionCard.totalSeconds, secondsLeft)
            return
        self.endSession()

    def endPressed(self):
        if self.sessionTimed:
            self.failSession()
        else:
            self.endSession()

    def stopSession(self):
        self.inSession = False
        self.sessionCard.hide()
        self.sessionPanel.showIdle()

    def failSession(self):
        session.failLastSession()
        self.stopSession()
        self.sessionToast = SessionDoneToast("Session failed", "You gave up before the timer ran out, so this one didn't count for the climb.", self.sessionToastDone, "Focus session")
        self.sessionToast.popUp()

    def endSession(self):
        minutes = self.sessionSeconds / 60
        if self.sessionTimed:
            minutes = self.sessionCard.totalSeconds / 60
        fraction = session.productiveFraction(self.sessionSeconds, self.productiveSeconds)
        earned = climbing.sessionEarned(minutes, fraction)
        session.endSession()
        self.stopSession()
        self.climbChanged()
        state = climbing.climbState()
        climbText = "+" + format(earned, ".2f").rstrip("0").rstrip(".") + "% on the climb"
        detailText = "You were focused " + str(int(round(fraction * 100))) + "% of the time. You're now " + climbSummary(state) + "."
        if minutes < climbing.SHORTEST_SESSION_MINUTES:
            detailText = "Sessions need to be at least " + str(climbing.SHORTEST_SESSION_MINUTES) + " minutes to count for the climb."
        if self.sessionBossMinutes > 0 and state["atBoss"]:
            climbText = "Hit the boss for " + str(self.sessionBossMinutes) + " min"
            detailText = "You were focused " + str(int(round(fraction * 100))) + "% of the time. " + bossName(state["bossesBeaten"]) + " has " + str(int(climbing.bossMinutesLeft() + 0.99)) + " focus minutes of health left."
        self.sessionToast = SessionDoneToast(climbText, detailText, self.sessionToastDone)
        self.sessionToast.popUp()
        if earned > 0:
            animations.confetti(self.sessionToast)

    def sessionToastDone(self, choice):
        self.sessionToast.deleteLater()
        self.sessionToast = None
        if choice == "continue":
            self.sessionChosen(session.CONTINUE_MINUTES)

    def hitBoss(self):
        self.bossSeconds = self.bossSeconds + 1
        if self.bossSeconds < 60:
            return
        self.bossSeconds = 0
        self.sessionBossMinutes = self.sessionBossMinutes + 1
        bossNumber = climbing.climbState()["bossesBeaten"]
        defeated = climbing.damageBoss(1)
        self.bossCard.hit()
        self.bossCard.refresh()
        if self.mountainPage is not None:
            self.mountainPage.refresh()
        if defeated:
            self.bossDefeated(bossNumber)

    def beatBossNow(self):
        state = climbing.climbState()
        if not state["atBoss"] or state["finished"]:
            return
        bossNumber = state["bossesBeaten"]
        climbing.damageBoss(climbing.bossHealth(bossNumber))
        self.bossDefeated(bossNumber)

    def bossDefeated(self, bossNumber):
        self.fightingBoss = False
        self.climbChanged()
        self.showBossToast(bossNumber, "defeat", "You wore it down with pure focus. The trail is open again, keep climbing!")

    def showBossToast(self, bossNumber, kind, detailText):
        if self.bossToast is not None:
            self.bossToast.deleteLater()
        self.bossToast = BossToast(bossNumber, kind, detailText, self.bossToastDone)
        self.bossToast.popUp()

    def bossToastDone(self):
        if self.bossToast is not None:
            self.bossToast.deleteLater()
        self.bossToast = None






    # Theme switching, light / dark / follow system

    def toggleTheme(self) -> None:
        newTheme = "dark"
        if getTheme() == "dark":
            newTheme = "light"
        self.themeChoice = choiceFor(newTheme, systemTheme())

        savedMemory = memory.load()
        savedMemory["themeChoice"] = self.themeChoice
        memory.save(savedMemory)
        self.switchTheme(newTheme)

    def systemThemeChanged(self, scheme=None) -> None:
        if self.themeChoice == "system":
            self.switchTheme(systemTheme())

    def switchTheme(self, themeName: str) -> None:
        if themeName == getTheme():
            return

        oldLook = None
        if self.isVisible():
            oldLook = self.grab()

        setTheme(themeName)
        self.setStyleSheet(applyTheme(STYLE))
        for statCard in self.statCards:
            statCard.restyle()
        self.themeButton.setDark(themeName == "dark", animate=oldLook is not None)
        if oldLook is not None:
            self.fadeOut(oldLook)

    def fadeOut(self, oldLook) -> None:
        oldLookCover = QLabel(self)
        oldLookCover.setPixmap(oldLook)
        oldLookCover.setGeometry(self.rect())
        oldLookCover.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        coverOpacity = QGraphicsOpacityEffect(oldLookCover)
        oldLookCover.setGraphicsEffect(coverOpacity)
        oldLookCover.show()
        self.themeButton.raise_()

        fadeAnimation = QPropertyAnimation(coverOpacity, b"opacity", oldLookCover)
        fadeAnimation.setDuration(350)
        fadeAnimation.setStartValue(1.0)
        fadeAnimation.setEndValue(0.0)
        fadeAnimation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fadeAnimation.finished.connect(oldLookCover.deleteLater)
        fadeAnimation.start()






    # Pause screen, pops up when you open something unproductive

    def showPause(self, window, appName, site):
        self.pausedWindow = window
        self.pausedName = appName
        self.pausedSite = site
        lostPercent = climbing.unproductivePenalty(appName)
        if lostPercent < 0:
            self.climbCard.refresh()
        if self.fightingBoss:
            self.bossCard.refresh()
        self.pauseScreen = PauseScreen(appName, self.backend.get_window_rect(window), self.pauseDone)
        self.pauseScreen.popUp()

    def pauseDone(self, choice):
        window = self.pausedWindow
        appName = self.pausedName
        self.pauseScreen = None

        if choice == "back":
            if self.pausedSite is None:
                self.backend.close_app(window.pid)
            else:
                self.backend.close_tab(window)
            self.lastApp = None
            self.lastBrowserWindow = None
            savedMemory = memory.load()
            savedMemory["backedOut"] = savedMemory.get("backedOut", 0) + 1
            memory.save(savedMemory)
        else:
            self.passedAt[appName] = time.time()
            self.usedSeconds[appName] = 0

        if choice == "emergency":
            self.emergencyApp = appName
        if choice == "open":
            self.breakWindow = window
            self.breakName = appName
            self.breakSite = self.pausedSite
            self.timesAsked = 0
            self.startBreakPeriod()






    # Quitting. kill keep alive helper first or it just reopens us

    def quitArete(self):
        keep_alive.stopHelper()
        if self.inSession:
            session.failLastSession()
        self.saveTimes()
        QApplication.quit()




    # Breaks, starting + checking in

    def startBreakPeriod(self):
        enforcement.useBreak()
        breakSeconds = enforcement.getBreakMinutes() * 60
        self.breakTimer.setInterval(breakSeconds * 1000)
        self.breakTimer.start()
        self.breakBadge.startBreak(breakSeconds)

    def showCheckIn(self):
        self.breakBadge.stopBreak()

        # Already went back to work on your own, still counts as a rebound
        if self.currentKind != "unproductive":
            self.recordRebound()
            self.endBreak()
            return

        self.breakWindow = self.currentWindow
        self.breakName = self.currentName
        self.breakSite = self.currentSite
        self.checkInScreen = CheckInScreen(self.breakName, self.timesAsked, enforcement.getBreakMinutes(), enforcement.breaksLeftToday(), self.checkInDone)
        self.checkInScreen.popUp()

    def endBreak(self):
        self.breakWindow = None
        self.breakName = None
        self.breakSite = None

        self.passedAt.clear()

    def checkInDone(self, choice):
        self.checkInScreen = None
        window = self.breakWindow
        if choice == "bounceBack":
            if self.breakSite is None:
                self.backend.close_app(window.pid)
            else:
                self.backend.close_tab(window)
            self.passedAt.pop(self.breakName, None)
            self.usedSeconds[self.breakName] = 0
            self.lastApp = None
            self.lastBrowserWindow = None
            self.endBreak()
            self.recordBounceBack()
        else:
            self.timesAsked = self.timesAsked + 1
            self.startBreakPeriod()






    # Breaks, ending early from the x on the badge

    def cancelBreak(self):
        self.breakTimer.stop()
        if self.currentKind == "unproductive":
            self.breakWindow = self.currentWindow
            self.breakName = self.currentName
            self.breakSite = self.currentSite
            self.checkInDone("bounceBack")
        else:
            self.endBreak()
            self.recordBounceBack()

    def recordBounceBack(self):
        self.recordRebound()
        climbing.bounceBackEarned(self.timesAsked + 1)
        self.climbChanged()
        savedMemory = memory.load()
        savedMemory["bounceBacks"] = savedMemory.get("bounceBacks", 0) + 1
        memory.save(savedMemory)




    # Stats, rebounding speed (how many break periods it took to get back to work)

    def recordRebound(self):
        savedMemory = memory.load()
        allRebounds = savedMemory.get("rebounds", [])
        allRebounds.append({"day": time_tracking.todayName(), "breakPeriods": self.timesAsked + 1})
        savedMemory["rebounds"] = allRebounds
        memory.save(savedMemory)
        self.refreshStats()




    # Drawing, sky picture first then the stylesheet paints the rounded border

    def paintEvent(self, event: QPaintEvent) -> None:
        styleOption = QStyleOption()
        styleOption.initFrom(self)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        panelShape = QPainterPath()
        panelShape.addRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 28, 28)
        painter.setClipPath(panelShape)
        painter.drawPixmap(0, 0, backdrop.backdropPicture(self.width(), self.height(), getTheme() == "dark", self.devicePixelRatioF()))
        painter.setClipping(False)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, styleOption, painter, self
        )


if __name__ == "__main__":
    app = QApplication([])
    window = Dashboard()
    window.show()
    app.exec()
