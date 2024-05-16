from qtpy.QtWidgets import QVBoxLayout, QWidget
from qtpy.QtCore import Signal

from ryven.gui_env import (
    node_gui, 
    NodeGUI, 
    NodeInspectorWidget,
)

from ryvencore_qt.inspector import InspectedChangedEvent
from ryvencore_qt.flows.view import FlowView
from ryvencore_qt.flows.commands import DelegateCommand, undo_text_multi
from ryvencore_qt.session_gui import SessionGUI
from ryven.main.packages.cognix_library.gui.config.abc import NodeConfigInspector

from cognix.api import CognixNode, NodeConfig

class CognixNodeInspectorWidget(NodeInspectorWidget, QWidget):
    """The basic CogniX Node Inspector. Handles GUI config as well"""
    
    def __init__(self, params: tuple[CognixNode, NodeGUI]):
        QWidget.__init__(self)
        self.node, self.node_gui = params
        NodeInspectorWidget.__init__(self, params)
        
    def on_insp_changed(self, val: CognixNode):
        self.setLayout(QVBoxLayout())
        config_gui_cls = self.gui_env.get_inspector(type(self.node.config))
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
    
    config_changed_signal = Signal(NodeConfig, NodeConfig)
    """Event that is raised when the config changes"""
    inspector_widget_class = CognixNodeInspectorWidget
    wrap_inspector_in_default = True
    
    def __init__(self, params: tuple[CognixNode, SessionGUI, FlowView]):
        super().__init__(params)
        self.node: CognixNode = self.node
        self.config_changed_signal.connect(self._on_config_changed)
        
    def initialized(self):
        self.apply_conf_events()

    def _on_deleted(self):
        self.remove_conf_events()
        super()._on_deleted()
    
    def _on_restored(self):
        self.config_changed_func = self.apply_conf_events()
    
    def _on_config_changed(self, old_conf: NodeConfig, new_conf: NodeConfig):
        """Invoked when a configuration changes"""
        
        def redo_undo(old_conf: NodeConfig, new_conf: NodeConfig):
            changed_event = InspectedChangedEvent(old_conf, new_conf, False)
            insp_widget: CognixNodeInspectorWidget = self.inspector_widget
            insp_widget.config_gui.on_insp_changed(changed_event)
            
            viewer_insp: CognixNodeInspectorWidget = self.viewer_widget.inspector_widget
            if viewer_insp:
                viewer_insp.on_insp_changed(changed_event)
                    
        self.flow_view.push_undo(
            DelegateCommand(
                self.flow_view,
                undo_text_multi(
                    [self.node], 
                    f"Config changed: {old_conf.__class__.__name__} -> {new_conf.__class__.__name__}"
                ),
                redo_undo(new_conf, old_conf),
                redo_undo(old_conf, new_conf),
            )
        )
        
    def apply_conf_events(self):
        """Creates the config changed GUI event based on config GUI class"""
        
        cognix_n = self.node
        # apply config changed event
        cognix_n.config_changed.sub(self.config_changed_signal.emit)
        
        # appl config param change events
        config = cognix_n.config
        if not config:
            return None
        
        config_gui_cls: NodeConfigInspector = self.gui_env.get_inspector(type(config))
        if not config_gui_cls:
            return None
        
        e = config_gui_cls.create_config_changed_event(cognix_n, self)
        if e:
            cognix_n.config.add_changed_event(e)
        
        self.config_changed_func = e
    
    def remove_conf_events(self):
        
        self.node.config_changed.unsub(self.config_changed_signal.emit)
        
        # config params
        if self.config_changed_func:
            self.node.config.remove_changed_event(self.config_changed_func)
            self.config_changed_func = None
        
    
        
        
        
