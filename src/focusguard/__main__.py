"""Entry point. For now this just launches the tray icon."""

from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtWidgets import QApplication

from focusguard.core.models import PermissionState
from focusguard.platform import get_backend
from focusguard.ui.parental_functions import setup_parental_functions, start_rules
from focusguard.ui.tray import Tray

log = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if sys.platform == "win32":
        # without this windows shows the python icon in the taskbar instead of ours
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FocusGuard")
    app = QApplication(sys.argv)
    app.setApplicationName("FocusGuard")
    app.setQuitOnLastWindowClosed(False)
    setup_parental_functions()

    backend = get_backend()
    backend.hide_from_taskbar()

    missing = [k for k, v in backend.check_permissions().items() if v is PermissionState.DENIED]
    if missing:
        log.warning("Missing permissions: %s (some info may be unavailable)", ", ".join(missing))

    tray = Tray()  # noqa: F841 (kept alive for the event loop)
    start_rules(tray)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
