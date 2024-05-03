from qtpy.QtGui import QFont

from qtpy.QtWidgets import (
    QWidget,
    QGraphicsWidget,
    QGraphicsTextItem,
    QGraphicsLayoutItem,
    QGraphicsItem,
    QStyleOptionGraphicsItem,
)

from dataclasses import dataclass, field
from numbers import Real, Integral
from qtpy.QtCore import Qt, QPointF, QSizeF, QTimeLine, QRectF
from qtpy.QtGui import QColor, QPainter, QFont


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


class GraphicsProgressBar(QGraphicsWidget):
    
    """A graphics progress bar for display in a Graphics View"""
    
    def __init__(self, color: QColor = QColor(0, 255, 0), height: Real = 20, parent: QGraphicsItem | None = None):
        super().__init__(parent)
        self._color = color
        self._progress: Real = 0
        self._offset: Real = 0
        self._height = 20
        self._width = 100
        self._font: QFont = None
        self._text_color: QColor = QColor(185, 185, 185)

        self.__timeline = None
    # PROPERTIES
    
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
        self._offset = self.__clamp(value, 0, 1)
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
    
    # ANIMATION
    
    def play_animation(
        self, percent: Integral, 
        duration: Integral = 1, 
        frames: Integral = 100 
    ):
        """
        Plays an animation that indicates indefinite loading
        
        Duration is in seconds
        """
        
        # timeline creation
        self.__timeline = QTimeLine(duration * 1000, self)
        self.__timeline.setFrameRange(0, frames)
        self.__timeline.setLoopCount(0)
        
        # progress
        self.progress = percent
        
        def update_timeline(frame):
            half_point = int(frames * 0.5)
            if frame < half_point:
                # forward
                percentage = 2 * frame / frames
            else:
                # reverse
                percentage = 2 * (1 - frame / frames)
            
            final_value = 1 - percent
            self.offset = final_value * percentage
        
        self.__timeline.frameChanged.connect(update_timeline)
        
        self.__timeline.start()

    def stop_animation(self):
        if self.__timeline:
            self.__timeline.stop()
            self.__timeline.deleteLater()
            self.__timeline = None

    # DRAWING
    
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
        
    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = ...):
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
        painter.drawRect(x + p_x, y, p_width, height)
        
        # Draw text
        text_rect = QRectF(x + rect_width, y, width - rect_width, height)
        painter.setPen(self._text_color)
        
        if self.__timeline:
            painter.drawText(text_rect, f'---%', Qt.AlignmentFlag.AlignCenter)
        else:
            painter.drawText(text_rect, f'{self.progress * 100}%', Qt.AlignmentFlag.AlignCenter)
    
    def __clamp(self, num, min_value, max_value):
        return max(min(num, max_value), min_value)


