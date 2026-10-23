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

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
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
from PySide6.QtGui import QFontDatabase, QPainter, QPaintEvent

from focusguard.core.classifier import classifyTypeOfApp
from focusguard.core.enforcement import Enforcer
from focusguard.platform import get_backend


# placeholder text for every dropdown until the real stuff exists
LOREM = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor "
    "incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud "
    "exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
)

# status text colours from the design
GOOD = "#d4f53c"
PERFECT = "#3cff2e"
OK = "#f5e83c"

STYLE = """


    QWidget#Dashboard {
        background-color: rgba(0, 0, 0, 120);
        border-radius: 12px;
        border: solid rgba(255, 255, 255, 100);
        border-width: 0.5px;
    }

    QScrollArea, QWidget#Content { background: transparent; border: none; }
    QScrollBar:vertical { background: transparent; width: 6px; margin: 4px 0; }
    QScrollBar::handle:vertical { background: rgba(255, 255, 255, 60); border-radius: 3px; min-height: 30px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { height: 0; background: none; }

    QLabel { color: white; }
    QLabel#AppName { color: rgba(255, 255, 255, 150); font-size: 16px; }
    QLabel#Hello { font-size: 32px; font-weight: 700; }
    QLabel#Streak { font-size: 15px; }
    QLabel#Section { font-size: 24px; }
    QLabel#BigNumber { font-size: 56px; font-weight: 800; }
    QLabel#Caption { font-size: 13px; color: rgba(255, 255, 255, 220); }
    QLabel#Status { font-size: 13px; font-weight: 600; }
    QLabel#DropdownBody { font-size: 13px; color: rgba(255, 255, 255, 130); padding-left: 24px; }

    QFrame#Divider { background-color: rgba(255, 255, 255, 90); border: none; }
    QFrame#TodayCard, QFrame#WeekCard {
        border: 1px solid rgba(255, 255, 255, 60);
        border-radius: 8px;
    }
    QFrame#TodayCard { background-color: rgba(0, 0, 0, 70); }
    QFrame#WeekCard { background-color: rgba(0, 0, 0, 70); }

    QPushButton#DropdownHeader {

        color: rgba(255, 255, 255, 150);
        font-size: 17px;
        text-align: left;
        background: transparent;
        border: none;
        padding: 2px 0;
    }
    QPushButton#DropdownHeader:hover { color: rgba(255, 255, 255, 220); }


"""


def label(text: str, name: str, align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft) -> QLabel:
    lbl = QLabel(text, objectName=name, alignment=align)
    lbl.setWordWrap(True)
    return lbl


def divider() -> QFrame:
    # short line under each section like the figma
    line = QFrame(objectName="Divider")
    line.setFixedSize(190, 1)
    return line


class StatCard(QFrame):
    def __init__(self, number: str, caption: str, status: str, color: str, card_type: str) -> None:
        super().__init__(objectName=card_type)
        self.setFixedHeight(140)
        # ignore caption width so all 3 cards split the row evenly
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        center = Qt.AlignmentFlag.AlignHCenter
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 12)
        layout.setSpacing(0)
        layout.addWidget(label(number, "BigNumber", center))
        layout.addWidget(label(caption, "Caption", center))
        layout.addStretch()
        status_lbl = label(status, "Status", center)
        status_lbl.setStyleSheet(f"color: {color};")
        layout.addWidget(status_lbl)


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
        self.update_header()

    def toggle(self) -> None:
        self.body.setVisible(not self.body.isVisible())
        self.update_header()

    def update_header(self) -> None:
        chevron = "⌄" if self.body.isVisible() else "›"
        self.header.setText(f" {chevron}   {self.title}")


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
        # apple system font (SF Pro on mac), everything inside inherits it
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(STYLE)

        # blur the desktop behind the panel. mac only, if it breaks (or wintoes) just skip it
        try:
            get_backend().blur_behind(int(self.winId()), corner_radius=12)
        except Exception as e:
            print(f"background blur unavailable: {e}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)






        # everything scrolls since the config list + time list
        scroll = QScrollArea(widgetResizable=True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget(objectName = "Content")
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(12)




        # NOTE: all of the text and stuff is all just 
        # uploaded original figma design in discord gc
        layout.addWidget(label("Focusguard Application", "AppName"))

        layout.addWidget(divider())
        layout.addSpacing(6)

        layout.addWidget(label("Hello, User!", "Hello"))
        layout.addWidget(label(
            "You’re on a <b><u>4</u></b> day streak of using Focusguard to stay "
            "disciplined! Lets keep that going!", "Streak"))
        
        layout.addSpacing(6)

        layout.addWidget(divider())



        # daily stats larp
        layout.addWidget(label("Today’s Stats", "Section"))
        layout.addLayout(self.card_row("TodayCard", [
            ("97", "% time focused", "Looking good!", GOOD),
            ("2.3", "Hours spent productive", "Perfect!", PERFECT),
            ("0.3", "Hours spent unproductive", "Perfect!", PERFECT),
        ]))
        layout.addWidget(Dropdown("Show more stats"))
        layout.addSpacing(6)
        layout.addWidget(divider())
        # weekly 
        layout.addWidget(label("Weekly Stats", "Section"))
        layout.addLayout(self.card_row("WeekCard", [
            ("90", "% time focused", "Looking good!", GOOD),
            ("7", "Warnings", "Doing OK", OK),
            ("0", "Bail-outs used", "Perfect!", PERFECT),
        ]))
        layout.addWidget(Dropdown("Show more stats"))
        layout.addSpacing(6)
        layout.addWidget(divider())




        # settings and config
        layout.addWidget(label("App Config", "Section"))
        
        for name in ["Absolute Time Limits", "Schedule Time Limits", "AI Categorizations",
                     "Super Focus Mode", "Bail-Outs", "Parental Controls"]:
            layout.addWidget(Dropdown(name))
        layout.addSpacing(6)
        layout.addWidget(divider())




        # new display for time tracking, for every heartbeat/change update
        layout.addWidget(label("Time Tracked", "Section"))
        self.backend = get_backend()
        self.times: dict[tuple[str, str], int] = {}
        self.enforcer = Enforcer(self.backend)
        self.time_list = QLabel(styleSheet="color: white;", alignment=Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.time_list)
        layout.addStretch()
        self.timer = QTimer(self, interval=1000, timeout=self.tick)
        self.timer.start()


    
    def card_row(self, card_type, cards: list[tuple[str, str, str, str]]) -> QHBoxLayout:
        row = QHBoxLayout()

        row.setSpacing(8)
        for number, caption, status, color in cards:
            row.addWidget(StatCard(number, caption, status, color, card_type))
        return row

    def tick(self) -> None:
        window = self.backend.get_active_window()
        if window is None or window.pid == os.getpid():
            return
        kind = classifyTypeOfApp(self.backend, window)
        key = (window.app_name, kind)
        self.times[key] = self.times.get(key, 0) + 1
        self.enforcer.check(window, kind, self.times[key])
        rows = sorted(self.times.items(), key=lambda kv: -kv[1])
        self.time_list.setText("\n".join(f"{name} ({kind}): {s // 60}m {s % 60}s" for (name, kind), s in rows))



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
