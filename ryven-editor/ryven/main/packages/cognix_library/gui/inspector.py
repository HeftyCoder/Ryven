from qtpy.QtWidgets import QVBoxLayout, QWidget
from ryven.gui_env import (
    node_gui, 
    NodeGUI, 
    NodeInspectorWidget,
    obj_insp_assoc,
)

from ryvencore_qt.flows.view import FlowView
from ryvencore_qt.session_gui import SessionGUI
from ryven.main.packages.cognix_library.gui.config.abc import NodeConfigInspector

from cognix.api import CognixNode

class CognixNodeInspectorWidget(NodeInspectorWidget, QWidget):
    """The basic CogniX Node Inspector. Handles GUI config as well"""
    
    def __init__(self, params: tuple[CognixNode, NodeGUI]):
        QWidget.__init__(self)
        NodeInspectorWidget.__init__(self, params)
        self.node, self.node_gui = params
        
        self.setLayout(QVBoxLayout())
        
        config_gui_cls = obj_insp_assoc().get_assoc(type(self.node.config))
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
    
    def __init__(self, params: tuple[CognixNode, SessionGUI, FlowView]):
        super().__init__(params)
        self.node: CognixNode = self.node

    def initialized(self):
        self.config_changed_func = self.apply_config_changed_event()

    def _on_deleted(self):
        if self.config_changed_func:
            self.node.config.remove_changed_event(self.config_changed_func)
            self.config_changed_func = None
        super()._on_deleted()
    
    def _on_restored(self):
        self.config_changed_func = self.apply_config_changed_event()
        
    def apply_config_changed_event(self):
        """Creates the config changed GUI event based on config GUI class"""
        
        cognix_n: CognixNode = self.node
        config = cognix_n.config
        if not config:
            return None
        
        config_gui_cls: NodeConfigInspector = obj_insp_assoc().get_assoc(type(config))
        if not config_gui_cls:
            return None
        
        e = config_gui_cls.create_config_changed_event(cognix_n, self)
        if e:
            cognix_n.config.add_changed_event(e)
        
        return e
    
        
        
        
