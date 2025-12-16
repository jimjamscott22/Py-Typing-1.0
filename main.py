import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import QApplication

from ui.main_window import TypingPracticeApp

def build_window_icon() -> QIcon:
    size = 128
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor("#1e88e5"))
    gradient.setColorAt(1, QColor("#42a5f5"))

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(pixmap.rect(), 28, 28)

    painter.setPen(QPen(QColor("#ffffff")))
    painter.setFont(QFont("Montserrat", 64, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")

    painter.end()
    return QIcon(pixmap)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(build_window_icon())

    window = TypingPracticeApp()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
