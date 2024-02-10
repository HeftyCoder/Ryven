from PySide6.QtCore import QRectF
from qtpy.QtWidgets import (
    QWidget, 
    QGraphicsItem, 
    QGraphicsWidget, 
    QStyleOptionGraphicsItem,
    QGraphicsLayoutItem,
)
from numbers import Real
from typing import Union
from qtpy.QtCore import Qt, QPointF, QSizeF
from qtpy.QtGui import QColor, QPainter, QFont, QPen


class GraphicsProgressBar(QGraphicsWidget):
    
    """A graphics progress bar for display in a Graphics View"""
    
    def __init__(self, color: QColor = QColor(0, 255, 0), height: Real = 20, parent: Union[QGraphicsItem, None] = None):
        super().__init__(parent)
        self._color = color
        self._progress: Real = 0
        self._offset: Real = 0
        self._height = 20
        self._width = 100
        self._font: QFont = None
        self._text_color: QColor = QColor(185, 185, 185)
        
    @property
    def color(self):
        return self._color
    
    @color.setter
    def color (self, color: QColor):
        self._color = color
        self.update()
    
    @property
    def progress(self):
        return self._progress

    @progress.setter
    def progress(self, value: Real):
        """Progress should be between 0 and 1"""
        self._progress = self.__clamp(value, 0, 1)
        self.update()
    
    @property
    def offset(self):
        return self._offset
    
    @offset.setter
    def offset(self, value: Real):
        self._offset = self.__clamp(value, 0, self._progress)
        self.update()
        
    def set_progress_values(self, progress: Real, offset: Real):
        self.progress = progress
        self.offset = offset
        self.update()
    
    @property
    def height(self):
        return self._height
    
    @height.setter
    def height(self, value: Real):
        self._height = value
        self.updateGeometry()
        self.update()
    
    @property
    def width(self):
        return self._width
    
    @width.setter
    def width(self, value: Real):
        self._width = value
        self.updateGeometry()
        self.update()
    
    def set_size(self, width: Real, height: Real):
        self._width = width
        self._height = height
        self.updateGeometry()
        self.update()
        
    @property
    def font(self):
        return self._font

    @font.setter
    def font(self, value: QFont):
        self._font = value
        self.update()
    
    @property
    def text_color(self):
        return self._text_color
    
    @text_color.setter
    def text_color(self, color: QColor):
        self._text_color = color
        if self._text_color is None:
            self._text_color = QColor(185, 185, 185)
        self.update()
    
    def boundingRect(self) -> QRectF:
        return QRectF(QPointF(0, 0), self.geometry().size())
    
    def setGeometry(self, rect: QRectF):
        self.prepareGeometryChange()
        rect.setHeight(self.height)
        rect.setWidth(self.width)
        QGraphicsLayoutItem.setGeometry(self, rect)
        self.setPos(rect.topLeft())
    
    def sizeHint(self, which, constraint=...):
        return QSizeF(self._width, self._height)
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Union[QWidget, None] = ...):
        rect = self.boundingRect()
        x, y, width, height = rect.x(), rect.y(), rect.width(), rect.height()
        
        rect_width = width - 40
        
        # Draw grey backgroundint(rect_width * self.progress)
        painter.setBrush(QColor(200, 200, 200))
        bar_rect = QRectF(x, y, rect_width, height)
        painter.drawRect(bar_rect)
        
        # Draw progress
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        p_x = int(rect_width * self.offset)
        # excess is cut automatically
        p_width = int(rect_width * self.progress)
        painter.drawRect(x + p_x, 0, p_width, height)
        
        # Draw text
        text_rect = QRectF(x + rect_width, y, width - rect_width, height)
        painter.setPen(self._text_color)
        painter.drawText(text_rect, f'{self.progress * 100}%', Qt.AlignmentFlag.AlignCenter)
    
    def __clamp(self, num, min_value, max_value):
        return max(min(num, max_value), min_value)