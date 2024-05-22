from __future__ import annotations
from ryvencore_qt.nodes.inspector import InspectorWidget, InspectedChangedEvent
from cognix.api import NodeConfig, CognixNode
from ryven.gui_env import NodeGUI

from typing import TYPE_CHECKING, Callable, Any, TypeVar
if TYPE_CHECKING:
    from ..inspector import CognixNodeGUI

ConfigType = TypeVar('ConfigType', bound=NodeConfig)

class NodeConfigInspector(InspectorWidget[ConfigType]):
    """Base class for inspecting a node config"""
    
    @classmethod
    def create_config_changed_event(cls, node: CognixNode, gui: CognixNodeGUI) -> Callable[[Any], None]:
        """
        VIRTUAL
        
        Override this to connect a config changed event to the gui.
        """
        pass
    
    def __init__(self, params: tuple[ConfigType, NodeGUI]):
        config, gui = params
        super().__init__(config, gui.flow_view)
    
    def on_insp_changed(self, change_event: InspectedChangedEvent[ConfigType]):
        pass
    
    def on_node_deleted(self, node: CognixNode):
        """Callback when a node is deleted"""
        pass