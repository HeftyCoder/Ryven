from __future__ import annotations

from ryvencore import (
    Data, 
    Node,
    Flow,
    Session, 
)

from enum import Enum
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .graph_player import GraphPlayer


# ----CONFIGURATION----

# TODO Provide a standard for defining and setting metadata for configs.
# Each config or property of the config should have some way of accesssing metadat
# through a unified API (most likely an abstract method on NodeConfig)

class NodeConfig:
    """An interface representing a node's configuration"""
    
    def __init__(self, node: CognixNode = None):
        self._node = node
    
    def node(self) -> CognixNode:
        """A property returning the node of this configuration"""
        return self._node
    
    @abstractmethod
    def to_json(self, indent=1) -> str:
        """Returns JSON representation of the object"""
        pass
    
    @abstractmethod
    def load(self, data: dict | str):
        """Loads the configuration from a JSON-compliant dict or a JSON str"""
        pass
    
# ----NODES----

class CognixNode(Node):
    """The basic building block of CogniX"""
    
    config_type: type[NodeConfig] | None = None
    """A JSON serializable configuration"""
    
    def __init__(self, flow: CognixFlow):
        super().__init__(flow)
        
        self.flow = flow
        self._config = self.config_type(self) if self.config_type else None
    
    @property
    def config(self) -> NodeConfig | None:
        """Returns this node's configuration, if it exists"""
        return self._config
    
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
    def reset(self):
        """
        VIRTUAL
        
        This is called when the node is reset. Typically happens when the GraphPlayer
        enters GraphState.Playing state. Implement any initialization here.
        """
        pass
    
    def on_start(self):
        pass
    
    def on_stop(self):
        pass
    
    def on_application_end(self):
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
    

# ----FLOW----

class CognixFlow(Flow):
    """
    An extension to a ryvencore Flow for CogniX.
    
    Specifically, it adds a CognixFlowPlayer for interpreting the graph.
    """
    
    _node_base_type = CognixNode
    
    def __init__(self, session: CognixSession, title: str):
        super().__init__(session, title)
        self.session = session


# ----SESSION----

class CognixSession(Session):
    """
    An extension to a ryvencore Session for CogniX.
    """
    
    _flow_base_type = CognixFlow

