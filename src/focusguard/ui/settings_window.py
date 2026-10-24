from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import time

from focusguard.ai import vision
from focusguard.storage import memory
from focusguard.ui.theme import applyTheme, getColors

SETTINGS_STYLE = """
    QDialog#PinDialog { background-color: @surface; }
    QPushButton#PinButton {
        color: @onSecondaryContainer;
        font-size: 14px;
        padding: 8px 16px;
        background-color: @secondaryContainer;
        border: none;
        border-radius: 16px;
    }
    QPushButton#PinButton:hover { background-color: @primaryContainer; color: @onPrimaryContainer; }
    QPushButton#MainButton {
        color: @onPrimary;
        font-size: 14px;
        font-weight: 600;
        padding: 8px 16px;
        background-color: @primary;
        border: none;
        border-radius: 16px;
    }
    QLineEdit {
        color: @onSurface;
        font-size: 15px;
        padding: 10px 14px;
        background-color: @surfaceContainerHighest;
        border: none;
        border-bottom: 2px solid @primary;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }
    QLabel#ErrorText { color: @error; font-size: 13px; }
    QCheckBox { color: @onSurface; font-size: 14px; spacing: 10px; }
"""

def makeBackArrow():
    arrow = QPixmap(32, 32)
    arrow.fill(Qt.GlobalColor.transparent)
    painter = QPainter(arrow)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(getColors()["onSurface"]), 2.4)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawLine(QPointF(9, 16), QPointF(23, 16))
    painter.drawLine(QPointF(9, 16), QPointF(15, 10))
    painter.drawLine(QPointF(9, 16), QPointF(15, 22))
    painter.end()
    return QIcon(arrow)


FREEZE_SECONDS = 3 * 60 * 60


def markChanged(settingName):
    savedMemory = memory.load()
    changedAt = savedMemory.get("changedAt", {})
    changedAt[settingName] = time.time()
    savedMemory["changedAt"] = changedAt
    memory.save(savedMemory)


def frozenSecondsLeft(settingName):
    changedAt = memory.load().get("changedAt", {})
    if settingName not in changedAt:
        return 0
    secondsLeft = changedAt[settingName] + FREEZE_SECONDS - time.time()
    if secondsLeft < 0:
        return 0
    return int(secondsLeft)


def frozenText(secondsLeft):
    hoursLeft = secondsLeft // 3600
    minutesLeft = (secondsLeft % 3600) // 60
    return "locked for " + str(hoursLeft) + "h " + str(minutesLeft) + "m"


SETTING_NAMES = ["Absolute Time Limits", "Schedule Time Limits", "AI Categorizations", "Super Focus Mode", "Bail-Outs"]


def getPin():
    return memory.load().get("parentPin", "")


def savePin(newPin):
    savedMemory = memory.load()
    savedMemory["parentPin"] = newPin
    memory.save(savedMemory)


def getLockedSettings():
    return memory.load().get("lockedSettings", [])


def saveLockedSettings(lockedSettings):
    savedMemory = memory.load()
    savedMemory["lockedSettings"] = lockedSettings
    memory.save(savedMemory)


class PinDialog(QDialog):
    def __init__(self, parent, mainStyle, creating):
        super().__init__(parent)
        from focusguard.ui.dashboard import label

        self.creating = creating
        self.setObjectName("PinDialog")
        self.setWindowTitle("Parental Controls")
        self.setFixedWidth(360)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
        self.setStyleSheet(applyTheme(mainStyle + SETTINGS_STYLE))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        if creating:
            layout.addWidget(label("Set up parental controls", "Section"))
            layout.addWidget(label("Create a PIN. You'll need it to change locked settings.", "Streak"))
        else:
            layout.addWidget(label("Enter the parent PIN", "Section"))

        self.pinBox = QLineEdit()
        self.pinBox.setEchoMode(QLineEdit.EchoMode.Password)
        self.pinBox.setPlaceholderText("PIN")
        layout.addWidget(self.pinBox)

        self.confirmBox = QLineEdit()
        self.confirmBox.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirmBox.setPlaceholderText("Type the PIN again")
        layout.addWidget(self.confirmBox)
        if not creating:
            self.confirmBox.hide()

        self.errorText = QLabel("", objectName="ErrorText")
        self.errorText.hide()
        layout.addWidget(self.errorText)

        buttonRow = QHBoxLayout()
        buttonRow.addStretch()
        cancelButton = QPushButton("Cancel", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        cancelButton.clicked.connect(self.reject)
        okButton = QPushButton("Save PIN" if creating else "Unlock", objectName="MainButton", cursor=Qt.CursorShape.PointingHandCursor)
        okButton.clicked.connect(self.checkPin)
        buttonRow.addWidget(cancelButton)
        buttonRow.addWidget(okButton)
        layout.addLayout(buttonRow)

        self.pinBox.returnPressed.connect(self.checkPin)
        self.confirmBox.returnPressed.connect(self.checkPin)

    def showError(self, text):
        self.errorText.setText(text)
        self.errorText.show()

    def checkPin(self):
        typedPin = self.pinBox.text()
        if self.creating:
            if typedPin == "":
                self.showError("Type a PIN first")
            elif typedPin != self.confirmBox.text():
                self.showError("The PINs didn't match")
            else:
                savePin(typedPin)
                self.accept()
        elif typedPin == getPin():
            self.accept()
        else:
            self.pinBox.clear()
            self.showError("Wrong PIN")


def askForPin(parent, mainStyle):
    if getPin() == "":
        return True
    return PinDialog(parent, mainStyle, False).exec() == QDialog.DialogCode.Accepted


class SettingsPage(QWidget):
    def __init__(self, mainStyle, goBack):
        super().__init__()
        from focusguard.ui.dashboard import Dropdown, label

        self.mainStyle = mainStyle
        self.setStyleSheet(applyTheme(SETTINGS_STYLE))

        scroll = QScrollArea(widgetResizable=True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget(objectName="Content")
        scroll.setWidget(content)

        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(scroll)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(12)

        topRow = QHBoxLayout()
        backButton = QPushButton(objectName="ThemeButton", cursor=Qt.CursorShape.PointingHandCursor)
        backButton.setFixedSize(32, 32)
        backButton.setIcon(makeBackArrow())
        backButton.setIconSize(QSize(32, 32))
        backButton.clicked.connect(goBack)
        topRow.setSpacing(10)
        topRow.addWidget(backButton, alignment=Qt.AlignmentFlag.AlignVCenter)
        settingsTitle = label("Settings", "AppName")
        settingsTitle.setWordWrap(False)
        topRow.addWidget(settingsTitle, alignment=Qt.AlignmentFlag.AlignVCenter)
        topRow.addStretch()
        layout.addLayout(topRow)
        layout.addSpacing(4)

        layout.addWidget(label("App Config", "Section"))
        for settingName in SETTING_NAMES:
            dropdown = Dropdown(settingName)
            dropdown.header.clicked.disconnect()
            dropdown.header.clicked.connect(lambda checked=False, d=dropdown: self.openSetting(d))
            layout.addWidget(dropdown)
        layout.addSpacing(8)

        layout.addWidget(label("AI Website Checking", "Section"))
        self.keyText = label("", "Streak")
        layout.addWidget(self.keyText)
        keyRow = QHBoxLayout()
        self.keyBox = QLineEdit()
        self.keyBox.setEchoMode(QLineEdit.EchoMode.Password)
        self.keyBox.setPlaceholderText("Gemini API key")
        self.saveKeyButton = QPushButton("Save key", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.saveKeyButton.clicked.connect(self.saveKey)
        keyRow.addWidget(self.keyBox)
        keyRow.addWidget(self.saveKeyButton)
        layout.addLayout(keyRow)
        layout.addSpacing(8)
        self.updateKeySection()

        layout.addWidget(label("Parental Controls", "Section"))
        self.parentText = label("", "Streak")
        layout.addWidget(self.parentText)

        self.lockBoxes = {}
        for settingName in SETTING_NAMES:
            lockBox = QCheckBox("Lock " + settingName)
            lockBox.clicked.connect(self.saveLocks)
            self.lockBoxes[settingName] = lockBox
            layout.addWidget(lockBox)

        parentRow = QHBoxLayout()
        self.setupButton = QPushButton("Set up parental controls", objectName="MainButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.setupButton.clicked.connect(self.setUpParentalControls)
        self.changePinButton = QPushButton("Change PIN", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.changePinButton.clicked.connect(self.changePin)
        self.turnOffButton = QPushButton("Turn off", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.turnOffButton.clicked.connect(self.turnOffParentalControls)
        parentRow.addWidget(self.setupButton)
        parentRow.addWidget(self.changePinButton)
        parentRow.addWidget(self.turnOffButton)
        parentRow.addStretch()
        layout.addLayout(parentRow)
        layout.addStretch()

        self.updateParentSection()

    def updateParentSection(self):
        isSetUp = getPin() != ""
        lockedSettings = getLockedSettings()
        self.setupButton.setVisible(not isSetUp)
        self.changePinButton.setVisible(isSetUp)
        self.turnOffButton.setVisible(isSetUp)
        for settingName in self.lockBoxes:
            lockBox = self.lockBoxes[settingName]
            lockBox.setVisible(isSetUp)
            lockBox.setChecked(settingName in lockedSettings)
            secondsLeft = frozenSecondsLeft("Lock " + settingName)
            lockBox.setEnabled(secondsLeft == 0)
            if secondsLeft == 0:
                lockBox.setText("Lock " + settingName)
            else:
                lockBox.setText("Lock " + settingName + " (" + frozenText(secondsLeft) + ")")
        if isSetUp:
            self.parentText.setText("Parental controls are on. Locked settings need the PIN to open.")
        else:
            self.parentText.setText("Parental controls are off.")

    def openSetting(self, dropdown):
        if not dropdown.body.isVisible() and dropdown.title in getLockedSettings():
            if not askForPin(self, self.mainStyle):
                return
        dropdown.toggle()

    def saveLocks(self):
        if not askForPin(self, self.mainStyle):
            self.updateParentSection()
            return
        oldLocks = getLockedSettings()
        lockedSettings = []
        for settingName in self.lockBoxes:
            if self.lockBoxes[settingName].isChecked():
                lockedSettings.append(settingName)
            if (settingName in oldLocks) != self.lockBoxes[settingName].isChecked():
                markChanged("Lock " + settingName)
        saveLockedSettings(lockedSettings)
        self.updateParentSection()

    def updateKeySection(self):
        secondsLeft = frozenSecondsLeft("Gemini API key")
        self.keyBox.setEnabled(secondsLeft == 0)
        self.saveKeyButton.setEnabled(secondsLeft == 0)
        if vision.getApiKey() == "":
            keyStatus = "No key saved. Unknown websites won't be checked by AI."
        else:
            keyStatus = "Key saved. Unknown websites are checked by AI after 1 minute."
        if secondsLeft > 0:
            keyStatus = keyStatus + " (" + frozenText(secondsLeft) + ")"
        self.keyText.setText(keyStatus)

    def saveKey(self):
        if self.keyBox.text().strip() == "":
            return
        vision.saveApiKey(self.keyBox.text())
        self.keyBox.clear()
        markChanged("Gemini API key")
        self.updateKeySection()

    def setUpParentalControls(self):
        PinDialog(self, self.mainStyle, True).exec()
        self.updateParentSection()

    def changePin(self):
        if askForPin(self, self.mainStyle):
            PinDialog(self, self.mainStyle, True).exec()

    def turnOffParentalControls(self):
        if askForPin(self, self.mainStyle):
            savePin("")
            saveLockedSettings([])
            self.updateParentSection()
