from dataclasses import dataclass
from typing import Type, Optional, Dict, TYPE_CHECKING
from inspect import getsource, getmodule

from ryvencore import Node

from types import MappingProxyType

if TYPE_CHECKING:
    from ryvencore_qt import NodeGUI

class SourceCodeStorage:
    """
    Stores node's source code as well as custom gui code.
    """
    
    def __init__(self, edit_src_codes = False):
        self.edit_src_codes = edit_src_codes
        self.__class_codes: Dict[Type[Node], NodeTypeCodes] = {}
        self.__class_codes_proxy = MappingProxyType(self.__class_codes)
        
        # below fields are only used when src code edits are enabled
        
        # maps node- or widget classes to their full module source code
        self.__mod_codes: Dict[Type, str] = {}
        self.__mode_codes_proxy = MappingProxyType(self.__mod_codes)
        # maps node- or widget objects to their modified source code
        self.__modif_codes: Dict[object, str] = {} 
        self.__modif_codes_proxy = MappingProxyType(self.__modif_codes)
    
    @property
    def class_codes(self):
        return self.__class_codes_proxy
    
    @property
    def mod_codes(self):
        return self.__mode_codes_proxy
    
    @property
    def modif_codes(self):
        return self.__modif_codes_proxy
    
    def register_node_type(self, n: Type[Node], defer_code_loading=True):
        """
        Registers a node type and loads its source code directly if deferred 
        source code loading is disabled.
        """

        if not defer_code_loading:
            self.load_src_code(n)
        else:
            self.__class_codes[n] = None
            
    def load_src_code(self, n: Type[Node], custom_gui: 'Type[NodeGUI]' = None):
        """
        Loads a node's source code and optionally its custom gui.
        
        If the GUI parameter is None, then it attempts to find the GUI
        through a dynamically set GUI attribute in the node.
        """
        
        if custom_gui:
            gui = custom_gui
        else:
            gui: Type[NodeGUI] = n.GUI if hasattr(n, 'GUI') else None 
        
        has_gui = gui is not None
        has_mw = has_gui and gui.main_widget_class is not None

        src = getsource(n)
        mw_src = getsource(gui.main_widget_class) if has_mw else None
        inp_src = {
            name: getsource(cls)
            for name, cls in gui.input_widget_classes.items()
        } if has_gui else None

        self.__class_codes[n] = NodeTypeCodes(
            node_cls=src,
            main_widget_cls=mw_src,
            custom_input_widget_clss=inp_src,
        )

        if self.edit_src_codes:
            
            self.__mod_codes[n] = getsource(getmodule(n))
            if has_mw:
                self.__mod_codes[gui.main_widget_class] = getsource(getmodule(gui.main_widget_class))
                for inp_cls in gui.input_widget_classes.values():
                    self.__mod_codes[inp_cls] = getsource(getmodule(inp_cls))    


@dataclass
class NodeTypeCodes:
    node_cls: str
    main_widget_cls: Optional[str]
    custom_input_widget_clss: Dict[str, str]


class Inspectable:
    """
    Represents an object whose source code can be inspected.
    This is either a node or some node widget.
    Used by the code editor to store polymorphic references to
    objects which can be inspected.
    """
    def __init__(self, node, obj, code):
        self.node = node
        self.obj = obj
        self.code = code


class NodeInspectable(Inspectable):
    def __init__(self, node, code):
        super().__init__(node, node, code)


class MainWidgetInspectable(Inspectable):
    pass


class CustomInputWidgetInspectable(Inspectable):
    pass
