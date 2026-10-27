# Settings page, swaps in where the dashboard normally is. Split into five segments:
# 1. Small helpers (back arrow, "locked for 2d 3h" text, schedule text)
# 2. Building the page (app config card + debug card)
# 3. Saved changes waiting to kick in (the 1 hour wait + cancel button)
# 4. The three dropdowns: Absolute Time Limits, Schedule Time Limits, AI Categorizations
# 5. Debug buttons + refreshing everything
#
# Every change waits 1 hour before it starts so its never made on impulse,
# then that setting stays locked for 3 days


from PySide6.QtCore import QPointF, QSize, Qt, QTime, QTimer
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStyleFactory,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from arete.ai import site_memory, vision
from arete.core import climbing, enforcement, mountains, setting_changes
from arete.core.debug_mode import isDebugMode, turnOffForSession
from arete.core.setting_changes import frozenSecondsLeft, markChanged
from arete.storage import memory, time_tracking
from arete.ui import animations
from arete.ui.theme import applyTheme, getColors


SETTINGS_STYLE = """
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
    QPushButton#MainButton:hover { background-color: @primaryShadow; }
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

SETTING_NAMES = ["Absolute Time Limits", "Schedule Time Limits", "AI Categorizations"]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


















# Helpers, the back arrow (map page uses it too)

def makeBackArrow():
    arrowPicture = QPixmap(32, 32)
    arrowPicture.fill(Qt.GlobalColor.transparent)
    painter = QPainter(arrowPicture)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    arrowPen = QPen(QColor(getColors()["onSurface"]), 2.4)
    arrowPen.setCapStyle(Qt.PenCapStyle.RoundCap)
    arrowPen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(arrowPen)
    painter.drawLine(QPointF(9, 16), QPointF(23, 16))
    painter.drawLine(QPointF(9, 16), QPointF(15, 10))
    painter.drawLine(QPointF(9, 16), QPointF(15, 22))
    painter.end()
    return QIcon(arrowPicture)


# Helpers, text

# seconds -> "locked for 2d 23h" / "locked for 5h 12m"
def lockedForText(secondsLeft):
    if secondsLeft // 86400 > 0:
        return "locked for " + str(secondsLeft // 86400) + "d " + str((secondsLeft % 86400) // 3600) + "h"
    return "locked for " + str((secondsLeft % 86400) // 3600) + "h " + str((secondsLeft % 3600) // 60) + "m"


# seconds -> "45m", or "8m 30s" once its under 10 minutes
def waitTimeText(secondsLeft):
    if secondsLeft // 60 >= 10:
        return str(secondsLeft // 60) + "m"
    return str(secondsLeft // 60) + "m " + str(secondsLeft % 60) + "s"


# {"days": [0, 2], "start": "16:00", "end": "18:00"} -> "Mon, Wed  16:00 to 18:00"
def studyTimeText(studyTime):
    if len(studyTime["days"]) == 7:
        return "Every day" + "  " + studyTime["start"] + " to " + studyTime["end"]
    return ", ".join([DAY_NAMES[dayNumber] for dayNumber in studyTime["days"]]) + "  " + studyTime["start"] + " to " + studyTime["end"]


# Helpers, swaps a dropdown's empty placeholder for the real controls

def replaceDropdownBody(dropdown, newBody):
    dropdown.layout().removeWidget(dropdown.body)
    dropdown.body.deleteLater()
    dropdown.body = newBody
    newBody.hide()
    dropdown.layout().addWidget(newBody)






# Settings page

class SettingsPage(QWidget):
    def __init__(self, mainStyle, goBack, onMemoryCleared=None, onForceQuit=None, onClimbChanged=None, onFightBoss=None):
        super().__init__()
        from arete.ui.dashboard import Dropdown, label, stopSideScrolling

        # what the dashboard wants to hear about
        self.mainStyle = mainStyle
        self.onMemoryCleared = onMemoryCleared
        self.onForceQuit = onForceQuit
        self.onClimbChanged = onClimbChanged
        self.onFightBoss = onFightBoss
        self.goBack = goBack
        self.pendingRows = {}
        self.setStyleSheet(applyTheme(SETTINGS_STYLE))

        # everything scrolls, sideways scrolling turned off
        scrollArea = QScrollArea(widgetResizable=True)
        stopSideScrolling(scrollArea)
        scrollContent = QWidget(objectName="Content")
        scrollArea.setWidget(scrollContent)
        pageLayout = QVBoxLayout(self)
        pageLayout.setContentsMargins(0, 0, 0, 0)
        pageLayout.addWidget(scrollArea)
        layout = QVBoxLayout(scrollContent)
        layout.setContentsMargins(20, 10, 20, 20)
        layout.setSpacing(12)



        # top row, back arrow + "Settings"
        topRow = QHBoxLayout()
        self.backButton = QPushButton(objectName="ThemeButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.backButton.setFixedSize(32, 32)
        self.backButton.setIcon(makeBackArrow())
        self.backButton.setIconSize(QSize(32, 32))
        self.backButton.clicked.connect(goBack)
        topRow.setSpacing(10)
        topRow.addWidget(self.backButton, alignment=Qt.AlignmentFlag.AlignVCenter)
        settingsTitle = label("Settings", "AppName")
        settingsTitle.setWordWrap(False)
        topRow.addWidget(settingsTitle, alignment=Qt.AlignmentFlag.AlignVCenter)
        topRow.addStretch()
        layout.addLayout(topRow)
        layout.addSpacing(4)



        # app config card, one dropdown per setting
        layout.addWidget(label("App Config", "Section"))
        configCard, configCardLayout = self.makeSectionCard()
        configCardLayout.addWidget(label("Changes start 1 hour after you save them, so they're never made on impulse.", "Streak"))
        for settingName in SETTING_NAMES:
            settingDropdown = Dropdown(settingName)
            if settingName == "Absolute Time Limits":
                replaceDropdownBody(settingDropdown, self.makeBreakLimits())
            if settingName == "Schedule Time Limits":
                replaceDropdownBody(settingDropdown, self.makeSchedule())
            if settingName == "AI Categorizations":
                replaceDropdownBody(settingDropdown, self.makeAiTab())
            configCardLayout.addWidget(settingDropdown)
        layout.addWidget(configCard)
        layout.addSpacing(8)



        # debug card, testing tools only, take them out before release
        if isDebugMode():
            layout.addWidget(label("Debug", "Section"))
            debugCard, debugCardLayout = self.makeSectionCard()
            debugCardLayout.addWidget(label("Testing tools.", "Streak"))

            debugButtonRow = QHBoxLayout()
            debugButtonRow.addWidget(self.makeSmallButton("Force quit", self.forceQuit))
            debugButtonRow.addWidget(self.makeSmallButton("Reset lock timers", self.resetLockTimers))
            debugButtonRow.addWidget(self.makeSmallButton("Clear all memory", self.clearAllMemory))
            debugButtonRow.addStretch()
            debugCardLayout.addLayout(debugButtonRow)
            debugCardLayout.addWidget(self.makeSmallButton("Turn off debug until restart", self.turnOffDebug), alignment=Qt.AlignmentFlag.AlignLeft)

            blockingSwitch = QCheckBox("Blocking on", objectName="Switch", cursor=Qt.CursorShape.PointingHandCursor)
            blockingSwitch.setChecked(enforcement.blockingOn)
            blockingSwitch.toggled.connect(self.toggleBlocking)
            debugCardLayout.addWidget(blockingSwitch)

            # type a % on the mountain ur on, or skip the boss
            climbRow = QHBoxLayout()
            self.climbBox = QLineEdit()
            self.climbBox.returnPressed.connect(self.setClimb)
            climbRow.addWidget(self.climbBox)
            climbRow.addWidget(self.makeSmallButton("Set climb %", self.setClimb))
            climbRow.addWidget(self.makeSmallButton("Beat boss now", self.fightBoss))
            debugCardLayout.addLayout(climbRow)
            layout.addWidget(debugCard)
            self.updateClimbBox()
        layout.addStretch()



        # cards fade in one after another, countdowns tick every second
        animations.staggerIn([configCard, debugCard] if isDebugMode() else [configCard], 70, 320)
        self.countdownTimer = QTimer(self, interval=1000, timeout=self.updateCountdowns)
        self.countdownTimer.start()




    # Building pieces, used all over the page

    def makeSectionCard(self):
        sectionCard = QFrame(objectName="TimeCard")
        sectionCardLayout = QVBoxLayout(sectionCard)
        sectionCardLayout.setContentsMargins(16, 14, 16, 16)
        sectionCardLayout.setSpacing(10)
        return sectionCard, sectionCardLayout

    # inside of a dropdown
    def makeTab(self):
        dropdownBody = QWidget()
        dropdownBodyLayout = QVBoxLayout(dropdownBody)
        dropdownBodyLayout.setContentsMargins(16, 8, 16, 8)
        dropdownBodyLayout.setSpacing(8)
        return dropdownBody, dropdownBodyLayout

    # light secondary button, "PinButton" is just the name of the style
    def makeSmallButton(self, buttonText, whenClicked):
        smallButton = QPushButton(buttonText, objectName="PinButton", cursor=Qt.CursorShape.PointingHandCursor)
        smallButton.clicked.connect(whenClicked)
        return smallButton

    # save button pushed over to the right
    def makeSaveRow(self, saveButton):
        saveRow = QHBoxLayout()
        saveRow.addStretch()
        saveRow.addWidget(saveButton)
        return saveRow

    def restyle(self):
        self.setStyleSheet(applyTheme(SETTINGS_STYLE))
        self.backButton.setIcon(makeBackArrow())




    # Saved changes, the 1 hour wait before they start + a cancel button

    # cant edit while its locked or while a change is already waiting
    def canEdit(self, settingName):
        return frozenSecondsLeft(settingName) == 0 and not setting_changes.isPending(settingName)

    def makePendingRow(self, settingName):
        from arete.ui.dashboard import label

        pendingRow = QWidget()
        pendingRowLayout = QHBoxLayout(pendingRow)
        pendingRowLayout.setContentsMargins(0, 0, 0, 0)
        pendingText = label("", "SliderHint")
        pendingRowLayout.addWidget(pendingText, 1)
        pendingRowLayout.addWidget(self.makeSmallButton("Cancel change", lambda checked=False: self.cancelChange(settingName)), alignment=Qt.AlignmentFlag.AlignVCenter)
        # debug can skip the wait
        if isDebugMode():
            pendingRowLayout.addWidget(self.makeSmallButton("Apply now", lambda checked=False: self.applyChangeNow(settingName)), alignment=Qt.AlignmentFlag.AlignVCenter)
        self.pendingRows[settingName] = (pendingRow, pendingText)
        return pendingRow

    def updatePendingRow(self, settingName):
        pendingRow, pendingText = self.pendingRows[settingName]
        pendingRow.setVisible(setting_changes.isPending(settingName))
        pendingText.setText("Saved. Your change starts in " + waitTimeText(setting_changes.pendingSecondsLeft(settingName)) + ".")

    def cancelChange(self, settingName):
        setting_changes.cancelChange(settingName)
        self.refreshEverything()

    def applyChangeNow(self, settingName):
        setting_changes.applyNow(settingName)
        self.refreshEverything()

    # every second, so the "starts in" + "locked for" times stay right
    def updateCountdowns(self):
        self.updateBreakLabels()
        self.updateSchedule()




    # Absolute Time Limits, how many breaks a day + how long each one is

    def makeBreakLimits(self):
        from arete.ui.dashboard import label

        breakLimits = QWidget()
        breakLimitsLayout = QVBoxLayout(breakLimits)
        breakLimitsLayout.setContentsMargins(16, 8, 16, 8)
        breakLimitsLayout.setSpacing(8)

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

        breakLimitsLayout.addWidget(self.breakCountLabel)
        breakLimitsLayout.addWidget(self.breakCountSlider)
        breakLimitsLayout.addSpacing(4)
        breakLimitsLayout.addWidget(self.breakLengthLabel)
        breakLimitsLayout.addWidget(self.breakLengthSlider)
        breakLimitsLayout.addWidget(self.breakTotalLabel)
        breakLimitsLayout.addWidget(self.makePendingRow("Absolute Time Limits"))
        breakLimitsLayout.addLayout(self.makeSaveRow(self.saveBreaksButton))
        self.showBreakValues()
        return breakLimits

    # sliders show the waiting change if there is one, otherwise whats saved
    def showBreakValues(self):
        self.breakCountSlider.setValue(setting_changes.upcomingValue("Absolute Time Limits", "maxBreaks", enforcement.getMaxBreaks()))
        self.breakLengthSlider.setValue(setting_changes.upcomingValue("Absolute Time Limits", "breakMinutes", enforcement.getBreakMinutes()))
        self.updateBreakLabels()

    def updateBreakLabels(self):
        self.breakCountLabel.setText("Break periods per day: <b>" + str(self.breakCountSlider.value()) + "</b>")
        self.breakLengthLabel.setText("Break length: <b>" + str(self.breakLengthSlider.value()) + " minutes</b>")

        # "Up to 1h 30m of breaks a day..."
        totalBreakMinutes = self.breakCountSlider.value() * self.breakLengthSlider.value()
        totalBreakText = str(totalBreakMinutes) + " minutes"
        if totalBreakMinutes >= 60:
            totalBreakText = str(totalBreakMinutes // 60) + "h " + str(totalBreakMinutes % 60) + "m"
        hintText = "Up to " + totalBreakText + " of breaks a day. After that, unproductive apps close for the rest of the day."

        breaksLockedSeconds = frozenSecondsLeft("Absolute Time Limits")
        canEditBreaks = self.canEdit("Absolute Time Limits")
        self.breakCountSlider.setEnabled(canEditBreaks)
        self.breakLengthSlider.setEnabled(canEditBreaks)
        self.saveBreaksButton.setEnabled(canEditBreaks)
        if breaksLockedSeconds > 0:
            hintText = hintText + " (" + lockedForText(breaksLockedSeconds) + ")"
        self.breakTotalLabel.setText(hintText)
        self.updatePendingRow("Absolute Time Limits")

    def saveBreakLimits(self):
        setting_changes.queueChange("Absolute Time Limits", {"maxBreaks": self.breakCountSlider.value(), "breakMinutes": self.breakLengthSlider.value()})
        self.updateBreakLabels()




    # Schedule Time Limits, study days + hours, can have more than one

    def makeSchedule(self):
        from arete.ui.dashboard import label

        scheduleTab, scheduleTabLayout = self.makeTab()
        scheduleTabLayout.addWidget(label("Study days and hours. You can add more than one.", "SliderHint"))

        # list of saved study times, filled in by showScheduleList
        self.scheduleListBox = QWidget()
        self.scheduleListLayout = QVBoxLayout(self.scheduleListBox)
        self.scheduleListLayout.setContentsMargins(0, 0, 0, 0)
        self.scheduleListLayout.setSpacing(6)
        scheduleTabLayout.addWidget(self.scheduleListBox)



        # day chips, Mon - Sun
        dayRow = QHBoxLayout()
        self.dayBoxes = []
        for dayNumber in range(7):
            dayChip = QPushButton(DAY_NAMES[dayNumber], objectName="DayChip", cursor=Qt.CursorShape.PointingHandCursor)
            dayChip.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            dayChip.setMinimumWidth(36)
            dayChip.setCheckable(True)
            self.dayBoxes.append(dayChip)
            dayRow.addWidget(dayChip)
        scheduleTabLayout.addLayout(dayRow)



        # From [16:00] to [18:00]   Add
        timeRow = QHBoxLayout()
        # fusion style so the time boxes look the same on mac + windows
        self.timeBoxStyle = QStyleFactory.create("Fusion")
        self.timeBoxStyle.setParent(self)
        self.startTimeBox = self.makeTimeBox()
        self.endTimeBox = self.makeTimeBox()
        timeRow.setSpacing(10)
        timeRow.addWidget(label("From", "SliderLabel"), alignment=Qt.AlignmentFlag.AlignVCenter)
        timeRow.addWidget(self.makeTimeChip(self.startTimeBox))
        timeRow.addWidget(label("to", "SliderLabel"), alignment=Qt.AlignmentFlag.AlignVCenter)
        timeRow.addWidget(self.makeTimeChip(self.endTimeBox))
        timeRow.addStretch()
        self.addScheduleButton = self.makeSmallButton("Add", self.addSchedule)
        timeRow.addWidget(self.addScheduleButton)
        scheduleTabLayout.addLayout(timeRow)



        # locked hint, error line, waiting change, save
        self.scheduleHint = label("", "SliderHint")
        scheduleTabLayout.addWidget(self.scheduleHint)
        self.scheduleError = QLabel("", objectName="ErrorText")
        self.scheduleError.hide()
        scheduleTabLayout.addWidget(self.scheduleError)
        scheduleTabLayout.addWidget(self.makePendingRow("Schedule Time Limits"))
        self.saveScheduleButton = QPushButton("Save", objectName="MainButton", cursor=Qt.CursorShape.PointingHandCursor)
        self.saveScheduleButton.clicked.connect(self.saveSchedule)
        scheduleTabLayout.addLayout(self.makeSaveRow(self.saveScheduleButton))
        self.showScheduleValues()
        return scheduleTab

    # HH:mm box with no arrows or focus ring
    def makeTimeBox(self):
        timeBox = QTimeEdit()
        timeBox.setDisplayFormat("HH:mm")
        timeBox.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
        timeBox.setFrame(False)
        timeBox.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        timeBox.setStyle(self.timeBoxStyle)
        timeBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timeBox.setFixedSize(64, 32)
        return timeBox

    # rounded box around a time box
    def makeTimeChip(self, timeBox):
        timeChip = QFrame(objectName="TimeChip")
        timeChipLayout = QHBoxLayout(timeChip)
        timeChipLayout.setContentsMargins(8, 2, 8, 2)
        timeChipLayout.addWidget(timeBox)
        return timeChip

    # loads the study times (old saves only had one, so that gets turned into a list) + resets the pickers
    def showScheduleValues(self):
        savedMemory = memory.load()
        savedStudyTimes = savedMemory.get("studySchedules")
        if savedStudyTimes is None and savedMemory.get("studySchedule", {}).get("days"):
            savedStudyTimes = [savedMemory["studySchedule"]]
        if savedStudyTimes is None:
            savedStudyTimes = []
        self.schedules = list(setting_changes.upcomingValue("Schedule Time Limits", "studySchedules", savedStudyTimes))
        for dayChip in self.dayBoxes:
            dayChip.setChecked(False)
        self.startTimeBox.setTime(QTime(16, 0))
        self.endTimeBox.setTime(QTime(18, 0))
        self.scheduleError.hide()
        self.showScheduleList()
        self.updateSchedule()

    # one row per study time with a remove button
    def showScheduleList(self):
        from arete.ui.dashboard import label

        while self.scheduleListLayout.count() > 0:
            oldRow = self.scheduleListLayout.takeAt(0).widget()
            oldRow.hide()
            oldRow.deleteLater()
        self.removeButtons = []
        if len(self.schedules) == 0:
            self.scheduleListLayout.addWidget(label("No study times yet.", "SliderLabel"))

        for studyTimeNumber in range(len(self.schedules)):
            studyTimeRow = QFrame(objectName="TimeChip")
            studyTimeRowLayout = QHBoxLayout(studyTimeRow)
            studyTimeRowLayout.setContentsMargins(12, 6, 6, 6)
            studyTimeLabel = label(studyTimeText(self.schedules[studyTimeNumber]), "SliderLabel")
            studyTimeLabel.setWordWrap(False)
            studyTimeRowLayout.addWidget(studyTimeLabel)
            studyTimeRowLayout.addStretch()
            removeButton = self.makeSmallButton("Remove", lambda checked=False, numberToRemove=studyTimeNumber: self.removeSchedule(numberToRemove))
            removeButton.setEnabled(self.canEdit("Schedule Time Limits"))
            self.removeButtons.append(removeButton)
            studyTimeRowLayout.addWidget(removeButton)
            self.scheduleListLayout.addWidget(studyTimeRow)

    # needs at least one day + an end after the start
    def addSchedule(self):
        chosenDays = [dayNumber for dayNumber in range(7) if self.dayBoxes[dayNumber].isChecked()]
        if len(chosenDays) == 0:
            self.scheduleError.setText("Pick at least one day.")
            self.scheduleError.show()
            return
        if self.startTimeBox.time().toString("HH:mm") >= self.endTimeBox.time().toString("HH:mm"):
            self.scheduleError.setText("The end time has to be after the start time.")
            self.scheduleError.show()
            return
        self.scheduleError.hide()
        self.schedules.append({"days": chosenDays, "start": self.startTimeBox.time().toString("HH:mm"), "end": self.endTimeBox.time().toString("HH:mm")})
        for dayChip in self.dayBoxes:
            dayChip.setChecked(False)
        self.showScheduleList()

    def removeSchedule(self, studyTimeNumber):
        self.schedules.pop(studyTimeNumber)
        self.showScheduleList()

    # turns everything off while its locked or waiting
    def updateSchedule(self):



        scheduleLockedSeconds = frozenSecondsLeft("Schedule Time Limits")
        canEditSchedule = self.canEdit("Schedule Time Limits")
        for dayChip in self.dayBoxes:
            dayChip.setEnabled(canEditSchedule)
        self.startTimeBox.setEnabled(canEditSchedule)
        self.endTimeBox.setEnabled(canEditSchedule)
        self.addScheduleButton.setEnabled(canEditSchedule)
        self.saveScheduleButton.setEnabled(canEditSchedule)
        self.scheduleHint.setText("Schedule " + lockedForText(scheduleLockedSeconds) if scheduleLockedSeconds > 0 else "")
        self.scheduleHint.setVisible(self.scheduleHint.text() != "")
        self.updatePendingRow("Schedule Time Limits")
        for removeButton in self.removeButtons:
            removeButton.setEnabled(canEditSchedule)

    def saveSchedule(self):
        self.scheduleError.hide()
        setting_changes.queueChange("Schedule Time Limits", {"studySchedules": self.schedules})
        self.updateSchedule()











    # AI Categorizations, gemini key + every site its sorted so far

    def makeAiTab(self):
        from arete.ui.dashboard import label

        aiTab, aiTabLayout = self.makeTab()
        aiTabLayout.addWidget(label(
            "The AI only checks websites in your browser that aren't on Arete's built-in lists, "
            "after you've been on them for 10 seconds. It only reads the site's public homepage (its description, "
            "then a little of its text if needed), never your screen or the page you're on. "
            "Each answer is remembered, so a site is only checked once.",
            "SliderHint",
        ))

        # "Key saved" / "No key saved" chip
        keyStatusRow = QHBoxLayout()
        self.keyText = label("", "ChipOn")
        self.keyText.setWordWrap(False)
        keyStatusRow.addWidget(self.keyText)
        keyStatusRow.addStretch()
        aiTabLayout.addLayout(keyStatusRow)

        # key box, dots instead of letters
        keyRow = QHBoxLayout()
        self.keyBox = QLineEdit()
        self.keyBox.setEchoMode(QLineEdit.EchoMode.Password)
        self.keyBox.setPlaceholderText("Gemini API key")
        self.saveKeyButton = self.makeSmallButton("Save key", self.saveKey)
        keyRow.addWidget(self.keyBox)
        keyRow.addWidget(self.saveKeyButton)
        aiTabLayout.addLayout(keyRow)

        # checks used today + the sorted sites table
        self.aiCountLabel = label("", "SliderHint")
        aiTabLayout.addWidget(self.aiCountLabel)
        self.aiSitesLabel = label("", "SitesList")
        self.aiSitesLabel.setTextFormat(Qt.TextFormat.RichText)
        aiTabLayout.addWidget(self.aiSitesLabel)
        self.updateKeySection()
        return aiTab

    # green dot productive, red dot unproductive
    def updateAiSites(self):
        self.aiCountLabel.setText(str(vision.aiChecksToday()) + " of " + str(vision.AI_CHECKS_PER_DAY) + " AI checks used today")
        sortedSites = site_memory.rememberedSitesList()
        if len(sortedSites) == 0:
            self.aiSitesLabel.setText("The AI hasn't sorted any websites yet.")
            return
        themeColors = getColors()
        siteTableRows = []
        for site, category in sortedSites:
            siteTableRows.append(
                "<tr><td width='16' style='color:" + (themeColors["error"] if category == "unproductive" else themeColors["green"]) + "; font-size:13px;'>●</td>"
                + "<td width='100%'>" + site + "</td>"
                + "<td align='right' style='color:" + themeColors["onSurfaceVariant"] + ";'>" + category + "</td></tr>"
            )
            # Nice one japmann go fuh you sel! :joy_cat:
        self.aiSitesLabel.setText("<b>Sites the AI sorted</b><table width='100%' cellspacing='0' cellpadding='3'>" + "".join(siteTableRows) + "</table>")

    def updateKeySection(self):
        keyLockedSeconds = frozenSecondsLeft("Gemini API key")
        self.keyBox.setEnabled(keyLockedSeconds == 0)
        self.saveKeyButton.setEnabled(keyLockedSeconds == 0)
        if vision.getApiKey() == "":
            keyStatusText = "No key saved"
            self.keyText.setObjectName("ChipOff")
        else:
            keyStatusText = "Key saved"
            self.keyText.setObjectName("ChipOn")
        if keyLockedSeconds > 0:
            keyStatusText = keyStatusText + ", " + lockedForText(keyLockedSeconds)
        self.keyText.setText(keyStatusText)
        # chip colour changes with its name, so qt has to look at the style again
        self.keyText.style().unpolish(self.keyText)
        self.keyText.style().polish(self.keyText)
        self.updateAiSites()

    # the key works straight away, but then stays locked for 3 days like everything else
    def saveKey(self):
        if self.keyBox.text().strip() == "":
            return
        vision.saveApiKey(self.keyBox.text())
        self.keyBox.clear()
        markChanged("Gemini API key")
        self.updateKeySection()




    # Debug, climb box + boss skip

    def updateClimbBox(self):
        climbState = climbing.climbState()
        self.climbBox.clear()
        self.climbBox.setPlaceholderText("Climb % on " + mountains.MOUNTAINS[climbState["mountainNumber"]]["shortName"] + " (0 - 100), now " + format(climbState["percent"], ".1f"))

    # % is on the mountain ur on now (kept between 0 and 100), so earlier mountains stay finished.
    # any bosses on this mountain below the new % count as beaten
    def setClimb(self):
        try:
            mountainPercent = min(max(float(self.climbBox.text().strip()), 0), 100)
        except ValueError:
            return
        mountainNumber = climbing.climbState()["mountainNumber"]
        totalPercent = mountainNumber * 100 + mountainPercent
        bossesBeaten = mountainNumber * len(mountains.BOSS_CHECKPOINTS)
        for bossPercent in mountains.bossPercents():
            if bossPercent > mountainNumber * 100 and bossPercent < totalPercent:
                bossesBeaten = bossesBeaten + 1
        climbing.setClimbPercent(totalPercent, bossesBeaten)
        self.updateClimbBox()
        if self.onClimbChanged is not None:
            self.onClimbChanged()

    def fightBoss(self):
        if self.onFightBoss is not None:
            self.onFightBoss()




    # Debug, the buttons along the top of the card

    def forceQuit(self):
        if self.onForceQuit is not None:
            self.onForceQuit()

    def toggleBlocking(self, isOn):
        enforcement.blockingOn = isOn

    # hides every debug tool until arete restarts, blocking goes back on since its switch goes away too
    def turnOffDebug(self):
        turnOffForSession()
        enforcement.blockingOn = True
        self.goBack()

    # unlocks every setting straight away
    def resetLockTimers(self):
        savedMemory = memory.load()
        savedMemory["changedAt"] = {}
        memory.save(savedMemory)
        self.refreshEverything()

    # wipes memory, tracked times + site verdicts (keeps the api key since its in its own file)
    def clearAllMemory(self):
        if QMessageBox.question(
            self,
            "Clear all memory",
            "This deletes all saved settings, streaks, break counts, tracked times and website verdicts. "
            "The Gemini API key is kept. This can't be undone.",
        ) != QMessageBox.StandardButton.Yes:
            return
        memory.FILE.unlink(missing_ok=True)
        time_tracking.FILE.unlink(missing_ok=True)
        site_memory.FILE.unlink(missing_ok=True)
        site_memory.rememberedSites = None
        if self.onMemoryCleared is not None:
            self.onMemoryCleared()
        self.refreshEverything()

    # reloads all three dropdowns from whats saved
    def refreshEverything(self):
        self.showBreakValues()
        self.updateKeySection()
        self.showScheduleValues()
