from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from arete.core import keep_alive
from arete.core.models import PermissionState
from arete.platform import get_backend
from arete.ui.tray import Tray

log = logging.getLogger(__name__)


def main() -> None:
    # keep alive helper is just us w/ --keep-alive, it watches arete
    if len(sys.argv) > 2 and sys.argv[1] == "--keep-alive":
        keep_alive.helperLoop(int(sys.argv[2]))
        return
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    # startup checks, admin + no terminal + only one copy
    keep_alive.makeSureIsAdmin()
    keep_alive.stopCtrlC()
    keep_alive.runWithoutTerminal()
    if keep_alive.alreadyRunning():
        return

    # qt app, stays alive w/ no windows since tray icon is the way in
    app = QApplication(sys.argv)
    app.setApplicationName("Arete")
    app.setQuitOnLastWindowClosed(False)
    keep_alive.quitOnCtrlC()
    keep_alive.startHelper()
    backend = get_backend()
    backend.hide_from_taskbar()

    # warn once at startup instead of silently failing every check
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
