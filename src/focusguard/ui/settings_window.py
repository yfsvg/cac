from PySide6.QtCore import QPointF, QSize, Qt, QTime
from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

import os
import time

from focusguard.ai import site_memory, vision
from focusguard.core import enforcement, session
from focusguard.storage import memory, time_tracking
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
    QLabel#SliderLabel { color: @onSurface; font-size: 14px; }
    QLabel#SliderHint { color: @onSurfaceVariant; font-size: 13px; }
    QSlider::groove:horizontal { height: 6px; background: @surfaceContainerHighest; border-radius: 3px; }
    QSlider::sub-page:horizontal { background: @primary; border-radius: 3px; }
    QSlider::handle:horizontal {
        background: @primary;
        width: 18px;
        height: 18px;
        margin: -6px 0;
        border-radius: 9px;
    }
    QSlider::handle:horizontal:disabled, QSlider::sub-page:horizontal:disabled { background: @outline; }
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


FREEZE_SECONDS = 3 * 24 * 60 * 60


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
    daysLeft = secondsLeft // 86400
    hoursLeft = (secondsLeft % 86400) // 3600
    minutesLeft = (secondsLeft % 3600) // 60
    if daysLeft > 0:
        return "locked for " + str(daysLeft) + "d " + str(hoursLeft) + "h"
    return "locked for " + str(hoursLeft) + "h " + str(minutesLeft) + "m"


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

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


def replaceBody(dropdown, newBody):
    dropdown.layout().removeWidget(dropdown.body)
    dropdown.body.deleteLater()
    dropdown.body = newBody
    newBody.hide()
    dropdown.layout().addWidget(newBody)


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
    def __init__(self, mainStyle, goBack, onMemoryCleared=None, onForceQuit=None):
        super().__init__()
        from focusguard.ui.dashboard import Dropdown, label

        self.mainStyle = mainStyle
        self.onMemoryCleared = onMemoryCleared
        self.onForceQuit = onForceQuit
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
            if settingName == "Absolute Time Limits":
                replaceBody(dropdown, self.makeBreakLimits())
            if settingName == "Schedule Time Limits":
                replaceBody(dropdown, self.makeSchedule())
            if settingName == "AI Categorizations":
                replaceBody(dropdown, self.makeAiTab())
            if settingName == "Super Focus Mode":
                replaceBody(dropdown, self.makeSuperFocus())
            if settingName == "Bail-Outs":
                replaceBody(dropdown, self.makeBailOuts())
            layout.addWidget(dropdown)
        layout.addSpacing(8)

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
        layout.addSpacing(8)

        layout.addWidget(label("Testing", "Section"))
        layout.addWidget(label("Only for the testing phase. Completely closes FocusGuard right away.", "Streak"))
        forceQuitRow = QHBoxLayout()
        forceQuitButton = QPushButton("Force quit", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        forceQuitButton.clicked.connect(self.forceQuit)
        forceQuitRow.addWidget(forceQuitButton)
        forceQuitRow.addStretch()
        layout.addLayout(forceQuitRow)
        layout.addSpacing(8)

        if os.environ.get("FOCUSGUARD_DEBUG") == "1":
            layout.addWidget(label("Debug", "Section"))
            layout.addWidget(label("Testing tools. These skip parental controls.", "Streak"))
            debugRow = QHBoxLayout()
            resetTimersButton = QPushButton("Reset lock timers", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            resetTimersButton.clicked.connect(self.resetLockTimers)
            clearMemoryButton = QPushButton("Clear all memory", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            clearMemoryButton.clicked.connect(self.clearAllMemory)
            debugRow.addWidget(resetTimersButton)
            debugRow.addWidget(clearMemoryButton)
            debugRow.addStretch()
            layout.addLayout(debugRow)
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

    def makeBreakLimits(self):
        from focusguard.ui.dashboard import label

        breakLimits = QWidget()
        breakLayout = QVBoxLayout(breakLimits)
        breakLayout.setContentsMargins(16, 8, 16, 8)
        breakLayout.setSpacing(8)

        self.breakCountLabel = label("", "SliderLabel")
        self.breakCountSlider = QSlider(Qt.Orientation.Horizontal)
        self.breakCountSlider.setRange(enforcement.MIN_BREAKS, enforcement.MAX_BREAKS)
        self.breakCountSlider.setValue(enforcement.getMaxBreaks())
        self.breakCountSlider.valueChanged.connect(self.updateBreakLabels)

        self.breakLengthLabel = label("", "SliderLabel")
        self.breakLengthSlider = QSlider(Qt.Orientation.Horizontal)
        self.breakLengthSlider.setRange(enforcement.MIN_BREAK_MINUTES, enforcement.MAX_BREAK_MINUTES)
        self.breakLengthSlider.setValue(enforcement.getBreakMinutes())
        self.breakLengthSlider.valueChanged.connect(self.updateBreakLabels)

        self.breakTotalLabel = label("", "SliderHint")
        self.saveBreaksButton = QPushButton("Save", objectName="MainButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.saveBreaksButton.clicked.connect(self.saveBreakLimits)
        saveRow = QHBoxLayout()
        saveRow.addStretch()
        saveRow.addWidget(self.saveBreaksButton)

        breakLayout.addWidget(self.breakCountLabel)
        breakLayout.addWidget(self.breakCountSlider)
        breakLayout.addSpacing(4)
        breakLayout.addWidget(self.breakLengthLabel)
        breakLayout.addWidget(self.breakLengthSlider)
        breakLayout.addWidget(self.breakTotalLabel)
        breakLayout.addLayout(saveRow)
        self.updateBreakLabels()
        return breakLimits

    def updateBreakLabels(self):
        breakCount = self.breakCountSlider.value()
        breakMinutes = self.breakLengthSlider.value()
        self.breakCountLabel.setText("Break periods per day: <b>" + str(breakCount) + "</b>")
        self.breakLengthLabel.setText("Break length: <b>" + str(breakMinutes) + " minutes</b>")
        totalMinutes = breakCount * breakMinutes
        totalText = str(totalMinutes) + " minutes"
        if totalMinutes >= 60:
            totalText = str(totalMinutes // 60) + "h " + str(totalMinutes % 60) + "m"
        hintText = "Up to " + totalText + " of breaks a day. After that, unproductive apps close for the rest of the day."
        secondsLeft = frozenSecondsLeft("Absolute Time Limits")
        isFrozen = secondsLeft > 0
        self.breakCountSlider.setEnabled(not isFrozen)
        self.breakLengthSlider.setEnabled(not isFrozen)
        self.saveBreaksButton.setEnabled(not isFrozen)
        if isFrozen:
            hintText = hintText + " (" + frozenText(secondsLeft) + ")"
        self.breakTotalLabel.setText(hintText)

    def saveBreakLimits(self):
        enforcement.saveBreakSettings(self.breakCountSlider.value(), self.breakLengthSlider.value())
        markChanged("Absolute Time Limits")
        self.updateBreakLabels()

    def forceQuit(self):
        if self.onForceQuit is not None:
            self.onForceQuit()

    def makeTab(self):
        tab = QWidget()
        tabLayout = QVBoxLayout(tab)
        tabLayout.setContentsMargins(16, 8, 16, 8)
        tabLayout.setSpacing(8)
        return tab, tabLayout

    def makeSaveRow(self, saveButton):
        saveRow = QHBoxLayout()
        saveRow.addStretch()
        saveRow.addWidget(saveButton)
        return saveRow

    def makeSchedule(self):
        from focusguard.ui.dashboard import label

        tab, tabLayout = self.makeTab()
        schedule = memory.load().get("studySchedule", {})
        tabLayout.addWidget(label("Study days and hours. During them your focus session keeps running until the end time.", "SliderHint"))
        dayRow = QHBoxLayout()
        self.dayBoxes = []
        for dayNumber in range(7):
            dayBox = QCheckBox(DAY_NAMES[dayNumber])
            dayBox.setChecked(dayNumber in schedule.get("days", []))
            self.dayBoxes.append(dayBox)
            dayRow.addWidget(dayBox)
        tabLayout.addLayout(dayRow)
        timeRow = QHBoxLayout()
        self.startTimeBox = QTimeEdit(QTime.fromString(schedule.get("start", "16:00"), "HH:mm"))
        self.startTimeBox.setDisplayFormat("HH:mm")
        self.endTimeBox = QTimeEdit(QTime.fromString(schedule.get("end", "18:00"), "HH:mm"))
        self.endTimeBox.setDisplayFormat("HH:mm")
        timeRow.addWidget(label("From", "SliderLabel"))
        timeRow.addWidget(self.startTimeBox)
        timeRow.addWidget(label("to", "SliderLabel"))
        timeRow.addWidget(self.endTimeBox)
        timeRow.addStretch()
        tabLayout.addLayout(timeRow)
        self.scheduleHint = label("", "SliderHint")
        tabLayout.addWidget(self.scheduleHint)
        self.saveScheduleButton = QPushButton("Save", objectName="MainButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.saveScheduleButton.clicked.connect(self.saveSchedule)
        tabLayout.addLayout(self.makeSaveRow(self.saveScheduleButton))
        self.updateSchedule()
        return tab

    def updateSchedule(self):
        secondsLeft = frozenSecondsLeft("Schedule Time Limits")
        for dayBox in self.dayBoxes:
            dayBox.setEnabled(secondsLeft == 0)
        self.startTimeBox.setEnabled(secondsLeft == 0)
        self.endTimeBox.setEnabled(secondsLeft == 0)
        self.saveScheduleButton.setEnabled(secondsLeft == 0)
        hintText = ""
        if secondsLeft > 0:
            hintText = "Schedule " + frozenText(secondsLeft)
        self.scheduleHint.setText(hintText)

    def saveSchedule(self):
        startText = self.startTimeBox.time().toString("HH:mm")
        endText = self.endTimeBox.time().toString("HH:mm")
        if startText >= endText:
            self.scheduleHint.setText("The end time has to be after the start time.")
            return
        chosenDays = []
        for dayNumber in range(7):
            if self.dayBoxes[dayNumber].isChecked():
                chosenDays.append(dayNumber)
        savedMemory = memory.load()
        savedMemory["studySchedule"] = {"days": chosenDays, "start": startText, "end": endText}
        memory.save(savedMemory)
        markChanged("Schedule Time Limits")
        self.updateSchedule()

    def makeAiTab(self):
        from focusguard.ui.dashboard import label

        tab, tabLayout = self.makeTab()
        explanation = (
            "The AI only checks websites in your browser that aren't on FocusGuard's built-in lists, "
            "after you've been on them for 1 minute. Each answer is remembered, so a site is only checked once."
        )
        tabLayout.addWidget(label(explanation, "SliderHint"))
        self.keyText = label("", "SliderLabel")
        tabLayout.addWidget(self.keyText)
        keyRow = QHBoxLayout()
        self.keyBox = QLineEdit()
        self.keyBox.setEchoMode(QLineEdit.EchoMode.Password)
        self.keyBox.setPlaceholderText("Gemini API key")
        self.saveKeyButton = QPushButton("Save key", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.saveKeyButton.clicked.connect(self.saveKey)
        keyRow.addWidget(self.keyBox)
        keyRow.addWidget(self.saveKeyButton)
        tabLayout.addLayout(keyRow)
        self.aiCountLabel = label("", "SliderHint")
        tabLayout.addWidget(self.aiCountLabel)
        self.aiSitesLabel = label("", "SliderHint")
        tabLayout.addWidget(self.aiSitesLabel)
        self.updateKeySection()
        return tab

    def updateAiSites(self):
        self.aiCountLabel.setText("AI checks today: " + str(vision.aiChecksToday()) + " of " + str(vision.AI_CHECKS_PER_DAY))
        sitesList = site_memory.rememberedSitesList()
        if len(sitesList) == 0:
            self.aiSitesLabel.setText("The AI hasn't sorted any websites yet.")
            return
        siteLines = []
        for site, category in sitesList:
            siteLines.append(site + ": " + category)
        self.aiSitesLabel.setText("Sites the AI sorted:\n" + "\n".join(siteLines))

    def makeSuperFocus(self):
        from focusguard.ui.dashboard import label

        tab, tabLayout = self.makeTab()
        self.superFocusBox = QCheckBox("Super Focus Mode")
        self.superFocusBox.setChecked(memory.load().get("superFocus", False))
        tabLayout.addWidget(self.superFocusBox)
        self.superFocusHint = label("", "SliderHint")
        tabLayout.addWidget(self.superFocusHint)
        self.saveSuperFocusButton = QPushButton("Save", objectName="MainButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.saveSuperFocusButton.clicked.connect(self.saveSuperFocus)
        tabLayout.addLayout(self.makeSaveRow(self.saveSuperFocusButton))
        self.updateSuperFocus()
        return tab

    def updateSuperFocus(self):
        secondsLeft = frozenSecondsLeft("Super Focus Mode")
        self.superFocusBox.setEnabled(secondsLeft == 0)
        self.saveSuperFocusButton.setEnabled(secondsLeft == 0)
        hintText = "When it's on, there are no breaks during a focus session. Unproductive apps only offer Emergency or Back to work."
        if secondsLeft > 0:
            hintText = hintText + " (" + frozenText(secondsLeft) + ")"
        self.superFocusHint.setText(hintText)

    def saveSuperFocus(self):
        savedMemory = memory.load()
        savedMemory["superFocus"] = self.superFocusBox.isChecked()
        memory.save(savedMemory)
        markChanged("Super Focus Mode")
        self.updateSuperFocus()

    def makeBailOuts(self):
        from focusguard.ui.dashboard import label

        tab, tabLayout = self.makeTab()
        self.bailOutLabel = label("", "SliderLabel")
        tabLayout.addWidget(self.bailOutLabel)
        self.bailOutSlider = QSlider(Qt.Orientation.Horizontal)
        self.bailOutSlider.setRange(0, session.MAX_BAIL_OUTS)
        self.bailOutSlider.setValue(session.bailOutsPerWeek())
        self.bailOutSlider.valueChanged.connect(self.updateBailOuts)
        tabLayout.addWidget(self.bailOutSlider)
        self.bailOutHint = label("", "SliderHint")
        tabLayout.addWidget(self.bailOutHint)
        self.saveBailOutsButton = QPushButton("Save", objectName="MainButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.saveBailOutsButton.clicked.connect(self.saveBailOuts)
        tabLayout.addLayout(self.makeSaveRow(self.saveBailOutsButton))
        self.updateBailOuts()
        return tab

    def updateBailOuts(self):
        self.bailOutLabel.setText("Bail-outs per week: <b>" + str(self.bailOutSlider.value()) + "</b>")
        hintText = "A bail-out ends your focus session early from the x on the session badge. You have " + str(session.bailOutsLeftThisWeek()) + " left this week."
        secondsLeft = frozenSecondsLeft("Bail-Outs")
        self.bailOutSlider.setEnabled(secondsLeft == 0)
        self.saveBailOutsButton.setEnabled(secondsLeft == 0)
        if secondsLeft > 0:
            hintText = hintText + " (" + frozenText(secondsLeft) + ")"
        self.bailOutHint.setText(hintText)

    def saveBailOuts(self):
        savedMemory = memory.load()
        savedMemory["bailOutsPerWeek"] = self.bailOutSlider.value()
        memory.save(savedMemory)
        markChanged("Bail-Outs")
        self.updateBailOuts()

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
        self.updateAiSites()

    def saveKey(self):
        if self.keyBox.text().strip() == "":
            return
        vision.saveApiKey(self.keyBox.text())
        self.keyBox.clear()
        markChanged("Gemini API key")
        self.updateKeySection()

    def refreshEverything(self):
        self.breakCountSlider.setValue(enforcement.getMaxBreaks())
        self.breakLengthSlider.setValue(enforcement.getBreakMinutes())
        self.updateBreakLabels()
        self.updateKeySection()
        self.updateSchedule()
        self.updateSuperFocus()
        self.bailOutSlider.setValue(session.bailOutsPerWeek())
        self.updateBailOuts()
        self.updateParentSection()

    def resetLockTimers(self):
        savedMemory = memory.load()
        savedMemory["changedAt"] = {}
        memory.save(savedMemory)
        self.refreshEverything()

    def clearAllMemory(self):
        answer = QMessageBox.question(
            self,
            "Clear all memory",
            "This deletes all saved settings, the parent PIN, streaks, break counts, tracked times and website verdicts. "
            "The Gemini API key is kept. This can't be undone.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        memory.FILE.unlink(missing_ok=True)
        time_tracking.FILE.unlink(missing_ok=True)
        site_memory.FILE.unlink(missing_ok=True)
        site_memory.rememberedSites = None
        if self.onMemoryCleared is not None:
            self.onMemoryCleared()
        self.refreshEverything()

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
