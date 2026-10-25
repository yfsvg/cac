import random
import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

TILE_COLORS = ["#E5534B", "#3D8BFD", "#2FB36D", "#F2B33D", "#9B6BF2", "#F07AB0", "#24B5C9", "#F08A3C"]
COLOR_NAMES = [("Red", "#E5534B"), ("Blue", "#3D8BFD"), ("Green", "#2FB36D"), ("Yellow", "#E6A817")]

WORDS = {
    "short": ["focus", "study", "climb", "brain", "learn", "notes", "quiet", "smart", "skill", "goals", "ridge", "peaks"],
    "medium": ["planet", "summit", "lesson", "puzzle", "school", "growth", "number", "rocket", "steady", "glacier"],
    "long": ["mountain", "practice", "homework", "progress", "patience", "schedule", "absolute", "discover", "strength"],
}


def tileStyle(color, textColor="white"):
    return f"QPushButton {{ background-color: {color}; color: {textColor}; border: none; border-radius: 12px; font-size: 20px; font-weight: 700; text-align: center; padding: 0; }}"


class BrainGame(QWidget):
    title = ""
    hint = ""

    def __init__(self, difficulty, whenDone):
        super().__init__()
        self.difficulty = difficulty
        self.whenDone = whenDone
        self.finished = False
        self.endTime = 0
        self.timers = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        titleLabel = QLabel(self.title, objectName="GameTitle")
        layout.addWidget(titleLabel)
        hintLabel = QLabel(self.hint, objectName="GameHint")
        hintLabel.setWordWrap(True)
        layout.addWidget(hintLabel)
        self.statusLabel = QLabel("", objectName="GameStatus")
        layout.addWidget(self.statusLabel)
        self.area = QWidget()
        layout.addWidget(self.area, 1)
        self.clockTimer = self.makeTimer(100, self.tickClock)

    def makeTimer(self, interval, whenFired, singleShot=False):
        timer = QTimer(self, interval=interval, timeout=whenFired)
        timer.setSingleShot(singleShot)
        self.timers.append(timer)
        return timer

    def later(self, milliseconds, whenFired):
        timer = self.makeTimer(milliseconds, whenFired, True)
        timer.start()

    def startClock(self, seconds):
        self.endTime = time.time() + seconds
        self.clockTimer.start()
        self.tickClock()

    def secondsLeft(self):
        secondsLeft = self.endTime - time.time()
        if secondsLeft < 0:
            return 0
        return secondsLeft

    def tickClock(self):
        self.updateStatus()
        if self.endTime > 0 and self.secondsLeft() <= 0:
            self.timeUp()

    def updateStatus(self):
        pass

    def timeUp(self):
        self.finish(False)

    def start(self):
        pass

    def stop(self):
        self.finished = True
        for timer in self.timers:
            timer.stop()

    def finish(self, passed):
        if self.finished:
            return
        self.stop()
        self.whenDone(passed)


class MemoryMatch(BrainGame):
    title = "Memory Match"
    hint = "Flip two cards at a time and find every matching pair before time runs out."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.pairCount = 3 + difficulty // 2
        self.seconds = 70 - difficulty * 4
        letters = "ABCDEFGH"[:self.pairCount]
        self.cards = list(letters + letters)
        random.shuffle(self.cards)
        self.buttons = []
        self.flipped = []
        self.matched = 0
        grid = QGridLayout(self.area)
        grid.setSpacing(8)
        columns = 4
        for index in range(len(self.cards)):
            button = QPushButton("?", cursor=Qt.CursorShape.PointingHandCursor)
            button.setFixedSize(64, 64)
            button.setStyleSheet(tileStyle("#5B5470"))
            button.clicked.connect(lambda checked=False, i=index: self.flip(i))
            self.buttons.append(button)
            grid.addWidget(button, index // columns, index % columns)

    def start(self):
        self.startClock(self.seconds)

    def updateStatus(self):
        self.statusLabel.setText(str(self.matched) + " / " + str(self.pairCount) + " pairs   ·   " + str(int(self.secondsLeft())) + "s left")

    def flip(self, index):
        if index in self.flipped or len(self.flipped) == 2 or self.buttons[index].text() != "?":
            return
        letter = self.cards[index]
        self.buttons[index].setText(letter)
        self.buttons[index].setStyleSheet(tileStyle(TILE_COLORS["ABCDEFGH".index(letter)]))
        self.flipped.append(index)
        if len(self.flipped) == 2:
            firstIndex, secondIndex = self.flipped
            if self.cards[firstIndex] == self.cards[secondIndex]:
                self.flipped = []
                self.matched = self.matched + 1
                self.updateStatus()
                if self.matched == self.pairCount:
                    self.finish(True)
            else:
                self.later(650, self.flipBack)

    def flipBack(self):
        for index in self.flipped:
            self.buttons[index].setText("?")
            self.buttons[index].setStyleSheet(tileStyle("#5B5470"))
        self.flipped = []


class SequenceMemory(BrainGame):
    title = "Sequence Memory"
    hint = "Watch the tiles light up, then click them in the same order."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.goalLength = 4 + difficulty // 2
        self.flashTime = 650 - difficulty * 40
        self.sequence = [random.randrange(4) for number in range(3)]
        self.typed = []
        self.showing = False
        self.buttons = []
        grid = QGridLayout(self.area)
        grid.setSpacing(10)
        for index in range(4):
            button = QPushButton("", cursor=Qt.CursorShape.PointingHandCursor)
            button.setFixedSize(96, 96)
            button.clicked.connect(lambda checked=False, i=index: self.pressed(i))
            self.buttons.append(button)
            grid.addWidget(button, index // 2, index % 2)
        self.dimAll()

    def dimAll(self):
        for index in range(4):
            dimColor = QColor(TILE_COLORS[index]).darker(220).name()
            self.buttons[index].setStyleSheet(tileStyle(dimColor))

    def start(self):
        self.playSequence()

    def updateStatus(self):
        self.statusLabel.setText("Length " + str(len(self.sequence)) + " of " + str(self.goalLength))

    def playSequence(self):
        self.showing = True
        self.typed = []
        self.updateStatus()
        self.statusLabel.setText("Watch...  length " + str(len(self.sequence)) + " of " + str(self.goalLength))
        delay = 500
        for index in self.sequence:
            self.later(delay, lambda i=index: self.buttons[i].setStyleSheet(tileStyle(TILE_COLORS[i])))
            self.later(delay + self.flashTime, self.dimAll)
            delay = delay + self.flashTime + 200
        self.later(delay, self.yourTurn)

    def yourTurn(self):
        self.showing = False
        self.statusLabel.setText("Your turn!  length " + str(len(self.sequence)) + " of " + str(self.goalLength))

    def pressed(self, index):
        if self.showing or self.finished:
            return
        self.buttons[index].setStyleSheet(tileStyle(TILE_COLORS[index]))
        self.later(180, self.dimAll)
        self.typed.append(index)
        if self.typed[-1] != self.sequence[len(self.typed) - 1]:
            self.finish(False)
            return
        if len(self.typed) == len(self.sequence):
            if len(self.sequence) >= self.goalLength:
                self.finish(True)
                return
            self.sequence.append(random.randrange(4))
            self.showing = True
            self.later(600, self.playSequence)


class QuickMath(BrainGame):
    title = "Quick Math"
    hint = "Solve as many as you can before the timer runs out. Press Enter to answer."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.goal = 5 + difficulty // 2
        self.correct = 0
        self.answer = 0
        areaLayout = QVBoxLayout(self.area)
        self.problemLabel = QLabel("", objectName="GameBig")
        self.problemLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        areaLayout.addWidget(self.problemLabel)
        self.answerBox = QLineEdit()
        self.answerBox.setPlaceholderText("Your answer")
        self.answerBox.returnPressed.connect(self.checkAnswer)
        areaLayout.addWidget(self.answerBox)
        areaLayout.addStretch()

    def start(self):
        self.nextProblem()
        self.answerBox.setFocus()
        self.startClock(40)

    def updateStatus(self):
        self.statusLabel.setText(str(self.correct) + " / " + str(self.goal) + " correct   ·   " + str(int(self.secondsLeft())) + "s left")

    def nextProblem(self):
        biggest = 10 + self.difficulty * 6
        kinds = ["+", "-"]
        if self.difficulty >= 4:
            kinds.append("×")
        if self.difficulty >= 7:
            kinds.append("÷")
        kind = random.choice(kinds)
        if kind == "+":
            first = random.randint(2, biggest)
            second = random.randint(2, biggest)
            self.answer = first + second
        elif kind == "-":
            first = random.randint(2, biggest)
            second = random.randint(1, first)
            self.answer = first - second
        elif kind == "×":
            first = random.randint(2, 3 + self.difficulty)
            second = random.randint(2, 12)
            self.answer = first * second
        else:
            second = random.randint(2, 3 + self.difficulty)
            self.answer = random.randint(2, 12)
            first = second * self.answer
        self.problemLabel.setText(str(first) + "  " + kind + "  " + str(second))
        self.answerBox.clear()

    def checkAnswer(self):
        if self.finished:
            return
        if self.answerBox.text().strip().lstrip("-").isdigit() and int(self.answerBox.text().strip()) == self.answer:
            self.correct = self.correct + 1
            if self.correct >= self.goal:
                self.finish(True)
                return
        self.nextProblem()
        self.updateStatus()


class OddOneOut(BrainGame):
    title = "Odd One Out"
    hint = "One square is a slightly different color. Click it! You need 4 out of 5."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.gridSize = 3 + difficulty // 3
        self.difference = 70 - difficulty * 6
        self.round = 0
        self.wins = 0
        self.grid = QGridLayout(self.area)
        self.grid.setSpacing(6)
        self.buttons = []
        for index in range(self.gridSize * self.gridSize):
            button = QPushButton("", cursor=Qt.CursorShape.PointingHandCursor)
            button.setFixedSize(280 // self.gridSize, 280 // self.gridSize)
            button.clicked.connect(lambda checked=False, i=index: self.picked(i))
            self.buttons.append(button)
            self.grid.addWidget(button, index // self.gridSize, index % self.gridSize)

    def start(self):
        self.nextRound()

    def updateStatus(self):
        self.statusLabel.setText("Round " + str(self.round) + " of 5   ·   " + str(self.wins) + " right   ·   " + str(int(self.secondsLeft())) + "s")

    def nextRound(self):
        if self.round == 5:
            self.finish(self.wins >= 4)
            return
        self.round = self.round + 1
        baseColor = QColor.fromHsv(random.randrange(360), 150, 200)
        oddValue = 200 - self.difference
        if random.random() < 0.5:
            oddValue = 200 + self.difference // 2
        oddColor = QColor.fromHsv(baseColor.hue(), 150, oddValue)
        self.oddIndex = random.randrange(len(self.buttons))
        for index in range(len(self.buttons)):
            color = oddColor if index == self.oddIndex else baseColor
            self.buttons[index].setStyleSheet(tileStyle(color.name()).replace("12px", "8px"))
        self.startClock(10 - self.difficulty // 2)

    def picked(self, index):
        if self.finished:
            return
        if index == self.oddIndex:
            self.wins = self.wins + 1
        self.nextRound()

    def timeUp(self):
        self.nextRound()


class NumberMemory(BrainGame):
    title = "Number Memory"
    hint = "Remember the number, then type it after it disappears. You need 2 out of 3."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.digits = 3 + difficulty // 2
        self.round = 0
        self.wins = 0
        self.number = ""
        areaLayout = QVBoxLayout(self.area)
        self.numberLabel = QLabel("", objectName="GameBig")
        self.numberLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        areaLayout.addWidget(self.numberLabel)
        self.answerBox = QLineEdit()
        self.answerBox.setPlaceholderText("Type the number")
        self.answerBox.returnPressed.connect(self.checkAnswer)
        self.answerBox.hide()
        areaLayout.addWidget(self.answerBox)
        areaLayout.addStretch()

    def start(self):
        self.nextRound()

    def updateStatus(self):
        self.statusLabel.setText("Round " + str(self.round) + " of 3   ·   " + str(self.wins) + " right")

    def nextRound(self):
        if self.round == 3:
            self.finish(self.wins >= 2)
            return
        self.round = self.round + 1
        digitCount = self.digits + self.round - 1
        self.number = str(random.randint(1, 9))
        for count in range(digitCount - 1):
            self.number = self.number + str(random.randint(0, 9))
        self.numberLabel.setText(self.number)
        self.answerBox.hide()
        self.updateStatus()
        self.later(1500 + digitCount * 350, self.hideNumber)

    def hideNumber(self):
        self.numberLabel.setText("?")
        self.answerBox.clear()
        self.answerBox.show()
        self.answerBox.setFocus()

    def checkAnswer(self):
        if self.answerBox.isHidden() or self.finished:
            return
        if self.answerBox.text().strip() == self.number:
            self.wins = self.wins + 1
        self.nextRound()


class ColorWords(BrainGame):
    title = "Color Words"
    hint = "Click the color the word is PAINTED in, not what it says. You need 8 out of 10."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.secondsPerWord = 3.2 - difficulty * 0.22
        self.round = 0
        self.wins = 0
        self.inkName = ""
        areaLayout = QVBoxLayout(self.area)
        self.wordLabel = QLabel("", objectName="GameBig")
        self.wordLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        areaLayout.addWidget(self.wordLabel)
        buttonRow = QHBoxLayout()
        for colorName, colorCode in COLOR_NAMES:
            button = QPushButton(colorName, cursor=Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(48)
            button.setStyleSheet(tileStyle("#3B3645").replace("20px", "15px"))
            button.clicked.connect(lambda checked=False, n=colorName: self.picked(n))
            buttonRow.addWidget(button)
        areaLayout.addLayout(buttonRow)
        areaLayout.addStretch()

    def start(self):
        self.nextWord()

    def updateStatus(self):
        self.statusLabel.setText("Word " + str(self.round) + " of 10   ·   " + str(self.wins) + " right   ·   " + format(self.secondsLeft(), ".1f") + "s")

    def nextWord(self):
        if self.round == 10:
            self.finish(self.wins >= 8)
            return
        self.round = self.round + 1
        wordName = random.choice(COLOR_NAMES)[0]
        self.inkName, inkCode = random.choice(COLOR_NAMES)
        self.wordLabel.setText(wordName.upper())
        self.wordLabel.setStyleSheet(f"color: {inkCode}; font-size: 44px; font-weight: 800;")
        self.startClock(self.secondsPerWord)

    def picked(self, colorName):
        if self.finished:
            return
        if colorName == self.inkName:
            self.wins = self.wins + 1
        self.nextWord()

    def timeUp(self):
        self.nextWord()


class NumberGrid(BrainGame):
    title = "Number Grid"
    hint = "Click the numbers in order, starting at 1, as fast as you can."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.gridSize = 3
        if difficulty >= 3:
            self.gridSize = 4
        if difficulty >= 7:
            self.gridSize = 5
        self.seconds = self.gridSize * self.gridSize * (2.4 - difficulty * 0.12)
        self.nextNumber = 1
        numbers = list(range(1, self.gridSize * self.gridSize + 1))
        random.shuffle(numbers)
        grid = QGridLayout(self.area)
        grid.setSpacing(6)
        for index in range(len(numbers)):
            button = QPushButton(str(numbers[index]), cursor=Qt.CursorShape.PointingHandCursor)
            button.setFixedSize(280 // self.gridSize, 280 // self.gridSize)
            button.setStyleSheet(tileStyle("#3B3645"))
            button.clicked.connect(lambda checked=False, b=button: self.picked(b))
            grid.addWidget(button, index // self.gridSize, index % self.gridSize)

    def start(self):
        self.startClock(self.seconds)

    def updateStatus(self):
        self.statusLabel.setText("Next: " + str(self.nextNumber) + "   ·   " + str(int(self.secondsLeft())) + "s left")

    def picked(self, button):
        if self.finished or button.text() != str(self.nextNumber):
            return
        button.setStyleSheet(tileStyle("#2FB36D"))
        self.nextNumber = self.nextNumber + 1
        if self.nextNumber > self.gridSize * self.gridSize:
            self.finish(True)


class PatternGrid(BrainGame):
    title = "Pattern Grid"
    hint = "Some squares light up. Remember them, then click all of them. You need 2 out of 3."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.gridSize = 3 + difficulty // 4
        self.litCount = 3 + difficulty // 2
        self.round = 0
        self.wins = 0
        self.lit = []
        self.clicked = []
        self.showing = False
        self.buttons = []
        grid = QGridLayout(self.area)
        grid.setSpacing(6)
        for index in range(self.gridSize * self.gridSize):
            button = QPushButton("", cursor=Qt.CursorShape.PointingHandCursor)
            button.setFixedSize(260 // self.gridSize, 260 // self.gridSize)
            button.clicked.connect(lambda checked=False, i=index: self.picked(i))
            self.buttons.append(button)
            grid.addWidget(button, index // self.gridSize, index % self.gridSize)
        self.clearGrid()

    def clearGrid(self):
        for button in self.buttons:
            button.setStyleSheet(tileStyle("#3B3645").replace("12px", "8px"))

    def start(self):
        self.nextRound()

    def updateStatus(self):
        self.statusLabel.setText("Round " + str(self.round) + " of 3   ·   " + str(self.wins) + " right")

    def nextRound(self):
        if self.round == 3:
            self.finish(self.wins >= 2)
            return
        self.round = self.round + 1
        self.updateStatus()
        self.clearGrid()
        self.clicked = []
        self.lit = random.sample(range(len(self.buttons)), self.litCount)
        self.showing = True
        for index in self.lit:
            self.buttons[index].setStyleSheet(tileStyle("#3D8BFD").replace("12px", "8px"))
        self.later(1400 + self.litCount * 150, self.hidePattern)

    def hidePattern(self):
        self.clearGrid()
        self.showing = False

    def picked(self, index):
        if self.showing or self.finished or index in self.clicked:
            return
        self.clicked.append(index)
        if index not in self.lit:
            self.buttons[index].setStyleSheet(tileStyle("#E5534B").replace("12px", "8px"))
            self.showing = True
            self.later(700, self.nextRound)
            return
        self.buttons[index].setStyleSheet(tileStyle("#3D8BFD").replace("12px", "8px"))
        if len(self.clicked) == len(self.lit):
            self.wins = self.wins + 1
            self.showing = True
            self.later(500, self.nextRound)


class WordScramble(BrainGame):
    title = "Word Scramble"
    hint = "Unscramble the letters to make a word. You need 2 out of 3."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        wordSize = "short"
        if difficulty >= 4:
            wordSize = "medium"
        if difficulty >= 7:
            wordSize = "long"
        self.words = random.sample(WORDS[wordSize], 3)
        self.seconds = 30 - difficulty
        self.round = 0
        self.wins = 0
        areaLayout = QVBoxLayout(self.area)
        self.lettersLabel = QLabel("", objectName="GameBig")
        self.lettersLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        areaLayout.addWidget(self.lettersLabel)
        self.answerBox = QLineEdit()
        self.answerBox.setPlaceholderText("Type the word")
        self.answerBox.returnPressed.connect(self.checkAnswer)
        areaLayout.addWidget(self.answerBox)
        areaLayout.addStretch()

    def start(self):
        self.nextWord()

    def updateStatus(self):
        self.statusLabel.setText("Word " + str(self.round) + " of 3   ·   " + str(self.wins) + " right   ·   " + str(int(self.secondsLeft())) + "s left")

    def nextWord(self):
        if self.round == 3:
            self.finish(self.wins >= 2)
            return
        self.round = self.round + 1
        word = self.words[self.round - 1]
        letters = list(word)
        while "".join(letters) == word:
            random.shuffle(letters)
        self.lettersLabel.setText(" ".join(letters).upper())
        self.answerBox.clear()
        self.answerBox.setFocus()
        self.startClock(self.seconds)

    def checkAnswer(self):
        if self.finished:
            return
        if self.answerBox.text().strip().lower() == self.words[self.round - 1]:
            self.wins = self.wins + 1
            self.nextWord()
        else:
            self.answerBox.clear()

    def timeUp(self):
        self.nextWord()


class Reaction(BrainGame):
    title = "Reaction Time"
    hint = "Click the box as soon as it turns green. Clicking too early counts as a slow try."

    def __init__(self, difficulty, whenDone):
        super().__init__(difficulty, whenDone)
        self.goalTime = 520 - difficulty * 22
        self.tries = []
        self.greenAt = 0
        self.waiting = False
        areaLayout = QVBoxLayout(self.area)
        self.box = QPushButton("Get ready...", cursor=Qt.CursorShape.PointingHandCursor)
        self.box.setFixedHeight(200)
        self.box.clicked.connect(self.clickedBox)
        areaLayout.addWidget(self.box)
        areaLayout.addStretch()
        self.greenTimer = self.makeTimer(1000, self.turnGreen, True)

    def start(self):
        self.nextTry()

    def updateStatus(self):
        averageText = "-"
        if len(self.tries) > 0:
            averageText = str(int(sum(self.tries) / len(self.tries))) + " ms"
        self.statusLabel.setText("Try " + str(len(self.tries) + 1) + " of 5   ·   average " + averageText + "   ·   goal " + str(self.goalTime) + " ms")

    def nextTry(self):
        if len(self.tries) == 5:
            self.finish(sum(self.tries) / 5 <= self.goalTime)
            return
        self.updateStatus()
        self.greenAt = 0
        self.waiting = True
        self.box.setText("Wait for green...")
        self.box.setStyleSheet(tileStyle("#B3261E"))
        self.greenTimer.start(random.randint(1200, 3200))

    def turnGreen(self):
        self.greenAt = time.time()
        self.box.setText("Click!")
        self.box.setStyleSheet(tileStyle("#2FB36D"))

    def clickedBox(self):
        if self.finished or not self.waiting:
            return
        self.waiting = False
        if self.greenAt == 0:
            self.greenTimer.stop()
            self.tries.append(1000)
            self.box.setText("Too early!")
        else:
            reactionTime = int((time.time() - self.greenAt) * 1000)
            self.tries.append(reactionTime)
            self.box.setText(str(reactionTime) + " ms")
        self.box.setStyleSheet(tileStyle("#3B3645"))
        self.later(900, self.nextTry)


ALL_GAMES = [MemoryMatch, SequenceMemory, QuickMath, OddOneOut, NumberMemory, ColorWords, NumberGrid, PatternGrid, WordScramble, Reaction]
