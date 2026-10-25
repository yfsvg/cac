# Using QWidget to make the window. For mac this appears in the top corner
# Dashboard is split into four segments:
# 1. Streak + welcome msg
# 2. Daily stats
# 3. Weekly stats
# 4. Settings and config (read figma doc for more)
#
# BEFORE MAKING EDITS READ GDOC SECTION "Dashboard priorities"


import os
import threading
import time
from datetime import date, timedelta

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QPainter, QPainterPath, QPaintEvent, QPen, QTransform

from focusguard.ai import vision
from focusguard.ai.site_memory import siteCategory
from focusguard.core.classifier import classifyTypeOfApp, isIgnoredApp, isUnproductiveSite, siteRoot
from focusguard.core import enforcement, keep_alive, setting_changes
from focusguard.core.enforcement import Enforcer
from focusguard.storage import memory, time_tracking
from focusguard.ui import animations
from focusguard.ui.settings_window import SettingsPage
from focusguard.ui.pause_screen import BreakBadge, CheckInScreen, PauseScreen
from focusguard.ui.theme import applyTheme, choiceFor, getColors, getTheme, resolveTheme, setTheme, systemTheme
from focusguard.platform import get_backend


# Status chip text colours (theme tokens)
GOOD = "@green"
PERFECT = "@green"
OK = "@orange"
NO_DATA = "@onSurfaceVariant"

STYLE = """
    QWidget#Dashboard {
        background-color: @surface;
        border-radius: 28px;
        border: 1px solid @outlineVariant;
    }

    QScrollArea, QWidget#Content { background: transparent; border: none; }
    QScrollBar:vertical { background: transparent; width: 6px; margin: 4px 0; }
    QScrollBar::handle:vertical { background: @outlineVariant; border-radius: 3px; min-height: 30px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { height: 0; background: none; }

    QLabel { color: @onSurface; }
    QLabel#AppName { color: @primary; font-size: 14px; font-weight: 600; }
    QLabel#Hello { color: @onPrimaryContainer; font-size: 32px; font-weight: 700; }

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

    QFrame#Hero { background-color: @primaryContainer; border-radius: 28px; }
    QFrame#StatCard { border-radius: 24px; }

    QFrame#TimeCard { background-color: @surfaceContainerLow; border-radius: 24px; }
    QLabel#SplitTitle { color: @onSurface; font-size: 15px; font-weight: 600; }

    QLabel#RowName { color: @onSurface; font-size: 13px; font-weight: 600; }
    QLabel#RowKind { color: @onSurfaceVariant; font-size: 12px; }
    QLabel#RowTime { color: @onSurface; font-size: 13px; }
    QLabel#DotNeutral { background-color: @secondary; border-radius: 5px; }
    QLabel#DotBrowser { background-color: @blue; border-radius: 5px; }
    QLabel#DotUnproductive { background-color: @error; border-radius: 5px; }
    QLabel#DotProductive { background-color: @green; border-radius: 5px; }


    QPushButton#DropdownHeader {
        color: @onSurface;
        font-size: 15px;
        text-align: left;
        background-color: @surfaceContainer;
        border: none;
        border-radius: 16px;
        padding: 12px 16px 12px 40px;
    }
    QPushButton#DropdownHeader:hover { background-color: @surfaceContainerHigh; }

    QPushButton#ThemeButton {
        color: @onSurface;
        font-size: 16px;
        background-color: @surfaceContainerHigh;
        border: none;
        border-radius: 16px;
    }
    QPushButton#ThemeButton:hover { background-color: @surfaceContainerHighest; }
"""

DOT_NAMES = {
    "neutral": "DotNeutral",
    "browser": "DotBrowser",
    "unproductive": "DotUnproductive",
    "productive": "DotProductive",
}

MAX_NAME_LENGTH = 30


def label(text: str, name: str, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft) -> QLabel:
    newLabel = QLabel(text, objectName=name, alignment=align)
    newLabel.setWordWrap(True)
    return newLabel


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
        cardLayout.addWidget(self.numberLabel)
        cardLayout.addWidget(label(caption, "Caption", centerAlign))
        cardLayout.addStretch()

        self.statusChip = QLabel(status, objectName="Chip")
        self.chipStyle = f"color: {statusColor};"
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))
        cardLayout.addWidget(self.statusChip, alignment=centerAlign)

    def restyle(self) -> None:
        self.setStyleSheet(applyTheme(self.cardStyle))
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))

    def setValues(self, number: str, status: str, statusColor: str) -> None:
        if number != self.numberLabel.text() and self.isVisible():
            animations.countUp(self.numberLabel, number)
        else:
            self.numberLabel.setText(number)
        self.statusChip.setText(status)
        self.chipStyle = f"color: {statusColor};"
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))




# Stat card wording, always encouraging so it never feels like a punishment

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


class DropdownHeader(QPushButton):
    def __init__(self) -> None:
        super().__init__(objectName="DropdownHeader", cursor=Qt.CursorShape.PointingHandCursor)
        self.isOpen = False

    def setOpen(self, isOpen: bool) -> None:
        if isOpen != self.isOpen:
            self.isOpen = isOpen
            self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(24, self.height() / 2)
        if self.isOpen:
            painter.rotate(90)
        chevronPen = QPen(QColor(getColors()["onSurface"]), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
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
        else:
            animations.collapse(self.body)
        self.header.setOpen(self.body.isHidden())

    def updateHeader(self) -> None:
        self.header.setText(self.title)
        self.header.setOpen(not self.body.isHidden())



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



class SettingsButton(QPushButton):
    def __init__(self) -> None:
        super().__init__(objectName="ThemeButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
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



class Dashboard(QWidget):
    def __init__(self) -> None:
        super().__init__()

        # No close tabs
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)



        # Init window & styling & layout
        self.setWindowTitle("focus guard appie")
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
        mainLayout.setContentsMargins(10, 10, 10, 10)



        topRow = QHBoxLayout()
        topRow.setContentsMargins(20, 10, 20, 0)
        topRow.addWidget(label("Focusguard", "AppName"))
        topRow.addStretch()

        self.themeButton = ThemeToggle(getTheme() == "dark")
        self.themeButton.clicked.connect(self.toggleTheme)
        topRow.addWidget(self.themeButton)

        self.settingsButton = SettingsButton()
        self.settingsButton.clicked.connect(self.openSettings)
        topRow.addWidget(self.settingsButton)
        mainLayout.addLayout(topRow)



        # Everything scrolls since the config list + time list
        scrollArea = QScrollArea(widgetResizable=True)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scrollContent = QWidget(objectName="Content")
        scrollArea.setWidget(scrollContent)
        self.pages = QStackedWidget()
        self.pages.addWidget(scrollArea)
        mainLayout.addWidget(self.pages)
        self.settingsPage = None

        layout = QVBoxLayout(scrollContent)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(12)



        heroCard = QFrame(objectName="Hero")
        heroLayout = QVBoxLayout(heroCard)
        heroLayout.setContentsMargins(24, 20, 24, 22)
        heroLayout.setSpacing(6)
        heroLayout.addWidget(label("Hello, User", "Hello"))
        heroLayout.addWidget(label(memory.streakText(memory.markOpenedToday()), "Streak"))
        layout.addWidget(heroCard)
        self.entranceWidgets = [heroCard]
        layout.addSpacing(8)



        layout.addWidget(label("Today’s Stats", "Section"))
        layout.addLayout(self.cardRow(["primary", "green", "tertiary"], [
            ("–", "% time focused", "No data yet", NO_DATA),
            ("–", "Hours spent productive", "No data yet", NO_DATA),
            ("–", "Average rebounding speed", "No data yet", NO_DATA),
        ]))
        self.todayCards = self.statCards[-3:]
        self.todayList = TimeList("Nothing tracked yet")
        layout.addWidget(Dropdown("Show more stats", self.todayList))
        layout.addSpacing(8)

        layout.addWidget(label("Weekly Stats", "Section"))
        layout.addLayout(self.cardRow(["blue", "orange", "secondary"], [
            ("–", "% time focused", "No data yet", NO_DATA),
            ("–", "Hours spent productive", "No data yet", NO_DATA),
            ("–", "Average rebounding speed", "No data yet", NO_DATA),
        ]))
        self.weekCards = self.statCards[-3:]
        self.weekList = TimeList("Nothing tracked yet")
        layout.addWidget(Dropdown("Show more stats", self.weekList))
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


    def cardRow(self, colorFamilies, cards: list[tuple[str, str, str, str]]) -> QHBoxLayout:
        cardRowLayout = QHBoxLayout()
        cardRowLayout.setSpacing(8)

        cardIndex = 0
        for number, caption, status, statusColor in cards:
            statCard = StatCard(number, caption, status, statusColor, colorFamilies[cardIndex])
            self.statCards.append(statCard)
            cardRowLayout.addWidget(statCard)
            cardIndex = cardIndex + 1
        return cardRowLayout



    def tick(self) -> None:
        for settingName in setting_changes.applyDueChanges():
            self.enforcer.sendNotification("Your " + settingName + " change is on now.")
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

        onBreakRightNow = self.breakName is not None

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
        threading.Thread(target=vision.classifySite, args=(self.backend, window, site), daemon=True).start()

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



    def saveTimes(self) -> None:
        time_tracking.saveDay(self.trackedDay, self.trackedTimes)
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
        animations.staggerIn(self.entranceWidgets + self.statCards)
        for statCard in self.statCards:
            animations.countUp(statCard.numberLabel, statCard.numberLabel.text(), 700)

    def openSettings(self) -> None:
        self.settingsPage = SettingsPage(STYLE, self.closeSettings, self.memoryCleared, self.quitFocusGuard)
        self.pages.addWidget(self.settingsPage)
        self.pages.setCurrentWidget(self.settingsPage)
        animations.fadeIn(self.settingsPage, 260)

    def closeSettings(self) -> None:
        self.pages.setCurrentIndex(0)
        animations.fadeIn(self.pages.widget(0), 260)
        self.pages.removeWidget(self.settingsPage)
        self.settingsPage.deleteLater()
        self.settingsPage = None



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



    def showPause(self, window, appName, site):
        self.pausedWindow = window
        self.pausedName = appName
        self.pausedSite = site
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



    def quitFocusGuard(self):
        keep_alive.stopHelper()
        self.saveTimes()
        QApplication.quit()

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




    # Drawing, lets the stylesheet paint the rounded background

    def paintEvent(self, event: QPaintEvent) -> None:
        styleOption = QStyleOption()
        styleOption.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, styleOption, painter, self
        )


if __name__ == "__main__":
    app = QApplication([])
    window = Dashboard()
    window.show()
    app.exec()
