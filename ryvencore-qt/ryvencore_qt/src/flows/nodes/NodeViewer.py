from typing import Tuple, TYPE_CHECKING
from qtpy.QtGui import QCloseEvent, QHideEvent, QShowEvent
from qtpy.QtWidgets import QTabWidget, QVBoxLayout, QDialog, QSplitter
from qtpy.QtCore import Qt

from ryvencore import Node

from .WidgetBaseClasses import NodeViewerWidget
from ...code_editor.CodePreviewWidget import CodePreviewWidget

if TYPE_CHECKING:
    from .NodeGUI import NodeGUI

class NodeViewerDefault(NodeViewerWidget, QDialog):
    """
    The default class for creating a view window for a node.
    
    Attaches a horizontal splitter as self.content. The inspector
    is also attached to the splitter.
    
    It is adviced to utilize this class for any potential overrides, as
    it connects to other qt events.
    """
    
    attach_inspect_widgets = True
    
    def __init__(self, params: Tuple[Node, 'NodeGUI'], parent=None):
        NodeViewerWidget.__init__(self, params)
        QDialog.__init__(self, parent)
        
        self.setLayout(QVBoxLayout())
        self.setWindowFlag(Qt.Widget)
    
        self.content = QSplitter()
        self.content.setOrientation(Qt.Orientation.Horizontal)
        self.layout().addWidget(self.content)
        
        if self.attach_inspect_widgets:
            self.inspect_tab_widget = QTabWidget()
            
            self.inspector_widget = self.node_gui.create_inspector()
            self.inspect_tab_widget.addTab(self.inspector_widget, 'Inspector')
            
            self.code_preview_widget = CodePreviewWidget(
                self.node_gui.session_gui.cd_storage,
            )
            self.inspect_tab_widget.addTab(self.code_preview_widget, 'Source Code')
            
            self.content.addWidget(self.inspect_tab_widget)
        
        self.setWindowTitle(f'{self.node_gui.display_title} Viewer')
        
    # Connect Viewer functons to QT events
    
    def showEvent(self, show_event: QShowEvent):
        
        if self.code_preview_widget:
            self.code_preview_widget._set_node(self.node)
            
        self.on_before_shown()
        super().showEvent(show_event)
        self.on_after_shown()
    
    def hideEvent(self, hide_event: QHideEvent):
        self.on_before_hidden()
        super().hideEvent(hide_event)
        self.on_after_hidden()
    
    def closeEvent(self, close_event: QCloseEvent):
        self.on_before_closed()
        super().closeEvent(close_event)
        self.on_after_closed()
    
    
     