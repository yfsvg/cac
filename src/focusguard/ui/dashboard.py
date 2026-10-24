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
from focusguard.core import enforcement
from focusguard.core.enforcement import Enforcer
from focusguard.storage import memory, streak, time_tracking
from focusguard.ui.settings_window import SettingsPage
from focusguard.ui.pause_screen import BreakBadge, CheckInScreen, PauseScreen
from focusguard.ui.theme import applyTheme, choiceFor, getColors, getTheme, resolveTheme, setTheme, systemTheme
from focusguard.platform import get_backend


# Placeholder text for every dropdown until the real stuff exists

LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
)

# Status chip text colours (theme tokens)
GOOD = "@green"
PERFECT = "@green"
OK = "@orange"

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

    QLabel#DropdownBody { font-size: 13px; color: @onSurfaceVariant; padding: 4px 16px 8px 16px; }

    QFrame#Hero { background-color: @primaryContainer; border-radius: 28px; }
    QFrame#StatCard { border-radius: 24px; }

    QFrame#TimeCard { background-color: @surfaceContainerLow; border-radius: 24px; }

    QPushButton#DropdownHeader {
        color: @onSurface;
        font-size: 15px;
        text-align: left;
        background-color: @surfaceContainer;
        border: none;
        border-radius: 16px;
        padding: 12px 16px;
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

# Dot colour per app kind in the time list
KIND_COLORS = {"browser": "blue", "unproductive": "error", "neutral": "secondary"}




# Small widgets, labels + cards + dropdowns

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
        cardLayout.addWidget(label(number, "BigNumber", centerAlign))
        cardLayout.addWidget(label(caption, "Caption", centerAlign))
        cardLayout.addStretch()

        self.statusChip = QLabel(status, objectName="Chip")
        self.chipStyle = f"color: {statusColor};"
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))
        cardLayout.addWidget(self.statusChip, alignment=centerAlign)

    def restyle(self) -> None:
        self.setStyleSheet(applyTheme(self.cardStyle))
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))


# Chevron header that opens/closes a paragraph underneath. No real content yet

class Dropdown(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        dropdownLayout = QVBoxLayout(self)
        dropdownLayout.setContentsMargins(0, 0, 0, 0)
        dropdownLayout.setSpacing(4)

        self.header = QPushButton(objectName="DropdownHeader", cursor=Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self.toggle)
        self.body = label(LOREM, "DropdownBody")
        self.body.hide()

        dropdownLayout.addWidget(self.header)
        dropdownLayout.addWidget(self.body)
        self.updateHeader()

    def toggle(self) -> None:
        self.body.setVisible(not self.body.isVisible())
        self.updateHeader()

    def updateHeader(self) -> None:
        chevron = "›"
        if self.body.isVisible():
            chevron = "⌄"
        self.header.setText(f" {chevron}   {self.title}")




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

        # 0 -> 1 while the icon spins over to the new one
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

        # Old icon spins out while the new one spins in
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




        # Top row, all material you as disucssed in gc
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




        # Hero card, welcome msg + streak
        heroCard = QFrame(objectName="Hero")
        heroLayout = QVBoxLayout(heroCard)
        heroLayout.setContentsMargins(24, 20, 24, 22)
        heroLayout.setSpacing(6)
        heroLayout.addWidget(label("Hello, User", "Hello"))
        heroLayout.addWidget(label(streak.streakText(streak.markOpenedToday()), "Streak"))
        layout.addWidget(heroCard)
        layout.addSpacing(8)




        # Stats, daily (larp)
        layout.addWidget(label("Today’s Stats", "Section"))
        layout.addLayout(self.cardRow(["primary", "green", "tertiary"], [
            ("97", "% time focused", "Looking good!", GOOD),
            ("2.3", "Hours spent productive", "Perfect!", PERFECT),
            ("0.3", "Hours spent unproductive", "Perfect!", PERFECT),
        ]))
        layout.addWidget(Dropdown("Show more stats"))
        layout.addSpacing(8)

        # Stats, weekly
        layout.addWidget(label("Weekly Stats", "Section"))
        layout.addLayout(self.cardRow(["blue", "orange", "secondary"], [
            ("90", "% time focused", "Looking good!", GOOD),
            ("7", "Warnings", "Doing OK", OK),
            ("0", "Bail-outs used", "Perfect!", PERFECT),
        ]))
        layout.addWidget(Dropdown("Show more stats"))
        layout.addSpacing(8)




        # Time tracking display, updates every heartbeat/change
        layout.addWidget(label("Time Tracked", "Section"))
        self.backend = get_backend()
        self.trackedTimes: dict[tuple[str, str], int] = time_tracking.loadToday()
        self.trackedDay = time_tracking.todayName()
        self.enforcer = Enforcer(self.backend)

        # Pause screen
        self.pauseScreen = None
        self.pausedWindow = None
        self.pausedName = None
        self.pausedSite = None

        # Browser site reading, only re-read the url when the tab changes
        self.lastBrowserWindow = None
        self.lastReadSite = None
        self.siteReadAt = 0

        # Breaks + check ins
        self.checkInScreen = None
        self.breakWindow = None
        self.breakName = None
        self.breakSite = None
        self.timesAsked = 0
        self.breakTimer = QTimer(self, singleShot=True, timeout=self.showCheckIn)
        self.breakBadge = BreakBadge(self.cancelBreak)

        # Whatever app/site is in front right now
        self.currentWindow = None
        self.currentName = None
        self.currentSite = None
        self.currentKind = None

        # Per app memory for this session
        self.lastApp = None
        self.emergencyApp = None
        self.passedAt = {}
        self.usedSeconds = {}
        self.unknownSeconds = {}
        self.askedSites = []

        timeCard = QFrame(objectName="TimeCard")
        timeCardLayout = QVBoxLayout(timeCard)
        timeCardLayout.setContentsMargins(20, 16, 20, 16)
        self.timeList = QLabel("Nothing tracked yet", alignment=Qt.AlignmentFlag.AlignTop)
        self.timeList.setTextFormat(Qt.TextFormat.RichText)
        timeCardLayout.addWidget(self.timeList)
        layout.addWidget(timeCard)
        layout.addStretch()




        # Timers, check the front app every second and save times every 10
        self.tickTimer = QTimer(self, interval=1000, timeout=self.tick)
        self.tickTimer.start()
        self.saveTimer = QTimer(self, interval=10000, timeout=self.saveTimes)
        self.saveTimer.start()
        QApplication.instance().aboutToQuit.connect(self.saveTimes)
        self.showTimes()


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




    # Tracking, runs every second

    def tick(self) -> None:
        window = self.backend.get_active_window()
        while len(vision.notices) > 0:
            self.enforcer.sendNotification(vision.notices.pop(0))

        if window is None or window.pid == os.getpid() or isIgnoredApp(window):
            return
        if self.pauseScreen is not None:
            return
        if self.checkInScreen is not None:
            return

        # Figure out what's in front, browsers count as whatever site they're on
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
        self.lastApp = appName
        if switchedApp:
            self.emergencyApp = None
        self.currentWindow = window
        self.currentName = appName
        self.currentSite = site
        self.currentKind = appKind

        # During a break every unproductive app is allowed, so no pause screen or closing
        # Also NOTE get parth on it
        onBreakRightNow = self.breakName is not None

        # Out of breaks for today, unproductive stuff just closes
        if appKind == "unproductive" and not onBreakRightNow:
            if enforcement.breaksLeftToday() == 0:
                self.enforcer.closeForToday(window, site)
                self.lastApp = None
                self.lastBrowserWindow = None
                return

        # Just opened something unproductive, ask why first
        if appKind == "unproductive" and switchedApp and not onBreakRightNow:
            secondsSincePassed = time.time() - self.passedAt.get(appName, 0)
            if secondsSincePassed > 600:
                self.showPause(window, appName, site)
                return
        if appName == self.emergencyApp:
            return

        # Add a second to the time list
        timeKey = (appName, appKind)
        if site is not None and appKind == "unproductive":
            timeKey = ("Browser unproductive", "unproductive")
        elif appKind == "browser":
            timeKey = ("Browser productive", "browser")
            if site is not None:
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

        # If youve on an unknown site for a minute,  ask the AI about it in the background
        self.askedSites.append(site)
        threading.Thread(target=vision.classifySite, args=(self.backend, window, site), daemon=True).start()

    def browserSite(self, window):
        browserWindow = (window.window_handle, window.title)
        needsTitleRecheck = window.title == "" and time.time() - self.siteReadAt > 10
        if browserWindow != self.lastBrowserWindow or needsTitleRecheck:
            self.lastBrowserWindow = browserWindow
            self.lastReadSite = siteRoot(self.backend.get_browser_url(window))
            self.siteReadAt = time.time()
        return self.lastReadSite




    # Saving + showing tracked times

    def saveTimes(self) -> None:
        time_tracking.saveDay(self.trackedDay, self.trackedTimes)
        if time_tracking.todayName() != self.trackedDay:
            self.trackedDay = time_tracking.todayName()
            self.trackedTimes = {}
            self.showTimes()

    def memoryCleared(self) -> None:
        self.trackedTimes = {}
        self.timeList.setText("Nothing tracked yet")

    def showTimes(self) -> None:
        if not self.trackedTimes:
            return
        colors = getColors()
        sortedTimes = sorted(self.trackedTimes.items(), key=lambda timeEntry: -timeEntry[1])

        timeRows = []
        for (name, rowKind), seconds in sortedTimes:
            dotColor = colors[KIND_COLORS[rowKind]]
            timeRows.append(
                f"<tr><td width='18' style='color:{dotColor}; font-size:16px;'>●</td>"
                f"<td width='100%' style='padding-left:4px;'><b>{name}</b> <span style='color:{colors['onSurfaceVariant']};'>{rowKind}</span></td>"
                f"<td style='padding-left:16px;' align='right' nowrap>{seconds // 60}m {seconds % 60}s</td></tr>"
            )
        self.timeList.setText("<table width='100%' cellspacing='0' cellpadding='3'>" + "".join(timeRows) + "</table>")




    # Settings page

    def openSettings(self) -> None:
        self.settingsPage = SettingsPage(STYLE, self.closeSettings, self.memoryCleared)
        self.pages.addWidget(self.settingsPage)
        self.pages.setCurrentWidget(self.settingsPage)

    def closeSettings(self) -> None:
        self.pages.setCurrentIndex(0)
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

        # Screenshot the old look first so it can fade out on top of the new one
        oldLook = None
        if self.isVisible():
            oldLook = self.grab()

        setTheme(themeName)
        self.setStyleSheet(applyTheme(STYLE))
        for statCard in self.statCards:
            statCard.restyle()
        self.showTimes()
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




    # Breaks, starting + checking in

    def startBreakPeriod(self):
        enforcement.useBreak()
        breakSeconds = enforcement.getBreakMinutes() * 60
        self.breakTimer.setInterval(breakSeconds * 1000)
        self.breakTimer.start()
        self.breakBadge.startBreak(breakSeconds)

    def showCheckIn(self):
        self.breakBadge.stopBreak()
        if self.currentKind != "unproductive":
            self.endBreak()
            return

        # Check in about whatever unproductive app you're on now, not just the one the break started on
        self.breakWindow = self.currentWindow
        self.breakName = self.currentName
        self.breakSite = self.currentSite
        self.checkInScreen = CheckInScreen(self.breakName, self.timesAsked, enforcement.getBreakMinutes(), enforcement.breaksLeftToday(), self.checkInDone)
        self.checkInScreen.popUp()

    def endBreak(self):
        self.breakWindow = None
        self.breakName = None
        self.breakSite = None

        # Once a break is over, every unproductive app needs a new pause before it opens again
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
        # Ending a break early counts as bouncing back, same as "I'm ready" on the check in
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
        savedMemory = memory.load()
        savedMemory["bounceBacks"] = savedMemory.get("bounceBacks", 0) + 1
        memory.save(savedMemory)




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
