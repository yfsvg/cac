from datetime import datetime

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from focusguard.core.classifier import site_root
from focusguard.storage import memory


def ask_pin():
    settings = memory.load()

    if settings["pin"] == "":
        pin, ok = QInputDialog.getText(None, "FocusGuard", "Create a PIN:", QLineEdit.EchoMode.Password)
        if not ok or pin == "":
            return None
        settings["pin"] = pin
        memory.save(settings)
        return settings

    while True:
        pin, ok = QInputDialog.getText(None, "FocusGuard", "Enter PIN:", QLineEdit.EchoMode.Password)
        if not ok:
            return None
        if pin == settings["pin"]:
            return settings


def clean_site(text):
    site = site_root(text)
    if site is None:
        return text
    return site


def fix_time(text):
    if len(text) == 4:
        return "0" + text
    return text


def in_study_time(settings):
    day = datetime.now().strftime("%a").lower()
    time = datetime.now().strftime("%H:%M")
    for block in settings["study_times"]:
        parts = block.split()
        if len(parts) != 3 or parts[0][:3] != day:
            continue
        if fix_time(parts[1]) <= time and time < fix_time(parts[2]):
            return True
    return False


def site_in_list(site, sites):
    if site is None:
        return False
    for item in sites:
        if site == item or site.endswith("." + item):
            return True
    return False


def is_allowed(settings, app_id, app_name, site, minutes_used):
    app_id = app_id.lower()
    short_name = app_id.replace(".exe", "").split(".")[-1]
    names = [app_id, app_name.lower(), short_name]

    for name in names:
        if name in settings["blocked_apps"]:
            return False
    if site_in_list(site, settings["blocked_sites"]):
        return False

    if in_study_time(settings):
        allowed = False
        for name in names:
            if name in settings["study_allowed"]:
                allowed = True
        if site_in_list(site, settings["study_allowed"]):
            allowed = True
        if not allowed:
            return False

    for limit in settings["time_limits"]:
        if " " not in limit:
            continue
        name, minutes = limit.rsplit(" ", 1)
        if name in names and minutes.isdigit() and minutes_used >= int(minutes):
            return False

    return True


class ListTab(QWidget):
    def __init__(self, settings, key, hint, is_site=False):
        super().__init__()
        self.settings = settings
        self.key = key
        self.is_site = is_site

        self.items = QListWidget()
        self.items.addItems(settings[key])

        self.entry = QLineEdit()
        self.entry.setPlaceholderText(hint)

        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add)

        remove_button = QPushButton("Remove")
        remove_button.clicked.connect(self.remove)

        row = QHBoxLayout()
        row.addWidget(self.entry)
        row.addWidget(add_button)
        row.addWidget(remove_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.items)
        layout.addLayout(row)

    def add(self):
        text = self.entry.text().strip().lower()
        if self.is_site:
            text = clean_site(text)
        if text != "" and text not in self.settings[self.key]:
            self.settings[self.key].append(text)
            self.items.addItem(text)
            memory.save_key(self.key, self.settings[self.key])
        self.entry.clear()

    def remove(self):
        row = self.items.currentRow()
        if row >= 0:
            self.settings[self.key].pop(row)
            self.items.takeItem(row)
            memory.save_key(self.key, self.settings[self.key])


class ParentalControls(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.setWindowTitle("Parental Controls")
        self.resize(450, 350)

        tabs = QTabWidget()
        tabs.addTab(ListTab(settings, "blocked_apps", "steam.exe or Steam"), "Blocked Apps")
        tabs.addTab(ListTab(settings, "blocked_sites", "youtube.com", True), "Blocked Sites")
        tabs.addTab(ListTab(settings, "study_times", "Mon 16:00 18:00"), "Study Time")
        tabs.addTab(ListTab(settings, "study_allowed", "word.exe or docs.google.com", True), "Allowed While Studying")
        tabs.addTab(ListTab(settings, "time_limits", "chrome.exe 60"), "Time Limits")

        change_pin_button = QPushButton("Change PIN")
        change_pin_button.clicked.connect(self.change_pin)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(change_pin_button)

    def change_pin(self):
        pin, ok = QInputDialog.getText(self, "FocusGuard", "New PIN:", QLineEdit.EchoMode.Password)
        if ok and pin != "":
            memory.save_key("pin", pin)
            QMessageBox.information(self, "FocusGuard", "PIN changed")


if __name__ == "__main__":
    app = QApplication([])
    settings = ask_pin()
    if settings is not None:
        window = ParentalControls(settings)
        window.show()
        app.exec()
