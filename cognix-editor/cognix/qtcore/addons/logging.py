from __future__ import annotations
from qtpy.QtCore import (
    Qt, 
    QModelIndex, 
    QPersistentModelIndex, 
    QSize,
    QRect,
)
from qtpy.QtGui import (
    QFont, 
    QFontMetrics,
    QStandardItemModel, 
    QStandardItem,
    QPainter,
    QTextDocument,
    QPalette,
    QColor,
)
from qtpy.QtWidgets import (
    QWidget, 
    QHBoxLayout, 
    QVBoxLayout, 
    QLabel, 
    QPlainTextEdit,
    QSplitter,
    QScrollArea,
    QListView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
)

from qtpy.QtCore import Signal
from cognixcore.addons.logging import Logger
from enum import StrEnum
import logging

class LogLevelColors(StrEnum):
    DEBUG = "#808080" # Gray
    INFO = "#0000FF" # Blue
    WARNING = "#FFFF00" # Yellow
    ERROR = "#FFA500" # Orange
    CRITICAL = "#FF0000" # Red

_level_color = {
    logging.DEBUG: LogLevelColors.DEBUG,
    logging.INFO: LogLevelColors.INFO,
    logging.WARNING: LogLevelColors.WARNING,
    logging.ERROR: LogLevelColors.ERROR,
    logging.CRITICAL: LogLevelColors.CRITICAL
}

class LogCallbackHandler(logging.Handler):
    """The callback handler for a LogWidget"""
    
    def __init__(self, log_widget: LogWidget, level: int | str = 0):
        super().__init__(level)
        self._log_widget = log_widget
    
    def emit(self, record: logging.LogRecord):
        self._log_widget.on_log_signal.emit(record, self._log_widget.formatter)

class LogItem(QStandardItem):
    """A log item to be used in a qt model."""
    
    def __init__(
        self, 
        record: logging.LogRecord, 
        formatter:logging.Formatter,
        icon=None
    ):
        
        self.record = record
        self.formatter = formatter
        
        msg = self.rich_text()
        # we have to build the message through html
        
        if not icon:
            QStandardItem.__init__(self, msg)
        else:
            QStandardItem.__init__(self, icon, msg)
        
        self.setEditable(False)
    
    def format_header(self) -> str:
        lvl = self.record.levelno
        time = self.formatter.formatTime(self.record) # d3d3d3
        return (
        f"""<font color='{_level_color[lvl]}'>{self.record.levelname}</font>
            <font color='LightGray'>{time}</font>
        """
        )
    
    def format_message(self) -> str:
        return self.record.getMessage()
    
    def rich_text(self):
        return f"{self.format_header()}<br>{self.format_message()}"
        
            
class LogItemDelegate(QStyledItemDelegate):
    
    def paint(self, painter, option, index):
        painter.save()
        # I don't seem them in the IDE so I'm setting them explicitly
        # so it is easier to work with
        state: QStyle.StateFlag = option.state
        rect: QRect = option.rect
        palette: QPalette = option.palette
        widget: QWidget = option.widget
        
        # Draw backgrounds for selection, hover, focus etc
        widget.style().drawPrimitive(QStyle.PE_PanelItemViewItem, option, painter, widget)
        
        text = index.data(Qt.DisplayRole)
        doc = QTextDocument()
        doc.setHtml(text)
        
        painter.translate(rect.topLeft())
        doc.drawContents(painter)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        # Retrieve the HTML content from the model
        html = index.data(Qt.DisplayRole)
        
        # Create a QTextDocument to measure the HTML content
        text_document = QTextDocument()
        text_document.setHtml(html)
        text_document.setTextWidth(option.rect.width())

        widget: QWidget = option.widget
        h = QFontMetrics(widget.font()).height() # a single line of height
        # Calculate and return the size hint for the item
        return QSize(text_document.idealWidth(), 2.5*h)

class LogWidget(QWidget):
    """Convenience class for a QWidget representing a log."""

    on_log_signal = Signal(logging.LogRecord, logging.Formatter)
    
    def __init__(self, logger: Logger):
        super().__init__()

        self.logger = logger
        self.formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = LogCallbackHandler(self)
        handler.setFormatter(self.formatter)
        self.logger.addHandler(handler)

        self.main_layout = QVBoxLayout()
        self.header_layout = QHBoxLayout()
        self.main_layout.addLayout(self.header_layout)
        
        title_label = QLabel(self.logger.name)
        title_label.setFont(QFont('Poppins', 12))
        self.header_layout.addWidget(title_label)

        # for messages + big message
        self.splitter = QSplitter()
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.main_layout.addWidget(self.splitter)
        
        # messages scroll
        # self.splitter.addWidget(self.msg_scroll)
        self.model = QStandardItemModel()
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(LogItemDelegate())
        
        def clicked(index: QModelIndex):
            
            item: LogItem = self.model.itemFromIndex(index)
            self.text_edit.clear()
            msg = f"{item.format_header()}<br><br>{item.format_message()}"
            self.text_edit.appendHtml(msg)
            
        self.list_view.clicked.connect(clicked)
        
        self.splitter.addWidget(self.list_view)
        
        # text edit
        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.splitter.addWidget(self.text_edit)

        self.setLayout(self.main_layout)
        
        # signal
        self.on_log_signal.connect(self.on_log)

    def on_log(self, record: logging.LogRecord, formatter: logging.Formatter):
        self.model.appendRow(
            LogItem(record=record, formatter=formatter)
        )
