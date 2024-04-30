"""Defines the abstract classes for nodes in CogniX"""
from __future__ import annotations
from ryvencore import Node
from ryvencore import Event
from ryvencore.addons.builtin import VarsAddon
from ryvencore.utils import get_mod_classes
from abc import ABCMeta, abstractmethod
from inspect import isclass

from ..config.abc import NodeConfig


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..flow import CognixFlow
    
class CognixNode(Node, metaclass=ABCMeta):
    """The basic building block of CogniX"""
    
    config_type: type[NodeConfig] | None = None
    """A configuration type that will be instantiated with the node, if given"""
    _config_as_cls_type: type[NodeConfig] | None = None
    """
    A nested class named Config can be defined to avoid setting the config_type.
    It will be used if the config_type is not defined.
    """
    def __init_subclass__(cls):
        attr = getattr(cls, 'Config', None)
        if (attr and isclass(attr)):
            cls._config_as_cls_type = attr
        
    def __init__(self, flow: CognixFlow):
        super().__init__(flow)
        
        self.updated = Event(int)
        self.flow = flow
        self.__vars_addon = self.flow.session.addons[VarsAddon.addon_name()]
        config_type = self.config_type if self.config_type else self._config_as_cls_type
        self._config = config_type(self) if config_type else None
    
    @property
    def config(self) -> NodeConfig | None:
        """Returns this node's configuration, if it exists"""
        return self._config
    
    @property
    def vars_addon(self) -> VarsAddon:
        """Returns the session's variable addon. Session local"""
        return self.__vars_addon
    
    def set_var_val(self, var_name: str, value):
        """Sets a variables' value"""
        self.vars_addon.var(self.flow, var_name).set(value)
    
    def get_var_val(self, var_name: str):
        """Gets a variables' value. If it doesn't exist, returns None"""
        var = self.vars_addon.var(self.flow, var_name)
        return var.get() if var else None
        
    def data(self) -> dict:
        return {
            **super().data(),
            'config': self._config.to_json() if self._config else None
        }
        
    def load(self, data: dict):
        super().load(data)
        config_data = data.get('config')
        if self._config and config_data:
            self._config.load(config_data)
        
    # VIRTUAL GOGNIX METHODS
    @abstractmethod
    def update_event(self, inp=-1):
        pass
    
    def reset(self):
        """
        VIRTUAL
        
        This is called when the node is reset. Typically happens when the GraphPlayer
        enters GraphState.Playing state. Implement any initialization here.
        """
        pass
    
    def on_start(self):
        """
        VIRTUAL
        
        Happens at the start of the graph player
        """
        pass
    
    def on_stop(self):
        """
        VIRTUAL
        
        Happens at the stop of the graph player
        """
        pass
    
    
    def on_application_end(self):
        """
        Runs when the application exits
        
        Maybe not useful right now
        """
        pass


class StartNode(CognixNode):
    """A node that has no inputs. It processes data only once."""
    
    def __init__(self, params):
        super().__init__(params)
        
    def update_event(self, inp=-1):
        """This method is called only once when the graph is starting."""
        return super().update_event(inp)
        

class FrameNode(CognixNode):
    """A node which updates every frame of the Cognix Application."""
    
    def __init__(self, params):
        super().__init__(params)
        # Setting this will stop the node from updating
        self._is_finished = False
    
    @property
    def is_finished(self):
        return self._is_finished
    
    def update_event(self, inp=-1):
        pass
    
    # Frame Updates
    def frame_update(self):
        """Wraps the frame_update_event with internal calls."""
        if self.frame_update_event():
            self.updating.emit(-1)
        
    @abstractmethod
    def frame_update_event(self) -> bool:
        """Called on every frame. Data might have been passed from other nodes"""
        pass
    
    def reset(self):
        self._is_finished = False
        return super().reset()

def get_cognix_node_classes(modname: str, to_fill: list | None = None, base_type: type = None):
    """Returns a list of node types defined in the current mode"""
    
    def filter_nodes(obj):
        return issubclass(obj, CognixNode) and not obj.__abstractmethods__
        
    return get_mod_classes(modname, to_fill, filter_nodes)

