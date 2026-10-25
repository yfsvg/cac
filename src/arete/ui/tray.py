"""Menu bar / system tray icon. Clicking it opens the dashboard."""
"""what actually appears on the widget"""

from PySide6.QtWidgets import QApplication, QStyle, QSystemTrayIcon
from arete.ui import animations
from arete.ui.dashboard import Dashboard


class Tray(QSystemTrayIcon):

    def __init__(self) -> None:

        super().__init__(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
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
