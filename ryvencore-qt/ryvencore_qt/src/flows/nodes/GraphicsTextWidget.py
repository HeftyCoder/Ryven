from typing import Optional
from qtpy.QtCore import QRectF, Qt
from qtpy.QtWidgets import QGraphicsItem
from qtpy.QtGui import QFont

from qtpy.QtWidgets import (
    QGraphicsWidget,
    QGraphicsTextItem,
    QGraphicsLayoutItem,
)

from qtpy.QtGui import QColor
from dataclasses import dataclass, field


@dataclass
class TextStyle:
    """A simple config class for GraphicsTextWidget"""
    
    color: QColor = field(default_factory=lambda: QColor('#FFFFFF'))
    font: QFont = field(default_factory=QFont)


class GraphicsTextWidget(QGraphicsWidget):
    """Wraps QGraphicsTextItem as a QGraphicsWidget"""
    
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
        self.update()
        
    def default_text_color(self):
        return self._text_item.defaultTextColor()
    
    def set_font(self, font):
        self._text_item.setFont(font)
        self.update()
        
    def set_text_style(self, style: TextStyle):
        self._text_item.setFont(style.font)
        self._text_item.setDefaultTextColor(style.color)
        self.update()