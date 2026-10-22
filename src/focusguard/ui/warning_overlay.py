"""The always-on-top overlay. Will become the "get off Steam" warning; for now it just shows what
FocusGuard sees: the frontmost app, its window title, and the site root when it's a browser.

Run standalone with `python -m focusguard.ui.warning_overlay`.
"""

from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout, QWidget

from focusguard.core.classifier import site_root
from focusguard.core.models import ActiveWindow, PermissionState
from focusguard.platform import PlatformBackend, get_backend

# top part
from focusguard.ui.tray import Tray

log = logging.getLogger(__name__)

POLL_INTERVAL_MS = 1000
MARGIN = 16
WIDTH = 340


class WarningOverlay(QWidget):
    def __init__(self, backend: PlatformBackend) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
            | Qt.WindowType.WindowTransparentForInput,
        )
        self.backend = backend
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(WIDTH)

        card = QFrame(self)
        card.setObjectName("card")
        card.setStyleSheet(
            "#card { background: rgba(20, 20, 24, 210); border-radius: 12px; }"
            "QLabel { color: #f2f2f2; background: transparent; }"
            "#site { color: #8fd3ff; }"
            "#title { color: #b8b8c0; }"
        )
        self.app_label = QLabel("…", card)
        self.app_label.setFont(QFont(self.font().family(), 13, QFont.Weight.DemiBold))
        self.site_label = QLabel(card)
        self.site_label.setObjectName("site")
        self.title_label = QLabel(card)
        self.title_label.setObjectName("title")

        inner = QVBoxLayout(card)
        inner.setContentsMargins(14, 10, 14, 10)
        inner.setSpacing(2)
        for label in (self.app_label, self.site_label, self.title_label):
            inner.addWidget(label)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)

    def start(self) -> None:
        self.refresh()
        self.show()
        try:
            self.backend.configure_overlay_window(int(self.winId()))
        except Exception:
            log.exception("Couldn't make the overlay float above other windows")
        self.timer.start(POLL_INTERVAL_MS)

    def refresh(self) -> None:
        window = self.backend.get_active_window()
        # Ignore ourselves in case the overlay ever ends up frontmost.
        if window is None or window.pid == os.getpid():
            return
        root = None
        if self.backend.is_browser(window):
            root = site_root(self.backend.get_browser_url(window)) or "(no site)"
        self.show_status(window, root)

    def show_status(self, window: ActiveWindow, root: str | None) -> None:
        self.app_label.setText(window.app_name or window.app_id or "Unknown app")
        self.site_label.setText(root or "")
        self.site_label.setVisible(root is not None)
        metrics = self.title_label.fontMetrics()
        self.title_label.setText(
            metrics.elidedText(window.title or "(no window title)", Qt.TextElideMode.ElideRight, WIDTH - 28)
        )
        self.adjustSize()
        self._move_to_corner()

    def _move_to_corner(self) -> None:
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - self.width() - MARGIN, screen.top() + MARGIN)


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("FocusGuard")
    app.setQuitOnLastWindowClosed(False)
    backend = get_backend()
    backend.hide_from_taskbar()

    missing = [k for k, v in backend.check_permissions().items() if v is PermissionState.DENIED]
    if missing:
        log.warning("Missing permissions: %s (some info may be unavailable)", ", ".join(missing))

    overlay = WarningOverlay(backend)
    overlay.start()
    tray = Tray()  # noqa: F841 (kept alive for the event loop)
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
