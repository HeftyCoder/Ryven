"""
Provides utilities for assigning functions for getting associations between objects

For example, a node must be able to get its GUI, but how it's assigned to a specific node
and how it's retrieved from a node is set outside of this core Qt library.
"""

from typing import TypeVar, Generic, Any, Callable
from ryvencore import InfoMsgs, Node, Data
from .nodes.gui import NodeGUI
from .base_widgets import InspectorWidget
    

ToType = TypeVar('ToType')
"""The To in the From-To type relationship"""
FromType = TypeVar('FromType')
"""The From in the From-To type relationship"""


class Association(Generic[FromType, ToType]):
    """
    A class for associating two types. It associates the definition of
    two types so that you can find the ToType from the FromType. This association
    also handles inheritance through MRO and registered virtual subclasses.

    The registered virtual subclasses search can be slow due to access restrictions
    for specific virtual types.
    
    The fastest approach, albeit a bit cumbersome, would be to explicitly state the
    association between the two types and not rely on inheritance. For small inheritance
    chains, however, the slowdown should be negligible.
    """
        
    def __init__(
        self, 
        parent_base_type: type[FromType], 
        assoc_base_type: type[ToType]
    ):
        
        self.__from_type = parent_base_type
        self.__to_type = assoc_base_type
        self.__from_to_dict: dict[type[FromType], type[ToType]] = {}
        """Stores any direct associations internally."""
    
    @property
    def from_type(self):
        return self.__from_type
    
    @property
    def to_type(self):
        return self.__to_type
    
    def associate_decor(self, *from_types: tuple[type[FromType]]):
        """Returns a decorator for creating the association"""
        
        def register(to_type: type[ToType]):
            return self.associate(to_type, *from_types)

        return register

    def associate(self, to_type: type[ToType], *from_types: type[FromType]):
        """Creates a from-to association"""
        
        if not issubclass(to_type, self.__to_type):
            raise ValueError(f"To Type: {to_type} is not of type {self.__to_type}")
        
        for from_type in from_types:
            
            if not issubclass(from_type, self.__from_type):
                InfoMsgs.write(f"From Type: {from_type} is not of type {self.__from_type}")
                continue
                    
            if from_type in self.__from_to_dict:
                InfoMsgs.write(f'{from_type} has defined an explicit association {self.__from_to_dict[from_type]}')
                continue
        
            self.__from_to_dict[from_type] = to_type
            InfoMsgs.write(f"Registered association: {to_type} for {from_type}")
        
        return to_type   

    def get_assoc(self, from_type: type[FromType], check_mro=True, check_virtual=False) -> type[ToType] | None:
        """
        Retrieves an association if it exists
        
        MRO is the typical python inheritance check.
        
        """
        
        if not issubclass(from_type, self.__from_type):
            raise ValueError(f"From Type: {from_type} is not of type {self.__from_type}")
        
        # returns an immediate association, if it exists 
        if not check_mro and not check_mro:
            return self.__from_to_dict.get(from_type)
        
        # ABC checking 
        
        # Checks based on the MRO
        if check_mro:
            for t in from_type.mro():
                to_type = self.__from_to_dict.get(t)
                if to_type:
                    return to_type
        
        # At this point, all we can do is check every key and stop if we find a subclss
        if check_virtual:
            for key, value in self.__from_to_dict.items():
                if issubclass(from_type, key):
                    return value

#   Node and NodGUI
_node_to_gui = Association(Node, NodeGUI)

def set_node_gui_assoc(assoc: Association[Node, NodeGUI]):
    """Sets the association between Node and NodeGUI"""
    global _node_to_gui
    _node_to_gui = assoc

def node_gui_assoc():
    """Retrieves the Association between Node and NodeGUI."""
    return _node_to_gui

def node_gui(node_cls: type[Node]):
    """
    Registers a node gui for a node class. The gui of a node is inherited to its sub-classes,
    but can be overridden by specifying a new gui for the sub-class.
    """
    
    return _node_to_gui.associate_decor(node_cls)

#   Inspected and Inspector (Anything can be inspected)
_obj_to_inspector = Association(object, InspectorWidget)

def set_obj_insp_assoc(assoc: Association[object, InspectorWidget]):
    """
    Sets the association between an object and an Inspector
    
    Used for anyone who wants to mainly change the attribute name for this association
    """
    global _obj_to_inspector
    _obj_to_inspector = assoc

def obj_insp_assoc():
    """Retrieves the Association between object type and inspector type"""
    return _obj_to_inspector

def inspector(obj_type):
    """
    Registers an inspector for an object. The inspector of an object is inherited to its sub-classes,
    but can be overridden by specifying a new inspector for the sub-class.
    """
    
    return _obj_to_inspector.associate_decor(obj_type)

class GUIEnvProxy:
    """Provides utilities for retrieving GUI related data"""
    
    def __init__(
        self, 
        get_node_gui: Callable[[type[Node]], type[NodeGUI] | None],
        get_inspector: Callable[[Any], type[InspectorWidget]]
    ):
        self.__get_node_gui = get_node_gui
        self.__get_inspector = get_inspector
    
    def get_node_gui(self, node_type: type[Node]):
        return self.__get_node_gui(node_type)
    
    def get_inspector(self, obj):
        return self.__get_inspector(obj)

def create_default_env():
    """
    Creates a default GUI environment based on the internals of this module
    
    Refer to set_obj_insp_association etc.
    """
    
    return GUIEnvProxy(
        _node_to_gui.get_assoc,
        _obj_to_inspector.get_assoc,
        
    )