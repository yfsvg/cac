"""Menu bar / system tray icon. Clicking it opens the dashboard."""
"""what actually appears on the widget"""

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from arete.ui import animations
from arete.ui.close_screen import CloseScreen
from arete.ui.dashboard import Dashboard


# app icon, used for the tray + windows + dock
ICON_FILE = Path(__file__).parent / "assets" / "icon.png"


def appIcon():
    return QIcon(str(ICON_FILE))


class Tray(QSystemTrayIcon):

    def __init__(self) -> None:

        super().__init__(appIcon())
        QApplication.instance().setWindowIcon(appIcon())
        self.dashboard = Dashboard()
        # enforcer warnings show up as tray notifs
        self.dashboard.enforcer.notify = self.showMessage
        self.closeScreen = None

        # right click menu. mac opens it on any click so open arete has to be in here too
        self.menu = QMenu()
        self.menu.addAction("Open Arete").triggered.connect(self.openDashboard)
        self.menu.addSeparator()
        self.menu.addAction("Close Arete").triggered.connect(self.askToClose)
        self.setContextMenu(self.menu)

        self.activated.connect(self.iconClicked)
        self.show()


    def iconClicked(self, reason) -> None:
        # right click already shows the menu
        if reason != QSystemTrayIcon.ActivationReason.Context:
            self.openDashboard()

    def openDashboard(self) -> None:
        if not self.dashboard.isVisible():
            self.dashboard.show()
            animations.slideWindowIn(self.dashboard)
            self.dashboard.playEntrance()
        # show and raise only hides it but daemon keeps on going baby
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()


    # closing, 1 min countdown first so u cant just quit on impulse

    def askToClose(self) -> None:
        if self.closeScreen is not None:
            self.closeScreen.bringBack()
            return
        self.closeScreen = CloseScreen(lambda: self.dashboard.inSession, self.closeCancelled, self.dashboard.quitArete)
        self.closeScreen.popUp()

    def closeCancelled(self) -> None:
        self.closeScreen = None
