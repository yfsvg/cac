"""Menu bar / system tray icon. Clicking it opens the dashboard."""
"""what actually appears on the widget"""

import os

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon
from focusguard.ui.dashboard import Dashboard

ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.png")


class Tray(QSystemTrayIcon):

    def __init__(self) -> None:

        icon = QIcon(ICON_PATH)
        super().__init__(icon)
        QApplication.setWindowIcon(icon)
        self.setToolTip("FocusGuard")
        self.dashboard = Dashboard()
        self.activated.connect(self.icon_clicked)
        self.show()


    def icon_clicked(self, reason) -> None:
        if reason != QSystemTrayIcon.ActivationReason.Trigger:
            return
        if self.dashboard.isVisible() and not self.dashboard.isMinimized():
            self.dashboard.hide()
        else:
            self.open_dashboard()


    def open_dashboard(self) -> None:
        # show and raise only hides it but daemon keeps on going baby
        self.dashboard.showNormal()  # also restores it if minimised
        self.dashboard.raise_()
        self.dashboard.activateWindow()
