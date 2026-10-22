from datetime import datetime

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

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


def is_allowed(settings, app, site, minutes_used):
    if app in settings["blocked_apps"]:
        return False
    if site in settings["blocked_sites"]:
        return False

    day = datetime.now().strftime("%a")
    time = datetime.now().strftime("%H:%M")
    for block in settings["study_times"]:
        parts = block.split()
        if parts[0] == day and parts[1] <= time and time < parts[2]:
            return False

    for limit in settings["time_limits"]:
        parts = limit.split()
        if parts[0] == app and minutes_used >= int(parts[1]):
            return False

    return True


class ListTab(QWidget):
    def __init__(self, settings, key, hint):
        super().__init__()
        self.settings = settings
        self.key = key

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
        if text != "":
            self.settings[self.key].append(text)
            self.items.addItem(text)
            memory.save(self.settings)
        self.entry.clear()

    def remove(self):
        row = self.items.currentRow()
        if row >= 0:
            self.settings[self.key].pop(row)
            self.items.takeItem(row)
            memory.save(self.settings)


class ParentalControls(QWidget):
    def __init__(self, settings):
        super().__init__()
        self.setWindowTitle("Parental Controls")
        self.resize(450, 350)

        tabs = QTabWidget()
        tabs.addTab(ListTab(settings, "blocked_apps", "steam.exe"), "Blocked Apps")
        tabs.addTab(ListTab(settings, "blocked_sites", "youtube.com"), "Blocked Sites")
        tabs.addTab(ListTab(settings, "study_times", "Mon 16:00 18:00"), "Study Time")
        tabs.addTab(ListTab(settings, "time_limits", "chrome.exe 60"), "Time Limits")

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)


if __name__ == "__main__":
    app = QApplication([])
    settings = ask_pin()
    if settings is not None:
        window = ParentalControls(settings)
        window.show()
        app.exec()
