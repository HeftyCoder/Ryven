from ryvencore_qt.src.flows.nodes.WidgetBaseClasses import InspectorWidget
from cognix.api import NodeConfig
from ryven.gui_env import Association
from .abc import NodeConfigInspector
        
class __InspectorToNodeConfig(Association[NodeConfig, NodeConfigInspector]):
    
    parent_base_type = NodeConfig
    assoc_base_type = NodeConfigInspector
    _attr_name = 'INSPECTOR'

def node_config_gui(node_config_cls: type[NodeConfig]):
    """
    Registers an inspector for a node config. The inspector of a config is inherited to its sub-classes,
    but can be overriden by specifying a new gui for the sub-class.
    """
    
    return __InspectorToNodeConfig.associate_decor(node_config_cls)

def get_config_inspector_cls(node_config_cls: type[NodeConfig]):
    """Returns the inspector class associated with the NodeConfig class"""
    return __InspectorToNodeConfig.get_assoc(node_config_cls)

