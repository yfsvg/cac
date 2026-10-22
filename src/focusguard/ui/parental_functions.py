import os
import signal
import subprocess
import sys
import time
from datetime import datetime

import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from focusguard.core.classifier import site_root
from focusguard.platform import get_backend
from focusguard.storage import memory
from focusguard.ui.parental_controls import ParentalControls, ask_pin, is_allowed

helper = None
timer = None
rules_timer = None
tray_icon = None
parental_window = None
warned = {}

SAFE_APPS = [
    "explorer.exe",
    "searchhost.exe",
    "startmenuexperiencehost.exe",
    "shellexperiencehost.exe",
    "taskmgr.exe",
    "lockapp.exe",
    "textinputhost.exe",
    "com.apple.finder",
    "com.apple.dock",
    "com.apple.loginwindow",
    "com.apple.systemuiserver",
    "com.apple.controlcenter",
    "com.apple.spotlight",
]


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


def open_parental_controls():
    global parental_window
    settings = ask_pin()
    if settings is None:
        return
    parental_window = ParentalControls(settings)
    parental_window.show()
    parental_window.raise_()
    parental_window.activateWindow()


def start_rules(tray):
    global rules_timer, tray_icon
    tray_icon = tray
    rules_timer = QTimer()
    rules_timer.timeout.connect(check_rules)
    rules_timer.start(5000)


def check_rules():
    backend = get_backend()
    window = backend.get_active_window()
    if window is None or window.pid == os.getpid():
        return
    app_id = window.app_id.lower()
    if app_id in SAFE_APPS:
        return

    settings = memory.load()
    today = datetime.now().strftime("%Y-%m-%d")
    if settings["usage_day"] != today:
        settings["usage_day"] = today
        settings["usage"] = {}
    if backend.get_idle_seconds() < 60:
        settings["usage"][app_id] = settings["usage"].get(app_id, 0) + 5
    memory.save(settings)
    minutes_used = settings["usage"].get(app_id, 0) // 60

    site = None
    if backend.is_browser(window):
        try:
            site = site_root(backend.get_browser_url(window))
        except Exception:
            site = None

    if is_allowed(settings, app_id, window.app_name, site, minutes_used):
        if app_id in warned:
            del warned[app_id]
        return

    if app_id not in warned or time.time() - warned[app_id] > 120:
        warned[app_id] = time.time()
        tray_icon.showMessage("FocusGuard", window.app_name + " isn't allowed right now. It will close in 30 seconds.")
        return

    seconds = time.time() - warned[app_id]
    if seconds >= 45:
        backend.close_app(window.pid, force=True)
    elif seconds >= 30:
        backend.close_app(window.pid)


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
