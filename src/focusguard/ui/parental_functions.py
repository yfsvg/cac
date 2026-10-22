import os
import signal
import subprocess
import sys
import time

import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from focusguard.storage import memory
from focusguard.ui.parental_controls import ask_pin

helper = None
timer = None


def python_path():
    if sys.platform == "win32":
        return os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return sys.executable


def start_in_background(command):
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


def stop_ctrl_c():
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    if sys.platform != "win32":
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)


def started_from_terminal():
    if sys.platform == "win32":
        return not sys.executable.lower().endswith("pythonw.exe")
    return sys.stdin is not None and sys.stdin.isatty()


def run_without_terminal():
    if not started_from_terminal():
        return
    start_in_background([python_path(), "-m", "focusguard"])
    sys.exit(0)


def start_helper():
    global helper
    helper = start_in_background([python_path(), "-m", "focusguard.ui.parental_functions", str(os.getpid())])


def check_helper():
    if helper.poll() is not None:
        start_helper()


def close_with_pin():
    settings = ask_pin()
    if settings is None:
        return
    timer.stop()
    helper.kill()
    QApplication.quit()


def setup_parental_functions():
    global timer
    stop_ctrl_c()
    run_without_terminal()
    memory.load()
    start_helper()
    timer = QTimer()
    timer.timeout.connect(check_helper)
    timer.start(2000)


def helper_loop(app_pid):
    while True:
        time.sleep(2)
        if not psutil.pid_exists(app_pid):
            start_in_background([python_path(), "-m", "focusguard"])
            return


if __name__ == "__main__":
    helper_loop(int(sys.argv[1]))
