"""using q widget to make the window. for mac this appears in the top corner"""
"""
Everything to be added to dashboard:
1. streak + welcome msg
2. Daily stats
3. Weekly stats
4. Settings and config (read figma doc for more)


BEFORE MAKING EDITS READ GDOC SECTION "Dashboard priorities"
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QStyleOption,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QPainter, QPaintEvent


class Dashboard(QWidget):
    def __init__(self) -> None:
        super().__init__()

        # no close tabs
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)




        # init window & styling & layout
        self.setWindowTitle("focus guard appie")
        windowPropertiesSize = QApplication.primaryScreen().availableGeometry()
        self.resize(500, windowPropertiesSize.height() - 50) # padding boy
        # set to right corner
        x = windowPropertiesSize.x() + (windowPropertiesSize.width() - 500) - 25
        y = windowPropertiesSize.y() + 25  # Top boundary of usable space
        self.move(x, y)

        self.setObjectName("Dashboard")
        self.setStyleSheet(
            """
            QWidget#Dashboard {
                background-color: rgba(0, 0, 0, 70); 
                border-radius: 12px;
                border: solid rgba(255, 255, 255, 100);
                border-width: 0.5px;
            }
        """

        )
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)



    def paintEvent(self, event: QPaintEvent) -> None:
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, opt, painter, self
        )


if __name__ == "__main__":
    app = QApplication([])
    window = Dashboard()
    window.show()
    app.exec()