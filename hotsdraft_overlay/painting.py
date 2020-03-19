from dataclasses import dataclass

from PyQt5.QtCore import QPoint, QRect, Qt
from PyQt5.QtGui import QPainter, QColor, QPen, QFont


@dataclass
class PaintCommand:
    def paint(self, painter: QPainter):
        raise NotImplemented()


@dataclass
class PaintRect(PaintCommand):
    rect: QRect
    color: QColor
    thickness: int

    def paint(self, painter: QPainter):
        painter.setPen(QPen(self.color, self.thickness, Qt.SolidLine))
        painter.drawRect(self.rect)


@dataclass
class PaintText(PaintCommand):
    text: str
    scale: int
    thickness: int
    position: QPoint
    color: QColor

    def paint(self, painter: QPainter):
        painter.setPen(QPen(self.color, self.thickness, Qt.SolidLine))
        painter.setFont(QFont("Arial", self.scale))
        painter.drawText(self.position, self.text)
