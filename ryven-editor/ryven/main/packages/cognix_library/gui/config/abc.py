from __future__ import annotations
from ryvencore_qt.src.flows.nodes.WidgetBaseClasses import InspectorWidget
from cognix import NodeConfig, CognixNode
from ryven.gui_env import NodeGUI

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..inspector import CognixNodeGUI

class NodeConfigInspector(InspectorWidget[NodeConfig]):
    """Base class for inspecting a node config"""
    
    @classmethod
    def create_config_changed_event(cls, node: CognixNode, gui: CognixNodeGUI):
        """
        VIRTUAL
        
        Override this to connect a config changed event to the gui.
        """
        pass
    
    def __init__(self, params: tuple[NodeConfig, NodeGUI]):
        config, gui = params
        super().__init__(config, gui.flow_view)
    
    def on_node_deleted(self, node: CognixNode):
        """Callback when a node is deleted"""
        pass