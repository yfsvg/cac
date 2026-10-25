from PySide6.QtCore import QPointF, QSize, Qt, QTime, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QStyleFactory,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from arete.ai import site_memory, vision
from arete.core import climbing, enforcement, mountains, setting_changes
from arete.core.debug_mode import isDebugMode
from arete.core.setting_changes import frozenSecondsLeft, markChanged
from arete.storage import memory, parent_pin, time_tracking
from arete.ui.theme import applyTheme, getColors

# Settings page -- app config dropdowns, AI key, parental controls

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
        border-bottom: 4px solid @primaryShadow;
        border-radius: 16px;
    }
    QPushButton#MainButton:pressed { border-bottom: 1px solid @primaryShadow; padding-top: 11px; }
    QLineEdit {
        color: @onSurface;
        font-size: 15px;
        padding: 10px 14px;
        background-color: @field;
        border: 1.5px solid @fieldBorder;
        border-radius: 12px;
    }
    QLineEdit:focus { border: 1.5px solid @primary; }
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
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border-radius: 6px;
        border: 2px solid @outline;
        background-color: transparent;
    }
    QCheckBox::indicator:checked { background-color: @primary; border-color: @primary; }
    QCheckBox#Switch::indicator {
        width: 40px;
        height: 22px;
        border-radius: 11px;
        border: none;
        background-color: @surfaceContainerHighest;
        image: none;
    }
    QCheckBox#Switch::indicator:checked { background-color: @primary; }
    QPushButton#DayChip {
        color: @onSurfaceVariant;
        font-size: 13px;
        font-weight: 600;
        background-color: @surfaceContainerHighest;
        border: none;
        border-radius: 15px;
        min-width: 42px;
        min-height: 30px;
    }
    QPushButton#DayChip:checked { color: @onPrimary; background-color: @primary; }
    QPushButton#DayChip:disabled { color: @outline; }
    QPushButton#DayChip:checked:disabled { color: @onPrimary; background-color: @primary; }
    QFrame#TimeChip { background-color: @field; border: 1.5px solid @fieldBorder; border-radius: 10px; }
    QTimeEdit { color: @onSurface; background-color: transparent; font-size: 14px; font-weight: 600; }
    QTimeEdit:disabled { color: @onSurface; }
    QLabel#ChipOn {
        color: @onGreenContainer;
        background-color: @greenContainer;
        font-size: 12px;
        font-weight: 600;
        border-radius: 10px;
        padding: 3px 10px;
    }
    QLabel#ChipOff {
        color: @onErrorContainer;
        background-color: @errorContainer;
        font-size: 12px;
        font-weight: 600;
        border-radius: 10px;
        padding: 3px 10px;
    }
    QLabel#SitesList { color: @onSurface; font-size: 13px; }
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





# seconds -> "2d 23h" etc

def frozenText(secondsLeft):
    daysLeft = secondsLeft // 86400
    hoursLeft = (secondsLeft % 86400) // 3600
    minutesLeft = (secondsLeft % 3600) // 60
    if daysLeft > 0:
        return "locked for " + str(daysLeft) + "d " + str(hoursLeft) + "h"
    return "locked for " + str(hoursLeft) + "h " + str(minutesLeft) + "m"


def waitText(secondsLeft):
    minutesLeft = secondsLeft // 60
    if minutesLeft >= 10:
        return str(minutesLeft) + "m"
    return str(minutesLeft) + "m " + str(secondsLeft % 60) + "s"


DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def scheduleText(schedule):
    days = schedule["days"]
    if len(days) == 7:
        dayText = "Every day"
    else:
        dayNames = []
        for dayNumber in days:
            dayNames.append(DAY_NAMES[dayNumber])
        dayText = ", ".join(dayNames)
    return dayText + "  " + schedule["start"] + " to " + schedule["end"]

SETTING_NAMES = ["Absolute Time Limits", "Schedule Time Limits", "AI Categorizations"]





# Parental controls - which settings need the pin

def getLockedSettings():
    return memory.load().get("lockedSettings", [])


def saveLockedSettings(lockedSettings):
    savedMemory = memory.load()
    savedMemory["lockedSettings"] = lockedSettings
    memory.save(savedMemory)


# Swaps a dropdown's placeholder text for real controls

def replaceBody(dropdown, newBody):
    dropdown.layout().removeWidget(dropdown.body)
    dropdown.body.deleteLater()
    dropdown.body = newBody
    newBody.hide()
    dropdown.layout().addWidget(newBody)





# PIN popup, for making a new pin or unlocking a locked setting

class PinDialog(QDialog):
    def __init__(self, parent, mainStyle, creating):
        super().__init__(parent)
        from arete.ui.dashboard import label

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
                parent_pin.savePin(typedPin)
                self.accept()
        elif parent_pin.pinMatches(typedPin):
            self.accept()
        else:
            self.pinBox.clear()
            self.showError("Wrong PIN")


def askForPin(parent, mainStyle):
    if not parent_pin.hasPin():
        return True
    return PinDialog(parent, mainStyle, False).exec() == QDialog.DialogCode.Accepted





# settings page, swaps in where the dashboard normally is

class SettingsPage(QWidget):
    def __init__(self, mainStyle, goBack, onMemoryCleared=None, onForceQuit=None, onClimbChanged=None, onFightBoss=None):
        super().__init__()
        from arete.ui.dashboard import Dropdown, label

        self.mainStyle = mainStyle
        self.onMemoryCleared = onMemoryCleared
        self.onForceQuit = onForceQuit
        self.onClimbChanged = onClimbChanged
        self.onFightBoss = onFightBoss
        self.pendingRows = {}
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
        layout.addWidget(label("Changes start 1 hour after you save them, so they're never made on impulse.", "Streak"))
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

        # Debug tools for testing, these skip parental controls so take them out before release
        if isDebugMode():
            layout.addWidget(label("Debug", "Section"))
            layout.addWidget(label("Testing tools. These skip parental controls.", "Streak"))
            debugRow = QHBoxLayout()
            forceQuitButton = QPushButton("Force quit", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            forceQuitButton.clicked.connect(self.forceQuit)
            resetTimersButton = QPushButton("Reset lock timers", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            resetTimersButton.clicked.connect(self.resetLockTimers)
            clearMemoryButton = QPushButton("Clear all memory", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            clearMemoryButton.clicked.connect(self.clearAllMemory)
            debugRow.addWidget(forceQuitButton)
            debugRow.addWidget(resetTimersButton)
            debugRow.addWidget(clearMemoryButton)
            debugRow.addStretch()
            layout.addLayout(debugRow)
            blockingSwitch = QCheckBox("Blocking on", objectName="Switch", cursor=Qt.CursorShape.PointingHandCursor)
            blockingSwitch.setChecked(enforcement.blockingOn)
            blockingSwitch.toggled.connect(self.toggleBlocking)
            layout.addWidget(blockingSwitch)
            climbRow = QHBoxLayout()
            self.climbBox = QLineEdit()
            self.climbBox.returnPressed.connect(self.setClimb)
            setClimbButton = QPushButton("Set climb %", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            setClimbButton.clicked.connect(self.setClimb)
            fightButton = QPushButton("Fight boss now", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            fightButton.clicked.connect(self.fightBoss)
            climbRow.addWidget(self.climbBox)
            climbRow.addWidget(setClimbButton)
            climbRow.addWidget(fightButton)
            layout.addLayout(climbRow)
            self.updateClimbBox()
        layout.addStretch()

        self.updateParentSection()
        self.countdownTimer = QTimer(self, interval=1000, timeout=self.updateCountdowns)
        self.countdownTimer.start()

    def updateClimbBox(self):
        totalText = format(climbing.climbState()["totalPercent"], ".1f")
        self.climbBox.clear()
        self.climbBox.setPlaceholderText("Climb % across all 3 mountains (0 - 300), now " + totalText)

    def setClimb(self):
        try:
            totalPercent = float(self.climbBox.text().strip())
        except ValueError:
            return
        bossesBeaten = 0
        for bossPercent in mountains.bossPercents():
            if bossPercent < totalPercent:
                bossesBeaten = bossesBeaten + 1
        climbing.setClimbPercent(totalPercent, bossesBeaten)
        self.updateClimbBox()
        if self.onClimbChanged is not None:
            self.onClimbChanged()

    def fightBoss(self):
        if self.onFightBoss is not None:
            self.onFightBoss()

    def toggleBlocking(self, isOn):
        enforcement.blockingOn = isOn

    def updateParentSection(self):
        isSetUp = parent_pin.hasPin()
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


    # pending changes, countdown till it kicks in + cancel button
    def canEdit(self, settingName):
        return frozenSecondsLeft(settingName) == 0 and not setting_changes.isPending(settingName)

    def makePendingRow(self, settingName):
        from arete.ui.dashboard import label

        pendingRow = QWidget()
        rowLayout = QHBoxLayout(pendingRow)
        rowLayout.setContentsMargins(0, 0, 0, 0)
        pendingText = label("", "SliderHint")
        rowLayout.addWidget(pendingText, 1)
        cancelButton = QPushButton("Cancel change", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        cancelButton.clicked.connect(lambda checked=False: self.cancelChange(settingName))
        rowLayout.addWidget(cancelButton, alignment=Qt.AlignmentFlag.AlignVCenter)
        if isDebugMode():
            applyButton = QPushButton("Apply now", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            applyButton.clicked.connect(lambda checked=False: self.applyChangeNow(settingName))
            rowLayout.addWidget(applyButton, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.pendingRows[settingName] = (pendingRow, pendingText)
        return pendingRow

    def updatePendingRow(self, settingName):
        pendingRow, pendingText = self.pendingRows[settingName]
        pendingRow.setVisible(setting_changes.isPending(settingName))
        secondsLeft = setting_changes.pendingSecondsLeft(settingName)
        pendingText.setText("Saved. Your change starts in " + waitText(secondsLeft) + ".")

    def cancelChange(self, settingName):
        setting_changes.cancelChange(settingName)
        self.refreshEverything()

    def applyChangeNow(self, settingName):
        setting_changes.applyNow(settingName)
        self.refreshEverything()

    def updateCountdowns(self):
        self.updateBreakLabels()
        self.updateSchedule()

    # Absolute time limits, break count + break length sliders

    def makeBreakLimits(self):
        from arete.ui.dashboard import label

        breakLimits = QWidget()
        breakLayout = QVBoxLayout(breakLimits)
        breakLayout.setContentsMargins(16, 8, 16, 8)
        breakLayout.setSpacing(8)

        self.breakCountLabel = label("", "SliderLabel")
        self.breakCountSlider = QSlider(Qt.Orientation.Horizontal)
        self.breakCountSlider.setRange(enforcement.MIN_BREAKS, enforcement.MAX_BREAKS)
        self.breakCountSlider.valueChanged.connect(self.updateBreakLabels)

        self.breakLengthLabel = label("", "SliderLabel")
        self.breakLengthSlider = QSlider(Qt.Orientation.Horizontal)
        self.breakLengthSlider.setRange(enforcement.MIN_BREAK_MINUTES, enforcement.MAX_BREAK_MINUTES)
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
        breakLayout.addWidget(self.makePendingRow("Absolute Time Limits"))
        breakLayout.addLayout(saveRow)
        self.showBreakValues()
        return breakLimits

    def showBreakValues(self):
        self.breakCountSlider.setValue(setting_changes.upcomingValue("Absolute Time Limits", "maxBreaks", enforcement.getMaxBreaks()))
        self.breakLengthSlider.setValue(setting_changes.upcomingValue("Absolute Time Limits", "breakMinutes", enforcement.getBreakMinutes()))
        self.updateBreakLabels()

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
        canEdit = self.canEdit("Absolute Time Limits")
        self.breakCountSlider.setEnabled(canEdit)
        self.breakLengthSlider.setEnabled(canEdit)
        self.saveBreaksButton.setEnabled(canEdit)
        if secondsLeft > 0:
            hintText = hintText + " (" + frozenText(secondsLeft) + ")"
        self.breakTotalLabel.setText(hintText)
        self.updatePendingRow("Absolute Time Limits")

    def saveBreakLimits(self):
        newValues = {"maxBreaks": self.breakCountSlider.value(), "breakMinutes": self.breakLengthSlider.value()}
        setting_changes.queueChange("Absolute Time Limits", newValues)
        self.updateBreakLabels()

    def forceQuit(self):
        if self.onForceQuit is not None:
            self.onForceQuit()


    # shared helpers for building each section
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


    # schedule tab, study days + start/end
    def makeSchedule(self):
        from arete.ui.dashboard import label

        tab, tabLayout = self.makeTab()
        tabLayout.addWidget(label("Study days and hours. You can add more than one.", "SliderHint"))
        self.scheduleListBox = QWidget()
        self.scheduleListLayout = QVBoxLayout(self.scheduleListBox)
        self.scheduleListLayout.setContentsMargins(0, 0, 0, 0)
        self.scheduleListLayout.setSpacing(6)
        tabLayout.addWidget(self.scheduleListBox)
        dayRow = QHBoxLayout()
        self.dayBoxes = []
        for dayNumber in range(7):
            dayBox = QPushButton(DAY_NAMES[dayNumber], objectName="DayChip", cursor=Qt.CursorShape.PointingHandCursor)
            dayBox.setCheckable(True)
            self.dayBoxes.append(dayBox)
            dayRow.addWidget(dayBox)
        tabLayout.addLayout(dayRow)
        timeRow = QHBoxLayout()
        self.timeBoxStyle = QStyleFactory.create("Fusion")
        self.timeBoxStyle.setParent(self)
        self.startTimeBox = QTimeEdit()
        self.startTimeBox.setDisplayFormat("HH:mm")
        self.startTimeBox.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
        self.startTimeBox.setFrame(False)
        self.startTimeBox.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.startTimeBox.setStyle(self.timeBoxStyle)
        self.startTimeBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.startTimeBox.setFixedSize(64, 32)
        self.endTimeBox = QTimeEdit()
        self.endTimeBox.setDisplayFormat("HH:mm")
        self.endTimeBox.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
        self.endTimeBox.setFrame(False)
        self.endTimeBox.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.endTimeBox.setStyle(self.timeBoxStyle)
        self.endTimeBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.endTimeBox.setFixedSize(64, 32)
        timeRow.setSpacing(10)
        timeRow.addWidget(label("From", "SliderLabel"), alignment=Qt.AlignmentFlag.AlignVCenter)
        timeRow.addWidget(self.makeTimeChip(self.startTimeBox))
        timeRow.addWidget(label("to", "SliderLabel"), alignment=Qt.AlignmentFlag.AlignVCenter)
        timeRow.addWidget(self.makeTimeChip(self.endTimeBox))
        timeRow.addStretch()
        self.addScheduleButton = QPushButton("Add", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.addScheduleButton.clicked.connect(self.addSchedule)
        timeRow.addWidget(self.addScheduleButton)
        tabLayout.addLayout(timeRow)
        self.scheduleHint = label("", "SliderHint")
        tabLayout.addWidget(self.scheduleHint)
        self.scheduleError = QLabel("", objectName="ErrorText")
        self.scheduleError.hide()
        tabLayout.addWidget(self.scheduleError)
        tabLayout.addWidget(self.makePendingRow("Schedule Time Limits"))
        self.saveScheduleButton = QPushButton("Save", objectName="MainButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.saveScheduleButton.clicked.connect(self.saveSchedule)
        tabLayout.addLayout(self.makeSaveRow(self.saveScheduleButton))
        self.showScheduleValues()
        return tab

    def showScheduleValues(self):
        savedMemory = memory.load()
        schedules = savedMemory.get("studySchedules")
        if schedules is None and savedMemory.get("studySchedule", {}).get("days"):
            schedules = [savedMemory["studySchedule"]]
        if schedules is None:
            schedules = []
        self.schedules = list(setting_changes.upcomingValue("Schedule Time Limits", "studySchedules", schedules))
        for dayBox in self.dayBoxes:
            dayBox.setChecked(False)
        self.startTimeBox.setTime(QTime(16, 0))
        self.endTimeBox.setTime(QTime(18, 0))
        self.scheduleError.hide()
        self.showScheduleList()
        self.updateSchedule()

    def showScheduleList(self):
        from arete.ui.dashboard import label

        while self.scheduleListLayout.count() > 0:
            oldRow = self.scheduleListLayout.takeAt(0).widget()
            oldRow.hide()
            oldRow.deleteLater()
        self.removeButtons = []
        if len(self.schedules) == 0:
            self.scheduleListLayout.addWidget(label("No study times yet.", "SliderLabel"))
        for index in range(len(self.schedules)):
            schedule = self.schedules[index]
            row = QFrame(objectName="TimeChip")
            rowLayout = QHBoxLayout(row)
            rowLayout.setContentsMargins(12, 6, 6, 6)
            rowText = label(scheduleText(schedule), "SliderLabel")
            rowText.setWordWrap(False)
            rowLayout.addWidget(rowText)
            rowLayout.addStretch()
            removeButton = QPushButton("Remove", objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
            removeButton.setEnabled(self.canEdit("Schedule Time Limits"))
            self.removeButtons.append(removeButton)
            removeButton.clicked.connect(lambda checked=False, i=index: self.removeSchedule(i))
            rowLayout.addWidget(removeButton)
            self.scheduleListLayout.addWidget(row)

    def addSchedule(self):
        startText = self.startTimeBox.time().toString("HH:mm")
        endText = self.endTimeBox.time().toString("HH:mm")
        chosenDays = []
        for dayNumber in range(7):
            if self.dayBoxes[dayNumber].isChecked():
                chosenDays.append(dayNumber)
        if len(chosenDays) == 0:
            self.scheduleError.setText("Pick at least one day.")
            self.scheduleError.show()
            return
        if startText >= endText:
            self.scheduleError.setText("The end time has to be after the start time.")
            self.scheduleError.show()
            return
        self.scheduleError.hide()
        self.schedules.append({"days": chosenDays, "start": startText, "end": endText})
        for dayBox in self.dayBoxes:
            dayBox.setChecked(False)
        self.showScheduleList()

    def removeSchedule(self, index):
        self.schedules.pop(index)
        self.showScheduleList()

    def makeTimeChip(self, timeBox):
        timeChip = QFrame(objectName="TimeChip")
        chipLayout = QHBoxLayout(timeChip)
        chipLayout.setContentsMargins(8, 2, 8, 2)
        chipLayout.addWidget(timeBox)
        return timeChip

    def updateSchedule(self):
        secondsLeft = frozenSecondsLeft("Schedule Time Limits")
        canEdit = self.canEdit("Schedule Time Limits")
        for dayBox in self.dayBoxes:
            dayBox.setEnabled(canEdit)
        self.startTimeBox.setEnabled(canEdit)
        self.endTimeBox.setEnabled(canEdit)
        self.addScheduleButton.setEnabled(canEdit)
        self.saveScheduleButton.setEnabled(canEdit)
        hintText = ""
        if secondsLeft > 0:
            hintText = "Schedule " + frozenText(secondsLeft)
        self.scheduleHint.setText(hintText)
        self.scheduleHint.setVisible(hintText != "")
        self.updatePendingRow("Schedule Time Limits")
        for removeButton in self.removeButtons:
            removeButton.setEnabled(canEdit)

    def saveSchedule(self):
        self.scheduleError.hide()
        setting_changes.queueChange("Schedule Time Limits", {"studySchedules": self.schedules})
        self.updateSchedule()


    # AI tab, gemini key + all the sites its sorted so far
    def makeAiTab(self):
        from arete.ui.dashboard import label

        tab, tabLayout = self.makeTab()
        explanation = (
            "The AI only checks websites in your browser that aren't on Arete's built-in lists, "
            "after you've been on them for 1 minute. Each answer is remembered, so a site is only checked once."
        )
        tabLayout.addWidget(label(explanation, "SliderHint"))
        keyStatusRow = QHBoxLayout()
        self.keyText = label("", "ChipOn")
        self.keyText.setWordWrap(False)
        keyStatusRow.addWidget(self.keyText)
        keyStatusRow.addStretch()
        tabLayout.addLayout(keyStatusRow)
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
        self.aiSitesLabel = label("", "SitesList")
        self.aiSitesLabel.setTextFormat(Qt.TextFormat.RichText)
        tabLayout.addWidget(self.aiSitesLabel)
        self.updateKeySection()
        return tab

    def updateAiSites(self):
        self.aiCountLabel.setText(str(vision.aiChecksToday()) + " of " + str(vision.AI_CHECKS_PER_DAY) + " AI checks used today")
        sitesList = site_memory.rememberedSitesList()
        if len(sitesList) == 0:
            self.aiSitesLabel.setText("The AI hasn't sorted any websites yet.")
            return
        colors = getColors()
        siteRows = []
        for site, category in sitesList:
            dotColor = colors["green"]
            if category == "unproductive":
                dotColor = colors["error"]
            siteRows.append(
                "<tr><td width='16' style='color:" + dotColor + "; font-size:13px;'>●</td>"
                + "<td width='100%'>" + site + "</td>"
                + "<td align='right' style='color:" + colors["onSurfaceVariant"] + ";'>" + category + "</td></tr>"
            )
        self.aiSitesLabel.setText("<b>Sites the AI sorted</b><table width='100%' cellspacing='0' cellpadding='3'>" + "".join(siteRows) + "</table>")

    def updateKeySection(self):
        secondsLeft = frozenSecondsLeft("Gemini API key")
        self.keyBox.setEnabled(secondsLeft == 0)
        self.saveKeyButton.setEnabled(secondsLeft == 0)
        if vision.getApiKey() == "":
            keyStatus = "No key saved"
            self.keyText.setObjectName("ChipOff")
        else:
            keyStatus = "Key saved"
            self.keyText.setObjectName("ChipOn")
        if secondsLeft > 0:
            keyStatus = keyStatus + ", " + frozenText(secondsLeft)
        self.keyText.setText(keyStatus)
        self.keyText.style().unpolish(self.keyText)
        self.keyText.style().polish(self.keyText)
        self.updateAiSites()

    def saveKey(self):
        if self.keyBox.text().strip() == "":
            return
        vision.saveApiKey(self.keyBox.text())
        self.keyBox.clear()
        markChanged("Gemini API key")
        self.updateKeySection()

    # Debug buttons, reset lock timers + clear all memory

    def refreshEverything(self):
        self.showBreakValues()
        self.updateKeySection()
        self.showScheduleValues()
        self.updateParentSection()

    def resetLockTimers(self):
        savedMemory = memory.load()
        savedMemory["changedAt"] = {}
        memory.save(savedMemory)
        self.refreshEverything()

    def clearAllMemory(self):
        clearAnswer = QMessageBox.question(
            self,
            "Clear all memory",
            "This deletes all saved settings, the parent PIN, streaks, break counts, tracked times and website verdicts. "
            "The Gemini API key is kept. This can't be undone.",
        )
        if clearAnswer != QMessageBox.StandardButton.Yes:
            return
        memory.FILE.unlink(missing_ok=True)
        time_tracking.FILE.unlink(missing_ok=True)
        site_memory.FILE.unlink(missing_ok=True)
        site_memory.rememberedSites = None
        if self.onMemoryCleared is not None:
            self.onMemoryCleared()
        self.refreshEverything()


    # parental control buttons, needs pin after setup
    def setUpParentalControls(self):
        PinDialog(self, self.mainStyle, True).exec()
        self.updateParentSection()

    def changePin(self):
        if askForPin(self, self.mainStyle):
            PinDialog(self, self.mainStyle, True).exec()

    def turnOffParentalControls(self):
        if askForPin(self, self.mainStyle):
            parent_pin.removePin()
            saveLockedSettings([])
            self.updateParentSection()
