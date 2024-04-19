from qtpy.QtWidgets import QVBoxLayout, QWidget
from ryven.gui_env import (
    node_gui, 
    NodeGUI, 
    NodeInspectorWidget,
    get_config_inspector_cls,
)

from cognix import CognixNode

class CognixNodeInspectorWidget(NodeInspectorWidget, QWidget):
    """The basic CogniX Node Inspector. Handles GUI config as well"""
    
    def __init__(self, params: tuple[CognixNode, NodeGUI]):
        QWidget.__init__(self)
        NodeInspectorWidget.__init__(self, params)
        self.node, self.node_gui = params
        
        self.setLayout(QVBoxLayout())
        
        config_gui_cls = get_config_inspector_cls(type(self.node.config))
        self.config_gui = config_gui_cls((self.node.config, self.node_gui)) if config_gui_cls else None
        if self.config_gui:
            self.layout().addWidget(self.config_gui)
        
    def load(self):
        
        if self.config_gui:
            self.config_gui.load()
    
    def unload(self):
        
        if self.config_gui:
            self.config_gui.unload()
            
    def on_node_deleted(self):
        
        if self.config_gui:
            self.config_gui.on_node_deleted(self.node)


@node_gui(CognixNode)
class CognixNodeGUI(NodeGUI):
    """The base CogniX Node GUI parameters"""
    inspector_widget_class = CognixNodeInspectorWidget
    wrap_inspector_in_default = True

