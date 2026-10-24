"""Entry point. For now this just launches the tray icon."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from focusguard.core import keep_alive, session
from focusguard.core.models import PermissionState
from focusguard.platform import get_backend
from focusguard.ui.tray import Tray

log = logging.getLogger(__name__)


def main() -> None:
    if len(sys.argv) > 2 and sys.argv[1] == "--keep-alive":
        keep_alive.helperLoop(int(sys.argv[2]))
        return
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    keep_alive.stopCtrlC()
    keep_alive.runWithoutTerminal()
    if keep_alive.alreadyRunning():
        return
    session.resumeAllowed = "--resume" in sys.argv
    app = QApplication(sys.argv)
    app.setApplicationName("FocusGuard")
    app.setQuitOnLastWindowClosed(False)
    keep_alive.startHelper()
    backend = get_backend()
    backend.hide_from_taskbar()

    missingPermissions = []
    for permissionName, permissionState in backend.check_permissions().items():
        if permissionState is PermissionState.DENIED:
            missingPermissions.append(permissionName)
    if len(missingPermissions) > 0:
        log.warning("Missing permissions: %s (some info may be unavailable)", ", ".join(missingPermissions))

    tray = Tray()  # noqa: F841 (kept alive for the event loop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
