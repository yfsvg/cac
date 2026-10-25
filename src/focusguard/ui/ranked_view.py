from math import cos, pi, sin

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPolygonF
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from focusguard.core import ranked
from focusguard.ui import animations


class RankEmblem(QWidget):
    def __init__(self, size=44):
        super().__init__()
        self.setFixedSize(size, size)
        self.divisionNumber = 0

    def setDivision(self, divisionNumber):
        self.divisionNumber = divisionNumber
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        size = self.width()
        middle = size / 2
        color = QColor(ranked.rankColor(self.divisionNumber))
        tierNumber = min(self.divisionNumber // 3, len(ranked.TIERS))
        pointCount = 4 + tierNumber
        shape = QPolygonF()
        for pointNumber in range(pointCount * 2):
            radius = middle * 0.95
            if pointNumber % 2 == 1:
                radius = middle * 0.62
            angle = pi * pointNumber / pointCount - pi / 2
            shape.append(QPointF(middle + radius * cos(angle), middle + radius * sin(angle)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(shape)
        painter.setBrush(QColor(255, 255, 255, 200))
        divisionDots = self.divisionNumber % 3 + 1
        if self.divisionNumber >= ranked.totalRanks():
            divisionDots = 3
        for dotNumber in range(divisionDots):
            dotX = middle + (dotNumber - (divisionDots - 1) / 2) * size * 0.14
            painter.drawEllipse(QPointF(dotX, middle), size * 0.05, size * 0.05)


class RankCard(QFrame):
    def __init__(self, whenLeaderboard):
        super().__init__(objectName="RankCard")
        cardLayout = QHBoxLayout(self)
        cardLayout.setContentsMargins(20, 16, 20, 16)
        cardLayout.setSpacing(16)
        self.emblem = RankEmblem(56)
        cardLayout.addWidget(self.emblem)
        textColumn = QVBoxLayout()
        textColumn.setSpacing(4)
        self.rankLabel = QLabel("Spark I", objectName="RankName")
        self.pointsLabel = QLabel("", objectName="RankPoints")
        self.progressBar = QProgressBar(objectName="RankBar")
        self.progressBar.setTextVisible(False)
        self.progressBar.setFixedHeight(8)
        self.todayLabel = QLabel("", objectName="RankToday")
        textColumn.addWidget(self.rankLabel)
        textColumn.addWidget(self.pointsLabel)
        textColumn.addWidget(self.progressBar)
        textColumn.addWidget(self.todayLabel)
        cardLayout.addLayout(textColumn, 1)
        leaderboardButton = QPushButton("Leaderboard", objectName="RankButton", cursor=Qt.CursorShape.PointingHandCursor)
        leaderboardButton.clicked.connect(whenLeaderboard)
        cardLayout.addWidget(leaderboardButton, alignment=Qt.AlignmentFlag.AlignTop)
        self.shownPoints = -1

    def refresh(self, animate=True):
        rankedData = ranked.loadRanked()
        points = rankedData["points"]
        divisionNumber, pointsIn, cost = ranked.rankFromPoints(points)
        self.emblem.setDivision(divisionNumber)
        self.rankLabel.setText(ranked.rankName(divisionNumber))
        if cost == 0:
            self.pointsLabel.setText(str(round(points)) + " FP, top rank")
            self.progressBar.setRange(0, 1)
            self.progressBar.setValue(1)
        else:
            self.pointsLabel.setText(str(int(pointsIn)) + " / " + str(cost) + " FP to " + ranked.rankName(divisionNumber + 1))
            self.progressBar.setRange(0, cost)
            if animate and self.shownPoints != round(points):
                startValue = self.progressBar.value()
                animations.animateValue(startValue, pointsIn, lambda value: self.progressBar.setValue(int(value)))
            else:
                self.progressBar.setValue(int(pointsIn))
        todayText = "+" + str(round(rankedData["gainedToday"])) + " FP today"
        if rankedData["lostToday"] > 0:
            todayText = todayText + ", -" + str(round(rankedData["lostToday"]))
        if ranked.hasShield(rankedData):
            todayText = todayText + "   🛡 Shield until " + rankedData["shieldUntil"][5:]
        self.todayLabel.setText(todayText)
        self.shownPoints = round(points)


class LeaderboardRow(QFrame):
    def __init__(self):
        super().__init__(objectName="BoardRow")
        rowLayout = QHBoxLayout(self)
        rowLayout.setContentsMargins(12, 6, 12, 6)
        rowLayout.setSpacing(10)
        self.positionLabel = QLabel("", objectName="BoardPosition")
        self.positionLabel.setFixedWidth(34)
        self.emblem = RankEmblem(22)
        self.nameLabel = QLabel("", objectName="BoardName")
        self.rankLabel = QLabel("", objectName="BoardRank")
        self.pointsLabel = QLabel("", objectName="BoardPoints")
        rowLayout.addWidget(self.positionLabel)
        rowLayout.addWidget(self.emblem)
        rowLayout.addWidget(self.nameLabel, 1)
        rowLayout.addWidget(self.rankLabel)
        rowLayout.addWidget(self.pointsLabel)

    def setRow(self, position, name, points, isPlayer):
        divisionNumber = ranked.rankFromPoints(points)[0]
        self.positionLabel.setText("#" + str(position))
        self.emblem.setDivision(divisionNumber)
        self.nameLabel.setText(name)
        self.rankLabel.setText(ranked.rankName(divisionNumber))
        self.pointsLabel.setText(str(int(points)) + " FP")
        objectName = "BoardRow"
        if isPlayer:
            objectName = "BoardRowPlayer"
        if self.objectName() != objectName:
            self.setObjectName(objectName)
            self.style().unpolish(self)
            self.style().polish(self)


class LeaderboardPage(QWidget):
    def __init__(self, whenBack, backIcon):
        super().__init__()
        pageLayout = QVBoxLayout(self)
        pageLayout.setContentsMargins(20, 10, 20, 20)
        pageLayout.setSpacing(10)
        topRow = QHBoxLayout()
        backButton = QPushButton(objectName="ThemeButton", cursor=Qt.CursorShape.PointingHandCursor)
        backButton.setFixedSize(32, 32)
        backButton.setIcon(backIcon)
        backButton.clicked.connect(whenBack)
        topRow.addWidget(backButton)
        topRow.addWidget(QLabel("Leaderboard", objectName="AppName"))
        topRow.addStretch()
        pageLayout.addLayout(topRow)
        pageLayout.addWidget(QLabel("Climb past other students by staying focused. Rankings update every day.", objectName="RankToday"))
        scrollArea = QScrollArea(widgetResizable=True)
        scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        listWidget = QWidget(objectName="Content")
        scrollArea.setWidget(listWidget)
        self.listLayout = QVBoxLayout(listWidget)
        self.listLayout.setContentsMargins(0, 0, 0, 0)
        self.listLayout.setSpacing(6)
        pageLayout.addWidget(scrollArea)
        self.rows = []
        self.gapLabel = QLabel("· · ·", objectName="RankToday", alignment=Qt.AlignmentFlag.AlignCenter)

    def refresh(self):
        board = ranked.leaderboard()
        playerPosition = 1
        for position, name, points, isPlayer in board:
            if isPlayer:
                playerPosition = position
        shownRows = []
        for entry in board:
            position = entry[0]
            if position <= 10 or abs(position - playerPosition) <= 5:
                shownRows.append(entry)
        while self.listLayout.count() > 0:
            self.listLayout.takeAt(0)
        while len(self.rows) < len(shownRows):
            self.rows.append(LeaderboardRow())
        lastPosition = 0
        for rowNumber in range(len(self.rows)):
            row = self.rows[rowNumber]
            if rowNumber >= len(shownRows):
                row.hide()
                continue
            position, name, points, isPlayer = shownRows[rowNumber]
            if position > lastPosition + 1 and lastPosition > 0:
                self.listLayout.addWidget(self.gapLabel)
            row.setRow(position, name, points, isPlayer)
            row.show()
            self.listLayout.addWidget(row)
            lastPosition = position
        self.listLayout.addStretch()
        visibleRows = []
        for rowNumber in range(len(shownRows)):
            visibleRows.append(self.rows[rowNumber])
        animations.staggerIn(visibleRows, 25, 260)
