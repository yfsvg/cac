from __future__ import annotations
import os
import signal
import subprocess
import sys
import time

import psutil
from PySide6.QtCore import QTimer

helper = None
helperTimer = None


def isDebugMode() -> bool:
    return os.environ.get("FOCUSGUARD_DEBUG") == "1"


def isFrozen() -> bool:
    return getattr(sys, "frozen", False)


def pythonPath() -> str:
    if sys.platform == "win32":
        return os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return sys.executable


def appCommand() -> list:
    if isFrozen():
        return [sys.executable]
    return [pythonPath(), "-m", "focusguard"]


def helperCommand(appPid: int) -> list:
    if isFrozen():
        return [sys.executable, "--keep-alive", str(appPid)]
    return [pythonPath(), "-m", "focusguard.core.keep_alive", str(appPid)]


def startInBackground(command: list):
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(command, creationflags=flags)
    return subprocess.Popen(
        command,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stopCtrlC() -> None:
    if isDebugMode():
        return
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if sys.platform != "win32":
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)


def startedFromTerminal() -> bool:
    if isFrozen():
        return False
    if sys.platform == "win32":
        return not sys.executable.lower().endswith("pythonw.exe")
    return sys.stdin is not None and sys.stdin.isatty()


def runWithoutTerminal() -> None:
    if isDebugMode() or not startedFromTerminal():
        return
    startInBackground(appCommand())
    sys.exit(0)


def startHelper() -> None:
    global helper, helperTimer
    if isDebugMode():
        return
    helper = startInBackground(helperCommand(os.getpid()))
    if helperTimer is None:
        helperTimer = QTimer()
        helperTimer.timeout.connect(checkHelper)
        helperTimer.start(2000)


def checkHelper() -> None:
    if helper is not None and helper.poll() is not None:
        startHelper()


def stopHelper() -> None:
    if helperTimer is not None:
        helperTimer.stop()
    if helper is not None:
        helper.kill()


def helperLoop(appPid: int) -> None:
    while True:
        time.sleep(2)
        if not psutil.pid_exists(appPid):
            startInBackground(appCommand())
            return


if __name__ == "__main__":
    helperLoop(int(sys.argv[1]))
