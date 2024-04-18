"""
This module automatically imports all requirements for Gui definitions of a nodes package.
"""

from ryvencore import Node
from ryvencore.InfoMsgs import InfoMsgs
from ryvencore_qt import NodeGUI, NodeInspectorWidget
from ryvencore_qt.src.flows.nodes.WidgetBaseClasses import InspectorWidget
from cognix import NodeConfig

from typing import TypeVar, Generic

import ryven.gui.std_input_widgets as inp_widgets

AssocType = TypeVar('AssocType')
"""The type to be inserted into the parent as an attribute"""
ParentType = TypeVar('ParentType')
"""The parent type"""


class Association(Generic[ParentType, AssocType]):
    """
    A class for statically creating a connection between two types.
    
    The parent class type ends up with an attribute containing the associated type
    """
    
    __explicit: set[type[ParentType]] = None
    parent_base_type: type[ParentType] = None
    assoc_base_type: type[AssocType] = None
    _attr_name = 'ASSOC'
    
    def __init_subclass__(cls):
        cls.__explicit = set()
        
    @classmethod
    def associate_decor(cls, parent_type: type[ParentType]):
        """Returns a decorator for creating the association"""
        
        if not issubclass(parent_type, cls.parent_base_type):
            raise ValueError(f"{parent_type} is not of type {cls.parent_base_type}")

        def register(assoc_type: type[AssocType]):
            if parent_type in cls.__explicit:
                InfoMsgs.write(f'{parent_type.__name__} has defined an explicit association {getattr(assoc_type, cls._attr_name).__name__}')
                return
            
            setattr(parent_type, cls._attr_name, assoc_type)
            cls.__explicit.add(parent_type)
            InfoMsgs.write(f"Registered association: {assoc_type} for {parent_type}")
            return assoc_type

        return register

    @classmethod
    def get_assoc(cls, parent_type: type[ParentType]) -> type[AssocType] | None:
        return getattr(parent_type, cls._attr_name) if hasattr(parent_type, cls._attr_name) else None

class __InspectorToNodeConfig(Association[NodeConfig, InspectorWidget]):
    
    parent_base_type = NodeConfig
    assoc_base_type = NodeGUI
    _attr_name = 'INSPECTOR'

def node_config(node_config_cls: type[NodeConfig]):
    """
    Registers an inspector for a node config. The inspector of a config is inherited to its sub-classes,
    but can be overriden by specifying a new gui for the sub-class.
    """
    
    return __InspectorToNodeConfig.associate_decor(node_config_cls)

def get_config_inspector_cls(node_config_cls: type[NodeConfig]):
    return __InspectorToNodeConfig.get_assoc(node_config_cls)


class __GuiToNode(Association[Node, NodeGUI]):
    
    parent_base_type = Node
    assoc_base_type = NodeGUI
    _attr_name = 'GUI'
    
def node_gui(node_cls: type[Node]):
    """
    Registers a node gui for a node class. The gui of a node is inherited to its sub-classes,
    but can be overridden by specifying a new gui for the sub-class.
    """
    
    return __GuiToNode.associate_decor(node_cls)

def get_node_gui_cls(node_cls: type[Node]):
    """Returns the type of NodeGUI this Node has"""
    return __GuiToNode.get_assoc(node_cls)
    
