from ryvencore import Node, Flow
from ryvencore.InfoMsgs import InfoMsgs
from ryvencore.Base import Event
from ryvencore.Node import NodeInput, NodeOutput
from abc import ABCMeta, abstractmethod

from ryvencore import Data

class CognixNode(Node, metaclass=ABCMeta):
    """The basic building block of a Cognix Graph"""
    
    def __init__(self, params):
        super().__init__(params)
        # events that ryvencore doesn't have
        self.updated = Event(int)
        self.output_changed = Event(NodeOutput, Data)
        
        from .graph_player import GraphPlayer # to avoid circular imports
        self._player: GraphPlayer = None
    
    @property
    def player(self):
        return self._player
    
    def update(self, inp=-1):
        """Overrides ryvencore to add an updated event and silence InfoMsgs"""
        if self.block_updates:
            return
        
        self.updating.emit(inp)
        self.flow.executor.update_node(self, inp)
        self.updated.emit(inp)
    
    def input(self, index: int):
        """Overriden to silence InfoMsgs"""
        return self.flow.executor.input(self, index)
    
    def set_output_val(self, index: int, data: Data):
        """Overrides ryvencore to add an on_output_changed event and silence InfoMsgs"""
        
        assert isinstance(data, Data), "Output value must be of type ryvencore.Data"
        self.flow.executor.set_output_val(self, index, data)
        self.output_changed.emit(self._outputs[index], data)
        
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
