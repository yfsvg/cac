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
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QCloseEvent, QPainter, QPaintEvent

from focusguard.platform import get_backend
from focusguard.ui.parental_functions import close_with_pin


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
        self.setStyleSheet(
            """
            QWidget#Dashboard {
                background-color: rgba(0, 0, 0, 70); 
                border-radius: 12px;
                border: solid rgba(255, 255, 255, 100);
                border-width: 0.5px;
            }
        """

        )
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # top bar: minimise + exit. neither quits the app, the daemon keeps running in the background
        title_bar = QHBoxLayout()
        # current app, refreshed every 2s
        self.current_app_label = QLabel("Current app: —")
        title_bar.addWidget(self.current_app_label)
        title_bar.addStretch()
        minimise_btn = QPushButton("–")
        minimise_btn.setToolTip("Minimise")
        minimise_btn.clicked.connect(self.showMinimized)
        exit_btn = QPushButton("✕")
        exit_btn.setToolTip("Close (FocusGuard keeps running in the tray)")
        exit_btn.clicked.connect(self.hide)
        for btn in (minimise_btn, exit_btn):
            btn.setFixedSize(26, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                """
                QPushButton {
                    background: transparent;
                    border: none;
                    font-size: 13px;
                }
            """
            )
            title_bar.addWidget(btn)
        main_layout.addLayout(title_bar)

        close_app_btn = QPushButton("Close")
        close_app_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #e1e1e1;
                border: 1px solid #adadad;
                color: black;
                padding: 3px 14px;
            }
            QPushButton:pressed { background-color: #cccccc; }
        """
        )
        close_app_btn.clicked.connect(close_with_pin)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_row.addWidget(close_app_btn)
        close_row.addStretch()
        main_layout.addLayout(close_row)
        main_layout.addStretch()

        self._backend = get_backend()
        self._app_timer = QTimer(self)
        self._app_timer.timeout.connect(self.update_current_app)
        self._app_timer.start(2000)
        self.update_current_app()

    def update_current_app(self) -> None:
        window = self._backend.get_active_window()
        # skip ourselves so clicking the side bar doesn't replace the real app
        if window is None or window.pid == os.getpid():
            return
        self.current_app_label.setText(f"Current app: {window.app_name}")

    def closeEvent(self, event: QCloseEvent) -> None:
        # alt+f4 / cmd+w just hides the window, never quits
        event.ignore()
        self.hide()



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