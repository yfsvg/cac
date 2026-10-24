"""using q widget to make the window. for mac this appears in the top corner"""
"""
Everything to be added to dashboard:
1. streak + welcome msg
2. Daily stats
3. Weekly stats
4. Settings and config (read figma doc for more)


BEFORE MAKING EDITS READ GDOC SECTION "Dashboard priorities"
"""
import os
import time

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, Qt, QTimer, QVariantAnimation
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor, QFontDatabase, QGuiApplication, QPainter, QPainterPath, QPaintEvent, QPen

from focusguard.core.classifier import classifyTypeOfApp, isIgnoredApp
from focusguard.core.enforcement import Enforcer
from focusguard.storage import memory
from focusguard.ui.pause_screen import PauseScreen
from focusguard.ui.theme import applyTheme, choiceFor, getColors, getTheme, resolveTheme, setTheme, systemTheme
from focusguard.platform import get_backend


# placeholder text for every dropdown until the real stuff exists
LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
)

# status chip text colours (theme tokens)
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

# dot colour per app kind in the time list
KIND_COLORS = {"browser": "blue", "unproductive": "error", "neutral": "secondary"}


def label(text: str, name: str, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft) -> QLabel:
    newLabel = QLabel(text, objectName=name, alignment=align)
    newLabel.setWordWrap(True)
    return newLabel


class StatCard(QFrame):
    def __init__(self, number: str, caption: str, status: str, statusColor: str, colorFamily: str) -> None:
        super().__init__(objectName="StatCard")
        # each card is a tonal container, text uses the matching "on" colour
        containerColor = "@" + colorFamily + "Container"
        onContainerColor = "@on" + colorFamily[0].upper() + colorFamily[1:] + "Container"
        self.cardStyle = f"QFrame#StatCard {{ background-color: {containerColor}; }} QLabel {{ color: {onContainerColor}; }}"
        self.setStyleSheet(applyTheme(self.cardStyle))
        self.setFixedHeight(150)
        # ignore caption width so all 3 cards split the row evenly
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        center = Qt.AlignmentFlag.AlignHCenter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(0)
        layout.addWidget(label(number, "BigNumber", center))
        layout.addWidget(label(caption, "Caption", center))
        layout.addStretch()
        self.statusChip = QLabel(status, objectName="Chip")
        self.chipStyle = f"color: {statusColor};"
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))
        layout.addWidget(self.statusChip, alignment=center)

    def restyle(self) -> None:
        self.setStyleSheet(applyTheme(self.cardStyle))
        self.statusChip.setStyleSheet(applyTheme(self.chipStyle))


class Dropdown(QWidget):
    """chevron header that opens/closes a paragraph underneath. no real content yet"""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.header = QPushButton(objectName="DropdownHeader", cursor=Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self.toggle)
        self.body = label(LOREM, "DropdownBody")
        self.body.hide()
        layout.addWidget(self.header)
        layout.addWidget(self.body)
        self.updateHeader()

    def toggle(self) -> None:
        self.body.setVisible(not self.body.isVisible())
        self.updateHeader()

    def updateHeader(self) -> None:
        chevron = "›"
        if self.body.isVisible():
            chevron = "⌄"
        self.header.setText(f" {chevron}   {self.title}")


def drawSun(painter: QPainter, color: QColor) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawEllipse(QPointF(0, 0), 4, 4)
    painter.setPen(QPen(color, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for ray in range(8):
        painter.drawLine(QPointF(0, -6.5), QPointF(0, -8.5))
        painter.rotate(45)


def drawMoon(painter: QPainter, color: QColor) -> None:
    moon = QPainterPath()
    moon.addEllipse(QPointF(0, 0), 7, 7)
    bite = QPainterPath()
    bite.addEllipse(QPointF(3.5, -3), 6, 6)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    painter.drawPath(moon.subtracted(bite))


class ThemeToggle(QPushButton):
    """sun/moon button in the top right. shows the theme you'd switch to (sun while dark), and spins
    the old icon out while the new one spins in"""

    def __init__(self, dark: bool) -> None:
        super().__init__(objectName="ThemeButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self.dark = dark
        self.progress = 1.0  # 0 right after a switch, 1 once settled
        self.spin = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=450)
        self.spin.setEasingCurve(QEasingCurve.Type.OutBack)  # overshoots a little so it lands with a bounce
        self.spin.valueChanged.connect(self.setProgress)

    def setDark(self, dark: bool, animate: bool) -> None:
        self.dark = dark
        if animate:
            self.spin.start()
        else:
            self.setProgress(1.0)

    def setProgress(self, value: float) -> None:
        self.progress = value
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)  # rounded background + hover from the stylesheet
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        color = QColor(getColors()["onSurface"])
        if self.progress < 1:
            self.drawIcon(painter, not self.dark, color, -120 * self.progress, 1 - self.progress)
        self.drawIcon(painter, self.dark, color, 120 * (1 - self.progress), self.progress)

    def drawIcon(self, painter: QPainter, dark: bool, color: QColor, angle: float, amount: float) -> None:
        painter.save()
        painter.setOpacity(max(0.0, min(1.0, amount)))
        painter.rotate(angle)
        size = 0.5 + 0.5 * amount
        painter.scale(size, size)
        if dark:
            drawSun(painter, color)
        else:
            drawMoon(painter, color)
        painter.restore()


class Dashboard(QWidget):
    def __init__(self) -> None:
        super().__init__()

        # no close tabs
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)




        # init window & styling & layout
        self.setWindowTitle("focus guard appie")
        windowPropertiesSize = QApplication.primaryScreen().availableGeometry()
        self.resize(500, windowPropertiesSize.height() - 50) # padding boy
        # set to right corner
        x = windowPropertiesSize.x() + (windowPropertiesSize.width() - 500) - 25
        y = windowPropertiesSize.y() + 25  # Top boundary of usable space
        self.move(x, y)

        self.setObjectName("Dashboard")
        # "system" follows the OS (and keeps following it live), "light"/"dark" is an override
        self.themeChoice = memory.load()["themeChoice"]
        setTheme(resolveTheme(self.themeChoice, systemTheme()))
        QGuiApplication.styleHints().colorSchemeChanged.connect(self.systemThemeChanged)
        self.statCards = []
        # apple system font (SF Pro on mac), everything inside inherits it
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(STYLE)) #blurless now

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(10, 10, 10, 10)

        # all material you as disucssed in gc
        # header sits outside the scroll area so the theme toggle stays pinned top right
        topRow = QHBoxLayout()
        topRow.setContentsMargins(20, 10, 20, 0)
        topRow.addWidget(label("Focusguard", "AppName"))
        topRow.addStretch()
        self.themeButton = ThemeToggle(getTheme() == "dark")
        self.themeButton.clicked.connect(self.toggleTheme)
        topRow.addWidget(self.themeButton)
        mainLayout.addLayout(topRow)






        # everything scrolls since the config list + time list
        scroll = QScrollArea(widgetResizable=True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget(objectName = "Content")
        scroll.setWidget(content)
        mainLayout.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(12)




        heroCard = QFrame(objectName="Hero")
        heroLayout = QVBoxLayout(heroCard)

        heroLayout.setContentsMargins(24, 20, 24, 22)
        heroLayout.setSpacing(6)
        heroLayout.addWidget(label("Hello, User", "Hello"))
        heroLayout.addWidget(label("Replace now with the tree system parth or japmann work?", "Streak"))
        layout.addWidget(heroCard)
        layout.addSpacing(8)



        # daily stats larp
        layout.addWidget(label("Today’s Stats", "Section"))
        layout.addLayout(self.cardRow(["primary", "green", "tertiary"], [
            ("97", "% time focused", "Looking good!", GOOD),
            ("2.3", "Hours spent productive", "Perfect!", PERFECT),
            ("0.3", "Hours spent unproductive", "Perfect!", PERFECT),
        ]))
        layout.addWidget(Dropdown("Show more stats"))
        layout.addSpacing(8)
        # weekly 
        layout.addWidget(label("Weekly Stats", "Section"))
        layout.addLayout(self.cardRow(["blue", "orange", "secondary"], [
            ("90", "% time focused", "Looking good!", GOOD),
            ("7", "Warnings", "Doing OK", OK),
            ("0", "Bail-outs used", "Perfect!", PERFECT),
        ]))
        layout.addWidget(Dropdown("Show more stats"))
        layout.addSpacing(8)




        # settings and config
        layout.addWidget(label("App Config", "Section"))
        
        for name in ["Absolute Time Limits", "Schedule Time Limits", "AI Categorizations",
                     "Super Focus Mode", "Bail-Outs", "Parental Controls"]:
            layout.addWidget(Dropdown(name))
        layout.addSpacing(8)




        # new display for time tracking, for every heartbeat/change update
        layout.addWidget(label("Time Tracked", "Section"))
        self.backend = get_backend()
        self.trackedTimes: dict[tuple[str, str], int] = {}
        self.enforcer = Enforcer(self.backend)
        self.pauseScreen = None
        self.pausedWindow = None
        self.lastApp = None
        self.emergencyApp = None
        self.passedAt = {}
        self.usedSeconds = {}
        timeCard = QFrame(objectName="TimeCard")
        timeCardLayout = QVBoxLayout(timeCard)
        timeCardLayout.setContentsMargins(20, 16, 20, 16)
        self.timeList = QLabel("Nothing tracked yet", alignment=Qt.AlignmentFlag.AlignTop)
        self.timeList.setTextFormat(Qt.TextFormat.RichText)
        timeCardLayout.addWidget(self.timeList)
        layout.addWidget(timeCard)
        layout.addStretch()
        self.timer = QTimer(self, interval=1000, timeout=self.tick)
        self.timer.start()


    
    def cardRow(self, colorFamilies, cards: list[tuple[str, str, str, str]]) -> QHBoxLayout:
        row = QHBoxLayout()

        row.setSpacing(8)
        cardIndex = 0
        for number, caption, status, statusColor in cards:
            card = StatCard(number, caption, status, statusColor, colorFamilies[cardIndex])
            self.statCards.append(card)
            row.addWidget(card)
            cardIndex = cardIndex + 1
        return row

    def tick(self) -> None:
        window = self.backend.get_active_window()
        # bail before the switch logic too, so clicking the taskbar and back isn't "switching apps"
        if window is None or window.pid == os.getpid() or isIgnoredApp(window):
            return
        if self.pauseScreen is not None:
            return
        appKind = classifyTypeOfApp(self.backend, window)

        switchedApp = window.app_name != self.lastApp
        self.lastApp = window.app_name
        if switchedApp:
            self.emergencyApp = None
        if appKind == "unproductive" and switchedApp:
            secondsSincePassed = time.time() - self.passedAt.get(window.app_name, 0)
            if secondsSincePassed > 600:
                self.showPause(window)
                return
        if window.app_name == self.emergencyApp:
            return

        key = (window.app_name, appKind)
        self.trackedTimes[key] = self.trackedTimes.get(key, 0) + 1
        self.usedSeconds[window.app_name] = self.usedSeconds.get(window.app_name, 0) + 1
        if self.enforcer.checkApp(window, appKind, self.usedSeconds[window.app_name]):
            self.usedSeconds[window.app_name] = 0
            self.passedAt.pop(window.app_name, None)
            self.lastApp = None
        self.showTimes()

    def showTimes(self) -> None:
        if not self.trackedTimes:
            return
        colors = getColors()
        rows = sorted(self.trackedTimes.items(), key=lambda kv: -kv[1])
        timeRows = []
        for (name, rowKind), seconds in rows:
            dotColor = colors[KIND_COLORS[rowKind]]
            timeRows.append(
                f"<tr><td width='18' style='color:{dotColor}; font-size:16px;'>●</td>"
                f"<td width='100%' style='padding-left:4px;'><b>{name}</b> <span style='color:{colors['onSurfaceVariant']};'>{rowKind}</span></td>"
                f"<td style='padding-left:16px;' align='right' nowrap>{seconds // 60}m {seconds % 60}s</td></tr>"
            )
        self.timeList.setText("<table width='100%' cellspacing='0' cellpadding='3'>" + "".join(timeRows) + "</table>")

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
        # picture of the old look, faded out on top of the new one. skipped while hidden
        oldLook = None
        if self.isVisible():
            oldLook = self.grab()
        setTheme(themeName)
        self.setStyleSheet(applyTheme(STYLE))
        for card in self.statCards:
            card.restyle()
        self.showTimes()
        self.themeButton.setDark(themeName == "dark", animate=oldLook is not None)
        if oldLook is not None:
            self.fadeOut(oldLook)

    def fadeOut(self, oldLook) -> None:
        cover = QLabel(self)
        cover.setPixmap(oldLook)
        cover.setGeometry(self.rect())
        cover.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        opacity = QGraphicsOpacityEffect(cover)
        cover.setGraphicsEffect(opacity)
        cover.show()
        self.themeButton.raise_()  # keep the spinning icon above the fade
        fade = QPropertyAnimation(opacity, b"opacity", cover)
        fade.setDuration(350)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade.finished.connect(cover.deleteLater)
        fade.start()

    def showPause(self, window):
        self.pausedWindow = window
        self.pauseScreen = PauseScreen(window.app_name, self.backend.get_window_rect(window), self.pauseDone)
        self.pauseScreen.popUp()

    def pauseDone(self, choice):
        window = self.pausedWindow
        self.pauseScreen = None
        if choice == "back":
            self.backend.close_app(window.pid)
            self.lastApp = None
            savedMemory = memory.load()
            savedMemory["backedOut"] = savedMemory.get("backedOut", 0) + 1
            memory.save(savedMemory)
        else:
            self.passedAt[window.app_name] = time.time()
            self.usedSeconds[window.app_name] = 0
        if choice == "emergency":
            self.emergencyApp = window.app_name



    def paintEvent(self, event: QPaintEvent) -> None:
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, opt, painter, self
        )


if __name__ == "__main__":
    app = QApplication([])
    window = Dashboard()
    window.show()
    app.exec()
