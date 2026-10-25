# Using QWidget to make the window. For mac this appears in the top corner
# Dashboard is split into four segments:
# 1. Everest climb + welcome msg
# 2. Daily stats
# 3. Weekly stats
# 4. Settings and config (read figma doc for more)
#
# BEFORE MAKING EDITS READ GDOC SECTION "Dashboard priorities"


import os
import threading
import time
from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPointF, QPropertyAnimation, QRectF, Qt, QTimer, QVariantAnimation
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
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QPainter, QPainterPath, QPaintEvent, QPen, QPixmap, QTransform

from focusguard.ai import vision
from focusguard.ai.site_memory import siteCategory
from focusguard.core.classifier import classifyTypeOfApp, isIgnoredApp, isUnproductiveSite, siteRoot
from focusguard.core import enforcement, keep_alive, setting_changes
from focusguard.core.enforcement import Enforcer
from focusguard.storage import memory, time_tracking
from focusguard.ui import animations
from focusguard.ui.settings_window import SettingsPage
from focusguard.ui.pause_screen import BreakBadge, CheckInScreen, PauseScreen
from focusguard.ui.theme import applyTheme, setClimbAccent, choiceFor, getColors, getTheme, resolveTheme, setTheme, systemTheme
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
    QLabel#AppName { color: @primary; font-size: 14px; font-weight: 700; padding: 5px 12px; }
    QLabel#Hello { color: @onSurface; font-size: 32px; font-weight: 700; }
    QLabel#ClimbMessage { color: @onSurface; font-size: 14px; }
    QLabel#ClimbMeters { color: @primary; font-size: 13px; font-weight: 700; }

    QLabel#Section { color: @onSurface; font-size: 20px; font-weight: 700; padding: 4px 14px; }
    QLabel#BigNumber { color: @primary; font-size: 44px; font-weight: 800; }
    QLabel#Caption { font-size: 12px; }

    QLabel#Chip {
        font-size: 12px;
        font-weight: 600;
        background-color: @chipBackground;
        border-radius: 10px;
        padding: 3px 10px;
    }

    QLabel#EmptyText { font-size: 13px; color: @onSurfaceVariant; padding: 4px 0 4px 0; }

    QFrame#Hero, QFrame#StatCard, QFrame#TimeCard { background: transparent; border: none; }
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
        background: transparent;
        border: none;
        border-radius: 16px;
        padding: 12px 16px 12px 40px;
    }
    QPushButton#DropdownHeader:hover { background-color: @frostHover; }

    QPushButton#ThemeButton {
        color: @onSurface;
        font-size: 16px;
        background-color: @frostTint;
        border: 1px solid @frostBorder;
        border-radius: 16px;
    }
    QPushButton#ThemeButton:hover { background-color: @frostBorder; }
"""

DOT_NAMES = {
    "neutral": "DotNeutral",
    "browser": "DotBrowser",
    "unproductive": "DotUnproductive",
    "productive": "DotProductive",
}

MAX_NAME_LENGTH = 30

# everest mountain behind the whole dashboard
CLIMB_BACKGROUND = Path(__file__).parent / "assets" / "everest_climb.svg"


# Frosted glass, paints the blurred mountain behind a box + a white tint on top
# so text stays readable over trees / clouds / snow

def paintFrosted(widget, painter, radius) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    boxPath = QPainterPath()
    boxPath.addRoundedRect(QRectF(widget.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)

    # blurred slice of the mountain thats right behind this box
    dashboard = widget.window()
    if hasattr(dashboard, "blurredPixmap"):
        painter.setClipPath(boxPath)
        boxOffset = widget.mapTo(dashboard, QPoint(0, 0))
        painter.drawPixmap(-boxOffset.x(), -boxOffset.y(), dashboard.blurredPixmap())
        painter.setClipping(False)

    # tint + border on top so text stays readable
    colors = getColors()
    painter.fillPath(boxPath, QColor(colors["frostTint"]))
    painter.setPen(QPen(QColor(colors["frostBorder"]), 1))
    painter.drawPath(boxPath)
    painter.restore()


# glass box, kids draw on top like normal
class FrostedFrame(QFrame):
    def __init__(self, objectName: str = "", radius: int = 24) -> None:
        super().__init__(objectName=objectName)
        self.radius = radius

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        paintFrosted(self, painter, self.radius)
        painter.end()
        super().paintEvent(event)


class FrostedLabel(QLabel):
    # little glass pill behind a label, for the section titles + app name
    def __init__(self, text: str, objectName: str, radius: int = 14) -> None:
        super().__init__(text, objectName=objectName)
        self.radius = radius

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        paintFrosted(self, painter, self.radius)
        painter.end()
        super().paintEvent(event)


def sectionLabel(text: str) -> QLabel:
    return FrostedLabel(text, "Section")




# small widgets, labels + stat cards

def label(text: str, name: str, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft) -> QLabel:
    newLabel = QLabel(text, objectName=name, alignment=align)
    newLabel.setWordWrap(True)
    return newLabel


class AppNameLabel(FrostedLabel):
    def __init__(self) -> None:
        super().__init__("Focusguard", "AppName")
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


class StatCard(FrostedFrame):
    def __init__(self, number: str, caption: str, status: str, statusColor: str) -> None:
        super().__init__("StatCard", 24)
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

        self.statusChip = QLabel(status, objectName="Chip")
        self.chipStyle = f"color: {statusColor};"
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))
        cardLayout.addWidget(self.statusChip, alignment=centerAlign)

    def restyle(self) -> None:
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))

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

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        paintFrosted(self, painter, 16)
        painter.end()

    def toggle(self) -> None:
        if self.body.isHidden():
            animations.expand(self.body)
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
        topRow.addWidget(AppNameLabel())
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
        # glass boxes show the mountain behind them, so they have to repaint when u scroll
        scrollArea.verticalScrollBar().valueChanged.connect(scrollContent.update)
        self.pages = QStackedWidget()
        self.pages.addWidget(scrollArea)
        mainLayout.addWidget(self.pages)
        self.settingsPage = None

        layout = QVBoxLayout(scrollContent)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(12)



        # Everest background, refreshClimb decides where it scrolls to
        self.climbBackground = QSvgRenderer(str(CLIMB_BACKGROUND))
        self.backgroundOffset = memory.CLIMB_STAGES[0]["offset"]
        self.backgroundCache = None
        self.backgroundCacheKey = None
        self.blurCache = None
        self.blurCacheKey = None
        self.accentStage = None
        self.cleanSeconds = 0

        heroCard = FrostedFrame("Hero", 28)
        heroLayout = QVBoxLayout(heroCard)
        heroLayout.setContentsMargins(24, 20, 24, 22)
        heroLayout.setSpacing(6)
        heroLayout.addWidget(label("Hello, User", "Hello"))
        self.climbMessage = label("", "ClimbMessage")
        heroLayout.addWidget(self.climbMessage)
        self.climbMetersText = label("", "ClimbMeters")
        heroLayout.addWidget(self.climbMetersText)
        layout.addWidget(heroCard)
        self.refreshClimb()
        self.entranceWidgets = [heroCard]
        layout.addSpacing(8)



        layout.addWidget(sectionLabel("Today’s Stats"), alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(self.cardRow([
            ("–", "% time focused", "No data yet", NO_DATA),
            ("–", "Hours spent productive", "No data yet", NO_DATA),
            ("–", "Average rebounding speed", "No data yet", NO_DATA),
        ]))
        self.todayCards = self.statCards[-3:]
        self.todayList = TimeList("Nothing tracked yet")
        layout.addWidget(Dropdown("Show more stats", self.todayList))
        layout.addSpacing(8)

        layout.addWidget(sectionLabel("Weekly Stats"), alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(self.cardRow([
            ("–", "% time focused", "No data yet", NO_DATA),
            ("–", "Hours spent productive", "No data yet", NO_DATA),
            ("–", "Average rebounding speed", "No data yet", NO_DATA),
        ]))
        self.weekCards = self.statCards[-3:]
        self.weekList = TimeList("Nothing tracked yet")
        layout.addWidget(Dropdown("Show more stats", self.weekList))
        layout.addSpacing(8)



        layout.addWidget(sectionLabel("Time Tracked"), alignment=Qt.AlignmentFlag.AlignLeft)
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

        timeCard = FrostedFrame("TimeCard", 24)
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


    def cardRow(self, cards: list[tuple[str, str, str, str]]) -> QHBoxLayout:
        cardRowLayout = QHBoxLayout()
        cardRowLayout.setSpacing(8)

        for number, caption, status, statusColor in cards:
            statCard = StatCard(number, caption, status, statusColor)
            self.statCards.append(statCard)
            cardRowLayout.addWidget(statCard)
        return cardRowLayout






    # Tracking, runs every second

    def tick(self) -> None:
        for settingName in setting_changes.applyDueChanges():
            self.enforcer.sendNotification("Your " + settingName + " change is on now.")

        # climbing, +50m for every hour focusguard is open without u using anything unproductive
        self.cleanSeconds = self.cleanSeconds + 1
        if self.cleanSeconds >= 3600:
            self.cleanSeconds = 0
            memory.addFocusHourMeters()
            self.refreshClimb()
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

        # using anything unproductive (breaks too) restarts the clean hour
        if appKind == "unproductive":
            self.cleanSeconds = 0

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






    # Saving times every 10 sec + on quit

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
        self.refreshClimb()
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
        animations.staggerIn(self.entranceWidgets + self.statCards)
        for statCard in self.statCards:
            animations.countUp(statCard.numberLabel, statCard.numberTarget, 700)



    # Settings page

    def openSettings(self) -> None:
        self.settingsPage = SettingsPage(STYLE, self.closeSettings, self.memoryCleared, self.quitFocusGuard, self.refreshClimb)
        self.pages.addWidget(self.settingsPage)
        self.pages.setCurrentWidget(self.settingsPage)
        animations.fadeIn(self.settingsPage, 260)

    def closeSettings(self) -> None:
        self.pages.setCurrentIndex(0)
        animations.fadeIn(self.pages.widget(0), 260)
        self.pages.removeWidget(self.settingsPage)
        self.settingsPage.deleteLater()
        self.settingsPage = None






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
        self.restyle()
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

    def quitFocusGuard(self):
        keep_alive.stopHelper()
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
        memory.addBounceBackMeters(self.timesAsked + 1)
        self.refreshStats()




    # Everest climb, hero card text + where the background sits

    def refreshClimb(self) -> None:
        meters = memory.climbMeters()
        stage = memory.climbStage(meters)
        goalName, metersLeft = memory.nextClimbGoal(meters)

        # hero text, stage message + meters line
        self.climbMessage.setText(stage["message"])

        metersText = stage["name"] + "  ·  " + format(meters, ",") + " m climbed"
        if metersLeft > 0:
            metersText = metersText + "  ·  " + format(metersLeft, ",") + " m to " + goalName
        else:
            metersText = metersText + "  ·  you're at the top!"
        self.climbMetersText.setText(metersText)

        # new stage = jump the mountain to its spot
        if stage["offset"] != self.backgroundOffset:
            self.backgroundOffset = stage["offset"]
            self.update()

        # green at the bottom -> purple at the peak, only restyle when the stage actually changes
        stageNumber = memory.CLIMB_STAGES.index(stage)
        if stageNumber != self.accentStage:
            self.accentStage = stageNumber
            setClimbAccent(stageNumber / (len(memory.CLIMB_STAGES) - 1))
            self.restyle()

    def restyle(self) -> None:
        # reapply colours after the theme or climb colour changes
        self.setStyleSheet(applyTheme(STYLE))
        for statCard in self.statCards:
            statCard.restyle()
        self.update()

    def backgroundPixmap(self) -> QPixmap:
        # only re-render the svg when the size or stage changes, way too slow to do every paint
        pixelRatio = self.devicePixelRatioF()
        cacheKey = (self.width(), self.height(), self.backgroundOffset, pixelRatio)
        if cacheKey == self.backgroundCacheKey:
            return self.backgroundCache

        # svg is scaled to the app width, then scrolled so the stages point is in the middle
        svgSize = self.climbBackground.defaultSize()
        backgroundScale = self.width() / svgSize.width()
        backgroundHeight = svgSize.height() * backgroundScale
        scrollY = self.backgroundOffset * backgroundScale - self.height() / 2
        if scrollY > backgroundHeight - self.height():
            scrollY = backgroundHeight - self.height()
        if scrollY < 0:
            scrollY = 0

        backgroundImage = QPixmap(int(self.width() * pixelRatio), int(self.height() * pixelRatio))
        backgroundImage.setDevicePixelRatio(pixelRatio)
        backgroundImage.fill(Qt.GlobalColor.transparent)
        imagePainter = QPainter(backgroundImage)
        imagePainter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.climbBackground.render(imagePainter, QRectF(0, -scrollY, self.width(), backgroundHeight))
        imagePainter.end()

        self.backgroundCache = backgroundImage
        self.backgroundCacheKey = cacheKey
        return backgroundImage

    def blurredPixmap(self) -> QPixmap:
        # blur = shrink the background way down then stretch it back up, cheap + looks like frosted glass
        backgroundImage = self.backgroundPixmap()
        if self.blurCacheKey == self.backgroundCacheKey:
            return self.blurCache

        fullImage = backgroundImage.toImage()
        # 2 small shrinks look smoother than 1 big one
        smallImage = fullImage.scaled(fullImage.width() // 4, fullImage.height() // 4, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        tinyImage = smallImage.scaled(smallImage.width() // 6, smallImage.height() // 6, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        smallImage = tinyImage.scaled(smallImage.width(), smallImage.height(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        fullImage = smallImage.scaled(fullImage.width(), fullImage.height(), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)


        blurredImage = QPixmap.fromImage(fullImage)
        blurredImage.setDevicePixelRatio(backgroundImage.devicePixelRatio())
        self.blurCache = blurredImage
        self.blurCacheKey = self.backgroundCacheKey
        return blurredImage




    # Drawing, lets the stylesheet paint the rounded background

    def paintEvent(self, event: QPaintEvent) -> None:
        styleOption = QStyleOption()
        styleOption.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, styleOption, painter, self
        )

        # everest background on top, clipped just inside the rounded border so the border still shows
        if self.climbBackground.isValid():
            clipPath = QPainterPath()
            clipPath.addRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 27, 27)
            painter.setClipPath(clipPath)
            painter.drawPixmap(0, 0, self.backgroundPixmap())


if __name__ == "__main__":
    app = QApplication([])
    window = Dashboard()
    window.show()
    app.exec()
