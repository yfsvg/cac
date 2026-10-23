"""Menu bar / system tray icon. Clicking it opens the dashboard."""
"""what actually appears on the widget"""

from PySide6.QtWidgets import QApplication, QStyle, QSystemTrayIcon
from focusguard.ui.dashboard import Dashboard


class Tray(QSystemTrayIcon):

    def __init__(self) -> None:

        super().__init__(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        self.dashboard = Dashboard()
        self.dashboard.enforcer.notify = self.showMessage
        self.activated.connect(self.open_dashboard)
        self.show()


    def open_dashboard(self) -> None:
        # show and raise only hides it but daemon keeps on going baby
        self.dashboard.show()
        self.dashboard.raise_()
        self.dashboard.activateWindow()
