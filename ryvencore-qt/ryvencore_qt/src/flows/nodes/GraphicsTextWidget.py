from typing import Optional
from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QGraphicsItem

from qtpy.QtWidgets import (
    QGraphicsWidget,
    QGraphicsTextItem,
    QGraphicsLayoutItem,
)

from qtpy.QtGui import QColor


class GraphicsTextWidget(QGraphicsWidget):
    
    def __init__(self, parent = None) -> None:
        super().__init__(parent)
        self._text_item = QGraphicsTextItem(parent=self)
        
    def boundingRect(self):
        return self._text_item.boundingRect()
    
    def sizeHint(self, which, constraint=...):
        return self._text_item.boundingRect().size()
    
    def setGeometry(self, rect):
        self.prepareGeometryChange()
        QGraphicsLayoutItem.setGeometry(self, rect)
        self.setPos(rect.topLeft())
        
    def set_text(self, value: str):
        self._text_item.setPlainText(value)
        self.update()
    
    def set_html(self, html: str):
        self._text_item.setHtml(html)
        self.update()
    
    def set_text_width(self, width):
        self._text_item.setTextWidth(width)
        self.update()
    
    def set_default_text_color(self, color: QColor):
        self._text_item.setDefaultTextColor(color)