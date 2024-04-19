from ryvencore_qt.src.flows.nodes.WidgetBaseClasses import InspectorWidget
from cognix import NodeConfig, CognixNode
from ryven.gui_env import NodeGUI

class NodeConfigInspector(InspectorWidget[NodeConfig]):
    """Base class for inspecting a node config"""
    
    def __init__(self, params: tuple[NodeConfig, NodeGUI]):
        config, gui = params
        super().__init__(config, gui.flow_view)
    
    def on_node_deleted(self, node: CognixNode):
        """Callback when a node is deleted"""
        pass